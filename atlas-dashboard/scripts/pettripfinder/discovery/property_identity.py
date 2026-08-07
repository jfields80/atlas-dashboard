"""PTF-DISCOVERY -- property-level identity extraction, naming, and guards.

Three defects in an ad-hoc Cleveland census pipeline motivated this module,
and each one is a rule here rather than a habit:

1. NAME/ADDRESS PAIRING. Names were collected in one pass and addresses in
   another, then joined by position. Every Destination Cleveland property
   page opens with a "<< Back to <PREVIOUS PROPERTY>" breadcrumb, so the name
   pass picked up 158 breadcrumbs and the two lists drifted by one row:
   "Courtyard by Marriott (Beachwood)" ended up carrying the Airport North
   hotel's street address. ``parse_property_container`` reads ONE property
   from ONE container and returns name and address bound together, or
   returns an incomplete record. It never reaches past its container.

2. CANONICAL NAMING. A trailing parenthetical was stripped as a "directory
   area label". For chain properties that parenthetical is the only
   disambiguator, so six distinct Courtyard hotels collapsed into one record
   named "Courtyard by Marriott". ``canonical_property_names`` strips a
   parenthetical only when doing so leaves the property distinguishable from
   its siblings, and otherwise keeps it.

3. DEDUPE. Records were keyed by canonical name alone, so a name collision
   deleted a real hotel at a different address. ``street_identity`` and
   ``assert_distinct_street_identities`` make the street the hard guard: the
   production ``deduplicate()`` pipeline already respects this, and these
   helpers exist so an ad-hoc pipeline cannot quietly skip it again.

A fourth rule concerns venue leakage. Classification uses structured evidence
first ("Guest Rooms" is a lodging section on the source page) and otherwise a
bounded, word-boundary head-noun test. It never matches loose substrings: an
earlier venue filter keyed on the fragment "field" and discarded every
Fairfield Inn, and ``test_property_identity`` keeps that from recurring.
Anything undecidable becomes NEEDS_REVIEW and is reported -- never silently
dropped.

Pure functions over already-captured text. No network, no file IO.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

SCHEMA = "ptf-property-identity/1.0"


class PropertyIdentityError(ValueError):
    """A malformed container or a violated identity guard (fail closed)."""


# --------------------------------------------------------------------------- #
# Lodging classification.
# --------------------------------------------------------------------------- #

LODGING_CONFIRMED = "LODGING_CONFIRMED"
LODGING_BY_NAME = "LODGING_BY_NAME"
NON_LODGING = "NON_LODGING"
NEEDS_REVIEW = "NEEDS_REVIEW"

#: A source-page section that only a lodging listing carries. Structured
#: evidence, and the only signal trusted on its own.
LODGING_SECTION_MARKERS = ("Guest Rooms",)

#: Head nouns, matched as whole words only. "Inn" must never match inside
#: another word, and no rule may ever consult a fragment such as "field".
LODGING_HEAD_NOUNS = (
    "hotel", "hotels", "inn", "inns", "suites", "motel", "lodge", "resort",
    "hostel", "motor lodge", "bed and breakfast", "b&b", "guesthouse",
)
NON_LODGING_HEAD_NOUNS = (
    "restaurant", "bar", "cafe", "café", "bistro", "grill", "grille", "tavern",
    "brewery", "taproom", "stadium", "arena", "museum", "theatre", "theater",
    "park", "trail", "bike area", "area", "golf course", "winery", "vineyard",
    "casino", "club", "market", "gallery", "zoo", "aquarium", "center",
    "centre", "school", "university", "hall", "church", "spa",
)

#: Exact lodging brand phrases, matched at word boundaries. A brand is bounded
#: and checkable in a way a heuristic is not: "Travelodge" and "Courtyard by
#: Marriott" carry no generic lodging noun, and inventing one (matching the
#: fragment "lodge" inside "Travelodge") is how the "field"/Fairfield bug
#: happened. Extend this list with real brands, never with fragments.
LODGING_BRANDS = (
    "marriott", "hilton", "hyatt", "sheraton", "westin", "four points",
    "doubletree", "embassy suites", "homewood", "home2", "hampton",
    "residence inn", "courtyard by marriott", "springhill", "towneplace",
    "fairfield", "ac hotel", "aloft", "element", "moxy", "travelodge",
    "wyndham", "ramada", "days inn", "super 8", "baymont", "microtel",
    "la quinta", "best western", "holiday inn", "crowne plaza", "staybridge",
    "candlewood", "avid", "kimpton", "intercontinental", "radisson",
    "country inn", "park inn", "choice hotels", "comfort inn", "comfort suites",
    "quality inn", "sleep inn", "clarion", "cambria", "econo lodge",
    "rodeway", "mainstay", "woodspring", "extended stay", "sonesta",
    "red roof", "motel 6", "studio 6", "drury", "great wolf lodge",
)

#: Connectors that turn a following noun into a LOCATION reference rather than
#: the thing itself: "1833 Restaurant at the Hotel at Oberlin" is a restaurant,
#: and "Alfredo's at the Inn" is not a hotel.
_LOCATIVE = re.compile(r"\b(?:at|in|inside|near|by)\s+(?:the\s+)?$", re.I)

_PAREN_TAIL = re.compile(r"\s*\(([^)]{2,80})\)\s*$")


def _word_positions(haystack: str, needle: str) -> List[int]:
    """Start offsets of ``needle`` in ``haystack`` at word boundaries only."""
    pattern = re.compile(r"\b%s\b" % re.escape(needle), re.I)
    return [m.start() for m in pattern.finditer(haystack)]


def _first_head_noun(name: str) -> Tuple[Optional[str], Optional[str], int]:
    """(kind, noun, offset) for the EARLIEST head noun in ``name``.

    The head of an English venue name comes first ("Restaurant at the Hotel"
    is a restaurant), so the earliest match wins rather than the last."""
    best: Tuple[Optional[str], Optional[str], int] = (None, None, len(name) + 1)
    for kind, vocabulary in (("lodging", LODGING_HEAD_NOUNS),
                             ("non_lodging", NON_LODGING_HEAD_NOUNS)):
        for noun in vocabulary:
            for offset in _word_positions(name, noun):
                # Prefer the earliest; on a tie prefer the longer noun so
                # "bike area" beats "area".
                if offset < best[2] or (offset == best[2] and len(noun) > len(best[1] or "")):
                    best = (kind, noun, offset)
    return best


def classify_lodging(display_name: str,
                     section_markers: Sequence[str] = ()) -> Tuple[str, str]:
    """(state, reason) for whether ``display_name`` is a lodging property.

    Structured evidence from the source page decides on its own. Otherwise a
    bounded head-noun test applies, and an undecidable name becomes
    NEEDS_REVIEW rather than being dropped."""
    markers = set(section_markers)
    for marker in LODGING_SECTION_MARKERS:
        if marker in markers:
            return LODGING_CONFIRMED, "source page carries its %r section" % marker

    name = display_name.strip()
    if not name:
        return NEEDS_REVIEW, "empty name"

    # A trailing parenthetical is a location qualifier, not the head noun:
    # "Eliot's Bar (Hilton Cleveland Downtown)" is a bar inside a hotel.
    base = _PAREN_TAIL.sub("", name).strip() or name

    kind, noun, offset = _first_head_noun(base)

    # A brand counts as a lodging signal only where it is not merely naming
    # the place something else sits inside ("The Greatroom Restaurant at
    # Marriott Key Tower" is a restaurant).
    brand = None
    for candidate in LODGING_BRANDS:
        for position in _word_positions(base, candidate):
            if not _LOCATIVE.search(base[:position]):
                if brand is None or position < brand[1]:
                    brand = (candidate, position)
                break

    if kind is None:
        if brand:
            return LODGING_BY_NAME, "%r carries the lodging brand %r" % (base, brand[0])
        return NEEDS_REVIEW, "no recognised lodging or venue head noun in %r" % base

    preceding = base[:offset]
    if _LOCATIVE.search(preceding):
        # The noun says WHERE this is, not WHAT it is.
        other_kind, other_noun, _ = _first_head_noun(preceding)
        if other_kind == "non_lodging":
            return NON_LODGING, ("%r is a %s located at a %s" % (base, other_noun, noun))
        return NEEDS_REVIEW, (
            "%r names a %s only as a location (%r), so its own type is unstated"
            % (base, noun, preceding.strip()))

    if kind == "non_lodging":
        # Both kinds present and neither is behind a locative -- e.g. "Kent
        # State University Hotel & Conference Center". Ambiguity resolves to
        # REVIEW, never to silent exclusion of a real hotel.
        lodging_present = any(
            _word_positions(base, n) for n in LODGING_HEAD_NOUNS)
        if lodging_present or brand:
            return NEEDS_REVIEW, (
                "%r carries both venue (%r) and lodging vocabulary -- ambiguous, "
                "review rather than exclude" % (base, noun))
        return NON_LODGING, "%r has the venue head noun %r" % (base, noun)
    return LODGING_BY_NAME, "%r has the lodging head noun %r" % (base, noun)


# --------------------------------------------------------------------------- #
# Property containers.
# --------------------------------------------------------------------------- #

#: The navigation breadcrumb that caused the one-row offset. It names the
#: PREVIOUS property and must never be read as this container's name. The
#: leading run accepts ANY punctuation, not just a guillemet: a capture whose
#: encoding was mangled arrives as "� Back to Aloft", and a breadcrumb
#: that is not recognised becomes a phantom hotel carrying its neighbour's
#: address. The anchor is the literal phrase, so this stays bounded.
BREADCRUMB = re.compile(r"^[^\w]*Back to\s+(?P<previous>.+?)\s*$", re.I)


def is_navigation_breadcrumb(name: str) -> bool:
    """True when ``name`` is a source's 'back to the previous listing' link.

    Intake paths that read already-parsed records (rather than containers)
    must call this: batch-001 admitted ten breadcrumb rows as hotels."""
    return bool(BREADCRUMB.match((name or "").strip()))

#: "Beachwood, OH, 44122" / "Cleveland, Ohio 44113" -- state spelled either way,
#: comma before the ZIP optional.
CITY_STATE_ZIP = re.compile(
    r"^(?P<city>[A-Za-z .'\-]+?),\s*(?P<state>OH|Ohio),?\s+(?P<zip>\d{5})(?:-\d{4})?$", re.I)

#: A street line must begin with a house number; a bare street name is a
#: fragment, and accepting one previously gave 57 Akron hotels a footer address.
STREET_LINE = re.compile(r"^\d+[A-Za-z]?\s+\S.*$")

_LOCATION_HEADING = "location"
_NAME_STOP_WORDS = {"menu", "search", "area map", "calendar", "view website",
                    "+add to my trip", "location", "social", "business hours"}


@dataclass(frozen=True)
class PropertyRecord:
    """One property, every field read from the SAME container."""
    source_id: str
    display_name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    phone: str = ""
    source_url: str = ""
    has_official_link: bool = False
    lodging_state: str = NEEDS_REVIEW
    lodging_reason: str = ""
    complete: bool = False
    incomplete_reasons: Tuple[str, ...] = ()
    previous_in_source: str = ""
    section_markers: Tuple[str, ...] = ()

    @property
    def street_identity(self) -> str:
        return street_identity(self.address, self.postal_code)


def parse_property_container(text: str, source_id: str,
                             source_url: str = "") -> PropertyRecord:
    """Read ONE property from ONE container.

    ``source_id`` is the container's own identifier (for Destination
    Cleveland, the property page slug) and is never derived from position in
    a list. Nothing outside ``text`` is consulted, so a neighbouring
    property's address cannot reach this record."""
    lines = [l.strip() for l in (text or "").splitlines()]
    reasons: List[str] = []

    # ---- name: the line AFTER the breadcrumb, never the breadcrumb ------- #
    display_name = ""
    previous = ""
    for index, line in enumerate(lines):
        match = BREADCRUMB.match(line)
        if not match:
            continue
        previous = match.group("previous")
        for candidate in lines[index + 1:index + 4]:
            if candidate and candidate.strip().lower() not in _NAME_STOP_WORDS:
                display_name = candidate
                break
        break
    if not display_name:
        # No breadcrumb (first property in a source, or a different template):
        # take the first substantive line that is not chrome.
        for line in lines[:12]:
            if line and line.strip().lower() not in _NAME_STOP_WORDS:
                display_name = line
                break
    if not display_name:
        reasons.append("no property name in container")
    if display_name and BREADCRUMB.match(display_name):
        raise PropertyIdentityError(
            "%s: refused to use the navigation breadcrumb %r as a property name"
            % (source_id, display_name))

    # ---- address: the block under this container's Location heading ------ #
    address = city = state = postal = phone = ""
    try:
        start = next(i for i, l in enumerate(lines) if l.lower() == _LOCATION_HEADING)
    except StopIteration:
        start = None
        reasons.append("no Location block in container")
    if start is not None:
        for line in lines[start + 1:start + 8]:
            if not line:
                continue
            if not address and STREET_LINE.match(line):
                address = line
                continue
            csz = CITY_STATE_ZIP.match(line)
            if csz and not postal:
                city = csz.group("city").strip()
                state = "OH"
                postal = csz.group("zip")
                continue
            if not phone and re.match(r"^[\d().+\- ]{10,20}$", line):
                phone = line
        if not address:
            reasons.append("no street line (a house number is required)")
        if not postal:
            reasons.append("no city/state/ZIP line")

    markers = tuple(m for m in LODGING_SECTION_MARKERS if m in lines)
    state_, reason = classify_lodging(display_name, markers)

    return PropertyRecord(
        source_id=source_id, display_name=display_name, address=address, city=city,
        state=state, postal_code=postal, phone=phone, source_url=source_url,
        has_official_link=("VIEW WEBSITE" in lines),
        lodging_state=state_, lodging_reason=reason,
        complete=not reasons, incomplete_reasons=tuple(reasons),
        previous_in_source=previous, section_markers=markers)


def validate_pairing(record: PropertyRecord) -> List[str]:
    """Warnings about a record whose parts may not describe one property.

    A parenthetical area label that disagrees with the container's own city
    is reported, never silently resolved: the label and the address are both
    published by the source, and only re-reading the container can say which
    is right."""
    warnings: List[str] = []
    if not record.complete:
        return ["incomplete: %s" % "; ".join(record.incomplete_reasons)]
    if record.display_name and record.previous_in_source and \
            record.display_name.strip().lower() == record.previous_in_source.strip().lower():
        warnings.append("name equals the previous property in the source -- possible offset")
    tail = _PAREN_TAIL.search(record.display_name)
    if tail and record.city:
        label = tail.group(1).lower()
        city = record.city.lower()
        parts = [p.strip() for p in re.split(r"[/,]", label) if p.strip()]
        if parts and not any(p in city or city in p for p in parts):
            warnings.append(
                "area label %r does not name the container's city %r"
                % (tail.group(1), record.city))
    return warnings


# --------------------------------------------------------------------------- #
# Canonical naming: a disambiguator is only dropped when it disambiguates
# nothing.
# --------------------------------------------------------------------------- #

def _base_name(display_name: str) -> str:
    return _PAREN_TAIL.sub("", (display_name or "").strip()).strip()


def _tidy(label: str) -> str:
    """Normalise a disambiguating fragment into name-shaped text."""
    text = re.sub(r"\s*/\s*", " ", re.sub(r"\s+", " ", label or "")).strip()
    return " ".join(w if (w[:1].isupper() or not w[:1].isalpha()) else w.capitalize()
                    for w in text.split())


def canonical_property_names(display_names: Sequence[str],
                             disambiguators: Optional[Sequence[str]] = None) -> List[str]:
    """Canonical name PER RECORD, resolved across the whole set.

    Returns a list positionally aligned with ``display_names`` -- not a dict
    keyed by name, because two records may legitimately arrive with the same
    display name and a dict would silently drop one of them.

    A trailing parenthetical is dropped only when no other record shares the
    resulting base name. Where the base name IS shared, that parenthetical is
    what distinguishes two real hotels, so it is folded into the canonical
    name rather than discarded.

    ``disambiguators`` (optionally the record's own city, read from the same
    container as its address) is used only for a record that shares a base
    name and has no parenthetical of its own -- the "two Staybridge Suites"
    case. It is source evidence, not invention: nothing here composes a
    marketing name the sources do not support. A record that still cannot be
    told apart keeps its base name and is reported by ``ambiguous_names``."""
    names = list(display_names)
    hints = list(disambiguators or [""] * len(names))
    if len(hints) != len(names):
        raise PropertyIdentityError(
            "disambiguators must align with display_names (%d vs %d)"
            % (len(hints), len(names)))

    bases: Dict[str, int] = {}
    for name in names:
        base = _base_name(name)
        bases[base] = bases.get(base, 0) + 1

    canonical: List[str] = []
    for name, hint in zip(names, hints):
        base = _base_name(name)
        tail = _PAREN_TAIL.search((name or "").strip())
        shared = bases.get(base, 0) > 1
        if tail and shared:
            canonical.append("%s %s" % (base, _tidy(tail.group(1))))
        elif tail:
            canonical.append(base)
        elif shared and (hint or "").strip() and (hint or "").strip().lower() not in base.lower():
            canonical.append("%s %s" % (base, _tidy(hint)))
        else:
            canonical.append(base)
    return canonical


def ambiguous_names(canonical_names: Sequence[str]) -> List[str]:
    """Canonical names still claimed by more than one record.

    These cannot identify a property: one would silently become the survivor
    for all. They must be resolved from evidence, never by picking."""
    counts: Dict[str, int] = {}
    for canonical in canonical_names:
        counts[canonical] = counts.get(canonical, 0) + 1
    return sorted(name for name, n in counts.items() if n > 1)


# --------------------------------------------------------------------------- #
# Street identity: the hard guard.
# --------------------------------------------------------------------------- #

_STREET_NOISE = re.compile(r"[^a-z0-9]+")
_STREET_SUFFIX = {
    "street": "st", "st": "st", "road": "rd", "rd": "rd", "avenue": "ave",
    "ave": "ave", "boulevard": "blvd", "blvd": "blvd", "drive": "dr", "dr": "dr",
    "lane": "ln", "ln": "ln", "circle": "cir", "cir": "cir", "court": "ct",
    "ct": "ct", "parkway": "pkwy", "pkwy": "pkwy", "place": "pl", "pl": "pl",
    "highway": "hwy", "hwy": "hwy", "square": "sq", "sq": "sq", "terrace": "ter",
}


def street_identity(address: str, postal_code: str = "") -> str:
    """A comparable street key: house number + normalised street + ZIP.

    Deliberately conservative -- it normalises spelling ("Street"/"St") and
    nothing else. Two addresses that differ in house number or ZIP are
    different places, and this key says so."""
    text = (address or "").strip().lower()
    text = re.sub(r"[.,]", " ", text)
    tokens = [t for t in _STREET_NOISE.split(text) if t]
    tokens = [_STREET_SUFFIX.get(t, t) for t in tokens]
    return "%s|%s" % (" ".join(tokens), (postal_code or "").strip())


SAME_PROPERTY = "SAME_PROPERTY"
DISTINCT_PROPERTIES = "DISTINCT_PROPERTIES"
NEEDS_ADJUDICATION = "NEEDS_ADJUDICATION"


def compare_identities(name_a: str, street_a: str,
                       name_b: str, street_b: str,
                       rebrand_evidence: bool = False) -> Tuple[str, str]:
    """(verdict, reason) for two identity records.

    Encodes the rule the broken pipeline lacked: matching names never
    outrank differing streets."""
    same_name = (name_a or "").strip().lower() == (name_b or "").strip().lower()
    same_street = street_a == street_b and bool(street_a.strip("|"))
    if same_name and same_street:
        return SAME_PROPERTY, "same name at the same street identity"
    if same_name and not same_street:
        if rebrand_evidence:
            return NEEDS_ADJUDICATION, (
                "same name at different streets, with rebrand evidence -- adjudicate")
        return DISTINCT_PROPERTIES, (
            "same name at different street identities: two properties of one brand, "
            "not a duplicate")
    if same_street and not same_name:
        return NEEDS_ADJUDICATION, (
            "two names at one street identity -- same-campus entities are possible, "
            "so this is a review, never an automatic merge")
    return DISTINCT_PROPERTIES, "different name and different street identity"


def assert_distinct_street_identities(records: Sequence[Dict],
                                      name_key: str = "canonical_name",
                                      street_key: str = "street_identity") -> None:
    """Fail closed if a pipeline is about to drop a record whose street
    identity is unique. Cheap insurance against re-implementing the
    name-keyed dedupe that deleted 26 real hotels."""
    by_name: Dict[str, List[Dict]] = {}
    for record in records:
        by_name.setdefault((record.get(name_key) or "").strip().lower(), []).append(record)
    collisions = {}
    for name, group in by_name.items():
        streets = {r.get(street_key) for r in group}
        if len(group) > 1 and len(streets) > 1:
            collisions[name] = sorted(str(s) for s in streets)
    if collisions:
        raise PropertyIdentityError(
            "canonical name collision across DIFFERENT street identities -- these are "
            "distinct properties and must not share one identity: %s" % collisions)


__all__ = [
    "SCHEMA", "PropertyIdentityError", "PropertyRecord",
    "LODGING_CONFIRMED", "LODGING_BY_NAME", "NON_LODGING", "NEEDS_REVIEW",
    "LODGING_HEAD_NOUNS", "NON_LODGING_HEAD_NOUNS", "BREADCRUMB",
    "SAME_PROPERTY", "DISTINCT_PROPERTIES", "NEEDS_ADJUDICATION",
    "classify_lodging", "is_navigation_breadcrumb", "parse_property_container",
    "validate_pairing",
    "canonical_property_names", "ambiguous_names", "street_identity",
    "compare_identities", "assert_distinct_street_identities",
]

"""PTF-DISCOVERY-001 -- FD-5 stable-key counting for the capture-time identity gate.

The capture runner has always verified identity before touching a policy region
(``runner.py``, IDENTITY before POLICY_SCAN). What it lacked was FD-5's
*evidentiary bar*: ``source_retrieval.assess_identity`` accepts ``EXACT_MATCH``
(``name AND (phone OR address)``) and ``STRONG_MATCH`` (which includes
``name AND city``). Under FD-5 those are **one** and **zero** approved stable
keys respectively, because name and city never count.

This module supplies the missing layer. It only ever WITHHOLDS: it can turn an
accepted verdict into ``IDENTITY_INCOMPLETE``, and it can never turn a rejected
one into a confirmation.

``assess_identity`` and ``verify_identity`` are deliberately NOT modified --
``operator_capture`` and the importer depend on their current behaviour, and an
additive wrapper is the safer shape (founder decision 5).

TWO RULES DECIDE EVERYTHING HERE
--------------------------------
1. **Two INDEPENDENT keys.** Independence is by *group*, not by count. The two
   address-derived variants share one group, so they can never be the two
   keys; the same holds for the two property-identifier variants, which are
   restatements of one fact.
2. **At least one key from an authoritative, field-specific source.** JSON-LD
   or structured metadata, a labelled DOM field, a field-specific rendered
   evidence view with geometry, or official adapter metadata. Generic body
   text, the page title, navigation chrome, marketing prose and unlabelled
   occurrences are never sufficient on their own -- an unlabelled digit run
   that happens to match a phone number is a coincidence, not a citation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery.url_record import (
    KEY_NORMALIZED_STREET_ADDRESS,
    KEY_OFFICIAL_PROPERTY_ID,
    KEY_POSTAL_PLUS_STREET_NUMBER,
    KEY_PROPERTY_PHONE,
    KEY_STABLE_CHAIN_IDENTIFIER,
)

from .contracts import DomSnapshot, ObservedIdentity

# --------------------------------------------------------------------------- #
# Approved keys and independence groups (founder decision 2).
#
# ``verified_coordinates`` is deliberately ABSENT. It remains a valid FD-5 key
# on the discovery/static path (``url_record.STABLE_IDENTITY_KEYS``, unchanged),
# but nothing at capture time can produce it: a ``DomSnapshot`` carries no
# coordinates and a ``QueueEntry`` carries no expected latitude/longitude, so
# listing it here would advertise a key this module can never collect. It is
# added back when, and only when, a real source for it exists.
# --------------------------------------------------------------------------- #

APPROVED_KEYS: FrozenSet[str] = frozenset({
    KEY_OFFICIAL_PROPERTY_ID,
    KEY_NORMALIZED_STREET_ADDRESS,
    KEY_POSTAL_PLUS_STREET_NUMBER,
    KEY_PROPERTY_PHONE,
    KEY_STABLE_CHAIN_IDENTIFIER,
})

GROUP_ADDRESS = "address"
GROUP_PHONE = "phone"
GROUP_PROPERTY_IDENTIFIER = "property_identifier"

#: Independence is decided here. Two keys in the same group restate one fact.
#:
#: The address pair is explicit in FD-5. The property-identifier pair is
#: grouped on the same principle: an official property ID and a stable
#: chain/property identifier are two names for the same brand-assigned handle,
#: and every founder-approved passing example pairs an identifier with an
#: address or a phone, never with the other identifier.
KEY_GROUPS: Dict[str, str] = {
    KEY_NORMALIZED_STREET_ADDRESS: GROUP_ADDRESS,
    KEY_POSTAL_PLUS_STREET_NUMBER: GROUP_ADDRESS,
    KEY_PROPERTY_PHONE: GROUP_PHONE,
    KEY_OFFICIAL_PROPERTY_ID: GROUP_PROPERTY_IDENTIFIER,
    KEY_STABLE_CHAIN_IDENTIFIER: GROUP_PROPERTY_IDENTIFIER,
}

MINIMUM_INDEPENDENT_KEYS = 2

# --------------------------------------------------------------------------- #
# Evidence bases (founder decision 3).
# --------------------------------------------------------------------------- #

BASIS_STRUCTURED = "structured_metadata"        # JSON-LD / microdata property block
BASIS_LABELED_DOM = "labeled_dom_field"         # itemprop, <address>, tel: href
BASIS_EVIDENCE_VIEW = "rendered_evidence_view"  # field-specific probe with geometry
BASIS_ADAPTER_METADATA = "adapter_metadata"     # official metadata from the adapter
BASIS_BODY_TEXT = "unlabeled_body_text"         # generic prose containment
BASIS_CANONICAL_URL = "canonical_url"           # the page's own <link rel=canonical>
BASIS_PAGE_TITLE = "page_title"                 # never counts, for any key
BASIS_URL = "url_only"                          # circular for the URL under test

#: Bases that can satisfy the "at least one authoritative key" requirement.
AUTHORITATIVE_BASES: FrozenSet[str] = frozenset({
    BASIS_STRUCTURED, BASIS_LABELED_DOM, BASIS_EVIDENCE_VIEW, BASIS_ADAPTER_METADATA,
})

#: Bases that may contribute a key but can never be the authoritative one.
#:
#: ``BASIS_CANONICAL_URL`` sits here rather than with the authoritative bases
#: (founder decision 5). A canonical link is genuinely page-published, so it is
#: not circular the way the requested URL is, and it may count toward the two
#: independent keys -- but it is not rendered, property-specific evidence, so it
#: can never be the one structured/strongly-bounded key confirmation requires.
WEAK_BASES: FrozenSet[str] = frozenset({BASIS_BODY_TEXT, BASIS_CANONICAL_URL})

#: Bases that never contribute a key at all. ``BASIS_URL`` is excluded because
#: proving a URL with that same URL is circular -- a property code lifted from
#: the address bar says nothing about what the page actually rendered.
NON_COUNTING_BASES: FrozenSet[str] = frozenset({BASIS_PAGE_TITLE, BASIS_URL})

#: Signals recorded for the operator but never counted as identity, whatever
#: their basis (founder decision 2).
NEVER_IDENTITY = ("name", "city", "page_title")


# --------------------------------------------------------------------------- #
# Outcomes (founder decision 4).
# --------------------------------------------------------------------------- #

IDENTITY_CONFIRMED = "IDENTITY_CONFIRMED"
IDENTITY_FAILED = "IDENTITY_FAILED"
IDENTITY_INCOMPLETE = "IDENTITY_INCOMPLETE"
ACCESS_BLOCKED = "ACCESS_BLOCKED"

IDENTITY_OUTCOMES: FrozenSet[str] = frozenset({
    IDENTITY_CONFIRMED, IDENTITY_FAILED, IDENTITY_INCOMPLETE, ACCESS_BLOCKED,
})

#: The only outcome that may proceed to policy interaction and capture.
MAY_PROCEED: FrozenSet[str] = frozenset({IDENTITY_CONFIRMED})


# --------------------------------------------------------------------------- #
# Normalisation.
# --------------------------------------------------------------------------- #

def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _phone_tail(value: str) -> str:
    return _digits(value)[-10:]


def _norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower()).split())


def _street_number(value: str) -> str:
    m = re.match(r"\s*(\d+)", (value or "").strip())
    return m.group(1) if m else ""


def token_present(needle: str, haystack: str) -> bool:
    """Boundary-aware containment on already-normalised text.

    The whole point: ``12`` must not match inside ``2012`` and ``main`` must not
    match inside ``domain``. A bare ``in`` test does both, which is how an
    unrelated year and an unrelated word can jointly "prove" a street address.
    """
    needle = (needle or "").strip()
    if not needle:
        return False
    return re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(needle),
                     haystack or "") is not None


# Abbreviation tables. Two renderings of one street must compare equal:
# "7474 N High St" and "7474 North High Street" are the same address.
_DIRECTIONALS = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
    "north": "north", "south": "south", "east": "east", "west": "west",
    "northeast": "northeast", "northwest": "northwest",
    "southeast": "southeast", "southwest": "southwest",
}

_STREET_TYPES = {
    "st": "street", "str": "street", "street": "street",
    "ave": "avenue", "av": "avenue", "avenue": "avenue",
    "rd": "road", "road": "road", "blvd": "boulevard", "boulevard": "boulevard",
    "dr": "drive", "drive": "drive", "ln": "lane", "lane": "lane",
    "pkwy": "parkway", "pky": "parkway", "parkway": "parkway",
    "hwy": "highway", "highway": "highway", "ct": "court", "court": "court",
    "cir": "circle", "circle": "circle", "pl": "place", "place": "place",
    "ter": "terrace", "terrace": "terrace", "trl": "trail", "trail": "trail",
    "sq": "square", "square": "square", "way": "way",
    "expy": "expressway", "expressway": "expressway",
    "tpke": "turnpike", "turnpike": "turnpike", "loop": "loop", "run": "run",
}

#: Everything from one of these onward is a unit designator, not the street.
#: "1375 N Cassady Ave Suite 100" and "1375 N Cassady Ave" are one address.
_UNIT_MARKERS = frozenset({
    "suite", "ste", "unit", "apt", "apartment", "fl", "floor", "rm", "room",
    "bldg", "building", "no", "num", "lot", "space", "trlr",
})


@dataclass(frozen=True)
class StreetParts:
    """A street address split into the pieces that can be compared safely."""

    number: str = ""
    core: FrozenSet[str] = frozenset()        # the name tokens that identify it
    directionals: FrozenSet[str] = frozenset()
    street_type: str = ""

    @property
    def usable(self) -> bool:
        return bool(self.number and self.core)


def parse_street(value: str) -> StreetParts:
    """Split a street address into number, name core, directionals and type."""
    tokens = _norm(value).split()
    if not tokens:
        return StreetParts()

    number = tokens[0] if tokens[0].isdigit() else ""
    rest = tokens[1:] if number else tokens

    # Drop the unit designator and everything after it.
    for i, tok in enumerate(rest):
        if tok in _UNIT_MARKERS:
            rest = rest[:i]
            break

    core, directions, stype = [], [], ""
    for tok in rest:
        if tok in _DIRECTIONALS:
            directions.append(_DIRECTIONALS[tok])
        elif tok in _STREET_TYPES:
            stype = _STREET_TYPES[tok]
        elif tok.isdigit() and len(tok) == 5:
            continue                      # a postal code trailing the street
        else:
            core.append(tok)

    return StreetParts(number=number, core=frozenset(core),
                       directionals=frozenset(directions), street_type=stype)


def _addresses_agree(expected: str, found: str) -> bool:
    """Do two renderings name the same street address?

    Requires ALL of:
      * street numbers present on both sides and exactly equal -- ``100`` and
        ``1100`` are different buildings, and substring containment called them
        the same;
      * street-name cores that agree, after abbreviation expansion and unit
        stripping. The smaller core must be contained in the larger, because a
        rendered ``<address>`` block legitimately carries city/state/ZIP that a
        queue's street-only field does not. Two cores that merely overlap
        partially do not agree;
      * street types that match when both sides state one -- ``Main Street``
        and ``Main Avenue`` are different streets.

    Directionals must agree when both sides state one; a side that omits the
    directional entirely is tolerated, since renderings routinely drop it.
    """
    a, b = parse_street(expected), parse_street(found)
    if not (a.usable and b.usable):
        return False
    if a.number != b.number:
        return False
    smaller, larger = sorted((a.core, b.core), key=len)
    if not smaller <= larger:
        return False
    if a.street_type and b.street_type and a.street_type != b.street_type:
        return False
    if a.directionals and b.directionals and a.directionals != b.directionals:
        return False
    return True


#: A complete phone-like run: optional country code, then 3-3-4 with at most one
#: separator between groups, and NOT embedded in a longer digit run.
_PHONE_RUN_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\d)")


def phone_runs(text: str) -> Tuple[str, ...]:
    """Every complete phone-like number in ``text``, as 10-digit tails.

    Scanned per line -- a capture's rendered text is newline-separated, so this
    is per text node in practice. The previous implementation concatenated every
    digit on the page into one string, which let ``$614``, ``475`` and
    ``Suite 7551`` from three unrelated sentences synthesise a phone number that
    was never printed.
    """
    out: List[str] = []
    for line in (text or "").splitlines():
        for match in _PHONE_RUN_RE.finditer(line):
            digits = _digits(match.group(0))
            if len(digits) >= 10:
                out.append(digits[-10:])
    return tuple(out)


#: Below this length a bare identifier in prose is a coincidence, not a citation
#: -- "chi" occurs inside "Chicago". Labelled and structured sources are exempt;
#: this floor applies only to unlabelled body text.
MIN_BODY_TEXT_IDENTIFIER_LENGTH = 4


# --------------------------------------------------------------------------- #
# Evidence.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class KeyEvidence:
    """One approved stable key, and exactly how it was proven."""

    key: str
    basis: str
    observed: str = ""
    expected: str = ""
    detail: str = ""

    @property
    def group(self) -> str:
        return KEY_GROUPS.get(self.key, self.key)

    @property
    def counts(self) -> bool:
        return self.key in APPROVED_KEYS and self.basis not in NON_COUNTING_BASES

    @property
    def authoritative(self) -> bool:
        return self.basis in AUTHORITATIVE_BASES

    def to_dict(self) -> dict:
        return {"key": self.key, "basis": self.basis, "group": self.group,
                "observed": self.observed, "expected": self.expected,
                "counts": self.counts, "authoritative": self.authoritative,
                "detail": self.detail}


@dataclass(frozen=True)
class KeyAssessment:
    """The FD-5 verdict for one navigated page."""

    outcome: str
    reason: str
    keys: Tuple[KeyEvidence, ...] = ()
    conflicts: Tuple[KeyEvidence, ...] = ()
    non_identity_signals: Tuple[str, ...] = ()

    @property
    def counting_keys(self) -> Tuple[KeyEvidence, ...]:
        return tuple(k for k in self.keys if k.counts)

    @property
    def independent_groups(self) -> Tuple[str, ...]:
        return tuple(sorted({k.group for k in self.counting_keys}))

    @property
    def has_authoritative(self) -> bool:
        return any(k.authoritative for k in self.counting_keys)

    @property
    def may_proceed(self) -> bool:
        return self.outcome in MAY_PROCEED

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome, "reason": self.reason,
            "keys": [k.to_dict() for k in self.keys],
            "conflicts": [k.to_dict() for k in self.conflicts],
            "independent_groups": list(self.independent_groups),
            "has_authoritative_key": self.has_authoritative,
            "non_identity_signals": list(self.non_identity_signals),
        }


# --------------------------------------------------------------------------- #
# Labelled-DOM extraction.
#
# "Labelled" means the markup itself names the field: a microdata ``itemprop``,
# an ``<address>`` element, or a ``tel:`` href. That is materially stronger than
# finding the same string loose in body text, where a ZIP, a room count or a
# price can collide with it.
# --------------------------------------------------------------------------- #

_ITEMPROP_RE = re.compile(
    r'<[^>]+itemprop=["\']([a-zA-Z]+)["\'][^>]*>(?:\s*)([^<]{0,200})', re.IGNORECASE)
_ITEMPROP_CONTENT_RE = re.compile(
    r'<[^>]+itemprop=["\']([a-zA-Z]+)["\'][^>]*content=["\']([^"\']{0,200})["\']',
    re.IGNORECASE)
_ADDRESS_TAG_RE = re.compile(r"<address[^>]*>(.*?)</address>", re.IGNORECASE | re.DOTALL)
_TEL_HREF_RE = re.compile(r'href=["\']tel:([^"\']+)["\']', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class LabeledFields:
    street: Tuple[str, ...] = ()
    postal: Tuple[str, ...] = ()
    phone: Tuple[str, ...] = ()
    property_code: Tuple[str, ...] = ()


def labeled_fields(dom: DomSnapshot) -> LabeledFields:
    """Field-specific values the markup itself labels. Never raises."""
    html = dom.html or ""
    street: List[str] = []
    postal: List[str] = []
    phone: List[str] = []
    code: List[str] = []

    for pattern in (_ITEMPROP_CONTENT_RE, _ITEMPROP_RE):
        for prop, value in pattern.findall(html):
            prop_l, value = prop.lower(), (value or "").strip()
            if not value:
                continue
            if prop_l == "streetaddress":
                street.append(value)
            elif prop_l == "postalcode":
                postal.append(value)
            elif prop_l in ("telephone", "phone"):
                phone.append(value)
            elif prop_l in ("propertyid", "identifier", "sku"):
                code.append(value)

    for block in _ADDRESS_TAG_RE.findall(html):
        text = _TAG_RE.sub(" ", block)
        text = " ".join(text.split())
        if text:
            street.append(text)

    phone.extend(h.strip() for h in _TEL_HREF_RE.findall(html) if h.strip())

    return LabeledFields(tuple(street), tuple(postal), tuple(phone), tuple(code))


# --------------------------------------------------------------------------- #
# Key collection.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ExpectedIdentity:
    """What the queue says this property is. Built from a QueueEntry, but kept
    as its own type so this module never needs a queue import."""

    street: str = ""
    postal_code: str = ""
    phone: str = ""
    property_code: str = ""
    name: str = ""
    city: str = ""

    @staticmethod
    def from_queue_entry(entry) -> "ExpectedIdentity":
        return ExpectedIdentity(
            street=entry.expected_address, postal_code=entry.expected_postal_code,
            phone=entry.expected_phone, property_code=entry.expected_property_code,
            name=entry.hotel_name, city=entry.expected_city)


_HOTEL_LD_TYPES = frozenset({"hotel", "lodgingbusiness", "resort", "motel",
                             "bedandbreakfast", "localbusiness"})


def _structured_from_jsonld(dom: DomSnapshot) -> ObservedIdentity:
    """Field-separated identity from the page's own JSON-LD.

    Implemented here rather than importing ``identity_check.identity_from_jsonld``
    because that module imports this one; a local read keeps the dependency
    one-way. It also means ``evaluate`` is correct when called directly, rather
    than silently ignoring structured data whenever no ``ObservedIdentity`` was
    threaded in from the caller.
    """
    blocks: List[dict] = []
    for block in dom.jsonld or ():
        if isinstance(block, dict):
            graph = block.get("@graph")
            blocks.extend(g for g in graph if isinstance(g, dict)) if isinstance(graph, list) \
                else blocks.append(block)
        elif isinstance(block, list):
            blocks.extend(b for b in block if isinstance(b, dict))

    for block in blocks:
        types = block.get("@type")
        names = [types] if isinstance(types, str) else list(types or ())
        if not any(str(t).lower() in _HOTEL_LD_TYPES for t in names):
            continue
        addr = block.get("address")
        addr = addr if isinstance(addr, dict) else {}
        return ObservedIdentity(
            name=str(block.get("name") or "").strip(),
            phone=str(block.get("telephone") or "").strip(),
            street=str(addr.get("streetAddress") or "").strip(),
            city=str(addr.get("addressLocality") or "").strip(),
            state=str(addr.get("addressRegion") or "").strip(),
            postal_code=str(addr.get("postalCode") or "").strip(),
            sources=("jsonld",))
    return ObservedIdentity()


def _field_observation_text(observations: Sequence, field: str) -> str:
    """Text from a readable field-specific evidence view, if one exists."""
    for obs in observations or ():
        if getattr(obs, "field", "") == field and getattr(obs, "readable", False):
            return getattr(obs, "text", "") or ""
    return ""


def collect_keys(dom: DomSnapshot, expected: ExpectedIdentity, *,
                 observed: Optional[ObservedIdentity] = None,
                 field_observations: Sequence = (),
                 adapter_metadata: Optional[Mapping] = None) -> Tuple[
                     Tuple[KeyEvidence, ...], Tuple[KeyEvidence, ...], Tuple[str, ...]]:
    """Return ``(agreeing_keys, conflicting_keys, non_identity_signals)``.

    Each key is emitted at the STRONGEST basis that proves it, so an address in
    JSON-LD is not downgraded because it also appears in body text.
    """
    from .evidence_completeness import FIELD_POSTAL_CODE, FIELD_PROPERTY_PHONE, FIELD_STREET

    agreeing: List[KeyEvidence] = []
    conflicting: List[KeyEvidence] = []
    signals: List[str] = []

    labeled = labeled_fields(dom)
    # Prefer what the caller observed, but never ignore the page's own JSON-LD
    # just because nothing was threaded in. Fields are merged individually: a
    # caller-supplied ObservedIdentity may carry a name from the title while
    # the address and phone live only in the structured block.
    from_page = _structured_from_jsonld(dom)
    supplied = observed or ObservedIdentity()
    structured = ObservedIdentity(
        name=supplied.name or from_page.name,
        phone=supplied.phone or from_page.phone,
        street=supplied.street or from_page.street,
        city=supplied.city or from_page.city,
        state=supplied.state or from_page.state,
        postal_code=supplied.postal_code or from_page.postal_code,
        property_code=supplied.property_code,
        sources=tuple(set(supplied.sources) | set(from_page.sources)))
    body = dom.text or ""
    meta = dict(adapter_metadata or {})

    # -- address: one key, strongest basis wins ----------------------------- #
    if expected.street:
        addr_basis = ""
        addr_value = ""
        view_text = _field_observation_text(field_observations, FIELD_STREET)
        candidates = [
            (BASIS_ADAPTER_METADATA, str(meta.get("street") or "")),
            (BASIS_STRUCTURED, structured.street),
            (BASIS_EVIDENCE_VIEW, view_text),
        ] + [(BASIS_LABELED_DOM, v) for v in labeled.street]
        for basis, value in candidates:
            if value and _addresses_agree(expected.street, value):
                addr_basis, addr_value = basis, value
                break
        if not addr_basis:
            # Body-text fallback, boundary-aware on BOTH halves: the street
            # number must stand alone as a token, and every name token must
            # too. "12" inside "2012" and "main" inside "domain" are not
            # evidence of anything.
            want = parse_street(expected.street)
            norm_body = _norm(body)
            if want.usable and token_present(want.number, norm_body) and all(
                    token_present(tok, norm_body) for tok in want.core):
                addr_basis, addr_value = BASIS_BODY_TEXT, expected.street

        if addr_basis:
            agreeing.append(KeyEvidence(
                KEY_NORMALIZED_STREET_ADDRESS, addr_basis,
                observed=addr_value, expected=expected.street))
        else:
            # An authoritative source that names a DIFFERENT street is a
            # contradiction; silence is not. A value we cannot parse into a
            # number plus a name is silence too -- it states nothing we can
            # disagree with, and calling it a conflict would fail pages that
            # merely render an address oddly.
            for basis, value in candidates:
                if value and basis in AUTHORITATIVE_BASES and parse_street(value).usable:
                    conflicting.append(KeyEvidence(
                        KEY_NORMALIZED_STREET_ADDRESS, basis,
                        observed=value, expected=expected.street,
                        detail="authoritative source names a different street "
                               "(street number or name core disagrees)"))
                    break
            else:
                # No address anywhere -- try the postal+number variant, which
                # shares the address group and therefore cannot add a second key.
                pv = ""
                for basis, value in ((BASIS_STRUCTURED, structured.postal_code),
                                     (BASIS_EVIDENCE_VIEW,
                                      _field_observation_text(field_observations,
                                                              FIELD_POSTAL_CODE))
                                     ) + tuple((BASIS_LABELED_DOM, v) for v in labeled.postal):
                    if value and expected.postal_code and value.strip() == expected.postal_code.strip():
                        num = _street_number(expected.street)
                        if num and token_present(num, _norm(body)):
                            pv = value
                            agreeing.append(KeyEvidence(
                                KEY_POSTAL_PLUS_STREET_NUMBER, basis,
                                observed=value, expected=expected.postal_code))
                            break
                if not pv:
                    signals.append("street_address_absent")

    # -- phone -------------------------------------------------------------- #
    if expected.phone:
        want = _phone_tail(expected.phone)
        found_basis = found_value = ""
        view_text = _field_observation_text(field_observations, FIELD_PROPERTY_PHONE)
        candidates = [
            (BASIS_ADAPTER_METADATA, str(meta.get("phone") or "")),
            (BASIS_STRUCTURED, structured.phone),
            (BASIS_EVIDENCE_VIEW, view_text),
        ] + [(BASIS_LABELED_DOM, v) for v in labeled.phone]
        conflict_seen = None
        for basis, value in candidates:
            if not value:
                continue
            if _phone_tail(value) == want:
                found_basis, found_value = basis, value
                break
            if basis in AUTHORITATIVE_BASES and conflict_seen is None and _digits(value):
                conflict_seen = (basis, value)
        if not found_basis and want and want in phone_runs(body):
            found_basis, found_value = BASIS_BODY_TEXT, expected.phone

        if found_basis:
            agreeing.append(KeyEvidence(KEY_PROPERTY_PHONE, found_basis,
                                        observed=found_value, expected=expected.phone))
        elif conflict_seen:
            conflicting.append(KeyEvidence(
                KEY_PROPERTY_PHONE, conflict_seen[0], observed=conflict_seen[1],
                expected=expected.phone,
                detail="authoritative source names a different phone"))

    # -- property identifier ------------------------------------------------ #
    # Counted ONLY from page content or adapter metadata. A code read out of the
    # requested URL proves nothing about the page that URL returned.
    if expected.property_code:
        want = expected.property_code.strip().lower()
        basis = value = ""
        # ``official_property_id`` is reserved for a source that NAMES the field
        # (an itemprop/structured identifier). Anything else proving the same
        # brand-assigned handle is a stable_chain_property_identifier. Both share
        # one independence group, so this changes provenance, never the count.
        key = KEY_STABLE_CHAIN_IDENTIFIER
        if want and str(meta.get("property_code") or "").strip().lower() == want:
            basis, value = BASIS_ADAPTER_METADATA, str(meta.get("property_code"))
        else:
            for v in labeled.property_code:
                if v.strip().lower() == want:
                    basis, value, key = BASIS_LABELED_DOM, v, KEY_OFFICIAL_PROPERTY_ID
                    break
            else:
                # Boundary-aware, and long enough to not be a coincidence:
                # "chi" occurs inside "chicago", which is not a citation.
                if (len(want) >= MIN_BODY_TEXT_IDENTIFIER_LENGTH
                        and token_present(want, _norm(body))):
                    basis, value = BASIS_BODY_TEXT, expected.property_code
                elif want and token_present(want, (dom.canonical_url or "").lower()):
                    # The page's OWN canonical link -- page-published, so not
                    # circular like the URL we requested, but not rendered
                    # property-specific evidence either, so it is weak
                    # (founder decision 5).
                    basis, value = BASIS_CANONICAL_URL, dom.canonical_url
        if basis:
            agreeing.append(KeyEvidence(key, basis, observed=value,
                                        expected=expected.property_code))
        else:
            signals.append("property_code_not_in_page_content")

    # -- never-identity signals, recorded only ------------------------------ #
    if structured.name or dom.title:
        signals.append("name")
    if structured.city or (expected.city and expected.city.lower() in body.lower()):
        signals.append("city")
    if dom.title:
        signals.append("page_title")

    return (tuple(agreeing), tuple(conflicting), tuple(sorted(set(signals))))


# --------------------------------------------------------------------------- #
# The verdict.
# --------------------------------------------------------------------------- #

def assess_keys(agreeing: Sequence[KeyEvidence], conflicting: Sequence[KeyEvidence],
                signals: Sequence[str] = ()) -> KeyAssessment:
    """Apply FD-5 to collected evidence. Fails closed at every branch."""
    counting = [k for k in agreeing if k.counts]
    groups = sorted({k.group for k in counting})

    if conflicting:
        return KeyAssessment(
            IDENTITY_FAILED,
            "stable key(s) contradicted: %s" % ", ".join(
                sorted({k.key for k in conflicting})),
            keys=tuple(agreeing), conflicts=tuple(conflicting),
            non_identity_signals=tuple(signals))

    if len(groups) < MINIMUM_INDEPENDENT_KEYS:
        if counting:
            detail = ("only %d independent stable key(s) (%s); FD-5 requires %d"
                      % (len(groups), ", ".join(groups), MINIMUM_INDEPENDENT_KEYS))
        elif signals:
            detail = ("no approved stable key; only non-identity signals (%s) -- "
                      "name, city and page title never establish identity"
                      % ", ".join(signals))
        else:
            detail = "no approved stable key was proven"
        return KeyAssessment(IDENTITY_INCOMPLETE, detail, keys=tuple(agreeing),
                             non_identity_signals=tuple(signals))

    if not any(k.authoritative for k in counting):
        return KeyAssessment(
            IDENTITY_INCOMPLETE,
            "%d independent keys, but none from an authoritative field-specific "
            "source; unlabelled body text alone cannot confirm identity" % len(groups),
            keys=tuple(agreeing), non_identity_signals=tuple(signals))

    return KeyAssessment(
        IDENTITY_CONFIRMED,
        "%d independent stable keys (%s), at least one authoritative"
        % (len(groups), ", ".join(groups)),
        keys=tuple(agreeing), non_identity_signals=tuple(signals))


def evaluate(dom: DomSnapshot, expected: ExpectedIdentity, *,
             observed: Optional[ObservedIdentity] = None,
             field_observations: Sequence = (),
             adapter_metadata: Optional[Mapping] = None) -> KeyAssessment:
    """Collect and judge in one call."""
    agreeing, conflicting, signals = collect_keys(
        dom, expected, observed=observed, field_observations=field_observations,
        adapter_metadata=adapter_metadata)
    return assess_keys(agreeing, conflicting, signals)

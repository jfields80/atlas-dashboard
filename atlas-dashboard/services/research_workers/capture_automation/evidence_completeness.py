"""PTF-CAPTURE-003E -- do not ask a human to attest an incomplete package.

The affirmation a human signs says they *saw* the hotel's identity on the
official page. Until now nothing checked that the screenshots put in front of
them could actually show it. Aloft Columbus University District is the concrete
case: its policy screenshot proves the pet policy and nothing else -- no
address, no phone -- so the operator affirming "address confirmed" would have
been affirming something the evidence in hand did not contain. The gate existed
in the sentence, not in the package.

This module makes the package prove each field before the prompt is presented:

  * a field is proven only by text that is PAINTED and IN FRAME in a validated
    screenshot -- DOM text that is display:none, zero-area, or scrolled out of
    the captured viewport proves nothing, because the human cannot read it;
  * fields may be spread across as many views as it takes, since a tall page
    cannot fit its name, address and policy in one 1000px frame;
  * a central-reservations number is not the property's phone, and is never
    accepted as one;
  * anything missing, unreadable or self-contradictory fails CLOSED -- the
    prompt is withheld and the missing fields are named, so the capture layer
    can go get them.

Pure and offline. It inspects view records and PNG bytes; it never launches a
browser, and it never attests, approves, promotes or publishes.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field as dc_field
from typing import Dict, Mapping, Optional, Sequence, Tuple

from .capture_writer import png_dimensions, png_is_complete

#: Every field the operator is asked to affirm, or that the policy read depends
#: on. Nothing here is optional: an attestation that cannot show the address is
#: not a weaker attestation, it is a different claim.
FIELD_HOTEL_NAME = "hotel_name"
FIELD_STREET = "street_address"
FIELD_CITY = "city"
FIELD_STATE = "state"
FIELD_POSTAL_CODE = "postal_code"
FIELD_PROPERTY_PHONE = "property_phone"
FIELD_POLICY_TEXT = "pet_policy_text"

REQUIRED_FIELDS = (
    FIELD_HOTEL_NAME, FIELD_STREET, FIELD_CITY, FIELD_STATE, FIELD_POSTAL_CODE,
    FIELD_PROPERTY_PHONE, FIELD_POLICY_TEXT,
)

#: North American toll-free area codes. A hotel page shows these for brand
#: reservations lines ("call 1-888-236-2427 to book"), never for the front
#: desk. Treating one as the property phone would record a call centre as the
#: property's own contact, which is exactly the identity blur the affirmation
#: is meant to prevent.
TOLL_FREE_AREA_CODES = ("800", "833", "844", "855", "866", "877", "888")

PHONE_PROPERTY = "PROPERTY"
PHONE_CENTRAL_RESERVATIONS = "CENTRAL_RESERVATIONS"
PHONE_UNKNOWN = "UNKNOWN"

#: Wording that marks a number as a booking/reservations line even when it is
#: not toll-free (some brands publish a local-rate reservations number).
_CENTRAL_CONTEXT = (
    "reservation", "reservations", "central", "book by phone", "call to book",
    "customer care", "customer service", "member support", "rewards",
)

#: Wording that marks a number as the property's own line.
_PROPERTY_CONTEXT = ("front desk", "hotel phone", "property phone", "tel", "call the hotel")


class EvidenceError(ValueError):
    """A view record that cannot be trusted as evidence."""


class EvidenceIncompleteError(RuntimeError):
    """Raised instead of presenting an attestation prompt. Carries the report."""

    def __init__(self, report: "EvidenceReport"):
        super().__init__(report.summary_line())
        self.report = report


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def national_digits(value: str) -> str:
    """The 10 NANP digits, dropping a leading country code."""
    d = _digits(value)
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return d


def classify_phone(text: str, *, context: str = "") -> str:
    """PROPERTY / CENTRAL_RESERVATIONS / UNKNOWN for one observed number.

    Context is the surrounding visible words. It is consulted BEFORE the area
    code so an explicitly labelled reservations line is never promoted to a
    property phone just because it happens to be local-rate.
    """
    d = national_digits(text)
    ctx = (context or "").lower()
    if any(w in ctx for w in _CENTRAL_CONTEXT):
        return PHONE_CENTRAL_RESERVATIONS
    if len(d) != 10:
        return PHONE_UNKNOWN
    if d[:3] in TOLL_FREE_AREA_CODES:
        return PHONE_CENTRAL_RESERVATIONS
    if any(w in ctx for w in _PROPERTY_CONTEXT):
        return PHONE_PROPERTY
    # A complete geographic NANP number on the property's own page, with
    # nothing marking it as a booking line.
    return PHONE_PROPERTY


#: US state names as they appear on brand pages, keyed by the postal code the
#: seed carries. Marriott renders "Ohio", the seed says "OH", and a needle of
#: "OH" would match the "OH" inside "OHIO" and inside dozens of unrelated
#: words -- so the expansion is explicit rather than substring-guessed.
_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia",
}

#: Street-suffix expansions. The seed abbreviates ("Olentangy River Rd"); the
#: page spells it out ("Olentangy River Road"). Hunting only the seed's form
#: found nothing and would have reported a present address as missing.
_STREET_SUFFIXES = (
    ("rd", "Road"), ("st", "Street"), ("ave", "Avenue"), ("blvd", "Boulevard"),
    ("dr", "Drive"), ("ln", "Lane"), ("pkwy", "Parkway"), ("cir", "Circle"),
    ("ct", "Court"), ("hwy", "Highway"), ("pl", "Place"), ("ter", "Terrace"),
    ("sq", "Square"), ("trl", "Trail"), ("way", "Way"),
)


#: suffix token (either spelling) -> its canonical long form
_SUFFIX_CANON = {}
for _short, _long in _STREET_SUFFIXES:
    _SUFFIX_CANON[_short] = _long.lower()
    _SUFFIX_CANON[_long.lower()] = _long.lower()


def street_line(value: str) -> str:
    """Just the street line, dropping any trailing city/state/ZIP.

    The seed flattens the whole address into one field -- "1295 Olentangy
    River Rd Columbus OH 43212" -- while the page prints the street on its own
    line. Comparing the flattened form against the page found nothing and
    reported a plainly visible address as missing.
    """
    tokens = [t for t in re.split(r"[\s,]+", (value or "").strip()) if t]
    out = []
    for tok in tokens:
        out.append(tok)
        if len(out) > 1 and tok.lower().rstrip(".") in _SUFFIX_CANON:
            break
    return " ".join(out)


#: Leading directional, either spelling. USPS treats these as the same
#: address; the seed and the brand page routinely disagree about which to
#: write, and until PTF-WYNDHAM that disagreement read as a contradiction:
#: the seed's "7474 N High St" was called missing from a page plainly
#: printing "7474 North High St".
_DIRECTIONALS = (
    ("n", "North"), ("s", "South"), ("e", "East"), ("w", "West"),
    ("ne", "Northeast"), ("nw", "Northwest"),
    ("se", "Southeast"), ("sw", "Southwest"),
)

_DIRECTIONAL_CANON = {}
for _short_d, _long_d in _DIRECTIONALS:
    _DIRECTIONAL_CANON[_short_d] = _long_d
    _DIRECTIONAL_CANON[_long_d.lower()] = _long_d


def _directional_swaps(value: str) -> Tuple[str, ...]:
    """The same street line with a leading directional written the other way.

    Positional on purpose, and narrowly so: only the token directly after the
    house number is considered, and only when it is a directional in its
    entirety. A blind substring swap would rewrite "Westerville" to
    "Wersterville" and "Newark" to "Northewark" -- which is why the rule is
    anchored to a token position rather than applied to text.
    """
    tokens = value.split()
    if len(tokens) < 3:                 # number + directional + street name
        return ()
    if not re.match(r"^\d", tokens[0]):  # not a house-numbered street line
        return ()
    raw = tokens[1].rstrip(".").lower()
    canon = _DIRECTIONAL_CANON.get(raw)
    if canon is None:
        return ()
    short = next(s for s, l in _DIRECTIONALS if l == canon)
    other = short.upper() if raw == canon.lower() else canon
    return (" ".join([tokens[0], other] + tokens[2:]),)


def street_variants(street: str) -> Tuple[str, ...]:
    """The seed's street, plus the spelled-out suffix a brand page tends to use."""
    s = street_line(street)
    if not s:
        return ()
    out = [s]
    m = re.match(r"^(.*?)[\s,]+([A-Za-z]+)\.?$", s)
    if m:
        head, suffix = m.group(1), m.group(2).lower().rstrip(".")
        for short, long in _STREET_SUFFIXES:
            if suffix == short and long.lower() != suffix:
                out.append("%s %s" % (head, long))
            elif suffix == long.lower():
                out.append("%s %s" % (head, short.upper()))
    # Directional and suffix vary independently -- "N High St" can meet
    # "North High Street" -- so every suffix form gets both directionals.
    out.extend(alt for v in list(out) for alt in _directional_swaps(v))
    # de-duplicate, preserve order
    seen, uniq = set(), []
    for v in out:
        if v.lower() not in seen:
            seen.add(v.lower())
            uniq.append(v)
    return tuple(uniq)


def phone_variants(phone: str) -> Tuple[str, ...]:
    """Every rendering of the same 10 digits a brand page is likely to paint."""
    d = national_digits(phone)
    if len(d) != 10:
        return (phone,) if phone else ()
    a, b, c = d[:3], d[3:6], d[6:]
    return ("%s-%s-%s" % (a, b, c), "+1 %s-%s-%s" % (a, b, c),
            "1-%s-%s-%s" % (a, b, c), "(%s) %s-%s" % (a, b, c),
            "+1%s%s%s" % (a, b, c))


def state_variants(code: str) -> Tuple[str, ...]:
    """The postal code and the state name a page is likely to spell out."""
    code = (code or "").strip()
    full = _STATE_NAMES.get(code.upper(), "")
    return tuple(x for x in (full, code) if x)


def name_variants(name: str) -> Tuple[str, ...]:
    """The seed name, plus its distinctive tail.

    Brands insert their own line -- Marriott renders "Aloft BY MARRIOTT
    Columbus University District" -- so the full seed string may never appear
    verbatim beside the address. Refusing that as a contradiction would reject
    the property's own page as evidence about itself.
    """
    name = (name or "").strip()
    if not name:
        return ()
    bits = name.split()
    out = [name]
    if len(bits) > 3:
        out.append(" ".join(bits[-3:]))
    return tuple(dict.fromkeys(out))


#: field -> how to expand what the queue expects into what a page may paint.
_VARIANTS = {
    FIELD_STREET: street_variants,
    FIELD_STATE: state_variants,
    FIELD_HOTEL_NAME: name_variants,
}


@dataclass(frozen=True)
class FieldObservation:
    """One field, as it was actually painted in one screenshot.

    ``visible`` is the DOM's answer (the element paints at all); ``in_frame``
    is the screenshot's answer (it fell inside the captured viewport). Both
    must be true, and they are recorded separately so a report can say which
    one failed.
    """
    field: str
    text: str
    visible: bool = True
    in_frame: bool = True
    context: str = ""
    box: Mapping[str, float] = dc_field(default_factory=dict)

    @property
    def readable(self) -> bool:
        area = float(self.box.get("width") or 0) * float(self.box.get("height") or 0)
        if self.box and area <= 0:
            return False
        return bool(self.visible and self.in_frame and (self.text or "").strip())

    def to_dict(self) -> dict:
        return {"field": self.field, "text": self.text, "visible": self.visible,
                "in_frame": self.in_frame, "context": self.context,
                "box": dict(self.box or {})}


@dataclass(frozen=True)
class EvidenceView:
    """A screenshot offered as evidence, plus what it visibly shows."""
    png_path: str
    png_sha256: str
    png_bytes: int
    png_width: int
    png_height: int
    page_url: str
    captured_at: str
    observations: Tuple[FieldObservation, ...] = ()

    @property
    def name(self) -> str:
        return pathlib.Path(self.png_path).name


def view_from_sidecar(sidecar: Mapping, *, directory=None,
                      observations: Sequence[FieldObservation] = ()) -> EvidenceView:
    """Build a view from a ``.view.json`` sidecar written by the capture layer."""
    png = sidecar.get("png_file") or sidecar.get("png_path") or ""
    path = str(pathlib.Path(directory) / png) if directory else png
    return EvidenceView(
        png_path=path,
        png_sha256=str(sidecar.get("png_sha256") or ""),
        png_bytes=int(sidecar.get("png_bytes") or 0),
        png_width=int(sidecar.get("png_width") or 0),
        png_height=int(sidecar.get("png_height") or 0),
        page_url=str(sidecar.get("final_url") or sidecar.get("page_url") or ""),
        captured_at=str(sidecar.get("captured_at") or ""),
        observations=tuple(observations),
    )


# --------------------------------------------------------------------------- #
# View-level validation: is this image what it says it is?
# --------------------------------------------------------------------------- #

def _same_official_page(view_url: str, official_url: str) -> bool:
    """Same host and same path, ignoring query, fragment and a trailing slash.

    A view of a *different* page on the same host proves nothing about this
    property, so the path must match too -- host equality alone would accept a
    brand landing page as evidence for one hotel.
    """
    from urllib.parse import urlsplit

    a, b = urlsplit(view_url or ""), urlsplit(official_url or "")
    if not a.hostname or not b.hostname:
        return False
    return (a.hostname.lower() == b.hostname.lower()
            and a.path.rstrip("/").lower() == b.path.rstrip("/").lower())


def validate_view(view: EvidenceView, *, official_url: str,
                  read_bytes=None) -> Tuple[str, ...]:
    """Problems with one view. Empty tuple means the image can be trusted.

    Reads the PNG off disk and re-derives its digest and dimensions rather than
    believing the sidecar: a sidecar is a claim about a file, and the file is
    the evidence.
    """
    problems = []
    if not _same_official_page(view.page_url, official_url):
        problems.append("view_url_is_not_the_official_page:%s" % (view.page_url or "(none)"))
    if not (view.captured_at or "").strip():
        problems.append("view_missing_captured_at")

    reader = read_bytes or (lambda p: pathlib.Path(p).read_bytes())
    try:
        data = reader(view.png_path)
    except OSError as exc:
        return tuple(problems + ["view_png_unreadable:%s" % exc.__class__.__name__])

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        problems.append("view_png_not_a_png")
        return tuple(problems)
    if not png_is_complete(data):
        problems.append("view_png_truncated_no_iend")
    import hashlib
    sha = hashlib.sha256(data).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", view.png_sha256 or ""):
        problems.append("view_sha256_not_a_digest")
    elif sha != view.png_sha256:
        problems.append("view_sha256_mismatch")
    if view.png_bytes and view.png_bytes != len(data):
        problems.append("view_byte_length_mismatch")
    try:
        w, h = png_dimensions(data)
    except Exception:                                    # noqa: BLE001
        problems.append("view_png_dimensions_unreadable")
    else:
        if w <= 0 or h <= 0:
            problems.append("view_png_zero_dimensions")
        if (view.png_width, view.png_height) != (0, 0) and (view.png_width, view.png_height) != (w, h):
            problems.append("view_dimensions_mismatch:%dx%d_vs_%dx%d"
                            % (view.png_width, view.png_height, w, h))
    return tuple(problems)


# --------------------------------------------------------------------------- #
# The completeness report.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class EvidenceReport:
    complete: bool
    proven: Mapping[str, Tuple[str, str]]      # field -> (view name, quote)
    missing: Tuple[str, ...]
    ambiguous: Tuple[str, ...]
    problems: Tuple[str, ...]
    rejected: Tuple[str, ...]                  # field -> why an observation did not count
    phones: Tuple[Tuple[str, str, str], ...] = ()   # (view, text, classification)

    def summary_line(self) -> str:
        if self.complete:
            return "evidence complete: all %d required fields visibly proven" % len(REQUIRED_FIELDS)
        bits = []
        if self.missing:
            bits.append("missing=%s" % ",".join(self.missing))
        if self.ambiguous:
            bits.append("ambiguous=%s" % ",".join(self.ambiguous))
        if self.problems:
            bits.append("problems=%s" % ",".join(self.problems))
        return "evidence INCOMPLETE: " + "; ".join(bits or ["no usable views"])

    def render(self) -> str:
        """The concise review package: which screenshot proves which field."""
        lines = ["REVIEW PACKAGE -- what the operator can actually see", ""]
        for f in REQUIRED_FIELDS:
            got = self.proven.get(f)
            if got:
                lines.append("  %-15s PROVEN  %s" % (f, got[0]))
                lines.append("  %-15s         %r" % ("", got[1][:110]))
            else:
                why = "AMBIGUOUS" if f in self.ambiguous else "MISSING"
                lines.append("  %-15s %s" % (f, why))
        if self.phones:
            lines.append("")
            lines.append("  phone numbers seen:")
            shown = []
            for view, text, kind in self.phones:
                if (text, kind) in shown:
                    continue
                shown.append((text, kind))
                lines.append("     %-22s %-22s %s" % (text, kind, view))
        if self.rejected:
            lines.append("")
            lines.append("  not counted as evidence:")
            # One line per distinct reason. Several needle variants can match
            # several elements, so the raw list repeats the same finding a
            # dozen times and buries the one that matters.
            seen = []
            for r in self.rejected:
                if r not in seen:
                    seen.append(r)
            for r in seen:
                lines.append("     %s" % r)
        if self.problems:
            lines.append("")
            lines.append("  view problems:")
            for p in self.problems:
                lines.append("     %s" % p)
        lines.append("")
        lines.append("  " + self.summary_line())
        return "\n".join(lines)


def _expected_matches(field: str, text: str, expected: Mapping[str, str]) -> bool:
    """Does an observation agree with what the queue expects for this field?

    Compared against every rendering the expected value can legitimately take,
    not just the seed's exact string. The seed writes "1295 Olentangy River
    Rd"; Marriott paints "1295 Olentangy River Road". A literal comparison
    calls that a contradiction and rejects the property's own page as evidence
    about itself -- which is not caution, it is a false negative that sends the
    capture layer hunting for something already on screen.
    """
    want = (expected.get(field) or "").strip()
    if not want:
        return True                       # nothing to contradict
    if field == FIELD_PROPERTY_PHONE:
        return national_digits(text) == national_digits(want)
    haystack = (text or "").lower()
    builder = _VARIANTS.get(field)
    candidates = builder(want) if builder else (want,)
    for candidate in candidates:
        if candidate.lower() in haystack:
            return True
    if field == FIELD_HOTEL_NAME:
        # Every word of the expected name must appear in the observed one. A
        # brand may ADD words ("Inn & Suites by Wyndham", "by Marriott"); a
        # different property drops the distinctive ones. Substring matching
        # cannot survive a brand line inserted mid-name, and a short tail
        # ("Columbus Airport") is not distinctive enough to be safe.
        return _name_tokens(want) <= _name_tokens(text)
    return False


def _name_tokens(text: str) -> frozenset:
    """Lowercase word set, punctuation discarded.

    "West-Hilliard" and "West - Hilliard" reduce to the same two tokens, which
    is the point: hyphen spacing is typesetting, not identity.
    """
    return frozenset(w for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if w)


def assess_evidence(views: Sequence[EvidenceView], *, official_url: str,
                    expected: Optional[Mapping[str, str]] = None,
                    read_bytes=None) -> EvidenceReport:
    """Can a human be shown this package and asked to affirm it?

    Fails closed on every axis: an unvalidated view contributes nothing, an
    unreadable observation contributes nothing, and two observations that
    disagree about the same field make it ambiguous rather than picking one.
    """
    expected = dict(expected or {})
    problems: list = []
    rejected: list = []
    usable: list = []

    for v in views:
        bad = validate_view(v, official_url=official_url, read_bytes=read_bytes)
        if bad:
            problems.extend("%s: %s" % (v.name, b) for b in bad)
            continue                       # an image we cannot trust proves nothing
        usable.append(v)

    # Collect every readable observation per field, remembering which view.
    seen: Dict[str, list] = {f: [] for f in REQUIRED_FIELDS}
    phones: list = []
    for v in usable:
        for obs in v.observations:
            if obs.field not in seen:
                rejected.append("%s: unknown field %r" % (v.name, obs.field))
                continue
            if not obs.readable:
                why = ("hidden_in_dom" if not obs.visible
                       else "out_of_frame" if not obs.in_frame else "empty_or_zero_area")
                rejected.append("%s: %s %s" % (v.name, obs.field, why))
                continue
            if obs.field == FIELD_PROPERTY_PHONE:
                kind = classify_phone(obs.text, context=obs.context)
                phones.append((v.name, obs.text.strip(), kind))
                if kind != PHONE_PROPERTY:
                    rejected.append("%s: %s is a %s number, not the property line"
                                    % (v.name, obs.text.strip(), kind.lower().replace("_", " ")))
                    continue
            if not _expected_matches(obs.field, obs.text, expected):
                rejected.append("%s: %s %r contradicts expected %r"
                                % (v.name, obs.field, obs.text.strip(),
                                   expected.get(obs.field)))
                continue
            seen[obs.field].append((v.name, obs.text.strip()))

    proven: Dict[str, Tuple[str, str]] = {}
    missing: list = []
    ambiguous: list = []
    for f in REQUIRED_FIELDS:
        hits = seen[f]
        if not hits:
            missing.append(f)
            continue
        if f == FIELD_PROPERTY_PHONE:
            distinct = {national_digits(t) for _, t in hits}
        elif (expected.get(f) or "").strip():
            # Every surviving observation already matched the expected value --
            # contradictions were rejected above -- so several of them agree by
            # construction. They differ only because the planner hunts more
            # than one rendering of the same fact ("Rd"/"Road", "OH"/"Ohio",
            # the full name and its tail). Comparing those to each other made
            # thoroughness look like disagreement.
            distinct = {" ".join((expected[f] or "").lower().split())}
        else:
            distinct = {" ".join((t or "").lower().split()) for _, t in hits}
        if len(distinct) > 1:
            ambiguous.append(f)
            continue
        proven[f] = hits[0]

    complete = not missing and not ambiguous and bool(usable)
    return EvidenceReport(complete=complete, proven=proven,
                          missing=tuple(missing), ambiguous=tuple(ambiguous),
                          problems=tuple(problems), rejected=tuple(rejected),
                          phones=tuple(phones))


def require_complete_evidence(views: Sequence[EvidenceView], *, official_url: str,
                              expected: Optional[Mapping[str, str]] = None,
                              read_bytes=None) -> EvidenceReport:
    """Gate an attestation prompt. Raises rather than asking a human to guess."""
    report = assess_evidence(views, official_url=official_url, expected=expected,
                             read_bytes=read_bytes)
    if not report.complete:
        raise EvidenceIncompleteError(report)
    return report


def fields_to_recapture(report: EvidenceReport) -> Tuple[str, ...]:
    """What an additional view must show for the package to become complete.

    Ambiguous fields are included: a second look is how a contradiction gets
    resolved, and resolving it by choosing between two readings is precisely
    what this gate refuses to do.
    """
    return tuple(f for f in REQUIRED_FIELDS
                 if f in report.missing or f in report.ambiguous)

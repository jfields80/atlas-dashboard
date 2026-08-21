"""What a Marriott property page looks like, and how to read one honestly.

Pure and deterministic: no network, no clock, no file reads. Everything here
takes bytes that a browser already produced and returns a judgement about them,
which is what makes the risky half of this pilot testable without spending a
Bright Data session.

WHY A BOUNDED LOCATOR AND NOT A KEYWORD SWEEP
---------------------------------------------
The single-page proof collected every line of the page containing "pet", "dog",
"cat" or "weight". It returned, among the real policy, this:

    Fitness center with cardiovascular and weight equipment

A keyword sweep does not find a policy; it finds a word. Worse, its output
looks like a quote, and a quote is what publication-grade evidence is made of.
So extraction here is BOUNDED to the page's own pet-policy container -- located
by structure, not by vocabulary -- and the smallest contiguous block holding
both the heading and the wording is the only text this module will read.

Marriott renders that container as::

    <div class="d-flex align-items-start">
      <span class="icon-pet-friendly ..."></span>
      <div class="t-font-s">
        <div class="pb-2 t-font-s">Pet Policy</div>
        <div class="t-font-xs"> ...the wording... </div>
      </div>
    </div>

so the primary locator is the parent of the element whose own text is exactly
"Pet Policy". That is template-shaped rather than icon-shaped, which matters:
the icon class is ``icon-pet-friendly`` and a property that does not take pets
has no reason to keep it.

WHAT THIS MODULE REFUSES TO DECIDE
----------------------------------
It reads labels. It does not interpret them.

* ``Maximum Pet Weight: 50.0lbs`` yields a weight VALUE and no OPERATOR. The
  corpus rule is that defaulting a comparison either way is a guest-visible
  error -- ``lte`` admits an eighty-pound dog to a property that wrote "under
  eighty pounds", ``lt`` turns away one the hotel accepts -- so the comparison
  is left ABSENT and reported as a deliberate non-inference.
* No ``fee_scope`` is ever emitted. Marriott's rows do not say whether a fee is
  per room or per pet, and unknown is absence.
* A recurring charge stated as ``per night`` in one place and ``per day`` in
  another is NOT normalised. ``per_day != per_night`` is frozen, the two
  spellings are a real contradiction on one first-party surface, and this
  module preserves it as one.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import outcomes as O          # noqa: E402
from scripts.pettripfinder.contracts import enums                   # noqa: E402
from scripts.pettripfinder.discovery.property_identity import (     # noqa: E402
    street_identity,
)

BRAND = "marriott"

#: The property's own first-party host. Anything else is not this surface.
FIRST_PARTY_HOSTS: Tuple[str, ...] = ("www.marriott.com", "marriott.com")

#: Marriott property URLs carry a five-character property code as the first
#: token of the hotel slug: ``/hotels/dtwad-ac-hotel-ann-arbor-downtown/``.
#: The code is the strongest identity signal on the page, and the reason the
#: identity gate does not rest on the name: ``cmhcees``, ``cmhates`` and
#: ``cmheses`` are three different hotels and no two share a code.
_PROPERTY_CODE_RE = re.compile(r"/hotels/([a-z0-9]{4,7})-", re.IGNORECASE)

#: The bounded pet-policy locators, tried in order. Each is (id, selector).
#: The first two are structural (heading -> parent), one per template Marriott
#: actually serves; the last two are the icon block, kept as fallbacks for
#: template drift.
#:
#: MARRIOTT SERVES TWO TEMPLATES AND THE OLD LIST ONLY SAW ONE
#: -----------------------------------------------------------
#: PTF-MARRIOTT-ACCORDION-LOCATOR-HARDENING-021 measured all seventeen
#: remaining Milwaukee Marriott properties. Fourteen render the policy beside
#: an ``icon-pet-friendly`` span under a ``<div>Pet Policy</div>`` heading,
#: which ``pet_policy_heading_parent`` binds exactly. The other three render it
#: into an accordion panel headed by ``<b>Pet Policy</b>`` and carry NO
#: ``icon-pet`` span at all, so every locator in the old list missed them: the
#: first requires a ``div``, and the other two require the icon.
#:
#: When they all miss, the generic signal walk runs instead, and on Marriott it
#: tends to land on the FAQ. That is not a harmless substitution. The Trade,
#: Autograph Collection stored "A non-refundable pet fee of $125.00 per stay
#: applies" from the FAQ while its own Pet Policy panel says "Pet deposit
#: starts at $125 (may increase for suites) + $20 daily pet fee" -- the record
#: omitted a recurring charge while looking complete.
#:
#: ``pet_policy_accordion_panel`` binds the accordion heading to its own panel.
#: The heading text must be exactly "Pet Policy", which is what keeps the
#: sibling panels on the same page -- Parking, Valet, Policies and Payments,
#: Services -- out of the block, and what keeps the JavaScript i18n dictionary
#: entry ``"hws.petPolicy":"Pet Policy"`` out of it too: that string lives in a
#: ``<script>``, and an element selector never reaches it.
#:
#: Deliberately NOT broadened to ``strong``/``h3``/``h4``. Those forms appear on
#: no captured Marriott page, and this list's standing rule is that a selector
#: is discovered by reading a persisted artifact rather than by guessing. Two
#: templates are measured, so two structural locators exist.
POLICY_LOCATORS: Tuple[Tuple[str, str], ...] = (
    ("pet_policy_heading_parent",
     "xpath=//div[normalize-space(text())='Pet Policy']/parent::*"),
    ("pet_policy_accordion_panel",
     "xpath=//b[normalize-space(text())='Pet Policy']/parent::*"),
    ("hotel_info_pet_icon_block",
     "css=div.hotel-info__column div.d-flex.align-items-start"
     ":has(span[class*='icon-pet'])"),
    ("any_pet_icon_block",
     "css=div.d-flex.align-items-start:has(span[class*='icon-pet'])"),
)

#: The two structural locators as bare XPath. The live walk hands the prefixed
#: forms above to Playwright; a differential over persisted documents cannot
#: start a browser, so the same expressions are named here in the one form lxml
#: evaluates. Derived from POLICY_LOCATORS rather than retyped, so the offline
#: evaluation and the live one cannot drift apart.
STRUCTURAL_XPATHS: Tuple[Tuple[str, str], ...] = tuple(
    (locator_id, selector[len("xpath="):])
    for locator_id, selector in POLICY_LOCATORS
    if selector.startswith("xpath="))

POLICY_HEADING = "Pet Policy"

#: The hotel-information section the policy block lives in. Scrolled into view
#: before the policy screenshot so the capture is of a rendered surface rather
#: than of a lazily-mounted placeholder.
HOTEL_INFO_LOCATOR = "css=div.hotel-info__column"

#: Phrases that mean the origin or an intermediary refused us. Kept tight on
#: purpose: a loose marker like "reference #" appears in ordinary page chrome,
#: and a false ACCESS_DENIED would discard a good capture.
DENIAL_MARKERS: Tuple[str, ...] = (
    "access denied",
    "request unsuccessful",
    "you don't have permission to access",
    "pardon our interruption",
    "verify you are a human",
    "are you a robot",
    "unusual traffic from your",
    "please enable javascript and cookies to continue",
    "request blocked",
    "attention required! | cloudflare",
)

#: A rendered Marriott overview page runs to many thousands of characters. The
#: shells observed during the proof carried a correct title and a body under a
#: few hundred. 1000 sits well clear of both.
MIN_HYDRATED_BODY_CHARS = 1000

#: Below this there is effectively nothing on the page at all.
MIN_ANY_BODY_CHARS = 40

_WHITESPACE_RE = re.compile(r"\s+")


def collapse(text: str) -> str:
    """Whitespace-collapsed text.

    Every quote this module produces is a substring of the collapsed block, and
    ``contracts.evidence.quote_is_contiguous`` collapses both sides before
    comparing, so a quote taken here survives the contiguity check against the
    saved page text. Nothing else is normalised: altering the words is the
    thing the contiguity rule exists to catch.
    """
    return _WHITESPACE_RE.sub(" ", text or "").strip()


def name_tokens(name: str) -> frozenset:
    """Comparable tokens for a hotel name, accents folded.

    A capture-time PRE-gate only. The authoritative identity rule is M10 in
    ``policy_membrane``, which is applied to every observation this pilot
    produces; this exists so a capture that is obviously the wrong property is
    rejected before artifacts are written rather than after. Folding matches
    M10's own reasoning: an unfolded diacritic shatters into one-character
    tokens that are free to appear inside unrelated hotel names.
    """
    text = (name or "").lower().replace("&", " and ")
    text = "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))
    return frozenset(t for t in re.split(r"[^a-z0-9]+", text) if t)


def host_of(url: str) -> str:
    return re.sub(r"^https?://", "", url or "").split("/")[0].lower()


def is_first_party(url: str) -> bool:
    return host_of(url) in FIRST_PARTY_HOSTS


def property_code(url: str) -> str:
    """The five-ish character property code from a Marriott URL, lowercased."""
    match = _PROPERTY_CODE_RE.search(url or "")
    return match.group(1).lower() if match else ""


# --------------------------------------------------------------------------- #
# Identity, read from the page's own structured data.
# --------------------------------------------------------------------------- #

_LD_JSON_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL)
_CANONICAL_RE = re.compile(
    r"<link[^>]*rel=[\"']canonical[\"'][^>]*href=[\"']([^\"']+)[\"']",
    re.IGNORECASE)


def canonical_url(html: str) -> str:
    match = _CANONICAL_RE.search(html or "")
    return match.group(1).strip() if match else ""


def hotel_jsonld(html: str) -> Optional[Dict]:
    """The page's ``schema.org/Hotel`` block, or ``None``.

    Marriott emits three JSON-LD blocks (Hotel, FAQPage, BreadcrumbList). Only
    the Hotel one carries identity; the others are skipped rather than merged,
    because a FAQ answer is prose about the property and not the property's own
    address.
    """
    for match in _LD_JSON_RE.finditer(html or ""):
        try:
            parsed = json.loads(match.group(1).strip())
        except (ValueError, TypeError):
            continue
        candidates = parsed if isinstance(parsed, list) else [parsed]
        for candidate in candidates:
            if isinstance(candidate, Mapping) and candidate.get("@type") == "Hotel":
                return dict(candidate)
    return None


@dataclass(frozen=True)
class IdentitySignals:
    """What the page said about which hotel it is."""

    name_on_page: str = ""
    address_on_page: str = ""
    postal_code: str = ""
    phone_on_page: str = ""
    property_code_on_page: str = ""
    canonical_url: str = ""
    pets_allowed_structured: str = ""
    jsonld_present: bool = False
    #: Every telephone number the page prints, normalised. ``phone_on_page`` is
    #: the STRUCTURED one and stays separate: a hotel that publishes no lodging
    #: JSON-LD still prints its own number in the footer, and confirming the
    #: census number appears there is evidence where structured data is silent.
    #: Read as a set of candidates, never as "the property's number".
    phones_on_page: Tuple[str, ...] = ()

    def to_dict(self) -> Dict:
        return {
            "name_on_page": self.name_on_page,
            "address_on_page": self.address_on_page,
            "postal_code": self.postal_code,
            "phone_on_page": self.phone_on_page,
            "property_code_on_page": self.property_code_on_page,
            "canonical_url": self.canonical_url,
            "pets_allowed_structured": self.pets_allowed_structured,
            "jsonld_present": self.jsonld_present,
            "phones_on_page": list(self.phones_on_page),
        }


def read_identity(html: str, *, final_url: str = "", title: str = "") -> IdentitySignals:
    """Collect every identity signal the page offers, strongest first."""
    node = hotel_jsonld(html)
    canonical = canonical_url(html)
    code = property_code(canonical) or property_code(final_url)
    if node:
        address = node.get("address") or {}
        if not isinstance(address, Mapping):
            address = {}
        return IdentitySignals(
            name_on_page=str(node.get("name") or "").strip(),
            address_on_page=str(address.get("streetAddress") or "").strip(),
            postal_code=str(address.get("postalCode") or "").strip(),
            phone_on_page=str(node.get("telephone") or "").strip(),
            property_code_on_page=code or property_code(str(node.get("@id") or "")),
            canonical_url=canonical or str(node.get("url") or ""),
            pets_allowed_structured=str(node.get("petsAllowed") or "").strip(),
            jsonld_present=True)
    # No structured data. The title is the weakest signal there is and is
    # recorded as such -- it is never sufficient on its own below.
    return IdentitySignals(name_on_page=collapse(title),
                           property_code_on_page=code,
                           canonical_url=canonical,
                           jsonld_present=False)


@dataclass(frozen=True)
class IdentityAssessment:
    confirmed: bool
    reasons: Tuple[str, ...]
    signals_matched: Tuple[str, ...]
    signals_conflicting: Tuple[str, ...]
    #: WHICH rule bound this page to the census row -- ``PROPERTY_CODE``,
    #: ``EXACT_ADDRESS_AND_NAME``, ``PHONE_AND_NAME``,
    #: ``CANONICAL_PATH_AND_NAME`` -- or empty when nothing bound it. Recorded
    #: so a confirmation can be audited without re-deriving it from the signal
    #: list, which several rules can produce identically.
    binding_method: str = ""


def assess_identity(signals: IdentitySignals, *, expected_name: str,
                    expected_property_code: str,
                    expected_postal_code: str = "",
                    expected_street: str = "") -> IdentityAssessment:
    """Is this page the property we asked for?

    The property code decides, and the name corroborates. That order is
    deliberate: "Do not use name alone if stronger signals exist" is the work
    order's instruction and it is also what the corpus learned the hard way --
    Columbus holds three Embassy Suites whose JSON-LD names are token-identical
    and whose codes are not.

    Confirmation requires the code AND at least one independent agreement
    (name, ZIP or street). A code with nothing behind it could be a URL we
    typed; a name with no code cannot tell two hotels on one campus apart.
    """
    matched: List[str] = []
    conflicting: List[str] = []
    reasons: List[str] = []

    page_code = (signals.property_code_on_page or "").lower()
    want_code = (expected_property_code or "").lower()
    if want_code and page_code:
        if page_code == want_code:
            matched.append("property_code")
        else:
            conflicting.append("property_code")
            reasons.append("page property code %r != expected %r"
                           % (page_code, want_code))
    elif want_code:
        reasons.append("no property code found on the page")

    page_tokens = name_tokens(signals.name_on_page)
    want_tokens = name_tokens(expected_name)
    if page_tokens and want_tokens:
        if page_tokens <= want_tokens or want_tokens <= page_tokens:
            matched.append("name")
        else:
            conflicting.append("name")
            reasons.append("page names %r, which is neither a subset nor a "
                           "superset of %r" % (signals.name_on_page, expected_name))
    else:
        reasons.append("no comparable name on the page")

    if expected_postal_code and signals.postal_code:
        if signals.postal_code.strip()[:5] == expected_postal_code.strip()[:5]:
            matched.append("postal_code")
        else:
            conflicting.append("postal_code")
            reasons.append("page ZIP %r != expected %r"
                           % (signals.postal_code, expected_postal_code))

    if expected_street and signals.address_on_page:
        if street_identity(signals.address_on_page, signals.postal_code) == \
                street_identity(expected_street, expected_postal_code):
            matched.append("street_identity")
        else:
            conflicting.append("street_identity")
            reasons.append("page street %r does not agree with expected %r"
                           % (signals.address_on_page, expected_street))

    confirmed = ("property_code" in matched
                 and len([m for m in matched if m != "property_code"]) >= 1
                 and "property_code" not in conflicting)
    if confirmed:
        reasons.append("confirmed on %s" % ", ".join(matched))
    return IdentityAssessment(confirmed=confirmed, reasons=tuple(reasons),
                              signals_matched=tuple(matched),
                              signals_conflicting=tuple(conflicting),
                              binding_method="PROPERTY_CODE" if confirmed else "")


# --------------------------------------------------------------------------- #
# Page health.
# --------------------------------------------------------------------------- #

def page_health(*, title: str, body_text: str, final_url: str,
                expected_property_code: str) -> Optional[str]:
    """The outcome this page forces, or ``None`` when it is worth reading.

    Ordered from "there is nothing here" outward, because a challenge page has
    a title and a body and would otherwise pass the emptiness checks. A page
    that survives all of these is not yet VALID -- identity and the policy
    surface are still ahead of it -- but it is a real rendered page.
    """
    haystack = (collapse(title) + " \n " + collapse(body_text)).lower()

    for marker in DENIAL_MARKERS:
        if marker in haystack:
            return O.ACCESS_DENIED

    if not collapse(title) and len(collapse(body_text)) < MIN_ANY_BODY_CHARS:
        return O.BLANK_PAGE

    if len(collapse(body_text)) < MIN_HYDRATED_BODY_CHARS:
        return O.UNHYDRATED

    if not is_first_party(final_url):
        return O.UNEXPECTED_PAGE

    # A generic brand landing page has no property code in its path. This is
    # the check that separates "Marriott answered" from "Marriott answered
    # about this hotel".
    if expected_property_code and \
            property_code(final_url).lower() != expected_property_code.lower():
        return O.UNEXPECTED_PAGE

    return None


# --------------------------------------------------------------------------- #
# The policy block.
# --------------------------------------------------------------------------- #

_BASIS_BY_WORD = {
    "stay": enums.BASIS_PER_STAY,
    "night": enums.BASIS_PER_NIGHT,
    "day": enums.BASIS_PER_DAY,
}

#: A labelled Marriott policy row: a named charge, a basis word, a colon, an
#: amount. The colon is what distinguishes the structured row from the summary
#: sentence above it, which restates the same numbers without one.
_LABELLED_CHARGE_RE = re.compile(
    r"(?P<label>(?:Non-?Refundable|Refundable)?\s*Pet\s+(?:Fee|Deposit)\s+"
    r"Per\s+(?P<basis>Stay|Night|Day))\s*:\s*"
    r"\$\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE)

#: A charge stated in the property's free prose: ``$20/day``, ``$100 per stay``.
#: Collected for CONTRADICTION DETECTION and never used to populate a field on
#: its own unless it is the only charge on the surface.
_PROSE_CHARGE_RE = re.compile(
    r"\$\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*(?:/|\s+per\s+|\s+a\s+)\s*"
    r"(?P<basis>night|day|stay)\b",
    re.IGNORECASE)

#: The same prose amount, followed closely by the property's own word for a
#: cleaning charge. Bounded to forty characters so it cannot reach across a
#: sentence and label an unrelated fee.
_PROSE_CLEANING_RE = re.compile(
    r"\$\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*(?:/|\s+per\s+|\s+a\s+)\s*"
    r"(?:night|day|stay)\b[^.$]{0,40}?\bclean(?:ing)?\b",
    re.IGNORECASE)

_WEIGHT_RE = re.compile(
    r"Maximum\s+Pet\s+Weight\s*:?\s*(?P<value>[\d,]+(?:\.\d+)?)\s*"
    r"(?P<unit>lbs?|pounds?|kgs?|kilograms?)\b",
    re.IGNORECASE)

_COUNT_RE = re.compile(
    r"Maximum\s+Number\s+of\s+Pets\s+in\s+Room\s*:?\s*(?P<count>\d+)",
    re.IGNORECASE)

_PETS_WELCOME_RE = re.compile(r"\bPets?\s+Welcome\b", re.IGNORECASE)
_PETS_REFUSED_RE = re.compile(
    r"\b(?:Pets?\s+Not\s+Allowed|No\s+Pets?\s+Allowed|"
    r"Pets?\s+Not\s+Permitted|Pets?\s+Are\s+Not\s+Allowed)\b", re.IGNORECASE)

_DOGS_ONLY_RE = re.compile(r"\bDogs\s+Only\b", re.IGNORECASE)
_CATS_REFUSED_RE = re.compile(
    r"\b(?:Cats?\s+are\s+not\s+permitted|No\s+Cats?\b|"
    r"Cats?\s+(?:are\s+)?not\s+allowed)\b", re.IGNORECASE)

#: Service-animal language is a legal access category and is never a pet
#: permission (membrane rule M6), so it is captured verbatim and establishes
#: nothing. Located by SEGMENT rather than by a sentence regex: Marriott's
#: block runs several statements together with no terminating punctuation, so
#: ``[^.]*`` around the phrase swallowed the entire policy surface -- which
#: would have made a fee row part of a service-animal quote.
_SERVICE_ANIMAL_RE = re.compile(r"\bservice\s+animals?\b", re.IGNORECASE)

_UNIT_CANON = {"lb": enums.UNIT_LB, "lbs": enums.UNIT_LB,
               "pound": enums.UNIT_LB, "pounds": enums.UNIT_LB,
               "kg": enums.UNIT_KG, "kgs": enums.UNIT_KG,
               "kilogram": enums.UNIT_KG, "kilograms": enums.UNIT_KG}


def _amount_minor(text: str) -> int:
    return int(round(float(text.replace(",", "")) * 100))


def segments(text: str) -> Tuple[Tuple[int, int], ...]:
    """Split the collapsed block into the statements it is made of.

    Marriott's rendered block concatenates a heading, a status line, the
    property's free prose and several labelled rows with no terminating
    punctuation between them. Sentence splitting on "." therefore produces one
    segment for the whole surface, which is how a service-animal quote ends up
    containing a fee row.

    So the boundaries are the block's own structure: a full stop, or the start
    of any statement this module recognises. Every offset is a real match
    position, so a segment is always a contiguous substring of the block.
    """
    bounds = {0, len(text)}
    for match in re.finditer(r"\.\s+", text):
        bounds.add(match.end())
    starters = (_LABELLED_CHARGE_RE, _WEIGHT_RE, _COUNT_RE, _PETS_WELCOME_RE,
                _PETS_REFUSED_RE, _DOGS_ONLY_RE, _CATS_REFUSED_RE)
    for pattern in starters:
        for match in pattern.finditer(text):
            bounds.add(match.start())
            bounds.add(match.end())
    heading = re.search(re.escape(POLICY_HEADING), text, re.IGNORECASE)
    if heading:
        bounds.add(heading.end())
    ordered = sorted(b for b in bounds if 0 <= b <= len(text))
    return tuple((a, b) for a, b in zip(ordered, ordered[1:])
                 if text[a:b].strip())


def _segment_containing(text: str, index: int) -> str:
    for start, end in segments(text):
        if start <= index < end:
            return collapse(text[start:end])
    return ""


@dataclass(frozen=True)
class Charge:
    """One money statement found on the policy surface, kept verbatim."""

    amount_minor: int
    basis: str
    origin: str              # "labelled_row" | "prose"
    refundable: Optional[bool]
    quote: str
    label: str = ""
    cleaning_labelled: bool = False

    def to_dict(self) -> Dict:
        return {"amount_minor": self.amount_minor, "basis": self.basis,
                "origin": self.origin, "refundable": self.refundable,
                "quote": self.quote, "label": self.label,
                "cleaning_labelled": self.cleaning_labelled}


@dataclass(frozen=True)
class PolicyReading:
    """Everything the bounded policy block says, and nothing it does not."""

    found: bool
    locator_id: str
    block_text: str
    heading_present: bool
    pets_allowed: Optional[bool] = None
    pets_allowed_quote: str = ""
    charges: Tuple[Charge, ...] = ()
    weight_value: Optional[float] = None
    weight_unit: str = ""
    weight_quote: str = ""
    pet_count_limit: Optional[int] = None
    pet_count_quote: str = ""
    dogs_only_quote: str = ""
    cats_refused_quote: str = ""
    service_animal_quote: str = ""
    contradictions: Tuple[Dict, ...] = ()
    parser_notes: Tuple[str, ...] = ()
    #: Charge components the block STATES and this reader did not turn into a
    #: :class:`Charge`. See :func:`unrepresented_charges` for why they are
    #: fatal to a fee field rather than merely interesting.
    unrepresented: Tuple[Dict, ...] = ()

    def to_dict(self) -> Dict:
        return {
            "found": self.found,
            "locator_id": self.locator_id,
            "block_text": self.block_text,
            "heading_present": self.heading_present,
            "pets_allowed": self.pets_allowed,
            "pets_allowed_quote": self.pets_allowed_quote,
            "charges": [c.to_dict() for c in self.charges],
            "weight_value": self.weight_value,
            "weight_unit": self.weight_unit,
            "weight_quote": self.weight_quote,
            "pet_count_limit": self.pet_count_limit,
            "pet_count_quote": self.pet_count_quote,
            "dogs_only_quote": self.dogs_only_quote,
            "cats_refused_quote": self.cats_refused_quote,
            "service_animal_quote": self.service_animal_quote,
            "contradictions": [dict(c) for c in self.contradictions],
            "parser_notes": list(self.parser_notes),
            "unrepresented": [dict(u) for u in self.unrepresented],
        }


#: Any dollar amount in the block, whatever wording surrounds it.
_ANY_AMOUNT_RE = re.compile(r"\$\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)")

#: Recurring-charge wording as an ADJECTIVE. ``_PROSE_CHARGE_RE`` needs "$20
#: per day"; a property that writes "$20 daily pet fee" states the same
#: recurring charge in a form no charge pattern here matches.
_RECURRING_WORD_RE = re.compile(r"\b(?:daily|nightly|per\s+night|per\s+day)\b",
                                re.IGNORECASE)

_DEPOSIT_WORD_RE = re.compile(r"\bdeposit\b", re.IGNORECASE)

#: The recurring bases. A block whose wording is recurring but whose charges
#: are all per-stay has a component this reader did not capture.
_RECURRING_BASES = frozenset({enums.BASIS_PER_NIGHT, enums.BASIS_PER_DAY})


def unrepresented_charges(text: str,
                          charges: Sequence["Charge"]) -> Tuple[Dict, ...]:
    """Charge components the block states that no emitted charge accounts for.

    WHY THIS EXISTS
    ---------------
    PTF-MARRIOTT-ACCORDION-LOCATOR-HARDENING-021 corrected the locator so The
    Trade's own Pet Policy panel is read instead of its FAQ. The panel says:

        Pet deposit starts at $125 (may increase for suites) + $20 daily pet
        fee. Non-Refundable Pet Fee Per Stay: $125.00

    and the reader still emitted exactly one charge -- $125 per stay -- because
    ``$20 daily`` is an adjective rather than a "per day" phrase and "deposit
    starts at $125" carries no basis word at all. A complete block therefore
    produced an understated fee, which is the same guest-visible error the
    locator fix was meant to end, relocated one layer down.

    So the reader stops asserting a single fee when the surface plainly states
    more than one component. It does NOT try to add them up: a deposit, a
    recurring charge and a per-stay fee are three different things, the frozen
    schema carries one ``pet_fee`` with one ``fee_basis``, and inventing a
    combined number would be a worse error than withholding.

    Three components are detected, each from the property's own words:

      amounts    a dollar figure in the block that no charge carries. Catches
                 tiered fees ("0-5 nights $75, 5+ $150") where only the first
                 tier became a charge, and second charges stated in prose
      recurring  recurring wording with no per-night or per-day charge emitted
      deposit    the word "deposit" with no deposit-labelled charge

    Returns a tuple of findings; empty means the emitted charges account for
    everything the block says about money.
    """
    findings: List[Dict] = []
    stated = {}
    for match in _ANY_AMOUNT_RE.finditer(text or ""):
        stated.setdefault(_amount_minor(match.group("amount")),
                          text[match.start():match.end()])
    represented = {c.amount_minor for c in charges}
    for amount in sorted(set(stated) - represented):
        findings.append({
            "kind": "amount_not_represented",
            "amount_minor": amount,
            "quote": stated[amount],
            "note": ("the block states this amount and no charge this reader "
                     "produced carries it"),
        })

    if _RECURRING_WORD_RE.search(text or "") and not any(
            c.basis in _RECURRING_BASES for c in charges):
        match = _RECURRING_WORD_RE.search(text)
        findings.append({
            "kind": "recurring_charge_not_represented",
            "amount_minor": None,
            "quote": _segment_containing(text, match.start()),
            "note": ("the block states a recurring charge and every charge "
                     "read from it is one-off; a per-stay figure alone "
                     "understates what a stay costs"),
        })

    if _DEPOSIT_WORD_RE.search(text or "") and not any(
            "deposit" in (c.label or "").lower() for c in charges):
        match = _DEPOSIT_WORD_RE.search(text)
        findings.append({
            "kind": "deposit_not_represented",
            "amount_minor": None,
            "quote": _segment_containing(text, match.start()),
            "note": ("the block states a deposit and no charge read from it "
                     "is labelled one; a deposit is not a fee"),
        })
    return tuple(findings)


def parse_policy_block(block_text: str, *, locator_id: str = "") -> PolicyReading:
    """Read the bounded policy block. Labels only; no interpretation.

    Every quote returned is a contiguous substring of the collapsed block, so
    it survives ``evidence.quote_is_contiguous`` against the saved page text.
    """
    text = collapse(block_text)
    if not text:
        return PolicyReading(found=False, locator_id=locator_id, block_text="",
                             heading_present=False,
                             parser_notes=("the policy container was empty",))

    notes: List[str] = []
    charges: List[Charge] = []

    cleaning_amounts = {_amount_minor(m.group("amount"))
                        for m in _PROSE_CLEANING_RE.finditer(text)}

    for match in _LABELLED_CHARGE_RE.finditer(text):
        label = collapse(match.group("label"))
        refundable: Optional[bool] = None
        lowered = label.lower().replace("-", "")
        if "nonrefundable" in lowered:
            refundable = False
        elif lowered.startswith("refundable"):
            refundable = True
        amount = _amount_minor(match.group("amount"))
        charges.append(Charge(
            amount_minor=amount,
            basis=_BASIS_BY_WORD[match.group("basis").lower()],
            origin="labelled_row", refundable=refundable,
            quote=text[match.start():match.end()], label=label,
            cleaning_labelled=amount in cleaning_amounts))

    for match in _PROSE_CHARGE_RE.finditer(text):
        amount = _amount_minor(match.group("amount"))
        charges.append(Charge(
            amount_minor=amount,
            basis=_BASIS_BY_WORD[match.group("basis").lower()],
            origin="prose", refundable=None,
            quote=text[match.start():match.end()],
            cleaning_labelled=amount in cleaning_amounts))

    # --- contradiction: one amount, two bases, one first-party surface ---- #
    bases_by_amount: Dict[int, List[Charge]] = {}
    for charge in charges:
        bases_by_amount.setdefault(charge.amount_minor, []).append(charge)
    contradictions: List[Dict] = []
    for amount, group in sorted(bases_by_amount.items()):
        distinct = sorted({c.basis for c in group})
        if len(distinct) > 1:
            contradictions.append({
                "amount_minor": amount,
                "field": "fee_basis",
                "bases_stated": distinct,
                "withholding_reason": enums.SOURCE_CONTRADICTORY,
                "quotes": [c.quote for c in group],
                "note": ("the same amount is stated on two different bases on "
                         "one first-party surface; per_day and per_night are "
                         "distinct under the frozen schema and this layer does "
                         "not select a winner"),
            })

    # --- weight: value and unit only, never a comparison ------------------- #
    weight_value: Optional[float] = None
    weight_unit = ""
    weight_quote = ""
    weight_seen: List[Tuple[float, str]] = []
    for match in _WEIGHT_RE.finditer(text):
        value = float(match.group("value").replace(",", ""))
        unit = _UNIT_CANON.get(match.group("unit").lower().rstrip("."), "")
        weight_seen.append((value, unit))
        # Prefer the labelled row (the one with a colon) over the summary line.
        if weight_value is None or ":" in match.group(0):
            weight_value, weight_unit = value, unit
            weight_quote = text[match.start():match.end()]
    distinct_weights = {w for w, _ in weight_seen}
    if len(distinct_weights) > 1:
        notes.append("the block states more than one maximum pet weight (%s); "
                     "the labelled row was taken and the disagreement is "
                     "recorded here" % sorted(distinct_weights))

    # --- pet count --------------------------------------------------------- #
    pet_count: Optional[int] = None
    pet_count_quote = ""
    counts_seen: List[int] = []
    for match in _COUNT_RE.finditer(text):
        counts_seen.append(int(match.group("count")))
        if pet_count is None or ":" in match.group(0):
            pet_count = int(match.group("count"))
            pet_count_quote = text[match.start():match.end()]
    if len(set(counts_seen)) > 1:
        notes.append("the block states more than one maximum pet count (%s)"
                     % sorted(set(counts_seen)))

    # --- allowed / refused -------------------------------------------------- #
    pets_allowed: Optional[bool] = None
    pets_allowed_quote = ""
    refused = _PETS_REFUSED_RE.search(text)
    welcome = _PETS_WELCOME_RE.search(text)
    if refused and welcome:
        notes.append("the block says both that pets are welcome and that they "
                     "are not allowed; neither is taken")
        contradictions.append({
            "amount_minor": None, "field": "pets_allowed",
            "bases_stated": [], "withholding_reason": enums.SOURCE_CONTRADICTORY,
            "quotes": [text[refused.start():refused.end()],
                       text[welcome.start():welcome.end()]],
            "note": "the surface asserts and denies pet acceptance",
        })
    elif refused:
        pets_allowed = False
        pets_allowed_quote = text[refused.start():refused.end()]
    elif welcome:
        pets_allowed = True
        pets_allowed_quote = text[welcome.start():welcome.end()]

    dogs_only = _DOGS_ONLY_RE.search(text)
    cats_refused = _CATS_REFUSED_RE.search(text)
    service = _SERVICE_ANIMAL_RE.search(text)

    return PolicyReading(
        found=True, locator_id=locator_id, block_text=text,
        heading_present=POLICY_HEADING.lower() in text.lower(),
        pets_allowed=pets_allowed, pets_allowed_quote=pets_allowed_quote,
        charges=tuple(charges),
        weight_value=weight_value, weight_unit=weight_unit,
        weight_quote=weight_quote,
        pet_count_limit=pet_count, pet_count_quote=pet_count_quote,
        dogs_only_quote=(text[dogs_only.start():dogs_only.end()]
                         if dogs_only else ""),
        cats_refused_quote=(text[cats_refused.start():cats_refused.end()]
                            if cats_refused else ""),
        service_animal_quote=(_segment_containing(text, service.start())
                              if service else ""),
        contradictions=tuple(contradictions), parser_notes=tuple(notes),
        unrepresented=unrepresented_charges(text, charges))


# --------------------------------------------------------------------------- #
# Reading -> the frozen observation vocabulary.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ExtractionResult:
    """The reading translated into ``ptf-policy-observation/1.0`` vocabulary.

    ``withheld`` and ``non_inferences`` are as much of the output as
    ``extraction`` is. A field this pilot declined to populate, and the reason,
    is the part a reviewer needs in order to trust the fields it did populate.
    """

    extraction: Dict
    evidence: Tuple[Dict, ...]
    flags: Tuple[Dict, ...]
    withheld: Dict[str, str]
    non_inferences: Tuple[str, ...]
    parser_warnings: Tuple[str, ...]


def _evidence_item(quote: str, location: str, fields: Sequence[str]) -> Dict:
    return {"quote": quote, "location": location, "field_refs": list(fields)}


def to_extraction(reading: PolicyReading, *, location: str) -> ExtractionResult:
    """Map a reading onto the closed extraction vocabulary.

    The mapping rules, in full, so a reviewer can check them against the block:

    * ``pets_allowed`` comes from "Pets Welcome" / "Pets Not Allowed" alone.
    * ``pet_fee`` is populated only when the recurring charge on the surface is
      unambiguous. Two labelled charges on different bases, with no prose
      naming one of them a cleaning charge, leaves BOTH ``pet_fee`` and
      ``fee_basis`` withheld.
    * ``fee_basis`` is dropped -- and only the basis, not the amount -- when the
      chosen charge's amount appears elsewhere on the surface with a different
      basis. The contradiction is preserved, never resolved.
    * ``cleaning_fee`` is populated only when the PROPERTY'S OWN PROSE calls
      that amount a cleaning charge. It is never inferred from a per-stay
      basis.
    * ``weight_limit`` carries a value and a unit and no operator or scope.
    * ``fee_scope`` is never populated. Marriott does not state it.
    """
    extraction: Dict = {}
    evidence: List[Dict] = []
    flags: List[Dict] = []
    withheld: Dict[str, str] = {}
    non_inferences: List[str] = [
        "fee_scope: not stated by the Marriott template; unknown is absence",
        "weight_limit.operator: 'Maximum' is not recorded as lt or lte; "
        "defaulting a comparison is a guest-visible error in both directions",
        "weight_limit.scope: not stated; per_pet is not assumed",
    ]

    if reading.pets_allowed is not None:
        extraction["pets_allowed"] = reading.pets_allowed
        evidence.append(_evidence_item(reading.pets_allowed_quote, location,
                                       ["pets_allowed"]))
    else:
        withheld["pets_allowed"] = (enums.SOURCE_CONTRADICTORY
                                    if reading.contradictions
                                    else enums.SOURCE_SILENT)

    # --- charges ----------------------------------------------------------- #
    labelled = [c for c in reading.charges if c.origin == "labelled_row"]
    prose_only = [c for c in reading.charges if c.origin == "prose"]
    contradicted_amounts = {c["amount_minor"] for c in reading.contradictions
                            if c.get("amount_minor") is not None}

    cleaning = [c for c in labelled if c.cleaning_labelled]
    fee_candidates = [c for c in labelled if not c.cleaning_labelled]
    if not labelled and prose_only:
        # No structured row at all. A single unambiguous prose statement is
        # still the property's own words and may carry the fee.
        distinct = {(c.amount_minor, c.basis) for c in prose_only}
        if len(distinct) == 1:
            fee_candidates = prose_only[:1]
        else:
            flags.append({"code": "FLAG_MULTI_POLICY_BLOCKS",
                          "detail": "the surface states several unlabelled "
                                    "charges and no structured row; no fee is "
                                    "taken from prose alone"})

    if cleaning:
        charge = cleaning[0]
        extraction["cleaning_fee"] = charge.amount_minor
        evidence.append(_evidence_item(charge.quote, location, ["cleaning_fee"]))

    if len(fee_candidates) == 1:
        charge = fee_candidates[0]
        extraction["pet_fee"] = charge.amount_minor
        extraction["fee_currency"] = "USD"
        evidence.append(_evidence_item(charge.quote, location,
                                       ["pet_fee", "fee_currency"]))
        if charge.amount_minor in contradicted_amounts:
            withheld["fee_basis"] = enums.SOURCE_CONTRADICTORY
            flags.append({
                "code": "FLAG_AMBIGUOUS_BASIS",
                "detail": ("the $%.2f charge is stated on more than one basis "
                           "on this surface; per_day and per_night are "
                           "distinct and this layer does not choose"
                           % (charge.amount_minor / 100.0))})
        else:
            extraction["fee_basis"] = charge.basis
            evidence.append(_evidence_item(charge.quote, location, ["fee_basis"]))
    elif len(fee_candidates) > 1:
        withheld["pet_fee"] = enums.SOURCE_AMBIGUOUS
        withheld["fee_basis"] = enums.SOURCE_AMBIGUOUS
        flags.append({
            "code": "FLAG_MULTI_POLICY_BLOCKS",
            "detail": ("the surface carries %d distinct pet charges (%s) and "
                       "the property's prose does not say which is the pet fee"
                       % (len(fee_candidates),
                          ", ".join(sorted(c.quote for c in fee_candidates))))})
    elif reading.pets_allowed:
        withheld["pet_fee"] = enums.SOURCE_SILENT

    if "fee_basis" in extraction:
        # A basis that was populated is not also withheld. Belt and braces:
        # the two maps must never disagree about one field.
        withheld.pop("fee_basis", None)

    # --- components the schema cannot carry -------------------------------- #
    # A single ``pet_fee`` cannot express "a deposit AND a nightly charge AND a
    # per-stay fee", nor a tiered fee whose second tier never became a charge.
    # Where the block states more than the emitted charges carry, the fee is
    # WITHHELD rather than asserted at whichever component happened to parse.
    # Publishing the parsed one would understate the cost while looking
    # complete, which is the failure this guard exists to prevent.
    # A charge this reader PARSED and no field can carry is such a component
    # too, and it was the one shape this guard could not see. Courtyard
    # Milwaukee Downtown writes "Daily cleaning fee of $5/ day in addition to
    # the one time non-refundable pet fee Non-Refundable Pet Fee Per Stay:
    # $50.00". Both amounts become charges; only structured rows become fee
    # candidates; so $50 published and $5 a day vanished without a withholding,
    # a flag or a note. ``unrepresented_charges`` could not catch it because it
    # asks which amounts became CHARGES, and this one did -- it just never
    # became a FIELD.
    #
    # Computed here rather than in the parser because only this layer knows
    # which charges the extraction ended up carrying.
    carried = {c.amount_minor for c in fee_candidates}
    carried.update(c.amount_minor for c in cleaning)
    unrepresented = list(reading.unrepresented) + [
        {"kind": "charge_not_represented", "amount_minor": charge.amount_minor,
         "quote": charge.quote,
         "note": ("the reader read this charge from the block and no field "
                  "carries it")}
        for charge in reading.charges if charge.amount_minor not in carried]

    if unrepresented:
        extraction.pop("pet_fee", None)
        extraction.pop("fee_basis", None)
        extraction.pop("fee_currency", None)
        evidence = [e for e in evidence
                    if not ({"pet_fee", "fee_basis", "fee_currency"}
                            & set(e.get("field_refs") or []))]
        withheld["pet_fee"] = enums.SCHEMA_CANNOT_REPRESENT
        withheld["fee_basis"] = enums.SCHEMA_CANNOT_REPRESENT
        flags.append({
            "code": "FLAG_MULTI_POLICY_BLOCKS",
            "detail": ("the block states charge components this schema cannot "
                       "carry together (%s); no single pet_fee is asserted"
                       % "; ".join(sorted(u["quote"] for u in
                                          unrepresented)))})
        non_inferences.append(
            "pet_fee: the surface states more than one charge component and "
            "the schema carries one amount and one basis; the components are "
            "not summed and none is chosen")

    # --- weight ------------------------------------------------------------- #
    if reading.weight_value is not None and reading.weight_unit:
        extraction["weight_limit"] = {"value": reading.weight_value,
                                      "unit": reading.weight_unit}
        evidence.append(_evidence_item(reading.weight_quote, location,
                                       ["weight_limit"]))

    # --- count -------------------------------------------------------------- #
    if reading.pet_count_limit is not None:
        extraction["pet_count_limit"] = reading.pet_count_limit
        # "in Room" is the label's own word, not an inference about scope.
        extraction["pet_count_scope"] = enums.SCOPE_PER_ROOM
        evidence.append(_evidence_item(reading.pet_count_quote, location,
                                       ["pet_count_limit", "pet_count_scope"]))

    # --- species ------------------------------------------------------------ #
    if reading.dogs_only_quote:
        extraction["species_allowed"] = ["dog"]
        evidence.append(_evidence_item(reading.dogs_only_quote, location,
                                       ["species_allowed"]))
    if reading.cats_refused_quote:
        extraction["cats_allowed"] = False
        evidence.append(_evidence_item(reading.cats_refused_quote, location,
                                       ["cats_allowed"]))
    if not reading.dogs_only_quote and not reading.cats_refused_quote:
        non_inferences.append(
            "species: a generic 'Pets Welcome' is not dogs+cats; the species "
            "map stays empty unless the surface names a species")

    # --- service animals ------------------------------------------------------ #
    if reading.service_animal_quote:
        extraction["service_animal_exception"] = reading.service_animal_quote
        evidence.append(_evidence_item(reading.service_animal_quote, location,
                                       ["service_animal_exception"]))

    for contradiction in reading.contradictions:
        if contradiction.get("field") == "pets_allowed":
            flags.append({"code": "FLAG_CONTRADICTS_OFFICIAL",
                          "detail": contradiction["note"]})

    return ExtractionResult(
        extraction=extraction, evidence=tuple(evidence), flags=tuple(flags),
        withheld=withheld, non_inferences=tuple(non_inferences),
        parser_warnings=tuple(reading.parser_notes))


__all__ = [
    "BRAND", "FIRST_PARTY_HOSTS", "POLICY_LOCATORS", "POLICY_HEADING",
    "HOTEL_INFO_LOCATOR", "DENIAL_MARKERS", "MIN_HYDRATED_BODY_CHARS",
    "MIN_ANY_BODY_CHARS", "collapse", "name_tokens", "host_of",
    "is_first_party", "property_code", "canonical_url", "hotel_jsonld",
    "IdentitySignals", "read_identity", "IdentityAssessment", "assess_identity",
    "page_health", "Charge", "PolicyReading", "parse_policy_block",
    "ExtractionResult", "to_extraction",
]

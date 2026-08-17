"""PTF-PROD-001 -- production hotel-profile renderer (narrow slice).

Translates the approved final-hybrid design authority
(design/prototypes/pettripfinder/ptf-design-001/final-hybrid/) into a
production, data-driven hotel-profile renderer. This is a narrow view-model
adapter + a single reusable render function -- NOT a new engine and NOT a
broadening of the AES-WEB component architecture (whose components remain
PROPOSED with unvalidated emitters). One template + one section order renders
all five verification states.

Doctrine preserved from the importer/site pipeline:
  * facts come only from repository-authorized verified evidence (READY
    candidates) or the promoted production CSV -- never invented;
  * an unstated field is shown as "Not stated by the reviewed source",
    never guessed and never rendered as "no";
  * VERIFIED_NO_PETS and POLICY_UNVERIFIED never use verified-pet-friendly
    styling or language;
  * no coordinates exist, so no distance/"nearby" is ever shown;
  * no internal HTTP/blocking/automation wording is ever exposed publicly.

No network. No provider calls. Reads production/candidate data, never writes
inventory or evidence.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from scripts.pettripfinder import canonical_view
from scripts.pettripfinder.contracts import compat_readers, enums
from scripts.pettripfinder.site_data import (
    normalize_name,
    read_production_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

STATE_VERIFIED = "VERIFIED_PET_FRIENDLY"
STATE_NO_PETS = "VERIFIED_NO_PETS"
STATE_UNVERIFIED = "POLICY_UNVERIFIED"

_MEDIA_CAP = 'Property photo unavailable. <a href="/methodology/#photos">How we handle photos</a>'
_NOT_STATED = "Not stated by the reviewed source"

#: PTF-RENDERER-FIDELITY-001. Silence and withholding are OPPOSITE claims about
#: a hotel and must never share a treatment. "Not stated" says the source did
#: not address the field; a withheld field means the source DID, and what it
#: said could not be published accurately. Sixty-six committed withholding
#: decisions rendered through the silence path until now, telling readers a
#: hotel had said nothing about a fee it had in fact contradicted itself about.
#: One semantic class across every surface, distinct from the dim class that
#: silence uses on the profile and from ``ptf-unknown`` on the comparison table.
WITHHELD_CLS = "ptf-withheld"
_HOME_SVG = ('<svg class="glyph" width="34" height="34" viewBox="0 0 24 24" fill="none" '
             'stroke="#f6f1e7" stroke-width="1.4" aria-hidden="true">'
             '<path d="M3 21V9l9-5 9 5v12"/><path d="M9 21v-6h6v6"/><path d="M3 21h18"/></svg>')


def _is_published_category(slug: str) -> bool:
    """Whether the market being built publishes this directory."""
    from scripts.pettripfinder.site_pages import is_published_category

    return is_published_category(slug)


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def _friendly_date(value: Optional[str]) -> str:
    """Render an ISO date as "Month D, YYYY" to match the approved design
    authority. Any non-ISO / empty value is returned unchanged.

    Accepts a full ISO-8601 timestamp as well as a bare date. Attested hotels
    carry an observed_at taken from the capture itself, which is a timestamp --
    and a page reading "Verified 2026-07-29T14:28:29.492Z" is an internal
    artifact leaking onto a consumer surface. Only the date is displayed; the
    exact instant remains in the attestation record where it belongs.
    """
    if not value:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ]\d{2}:\d{2}.*)?$", value.strip())
    if not m:
        return value
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return "%s %d, %d" % (_MONTHS[mo - 1], d, y)


def _cap_first(s: str) -> str:
    s = (s or "").strip()
    return (s[:1].upper() + s[1:]) if s else s


# --------------------------------------------------------------------------- #
# Corridor display labels (PTF-CORRIDORS-002 Part D).
#
# The second, address-token display taxonomy that used to live here is
# retired: the label now comes from the SAME market-config assignment that
# drives corridor routes, sitemap entries, and navigation
# (``scripts/pettripfinder/markets``). An assigned hotel shows its
# corridor's configured display area (even when the corridor is suppressed
# from publication -- the label is a fact about location, the route is
# not); an unassigned hotel falls back to its own city, never to an area
# inferred from address text or a marketing name. The metro anchor is the
# market's primary city + state code.
# --------------------------------------------------------------------------- #


def _market_display_context(market_id: str = None):
    """(market, assignment over ALL seed hotel rows) -- cached per market id:
    the config files and the seed CSV are committed, deterministic inputs.

    PTF-MULTIMARKET-001: the market is named, not inferred from the number
    of configured markets, and the cache is keyed by that name so a second
    registered market can never be served from another market's entry."""
    from scripts.pettripfinder.market_context import PRODUCTION_MARKET_ID, resolve_market
    market_id = market_id or PRODUCTION_MARKET_ID
    cached = _MARKET_DISPLAY_CONTEXT.get(market_id)
    if cached is None:
        from scripts.pettripfinder.markets import assign_hotels
        market = resolve_market(market_id=market_id)
        rows = [r for r in read_production_rows()
                if r.get("category") == "pet-friendly-hotels"]
        cached = (market, assign_hotels(market, rows))
        _MARKET_DISPLAY_CONTEXT[market_id] = cached
    return cached


_MARKET_DISPLAY_CONTEXT = {}


def _corridor_area(city: str, name: str = "", market_id: str = None) -> str:
    from scripts.pettripfinder.markets import corridor_display_area
    market, assignment = _market_display_context(market_id)
    return "%s corridor" % corridor_display_area(market, assignment, name, city)


def _corridor_label(city: str, name: str = "", market_id: str = None) -> str:
    from scripts.pettripfinder.markets import corridor_display_label
    market, assignment = _market_display_context(market_id)
    return corridor_display_label(market, assignment, name, city)


def _related_fact(ff: Dict[str, str]) -> str:
    """One useful supported pet-policy fact for a related card, in priority
    order. "" when the source stated nothing usable -- never inferred."""
    if ff.get("pet_fee"):
        basis = ff.get("fee_basis")
        return "%s%s" % (ff["pet_fee"], (" " + basis) if basis else "")
    sp = (ff.get("species_allowed") or "").lower()
    if "dog" in sp and "cat" in sp:
        return "Dogs and cats accepted"
    if "cat" in sp:
        return "Cats accepted"
    if "dog" in sp:
        return "Dogs accepted"
    if ff.get("pet_count_limit"):
        return "Up to %s pets" % ff["pet_count_limit"]
    if ff.get("pets_allowed") == "true":
        return "Pets welcome"
    return ""


def _initials(name: str) -> str:
    words = re.sub(r"[^A-Za-z0-9 ]", " ", name or "").split()
    letters = [w[0] for w in words if w and w[0].isalpha()]
    return ("".join(letters[:2]) or "PT").upper()


# --------------------------------------------------------------------------- #
# View model.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RelatedHotel:
    name: str
    area: str
    fact: str          # one supported pet-policy fact, or "" (omitted)
    verified_at: str
    route: str


@dataclass(frozen=True)
class HotelProfileVM:
    state: str
    name: str
    corridor: str
    initials: str
    address: str
    phone: str
    official_url: str
    verified_at: Optional[str]
    source_name: Optional[str]
    summary: str
    facts: Tuple[Tuple[str, str, str], ...]           # (label, value, cls)
    verif_badge_text: str
    verif_badge_cls: str                               # ok | stop | neutral
    verif_chip: str                                    # short chip in media
    trust_cls: str
    trust_line: str
    evidence_quote: Optional[str]
    details_rows: Tuple[Tuple[str, str, str], ...] = ()   # (label, value, cls)
    details_plain: str = ""
    details_note: str = ""
    service_note: str = ""
    prov_status: str = ""                              # non-empty => unverified provenance
    actions_mode: str = "book"                         # book | alt | unverif
    related: Tuple[RelatedHotel, ...] = ()
    source_url: str = ""                               # exact committed policy-evidence URL (PROD-004)

    @property
    def media_state(self) -> str:
        return self.verif_badge_cls


# --------------------------------------------------------------------------- #
# Summary / facts / details composition (deterministic; evidence-only).
# --------------------------------------------------------------------------- #

#: Fields whose total absence means the reviewed source stated no policy detail
#: at all. A staged schedule and a tiered ceiling are policy detail too: a record
#: carrying one is NOT sparse, and must never be described as stating no fee.
_STATED_FIELDS = ("species_allowed", "pet_fee", "pet_count_limit", "weight_limit",
                  "fee_schedule", "fee_cap_tiers",
                  # PTF-COLUMBUS-FINAL-CLOSURE-001: a per-pet fee schedule is a
                  # stated fact like any other. Its absence here meant a record
                  # carrying only that schedule was treated as sparse and
                  # rendered "Fee, pet limit, weight limit: Not stated".
                  "fee_pet_schedule",
                  # PTF-COLUMBUS-HYATT-002: a combined-only record has stated a
                  # weight rule, and calling it sparse would print "weight
                  # limit: Not stated" on a page that carries one.
                  "weight_limit_combined",
                  # PTF-RENDERER-FIDELITY-001. A stated deposit or cleaning fee
                  # is money the guest will be asked for, which is policy
                  # detail by any reading. No committed record changes verdict
                  # -- both properties carrying one state other facts too --
                  # but a record that stated only a deposit would have had it
                  # dropped.
                  "pet_deposit", "cleaning_fee")

#: PTF-RENDERER-FIDELITY-001. Prose the property stated about its pet policy
#: that is not one of the structured facts above. A record carrying only these
#: is still SPARSE -- eight dim "Not stated" rows would be noise on a page that
#: has almost nothing -- but its own words must still reach the reader.
#:
#: Americas Best Value Inn Celina states "Small pets are allowed with manager's
#: approval. Please call hotel directly for fees and restrictions" and rendered
#: "the reviewed official source did not state the species, fee, pet limit, or
#: weight limit": a page that speaks, described as one that says nothing.
_RESTRICTION_FIELDS = ("breed_restrictions", "unattended_policy",
                       "reservation_requirement", "general_restrictions",
                       "pet_room_restriction")

#: The label each restriction carries, matching the rich detail table so a
#: reader moving between two profiles sees one vocabulary.
_RESTRICTION_LABELS = {
    "breed_restrictions": "Breed restrictions",
    "unattended_policy": "Unattended-pet rule",
    "reservation_requirement": "Reservation requirement",
    "general_restrictions": "Other restrictions",
    "pet_room_restriction": "Pet room availability",
}


#: Species this renderer can name, in the order a reader expects them.
_SPECIES_ORDER = (("bird", "Birds"), ("fish", "fish"), ("dog", "dogs"), ("cat", "cats"))


def _species_phrase(species: str) -> str:
    """A sentence naming every species the source permits.

    A property that admits birds and fish as well as dogs and cats has said so;
    rendering only the usual two would tell a bird's owner the hotel refuses it.
    """
    sp = (species or "").lower()
    named = [label for stem, label in _SPECIES_ORDER if stem in sp]
    if len(named) > 2:
        listed = ", ".join(named[:-1]) + ", and " + named[-1]
        return "%s are accepted." % listed
    if "dog" in sp and "cat" in sp:
        return "Dogs and cats are accepted."
    if "dog" in sp:
        return "Dogs are accepted."
    if "cat" in sp:
        return "Cats are accepted."
    return "Pets are welcome."


# A weight limit is COMBINED across pets only where the source says so. Drury
# ("a combined weight of 80 pounds") and Hyatt ("75 pounds combined") do; a
# Marriott property stating "Maximum Pet Weight: 40.0lbs" states a PER-PET
# limit, and calling that combined understates what a guest may bring.
def _source_states_combined_weight(evidence: str, weight_limit: str = "") -> bool:
    """True only when the official wording ties THIS limit to all pets together.

    PTF-SITE-006. The summary previously called EVERY weight limit combined, so
    Aloft Columbus Easton published "up to 2 pets with a combined weight limit
    of 40.0 pounds" from a source that says "Maximum Pet Weight: 40.0lbs" per
    pet. Whether a limit is per-pet or combined is the difference between one
    40lb dog and two, so it is never inferred.

    The word "combined" appearing anywhere is not enough. A Hyatt source reads
    "up to 50 pounds (two dogs permitted if combined weight is under 75
    pounds)" -- it states a per-pet limit of 50 AND a combined limit of 75, and
    the recorded weight_limit is the per-pet 50. Matching on the bare word would
    relabel that 50 as combined, which is the same error in a subtler form. So
    a word from the "combine" family must sit next to the number actually
    being published.

    PTF-COLUMBUS-STRUCTURAL-UNRESOLVED-001: matches the "combin-" stem, not
    only the literal "combined" -- IHG's Candlewood Suites Columbus - Grove
    City page reads "max combine weight of 80lbs for two pets", and the
    un-conjugated "combine" is exactly as load-bearing as "combined" would
    have been. This is a fallback only; a record carrying a structured
    weight_limit_operator == "combined" value never reaches this function
    (see _verified_summary).
    """
    text = evidence or ""
    m = re.search(r"\d+(?:\.\d+)?", weight_limit or "")
    if not m:
        return False
    number = _TRAILING_ZEROS_RE.sub(r"\1", m.group(0))
    # The number, in either recorded form, within a short window of a
    # "combine"-family word (combine, combines, combined, combining).
    for form in {number, m.group(0)}:
        n = re.escape(form)
        if re.search(r"combin\w*[^.]{0,30}?%s|%s[^.]{0,30}?combin\w*" % (n, n), text, re.I):
            return True
    return False


_NONREFUNDABLE_RE = re.compile(r"non[- ]?refundable", re.I)
_TRAILING_ZEROS_RE = re.compile(r"(\d+)\.0+(?=\D|$)")


def _prose_number(text: str) -> str:
    """"$50.00" -> "$50", "40.0 pounds" -> "40 pounds", for running prose.

    The structured fields keep their exact recorded values; only the sentence
    drops a trailing zero a reader does not need.
    """
    return _TRAILING_ZEROS_RE.sub(r"\1", text or "")


def canonical_fee_scope(f: Dict) -> str:
    """The canonical fee scope of a legacy facts dict, or "".

    PTF-RENDERER-FIDELITY-001. Four spellings of this field reached the corpus
    and this renderer recognised exactly one of them, so twelve of fourteen
    committed values -- every per-pet fee in Dayton among them -- reached no
    public surface at all. A guest bringing two dogs to a $15-per-pet property
    read $15.

    The translation table is the frozen one from the contracts package; nothing
    is re-derived here.
    """
    explicit = enums.LEGACY_FEE_SCOPES.get(
        str(f.get("fee_scope") or "").strip().lower(), "")
    if explicit:
        return explicit
    # Seven records state the scope INSIDE the basis string -- "per room per
    # night", "per stay per pet". Reading only the dedicated field would call
    # those unscoped and print a disclosure about a fact the source did give.
    # The decomposition table is Phase A's; nothing is re-derived here.
    _, from_basis, _, _ = compat_readers.decompose_fee_basis(f.get("fee_basis"))
    return from_basis or ""


def fee_qualifier_phrase(f: Dict) -> str:
    """``per pet per night`` / ``per room per stay`` / ``per night`` / "".

    Scope leads where it is carried in its own field, because scope is the half
    a reader needs when more than one animal is coming and the half that used
    to be dropped.

    Where the legacy basis string already carries the scope it is returned
    verbatim: "per night for up to 2 pets" is the source's own wording and
    rebuilding it as "per room per night for up to 2 pets" would say the same
    thing twice while changing a page nobody asked us to change.
    """
    basis = str(f.get("fee_basis") or "").strip().lower()
    explicit = enums.LEGACY_FEE_SCOPES.get(
        str(f.get("fee_scope") or "").strip().lower(), "")
    if not explicit:
        return basis
    word = canonical_view.SCOPE_WORDS[explicit]
    if not basis:
        return word
    if word in basis:
        return basis
    return "%s %s" % (word, basis)


def fee_scope_display(f: Dict) -> str:
    """Comparison-table cell for fee scope: ``Per pet`` / ``Per room`` / ""."""
    scope = canonical_fee_scope(f)
    return _cap_first(canonical_view.SCOPE_WORDS[scope]) if scope else ""


def cap_qualifier_note(f: Dict) -> str:
    """What a fee cap's ceiling is qualified by, for the comparison table.

    PTF-RENDERER-FIDELITY-001 §11. A cap NEVER inherits scope from the fee it
    caps. "Maximum $150" with no stated scope might cap the room or cap each
    animal, and for two pets those are $150 and $300 -- so where the source did
    not say, the cell says that rather than letting the ceiling look universal.
    """
    cap = f.get("fee_cap") or {}
    if not cap.get("amount"):
        return ""
    parts = []
    if cap.get("basis"):
        parts.append(str(cap["basis"]).lower())
    if cap.get("applies_to"):
        parts.append(str(cap["applies_to"]))
    # Legacy caps carry no structured scope at all; Phase A raises every one of
    # them for review rather than guessing, and until that review lands the
    # honest display is to name the gap.
    if not cap.get("scope"):
        parts.append("scope not stated")
    return "; ".join(parts)


def second_amount_note(f: Dict) -> str:
    """A sentence for a record whose own wording names a larger, unstructured fee.

    PTF-RENDERER-FIDELITY-001 §8. Staybridge Suites Miamisburg publishes a $50
    scalar while its restriction text says $50 per pet for one to six nights
    and $150 per pet for seven or more. The comparison table suppresses the
    scalar outright; the profile, which shows the restriction text in full,
    keeps the figure but must not let it stand as the whole answer.

    Returns "" unless the canonical view proves a second relevant amount.

    The withholding decisions travel WITH the facts. Built from ``{"facts": f}``
    alone, the view saw an empty withheld map, so a record that had decided it
    could not publish its fee ladder looked, from in here, like a record with no
    ladder at all -- and its scalar printed as the whole charge. Four records
    across Cleveland and Dayton were in exactly that state.
    """
    view = canonical_view.build({"facts": f,
                                 "withheld_fields": f.get("_withheld") or {}})
    if view.fee_display_mode != "withhold_scalar" or not view.fee:
        return ""
    return ("The hotel's published wording states a further amount for longer "
            "stays; the figure above is not the whole charge.")


def _cats_state(f: Dict) -> str:
    """``accepted`` | ``prohibited`` | ``""`` for a legacy facts dict.

    ``cats_allowed`` is a committed boolean and mechanically safe to read; a
    prose species list that names cats is an affirmative mention. A page that
    says only "pets welcome" yields NEITHER -- generic pets never becomes
    dogs+cats, which is the discipline two markets recorded by hand and the
    renderer then discarded.
    """
    explicit = f.get("cats_allowed")
    if explicit in ("false", False):
        return enums.SPECIES_PROHIBITED
    if explicit in ("true", True):
        return enums.SPECIES_ACCEPTED
    if "cat" in str(f.get("species_allowed") or "").lower():
        return enums.SPECIES_ACCEPTED
    return ""


# Shown wherever a fee is withheld because the official source contradicts
# itself. Neutral by design: it reports the state of the source, blames no one,
# and points the reader at the recorded wording and the hotel.
FEE_CONFLICT_NOTICE = ("Official source contains conflicting pet-fee terms. "
                       "See the exact recorded policy wording or confirm with "
                       "the hotel.")

# Shown where a fee is withheld because the source states a RANGE or a
# conditional fee rather than a figure -- "75 to 150 dollars depending on
# length of stay". Deliberately NOT the conflict wording: nothing here
# contradicts anything. The source is clear and simply says more than a single
# number can carry, and saying "conflicting" would misdescribe the hotel.
FEE_RANGE_NOTICE = ("Official source gives a pet-fee range that depends on "
                    "the stay, not a single figure. See the exact recorded "
                    "policy wording or confirm with the hotel.")


def withheld_cell(f: Dict, path: str) -> Optional[Tuple[str, str]]:
    """``(text, css)`` for a table cell whose field was deliberately withheld.

    ``None`` -- not ``("", "")`` -- when the field carries no decision. An
    empty tuple is TRUTHY, so returning one made every ``withheld_cell(...) or
    fallback`` take the withheld branch and blanked the cell on all 156
    records. Caught by the rendered-diff gate, which is what it is for.
    """
    decision = (f.get("_withheld") or {}).get(path)
    if not decision:
        return None
    label = (decision.get("public_label")
             or canonical_view.WITHHELD_SHORT_LABELS.get(decision.get("reason_code", ""))
             or canonical_view.WITHHELD_GENERIC_LABEL)
    return (label, WITHHELD_CLS)


def _withheld_chip_label(f: Dict) -> str:
    """The comparison chip for a withheld fee.

    PTF-POLICY-SCHEMA-MIGRATION-001A: a reviewed decision may name its own
    label. "Range by stay" fits a $75-$150 spread and misdescribes a fee
    charged every three nights, which is one amount on a repeating cycle.
    """
    for key, generic in (("fee_conflict", "Source conflict"),
                         ("fee_withheld", "Range by stay")):
        marker = f.get(key)
        if not marker:
            continue
        own = marker.get("public_label") if isinstance(marker, dict) else ""
        return own or generic
    return ""


def fee_withheld_notice(f: Dict) -> str:
    """The right sentence for whichever reason the fee was withheld, or "".

    PTF-POLICY-SCHEMA-MIGRATION-001A. A reviewed withholding may carry its own
    sentence, and where it does the reader gets that instead of the generic
    one. "Official source contains conflicting pet-fee terms" is true of every
    contradiction in the corpus; it does not tell a guest that the conflict is
    between a nightly rate and a per-stay rate, which is the part they can put
    to the hotel.
    """
    for key, generic in (("fee_conflict", FEE_CONFLICT_NOTICE),
                         ("fee_withheld", FEE_RANGE_NOTICE)):
        marker = f.get(key)
        if not marker:
            continue
        own = marker.get("public_copy") if isinstance(marker, dict) else ""
        return own or generic
    return ""


def weight_phrase(f: Dict) -> str:
    """The weight limit as the source states it, exclusivity preserved.

    "Under 80 lbs" and "up to 80 lbs" are different promises: the first turns
    an 80-pound dog away, the second takes it. Rendering the first as
    "Maximum pet weight is 80 pounds" told owners of 80-pound dogs the hotel
    would accept them, which its own page denies.

    Absent operator means inclusive -- what every labelled "Maximum Pet
    Weight: N" has always meant -- so existing hotels read exactly as before.
    """
    value = (f.get("weight_limit") or "").strip()
    if not value:
        return ""
    op = f.get("weight_limit_operator") or ""
    if op == "lt":
        return "under %s" % _prose_number(value)
    if op == "combined":
        return "%s combined" % _prose_number(value)
    return _prose_number(value)


#: PTF-POLICY-PRECISION-001. Cell text for a dimension the property affirmatively
#: said it does not restrict. Deliberately names the property: a reader must be
#: able to tell "they told us there is no limit" from "we do not know", and the
#: dim "Not stated" used for silence cannot carry that difference.
UNRESTRICTED_WEIGHT_DISPLAY = "No restriction stated by the property"
UNRESTRICTED_BREED_DISPLAY = "None stated by the property"


def weight_display(f: Dict, *, combined_fallback: bool = False) -> str:
    """Table/chip form of the same limit: "Under 80.0 pounds", or "" if absent.

    Keeps the exact recorded value -- structured cells never round, only the
    running sentence does -- and carries the same exclusivity as the prose so
    the two can never disagree with each other.

    A source that states there is NO weight restriction gets its own cell text
    rather than the empty string, because an empty string renders as the same
    dim "Not stated" that silence renders as.
    """
    value = (f.get("weight_limit") or "").strip()
    if not value:
        if f.get("weight_limit_stated_none") == "true":
            return UNRESTRICTED_WEIGHT_DISPLAY
        # PTF-POLICY-SCHEMA-MIGRATION-001. A property may state ONLY a combined
        # limit -- Drury's two pages say "a combined weight of 80 pounds" and
        # never a per-pet maximum. Under the legacy shape that value sat in
        # weight_limit with the operator overloaded to "combined", so this cell
        # found it; 1.2 moves it to its own field, and without this branch the
        # summary cell told a reader the hotel stated no weight limit at all.
        # That is the opposite of what the page says.
        if combined_fallback and combined_weight_display(f):
            return "%s combined" % (f.get("weight_limit_combined") or "").strip()
        return ""
    op = f.get("weight_limit_operator") or ""
    if op == "lt":
        return "Under %s" % value
    if op == "combined":
        return "%s combined" % value
    if has_combined_weight(f):
        # A bare "50 pounds" beside a "75 pounds" row invites the reader to
        # wonder which applies to which. Only new-style records reach this
        # branch, so no existing page changes.
        return "%s per pet" % value
    return value


# --------------------------------------------------------------------------- #
# PTF-COLUMBUS-HYATT-002. Two weight limits at once.
#
# Every Hyatt page in the manual-evidence batch states BOTH "Individual pet
# weight limit: 50 Pounds" and "Combined pets weight limit: 75 Pounds". Those
# are different promises about different things -- one bounds each animal, the
# other bounds the pair -- and a schema with one `weight_limit` could only
# publish one of them. Publishing the 75 alone tells the owner of a 60 lb dog
# they are welcome; publishing the 50 alone hides that two 40 lb dogs are also
# refused. Neither is the page.
#
# The extension is additive and legacy-safe:
#
#   weight_limit / weight_limit_operator   the INDIVIDUAL limit, as always
#   weight_limit_combined                  the combined limit for all pets
#   weight_limit_combined_operator         "lt" (strict) or absent (inclusive)
#
# Records written before this -- including the three that express a combined
# limit the only way that used to exist, `weight_limit_operator == "combined"`
# -- carry neither new key and render byte-identically. That older form stays
# supported and stays mutually exclusive with the new one: a record may not
# say "combined" twice, and `weight_conflict_reason` refuses it.
# --------------------------------------------------------------------------- #

def has_combined_weight(f: Dict) -> bool:
    return bool((f.get("weight_limit_combined") or "").strip())


def combined_weight_display(f: Dict) -> str:
    """Table form of the combined limit, or "" if the record carries none."""
    value = (f.get("weight_limit_combined") or "").strip()
    if not value:
        return ""
    op = f.get("weight_limit_combined_operator") or ""
    lead = "Under %s" % value if op == "lt" else value
    return "%s for all pets together" % lead


def combined_weight_phrase(f: Dict) -> str:
    """Sentence form: "under 75 pounds" / "75 pounds"."""
    value = (f.get("weight_limit_combined") or "").strip()
    if not value:
        return ""
    op = f.get("weight_limit_combined_operator") or ""
    if op == "lt":
        return "under %s" % _prose_number(value)
    return _prose_number(value)


def weight_conflict_reason(f: Dict) -> str:
    """Why this record's weight fields cannot be published, or "".

    Fails closed on the one combination that would be read two ways. The old
    ``weight_limit_operator == "combined"`` form already means "this number
    bounds the pets together", so a record carrying it AND the new combined
    field is asserting two different combined ceilings, and there is no way to
    guess which the page meant.
    """
    if not has_combined_weight(f):
        return ""
    if (f.get("weight_limit_operator") or "") == "combined":
        return ("weight_limit_operator is 'combined' and weight_limit_combined "
                "is also set: the record states two different combined limits")
    op = f.get("weight_limit_combined_operator") or ""
    if op not in ("", "lt", "lte"):
        return "unsupported weight_limit_combined_operator %r" % op
    return ""


#: PTF-COLUMBUS-HYATT-002. A tier marked ``additive`` is charged ON TOP of the
#: tier before it rather than instead of it.
#:
#: Two Hyatt pages in the manual batch read "7-30 nights + additional cleaning
#: fee: $200 / STAY" while two others read "7-30 nights (includes cleaning
#: fee): $200 / STAY". Same number, opposite meaning: one is a surcharge on the
#: $100 already stated, the other is the whole price of the stay. Rendered the
#: same way, the first understates a long stay by the entire base fee.
#:
#: Absent means what it has always meant -- the tier amount IS the charge for
#: that band -- so every ladder published before this renders unchanged.
def _is_additive(t: Dict) -> bool:
    return bool(t.get("additive"))


def tier_fee_range(tiers: Sequence[Dict]) -> str:
    """"$75–$125" for a ladder; a single amount if every tier charges the same.

    An additive ladder is joined with "+" instead: "$100 + $200" says a longer
    stay pays both, without this function inventing the sum. Adding them would
    be arithmetic the source never performed, and the two Hyatt pages that
    state an additional fee do not state a total anywhere.

    Shared with the comparison table so one ladder cannot be summarised two
    different ways on two pages.
    """
    amounts = [_prose_number("$%s" % t.get("amount", "")) for t in tiers if t.get("amount")]
    if not amounts:
        return ""
    if any(_is_additive(t) for t in tiers):
        return " + ".join(amounts)
    lo = min(amounts, key=lambda a: float(a.lstrip("$")))
    hi = max(amounts, key=lambda a: float(a.lstrip("$")))
    return lo if lo == hi else "%s–%s" % (lo, hi)


def _tier_range_phrase(t: Dict) -> str:
    """"1-4 nights" -> "stays of 1-4 nights"; open-ended -> "5 nights or more"."""
    lo, hi = t.get("condition_min"), t.get("condition_max")
    unit = t.get("boundary_unit") or "nights"
    if hi is None:
        return "stays of %s %s or more" % (lo, unit)
    if lo == hi:
        return "stays of %s %s" % (lo, unit)
    return "stays of %s–%s %s" % (lo, hi, unit)


def _tier_amount(t: Dict) -> str:
    return _prose_number("$%s" % t.get("amount", ""))


def _tier_scope_phrase(t: Dict) -> str:
    """" per pet" when the source states that scope for THIS tier, else "".

    A per-pet charge and a per-room charge are the same number and different
    policies: a second dog doubles one and not the other. Shown only where the
    source states it -- a tier whose scope is unstated says nothing.

    PTF-RENDERER-FIDELITY-001. This compared against ``per_pet`` alone, and the
    corpus spells tier scope BOTH ways: ``'per_pet'`` once and ``'per pet'``
    twice. Hampton Inn Troy's ladder is per pet in both its tiers and rendered
    as though it were per room, so a two-dog stay read at half its price. The
    canonical translation is Phase A's, not a second table.
    """
    scope = enums.LEGACY_FEE_SCOPES.get(
        str(t.get("scope") or "").strip().lower(), "")
    if not scope:
        return ""
    return " %s" % canonical_view.SCOPE_WORDS[scope]


def _tier_basis_phrase(tiers) -> str:
    """" per stay" when EVERY tier records a source-stated basis, else "".

    All-or-nothing on purpose: a ladder whose rungs disagree about recurrence is
    not one this sentence can describe.
    """
    if not tiers or not all(t.get("basis_stated") for t in tiers):
        return ""
    stated = {(t.get("stated_basis") or "").strip().lower() for t in tiers}
    stated.discard("")
    if len(stated) != 1:
        return ""
    return " %s" % stated.pop()


# --------------------------------------------------------------------------- #
# PTF-RENDER refundability binding.
#
# A ladder priced $75 for a short stay and $125 for a long one may have only
# ONE of those amounts described as non-refundable by the source. Qualifying the
# whole sentence then makes a claim about the other tier that no wording
# supports. The amount the source actually names decides which tier carries the
# word, and an amount that resolves to no single tier withholds it entirely.
# --------------------------------------------------------------------------- #

_MONEY_RE = re.compile(
    r"\$\s*(?P<sym>\d[\d,]*(?:\.\d{1,2})?)"
    r"|(?P<bare>\d[\d,]*(?:\.\d{1,2})?)\s*(?:USD|dollars)\b", re.I)

# How far from the words "non-refundable" a figure may sit and still be read as
# the figure those words describe. Sources place it adjacent -- "Deposit  Yes.
# $125.00 Non-refundable Fee" before, "Non-Refundable Pet Fee Per Stay: $50.00"
# after -- while an unrelated tier or a weight sits further off.
_NONREFUNDABLE_WINDOW = 40

REFUND_NONE = "none"
REFUND_GENERIC = "generic"
REFUND_TIER = "tier"
REFUND_UNRESOLVED = "unresolved"


def _money_values(text: str) -> List[Tuple[Decimal, int, int]]:
    """``(value, start, end)`` for every currency figure in ``text``."""
    out: List[Tuple[Decimal, int, int]] = []
    for m in _MONEY_RE.finditer(text or ""):
        raw = m.group("sym") or m.group("bare") or ""
        try:
            out.append((Decimal(raw.replace(",", "")), m.start(), m.end()))
        except ArithmeticError:
            continue
    return out


def _amount_of(value) -> Optional[Decimal]:
    try:
        return Decimal(str(value).replace("$", "").replace(",", "").strip())
    except (ArithmeticError, AttributeError, TypeError, ValueError):
        return None


def refundability_amounts(evidence: str) -> Tuple[Decimal, ...]:
    """Every amount THIS record's wording states to be non-refundable.

    Each occurrence of "non-refundable" claims the currency figure nearest to
    it within a bounded window. Nearest wins because these sources write the
    figure against the words; a further-off figure belongs to something else.
    An occurrence with no figure in range contributes nothing, which is what
    lets a bare "non-refundable pet fee" stay generic.
    """
    text = evidence or ""
    money = _money_values(text)
    found: List[Decimal] = []
    for m in _NONREFUNDABLE_RE.finditer(text):
        best: Optional[Tuple[int, Decimal]] = None
        for value, start, end in money:
            if end <= m.start():
                gap = m.start() - end
            elif start >= m.end():
                gap = start - m.end()
            else:
                gap = 0
            if gap <= _NONREFUNDABLE_WINDOW and (best is None or gap < best[0]):
                best = (gap, value)
        if best is not None:
            found.append(best[1])
    return tuple(found)


def refundability_binding(tiers: Sequence[Dict],
                          evidence: str = "") -> Tuple[str, Tuple[str, ...]]:
    """Bind a non-refundable statement to the tier its own wording supports.

    ``(mode, amounts)`` where mode is:

      ``none``        the wording states no non-refundability;
      ``generic``     stated without naming a figure, so it describes the whole
                      schedule and renders on the leading tier as before;
      ``tier``        stated for exactly one figure matching exactly one tier;
      ``unresolved``  figures were named that do not resolve to a single tier
                      -- two contradictory ones, one matching no tier, or one
                      matching several. The qualifier is withheld rather than
                      attached to a tier the source never described.

    Only the evidence handed in is consulted, which is always a single record's
    own approved wording; nothing is shared between hotels.
    """
    if not _NONREFUNDABLE_RE.search(evidence or ""):
        return (REFUND_NONE, ())
    amounts = refundability_amounts(evidence)
    if not amounts:
        return (REFUND_GENERIC, ())
    distinct = sorted(set(amounts))
    if len(distinct) != 1:
        return (REFUND_UNRESOLVED, tuple(str(a) for a in distinct))
    target = distinct[0]
    matched = [t for t in (tiers or []) if _amount_of(t.get("amount")) == target]
    if len(matched) != 1:
        return (REFUND_UNRESOLVED, (str(target),))
    return (REFUND_TIER, (str(target),))


def _tiered_fee_sentence(tiers: Sequence[Dict], evidence: str = "") -> str:
    """A source-faithful sentence for a stay-length fee ladder.

    Deliberately states no basis. A field reading "$75(1-4n)$125(5+n)" gives an
    amount and a stay range and says nothing about recurrence -- calling it
    "per night" or "per stay" would invent the difference. Basis appears only
    where the source states one, carried on the tier as ``basis_stated``.

    Refundability is bound to the tier the source named, so a ladder whose
    upper rung is the non-refundable one says so on that rung.
    """
    if not tiers:
        return ""
    mode, amounts = refundability_binding(tiers, evidence)
    target = _amount_of(amounts[0]) if mode == REFUND_TIER else None

    def _binds(tier: Dict) -> bool:
        return mode == REFUND_TIER and _amount_of(tier.get("amount")) == target

    # Where the SOURCE states the recurrence -- "1-4 nights $75.00 per stay" --
    # it is carried through. Where it does not, nothing is said: an amount and a
    # stay range say nothing about whether the charge repeats.
    basis = _tier_basis_phrase(tiers)
    first, rest = tiers[0], tiers[1:]
    lead = "non-refundable " if (mode == REFUND_GENERIC or _binds(first)) else ""
    s = "A %spet fee of %s%s%s applies for %s" % (
        lead, _tier_amount(first), basis, _tier_scope_phrase(first),
        _tier_range_phrase(first))
    for t in rest:
        prefix = "a non-refundable pet fee of " if _binds(t) else ""
        # "an additional $200" and "$200" are the difference between a
        # surcharge and a replacement price. The word is the source's.
        if _is_additive(t):
            prefix = "an additional " + prefix if prefix else "an additional "
        s += ", and %s%s%s%s applies for %s" % (
            prefix, _tier_amount(t), basis, _tier_scope_phrase(t),
            _tier_range_phrase(t))
    return s + "."


# --------------------------------------------------------------------------- #
# PTF-FEES-PROSE rendering. Two dimensions the older fields cannot carry.
#
# A STAGED fee charges the first night at one rate and every night after it at
# another. There is no single "the fee": $45 is the price of exactly one night,
# and showing it alone understates every longer stay. Both stages render or
# neither does.
#
# A TIERED CEILING is a maximum that itself varies with stay length. It is not a
# fee ladder and must never be labelled as one -- at a property charging $25 a
# night under a $75 six-night ceiling, a one-night stay costs $25, and showing
# the $75 as a charge would treble it.
#
# Both fail closed: a half-stated schedule and a tier missing its amount or its
# stay window render nothing at all, which is the pre-existing outcome for a
# hotel carrying neither field.
# --------------------------------------------------------------------------- #

def _money_amount(block) -> str:
    """"$80" from a {amount, currency} block, matching how every other charge
    row prints money."""
    amount = str((block or {}).get("amount") or "").strip()
    return _prose_number("$%s" % amount) if amount else ""


def _per_pet_basis(block) -> str:
    """" per stay" / " per night" -- the basis the source stated, or nothing."""
    basis = str((block or {}).get("basis") or "").strip()
    return (" %s" % basis) if basis else ""


def staged_fee(f: Dict) -> Tuple[str, str]:
    """``(first night, each additional night)`` for prose, or ``("", "")``.

    Empty unless BOTH stages are stated. Half a schedule is not a schedule: the
    first night alone reads as the whole price, and the additional night alone
    says nothing about arriving.
    """
    schedule = f.get("fee_schedule")
    if not isinstance(schedule, dict):
        return ("", "")
    first = (schedule.get("first_night") or {}).get("amount") or ""
    additional = (schedule.get("additional_night") or {}).get("amount") or ""
    if not first or not additional:
        return ("", "")
    return (_prose_number("$%s" % first), _prose_number("$%s" % additional))


def cap_tiers(f: Dict) -> Tuple[Dict, ...]:
    """Usable ceiling tiers, in the order the source stated them.

    Empty if ANY tier is unusable. A ladder rendered with one rung missing tells
    a reader the ceiling for a stay length it never covered.
    """
    raw = f.get("fee_cap_tiers")
    if not isinstance(raw, (list, tuple)) or not raw:
        return ()
    for t in raw:
        if not isinstance(t, dict) or not t.get("amount"):
            return ()
        if t.get("min_nights") in (None, ""):
            return ()
    return tuple(raw)


def _cap_basis(cap: Dict) -> str:
    """" per stay" where the source stated a basis for the ceiling, else "".

    Never guessed. A ceiling with no stated basis is shown as a bare amount,
    which is what every ceiling recorded before this field said.
    """
    basis = (cap.get("basis") or "").strip()
    return " %s" % basis.lower() if basis else ""


def _cap_tier_range_phrase(t: Dict) -> str:
    """"stays of 1–6 nights", "stays of 7 or more nights"."""
    low, high = t.get("min_nights"), t.get("max_nights")
    if high in (None, "", 0):
        return "stays of %s or more nights" % low
    if high == low:
        return "stays of %s night%s" % (low, "" if str(low) == "1" else "s")
    return "stays of %s–%s nights" % (low, high)


def _cap_tier_amount(t: Dict) -> str:
    return _prose_number("$%s" % t.get("amount", "")) + _cap_basis(t)


def staged_fee_sentence(f: Dict, evidence: str = "") -> str:
    """Both stages in one sentence, with neither standing for the whole stay."""
    first, additional = staged_fee(f)
    if not first:
        return ""
    nonref = "non-refundable " if _NONREFUNDABLE_RE.search(evidence or "") else ""
    return ("A %spet fee of %s applies for the first night and %s for each "
            "additional night." % (nonref, first, additional))


def cap_tier_sentence(tiers: Sequence[Dict]) -> str:
    """The ceiling ladder, stated as a maximum and never as a charge."""
    if not tiers:
        return ""
    first, rest = tiers[0], tiers[1:]
    s = "A maximum of %s applies for %s" % (
        _cap_tier_amount(first), _cap_tier_range_phrase(first))
    for t in rest:
        s += ", and %s for %s" % (_cap_tier_amount(t), _cap_tier_range_phrase(t))
    return s + "."


#: A room-scoped nightly rate: "per night for up to 2 pets". Matched on the
#: STRUCTURED basis, so the wording follows the policy shape rather than the
#: property -- any hotel stating this basis reads the same way.
_ROOM_NIGHTLY_BASIS_RE = re.compile(
    r"^per\s+night\s+for\s+up\s+to\s+(?P<count>\d+)\s+pets?$")


def _qualifier_phrase(raw: str) -> str:
    """"for two (2) pets" -> "for two pets".

    Only the redundant numeral parenthetical is dropped; the qualifier itself is
    never reworded, because what it limits is the whole point of keeping it.
    """
    return " ".join(re.sub(r"\s*\(\s*\d+\s*\)", "", raw or "").split())


def _pets_phrase(count) -> str:
    """"2 pets" / "1 pet". A policy that permits one animal should not read
    "Up to 1 pets permitted per room"."""
    return "%s pet%s" % (count, "" if str(count).strip() == "1" else "s")


#: PTF-POLICY-PRECISION-001. The unit a pet count applies to. "Up to two pets
#: are permitted per suite" is what an all-suite property states, and calling it
#: a room changes the promise for a guest booking a multi-room suite. Only the
#: two units a source has actually stated are accepted.
_COUNT_SCOPES = ("room", "suite")


def _count_scope(f: Dict) -> Optional[str]:
    """The unit the source stated the count in, or None if it stated none.

    PTF-POLICY-SCHEMA-MIGRATION-001A. This used to return "room" for absence as
    well as for a stated room scope, so a property that wrote only "2 pets max"
    was published as "2 per room" -- a scope it never gave. Two-thirds of the
    corpus states a count without a unit, so the fabrication was the common
    case, not the edge one.

    It also made the authority untestable from the page: three records carrying
    an unsupported ``pet_count_scope: room`` were removed from the authority and
    their pages did not move, because the renderer put the same word back. The
    default is gone; absence now renders as absence.
    """
    scope = str(f.get("pet_count_scope") or "").strip().lower()
    return scope if scope in _COUNT_SCOPES else None


def _per_count_scope(f: Dict) -> str:
    """" per room" / " per suite" where the source stated one, else "".

    Returned with its leading space so a caller can append it to a sentence
    that has to read correctly with or without it.
    """
    scope = _count_scope(f)
    return " per %s" % scope if scope else ""


def _verified_summary(f: Dict[str, str], evidence: str = "") -> str:
    """Compose the consumer summary from stated facts plus the source wording.

    ``evidence`` is the recorded official quote. It is consulted only to decide
    between two phrasings the facts alone cannot distinguish -- combined versus
    per-pet weight, and whether a fee is non-refundable. Nothing is added to the
    summary that the quote does not support.
    """
    tiers = f.get("fee_tiers") or []
    conflict = f.get("fee_conflict") or f.get("fee_withheld")
    if not tiers and not conflict and not any(
            f.get(k) for k in _STATED_FIELDS):
        return ("Pets are welcome. The reviewed official source did not state the species, "
                "fee, pet limit, or weight limit.")
    parts = [_species_phrase(f.get("species_allowed", ""))]
    if conflict:
        # No amount and no basis. Either the source gives two incompatible
        # answers, or it gives a range no single figure can carry; the notice
        # says which, because they are different facts about the hotel.
        parts.append(fee_withheld_notice(f))
    if tiers:
        parts.append(_tiered_fee_sentence(tiers, evidence))
        # PTF-RENDERER-FIDELITY-001 §10. A ladder still has a scope, and a
        # per-pet ladder doubles for a second animal. Hampton Inn Troy states
        # $75/$125 PER PET and the ladder sentence alone never said so, so a
        # two-dog stay read as half its price. Said only where the record's own
        # scope field states it, and only where the tiers do not already carry
        # their own.
        tier_scope = canonical_fee_scope(f)
        if tier_scope and not any(t.get("scope") in ("per_room", "per_pet",
                                                     "per pet", "per room")
                                  for t in tiers):
            parts.append("Those amounts are charged %s."
                         % canonical_view.SCOPE_WORDS[tier_scope])
    # A staged schedule speaks for the whole fee, so no scalar may be shown
    # beside it -- two fee sentences on one page is the duplication guard, and
    # the scalar would be the first night's price wearing the stay's name.
    staged = staged_fee_sentence(f, evidence)
    tier_caps = cap_tiers(f)
    if staged:
        parts.append(staged)
        scalar_cap = f.get("fee_cap") or {}
        if scalar_cap.get("amount") and not tier_caps:
            parts.append("A maximum of %s%s applies." % (
                _prose_number("$%s" % scalar_cap["amount"]), _cap_basis(scalar_cap)))
    fee, basis = (None, None) if (tiers or conflict or staged) else (f.get("pet_fee"),
                                                                    f.get("fee_basis"))
    if fee:
        nonref = " non-refundable" if _NONREFUNDABLE_RE.search(evidence or "") else ""
        cap = f.get("fee_cap") or {}
        pending_cap_sentence = ""
        basis_unspecified = False
        scope_unstated = False
        room_nightly = _ROOM_NIGHTLY_BASIS_RE.match((basis or "").strip().lower())
        if room_nightly:
            # A nightly rate that covers a number of pets rather than charging
            # each one. Saying it directly avoids "applies per night for up to
            # 2 pets, up to a maximum of $75" -- two "up to" phrases for two
            # different quantities in one sentence.
            s = "A %s%s nightly fee covers up to %s pets" % (
                _prose_number(fee), nonref, room_nightly.group("count"))
            if cap.get("amount") and not tier_caps:
                s += " and is capped at %s per stay" % _prose_number(
                    "$%s" % cap["amount"])
        else:
            # PTF-POLICY-PRECISION-001. A stated amount with no stated basis is
            # genuinely ambiguous: $100 could be the whole stay or every night,
            # and the difference is the price of the trip. Where the source
            # states a basis nothing changes. Where it does not, the sentence
            # says so instead of letting "a $100 fee applies" read as a complete
            # answer -- and it still infers nothing: per stay, per night and per
            # pet all stay unsaid, because the source did not say them.
            # PTF-RENDERER-FIDELITY-001. Scope and basis are said together, in
            # that order, because they answer one question between them: what
            # does this cost me, for how long, and for how many animals. A
            # room-scoped fee is one charge however many pets arrive; a
            # per-pet fee doubles for two. Saying only the basis left a guest
            # with two dogs to guess which, and the guess is the price of the
            # trip.
            qualifier = fee_qualifier_phrase(f)
            scope = canonical_fee_scope(f)
            if qualifier:
                s = "A %s%s fee applies %s" % (_prose_number(fee), nonref, qualifier)
            else:
                s = "A %s%s pet fee is stated" % (_prose_number(fee), nonref)
                basis_unspecified = True
            if not scope and basis and str(f.get("pet_count_limit") or "") != "1":
                # The amount and its recurrence are known, the scope is not.
                # Saying so stops "$50 per night" reading as a complete answer
                # to a guest bringing two animals.
                #
                # Not said where the property allows exactly one pet: at one
                # animal, per-pet and per-room are the same arithmetic, so the
                # ambiguity cannot change any answer and the sentence would be
                # noise on a page that is already correct. This is the
                # computation contract's own case E, applied to prose.
                scope_unstated = True
            if cap.get("amount") and not tier_caps:
                # The ceiling belongs in the same sentence as the rate it caps
                # -- a reader who sees "$50 per night" and stops has the wrong
                # total.
                # The ceiling is stated with everything the source gave it.
                # "for two (2) pets" is a qualifier, not a per-pet charge: it
                # says what two animals cost at most and nothing about one.
                if cap.get("applies_to"):
                    # A ceiling that names how many animals it covers is stated
                    # separately and attributed, so it can never read as the
                    # price of one pet.
                    pending_cap_sentence = "The hotel states a maximum of %s%s %s." % (
                        _prose_number("$%s" % cap["amount"]),
                        (" %s" % cap["basis"].lower()) if cap.get("basis") else "",
                        _qualifier_phrase(cap["applies_to"]))
                else:
                    s += ", up to a maximum of %s%s" % (
                        _prose_number("$%s" % cap["amount"]),
                        (" %s" % cap["basis"].lower()) if cap.get("basis") else "")
        if basis_unspecified:
            tail = "; the fee basis is not specified."
        elif scope_unstated:
            # PTF-RENDERER-FIDELITY-001. The source gave an amount and a
            # recurrence and never said who it attaches to. A reader bringing
            # two animals cannot tell whether to double it, so the sentence
            # says that rather than letting the figure look complete.
            tail = ("; the source does not say whether this is charged per pet "
                    "or per room.")
        else:
            tail = "."
        parts.append(s + tail)
        # §8. Where the record's own wording carries a larger amount that never
        # reached a structured field, the figure above is not the whole charge
        # and the page says so rather than letting it look complete.
        second = second_amount_note(f)
        if second:
            parts.append(second)
        if pending_cap_sentence:
            parts.append(pending_cap_sentence)

    # PTF-REVIEW-B2. A per-ANIMAL ladder has no single fee, so the fee sentence
    # above never fires for it -- and without this branch the property rendered
    # as though it charged nothing at all. Each rung is stated in turn; the
    # second animal's price is explicitly ADDITIONAL, never multiplied.
    pet_schedule = f.get("fee_pet_schedule") or {}
    first_pet, second_pet = pet_schedule.get("first_pet"), pet_schedule.get("second_pet")
    if first_pet and second_pet and not conflict:
        parts.append("The first pet costs %s%s, and a second pet costs an "
                     "additional %s%s." % (
                         _prose_number("$%s" % first_pet["amount"]),
                         (" %s" % first_pet["basis"].lower()) if first_pet.get("basis") else "",
                         _prose_number("$%s" % second_pet["amount"]),
                         (" %s" % second_pet["basis"].lower()) if second_pet.get("basis") else ""))

    # A ceiling that varies with stay length gets its own sentence: it will not
    # fit inside the rate's, and it is a maximum rather than a charge.
    if tier_caps and not conflict:
        parts.append(cap_tier_sentence(tier_caps))

    count = f.get("pet_count_limit")
    weight = _prose_number(f.get("weight_limit", ""))
    weight_op = f.get("weight_limit_operator") or ""
    bound = f.get("species_weight_limits") or {}
    # weight_limit_operator == "combined" is the authoritative structured signal
    # (PTF-POLICY-P0-001's own vocabulary, already emitted by the Drury
    # adapter) and is trusted outright. The regex on raw evidence text is a
    # fallback used ONLY when no structured operator was recorded at all --
    # an explicit "lt" or "per_pet" from the source must never be second-
    # guessed by a word that happens to appear near the number for an
    # unrelated reason (housekeeping schedules, unrelated policy clauses).
    is_combined = (weight_op == "combined"
                   or (not weight_op
                       and _source_states_combined_weight(evidence, f.get("weight_limit", ""))))
    if bound:
        # Named animal, named ceiling, and silence about the rest -- because the
        # source limited one species and said nothing about the other. "Maximum
        # pet weight is 20 pounds" would invent the missing half.
        species, rule = sorted(bound.items())[0]
        parts.append("%s must weigh %s or less%s" % (
            _cap_first(species), _prose_number(rule.get("value", "")),
            (", with up to %s permitted%s." % (_pets_phrase(count), _per_count_scope(f)))
            if count else "."))
    elif weight and has_combined_weight(f):
        # Both limits stated. Both are said, in that order, and the combined
        # one is explicitly attributed to the pets together so it can never be
        # read as a per-animal ceiling.
        each = ("Each pet must weigh %s" % weight_phrase(f)
                if (f.get("weight_limit_operator") or "") == "lt"
                else "Each pet may weigh up to %s" % weight)
        parts.append("%s, with a combined limit of %s for %s." % (
            each, combined_weight_phrase(f),
            _pets_phrase(count) if count else "all pets together"))
    elif not weight and has_combined_weight(f):
        parts.append("A combined weight limit of %s applies%s."
                     % (combined_weight_phrase(f),
                        " for %s" % _pets_phrase(count) if count else ""))
    elif weight and is_combined:
        parts.append("Up to %s with a combined weight limit of %s."
                     % (_pets_phrase(count), weight)
                     if count else "A combined weight limit of %s applies." % weight)
    elif weight and (f.get("weight_limit_operator") or "") == "lt":
        # An exclusive ceiling gets a sentence that excludes: "under 80 pounds"
        # turns the 80-pound dog away, and "maximum ... is 80 pounds" does not.
        parts.append("Pets must weigh %s%s" % (
            weight_phrase(f),
            (", with up to %s permitted%s." % (_pets_phrase(count), _per_count_scope(f)))
            if count else "."))
    elif weight:
        parts.append("Maximum pet weight is %s%s" % (
            weight,
            (", with up to %s permitted%s." % (_pets_phrase(count), _per_count_scope(f)))
            if count else "."))
    elif count:
        # A source that says "No weight limit per pet" has stated a FACT, not
        # left a gap. Rendering it as silence would tell a reader the hotel was
        # unclear when it was explicit.
        if f.get("weight_limit_stated_none") == "true":
            # PTF-POLICY-PRECISION-001: the verb has to agree with the count.
            # This branch was written for the one-pet case and read "2 pets is
            # permitted" the first time a multi-pet property stated it.
            phrase = _cap_first(_pets_phrase(count).replace("1 pet", "One pet"))
            parts.append("%s %s permitted%s, with no pet weight limit "
                         "stated by the hotel."
                         % (phrase, "is" if phrase.startswith("One pet") else "are",
                            _per_count_scope(f)))
        elif f.get("fee_scope") == "per_room":
            # A room-scoped fee has just told the reader the charge covers the
            # room; the allowance sentence that follows it carries its verb so
            # the two read as one statement about the room rather than as a
            # heading and a fragment. Everywhere else the established phrasing
            # stands unchanged -- this is a wording choice for one path, not a
            # licence to reword every profile that states a count.
            phrase = _pets_phrase(count)
            parts.append("Up to %s %s permitted%s."
                         % (phrase, "is" if phrase.startswith("1 pet") else "are",
                            _per_count_scope(f)))
        else:
            parts.append("Up to %s permitted%s." % (_pets_phrase(count), _per_count_scope(f)))
    elif f.get("weight_limit_stated_none") == "true":
        parts.append("The hotel states no pet weight limit.")

    # A refundable pet deposit is a separate obligation from the fee: the guest
    # gets it back. Stated last so it can never be read as part of the price.
    deposit = f.get("pet_deposit") or {}
    if isinstance(deposit, dict) and deposit.get("amount"):
        parts.append("A separate refundable pet deposit of %s is also stated."
                     % _prose_number("$%s" % deposit["amount"]))
    return " ".join(parts)


def _breed_chip(f: Dict) -> Tuple[Tuple[str, str, str], ...]:
    """A breed chip ONLY where the property affirmatively stated it restricts no
    breeds (PTF-POLICY-PRECISION-001).

    Deliberately not emitted for silence, and not for a record that merely lists
    a restriction: adding a chip to every profile would rewrite pages that this
    work order must leave alone, and a dim "Not stated" breed row would add a
    line to say nothing.
    """
    if f.get("breed_restrictions_stated_none") == "true":
        return (("Breed restrictions", UNRESTRICTED_BREED_DISPLAY, ""),)
    return ()


def _verified_facts(f: Dict[str, str]) -> Tuple[Tuple[str, str, str], ...]:
    sp = (f.get("species_allowed") or "").lower()
    sparse = not any(f.get(k) for k in _STATED_FIELDS)
    def cell(v):
        return (v, "") if v else ("Not stated", "dim")
    if sparse:
        # Verified generic pet-friendly policy: pets are welcome, but the
        # reviewed source did NOT identify accepted species. Never infer
        # dogs/cats from a generic pets-allowed statement -- present the policy
        # itself plus an explicit "Not stated" species, not a fabricated "Dogs".
        head = (("Pet policy", "Pets welcome", "yes"), ("Species", "Not stated", "dim"))
    else:
        # PTF-RENDERER-FIDELITY-001. An explicit refusal is a FACT, and three
        # committed records carry one. Rendering "cats: not stated" for a
        # property whose own page says cats are not accepted tells a reader the
        # hotel was silent when it was clear, and sends someone travelling with
        # a cat to a hotel that will turn them away.
        cats_state = _cats_state(f)
        if cats_state == enums.SPECIES_PROHIBITED:
            cats_cell = ("Not allowed", "stop")
        elif cats_state == enums.SPECIES_ACCEPTED:
            cats_cell = ("Accepted", "yes")
        else:
            cats_cell = ("Not stated", "dim")
        head = (
            ("Dogs", *(("Accepted", "yes") if "dog" in sp else ("Not stated", "dim"))),
            ("Cats", *cats_cell),
        )
    tiers = f.get("fee_tiers") or []
    if f.get("fee_conflict") or f.get("fee_withheld"):
        # PTF-RENDERER-FIDELITY-001. Withheld, not silent -- these chips carry
        # the withheld class so a reader (and a stylesheet) can tell a fee the
        # hotel never mentioned from one whose own page contradicts itself.
        return head + (
            ("Pet charge", "See policy wording", WITHHELD_CLS),
            ("Charge basis", _withheld_chip_label(f), WITHHELD_CLS),
            ("Max pets", *cell(f.get("pet_count_limit"))),
            ("Weight limit", *(withheld_cell(f, "weight_limit")
                              or cell(weight_display(f, combined_fallback=True)))),
        ) + _breed_chip(f)
    if tiers:
        # A ladder has no single charge and no stated basis, so the chips say
        # the range and name the reason rather than showing one number.
        return head + (
            ("Pet charge", tier_fee_range(tiers), ""),
            ("Charge basis", "Tiered by stay length", "sm"),
            ("Max pets", *cell(f.get("pet_count_limit"))),
            ("Weight limit", *(withheld_cell(f, "weight_limit")
                              or cell(weight_display(f, combined_fallback=True)))),
        ) + _breed_chip(f)
    # A staged fee has no single charge, so the chip names both stages rather
    # than the first night's price standing in for the stay.
    first_night, additional_night = staged_fee(f)
    if first_night:
        return head + (
            ("Pet charge", "%s first night, then %s" % (first_night, additional_night), ""),
            ("Charge basis", "Staged by night", "sm"),
            ("Max pets", *cell(f.get("pet_count_limit"))),
            ("Weight limit", *(withheld_cell(f, "weight_limit")
                              or cell(weight_display(f, combined_fallback=True)))),
        ) + _breed_chip(f)
    cap = (f.get("fee_cap") or {}).get("amount")
    charge = f.get("pet_fee")
    # A ceiling only ever LOWERS a total, so leaving a tiered one out of the
    # compact chip cannot overstate what a guest pays -- and putting "$75–$150"
    # beside a $25 rate invites reading the ceiling as the charge. The tiers are
    # stated in full in the summary and the detail table.
    if charge and cap and not cap_tiers(f):
        charge = "%s (max %s)" % (charge, _prose_number("$%s" % cap))
    # PTF-RENDERER-FIDELITY-001. The basis chip carries the SCOPE too. "Per
    # night" beside a $15 charge is a different promise from "Per pet per
    # night", and eight Dayton properties charge the second while the chip said
    # the first.
    qualifier = fee_qualifier_phrase(f)
    return head + (
        ("Pet charge", *cell(charge)),
        ("Charge basis", *((_cap_first(qualifier), "sm") if qualifier
                           else ("Not stated", "dim"))),
        ("Max pets", *cell(f.get("pet_count_limit"))),
        ("Weight limit", *(withheld_cell(f, "weight_limit")
                              or cell(weight_display(f, combined_fallback=True)))),
    ) + _breed_chip(f)


class PolicyRenderError(ValueError):
    """A fact value the details table has no agreed way to display."""


#: Species in a fixed order, so a page never reorders itself between builds.
_SPECIES_ROW_ORDER = ("dogs", "cats", "birds", "fish")
_SPECIES_SINGULAR = {"dogs": "Dogs", "cats": "Cats", "birds": "Birds", "fish": "Fish"}

#: The structured fact schemas the details table understands. A dict outside
#: this set is a fact somebody added without deciding how a guest should read it,
#: and guessing on their behalf is how "{'amount': '150.00'}" reaches a page.
_MONEY_KEYS = {"amount", "currency", "basis", "evidence_quote", "applies_to"}


def _money_fact(field: str, value: Dict, hotel_key: str) -> str:
    """``$150 per stay`` from an approved money object. Amount is mandatory."""
    unknown = set(value) - _MONEY_KEYS
    if unknown or not str(value.get("amount", "")).strip():
        raise PolicyRenderError(
            "unrenderable_fact hotel=%s field=%s shape=%s"
            % (hotel_key, field, sorted(value)))
    out = _prose_number("$%s" % value["amount"])
    basis = str(value.get("basis") or "").strip()
    if basis:
        out += " %s" % basis.lower()
    return out


def _species_weight_fact(field: str, value: Dict, hotel_key: str) -> str:
    """``Cats: maximum 20 pounds`` -- and silence about every other species.

    A species the source did not limit gets no sentence here. Rendering "Dogs:
    not stated" beside it would read as a restriction the hotel never wrote, and
    the whole reason this fact is structured is that "Dogs and 20-lb. cats"
    limits exactly one of them.
    """
    parts = []
    for species in _SPECIES_ROW_ORDER:
        rule = value.get(species)
        if rule is None:
            continue
        if not isinstance(rule, dict) or not str(rule.get("value", "")).strip():
            raise PolicyRenderError(
                "unrenderable_fact hotel=%s field=%s species=%s shape=%r"
                % (hotel_key, field, species, rule))
        parts.append("%s: maximum %s" % (_SPECIES_SINGULAR[species],
                                         str(rule["value"]).strip()))
    unknown = set(value) - set(_SPECIES_ROW_ORDER)
    if unknown or not parts:
        raise PolicyRenderError("unrenderable_fact hotel=%s field=%s shape=%s"
                                % (hotel_key, field, sorted(value)))
    return "; ".join(parts)


def format_fact_value(field: str, value, *, hotel_key: str = "") -> str:
    """The one place a fact value becomes display text. Fails closed.

    Scalars pass through unchanged so every existing page stays byte-identical.
    Structured values are rendered only where a schema has been agreed; anything
    else raises with the hotel and field named, because a silent omission hides a
    fact a reviewer approved and ``str(dict)`` publishes Python syntax.

    Returns UNESCAPED text: escaping belongs to the template, once, at the leaf.
    """
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (str, int, float, Decimal)):
        return str(value)
    if isinstance(value, dict):
        if field == "species_weight_limits":
            return _species_weight_fact(field, value, hotel_key)
        if field in ("pet_deposit", "fee_cap"):
            return _money_fact(field, value, hotel_key)
    raise PolicyRenderError("unrenderable_fact hotel=%s field=%s type=%s"
                            % (hotel_key, field, type(value).__name__))


#: Fields a reader looks for on a profile, in the order the detail table lists
#: them, mapped to the label a withheld row carries. Only these produce a
#: withheld row: a decision recorded against a field the profile never shows
#: would add a line about something the page does not otherwise discuss.
_WITHHELD_ROW_LABELS = (
    ("pet_fee", "Pet charge"),
    ("pet_fee.scope", "Pet charge"),
    ("fee_basis", "Charge basis"),
    ("fee_scope", "Charge basis"),
    ("fee_tiers", "Pet charge"),
    ("pet_deposit", "Refundable deposit"),
    ("cleaning_fee", "Cleaning fee"),
    ("species_allowed", "Accepted species"),
    ("cats_allowed", "Cats"),
    ("weight_limit", "Weight restriction"),
    ("weight_limit_combined", "Combined weight limit"),
    ("weight_limit_operator", "Weight restriction"),
    ("pet_count_limit", "Maximum pets"),
    ("pet_count_scope", "Maximum pets"),
)


def withheld_rows(record: Optional[Dict]) -> Tuple[Tuple[str, str, str], ...]:
    """Detail rows for every field this record deliberately does not publish.

    PTF-RENDERER-FIDELITY-001. ``withheld_fields`` was written by six
    integration scripts and read by none, so Cleveland's twenty and Dayton's
    forty-six withholding decisions reached the public as the generic dim "Not
    stated by the reviewed source" -- telling a reader the hotel was silent
    about a fee whose own page contradicts itself.

    Rows are emitted only for fields the profile otherwise discusses, only when
    the field is genuinely absent from the published facts, and never with the
    silence copy.

    A REASON CODE IS REQUIRED
    -------------------------
    Sixty-six of the committed entries are flat prose with no reason code, and
    they are not all the same kind of thing. Cleveland Marriott's reads "dogs
    are named; cats are not, and absence is not a refusal to publish either
    way" -- that is SILENCE, and telling a reader the hotel's wording could not
    be summarised would be a worse falsehood than the "Not stated" it replaces.
    Dayton's "the page states no pet count" is silence too.

    Classifying them means reading the sentence, which is Phase F review work
    and cannot be guessed here. So an entry without a reason code renders
    exactly as it does today -- as silence -- and only decisions carrying a
    machine-readable reason are surfaced as withheld. The distinction is fully
    implemented; what limits its reach is the data, and that limit is reported
    rather than papered over.
    """
    if not record:
        return ()
    view = canonical_view.build(record)
    facts = record.get("facts") or {}
    # The fee-specific branch above already renders its own withheld rows;
    # emitting ours as well states the same withholding twice.
    #
    # PTF-POLICY-SCHEMA-MIGRATION-001A: read this from the DISPLAY projection,
    # not the canonical facts. 1.2 replaced the two legacy markers with a
    # reason-coded decision, so `facts.get("fee_conflict")` became permanently
    # False and every conflicted record printed its sentence twice -- once as
    # "Charge basis" and again as "Pet charge".
    shown = canonical_view.display_facts(record)
    legacy_fee_withheld = bool(shown.get("fee_conflict") or shown.get("fee_withheld"))
    out = []
    seen = set()
    for path, label in _WITHHELD_ROW_LABELS:
        if path not in view.withheld or label in seen:
            continue
        if not view.withheld_reason_code(path):
            continue
        if legacy_fee_withheld and label in ("Pet charge", "Charge basis"):
            continue
        # A field that IS published is not withheld, whatever the map says.
        root = path.split(".", 1)[0]
        if root in facts and "." not in path:
            continue
        out.append((label, view.withheld_copy(path), WITHHELD_CLS))
        seen.add(label)
    return tuple(out)


def service_animal_rows(record: Optional[Dict]) -> Tuple[Tuple[str, str, str], ...]:
    """The property's own service-animal statement, if it made one.

    Kept apart from the pet-policy rows on purpose: a service animal is a legal
    access category, not a commercial term, and a weight limit sitting beside
    it invites a reader to apply one to the other. Six committed records carry
    a statement that has never reached a page.

    Nothing is invented. Where the compatibility view cannot recover a
    source-backed statement, no row appears.
    """
    if not record:
        return ()
    view = canonical_view.build(record)
    if not view.has_service_animal_statement:
        return ()
    # PTF-POLICY-SCHEMA-MIGRATION-001. The legacy field was a bare boolean, so
    # this row could only say "welcome" whatever the property had written.
    # Migrated records carry what the property said about CHARGES, and several
    # say it plainly -- Drury's two pages read "Service animals are free of
    # charge" -- so the row now reports that instead of rounding it off. A
    # record whose source did not address charges keeps the original sentence:
    # silence about a fee is not a statement that none applies.
    charges = str(view.service_animal.get("charges_stated") or "")
    if charges == enums.SERVICE_ANIMAL_NO_CHARGE:
        copy = "The property states that service animals are welcome at no charge."
    elif charges == enums.SERVICE_ANIMAL_CHARGE_STATED:
        copy = ("The property states that service animals are welcome and that a "
                "charge applies.")
    else:
        copy = "The property states that service animals are welcome."
    return (("Property statement on service animals", copy, ""),)


def _verified_details(f: Dict[str, str],
                      record: Optional[Dict] = None) -> Tuple[Tuple, str, str]:
    sparse = not any(f.get(k) for k in _STATED_FIELDS)
    svc = "A separate legal access category — not treated as a pet-policy exception."
    if sparse:
        # Any prose the property DID state, kept in its own row rather than
        # collapsed into "Breed / unattended rules: Not stated" beneath it.
        stated = tuple((_RESTRICTION_LABELS[k], f[k], "")
                       for k in _RESTRICTION_FIELDS if f.get(k))
        rows = (
            ("Accepted species", "Pets welcome (species not specified)", ""),
            ("Fee, pet limit, weight limit", _NOT_STATED, "dim"),
        ) + (stated or (("Breed / unattended rules", _NOT_STATED, "dim"),)) + (
            *withheld_rows(record),
            *service_animal_rows(record),
            ("Service animals", svc, ""),
        )
        note = ("“Not stated” means the reviewed source did not address the field — not that "
                "the answer is no. Confirm specifics with the property before booking.")
        return rows, "", note
    def d(v):
        return (v, "") if v else (_NOT_STATED, "dim")

    # Charge rows, in strict precedence: a staged schedule, then a tier ladder,
    # then a withheld fee, then the scalar. Exactly one of these speaks, so no
    # page can carry two accounts of the same money.
    first_night, additional_night = staged_fee(f)
    tier_caps = cap_tiers(f)
    per_pet = f.get("fee_pet_schedule") or {}
    if first_night:
        charge_rows = (("Pet charge, first night", first_night, ""),
                       ("Pet charge, each additional night", additional_night, ""))
    elif per_pet.get("first_pet") or per_pet.get("second_pet"):
        # PTF-COLUMBUS-FINAL-CLOSURE-001. fee_pet_schedule reached the SUMMARY
        # ("the first pet costs $80 per stay, and a second pet costs an
        # additional $50") and never reached this table, so Hilton Columbus
        # Polaris has been publishing "Pet charge: Not stated by the reviewed
        # source" directly beneath a sentence stating it. One live page is
        # corrected by this and two more avoid inheriting the same contradiction.
        charge_rows = tuple(
            ("Pet charge, %s pet" % label,
             _money_amount(per_pet[key]) + _per_pet_basis(per_pet[key]), "")
            for key, label in (("first_pet", "first"), ("second_pet", "second"))
            if per_pet.get(key))
    elif f.get("fee_tiers"):
        # PTF-COLUMBUS-HYATT-002: the row has to carry "additional" too. The
        # summary and the chip both say a 7-30 night stay pays $100 AND $200,
        # but a reader scanning only this table saw "Pet charge, 7-30 nights:
        # $200" and would read the surcharge as the price of the band.
        charge_rows = tuple(
            ("Pet charge, %s" % _tier_range_phrase(t).replace("stays of ", ""),
             _tier_amount(t) + _tier_scope_phrase(t)
             + (" additional" if _is_additive(t) else ""), "")
            for t in f["fee_tiers"])
    elif f.get("fee_conflict") or f.get("fee_withheld"):
        charge_rows = (("Pet charge", fee_withheld_notice(f), "dim"),)
    else:
        charge_rows = (("Pet charge", *d(f.get("pet_fee"))),)

    scalar_cap = f.get("fee_cap") or {}
    if tier_caps:
        maximum_rows = tuple(
            ("Maximum total, %s" % _cap_tier_range_phrase(t), _cap_tier_amount(t), "")
            for t in tier_caps)
    elif scalar_cap.get("amount") and not (f.get("fee_conflict") or f.get("fee_withheld")):
        maximum_rows = (("Maximum total",
                         _prose_number("$%s" % scalar_cap["amount"])
                         + _cap_basis(scalar_cap), ""),)
    else:
        maximum_rows = ()

    # PTF-RENDERER-FIDELITY-001. A stated refusal gets its own row. Three
    # committed records say cats are not accepted, and folding that into the
    # accepted-species sentence (or omitting it) let a traveller with a cat
    # read a hotel that will turn them away as merely unspecific.
    cats_state = _cats_state(f)
    species_rows = (
        ("Accepted species", *(lambda v: (_cap_first(v), "") if v else (_NOT_STATED, "dim"))(f.get("species_allowed"))),
    )
    if cats_state == enums.SPECIES_PROHIBITED:
        species_rows += (("Cats", "Not accepted by the property", "stop"),)

    rows = (
        *species_rows,
        # The detail table has to name the same unit the summary does. It said
        # "per room" for every record, so an all-suite property read "2 pets are
        # permitted per suite" in the sentence and "2 per room" in the table on
        # the same page. Where the source stated no unit, neither does the row.
        ("Maximum pets", *(lambda v: ("%s%s" % (v, _per_count_scope(f)), "")
                           if v else (_NOT_STATED, "dim"))(f.get("pet_count_limit"))),
        *charge_rows,
        *maximum_rows,
        ("Charge basis",
         *(("Tiered by stay length; the source does not state a per-night or "
            "per-stay basis.", "") if f.get("fee_tiers")
           else ("Staged: the first night is charged at a different rate from "
                 "each additional night.", "") if first_night
           # PTF-POLICY-SCHEMA-MIGRATION-001A. When a fee is withheld the row
           # above already carries the full explanation, so this one carries
           # the short form. Printing the same sentence twice in one table
           # reads as a rendering fault, not as emphasis -- and the generic
           # text it replaced was wrong on at least one record: a fee charged
           # "every 3 nights" is not a range, and calling it one sent a reader
           # looking for two numbers that do not exist.
           else ("Withheld: %s." % _withheld_chip_label(f).rstrip("."),
                 WITHHELD_CLS)
           if f.get("fee_conflict") or f.get("fee_withheld")
           # PTF-RENDERER-FIDELITY-001. Scope travels with the basis, and where
           # the source gave an amount and a recurrence but never said who it
           # attaches to, the row says that rather than showing half a rule as
           # though it were the whole one.
           else (_cap_first(fee_qualifier_phrase(f)), "")
           if fee_qualifier_phrase(f) and canonical_fee_scope(f)
           # Compact in a table cell; the summary sentence above states the
           # same gap in full. Suppressed at a one-pet limit, where per-pet and
           # per-room are the same arithmetic.
           else (_cap_first(fee_qualifier_phrase(f))
                 + " (per pet or per room not stated)", "")
           if fee_qualifier_phrase(f) and str(f.get("pet_count_limit") or "") != "1"
           else (_cap_first(fee_qualifier_phrase(f)), "")
           if fee_qualifier_phrase(f)
           else (_NOT_STATED, "dim"))),
        # Relabelled only where a combined limit sits beside it: two rows both
        # called "weight" with different numbers is exactly the ambiguity this
        # schema exists to remove. Records without a combined limit keep the
        # original label and are byte-identical.
        ("Individual weight limit" if has_combined_weight(f) else "Weight restriction",
         *d(weight_display(f))),
        *((("Combined weight limit", combined_weight_display(f), ""),)
          if has_combined_weight(f) else ()),
        # Emitted ONLY where the source limited one species. A dim "not
        # stated" row on every other profile would add a line to 38 live
        # pages to say nothing.
        *((("Species-specific weight limits",
            format_fact_value("species_weight_limits", f["species_weight_limits"],
                              hotel_key=f.get("_hotel_key", "")), ""),)
          if f.get("species_weight_limits") else ()),
        ("Refundable deposit",
         *d(format_fact_value("pet_deposit", f.get("pet_deposit"),
                              hotel_key=f.get("_hotel_key", "")))),
        # PTF-RENDERER-FIDELITY-001 §18. A cleaning fee is a SEPARATE charge,
        # never a pet-fee tier and never summed into a displayed total. One
        # committed record carries one and it reached no surface at all.
        # Refundability is not asserted: the legacy shape is a bare amount, and
        # inferring it from a heading is how "Deposit Yes. $75 Non-refundable
        # Fee" becomes a refundable deposit.
        *((("Cleaning fee", _prose_number(str(f["cleaning_fee"])), ""),)
          if f.get("cleaning_fee") else ()),
        ("Breed restrictions",
         *((UNRESTRICTED_BREED_DISPLAY, "")
           if f.get("breed_restrictions_stated_none") == "true"
           else d(f.get("breed_restrictions")))),
        ("Unattended-pet rule", *d(f.get("unattended_policy"))),
        # Additive rows, each omitted entirely (not a dim "Not stated") when
        # absent -- these four fields are new to the render layer and none of
        # the 77 currently-published records populate more than one of them,
        # so an unconditional row would print "Not stated" on every existing
        # page for a fact no source was ever asked about. Emitting the row
        # only when the field is present keeps every hotel that lacks it
        # byte-identical to today's output.
        *((("Other restrictions", f["general_restrictions"], ""),)
          if f.get("general_restrictions") else ()),
        *((("Pet room availability", f["pet_room_restriction"], ""),)
          if f.get("pet_room_restriction") else ()),
        *((("Eligible room types", f["eligible_room_types"], ""),)
          if f.get("eligible_room_types") else ()),
        *((("Reservation requirement", f["reservation_requirement"], ""),)
          if f.get("reservation_requirement") else ()),
        # Deliberately withheld facts, then the property's own service-animal
        # statement, then the site's standing legal line. The order matters: a
        # withholding decision belongs beside the policy it concerns, and the
        # legal category stays last and separate so nothing above it reads as
        # applying to a service animal.
        *withheld_rows(record),
        *service_animal_rows(record),
        ("Service animals", svc, ""),
    )
    # PTF-POLICY-SCHEMA-MIGRATION-001. A withheld row and a "Not stated" row
    # under the SAME label are a page contradicting itself: Days Inn showed
    # "Refundable deposit -- Not stated by the reviewed source" immediately
    # above "Refundable deposit -- The hotel's wording is unclear on this."
    # Before Phase F no record could reach this state, because no withholding
    # carried a reason code. The withheld row wins: it is the more specific and
    # the more truthful of the two.
    withheld_labels = {label for label, _, _ in withheld_rows(record)}
    rows = tuple(row for row in rows
                 if not (row[0] in withheld_labels and row[2] == "dim"))
    return rows, "", ""


# --------------------------------------------------------------------------- #
# Adapters.
# --------------------------------------------------------------------------- #

def _related_from_production(self_name: str, all_hotel_rows, facts_map, limit=3,
                             market_id: str = None) -> Tuple[RelatedHotel, ...]:
    # PTF-MULTI-MARKET-ASSEMBLER-001. The related-hotel route was slugged here
    # directly, which is only correct for a legacy_unprefixed market. Every
    # Dayton and Cleveland profile therefore carried three links into a
    # namespace that market does not publish. The market's own route helper is
    # the single authority on where a hotel page lives, so ask it.
    from scripts.pettripfinder.markets import hotel_route
    market, _ = _market_display_context(market_id)
    out = []
    for row in sorted(all_hotel_rows, key=lambda r: normalize_name(r["name"])):
        if normalize_name(row["name"]) == normalize_name(self_name):
            continue
        fe = facts_map.get(normalize_name(row["name"]))
        fact = _related_fact(canonical_view.display_facts(fe)) if fe else ""
        date = _friendly_date((fe["verified_at"] if fe else "") or row.get("observed_at", ""))
        out.append(RelatedHotel(
            name=row["name"],
            area=_corridor_area(row.get("city", ""), row["name"], market_id),
            fact=fact, verified_at=date,
            route=hotel_route(market, row["name"])))
        if len(out) >= limit:
            break
    return tuple(out)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def build_vm_from_production(row: Dict[str, str], facts_entry: Optional[Dict],
                            all_hotel_rows, facts_map,
                            market_id: str = None) -> HotelProfileVM:
    """Verified pet-friendly VM from a production seed row + its READY-candidate
    facts. Rich when the candidate stated fee/species/limits; sparse when it
    stated only that pets are welcome. Never invents a field."""
    # PTF-POLICY-SCHEMA-MIGRATION-001. Display values, whichever schema the
    # authority speaks. A legacy record passes through untouched; a migrated
    # one is projected from its canonical structures.
    f = canonical_view.display_facts(facts_entry)
    date = _friendly_date((facts_entry or {}).get("verified_at", "") or row.get("observed_at", ""))
    # The record, not just its facts: withholding decisions and the property's
    # service-animal statement live at record level and the detail table could
    # not see them before.
    rows, plain, note = _verified_details(f, facts_entry)
    # exact wording, carried on the fixture facts entry (committed, reproducible)
    quote = (facts_entry or {}).get("evidence_quote") if facts_entry else None
    return HotelProfileVM(
        state=STATE_VERIFIED, name=row["name"],
        corridor=_corridor_label(row.get("city", ""), row["name"], market_id),
        initials=_initials(row["name"]),
        address="%s, %s, %s %s" % (row.get("address", ""), row.get("city", ""), row.get("state", ""), row.get("postal_code", "")),
        phone=row.get("phone", ""), official_url=row.get("website_url", ""),
        verified_at=date, source_name="the official %s website" % _brand_of(row.get("website_url", "")),
        summary=_verified_summary(f, quote or ""),
        facts=_verified_facts(f),
        verif_badge_text="Policy verified · %s" % date, verif_badge_cls="ok", verif_chip="✓ Verified policy",
        trust_cls="ok",
        trust_line="Policy verified %s from %s." % (date, "the official %s website" % _brand_of(row.get("website_url", ""))),
        evidence_quote=quote,
        details_rows=rows, details_plain=plain, details_note=note,
        actions_mode="book",
        related=_related_from_production(row["name"], all_hotel_rows, facts_map,
                                         market_id=market_id),
        source_url=((facts_entry or {}).get("source_url", "") if facts_entry else ""))


def build_vm_from_no_pets(cand: Dict, all_hotel_rows, facts_map) -> HotelProfileVM:
    proposed = dict(cand.get("proposed_fields", []))
    name = proposed.get("name") or cand["context"]["candidate_name"]
    city = proposed.get("city") or cand["context"]["expected_city"]
    date = _friendly_date(cand.get("snapshot", {}).get("observed_at", ""))
    quote = next((e["snapshot_quote"] for e in cand.get("evidence", [])
                  if e["field_name"] == "pets_allowed"), None)
    facts = (
        ("Dogs", "Not accepted", "no"), ("Cats", "Not accepted", "no"),
        ("Pet charge", "Does not apply", "dim"), ("Charge basis", "Does not apply", "dim"),
        ("Max pets", "Does not apply", "dim"), ("Weight limit", "Does not apply", "dim"),
    )
    return HotelProfileVM(
        state=STATE_NO_PETS, name=name, corridor=_corridor_label(city, name),
        initials=_initials(name),
        address="%s, %s, OH" % (proposed.get("address", ""), city),
        phone="", official_url=proposed.get("website_url", "") or cand.get("snapshot", {}).get("requested_url", ""),
        verified_at=date, source_name="the official property website",
        summary=("This property does <b>not</b> accept pets. We’re showing it so you can rule it "
                 "out and find a stay that welcomes your dog or cat."),
        facts=facts,
        verif_badge_text="Verified · Pets not accepted", verif_badge_cls="stop", verif_chip="Pets not accepted",
        trust_cls="stop",
        trust_line="Verified %s from the official property website: pets are not accepted." % date,
        evidence_quote=quote,
        details_plain=("Pets are not accepted at this property, so there is no fee, pet limit, or "
                       "weight allowance to show."),
        service_note=("The official source states service animals are welcome. Service animals are a "
                      "legal access category under the ADA — not a pet-policy exception — and we "
                      "never present them as one."),
        actions_mode="alt",
        related=_related_from_production(name, all_hotel_rows, facts_map))


def build_vm_from_unverified(cand: Dict, all_hotel_rows, facts_map) -> HotelProfileVM:
    name = cand["context"]["candidate_name"]
    city = cand["context"]["expected_city"]
    facts = tuple((lbl, "Not verified", "dim") for lbl in
                  ("Dogs", "Cats", "Pet charge", "Charge basis", "Max pets", "Weight limit"))
    return HotelProfileVM(
        state=STATE_UNVERIFIED, name=name, corridor=_corridor_label(city, name),
        initials=_initials(name),
        address="%s, OH" % city,
        phone="", official_url=cand.get("snapshot", {}).get("requested_url", ""),
        verified_at=None, source_name=None,
        summary=("We could not confirm this property’s current pet policy from an approved "
                 "official source."),
        facts=facts,
        verif_badge_text="Pet policy not verified", verif_badge_cls="neutral", verif_chip="Not verified",
        trust_cls="neutral",
        trust_line=("We could not confirm this property’s current pet policy from an approved "
                    "official source."),
        evidence_quote=None,
        details_plain=("No verified pet-policy details are available for this property. Please "
                       "confirm directly with the property before you travel with a pet."),
        prov_status="not verified",
        actions_mode="unverif",
        related=_related_from_production(name, all_hotel_rows, facts_map))


def build_vm_from_production_unverified(row: Dict[str, str], all_hotel_rows, facts_map,
                                        market_id: str = None) -> HotelProfileVM:
    """POLICY_UNVERIFIED VM for a real production seed row that has no verified
    facts. Identical honest wording to build_vm_from_unverified, but keeps the
    row's real identity (full address + phone + official URL) instead of the
    address-less fixture-candidate shape -- so a production unverified hotel
    still shows its correct location and contact, never asserting a pet policy."""
    name = row["name"]
    facts = tuple((lbl, "Not verified", "dim") for lbl in
                  ("Dogs", "Cats", "Pet charge", "Charge basis", "Max pets", "Weight limit"))
    return HotelProfileVM(
        state=STATE_UNVERIFIED, name=name,
        corridor=_corridor_label(row.get("city", ""), name, market_id),
        initials=_initials(name),
        address="%s, %s, %s %s" % (row.get("address", ""), row.get("city", ""),
                                   row.get("state", ""), row.get("postal_code", "")),
        phone=row.get("phone", ""), official_url=row.get("website_url", ""),
        verified_at=None, source_name=None,
        summary=("We could not confirm this property’s current pet policy from an approved "
                 "official source."),
        facts=facts,
        verif_badge_text="Pet policy not verified", verif_badge_cls="neutral", verif_chip="Not verified",
        trust_cls="neutral",
        trust_line=("We could not confirm this property’s current pet policy from an approved "
                    "official source."),
        evidence_quote=None,
        details_plain=("No verified pet-policy details are available for this property. Please "
                       "confirm directly with the property before you travel with a pet."),
        prov_status="not verified",
        actions_mode="unverif",
        related=_related_from_production(name, all_hotel_rows, facts_map,
                                         market_id=market_id))


_BRAND_MAP = {"druryhotels.com": "Drury Hotels", "daysinncolumbusohio.com": "Days Inn",
              "sonesta.com": "Sonesta", "wyndhamhotels.com": "Wyndham",
              "plazahotelcolumbus.com": "property"}


def _brand_of(url: str) -> str:
    from urllib.parse import urlsplit
    host = (urlsplit(url).hostname or "").lower().lstrip("www.")
    for k, v in _BRAND_MAP.items():
        if k in host:
            return v
    return "property"


# --------------------------------------------------------------------------- #
# Render.
# --------------------------------------------------------------------------- #

def _facts_html(vm: HotelProfileVM) -> str:
    cells = "".join(
        '<div class="fh-cell"><div class="k">%s</div><div class="v %s">%s</div></div>'
        % (_e(lbl), cls, _e(val)) for lbl, val, cls in vm.facts)
    return '<div class="fh-facts">%s</div>' % cells


def _actions_html(vm: HotelProfileVM) -> str:
    call = '<a class="btn btn-line" href="/go/%s/call/">Call %s</a>' % (_slug(vm.name), _e(vm.phone)) if vm.phone else ""
    if vm.actions_mode == "book":
        return ('<a class="btn btn-primary" href="/go/%s/booking/">Check booking options</a>'
                '<div class="secondaries"><a class="btn btn-line" href="/go/%s/official-website/">Visit official site</a>'
                '<a class="btn btn-line" href="/go/%s/directions/">Directions</a>%s</div>'
                % (_slug(vm.name), _slug(vm.name), _slug(vm.name), call))
    if vm.actions_mode == "alt":
        return ('<a class="btn btn-primary alt" href="/pet-friendly-hotels/">Find pet-friendly alternatives</a>'
                '<div class="secondaries"><a class="btn btn-line" href="/go/%s/official-website/">Visit official site</a></div>'
                % _slug(vm.name))
    return ('<a class="btn btn-primary alt" href="/go/%s/official-website/">Visit official site</a>'
            '<div class="secondaries"><a class="btn btn-line" href="/methodology/">How to confirm the policy</a></div>'
            % _slug(vm.name))


def _mobilebar_html(vm: HotelProfileVM) -> str:
    if vm.actions_mode == "book":
        return ('<a class="btn btn-primary" href="/go/%s/booking/">Check booking options</a>'
                '<a class="btn btn-line" href="/go/%s/official-website/">Official site</a>'
                % (_slug(vm.name), _slug(vm.name)))
    if vm.actions_mode == "alt":
        return ('<a class="btn btn-primary alt" href="/pet-friendly-hotels/">Find alternatives</a>'
                '<a class="btn btn-line" href="/go/%s/official-website/">Official site</a>' % _slug(vm.name))
    return ('<a class="btn btn-primary alt" href="/go/%s/official-website/">Visit official site</a>'
            '<a class="btn btn-line" href="/methodology/">How to confirm</a>' % _slug(vm.name))


def _trust_html(vm: HotelProfileVM) -> str:
    icon = {"ok": "✓", "stop": "✕", "neutral": "•"}[vm.trust_cls]
    q = ('<details><summary>Exact wording available</summary><p class="quote">“%s”</p></details>'
         % _e(vm.evidence_quote)) if vm.evidence_quote else ""
    return '<div class="fh-trust %s"><span class="badge">%s %s</span>%s</div>' % (
        vm.trust_cls, icon, _e(vm.trust_line), q)


def _details_html(vm: HotelProfileVM) -> str:
    if vm.details_plain:
        svc = '<div class="fh-service"><b>Service animals:</b> %s</div>' % _e(vm.service_note) if vm.service_note else ""
        return '<p class="fh-plain">%s</p>%s' % (_e(vm.details_plain), svc)
    rows = "".join('<div class="row"><dt>%s</dt><dd class="%s">%s</dd></div>' % (_e(l), c, _e(v))
                   for l, v, c in vm.details_rows)
    note = '<p class="fh-fallback" style="margin-top:24px">%s</p>' % _e(vm.details_note) if vm.details_note else ""
    return '<dl class="fh-details">%s</dl>%s' % (rows, note)


def _prov_html(vm: HotelProfileVM) -> str:
    if vm.prov_status:
        return ('<div class="fh-prov"><div>Status: <b>not verified</b>. No approved official source has '
                'confirmed this property’s pet policy.</div><div class="links"><a href="/methodology/">How verification works ›</a></div></div>')
    q = ('<details><summary>See the exact recorded wording</summary><p class="quote">“%s”</p></details>'
         % _e(vm.evidence_quote)) if vm.evidence_quote else ""
    # Exact committed policy-evidence source link (PROD-004). A citation link to
    # the reviewed policy page -- distinct from the "Visit official site" business
    # CTA (a /go/ outbound redirect). Direct external link with safe attributes;
    # the exact target URL is preserved and never routed through the seed website.
    evidence = ('<div class="fh-evidence"><a class="fh-evidence-link" rel="nofollow noopener external" '
                'target="_blank" href="%s">View the official pet-policy source ›</a></div>'
                % _e(vm.source_url)) if vm.source_url else ""
    return ('<div class="fh-prov"><div>Read from <b>%s</b>, verified <b>%s</b>.</div>%s%s'
            '<div class="links"><a href="/methodology/">How we verify ›</a> · '
            '<a href="/go/%s/report-change/">Report an outdated policy ›</a></div></div>'
            % (_e(vm.source_name or "the official source"), _e(vm.verified_at or ""), q, evidence, _slug(vm.name)))


def _related_html(vm: HotelProfileVM) -> str:
    cards = []
    for r in vm.related:
        fact = '<div class="rf">%s</div>' % _e(r.fact) if r.fact else ""
        date = '<div class="rv">✓ Verified · %s</div>' % _e(r.verified_at) if r.verified_at else ""
        cards.append('<a class="fh-rel" href="%s"><div class="rn">%s</div><div class="ra">%s</div>%s%s<div class="rl">View policy ›</div></a>'
                     % (r.route, _e(r.name), _e(r.area), fact, date))
    return '<div class="fh-rel-grid">%s</div>' % "".join(cards)


def render_hotel_profile(vm: HotelProfileVM, *, css_href: str = "hotel_profile.css",
                         diag: bool = False, market_home: str = "/columbus-oh/") -> str:
    # ``market_home`` is the route of the Columbus market hub used by the two
    # "Columbus" links (breadcrumb root + the pet-travel-resources fallback).
    # It is a link TARGET only -- no visual/markup change -- and defaults to the
    # design authority's "/columbus-oh/" so the approved prototype and every
    # committed fixture render byte-for-byte identically. The production site
    # build passes its real hub route ("/") where no /columbus-oh/ page exists.
    crumb_area = vm.corridor.split(" ·")[0]
    hero = (
        '<section class="fh-hero">'
        '<div class="fh-media-wrap">'
        '<figure class="fh-media" data-media-slot="hotel-primary" role="img" aria-label="Branded placeholder for %s. No approved photograph of this property is available.">'
        '%s<div class="init">%s</div>'
        '<div class="mrow">%s<small>%s</small></div>'
        '<span class="mchip">%s</span></figure>'
        '<p class="fh-media-cap">%s</p></div>'
        '<span class="fh-corridor">%s</span>'
        '<h1 class="fh-name">%s</h1>'
        '<span class="fh-verif %s"><span class="dot" aria-hidden="true"></span>%s</span>'
        '<p class="fh-summary">%s</p>'
        '%s'
        '<div class="fh-actions">%s</div>'
        '</section>'
    ) % (_e(vm.name), _HOME_SVG, _e(vm.initials), _e(vm.name.split(" Columbus")[0]),
         _e(crumb_area), vm.verif_chip, _MEDIA_CAP, _e(vm.corridor), _e(vm.name),
         vm.verif_badge_cls, _e(vm.verif_badge_text), vm.summary, _facts_html(vm), _actions_html(vm))

    body = (
        _trust_html(vm)
        + '<div class="fh-body">'
        + '<section class="fh-sec" style="border-top:0;padding-top:0"><h2 class="fh-h2">Full policy details</h2>%s</section>' % _details_html(vm)
        + '<section class="fh-sec"><h2 class="fh-h2">Address &amp; directions</h2><p class="fh-addr">%s · <a href="/go/%s/directions/">Get directions ›</a></p></section>' % (_e(vm.address), _slug(vm.name))
        + '<section class="fh-sec"><h2 class="fh-h2">Traveling with a pet in Columbus</h2>'
          '<p class="fh-plain">Distance-based recommendations aren’t available for this property yet.</p>'
          '<p class="fh-fallback"><a href="%s">Explore Columbus pet-travel resources ›</a></p></section>' % market_home
        + '<section class="fh-sec"><h2 class="fh-h2">Verification &amp; provenance</h2>%s</section>' % _prov_html(vm)
        + '<section class="fh-sec"><h2 class="fh-h2">More verified pet-friendly stays</h2>%s</section>' % _related_html(vm)
        + '</div>'
    )

    menu_js = ("<script>var b=document.querySelector('.fh-menu'),n=document.getElementById('sitenav');"
               "if(b&&n){b.addEventListener('click',function(){var o=n.getAttribute('data-open')==='true';"
               "n.setAttribute('data-open',String(!o));b.setAttribute('aria-expanded',String(!o));});}</script>")
    diag_js = ""
    if diag:
        diag_js = ("<script>requestAnimationFrame(function(){var iw=innerWidth,sw=document.documentElement.scrollWidth,o=sw>iw+1;"
                   "var d=document.createElement('div');d.style.cssText='position:fixed;top:6px;left:6px;z-index:999;font:12px monospace;background:'+(o?'#c00':'#0a7a0a')+';color:#fff;padding:4px 8px;border-radius:4px';"
                   "d.textContent='innerW='+iw+' scrollW='+sw+' '+(o?'OVERFLOW':'no-overflow');document.body.appendChild(d);});</script>")

    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>%s — Pet Policy | PetTripFinder</title>'
        '<meta name="description" content="%s">'
        '<link rel="stylesheet" href="%s"></head><body>'
        '<a class="skip-link" href="#main">Skip to main content</a>'
        '<header class="fh-header"><div class="wrap">'
        '<a class="fh-brand" href="/">PetTripFinder<b> · Columbus</b></a>'
        '<button class="fh-menu" aria-expanded="false" aria-controls="sitenav">Menu</button>'
        # PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001. The Parks link is emitted only
        # when this market actually publishes a parks directory; a hotels-only
        # market linked 19 profiles at a page that does not exist. Columbus
        # publishes parks, so its markup is unchanged.
        '<nav class="fh-nav" id="sitenav" aria-label="Main"><a href="/pet-friendly-hotels/">Hotels</a>'
        + ('<a href="/pet-friendly-parks/">Parks</a>'
           if _is_published_category("pet-friendly-parks") else "")
        + '<a href="/methodology/">How we verify</a></nav>'
        '</div></header>'
        '<div class="wrap"><nav class="fh-crumbs" aria-label="Breadcrumb"><ol>'
        '<li><a href="%s">Columbus</a></li><li><a href="/pet-friendly-hotels/">Pet-Friendly Hotels</a></li>'
        '<li><a href="#">%s</a></li><li aria-current="page">%s</li></ol></nav>'
        '%s<main id="main">%s</main></div>'
        '<footer class="fh-footer"><div class="wrap"><div>© 2026 PetTripFinder · Your verified Columbus pet-travel guide'
        '<br><span style="font-size:12.5px">Some booking links are affiliate links; using them may earn PetTripFinder a commission and never changes a property’s placement or its verified policy.</span></div>'
        '<div><a href="/methodology/">How we verify</a> · <a href="/about/">About</a> · <a href="/contact/">Contact</a></div></div></footer>'
        '<div class="fh-mobilebar">%s</div>'
        '%s%s</body></html>'
    ) % (_e(vm.name), _e(re.sub("<[^>]+>", "", vm.summary))[:150], css_href,
         market_home, _e(crumb_area), _e(vm.name), hero, body, _mobilebar_html(vm), menu_js, diag_js)


# --------------------------------------------------------------------------- #
# Controlled fixture builders.
#
# The fixture DATA is committed (hotel_profile_fixtures.json), transcribed
# verbatim from the repository-authorized verified importer candidates, so the
# renderer, the fixture runner, and the tests are fully reproducible in a clean
# checkout -- they never read the gitignored operational data/ tree. Property
# IDENTITY (address/phone/URL) still comes from the tracked production seed CSV
# via read_production_rows(); only the verified pet-policy FACTS and the two
# out-of-inventory (no-pets / unverified) records live in the committed fixture
# file.
# --------------------------------------------------------------------------- #

_FIXTURE_DATA_PATH = Path(__file__).resolve().parent / "hotel_profile_fixtures.json"


def _load_fixture_data() -> Dict:
    return json.loads(_FIXTURE_DATA_PATH.read_text(encoding="utf-8"))


def build_fixture_vms() -> Dict[str, HotelProfileVM]:
    """The five controlled production fixtures. rich/sparse/no-photo combine the
    promoted production CSV identity with committed verified facts; no-pets and
    unverified come from committed, repository-authorized candidate excerpts
    (intentionally not part of the verified pet-friendly production set). No
    gitignored operational data is read -- reproducible from a clean checkout."""
    rows = read_production_rows()
    hotels = [r for r in rows if r["category"] == "pet-friendly-hotels"]
    data = _load_fixture_data()
    facts_map = data["verified_facts"]

    def row_by(name_start):
        return next(r for r in hotels if r["name"].startswith(name_start))

    rich_row = row_by("Drury Inn & Suites Columbus Grove City")
    sparse_row = row_by("Days Inn by Wyndham Grove City")

    np = data["no_pets"]
    cand_no_pets = {
        "context": {"candidate_name": np["name"], "expected_city": np["city"]},
        "proposed_fields": [["name", np["name"]], ["city", np["city"]],
                            ["address", np["address"]], ["website_url", np["website_url"]]],
        "snapshot": {"observed_at": np["verified_at"], "requested_url": np["website_url"]},
        "evidence": [{"field_name": "pets_allowed", "snapshot_quote": np["evidence_quote"]}],
    }
    uv = data["unverified"]
    cand_unverified = {
        "context": {"candidate_name": uv["name"], "expected_city": uv["city"]},
        "proposed_fields": [], "evidence": [],
        "snapshot": {"requested_url": uv["official_url"]},
    }

    return {
        "rich": build_vm_from_production(rich_row, facts_map.get(normalize_name(rich_row["name"])), hotels, facts_map),
        "sparse": build_vm_from_production(sparse_row, facts_map.get(normalize_name(sparse_row["name"])), hotels, facts_map),
        # no-photo is the same verified record as rich -- every hotel is
        # photo-less, so the placeholder is the default; this proves the media
        # region is stable whether a photo or the placeholder fills it.
        "no-photo": build_vm_from_production(rich_row, facts_map.get(normalize_name(rich_row["name"])), hotels, facts_map),
        "no-pets": build_vm_from_no_pets(cand_no_pets, hotels, facts_map),
        "unverified": build_vm_from_unverified(cand_unverified, hotels, facts_map),
    }

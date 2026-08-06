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
_HOME_SVG = ('<svg class="glyph" width="34" height="34" viewBox="0 0 24 24" fill="none" '
             'stroke="#f6f1e7" stroke-width="1.4" aria-hidden="true">'
             '<path d="M3 21V9l9-5 9 5v12"/><path d="M9 21v-6h6v6"/><path d="M3 21h18"/></svg>')


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
# Authoritative display-corridor taxonomy (PTF-PROD-001A correction 1).
#
# Presentation-only. Deliberately NOT site_data.assign_corridor: that adapter's
# Downtown/Dublin grouping drives the >=5-property *indexable-corridor* logic
# used by the site build / reconciliation, and must keep its exact semantics.
# This produces the display label the approved design authority uses:
# "<Area> corridor · Columbus, OH", anchored to the Columbus market. A suburb
# city becomes "<City> corridor"; a Columbus-city hotel is placed into a named
# sub-area corridor by ADDRESS markers (never a marketing name), with an
# airport fallback used only when no street address is available.
# --------------------------------------------------------------------------- #

_DOWNTOWN_MARKERS = ("nationwide blvd", "state street", "capitol square")
_HIGH_ST_RE = re.compile(r"\b(\d{1,4})\s+(?:north|south|n|s)?\.?\s*high\s+st", re.I)
_METRO_ANCHOR = "Columbus, OH"


def _corridor_area(city: str, address: str, name: str = "") -> str:
    c = (city or "").strip()
    addr = (address or "").lower()
    if c.lower() == "columbus":
        if any(m in addr for m in _DOWNTOWN_MARKERS):
            return "Downtown corridor"
        m = _HIGH_ST_RE.search(addr)
        if m and int(m.group(1)) < 1000:
            return "Downtown corridor"
        if "west hilliard" in addr or "westbelt" in addr:
            return "West Hilliard corridor"
        if "polaris" in addr:
            return "Polaris corridor"
        if "airport" in addr:
            return "Airport corridor"
        if not addr and "airport" in (name or "").lower():
            return "Airport corridor"     # last-resort hint when no address exists
        return "Columbus corridor"
    if c:
        return "%s corridor" % c
    return "Columbus corridor"


def _corridor_label(city: str, address: str, name: str = "") -> str:
    return "%s · %s" % (_corridor_area(city, address, name), _METRO_ANCHOR)


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
                  "fee_schedule", "fee_cap_tiers")


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
    "combined" must sit next to the number actually being published.
    """
    text = evidence or ""
    m = re.search(r"\d+(?:\.\d+)?", weight_limit or "")
    if not m:
        return False
    number = _TRAILING_ZEROS_RE.sub(r"\1", m.group(0))
    # The number, in either recorded form, within a short window of "combined".
    for form in {number, m.group(0)}:
        n = re.escape(form)
        if re.search(r"combined[^.]{0,30}?%s|%s[^.]{0,30}?combined" % (n, n), text, re.I):
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


def fee_withheld_notice(f: Dict) -> str:
    """The right sentence for whichever reason the fee was withheld, or ""."""
    if f.get("fee_conflict"):
        return FEE_CONFLICT_NOTICE
    if f.get("fee_withheld"):
        return FEE_RANGE_NOTICE
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
    if (f.get("weight_limit_operator") or "") == "lt":
        return "under %s" % _prose_number(value)
    return _prose_number(value)


def weight_display(f: Dict) -> str:
    """Table/chip form of the same limit: "Under 80.0 pounds", or "" if absent.

    Keeps the exact recorded value -- structured cells never round, only the
    running sentence does -- and carries the same exclusivity as the prose so
    the two can never disagree with each other.
    """
    value = (f.get("weight_limit") or "").strip()
    if not value:
        return ""
    if (f.get("weight_limit_operator") or "") == "lt":
        return "Under %s" % value
    return value


def tier_fee_range(tiers: Sequence[Dict]) -> str:
    """"$75–$125" for a ladder; a single amount if every tier charges the same.

    Shared with the comparison table so one ladder cannot be summarised two
    different ways on two pages.
    """
    amounts = [_prose_number("$%s" % t.get("amount", "")) for t in tiers if t.get("amount")]
    if not amounts:
        return ""
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
    source states it -- a tier whose scope is unstated says nothing, exactly as
    before, so no existing profile changes.
    """
    return " per pet" if t.get("scope") == "per_pet" else ""


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


def _tiered_fee_sentence(tiers: Sequence[Dict], evidence: str = "") -> str:
    """A source-faithful sentence for a stay-length fee ladder.

    Deliberately states no basis. A field reading "$75(1-4n)$125(5+n)" gives an
    amount and a stay range and says nothing about recurrence -- calling it
    "per night" or "per stay" would invent the difference. Basis appears only
    where the source states one, carried on the tier as ``basis_stated``.
    """
    if not tiers:
        return ""
    nonref = "non-refundable " if _NONREFUNDABLE_RE.search(evidence or "") else ""
    # Where the SOURCE states the recurrence -- "1-4 nights $75.00 per stay" --
    # it is carried through. Where it does not, nothing is said: an amount and a
    # stay range say nothing about whether the charge repeats.
    basis = _tier_basis_phrase(tiers)
    first, rest = tiers[0], tiers[1:]
    s = "A %spet fee of %s%s%s applies for %s" % (
        nonref, _tier_amount(first), basis, _tier_scope_phrase(first),
        _tier_range_phrase(first))
    for t in rest:
        s += ", and %s%s%s applies for %s" % (
            _tier_amount(t), basis, _tier_scope_phrase(t), _tier_range_phrase(t))
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
            s = "A %s%s fee applies" % (_prose_number(fee), nonref)
            if basis:
                s += " %s" % basis.lower()
            # A room-scoped fee is one charge however many animals arrive. Said
            # plainly and only where the source said it -- a guest bringing two
            # pets otherwise has to guess whether to double the figure.
            if f.get("fee_scope") == "per_room":
                s += " for the room"
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
        parts.append(s + ".")
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
    bound = f.get("species_weight_limits") or {}
    if bound:
        # Named animal, named ceiling, and silence about the rest -- because the
        # source limited one species and said nothing about the other. "Maximum
        # pet weight is 20 pounds" would invent the missing half.
        species, rule = sorted(bound.items())[0]
        parts.append("%s must weigh %s or less%s" % (
            _cap_first(species), _prose_number(rule.get("value", "")),
            (", with up to %s permitted per room." % _pets_phrase(count))
            if count else "."))
    elif weight and _source_states_combined_weight(evidence, f.get("weight_limit", "")):
        parts.append("Up to %s with a combined weight limit of %s."
                     % (_pets_phrase(count), weight)
                     if count else "A combined weight limit of %s applies." % weight)
    elif weight and (f.get("weight_limit_operator") or "") == "lt":
        # An exclusive ceiling gets a sentence that excludes: "under 80 pounds"
        # turns the 80-pound dog away, and "maximum ... is 80 pounds" does not.
        parts.append("Pets must weigh %s%s" % (
            weight_phrase(f),
            (", with up to %s permitted per room." % _pets_phrase(count))
            if count else "."))
    elif weight:
        parts.append("Maximum pet weight is %s%s" % (
            weight,
            (", with up to %s permitted per room." % _pets_phrase(count))
            if count else "."))
    elif count:
        # A source that says "No weight limit per pet" has stated a FACT, not
        # left a gap. Rendering it as silence would tell a reader the hotel was
        # unclear when it was explicit.
        if f.get("weight_limit_stated_none") == "true":
            parts.append("%s is permitted per room, with no pet weight limit "
                         "stated by the hotel."
                         % _cap_first(_pets_phrase(count).replace("1 pet", "One pet")))
        elif f.get("fee_scope") == "per_room":
            # A room-scoped fee has just told the reader the charge covers the
            # room; the allowance sentence that follows it carries its verb so
            # the two read as one statement about the room rather than as a
            # heading and a fragment. Everywhere else the established phrasing
            # stands unchanged -- this is a wording choice for one path, not a
            # licence to reword every profile that states a count.
            phrase = _pets_phrase(count)
            parts.append("Up to %s %s permitted per room."
                         % (phrase, "is" if phrase.startswith("1 pet") else "are"))
        else:
            parts.append("Up to %s permitted per room." % _pets_phrase(count))
    elif f.get("weight_limit_stated_none") == "true":
        parts.append("The hotel states no pet weight limit.")

    # A refundable pet deposit is a separate obligation from the fee: the guest
    # gets it back. Stated last so it can never be read as part of the price.
    deposit = f.get("pet_deposit") or {}
    if isinstance(deposit, dict) and deposit.get("amount"):
        parts.append("A separate refundable pet deposit of %s is also stated."
                     % _prose_number("$%s" % deposit["amount"]))
    return " ".join(parts)


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
        head = (
            ("Dogs", *(("Accepted", "yes") if "dog" in sp else ("Not stated", "dim"))),
            ("Cats", *(("Accepted", "yes") if "cat" in sp else ("Not stated", "dim"))),
        )
    tiers = f.get("fee_tiers") or []
    if f.get("fee_conflict") or f.get("fee_withheld"):
        return head + (
            ("Pet charge", "See policy wording", "dim"),
            ("Charge basis",
             "Source conflict" if f.get("fee_conflict") else "Range by stay", "dim"),
            ("Max pets", *cell(f.get("pet_count_limit"))),
            ("Weight limit", *cell(weight_display(f))),
        )
    if tiers:
        # A ladder has no single charge and no stated basis, so the chips say
        # the range and name the reason rather than showing one number.
        return head + (
            ("Pet charge", tier_fee_range(tiers), ""),
            ("Charge basis", "Tiered by stay length", "sm"),
            ("Max pets", *cell(f.get("pet_count_limit"))),
            ("Weight limit", *cell(weight_display(f))),
        )
    # A staged fee has no single charge, so the chip names both stages rather
    # than the first night's price standing in for the stay.
    first_night, additional_night = staged_fee(f)
    if first_night:
        return head + (
            ("Pet charge", "%s first night, then %s" % (first_night, additional_night), ""),
            ("Charge basis", "Staged by night", "sm"),
            ("Max pets", *cell(f.get("pet_count_limit"))),
            ("Weight limit", *cell(weight_display(f))),
        )
    cap = (f.get("fee_cap") or {}).get("amount")
    charge = f.get("pet_fee")
    # A ceiling only ever LOWERS a total, so leaving a tiered one out of the
    # compact chip cannot overstate what a guest pays -- and putting "$75–$150"
    # beside a $25 rate invites reading the ceiling as the charge. The tiers are
    # stated in full in the summary and the detail table.
    if charge and cap and not cap_tiers(f):
        charge = "%s (max %s)" % (charge, _prose_number("$%s" % cap))
    return head + (
        ("Pet charge", *cell(charge)),
        ("Charge basis", *(lambda v: (_cap_first(v), "sm") if v else ("Not stated", "dim"))(f.get("fee_basis"))),
        ("Max pets", *cell(f.get("pet_count_limit"))),
        ("Weight limit", *cell(weight_display(f))),
    )


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


def _verified_details(f: Dict[str, str]) -> Tuple[Tuple, str, str]:
    sparse = not any(f.get(k) for k in _STATED_FIELDS)
    svc = "A separate legal access category — not treated as a pet-policy exception."
    if sparse:
        rows = (
            ("Accepted species", "Pets welcome (species not specified)", ""),
            ("Fee, pet limit, weight limit", _NOT_STATED, "dim"),
            ("Breed / unattended rules", _NOT_STATED, "dim"),
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
    if first_night:
        charge_rows = (("Pet charge, first night", first_night, ""),
                       ("Pet charge, each additional night", additional_night, ""))
    elif f.get("fee_tiers"):
        charge_rows = tuple(
            ("Pet charge, %s" % _tier_range_phrase(t).replace("stays of ", ""),
             _tier_amount(t) + _tier_scope_phrase(t), "")
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

    rows = (
        ("Accepted species", *(lambda v: (_cap_first(v), "") if v else (_NOT_STATED, "dim"))(f.get("species_allowed"))),
        ("Maximum pets", *(lambda v: (v + " per room", "") if v else (_NOT_STATED, "dim"))(f.get("pet_count_limit"))),
        *charge_rows,
        *maximum_rows,
        ("Charge basis",
         *(("Tiered by stay length; the source does not state a per-night or "
            "per-stay basis.", "") if f.get("fee_tiers")
           else ("Staged: the first night is charged at a different rate from "
                 "each additional night.", "") if first_night
           else ("Withheld: the official source states conflicting terms.", "dim")
           if f.get("fee_conflict")
           else ("Withheld: the official source gives a range that depends on "
                 "the stay.", "dim")
           if f.get("fee_withheld")
           else (lambda v: (_cap_first(v), "") if v else (_NOT_STATED, "dim"))(
               f.get("fee_basis")))),
        ("Weight restriction", *d(weight_display(f))),
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
        ("Breed restrictions", *d(f.get("breed_restrictions"))),
        ("Unattended-pet rule", *d(f.get("unattended_policy"))),
        ("Service animals", svc, ""),
    )
    return rows, "", ""


# --------------------------------------------------------------------------- #
# Adapters.
# --------------------------------------------------------------------------- #

def _related_from_production(self_name: str, all_hotel_rows, facts_map, limit=3) -> Tuple[RelatedHotel, ...]:
    out = []
    for row in sorted(all_hotel_rows, key=lambda r: normalize_name(r["name"])):
        if normalize_name(row["name"]) == normalize_name(self_name):
            continue
        fe = facts_map.get(normalize_name(row["name"]))
        fact = _related_fact(fe["facts"]) if fe else ""
        date = _friendly_date((fe["verified_at"] if fe else "") or row.get("observed_at", ""))
        out.append(RelatedHotel(
            name=row["name"], area=_corridor_area(row.get("city", ""), row.get("address", ""), row["name"]),
            fact=fact, verified_at=date,
            route="/pet-friendly-hotels/%s/" % _slug(row["name"])))
        if len(out) >= limit:
            break
    return tuple(out)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def build_vm_from_production(row: Dict[str, str], facts_entry: Optional[Dict],
                            all_hotel_rows, facts_map) -> HotelProfileVM:
    """Verified pet-friendly VM from a production seed row + its READY-candidate
    facts. Rich when the candidate stated fee/species/limits; sparse when it
    stated only that pets are welcome. Never invents a field."""
    f = (facts_entry or {}).get("facts", {}) if facts_entry else {}
    date = _friendly_date((facts_entry or {}).get("verified_at", "") or row.get("observed_at", ""))
    rows, plain, note = _verified_details(f)
    # exact wording, carried on the fixture facts entry (committed, reproducible)
    quote = (facts_entry or {}).get("evidence_quote") if facts_entry else None
    return HotelProfileVM(
        state=STATE_VERIFIED, name=row["name"],
        corridor=_corridor_label(row.get("city", ""), row.get("address", ""), row["name"]),
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
        related=_related_from_production(row["name"], all_hotel_rows, facts_map),
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
        state=STATE_NO_PETS, name=name, corridor=_corridor_label(city, proposed.get("address", ""), name),
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
        state=STATE_UNVERIFIED, name=name, corridor=_corridor_label(city, "", name),
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


def build_vm_from_production_unverified(row: Dict[str, str], all_hotel_rows, facts_map) -> HotelProfileVM:
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
        corridor=_corridor_label(row.get("city", ""), row.get("address", ""), name),
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
        related=_related_from_production(name, all_hotel_rows, facts_map))


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
        '<nav class="fh-nav" id="sitenav" aria-label="Main"><a href="/pet-friendly-hotels/">Hotels</a><a href="/pet-friendly-parks/">Parks</a><a href="/methodology/">How we verify</a></nav>'
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

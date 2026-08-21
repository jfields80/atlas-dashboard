"""The fixed corpus PTF-MILWAUKEE-READER-TO-TIERS-034 is measured against.

Every case is a policy block and the answer the reader must give it. The
positives say what a ladder looks like when the source determines it; the
negatives say what must NEVER become one, and they carry the weight here --
teaching a reader to build a fee structure is teaching it to assert a price
schedule, and the failure mode is not a missing fact but a quoted price the
hotel never stated.

The two shapes the schema holds are separated on purpose: a stay-length ladder
goes to ``fee_tiers`` and a per-animal ladder to ``fee_pet_schedule``, and a
surface that states both at once is refused rather than reconciled.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

TIER = "TIER"
SCHEDULE = "SCHEDULE"
NEGATIVE = "NEGATIVE"
REGRESSION = "REGRESSION"


@dataclass(frozen=True)
class Case:
    """One block, and what the reader must make of it."""

    case_id: str
    kind: str
    scenario: str
    text: str
    #: Tiers the reader must emit, as (amount_cents, min, max) triples.
    tiers: Tuple[Tuple[int, int, Optional[int]], ...] = ()
    #: Schedule rungs, as (pet_ordinal, amount_cents) pairs.
    rungs: Tuple[Tuple[int, int], ...] = ()
    must_extract: Tuple[str, ...] = ()
    must_not_extract: Tuple[str, ...] = ()
    must_withhold: Tuple[str, ...] = ()
    why: str = ""


CASES: Tuple[Case, ...] = (
    # --- ladders the source determines ------------------------------------- #
    Case(case_id="T1-two-band-ladder",
         kind=TIER,
         scenario="two rungs, the second open-ended",
         text="Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee Other "
              "pet information $75(1-4n), $125(5+n) 2 pets max, dog/cat only",
         tiers=((7500, 1, 4), (12500, 5, None)),
         must_extract=("fee_tiers",),
         must_not_extract=("pet_fee",),
         why="the shape eighteen Milwaukee rows were held for"),
    Case(case_id="T2-three-band-ladder",
         kind=TIER,
         scenario="three rungs, the first a single night",
         text="Other pet information $50/stay for 1 night, $75/stay for 2-4 "
              "nights, $125/stay for 5+ nights 2 pets max",
         tiers=((5000, 1, 1), (7500, 2, 4), (12500, 5, None)),
         must_extract=("fee_tiers",),
         why="a ladder may be longer than two, and its first rung may be one "
             "night"),
    Case(case_id="T3-abbreviated-single-night",
         kind=TIER,
         scenario="the single-night rung written in the chain's own shorthand",
         text="Pets allowed Yes Other pet information $50(1n),$75(2-4n),"
              "$125(5+n) 2petsMax,dog/cat only",
         tiers=((5000, 1, 1), (7500, 2, 4), (12500, 5, None)),
         must_extract=("fee_tiers",),
         why="the row published no fee at all while its page printed three"),
    Case(case_id="T4-basis-stated",
         kind=TIER,
         scenario="each rung states its own basis",
         text="Other pet information $75/stay 1-4 nights, $125/stay 5+ nights",
         tiers=((7500, 1, 4), (12500, 5, None)),
         must_extract=("fee_tiers",),
         why="basis_stated must be true only where the surface says it"),
    Case(case_id="T5-per-pet-scope",
         kind=TIER,
         scenario="a ladder priced per animal",
         text="Pets welcome. $50 per pet for 1-4 nights, $90 per pet for 5+ "
              "nights.",
         tiers=((5000, 1, 4), (9000, 5, None)),
         must_extract=("fee_tiers",),
         why="scope is carried where stated and never inferred"),
    Case(case_id="T6-per-room-scope",
         kind=TIER,
         scenario="a ladder priced per room",
         text="Pets welcome. $50 per room for 1-4 nights, $90 per room for 5+ "
              "nights.",
         tiers=((5000, 1, 4), (9000, 5, None)),
         must_extract=("fee_tiers",),
         why="the other half of the scope vocabulary"),
    Case(case_id="T7-per-day-not-per-night",
         kind=TIER,
         scenario="a daily ladder",
         text="Pets welcome. $20/day for 1-4 nights, $30/day for 5+ nights.",
         tiers=((2000, 1, 4), (3000, 5, None)),
         must_extract=("fee_tiers",),
         why="the source said daily and per_day is not per_night"),

    # --- ladders priced by animal ------------------------------------------ #
    Case(case_id="S1-pet-count-schedule",
         kind=SCHEDULE,
         scenario="a price per animal, stated as counts",
         text="Pets welcome. 1 pet $15 per night, 2 pets $25 per night.",
         rungs=((1, 1500), (2, 2500)),
         must_extract=("fee_pet_schedule",),
         must_not_extract=("pet_fee", "fee_tiers"),
         why="the second shape 1.2 holds"),
    Case(case_id="S2-ordinal-words",
         kind=SCHEDULE,
         scenario="the same ladder written in ordinals",
         text="Pets welcome. First pet $20 per night, second pet $30 per night.",
         rungs=((1, 2000), (2, 3000)),
         must_extract=("fee_pet_schedule",),
         why="'first pet' and '1 pet' are the same rung"),

    # --- what must never become a structure -------------------------------- #
    Case(case_id="N1-overlapping-bands",
         kind=NEGATIVE,
         scenario="two rungs claiming the same night",
         text="Pets Welcome 2 pets 50lbs max per pet per room with "
              "non-refundable fee.0-5 nights $75 5+ $150",
         must_not_extract=("fee_tiers", "pet_fee"),
         must_withhold=("pet_fee",),
         why="night five is priced twice and choosing is quoting a price the "
             "hotel did not"),
    Case(case_id="N2-gap-between-bands",
         kind=NEGATIVE,
         scenario="a night nothing prices",
         text="Dogs are allowed with a 50 USD nonrefundable fee, per pet, for "
              "stays 1 to 6 nights, 150 USD for stays over 7 nights.",
         must_not_extract=("fee_tiers",),
         must_withhold=("pet_fee",),
         why="night seven falls between the rungs"),
    Case(case_id="N3-ceiling-is-not-a-price",
         kind=NEGATIVE,
         scenario="a ladder whose rung is a ceiling",
         text="Pets allowed with nonrefundable fee. Up to 75 dollars for 1 to "
              "6 nights, up to 150 dollars for 7+ nights.",
         must_not_extract=("fee_tiers", "pet_fee"),
         must_withhold=("pet_fee",),
         why="CEILING != PRICE, and a ladder of ceilings prices nothing"),
    Case(case_id="N4-additional-charge-role",
         kind=NEGATIVE,
         scenario="a rung that reads as an addition, not a replacement",
         text="Pet Fees 1-6 nights : $100 / STAY 7-30 nights + additional "
              "cleaning fee : $200 / STAY",
         must_not_extract=("fee_tiers", "pet_fee", "cleaning_fee"),
         must_withhold=("pet_fee",),
         why="whether $200 is the long-stay price or a separate charge is "
             "exactly what the page does not say"),
    Case(case_id="N5-contradictory-basis",
         kind=NEGATIVE,
         scenario="the same money on two bases",
         text="Pets are welcome at Crowne Plaza Milwaukee Airport. We love "
              "pets, and the pet fee is 75.00 USD per stay. A cleaning fee of "
              "250.00 will be assessed for the discovery of an unauthorized "
              "pet. Pet fee per night: 75 USD Pet weight limit: 75 2 pets "
              "allowed Pets allowed: Only dogs and cats allowed",
         must_not_extract=("fee_tiers", "fee_basis", "pet_fee"),
         must_withhold=("pet_fee", "fee_basis"),
         why="the surface states one amount on two bases and a third charge "
             "beside it; per_stay is not per_night and neither is chosen"),
    Case(case_id="N6-room-type-condition",
         kind=NEGATIVE,
         scenario="a price that depends on the room booked",
         text="It is an additional $20 fee per dog, per night ($30/dog/night "
              "in Suites) and we have a maximum of two (2) dogs per room.",
         must_not_extract=("fee_tiers", "pet_fee"),
         why="1.2 has no condition type for which room was booked"),
    Case(case_id="N7-species-condition",
         kind=NEGATIVE,
         scenario="a price that depends on the animal",
         text="Pets welcome. Dogs $50 per night for 1-4 nights, cats $30 per "
              "night for 1-4 nights.",
         must_not_extract=("fee_tiers",),
         why="1.2 has no condition type for species"),
    Case(case_id="N8-weight-condition",
         kind=NEGATIVE,
         scenario="a price that depends on the animal's weight",
         text="Pets welcome. $50 per stay under 25 lbs for 1-4 nights, $100 "
              "per stay over 25 lbs for 5+ nights.",
         must_not_extract=("fee_tiers",),
         why="1.2 has no condition type for weight"),
    Case(case_id="N9-unsupported-basis",
         kind=NEGATIVE,
         scenario="a recurrence FEE_BASES has no member for",
         text="Pets welcome. $75 per 7 day stay for 1-4 nights, $125 per 7 day "
              "stay for 5+ nights.",
         must_not_extract=("fee_tiers", "pet_fee", "fee_basis"),
         must_withhold=("pet_fee",),
         why="not invented, and not silently dropped either"),
    Case(case_id="N10-tax-qualifier",
         kind=NEGATIVE,
         scenario="a rung stated plus tax",
         text="Pets Allowed. Pet fee is 50 USD plus applicable taxes for up to "
              "5 nights. For 6 or more nights, the fee is 125 USD plus "
              "applicable taxes.",
         must_not_extract=("fee_tiers",),
         must_withhold=("pet_fee",),
         why="a tier carries no tax_relationship, so the rung would publish a "
             "number the guest does not pay"),
    Case(case_id="N11-open-ended-rung",
         kind=NEGATIVE,
         scenario="a per-animal ladder with no ordinal",
         text="Pets welcome. First pet $20 per night, each additional pet $10 "
              "per night.",
         must_not_extract=("fee_pet_schedule",),
         why="'each additional' could be the second animal or the fifth"),
    Case(case_id="N12-room-rate-card",
         kind=NEGATIVE,
         scenario="room prices next to a pet statement",
         text="Pets Welcome. 1 King Bed 4 Guests Discounted rate: $160 USD "
              "/night Strikethrough Rate: $172 Member Rate 160.00 per night",
         must_not_extract=("fee_tiers", "pet_fee"),
         why="a rate card is not a fee ladder"),
    Case(case_id="N13-service-animal-only",
         kind=NEGATIVE,
         scenario="a page that only mentions service animals",
         text="Service Animals are Welcome. Deposit Policy: A $50 refundable "
              "deposit for incidentals is required at check-in for all guests.",
         must_not_extract=("fee_tiers", "pet_fee", "pets_allowed"),
         why="a legal obligation is not a pet policy"),
    Case(case_id="N14-amenity-only",
         kind=NEGATIVE,
         scenario="an amenity chip",
         text="Pet Friendly",
         must_not_extract=("fee_tiers", "pet_fee"),
         why="a chip in a list states no term"),

    # --- what must not move ------------------------------------------------ #
    Case(case_id="R1-simple-prose-fee",
         kind=REGRESSION,
         scenario="the shape the reader was built for",
         text="Pets Welcome. Pet fee $25 per night.",
         must_extract=("pet_fee", "fee_basis"),
         must_not_extract=("fee_tiers",),
         why="one price is not a ladder"),
    Case(case_id="R2-capped-nightly-fee",
         kind=REGRESSION,
         scenario="a nightly fee with a stated ceiling",
         text="Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per "
              "stay.",
         must_extract=("pet_fee", "fee_cap"),
         must_not_extract=("fee_tiers",),
         why="two prices and no band is a cap, and the cap has its own field"),
    Case(case_id="R3-per-day-simple",
         kind=REGRESSION,
         scenario="a daily fee with no band",
         text="Pets welcome. The Pet Friendly rate is 35.00 USD per day.",
         must_extract=("pet_fee", "fee_basis"),
         must_not_extract=("fee_tiers",),
         why="per_day survives untouched"),
    Case(case_id="R4-label-value-table",
         kind=REGRESSION,
         scenario="033's label-and-value layout",
         text="Pet Fees Price : $40 / NIGHT Weight Limits Individual pet "
              "weight limit : 150 Pounds Maximum number of pets is 2.",
         must_extract=("pet_fee", "weight_limit", "pet_count_limit"),
         must_not_extract=("fee_tiers",),
         why="the previous work order's win must not regress"),
)


def cases() -> List[Case]:
    return list(CASES)


def by_kind(kind: str) -> List[Case]:
    return [case for case in CASES if case.kind == kind]


__all__ = ["Case", "CASES", "cases", "by_kind",
           "TIER", "SCHEDULE", "NEGATIVE", "REGRESSION"]

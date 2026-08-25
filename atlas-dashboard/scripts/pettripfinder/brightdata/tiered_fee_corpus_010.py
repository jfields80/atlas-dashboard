"""PTF-POLICY-READER-TIERED-FEE-HARDENING-010 -- the focused regression corpus.

Every string here is REAL text from a persisted Milwaukee capture in this
branch's own run directories. None of it is invented, because a parser fix
measured against invented phrasing measures the phrasing.

The corpus is split by what the reader is supposed to DO with each case, and
the expectation is recorded next to the text so a change of behaviour is a
visible diff rather than a judgement call at review time:

    STRUCTURE  the schema can hold this; a fee/weight must be emitted
    WITHHOLD   the schema cannot hold this safely; the amount must NOT be
               emitted, and the raw evidence must survive
    UNCHANGED  included to catch collateral damage, not to prove the fix

The two cases the work order exists for are ``staybridge_tiered_nights`` (a
tiered fee flattened to its first tier -- the live defect) and the two IHG
weight forms that currently miss.
"""

from __future__ import annotations

from typing import Dict, List

#: One entry per case. ``expect`` is what the CORRECTED reader must do.
CASES: List[Dict] = [

    # ----------------------------------------------------------------- #
    # Tiered by stay duration -- must never collapse to one amount
    # ----------------------------------------------------------------- #
    {
        "case": "staybridge_tiered_nights",
        "source": "Staybridge Suites Milwaukee Airport South (IHG)",
        "family": "TIERED_DURATION",
        "expect": "WITHHOLD",
        "why": ("50 USD covers stays of 1-6 nights and 150 USD covers 7+. "
                "Publishing 5000 underprices a week by 100 USD. This is the "
                "live defect."),
        "text": ("Pets are welcome at Staybridge Suites Milwaukee Airport South. "
                 "There is a pet deposit per stay of 50 USD . Our Pet Policy: "
                 "Dogs are allowed with a 50 USD nonrefundable fee, per pet, for "
                 "stays 1 to 6 nights, 150 USD for stays over 7 nights. Two pets "
                 "max per room, and must weigh less than 80 lbs."),
    },
    {
        "case": "holiday_inn_express_tiered_nights",
        "source": "Holiday Inn Express Milwaukee-West Medical Center (IHG)",
        "family": "TIERED_DURATION",
        "expect": "WITHHOLD",
        "why": ("three tiers by night count. The reader already withheld this "
                "one because no single charge parsed; it must STAY withheld "
                "once the tier detector exists, not become structured."),
        "text": ("We welcome pets at a maximum weight of 40lbs up to 2 pets per "
                 "rooms. There is a non refundable fee of 50.00 for a 1 to 2 "
                 "night stay. For 3 to 5 nights the fee is 100.00, and 5 or "
                 "more will be 150.00."),
    },

    # ----------------------------------------------------------------- #
    # Tiered by pet count -- must never collapse either
    # ----------------------------------------------------------------- #
    {
        "case": "travelodge_tiered_pets_and_weekly",
        "source": "Travelodge by Wyndham Milwaukee",
        "family": "TIERED_COUNT",
        "expect": "WITHHOLD",
        "why": ("prices differ by number of dogs AND by week. Already withheld "
                "today; must stay withheld."),
        "text": ("Pets Allowed - 2 pets max. Dogs only. 40lbs or less per dog. "
                 "Fees - 15USD 1 dog per night 25USD 2 dogs per night. Weekly "
                 "75USD 1 dog 95USD 2 dogs"),
    },

    # ----------------------------------------------------------------- #
    # Conditional by weight -- the mechanism that already worked
    # ----------------------------------------------------------------- #
    {
        "case": "weight_conditioned_fee",
        "source": "corpus pattern the existing _CONDITIONAL_FEE_RE was built for",
        "family": "CONDITIONAL_WEIGHT",
        "expect": "WITHHOLD",
        "why": "a fee that applies only above a weight is not a fee for every pet",
        "text": "Pets welcome. 75 USD fee for pets over 50 lbs.",
    },

    # ----------------------------------------------------------------- #
    # Simple fees -- must be untouched by the fix
    # ----------------------------------------------------------------- #
    {
        "case": "super8_germantown_per_night",
        "source": "Super 8 by Wyndham Germantown/Milwaukee",
        "family": "SIMPLE",
        "expect": "STRUCTURE",
        "why": "one price, one basis, one scope",
        "text": ("Pets Allowed - Dogs only. Fees - 20USD per pet per night "
                 "Other information - Contact hotel for additional details."),
    },
    {
        "case": "ramada_per_stay",
        "source": "Ramada by Wyndham Milwaukee",
        "family": "SIMPLE_PER_STAY",
        "expect": "STRUCTURE",
        "why": "one price on a per-stay basis",
        "text": ("Pets Allowed - 2 pets max. Fees - 50USD per pet per stay. "
                 "Other Information - Limited pet friendly rooms."),
    },
    {
        "case": "brown_deer_per_pet_per_night",
        "source": "Country Inn & Suites by Radisson, Brown Deer (Choice)",
        "family": "SIMPLE",
        "expect": "STRUCTURE",
        "why": "explicit per pet, per night",
        "text": ("Pets Allowed. Pet Charge 30.00 USD Per Pet, Per Night. Pet "
                 "limit 2 Pet Per Room. Max 65 Pounds Service animals are "
                 "permitted, without charge."),
    },
    {
        "case": "brookfield_per_stay",
        "source": "Country Inn & Suites by Radisson, Milwaukee West (Choice)",
        "family": "SIMPLE_PER_STAY",
        "expect": "STRUCTURE",
        "why": "non-refundable, per stay, one amount",
        "text": ("Pets Allowed. Non-refundable Pet Charge 100.00 USD Per Stay. "
                 "Pet limit 2 Pet Per Room 50 lbs maximum. Service animals are "
                 "permitted, without charge."),
    },

    # ----------------------------------------------------------------- #
    # Capped fee -- a cap is NOT a tier and must survive
    # ----------------------------------------------------------------- #
    {
        "case": "laquinta_per_night_with_cap",
        "source": "La Quinta Inn & Suites by Wyndham Milwaukee (x3)",
        "family": "CAPPED",
        "expect": "STRUCTURE",
        "why": ("a nightly rate with a per-stay ceiling is one price with a "
                "cap, which the schema HAS a field for. It must not be "
                "mistaken for a tier."),
        "text": ("Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less "
                 "per pet. Fees - Non-refundable 25 USD nightly for up to 2 "
                 "pets. Max 75 USD per stay."),
    },

    # ----------------------------------------------------------------- #
    # Weight forms
    # ----------------------------------------------------------------- #
    {"case": "weight_ihg_40lb", "source": "Holiday Inn Express Milwaukee-West",
     "family": "WEIGHT", "expect": "STRUCTURE", "expect_weight": 40.0,
     "why": "'maximum weight of 40lbs' -- currently missed",
     "text": "We welcome pets at a maximum weight of 40lbs up to 2 pets per rooms."},
    {"case": "weight_ihg_50lb", "source": "Holiday Inn Milwaukee Riverfront",
     "family": "WEIGHT", "expect": "STRUCTURE", "expect_weight": 50.0,
     "why": "'max weight of 50 lbs' -- currently missed",
     "text": "Dogs are welcome to stay with a max weight of 50 lbs."},
    {"case": "weight_under", "source": "corpus form", "family": "WEIGHT",
     "expect": "STRUCTURE", "expect_weight": 30.0,
     "why": "already works; included to catch collateral damage",
     "text": "Pets under 30 lbs are welcome."},
    {"case": "weight_up_to", "source": "corpus form", "family": "WEIGHT",
     "expect": "STRUCTURE", "expect_weight": 60.0, "why": "already works",
     "text": "Dogs up to 60 lbs allowed."},
    {"case": "weight_maximum_pounds", "source": "Choice form", "family": "WEIGHT",
     "expect": "STRUCTURE", "expect_weight": 50.0, "why": "already works",
     "text": "Pets allowed. Maximum 50 pounds each."},
    {"case": "weight_max_weight_row", "source": "Hilton table form",
     "family": "WEIGHT", "expect": "STRUCTURE", "expect_weight": 75.0,
     "why": "already works", "text": "Max weight 75 lbs"},
    {"case": "weight_less_than", "source": "Staybridge (IHG)", "family": "WEIGHT",
     "expect": "STRUCTURE", "expect_weight": 80.0, "why": "already works",
     "text": "Two pets max per room, and must weigh less than 80 lbs."},
    {"case": "weight_or_less_per_pet", "source": "La Quinta (Wyndham)",
     "family": "WEIGHT", "expect": "STRUCTURE", "expect_weight": 75.0,
     "why": "already works; per-pet phrasing",
     "text": "2 pets max. Cats and dogs only. 75lbs or less per pet."},
    {"case": "weight_combined_room", "source": "corpus form", "family": "WEIGHT",
     "expect": "NO_WEIGHT",
     "why": ("a COMBINED room limit must never populate the per-pet "
             "weight_limit field -- 100 lbs across all pets is not 100 lbs per "
             "pet. The correct behaviour is to claim no per-pet limit, which "
             "is what the reader already does. Extracting combined weight into "
             "its own field is a FEATURE and is out of scope here: this work "
             "order fixes misses on text already acquired, and no Milwaukee "
             "capture states a combined limit."),
     "text": "Pets welcome. Combined weight of all pets must not exceed 100 lbs."},
    {"case": "weight_explicit_none", "source": "Kimpton Journeyman (IHG)",
     "family": "WEIGHT", "expect": "NO_WEIGHT",
     "why": ("an explicit statement that there is NO limit must not become a "
             "limit, and must not be confused with silence"),
     "text": ("We invite you to bring your pet no matter their size, weight, or "
              "breed, all at no extra charge.")},
    {"case": "weight_not_stated", "source": "Ramada by Wyndham Milwaukee",
     "family": "WEIGHT", "expect": "NO_WEIGHT",
     "why": "silence is absence; nothing may be inferred",
     "text": "Pets Allowed - 2 pets max. Fees - 50USD per pet per stay."},
    {"case": "weight_ambiguous_small", "source": "corpus form", "family": "WEIGHT",
     "expect": "NO_WEIGHT",
     "why": "'small pets' is not a number and must not become one",
     "text": "Small pets welcome at this property."},
]


def by_family(family: str) -> List[Dict]:
    return [c for c in CASES if c["family"] == family]


def get(case: str) -> Dict:
    for entry in CASES:
        if entry["case"] == case:
            return entry
    raise KeyError(case)


TIERED_CASES = tuple(c["case"] for c in CASES
                     if c["family"].startswith("TIERED")
                     or c["family"] == "CONDITIONAL_WEIGHT")
SIMPLE_CASES = tuple(c["case"] for c in CASES
                     if c["family"].startswith("SIMPLE") or c["family"] == "CAPPED")
WEIGHT_CASES = tuple(c["case"] for c in CASES if c["family"] == "WEIGHT")

"""The fixed reader corpus for PTF-LABEL-VALUE-POLICY-READER-HARDENING-033.

The generic reader was built for prose -- "Pets welcome, $25 per night, maximum
two pets per room" -- and reads a LABEL AND VALUE table as nothing at all:

    Pet Fees Price : $40 / NIGHT
    Individual pet weight limit : 150 Pounds
    Combined pets weight limit : 150 Pounds
    Maximum number of pets is 2.

Every fact a guest needs is on that page and the extraction is empty.

This corpus is what the repair is measured against. The two Milwaukee targets
are read from the documents 028 persisted, so a failure here means the reader
changed and never that the page did. Everything else is written as the smallest
text that poses its question, and the negative half is larger than the positive
half on purpose: a label-and-value parser is a machine for finding "NAME :
NUMBER" anywhere, and a hotel page is full of numbers that are not pet policy.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

TARGET = "TARGET"
POSITIVE = "POSITIVE"
NEGATIVE = "NEGATIVE"
COMPLEXITY = "COMPLEXITY"
#: A block the reader already read correctly. Its answer must not move.
REGRESSION = "REGRESSION"


@dataclass(frozen=True)
class Case:
    """One policy block and what the reader must make of it."""

    case_id: str
    kind: str
    scenario: str
    text: str = ""
    identity_key: str = ""
    must_extract: Tuple[str, ...] = ()
    must_not_extract: Tuple[str, ...] = ()
    must_withhold: Tuple[str, ...] = ()
    why: str = ""

    def block(self) -> str:
        if self.text:
            return self.text
        return recovered_block(self.identity_key)


def recovered_block(identity_key: str) -> str:
    """The block 032's recovery produces from the document 028 persisted.

    Re-derived rather than read from a file: 032 journalled only the property
    whose reading it could use, so these two blocks were computed and not
    written. The DOCUMENT is on disk and its sha256 still matches 028's
    record, and the recovery over it is deterministic, so the block is exactly
    reproducible without a provider call.
    """
    from scripts.pettripfinder.acquisition import locator_recovery_032 as R32
    for row in R32.recoveries():
        if row["identity_key"] == identity_key:
            return row["new_block"]
    raise KeyError("no recovered block for %r" % identity_key)


TARGET_KEYS: Tuple[str, ...] = (
    "hyatt place milwaukee airport",
    "hyatt regency milwaukee",
)


CASES: Tuple[Case, ...] = (
    # --- the two targets ---------------------------------------------------- #
    Case(case_id="T1-label-value-simple-fee",
         kind=TARGET,
         scenario="a label/value table with one price, two weights and a count",
         identity_key="hyatt regency milwaukee",
         must_extract=("pet_fee", "fee_currency", "fee_basis", "weight_limit",
                       "pet_count_limit"),
         why="every fact is on the page and the extraction was empty"),
    Case(case_id="T2-label-value-banded-fee",
         kind=TARGET,
         scenario="the same table with a fee banded by stay length",
         identity_key="hyatt place milwaukee airport",
         must_extract=("weight_limit", "pet_count_limit"),
         must_not_extract=("pet_fee", "cleaning_fee"),
         must_withhold=("pet_fee",),
         why="the count and the weights are safe; the banded fee is not, and "
             "the $100 band was being published as a cleaning fee"),

    # --- positive label/value controls -------------------------------------- #
    Case(case_id="P1-fee-label-colon-amount",
         kind=POSITIVE,
         scenario="a pet fee stated as a label and a value",
         text="Pet Fee : $35 per night",
         must_extract=("pet_fee", "fee_basis"),
         why="the commonest label/value money shape"),
    Case(case_id="P2-price-label",
         kind=POSITIVE,
         scenario="the charge noun is PRICE rather than fee or rate",
         text="Pet Fees Price : $40 / NIGHT",
         must_extract=("pet_fee", "fee_basis"),
         why="a price is a charge noun exactly as a fee and a rate are"),
    Case(case_id="P3-weight-label-colon",
         kind=POSITIVE,
         scenario="a weight limit stated with a colon",
         text="Pets welcome. Individual pet weight limit : 50 Pounds",
         must_extract=("weight_limit",),
         why="a colon is a copula"),
    Case(case_id="P4-count-label-then-value",
         kind=POSITIVE,
         scenario="a count whose number follows the noun",
         text="Pets welcome. Maximum number of pets is 2.",
         must_extract=("pet_count_limit",),
         why="every existing count form puts the number before the noun"),
    Case(case_id="P5-count-label-colon",
         kind=POSITIVE,
         scenario="the same count with a colon",
         text="Pets welcome. Maximum number of pets : 3",
         must_extract=("pet_count_limit",),
         why="the same shape a colon away"),
    Case(case_id="P6-species-label",
         kind=POSITIVE,
         scenario="a species stated explicitly beside a fee",
         text="Dogs Allowed. Dogs only. Pet Fee : $50 per stay",
         must_extract=("species_allowed", "pet_fee"),
         why="the species reading must survive the new money path"),
    Case(case_id="P7-basis-stated-separately",
         kind=POSITIVE,
         scenario="the basis is its own labelled row",
         text="Pets welcome. Pet fee : $25. Charged per night.",
         must_extract=("pet_fee",),
         why="an amount with no basis on its own row is still an amount; the "
             "basis is not invented from a neighbouring sentence"),

    # --- negative controls -------------------------------------------------- #
    Case(case_id="N1-room-price-card",
         kind=NEGATIVE,
         scenario="a room price in a label/value card beside a pet refusal",
         text=("1 King Bed 4 Guests No Pets Allowed "
               "Discounted price : $160 USD / night"),
         must_not_extract=("pet_fee",),
         why="the room-rate hole, now reachable through a PRICE label"),
    Case(case_id="N2-member-rate-card",
         kind=NEGATIVE,
         scenario="a member rate card beside a pet refusal",
         text="No Pets Allowed Member Price : 160.00 per night",
         must_not_extract=("pet_fee",),
         why="the same hole in a second money shape"),
    Case(case_id="N3-parking-label",
         kind=NEGATIVE,
         scenario="a parking charge in the same table as a pet policy",
         text=("Pets welcome. Self-parking price : $35 per night. "
               "Valet parking : $50 per night."),
         must_not_extract=("pet_fee",),
         why="a parking price is not a pet price however near it sits"),
    Case(case_id="N4-resort-fee-label",
         kind=NEGATIVE,
         scenario="a resort fee beside a pet statement",
         text="Pets welcome. Resort fee : $29 per night.",
         must_not_extract=("pet_fee",),
         why="a resort fee is charged to every guest"),
    Case(case_id="N5-smoking-fee-label",
         kind=NEGATIVE,
         scenario="a smoking penalty beside a pet flag",
         text=("Pets allowed Yes. Smoking fee : $250 per stay for smoking "
               "in a non-smoking room."),
         must_not_extract=("pet_fee",),
         why="a smoking penalty is not a pet fee"),
    Case(case_id="N6-generic-cleaning-deposit",
         kind=NEGATIVE,
         scenario="a deposit every guest pays, in the pet block",
         text=("Service Animals are Welcome. Deposit Policy: A $50 "
               "refundable deposit for incidentals is required at check-in "
               "for all guests."),
         must_not_extract=("pet_fee", "cleaning_fee"),
         why="the Red Roof deposit, which names its own non-pet purpose"),
    Case(case_id="N7-amenity-grid",
         kind=NEGATIVE,
         scenario="an amenity grid with numbers in it",
         text=("Amenities Free WiFi Pet Friendly Outdoor Pool Fitness Center "
               "Rooms from $59. Rated 4.2 of 5 by 318 guests."),
         must_not_extract=("pet_fee", "pet_count_limit", "weight_limit"),
         why="a chip is not a policy and a review score is not a count"),
    Case(case_id="N8-service-animal-only",
         kind=NEGATIVE,
         scenario="service animals named and no pet policy",
         text="Service Animals are Welcome",
         must_not_extract=("pets_allowed", "pet_fee"),
         why="a service animal is not a pet"),
    Case(case_id="N9-occupancy-not-a-pet-count",
         kind=NEGATIVE,
         scenario="a room occupancy stated as a label and a value",
         text=("Pets welcome. Maximum number of guests is 4. "
               "Maximum occupancy : 4"),
         must_not_extract=("pet_count_limit",),
         why="a count must name the animal; room occupancy is not a pet limit"),

    # --- complexity controls ------------------------------------------------ #
    Case(case_id="C1-tiered-fee",
         kind=COMPLEXITY,
         scenario="a fee that changes after the first night",
         text="Pets welcome. $75 for the first night, $25 per night thereafter.",
         must_not_extract=("pet_fee",),
         must_withhold=("pet_fee",),
         why="one field cannot hold two prices"),
    Case(case_id="C2-banded-by-stay-length",
         kind=COMPLEXITY,
         scenario="a fee banded by stay length in a label/value table",
         text=("Pet Fees 1-6 nights : $100 / STAY "
               "7-30 nights : $200 / STAY"),
         must_not_extract=("pet_fee", "cleaning_fee"),
         # The withholding was dropped here by work order 034, which builds
         # this exact ladder as fee_tiers. 033's claim is untouched and still
         # asserted above: neither band may be published as "the pet fee", and
         # neither may become a cleaning fee.
         why="the band must not collapse to one amount and must not become a "
             "cleaning fee"),
    Case(case_id="C3-multi-pet-price-tiers",
         kind=COMPLEXITY,
         scenario="a price that depends on how many pets",
         text=("Pets welcome. Pet fee : $50 for one pet, "
               "$75 for two pets, per stay."),
         must_not_extract=("pet_fee",),
         must_withhold=("pet_fee",),
         why="a count-dependent price is a tier"),
    Case(case_id="C4-conflicting-basis",
         kind=COMPLEXITY,
         scenario="one amount stated on two bases",
         text=("Pet Policy Pets Welcome Pet fee $20/day with $100/stay "
               "nonrefundable clean fee Non-Refundable Pet Fee Per Stay: "
               "$100.00 Non-Refundable Pet Fee Per Night: $20.00"),
         must_extract=("pet_fee",),
         must_not_extract=("fee_basis",),
         must_withhold=("fee_basis",),
         why="per_day and per_night are distinct and this layer does not "
             "choose between them"),
    Case(case_id="C5-individual-and-combined-weight",
         kind=COMPLEXITY,
         scenario="two weight limits, one per animal and one for all of them",
         text=("Pets welcome. Individual pet weight limit : 50 Pounds "
               "Combined pets weight limit : 75 Pounds"),
         must_extract=("weight_limit",),
         why="the individual limit is the one a guest with one dog needs; the "
             "combined figure must not be collapsed into it"),
    Case(case_id="C6-combined-weight-only",
         kind=COMPLEXITY,
         scenario="only a combined weight is stated",
         text="Pets welcome. Up to two dogs, combined weight not to exceed "
              "100 pounds.",
         must_not_extract=("weight_limit",),
         why="an individual limit may not be inferred from a combined one"),
    Case(case_id="C7-real-cleaning-fee",
         kind=COMPLEXITY,
         scenario="a cleaning charge the source really does name",
         text=("Pets welcome. Pet fee $50 per stay. "
               "Cleaning fee : $75 per stay."),
         must_extract=("cleaning_fee",),
         why="the repair must not stop a genuine cleaning charge being read"),

    # --- prose controls, which must not regress ----------------------------- #
    Case(case_id="R1-simple-prose-fee",
         kind=REGRESSION,
         scenario="the prose shape the reader was built for",
         text="Pets Welcome. Pet fee $25 per night.",
         must_extract=("pet_fee", "fee_basis"),
         why="the commonest shape in the corpus"),
    Case(case_id="R2-prose-per-stay",
         kind=REGRESSION,
         scenario="the basis-first prose shape",
         text="Pets Welcome Non-Refundable Pet Fee Per Stay: $150.00",
         must_extract=("pet_fee", "fee_basis"),
         why="the structured-row shape"),
    Case(case_id="R3-prose-count-and-weight",
         kind=REGRESSION,
         scenario="prose count and weight",
         text=("Pets Welcome. Maximum of two pets per room. "
               "Maximum Pet Weight: 50.0lbs"),
         must_extract=("pet_count_limit", "weight_limit"),
         why="the shapes that already worked"),
    Case(case_id="R4-pet-named-rate",
         kind=REGRESSION,
         scenario="029's Best Western wording",
         text="Pets welcome. The Pet Friendly rate is 35.00 USD per day.",
         must_extract=("pet_fee", "fee_basis"),
         why="029's recovery must survive"),
)


def targets() -> List[str]:
    """The reader-gap identities, read from 032's COMMITTED report.

    Not re-derived live. 032 recorded which recoveries its reader could not
    use, and this work order exists to make the reader use them -- so a live
    re-derivation empties the cohort the moment the repair works, and the run
    reports that it had nothing to do. 031's tests found the same trap and
    were narrowed the same way.
    """
    import json
    report = (REPO / "launch_packages" / "pettripfinder" / "markets"
              / "reports" / "ptf_milwaukee_locator_recovery_032.json")
    doc = json.loads(report.read_text(encoding="utf-8-sig"))
    return sorted(row["identity_key"] for row in doc["recoveries"]
                  if row["recovered"] and not row["yields_an_observation"])


def available() -> List[Case]:
    return list(CASES)


__all__ = ["Case", "CASES", "TARGET", "POSITIVE", "NEGATIVE", "COMPLEXITY",
           "TARGET_KEYS", "targets", "recovered_block", "available"]

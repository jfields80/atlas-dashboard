"""The fixed reader corpus for PTF-GENERIC-READER-BEST-WESTERN-HARDENING-029.

A reader change is only safe if the things it must NOT change are pinned before
it is made. This is that pin: two target blocks that must improve, one refusal
from the same brand that must not move, and one case for each protection the
reader has accumulated -- tiered, banded, multi-component, contradictory basis,
capped, amenity-only, service-animal-only, and the room-rate hole.

The two targets are the real persisted 028 blocks, read off disk by identity so
they cannot drift from what was actually captured. Everything else is written
here as the smallest text that poses its question.

WHY THE ROOM-RATE CONTROLS ARE IN A READER CORPUS
--------------------------------------------------
The Best Western surfaces call their pet charge "the Pet Friendly rate", and
the guard that stops a nightly ROOM rate being published as a pet fee vetoes
exactly that wording. Any repair to one is a risk to the other, so both live in
one corpus and are measured together.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

TARGET = "TARGET"
CONTROL = "CONTROL"
PROTECTION = "PROTECTION"


@dataclass(frozen=True)
class Case:
    """One policy block and what the reader must make of it."""

    case_id: str
    kind: str
    scenario: str
    #: Written here, or read from a persisted capture by identity.
    text: str = ""
    identity_key: str = ""
    #: Fields that must appear in the extraction after the repair.
    must_extract: Tuple[str, ...] = ()
    #: Fields that must NOT appear -- the protections.
    must_not_extract: Tuple[str, ...] = ()
    #: Fields that must be withheld after the repair.
    must_withhold: Tuple[str, ...] = ()
    why: str = ""

    def block(self) -> str:
        if self.text:
            return self.text
        return persisted_block(self.identity_key)


def persisted_block(identity_key: str) -> str:
    """The policy block a run actually captured, read from its own artifact.

    Never re-fetched and never re-located: the canonical locator recorded this
    boundary at capture time and re-locating would answer a different question.
    """
    from scripts.pettripfinder.acquisition import premium_resolution_028 as P28
    for row in P28.journal_rows():
        if row["identity_key"] != identity_key:
            continue
        attempt = row["canonical_artifacts"].get("attempt_dir")
        if not attempt:
            break
        return (REPO / attempt / "policy-block.txt").read_text(encoding="utf-8")
    raise KeyError("no persisted policy block for %r" % identity_key)


#: The two under-read blocks, derived in ``targets()`` and named here only so
#: the corpus can be read. Nothing selects them by name.
TARGET_KEYS: Tuple[str, ...] = (
    "best western plus milwaukee airport hotel and conference center",
    "best western waukesha grand",
)

REFUSAL_KEY = "best western germantown inn"


CASES: Tuple[Case, ...] = (
    # --- the two targets ---------------------------------------------------- #
    Case(case_id="T1-multi-component-daily-rate",
         kind=TARGET,
         scenario="count, weight, species and a daily rate, plus a deposit",
         identity_key=TARGET_KEYS[0],
         must_extract=("pets_allowed", "pet_count_limit", "weight_limit"),
         why="the page states two dogs, eighty pounds and a daily rate; the "
             "reader represented the allowed flag alone"),
    Case(case_id="T2-single-daily-rate",
         kind=TARGET,
         scenario="the same wording with one charge and no deposit",
         identity_key=TARGET_KEYS[1],
         must_extract=("pets_allowed", "pet_count_limit", "weight_limit",
                       "pet_fee", "fee_basis"),
         why="one stated amount on one stated basis, and nothing competing"),

    # --- the same brand's refusal ------------------------------------------ #
    Case(case_id="C1-brand-refusal",
         kind=CONTROL,
         scenario="the same brand refusing pets outright",
         identity_key=REFUSAL_KEY,
         must_extract=("pets_allowed",),
         must_not_extract=("pet_fee", "pet_count_limit", "weight_limit"),
         why="a refusal must stay a refusal however much the reader learns "
             "about the brand's other wording"),

    # --- ordinary policies that must not regress ---------------------------- #
    Case(case_id="C2-simple-per-night",
         kind=CONTROL,
         scenario="a plain nightly fee",
         text="Pets Welcome. Pet fee $25 per night.",
         must_extract=("pets_allowed", "pet_fee", "fee_basis"),
         why="the commonest shape in the corpus"),
    Case(case_id="C3-simple-per-stay",
         kind=CONTROL,
         scenario="a plain per-stay fee",
         text="Pets Welcome Non-Refundable Pet Fee Per Stay: $150.00",
         must_extract=("pets_allowed", "pet_fee", "fee_basis"),
         why="the basis-first shape"),
    Case(case_id="C4-capped-fee",
         kind=CONTROL,
         scenario="a nightly fee with a stated ceiling",
         text=("Pets welcome. $20 per pet per night, "
               "not to exceed $100 per pet per stay."),
         must_extract=("pets_allowed", "pet_fee", "fee_cap"),
         why="CEILING is not PRICE, and both are recorded"),
    Case(case_id="C5-count-limit",
         kind=CONTROL,
         scenario="a stated pet count",
         text="Pets Welcome. Maximum of two pets per room.",
         must_extract=("pets_allowed", "pet_count_limit", "pet_count_scope"),
         why="the count shape that already worked"),
    Case(case_id="C6-weight-limit",
         kind=CONTROL,
         scenario="a stated maximum weight",
         text="Pets Welcome. Maximum Pet Weight: 50.0lbs",
         must_extract=("pets_allowed", "weight_limit"),
         why="the weight shape that already worked"),
    Case(case_id="C7-dogs-only",
         kind=CONTROL,
         scenario="one species named",
         text="Dogs Allowed. Dogs only, no other pets are allowed.",
         must_extract=("pets_allowed", "species_allowed"),
         why="a species restriction is not a refusal"),
    Case(case_id="C8-dogs-and-cats",
         kind=CONTROL,
         scenario="two species named",
         text="We welcome dogs and cats. Pet fee $50 per stay.",
         must_extract=("pets_allowed", "pet_fee"),
         why="the fee and the flag are read. ``species_allowed`` is NOT "
             "asserted here: this wording is not among the species forms the "
             "reader recognises, which it did not recognise before this work "
             "order either. Recorded as a measured gap rather than repaired, "
             "because widening species parsing is not what 029 was asked to "
             "do and it has its own corpus of ways to be wrong"),
    Case(case_id="C9-no-fee-stated",
         kind=CONTROL,
         scenario="pets allowed and nothing about money",
         text="Pets are welcome at our hotel. Please notify us in advance.",
         must_extract=("pets_allowed",),
         must_not_extract=("pet_fee", "fee_basis"),
         must_withhold=("pet_fee",),
         why="silence about a fee is absence, never zero"),

    # --- the protections ---------------------------------------------------- #
    Case(case_id="P1-tiered-fee",
         kind=PROTECTION,
         scenario="a fee that changes with the number of nights",
         text=("Pets welcome. $75 for the first night, "
               "$25 per night thereafter."),
         must_not_extract=("pet_fee",),
         must_withhold=("pet_fee",),
         why="one field cannot hold two prices"),
    Case(case_id="P2-banded-fee",
         kind=PROTECTION,
         scenario="a fee stated in duration bands",
         text=("Pets welcome. Pet fee: $50 (1-4 nights), $100 (5+ nights)."),
         must_not_extract=("pet_fee",),
         must_withhold=("pet_fee",),
         why="a band is a tier written as a table"),
    Case(case_id="P3-multi-component-fee",
         kind=PROTECTION,
         scenario="a nightly fee plus a separate non-refundable charge",
         text=("Pets welcome. A $125 non-refundable pet deposit and a $20 "
               "daily pet fee apply."),
         must_not_extract=("pet_fee",),
         must_withhold=("pet_fee",),
         why="two components cannot be one field"),
    Case(case_id="P4-contradictory-basis",
         kind=PROTECTION,
         scenario="one amount stated on two bases",
         text=("Pet Policy Pets Welcome Pet fee $20/day with $100/stay "
               "nonrefundable clean fee Non-Refundable Pet Fee Per Stay: "
               "$100.00 Non-Refundable Pet Fee Per Night: $20.00"),
         must_extract=("pets_allowed", "pet_fee"),
         must_not_extract=("fee_basis",),
         must_withhold=("fee_basis",),
         why="per_day and per_night are distinct and this layer does not "
             "choose between them"),
    Case(case_id="P5-amenity-only",
         kind=PROTECTION,
         scenario="an amenity chip and nothing else",
         text="Pet Friendly",
         must_not_extract=("pet_fee", "pet_count_limit", "weight_limit"),
         why="a chip is not a policy"),
    Case(case_id="P6-service-animal-only",
         kind=PROTECTION,
         scenario="service animals named and no pet policy",
         text="Service Animals are Welcome",
         must_not_extract=("pets_allowed", "pet_fee"),
         why="a service animal is not a pet and the ADA is not a policy"),
    Case(case_id="P7-room-rate-with-refusal",
         kind=PROTECTION,
         scenario="a discounted ROOM rate beside a pet refusal",
         text=("1 King Bed 4 Guests No Pets Allowed "
               "Discounted rate: $160 USD /night"),
         must_not_extract=("pet_fee",),
         why="the hole the rate-marker guard exists to keep shut"),
    Case(case_id="P8-room-rate-member",
         kind=PROTECTION,
         scenario="a member ROOM rate beside a pet refusal",
         text="No Pets Allowed Member Rate 160.00 per night",
         must_not_extract=("pet_fee",),
         why="the same hole in a second money shape"),
    Case(case_id="P9-room-rate-strikethrough",
         kind=PROTECTION,
         scenario="two ROOM rates beside a pet refusal",
         text=("No Pets Allowed Strikethrough Rate: $172 "
               "Discounted rate: $160 /night"),
         must_not_extract=("pet_fee",),
         why="the same hole with a competing amount"),
    Case(case_id="P10-combined-weight",
         kind=PROTECTION,
         scenario="a weight stated for two animals together",
         text=("Pets welcome. Up to two dogs, combined weight not to exceed "
               "100 pounds."),
         must_extract=("pets_allowed", "pet_count_limit"),
         must_not_extract=("weight_limit",),
         why="an individual limit may not be inferred from a combined one"),
)


def targets() -> List[str]:
    """The under-read identities, derived from 028 rather than listed.

    A Best Western row that 028 recorded as publication grade and whose audit
    verdict was a reader-or-locator issue is under-read by definition: the page
    arrived, the identity bound, a policy block was located, and the reader
    represented nothing a guest could use.
    """
    from scripts.pettripfinder.acquisition import premium_resolution_028 as P28
    found: List[str] = []
    for row in P28.journal_rows():
        audit = P28.premium_audit(row)
        if (row["brand"] == "BEST_WESTERN"
                and row["publication_grade"]
                and audit["verdict"]
                == P28.PREMIUM_ACCESS_BUT_READER_OR_LOCATOR_ISSUE):
            found.append(row["identity_key"])
    return sorted(found)


def available() -> List[Case]:
    return [case for case in CASES if case.text or case.identity_key]


__all__ = ["Case", "CASES", "TARGET", "CONTROL", "PROTECTION", "targets",
           "persisted_block", "available", "TARGET_KEYS", "REFUSAL_KEY"]

# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FIRECRAWL-RATE-LIMIT-RECOVERY-010, Phase 6.

Detroit's position after the recovery, and the one operational question:
is a Bright Data pilot justified?

CANDIDATES ARE COUNTED BY DISTINCT IDENTITY, not by attempt. Pass 008 bought
two pages twice, and a market that counts those twice would report inventory it
does not have. Nothing here is applied to authority.

THE FIRECRAWL RATE IS NOT CARRIED ACROSS TO THE BRIGHT DATA POPULATION. Those
are Marriott and Hilton rows plus registry-deferred families -- a different
population reached through a different provider past different defences. What
the corrected Firecrawl measurement supports is a decision about whether
Detroit is worth continuing to invest in at all; the pilot exists precisely
because the Bright Data rate is UNKNOWN and has to be measured small.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FIRECRAWL-RATE-LIMIT-RECOVERY-010"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
OUT_PATH = LP / "detroit_ann_arbor_decision_point_010.json"

CLASSIFICATIONS = (
    ("008", LP / "detroit_ann_arbor_firecrawl_classification_008.json"),
    ("009", LP / "detroit_ann_arbor_retry_classification_009.json"),
    ("010", LP / "detroit_ann_arbor_rate_limit_classification_010.json"),
)

#: Counted from the committed authority under 009. Unchanged by this order,
#: which applies nothing.
BRAND_WALL_ROWS = 69
REGISTRY_DEFERRED_ROWS = 43
ROUTING_REPAIR_ROWS = 2
POLICY_NOT_FOUND_HOLDS = 2
CENSUS_WITHOUT_ROUTE = 45

USD_PER_CREDIT = 0.0721333333333333 / 0.54
CUMULATIVE_CREDITS = 62.0 + 20.0 + 29.0


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def run() -> None:
    authority = load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]
    exclusions = load(LP / "markets" / "authority" / MARKET
                      / "hotel_exclusions.json")["exclusions"]
    approved_pet = {row["identity_key"] for row in authority}
    approved_no = {row["normalized_name"] for row in exclusions}

    # One verdict per IDENTITY, latest pass wins: a later pass re-read the same
    # page against a corrected gate, so it supersedes what the earlier one
    # concluded about that identity.
    verdict: Dict[str, Dict] = {}
    for label, path in CLASSIFICATIONS:
        for result in load(path)["results"]:
            if result["class"] in ("PET_FRIENDLY", "VERIFIED_NO_PETS", "HOLD"):
                verdict[result["identity_key"]] = dict(result, _pass=label)

    new_pet = {key for key, row in verdict.items()
               if row["class"] == "PET_FRIENDLY"
               and key not in approved_pet and key not in approved_no}
    new_no = {key for key, row in verdict.items()
              if row["class"] == "VERIFIED_NO_PETS"
              and key not in approved_pet and key not in approved_no}
    holds = {key for key, row in verdict.items() if row["class"] == "HOLD"}

    by_pass = Counter(row["_pass"] for row in verdict.values()
                      if row["class"] in ("PET_FRIENDLY", "VERIFIED_NO_PETS"))

    projected_pet = len(approved_pet) + len(new_pet)
    projected_no = len(approved_no) + len(new_no)
    bright_data = REGISTRY_DEFERRED_ROWS + BRAND_WALL_ROWS

    position = OrderedDict([
        ("existing_approved_pet_friendly", len(approved_pet)),
        ("new_pet_friendly_candidates", len(new_pet)),
        ("existing_verified_no_pets", len(approved_no)),
        ("new_verified_no_pets_candidates", len(new_no)),
        ("candidates_by_pass", dict(by_pass)),
        ("counted_by", "DISTINCT IDENTITY, not attempt: Pass 008 bought two "
                       "pages twice and counting those twice would report "
                       "inventory Detroit does not have"),
        ("total_resolved_if_founder_approves",
         projected_pet + projected_no),
        ("projected_pet_friendly", projected_pet),
        ("projected_verified_no_pets", projected_no),
        ("holds_awaiting_founder", len(holds)),
        ("unresolved", OrderedDict([
            ("brightdata_class", bright_data),
            ("routing_repair", ROUTING_REPAIR_ROWS),
            ("policy_not_found_source_silence", POLICY_NOT_FOUND_HOLDS),
            ("census_without_a_route", CENSUS_WITHOUT_ROUTE),
        ])),
    ])

    # ---- the one operational question ---------------------------------- #
    firecrawl_pet_rate = len(new_pet) / max(1, len(new_pet) + len(new_no))
    decision = OrderedDict([
        ("question",
         "does the resulting Detroit inventory justify proceeding to a Bright "
         "Data pilot?"),
        ("answer", "YES"),
        ("why",
         "Detroit clears the threshold on its own numbers. Approving the clean "
         "candidates takes pet-friendly from %d to %d -- the listings a "
         "pet-travel directory exists to show -- and total resolved inventory "
         "to %d. A market at that size is worth extending; the question was "
         "open while Detroit looked like a no-pets market, and the recovery "
         "cohort answered it: %d of the %d rows it read are pet-friendly."
         % (len(approved_pet), projected_pet,
            projected_pet + projected_no, len(new_pet),
            len(new_pet) + len(new_no))),
        ("what_changed_the_picture",
         "Pass 009 read 18 properties and found ZERO pet-friendly, which "
         "pointed at a no-pets market. That cohort was Holiday Inn Express and "
         "Comfort Inn -- limited-service brands. This cohort reached the "
         "extended-stay and boutique names (Staybridge, EVEN, Hotel Indigo, "
         "Suburban Studios) and %d of %d are pet-friendly. The market is not "
         "uniform, and a rate measured on one brand mix does not describe "
         "another."
         % (len(new_pet), len(new_pet) + len(new_no))),
        ("what_this_does_NOT_license",
         "extrapolating the Firecrawl rate to Marriott and Hilton. Those are a "
         "different family population reached through a different provider "
         "past different defences, and the %d brand-wall rows have never been "
         "attempted at all. The pilot exists BECAUSE that rate is unknown."
         % BRAND_WALL_ROWS),
        ("recommended_pilot", OrderedDict([
            ("run", False),
            ("status", "RECOMMENDATION ONLY -- NOT EXECUTED, NOT AUTHORISED"),
            ("rows", 12),
            ("why_12", "inside the 10-15 the order allows, and enough that a "
                       "Wilson interval on the result is narrow enough to size "
                       "the remaining %d rows without another pilot"
                       % bright_data),
            ("composition", "stratified, not the first 12 by name: 6 Marriott "
                            "and 6 Hilton, since they are the two brand walls "
                            "and may behave differently from each other"),
            ("what_it_measures", "whether the managed browser reaches these "
                                 "two brands at all, and at what cost per "
                                 "attempt -- the access question first, the "
                                 "pet-friendly rate second"),
            ("do_not_size_the_full_cohort_from_it_until",
             "the pilot's own Wilson LOWER bound is known; sizing %d rows on a "
             "12-row point estimate is the mistake this project has already "
             "made once" % bright_data),
        ])),
    ])

    write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-decision-point/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("note",
         "Detroit's position after the rate-limit recovery. NOTHING IS APPLIED "
         "TO AUTHORITY by this order: every candidate is awaiting founder "
         "approval, and the pilot below is a recommendation that was not run."),
        ("cumulative_firecrawl", OrderedDict([
            ("attempts", 65 + 49 + 29),
            ("credits", CUMULATIVE_CREDITS),
            ("usd", round(CUMULATIVE_CREDITS * USD_PER_CREDIT, 2)),
        ])),
        ("position", position),
        ("decision", decision),
    ]))

    print("=== Phase 6: Detroit decision point ===")
    print("  approved pet-friendly   : %d  (+%d candidates -> %d)"
          % (len(approved_pet), len(new_pet), projected_pet))
    print("  approved verified no-pets: %d  (+%d candidates -> %d)"
          % (len(approved_no), len(new_no), projected_no))
    print("  total resolved if approved:", projected_pet + projected_no)
    print("  holds awaiting founder  :", len(holds))
    print("  bright-data class       :", bright_data)
    print("  routing repair          :", ROUTING_REPAIR_ROWS)
    print("  census without a route  :", CENSUS_WITHOUT_ROUTE)
    print()
    print("  BRIGHT DATA PILOT JUSTIFIED:", decision["answer"],
          "-- recommend %d rows (6 Marriott / 6 Hilton), NOT executed"
          % decision["recommended_pilot"]["rows"])
    print("wrote", OUT_PATH.name)


if __name__ == "__main__":
    run()

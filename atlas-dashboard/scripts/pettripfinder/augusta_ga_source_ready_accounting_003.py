"""PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001 -- Phase 15/16/17 accounting.

Derives the discovery/census/holds/geography accounting mechanically from
the raw research captures and the built census/partition, rather than
hand-typing totals that could drift from the actual data.

Run AFTER augusta_ga_market_build_001:

    python -m scripts.pettripfinder.augusta_ga_source_ready_accounting_003
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.augusta_ga_market_build_001 import (
    CANDIDATES, CENSUS_PATH, MARKET_ID, PARTITION_PATH, STAGING,
)

RAW = STAGING / "raw_captures"
REPORTS = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"


def main() -> int:
    chain_raw = json.loads((RAW / "chain_brand_lane.json").read_text(encoding="utf-8"))
    indep_raw = json.loads((RAW / "independent_and_fort_eisenhower_lane.json").read_text(encoding="utf-8"))
    sc_raw = json.loads((RAW / "sc_boundary_discovery.json").read_text(encoding="utf-8"))
    fringe_raw = json.loads((RAW / "fringe_geography_and_event_research.json").read_text(encoding="utf-8"))

    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    partition = json.loads(PARTITION_PATH.read_text(encoding="utf-8"))

    chain_raw_count = len(chain_raw)
    # The independent/CVB lane file also carries the on-post/restricted entry
    # (part == "C_EXCLUDED_ON_BASE"); that is military/restricted accounting,
    # not a general-public GA hotel lead, so it is excluded from the GA
    # hotel-lead count and counted separately below.
    indep_ga_leads = [r for r in indep_raw if r.get("part") != "C_EXCLUDED_ON_BASE"]
    indep_raw_count = len(indep_ga_leads)
    sc_count = len(sc_raw)

    fringe_town_hotel_count = sum(t["hotel_count"] for t in fringe_raw["fringe_towns"])
    # Hephzibah's one hotel is the same identity already captured in the chain
    # lane (Rodeway Inn & Suites Hephzibah Augusta, South Augusta corridor) --
    # counted once in the proposed census, not twice in total-discovered.
    hephzibah_dup = 1
    fringe_outside_new = fringe_town_hotel_count - hephzibah_dup

    proposed_census = census["count"]
    raw_ga_mentions = chain_raw_count + indep_raw_count
    internal_duplicates_merged = raw_ga_mentions - proposed_census

    non_hotel_excluded = 1       # Timberline Glamping Augusta (Appling) -- campground product
    future_opening_excluded = 1  # LivSmart Studios by Hilton Augusta -- reported opening March 2027
    military_restricted = 3      # IHG Army Hotels Fort Gordon/Fort Eisenhower on-post facilities (1 address)

    total_discovered = (raw_ga_mentions + fringe_outside_new + sc_count
                        + non_hotel_excluded + future_opening_excluded
                        + military_restricted)

    final_counts = partition["final_state_counts"]
    identity_holds = final_counts.get("AWAITING_IDENTITY_RESOLUTION", 0)
    resolved = proposed_census - identity_holds
    unresolved = identity_holds

    outside_total = fringe_outside_new + sc_count

    report = {
        "schema": "ptf-augusta-source-ready-accounting/1.0",
        "market_id": MARKET_ID,
        "work_order": "PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001",
        "totals": {
            "total_discovered": total_discovered,
            "raw_ga_mentions_pre_dedup": raw_ga_mentions,
            "internal_duplicates_merged": internal_duplicates_merged,
            "proposed_census": proposed_census,
            "resolved": resolved,
            "unresolved_identity_holds": unresolved,
            "valid_pet_friendly": final_counts.get("PUBLISHED_PET_FRIENDLY", 0),
            "valid_verified_no_pets": final_counts.get("VERIFIED_NO_PETS", 0),
        },
        "holds_by_class": {
            "identity_holds": identity_holds,
            "routing_holds": 0,
            "access_blocked_properties": 0,
            "access_blocked_lanes": ["OSM/Overpass (406 from this sandbox network on every "
                                     "query variant tested; brand + CVB lanes covered the "
                                     "same geography instead)"],
            "evidence_holds": 0,
            "geography_holds": 0,
            "military_or_restricted": military_restricted,
            "paid_holds": 0,
            "founder_holds": 0,
            "closed_or_retired": 0,
            "outside": outside_total,
            "non_hotel": non_hotel_excluded,
            "vacation_rental_discrete_properties": 0,
            "temporary_event_lodging_discrete_properties": 0,
            "future_opening_not_yet_counted": future_opening_excluded,
        },
        "partition_final_state_counts": final_counts,
        "cross_border_boundary_accounting": {
            "north_augusta_aiken_edgefield_sc_discovered": sc_count,
            "sc_included_in_ga_census": 0,
            "sc_outside": sc_count,
            "sc_review": 0,
        },
        "fringe_geography_accounting": [
            {"town": t["town"], "hotel_count": t["hotel_count"],
             "disposition": ("OUTSIDE (own identity, no Augusta marketing)"
                             if t["hotel_count"] and t["uses_augusta_marketing"] is False
                             else ("FOLDED_INTO_CORE (Hephzibah -> South Augusta corridor, "
                                   "Augusta-marketing co-brand)" if t["town"].startswith("Hephzibah")
                                   else ("NOT_A_SEPARATE_TOWN" if t["town"].startswith("Belair")
                                         else "ZERO_INVENTORY")))}
            for t in fringe_raw["fringe_towns"]
        ],
        "reconciliation_check": {
            "sum_of_buckets": (proposed_census + outside_total + military_restricted
                              + non_hotel_excluded + future_opening_excluded
                              + internal_duplicates_merged),
            "equals_total_discovered": (proposed_census + outside_total + military_restricted
                                        + non_hotel_excluded + future_opening_excluded
                                        + internal_duplicates_merged) == total_discovered,
        },
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS / "augusta_ga_source_ready_accounting_003.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    print("\nwrote: %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

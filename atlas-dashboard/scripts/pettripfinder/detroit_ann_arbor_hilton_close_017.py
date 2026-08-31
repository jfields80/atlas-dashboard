# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-SCALE-017, Phases 6 to 9.

Classifies the final Hilton cohort, closes Hilton, rebuilds the consolidated
Bright Data application inventory, and states Detroit's projected next position.
NO AUTHORITY IS APPLIED.

THIS RUN DEGRADED, AND THAT IS REPORTED RATHER THAN AVERAGED IN. Nine of
thirteen attempts failed with infrastructure signatures -- ``Page.goto: Timeout
120000ms exceeded``, ``TargetClosedError`` (the managed browser session died),
and pages that arrived unhydrated. None is a property-specific or
template-specific refusal, and order 016 read ten properties on the SAME host
and the SAME sub-brands with zero failures eleven minutes of wall-clock earlier.

So these failures are not a measurement of Hilton's pages, and folding them into
Hilton's yield would reverse a SCALE decision on evidence about session health.
Both denominators are published, as this market did for the parser defect in
order 008: the ALL-ATTEMPTS rate is what the money bought, and the
REACHED-A-PAGE rate is what the properties say.

THE CAUSE IS NOT KNOWN AND IS NOT GUESSED. Two candidates are recorded. Vendor
or network degradation in that window is one. The other is this order's own
instrument: the live balance guard shells out to the Bright Data CLI before
every attempt and nearly doubled the cycle time, 72s to 127s. It runs BETWEEN
attempts and so cannot close a live session, which argues against it -- but it
changed run conditions materially and that is not something to wave away.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_firecrawl_classification_008 as C8,
    detroit_ann_arbor_brightdata_measure_013 as M13,
    detroit_ann_arbor_brightdata_pilot_013 as P13,
    detroit_ann_arbor_brightdata_pilot_014 as P14,
    detroit_ann_arbor_hilton_scale_017 as S17)

MARKET = S17.MARKET
WORK_ORDER = S17.WORK_ORDER
LANE = S17.LANE
AS_OF = S17.AS_OF

LP = S17.LP
RUN_DIR_017 = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
               / "detroit-ann-arbor-hilton-017")
CLASS_017 = LP / "detroit_ann_arbor_hilton_classification_017.json"
FINAL = LP / "detroit_ann_arbor_hilton_closure_017.json"
INVENTORY = LP / "detroit_ann_arbor_brightdata_application_inventory_017.json"
NEXT_STATE = LP / "detroit_ann_arbor_next_state_017.json"

SOURCES = (
    LP / "detroit_ann_arbor_brightdata_classification_013.json",
    LP / "detroit_ann_arbor_brightdata_classification_014.json",
    LP / "detroit_ann_arbor_marriott_classification_015.json",
    LP / "detroit_ann_arbor_hilton_classification_016.json",
)

#: Prepaid balance, the authoritative spend control since order 015.
BALANCE_SPENT_017 = round(10.10 - 9.41, 2)
BALANCE_SPENT_TOTAL = round(5.32 + BALANCE_SPENT_017, 2)
BILLED_TOTAL = 16 + 16 + 16 + 10 + 13

#: Adapter outcomes that mean the SESSION failed, not the page. A page that
#: never arrived says nothing about the hotel whose page it was.
INFRASTRUCTURE_OUTCOMES = ("NAVIGATION_FAILED", "UNHYDRATED", "TIMEOUT",
                           "CAPTURE_FAILED", "BLANK_PAGE",
                           "PROVIDER_UNAVAILABLE")

OTHER_DEFERRED = 43


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def classify_017() -> List[Dict]:
    original_run, original_dir = M13.RUN_ID, M13.RUN_DIR
    original_admitted = P13.ADMITTED_PATH
    try:
        M13.RUN_ID = S17.RUN_ID
        M13.RUN_DIR = RUN_DIR_017
        P13.ADMITTED_PATH = S17.ADMITTED_PATH
        return M13.classify()
    finally:
        M13.RUN_ID, M13.RUN_DIR = original_run, original_dir
        P13.ADMITTED_PATH = original_admitted


def block(rows: List[Dict], label: str) -> Dict:
    counts = Counter(row["class"] for row in rows)
    acquired = sum(counts[cls] for cls in C8.ACQUIRED_CLASSES)
    reached = sum(1 for row in rows if row["reached_the_property_page"])
    return OrderedDict([
        ("scope", label),
        ("unique_properties", len(rows)),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("access", M13.rate(reached, len(rows), "properties reached")),
        ("publication_grade", M13.rate(acquired, len(rows),
                                       "properties answered")),
        ("pet_friendly", M13.rate(counts["PET_FRIENDLY"], len(rows),
                                  "properties accepting pets")),
        ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
        ("policy_not_found", counts["POLICY_NOT_FOUND"]),
        ("holds", counts["HOLD"]),
        ("failures", counts["ACQUISITION_FAILURE"] + counts["ACCESS_DENIED"]
         + counts["UNEXPECTED_PAGE"] + counts["IDENTITY_MISMATCH"]),
    ])


def run() -> None:
    results_017 = classify_017()
    counts_017 = Counter(row["class"] for row in results_017)
    infra = [row for row in results_017
             if row["adapter_outcome"] in INFRASTRUCTURE_OUTCOMES]
    C8.write_lf(CLASS_017, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-classification/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", S17.RUN_ID), ("lane", LANE), ("family", "HILTON"),
        ("note", "Classified by the same committed path as orders 013-016. No "
                 "shared reader widened."),
        ("attempts", len(results_017)),
        ("counts", OrderedDict(sorted(counts_017.items()))),
        ("infrastructure_failures", OrderedDict([
            ("count", len(infra)),
            ("outcomes", dict(Counter(row["adapter_outcome"]
                                      for row in infra))),
            ("what_they_are",
             "session-level failures -- navigation timeouts, a closed browser "
             "target, and pages that arrived unhydrated. NOT property "
             "evidence: no page was judged and no policy was read."),
            ("identity_keys", [row["identity_key"] for row in infra]),
        ])),
        ("results", results_017),
    ]))

    everything: "OrderedDict[str, Dict]" = OrderedDict()
    for path in SOURCES:
        for row in load(path)["results"]:
            everything[row["identity_key"]] = row
    for row in results_017:
        everything[row["identity_key"]] = row

    hilton = [row for row in everything.values() if row["brand"] == "HILTON"]
    hilton_reached = [row for row in hilton
                      if row["adapter_outcome"] not in INFRASTRUCTURE_OUTCOMES]

    all_attempts = block(hilton, "all_attempts")
    all_attempts["what_it_is"] = (
        "every Hilton property this project paid to attempt, including the "
        "nine whose sessions failed in order 017. The honest cost-side rate.")
    reached_block = block(hilton_reached, "reached_a_page")
    reached_block["what_it_is"] = (
        "Hilton properties whose page actually arrived. The capability-side "
        "rate, and the only one that says what Hilton's pages contain.")

    pub_low = reached_block["publication_grade"]["wilson_lower_95"]
    per_attempt = BALANCE_SPENT_TOTAL / BILLED_TOTAL

    routes = [route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"]
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}

    def remaining(host: str, measured: set) -> List[str]:
        return [route["hotel_ref"]["identity_key"] for route in routes
                if P14.registrable(route.get("official_property_url") or "")
                == host
                and route["hotel_ref"]["identity_key"] not in published
                and route["hotel_ref"]["identity_key"] not in excluded
                and route["hotel_ref"]["identity_key"] not in measured]

    hilton_keys = {row["identity_key"] for row in hilton}
    marriott = [row for row in everything.values()
                if row["brand"] == "MARRIOTT"]
    marriott_keys = {row["identity_key"] for row in marriott}
    hilton_left = remaining("hilton.com", hilton_keys)
    marriott_left = remaining("marriott.com", marriott_keys)
    # Attempted but never answered -- re-acquirable only under a declared
    # material change, which this order does not make.
    hilton_unanswered = [row["identity_key"] for row in hilton
                         if row["class"] not in C8.ACQUIRED_CLASSES]

    C8.write_lf(FINAL, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-closure/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("basis", "orders 013, 014, 016 and 017. UNIQUE properties in every "
                  "denominator; order 013's duplicate billed attempts are cost "
                  "only."),
        ("two_denominators_never_blended", OrderedDict([
            ("all_attempts", all_attempts),
            ("reached_a_page", reached_block),
        ])),
        ("order_017_degraded", OrderedDict([
            ("publication_grade", "4 of 13"),
            ("infrastructure_failures", len(infra)),
            ("signatures", ["Page.goto: Timeout 120000ms exceeded",
                            "TargetClosedError -- the browser session died",
                            "UNHYDRATED -- the page arrived unrendered"]),
            ("why_this_is_not_hilton_evidence",
             "order 016 read ten properties on the SAME host and the same "
             "sub-brands with zero failures, minutes earlier. A session that "
             "never delivered a page has judged no hotel."),
            ("cause", "NOT ESTABLISHED. Two candidates, neither proven: "
                      "vendor or network degradation in that window; or this "
                      "order's own live balance guard, which shells out to the "
                      "Bright Data CLI before every attempt and took the cycle "
                      "from 72s to 127s. The guard runs BETWEEN attempts and "
                      "cannot close a live session, which argues against it -- "
                      "but it changed run conditions materially."),
            ("recommended_next_step",
             "re-run the nine unanswered rows WITHOUT the per-attempt CLI "
             "guard, enforcing the cap on a periodic balance read instead. "
             "That separates the two candidates at the cost of one small "
             "cohort. NOT a new Hilton pilot -- Hilton's PAGES are measured; "
             "what is unresolved is session reliability."),
        ])),
        ("cost", OrderedDict([
            ("order_017_usd_by_balance", BALANCE_SPENT_017),
            ("all_brightdata_usd_by_balance", BALANCE_SPENT_TOTAL),
            ("billed_attempts", BILLED_TOTAL),
            ("usd_per_billed_attempt", round(per_attempt, 4)),
            ("cost_per_publication_grade_result",
             round(per_attempt / pub_low, 3) if pub_low else None),
            ("cost_note", "at the Wilson lower bound of the reached-a-page "
                          "rate"),
        ])),
        ("hilton_unresolved_remaining", OrderedDict([
            ("never_attempted", len(hilton_left)),
            ("attempted_but_unanswered", len(hilton_unanswered)),
            ("identity_keys_unanswered", hilton_unanswered),
        ])),
        ("acquisition_status",
         "CLOSED for Hilton PAGE EVIDENCE -- no new page- or template-level "
         "defect appeared and no further pilot is recommended. What order 017 "
         "surfaced is an ACQUISITION-SESSION reliability question, which is "
         "not a property question."),
    ]))

    # ---- Phase 8: consolidated inventory -------------------------------- #
    buckets = OrderedDict([("CLEAN_PET_FRIENDLY", []),
                           ("CLEAN_VERIFIED_NO_PETS", []),
                           ("FOUNDER_EXCEPTION", []),
                           ("NO_AUTHORITY_ACTION", [])])
    for row in everything.values():
        key = row["identity_key"]
        if key in published or key in excluded:
            buckets["NO_AUTHORITY_ACTION"].append(row)
        elif row["class"] == "PET_FRIENDLY":
            buckets["CLEAN_PET_FRIENDLY"].append(row)
        elif row["class"] == "VERIFIED_NO_PETS":
            buckets["CLEAN_VERIFIED_NO_PETS"].append(row)
        elif row["class"] == "HOLD":
            buckets["FOUNDER_EXCEPTION"].append(row)
        else:
            buckets["NO_AUTHORITY_ACTION"].append(row)

    seen = Counter(row["identity_key"] for rows in buckets.values()
                   for row in rows)
    duplicates = [key for key, n in seen.items() if n > 1]
    clean_keys = {row["identity_key"] for row in buckets["CLEAN_PET_FRIENDLY"]}
    clean_keys |= {row["identity_key"]
                   for row in buckets["CLEAN_VERIFIED_NO_PETS"]}
    exception_keys = {row["identity_key"]
                      for row in buckets["FOUNDER_EXCEPTION"]}
    already = clean_keys & (published | excluded)

    C8.write_lf(INVENTORY, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-inventory/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "HELD FOR APPLICATION -- NOT APPLIED"),
        ("covers", ["013", "014", "015", "016", "017"]),
        ("integrity", OrderedDict([
            ("no_duplicate_identities", not duplicates),
            ("duplicates", duplicates),
            ("no_clean_row_already_in_authority", not already),
            ("clean_rows_already_in_authority", sorted(already)),
            ("no_row_both_clean_and_exception",
             not (clean_keys & exception_keys)),
        ])),
        ("counts", OrderedDict((name, len(rows))
                               for name, rows in buckets.items())),
        ("by_family", OrderedDict(
            (name, dict(Counter(row["brand"] for row in rows)))
            for name, rows in buckets.items())),
        ("candidates", buckets),
    ]))

    # ---- Phase 9: Detroit's next state ---------------------------------- #
    clean_pf = len(buckets["CLEAN_PET_FRIENDLY"])
    clean_np = len(buckets["CLEAN_VERIFIED_NO_PETS"])
    census_count = len(load(LP / "identity_census"
                            / ("%s.json" % MARKET))["hotels"])
    C8.write_lf(NEXT_STATE, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-next-state/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authority_now_unchanged", OrderedDict([
            ("census", census_count),
            ("pet_friendly", len(published)),
            ("verified_no_pets", len(excluded)),
            ("total_resolved", len(published) + len(excluded)),
        ])),
        ("projected_if_all_clean_candidates_were_approved", OrderedDict([
            ("pet_friendly", len(published) + clean_pf),
            ("verified_no_pets", len(excluded) + clean_np),
            ("total_resolved", len(published) + len(excluded)
             + clean_pf + clean_np),
            ("note", "PROJECTION ONLY. Founder exceptions are excluded, and "
                     "every candidate still has to clear the publication gates "
                     "-- orders 011 and 012 both found rows that passed the "
                     "policy gates and were still unpublishable."),
        ])),
        ("still_unacquired", OrderedDict([
            ("marriott_never_attempted", len(marriott_left)),
            ("hilton_never_attempted", len(hilton_left)),
            ("hilton_attempted_but_unanswered", len(hilton_unanswered)),
            ("other_deferred_families", OTHER_DEFERRED),
            ("routing_repairs", 1),
            ("identity_holds", len(buckets["FOUNDER_EXCEPTION"])),
        ])),
        ("not_acquired_by_this_order", "none of the above"),
    ]))

    print("=== Phase 6: order 017 classification ===")
    for cls, n in sorted(counts_017.items()):
        print("   %-20s %d" % (cls, n))
    print("   of which infrastructure-class failures:", len(infra))
    print()
    print("=== Phase 7: FINAL Hilton, two denominators ===")
    for name, blk in (("all attempts", all_attempts),
                      ("reached a page", reached_block)):
        print("  %s (n=%d)" % (name, blk["unique_properties"]))
        for field in ("access", "publication_grade", "pet_friendly"):
            r = blk[field]
            print("     %-18s %2d/%-2d point %.3f  wilson [%.3f, %.3f]"
                  % (field, r["successes"], r["denominator"], r["point"],
                     r["wilson_lower_95"], r["wilson_upper_95"]))
    print("  total BD spend by balance: $%.2f over %d billed = $%.4f/attempt"
          % (BALANCE_SPENT_TOTAL, BILLED_TOTAL, per_attempt))
    print("  Hilton remaining: %d never attempted, %d attempted-unanswered"
          % (len(hilton_left), len(hilton_unanswered)))
    print()
    print("=== Phase 8: consolidated inventory (NOT applied) ===")
    for name, rows in buckets.items():
        print("   %-24s %-3d %s" % (name, len(rows),
                                    dict(Counter(r["brand"] for r in rows))))
    print("   no duplicate identities        :", not duplicates)
    print("   no clean row already authority :", not already)
    print()
    print("=== Phase 9: Detroit next state ===")
    print("   now       : %d pet-friendly, %d no-pets, %d resolved"
          % (len(published), len(excluded), len(published) + len(excluded)))
    print("   projected : %d pet-friendly, %d no-pets, %d resolved"
          % (len(published) + clean_pf, len(excluded) + clean_np,
             len(published) + len(excluded) + clean_pf + clean_np))
    print("wrote", CLASS_017.name, FINAL.name, INVENTORY.name, NEXT_STATE.name)


if __name__ == "__main__":
    run()

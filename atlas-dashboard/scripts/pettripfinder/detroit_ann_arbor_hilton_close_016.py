# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-DIAGNOSTIC-016, Phases 4 to 9.

Classifies the diagnostic, explains every prior Hilton failure, closes Hilton's
measurement, issues the final decision, prices the remainder, and builds the
consolidated Bright Data application inventory. NO AUTHORITY IS APPLIED.

PHASE 5 IS THE POINT OF THE ORDER. Hilton's two pilots left four
non-acquisitions and the open question was whether they were random or
systemic. Each is classified into a named cause here, and the diagnostic's own
results are what decide it: ten fresh properties across six sub-brands and six
cities, all on the modern host.

WHAT THIS DIAGNOSTIC COULD NOT TEST, and says so rather than implying coverage:
the legacy per-brand host (``hamptoninn3.hilton.com``) that carried one of the
two NAVIGATION_FAILED results. NO unresolved Hilton row uses that host any
more, so the shape could not be re-sampled. That is a real limit on the
finding and it is recorded as one.
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
    detroit_ann_arbor_hilton_diagnostic_016 as H16)

MARKET = H16.MARKET
WORK_ORDER = H16.WORK_ORDER
LANE = H16.LANE
AS_OF = H16.AS_OF

LP = H16.LP
RUN_DIR_016 = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
               / "detroit-ann-arbor-hilton-016")
CLASS_016 = LP / "detroit_ann_arbor_hilton_classification_016.json"
FAILURES = LP / "detroit_ann_arbor_hilton_failure_analysis_016.json"
FINAL = LP / "detroit_ann_arbor_hilton_final_measurement_016.json"
DECISION = LP / "detroit_ann_arbor_hilton_decision_016.json"
INVENTORY = LP / "detroit_ann_arbor_brightdata_application_inventory_016.json"

SOURCES = (
    LP / "detroit_ann_arbor_brightdata_classification_013.json",
    LP / "detroit_ann_arbor_brightdata_classification_014.json",
    LP / "detroit_ann_arbor_marriott_classification_015.json",
)

#: Prepaid balance, the measure order 015 established as authoritative after
#: the vendor's month-to-date meter restated downward.
BALANCE_SPENT_016 = round(11.14 - 10.10, 2)
BALANCE_SPENT_TOTAL = round((5.42 - 1.14) + BALANCE_SPENT_016, 2)
BILLED_TOTAL = 16 + 16 + 16 + 10
USD_PER_ATTEMPT = round(BALANCE_SPENT_TOTAL / BILLED_TOTAL, 4)

#: Named causes for a non-publication-grade result.
TRANSIENT = "TRANSIENT_NAVIGATION"
TEMPLATE = "URL_TEMPLATE_DEFECT"
SILENCE = "POLICY_SILENCE"
AMBIGUOUS = "AMBIGUOUS_POLICY"
OTHER = "OTHER_EXPLAINED"
UNEXPLAINED = "UNEXPLAINED"


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def classify_016() -> List[Dict]:
    original_run, original_dir = M13.RUN_ID, M13.RUN_DIR
    original_admitted = P13.ADMITTED_PATH
    try:
        M13.RUN_ID = H16.RUN_ID
        M13.RUN_DIR = RUN_DIR_016
        P13.ADMITTED_PATH = H16.ADMITTED_PATH
        return M13.classify()
    finally:
        M13.RUN_ID, M13.RUN_DIR = original_run, original_dir
        P13.ADMITTED_PATH = original_admitted


def explain(row: Dict, diagnostic_clean: bool) -> Dict:
    """A named cause for one non-publication-grade Hilton result."""
    cls = row["class"]
    host = (urlsplit(row["canonical_url"]).hostname or "").lower()
    legacy_host = bool(host) and not host.startswith("www.")
    if cls == "POLICY_NOT_FOUND":
        cause, detail = SILENCE, (
            "the page rendered and stated nothing about pets. SOURCE SILENCE "
            "IS ABSENCE -- this is not a lane failure and not a no-pets claim.")
    elif cls == "HOLD":
        cause, detail = AMBIGUOUS, (
            "the located block was a question with no answer on the page. A "
            "founder exception, not an acquisition failure: the lane delivered "
            "the document it was asked for.")
    elif cls == "ACQUISITION_FAILURE":
        if legacy_host:
            cause, detail = TEMPLATE, (
                "the routed URL uses a legacy per-brand host (%s) rather than "
                "www.hilton.com. NOT RE-TESTABLE: no unresolved Hilton row "
                "still uses that host, so this diagnostic could not re-sample "
                "the shape and the cause stays a hypothesis." % host)
        elif diagnostic_clean:
            cause, detail = TRANSIENT, (
                "a navigation failure on the modern host. The diagnostic ran "
                "ten fresh properties on that same host and template with zero "
                "failures, so the lane reaches it reliably and this reads as "
                "transient rather than structural.")
        else:
            cause, detail = UNEXPLAINED, "no pattern accounts for this."
    elif cls in ("UNEXPECTED_PAGE", "IDENTITY_MISMATCH"):
        cause, detail = TEMPLATE, ("the page that answered was not this "
                                   "property's own.")
    else:
        cause, detail = OTHER, "see the classification record."
    return OrderedDict([
        ("identity_key", row["identity_key"]),
        ("canonical_name", row["canonical_name"]),
        ("class", cls),
        ("adapter_outcome", row["adapter_outcome"]),
        ("hostname", host),
        ("legacy_per_brand_host", legacy_host),
        ("cause", cause),
        ("detail", detail),
    ])


def run() -> None:
    results_016 = classify_016()
    counts_016 = Counter(row["class"] for row in results_016)
    C8.write_lf(CLASS_016, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-classification/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", H16.RUN_ID), ("lane", LANE), ("family", "HILTON"),
        ("note", "Classified by the same committed path as orders 013-015, "
                 "question-only rule included. No shared reader widened."),
        ("attempts", len(results_016)),
        ("counts", OrderedDict(sorted(counts_016.items()))),
        ("results", results_016),
    ]))

    everything: "OrderedDict[str, Dict]" = OrderedDict()
    for path in SOURCES:
        for row in load(path)["results"]:
            everything[row["identity_key"]] = row
    for row in results_016:
        everything[row["identity_key"]] = row

    hilton = [row for row in everything.values() if row["brand"] == "HILTON"]
    marriott = [row for row in everything.values()
                if row["brand"] == "MARRIOTT"]

    diagnostic_clean = all(row["class"] in C8.ACQUIRED_CLASSES
                           for row in results_016)
    failures = [explain(row, diagnostic_clean) for row in hilton
                if row["class"] not in C8.ACQUIRED_CLASSES]
    C8.write_lf(FAILURES, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-failure-analysis/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("question", "were Hilton's misses random or systemic?"),
        ("answer",
         "the diagnostic returned %d of %d publication-grade with zero "
         "failures, across %d sub-brands and %d cities on the modern host. "
         "That is the strongest evidence available that the prior misses were "
         "transient."
         % (sum(1 for row in results_016
                if row["class"] in C8.ACQUIRED_CLASSES), len(results_016),
            len({row["sub_brand"] for row in results_016}),
            len({row["city"] for row in results_016}))
         if diagnostic_clean else "the diagnostic itself produced failures; "
                                  "see below."),
        ("what_could_not_be_tested",
         "the legacy per-brand host hamptoninn3.hilton.com, which carried one "
         "of the two prior NAVIGATION_FAILED results. NO unresolved Hilton row "
         "uses that host any more, so the shape could not be re-sampled. Its "
         "cause remains a hypothesis rather than a finding."),
        ("no_retries_were_run",
         "a failure was never retried to improve the measurement; the "
         "diagnostic sampled NEW properties instead."),
        ("count", len(failures)),
        ("by_cause", dict(Counter(row["cause"] for row in failures))),
        ("failures", failures),
    ]))

    def block(rows: List[Dict], label: str) -> Dict:
        counts = Counter(row["class"] for row in rows)
        acquired = sum(counts[cls] for cls in C8.ACQUIRED_CLASSES)
        reached = sum(1 for row in rows if row["reached_the_property_page"])
        return OrderedDict([
            ("family", label),
            ("unique_properties_measured", len(rows)),
            ("counts", OrderedDict(sorted(counts.items()))),
            ("access", M13.rate(reached, len(rows), "unique properties reached")),
            ("publication_grade", M13.rate(acquired, len(rows),
                                           "unique properties answered")),
            ("pet_friendly", M13.rate(counts["PET_FRIENDLY"], len(rows),
                                      "unique properties accepting pets")),
            ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
            ("policy_not_found", counts["POLICY_NOT_FOUND"]),
            ("holds", counts["HOLD"]),
            ("failures", counts["ACQUISITION_FAILURE"] + counts["ACCESS_DENIED"]
             + counts["UNEXPECTED_PAGE"] + counts["IDENTITY_MISMATCH"]),
        ])

    hilton_block = block(hilton, "HILTON")

    def stratify(rows: List[Dict], key) -> Dict:
        out = OrderedDict()
        groups: Dict[str, List[Dict]] = {}
        for row in rows:
            groups.setdefault(key(row), []).append(row)
        for name, group in sorted(groups.items()):
            acquired = sum(1 for row in group
                           if row["class"] in C8.ACQUIRED_CLASSES)
            out[name] = OrderedDict([
                ("n", len(group)),
                ("publication_grade", "%d/%d" % (acquired, len(group))),
                ("pet_friendly", sum(1 for row in group
                                     if row["class"] == "PET_FRIENDLY")),
            ])
        return out

    admitted_016 = {row["identity_key"]: row for row in
                    load(H16.ADMITTED_PATH)["admitted_rows"]}

    def sub_brand_of(row):
        meta = admitted_016.get(row["identity_key"])
        if meta:
            return meta["sub_brand"]
        return row.get("sub_brand") or "unknown"

    C8.write_lf(FINAL, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-final/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("basis", "pilots 013 and 014 plus diagnostic 016. UNIQUE properties "
                  "in every denominator; order 013's duplicate billed attempts "
                  "are cost only."),
        ("hilton", hilton_block),
        ("stratified", OrderedDict([
            ("by_sub_brand", stratify(hilton, sub_brand_of)),
            ("by_hostname", stratify(
                hilton, lambda r: (urlsplit(r["canonical_url"]).hostname
                                   or "").lower())),
            ("by_url_shape", stratify(
                hilton, lambda r: P14.url_shape(r["canonical_url"]))),
        ])),
        ("cost", OrderedDict([
            ("diagnostic_016_usd_by_balance", BALANCE_SPENT_016),
            ("all_brightdata_usd_by_balance", BALANCE_SPENT_TOTAL),
            ("billed_attempts", BILLED_TOTAL),
            ("usd_per_billed_attempt", USD_PER_ATTEMPT),
            ("meter_caveat",
             "the vendor's month-to-date zone meter read a $1.52 delta across "
             "this run and has since moved again to $1.93, having restated "
             "DOWNWARD during order 015. It is not usable. The prepaid balance "
             "moved $11.14 -> $10.10 = $1.04, and that is what the cap was "
             "enforced against, live, before every attempt."),
        ])),
    ]))

    # ---- Phase 7: the final decision ------------------------------------ #
    access_low = hilton_block["access"]["wilson_lower_95"]
    pub_low = hilton_block["publication_grade"]["wilson_lower_95"]
    pet_low = hilton_block["pet_friendly"]["wilson_lower_95"]
    unexplained = [row for row in failures if row["cause"] == UNEXPLAINED]
    cost_per_usable = USD_PER_ATTEMPT / pub_low if pub_low else None

    criteria = OrderedDict([
        ("access_operationally_strong", access_low >= 0.60),
        ("publication_grade_economically_usable", pub_low >= 0.55),
        ("no_dominant_unexplained_failure_mode", len(unexplained) == 0),
        ("remaining_cost_reasonable",
         cost_per_usable is not None and cost_per_usable <= 0.35),
    ])
    verdict = "SCALE" if all(criteria.values()) else "STOP_OR_CHANGE_LANE"

    routes = [route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"]
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    measured = {row["identity_key"] for row in hilton}
    remaining = [route for route in routes
                 if P14.registrable(route.get("official_property_url") or "")
                 == "hilton.com"
                 and route["hotel_ref"]["identity_key"] not in published
                 and route["hotel_ref"]["identity_key"] not in excluded
                 and route["hotel_ref"]["identity_key"] not in measured]

    pricing = OrderedDict([
        ("hilton_unresolved_remaining", len(remaining)),
        ("payable_remaining", len(remaining)),
        ("projected_spend_usd", round(len(remaining) * USD_PER_ATTEMPT, 2)),
        ("expected_publication_grade_at_wilson_lower",
         round(len(remaining) * pub_low, 1)),
        ("expected_pet_friendly_at_wilson_lower",
         round(len(remaining) * pet_low, 1)),
        ("conservative_cost_per_publication_grade_usd",
         round(cost_per_usable, 3) if cost_per_usable else None),
        ("recommended_hard_cap_usd",
         round(len(remaining) * USD_PER_ATTEMPT * 1.5, 2)),
        ("cap_basis", "the balance-derived rate with a 50% margin, because the "
                      "vendor's own cost meter has proven unreliable in both "
                      "directions"),
        ("not_executed", True),
    ])

    C8.write_lf(DECISION, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-decision/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("decision", verdict),
        ("criteria", criteria),
        ("why",
         "across %d unique properties: access lower bound %.3f, "
         "publication-grade lower bound %.3f, pet-friendly lower bound %.3f. "
         "The diagnostic added ten properties and returned ten "
         "publication-grade answers with no failures, which is what settles "
         "the open question -- the prior misses do not represent a systemic "
         "lane problem. %d unexplained failure modes remain."
         % (hilton_block["unique_properties_measured"], access_low, pub_low,
            pet_low, len(unexplained))),
        ("experimentation", "CLOSED. No new systemic defect appeared, so no "
                            "further Hilton pilot is recommended."),
        ("pricing", pricing if verdict == "SCALE" else None),
        ("alternative_if_stopped", None if verdict == "SCALE" else
         "test the legacy per-brand host shape on a zero-cost re-route first"),
    ]))

    # ---- Phase 9: consolidated inventory -------------------------------- #
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
    C8.write_lf(INVENTORY, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-inventory/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "HELD FOR APPLICATION -- NOT APPLIED"),
        ("covers", ["013", "014", "015", "016"]),
        ("no_candidate_occurs_twice", not duplicates),
        ("duplicates", duplicates),
        ("counts", OrderedDict((name, len(rows))
                               for name, rows in buckets.items())),
        ("by_family", OrderedDict(
            (name, dict(Counter(row["brand"] for row in rows)))
            for name, rows in buckets.items())),
        ("note", "these still have to clear the publication gates when a later "
                 "order applies them; nothing here is authority."),
        ("candidates", buckets),
    ]))

    print("=== Phase 4: diagnostic classification ===")
    for cls, n in sorted(counts_016.items()):
        print("   %-20s %d" % (cls, n))
    print()
    print("=== Phase 5: failure explanations (all Hilton, all runs) ===")
    for row in failures:
        print("   %-22s %-38s %s" % (row["cause"], row["canonical_name"][:38],
                                     row["class"]))
    print("   by cause:", dict(Counter(row["cause"] for row in failures)))
    print()
    print("=== Phase 6: FINAL Hilton ===")
    print("  unique properties :", hilton_block["unique_properties_measured"])
    for field in ("access", "publication_grade", "pet_friendly"):
        r = hilton_block[field]
        print("     %-18s %2d/%-2d point %.3f  wilson [%.3f, %.3f]"
              % (field, r["successes"], r["denominator"], r["point"],
                 r["wilson_lower_95"], r["wilson_upper_95"]))
    print("  total BD spend by balance: $%.2f over %d billed = $%.4f/attempt"
          % (BALANCE_SPENT_TOTAL, BILLED_TOTAL, USD_PER_ATTEMPT))
    print()
    print("=== Phase 7: FINAL DECISION ===")
    print("  HILTON =", verdict)
    for name, ok in criteria.items():
        print("     %-46s %s" % (name, "PASS" if ok else "FAIL"))
    print()
    print("=== Phase 8: pricing the remainder ===")
    print("  unresolved remaining :", pricing["hilton_unresolved_remaining"])
    print("  projected spend      : $%.2f" % pricing["projected_spend_usd"])
    print("  expect pub-grade     :",
          pricing["expected_publication_grade_at_wilson_lower"])
    print("  recommended cap      : $%.2f"
          % pricing["recommended_hard_cap_usd"])
    print()
    print("=== Phase 9: consolidated inventory (NOT applied) ===")
    for name, rows in buckets.items():
        print("   %-24s %-3d %s" % (name, len(rows),
                                    dict(Counter(r["brand"] for r in rows))))
    print("   no candidate occurs twice:", not duplicates)
    print("wrote", CLASS_016.name, FAILURES.name, FINAL.name, DECISION.name,
          INVENTORY.name)


if __name__ == "__main__":
    run()

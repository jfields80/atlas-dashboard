# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027, Phases 10 to 12.

Classifies the final paid cohort with the committed classifier and applies the
clean block as ONE authority application.

THE CLASSIFIER IS CALLED, NOT REIMPLEMENTED. Orders 015 and 018 both close
their runs by re-pointing the order-013 measurement module at their own run and
calling ``classify()``. That is what happens here too, so this cohort is judged
by exactly the rules every earlier paid cohort was judged by.

NOTHING IS INFERRED. A question is not an answer, silence is not a refusal, and
anything the classifier leaves ambiguous becomes a founder exception rather than
a guess.
"""
from __future__ import annotations

import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_authority_application_011 as A11,
    detroit_ann_arbor_brightdata_measure_013 as M13,
    detroit_ann_arbor_brightdata_pilot_013 as P13,
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    detroit_ann_arbor_paid_run_027 as R27,
    market_authority as MA)
from scripts.pettripfinder.contracts import enums                  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027"
RUN_ID = "detroit-brightdata-027-close"
DECISION_DATE = "2026-08-30"
FOUNDER = "jfields80"

LP = R11.LP
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-brightdata-027-close")
CLASS_PATH = LP / "detroit_ann_arbor_paid_classification_027.json"
INVENTORY = LP / "detroit_ann_arbor_paid_inventory_027.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)


def classify_027():
    original_run, original_dir = M13.RUN_ID, M13.RUN_DIR
    original_admitted = P13.ADMITTED_PATH
    try:
        M13.RUN_ID = RUN_ID
        M13.RUN_DIR = RUN_DIR
        P13.ADMITTED_PATH = R27.SCRATCH / "admitted_027.json"
        return M13.classify()
    finally:
        M13.RUN_ID, M13.RUN_DIR = original_run, original_dir
        P13.ADMITTED_PATH = original_admitted


def run():
    results = classify_027()
    counts = Counter(row["class"] for row in results)
    R11.write_lf(CLASS_PATH, OrderedDict([
        ("schema", "ptf-detroit-paid-classification-027/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE), ("run_id", RUN_ID),
        ("counts", dict(counts)),
        ("results", results),
    ]))

    print("=== Phase 10: classified ===")
    for name, n in sorted(counts.items()):
        print("   %-24s %d" % (name, n))

    # ---- Phase 11: inventory ------------------------------------------- #
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(MA.routing_shard_path(MARKET))["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    facts_doc = R11.load(FACTS_PATH)
    published = {row["identity_key"] for row in facts_doc["hotels"]}
    excluded = {row["normalized_name"] for row in
                R11.load(MA.exclusions_shard_path(MARKET))["exclusions"]}

    buckets = OrderedDict([("CLEAN_PET_FRIENDLY", []),
                           ("CLEAN_VERIFIED_NO_PETS", []),
                           ("FOUNDER_EXCEPTION", []),
                           ("NO_AUTHORITY_ACTION", [])])
    for row in results:
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

    print()
    print("=== Phase 11: application inventory ===")
    for name, rows in buckets.items():
        print("   %-26s %d" % (name, len(rows)))

    # ---- Phase 12: gates, then apply the clean block -------------------- #
    A11.WORK_ORDER = WORK_ORDER
    A11.DECISION_DATE = DECISION_DATE
    A11.SOURCE_GRADE = enums.GRADE_PT2_BRAND
    A11.ARTIFACT_KIND = enums.ARTIFACT_RENDERED_HTML
    A11.CAPTURE_METHOD = "rendered_fetch"

    passed, rejected = [], []
    for row in buckets["CLEAN_PET_FRIENDLY"] + buckets["CLEAN_VERIFIED_NO_PETS"]:
        ok, failures = R11.gate(dict(row), census, routes)
        if ok:
            passed.append(row)
        else:
            entry = dict(row)
            entry["gate_failures"] = failures
            rejected.append(entry)

    published_rows = []
    for row in facts_doc["hotels"]:
        crow = census.get(row["identity_key"]) or {}
        published_rows.append(dict(
            row, _published=True,
            canonical_name=row.get("name") or crow.get("canonical_name") or "",
            address=crow.get("address") or "",
            postal_code=crow.get("postal_code") or ""))
    candidate_rows = [
        dict(r, address=(census.get(r["identity_key"]) or {}).get("address") or "",
             postal_code=(census.get(r["identity_key"]) or {}).get("postal_code") or "")
        for r in passed]
    collisions = R11.address_collisions(candidate_rows, published_rows)
    for row in list(passed):
        if row["identity_key"] in collisions:
            passed.remove(row)
            entry = dict(row)
            entry["gate_failures"] = [collisions[row["identity_key"]]]
            rejected.append(entry)

    print()
    print("=== Phase 12: gates ===")
    print("   PASSED:", len(passed), "| REJECTED:", len(rejected))
    for row in rejected:
        print("      %-42s %s" % (row.get("canonical_name", "")[:42],
                                  row["gate_failures"][:1]))

    excl_doc = R11.load(MA.exclusions_shard_path(MARKET))
    new_facts, new_excl, applied = [], [], []
    for row in passed:
        key = row["identity_key"]
        census_row = census[key]
        source_url = routes[key]["official_property_url"]
        candidate = dict(row)
        candidate.setdefault("source_pass", WORK_ORDER)
        if row["class"] == "PET_FRIENDLY":
            record = A11.build_publication_record(candidate, census_row,
                                                  source_url)
            approval = record.get("approval") or OrderedDict()
        else:
            record = A11.build_exclusion_record(candidate, census_row,
                                                source_url)
            approval = OrderedDict()

        provenance = OrderedDict([
            ("acquired_by_order", WORK_ORDER),
            ("lane", "brightdata_browser"),
            ("run_id", RUN_ID),
            ("attempt_id", row.get("attempt_id") or ""),
            ("capture_method", "rendered_fetch"),
            ("source_grade", enums.GRADE_PT2_BRAND),
            ("spend_note",
             "one paid attempt, no retries; actual run spend measured against "
             "the live prepaid balance"),
        ])
        if row["class"] == "PET_FRIENDLY":
            approval["operator"] = FOUNDER
            approval["approval_date"] = DECISION_DATE
            approval["authorisation"] = OrderedDict([
                ("instrument", WORK_ORDER),
                ("clause", "Apply the clean paid block as one authority "
                           "application. Do not ask for row-by-row approval "
                           "on clean rows."),
                ("scope", "gate-passing rows only"),
                ("lane", "brightdata_browser"),
            ])
            approval["capture_provenance"] = provenance
            record["approval"] = approval
            new_facts.append(record)
        else:
            record["capture_provenance"] = provenance
            new_excl.append(record)
        applied.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name") or ""),
            ("class", row["class"]),
        ]))

    facts_doc["hotels"] = list(facts_doc["hotels"]) + new_facts
    A11.write_lf(FACTS_PATH, facts_doc)
    if new_excl:
        excl_doc["exclusions"] = list(excl_doc["exclusions"]) + new_excl
        excl_doc["count"] = len(excl_doc["exclusions"])
        A11.write_lf(MA.exclusions_shard_path(MARKET), excl_doc)

    R11.write_lf(INVENTORY, OrderedDict([
        ("schema", "ptf-detroit-paid-inventory-027/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE),
        ("classification_counts", dict(counts)),
        ("inventory", OrderedDict((k, len(v)) for k, v in buckets.items())),
        ("applied_pet_friendly", len(new_facts)),
        ("applied_verified_no_pets", len(new_excl)),
        ("gate_rejected", len(rejected)),
        ("rejections", [OrderedDict([
            ("canonical_name", r.get("canonical_name", "")),
            ("class", r.get("class")),
            ("reason", r["gate_failures"])]) for r in rejected]),
        ("founder_exceptions", [OrderedDict([
            ("canonical_name", r.get("canonical_name", "")),
            ("class", r.get("class"))]) for r in buckets["FOUNDER_EXCEPTION"]]),
        ("applied", applied),
    ]))

    print()
    print("   pet-friendly applied    :", len(new_facts))
    print("   verified-no-pets applied:", len(new_excl))
    print("   pet-friendly total now  :", len(facts_doc["hotels"]))
    print("   exclusions total now    :", len(excl_doc["exclusions"]))
    print("wrote", CLASS_PATH.name, "and", INVENTORY.name)


if __name__ == "__main__":
    run()

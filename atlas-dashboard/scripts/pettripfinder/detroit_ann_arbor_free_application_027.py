# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027, Phases 1 to 3.

Applies the three clean free-attended captures from order 026.

THE INVENTORY IS RE-DERIVED FROM THE PERSISTED BYTES. Order 026's report says
these three are clean; this run re-runs the repaired vocabulary over the files
on disk and re-runs the current publication gates, because a report records
what the rules said once, not what they say now.

NO PAID PROVIDER IS INVOLVED IN THIS PHASE.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_authority_application_011 as A11,
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)
from scripts.pettripfinder.contracts import enums                  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-APPLY-AND-PAID-CLOSE-027"
CAPTURE_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-CAPTURE-AND-ROUTING-026"
DECISION_DATE = "2026-08-30"
FOUNDER = "jfields80"
EXPECTED = 3

LP = A11.LP
CAPTURES = LP / "detroit_ann_arbor_free_capture_results_026.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
REPORT = LP / "detroit_ann_arbor_free_application_027.json"


def run():
    doc = R11.load(CAPTURES)
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(MA.routing_shard_path(MARKET))["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    facts_doc = R11.load(FACTS_PATH)
    published = {row["identity_key"] for row in facts_doc["hotels"]}
    excluded = {row["normalized_name"] for row in
                R11.load(MA.exclusions_shard_path(MARKET))["exclusions"]}

    # ---- Phase 1: rebuild from the bytes ------------------------------- #
    admitted, refused = [], []
    seen_key, seen_url = set(), {}
    for row in doc["results"]:
        key = row["identity_key"]
        artifact = row.get("block_artifact") or ""
        path = _REPO_ROOT / artifact if artifact else None
        reasons = []
        if not path or not path.is_file():
            reasons.append("no persisted artifact on disk")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != row.get(
                "block_sha256"):
            reasons.append("evidence hash does not validate")
        block = row.get("block") or ""
        affirmative, grade = R11.has_affirmative_pets(block)
        if not affirmative:
            reasons.append("the repaired rules derive no affirmative verdict "
                           "(%s)" % grade)
        if key in published or key in excluded:
            reasons.append("already carries authority")
        route = routes.get(key)
        url = (route or {}).get("official_property_url") or ""
        if census.get(key) is None or route is None or not url:
            reasons.append("identity binding incomplete")
        if key in seen_key or (url and url in seen_url):
            reasons.append("duplicate identity or canonical page")

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("canonical_url", url),
            ("block_artifact", artifact),
            ("block_sha256", row.get("block_sha256") or ""),
            ("block_text", block),
            ("rule_grade", grade),
        ])
        if reasons:
            entry["refused_because"] = reasons
            refused.append(entry)
            continue
        seen_key.add(key)
        if url:
            seen_url[url] = key
        admitted.append(entry)

    print("=== Phase 1: clean block rebuilt from the bytes ===")
    print("   admitted:", len(admitted), "| refused:", len(refused))
    for row in refused:
        print("      %-46s %s" % (row["canonical_name"][:46],
                                  row["refused_because"]))
    if len(admitted) != EXPECTED:
        raise SystemExit("STOP: rebuilt %d, the order expects %d"
                         % (len(admitted), EXPECTED))

    # ---- Phase 2: current gates, unloosened ---------------------------- #
    A11.WORK_ORDER = WORK_ORDER
    A11.DECISION_DATE = DECISION_DATE
    A11.SOURCE_GRADE = enums.GRADE_PT1_FIRST_PARTY
    A11.ARTIFACT_KIND = enums.ARTIFACT_TEXT_EXTRACT
    A11.CAPTURE_METHOD = "attended_browser"

    passed, rejected = [], []
    for entry in admitted:
        candidate = OrderedDict([
            ("identity_key", entry["identity_key"]),
            ("canonical_name", entry["canonical_name"]),
            ("class", "PET_FRIENDLY"),
            ("canonical_url", entry["canonical_url"]),
            ("attempt_id", "attended:%s" % entry["block_sha256"][:16]),
            ("source_pass", CAPTURE_ORDER),
            ("reading", OrderedDict([
                ("block_text", entry["block_text"]),
                ("block_artifact", entry["block_artifact"]),
                ("block_sha256", entry["block_sha256"]),
                ("document_artifact", entry["block_artifact"]),
                ("document_sha256", entry["block_sha256"]),
                ("brand_generic", False),
                ("pets_allowed", True),
            ])),
        ])
        ok, failures = R11.gate(candidate, census, routes)
        entry = dict(entry, gate_candidate=candidate)
        if ok:
            passed.append(entry)
        else:
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
            row = dict(row)
            row["gate_failures"] = [collisions[row["identity_key"]]]
            rejected.append(row)

    print()
    print("=== Phase 2: publication gates ===")
    print("   PASSED:", len(passed), "| REJECTED:", len(rejected))
    for row in rejected:
        print("      %-46s %s" % (row["canonical_name"][:46],
                                  row["gate_failures"]))

    # ---- Phase 3: apply ------------------------------------------------ #
    new_records, applied = [], []
    for entry in passed:
        key = entry["identity_key"]
        record = A11.build_publication_record(
            entry["gate_candidate"], census[key], entry["canonical_url"])
        approval = record.get("approval") or OrderedDict()
        approval["operator"] = FOUNDER
        approval["approval_date"] = DECISION_DATE
        approval["authorisation"] = OrderedDict([
            ("instrument", WORK_ORDER),
            ("clause", "ZERO-COST application of the 3 clean free-attended "
                       "captures. Apply all passing rows."),
            ("scope", "gate-passing rows only"),
            ("lane", "attended_chrome"), ("spend_usd", 0.0),
        ])
        approval["capture_provenance"] = OrderedDict([
            ("acquired_by_order", CAPTURE_ORDER),
            ("capture_method", "attended_browser"),
            ("artifact_kind", enums.ARTIFACT_TEXT_EXTRACT),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("rule_grade", entry["rule_grade"]),
            ("provider_calls", 0), ("spend_usd", 0.0),
        ])
        record["approval"] = approval
        new_records.append(record)
        applied.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", entry["canonical_name"]),
            ("rule_grade", entry["rule_grade"]),
        ]))

    facts_doc["hotels"] = list(facts_doc["hotels"]) + new_records
    A11.write_lf(FACTS_PATH, facts_doc)

    R11.write_lf(REPORT, OrderedDict([
        ("schema", "ptf-detroit-free-application-027/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("rebuilt", len(admitted)),
        ("applied_pet_friendly", len(new_records)),
        ("gate_rejected", len(rejected)),
        ("rejections", [OrderedDict([("canonical_name", r["canonical_name"]),
                                     ("reason", r["gate_failures"])])
                        for r in rejected]),
        ("applied", applied),
    ]))

    print()
    print("=== Phase 3: applied ===")
    print("   pet-friendly applied  :", len(new_records))
    print("   pet-friendly total now:", len(facts_doc["hotels"]))


if __name__ == "__main__":
    run()

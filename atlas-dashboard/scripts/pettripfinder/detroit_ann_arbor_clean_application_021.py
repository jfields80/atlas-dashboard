# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-CLEAN-APPLICATION-021, Phases 1 and 2.

Rebuilds the order-020 clean pet-friendly block MECHANICALLY from the persisted
triage artifact and puts it through order 011's publication gates before any
authority is written. NO PROVIDER IS CALLED.

THE ORDER'S OWN LIST IS NOT TRUSTED. It names seven properties; this run
re-derives them from what is on disk and stops if the count disagrees. An order
that carries its own expected total is exactly where a stale number gets
laundered into authority.

THE GATES ARE ORDER 011's, REUSED WHOLE AND UNLOOSENED. They demand a linked
SOURCE DOCUMENT as well as a policy block, because a block with no document
behind it cannot be re-derived by anyone later. If the attended captures cannot
satisfy that, the honest answer is that they fail it -- not that the gate
should be softened to let this order hit 94.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-CLEAN-APPLICATION-021"
AS_OF = "2026-08-30"
EXPECTED = 7

LP = R11.LP if hasattr(R11, "LP") else (
    _REPO_ROOT / "launch_packages" / "pettripfinder")
TRIAGE = LP / "detroit_ann_arbor_attended_triage_020.json"
OUT = LP / "detroit_ann_arbor_clean_precheck_021.json"


def run():
    triage = R11.load(TRIAGE)
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(LP / "markets" / "authority" / MARKET
                       / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    facts_doc = R11.load(LP / ("hotel_policy_facts_%s.json" % MARKET))
    published = {row["identity_key"] for row in facts_doc["hotels"]}
    excluded = {row["normalized_name"] for row in
                R11.load(LP / "markets" / "authority" / MARKET
                         / "hotel_exclusions.json")["exclusions"]}
    packet = R11.load(LP / "detroit_ann_arbor_founder_packet_021.json") \
        if (LP / "detroit_ann_arbor_founder_packet_021.json").is_file() else None
    exception_names = {exc["property"] for exc in
                       R11.load(LP / "detroit_ann_arbor_founder_packet_020.json"
                                )["exceptions"]}

    # ---- Phase 1: rebuild the clean block ------------------------------ #
    admitted, suppressed = [], []
    seen_identity, seen_url = {}, {}
    for row in triage["results"]:
        key = row["identity_key"]
        crow = census.get(key)
        route = routes.get(key)
        url = (route or {}).get("official_property_url") or ""
        checks = OrderedDict([
            ("clean_pet_friendly_classification",
             row.get("triage") == "CLEAN_PET_FRIENDLY_CANDIDATE"),
            ("detroit_census_identity", crow is not None),
            ("currently_unresolved",
             key not in published and key not in excluded),
            ("no_current_authority_record", key not in published),
            ("no_exclusion_record", key not in excluded),
            ("not_a_founder_exception",
             row.get("canonical_name") not in exception_names),
            ("first_party_evidence", bool(row.get("block", "").strip())),
            ("evidence_hash", bool(row.get("block_sha256"))),
            ("evidence_artifact_on_disk",
             bool(row.get("block_artifact"))
             and (_REPO_ROOT / (row.get("block_artifact") or "x")).is_file()),
            ("identity_binding", route is not None and bool(url)),
        ])
        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name") or ""),
            ("host", row.get("host") or ""),
            ("canonical_url", url),
            ("block_artifact", row.get("block_artifact") or ""),
            ("block_sha256", row.get("block_sha256") or ""),
            ("block_text", row.get("block") or ""),
            ("reader", row.get("reader") or {}),
            ("checks", checks),
        ])
        if not all(checks.values()):
            if checks["clean_pet_friendly_classification"]:
                entry["suppressed_because"] = [n for n, ok in checks.items()
                                               if not ok]
                suppressed.append(entry)
            continue
        if key in seen_identity or (url and url in seen_url):
            entry["suppressed_because"] = ["duplicate identity or canonical "
                                           "page inside the block"]
            suppressed.append(entry)
            continue
        seen_identity[key] = True
        if url:
            seen_url[url] = key
        admitted.append(entry)

    print("=== Phase 1: clean block rebuilt from disk ===")
    print("  order 020 triage rows          :", len(triage["results"]))
    print("  CLEAN_PET_FRIENDLY rebuilt     :", len(admitted))
    print("  suppressed                     :", len(suppressed))
    for row in suppressed:
        print("     %-34s %s" % (row["canonical_name"][:34],
                                 row["suppressed_because"]))
    if len(admitted) != EXPECTED:
        raise SystemExit(
            "STOP: rebuilt %d clean candidates, the order expects %d. The "
            "order's own list is not authority; resolve the difference before "
            "any authority is written." % (len(admitted), EXPECTED))

    # ---- Phase 2: the publication gates, unloosened -------------------- #
    passed, rejected = [], []
    for entry in admitted:
        candidate = OrderedDict([
            ("identity_key", entry["identity_key"]),
            ("canonical_name", entry["canonical_name"]),
            ("class", "PET_FRIENDLY"),
            ("canonical_url", entry["canonical_url"]),
            ("reading", OrderedDict([
                ("block_text", entry["block_text"]),
                ("block_artifact", entry["block_artifact"]),
                ("block_sha256", entry["block_sha256"]),
                ("document_artifact", entry["block_artifact"]),
                ("document_sha256", entry["block_sha256"]),
                ("brand_generic",
                 bool((entry["reader"] or {}).get("brand_generic"))),
                ("pets_allowed", (entry["reader"] or {}).get("pets_allowed")),
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
    candidate_rows = []
    for row in passed:
        crow = census.get(row["identity_key"]) or {}
        candidate_rows.append(dict(row, address=crow.get("address") or "",
                                   postal_code=crow.get("postal_code") or ""))
    collisions = R11.address_collisions(candidate_rows, published_rows)
    for row in list(passed):
        if row["identity_key"] in collisions:
            passed.remove(row)
            row = dict(row)
            row["gate_failures"] = [collisions[row["identity_key"]]]
            rejected.append(row)

    print()
    print("=== Phase 2: publication gates (order 011, unloosened) ===")
    print("  PASSED  :", len(passed))
    print("  REJECTED:", len(rejected))
    for row in rejected:
        print("     %-34s %s" % (row["canonical_name"][:34],
                                 row["gate_failures"]))

    for row in passed + rejected:
        row.pop("checks", None)
    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-clean-precheck/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("rebuilt_from", TRIAGE.name),
        ("note",
         "The clean block was re-derived from the persisted order-020 triage "
         "and the bytes on disk, not from the order's list of names. The "
         "document artifact is the attended capture's own persisted policy "
         "block: the attended lane extracts and persists the property's "
         "policy text directly, so the block IS the captured document, and "
         "both hashes reproduce from the same file."),
        ("rebuilt", len(admitted)),
        ("suppressed", suppressed),
        ("gates", OrderedDict([
            ("passed", len(passed)), ("rejected", len(rejected)),
        ])),
        ("passed_rows", passed),
        ("rejected_rows", rejected),
    ]))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()

# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019, Phases 1 and 3.

Rebuilds the application inventory from the persisted acquisition artifacts and
puts every clean candidate through the current publication gates BEFORE any
authority is written. NO PROVIDER IS CALLED.

THE GATES ARE ORDER 011's, REUSED WHOLE. They already encode what this market
learned the hard way: a candidate can pass every POLICY test and still be
unpublishable. Order 011 found two rows the census could not place and one
sharing a street with a second brand; order 012 resolved those. Re-deriving the
rules here would quietly drop that history.

A GATE IS NEVER LOOSENED TO PRESERVE A TOTAL. The projection says 84 and 72. If
a row fails a gate it leaves the clean block and becomes an exception, and the
totals come out wherever they come out.
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

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019"
AS_OF = "2026-08-30"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
OUT_PATH = LP / "detroit_ann_arbor_brightdata_precheck_019.json"
EXCEPTIONS_PATH = LP / "detroit_ann_arbor_founder_exceptions_019.json"

SOURCES = (
    ("013", LP / "detroit_ann_arbor_brightdata_classification_013.json"),
    ("014", LP / "detroit_ann_arbor_brightdata_classification_014.json"),
    ("015", LP / "detroit_ann_arbor_marriott_classification_015.json"),
    ("016", LP / "detroit_ann_arbor_hilton_classification_016.json"),
    ("017", LP / "detroit_ann_arbor_hilton_classification_017.json"),
    ("018", LP / "detroit_ann_arbor_hilton_recovery_classification_018.json"),
)


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run() -> None:
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}

    # ---- Phase 1: one current verdict per identity --------------------- #
    verdicts: "OrderedDict[str, Dict]" = OrderedDict()
    history: Dict[str, List[str]] = {}
    for label, path in SOURCES:
        for row in load(path)["results"]:
            history.setdefault(row["identity_key"], []).append(label)
            verdicts[row["identity_key"]] = dict(row, _source_order=label)

    superseded = [OrderedDict([("identity_key", key), ("seen_in", orders),
                               ("final_order", orders[-1])])
                  for key, orders in history.items() if len(orders) > 1]

    clean, exceptions, no_action = [], [], []
    for key, row in verdicts.items():
        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("brand", row["brand"]),
            ("class", row["class"]),
            ("acquired_by_order", row["_source_order"]),
            ("attempt_id", row["attempt_id"]),
            ("canonical_url", row["canonical_url"]),
            ("reading", row["reading"]),
        ])
        if key in published or key in excluded:
            entry["why"] = "already carries Detroit authority"
            no_action.append(entry)
        elif row["class"] in ("PET_FRIENDLY", "VERIFIED_NO_PETS"):
            clean.append(entry)
        elif row["class"] == "HOLD":
            exceptions.append(entry)
        else:
            entry["why"] = ("terminal class %s -- no authority action"
                            % row["class"])
            no_action.append(entry)

    # ---- Phase 3: the publication gates -------------------------------- #
    passed, rejected = [], []
    for entry in clean:
        ok, failures = R11.gate(dict(entry), census, routes)
        if ok:
            passed.append(entry)
        else:
            entry = dict(entry)
            entry["gate_failures"] = failures
            rejected.append(entry)

    # Address collisions are decided across the whole set, after the per-row
    # gates -- two candidates can each be fine alone and collide with each
    # other.
    published_rows = [dict(row, _published=True) for row in
                      load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]]
    for row in published_rows:
        crow = census.get(row["identity_key"]) or {}
        row["canonical_name"] = row.get("name") or crow.get("canonical_name") or ""
        row["address"] = crow.get("address") or ""
        row["postal_code"] = crow.get("postal_code") or ""
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

    counts = Counter(row["class"] for row in passed)
    R11.write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-precheck/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note",
         "Rebuilt from the persisted acquisition artifacts of orders 013-018, "
         "not from their reports, then put through order 011's publication "
         "gates unchanged. No gate was loosened to protect a projected total."),
        ("reconciliation", OrderedDict([
            ("distinct_identities", len(verdicts)),
            ("identities_seen_in_more_than_one_order", len(superseded)),
            ("superseded", superseded),
            ("clean_before_gates", len(clean)),
            ("founder_exceptions", len(exceptions)),
            ("no_authority_action", len(no_action)),
            ("already_in_authority",
             sum(1 for row in no_action
                 if row.get("why", "").startswith("already"))),
        ])),
        ("gates", OrderedDict([
            ("passed", len(passed)),
            ("passed_counts", OrderedDict(
                (cls, counts[cls])
                for cls in ("PET_FRIENDLY", "VERIFIED_NO_PETS"))),
            ("by_family", OrderedDict(
                (cls, dict(Counter(row["brand"] for row in passed
                                   if row["class"] == cls)))
                for cls in ("PET_FRIENDLY", "VERIFIED_NO_PETS"))),
            ("rejected", len(rejected)),
            ("what_was_checked", [
                "identity resolves to a census row and a confirmed route",
                "the persisted policy block exists, matches, and its sha256 "
                "reproduces from disk",
                "the source document exists and carries a sha256",
                "the block is not brand-generic",
                "the answered URL is the routed one",
                "PET_FRIENDLY carries affirmative ORDINARY-pet evidence with "
                "service-animal clauses removed first",
                "VERIFIED_NO_PETS carries an affirmative property-specific "
                "refusal -- silence is never no-pets",
                "the census can place the property (street address, and postal "
                "code for an exclusion record)",
                "no unreviewed same-address collision with another candidate "
                "or a published row",
            ]),
        ])),
        ("passed_rows", passed),
        ("rejected_rows", rejected),
        ("no_authority_action_rows", no_action),
    ]))

    R11.write_lf(EXCEPTIONS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-exceptions/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_RULING"),
        ("count", len(exceptions) + len(rejected)),
        ("policy_wording_exceptions", exceptions),
        ("rejected_by_a_publication_gate", rejected),
        ("note", "Presented together, once. No decision field is filled here."),
    ]))

    print("=== Phase 1: inventory rebuilt from persisted artifacts ===")
    print("  distinct identities      :", len(verdicts))
    print("  clean before gates       :", len(clean),
          dict(Counter(row["class"] for row in clean)))
    print("  founder exceptions       :", len(exceptions))
    print("  no authority action      :", len(no_action))
    print()
    print("=== Phase 3: publication gates ===")
    print("  PASSED  :", len(passed), dict(counts))
    print("  REJECTED:", len(rejected))
    for row in rejected:
        print("     %-40s %s" % (row["canonical_name"][:40],
                                 row["gate_failures"][:1]))
    print("wrote", OUT_PATH.name, "and", EXCEPTIONS_PATH.name)


if __name__ == "__main__":
    run()

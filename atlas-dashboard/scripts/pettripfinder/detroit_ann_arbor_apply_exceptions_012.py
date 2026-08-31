# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012, Phase 4.

Applies the five resolved exceptions through order 011's own paths.

THIS DRIVES 011's CODE, IT DOES NOT RESTATE IT. The reconciliation gates, the
record builders, the contract checks and the geography and collision rules are
all order 011's; this module changes exactly two inputs and re-runs them:

  * the two HOLD rows now carry a founder disposition, so their class becomes
    VERIFIED_NO_PETS. The reader still returns an unresolved boolean and the
    SHARED READER IS UNTOUCHED -- the resolved value is stamped
    ``FOUNDER_DISPOSITION`` so no one later mistakes a founder's ruling on one
    property for something the reader decided.
  * the census now states the two Auburn Hills addresses, and the Troy pair now
    has a reviewed same-campus resolution, so 011's own gates stop rejecting
    those three of their own accord. Nothing about those gates is relaxed.

If a gate still refuses a row, it stays refused. The point of resolving an
exception is to give the gate the fact it was missing, never to route around it.
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
    detroit_ann_arbor_authority_application_011 as A11,
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012"
DECISION_DATE = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
DISPOSITIONS_PATH = LP / "detroit_ann_arbor_founder_dispositions_012.json"
CANDIDATES_PATH = LP / "detroit_ann_arbor_reconciled_candidates_012.json"
DECISIONS_PATH = LP / "detroit_ann_arbor_founder_decisions_012.json"

AUTHORISATION_CLAUSE = (
    "Approve the two policy holds as VERIFIED_NO_PETS on identity-specific "
    "founder dispositions; apply the three display exceptions resolved from "
    "first-party evidence at zero cost.")


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def reconcile() -> Dict:
    """Order 011's reconciliation, with the dispositions applied first."""
    dispositions = {row["identity_key"]: row
                    for row in load(DISPOSITIONS_PATH)["dispositions"]}

    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}

    # ALREADY ANSWERED IS DONE. Order 011 applied most of these identities and
    # then WITHDREW their routes, because publication answered the question the
    # route existed to ask. Re-proposing them here would fail the route gate for
    # a reason that is actually a success, and would try to write a second
    # authority record for a hotel that already has one.
    already = {row["identity_key"] for row in
               load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    already |= {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}

    verdicts: "OrderedDict[str, Dict]" = OrderedDict()
    for _label, path in R11.SOURCES:
        for result in load(path)["results"]:
            if (result["class"] in R11.CANDIDATE_CLASSES
                    and result["identity_key"] not in already):
                verdicts[result["identity_key"]] = dict(result)

    applied = []
    for key, ruling in dispositions.items():
        row = verdicts.get(key)
        if row is None:
            raise SystemExit("STOP: %s has no verdict to dispose of" % key)
        if row["class"] != R11.HOLD:
            raise SystemExit("STOP: %s is %s, not a HOLD" % (key, row["class"]))
        reading = dict(row["reading"] or {})
        if ruling["exact_quote_ruled_on"] not in (reading.get("block_text") or ""):
            raise SystemExit("STOP: %s -- the disposed quote is not in the "
                             "reading this run is about to reclassify" % key)
        # The FOUNDER resolves the boolean the reader declined to. Stamped, so
        # a later reader cannot be credited with a decision it did not make.
        reading["pets_allowed"] = False
        reading["pets_allowed_source"] = "FOUNDER_DISPOSITION"
        reading["pets_allowed_authorisation"] = WORK_ORDER
        row["reading"] = reading
        row["class"] = ruling["decision"]
        row["founder_disposition"] = OrderedDict([
            ("decided_by", ruling["decided_by"]),
            ("decided_at", ruling["decided_at"]),
            ("authorisation", ruling["authorisation"]),
            ("exact_quote_ruled_on", ruling["exact_quote_ruled_on"]),
            ("scope", ruling["scope"]),
            ("shared_reader_modified", False),
        ])
        applied.append(key)

    clean, rejected, holds = [], [], []
    for key, candidate in verdicts.items():
        if candidate["class"] == R11.HOLD:
            holds.append(candidate)
            continue
        ok, failures = R11.gate(candidate, census, routes)
        row = OrderedDict([
            ("identity_key", key),
            ("canonical_name", candidate["canonical_name"]),
            ("brand", candidate["brand"]),
            ("class", candidate["class"]),
            ("source_pass", candidate.get("_pass") or "012"),
            ("attempt_id", candidate["attempt_id"]),
            ("canonical_url", candidate["canonical_url"]),
            ("reading", candidate["reading"]),
        ])
        if candidate.get("founder_disposition"):
            row["founder_disposition"] = candidate["founder_disposition"]
        (clean if ok else rejected).append(row)
        if not ok:
            row["gate_failures"] = failures

    published_rows = [dict(row, _published=True) for row in
                      load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]]
    for row in published_rows:
        census_row = census.get(row["identity_key"]) or {}
        row["canonical_name"] = row.get("name") or census_row.get("canonical_name") or ""
        row["address"] = census_row.get("address") or ""
        row["postal_code"] = census_row.get("postal_code") or ""
    candidate_rows = []
    for row in clean:
        census_row = census.get(row["identity_key"]) or {}
        candidate_rows.append(dict(row, address=census_row.get("address") or "",
                                   postal_code=census_row.get("postal_code") or ""))
    collisions = R11.address_collisions(candidate_rows, published_rows)
    for row in list(clean):
        if row["identity_key"] in collisions:
            clean.remove(row)
            row["gate_failures"] = [collisions[row["identity_key"]]]
            rejected.append(row)

    counts = Counter(row["class"] for row in clean)
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-reconciled-candidates/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note",
         "Order 011's reconciliation and gates, re-run after this order "
         "resolved the five exceptions. Two HOLDs carry an identity-specific "
         "founder disposition; the other three were unblocked by giving the "
         "gates the facts they were missing -- two street addresses and a "
         "reviewed same-campus resolution -- never by relaxing a gate."),
        ("shared_reader_modified", False),
        ("founder_dispositions_applied", applied),
        ("already_answered_and_skipped", len(already)),
        ("gates", OrderedDict([
            ("clean", len(clean)),
            ("clean_counts", OrderedDict(
                (cls, counts[cls]) for cls in (R11.PET_FRIENDLY,
                                               R11.VERIFIED_NO_PETS))),
            ("rejected", len(rejected)),
            ("holds_remaining", len(holds)),
        ])),
        ("clean_candidates", clean),
        ("rejected_candidates", rejected),
        ("holds", holds),
    ])
    R11.write_lf(CANDIDATES_PATH, doc)
    return doc


def run() -> None:
    doc = reconcile()
    print("=== Phase 4: reconciliation after the exceptions ===")
    print("  clean            :", doc["gates"]["clean"],
          dict(doc["gates"]["clean_counts"]))
    print("  rejected         :", doc["gates"]["rejected"])
    for row in doc["rejected_candidates"]:
        print("     STILL REFUSED %-38s %s"
              % (row["canonical_name"][:38], row["gate_failures"][:1]))
    print("  holds remaining  :", doc["gates"]["holds_remaining"])

    # Order 011's authority application, pointed at this order's candidates.
    A11.CANDIDATES = CANDIDATES_PATH
    A11.DECISIONS_PATH = DECISIONS_PATH
    A11.WORK_ORDER = WORK_ORDER
    A11.AUTHORISATION_CLAUSE = AUTHORISATION_CLAUSE
    A11.run()


if __name__ == "__main__":
    try:
        run()
    except A11.Stop as stop:
        raise SystemExit("STOP: %s" % stop)

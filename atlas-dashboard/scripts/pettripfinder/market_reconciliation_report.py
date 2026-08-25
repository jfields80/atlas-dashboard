"""PTF-CENSUS-PARTITION-NORMALIZATION-001 -- what each market now knows.

A deterministic, non-public reconciliation over the committed identity
authorities. It reads census, partition, routing, policy package and exclusion
registry for every registered market and reports what they agree on -- and,
more usefully, anything they do not.

Read-only. Prints by default; writes JSON only where an operator names a path,
and refuses to write inside the authority directories it describes.

    python -m scripts.pettripfinder.market_reconciliation_report
    python -m scripts.pettripfinder.market_reconciliation_report --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from scripts.pettripfinder.census_partition_builder import PACKAGE_DIR, WORK_ORDER
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

CENSUS_DIR = PACKAGE_DIR / "identity_census"

MARKETS = ("columbus-oh", "cleveland-akron-canton-oh", "dayton-oh",
           "cincinnati-oh", "louisville-ky")

PARTITION_FILES = {
    "columbus-oh": "columbus_final_partition_001.json",
    "cleveland-akron-canton-oh": "cleveland_final_partition_002.json",
    "dayton-oh": "dayton_final_partition_001.json",
    "cincinnati-oh": "cincinnati_final_partition_001.json",
    "louisville-ky": "louisville_final_partition_001.json",
}

POLICY_FILES = {
    "columbus-oh": "hotel_policy_facts.json",
    "cleveland-akron-canton-oh": "hotel_policy_facts_cleveland-akron-canton-oh.json",
    "dayton-oh": "hotel_policy_facts_dayton-oh.json",
}


def _read(path: Path) -> Optional[Mapping]:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def market_report(market_id: str) -> "OrderedDict":
    census_doc = _read(CENSUS_DIR / ("%s.json" % market_id))
    partition_doc = _read(PACKAGE_DIR / PARTITION_FILES[market_id])
    routing = (_read(PACKAGE_DIR / "identity_routing.json") or {}).get("routes", [])
    exclusions = (_read(PACKAGE_DIR / "hotel_exclusions.json") or {}).get("exclusions", [])

    if census_doc is None or partition_doc is None:
        return OrderedDict((("market_id", market_id), ("status", "ABSENT")))

    keys = census.identity_keys(census_doc)
    rec = partition.reconcile(keys, partition_doc, market_id=market_id)

    policy_file = POLICY_FILES.get(market_id)
    published = set()
    if policy_file:
        doc = _read(PACKAGE_DIR / policy_file)
        if doc:
            published = {ptf_identity_key(h["name"]) for h in doc["hotels"]}

    market_routes = [r for r in routing if r.get("market_id") == market_id]
    active = [r for r in market_routes if r.get("status") != enums.ROUTING_RETIRED]
    outside = partition.routing_subset_violations(routing, keys, market_id=market_id)

    census_keys = [r["identity_key"] for r in census_doc["hotels"]]
    duplicates = sorted({k for k in census_keys if census_keys.count(k) > 1})

    by_address: Dict[str, List[str]] = {}
    for row in census_doc["hotels"]:
        addr = (row.get("address") or "").strip().lower()
        if addr:
            by_address.setdefault(addr, []).append(row["canonical_name"])
    shared_addresses = {a: n for a, n in sorted(by_address.items()) if len(n) > 1}

    blockers = OrderedDict(
        (state, rec.counts_by_state[state])
        for state in enums.BLOCKER_STATES if rec.counts_by_state.get(state))

    return OrderedDict((
        ("market_id", market_id),
        ("status", "OK" if rec.agrees and not outside and not duplicates else "REVIEW"),
        ("census_count", rec.census_count),
        ("partition_count", rec.partition_count),
        ("membership_agrees", rec.agrees),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("out_of_current_category", rec.out_of_category),
        ("resolved", rec.resolved),
        ("unresolved", rec.unresolved),
        ("blocker_distribution", blockers),
        ("routing_records", len(market_routes)),
        ("routing_active", len(active)),
        ("routing_retired", len(market_routes) - len(active)),
        ("routing_outside_census", [i.detail for i in outside]),
        ("published_holding_active_route",
         sorted({r["hotel_ref"]["identity_key"] for r in active}
                & published)),
        ("duplicate_identity_keys", duplicates),
        ("shared_addresses", shared_addresses),
        ("exclusion_registry_rows",
         sum(1 for e in exclusions if e.get("market_id") == market_id)),
        ("source_authorities", list(census_doc.get("source_authorities") or ())),
    ))


def build_report() -> "OrderedDict":
    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("phase", "C"),
        ("note", "Deterministic reconciliation over committed identity "
                 "authorities. Read-only; describes, never repairs."),
        ("markets", [market_report(m) for m in MARKETS]),
    ))


def _print(report: Mapping) -> None:
    out = sys.stdout.write
    out("\n%s -- market reconciliation\n%s\n\n" % (report["work_order"], "=" * 72))
    for m in report["markets"]:
        if m["status"] == "ABSENT":
            out("%-28s ABSENT\n" % m["market_id"])
            continue
        out("%-28s %s\n" % (m["market_id"], m["status"]))
        out("    census %3d  partition %3d  membership_agrees=%s\n"
            % (m["census_count"], m["partition_count"], m["membership_agrees"]))
        out("    published %3d  no-pets %2d  out-of-category %2d  "
            "resolved %3d  unresolved %3d\n"
            % (m["published"], m["verified_no_pets"], m["out_of_current_category"],
               m["resolved"], m["unresolved"]))
        out("    routing: %d records (%d active, %d retired), outside census %d\n"
            % (m["routing_records"], m["routing_active"], m["routing_retired"],
               len(m["routing_outside_census"])))
        for detail in m["routing_outside_census"]:
            out("        OUTSIDE: %s\n" % detail)
        if m["published_holding_active_route"]:
            out("        PUBLISHED WITH ACTIVE ROUTE: %s\n"
                % ", ".join(m["published_holding_active_route"]))
        if m["duplicate_identity_keys"]:
            out("        DUPLICATE KEYS: %s\n" % ", ".join(m["duplicate_identity_keys"]))
        if m["shared_addresses"]:
            out("    shared addresses (distinct identities, not merged): %d\n"
                % len(m["shared_addresses"]))
        out("    blockers:\n")
        for state, n in m["blocker_distribution"].items():
            out("        %-38s %3d\n" % (state, n))
        out("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    report = build_report()
    if args.out:
        destination = args.out.resolve()
        for protected in (PACKAGE_DIR.resolve(),):
            if protected == destination or protected in destination.parents:
                parser.error("refusing to write inside %s" % protected)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        sys.stdout.write("wrote %s\n" % destination)
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    else:
        _print(report)
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011 -- display inventory.

Seeds the newly published hotels and withdraws the routes that seeding answers.

A published record with no display row is not published: the release contract's
verified-only join FAILS CLOSED on it, which is how this step announced itself.
Seeding is not a separate act from applying the approval -- it is the second
half of it.

THIS CALLS ORDER 005's CODE RATHER THAN RESTATING IT. ``build_seed_rows``,
``verify_seed`` and ``withdraw_answered_routes`` are that order's, and its gates
are the ones that matter: exactly the published set, nothing held, nothing
verified-no-pets, every row renderable.

Only the WITHDRAWAL is driven differently. Order 005 asserts that every seeded
hotel still has a route to withdraw, which is true the first time and false ever
after -- it withdrew the original seventeen when it ran. So the withdrawal is
handed only the rows this order newly seeds, and the seed file itself is
rewritten in full from authority, because it is derived from authority and not
appended to by hand.

WITHDRAWN, NOT RETIRED: ``ROUTING_RETIRED`` says a binding should never have
been made. These bindings were correct and are the reason these hotels could be
published at all.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA          # noqa: E402
from scripts.pettripfinder import (                               # noqa: E402
    detroit_ann_arbor_display_inventory_005 as D5)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
WITHDRAWALS_PATH = LP / "detroit_ann_arbor_route_withdrawals_011.json"


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def run() -> None:
    facts = load(LP / ("hotel_policy_facts_%s.json" % MARKET))
    census = load(LP / "identity_census" / ("%s.json" % MARKET))
    partition = load(LP / "detroit_ann_arbor_final_partition_001.json")
    exclusions = load(MA.exclusions_shard_path(MARKET))

    census_by_key = {row["identity_key"]: row for row in census["hotels"]}
    partition_by_key = {item["identity_key"]: item
                        for item in partition["items"]}
    excluded_keys = {row["normalized_name"]
                     for row in exclusions["exclusions"]}

    rows = D5.build_seed_rows(facts, census_by_key, partition_by_key,
                              excluded_keys)
    checks = D5.verify_seed(rows, facts, partition_by_key)

    seed_path = MA.seed_shard_path(MARKET)
    # WHICH ROWS STILL HOLD A ROUTE, not which are absent from the seed file.
    # The seed file is derived and gets rewritten wholesale, so its contents say
    # nothing about what has been withdrawn -- and an earlier partial run had
    # already rewritten it. The routing shard is the thing that actually records
    # whether a hotel's route has been answered yet, so it is what decides here.
    routing = load(MA.routing_shard_path(MARKET))
    still_routed = {(route["hotel_ref"].get("canonical_name") or "").strip().lower()
                    for route in routing["routes"]}
    new_rows = [row for row in rows
                if row["name"].strip().lower() in still_routed]

    with seed_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(D5.SEED_COLUMNS),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    # ``withdraw_answered_routes`` OVERWRITES the shared withdrawals archive at
    # markets/reports/<market>_routing_withdrawals.json, and that archive exists
    # to preserve how this market reached its published set. Overwriting it
    # would erase order 005's record of the seventeen routes IT withdrew. So the
    # prior archive is read first and merged back afterwards, and every record
    # is stamped with the order that actually withdrew it -- the file's
    # top-level work_order alone cannot say that once it holds two orders' work.
    archive_path = (LP / "markets" / "reports"
                    / ("%s_routing_withdrawals.json" % MARKET))
    prior = load(archive_path) if archive_path.is_file() else {}
    prior_records = list(prior.get("withdrawn") or [])
    prior_order = prior.get("work_order") or ""
    for record in prior_records:
        record.setdefault("withdrawn_by_work_order", prior_order)

    routes = D5.withdraw_answered_routes(new_rows)

    archive = load(archive_path)
    for record in archive["withdrawn"]:
        record["withdrawn_by_work_order"] = WORK_ORDER
    known = {json.dumps(r, sort_keys=True) for r in archive["withdrawn"]}
    merged = prior_records + [r for r in archive["withdrawn"]
                              if json.dumps(r, sort_keys=True) not in
                              {json.dumps(p, sort_keys=True)
                               for p in prior_records}]
    archive["withdrawn"] = merged
    archive["count"] = len(merged)
    archive["work_order"] = WORK_ORDER
    archive["work_orders"] = sorted({r.get("withdrawn_by_work_order") or ""
                                     for r in merged} - {""})
    archive["note"] = (
        "CUMULATIVE. Every route this market has ever withdrawn because "
        "publication answered it, across all orders -- each record stamped "
        "with the order that withdrew it. %s"
        % (archive.get("note") or ""))
    write_lf(archive_path, archive)
    routes["archive_total"] = len(merged)
    write_lf(WITHDRAWALS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-route-withdrawals/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("note",
         "Routes withdrawn because publication answered the question they "
         "existed to ask. WITHDRAWN, never ROUTING_RETIRED: the bindings were "
         "correct, and they are why these hotels could be published."),
        ("seed_rows_total", len(rows)),
        ("seed_rows_added_by_this_order", len(new_rows)),
        ("routes", routes),
    ]))

    print("seed rows        : %d total (%d new this order)"
          % (len(rows), len(new_rows)))
    print("verify_seed      :", checks)
    print("routes before/withdrawn/after: %d / %d / %d"
          % (routes["before"], routes["withdrawn"], routes["after"]))
    print("wrote", seed_path.name, "and", WITHDRAWALS_PATH.name)


if __name__ == "__main__":
    run()

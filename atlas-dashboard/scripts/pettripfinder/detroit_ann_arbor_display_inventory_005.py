"""PTF-DETROIT-ANN-ARBOR-DISPLAY-INVENTORY-AND-RELEASE-CONTRACT-005.

Seed Detroit's display inventory, and withdraw the routes that seeding answers.

WHY THE TWO ARE ONE SCRIPT
--------------------------
They are one act with two halves. A seed row and a routing record are answers to
DIFFERENT questions -- "what does this market display" and "where do we go to
read this property's policy" -- and the moment publication answers the second,
the seed becomes the source of truth and the route must leave the routing
authority. Doing half of this leaves the market asserting both at once, which
``test_no_committed_route_is_already_seed_inventory`` refuses outright.

WHAT MAY BE SEEDED
------------------
Exactly the published set, and nothing else. A seed row is a claim that a hotel
RENDERS, so it must map 1:1 onto a committed publication-grade policy record. A
held row, an unresolved row, a verified-no-pets row and a source-silent hold are
all things this market must NOT display, and each is refused by name below
rather than filtered out quietly.

WITHDRAWN, NOT RETIRED
----------------------
``ROUTING_RETIRED`` means the binding should never have been made -- a statement
about a mistake. These bindings were correct, and they are the reason the hotels
could be published at all. They are archived in full to a withdrawals report,
answered-by-publication, and nothing is deleted.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

from scripts.pettripfinder import market_authority as MA

_REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-DISPLAY-INVENTORY-AND-RELEASE-CONTRACT-005"
DATE = "2026-08-29"

SEED_COLUMNS = ("name", "category", "address", "city", "state", "postal_code",
                "phone", "website_url", "source_url", "source_type",
                "observed_at", "rating", "amenities", "pet_policy", "canonical",
                "market_id")
CATEGORY = "pet-friendly-hotels"


class Stop(SystemExit):
    pass


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def build_seed_rows(facts: Dict, census_by_key: Dict, partition_by_key: Dict,
                    excluded_keys: set) -> List[Dict]:
    rows: List[Dict] = []
    for record in facts["hotels"]:
        key = record["identity_key"]
        row = census_by_key.get(key)
        if row is None:
            raise Stop("STOP: published %r is not in the committed census" % key)
        state = partition_by_key[key]["final_state"]
        if state != "PUBLISHED_PET_FRIENDLY":
            raise Stop("STOP: %r is published authority but its partition state is %r"
                       % (key, state))
        if key in excluded_keys:
            raise Stop("STOP: %r is both published and excluded" % key)
        if not record.get("approval"):
            raise Stop("STOP: %r carries no founder approval" % key)
        rows.append(OrderedDict([
            ("name", row["canonical_name"]),
            ("category", CATEGORY),
            ("address", row.get("address") or ""),
            ("city", row.get("city") or ""),
            ("state", row.get("state") or ""),
            ("postal_code", row.get("postal_code") or ""),
            ("phone", row.get("phone") or ""),
            ("website_url", record["source_url"]),
            ("source_url", record["source_url"]),
            ("source_type", "OFFICIAL_PROPERTY"),
            ("observed_at", record.get("verification_date") or DATE),
            ("rating", ""), ("amenities", ""),
            # The row's OWN policy words, verbatim from the approved record.
            # This field is not decoration: listing_dataset_builder treats a
            # seed row that CARRIES pet_policy and leaves it blank as
            # LISTING_PENDING_EVIDENCE and refuses to render it. A published
            # hotel with an empty policy string is a page that promises a
            # reader something it does not have, so the builder is right and
            # the string is copied rather than composed.
            ("pet_policy", record["evidence_quote"]),
            ("canonical", ""),
            ("market_id", MARKET),
        ]))
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def verify_seed(rows: List[Dict], facts: Dict, partition_by_key: Dict) -> Dict:
    """Every gate this order names, checked here rather than after the fact."""
    published_keys = {h["identity_key"] for h in facts["hotels"]}
    names = [r["name"] for r in rows]

    if len(rows) != len(published_keys):
        raise Stop("STOP: %d seed rows for %d published records"
                   % (len(rows), len(published_keys)))
    dupe_names = [n for n, c in Counter(n.strip().lower() for n in names).items() if c > 1]
    if dupe_names:
        raise Stop("STOP: duplicate display key(s) %s" % dupe_names)

    # No held / unresolved / no-pets row may appear. Checked by asking the
    # partition what each seeded name IS, rather than trusting the join.
    by_name = {v["canonical_name"].strip().lower(): k
               for k, v in partition_by_key.items() if v.get("canonical_name")}
    for name in names:
        key = by_name.get(name.strip().lower())
        if key is None:
            raise Stop("STOP: seeded %r matches no partition row" % name)
        state = partition_by_key[key]["final_state"]
        if state != "PUBLISHED_PET_FRIENDLY":
            raise Stop("STOP: seeded %r is %r, which may not display" % (name, state))

    # Cross-market display collision: no other market may already seed this name.
    global_seed = PACKAGE / "seed_businesses.csv"
    if global_seed.is_file():
        others = {r["name"].strip().lower(): r.get("market_id")
                  for r in csv.DictReader(global_seed.open(encoding="utf-8"))
                  if r.get("market_id") != MARKET and r.get("category") == CATEGORY}
        clash = sorted(n for n in (x.strip().lower() for x in names) if n in others)
        if clash:
            raise Stop("STOP: cross-market display collision %s"
                       % [(c, others[c]) for c in clash])
    # Every seeded row must actually RENDER. A row that reaches the dataset
    # builder and is dropped as pending evidence is a published hotel with no
    # page, which is worse than not seeding it: the market would report 17
    # published and show nothing.
    from scripts.pettripfinder.listing_dataset_builder import (
        LISTING_RENDERABLE, listing_readiness)
    pending = [(r["name"], listing_readiness(r)[1]) for r in rows
               if listing_readiness(r)[0] != LISTING_RENDERABLE]
    if pending:
        raise Stop("STOP: %d seeded row(s) would not render: %s" % (len(pending), pending[:4]))

    return {"rows": len(rows), "unique_display_keys": len(set(n.lower() for n in names)),
            "unique_identities": len(published_keys),
            "all_renderable": True}


def withdraw_answered_routes(seed_rows: List[Dict]) -> Dict:
    routing_path = MA.routing_shard_path(MARKET)
    routing = _load(routing_path)
    seeded = {r["name"].strip().lower() for r in seed_rows}

    keep, withdrawn = [], []
    for route in routing["routes"]:
        name = (route["hotel_ref"].get("canonical_name") or "").strip().lower()
        (withdrawn if name in seeded else keep).append(route)

    if len(withdrawn) != len(seed_rows):
        raise Stop("STOP: %d routes withdrawn for %d seeded hotels -- a seeded hotel "
                   "with no route, or a route matched twice"
                   % (len(withdrawn), len(seed_rows)))

    before = routing["count"]
    routing["routes"] = keep
    routing["count"] = len(keep)
    routing["note"] = routing["note"] + (
        " %s WITHDREW %d routes: publication answered them, and the seed inventory is now "
        "the source of truth for those properties. WITHDRAWN, not ROUTING_RETIRED -- retired "
        "means the binding should never have been made, and these bindings are the reason "
        "the hotels could be published. Every withdrawn record is archived in full at "
        "markets/reports/%s_routing_withdrawals.json."
        % (WORK_ORDER, len(withdrawn), MARKET))
    _write_json(routing_path, routing)

    report = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-routing-withdrawals/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", DATE),
        ("disposition", "WITHDRAWN_ANSWERED_BY_PUBLICATION"),
        ("note",
         "Routes withdrawn from the routing authority because publication answered them. "
         "The binding is preserved here in full -- how the URL was bound, on what identity "
         "signals, by which prior work order, and at what status -- so nothing about how "
         "this market reached its published set is lost. NONE of these is "
         "ROUTING_RETIRED: every one was a correct binding that did its job."),
        ("routes_before", before), ("routes_withdrawn", len(withdrawn)),
        ("routes_after", len(keep)),
        ("count", len(withdrawn)), ("withdrawn", withdrawn),
    ])
    _write_json(PACKAGE / "markets" / "reports" / ("%s_routing_withdrawals.json" % MARKET),
                report)
    return {"before": before, "withdrawn": len(withdrawn), "after": len(keep)}


def main(argv=None) -> int:
    facts = _load(PACKAGE / ("hotel_policy_facts_%s.json" % MARKET))
    census = _load(PACKAGE / "identity_census" / ("%s.json" % MARKET))
    partition = _load(PACKAGE / "detroit_ann_arbor_final_partition_001.json")
    exclusions = _load(MA.exclusions_shard_path(MARKET))

    census_by_key = {r["identity_key"]: r for r in census["hotels"]}
    partition_by_key = {i["identity_key"]: i for i in partition["items"]}
    excluded_keys = {e["normalized_name"] for e in exclusions["exclusions"]}

    rows = build_seed_rows(facts, census_by_key, partition_by_key, excluded_keys)
    checks = verify_seed(rows, facts, partition_by_key)

    seed_path = MA.seed_shard_path(MARKET)
    with seed_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SEED_COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    routes = withdraw_answered_routes(rows)

    print("seed rows            : 0 -> %d  (%s)" % (checks["rows"], checks))
    print("routes before/withdrawn/after: %d / %d / %d"
          % (routes["before"], routes["withdrawn"], routes["after"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

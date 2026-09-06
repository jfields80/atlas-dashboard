"""PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003 Phase 9 -- retire the routes the promotion published.

    python -m scripts.pettripfinder.cincinnati_oh_route_retirement_003
    python -m scripts.pettripfinder.cincinnati_oh_route_retirement_003 --write

A route says where an identity's policy page is, so that someone can go and read
it. Once the identity is PUBLISHED, its seed row carries that URL and the route
becomes a second, independently editable copy of the same fact -- which is the
shape a double-source defect takes. ``test_no_committed_route_is_already_seed_
inventory`` states the rule in its own failure message: "the seed remains the
source of truth for it".

Promoting 31 pet-friendly rows put 29 of them into the seed while their routes
were still ROUTING_CONFIRMED, so this module closes the gap the promotion opened.
The other two were never routed.

TO RETIRE A ROUTE IS TO REMOVE IT
---------------------------------
That is what this repository means by the word, and
PTF-CINCINNATI-HARDENED-SYNC-002 Phase 4b is the worked precedent: an earlier
order set ``status = ROUTING_RETIRED`` and left all twenty-one rows in the shard,
with a note describing exactly the right thing while doing the opposite. The
intent was correct; the mechanism was not. This module removes them.

Unlike that order, this one is entitled to set the disposition first. Sync 002
refused to promote a route to ROUTING_RETIRED because the disposition was "one
nobody made" -- it was cleaning up after a different order. Here the publication
IS this order's act, so recording that these routes are retired BECAUSE this
order published their identities is not inventing a disposition, it is stating
one. The status is set and the row is then removed in the same run, and the
ledger records both.

WHAT IT DELIBERATELY DOES NOT TOUCH
-----------------------------------
Routes whose identity is a VERIFIED_NO_PETS exclusion are KEPT. The seed rule is
the one this repository enforces; there is no rule against routing an excluded
identity, and two live markets do it -- Columbus keeps 13 and Grand Rapids 15.
Removing them would invent a rule to be consistent with.

NOTHING IS LOST
---------------
Every removed route is written verbatim to this order's ledger before it leaves
the shard, and each row is asserted to have a seed row carrying a website_url
before anything is removed. The URL is not lost: that is the whole premise.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA     # noqa: E402
from scripts.pettripfinder.site_data import normalize_name   # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003"
MARKET_ID = "cincinnati-oh"
AS_OF = "2026-09-05"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER = (PKG / "markets" / "reports"
          / "cincinnati_oh_route_retirement_003_ledger.json")

# The shard path comes from market_authority, never from a filename this module
# spells out: a module that can name a generated global can write one, and the
# globals are built from the shards by build_global_authority.
ROUTING = MA.routing_shard_path(MARKET_ID)

RETIRED = "ROUTING_RETIRED"


class RetirementError(RuntimeError):
    pass


def seed_identities() -> Dict[str, Dict]:
    return {normalize_name(row["name"]): row
            for row in MA.load_market_seed_rows(MARKET_ID)
            if row["category"] == "pet-friendly-hotels"}


def plan() -> Dict:
    doc = MA.load_market_routing_document(MARKET_ID)
    seed = seed_identities()
    keep: List[Dict] = []
    remove: List[Dict] = []
    for route in doc["routes"]:
        name = route["hotel_ref"]["normalized_name"]
        if name not in seed:
            keep.append(route)
            continue
        if not seed[name].get("website_url"):
            raise RetirementError(
                "%s: the seed row carries no website_url, so removing its route "
                "would lose the only URL for it" % name)
        remove.append(route)
    return {"document": doc, "keep": keep, "remove": remove, "seed": seed}


def run(write: bool) -> int:
    result = plan()
    doc, keep, remove = result["document"], result["keep"], result["remove"]

    print("routes before      : %d" % len(doc["routes"]))
    print("removed (now seed) : %d" % len(remove))
    print("routes after       : %d" % len(keep))
    for route in remove:
        print("   - %-52s %s"
              % (route["hotel_ref"]["normalized_name"],
                 route["official_property_url"][:58]))

    if not write:
        print("(check only -- pass --write)")
        return 0

    ledger = OrderedDict((
        ("schema", "ptf-route-retirement-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("why", "Each identity below was published by %s, so its URL now lives on "
                "its seed row and the route would be a second editable copy of the "
                "same fact. The routes are recorded here verbatim, with the "
                "retirement disposition this order is entitled to set because the "
                "publication is this order's own act, and then removed from the "
                "shard." % WORK_ORDER),
        ("routes_before", len(doc["routes"])),
        ("routes_removed", len(remove)),
        ("routes_after", len(keep)),
        ("retired", [dict(r, status=RETIRED,
                          retired_by=WORK_ORDER, retired_at=AS_OF,
                          retirement_reason=(
                              "this identity is now seed inventory (published by "
                              "%s), so its route is removed rather than left "
                              "coexisting with the seed row that carries its URL"
                              % WORK_ORDER))
                     for r in remove]),
    ))
    LEDGER.write_bytes((json.dumps(ledger, indent=1) + "\n").encode("utf-8"))

    shard = MA.build_routing_shard(MARKET_ID, keep,
                                   source_batches=doc.get("source_batches"))
    ROUTING.write_bytes((MA.render_json(shard)).encode("utf-8"))
    print("wrote %s" % LEDGER.name)
    print("wrote %s" % ROUTING.name)
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    return run(args.write)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

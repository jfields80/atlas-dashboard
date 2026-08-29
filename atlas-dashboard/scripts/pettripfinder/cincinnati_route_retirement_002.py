"""PTF-CINCINNATI-HARDENED-SYNC-002 Phase 4b -- retire, the way this repo means it.

    python -m scripts.pettripfinder.cincinnati_route_retirement_002
    python -m scripts.pettripfinder.cincinnati_route_retirement_002 --write

THE DIVERGENCE
--------------
``test_no_committed_route_is_already_seed_inventory`` states the rule in its own
failure message: "the seed remains the source of truth for it". A route says
where an identity's policy page is so that someone can go and read it. Once the
identity is published, the seed row carries that URL and the route is a second,
independently editable copy of the same fact -- which is the shape a
double-source defect takes.

Every market on the lineage obeys it, and the count says so plainly:

    cleveland-akron-canton-oh   38 routes, 99 seed rows,  0 overlap
    columbus-oh                 20 routes, 89 seed rows,  0 overlap
    dayton-oh                    9 routes, 47 seed rows,  0 overlap
    grand-rapids-holland-mi     72 routes, 43 seed rows,  0 overlap
    cincinnati-oh              210 routes, 21 seed rows, 21 overlap

Cleveland's Pass 4 is the worked example: retiring 23 routes took its total from
288 to 265, and the held/retired buckets did not move. In this repository, to
RETIRE a route is to REMOVE it.

PTF-CINCINNATI-PASS1-AUTHORITY-APPLICATION-001 read the word the other way. It
set ``status = ROUTING_RETIRED`` and left all twenty-one rows in the shard, with
a note that says exactly the right thing -- "this identity is now seed inventory
(published), so its route is retired rather than left coexisting with it" --
while doing the opposite of what the note describes. The intent was correct; the
mechanism was not.

WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT
--------------------------------------------------
It removes the 21 routes whose identity is seed inventory, and it KEEPS the 6
whose identity is a VERIFIED_NO_PETS exclusion. The seed rule is the one this
repository actually enforces; there is no rule against routing an excluded
identity, and two live markets do it -- Columbus keeps 13 and Grand Rapids 15,
both ROUTING_CONFIRMED. Removing Cincinnati's six would invent a rule to be
consistent with, which is a worse error than the one being fixed. They keep the
founder's recorded ROUTING_RETIRED disposition; only their coexistence with a
seed row was ever the problem, and they have none.

NOTHING IS LOST
---------------
Every removed route is written verbatim to
``cincinnati_route_retirement_002_ledger.json`` before it leaves the shard, and
each row's binding evidence already lives in
``cincinnati-oh_routing_evidence_001a.json`` and
``cincinnati_url_routing_recovery_001_results.json``, neither of which this
touches. The URL itself is not lost either -- that is the entire premise: the
published seed row carries it, and the run asserts so per row before removing
anything.
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

WORK_ORDER = "PTF-CINCINNATI-HARDENED-SYNC-002"
MARKET_ID = "cincinnati-oh"
AS_OF = "2026-08-29"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER = (PKG / "markets" / "reports"
          / "cincinnati_route_retirement_002_ledger.json")

# The shard paths come from market_authority, never from a path this module
# spells out. Naming a generated global's filename here is what
# ``test_no_new_module_writes_a_generated_global_artifact`` scans for, and it is
# right to: a module that can name the file can write it, and the global is
# built from the shards by build_global_authority.py.
ROUTING = MA.routing_shard_path(MARKET_ID)
SEED = MA.seed_shard_path(MARKET_ID)


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
        if name in seed:
            if route["status"] != "ROUTING_RETIRED":
                raise RetirementError(
                    "%s is seed inventory but its route is %s, not retired. "
                    "An ACTIVE route for a published identity is a disposition "
                    "nobody made and is not this module's to make."
                    % (name, route["status"]))
            if not seed[name].get("website_url"):
                raise RetirementError(
                    "%s: the seed row carries no website_url, so removing its "
                    "route would lose the only URL for it" % name)
            remove.append(route)
        else:
            keep.append(route)
    return {"document": doc, "keep": keep, "remove": remove, "seed": seed}


def run(write: bool) -> int:
    result = plan()
    doc, keep, remove = result["document"], result["keep"], result["remove"]
    kept_retired = [r for r in keep if r["status"] == "ROUTING_RETIRED"]

    print("routes before      : %d" % len(doc["routes"]))
    print("removed (seed)     : %d" % len(remove))
    print("routes after       : %d" % len(keep))
    print("retired kept       : %d (VERIFIED_NO_PETS identities; Columbus and "
          "Grand Rapids route excluded identities too)" % len(kept_retired))
    for route in remove:
        print("   - %-50s %s"
              % (route["hotel_ref"]["normalized_name"],
                 route["official_property_url"][:60]))

    if not write:
        print("(check only -- pass --write)")
        return 0

    ledger = OrderedDict((
        ("schema", "ptf-market-route-retirement-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("why", "PTF-CINCINNATI-PASS1-AUTHORITY-APPLICATION-001 marked these "
                "routes ROUTING_RETIRED but left them in the shard. In this "
                "repository retirement is removal -- Cleveland Pass 4's 23 "
                "retirements took its route total from 288 to 265 -- and "
                "test_no_committed_route_is_already_seed_inventory enforces "
                "it: once an identity is published, its seed row is the source "
                "of truth for its URL and a route beside it is a second, "
                "independently editable copy of the same fact."),
        ("what_is_preserved",
         "These records verbatim, plus the binding evidence in "
         "cincinnati-oh_routing_evidence_001a.json and "
         "cincinnati_url_routing_recovery_001_results.json, which are "
         "untouched. Each identity's official URL remains on its published "
         "seed row, asserted per row before removal."),
        ("count", len(remove)),
        ("removed_routes", remove),
    ))
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")

    shard = MA.build_routing_shard(MARKET_ID, keep,
                                   doc.get("source_batches") or ())
    ROUTING.write_text(MA.render_json(shard), encoding="utf-8", newline="")
    print("WROTE %s (%d routes)" % (ROUTING.name, len(keep)))
    print("WROTE %s (%d preserved)" % (LEDGER.name, len(remove)))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except RetirementError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())

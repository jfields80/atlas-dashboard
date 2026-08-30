# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005 Phase 5a -- fill the addresses this order needs.

    python -m scripts.pettripfinder.pittsburgh_census_address_fill_005
    python -m scripts.pettripfinder.pittsburgh_census_address_fill_005 --write

The three identities the founder ruled publishable in this order are registered
but were never given a street address. Both consumers refuse them for it:
``hotel_exclusions.validate`` lists ``address`` in REQUIRED_FIELDS, and the seed
importer refuses an addressless inventory row.

Identical in kind to PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 7a, and identical in
its limits:

  * ADD ONLY -- a non-empty address is never overwritten; the run refuses
    rather than disagree with a committed one, because disagreeing is an
    identity question and belongs to the founder.
  * No identity is added, removed, renamed, superseded or downgraded. The row
    count and schema do not move, so the release contract's census pin -- which
    binds by COUNT and SCHEMA, not by hash -- does not lapse.
  * Each address comes ONLY from that identity's own bound first-party page:
    ``observation.identity_check.address_on_page``, from the capture whose
    SHA-256 the founder's ruling names. Nothing is geocoded, inferred from a
    name, or copied from a sibling property.

Every fill is written to a ledger with its source page and snapshot hash, so a
single one can be checked or reverted on its own.
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

from scripts.pettripfinder.contracts import census as CENSUS_CONTRACT     # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (          # noqa: E402
    CENSUS, MARKET_ID, REPORTS, _load, _observations, _write)
from scripts.pettripfinder.pittsburgh_hold_application_005 import (       # noqa: E402
    AS_OF, HOLD_RULINGS, WORK_ORDER)

LEDGER = REPORTS / "pittsburgh_hold_resolution_005_census_address_fills.json"


class FillError(RuntimeError):
    pass


def _clean(value: object) -> str:
    return str(value or "").strip()


def plan() -> Dict:
    census = _load(CENSUS)
    rows = {h["identity_key"]: h for h in census["hotels"]}
    obs = _observations()
    fills: List[Dict] = []
    for held, ruling in HOLD_RULINGS.items():
        target = ruling["target"]
        row = rows.get(target)
        if row is None:
            raise FillError("%s is not a registered identity" % target)
        if _clean(row.get("address")):
            continue
        record = obs.get(held)
        if record is None:
            raise FillError("%s has no owned observation" % held)
        source = record["observation"]
        address = _clean((source.get("identity_check") or {}).get("address_on_page"))
        if not address:
            raise FillError("%s: the bound page states no street address" % held)
        fills.append(OrderedDict((
            ("identity_key", target),
            ("canonical_name", row.get("canonical_name")),
            ("address_filled", address),
            ("source", "observation.identity_check.address_on_page"),
            ("observed_from_identity", held),
            ("source_url", source.get("source_url")),
            ("bound_snapshot_hash", source.get("snapshot_hash")),
            ("observed_at", source.get("observed_at")),
        )))
    return OrderedDict((("census", census), ("fills", fills)))


def run(write: bool) -> int:
    planned = plan()
    census, fills = planned["census"], planned["fills"]
    by_key = {f["identity_key"]: f for f in fills}
    filled = json.loads(json.dumps(census))
    for hotel in filled["hotels"]:
        fill = by_key.get(hotel["identity_key"])
        if fill is None:
            continue
        if _clean(hotel.get("address")):
            raise FillError("%s already carries an address; this run is "
                            "ADD-ONLY" % hotel["identity_key"])
        hotel["address"] = fill["address_filled"]

    if len(filled["hotels"]) != len(census["hotels"]):
        raise FillError("the row count moved")
    if filled.get("count") != census.get("count"):
        raise FillError("the declared count moved")
    issues = CENSUS_CONTRACT.validate(filled, market_states=["PA"])
    if issues:
        raise FillError("the filled census does not validate: %s"
                        % list(issues)[:5])

    print("census rows        : %d (unchanged)" % len(filled["hotels"]))
    print("addresses filled   : %d" % len(fills))
    for fill in fills:
        print("   %-52s %s" % (fill["identity_key"][:51], fill["address_filled"]))
    print("contract issues    : 0")
    if not write:
        print("(check only -- pass --write)")
        return 0

    _write(CENSUS, filled)
    print("WROTE %s" % CENSUS.name)
    _write(LEDGER, OrderedDict((
        ("schema", "ptf-census-field-completion/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("what_this_is",
         "Street addresses filled on identities the registered census already "
         "held, each read from that identity's own bound first-party page. "
         "ADD-ONLY: nothing added, removed, renamed or superseded, and no "
         "committed address replaced. Row count and schema unchanged."),
        ("count", len(fills)),
        ("fills", fills),
    )))
    print("WROTE %s" % LEDGER.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except FillError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

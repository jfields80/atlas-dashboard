# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-FREE-LANE-APPLICATION-007 Phase 7 -- withdraw answered routes.

    python -m scripts.pettripfinder.cincinnati_route_withdrawal_007 --write

An acquisition route is a standing instruction to go and find this property's
policy. Once authority holds the answer the instruction is stale, and a route
sitting beside a published seed row is a second independently editable copy of
the same URL. So every identity that entered authority in this order loses its
route, published and excluded alike.

Two things this does NOT do.

It does not delete history. Every removed record is preserved verbatim in the
withdrawal ledger, which is the artifact a later reader consults when they find
no route and need to know why.

It does not withdraw the held row. Comfort Suites MainStay was ruled
HOLD_FOR_IDENTITY_REVIEW and the founder said explicitly not to withdraw its
route: a withdrawn route is how a row stops being worked, and this one still
needs working. Withdrawing it would have quietly converted a hold into an
abandonment.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA            # noqa: E402
from scripts.pettripfinder.cincinnati_free_lane_application_007 import (  # noqa: E402
    HELD, MARKET_ID, PACKAGE, REPORTS, RENAME_FROM, WORK_ORDER, _load)

AS_OF = "2026-08-30"
LEDGER = REPORTS / "cincinnati_free_lane_route_withdrawals_007.json"


class WithdrawalError(RuntimeError):
    pass


def answered_identities():
    """Only the identities THIS order put into authority.

    Not everything authority answers. Fifteen identities excluded by earlier
    orders still carry routes, and withdrawing those would be this order
    silently finishing another order's work -- a change nobody asked for and
    nobody reviewed. They are left exactly as they are.
    """
    from scripts.pettripfinder.cincinnati_free_lane_application_007 import (
        PROBE, RULINGS, SCALE, RENAME_TO)
    from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
    rows = _load(PROBE)["rows"] + _load(SCALE)["rows"]
    answered = {r["identity_key"] for r in rows
                if r["triage"].startswith("CLEAN_")}
    for key, ruling in RULINGS.items():
        if ruling["publishes"] or ruling.get("excludes"):
            answered.add(key)
    answered.add(ptf_identity_key(RENAME_TO))
    answered.discard(HELD)
    return answered


def plan():
    doc = MA.load_market_routing_document(MARKET_ID)
    answered = answered_identities()
    keep, remove = [], []
    for route in doc["routes"]:
        key = route["hotel_ref"]["identity_key"]
        if key == HELD:
            keep.append(route)
            continue
        if key in answered:
            record = OrderedDict(route)
            record["withdrawn_at"] = AS_OF
            record["withdrawn_by"] = WORK_ORDER
            record["withdrawn_reason"] = (
                "The identity entered Cincinnati authority in this order, so "
                "the acquisition instruction this route carries is answered.")
            remove.append(record)
            continue
        keep.append(route)

    if any(r["hotel_ref"]["identity_key"] == HELD for r in remove):
        raise WithdrawalError("the held identity's route was withdrawn")
    if not any(r["hotel_ref"]["identity_key"] == HELD for r in keep):
        raise WithdrawalError(
            "%s has no route to keep; the founder ordered it kept" % HELD)
    return doc, keep, remove


def run(write: bool) -> int:
    doc, keep, remove = plan()
    print("routes before   : %d" % len(doc["routes"]))
    print("withdrawn       : %d" % len(remove))
    print("routes after    : %d" % len(keep))
    print("held, kept      : %s" % HELD)
    if not write:
        print("(check only -- pass --write)")
        return 0

    ledger = OrderedDict((
        ("schema", "ptf-market-route-retirement-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("why", "Every identity listed here entered Cincinnati authority in "
                "PTF-CINCINNATI-FREE-LANE-APPLICATION-007 -- as a published "
                "policy record or as a registered VERIFIED_NO_PETS exclusion "
                "-- so its acquisition route is answered. In this repository "
                "retirement is REMOVAL, not a status flip: a published "
                "identity's seed row is the source of truth for its URL, and "
                "a route beside it is a second copy of the same fact."),
        ("what_is_preserved",
         "These records verbatim, including each route's binding evidence and "
         "identity context. Published identities keep their URL on their seed "
         "row; excluded identities keep theirs on the exclusion record's "
         "official_url."),
        ("not_withdrawn", OrderedDict((
            ("identity_key", HELD),
            ("why", "Ruled HOLD_FOR_IDENTITY_REVIEW. The founder ordered its "
                    "route kept: a withdrawn route is how a row stops being "
                    "worked, and this row still needs working."),
        ))),
        ("count", len(remove)),
        ("removed_routes", remove),
    ))
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")
    print("WROTE %s" % LEDGER.name)

    shard = MA.build_routing_shard(MARKET_ID, keep,
                                   doc.get("source_batches") or ())
    MA.routing_shard_path(MARKET_ID).write_text(
        MA.render_json(shard), encoding="utf-8", newline="\n")
    print("WROTE routing shard (%d routes)" % len(keep))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except WithdrawalError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

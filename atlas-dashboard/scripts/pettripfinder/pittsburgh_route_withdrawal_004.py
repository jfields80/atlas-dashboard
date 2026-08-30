# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 6 -- defect D2, withdraw answered routes.

    python -m scripts.pettripfinder.pittsburgh_route_withdrawal_004 --write

An acquisition route is a standing instruction to go and find this property's
policy. Once authority holds the answer the instruction is stale, and a route
sitting beside a published seed row is a second independently editable copy of
the same URL.

Pittsburgh's routing shard carries six routes and the audit found every one of
them answered -- four by a published policy record, two by a registered
VERIFIED_NO_PETS exclusion. All six were answered by EARLIER Pittsburgh orders,
not by this one; D2 is that nobody withdrew them at the time.

WHAT IS ANSWERED IS READ FROM AUTHORITY, NOT FROM A LIST
----------------------------------------------------------
The answered set is derived from the committed policy package and exclusion
shard as they stand after Phase 8, so this cannot drift from what the market
actually holds. A route whose identity is in neither is UNANSWERED and is kept:
a withdrawn route is how a row stops being worked, and withdrawing one that
still needs working would quietly convert a live question into an abandonment.

THIS DOES NOT TOUCH THE SHARED CUMULATIVE ARCHIVE
---------------------------------------------------
PTF-DETROIT-FOUNDER-REVIEW-AUTHORITY-011 found that ``withdraw_answered_routes``
OVERWRITES the shared withdrawals archive, losing every earlier order's history.
So that function is not used here. Instead this writes its OWN work-order-scoped
ledger beside the other markets' -- written fresh, never read, never appended to
-- which is how Cincinnati keeps ``...withdrawals_007.json`` and ``..._010.json``
side by side. Nothing any other order wrote is opened.

Retirement is REMOVAL, not a status flip: a published identity's seed row is the
source of truth for its URL, and a route beside it is a second copy of the same
fact. Every removed record is preserved verbatim in the ledger, stamped with
Pittsburgh-specific provenance, which is the artifact a later reader consults
when they find no route and need to know why.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA            # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (    # noqa: E402
    AS_OF, MARKET_ID, PACKAGE, REPORTS, WORK_ORDER, _load, _write, holds)

LEDGER = REPORTS / "pittsburgh_hardened_sync_004_route_withdrawals.json"


class WithdrawalError(RuntimeError):
    pass


def answered() -> Dict[str, str]:
    """``identity_key -> the authority that answers it``, read from authority."""
    out: Dict[str, str] = {}
    for record in _load(PACKAGE)["hotels"]:
        out[record["identity_key"]] = "PUBLISHED_PET_FRIENDLY"
    for row in MA.load_market_exclusions_document(MARKET_ID)["exclusions"]:
        out.setdefault(row["normalized_name"], row["exclusion_state"])
    return out


def plan() -> Tuple[Dict, List[Dict], List[Dict]]:
    doc = MA.load_market_routing_document(MARKET_ID)
    resolved = answered()
    held = set(holds())
    keep, remove = [], []
    for route in doc["routes"]:
        key = route["hotel_ref"]["identity_key"]
        state = resolved.get(key)
        if state is None or key in held:
            keep.append(route)
            continue
        record = OrderedDict(route)
        record["withdrawn_at"] = AS_OF
        record["withdrawn_by"] = WORK_ORDER
        record["withdrawn_market_id"] = MARKET_ID
        record["withdrawn_answered_by"] = state
        record["withdrawn_reason"] = (
            "Pittsburgh authority holds this identity as %s, so the "
            "acquisition instruction this route carries is answered. Defect D2 "
            "of the hardened-readiness audit: the route outlived the answer."
            % state)
        remove.append(record)
    for route in remove:
        if route["hotel_ref"]["identity_key"] in held:
            raise WithdrawalError("a held identity's route was withdrawn")
    return doc, keep, remove


def run(write: bool) -> int:
    doc, keep, remove = plan()
    print("routes before  : %d" % len(doc["routes"]))
    print("withdrawn      : %d" % len(remove))
    print("routes after   : %d" % len(keep))
    for route in remove:
        print("   %-52s %s" % (route["hotel_ref"]["identity_key"][:51],
                               route["withdrawn_answered_by"]))
    if not write:
        print("(check only -- pass --write)")
        return 0

    _write(LEDGER, OrderedDict((
        ("schema", "ptf-market-route-retirement-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("defect", "D2 -- already-answered Pittsburgh identities still carried "
                   "active acquisition routes"),
        ("why", "Every identity listed here is held by Pittsburgh authority -- "
                "as a published policy record or as a registered exclusion -- "
                "so its acquisition route is answered. In this repository "
                "retirement is REMOVAL, not a status flip: a published "
                "identity's seed row is the source of truth for its URL, and a "
                "route beside it is a second copy of the same fact."),
        ("what_is_preserved",
         "These records verbatim, including each route's binding evidence and "
         "identity context. Published identities keep their URL on their seed "
         "row; excluded identities keep theirs on the exclusion record's "
         "official_url."),
        ("shared_archive_untouched",
         "This ledger is written fresh and is scoped to this work order. No "
         "cumulative cross-market withdrawals archive was opened or rewritten "
         "(PTF-DETROIT-FOUNDER-REVIEW-AUTHORITY-011: withdraw_answered_routes "
         "OVERWRITES that file, so it is not used here)."),
        ("routes_before", len(doc["routes"])),
        ("routes_after", len(keep)),
        ("count", len(remove)),
        ("removed_routes", remove),
    )))
    print("WROTE %s" % LEDGER.name)
    shard = MA.build_routing_shard(MARKET_ID, keep, doc.get("source_batches") or ())
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

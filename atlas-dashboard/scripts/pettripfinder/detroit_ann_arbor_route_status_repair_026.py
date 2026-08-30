# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FREE-CAPTURE-AND-ROUTING-026, Phase 6.

Corrects the status of the Roberts Riverwalk route.

THE SHARD STILL CARRIED A HIJACKED DOMAIN AS ROUTING_CONFIRMED. Order 025
established that detroitriverwalkhotel.com lapsed and now 301s to an
online-gambling site, and it preserved the route as historical evidence -- but
it left the STATUS alone. ROUTING_CONFIRMED is the only status the capture
queue may act on, so every future cohort builder keying on "confirmed route"
would pick this up and send someone to open it. That is not hypothetical: this
order's own first cohort run admitted it.

The route is NOT deleted and NOT retired. RETIRED means the binding should
never have been made, and that is untrue -- the binding was correct when it was
made and records how the URL was bound. HELD is the honest status: retained,
visible, undecided, and explicitly not a work instruction.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-CAPTURE-AND-ROUTING-026"
AS_OF = "2026-08-30"
ROBERTS = "roberts riverwalk hotel"
POISONED = "detroitriverwalkhotel.com"


def run():
    path = MA.routing_shard_path(MARKET)
    doc = R11.load(path)
    changed = []
    for route in doc["routes"]:
        key = route["hotel_ref"]["identity_key"]
        if key != ROBERTS:
            continue
        if POISONED not in (route.get("official_property_url") or ""):
            raise SystemExit("STOP: %r no longer points at %s; not touching a "
                             "route whose URL has changed underneath this "
                             "order" % (key, POISONED))
        before = route.get("status")
        route["status"] = "ROUTING_HELD"
        route["verified_at"] = AS_OF
        sources = route.setdefault("binding_sources", [])
        note = ("%s: the routed domain LAPSED and now redirects to an "
                "online-gambling site. The binding is preserved as the "
                "historical record of how this URL was bound, but the status "
                "is HELD so no capture queue may act on it. A new first-party "
                "route must be established before this identity is worked."
                % WORK_ORDER)
        if note not in sources:
            sources.append(note)
        changed.append((key, before, route["status"]))

    if not changed:
        raise SystemExit("STOP: no Roberts Riverwalk route found")
    R11.write_lf(path, doc)

    print("=== Phase 6: poisoned route status corrected ===")
    for key, before, after in changed:
        print("   %-32s %s -> %s" % (key, before, after))
    print("   the URL and its binding history are PRESERVED, not deleted")


if __name__ == "__main__":
    run()

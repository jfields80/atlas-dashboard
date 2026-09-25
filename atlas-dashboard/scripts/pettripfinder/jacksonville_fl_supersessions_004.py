"""PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004 -- extend the supersessions chain with the Jacksonville
deployment production now serves.

    python -m scripts.pettripfinder.jacksonville_fl_supersessions_004 [--write]

THE CHAIN IS EXTENDED, NEVER REWRITTEN
---------------------------------------
`supersessions.json` lapsed for nineteen launches before the lineage repair, so the three canonical steps are
done explicitly and each is checked:

  1. `reviewed_by` becomes this order.
  2. The previously CURRENT authorization stops calling itself current: its note becomes historical, naming the
     deployment that replaced it. Its bound release contracts are re-hashed and any drift is reported -- a
     silent hash change there is a market moving under a live authorization.
  3. This deployment's authorization is APPENDED as the new CURRENT entry, with its own bound contracts
     re-hashed.

The chain lists only authorizations production actually CONSUMED, because `chain_problems` derives from the
deployment records. Jacksonville's is consumed, so it belongs; nothing here is deleted or reordered.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004"
AUTHORIZING_WORK_ORDER = "PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
AUTHORIZATION_ID = "ptf-auth-jacksonville-003-f82f0714db2d"
PREVIOUS_AUTHORIZATION_ID = "ptf-auth-west-palm-beach-006-23728b4bff71"
DEPLOYMENT_ID = "6ab6c8798bd9daf5038ae3e5"
PREVIOUS_DEPLOYMENT_ID = "6ab599163f833ab7f48b395d"
MARKET = "jacksonville-fl"
PATH = os.path.join(_DASH, "tests", "pettripfinder", "pins", "supersessions.json")
CONTRACTS = os.path.join(_DASH, "deploy", "netlify", "release_contracts")

NEW_NOTE = (
    "The CURRENT live authorization. It binds all 34 release contracts exactly, because production was "
    "authorized against what source holds and no application order has moved a market since. Registered with an "
    "EMPTY moved list rather than left unregistered: an unregistered authorization binds everything by default, "
    "so the two read alike today, and only the explicit entry says that emptiness was checked. The next "
    "application order that re-authors a market lists it here. Lineage it rests on, recorded here because it is "
    "not a chain entry: jacksonville-fl was built from zero by "
    "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 on the West-Palm-Beach-live release, registered by "
    "PTF-JACKSONVILLE-FL-REGISTRATION-AND-STAGING-002 as COMPOSITE_FRESH_MARKET_DATA_ONLY (FAST 15/15, 0 broad "
    "regression runs) into package pkg-jacksonville-fl-60ba2edccd4882b3, and founder-authorized ONCE by "
    "%s. This is the market's FIRST authorization and FIRST deployment: nothing was superseded, no earlier "
    "authorization exists for it, and this entry inherits nothing. The founder's decision deliberately withheld "
    "the 1201 Kings Avenue dual-brand Hilton pair (2 rows, no identity_resolutions.json ruling written) and kept "
    "Amelia Island a CORRIDOR of this market rather than promoting it." % AUTHORIZING_WORK_ORDER
)

HISTORICAL_NOTE_SUFFIX = (
    " Historical. It was the current live authorization until deploy %s published jacksonville-fl as the "
    "thirty-fourth market (authorization %s, %s), which this chain records as the new CURRENT entry."
    % (DEPLOYMENT_ID, AUTHORIZATION_ID, WORK_ORDER)
)


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh, object_pairs_hook=OrderedDict)


def _bound_contracts(auth):
    """An authorization binds its release contracts as a LIST of {market_id, path, sha256}."""
    return OrderedDict((c["market_id"], c["sha256"]) for c in (auth.get("release_contracts") or []))


def _contract_drift(bound):
    """Markets whose committed release contract no longer hashes to what the authorization bound."""
    drift = []
    for market, want in sorted(bound.items()):
        p = os.path.join(CONTRACTS, "%s.json" % market)
        got = hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else None
        if got != want:
            drift.append(market)
    return drift


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    doc = _load(PATH)
    chain = doc["authorizations"]
    if AUTHORIZATION_ID in chain:
        raise SystemExit("%s is already in the chain" % AUTHORIZATION_ID)
    if PREVIOUS_AUTHORIZATION_ID not in chain:
        raise SystemExit("the previous CURRENT authorization %s is not in the chain" % PREVIOUS_AUTHORIZATION_ID)

    # CONSUMPTION IS RECORDED IN THE STATUS HISTORY, not in a top-level field: `transition` appends the
    # deployment id to the entry it writes. Reading a top-level `deploy_id` finds None on a properly consumed
    # authorization and would refuse a chain entry that belongs.
    auth = DA.load_authorization(AUTHORIZATION_ID)
    last = (auth.get("status_history") or [{}])[-1]
    if auth["authorization_status"] != DA.DEPLOYED or last.get("deployment_id") != DEPLOYMENT_ID:
        raise SystemExit("%s is %s (consumed deployment_id %r); only a CONSUMED authorization joins the chain"
                         % (AUTHORIZATION_ID, auth["authorization_status"], last.get("deployment_id")))

    # STEP 2 -- the previous CURRENT entry becomes historical, and its bound contracts are re-hashed for drift.
    prev_auth = DA.load_authorization(PREVIOUS_AUTHORIZATION_ID)
    prev_bound = _bound_contracts(prev_auth)
    drift = _contract_drift(prev_bound)
    prev_entry = chain[PREVIOUS_AUTHORIZATION_ID]
    prev_note = prev_entry["note"]
    if "Historical." not in prev_note:
        prev_note = prev_note.replace("The CURRENT live authorization.", "Was the current live authorization.", 1)
        prev_note = prev_note + HISTORICAL_NOTE_SUFFIX
    prev_entry["note"] = prev_note

    # STEP 3 -- append this deployment's authorization as the new CURRENT entry.
    bound = _bound_contracts(auth)
    mine_drift = _contract_drift(bound)
    chain[AUTHORIZATION_ID] = OrderedDict((
        ("work_order", AUTHORIZING_WORK_ORDER),
        ("moved_by_later_work", OrderedDict()),
        ("note", NEW_NOTE),
    ))

    # STEP 1 -- this order reviewed the chain.
    doc["reviewed_by"] = WORK_ORDER

    print("chain entries        :", len(chain) - 1, "->", len(chain))
    print("previous CURRENT     :", PREVIOUS_AUTHORIZATION_ID)
    print("  bound contracts    :", len(prev_bound), "| DRIFT:", drift or "none")
    print("new CURRENT          :", AUTHORIZATION_ID)
    print("  bound contracts    :", len(bound), "| DRIFT:", mine_drift or "none")
    print("reviewed_by          :", doc["reviewed_by"])
    if drift or mine_drift:
        raise SystemExit("release-contract drift under a live authorization: %r / %r" % (drift, mine_drift))
    if not args.write:
        print("nothing written (pass --write)")
        return 0
    with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("written              :", os.path.relpath(PATH, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

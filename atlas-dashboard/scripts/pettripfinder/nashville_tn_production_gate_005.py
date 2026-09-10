"""PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 -- the gate, opened narrowly.

Opens the redesigned production lane for ONE market and ONE candidate, and
closes it again once that candidate is live and verified.

WHY IT IS OPENED AND CLOSED RATHER THAN LEFT ON

An empty allowlist means no market can be deployed by this machinery, whatever
else is green. That is the design, and leaving the allowlist populated after a
launch converts a single launch decision into a standing one. Lexington's own
``consumed`` block says so in as many words, and this follows it.

WHAT "NARROW" MEANS HERE, EXACTLY

The gate allowlists a MARKET. It has no candidate-digest control, and the loader
reads only ``RELEASE_COORDINATOR_PRODUCTION_ENABLED`` and
``RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS``. The exact-candidate binding
is not weaker for that: ``release_coordinator.authorization_problems`` refuses
any candidate whose digest is not the one the authorization binds
(CANDIDATE_DIGEST_MISMATCH) and any bundle that is not the authorized artifact
(BUNDLE_DIGEST_MISMATCH). So the candidate digest is recorded here for AUDIT and
is not presented as a control -- writing a field nothing reads and calling it a
gate would be worse than having none. The gate's own note makes that point and
this module does not contradict it.

CLOSING DOES NOT DISABLE THE FACTORY

``--close`` empties the allowlist and returns ENABLED to NO. It does not touch
``FAST_PATH_IMPLEMENTED``, ``FAST_PATH_VALIDATED`` or anything else: the lane
stays built and proven, it simply has no market it may act on.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
MARKET_ID = "nashville-tn"
GATE = _DASH / "launch_packages" / "pettripfinder" / "release_production_gate.json"
AUTH_DIR = _DASH / "deploy" / "netlify" / "deployment_authorizations"


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh, object_pairs_hook=OrderedDict)


def _write(path, doc):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorization", required=True, help="the authorization id to open for")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--open", action="store_true")
    group.add_argument("--close", action="store_true")
    ap.add_argument("--host-deployment-id", default="")
    args = ap.parse_args(argv)

    auth = _load(AUTH_DIR / ("%s.json" % args.authorization))
    if auth["work_order"] != WORK_ORDER:
        raise SystemExit("REFUSING: %s belongs to %s" % (args.authorization, auth["work_order"]))
    if MARKET_ID not in auth["founder_authorized_markets"]:
        raise SystemExit("REFUSING: the authorization does not authorize %s" % MARKET_ID)

    gate = _load(GATE)

    if args.open:
        if gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"]:
            raise SystemExit("REFUSING: the allowlist is not empty: %s. A previous opening was "
                             "never closed." % gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"])
        gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] = "YES"
        gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] = [MARKET_ID]
        gate["open_for"] = OrderedDict((
            ("work_order", WORK_ORDER),
            ("market_id", MARKET_ID),
            ("authorization_id", args.authorization),
            ("authorized_candidate_digest", auth["bundle_sha256"]),
            ("authorized_parent_deployment_id", auth["rollback_target"]),
            ("opened_at", _now()),
            ("scope",
             "ONE market and ONE candidate. The allowlist names the market; the candidate digest "
             "above is recorded for AUDIT and is enforced by "
             "release_coordinator.authorization_problems (CANDIDATE_DIGEST_MISMATCH / "
             "BUNDLE_DIGEST_MISMATCH), not by this file."),
            ("must_be_closed_after",
             "live verification passes, or the launch is abandoned. An opening that outlives its "
             "candidate is a standing permission, which is what the empty allowlist prevents."),
        ))
        _write(GATE, gate)
        print("gate OPENED")
        print("  ENABLED         :", gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"])
        print("  ALLOWED_MARKETS :", gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"])
        print("  candidate       :", auth["bundle_sha256"])
        return 0

    # The block being replaced is the PREVIOUS launch's, and older blocks name
    # their opening by work order rather than by authorization id. Reading only
    # the newer key silently records "supersedes: null" and loses the chain.
    previous = gate.get("consumed") or {}
    supersedes = previous.get("authorization_id") or previous.get("work_order")

    opening = gate.get("open_for") or {}
    if opening.get("authorization_id") != args.authorization:
        raise SystemExit("REFUSING: the gate is open for %r, not %r"
                         % (opening.get("authorization_id"), args.authorization))
    gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] = "NO"
    gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] = []
    gate.pop("open_for", None)
    gate["consumed"] = OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("authorization_id", args.authorization),
        ("candidate_digest", auth["bundle_sha256"]),
        ("host_deployment_id", args.host_deployment_id),
        ("opened_at", opening.get("opened_at")),
        ("closed_at", _now()),
        ("why_closed",
         "the opening was candidate-specific by design. It authorised ONE market and ONE "
         "candidate; that candidate is now live and verified, so the permission has done its "
         "job. Closing it restores the empty allowlist, which is what stops a single launch "
         "decision from becoming a standing one. The lane itself is untouched: "
         "FAST_PATH_IMPLEMENTED and FAST_PATH_VALIDATED stay YES and nothing is disabled."),
        ("supersedes", supersedes),
    ))
    _write(GATE, gate)
    print("gate CLOSED")
    print("  ENABLED         :", gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"])
    print("  ALLOWED_MARKETS :", gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"])
    print("  consumed by     :", args.authorization,
          "| host deploy:", args.host_deployment_id or "(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

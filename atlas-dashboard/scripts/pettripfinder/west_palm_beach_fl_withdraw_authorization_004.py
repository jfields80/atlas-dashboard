"""PTF-WEST-PALM-BEACH-FL-PREDEPLOY-IDENTITY-CORRECTION-004 -- phase 7.

    python -m scripts.pettripfinder.west_palm_beach_fl_withdraw_authorization_004 [--write]

WHY THIS EXISTS
---------------
``ptf-auth-west-palm-beach-003-217f87eeba72`` is AUTHORIZED and UNCONSUMED, and it is bound to
bundle ``217f87ee...`` -- bytes that publish a profile titled after a management company. The
identity correction replaced those bytes, so the authorization must stop being deployable
BEFORE anything else happens.

ONE WRITE, CANONICAL AND NON-DESTRUCTIVE
-----------------------------------------
The authorization is transitioned AUTHORIZED -> SUPERSEDED through
``deployment_authorization.transition``. That is a supported edge in the module's own
``TRANSITIONS`` table and it is terminal: ``SUPERSEDED`` has no outgoing edge, and
``deployability_problems`` refuses any status outside ``DEPLOYABLE_STATUSES``. Nothing is
deleted, nothing is back-dated, and the record keeps its bundle and sitemap digests, so a later
reader can still see exactly what was authorized and when it stopped being so. It is NOT marked
DEPLOYED: no deployment happened.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
------------------------------------------
It does not move West Palm Beach's participation row back to
``SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH``, because the repository does not permit
that and this order does not license weakening the rule that stops it. The decision chain is
MONOTONE by contract: ``launch_participation.decision_problems`` refuses a block that drops a
market its predecessor authorized ("this decision drops market(s) the previous one authorized")
and separately refuses a lineage whose authorized-set sizes are not non-decreasing ("decision
lineage shrinks the authorized set"). A launch decision, once made, is evidence that it was
made; it is not a toggle.

That has a consequence worth stating plainly rather than working around: because a registration
may only ever write SOURCE_READY and refuses while the founder-authorized set has moved, a
package correction to an ALREADY FOUNDER-AUTHORIZED market cannot be re-registered narrowly.
Superseding the deployment authorization is therefore the whole of the safety this order can
deliver by itself -- and it is sufficient for safety, because nothing deploys without a
DEPLOYABLE authorization bound to the exact candidate bytes.
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

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402
from scripts.pettripfinder import launch_participation as LP       # noqa: E402

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-PREDEPLOY-IDENTITY-CORRECTION-004"
MARKET = "west-palm-beach-fl"
DECIDED_ON = "2026-09-22"
OLD_AUTHORIZATION = "ptf-auth-west-palm-beach-003-217f87eeba72"
OLD_BUNDLE = "217f87eeba72c9f94c2eaf3ce82c37af35b261e8f21abb847c0b6337216c5054"
OLD_PACKAGE = "pkg-west-palm-beach-fl-789c0187e366abe8"
NEW_PACKAGE = "pkg-west-palm-beach-fl-94d6f4115daa9b88"

WITHDRAWN_BECAUSE = (
    "%s withdrew this authorization before any deployment. It is bound to bundle %s, which "
    "publishes /pet-friendly-hotels/west-palm-beach-fl/apple-ten-hospitality-management-inc/ -- a "
    "traveler-facing profile titled after a management company. The premises is Hilton Garden Inn "
    "Boca Raton, 8201 Congress Ave, Boca Raton FL 33487, Hilton property code bctbrgi, whose own "
    "brand page states the name at tier 1; the DBPR value that won was the LICENSEE identity, "
    "carried in a record whose Business Name and Licensee Name are identical. The corrected "
    "source package is %s and it supersedes %s. This authorization is SUPERSEDED, never consumed: "
    "no deployment happened, and the record keeps its own bundle and sitemap digests so what was "
    "authorized stays legible." % (WORK_ORDER, OLD_BUNDLE[:12], NEW_PACKAGE, OLD_PACKAGE))

def withdraw(write: bool = False) -> dict:
    auth = DA.load_authorization(OLD_AUTHORIZATION)
    before_status = auth.get("authorization_status")
    if auth.get("deploy_id"):
        raise SystemExit("%s has been CONSUMED (deploy_id %s); this order refuses to touch a "
                         "deployed authorization" % (OLD_AUTHORIZATION, auth["deploy_id"]))
    if auth.get("bundle_sha256") != OLD_BUNDLE:
        raise SystemExit("%s binds bundle %r, not the bundle this correction replaces"
                         % (OLD_AUTHORIZATION, auth.get("bundle_sha256")))

    superseded = auth
    if before_status != DA.SUPERSEDED:
        superseded = DA.transition(auth, DA.SUPERSEDED, note=WITHDRAWN_BECAUSE)

    if write:
        DA.write_authorization(superseded)

    # Stale-authorization safety, stated as a measurement rather than a hope: no authorization
    # that survives may deploy the corrected bytes, and the superseded one may not deploy at all.
    reread = DA.load_authorization(OLD_AUTHORIZATION) if write else superseded
    others = [a for a in DA.list_authorizations()
              if a.get("authorization_id") != OLD_AUTHORIZATION
              and a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]

    return {
        "authorization_id": OLD_AUTHORIZATION,
        "authorization_status_before": before_status,
        "authorization_status_after": reread.get("authorization_status"),
        "consumed": bool(reread.get("deploy_id")),
        "deployable_after": reread.get("authorization_status") in DA.DEPLOYABLE_STATUSES,
        "terminal_status": not DA.TRANSITIONS.get(reread.get("authorization_status"), ()),
        "bundle_it_binds": reread.get("bundle_sha256"),
        "history_preserved": bool(reread.get("bundle_sha256") and reread.get("sitemap_sha256")),
        "other_deployable_authorizations": [a.get("authorization_id") for a in others],
        "participation_untouched": True,
        "participation_status": LP.launch_status(MARKET),
        "written": write,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    print(json.dumps(withdraw(write=ap.parse_args().write), indent=1))

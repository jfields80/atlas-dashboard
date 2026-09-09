"""PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003 -- the enablement plan.

The redesigned production lane is closed at three independent flags, and this
order does NOT open any of them. It writes the exact change a founder would
make to open the lane for LEXINGTON ALONE, reads the current value of every
flag from the committed file so the "before" side cannot drift, and states what
each flag would permit.

WHY IT IS NOT APPLIED HERE

Applying it would make Lexington deployable by the release coordinator BEFORE a
founder authorization exists, which is exactly the ordering the flags were
built to prevent. The plan is therefore a proposal: it names the file, the
field, the old value, the new value and the guard that still has to pass after
the change.

Note what the narrowing is NOT: none of these flags is a global switch. Both
allowlists are empty today, so every market -- including all eleven live ones --
is refused by the coordinator. The proposed change adds ONE market id to each
allowlist. It does not widen anything for Cincinnati, Toledo, Detroit,
Nashville, Chattanooga, Fort Wayne or any other market.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003"
MARKET_ID = "lexington-ky"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
FAST = os.path.join(PKG, "fast_release_activation.json")
GATE = os.path.join(PKG, "release_production_gate.json")
OUT = os.path.join(REPORTS, "lexington_ky_production_enablement_plan_003.json")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-digest", required=True)
    ap.add_argument("--receipt-digest", required=True)
    ap.add_argument("--package-digest", required=True)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    fast = _load(FAST)
    gate = _load(GATE)

    changes = [
        OrderedDict((
            ("file", "launch_packages/pettripfinder/fast_release_activation.json"),
            ("field", "FAST_PATH_PRODUCTION_ACTIVATION"),
            ("current", fast["FAST_PATH_PRODUCTION_ACTIVATION"]),
            ("proposed", "ENABLED"),
            ("permits", "a Regression V2 plan may replace the broad regression with a fast-lane "
                        "receipt -- but only for a market that is ALSO in pilot_allowlist, so "
                        "this field alone opens nothing"),
        )),
        OrderedDict((
            ("file", "launch_packages/pettripfinder/fast_release_activation.json"),
            ("field", "pilot_allowlist"),
            ("current", fast["pilot_allowlist"]),
            ("proposed", [MARKET_ID]),
            ("permits", "the fast path for Lexington and no other market"),
        )),
        OrderedDict((
            ("file", "launch_packages/pettripfinder/fast_release_activation.json"),
            ("field", "PRODUCTION_RELEASE_CONSUMPTION"),
            ("current", fast["PRODUCTION_RELEASE_CONSUMPTION"]),
            ("proposed", "ENABLED_FOR_PILOT_ALLOWLIST"),
            ("permits", "the production assembler and deployer to consume a validated bundle "
                        "from the persistent cache for an allowlisted market. Leaving it "
                        "DISABLED is also safe: Lexington is a market that has never been "
                        "built, so there is no cache entry to consume and the lane builds it "
                        "cold either way. The measured cost of building it cold is in this "
                        "order's performance report."),
            ("optional", True),
        )),
        OrderedDict((
            ("file", "launch_packages/pettripfinder/release_production_gate.json"),
            ("field", "RELEASE_COORDINATOR_PRODUCTION_ENABLED"),
            ("current", gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"]),
            ("proposed", "YES"),
            ("permits", "the release coordinator to make a REAL host call -- but only for a "
                        "market in RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS, and only "
                        "with a founder authorization binding the exact digests"),
        )),
        OrderedDict((
            ("file", "launch_packages/pettripfinder/release_production_gate.json"),
            ("field", "RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"),
            ("current", gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"]),
            ("proposed", [MARKET_ID]),
            ("permits", "real production activation for Lexington and no other market"),
        )),
    ]

    doc = OrderedDict((
        ("schema", "ptf-production-enablement-plan/1.0"),
        ("status", "PROPOSED_NOT_APPLIED"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("what_this_is",
         "The exact flag change that would open the redesigned production lane for Lexington "
         "alone. It is NOT applied: applying it would make Lexington deployable by the release "
         "coordinator before a founder authorization exists, which is the ordering these flags "
         "were built to prevent."),
        ("applied", False),
        ("scope", "LEXINGTON_ONLY"),
        ("global_enablement_refused",
         "no flag is set to a value that admits every market. Both allowlists are empty today, "
         "so the coordinator refuses all thirteen registered markets including the eleven that "
         "are live; the proposal adds exactly one market id to each."),
        ("current_state", OrderedDict((
            ("FAST_PATH_IMPLEMENTED", fast["FAST_PATH_IMPLEMENTED"]),
            ("FAST_PATH_VALIDATED", fast["FAST_PATH_VALIDATED"]),
            ("FAST_PATH_PRODUCTION_ACTIVATION", fast["FAST_PATH_PRODUCTION_ACTIVATION"]),
            ("PERSISTENT_CACHE_IMPLEMENTED", fast["PERSISTENT_CACHE_IMPLEMENTED"]),
            ("PERSISTENT_CACHE_VALIDATED", fast["PERSISTENT_CACHE_VALIDATED"]),
            ("PRODUCTION_RELEASE_CONSUMPTION", fast["PRODUCTION_RELEASE_CONSUMPTION"]),
            ("pilot_allowlist", fast["pilot_allowlist"]),
            ("RELEASE_COORDINATOR_PRODUCTION_ENABLED",
             gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"]),
            ("RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS",
             gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"]),
        ))),
        ("proposed_changes", changes),
        ("digests_the_activation_must_be_bound_to", OrderedDict((
            ("final_candidate_digest", args.candidate_digest),
            ("fast_lane_receipt_digest", args.receipt_digest),
            ("sealed_package_digest", args.package_digest),
        ))),
        ("guards_that_still_run_after_the_change", gate["requires_for_each_activation"]),
        ("order_of_operations", [
            "1. the founder authorizes the exact candidate digest",
            "2. the launch_participation row for lexington-ky flips to "
            "FOUNDER_AUTHORIZED_FOR_LAUNCH",
            "3. these flags are applied, narrowed to lexington-ky",
            "4. the coordinator re-reads CURRENT VERIFIED LIVE and refuses if it moved",
            "5. only then is a host call made",
        ]),
        ("nothing_enabled_by_this_order", True),
    ))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("proposed changes :", len(changes), "fields across 2 files")
    print("applied          :", doc["applied"])
    print("written          :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

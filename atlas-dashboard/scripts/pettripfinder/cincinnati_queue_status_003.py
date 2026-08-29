"""PTF-CINCINNATI-ZERO-COST-CAPTURE-003 -- fold this pass's observations into
the live queue.

    python -m scripts.pettripfinder.cincinnati_queue_status_003
    python -m scripts.pettripfinder.cincinnati_queue_status_003 --write

WHAT MOVES AND WHAT DOES NOT
-----------------------------
``final_state`` does NOT move. It is derived from the committed partition,
which is authority, and this pass wrote no authority: a row observed as a
publication candidate is not published until a founder says so, and a queue
that showed it as PUBLISHED_PET_FRIENDLY before that would be claiming an
approval nobody made.

What moves is ``review_status`` and a new ``last_observation`` block, which
record that the row WAS looked at, when, by what method, with what outcome, and
where its evidence sits. That is the thing the stale 250-row queue could not do
and the reason it sent people to re-find URLs this market already owned.

A row observed and found silent is OBSERVED_POLICY_NOT_FOUND, not NOT_STARTED:
the difference is whether the next pass should visit it again, and pretending
nobody has looked wastes exactly the attention this queue exists to direct.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

WORK_ORDER = "PTF-CINCINNATI-ZERO-COST-CAPTURE-003"
AS_OF = "2026-08-29"
REPORTS = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
           / "reports")
QUEUE = REPORTS / "cincinnati-oh_founder_review_queue.json"
RESULTS = REPORTS / "cincinnati_capture_pass3_001_results.json"

#: capture outcome -> the queue's review status and next lane.
MAP = {
    "PUBLICATION_CANDIDATE": ("OBSERVED_AWAITING_FOUNDER",
                              "FOUNDER_REVIEW_REQUIRED"),
    "VERIFIED_NO_PETS": ("OBSERVED_AWAITING_FOUNDER",
                         "FOUNDER_REVIEW_REQUIRED"),
    "POLICY_NOT_FOUND": ("OBSERVED_POLICY_NOT_FOUND",
                         "POLICY_RE_OBSERVATION_REQUIRED"),
    "ACCESS_BLOCKED": ("OBSERVED_ACCESS_BLOCKED", "HOLD_ACCESS_BLOCKED"),
    "ROUTING_REPAIR_REQUIRED": ("OBSERVED_ROUTE_INVALID",
                                "ROUTING_REPAIR_REQUIRED"),
    "IDENTITY_MISMATCH": ("OBSERVED_IDENTITY_MISMATCH", "IDENTITY_REVIEW"),
}

LANES = {
    "FOUNDER_REVIEW_REQUIRED":
        "Observed with evidence. Awaiting a founder decision; see the clean "
        "candidate files or the exception packet.",
    "ROUTING_REPAIR_REQUIRED":
        "The committed URL no longer belongs to this property. Retire the "
        "route; do not re-observe the page.",
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"),
                       object_pairs_hook=OrderedDict)
    results = {r["identity_key"]: r for r in
               json.loads(RESULTS.read_text(encoding="utf-8"))["rows"]}

    touched = 0
    for row in queue["rows"]:
        res = results.get(row["identity_key"])
        if res is None:
            continue
        status, lane = MAP[res["outcome"]]
        row["review_status"] = status
        row["capture_lane"] = lane
        row["next_action"] = LANES.get(lane, row["next_action"])
        row["last_observation"] = OrderedDict((
            ("work_order", WORK_ORDER), ("observed_at", AS_OF),
            ("method", "attended_chrome_render"),
            ("outcome", res["outcome"]), ("triage", res["triage"]),
            ("final_url", res["final_url"]), ("sha256", res.get("sha256")),
            ("provider_calls", 0), ("cost_usd", 0.0),
        ))
        touched += 1

    queue["work_order"] = WORK_ORDER
    queue["generated_at"] = AS_OF
    queue["note"] = (
        queue["note"] + " PTF-CINCINNATI-ZERO-COST-CAPTURE-003 then observed "
        "93 of these rows by attended browser at zero cost and recorded the "
        "outcome on each. final_state is deliberately UNCHANGED: this pass "
        "wrote no authority, so no row became published or refused by being "
        "looked at.")
    queue["review_status_counts"] = OrderedDict(
        sorted(Counter(r["review_status"] for r in queue["rows"]).items()))
    queue["lane_counts"] = OrderedDict(
        sorted(Counter(r["capture_lane"] for r in queue["rows"]).items()))
    for lane, why in LANES.items():
        queue["lane_meanings"][lane] = why
    queue["lane_meanings"] = OrderedDict(sorted(queue["lane_meanings"].items()))

    print("rows updated : %d" % touched)
    print("review_status: %s" % dict(queue["review_status_counts"]))
    print("lanes        : %s" % dict(queue["lane_counts"]))

    if args.write:
        QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
        print("WROTE %s" % QUEUE.name)
    else:
        print("(check only -- pass --write)")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())

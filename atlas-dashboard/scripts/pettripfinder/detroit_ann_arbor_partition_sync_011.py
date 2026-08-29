# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011 -- partition sync.

Moves the newly decided identities to their terminal states.

THE PARTITION DOES NOT DECIDE ANYTHING. Its own note says so: "terminal states
are read from the authority that owns them -- the policy package and the
exclusion shard -- never re-decided here." This run applies that rule to the
rows authority just answered, and to nothing else.

So it is deliberately NOT a rebuild. Every item whose identity did not gain
authority in this order keeps the state it had, including the open ones; the
only rows that move are those the policy package or the exclusion shard now
carries. A row that reaches a terminal state also stops carrying a next action,
because there is no longer an action to take.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                 # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def run() -> None:
    partition = load(PARTITION_PATH)
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}

    moved = []
    for item in partition["items"]:
        key = item["identity_key"]
        if key in published:
            target = enums.PUBLISHED_PET_FRIENDLY
        elif key in excluded:
            target = enums.VERIFIED_NO_PETS
        else:
            continue
        if item["final_state"] == target:
            continue
        moved.append(OrderedDict([
            ("identity_key", key),
            ("was", item["final_state"]),
            ("now", target),
        ]))
        item["final_state"] = target
        item["resolved"] = True
        item["next_action"] = ""
        item["next_action_source"] = WORK_ORDER
        item["determined_by"] = WORK_ORDER
        item["updated_at"] = AS_OF

    counts = Counter(item["final_state"] for item in partition["items"])
    partition["final_state_counts"] = OrderedDict(sorted(counts.items()))
    partition["note"] = (
        "%s moved %d identities to a terminal state after the founder approved "
        "the Firecrawl 008/009/010 candidates. The partition does not decide "
        "anything: terminal states are read from the authority that owns them "
        "-- the policy package and the exclusion shard. No other item changed, "
        "and every open state was left exactly as it was. %s"
        % (WORK_ORDER, len(moved), partition.get("note") or ""))
    if WORK_ORDER not in partition.get("source_authorities", []):
        partition["source_authorities"] = list(
            partition.get("source_authorities", [])) + [WORK_ORDER]
    partition["as_of"] = AS_OF
    write_lf(PARTITION_PATH, partition)

    print("partition items moved to a terminal state:", len(moved))
    print("  ->", dict(Counter(row["now"] for row in moved)))
    print("final state counts:", dict(partition["final_state_counts"]))


if __name__ == "__main__":
    run()

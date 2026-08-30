# -*- coding: utf-8 -*-
"""Founder-review queue sync after the order-020 rulings.

The queue is the UNRESOLVED SET. Two identities the founder just published must
leave it; a resolved row left in the queue asks for review of work already done.

SURVIVORS ARE NOT RENUMBERED AND NOT REHASHED. Rows are matched by identity and
keep their row_number, batch and row_sha256 exactly as they were: queue row
numbers are not stable across a rebuild, and renumbering would invalidate every
hash for nothing.

ONE SENTENCE IS PREPENDED TO THE NOTE, NOT A REPEAT OF AN EXISTING ONE. The
committed note already carries the same sentence several times over from
earlier orders that each appended their own copy; this run adds its own once
and leaves that history alone rather than compounding it.
"""
from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020-FOUNDER-RULINGS"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
QUEUE_PATH = (LP / "markets" / "reports"
              / ("%s_founder_review_queue.json" % MARKET))


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run() -> None:
    queue = load(QUEUE_PATH)
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    resolved = published | excluded

    before = len(queue["items"])
    removed = [row for row in queue["items"]
               if row["identity_key"] in resolved]
    queue["items"] = [row for row in queue["items"]
                      if row["identity_key"] not in resolved]
    queue["count"] = len(queue["items"])
    queue["work_order"] = WORK_ORDER
    queue["note"] = (
        "%s removed %d identities the founder resolved in the order-020 "
        "rulings. The queue is the UNRESOLVED SET. Survivors keep their "
        "row_number, batch and row_sha256 unchanged and are matched by "
        "identity, because queue row numbers are not stable across a "
        "rebuild. %s" % (WORK_ORDER, len(removed), queue.get("note") or ""))

    partition = load(LP / "detroit_ann_arbor_final_partition_001.json")
    unresolved = {item["identity_key"] for item in partition["items"]
                  if not item["resolved"]}
    queued = {row["identity_key"] for row in queue["items"]}
    if queued != unresolved:
        raise SystemExit(
            "STOP: the queue is not the unresolved set -- only in queue %s, "
            "only unresolved %s"
            % (sorted(queued - unresolved)[:3],
               sorted(unresolved - queued)[:3]))

    QUEUE_PATH.write_text(
        json.dumps(queue, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")

    print("queue %d -> %d (removed %d)" % (before, len(queue["items"]),
                                           len(removed)))
    for row in removed:
        print("   left the queue: %s" % row["canonical_name"])
    print("queue == unresolved set:", queued == unresolved)


if __name__ == "__main__":
    run()

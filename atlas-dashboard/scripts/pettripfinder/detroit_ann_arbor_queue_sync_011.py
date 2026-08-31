# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011 -- queue sync.

Drops the identities this order resolved from the founder review queue.

The queue is the UNRESOLVED SET, and its own tests say so: the set of queued
identity keys must equal the set of partition items that are not resolved. Once
authority answers 53 of them, leaving them queued asks a founder to review work
that is already done.

NOTHING IS RENUMBERED. ``row_sha256`` is computed over the whole item including
``row_number`` and ``batch``, so renumbering the survivors would invalidate
every hash to no purpose -- and this corpus has already learned that queue row
numbers are not stable across a rebuild and that rows must be re-matched by
identity instead. Survivors keep their number, their batch and their hash
exactly; only the resolved rows leave.
"""
from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
QUEUE_PATH = (LP / "markets" / "reports"
              / ("%s_founder_review_queue.json" % MARKET))
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def run() -> None:
    queue = load(QUEUE_PATH)
    partition = load(PARTITION_PATH)
    unresolved = {item["identity_key"] for item in partition["items"]
                  if not item["resolved"]}

    before = len(queue["items"])
    kept = [item for item in queue["items"]
            if item["identity_key"] in unresolved]
    dropped = [item["identity_key"] for item in queue["items"]
               if item["identity_key"] not in unresolved]

    missing = unresolved - {item["identity_key"] for item in kept}
    if missing:
        raise SystemExit("STOP: %d unresolved identities are not in the queue: "
                         "%s" % (len(missing), sorted(missing)[:5]))

    queue["items"] = kept
    queue["count"] = len(kept)
    queue["work_order"] = WORK_ORDER
    queue["as_of"] = AS_OF
    queue["note"] = (
        "%s removed %d identities the founder resolved from the Firecrawl "
        "008/009/010 candidates. The queue is the UNRESOLVED SET; a resolved "
        "row left in it asks for review of work already done. Survivors keep "
        "their row_number, batch and row_sha256 unchanged -- renumbering would "
        "invalidate every hash for nothing, and queue row numbers are not "
        "stable across a rebuild, so rows are matched by identity. %s"
        % (WORK_ORDER, len(dropped), queue.get("note") or ""))
    write_lf(QUEUE_PATH, queue)

    print("queue: %d -> %d (dropped %d resolved)"
          % (before, len(kept), len(dropped)))
    print("matches the partition's unresolved set:",
          {item["identity_key"] for item in kept} == unresolved)


if __name__ == "__main__":
    run()

"""PTF-CENSUS-PARTITION-NORMALIZATION-001 -- routing authority, canonicalised.

Two changes, both additive to the routing semantics that already work:

  * every record gains the canonical ``identity_key`` and an explicit
    ``category``, so membership against a market census is a set operation
    rather than a string comparison between two normalisers;
  * the two Cleveland records that bind accommodation routes to identities
    Cleveland's census does not contain are RETIRED.

On those two
------------
``Eastland Inn Restaurant`` and ``The Welshfield Inn`` are cross-category
residue: a restaurant and an inn that the Cleveland market factory deliberately
left out of its 188-identity hotel census. The invariant they violate is fixed
by retiring the invalid accommodation routes, NOT by expanding the census to
190 to house them -- contaminating a hotel census with non-hotels to satisfy a
membership rule would be the rule defeating its own purpose.

Nothing is deleted. A retired record keeps its URL, its binding sources and its
identity signals, and gains the date and reason it was retired, so the history
of how it was bound survives.

What this does NOT do
---------------------
No URL is re-researched, no held route is resolved, and no route is created.
Retirement-on-publication is checked rather than applied: no published identity
currently holds an active route, so the invariant already holds and Phase C
enforces it with a gate instead of a rewrite.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.census_partition_builder import PACKAGE_DIR, WORK_ORDER
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import (
    IDENTITY_KEY_CONTRACT, ptf_identity_key,
)

ROUTING_PATH = PACKAGE_DIR / "identity_routing.json"
RETIRED_AT = "2026-08-14"

#: The two Cleveland cross-category routes, named explicitly rather than
#: derived, so retiring a record is always a reviewed decision and never a
#: side effect of a set difference.
CROSS_CATEGORY_RETIREMENTS: Dict[str, str] = {
    "eastland inn restaurant":
        "Cross-category residue: a restaurant, deliberately excluded from the "
        "Cleveland hotel census. The accommodation route is retired rather "
        "than the census expanded to hold a non-hotel.",
    "the welshfield inn":
        "Cross-category residue: an inn that the Cleveland market factory did "
        "not admit to its 188-identity hotel census. The accommodation route "
        "is retired rather than the census expanded to hold it.",
}


def upgrade(document: Mapping) -> Tuple[Mapping, List[str]]:
    notes: List[str] = []
    routes: List[Mapping] = []
    for route in document["routes"]:
        name = route["hotel_ref"]["canonical_name"]
        key = ptf_identity_key(name)

        ref = OrderedDict(route["hotel_ref"])
        # Placed first so a reader sees the join key before the two display
        # names it is derived from.
        ref = OrderedDict([("identity_key", key)]
                          + [(k, v) for k, v in ref.items() if k != "identity_key"])

        updated = OrderedDict(route)
        updated["hotel_ref"] = ref
        updated["category"] = route.get("category", enums.CATEGORY_ACCOMMODATION)

        reason = CROSS_CATEGORY_RETIREMENTS.get(key)
        if reason and route.get("status") != enums.ROUTING_RETIRED:
            updated["status"] = enums.ROUTING_RETIRED
            updated["retired_at"] = RETIRED_AT
            updated["retired_reason"] = reason
            updated["retired_by"] = WORK_ORDER
            notes.append("retired: %s" % name)
        routes.append(updated)

    out = OrderedDict(document)
    out["identity_key_contract"] = IDENTITY_KEY_CONTRACT
    out["count"] = len(routes)
    out["routes"] = routes
    return out, notes


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    document = json.loads(ROUTING_PATH.read_text(encoding="utf-8-sig"))
    upgraded, notes = upgrade(document)

    active = [r for r in upgraded["routes"] if r["status"] != enums.ROUTING_RETIRED]
    retired = [r for r in upgraded["routes"] if r["status"] == enums.ROUTING_RETIRED]
    out = sys.stdout.write
    out("routes=%d active=%d retired=%d\n"
        % (len(upgraded["routes"]), len(active), len(retired)))
    for note in notes:
        out("    %s\n" % note)

    if args.write:
        text = json.dumps(upgraded, indent=2, ensure_ascii=False) + "\n"
        ROUTING_PATH.write_text(text, encoding="utf-8", newline="\n")
        out("wrote %s\n" % ROUTING_PATH.name)
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())

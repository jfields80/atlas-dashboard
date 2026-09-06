"""PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003 -- re-derive the final partition.

The partition is a VIEW over the committed authorities, so it is re-derived here
rather than hand-edited: a row is PUBLISHED_PET_FRIENDLY because the policy package
holds it, VERIFIED_NO_PETS or OUT_OF_CURRENT_CATEGORY because the exclusion shard
holds it, and otherwise it keeps the blocked state the previous derivation gave it.
Nothing invents a state, and no count is typed by hand.

The document is rebuilt through ``census_partition_builder.partition_document`` so
its counts, its terminal/next-action shape and its state-meaning block stay
canonical. It is written back to the SAME path the readers already resolve,
``cincinnati_final_partition_001.json``, because a new versioned filename would be
a partition no consumer looks at.

A terminal state with no authority behind it is a contradiction and stops the run:
a row cannot be published or refused because a previous document said so, only
because an authority holds it now.

Read-only with respect to the census. This order promoted policy, not identity, and
the census still holds 257 rows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.census_partition_builder import (      # noqa: E402
    partition_document, partition_item)
from scripts.pettripfinder.contracts import enums                 # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003"
MARKET = "cincinnati-oh"
AS_OF = "2026-09-05"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
PARTITION_PATH = PACKAGE / "cincinnati_final_partition_001.json"

NOTE = (
    "Final states derive from committed authority: PUBLISHED_PET_FRIENDLY from the "
    "market's policy package, VERIFIED_NO_PETS and OUT_OF_CURRENT_CATEGORY from its "
    "exclusion shard, and every other row keeps the blocked state its previous "
    "derivation gave it. %s promoted the clean inventory left pending by "
    "PTF-CINCINNATI-PARALLEL-REVALIDATION-002 -- 31 pet-friendly and 27 "
    "verified-no-pets -- and moved no census row. The Cincinnatian Hotel was held "
    "out of the no-pets cohort by founder decision, because its only visible "
    "evidence is a service-animal sentence beside a structured flag and this market "
    "has already ruled that a bare structured flag is not a refusal." % WORK_ORDER)


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rebuild(write: bool = False) -> Dict:
    previous = _load(PARTITION_PATH)
    policy = _load(PACKAGE / ("hotel_policy_facts_%s.json" % MARKET))
    shard = _load(PACKAGE / "markets" / "authority" / MARKET / "hotel_exclusions.json")

    published = {h["identity_key"] for h in policy["hotels"]}
    excluded: Dict[str, str] = {}
    for record in shard["exclusions"]:
        excluded[record["normalized_name"]] = record["exclusion_state"]

    overlap = published & set(excluded)
    if overlap:
        raise SystemExit("%s: %d identity(ies) are both published and excluded: %s"
                         % (WORK_ORDER, len(overlap), sorted(overlap)))

    items, moved = [], []
    for row in previous["items"]:
        key = row["identity_key"]
        if key in published:
            state = enums.PUBLISHED_PET_FRIENDLY
        elif key in excluded:
            state = excluded[key]
        else:
            state = row["final_state"]
            if state in enums.TERMINAL_STATES:
                raise SystemExit(
                    "%s: %r is terminal (%s) but no authority holds it"
                    % (WORK_ORDER, key, state))
        if state != row["final_state"]:
            moved.append({"identity_key": key, "from": row["final_state"],
                          "to": state})
        items.append(partition_item(
            identity_key=key, canonical_name=row["canonical_name"],
            slug=row["slug"], city=row["city"], state=row["state"],
            postal_code=row["postal_code"], final_state=state,
            next_action_source=row.get("next_action_source") or "",
            determined_by=(row.get("determined_by")
                           or previous.get("work_order") or ""),
            updated_at=(AS_OF if state != row["final_state"]
                        else row.get("updated_at", "")),
            official_url=row.get("official_url") or "",
            state_override_reason=row.get("state_override_reason") or ""))

    document = partition_document(
        MARKET, items, as_of=AS_OF, note=NOTE,
        source_authorities=[
            "launch_packages/pettripfinder/hotel_policy_facts_cincinnati-oh.json",
            "launch_packages/pettripfinder/markets/authority/cincinnati-oh/hotel_exclusions.json",
        ])
    document["work_order"] = WORK_ORDER

    counts = document["final_state_counts"]
    pf = counts.get(enums.PUBLISHED_PET_FRIENDLY, 0)
    no_pets = counts.get(enums.VERIFIED_NO_PETS, 0)
    ooc = counts.get(enums.OUT_OF_CURRENT_CATEGORY, 0)
    resolved = sum(1 for i in document["items"] if i["resolved"])
    unresolved = document["count"] - resolved
    if resolved != pf + no_pets + ooc:
        raise SystemExit("%s: resolved %d != %d + %d + %d"
                         % (WORK_ORDER, resolved, pf, no_pets, ooc))
    if document["count"] != previous["count"]:
        raise SystemExit("%s: the census moved, %d -> %d, and this order may not "
                         "move it" % (WORK_ORDER, previous["count"],
                                      document["count"]))

    if write:
        # indent=1 is the indent this document was committed with. Changing it
        # would reformat every line to record a 58-row state change.
        text = json.dumps(document, indent=1, ensure_ascii=False) + "\n"
        PARTITION_PATH.write_text(text, encoding="utf-8", newline="\n")

    return {"work_order": WORK_ORDER, "written": write, "census": document["count"],
            "published_pet_friendly": pf, "verified_no_pets": no_pets,
            "out_of_current_category": ooc, "resolved": resolved,
            "unresolved": unresolved, "rows_moved": len(moved), "moved": moved}


if __name__ == "__main__":
    result = rebuild(write="--write" in sys.argv)
    summary = {k: result[k] for k in (
        "census", "published_pet_friendly", "verified_no_pets",
        "out_of_current_category", "resolved", "unresolved", "rows_moved")}
    print(json.dumps(summary, indent=1))

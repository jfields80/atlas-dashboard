# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 12 -- rebuild Pittsburgh's authority.

    python -m scripts.pettripfinder.pittsburgh_rebuild_004 --write

Runs after the signed application. Rebuilds the two artifacts that are DERIVED
from authority rather than authored beside it:

  seed shard   the public inventory. One row per published identity, keyed by
               the CENSUS canonical name, because ``site_data`` joins display
               rows to policy records on ``normalize_name`` and fails closed
               otherwise -- the page's own name is a rebrand or a regional
               name often enough that using it silently unpublishes the row.

  partition    the market's identity ledger. Rebuilt WHOLE, never patched: a
               renamed or reconciled identity patched in place would sit in the
               partition twice, and the partition contract requires its key set
               to equal the census's exactly.

STATE PRECEDENCE, AND WHY UNRESOLVED ROWS KEEP THEIR OWN REASON
-----------------------------------------------------------------
Published beats excluded beats a prior category exit beats whatever the row
last said. An unresolved row keeps its committed ``final_state`` and its
``next_action`` -- Pittsburgh's 38 AWAITING_IDENTITY_RESOLUTION rows are
waiting on identity work this order does not do, and flattening them to a
generic "awaiting policy" would erase what they are actually waiting for.

``determined_by`` moves to this work order only where this order actually moved
the state. A row it did not touch keeps the order that decided it.

The policy package is NOT rebuilt here. It is authored by the application from
founder signatures and migrated by Phase 5; regenerating it from a projection
would discard the approvals it carries.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA               # noqa: E402
from scripts.pettripfinder.contracts import partition as PARTITION_CONTRACT  # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (       # noqa: E402
    AS_OF, CENSUS, MARKET_ID, PACKAGE, PACKAGE_DIR, WORK_ORDER, _load, _write)

PARTITION = PACKAGE_DIR / "pittsburgh_final_partition_001.json"
QUEUE = PACKAGE_DIR / "markets" / "reports" / ("%s_founder_review_queue.json" % MARKET_ID)
SEED_COLUMNS = MA.SEED_COLUMNS
RESOLVED_STATES = ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
                   "OUT_OF_CURRENT_CATEGORY")


class RebuildError(RuntimeError):
    pass


def _seed_row(record: Dict, census_row: Dict) -> Dict:
    return OrderedDict((
        ("name", census_row["canonical_name"]),
        ("category", "pet-friendly-hotels"),
        ("address", census_row.get("address", "")),
        ("city", census_row.get("city", "")),
        ("state", census_row.get("state", "")),
        ("postal_code", census_row.get("postal_code", "")),
        ("phone", census_row.get("phone", "")),
        ("website_url", record["source_url"]),
        ("source_url", record["source_url"]),
        ("source_type", "OFFICIAL_PROPERTY"),
        ("observed_at", record["verified_at"]),
        ("rating", ""),
        ("amenities", ""),
        ("pet_policy", record["evidence_quote"]),
        ("canonical", "true"),
        ("market_id", MARKET_ID),
    ))


def rebuild_seed(package: Dict, census: Dict) -> Tuple[List[Dict], int]:
    existing = MA.load_market_seed_rows(MARKET_ID)
    have = {row["name"] for row in existing}
    rows = [OrderedDict((c, row.get(c, "")) for c in SEED_COLUMNS)
            for row in existing]
    added = 0
    for record in package["hotels"]:
        key = record["identity_key"]
        census_row = census.get(key)
        if census_row is None:
            raise RebuildError("%s is published but not in the census" % key)
        if census_row["canonical_name"] in have or record["name"] in have:
            continue
        if not str(census_row.get("address") or "").strip():
            raise RebuildError("%s has no street address; the importer refuses "
                               "an addressless seed row" % key)
        rows.append(_seed_row(record, census_row))
        added += 1
    return rows, added


def rebuild_partition(package: Dict, census: Dict, exclusions, routes
                      ) -> Tuple[Dict, Counter]:
    published = {h["identity_key"]: h for h in package["hotels"]}
    excluded = {e["normalized_name"]: e for e in exclusions}
    routed = {r["hotel_ref"]["identity_key"]: r for r in routes}
    prior = {i["identity_key"]: i for i in _load(PARTITION)["items"]}

    items = []
    for key, row in sorted(census.items()):
        was = prior.get(key) or prior.get(row.get("prior_identity_key") or "")
        if key in published:
            state, resolved = "PUBLISHED_PET_FRIENDLY", True
        elif key in excluded:
            state, resolved = excluded[key]["exclusion_state"], True
        elif was and was["final_state"] == "OUT_OF_CURRENT_CATEGORY":
            state, resolved = "OUT_OF_CURRENT_CATEGORY", True
        elif was and not was["resolved"]:
            state, resolved = was["final_state"], False
        else:
            state, resolved = "AWAITING_POLICY_OBSERVATION", False

        moved = (key in published or key in excluded) and (
            not was or was["final_state"] != state)
        official = (published[key]["source_url"] if key in published
                    else excluded[key]["official_url"] if key in excluded
                    else (routed.get(key) or {}).get(
                        "official_property_url",
                        row.get("official_url") or (was or {}).get("official_url", "")))
        items.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name", "")),
            ("slug", row.get("slug", key.replace(" ", "-"))),
            ("city", row.get("city", "")),
            ("state", row.get("state", "")),
            ("postal_code", row.get("postal_code", "")),
            ("final_state", state),
            ("resolved", resolved),
            ("next_action", "" if resolved else (was or {}).get("next_action", "")),
            ("next_action_source", "" if resolved
             else (was or {}).get("next_action_source", "")),
            ("determined_by", WORK_ORDER if moved
             else (was or {}).get("determined_by", WORK_ORDER)),
            ("updated_at", AS_OF if (was or {}).get("final_state") != state
             else (was or {}).get("updated_at", AS_OF)),
            ("official_url", official),
            ("state_override_reason", "" if resolved
             else (was or {}).get("state_override_reason", "")),
        )))

    counts = Counter(i["final_state"] for i in items)
    doc = _load(PARTITION)
    doc["work_order"] = WORK_ORDER
    doc["as_of"] = AS_OF
    doc["count"] = len(items)
    doc["final_state_counts"] = OrderedDict(sorted(counts.items()))
    doc["items"] = items
    return doc, counts


def rebuild_queue(partition_doc: Dict, census: Dict) -> Dict:
    """The founder review queue IS the unresolved set, rebuilt whole.

    Row numbers are NOT stable across a rebuild (PTF-PITTSBURGH-REVALIDATION-
    001), so nothing carries over by position: every field is re-derived, and
    the prior queue is consulted only by identity_key, for the corridor and the
    requested-evidence wording it recorded.
    """
    prior = {row["identity_key"]: row for row in _load(QUEUE)["items"]}
    items = []
    for item in partition_doc["items"]:
        if item["resolved"]:
            continue
        key = item["identity_key"]
        was = prior.get(key, {})
        row = census.get(key, {})
        entry = OrderedDict((
            ("row_number", len(items) + 1),
            ("identity_key", key),
            ("hotel_id", key),
            ("canonical_name", item["canonical_name"]),
            ("address", row.get("address", "")),
            ("phone", row.get("phone", "")),
            ("official_candidate_url", item["official_url"]),
            ("corridor", row.get("corridor") or was.get("corridor", "")),
            ("current_classification", item["final_state"]),
            ("blocking_reason", item["final_state"]),
            ("requested_evidence",
             "property-level official URL and a citable pet-policy artifact"
             if not item["official_url"]
             else "citable pet-policy artifact from the property's own page"),
            ("next_action", item["next_action"]),
            ("batch", "batch-%03d" % ((len(items) // 10) + 1)),
            ("review_status", "NOT_STARTED"),
        ))
        entry["row_sha256"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True, ensure_ascii=False)
            .encode("utf-8")).hexdigest()
        items.append(entry)

    doc = _load(QUEUE)
    doc["work_order"] = WORK_ORDER
    doc["as_of"] = AS_OF
    doc["count"] = len(items)
    doc["items"] = items
    return doc


def run(write: bool) -> int:
    package = _load(PACKAGE)
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    exclusions = MA.load_market_exclusions_document(MARKET_ID)["exclusions"]
    routes = MA.load_market_routing_document(MARKET_ID)["routes"]

    rows, added = rebuild_seed(package, census)
    doc, counts = rebuild_partition(package, census, exclusions, routes)
    queue = rebuild_queue(doc, census)

    issues = PARTITION_CONTRACT.validate(doc)
    if issues:
        raise RebuildError("partition does not validate: %s" % list(issues)[:5])
    mismatch = PARTITION_CONTRACT.reconcile(set(census), doc)
    problems = PARTITION_CONTRACT.reconciliation_issues(mismatch)
    if problems:
        raise RebuildError("partition does not reconcile with the census: %s"
                           % list(problems)[:5])
    if len(rows) != len(package["hotels"]):
        raise RebuildError("seed rows (%d) and published records (%d) disagree"
                           % (len(rows), len(package["hotels"])))

    print("published records : %d" % len(package["hotels"]))
    print("seed rows         : %d (+%d)" % (len(rows), added))
    print("partition items   : %d" % len(doc["items"]))
    for state, n in sorted(counts.items()):
        print("   %-32s %d" % (state, n))
    resolved = sum(n for s, n in counts.items() if s in RESOLVED_STATES)
    print("resolved          : %d of %d" % (resolved, len(doc["items"])))
    unresolved = [i for i in doc["items"] if not i["resolved"]]
    if len(queue["items"]) != len(unresolved):
        raise RebuildError("the queue (%d) is not the unresolved set (%d)"
                           % (len(queue["items"]), len(unresolved)))
    if {q["identity_key"] for q in queue["items"]} != {i["identity_key"] for i in unresolved}:
        raise RebuildError("the queue and the unresolved set name different identities")
    print("review queue      : %d (== unresolved)" % len(queue["items"]))
    print("partition issues  : 0")
    if not write:
        print("(check only -- pass --write)")
        return 0

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(SEED_COLUMNS),
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    MA.seed_shard_path(MARKET_ID).write_text(buffer.getvalue(),
                                             encoding="utf-8", newline="")
    print("WROTE seed shard (%d rows)" % len(rows))
    PARTITION.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    print("WROTE %s (%d items)" % (PARTITION.name, len(doc["items"])))
    _write(QUEUE, queue)
    print("WROTE %s (%d items)" % (QUEUE.name, len(queue["items"])))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except RebuildError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

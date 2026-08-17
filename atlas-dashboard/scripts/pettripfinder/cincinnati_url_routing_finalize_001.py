"""PTF-CINCINNATI-URL-ROUTING-RECOVERY-001C -- finalize the 223-row queue.

Once ``cincinnati_url_routing_recovery_001_progress.json`` shows
adjudicated == 223 and remaining == 0, this module is the one-shot pipeline
that turns that checkpoint into durable outputs:

1. the final per-row results file (``..._results.json``)
2. routing authority (``identity_routing.json``), additive, via the
   canonical validator in ``identity_routing.py``
3. the Cincinnati partition, mechanically re-derived (no hand edits)
4. the strict capture-ready queue, with an EVIDENCE_READY/ROUTING_READY
   split
5. a corridor-readiness before/after report

Routing-only rules preserved from the parent work orders: no policy field is
ever written here (the membrane in identity_routing.py enforces that), and a
ROUTING_UNRESOLVED or no-URL row is never silently dropped -- it stays in
AWAITING_OFFICIAL_URL and is carried forward as a census-review candidate
where the evidence names one.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.identity_routing import (          # noqa: E402
    ROUTING_CONFIRMED,
    ROUTING_PATH,
    validate_authority,
)

MARKET_ID = "cincinnati-oh"
WORK_ORDER = "PTF-CINCINNATI-URL-ROUTING-RECOVERY-001C"
AS_OF = "2026-08-17"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
PROGRESS_PATH = REPORTS / "cincinnati_url_routing_recovery_001_progress.json"
RESULTS_PATH = REPORTS / "cincinnati_url_routing_recovery_001_results.json"
CENSUS_PATH = PKG / "identity_census" / "cincinnati-oh.json"
PARTITION_PATH = PKG / "cincinnati_final_partition_001.json"
MARKET_CONFIG_PATH = PKG / "markets" / "cincinnati-oh.json"
CAPTURE_QUEUE_PATH = REPORTS / "cincinnati_capture_ready_queue_002.json"
CORRIDOR_REPORT_PATH = REPORTS / "cincinnati_corridor_readiness_001c.json"

#: Brands whose property pages are client-rendered SPAs or sit behind a WAF
#: that a static fetch cannot pass (per the 001A/001B/001C session memory).
#: A routed identity in one of these lanes needs an attended browser session
#: to actually observe its pet-policy content -- the URL is real, the
#: content is not statically reachable.
ATTENDED_REQUIRED_LANES = frozenset({"choice", "marriott", "hyatt", "ihg"})

NO_ROUTE_VERDICTS = frozenset({"ROUTING_UNRESOLVED"})
#: PROPERTY_CLOSED_OR_CONVERTED rows with a non-empty final_url (the ESA ->
#: Studio 6 case: the OLD identity converted, but the CURRENT property page
#: is real and verified) still get a route. Only a verdict with no URL at
#: all is excluded here.
CENSUS_REVIEW_VERDICTS = frozenset({
    "PROPERTY_CLOSED_OR_CONVERTED", "PROPERTY_CONVERTED_OR_REBRANDED",
})

PRIORITY_CORRIDORS = (
    "cincinnati-oh__erlanger-florence-airport",
    "cincinnati-oh__downtown-cincinnati",
    "cincinnati-oh__blue-ash-sharonville",
    "cincinnati-oh__mason-deerfield",
    "cincinnati-oh__west-chester-liberty-township",
    "cincinnati-oh__covington-newport",
    "cincinnati-oh__springdale-forest-park",
    "cincinnati-oh__middletown-monroe",
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")


def build_results(progress: dict, census_by_key: dict) -> dict:
    rows = []
    for row in progress["adjudicated"]:
        has_url = bool(row["final_url"])
        excluded_reason = None
        if not has_url:
            excluded_reason = "no verified URL (%s)" % row["verdict"]
        rows.append({
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "brand_lane": row["brand_lane"],
            "corridor": row["corridor"],
            "verdict": row["verdict"],
            "final_url": row["final_url"],
            "property_code": row["property_code"],
            "page_street": row["page_street"],
            "page_postal_code": row["page_postal_code"],
            "page_city": row["page_city"],
            "page_state": row["page_state"],
            "page_phone": row["page_phone"],
            "binding_signals": row["binding_signals"],
            "source_relationship": row["source_relationship"],
            "included_in_routing_authority": has_url,
            "excluded_reason": excluded_reason,
            "census_review_candidate": row["verdict"] in CENSUS_REVIEW_VERDICTS,
            "note": row["note"],
        })
    rows.sort(key=lambda r: r["identity_key"])
    included = sum(1 for r in rows if r["included_in_routing_authority"])
    return {
        "schema": "ptf-market-routing-results/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET_ID,
        "as_of": AS_OF,
        "note": ("Final adjudication of all 223 PTF-CINCINNATI-URL-ROUTING-RECOVERY-001 "
                 "targets. This file is a report, not authority -- routing authority "
                 "lives in identity_routing.json."),
        "total": len(rows),
        "included_in_routing_authority": included,
        "excluded_no_url": len(rows) - included,
        "census_review_candidates": sum(1 for r in rows if r["census_review_candidate"]),
        "rows": rows,
    }


def build_routing_records(results: dict, census_by_key: dict) -> list:
    records = []
    for row in results["rows"]:
        if not row["included_in_routing_authority"]:
            continue
        census_row = census_by_key[row["identity_key"]]
        binding_method = "PAGE_RENDERED" if row["verdict"].startswith("EXACT") \
            and row["source_relationship"] == "EXACT_PROPERTY_FIRST_PARTY" \
            else "BRAND_INDEX_BINDING"
        signals = ["binding:%s" % s for s in row["binding_signals"]]
        context = {"address": census_row["address"], "city": census_row["city"],
                   "state": census_row["state"], "postal_code": census_row["postal_code"]}
        if census_row.get("phone"):
            context["phone"] = census_row["phone"]
        record = {
            "routing_id": "route-%s-%s" % (MARKET_ID, row["identity_key"].replace(" ", "-")),
            "schema_version": "1.0.0",
            "hotel_ref": {
                "market_id": MARKET_ID,
                "canonical_name": row["canonical_name"],
                "normalized_name": row["identity_key"],
                "identity_key": row["identity_key"],
            },
            "market_id": MARKET_ID,
            "official_property_url": row["final_url"],
            "official_domain": _registrable_domain(row["final_url"]),
            "property_code": row["property_code"] or "",
            "brand": row["brand_lane"].upper(),
            "binding_method": binding_method,
            "binding_sources": [row["source_relationship"] or "WEB_SEARCH_CORROBORATION"],
            "identity_signals_matched": signals,
            "identity_context": context,
            "observed_at": AS_OF,
            "verified_at": AS_OF,
            "status": ROUTING_CONFIRMED,
            "notes": row["note"] + (
                " [CENSUS_REVIEW_CANDIDATE -- routing points at the CURRENT "
                "property; identity/naming change is a founder decision, not "
                "made here.]" if row["census_review_candidate"] else ""),
            "category": "accommodation",
        }
        records.append(record)
    return records


def _registrable_domain(url: str) -> str:
    from urllib.parse import urlsplit
    host = (urlsplit(url).hostname or "").lower()
    labels = [l for l in host.split(".") if l]
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def rebuild_partition(partition: dict, results: dict) -> dict:
    by_key = {row["identity_key"]: row for row in results["rows"]}
    items = []
    for item in partition["items"]:
        row = by_key.get(item["identity_key"])
        if row is None or item["final_state"] != "AWAITING_OFFICIAL_URL":
            items.append(item)
            continue
        new_item = dict(item)
        if row["included_in_routing_authority"]:
            new_item["final_state"] = "AWAITING_POLICY_OBSERVATION"
            new_item["resolved"] = False
            new_item["official_url"] = row["final_url"]
            new_item["next_action"] = ("Observe pet policy content on the routed page "
                                       "(attended capture required)" if row["brand_lane"]
                                       in ATTENDED_REQUIRED_LANES else
                                       "Observe pet policy content on the routed page.")
            new_item["next_action_source"] = "%s routing pass" % WORK_ORDER
            new_item["determined_by"] = WORK_ORDER
            new_item["updated_at"] = AS_OF
            if row["census_review_candidate"]:
                new_item["state_override_reason"] = (
                    "CENSUS_REVIEW_CANDIDATE: %s" % row["verdict"])
        else:
            new_item["state_override_reason"] = "ROUTING_UNRESOLVED this pass: " + \
                (row["note"][:200] if row["note"] else "")
            new_item["updated_at"] = AS_OF
        items.append(new_item)
    new_partition = dict(partition)
    new_partition["items"] = items
    new_partition["work_order"] = WORK_ORDER
    new_partition["as_of"] = AS_OF
    new_partition["count"] = len(items)
    new_partition["final_state_counts"] = dict(sorted(
        collections.Counter(i["final_state"] for i in items).items()))
    return new_partition


def build_capture_queue(results: dict, census_by_key: dict, partition: dict) -> dict:
    excluded_states = {"AWAITING_IDENTITY_RESOLUTION", "OUT_OF_CURRENT_CATEGORY",
                       "AWAITING_OFFICIAL_URL"}
    by_key_state = {i["identity_key"]: i["final_state"] for i in partition["items"]}
    rows = []
    for row in results["rows"]:
        if not row["included_in_routing_authority"]:
            continue
        if row["census_review_candidate"]:
            continue
        state = by_key_state.get(row["identity_key"])
        if state in excluded_states:
            continue
        census_row = census_by_key[row["identity_key"]]
        readiness = "ROUTING_READY" if row["brand_lane"] in ATTENDED_REQUIRED_LANES \
            else "EVIDENCE_READY"
        rows.append({
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "market_id": MARKET_ID,
            "corridor": row["corridor"],
            "brand_lane": row["brand_lane"],
            "official_url": row["final_url"],
            "property_code": row["property_code"],
            "address": census_row["address"],
            "city": census_row["city"],
            "state": census_row["state"],
            "postal_code": census_row["postal_code"],
            "phone": census_row.get("phone", ""),
            "readiness": readiness,
            "readiness_reason": (
                "Client-rendered SPA or WAF-walled brand -- static fetch will not "
                "surface the policy content; attended browser capture required."
                if readiness == "ROUTING_READY" else
                "Server-rendered brand page or independent site -- a static fetch "
                "should surface the policy content directly."),
            "status": "NOT_STARTED",
        })
    rows.sort(key=lambda r: r["identity_key"])
    return {
        "schema": "ptf-market-capture-queue/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET_ID,
        "as_of": AS_OF,
        "note": ("Strict capture-ready queue: routed, non-census-review, not "
                 "identity/category-excluded, not already policy-observed. Every "
                 "row starts NOT_STARTED."),
        "count": len(rows),
        "readiness_counts": dict(sorted(
            collections.Counter(r["readiness"] for r in rows).items())),
        "rows": rows,
    }


def build_corridor_readiness(census, old_partition_items, new_partition_items) -> dict:
    corridors = _load(MARKET_CONFIG_PATH)["corridors"]
    corridor_ids = [c["corridor_id"] for c in corridors]
    census_by_key = {h["identity_key"]: h for h in census["hotels"]}

    def state_by_corridor(items):
        out = collections.defaultdict(lambda: collections.Counter())
        for item in items:
            corridor = census_by_key.get(item["identity_key"], {}).get("corridor")
            out[corridor][item["final_state"]] += 1
        return out

    before = state_by_corridor(old_partition_items)
    after = state_by_corridor(new_partition_items)

    def readiness_pct(counter):
        total = sum(counter.values())
        if not total:
            return 0.0
        ready = counter.get("AWAITING_POLICY_OBSERVATION", 0)
        return round(100.0 * ready / total, 1)

    rows = []
    for cid in corridor_ids:
        rows.append({
            "corridor_id": cid,
            "priority": cid in PRIORITY_CORRIDORS,
            "total_identities": sum(before.get(cid, {}).values()),
            "before": dict(before.get(cid, {})),
            "after": dict(after.get(cid, {})),
            "policy_capture_ready_pct_before": readiness_pct(before.get(cid, {})),
            "policy_capture_ready_pct_after": readiness_pct(after.get(cid, {})),
        })
    return {
        "schema": "ptf-market-corridor-readiness/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET_ID,
        "as_of": AS_OF,
        "priority_corridors": list(PRIORITY_CORRIDORS),
        "corridors": rows,
    }


def main() -> None:
    progress = _load(PROGRESS_PATH)
    if progress["remaining_count"] != 0:
        raise SystemExit("progress checkpoint is not complete: %d remaining"
                         % progress["remaining_count"])

    census = _load(CENSUS_PATH)
    census_by_key = {h["identity_key"]: h for h in census["hotels"]}
    partition = _load(PARTITION_PATH)
    old_items = [dict(i) for i in partition["items"]]

    results = build_results(progress, census_by_key)
    _write(RESULTS_PATH, results)

    new_records = build_routing_records(results, census_by_key)
    existing_doc = _load(ROUTING_PATH)
    combined = {"schema": existing_doc["schema"], "routes": existing_doc["routes"] + new_records}
    validated = validate_authority(combined)  # raises if anything collides
    new_doc = dict(existing_doc)
    new_doc["routes"] = validated
    new_doc["count"] = len(validated)
    new_doc["source_batches"] = existing_doc.get("source_batches", []) + ["cincinnati-url-routing-recovery-001c"]
    _write(ROUTING_PATH, new_doc)

    new_partition = rebuild_partition(partition, results)
    _write(PARTITION_PATH, new_partition)

    queue = build_capture_queue(results, census_by_key, new_partition)
    _write(CAPTURE_QUEUE_PATH, queue)

    corridor_report = build_corridor_readiness(census, old_items, new_partition["items"])
    _write(CORRIDOR_REPORT_PATH, corridor_report)

    print("results: %d rows, %d routed, %d excluded" % (
        results["total"], results["included_in_routing_authority"], results["excluded_no_url"]))
    print("routing authority: %d total (%d new)" % (len(validated), len(new_records)))
    print("partition final_state_counts:", new_partition["final_state_counts"])
    print("capture queue: %d rows, %s" % (queue["count"], queue["readiness_counts"]))


if __name__ == "__main__":
    main()

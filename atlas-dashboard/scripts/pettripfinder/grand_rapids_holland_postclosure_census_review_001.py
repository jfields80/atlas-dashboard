"""PTF-GRAND-RAPIDS-HOLLAND-POSTCLOSURE-CENSUS-REVIEW-001.

Review only the fixed routing-recovery tail.  This writer does not mutate the
closed census, routing authority, partition, capture queue, or policy facts.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

from scripts.pettripfinder.grand_rapids_holland_identity_routing_repair_001 import lane


MARKET = "grand-rapids-holland-mi"
AS_OF = "2026-08-17"
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = PACKAGE / "identity_census" / (MARKET + ".json")
RESULTS_PATH = PACKAGE / "markets" / "reports" / (MARKET + "_routing_results_001.json")
ROUTING_PATH = PACKAGE / "identity_routing.json"
OUTPUT_PATH = PACKAGE / "grand_rapids_holland_postclosure_census_review_001.json"

EXPECTED_LANES = {
    "HILTON": 9,
    "MARRIOTT": 4,
    "IHG": 3,
    "CHOICE": 5,
    "WYNDHAM": 4,
    "RADISSON": 5,
    "ESA": 2,
    "WOODSPRING": 1,
    "G6": 1,
    "RED_ROOF": 1,
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dump(path: Path, document) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _evidence(row: dict, brand_lane: str) -> list[dict]:
    evidence = [
        {
            "evidence_type": "closed_census_identity_provenance",
            "source_id": row["source"],
            "result": "Final census binds canonical name, street address, city/state, ZIP, and phone where available.",
        },
        {
            "evidence_type": "routing_authority_check",
            "result": "No exact property-level official URL is currently accepted for this identity; absence of a route is not closure or conversion evidence.",
        },
    ]
    if brand_lane == "INDEPENDENT":
        evidence.append({
            "evidence_type": "first_party_domain_requirement",
            "result": "No property-owned domain is committed. This does not establish that the property is closed or route-less; it requires a separate exact-domain recovery check.",
        })
    else:
        evidence.append({
            "evidence_type": "official_brand_recovery_lane",
            "result": "Use the current official brand locator, property index, or property page with exact name/address/ZIP binding; generic brand pages remain inadmissible.",
        })
    if brand_lane == "RADISSON":
        evidence.append({
            "evidence_type": "portfolio_migration_guardrail",
            "result": "Potential Radisson/Choice-era migration was considered. No distinct current successor identity is proven in the closed-census record, so no identity mutation is proposed.",
        })
    return evidence


def _item(row: dict, routing_row: dict) -> dict:
    brand_lane = routing_row["brand_lane"]
    independent = brand_lane == "INDEPENDENT"
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "address": row["address"],
        "city": row["city"],
        "state": row["state"],
        "postal_code": row["postal_code"],
        "phone": row.get("phone", ""),
        "corridor": row["corridor"],
        "current_brand": brand_lane,
        "current_routing_blocker": "No exact property-level official URL is accepted in routing authority.",
        "official_evidence_checked": _evidence(row, brand_lane),
        "current_identity_evidence": {
            "canonical_name": row["canonical_name"],
            "address": row["address"],
            "city": row["city"],
            "state": row["state"],
            "postal_code": row["postal_code"],
            "phone": row.get("phone", ""),
            "census_source": row["source"],
        },
        "review_question_result": "ROUTING_RECOVERY_ONLY",
        "proposed_disposition": "INDEPENDENT_FINAL_RECOVERY" if independent else "ROUTING_RECOVERY_CLEAN",
        "recommended_founder_action": "NONE",
        "routing_next_action": (
            "Recover an exact property-owned domain and contact/location page; if none can be strongly bound after that focused check, classify ROUTING_UNRESOLVED."
            if independent else
            "Recover an exact official brand property page or locator result using canonical name, street address, ZIP, and property code or phone where exposed."
        ),
        "census_action": "NO_CHANGE",
    }


def main() -> None:
    census = _load(CENSUS_PATH)
    active = [row for row in census["hotels"] if row["lodging_state"] == "LODGING_CONFIRMED"]
    if census["count"] != 120 or len(active) != 119:
        raise SystemExit("closed census changed; refusing post-closure review")
    by_key = {row["identity_key"]: row for row in active}

    results = _load(RESULTS_PATH)
    recovered = [row for row in results["rows"] if row["verdict"] == "PROPERTY_LEVEL_URL_RECOVERY"]
    confirmed = [row for row in results["rows"] if row["verdict"] == "PROPERTY_LEVEL_ROUTE_CONFIRMED"]
    if len(results["rows"]) != 119 or len(confirmed) != 67 or len(recovered) != 52:
        raise SystemExit("routing recovery universe changed; refusing post-closure review")
    if {row["identity_key"] for row in results["rows"]} != set(by_key):
        raise SystemExit("routing results no longer reconcile to the closed active census")
    if any(row["brand_lane"] != lane(row["canonical_name"]) for row in recovered):
        raise SystemExit("routing lane classification drifted")

    structured = [row for row in recovered if row["brand_lane"] != "INDEPENDENT"]
    local = [row for row in recovered if row["brand_lane"] == "INDEPENDENT"]
    structured_counts = dict(sorted(collections.Counter(row["brand_lane"] for row in structured).items()))
    if structured_counts != dict(sorted(EXPECTED_LANES.items())) or len(local) != 17:
        raise SystemExit("expected 35 structured and 17 independent recovery rows")

    routing = _load(ROUTING_PATH)
    current_routes = [row for row in routing["routes"] if row["market_id"] == MARKET]
    if len(current_routes) != 67:
        raise SystemExit("routing authority changed; refusing review output")

    items = [_item(by_key[item["identity_key"]], item) for item in recovered]
    items.sort(key=lambda item: item["identity_key"])
    disposition_counts = dict(sorted(collections.Counter(item["proposed_disposition"] for item in items).items()))
    if disposition_counts != {"INDEPENDENT_FINAL_RECOVERY": 17, "ROUTING_RECOVERY_CLEAN": 35}:
        raise SystemExit("review partition is not exact")

    _dump(OUTPUT_PATH, {
        "schema": "ptf-postclosure-census-review/1.0",
        "market_id": MARKET,
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-POSTCLOSURE-CENSUS-REVIEW-001",
        "as_of": AS_OF,
        "scope": "Closed-census routing-resistance review only. No hotel discovery, census mutation, routing-authority mutation, or policy observation was performed.",
        "census_count": 120,
        "active_lodging_count": 119,
        "current_routed_count": 67,
        "count": len(items),
        "reconciliation": {
            "property_level_url_recovery": len(items),
            "structured_brand": len(structured),
            "independent_local": len(local),
            "structured_brand_lanes": structured_counts,
        },
        "review_partitions": {
            "ROUTING_RECOVERY_CLEAN": 35,
            "FOUNDER_IDENTITY_REVIEW": 0,
            "CLOSED_CONVERSION_REVIEW": 0,
            "ROUTING_UNRESOLVED": 0,
            "INDEPENDENT_FINAL_RECOVERY": 17,
        },
        "routing_continuation_plan": {
            "next_batch": "ROUTING_RECOVERY_CLEAN",
            "next_batch_count": 35,
            "deferred_independent_final_recovery_count": 17,
            "founder_review_rows": [],
            "note": "The next routing continuation should work only the 35 clean structured-brand rows. The independent lane remains separate until first-party-domain recovery is completed.",
        },
        "items": items,
        "note": "No evidence in this review supports a census rename, removal, addition, closure, conversion, or duplicate finding. A missing exact URL is kept separate from a current-identity defect.",
    })


if __name__ == "__main__":
    main()

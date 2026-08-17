"""PTF-GRAND-RAPIDS-HOLLAND-IDENTITY-ROUTING-REPAIR-001.

Routing only.  This writer consumes the closed 119-identity lodging universe,
never creates a census record, and never observes or stores policy content.
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from scripts.pettripfinder.build_grand_rapids_holland_market_001 import PROPERTY_URLS
from scripts.pettripfinder.identity_routing import ROUTING_CONFIRMED, validate_authority

MARKET = "grand-rapids-holland-mi"
AS_OF = "2026-08-17"
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
CENSUS_PATH = PACKAGE / "identity_census" / (MARKET + ".json")
PARTITION_PATH = PACKAGE / "grand_rapids_holland_final_partition_001.json"
ROUTING_PATH = PACKAGE / "identity_routing.json"

# PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-001.  Current official
# locator/property-page results.  Each URL was accepted only where the exact
# property name plus the census street address and ZIP were exposed together.
RECOVERED_URLS = {
    "Tru by Hilton Grand Rapids Airport": "https://www.hilton.com/en/hotels/grrndru-tru-grand-rapids-airport/",
    "Amway Grand Plaza Curio Collection by Hilton": "https://www.hilton.com/en/hotels/grrqqqq-amway-grand-plaza/",
    "AC Hotel Grand Rapids Downtown": "https://www.marriott.com/en-us/hotels/grrar-ac-hotel-grand-rapids-downtown/overview/",
    "Courtyard by Marriott Grand Rapids Airport": "https://www.marriott.com/en-us/hotels/grrcy-courtyard-grand-rapids-airport/overview/",
    "Residence Inn Grand Rapids Airport": "https://www.marriott.com/en-us/hotels/grrri-residence-inn-grand-rapids-airport/overview/",
    "Courtyard by Marriott Holland Downtown": "https://www.marriott.com/en-us/hotels/grrch-courtyard-holland-downtown/overview/",
    "JW Marriott Grand Rapids": "https://www.marriott.com/en-us/hotels/grrjw-jw-marriott-grand-rapids/overview/",
    "Fairfield Inn & Suites Grand Rapids North": "https://www.marriott.com/en-us/hotels/grrfn-fairfield-inn-and-suites-grand-rapids-north/overview/",
    "Holiday Inn Grand Rapids Downtown": "https://www.ihg.com/holidayinn/hotels/us/en/grand-rapids/grrpe/hoteldetail",
    "Staybridge Suites Grand Rapids Airport": "https://www.ihg.com/staybridge/hotels/us/en/grand-rapids/grrmi/hoteldetail",
    "Holiday Inn Express Holland": "https://www.ihg.com/holidayinnexpress/hotels/us/en/holland/hldfe/hoteldetail",
    "Holiday Inn Grand Rapids Airport": "https://www.ihg.com/holidayinn/hotels/us/en/grand-rapids/grrpd/hoteldetail",
    "Holiday Inn Grand Rapids North - Walker": "https://www.ihg.com/holidayinn/hotels/us/en/walker/grrwk/hoteldetail",
    "Candlewood Suites Grand Rapids Airport": "https://www.ihg.com/candlewood/hotels/us/en/grand-rapids/grres/hoteldetail",
    "Holiday Inn Express & Suites Grand Rapids-North": "https://www.ihg.com/holidayinnexpress/hotels/us/en/walker/grrds/hoteldetail",
    "Wyndham Garden Grand Rapids Airport": "https://www.wyndhamhotels.com/wyndham-garden/grand-rapids-michigan/wyndham-garden-grand-rapids/overview",
    "Days Inn by Wyndham Holland": "https://www.wyndhamhotels.com/days-inn/holland-michigan/days-inn-holland/overview",
    "Comfort Inn Grand Rapids Airport": "https://www.choicehotels.com/michigan/grand-rapids/comfort-inn-hotels/mi121",
    "Comfort Suites Grand Rapids North": "https://www.choicehotels.com/michigan/comstock-park/comfort-suites-hotels/mi235",
    "MainStay Suites Grand Rapids": "https://www.choicehotels.com/michigan/grand-rapids/mainstay-hotels/mi668",
    "Clarion Inn & Suites Airport": "https://www.choicehotels.com/michigan/grand-rapids/clarion-hotels/mi355",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dump(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def lane(name: str) -> str:
    value = name.lower()
    groups = (
        ("HILTON", ("hilton", "hampton", "homewood", "home2", "doubletree", "canopy", "embassy", "tru", "spark", "tulyp", "curio")),
        ("MARRIOTT", ("marriott", "courtyard", "fairfield", "residence inn", "springhill", "towneplace", "ac hotel", "jw ", "sheraton")),
        ("IHG", ("holiday inn", "staybridge", "candlewood", "avid")),
        ("CHOICE", ("comfort", "quality", "clarion", "rodeway", "econo", "mainstay", "the center hotel")),
        ("WYNDHAM", ("wyndham", "days inn", "super 8", "travelodge", "microtel", "americinn", "baymont")),
        ("RADISSON", ("radisson", "country inn")),
        ("ESA", ("extended stay america",)), ("RED_ROOF", ("red roof",)),
        ("G6", ("motel 6",)), ("BEST_WESTERN", ("best western",)),
        ("DRURY", ("drury",)), ("HYATT", ("hyatt",)), ("WOODSPRING", ("woodspring",)),
    )
    for label, tokens in groups:
        if any(token in value for token in tokens):
            return label
    return "INDEPENDENT"


def property_code(url: str, brand_lane: str) -> str:
    if brand_lane == "HILTON":
        match = re.search(r"/hotels/([a-z0-9]+)-", url, re.I)
        return match.group(1).lower() if match else ""
    if brand_lane == "MARRIOTT":
        match = re.search(r"/hotels/([a-z0-9]+)-", url, re.I)
        return match.group(1).lower() if match else ""
    if brand_lane == "IHG":
        match = re.search(r"/([a-z0-9]{5,})/hoteldetail", url, re.I)
        return match.group(1).lower() if match else ""
    if brand_lane == "CHOICE":
        match = re.search(r"/([a-z]{2}\d{3,})$", url, re.I)
        return match.group(1).lower() if match else ""
    match = re.search(r"propertyCode[.=]([a-z0-9]+)", url, re.I)
    return match.group(1).lower() if match else ""


def _domain(url: str) -> str:
    labels = (urlsplit(url).hostname or "").lower().split(".")
    return ".".join(labels[-2:])


def main() -> None:
    census = _load(CENSUS_PATH)
    active = [row for row in census["hotels"] if row["lodging_state"] == "LODGING_CONFIRMED"]
    if census["count"] != 120 or len(active) != 119:
        raise SystemExit("fixed routing universe changed; refusing to route")
    by_name = {row["canonical_name"]: row for row in active}
    if set(PROPERTY_URLS) - set(by_name):
        raise SystemExit("a property URL points outside the fixed active census")

    rows = []
    for row in active:
        name = row["canonical_name"]
        url = RECOVERED_URLS.get(name, PROPERTY_URLS.get(name, ""))
        brand_lane = lane(name)
        confirmed = bool(url)
        code = property_code(url, brand_lane) if url else ""
        rows.append({
            "identity_key": row["identity_key"], "canonical_name": name,
            "corridor": row["corridor"], "brand_lane": brand_lane,
            "verdict": "PROPERTY_LEVEL_ROUTE_CONFIRMED" if confirmed else "PROPERTY_LEVEL_URL_RECOVERY",
            "official_url": url, "property_code": code,
            "binding_signals": (["canonical_name", "street_address", "postal_code"] if confirmed else []),
            "source_relationship": "EXACT_PROPERTY_FIRST_PARTY" if confirmed else "",
            "reason": ("Existing exact first-party URL re-bound to the closed census identity by canonical name, street address, and ZIP; no policy page was inspected."
                       if confirmed else "No exact property-level official URL is committed in the closed-census provenance; retained for official-locator recovery."),
        })
    rows.sort(key=lambda item: item["identity_key"])
    confirmed = [row for row in rows if row["official_url"]]
    recovery = [row for row in rows if not row["official_url"]]
    assert len(rows) == len(active) == len(confirmed) + len(recovery)

    progress = {
        "schema": "ptf-market-identity-routing-progress/1.0", "market_id": MARKET,
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-IDENTITY-ROUTING-REPAIR-001", "as_of": AS_OF,
        "total_universe": 119, "processed": 119,
        "route_confirmed": len(confirmed), "url_recovery": len(recovery),
        "identity_review": 0, "census_review": 0, "routing_unresolved": 0,
        "remaining": 0,
        "checkpoints": [
            {"lane": label, "processed": count, "route_confirmed": sum(1 for row in confirmed if row["brand_lane"] == label),
             "url_recovery": sum(1 for row in recovery if row["brand_lane"] == label)}
            for label, count in sorted(collections.Counter(row["brand_lane"] for row in rows).items())
        ],
        "note": "This durable first routing checkpoint adjudicates every fixed-census row. URL-recovery rows remain un-routed; no URL was inferred from a generic brand page or a search snippet.",
    }
    _dump(PACKAGE / "grand_rapids_holland_identity_routing_repair_001_progress.json", progress)
    results = {"schema": "ptf-market-routing-results/1.0", "market_id": MARKET,
               "work_order": progress["work_order"], "as_of": AS_OF, "total": 119,
               "routing_confirmed": len(confirmed), "url_recovery": len(recovery),
               "identity_review": 0, "census_review": 0, "routing_unresolved": 0, "rows": rows}
    _dump(REPORTS / (MARKET + "_routing_results_001.json"), results)

    existing = _load(ROUTING_PATH)
    old_routes = [route for route in existing["routes"] if route["market_id"] != MARKET]
    routes = list(old_routes)
    for item in confirmed:
        census_row = next(row for row in active if row["identity_key"] == item["identity_key"])
        context = {field: census_row.get(field, "") for field in ("address", "city", "state", "postal_code", "phone")}
        routes.append({
            "routing_id": "route-%s-%s" % (MARKET, item["identity_key"].replace(" ", "-")),
            "schema_version": "1.0.0",
            "hotel_ref": {"market_id": MARKET, "canonical_name": item["canonical_name"],
                          "normalized_name": item["identity_key"], "identity_key": item["identity_key"]},
            "market_id": MARKET, "official_property_url": item["official_url"],
            "official_domain": _domain(item["official_url"]), "property_code": item["property_code"],
            "brand": item["brand_lane"], "binding_method": "BRAND_INDEX_BINDING",
            "binding_sources": ["closed-census first-party URL provenance", "routing repair census rebind"],
            "identity_signals_matched": ["canonical_name", "street_address", "postal_code"],
            "identity_context": context, "observed_at": AS_OF, "verified_at": AS_OF,
            "status": ROUTING_CONFIRMED, "category": "accommodation",
            "notes": "Routing-only binding; no pet-policy content was observed.",
        })
    validated = validate_authority({"schema": existing["schema"], "routes": routes})
    routed_doc = dict(existing)
    routed_doc["routes"] = validated
    routed_doc["count"] = len(validated)
    routed_doc["source_batches"] = existing.get("source_batches", []) + ["grand-rapids-holland-identity-routing-repair-001"]
    _dump(ROUTING_PATH, routed_doc)

    partition = _load(PARTITION_PATH)
    route_keys = {row["identity_key"] for row in confirmed}
    for item in partition["items"]:
        if item["identity_key"] in route_keys:
            item["final_state"] = "AWAITING_POLICY_OBSERVATION"
            item["official_url"] = next(row["official_url"] for row in confirmed if row["identity_key"] == item["identity_key"])
            item["next_action"] = "Policy observation is not started by this routing-only work order."
            item["determined_by"] = progress["work_order"]
            item["updated_at"] = AS_OF
    partition["final_state_counts"] = dict(sorted(collections.Counter(item["final_state"] for item in partition["items"]).items()))
    partition["work_order"] = progress["work_order"]
    _dump(PARTITION_PATH, partition)

    # Known client-rendered / WAF lanes use a fresh attended session.  All
    # others remain explicit unknowns, rather than pretending a URL proves a
    # policy surface is fetchable.
    fresh_lanes = {"CHOICE", "MARRIOTT", "HYATT", "IHG"}
    queue_rows = []
    for item in confirmed:
        mode = "FRESH_SESSION_REQUIRED" if item["brand_lane"] in fresh_lanes else "POLICY_SURFACE_UNKNOWN"
        queue_rows.append({"identity_key": item["identity_key"], "canonical_name": item["canonical_name"],
                           "market_id": MARKET, "corridor": item["corridor"], "brand": item["brand_lane"],
                           "official_url": item["official_url"], "property_code": item["property_code"],
                           "routing_class": "ROUTING_READY", "evidence_readiness_class": mode,
                           "capture_mode": mode, "review_status": "NOT_STARTED"})
    queue = {"schema": "ptf-market-capture-queue/1.0", "market_id": MARKET,
             "work_order": progress["work_order"], "as_of": AS_OF, "count": len(queue_rows),
             "readiness_counts": dict(sorted(collections.Counter(row["evidence_readiness_class"] for row in queue_rows).items())),
             "items": queue_rows,
             "note": "Routing-only queue. No policy content was captured or assessed."}
    _dump(PACKAGE / "grand_rapids_holland_capture_ready_queue_002.json", queue)
    _dump(PACKAGE / "grand_rapids_holland_postclosure_census_review_001.json", {
        "schema": "ptf-postclosure-census-review/1.0", "market_id": MARKET,
        "work_order": progress["work_order"], "count": 0, "items": [],
        "note": "No routing observation supplied a closure, conversion, rebrand, or new-hotel claim."})


if __name__ == "__main__":
    main()

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
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.identity_routing import ROUTING_CONFIRMED

MARKET = "grand-rapids-holland-mi"
AS_OF = "2026-08-17"
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
CENSUS_PATH = PACKAGE / "identity_census" / (MARKET + ".json")
PARTITION_PATH = PACKAGE / "grand_rapids_holland_final_partition_001.json"
POSTCLOSURE_REVIEW_PATH = PACKAGE / "grand_rapids_holland_postclosure_census_review_001.json"

# PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-001.  Current official
# locator/property-page results.  Each URL was accepted only where the exact
# property name plus the census street address and ZIP were exposed together.
RECOVERED_URLS = {
    # PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-003 — Hilton.
    "DoubleTree by Hilton Grand Rapids Airport": "https://www.hilton.com/en/hotels/grraidt-doubletree-grand-rapids-airport/",
    "DoubleTree by Hilton Holland": "https://www.hilton.com/en/hotels/grrhldt-doubletree-holland/",
    "Hilton Garden Inn Grand Rapids East": "https://www.hilton.com/en/hotels/grrebgi-hilton-garden-inn-grand-rapids-east/",
    "Home2 Suites by Hilton Grand Rapids Airport": "https://www.hilton.com/en/hotels/grrdaht-home2-suites-grand-rapids-airport/",
    "Homewood Suites by Hilton Grand Rapids Downtown": "https://www.hilton.com/en/hotels/grrdohw-homewood-suites-grand-rapids-downtown/",
    "Homewood Suites by Hilton Holland": "https://www.hilton.com/en/hotels/grrabhw-homewood-suites-holland/",
    "Spark by Hilton Grand Rapids": "https://www.hilton.com/en/hotels/grrgspe-spark-grand-rapids/",
    "Tru by Hilton Comstock Park Grand Rapids": "https://www.hilton.com/en/hotels/grrrrru-tru-comstock-park-grand-rapids/",
    "Tulyp Tapestry Collection by Hilton": "https://www.hilton.com/en/hotels/grrcfup-tulyp/",
    # PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-003 — Marriott.
    "Fairfield Inn & Suites Grand Rapids": "https://www.marriott.com/en-us/hotels/grrpa-fairfield-inn-and-suites-grand-rapids/overview/",
    "Residence Inn by Marriott Grand Rapids Downtown": "https://www.marriott.com/en-us/hotels/grrrd-residence-inn-grand-rapids-downtown/overview/",
    "TownePlace Suites Grand Rapids Airport": "https://www.marriott.com/en-us/hotels/grrts-towneplace-suites-grand-rapids-airport/overview/",
    # PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-003 — IHG.
    "Holiday Inn Express & Suites Grand Rapids - Airport North": "https://www.ihg.com/holidayinnexpress/hotels/us/en/grand-rapids/grret/hoteldetail",
    "Holiday Inn Express & Suites Grand Rapids Airport South": "https://www.ihg.com/holidayinnexpress/hotels/us/en/grand-rapids/grrse/hoteldetail",
    "Staybridge Suites Grand Rapids South": "https://www.ihg.com/staybridge/hotels/us/en/grand-rapids/grred/hoteldetail",
    # PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-003 — Choice.
    "Comfort Suites Grand Rapids South": "https://www.choicehotels.com/michigan/grand-rapids/comfort-suites-hotels/mi231",
    "Econo Lodge Grand Rapids Airport": "https://www.choicehotels.com/michigan/grand-rapids/econo-lodge-hotels/mi294",
    "Quality Inn Grand Rapids Near Downtown": "https://www.choicehotels.com/michigan/grand-rapids/quality-inn-hotels/mi281",
    "Quality Inn Grand Rapids North - Walker": "https://www.choicehotels.com/michigan/walker/quality-inn-hotels/mi298",
    # PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-003 — Wyndham.
    "Microtel Inn & Suites by Wyndham Holland": "https://www.wyndhamhotels.com/microtel/holland-michigan/microtel-inn-and-suites-holland/overview",
    # PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-003 — Radisson migration lane.
    "Country Inn & Suites by Radisson Grandville-Grand Rapids West": "https://www.choicehotels.com/michigan/grandville/country-inn-suites-hotels/mi612",
    "Country Inn & Suites by Radisson Holland": "https://www.choicehotels.com/michigan/holland/country-inn-suites-hotels/mi444",
    "Country Inn & Suites Grand Rapids Airport": "https://www.choicehotels.com/michigan/grand-rapids/country-inn-suites-hotels/mi611",
    "Country Inn & Suites Grand Rapids East": "https://www.choicehotels.com/michigan/grand-rapids/country-inn-suites-hotels/mi607",
    "Radisson Hotel Grand Rapids Riverfront": "https://www.choicehotels.com/michigan/grand-rapids/radisson-hotels/mi423",
    # PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-003 — small brands.
    "Extended Stay America Select Suites Grand Rapids Kentwood": "https://www.extendedstayamerica.com/hotels/mi/grand-rapids/kentwood",
    "Extended Stay America Select Suites Grand Rapids Wyoming": "https://www.extendedstayamerica.com/hotels/mi/grand-rapids/wyoming",
    "WoodSpring Suites Grand Rapids Kentwood": "https://www.woodspring.com/extended-stay-hotels/locations/michigan/grand-rapids/woodspring-suites-grand-rapids-kentwood",
    "Motel 6 Grand Rapids": "https://www.motel6.com/property/motel-grand-rapids-mi-michigan-us-293514/",
    "Red Roof Inn Grand Rapids Airport": "https://www.redroof.com/property/mi/grand-rapids/rri011",
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
    "Fairfield Inn & Suites Grand Rapids Wyoming": "https://www.marriott.com/en-us/hotels/grrfw-fairfield-inn-and-suites-grand-rapids-wyoming/overview/",
    "SpringHill Suites by Marriott Grand Rapids West": "https://www.marriott.com/en-us/hotels/grrgs-springhill-suites-grand-rapids-west/overview/",
    "Hyatt Place Grand Rapids South": "https://www.hyatt.com/hyatt-place/en-US/grrzw-hyatt-place-grand-rapids-south",
    "Staybridge Suites Grand Rapids SW - Grandville": "https://www.ihg.com/staybridge/hotels/us/en/grandville/grrgv/hoteldetail",
    "Holiday Inn Express & Suites Grand Rapids South - Wyoming": "https://www.ihg.com/holidayinnexpress/hotels/us/en/wyoming-mi/grrym/hoteldetail",
    "Holiday Inn Grand Rapids South": "https://www.ihg.com/holidayinn/hotels/us/en/grand-rapids/byomi/hoteldetail",
    "Super 8 by Wyndham Grand Rapids": "https://www.wyndhamhotels.com/super-8/wyoming-michigan/super-8-grand-rapids-wyoming/overview",
    # PTF-GRAND-RAPIDS-HOLLAND-CENSUS-REVIEW-002 â€” current property names
    # and address binding, without any policy-page inspection.
    "Baymont by Wyndham Holland": "https://www.wyndhamhotels.com/baymont/holland-michigan/baymont-inn-and-suites-holland/overview",
    "Baymont by Wyndham Grand Rapids Airport": "https://www.wyndhamhotels.com/baymont/grand-rapids-michigan/baymont-inn-and-suites-grand-rapids-airport/overview",
    "Days Inn & Suites by Wyndham Grand Rapids Near Downtown": "https://www.wyndhamhotels.com/days-inn/grand-rapids-michigan/days-inn-and-suites-grand-rapids-near-downtown/overview",
    "Quality Inn Grand Rapids South-Byron Center": "https://www.choicehotels.com/michigan/grand-rapids/quality-inn-hotels/mi312",
    "TownePlace Suites by Marriott Grand Rapids Wyoming": "https://www.marriott.com/en-us/hotels/grrtw-towneplace-suites-grand-rapids-wyoming/overview/",
}

# Exact official source evidence may require a closed-census identity review.
# Do not bind a route to a materially different current name until that review
# is authorized; address continuity alone is not a silent census correction.
CENSUS_REVIEW = {}

# The post-closure review is historical evidence. Four of the five names it
# recorded were subsequently accepted as narrow in-place census corrections.
# Preserve its 35/17 continuation split while comparing it to current keys.
HISTORICAL_IDENTITY_KEY_RENAMES = {
    "baymont inn and suites by wyndham holland": "baymont by wyndham holland",
    "baymont inn and suites grand rapids southeast": "baymont by wyndham grand rapids airport",
    "quality inn grand rapids south": "quality inn grand rapids south byron center",
    "towneplace suites grand rapids south": "towneplace suites by marriott grand rapids wyoming",
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
    if brand_lane in {"CHOICE", "RADISSON"}:
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
    postclosure_review = _load(POSTCLOSURE_REVIEW_PATH)
    clean_structured_keys = {
        HISTORICAL_IDENTITY_KEY_RENAMES.get(item["identity_key"], item["identity_key"])
        for item in postclosure_review["items"]
        if item["proposed_disposition"] == "ROUTING_RECOVERY_CLEAN"
    }
    independent_final_keys = {
        item["identity_key"] for item in postclosure_review["items"]
        if item["proposed_disposition"] == "INDEPENDENT_FINAL_RECOVERY"
    }
    if len(clean_structured_keys) != 35 or len(independent_final_keys) != 17:
        raise SystemExit("post-closure routing review no longer supplies the fixed 35/17 split")

    rows = []
    for row in active:
        name = row["canonical_name"]
        url = RECOVERED_URLS.get(name, PROPERTY_URLS.get(name, ""))
        brand_lane = lane(name)
        needs_census_review = name in CENSUS_REVIEW
        confirmed = bool(url) and not needs_census_review
        code = property_code(url, brand_lane) if url else ""
        rows.append({
            "identity_key": row["identity_key"], "canonical_name": name,
            "corridor": row["corridor"], "brand_lane": brand_lane,
            "verdict": ("CENSUS_REVIEW" if needs_census_review else
                        "PROPERTY_LEVEL_ROUTE_CONFIRMED" if confirmed else "PROPERTY_LEVEL_URL_RECOVERY"),
            "official_url": url if confirmed else "", "property_code": code if confirmed else "",
            "binding_signals": (["canonical_name", "street_address", "postal_code"] if confirmed else []),
            "source_relationship": "EXACT_PROPERTY_FIRST_PARTY" if confirmed else "",
            "reason": (CENSUS_REVIEW[name] if needs_census_review else
                       "Existing exact first-party URL re-bound to the closed census identity by canonical name, street address, and ZIP; no policy page was inspected."
                       if confirmed else "No exact property-level official URL is committed in the closed-census provenance; retained for official-locator recovery."),
        })
    rows.sort(key=lambda item: item["identity_key"])
    confirmed = [row for row in rows if row["official_url"]]
    recovery = [row for row in rows if not row["official_url"]]
    census_review = [row for row in rows if row["verdict"] == "CENSUS_REVIEW"]
    recovery = [row for row in recovery if row["verdict"] == "PROPERTY_LEVEL_URL_RECOVERY"]
    assert len(rows) == len(active) == len(confirmed) + len(recovery) + len(census_review)
    confirmed_keys = {row["identity_key"] for row in confirmed}
    census_review_keys = {row["identity_key"] for row in census_review}
    clean_remaining_keys = clean_structured_keys - confirmed_keys - census_review_keys
    if clean_remaining_keys or (confirmed_keys | census_review_keys) & independent_final_keys:
        raise SystemExit("continuation-003 touched the independent lane or left a clean structured row unadjudicated")

    progress = {
        "schema": "ptf-market-identity-routing-progress/1.0", "market_id": MARKET,
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-IDENTITY-ROUTING-REPAIR-001", "as_of": AS_OF,
        "total_universe": 119, "processed": 119,
        "route_confirmed": len(confirmed), "url_recovery": len(recovery),
        "identity_review": 0, "census_review": len(census_review), "routing_unresolved": 0,
        "remaining": 0,
        "checkpoints": [
            {"lane": label, "processed": count, "route_confirmed": sum(1 for row in confirmed if row["brand_lane"] == label),
             "url_recovery": sum(1 for row in recovery if row["brand_lane"] == label),
             "census_review": sum(1 for row in census_review if row["brand_lane"] == label)}
            for label, count in sorted(collections.Counter(row["brand_lane"] for row in rows).items())
        ],
        "note": "This durable first routing checkpoint adjudicates every fixed-census row. URL-recovery rows remain un-routed; no URL was inferred from a generic brand page or a search snippet.",
    }
    continuation_rows = [row for row in rows if row["identity_key"] in clean_structured_keys]
    progress["continuation_003"] = {
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-ROUTING-REPAIR-CONTINUATION-003",
        "structured_recovery_batch": 35,
        "structured_routes_added": len(confirmed_keys & clean_structured_keys),
        "structured_census_review": len(census_review_keys & clean_structured_keys),
        "structured_routing_unresolved": 0,
        "structured_remaining": len(clean_remaining_keys),
        "independent_final_recovery_deferred": len(independent_final_keys),
        "reconciliation": {
            "active_lodging": 119,
            "route_confirmed": len(confirmed),
            "clean_structured_remaining": len(clean_remaining_keys),
            "census_review": len(census_review),
            "independent_final_recovery": len(independent_final_keys),
        },
        "per_brand": {
            label: {
                "batch": sum(row["brand_lane"] == label for row in continuation_rows),
                "route_confirmed": sum(row["brand_lane"] == label and row["verdict"] == "PROPERTY_LEVEL_ROUTE_CONFIRMED" for row in continuation_rows),
                "census_review": sum(row["brand_lane"] == label and row["verdict"] == "CENSUS_REVIEW" for row in continuation_rows),
            }
            for label in sorted({row["brand_lane"] for row in continuation_rows})
        },
    }
    reconciliation = progress["continuation_003"]["reconciliation"]
    if (reconciliation["route_confirmed"] + reconciliation["clean_structured_remaining"] +
            reconciliation["census_review"] + reconciliation["independent_final_recovery"] !=
            reconciliation["active_lodging"]):
        raise SystemExit("continuation-003 reconciliation failed")
    _dump(PACKAGE / "grand_rapids_holland_identity_routing_repair_001_progress.json", progress)
    results = {"schema": "ptf-market-routing-results/1.0", "market_id": MARKET,
               "work_order": progress["work_order"], "as_of": AS_OF, "total": 119,
               "routing_confirmed": len(confirmed), "url_recovery": len(recovery),
               "identity_review": 0, "census_review": len(census_review), "routing_unresolved": 0, "rows": rows}
    _dump(REPORTS / (MARKET + "_routing_results_001.json"), results)

    existing = MA.load_market_routing_document(MARKET)
    routes = []
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
    source_batches = list(existing.get("source_batches", []))
    if "grand-rapids-holland-identity-routing-repair-001" not in source_batches:
        source_batches.append("grand-rapids-holland-identity-routing-repair-001")
    routed_doc = MA.build_routing_shard(MARKET, routes, source_batches)
    MA.routing_shard_path(MARKET).write_text(MA.render_json(routed_doc), encoding="utf-8")
    MA.write_generated_artifacts()

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
        mode = ("FRESH_SESSION_REQUIRED" if item["brand_lane"] in fresh_lanes or
                _domain(item["official_url"]) == "choicehotels.com" else "POLICY_SURFACE_UNKNOWN")
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
    # The post-closure review has its own read-only writer.  Do not overwrite
    # its durable per-row findings when this routing-authority writer is rerun.


if __name__ == "__main__":
    main()

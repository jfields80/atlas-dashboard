"""PTF-INDIANAPOLIS-IDENTITY-ROUTING-REPAIR-001.

Audits every unresolved Indianapolis identity and writes:
  launch_packages/pettripfinder/indianapolis_identity_routing_repair_001.json
  launch_packages/pettripfinder/indianapolis_capture_ready_queue_002.json

Does not recapture, publish, merge, or deploy. Does not silently change
canonical names, phones, or addresses.
"""

from __future__ import annotations

import json
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from scripts.pettripfinder.contracts import census as census_mod
from scripts.pettripfinder.contracts import enums, partition as partition_mod
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from services.research_workers.source_retrieval import extract_property_code_from_url
from services.research_workers import vocabulary as V

_REPO = Path(__file__).resolve().parents[2]
PACKAGE = _REPO / "launch_packages" / "pettripfinder"
CENSUS_PATH = PACKAGE / "identity_census" / "indianapolis-in.json"
PARTITION_PATH = PACKAGE / "indianapolis_final_partition_001.json"
REPAIR_PATH = PACKAGE / "indianapolis_identity_routing_repair_001.json"
QUEUE_PATH = PACKAGE / "indianapolis_capture_ready_queue_002.json"
WORK_ORDER = "PTF-INDIANAPOLIS-IDENTITY-ROUTING-REPAIR-001"
MARKET = "indianapolis-in"

PASS1_UNCERTAIN = (
    "baymont by wyndham plainfield indianapolis airport area",
    "best western plus indianapolis northwest",
    "comfort inn indianapolis airport plainfield",
    "comfort suites indianapolis airport",
    "courtyard by marriott indianapolis airport",
    "courtyard by marriott indianapolis castleton",
    "crowne plaza indianapolis downtown union station",
    "delta hotels by marriott indianapolis airport",
)
EMBASSY = "embassy suites by hilton indianapolis downtown"
CROWNE_AIRPORT = "crowne plaza indianapolis airport"
COMFORT_SUITES = "comfort suites indianapolis airport"
HYATT_PLACE = "hyatt place indianapolis airport"

PASS1_SIGNALS = {
    "baymont by wyndham plainfield indianapolis airport area": {
        "agree": ["name_in_body", "city", "phone@structured_metadata"],
        "disagree_or_absent": ["street_address_not_in_structured_metadata"],
        "runner_reason": "IDENTITY_FAILED",
        "final_url": "https://www.wyndhamhotels.com/baymont/plainfield-indiana/baymont-inn-and-suites-plainfield-indianapolis-arpt-area/overview",
        "eight_class": "IDENTITY_CONFIRMED",
        "note": "Same hotel. Official Wyndham property overview. Capture-time gate saw only the phone key. URL has no path-segment property code.",
    },
    "best western plus indianapolis northwest": {
        "agree": ["name_in_body", "city", "street_address@structured_metadata"],
        "disagree_or_absent": ["phone_absent_from_census", "propertyCode.15116_not_a_path_segment"],
        "runner_reason": "IDENTITY_INCOMPLETE",
        "final_url": "https://www.bestwestern.com/en_US/book/hotels-in-indianapolis/best-western-plus-indianapolis-nw-hotel/propertyCode.15116.html",
        "eight_class": "IDENTITY_CONFIRMED",
        "note": "Same hotel. Address matched. JSON-LD petsAllowed was not used. Needs official phone before capture.",
    },
    "comfort inn indianapolis airport plainfield": {
        "agree": ["name_in_body", "city", "phone@structured_metadata"],
        "disagree_or_absent": ["street_address_not_in_structured_metadata"],
        "runner_reason": "IDENTITY_FAILED",
        "final_url": "https://www.choicehotels.com/indiana/plainfield/comfort-inn-hotels/in082",
        "eight_class": "IDENTITY_CONFIRMED",
        "note": "Same hotel. Official Choice property page in082. Second key is the URL property code.",
    },
    "comfort suites indianapolis airport": {
        "agree": ["name_in_body", "city"],
        "disagree_or_absent": ["phone_present_but_different"],
        "runner_reason": "IDENTITY_MISMATCH",
        "final_url": "https://www.choicehotels.com/indiana/indianapolis/comfort-suites-hotels/in293",
        "eight_class": "IDENTITY_CORRECTION_REQUIRED",
        "note": "Official Choice page in293 matches name and city. Census phone 317-481-0700 disagreed with the page. Do not recapture until the phone is reviewed. Do not silently overwrite.",
        "proposed_correction": {
            "field": "phone",
            "current": "317-481-0700",
            "proposed": None,
            "action": "REVIEW",
            "reason": "Pass-1 page presented a different phone. Page fetch is bot-walled; founder must read the official in293 page and decide whether the census phone is stale.",
        },
    },
    "courtyard by marriott indianapolis airport": {
        "agree": ["name_in_title", "city", "phone@structured_metadata"],
        "disagree_or_absent": ["street_address_not_in_structured_metadata"],
        "runner_reason": "IDENTITY_FAILED",
        "final_url": "https://www.marriott.com/hotels/travel/indca-courtyard-indianapolis-airport/",
        "eight_class": "IDENTITY_CONFIRMED",
        "note": "Same hotel. Official Marriott travel URL indca. Sibling Marriott policy not inherited.",
    },
    "courtyard by marriott indianapolis castleton": {
        "agree": ["name_in_title", "city", "street_address@structured_metadata"],
        "disagree_or_absent": ["phone_absent_from_census"],
        "runner_reason": "IDENTITY_INCOMPLETE",
        "final_url": "https://www.marriott.com/en-us/hotels/indcs-courtyard-indianapolis-castleton/overview/",
        "eight_class": "IDENTITY_CONFIRMED",
        "note": "Same hotel. Official Marriott overview indcs. Second key is the URL property code.",
    },
    "crowne plaza indianapolis downtown union station": {
        "agree": ["name_in_body", "city", "street_address@structured_metadata"],
        "disagree_or_absent": ["phone_absent_from_census"],
        "runner_reason": "IDENTITY_INCOMPLETE",
        "final_url": "https://www.ihg.com/crowneplaza/hotels/us/en/indianapolis/inddt/hoteldetail",
        "eight_class": "IDENTITY_CONFIRMED",
        "note": "Same hotel. Official IHG page inddt. Crowne Plaza Airport refusal is not inherited.",
    },
    "delta hotels by marriott indianapolis airport": {
        "agree": ["name_in_body", "city", "phone@structured_metadata"],
        "disagree_or_absent": ["street_address_not_in_structured_metadata"],
        "runner_reason": "IDENTITY_FAILED",
        "final_url": "https://www.marriott.com/en-us/hotels/indde-delta-hotels-indianapolis-airport/overview/",
        "eight_class": "IDENTITY_CONFIRMED",
        "note": "Same hotel. Official Marriott overview indde. Sibling Marriott policy not inherited.",
    },
}


def _audit_class(hotel: Mapping, part: Mapping) -> str:
    key = hotel["identity_key"]
    if key == EMBASSY or key == HYATT_PLACE:
        return "ACCESS_BLOCKED"
    if hotel["identity_state"] != enums.IDENTITY_CONFIRMED:
        return "IDENTITY_REVIEW_REQUIRED"
    if key == COMFORT_SUITES:
        return "IDENTITY_REVIEW_REQUIRED"
    url = hotel.get("official_url") or ""
    routing = hotel.get("routing_class") or ""
    if not url:
        return "OFFICIAL_URL_RECOVERY_REQUIRED"
    if routing == "BRAND_PROPERTY_PAGE":
        return "EXACT_PROPERTY_URL_READY"
    if routing in ("BRAND_INDEX_OR_CITY_LOCATOR", "OFFICIAL_TOURISM_LISTING_ONLY"):
        return "PROPERTY_LEVEL_URL_UPGRADE_REQUIRED"
    if routing == "ACCESS_BLOCKED":
        return "ACCESS_BLOCKED"
    return "OFFICIAL_URL_RECOVERY_REQUIRED"


def _capture_ready(hotel: Mapping) -> bool:
    key = hotel["identity_key"]
    if key in (EMBASSY, HYATT_PLACE, COMFORT_SUITES, CROWNE_AIRPORT):
        return False
    if hotel["identity_state"] != enums.IDENTITY_CONFIRMED:
        return False
    if hotel.get("routing_class") != "BRAND_PROPERTY_PAGE":
        return False
    url = hotel.get("official_url") or ""
    if not url:
        return False
    return bool(extract_property_code_from_url(url))


def _eight_row(hotel: Mapping) -> OrderedDict:
    key = hotel["identity_key"]
    sig = PASS1_SIGNALS[key]
    code = extract_property_code_from_url(hotel.get("official_url") or "") or (
        hotel.get("property_code") or "")
    return OrderedDict((
        ("identity_key", key),
        ("canonical_property_name", hotel["canonical_name"]),
        ("census_name", hotel["canonical_name"]),
        ("official_property_url", hotel.get("official_url") or ""),
        ("final_url", sig["final_url"]),
        ("street_address", hotel.get("address") or ""),
        ("city", hotel["city"]),
        ("state", hotel["state"]),
        ("postal_code", hotel.get("postal_code") or ""),
        ("phone", hotel.get("phone") or ""),
        ("brand", hotel.get("brand") or ""),
        ("property_code", code),
        ("source_authority", hotel.get("source") or ""),
        ("signals_agree", sig["agree"]),
        ("signals_disagree_or_absent", sig["disagree_or_absent"]),
        ("pass1_runner_reason", sig["runner_reason"]),
        ("classification", sig["eight_class"]),
        ("note", sig["note"]),
        ("proposed_correction", sig.get("proposed_correction")),
    ))


def _queue_entry(hotel: Mapping) -> OrderedDict:
    url = hotel["official_url"]
    code = extract_property_code_from_url(url) or hotel.get("property_code") or ""
    return OrderedDict((
        ("hotel_id", hotel["identity_key"]),
        ("listing_key", hotel["identity_key"]),
        ("hotel_name", hotel["canonical_name"]),
        ("brand", hotel.get("brand") or ""),
        ("official_url", url),
        ("expected_address", hotel.get("address") or ""),
        ("expected_city", hotel["city"]),
        ("expected_state", hotel["state"]),
        ("expected_postal_code", hotel.get("postal_code") or ""),
        ("expected_phone", hotel.get("phone") or ""),
        ("expected_property_code", code),
        ("queue_entry_id", "INDY-CR2-%s" % hotel["slug"]),
        ("market_id", MARKET),
        ("supported_adapter", hotel.get("brand") or ""),
        ("identity_confidence", hotel["identity_state"]),
        ("notes", WORK_ORDER),
        ("worker_contract_version", V.CONTRACT_VERSION),
    ))


def main() -> int:
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))
    partition = json.loads(PARTITION_PATH.read_text(encoding="utf-8-sig"))
    rec = partition_mod.reconcile(
        census_mod.identity_keys(census), partition, market_id=MARKET)
    if not rec.agrees:
        raise SystemExit("census/partition do not agree")
    part_by = {i["identity_key"]: i for i in partition["items"]}
    hotels = {h["identity_key"]: h for h in census["hotels"]}

    eight = [_eight_row(hotels[k]) for k in PASS1_UNCERTAIN]
    embassy = OrderedDict((
        ("identity_key", EMBASSY),
        ("classification", "ACCESS_BLOCKED"),
        ("note", "Hilton official URL produced no title or identity text in 20.5s. "
                 "Keep ACCESS_BLOCKED. One fresh-session operator retry after this "
                 "repair, not another automated probe. A block/shell is not policy."),
        ("official_property_url", hotels[EMBASSY].get("official_url") or ""),
        ("property_code", hotels[EMBASSY].get("property_code") or "indwses"),
    ))

    unresolved = [h for h in census["hotels"]
                  if part_by[h["identity_key"]]["final_state"]
                  not in enums.TERMINAL_STATES]
    audit_rows = []
    for h in unresolved:
        klass = _audit_class(h, part_by[h["identity_key"]])
        audit_rows.append(OrderedDict((
            ("identity_key", h["identity_key"]),
            ("canonical_name", h["canonical_name"]),
            ("identity_state", h["identity_state"]),
            ("routing_class", h.get("routing_class") or ""),
            ("final_state", part_by[h["identity_key"]]["final_state"]),
            ("official_url", h.get("official_url") or ""),
            ("url_property_code", extract_property_code_from_url(
                h.get("official_url") or "")),
            ("audit_class", klass),
            ("capture_ready", _capture_ready(h)),
        )))
    audit_counts = OrderedDict(sorted(Counter(
        r["audit_class"] for r in audit_rows).items()))

    ready_hotels = [h for h in unresolved if _capture_ready(h)]
    ready_hotels.sort(key=lambda h: h["identity_key"])
    queue = OrderedDict((
        ("schema", "ptf-capture-queue/1.1"),
        ("batch_id", "indianapolis-capture-ready-002"),
        ("created_at", "2026-08-16"),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("gate", "IDENTITY_CONFIRMED + BRAND_PROPERTY_PAGE + extractable "
                 "URL property code + no phone conflict + not Hilton/Hyatt blocked"),
        ("hotels", [_queue_entry(h) for h in ready_hotels]),
    ))

    eight_classes = OrderedDict(sorted(Counter(
        r["classification"] for r in eight).items()))
    repair = OrderedDict((
        ("schema", "ptf-indianapolis-identity-routing-repair/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-16"),
        ("market_id", MARKET),
        ("crowne_plaza_airport", OrderedDict((
            ("identity_key", CROWNE_AIRPORT),
            ("decision", "APPROVE_VERIFIED_NO_PETS"),
            ("exclusion_id", "indy-crowne-plaza-indianapolis-airport"),
            ("status", "APPLIED"),
            ("published", False),
        ))),
        ("pass1_eight", eight),
        ("pass1_eight_class_counts", eight_classes),
        ("embassy_suites_downtown", embassy),
        ("census_count", rec.census_count),
        ("identities_audited", len(audit_rows)),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("unresolved", rec.unresolved),
        ("audit_class_counts", audit_counts),
        ("identity_corrections_proposed", 1),
        ("identity_corrections_applied", 0),
        ("url_corrections", 0),
        ("renamed_or_converted", 0),
        ("closed", 0),
        ("exact_property_urls_confirmed",
         audit_counts.get("EXACT_PROPERTY_URL_READY", 0)),
        ("capture_ready_count", len(ready_hotels)),
        ("hilton_manual_access_blocked_count",
         audit_counts.get("ACCESS_BLOCKED", 0)),
        ("still_unresolved", rec.unresolved),
        ("rule",
         "No OTA used as identity authority. No sibling-brand policy "
         "inference. Crowne Downtown does not inherit Crowne Airport. "
         "Canonical name/phone/address were not silently mutated. "
         "Comfort Suites phone is a REVIEW proposal only."),
        ("audit_rows", audit_rows),
    ))

    REPAIR_PATH.write_text(json.dumps(repair, indent=2) + "\n", encoding="utf-8")
    QUEUE_PATH.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "census": rec.census_count,
        "audited": len(audit_rows),
        "audit_class_counts": audit_counts,
        "eight_classes": eight_classes,
        "capture_ready": len(ready_hotels),
        "ready_keys": [h["identity_key"] for h in ready_hotels],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

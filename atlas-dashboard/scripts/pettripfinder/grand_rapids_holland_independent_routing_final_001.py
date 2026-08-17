"""PTF-GRAND-RAPIDS-HOLLAND-INDEPENDENT-ROUTING-FINAL-001.

This final routing lane is limited to the fixed 17 identities from the
post-closure review. It records only property-level route identity evidence;
it never reads or stores pet-policy content.
"""
from __future__ import annotations

import json
from pathlib import Path

MARKET = "grand-rapids-holland-mi"
AS_OF = "2026-08-17"
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
POSTCLOSURE = PACKAGE / "grand_rapids_holland_postclosure_census_review_001.json"
OUTPUT = PACKAGE / "grand_rapids_holland_independent_routing_final_001.json"
QUEUE = PACKAGE / "grand_rapids_holland_capture_ready_queue_002.json"
CAPTURE_BATCH = PACKAGE / "grand_rapids_holland_claude_capture_batch_001.json"

# Every entry below was checked against its exact fixed-census address. Empty
# URLs are intentional fail-closed outcomes after checking for an exact,
# property-owned current domain; directory and OTA pages are not routes.
DECISIONS = {
    "Brikcrete Motel": ("PROPERTY_LEVEL_ROUTE_CONFIRMED", "https://www.brikcretewyomingmi.com/",
                         "Property-owned site names Brikcrete Motel and binds 4721 South Division Ave, Wyoming, MI 49548 and phone 616-532-3657."),
    "Budgetel Inn & Suites Hotel": ("PROPERTY_LEVEL_ROUTE_CONFIRMED", "https://www.budgetel.com/hotel-details/bi-grand-rapids-mi",
                                     "Official Budgetel property page names its Grand Rapids hotel and binds 35 28th St SW, Grand Rapids, MI 49548 and phone 616-452-5141."),
    "Casa Via Motel": ("ROUTING_UNRESOLVED", "",
                        "The exact census address is corroborated by local government records, but no current property-owned domain was established; directory evidence is not routing authority."),
    "CityFlatsHotel Grand Rapids": ("PROPERTY_LEVEL_ROUTE_CONFIRMED", "https://cityflatshotel.com/",
                                     "Property-owned CityFlatsHotel site identifies its Grand Rapids hotel; its current official brand page corroborates 83 Monroe Center NW, Grand Rapids, MI 49503."),
    "Grand Rapids Inn": ("PROPERTY_LEVEL_ROUTE_CONFIRMED", "https://www.grandrapidsinn.com/",
                          "Property-owned site names Grand Rapids Inn and binds 250 28th St SW, Grand Rapids, MI 49548 and phone 616-452-2131."),
    "Grandmark Lodging": ("ROUTING_UNRESOLVED", "",
                          "No current property-owned domain was established for the exact 3300 28th St SW, Grandville, MI 49418 identity; third-party listings cannot become a route."),
    "Haworth Hotel at Hope College": ("PROPERTY_LEVEL_ROUTE_CONFIRMED", "https://haworthhotel.com/",
                                      "Property-owned Haworth Hotel site binds the hotel to 225 College Ave, Holland, MI 49423 and phone 616-395-7200."),
    "Jim Williams Motel": ("ROUTING_UNRESOLVED", "",
                           "No current property-owned domain was established for the exact 3821 South Division Ave, Wyoming, MI 49548 identity; directory evidence is not routing authority."),
    "Knights Inn Grand Rapids": ("PROPERTY_LEVEL_ROUTE_CONFIRMED", "https://www.knightsinn.com/us/mi/grand-rapids/knights-inn-grand-rapids",
                                  "Official Knights Inn property page names the Grand Rapids hotel and binds 3524 28th St SE, Grand Rapids, MI 49512 and phone 616-323-3000."),
    "Lazy T Motel": ("ROUTING_UNRESOLVED", "",
                     "No current property-owned domain was established for the exact 3370 Plainfield Ave NE, Grand Rapids, MI 49525 identity; directory evidence is not routing authority."),
    "Plainfield Motel": ("ROUTING_UNRESOLVED", "",
                          "No current property-owned domain was established for the exact 3709 Plainfield Ave NE, Grand Rapids, MI 49525 identity; directory evidence is not routing authority."),
    "Pleasant Motel": ("ROUTING_UNRESOLVED", "",
                        "No current property-owned domain was established for the exact 171 28th St SE, Grand Rapids, MI 49548 identity; directory evidence is not routing authority."),
    "Rainbow Motel": ("ROUTING_UNRESOLVED", "",
                       "No current property-owned domain was established for the exact 2360 South Division Ave, Grand Rapids, MI 49507 identity; similarly named out-of-market motel sites were rejected."),
    "Riviera Motel": ("ROUTING_UNRESOLVED", "",
                       "No current property-owned domain was established for the exact 4350 Remembrance Rd NW, Walker, MI 49534 identity; similarly named out-of-market motel sites were rejected."),
    "Swan Inn Motel": ("PROPERTY_LEVEL_ROUTE_CONFIRMED", "https://www.swaninnmotel.com/",
                        "Property-owned Swan Inn Motel domain is bound by its exact local listing to 5182 Alpine Ave NW, Comstock Park, MI 49321 and phone 616-784-1224."),
    "White Pines Inn & Suites Holland": ("PROPERTY_LEVEL_ROUTE_CONFIRMED", "https://www.whitepinesholland.com/",
                                         "Property-owned site names White Pines Inn & Suites of Holland and binds 2888 W Shore Dr, Holland, MI 49424 and phone 616-994-0400."),
    "Wooden Shoe Motel": ("ROUTING_UNRESOLVED", "",
                          "No current property-owned domain was established for the exact 465 US Highway 31, Holland, MI 49423 identity; historic or generic brand links were rejected."),
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dump(path: Path, document) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    review = _load(POSTCLOSURE)
    fixed = [item for item in review["items"]
             if item["proposed_disposition"] == "INDEPENDENT_FINAL_RECOVERY"]
    if len(fixed) != 17 or {item["canonical_name"] for item in fixed} != set(DECISIONS):
        raise SystemExit("independent routing universe is not the fixed 17-row review set")
    items = []
    for item in fixed:
        outcome, official_url, reason = DECISIONS[item["canonical_name"]]
        items.append({
            "identity_key": item["identity_key"], "canonical_name": item["canonical_name"],
            "address": item["address"], "city": item["city"], "postal_code": item["postal_code"],
            "corridor": item["corridor"], "outcome": outcome, "official_url": official_url,
            "identity_signals": (["canonical_name", "street_address", "postal_code", "phone_or_locality"]
                                 if outcome == "PROPERTY_LEVEL_ROUTE_CONFIRMED" else []),
            "reason": reason, "policy_observed": False,
        })
    document = {
        "schema": "ptf-market-independent-routing-final/1.0", "market_id": MARKET,
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-INDEPENDENT-ROUTING-FINAL-001", "as_of": AS_OF,
        "total": len(items), "items": sorted(items, key=lambda row: row["identity_key"]),
    }
    _dump(OUTPUT, document)

    # This active writer writes only the market routing shard and calls the
    # canonical global assembler after the shard mutation.
    from scripts.pettripfinder import grand_rapids_holland_identity_routing_repair_001 as writer
    writer.main()

    queue = _load(QUEUE)
    fresh = sorted((row for row in queue["items"]
                    if row["capture_mode"] == "FRESH_SESSION_REQUIRED"),
                   key=lambda row: row["identity_key"])
    selected = fresh[:25]
    if len(selected) != 25:
        raise SystemExit("first Claude capture batch needs 25 clean fresh-session routes")
    _dump(CAPTURE_BATCH, {
        "schema": "ptf-market-claude-capture-batch/1.0", "market_id": MARKET,
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-INDEPENDENT-ROUTING-FINAL-001",
        "as_of": AS_OF, "count": len(selected), "items": selected,
        "note": "Preparation only. Every row remains NOT_STARTED; no pet-policy content was accessed.",
    })


if __name__ == "__main__":
    main()

"""Apply PTF-GRAND-RAPIDS-HOLLAND-CENSUS-REVIEW-002's five approved holds.

This is deliberately narrow: it rebuilds the existing closed census from its
maintained source tuples, applies only the five current-identity corrections,
and records the first-party routing corroboration.  It never discovers a new
property and never reads pet-policy content.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder import build_grand_rapids_holland_market_001 as factory

MARKET = "grand-rapids-holland-mi"
AS_OF = "2026-08-17"
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
MARKET_CONFIG = PACKAGE / "markets" / f"{MARKET}.json"
OUTPUT = PACKAGE / "grand_rapids_holland_census_review_002.json"

REVIEWS = (
    {
        "prior_canonical_name": "Baymont Inn & Suites by Wyndham Holland",
        "canonical_name": "Baymont by Wyndham Holland",
        "action": "RENAME_IN_PLACE",
        "address": "680 E 24th St", "city": "Holland", "postal_code": "49423",
        "brand": "Wyndham",
        "official_url": "https://www.wyndhamhotels.com/baymont/holland-michigan/baymont-inn-and-suites-holland/overview",
        "evidence": "Current official Wyndham property page binds Baymont by Wyndham Holland to 680 E 24th St, Holland, MI 49423.",
    },
    {
        "prior_canonical_name": "Baymont Inn & Suites Grand Rapids Southeast",
        "canonical_name": "Baymont by Wyndham Grand Rapids Airport",
        "action": "RENAME_IN_PLACE",
        "address": "2873 Kraft Ave SE", "city": "Grand Rapids", "postal_code": "49512",
        "brand": "Wyndham",
        "official_url": "https://www.wyndhamhotels.com/baymont/grand-rapids-michigan/baymont-inn-and-suites-grand-rapids-airport/overview",
        "evidence": "Current official Wyndham property page binds Baymont by Wyndham Grand Rapids Airport to 2873 Kraft Ave SE, Grand Rapids, MI 49512.",
    },
    {
        "prior_canonical_name": "Days Inn & Suites by Wyndham Grand Rapids Near Downtown",
        "canonical_name": "Days Inn & Suites by Wyndham Grand Rapids Near Downtown",
        "action": "ADDRESS_CORRECTION",
        "address": "255A 28th St SW", "city": "Grand Rapids", "postal_code": "49548",
        "brand": "Wyndham",
        "official_url": "https://www.wyndhamhotels.com/days-inn/grand-rapids-michigan/days-inn-and-suites-grand-rapids-near-downtown/overview",
        "evidence": "Current official Wyndham property page retains the census name and binds it to 255A 28th St SW, Grand Rapids, MI 49548.",
    },
    {
        "prior_canonical_name": "Quality Inn Grand Rapids South",
        "canonical_name": "Quality Inn Grand Rapids South-Byron Center",
        "action": "RENAME_IN_PLACE",
        "address": "7625 Caterpillar Ct SW", "city": "Grand Rapids", "postal_code": "49548",
        "brand": "Choice",
        "official_url": "https://www.choicehotels.com/michigan/grand-rapids/quality-inn-hotels/mi312",
        "evidence": "Current official Choice property page binds Quality Inn Grand Rapids South-Byron Center to 7625 Caterpillar Ct SW, Grand Rapids, MI 49548.",
    },
    {
        "prior_canonical_name": "TownePlace Suites Grand Rapids South",
        "canonical_name": "TownePlace Suites by Marriott Grand Rapids Wyoming",
        "action": "RENAME_IN_PLACE",
        "address": "5880 Clyde Park Ave SW", "city": "Wyoming", "postal_code": "49509",
        "brand": "Marriott",
        "official_url": "https://www.marriott.com/en-us/hotels/grrtw-towneplace-suites-grand-rapids-wyoming/overview/",
        "evidence": "Current official Marriott property page binds TownePlace Suites by Marriott Grand Rapids Wyoming to 5880 Clyde Park Ave SW, Wyoming, MI 49509.",
    },
)


def _identity_key(name: str) -> str:
    return factory.ptf_identity_key(name)


def _write_json(path: Path, document: object) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    # The source tuples above are maintained by the factory. Rebuilding is the
    # canonical way to keep census, ledger, and partition identity fields in
    # lockstep; it does not change the closed 120-row market universe.
    factory.build()
    census = json.loads((PACKAGE / "identity_census" / f"{MARKET}.json").read_text(encoding="utf-8-sig"))
    active = [item for item in census["hotels"] if item["lodging_state"] == "LODGING_CONFIRMED"]
    if census["count"] != 120 or len(active) != 119:
        raise SystemExit("five-row review changed the fixed census universe")
    by_name = {item["canonical_name"]: item for item in active}
    for review in REVIEWS:
        item = by_name.get(review["canonical_name"])
        if not item:
            raise SystemExit(f"reviewed identity missing from rebuilt census: {review['canonical_name']}")
        if (item["address"], item["city"], item["postal_code"]) != (
            review["address"], review["city"], review["postal_code"]
        ):
            raise SystemExit(f"reviewed identity mismatch: {review['canonical_name']}")
        review["identity_key"] = item["identity_key"]

    config = json.loads(MARKET_CONFIG.read_text(encoding="utf-8-sig"))
    id_replacements = {
        _identity_key(item["prior_canonical_name"]): item["identity_key"]
        for item in REVIEWS if item["prior_canonical_name"] != item["canonical_name"]
    }
    for corridor in config["corridors"]:
        corridor["explicit_hotel_ids"] = [id_replacements.get(key, key) for key in corridor["explicit_hotel_ids"]]
    _write_json(MARKET_CONFIG, config)

    document = {
        "schema": "ptf-market-census-review/1.0",
        "market_id": MARKET,
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-CENSUS-REVIEW-002",
        "as_of": AS_OF,
        "census_before": 120,
        "census_after": census["count"],
        "active_lodging_before": 119,
        "active_lodging_after": len(active),
        "items": [
            {
                **review,
                "disposition": review["action"],
                "routing_follow_up": "PROPERTY_LEVEL_ROUTE_CONFIRMED",
                "policy_observed": False,
            }
            for review in REVIEWS
        ],
        "summary": {
            "NO_CENSUS_CHANGE": 0,
            "RENAME_IN_PLACE": 4,
            "ADDRESS_CORRECTION": 1,
            "BRAND_CONVERSION_IN_PLACE": 0,
            "CLOSED_OR_CONVERTED": 0,
            "CONFIRMED_DUPLICATE": 0,
            "IDENTITY_UNRESOLVED": 0,
            "FOUNDER_IDENTITY_REVIEW": 0,
        },
        "note": "Only the five routing-triggered holds were adjudicated. No lodging was added, removed, or policy-reviewed.",
    }
    _write_json(OUTPUT, document)


if __name__ == "__main__":
    main()

"""Build the Phase-1 Grand Rapids--Holland market foundation.

The inventory below is an independent, source-bounded discovery checkpoint,
not a corridor-derived census.  Every source listing reaches a disposition;
no policy page is fetched or interpreted by this module.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, OrderedDict
from pathlib import Path

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

MARKET = "grand-rapids-holland-mi"
WORK_ORDER = "PTF-GRAND-RAPIDS-HOLLAND-MARKET-FACTORY-001"
AS_OF = "2026-08-16"
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"

# name, address, city, zip, phone, source_id, corridor.  These are only the
# individually exposed listings in the listed official destination sources.
CANONICAL = (
    ("Affordable Suites", "2710 E Beltline Ave SE", "Kentwood", "49546", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Comfort Inn Grand Rapids Airport", "4155 28th St SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Courtyard by Marriott Grand Rapids Airport", "4741 28th St SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("DoubleTree by Hilton Grand Rapids Airport", "4747 28th St SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Extended Stay America Select Suites Grand Rapids Kentwood", "3747 29th St SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Fairfield Inn & Suites Grand Rapids", "3930 Stahl Dr SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Holiday Inn Grand Rapids Airport", "3063 Lake Eastbrook Blvd SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Home2 Suites by Hilton Grand Rapids Airport", "4260 Sparks Dr SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Knights Inn Grand Rapids", "3524 28th St SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Residence Inn Grand Rapids Airport", "4443 28th St SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Spark by Hilton Grand Rapids", "4284 29th St SE", "Kentwood", "49512", "616-975-9000", "experience_gr_directory", "grr-airport-kentwood"),
    ("Staybridge Suites Grand Rapids Airport", "3000 Lake Eastbrook Blvd SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Tru by Hilton Grand Rapids Airport", "4570 28th St SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("WoodSpring Suites Grand Rapids Kentwood", "3090 Lake Eastbrook Blvd SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("Wyndham Garden Grand Rapids Airport", "4495 28th St SE", "Kentwood", "49512", "", "experience_gr_kentwood", "grr-airport-kentwood"),
    ("CityFlatsHotel Grand Rapids", "83 Monroe Center NW", "Grand Rapids", "49503", "616-608-1720", "experience_gr_directory", "downtown-grand-rapids"),
    ("Amway Grand Plaza Curio Collection by Hilton", "187 Monroe Ave NW", "Grand Rapids", "49503", "616-774-2000", "experience_gr_directory", "downtown-grand-rapids"),
    ("Holiday Inn Grand Rapids Downtown", "310 Pearl St NW", "Grand Rapids", "49504", "616-235-7611", "experience_gr_directory", "downtown-grand-rapids"),
    ("AC Hotel Grand Rapids Downtown", "50 Monroe Ave NW", "Grand Rapids", "49503", "616-776-3200", "experience_gr_directory", "downtown-grand-rapids"),
    ("Homewood Suites by Hilton Grand Rapids Downtown", "161 Ottawa Ave NW", "Grand Rapids", "49503", "616-451-2300", "experience_gr_directory", "downtown-grand-rapids"),
    ("JW Marriott Grand Rapids", "235 Louis St NW", "Grand Rapids", "49503", "616-242-1500", "experience_gr_directory", "downtown-grand-rapids"),
    ("Residence Inn by Marriott Grand Rapids Downtown", "40 Louis St NW", "Grand Rapids", "49503", "616-776-5905", "experience_gr_directory", "downtown-grand-rapids"),
    ("Fairfield Inn & Suites Grand Rapids North", "620 Center Dr NW", "Walker", "49544", "616-647-0600", "experience_gr_directory", "walker-northwest-grand-rapids"),
    ("Holiday Inn Grand Rapids South", "6569 Clay Ave SW", "Grand Rapids", "49548", "616-871-9700", "experience_gr_directory", "wyoming-grandville"),
    ("Holiday Inn Express Holland", "12381 Felch St", "Holland", "49424", "616-738-2800", "holland_cvb", "holland-zeeland"),
    ("Courtyard by Marriott Holland Downtown", "121 E 8th St", "Holland", "49423", "616-582-8500", "holland_cvb", "holland-zeeland"),
    ("Country Inn & Suites by Radisson Holland", "12260 James St", "Holland", "49424", "616-396-6677", "holland_cvb", "holland-zeeland"),
    ("DoubleTree by Hilton Holland", "650 E 24th St", "Holland", "49423", "616-394-0111", "holland_cvb", "holland-zeeland"),
    ("Haworth Hotel at Hope College", "225 College Ave", "Holland", "49423", "616-395-7200", "holland_cvb", "holland-zeeland"),
    ("Tulyp Tapestry Collection by Hilton", "61 E 7th St", "Holland", "49423", "616-796-2100", "holland_cvb", "holland-zeeland"),
    ("Homewood Suites by Hilton Holland", "625 S Point Hotel Dr", "Holland", "49423", "616-795-0134", "holland_cvb", "holland-zeeland"),
)

NON_CENSUS = (
    ("Sleep Inn & Suites", "4284 29th St SE", "Kentwood", "49512", "experience_gr_kentwood", "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR", "The current Experience GR directory names the same address Spark by Hilton Grand Rapids; retained as a source-name history, not a second property."),
    ("Dutch Colonial Inn", "560 Central Ave", "Holland", "49423", "holland_cvb", "CATEGORY_EXCLUDED", "Official CVB listing identifies this property as a bed and breakfast; the current PetTripFinder hotel category excludes B&Bs."),
    ("Baymont Inn & Suites Grand Haven", "1500 S Beacon Blvd", "Grand Haven", "49417", "visit_grand_haven", "BOUNDARY_EXCLUDED", "Grand Haven is an explicitly reviewed lakeshore destination outside the Grand Rapids--Holland market boundary."),
    ("Delta Hotels Muskegon Convention Center", "939 3rd St", "Muskegon", "49440", "visit_muskegon", "BOUNDARY_EXCLUDED", "Muskegon is an explicitly reviewed independent lakeshore destination outside this market."),
    ("Hotel Saugatuck", "", "Saugatuck", "49453", "saugatuck_douglas_cvb", "BOUNDARY_EXCLUDED", "Saugatuck/Douglas is an explicitly reviewed resort destination, not a corridor extension of Holland."),
    ("Baymont Inn & Suites Conference Center", "", "South Haven", "49090", "visit_south_haven", "BOUNDARY_EXCLUDED", "South Haven is an explicitly reviewed southwest-Michigan destination outside this market."),
)

SOURCES = (
    ("experience_gr_kentwood", "Experience Grand Rapids: Discover Kentwood, MI", "experiencegr.com", "CVB", "Kentwood / GRR", 16, "PARTIAL", "Names, street addresses, and descriptive lodging text; an article-level roster, not a full market directory."),
    ("experience_gr_directory", "Experience Grand Rapids hotel detail listings", "experiencegr.com", "CVB", "Grand Rapids / Walker / Wyoming", 9, "PARTIAL", "Property name, address, phone, and lodging detail pages; dynamic directory pagination is not statically enumerable."),
    ("holland_cvb", "Holland Area Visitors Bureau hotels and meeting venues", "holland.org", "CVB", "Holland", 8, "PARTIAL", "Property name, address, phone, hotel/meeting designation; dynamic lodging list pagination remains unresolved."),
    ("visit_grand_haven", "Grand Haven Area Visitors Bureau hotels and motels", "visitgrandhaven.com", "CVB", "Grand Haven", 1, "PARTIAL", "Explicit boundary-review lead; dynamic directory not used to define the core census."),
    ("visit_muskegon", "Visit Muskegon hotel and motel directory", "visitmuskegon.org", "CVB", "Muskegon", 1, "PARTIAL", "Explicit boundary-review lead; dynamic directory not used to define the core census."),
    ("saugatuck_douglas_cvb", "Saugatuck/Douglas lodging directory", "saugatuck.com", "CVB", "Saugatuck / Douglas", 1, "PARTIAL", "Explicit boundary-review lead; tourism directory distinguishes hotels from rentals and B&Bs."),
    ("visit_south_haven", "Visit South Haven places-to-stay directory", "southhaven.org", "CVB", "South Haven", 1, "PARTIAL", "Explicit boundary-review lead; source itself reports a broader dynamic lodging catalog."),
)


def _slug(name):
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _candidate(name, address, city, postal, phone, source, disposition, reason, corridor=""):
    key = ptf_identity_key(name)
    return OrderedDict((
        ("source_listing_name", name), ("source_id", source),
        ("source_url", ""), ("candidate_canonical_name", name),
        ("identity_key", key), ("address", address), ("city", city),
        ("state", "MI"), ("postal_code", postal), ("phone", phone),
        ("brand", ""), ("property_code", ""), ("official_url", ""),
        ("disposition", disposition), ("reason", reason), ("corridor", corridor),
    ))


def build():
    canonical_candidates = [_candidate(*r[:6], "CANONICAL_CENSUS", "Official destination-source lodging listing.", r[6]) for r in CANONICAL]
    non_census_candidates = [
        _candidate(r[0], r[1], r[2], r[3], "", r[4], r[5], r[6])
        for r in NON_CENSUS
    ]
    candidates = canonical_candidates + non_census_candidates
    source_rows = OrderedDict((
        ("schema", "ptf-market-source-listings/1.0"), ("market_id", MARKET),
        ("as_of", AS_OF), ("count", len(candidates)), ("items", candidates),
    ))
    _dump(PACKAGE / "grand_rapids_holland_source_listings_001.json", source_rows)
    _dump(PACKAGE / "grand_rapids_holland_candidate_ledger_001.json", OrderedDict((
        ("schema", "ptf-market-candidate-ledger/1.0"), ("market_id", MARKET),
        ("work_order", WORK_ORDER), ("raw_listings", len(candidates)),
        ("counts", dict(sorted(Counter(c["disposition"] for c in candidates).items()))),
        ("items", candidates),
    )))
    boundary = [c for c in candidates if c["disposition"] == "BOUNDARY_EXCLUDED"]
    _dump(PACKAGE / "grand_rapids_holland_boundary_review_001.json", OrderedDict((
        ("schema", "ptf-market-boundary-review/1.0"), ("market_id", MARKET),
        ("explicitly_excluded_areas", ["Lansing / East Lansing", "Traverse City / Northwest Michigan", "Kalamazoo / Battle Creek"]),
        ("items", boundary),
        ("area_findings", OrderedDict((
            ("Grand Haven", "BOUNDARY_EXCLUDED: separate lakeshore destination."),
            ("Muskegon", "BOUNDARY_EXCLUDED: separate Muskegon County lakeshore destination."),
            ("Saugatuck / Douglas", "BOUNDARY_EXCLUDED: separate resort destination."),
            ("South Haven", "BOUNDARY_EXCLUDED: separate southwest-Michigan destination."),
        ))),
    )))
    hotels = []
    for c in canonical_candidates:
        hotels.append(OrderedDict((
            ("identity_key", c["identity_key"]), ("canonical_name", c["candidate_canonical_name"]),
            ("slug", _slug(c["candidate_canonical_name"])), ("market_id", MARKET),
            ("address", c["address"]), ("city", c["city"]), ("state", "MI"),
            ("postal_code", c["postal_code"]), ("phone", c["phone"]),
            ("official_url", ""), ("source", c["source_id"]),
            ("identity_state", "IDENTITY_CONFIRMED"), ("lodging_state", "LODGING_CONFIRMED"),
            ("policy_state", "POLICY_NOT_VERIFIED"), ("corridor", "%s__%s" % (MARKET, c["corridor"])),
            ("assignment_basis", "explicit"), ("assignment_value", c["identity_key"]),
            ("collision_state", "NONE"),
        )))
    category = next(c for c in non_census_candidates if c["disposition"] == "CATEGORY_EXCLUDED")
    hotels.append(OrderedDict((
        ("identity_key", category["identity_key"]), ("canonical_name", category["candidate_canonical_name"]),
        ("slug", _slug(category["candidate_canonical_name"])), ("market_id", MARKET),
        ("address", category["address"]), ("city", category["city"]), ("state", "MI"),
        ("postal_code", category["postal_code"]), ("phone", ""), ("official_url", ""),
        ("source", category["source_id"]), ("identity_state", "IDENTITY_CONFIRMED"),
        ("lodging_state", "NOT_LODGING"), ("policy_state", "POLICY_NOT_VERIFIED"),
        ("corridor", ""), ("assignment_basis", "unassigned"), ("assignment_value", ""), ("collision_state", "NONE"),
    )))
    census = OrderedDict((
        ("schema", "ptf-market-identity-census/1.1"), ("market_id", MARKET),
        ("count", len(hotels)), ("work_order", WORK_ORDER),
        ("scope_note", "Independent source-bounded Phase-1 census; corridors classify this output and did not generate it."),
        ("hotels", hotels),
    ))
    _dump(PACKAGE / "identity_census" / (MARKET + ".json"), census)
    items = []
    for row in hotels:
        category_state = row["lodging_state"] == "NOT_LODGING"
        items.append(OrderedDict((
            ("identity_key", row["identity_key"]), ("canonical_name", row["canonical_name"]),
            ("slug", row["slug"]), ("city", row["city"]), ("state", "MI"), ("postal_code", row["postal_code"]),
            ("final_state", "OUT_OF_CURRENT_CATEGORY" if category_state else "AWAITING_OFFICIAL_URL"),
            ("resolved", category_state), ("next_action", "" if category_state else "Obtain an exact first-party property URL without inspecting pet-policy content."),
            ("next_action_source", "" if category_state else "routing/readiness assessment"),
            ("determined_by", WORK_ORDER), ("updated_at", AS_OF), ("official_url", ""), ("state_override_reason", ""),
        )))
    partition = OrderedDict((
        ("schema", "ptf-market-final-partition/1.1"), ("market_id", MARKET),
        ("count", len(items)), ("items", items),
        ("final_state_counts", dict(sorted(Counter(i["final_state"] for i in items).items()))),
    ))
    _dump(PACKAGE / "grand_rapids_holland_final_partition_001.json", partition)
    unresolved = [i for i in items if not i["resolved"]]
    queue = []
    for i in unresolved:
        digest = hashlib.sha256(json.dumps(i, sort_keys=True).encode("utf-8")).hexdigest()
        queue.append(OrderedDict((
            ("identity_key", i["identity_key"]), ("hotel_id", i["identity_key"]),
            ("canonical_name", i["canonical_name"]), ("review_status", "NOT_STARTED"),
            ("next_action", i["next_action"]), ("row_sha256", digest),
        )))
    _dump(REPORTS / (MARKET + "_founder_review_queue.json"), OrderedDict((
        ("schema", "ptf-market-review-queue/1.0"), ("market_id", MARKET), ("count", len(queue)), ("items", queue),
    )))
    routing = []
    for row in hotels:
        if row["lodging_state"] == "NOT_LODGING":
            continue
        routing.append(OrderedDict((
            ("identity_key", row["identity_key"]), ("canonical_name", row["canonical_name"]),
            ("source", row["source"]), ("official_url", ""), ("url_classification", "MISSING_URL"),
            ("routing_ready", False), ("evidence_readiness", "POLICY_SURFACE_UNKNOWN"),
            ("capture_readiness", "NOT_CAPTURE_READY"), ("assessment_status", "ASSESSMENT_ONLY"),
            ("not_routing_authority", True),
        )))
    _dump(REPORTS / (MARKET + "_routing_readiness.json"), OrderedDict((
        ("schema", "ptf-market-routing-assessment/1.0"), ("market_id", MARKET),
        ("summary", {"property_level_urls": 0, "missing_urls": len(routing), "routing_ready": 0, "evidence_ready_estimate": 0, "manual_or_bot_wall": 0}),
        ("items", routing),
    )))
    _dump(PACKAGE / "grand_rapids_holland_capture_ready_queue_001.json", OrderedDict((
        ("schema", "ptf-market-capture-ready/1.0"), ("market_id", MARKET), ("count", 0),
        ("items", []), ("note", "No property-level first-party URL was assessed in this discovery-only pass; no capture was executed."),
    )))
    _dump(REPORTS / (MARKET + "_source_registry.json"), OrderedDict((
        ("schema", "ptf-market-source-registry/1.0"), ("market_id", MARKET),
        ("sources", [OrderedDict((
            ("source_id", s[0]), ("name", s[1]), ("domain", s[2]), ("family", s[3]),
            ("geography", s[4]), ("listings_exposed", s[5]), ("completeness", s[6]), ("fields_exposed", s[7]),
        )) for s in SOURCES]),
    )))
    _dump(REPORTS / (MARKET + "_duplicate_ledger.json"), OrderedDict((
        ("schema", "ptf-market-reconciliation/1.0"), ("market_id", MARKET),
        ("counts", {"raw_listings": len(candidates), "canonical_census": len(hotels), "boundary_excluded": len(boundary), "category_excluded": 1, "source_listing_already_accounted_for": 1, "duplicates": 0, "identity_unresolved": 0, "closed_or_converted": 0}),
        ("items", [c for c in candidates if c["disposition"] != "CANONICAL_CENSUS"]),
    )))


if __name__ == "__main__":
    build()

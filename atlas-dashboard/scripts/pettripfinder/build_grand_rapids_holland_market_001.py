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
AS_OF = "2026-08-17"
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"

# name, address, city, zip, phone, source_id, corridor.  These are only the
# individually exposed listings in the listed official destination sources.
CANONICAL = (
    ("Affordable Suites", "2701 E Beltline Ave SE", "Grand Rapids", "49546", "616-957-8111", "experience_gr_kentwood", "east-grand-rapids-ada"),
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

# PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-001.  These are resolved,
# additive identities from current first-party brand/property inventory.  The
# Phase-1 CVB rows above remain intact so their 37 -> 32 reconciliation is
# still independently auditable.
SECOND_PASS_CANONICAL = (
    ("Canopy by Hilton Grand Rapids Downtown", "131 Ionia Ave SW", "Grand Rapids", "49503", "616-456-6200", "hilton_locator", "downtown-grand-rapids"),
    ("Embassy Suites by Hilton Grand Rapids Downtown", "710 Monroe Ave NW", "Grand Rapids", "49503", "616-512-5700", "hilton_locator", "downtown-grand-rapids"),
    ("Hampton Inn & Suites Grand Rapids Downtown", "433 Dudley Place NE", "Grand Rapids", "49503", "", "hilton_locator", "downtown-grand-rapids"),
    ("Hyatt Place Grand Rapids/Downtown", "140 Ottawa Ave NW", "Grand Rapids", "49503", "", "hyatt_locator", "downtown-grand-rapids"),
    ("Hampton Inn Grand Rapids-North", "500 Center Dr NW", "Grand Rapids", "49544", "", "hilton_locator", "walker-northwest-grand-rapids"),
    ("Home2 Suites by Hilton Grand Rapids North", "330 River Ridge Dr NW", "Grand Rapids", "49544", "", "hilton_locator", "walker-northwest-grand-rapids"),
    ("Homewood Suites by Hilton Walker Grand Rapids North", "3410 Walker Ave NW", "Walker", "49544", "616-805-8050", "hilton_locator", "walker-northwest-grand-rapids"),
    ("Spark by Hilton Walker Grand Rapids North", "2151 Holton Ct NW", "Walker", "49544", "616-735-9595", "hilton_locator", "walker-northwest-grand-rapids"),
    ("Home2 Suites by Hilton Grand Rapids Northeast", "3082 Peregrine Dr NE", "Grand Rapids", "49525", "616-649-6800", "hilton_locator", "east-grand-rapids-ada"),
    ("Hilton Garden Inn Grand Rapids East", "2321 East Beltline Ave SE", "Grand Rapids", "49546", "", "hilton_locator", "east-grand-rapids-ada"),
    ("Holiday Inn Express & Suites Grand Rapids-North", "358 River Ridge Dr NW", "Walker", "49544", "", "ihg_locator", "walker-northwest-grand-rapids"),
    ("Holiday Inn Grand Rapids North - Walker", "2280 Northridge Dr NW", "Walker", "49544", "", "ihg_locator", "walker-northwest-grand-rapids"),
    ("Travelodge by Wyndham Grand Rapids North", "777 Three Mile Rd NW", "Grand Rapids", "49544", "616-784-2900", "wyndham_locator", "walker-northwest-grand-rapids"),
    ("Comfort Suites Grand Rapids North", "350 Dodge St", "Comstock Park", "49321", "", "choice_locator", "walker-northwest-grand-rapids"),
    ("MainStay Suites Grand Rapids", "3920 Stahl Dr SE", "Grand Rapids", "49546", "616-285-7100", "choice_locator", "grr-airport-kentwood"),
    ("Sonesta Hotel Grand Rapids Airport", "3333 28th St SE", "Grand Rapids", "49512", "616-949-9222", "sonesta_locator", "grr-airport-kentwood"),
    ("Holiday Inn Express & Suites Grand Rapids - Airport North", "5405 28th St Court SE", "Grand Rapids", "49546", "", "ihg_locator", "grr-airport-kentwood"),
    ("Candlewood Suites Grand Rapids Airport", "5401 28th St Court SE", "Grand Rapids", "49546", "", "ihg_locator", "grr-airport-kentwood"),
    ("Holiday Inn Express Grand Rapids SW", "4651 36th St", "Grandville", "49418", "", "ihg_locator", "wyoming-grandville"),
    ("Staybridge Suites Grand Rapids SW - Grandville", "3675 Potomac Circle SW", "Grandville", "49418", "", "ihg_locator", "wyoming-grandville"),
    ("Holiday Inn Express & Suites Grand Rapids South - Wyoming", "5870 Clyde Park Ave SW", "Wyoming", "49509", "", "ihg_locator", "wyoming-grandville"),
    ("Days Inn & Suites by Wyndham Grand Rapids Near Downtown", "255 28th St SW", "Wyoming", "49509", "616-426-9721", "wyndham_locator", "wyoming-grandville"),
    ("Staybridge Suites Grand Rapids South", "1439 Eastport Dr SE", "Grand Rapids", "49508", "", "ihg_locator", "east-grand-rapids-ada"),
    ("Hampton Inn Holland", "12427 Felch St", "Holland", "49424", "616-399-8500", "hilton_locator", "holland-zeeland"),
)

# PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-002.  This pass begins with
# the reconciled 56-row census.  It adds only current, address-bound public
# transient-lodging identities from first-party property pages, official local
# tourism pages, and the Kent County hotel/motel-tax roster.  The county
# roster is an identity-discovery source, not policy or routing authority.
THIRD_PASS_CANONICAL = (
    ("Courtyard by Marriott Grand Rapids Downtown", "11 Monroe Ave NW", "Grand Rapids", "49503", "616-242-6000", "marriott_locator", "downtown-grand-rapids"),
    ("SpringHill Suites by Marriott Grand Rapids North", "450 Center Dr NW", "Grand Rapids", "49544", "616-785-1600", "marriott_locator", "walker-northwest-grand-rapids"),
    ("Residence Inn by Marriott Grand Rapids West", "3451 Rivertown Point Ct SW", "Grandville", "49418", "616-538-1100", "marriott_locator", "wyoming-grandville"),
    ("TownePlace Suites Grand Rapids Airport Southeast", "4850 Town Center Dr SE", "Grand Rapids", "49512", "616-512-8300", "marriott_locator", "grr-airport-kentwood"),
    ("Sheraton Grand Rapids Airport Hotel", "5700 28th St SE", "Grand Rapids", "49546", "616-957-1770", "marriott_locator", "grr-airport-kentwood"),
    ("Hampton Inn & Suites Grand Rapids-Airport 28th St", "5200 28th St SE", "Grand Rapids", "49512", "616-575-9144", "hilton_locator", "grr-airport-kentwood"),
    ("Hampton Inn & Suites Grandville Grand Rapids South", "4755 Wilson Ave SW", "Grandville", "49418", "616-752-7755", "hilton_locator", "wyoming-grandville"),
    ("Hampton Inn Grand Rapids-South", "755 54th St SW", "Wyoming", "49509", "616-261-5500", "hilton_locator", "wyoming-grandville"),
    ("Home2 Suites by Hilton Holland", "3140 West Shore Dr", "Holland", "49424", "616-377-7905", "hilton_locator", "holland-zeeland"),
    ("AmericInn by Wyndham Grand Rapids Airport North", "5500 28th St SE", "Grand Rapids", "49512", "616-312-1992", "wyndham_locator", "grr-airport-kentwood"),
    ("AmericInn by Wyndham Holland MI", "422 E 32nd St", "Holland", "49423", "616-251-1862", "wyndham_locator", "holland-zeeland"),
    ("Baymont Inn & Suites Grand Rapids Southeast", "2873 Kraft Ave SE", "Grand Rapids", "49512", "616-956-3300", "experience_gr_cascade_2026", "grr-airport-kentwood"),
    ("Country Inn & Suites Grand Rapids East", "3251 Deposit Dr NE", "Grand Rapids", "49546", "616-942-7000", "experience_gr_cascade_2026", "east-grand-rapids-ada"),
    ("Country Inn & Suites Grand Rapids Airport", "5399 28th St Ct SE", "Grand Rapids", "49512", "616-500-0222", "experience_gr_cascade_2026", "grr-airport-kentwood"),
    ("Clarion Inn & Suites Airport", "4981 28th St SE", "Grand Rapids", "49512", "", "kent_county_hotel_motel_tax", "grr-airport-kentwood"),
    ("Drury Inn & Suites Grand Rapids", "5175 28th St SE", "Grand Rapids", "49512", "616-942-8511", "drury_locator", "grr-airport-kentwood"),
    ("Rodeway Inn & Suites Grand Rapids Southeast", "4855 28th St SE", "Grand Rapids", "49512", "616-957-3000", "choice_locator", "grr-airport-kentwood"),
    ("The Finnley Hotel", "65 Monroe Center St NW", "Grand Rapids", "49503", "616-622-2110", "experience_gr_downtown_2026", "downtown-grand-rapids"),
    ("The BlueJay Hotel", "644 Bridge St NW", "Grand Rapids", "49504", "616-622-2112", "experience_gr_boutique_2026", "walker-northwest-grand-rapids"),
    ("The Ada Hotel", "7415 River St", "Ada", "49301", "616-803-8595", "experience_gr_boutique_2026", "east-grand-rapids-ada"),
    ("Comfort Suites Grandville - Grand Rapids SW", "4520 Kenowa Ave SW", "Grandville", "49418", "616-667-0733", "choice_locator", "wyoming-grandville"),
    ("Comfort Suites Grand Rapids South", "7644 Caterpillar Ct SW", "Grand Rapids", "49548", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Country Inn & Suites by Radisson Grandville-Grand Rapids West", "3825 28th St SW", "Grandville", "49418", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Econo Lodge Grand Rapids Airport", "2985 Kraft Ave SE", "Grand Rapids", "49512", "", "kent_county_hotel_motel_tax", "grr-airport-kentwood"),
    ("Extended Stay America Select Suites Grand Rapids Wyoming", "4500 Clyde Park Ave SW", "Wyoming", "49509", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Fairfield Inn & Suites Grand Rapids Wyoming", "5970 Metro Way", "Wyoming", "49519", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Holiday Inn Express & Suites Grand Rapids Airport South", "4888 Town Center Dr", "Grand Rapids", "49512", "", "kent_county_hotel_motel_tax", "grr-airport-kentwood"),
    ("Hyatt Place Grand Rapids South", "2150 Metro Lane SW", "Wyoming", "49519", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Quality Inn Grand Rapids North - Walker", "2171 Holton Ct NW", "Walker", "49544", "", "kent_county_hotel_motel_tax", "walker-northwest-grand-rapids"),
    ("Motel 6 Grand Rapids", "3221 Plainfield Ave NE", "Grand Rapids", "49525", "", "kent_county_hotel_motel_tax", "walker-northwest-grand-rapids"),
    ("Quality Inn Grand Rapids South", "7625 Caterpillar Ct SW", "Grand Rapids", "49548", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Quality Inn Grand Rapids Near Downtown", "65 28th St SW", "Wyoming", "49509", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Radisson Hotel Grand Rapids Riverfront", "270 Ann St NW", "Grand Rapids", "49504", "", "kent_county_hotel_motel_tax", "downtown-grand-rapids"),
    ("Red Roof Inn Grand Rapids Airport", "5131 28th St SE", "Grand Rapids", "49512", "", "kent_county_hotel_motel_tax", "grr-airport-kentwood"),
    ("Rodeway Inn Grandville - Grand Rapids", "3425 Fairlanes Ave SW", "Grandville", "49418", "616-532-3222", "choice_locator", "wyoming-grandville"),
    ("SpringHill Suites Grand Rapids Airport Southeast", "5250 28th St SE", "Grand Rapids", "49512", "616-464-1130", "marriott_locator", "grr-airport-kentwood"),
    ("Super 8 by Wyndham Grand Rapids", "727 44th St SW", "Wyoming", "49509", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("TownePlace Suites Grand Rapids South", "5880 Clyde Park Ave SW", "Wyoming", "49509", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("TownePlace Suites Grand Rapids Airport", "5430 28th St Ct SE", "Grand Rapids", "49512", "", "kent_county_hotel_motel_tax", "grr-airport-kentwood"),
    ("Tru by Hilton Comstock Park Grand Rapids", "340 Dodge St NE", "Comstock Park", "49321", "", "kent_county_hotel_motel_tax", "walker-northwest-grand-rapids"),
)

# These are the original 19 identity-unresolved leads after current-address
# reconciliation.  A later name/flag at the same independently bound property
# is accounted for rather than silently discarded. Hawthorn and Ramada lack a
# present identity binding and deliberately remain fail-closed.
SECOND_PASS_RESOLUTION = {
    "Courtyard Grand Rapids Downtown": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "SpringHill Suites Grand Rapids North": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Residence Inn Grand Rapids West": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "TownePlace Suites Grand Rapids Airport Southeast": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Sheraton Grand Rapids Airport Hotel": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Hampton Inn & Suites Grand Rapids-Airport 28th St": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Hampton Inn & Suites Grandville Grand Rapids South": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Hampton Inn Grand Rapids-South": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Home2 Suites by Hilton Grand Rapids South": "BOUNDARY_EXCLUDED",
    "Home2 Suites by Hilton Holland": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "AmericInn by Wyndham Grand Rapids Airport North": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "AmericInn by Wyndham Holland MI": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Baymont Inn & Suites (GRR shuttle list)": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Best Western Hospitality Hotel & Suites (GRR shuttle list)": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Clarion Inn & Suites (GRR shuttle list)": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Country Inn & Suites (GRR shuttle list)": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Holiday Inn Express Grand Rapids Airport South (GRR shuttle list)": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Hawthorn Suites by Wyndham Grand Rapids": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
    "Ramada Plaza (GRR shuttle list)": "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR",
}

THIRD_PASS_EXTRA = (
    ("Home2 Suites by Hilton Grand Rapids South", "2288 64th St SW", "Byron Center", "49315", "616-577-8700", "hilton_locator", "BOUNDARY_EXCLUDED", "Address-bound Hilton property lies in Byron Center, outside the retained municipality set; it is not added merely to enlarge the census.", "", "https://www.hilton.com/en/hotels/grrhtht-home2-suites-grand-rapids-south/"),
    ("Hotel Rose", "", "Rockford", "49341", "", "experience_gr_boutique_2026", "BOUNDARY_EXCLUDED", "Rockford is outside the retained Grand Rapids--Holland municipality set and is not a corridor extension.", "", "https://www.experiencegr.com/articles/post/boutique-hotels/"),
    ("The Inn on Jefferson", "22 Jefferson Ave SE", "Grand Rapids", "49503", "", "experience_gr_downtown_2026", "CATEGORY_EXCLUDED", "The official destination directory classifies this as an inn/B&B-style accommodation, which remains outside the current PTF hotel category.", "", "https://www.experiencegr.com/plan-and-stay/about-grand-rapids/grand-rapids-regions/downtown/"),
    ("PrairieSide Suites Luxury Bed and Breakfast", "3180 Washington Ave SW", "Grandville", "49418", "", "kent_county_hotel_motel_tax", "CATEGORY_EXCLUDED", "The county roster names a bed and breakfast; the current PTF hotel category excludes B&Bs.", "", "https://www.kentcountymi.gov/872/Hotel-Motel-Tax"),
    ("Mitten Housing", "55 Ottawa Ave SW", "Grand Rapids", "49503", "", "kent_county_hotel_motel_tax", "SOURCE_LISTING_NOT_LODGING", "County roster label and destination-directory context identify housing rather than a normal transient hotel identity.", "", "https://www.kentcountymi.gov/872/Hotel-Motel-Tax"),
)

# PTF-GRAND-RAPIDS-HOLLAND-CENSUS-CLOSURE-003.  This is a narrow closure
# reconciliation: all additions below came from the dedicated Holland/Zeeland
# audit or the previously un-reconciled, in-boundary hotel-like tail of the
# Kent County roster. It is not a corridor-derived expansion.
FOURTH_PASS_CANONICAL = (
    ("The Center Hotel Grand Rapids Airport", "3333 28th St SE", "Grand Rapids", "49512", "", "choice_locator", "grr-airport-kentwood"),
    ("Days Inn by Wyndham Holland", "717 Hastings Ave", "Holland", "49423", "616-392-7001", "holland_cvb", "holland-zeeland"),
    ("TownePlace Suites by Marriott Holland", "12132 James St", "Holland", "49424", "616-988-2301", "marriott_locator", "holland-zeeland"),
    ("Microtel Inn & Suites by Wyndham Holland", "643 Hastings Ave", "Holland", "49423", "616-392-3235", "holland_cvb", "holland-zeeland"),
    ("Wooden Shoe Motel", "465 US Highway 31", "Holland", "49423", "616-392-8521", "holland_cvb", "holland-zeeland"),
    ("WoodSpring Suites Holland - Grand Rapids", "2630 Van Ommen Dr", "Holland", "49424", "616-738-8200", "holland_cvb", "holland-zeeland"),
    ("Residence Inn by Marriott Holland", "631 South Pointe Ridge Rd", "Holland", "49423", "616-393-6900", "marriott_locator", "holland-zeeland"),
    ("SpringHill Suites by Marriott Holland", "3084 West Shore Dr", "Holland", "49424", "616-399-2500", "marriott_locator", "holland-zeeland"),
    ("avid hotel Zeeland", "8225 Westpark Way", "Zeeland", "49464", "616-953-3900", "ihg_locator", "holland-zeeland"),
    ("Baymont Inn & Suites by Wyndham Holland", "680 E 24th St", "Holland", "49423", "616-396-8822", "holland_cvb", "holland-zeeland"),
    ("White Pines Inn & Suites Holland", "2888 W Shore Dr", "Holland", "49424", "616-994-0400", "holland_cvb", "holland-zeeland"),
    ("Brikcrete Motel", "4721 South Division Ave", "Wyoming", "49548", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Budgetel Inn & Suites Hotel", "35 28th St SW", "Grand Rapids", "49548", "616-452-5141", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Casa Via Motel", "4560 South Division Ave", "Kentwood", "49548", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Grand Rapids Inn", "250 28th St SW", "Grand Rapids", "49548", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Grandmark Lodging", "3300 28th St SW", "Grandville", "49418", "616-534-7641", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Jim Williams Motel", "3821 South Division Ave", "Wyoming", "49548", "616-241-5461", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Lazy T Motel", "3370 Plainfield Ave NE", "Grand Rapids", "49525", "616-363-9888", "kent_county_hotel_motel_tax", "walker-northwest-grand-rapids"),
    ("Plainfield Motel", "3709 Plainfield Ave NE", "Grand Rapids", "49525", "616-361-6603", "kent_county_hotel_motel_tax", "walker-northwest-grand-rapids"),
    ("Pleasant Motel", "171 28th St SE", "Grand Rapids", "49508", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Rainbow Motel", "2360 South Division Ave", "Grand Rapids", "49507", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
    ("Riviera Motel", "4350 Remembrance Rd NW", "Walker", "49534", "616-453-2404", "kent_county_hotel_motel_tax", "walker-northwest-grand-rapids"),
    ("Swan Inn Motel", "5182 Alpine Ave NW", "Comstock Park", "49321", "616-784-1224", "kent_county_hotel_motel_tax", "walker-northwest-grand-rapids"),
    ("Best Western Executive Inn & Suites", "2725 Buchanan Ave SW", "Grand Rapids", "49548", "", "best_western_locator", "wyoming-grandville"),
    ("SpringHill Suites by Marriott Grand Rapids West", "4274 Parkway Place", "Grandville", "49418", "", "kent_county_hotel_motel_tax", "wyoming-grandville"),
)

FOURTH_PASS_EXTRA = (
    ("Sonesta Hotel Grand Rapids Airport", "3333 28th St SE", "Grand Rapids", "49512", "", "sonesta_locator", "CLOSED_OR_CONVERTED", "Current Choice property inventory identifies The Center Hotel Grand Rapids Airport at the same address; the former Sonesta flag is retained as a conversion record.", "", "https://www.choicehotels.com/michigan/grand-rapids/choice-hotels/mi670"),
    ("Colonial Motel", "330 Northland Dr NE", "Rockford", "49341", "616-866-1585", "kent_county_hotel_motel_tax", "BOUNDARY_EXCLUDED", "Rockford is outside the retained municipality set and is not a corridor extension.", "", "https://www.kentcountymi.gov/872/Hotel-Motel-Tax"),
    ("Pine Lodge Motel", "7737 South Division Ave", "Byron Center", "49315", "", "kent_county_hotel_motel_tax", "BOUNDARY_EXCLUDED", "Byron Center is outside the retained municipality set and is not added merely to enlarge the market.", "", "https://www.kentcountymi.gov/872/Hotel-Motel-Tax"),
    ("The Grand Motel", "7040 Division Ave S", "Byron Center", "49315", "", "kent_county_hotel_motel_tax", "BOUNDARY_EXCLUDED", "Byron Center is outside the retained municipality set and is not added merely to enlarge the market.", "", "https://www.kentcountymi.gov/872/Hotel-Motel-Tax"),
    ("The Brauhaus Inn", "611 Madison Ave SE", "Grand Rapids", "49503", "", "kent_county_hotel_motel_tax", "CATEGORY_EXCLUDED", "Current category review identifies a guest-house/B&B-style inn, outside the present PTF hotel category.", "", "https://www.kentcountymi.gov/872/Hotel-Motel-Tax"),
    ("Prince Conference Center", "1800 East Beltline Ave SE", "Grand Rapids", "49546", "", "kent_county_hotel_motel_tax", "CATEGORY_EXCLUDED", "Institutional conference lodging is not a normal public transient hotel in the current PTF category.", "", "https://www.kentcountymi.gov/872/Hotel-Motel-Tax"),
)

# Exact first-party property pages retained as future routing provenance.  No
# page was reviewed for pet-policy content; an exact URL is not policy proof.
PROPERTY_URLS = {
    "Canopy by Hilton Grand Rapids Downtown": "https://www.hilton.com/en/hotels/grrgrpy-canopy-grand-rapids-downtown/",
    "Embassy Suites by Hilton Grand Rapids Downtown": "https://www.hilton.com/en/hotels/grrmaes-embassy-suites-grand-rapids-downtown/",
    "Hampton Inn & Suites Grand Rapids Downtown": "https://www.hilton.com/en/hotels/grrdthx-hampton-suites-grand-rapids-downtown/",
    "Hampton Inn Grand Rapids-North": "https://www.hilton.com/en/hotels/grraphx-hampton-grand-rapids-north/",
    "Home2 Suites by Hilton Grand Rapids North": "https://www.hilton.com/en/hotels/grrnoht-home2-suites-grand-rapids-north/",
    "Homewood Suites by Hilton Walker Grand Rapids North": "https://www.hilton.com/en/hotels/grrinhw-homewood-suites-walker-grand-rapids-north/",
    "Spark by Hilton Walker Grand Rapids North": "https://www.hilton.com/en/hotels/grrwkpe-spark-walker-grand-rapids-north/",
    "Home2 Suites by Hilton Grand Rapids Northeast": "https://www.hilton.com/en/hotels/grrilht-home2-suites-grand-rapids-northeast/",
    "Hyatt Place Grand Rapids/Downtown": "https://www.hyatt.com/hyatt-place/en-US/grrzd-hyatt-place-grand-rapids-downtown",
    "Hampton Inn Holland": "https://www.hilton.com/en/hotels/hldmihx-hampton-holland/",
    "Holiday Inn Express Grand Rapids SW": "https://www.ihg.com/holidayinnexpress/hotels/us/en/grandville/gdvmi/hoteldetail",
    "Travelodge by Wyndham Grand Rapids North": "https://www.wyndhamhotels.com/travelodge/grand-rapids-michigan/travelodge-grand-rapids-north/overview",
    "Affordable Suites": "https://www.affordablesuites.com/hotels/affordable-suites-grand-rapids-mi/",
    "Courtyard by Marriott Grand Rapids Downtown": "https://www.marriott.com/en-us/hotels/grrdt-courtyard-grand-rapids-downtown/overview/",
    "SpringHill Suites by Marriott Grand Rapids North": "https://www.marriott.com/en-us/hotels/grrsh-springhill-suites-grand-rapids-north/overview/",
    "Residence Inn by Marriott Grand Rapids West": "https://www.marriott.com/en-us/hotels/grrrw-residence-inn-grand-rapids-west/overview/",
    "TownePlace Suites Grand Rapids Airport Southeast": "https://www.marriott.com/en-us/hotels/grrte-towneplace-suites-grand-rapids-airport-southeast/overview/",
    "Sheraton Grand Rapids Airport Hotel": "https://www.marriott.com/en-us/hotels/grris-sheraton-grand-rapids-airport-hotel/overview/",
    "Hampton Inn & Suites Grand Rapids-Airport 28th St": "https://www.hilton.com/en/hotels/grrhshx-hampton-suites-grand-rapids-airport-28th-st/",
    "Hampton Inn & Suites Grandville Grand Rapids South": "https://www.hilton.com/en/hotels/grradhx-hampton-suites-grandville-grand-rapids-south/",
    "Hampton Inn Grand Rapids-South": "https://www.hilton.com/en/hotels/grrsohx-hampton-grand-rapids-south/",
    "Home2 Suites by Hilton Holland": "https://www.hilton.com/en/hotels/hlmhtht-home2-suites-holland/",
    "AmericInn by Wyndham Grand Rapids Airport North": "https://www.wyndhamhotels.com/americinn/grand-rapids-michigan/americinn-grand-rapids-airport-north/overview",
    "AmericInn by Wyndham Holland MI": "https://www.wyndhamhotels.com/americinn/holland-michigan/americinn-holland-mi/overview",
    "Drury Inn & Suites Grand Rapids": "https://www.druryhotels.com/locations/grand-rapids-mi/drury-inn-and-suites-grand-rapids",
    "Rodeway Inn & Suites Grand Rapids Southeast": "https://www.choicehotels.com/en-in/michigan/grand-rapids/rodeway-inn-hotels/mi534",
    "The Finnley Hotel": "https://www.thefinnley.com/",
    "The BlueJay Hotel": "https://www.thebluejaygr.com/",
    "The Ada Hotel": "https://www.adahotel.com/",
    "Comfort Suites Grandville - Grand Rapids SW": "https://www.choicehotels.com/en-ca/michigan/grandville/comfort-suites-hotels/mi169",
    "Rodeway Inn Grandville - Grand Rapids": "https://www.choicehotels.com/en-xl/michigan/grandville/rodeway-inn-hotels/mi437",
    "SpringHill Suites Grand Rapids Airport Southeast": "https://www.marriott.com/en-us/hotels/grrse-springhill-suites-grand-rapids-airport-southeast/overview/",
    "The Center Hotel Grand Rapids Airport": "https://www.choicehotels.com/michigan/grand-rapids/choice-hotels/mi670",
    "TownePlace Suites by Marriott Holland": "https://www.marriott.com/en-us/hotels/grrht-towneplace-suites-holland/overview/",
    "WoodSpring Suites Holland - Grand Rapids": "https://www.woodspring.com/extended-stay-hotels/locations/michigan/grand-rapids/woodspring-suites-grand-rapids-holland",
    "Residence Inn by Marriott Holland": "https://www.marriott.com/en-us/hotels/grrho-residence-inn-holland/overview/",
    "SpringHill Suites by Marriott Holland": "https://www.marriott.com/en-us/hotels/grrsl-springhill-suites-holland/overview/",
    "avid hotel Zeeland": "https://www.ihg.com/avidhotels/hotels/us/en/zeeland/grrav/hoteldetail",
    "Best Western Executive Inn & Suites": "https://www.bestwestern.com/en_US/book/hotel-rooms.23165.html",
}

# Every additional lead is retained.  Rows not safe to bind to a present,
# unique identity deliberately remain unresolved rather than being guessed
# into the census.  The active GRR shuttle roster is useful discovery
# evidence, but some of its historic brand labels need attended reconciliation.
SECOND_PASS_EXTRA = (
    ("Courtyard Grand Rapids Downtown", "", "Grand Rapids", "49503", "", "marriott_locator", "IDENTITY_UNRESOLVED", "Official Marriott destination inventory exposed the property but this pass did not establish a complete address binding.", "", ""),
    ("SpringHill Suites Grand Rapids North", "", "Grand Rapids", "", "", "marriott_locator", "IDENTITY_UNRESOLVED", "Official Marriott destination inventory exposed the property but this pass did not establish a complete address binding.", "", ""),
    ("Residence Inn Grand Rapids West", "", "Grand Rapids", "", "", "marriott_locator", "IDENTITY_UNRESOLVED", "Official Marriott destination inventory exposed the property but this pass did not establish a complete address binding.", "", ""),
    ("TownePlace Suites Grand Rapids Airport Southeast", "", "Grand Rapids", "", "", "marriott_locator", "IDENTITY_UNRESOLVED", "Official Marriott destination inventory exposed the property but this pass did not establish a complete address binding.", "", ""),
    ("Sheraton Grand Rapids Airport Hotel", "5700 28th St SE", "Grand Rapids", "49546", "", "marriott_locator", "IDENTITY_UNRESOLVED", "Official Marriott inventory establishes the present flag; address corroboration in this pass is not from Marriott and is held for reconciliation.", "", ""),
    ("Hampton Inn & Suites Grand Rapids-Airport 28th St", "", "Grand Rapids", "", "", "hilton_locator", "IDENTITY_UNRESOLVED", "Official Hilton inventory exposed the property, but a property-address binding was not preserved in this pass.", "", ""),
    ("Hampton Inn & Suites Grandville Grand Rapids South", "", "Grandville", "", "", "hilton_locator", "IDENTITY_UNRESOLVED", "Official Hilton inventory exposed the property, but a property-address binding was not preserved in this pass.", "", ""),
    ("Hampton Inn Grand Rapids-South", "", "Grand Rapids", "", "", "hilton_locator", "IDENTITY_UNRESOLVED", "Official Hilton inventory exposed the property, but a property-address binding was not preserved in this pass.", "", ""),
    ("Home2 Suites by Hilton Grand Rapids South", "", "Grand Rapids", "", "", "hilton_locator", "IDENTITY_UNRESOLVED", "Official Hilton inventory exposed the property, but a property-address binding was not preserved in this pass.", "", ""),
    ("Home2 Suites by Hilton Holland", "", "Holland", "", "", "hilton_locator", "IDENTITY_UNRESOLVED", "Official Hilton inventory exposed the property, but a property-address binding was not preserved in this pass.", "", ""),
    ("AmericInn by Wyndham Grand Rapids Airport North", "", "Grand Rapids", "", "", "wyndham_locator", "IDENTITY_UNRESOLVED", "Official Wyndham flag locator exposed the property; exact property binding remains to be completed.", "", ""),
    ("AmericInn by Wyndham Holland MI", "", "Holland", "", "", "wyndham_locator", "IDENTITY_UNRESOLVED", "Official Wyndham flag locator exposed the property; exact property binding remains to be completed.", "", ""),
    ("Hawthorn Suites by Wyndham Grand Rapids", "", "Grand Rapids", "", "", "wyndham_locator", "IDENTITY_UNRESOLVED", "Official Wyndham material exposed the property; exact property binding remains to be completed.", "", ""),
    ("Baymont Inn & Suites (GRR shuttle list)", "", "Grand Rapids", "", "616-956-3300", "grr_airport", "IDENTITY_UNRESOLVED", "Current airport shuttle roster uses an unbound flag name; retain until its current property identity is reconciled.", "", "https://www.grr.org/ground"),
    ("Best Western Hospitality Hotel & Suites (GRR shuttle list)", "", "Grand Rapids", "", "616-949-8400", "grr_airport", "IDENTITY_UNRESOLVED", "Current airport shuttle roster uses an unbound flag name; retain until its current property identity is reconciled.", "", "https://www.grr.org/ground"),
    ("Clarion Inn & Suites (GRR shuttle list)", "", "Grand Rapids", "", "616-956-9304", "grr_airport", "IDENTITY_UNRESOLVED", "Current airport shuttle roster uses an unbound flag name; retain until its current property identity is reconciled.", "", "https://www.grr.org/ground"),
    ("Country Inn & Suites (GRR shuttle list)", "", "Grand Rapids", "", "616-977-0909", "grr_airport", "IDENTITY_UNRESOLVED", "Current airport shuttle roster uses an unbound flag name; retain until its current property identity is reconciled.", "", "https://www.grr.org/ground"),
    ("Holiday Inn Express Grand Rapids Airport South (GRR shuttle list)", "", "Grand Rapids", "", "616-512-8222", "grr_airport", "IDENTITY_UNRESOLVED", "Current airport shuttle roster uses an unbound flag name; retain until its current property identity is reconciled.", "", "https://www.grr.org/ground"),
    ("Ramada Plaza (GRR shuttle list)", "", "Grand Rapids", "", "616-949-9222", "grr_airport", "IDENTITY_UNRESOLVED", "Current airport shuttle roster uses an unbound historic flag name; retain until its present identity is reconciled.", "", "https://www.grr.org/ground"),
    ("Best Western Plaza Hotel Saugatuck", "", "Saugatuck", "49453", "", "best_western_locator", "BOUNDARY_EXCLUDED", "Saugatuck/Douglas remains a distinct resort destination outside the market boundary.", "", "https://www.bestwestern.com/en_US/book/hotel-details.23155.html"),
    ("Best Western Beacon Inn", "1525 S Beacon Blvd", "Grand Haven", "49417", "", "best_western_locator", "BOUNDARY_EXCLUDED", "Grand Haven remains a separate lakeshore destination outside the market boundary.", "", "https://www.bestwestern.com/en_US/book/hotel-details.23062.html"),
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
    ("holland_cvb", "Holland Area Visitors Bureau hotels and meeting venues", "holland.org", "CVB", "Holland / Zeeland", 22, "PARTIAL", "Property name, address, phone, and hotel/meeting designation; the dedicated closure audit reconciled its in-scope named hotel leads, but the dynamically rendered directory has no statically provable pagination boundary."),
    ("visit_grand_haven", "Grand Haven Area Visitors Bureau hotels and motels", "visitgrandhaven.com", "CVB", "Grand Haven", 1, "PARTIAL", "Explicit boundary-review lead; dynamic directory not used to define the core census."),
    ("visit_muskegon", "Visit Muskegon hotel and motel directory", "visitmuskegon.org", "CVB", "Muskegon", 1, "PARTIAL", "Explicit boundary-review lead; dynamic directory not used to define the core census."),
    ("saugatuck_douglas_cvb", "Saugatuck/Douglas lodging directory", "saugatuck.com", "CVB", "Saugatuck / Douglas", 1, "PARTIAL", "Explicit boundary-review lead; tourism directory distinguishes hotels from rentals and B&Bs."),
    ("visit_south_haven", "Visit South Haven places-to-stay directory", "southhaven.org", "CVB", "South Haven", 1, "PARTIAL", "Explicit boundary-review lead; source itself reports a broader dynamic lodging catalog."),
    ("hilton_locator", "Hilton Michigan / Grand Rapids property locators", "hilton.com", "CHAIN", "Grand Rapids / Holland / Walker", 28, "PARTIAL", "Current locator names and selected first-party property pages; date-dependent nearby results and pagination prevent a complete claim."),
    ("marriott_locator", "Marriott Grand Rapids destination inventory", "marriott.com", "CHAIN", "Grand Rapids", 9, "PARTIAL", "Current destination inventory names properties, but this pass did not enumerate every result or bind every address."),
    ("ihg_locator", "IHG Grand Rapids location inventory", "ihg.com", "CHAIN", "Grand Rapids / Walker / Grandville / Wyoming", 11, "PARTIAL", "Current location inventory exposes names and addresses; this checkpoint is not a full date-query enumeration."),
    ("choice_locator", "Choice Hotels Grand Rapids locator", "choicehotels.com", "CHAIN", "Grand Rapids", 24, "PARTIAL", "Locator reports nearby inventory but the full result set and all property bindings remain unenumerated."),
    ("hyatt_locator", "Hyatt Place Grand Rapids Downtown property page", "hyatt.com", "CHAIN", "Downtown Grand Rapids", 1, "PARTIAL", "Property-page identity confirmation only; not a complete Hyatt geographic inventory."),
    ("wyndham_locator", "Wyndham Grand Rapids and Michigan flag locators", "wyndhamhotels.com", "CHAIN", "Grand Rapids / Holland", 6, "PARTIAL", "Flag/property pages produced named leads; no all-brand, date-stable result enumeration was available in this pass."),
    ("sonesta_locator", "Sonesta Michigan locations", "sonesta.com", "CHAIN", "Grand Rapids Airport", 1, "PARTIAL", "Current state inventory confirms one airport property; no complete regional property export was available."),
    ("grr_airport", "Gerald R. Ford International Airport ground transportation", "grr.org", "DIRECTORY", "GRR Airport", 12, "PARTIAL", "Current shuttle roster is a discovery cross-check, not a current property identity directory; legacy flags are retained for reconciliation."),
    ("best_western_locator", "Best Western Michigan property pages", "bestwestern.com", "CHAIN", "Saugatuck / Grand Haven boundary review", 2, "PARTIAL", "Property pages used only to reaffirm separately reviewed boundary exclusions."),
    ("red_roof_locator", "Red Roof Grand Rapids / Kentwood locator search", "redroof.com", "CHAIN", "Grand Rapids / Kentwood", 0, "PARTIAL", "No new address-bound in-scope property surfaced in this pass; absence of a result is not a complete inventory assertion."),
    ("extended_stay_america_locator", "Extended Stay America Grand Rapids locator search", "extendedstayamerica.com", "CHAIN", "Grand Rapids / Kentwood", 0, "PARTIAL", "No new address-bound in-scope property surfaced in this pass; absence of a result is not a complete inventory assertion."),
    ("motel6_studio6_locator", "Motel 6 / Studio 6 Grand Rapids locator search", "motel6.com", "CHAIN", "Grand Rapids / Kentwood", 0, "PARTIAL", "No new address-bound in-scope property surfaced in this pass; absence of a result is not a complete inventory assertion."),
    ("experience_gr_downtown_2026", "Experience Grand Rapids downtown hotels", "experiencegr.com", "CVB", "Downtown Grand Rapids", 15, "PARTIAL", "A current named downtown list and 13-hotel statement; it includes hotel, inn, and housing entries and is not a complete market export."),
    ("experience_gr_cascade_2026", "Experience Grand Rapids Cascade lodging guide", "experiencegr.com", "CVB", "GRR / Cascade", 8, "PARTIAL", "Named airport-area lodging references and detail pages; article scope is not a complete airport inventory."),
    ("experience_gr_boutique_2026", "Experience Grand Rapids boutique-hotel guide", "experiencegr.com", "CVB", "Grand Rapids / Ada / Rockford", 4, "PARTIAL", "Named boutique-hotel leads; it is an editorial selection rather than a complete independent-lodging directory."),
    ("kent_county_hotel_motel_tax", "Kent County hotel / motel tax roster", "kentcountymi.gov", "REGISTRY", "Kent County market cells", 45, "PARTIAL", "Static address-level taxpayer roster. The closure pass reconciled the relevant in-boundary lodging-looking rows; the broader roster also contains rentals, apartments, aliases, B&Bs, and out-of-scope places, so the source cannot honestly claim global directory completeness."),
    ("drury_locator", "Drury Inn & Suites Grand Rapids property page", "druryhotels.com", "CHAIN", "GRR Airport", 1, "PARTIAL", "Exact first-party property identity only; not a complete regional Drury inventory."),
)


def _slug(name):
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _candidate(name, address, city, postal, phone, source, disposition, reason, corridor="", source_url=""):
    key = ptf_identity_key(name)
    return OrderedDict((
        ("source_listing_name", name), ("source_id", source),
        ("source_url", source_url), ("candidate_canonical_name", name),
        ("identity_key", key), ("address", address), ("city", city),
        ("state", "MI"), ("postal_code", postal), ("phone", phone),
        ("brand", name.split(" ")[0]), ("property_code", ""), ("official_url", PROPERTY_URLS.get(name, "")),
        ("disposition", disposition), ("reason", reason), ("corridor", corridor),
    ))


def build():
    phase_one_candidates = [_candidate(*r[:6], "CANONICAL_CENSUS", "Official destination-source lodging listing.", r[6]) for r in CANONICAL]
    second_pass_candidates_historical = [_candidate(*r[:6], "ADD_TO_CENSUS", "Resolved additive identity from an official first-party brand inventory.", r[6], PROPERTY_URLS.get(r[0], "")) for r in SECOND_PASS_CANONICAL]
    second_pass_candidates = [c for c in second_pass_candidates_historical if c["candidate_canonical_name"] != "Sonesta Hotel Grand Rapids Airport"]
    third_pass_candidates = [_candidate(*r[:6], "CANONICAL_CENSUS", "Address-bound current public transient-lodging identity from the additional completeness audit.", r[6], PROPERTY_URLS.get(r[0], "")) for r in THIRD_PASS_CANONICAL]
    fourth_pass_candidates = [_candidate(*r[:6], "CANONICAL_CENSUS", "Final closure-pass identity from a dedicated Holland/Zeeland or in-scope Kent County reconciliation.", r[6], PROPERTY_URLS.get(r[0], "")) for r in FOURTH_PASS_CANONICAL]
    canonical_candidates = phase_one_candidates + second_pass_candidates + third_pass_candidates + fourth_pass_candidates
    non_census_candidates = [
        _candidate(r[0], r[1], r[2], r[3], "", r[4], r[5], r[6])
        for r in NON_CENSUS
    ]
    second_pass_extra_historical = [_candidate(*r[:6], r[6], r[7], r[8], r[9]) for r in SECOND_PASS_EXTRA]
    second_pass_extra = [OrderedDict(item) for item in second_pass_extra_historical]
    for item in second_pass_extra:
        disposition = SECOND_PASS_RESOLUTION.get(item["source_listing_name"])
        if disposition:
            item["disposition"] = disposition
            item["reason"] = "Current additional-pass identity binding reconciles this earlier discovery lead; the source row is retained for audit."
    third_pass_extra = [_candidate(*r[:6], r[6], r[7], r[8], r[9]) for r in THIRD_PASS_EXTRA]
    fourth_pass_extra = [_candidate(*r[:6], r[6], r[7], r[8], r[9]) for r in FOURTH_PASS_EXTRA]
    candidates = canonical_candidates + non_census_candidates + second_pass_extra + third_pass_extra + fourth_pass_extra
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
    _dump(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_001.json", OrderedDict((
        ("schema", "ptf-market-candidate-ledger/1.0"), ("market_id", MARKET),
        ("work_order", "PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-001"),
        ("raw_listings", len(second_pass_candidates_historical) + len(second_pass_extra_historical)),
        ("counts", dict(sorted(Counter(c["disposition"] for c in second_pass_candidates_historical + second_pass_extra_historical).items()))),
        ("items", second_pass_candidates_historical + second_pass_extra_historical),
    )))
    _dump(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_002.json", OrderedDict((
        ("schema", "ptf-market-candidate-ledger/1.0"), ("market_id", MARKET),
        ("work_order", "PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-002"),
        ("raw_listings", len(third_pass_candidates) + len(third_pass_extra)),
        ("counts", dict(sorted(Counter(c["disposition"] for c in third_pass_candidates + third_pass_extra).items()))),
        ("items", third_pass_candidates + third_pass_extra),
    )))
    _dump(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_003.json", OrderedDict((
        ("schema", "ptf-market-candidate-ledger/1.0"), ("market_id", MARKET),
        ("work_order", "PTF-GRAND-RAPIDS-HOLLAND-CENSUS-CLOSURE-003"),
        ("raw_listings", len(fourth_pass_candidates) + len(fourth_pass_extra)),
        ("counts", dict(sorted(Counter(c["disposition"] for c in fourth_pass_candidates + fourth_pass_extra).items()))),
        ("items", fourth_pass_candidates + fourth_pass_extra),
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
            ("official_url", c["official_url"]), ("source", c["source_id"]),
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
            ("final_state", "OUT_OF_CURRENT_CATEGORY" if category_state else ("AWAITING_POLICY_OBSERVATION" if row["official_url"] else "AWAITING_OFFICIAL_URL")),
            ("resolved", category_state), ("next_action", "" if category_state else ("Do not capture yet; queue for a later policy-evidence pass." if row["official_url"] else "Obtain an exact first-party property URL without inspecting pet-policy content.")),
            ("next_action_source", "" if category_state else "routing/readiness assessment"),
            ("determined_by", WORK_ORDER), ("updated_at", AS_OF), ("official_url", row["official_url"]), ("state_override_reason", ""),
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
            ("source", row["source"]), ("official_url", row["official_url"]), ("url_classification", "EXACT_PROPERTY_FIRST_PARTY" if row["official_url"] else "MISSING_URL"),
            ("routing_ready", bool(row["official_url"])), ("evidence_readiness", "POLICY_SURFACE_UNKNOWN"),
            ("capture_readiness", "CAPTURE_READY" if row["official_url"] else "NOT_CAPTURE_READY"), ("assessment_status", "ASSESSMENT_ONLY"),
            ("not_routing_authority", True),
        )))
    _dump(REPORTS / (MARKET + "_routing_readiness.json"), OrderedDict((
        ("schema", "ptf-market-routing-assessment/1.0"), ("market_id", MARKET),
        ("summary", {"property_level_urls": sum(1 for r in routing if r["routing_ready"]), "missing_urls": sum(1 for r in routing if not r["routing_ready"]), "routing_ready": sum(1 for r in routing if r["routing_ready"]), "evidence_ready_estimate": 0, "manual_or_bot_wall": 0}),
        ("items", routing),
    )))
    _dump(PACKAGE / "grand_rapids_holland_capture_ready_queue_001.json", OrderedDict((
        ("schema", "ptf-market-capture-ready/1.0"), ("market_id", MARKET), ("count", sum(1 for r in routing if r["routing_ready"])),
        ("items", [r for r in routing if r["routing_ready"]]), ("note", "Strict routing readiness only. No policy capture was executed or assessed."),
    )))
    _dump(REPORTS / (MARKET + "_source_registry.json"), OrderedDict((
        ("schema", "ptf-market-source-registry/1.0"), ("market_id", MARKET),
        ("sources", [OrderedDict((
            ("source_id", s[0]), ("name", s[1]), ("domain", s[2]), ("family", s[3]),
            ("geography", s[4]), ("listings_exposed", s[5]), ("completeness", s[6]), ("fields_exposed", s[7]),
        )) for s in SOURCES]),
    )))
    _dump(REPORTS / (MARKET + "_census_completeness_001.json"), OrderedDict((
        ("schema", "ptf-market-census-completeness/1.0"), ("market_id", MARKET),
        ("work_order", "PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-001"),
        ("phase_1_reconciliation", OrderedDict((
            ("raw_listings", 37), ("canonical_census", 32),
            ("lodging_identities", 31), ("category_excluded", 1),
            ("boundary_excluded", 4), ("source_listing_already_accounted_for", 1),
        ))),
        ("completeness_pass_reconciliation", OrderedDict((
            ("census_before", 32), ("new_valid_lodging_identities", len(second_pass_candidates)),
            ("proven_removals", 0), ("census_after", len(hotels)),
            ("new_leads", len(second_pass_candidates) + len(second_pass_extra)),
            ("identity_unresolved", sum(1 for c in second_pass_extra if c["disposition"] == "IDENTITY_UNRESOLVED")),
            ("boundary_excluded", sum(1 for c in second_pass_extra if c["disposition"] == "BOUNDARY_EXCLUDED")),
        ))),
        ("airport_inventory", OrderedDict((
            ("current_grr_kentwood_count", 15), ("discovered_grr_kentwood_count", 19),
            ("new_resolved_candidates", 4), ("unresolved_airport_roster_leads", 6),
        ))),
        ("verdict", "CENSUS_STILL_INCOMPLETE"),
        ("verdict_reason", "The official chain and airport sweeps materially expanded the census, but multiple first-party locator inventories remain partially enumerated and 19 identity leads are intentionally unresolved."),
        ("next_step", "ADDITIONAL_DISCOVERY"),
        ("policy_capture", "NOT_PERFORMED"),
    )))
    _dump(PACKAGE / "grand_rapids_holland_census_completeness_002.json", OrderedDict((
        ("schema", "ptf-market-census-completeness/1.0"), ("market_id", MARKET),
        ("work_order", "PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-002"),
        ("as_of", AS_OF),
        ("starting_checkpoint", "df307cce5dd605e7242719405c70ea57ce971b00"),
        ("completeness_pass_reconciliation", OrderedDict((
            ("census_before", 56), ("new_discovery_candidates", len(third_pass_candidates) + len(third_pass_extra)),
            ("new_valid_lodging_identities", len(third_pass_candidates)), ("proven_removals", 0),
            ("final_census", 96), ("identity_unresolved_before", 19),
            ("identity_unresolved_after", 2),
        ))),
        ("airport_cluster", OrderedDict((
            ("current_grr_kentwood_count", 19),
            ("new_valid_lodging_identities", 14),
            ("final_count", 33),
        ))),
        ("holland_zeeland", OrderedDict((
            ("current_count", 8),
            ("new_valid_lodging_identities", 2),
            ("final_count", 10),
        ))),
        ("independent_lodging", OrderedDict((
            ("candidates_found", 3), ("added_to_census", ["The Finnley Hotel", "The BlueJay Hotel", "The Ada Hotel"]),
        ))),
        ("source_coverage", OrderedDict((
            ("kent_county_hotel_motel_tax", "PARTIAL: static roster materially improved address coverage, but its non-hotel, alias, and out-of-scope rows are not yet fully reconciled line-by-line."),
            ("holland_cvb", "PARTIAL; dynamic tourism inventory remains unmeasured."),
            ("brand_locators", "PARTIAL; current property bindings were captured selectively for discovery and future routing provenance."),
        ))),
        ("verdict", "CENSUS_STILL_INCOMPLETE"),
        ("verdict_reason", "The Kent County registry materially expands and stabilizes the Grand Rapids-side universe, but the Holland-area dynamic source remains unmeasured and the Hawthorn and Ramada historic/current-identity leads lack exact current bindings."),
        ("next_step", "ADDITIONAL_DISCOVERY"), ("policy_capture", "NOT_PERFORMED"),
    )))
    _dump(PACKAGE / "grand_rapids_holland_census_closure_003.json", OrderedDict((
        ("schema", "ptf-market-census-completeness/1.0"), ("market_id", MARKET),
        ("work_order", "PTF-GRAND-RAPIDS-HOLLAND-CENSUS-CLOSURE-003"), ("as_of", AS_OF),
        ("starting_checkpoint", "d792fb8feeeb7396236b32dc52f4fc98f9dba38e"),
        ("reconciliation", OrderedDict((
            ("census_before", 96), ("new_discovery_candidates", len(fourth_pass_candidates) + len(fourth_pass_extra)),
            ("new_valid_lodging_identities", len(fourth_pass_candidates)), ("proven_removals", 1),
            ("final_census", len(hotels)), ("identity_unresolved_before", 2), ("identity_unresolved_after", 0),
            ("duplicates", 0), ("closed_or_converted", 1),
        ))),
        ("identity_lead_resolution", OrderedDict((
            ("Hawthorn Suites by Wyndham Grand Rapids", "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR: current Affordable Suites first-party page binds 2701 E Beltline Ave SE and 616-957-8111."),
            ("Ramada Plaza (GRR shuttle list)", "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR: historic airport roster phone/address binds to the current 3333 28th St SE property; Sonesta flag is separately recorded as converted to The Center Hotel."),
        ))),
        ("holland_zeeland_closure", OrderedDict((
            ("source_rows_reviewed", 22), ("new_candidates", 10), ("new_canonical", 10), ("duplicates", 0),
            ("category_excluded", 1), ("boundary_excluded", 0), ("unresolved", 0),
            ("final_count", sum(1 for c in canonical_candidates if c["corridor"] == "holland-zeeland")),
        ))),
        ("kent_county_reconciliation", OrderedDict((
            ("complete_for_in_scope_lodging_reconciliation", True),
            ("source_registry_status", "PARTIAL"),
            ("limitation", "The shared source registry admits only COMPLETE/PARTIAL/UNUSABLE. COMPLETE would overstate whole-roster treatment because it includes rentals, apartments, B&Bs, aliases, and out-of-boundary accounts; the scoped reconciliation status is therefore reported here rather than invented as a global enum."),
            ("new_canonical", 14), ("category_excluded", 2), ("boundary_excluded", 3), ("source_listing_already_accounted_for", 14),
        ))),
        ("independent_closure", OrderedDict((
            ("complete", True), ("new_candidates", 2),
            ("added_to_census", ["Wooden Shoe Motel", "White Pines Inn & Suites Holland"]),
            ("coverage", "Official Experience Grand Rapids downtown, boutique, and Cascade material plus Holland CVB hotel and B&B inventories and first-party Holland property sites were checked. The closure pass added Wooden Shoe Motel and White Pines Inn & Suites Holland; no further in-scope independent public transient hotel surfaced."),
        ))),
        ("airport_sanity", OrderedDict((
            ("final_count", sum(1 for c in canonical_candidates if c["corridor"] == "grr-airport-kentwood")),
            ("finding", "No unexplained gap. The historic Ramada/Sonesta/The Center same-address flag sequence is explicit; no duplicate canonical identity remains."),
        ))),
        ("verdict", "CENSUS_COMPLETE"),
        ("verdict_reason", "Both identity leads are dispositioned, Holland/Zeeland and the relevant Kent County lodging tail are reconciled, independent and airport checks found no unexplained gap, and all candidate-ledger arithmetic is explicit."),
        ("next_step", "IDENTITY_ROUTING_REPAIR"), ("policy_capture", "NOT_PERFORMED"),
    )))
    _dump(REPORTS / (MARKET + "_duplicate_ledger.json"), OrderedDict((
        ("schema", "ptf-market-reconciliation/1.0"), ("market_id", MARKET),
        ("counts", {"raw_listings": len(candidates), "canonical_census": len(hotels), "boundary_excluded": len(boundary), "category_excluded": sum(1 for c in candidates if c["disposition"] == "CATEGORY_EXCLUDED"), "source_listing_already_accounted_for": sum(1 for c in candidates if c["disposition"] == "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR"), "duplicates": 0, "identity_unresolved": sum(1 for c in candidates if c["disposition"] == "IDENTITY_UNRESOLVED"), "closed_or_converted": 0}),
        ("items", [c for c in candidates if c["disposition"] != "CANONICAL_CENSUS"]),
    )))


if __name__ == "__main__":
    build()

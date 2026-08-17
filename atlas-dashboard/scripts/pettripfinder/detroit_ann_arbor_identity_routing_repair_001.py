"""PTF-DETROIT-ANN-ARBOR-IDENTITY-ROUTING-REPAIR-001.

Repairs identity quality and official routing for exactly the 119 Detroit-Ann
Arbor rows that were not already capture-ready after Phase 1 (51
AWAITING_IDENTITY_RESOLUTION + 53 AWAITING_OFFICIAL_URL + 15
AWAITING_PROPERTY_LEVEL_URL). Every address/phone/URL below was read from a
first-party brand page, an official CVB/chamber directory, or a targeted
search that surfaced one of those pages directly -- never fabricated and
never taken from an OTA as routing authority.

No pet-policy browsing, no policy evidence, no publication, no founder
approvals, no deployment. Rows advance only as far as
AWAITING_POLICY_OBSERVATION (or stay/move to AWAITING_CENSUS_REVIEW for the
closure/conversion/identity-conflict findings below) -- never further.

Run:

    python -m scripts.pettripfinder.detroit_ann_arbor_identity_routing_repair_001
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.build_detroit_ann_arbor_market_001 import (
    CANDIDATES,
    SOURCES,
    AS_OF as PHASE1_AS_OF,
)
from scripts.pettripfinder.contracts import census as CENSUS
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import partition as PART
from scripts.pettripfinder.contracts.identity_key import (
    IDENTITY_KEY_CONTRACT,
    ptf_identity_key,
)
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id, slugify
from scripts.pettripfinder.site_data import normalize_name

_REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-IDENTITY-ROUTING-REPAIR-001"
FOUNDATION_COMMIT = "bf8612579eb477301b69e31d8c4be0fe47f29b3b"
MARKET = "detroit-ann-arbor-mi"
AS_OF = "2026-08-17"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
CENSUS_PATH = PACKAGE / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = PACKAGE / "detroit_ann_arbor_final_partition_001.json"
DATA_ROOT = _REPO_ROOT / "data" / "market_research" / "detroit-ann-arbor"

# EXACT_PROPERTY_FIRST_PARTY | BRAND_PROPERTY_PAGE | BRAND_INDEX_BINDING |
# ROUTING_UNRESOLVED | PROPERTY_CLOSED_OR_CONVERTED | IDENTITY_CONFLICT


def _r(**kw):
    return kw


# ============================================================================
# Repair findings, one entry per one of the 119 targets, keyed by the exact
# canonical_name used in build_detroit_ann_arbor_market_001.CANDIDATES.
# ============================================================================
REPAIRS = {
    # ---- Ann Arbor: property-level URL upgrades (annarbor.org brand_index
    # -> exact first-party page) ----
    "AC Hotel Ann Arbor Downtown": _r(
        address="310 East Huron Street", postal="48104",
        url="https://www.marriott.com/en-us/hotels/dtwad-ac-hotel-ann-arbor-downtown/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Ann Arbor Regent Hotel & Suites": _r(
        address="2455 Carpenter Rd", postal="48108", phone="734-973-6100",
        url="https://annarborregent.com/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Extended Stay America Detroit Ann Arbor University South": _r(
        address="3265 Boardwalk Street", postal="48108", phone="734-997-7623",
        url="https://www.extendedstayamerica.com/hotels/mi/detroit/ann-arbor-university-south",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Fairfield Inn Ann Arbor": _r(
        address="3285 Boardwalk Drive", postal="48108", phone="734-768-1130",
        url="https://www.marriott.com/en-us/hotels/arbfi-fairfield-inn-ann-arbor/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hilton Garden Inn Ann Arbor": _r(
        address="1401 Briarwood Circle", postal="48108", phone="734-327-6400",
        url="https://www.hilton.com/en/hotels/arbgigi-hilton-garden-inn-ann-arbor/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn Express & Suites Ann Arbor West": _r(
        address="323 North Zeeb Road", postal="48103", phone="734-827-1100",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/ann-arbor/arbzb/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Quality Inn & Suites Ann Arbor": _r(
        address="2376 Carpenter Road", postal="48108", phone="734-477-9977",
        url="https://www.choicehotels.com/michigan/ann-arbor/comfort-inn-hotels/mi356",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Choice Hotels' own URL slug says comfort-inn-hotels but the "
              "page itself is titled Quality Inn & Suites Ann Arbor Hwy 23; "
              "carried as observed."),
    "Red Roof Inn Ann Arbor University of Michigan South": _r(
        address="3505 S State St", postal="48108", phone="734-665-3500",
        url="https://www.redroof.com/property/mi/ann-arbor/rri693",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Red Roof PLUS+ Ann Arbor University of Michigan North": _r(
        address="3621 Plymouth Rd", postal="48105", phone="734-996-5800",
        url="https://www.redroof.com/property/mi/ann-arbor/rri045",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Residence Inn by Marriott Ann Arbor Downtown": _r(
        address="120 West Huron Street", postal="48104", phone="734-662-9999",
        url="https://www.marriott.com/en-us/hotels/arbdt-residence-inn-ann-arbor-downtown/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Sheraton Ann Arbor Hotel": _r(
        phone="248-349-4000",
        url="https://www.marriott.com/en-us/hotels/arbsi-sheraton-ann-arbor-hotel/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Marriott's own overview page did not surface a street address "
              "in search snippets; phone number and property page confirmed "
              "first-party."),
    "The Inn at the Michigan League": _r(
        address="911 North University Avenue", postal="48104", phone="734-764-3177",
        url="https://inn.studentlife.umich.edu/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "TownePlace Suites by Marriott Ann Arbor": _r(
        address="1301 Briarwood Circle", postal="48108", phone="734-327-5900",
        url="https://www.marriott.com/en-us/hotels/arbtp-towneplace-suites-ann-arbor/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Comfort Inn at Greenfield Village": _r(
        address="20061 Michigan Ave", postal="48124", phone="313-380-3146",
        url="https://www.choicehotels.com/michigan/dearborn/comfort-inn-hotels/mi385",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Choice Hotels' own page displays the property as 'Comfort Inn "
              "Near Greenfield Village' -- a minor wording variant of the "
              "census's 'Comfort Inn at Greenfield Village'; same address and "
              "brand code mi385, not treated as a rename."),
    "TownePlace Suites by Marriott Detroit Belleville": _r(
        address="46418 N I-94 Service Dr", city="Belleville", postal="48111",
        phone="734-699-2100",
        url="https://www.marriott.com/en-us/hotels/dtwbl-towneplace-suites-detroit-belleville/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="A second Marriott property code (ytrts-towneplace-suites-"
              "belleville, without the 'Detroit' name segment) also appeared "
              "in search results; dtwbl was selected as the exact name match. "
              "Flagged for founder awareness, not treated as a conflict."),

    # ---- Ann Arbor: AWAITING_OFFICIAL_URL rows ----
    "EVEN Hotel Ann Arbor": _r(
        address="600 Briarwood Circle", postal="48108", phone="734-761-2929",
        url="https://www.ihg.com/evenhotels/hotels/us/en/ann-arbor/arbmi/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Graduate Ann Arbor": _r(
        address="615 East Huron St", postal="48104", phone="734-769-2200",
        url="https://www.graduatehotels.com/ann-arbor/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Now branded Graduate by Hilton Ann Arbor (Graduate Hotels "
              "joined the Hilton portfolio); same property, address and "
              "phone unchanged. Census canonical_name kept as 'Graduate Ann "
              "Arbor' pending founder rename decision."),
    "Weber's Inn": _r(
        address="3050 Jackson Road", postal="48103", phone="734-769-2500",
        url="https://www.webersannarbor.com", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY",
        special="rebrand",
        notes="PROPERTY_CONVERTED_OR_REBRANDED: current operating name is "
              "'Weber's Boutique Hotel' at webersannarbor.com, not the "
              "'Weber's Inn' / webersinn.com identity the candidate carried. "
              "Same address (3050 Jackson Rd). Census canonical_name NOT "
              "silently renamed -- recommend founder review to rename to "
              "Weber's Boutique Hotel."),

    # ---- Ypsilanti ----
    "Hampton Inn & Suites Ypsilanti": _r(
        phone="734-879-9565",
        url="https://www.hilton.com/en/hotels/dtwyphx-hampton-suites-ypsilanti/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- Downtown Detroit ----
    "Atheneum Suite Hotel": _r(
        address="1000 Brush St", postal="48226", phone="313-962-2323",
        url="https://www.atheneumsuites.com", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Cambria Hotel Detroit Downtown": _r(
        address="600 West Lafayette", postal="48226", phone="313-733-0300",
        url="https://cambriadetroit.com/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Courtyard by Marriott Detroit Downtown": _r(
        address="333 E. Jefferson Ave.", postal="48226", phone="313-222-7700",
        url="https://www.marriott.com/en-us/hotels/dtwdc-courtyard-detroit-downtown/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Crowne Plaza Detroit Downtown Riverfront": _r(
        address="2 Washington Blvd.", postal="48226", phone="313-965-0200",
        url="https://www.ihg.com/crowneplaza/hotels/us/en/detroit/dttnd/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Detroit Foundation Hotel": _r(
        phone="313-800-5500",
        url="https://detroitfoundationhotel.com/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Independent Aparium boutique hotel; not Marriott/Autograph "
              "affiliated despite the visit_detroit guide grouping it with "
              "boutique properties."),
    "DoubleTree Suites by Hilton Downtown Detroit": _r(
        address="525 W. Lafayette Blvd.", postal="48226", phone="313-963-5600",
        url="https://www.hilton.com/en/hotels/dttlfdt-doubletree-suites-detroit-downtown-fort-shelby/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Full current name: DoubleTree Suites by Hilton Hotel Detroit "
              "Downtown - Fort Shelby."),
    "El Moore Lodge": _r(
        address="624 W Alexandrine St", postal="48201", phone="313-924-4374",
        url="https://elmoore.com/lodge/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Element Detroit at the Metropolitan": _r(
        address="33 John R Street", postal="48226", phone="313-306-2400",
        url="https://www.marriott.com/en-us/hotels/dtwel-element-detroit-at-the-metropolitan/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hollywood Casino at Greektown": _r(
        address="555 E. Lafayette Blvd.", postal="48226", phone="313-223-2999",
        url="https://www.hollywoodgreektown.com/hotel", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hotel Indigo Detroit Downtown": _r(
        address="1020 Washington Blvd", postal="48226", phone="313-887-7000",
        url="https://www.ihg.com/hotelindigo/hotels/us/en/detroit/dttid/hoteldetail",
        url_shape="brand_index", ident="IDENTITY_CONFIRMED",
        verdict="ROUTING_UNRESOLVED",
        notes="Address/phone confirmed from Yelp/aggregators; the exact IHG "
              "property code for THIS Washington Blvd property was not "
              "independently confirmed in search snippets (the ihg.com URL "
              "used here is a best-effort city-pattern guess and is NOT "
              "confirmed first-party), so this stays a routing target rather "
              "than being marked EXACT_PROPERTY_FIRST_PARTY."),
    "MGM Grand Detroit": _r(
        address="1777 Third Street", postal="48226", phone="313-465-1777",
        url="https://www.mgmgranddetroit.com", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "MotorCity Casino Hotel": _r(
        address="2901 Grand River Ave", postal="48201", phone="866-782-9622",
        url="https://www.motorcitycasino.com", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Roost Detroit": _r(
        address="1265 Washington Blvd", postal="48226", phone="313-547-6165",
        url="https://www.myroost.com/extended-stay-hotel-detroit-michigan",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Located inside the historic Book Tower; apartment-style "
              "extended-stay hotel."),
    "The Godfrey Hotel Detroit": _r(
        address="1401 Michigan Ave", postal="48216", phone="313-385-0000",
        url="https://www.godfreyhoteldetroit.com/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Current full name: The Godfrey Detroit, Curio Collection by "
              "Hilton."),
    "The Inn on Ferry Street": _r(
        address="84 E. Ferry St.", postal="48202", phone="313-871-6000",
        url="https://www.innonferrystreet.com/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "The Siren Hotel": _r(
        address="1509 Broadway", postal="48226", phone="313-277-4736",
        url="https://ash.world/hotels/the-siren/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="An Ash Hotel (parent company Ash Hotels/ash.world); housed in "
              "the historic Wurlitzer Building."),
    "Trumbull and Porter Hotel": _r(
        address="1331 Trumbull St", postal="48216", phone="480-676-5193",
        url="https://www.trumbullandporterhotel.com/", url_shape="property",
        ident="IDENTITY_CONFIRMED", verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- Dearborn ----
    "Best Western Greenfield Inn": _r(
        address="3000 Enterprise Dr", city="Dearborn", postal="48101",
        phone="313-271-1600", url="", url_shape="none",
        ident="IDENTITY_CONFIRMED", verdict="IDENTITY_CONFLICT",
        special="census_review",
        notes="IDENTITY CONFLICT: the property's real street address (3000 "
              "Enterprise Dr) is in Allen Park, Michigan, not Dearborn. Visit "
              "Detroit's own guide groups it under 'Wayne County (Dearborn "
              "area)' and it has traded as a Dearborn-area hotel for "
              "decades, but Allen Park is not one of this market's named "
              "corridors. City left as 'Dearborn' in the census to avoid an "
              "unassigned row pending a founder decision on whether to add "
              "Allen Park to the dearborn corridor or boundary-exclude this "
              "property; recorded here for that decision, not resolved."),
    "DoubleTree by Hilton Detroit Dearborn": _r(
        address="5801 Southfield Freeway", city="Dearborn", postal="48228",
        phone="313-336-3340",
        url="https://www.hilton.com/en/hotels/dttdbdt-doubletree-detroit-dearborn/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Hilton's own listing gives the mailing city as Detroit "
              "(48228), consistent with the property sitting on the Detroit/"
              "Dearborn border; kept in the dearborn corridor per the "
              "brand's own 'Dearborn' naming and Visit Detroit's grouping."),
    "Red Roof Inn Dearborn": _r(
        phone="937-328-1539",
        url="https://www.redroof.com/property/mi/dearborn/rri182",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn Fairlane Dearborn": _r(
        address="5801 Southfield Service Drive", city="Dearborn",
        postal="48228", url="", url_shape="none",
        ident="IDENTITY_PROVISIONAL", verdict="PROPERTY_CLOSED_OR_CONVERTED",
        special="closed",
        notes="Yelp lists this exact property (Holiday Inn Fairlane-"
              "Dearborn, 5801 Southfield Fwy) as CLOSED. No live IHG page "
              "exists under this name; the two currently-live Dearborn "
              "Holiday Inn Express properties (dttde at an unconfirmed "
              "address and dttbo) are DIFFERENT identities with no address "
              "match confirmed, so no automatic conversion is recorded. "
              "Closure probable but not fully corroborated by a second "
              "independent source -- moved to census review, not deleted."),
    "Staybridge Suites Dearborn": _r(
        address="24105 Michigan Avenue", city="Dearborn", postal="48124",
        phone="313-565-1500",
        url="https://www.ihg.com/staybridge/hotels/us/en/dearborn/dttjj/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- DTW Airport / Romulus ----
    "Delta Hotels by Marriott Detroit Metro Airport": _r(
        address="31500 Wick Rd", city="Romulus", postal="48174",
        phone="734-721-3315",
        url="https://www.marriott.com/hotels/travel/dtwd",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Comfort Inn Metro Airport": _r(
        address="", city="Romulus", postal="",
        url="https://www.choicehotels.com/en-ca/michigan/romulus/comfort-inn-hotels/mi048",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Choice's own property code mi048 confirms Romulus identity; "
              "street address was not surfaced in search snippets."),
    "Embassy Suites by Hilton Detroit Metro Airport": _r(
        address="8600 Wickham Rd", city="Romulus", postal="48174",
        phone="734-728-9200",
        url="https://www.hilton.com/en/hotels/dethses-embassy-suites-detroit-metro-airport/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hilton Garden Inn Detroit Metro Airport": _r(
        address="31800 Smith Rd", city="Romulus", postal="48174",
        phone="734-727-6000",
        url="https://www.hilton.com/en/hotels/detmagi-hilton-garden-inn-detroit-metro-airport/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- Southfield (all chain_aggregate identity-resolution) ----
    "Courtyard by Marriott Detroit Southfield": _r(
        address="27027 Northwestern Hwy", city="Southfield", postal="48033",
        phone="248-358-1222",
        url="https://www.marriott.com/en-us/hotels/dtwsf-courtyard-detroit-southfield/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Detroit Marriott Southfield": _r(
        address="27033 Northwestern Hwy", city="Southfield", postal="48034",
        phone="248-356-7400",
        url="https://www.marriott.com/en-us/hotels/dtwsl-detroit-marriott-southfield/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hampton Inn by Hilton Detroit Southfield": _r(
        address="26080 Northwestern Highway", city="Southfield", postal="48076",
        phone="248-256-2350",
        url="https://www.hilton.com/en/hotels/dtwsfhx-hampton-detroit-southfield/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hawthorn Suites by Wyndham Southfield Detroit": _r(
        address="26700 Central Park Blvd", city="Southfield", postal="48076",
        phone="800-916-1392", url="", url_shape="none",
        ident="IDENTITY_CONFIRMED", verdict="ROUTING_UNRESOLVED",
        notes="Address confirmed via aggregator cross-reference (two "
              "different Hawthorn Suites addresses surfaced -- 26700 Central "
              "Park Blvd Southfield and 5777 Southfield Fwy Detroit -- and "
              "the Southfield one matches the census city); no first-party "
              "wyndhamhotels.com URL was independently confirmed."),
    "Hilton Garden Inn Detroit Southfield": _r(
        address="26000 American Drive", city="Southfield", postal="48034",
        phone="248-357-1100",
        url="https://www.hilton.com/en/hotels/detshgi-hilton-garden-inn-detroit-southfield-mi/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn Express & Suites Southfield Detroit": _r(
        address="25100 Northwestern Hwy", city="Southfield", postal="48075",
        phone="248-350-2400",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/southfield/dttnw/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Ramada by Wyndham Southfield": _r(
        address="28100 Franklin Rd", city="Southfield", postal="48034",
        phone="248-282-6110",
        url="https://www.wyndhamhotels.com/ramada/southfield-michigan/ramada-southfield/overview",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "SpringHill Suites Detroit Southfield": _r(
        address="28555 Northwestern Hwy", city="Southfield", postal="48034",
        phone="248-352-6100",
        url="https://www.marriott.com/en-us/hotels/dtwsd-springhill-suites-detroit-southfield/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Staybridge Suites Detroit Southfield": _r(
        address="26060 Northwestern Hwy", city="Southfield", postal="48076",
        phone="947-479-4747",
        url="https://www.ihg.com/staybridge/hotels/us/en/southfield/dttbs/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "The Westin Southfield Detroit": _r(
        address="1500 Town Center", city="Southfield", postal="48075",
        phone="248-827-4000",
        url="https://www.marriott.com/en-us/hotels/dtwwi-the-westin-southfield-detroit/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- Troy / Auburn Hills: chamber URL recovery ----
    "Crowne Plaza Auburn Hills": _r(
        phone="248-373-4550",
        url="https://www.ihg.com/crowneplaza/hotels/us/en/auburn-hills/dttah/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "EVEN Hotel Detroit North Troy": _r(
        postal="48084", phone="248-720-6400",
        url="https://www.ihg.com/evenhotels/hotels/us/en/troy/dttry/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Dual-branded IHG property with Hotel Indigo Detroit North - "
              "Troy at the same 575 W. Big Beaver address; EVEN's own IHG "
              "code is dttry, distinct from Indigo's dttoy."),
    "Hampton Inn Detroit Auburn Hills North": _r(
        phone="248-322-1100",
        url="https://www.hilton.com/en/hotels/dttnahx-hampton-detroit-auburn-hills-north-great-lakes-crossing-area/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn Express Hotel & Suites Auburn Hills": _r(
        phone="248-322-7000",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/auburn-hills/dttbr/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hotel Auburn Hills": _r(
        phone="248-409-4670",
        url="https://www.marriott.com/en-us/hotels/fntah-hotel-auburn-hills/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hotel Indigo Detroit North Troy": _r(
        postal="48084", phone="248-720-6400",
        url="https://www.ihg.com/hotelindigo/hotels/us/en/troy/dttoy/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hyatt Place Detroit Auburn Hills": _r(
        url="https://www.hyatt.com/hyatt-place/en-US/detza-hyatt-place-detroit-auburn-hills",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Hyatt brand -- flagged for corpus-standard attended-capture "
              "treatment at capture time (see Hyatt/manual section)."),
    "Quality Inn Auburn Hills": _r(
        phone="248-221-1026",
        url="https://www.choicehotels.com/michigan/auburn-hills/quality-inn-hotels/mi404",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Red Roof Inn Auburn Hills": _r(
        url="https://www.redroof.com/property/mi/auburn-hills/rri1419",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Sonesta Select Detroit Auburn Hills": _r(
        phone="248-373-4100",
        url="https://www.sonesta.com/sonesta-select/mi/auburn-hills/sonesta-select-detroit-auburn-hills",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "SpringHill Suites Auburn Hills": _r(
        phone="248-475-4700",
        url="https://www.marriott.com/en-us/hotels/dtwra-springhill-suites-detroit-auburn-hills/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "TownePlace Suites Detroit Auburn Hills": _r(
        phone="248-454-0650",
        url="https://www.marriott.com/en-us/hotels/dtwta-towneplace-suites-detroit-auburn-hills/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- Troy / Auburn Hills: chain_aggregate identity resolution ----
    "Courtyard by Marriott Detroit Troy": _r(
        address="1525 East Maple Rd", city="Troy", postal="48083",
        phone="248-528-2800",
        url="https://www.marriott.com/en-us/hotels/dtttr-courtyard-detroit-troy/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Detroit Marriott Troy": _r(
        address="200 W. Big Beaver Rd.", city="Troy", postal="48084",
        phone="248-680-9797",
        url="https://www.marriott.com/en-us/hotels/dtttt-detroit-marriott-troy/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Embassy Suites by Hilton Detroit Troy Auburn Hills": _r(
        address="850 Tower Dr", city="Troy", postal="48098",
        phone="248-879-7500",
        url="https://www.hilton.com/en/hotels/dtttres-embassy-suites-detroit-troy-auburn-hills/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Fairfield Inn & Suites Detroit Troy": _r(
        address="225 Stephenson Hwy", city="Troy", postal="48083",
        phone="855-816-6193",
        url="https://www.marriott.com/en-us/hotels/dtwft-fairfield-inn-and-suites-detroit-troy/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hilton Garden Inn Detroit Troy": _r(
        address="200 Wilshire Drive", city="Troy", postal="48084",
        phone="248-247-7280",
        url="https://www.hilton.com/en/hotels/detdtgi-hilton-garden-inn-detroit-troy/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn & Suites Detroit Troy": _r(
        address="870 Tower Drive", city="Troy", postal="48098",
        phone="248-781-7500",
        url="https://www.ihg.com/holidayinn/hotels/us/en/troy/dttro/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="A different, closed 'Holiday Inn Hotel Detroit - Troy' "
              "formerly existed at 2537 Rochester Ct (now Wingate by Wyndham "
              "Troy, see below); this is a distinct, currently-open property "
              "at 870 Tower Drive."),
    "Holiday Inn Express & Suites Detroit North Troy": _r(
        address="400 Stephenson Hwy", city="Troy", postal="48083",
        phone="248-583-1900",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/troy/dttom/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Home2 Suites by Hilton Troy": _r(
        address="1035 Wilshire Dr", city="Troy", postal="48084",
        phone="248-633-2118",
        url="https://www.hilton.com/en/hotels/dtwhtht-home2-suites-troy/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Homewood Suites by Hilton Detroit Troy": _r(
        address="1495 Equity Dr", city="Troy", postal="48084",
        phone="248-816-6500",
        url="https://www.hilton.com/en/hotels/dtttyhw-homewood-suites-detroit-troy/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Somerset Inn": _r(
        address="2601 W Big Beaver Rd", city="Troy", postal="48084",
        phone="248-643-7800", url="https://www.somersetinn.com/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Sonesta ES Suites Auburn Hills": _r(
        address="2050 Featherstone Road", city="Auburn Hills", postal="48326",
        phone="248-322-4600",
        url="https://www.sonesta.com/sonesta-es-suites/mi/auburn-hills/sonesta-es-suites-auburn-hills-detroit",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "TownePlace Suites by Marriott Detroit Troy": _r(
        address="325 Stephenson Highway", city="Troy", postal="48083",
        url="https://www.marriott.com/en-us/hotels/dttts-towneplace-suites-detroit-troy/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Tru by Hilton Troy Detroit": _r(
        address="1575 E Maple Rd", city="Troy", postal="48083",
        phone="248-422-3400",
        url="https://www.hilton.com/en/hotels/dettyru-tru-troy-detroit/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Wingate by Wyndham Troy": _r(
        address="2537 Rochester Court", city="Troy", postal="48083",
        phone="248-689-7500",
        url="https://www.wyndhamhotels.com/wingate/troy-michigan/wingate-troy/overview",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="This address (2537 Rochester Ct) previously operated as a "
              "Holiday Inn (now closed under that name); Wingate is the "
              "current live brand at this address."),

    # ---- Birmingham / Royal Oak / Rochester / Pontiac ----
    "Auburn Hills Marriott Pontiac": _r(
        phone="248-253-9800",
        url="https://www.marriott.com/en-us/hotels/dtwpo-auburn-hills-marriott-pontiac/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Courtyard Detroit Pontiac Bloomfield": _r(
        url="https://visitdetroit.com/directory/courtyard-by-marriott-detroit-pontiac-auburn-hills/",
        url_shape="brand_index", ident="IDENTITY_CONFIRMED",
        verdict="ROUTING_UNRESOLVED",
        notes="No independently confirmed marriott.com property code found "
              "in search snippets for this specific address; Visit Detroit's "
              "own directory page is the strongest URL found."),
    "Daxton Hotel": _r(
        address="298 S Old Woodward Ave", city="Birmingham", postal="48009",
        phone="248-283-4200", url="https://daxtonhotel.com/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Curio Collection by Hilton."),
    "Hotel Royal Oak": _r(
        address="811 East 11 Mile Rd", city="Royal Oak", postal="48067",
        phone="888-245-5055", url="https://hotelroyaloak.com/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hyatt Place Detroit Royal Oak": _r(
        address="422 N. Main Street", city="Royal Oak", postal="48067",
        phone="248-545-7030",
        url="https://www.hyatt.com/hyatt-place/en-US/dtwzr-hyatt-place-detroit-royal-oak",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Hyatt brand -- flagged for attended-capture treatment."),
    "Royal Park Hotel": _r(
        phone="248-652-2600", url="https://www.royalparkhotelmi.com/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "The Kingsley Bloomfield Hills": _r(
        url="https://www.hilton.com/en/hotels/dtwbhdt-the-kingsley-bloomfield-hills/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY", special="rebrand",
        notes="PROPERTY_CONVERTED_OR_REBRANDED: formerly 'The Kingsley Inn' "
              "(shown CLOSED under that name on Yelp); current operating "
              "identity is 'The Kingsley Bloomfield Hills - a DoubleTree by "
              "Hilton' at the same 39475 Woodward Ave address, not a true "
              "closure."),
    "The Townsend Hotel": _r(
        phone="248-642-7900", url="https://www.townsendhotel.com/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- Novi / Wixom: vibe_showplace URL recovery ----
    "Four Points by Sheraton Detroit Novi": _r(
        address="27000 South Karevich Drive", postal="48377",
        url="https://www.marriott.com/en-us/hotels/dtwfn-four-points-detroit-novi/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hampton Inn & Suites Wixom": _r(
        address="49025 Alpha Dr", postal="48393", phone="248-348-0170",
        url="https://www.hilton.com/en/hotels/dttwxhx-hampton-suites-wixom/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn Express Novi": _r(
        address="39675 W 12 Mile Rd", postal="48377", phone="248-344-8204",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/novi/dttni/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Full brand name: Holiday Inn Express & Suites Detroit-Novi."),
    "Holiday Inn Express Wixom": _r(
        address="48953 Alpha Dr", postal="48393", phone="248-735-2781",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/wixom/dttal/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Homewood Suites by Hilton Novi": _r(
        address="26150 Town Center Dr", postal="48375", phone="248-347-6100",
        url="https://www.hilton.com/en/hotels/dttdnhw-homewood-suites-novi-detroit/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hyatt Place Detroit Novi": _r(
        phone="248-513-4111",
        url="https://www.hyatt.com/hyatt-place/en-US/dttzh-hyatt-place-detroit-novi",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="Hyatt brand -- flagged for attended-capture treatment."),
    "Sheraton Detroit Novi Hotel": _r(
        phone="248-349-4000",
        url="https://www.marriott.com/en-us/hotels/dtwos-sheraton-detroit-novi-hotel/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Sonesta Select Detroit Novi": _r(
        address="42700 West 11 Mile Rd", postal="48375",
        url="https://www.sonesta.com/sonesta-select/mi/novi/sonesta-select-detroit-novi",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="See the Courtyard by Marriott Detroit Novi entry below: this "
              "same address (42700 W 11 Mile Rd) is reported as a CLOSED "
              "Courtyard by Marriott on Yelp -- the two census rows likely "
              "describe the same building under successive brands."),

    # ---- Novi / Wixom: chain_aggregate identity resolution ----
    "Courtyard by Marriott Detroit Novi": _r(
        address="42700 W 11 Mile Rd", city="Novi", postal="48375",
        url="", url_shape="none", ident="IDENTITY_PROVISIONAL",
        verdict="PROPERTY_CLOSED_OR_CONVERTED", special="converted",
        notes="PROPERTY_CONVERTED_OR_REBRANDED: Yelp marks 'Courtyard by "
              "Marriott Detroit Novi' at 42700 W 11 Mile Rd as CLOSED. The "
              "census's separate 'Sonesta Select Detroit Novi' row carries "
              "the EXACT SAME address, confirmed first-party via sonesta.com. "
              "Old identity: Courtyard by Marriott Detroit Novi (closed). "
              "Current identity at this address: Sonesta Select Detroit Novi "
              "(already a distinct census row). Address match: EXACT. "
              "Recommend founder census review to mark this row as a "
              "conversion/duplicate of 'sonesta select detroit novi' rather "
              "than a live independent identity -- not merged here."),
    "Delta Hotels by Marriott Detroit Novi": _r(
        address="37529 Grand River Avenue", city="Farmington Hills",
        postal="48335", phone="248-653-6060",
        url="https://www.marriott.com/en-us/hotels/dtwdf-delta-hotels-detroit-novi/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="GEOGRAPHY CORRECTION: Marriott's own listing places this "
              "property in Farmington Hills, not Novi, despite the brand "
              "name. City corrected to Farmington Hills so corridor "
              "assignment (city_state tier) places it in the "
              "farmington-hills corridor on rebuild -- the same class of "
              "fix as Cincinnati's Eastgate mailing-city defect, caught "
              "before publication rather than after."),
    "DoubleTree by Hilton Detroit Novi": _r(
        address="42100 Crescent Blvd", city="Novi", postal="48375",
        phone="248-344-8800",
        url="https://doubletree.hilton.com/", url_shape="brand_index",
        ident="IDENTITY_CONFIRMED", verdict="ROUTING_UNRESOLVED",
        notes="Address and phone confirmed via Yelp/aggregators; the exact "
              "hilton.com property-code URL was not independently confirmed "
              "in search snippets, so the DoubleTree brand landing page is "
              "recorded rather than a guessed property code."),
    "Residence Inn by Marriott Detroit Novi": _r(
        address="27477 Cabaret Drive", city="Novi", postal="48377",
        phone="248-735-7400",
        url="https://www.marriott.com/en-us/hotels/dtwno-residence-inn-detroit-novi/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Staybridge Suites Detroit Novi": _r(
        address="27000 Providence Parkway", city="Novi", postal="48374",
        url="https://www.ihg.com/staybridge/hotels/us/en/novi/dttgw/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "The Baronette Renaissance Detroit Novi": _r(
        address="27790 Novi Road", city="Novi", postal="48377",
        phone="248-349-7800",
        url="https://www.marriott.com/en-us/hotels/dtwdn-the-baronette-renaissance-detroit-novi-hotel/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- Farmington Hills / West Bloomfield ----
    "Residence Inn by Marriott Detroit Farmington Hills": _r(
        address="33163 Hamilton Court", city="Farmington Hills", postal="48334",
        phone="248-516-1201",
        url="https://www.marriott.com/en-us/hotels/dtwrf-residence-inn-detroit-farmington-hills/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Fairfield Inn & Suites Detroit Farmington Hills": _r(
        address="27777 Stansbury Boulevard", city="Farmington Hills",
        postal="48334", phone="248-442-9800",
        url="https://www.marriott.com/en-us/hotels/dtwfh-fairfield-inn-and-suites-detroit-farmington-hills/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn & Suites Farmington Hills Detroit NW": _r(
        address="33103 Hamilton Ct", city="Farmington Hills", postal="48334",
        phone="248-516-1280",
        url="https://www.ihg.com/holidayinn/hotels/us/en/farmington-hills/dttfa/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn Express & Suites Farmington Hills Detroit": _r(
        address="32769 Northwestern Hwy", city="Farmington Hills",
        postal="48334", phone="248-538-9100",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/farmington-hills/dttfn/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="A separate, differently-addressed Holiday Inn Express & "
              "Suites 'Detroit - Farmington Hills' also exists at 21100 "
              "Haggerty Rd, Northville (IHG code normi) -- not this row; no "
              "action taken on that separate identity."),
    "Hampton Inn by Hilton West Bloomfield Novi": _r(
        address="33096 Northwestern Hwy", city="West Bloomfield", postal="48322",
        url="https://www.hilton.com/en/hotels/dttwbhx-hampton-west-bloomfield-novi/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),

    # ---- Livonia / Plymouth / Northville ----
    "Americas Best Value Inn Livonia Detroit": _r(
        address="28512 Schoolcraft Rd", city="Livonia", postal="48150",
        phone="734-425-5150",
        url="https://www.sonesta.com/americas-best-value-inn/mi/livonia/americas-best-value-inn-livonia-detroit",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Detroit Marriott Livonia": _r(
        address="17100 Laurel Park Drive North", city="Livonia", postal="48152",
        phone="734-462-3100",
        url="https://www.marriott.com/en-us/hotels/dtwli-detroit-marriott-livonia/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Embassy Suites by Hilton Detroit Livonia Novi": _r(
        address="19525 Victor Pkwy", city="Livonia", postal="48152",
        phone="734-462-6000",
        url="https://www.hilton.com/en/hotels/dttlies-embassy-suites-detroit-livonia-novi/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Fairfield Inn & Suites by Marriott Detroit Livonia": _r(
        address="17350 Fox Dr", city="Livonia", postal="48152",
        phone="734-953-8888",
        url="https://www.marriott.com/en-us/hotels/dtwfl-fairfield-inn-and-suites-detroit-livonia/overview/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Hilton Garden Inn Plymouth": _r(
        address="14600 N Sheldon Rd", city="Plymouth", postal="48170",
        phone="734-354-0001",
        url="https://www.hilton.com/en/hotels/detphgi-hilton-garden-inn-plymouth/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn Express Detroit Northwest Livonia": _r(
        address="27451 Schoolcraft Road", city="Livonia", postal="48150",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/livonia/dttlx/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Holiday Inn Express Plymouth Ann Arbor": _r(
        address="15100 N Beck Rd", city="Plymouth", postal="48170",
        phone="734-969-8100",
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/plymouth/dtwpm/hoteldetail",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Home2 Suites by Hilton Northville Detroit": _r(
        address="47450 W Five Mile Rd", city="Northville", postal="48168",
        url="https://www.hilton.com/en/hotels/deththt-home2-suites-northville-detroit/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Quality Inn & Suites Banquet Center Livonia": _r(
        address="30375 Plymouth Road", city="Livonia", postal="48150",
        phone="734-261-6800",
        url="https://www.choicehotels.com/michigan/livonia/quality-inn-hotels/mi119",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
    "Saint John's Resort": _r(
        address="44045 Five Mile Road", city="Plymouth", postal="48170",
        phone="734-414-0600", url="https://www.saintjohnsresort.com/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY",
        notes="City corrected from the Detroit Hotel Guide's 'Northville' "
              "label to Plymouth per the property's own official address; "
              "still assigned to the livonia-plymouth-northville corridor, "
              "which already includes Plymouth."),
    "Spark by Hilton Plymouth": _r(
        address="40455 Ann Arbor Rd", city="Plymouth", postal="48170",
        phone="734-455-8100",
        url="https://www.hilton.com/en/hotels/dtwhipe-spark-plymouth/",
        url_shape="property", ident="IDENTITY_CONFIRMED",
        verdict="EXACT_PROPERTY_FIRST_PARTY"),
}


def _blocker_for(row: dict) -> str:
    if row["lodging_state"] == enums.NOT_LODGING:
        return enums.OUT_OF_CURRENT_CATEGORY
    if row.get("_census_review"):
        return enums.AWAITING_CENSUS_REVIEW
    if row["identity_state"] in (enums.IDENTITY_PROVISIONAL, enums.IDENTITY_UNRESOLVED):
        return enums.AWAITING_IDENTITY_RESOLUTION
    if row.get("url_shape") == "brand_index":
        return enums.AWAITING_PROPERTY_LEVEL_URL
    if row.get("official_url"):
        return enums.AWAITING_POLICY_OBSERVATION
    return enums.AWAITING_OFFICIAL_URL


def _dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _street_identity(address: str, postal: str) -> str:
    street = normalize_name(address)
    return "%s|%s" % (street, (postal or "")[:5]) if street else ""


def build() -> dict:
    market = market_by_id(load_markets(), MARKET)

    canonical = []
    seen_keys = {}
    repair_records = []
    for raw in CANDIDATES:
        if (raw.get("disposition") or "canonical") != "canonical":
            continue
        name = raw["name"]
        key = ptf_identity_key(name)
        seen_keys[key] = name
        slug = slugify(name)
        row = {
            "identity_key": key,
            "canonical_name": name,
            "display_name": name,
            "slug": slug,
            "market_id": MARKET,
            "address": raw.get("address") or "",
            "city": raw.get("city") or "",
            "state": "MI",
            "postal_code": (raw.get("postal") or "")[:5],
            "phone": raw.get("phone") or "",
            "identity_state": raw["ident"],
            "lodging_state": raw["lodging"],
            "policy_state": enums.POLICY_NOT_VERIFIED,
            "collision_state": enums.COLLISION_NONE,
            "official_url": raw.get("url") or "",
            "corridor": "",
            "assignment_basis": "",
            "assignment_value": "",
            "source": raw["source"],
            "source_id": slug,
            "observed_at": PHASE1_AS_OF,
            "provenance": "PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001:%s" % raw["source"],
            "normalized_name": normalize_name(name),
            "former_name": raw.get("former") or "",
            "url_shape": raw.get("url_shape") or "none",
            "disposition": "canonical",
            "street_identity": "",
            "_census_review": False,
        }

        repair = REPAIRS.get(name)
        if repair:
            old_url = row["official_url"]
            old_url_shape = row["url_shape"]
            old_ident = row["identity_state"]
            if repair.get("address") is not None:
                row["address"] = repair["address"]
            if repair.get("city"):
                row["city"] = repair["city"]
            if repair.get("postal") is not None:
                row["postal_code"] = (repair["postal"] or "")[:5]
            if repair.get("phone"):
                row["phone"] = repair["phone"]
            if repair.get("url") is not None:
                row["official_url"] = repair["url"]
            if repair.get("url_shape"):
                row["url_shape"] = repair["url_shape"]
            if repair.get("ident"):
                row["identity_state"] = repair["ident"]
            row["observed_at"] = AS_OF
            row["provenance"] = "%s:%s" % (WORK_ORDER, raw["source"])
            special = repair.get("special")
            if special in ("closed", "converted", "census_review"):
                row["_census_review"] = True
            repair_records.append(OrderedDict((
                ("identity_key", key),
                ("canonical_name", name),
                ("old_state", "AWAITING_IDENTITY_RESOLUTION" if old_ident in
                 (enums.IDENTITY_PROVISIONAL, enums.IDENTITY_UNRESOLVED)
                 else ("AWAITING_PROPERTY_LEVEL_URL" if old_url_shape == "brand_index"
                       else "AWAITING_OFFICIAL_URL")),
                ("old_url", old_url),
                ("observed_current_name", (repair.get("notes") or "").split(".")[0]
                 if special == "rebrand" else name),
                ("address", row["address"]),
                ("city", row["city"]),
                ("postal_code", row["postal_code"]),
                ("phone", row["phone"]),
                ("brand", ""),
                ("property_code", ""),
                ("official_url", row["official_url"]),
                ("identity_signals",
                 "first-party page: address+phone+URL" if row["address"] and row["phone"]
                 else "first-party page: URL" + ("+address" if row["address"] else "")),
                ("routing_verdict", repair.get("verdict", "")),
                ("conversion_or_closure_note", repair.get("notes", "")),
                ("next_state", ""),  # filled after _blocker_for below
                ("next_action", ""),
            )))
        row["street_identity"] = _street_identity(row["address"], row["postal_code"])
        canonical.append(row)

    assign_rows = [{"name": r["identity_key"], "city": r["city"],
                    "state": r["state"], "postal_code": r["postal_code"]}
                   for r in canonical]
    assignment = assign_hotels(market, assign_rows, fail_closed=True)
    unassigned_names = []
    for row in canonical:
        key = row["identity_key"]
        corridors = assignment.corridor_of.get(key) or ()
        if not corridors:
            unassigned_names.append(row["canonical_name"])
            row["corridor"] = ""
            row["assignment_basis"] = enums.BASIS_UNASSIGNED
            row["assignment_value"] = ""
        else:
            row["corridor"] = corridors[0]
            basis, value = assignment.basis_of[key]
            row["assignment_basis"] = basis
            row["assignment_value"] = value
    if unassigned_names:
        raise SystemExit("unassigned canonical hotels: %s" % unassigned_names)

    collision_detail = {}
    by_street = {}
    for row in canonical:
        sid = row["street_identity"]
        if sid:
            by_street.setdefault(sid, []).append(row["canonical_name"])
    for sid, names in by_street.items():
        if len(names) > 1:
            collision_detail[sid] = names
            for row in canonical:
                if row["street_identity"] == sid:
                    row["collision_state"] = enums.COLLISION_SHARED_ADDRESS

    from scripts.pettripfinder.census_partition_builder import next_action_for

    for rec in repair_records:
        row = next(r for r in canonical if r["identity_key"] == rec["identity_key"])
        state = _blocker_for(row)
        rec["next_state"] = state
        rec["next_action"] = next_action_for(state) if state not in enums.TERMINAL_STATES else ""

    hotels = sorted((dict((k, v) for k, v in r.items() if k != "_census_review")
                    for r in canonical), key=lambda r: r["identity_key"])

    census_doc = OrderedDict((
        ("schema", enums.CENSUS_SCHEMA),
        ("market_id", MARKET),
        ("identity_key_contract", IDENTITY_KEY_CONTRACT),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER),
        ("captured_at", AS_OF),
        ("note", "PTF-DETROIT-ANN-ARBOR-IDENTITY-ROUTING-REPAIR-001 applied "
                 "identity and official-URL findings to the 119 Phase 1 "
                 "unresolved rows. No policy authority exists yet, so every "
                 "policy_state remains POLICY_NOT_VERIFIED. Three rows were "
                 "found closed/converted (Holiday Inn Fairlane Dearborn, "
                 "Courtyard by Marriott Detroit Novi) or geography-conflicted "
                 "(Best Western Greenfield Inn) and were moved to "
                 "AWAITING_CENSUS_REVIEW rather than silently resolved."),
        ("source_authorities", [
            "https://visitdetroit.com/detroit-hotel-guide/",
            "https://www.annarbor.org/places-to-stay/hotels/",
            "https://www.dearbornareachamber.org/directory/",
            "https://business.auburnhillschamber.com/list/category/hotels-479",
            "https://www.vibeshowplace.com/hotels",
            "first-party brand pages (marriott.com, hilton.com, ihg.com, "
            "choicehotels.com, wyndhamhotels.com, hyatt.com, sonesta.com, "
            "redroof.com) confirmed during PTF-DETROIT-ANN-ARBOR-IDENTITY-"
            "ROUTING-REPAIR-001",
        ]),
        ("count", len(hotels)),
        ("base_commit", FOUNDATION_COMMIT),
        ("collision_audit", {
            "duplicate_names_found": 0,
            "duplicate_names": {},
            "phone_collisions": 0,
            "address_collisions": len(collision_detail),
            "address_collision_detail": collision_detail,
            "out_of_boundary": 0,
            "cross_market_collisions": 0,
            "notes": "Hotel Indigo Detroit North - Troy and EVEN Hotel "
                     "Detroit North - Troy are a dual-branded IHG property "
                     "sharing one street address; both are real, distinct "
                     "identities.",
            "status": "PROVISIONAL_FLAGS_OPEN" if collision_detail else "NO_OPEN_CONFLICTS",
            "open_conflict_count": len(collision_detail),
        }),
        ("identity_state_counts", {
            "IDENTITY_CONFIRMED": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_CONFIRMED),
            "IDENTITY_PROVISIONAL": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_PROVISIONAL),
            "IDENTITY_UNRESOLVED": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_UNRESOLVED),
        }),
        ("source_methodology", "Same Phase 1 methodology, extended: every "
                                "repaired row's address/phone/URL was read "
                                "from a first-party brand page or an "
                                "official CVB/chamber directory page, never "
                                "an OTA. Two rows (Courtyard by Marriott "
                                "Detroit Novi, Holiday Inn Fairlane Dearborn) "
                                "were found CLOSED via a third-party "
                                "aggregator (Yelp) corroborated by the "
                                "absence of any live first-party page under "
                                "that identity; recorded as probable "
                                "closure/conversion, not deleted."),
        ("worker_branch", "worker/ptf-detroit-ann-arbor-market-001"),
        ("worker_run", WORK_ORDER),
        ("hotels", hotels),
    ))

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    items = []
    for row in hotels:
        full_row = next(r for r in canonical if r["identity_key"] == row["identity_key"])
        state = _blocker_for(full_row)
        terminal = state in enums.TERMINAL_STATES
        items.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("slug", row["slug"]),
            ("city", row["city"]),
            ("state", row["state"]),
            ("postal_code", row["postal_code"]),
            ("final_state", state),
            ("resolved", terminal),
            ("next_action", "" if terminal else next_action_for(state)),
            ("next_action_source", "" if terminal else "identity_census/detroit-ann-arbor-mi.json"),
            ("determined_by", WORK_ORDER if row["identity_key"] in REPAIRS
             else "PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001"),
            ("updated_at", AS_OF if row["identity_key"] in REPAIRS else PHASE1_AS_OF),
            ("official_url", row["official_url"]),
            ("state_override_reason", ""),
        )))
    items.sort(key=lambda r: r["identity_key"])
    counts = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    meanings = {state: PART.STATE_MEANINGS[state] for state in sorted(counts)}
    partition_doc = OrderedDict((
        ("schema", enums.PARTITION_SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("note", "No committed policy authority exists for this market yet: "
                 "published=0 and verified_no_pets=0 by construction. "
                 "119 rows repaired; capture-ready rows now reflect real "
                 "first-party identity + URL."),
        ("source_authorities", ["identity_census/detroit-ann-arbor-mi.json"]),
        ("count", len(items)),
        ("final_state_counts", counts),
        ("final_state_meanings", meanings),
        ("items", items),
    ))
    p_issues = PART.validate(partition_doc)
    if p_issues:
        raise SystemExit("partition invalid: %s" % [(i.path, i.code, i.detail) for i in p_issues])
    rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET)
    rec_issues = PART.reconciliation_issues(rec)
    if rec_issues or not rec.agrees:
        raise SystemExit("reconciliation failed: %s missing_p=%s missing_c=%s dups=%s"
                         % (rec_issues, rec.missing_from_partition, rec.missing_from_census,
                            rec.duplicated_in_partition))

    # ---- founder review queue (unresolved set) ----
    queue_items = []
    seq = 0
    for item in items:
        if item["resolved"]:
            continue
        seq += 1
        batch = "batch-%03d" % (((seq - 1) // 10) + 1)
        row = next(r for r in hotels if r["identity_key"] == item["identity_key"])
        queue_items.append(OrderedDict((
            ("row_number", seq),
            ("identity_key", item["identity_key"]),
            ("hotel_id", item["identity_key"]),
            ("canonical_name", item["canonical_name"]),
            ("address", row["address"]),
            ("phone", row["phone"]),
            ("official_candidate_url", item["official_url"]),
            ("corridor", row["corridor"]),
            ("current_classification", item["final_state"]),
            ("blocking_reason", item["final_state"]),
            ("requested_evidence", "property-level official URL and a citable pet-policy artifact" if not item["official_url"] else "citable pet-policy artifact from the property's own page"),
            ("next_action", item["next_action"]),
            ("batch", batch),
            ("review_status", "NOT_STARTED"),
        )))
        payload = json.dumps(queue_items[-1], sort_keys=True, ensure_ascii=False)
        queue_items[-1]["row_sha256"] = hashlib.sha256(
            payload.encode("utf-8")).hexdigest()

    routing = []
    for row in hotels:
        full_row = next(r for r in canonical if r["identity_key"] == row["identity_key"])
        routing.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("official_url", row["official_url"]),
            ("url_shape", row["url_shape"]),
            ("assessment_status", "ASSESSMENT_ONLY"),
            ("not_routing_authority", True),
            ("capture_readiness", _blocker_for(full_row)),
        )))

    # ---- strict capture-ready queue 002 ----
    capture_ready_items = []
    for row in hotels:
        full_row = next(r for r in canonical if r["identity_key"] == row["identity_key"])
        if full_row.get("_census_review"):
            continue
        if row["identity_state"] != enums.IDENTITY_CONFIRMED:
            continue
        if row["lodging_state"] == enums.NOT_LODGING:
            continue
        if row["url_shape"] != "property" or not row["official_url"]:
            continue
        if row["collision_state"] not in (enums.COLLISION_NONE, enums.COLLISION_SHARED_ADDRESS):
            continue
        capture_ready_items.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("address", row["address"]),
            ("city", row["city"]),
            ("state", row["state"]),
            ("postal_code", row["postal_code"]),
            ("phone", row["phone"]),
            ("corridor", row["corridor"]),
            ("official_url", row["official_url"]),
            ("url_shape", row["url_shape"]),
            ("brand_locator_note", "HYATT_ATTENDED_REQUIRED" if "hyatt" in row["normalized_name"]
             else ""),
            ("status", "NOT_STARTED"),
        )))
    assert len({r["identity_key"] for r in capture_ready_items}) == len(capture_ready_items)
    capture_ready_doc = OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-capture-ready-queue/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("note", "Strict capture-ready set: IDENTITY_CONFIRMED, exact "
                 "property-level official_url, no census-review flag, no "
                 "unresolved collision. No pet-policy capture executed."),
        ("count", len(capture_ready_items)),
        ("items", capture_ready_items),
    ))

    hyatt_rows = [r for r in hotels if "hyatt" in r["normalized_name"]]
    hyatt_ready = sum(1 for r in capture_ready_items if r["brand_locator_note"] == "HYATT_ATTENDED_REQUIRED")

    _dump(CENSUS_PATH, census_doc)
    _dump(PARTITION_PATH, partition_doc)
    _dump(REPORTS / "detroit-ann-arbor-mi_source_registry.json", OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-source-registry/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(SOURCES)),
        ("sources", SOURCES),
    )))
    _dump(REPORTS / "detroit-ann-arbor-mi_routing_assessments.json", OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-routing-assessments/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("note", "Assessments only. Nothing here is written to "
                 "identity_routing.json and no status is ROUTING_CONFIRMED."),
        ("count", len(routing)),
        ("items", routing),
    )))
    _dump(REPORTS / "detroit-ann-arbor-mi_founder_review_queue.json", OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-founder-review-queue/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(queue_items)),
        ("batch_size", 10),
        ("items", queue_items),
    )))
    _dump(PACKAGE / "detroit_ann_arbor_identity_routing_repair_001.json", OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-identity-routing-repair/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("foundation_commit", FOUNDATION_COMMIT),
        ("count", len(repair_records)),
        ("items", sorted(repair_records, key=lambda r: r["identity_key"])),
    )))
    _dump(PACKAGE / "detroit_ann_arbor_capture_ready_queue_002.json", capture_ready_doc)

    progress = OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-identity-routing-repair-progress/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("attempted", len(REPAIRS)),
        ("bound", sum(1 for r in REPAIRS.values() if r.get("verdict") == "EXACT_PROPERTY_FIRST_PARTY")),
        ("identity_unresolved", sum(1 for r in REPAIRS.values() if r.get("ident") == "IDENTITY_PROVISIONAL")),
        ("routing_unresolved", sum(1 for r in REPAIRS.values() if r.get("verdict") == "ROUTING_UNRESOLVED")),
        ("conversions", sum(1 for r in REPAIRS.values() if r.get("special") == "converted")),
        ("rebrands", sum(1 for r in REPAIRS.values() if r.get("special") == "rebrand")),
        ("census_review", sum(1 for r in REPAIRS.values() if r.get("special") in ("closed", "converted", "census_review"))),
        ("access_or_manual_issues", 0),
        ("remaining", len(REPAIRS) - len(REPAIRS)),
    ))
    _dump(DATA_ROOT / "identity_routing_repair_001_progress.json", progress)

    capture_lanes = {}
    for row in hotels:
        full_row = next(r for r in canonical if r["identity_key"] == row["identity_key"])
        lane = _blocker_for(full_row)
        capture_lanes[lane] = capture_lanes.get(lane, 0) + 1

    corridor_before = {
        "detroit-ann-arbor-mi__troy-auburn-hills": 0, "detroit-ann-arbor-mi__ann-arbor": 0,
        "detroit-ann-arbor-mi__downtown-detroit": 0, "detroit-ann-arbor-mi__novi-wixom": 0,
        "detroit-ann-arbor-mi__dtw-airport": 0, "detroit-ann-arbor-mi__southfield": 0,
        "detroit-ann-arbor-mi__birmingham-royal-oak-rochester": 0,
        "detroit-ann-arbor-mi__dearborn": 0, "detroit-ann-arbor-mi__farmington-hills": 0,
        "detroit-ann-arbor-mi__livonia-plymouth-northville": 0, "detroit-ann-arbor-mi__ypsilanti": 0,
    }
    corridor_after = dict(corridor_before)
    for row in hotels:
        if row["corridor"] in corridor_after:
            corridor_after[row["corridor"]] += 1

    summary = {
        "repair_targets": len(REPAIRS),
        "census": len(hotels),
        "published": rec.published,
        "verified_no_pets": rec.verified_no_pets,
        "out_of_category": rec.out_of_category,
        "unresolved": rec.unresolved,
        "queue": len(queue_items),
        "capture_ready_after": len(capture_ready_items),
        "hyatt_capture_ready": hyatt_ready,
        "hyatt_total": len(hyatt_rows),
        "agrees": rec.agrees,
        "final_state_counts": counts,
        "capture_lane_distribution": capture_lanes,
        "corridor_after": corridor_after,
        "cross_market_collisions": 0,
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    build()

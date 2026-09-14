"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

IDENTITY_ONLY_PAGES: properties whose OWN page states their address but no
operative pet policy the shared reader reads. Each row: (name, street, city,
postal, phone, url, the sha256 (prefix) of the document read, note). They open or
confirm a building and carry no policy. The Extended Stay America and Motel 6 /
Studio 6 rows were read in the attended browser (the brands refuse a plain
client); their documents were hashed in the same browser call.

COMPETITOR_LEADS: names only, from web-search result pages summarising
competitor pet-travel directories and hotel lists. A lead proposes and never
decides; its pet claims are never read.
"""
from __future__ import annotations

IDENTITY_ONLY_PAGES = [
    ("Extended Stay America - Savannah - Pooler", "500 Outlets Parkway South", "Pooler", "31322", "+19122021055",
     "https://www.extendedstayamerica.com/hotels/ga/savannah/savannah-pooler", "21d08b86d1b6",
     "the brand's own property page (attended browser) states the address in its Hotel JSON-LD; its pet wording is a "
     "'Pet-friendly room' amenity chip and a terms-of-use fee schedule ('Not to exceed a $25.00 per day cleaning fee'), "
     "which establish no acceptance"),
    ("Extended Stay America - Savannah - Midtown", "5511 Abercorn St.", "Savannah", "31405", "+19126920076",
     "https://www.extendedstayamerica.com/hotels/ga/savannah/midtown", "762c95580ccf",
     "the brand's own property page (attended browser) states the address in its Hotel JSON-LD; its pet wording is an "
     "amenity chip and a terms-of-use fee schedule only"),
    ("Motel 6 Savannah, GA - Midtown", "201 Stephenson Avenue", "Savannah", "31405", "",
     "https://www.motel6.com/property/motel-savannah-ga-georgia-us-293171/", "e5bfcec72fe7",
     "the brand's own property page (attended browser) states the street in its JSON-LD and 31405 in its text; its pet "
     "wording is the chain's 'Pets Allowed' / 'Pets stay free' amenity and promotion labels, not a property statement"),
    ("Studio 6 Extended Stay - Savannah, GA", "60 West Montgomery Cross Road", "Savannah", "31406", "",
     "https://www.motel6.com/property/motel-savannah-ga-georgia-us-293207/", "2746faf922a7",
     "the brand's own property page (attended browser); street in its JSON-LD, 31406 in its text; 'Pets Allowed' label only"),
    ("Motel 6 Pooler, GA - Savannah Airport", "1016 East US Hwy 80", "Pooler", "31322", "",
     "https://www.motel6.com/property/motel-pooler-georgia-us-293184/", "794f0a9f1c1a",
     "the brand's own property page (attended browser); street in its JSON-LD, 31322 in its text; marketing copy calls it "
     "'pet-friendly' (a label, not a policy)"),
    ("Motel 6 Savannah, GA - Gateway & I-95", "6 Gateway Boulevard East", "Savannah", "31419", "",
     "https://www.motel6.com/property/motel-savannah-ga-georgia-us-293154/", "125b0cf7f56e",
     "the brand's own property page (attended browser); street in its JSON-LD, 31419 in its text; 'Pet-Friendly "
     "Accommodation' label only. Shares its street with Studio 6 Gateway (a second G6 property id at the same address)"),
    ("Studio 6 Extended Stay - Savannah, GA - Gateway & I-95", "6 Gateway Boulevard East", "Savannah", "31419", "",
     "https://www.motel6.com/property/motel-savannah-ga-georgia-us-293157/", "82ae87394255",
     "the brand's own property page (attended browser); shares 6 Gateway Boulevard East with Motel 6 Gateway"),
    ("WoodSpring Suites Savannah Garden City", "4912 Augusta Road", "Savannah", "31408", "",
     "https://www.woodspring.com/extended-stay-hotels/locations/georgia/savannah/woodspring-suites-savannah-garden-city",
     "8354180e27d0",
     "the brand's own property page states '4912 Augusta Road' / 31408; its Pet Policy block ('Limit 2 dogs under 80 lbs. per "
     "room. No cats. Non-refundable deposit of $75 UDS and then $10 per day per pet.') is read FEE_ONLY by the shared reader"),
    ("WoodSpring Suites Savannah Pooler", "122 Godley Station Blvd South", "Pooler", "31322", "",
     "https://www.woodspring.com/extended-stay-hotels/locations/georgia/savannah-hinesville-statesboro/woodspring-suites-savannah-pooler",
     "c6d859051ee6",
     "the brand's own property page states '122 Godley Station Blvd South' / 31322; its Pet Policy block opens with a service-"
     "animal sentence and is read SERVICE_ANIMAL_ONLY by the shared reader"),
    ("Azalea Inn and Villas", "217 E Huntingdon St", "Savannah", "31401", "(912) 236-6080",
     "https://www.azaleainn.com/Home/FrequentlyAskedQuestions", "cd61749900b6",
     "the inn's own site states '217 E Huntingdon St Savannah, GA 31401'; its FAQ refusal ('Sorry, none of our rooms are "
     "pet or ESA friendly') is a sentence the shared reader does not read, so it is held, never reworded"),
]

_LEAD_SRC = ("web search result pages summarising competitor Savannah hotel and pet-friendly lodging lists "
             "(BringFido, TripAdvisor, Expedia / Orbitz, Savannah.com and hotel-list aggregators; names only; "
             "competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    "Best Western Savannah Historic District",
    "East Bay Inn",
    "Thunderbird Inn",
    "Kimpton Brice Hotel",
    "Staybridge Suites Savannah Historic District",
    "Homewood Suites by Hilton Savannah Historic District Riverfront",
    "Holiday Inn Savannah Historic District",
    "Quality Inn Savannah Historic District",
    "The DeSoto Savannah",
    "Residence Inn by Marriott Savannah Downtown Historic District",
    "Hampton Inn & Suites Savannah I-95 South Gateway",
    "Olde Harbour Inn",
    "Hotel Bardo Savannah",
    "Country Inn & Suites by Radisson Savannah Gateway GA",
    "Country Inn & Suites by Radisson Savannah I-95 North GA",
    "Hampton Inn Savannah I-95 North",
    "Eliza Thompson House",
    "The Gastonian",
    "The Marshall House",
    "Kehoe House",
    "Hamilton-Turner Inn",
    "Forsyth Park Inn",
    "Planters Inn on Reynolds Square",
    "The Douglas",
    "Mansion on Forsyth Park",
    "The Ballastone Inn",
    "McMillan Inn",
    "Green Palm Inn",
    "Zeigler House Inn",
    "Extended Stay America Premier Suites Savannah Pooler",
    "InTown Suites Extended Stay Savannah GA Garden City",
    "Red Roof Inn & Suites Savannah Airport",
)]

#: No regional visitor-center roster beyond the two bureaus in this market.
REGIONAL_VISITOR_CENTER_SOURCE = ""
REGIONAL_VISITOR_CENTER_LEADS = ()

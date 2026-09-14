"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

IDENTITY_ONLY_PAGES: properties whose OWN page states their address but no
operative pet policy the shared reader reads. Each row: (name, street, city,
postal, phone, url, the sha256 (prefix) of the document read, note). They open or
confirm a building and carry no policy.

COMPETITOR_LEADS: names only, from web-search result pages summarising
competitor pet-travel directories and hotel lists. A lead proposes and never
decides; its pet claims are never read.
"""
from __future__ import annotations

_ESA_NOTE = ("the brand's own property page (attended browser, same-origin fetch; hashed in the same call) states the "
             "address in its Hotel JSON-LD; its pet wording is a 'Pet-friendly room' amenity chip and a terms-of-use fee "
             "schedule ('Pet fees: Not to exceed a $25.00 per day cleaning fee plus tax, for the first six (6) nights, per "
             "pet.'), which establish no acceptance (AMENITY_CHIP_ONLY / FEE_ONLY)")
IDENTITY_ONLY_PAGES = [
    ("Extended Stay America - Charleston - Airport", "5045 N. Arco Ln.", "North Charleston", "29418", "+18437403440",
     "https://www.extendedstayamerica.com/hotels/sc/charleston/airport", "7bda0b8da1c3", _ESA_NOTE),
    ("Extended Stay America - Charleston - North Charleston - I-526", "4835 Rivers Ave", "North Charleston", "29406",
     "+18435293055", "https://www.extendedstayamerica.com/hotels/sc/charleston/north-charleston-i-526", "e59ebc65c2c8",
     _ESA_NOTE),
    ("Extended Stay America - Charleston - Ashley Phosphate Rd.", "7477 Northside Dr", "Charleston", "29420",
     "+18435535222", "https://www.extendedstayamerica.com/hotels/sc/charleston/ashley-phosphate-rd", "05c22de57167",
     _ESA_NOTE),
    ("Extended Stay America - Charleston - Northwoods Blvd.", "7641 Northwoods Blvd.", "North Charleston", "29406",
     "+18435530036", "https://www.extendedstayamerica.com/hotels/sc/charleston/northwoods-blvd", "6c1570b14bb3",
     _ESA_NOTE),
    ("WoodSpring Suites North Charleston Airport I-526", "4475 Leeds Place West", "North Charleston", "29405",
     "", "https://www.woodspring.com/extended-stay-hotels/locations/south-carolina/charleston/woodspring-suites-north-charleston",
     "37959b8f4ca5",
     "the brand's own property page states its address (29405-8402); its Pet Policy block ('Non refundable per pet fee. 50 "
     "USD registration fee for 1-7 nights, 20 USD begins on 8th night for each subsequent week. A max of 80 pounds total "
     "and a max of 2 pets (dogs, no cats).') states fees and limits but no acceptance the shared reader reads "
     "(QUOTE_NOT_OPERATIVE); held, never reworded"),
]

_LEAD_SRC = ("web search result pages summarising competitor Charleston hotel and pet-friendly lodging lists "
             "(names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    # BringFido / Tripadvisor / hotel-list summaries (names only)
    "The Charleston Place", "Kings Courtyard Inn", "John Rutledge House Inn", "Barksdale House Inn",
    "Live Oak Charleston Historic District a Tribute Portfolio Hotel", "Wentworth Mansion", "Fulton Lane Inn",
    "The Vendue", "Andrew Pinckney Inn", "Market Pavilion Hotel", "Hotel Bella Grace", "The Restoration on King",
    "Ansonborough Inn", "Water's Edge Inn", "Days Inn Goose Creek", "Days Inn by Wyndham Ladson Summerville Charleston",
    "West Ashley Inn", "North Charleston Lodge", "Charleston Creekside Inn", "Motel 6 Summerville", "Carolina Inn",
    "Quality Inn Goose Creek", "Courtyard by Marriott Charleston Summerville", "Sweetgrass Inn",
)]

#: Folly Beach's own visitor directory, 'Hotels & Inns' (names only; tier 2; never policy).
REGIONAL_VISITOR_CENTER_SOURCE = "https://visitfolly.com/stay-directory/"
REGIONAL_VISITOR_CENTER_LEADS = (
    "Beachside Boutique Inn", "Folliday Inn", "Hotel Folly", "Regatta Inn", "Riverside Inn and Cottages",
    "Tides Folly Beach", "Vera Hotel", "Water's Edge Inn",
)

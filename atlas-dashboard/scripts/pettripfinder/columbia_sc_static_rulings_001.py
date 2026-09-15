"""PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

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
_ESA = "https://www.extendedstayamerica.com/hotels/sc/"
IDENTITY_ONLY_PAGES = [
    ("Extended Stay America - Columbia - Ft. Jackson", "5430 Forest Dr.", "Columbia", "29206", "+18037822025",
     _ESA + "columbia/ft-jackson", "f82ba1df2053", _ESA_NOTE),
    ("Extended Stay America - Columbia - West - Interstate-126", "450 Gracern Rd.", "Columbia", "29210", "+18032517878",
     _ESA + "columbia/west-interstate-126", "1cb11e3bde74", _ESA_NOTE),
    ("Extended Stay America - Columbia - Northwest/Harbison", "1170 Kinley Road", "Irmo", "29063", "+18037818590",
     _ESA + "columbia/northwest-harbison", "d766ccace9a6", _ESA_NOTE),
    ("Extended Stay America - Columbia - Greystone", "180 Stoneridge Dr.", "Columbia", "29210", "+18037710303",
     _ESA + "columbia/west-stoneridge-dr", "9002c860ffdf", _ESA_NOTE),
]

_LEAD_SRC = ("web search result pages summarising competitor Columbia SC hotel and pet-friendly lodging lists "
             "(names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    # BringFido city-page search-result summary (Columbia SC) and hotelguides.com Columbia / West Columbia / Lexington /
    # Two Notch Road / Broad River Road lists
    "Home2 Suites by Hilton Columbia Southeast Fort Jackson", "Motel 6 Columbia SC - Fort Jackson Area",
    "Hyatt Place Columbia Harbison", "Graduate by Hilton Columbia SC", "Hilton Garden Inn Columbia Northeast",
    "Embassy Suites Greystone Columbia", "Best Western Plus Northeast Columbia", "Lexington Inn & Suites",
    "Hawthorn Suites by Wyndham Columbia", "Microtel Inn by Wyndham Columbia", "Days Inn Riverbanks Zoo Columbia",
    "Wingate by Wyndham Lexington", "La Quinta Inn Maingate Fort Jackson Columbia", "Super 8 Motel Columbia",
    "stayAPT Suites Harbison Irmo", "Extended Stay America Suites Irmo", "Baymont Inn & Suites Fort Jackson Columbia",
)]

#: No regional visitor-center roster in this market (names only; tier 2; never policy).
REGIONAL_VISITOR_CENTER_SOURCE = ""
REGIONAL_VISITOR_CENTER_LEADS = (
)

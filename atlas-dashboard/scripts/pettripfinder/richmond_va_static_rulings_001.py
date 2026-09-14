"""PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

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
_ESA = "https://www.extendedstayamerica.com/hotels/va/richmond/"
IDENTITY_ONLY_PAGES = [
    ("Extended Stay America - Richmond - W. Broad Street - Glenside - North", "6807 Paragon Pl.", "Richmond", "23230",
     "+18042857050", _ESA + "w-broad-street-glenside-north", "57308763ba64", _ESA_NOTE),
    ("Extended Stay America - Richmond - W. Broad Street - Glenside - South", "6811 Paragon Pl.", "Richmond", "23230",
     "+18042852065", _ESA + "w-broad-street-glenside-south", "88cb9c32a9a2", _ESA_NOTE),
    ("Extended Stay America - Richmond - Innsbrook", "10060 W. Broad St.", "Glen Allen", "23060",
     "+18047470840", _ESA + "innsbrook", "1325e7e0064e", _ESA_NOTE),
    ("Extended Stay America - Richmond - West End - I-64", "10961 W. Broad St.", "Glen Allen", "23060",
     "+18047478898", _ESA + "west-end-i-64", "f8aa5c17624b", _ESA_NOTE),
    ("Extended Stay America - Richmond - Glen Allen - Short Pump", "4231 Park Place Court", "Glen Allen", "23060",
     "+18047475253", _ESA + "glen-allen-short-pump", "b1833eb1c579", _ESA_NOTE),
]

_LEAD_SRC = ("web search result pages summarising competitor Richmond hotel and pet-friendly lodging lists "
             "(names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    # BringFido / Tripadvisor / hotel-list search-result summaries (names only)
    "Candlewood Suites Richmond - West Broad", "Quirk Hotel Richmond", "Residence Inn Richmond Midtown/Glenside",
    "Hampton Inn & Suites Richmond Glenside", "The Commonwealth", "Aloft Richmond West Short Pump", "Pinball Pete's BnB",
    "Country Inn & Suites by Radisson Richmond I-95 South", "Moxy Richmond Downtown", "The Jefferson Hotel",
    "Graduate Richmond", "Delta Hotels Richmond Downtown", "Embassy Suites Richmond",
)]

#: No regional visitor-center roster in this market (names only; tier 2; never policy).
REGIONAL_VISITOR_CENTER_SOURCE = ""
REGIONAL_VISITOR_CENTER_LEADS = (
)

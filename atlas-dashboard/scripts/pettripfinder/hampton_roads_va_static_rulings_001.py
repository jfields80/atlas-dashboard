"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

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
_ESA = "https://www.extendedstayamerica.com/hotels/va/"
IDENTITY_ONLY_PAGES = [
    ("Extended Stay America - Norfolk - Virginia Beach", "5757 Cleveland Street", "Virginia Beach", "23462",
     "+17574909367", _ESA + "virginia-beach/virginia-beach", "5319326cba57", _ESA_NOTE),
    ("Extended Stay America - Virginia Beach - Independence Blvd.", "4548 Bonney Rd.", "Virginia Beach", "23462",
     "+17574739200", _ESA + "virginia-beach/independence-blvd", "85c2019f2ca8", _ESA_NOTE),
    ("Extended Stay America - Chesapeake - Churchland Blvd.", "3214 Churchland Blvd.", "Chesapeake", "23321",
     "+17574839200", _ESA + "chesapeake/churchland-blvd", "9405befa06f2", _ESA_NOTE),
    ("Extended Stay America - Newport News - Oyster Point", "11708 Jefferson Ave.", "Newport News", "23606",
     "+17578732266", _ESA + "newport-news/oyster-point", "e893d1ea5ebe", _ESA_NOTE),
    ("Extended Stay America - Newport News - Yorktown", "200 Cybernetics Way", "Yorktown", "23693",
     "+17578748884", _ESA + "newport-news/yorktown", "36aae4da6188", _ESA_NOTE),
    ("Extended Stay America - Chesapeake - Crossways Blvd.", "1540 Crossways Blvd.", "Chesapeake", "23320",
     "+17574248600", _ESA + "chesapeake/crossways-blvd", "c102067ea3bb", _ESA_NOTE),
]

_LEAD_SRC = ("web search result pages summarising competitor Hampton Roads hotel and pet-friendly lodging lists "
             "(names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    # BringFido city-page and property-page search-result summaries (Virginia Beach, Norfolk, Chesapeake, Newport News)
    "Hampton Inn Norfolk Virginia Beach", "Extended Stay America Suites - Norfolk - Virginia Beach",
    "Residence Inn by Marriott Virginia Beach Oceanfront", "Wyndham Virginia Beach Oceanfront", "Motel 6 Virginia Beach",
    "Embassy Suites by Hilton Virginia Beach Oceanfront Resort", "La Quinta by Wyndham Virginia Beach",
    "Best Western Plus Chesapeake Bay-Norfolk", "Hampton Inn Norfolk Naval Base", "Delta Hotels by Marriott Chesapeake Norfolk",
    "Candlewood Suites Chesapeake-Suffolk", "Hilton Garden Inn Newport News", "Hampton Inn & Suites Newport News (Oyster Point)",
    "Holiday Inn Newport News - Hampton", "Motel 6 Newport News VA - Fort Eustis", "Comfort Inn Newport News - Hampton I-64",
)]

#: No regional visitor-center roster in this market (names only; tier 2; never policy).
REGIONAL_VISITOR_CENTER_SOURCE = ""
REGIONAL_VISITOR_CENTER_LEADS = (
)

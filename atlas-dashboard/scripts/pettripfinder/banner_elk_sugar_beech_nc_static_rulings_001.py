"""PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

IDENTITY_ONLY_PAGES: properties whose OWN site states their address but no
operative pet policy. Each row: (name, street, city, postal, phone, url, the
sha256 prefix of the document read, note). They open or confirm a building and
carry no policy.

COMPETITOR_LEADS: names only, from web-search result pages summarising
competitor pet-travel and hotel directories. A lead proposes and never decides;
its pet claims are never read.
"""
from __future__ import annotations

IDENTITY_ONLY_PAGES = [
    ("The Inn at Shady Lawn", "330 Cranberry Street", "Newland", "28657", "(828) 742-1763",
     "https://theinnatshadylawn.com/", "ea5891538fcb",
     "the inn's own home page states 'Address 330 Cranberry Street Newland, NC, NC 28657'; its pages state no pet "
     "policy (reservations run through an external booking engine)"),
    ("Top of the Beech Inn", "606 Beech Mountain Pkwy", "Beech Mountain", "28604", "(828) 387-2354",
     "http://www.beech-mountain.org/", "5ea29eed4a0c",
     "the inn's own page states 'Top of the Beech Inn * 606 Beech Mountain Pkwy * ... NC 28604'; no pet policy on "
     "the pages read, and the operator's beechmountaininns.com refused a plain client (403) and the attended browser"),
    ("Linville Falls Lodge & Cottages", "48 North Carolina 183", "Linville Falls", "28647", "828-765-2658",
     "https://www.linvillefallslodge.com/", "775ed240f5f9",
     "the lodge's own site (JSON-LD) states '48 North Carolina 183', postal code 28647 -- a postal code no corridor "
     "claims (the map's 8890 NC Highway 183, Newland 28657 is superseded by the property's own address)"),
]

_LEAD_SRC = ("web search result pages summarising competitor Banner Elk / Beech Mountain / Linville hotel and "
             "pet-friendly lodging lists (names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    "The Lodge at Banner Elk",
    "Beech Mountain Inns",
    "The Inn at Shady Lawn",
    "Smoketree Lodge",
    "Beech Alpen Inn",
    "Azalea Inn Bed & Breakfast",
    "Inn at Elk River",
    "Tufts House Inn",
    "Perry House Bed & Breakfast",
    "The Banner Elk Inn B&B and Cottages",
    "Taylor House Inn",
    "Little Main Street Inn & Suites",
    "Linville Cottage Bed & Breakfast",
    "Deer Brook Inn Bed & Breakfast",
    "Eseeola Lodge",
    "Pixie Motor Inn",
    "Bear's Loft",
    "Hillcrest Haven",
)]

#: High Country Host is read as a DESTINATION roster in this market (its Avery listings
#: have their own pages), so no names-only regional roster is carried here.
REGIONAL_VISITOR_CENTER_SOURCE = "https://www.highcountryhost.com/lodging/hotels-motels-and-inns"
REGIONAL_VISITOR_CENTER_LEADS = ()

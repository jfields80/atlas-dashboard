"""PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

IDENTITY_ONLY_PAGES: properties whose OWN site states their address but no
operative pet policy. Each row: (name, street, city, postal, phone, url, the
sha256 of the document read, note). They open or confirm a building and carry
no policy.

COMPETITOR_LEADS: names only, from web-search result pages summarising
competitor pet-travel directories. A lead proposes and never decides; its pet
claims are never read.
"""
from __future__ import annotations

IDENTITY_ONLY_PAGES = [
    ("1878 Bed and Breakfast", "538 Carthage Street", "Cameron", "28326", "",
     "https://1878bedandbreakfast.com/", "7c21b18634fc",
     "the B&B's own home page (read in the attended browser; the plain client got 403) states '538 Carthage Street "
     "Cameron, NC 28326'; no pet wording on the pages read"),
    ("Carolina Pine Inn", "175 Persimmon Dr", "Pinebluff", "28373", "",
     "https://www.carolinapineinn.com/", "",
     "the inn's own home page (attended browser; plain client 403) states '175 Persimmon Dr, Pinebluff, NC, 28373'; "
     "no pet wording on the page read"),
    ("The Old Buggy Inn", "301 McReynolds St.", "Carthage", "28327", "+1 910 947 1901",
     "https://theoldbuggyinn.com/", "",
     "the inn's own home page (attended browser; plain client 403) states '301 McReynolds St. Carthage, NC 28327'; "
     "no pet wording on the home or privacy pages"),
    ("AmeriVu Inn & Suites Aberdeen", "1408 North Sandhill Blvd", "Aberdeen", "28315", "",
     "https://www.amerivuinn.com/aberdeen/", "1c6f0500aa4b",
     "the hotel's own page states '1408 North Sandhill Blvd Aberdeen, North Carolina 28315' (the map's Super 8 and a "
     "directory's Motel 6 at the same street are earlier flags); its only pet word is an amenity chip "
     "'Pet-Friendly', which never establishes a policy"),
    ("Pine Crest Inn", "50 Dogwood Road", "Pinehurst", "28374", "910-295-6121",
     "https://www.pinecrestinnpinehurst.com/", "0e3070ceb221",
     "the inn's own site states '50 Dogwood Road, Pinehurst, NC 28374'; its home, stay, rates and room pages carry no "
     "pet wording"),
    ("Pine Needles Lodge & Golf Club", "1005 Midland Road", "Southern Pines", "28387", "",
     "https://pineneedleslodge.com/", "91ee3c20d06d",
     "the lodge's own site states '1005 Midland Road, Southern Pines, NC 28387'; its home, FAQ and amenities pages "
     "carry no pet wording"),
    ("The Inn at Mid Pines", "1010 Midland Road", "Southern Pines", "28387", "",
     "https://midpinesinn.com/", "be82eefa4f3d",
     "the inn's own site states '1010 Midland Road, Southern Pines, NC 28387'; its home and FAQ pages carry no pet "
     "wording"),
]

_LEAD_SRC = ("web search result pages summarising competitor Pinehurst / Southern Pines / Aberdeen pet-friendly "
             "lodging lists (names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    "Hampton Inn & Suites Southern Pines-Pinehurst",
    "Hilton Garden Inn Southern Pines Pinehurst",
    "Homewood Suites by Hilton Olmsted Village (near Pinehurst)",
    "SureStay Plus Hotel by Best Western Southern Pines Pinehurst",
    "TownePlace Suites Southern Pines Aberdeen",
    "Residence Inn by Marriott Pinehurst Southern Pines",
    "Microtel Inn & Suites by Wyndham Southern Pines Pinehurst",
    "Days Inn Conference Center Southern Pines",
    "Super 8 Motel Southern Pines Aberdeen",
    "Knollwood House",
    "Beggar's Ride Bed, Breakfast and Barn",
    "Conroy B&B",
    "Pine Gables of Aberdeen",
    "Duck Smith House Bed & Breakfast",
    "Lucky Bar Farm",
    "The MacPherson House",
)]

#: No regional visitor-centre roster beyond the CVB's own index in this market.
REGIONAL_VISITOR_CENTER_SOURCE = "https://homeofgolf.com/plan-your-visit/welcome-centers/"
REGIONAL_VISITOR_CENTER_LEADS = ()

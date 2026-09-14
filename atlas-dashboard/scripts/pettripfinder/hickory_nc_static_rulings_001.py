"""PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

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
    ("2nd Street Inn", "13 2nd Street NE", "Hickory", "28601", "",
     "https://www.2ndstreetinn.com/", "ea99757c9cc3c9f2f3ab4d04e2e201b9d302c39ab40ec3e0ce0d51588e195fcf",
     "the inn's own home page states '13 2nd Street NE Hickory, NC 28601'; neither the home page nor its booking page "
     "carries any pet wording"),
    ("The Dragonfly Inn", "224 3rd Ave NW", "Hickory", "28601", "",
     "https://dragonflyinnhickory.com/", "8051ba317f04",
     "the inn's own site (Organization JSON-LD) states '224 3rd Ave NW, Hickory, North Carolina 28601'; its only pet "
     "words are the booking engine's translation vocabulary ('Pets welcome' / 'Pets not allowed' side by side), never "
     "an operative statement"),
    ("Motel 6 Hickory, NC", "484 U.S. Highway 70 Southwest", "Hickory", "28602", "",
     "https://www.motel6.com/property/motel-hickory-north-carolina-us-293883/",
     "cb3297b58d05bda3835133cb0ef376f8e246cba8be9b71e285777aaa3792b7f8",
     "the brand's own property page (attended browser; plain client timed out) states '484 U.S. Highway 70 Southwest, "
     "Hickory, North Carolina, 28602' (JSON-LD and property record); its pet words are amenity chips ('Pets Allowed', "
     "'Up to 2 pets allowed') and a chain-wide footer link ('Pets Stay Free Details'); the property's own pet policy "
     "renders client-side behind 'View pet policy' and was not read, so no policy is recorded"),
    ("Studio 6 Hickory, NC", "484 U.S. Highway 70 Southwest", "Hickory", "28602", "",
     "https://www.motel6.com/property/motel-hickory-north-carolina-us-294232/", "",
     "the brand's own property page for property 294232 states the same street and ZIP as Motel 6 Hickory (293883); "
     "two brand property ids at one street, co-location unproven; amenity chips only"),
]

_LEAD_SRC = ("web search result pages summarising competitor Hickory / Conover / Newton pet-friendly lodging lists "
             "(names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    "Comfort Inn Conover-Hickory",
    "MainStay Suites Conover-Hickory",
    "Hilton Garden Inn Hickory",
    "Red Roof Inn Hickory",
    "Crowne Plaza Hotel Hickory",
    "Days Inn & Suites by Wyndham Hickory",
    "Days Inn by Wyndham Conover-Hickory",
    "Sleep Inn Hickory South",
    "Studio 6 Hickory NC",
    "Holiday Inn Express Hotel & Suites Conover - Hickory Area",
    "Budget Inn Express Hickory",
)]

#: No regional visitor-centre roster beyond the tourism organisation's own index in this market.
REGIONAL_VISITOR_CENTER_SOURCE = ""
REGIONAL_VISITOR_CENTER_LEADS = ()

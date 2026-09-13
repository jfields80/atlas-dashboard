"""PTF-OUTER-BANKS-NC-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

IDENTITY_ONLY_PAGES: properties whose OWN site states their address but no
operative pet policy. Each row: (name, street, city, postal, phone, url, the
sha256 of the document read, note). They open or confirm a building and carry
no policy.

COMPETITOR_LEADS: names only, from web-search result pages summarising
competitor pet-travel directories. A lead proposes and never decides; its pet
claims are never read.
"""
from __future__ import annotations

IDENTITY_ONLY_PAGES = []

_LEAD_SRC = ("web search result pages summarising competitor Outer Banks pet-friendly lodging lists "
             "(names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    "Travelodge by Wyndham Outer Banks/Kill Devil Hills",
    "TownePlace Suites by Marriott Outer Banks Kill Devil Hills",
    "John Yancey Oceanfront Inn",
    "Hilton Garden Inn Outer Banks/Kitty Hawk",
    "Comfort Inn South Oceanfront",
    "Blue Heron Motel",
    "Hampton Inn & Suites Outer Banks/Corolla",
    "The Inn at Corolla Light",
    "The Sanderling Resort",
    "Heart of Manteo Motor Lodge",
    "White Doe Inn",
    "Island Guesthouse and Motel",
)]

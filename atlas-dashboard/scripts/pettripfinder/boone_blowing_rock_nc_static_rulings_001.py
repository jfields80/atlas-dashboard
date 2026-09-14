"""PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 -- identity-only reads and competitor leads.

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
    ("The Inn at Ragged Gardens", "203 Sunset Drive", "Blowing Rock", "28605", "828-295-9703",
     "https://www.ragged-gardens.com/", "4ec7d9044d29",
     "the inn's own footer states 'Physical address: 203 Sunset Drive, Blowing Rock, NC 28605'; no pet policy on the "
     "pages read"),
    ("Gideon Ridge Inn", "202 Gideon Ridge Rd.", "Blowing Rock", "28605", "",
     "https://www.gideonridge.com/", "22bf61a75aad",
     "the inn's own page states '202 Gideon Ridge Rd. Blowing Rock, NC, 28605'; no pet policy on the page read"),
    ("Hellbender Bed & Beverage", "239 Sunset Dr", "Blowing Rock", "28605", "(828) 295-3487",
     "https://www.hellbender.bar/", "a01ca1b0036a",
     "the inn's own contact block states '239 Sunset Dr Blowing Rock, NC 28605'; no pet policy on the page read"),
    ("The Windmoor Hotel", "125 Sunset Drive", "Blowing Rock", "28605", "(828) 237-1255",
     "https://www.windmoorhotel.com/", "8771704f01ff",
     "the hotel's own page text states '125 Sunset Drive Blowing Rock, NC 28605'. Its JSON-LD carries 775 W King St, "
     "Boone -- The 1850 Hotel's address, a shared operator template -- and is NOT used. Its FAQ refusal ('... is not "
     "pet-friendly ...') is a sentence the shared reader does not read, so it is held, never reworded"),
    ("The Blowing Rock Manor", "567 Main Street", "Blowing Rock", "28605", "(828) 263-4180",
     "https://blowingrockmanor.com/", "5f1fe1b9071b",
     "the hotel's own page text states '567 Main Street Blowing Rock, NC 28605' (its JSON-LD carries the sister 1850 "
     "Hotel's Boone address and is not used); its FAQ refusal is a sentence the shared reader does not read"),
    ("Hemlock Inn and Suites", "134 Morris Street", "Blowing Rock", "28605", "(828)295-7987",
     "https://www.hemlockinn.net/", "fd80d5f3e9b1",
     "the inn's own page states '134 Morris Street PO Box 422 Blowing Rock, NC 28605'; its 'All of our rooms are "
     "non-smoking and pet-free.' is a sentence the shared reader does not read, so it is held"),
    ("The Inn at Crestwood", "3236 Shulls Mill Rd", "Boone", "28607", "",
     "https://www.crestwoodnc.com/pet-fee", "0da92f401924",
     "the inn's own pet page states '3236 Shulls Mill Rd, Boone, NC 28607'; its pet sentences are fee statements the "
     "shared reader classifies FEE_ONLY"),
    ("Boxwood Lodge", "671 Main St", "Blowing Rock", "28605", "",
     "https://www.thevillageinnsofblowingrock.com/", "10cf8e3e7a6e",
     "the Village Inns of Blowing Rock's own page (its operator's site; boxwoodlodge.com did not answer) carries a "
     "LodgingBusiness JSON-LD address '671 Main St, Blowing Rock 28605' for the lodge; the operator's pet sentence "
     "is one the shared reader does not read"),
    ("Rhode's Motor Lodge", "1377 Blowing Rock Rd.", "Boone", "28607", "828-865-1110",
     "https://www.rhodesmotorlodge.com/policies", "91b5db1b2fad",
     "the lodge's own policies page states '1377 BLOWING ROCK RD. HWY 321 BOONE, N.C. 28607'; its dog policy is read by "
     "the shared reader as FEE_ONLY"),
]

_LEAD_SRC = ("web search result pages summarising competitor Boone / Blowing Rock pet-friendly lodging lists "
             "(names only; competitor pet claims never read)")
COMPETITOR_LEADS = [(n, _LEAD_SRC) for n in (
    "Home2 Suites by Hilton Boone",
    "Hampton Inn & Suites Boone",
    "Graystone Lodge, an Ascend Collection Hotel",
    "La Quinta Inn & Suites by Wyndham Boone University",
    "Best Western Blue Ridge Plaza",
    "The Horton Hotel",
    "Village Inn of Blowing Rock",
    "Alpine Village Inn",
    "Hillwinds Inn",
    "Homestead Inn",
    "Inn at Ragged Gardens",
    "Chetola Resort",
    "Westglow Resort & Spa",
    "Green Park Inn",
    "Blowing Rock Inn",
    "Scottish Inns Boone",
    "Greenes Motel Boone",
)]

#: The regional visitor center's own lodging roster (High Country Host, the High Country's
#: regional visitor center at 6370 US-321 South, Blowing Rock): its "Hotels, Motels and Inns"
#: page, read 2026-09-13. Names only -- its descriptions carry no address; a lead proposes.
REGIONAL_VISITOR_CENTER_SOURCE = "https://highcountryhost.com/lodging/hotels-motels-and-inns"
REGIONAL_VISITOR_CENTER_LEADS = (
    "Mountainaire Inn and Log Cabins",
    "Country Inn and Suites Boone",
    "The Horton Hotel & Rooftop Lounge",
    "The Manor Blowing Rock",
    "TownePlace Suites Boone",
    "Rhodes Motor Lodge",
    "Alpine Village Inn",
    "Hidden Valley Motel",
    "Comfort Suites Boone University Area",
    "Quality Inn & Suites - University",
    "Holiday Inn Express of Boone",
    "Chetola Resort at Blowing Rock",
    "La Quinta Inn Suites",
    "Graystone Lodge, Ascend Hotel Collection",
    "Hemlock Inn",
    "Meadowbrook Inn",
    "Blowing Rock Inn",
    "Courtyard by Marriott",
    "Fairfield Inn & Suites",
    # outside, recorded so the refusal is a decision
    "Jefferson Landing Lodge & Golf",
    "Holiday Inn Express of Wilkesboro & Yadkin Valley Event Center",
)

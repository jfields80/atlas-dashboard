"""PTF-PHOENIX-AZ-HARDENED-SOURCE-READY-001 -- the vacation-rental / timeshare / resort-residence / venue filter.

Two mechanisms, both refusal DECISIONS with their reasons:

1. ``NOT_LODGING_WHY`` / ``LODGING_UNCONFIRMED`` -- matched on the full normalised name
   (``site_data.normalize_name``) of a census candidate, added only after that row's evidence was read.
2. ``nonhotel_by_name`` -- the order's Phase 5 rule applied to a row's OWN name: a vacation-home community, a
   villa / condo / townhome rental, a resort-residence club or a vacation-ownership (timeshare) resort is refused
   UNLESS a brand's own public hotel inventory or a hotel page read reached the row. When the operator itself lists
   those exact premises as a bookable hotel with its own property page, the row is judged on that page instead --
   that is the "prove exact public hotel operation" test, and a name alone never passes or fails it.

The reason string always starts with the exclusion class (VACATION_RENTAL / TIMESHARE / RESORT_RESIDENCE / NON_HOTEL)
so the accounting counts each class without re-deriving it.

Nothing here fetches and nothing here admits.
"""
from __future__ import annotations

import re

_APARTMENTS = ("NON_HOTEL -- apartment inventory rented by the unit, not a hotel selling public nightly rooms under a "
               "front desk; refused under the order's apartment rule")
_VENUE = "NON_HOTEL -- a venue, club or office, not public lodging"

#: Rows whose LODGING category cannot be settled from the evidence. Held as IDENTITY_REVIEW_REQUIRED. Empty at
#: authoring time; a later coverage-closure pass adds rows here only after reading that row's own evidence.
LODGING_UNCONFIRMED = {
}

#: Rows refused by their OWN full normalised name, each with its reason. Added only after that row's own
#: first-party evidence was read. PHOENIX's exposure is its RESORT-RESIDENCE, VACATION-CLUB and SHORT-TERM-RENTAL
#: stock: the Paradise Valley / North Scottsdale resort residences and villas, the Marriott / Hilton / Wyndham /
#: Westgate vacation clubs, Old Town Scottsdale's serviced-apartment operators (Sonder, Mint House, Kasa,
#: Placemakr) and the Valley's casita rentals. Nothing is inherited from Denver: every Denver ruling (Vail Resorts'
#: Broomfield office, Chief Hosa Lodge, the Artesian) names Colorado premises and is not carried.
NOT_LODGING_WHY = {
}

#: VACATION-OWNERSHIP PROPERTIES KEYED BY THE BRAND'S OWN PROPERTY CODE. A brand inventory lists these beside its
#: hotels, and the public-hotel-lane override in ``nonhotel_by_name`` would otherwise admit them on that listing
#: alone. Each code was read on the brand's own page by this order (phoenix_az_browser_lane_001): the page names a
#: vacation club, villa resort or residence club, not a public hotel. TIMESHARE -- never admitted.
TIMESHARE_CODES = {
    ("MARRIOTT", "phxcv"): ("TIMESHARE -- Marriott's Canyon Villas (5220 E Marriott Dr, 85054) is a Marriott Vacation "
                            "Club villa resort; its own page is titled 'Phoenix Vacation Resort'"),
    ("MARRIOTT", "phxso"): ("TIMESHARE -- Sheraton Desert Oasis Villas, Scottsdale (17700 N Hayden Rd, 85255) is a "
                            "Sheraton / Marriott Vacation Club villa resort"),
    ("MARRIOTT", "phxwk"): ("TIMESHARE -- The Westin Kierland Villas, Scottsdale (15620 N Clubgate Dr, 85254) is a "
                            "Westin / Marriott Vacation Club villa resort"),
    ("MARRIOTT", "phxpr"): ("TIMESHARE -- Phoenician Residences, a Luxury Collection Residence Club (6000 E Camelback "
                            "Rd, 85251) is a vacation-ownership residence club on The Phoenician's campus"),
    ("IHG", "phxcv"): ("TIMESHARE -- Holiday Inn Club Vacations Scottsdale Resort (7677 E Princess Blvd, 85255) is "
                       "IHG's vacation-ownership club resort"),
    ("CHOICE", "az385"): ("TIMESHARE -- Bluegreen Vacations Cibola Vista Resort and Spa (27501 N Lake Pleasant Pkwy, "
                          "85383) is a Bluegreen vacation-ownership resort listed through Choice's Ascend Collection"),
    ("CHOICE", "az654"): ("TIMESHARE -- Westgate Painted Mountain Golf Resort (6302 E McKellips Rd, 85215) is a "
                          "Westgate Resorts vacation-ownership resort listed through Choice's Ascend Collection"),
    # Hilton's own city-page cards name these three HILTON VACATION CLUB properties; a vacation club's name on the
    # brand's own card is first-party evidence of vacation ownership, so they were not opened in the attended
    # browser (the Akamai window is spent on public hotels).
    ("HILTON", "phxregv"): ("TIMESHARE -- Hilton Vacation Club Scottsdale Links Resort (85255) is a Hilton Grand "
                            "Vacations vacation-ownership resort, so named on Hilton's own city-page card"),
    ("HILTON", "phxmrgv"): ("TIMESHARE -- Hilton Vacation Club Scottsdale Villa Mirage (85255) is a Hilton Grand "
                            "Vacations vacation-ownership resort, so named on Hilton's own city-page card"),
    ("HILTON", "phxragv"): ("TIMESHARE -- Hilton Vacation Club Rancho Manana (Cave Creek 85331) is a Hilton Grand "
                            "Vacations vacation-ownership resort, so named on Hilton's own city-page card"),
}


def timeshare_by_code(brand, code):
    """The TIMESHARE reason for a brand property code this order read as a vacation-ownership property, or None."""
    return TIMESHARE_CODES.get(((brand or "").upper(), (code or "").lower()))


#: VACATION OWNERSHIP. Names that are, on their face, a timeshare / vacation-ownership club resort. Generic chain
#: vocabulary (statewide, not Orlando-specific) is kept from the Orlando V2 / Miami / Fort Lauderdale
#: precedent; Palm-Beach-specific resort names are added only as this order's own evidence surfaces them.
_TIMESHARE = re.compile(
    r"\b(hilton grand vacations|grand vacations club|hgv club|marriott vacation club|worldmark|club wyndham|"
    r"wyndham vacation|bluegreen|diamond resorts|holiday inn club vacations|vistana|westgate (lakes|vacation "
    r"villas|town center|palace|leisure)|disney vacation club|vacation villas|vac villas|hyatt vacation club|"
    r"hyatt residence club|sheraton vistana|festiva|welk resorts?|lawrence welk|hilton vacation club|club intrawest|"
    r"shell vacations|raintree|"
    r"timeshare|vacation ownership|vacation club|residence club)\b", re.I)
#: WHOLE-HOME AND UNIT RENTALS.
_VACATION_RENTAL = re.compile(
    r"\b(vacation homes?|vacation rentals?|rental homes?|resort homes|townhomes?|townhouses?|condos?|condominiums?|"
    r"homes and courts|str #\s*\d*|villa rentals?|luxury villas|pool homes?|private homes?|holiday homes?)\b", re.I)
#: RESORT RESIDENCES -- privately owned residences inside a resort campus, rented by their owners or a manager.
_RESORT_RESIDENCE = re.compile(r"\b(private residences|resort residences|the residences at|residence club)\b", re.I)
#: SHORT-TERM-RENTAL / SERVICED-APARTMENT OPERATORS -- app-managed unit portfolios inside residential towers, not a
#: public hotel operation (Old Town Scottsdale, downtown Phoenix and Tempe carry many).
#: A brand-inventory or hotel-page read still overrides this.
_STR_OPERATOR = re.compile(r"\b(sonder|kasa|vacasa|evolve|domio|lyric|airbnb|vrbo|frontdesk|blueground|"
                           r"stay alfred|mint house|cozysuites|luxury rentals?|furnished|avantstay|placemakr|"
                           r"corporate housing|onthesand|beach cottage rentals?)\b", re.I)
#: MEASURED IN THIS ORDER: the committed nonhotel-rulings modules this file was cloned from (Jacksonville, Miami,
#: Fort Lauderdale, West Palm Beach) carry literal BACKSPACE bytes (0x08) where this pattern's two ``\b`` word
#: boundaries belong -- a heredoc that wrote ``\b`` into a non-raw string -- so in those markets this rule could
#: never match anything. It was repaired in San Diego's own copy and is kept repaired here, and recorded as a finding; the other
#: markets' modules are not touched by this order (a cross-market change).
#: An ORDINARY APARTMENT COMMUNITY. The Fort Lauderdale build found that South Florida's vintage beachfront
#: motels are licensed MOTL and named "... Apartment Motel" / "... Apartment Hotel"; the Philips Highway and
#: University Boulevard motor-court row in 32216 -- 18 hotel-rank licences, this market's oldest -- and the
#: Commonwealth Avenue row on the Westside carry the same vocabulary.
#: Those are public lodging on the state's own record, so the apartment rule never fires on a name that also
#: states hotel / motel / inn / resort / hostel. Carried forward as a rule, not as a ruling.
_APARTMENT_NAME = re.compile(r"\b(apartments?|apts?|apt homes|lofts llc)\b", re.I)

#: Lanes whose presence means a brand's own public hotel inventory or a hotel page reached the row.
_PUBLIC_HOTEL_LANES = ("PROPERTY_PAGE", "BRAND_INVENTORY")


#: A register row or listing whose own name is a COMPANY (LLC / Inc / management / realty) and not a hotel, or whose
#: own street is a unit inside a residential tower ("1236 1st St S Unit 305", "Ste 210"), is a condo-unit rental
#: programme operating inside someone else's building -- not a public hotel establishment.
_COMPANY_NAME = re.compile(r"\b(llc|inc|corp|management|mgmt|real estate|realty|properties|holdings|investments?|"
                           r"enterprises|rentals?)\b", re.I)
_HOTEL_WORD = re.compile(r"\b(hotel|motel|inn|resort|lodge|suites|hostel)\b", re.I)
_HOTEL_WORD_STRICT = re.compile(r"\b(hotel|motel|inn|resort|hostel)\b", re.I)
_UNIT_STREET = re.compile(r"\b(unit|apt|ste|suite)\s*#?\s*[a-z]{0,3}-?\s*\d+", re.I)


def nonhotel_by_name(name, lanes, street=""):
    """The exclusion reason for a row whose own name reads as non-hotel lodging, or None."""
    n = re.sub(r"[’']", "", name or "")
    if any(str(l or "").startswith(_PUBLIC_HOTEL_LANES) for l in (lanes or ())):
        return None
    if _UNIT_STREET.search(street or "") and not _HOTEL_WORD_STRICT.search(n):
        return ("VACATION_RENTAL -- the row's own address is a unit inside a building (%r) and its name (%r) is not a "
                "hotel's; a unit-rental programme inside a residential tower is never a hotel identity" % (street, name))
    if _COMPANY_NAME.search(n) and not _HOTEL_WORD.search(n):
        if re.search(r"\b(rentals?|management|mgmt|realty|real estate)\b", n, re.I):
            return ("VACATION_RENTAL -- the licence names a rental / management / realty company (%r), not a public "
                    "hotel establishment; a company licensed to rent units is a unit-rental programme" % name)
        return ("IDENTITY_REVIEW -- the licence names only an owning company (%r), not the establishment it operates; "
                "an LLC name proposes no hotel identity until a first-party page names the premises" % name)
    if _TIMESHARE.search(n):
        return ("TIMESHARE -- the row's own name (%r) is a vacation-ownership / timeshare club resort, and no brand's "
                "public hotel inventory and no hotel page read reached it; individual timeshare units and "
                "vacation-ownership inventory are never admitted without proof of exact public hotel operation" % name)
    if _RESORT_RESIDENCE.search(n):
        return ("RESORT_RESIDENCE -- the row's own name (%r) is a private resort-residence club, not a public hotel" % name)
    if _STR_OPERATOR.search(n):
        return ("VACATION_RENTAL -- the row's own name (%r) is a short-term-rental / serviced-apartment operator's "
                "unit portfolio, not a public hotel operation" % name)
    if _VACATION_RENTAL.search(n):
        return ("VACATION_RENTAL -- the row's own name (%r) is a vacation-home, villa, townhome or condo rental "
                "community; whole-home and unit rentals are never hotel identities" % name)
    if _APARTMENT_NAME.search(n) and not _HOTEL_WORD_STRICT.search(n):
        return _APARTMENTS + " (%r)" % name
    return None


def exclusion_class(reason):
    """VACATION_RENTAL / TIMESHARE / RESORT_RESIDENCE / NON_HOTEL from a NON_LODGING reason string."""
    head = (reason or "").split(" --", 1)[0].strip()
    return head if head in ("VACATION_RENTAL", "TIMESHARE", "RESORT_RESIDENCE", "NON_HOTEL") else "NON_HOTEL"

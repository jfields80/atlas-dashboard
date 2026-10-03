"""PTF-SEATTLE-WA-HARDENED-SOURCE-READY-001 -- the vacation-rental / timeshare / resort-residence / venue filter.

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
_PLACES = "seattle_wa_places_route_discovery_001"
_UNCONFIRMED_PERMIT = ("the only evidence is a City of Seattle business licence at %s, and Google Places (%s) binds no "
                       "lodging business at that house number and ZIP; Seattle's short-term-rental hosts hold the same "
                       "licences, so the row is neither a confirmed public hotel nor a confirmed rental -- held for "
                       "review")
LODGING_UNCONFIRMED = {
    # Nothing is inherited from San Antonio. Each row below is a City of Seattle licence whose ONLY lodging evidence is
    # the licence itself; Places route discovery (seattle_wa_places_route_discovery_001) found no business at its house
    # number + ZIP. Held for review -- never admitted, never refused as a rental on a name.
    'admiral guesthouse': _UNCONFIRMED_PERMIT % ('5059 SW Waite St', _PLACES),
    'alki beach bed and breakfast': _UNCONFIRMED_PERMIT % ('2437 55th Ave SW # A', _PLACES),
    'alki guesthouse': _UNCONFIRMED_PERMIT % ('3044 64th Ave SW', _PLACES),
    'ballard guest suite': _UNCONFIRMED_PERMIT % ('701 NW 60th St', _PLACES),
    'boti b and b': _UNCONFIRMED_PERMIT % ('2717 E Spring St', _PLACES),
    'btc 612': _UNCONFIRMED_PERMIT % ('3504 NE 143rd St', _PLACES),
    'cedar grove lodge': _UNCONFIRMED_PERMIT % ('4714 47th Ave SW', _PLACES),
    'chamonix lodge': _UNCONFIRMED_PERMIT % ('11536 Meridian Ave N # A', _PLACES),
    'chaos capital lodgings': _UNCONFIRMED_PERMIT % ('1433 E Howell St', _PLACES),
    'charming seattle guesthouse': _UNCONFIRMED_PERMIT % ('4554 33rd Ave S', _PLACES),
    'comfortstayd': _UNCONFIRMED_PERMIT % ('1503 N 122nd St', _PLACES),
    'diane xiao': _UNCONFIRMED_PERMIT % ('806a 23rd Ave S', _PLACES),
    'greenlake view home': _UNCONFIRMED_PERMIT % ('336 N 73rd St', _PLACES),
    'guest house 9105': _UNCONFIRMED_PERMIT % ('9105 Matthews Ave NE', _PLACES),
    'hitts hill guest house': _UNCONFIRMED_PERMIT % ('3844 S Lucile St', _PLACES),
    'jennie s grand b and b': _UNCONFIRMED_PERMIT % ('1122 Grand Ave', _PLACES),
    'judkins park inn': _UNCONFIRMED_PERMIT % ('2208 S Norman St', _PLACES),
    'kubota inn llc': _UNCONFIRMED_PERMIT % ('5720 S Cooper St', _PLACES),
    'lakewastr': _UNCONFIRMED_PERMIT % ('2124 31st Ave S', _PLACES),
    'luxe guesthouse seattle': _UNCONFIRMED_PERMIT % ('5070 B Harold Pl NE', _PLACES),
    'minerva inn llc': _UNCONFIRMED_PERMIT % ('517 11th Ave E', _PLACES),
    'ne seattle stays': _UNCONFIRMED_PERMIT % ('6833 36th Ave NE # B', _PLACES),
    'nestled inn llc': _UNCONFIRMED_PERMIT % ('1802 30th Ave S', _PLACES),
    'nw lodge seattle llc': _UNCONFIRMED_PERMIT % ('2728 NE 130th St', _PLACES),
    'pangolin guest house': _UNCONFIRMED_PERMIT % ('2352 Franklin Ave E', _PLACES),
    'pawliday inn': _UNCONFIRMED_PERMIT % ('302 18th Ave E', _PLACES),
    'rainier beach guest house': _UNCONFIRMED_PERMIT % ('10015 65th Ave S', _PLACES),
    'salmon bay bed and breakfast': _UNCONFIRMED_PERMIT % ('7003 17th Ave NW', _PLACES),
    'teddy cp': _UNCONFIRMED_PERMIT % ('917 NW 103rd St', _PLACES),
    'wallingford suites': _UNCONFIRMED_PERMIT % ('4214 1st Ave NW', _PLACES),
    'winters alki beach hideaway': _UNCONFIRMED_PERMIT % ('2527 56th Ave SW', _PLACES),
    'seattle pacific hotel': _UNCONFIRMED_PERMIT % ('1228 Bigelow Ave N', _PLACES),
    'the evanstones motor lodge': _UNCONFIRMED_PERMIT % ('3804 Evanston Ave N', _PLACES),
    # The only website Places names for these is not a hotel operator's; the premises is neither a confirmed hotel
    # nor a confirmed non-hotel.
    'skyway inn hotel': ("the only website Places (%s) names for 20045 International Blvd is an airport-PARKING "
                         "operator's (skywayparkingseatac.com, title 'Home - Skyway Parking'); no hotel operation is "
                         "confirmed at the premises -- held for review" % _PLACES),
    'the corona': ("the only website Places (%s) names for 606 2nd Avenue is corona.seattlehistoriclofts.com (a "
                   "historic-lofts residential site), which refused the plain client (403); no hotel operation is "
                   "confirmed -- held for review" % _PLACES),
}

#: Rows refused by their OWN full normalised name, each with its reason. Added only after that row's own
#: first-party evidence was read. SEATTLE's exposure is its furnished condo / apartment and serviced-apartment stock
#: (Sonder, Kasa, Mint House, Placemakr, Blueground, Barsala), its corporate-housing portfolios, patient housing
#: around the medical campuses, the WorldMark Camlin vacation-ownership building and the register's short-term-rental
#: hosts. Nothing is inherited from San Antonio.
_RESIDENCE = ("VACATION_RENTAL -- the City of Seattle business licence is named for %s, and Google Places (%s) "
              "resolves that address to a bare residential premises with no lodging business: a private home or unit "
              "licensed for short-term rental, not a public hotel")
NOT_LODGING_WHY = {
    # Licence rows Places BOUND (house number + ZIP) to a bare residential premises with no lodging business.
    '18665 151st ave ne': _RESIDENCE % ('its own address, 18665 151st Ave NE (a map row whose name IS its street address)', _PLACES),
    'ashworth golestan': _RESIDENCE % ("a private individual ('Ashworth Golestan') at 3053 30th Ave W (Places: a sub-premise / unit)", _PLACES),
    'c and c b and b': _RESIDENCE % ("'C and C B and B' at 4710 Burke Ave N", _PLACES),
    'daisy maes b and b': _RESIDENCE % ("'Daisy Maes B & B' at 6731 1st Ave NW", _PLACES),
    'ed b and b': _RESIDENCE % ("'Ed B and B' at 130 NE 57th St", _PLACES),
    'floresca jose l': _RESIDENCE % ("a private individual ('Floresca Jose L') at 1433 20th Ave", _PLACES),
    'heath horton': _RESIDENCE % ("a private individual ('Heath Horton') at 2000 Alaskan Way # 548 (Places: Apt 548, a unit)", _PLACES),
    'jiaming xie': _RESIDENCE % ("a private individual ('Jiaming Xie') at 13705 Corliss Ave N", _PLACES),
    'libertty sabrina': _RESIDENCE % ("a private individual ('Libertty Sabrina') at 3601 SW Raymond St", _PLACES),
    'maple leaf lodge': _RESIDENCE % ("'Maple Leaf Lodge' at 8921 5th Ave NE", _PLACES),
    'miller air b n b': _RESIDENCE % ("'Miller Air B N B' -- an Airbnb by its own name -- at 133 Queen Anne Ave N # 506 (Places: Unit 506)", _PLACES),
    'moonlight guest house': _RESIDENCE % ("'Moonlight Guest House' at 5228 42nd Ave SW", _PLACES),
    'nostalgique': _RESIDENCE % ("'Nostalgique' at 12034 25th Ave NE", _PLACES),
    'peacock garden b and b': _RESIDENCE % ("'Peacock Garden B and B' at 2435 W Boston St", _PLACES),
    'reddysetgomez guest house': _RESIDENCE % ("'Reddysetgomez Guest House' at 3006 38th Ave SW", _PLACES),
    'sarah s suites 1': _RESIDENCE % ("'Sarah's Suites 1' at 7712 46th Ave S", _PLACES),
    'suzanne wen': _RESIDENCE % ("a private individual ('Suzanne Wen') at 3930 Midvale Ave N", _PLACES),
    'talaramba b and b': _RESIDENCE % ("'Talaramba B and B' at 4838 S Morgan St", _PLACES),
    'vynne hernandez suites': _RESIDENCE % ("'Vynne-Hernandez Suites' at 2612 NE 82nd St", _PLACES),
    'wander lodge': _RESIDENCE % ("'Wander Lodge' at 4144 48th Ave SW", _PLACES),
    'west seattle guesthouse': _RESIDENCE % ("'West Seattle Guesthouse' at 3550 SW 100th St", _PLACES),
    'woodsy haven': _RESIDENCE % ("'Woodsy Haven' at 9313 NW 26th Pl NW", _PLACES),
    # Licence rows Places bound to an apartment building or condominium complex.
    'k and m b and b': ("VACATION_RENTAL -- the City of Seattle licence is at a unit address (2219 2nd Ave # 100), and Google "
                    "Places (%s) names the premises Concept One Apartments (an apartment building); a unit in a multi-unit residential "
                    "building is not a public hotel" % _PLACES),
    'kevan homes': ("VACATION_RENTAL -- the City of Seattle licence is at a unit address (1311 12th Ave S # B402), and Google "
                    "Places (%s) names the premises Harwood Condominiums (a condominium complex); a unit in a multi-unit residential "
                    "building is not a public hotel" % _PLACES),
    # Offices, housing nonprofits, a visitor centre, corporate housing, hostels, a member club and patient housing.
    'back of house concepts': ("NON_HOTEL -- the City of Seattle licence names a company ('Back of House Concepts') at 14632 SE 22nd St, Bellevue, and Places (%s) finds no lodging business there; a hospitality-services company is not a public hotel" % _PLACES),
    'seattle visitor information centers': ("NON_HOTEL -- Visit Seattle's own visitor information centre (705 Pike Street, the convention center), listed by the bureau; a visitor centre is not lodging"),
    'tlc suites dba temporary living corporation': ("VACATION_RENTAL -- the licence names 'TLC Suites dba Temporary Living Corporation' at a unit address (600 1st Ave #239): a corporate-housing operator's unit portfolio, not a public hotel"),
    'hedreen hotel llc': ("NON_HOTEL -- the licence names an owning company ('Hedreen Hotel LLC') at an office suite (1700 7th Ave # 2300); a hotel-owning entity's office is not a hotel premises"),
    'ivi hotel management of washington inc': ("NON_HOTEL -- the licence names a hotel-MANAGEMENT company at an office suite (20415 72nd Ave S # 120, Kent); a management company's office is not a hotel premises"),
    'plymouth housing group': ('NON_HOTEL -- Plymouth Housing (2113 3rd Ave) is a permanent supportive-housing nonprofit; residential housing is not public lodging'),
    'low income housing institute': ('NON_HOTEL -- the Low Income Housing Institute (1253 S Jackson St # A) is an affordable-housing nonprofit; residential housing is not public lodging'),
    'seattle city suites llc': ("VACATION_RENTAL -- the licence names 'Seattle City Suites LLC' at a unit inside a residential tower (2415 2nd Ave # 527); a unit-rental programme is not a public hotel"),
    'hostel fish seattle': ("NON_HOTEL -- a hostel (2327 2nd Ave); hostels are NON_LODGING under the geography's rule"),
    'american hotel hostel': ("NON_HOTEL -- a hostel by its own name and site (520 S King St); hostels are NON_LODGING under the geography's rule"),
    'green tortoise hostel by the market': ("NON_HOTEL -- a hostel by its own name (105 B Pike St); hostels are NON_LODGING under the geography's rule"),
    'columbia city hostel': ("NON_HOTEL -- a hostel by its own name at a unit address (4419 S Brandon St # D); hostels are NON_LODGING under the geography's rule"),
    'washington athletic club': ('NON_HOTEL -- the Washington Athletic Club (1325 Sixth Ave) is a private member club whose guest rooms are sold to members and their guests; member-only club lodging is never admitted'),
    'the collegiana': ("NON_HOTEL -- The Collegiana (4311 12th Ave NE) is listed by UW Medicine under its own patient 'lodging options' (the census route is uwmedicine.org/patient-resources/lodging-options/the-collegiana); patient housing is not public lodging"),
    # The website Places names for the licence, fetched by this order (its persisted document), is an APARTMENT or
    # SENIOR-LIVING operator's -- residential leasing, not a public hotel.
    'boyer avenue co': ("NON_HOTEL -- the website Places names for 2410 Boyer Ave E # 1 is 'Four Seasons Apartments - "
                        "Redside Partners' (redsidepartners.com/property/four-seasons-apartments, fetched by this "
                        "order); an apartment building is not a public hotel"),
    'cory shelest': ("NON_HOTEL -- the licence names a private individual at 3120 Harvard Ave E; the website Places "
                     "names there is 'Odessa on Lake Union' ('Thoughtfully designed studio apartments ... Flexible leases "
                     "3 / 6 / 9 / 12 month', fetched by this order); an apartment building is not a public hotel"),
    'curben hotel': ("NON_HOTEL -- 'The Curben Hotel' (1726 Summit Ave) is listed by its property manager The Neiders "
                     "Company as an APARTMENT community (neiders.com/property/the-curben-hotel-washington-seattle-"
                     "apartment, 'we are a pet-friendly community', fetched by this order); a historic name does not "
                     "make an apartment building a public hotel"),
    'parkshore': ("NON_HOTEL -- Parkshore (1630 43rd Ave E) is a retirement community ('Parkshore in Seattle, WA | Senior "
                  "Living', transformingage.org, fetched by this order); senior living is not public lodging"),
    'quocation': ("NON_HOTEL -- the website Places names for 510 Broadway is 'Adapt Broadway | Micro & Lofted Studios' "
                  "(schema.org ApartmentComplex, a leasing office and application fee, fetched by this order); an "
                  "apartment complex is not a public hotel"),
}

#: NON-HOTEL PROPERTIES KEYED BY THE BRAND'S OWN PROPERTY CODE. A brand inventory lists these beside its hotels,
#: and the public-hotel-lane override in ``nonhotel_by_name`` would otherwise admit them on that listing alone (the
#: PHOENIX CORRECTION-003 lesson: four Wyndham vacation clubs were admitted and published on a brand listing).
#: Each code is added only from the brand's OWN route or page: the brand itself names a vacation club, a villa
#: resort, a residence club or an apartment product, not a public hotel. Never admitted. Empty at authoring time.
TIMESHARE_CODES = {
}


def timeshare_by_code(brand, code):
    """The TIMESHARE / VACATION_RENTAL reason for a brand property code this order read as a non-hotel product."""
    return TIMESHARE_CODES.get(((brand or "").upper(), (code or "").lower()))


#: VACATION OWNERSHIP AND APARTMENT PRODUCTS NAMED BY THE BRAND'S OWN ROUTE. The route is the brand's own URL, so a
#: vacation-club or apartment segment in it is the brand's own statement of what the property is -- first-party
#: evidence that outranks the brand inventory's listing of it beside hotels. Wyndham files its clubs under the
#: 'wyndham-vacation-resorts' / 'club-wyndham' / 'worldmark' segments (measured in Phoenix correction 003); Marriott,
#: Hilton, IHG and Hyatt name theirs in the slug.
_TIMESHARE_ROUTE = re.compile(
    r"(wyndhamhotels\.com/(?:wyndham-vacation[a-z-]*|club-wyndham|worldmark)/|"
    r"marriott-vacation-club|vacation-villas|-villas-|residence-club|hilton-grand-vacations|hilton-vacation-club|"
    r"holiday-inn-club-vacations|holidayinnclubvacations|hyatt-vacation-club|hyatt-residence-club|bluegreen|"
    r"diamond-resorts|club-wyndham|worldmark|clubwyndham)", re.I)
_APARTMENT_ROUTE = re.compile(r"(sonder-|/sonder|-apartments-|apartments-by-marriott|placemakr|mint-house|"
                              r"kasa-|blueground|lyric-)", re.I)


def timeshare_by_route(route):
    """The TIMESHARE / VACATION_RENTAL reason a brand's OWN route states, or None."""
    r = route or ""
    if _TIMESHARE_ROUTE.search(r):
        return ("TIMESHARE -- the brand's own route (%s) files this property as a vacation-ownership club, villa "
                "resort or residence club; vacation-ownership inventory never enters hotel accounting on a brand "
                "listing" % r)
    if _APARTMENT_ROUTE.search(r):
        return ("VACATION_RENTAL -- the brand's own route (%s) names a serviced-apartment product; an apartment "
                "operator's unit portfolio is not a public hotel operation" % r)
    return None


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
#: public hotel operation (downtown, Belltown, South Lake Union, Capitol Hill and Bellevue carry many).
#: A brand-inventory or hotel-page read still overrides this.
_STR_OPERATOR = re.compile(r"\b(sonder|kasa|vacasa|evolve|domio|lyric|airbnb|vrbo|frontdesk|blueground|barsala|"
                           r"stay alfred|mint house|cozysuites|luxury rentals?|furnished|avantstay|placemakr|"
                           r"corporate housing|onthesand|beach cottage rentals?|wanderjaunt|zeus living|"
                           r"furnished finder|stayduo)\b", re.I)
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
    """VACATION_RENTAL / TIMESHARE / RESORT_RESIDENCE / MILITARY_RESTRICTED / NON_HOTEL from a reason string."""
    head = (reason or "").split(" --", 1)[0].strip()
    return head if head in ("VACATION_RENTAL", "TIMESHARE", "RESORT_RESIDENCE", "MILITARY_RESTRICTED",
                            "NON_HOTEL") else "NON_HOTEL"

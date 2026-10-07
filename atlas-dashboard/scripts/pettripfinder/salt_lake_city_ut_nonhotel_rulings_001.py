"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- the vacation-rental / timeshare / resort-residence / venue filter
(Phases 4, 5, 7 and 8: Park City's condominium lodges, private chalets, property-management portfolios and
vacation-ownership resorts).

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

#: Rows whose LODGING category cannot be settled from the evidence. Held as IDENTITY_REVIEW_REQUIRED. Added only
#: after reading that row's own evidence in this order. Empty at authoring time.
LODGING_UNCONFIRMED = {
    # The club's own page (altaclub.org, attended browser 2026-10-07) speaks of membership and private events and
    # states nothing about public nightly rooms; whether "The Inn at the Alta Club" sells rooms to the public is
    # unproven, so the row is held, never refused and never published.
    "the inn at the alta club": "a private club's own page states membership and private events, and no public "
                                "nightly rooms (altaclub.org)",
}

#: Rows refused by their OWN full normalised name, each with its reason. Added only after that row's own first-party
#: evidence was read IN THIS ORDER. SALT LAKE CITY / PARK CITY's exposure is Park City's condominium lodges and
#: private chalets sold nightly by property managers, its branded residences beside resort hotels, downtown Salt Lake
#: City's serviced apartments and corporate housing, and University of Utah housing. Nothing is inherited from any
#: other market. Empty at authoring time.
NOT_LODGING_WHY = {
    # Each entry below was read on its OWN first-party page in the attended browser on 2026-10-07
    # (markets/staging/salt-lake-city-ut/raw_captures/browser_reads_001.jsonl).
    "stag lodge": "VACATION_RENTAL -- Deer Valley Resort's own lodging page lists '3- to 7-Bedroom Residences' only: "
                  "resort-managed residences rented by the unit, no hotel rooms",
    "the grand lodge": "VACATION_RENTAL -- Deer Valley Resort's own page is titled 'Vacation Rentals' and lists '1- to "
                       "6-Bedroom Residences' only",
    "trail s end lodge": "VACATION_RENTAL -- Deer Valley Resort's own lodging page lists '1- to 4-Bedroom Residences' "
                         "only: resort-managed residences rented by the unit",
    "the lowell": "VACATION_RENTAL -- the only first-party page is a rental manager's complex page titled 'The Lowell "
                  "Condominiums' (parkcitylodging.com/rentals/complexes/the-lowell): condominiums rented by the unit",
    "park city vacations": "VACATION_RENTAL -- the business's own page offers 'Over 200 Park City private homes, condos "
                           "and hotel options': a rental agency, not one premises",
    "empire pass at deer valley": "NON_HOTEL -- an AREA, not a premises: Deer Valley Resort's own lodging directory files "
                                  "properties under an 'Empire Pass Area' heading and lists none named Empire Pass",
    "ap1 lofts": _APARTMENTS + " (its own page: 'AP1 Lofts Apartments')",
    "crystal ranch lodge and hotel": "NON_HOTEL -- the business's own site is a guided fly-fishing and snowmobiling "
                                     "outfitter whose only Salt Lake address is an office suite (428 W 4800 S, STE 2C)",
    "the other side inn": _VENUE + " (its own site: an event venue with event and conference rooms, no lodging)",
    # The same three rows under the names their own pages give them (the census adopts a first-party page title as the
    # row's name once the page binds, and the ruling is keyed on the row's name as the census holds it).
    "grand lodge": "VACATION_RENTAL -- Deer Valley Resort's own page is titled 'Vacation Rentals' and lists '1- to "
                   "6-Bedroom Residences' only",
    "the lodge at crystal ranch": "NON_HOTEL -- the business's own site is a guided fly-fishing and snowmobiling "
                                  "outfitter whose only Salt Lake address is an office suite (428 W 4800 S, STE 2C)",
    "the other side": _VENUE + " (its own site: an event venue with event and conference rooms, no lodging)",
}

#: KANSAS CITY: a register or bureau row whose OWN name is a retreat / renewal / pastoral centre, a winery, an orchard or
#: a camp is a venue or an institution that licenses beds, not a public hotel selling nightly rooms -- unless its own
#: name also states hotel / motel / inn / resort / hostel (Unity Village's "Unity Hotel and Conference Center" is a
#: hotel, judged on its own page).
_VENUE_NAME = re.compile(r"\b(pastoral center|renewal center|retreat center|retreat house|winery|vineyards?|orchard|"
                         r"camp|church|monastery|abbey|seminary)\b", re.I)

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
#: vocabulary is kept from the earlier markets' precedent. SALT LAKE CITY / PARK CITY additions: Westgate (Westgate
#: Park City Resort & Spa is a Westgate vacation-ownership resort) and Marriott Vacation Club's own naming convention
#: -- its resorts are titled "Marriott's <resort>" (Marriott's MountainSide, Marriott's Summit Watch), which the
#: brand never uses for a hotel.
_TIMESHARE = re.compile(
    r"\b(hilton grand vacations|grand vacations club|hgv club|marriott vacation club|worldmark|club wyndham|"
    r"wyndham vacation|bluegreen|diamond resorts|holiday inn club vacations?|vistana|westgate (lakes|vacation "
    r"villas|town center|palace|leisure)|disney vacation club|vacation villas|vac villas|hyatt vacation club|"
    r"hyatt residence club|sheraton vistana|festiva|welk resorts?|lawrence welk|hilton vacation club|club intrawest|"
    r"shell vacations|raintree|westgate|marriotts|sunrise lodge|"
    r"timeshare|vacation ownership|vacation club|residence club)\b", re.I)
#: WHOLE-HOME AND UNIT RENTALS.
_VACATION_RENTAL = re.compile(
    r"\b(vacation homes?|vacation rentals?|rental homes?|resort homes|townhomes?|townhouses?|condos?|condominiums?|"
    r"homes and courts|str #\s*\d*|villa rentals?|luxury villas|pool homes?|private homes?|holiday homes?|"
    r"chalets?|ski homes?|cabins?|nightly rentals?|lodging rentals?)\b", re.I)
#: RESORT RESIDENCES -- privately owned residences inside a resort campus, rented by their owners or a manager.
_RESORT_RESIDENCE = re.compile(r"\b(private residences|resort residences|the residences at|residence club)\b", re.I)
#: SHORT-TERM-RENTAL / SERVICED-APARTMENT OPERATORS -- app-managed unit portfolios inside residential towers, not a
#: public hotel operation (downtown Salt Lake City carries several), and Park City's property-management companies,
#: which sell owners' condominium units and homes nightly under a lodging brand of their own.
#: A brand-inventory or hotel-page read still overrides this.
_STR_OPERATOR = re.compile(r"\b(sonder|kasa|vacasa|evolve|domio|lyric|airbnb|vrbo|frontdesk|blueground|barsala|"
                           r"stay alfred|mint house|cozysuites|luxury rentals?|furnished|avantstay|placemakr|"
                           r"corporate housing|onthesand|beach cottage rentals?|wanderjaunt|zeus living|"
                           r"furnished finder|stayduo|roami|minnestay|landing furnished|zencity|aka|park city lodging|"
                           r"all seasons resort lodging|deer valley resort lodging|resortquest|natural retreats|"
                           r"inspirato|exclusive resorts|abode|wyndham vacation rentals|redawning|"
                           r"luxury destinations|property management|condo rentals?)\b", re.I)
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

#: The "by <operator>" suffix a short-term-rental operator puts on its buildings' names.
_BY_STR_OPERATOR = re.compile(r"\bby\s+(kasa|sonder|placemakr|mint\s+house|lyric|blueground|domio|vacasa|"
                              r"avantstay|frontdesk|landing|redawning|cloud dream homes|park city experience)\b"
                              # SALT LAKE CITY: a row whose own name STARTS with a serviced-apartment operator's
                              # brand ("Placemakr Salt Lake City Downtown", "Landing Furnished Apartments") is that
                              # operator's unit portfolio even when a brand lane lists it.
                              r"|^\s*(placemakr|sonder|kasa|mint house|blueground|landing furnished|zeus)\b", re.I)

#: Lanes whose presence means a brand's own public hotel inventory or a hotel page reached the row.
_PUBLIC_HOTEL_LANES = ("PROPERTY_PAGE", "BRAND_INVENTORY")


#: A register row or listing whose own name is a COMPANY (LLC / Inc / management / realty) and not a hotel, or whose
#: own street is a unit inside a residential tower ("1236 1st St S Unit 305", "Ste 210"), is a condo-unit rental
#: programme operating inside someone else's building -- not a public hotel establishment.
_COMPANY_NAME = re.compile(r"\b(llc|inc|corp|management|mgmt|real estate|realty|properties|holdings|investments?|"
                           r"enterprises|rentals?|corporation|company)\b", re.I)
_HOTEL_WORD = re.compile(r"\b(hotel|motel|inn|resort|lodge|suites|hostel)\b", re.I)
_HOTEL_WORD_STRICT = re.compile(r"\b(hotel|motel|inn|resort|hostel)\b", re.I)
_CAMP_OR_HOSTEL = re.compile(r"\b(rv park|rv resort|r\.v\. park|mobile home|mobile terrace|mobile estates|"
                             r"manufactured home|campground|campgrounds|kampground|koa|hostel|"
                             # SALT LAKE CITY: membership-campground and RV-resort operators ("Four Seasons Outdoor
                             # Resorts", "Sun Outdoors Salt Lake City")
                             r"outdoor resorts?|sun outdoors|rv resorts?)\b", re.I)
_UNIT_STREET = re.compile(r"\b(unit|apt|ste|suite)\s*#?\s*[a-z]{0,3}-?\s*\d+", re.I)


def nonhotel_by_name(name, lanes, street=""):
    """The exclusion reason for a row whose own name reads as non-hotel lodging, or None."""
    n = re.sub(r"[’']", "", name or "")
    # PORTLAND (kept): an RV park, mobile-home park, campground or hostel is NON_LODGING under the geography's rule even
    # when its OWN page was read (the page of a campground is still a campground's) -- so this test runs before the
    # public-hotel-lane override. 'RV resort' names a campground, so its 'resort' is not a hotel word.
    if _CAMP_OR_HOSTEL.search(n) and not _HOTEL_WORD_STRICT.search(
            re.sub(r"\b(hostel|rv resort)\b", "", n, flags=re.I)):
        return ("NON_HOTEL -- the row's own name (%r) is an RV park, mobile-home park, campground or hostel; those are "
                "NON_LODGING under the geography's rule, never a hotel identity" % name)
    # The Phoenix correction-003 lesson as a NAME rule: a row whose OWN name is a vacation-ownership club or
    # timeshare resort ("Marriott's MountainSide", "Westgate Park City Resort & Spa", "Sunrise Lodge, a Hilton Grand
    # Vacations Club") is TIMESHARE whatever lane listed it: a brand listing is not proof of a public hotel operation,
    # and a pet-policy page does not change that.
    if _TIMESHARE.search(n):
        return ("TIMESHARE -- the row's own name (%r) is a vacation-ownership / timeshare club resort; vacation-ownership "
                "inventory never enters hotel accounting, even when a brand lists it beside its hotels" % name)
    # A row whose OWN name carries a short-term-rental operator's "by <operator>" suffix is that operator's unit
    # portfolio whatever lane listed it: the operator's own listing is the only "property page" such a row has, so
    # the public-hotel-lane override below must not admit it on that listing.
    if _BY_STR_OPERATOR.search(n):
        return ("VACATION_RENTAL -- the row's own name (%r) is a short-term-rental / serviced-apartment operator's "
                "unit portfolio, not a public hotel operation" % name)
    # SALT LAKE CITY (Phases 4 and 5): a row whose own name is a set of RESIDENCES ("Stein Eriksen Residences") is a
    # building of privately owned residences beside a resort hotel; even when a brand or bureau lists it, whether its
    # nightly units are a distinct public hotel component is not proved by the listing. HELD, never admitted and never
    # refused on a guess.
    if re.search(r"\bresidences\b", n, re.I) and not _HOTEL_WORD_STRICT.search(n):
        return ("IDENTITY_REVIEW -- RESORT_RESIDENCE_UNCONFIRMED: the row's own name (%r) is a residences building; a "
                "distinct public hotel component is not proved by a listing, so it is held, never published" % name)
    if any(str(l or "").startswith(_PUBLIC_HOTEL_LANES) for l in (lanes or ())):
        return None
    if _VENUE_NAME.search(n) and not _HOTEL_WORD_STRICT.search(n):
        return ("NON_HOTEL -- the row's own name (%r) is a retreat / pastoral centre, winery, orchard or camp: a venue or "
                "institution, not a public hotel selling nightly rooms" % name)
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

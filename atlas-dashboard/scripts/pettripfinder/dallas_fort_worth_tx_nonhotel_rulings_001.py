"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- the vacation-rental / timeshare / resort-residence /
apartment / venue filter (Phases 17, 18 and 19: the Metroplex's serviced-apartment and corporate-housing operators,
Uptown / Victory Park / Legacy West residence towers, Arlington stadium-week rentals, extended-stay look-alikes and
vacation-ownership clubs). Cloned from the Fort Myers module.

Two mechanisms, both refusal DECISIONS with their reasons:

1. ``NOT_LODGING_WHY`` / ``LODGING_UNCONFIRMED`` -- matched on the full normalised name
   (``site_data.normalize_name``) of a census candidate, added only after that row's evidence was read.
2. ``nonhotel_by_name`` -- the order's rule applied to a row's OWN name: a vacation-home community, a villa / condo /
   townhome rental, a serviced-apartment operator, a resort-residence club or a vacation-ownership (timeshare) resort
   is refused UNLESS a brand's own public hotel inventory or a hotel page read reached the row. When the operator itself
   lists those exact premises as a bookable hotel with its own property page, the row is judged on that page instead
   -- that is the "prove exact public hotel operation" test, and a name alone never passes or fails it.

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
#: after reading that row's own evidence in this order.
LODGING_UNCONFIRMED = {
    # The site Places names for this row (attended read, tag "ind") is Parks Residential's apartment community, not a
    # hotel page; WaterWalk is ALSO an extended-stay brand, so the category stays open -- held, never admitted, never
    # refused on a third party's page.
    "waterwalk": "the only page reached for this row (Places' website, read attended in this order) is an apartment "
                 "community's leasing site; whether 2220 N Glenville Dr sells public nightly rooms is not shown",
}

#: Rows refused by their OWN full normalised name, each with its reason. Added only after that row's own first-party
#: evidence was read IN THIS ORDER. The Metroplex's exposure is serviced apartments and corporate housing, Uptown /
#: Legacy residence towers, stadium-week rentals and university housing (SMU, TCU, UTA, UTD). Nothing is inherited from
#: any other market. Each entry below was read attended in this order (browser_reads_001.jsonl, tag "ind").
NOT_LODGING_WHY = {
    "hilton worldwide corporate office": _VENUE + " (Hilton's corporate office building in Addison; its own name "
                                         "says office, and no hotel operates under it)",
    "the hampton social dallas": _VENUE + " (its own site is a restaurant and bar at 1520 Main St)",
    "bhartiya nivas": "NON_HOTEL -- a senior-living residence (its own site), not a hotel selling public nightly rooms",
    "trinity terrace": "NON_HOTEL -- a life-plan (continuing-care) retirement community (its own site), not public "
                       "lodging",
    "uptown by onni": _APARTMENTS + " (its own site leases apartments at 2355 Thomas Ave)",
    # tag "fu": the only site any lane names for 3804 Tanacross Dr is Casa de Esperanza's -- single-room-occupancy
    # apartment homes with utilities included, at the licence's own address; the former Crossland is converted.
    "crossland fort worth fossil creek 3547": _APARTMENTS + " (3804 Tanacross Dr is now Casa de Esperanza's "
                                              "single-room-occupancy apartments, on that operator's own site)",
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
#: vocabulary is kept from the earlier markets' precedent, with Westgate and Marriott Vacation Club's own naming
#: convention -- its resorts are titled "Marriott's <resort>" (Marriott's Crystal Shores on Marco Island), which the
#: brand never uses for a hotel.
_TIMESHARE = re.compile(
    r"\b(hilton grand vacations|grand vacations club|hgv club|marriott vacation club|worldmark|club wyndham|"
    r"wyndham vacation|bluegreen|diamond resorts|holiday inn club vacations?|vistana|westgate (lakes|vacation "
    r"villas|town center|palace|leisure)|disney vacation club|vacation villas|vac villas|hyatt vacation club|"
    r"hyatt residence club|sheraton vistana|festiva|welk resorts?|lawrence welk|hilton vacation club|club intrawest|"
    r"(?<!royal )shell vacations|raintree|westgate|marriotts|"
    r"timeshare|vacation ownership|vacation club|residence club)\b", re.I)
#: WHOLE-HOME AND UNIT RENTALS.
_VACATION_RENTAL = re.compile(
    r"\b(vacation homes?|vacation rentals?|rental homes?|resort homes|townhomes?|townhouses?|condos?|condominiums?|"
    r"homes and courts|str #\s*\d*|villa rentals?|luxury villas|pool homes?|private homes?|holiday homes?|"
    r"chalets?|ski homes?|cabins?|nightly rentals?|lodging rentals?)\b", re.I)
#: RESORT RESIDENCES -- privately owned residences inside a resort campus, rented by their owners or a manager.
_RESORT_RESIDENCE = re.compile(r"\b(private residences|resort residences|the residences at|residence club)\b", re.I)
#: SHORT-TERM-RENTAL / SERVICED-APARTMENT OPERATORS -- app-managed unit portfolios inside residential towers, not a
#: public hotel operation, and the beach / island property-management companies, which sell owners' condominium
#: units, cottages and homes nightly under a rental brand of their own.
#: A brand-inventory or hotel-page read still overrides this.
_STR_OPERATOR = re.compile(r"\b(sonder|kasa|vacasa|evolve|domio|lyric|airbnb|vrbo|frontdesk|blueground|barsala|"
                           r"stay alfred|mint house|cozysuites|luxury rentals?|furnished|avantstay|placemakr|"
                           r"corporate housing|onthesand|beach cottage rentals?|wanderjaunt|zeus living|"
                           r"furnished finder|stayduo|roami|minnestay|landing furnished|zencity|aka|royal shell|"
                           r"vip vacation rentals?|island vacation rentals?|resortquest|natural retreats|"
                           r"inspirato|exclusive resorts|abode|wyndham vacation rentals|redawning|"
                           r"luxury destinations|property management|condo rentals?)\b", re.I)
#: MEASURED IN THIS ORDER: the committed nonhotel-rulings modules this file was cloned from (Jacksonville, Miami,
#: Fort Lauderdale, West Palm Beach) carry literal BACKSPACE bytes (0x08) where this pattern's two ``\b`` word
#: boundaries belong -- a heredoc that wrote ``\b`` into a non-raw string -- so in those markets this rule could
#: never match anything. It was repaired in San Diego's own copy and is kept repaired here, and recorded as a finding; the other
#: markets' modules are not touched by this order (a cross-market change).
#: An ORDINARY APARTMENT COMMUNITY. The Fort Lauderdale build found vintage motels licensed as hotels and named
#: "... Apartment Motel" / "... Apartment Hotel" (kept as a finding from that market).
#: Those are public lodging on the state's own record, so the apartment rule never fires on a name that also
#: states hotel / motel / inn / resort / hostel. Carried forward as a rule, not as a ruling.
_APARTMENT_NAME = re.compile(r"\b(apartments?|apts?|apt homes|lofts llc)\b", re.I)

#: The "by <operator>" suffix a short-term-rental operator puts on its buildings' names.
_BY_STR_OPERATOR = re.compile(r"\bby\s+(kasa|sonder|placemakr|mint\s+house|lyric|blueground|domio|vacasa|"
                              r"avantstay|frontdesk|landing|redawning|cloud dream homes|royal shell)\b"
                              # A row whose own name STARTS with a serviced-apartment operator's brand ("Placemakr
                              # ...", "Landing Furnished Apartments") is that operator's unit portfolio even when a
                              # brand lane lists it (kept from the parent).
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
                             # membership-campground and RV-resort operators ("Sun Outdoors ...", kept from the
                             # parent)
                             r"outdoor resorts?|sun outdoors|rv resorts?)\b", re.I)
_UNIT_STREET = re.compile(r"\b(unit|apt|ste|suite)\s*#?\s*[a-z]{0,3}-?\s*\d+", re.I)


#: DALLAS-FORT WORTH: an in-terminal hourly rest-suite business behind airport security (Minute Suites at DFW Terminal
#: D, "Minute Suites Dallas/Fort Worth-D23") is not a public hotel a traveller with a pet can check into; refused by its
#: own name whatever lane lists it.
_AIRSIDE_REST_SUITES = re.compile(r"\b(minute suites|sleep ?pods?|nap suites?|jabbrrbox)\b", re.I)


def nonhotel_by_name(name, lanes, street=""):
    """The exclusion reason for a row whose own name reads as non-hotel lodging, or None."""
    n = re.sub(r"[’']", "", name or "")
    if _AIRSIDE_REST_SUITES.search(n):
        return ("NON_HOTEL -- the row's own name (%r) is an airside hourly rest-suite business inside an airport "
                "terminal behind security, not a public hotel" % name)
    # PORTLAND (kept): an RV park, mobile-home park, campground or hostel is NON_LODGING under the geography's rule even
    # when its OWN page was read (the page of a campground is still a campground's) -- so this test runs before the
    # public-hotel-lane override. 'RV resort' names a campground, so its 'resort' is not a hotel word.
    if _CAMP_OR_HOSTEL.search(n) and not _HOTEL_WORD_STRICT.search(
            re.sub(r"\b(hostel|rv resort)\b", "", n, flags=re.I)):
        return ("NON_HOTEL -- the row's own name (%r) is an RV park, mobile-home park, campground or hostel; those are "
                "NON_LODGING under the geography's rule, never a hotel identity" % name)
    # The Phoenix correction-003 lesson as a NAME rule: a row whose OWN name is a vacation-ownership club or
    # timeshare resort ("Marriott's <resort>", a Westgate resort, "<resort>, a Hilton Grand Vacations Club") is
    # TIMESHARE whatever lane listed it: a brand listing is not proof of a public hotel operation,
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
    # (Phases 7 and 8, kept from the parent): a row whose own name is a set of RESIDENCES is a building of privately
    # owned residences beside a resort hotel; even when a brand or bureau lists it, whether its nightly units are a
    # distinct public hotel component is not proved by the listing. HELD, never admitted and never refused on a guess.
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
        if re.search(r"\b(rentals?|management|mgmt|realty|real estate|vacations?|vacation homes?|vacation "
                     r"properties|castles)\b", n, re.I):
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

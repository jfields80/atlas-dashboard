"""PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001 -- the vacation-rental / timeshare / resort-residence / venue filter.

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
#: first-party evidence was read. SAN DIEGO's exposure is its COASTAL VACATION-OWNERSHIP and BEACH-RENTAL stock:
#: the Carlsbad and Oceanside vacation-ownership resorts (Grand Pacific Palisades, Carlsbad Seapointe, Marriott
#: and Hilton vacation clubs, Club Wyndham, WorldMark), Coronado's and Mission Beach's owner-rented cottages and
#: condominiums, the downtown serviced-apartment towers and the City's own 355 active short-term-rental
#: certificates. EMPTY AT AUTHORING TIME. Nothing is inherited from any Florida market.
NOT_LODGING_WHY = {
    "grand pacific palisades resort": (
        "TIMESHARE -- Grand Pacific Palisades Resort (5805 Armada Drive, Carlsbad 92008) is a Grand Pacific Resorts "
        "vacation-ownership resort. Hilton's own city-page card and its own property page name the PUBLIC hotel on "
        "that campus as 'The Cassara Carlsbad, Tapestry Collection by Hilton' at '5805 Armada Dr Building B' "
        "(property code sanppup); that hotel is its own census identity. The vacation-ownership resort itself is "
        "never admitted, and it may not carry the hotel's brand property code (shared campus, not merged)."),
    "marbrisa carlsbad resort": (
        "TIMESHARE -- Hilton's own property page for these premises (1594 MarBrisa Circle, Carlsbad 92008, code "
        "sanmbgv) names them 'Hilton Grand Vacations Club MarBrisa Carlsbad', a vacation-ownership club resort; the "
        "bureau's 'MarBrisa Carlsbad Resort' listing is the same premises and is never a hotel identity."),
    "aviara golf at park hyatt resort": (
        "NON_HOTEL -- the Visit Carlsbad listing 'Aviara Golf at Park Hyatt Resort' (7447 Batiquitos Drive) is the "
        "resort's GOLF CLUB, a separate listing from the hotel; the hotel itself is Park Hyatt Aviara Resort "
        "(7100 Aviara Resort Drive, code sanpa), its own census identity."),
    "exquisite twelve bedroom oceanfront home": (
        "VACATION_RENTAL -- a whole-home rental named by its bedroom count; never a hotel identity."),
    "wyndham harbour lights": (
        "TIMESHARE -- the brand's own property service for this route (wyndhamhotels.com/wyndham-vacations/..."
        "/club-wyndham-harbour-lights) names the premises 'Club Wyndham Harbour Lights' (911 Fifth Ave, 92101), "
        "a Club Wyndham vacation-ownership resort; never admitted without proof of public hotel operation."),
    "club wyndham harbour lights": (
        "TIMESHARE -- the brand's own property service names these premises 'Club Wyndham Harbour Lights' (911 "
        "Fifth Ave, 92101), a Club Wyndham vacation-ownership resort; the same premises as the 'Wyndham Harbour "
        "Lights' map / register row. A timeshare's own brand page is not proof of public hotel operation."),
    "legoland california resort": (
        "NON_HOTEL -- the LEGOLAND California theme park itself; its two public hotels (LEGOLAND Hotel and "
        "LEGOLAND Castle Hotel) are their own census identities."),
}

#: VACATION OWNERSHIP. Names that are, on their face, a timeshare / vacation-ownership club resort. Generic chain
#: vocabulary (statewide, not Orlando-specific) is kept from the Orlando V2 / Miami / Fort Lauderdale
#: precedent; Palm-Beach-specific resort names are added only as this order's own evidence surfaces them.
_TIMESHARE = re.compile(
    r"\b(hilton grand vacations|grand vacations club|hgv club|marriott vacation club|worldmark|club wyndham|"
    r"wyndham vacation|bluegreen|diamond resorts|holiday inn club vacations|vistana|westgate (lakes|vacation "
    r"villas|town center|palace|leisure)|disney vacation club|vacation villas|vac villas|hyatt vacation club|"
    r"hyatt residence club|sheraton vistana|festiva|grand pacific palisades|grand pacific resorts|carlsbad seapointe|"
    r"welk resorts?|lawrence welk|hilton vacation club|club intrawest|shell vacations|raintree|"
    r"coronado beach resort|pacific shores resort|"
    r"timeshare|vacation ownership|vacation club|residence club)\b", re.I)
#: WHOLE-HOME AND UNIT RENTALS.
_VACATION_RENTAL = re.compile(
    r"\b(vacation homes?|vacation rentals?|rental homes?|resort homes|townhomes?|townhouses?|condos?|condominiums?|"
    r"homes and courts|str #\s*\d*|villa rentals?|luxury villas|pool homes?|private homes?|holiday homes?)\b", re.I)
#: RESORT RESIDENCES -- privately owned residences inside a resort campus, rented by their owners or a manager.
_RESORT_RESIDENCE = re.compile(r"\b(private residences|resort residences|the residences at|residence club)\b", re.I)
#: SHORT-TERM-RENTAL / SERVICED-APARTMENT OPERATORS -- app-managed unit portfolios inside residential towers, not a
#: public hotel operation (downtown San Diego, Little Italy and the beach communities carry many).
#: A brand-inventory or hotel-page read still overrides this.
_STR_OPERATOR = re.compile(r"\b(sonder|kasa|vacasa|evolve|domio|lyric|airbnb|vrbo|frontdesk|blueground|"
                           r"stay alfred|mint house|cozysuites|luxury rentals?|beach rentals?|furnished|avantstay|"
                           r"corporate housing|onthesand|beach cottage rentals?)\b", re.I)
#: MEASURED IN THIS ORDER: the committed nonhotel-rulings modules this file was cloned from (Jacksonville, Miami,
#: Fort Lauderdale, West Palm Beach) carry literal BACKSPACE bytes (0x08) where this pattern's two ``\b`` word
#: boundaries belong -- a heredoc that wrote ``\b`` into a non-raw string -- so in those markets this rule could
#: never match anything. It is repaired HERE, in San Diego's own copy, and recorded as a finding; the other
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


#: SAN DIEGO: a register row or listing whose own name is a COMPANY (LLC / Inc / management / realty) and not a hotel, or whose
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

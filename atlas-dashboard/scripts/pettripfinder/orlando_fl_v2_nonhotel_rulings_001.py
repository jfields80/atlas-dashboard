"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- the vacation-rental / timeshare / resort-residence / venue filter.

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

#: Rows whose LODGING category cannot be settled from the evidence. Held as IDENTITY_REVIEW_REQUIRED.
LODGING_UNCONFIRMED = {
}

NOT_LODGING_WHY = {
    "jetblue orlando support center lodge": (
        "NON_HOTEL -- JetBlue University's crew-training lodge at 8465 Hangar Boulevard (licensed HOTL to the airline's "
        "lodge management company) houses JetBlue trainees; it is not sold to the public"),
    "lake nona club": _VENUE + " (Lake Nona Golf & Country Club's members' lodge, licensed for 18 units)",
    "bay hill club lodge": (
        "NON_HOTEL -- the Bay Hill Club & Lodge rooms are sold to club members and tournament guests through the club, "
        "not a public hotel with its own booking page; held out of the census as club lodging"),
    "orange county national golf club llc": _VENUE + " (a golf club's stay-and-play lodge licensed to the golf club)",
    "shades of green": ("NON_HOTEL -- MILITARY_GOVERNMENT_NONPUBLIC: Shades of Green is an Armed Forces Recreation Center "
                        "open only to eligible military patrons"),
}

#: VACATION OWNERSHIP. Names that are, on their face, a timeshare / vacation-ownership club resort.
_TIMESHARE = re.compile(
    r"\b(hilton grand vacations|grand vacations club|hgv club|marriott vacation club|marriotts (lakeshore reserve|grande "
    r"vista|harbour lake|cypress harbour|sabal palms|royal palms|imperial palms)|worldmark|club wyndham|wyndham vacation|"
    r"bluegreen|diamond resorts|holiday inn club vacations|vistana|westgate (lakes|vacation villas|town center|palace|"
    r"leisure)|disney vacation club|vacation villas|vac villas|hyatt vacation club|hyatt residence club|sheraton vistana|"
    r"summer bay resort|festiva|orange lake resort|parkway international|liki tiki|star island resort|mystic dunes|"
    r"el sol resort|legacy vacation|silver lake resort|lake buena vista resort village|tuscana resort|"
    r"timeshare|vacation ownership|vacation club|residence club)\b", re.I)
#: WHOLE-HOME AND UNIT RENTALS.
_VACATION_RENTAL = re.compile(
    r"\b(vacation homes?|vacation rentals?|rental homes?|resort homes|townhomes?|townhouses?|condos?|condominiums?|"
    r"homes and courts|str #\s*\d*|villa rentals?|luxury villas|pool homes?|private homes?|holiday homes?|"
    r"windsor hills|windsor palms|encore resort|storey lake|solara resort|champions gate resort homes|"
    r"reunion resort homes|vista cay|blue heron beach|magic village|compass bay|paradise palms|regal oaks|"
    r"terra verde|lucaya village|bella piazza|emerald island|high grove|sonoma resort|west haven)\b", re.I)
#: RESORT RESIDENCES -- privately owned residences inside a resort campus, rented by their owners or a manager.
_RESORT_RESIDENCE = re.compile(r"\b(private residences|resort residences|the residences at|residence club)\b", re.I)
_APARTMENT_NAME = re.compile(r"\b(apartments?|apt homes|lofts llc)\b", re.I)

#: Lanes whose presence means a brand's own public hotel inventory or a hotel page reached the row.
_PUBLIC_HOTEL_LANES = ("PROPERTY_PAGE", "BRAND_INVENTORY")


def nonhotel_by_name(name, lanes):
    """The exclusion reason for a row whose own name reads as non-hotel lodging, or None."""
    n = re.sub(r"[’']", "", name or "")
    if any(str(l or "").startswith(_PUBLIC_HOTEL_LANES) for l in (lanes or ())):
        return None
    if _TIMESHARE.search(n):
        return ("TIMESHARE -- the row's own name (%r) is a vacation-ownership / timeshare club resort, and no brand's "
                "public hotel inventory and no hotel page read reached it; individual timeshare units and "
                "vacation-ownership inventory are never admitted without proof of exact public hotel operation" % name)
    if _RESORT_RESIDENCE.search(n):
        return ("RESORT_RESIDENCE -- the row's own name (%r) is a private resort-residence club, not a public hotel" % name)
    if _VACATION_RENTAL.search(n):
        return ("VACATION_RENTAL -- the row's own name (%r) is a vacation-home, villa, townhome or condo rental "
                "community; whole-home and unit rentals are never hotel identities" % name)
    if _APARTMENT_NAME.search(n):
        return _APARTMENTS + " (%r)" % name
    return None


def exclusion_class(reason):
    """VACATION_RENTAL / TIMESHARE / RESORT_RESIDENCE / NON_HOTEL from a NON_LODGING reason string."""
    head = (reason or "").split(" --", 1)[0].strip()
    return head if head in ("VACATION_RENTAL", "TIMESHARE", "RESORT_RESIDENCE", "NON_HOTEL") else "NON_HOTEL"

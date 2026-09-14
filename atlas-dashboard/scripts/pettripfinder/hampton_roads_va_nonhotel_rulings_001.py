"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- the vacation-rental / timeshare / condo / military / venue filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, a city bureau's own
category, or the property's own site.

Nothing here fetches and nothing here admits.
"""
from __future__ import annotations

_RENTAL_CO = "a vacation-rental / property-management / realty company, not a lodging establishment"
_APARTMENTS = ("apartment inventory rented by the unit, not a hotel selling public nightly rooms under a front "
               "desk; refused under the order's apartment rule")
_VENUE = "a venue, association or office, not lodging"
_TIMESHARE = ("vacation-ownership (timeshare) club inventory sold to owners and exchanged by points; it does not "
              "independently qualify as a public hotel under the order's timeshare rule")
_CONDO = ("an individual condominium / beach-house rental unit or unit collection, not a hotel operating public nightly "
          "rooms; refused under the order's condo and vacation-rental rule")

#: Rows whose LODGING category cannot be settled from the evidence. Held as
#: IDENTITY_REVIEW_REQUIRED (never admitted, never refused as non-hotel by guesswork).
_VACATION_OWNERSHIP = ("an Oceanfront vacation-ownership / condo resort whose only website any lane names is a timeshare "
                       "sales or rental agent (%s), not the resort's own hotel operation; whether it sells public nightly "
                       "hotel rooms under an on-site front desk, or only owner and rental-program units, is not settled by "
                       "the evidence read (order: timeshare units without normal public hotel operation are not admitted)")
LODGING_UNCONFIRMED = {
    "barclay towers resort": _VACATION_OWNERSHIP % "vbtimesharerentals.com",
    "boardwalk resort and hotel villas": _VACATION_OWNERSHIP % "vbtimesharerentals.com / tophotelreservations.com",
    "four sails resort": _VACATION_OWNERSHIP % "vbtimesharerentals.com; the bureau files Capital Vacations LLC at the same street",
    "turtle cay resort": _VACATION_OWNERSHIP % "tophotelreservations.com",
    "beach quarters resort": _VACATION_OWNERSHIP % "tophotelreservations.com",
    "ocean key resort": _VACATION_OWNERSHIP % "vsaresorts.com (VSA Resorts)",
    "ocean sands resort and spa": _VACATION_OWNERSHIP % "vsaresorts.com (VSA Resorts)",
    "the atrium resort": _VACATION_OWNERSHIP % "vsaresorts.com (VSA Resorts)",
    "ocean holiday": _VACATION_OWNERSHIP % "vabeachvacations.com",
}

#: PHASE 6 -- resort / multi-building identities that are not ONE bookable hotel identity. Held as
#: IDENTITY_REVIEW_REQUIRED with the RESORT_COMPONENT_IDENTITY class; never published as a vague complex.
RESORT_COMPLEX_IDENTITY = {
}

#: A map row that is a building or wing of a hotel the census already carries under its own name.
COMPONENT_OF = {
    "red roof inn": ("Red Roof Inn Newport News", "a map row naming only the flag at 16890 Warwick Boulevard, the building Red "
                     "Roof's own record (rri1371) states as '16890 Warwick Blvd, Building A' beside Choice's Quality Inn in "
                     "Building B"),
}

NOT_LODGING_WHY = {
    "virginia beach cvb hotel": ("the Virginia Beach Convention & Visitors Bureau's own office listing (website visitvirginiabeach.com, "
                                 "2101 Parks Avenue) that the bureau files in its accommodations group; " + _VENUE),
    "virginia beach hotel association": "the hoteliers' trade association office at 1060 Laskin Road; " + _VENUE,
    "salt air family concierge": "a family travel-concierge / rental-arrangement service with no lodging premises; " + _RENTAL_CO,
    "flohom": "a short-term rental operator whose listings link to its own booking engine for units; " + _RENTAL_CO,
    "vb timeshare rentals inc": "a timeshare rental agency office (968 South Oriole Drive, Suite 203); " + _TIMESHARE,
    "solace apartments": _APARTMENTS + " (a map row tagged as lodging on an apartment community)",
    "the james apartments": _APARTMENTS + " (a map row tagged as lodging on a downtown Norfolk apartment building)",
    "national at harbor towers": _APARTMENTS + " (a map row tagged as lodging on the Harbor Towers residential tower)",
    "in law suite": _CONDO + " (a map row naming a private in-law suite on Baum Road)",
}

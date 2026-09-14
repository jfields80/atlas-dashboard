"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- the vacation-rental / timeshare / apartment / venue filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, the Charleston
Area CVB's own category, or the property's own site.

Nothing here fetches and nothing here admits.
"""
from __future__ import annotations

_RENTAL_CO = "a vacation-rental / property-management company, not a lodging establishment"
_APARTMENTS = ("apartment inventory rented by the unit, not a hotel selling public nightly rooms under a front "
               "desk; refused under the order's apartment rule")
_VENUE = "a venue or bar, not lodging"
_TIMESHARE = ("vacation-ownership (timeshare) club inventory sold to owners and exchanged by points; it does not "
              "independently qualify as a public hotel under the order's timeshare rule")

#: Rows whose LODGING category cannot be settled from the evidence. Held as
#: IDENTITY_REVIEW_REQUIRED (never admitted, never refused as non-hotel by guesswork).
_VACATION_CLUB = ("a Hilton Grand Vacations club property: vacation-ownership inventory that Hilton also sells by the "
                  "night. Whether it independently qualifies as a public hotel under the order's timeshare rule is not "
                  "settled by the evidence read (a founder ruling); its own page states only 'Service animals only'")
_STR_UNTYPED = ("a map row (tourism=guest_house) with no website of its own, no bureau listing and no brand; whether it "
                "is an inn with bookable rooms on its own premises or a whole-house / apartment short-term rental is not "
                "settled by the evidence read")
LODGING_UNCONFIRMED = {
    "hilton vacation club lodge alley inn charleston": _VACATION_CLUB,
    "hilton club liberty place charleston": _VACATION_CLUB.replace("Hilton Grand Vacations club property",
                                                                   "Hilton Club (members' vacation-ownership) property"),
    "hilton vacation club king 583 charleston": _VACATION_CLUB,
    "bee and blossom historic charm": _STR_UNTYPED,
    "charleston 1857 luxury guesthouse": _STR_UNTYPED,
    "5 doughty street": _STR_UNTYPED,
    "the preserve collection": _STR_UNTYPED,
    "27 state": ("a map row whose website (27statestreet.com) served no lodging address, policy or room typing on this "
                 "run; " + _STR_UNTYPED.split("; ", 1)[1]),
    "the vibe on spring": ("a map row whose website (thevibeonspring.com) served no readable content on this run; "
                           + _STR_UNTYPED.split("; ", 1)[1]),
    "historic 86 church street charleston": ("its only website is an allcharlestonhotels.com aggregator page, not the "
                                             "operator's own site; " + _STR_UNTYPED.split("; ", 1)[1]),
    "the quarters on spring": ("its only website is an allcharlestonhotels.com aggregator page, not the operator's own "
                               "site; " + _STR_UNTYPED.split("; ", 1)[1]),
    "the quarters on vendue": ("its only website is an allcharlestonhotels.com aggregator page, not the operator's own "
                               "site; " + _STR_UNTYPED.split("; ", 1)[1]),
}

#: PHASE 8 -- resort / multi-building identities that are not ONE bookable hotel identity. Held as
#: IDENTITY_REVIEW_REQUIRED with the RESORT_COMPONENT_IDENTITY class; never published as a vague complex.
RESORT_COMPLEX_IDENTITY = {
    "wild dunes resort sweetgrass inn and boardwalk inn":
        "Hyatt's one listing (chsdb, 5757 Palm Blvd, Isle of Palms) names TWO distinct hotels -- the Sweetgrass Inn and "
        "the Boardwalk Inn -- plus a second listing for the resort's Residences at Sweetgrass (chsdv) that resolves to the "
        "same page; the bureau lists the Boardwalk Inn separately at 200 Grand Pavilion Boulevard. The operative pet "
        "policy (the resort FAQ refuses pets 'anywhere on the resort grounds', on a document stating no address) must "
        "bind to each inn's own premises, so the complex identity is held",
    "boardwalk inn":
        "the Wild Dunes resort's Boardwalk Inn, listed by the bureau at 200 Grand Pavilion Boulevard with no postal code; "
        "Hyatt books it only inside the combined 'Sweetgrass Inn and Boardwalk Inn' listing, so no first-party page states "
        "this inn's own identity",
}

#: A map row that is a building or wing of a hotel the census already carries under its own name.
COMPONENT_OF = {
    "the enclave at the vendue": ("the vendue", "The Enclave is The Vendue's second building on Vendue Range; the map's "
                                  "website tag is The Vendue's own rooms page (thevendue.com/hotel-rooms-charleston)"),
    "the residences at zero george": ("zero george", "the residences are Zero George's own suites (its FAQ names its "
                                      "'1 Bedroom and 3 Bedroom Residences'); one hotel identity"),
}

NOT_LODGING_WHY = {
    "charming inns": "the Charming Inns hotel group's corporate site (charminginns.com, where victoriahouseinn.com "
                     "redirects); its JSON-LD address is the group's, not a lodging establishment of its own",
    "the palms of charleston": "a unit in the Lowcountry Getaway vacation-rental portfolio (its only website is "
                               "lowcountrygetaway.com/properties/palms); " + _RENTAL_CO,
    "the rutledge avenue inn": "a suite in the Duvet vacation-rental portfolio (stayduvet.com/charleston-rentals); "
                               + _RENTAL_CO,
    "emerson square charleston": "a Guesty booking page for a short-term-rental unit (emersonsquare.guestybookings.com); "
                                 + _RENTAL_CO,
    "22 charlotte": "its own policies page rents a 'Cozy Cottage' for stays of 30 days or more -- a monthly cottage "
                    "rental, not a hotel selling nightly rooms",
    "two meeting street inn": "now the Kiawah Island Club's private members' inn (its only website is "
                              "kiawahisland.com/island-club/two-meeting-street-inn); private / member-only lodging is not "
                              "public lodging",
}

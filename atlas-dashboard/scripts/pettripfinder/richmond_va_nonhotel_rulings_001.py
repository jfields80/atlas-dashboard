"""PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 -- the vacation-rental / timeshare / apartment / venue filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, Visit Richmond VA's own category, or the property's own site.

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
LODGING_UNCONFIRMED = {
    "roslyn retreat and conference center": (
        "a diocesan retreat and conference center Visit Richmond lists under lodging; whether its group-retreat rooms are "
        "public nightly lodging sold to individual travellers is not settled by the evidence read"),
    "classified moto": (
        "a Visit Richmond lodging listing with no website, no map row and no brand; whether it is a public lodging "
        "establishment at all is not settled by the evidence read"),
}

#: PHASE 8 -- resort / multi-building identities that are not ONE bookable hotel identity. Held as
#: IDENTITY_REVIEW_REQUIRED with the RESORT_COMPONENT_IDENTITY class; never published as a vague complex.
RESORT_COMPLEX_IDENTITY = {
}

#: A map row that is a building or wing of a hotel the census already carries under its own name.
COMPONENT_OF = {
}

NOT_LODGING_WHY = {
    "central virginia african american chamber of commerce": (
        "a chamber of commerce office (cvaacc.org) that Visit Richmond files under its lodging category; not lodging"),
    "eileen rva": ("its own site (eileenrva.com) rents numbered apartment units ('All units other than 101 and 102 are on "
                   "2nd floor') with house rules and no front desk; " + _APARTMENTS),
    "richmond raceway":"a motorsports venue (its listing website is the raceway's ADA page); " + _VENUE,
    "university forest apartments 1400s": _APARTMENTS + " (a map row tagged as lodging on an apartment community)",
}

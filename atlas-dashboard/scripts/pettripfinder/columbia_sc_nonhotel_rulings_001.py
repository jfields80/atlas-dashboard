"""PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001 -- the vacation-rental / timeshare / condo / military / venue filter, by name.

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
    "flutter wing": ("a Main Street listing the bureau links only to a Hotel Trundle sub-page that answers 404; whether it is a "
                     "separately bookable public lodging establishment, a wing of Hotel Trundle or a short-term rental is not "
                     "settled by any first-party page read"),
}

#: PHASE 6 -- resort / multi-building identities that are not ONE bookable hotel identity. Held as
#: IDENTITY_REVIEW_REQUIRED with the RESORT_COMPONENT_IDENTITY class; never published as a vague complex.
RESORT_COMPLEX_IDENTITY = {
}

#: A map row that is a building or wing of a hotel the census already carries under its own name.
COMPONENT_OF = {
}

NOT_LODGING_WHY = {
    "the 1425 inn": ("an apartment unit of Historic Stays of Columbia: the bureau's own link (1425inn.com) redirects to "
                     "historicstaysofcolumbia.com, whose own home page (attended browser, 2026-09-15) calls its three downtown "
                     "buildings 'rental apartments' and 'luxury apartments'; " + _APARTMENTS),
    "historic stays of columbia": ("a downtown rental-apartment operator (historicstaysofcolumbia.com: 'Historic apartments for "
                                   "rent'); " + _RENTAL_CO),
}

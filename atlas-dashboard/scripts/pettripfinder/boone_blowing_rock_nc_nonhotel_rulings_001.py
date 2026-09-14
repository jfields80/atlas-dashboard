"""PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 -- the cabin / vacation-rental / timeshare filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, Explore
Boone's own sub-category, or the property's own site.

Nothing here fetches and nothing here admits.
"""
from __future__ import annotations

_TIMESHARE = ("a vacation-ownership (timeshare) resort: owner weeks / points inventory, not a hotel selling "
              "public nightly rooms under its own front desk; refused under the order's timeshare rule")
_CONDO = ("a condominium complex whose units are rented individually through owners or rental agencies; "
          "refused under the order's condo-unit rule")
_CABINS = ("a cabin / chalet / vacation-home rental, not operated as a qualifying lodging establishment "
           "with nightly rooms and a front desk; refused under the order's cabin and vacation-rental rule")
_REALTY = "a cabin-rental / property-management company, not a lodging establishment"

#: Rows whose LODGING category cannot be settled from the evidence. Held as
#: IDENTITY_REVIEW_REQUIRED (never admitted, never refused as non-hotel by guesswork).
LODGING_UNCONFIRMED = {
    "art of living retreat center":
        "a wellness / meditation retreat campus (639 Whispering Hills Road) whose own site sells retreat programs, "
        "wellness packages and event venues with campus accommodations; whether it sells public nightly rooms as a "
        "lodging establishment independent of a program is unconfirmed (its FAQ 'No, our facility does not permit "
        "pets' is also a sentence the shared reader does not read)",
    "willow valley resort":
        "a 'family oriented legacy resort' in Vilas whose own site carries a Homeowners section and golf course; the "
        "bureau files it under Cabins, Cottages & Condos first. Whether it operates public nightly rooms under a front "
        "desk or is owner / timeshare condo inventory is unconfirmed",
}

NOT_LODGING_WHY = {}

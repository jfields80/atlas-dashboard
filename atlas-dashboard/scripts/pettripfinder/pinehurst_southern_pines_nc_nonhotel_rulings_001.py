"""PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001 -- the cabin / vacation-rental / timeshare filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, the Visitors Bureau's own category, or the property's own site.

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
    "duncraig manor":
        "a 1928 Tudor estate the bureau files under Hotels / Inns beside Event Venue and Wedding Venue; its own site "
        "(790 E Connecticut Ave, Southern Pines 28387) now presents it as 'North Carolina's most distinctive luxury "
        "event venue' and offers no bookable rooms on the page read, so whether it still sells public nightly rooms "
        "is unconfirmed",
}

_GOLF_PACKAGES = ("a golf-package operator whose lodging is its villas, lodges and cottages (Talamore Villas, Mid South "
                  "Lodges, Palmer and Brooks Cottages) and resold condos and golf homes, not a hotel selling public "
                  "nightly rooms under a front desk; refused under the order's golf-villa / condo rule")
NOT_LODGING_WHY = {
    "maples golf packages": _GOLF_PACKAGES,
    "talamore golf resort": _GOLF_PACKAGES,
    "tanglewood farm":
        "the farm's own site now titles itself 'Luxury Vacation Rentals & Gourmet Food' (tanglewoodfarmsp.com); a "
        "vacation-rental farm stay, not an inn with bookable rooms under a front desk; refused under the order's "
        "vacation-rental rule",
    "the old church in pinehurst village":
        "the property's own site is titled 'Reserve to Rent' and sells 'The Space' -- a renovated 1919 church rented "
        "as a whole property; a single vacation rental, not a hotel identity",
}

"""PTF-OUTER-BANKS-NC-PARALLEL-SOURCE-READY-001 -- the vacation-rental / timeshare filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, the Visitors
Bureau's own sub-category, or the property's own site.

Nothing here fetches and nothing here admits.
"""
from __future__ import annotations

_TIMESHARE = ("a vacation-ownership (timeshare) resort: owner weeks / points inventory, not a hotel selling "
              "public nightly rooms under its own front desk; refused under the order's timeshare rule")
_CONDO = ("a condominium complex whose units are rented individually through owners or rental agencies; "
          "refused under the order's condo-unit rule")
_COTTAGES = ("a cottage collection / vacation-house rental, not operated as a qualifying lodging establishment "
             "with nightly rooms and a front desk; refused under the order's vacation-rental rule")
_REALTY = "a realty / property-management rental office, not a lodging establishment"

#: Rows whose LODGING category cannot be settled from the evidence: they may be a hotel
#: establishment or a rental product, and no first-party page said which. Held as
#: IDENTITY_REVIEW_REQUIRED (never admitted, never refused as non-hotel by guesswork).
LODGING_UNCONFIRMED = {
    "ocean villas": "a map-only row named 'Ocean Villas' at 7031 S Virginia Dare Trail; no destination listing and no "
                    "official site any lane found, and 'villas' on this beach names condo / cottage rental complexes as "
                    "often as motels -- lodging category unconfirmed",
    "ocean villas ii": "a map-only row named 'Ocean Villas II' at 7023 S Virginia Dare Trail; as 'Ocean Villas' -- lodging "
                       "category unconfirmed",
    "pierhouse b and b": "the bureau lists 'Pierhouse B&B' (2048 N Virginia Dare Trail) under Bed & Breakfasts, but the "
                         "only website it gives is Sandbar Beach Rentals, a vacation-rental company whose own page states "
                         "a different street (1817 N Virginia Dare Trail); whether an inn operates at 2048 is unconfirmed",
    "pierhouse bandb": "the bureau lists 'Pierhouse B&B' (2048 N Virginia Dare Trail) under Bed & Breakfasts, but the only "
                       "website it gives is Sandbar Beach Rentals, a vacation-rental company whose own page states a "
                       "different street (1817 N Virginia Dare Trail); whether an inn operates at 2048 is unconfirmed",
}

NOT_LODGING_WHY = {
    # vacation ownership
    "hilton vacation club beachwoods kitty hawk":
        "Hilton Vacation Club Beachwoods is " + _TIMESHARE + " (Hilton Grand Vacations club inventory; its own page "
        "states 'Service animals only')",
    "barrier island station at kitty hawk": "Barrier Island Station is " + _TIMESHARE,
    "sea scape beach and golf villas": "Sea Scape Beach & Golf Villas is " + _TIMESHARE,
    "villas at spa koru": "The Villas at Spa Koru is " + _TIMESHARE + " (and on Hatteras Island, outside)",
    # rental houses and cottage collections
    "moon glow": "Moon Glow is an individual vacation house marketed by a rental agency (carolinadesigns.com); " + _COTTAGES,
    "dolphin inn obx beach house": "Dolphin Inn OBX Beach House is an individual vacation rental house; " + _COTTAGES,
    "saltaire cottages": "Saltaire Cottages is " + _COTTAGES,
    "clemons cottage": "Clemons Cottage is a single rental cottage marketed by Cottages on Roanoke Island (the bureau "
                       "files it under Bed & Breakfasts, but its only website is the cottage-rental company's); "
                       + _COTTAGES,
    # not lodging at all
    "kitty hawk pier": "Kitty Hawk Pier is the fishing pier / restaurant beside Hilton Garden Inn at 5353 N Virginia "
                       "Dare Trail, not a separate lodging establishment",
}

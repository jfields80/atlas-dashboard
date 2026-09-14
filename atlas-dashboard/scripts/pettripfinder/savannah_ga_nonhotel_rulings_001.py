"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- the vacation-rental / apartment / venue filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, Visit
Savannah's own category, or the property's own site.

Nothing here fetches and nothing here admits.
"""
from __future__ import annotations

_RENTAL_CO = "a vacation-rental / property-management company, not a lodging establishment"
_APARTMENTS = ("apartment inventory rented by the unit, not a hotel selling public nightly rooms under a front "
               "desk; refused under the order's apartment rule")
_VENUE = "a venue or bar, not lodging"

#: Rows whose LODGING category cannot be settled from the evidence. Held as
#: IDENTITY_REVIEW_REQUIRED (never admitted, never refused as non-hotel by guesswork).
LODGING_UNCONFIRMED = {
    "the ann savannah apartments by marriott bonvoy":
        "Marriott's own page names it 'Apartments by Marriott Bonvoy' (110 Ann Street) and the bureau files it under "
        "both Hotels & Motels and Vacation Rentals. Whether it operates public nightly rooms under a front desk as a "
        "hotel, or is apartment inventory rented by the unit, is not settled by the evidence read",
    "signia by hilton savannah":
        "not yet open: the bureau's own listing links Hilton's news release that the Signia by Hilton on Hutchinson "
        "Island is expected to open in 2028, and Hilton's own page states no street number (International Drive, the "
        "31402 post-office code); a hotel that does not yet trade is never a census identity",
}

NOT_LODGING_WHY = {
    "hos management": "a hotel management company office (103 S Godley Station Blvd Ste 201, Pooler) the bureau files "
                      "under Hotels & Motels; " + _RENTAL_CO.replace("vacation-rental / property-management", "hotel management"),
    "savannah convention center": _VENUE + " (the Savannah Convention Center on Hutchinson Island, which the bureau "
                                  "files under Hotels & Motels)",
    "bar julian": _VENUE + " (the Thompson Savannah's rooftop bar, which the bureau files under Hotels & Motels)",
    "stayinsavannah com": "a booking website the bureau lists at the DoubleTree's address and phone, not a lodging "
                          "establishment of its own",
}

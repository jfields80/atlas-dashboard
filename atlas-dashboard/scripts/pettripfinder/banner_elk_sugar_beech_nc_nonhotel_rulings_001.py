"""PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001 -- the condo / cabin / rental / timeshare / camp filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, the roster's
own category, or the property's own site (persisted by sha256 in the static and
policy-page lanes).

Nothing here fetches and nothing here admits.
"""
from __future__ import annotations

_TIMESHARE = ("a vacation-ownership (timeshare) resort: owner weeks / points inventory, not a hotel selling "
              "public nightly rooms under its own front desk; refused under the order's timeshare rule")
_CONDO = ("a condominium complex / homeowners' association whose units are individually owned and rented "
          "unit-by-unit through owners or rental agencies; refused under the order's condo-unit rule")
_REALTY = ("a vacation-rental / property-management company or booking platform renting other owners' cabins, "
           "chalets and condos, not a lodging establishment; refused under the order's rental-portfolio rule")
_CABINS = ("a cabin / cottage / chalet rental, not operated as a qualifying lodging establishment with nightly "
           "rooms and a front desk; refused under the order's cabin and vacation-rental rule")
_CAMP = ("a summer camp, retreat centre, campground or RV park -- group or campsite lodging, not a hotel "
         "establishment; refused under the order's campground / camp rule")

NOT_LODGING_WHY = {
    # rental companies and platforms (their own sites were read: listings of owners' units)
    "above and beyond mountain rentals": _REALTY,
    "beech mountain chalet rentals": _REALTY + " (gobeech.com lists owners' chalets and condos by unit code)",
    "beech mountain resort lodging": _REALTY + " (the resort's own page: 'a curated collection of vacation rentals')",
    "resort real estate and rentals at sugar mountain": _REALTY,
    "resort real estate and rentals": _REALTY,
    "blue ridge mountain rentals": _REALTY,
    "mill ridge poa chalet rentals": _REALTY + " (a property-owners' association chalet rental desk)",
    "cornerstone cabins and lodge of banner elk nc": _REALTY + " (cornerstonerentals.com: 'Our rentals are pet friendly')",
    "cornerstone cabins and lodge of banner elk": _REALTY + " (cornerstonerentals.com)",
    "dereka s high country vacations": _REALTY,
    "derekas high country vacations": _REALTY,
    "nc cabin rentals llc": _REALTY,
    "foscoe realty rentals echota": _REALTY,
    "vacasa": _REALTY,
    "vrbo rentals": _REALTY,
    "airbnb": _REALTY,
    "white wolf lodge": _REALTY + " (whitewolflodge.org sells 'Winter Rentals' and 'Summer Rentals' listings and "
                                  "a BBQ restaurant; no hotel rooms under a front desk)",
    "alpine log cabin": _CABINS,
    # condominium complexes
    "christie village": _CONDO + " (its own rental FAQ: pets 'for Christie Village homeowners only')",
    "highlands at sugar resort": _CONDO,
    "sugar ski and country club hoa": _CONDO + " (the resort's partner list: 'resort style condominium')",
    "sugar ski and country club": _CONDO + " (the resort's partner list: 'resort style condominium')",
    "sugar top resort condominium association inc": _CONDO,
    "the citadel": _CONDO + " (Sugar Top's condominium tower)",
    "appres ski": _CONDO,
    "pinnacle inn": _CONDO + " (the Beech Mountain Visitor Center: 'individually owned ski suite studio rentals'; "
                             "rentals through Beech Mountain Chalet Rentals, no direct phone)",
    # timeshare
    "blue ridge village resort bluegreen vacations corporation": _TIMESHARE,
    # camps, retreats, campgrounds and RV parks
    "holston camp and retreat center": _CAMP,
    "lutherock camp and conference center": _CAMP,
    "lutherock camp and retreat center": _CAMP,
    "ymca camp harrison": _CAMP,
    "mountain river family campground": _CAMP,
    "the barlow rv": _CAMP,
    # cabins and cottages
    "linville river cottages": _CABINS,
    "cross creek log cabins": _CABINS,
    "heathbrooke cabin": _CABINS,
    # not lodging at all
    "the village of banner elk": ("a dining / shopping / entertainment village (bannerelkvillage.com: restaurants, "
                                  "shops, an arcade); its own site offers no lodging; not a lodging business"),
}

#: Rows whose LODGING category cannot be settled from the evidence. Held as
#: IDENTITY_REVIEW_REQUIRED (never admitted, never refused as non-hotel by guesswork).
LODGING_UNCONFIRMED = {
    "eseeola lodge":
        "the lodge of the private Linville Golf Club (175 Linville Avenue); the club's own site is a members' "
        "portal with cottages for rent to members, and whether the lodge sells public nightly rooms "
        "independent of membership is unconfirmed",
}

#: Map-only rows whose CURRENT identity is unconfirmed. Held as IDENTITY_REVIEW_REQUIRED.
IDENTITY_REVIEWS = {
    "pineola motel":
        "a map-only 'Pineola Motel' at 340 Jonas Ridge Highway, 600 m from The Pineola (3085 Linville Falls "
        "Highway), whose own site names no motel of that name; whether the map row is a second building or the "
        "stale name of The Pineola is unconfirmed, so neither a merge nor a second identity is invented",
}

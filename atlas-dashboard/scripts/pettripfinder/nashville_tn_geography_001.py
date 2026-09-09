"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phase 2, the market geography.

Writes the PROPOSED market contract for Greater Nashville, Tennessee:

    launch_packages/pettripfinder/markets/proposed/nashville-tn.json

``markets/*.json`` IS the market registry, so writing there would REGISTER the
market and invalidate the current deployment record. This order stops at the
serialized promotion boundary, so the contract is authored under
``markets/proposed/`` and promoting Nashville later is a MOVE of this file, not
a rewrite. That is the Toledo precedent (PTF-TOLEDO-OH-NEW-MARKET-001).

WHAT THE GEOGRAPHY IS, AND WHAT IT DELIBERATELY IS NOT
------------------------------------------------------
The market is the practical Greater Nashville TRAVELER LODGING market. It is
not the municipal line, not Davidson County alone, and emphatically not the
Nashville MSA, which reaches Clarksville, Columbia, Gallatin, Dickson and
Springfield and would roughly double the census for no traveler reason.

Membership basis is CORRIDOR_REGISTRY: the corridors are a POSTAL-CODE
PARTITION and every lodging ZIP in the market is claimed by exactly one
corridor. A discovered hotel is therefore never placed by its mailing city --
the failure that put twelve outer-neighbourhood hotels inside Downtown
Cincinnati. "Nashville" is the mailing city of Antioch, Hermitage, Bellevue,
Donelson, Green Hills and Old Hickory alike; it decides nothing here.

THE ONE ZIP THAT TWO CORRIDORS WANT
-----------------------------------
ZIP 37214 carries BOTH the Donelson/BNA airport cluster AND the Music Valley
Drive / Opryland cluster, four miles apart and two entirely different traveler
markets. A ZIP partition cannot split them, so 37214 is claimed by
``airport-donelson`` for MEMBERSHIP, and the Opryland corridor claims its
properties by ``explicit_hotel_ids``, which is tier 2 in
``markets.assignment.assign_hotels`` and therefore outranks the tier-3 ZIP
match for display. Membership stays deterministic; display stays true. Same
mechanism Indianapolis uses for ZIP 46202.

THE FRINGE, HELD RATHER THAN ASSUMED
------------------------------------
This order was told to evaluate, not to assume, the areas that ring Davidson
County. Three of them are ADMITTED on evidence and five are HELD:

  ADMITTED  Brentwood (37027) -- contiguous with Davidson County at I-65, the
            Maryland Farms lodging node, and named "Nashville Brentwood" by the
            operators' OWN published property names (Marriott's roster carries
            bnaab AC Hotel NASHVILLE Brentwood, bnasb Sheraton NASHVILLE
            Brentwood, bnabr Courtyard NASHVILLE Brentwood, bnabt TownePlace
            Suites NASHVILLE Brentwood, bnawo SpringHill Suites NASHVILLE
            Brentwood). Five separate first-party market claims.
  ADMITTED  Goodlettsville (37072) -- ZIP 37072 STRADDLES the Davidson/Sumner
            county line; part of it is Metropolitan Nashville-Davidson ground.
            Marriott names bnagv Courtyard NASHVILLE Goodlettsville and bnatg
            TownePlace Suites NASHVILLE Goodlettsville.
  ADMITTED  Madison / Rivergate (37115) -- unincorporated Davidson County.

  HELD      Franklin / Cool Springs (37067, 37064, 37069), Mount Juliet
            (37122), Hendersonville (37075), Smyrna / La Vergne (37167, 37086)
            and Lebanon (37087, 37090). Each is authored as a corridor with
            ``included_postal_codes`` EMPTY and its candidate ZIPs recorded in
            ``_held_postal_codes``. A held corridor claims nothing, so its
            hotels are discovered, identified, routed and then classified
            OUT_OF_MARKET_BOUNDARY_DECISION rather than silently missed -- and
            a founder ruling that admits one is a one-line ZIP move, fully
            reversible, with the census effect stated in the packet.

Nothing here publishes. ``show_in_navigation`` and ``show_in_sitemap`` are
false on the market and on every corridor, exactly as Toledo shipped them.

Output:
  launch_packages/pettripfinder/markets/proposed/nashville-tn.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
OUT = os.path.join(PKG, "markets", "proposed", "nashville-tn.json")

#: ``(slug, name, display_area, description, admitted ZIPs, held ZIPs)``.
#: A corridor with an EMPTY admitted list and a non-empty held list is a
#: FOUNDER HOLD: it claims nothing and admits nothing until a ruling moves the
#: ZIPs from ``_held_postal_codes`` into ``included_postal_codes``.
CORRIDORS = [
    ("downtown-broadway", "Downtown Nashville / Broadway / SoBro", "Downtown",
     "Lower Broadway, SoBro, the Music City Center, Bridgestone Arena, Printers "
     "Alley, Nashville Yards, the Capitol district and the Nissan Stadium East Bank.",
     ["37201", "37219", "37213", "37243", "37246"], []),
    ("the-gulch-midtown-music-row", "The Gulch / Midtown / Music Row", "The Gulch / Music Row",
     "The Gulch, Division Street, Demonbreun Hill, Midtown and the Music Row "
     "publishing district -- walkable to Broadway but its own overnight market.",
     ["37203"], []),
    ("vanderbilt-west-end", "Vanderbilt / West End / Hillsboro Village", "Vanderbilt / West End",
     "Vanderbilt University and Medical Center, West End Avenue, Centennial Park, "
     "Elliston Place, Belmont University and Hillsboro Village.",
     ["37212"], []),
    ("green-hills-berry-hill", "Green Hills / Berry Hill / 8th South", "Green Hills",
     "Green Hills, Hillsboro Pike, Forest Hills, Oak Hill, Berry Hill, Melrose "
     "and the 8th Avenue South corridor.",
     ["37204", "37215", "37220"], []),
    ("west-nashville-belle-meade", "West Nashville / Belle Meade / Charlotte Pike", "West Nashville",
     "Belle Meade, White Bridge, Sylvan Park, The Nations and the Charlotte Pike "
     "corridor west of I-440.",
     ["37205", "37209"], []),
    ("germantown-metrocenter", "Germantown / MetroCenter / North Nashville", "Germantown / MetroCenter",
     "Germantown, MetroCenter, Jefferson Street, Bordeaux, Whites Creek and "
     "Joelton, on the I-65 and I-24 northern approaches.",
     ["37208", "37228", "37218", "37189", "37080"], []),
    ("east-nashville", "East Nashville / Inglewood / Dickerson Pike", "East Nashville",
     "Five Points, Lockeland Springs, Inglewood, the Gallatin Pike corridor and "
     "the Dickerson Pike / Trinity Lane I-65 interchange.",
     ["37206", "37216", "37207"], []),
    ("airport-donelson", "BNA Airport / Donelson / Briley Parkway", "Airport / Donelson",
     "Nashville International Airport, Briley Parkway, Elm Hill Pike, Royal "
     "Parkway, Donelson, Lebanon Pike and the Murfreesboro Pike I-24 interchanges.",
     ["37214", "37217", "37210"], []),
    ("opryland-music-valley", "Opryland / Music Valley", "Opryland / Music Valley",
     "Gaylord Opryland, the Grand Ole Opry House, Opry Mills and the Music "
     "Valley Drive hotel row -- inside ZIP 37214 but four miles from the airport "
     "and a different traveler market, so its properties are claimed by name.",
     [], []),
    ("south-nashville-antioch", "South Nashville / Antioch / I-24", "South Nashville / Antioch",
     "Nolensville Pike, Harding Place, Hickory Hollow, Bell Road and the I-24 "
     "southeast interchanges.",
     ["37211", "37013"], []),
    ("hermitage-old-hickory", "Hermitage / Old Hickory / I-40 East", "Hermitage",
     "Hermitage, Old Hickory, the Andrew Jackson Hermitage corridor and I-40 "
     "exit 221 inside Davidson County.",
     ["37076", "37138"], []),
    ("madison-rivergate-goodlettsville", "Madison / Rivergate / Goodlettsville", "Madison / Rivergate",
     "Madison, the Rivergate retail cluster and Goodlettsville at I-65 exits 92 "
     "to 97. ZIP 37072 straddles the Davidson/Sumner county line.",
     ["37115", "37072"], []),
    ("bellevue-i40-west", "Bellevue / I-40 West", "Bellevue",
     "Bellevue, Old Hickory Boulevard west and the I-40 exit 196 corridor.",
     ["37221"], []),
    ("brentwood-maryland-farms", "Brentwood / Maryland Farms", "Brentwood",
     "Maryland Farms, Brentwood South and the I-65 exits 74 and 71 business "
     "lodging cluster, contiguous with Davidson County.",
     ["37027"], []),
    ("cool-springs-franklin", "Franklin / Cool Springs", "Franklin / Cool Springs",
     "Cool Springs, Berry Farms and downtown Franklin at I-65 exits 68 to 65. "
     "HELD: the operators' own property names call this FRANKLIN, not Nashville.",
     [], ["37067", "37064", "37069"]),
    ("mount-juliet-i40-east", "Mount Juliet / I-40 East", "Mount Juliet",
     "Providence and the I-40 exit 226 cluster in Wilson County. HELD for a "
     "founder ruling.",
     [], ["37122"]),
    ("hendersonville", "Hendersonville", "Hendersonville",
     "Vietnam Veterans Boulevard and the Old Hickory Lake shore in Sumner "
     "County. HELD for a founder ruling.",
     [], ["37075"]),
    ("smyrna-la-vergne", "Smyrna / La Vergne", "Smyrna",
     "The I-24 exits 66 to 70 cluster in Rutherford County. HELD for a founder "
     "ruling; this order recommends EXCLUDE as Murfreesboro-orbit inventory.",
     [], ["37167", "37086"]),
    ("lebanon-i40-east", "Lebanon", "Lebanon",
     "I-40 exits 238 and 239 in Wilson County, thirty miles east. HELD for a "
     "founder ruling; this order recommends EXCLUDE.",
     [], ["37087", "37090"]),
]

BOUNDARY_NOTE = (
    "PTF-NASHVILLE-TN-NEW-MARKET-001 visitor market: the practical Greater "
    "Nashville traveler lodging market, not the municipal line and not the "
    "Nashville MSA. INCLUDED: the whole of Metropolitan Nashville-Davidson "
    "County -- downtown and Lower Broadway, SoBro, the East Bank, the Gulch, "
    "Midtown and Music Row, Vanderbilt and West End, Hillsboro Village and "
    "Belmont, Green Hills, Forest Hills, Oak Hill, Berry Hill, Belle Meade, "
    "Sylvan Park and The Nations, Germantown, MetroCenter, Bordeaux, Whites "
    "Creek, Joelton, East Nashville and Inglewood, the Dickerson Pike I-65 "
    "corridor, BNA airport and Briley Parkway, Donelson, Music Valley and "
    "Opryland, Murfreesboro Pike, South Nashville and Antioch, Hermitage and "
    "Old Hickory, Madison and Rivergate, and Bellevue -- PLUS two contiguous "
    "corridors admitted on first-party evidence: Brentwood (37027), whose "
    "lodging the operators' own published property names call NASHVILLE "
    "Brentwood five times over, and Goodlettsville (37072), whose ZIP straddles "
    "the Davidson/Sumner county line. HELD FOR A FOUNDER RULING, authored as "
    "corridors that claim no postal code and therefore admit nothing: Franklin "
    "and Cool Springs, Mount Juliet, Hendersonville, Smyrna and La Vergne, and "
    "Lebanon. EXCLUDED OUTRIGHT: Murfreesboro, Spring Hill, Columbia, "
    "Clarksville, Gallatin, Dickson, Springfield, Cookeville and Bowling Green, "
    "Kentucky -- every one of which is reached by a BNA-prefixed Marriott "
    "property code, which is precisely why a code prefix is a SELECTOR here and "
    "never a membership decision. No committed discovery box overlaps this one: "
    "the nearest committed market, Louisville, Kentucky, begins at 37.9 N, more "
    "than 1.4 degrees of latitude north. This market publishes nothing in this "
    "work order.")

CORRIDOR_NOTE = (
    "Corridors are a postal-code partition (census_membership_basis "
    "CORRIDOR_REGISTRY). Every admitted lodging ZIP is claimed by exactly one "
    "corridor, so a discovered hotel is never placed by mailing city -- "
    "'Nashville' is the mailing city of Antioch, Hermitage, Bellevue, Donelson, "
    "Green Hills and Old Hickory alike and decides nothing. ONE EXCEPTION, "
    "authored deliberately: ZIP 37214 carries both the Donelson/BNA cluster and "
    "the Music Valley Drive / Opryland cluster, four miles apart and two "
    "different traveler markets. 37214 is claimed by airport-donelson for "
    "MEMBERSHIP; the Opryland corridor claims its properties by "
    "explicit_hotel_ids, which is tier 2 in markets.assignment.assign_hotels and "
    "outranks the tier-3 ZIP match, so display stays true without making "
    "membership ambiguous. ZIP 37209 joins Belle Meade rather than Germantown "
    "because The Nations and Charlotte Pike are one west-side retail corridor. "
    "ZIP 37210 joins airport-donelson rather than downtown because Elm Hill Pike "
    "and the Fairgrounds sit on the airport approach, not on Broadway.")

HOLD_NOTE = (
    "A corridor whose included_postal_codes is EMPTY and whose "
    "_held_postal_codes is not is a FOUNDER HOLD authored by "
    "PTF-NASHVILLE-TN-NEW-MARKET-001. It claims nothing and admits nothing: "
    "every hotel in those ZIPs is discovered, identified and then classified "
    "OUT_OF_MARKET_BOUNDARY_DECISION, so the founder rules on evidence rather "
    "than on an absence. Admitting one is a one-line move of the ZIPs from "
    "_held_postal_codes into included_postal_codes and is fully reversible. "
    "No held row is published, counted as census, or given paid acquisition "
    "budget by this order.")


def corridor(index, slug, name, area, description, zips, held):
    return OrderedDict([
        ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
        ("market_id", MARKET_ID),
        ("name", name),
        ("slug", slug),
        ("title", "Pet-Friendly Hotels in %s | PetTripFinder Nashville" % name),
        ("meta_description",
         "Verified pet-friendly hotels in %s, with real pet fees and policies "
         "read from each hotel's own official website." % name),
        ("description", description),
        ("included_cities", []),
        ("included_postal_codes", list(zips)),
        ("explicit_hotel_ids", []),
        ("excluded_hotel_ids", []),
        ("minimum_hotel_count", 5),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("allow_multi_corridor", False),
        ("display_order", index),
        ("display_area", area),
        ("state_code", "TN"),
    ] + ([("_held_postal_codes", list(held)),
          ("_hold", "FOUNDER_GEOGRAPHY_HOLD")] if held else []))


def build():
    corridors = [corridor(i + 1, *row) for i, row in enumerate(CORRIDORS)]

    # The partition proof, run here rather than asserted: no admitted ZIP may
    # be claimed twice, and a held ZIP may never also be admitted.
    admitted = Counter(z for c in corridors for z in c["included_postal_codes"])
    doubled = sorted(z for z, n in admitted.items() if n > 1)
    if doubled:
        raise SystemExit("ZIP claimed by more than one corridor: %s" % doubled)
    held = {z for c in corridors for z in c.get("_held_postal_codes", [])}
    both = sorted(held & set(admitted))
    if both:
        raise SystemExit("ZIP both admitted and held: %s" % both)

    doc = OrderedDict([
        ("schema", "ptf-market/1.1"),
        ("market_id", MARKET_ID),
        ("market_name", "Greater Nashville, Tennessee"),
        ("market_slug", MARKET_ID),
        ("state_name", "Tennessee"),
        ("state_code", "TN"),
        ("primary_state_code", "TN"),
        ("states", ["TN"]),
        ("primary_city", "Nashville"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Nashville, Tennessee | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Greater Nashville, Tennessee, with "
         "real pet fees and policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's "
         "own official website."),
        ("navigation_label", "Nashville"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", "market_prefixed"),
        ("census_membership_basis", "CORRIDOR_REGISTRY"),
        ("_boundary_note", BOUNDARY_NOTE),
        ("_corridor_note", CORRIDOR_NOTE),
        ("_founder_hold_note", HOLD_NOTE),
        ("corridors", corridors),
        ("registered_by", None),
        ("registered_at", None),
        ("_registration_note",
         "NOT REGISTERED. This file lives under markets/proposed/ on purpose: "
         "launch_packages/pettripfinder/markets/*.json IS the market registry and "
         "writing there would register Nashville and invalidate the current "
         "deployment record (PTF-047). Promoting Nashville is a MOVE of this file "
         "into markets/, performed by "
         "PTF-NASHVILLE-TN-PROMOTION-AND-APPLICATION-002, which must first "
         "integrate the then-current deployed canonical lineage."),
        ("authored_by", WORK_ORDER),
    ])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print("wrote %s" % os.path.relpath(OUT, _DASH))
    print("corridors            %d" % len(corridors))
    print("  admitted           %d" % sum(1 for c in corridors if c["included_postal_codes"]))
    print("  held (claim none)  %d" % sum(1 for c in corridors if c.get("_hold")))
    print("  by-name only       %d" % sum(
        1 for c in corridors if not c["included_postal_codes"] and not c.get("_hold")))
    print("admitted ZIPs        %d, each claimed exactly once" % len(admitted))
    print("held ZIPs            %d" % len(held))


if __name__ == "__main__":
    build()

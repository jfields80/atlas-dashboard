"""PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001 -- Augusta, GA shadow market build.

Builds a SHADOW (not registered) source-ready package for the Augusta,
Georgia / Greater Augusta market from real, web-researched hotel identity
data. Writes only under this market's own staging tree
(``launch_packages/pettripfinder/markets/staging/augusta-ga/``) plus its own
``markets/reports/augusta_ga_*`` report files -- nothing under the live
``launch_packages/pettripfinder/markets/`` or
``launch_packages/pettripfinder/markets/authority/`` directories, and no
change to any generated global compatibility artifact. That is what keeps
this a shadow build: ``market_authority.sharded_market_ids()`` run against
the live, unmodified authority directory must not contain ``augusta-ga``
after this script runs.

No per-property pet-policy evidence was captured in this pass (identity and
census work only, per PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001's scope).
Every census row's ``policy_state`` is therefore ``POLICY_NOT_VERIFIED`` and
every partition item lands in a blocker state -- the same honest pattern
``build_pittsburgh_market_001.py`` documents for its own revalidation pass.

Run:

    python -m scripts.pettripfinder.augusta_ga_market_build_001
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.census_partition_builder import (
    census_document, census_row, partition_document, partition_item,
    slugify, write_json,
)
from scripts.pettripfinder.contracts import enums

WORK_ORDER = "PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
AS_OF = "2026-09-14"

STAGING = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "staging" / MARKET_ID
LAUNCH_PKG = STAGING / "launch_package"
REPORTS = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"

CENSUS_PATH = LAUNCH_PKG / "identity_census" / ("%s.json" % MARKET_ID)
PARTITION_PATH = LAUNCH_PKG / ("%s_final_partition_001.json" % MARKET_ID.replace("-", "_"))
MARKET_CONFIG_PATH = LAUNCH_PKG / "markets" / ("%s.json" % MARKET_ID)
ROUTING_SHARD_PATH = LAUNCH_PKG / "markets" / "authority" / MARKET_ID / "identity_routing.json"
EXCLUSIONS_SHARD_PATH = LAUNCH_PKG / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json"
SEED_CSV_PATH = LAUNCH_PKG / "markets" / "authority" / MARKET_ID / "seed_businesses.csv"

# disposition:
#   observation  -> identity + property-level URL confirmed; no policy page
#                   content read this pass -> AWAITING_POLICY_OBSERVATION
#   no_url       -> identity confirmed, no usable official/property URL found
#                   -> AWAITING_OFFICIAL_URL
#   collision    -> identity not settled (shared address or shared brand
#                   property code with another row) -> AWAITING_IDENTITY_RESOLUTION

def _c(name, address, city, zip_, corridor, url=None, disposition="observation",
       collision_note="", notes=""):
    return dict(name=name, address=address, city=city, state="GA", zip=zip_,
                corridor=corridor, official_url=url or "", disposition=disposition,
                collision_note=collision_note, notes=notes)


CANDIDATES = [
    # --- Downtown Augusta (30901) ---
    _c("Augusta Marriott at the Convention Center", "2 10th Street", "Augusta", "30901",
       "downtown", "https://www.marriott.com/en-us/hotels/agsmc-augusta-marriott-at-the-convention-center/overview/"),
    _c("Hyatt House Augusta/Downtown", "1268 Broad Street", "Augusta", "30901",
       "downtown", "https://www.hyatt.com/hyatt-house/en-US/agshx-hyatt-house-augusta-downtown"),
    _c("Holiday Inn Express Augusta Downtown", "444 Broad Street", "Augusta", "30901",
       "downtown", "https://www.ihg.com/holidayinnexpress/hotels/us/en/augusta/agsag/hoteldetail"),
    _c("Ramada by Wyndham Augusta Downtown Hotel & Conference Center", "640 Broad Street", "Augusta", "30901",
       "downtown", "https://www.wyndhamhotels.com/ramada/augusta-georgia/ramada-augusta-downtown/overview"),
    _c("Econo Lodge Downtown Augusta", "1103 15th Street", "Augusta", "30901",
       "downtown", "https://www.choicehotels.com/georgia/augusta/econo-lodge-hotels"),
    _c("The Partridge Inn Augusta, Curio Collection by Hilton", "2110 Walton Way", "Augusta", "30904",
       "downtown", "https://www.hilton.com/en/hotels/agswepi-the-partridge-inn-augusta/",
       notes="On the Downtown/Medical District border; folded into Downtown -- Medical District has no other "
             "verified property and does not clear the no-thin-corridor bar on its own this pass."),
    _c("Queen Anne Inn", "406 Greene Street", "Augusta", "30901",
       "downtown", "https://www.queenanneinnaugusta.com/",
       notes="Independent B&B, Olde Town historic district; on the official Visit Augusta CVB lodging list."),
    _c("Olde Town Inn (Fox's Lair)", "349 Telfair Street", "Augusta", "30901",
       "downtown", "https://oldetowninnaugusta.com/",
       notes="Independent boutique inn; on the official Visit Augusta CVB lodging list."),

    # --- Washington Road / Augusta National corridor (mostly 30907/30909) ---
    _c("Wingate by Wyndham Augusta Washington Road", "2650-C Center West Parkway", "Augusta", "30909",
       "washington-road", "https://www.wyndhamhotels.com/wingate/augusta-georgia/wingate-by-wyndham-augusta-washington-road/overview"),
    _c("Tru by Hilton Augusta Washington Road", "2853 Washington Road", "Augusta", "30909",
       "washington-road", "https://www.hilton.com/en/hotels/agsgvru-tru-augusta-washington-road/"),
    _c("Spark by Hilton Augusta", "1050 Claussen Road", "Augusta", "30907",
       "washington-road", "https://www.hilton.com/en/hotels/agsggpe-spark-augusta/",
       notes="Same address as the former Sleep Inn and Conference Center; treated as one identity (rebrand), "
             "not two."),
    _c("Best Western Plus Augusta North Inn & Suites", "1062 Claussen Road", "Augusta", "30907",
       "washington-road", "https://www.bestwestern.com/en_US/book/hotels-in-augusta/best-western-plus-augusta-north-inn-suites/propertyCode.11231.html"),
    _c("Candlewood Suites Augusta", "1080 Claussen Road", "Augusta", "30907",
       "washington-road", "https://www.ihg.com/candlewood/hotels/us/en/augusta/agscw/hoteldetail"),
    _c("Hilton Garden Inn Augusta", "1065 Stevens Creek Road", "Augusta", "30907",
       "washington-road", "https://www.hilton.com/en/hotels/agsgigi-hilton-garden-inn-augusta/"),
    _c("Homewood Suites by Hilton Augusta", "1049 Stevens Creek Road", "Augusta", "30907",
       "washington-road", "https://www.hilton.com/en/hotels/augwehw-homewood-suites-augusta/"),
    _c("Holiday Inn Express Augusta (Stevens Creek Rd)", "1073 Stevens Creek Road", "Augusta", "30907",
       "washington-road", "https://www.ihg.com/holidayinnexpress/hotels/us/en/augusta/agsst/hoteldetail",
       notes="Distinct from Holiday Inn Express Augusta Downtown (444 Broad St)."),
    _c("Sheraton Augusta Hotel", "1069 Stevens Creek Road", "Augusta", "30907",
       "washington-road", "https://www.marriott.com/en-us/hotels/agshi-sheraton-augusta-hotel/overview/"),
    _c("Courtyard by Marriott Augusta", "1045 Stevens Creek Road", "Augusta", "30907",
       "washington-road", "https://www.marriott.com/en-us/hotels/agscy-courtyard-augusta/overview/"),
    _c("Comfort Suites Augusta Riverwatch", "2911 Riverwest Drive", "Augusta", "30907",
       "washington-road", "https://www.choicehotels.com/georgia/augusta/comfort-suites-hotels"),
    _c("Baymont Inn & Suites Augusta (Riverwest)", "2905 Riverwest Drive", "Augusta", "30907",
       "washington-road", "https://www.wyndhamhotels.com/baymont/augusta-georgia/baymont-inn-and-suites-augusta/overview"),
    _c("Microtel Inn & Suites by Wyndham Augusta", "2909 Riverwest Drive", "Augusta", "30907",
       "washington-road", "https://www.wyndhamhotels.com/microtel/augusta-georgia/microtel-inn-and-suites-augusta/overview"),
    _c("WoodSpring Suites Augusta Riverwatch", "2995 Riverwatch Parkway", "Augusta", "30907",
       "washington-road", "https://www.woodspring.com/extended-stay-hotels/locations/georgia/augusta/woodspring-suites-augusta-riverwatch"),
    _c("Quality Inn & Suites Augusta I-20", "2562 Center West Parkway", "Augusta", "30909",
       "washington-road", "https://www.choicehotels.com/georgia/augusta/quality-inn-hotels/gaa72"),
    _c("Rodeway Inn Augusta (Washington Rd)", "3027 Washington Road, Unit B", "Augusta", "30907",
       "washington-road", "https://www.choicehotels.com/georgia/augusta/rodeway-inn-hotels/gab67",
       disposition="collision", collision_note="shared-address-3027-washington-road",
       notes="Shares a street number with Masters Inn Augusta at the same address (no unit). Held for identity "
             "resolution rather than assumed to be the same building or assumed distinct."),
    _c("Red Roof Inn Washington Road Augusta", "3030 Washington Road, Building A", "Augusta", "30907",
       "washington-road", "https://www.redroof.com/property/GA/Augusta/RedRoofInnAugustaWashingtonRoad"),
    _c("HomeTowne Studios Augusta (Washington Rd)", "3030 Washington Road, Building B", "Augusta", "30907",
       "washington-road", "https://www.hometowne.com/",
       notes="Co-located sister Red Roof brand at the same complex as the Red Roof Inn above, in a separate "
             "building -- treated as a distinct identity, the same pattern as Motel 6 / Studio 6 co-location."),
    _c("Fairfield Inn & Suites Augusta Washington Rd. / I-20", "3023 1/2 Washington Road", "Augusta", "30907",
       "washington-road", "https://www.marriott.com/en-us/hotels/agswr-fairfield-inn-and-suites-augusta-washington-rd/overview/"),
    _c("Super 8 Motel Augusta (Washington Rd)", "3026 Washington Road", "Augusta", "30907",
       "washington-road", "https://www.wyndhamhotels.com/super-8/augusta-georgia/super-8-augusta-ga/overview"),
    _c("Days Inn Washington Road Augusta", "3020 Washington Road", "Augusta", "30907",
       "washington-road", "https://www.wyndhamhotels.com/days-inn/augusta-georgia/days-inn-augusta/overview"),
    _c("Hampton Inn & Suites Augusta-Washington Rd", "3028 B Washington Road", "Augusta", "30907",
       "washington-road", "https://www.hilton.com/en/hotels/agswrhx-hampton-suites-augusta-washington-rd/"),
    _c("Sonesta Essential Augusta", "3039B Washington Road", "Augusta", "30907",
       "washington-road", "https://www.sonesta.com/sonesta-essential/ga/augusta/sonesta-essential-augusta",
       disposition="collision", collision_note="shared-address-3039-washington-road",
       notes="Address is one letter-suffix away from Heritage Inn Augusta (3039, no suffix) on the same street. "
             "Held for identity resolution rather than assumed to be a rebrand or assumed distinct."),
    _c("Masters Inn Augusta (aka Masters Economy Inn)", "3027 Washington Road", "Augusta", "30907",
       "washington-road", "http://mastersinn.com",
       disposition="collision", collision_note="shared-address-3027-washington-road",
       notes="See Rodeway Inn Augusta (Washington Rd) above -- same street number."),
    _c("Heritage Inn Augusta", "3039 Washington Road", "Augusta", "30907",
       "washington-road", "",
       disposition="collision", collision_note="shared-address-3039-washington-road",
       notes="See Sonesta Essential Augusta above -- adjacent address. One reseller page ties a "
             "'travelodge'-branded domain to this address, unverified; no confirmed official URL either way."),
    _c("Sunset Inn Augusta", "3034 Washington Road", "Augusta", "30907",
       "washington-road", "", disposition="no_url",
       notes="Independent motel; no official or independent website found."),
    _c("Rodeway Inn Augusta West - Fort Eisenhower", "601 Northwest Frontage Road", "Augusta", "30907",
       "washington-road", "https://www.choicehotels.com/georgia/augusta/rodeway-inn-hotels/gac29"),
    _c("Baymont Inn & Suites West Augusta (NW Frontage Rd)", "629 NW Frontage Road", "Augusta", "30907",
       "washington-road", "https://www.wyndhamhotels.com/baymont/augusta-georgia/baymont-inn-and-suites-west-augusta/overview",
       notes="Distinct property from Baymont Inn & Suites Augusta (Riverwest Dr)."),
    _c("Knights Inn at Boy Scout Road Augusta", "210 Boy Scout Road", "Augusta", "30909",
       "washington-road", "https://www.wyndhamhotels.com/knights-inn/augusta-georgia/knights-inn-augusta/overview"),
    _c("West Bank Inn", "2904 Washington Road", "Augusta", "30909",
       "washington-road", "https://www.westbankinn.net/",
       notes="Independent motel near I-20 Exit 199 / National Hills."),

    # --- West Augusta (Jimmie Dyess Pkwy / Park West / Perimeter Pkwy / Marks Church / Wheeler Rd) ---
    _c("Econo Lodge West Augusta", "4045 Jimmie Dyess Parkway", "Augusta", "30909",
       "west-augusta", "https://www.choicehotels.com/georgia/augusta/econo-lodge-hotels/gab65"),
    _c("La Quinta Inn & Suites by Wyndham Augusta/Fort Eisenhower", "4049 Jimmie Dyess Parkway", "Augusta", "30909",
       "west-augusta", "https://www.wyndhamhotels.com/la-quinta/augusta-georgia/la-quinta-inn-and-suites-augusta-fort-gordon/overview"),
    _c("Comfort Inn & Suites West Augusta", "4071 Jimmie Dyess Parkway", "Augusta", "30909",
       "west-augusta", "https://www.choicehotels.com/georgia/augusta/comfort-inn-hotels",
       notes="Also listed as 'Comfort Inn & Suites Augusta West Near Fort Eisenhower' by a second directory; "
             "same address, treated as one identity."),
    _c("Quality Inn & Suites Augusta Fort Gordon Area", "4073 Jimmie Dyess Parkway", "Augusta", "30909",
       "west-augusta", "", disposition="observation",
       notes="Distinct address from the Quality Inn on Gordon Highway (2176) and the one on Center West Pkwy "
             "(2562); no property-level URL confirmed yet."),
    _c("Hampton Inn & Suites West Augusta", "4081 Jimmie Dyess Parkway", "Augusta", "30909",
       "west-augusta", "https://www.hilton.com/en/hotels/agswshx-hampton-suites-west-augusta/"),
    _c("Holiday Inn Express & Suites West Augusta", "4087 Jimmie Dyess Parkway", "Augusta", "30909",
       "west-augusta", "https://www.ihg.com/holidayinnexpress/hotels/us/en/augusta/agsjd/hoteldetail",
       disposition="collision", collision_note="ihg-code-agsjd-reused",
       notes="Two research passes independently confirmed this exact property/address/code. Held only because "
             "a second listing below reuses the same IHG code."),
    _c("Holiday Inn West Augusta", "441 Park West", "Augusta", "30909",
       "west-augusta", "https://www.ihg.com/holidayinn/hotels/us/en/augusta/agsjd/hoteldetail",
       disposition="collision", collision_note="ihg-code-agsjd-reused",
       notes="Carries the SAME IHG property code (agsjd) as Holiday Inn Express & Suites West Augusta above at "
             "a different address -- almost certainly one property double-listed under two brand/address "
             "combinations, but not confirmed. Held for identity resolution; not merged and not dropped."),
    _c("Hyatt Place Augusta", "160 Mason McKnight Jr. Parkway", "Augusta", "30907",
       "west-augusta", "https://www.hyatt.com/hyatt-place/en-US/agsza-hyatt-place-augusta"),
    _c("Extended Stay America Premier Suites - Augusta", "1137 Garredd Boulevard", "Augusta", "30909",
       "west-augusta", "https://www.extendedstayamerica.com/hotels/ga/augusta/augusta"),
    _c("DoubleTree by Hilton Hotel Augusta", "2651 Perimeter Parkway", "Augusta", "30909",
       "west-augusta", "https://www.hilton.com/en/hotels/agsddt-doubletree-augusta/"),
    _c("Affordable Suites of America Augusta", "2633 Perimeter Parkway", "Augusta", "30909",
       "west-augusta", "", disposition="no_url",
       notes="Independent extended-stay; no official website found."),
    _c("Home2 Suites by Hilton Augusta, GA", "3606 Exchange Lane", "Augusta", "30909",
       "west-augusta", "https://www.hilton.com/en/hotels/agsawht-home2-suites-augusta-ga/"),
    _c("Residence Inn by Marriott Augusta", "1116 Marks Church Road", "Augusta", "30909",
       "west-augusta", "https://www.marriott.com/en-us/hotels/agsri-residence-inn-augusta/overview/"),
    _c("SpringHill Suites by Marriott Augusta", "1110 Marks Church Road", "Augusta", "30909",
       "west-augusta", "https://www.marriott.com/en-us/hotels/agssh-springhill-suites-augusta/overview/"),
    _c("My Place Hotel-Augusta, GA", "3731 Wheeler Road", "Augusta", "30909",
       "west-augusta", "https://www.myplacehotels.com/locations/my-place-hotel-augusta"),
    _c("Days Inn Wheeler Road Augusta", "3654 Wheeler Road", "Augusta", "30909",
       "west-augusta", "https://www.wyndhamhotels.com/days-inn/augusta-georgia/days-inn-augusta-wheeler-rd/overview"),
    _c("Perrin Guest House Inn (aka Perrin Plantation and Inn)", "208 Lafayette Drive", "Augusta", "30909",
       "west-augusta", "", disposition="no_url",
       notes="Independent circa-1863 plantation-home B&B; no official website found."),

    # --- Gordon Highway corridor / Fort Eisenhower (formerly Fort Gordon) gate area ---
    _c("Studio 6 Fort Gordon Augusta", "3421 Wrightsboro Road", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.studio6.com/en/home/motels.ga.augusta.5080.html",
       notes="Co-located G6 Hospitality sister brand with Motel 6 below at the same site -- treated as a "
             "distinct identity (dual-brand-building rule)."),
    _c("Motel 6 Augusta, GA - Ft Gordon", "3421 Wrightsboro Road", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.motel6.com/en/home/motels.ga.augusta.5080.html"),
    _c("Quality Inn & Suites South Augusta (near Fort Gordon)", "2176 Gordon Highway", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.choicehotels.com/georgia/augusta/quality-inn-hotels"),
    _c("Hampton Inn Gordon Highway Augusta", "306 Timbercreek Lane", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.hilton.com/en/hotels/agsghhx-hampton-inn-augusta-gordon-highway/"),
    _c("Homewood Suites by Hilton Augusta Gordon Highway", "312 Timbercreek Lane", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.hilton.com/en/hotels/agsgohw-homewood-suites-augusta-gordon-highway/"),
    _c("Days Inn Fort Gordon Augusta", "2154 Gordon Highway", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.wyndhamhotels.com/days-inn/augusta-georgia/days-inn-fort-gordon-augusta/overview"),
    _c("Fairfield Inn & Suites by Marriott Augusta (Gordon Hwy / Fort Eisenhower Area)", "2175 Gordon Highway",
       "Augusta", "30909", "gordon-highway-fort-eisenhower",
       "https://www.marriott.com/en-us/hotels/agsaf-fairfield-inn-and-suites-augusta-fort-eisenhower-area/overview/",
       notes="Distinct property from the Fairfield Inn & Suites on Washington Rd."),
    _c("Ramada Hotel Fort Gordon Augusta", "2155 Gordon Highway", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.wyndhamhotels.com/ramada/augusta-georgia/ramada-fort-gordon-augusta/overview"),
    _c("WoodSpring Suites Fort Gordon Augusta", "2115 Noland Road Connector", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.woodspring.com/extended-stay-hotels/locations/georgia/augusta/woodspring-suites-augusta-"),
    _c("Wingate by Wyndham Fort Gordon Augusta", "2123 Noland Connector", "Augusta", "30906",
       "gordon-highway-fort-eisenhower", "https://www.wyndhamhotels.com/wingate/augusta-georgia/wingate-fort-gordon-augusta/overview"),
    _c("Super 8 Hotel Fort Gordon Augusta", "2137 Gordon Highway", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.wyndhamhotels.com/super-8/augusta-georgia/super-8-fort-gordon-augusta/overview"),
    _c("Scottish Inn Augusta (aka Deluxe Inn Augusta)", "1636 Gordon Highway", "Augusta", "30906",
       "gordon-highway-fort-eisenhower", "", disposition="no_url",
       notes="Same address surfaces as both 'Deluxe Inn Augusta' and 'Scottish Inns - Gordon Highway' across "
             "directories -- treated as one independently-franchised identity, not two; no confirmed official "
             "website either name."),
    _c("Comfort Inn & Suites Augusta Fort Eisenhower Area", "2121 Noland Connector", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "",
       notes="Distinct address from the Comfort Inn on Jimmie Dyess Pkwy; on the official Visit Augusta CVB "
             "lodging list."),
    _c("Red Carpet Inn - Augusta", "2050 Gordon Highway", "Augusta", "30909",
       "gordon-highway-fort-eisenhower", "https://www.stayhihotels.com/property/red-carpet-inn-augusta-ga/",
       notes="Independent/regional franchise."),
    _c("Budget Inn Express", "1616 Gordon Highway", "Augusta", "30906",
       "gordon-highway-fort-eisenhower", "https://www.budgetinnexpressaugusta.us/",
       notes="Independent; on the official Visit Augusta CVB lodging list."),

    # --- South Augusta ---
    _c("Americas Best Value Inn Augusta", "3320 Deans Bridge Road", "Augusta", "30906",
       "south-augusta", "", disposition="no_url"),
    _c("Rodeway Inn Augusta South", "2926 Peach Orchard Road", "Augusta", "30906",
       "south-augusta", "https://www.choicehotels.com/georgia/augusta/rodeway-inn-hotels/ga585"),
    _c("Rodeway Inn & Suites Hephzibah Augusta", "3682 Deans Bridge Road", "Hephzibah", "30815",
       "south-augusta", "https://www.hotelplanner.com/Hotels/56258/Reservations-Rodeway-Inn-Suites-Hephzibah-Augusta-Hephzibah-3682-Deans-Bridge-Rd-30815",
       notes="Hephzibah is an incorporated city inside Richmond County, adjoining south Augusta along Deans "
             "Bridge Rd; its own brand name blends 'Hephzibah' and 'Augusta'."),

    # --- Grovetown, GA ---
    _c("Baymont Inn & Suites Grovetown", "461 Parkwest Drive", "Grovetown", "30813",
       "grovetown", "https://www.wyndhamhotels.com/baymont/grovetown-georgia/baymont-inn-and-suites-grovetown/overview"),
    _c("Days Inn & Suites Grovetown", "459 Park West Drive", "Grovetown", "30813",
       "grovetown", "https://www.wyndhamhotels.com/days-inn/grovetown-georgia/days-inn-grovetown/overview"),
    _c("Best Western Augusta West (Grovetown)", "452 Parkwest Drive", "Grovetown", "30813",
       "grovetown", "https://www.bestwestern.com/en_US/book/hotels-in-grovetown/best-western-augusta-west/propertyCode.11194.html"),
    _c("Sleep Inn & Suites Grovetown - Augusta West", "456 Parkwest Drive", "Grovetown", "30813",
       "grovetown", "https://www.choicehotels.com/georgia/grovetown/sleep-inn-hotels"),
    _c("Home2 Suites by Hilton Grovetown Augusta Area", "903 Husk Box Way", "Grovetown", "30813",
       "grovetown", "https://www.hilton.com/en/hotels/agsgtht-home2-suites-grovetown-augusta-area/"),
    _c("avid hotel Augusta W - Grovetown", "900 Husk Box Way", "Grovetown", "30813",
       "grovetown", "https://www.ihg.com/avidhotels/hotels/us/en/grovetown/agsav/hoteldetail"),
    _c("TownePlace Suites by Marriott Grovetown", "893 Husk Box Way", "Grovetown", "30813",
       "grovetown", "https://www.marriott.com/en-us/hotels/agsgp-towneplace-suites-grovetown/overview/",
       notes="Dual-brand building shared with Fairfield Inn & Suites Grovetown -- two hotels, per the "
             "dual-brand-building rule."),
    _c("Fairfield Inn & Suites Grovetown", "893 Husk Box Way", "Grovetown", "30813",
       "grovetown", "https://www.marriott.com/en-us/hotels/agsgf-fairfield-inn-and-suites-grovetown/overview/",
       notes="Dual-brand building shared with TownePlace Suites Grovetown."),
    _c("Holiday Inn Express & Suites Augusta W - Grovetown", "3341 Log Deck Way", "Grovetown", "30813",
       "grovetown", "https://www.ihg.com/holidayinnexpress/hotels/us/en/grovetown/agsgr/hoteldetail"),
]

assert len(CANDIDATES) == 82, "expected 82 identity-resolved GA candidates, got %d" % len(CANDIDATES)

CORRIDOR_ORDER = [
    "downtown", "washington-road", "west-augusta",
    "gordon-highway-fort-eisenhower", "south-augusta", "grovetown",
]
CORRIDOR_LABELS = {
    "downtown": "Downtown Augusta",
    "washington-road": "Washington Road / Augusta National",
    "west-augusta": "West Augusta",
    "gordon-highway-fort-eisenhower": "Gordon Highway / Fort Eisenhower Gate",
    "south-augusta": "South Augusta",
    "grovetown": "Grovetown, GA",
}


def _disposition_to_final_state(disposition: str) -> str:
    return {
        "observation": enums.AWAITING_POLICY_OBSERVATION,
        "no_url": enums.AWAITING_OFFICIAL_URL,
        "collision": enums.AWAITING_IDENTITY_RESOLUTION,
    }[disposition]


def build_rows():
    census_rows = []
    partition_items = []
    for cand in CANDIDATES:
        name = cand["name"]
        key_source = name
        try:
            slug = slugify(name)
        except Exception:
            slug = ""
        identity_key = None
        from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
        identity_key = ptf_identity_key(key_source)

        identity_state = (enums.IDENTITY_PROVISIONAL if cand["disposition"] == "collision"
                          else enums.IDENTITY_CONFIRMED)
        lodging_state = enums.LODGING_BY_NAME
        collision_state = (enums.COLLISION_SHARED_ADDRESS
                           if cand["disposition"] == "collision" and "address" in cand["collision_note"]
                           else (enums.COLLISION_PROPERTY_CODE
                                 if cand["disposition"] == "collision" else enums.COLLISION_NONE))

        row = census_row(
            identity_key=identity_key,
            canonical_name=name,
            slug=slug,
            market_id=MARKET_ID,
            city=cand["city"],
            state=cand["state"],
            postal_code=cand["zip"],
            identity_state=identity_state,
            lodging_state=lodging_state,
            policy_state=enums.POLICY_NOT_VERIFIED,
            source="PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001 identity research (chain + independent + CVB lanes)",
            address=cand["address"],
            corridor=cand["corridor"],
            assignment_basis=enums.BASIS_EXPLICIT,
            assignment_value=cand["corridor"],
            collision_state=collision_state,
            observed_at=AS_OF,
            provenance="augusta_ga_market_build_001",
            official_url=cand["official_url"],
            carried={"notes": cand["notes"], "collision_note": cand["collision_note"]} if cand["notes"] or cand["collision_note"] else None,
        )
        census_rows.append(row)

        final_state = _disposition_to_final_state(cand["disposition"])
        item = partition_item(
            identity_key=identity_key,
            canonical_name=name,
            slug=slug,
            city=cand["city"],
            state=cand["state"],
            postal_code=cand["zip"],
            final_state=final_state,
            next_action_source="PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001",
            determined_by="PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001",
            updated_at=AS_OF,
            official_url=cand["official_url"],
        )
        partition_items.append(item)
    return census_rows, partition_items


def build_market_config():
    corridor_counts = {c: 0 for c in CORRIDOR_ORDER}
    for cand in CANDIDATES:
        corridor_counts[cand["corridor"]] += 1

    corridors = []
    for order, corridor_id in enumerate(CORRIDOR_ORDER, start=1):
        rows_here = [c for c in CANDIDATES if c["corridor"] == corridor_id]
        cities = sorted({r["city"] for r in rows_here})
        zips = sorted({r["zip"] for r in rows_here})
        corridors.append({
            "corridor_id": "augusta-ga-%s" % corridor_id,
            "market_id": MARKET_ID,
            "name": CORRIDOR_LABELS[corridor_id],
            "slug": corridor_id,
            "title": "Pet-Friendly Hotels in %s" % CORRIDOR_LABELS[corridor_id],
            "meta_description": "Pet-friendly hotels in the %s area of Greater Augusta, Georgia." % CORRIDOR_LABELS[corridor_id],
            "description": "",
            "included_cities": cities,
            "included_postal_codes": zips,
            "explicit_hotel_ids": [],
            "excluded_hotel_ids": [],
            "minimum_hotel_count": len(rows_here),
            "show_in_navigation": False,
            "show_in_sitemap": False,
            # Augusta's corridors are named-road areas (Washington Rd, Gordon
            # Hwy, ...), not ZIP boundaries, and several ZIPs (30906, 30907,
            # 30909) genuinely span more than one of them in the real postal
            # geography. Every corridor opts in to sharing rather than one
            # arbitrarily dropping a ZIP it legitimately has inventory in.
            "allow_multi_corridor": True,
            "display_order": order,
            "display_area": CORRIDOR_LABELS[corridor_id],
        })

    return {
        "schema": "ptf-market/1.1",
        "market_id": MARKET_ID,
        "market_name": "Augusta – Richmond County / Greater Augusta",
        "market_slug": MARKET_ID,
        "state_name": "Georgia",
        "state_code": "GA",
        "primary_state_code": "GA",
        "states": ["GA"],
        "primary_city": "Augusta",
        "country_code": "US",
        "title": "Pet-Friendly Hotels in Augusta, Georgia | PetTripFinder",
        "meta_description": "Pet-friendly hotels across Greater Augusta, Georgia -- downtown, Washington Road, "
                             "West Augusta, Gordon Highway / Fort Eisenhower, South Augusta and Grovetown.",
        "introductory_copy": "",
        "navigation_label": "Augusta, GA",
        "show_in_navigation": False,
        "show_in_sitemap": False,
        "minimum_published_hotels": 1,
        "route_mode": "market_prefixed",
        "corridors": corridors,
    }


def main() -> int:
    census_rows, partition_items = build_rows()

    census_doc = census_document(
        MARKET_ID, census_rows, captured_at=AS_OF,
        note="Augusta, GA identity/census research pass (PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001). "
             "No per-property pet-policy evidence captured this pass -- every row's policy_state is "
             "POLICY_NOT_VERIFIED and the partition carries only identity/routing blockers.",
        source_authorities=["augusta_ga_market_build_001"])
    census_doc["work_order"] = WORK_ORDER

    partition_doc = partition_document(
        MARKET_ID, partition_items, as_of=AS_OF,
        note="Augusta, GA source-ready partition. Zero PUBLISHED_PET_FRIENDLY / VERIFIED_NO_PETS rows by "
             "design -- policy evidence capture is deferred to a future pass.",
        source_authorities=["augusta_ga_market_build_001"])
    partition_doc["work_order"] = WORK_ORDER

    market_config = build_market_config()

    routing_shard = {
        "schema": "ptf-identity-routing/1.0",
        "market_id": MARKET_ID,
        "note": "No property-level routing bindings captured this pass; identity/census only.",
        "count": 0,
        "routes": [],
    }
    exclusions_shard = {
        "schema": "ptf-hotel-exclusions/1.0",
        "market_id": MARKET_ID,
        "exclusions": [],
    }

    census_hash = write_json(CENSUS_PATH, census_doc)
    partition_hash = write_json(PARTITION_PATH, partition_doc)
    market_hash = write_json(MARKET_CONFIG_PATH, market_config)
    routing_hash = write_json(ROUTING_SHARD_PATH, routing_shard)
    exclusions_hash = write_json(EXCLUSIONS_SHARD_PATH, exclusions_shard)

    SEED_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    seed_columns = ["name", "category", "address", "city", "state", "postal_code", "phone",
                     "website_url", "source_url", "source_type", "observed_at", "rating",
                     "amenities", "pet_policy", "canonical", "market_id"]
    with SEED_CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(seed_columns)

    print("census   : %s (%s)" % (CENSUS_PATH, census_hash[:16]))
    print("partition: %s (%s)" % (PARTITION_PATH, partition_hash[:16]))
    print("market   : %s (%s)" % (MARKET_CONFIG_PATH, market_hash[:16]))
    print("routing  : %s (%s)" % (ROUTING_SHARD_PATH, routing_hash[:16]))
    print("excludes : %s (%s)" % (EXCLUSIONS_SHARD_PATH, exclusions_hash[:16]))
    print("seed csv : %s" % SEED_CSV_PATH)
    print("rows     : %d" % len(census_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

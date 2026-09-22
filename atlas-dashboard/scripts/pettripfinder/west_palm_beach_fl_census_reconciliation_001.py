"""PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 -- Phases 9, 11 and 24: one identity graph.

Cloned from the Fort Lauderdale census helper (itself from Miami, Tampa V2, Orlando V2, Savannah, Boone,
Outer Banks and Atlanta), with Palm Beach County's vocabulary. Independent discovery lanes, none
authoritative on its own:

  REGISTRY_FL_DBPR    every HOTL / MOTL / BNB public-lodging licence in an admitted or careful-evaluation postal
                      code, from the State of Florida's own licence extract (tier 2: the state's record of the
                      licensed premises -- street, ZIP, licence number, rental units).
  OSM_OVERPASS        tourism=hotel / motel / guest_house / apartment / chalet elements inside the observation box,
                      read from the local Geofabrik Florida extract (ODbL).
  BRAND_INVENTORY     the committed national Marriott harvest (PBI-coded routes); Marriott's Florida hotel sitemap
                      page; Hilton's own Florida city pages (property cards stating each hotel's address); the
                      brands' own sitemaps that answered (Wyndham, Drury, Loews, ESA, Sonesta, InTown, WoodSpring).
  DESTINATION_ORGANIZATION  the lodging listings of Discover The Palm Beaches, Palm Beach County's own CVB
                      (thepalmbeaches.com), selected from the bureau's own sitemap and read through the
                      already-authorized Firecrawl renderer (the bureau refuses a plain client outright).
  PROPERTY_PAGE       the address each property's OWN page (or its brand's own property service) states, from the
                      static, Firecrawl and attended passes.
  COMPETITOR_LEAD     names only, from BringFido. Discovery only.

WHAT DECIDES AN IDENTITY
------------------------
Address, postal code, phone or brand property code. Never a name on its own. A DBPR phone is the licensee's line
and, like a map phone, is never a merge key.

WHAT DECIDES MEMBERSHIP
-----------------------
The market contract's postal partition (west_palm_beach_fl_geography_001). Refused neighbours carry their
reason; BROWARD names the EXISTING LIVE market fort-lauderdale-fl and Miami-Dade names the EXISTING LIVE
market miami-fl -- both already publish that inventory, so admitting one of their postal codes would publish
the same hotel twice. Martin / St. Lucie and Monroe name future standalones.

VACATION RENTALS, CONDOS, TIMESHARES AND RESORT RESIDENCES ARE NOT HOTELS
--------------------------------------------------------------------------
Palm Beach County carries 856 DBPR condominium (CNDO) and 1,843 vacation-dwelling (DWEL) licences and 1,110
non-transient apartments against just 194 hotel / motel / B&B licences -- PGA National's villas, Wellington's
equestrian-season rentals, Singer Island's and Highland Beach's towers and the Delray / Boca oceanfronts hold
most of them; they are counted by the registry lane and never enter this graph. A licence or map row whose own name
reads as a vacation home community, villa / condo rental, resort residence or vacation-ownership club -- and that
no brand's public hotel inventory and no hotel page read reached -- is NON_LODGING with a VACATION_RENTAL /
TIMESHARE / RESORT_RESIDENCE reason (west_palm_beach_fl_nonhotel_rulings_001).

REGISTERED
----------
Written to identity_census_proposed/ while the market was shadow; REGISTERED by PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002,
so it is written to identity_census/, as every registered market's census is.

Nothing here fetches. Nothing here carries a pet policy.

Outputs:
  launch_packages/pettripfinder/identity_census/west-palm-beach-fl.json
  launch_packages/pettripfinder/markets/reports/west_palm_beach_fl_census_reconciliation_001.json
  launch_packages/pettripfinder/markets/reports/west_palm_beach_fl_competitor_gap_matrix_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name      # noqa: E402
from scripts.pettripfinder.markets import contract as MC        # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder import west_palm_beach_fl_geography_001 as GEO  # noqa: E402

#: Admitted-ZIP rows whose MUNICIPALITY cannot be decided from a first-party page, in a postal code the
#: geography shares with a refused municipality. Held, never admitted by the map's city label. Empty at
#: authoring time.
GEOGRAPHY_HOLDS = {}

#: TWO CENSUS ROWS, ONE PREMISES, AND THE HOUSE NUMBERS DISAGREE.
#:
#: Keyed on the normalised canonical name; every row named here is demoted to IDENTITY_REVIEW_REQUIRED so that
#: ONE building cannot publish TWICE and cannot publish under an address its own operator contradicts. A row is
#: added only after THIS order's own first-party read proved it, and the reason names the exact resolution a
#: registration order should make. Never repaired here: rewriting a street silently is precisely what the
#: evidence contract forbids.
SAME_PREMISES_HOLDS = {
    "ben west palm": (
        "SAME PREMISES AS 'The Ben, Autograph Collection'. The Florida DBPR licence HOT6014077 ('BEN WEST "
        "PALM') is at 251 N NARCISSUS AVE 33401, and the brand's OWN property page for MARSHA code pbiak, "
        "read by this order's attended browser on 2026-09-22, states the premises as '251 N Narcissus "
        "Avenue, West Palm Beach, Florida, USA, 33401'. The licence and the operator agree. RESOLUTION a "
        "registration order should make: correct the brand row's street to 251 N Narcissus Ave and alias this "
        "licence row into it, publishing ONE hotel."),
    "courtyard by marriott west palm beach airport": (
        "SAME PREMISES AS 'Courtyard West Palm Beach Airport'. Both rows state house number 1800 in 33401 and "
        "the same street spelled two ways -- this row carries '1800 Centre Dr. E.' from the DBPR licence and "
        "the destination bureau, the other carries '1800 Centrepark Drive East' from the committed national "
        "Marriott harvest and OSM. The brand's OWN page for MARSHA code pbicy, read by this order's attended "
        "browser on 2026-09-22, states the premises as '1800 Centrepark Drive East, West Palm Beach, Florida, "
        "USA, 33401'. RESOLUTION: adopt the operator's own spelling and alias this row into the coded row, "
        "publishing ONE hotel."),
    "sonesta select boca raton": (
        "SAME PREMISES AS 'Sonesta Select Boca Raton Town Center'. Both rows state house number 2000 in 33431 "
        "and share the telephone 561-241-7070, and both of this market's routes for them resolve to ONE "
        "property slug on the brand's own host (sonesta-select-boca-raton). The brand's OWN page, read by "
        "this order's attended browser on 2026-09-22, is titled 'Sonesta Select Boca Raton Town Center' and "
        "states the premises as '2000 NW Executive Center Circle, Boca Raton, FL 33431'. The shared telephone "
        "is corroboration only and was never the merge key -- the house number, the street and the brand's "
        "own single property page are. The Town Center row is NOT held: after the street-spelling merge it "
        "carries both the operator's own name and the operator's own complete street ('2000 Northwest "
        "Executive Center Circle'), so ONE correct row publishes and this abbreviated licence row is the one "
        "aliased into it."),
    "the ben autograph collection": (
        "SAME PREMISES AS the DBPR-licensed row 'Ben West Palm', and this row's street DISAGREES with its own "
        "operator. It carries MARSHA code pbiak and street '215 North Narcissus Avenue' from the committed "
        "national Marriott harvest, OSM and a competitor lead; the brand's OWN page for pbiak, read this "
        "order, states 251 N Narcissus Avenue, as does DBPR licence HOT6014077. The harvested house number is "
        "stale. Held rather than published: publishing a hotel at a house number its own operator contradicts "
        "would send a guest to the wrong door. RESOLUTION: adopt 251 N Narcissus Ave from the first-party "
        "read and alias the licence row into this one."),
}

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "west-palm-beach-fl"
SCHEMA = "ptf-market-identity-census/1.1"
REPORT_SCHEMA = "ptf-census-reconciliation/1.0"
GAP_SCHEMA = "ptf-competitor-gap-matrix/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")

REPORTS = os.path.join(PKG, "markets", "reports")
#: REGISTERED by PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002: the census is written to the registry's own
#: identity_census/ and the contract is read from markets/<id>.json, as every registered market's is. The
#: source-ready order's proposed/ copies are history.
CENSUS_DIR = os.path.join(PKG, "identity_census")
CONTRACT_PATH = os.path.join(PKG, "markets", "west-palm-beach-fl.json")

OSM_LANE = os.path.join(REPORTS, "west_palm_beach_fl_osm_lane_001.json")
BRAND = os.path.join(REPORTS, "west_palm_beach_fl_brand_inventory_001.json")
ATTENDED_PASS = os.path.join(REPORTS, "west_palm_beach_fl_policy_reads_001.json")
SOUTH_FL_REUSE = os.path.join(REPORTS, "west_palm_beach_fl_south_florida_reuse_001.json")
DESTINATION = os.path.join(REPORTS, "west_palm_beach_fl_destination_roster_001.json")
DBPR_LANE = os.path.join(REPORTS, "west_palm_beach_fl_dbpr_lane_001.json")

# --------------------------------------------------------------------------- #
# Classification vocabulary (the work order's, verbatim).
# --------------------------------------------------------------------------- #
TRUE_HOTEL_IDENTITY = "TRUE_HOTEL_IDENTITY"
DUPLICATE_LISTING = "DUPLICATE_LISTING"
SAME_CAMPUS_DISTINCT_ENTITY = "SAME_CAMPUS_DISTINCT_ENTITY"
NON_LODGING = "NON_LODGING"
OUTSIDE_MARKET = "OUTSIDE_MARKET"
NAME_ONLY_UNRESOLVED = "NAME_ONLY_UNRESOLVED"
ADDRESS_CONFLICT = "ADDRESS_CONFLICT"
IDENTITY_REVIEW_REQUIRED = "IDENTITY_REVIEW_REQUIRED"
SAME_IDENTITY_REBRAND_SUCCESSOR = "SAME_IDENTITY_REBRAND_SUCCESSOR"

from scripts.pettripfinder.west_palm_beach_fl_nonhotel_rulings_001 import NOT_LODGING_WHY, LODGING_UNCONFIRMED, nonhotel_by_name  # noqa: E402
NOT_LODGING_NAMES = set(NOT_LODGING_WHY)
NON_HOTEL_LEAD_TYPES = {"Campground"}
#: The bureau's own Lodging sub-categories that are NOT hotel establishments.
NON_HOTEL_BUREAU_SUBCATEGORIES = {
    "Vacation Rentals", "Vacation Rental Companies", "Campgrounds", "RV Parks", "Real Estate", "Timeshares",
}
#: A bureau files a listing under several categories. The vacation-rental rule reads EVERY category the bureau
#: gives a listing: one that carries none of the bureau's hotel-type categories and carries "Vacation Rentals"
#: is not a hotel establishment on the bureau's own typing.
HOTEL_BUREAU_SUBCATEGORIES = {"Hotels & Motels", "Bed & Breakfasts", "Historic Inns", "Hotels & Resorts", "Hotels", "Resorts",
                              "Full Service Properties"}
_CAMPGROUND_NAME = re.compile(r"\b(rv|campground|camping|state park|kampground)\b", re.I)
STR_PLACEHOLDERS = set()

#: Government / institutional lodging refused by name. Empty at authoring time; the mechanism stays so a later
#: row is refused by decision, not by accident.
MILITARY_NONPUBLIC_NAMES = {}

#: A map row named like a private cottage or a rental is not a hotel identity.
_OSM_NOT_HOTEL = re.compile(r"\b(cottage|cottages|cabin|cabins|house|bed and breakfast|bed & breakfast|b&b|farm|vacations)\b", re.I)

_RENTAL_WORDS = re.compile(
    r"\b(airbnb|vrbo|apartment|apt\b|condo|cottage|bungalow|home w|house w|townhome|townhouse"
    r"|studio loft|guest ?house|cabin|retreat|rental|bnb|bed and breakfast)\b", re.I)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _route_key(url: str) -> str:
    return (url or "").split("?")[0].split("#")[0].rstrip("/").lower().replace("http://", "https://")


def phone_key(value: str) -> str:
    d = re.sub(r"\D", "", value or "")
    return d[-10:] if len(d) >= 10 else ""


def street_identity(street: str, postal: str) -> str:
    if not (street or "").strip():
        return ""
    return address_key(_merge_spelling((street or "").replace("'", "").replace("’", "")), postal or "")


#: Spellings the shared ``address_key`` keeps apart but that name one street ("N Dale Mabry Hwy" / "North
#: Dale Mabry Highway", "US Hwy 19" / "US Highway 19"). Used for the MERGE key only.
_SPELLING = (
    (re.compile(r"\btrail\b", re.I), "trl"), (re.compile(r"\bhighway\b", re.I), "hwy"),
    (re.compile(r"\bmem\b", re.I), "memorial"), (re.compile(r"\b(us|u\.s\.|sr|state road|state rd)\s+(hwy\s+)?(?=\d)", re.I), "hwy "),
    (re.compile(r"\bcircle\b", re.I), "cir"), (re.compile(r"\bcourt\b", re.I), "ct"), (re.compile(r"\blane\b", re.I), "ln"),
    (re.compile(r"\bplace\b", re.I), "pl"), (re.compile(r"\bboulevard\b", re.I), "blvd"), (re.compile(r"\bharbour\b", re.I), "harbor"),
    # PALM BEACH COUNTY: the grid is spelled both "NW 53 St" and "Northwest 53rd Street"; the shared key drops
    # bare digits but keeps "36th", so the ordinal suffix and the spelled-out quadrant are folded here.
    (re.compile(r"\bnorthwest\b", re.I), "nw"), (re.compile(r"\bnortheast\b", re.I), "ne"),
    (re.compile(r"\bsouthwest\b", re.I), "sw"), (re.compile(r"\bsoutheast\b", re.I), "se"),
    (re.compile(r"\b(terrace|terr)\b", re.I), "ter"),
    (re.compile(r"(?<=\s)(\d+)(?:st|nd|rd|th)?(?=\s+(?:st|street|ave|avenue|ct|court|ter|pl|place|rd|road|dr|drive|"
                r"way|ln|lane|blvd|pkwy|cir|circle)\b)", re.I), r"n\1"),
)


_QUADRANT = {"northwest": "NW", "northeast": "NE", "southwest": "SW", "southeast": "SE", "nw": "NW", "ne": "NE",
             "sw": "SW", "se": "SE", "n": "N", "s": "S", "e": "E", "w": "W", "north": "N", "south": "S",
             "east": "E", "west": "W"}
_GRID = re.compile(r"\b(northwest|northeast|southwest|southeast|nw|ne|sw|se|north|south|east|west|n|s|e|w)\.?\s+"
                   r"(\d+)(?:st|nd|rd|th)?(?=\s+(?:st|street|ave|avenue|ct|court|ter|terr|terrace|pl|place|rd|road|dr|"
                   r"drive|way|ln|lane|blvd|pkwy|cir)\b)", re.I)


#: A house number followed directly by a bare numbered street ("661 NW 53 St", the Boca Raton grid).
_BARE_NUMBERED = re.compile(r"^(\s*\d+[a-z]?\s+)(\d+)(?:st|nd|rd|th)?(?=\s+(?:st|street|ave|avenue|ct|court|ter|terr|"
                            r"terrace|pl|place|rd|road|dr|drive|way|ln|lane)\b)", re.I)


#: "N.W." / "N.W" / "N. W." / "S.E." are the same quadrant as NW / SE (proved in Miami, kept here): the
#: trailing dot is optional on real pages ("711 N.W 72nd Avenue"), and without this the same building entered the
#: census twice.
_DOTTED_QUADRANT = re.compile(r"\b([NnSs])\.\s*([EeWw])\.?(?=\s)", re.I)


def _ordinal(n):
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suffix)


#: An ampersand with no spaces around it ("B&B Hotel"). The two shared normalisers disagree on it --
#: ``site_data.normalize_name`` folds it away ("bandb"), ``ptf_identity_key`` expands it ("b and b") -- and the
#: shared registration CLI fails closed when a seed row's name and the census key disagree. The census therefore
#: states the name the way both read it the same, spelled out. Nothing else about the name changes.
_TIGHT_AMPERSAND = re.compile(r"(?<=[A-Za-z0-9])&(?=[A-Za-z0-9])")


def canonical_name(name):
    return _TIGHT_AMPERSAND.sub(" and ", name or "")


#: PALM BEACH COUNTY: "SR 7" (the Florida DBPR's spelling) and "State Road 7" / "US 441" (the brands')
#: are ONE street, as are SR 80 (Southern Blvd) and SR 809 (Military Trail). Folded to the state's own short
#: form BEFORE any key is built, or a brand page read never reaches the licence row it belongs to.
#: Proved necessary in Fort Lauderdale, where SR 84 / State Road 84 built two address keys for one building.
_STATE_ROAD = re.compile(r"\bs(?:tate)?[ .\-]*r(?:oa)?d?\.?[ .\-]*(\d+)\b", re.I)


def fold_state_road(street):
    """"State Road 84" / "State Rd 84" / "SR-84" / "S.R. 84" -> "SR 84". Reporting and keying only."""
    if not street:
        return street
    return _STATE_ROAD.sub(lambda m: "SR %s" % m.group(1), street)


#: PALM BEACH COUNTY: US-1 IS THIS COUNTY'S SPINE. Jupiter, Juno Beach, North Palm Beach, Lake Park, Riviera
#: Beach, Lantana, Delray Beach and Boca Raton all carry US-1 lodging addresses, and every source spells it
#: differently: the DBPR writes "757 N US HWY 1" and "810 US 1", the brands write "13801 U.S. Highway 1",
#: OSM writes "US-1". Folded to one spelling BEFORE any key is built.
#:
#: This is NOT already handled by the general spelling table, and the failure was measured rather than
#: assumed: ``_merge_spelling`` strips punctuation before that table runs, so "U.S. Highway 1" became
#: "U S  Highway 1", the "us" alternative no longer matched, and the trailing bare "S" was then eaten by the
#: directional strip -- leaving the merge key "U hwy 1" against the licence's "hwy 1". Two keys, one street.
#: It is the same class of defect as Fort Lauderdale's "SR 84" / "State Road 84" split, on this county's
#: busiest lodging road.
#: The leading word boundary matters: without it this pattern matches the "us" inside "Plus",
#: "Columbus" or "Citrus" and would rewrite an ordinary street into a highway. A separator is
#: required after the "US" for the same reason.
_US_HIGHWAY = re.compile(r"\bu\.?\s*s\.?[ .\-]+(?:hwy\.?|highway|route|rte\.?|rt\.?)?[ .\-]*(\d+)\b", re.I)


def fold_us_highway(street):
    """"U.S. Highway 1" / "US Hwy 1" / "US-1" / "U S Highway 1" -> "US 1". Reporting and keying only."""
    if not street:
        return street
    return _US_HIGHWAY.sub(lambda m: "US %s" % m.group(1), street)


def canonical_street(street):
    """PALM BEACH COUNTY: the census states a county grid street the way a property's own page writes it ("661 NW 53rd
    Ave"), whether the licence abbreviated it ("2601 Nw 42 Ave") or the map spelled it out ("2601 Northwest 42nd
    Avenue"): quadrant abbreviated and upper-cased, the numbered street given its ordinal. Nothing else changes.
    The shared identity gate keeps "42nd" and drops a bare "42", so an unordinalised licence spelling would refuse
    the property's own page for a spelling, not a building."""
    if not street:
        return street
    # "N.W." / "N. W." / "S.E." are the same quadrant as NW / SE; the dots only break the match below.
    street = fold_state_road(street)
    street = fold_us_highway(street)
    street = _DOTTED_QUADRANT.sub(lambda m: (m.group(1) + m.group(2)).upper(), street)
    s = _GRID.sub(lambda m: "%s %s" % (_QUADRANT[m.group(1).lower()], _ordinal(m.group(2))), street)
    return _BARE_NUMBERED.sub(lambda m: "%s%s" % (m.group(1), _ordinal(m.group(2))), s)


def _merge_spelling(street):
    # the dotted quadrant is folded BEFORE the merge key is built, or "711 N.W 72nd Avenue" and "711 NW 72nd Ave"
    # are two buildings to the shared key (proved in Miami, kept here)
    street = fold_us_highway(street or "")
    street = _DOTTED_QUADRANT.sub(lambda m: (m.group(1) + m.group(2)).upper(), street or "")
    s = re.sub(r"[^A-Za-z0-9 \-]", " ", street or "")
    s = re.sub(r"\bmemorial\s+h(w)?\s*$", "memorial hwy", s, flags=re.I)
    for rx, rep in _SPELLING:
        s = rx.sub(rep, s)
    s = re.sub(r"\b(n|s|e|w|north|south|east|west)\b", " ", s, flags=re.I) if re.match(r"\s*\d", s) else s
    return " ".join(s.split())


#: the shared ``address_key`` drops street directionals, so two hotels on opposite sides of a divided highway or
#: a numbered-street grid are not the same building. The MERGE refuses to join two streets whose own
#: directionals disagree.
_DIR_WORDS = {"e": "e", "east": "e", "w": "w", "west": "w", "n": "n", "north": "n", "s": "s", "south": "s"}


def street_directionals(street):
    toks = re.sub(r"[^a-z0-9 ]", " ", (street or "").lower()).split()
    return {_DIR_WORDS[x] for x in toks[1:] if x in _DIR_WORDS}


def directional_conflict(a, b):
    da, db = street_directionals(a), street_directionals(b)
    return bool(da) and bool(db) and da != db


class Node:
    """One proposed building identity and every observation attached to it."""

    __slots__ = ("name", "street", "city", "region", "postal", "phone", "brand",
                 "property_code", "route", "lat", "lng", "observations", "keys",
                 "ambiguous_matches", "rejections")

    def __init__(self):
        self.name = ""
        self.street = ""
        self.city = ""
        self.region = ""
        self.postal = ""
        self.phone = ""
        self.brand = ""
        self.property_code = ""
        self.route = ""
        self.lat = None
        self.lng = None
        self.observations = []
        self.keys = set()
        self.ambiguous_matches = []
        self.rejections = []

    def absorb(self, obs):
        self.observations.append(obs)
        # THE ADDRESS THE PROPERTY'S OWN PAGE STATES WINS. A tier-1 property-page observation OVERWRITES the
        # postal address; every other lane only fills a blank.
        first_party = str(obs.get("lane", "")).startswith("PROPERTY_PAGE")
        for field in ("street", "city", "region", "postal", "phone", "brand",
                      "property_code", "route"):
            if not getattr(self, field) and obs.get(field):
                setattr(self, field, obs[field])
            elif (first_party and obs.get(field)
                  and field in ("street", "city", "region", "postal")):
                setattr(self, field, obs[field])
        if obs.get("lat") is not None and self.lat is None:
            self.lat, self.lng = obs.get("lat"), obs.get("lng")
        # The longest name wins.
        if len(obs.get("name") or "") > len(self.name):
            self.name = obs["name"]


def _decode_entities(text):
    import html
    t = html.unescape(html.unescape(text or ""))
    t = t.replace("™", "").replace("®", "")
    import unicodedata
    t = "".join(ch for ch in unicodedata.normalize("NFKD", t) if not unicodedata.combining(ch))
    return t.replace(" ", " ").strip()


def observation(lane, tier, source_url, name, **kw):
    o = OrderedDict([("lane", lane), ("tier", tier), ("source_url", source_url),
                     ("name", _decode_entities(name))])
    for k, v in kw.items():
        if v not in (None, ""):
            o[k] = v
    return o


# --------------------------------------------------------------------------- #
# Lane readers.
# --------------------------------------------------------------------------- #

#: Map rows whose building the property's OWN site names differently today, joined to that read by its route.
MAP_ROWS_SUPERSEDED_BY_A_READ = {}


def read_osm():
    """OpenStreetMap lodging elements from the market-local extract lane, tier 3."""
    doc = _load(OSM_LANE, {}) or {}
    read_routes = {_route_key(r.get("requested_url") or "")
                   for r in (_load(ATTENDED_PASS, {}) or {}).get("rows", [])
                   if r.get("identity_confirmed")}
    out = []
    for e in doc.get("elements", []):
        t = e.get("tags") or {}
        name = (t.get("name") or "").split(";")[0].strip()
        if not name:
            continue
        street = " ".join(x for x in (t.get("addr:housenumber", ""), t.get("addr:street", "")) if x).strip()
        website = (t.get("website") or t.get("contact:website") or "").strip()
        superseded = MAP_ROWS_SUPERSEDED_BY_A_READ.get("%s/%s" % (e.get("type"), e.get("id")))
        if superseded:
            website = superseded[0]
        if website and _route_key(website) in read_routes:
            out.append(observation(
                "OSM_OVERPASS", 3, e.get("osm_url") or "https://www.openstreetmap.org/", name,
                city=(t.get("addr:city") or "").strip(),
                region=state_code((t.get("addr:state") or "").strip()),
                lat=e.get("lat"), lng=e.get("lng"),
                osm_element="%s/%s" % (e.get("type"), e.get("id")),
                osm_categories=[t.get("tourism")],
                website_url=website, route=website, joins_read_route=True,
                map_street_superseded="%s %s" % (street, (t.get("addr:postcode") or "").strip()),
                map_label_superseded=superseded[1] if superseded else None,
                non_hotel_name=bool(_OSM_NOT_HOTEL.search(name)),
            ))
            continue
        out.append(observation(
            "OSM_OVERPASS", 3, e.get("osm_url") or "https://www.openstreetmap.org/", name,
            street=street, city=(t.get("addr:city") or "").strip(),
            region=state_code((t.get("addr:state") or "").strip()),
            postal=(t.get("addr:postcode") or "").strip()[:5],
            phone=(t.get("phone") or t.get("contact:phone") or "").strip(),
            lat=e.get("lat"), lng=e.get("lng"),
            osm_element="%s/%s" % (e.get("type"), e.get("id")),
            osm_categories=[t.get("tourism")],
            website_url=(t.get("website") or t.get("contact:website") or "").strip(),
            non_hotel_name=bool(_OSM_NOT_HOTEL.search(name)),
        ))
    return out


_MARRIOTT = re.compile(r"marriott\.com/en-us/hotels/([a-z0-9]{5,7})-([a-z0-9-]+)/overview", re.I)
_WYNDHAM = re.compile(
    r"wyndhamhotels\.com/([a-z0-9-]+)/([a-z-]+)-florida/([a-z0-9-]+)/overview",
    re.I)


def _titlecase(slug):
    return " ".join(w.capitalize() for w in (slug or "").replace("-", " ").split())


_STATE_CODE = {
    "alabama": "AL", "arkansas": "AR", "arizona": "AZ", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL",
    "georgia": "GA", "iowa": "IA", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "massachusetts": "MA", "maryland": "MD", "maine": "ME", "michigan": "MI",
    "minnesota": "MN", "missouri": "MO", "mississippi": "MS", "montana": "MT",
    "north carolina": "NC", "north dakota": "ND", "nebraska": "NE",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "nevada": "NV", "new york": "NY", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "virginia": "VA", "vermont": "VT",
    "washington": "WA", "wisconsin": "WI", "west virginia": "WV",
    "wyoming": "WY", "district of columbia": "DC",
}


def state_code(value):
    """The two-letter code for a state a first-party page named, or ""."""
    v = (value or "").strip()
    if not v:
        return ""
    if len(v) == 2 and v.isalpha():
        return v.upper()
    return _STATE_CODE.get(v.lower(), "")


def _brand_doc():
    return _load(BRAND, {}) or {}


def read_brand_owned():
    """Rung 0. The committed national brand harvest, read at zero requests."""
    out = []
    for r in _brand_doc().get("leads", []):
        if r.get("lane") != "BRAND_INVENTORY_OWNED":
            continue
        url, fam = r["route"], r["family"]
        name, code = "", (r.get("property_code") or "")
        m = _MARRIOTT.search(url)
        if m:
            code, name = m.group(1).lower(), _titlecase(m.group(2))
        else:
            w = _WYNDHAM.search(url)
            name = _titlecase(w.group(3)) if w else _name_from_route(url)
        if not name:
            continue
        out.append(observation(
            "BRAND_INVENTORY_OWNED", 1, url, name,
            brand=fam, property_code=code, route=url, merge_alias=normalize_name(name),
            admitted_by="ROUTE_READ_FROM_A_COMMITTED_NATIONAL_BRAND_INVENTORY",
            seen_in=r.get("owned_source", ""),
        ))
    return out


_SLUG_NOISE = {"hotels", "hotel", "overview", "index", "en", "us", "fl", "florida"}


def _name_from_route(url):
    """A proposed NAME from a brand's own property route slug."""
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    if tail in ("overview", "hoteldetail", "index.html"):
        parts = url.rstrip("/").split("/")
        tail = parts[-2] if len(parts) > 1 else tail
    tail = re.sub(r"[.](html?|aspx)$", "", tail)
    words = [w for w in tail.replace("_", "-").split("-")
             if w and w.lower() not in _SLUG_NOISE and not w.isdigit()]
    if words and re.fullmatch(r"[a-z0-9]{6,8}", words[0].lower()) and any(
            ch.isdigit() for ch in words[0]):
        words = words[1:]
    return _titlecase("-".join(words))


def read_brand_city_pages():
    """Hilton's coded roster, read from the brand's OWN Florida city pages and their in-market interlinks."""
    out = []
    for r in _brand_doc().get("leads", []):
        if r.get("lane") != "BRAND_CITY_PAGE":
            continue
        card = r.get("brand_card") or {}
        # PALM BEACH COUNTY: a card must state Florida AND a South Florida / Treasure Coast postal prefix
        # (334 Palm Beach, 330/333 Broward and 331/332 Miami-Dade for the boundary audit, 349 Martin /
        # St. Lucie for the northern line) to be a lead of this box at all. Prefix 334 is the market; every
        # other prefix here exists so the county boundary audit sees the neighbour instead of being blind.
        if state_code(card.get("state")) != "FL":
            continue
        if (card.get("postal_code") or "")[:3] not in (
                "334", "330", "331", "332", "333", "349"):
            continue
        name = card.get("name") or _name_from_route(r["route"])
        if not name:
            continue
        out.append(observation(
            "BRAND_INVENTORY_CITY_PAGE", 1, r["route"], name,
            brand=r["family"], property_code=r.get("property_code", ""),
            route=r["route"], merge_alias=normalize_name(_name_from_route(r["route"])),
            street=card.get("street"), city=card.get("city"), region=state_code(card.get("state")),
            postal=(card.get("postal_code") or "")[:5], phone=card.get("phone"),
            lat=card.get("lat"), lng=card.get("lng"),
            admitted_by="ADDRESS_FROM_THE_BRAND_OWN_CITY_PAGE_PROPERTY_CARD" if card else
                        "ROUTE_READ_FROM_THE_BRAND_OWN_CITY_PAGE",
            seen_in=r.get("found_in", ""),
            document_sha256=r.get("found_in_sha256"),
        ))
    return out


def read_brand_state_sitemap():
    """Marriott's own Florida hotel sitemap page: MARSHA code, title and route."""
    out = []
    for r in _brand_doc().get("leads", []):
        if r.get("lane") != "BRAND_STATE_SITEMAP_PAGE":
            continue
        if not ((r.get("property_code") or "").lower().startswith("mia") or places_in(r.get("brand_title") or "")):
            continue
        name = r.get("brand_title") or _name_from_route(r["route"])
        out.append(observation(
            "BRAND_INVENTORY_STATE_SITEMAP", 1, r["route"], name,
            brand=r["family"], property_code=(r.get("property_code") or "").lower(),
            route=r["route"], merge_alias=normalize_name(name),
            admitted_by="ROUTE_READ_FROM_THE_BRAND_OWN_STATE_HOTEL_SITEMAP",
            seen_in=r.get("found_in", ""), document_sha256=r.get("found_in_sha256"),
        ))
    return out


_PROPERTY_ROUTE = re.compile(
    r"wyndhamhotels\.com/(?![a-z]{2}-[a-z]{2}/)[a-z0-9-]+/[a-z-]+-florida/[a-z0-9-]+/overview$",
    re.I)

_OTHER_PROPERTY_ROUTE = re.compile(
    r"(druryhotels\.com/locations/[a-z-]+-fl/[a-z0-9-]+$"
    r"|loewshotels\.com/(?!.*sitemap)[a-z0-9-]+$"
    r"|sonesta\.com/[a-z0-9-]+/fl/[a-z-]+/[a-z0-9-]+$"
    r"|woodspring\.com/extended-stay-hotels/locations/florida/[a-z-]+/(?!hotels$)[a-z0-9-]+$"
    r"|bestwestern\.com/en_us/book/[a-z-]+/hotel-rooms/[a-z0-9-]+/propertycode\.\d+\.html$"
    r"|choicehotels\.com/florida/[a-z-]+/[a-z-]+-hotels/fl[a-z0-9]{3,4}$)", re.I)


def read_brand_sitemaps():
    """Property routes read from a brand's OWN sitemap -- tier 1 routing evidence."""
    out = []
    attended = _load(ATTENDED_PASS, {}) or {}
    retired = {p if p.startswith("http") else "https://www.wyndhamhotels.com" + p
               for p in attended.get("wyndham_retired_routes", [])}
    seen_routes = set()
    _disc = (_load(os.path.join(REPORTS, "west_palm_beach_fl_firecrawl_discovery_001.json"), {}) or {}).get("routes", [])
    for r in list(_brand_doc().get("leads", [])) + list(_disc):
        if r.get("lane") != "BRAND_SITEMAP":
            continue
        route = r["route"].split("?")[0].split("#")[0]
        if route in seen_routes:
            continue
        seen_routes.add(route)
        if route in retired or not (_PROPERTY_ROUTE.search(route) or _OTHER_PROPERTY_ROUTE.search(route)):
            continue
        r = dict(r, route=route)
        _city = _WYNDHAM_URL_CITY.search(route)
        if _city and _city.group(1).replace("-", " ") not in _ALL_PLACES:
            continue
        _bw = re.search(r"/hotel-rooms/([a-z0-9-]+)/propertycode\.(\d+)\.html$", route, re.I)
        _ch = re.search(r"choicehotels\.com/florida/([a-z-]+)/([a-z-]+)-hotels/(fl[a-z0-9]{3,4})$", route, re.I)
        if _ch:
            name = "%s %s" % (_titlecase(_ch.group(2)), _titlecase(_ch.group(1)))
        else:
            name = _titlecase(_bw.group(1)) if _bw else _name_from_route(r["route"])
        if not name:
            continue
        out.append(observation(
            "BRAND_INVENTORY_SITEMAP", 1, r["route"], name,
            brand=r["family"], route=r["route"], merge_alias=normalize_name(name),
            property_code=(_bw.group(2) if _bw else _ch.group(3).lower() if _ch else ""),
            admitted_by="ROUTE_READ_FROM_THE_BRAND_OWN_SITEMAP",
            seen_in=r.get("found_in", ""),
            document_sha256=r.get("found_in_sha256"),
        ))
    return out


def read_property_pages():
    """The address a property's OWN page states -- tier 1, and the only thing allowed to turn a brand-roster
    or map row into a Palm Beach County identity."""
    doc = _load(ATTENDED_PASS, {}) or {}
    out = []
    for r in doc.get("rows", []):
        if not r.get("identity_confirmed"):
            continue
        sig = r.get("identity_signals") or {}
        street = (sig.get("address_on_page") or "").strip()
        if not street:
            continue
        lane = "PROPERTY_PAGE_STATIC" if r.get("lane") == "DIRECT_STATIC_FETCH" else "PROPERTY_PAGE_ATTENDED"
        brand = r.get("brand")
        if brand == "INDEPENDENT":
            brand = ""
        out.append(observation(
            lane, 1, r.get("final_url") or r.get("requested_url"),
            (sig.get("name_on_page") or "").strip(),
            street=street, postal=(sig.get("postal_code") or "").strip()[:5],
            city=(sig.get("locality") or "").strip(),
            region=state_code(sig.get("region")),
            phone=(sig.get("phone_on_page") or "").strip(),
            property_code=(sig.get("property_code_on_page") or "").strip(),
            brand=brand, route=r.get("requested_url"),
            document_sha256=r.get("document_sha256"),
            document_bytes=r.get("document_bytes"),
            binding_method=r.get("identity_binding_method"),
            lat=sig.get("lat"), lng=sig.get("lng"),
        ))
    return out


from scripts.pettripfinder.west_palm_beach_fl_static_rulings_001 import (  # noqa: E402
    IDENTITY_ONLY_PAGES, COMPETITOR_LEADS, REGIONAL_VISITOR_CENTER_LEADS, REGIONAL_VISITOR_CENTER_SOURCE)


def read_identity_only_pages():
    out = []
    for name, street, city, postal, phone, url, _sha, note in IDENTITY_ONLY_PAGES:
        out.append(observation(
            "PROPERTY_PAGE_IDENTITY_ONLY", 1, url, name, street=street, city=city, region="FL",
            postal=postal, phone=phone, route=url, binding_method="ADDRESS_ON_THE_PROPERTYS_OWN_SITE",
            identity_note=note))
    return out


#: One building, two trade names, and NO first-party page read to say which is current. A founder / later-order
#: ruling. Empty at authoring time.
REBRAND_HOLDS = {}

#: A DUAL-BRAND building is TWO hotels (standing rule). A licence or listing that names both hotels as one row is
#: never published as one identity: each hotel needs its own exact-premises identity (its own brand property code
#: and its own page) before either can carry a policy. Held for the split, never merged, never guessed.
DUAL_BRAND_COMBINED = [
    # PALM BEACH COUNTY: empty at authoring time; the rule stays armed and is re-asserted by the partition
    # contract. A dual-brand building is TWO hotels and is HELD for the split, never published as one
    # (standing rule, proved on AC/Element Miami Brickell and Eden Roc/Nobu Miami Beach in the Miami build,
    # and on Tru/Home2 Fort Lauderdale Downtown and Home2/Tru Pompano Beach in the Fort Lauderdale build).
]

#: A second row naming ONE building of an establishment that another census row already carries under the licence
#: that covers the whole premises. Keyed on the normalised name; each read from the evidence before it was added.
#: A row is added only after THIS market's own evidence proves the duplicate.
DUPLICATE_OF = {
    # PALM BEACH COUNTY: empty at authoring time. A row is added ONLY after THIS market's own evidence proves
    # the duplicate -- a first-party read of the brand's own page for the property code, joined to the DBPR
    # licence that covers the whole premises. Never inherited from another market and never guessed.
}


def read_destination_roster():
    """Discover The Palm Beaches' roster: a NAME-ONLY lane, tier 3.

    Unlike Visit Lauderdale's Simpleview listings service (which handed Fort Lauderdale 376 listings with 360
    websites), this bureau publishes NO street, postal code, telephone or outbound website on any document the
    roster lane can read -- it renders all four client-side from a Simpleview CRM this order has no
    authorization to call. The measurement is recorded in west_palm_beach_fl_destination_roster_001.json.

    So every roster observation here carries a NAME and the bureau's own listing URL and nothing else. A name
    proposes an identity and never decides one: these rows can only ever ATTACH to a building another lane
    already established (the licensed premises, a brand's own inventory, a map row or a first-party read), and
    one that attaches to nothing stays NAME_ONLY_UNRESOLVED and is counted as a gap-challenge lead. No bureau
    amenity chip -- including its "Pet-Friendly" tag -- is read, stored or published.
    """
    doc = _load(DESTINATION, {}) or {}
    out = []
    for r in (doc.get("leads") or []):
        name = (r.get("name") or "").strip()
        if not name:
            continue
        out.append(observation(
            "DESTINATION_ORGANIZATION", 3, r["listing_url"], name,
            bureau_slug=r.get("slug"),
        ))
    return out


def merge_destination_rows(nodes):
    """A roster row with a street and no trusted ZIP joins the ONE building that states the same house number
    and either the same ZIP-free street identity or shared chain vocabulary. Never on a name alone, never on
    the roster's ZIP."""
    merged, absorbed = [], set()
    targets = [n for n in nodes if n.street and n.postal]
    for n in nodes:
        if not n.street or n.postal:
            continue
        if not all(o.get("lane") == "DESTINATION_ORGANIZATION" for o in n.observations):
            continue
        num = (n.street.split() or [""])[0]
        key = address_key(n.street, "")
        hits = [h for h in targets if (h.street.split() or [""])[0] == num
                and (address_key(h.street, "") == key
                     or any(chain_tokens(o.get("name") or "") & chain_tokens(n.name)
                            for o in h.observations))]
        if len(hits) != 1:
            continue
        h = hits[0]
        for o in n.observations:
            o = OrderedDict(o)
            o["binding"] = "DESTINATION_ROSTER_SAME_HOUSE_NUMBER_AND_STREET_OR_CHAIN"
            h.observations.append(o)
        absorbed.add(id(n))
        merged.append(OrderedDict([("absorbed", n.name), ("absorbed_street", n.street),
                                   ("into", h.name), ("street", h.street), ("postal_code", h.postal)]))
    return [n for n in nodes if id(n) not in absorbed], merged


def read_regional_visitor_center():
    return [observation("REGIONAL_VISITOR_CENTER", 2, REGIONAL_VISITOR_CENTER_SOURCE, name,
                        merge_alias=normalize_name(name),
                        lead_source="regional visitor center lodging roster (names only)")
            for name in REGIONAL_VISITOR_CENTER_LEADS]


PLACES_REPORT = os.path.join(REPORTS, "west_palm_beach_fl_places_route_discovery_001.json")
#: Place types that are a hotel establishment (a hostel is NON_LODGING under the geography's rule).
_PLACES_HOTEL_TYPES = {"hotel", "motel", "resort_hotel", "extended_stay_hotel", "inn", "bed_and_breakfast"}


def read_gap_verified():
    """PHASE 10 closure: a BringFido TRUE_MISSING lead that Google Places (existing key) verified as an OPERATIONAL
    hotel establishment with its own street number at an ADMITTED postal code, carried by no census node (house
    number + ZIP or phone). The Places card is identity evidence (tier 3), never policy; the competitor name only
    selected the query. A lead with no street number, or typed only as a hostel / generic lodging, is not admitted."""
    doc = _load(PLACES_REPORT, {}) or {}
    out = []
    for r in doc.get("rows", []):
        if r.get("cohort") != "GAP_VERIFICATION" or r.get("verdict") != "VERIFIED_MISSING_AT_ADMITTED_POSTAL_CODE":
            continue
        p = r.get("place") or {}
        if not p.get("street_number") or not (set(p.get("types") or []) & _PLACES_HOTEL_TYPES):
            continue
        out.append(observation(
            "IDENTITY_VERIFIED_PLACES", 3, "https://www.google.com/maps/place/?q=place_id:%s" % p["google_place_id"],
            p["display_name"], street="%s %s" % (p["street_number"], p.get("route", "")), city=p.get("locality"),
            region="FL", postal=p.get("postal_code"), phone=p.get("phone"), website_url=p.get("website_uri"),
            lat=p.get("lat"), lng=p.get("lng"), google_place_id=p["google_place_id"],
            selected_by_competitor_lead=r.get("bringfido_name"),
            admitted_by="PLACES_OPERATIONAL_HOTEL_AT_ADMITTED_POSTAL_CODE_NOT_IN_CENSUS"))
    return out


def read_competitor():
    """BringFido leads: names only, tier 4, never policy."""
    return [observation("COMPETITOR_LEAD", 4, src, name, merge_alias=normalize_name(name),
                        lead_source="BringFido city pages (discovery only)")
            for name, src in COMPETITOR_LEADS]


_SMALL_WORDS = {"and", "at", "by", "of", "the", "on", "in", "near"}


def _registry_title(text):
    """A licence's ALL-CAPS business name in ordinary capitalisation. Typography only: the identity key folds case."""
    words = []
    for i, w in enumerate((text or "").split()):
        lw = w.lower()
        if i and lw in _SMALL_WORDS:
            words.append(lw)
        elif re.fullmatch(r"[a-z]{1,2}\d*|i+", lw) and lw in ("ac", "jw", "ii", "iii", "iv", "es", "fc", "mia", "sls", "w"):
            words.append(w.upper())
        else:
            words.append("-".join(p[:1].upper() + p[1:].lower() for p in w.split("-")))
    return " ".join(words)


def read_dbpr():
    """PALM BEACH COUNTY: the Florida DBPR public-lodging licence registry -- tier 2 identity and eligibility evidence."""
    doc = _load(DBPR_LANE, {}) or {}
    out = []
    groups = OrderedDict()
    for r in doc.get("leads", []):
        base = re.sub(r"\s*-?\s*\b(building|bldg)\s*\d+\s*$", "", (r.get("business_name") or "").strip(), flags=re.I)
        if base != (r.get("business_name") or "").strip():
            groups.setdefault((base.upper(), (r.get("licensee_name") or "").upper()), []).append(r)
    folded_buildings = {}
    for (base, _lic), rows in groups.items():
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda x: (x.get("business_name") or ""))
        for other in rows[1:]:
            folded_buildings[other.get("license_number")] = rows[0].get("license_number")
    extra = {}
    for r in doc.get("leads", []):
        if r.get("license_number") in folded_buildings:
            extra.setdefault(folded_buildings[r["license_number"]], []).append(
                OrderedDict([("license_number", r.get("license_number")), ("business_name", r.get("business_name")),
                             ("street", r.get("street")), ("rental_units", r.get("rental_units"))]))
    for r in doc.get("leads", []):
        if r.get("license_number") in folded_buildings:
            continue
        name = _registry_title(r.get("business_name") or r.get("name") or "")
        if not name:
            continue
        if r.get("license_number") in extra:
            name = re.sub(r"\s*-?\s*\b(Building|Bldg)\s*\d+\s*$", "", name)
        out.append(observation(
            "REGISTRY_FL_DBPR", 2, r.get("raw_pointer") or "https://www2.myfloridalicense.com/", name,
            street=_registry_title(r.get("street") or ""), city=_registry_title(r.get("city") or ""),
            region="FL", postal=(r.get("postal_code") or "")[:5], phone=r.get("phone") or "",
            license_number=r.get("license_number"), rank_code=r.get("rank_code"),
            rental_units=r.get("rental_units"), county=r.get("county"),
            licensee_name=r.get("licensee_name"), snapshot_sha256=r.get("snapshot_sha256"),
            additional_licensed_buildings=extra.get(r.get("license_number")),
        ))
    return out


# --------------------------------------------------------------------------- #
# The graph.
# --------------------------------------------------------------------------- #

_FOLDED = object()


def merge(observations):
    """One node per building. Keyed on street identity, phone or property code."""
    nodes = []
    by_key = {}
    conflicts = []
    for obs in observations:
        sid = street_identity(obs.get("street", ""), obs.get("postal", ""))
        pk = phone_key(obs.get("phone", ""))
        code = (obs.get("property_code") or "").lower()
        brand = (obs.get("brand") or "").upper()
        cand_keys = []
        alias = obs.get("merge_alias") or ""
        if alias:
            cand_keys.append("alias:" + alias)
        if sid:
            cand_keys.append("street:" + sid)
        if pk and obs.get("lane") not in ("OSM_OVERPASS", "REGISTRY_FL_DBPR"):
            cand_keys.append("phone:" + pk)
        if code and brand:
            cand_keys.append("code:%s:%s" % (brand, code))
        _route = _route_key(obs.get("route") or "")
        if _route and (re.search(r"(wyndhamhotels|hilton|marriott|ihg|redroof|extendedstayamerica|hyatt|choicehotels|bestwestern|woodspring|druryhotels|sonesta|motel6)\.com/", _route)
                       or str(obs.get("lane", "")).startswith("PROPERTY_PAGE")
                       or obs.get("joins_read_route")):
            cand_keys.append("route:" + _route)
        # CO-LOCATED DISTINCT HOTELS. A dual-brand building is TWO hotels.
        if sid and ("street:" + sid) in by_key and directional_conflict(
                nodes[by_key["street:" + sid]].street if nodes[by_key["street:" + sid]] is not _FOLDED else "",
                obs.get("street", "")):
            cand_keys = [k for k in cand_keys if not k.startswith("street:")]
        if code and brand and ("street:" + sid) in by_key:
            other = nodes[by_key["street:" + sid]]
            if (other.property_code and other.brand
                    and other.brand.upper() == brand
                    and other.property_code.lower() != code):
                cand_keys = [k for k in cand_keys if not k.startswith("street:")]

        hits = {by_key[k] for k in cand_keys if k in by_key}
        if len(hits) > 1:
            code_key = "code:%s:%s" % (brand, code) if (code and brand) else ""
            preferred = by_key.get(code_key) if code_key else None
            if preferred is None and sid and ("street:" + sid) in by_key \
                    and by_key["street:" + sid] in hits:
                preferred = by_key["street:" + sid]
            conflicts.append(OrderedDict([
                ("observation", obs),
                ("claimed_by", sorted({nodes[i].name for i in hits if nodes[i] is not _FOLDED})),
                ("resolved_by", "BRAND_PROPERTY_CODE" if preferred is not None
                                else "LOWEST_ESTABLISHED_NODE"),
                ("why", "the observation's street identity, phone or property code matches more "
                        "than one already-established node"),
            ]))
            keep = preferred if preferred is not None else min(hits)
            node = nodes[keep]
            for other_idx in sorted(hits - {keep}):
                other = nodes[other_idx]
                if other is None or other is node:
                    continue
                if (other.property_code and node.property_code
                        and other.property_code.lower() != node.property_code.lower()):
                    continue
                if (other.street and node.street
                        and not (chain_tokens(other.name) & chain_tokens(node.name))
                        and street_identity(other.street, other.postal)
                        and street_identity(node.street, node.postal)
                        and street_identity(other.street, other.postal)
                        != street_identity(node.street, node.postal)):
                    continue
                for o in other.observations:
                    node.absorb(o)
                for k in other.keys:
                    by_key[k] = keep
                    node.keys.add(k)
                nodes[other_idx] = _FOLDED
        elif hits:
            node = nodes[hits.pop()]
        else:
            node = Node()
            nodes.append(node)
        idx = nodes.index(node)
        if node.street and obs.get("street"):
            a = street_identity(node.street, node.postal)
            b = street_identity(obs["street"], obs.get("postal", ""))
            phone_ok = bool(chain_tokens(node.name) & chain_tokens(obs.get("name") or ""))
            if a and b and (a != b or directional_conflict(node.street, obs["street"])) and not any(
                    (k.startswith("alias:") or (phone_ok and k.startswith("phone:")))
                    and k in by_key for k in cand_keys):
                node = Node()
                nodes.append(node)
                idx = len(nodes) - 1
        node.absorb(obs)
        for k in cand_keys:
            by_key.setdefault(k, idx)
            node.keys.add(k)
    return [n for n in nodes if n is not _FOLDED], conflicts


# --------------------------------------------------------------------------- #
# Name attachment. A name PROPOSES; it never decides.
# --------------------------------------------------------------------------- #
_GENERIC_TOKENS = {
    "hotel", "hotels", "inn", "inns", "suites", "suite", "and", "by", "the", "of", "at",
    "a", "an", "motel", "lodge", "lodging", "resort", "conference", "center", "centre",
    "extended", "stay", "america", "select", "s",
    "marriott", "hilton", "wyndham", "hyatt", "ihg", "choice", "radisson",
    "intercontinental", "sonesta", "g6", "curio", "collection", "tapestry",
    "autograph", "tribute", "portfolio", "trademark", "ascend", "bonvoy",
    "fl", "florida", "bed", "breakfast", "b",
    "spa", "luxury", "rooftop", "lounge", "member", "design", "boutique", "club", "golf", "i",
}
#: Municipalities inside this market. A name that STATES one of these is making a claim about which town the
#: building is in. SEVEN of them carry "Palm" in the name, which is exactly why a name never places a property.
_IN_MARKET_MUNICIPALITIES = {
    "west palm beach", "w palm beach", "wpb", "downtown west palm beach", "clematis", "rosemary square",
    "palm beach", "town of palm beach", "worth avenue", "palm beach gardens", "north palm beach",
    "royal palm beach", "palm beach shores", "singer island", "riviera beach", "lake park", "mangonia park",
    "juno beach", "jupiter", "jupiter farms", "abacoa", "tequesta", "lake worth", "lake worth beach",
    "lantana", "manalapan", "hypoluxo", "boynton beach", "ocean ridge", "delray beach", "boca raton",
    "highland beach", "wellington", "greenacres", "palm springs", "lake clarke shores", "haverhill",
    "loxahatchee", "the acreage", "westlake", "belle glade", "pahokee", "south bay", "canal point",
    "atlantis", "glen ridge", "briny breezes", "gulf stream", "south palm beach", "cloud lake",
}
#: Refused places: the TWO EXISTING LIVE markets' own municipalities (Broward -> fort-lauderdale-fl,
#: Miami-Dade -> miami-fl) and the named future standalones (Martin / St. Lucie, the Keys).
_FUTURE_SUBMARKET_PLACES = {"fort lauderdale", "ft lauderdale", "lauderdale", "las olas", "hollywood",
                            "hollywood beach", "hallandale beach", "hallandale", "dania beach", "dania",
                            "pompano beach", "pompano", "deerfield beach", "lighthouse point",
                            "hillsboro beach", "lauderdale by the sea", "sea ranch lakes", "wilton manors",
                            "oakland park", "lauderdale lakes", "lauderhill", "tamarac", "north lauderdale",
                            "plantation", "davie", "cooper city", "southwest ranches", "sunrise", "weston",
                            "pembroke pines", "miramar", "west park", "coral springs", "coconut creek",
                            "margate", "parkland", "port everglades",
                            "miami", "miami beach", "south beach", "brickell", "downtown miami", "doral",
                            "coral gables", "coconut grove", "key biscayne", "aventura", "sunny isles",
                            "sunny isles beach", "bal harbour", "surfside", "north miami", "north miami beach",
                            "hialeah", "miami lakes", "homestead", "miami gardens", "miami shores",
                            "stuart", "hobe sound", "jensen beach", "palm city", "indiantown", "jupiter island",
                            "port st lucie", "port saint lucie", "fort pierce", "vero beach",
                            "key largo", "islamorada", "marathon", "key west"}
_OUT_OF_MARKET_PLACES = set(_FUTURE_SUBMARKET_PLACES)
_ALL_PLACES = _IN_MARKET_MUNICIPALITIES | _OUT_OF_MARKET_PLACES
#: Place words that are ALSO chain or naming vocabulary: a place phrase still names the town, but its words are
#: never stripped from a name's chain vocabulary.
_PLACE_WORDS_KEPT_IN_CHAIN = {"garden", "gardens", "park", "springs", "harbor", "beach", "lakes", "shores",
                              "palm", "palms", "worth", "ridge", "point", "island"}
_DIRECTIONALS = {
    "north", "south", "east", "west", "northwest", "northeast", "southwest", "southeast",
    "village", "bypass", "area", "near", "blvd", "road", "rd", "center", "downtown",
    # PALM BEACH COUNTY area words that tell same-brand hotels apart (Courtyard Downtown / Airport /
    # Jupiter / Wellington / Boca Raton / Delray Beach / PGA / Singer Island)
    "airport", "beach", "oceanfront", "waterfront", "intracoastal", "marina", "harbor", "harbour", "pier",
    "causeway", "convention", "mall", "stadium", "arena", "university", "medical", "hospital", "corporate",
    "executive", "turnpike", "outlets", "equestrian", "polo", "golf", "pga", "resort", "spa", "island",
    "worth", "olive", "clematis", "rosemary", "okeechobee", "belvedere", "congress", "glades", "military",
    "jupiter", "tequesta", "juno", "lantana", "boynton", "delray", "boca", "raton", "wellington",
    "greenacres", "riviera", "singer", "gardens", "highland", "manalapan", "hypoluxo", "loxahatchee",
    "westlake", "atlantic", "mizner", "abacoa", "metrocentre", "northwood",
}
_NAME_MATCH_THRESHOLD = 0.75


def places_in(text: str):
    n = normalize_name(text)
    padded = " %s " % n
    return {p for p in _ALL_PLACES if (" %s " % p) in padded}


def directionals_in(text: str):
    return {t for t in normalize_name(text).split() if t in _DIRECTIONALS}


def chain_tokens(name: str):
    toks = [t for t in normalize_name(name).split() if t and not t.isdigit()]
    return {t for t in toks
            if t not in _GENERIC_TOKENS and t not in _DIRECTIONALS
            and t not in {w for p in _ALL_PLACES for w in p.split()} - _PLACE_WORDS_KEPT_IN_CHAIN}


def node_place_vocabulary(node, corridor_municipality=""):
    blob = " ".join(x for x in (node.city, node.name, corridor_municipality) if x)
    return places_in(blob), directionals_in(blob)


def specific_municipality(places):
    return set(places)


def attachment_verdict(soft_name, node, corridor_municipality=""):
    soft_places = places_in(soft_name)
    soft_dirs = directionals_in(soft_name)
    hard_places, hard_dirs = node_place_vocabulary(node, corridor_municipality)

    soft_muni = specific_municipality(soft_places)
    hard_muni = specific_municipality(hard_places)
    if soft_muni and hard_muni and not (soft_muni & hard_muni):
        return 0.0, ("the name states %s and the building's own city is %s"
                     % (sorted(soft_muni), sorted(hard_muni)))
    if soft_places and not hard_places and (soft_places & _OUT_OF_MARKET_PLACES):
        return 0.0, ("the name states %s, which is outside this market, and the building's own "
                     "evidence names no town to corroborate it" % sorted(soft_places))
    if soft_dirs and hard_dirs and not (soft_dirs & hard_dirs):
        return 0.0, ("the name states the area %s and the building's own evidence states %s"
                     % (sorted(soft_dirs), sorted(hard_dirs)))
    if soft_dirs and not hard_dirs and not (soft_places & hard_places):
        return 0.0, ("the name states the area %s and the building's own evidence states no area "
                     "and no town in common, so there is nothing to corroborate against"
                     % sorted(soft_dirs))

    sc, hc = chain_tokens(soft_name), chain_tokens(node.name)
    if not sc or not hc:
        return 0.0, "one name carries no distinguishing brand vocabulary"
    chain = len(sc & hc) / float(len(sc | hc))
    if chain < _NAME_MATCH_THRESHOLD:
        return 0.0, "brand vocabulary overlap %.2f is below the %.2f bar" % (
            chain, _NAME_MATCH_THRESHOLD)
    place_bonus = 1.0 if (soft_places & hard_places) else (0.5 if not soft_places else 0.0)
    dir_bonus = 1.0 if (soft_dirs & hard_dirs) else (0.5 if not soft_dirs else 0.0)
    score = round(0.6 * chain + 0.2 * place_bonus + 0.2 * dir_bonus, 4)
    return score, ("brand %.2f, town %s, area %s"
                   % (chain,
                      sorted(soft_places & hard_places) or ("not stated" if not soft_places
                                                            else "unconfirmed"),
                      sorted(soft_dirs & hard_dirs) or ("not stated" if not soft_dirs
                                                        else "unconfirmed")))


def _km(lat1, lng1, lat2, lng2):
    import math
    dy = (lat1 - lat2) * 111.0
    dx = (lng1 - lng2) * 111.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.hypot(dx, dy)


def attach_name_only(nodes, node_corridor_municipality=None):
    """Bind a name-only observation to at most ONE established building."""
    node_corridor_municipality = node_corridor_municipality or {}
    hard = [n for n in nodes if n.street or n.phone]
    soft = [n for n in nodes if not (n.street or n.phone)]
    bound, ambiguous, unbound = [], [], []
    for s in soft:
        scored, rejections = [], []
        exact = [h for h in hard if normalize_name(h.name.replace("'", "").replace("’", ""))
                 == normalize_name(s.name.replace("'", "").replace("’", ""))
                 and not (s.lat is not None and h.lat is not None
                          and _km(s.lat, s.lng, h.lat, h.lng) > 5.0)]
        if len(exact) == 1:
            scored.append((1.0, "exact normalised name, one addressed building", exact[0]))
            hard_iter = []
        else:
            hard_iter = hard
        for h in hard_iter:
            if s.lat is not None and h.lat is not None and _km(s.lat, s.lng, h.lat, h.lng) > 5.0:
                continue
            score, why = attachment_verdict(s.name, h,
                                            node_corridor_municipality.get(id(h), ""))
            if score > 0:
                scored.append((score, why, h))
            elif chain_tokens(s.name) & chain_tokens(h.name):
                rejections.append(OrderedDict([("candidate", h.name), ("why", why)]))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            s.rejections = rejections[:6]
            unbound.append(s)
            continue
        if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.05:
            s.ambiguous_matches = [h.name for _, _, h in scored[:4]]
            ambiguous.append(s)
            continue
        score, why, h = scored[0]
        for obs in s.observations:
            o = OrderedDict(obs)
            o["binding"] = "NAME_MATCH_UNCONFIRMED"
            o["binding_score"] = score
            o["binding_reason"] = why
            o["binding_caveat"] = (
                "Bound to this building by NAME plus its own hard geography. The observation "
                "carried no street address, no phone and no comparable property code. The "
                "binding is a proposal for the routing and policy lanes to confirm on the "
                "property's OWN page; it is not an identity decision and it publishes nothing.")
            h.observations.append(o)
            for field in ("brand", "property_code", "route"):
                if not getattr(h, field) and o.get(field):
                    setattr(h, field, o[field])
        bound.append((s, h, score))
    return hard, bound, ambiguous, unbound


#: PALM BEACH COUNTY: chain flags that a Florida DBPR licence sometimes carries with NO place word. A bare flag is not a
#: premises identity, and because the shared exclusion registry matches on the normalised canonical name across
#: every market, a bare-flag row in one market bars an identically named hotel in another (caught by
#: release_contracts.verify_all on Cleveland's Holiday Inn Express & Suites).
_BARE_CHAIN_FLAG = re.compile(
    r"^(holiday inn express( hotel)?( (and|&) suites)?|holiday inn|hampton inn( (and|&) suites)?|"
    r"courtyard by marriott|residence inn( by marriott)?|fairfield inn( (and|&) suites)?|"
    r"springhill suites|towneplace suites|home2 suites|homewood suites|embassy suites|doubletree|"
    r"hilton garden inn|candlewood suites|staybridge suites|comfort inn( (and|&) suites)?|"
    r"comfort suites|quality inn( (and|&) suites)?|best western( plus)?|la quinta inn( (and|&) suites)?|"
    r"days inn|super 8|motel 6|red roof inn|extended stay america|wyndham garden|tru by hilton|"
    r"aloft|element|sonesta|woodspring suites)$", re.I)


#: BARE CHAIN FLAGS THIS ORDER READ FIRST-PARTY, where no census lane carried the fuller name.
#:
#: Keyed on (normalised bare flag, postal code). A bare flag is not a premises identity, and because the shared
#: exclusion registry matches on the normalised canonical name ACROSS EVERY MARKET, a bare-flag row here bars an
#: identically named hotel everywhere else -- Tampa already holds a bare "Best Western", and the global
#: authority build refuses with `duplicate excluded identity`. The standing rule is to fix it AT THE SOURCE and
#: never by superseding the other market's exclusion, so the name comes from the brand's OWN page, read by this
#: order, and never from anything this order invented.
FIRST_PARTY_BARE_FLAG_NAMES = {
    ("best western", "33477"): (
        "Best Western Intracoastal Inn",
        "the DBPR licence carries only the bare flag 'BEST WESTERN'. The brand's OWN hotel-search page named "
        "this premises 'Best Western Intracoastal Inn' at property code 10267, and the brand's own property "
        "page for 10267 states the premises as '810 S US Highway 1, Jupiter, Florida United States' and the "
        "policy 'Pets are not accepted.' -- both read by this order's attended browser on 2026-09-22. The "
        "census row's own street (810 US 1, 33477) is that premises."),
}


def _place_from_route_slug(url):
    """The municipality a brand's OWN route states, when this market's geography admits it.

    Returns "" unless exactly one path segment of the URL normalises to a municipality this market admits, so
    a slug this function does not understand can never name a property after somewhere the market does not
    contain. Reporting and naming only -- it never admits or places a property; the postal code does that.
    """
    if not url:
        return ""
    segs = [seg for seg in re.split(r"[/?#]", str(url)) if seg]
    hits = []
    for seg in segs:
        cand = " ".join(seg.replace("-", " ").replace("_", " ").split()).lower()
        if cand in _IN_MARKET_MUNICIPALITIES and cand not in hits:
            hits.append(cand)
    if len(hits) != 1:
        return ""
    return " ".join(w.capitalize() for w in hits[0].split())


def name_bare_chain_flags(nodes):
    """A node whose chosen name is a BARE chain flag takes a longer name from its own observations that starts
    with that flag and adds a place. Returns the rulings, each citing the lane that supplied the fuller name."""
    rulings = []
    for n in nodes:
        chosen = " ".join((n.name or "").split())
        if not chosen or not _BARE_CHAIN_FLAG.match(normalize_name(chosen)):
            continue
        flag = normalize_name(chosen)
        # A first-party read of the brand's own page outranks the census lanes' silence.
        fp = FIRST_PARTY_BARE_FLAG_NAMES.get((flag, (n.postal or "")[:5]))
        if fp:
            rulings.append(OrderedDict([
                ("was", chosen), ("now", fp[0]),
                ("lanes", ["PROPERTY_PAGE_ATTENDED"]),
                ("sources", ["https://www.bestwestern.com/en_US/book/hotels-in-jupiter/"
                             "best-western-intracoastal-inn/propertyCode.10267.html"]),
                ("why", "FIRST-PARTY NAMING: " + fp[1]),
            ]))
            n.name = fp[0]
            continue
        better = []
        for o in n.observations:
            cand = " ".join((o.get("name") or "").split())
            cn = normalize_name(cand)
            if cand and cn != flag and cn.startswith(flag) and len(_listing_slug(cand)) <= 80:
                better.append((cand, o.get("lane"), o.get("source_url")))
        if not better:
            # FALLBACK: the place the BRAND'S OWN ROUTE states.
            #
            # This is the rule this module's own report already describes -- "each such row takes the
            # property's OWN name from its brand's route slug, never a name this order invents" -- and it was
            # not implemented. Measured here: "Comfort Inn & Suites" at 1221 Hypoluxo Rd 33462 carries Choice's
            # own route /florida/lantana/comfort-inn-hotels/fl056. No observation name STARTS WITH the flag
            # (the row's own alias is "comfort inn lantana", which starts with the shorter "comfort inn"), so
            # the observation search above finds nothing and the row stayed a bare flag -- and a bare flag
            # collides with every identically named hotel in every other market through the shared exclusion
            # registry. Lexington already holds a bare "Comfort Inn & Suites", and the global authority build
            # refuses with `duplicate excluded identity`.
            #
            # The place is taken from the brand's own URL, never invented, and only when that place is one this
            # market's own geography admits -- so a mis-parsed slug cannot name a property after a town the
            # market does not contain.
            # the node's own route, else any website a lane recorded for it -- both first-party URLs
            _urls = [n.route or ""] + [str(o.get("website_url") or o.get("route") or o.get("source_url") or "")
                                       for o in n.observations]
            place = ""
            for _u in _urls:
                place = _place_from_route_slug(_u)
                if place:
                    break
            if not place:
                continue
            picked = "%s %s" % (chosen, place)
            if len(_listing_slug(picked)) > 80:
                continue
            rulings.append(OrderedDict([
                ("was", chosen), ("now", picked),
                ("lanes", ["BRAND_ROUTE_SLUG"]),
                ("sources", [next((u for u in _urls if u), "")]),
                ("why", "the chosen name was a BARE CHAIN FLAG with no place and no observation carried a "
                        "fuller one; the place comes from the BRAND'S OWN route slug, which is first-party, "
                        "and is admitted by this market's own geography"),
            ]))
            n.name = picked
            continue
        names = sorted({b[0] for b in better})
        if len(names) != 1:
            continue                      # two different fuller names is a review, never a coin flip
        picked = names[0]
        rulings.append(OrderedDict([
            ("was", chosen), ("now", picked),
            ("lanes", sorted({b[1] for b in better if b[1]})),
            ("sources", sorted({b[2] for b in better if b[2]})[:3]),
            ("why", "the chosen name was a BARE CHAIN FLAG with no place; a bare flag is not a premises "
                    "identity and collides with identically named hotels in other markets through the shared "
                    "exclusion registry"),
        ]))
        n.name = picked
    return rulings


def merge_zipless(nodes):
    """A second pass for rows whose source printed a street but no postal code."""
    with_zip = [n for n in nodes if n.street and n.postal]
    without = [n for n in nodes if n.street and not n.postal]
    merged, ambiguous = [], []
    absorbed = set()
    for n in without:
        key = address_key(n.street, "")
        hits = [h for h in with_zip
                if address_key(h.street, "") == key and not directional_conflict(h.street, n.street)
                and not (n.city and h.city
                         and normalize_name(n.city) != normalize_name(h.city))]
        if len(hits) != 1:
            if hits:
                ambiguous.append(OrderedDict([
                    ("name", n.name), ("street", n.street),
                    ("candidates", [h.name for h in hits])]))
            continue
        h = hits[0]
        for obs in n.observations:
            o = OrderedDict(obs)
            o["binding"] = "STREET_IDENTITY_WITHOUT_POSTAL"
            o["binding_reason"] = (
                "the source printed this street and no postal code; exactly one building in the "
                "census states the same street identity, and the two do not name different cities")
            h.observations.append(o)
        for field in ("city", "phone", "brand", "property_code", "route"):
            if not getattr(h, field) and getattr(n, field):
                setattr(h, field, getattr(n, field))
        if len(n.name) > len(h.name):
            h.name = n.name
        absorbed.add(id(n))
        merged.append(OrderedDict([("absorbed", n.name), ("into", h.name),
                                   ("street", h.street), ("postal_code", h.postal)]))
    return [n for n in nodes if id(n) not in absorbed], merged, ambiguous


_STREET_DROP = {"n", "s", "e", "w", "ne", "nw", "se", "sw", "north", "south", "east", "west",
                "northeast", "northwest", "southeast", "southwest", "st", "street", "rd", "road",
                "dr", "drive", "ave", "av", "avenue", "blvd", "boulevard", "pkwy", "parkway", "pky",
                "ln", "lane", "ct", "court", "pl", "place", "ste", "suite", "hwy", "highway", "way",
                "cir", "circle", "ter", "terrace", "trl", "trail", "sq", "square", "concourse"}


def _canon_words(street):
    a = re.sub(r"[^a-z0-9 ]", " ", (street or "").lower())
    toks = a.split()[1:] if a.split() and (a.split()[0].isdigit() or a.split()[0] in ("one", "two", "three")) else a.split()
    return {t for t in toks if t not in _STREET_DROP and not t.isdigit()}


def _route_numbers(street):
    toks = re.sub(r"[^a-z0-9 ]", " ", (street or "").lower()).split()
    if len(toks) < 2 or not re.search(r"\b(fl|hwy|highway|us|sr|route)\b", " ".join(toks[1:])):
        return ()
    return tuple(x for x in toks[1:] if x.isdigit())


def _canon_street_words(a, b):
    wa, wb = _canon_words(a), _canon_words(b)
    return bool(wa) and bool(wb) and (wa == wb or wa <= wb or wb <= wa)


def merge_street_spelling(nodes, zips=None):
    """A third pass for one building spelled two ways."""
    read = [n for n in nodes if any(str(o.get("lane", "")).startswith(("PROPERTY_PAGE", "REGISTRY_FL_DBPR"))
                                    for o in n.observations) and n.street and n.postal]
    merged, absorbed = [], set()
    for n in nodes:
        if n in read or not n.street or not n.postal or id(n) in absorbed:
            continue
        if not all(o.get("lane") in ("OSM_OVERPASS", "DESTINATION_ORGANIZATION") for o in n.observations):
            continue
        _words = {"one": "1", "two": "2", "three": "3"}

        def _num(st):
            first = (st.split() or [""])[0]
            return _words.get(first.lower(), first)
        num = _num(n.street)

        def _plural_free(st):
            return re.sub(r"s\b", "", normalize_name(st))

        def _same_corridor(a, b):
            if a[:5] == b[:5]:
                return True
            return bool(zips) and zips.get(a[:5]) is not None and zips.get(a[:5]) == zips.get(b[:5])
        hits = [h for h in read if _same_corridor(h.postal, n.postal)
                and _num(h.street) == num and not directional_conflict(h.street, n.street)
                and (chain_tokens(n.name) & chain_tokens(h.name)
                     or normalize_name(n.name) in {normalize_name(o.get("name") or "")
                                                   for o in h.observations}
                     or _plural_free(h.street) == _plural_free(n.street)
                     or _canon_street_words(h.street, n.street)
                     or (_route_numbers(h.street) and _route_numbers(h.street) == _route_numbers(n.street)))]
        if len(hits) != 1:
            continue
        h = hits[0]
        for o in n.observations:
            o = OrderedDict(o)
            o["binding"] = "SAME_HOUSE_NUMBER_POSTAL_AND_CHAIN_AS_A_READ_BUILDING"
            h.observations.append(o)
        absorbed.add(id(n))
        merged.append(OrderedDict([("absorbed", n.name), ("absorbed_street", n.street),
                                   ("into", h.name), ("street", h.street),
                                   ("postal_code", h.postal)]))
    return [n for n in nodes if id(n) not in absorbed], merged


def _listing_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")


def fold_registry_rows_into_a_page_read(nodes):
    """One licensed building, two street NAMES. A node that only the registry, the map and the bureau reached
    folds into the ONE building whose own page was read when both state the same house number and postal code,
    their chain vocabulary overlaps, and that page-read building carries no licence of its own."""
    reads = [h for h in nodes if h.street and h.postal
             and any(str(o.get("lane", "")).startswith("PROPERTY_PAGE") for o in h.observations)
             and not any(o.get("lane") == "REGISTRY_FL_DBPR" for o in h.observations)]
    folded, absorbed = [], set()
    for n in nodes:
        lanes = {o.get("lane") for o in n.observations}
        if "REGISTRY_FL_DBPR" not in lanes or not lanes <= {"REGISTRY_FL_DBPR", "OSM_OVERPASS", "DESTINATION_ORGANIZATION"}:
            continue
        if not n.street or not n.postal:
            continue
        num = (n.street.split() or [""])[0]
        hits = [h for h in reads if id(h) not in absorbed and h.postal[:5] == n.postal[:5]
                and (h.street.split() or [""])[0] == num and (chain_tokens(n.name) & chain_tokens(h.name))]
        if len(hits) != 1:
            continue
        h = hits[0]
        for o in n.observations:
            o = OrderedDict(o)
            o["binding"] = "LICENCE_STREET_RENAMED_SAME_HOUSE_NUMBER_POSTAL_AND_CHAIN_AS_A_PAGE_READ_BUILDING"
            o["superseded_street"] = n.street
            h.observations.append(o)
        absorbed.add(id(n))
        folded.append(OrderedDict([("absorbed", n.name), ("absorbed_street", n.street), ("into", h.name),
                                   ("street", h.street), ("postal_code", h.postal)]))
    return [n for n in nodes if id(n) not in absorbed], folded


def fold_map_rows_beside_a_read(nodes):
    """A MAP-ONLY node folds into a node whose OWN page was read when the two carry the identical normalised
    name (or the map name is the read node's page name), the same postal code, and house numbers no more than
    30 apart on the same street words."""
    def _num(st):
        m = re.match(r"\s*(\d+)\s+(.*)", st or "")
        return (int(m.group(1)), _canon_words(st)) if m else (None, set())

    read = [n for n in nodes if n.street and n.postal and any(
        str(o.get("lane", "")).startswith(("PROPERTY_PAGE", "DESTINATION_ORGANIZATION", "REGISTRY_FL_DBPR")) for o in n.observations)]
    folded, absorbed = [], set()
    for n in nodes:
        if n in read or not n.street or not n.postal:
            continue
        if not all(o.get("lane") == "OSM_OVERPASS" for o in n.observations):
            continue
        num, words = _num(n.street)
        if num is None:
            continue
        names = {normalize_name(o.get("name") or "") for o in n.observations}
        hits = []
        for h in read:
            hnum, hwords = _num(h.street)
            if hnum is None or h.postal[:5] != n.postal[:5] or abs(hnum - num) > 30 or directional_conflict(h.street, n.street):
                continue
            if not (words and hwords and (words <= hwords or hwords <= words)):
                continue
            if names & {normalize_name(o.get("name") or "") for o in h.observations}:
                hits.append(h)
        if len(hits) != 1:
            continue
        h = hits[0]
        for o in n.observations:
            o = OrderedDict(o)
            o["binding"] = "SAME_NAME_MAP_ROW_WITHIN_THIRTY_HOUSE_NUMBERS_OF_A_READ_BUILDING"
            h.observations.append(o)
        absorbed.add(id(n))
        folded.append(OrderedDict([("absorbed", n.name), ("absorbed_street", n.street),
                                   ("into", h.name), ("street", h.street), ("postal_code", h.postal)]))
    return [n for n in nodes if id(n) not in absorbed], folded


def fold_rows_into_a_read_by_name(nodes):
    """One hotel, two addresses in two secondary sources -- joined to the ONE building this order read by an
    identical name (bureau) or identical brand vocabulary within 350m (map)."""
    read = [n for n in nodes if any(str(o.get("lane", "")).startswith("PROPERTY_PAGE") for o in n.observations)]
    folded, absorbed = [], set()
    for n in nodes:
        if n in read:
            continue
        lanes = {o.get("lane") for o in n.observations}
        hits = []
        if lanes == {"DESTINATION_ORGANIZATION"}:
            nm = normalize_name(n.name)
            hits = [h for h in read if nm and nm in {normalize_name(o.get("name") or "") for o in h.observations
                                                     if str(o.get("lane", "")).startswith("PROPERTY_PAGE")}]
            how = "IDENTICAL_NAME_TO_A_READ_BUILDING_ROSTER_ADDRESS_SUPERSEDED"
        elif lanes == {"OSM_OVERPASS"} and n.lat is not None and n.postal:
            ct = chain_tokens(n.name)
            hits = [h for h in read if ct and len(ct) >= 2 and chain_tokens(h.name) == ct
                    and h.lat is not None and (h.postal or "")[:5] == n.postal[:5]
                    and _km(float(n.lat), float(n.lng), float(h.lat), float(h.lng)) <= 0.35]
            how = "IDENTICAL_BRAND_VOCABULARY_AND_PIN_WITHIN_350M_OF_A_READ_BUILDING_MAP_ADDRESS_SUPERSEDED"
        else:
            continue
        if len(hits) != 1:
            continue
        h = hits[0]
        for o in n.observations:
            o = OrderedDict(o)
            o["binding"] = how
            o["superseded_street"] = n.street
            h.observations.append(o)
        absorbed.add(id(n))
        folded.append(OrderedDict([("absorbed", n.name), ("absorbed_street", n.street), ("into", h.name),
                                   ("street", h.street), ("postal_code", h.postal), ("binding", how)]))
    return [n for n in nodes if id(n) not in absorbed], folded


#: Destination-roster rows whose building a first-party read states under its CURRENT flag at the same street.
ROSTER_ROWS_SUPERSEDED_BY_A_READ = {}


def fold_roster_rows_superseded_by_a_read(nodes):
    folded, absorbed = [], set()
    for n in nodes:
        if {o.get("lane") for o in n.observations} != {"DESTINATION_ORGANIZATION"}:
            continue
        rule = ROSTER_ROWS_SUPERSEDED_BY_A_READ.get(normalize_name(n.name))
        if not rule:
            continue
        hits = [h for h in nodes if h is not n and normalize_name(h.street).startswith(rule[0])
                and any(str(o.get("lane", "")).startswith("PROPERTY_PAGE") for o in h.observations)]
        if len(hits) != 1:
            continue
        for o in n.observations:
            o = OrderedDict(o)
            o["binding"] = "ROSTER_ROW_SUPERSEDED_BY_A_READ_UNDER_THE_CURRENT_FLAG"
            o["superseded_why"] = rule[1]
            hits[0].observations.append(o)
        absorbed.add(id(n))
        folded.append(OrderedDict([("absorbed", n.name), ("into", hits[0].name), ("why", rule[1])]))
    return [n for n in nodes if id(n) not in absorbed], folded


_WYNDHAM_URL_CITY = re.compile(r"wyndhamhotels\.com/[a-z0-9-]+/([a-z-]+)-florida/", re.I)


def fill_missing_cities(rows):
    """Fill a BLANK city from this market's own evidence. Never overwrite one."""
    by_zip = {}
    for r in rows:
        if (r.get("city") or "").strip() and r.get("postal_code"):
            by_zip.setdefault(r["postal_code"], set()).add(r["city"].strip())
    filled, unfilled = [], []
    for r in rows:
        if (r.get("city") or "").strip():
            continue
        peers = by_zip.get(r.get("postal_code") or "", set())
        if len(peers) == 1:
            city = next(iter(peers))
            basis = ("every other admitted identity in postal code %s states this city"
                     % r["postal_code"])
        else:
            urls = [o.get("route") or o.get("source_url") or "" for o in r.get("evidence", [])]
            m = next((_WYNDHAM_URL_CITY.search(u) for u in urls
                      if _WYNDHAM_URL_CITY.search(u)), None)
            if not m:
                unfilled.append(OrderedDict([("identity_key", r["identity_key"]),
                                             ("street", r["street"]),
                                             ("postal_code", r["postal_code"])]))
                continue
            city = m.group(1).replace("-", " ").title()
            basis = ("the city segment of the property's own canonical URL on the brand's site "
                     "(%s)" % m.group(0))
        r["city"] = city
        r["city_basis"] = basis
        filled.append(OrderedDict([("identity_key", r["identity_key"]), ("city", city),
                                   ("basis", basis)]))
    return filled, unfilled


_BRAND_SLUG = (
    re.compile(r"hilton\.com/en/hotels/[a-z0-9]{4,9}-([a-z0-9-]+)/?$", re.I),
    re.compile(r"marriott\.com/en-us/hotels/[a-z0-9]{5,7}-([a-z0-9-]+)/overview/?$", re.I),
)

_BRAND_WORDS = {
    "marriott", "hilton", "hyatt", "radisson", "wyndham", "choice", "sheraton", "westin",
    "renaissance", "courtyard", "residence", "towneplace", "springhill", "fairfield",
    "doubletree", "embassy", "candlewood", "staybridge", "holiday", "crowne", "ramada",
    "baymont", "super", "days", "quality", "comfort", "sleep", "clarion", "econo",
    "travelodge", "howard", "johnson", "roof", "studio", "woodspring", "sonesta",
    "drury", "western", "quinta", "home2", "tru", "element", "aloft", "hampton",
    "homewood", "delta", "spark", "wingate", "hawthorn", "microtel", "motel6",
    "canopy", "signia", "waldorf", "moxy", "le", "meridien",
    "jw", "regis", "indigo", "kimpton", "voco", "even", "omni",
    "loews", "americinn", "waterwalk", "extended", "intown", "red",
    "rodeway", "suburban", "mainstay", "cambria", "ascend", "motel", "studio6", "knights",
    "avid", "tempo", "echo", "tryp", "glo", "gaylord", "margaritaville", "melia", "ritz",
    "four", "points", "stayable", "hometowne", "oyo",
}


def name_bare_identities(rows):
    """Give a bare brand label its own brand's name for the property."""
    named = []
    for r in rows:
        brands = set()
        for o in r.get("evidence", []):
            brands |= {t for t in normalize_name(o.get("name") or "").split()
                       if t in _BRAND_WORDS}
        sigs = []
        for o in r.get("evidence", []):
            w = {t for t in normalize_name(o.get("name") or "").split() if t in _BRAND_WORDS}
            if w and not any(w & x for x in sigs):
                sigs.append(w)
        if len(sigs) > 1:
            continue
        toks = [t for t in normalize_name(r["canonical_name"]).split() if t]
        if len(toks) > 2 or any(t in _ALL_PLACES or t in _DIRECTIONALS for t in toks):
            continue
        route = ""
        for o in r.get("evidence", []):
            cand = o.get("route") or ""
            if any(rx.search(cand) for rx in _BRAND_SLUG):
                route = cand
                break
        if not route:
            continue
        m = next(rx.search(route) for rx in _BRAND_SLUG if rx.search(route))
        proposed = " ".join(w.capitalize() for w in m.group(1).split("-"))
        if normalize_name(proposed) == normalize_name(r["canonical_name"]):
            continue
        was_chain = {t for t in normalize_name(r["canonical_name"]).split()
                     if t in _BRAND_WORDS}
        now_chain = {t for t in normalize_name(proposed).split() if t in _BRAND_WORDS}
        if was_chain and now_chain and not (was_chain & now_chain):
            continue
        named.append(OrderedDict([
            ("was", r["canonical_name"]), ("now", proposed), ("route", route),
            ("basis", "the property's own slug on its brand's site; the map source left the "
                      "identity bare and a bare brand label is not an identity")]))
        aliases = set(r.get("identity_key_aliases") or []) | {r["identity_key"],
                                                              normalize_name(proposed)}
        r["canonical_name"] = proposed
        r["identity_key"] = ptf_identity_key(proposed)
        r["identity_key_aliases"] = sorted(a for a in aliases if a)
        r["canonical_name_basis"] = named[-1]["basis"]
    return named


ADMITTED_STATES = frozenset({"FL", "FLORIDA"})


def corridor_index():
    """``corridor id`` and ``state`` per admitted postal code, from the contract."""
    cfg = MC.parse_market(_load(CONTRACT_PATH), source=CONTRACT_PATH)
    zips, states = {}, {}
    for c in cfg.corridors:
        for z in c.included_postal_codes:
            zips[z] = c.corridor_id
            states[z] = (getattr(c, "state_code", "") or cfg.state_code or "").upper()
    return cfg, zips, states


def explicit_index(cfg):
    out = {}
    for c in cfg.corridors:
        for key in c.explicit_hotel_ids:
            out.setdefault(key, c.corridor_id)
    return out


#: The municipality each corridor of the contract sits in (name attachment only).
CORRIDOR_MUNICIPALITY = GEO.corridor_municipality()

#: The mailing municipalities each corridor's postal codes actually carry. A property whose OWN stated
#: municipality is a known place outside its ZIP's corridor list is a GEOGRAPHY_HOLD.
CORRIDOR_CITIES = {
    "downtown-west-palm-beach": {"west palm beach", "w palm beach", "wpb", "downtown west palm beach",
                                 "clematis", "rosemary square", "palm beach"},
    "palm-beach-worth-avenue": {"palm beach", "town of palm beach", "worth avenue", "west palm beach"},
    "northwood-metrocentre": {"west palm beach", "w palm beach", "wpb", "mangonia park", "riviera beach",
                              "northwood"},
    "riviera-beach-singer-island": {"riviera beach", "palm beach shores", "singer island", "lake park",
                                    "west palm beach", "north palm beach", "palm beach gardens"},
    "palm-beach-gardens": {"palm beach gardens", "north palm beach", "west palm beach", "jupiter"},
    "jupiter-tequesta": {"jupiter", "jupiter farms", "abacoa", "tequesta", "juno beach",
                         "palm beach gardens", "hobe sound"},
    "palm-beach-international-airport": {"west palm beach", "w palm beach", "wpb", "lake clarke shores",
                                         "palm springs", "haverhill", "lake worth", "glen ridge",
                                         "cloud lake", "atlantis"},
    "lake-worth-beach": {"lake worth", "lake worth beach", "palm springs", "greenacres", "atlantis",
                         "west palm beach", "lantana"},
    "delray-beach": {"delray beach", "delray", "gulf stream", "highland beach", "boynton beach",
                     "boca raton"},
    "boca-raton": {"boca raton", "highland beach", "delray beach"},
    "boynton-beach": {"boynton beach", "ocean ridge", "briny breezes", "gulf stream", "delray beach",
                      "lantana", "hypoluxo"},
    "lantana-manalapan-hypoluxo": {"lantana", "manalapan", "hypoluxo", "lake worth", "south palm beach",
                                   "boynton beach"},
    "north-palm-beach-juno-beach": {"north palm beach", "juno beach", "palm beach gardens", "lake park",
                                    "jupiter"},
    "western-communities": {"wellington", "royal palm beach", "greenacres", "loxahatchee", "the acreage",
                            "westlake", "west palm beach", "haverhill", "lake worth"},
    "the-glades": {"belle glade", "pahokee", "south bay", "canal point"},
}


def municipality_conflict(postal, city):
    c = " ".join((city or "").lower().replace(".", " ").split())
    if not c or c not in _ALL_PLACES:
        return None
    klass, slug, _why = GEO.classify_postal(postal, city)
    if not slug:
        return None
    if c in CORRIDOR_CITIES.get(slug, set()):
        return None
    return ("the property's own page states the municipality %r beside postal code %s, which the "
            "corridor registry places in %s (%s); one of the two first-party facts is wrong and the "
            "ZIP alone never decides which" % (city, (postal or "")[:5], slug, ", ".join(sorted(CORRIDOR_CITIES.get(slug, ())))))


_FIRST_PARTY_NAME_LANES = ("PROPERTY_PAGE", "BRAND_INVENTORY")


def distinct_brand_signatures(node):
    """The distinct chain identities the FIRST-PARTY evidence gives this building."""
    sigs = []
    for obs in node.observations:
        if not str(obs.get("lane", "")).startswith(_FIRST_PARTY_NAME_LANES):
            continue
        words = {t for t in normalize_name(obs.get("name") or "").split() if t in _BRAND_WORDS}
        if not words:
            continue
        if not any(words & s for s in sigs):
            sigs.append(words)
        else:
            for i, s in enumerate(sigs):
                if words & s:
                    sigs[i] = s | words
                    break
    return sigs


#: A map-only row under a flag whose own Palm-Beach-area route on the brand's site is RETIRED. Empty at authoring time.
RETIRED_WYNDHAM_FLAGS = ()


def classify(node, zips, name_counts, street_counts):
    n = normalize_name(node.name)
    if not n:
        return IDENTITY_REVIEW_REQUIRED, ("the only source that found this building published no "
                                          "name for it; an address without a name cannot be a "
                                          "published identity")
    lanes = {o["lane"] for o in node.observations}
    lead_types = {o.get("lead_type") for o in node.observations if o.get("lead_type")}

    if n in MILITARY_NONPUBLIC_NAMES:
        return OUTSIDE_MARKET, ("MILITARY_GOVERNMENT_NONPUBLIC -- %s; the geography's military / "
                                "government lodging rule refuses it" % MILITARY_NONPUBLIC_NAMES[n])
    if normalize_name(node.city) in _OUT_OF_MARKET_PLACES:
        _fs = normalize_name(node.city) in _FUTURE_SUBMARKET_PLACES
        return OUTSIDE_MARKET, (("FUTURE_SUBMARKET -- " if _fs else "")
                                + "the row's own municipality %r is a place the geography refuses by name"
                                % node.city)
    _rk = address_key(node.street, "") if node.street else ""
    for _hold_key, _why in REBRAND_HOLDS.items():
        if _rk and (_rk == address_key(_hold_key, "") or _rk.startswith(_hold_key)):
            return SAME_IDENTITY_REBRAND_SUCCESSOR, "REBRAND_HOLD -- " + _why
    if n in LODGING_UNCONFIRMED:
        return IDENTITY_REVIEW_REQUIRED, "LODGING_CATEGORY_UNCONFIRMED -- " + LODGING_UNCONFIRMED[n]
    if n in NOT_LODGING_NAMES or n in STR_PLACEHOLDERS:
        return NON_LODGING, NOT_LODGING_WHY.get(n, "the source lists a business that is not lodging")
    _nh = nonhotel_by_name(node.name, {o.get("lane") for o in node.observations}, street=node.street)
    if _nh:
        if _nh.startswith("IDENTITY_REVIEW"):
            return IDENTITY_REVIEW_REQUIRED, _nh
        return NON_LODGING, _nh
    if n in DUPLICATE_OF:
        return DUPLICATE_LISTING, DUPLICATE_OF[n]
    for _rx, _why in DUAL_BRAND_COMBINED:
        if _rx.search(node.name or ""):
            return IDENTITY_REVIEW_REQUIRED, "DUAL_BRAND_SPLIT_REQUIRED -- " + _why
    _subcats = {s for o in node.observations if o.get("lane") == "DESTINATION_ORGANIZATION"
                for s in (o.get("bureau_all_subcategories") or [o.get("bureau_subcategory")]) if s}
    if _subcats and not (_subcats & HOTEL_BUREAU_SUBCATEGORIES) and (_subcats & NON_HOTEL_BUREAU_SUBCATEGORIES) and not any(
            str(o.get("lane", "")).startswith(("PROPERTY_PAGE", "BRAND_INVENTORY")) for o in node.observations):
        return NON_LODGING, ("VACATION_RENTAL -- the destination bureau files this listing under %s -- a vacation-rental "
                             "category, not a hotel establishment; refused under the order's vacation-rental / "
                             "condo / historic-home filter" % sorted(_subcats))
    if _subcats and not (_subcats & HOTEL_BUREAU_SUBCATEGORIES) and _CAMPGROUND_NAME.search(node.name or "") and not any(
            str(o.get("lane", "")).startswith(("PROPERTY_PAGE", "BRAND_INVENTORY")) for o in node.observations):
        return NON_LODGING, ("the destination bureau files this listing only under %s and its own name is a campground, RV "
                             "park or state park; campgrounds and RV parks are NON_LODGING" % sorted(_subcats))
    if lead_types and lead_types <= NON_HOTEL_LEAD_TYPES:
        return NON_LODGING, "every lane that typed this row typed it %s" % sorted(lead_types)
    if lanes == {"OSM_OVERPASS"} and any(
            (" %s " % t) in (" %s " % n) for t in RETIRED_WYNDHAM_FLAGS):
        return IDENTITY_REVIEW_REQUIRED, (
            "a map row under a flag (%s) whose own Palm-Beach-area route on the brand's site is "
            "RETIRED -- it redirects to the brand's city search, which does not list it; the "
            "building's current identity is unconfirmed" % ", ".join(
                t for t in RETIRED_WYNDHAM_FLAGS if (" %s " % t) in (" %s " % n)))
    if lanes == {"OSM_OVERPASS"} and all(o.get("non_hotel_name") for o in node.observations) and not \
            re.search(r"\b(motel|motor court|motor lodge|hotel|inn)\b", node.name or "", re.I):
        return NON_LODGING, ("a map row whose own name reads as a private cottage, house, estate or "
                             "bed and breakfast; never a hotel identity on a map tag alone")
    _osm_cats = {c for o in node.observations for c in (o.get("osm_categories") or []) if c}
    if lanes == {"OSM_OVERPASS"} and _osm_cats and _osm_cats <= {"apartment", "chalet"}:
        return NON_LODGING, ("a map row tagged tourism=%s (a vacation apartment / condo unit or rental "
                             "chalet) that no brand, bureau or property page typed as a hotel; refused under "
                             "the order's cabin and condo-unit rule" % "/".join(sorted(_osm_cats)))
    if lanes == {"OSM_OVERPASS"} and re.match(r"\s*STVR\b", node.name or ""):
        return NON_LODGING, ("VACATION_RENTAL -- a map row the map itself names 'STVR' (a short-term vacation rental); "
                             "an individual rental unit, never a hotel identity")
    if lanes <= {"COMPETITOR_LEAD", "REGIONAL_VISITOR_CENTER"} and _RENTAL_WORDS.search(node.name or ""):
        return NON_LODGING, ("a competitor short-term-rental listing, named only by the competitor "
                             "and reading as a private dwelling; never a hotel identity")
    _hard_read = any(o.get("lane", "").startswith("PROPERTY_PAGE") for o in node.observations)
    if node.ambiguous_matches and not (_hard_read and node.street and node.postal):
        return IDENTITY_REVIEW_REQUIRED, (
            "a name-only observation that matches more than one established building equally "
            "well (%s); a tie is a review, never a coin flip"
            % ", ".join(node.ambiguous_matches[:4]))
    # REFUSED NEIGHBOURS BY PIN. A row with NO postal code of its own that every source pins SOUTH of the
    # Palm Beach / Broward county line (lat < 26.3340, the Boca Raton - Deerfield Beach line at the Hillsboro
    # Canal) or NORTH of the Palm Beach / Martin county line (lat > 26.9770, the Tequesta - Hobe Sound line)
    # cannot be an admitted identity whatever else is unknown about it. Both neighbours are named markets:
    # Broward is the LIVE fort-lauderdale-fl market and already publishes its own inventory.
    _pins = [(o.get("lat"), o.get("lng")) for o in node.observations
             if o.get("lat") is not None and o.get("lng") is not None]
    if not node.postal and _pins and all(float(t) < 26.3340 or float(t) > 26.9770 for t, g in _pins):
        return OUTSIDE_MARKET, ("no postal code of its own, and every source pins it beyond the admitted corridors "
                                "(Broward County south -- the LIVE fort-lauderdale-fl market -- or Martin County "
                                "north; %.4f, %.4f)" % (float(_pins[0][0]), float(_pins[0][1])))
    if not node.street and not node.phone and not node.postal:
        _named = places_in(node.name)
        if _named and _named <= _OUT_OF_MARKET_PLACES:
            return OUTSIDE_MARKET, ("a name-only lead whose own name states %s, a place the geography refuses by "
                                    "name; recorded, never admitted" % sorted(_named))
    if not node.street and not node.phone:
        if node.lat is not None:
            return NAME_ONLY_UNRESOLVED, (
                "no street address and no phone, but the map source placed it at %.5f, %.5f "
                "inside this market's bounds: an ADDRESS FILL, not a new discovery"
                % (node.lat, node.lng))
        if node.route:
            return NAME_ONLY_UNRESOLVED, (
                "a brand roster row whose property page this order never read, so it has no "
                "address of its own: an ADDRESS FILL from a first-party read, not a new discovery")
        return NAME_ONLY_UNRESOLVED, ("no street address, no phone, no coordinates and no "
                                      "building this name clearly matches: a name alone proposes "
                                      "an identity and never decides one")
    if node.region and node.region.upper() not in ADMITTED_STATES:
        return OUTSIDE_MARKET, ("the row's own state is %s; every corridor of this market is in "
                                "Florida" % node.region)
    if node.postal and node.postal[:5] not in zips:
        _fs = (" FUTURE_SUBMARKET %s --" % GEO.future_market_for(node.postal)) if GEO.future_market_for(node.postal) else ""
        return OUTSIDE_MARKET, ("%s postal code %s is claimed by no corridor of The Palm Beaches "
                                "contract; %s" % (_fs, node.postal[:5],
                                GEO.classify_postal(node.postal, node.city)[2])).strip()
    if node.postal and node.city:
        _klass, _slug, _why = GEO.classify_postal(node.postal, node.city)
        if _klass == "OUTSIDE":
            return OUTSIDE_MARKET, ("the property's own stated municipality %r inside the shared "
                                    "postal code %s is refused by the geography: %s"
                                    % (node.city, node.postal[:5], _why))
    _bnl = brand_not_listed(node)
    if _bnl:
        return IDENTITY_REVIEW_REQUIRED, "BRAND_INVENTORY_DOES_NOT_LIST -- " + _bnl
    _mc = municipality_conflict(node.postal, node.city)
    if _mc:
        return IDENTITY_REVIEW_REQUIRED, "GEOGRAPHY_HOLD -- " + _mc
    _sp = SAME_PREMISES_HOLDS.get(normalize_name(node.name))
    if _sp:
        return IDENTITY_REVIEW_REQUIRED, "SAME_PREMISES_HOLD -- " + _sp
    _gh = GEOGRAPHY_HOLDS.get(normalize_name(node.name))
    if _gh:
        return IDENTITY_REVIEW_REQUIRED, "GEOGRAPHY_HOLD -- " + _gh
    if not node.postal and not node.property_code:
        return IDENTITY_REVIEW_REQUIRED, ("no postal code and no brand property code, so market "
                                          "membership cannot be decided deterministically")
    brands = distinct_brand_signatures(node)
    if len(brands) > 1:
        return SAME_IDENTITY_REBRAND_SUCCESSOR, (
            "one address, two brand identities in the evidence (%s). The building is one building; "
            "which name it trades under today is a founder ruling, and publishing the wrong one "
            "would send a guest to a hotel that no longer answers to it."
            % " | ".join(" ".join(sorted(b)) for b in brands))
    sk = street_identity(node.street, node.postal)
    if sk and street_counts.get(sk, 0) > 1:
        if node.property_code and node.brand and node.route:
            return TRUE_HOTEL_IDENTITY, ""
        return SAME_CAMPUS_DISTINCT_ENTITY, (
            "another distinct identity states the same street identity, and this row states no "
            "brand property code and canonical first-party URL of its own, so the exclusion "
            "contract's co-located-distinct proof cannot be made for it; both rows are retained "
            "and neither is aliased")
    if name_counts.get((n, ""), 0) > 1 and not _hard_read:
        return IDENTITY_REVIEW_REQUIRED, ("another node normalises to the same name at a different "
                                          "address; a same-brand same-city pair is demoted to "
                                          "review, never auto-aliased")
    return TRUE_HOTEL_IDENTITY, ""


#: Brand families whose OWN Palm-Beach-area inventory this order read. Families whose inventory refused this
#: client are NOT listed: a map row under their flag is not demoted for a read that never happened.
_COVERED_FLAGS = (
    ("HILTON", r"\b(hampton|hilton|home2|homewood|embassy suites|doubletree|spark by hilton|tru by hilton|tempo|signia|waldorf)\b"),
    ("MARRIOTT", r"\b(courtyard by marriott|courtyard marriott|courtyard palm beach|courtyard west palm beach|courtyard oceanside|courtyard by|courtyard(?= (palm|west|downtown|airport|boca|delray|jupiter|wellington))|residence inn|fairfield|springhill|towneplace|aloft|element|westin|sheraton|four points|ac hotel|marriott|moxy|gaylord|ritz)\b"),
    ("WYNDHAM", r"\b(days inn|super 8|baymont|la quinta|wingate|microtel|travelodge|ramada|howard johnson|hawthorn|tryp)\b"),
)


def brand_not_listed(node):
    lanes = {o.get("lane") for o in node.observations}
    # PALM BEACH COUNTY: the brand inventories this order could read are PARTIAL (Hilton city pages carry the
    # twenty nearest cards; Marriott's Florida sitemap omits several flags). An ACTIVE DBPR licence
    # (the state's own current record) or the destination bureau's own current listing is independent evidence the
    # flag trades at that address today, so only a MAP-ONLY or COMPETITOR-ONLY flagged row is demoted here.
    if lanes & {"REGISTRY_FL_DBPR", "DESTINATION_ORGANIZATION"}:
        return None
    if lanes & {"PROPERTY_PAGE_ATTENDED", "PROPERTY_PAGE_STATIC", "PROPERTY_PAGE_IDENTITY_ONLY",
                "BRAND_INVENTORY_OWNED", "BRAND_INVENTORY_CITY_PAGE", "BRAND_INVENTORY_STATE_SITEMAP",
                "BRAND_INVENTORY_SITEMAP"}:
        return None
    for fam, rx in _COVERED_FLAGS:
        if re.search(rx, node.name or "", re.I):
            return ("a %s row naming a %s flag (%r) that no read of that brand's own Palm-Beach-area inventory "
                    "joined at this address; a retired, rebranded or mis-drawn row is never admitted on its label"
                    % ("/".join(sorted(lanes)), fam, node.name))
    return None


SOURCE_AUTHORITIES = [
    "Florida Department of Business and Professional Regulation active public-lodging licence extracts hrlodge1..7.csv "
    "(https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/, retrieved 2026-09-19)",
    "OpenStreetMap via the Geofabrik Florida extract (2026-09-15 snapshot), reduced to this market's observation box "
    "(ODbL, (c) OpenStreetMap contributors)",
    "launch_packages/pettripfinder/markets/reports/dayton_oh_brand_directory_harvest_001.json (the committed national "
    "Marriott harvest, MIA-coded routes)",
    "https://www.marriott.com/en-us/hotel-sitemap/usa-florida-hotel-sitemap (the brand's own Florida hotel sitemap page)",
    "https://www.hilton.com/en/locations/usa/florida/<city>/ (Florida city pages and their in-market interlinks, with "
    "property cards)",
    "the brands' own sitemaps that answered this client",
    "https://www.thepalmbeaches.com listings (Discover The Palm Beaches' own sitemap-published listing pages)",
    "https://www.bringfido.com city pages (JSON-LD Hotel ItemList; names only, discovery/gap-challenge)",
    "each property's own page (static, Firecrawl and attended browser passes)",
]


def build():
    cfg, zips, corridor_state = corridor_index()
    explicit = explicit_index(cfg)
    lanes = OrderedDict([
        ("REGISTRY_FL_DBPR", read_dbpr()),
        ("OSM_OVERPASS", read_osm()),
        ("BRAND_INVENTORY_OWNED", read_brand_owned()),
        ("BRAND_INVENTORY_CITY_PAGE", read_brand_city_pages()),
        ("BRAND_INVENTORY_STATE_SITEMAP", read_brand_state_sitemap()),
        ("BRAND_INVENTORY_SITEMAP", read_brand_sitemaps()),
        ("DESTINATION_ORGANIZATION", read_destination_roster()),
        ("REGIONAL_VISITOR_CENTER", read_regional_visitor_center()),
        ("COMPETITOR_LEAD", read_competitor()),
        ("IDENTITY_VERIFIED_PLACES", read_gap_verified()),
        ("PROPERTY_PAGE", read_property_pages() + read_identity_only_pages()),
    ])
    all_obs = [o for rows in lanes.values() for o in rows]
    nodes, merge_conflicts = merge(all_obs)
    nodes, early_spelling_merged = merge_street_spelling(nodes, zips)
    nodes, zipless_merged, zipless_ambiguous = merge_zipless(nodes)
    nodes, destination_merged = merge_destination_rows(nodes)
    for n in nodes:
        if not n.postal:
            stated = [o.get("stated_postal_code") for o in n.observations
                      if o.get("lane") == "DESTINATION_ORGANIZATION" and o.get("stated_postal_code")]
            if stated and all(o.get("lane") in ("DESTINATION_ORGANIZATION", "COMPETITOR_LEAD", "REGIONAL_VISITOR_CENTER",
                                                "OSM_OVERPASS")
                              for o in n.observations):
                n.postal = stated[0]
    corridor_municipality = {}
    for n in nodes:
        cid = zips.get((n.postal or "")[:5], "")
        if cid:
            corridor_municipality[id(n)] = CORRIDOR_MUNICIPALITY.get(cid.split("__", 1)[-1], "")
    nodes, spelling_merged = merge_street_spelling(nodes, zips)
    nodes, licence_folded = fold_registry_rows_into_a_page_read(nodes)
    spelling_merged = early_spelling_merged + spelling_merged + licence_folded
    nodes, neighbour_folded = fold_map_rows_beside_a_read(nodes)
    nodes, name_folded = fold_rows_into_a_read_by_name(nodes)
    nodes, roster_superseded = fold_roster_rows_superseded_by_a_read(nodes)
    name_folded = name_folded + roster_superseded
    neighbour_folded = neighbour_folded + name_folded
    for n in nodes:
        if any(str(o.get("lane", "")).startswith("PROPERTY_PAGE") for o in n.observations):
            continue
        bureau = [o.get("name") for o in n.observations
                  if o.get("lane") == "DESTINATION_ORGANIZATION" and o.get("name")]
        if bureau:
            n.name = bureau[0]
    hard, bound, ambiguous, unbound = attach_name_only(nodes, corridor_municipality)
    nodes = hard + ambiguous + unbound
    for n in nodes:
        page_names = [o.get("name") for o in n.observations
                      if str(o.get("lane", "")).startswith("PROPERTY_PAGE") and o.get("name")]
        if page_names:
            n.name = page_names[0]
        if len(_listing_slug(n.name)) > 80:
            for name_lanes in (("BRAND_INVENTORY_OWNED", "BRAND_INVENTORY_CITY_PAGE", "BRAND_INVENTORY_SITEMAP"),
                               ("REGISTRY_FL_DBPR",), ("OSM_OVERPASS",)):
                fits = sorted({o.get("name") for o in n.observations if o.get("lane") in name_lanes and o.get("name")
                               and len(_listing_slug(o["name"])) <= 80}, key=lambda s: (-len(s), s))
                if fits:
                    n.name = fits[0]
                    break
    bare_flag_renamed = name_bare_chain_flags(nodes)

    code_detached = []
    for n in nodes:
        page = [o for o in n.observations if str(o.get("lane", "")).startswith("PROPERTY_PAGE")
                and (o.get("property_code") or "").strip() and o.get("brand")]
        codes = sorted({o["property_code"].strip().lower() for o in page})
        if len(codes) != 1:
            continue
        code = codes[0]
        keep = []
        for o in n.observations:
            oc = (o.get("property_code") or "").strip().lower()
            if (oc and oc != code and (o.get("brand") or "") == page[0].get("brand")
                    and not str(o.get("lane", "")).startswith("PROPERTY_PAGE")):
                code_detached.append(OrderedDict([("from", n.name), ("street", n.street), ("page_code", code),
                                                  ("detached_code", oc), ("detached_name", o.get("name")),
                                                  ("lane", o.get("lane"))]))
                continue
            keep.append(o)
        n.observations = keep
        if (n.property_code or "").lower() != code:
            n.property_code = code
            n.route = next((o.get("route") for o in page if o["property_code"].strip().lower() == code and o.get("route")),
                           n.route)

    # SAME-NAME COLLISION IS AN IN-MARKET TEST ONLY.
    #
    # This market's observation set deliberately carries the refused neighbours it must account for: every
    # Broward and Miami-Dade DBPR licence in a NAMED OUTSIDE postal code, so the Phase 22 county boundary audit
    # can count them. Those rows are OUTSIDE_MARKET and can never publish here -- but if they are counted in
    # the collision test, a generic chain flag in somebody else's market silently HOLDS a real hotel in this
    # one. Measured on this market's first census pass: "Budget Inn" (828 S Dixie Hwy, Lake Worth Beach 33460)
    # was held by Budget Inns in Pompano Beach 33069 and Miami 33147; "Relax Inn" (7448 Lake Worth Rd 33467)
    # by a Relax Inn in Fort Lauderdale 33316; "Super 8 Motel" (757 N US Hwy 1, Juno Beach 33408) by Super 8s
    # in Dania Beach and Homestead. All three neighbours belong to the LIVE fort-lauderdale-fl and miami-fl
    # markets and say nothing whatever about whether this market's row is ambiguous.
    #
    # This is the standing rule stated the other way round -- a bare chain flag in one market must never bar an
    # identically named hotel in another -- so the count is taken over ADMITTED-postal nodes only. A genuine
    # in-market same-name pair (two "Hilton West Palm Beach" nodes at 600 and 6000 Okeechobee) is still caught.
    # A node the brand's OWN inventory does not list is not an established identity either, so it cannot make
    # another row ambiguous. Measured here: an OSM-only pin spelling "Hilton West Palm Beach" at 6000
    # Okeechobee Boulevard (the real premises, on Hilton's own city-page card and on DBPR licence, is 600)
    # was holding the actual hotel. A map pin never demotes a first-party read.
    name_counts = Counter((normalize_name(n.name), "") for n in nodes
                          if (n.street or n.phone) and (n.postal or "")[:5] in zips
                          and not brand_not_listed(n))
    street_counts = Counter(street_identity(n.street, n.postal) for n in nodes
                            if street_identity(n.street, n.postal))

    rows = []
    for node in nodes:
        klass, why = classify(node, zips, name_counts, street_counts)
        z = (node.postal or "")[:5]
        sk = street_identity(node.street, node.postal)
        aliases = sorted({normalize_name(o.get("name") or "") for o in node.observations
                          if (o.get("name") or "").strip()}
                         | {o["read_for_identity_key"] for o in node.observations
                            if o.get("read_for_identity_key")})
        node.name = canonical_name(node.name)
        _key = ptf_identity_key(node.name)
        _corridor = explicit.get(_key) or zips.get(z, "")
        _basis = ("explicit" if explicit.get(_key)
                  else "postal_code" if z in zips else "")
        _slug = re.sub(r"[^a-z0-9]+", "-", _key).strip("-")
        _identity_state = ("IDENTITY_CONFIRMED" if klass == TRUE_HOTEL_IDENTITY
                           else "IDENTITY_PROVISIONAL"
                           if klass in (SAME_CAMPUS_DISTINCT_ENTITY,
                                        SAME_IDENTITY_REBRAND_SUCCESSOR, OUTSIDE_MARKET)
                           else "IDENTITY_UNRESOLVED")
        _lodging_state = ("NOT_LODGING" if klass == NON_LODGING
                          else "LODGING_CONFIRMED" if klass == TRUE_HOTEL_IDENTITY
                          else "NEEDS_REVIEW" if klass == IDENTITY_REVIEW_REQUIRED
                          else "LODGING_BY_NAME")
        _collision = ("SHARED_ADDRESS" if sk and street_counts.get(sk, 0) > 1 else "NONE")
        rows.append(OrderedDict([
            ("identity_key", _key),
            ("slug", _slug),
            ("market_id", MARKET_ID),
            ("identity_state", _identity_state),
            ("lodging_state", _lodging_state),
            ("collision_state", _collision),
            ("identity_key_aliases", [a for a in aliases if a]),
            ("canonical_name", node.name),
            ("classification", klass),
            ("classification_reason", why),
            ("street", canonical_street(node.street)), ("city", node.city),
            ("state", node.region or corridor_state.get(z, "")),
            ("postal_code", z), ("phone", node.phone),
            ("phone_key", phone_key(node.phone)),
            ("street_identity", address_key(canonical_street(node.street), node.postal)
             if (node.street or "").strip() else ""),
            ("brand", node.brand), ("property_code", node.property_code),
            ("official_url", node.route),
            ("latitude", node.lat), ("longitude", node.lng),
            ("corridor", _corridor),
            ("assignment_basis", _basis),
            ("assignment_value", _key if _basis == "explicit"
                                 else (z if z in zips else "")),
            ("lanes", sorted({o["lane"] for o in node.observations})),
            ("best_tier", min(o["tier"] for o in node.observations)),
            ("policy_state", "POLICY_NOT_VERIFIED"),
            ("policy_note", "Identity evidence never establishes a pet policy."),
            ("evidence", node.observations),
        ]))

    rows.sort(key=lambda r: (r["classification"], r["identity_key"]))
    admitted = [r for r in rows if r["classification"] == TRUE_HOTEL_IDENTITY]
    city_filled, city_unfilled = fill_missing_cities(admitted)
    for r in admitted:
        if not (r.get("city") or "").strip():
            r["classification"] = IDENTITY_REVIEW_REQUIRED
            r["classification_reason"] = ("no municipality stated by any first-party source and the admitted "
                                          "rows in postal code %s name more than one city; a city is never guessed"
                                          % r.get("postal_code"))
            r["identity_state"] = "IDENTITY_UNRESOLVED"
            r["lodging_state"] = "NEEDS_REVIEW"
    renamed = name_bare_identities(admitted)
    counts = Counter(r["classification"] for r in rows)
    confirmed = [r for r in rows if r["classification"] == TRUE_HOTEL_IDENTITY]
    by_corridor = Counter(r["corridor"] for r in confirmed)

    census = OrderedDict([
        ("schema", SCHEMA), ("market_id", MARKET_ID),
        ("status", "PROPOSED_CENSUS_SHADOW_UNTIL_REGISTERED"),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER), ("captured_at", "2026-09-20"),
        ("note",
         "PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 West Palm Beach / Palm Beach County census, "
         "built from zero under the current hardened factory on the Miami-live lineage, REGISTERED by "
         "PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002 (identity_census/). Every row carries the "
         "observations that produced it; nothing here carries a pet policy."),
        ("source_authorities", SOURCE_AUTHORITIES),
        ("count", len(confirmed)),
        ("total_candidates", len(rows)),
        ("classification_counts", OrderedDict(sorted(counts.items()))),
        ("corridor_counts", OrderedDict(sorted(by_corridor.items()))),
        ("hotels", confirmed),
        ("non_admitted", [r for r in rows if r["classification"] != TRUE_HOTEL_IDENTITY]),
    ])

    report = OrderedDict([
        ("schema", REPORT_SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "5 and 8 -- census reconciliation into one identity graph"),
        ("what_decides_an_identity",
         "Street identity (house number + distinctive street words + ZIP), a normalised phone, or a "
         "brand property code inside its own family. Never a name alone, and never a city, "
         "neighbourhood, airport, downtown or directional token. A name match whose addresses "
         "disagree is reported, never merged."),
        ("what_decides_membership",
         "The proposed market contract's postal partition. A row in an unclaimed ZIP is "
         "OUTSIDE_MARKET with its ZIP recorded, so the decision is reviewable."),
        ("this_runs_twice",
         "The pipeline is census -> routing -> capture -> census. The first pass admits what the "
         "map, the destination roster and the owned brand inventories can place; the routing lane "
         "then carries every brand-roster row the first pass could NOT place to its own property "
         "page; and this pass reads the address that page states and feeds it back. A property "
         "code selects a row; only the page admits it."),
        ("lane_yields", OrderedDict((k, len(v)) for k, v in lanes.items())),
        ("observations_total", len(all_obs)),
        ("nodes_after_hard_key_merge", len(nodes)),
        ("name_attachment", OrderedDict([
            ("what_it_is",
             "An observation with no street, no phone and no comparable property code cannot open "
             "a building of its own. It is offered to every building that already has hard "
             "evidence and binds only to a single clear best match, marked "
             "NAME_MATCH_UNCONFIRMED. A tie becomes IDENTITY_REVIEW_REQUIRED; no match stays "
             "NAME_ONLY_UNRESOLVED."),
            ("bound", len(bound)), ("ambiguous", len(ambiguous)), ("unbound", len(unbound)),
            ("bindings", [OrderedDict([("observation_name", s_.name),
                                       ("bound_to", h_.name), ("score", sc)])
                          for s_, h_, sc in bound]),
            ("ambiguous_rows", [OrderedDict([("name", n.name),
                                             ("candidates", n.ambiguous_matches)])
                                for n in ambiguous]),
            ("unbound_rows_with_a_same_brand_candidate", [
                OrderedDict([("name", n.name), ("rejected_candidates", n.rejections)])
                for n in unbound if n.rejections]),
        ])),
        ("classification_counts", OrderedDict(sorted(counts.items()))),
        ("corridor_counts", OrderedDict(sorted(by_corridor.items()))),
        ("bare_chain_flag_renamed", bare_flag_renamed),
        ("bare_chain_flag_rule",
         "A census name that is a BARE CHAIN FLAG is not a premises identity. Because the shared "
         "exclusion registry matches on the normalised canonical name across every market, a bare-flag "
         "row bars identically named hotels elsewhere. Such a row takes the one longer name its own "
         "observations agree on that starts with the flag and adds a place; two different fuller names "
         "are a review, never a coin flip."),
        ("first_party_naming", OrderedDict([
            ("what_it_is",
             "A bare brand label is not an identity. Each such row takes the property's OWN name "
             "from its brand's route slug -- never a name this order invents."),
            ("renamed", renamed),
        ])),
        ("city_backfill", OrderedDict([
            ("what_it_is",
             "A blank city filled from this market's OWN evidence: another admitted row in the "
             "same postal code, or the city segment of the property's own canonical URL. A "
             "brand's marketing NAME is never read as a city."),
            ("filled", city_filled), ("left_blank", city_unfilled),
        ])),
        ("merge_conflicts", merge_conflicts),
        ("same_premises_holds", OrderedDict([
            ("what_this_is", "Rows this order's own first-party read proved to be ONE premises carried as TWO "
                             "census rows, held so one building cannot publish twice and cannot publish under "
                             "an address its own operator contradicts."),
            ("rows", SAME_PREMISES_HOLDS),
            ("never_repaired_here", "The street is never rewritten by this lane; each hold names the exact "
                                    "resolution a registration order should make."),
        ])),
        ("same_name_collision_is_an_in_market_test", OrderedDict([
            ("rule", "The same-name collision test counts ADMITTED-postal nodes only, and ignores nodes the "
                     "brand's own inventory does not list."),
            ("why", "This market's observation set deliberately carries every Broward and Miami-Dade licence "
                    "in a named OUTSIDE postal code so the county boundary audit can count them. Counted in "
                    "the collision test, a generic chain flag in somebody else's market silently HELD a real "
                    "hotel in this one -- the standing rule stated the other way round."),
            ("measured_on_the_first_pass", [
                "Budget Inn, 828 S Dixie Hwy, Lake Worth Beach 33460 -- held by Budget Inns in Pompano Beach "
                "33069 and Miami 33147 (both the LIVE markets' own inventory)",
                "Relax Inn, 7448 Lake Worth Rd 33467 -- held by a Relax Inn in Fort Lauderdale 33316",
                "Super 8 Motel, 757 N US Hwy 1, Juno Beach 33408 -- held by Super 8s in Dania Beach 33004 and "
                "Homestead 33034",
                "Hilton West Palm Beach, 600 Okeechobee Blvd 33401 -- held by an OSM-ONLY pin spelling the "
                "same name at 6000 Okeechobee Boulevard, which Hilton's own city-page card and the DBPR "
                "licence both contradict",
            ]),
            ("a_genuine_in_market_pair_is_still_caught", True),
        ])),
        ("name_bound_codes_detached_by_the_page_code", code_detached),
        ("street_spelling_merge", spelling_merged),
        ("same_name_map_rows_folded_into_a_read_building", neighbour_folded),
        ("destination_roster_merge", destination_merged),
        ("rebrand_holds", REBRAND_HOLDS),
        ("map_rows_superseded_by_a_read", OrderedDict((k, v[1]) for k, v in MAP_ROWS_SUPERSEDED_BY_A_READ.items())),
        ("geography_holds", GEOGRAPHY_HOLDS),
        ("postal_less_street_merge", OrderedDict([
            ("what_it_is",
             "address_key puts the ZIP in the identity key, so a source that prints a street "
             "without a postal code can never meet the same building's row that has one. This "
             "pass closes that gap on street identity alone, and only when exactly one building "
             "matches and the two do not name different cities."),
            ("merged", zipless_merged),
            ("left_ambiguous", zipless_ambiguous),
        ])),
        ("corridors_below_publication_minimum", [
            OrderedDict([("corridor_id", c.corridor_id), ("minimum", c.minimum_hotel_count),
                         ("confirmed_identities", by_corridor.get(c.corridor_id, 0))])
            for c in cfg.corridors if by_corridor.get(c.corridor_id, 0) < c.minimum_hotel_count]),
        ("rows", rows),
    ])
    return census, report, rows, lanes


def gap_matrix(rows, lanes):
    """Phase 6: what the competitor directory has that this census does not."""
    comp = [r for r in rows if "COMPETITOR_LEAD" in r["lanes"]]
    only_comp = [r for r in comp if r["lanes"] == ["COMPETITOR_LEAD"]]
    matched = [r for r in comp if len(r["lanes"]) > 1]
    return OrderedDict([
        ("schema", GAP_SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "6 -- competitor gap matrix"),
        ("a_competitor_row_is_a_lead",
         "A competitor row cannot enter The Palm Beaches authority without first-party identity "
         "confirmation, and a competitor's pet-friendly claim is never policy evidence. This "
         "matrix exists to find identities the free first-party lanes MISSED, not to import a "
         "competitor's inventory."),
        ("counts", OrderedDict([
            ("competitor_rows_observed", len(comp)),
            ("also_seen_by_a_first_party_lane", len(matched)),
            ("competitor_only", len(only_comp)),
            ("competitor_only_by_class",
             OrderedDict(sorted(Counter(r["classification"] for r in only_comp).items()))),
            ("matched_by_class",
             OrderedDict(sorted(Counter(r["classification"] for r in matched).items()))),
        ])),
        ("true_missing_identities_competitor_only", [
            OrderedDict([("canonical_name", r["canonical_name"]), ("street", r["street"]),
                         ("city", r["city"]), ("postal_code", r["postal_code"]),
                         ("phone", r["phone"]), ("classification", r["classification"]),
                         ("reason", r["classification_reason"])])
            for r in only_comp if r["classification"] == TRUE_HOTEL_IDENTITY]),
        ("competitor_only_not_admitted", [
            OrderedDict([("canonical_name", r["canonical_name"]), ("street", r["street"]),
                         ("city", r["city"]), ("postal_code", r["postal_code"]),
                         ("classification", r["classification"]),
                         ("reason", r["classification_reason"])])
            for r in only_comp if r["classification"] != TRUE_HOTEL_IDENTITY]),
        ("matched_rows", [
            OrderedDict([("canonical_name", r["canonical_name"]), ("street", r["street"]),
                         ("postal_code", r["postal_code"]), ("lanes", r["lanes"]),
                         ("classification", r["classification"])])
            for r in matched]),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census-out",
                    default=os.path.join(CENSUS_DIR, "west-palm-beach-fl.json"))
    ap.add_argument("--report-out",
                    default=os.path.join(REPORTS, "west_palm_beach_fl_census_reconciliation_001.json"))
    ap.add_argument("--gap-out",
                    default=os.path.join(REPORTS, "west_palm_beach_fl_competitor_gap_matrix_001.json"))
    args = ap.parse_args(argv)
    census, report, rows, lanes = build()
    gaps = gap_matrix(rows, lanes)
    for path, doc in ((args.census_out, census), (args.report_out, report), (args.gap_out, gaps)):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1)
            fh.write("\n")
    print("lane yields         :", dict(report["lane_yields"]))
    print("observations        :", report["observations_total"])
    na = report["name_attachment"]
    print("nodes (hard-key)    :", report["nodes_after_hard_key_merge"])
    print("name attachment     : bound %d, ambiguous %d, unbound %d" % (na["bound"], na["ambiguous"], na["unbound"]))
    print("classification      :", dict(report["classification_counts"]))
    print("confirmed identities:", census["count"])
    print("merge conflicts     :", len(report["merge_conflicts"]))
    print("competitor-only     :", gaps["counts"]["competitor_only"],
          "of which true hotels:", len(gaps["true_missing_identities_competitor_only"]))
    print("written             :", args.census_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

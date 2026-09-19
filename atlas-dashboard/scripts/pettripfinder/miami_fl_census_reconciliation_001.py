"""PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 -- Phases 9, 11 and 24: one identity graph.

Cloned from the Tampa FL V2 census helper (itself from Orlando V2, Savannah, Boone, Outer Banks and Atlanta), with
Greater Miami's vocabulary. Independent discovery lanes, none authoritative on its own:

  REGISTRY_FL_DBPR    every HOTL / MOTL / BNB public-lodging licence in an admitted or careful-evaluation postal
                      code, from the State of Florida's own licence extract (tier 2: the state's record of the
                      licensed premises -- street, ZIP, licence number, rental units).
  OSM_OVERPASS        tourism=hotel / motel / guest_house / apartment / chalet elements inside the observation box,
                      read from the local Geofabrik Florida extract (ODbL).
  BRAND_INVENTORY     the committed national Marriott harvest (MIA-coded routes); Marriott's Florida hotel sitemap
                      page; Hilton's own Florida city pages (property cards stating each hotel's address); the
                      brands' own sitemaps that answered (Wyndham, Drury, Loews, ESA, Sonesta, InTown, WoodSpring).
  DESTINATION_ORGANIZATION  every /l/hotels/ listing of the Greater Miami CVB (miamiandbeaches.com), JSON-LD cards.
  PROPERTY_PAGE       the address each property's OWN page (or its brand's own property service) states, from the
                      static, Firecrawl and attended passes.
  COMPETITOR_LEAD     names only, from BringFido. Discovery only.

WHAT DECIDES AN IDENTITY
------------------------
Address, postal code, phone or brand property code. Never a name on its own. A DBPR phone is the licensee's line
and, like a map phone, is never a merge key.

WHAT DECIDES MEMBERSHIP
-----------------------
The market contract's postal partition (miami_fl_geography_001). Refused neighbours carry their reason, and a
future-standalone market is named where one is preserved.

VACATION RENTALS, CONDOS, TIMESHARES AND RESORT RESIDENCES ARE NOT HOTELS
--------------------------------------------------------------------------
Miami-Dade, especially Miami Beach, Sunny Isles and Brickell, carries thousands of DBPR condominium (CNDO) and vacation-dwelling (DWEL)
licences; they are counted by the registry lane and never enter this graph. A licence or map row whose own name
reads as a vacation home community, villa / condo rental, resort residence or vacation-ownership club -- and that
no brand's public hotel inventory and no hotel page read reached -- is NON_LODGING with a VACATION_RENTAL /
TIMESHARE / RESORT_RESIDENCE reason (miami_fl_nonhotel_rulings_001).

SHADOW UNTIL REGISTERED
-----------------------
Written to identity_census_proposed/, never identity_census/.

Nothing here fetches. Nothing here carries a pet policy.

Outputs:
  launch_packages/pettripfinder/identity_census_proposed/miami-fl.json
  launch_packages/pettripfinder/markets/reports/miami_fl_census_reconciliation_001.json
  launch_packages/pettripfinder/markets/reports/miami_fl_competitor_gap_matrix_001.json
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
from scripts.pettripfinder import miami_fl_geography_001 as GEO  # noqa: E402

#: Admitted-ZIP rows whose MUNICIPALITY cannot be decided from a first-party page, in a postal code the
#: geography shares with a refused municipality. Held, never admitted by the map's city label. Empty at
#: authoring time.
GEOGRAPHY_HOLDS = {}

WORK_ORDER = "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "miami-fl"
SCHEMA = "ptf-market-identity-census/1.1"
REPORT_SCHEMA = "ptf-census-reconciliation/1.0"
GAP_SCHEMA = "ptf-competitor-gap-matrix/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")

REPORTS = os.path.join(PKG, "markets", "reports")
#: SHADOW UNTIL REGISTERED: the census is written to the market zone's proposed census path. The later
#: registration order copies it into identity_census/.
CENSUS_DIR = os.path.join(PKG, "identity_census_proposed")
CONTRACT_PATH = os.path.join(PKG, "markets", "proposed", "miami-fl.json")

OSM_LANE = os.path.join(REPORTS, "miami_fl_osm_lane_001.json")
BRAND = os.path.join(REPORTS, "miami_fl_brand_inventory_001.json")
ATTENDED_PASS = os.path.join(REPORTS, "miami_fl_policy_reads_001.json")
DESTINATION = os.path.join(REPORTS, "miami_fl_destination_roster_001.json")
DBPR_LANE = os.path.join(REPORTS, "miami_fl_dbpr_lane_001.json")

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

from scripts.pettripfinder.miami_fl_nonhotel_rulings_001 import NOT_LODGING_WHY, LODGING_UNCONFIRMED, nonhotel_by_name  # noqa: E402
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
    # MIAMI: the Miami-Dade grid is spelled both "NW 36 St" and "Northwest 36th Street"; the shared key drops
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


#: A house number followed directly by a bare numbered street ("300 17 St", Miami Beach's own grid).
_BARE_NUMBERED = re.compile(r"^(\s*\d+[a-z]?\s+)(\d+)(?:st|nd|rd|th)?(?=\s+(?:st|street|ave|avenue|ct|court|ter|terr|"
                            r"terrace|pl|place|rd|road|dr|drive|way|ln|lane)\b)", re.I)


def _ordinal(n):
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suffix)


def canonical_street(street):
    """MIAMI: the census states a Miami-Dade grid street the way a property's own page writes it ("2601 NW 42nd
    Ave"), whether the licence abbreviated it ("2601 Nw 42 Ave") or the map spelled it out ("2601 Northwest 42nd
    Avenue"): quadrant abbreviated and upper-cased, the numbered street given its ordinal. Nothing else changes.
    The shared identity gate keeps "42nd" and drops a bare "42", so an unordinalised licence spelling would refuse
    the property's own page for a spelling, not a building."""
    if not street:
        return street
    s = _GRID.sub(lambda m: "%s %s" % (_QUADRANT[m.group(1).lower()], _ordinal(m.group(2))), street)
    return _BARE_NUMBERED.sub(lambda m: "%s%s" % (m.group(1), _ordinal(m.group(2))), s)


def _merge_spelling(street):
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
        # MIAMI: a card must state Florida AND a South Florida postal prefix (330-332 Miami-Dade, 333 Broward for the
        # boundary audit) to be a lead of this box at all.
        if state_code(card.get("state")) != "FL":
            continue
        if (card.get("postal_code") or "")[:3] not in (
                "330", "331", "332", "333"):
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
    _disc = (_load(os.path.join(REPORTS, "miami_fl_firecrawl_discovery_001.json"), {}) or {}).get("routes", [])
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
    or map row into a Miami identity."""
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


from scripts.pettripfinder.miami_fl_static_rulings_001 import (  # noqa: E402
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
    (re.compile(r"\bac hotel miami brickell\s*&\s*element miami brickell\b", re.I),
     "one DBPR licence / bureau listing names two Marriott hotels (AC Hotel Miami Brickell and Element Miami Brickell) "
     "at 115 SW 8th St; each needs its own MARSHA code and page before either is published"),
    (re.compile(r"\beden roc miami beach\s*&\s*nobu hotel miami beach\b", re.I),
     "one DBPR licence / bureau listing names two hotels (Eden Roc Miami Beach and Nobu Hotel Miami Beach) at 4525 "
     "Collins Ave; each needs its own operator page before either is published"),
]

#: A second row naming ONE building of an establishment that another census row already carries under the licence
#: that covers the whole premises. Keyed on the normalised name; each read from the evidence before it was added.
DUPLICATE_OF = {
    "dorset hotel": ("DUPLICATE_LISTING -- a map row for the Dorset building at 1720 Collins Avenue, which the DBPR "
                     "licence 'Catalina Hotel / Dorset Hotel / Maxine Hotel' (1720-1756 Collins Avenue, buildings "
                     "1720, 1732, 1756) already carries as one licensed establishment"),
}


def read_destination_roster():
    """The Greater Miami CVB's hotel roster: tier-2 discovery and identity evidence.

    The roster report nests listings under ``bureaus`` (the GMCVB, plus the Miami Beach marketing sites probed and
    recorded with no roster); every bureau's own ``listings`` are pooled here.
    """
    doc = _load(DESTINATION, {}) or {}
    listings = []
    for bureau in (doc.get("bureaus") or {}).values():
        listings.extend(bureau.get("listings") or [])
    read_routes = {_route_key(r.get("requested_url") or "")
                   for r in (_load(ATTENDED_PASS, {}) or {}).get("rows", [])
                   if r.get("identity_confirmed")}
    out = []
    for r in listings:
        if not (r.get("name") or "").strip():
            continue
        joined = _route_key(r.get("website") or "") in read_routes
        out.append(observation(
            "DESTINATION_ORGANIZATION", 2, r["listing_url"], r["name"],
            street="" if joined else r.get("street", ""), city=r.get("city", ""), region=state_code(r.get("region")),
            stated_postal_code=r.get("stated_postal_code"), stated_phone=r.get("stated_phone"),
            website_url=r.get("website"),
            route=r.get("website") if joined else "",
            joins_read_route=joined,
            document_sha256=r.get("document_sha256"),
            bureau_subcategory=r.get("bureau_subcategory"),
            bureau_all_subcategories=r.get("bureau_all_subcategories"),
            lat=r.get("lat"), lng=r.get("lng"),
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


PLACES_REPORT = os.path.join(REPORTS, "miami_fl_places_route_discovery_001.json")
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
    """MIAMI: the Florida DBPR public-lodging licence registry -- tier 2 identity and eligibility evidence."""
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
#: building is in.
_IN_MARKET_MUNICIPALITIES = {
    "miami", "miami beach", "south beach", "mid beach", "north beach", "brickell", "downtown miami", "doral",
    "coral gables", "coconut grove", "miami springs", "virginia gardens", "key biscayne", "aventura",
    "sunny isles", "sunny isles beach", "bal harbour", "surfside", "bay harbor islands", "north miami",
    "north miami beach", "north bay village", "hialeah", "hialeah gardens", "miami lakes", "kendall",
    "south miami", "homestead", "florida city", "cutler bay", "miami gardens", "opa locka", "sweetwater",
    "medley", "pinecrest", "palmetto bay", "miami shores", "el portal", "west miami", "wynwood", "edgewater",
    "little havana", "fisher island",
}
#: Refused places that preserve a named future standalone market.
_FUTURE_SUBMARKET_PLACES = {"fort lauderdale", "ft lauderdale", "hollywood", "hallandale", "hallandale beach",
                            "dania", "dania beach", "pompano beach", "deerfield beach", "lauderdale by the sea",
                            "boca raton", "west palm beach", "palm beach", "key largo", "islamorada", "marathon",
                            "key west", "miramar", "pembroke pines", "davie", "plantation", "sunrise",
                            "weston", "lauderhill", "tamarac", "coral springs"}
_OUT_OF_MARKET_PLACES = set(_FUTURE_SUBMARKET_PLACES)
_ALL_PLACES = _IN_MARKET_MUNICIPALITIES | _OUT_OF_MARKET_PLACES
#: Place words that are ALSO chain or naming vocabulary: a place phrase still names the town, but its words are
#: never stripped from a name's chain vocabulary.
_PLACE_WORDS_KEPT_IN_CHAIN = {"garden", "park", "springs", "harbor", "beach", "gardens", "lakes", "shores"}
_DIRECTIONALS = {
    "north", "south", "east", "west", "northwest", "northeast", "southwest", "southeast",
    "village", "bypass", "area", "near", "blvd", "road", "rd", "center", "downtown",
    # MIAMI area words that tell same-brand hotels apart (Courtyard Downtown / Airport / Coral Gables / Dadeland)
    "airport", "brickell", "beach", "mid", "oceanfront", "bayfront", "bay", "blue", "lagoon", "doral", "dadeland",
    "kendall", "gables", "grove", "wynwood", "edgewater", "midtown", "design", "district", "port", "cruise",
    "international", "mall", "aventura", "sunny", "isles", "hialeah", "springs", "lakes", "gardens", "stadium",
    "coconut", "coral", "key", "biscayne", "convention", "river", "collins", "ocean", "central", "university",
    "fiu", "civic", "health", "waterfront", "harbor", "marina", "cityplace",
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
    "downtown-brickell": {"miami", "brickell", "downtown miami"},
    "south-beach": {"miami beach", "south beach", "fisher island", "miami"},
    "mid-beach": {"miami beach", "mid beach"},
    "north-beach": {"miami beach", "north beach", "north bay village"},
    "mia-airport-miami-springs": {"miami", "miami springs", "virginia gardens", "doral", "medley"},
    "airport-west-blue-lagoon": {"miami", "west miami"},
    "doral": {"doral", "miami", "sweetwater", "medley"},
    "coral-gables": {"coral gables", "miami", "south miami"},
    "coconut-grove": {"miami", "coconut grove"},
    "midtown-wynwood-edgewater": {"miami", "miami shores", "el portal", "wynwood", "edgewater"},
    "little-havana": {"miami", "little havana"},
    "key-biscayne": {"key biscayne", "miami"},
    "bal-harbour-surfside": {"bal harbour", "surfside", "bay harbor islands", "miami beach"},
    "sunny-isles-beach": {"sunny isles beach", "sunny isles", "north miami beach", "miami beach", "miami"},
    "aventura": {"aventura", "miami", "north miami beach"},
    "north-miami": {"north miami", "north miami beach", "miami"},
    "hialeah-miami-lakes": {"hialeah", "hialeah gardens", "miami lakes", "miami"},
    "miami-gardens-opa-locka": {"miami gardens", "opa locka", "miami"},
    "kendall-south-dade": {"miami", "kendall", "cutler bay", "pinecrest", "palmetto bay", "south miami"},
    "homestead-florida-city": {"homestead", "florida city"},
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


#: A map-only row under a flag whose own Miami-area route on the brand's site is RETIRED. Empty at authoring time.
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
            "a map row under a flag (%s) whose own Miami-area route on the brand's site is "
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
    # REFUSED NEIGHBOURS BY PIN. A row with NO postal code of its own that every source pins north of the
    # Miami-Dade / Broward county line (lat > 25.978) or south of Florida City into the Keys (lat < 25.39) cannot be
    # an admitted identity whatever else is unknown about it.
    _pins = [(o.get("lat"), o.get("lng")) for o in node.observations
             if o.get("lat") is not None and o.get("lng") is not None]
    if not node.postal and _pins and all(float(t) < 25.39 or float(t) > 25.978 for t, g in _pins):
        return OUTSIDE_MARKET, ("no postal code of its own, and every source pins it beyond the admitted corridors "
                                "(Broward County north or the Florida Keys south; %.4f, %.4f)"
                                % (float(_pins[0][0]), float(_pins[0][1])))
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
        return OUTSIDE_MARKET, ("%s postal code %s is claimed by no corridor of the Greater Miami "
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


#: Brand families whose OWN Miami-area inventory this order read. Families whose inventory refused this
#: client are NOT listed: a map row under their flag is not demoted for a read that never happened.
_COVERED_FLAGS = (
    ("HILTON", r"\b(hampton|hilton|home2|homewood|embassy suites|doubletree|spark by hilton|tru by hilton|tempo|signia|waldorf)\b"),
    ("MARRIOTT", r"\b(courtyard|residence inn|fairfield|springhill|towneplace|aloft|element|westin|sheraton|four points|ac hotel|marriott|moxy|gaylord|ritz)\b"),
    ("WYNDHAM", r"\b(days inn|super 8|baymont|la quinta|wingate|microtel|travelodge|ramada|howard johnson|hawthorn|tryp)\b"),
)


def brand_not_listed(node):
    lanes = {o.get("lane") for o in node.observations}
    # MIAMI: the brand inventories this order could read are PARTIAL (Hilton city pages carry the twenty nearest
    # cards; Marriott's Florida sitemap omits Ritz-Carlton and several Doral / airport flags). An ACTIVE DBPR licence
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
            return ("a %s row naming a %s flag (%r) that no read of that brand's own Miami-area inventory "
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
    "https://www.miamiandbeaches.com/l/hotels/ listings (the Greater Miami CVB's own sitemap and listing JSON-LD)",
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

    name_counts = Counter((normalize_name(n.name), "") for n in nodes
                          if n.street or n.phone)
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
        ("work_order", WORK_ORDER), ("captured_at", "2026-09-19"),
        ("note",
         "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 Miami census, built from zero under the current hardened "
         "factory, SHADOW UNTIL REGISTERED (identity_census_proposed/). Every row carries the observations that "
         "produced it; nothing here carries a pet policy."),
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
         "A competitor row cannot enter Greater Miami authority without first-party identity "
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
                    default=os.path.join(CENSUS_DIR, "miami-fl.json"))
    ap.add_argument("--report-out",
                    default=os.path.join(REPORTS, "miami_fl_census_reconciliation_001.json"))
    ap.add_argument("--gap-out",
                    default=os.path.join(REPORTS, "miami_fl_competitor_gap_matrix_001.json"))
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

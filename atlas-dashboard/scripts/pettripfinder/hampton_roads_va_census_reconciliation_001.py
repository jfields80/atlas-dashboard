"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- Phases 5-9: one identity graph.

Cloned from the Charleston SC census helper (itself from Savannah GA, Boone - Blowing Rock NC and Atlanta GA).
Independent discovery lanes, none authoritative on its own:

  OSM_OVERPASS        tourism=hotel / motel / guest_house / apartment / chalet elements
                      inside the observation box, read from the local Geofabrik Virginia
                      extract (ODbL).
  BRAND_INVENTORY     the committed national Marriott harvest (RIC-coded routes);
                      Marriott's Virginia hotel sitemap page; Hilton's own Virginia
                      city pages (property cards stating each hotel's address);
                      Wyndham's, Drury's and WoodSpring's own sitemaps.
  DESTINATION_ORGANIZATION  every lodging listing of the Hampton Roads city bureaus this order could read
                      (Visit Virginia Beach, Visit Chesapeake, Visit Newport News), with each bureau's own sub-categories.
  PROPERTY_PAGE       the address each property's OWN page (or its brand's own
                      property service) states, from the attended and static passes.
  COMPETITOR_LEAD     names only, from search-result summaries of competitor lists.

WHAT DECIDES AN IDENTITY
------------------------
Address, postal code, phone or brand property code. Never a name on its own.

WHAT DECIDES MEMBERSHIP
-----------------------
The market contract's postal partition (hampton_roads_va_geography_001). Petersburg,
Colonial Heights, Hopewell and Prince George are OUTSIDE and every such row carries
the future-market reason so the later petersburg-tri-cities-va order starts from it.

APARTMENTS, CORPORATE HOUSING, STUDENT HOUSING AND SHORT-TERM RENTALS ARE NOT HOTELS
-----------------------------------------------------------------------------------
Hampton Roads carries substantial oceanfront condo-hotels, timeshare clubs, vacation-rental companies,
beach houses, campgrounds and military lodging. None is admitted: a row whose only
typing evidence is a campground or RV park, or a map apartment / chalet tag is
NON_LODGING; named rental companies, apartment inventory and venues are refused BY
NAME with the reason
(hampton_roads_va_nonhotel_rulings_001).

SHADOW UNTIL REGISTERED
-----------------------
Written to identity_census_proposed/, never identity_census/.

Nothing here fetches. Nothing here carries a pet policy.

Outputs:
  launch_packages/pettripfinder/identity_census_proposed/hampton-roads-va.json
  launch_packages/pettripfinder/markets/reports/hampton_roads_va_census_reconciliation_001.json
  launch_packages/pettripfinder/markets/reports/hampton_roads_va_competitor_gap_matrix_001.json
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
from scripts.pettripfinder import hampton_roads_va_geography_001 as GEO  # noqa: E402

#: Admitted-ZIP rows whose MUNICIPALITY cannot be decided from a first-party page,
#: in a postal code the geography shares with a refused municipality. Held, never
#: admitted by the map's city label.
GEOGRAPHY_HOLDS = {
    "red roof inn newport news yorktown": (
        "Red Roof's own property record for rri826 (attended browser, sha256 4d5932ec... payload) states the city 'Newport News' beside postal code 23692, which is York County (Yorktown); the brand's own route files it under /va/yorktown/. One of the two first-party facts is wrong and the ZIP alone never decides which"),
}

WORK_ORDER = "PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hampton-roads-va"
SCHEMA = "ptf-market-identity-census/1.1"
REPORT_SCHEMA = "ptf-census-reconciliation/1.0"
GAP_SCHEMA = "ptf-competitor-gap-matrix/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")


def _first_existing(*paths):
    """The registered path if this market has been promoted, else the proposed one."""
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[-1]


REPORTS = os.path.join(PKG, "markets", "reports")
#: SHADOW UNTIL REGISTERED: the census is written to the market zone's proposed
#: census path. The later registration order copies it into identity_census/.
CENSUS_DIR = os.path.join(PKG, "identity_census_proposed")
CONTRACT_PATH = _first_existing(os.path.join(PKG, "markets", "hampton-roads-va.json"),
                                os.path.join(PKG, "markets", "proposed", "hampton-roads-va.json"))
PROPOSED_CONTRACT = os.path.join(REPORTS, "hampton_roads_va_corridor_registry_001.json")

OSM_LANE = os.path.join(REPORTS, "hampton_roads_va_osm_lane_001.json")
BRAND = os.path.join(REPORTS, "hampton_roads_va_brand_inventory_001.json")
ATTENDED_PASS = os.path.join(REPORTS, "hampton_roads_va_attended_capture_001.json")
DESTINATION = os.path.join(REPORTS, "hampton_roads_va_destination_roster_001.json")
#: CHARLESTON: the market-local reading of the static lane's own-site JSON-LD addresses (identity only).
STATIC_LANE = os.path.join(REPORTS, "hampton_roads_va_static_lane_001.json")
POLICY_PAGES_LANE = os.path.join(REPORTS, "hampton_roads_va_policy_pages_lane_001.json")

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

#: Names that are not lodging even though a lead source lists them. Every one is
#: matched on the full normalised name, never on a substring, so "Sunshine
#: Studios" can never retire "Studio 6".
#: Why each NON_LODGING name is refused -- written down so a refusal is a decision.
#: Outer Banks map and bureau rows include vacation-ownership resorts, condo
#: complexes, cottage collections and realty rental offices.
from scripts.pettripfinder.hampton_roads_va_nonhotel_rulings_001 import (  # noqa: E402
    NOT_LODGING_WHY, LODGING_UNCONFIRMED, RESORT_COMPLEX_IDENTITY, COMPONENT_OF)
NOT_LODGING_NAMES = set(NOT_LODGING_WHY)
NON_HOTEL_LEAD_TYPES = {"Campground"}
#: The bureau's own Lodging sub-categories that are NOT hotel establishments. A row
#: whose ONLY typing evidence is one of these (no brand roster, no property page) is
#: NON_LODGING under the vacation-rental rule.
NON_HOTEL_BUREAU_SUBCATEGORIES = {
    # the bureau's own spelling, as its category page is titled
    "Vacation Rentals", "Cottages", "Apartments", "Corporate Housing",
    # defensive spellings of the same categories
    "Vacation Rental Companies", "Campgrounds", "RV Parks", "Real Estate", "Timeshares",
}
#: Visit Savannah files a listing under several categories. The vacation-rental rule reads
#: EVERY category the bureau gives a listing: one that carries none of the bureau's hotel-type
#: categories and carries "Vacation Rentals" is not a hotel establishment on the bureau's own
#: typing ("Extended Stay" and "Places to Stay" type nothing on their own).
HOTEL_BUREAU_SUBCATEGORIES = {"Hotels", "Bed & Breakfasts", "Historic Inns", "Extended Stay", "Downtown Hotel",
                              "North Hotel", "South Hotel", "West Hotel", "Full Service Hotel",
                              # HAMPTON ROADS bureaus' own hotel-type sub-categories (Visit Virginia Beach CRM, Visit
                              # Chesapeake, Visit Newport News)
                              "Hotels & Resorts", "Hotels Near Convention Center", "Motel", "Bed & Breakfast",
                              "Limited Service", "Full Service", "All Suites", "Places to Stay"}
NON_HOTEL_BUREAU_SUBCATEGORIES |= {"Beach Vacation Homes", "Condo Rentals", "Camping & Cabins", "Campground",
                                   "Group Lodging"}
#: A bureau listing typed only "Places to Stay" whose own name is a campground, RV park or park.
_CAMPGROUND_NAME = re.compile(r"\b(rv|campground|camping|state park|kampground)\b", re.I)
STR_PLACEHOLDERS = set()

#: Government / institutional lodging refused by name. Greenville has none in the
#: evidence (ECU's campus housing is student housing, never listed by any lane);
#: the mechanism stays so a later row is refused by decision, not by accident.
MILITARY_NONPUBLIC_NAMES = {}
#: HAMPTON ROADS: the military lodging rule, by the lodging programme's own name. Navy Gateway Inns & Suites, IHG Army
#: Hotels, Air Force Inns and installation transient quarters require installation access or military / DoD
#: eligibility; none is admitted without proof of ordinary public booking, and no lane in this order supplied one.
_MILITARY_LODGING = re.compile(
    r"\b(navy gateway|ngis|army hotels?|air force inns?|afi\b|bayview inns?|transient (?:quarters|lodging)|"
    r"unaccompanied housing|bachelor (?:officer|enlisted) quarters|military lodging|fort eustis lodging|navy lodges?)\b", re.I)

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
    # SAVANNAH: an apostrophe is typography ("115 O'Leary Road" on the brand's page, "115 Oleary Road"
    # on the map); it is folded before the shared key is taken, for both spellings alike.
    return address_key((street or "").replace("'", "").replace("\u2019", ""), postal or "")


#: SAVANNAH: the shared ``address_key`` drops street directionals, so "201 E. Bay St." (Hampton Inn)
#: and "201 West Bay Street" (Hotel Indigo), or "11 Gateway Boulevard East" (Holiday Inn) and "11 West
#: Gateway Boulevard" (TownePlace Suites), are one key -- and in Savannah's grid they are different
#: buildings on opposite sides of Bull Street or of the interchange. The MERGE refuses to join two
#: streets whose own directionals disagree. A street with no directional agrees with either ("4701 US
#: Highway 17 S" and "4701 US-17"). The shared key itself is never changed.
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
        # THE ADDRESS THE PROPERTY'S OWN PAGE STATES WINS. A map source writes
        # "222 E 3rd St" where the hotel writes "222 East Third Street"; both
        # are the same building and neither is wrong, but only one of them is
        # what the operator publishes, and the capture lane keys its reads on
        # it. Letting whichever lane arrived first own the street made eleven
        # already-read Raleigh hotels unjoinable to their own reads the
        # moment the OpenStreetMap lane was folded in. A tier-1 property-page
        # observation therefore OVERWRITES the postal address; every other lane
        # only fills a blank.
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
        # The longest name wins: "Courtyard by Marriott Raleigh SouthPark"
        # is a better display identity than the map source's bare "Courtyard",
        # and a bare brand label collides across markets.
        if len(obs.get("name") or "") > len(self.name):
            self.name = obs["name"]


#: An HTML entity that reached a NAME. A Firecrawl read of a Holiday Inn
#: Express returned "Holiday Inn Express &amp; Suites", and ``normalize_name``
#: turned that into the identity key "holiday inn express andamp suites" -- a
#: key no other lane can ever meet, so the same building opened a second row.
#: Decoding is done once, at the door, so every lane's names are comparable.
def _decode_entities(text):
    import html
    t = html.unescape(html.unescape(text or ""))
    # A trademark sign is typography, not a name: ARRIVE's own page writes
    # "Design Hotels\u2122", and the identity-key contract spells it "tm" where
    # normalize_name drops it, so the two keys would disagree.
    t = t.replace("\u2122", "").replace("\u00ae", "")
    # Atlanta: a diacritic is typography too. The census contract keys on ptf_identity_key
    # ("le meridien") while the shared registration join keys on normalize_name ("le m ridien"),
    # so an accented name would fail closed at registration. Folding it at the door keeps
    # both keys identical ("Le Méridien" -> "Le Meridien").
    import unicodedata
    t = "".join(ch for ch in unicodedata.normalize("NFKD", t) if not unicodedata.combining(ch))
    return t.replace("\u00a0", " ").strip()


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
        # THE PROPERTY'S OWN ADDRESS BEATS THE MAP'S. The map's Days Inn row
        # writes one street beside a website that IS the brand route this order
        # read, whose Hotel JSON-LD states another spelling of the same building. Keyed on its own street the map row would open a second
        # building for one hotel. When the map row's website is EXACTLY a route
        # whose own page was read, the row joins that read by the route and its
        # map street is kept only as a superseded note.
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
    r"wyndhamhotels\.com/([a-z0-9-]+)/([a-z-]+)-virginia/([a-z0-9-]+)/overview",
    re.I)


def _titlecase(slug):
    return " ".join(w.capitalize() for w in (slug or "").replace("-", " ").split())


#: A US state, however a first-party page happens to spell it. Marriott's
#: Hotel JSON-LD writes ``addressRegion: "Tennessee"``; Hilton's __NEXT_DATA__
#: writes ``state: "TN"``. Truncating to two characters turns the first into
#: "TE", which no state code matches -- and the membership rule then reads that
#: as AFFIRMATIVE evidence that the property is in another state. Twenty real
#: Raleigh hotels were classified OUTSIDE_MARKET by exactly that before this
#: existed. A spelling is not a fact about geography.
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
    """The two-letter code for a state a first-party page named, or "".

    Returns "" -- not a guess -- for anything it does not recognise, because
    membership treats an unrecognised state as evidence of being elsewhere and
    an empty one as no evidence at all. Missing evidence is not contrary
    evidence.
    """
    v = (value or "").strip()
    if not v:
        return ""
    if len(v) == 2 and v.isalpha():
        return v.upper()
    return _STATE_CODE.get(v.lower(), "")


def _brand_doc():
    return _load(BRAND, {}) or {}


def read_brand_owned():
    """Rung 0. The committed national brand harvest, read at zero requests.

    A row here NAMES a property and gives its canonical first-party route. It
    admits nothing: an RDU property code is the Raleigh-Durham AIRPORT code and
    reaches Durham and Chapel Hill as readily as Cary.
    """
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


#: Words a brand puts in a route slug that name the CHAIN, the state or the
#: page rather than the property. Stripped before a slug becomes a name.
#: "north" and "south" are NOT noise in this market -- North Hills, North
#: Raleigh, Raleigh North and South Hills are all real distinguishing area
#: words -- so only the state's own tokens are stripped.
_SLUG_NOISE = {"hotels", "hotel", "overview", "index", "en", "us",
               "va", "virginia"}


def _name_from_route(url):
    """A proposed NAME from a brand's own property route slug.

    A slug is a first-party identifier for the property, so it may NAME a row
    whose roster entry carried no name. It never decides WHERE the building is:
    the address the property's own page states does that, one lane later.
    """
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    if tail in ("overview", "hoteldetail", "index.html"):
        parts = url.rstrip("/").split("/")
        tail = parts[-2] if len(parts) > 1 else tail
    tail = re.sub(r"[.](html?|aspx)$", "", tail)
    words = [w for w in tail.replace("_", "-").split("-")
             if w and w.lower() not in _SLUG_NOISE and not w.isdigit()]
    if words and re.fullmatch(r"[a-z0-9]{6,8}", words[0].lower()) and any(
            ch.isdigit() for ch in words[0]):
        words = words[1:]          # a Hilton route leads with its property code
    return _titlecase("-".join(words))


def read_brand_city_pages():
    """Hilton's coded roster, read from the brand's OWN Georgia (and two observed South Carolina) city pages.

    Tier-1 ROUTING and IDENTITY evidence. Not policy, and not an admission: the
    route is captured so the property's OWN page can state its address. Hilton
    publishes a Raleigh city page and a Durham city page; a code found on either
    is a lead, and the postal code on the property's page decides which market
    it belongs to -- or whether it belongs to neither.
    """
    out = []
    for r in _brand_doc().get("leads", []):
        if r.get("lane") != "BRAND_CITY_PAGE":
            continue
        card = r.get("brand_card") or {}
        # OUTER BANKS: the plain client's city page also carries property codes from the
        # brand's national navigation (Kansas and Nebraska hotels). A code whose own
        # structured card does not state North Carolina is not a lead at all.
        # SAVANNAH: the city page's national navigation also lists north-Georgia hotels (Dalton,
        # Calhoun, Canton) and a Murphy NC one. A card must state Georgia or South Carolina AND a
        # coastal postal prefix (313xx / 314xx Savannah-Hinesville, 304xx Statesboro, 299xx
        # Lowcountry SC) to be a lead of this market's observation box at all.
        if state_code(card.get("state")) not in ("VA",):
            continue
        # HAMPTON ROADS: 233xx Chesapeake / Suffolk / Smithfield, 234xx Virginia Beach, 235xx Norfolk, 236xx Hampton /
        # Newport News / Yorktown, 237xx Portsmouth, 231xx the observed Williamsburg / Gloucester neighbours.
        if (card.get("postal_code") or "")[:3] not in ("231", "233", "234", "235", "236", "237"):
            continue
        name = card.get("name") or _name_from_route(r["route"])
        if not name:
            continue
        # Atlanta: Hilton's own city page serves each property's structured card
        # (name, street, city, state, postal code, phone, pin). That is the brand's
        # own address data, tier 1, so an unread property still gets an address
        # and an out-of-market property is classified on its own postal code.
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
    """Marriott's own Georgia hotel sitemap page: MARSHA code, title and route."""
    out = []
    for r in _brand_doc().get("leads", []):
        if r.get("lane") != "BRAND_STATE_SITEMAP_PAGE":
            continue
        # SAVANNAH: the lane's title match read "gateway" and "riverfront" as leads, which admitted
        # Atlanta Airport Gateway and Bainbridge Riverfront titles. A row is a lead only when its
        # MARSHA code is SAV-prefixed or its own title names a place this market knows.
        if not ((r.get("property_code") or "").lower().startswith(("orf", "phf")) or places_in(r.get("brand_title") or "")):
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


#: A brand sitemap route that names ONE property: Wyndham's en-us overview page,
#: Locale duplicates, rooms-rates and
#: meetings subpages, and city / airport / university index pages are not.
_PROPERTY_ROUTE = re.compile(
    r"wyndhamhotels\.com/(?![a-z]{2}-[a-z]{2}/)[a-z0-9-]+/[a-z-]+-virginia/[a-z0-9-]+/overview$",
    re.I)


def read_brand_sitemaps():
    """Property routes read from a brand's OWN sitemap -- tier 1 routing evidence.

    Rung 2 of the brand inventory. Like every roster row it NAMES a property and
    routes to it, and admits nothing: the postal code the property's own page
    states decides membership.
    """
    out = []
    attended = _load(ATTENDED_PASS, {}) or {}
    # This market's capture report records the retired routes as FULL URLs.
    retired = {p if p.startswith("http") else "https://www.wyndhamhotels.com" + p
               for p in attended.get("wyndham_retired_routes", [])}
    for r in _brand_doc().get("leads", []):
        if r.get("lane") != "BRAND_SITEMAP":
            continue
        route = r["route"]
        if route in retired or not _PROPERTY_ROUTE.search(route):
            continue
        _city = _WYNDHAM_URL_CITY.search(route)
        if _city and _city.group(1).replace("-", " ") not in _ALL_PLACES:
            continue
        name = _name_from_route(r["route"])
        if not name:
            continue
        out.append(observation(
            "BRAND_INVENTORY_SITEMAP", 1, r["route"], name,
            brand=r["family"], route=r["route"], merge_alias=normalize_name(name),
            admitted_by="ROUTE_READ_FROM_THE_BRAND_OWN_SITEMAP",
            seen_in=r.get("found_in", ""),
            document_sha256=r.get("found_in_sha256"),
        ))
    return out


def read_property_pages():
    """The address a property's OWN page states -- tier 1, and the only thing
    allowed to turn a brand-roster or map row into a Greenville identity."""
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


#: Identity-only reads: properties whose OWN site states their address but not a
#: pet policy. They open or confirm a building; they carry no policy.
from scripts.pettripfinder.hampton_roads_va_static_rulings_001 import (  # noqa: E402
    IDENTITY_ONLY_PAGES, COMPETITOR_LEADS, REGIONAL_VISITOR_CENTER_LEADS, REGIONAL_VISITOR_CENTER_SOURCE)


def read_identity_only_pages():
    out = []
    for name, street, city, postal, phone, url, _sha, note in IDENTITY_ONLY_PAGES:
        out.append(observation(
            "PROPERTY_PAGE_IDENTITY_ONLY", 1, url, name, street=street, city=city, region="VA",
            postal=postal, phone=phone, route=url, binding_method="ADDRESS_ON_THE_PROPERTYS_OWN_SITE",
            identity_note=note))
    return out


#: Map rows whose building the property's OWN site names differently today, joined
#: to that read by its route. The label on the map is kept as evidence.
MAP_ROWS_SUPERSEDED_BY_A_READ = {
}

#: One building, two trade names, and NO first-party page read to say which is
#: current. Keyed on the ZIP-free street identity. A founder / later-order ruling.
REBRAND_HOLDS = {}

#: CHARLESTON: the Charleston Area CVB states no postal code, so an independent the bureau lists and the map never
#: addressed could never be placed. The static and policy-page lanes persist each property's OWN site; when a
#: document that site served carries a schema.org lodging JSON-LD address with a street AND a postal code, that is
#: the property's own first-party statement of where it is. It opens or confirms a building (identity only, no
#: policy). A JSON-LD block of a non-lodging type (Organization, LocalBusiness of a management company) never counts.
_LODGING_LD_TYPES = re.compile(r"hotel|lodging|motel|inn|resort|bedandbreakfast|hostel", re.I)


def read_static_identity_pages():
    out, seen = [], set()
    docs = []
    for r in (_load(STATIC_LANE, {}) or {}).get("rows", []):
        if r.get("status") == 200:
            docs.append((r.get("final_url") or r["url"], r.get("sha256"), r.get("jsonld_addresses") or []))
    for s in (_load(POLICY_PAGES_LANE, {}) or {}).get("rows", []):
        for p in s.get("pages") or []:
            if p.get("status") == 200:
                docs.append((p.get("final_url") or p["url"], p.get("sha256"), p.get("jsonld_addresses") or []))
    # RICHMOND: a site whose own policy document this order already bound in the capture pass (brand_pages) is identified
    # by that read. Its JSON-LD block may spell the same building differently ("1600 Robinhood Road, 23220" beside the
    # page's "1600 Robin Hood Road") and would open a second building for one hotel.
    from urllib.parse import urlparse as _up
    read_hosts = {(_up(r.get("final_url") or r.get("requested_url") or "").netloc.lower().replace("www.", ""),
                   ((r.get("identity_signals") or {}).get("address_on_page") or "").split(" ")[0],
                   ((r.get("identity_signals") or {}).get("postal_code") or "")[:5])
                  for r in (_load(ATTENDED_PASS, {}) or {}).get("rows", []) if r.get("brand_page_seed")}
    for url, sha, addrs in docs:
        if any(d in (url or "") for d in _NOT_OWN_SITE):
            continue
        _host = _up(url or "").netloc.lower().replace("www.", "")
        for a in addrs:
            _pz = re.sub(r"[^0-9]", "", str(a.get("postal") or ""))[:5]
            if (_host, (a.get("street") or "").strip().split(" ")[0], _pz) in read_hosts:
                continue
            if not _LODGING_LD_TYPES.search(json.dumps(a.get("type"))):
                continue
            street = (a.get("street") or "").strip()
            postal = re.sub(r"[^0-9]", "", str(a.get("postal") or ""))[:5]
            name = (a.get("name") or "").strip()
            if not (street and len(postal) == 5 and name):
                continue
            # RICHMOND: a site template's JSON-LD can carry another property's postal code (brentwoodinnandsuites.com
            # states 8901 Brook Road beside Georgia's 30458). A Virginia market reads only a Virginia postal code
            # (2xxxx) from a JSON-LD block; anything else is not the property's own statement of where it is.
            if not postal.startswith("2"):
                continue
            key = (normalize_name(name), address_key(street, postal))
            if key in seen:
                continue
            seen.add(key)
            out.append(observation(
                "PROPERTY_PAGE_IDENTITY_ONLY", 1, url, name, street=street, city=(a.get("city") or "").strip(),
                region=state_code(a.get("region") or "VA") or "VA", postal=postal,
                phone=(a.get("phone") or "").strip() if isinstance(a.get("phone"), str) else "",
                route=url, binding_method="LODGING_JSONLD_ADDRESS_ON_THE_PROPERTYS_OWN_SITE",
                document_sha256=sha,
                identity_note="the property's own site states this lodging address in its schema.org JSON-LD"))
    return out


#: Hosts that are never a property's own site (brands are read in their own lanes; directories are leads).
_NOT_OWN_SITE = ("marriott.com", "hilton.com", "ihg.com", "choicehotels.com", "hyatt.com", "bestwestern.com",
                 "wyndhamhotels.com", "visitvirginiabeach.com", "visitchesapeake.com", "visitnewportnews.com",
                 "visitnorfolk.com", "visithampton.com", "visitportsmouthva.com", "tripadvisor", "expedia", "booking.com",
                 "vrbo", "airbnb", "facebook.com", "instagram.com", "yelp.com",
                 # RICHMOND: third-party booking directories whose pages carry a lodging JSON-LD of their own
                 "hrs.com", "zenhotels.com", "hotels.com", "agoda", "trip.com", "tophotelreservations.com",
                 "sellatimeshare.com", "sellmytimesharenow.com", "stayflexi.com", "outdoorsy.com")


#: RICHMOND: bureau listings that name a brand property this order READ on the brand's own page, keyed on the
#: normalised listing name: (brand family, property code, why the roster street cannot meet the page's).
ROSTER_LISTINGS_OF_A_READ_PROPERTY = {
    "hampton inn norfolk chesapeake": (
        "HILTON", "orfcphx", "Visit Chesapeake lists 'Hampton Inn Norfolk/Chesapeake' at '701-A Woodlake Drive'; Hilton's own "
        "page states 701 Woodlake Dr. for Hampton Inn Norfolk/Chesapeake (Greenbrier Area), and the suite letter keeps the "
        "street key from meeting it"),
}


def read_destination_roster():
    """The county tourism roster: tier-2 discovery and identity evidence.

    Its ZIPs are loose (it prints 27858 for 3212 South Memorial Drive, whose map
    row states 27834), so the stated ZIP is carried as ``stated_postal_code``
    and never keys a building; its phone is carried as ``stated_phone`` and never
    keys one either. A listing whose website is EXACTLY a route this order read
    joins that read by the route and carries no street of its own.
    """
    listings = []
    for path in (DESTINATION,):
        listings.extend((_load(path, {}) or {}).get("listings", []))
    read_routes = {_route_key(r.get("requested_url") or "")
                   for r in (_load(ATTENDED_PASS, {}) or {}).get("rows", [])
                   if r.get("identity_confirmed")}
    out = []
    for r in listings:
        # A profile page the bureau refused on this read (403) states no name and no address:
        # it is recorded in the roster report's unreadable pages, never a census node.
        if not (r.get("name") or "").strip():
            continue
        joined =_route_key(r.get("website") or "") in read_routes
        _bound = ROSTER_LISTINGS_OF_A_READ_PROPERTY.get(normalize_name(r["name"]))
        if _bound:
            # RICHMOND: a bureau listing for a brand property whose OWN page this order read, but whose roster street
            # cannot meet the page's (a shared building, a suite letter, an office-park prefix). It joins that read
            # by the brand property code the ruling names; its roster street is kept only as evidence.
            out.append(observation(
                "DESTINATION_ORGANIZATION", 2, r["listing_url"], r["name"], city=r.get("city", ""),
                region=state_code(r.get("region")), brand=_bound[0], property_code=_bound[1],
                stated_postal_code=r.get("stated_postal_code"), stated_phone=r.get("stated_phone"),
                website_url=r.get("website"), roster_street_superseded=r.get("street", ""),
                binding="ROSTER_LISTING_OF_A_READ_BRAND_PROPERTY", binding_reason=_bound[2],
                document_sha256=r.get("document_sha256"),
                bureau_subcategory=r.get("bureau_subcategory"),
                bureau_all_subcategories=r.get("bureau_all_subcategories"),
                lat=r.get("lat"), lng=r.get("lng"),
            ))
            continue
        out.append(observation(
            "DESTINATION_ORGANIZATION", 2, r["listing_url"], r["name"],
            street="" if joined else r.get("street", ""), city=r.get("city", ""), region=state_code(r.get("region")),
            stated_postal_code=r.get("stated_postal_code"), stated_phone=r.get("stated_phone"),
            website_url=r.get("website"),
            route=r.get("website") if joined else "",
            joins_read_route=joined,
            document_sha256=r.get("document_sha256"),
            amenity_word_pet_friendly_never_policy=r.get("amenity_word_pet_friendly"),
            bureau_subcategory=r.get("bureau_subcategory"),
            bureau_all_subcategories=r.get("bureau_all_subcategories"),
            lat=r.get("lat"), lng=r.get("lng"),
        ))
    return out


def merge_destination_rows(nodes):
    """A roster row with a street and no trusted ZIP joins the ONE building that
    states the same house number and either the same ZIP-free street identity or
    shared chain vocabulary. Never on a name alone, never on the roster's ZIP."""
    merged, absorbed = [], set()
    targets = [n for n in nodes if n.street and n.postal]
    for n in nodes:
        if not n.street or n.postal:
            continue
        if not all(o.get("lane") == "DESTINATION_ORGANIZATION" for o in n.observations):
            continue
        num = (n.street.split() or [""])[0]
        key = address_key(n.street, "")
        # Compare against EVERY name the target's evidence carries: the node's
        # display name at this point may still be a stale map label.
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
    """A regional visitor-center roster: names only, tier 2, never policy (none in this market)."""
    return [observation("REGIONAL_VISITOR_CENTER", 2, REGIONAL_VISITOR_CENTER_SOURCE, name,
                        merge_alias=normalize_name(name),
                        lead_source="regional visitor center lodging roster (names only)")
            for name in REGIONAL_VISITOR_CENTER_LEADS]


def read_competitor():
    """Competitor directory leads: names only, tier 4, never policy."""
    return [observation("COMPETITOR_LEAD", 4, src, name, merge_alias=normalize_name(name),
                        lead_source="competitor directories via a web search result (discovery only)")
            for name, src in COMPETITOR_LEADS]


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
        # A property page captured FOR a brand-roster row IS that row. The
        # capture carried the identity key it was for; without this key the
        # page's address opens a second node and the roster row stays
        # addressless beside it.
        alias = obs.get("merge_alias") or ""
        if alias:
            cand_keys.append("alias:" + alias)
        if sid:
            cand_keys.append("street:" + sid)
        # A MAP phone is tier-3 and never a merge key: OpenStreetMap gives the
        # Wingate at 31 Airport Park Road the Fairfield's switchboard number, and
        # keyed on it the two buildings became one. Map rows join on street.
        if pk and obs.get("lane") != "OSM_OVERPASS":
            cand_keys.append("phone:" + pk)
        if code and brand:
            cand_keys.append("code:%s:%s" % (brand, code))
        # ONE ROUTE, ONE PROPERTY. Wyndham's sitemap names a property only by its
        # route, and the attended read of that SAME route states its address;
        # without a route key the roster row stays name-only beside its own read.
        # The route key extends to every brand host, because a map
        # row whose website is exactly a read route carries that route (above).
        _route = _route_key(obs.get("route") or "")
        if _route and (re.search(r"(wyndhamhotels|hilton|marriott|ihg|redroof|extendedstayamerica|hyatt|choicehotels|bestwestern|woodspring|druryhotels|sonesta|motel6)\.com/", _route)
                       or str(obs.get("lane", "")).startswith("PROPERTY_PAGE")
                       or obs.get("joins_read_route")):
            cand_keys.append("route:" + _route)
        # CO-LOCATED DISTINCT HOTELS. A dual-brand building is TWO hotels, and
        # Raleigh has at least six: Sheraton Raleigh and Le Meridien share
        # 555 South McDowell Street (South Tower / North Tower); Courtyard and
        # Residence Inn share 9110 Harris Corners Parkway; AC Hotel and
        # Residence Inn share 220 East Trade Street; Fairfield and Residence Inn
        # share 2220 West Tyvola Road. Merging on the street alone publishes one
        # of each pair and silently loses the other. So when this observation
        # carries a brand property code and the node the street would put it in
        # already holds a DIFFERENT code in the SAME brand family, the street
        # key is refused: that is the exclusion contract's `co_located_distinct`
        # rule (distinct codes, one family, one street) applied at merge time
        # rather than after the damage.
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

        # CHARLESTON: a shared switchboard is not an identity either. Hilton Garden Inn and Homewood Suites
        # Summerville state one street (406 Sigma Drive) AND one phone (+1 843-832-1304) under two Hilton codes; the
        # street key was already refused above, and the phone key would have folded the Homewood into the HGI.
        if code and brand:
            for _k in [k for k in cand_keys if k.startswith("phone:") and k in by_key]:
                _other = nodes[by_key[_k]]
                if (_other is not _FOLDED and _other.property_code and _other.brand
                        and _other.brand.upper() == brand and _other.property_code.lower() != code):
                    cand_keys.remove(_k)
        hits = {by_key[k] for k in cand_keys if k in by_key}
        if len(hits) > 1:
            # Two established nodes claim this observation. A BRAND PROPERTY
            # CODE settles it and nothing else does: the code names ONE property
            # inside one brand family, while a street is shared by every hotel
            # in a dual-brand building and a phone can be a shared switchboard.
            # Taking the lowest index instead put Le Meridien's cltmd read on
            # the Sheraton's node -- one tower of 555 South McDowell Street
            # swallowing the other, and the same package key written twice.
            code_key = "code:%s:%s" % (brand, code) if (code and brand) else ""
            preferred = by_key.get(code_key) if code_key else None
            # A shared or mis-mapped PHONE never outvotes the building's own
            # street. The map gives Wingate (31 Airport Park Road) Fairfield's
            # switchboard number; without this the Fairfield page read landed on
            # the Wingate node because that node happened to be older.
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
            # FOLD, don't orphan. A map row that reached this street first and a
            # brand-roster row that reached this property code first are the SAME
            # building once the property's own page states both. Leaving the map
            # row behind would hold both as a shared-address pair. A node is folded
            # only when it carries no DIFFERENT brand property code -- two codes at
            # one street stay two hotels.
            for other_idx in sorted(hits - {keep}):
                other = nodes[other_idx]
                if other is None or other is node:
                    continue
                if (other.property_code and node.property_code
                        and other.property_code.lower() != node.property_code.lower()):
                    continue
                # Two buildings joined only through a shared operator phone are
                # never folded: their own street identities disagree.
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
        # Address disagreement blocks the merge rather than overwriting.
        if node.street and obs.get("street"):
            a = street_identity(node.street, node.postal)
            b = street_identity(obs["street"], obs.get("postal", ""))
            # SHARED OWNERSHIP, DISTINCT PREMISES. Carolina Beach Inn (205 Harper
            # Avenue) and SeaBirds (118 Fort Fisher Boulevard South) publish one
            # operator phone. A phone outvotes two street identities only when
            # the two names share chain vocabulary (a corner building the map
            # addresses on one street and the brand on the other); otherwise the
            # disagreement opens a second building.
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
#: Tokens that carry no distinguishing signal: every second hotel has them. The
#: market's own name is here on purpose -- "raleigh" is in most of these names
#: and therefore separates none of them.
_GENERIC_TOKENS = {
    "hotel", "hotels", "inn", "inns", "suites", "suite", "and", "by", "the", "of", "at",
    "a", "an", "motel", "lodge", "lodging", "resort", "conference", "center", "centre",
    "extended", "stay", "america", "select", "s", "by",
    "marriott", "hilton", "wyndham", "hyatt", "ihg", "choice", "radisson",
    "intercontinental", "sonesta", "g6", "curio", "collection", "tapestry",
    "autograph", "tribute", "portfolio", "trademark", "ascend", "bonvoy",
    "va", "virginia", "bed", "breakfast", "b",
    # SAVANNAH / CHARLESTON: marketing vocabulary that names no chain.
    "spa", "luxury", "rooftop", "lounge", "member", "design", "boutique", "club", "golf", "harbor", "i",
    "an", "slh", "historic", "charming",
}
#: Municipalities inside this market. A name that STATES one of these is making
#: a claim about which town the building is in.
_IN_MARKET_MUNICIPALITIES = {
    "virginia beach", "norfolk", "chesapeake", "portsmouth", "hampton", "newport news", "suffolk", "smithfield",
    "carrollton", "yorktown", "grafton", "tabb", "seaford", "fort monroe",
}
#: The Williamsburg / Historic Triangle places, preserved for the future market.
_FUTURE_SUBMARKET_PLACES = {"williamsburg", "jamestown", "james city", "toano", "lightfoot", "kingsmill", "norge",
                            "busch gardens"}
_OUT_OF_MARKET_PLACES = _FUTURE_SUBMARKET_PLACES | {
    "poquoson", "gloucester", "gloucester point", "hayes", "mathews", "cape charles", "cheriton", "exmore", "onley",
    "chincoteague", "moyock", "currituck", "elizabeth city", "kitty hawk", "kill devil hills", "nags head", "corolla",
    "windsor", "surry", "franklin", "courtland", "holland", "whaleyville", "chuckatuck", "new kent", "providence forge",
    "west point", "richmond", "isle of wight", "fort eustis", "langley afb", "joint base langley eustis",
}
_ALL_PLACES = _IN_MARKET_MUNICIPALITIES | _OUT_OF_MARKET_PLACES
#: Place words that are ALSO chain or naming vocabulary ("Hilton Garden Inn", "Home2 Suites
#: Hilton Head"): a place phrase still names the town, but its words are never stripped from a
#: name's chain vocabulary.
_PLACE_WORDS_KEPT_IN_CHAIN = {"garden", "hilton"}
_DIRECTIONALS = {
    "north", "south", "east", "west", "northwest", "northeast", "southwest", "southeast",
    "village", "bypass", "area", "near", "blvd", "road", "rd", "center", "downtown",
    # HAMPTON ROADS area words that tell same-brand hotels apart (Courtyard Oceanfront North / South / Town Center /
    # Greenbrier / Downtown / Airport; Hampton Inn Oceanfront North / South; Residence Inn Town Center / Oceanfront)
    "airport", "medical", "university", "oceanfront", "oceanside", "beachfront", "centre", "greenbrier",
    "battlefield", "waterside", "waterfront", "coliseum", "convention", "oyster", "harbour", "harbor",
    "military", "circle", "odu", "dominion", "ghent", "lynnhaven", "pembroke", "bayfront", "37th", "21st",
    "i64", "i264", "i664", "orf", "phf", "mall", "towne", "peninsula", "mercury", "naval", "creek", "denbigh",
    "phoebus", "olde",
}
#: How much of the DISTINGUISHING brand vocabulary two names must share before a
#: name-only observation may attach. Deliberately strict: a wrong attachment
#: moves a brand route onto the wrong hotel, and the policy lane would then read
#: the wrong building's page and publish it.
_NAME_MATCH_THRESHOLD = 0.75


def places_in(text: str):
    """Every place name this market knows that the text states."""
    n = normalize_name(text)
    padded = " %s " % n
    return {p for p in _ALL_PLACES if (" %s " % p) in padded}


def directionals_in(text: str):
    return {t for t in normalize_name(text).split() if t in _DIRECTIONALS}


def chain_tokens(name: str):
    """The brand vocabulary: what is left after generic, place and area words."""
    toks = [t for t in normalize_name(name).split() if t and not t.isdigit()]
    return {t for t in toks
            if t not in _GENERIC_TOKENS and t not in _DIRECTIONALS
            and t not in {w for p in _ALL_PLACES for w in p.split()} - _PLACE_WORDS_KEPT_IN_CHAIN}


def node_place_vocabulary(node, corridor_municipality=""):
    """Where a building IS, from its own evidence: city, corridor and name.

    The STREET is deliberately excluded. A street name carries directionals that
    are not areas of town -- the Courtyard at 415 WEST Dussel Drive is in Maumee,
    not in West Toledo -- and including it bound "Courtyard Toledo West" to it.
    """
    blob = " ".join(x for x in (node.city, node.name, corridor_municipality) if x)
    return places_in(blob), directionals_in(blob)


def specific_municipality(places):
    """The town a set of place words actually names, ignoring the market itself."""
    return set(places)


def attachment_verdict(soft_name, node, corridor_municipality=""):
    """May this name-only observation attach to this building? Say why not.

    Three rejections, each one a failure this run actually observed:

    * the name states a town the building is not in ("TownePlace Suites by
      Marriott MONROE" offered to the TownePlace in Oregon, Ohio);
    * both name an area of town and the areas differ ("Residence Inn ... Toledo
      WEST" offered to the Residence Inn in MAUMEE);
    * the name states an area and the building's hard evidence states no area at
      all and no town in common, so there is nothing to corroborate against
      ("Red Roof Inn Toledo UNIVERSITY" offered to Red Roof Inn Toledo/Maumee).
    """
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
    """Bind a name-only observation to at most ONE established building.

    An observation with no street, no phone and no comparable property code
    cannot open a building of its own without saying so. It is offered to every
    building that already has hard evidence and binds only to a single clear
    best match. A tie is a review, never a coin flip; no match stays its own
    row, and every rejection keeps its reason.
    """
    node_corridor_municipality = node_corridor_municipality or {}
    hard = [n for n in nodes if n.street or n.phone]
    soft = [n for n in nodes if not (n.street or n.phone)]
    bound, ambiguous, unbound = [], [], []
    for s in soft:
        scored, rejections = [], []
        # An EXACT normalised name that exactly one addressed building carries binds
        # to it even when the name has no distinguishing chain vocabulary ("Motel 6
        # Greenville NC"): identical names cannot be told apart by overlap.
        # BOONE: an apostrophe is typography ("Rhode's Motor Lodge" on its own site, "Rhodes Motor Lodge" on
        # the regional roster), so the exact-name test compares both spellings without it.
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
            # A name-only MAP row carries a pin. A candidate whose own pin is more than
            # 5 km away is a different building of the same flag (the Quality Inns in
            # Washington and Williamston for a Greenville pin), never a tie.
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
    """A second pass for rows whose source printed a street but no postal code.

    ``address_key`` puts the ZIP in the key, so "444 N. Summit Street" with no
    postal can never meet "444 North Summit" in 43604 -- and OSM prints a street
    without a postal often enough that it split three real Toledo hotels into
    pairs when this pass was first written. This pass offers each postal-less row to the rows that DO carry
    one, on street identity alone, and merges only when exactly one building
    matches and the two do not name different cities.
    """
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


#: Atlanta: the map writes "200 Interstate North Parkway Southeast" where the
#: property's own page writes "200 Interstate North Parkway SE", and the shared
#: ``address_key`` keeps "southeast" as a distinguishing word. For the spelling
#: pass only, both are reduced to their distinctive street words -- quadrant
#: directionals and suffixes dropped -- and compared. The house number, the
#: corridor and the single-match rule still apply.
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
    """SAVANNAH: the route number a highway address names ("7220 GA-21" / "7220 Highway 21")."""
    toks = re.sub(r"[^a-z0-9 ]", " ", (street or "").lower()).split()
    if len(toks) < 2 or not re.search(r"\b(va|sc|ga|hwy|highway|us|sr|route|rt)\b", " ".join(toks[1:])):
        return ()
    return tuple(x for x in toks[1:] if x.isdigit())


def _canon_street_words(a, b):
    wa, wb = _canon_words(a), _canon_words(b)
    return bool(wa) and bool(wb) and (wa == wb or wa <= wb or wb <= wa)


def merge_street_spelling(nodes, zips=None):
    """A third pass for one building spelled two ways.

    ``address_key`` keeps "NC Highway 68 South" and "NC Hwy 68 S" apart, so the
    map's Hilton Garden Inn stayed beside the page's. A MAP-ONLY node folds into
    a node the order READ when both state the same house number and the same
    postal code and their chain vocabulary overlaps -- and never when the map
    node carries a different chain word, which is a rebrand question instead.
    """
    read = [n for n in nodes if any(str(o.get("lane", "")).startswith("PROPERTY_PAGE")
                                    for o in n.observations) and n.street and n.postal]
    merged, absorbed = [], set()
    for n in nodes:
        if n in read or not n.street or not n.postal:
            continue
        # A building only the map AND the county roster spell ("400
        # Northwest Drive") folds the same way into the one its own page spells
        # ("400 Northwest Circle").
        if not all(o.get("lane") in ("OSM_OVERPASS", "DESTINATION_ORGANIZATION") for o in n.observations):
            continue
        # "One Buckstone Place" on the page is "1 Buckstone Place" on the map.
        _words = {"one": "1", "two": "2", "three": "3"}

        def _num(st):
            first = (st.split() or [""])[0]
            return _words.get(first.lower(), first)
        num = _num(n.street)

        def _plural_free(st):
            return re.sub(r"s\b", "", normalize_name(st))
        # Greenville: the postal codes must be the SAME CORRIDOR, not the same string.
        # Microtel's own page prints the PO-box ZIP 27835 for 450 Moye Boulevard, which
        # the map and the bureau print as 27834; the contract claims both for one
        # corridor, so the house number and the chain decide. And a bare "Hilton
        # Greenville" carries no chain vocabulary at all once the parent brand and the
        # market's own name are removed, so an IDENTICAL normalised name is accepted
        # in place of shared chain words -- still only at the same house number.
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


def fold_map_rows_beside_a_read(nodes):
    """OUTER BANKS: one resort, two map house numbers.

    OpenStreetMap draws Sea Ranch Resort as buildings at 1725 and 1731 North Virginia
    Dare Trail, and the Outer Banks Motor Lodge at 1511 where its own site states 1509.
    A MAP-ONLY node folds into a node whose OWN page was read when the two carry the
    identical normalised name (or the map name is the read node's page name), the same
    postal code, and house numbers no more than 10 apart on the same street words.
    Never across names, never across postal codes, never into an unread node.
    """
    def _num(st):
        m = re.match(r"\s*(\d+)\s+(.*)", st or "")
        return (int(m.group(1)), _canon_words(st)) if m else (None, set())

    # SAVANNAH: a building the Visitors Bureau lists at its own stated street is a target too (the map
    # draws the Marshall House at 107 East Broughton; the bureau and the inn state 123), still only on the
    # IDENTICAL name and within thirty house numbers on the same street words.
    read = [n for n in nodes if n.street and n.postal and any(
        str(o.get("lane", "")).startswith(("PROPERTY_PAGE", "DESTINATION_ORGANIZATION")) for o in n.observations)]
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
            hnames = {normalize_name(o.get("name") or "") for o in h.observations}
            if names & hnames:
                hits.append(h)
                continue
            # RICHMOND: the map writes "Extended Stay America Suites - Richmond - Glen Allen - Short Pump" at 4225 Park
            # Place Court where the brand's page writes "Extended Stay America - Richmond - Glen Allen - Short Pump" at
            # 4231, and "WoodSpring Suites" at 6902 West Broad Street where the brand's page writes "WoodSpring Suites
            # Richmond West I-64" at 6900. The names agree once the word "suites" is set aside, or the map name's whole
            # distinguishing chain vocabulary is inside the read name's -- still only within ten house numbers on the
            # same street words, in the same postal code, and into exactly one read building.
            _ns = lambda s: " ".join(t for t in s.split() if t != "suites")  # noqa: E731
            if abs(hnum - num) <= 10 and (
                    {_ns(x) for x in names} & {_ns(x) for x in hnames}
                    or any(chain_tokens(x) and chain_tokens(x) <= chain_tokens(h.name) for x in names)):
                hits.append(h)
        if len(hits) != 1:
            continue
        h = hits[0]
        for o in n.observations:
            o = OrderedDict(o)
            o["binding"] = "SAME_NAME_MAP_ROW_WITHIN_TEN_HOUSE_NUMBERS_OF_A_READ_BUILDING"
            h.observations.append(o)
        absorbed.add(id(n))
        folded.append(OrderedDict([("absorbed", n.name), ("absorbed_street", n.street),
                                   ("into", h.name), ("street", h.street), ("postal_code", h.postal)]))
    return [n for n in nodes if id(n) not in absorbed], folded


def fold_rows_into_a_read_by_name(nodes):
    """SAVANNAH: one hotel, two addresses in two secondary sources.

    (a) A node only the Visitors Bureau lists, whose name is IDENTICAL (normalised) to the page name of
        exactly one building this order READ, is that building: the bureau lists the JW Marriott Plant
        Riverside at 400 West River Street, and Marriott's own page states 500. The roster is tier-2
        identity evidence with loose addresses; the property's own page wins.
    (b) A node only the map draws, whose distinguishing brand vocabulary is IDENTICAL to exactly one read
        building's and whose pin lies within 350 m of it in the same postal code, is that building: the
        map draws The Cotton Sail Hotel on its River Street face (121 West River Street), the brand's page
        states its Bay Street entrance (126 W. Bay Street).
    Never on a partial name, never across postal codes, never into an unread node."""
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


#: SAVANNAH: destination-roster rows whose building a first-party read states under its CURRENT flag at
#: the same street. The roster keeps the old trade name. (normalised roster name, street prefix the read
#: states, why). The roster row folds into the read; its label is kept as evidence.
ROSTER_ROWS_SUPERSEDED_BY_A_READ = {
}


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


#: Wyndham publishes the property's city as a segment of its own canonical URL
#: (".../baymont/northwood-ohio/..."). Validated on this market's own data before
#: it was trusted: three rows whose city the census already knew agreed, none
#: disagreed. This is a STRUCTURED field in the brand's location taxonomy and is
#: NOT the same thing as a brand's marketing name -- Hilton calls two Rossford
#: hotels by a two-town marketing name, so a name is never read as a city.
_WYNDHAM_URL_CITY = re.compile(r"wyndhamhotels\.com/[a-z0-9-]+/([a-z-]+)-virginia/", re.I)


def fill_missing_cities(rows):
    """Fill a BLANK city from this market's own evidence. Never overwrite one.

    Two rules, strongest first:
      1. another admitted row in the SAME postal code that states a city, and
         only when every such row agrees;
      2. the city segment of the property's own Wyndham canonical URL.
    A row no rule reaches keeps its blank city and is reported, because an
    invented city is worse than a missing one.
    """
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
                     "(%s); the rule was validated on this market's own data -- 3 rows whose "
                     "city was already known agreed, 0 disagreed" % m.group(0))
        r["city"] = city
        r["city_basis"] = basis
        filled.append(OrderedDict([("identity_key", r["identity_key"]), ("city", city),
                                   ("basis", basis)]))
    return filled, unfilled


#: A brand's own property-page slug, which is a first-party identifier for the
#: hotel and not a marketing line. Used ONLY to name an identity a map source
#: left bare -- never to overrule a name a first-party page states.
_BRAND_SLUG = (
    re.compile(r"hilton\.com/en/hotels/[a-z0-9]{4,9}-([a-z0-9-]+)/?$", re.I),
    re.compile(r"marriott\.com/en-us/hotels/[a-z0-9]{5,7}-([a-z0-9-]+)/overview/?$", re.I),
)


def name_bare_identities(rows):
    """Give a bare brand label its own brand's name for the property.

    OSM prints "Hampton" and "Home2 Suites" with no geography, and a bare label
    is not an identity: Detroit already owns the key "hampton", so a Toledo row
    named "Hampton" collides across markets and the seed assembler refuses it --
    one identity is one listing. The fix is the property's OWN name, taken from
    the brand's own route slug, not a label this order invents.
    """
    named = []
    for r in rows:
        # NEVER rename a building whose identity is unresolved. 1390 Arrowhead
        # Drive is "Super 8" to the map source and "Spark by Hilton Maumee
        # would invent a REBRAND ruling, which only the founder makes: an
        # address that two sources give two chain identities is a lineage
        # question, and this file reports it rather than deciding it.
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
        # A naming fill ADDS geography to a chain the row already names. If the
        # proposed name changes the CHAIN, it is a REBRAND claim, and this file
        # never invents one: a building the map source calls one chain and the
        # brand roster calls another is a lineage question for the founder, and
        # publishing the wrong one sends a guest to a hotel that no longer
        # answers to that name.
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


#: The states this market admits. Raleigh is the first PetTripFinder market
#: whose admitted corridors cross a state line: Fort Mill, Tega Cay and Indian
#: Land are in South Carolina, and the held Rock Hill corridor is there too. A
#: row whose OWN page states any other state is outside the market on that
#: evidence alone.
ADMITTED_STATES = frozenset({"VA", "VIRGINIA"})


def corridor_index():
    """``corridor id`` and ``state`` per admitted postal code, from the contract.

    The state is read from the corridor that CLAIMS the ZIP, never guessed from
    the market's primary state. Filling every unstated state with "NC" would
    the market's primary state. Every Raleigh corridor is in North Carolina,
    and the rule still reads the corridor rather than assuming it.
    """
    cfg = MC.parse_market(_load(CONTRACT_PATH), source=CONTRACT_PATH)
    zips, states = {}, {}
    for c in cfg.corridors:
        for z in c.included_postal_codes:
            zips[z] = c.corridor_id
            states[z] = (getattr(c, "state_code", "") or cfg.state_code or "").upper()
    return cfg, zips, states


def explicit_index(cfg):
    """``identity key -> corridor id`` for the corridors that claim by NAME.

    This mirrors ``markets.assignment.assign_hotels`` exactly: explicit is
    tier 2 and the ZIP is tier 3, so a hotel named explicitly is displayed
    where the registry names it even though its postal code belongs to another
    corridor. Raleigh's registry needs none at authoring time: every admitted
    ZIP is claimed by exactly one corridor and no two clusters share one. The
    mechanism is wired anyway, because it is the only reversible way to place a
    property the ZIP partition would otherwise misfile, and a later ruling adds
    a key here rather than moving a ZIP that other hotels depend on.
    """
    out = {}
    for c in cfg.corridors:
        for key in c.explicit_hotel_ids:
            out.setdefault(key, c.corridor_id)
    return out


#: The municipality each corridor of the contract sits in (name attachment only).
CORRIDOR_MUNICIPALITY = GEO.corridor_municipality()

#: The mailing municipalities each corridor's postal codes actually carry. A
#: property whose OWN stated municipality is a known place outside its ZIP's
#: corridor list is a GEOGRAPHY_HOLD: one of the two first-party facts is wrong
#: and the ZIP alone does not get to decide which.
CORRIDOR_CITIES = GEO.CITY_OF_CORRIDOR


def municipality_conflict(postal, city):
    """A reason string when the stated municipality contradicts the ZIP's corridor."""
    c = " ".join((city or "").lower().replace(".", " ").replace("'", "").split())
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


#: Brand words that identify a chain. Two of these on one address means the
#: building changed hands or flag, which is a lineage question and not a merge
#: error: 3100 Glendale Avenue is BOTH "Radisson Hotel at The University of
#: a Radisson and a Delta Hotels by Marriott in the Toledo run's evidence.
_BRAND_WORDS = {
    "marriott", "hilton", "hyatt", "radisson", "wyndham", "choice", "sheraton", "westin",
    "renaissance", "courtyard", "residence", "towneplace", "springhill", "fairfield",
    "doubletree", "embassy", "candlewood", "staybridge", "holiday", "crowne", "ramada",
    "baymont", "super", "days", "quality", "comfort", "sleep", "clarion", "econo",
    "travelodge", "howard", "johnson", "roof", "studio", "woodspring", "sonesta",
    "drury", "western", "quinta", "home2", "tru", "element", "aloft", "hampton",
    "homewood", "delta", "spark", "wingate", "hawthorn", "microtel", "motel6",
    "home2", "embassy", "canopy", "signia", "waldorf", "moxy", "aloft", "le", "meridien", "westin",
    "jw", "regis", "indigo", "kimpton", "voco", "even", "crowne", "staybridge", "hyatt", "omni",
    "loews", "americinn", "waterwalk", "extended", "intown", "woodspring", "sonesta", "red",
    "econo", "rodeway", "suburban", "mainstay", "cambria", "ascend", "motel", "studio6", "knights",
    # SAVANNAH: IHG's Atwell Suites and Hyatt Place state one address and one phone (4 Stephen S. Green Drive).
    "atwell", "avid", "tempo", "echo", "tryp", "clarks", "cottonwood", "glo",
    "surestay", "cambria", "moxy", "lowline", "jdv", "curio", "ascend",
}


#: Lanes whose NAME is a first-party statement of what this building trades as
#: today: the property's own page, and the brand's own published inventory.
_FIRST_PARTY_NAME_LANES = ("PROPERTY_PAGE", "BRAND_INVENTORY")


def distinct_brand_signatures(node):
    """The distinct chain identities the FIRST-PARTY evidence gives this building.

    A map source and a directory carry the flag a building traded under when
    somebody last edited them, and Raleigh's airport corridor has churned:
    OpenStreetMap still calls 3695 Foothills Way a Clarion, 242 East Woodlawn a
    Best Western Sterling, 3127 Sloan Drive a La Quinta and 4920 South Tryon a
    Hyatt House, while each of those properties' own pages state Candlewood
    Suites, City Express by Marriott, Spark by Hilton and TownePlace Suites.
    Counting a stale third-party label as a second brand identity turns six
    resolved rebrands into six founder holds and publishes none of them. A
    REBRAND is a finding, and the current flag is the one the operator
    publishes; the stale name stays on the row as evidence. Two FIRST-PARTY
    identities at one address remain a genuine hold.
    """
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


#: Wyndham flags with a Greenville-area route that redirected to the brand's city
#: search in this order's attended pass (see the capture report): Wingate by Wyndham
#: Greenville and Travelodge Greenville. The rule only ever reaches a MAP-ONLY row -- a
#: building whose own live page was read is not a map-only row.
RETIRED_WYNDHAM_FLAGS = ()


#: street identity -> the nodes that state it (filled per build; read by classify's same-premises guard).
_PREMISES_PEERS = {}


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
    if _MILITARY_LODGING.search(node.name or "") or GEO.is_military_postal(node.postal):
        return OUTSIDE_MARKET, ("MILITARY_GOVERNMENT_NONPUBLIC -- %r%s: installation lodging that requires installation "
                                "access or military eligibility; the order's military lodging rule refuses it unless "
                                "ordinary public booking is proved, and no lane proved it"
                                % (node.name, (" in installation postal code %s" % node.postal[:5])
                                   if GEO.is_military_postal(node.postal) else ""))
    if normalize_name(node.city) in _OUT_OF_MARKET_PLACES:
        _fs = normalize_name(node.city) in _FUTURE_SUBMARKET_PLACES
        return OUTSIDE_MARKET, (("FUTURE_SUBMARKET %s -- " % GEO.FUTURE_SUBMARKET if _fs else "")
                                + "the row's own municipality %r is a place the geography refuses by name"
                                % node.city)
    _rk = address_key(node.street, "") if node.street else ""
    for _hold_key, _why in REBRAND_HOLDS.items():
        if _rk and (_rk == address_key(_hold_key, "") or _rk.startswith(_hold_key)):
            return SAME_IDENTITY_REBRAND_SUCCESSOR, "REBRAND_HOLD -- " + _why
    if n in LODGING_UNCONFIRMED:
        return IDENTITY_REVIEW_REQUIRED, "LODGING_CATEGORY_UNCONFIRMED -- " + LODGING_UNCONFIRMED[n]
    if n in RESORT_COMPLEX_IDENTITY:
        return IDENTITY_REVIEW_REQUIRED, "RESORT_COMPONENT_IDENTITY -- " + RESORT_COMPLEX_IDENTITY[n]
    if n in COMPONENT_OF:
        return DUPLICATE_LISTING, ("COMPONENT_OF %r -- %s; the building is carried once, under the hotel's own identity"
                                   % COMPONENT_OF[n])
    if n in NOT_LODGING_NAMES or n in STR_PLACEHOLDERS:
        return NON_LODGING, NOT_LODGING_WHY.get(n, "the source lists a business that is not lodging")
    # THE VACATION-RENTAL RULE, on the destination organisation's own typing. A row that no
    # brand roster and no property page reached, and that the Visitors Bureau itself files
    # under a condo / vacation-rental / campground sub-category, is not a hotel identity.
    _subcats = {s for o in node.observations if o.get("lane") == "DESTINATION_ORGANIZATION"
                for s in (o.get("bureau_all_subcategories") or [o.get("bureau_subcategory")]) if s}
    if _subcats and not (_subcats & HOTEL_BUREAU_SUBCATEGORIES) and (_subcats & NON_HOTEL_BUREAU_SUBCATEGORIES) and not any(
            str(o.get("lane", "")).startswith(("PROPERTY_PAGE", "BRAND_INVENTORY")) for o in node.observations):
        return NON_LODGING, ("the city bureau files this listing under %s -- a rental / apartment "
                             "category, not a hotel establishment; refused under the order's non-hotel filter"
                             % sorted(_subcats))
    if _subcats and not (_subcats & HOTEL_BUREAU_SUBCATEGORIES) and _CAMPGROUND_NAME.search(node.name or "") and not any(
            str(o.get("lane", "")).startswith(("PROPERTY_PAGE", "BRAND_INVENTORY")) for o in node.observations):
        return NON_LODGING, ("the city bureau files this listing only under %s and its own name is a campground, RV "
                             "park or state park; campgrounds and RV parks are NON_LODGING" % sorted(_subcats))
    if lead_types and lead_types <= NON_HOTEL_LEAD_TYPES:
        return NON_LODGING, "every lane that typed this row typed it %s" % sorted(lead_types)
    # A MAP ROW NAMED FOR A FLAG WHOSE OWN ROUTE IS RETIRED. Wyndham's own
    # Greenville routes for Wingate and Travelodge now
    # redirect to the brand's city search, which lists none of them. A map row
    # still carrying that flag is a lineage question, never an admitted hotel.
    if lanes == {"OSM_OVERPASS"} and any(
            (" %s " % t) in (" %s " % n) for t in RETIRED_WYNDHAM_FLAGS):
        return IDENTITY_REVIEW_REQUIRED, (
            "a map row under a flag (%s) whose own Greenville-area route on the brand's site is "
            "RETIRED -- it redirects to the brand's city search, which does not list it; the "
            "building's current identity is unconfirmed" % ", ".join(
                t for t in RETIRED_WYNDHAM_FLAGS if (" %s " % t) in (" %s " % n)))
    if lanes == {"OSM_OVERPASS"} and all(o.get("non_hotel_name") for o in node.observations) and not \
            re.search(r"\b(motel|motor court|motor lodge|hotel|inn)\b", node.name or "", re.I):
        # "Inn" is exempt as well (Outer Banks: inns whose names merely contain "house");
        # a genuine rental cabin named "Inn" is refused BY NAME in the rulings module.
        return NON_LODGING, ("a map row whose own name reads as a private cottage, house, estate or "
                             "bed and breakfast; never a hotel identity on a map tag alone")
    # A map row the map itself tags tourism=apartment or tourism=chalet (the High Country's
    # ski condos and rental chalets) and that no other lane typed is a rental unit, never a
    # hotel identity on the map tag alone.
    _osm_cats = {c for o in node.observations for c in (o.get("osm_categories") or []) if c}
    if lanes == {"OSM_OVERPASS"} and _osm_cats and _osm_cats <= {"apartment", "chalet"}:
        return NON_LODGING, ("a map row tagged tourism=%s (a vacation apartment / condo unit or rental "
                             "chalet) that no brand, bureau or property page typed as a hotel; refused under "
                             "the order's cabin and condo-unit rule" % "/".join(sorted(_osm_cats)))
    if lanes == {"OSM_OVERPASS"} and re.match(r"\s*STVR\b", node.name or ""):
        return NON_LODGING, ("a map row the map itself names 'STVR' (a permitted short-term vacation "
                             "rental); an individual rental unit, never a hotel identity")
    if lanes <= {"COMPETITOR_LEAD", "REGIONAL_VISITOR_CENTER"} and _RENTAL_WORDS.search(node.name or ""):
        return NON_LODGING, ("a competitor short-term-rental listing, named only by the competitor "
                             "and reading as a private dwelling; never a hotel identity")
    # A NAME never outranks a first-party read. A building this order actually
    # READ -- its own page stating its own street, postal code and brand
    # property code -- is identified by that evidence, and a map row or a
    # directory lead whose NAME happens to match two of them equally well is a
    # fact about the lead, not about the building. Folding the OpenStreetMap
    # lane in demoted dozens of confirmed hotels to review on exactly that,
    # which is the tail wagging the dog: the ambiguity is recorded on the node
    # and the hard evidence decides.
    _hard_read = any(o.get("lane", "").startswith("PROPERTY_PAGE") for o in node.observations)
    if node.ambiguous_matches and not (_hard_read and node.street and node.postal):
        return IDENTITY_REVIEW_REQUIRED, (
            "a name-only observation that matches more than one established building equally "
            "well (%s); a tie is a review, never a coin flip"
            % ", ".join(node.ambiguous_matches[:4]))
    # TYBEE ISLAND AND THE REFUSED NEIGHBOURS BY PIN. A row with NO postal code of its own that
    # every source pins on Tybee Island (east of lng -80.90), north of the Port Wentworth line
    # (lat > 32.22: Rincon / Hardeeville), south of Richmond Hill (lat < 31.87: Midway) or west of
    # lng -81.42 (Pembroke / Ellabell) cannot be an admitted identity whatever else is unknown
    # about it. Refusal only: a pin never ADMITS a building.
    _pins = [(o.get("lat"), o.get("lng")) for o in node.observations
             if o.get("lat") is not None and o.get("lng") is not None]
    # CHARLESTON: Kiawah Island and Seabrook Island sit south-west of lat 32.645 / lng -80.02 (Folly Beach, at
    # lng -79.94, is east of that line); Moncks Corner lies north of lat 33.12, Edisto / Ravenel west of lng -80.26
    # and Awendaw east of lng -79.69. A pin never ADMITS a building.
    # RICHMOND: Colonial Heights and Petersburg lie south of lat 37.28 and Hopewell / Prince George south of 37.34 and
    # east of lng -77.34 (Chester's southern edge is near 37.30 at lng -77.42); Doswell lies north of 37.80, Powhatan and
    # Goochland west of lng -77.78, and New Kent east of lng -77.20. A pin never ADMITS a building.
    # HAMPTON ROADS: Williamsburg, James City County and historic Yorktown lie north of lat 37.20 (the US-17 FRINGE
    # corridor at Grafton tops out near 37.18); North Carolina lies south of lat 36.55; western Suffolk, Windsor and Surry
    # west of lng -76.70 (downtown Suffolk is -76.58, Smithfield -76.63); the Eastern Shore north of lat 37.00 and east of
    # lng -76.10. A pin never ADMITS a building.
    if not node.postal and _pins and all(float(t) > 37.20 and float(g) < -76.30 for t, g in _pins):
        return OUTSIDE_MARKET, ("FUTURE_SUBMARKET %s -- no postal code of its own, and every source pins it "
                                "in Williamsburg / historic Yorktown / Gloucester (%.4f, %.4f)"
                                % (GEO.FUTURE_SUBMARKET, float(_pins[0][0]), float(_pins[0][1])))
    if not node.postal and _pins and all(float(t) < 36.55 or float(g) < -76.70 or (float(t) > 37.00 and float(g) > -76.10)
                                         for t, g in _pins):
        return OUTSIDE_MARKET, ("no postal code of its own, and every source pins it beyond the admitted "
                                "corridors (North Carolina south, western Suffolk / Surry west or the Eastern Shore; "
                                "%.4f, %.4f)" % (float(_pins[0][0]), float(_pins[0][1])))
    if not node.street and not node.phone and not node.postal:
        # A NAME-ONLY lead whose own name states only places the geography refuses ("Holiday Inn Express of
        # Wilkesboro", "Jefferson Landing Lodge") is outside on its own words; a name never ADMITS.
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
                                "Virginia" % node.region)
    if node.postal and node.postal[:5] not in zips:
        _fs = (" FUTURE_SUBMARKET %s --" % GEO.FUTURE_SUBMARKET) if GEO.is_future_submarket(node.postal, node.city) else ""
        return OUTSIDE_MARKET, ("%s postal code %s is claimed by no corridor of the Hampton Roads "
                                "contract; %s" % (_fs, node.postal[:5],
                                GEO.classify_postal(node.postal, node.city)[2])).strip()
    if node.postal and node.city:
        _klass, _slug, _why = GEO.classify_postal(node.postal, node.city)
        if _klass == "OUTSIDE":
            _fs = ("FUTURE_SUBMARKET %s -- " % GEO.FUTURE_SUBMARKET) if GEO.is_future_submarket(node.postal, node.city) else ""
            return OUTSIDE_MARKET, (_fs + "the property's own stated municipality %r inside the shared "
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
        # CO-LOCATED DISTINCT, the exclusion contract's own rule (founder ruling
        # A, PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004): two hotels may share one
        # street identity when each states a brand property code and a canonical
        # first-party URL of its own, and the two codes differ within the same
        # brand family. Raleigh has seven such pairs -- Sheraton Raleigh and
        # Le Meridien in the two towers of 555 South McDowell Street, Courtyard
        # and Residence Inn at 9110 Harris Corners Parkway, AC Hotel and
        # Residence Inn at 220 East Trade Street, Fairfield and Residence Inn at
        # 2220 West Tyvola Road among them. Each is a real, separately bookable
        # hotel with its own policy; holding them all would lose fourteen
        # buildings to a rule meant to catch duplicates. A row missing a code,
        # missing a URL, or sharing a URL is NOT proved distinct and is held.
        if node.property_code and node.brand and node.route:
            # CHARLESTON: the sealed-package writer proves a shared premises through the SHARED exclusion
            # contract's co_located_distinct(name, official_url), which reads Marriott / Hilton / IHG route codes
            # but not Hyatt's. Hyatt House Charleston/Historic District (chsxh) and The Lowline Hotel (chszh) share
            # 560 King Street; a pair the shared rule cannot prove is held here as a same-campus identity for the
            # registration order's resolution, rather than refused at seal time.
            peers = [p for p in _PREMISES_PEERS.get(sk, ()) if p is not node]
            from scripts.pettripfinder import hotel_exclusions as _HE
            if peers and any(_HE.co_located_distinct(
                    {"canonical_name": node.name, "official_url": node.route},
                    {"canonical_name": p.name, "official_url": p.route})[0] != _HE.CO_LOCATED_DISTINCT
                    for p in peers):
                return SAME_CAMPUS_DISTINCT_ENTITY, (
                    "SAME_CAMPUS_UNPROVEN -- another identity states the same street identity and the shared "
                    "co-located-distinct rule cannot prove the pair from their first-party URLs (%s); both rows are "
                    "retained for a same-campus resolution at registration" % ", ".join(p.name for p in peers))
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


#: SAVANNAH: brand families whose OWN Savannah-area inventory this order read in full (Marriott's SAV-coded
#: harvest and Georgia sitemap page, Hilton's city pages and sub-pages, IHG's destination pages, Choice's
#: city pages, Best Western's property sitemap, Wyndham's sitemap and property service). A map or bureau
#: row under one of their flags that NO first-party read joined is a flag the brand's own inventory does
#: not list at that address today -- a retired, rebranded or mis-drawn row -- and is held for review,
#: never admitted on the map's label.
_COVERED_FLAGS = (
    # HAMPTON ROADS: "Hampton" is a CITY here ("Comfort Inn Newport News - Hampton I-64", "Sonesta Simply Suites Hampton"),
    # so only "Hampton Inn" names the flag.
    ("HILTON", r"\b(hampton inn|hilton|home2|homewood|embassy suites|doubletree|spark by hilton|tru by hilton|tempo|signia)\b"),
    ("MARRIOTT", r"\b(courtyard|residence inn|fairfield|springhill|towneplace|aloft|element|westin|sheraton|four points|ac hotel|marriott|moxy)\b"),
    ("IHG", r"\b(holiday inn|candlewood|staybridge|avid|atwell|hotel indigo|crowne plaza)\b"),
    ("HYATT", r"\b(hyatt place|hyatt house)\b"),
    ("CHOICE", r"\b(comfort inn|comfort suites|quality inn|sleep inn|econo lodge|clarion|cambria|mainstay|suburban|rodeway|country inn)\b"),
    ("WYNDHAM", r"\b(days inn|super 8|baymont|la quinta|wingate|microtel|travelodge|ramada|howard johnson|hawthorn|tryp|echo suites)\b"),
    ("BEST_WESTERN", r"\b(best western|gl[oō] )\b"),
)


#: RICHMOND: flag rows whose brand's OWN inventory DID list a property at that place, but whose property page refused
#: this client on this run (Choice's 403 shell after 22 reads). The brand's listing is not an absence, so the row is not
#: held as unlisted; the final partition records it ACCESS_BLOCKED. (normalised name -> the refused route)
BRAND_ROUTE_REFUSED = {
    "comfort suites airport": "https://www.choicehotels.com/virginia/newport-news/comfort-suites-hotels/va384 (403 wall)",
    "sleep inn and suites": "https://www.choicehotels.com/virginia/newport-news/sleep-inn-hotels/va358 (403 wall)",
    "country inn and suites by carlson newport news south":
        "https://www.choicehotels.com/virginia/newport-news/country-inn-suites-hotels/va761 (403 wall)",
    "clarion inn and suites": "https://www.choicehotels.com/virginia/virginia-beach/clarion-hotels/va050 (403 wall)",
}


def brand_not_listed(node):
    lanes = {o.get("lane") for o in node.observations}
    if lanes & {"PROPERTY_PAGE_ATTENDED", "PROPERTY_PAGE_STATIC", "PROPERTY_PAGE_IDENTITY_ONLY",
                "BRAND_INVENTORY_OWNED", "BRAND_INVENTORY_CITY_PAGE", "BRAND_INVENTORY_STATE_SITEMAP",
                "BRAND_INVENTORY_SITEMAP"}:
        return None
    if normalize_name(node.name) in BRAND_ROUTE_REFUSED:
        return None
    for fam, rx in _COVERED_FLAGS:
        if re.search(rx, node.name or "", re.I):
            return ("a %s row naming a %s flag (%r) that no read of that brand's own Hampton Roads inventory "
                    "joined at this address; a retired, rebranded or mis-drawn row is never admitted on its label"
                    % ("/".join(sorted(lanes)), fam, node.name))
    return None


SOURCE_AUTHORITIES = [
    "OpenStreetMap via the Geofabrik Virginia extract (2026-09-14 snapshot), reduced to this market's "
    "observation box (ODbL, (c) OpenStreetMap contributors)",
    "launch_packages/pettripfinder/markets/reports/dayton_oh_brand_directory_harvest_001.json (the committed "
    "national Marriott harvest, RIC-coded routes)",
    "https://www.marriott.com/en-us/hotel-sitemap/usa-virginia-hotel-sitemap (the brand's own Virginia hotel "
    "sitemap page)",
    "https://www.hilton.com/en/locations/usa/virginia/<city>/ (Hampton Roads city pages and sub-pages, with "
    "property cards)",
    "https://www.wyndhamhotels.com/sitemap.xml and the brands' own sitemaps that answered a plain client; Wyndham "
    "overview pages and the brand's own property service",
    "https://www.visitvirginiabeach.com (the bureau CRM's WordPress listing API, attended browser), https://www.visitchesapeake.com and https://www.visitnewportnews.com (Simpleview listing services, plain client)",
    "the brands' own property pages read in the attended browser",
    "each property's own page (attended browser pass and plain static reads)",
    "web search result pages summarising competitor lists (competitor leads; names only)",
]


def build():
    cfg, zips, corridor_state = corridor_index()
    explicit = explicit_index(cfg)
    lanes = OrderedDict([
        ("OSM_OVERPASS", read_osm()),
        ("BRAND_INVENTORY_OWNED", read_brand_owned()),
        ("BRAND_INVENTORY_CITY_PAGE", read_brand_city_pages()),
        ("BRAND_INVENTORY_STATE_SITEMAP", read_brand_state_sitemap()),
        ("BRAND_INVENTORY_SITEMAP", read_brand_sitemaps()),
        ("DESTINATION_ORGANIZATION", read_destination_roster()),
        ("REGIONAL_VISITOR_CENTER", read_regional_visitor_center()),
        ("COMPETITOR_LEAD", read_competitor()),
        ("PROPERTY_PAGE", read_property_pages() + read_identity_only_pages() + read_static_identity_pages()),
    ])
    all_obs = [o for rows in lanes.values() for o in rows]
    nodes, merge_conflicts = merge(all_obs)
    # The spelling pass runs once BEFORE the postal-less pass as well, so a map row the
    # page spells differently is already folded when a zipless roster row looks for its
    # one building (Microtel: map 27834, page 27835, bureau no ZIP).
    nodes, early_spelling_merged = merge_street_spelling(nodes, zips)
    nodes, zipless_merged, zipless_ambiguous = merge_zipless(nodes)
    nodes, destination_merged = merge_destination_rows(nodes)
    # A roster-only building (no map row, no read) takes the roster's stated ZIP for
    # MEMBERSHIP only, and says so; its identity never keyed on it.
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
            # Greenville's corridor slugs name AREAS ("convention center medical district"),
            # not towns, and an area word from a slug would out-vote the property's own
            # name. The municipality each corridor sits in is stated instead.
            corridor_municipality[id(n)] = CORRIDOR_MUNICIPALITY.get(cid.split("__", 1)[-1], "")
    nodes, spelling_merged = merge_street_spelling(nodes, zips)
    spelling_merged = early_spelling_merged + spelling_merged
    nodes, neighbour_folded = fold_map_rows_beside_a_read(nodes)
    nodes, name_folded = fold_rows_into_a_read_by_name(nodes)
    nodes, roster_superseded = fold_roster_rows_superseded_by_a_read(nodes)
    name_folded = name_folded + roster_superseded
    neighbour_folded = neighbour_folded + name_folded
    # A building no property page named keeps the name the destination bureau lists it
    # under rather than a bare map label ("Comfort Inn"), so competitor leads can meet it
    # and a bare label never collides.
    for n in nodes:
        if any(str(o.get("lane", "")).startswith("PROPERTY_PAGE") for o in n.observations):
            continue
        bureau = [o.get("name") for o in n.observations
                  if o.get("lane") == "DESTINATION_ORGANIZATION" and o.get("name")]
        if bureau:
            n.name = bureau[0]
    hard, bound, ambiguous, unbound = attach_name_only(nodes, corridor_municipality)
    nodes = hard + ambiguous + unbound
    # The name the property's OWN page states is the canonical name. "Longest
    # wins" let a Hilton slug outrank the page's own name for the hotel.
    for n in nodes:
        page_names = [o.get("name") for o in n.observations
                      if str(o.get("lane", "")).startswith("PROPERTY_PAGE") and o.get("name")]
        if page_names:
            n.name = page_names[0]

    # A same-brand, same-city PAIR is demoted to review rather than aliased.
    # The pair has to be a pair of BUILDINGS: only nodes that state a street or
    # a phone are counted. A name-only lead carries no address at all, so it
    # cannot be "another node at a different address" -- counting it demoted 47
    # fully-addressed, identity-confirmed Raleigh hotels because a BringFido
    # or destination-roster row happened to spell the same name.
    # Greenville: counted per TOWN. The Econo Lodges in Washington and Kinston are
    # not "another node at a different address" for the one on Cross Winds Street:
    # a same-brand pair is only ambiguous inside one municipality.
    # Atlanta: counted across the WHOLE market, not per town. A bare map label ("Motel 6",
    # "Country Inn & Suites") carries no city, and per-town counting let two such rows
    # at different addresses both publish under one identity key -- which the registered
    # census contract forbids. A building whose own page was read keeps its name.
    name_counts = Counter((normalize_name(n.name), "") for n in nodes
                          if n.street or n.phone)
    street_counts = Counter(street_identity(n.street, n.postal) for n in nodes
                            if street_identity(n.street, n.postal))

    _PREMISES_PEERS.clear()
    for n in nodes:
        _sk = street_identity(n.street, n.postal)
        if _sk and street_counts.get(_sk, 0) > 1:
            _PREMISES_PEERS.setdefault(_sk, []).append(n)
    rows = []
    for node in nodes:
        klass, why = classify(node, zips, name_counts, street_counts)
        z = (node.postal or "")[:5]
        sk = street_identity(node.street, node.postal)
        # Every key any lane used for this building. A read captured under the
        # brand roster's name for a property must still find its census row
        # after the merge renamed it, or a clean read is silently orphaned.
        aliases = sorted({normalize_name(o.get("name") or "") for o in node.observations
                          if (o.get("name") or "").strip()}
                         | {o["read_for_identity_key"] for o in node.observations
                            if o.get("read_for_identity_key")})
        # Tier order, the same one the assignment authority uses: an explicit
        # naming outranks the postal code, and the basis records which fired.
        # The registered census contract derives the key with ptf_identity_key/1.0, which
        # transliterates ("Le Méridien" -> "le meridien") where normalize_name drops the letter.
        _key = ptf_identity_key(node.name)
        _corridor = explicit.get(_key) or zips.get(z, "")
        _basis = ("explicit" if explicit.get(_key)
                  else "postal_code" if z in zips else "")
        # The REGISTERED census contract requires four fields a shadow census
        # never needed: a slug, the market id, and the two axes it separates on
        # purpose -- IDENTITY (is this a real, distinct property?) and LODGING
        # (is it in category?). They are derived here rather than added by a
        # later promotion, because Raleigh's census IS the registered one
        # from the moment it is written.
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
            ("street", node.street), ("city", node.city),
            ("state", node.region or corridor_state.get(z, "")),
            ("postal_code", z), ("phone", node.phone),
            ("phone_key", phone_key(node.phone)),
            # The shared key, exactly as the exclusion contract and package writer compute it.
            ("street_identity", address_key(node.street, node.postal) if (node.street or "").strip() else ""),
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
    # A row whose municipality no first-party or same-ZIP evidence states is not a
    # registrable identity (the census contract requires a city). It is demoted to
    # review rather than given a guessed city.
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
        ("work_order", WORK_ORDER), ("captured_at", "2026-09-14"),
        ("note",
         "PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 Hampton Roads census, built from zero "
         "under the modern factory and written to identity_census_proposed/ (shadow until registered). Every row carries "
         "the observations that produced it; nothing here carries a pet policy."),
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
             "A bare brand label is not an identity: Detroit already owns the key 'hampton', so a "
             "Raleigh row named 'Hampton' collides across markets and the seed assembler "
             "refuses it. Each such row takes the property's OWN name from its brand's route "
             "slug -- never a name this order invents."),
            ("renamed", renamed),
        ])),
        ("city_backfill", OrderedDict([
            ("what_it_is",
             "A blank city filled from this market's OWN evidence: another admitted row in the "
             "same postal code, or the city segment of the property's own canonical URL. A "
             "brand's marketing NAME is never read as a city: in this market almost every "
             "hotel in Antioch, Hermitage, Bellevue, Donelson, Green Hills and Old Hickory "
             "is named 'Raleigh' by its own operator."),
            ("filled", city_filled), ("left_blank", city_unfilled),
        ])),
        ("merge_conflicts", merge_conflicts),
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
         "A competitor row cannot enter Hampton Roads authority without first-party identity "
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
                    default=os.path.join(CENSUS_DIR, "hampton-roads-va.json"))
    ap.add_argument("--report-out",
                    default=os.path.join(REPORTS, "hampton_roads_va_census_reconciliation_001.json"))
    ap.add_argument("--gap-out",
                    default=os.path.join(REPORTS, "hampton_roads_va_competitor_gap_matrix_001.json"))
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

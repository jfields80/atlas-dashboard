"""PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001 -- Phases 5, 6 and 8: one identity graph.

Independent discovery lanes ran for Raleigh, none of them authoritative on
its own:

  OSM_OVERPASS        hotel and motel elements inside this market's twenty-eight
                      discovery cells, answered from the md5-verified Geofabrik
                      North Carolina extract under the ODbL.
  BRAND_INVENTORY     Marriott's RDU* roster, OWNED at zero requests from the
                      committed Dayton national harvest, plus Hilton's roster
                      read from the brand's OWN North Carolina city pages, plus
                      every other family's own sitemap routes.
  COMPETITOR_LEAD     accessible pet-travel directories (tier 4, leads only,
                      never policy).

This module merges them into ONE identity per building and says, for every
candidate, which class it is and what evidence put it there.

WHAT DECIDES AN IDENTITY
------------------------
Address, postal code, phone or brand property code. Never a name on its own,
and never a city, neighbourhood, "airport", "downtown" or a directional. Two
rows merge when they agree on a STREET IDENTITY (house number + distinctive
street words + ZIP) or on a normalised phone; a name match alone produces
NAME_ONLY_UNRESOLVED, and a name match whose addresses DISAGREE produces
ADDRESS_CONFLICT and blocks the merge.

WHAT DECIDES MEMBERSHIP
-----------------------
The market contract's postal partition, and nothing else. The rule is WAKE
COUNTY, NORTH CAROLINA: Raleigh proper, Cary, Morrisville, Apex, Garner, Wake
Forest, Knightdale and Wake's outer towns, each claiming its own postal codes.

Raleigh is the market where a BRAND'S OWN NAME FOR A PROPERTY is most likely to
be wrong about geography. Marriott's RDU prefix is the Raleigh-Durham AIRPORT
code and reaches Durham, the Durham side of Research Triangle Park and Chapel
Hill as readily as Cary; dozens of properties are named "...Raleigh-Durham...
Research Triangle Park..." and stand in Durham County. Every one of them is
discovered, identified, and then classified on the postal code its own page
states. "Raleigh-Durham" is an airport, not a market.

Nothing here fetches. Nothing here writes outside Raleigh artifacts. Nothing
here carries a pet policy: identity evidence never establishes one.

Outputs:
  launch_packages/pettripfinder/identity_census/raleigh-nc.json
  launch_packages/pettripfinder/markets/reports/raleigh_nc_census_reconciliation_001.json
  launch_packages/pettripfinder/markets/reports/raleigh_nc_competitor_gap_matrix_001.json
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

WORK_ORDER = "PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001"
MARKET_ID = "raleigh-nc"
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
#: Raleigh is built under the MODERN factory and has no legacy shadow, so its
#: census is written where a registered market's census lives. There is no
#: pinned Raleigh census to overwrite: this order creates the file.
CENSUS_DIR = os.path.join(PKG, "identity_census")
CONTRACT_PATH = _first_existing(os.path.join(PKG, "markets", "raleigh-nc.json"),
                                os.path.join(PKG, "markets", "proposed", "raleigh-nc.json"))
PROPOSED_CONTRACT = os.path.join(REPORTS, "raleigh_nc_corridor_registry_001.json")

CANDIDATES = os.path.join(_DASH, "data", "discovery", "raleigh_nc_free_001", "candidates",
                          "raleigh-nc_candidates.json")
BRAND = os.path.join(REPORTS, "raleigh_nc_brand_inventory_001.json")
STATIC_LANE = os.path.join(REPORTS, "raleigh_nc_free_static_lane_001.json")
FIRECRAWL_PASS = os.path.join(REPORTS, "raleigh_nc_firecrawl_pass_001.json")
ATTENDED_PASS = os.path.join(REPORTS, "raleigh_nc_attended_capture_001.json")
STATIC_CAPTURE = os.path.join(REPORTS, "raleigh_nc_free_static_capture_001.json")
LEADS = os.path.join(REPORTS, "raleigh_nc_lead_sources_001.json")

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
NOT_LODGING_NAMES = {
    "raleigh convention center", "visit raleigh", "greater raleigh convention and visitors bureau",
    "pnc arena", "carter finley stadium", "walnut creek amphitheatre",
    "coastal credit union music park", "north carolina state fairgrounds",
    "north carolina museum of art", "north carolina museum of natural sciences",
    "marbles kids museum", "wakemed", "duke energy center for the performing arts",
    "raleigh durham international airport", "lenovo center", "dorothea dix park",
    "jc raulston arboretum", "pullen park", "koka booth amphitheatre",
}
#: Categories a competitor lead can carry that are not a hotel identity.
NON_HOTEL_LEAD_TYPES = {"Campground"}
#: Short-term-rental aggregator placeholders BringFido lists as if they were
#: properties. They name a marketplace, not a building.
STR_PLACEHOLDERS = {"raleigh airbnb rentals", "vrbo raleigh", "airbnb raleigh",
                    "vrbo rentals", "raleigh vacation rentals", "airbnb rentals",
                    "cary vacation rentals", "airbnb cary", "durham airbnb rentals"}

_RENTAL_WORDS = re.compile(
    r"\b(airbnb|vrbo|apartment|apt\b|condo|cottage|bungalow|home w|house w|townhome|townhouse"
    r"|studio loft|guest ?house|cabin|retreat|rental|bnb|bed and breakfast)\b", re.I)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def phone_key(value: str) -> str:
    d = re.sub(r"\D", "", value or "")
    return d[-10:] if len(d) >= 10 else ""


def street_identity(street: str, postal: str) -> str:
    if not (street or "").strip():
        return ""
    return address_key(street, postal or "")


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
    rows = _load(CANDIDATES, []) or []
    out = []
    for r in rows:
        src = (r.get("source_records") or [{}])[0]
        out.append(observation(
            "OSM_OVERPASS", 3,
            src.get("provider_place_url") or "https://www.openstreetmap.org/",
            r.get("name"),
            street=(r.get("address_line") or "").strip(),
            city=(r.get("city") or "").strip(),
            # NEVER hardcoded. Raleigh spans two states and this market's own
            # South Carolina corridors are admitted, so a map row's state is
            # taken from the row itself and left EMPTY when the map source did
            # not state one. An empty state is no evidence; a wrong one is
            # affirmative evidence that the building is somewhere else.
            region=state_code((r.get("region") or r.get("state") or "").strip()),
            postal=(r.get("postal_code") or "").strip(),
            phone=(src.get("phone") or "").strip(),
            lat=r.get("latitude"), lng=r.get("longitude"),
            candidate_id=r.get("candidate_id"),
            osm_categories=src.get("provider_categories"),
            # A website the map source states for this building. Carried as
            # EVIDENCE, never as a route: the routing lane decides whether it
            # is a property page or a brand locator index, and the capture lane
            # decides whether the page is this hotel.
            website_url=(src.get("website_url") or "").strip(),
        ))
    return out


_MARRIOTT = re.compile(r"marriott\.com/en-us/hotels/([a-z0-9]{5,7})-([a-z0-9-]+)/overview", re.I)
_WYNDHAM = re.compile(
    r"wyndhamhotels\.com/([a-z0-9-]+)/([a-z-]+)-(?:north|south)-carolina/([a-z0-9-]+)/overview",
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
               "nc", "carolina"}


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
    """Hilton's coded roster, read from the brand's OWN North Carolina city pages.

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
        name = _name_from_route(r["route"])
        if not name:
            continue
        out.append(observation(
            "BRAND_INVENTORY_CITY_PAGE", 1, r["route"], name,
            brand=r["family"], property_code=r.get("property_code", ""),
            route=r["route"], merge_alias=normalize_name(name),
            admitted_by="ROUTE_READ_FROM_THE_BRAND_OWN_CITY_PAGE",
            seen_in=r.get("found_in", ""),
            document_sha256=r.get("found_in_sha256"),
        ))
    return out


def read_brand_sitemaps():
    """Property routes read from a brand's OWN sitemap -- tier 1 routing evidence.

    Rung 2 of the brand inventory. Like every roster row it NAMES a property and
    routes to it, and admits nothing: the postal code the property's own page
    states decides membership.
    """
    out = []
    for r in _brand_doc().get("leads", []):
        if r.get("lane") != "BRAND_SITEMAP":
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


def read_cvb():
    """The official destination organisation's own lodging roster, tier 2.

    Toledo's CVB published a partner sitemap carrying a full address per
    partner. Raleigh's destination organisations are probed the same way and
    whatever they serve is read. A lodging-shaped URL with no address is a
    NAME-ONLY lead and is treated as one; it never places a building.
    """
    doc = _load(LEADS, {}) or {}
    out = []
    for org, block in (doc.get("destination_organisations") or {}).items():
        for url in block.get("lodging_links") or []:
            name = _name_from_route(url)
            if not name:
                continue
            out.append(observation(
                "CVB_PARTNER", 2, url, name,
                merge_alias=normalize_name(name), seen_in=org,
            ))
    return out


def read_property_pages():
    """The address a property's OWN page states -- tier 1, and the only thing
    allowed to turn a brand-roster row into a Raleigh identity.

    This closes the loop the routing lane opened. A brand's published inventory
    says a property exists and gives its canonical route; it does not say where
    the building is, and a TOL prefix reaches Findlay, Fostoria, Wauseon and Port
    Clinton as readily as Maumee. So the route is captured, the page states an
    address, and THAT is what this lane feeds back into the identity graph.

    It is also how a rebrand surfaces: Wyndham's own page puts Baymont Maumee at
    6425 Kit Lane, 43537 -- the address the map source still calls Best Western.
    """
    out = []
    for path, lane in ((STATIC_CAPTURE, "PROPERTY_PAGE_STATIC"),
                       (FIRECRAWL_PASS, "PROPERTY_PAGE_FIRECRAWL")):
        doc = _load(path, {}) or {}
        for r in doc.get("rows", []):
            ident = r.get("identity_assessment") or {}
            if not ident.get("confirmed"):
                continue
            sig = ident.get("signals") or {}
            street = (sig.get("address_on_page") or "").strip()
            postal = (sig.get("postal_code") or "").strip()[:5]
            if not street:
                continue
            out.append(observation(
                lane, 1, r.get("final_url") or r.get("requested_url"),
                (sig.get("name_on_page") or r.get("canonical_name") or "").strip(),
                street=street, postal=postal,
                phone=(sig.get("phone_on_page") or "").strip(),
                property_code=(sig.get("property_code_on_page") or "").strip(),
                route=r.get("requested_url"),
                merge_alias=r.get("identity_key"),
                document_sha256=r.get("page_sha256"),
                binding_method=ident.get("binding_method"),
                read_for_identity_key=r.get("identity_key"),
            ))
    # The free static lane's own shape. A brand whose ROSTER named a property
    # but gave it no address is a NAME-ONLY row until something states one; the
    # static read of that property's own page is what states it, and feeding it
    # back here is what turns three Drury roster rows into three buildings.
    doc = _load(STATIC_LANE, {}) or {}
    for r in doc.get("rows", []):
        sig = r.get("identity_signals") or {}
        street = (sig.get("address_on_page") or "").strip()
        if not street:
            continue
        out.append(observation(
            "PROPERTY_PAGE_STATIC", 1,
            r.get("final_url") or r.get("requested_url"),
            (sig.get("name_on_page") or "").strip(),
            street=street, postal=(sig.get("postal_code") or "").strip()[:5],
            city=(sig.get("locality") or "").strip(),
            region=state_code(sig.get("region")),
            phone=(sig.get("phone_on_page") or "").strip(),
            brand=r.get("brand"), route=r.get("requested_url"),
            document_sha256=r.get("document_sha256"),
            lat=float(sig["latitude"]) if sig.get("latitude") else None,
            lng=float(sig["longitude"]) if sig.get("longitude") else None,
            binding_method="PROPERTY_RECORD_ADDRESS_ON_THE_PAGES_OWN_DOMAIN",
        ))

    # The attended pass reads Marriott and Hilton, which no other lane can. Its
    # rows carry the address the property's OWN page states, so they are the
    # same tier-1 identity evidence as the static and Firecrawl reads.
    doc = _load(ATTENDED_PASS, {}) or {}
    for r in doc.get("rows", []):
        if not r.get("identity_confirmed"):
            continue
        sig = r.get("identity_signals") or {}
        street = (sig.get("address_on_page") or "").strip()
        if not street:
            continue
        out.append(observation(
            "PROPERTY_PAGE_ATTENDED", 1, r.get("final_url") or r.get("requested_url"),
            (sig.get("name_on_page") or "").strip(),
            street=street, postal=(sig.get("postal_code") or "").strip()[:5],
            city=(sig.get("locality") or "").strip(),
            region=state_code(sig.get("region")),
            phone=(sig.get("phone_on_page") or "").strip(),
            property_code=(sig.get("property_code_on_page") or "").strip(),
            brand=r.get("brand"), route=r.get("requested_url"),
            document_bytes=r.get("document_bytes"),
            binding_method=r.get("identity_binding_method"),
        ))
    return out


def read_competitor():
    """BringFido rows, tier 4. Leads and TARGETING HINTS only.

    ``competitor_pets_allowed_claim`` is carried through so the policy lane
    knows where to look first. It is never authority, never published, and can
    never settle a pets decision -- only a first-party read does that.
    """
    doc = _load(LEADS, {}) or {}
    out = []
    for r in ((doc.get("bringfido") or {}).get("leads") or []):
        out.append(observation(
            "COMPETITOR_LEAD", 4,
            r.get("directory_url") or "https://www.bringfido.com/",
            r.get("name"),
            street=r.get("street", ""), city=r.get("city", ""),
            region=r.get("region", ""), postal=r.get("postal_code", ""),
            phone=r.get("telephone", ""), lead_type=r.get("lead_type", ""),
            seen_in=r.get("seen_on_city", ""),
            competitor_pets_allowed_claim=r.get("competitor_pets_allowed_claim"),
            targeting_hint_only="a competitor claim is never policy authority",
        ))
    return out


# --------------------------------------------------------------------------- #
# The graph.
# --------------------------------------------------------------------------- #

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
        if pk:
            cand_keys.append("phone:" + pk)
        if code and brand:
            cand_keys.append("code:%s:%s" % (brand, code))
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
        if code and brand and ("street:" + sid) in by_key:
            other = nodes[by_key["street:" + sid]]
            if (other.property_code and other.brand
                    and other.brand.upper() == brand
                    and other.property_code.lower() != code):
                cand_keys = [k for k in cand_keys if not k.startswith("street:")]

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
            conflicts.append(OrderedDict([
                ("observation", obs),
                ("claimed_by", sorted({nodes[i].name for i in hits})),
                ("resolved_by", "BRAND_PROPERTY_CODE" if preferred is not None
                                else "LOWEST_ESTABLISHED_NODE"),
                ("why", "the observation's street identity, phone or property code matches more "
                        "than one already-established node"),
            ]))
            node = nodes[preferred if preferred is not None else min(hits)]
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
            if a and b and a != b and not any(
                    (k.startswith("phone:") or k.startswith("alias:")) and k in by_key
                    for k in cand_keys):
                node = Node()
                nodes.append(node)
                idx = len(nodes) - 1
        node.absorb(obs)
        for k in cand_keys:
            by_key.setdefault(k, idx)
            node.keys.add(k)
    return nodes, conflicts


# --------------------------------------------------------------------------- #
# Name attachment. A name PROPOSES; it never decides.
# --------------------------------------------------------------------------- #
#: Tokens that carry no distinguishing signal: every second hotel has them. The
#: market's own name is here on purpose -- "raleigh" is in most of these names
#: and therefore separates none of them.
_GENERIC_TOKENS = {
    "hotel", "hotels", "inn", "inns", "suites", "suite", "and", "by", "the", "of", "at",
    "a", "an", "motel", "lodge", "lodging", "resort", "conference", "center", "centre",
    "extended", "stay", "america", "select", "s", "raleigh",
    # PARENT COMPANIES. One source writes "Residence Inn by MARRIOTT Raleigh
    # Vanderbilt" and the next writes "Residence Inn Raleigh Vanderbilt";
    # counting the parent as distinguishing vocabulary halved the overlap in
    # Toledo and refused eleven correct bindings, including every Marriott and
    # Hilton route that market had already recovered for free. The SUB-brand is
    # what names the hotel. Raleigh adds the soft-brand collection words --
    # Autograph, Tribute Portfolio, Curio, Tapestry, Trademark, Ascend -- which
    # this market has far more of than any prior one and which likewise name a
    # programme rather than a building.
    "marriott", "hilton", "wyndham", "hyatt", "ihg", "choice", "radisson",
    "intercontinental", "sonesta", "g6", "curio", "collection", "tapestry",
    "autograph", "tribute", "portfolio", "trademark", "ascend", "bonvoy",
}
#: Municipalities inside this market. A name that STATES one of these is making
#: a claim about which town the building is in.
_IN_MARKET_MUNICIPALITIES = {
    # Wake County municipalities and the districts the corridor registry names.
    "cary", "morrisville", "apex", "garner", "wake forest", "knightdale",
    "holly springs", "fuquay varina", "fuquay", "varina", "rolesville",
    "wendell", "zebulon",
    "downtown", "north hills", "midtown", "crabtree", "crabtree valley",
    "glenwood", "glenwood south", "brier creek", "wakefield", "leesville",
    "north raleigh", "west raleigh", "east raleigh", "southeast raleigh",
    "wakemed", "capital boulevard", "capital blvd", "triangle town center",
    "ncsu", "nc state", "state fairgrounds", "pnc arena", "blue ridge",
    "crossroads", "weston", "parkside", "perimeter park", "rdu",
    "six forks", "falls of neuse", "new bern",
}
#: Places OUTSIDE this market that a lead source names. A soft row naming one of
#: these is not this building. Two mechanisms put them here. First, the five
#: FRINGE areas this order authored as corridors that claim no postal code:
#: naming one of them is naming a held building, not an admitted one. Second,
#: Marriott's CLT prefix, which is the Raleigh Douglas AIRPORT code and
#: reaches Shelby (cltby), Statesville (cltfv), Hickory (cltht), Salisbury
#: (cltsb), Mooresville, Monroe and Gastonia -- every one of them observed in
#: the committed owned roster, and the reason a code never admits a row.
_OUT_OF_MARKET_PLACES = {
    # Durham County. The single largest hazard in this market: the RDU airport
    # code, the "Raleigh-Durham" brand naming convention and the Research
    # Triangle Park label all reach across the county line.
    "durham", "research triangle park", "rtp", "southpoint", "brightleaf",
    "duke", "west durham", "north durham",
    # Orange County.
    "chapel hill", "carrboro", "hillsborough", "unc", "meadowmont",
    # Johnston, Franklin, Granville, Chatham, Lee, Harnett and beyond.
    "clayton", "smithfield", "selma", "benson", "four oaks", "kenly",
    "youngsville", "louisburg", "franklinton", "creedmoor", "butner",
    "pittsboro", "siler city", "sanford", "lillington", "angier", "dunn",
    "rocky mount", "henderson", "oxford", "roxboro", "burlington", "graham",
    "mebane", "goldsboro", "wilson", "greenville", "fayetteville",
    "winston salem", "greensboro", "raleigh", "asheville", "wilmington",
}
#: "Raleigh" is not a distinguishing word inside a hotel NAME -- most of this
#: market's hotels carry it -- but it is a real answer to "which town is this
#: building in", so it counts as a place for a building's own geography and
#: never for name scoring.
_ALL_PLACES = _IN_MARKET_MUNICIPALITIES | _OUT_OF_MARKET_PLACES | {"raleigh"}
#: Area and directional words. They are the difference between two hotels of the
#: same brand in the same town: this market has a dozen Courtyards and nine
#: SpringHill Suites whose names differ ONLY in the area word -- Raleigh
#: AIRPORT, AIRPORT NORTH, ARROWOOD, BALLANTYNE, CITY CENTER, MATTHEWS,
#: NORTHLAKE, SOUTHPARK, STEELE CREEK, UNIVERSITY RESEARCH PARK and WAVERLY --
#: so the area word is the whole difference between them.
_DIRECTIONALS = {
    "north", "south", "east", "west", "northwest", "northeast", "southwest", "southeast",
    "downtown", "midtown", "uptown", "airport", "university", "research", "park",
    "center", "centre", "city", "southpark", "ballantyne", "northlake", "arrowood",
    "steelecreek", "steele", "creek", "waverly", "piper", "glen", "loso",
    "carowinds", "speedway", "mills", "concord", "matthews", "pineville",
    "huntersville", "cornelius", "davidson", "norman", "lake", "birkdale",
    "tyvola", "yorkmont", "billy", "graham", "westinghouse", "rivergate",
    "berewick", "dilworth", "midwood", "plaza", "noda", "myers", "elizabeth",
    "gateway", "convention", "coliseum", "stadium", "mall", "campus", "medical",
    "corporate", "quail", "hollow", "carmel", "providence", "blakeney",
    "highland", "mallard", "prosperity", "sugar", "derita", "ayrsley",
    "belmont", "gastonia", "cramerton", "mill", "tega", "cay", "baxter",
    "kingsley", "indian", "land", "harrisburg", "wilkinson", "tryon",
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
            and t not in {w for p in _ALL_PLACES for w in p.split()}}


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
    named = {p for p in places if p != "raleigh"}
    return named or ({"raleigh"} if "raleigh" in places else set())


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
        for h in hard:
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
                if address_key(h.street, "") == key
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


#: Wyndham publishes the property's city as a segment of its own canonical URL
#: (".../baymont/northwood-ohio/..."). Validated on this market's own data before
#: it was trusted: three rows whose city the census already knew agreed, none
#: disagreed. This is a STRUCTURED field in the brand's location taxonomy and is
#: NOT the same thing as a brand's marketing name -- Hilton calls two Rossford
#: hotels by a two-town marketing name, so a name is never read as a city.
_WYNDHAM_URL_CITY = re.compile(r"wyndhamhotels\.com/[a-z0-9-]+/([a-z-]+)-ohio/", re.I)


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
        r["identity_key"] = normalize_name(proposed)
        r["identity_key_aliases"] = sorted(a for a in aliases if a)
        r["canonical_name_basis"] = named[-1]["basis"]
    return named


#: The states this market admits. Raleigh is the first PetTripFinder market
#: whose admitted corridors cross a state line: Fort Mill, Tega Cay and Indian
#: Land are in South Carolina, and the held Rock Hill corridor is there too. A
#: row whose OWN page states any other state is outside the market on that
#: evidence alone.
ADMITTED_STATES = frozenset({"NC", "NORTH CAROLINA"})


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


def classify(node, zips, name_counts, street_counts):
    n = normalize_name(node.name)
    if not n:
        return IDENTITY_REVIEW_REQUIRED, ("the only source that found this building published no "
                                          "name for it; an address without a name cannot be a "
                                          "published identity")
    lanes = {o["lane"] for o in node.observations}
    lead_types = {o.get("lead_type") for o in node.observations if o.get("lead_type")}

    if n in NOT_LODGING_NAMES or n in STR_PLACEHOLDERS:
        return NON_LODGING, "the source lists a business that is not lodging"
    if lead_types and lead_types <= NON_HOTEL_LEAD_TYPES:
        return NON_LODGING, "every lane that typed this row typed it %s" % sorted(lead_types)
    if lanes == {"COMPETITOR_LEAD"} and _RENTAL_WORDS.search(node.name or ""):
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
        return OUTSIDE_MARKET, ("the row's own state is %s; this market admits North Carolina "
                                "only -- every corridor of this market is in North Carolina "
                                "and the rule is Wake County, so a property whose own page "
                                "there too" % node.region)
    if node.postal and node.postal[:5] not in zips:
        return OUTSIDE_MARKET, ("postal code %s is claimed by no corridor of the Raleigh "
                                "contract. Four fringe areas -- Rock Hill SC, Kannapolis, "
                                "Mooresville/north Lake Norman and Monroe/Indian Trail/Waxhaw -- "
                                "are authored as corridors that deliberately claim NO postal "
                                "code and are HELD for a founder ruling; a row in one of their "
                                "ZIPs lands here on purpose, not by omission"
                                % node.postal[:5])
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
            return TRUE_HOTEL_IDENTITY, ""
        return SAME_CAMPUS_DISTINCT_ENTITY, (
            "another distinct identity states the same street identity, and this row states no "
            "brand property code and canonical first-party URL of its own, so the exclusion "
            "contract's co-located-distinct proof cannot be made for it; both rows are retained "
            "and neither is aliased")
    if name_counts.get(n, 0) > 1:
        return IDENTITY_REVIEW_REQUIRED, ("another node normalises to the same name at a different "
                                          "address; a same-brand same-city pair is demoted to "
                                          "review, never auto-aliased")
    return TRUE_HOTEL_IDENTITY, ""


def build():
    cfg, zips, corridor_state = corridor_index()
    explicit = explicit_index(cfg)
    lanes = OrderedDict([
        ("OSM_OVERPASS", read_osm()),
        ("BRAND_INVENTORY_OWNED", read_brand_owned()),
        ("BRAND_INVENTORY_CITY_PAGE", read_brand_city_pages()),
        ("BRAND_INVENTORY_SITEMAP", read_brand_sitemaps()),
        ("CVB_PARTNER", read_cvb()),
        ("COMPETITOR_LEAD", read_competitor()),
        ("PROPERTY_PAGE", read_property_pages()),
    ])
    all_obs = [o for rows in lanes.values() for o in rows]
    nodes, merge_conflicts = merge(all_obs)
    nodes, zipless_merged, zipless_ambiguous = merge_zipless(nodes)
    corridor_municipality = {}
    for n in nodes:
        cid = zips.get((n.postal or "")[:5], "")
        if cid:
            corridor_municipality[id(n)] = cid.split("__", 1)[-1].replace("-", " ")
    hard, bound, ambiguous, unbound = attach_name_only(nodes, corridor_municipality)
    nodes = hard + ambiguous + unbound

    # A same-brand, same-city PAIR is demoted to review rather than aliased.
    # The pair has to be a pair of BUILDINGS: only nodes that state a street or
    # a phone are counted. A name-only lead carries no address at all, so it
    # cannot be "another node at a different address" -- counting it demoted 47
    # fully-addressed, identity-confirmed Raleigh hotels because a BringFido
    # or destination-roster row happened to spell the same name.
    name_counts = Counter(normalize_name(n.name) for n in nodes
                          if n.street or n.phone)
    street_counts = Counter(street_identity(n.street, n.postal) for n in nodes
                            if street_identity(n.street, n.postal))

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
        _key = normalize_name(node.name)
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
            ("street_identity", street_identity(node.street, node.postal)),
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
    renamed = name_bare_identities(admitted)
    counts = Counter(r["classification"] for r in rows)
    confirmed = [r for r in rows if r["classification"] == TRUE_HOTEL_IDENTITY]
    by_corridor = Counter(r["corridor"] for r in confirmed)

    census = OrderedDict([
        ("schema", SCHEMA), ("market_id", MARKET_ID),
        ("status", "REGISTERED_CENSUS"),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER), ("captured_at", "2026-09-10"),
        ("note",
         "PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001 Raleigh census. Raleigh was built "
         "under the MODERN factory and has no legacy shadow market, so this census is written "
         "directly to identity_census/ -- the registered location -- rather than to a proposed "
         "directory it would later have to be promoted out of. No pinned census is overwritten: "
         "this order CREATES the file, and the release contract that pins its count is authored "
         "in the same registration batch. Every row carries the observations that produced it; "
         "nothing here carries a pet policy."),
        ("source_authorities", [
            "OpenStreetMap via the md5-verified Geofabrik North Carolina "
            "extracts, reduced to this market's bounding box (ODbL, "
            "(c) OpenStreetMap contributors)",
            "https://www.marriott.com/sitemap-index.xml (OWNED at zero requests, via "
            "dayton_oh_brand_directory_harvest_001, captured 2026-09-02)",
            "https://www.hilton.com/en/locations/usa/{north,south}-carolina/<city>/ "
            "(twenty-one city pages)",
            "https://www.wyndhamhotels.com/sitemap.xml (the brand's own property shards)",
            "https://www.sonesta.com/sitemap/sitemap-0.xml",
            "https://www.omnihotels.com/sitemap.xml",
            "https://www.loewshotels.com/sitemap-desktop.xml",
            "https://www.druryhotels.com/locations/raleigh-nc",
            "https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/raleigh",
            "https://www.bringfido.com/lodging/city/<city>/ (LEADS AND TARGETING HINTS ONLY)",
        ]),
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
         "A competitor row cannot enter Raleigh authority without first-party identity "
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
                    default=os.path.join(CENSUS_DIR, "raleigh-nc.json"))
    ap.add_argument("--report-out",
                    default=os.path.join(REPORTS, "raleigh_nc_census_reconciliation_001.json"))
    ap.add_argument("--gap-out",
                    default=os.path.join(REPORTS, "raleigh_nc_competitor_gap_matrix_001.json"))
    args = ap.parse_args(argv)
    census, report, rows, lanes = build()
    gaps = gap_matrix(rows, lanes)
    for path, doc in ((args.census_out, census), (args.report_out, report), (args.gap_out, gaps)):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
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

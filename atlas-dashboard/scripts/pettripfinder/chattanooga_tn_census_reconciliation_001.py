"""PTF-CHATTANOOGA-TN-NEW-MARKET-001 -- Phases 5, 6, 8 and 9: one identity graph.

Every free lane's observations are merged into one node per BUILDING, each node
is classified with the work order's own vocabulary, and the result is written as
Chattanooga's PROPOSED census. Nothing here is registered and nothing here
carries a pet policy.

WHAT DECIDES AN IDENTITY
-----------------------
Street identity (house number + distinctive street words + ZIP), a normalised
phone, or a brand property code inside its own family. Never a name alone, and
never "Chattanooga", "downtown", "airport", "Hamilton Place", "Lookout Mountain"
or a directional word. A name match whose addresses disagree is reported, never
merged.

WHAT DECIDES MEMBERSHIP
-----------------------
The proposed market contract's postal partition, and the row's own state. This
market admits TENNESSEE only. A row whose own source states a Georgia address is
NORTH_GEORGIA_FRINGE_HOLD -- a Phase 6 border classification that this market
carries explicitly rather than letting it fall silently into OUTSIDE_MARKET,
because the founder packet has to be able to see it and rule on it.

THE PIPELINE RUNS TWICE
-----------------------
census -> routing -> capture -> census. The first pass admits what the map, the
destination bureau's roster and the owned brand inventories can place. The
routing lane then carries every brand-roster row the first pass could NOT place
to its own property page, and this pass reads the address that page states and
feeds it back. A property code SELECTS a row; only the page ADMITS it.

Output:
  launch_packages/pettripfinder/identity_census_proposed/chattanooga-tn.json
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_census_reconciliation_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name      # noqa: E402
from scripts.pettripfinder.markets import contract as MC        # noqa: E402

WORK_ORDER = "PTF-CHATTANOOGA-TN-NEW-MARKET-001"
MARKET_ID = "chattanooga-tn"
SCHEMA = "ptf-market-identity-census/1.1"
REPORT_SCHEMA = "ptf-census-reconciliation/1.0"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PROPOSED_CENSUS_DIR = os.path.join(PKG, "identity_census_proposed")


def _first_existing(*paths):
    """The registered path if this market has been promoted, else the proposed one."""
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[-1]


CONTRACT_PATH = _first_existing(
    os.path.join(PKG, "markets", "chattanooga-tn.json"),
    os.path.join(PKG, "markets", "proposed", "chattanooga-tn.json"))

CANDIDATES = os.path.join(_DASH, "data", "discovery", "chattanooga_tn_001", "candidates",
                          "chattanooga-tn_candidates.json")
LEADS = os.path.join(REPORTS, "chattanooga_tn_lead_sources_001.json")
STATIC_CAPTURE = os.path.join(REPORTS, "chattanooga_tn_free_static_capture_001.json")
FIRECRAWL_PASS = os.path.join(REPORTS, "chattanooga_tn_firecrawl_pass_001.json")
ATTENDED_PASS = os.path.join(REPORTS, "chattanooga_tn_attended_capture_001.json")

# --------------------------------------------------------------------------- #
# Classification vocabulary (the work order's, verbatim, plus the Phase 6 hold).
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
#: Phase 6. A real lodging identity, correctly discovered, whose own page states
#: a GEORGIA address IN THE STATE-LINE BELT. Held OUT of the promoted set and
#: carried to the founder.
NORTH_GEORGIA_FRINGE_HOLD = "NORTH_GEORGIA_FRINGE_HOLD"
#: The Georgia postal codes that are genuinely a Chattanooga fringe: Catoosa,
#: Walker and Dade counties, which touch the state line and whose lodging sits
#: on the same I-75 and I-24 approaches as East Ridge and Lookout Valley. A
#: Georgia address OUTSIDE this belt is not a border question at all -- Dalton,
#: Calhoun, Rome and Ellijay are their own markets thirty to seventy miles away,
#: and Marriott's regional "cha" code prefix reaches every one of them.
GA_FRINGE_POSTAL_CODES = {
    "30736",  # Ringgold, Catoosa County
    "30742",  # Fort Oglethorpe, Catoosa County
    "30741",  # Rossville, Walker County
    "30707",  # Chickamauga, Walker County
    "30725",  # Flintstone, Walker County
    "30739",  # Rock Spring, Walker County
    "30750",  # Lookout Mountain, Walker County
    "30752",  # Trenton, Dade County
    "30738",  # Rising Fawn, Dade County
    "30757",  # Wildwood, Dade County
}

#: Businesses a lead source lists that are not lodging. Matched on the FULL
#: normalised name, never a substring, so a gallery called "Studio" can never
#: retire "Studio 6".
NOT_LODGING_NAMES = {
    "camp jordan arena sports complex", "lodge factory store",
    "lodge museum of cast iron cooking", "renaissance park", "renaissance commons",
    "chattanooga relocation services", "crye leike relocation services",
    "preserve chattanooga inc", "lookout mountain conservancy",
    "isha institute of inner sciences", "bridge innovate",
    # Sonesta publishes a LANDMARK page per point of interest, not only a
    # property page. "Hamilton Place Mall" and the two Erlanger hospital pages
    # are landmarks the brand indexes; none is a hotel identity, and the first
    # of them reached this run's capture lane before this rule existed.
    "hamilton place mall", "erlanger main hospital", "erlanger east hospital",
}
_RENTAL_WORDS = re.compile(
    r"\b(airbnb|vrbo|apartment|apt\b|condo|cottage|bungalow|treehouse|townhome|townhouse"
    r"|guest ?house|cabin|campground|rv park|rv resort|marina|rental)\b", re.I)


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
        for field in ("street", "city", "region", "postal", "phone", "brand",
                      "property_code", "route"):
            if not getattr(self, field) and obs.get(field):
                setattr(self, field, obs[field])
        if obs.get("lat") is not None and self.lat is None:
            self.lat, self.lng = obs.get("lat"), obs.get("lng")
        if len(obs.get("name") or "") > len(self.name):
            self.name = obs["name"]


def observation(lane, tier, source_url, name, **kw):
    o = OrderedDict([("lane", lane), ("tier", tier), ("source_url", source_url),
                     ("name", (name or "").strip())])
    for k, v in kw.items():
        if v not in (None, ""):
            o[k] = v
    return o


# --------------------------------------------------------------------------- #
# Lane readers.
# --------------------------------------------------------------------------- #

#: A map source's ``website`` tag is a FREE ROUTING lane -- OpenStreetMap
#: carries the property's own domain for a good share of independents, which is
#: the one thing no brand inventory can supply. It is a route proposal only: the
#: page's own address still has to confirm the identity. An aggregator or a
#: social page is not a property route.
_NOT_A_PROPERTY_ROUTE = re.compile(
    r"(facebook\.com|instagram\.com|twitter\.com|x\.com/|tripadvisor|booking\.com|expedia"
    r"|hotels\.com|yelp\.com|google\.com|linktr\.ee)", re.I)


def read_osm():
    rows = _load(CANDIDATES, []) or []
    out = []
    for r in rows:
        src = (r.get("source_records") or [{}])[0]
        website = (src.get("website_url") or "").strip()
        if website and _NOT_A_PROPERTY_ROUTE.search(website):
            website = ""
        postal = (r.get("postal_code") or src.get("postal_code") or "").strip()
        region = _region((r.get("state") or src.get("state") or "").strip())
        # A Georgia postal code is a Georgia address even when the map source
        # left the state tag empty. The Phase 6 border audit has to see it.
        if not region and postal[:2] == "30":
            region = "GA"
        elif not region and postal[:2] == "37":
            region = "TN"
        out.append(observation(
            "OSM_LOCAL_EXTRACT", 3,
            src.get("provider_place_url") or "https://www.openstreetmap.org/",
            r.get("name"),
            street=(r.get("address_line") or src.get("address_line") or "").strip(),
            city=(r.get("city") or src.get("city") or "").strip(),
            region=region,
            postal=postal,
            phone=(src.get("phone") or "").strip(),
            route=website,
            lat=r.get("latitude"), lng=r.get("longitude"),
            candidate_id=r.get("candidate_id"),
            osm_categories=src.get("provider_categories"),
            route_note=("the property's own website as OpenStreetMap states it; a route "
                        "proposal, confirmed only by the page's own address" if website else ""),
        ))
    return out


#: Which lane each lead source is, and which evidence tier it earns.
#: Tier 1 is a first-party brand inventory; tier 2 is the official destination
#: bureau; tier 3 is a map source.
_LEAD_LANES = {
    "OWNED_DAYTON_BRAND_HARVEST": ("BRAND_INVENTORY_OWNED", 1),
    "OWNED_CINCINNATI_BRAND_AUDIT": ("BRAND_INVENTORY_OWNED", 1),
    "HILTON_CITY_PAGE": ("BRAND_INVENTORY_CITY_PAGE", 1),
    "WYNDHAM_BRAND_SITEMAP": ("BRAND_INVENTORY_SITEMAP", 1),
    "DRURY_CITY_PAGE": ("BRAND_INVENTORY_CITY_PAGE", 1),
    "SONESTA_CITY_PAGE": ("BRAND_INVENTORY_CITY_PAGE", 1),
    "WOODSPRING_CITY_PAGE": ("BRAND_INVENTORY_CITY_PAGE", 1),
    "CVB_VISIT_CHATTANOOGA": ("CVB_DESTINATION_ROSTER", 2),
}


def read_leads():
    doc = _load(LEADS, {}) or {}
    lanes = {}
    for r in doc.get("leads", []):
        lane, tier = _LEAD_LANES.get(r.get("source") or "", ("LEAD_SOURCE", 3))
        name = (r.get("name") or "").replace("&#038;", "&").replace("&amp;", "&")
        obs = observation(
            lane, tier, r.get("source_url") or "", name,
            street=r.get("street") or "", city=r.get("city") or "",
            region=_region(r.get("region") or ""), postal=(r.get("postal_code") or "")[:5],
            phone=r.get("phone") or "", brand=r.get("family") or "",
            property_code=r.get("property_code") or "",
            route=r.get("source_url") or "",
            merge_alias=normalize_name(name),
            lat=_num(r.get("latitude")), lng=_num(r.get("longitude")),
            lead_note=r.get("note") or "",
        )
        lanes.setdefault(lane, []).append(obs)
    return lanes


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _region(value):
    v = (value or "").strip()
    low = v.lower()
    if low in ("tn", "tennessee"):
        return "TN"
    if low in ("ga", "georgia"):
        return "GA"
    if low in ("al", "alabama"):
        return "AL"
    return v.upper() if len(v) == 2 else v


def read_property_pages():
    """The address a property's OWN page states -- tier 1, and the only thing
    allowed to turn a brand-roster row into a Chattanooga identity.

    Three lanes write this evidence in three shapes, and one reader folds them:
    the static and Firecrawl reports carry an ``identity_assessment`` block, and
    the attended report carries ``identity_signals``. In every case the fields
    read are the ones the PAGE stated about itself.
    """
    out = []
    for path, lane in ((STATIC_CAPTURE, "PROPERTY_PAGE_STATIC"),
                       (FIRECRAWL_PASS, "PROPERTY_PAGE_FIRECRAWL"),
                       (ATTENDED_PASS, "PROPERTY_PAGE_ATTENDED")):
        doc = _load(path, {}) or {}
        for r in doc.get("rows") or []:
            sig = ((r.get("identity_assessment") or {}).get("signals")
                   or r.get("identity_signals") or {})
            confirmed = r.get("identity_confirmed")
            if confirmed is None:
                confirmed = (r.get("identity_assessment") or {}).get("confirmed")
            street = sig.get("address_on_page") or ""
            phone = sig.get("phone_on_page") or ""
            if not (street or phone):
                continue
            # An UNCONFIRMED identity is never allowed to state an address for a
            # census row: that is how one hotel's page becomes another's record.
            if not confirmed:
                continue
            out.append(observation(
                lane, 1, r.get("final_url") or r.get("requested_url") or "",
                sig.get("name_on_page") or r.get("canonical_name") or "",
                street=street,
                city=sig.get("locality") or sig.get("city") or "",
                region=_region(sig.get("region") or ""),
                postal=(sig.get("postal_code") or "")[:5],
                phone=phone,
                brand=r.get("brand") or r.get("family") or "",
                property_code=(sig.get("property_code_on_page")
                               or r.get("property_code") or ""),
                route=r.get("final_url") or r.get("requested_url") or "",
                merge_alias=normalize_name(r.get("canonical_name")
                                           or sig.get("name_on_page") or ""),
                read_for_identity_key=r.get("identity_key") or "",
                binding_method=(r.get("identity_binding_method")
                                or "CANONICAL_PATH_AND_NAME"),
                content_sha256=r.get("page_sha256") or "",
                market_verdict=r.get("market_verdict") or "",
            ))
    return out


# --------------------------------------------------------------------------- #
# The graph.
# --------------------------------------------------------------------------- #

def merge(observations):
    """One node per building. Keyed on street identity, phone or property code."""
    nodes, by_key, conflicts = [], {}, []
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
        if pk:
            cand_keys.append("phone:" + pk)
        if code and brand:
            cand_keys.append("code:%s:%s" % (brand, code))
        hits = {by_key[k] for k in cand_keys if k in by_key}
        if len(hits) > 1:
            conflicts.append(OrderedDict([
                ("observation", obs),
                ("claimed_by", sorted({nodes[i].name for i in hits})),
                ("why", "the observation's street identity, phone or property code matches more "
                        "than one already-established node"),
            ]))
            node = nodes[min(hits)]
        elif hits:
            node = nodes[hits.pop()]
        else:
            node = Node()
            nodes.append(node)
        idx = nodes.index(node)
        # Address disagreement blocks the merge rather than overwriting it.
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
#: Tokens that carry no distinguishing signal. The market's own name is here on
#: purpose: "chattanooga" is in most of these names and separates none of them.
#: The PARENT COMPANIES are here for the reason Toledo measured -- one source
#: writes "Residence Inn by MARRIOTT Chattanooga" and the next writes "Residence
#: Inn Chattanooga", and counting the parent as distinguishing vocabulary
#: refuses correct bindings. The sub-brand is what names the hotel.
_GENERIC_TOKENS = {
    "hotel", "hotels", "inn", "inns", "suites", "suite", "and", "by", "the", "of", "at",
    "a", "an", "motel", "lodge", "lodging", "resort", "conference", "center", "centre",
    "extended", "stay", "america", "select", "s", "chattanooga", "tn", "tennessee",
    "marriott", "hilton", "wyndham", "hyatt", "ihg", "choice", "radisson",
    "intercontinental", "sonesta", "g6", "collection", "autograph", "tribute",
    "portfolio", "member", "design",
}
#: Municipalities and named communities inside this market. A name that STATES
#: one of these is making a claim about which town the building is in.
_IN_MARKET_MUNICIPALITIES = {
    "east ridge", "red bank", "hixson", "ooltewah", "collegedale", "apison", "harrison",
    "signal mountain", "soddy daisy", "soddy", "lakesite", "walden", "ridgeside",
    "lupton city", "middle valley",
}
#: Places OUTSIDE this market that a lead source names. Every one was observed
#: in this run's own evidence: the Marriott and Hilton "cha" prefixes reach
#: Cleveland TN, Dalton GA, Calhoun GA, Ellijay GA and Rome GA, and the
#: destination bureau promotes a multi-state region well beyond Hamilton County.
#: "Cleveland" is here for a second reason: Cleveland, OHIO is a LIVE market,
#: and a Cleveland, TENNESSEE row must never bind to it.
_OUT_OF_MARKET_PLACES = {
    "cleveland", "kimball", "sewanee", "monteagle", "jasper", "south pittsburg",
    "whitwell", "dunlap", "pikeville", "spring city", "dayton", "decatur", "athens",
    "etowah", "sweetwater", "madisonville", "crossville", "tracy city", "manchester",
    "tullahoma", "winchester", "nashville", "knoxville", "murfreesboro",
    # north Georgia and north-east Alabama, over the state line
    "dalton", "calhoun", "ellijay", "rome", "ringgold", "fort oglethorpe", "ft oglethorpe",
    "rossville", "chickamauga", "lafayette", "trenton", "rising fawn", "summerville",
    "blue ridge", "cartersville", "adairsville", "chatsworth", "fort payne", "scottsboro",
    "stevenson", "bridgeport",
}
_ALL_PLACES = _IN_MARKET_MUNICIPALITIES | _OUT_OF_MARKET_PLACES | {"chattanooga"}
#: Area and directional words: the difference between two hotels of the same
#: brand in the same town. "Lookout Mountain" is HERE and not in the municipality
#: set on purpose -- almost every hotel that carries the name sits in Chattanooga
#: or Tiftonia, not in the small town of Lookout Mountain, Tennessee, so reading
#: it as a municipality claim would reject correct bindings.
_DIRECTIONALS = {
    "north", "south", "east", "west", "northwest", "northeast", "southwest", "southeast",
    "downtown", "uptown", "midtown", "airport", "riverfront", "waterfront", "southside",
    "northshore", "shore", "lookout", "mountain", "valley", "tiftonia", "brainerd",
    "hamilton", "place", "shallowford", "gunbarrel", "northgate", "elmo", "choo",
    "cameron", "harbor", "university", "hospital", "mall", "campus", "ridge",
}
_NAME_MATCH_THRESHOLD = 0.75


def places_in(text: str):
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

    The STREET is deliberately excluded: a street name carries directionals that
    are not areas of town.
    """
    blob = " ".join(x for x in (node.city, node.name, corridor_municipality) if x)
    return places_in(blob), directionals_in(blob)


def specific_municipality(places):
    named = {p for p in places if p != "chattanooga"}
    return named or ({"chattanooga"} if "chattanooga" in places else set())


def attachment_verdict(soft_name, node, corridor_municipality=""):
    """May this name-only observation attach to this building? Say why not."""
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
    """Bind a name-only observation to at most ONE established building."""
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

    ``address_key`` puts the ZIP in the key, so a source printing a street with
    no postal can never meet the same building's row that has one.
    """
    with_zip = [n for n in nodes if n.street and n.postal]
    without = [n for n in nodes if n.street and not n.postal]
    merged, ambiguous, absorbed = [], [], set()
    for n in without:
        key = address_key(n.street, "")
        hits = [h for h in with_zip
                if address_key(h.street, "") == key
                and not (n.city and h.city
                         and normalize_name(n.city) != normalize_name(h.city))]
        if len(hits) != 1:
            if hits:
                ambiguous.append(OrderedDict([("name", n.name), ("street", n.street),
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


#: How American sources spell the same street. Every substitution below was
#: forced by a PAIR this run actually split into two census rows:
#:   "Two Carter Plaza" vs "2 Carter Plaza"          (Chattanooga Marriott Downtown)
#:   "3801 Cummings Highway" vs "3801 Cummings Hwy." (Days Inn Lookout Mountain West)
#:   "105 West Main Street" vs "105 W. Main St"      (Caption by Hyatt Downtown)
_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
}
_STREET_SUFFIX = {
    "street": "st", "avenue": "ave", "av": "ave", "road": "rd", "drive": "dr",
    "boulevard": "blvd", "highway": "hwy", "parkway": "pkwy", "lane": "ln",
    "place": "pl", "court": "ct", "circle": "cir", "terrace": "ter", "turnpike": "tpke",
    "square": "sq", "trail": "trl", "expressway": "expy", "plaza": "plz",
}
_STREET_DIRECTIONAL = {
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
}


def loose_street_key(street: str) -> str:
    """A street identity that survives how two sources chose to spell it.

    Deliberately NOT a replacement for ``address_key``: it drops the postal code,
    so on its own it would merge two buildings on the same-numbered street in
    different towns. It is only ever used by the pass below, which additionally
    requires exactly one candidate, agreeing cities, and a second corroborating
    signal.
    """
    s = re.sub(r"[^a-z0-9 ]+", " ", (street or "").lower())
    toks = [t for t in s.split() if t]
    toks = [_NUMBER_WORDS.get(t, t) for t in toks]
    toks = [_STREET_DIRECTIONAL.get(t, t) for t in toks]
    toks = [_STREET_SUFFIX.get(t, t) for t in toks]
    number = toks[0] if toks and toks[0].isdigit() else ""
    words = [t for t in toks[1:] if not t.isdigit()
             and t not in set(_STREET_DIRECTIONAL.values())
             and t not in set(_STREET_SUFFIX.values())
             and t not in ("ste", "suite", "unit", "the")]
    if not number:
        number = next((t for t in toks if t.isdigit()), "")
        words = [t for t in toks if not t.isdigit()
                 and t not in set(_STREET_DIRECTIONAL.values())
                 and t not in set(_STREET_SUFFIX.values())
                 and t not in ("ste", "suite", "unit", "the")]
    return "%s|%s" % (number, " ".join(words[:2])) if number and words else ""


def merge_same_building_spelled_differently(nodes):
    """A THIRD pass, for one building whose sources spelled its street apart.

    ``address_key`` is exact on both the street words and the postal code, which
    is the right default: it never merges two buildings. It also never merges ONE
    building that a map source wrote as "2 Carter Plaza" and the hotel wrote as
    "Two Carter Plaza", or that the bureau put in 37402 and the map put in 37408.
    Five real Chattanooga hotels were split into pairs here and then demoted to
    IDENTITY_REVIEW_REQUIRED for normalising to the same name at "different"
    addresses.

    The merge is allowed only when ALL of these hold:
      * the loose street keys are equal;
      * exactly ONE candidate matches, so a tie is never resolved by guessing;
      * the two do not name different cities;
      * and a second signal corroborates -- the same postal code, the same
        phone, or overlapping brand vocabulary in the two names.
    """
    merged, ambiguous, absorbed = [], [], set()
    keyed = [(n, loose_street_key(n.street)) for n in nodes]
    keyed = [(n, k) for n, k in keyed if k]
    for i, (n, key) in enumerate(keyed):
        if id(n) in absorbed:
            continue
        hits = []
        for j, (m, k2) in enumerate(keyed):
            if j <= i or k2 != key or id(m) in absorbed:
                continue
            if n.city and m.city and normalize_name(n.city) != normalize_name(m.city):
                continue
            same_zip = bool(n.postal and m.postal and n.postal[:5] == m.postal[:5])
            same_phone = bool(phone_key(n.phone) and phone_key(n.phone) == phone_key(m.phone))
            shared_brand = bool(chain_tokens(n.name) & chain_tokens(m.name))
            if same_zip or same_phone or shared_brand:
                hits.append((m, same_zip, same_phone, shared_brand))
        if len(hits) != 1:
            if hits:
                ambiguous.append(OrderedDict([
                    ("name", n.name), ("street", n.street), ("loose_key", key),
                    ("candidates", [h[0].name for h in hits])]))
            continue
        m, same_zip, same_phone, shared_brand = hits[0]
        why = ("the two sources spelled one building's street differently (%r and %r); exactly "
               "one building matched on the normalised street, the cities do not disagree, and "
               "%s corroborates"
               % (n.street, m.street,
                  " and ".join([x for x, ok in (("the postal code", same_zip),
                                                ("the phone", same_phone),
                                                ("the brand vocabulary in both names",
                                                 shared_brand)) if ok])))
        for obs in m.observations:
            o = OrderedDict(obs)
            o["binding"] = "STREET_IDENTITY_SPELLING_NORMALISED"
            o["binding_reason"] = why
            n.observations.append(o)
        for field in ("street", "city", "region", "postal", "phone", "brand",
                      "property_code", "route"):
            if not getattr(n, field) and getattr(m, field):
                setattr(n, field, getattr(m, field))
        if n.lat is None and m.lat is not None:
            n.lat, n.lng = m.lat, m.lng
        if len(m.name) > len(n.name):
            n.name = m.name
        absorbed.add(id(m))
        merged.append(OrderedDict([("absorbed", m.name), ("into", n.name),
                                   ("street", n.street), ("postal_code", n.postal),
                                   ("loose_key", key), ("why", why)]))
    return [n for n in nodes if id(n) not in absorbed], merged, ambiguous


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
            r["city"] = next(iter(peers))
            r["city_basis"] = ("every other admitted identity in postal code %s states this city"
                               % r["postal_code"])
            filled.append(OrderedDict([("identity_key", r["identity_key"]),
                                       ("city", r["city"]), ("basis", r["city_basis"])]))
        else:
            unfilled.append(OrderedDict([("identity_key", r["identity_key"]),
                                         ("street", r["street"]),
                                         ("postal_code", r["postal_code"])]))
    return filled, unfilled


def corridor_index():
    cfg = MC.parse_market(_load(CONTRACT_PATH), source=CONTRACT_PATH)
    zips = {}
    for c in cfg.corridors:
        for z in c.included_postal_codes:
            zips[z] = c.corridor_id
    return cfg, zips


#: Brand words that identify a chain. Two distinct ones on one address means the
#: building changed hands or flag, which is a LINEAGE question and not a merge
#: error.
_BRAND_WORDS = {
    "marriott", "hilton", "hyatt", "radisson", "wyndham", "choice", "sheraton", "westin",
    "renaissance", "courtyard", "residence", "towneplace", "springhill", "fairfield",
    "doubletree", "embassy", "candlewood", "staybridge", "holiday", "crowne", "ramada",
    "baymont", "super", "days", "quality", "comfort", "sleep", "clarion", "econo",
    "travelodge", "howard", "johnson", "roof", "studio", "woodspring", "sonesta",
    "drury", "western", "quinta", "home2", "tru", "element", "aloft", "hampton",
    "homewood", "delta", "spark", "wingate", "hawthorn", "microtel", "motel6", "moxy",
    "kinley", "edwin", "dwell", "caption", "knights", "mainstay", "intown", "douglas",
    "chanticleer", "clemons", "indigo", "chattanoogan",
}


def distinct_brand_signatures(node):
    sigs = []
    for obs in node.observations:
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

    if n in NOT_LODGING_NAMES:
        return NON_LODGING, "the source lists a business that is not lodging"
    if lanes <= {"CVB_DESTINATION_ROSTER"} and _RENTAL_WORDS.search(node.name or ""):
        return NON_LODGING, ("a destination-bureau listing that reads as a private dwelling, a "
                             "campground or a marina rather than a hotel identity")
    if node.ambiguous_matches:
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
    # Phase 6, the Tennessee/Georgia border. Ruled BEFORE the postal partition so
    # a Georgia row is never reported as a mere unclaimed ZIP.
    if node.region and node.region.upper() in ("GA", "GEORGIA"):
        z = (node.postal or "")[:5]
        if z in GA_FRINGE_POSTAL_CODES:
            return NORTH_GEORGIA_FRINGE_HOLD, (
                "the row's own page states a GEORGIA address (%s, %s) in the Catoosa / Walker / "
                "Dade county belt that touches the state line and genuinely serves Chattanooga "
                "travelers. This market admits Tennessee only, so the identity is real, correctly "
                "discovered, and HELD for a founder ruling. It is not a discovery failure."
                % (node.city or "city not stated", z or "no postal"))
        return OUTSIDE_MARKET, (
            "the row's own page states a GEORGIA address (%s, %s). It is not in the state-line "
            "belt that serves this market -- Dalton, Calhoun, Rome and Ellijay are their own "
            "markets thirty to seventy miles away -- so it is outside, not a border hold. The "
            "brand's property code selected it; the page's own address rejected it."
            % (node.city or "city not stated", z or "no postal"))
    if node.region and node.region.upper() not in ("TN", "TENNESSEE"):
        return OUTSIDE_MARKET, ("the row's own state is %s; this market admits Tennessee only"
                                % node.region)
    if node.postal and node.postal[:5] not in zips:
        return OUTSIDE_MARKET, ("postal code %s is claimed by no corridor of the proposed "
                                "Chattanooga contract" % node.postal[:5])
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
        return SAME_CAMPUS_DISTINCT_ENTITY, ("another distinct identity states the same street "
                                             "identity; both are retained and neither is aliased")
    if name_counts.get(n, 0) > 1:
        return IDENTITY_REVIEW_REQUIRED, ("another node normalises to the same name at a different "
                                          "address; a same-brand same-city pair is demoted to "
                                          "review, never auto-aliased")
    return TRUE_HOTEL_IDENTITY, ""


def build():
    cfg, zips = corridor_index()
    lane_obs = read_leads()
    lanes = OrderedDict()
    lanes["OSM_LOCAL_EXTRACT"] = read_osm()
    for key in ("BRAND_INVENTORY_OWNED", "BRAND_INVENTORY_CITY_PAGE",
                "BRAND_INVENTORY_SITEMAP", "CVB_DESTINATION_ROSTER", "LEAD_SOURCE"):
        lanes[key] = lane_obs.get(key, [])
    lanes["PROPERTY_PAGE"] = read_property_pages()

    all_obs = [o for rows in lanes.values() for o in rows]
    nodes, merge_conflicts = merge(all_obs)
    nodes, zipless_merged, zipless_ambiguous = merge_zipless(nodes)
    nodes, spelling_merged, spelling_ambiguous = merge_same_building_spelled_differently(nodes)
    corridor_municipality = {}
    for n in nodes:
        cid = zips.get((n.postal or "")[:5], "")
        if cid:
            corridor_municipality[id(n)] = cid.split("__", 1)[-1].replace("-", " ")
    hard, bound, ambiguous, unbound = attach_name_only(nodes, corridor_municipality)
    nodes = hard + ambiguous + unbound

    name_counts = Counter(normalize_name(n.name) for n in nodes)
    street_counts = Counter(street_identity(n.street, n.postal) for n in nodes
                            if street_identity(n.street, n.postal))

    rows = []
    for node in nodes:
        klass, why = classify(node, zips, name_counts, street_counts)
        z = (node.postal or "")[:5]
        aliases = sorted({normalize_name(o.get("name") or "") for o in node.observations
                          if (o.get("name") or "").strip()}
                         | {o["read_for_identity_key"] for o in node.observations
                            if o.get("read_for_identity_key")})
        rows.append(OrderedDict([
            ("identity_key", normalize_name(node.name)),
            ("identity_key_aliases", [a for a in aliases if a]),
            ("canonical_name", node.name),
            ("classification", klass),
            ("classification_reason", why),
            ("street", node.street), ("city", node.city),
            ("state", node.region or ("TN" if z in zips else "")),
            ("postal_code", z), ("phone", node.phone),
            ("phone_key", phone_key(node.phone)),
            ("street_identity", street_identity(node.street, node.postal)),
            ("brand", node.brand), ("property_code", node.property_code),
            ("official_url", node.route),
            ("latitude", node.lat), ("longitude", node.lng),
            ("corridor", zips.get(z, "")),
            ("assignment_basis", "postal_code" if z in zips else ""),
            ("assignment_value", z if z in zips else ""),
            ("lanes", sorted({o["lane"] for o in node.observations})),
            ("best_tier", min(o["tier"] for o in node.observations)),
            ("policy_state", "POLICY_NOT_VERIFIED"),
            ("policy_note", "Identity evidence never establishes a pet policy."),
            ("evidence", node.observations),
        ]))

    rows.sort(key=lambda r: (r["classification"], r["identity_key"]))
    admitted = [r for r in rows if r["classification"] == TRUE_HOTEL_IDENTITY]
    city_filled, city_unfilled = fill_missing_cities(admitted)
    counts = Counter(r["classification"] for r in rows)
    by_corridor = Counter(r["corridor"] for r in admitted)
    border = [r for r in rows if r["classification"] == NORTH_GEORGIA_FRINGE_HOLD]

    census = OrderedDict([
        ("schema", SCHEMA), ("market_id", MARKET_ID),
        ("status", "PROPOSED_NOT_REGISTERED"),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER),
        ("captured_at", time.strftime("%Y-%m-%d", time.gmtime())),
        ("note",
         "PTF-CHATTANOOGA-TN-NEW-MARKET-001 proposed Chattanooga census. It lives in "
         "identity_census_proposed/ and NOT in identity_census/, because the registered census "
         "directory is contract-pinned and adding a market there registers it. Every row carries "
         "the observations that produced it; nothing here carries a pet policy."),
        ("source_authorities", [
            "https://download.geofabrik.de/north-america/us/tennessee-latest.osm.pbf (ODbL, "
            "(c) OpenStreetMap contributors)",
            "https://www.visitchattanooga.com/sitemap.xml (Chattanooga Tourism Co., identity only)",
            "https://www.hilton.com/en/locations/usa/tennessee/chattanooga/",
            "https://www.marriott.com/sitemap-index.xml (owned, via "
            "dayton_oh_brand_directory_harvest_001)",
            "https://www.wyndhamhotels.com/sitemap.xml",
            "https://www.druryhotels.com/locations/chattanooga-tn",
            "https://www.sonesta.com/locations/us/tennessee/chattanooga",
            "https://www.woodspring.com/extended-stay-hotels/locations/tennessee/chattanooga/hotels",
        ]),
        ("count", len(admitted)),
        ("total_candidates", len(rows)),
        ("classification_counts", OrderedDict(sorted(counts.items()))),
        ("corridor_counts", OrderedDict(sorted(by_corridor.items()))),
        ("hotels", admitted),
        ("non_admitted", [r for r in rows if r["classification"] != TRUE_HOTEL_IDENTITY]),
    ])

    report = OrderedDict([
        ("schema", REPORT_SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "5, 6, 8 and 9 -- census reconciliation into one identity graph"),
        ("what_decides_an_identity",
         "Street identity (house number + distinctive street words + ZIP), a normalised phone, or "
         "a brand property code inside its own family. Never a name alone, and never Chattanooga, "
         "downtown, airport, Hamilton Place, Lookout Mountain or a directional token. A name "
         "match whose addresses disagree is reported, never merged."),
        ("what_decides_membership",
         "The proposed market contract's postal partition AND the row's own state. A Georgia "
         "address is NORTH_GEORGIA_FRINGE_HOLD, never a silent OUTSIDE_MARKET, so the founder "
         "packet can rule on it."),
        ("this_runs_twice",
         "census -> routing -> capture -> census. A property code SELECTS a row; only the page "
         "ADMITS it."),
        ("lane_yields", OrderedDict((k, len(v)) for k, v in lanes.items())),
        ("observations_total", len(all_obs)),
        ("nodes_after_hard_key_merge", len(nodes)),
        ("merge_conflicts", merge_conflicts),
        ("zipless_second_pass", OrderedDict([
            ("merged", zipless_merged), ("ambiguous", zipless_ambiguous)])),
        ("spelling_third_pass", OrderedDict([
            ("what_it_is",
             "address_key is exact on both the street words and the postal code, so it never "
             "merges two buildings -- and never merges ONE building whose sources wrote 'Two "
             "Carter Plaza' and '2 Carter Plaza', 'Cummings Highway' and 'Cummings Hwy.', or put "
             "the same street in two postal codes. This pass merges only on a normalised street "
             "key, with exactly one candidate, agreeing cities, and a corroborating postal code, "
             "phone or brand vocabulary."),
            ("merged", spelling_merged), ("ambiguous", spelling_ambiguous)])),
        ("name_attachment", OrderedDict([
            ("bound", len(bound)), ("ambiguous", len(ambiguous)), ("unbound", len(unbound)),
            ("bindings", [OrderedDict([("observation_name", s_.name), ("bound_to", h_.name),
                                       ("score", sc)]) for s_, h_, sc in bound]),
            ("ambiguous_rows", [OrderedDict([("name", n.name),
                                             ("candidates", n.ambiguous_matches)])
                                for n in ambiguous]),
            ("unbound_rows_with_a_same_brand_candidate", [
                OrderedDict([("name", n.name), ("rejected_candidates", n.rejections)])
                for n in unbound if n.rejections]),
        ])),
        ("classification_counts", OrderedDict(sorted(counts.items()))),
        ("corridor_counts", OrderedDict(sorted(by_corridor.items()))),
        ("tennessee_georgia_border_audit", OrderedDict([
            ("rule", "This market admits Tennessee municipalities only. A property whose OWN "
                     "source states a Georgia address is held, whatever its marketing name says."),
            ("held", len(border)),
            ("rows", [OrderedDict([("canonical_name", r["canonical_name"]),
                                   ("city", r["city"]), ("state", r["state"]),
                                   ("postal_code", r["postal_code"]),
                                   ("official_url", r["official_url"])]) for r in border]),
        ])),
        ("city_fill", OrderedDict([("filled", city_filled), ("unfilled", city_unfilled)])),
    ])
    return census, report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--census-out", default=os.path.join(
        PROPOSED_CENSUS_DIR, "chattanooga-tn.json"))
    ap.add_argument("--report-out", default=os.path.join(
        REPORTS, "chattanooga_tn_census_reconciliation_001.json"))
    args = ap.parse_args(argv)

    census, report = build()
    for path, doc in ((args.census_out, census), (args.report_out, report)):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
            fh.write("\n")
    print("observations        : %d" % report["observations_total"])
    print("lane yields         : %s" % json.dumps(report["lane_yields"]))
    print("nodes               : %d" % report["nodes_after_hard_key_merge"])
    print("classifications     : %s" % json.dumps(report["classification_counts"]))
    print("TRUE_HOTEL_IDENTITY : %d" % census["count"])
    print("GA border held      : %d" % report["tennessee_georgia_border_audit"]["held"])
    print("corridors           : %s" % json.dumps(report["corridor_counts"]))
    print("census              : %s" % os.path.relpath(args.census_out, _DASH).replace("\\", "/"))
    print("report              : %s" % os.path.relpath(args.report_out, _DASH).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""PTF-TOLEDO-OH-NEW-MARKET-001 -- Phases 5, 6 and 8: one identity graph.

Four independent discovery lanes ran for Toledo, none of them authoritative on
its own:

  OSM_LOCAL_EXTRACT   80 candidates from the Geofabrik Ohio extract, reduced to
                      this market's bbox and answered offline (0 network calls).
  BRAND_INVENTORY     Marriott TOL* and Wyndham/Sonesta/WoodSpring Ohio rows,
                      OWNED from the committed Dayton and Cleveland harvests,
                      plus Hilton's TOL* roster read from its own city page.
  CVB_PARTNER         Destination Toledo's own partner roster (tier 2).
  COMPETITOR_LEAD     BringFido's Toledo-area city pages (tier 4, leads only).

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
The proposed market contract's postal partition, and nothing else. A Michigan
row, an Ottawa County row or a row in an unclaimed ZIP is OUTSIDE_MARKET with
its ZIP recorded, so the decision is reviewable rather than implicit.

Nothing here fetches. Nothing here writes outside Toledo artifacts. Nothing here
carries a pet policy: identity evidence never establishes one.

Outputs:
  launch_packages/pettripfinder/identity_census_proposed/toledo-oh.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_census_reconciliation_001.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_competitor_gap_matrix_001.json
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

WORK_ORDER = "PTF-TOLEDO-OH-NEW-MARKET-001"
MARKET_ID = "toledo-oh"
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
PROPOSED_CENSUS_DIR = os.path.join(PKG, "identity_census_proposed")
CONTRACT_PATH = _first_existing(os.path.join(PKG, "markets", "toledo-oh.json"),
                                os.path.join(PKG, "markets", "proposed", "toledo-oh.json"))

CANDIDATES = os.path.join(_DASH, "data", "discovery", "toledo_oh_001", "candidates",
                          "toledo-oh_candidates.json")
STATIC_CAPTURE = os.path.join(REPORTS, "toledo_oh_free_static_capture_001.json")
FIRECRAWL_PASS = os.path.join(REPORTS, "toledo_oh_firecrawl_pass_001.json")
ATTENDED_PASS = os.path.join(REPORTS, "toledo_oh_attended_capture_001.json")
OWNED = os.path.join(REPORTS, "toledo_oh_owned_evidence_001.json")
CITY_PAGES = os.path.join(REPORTS, "toledo_oh_brand_city_pages_001.json")
LEADS = os.path.join(REPORTS, "toledo_oh_lead_sources_001.json")

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
    "art bound studio", "copper moon studio gallery and gifts", "firenation glass studio and gallery",
    "great lakes studios", "huron street studios", "spin and splat art studio", "sunshine studios",
    "ice breaker lounge at maumee bay lodge", "key hotel and property management",
}
#: Categories a competitor lead can carry that are not a hotel identity.
NON_HOTEL_LEAD_TYPES = {"Campground"}
#: Short-term-rental aggregator placeholders BringFido lists as if they were
#: properties. They name a marketplace, not a building.
STR_PLACEHOLDERS = {"toledo airbnb rentals", "vrbo toledo", "airbnb toledo", "vrbo rentals"}

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
        for field in ("street", "city", "region", "postal", "phone", "brand",
                      "property_code", "route"):
            if not getattr(self, field) and obs.get(field):
                setattr(self, field, obs[field])
        if obs.get("lat") is not None and self.lat is None:
            self.lat, self.lng = obs.get("lat"), obs.get("lng")
        # The longest name wins: "Courtyard by Marriott Toledo Maumee/Arrowhead"
        # is a better display identity than the OSM node's bare "Courtyard".
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

def read_osm():
    rows = _load(CANDIDATES, []) or []
    out = []
    for r in rows:
        src = (r.get("source_records") or [{}])[0]
        out.append(observation(
            "OSM_LOCAL_EXTRACT", 3,
            src.get("provider_place_url") or "https://www.openstreetmap.org/",
            r.get("name"),
            street=(r.get("address_line") or "").strip(),
            city=(r.get("city") or "").strip(),
            region="OH",
            postal=(r.get("postal_code") or "").strip(),
            phone=(src.get("phone") or "").strip(),
            lat=r.get("latitude"), lng=r.get("longitude"),
            candidate_id=r.get("candidate_id"),
            osm_categories=src.get("provider_categories"),
        ))
    return out


_MARRIOTT = re.compile(r"marriott\.com/en-us/hotels/([a-z0-9]{5,7})-([a-z0-9-]+)/overview", re.I)
_WYNDHAM = re.compile(r"wyndhamhotels\.com/([a-z0-9-]+)/([a-z-]+)-ohio/([a-z0-9-]+)/overview", re.I)


def _titlecase(slug):
    return " ".join(w.capitalize() for w in (slug or "").replace("-", " ").split())


def read_brand_owned():
    doc = _load(OWNED, {}) or {}
    out = []
    for r in doc.get("owned_leads", []):
        url, fam = r["url"], r["family"]
        name, code = "", r.get("property_code", "")
        m = _MARRIOTT.search(url)
        if m:
            code, name = m.group(1).lower(), _titlecase(m.group(2))
        else:
            w = _WYNDHAM.search(url)
            if w:
                name = _titlecase(w.group(3))
            else:
                name = _titlecase(url.rstrip("/").rsplit("/", 1)[-1])
        out.append(observation(
            "BRAND_INVENTORY_OWNED", 1, url, name,
            brand=fam, property_code=code, route=url, merge_alias=normalize_name(name),
            admitted_by=r.get("admitted_by"), seen_in=", ".join(r.get("seen_in") or []),
        ))
    return out


def read_brand_city_pages():
    doc = _load(CITY_PAGES, {}) or {}
    out = []
    for code, r in ((doc.get("hilton") or {}).get("codes") or {}).items():
        out.append(observation(
            "BRAND_INVENTORY_CITY_PAGE", 1, r["route"], _titlecase(r["slug"]),
            brand="HILTON", property_code=code, route=r["route"],
            merge_alias=normalize_name(_titlecase(r["slug"])),
            admitted_by=r.get("selected_by"),
            seen_in=", ".join(r.get("seen_on_city_pages") or []),
        ))
    return out


def read_cvb():
    doc = _load(LEADS, {}) or {}
    out = []
    for r in ((doc.get("official_destination_partner_roster") or {}).get("rows") or []):
        if r.get("status") != 200:
            continue
        nm = (r.get("name") or "").replace("&#038;", "&").replace("&amp;", "&")
        out.append(observation(
            "CVB_PARTNER", 2, r["url"], nm,
            street=r.get("street", ""), city=r.get("city", ""),
            region="OH" if (r.get("region") or "").lower().startswith("ohio") else r.get("region", ""),
            postal=r.get("postal_code", ""), phone=r.get("telephone", ""),
        ))
    return out


def read_property_pages():
    """The address a property's OWN page states -- tier 1, and the only thing
    allowed to turn a brand-roster row into a Toledo identity.

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
            region=(sig.get("region") or "").strip()[:2].upper(),
            phone=(sig.get("phone_on_page") or "").strip(),
            property_code=(sig.get("property_code_on_page") or "").strip(),
            brand=r.get("brand"), route=r.get("requested_url"),
            document_bytes=r.get("document_bytes"),
            binding_method=r.get("identity_binding_method"),
        ))
    return out


def read_competitor():
    doc = _load(LEADS, {}) or {}
    out = []
    for bucket in ("leads_in_market_state", "leads_outside_market_state"):
        for r in doc.get(bucket, []):
            out.append(observation(
                "COMPETITOR_LEAD", 4, r.get("competitor_url") or "https://www.bringfido.com/",
                r.get("name"),
                street=r.get("street", ""), city=r.get("city", ""),
                region=r.get("region", ""), postal=r.get("postal_code", ""),
                phone=r.get("telephone", ""), lead_type=r.get("lead_type", ""),
                seen_in=", ".join(r.get("seen_on_city_pages") or []),
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
        hits = {by_key[k] for k in cand_keys if k in by_key}
        if len(hits) > 1:
            # Two established nodes claim this observation. Never guess.
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
#: market's own name is here on purpose -- "toledo" is in most of these names
#: and therefore separates none of them.
_GENERIC_TOKENS = {
    "hotel", "hotels", "inn", "inns", "suites", "suite", "and", "by", "the", "of", "at",
    "a", "an", "motel", "lodge", "lodging", "resort", "conference", "center", "centre",
    "extended", "stay", "america", "select", "s", "toledo",
    # PARENT COMPANIES. One source writes "Residence Inn by MARRIOTT Toledo
    # Maumee" and the next writes "Residence Inn Toledo Maumee"; counting the
    # parent as distinguishing vocabulary halved the overlap and refused eleven
    # correct bindings, including every Marriott and Hilton route this market
    # had already recovered for free. The sub-brand is what names the hotel.
    "marriott", "hilton", "wyndham", "hyatt", "ihg", "choice", "radisson",
    "intercontinental", "sonesta",
}
#: Municipalities inside this market. A name that STATES one of these is making
#: a claim about which town the building is in.
_IN_MARKET_MUNICIPALITIES = {
    "maumee", "perrysburg", "rossford", "sylvania", "holland", "oregon", "northwood",
    "swanton", "walbridge", "millbury", "waterville", "whitehouse", "monclova",
    "bowling green",
}
#: Places OUTSIDE this market that a lead source names. A soft row naming one of
#: these is not this building: BringFido's Toledo hub links Monroe, Milan, Erie
#: and Luna Pier, and Marriott's TOL prefix reaches Findlay, Fostoria, Wauseon
#: and Port Clinton. Each was observed doing exactly that in this run.
_OUT_OF_MARKET_PLACES = {
    "monroe", "milan", "dundee", "temperance", "lambertville", "erie", "luna pier",
    "la salle", "ottawa lake", "adrian", "tecumseh", "ann arbor", "findlay", "fostoria",
    "wauseon", "napoleon", "defiance", "fremont", "port clinton", "sandusky", "clyde",
    "oak harbor", "genoa", "bellevue", "catawba", "put in bay", "archbold", "bryan",
}
#: "Toledo" is not a distinguishing word inside a hotel NAME, but it is a real
#: answer to "which town is this building in", so it counts as a place for a
#: building's own geography and never for name scoring.
_ALL_PLACES = _IN_MARKET_MUNICIPALITIES | _OUT_OF_MARKET_PLACES | {"toledo"}
#: Area and directional words. They are the difference between two hotels of the
#: same brand in the same town: Courtyard Toledo WEST and Courtyard Toledo NORTH.
_DIRECTIONALS = {
    "north", "south", "east", "west", "northwest", "northeast", "southwest", "southeast",
    "downtown", "university", "westgate", "airport", "arrowhead", "levis", "commons",
    "central", "secor", "glendale", "alexis", "meadows", "franklin", "mall", "campus",
    "riverfront", "waterfront",
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
    named = {p for p in places if p != "toledo"}
    return named or ({"toledo"} if "toledo" in places else set())


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
    without a postal often enough that this split three real Toledo hotels
    (Renaissance Toledo Downtown, Delta Hotels Toledo, Red Roof Toledo/Maumee)
    into pairs. This pass offers each postal-less row to the rows that DO carry
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


def corridor_index():
    cfg = MC.parse_market(_load(CONTRACT_PATH), source=CONTRACT_PATH)
    zips = {}
    for c in cfg.corridors:
        for z in c.included_postal_codes:
            zips[z] = c.corridor_id
    return cfg, zips


#: Brand words that identify a chain. Two of these on one address means the
#: building changed hands or flag, which is a lineage question and not a merge
#: error: 3100 Glendale Avenue is BOTH "Radisson Hotel at The University of
#: Toledo" and "Delta Hotels by Marriott Toledo" in this run's evidence.
_BRAND_WORDS = {
    "marriott", "hilton", "hyatt", "radisson", "wyndham", "choice", "sheraton", "westin",
    "renaissance", "courtyard", "residence", "towneplace", "springhill", "fairfield",
    "doubletree", "embassy", "candlewood", "staybridge", "holiday", "crowne", "ramada",
    "baymont", "super", "days", "quality", "comfort", "sleep", "clarion", "econo",
    "travelodge", "howard", "johnson", "roof", "studio", "woodspring", "sonesta",
    "drury", "western", "quinta", "home2", "tru", "element", "aloft", "hampton",
    "homewood", "delta", "spark", "wingate", "hawthorn", "microtel", "motel6",
}


def distinct_brand_signatures(node):
    """The distinct chain identities the evidence gives this one building."""
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
    lead_types = {o.get("lead_type") for o in node.observations if o.get("lead_type")}

    if n in NOT_LODGING_NAMES or n in STR_PLACEHOLDERS:
        return NON_LODGING, "the source lists a business that is not lodging"
    if lead_types and lead_types <= NON_HOTEL_LEAD_TYPES:
        return NON_LODGING, "every lane that typed this row typed it %s" % sorted(lead_types)
    if lanes == {"COMPETITOR_LEAD"} and _RENTAL_WORDS.search(node.name or ""):
        return NON_LODGING, ("a competitor short-term-rental listing, named only by the competitor "
                             "and reading as a private dwelling; never a hotel identity")
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
    if node.region and node.region.upper() not in ("OH", "OHIO"):
        return OUTSIDE_MARKET, "the row's own state is %s; this market admits Ohio only" % node.region
    if node.postal and node.postal[:5] not in zips:
        return OUTSIDE_MARKET, ("postal code %s is claimed by no corridor of the proposed Toledo "
                                "contract" % node.postal[:5])
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
    lanes = OrderedDict([
        ("OSM_LOCAL_EXTRACT", read_osm()),
        ("BRAND_INVENTORY_OWNED", read_brand_owned()),
        ("BRAND_INVENTORY_CITY_PAGE", read_brand_city_pages()),
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

    name_counts = Counter(normalize_name(n.name) for n in nodes)
    street_counts = Counter(street_identity(n.street, n.postal) for n in nodes
                            if street_identity(n.street, n.postal))

    rows = []
    for node in nodes:
        klass, why = classify(node, zips, name_counts, street_counts)
        z = (node.postal or "")[:5]
        # Every key any lane used for this building. A read captured under the
        # brand roster's name for a property must still find its census row
        # after the merge renamed it, or a clean read is silently orphaned.
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
            ("state", node.region or ("OH" if z in zips else "")),
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
    counts = Counter(r["classification"] for r in rows)
    confirmed = [r for r in rows if r["classification"] == TRUE_HOTEL_IDENTITY]
    by_corridor = Counter(r["corridor"] for r in confirmed)

    census = OrderedDict([
        ("schema", SCHEMA), ("market_id", MARKET_ID),
        ("status", "PROPOSED_NOT_REGISTERED"),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER), ("captured_at", "2026-09-06"),
        ("note",
         "PTF-TOLEDO-OH-NEW-MARKET-001 proposed Toledo census. It lives in "
         "identity_census_proposed/ and NOT in identity_census/, because the registered census "
         "directory is contract-pinned and adding a market there registers it. Every row carries "
         "the observations that produced it; nothing here carries a pet policy."),
        ("source_authorities", [
            "https://download.geofabrik.de/north-america/us/ohio-latest.osm.pbf (ODbL, "
            "(c) OpenStreetMap contributors)",
            "https://visittoledo.org/partner-sitemap.xml",
            "https://www.hilton.com/en/locations/usa/ohio/toledo/",
            "https://www.marriott.com/sitemap-index.xml (owned, via "
            "dayton_oh_brand_directory_harvest_001)",
            "https://www.wyndhamhotels.com/sitemap.xml (owned, via the Dayton and Cleveland "
            "harvests)",
            "https://www.bringfido.com/lodging/city/toledo_oh_us/ (LEADS ONLY)",
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
         "A competitor row cannot enter Toledo authority without first-party identity "
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
                    default=os.path.join(PROPOSED_CENSUS_DIR, "toledo-oh.json"))
    ap.add_argument("--report-out",
                    default=os.path.join(REPORTS, "toledo_oh_census_reconciliation_001.json"))
    ap.add_argument("--gap-out",
                    default=os.path.join(REPORTS, "toledo_oh_competitor_gap_matrix_001.json"))
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

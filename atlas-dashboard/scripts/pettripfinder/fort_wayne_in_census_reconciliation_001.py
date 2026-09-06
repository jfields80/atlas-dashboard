"""PTF-FORT-WAYNE-IN-NEW-MARKET-001 -- Phase 5/6/8 (census reconciliation).

Fold every free discovery lane into ONE Fort Wayne identity graph, classify each
candidate, and emit the market's proposed shadow census.

Lanes folded (all zero-cost, all first-party except the last):
  OSM        fort_wayne_in_osm_census_sweep_001.json         identity, varying quality
  BRAND      fort_wayne_in_brand_directory_harvest_001.json  official brand inventory
  CVB        fort_wayne_in_cvb_directory_harvest_001.json    official tourism directory
  COMPETITOR fort_wayne_in_competitor_leads_001.json         LEADS ONLY, never authority

THE JOIN RULE, AND WHY IT IS NOT THE NAME

A name PROPOSES an identity; it never decides one. This market makes the reason
concrete several times over: "Hampton Inn" names a property on West Jefferson
Boulevard and another on Dupont Road; "Fairfield Inn & Suites by Marriott"
appears twice in the CVB under one slug; and Marriott issues the FWA-prefixed
code ``fwafw`` to a Fairfield Inn in WARSAW, forty miles outside this market.

So two observations merge only on a STRONG key:

  ADDRESS   street number + street words + ZIP, DIRECTIONALS KEPT
  PHONE     ten digits
  CODE      brand property code, always scoped to its brand family

and never merge when a strong key CONTRADICTS: two rows with different ZIPs, or
different street numbers, or different codes in the same family, stay apart no
matter how identical their names are. Observations that share only a name key
and carry no address at all are not merged either -- they are emitted as
NAME_ONLY_UNRESOLVED for review.

The directional survives the address key on purpose. A key that folds "W" and
"E" away nearly un-published a live Cincinnati hotel by merging two buildings on
the same-numbered street; ``hotel_exclusions.address_key`` still drops them, so
this module does not reuse it.

MEMBERSHIP is decided by the committed market-membership contract on the
market's own declared geography, never by which city page a lane filed a row
under. A row inside the box is not thereby admitted, and a row with no geography
is UNRESOLVED for review rather than asserted to be outside.

Nothing here publishes and nothing here is policy evidence.

Outputs:
  launch_packages/pettripfinder/markets/reports/fort_wayne_in_census_reconciliation_001.json
  launch_packages/pettripfinder/identity_census_proposed/fort-wayne-in.json
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

from scripts.pettripfinder.contracts.identity_key import (  # noqa: E402
    IdentityKeyError, ptf_identity_key,
)
from scripts.pettripfinder.discovery import market_membership as MM  # noqa: E402
from scripts.pettripfinder.discovery.market_config import load_market_config  # noqa: E402
from scripts.pettripfinder.markets import contract as MC  # noqa: E402

WORK_ORDER = "PTF-FORT-WAYNE-IN-NEW-MARKET-001"
MARKET_ID = "fort-wayne-in"
SCHEMA = "ptf-census-reconciliation/1.0"
CENSUS_SCHEMA = "ptf-market-identity-census/1.1"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PROPOSED = os.path.join(PKG, "identity_census_proposed")

OSM_REPORT = os.path.join(REPORTS, "fort_wayne_in_osm_census_sweep_001.json")
BRAND_REPORT = os.path.join(REPORTS, "fort_wayne_in_brand_directory_harvest_001.json")
CVB_REPORT = os.path.join(REPORTS, "fort_wayne_in_cvb_directory_harvest_001.json")
COMPETITOR_REPORT = os.path.join(REPORTS, "fort_wayne_in_competitor_leads_001.json")

# --------------------------------------------------------------------------- #
# Keys
# --------------------------------------------------------------------------- #

#: Street-type words that carry no distinguishing information. DIRECTIONALS ARE
#: NOT HERE, and that is the point of this list existing separately.
_STREET_TYPES = {
    "st", "street", "rd", "road", "dr", "drive", "ave", "avenue", "blvd",
    "boulevard", "pkwy", "parkway", "ln", "lane", "ct", "court", "pl", "place",
    "cir", "circle", "way", "trl", "trail", "hwy", "highway", "ste", "suite",
    "unit", "expy", "expressway", "ext",
}
#: Directional forms folded to ONE spelling each -- folded together, never away.
_DIRECTIONALS = {
    "n": "n", "north": "n", "s": "s", "south": "s", "e": "e", "east": "e",
    "w": "w", "west": "w", "ne": "ne", "northeast": "ne", "nw": "nw",
    "northwest": "nw", "se": "se", "southeast": "se", "sw": "sw",
    "southwest": "sw",
}


def address_parts(street: str, postal_code: str):
    """``(number, directions, words, zip)`` -- the parts of a building address.

    OpenStreetMap permits a semicolon-separated multi-value ``addr:street``, and
    this market carries one ("West Jefferson Blvd;West Jefferson Blvd"). Reading
    it whole turns the tail into a phantom street word and splits a building off
    from itself, so only the first value is read.
    """
    first_value = (street or "").split(";")[0]
    text = re.sub(r"[^a-z0-9 ]", " ", first_value.lower())
    tokens = [t for t in text.split() if t]
    number = ""
    for t in tokens:
        m = re.match(r"^(\d+)$", t)
        if m:
            number = m.group(1)
            break
    directions = frozenset(_DIRECTIONALS[t] for t in tokens if t in _DIRECTIONALS)
    words = tuple(sorted(t for t in tokens
                         if not t[:1].isdigit()
                         and t not in _STREET_TYPES
                         and t not in _DIRECTIONALS))
    zip5 = (postal_code or "").strip()[:5]
    if not number or not words:
        return None
    return (number, directions, words, zip5)


def address_key(street: str, postal_code: str) -> str:
    """The printable form of :func:`address_parts`, for reports and audits."""
    parts = address_parts(street, postal_code)
    if parts is None:
        return ""
    number, directions, words, zip5 = parts
    return "%s|%s|%s|%s" % (number, "".join(sorted(directions)),
                            " ".join(words), zip5)


def same_building(a, b) -> bool:
    """Do two address parts name one building?

    Number, street words and ZIP must all agree. The DIRECTIONAL must not
    CONTRADICT -- which is not the same as must match. A source that omits the
    direction has not asserted a different one, and OSM omits it where the CVB
    states it ("7001 IN 930" against "7001 IN 930 East"); treating that absence
    as a contradiction split a building off from itself. Two rows that each
    state a direction, differently, are two buildings and never merge.
    """
    if a is None or b is None:
        return False
    if (a[0], a[2], a[3]) != (b[0], b[2], b[3]):
        return False
    if a[1] and b[1] and a[1] != b[1]:
        return False
    return True


def phone_key(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def code_key(family: str, code: str) -> str:
    """A property code is an identity only WITHIN its brand family."""
    if not family or not code:
        return ""
    return "%s:%s" % (family.upper(), code.lower())


def name_key(name: str) -> str:
    try:
        return ptf_identity_key(name)
    except IdentityKeyError:
        return ""


#: A brand page that answers 200 without serving the property asked for. The
#: title is the only thing that says so -- the status does not.
_SOFT_404_TITLE = re.compile(
    r"^\s*(search results|hotels? in |find hotels|extended stay hotels in )", re.I)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


# --------------------------------------------------------------------------- #
# Observations
# --------------------------------------------------------------------------- #

def observation(lane, source_id, name, street="", city="", state="IN",
                postal_code="", phone="", url="", family="", code="",
                latitude=None, longitude=None, note=""):
    return OrderedDict([
        ("lane", lane), ("source_id", source_id), ("name", (name or "").strip()),
        ("street", (street or "").strip()), ("city", (city or "").strip()),
        ("state", (state or "").strip()), ("postal_code", (postal_code or "").strip()[:5]),
        ("phone", (phone or "").strip()), ("url", (url or "").strip()),
        ("brand_family", (family or "").strip()), ("property_code", (code or "").strip()),
        ("latitude", latitude), ("longitude", longitude), ("note", note),
    ])


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def load_observations():
    obs, lanes = [], OrderedDict()

    osm = _load(OSM_REPORT)
    if osm:
        for r in osm["rows"]:
            obs.append(observation(
                "OSM", r["osm_id"], r["name"], r["street"], r["city"],
                r["state"] or "IN", r["postal_code"], r["phone"], r["website"],
                latitude=r["latitude"], longitude=r["longitude"]))
        lanes["OSM"] = len(osm["rows"])

    brand = _load(BRAND_REPORT)
    if brand:
        n = 0
        for c in brand.get("candidates", []):
            page = c.get("page") or {}
            ident = page.get("identity") or {}
            if page.get("status") != 200:
                continue
            # A brand that answers 200 with its SEARCH page for a retired slug
            # has not served a property, and its page still carries a name --
            # "Search Results". Admitting that name invented a Fort Wayne hotel
            # called Search Results and then reported it as a name collision.
            # A soft 404 settles nothing and contributes no observation.
            if _SOFT_404_TITLE.search(page.get("title") or ""):
                continue
            nm = (ident.get("name_on_page") or "").strip()
            if not nm:
                continue
            obs.append(observation(
                "BRAND", c["url"], nm,
                ident.get("address_on_page") or "", "", "IN",
                ident.get("postal_code") or "",
                ident.get("phone_on_page") or "",
                page.get("final_url") or c["url"],
                c["family"],
                (ident.get("property_code_on_page") or c.get("property_code") or ""),
                note="selected_by=%s" % c.get("selected_by", "")))
            n += 1
        lanes["BRAND"] = n

    cvb = _load(CVB_REPORT)
    if cvb:
        n = 0
        for r in cvb["rows"]:
            if r["classification"] not in ("LODGING", "OUT_OF_CURRENT_CATEGORY"):
                continue
            # The CVB's JSON-LD ``url`` is the CVB's OWN listing address, not the
            # hotel's website -- it renders its outbound "Visit Website" link
            # client-side, so a plain client never sees one. Carrying the listing
            # URL forward as ``official_url`` routed 22 independents at the
            # DIRECTORY instead of at the property, which is precisely the thing a
            # directory must never become. A self-referential URL is dropped: the
            # CVB contributes address, city, postal and telephone here, and no
            # route.
            website = r["official_website"] or ""
            if "visitfortwayne.com" in website.lower():
                website = ""
            obs.append(observation(
                "CVB", r["cvb_url"], r["name"], r["street"], r["city"],
                r["region"] or "IN", r["postal_code"], r["telephone"],
                website, latitude=r["latitude"],
                longitude=r["longitude"],
                note="cvb_classification=%s" % r["classification"]))
            n += 1
        lanes["CVB"] = n

    comp = _load(COMPETITOR_REPORT)
    if comp:
        n = 0
        for r in comp["leads"]:
            if r["shape"] != "HOTEL_SHAPE":
                continue
            obs.append(observation(
                "COMPETITOR", r["name"], r["name"], r["street"], r["city"],
                "IN", r["postal_code"],
                note="LEAD ONLY -- competitor rows carry no first-party evidence"))
            n += 1
        lanes["COMPETITOR"] = n

    return obs, lanes


# --------------------------------------------------------------------------- #
# Clustering
# --------------------------------------------------------------------------- #

def cluster(observations):
    """Union observations on strong keys only; never on a name alone."""
    parent = list(range(len(observations)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_number, by_phone, by_code = {}, {}, {}
    for i, o in enumerate(observations):
        parts = address_parts(o["street"], o["postal_code"])
        pk = phone_key(o["phone"])
        ck = code_key(o["brand_family"], o["property_code"])
        o["_address_parts"] = parts
        o["_address_key"] = address_key(o["street"], o["postal_code"])
        o["_phone_key"], o["_code_key"] = pk, ck
        o["_name_key"] = name_key(o["name"])
        if parts:
            by_number.setdefault((parts[0], parts[3]), []).append(i)
        if pk:
            by_phone.setdefault(pk, []).append(i)
        if ck:
            by_code.setdefault(ck, []).append(i)

    # Phone and property code are exact keys: equal means the same property.
    for bucket in (by_phone, by_code):
        for members in bucket.values():
            for j in members[1:]:
                union(members[0], j)

    # Address is a compatibility join, not an exact key, and every pair that
    # shares a street number and ZIP but does NOT agree on the street is
    # recorded rather than silently split -- those pairs are this market's real
    # identity questions (one building the sources name two ways, or two
    # buildings that happen to share a number).
    number_conflicts = []
    for (number, zip5), members in by_number.items():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                i, j = members[x], members[y]
                a = observations[i]["_address_parts"]
                b = observations[j]["_address_parts"]
                if same_building(a, b):
                    union(i, j)
                else:
                    number_conflicts.append(OrderedDict([
                        ("street_number", number), ("postal_code", zip5),
                        ("a", OrderedDict([("lane", observations[i]["lane"]),
                                           ("name", observations[i]["name"]),
                                           ("street", observations[i]["street"])])),
                        ("b", OrderedDict([("lane", observations[j]["lane"]),
                                           ("name", observations[j]["name"]),
                                           ("street", observations[j]["street"])])),
                        ("why", "same street number and ZIP, but the street itself "
                                "does not agree; not merged"),
                    ]))

    groups = OrderedDict()
    for i in range(len(observations)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values()), number_conflicts


def _first(values):
    for v in values:
        if v:
            return v
    return ""


#: Lane precedence when two lanes state the same field differently. A brand's
#: own property page outranks a tourism directory, which outranks a community
#: map, which outranks a competitor -- which supplies nothing but a name.
_LANE_RANK = {"BRAND": 0, "CVB": 1, "OSM": 2, "COMPETITOR": 3}


def merge_group(indexes, observations):
    rows = sorted((observations[i] for i in indexes),
                  key=lambda o: _LANE_RANK.get(o["lane"], 9))
    name = _first([r["name"] for r in rows])
    postal = _first([r["postal_code"] for r in rows])
    street = _first([r["street"] for r in rows])
    city = _first([r["city"] for r in rows])
    phone = _first([r["phone"] for r in rows])
    code = _first([r["property_code"] for r in rows])
    family = _first([r["brand_family"] for r in rows])
    lat = _first([r["latitude"] for r in rows]) or None
    lng = _first([r["longitude"] for r in rows]) or None
    url = _first([r["url"] for r in rows if r["lane"] == "BRAND"]) or \
        _first([r["url"] for r in rows])

    lanes = sorted({r["lane"] for r in rows})
    postals = sorted({r["postal_code"] for r in rows if r["postal_code"]})
    streets = sorted({address_key(r["street"], r["postal_code"]) for r in rows
                      if address_key(r["street"], r["postal_code"])})
    return OrderedDict([
        ("canonical_name", name), ("street", street), ("city", city),
        ("state", "IN"), ("postal_code", postal), ("phone", phone),
        ("brand_family", family), ("property_code", code), ("official_url", url),
        ("latitude", lat), ("longitude", lng),
        ("lanes", lanes), ("observation_count", len(rows)),
        ("distinct_postal_codes", postals),
        ("distinct_address_keys", streets),
        ("observations", rows),
    ])


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #

EXACT_UNIQUE_IDENTITY = "EXACT_UNIQUE_IDENTITY"
DUPLICATE_LISTING = "DUPLICATE_LISTING"
SAME_CAMPUS_DISTINCT_ENTITY = "SAME_CAMPUS_DISTINCT_ENTITY"
NAME_ONLY_UNRESOLVED = "NAME_ONLY_UNRESOLVED"
ADDRESS_CONFLICT = "ADDRESS_CONFLICT"
IDENTITY_REVIEW_REQUIRED = "IDENTITY_REVIEW_REQUIRED"
OUTSIDE_MARKET = "OUTSIDE_MARKET"
NON_LODGING = "NON_LODGING"

#: A name that only a competitor lane ever stated, with no address anywhere, is
#: a lead and not an identity.
def classify(group, membership_outcome):
    lanes = set(group["lanes"])
    if membership_outcome == MM.OUT_OF_GEOGRAPHY:
        return OUTSIDE_MARKET, "the row's own stated geography places it outside the market"
    if len(group["distinct_address_keys"]) > 1:
        return ADDRESS_CONFLICT, ("observations disagree on the building: %s"
                                  % group["distinct_address_keys"])
    if len(group["distinct_postal_codes"]) > 1:
        return ADDRESS_CONFLICT, ("observations disagree on the postal code: %s"
                                  % group["distinct_postal_codes"])
    if not group["street"]:
        if lanes == {"COMPETITOR"}:
            return NAME_ONLY_UNRESOLVED, ("named only by a competitor directory, "
                                          "with no street address from any lane")
        return NAME_ONLY_UNRESOLVED, "no lane states a street address for this name"
    if membership_outcome == MM.UNRESOLVED:
        return IDENTITY_REVIEW_REQUIRED, ("the row states a street but its geography "
                                          "cannot settle market membership")
    return EXACT_UNIQUE_IDENTITY, "one building, corroborated and inside the market"


def build(args):
    market = load_market_config(MARKET_ID)
    observations, lanes = load_observations()
    print("observations", len(observations), json.dumps(lanes), flush=True)

    groups_raw, number_conflicts = cluster(observations)
    groups = [merge_group(g, observations) for g in groups_raw]

    # Same-campus detection: two DIFFERENT identities at one address key. Done
    # after merging, because merging is what would have hidden them.
    by_addr = {}
    for g in groups:
        for ak in g["distinct_address_keys"]:
            by_addr.setdefault(ak, []).append(g)

    out = []
    for g in groups:
        candidate = {
            "city": g["city"], "state": g["state"],
            "postal_code": g["postal_code"],
            "latitude": g["latitude"], "longitude": g["longitude"],
        }
        outcome, why, _ = MM.decide(
            candidate, basis=MC.MEMBERSHIP_MARKET_GEOGRAPHY,
            corridor_of_zip={}, coords_in_bounds=None, geography=market)
        state, reason = classify(g, outcome)
        g = OrderedDict(g)
        g["membership_outcome"] = outcome
        g["membership_reason"] = why
        g["classification"] = state
        g["classification_reason"] = reason
        g["identity_key"] = name_key(g["canonical_name"])
        g["slug"] = slugify(g["canonical_name"])
        out.append(g)

    for ak, members in by_addr.items():
        if len(members) > 1:
            keys = sorted({m["identity_key"] for m in members
                           for m in [m]})
            for g in out:
                if ak in g["distinct_address_keys"] and \
                        g["classification"] == EXACT_UNIQUE_IDENTITY:
                    g["classification"] = SAME_CAMPUS_DISTINCT_ENTITY
                    g["classification_reason"] = (
                        "another distinct identity shares this address key (%s); "
                        "co-located properties need an explicit identity ruling "
                        "before either publishes" % ak)
                    g["same_address_group"] = sorted(keys)

    # A name shared by two DIFFERENT identity groups is an alias question, not
    # an answer: it is surfaced for review and never resolved by merging.
    by_name = {}
    for g in out:
        if g["identity_key"]:
            by_name.setdefault(g["identity_key"], []).append(g)
    name_collisions = []
    for key, members in sorted(by_name.items()):
        if len(members) > 1:
            name_collisions.append(OrderedDict([
                ("identity_key", key),
                ("groups", [OrderedDict([("canonical_name", m["canonical_name"]),
                                         ("street", m["street"]),
                                         ("postal_code", m["postal_code"]),
                                         ("lanes", m["lanes"])]) for m in members]),
                ("why", "one normalized name over two buildings; an alias or a "
                        "rebrand ruling is required before either publishes"),
            ]))
            for m in members:
                if m["classification"] == EXACT_UNIQUE_IDENTITY:
                    m["classification"] = IDENTITY_REVIEW_REQUIRED
                    m["classification_reason"] = (
                        "another distinct building normalizes to the same identity "
                        "key %r" % key)

    out.sort(key=lambda g: (g["classification"], g["canonical_name"].lower()))
    return market, observations, lanes, out, number_conflicts, name_collisions


def report(market, observations, lanes, groups, number_conflicts, name_collisions):
    confirmed = [g for g in groups if g["classification"] == EXACT_UNIQUE_IDENTITY]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "5/6/8 -- census reconciliation and proposed shadow census"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("what_this_is",
         "Every free discovery lane folded into one identity graph. Observations merge "
         "only on a STRONG key -- address (directionals kept), ten-digit phone, or a "
         "brand-scoped property code -- and never on a name, which only proposes an "
         "identity. A contradicting strong key blocks the merge outright. Market "
         "membership is decided by the committed market-membership contract on the "
         "market's declared geography. Nothing here is policy evidence and nothing "
         "here publishes."),
        ("census_membership_basis", MC.MEMBERSHIP_MARKET_GEOGRAPHY),
        ("lane_observation_counts", lanes),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("counts", OrderedDict([
            ("observations", len(observations)),
            ("identity_groups", len(groups)),
            ("by_classification",
             OrderedDict(sorted(Counter(g["classification"] for g in groups).items()))),
            ("by_membership",
             OrderedDict(sorted(Counter(g["membership_outcome"] for g in groups).items()))),
            ("confirmed_active_identities", len(confirmed)),
            ("multi_lane_corroborated",
             sum(1 for g in groups if len(g["lanes"]) > 1)),
            ("with_official_url", sum(1 for g in confirmed if g["official_url"])),
            ("with_property_code", sum(1 for g in confirmed if g["property_code"])),
            ("same_number_street_disagreements", len(number_conflicts)),
            ("name_collisions_across_buildings", len(name_collisions)),
        ])),
        ("same_number_street_disagreement", number_conflicts),
        ("name_collisions_across_buildings", name_collisions),
        ("groups", groups),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "fort_wayne_in_census_reconciliation_001.json"))
    args = ap.parse_args(argv)
    market, observations, lanes, groups, number_conflicts, name_collisions = build(args)
    rep = report(market, observations, lanes, groups, number_conflicts, name_collisions)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

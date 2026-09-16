"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phases 8-10: one identity graph.

Cloned from the Savannah GA / Lexington KY census helpers; Augusta tokens and
Augusta's own postal-code corridor partition (augusta_ga_geography_001).

INDEPENDENT DISCOVERY LANES, NONE AUTHORITATIVE ON ITS OWN
-----------------------------------------------------------
  OSM_OVERPASS         tourism=hotel/motel elements inside the observation box,
                       read from the local Geofabrik Georgia + South Carolina
                       extracts (data/discovery/augusta_ga/discovery_001).
  BRAND_INVENTORY_OWNED the committed national Marriott harvest (AGS-coded routes).
  BRAND_STATE_SITEMAP_PAGE  Marriott's own Georgia hotel sitemap page.
  BRAND_CITY_PAGE      Hilton's own Georgia + two South Carolina city pages
                       (property cards stating each hotel's address).
  BRAND_SITEMAP        Wyndham's and WoodSpring's own sitemaps.

WHAT DECIDES AN IDENTITY
------------------------
Address, postal code, phone or brand property code. Never a name on its own.

WHAT DECIDES MEMBERSHIP
------------------------
The market contract's postal-code partition (augusta_ga_geography_001.classify_postal).
A brand's marketing name ("Fort Gordon Area", "Washington Rd.") NEVER admits and
NEVER places a property -- real discovery evidence shows both marketing phrases
attached to hotels in BOTH 30907 and 30909. A candidate with no verified postal
code is geography_state=PENDING_VERIFICATION, carried into the census un-corridored,
resolved by the very next phase (the static first-party lane's address extraction),
never guessed here from a URL slug.

A KNOWN FALSE-POSITIVE CLASS, FILTERED HERE
--------------------------------------------
The Hilton city-page walk returned 10 real hotels in Macon, Warner Robins, Perry,
Dublin, Forsyth, Cordele, Americus, Locust Grove and Madison, GA -- all inside
Georgia, all 100+ miles from Augusta, pulled in because a Hilton subpage view
(the amenity/attraction views) widens its radius well past a single city. State
agreement is not enough; a Hilton lead's OWN brand-card city must be an Augusta-
area municipality or an observed South Carolina town, or it is EXCLUDED as
OUT_OF_METRO_FALSE_POSITIVE and never enters the census at all -- not even as a hold.

VACATION RENTALS, MILITARY LODGING ARE NOT HOTELS
---------------------------------------------------
No row is admitted whose only typing evidence is a private-home/Airbnb/Vrbo name
pattern (NON_LODGING) or on-post/military-restricted lodging (MILITARY_RESTRICTED
-- none found in this discovery pass, the mechanism stays for the next one).

SHADOW UNTIL REGISTERED
------------------------
Written to identity_census_proposed/, never identity_census/.

Nothing here fetches a policy. Nothing here carries a pet policy.

Outputs:
  launch_packages/pettripfinder/identity_census_proposed/augusta-ga.json
  launch_packages/pettripfinder/markets/reports/augusta_ga_census_reconciliation_001.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.hotel_exclusions import address_key           # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder import augusta_ga_geography_001 as GEO         # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
SCHEMA = "ptf-market-identity-census/1.1"
REPORT_SCHEMA = "ptf-census-reconciliation/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS_OUT = os.path.join(PKG, "identity_census_proposed", "augusta-ga.json")
REPORT_OUT = os.path.join(REPORTS, "augusta_ga_census_reconciliation_001.json")

OSM_CANDIDATES = os.path.join(_DASH, "data", "discovery", "augusta_ga", "discovery_001",
                              "candidates", "augusta-ga_candidates.json")
BRAND = os.path.join(REPORTS, "augusta_ga_brand_inventory_001.json")

# --------------------------------------------------------------------------- #
# Classification vocabulary (the mission's, verbatim where it names one).
# --------------------------------------------------------------------------- #
TRUE_HOTEL_IDENTITY = "TRUE_HOTEL_IDENTITY"
DUPLICATE_LISTING = "DUPLICATE_LISTING"
SAME_CAMPUS_DISTINCT_ENTITY = "SAME_CAMPUS_DISTINCT_ENTITY"
NON_LODGING = "NON_LODGING"
OUTSIDE_MARKET = "OUTSIDE_MARKET"
OUT_OF_METRO_FALSE_POSITIVE = "OUT_OF_METRO_FALSE_POSITIVE"
IDENTITY_REVIEW_REQUIRED = "IDENTITY_REVIEW_REQUIRED"
ADDRESS_CONFLICT = "ADDRESS_CONFLICT"

#: Known Augusta-area municipalities (GA) plus the observed South Carolina towns.
#: A Hilton brand-card city outside this set, even inside Georgia, is a false
#: positive from the city-page walk's wider radius, not an Augusta-market lead.
KNOWN_MUNICIPALITIES = {
    "augusta", "martinez", "evans", "grovetown", "harlem", "hephzibah",
    "thomson", "wrens", "waynesboro", "lincolnton", "fort eisenhower", "fort gordon",
    "north augusta", "aiken", "edgefield", "graniteville", "clearwater",
}
SC_TOWNS = {"north augusta", "aiken", "edgefield", "graniteville", "clearwater"}

#: A map/name row typed as a private rental, not a hotel establishment.
_RENTAL_WORDS = re.compile(
    r"\b(airbnb|vrbo|apartment|apt\b|condo|cottage|bungalow|townhome|townhouse"
    r"|guest ?house|cabin|retreat|rental|bnb|bed and breakfast|vacation home)\b", re.I)
#: On-post / government / restricted lodging -- none found this pass; the
#: mechanism is checked so a later discovery is refused BY DECISION, not by accident.
_MILITARY_WORDS = re.compile(r"\b(barracks|billeting|unaccompanied housing|on-?post lodging)\b", re.I)

CAMPUS_RADIUS_METERS = 150.0
DUP_RADIUS_METERS = 45.0

LOCALITY_WORDS = {
    "augusta", "downtown", "airport", "medical", "district", "center", "centre",
    "north", "south", "east", "west", "georgia", "ga", "inn", "suites", "suite",
    "hotel", "hotels", "motel", "the", "and", "by", "at", "of", "place", "resort",
    "spa", "conference", "area", "near", "washington", "road", "rd", "gordon",
    "eisenhower", "fort", "wyndham", "hilton", "marriott", "highway", "riverwatch",
}


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def distinctive(name):
    return {t for t in norm(name).split() if t not in LOCALITY_WORDS}


def haversine_m(a, b):
    lat1, lng1 = a
    lat2, lng2 = b
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "unnamed"


# --------------------------------------------------------------------------- #
# rung 1 -- OSM candidates
# --------------------------------------------------------------------------- #
def load_osm():
    rows = json.load(open(OSM_CANDIDATES, encoding="utf-8"))
    out = []
    for r in rows:
        src = (r.get("source_records") or [{}])[0]
        prov = dict(src.get("provenance") or [])
        cell_id = prov.get("cell_id", "")
        out.append(OrderedDict([
            ("lane", "OSM_OVERPASS"), ("tier", 3),
            ("candidate_id", r.get("candidate_id")),
            ("name", (r.get("name") or "").strip()),
            ("address_line", (r.get("address_line") or "").strip()),
            ("city", (r.get("city") or "").strip()),
            ("postal_code", (r.get("postal_code") or "").strip()),
            ("latitude", r.get("latitude")), ("longitude", r.get("longitude")),
            ("cell_id", cell_id),
            ("category_candidates", r.get("category_candidates") or []),
            ("source_url", "https://www.openstreetmap.org/%s" %
             (src.get("provider_record_id") or "")),
            ("brand", ""), ("property_code", ""),
        ]))
    return out


# --------------------------------------------------------------------------- #
# rung 2 -- brand-inventory leads (already free/static; see brand_inventory_001)
# --------------------------------------------------------------------------- #
_WYNDHAM_LOCALE = re.compile(r"^https://www\.wyndhamhotels\.com/(?:en-ca/|en-uk/|es-xl/)?")


def load_brand():
    doc = json.load(open(BRAND, encoding="utf-8"))
    excluded_out_of_metro = []
    by_property = OrderedDict()
    for r in doc["leads"]:
        fam = r["family"]
        route = r["route"]
        if fam in ("WYNDHAM", "WOODSPRING"):
            base = _WYNDHAM_LOCALE.sub("https://www.wyndhamhotels.com/", route)
            base = base.rsplit("/overview")[0].rsplit("/rooms-rates")[0]
            if base.rstrip("/").endswith(("wyndhamhotels.com/hotels", "wyndhamhotels.com/university")):
                continue  # brand navigation pages, not a property route
            key = ("WYNDHAM_FAMILY", base)
            slug = base.rsplit("/", 1)[-1]
            title = slug.replace("-", " ").title()
            by_property.setdefault(key, OrderedDict([
                ("lane", "BRAND_SITEMAP"), ("tier", 2), ("name", title),
                ("brand", fam), ("property_code", ""), ("source_url", base),
                ("address_line", ""), ("city", ""), ("postal_code", ""),
                ("latitude", None), ("longitude", None),
                ("url_slug", slug),
            ]))
        elif fam == "MARRIOTT":
            title = r.get("brand_title") or r["route"].rsplit("/", 1)[-1]
            by_property[("MARRIOTT", r["property_code"])] = OrderedDict([
                ("lane", "BRAND_INVENTORY_OWNED"), ("tier", 2), ("name", title),
                ("brand", "MARRIOTT"), ("property_code", r["property_code"]),
                ("source_url", r["route"]),
                ("address_line", ""), ("city", ""), ("postal_code", ""),
                ("latitude", None), ("longitude", None),
                ("url_slug", _slugify(title)),
            ])
        elif fam == "HILTON":
            card = r.get("brand_card") or {}
            city = norm(card.get("city"))
            if not city or city not in KNOWN_MUNICIPALITIES:
                excluded_out_of_metro.append(OrderedDict([
                    ("name", card.get("name") or r["property_code"]),
                    ("property_code", r["property_code"]),
                    ("card_city", card.get("city")), ("card_state", card.get("state")),
                    ("card_postal", card.get("postal_code")),
                    ("why", "Hilton city-page walk false positive: brand card states city %r, "
                            "not an Augusta-area municipality or observed South Carolina town -- "
                            "excluded as %s, never entered the census" %
                            (card.get("city"), OUT_OF_METRO_FALSE_POSITIVE)),
                ]))
                continue
            by_property[("HILTON", r["property_code"])] = OrderedDict([
                ("lane", "BRAND_CITY_PAGE"), ("tier", 2), ("name", card.get("name") or ""),
                ("brand", "HILTON"), ("property_code", r["property_code"]),
                ("source_url", r["route"]),
                ("address_line", card.get("street") or ""), ("city", card.get("city") or ""),
                ("postal_code", card.get("postal_code") or ""),
                ("latitude", card.get("lat")), ("longitude", card.get("lng")),
                ("url_slug", _slugify(card.get("name"))),
            ])
    return list(by_property.values()), excluded_out_of_metro


def geography_of(rec):
    """(state, corridor_slug_or_None, basis, reason) for one merged record."""
    postal = rec.get("postal_code") or ""
    city = rec.get("city") or ""
    if postal:
        klass, slug, why = GEO.classify_postal(postal, city)
        if klass == "OUTSIDE":
            return "OUTSIDE", None, "postal_code", why
        return "RESOLVED", slug, "postal_code", why
    lat, lng = rec.get("latitude"), rec.get("longitude")
    if lat is not None and lng is not None:
        area = GEO.coverage_area(lat, lng)
        if area:
            return ("PENDING_VERIFICATION", None, "coverage_area_provisional",
                    "no postal code stated yet; coordinates fall inside the %r observation "
                    "area -- provisional only, resolved by the static first-party lane's "
                    "address extraction, never admitted to a corridor on this basis alone" % area)
    return ("PENDING_VERIFICATION", None, "none",
            "no postal code and no coordinates; identity carried into the census unresolved, "
            "resolved by the static first-party lane")


def build(as_of):
    osm = load_osm()
    brand, excluded_metro = load_brand()
    all_recs = osm + brand

    # -- typing filters (never silent) ---------------------------------------
    typed = []
    non_lodging = []
    for r in all_recs:
        name = r["name"] or ""
        cats = r.get("category_candidates") or []
        if _RENTAL_WORDS.search(name) or "apartments" in cats or "guest_house" in cats:
            non_lodging.append(OrderedDict([("name", name), ("lane", r["lane"]),
                                            ("why", "name/category matches the private-rental "
                                                     "pattern; not a single-establishment hotel")]))
            continue
        if _MILITARY_WORDS.search(name):
            non_lodging.append(OrderedDict([("name", name), ("lane", r["lane"]),
                                            ("why", "matches on-post/restricted lodging wording; "
                                                     "MILITARY_RESTRICTED, never a census candidate")]))
            continue
        typed.append(r)

    # -- geography -------------------------------------------------------------
    for r in typed:
        state, slug, basis, why = geography_of(r)
        r["geography_state"] = state
        r["corridor"] = slug
        r["assignment_basis"] = basis
        r["geography_why"] = why

    outside = [r for r in typed if r["geography_state"] == "OUTSIDE"]
    admissible = [r for r in typed if r["geography_state"] != "OUTSIDE"]

    # -- identity graph: group by proximity (when coordinates exist) ----------
    def informativeness(r):
        return (1 if r["postal_code"] else 0, 1 if r["address_line"] else 0,
                2 if r["lane"] == "OSM_OVERPASS" else 1, len(norm(r["name"])))

    with_coords = [r for r in admissible if r["latitude"] is not None and r["longitude"] is not None]
    without_coords = [r for r in admissible if r not in with_coords]
    ordered = sorted(with_coords, key=informativeness, reverse=True)
    groups, assigned = [], set()
    for i, a in enumerate(ordered):
        if id(a) in assigned:
            continue
        group = [a]
        assigned.add(id(a))
        for b in ordered[i + 1:]:
            if id(b) in assigned:
                continue
            d = haversine_m((float(a["latitude"]), float(a["longitude"])),
                            (float(b["latitude"]), float(b["longitude"])))
            if d > CAMPUS_RADIUS_METERS:
                continue
            group.append(b)
            b["_distance_to_anchor"] = round(d, 1)
            assigned.add(id(b))
        groups.append(group)
    for r in without_coords:
        groups.append([r])

    records = []
    for gi, group in enumerate(groups):
        anchor = group[0]
        anchor["classification"] = ""
        anchor["classification_why"] = ""
        anchor["evidence"] = [dict(anchor)]
        anchor["aliases"] = []
        for other in group[1:]:
            d = other.get("_distance_to_anchor", 0.0)
            same_addr = (anchor["address_line"] and other["address_line"]
                         and norm(anchor["address_line"]) == norm(other["address_line"]))
            a_dist, b_dist = distinctive(anchor["name"]), distinctive(other["name"])
            names_compatible = bool(a_dist & b_dist)
            zip_conflict = (anchor["postal_code"] and other["postal_code"]
                            and anchor["postal_code"][:5] != other["postal_code"][:5])
            addr_conflict = (anchor["address_line"] and other["address_line"]
                             and norm(anchor["address_line"]) != norm(other["address_line"]))
            anchor_located = bool(anchor["address_line"] or anchor["postal_code"])
            other_located = bool(other["address_line"] or other["postal_code"])
            if names_compatible and (zip_conflict or addr_conflict):
                other["classification"] = ADDRESS_CONFLICT
                other["classification_why"] = (
                    "%.0f m from %r sharing a distinctive name token, but the two rows state "
                    "different %s -- a name proposes an identity and never decides it; held"
                    % (d, anchor["name"], "postal codes" if zip_conflict else "street addresses"))
                other["evidence"] = [dict(other)]
                records.append(other)
                continue
            if names_compatible and (same_addr or (d <= DUP_RADIUS_METERS and not addr_conflict)):
                anchor["evidence"].append(dict(other))
                anchor["aliases"].append(other["name"])
                if not anchor["postal_code"] and other["postal_code"]:
                    anchor["postal_code"], anchor["city"] = other["postal_code"], other["city"] or anchor["city"]
                    state, slug, basis, why = geography_of(anchor)
                    anchor["geography_state"], anchor["corridor"] = state, slug
                    anchor["assignment_basis"], anchor["geography_why"] = basis, why
                continue
            if same_addr and not names_compatible:
                other["classification"] = SAME_CAMPUS_DISTINCT_ENTITY
                other["classification_why"] = (
                    "states the same street address as %r but shares no distinctive name "
                    "token -- two entities until an identity proof says otherwise" % anchor["name"])
                other["evidence"] = [dict(other)]
                records.append(other)
                continue
            if anchor_located and other_located:
                # Both rows state their OWN location (an address, a postal code, or -- for a
                # brand lead with neither yet -- at minimum this grouping never happened without
                # coordinates) and the names disagree: a neighbour in a hotel cluster, not an
                # alias and not an ambiguity. Gordon Highway and Washington Road each hold a
                # dozen-plus distinct brands within one campus radius of each other.
                other["classification"] = TRUE_HOTEL_IDENTITY
                other["classification_why"] = (
                    "%.0f m from %r but states its own distinct location and shares no "
                    "distinctive name token -- a neighbour in a hotel cluster, not an alias"
                    % (d, anchor["name"]))
                other["evidence"] = [dict(other)]
                records.append(other)
                continue
            other["classification"] = IDENTITY_REVIEW_REQUIRED
            other["classification_why"] = (
                "%.0f m from %r and at least one of the two rows states no address or postal "
                "code at all, so this is either a duplicate under a different name or a "
                "genuinely separate neighbour; held for review rather than guessed"
                % (d, anchor["name"]))
            other["evidence"] = [dict(other)]
            records.append(other)
        if not anchor["classification"]:
            anchor["classification"] = TRUE_HOTEL_IDENTITY
            anchor["classification_why"] = (
                "unique premises with %s and no competing row within %d m"
                % ("a stated postal code" if anchor["postal_code"] else "coordinates only",
                   CAMPUS_RADIUS_METERS))
        records.append(anchor)

    # -- a candidate with NO coordinates never entered the proximity grouping
    # above, so it stands as its own identity even when a fuller-named brand
    # lead is almost certainly the same premises (e.g. OSM's bare "Spark by
    # Hilton" vs. the brand card's "Spark by Hilton Augusta"). A NAME-TOKEN
    # merge was tried and reverted: Augusta carries multiple real, distinct
    # properties of the same brand (two separate Wingates, two separate
    # WoodSprings, five separate Days Inns), each reducing to the SAME single
    # brand token once locality words are stripped -- an exact-token-set merge
    # silently erased genuine hotels. A soft duplicate surviving as two rows
    # is a far safer failure than a merge that hides a real property; the
    # static first-party lane's verified address is what actually resolves
    # this, not a name guess. Flagged for that lane, not merged here.
    singleton_dupes = []
    seen_dtok = {}
    for r in records:
        if r["classification"] != TRUE_HOTEL_IDENTITY or r["latitude"] is not None:
            continue
        tok = frozenset(distinctive(r["name"]))
        if tok:
            seen_dtok.setdefault(tok, []).append(r["name"])
    for r in records:
        if r["classification"] != TRUE_HOTEL_IDENTITY:
            continue
        tok = frozenset(distinctive(r["name"]))
        matches = [n for n in seen_dtok.get(tok, []) if n != r["name"]]
        if matches and r["latitude"] is None:
            singleton_dupes.append({"name": r["name"], "possible_same_as": matches})

    for r in outside:
        r["classification"] = OUTSIDE_MARKET
        r["classification_why"] = r["geography_why"]
        r.setdefault("evidence", [dict(r)])
        r.setdefault("aliases", [])
        records.append(r)

    # -- build the census hotel rows for everything not OUTSIDE/NON_LODGING ---
    hotels = []
    seen_keys = set()
    for r in records:
        if r["classification"] == OUTSIDE_MARKET:
            continue
        name = r["name"] or (r["evidence"][0].get("name") if r.get("evidence") else "")
        try:
            ikey = ptf_identity_key(name)
        except Exception:
            r["classification"] = IDENTITY_REVIEW_REQUIRED
            r["classification_why"] = "name %r produces no usable identity key" % name
            continue
        dedup_key = ikey
        n = 2
        while dedup_key in seen_keys:
            dedup_key = "%s (%d)" % (ikey, n)
            n += 1
        seen_keys.add(dedup_key)
        akey = address_key(r["address_line"], r["postal_code"]) if r["address_line"] else ""
        hotels.append(OrderedDict([
            ("identity_key", dedup_key), ("slug", _slugify(name)),
            ("market_id", MARKET_ID),
            ("classification", r["classification"]), ("classification_reason", r["classification_why"]),
            ("canonical_name", name),
            ("street", r["address_line"]), ("city", r["city"]),
            ("state", "GA"),
            ("postal_code", r["postal_code"]), ("street_identity", akey),
            ("brand", r["brand"]), ("property_code", r["property_code"]),
            ("official_url", r["source_url"] if r["lane"] != "OSM_OVERPASS" else ""),
            ("latitude", r["latitude"]), ("longitude", r["longitude"]),
            ("corridor", r["corridor"]), ("geography_state", r["geography_state"]),
            ("assignment_basis", r["assignment_basis"]),
            ("lanes", sorted({e.get("lane") for e in r.get("evidence", [])})),
            ("aliases", r.get("aliases", [])),
            ("policy_state", "POLICY_NOT_VERIFIED"),
            ("policy_note", "Identity evidence never establishes a pet policy."),
            ("evidence", [OrderedDict([
                ("lane", e.get("lane")), ("tier", e.get("tier")),
                ("source_url", e.get("source_url")), ("name", e.get("name")),
                ("street", e.get("address_line")), ("city", e.get("city")),
                ("postal", e.get("postal_code")), ("lat", e.get("latitude")),
                ("lng", e.get("longitude")), ("cell_id", e.get("cell_id")),
            ]) for e in r.get("evidence", [])]),
        ]))

    non_admitted = []
    for r in records:
        if r["classification"] == OUTSIDE_MARKET:
            non_admitted.append(OrderedDict([("name", r["name"]), ("classification", r["classification"]),
                                             ("why", r["classification_why"]), ("lane", r["lane"])]))
    for r in non_lodging:
        non_admitted.append(OrderedDict([("name", r["name"]), ("classification", NON_LODGING),
                                         ("why", r["why"]), ("lane", r["lane"])]))
    for r in excluded_metro:
        non_admitted.append(OrderedDict([("name", r["name"]), ("classification", OUT_OF_METRO_FALSE_POSITIVE),
                                         ("why", r["why"]), ("lane", "BRAND_CITY_PAGE")]))

    class_counts = Counter(h["classification"] for h in hotels)
    geo_counts = Counter(h["geography_state"] for h in hotels)
    corridor_counts = Counter(h["corridor"] for h in hotels if h["corridor"])
    non_admitted_counts = Counter(r["classification"] for r in non_admitted)

    census = OrderedDict([
        ("schema", SCHEMA), ("market_id", MARKET_ID), ("status", "SHADOW_UNTIL_REGISTERED"),
        ("work_order", WORK_ORDER), ("captured_at", as_of),
        ("note", "Phase 8-10 census reconciliation: OSM discovery + brand-inventory leads merged "
                 "into one identity graph. Rows with geography_state=PENDING_VERIFICATION carry no "
                 "corridor yet and are resolved by the static first-party lane, never guessed here."),
        ("source_authorities", ["augusta_ga_geography_001", "augusta_ga_brand_inventory_001",
                                "data/discovery/augusta_ga/discovery_001"]),
        ("count", len(hotels)), ("total_candidates", len(all_recs)),
        ("classification_counts", OrderedDict(sorted(class_counts.items()))),
        ("corridor_counts", OrderedDict(sorted(corridor_counts.items()))),
        ("geography_state_counts", OrderedDict(sorted(geo_counts.items()))),
        ("hotels", hotels), ("non_admitted", non_admitted),
    ])
    report = OrderedDict([
        ("schema", REPORT_SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "8-10 -- census reconciliation into one identity graph"), ("as_of", as_of),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("inputs", OrderedDict([
            ("osm_candidates", os.path.relpath(OSM_CANDIDATES, _DASH).replace("\\", "/")),
            ("brand_inventory", os.path.relpath(BRAND, _DASH).replace("\\", "/")),
        ])),
        ("geography_method",
         "Postal-code partition (augusta_ga_geography_001.classify_postal). A candidate with no "
         "stated postal code is geography_state=PENDING_VERIFICATION, carried unresolved -- never "
         "assigned a corridor from a brand's marketing name or a URL slug."),
        ("known_false_positive_filter",
         "Hilton city-page leads whose own brand-card city is not an Augusta-area municipality or "
         "an observed South Carolina town are excluded before the identity graph runs, never "
         "entering the census: %d excluded (%s)."
         % (len(excluded_metro), ", ".join(sorted({e['card_city'] or '?' for e in excluded_metro})))),
        ("dedup_method",
         "Candidates within %d m are grouped; a row is merged into its group's anchor only when "
         "the two rows state the same street address, sit within %d m, or share a distinctive "
         "name token -- a postal or address disagreement blocks the merge and reports "
         "ADDRESS_CONFLICT instead." % (CAMPUS_RADIUS_METERS, DUP_RADIUS_METERS)),
        ("totals", OrderedDict([
            ("candidates_in", len(all_recs)),
            ("typed_as_lodging", len(typed)), ("non_lodging_excluded", len(non_lodging)),
            ("out_of_metro_excluded", len(excluded_metro)),
            ("outside_market", len(outside)),
            ("proposed_census", len(hotels)),
            ("classifications", OrderedDict(sorted(class_counts.items()))),
            ("geography_state", OrderedDict(sorted(geo_counts.items()))),
            ("corridor_assignment", OrderedDict(sorted(corridor_counts.items()))),
            ("non_admitted", OrderedDict(sorted(non_admitted_counts.items()))),
        ])),
        ("possible_duplicates_for_static_lane_review", singleton_dupes),
    ])

    os.makedirs(os.path.dirname(CENSUS_OUT), exist_ok=True)
    with open(CENSUS_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(census, fh, indent=1, ensure_ascii=False, default=str)
        fh.write("\n")
    with open(REPORT_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False, default=str)
        fh.write("\n")
    print(json.dumps(report["totals"], indent=1))
    print("wrote", CENSUS_OUT)
    print("wrote", REPORT_OUT)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=time.strftime("%Y-%m-%d", time.gmtime()))
    args = ap.parse_args()
    build(args.as_of)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

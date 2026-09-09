"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phase 5, census reconciliation.

Takes the 91 free-census candidates and resolves them into ONE identity graph
with exactly one classification per candidate, from the order's vocabulary.

Geography is decided by POINT-IN-POLYGON against the OSM county boundaries this
order extracted (`lexington_ky_county_boundaries_001.json`), never by the
discovery bounding box. The box is deliberately wider than the market so the
three fringe county seats get measured; using it to admit would sweep them in.
Lexington-Fayette is a merged city-county, so "inside Fayette County" and
"inside the city of Lexington" are the same test.

Deduplication never aliases on a bare chain name, on a locality word, or on a
directional. Two rows merge only when their own stated geography agrees:
either the same street address, or coordinates within a tight radius AND
compatible names. Anything that disagrees is held, not merged -- an address or
postal conflict BLOCKS an automatic alias by contract.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
CANDIDATES = os.path.join(_DASH, "data", "discovery", "lexington_ky_free_census_001",
                          "free_census_candidates.json")
BOUNDARIES = os.path.join(REPORTS, "lexington_ky_county_boundaries_001.json")

# ---- classification vocabulary (the order's, exactly) -----------------------
EXACT_UNIQUE_IDENTITY = "EXACT_UNIQUE_IDENTITY"
ALIAS_OF_EXISTING = "ALIAS_OF_EXISTING"
SAME_IDENTITY_REBRAND_SUCCESSOR = "SAME_IDENTITY_REBRAND_SUCCESSOR"
SAME_CAMPUS_DISTINCT_ENTITY = "SAME_CAMPUS_DISTINCT_ENTITY"
DUPLICATE_LISTING = "DUPLICATE_LISTING"
CLOSED_OR_CONVERTED = "CLOSED_OR_CONVERTED"
NON_LODGING = "NON_LODGING"
OUTSIDE_MARKET = "OUTSIDE_MARKET"
NAME_ONLY_UNRESOLVED = "NAME_ONLY_UNRESOLVED"
ADDRESS_CONFLICT = "ADDRESS_CONFLICT"
IDENTITY_REVIEW_REQUIRED = "IDENTITY_REVIEW_REQUIRED"

# Postal codes are corroboration, never the primary test: the polygon is.
FAYETTE_ZIPS = {str(z) for z in range(40502, 40518)} | {
    "40522", "40523", "40524", "40526", "40533", "40536", "40544", "40546",
    "40550", "40555", "40574", "40575", "40576", "40577", "40578", "40579",
    "40580", "40581", "40582", "40583", "40588", "40591", "40592", "40593",
    "40594", "40595", "40596", "40598",
}
FRINGE_ZIPS = {"40324": "Scott County", "40356": "Jessamine County",
               "40340": "Jessamine County", "40383": "Woodford County",
               "40390": "Jessamine County", "40347": "Woodford County"}

# A bare chain word never identifies a hotel. Held here so the dedup step can
# refuse to alias on one.
BARE_CHAIN_NAMES = {
    "best western", "comfort inn", "comfort suites", "hampton inn", "courtyard",
    "residence inn", "fairfield inn", "fairfield inn suites", "holiday inn express",
    "hilton garden inn", "home2 suites", "home 2 suites", "homewood suites",
    "towneplace suites", "springhill suites", "country inn suites", "days inn",
    "super 8", "quality inn", "sleep inn", "econo lodge", "motel 6", "red roof inn",
    "extended stay america", "woodspring suites", "la quinta inn", "tru",
    "embassy suites", "hyatt place", "staybridge suites", "candlewood suites",
    "double tree hilton", "doubletree", "baymont", "microtel inn suites",
    "four points by sheraton", "clarion hotel", "ramada conference center",
    "guesthouse inn suites", "surestay plus hotel by best western",
}
LOCALITY_WORDS = {
    "lexington", "downtown", "airport", "university", "medical", "center", "north",
    "south", "east", "west", "northeast", "northwest", "southeast", "southwest",
    "keeneland", "hamburg", "fayette", "kentucky", "ky", "inn", "suites", "hotel",
    "the", "and", "by", "at", "of", "place", "resort", "spa", "conference",
}

DUP_RADIUS_METERS = 45.0
CAMPUS_RADIUS_METERS = 150.0


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def distinctive(name):
    """The tokens that could actually identify a property, chain words removed."""
    return {t for t in norm(name).split() if t not in LOCALITY_WORDS} - set()


def point_in_ring(lat, lng, ring):
    """Ray casting. `ring` is [[lng, lat], ...]."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def haversine_m(a, b):
    lat1, lng1 = a
    lat2, lng2 = b
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def load_counties():
    d = json.load(open(BOUNDARIES, encoding="utf-8"))
    return d["counties"]


def county_of(lat, lng, counties):
    if lat is None or lng is None:
        return ""
    for name, c in counties.items():
        for ring in c["rings"]:
            if point_in_ring(float(lat), float(lng), ring):
                return name
    return ""


def cell_of(rec):
    m = re.search(r"\('cell_id', '([^']+)'\)", str(rec.get("source_records")))
    return m.group(1) if m else ""


def osm_ref(rec):
    m = re.search(r"provider_record_id='([^']+)'", str(rec.get("source_records")))
    return m.group(1) if m else ""


def brand_url(rec):
    u = rec.get("website_url") or ""
    if u:
        return u
    m = re.search(r"website_url='([^']*)'", str(rec.get("source_records")))
    return m.group(1) if m else ""


def build(args):
    rows = json.load(open(CANDIDATES, encoding="utf-8"))
    counties = load_counties()

    recs = []
    for r in rows:
        lat = r.get("latitude")
        lng = r.get("longitude")
        rec = OrderedDict([
            ("candidate_id", r.get("candidate_id")),
            ("name", (r.get("name") or "").strip()),
            ("normalized_name", norm(r.get("name"))),
            ("address_line", (r.get("address_line") or "").strip()),
            ("city", (r.get("city") or "").strip()),
            ("state", (r.get("state") or "").strip()),
            ("postal_code", (r.get("postal_code") or "").strip()),
            ("latitude", lat), ("longitude", lng),
            ("cell_id", cell_of(r)),
            ("osm_element", osm_ref(r)),
            ("website_url", brand_url(r)),
            ("review_state", r.get("review_state")),
        ])
        rec["county"] = county_of(lat, lng, counties)
        recs.append(rec)

    # ---- geography ---------------------------------------------------------
    for rec in recs:
        zip5 = rec["postal_code"][:5]
        county = rec["county"]
        city = norm(rec["city"])
        signals = []
        if county:
            signals.append("polygon:%s" % county)
        if zip5:
            signals.append("postal:%s" % zip5)
        if city:
            signals.append("city:%s" % rec["city"])
        rec["geography_signals"] = signals

        if county == "Fayette County":
            if zip5 and zip5 not in FAYETTE_ZIPS:
                rec["geography"] = "IN_MARKET_POSTAL_CONFLICT"
                rec["geography_why"] = (
                    "coordinates are inside the Fayette County polygon but the stated postal "
                    "code %s is not a Fayette code; the conflict is held, not resolved" % zip5)
            elif city and city != "lexington":
                rec["geography"] = "IN_MARKET_CITY_CONFLICT"
                rec["geography_why"] = (
                    "coordinates are inside the Fayette County polygon but the candidate states "
                    "city %r; Lexington-Fayette is a merged city-county, so a different stated "
                    "city on Fayette ground is a real conflict and is held" % rec["city"])
            else:
                rec["geography"] = "IN_MARKET"
                rec["geography_why"] = (
                    "inside the OSM Fayette County boundary (admin_level=6); Lexington-Fayette "
                    "is a merged city-county")
        elif county:
            rec["geography"] = "OUT_OF_MARKET"
            rec["geography_why"] = "inside the OSM %s boundary, not Fayette" % county
        elif zip5 in FRINGE_ZIPS:
            rec["geography"] = "OUT_OF_MARKET"
            rec["geography_why"] = "postal %s is a %s code; no polygon hit" % (zip5, FRINGE_ZIPS[zip5])
        elif zip5 in FAYETTE_ZIPS:
            rec["geography"] = "IN_MARKET"
            rec["geography_why"] = "Fayette postal %s; coordinates hit no county polygon" % zip5
        else:
            rec["geography"] = "UNRESOLVED"
            rec["geography_why"] = "no county polygon hit and no postal code that names a county"

    # ---- identity graph ----------------------------------------------------
    for rec in recs:
        rec["classification"] = ""
        rec["classification_why"] = ""
        rec["identity_group"] = ""
        rec["aliases"] = []

    named = [r for r in recs if r["normalized_name"]]
    unnamed = [r for r in recs if not r["normalized_name"]]

    for r in unnamed:
        r["classification"] = NAME_ONLY_UNRESOLVED
        r["classification_why"] = (
            "the OSM element states no name at all, so nothing here proposes an identity; "
            "a coordinate is not an identity")

    # Pair up candidates that are close enough to be the same premises. The
    # ANCHOR of a group is its most-informative row -- one that states a street
    # address outranks one that does not, and a longer name outranks a bare
    # chain word. Anchoring on whichever row happened to sort first is how the
    # row carrying the evidence gets demoted to a duplicate of the row that
    # carries none.
    def informativeness(r):
        return (1 if r["address_line"] else 0,
                1 if r["postal_code"] else 0,
                0 if norm(r["name"]) in BARE_CHAIN_NAMES else 1,
                len(r["normalized_name"]))

    ordered = sorted(named, key=informativeness, reverse=True)
    groups = []
    assigned = set()
    for a in ordered:
        if a["candidate_id"] in assigned:
            continue
        group = [a]
        assigned.add(a["candidate_id"])
        for b in ordered:
            if b["candidate_id"] in assigned:
                continue
            if a["latitude"] is None or b["latitude"] is None:
                continue
            d = haversine_m((float(a["latitude"]), float(a["longitude"])),
                            (float(b["latitude"]), float(b["longitude"])))
            if d > CAMPUS_RADIUS_METERS:
                continue
            group.append(b)
            b["_distance_to_anchor"] = round(d, 1)
            assigned.add(b["candidate_id"])
        groups.append(group)

    for gi, group in enumerate(groups):
        gid = "lexgrp_%03d" % gi
        anchor = group[0]
        for r in group:
            r["identity_group"] = gid
        if len(group) == 1:
            continue
        for other in group[1:]:
            d = other.get("_distance_to_anchor", 0.0)
            same_addr = (anchor["address_line"] and other["address_line"]
                         and norm(anchor["address_line"]) == norm(other["address_line"]))
            a_dist = distinctive(anchor["name"])
            b_dist = distinctive(other["name"])
            a_bare = norm(anchor["name"]) in BARE_CHAIN_NAMES
            b_bare = norm(other["name"]) in BARE_CHAIN_NAMES
            names_compatible = bool(a_dist & b_dist) or (a_bare and b_bare and
                                                         norm(anchor["name"]) == norm(other["name"]))
            zip_conflict = (anchor["postal_code"][:5] and other["postal_code"][:5]
                            and anchor["postal_code"][:5] != other["postal_code"][:5])
            addr_conflict = (anchor["address_line"] and other["address_line"]
                             and norm(anchor["address_line"]) != norm(other["address_line"]))

            # Order matters. Proximity alone means nothing here: Lexington's
            # interstate and airport clusters put five separately-owned hotels
            # inside one 150 m circle, each with its own street address. Two
            # rows that state DIFFERENT addresses and share no distinctive name
            # token are simply two different hotels, and calling that an
            # "address conflict" would hold most of the market for review.
            # A conflict is when the NAMES say one identity and the GEOGRAPHY
            # disagrees.
            if names_compatible and (zip_conflict or addr_conflict):
                other["classification"] = ADDRESS_CONFLICT
                other["classification_why"] = (
                    "%.0f m from %r and the names share a distinctive token, so these rows "
                    "propose ONE identity -- but they state different %s. A name proposes an "
                    "identity and never decides it: the disagreement blocks the alias and the "
                    "row is held."
                    % (d, anchor["name"], "postal codes" if zip_conflict else "street addresses"))
                continue
            if names_compatible and (same_addr or d <= DUP_RADIUS_METERS):
                other["classification"] = DUPLICATE_LISTING
                other["classification_why"] = (
                    "%s as %r and a shared distinctive name token; one premises listed twice"
                    % ("same stated street address" if same_addr
                       else "%.0f m" % d, anchor["name"]))
                anchor["aliases"].append(other["name"])
                continue
            if same_addr and not names_compatible:
                other["classification"] = SAME_CAMPUS_DISTINCT_ENTITY
                other["classification_why"] = (
                    "states the SAME street address as %r but shares no distinctive name "
                    "token -- a dual-brand or shared-parcel property; two entities until an "
                    "identity proof says otherwise" % anchor["name"])
                continue
            if (a_bare or b_bare) and not (other["address_line"] and anchor["address_line"]):
                other["classification"] = IDENTITY_REVIEW_REQUIRED
                other["classification_why"] = (
                    "%.0f m from %r, and the row with the weaker name states no street "
                    "address, so this is either a duplicate of it, a predecessor brand at the "
                    "same premises, or a genuinely separate neighbour. A bare chain name never "
                    "identifies one hotel; held for review rather than merged or split"
                    % (d, anchor["name"]))
                continue
            # Different addresses, different names, both stated: two hotels.
            other["classification"] = EXACT_UNIQUE_IDENTITY
            other["classification_why"] = (
                "%.0f m from %r but states its own distinct street address and shares no "
                "distinctive name token -- a neighbour in a hotel cluster, not an alias"
                % (d, anchor["name"]))

    # ---- final classification for everything still unclassified ------------
    for r in recs:
        if r["classification"]:
            continue
        if r["geography"] == "OUT_OF_MARKET":
            r["classification"] = OUTSIDE_MARKET
            r["classification_why"] = r["geography_why"]
        elif r["geography"] in ("IN_MARKET_POSTAL_CONFLICT", "IN_MARKET_CITY_CONFLICT"):
            r["classification"] = ADDRESS_CONFLICT
            r["classification_why"] = r["geography_why"]
        elif r["geography"] == "UNRESOLVED":
            r["classification"] = IDENTITY_REVIEW_REQUIRED
            r["classification_why"] = r["geography_why"]
        elif norm(r["name"]) in BARE_CHAIN_NAMES and not r["address_line"]:
            r["classification"] = IDENTITY_REVIEW_REQUIRED
            r["classification_why"] = (
                "a bare chain name (%r) with no stated street address proposes a brand, not a "
                "property; verification on address, phone or property code is required before "
                "this becomes an identity" % r["name"])
        else:
            r["classification"] = EXACT_UNIQUE_IDENTITY
            r["classification_why"] = (
                "unique premises inside the Fayette County polygon with its own stated "
                "geography and no competing row within %d m" % CAMPUS_RADIUS_METERS)

    # Anything outside the market that also got a dedup class keeps OUTSIDE_MARKET:
    # geography is the stronger statement and the census must not carry it.
    for r in recs:
        if r["geography"] == "OUT_OF_MARKET" and r["classification"] != OUTSIDE_MARKET:
            r["prior_classification"] = r["classification"]
            r["classification"] = OUTSIDE_MARKET
            r["classification_why"] = (
                "%s (superseded %s: geography is decided before identity)"
                % (r["geography_why"], r["prior_classification"]))

    counts = Counter(r["classification"] for r in recs)
    geo_counts = Counter(r["geography"] for r in recs)
    county_counts = Counter(r["county"] or "(no polygon)" for r in recs)
    corridor_counts = Counter(r["cell_id"] for r in recs
                              if r["classification"] == EXACT_UNIQUE_IDENTITY)

    report = OrderedDict([
        ("schema", "ptf-census-reconciliation/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "5 -- census reconciliation into one identity graph"),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("inputs", OrderedDict([
            ("free_census_candidates", os.path.relpath(CANDIDATES, _DASH).replace("\\", "/")),
            ("county_boundaries", os.path.relpath(BOUNDARIES, _DASH).replace("\\", "/")),
        ])),
        ("geography_method",
         "Point-in-polygon against the OSM admin_level=6 county boundaries extracted from the "
         "same Geofabrik Kentucky file the census came from. The discovery bounding box is NOT "
         "used to admit: it is deliberately wider than the market so the fringe county seats "
         "get measured. Postal codes corroborate; they never overrule the polygon, and a "
         "postal or city that disagrees with the polygon is HELD as a conflict, not resolved."),
        ("dedup_method",
         "Candidates within %d m are grouped. Inside a group a row is aliased only when the "
         "two rows state the same street address, or sit within %d m AND share a distinctive "
         "name token that is not a chain word, a locality word or a directional. A postal or "
         "address disagreement BLOCKS the alias and reports ADDRESS_CONFLICT. Two rows whose "
         "only commonality is a bare chain name are held for review, never merged."
         % (CAMPUS_RADIUS_METERS, DUP_RADIUS_METERS)),
        ("totals", OrderedDict([
            ("candidates_in", len(rows)),
            ("classifications", OrderedDict(sorted(counts.items()))),
            ("geography", OrderedDict(sorted(geo_counts.items()))),
            ("county_polygon_hits", OrderedDict(sorted(county_counts.items()))),
            ("corridor_assignment_of_unique_identities",
             OrderedDict(sorted(corridor_counts.items()))),
        ])),
        ("records", recs),
    ])

    os.makedirs(REPORTS, exist_ok=True)
    out = args.out or os.path.join(REPORTS, "lexington_ky_census_reconciliation_001.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, default=str)
        fh.write("\n")
    print(json.dumps(report["totals"], indent=1))
    print("wrote", out)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--out", default=None)
    build(ap.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

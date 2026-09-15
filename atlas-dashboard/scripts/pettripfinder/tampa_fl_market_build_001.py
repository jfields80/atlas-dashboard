"""PTF-TAMPA-FL-PARALLEL-SOURCE-READY-001 -- Tampa, FL shadow source-ready market build.

Deterministic: reads only committed, market-owned raw captures and rulings under
``launch_packages/pettripfinder/markets/staging/tampa-fl/`` and writes only
Tampa-owned outputs (staging launch package + report). No shared registry,
participation, release contract, global authority or live state is touched.

Modeled on orlando_fl_market_build_001.py (worker/ptf-orlando-fl-market-001,
built on this same base commit) -- same pipeline shape, Tampa Bay-specific
leads/geography/brand filters.

Pipeline
  1. leads      DBPR licences, Hilton inventory, owned Marriott codes, two CVBs, OSM
  2. identity   premises identities (licence group or brand property code anchors)
  3. rulings    identity_rulings_001.json (cited bindings / classifications / holds)
  4. classify   lodging category (hotel, mixed resort, timeshare, vacation rental, ...)
  5. geography  CORE / CORRIDOR / FRINGE / OUTSIDE + corridor assignment
  6. evidence   tampa_fl_policy_evidence_001 (durable pages + shared readers)
  7. outputs    census, partition, market config, authority shards, evidence ledger, accounting

Run:
    python -m scripts.pettripfinder.tampa_fl_market_build_001 [--out-root DIR]
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.census_partition_builder import (  # noqa: E402
    census_document, census_row, partition_document, partition_item, slugify,
)
from scripts.pettripfinder.contracts import enums  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder import tampa_fl_identity_rules_001 as R  # noqa: E402
from scripts.pettripfinder import tampa_fl_policy_evidence_001 as EV  # noqa: E402

WORK_ORDER = "PTF-TAMPA-FL-PARALLEL-SOURCE-READY-001"
MARKET_ID = "tampa-fl"
AS_OF = "2026-09-15"
STAGING_REL = Path("launch_packages") / "pettripfinder" / "markets" / "staging" / MARKET_ID
REPORTS_REL = Path("launch_packages") / "pettripfinder" / "markets" / "reports"
STAGING = _REPO_ROOT / STAGING_REL
RAW = STAGING / "raw_captures"

REFUSING_BRAND_DOMAINS = ("marriott.com", "ihg.com", "hyatt.com", "choicehotels.com", "bestwestern.com", "wyndhamhotels.com",
                          "redroof.com", "motel6.com", "omnihotels.com", "radissonhotels.com", "druryhotels.com", "hilton.com")
CLIENT_RENDERED_DOMAINS = ()


def _load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def _load_optional(name):
    p = RAW / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. leads
# ---------------------------------------------------------------------------

def build_leads():
    leads = []
    for r in _load("dbpr_lodging_inscope_001.json")["licences"]:
        g = r.get("geocode") or {}
        leads.append(dict(src="DBPR", sid=r["license_number"], name=r["business_name"], street=r["street"], city=r["city"].title(), zip=r["postal"],
                          lat=g.get("lat"), lng=g.get("lng"), url="", phone=r["phone"],
                          extra={"rank": r["rank_code"], "units": r["units"], "county": r["county"], "licensee": r["licensee_name"],
                                 "geocode": g.get("match_type"), "source_row": r["source"]["row"], "source_file": r["source"]["file"]}))
    hilton_doc = _load_optional("hilton_inventory_001.json")
    if hilton_doc:
        for r in hilton_doc["hotels"]:
            leads.append(dict(src="HILTON", sid=r["property_code"], name=r["name"], street=r.get("street") or "", city=r.get("city") or "", zip=(r.get("postal") or "")[:5],
                              lat=r.get("lat"), lng=r.get("lng"), url=r.get("url") or "", phone=r.get("phone") or "", extra={"brand_code": r.get("brand_code"), "open": r.get("open")}))
    for fname, tag in (("visittampabay_hotels_001.json", "VISITTAMPABAY"), ("visitstpeteclearwater_hotels_001.json", "VISITSTPETECLEARWATER")):
        doc = _load_optional(fname)
        if not doc:
            continue
        for r in doc["docs"]:
            leads.append(dict(src=tag, sid=str(r.get("recid")), name=r.get("title") or "", street=r.get("address1") or "", city=r.get("city") or "",
                              zip=(r.get("zip") or "")[:5], lat=r.get("latitude"), lng=r.get("longitude"), url=r.get("weburl") or "", phone=r.get("phone") or "",
                              extra={"listing": r.get("absolute_url")}))
    osm_doc = _load_optional("osm_overpass_lodging_001.json")
    if osm_doc:
        for e in osm_doc["elements"]:
            t = e["tags"]
            if not t.get("name"):
                continue
            lat = e.get("lat") or (e.get("center") or {}).get("lat")
            lng = e.get("lon") or (e.get("center") or {}).get("lon")
            street = ((t.get("addr:housenumber") or "") + " " + (t.get("addr:street") or "")).strip()
            leads.append(dict(src="OSM", sid="%s/%s" % (e["type"], e["id"]), name=t["name"], street=street, city=t.get("addr:city") or "", zip=(t.get("addr:postcode") or "")[:5],
                              lat=lat, lng=lng, url=t.get("website") or t.get("contact:website") or "", phone=t.get("phone") or "",
                              extra={"tourism": t.get("tourism"), "building": t.get("building"), "brand": t.get("brand")}))
    marriott_doc = _load_optional("marriott_owned_harvest_codes_001.json")
    if marriott_doc:
        for code, slug in marriott_doc["codes"].items():
            leads.append(dict(src="MARRIOTT_HARVEST", sid=code, name=slug.replace("-", " "), street="", city="", zip="", lat=None, lng=None,
                              url="https://www.marriott.com/en-us/hotels/%s-%s/overview/" % (code, slug), phone="", extra={}))
    for l in leads:
        l["key"] = l["src"] + ":" + l["sid"]
    return leads


# ---------------------------------------------------------------------------
# 2. identity resolution (anchor = DBPR licence group or brand property code)
# ---------------------------------------------------------------------------

def _subs(n):
    return {b[1] for b in R.brands_in(n)}


def _bldg_norm(n):
    n = re.sub(r"\b(BUILDING|BLDG)\s*\d+\b", "", n.upper())
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", n).split())


def resolve(all_leads):
    in_box = [l for l in all_leads if l["lat"] is None or (27.55 < l["lat"] < 28.35 and -82.85 < l["lng"] < -82.15)]
    DB = [l for l in in_box if l["src"] == "DBPR"]
    HI = [l for l in in_box if l["src"] == "HILTON"]
    MA = [l for l in in_box if l["src"] == "MARRIOTT_HARVEST"]
    OT = [l for l in in_box if l["src"] in ("VISITTAMPABAY", "VISITSTPETECLEARWATER", "OSM") and (l["src"] != "OSM" or l["extra"].get("tourism"))]
    decisions, identities = [], []

    groups = []
    for d in DB:
        for g in groups:
            g0 = g["licenses"][0]
            if _bldg_norm(d["name"]) == _bldg_norm(g0["name"]) and re.search(r"BUILDING|BLDG", d["name"] + g0["name"]):
                g["licenses"].append(d)
                decisions.append(["DBPR_MULTI_BUILDING_MERGE", g0["key"], d["key"]])
                break
        else:
            groups.append({"licenses": [d]})
    flags = collections.defaultdict(list)
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            la, lb = a["licenses"][0], b["licenses"][0]
            if _bldg_norm(la["name"]) == _bldg_norm(lb["name"]) and la["lat"] and lb["lat"] and R.haversine_m(la["lat"], la["lng"], lb["lat"], lb["lng"]) < 400:
                flags[la["key"]].append(["SAME_NAME_ADJACENT_LICENSE", lb["key"]])
                flags[lb["key"]].append(["SAME_NAME_ADJACENT_LICENSE", la["key"]])

    def new_identity(kind, anchor, name):
        ident = {"kind": kind, "anchor": anchor, "name": name, "licenses": [], "brand_codes": [], "leads": [], "flags": [], "binds": []}
        identities.append(ident)
        return ident

    lic_group = {d["key"]: g for g in groups for d in g["licenses"]}
    group_idents = collections.defaultdict(list)

    for h in HI:
        ident = new_identity("BRAND_CODE", h["key"], h["name"])
        ident["brand_codes"].append("HILTON:" + h["sid"])
        ident["leads"].append(h)
        cands = [g for g in groups if any(R.same_address(h["street"], d["street"]) for d in g["licenses"])]
        cands = [g for g in cands if not any(R.brand_conflict(h["name"], d["name"]) for d in g["licenses"])]
        if not cands and h["lat"]:
            hs = _subs(h["name"])
            for g in groups:
                for d in g["licenses"]:
                    nh, nd = R.split_number(h["street"])[0], R.split_number(d["street"])[0]
                    if d["zip"] == (h["zip"] or "")[:5] and nh and nh == nd and (_subs(d["name"]) & hs):
                        cands.append(g)
                        decisions.append(["HILTON_ADDRESS_ALIAS_SAME_NUMBER_ZIP_BRAND", h["key"], d["key"]])
        if len(cands) > 1:
            cands.sort(key=lambda g: -max(R.name_sim(h["name"], d["name"]) for d in g["licenses"]))
            decisions.append(["HILTON_MULTI_LICENCE_AT_ADDRESS_BEST_NAME", h["key"], [g["licenses"][0]["key"] for g in cands]])
            cands = cands[:1]
        if cands:
            group_idents[id(cands[0])].append(ident)
            ident["licenses"] = [d["key"] for d in cands[0]["licenses"]]
            ident["binds"].append(["LICENCE_BY_ADDRESS", cands[0]["licenses"][0]["key"]])

    pool = [(g, d) for g in groups for d in g["licenses"]] + [(None, l) for l in OT]
    url_code_idx = collections.defaultdict(list)
    for l in OT:
        m = re.search(r"marriott\.com/(?:[a-z-]+/)?hotels/(?:travel/)?([a-z]{5})\b|marriott\.com/([a-z]{5})/?$", (l["url"] or "").lower())
        if m:
            url_code_idx[m.group(1) or m.group(2)].append(l)
    city_tokens = ("clearwater", "st petersburg", "st pete", "brandon", "oldsmar", "wesley chapel", "largo", "tarpon springs")
    for mh in MA:
        ident = new_identity("BRAND_CODE", mh["key"], mh["name"])
        ident["brand_codes"].append("MARRIOTT:" + mh["sid"])
        ident["leads"].append(mh)
        slug, sb = mh["name"], _subs(mh["name"])
        toks = [c for c in city_tokens if c in slug]
        scored = []
        for g, x in pool:
            if sb and not (_subs(x["name"]) & sb):
                continue
            if toks and not any(c in (x["name"] + " " + x["city"]).lower() for c in toks):
                continue
            s = R.name_sim(slug, x["name"])
            if s >= 0.5:
                scored.append((s, g, x))
        scored.sort(key=lambda t: (-t[0], t[2]["key"]))
        chosen = None
        if url_code_idx.get(mh["sid"]):
            chosen = ("URL_CODE", sorted(url_code_idx[mh["sid"]], key=lambda l: l["key"])[0])
        elif scored:
            best = scored[0]
            rivals = [t for t in scored[1:] if t[0] > best[0] - 0.12 and not (t[1] is not None and t[1] is best[1])
                      and t[2]["street"] and best[2]["street"] and not R.same_address(t[2]["street"], best[2]["street"])]
            if rivals:
                decisions.append(["MARRIOTT_SLUG_AMBIGUOUS", mh["key"], [[round(t[0], 2), t[2]["key"]] for t in [best] + rivals[:3]]])
            else:
                chosen = ("SLUG_NAME_%.2f" % best[0], best[2])
        if not chosen:
            continue
        x = chosen[1]
        ident["binds"].append([chosen[0], x["key"]])
        g = lic_group.get(x["key"])
        if g is None and x["street"]:
            for g2 in groups:
                for d in g2["licenses"]:
                    nx, nd = R.split_number(x["street"])[0], R.split_number(d["street"])[0]
                    if nx and nx == nd and d["zip"] == (x["zip"] or "")[:5] and (_subs(d["name"]) & sb):
                        g = g2
        if g is None and x["lat"]:
            near = sorted([(R.haversine_m(x["lat"], x["lng"], d["lat"], d["lng"]), d["key"], g2) for g2 in groups for d in g2["licenses"]
                           if d["lat"] and (_subs(d["name"]) & sb)], key=lambda t: (t[0], t[1]))
            near = [t for t in near if t[0] < 200]
            if near:
                g = near[0][2]
                decisions.append(["MARRIOTT_PROXIMITY_BRAND_%dm" % near[0][0], mh["key"], near[0][1]])
        if g is None and x["street"]:
            gs = [g2 for g2 in groups if any(R.same_address(x["street"], d["street"]) for d in g2["licenses"])
                  and not any(R.brand_conflict(slug, d["name"]) for d in g2["licenses"])]
            gs.sort(key=lambda g2: -max(R.name_sim(slug, d["name"]) for d in g2["licenses"]))
            g = gs[0] if gs else None
        if x["src"] != "DBPR":
            ident["leads"].append(x)
            x["_attached"] = True
        if g is not None:
            group_idents[id(g)].append(ident)
            ident["licenses"] = [d["key"] for d in g["licenses"]]

    for g in groups:
        d0 = g["licenses"][0]
        attached = group_idents.get(id(g), [])
        if attached:
            for ident in attached:
                ident["dbpr_names"] = [d["name"] for d in g["licenses"]]
            continue
        nb = R.brands_in(d0["name"])
        if len(nb) == 2 and frozenset(b[1] for b in nb) in R.DUAL_BRAND_PAIRS:
            for b in nb:
                ident = new_identity("DBPR_DUAL_BRAND_SPLIT", d0["key"] + "#" + b[1], "%s [%s]" % (d0["name"], b[1]))
                ident["licenses"] = [d["key"] for d in g["licenses"]]
                ident["split_brand"] = b[1]
                ident["dbpr_names"] = [d["name"] for d in g["licenses"]]
            decisions.append(["DBPR_DUAL_BRAND_SPLIT", d0["key"], [b[1] for b in nb]])
            continue
        ident = new_identity("DBPR_LICENSE", d0["key"], d0["name"])
        if len(nb) >= 2:
            ident["flags"].append(["MULTI_BRAND_LICENCE_NAME", [b[1] for b in nb]])
        ident["licenses"] = [d["key"] for d in g["licenses"]]
        ident["dbpr_names"] = [d["name"] for d in g["licenses"]]
        for d in g["licenses"]:
            ident["flags"] += flags.get(d["key"], [])

    lead_by_key = {l["key"]: l for l in in_box}

    def points(ident):
        return [lead_by_key[k] for k in ident["licenses"]] + [l for l in ident["leads"] if l["src"] != "MARRIOTT_HARVEST"]

    def isubs(ident):
        if ident.get("split_brand"):
            return {ident["split_brand"]}
        if ident["kind"] == "BRAND_CODE":
            return _subs(ident["leads"][0]["name"]) or _subs(ident["name"])
        s = set()
        for p in [ident] + points(ident):
            s |= _subs(p["name"])
        return s

    def is_ts(names):
        return any(R.TIMESHARE_RX.search(n) for n in names)

    unattached, ambiguous = [], []
    for l in OT:
        if l.get("_attached"):
            continue
        lsub, l_ts = _subs(l["name"]), bool(R.TIMESHARE_RX.search(l["name"]))
        best = []
        for ident in identities:
            isub = isubs(ident)
            if lsub and isub and not (lsub & isub):
                continue
            if ident["kind"] != "DISCOVERY" and l_ts != is_ts([ident["name"]] + ident.get("dbpr_names", [])):
                continue
            score, why = 0, None
            for p in points(ident):
                if l["street"] and p["street"] and R.same_address(l["street"], p["street"]):
                    if l["zip"] and p["zip"] and l["zip"] != p["zip"] and l["lat"] and p["lat"] and R.haversine_m(l["lat"], l["lng"], p["lat"], p["lng"]) > 3000:
                        continue
                    score, why = max((score, why or ""), (3 if (lsub & isub) else 2, "ADDRESS"))
                elif l["street"] and p["street"] and R.split_number(l["street"])[0] and R.split_number(l["street"])[0] == R.split_number(p["street"])[0] and l["zip"] == p["zip"] and (lsub & isub):
                    score, why = max((score, why or ""), (2, "ADDRESS_ALIAS_NUMBER_ZIP_BRAND"))
                elif l["lat"] and p["lat"]:
                    dist = R.haversine_m(l["lat"], l["lng"], p["lat"], p["lng"])
                    if dist < 2500 and R.name_sim(l["name"], p["name"]) >= 0.75:
                        score, why = max((score, why or ""), (1.5, "STRONG_NAME_%dm" % dist))
                    elif (dist < 400 and lsub and (lsub & isub)) or (dist < 150 and R.core_sim(l["name"], p["name"]) >= 0.5):
                        score, why = max((score, why or ""), (1 + (400 - dist) / 1000.0, "PROXIMITY_%dm" % dist))
            if score:
                best.append((score, why, ident))
        if not best and l["street"]:
            at = [ident for ident in identities if ident["kind"] != "DISCOVERY" and l_ts == is_ts([ident["name"]] + ident.get("dbpr_names", []))
                  and any(p["street"] and R.same_address(l["street"], p["street"]) for p in points(ident))]
            if len(at) == 1:
                at[0]["leads"].append(l)
                at[0]["binds"].append(["LEAD_ADDRESS_WITH_BRAND_NAME_CONFLICT", l["key"]])
                at[0]["flags"].append(["BRAND_NAME_CONFLICT_AT_SAME_ADDRESS", l["key"], l["name"]])
                continue
            if len(at) > 1:
                for ident in at:
                    ident["leads"].append(l)
                    ident["binds"].append(["UMBRELLA_LISTING_AT_SHARED_ADDRESS", l["key"]])
                decisions.append(["LEAD_UMBRELLA_SHARED", l["key"], [x["anchor"] for x in at]])
                continue
        if not best:
            unattached.append(l)
            continue
        best.sort(key=lambda t: -t[0])
        top = [b for b in best if b[0] == best[0][0] or (best[0][0] < 2 and b[0] < 2 and best[0][0] - b[0] < 0.08)]
        if len(top) > 1:
            if len({tuple(t[2]["licenses"]) for t in top}) == 1 and top[0][2]["licenses"]:
                for t in top:
                    t[2]["leads"].append(l)
                    t[2]["binds"].append(["SHARED_DUAL_BRAND_LISTING", l["key"]])
                continue
            ambiguous.append({"lead": l["key"], "name": l["name"], "candidates": sorted(t[2]["anchor"] for t in top)})
            continue
        top[0][2]["leads"].append(l)
        top[0][2]["binds"].append([top[0][1], l["key"]])

    for l in unattached:
        placed = None
        for ident in identities:
            if ident["kind"] != "DISCOVERY":
                continue
            for p in ident["leads"]:
                if R.brand_conflict(l["name"], p["name"]):
                    continue
                if (l["street"] and p["street"] and R.same_address(l["street"], p["street"])) or \
                   (l["lat"] and p["lat"] and R.haversine_m(l["lat"], l["lng"], p["lat"], p["lng"]) < 120 and R.core_sim(l["name"], p["name"]) >= 0.5):
                    placed = ident
                    break
            if placed:
                break
        if placed is None:
            placed = new_identity("DISCOVERY", l["key"], l["name"])
        placed["leads"].append(l)
    return identities, decisions, ambiguous, lead_by_key


# ---------------------------------------------------------------------------
# 3-5. rulings, classification, geography
# ---------------------------------------------------------------------------

def apply_identity_rulings(identities):
    path = STAGING / "identity_rulings_001.json"
    if not path.exists():
        return []
    rulings = json.loads(path.read_text(encoding="utf-8"))
    by_anchor = {i["anchor"]: i for i in identities}
    applied = []
    for b in rulings.get("bind_brand_code_to_licence", []):
        brand = next(i for i in identities if b["brand_code"] in i["brand_codes"])
        lic = next((i for i in identities if i is not brand and b["licence"] in i["licenses"] and i["kind"] == "DBPR_LICENSE"), None)
        if lic is None:
            if b["licence"] not in brand["licenses"]:
                raise ValueError("identity ruling cannot find licence %s" % b["licence"])
            brand["binds"].append(["IDENTITY_RULING", b["licence"], b["basis"]])
            brand["ruling_identity_state"] = b["identity_state"]
            if b.get("hold"):
                brand["flags"].append(["RULING_HOLD", b["hold"], b["basis"]])
            applied.append({"ruling": "confirm", "brand_code": b["brand_code"], "licence": b["licence"], "absorbed_anchor": None})
            continue
        brand["licenses"] = list(lic["licenses"])
        brand["dbpr_names"] = lic.get("dbpr_names", [])
        brand["leads"] += [l for l in lic["leads"] if l not in brand["leads"]]
        brand["flags"] += lic["flags"]
        brand["binds"].append(["IDENTITY_RULING", b["licence"], b["basis"]])
        brand["ruling_identity_state"] = b["identity_state"]
        if b.get("hold"):
            brand["flags"].append(["RULING_HOLD", b["hold"], b["basis"]])
        identities.remove(lic)
        applied.append({"ruling": "bind", "brand_code": b["brand_code"], "licence": b["licence"], "absorbed_anchor": lic["anchor"]})
    for c in rulings.get("classify_identity", []):
        ident = by_anchor.get(c["anchor"]) or next(i for i in identities if c["anchor"] in i["brand_codes"] or c["anchor"] in i["licenses"])
        ident["ruling_class"] = [c["class"], c["basis"]]
        applied.append({"ruling": "classify", "anchor": c["anchor"], "class": c["class"]})
    return applied


def best_name(ident, lead_by_key, shared_leads=frozenset()):
    lic = [lead_by_key[k] for k in ident["licenses"]]
    want = {ident["split_brand"]} if ident.get("split_brand") else None
    order = ([l for l in ident["leads"] if l["src"] == "HILTON"] + [l for l in ident["leads"] if l["src"] in ("VISITTAMPABAY", "VISITSTPETECLEARWATER")]
             + [l for l in ident["leads"] if l["src"] == "OSM"])
    if ident["kind"] == "BRAND_CODE":
        slug_name = ident["leads"][0]["name"]
        order = sorted(order, key=lambda l: (-round(R.name_sim(slug_name, l["name"]), 3), {"HILTON": 0, "VISITTAMPABAY": 1, "VISITSTPETECLEARWATER": 1, "OSM": 2}[l["src"]], l["key"]))
    own = {ident["split_brand"]} if ident.get("split_brand") else (_subs(ident["leads"][0]["name"]) if ident["kind"] == "BRAND_CODE" else None)
    for l in order:
        if l["key"] in shared_leads:
            continue
        if want and not (_subs(l["name"]) & want):
            continue
        if own and len(_subs(l["name"])) > 1:
            continue
        if ident["kind"] != "DISCOVERY" and any(f[0] == "BRAND_NAME_CONFLICT_AT_SAME_ADDRESS" and f[1] == l["key"] for f in ident["flags"]):
            continue
        if len(l["name"]) >= 6 and not re.fullmatch(r"(?i)(marriott|hotel|motel|resort)", l["name"].strip()):
            return re.sub(r"\s+", " ", l["name"].replace("�", "")).strip()
    if ident["kind"] == "BRAND_CODE" and ident["brand_codes"][0].startswith("MARRIOTT:"):
        return ident["name"].title().replace("And ", "and ").replace(" At ", " at ")
    if lic:
        base = lic[0]["name"].title()
        return base + (" (%s)" % ident["split_brand"].replace("_", " ").title() if ident.get("split_brand") else "")
    return ident["name"]


def classify_all(identities, lead_by_key):
    rows = []
    lead_use = collections.Counter(l["key"] for ident in identities for l in ident["leads"])
    shared_leads = frozenset(k for k, n in lead_use.items() if n > 1)
    for ident in identities:
        lic = [lead_by_key[k] for k in ident["licenses"]]
        pts = lic + [l for l in ident["leads"] if l["src"] != "MARRIOTT_HARVEST"]
        names = [ident["name"]] + ([l["name"] for l in lic] if ident["kind"] != "DISCOVERY" else [p["name"] for p in pts])
        ranks = [l["extra"]["rank"] for l in lic]
        units = sum(l["extra"]["units"] for l in lic)
        klass, why = R.classify(names, ranks, units, sorted({p["src"] for p in pts}))
        if ident.get("ruling_class"):
            klass, why = ident["ruling_class"][0], "IDENTITY_RULING: " + ident["ruling_class"][1]
        order = {"HILTON": 0, "VISITTAMPABAY": 1, "VISITSTPETECLEARWATER": 1, "OSM": 2, "DBPR": 3}
        coord = sorted([p for p in pts if p.get("lat")], key=lambda p: (order[p["src"]], p["key"]))
        addrp = sorted([p for p in pts if p.get("street")], key=lambda p: ({"DBPR": 0, "HILTON": 1, "VISITTAMPABAY": 2, "VISITSTPETECLEARWATER": 2, "OSM": 3}[p["src"]], p["key"]))
        city = addrp[0]["city"] if addrp else ""
        postal = addrp[0]["zip"] if addrp else ""
        lat = coord[0]["lat"] if coord else None
        lng = coord[0]["lng"] if coord else None
        geo, corr, rule = R.assign(city, postal, lat, lng)
        if klass == "OUTSIDE":
            geo, corr, rule = "OUTSIDE", None, "IDENTITY_RULING"
        rows.append(dict(ident=ident, klass=klass, why=why, geo=geo, corridor=corr, geo_rule=rule, city=city, postal=postal, lat=lat, lng=lng,
                         street=addrp[0]["street"] if addrp else "", coord_source=(coord[0]["src"] if coord else None),
                         sources=sorted({p["src"] for p in pts} | ({"MARRIOTT_HARVEST"} if any(c.startswith("MARRIOTT") for c in ident["brand_codes"]) else set())),
                         name=best_name(ident, lead_by_key, shared_leads)))
    return rows


# ---------------------------------------------------------------------------
# 6. routing + evidence -> partition state
# ---------------------------------------------------------------------------

PROPERTY_URL_RX = [
    re.compile(r"marriott\.com/(?:[a-z-]+/)?hotels/(?:travel/)?[a-z]{5}\b"), re.compile(r"hilton\.com/(?:[a-z-]+/)?hotels/[a-z0-9]{7}-"),
    re.compile(r"ihg\.com/[a-z]+/hotels/[a-z]{2}/[a-z]{2}/[^/]+/[a-z0-9]{5}/hoteldetail"), re.compile(r"hyatt\.com/.+/[a-z]{5}-"),
    re.compile(r"choicehotels\.com/[a-z-]+/[a-z-]+/[a-z-]+-hotels/[a-z]{2}\d{3}"), re.compile(r"wyndhamhotels\.com/[a-z0-9-]+/[a-z-]+-florida/[a-z0-9-]+/"),
    re.compile(r"bestwestern\.com/.+propertyCode\.\d+"),
]


def route_for(row):
    ident = row["ident"]
    urls = []
    for code in ident["brand_codes"]:
        for l in ident["leads"]:
            if l["src"] in ("HILTON", "MARRIOTT_HARVEST") and l["url"]:
                urls.append(l["url"])
    for l in sorted(ident["leads"], key=lambda l: ({"VISITTAMPABAY": 0, "VISITSTPETECLEARWATER": 0, "OSM": 1}.get(l["src"], 2), l["key"])):
        u = (l["url"] or "").strip()
        if u and "doubleclick" not in u and u not in urls:
            urls.append(u if u.startswith("http") else "http://" + u)
    if not urls:
        return None, "NO_URL"
    for u in urls:
        host = re.sub(r"^https?://(www\.)?", "", u.lower()).split("/")[0]
        if any(host.endswith(d) for d in REFUSING_BRAND_DOMAINS + CLIENT_RENDERED_DOMAINS):
            if any(rx.search(u.lower()) for rx in PROPERTY_URL_RX):
                return u, "BRAND_PROPERTY_URL"
            continue
        return u, "OWN_SITE_URL"
    return urls[0], "BRAND_INDEX_URL"


def partition_state(row, evidence, url_status):
    ident, klass = row["ident"], row["klass"]
    url, route_class = route_for(row)
    ev = evidence.get(ident["anchor"], []) + [e for code in ident["brand_codes"] for e in evidence.get(code, []) if code != ident["anchor"]]
    for k in ident["licenses"]:
        if k != ident["anchor"]:
            ev += evidence.get(k, [])
    seen, ev2 = set(), []
    for e in ev:
        if (e["anchor"], e["requested_url"]) not in seen:
            seen.add((e["anchor"], e["requested_url"]))
            ev2.append(e)
    ev = ev2
    holds = [f for f in ident["flags"] if f[0] in ("SAME_NAME_ADJACENT_LICENSE", "MULTI_BRAND_LICENCE_NAME", "RULING_HOLD")]
    holds += [f for f in ident["flags"] if f[0] == "BRAND_NAME_CONFLICT_AT_SAME_ADDRESS" and not f[1].startswith("OSM:")]
    if klass == "MIXED_RESORT_HOLD":
        return enums.AWAITING_CENSUS_REVIEW, "MIXED_RESORT_HOLD: " + row["why"], url, route_class, ev, "MIXED_RESORT"
    if row["corridor"] is None:
        return enums.AWAITING_CENSUS_REVIEW, "GEOGRAPHY_HOLD: no corridor rule assigns this identity (%s)" % row["geo_rule"], url, route_class, ev, "GEOGRAPHY"
    if holds:
        return enums.AWAITING_IDENTITY_RESOLUTION, "IDENTITY_HOLD: " + "; ".join(str(h[0]) + ("=" + str(h[1]) if len(h) > 1 else "") for h in holds), url, route_class, ev, "IDENTITY"
    decisions = {e["decision"] for e in ev}
    if "PET_FRIENDLY" in decisions and "NO_PETS" in decisions:
        return enums.AWAITING_CONTRADICTION_RESOLUTION, "EVIDENCE_CONTRADICTION: pages disagree (acceptance and refusal)", url, route_class, ev, "EVIDENCE"
    if "PET_FRIENDLY" in decisions and "EVIDENCE_HOLD" in decisions:
        return enums.AWAITING_CONTRADICTION_RESOLUTION, "EVIDENCE_HOLD: one page reads as acceptance, another page's wording the shared reader declined", url, route_class, ev, "EVIDENCE"
    if "PET_FRIENDLY" in decisions:
        return enums.PUBLISHED_PET_FRIENDLY, "", url, route_class, ev, None
    if "NO_PETS" in decisions and "EVIDENCE_HOLD" not in decisions:
        return enums.VERIFIED_NO_PETS, "", url, route_class, ev, None
    if "EVIDENCE_HOLD" in decisions or "NO_PETS" in decisions:
        notes = sorted({e.get("note", "") for e in ev if e["decision"] in ("EVIDENCE_HOLD", "NO_PETS")})
        return enums.AWAITING_CONTRADICTION_RESOLUTION, "EVIDENCE_HOLD: " + " / ".join(notes), url, route_class, ev, "EVIDENCE"
    if "SILENT" in decisions:
        return enums.AWAITING_ATTENDED_CAPTURE, "Brand property page served but its policy card is client-rendered (accordion); attended capture required", url, route_class, ev, "ATTENDED"
    if "FETCH_FAILED" in decisions:
        return enums.AWAITING_ROUTING_REPLACEMENT, "Bound brand page returned a non-200 status at capture", url, route_class, ev, "ROUTING"
    if route_class == "NO_URL":
        return enums.AWAITING_OFFICIAL_URL, "No official or property URL found in any lane", None, route_class, ev, "ROUTING"
    host = re.sub(r"^https?://(www\.)?", "", url.lower()).split("/")[0]
    if route_class == "BRAND_INDEX_URL":
        return enums.AWAITING_PROPERTY_LEVEL_URL, "Only a brand index / locator URL is bound", url, route_class, ev, "ROUTING"
    if route_class == "BRAND_PROPERTY_URL":
        return enums.ACCESS_BLOCKED, "Brand property page refuses a plain client (403 / bot wall) this run; attended capture not completed for this property this run", url, route_class, ev, "ACCESS"
    status = url_status.get(url)
    if status not in (None, 200):
        return enums.AWAITING_ROUTING_REPLACEMENT, "Own-site URL did not serve (%s) at capture" % status, url, route_class, ev, "ROUTING"
    return enums.AWAITING_POLICY_OBSERVATION, "Own-site pages served; no operative pet policy wording captured (UNKNOWN, never a refusal)", url, route_class, ev, "OBSERVATION"


# ---------------------------------------------------------------------------
# 7. outputs
# ---------------------------------------------------------------------------

def write_json(path: Path, doc) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out_root = Path(argv[argv.index("--out-root") + 1]) if "--out-root" in argv else _REPO_ROOT
    staging_out = out_root / STAGING_REL
    reports_out = out_root / REPORTS_REL

    leads = build_leads()
    identities, decisions, ambiguous, lead_by_key = resolve(leads)
    applied = apply_identity_rulings(identities)
    rows = classify_all(identities, lead_by_key)
    evidence_records = EV.build()
    evidence = collections.defaultdict(list)
    for e in evidence_records:
        evidence[e["anchor"]].append(e)
    lane_doc = _load_optional("lane_attempts_001.json") or {"url_last_status": {}}
    url_status = lane_doc.get("url_last_status", {})

    IN_CENSUS = {"HOTEL", "MIXED_RESORT_HOLD"}
    census_rows, partition_items, ledger_rows, census_meta = [], [], [], []
    admitted = sorted([r for r in rows if r["klass"] in IN_CENSUS and r["geo"] != "OUTSIDE"], key=lambda r: r["ident"]["anchor"])
    names_seen = collections.Counter(ptf_identity_key(r["name"]) for r in admitted)
    final_names = {}
    for r in admitted:
        name = r["name"]
        if names_seen[ptf_identity_key(name)] > 1:
            name = "%s (%s)" % (name, r["street"].title() if r["street"] else r["ident"]["anchor"])
        final_names[id(r)] = name
    again = collections.Counter(ptf_identity_key(n) for n in final_names.values())
    for r in admitted:
        if again[ptf_identity_key(final_names[id(r)])] > 1:
            final_names[id(r)] = "%s [%s]" % (final_names[id(r)], (r["ident"]["brand_codes"] or [r["ident"]["anchor"]])[0].split(":")[1])
    for r in admitted:
        name = final_names[id(r)]
        state, reason, url, route_class, ev, hold_class = partition_state(r, evidence, url_status)
        ident = r["ident"]
        identity_state = enums.IDENTITY_CONFIRMED
        if state == enums.AWAITING_IDENTITY_RESOLUTION:
            identity_state = enums.IDENTITY_PROVISIONAL
        if ident.get("ruling_identity_state"):
            identity_state = ident["ruling_identity_state"]
        collision = enums.COLLISION_NONE
        if any(f[0] in ("SAME_NAME_ADJACENT_LICENSE", "BRAND_NAME_CONFLICT_AT_SAME_ADDRESS") for f in ident["flags"]):
            collision = enums.COLLISION_SHARED_ADDRESS if any(f[0] == "BRAND_NAME_CONFLICT_AT_SAME_ADDRESS" for f in ident["flags"]) else enums.COLLISION_PROPERTY_CODE
        lodging = enums.LODGING_CONFIRMED if r["klass"] == "HOTEL" else enums.LODGING_NEEDS_REVIEW
        policy = {enums.PUBLISHED_PET_FRIENDLY: enums.POLICY_OBSERVED, enums.VERIFIED_NO_PETS: enums.VERIFIED_NO_PETS}.get(state, enums.POLICY_NOT_VERIFIED)
        key = ptf_identity_key(name)
        lic = [lead_by_key[k] for k in ident["licenses"]]
        carried = {
            "tampa_anchor": ident["anchor"], "identity_kind": ident["kind"], "geography_class": r["geo"], "geography_rule": r["geo_rule"],
            "coordinates": {"lat": r["lat"], "lng": r["lng"], "source": r["coord_source"]} if r["lat"] is not None else None,
            "dbpr_licences": [{"license_number": l["sid"], "rank_code": l["extra"]["rank"], "dba": l["name"], "units": l["extra"]["units"], "licensee": l["extra"]["licensee"]} for l in lic],
            "brand_property_codes": ident["brand_codes"], "discovery_lanes": r["sources"], "lodging_class": r["klass"], "lodging_class_basis": r["why"],
            "route_class": route_class, "hold_class": hold_class, "identity_binds": ident["binds"], "identity_flags": ident["flags"],
        }
        census_rows.append(census_row(
            identity_key=key, canonical_name=name, slug=slugify(name), market_id=MARKET_ID, city=r["city"] or "Tampa", state="FL",
            postal_code=r["postal"], identity_state=identity_state, lodging_state=lodging, policy_state=policy,
            source="PTF-TAMPA-FL lanes: " + ", ".join(r["sources"]), source_id=ident["anchor"], address=r["street"],
            phone=(lic[0]["phone"] if lic else ""), corridor=r["corridor"] or "", assignment_basis=enums.BASIS_EXPLICIT if r["corridor"] else "",
            assignment_value=r["corridor"] or "", collision_state=collision, observed_at=AS_OF, provenance="tampa_fl_market_build_001",
            official_url=url or "", carried=carried))
        partition_items.append(partition_item(
            identity_key=key, canonical_name=name, slug=slugify(name), city=r["city"] or "Tampa", state="FL", postal_code=r["postal"],
            final_state=state, next_action_source=WORK_ORDER, determined_by=WORK_ORDER, updated_at=AS_OF, official_url=url or "",
            state_override_reason=reason))
        for e in ev:
            ledger_rows.append(dict(identity_key=key, canonical_name=name, **{k: v for k, v in e.items()}))
        census_meta.append({"key": key, "state": state, "corridor": r["corridor"], "row": r, "hold_class": hold_class})

    census_doc = census_document(MARKET_ID, census_rows, captured_at=AS_OF,
                                 note="Tampa Bay shadow census (%s). Backbone: Florida DBPR active public-lodging licences (HOTL/MOTL) for Hillsborough and Pinellas counties plus Wesley Chapel, Pasco; brand, CVB and OSM lanes bind names, codes, URLs and coordinates. Timeshare, vacation-rental, resort-residence, non-hotel, restricted and outside identities are accounted in the accounting report, not admitted." % WORK_ORDER,
                                 source_authorities=["tampa_fl_market_build_001", "raw_captures/dbpr_lodging_inscope_001.json", "raw_captures/hilton_inventory_001.json",
                                                     "raw_captures/visittampabay_hotels_001.json", "raw_captures/visitstpeteclearwater_hotels_001.json",
                                                     "raw_captures/osm_overpass_lodging_001.json", "raw_captures/marriott_owned_harvest_codes_001.json"])
    census_doc["work_order"] = WORK_ORDER
    partition_doc = partition_document(MARKET_ID, partition_items, as_of=AS_OF,
                                       note="Tampa shadow partition. PUBLISHED_PET_FRIENDLY / VERIFIED_NO_PETS only where a durable first-party page was read by the shared readers; every other row carries one honest blocker.",
                                       source_authorities=["tampa_fl_market_build_001", "tampa_fl_policy_evidence_001"])
    partition_doc["work_order"] = WORK_ORDER

    # ---- market config
    corr_rows = collections.defaultdict(list)
    for m in census_meta:
        if m["corridor"]:
            corr_rows[m["corridor"]].append(m)
    corridors = []
    for order, (cid, label, klass) in enumerate(R.CORRIDORS, start=1):
        ms = corr_rows.get(cid, [])
        if not ms:
            continue
        corridors.append({
            "corridor_id": "%s__%s" % (MARKET_ID, cid), "market_id": MARKET_ID, "name": label, "slug": cid,
            "title": "Pet-Friendly Hotels in %s | PetTripFinder Tampa Bay" % label,
            "meta_description": "Verified pet-friendly hotels in %s, Tampa Bay, Florida, with pet policies read from each hotel's own official website." % label,
            "description": "%s corridor of Tampa Bay (%s); assignment is explicit per hotel from coordinates and city (tampa_fl_identity_rules_001.assign)." % (label, klass),
            "included_cities": [], "included_postal_codes": sorted({m["row"]["postal"] for m in ms if m["row"]["postal"]}),
            "explicit_hotel_ids": sorted(m["key"] for m in ms),
            "excluded_hotel_ids": [], "minimum_hotel_count": 5, "show_in_navigation": False, "show_in_sitemap": False,
            "allow_multi_corridor": True, "display_order": order, "display_area": label, "state_code": "FL",
        })
    market_config = {
        "schema": "ptf-market/1.1", "market_id": MARKET_ID, "market_name": "Tampa – Tampa Bay, Florida", "market_slug": MARKET_ID,
        "state_name": "Florida", "state_code": "FL", "primary_state_code": "FL", "states": ["FL"], "primary_city": "Tampa", "country_code": "US",
        "title": "Pet-Friendly Hotels in Tampa Bay, Florida | PetTripFinder",
        "meta_description": "Verified pet-friendly hotels across Tampa Bay -- Downtown Tampa, Ybor City, Westshore/TPA Airport, Busch Gardens/USF, Clearwater Beach, St. Petersburg and the Gulf Beaches.",
        "introductory_copy": "", "navigation_label": "Tampa Bay, FL", "show_in_navigation": False, "show_in_sitemap": False,
        "minimum_published_hotels": 5, "route_mode": "market_prefixed", "corridors": corridors,
    }

    # ---- authority shards (empty; shadow build binds routes on the census rows only)
    routing_shard = {"schema": "ptf-identity-routing/1.0", "market_id": MARKET_ID, "note": "SHADOW_UNTIL_REGISTERED: no global routing bindings emitted; per-row route on census official_url + carried route_class.", "count": 0, "routes": []}
    exclusions_shard = {"schema": "ptf-hotel-exclusions/1.0", "market_id": MARKET_ID, "exclusions": []}

    out = {}
    lp = staging_out / "launch_package"
    out["census"] = write_json(lp / "identity_census" / ("%s.json" % MARKET_ID), census_doc)
    out["partition"] = write_json(lp / ("tampa_fl_final_partition_001.json"), partition_doc)
    out["market"] = write_json(lp / "markets" / ("%s.json" % MARKET_ID), market_config)
    out["routing_shard"] = write_json(lp / "markets" / "authority" / MARKET_ID / "identity_routing.json", routing_shard)
    out["exclusions_shard"] = write_json(lp / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json", exclusions_shard)
    seed = lp / "markets" / "authority" / MARKET_ID / "seed_businesses.csv"
    seed.parent.mkdir(parents=True, exist_ok=True)
    with seed.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerow(["name", "category", "address", "city", "state", "postal_code", "phone", "website_url", "source_url",
                                                     "source_type", "observed_at", "rating", "amenities", "pet_policy", "canonical", "market_id"])
    out["seed_csv"] = hashlib.sha256(seed.read_bytes()).hexdigest()
    out["evidence_ledger"] = write_json(lp / "tampa_fl_policy_evidence_ledger_001.json", {
        "schema": "ptf-tampa-fl-policy-evidence-ledger/1.0", "market_id": MARKET_ID, "work_order": WORK_ORDER, "count": len(ledger_rows),
        "rows": sorted(ledger_rows, key=lambda e: (e["identity_key"], e["requested_url"]))})

    # ---- accounting
    acct = accounting(rows, census_meta, ambiguous, decisions, applied, evidence_records, market_config)
    out["accounting"] = write_json(reports_out / "tampa_fl_source_ready_accounting_001.json", acct)
    out["identity_resolution"] = write_json(staging_out / "tampa_fl_identity_resolution_001.json", {
        "schema": "ptf-tampa-fl-identity-resolution/1.0", "market_id": MARKET_ID,
        "identities": [{"anchor": r["ident"]["anchor"], "kind": r["ident"]["kind"], "name": r["name"], "class": r["klass"], "class_basis": r["why"],
                        "geography": r["geo"], "corridor": r["corridor"], "geography_rule": r["geo_rule"], "city": r["city"], "postal": r["postal"],
                        "street": r["street"], "lat": r["lat"], "lng": r["lng"], "lanes": r["sources"], "licences": r["ident"]["licenses"],
                        "brand_codes": r["ident"]["brand_codes"], "leads": sorted(l["key"] for l in r["ident"]["leads"]), "binds": r["ident"]["binds"],
                        "flags": r["ident"]["flags"]} for r in sorted(rows, key=lambda r: r["ident"]["anchor"])],
        "decisions": decisions, "ambiguous_leads": ambiguous, "rulings_applied": applied})
    for k, v in out.items():
        print("%-20s %s" % (k, v[:16]))
    print("census rows", len(census_rows), collections.Counter(m["state"] for m in census_meta))
    return 0


def accounting(rows, census_meta, ambiguous, decisions, applied, evidence_records, market_config):
    klass = collections.Counter()
    for r in rows:
        if r["klass"] in ("HOTEL", "MIXED_RESORT_HOLD") and r["geo"] == "OUTSIDE":
            klass["OUTSIDE"] += 1
        elif r["klass"] == "REVIEW_NO_LICENSE" and r["geo"] == "OUTSIDE":
            klass["OUTSIDE"] += 1
        else:
            klass[r["klass"]] += 1
    census_n = len(census_meta)
    states = collections.Counter(m["state"] for m in census_meta)
    holds = collections.Counter(m["hold_class"] for m in census_meta if m["hold_class"])
    by_corr = collections.defaultdict(lambda: collections.Counter())
    for m in census_meta:
        by_corr[m["corridor"] or "(geography hold)"][m["state"]] += 1
    corridor_pages = {c["slug"]: {"census": sum(by_corr[c["slug"]].values()), "pet_friendly": by_corr[c["slug"]][enums.PUBLISHED_PET_FRIENDLY],
                                  "page_eligible": by_corr[c["slug"]][enums.PUBLISHED_PET_FRIENDLY] >= c["minimum_hotel_count"]} for c in market_config["corridors"]}
    review = [r for r in rows if r["klass"] == "REVIEW_NO_LICENSE" and r["geo"] != "OUTSIDE"]
    census_rows_geo = [m["row"] for m in census_meta]
    review_out = collections.Counter()
    review_detail = []
    for r in review:
        near = sorted([(R.haversine_m(r["lat"], r["lng"], c["lat"], c["lng"]), c) for c in census_rows_geo if r["lat"] is not None and c["lat"] is not None], key=lambda t: t[0])
        verdict = "REVIEW"
        target = None
        rs = _subs(r["name"])
        for dist, c in near[:5]:
            cs = _subs(c["name"])
            if dist <= 400 and rs and (rs & cs):
                verdict, target = "DUPLICATE", c["ident"]["anchor"]
                break
            if dist <= 150 and rs and cs and not (rs & cs):
                verdict, target = "REBRAND", c["ident"]["anchor"]
                break
            if dist <= 150 and R.core_sim(r["name"], c["name"]) >= 0.5:
                verdict, target = "DUPLICATE", c["ident"]["anchor"]
                break
        review_out[verdict] += 1
        review_detail.append({"anchor": r["ident"]["anchor"], "name": r["name"], "corridor": r["corridor"], "verdict": verdict, "nearest_census_anchor": target})
    pf = states[enums.PUBLISHED_PET_FRIENDLY]
    np_ = states[enums.VERIFIED_NO_PETS]
    total = len(rows)
    buckets = {
        "PROPOSED_CENSUS": census_n,
        "OUTSIDE": klass["OUTSIDE"], "TIMESHARE": klass["TIMESHARE"], "VACATION_RENTAL": klass["VACATION_RENTAL"], "RESORT_RESIDENCE": klass["RESORT_RESIDENCE"],
        "NON_HOTEL": klass["NON_HOTEL"] + klass["NON_HOTEL_BNB"], "RESTRICTED_NON_PUBLIC": klass["RESTRICTED_NON_PUBLIC"],
        "LEAD_REVIEW_DUPLICATE": review_out["DUPLICATE"], "LEAD_REVIEW_REBRAND": review_out["REBRAND"], "LEAD_REVIEW_OPEN": review_out["REVIEW"],
    }
    assert sum(buckets.values()) == total, (sum(buckets.values()), total, buckets)
    beaches = [m for m in census_meta if m["corridor"] in ("clearwater-beach", "st-pete-beach-gulf-beaches")]
    downtown_core = [m for m in census_meta if m["corridor"] in ("downtown-tampa-riverwalk", "ybor-city", "downtown-st-petersburg", "downtown-clearwater")]
    return {
        "schema": "ptf-tampa-fl-source-ready-accounting/1.0", "market_id": "tampa-fl", "work_order": "PTF-TAMPA-FL-PARALLEL-SOURCE-READY-001", "as_of": AS_OF,
        "unit": "premises identity after cross-lane resolution (a DBPR licence group or a brand property code); lead-level duplicates are reported separately",
        "TOTAL_DISCOVERED": total, "reconciliation": buckets, "reconciles": sum(buckets.values()) == total,
        "PROPOSED_CENSUS": census_n, "VALID_PET_FRIENDLY": pf, "VALID_VERIFIED_NO_PETS": np_, "RESOLVED": pf + np_, "UNRESOLVED": census_n - pf - np_,
        "partition_states": dict(sorted(states.items())),
        "HOLDS": {"IDENTITY_HOLDS": holds["IDENTITY"], "ROUTING_HOLDS": holds["ROUTING"], "ACCESS_BLOCKED": holds["ACCESS"], "EVIDENCE_HOLDS": holds["EVIDENCE"],
                  "ATTENDED_CAPTURE_HOLDS": holds["ATTENDED"], "POLICY_OBSERVATION_PENDING": holds["OBSERVATION"], "GEOGRAPHY_HOLDS": holds["GEOGRAPHY"],
                  "MIXED_RESORT_HOLDS": holds["MIXED_RESORT"], "PAID_HOLDS": 0, "FOUNDER_HOLDS": 0},
        "EXCLUSIONS": {"CLOSED_RETIRED": 0, "OUTSIDE": klass["OUTSIDE"], "NON_HOTEL": klass["NON_HOTEL"] + klass["NON_HOTEL_BNB"],
                       "VACATION_RENTAL": klass["VACATION_RENTAL"], "TIMESHARE": klass["TIMESHARE"], "RESORT_RESIDENCE": klass["RESORT_RESIDENCE"],
                       "RESTRICTED_NON_PUBLIC": klass["RESTRICTED_NON_PUBLIC"]},
        "lead_level": {"ambiguous_leads_unattached_counted_as_duplicate": len(ambiguous), "ambiguous_leads": ambiguous},
        "discovery_lead_review": {"counts": dict(review_out), "detail": sorted(review_detail, key=lambda d: d["anchor"])},
        "corridor_coverage": {k: {"census": sum(v.values()), "states": dict(sorted(v.items()))} for k, v in sorted(by_corr.items())},
        "corridor_pages": corridor_pages,
        "gulf_beach_vacation_ownership_audit": {
            "BEACH_CORRIDOR_QUALIFYING_HOTELS": len(beaches), "BEACH_CORRIDOR_PET_FRIENDLY": sum(1 for m in beaches if m["state"] == enums.PUBLISHED_PET_FRIENDLY),
            "DOWNTOWN_CORE_QUALIFYING_HOTELS": len(downtown_core), "DOWNTOWN_CORE_PET_FRIENDLY": sum(1 for m in downtown_core if m["state"] == enums.PUBLISHED_PET_FRIENDLY),
            "TIMESHARE_EXCLUSIONS": klass["TIMESHARE"], "VACATION_RENTAL_EXCLUSIONS": klass["VACATION_RENTAL"],
            "MIXED_RESORT_HOLDS": holds["MIXED_RESORT"], "AMBIGUOUS_PREMISES_HOLDS": holds["IDENTITY"],
            "no_unit_in_census_proof": "every census row carries a DBPR HOTL/MOTL licence (or is a MIXED_RESORT_HOLD with lodging_state NEEDS_REVIEW); no TAPT/BNB/CNDO/DWEL/NAPT unit licence, numbered condo unit, timeshare or vacation-rental identity is admitted -- checked by FAST 15.",
        },
        "evidence": {"records": len(evidence_records), "decisions": dict(collections.Counter(e["decision"] for e in evidence_records)),
                     "lanes": dict(collections.Counter(e["capture_lane"] for e in evidence_records)), "paid_provider_calls": 0, "usd_spent": 0},
        "identity_decisions": dict(collections.Counter(d[0] if not d[0].startswith("MARRIOTT_PROXIMITY") else "MARRIOTT_PROXIMITY_BRAND" for d in decisions)),
        "identity_rulings_applied": applied,
    }


if __name__ == "__main__":
    raise SystemExit(main())

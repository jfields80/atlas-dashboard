"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phases 3/4/11/12.

Reconcile EVERY shadow identity -- the zero-cost OpenStreetMap discovery
candidates and the first-party brand-directory harvest -- against the pinned
188-row census, on physical / deterministic signals:

    canonical first-party URL, brand property code        (decide alone)
    exact street + postal, telephone                      (propose; a
        compatible name or a second premises signal confirms)
    current brand vs historical brand, building/unit      (successor vs
        same-campus questions -> founder)

A name may PROPOSE a match; a name may never DECIDE one. Nothing is
fuzzy-merged. The result is one reconciliation report and a SHADOW census
(prior 188 rows + the TRUE_MISSING additions, schema-validated) written to
identity_census/recensus/ -- the pinned census is never touched.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict, defaultdict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402
from scripts.pettripfinder.discovery.duplicates import normalize_phone, normalize_street  # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.markets.contract import slugify  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-shadow-recensus-reconciliation/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
RECENSUS_DIR = os.path.join(PKG, "identity_census", "recensus")
OSM_CANDIDATES = os.path.join(_DASH, "data", "discovery", "cleveland_akron_canton_oh_recensus_001", "candidates", f"{MARKET_ID}_candidates.json")
DISCOVERY_CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "cleveland_akron_canton_oh.json")

NON_LODGING = re.compile(r"\b(restaurant|winery|brewery|golf|country club|banquet|catering|tavern|grill|campground|rv park|"
                         r"apartments?|conference center|event center|hostel|dormitor|residence hall|hall of fame|casino|arena|stadium)\b", re.I)
LODGING = re.compile(r"\b(inn|hotel|suites?|lodge|motel|resort|bed and breakfast|b ?and ?b|b&b|guest ?house|cabins?|extended stay|residence|studio|manor)\b", re.I)
BRANDS = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|moxy|element|renaissance|ritz"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|curio"),
    ("IHG", r"holiday inn|crowne? plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring|everhome"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|trademark|knights inn"),
    ("ESA", r"extended stay america"), ("BEST_WESTERN", r"best western|surestay"), ("MOTEL6", r"motel 6|studio 6"),
    ("RED_ROOF", r"red roof|hometowne"), ("SONESTA", r"sonesta|simply suites"), ("RADISSON", r"radisson|country inn|park inn"),
    ("INTOWN", r"intown suites"), ("DRURY", r"drury"), ("MY_PLACE", r"my place"), ("HYATT", r"hyatt"), ("MAGNUSON", r"magnuson"),
]


def brand_of(name: str) -> str:
    n = (name or "").lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def canon_url(url: str) -> str:
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = re.sub(r"[?#].*$", "", u).rstrip("/")
    return u


def street_key(address: str, postal: str) -> str:
    st = normalize_street(address or "")
    pc = (postal or "")[:5]
    if not st or not pc or not re.match(r"^\d", st):
        return ""
    return st + "|" + pc


_ORDINAL = re.compile(r"^(\d+)(st|nd|rd|th)$")
_STREET_WORDS = {"e", "east", "w", "west", "n", "north", "s", "south", "ne", "nw", "se", "sw", "st", "street", "ave", "avenue",
                 "rd", "road", "dr", "drive", "blvd", "boulevard", "ct", "court", "ln", "lane", "pkwy", "parkway", "hwy", "highway"}


def number_street(address: str) -> str:
    """'1940 East 6th Street' -> '1940|6'; '24 Public Square' -> '24|publ'. A
    house number plus the first distinctive street token, for rows that carry
    no postal code. Proposes only."""
    toks = re.findall(r"[a-z0-9]+", (address or "").lower())
    if not toks or not toks[0].isdigit():
        return ""
    for t in toks[1:]:
        if t in _STREET_WORDS:
            continue
        m = _ORDINAL.match(t)
        core = m.group(1) if m else t
        return toks[0] + "|" + core[:4]
    return ""


def shadow_from_osm(path):
    if not os.path.exists(path):
        return []
    doc = read_json(path)
    cands = doc if isinstance(doc, list) else doc.get("candidates", [])
    out = []
    for c in cands:
        recs = c.get("source_records") or []
        phone = next((r.get("phone") for r in recs if r.get("phone")), "")
        cats = set()
        status = set()
        for r in recs:
            cats.update(r.get("provider_categories") or [])
            if r.get("business_status"):
                status.add(r["business_status"])
        out.append(OrderedDict([
            ("source", "openstreetmap"), ("source_id", c.get("candidate_id") or ";".join(str(p) for p in (c.get("provider_ids") or [])[:1])),
            ("name", c.get("name") or ""), ("address", c.get("address_line") or ""), ("city", c.get("city") or ""), ("state", c.get("state") or "OH"),
            ("postal_code", (c.get("postal_code") or "")[:5]), ("phone", phone or ""), ("website_url", c.get("website_url") or ""),
            ("categories", sorted(cats)), ("business_status", sorted(status)), ("lifecycle_status", c.get("lifecycle_status")),
            ("latitude", c.get("latitude")), ("longitude", c.get("longitude")), ("page_identity", None),
        ]))
    return out


def shadow_from_harvest(path):
    if not os.path.exists(path):
        return []
    doc = read_json(path)
    out = []
    for c in doc.get("candidates", []):
        page = c.get("page") or {}
        if page.get("status") != 200:
            continue
        ident = page.get("identity") or {}
        name = ident.get("name") or ""
        if not name:
            # fall back to the <title> before any " | " / " - " separator
            t = page.get("title") or ""
            name = re.split(r"\s+[|\-–]\s+", t)[0].strip()
        if page.get("soft_404_suspected") or re.match(r"(?i)search results|hotels? in|find hotels", name or ""):
            # a delisted brand page names nothing; the URL slug is the only trace of the property
            slug = re.sub(r"/overview/?$", "", c["url"].rstrip("/")).rsplit("/", 1)[-1]
            name = "(delisted) " + slug.replace("-", " ")
        out.append(OrderedDict([
            ("source", "brand_directory"), ("source_id", c["url"]), ("name", name), ("address", ident.get("street") or ident.get("street_address") or ""),
            ("city", ident.get("locality") or ident.get("city") or ""), ("state", ident.get("region") or "OH"), ("postal_code", (ident.get("postal_code") or "")[:5]),
            ("phone", ident.get("telephone") or ident.get("phone") or ""), ("website_url", c["url"]), ("categories", ["hotel"]), ("business_status", []),
            ("lifecycle_status", None), ("latitude", None), ("longitude", None), ("page_identity", ident), ("family", c["family"]),
            ("property_code", ident.get("property_code") or DEDUP.property_code({"official_url": c["url"]})), ("soft_404", page.get("soft_404_suspected")),
        ]))
    return out


def build(args) -> OrderedDict:
    census_doc = read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))
    census = census_doc["hotels"]
    market = read_json(os.path.join(PKG, "markets", f"{MARKET_ID}.json"))
    config = read_json(DISCOVERY_CONFIG)
    audit = read_json(os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_census_audit_005.json"))
    replay = read_json(os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_evidence_replay_006.json"))
    conversion_keys = {k for f in audit["findings"] if f["kind"] in ("CONVERSION_OR_RENAME_PENDING", "PRIOR_RENAME_OR_REVIEW_TRACE") for k in f["identity_keys"]}
    # registered rows whose CURRENT first-party page bound to them in this order (live static re-read or owned-evidence replay)
    page_bound_live = set()
    live_p = os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_live_audit_010.json")
    if os.path.exists(live_p):
        for row in read_json(live_p)["rows"]:
            if (row.get("live_audit") or "").startswith("CURRENTLY_CORRECT") or ((row.get("identity_assessment") or {}).get("confirmed") is True) or ((row.get("text_bound_read") or {}).get("text_bound")):
                page_bound_live.add(row["identity_key"])
    for rec in replay["records"]:
        if any(c in ("AGREES_WITH_LIVE_PF", "AGREES_WITH_LIVE_NO_PETS") for c in rec.get("classification", [])):
            page_bound_live.add(rec["identity_key"])

    postal_to_corridor = {}
    for c in market["corridors"]:
        for pc in c.get("included_postal_codes") or []:
            postal_to_corridor[pc] = c["corridor_id"]
    census_postals = {(r.get("postal_code") or "")[:5] for r in census}
    postal_city = {}
    for r in census:
        postal_city.setdefault((r.get("postal_code") or "")[:5], r.get("city") or "")
    municipalities = {m.lower() for m in config["included_municipalities"]}
    bounds = config["geographic_bounds"]

    by_key = {r["identity_key"]: r for r in census}
    by_url, by_code, by_street, by_phone, by_number, by_number_street = {}, {}, defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for r in census:
        ns = number_street(r.get("address") or "")
        if ns:
            by_number_street[ns].append(r["identity_key"])
        m_num = re.match(r"\s*(\d+)", r.get("address") or "")
        if m_num and (r.get("postal_code") or "")[:5]:
            by_number[(m_num.group(1), (r.get("postal_code") or "")[:5])].append(r["identity_key"])
        u = canon_url(r.get("official_url") or "")
        if u:
            by_url[u] = r["identity_key"]
        code = DEDUP.property_code({"official_url": r.get("official_url") or ""})
        if code:
            by_code[code] = r["identity_key"]
        sk = street_key(r.get("address") or "", r.get("postal_code") or "")
        if sk:
            by_street[sk].append(r["identity_key"])
        ph = normalize_phone(r.get("phone") or "")
        if ph:
            by_phone[ph].append(r["identity_key"])
    # owned evidence for identities not in the census (e.g. a pass-3 page that named a different hotel)
    owned_new = {}
    for rec in replay["records"]:
        if not rec.get("identity_in_census") and rec.get("replay") in ("PET_FRIENDLY_STATED", "NO_PETS_STATED"):
            owned_new[canon_url(rec.get("final_url") or "")] = rec

    shadow = shadow_from_osm(OSM_CANDIDATES) + shadow_from_harvest(os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_brand_directory_harvest_003.json"))
    # de-duplicate the shadow itself on url / street / phone, keeping the richer record
    seen_sig = {}
    merged = []
    for s in shadow:
        sig = canon_url(s["website_url"]) or street_key(s["address"], s["postal_code"]) or normalize_phone(s["phone"]) or ("name:" + ptf_identity_key(s["name"]) if s["name"].strip() else "")
        if sig and sig in seen_sig:
            prev = merged[seen_sig[sig]]
            prev.setdefault("also_seen_as", []).append(OrderedDict([("source", s["source"]), ("source_id", s["source_id"]), ("name", s["name"])]))
            for f in ("address", "postal_code", "phone", "website_url", "city"):
                if not prev.get(f) and s.get(f):
                    prev[f] = s[f]
            continue
        if sig:
            seen_sig[sig] = len(merged)
        merged.append(s)

    results = []
    for s in merged:
        name = (s["name"] or "").strip()
        r = OrderedDict([("source", s["source"]), ("source_id", s["source_id"]), ("name", name), ("address", s["address"]), ("city", s["city"]),
                         ("postal_code", s["postal_code"]), ("phone", s["phone"]), ("website_url", s["website_url"]), ("brand_family", s.get("family") or brand_of(name))])
        signals = OrderedDict()
        matched = OrderedDict()
        if not name:
            r["classification"] = "IDENTITY_UNRESOLVED"
            r["why"] = "unnamed candidate"
            results.append(r)
            continue
        key = ptf_identity_key(name)
        r["identity_key"] = key
        if key in by_key:
            matched["EXACT_KEY"] = key
        u = canon_url(s["website_url"])
        if u and u in by_url:
            matched["CANONICAL_URL"] = by_url[u]
        code = s.get("property_code") or DEDUP.property_code({"official_url": s["website_url"] or ""})
        if code and code in by_code:
            matched["PROPERTY_CODE"] = by_code[code]
        sk = street_key(s["address"], s["postal_code"])
        if sk and sk in by_street:
            signals["STREET_AND_POSTAL"] = by_street[sk]
        else:
            m_num = re.match(r"\s*(\d+)", s["address"] or "")
            if m_num and s["postal_code"] and (m_num.group(1), s["postal_code"]) in by_number:
                ns_mine = number_street(s["address"] or "")
                same_street = [k for k in by_number[(m_num.group(1), s["postal_code"])] if number_street(by_key[k].get("address") or "") == ns_mine]
                if same_street:
                    signals["STREET_NUMBER_AND_POSTAL"] = same_street
            elif not s["postal_code"]:
                ns = number_street(s["address"] or "")
                if ns and ns in by_number_street:
                    signals["STREET_NUMBER_AND_STREET_TOKEN"] = by_number_street[ns]
        ph = normalize_phone(s["phone"])
        if ph and ph in by_phone:
            signals["TELEPHONE"] = by_phone[ph]
        name_props = [k for k, row in by_key.items() if DEDUP.names_compatible(name, row["canonical_name"])]
        r["deciding_matches"] = matched
        r["proposing_signals"] = signals
        r["name_compatible_with"] = name_props[:5]

        # geography
        pc = s["postal_code"]
        in_market = bool(pc and (pc in postal_to_corridor or pc in census_postals)) or (s["city"] or "").lower() in municipalities
        if not in_market and s.get("latitude") is not None:
            in_market = bounds["min_lat"] <= float(s["latitude"]) <= bounds["max_lat"] and bounds["min_lng"] <= float(s["longitude"]) <= bounds["max_lng"]
        r["in_market"] = in_market
        r["corridor"] = postal_to_corridor.get(pc, "")

        lodging_name = bool(LODGING.search(name)) or r["brand_family"] != "INDEPENDENT"
        non_lodging = bool(NON_LODGING.search(name)) and not lodging_name
        closed = any(st.upper().startswith("CLOSED") for st in (s.get("business_status") or [])) or bool(s.get("soft_404")) or (s.get("lifecycle_status") or "").upper() in ("CLOSED", "PERMANENTLY_CLOSED")

        no_premises = not (s["postal_code"] or s["address"] or s.get("latitude") is not None)
        if "EXACT_KEY" in matched:
            cls, why = "ALREADY_REGISTERED_EXACT", "identity key equals a registered row"
        elif "CANONICAL_URL" in matched or "PROPERTY_CODE" in matched:
            cls, why = "ALREADY_REGISTERED_ALIAS", "canonical URL / property code decides: same page as registered row %s" % (matched.get("CANONICAL_URL") or matched.get("PROPERTY_CODE"))
        elif signals:
            keys = sorted({k for v in signals.values() for k in v})
            compatible = [k for k in keys if DEDUP.names_compatible(name, by_key[k]["canonical_name"])]
            same_family = [k for k in keys if r["brand_family"] != "INDEPENDENT" and brand_of(by_key[k]["canonical_name"]) == r["brand_family"]]
            street_signal = any(k in signals for k in ("STREET_AND_POSTAL", "STREET_NUMBER_AND_POSTAL", "STREET_NUMBER_AND_STREET_TOKEN"))
            two_signals = len(signals) >= 2
            if compatible:
                cls, why = "ALREADY_REGISTERED_ALIAS", "premises signal %s confirmed by a compatible name (%s)" % ("+".join(signals), compatible[0])
                matched["PREMISES_CONFIRMED_BY_NAME"] = compatible[0]
            elif same_family and (street_signal or two_signals):
                cls, why = "ALREADY_REGISTERED_ALIAS", "premises signal %s confirmed by the same brand family %s (%s); one brand does not run two of its own hotels at one address" % ("+".join(signals), r["brand_family"], same_family[0])
                matched["PREMISES_CONFIRMED_BY_BRAND_FAMILY"] = same_family[0]
            else:
                fams = {brand_of(by_key[k]["canonical_name"]) for k in keys}
                if street_signal and (r["brand_family"] != "INDEPENDENT" and fams - {r["brand_family"]}):
                    if s["source"] == "openstreetmap" and any(k in page_bound_live for k in keys):
                        cls, why = "PROPERTY_CLOSED_OR_CONVERTED", "OSM still names a different brand at the premises of %s, whose current first-party page bound to the registered identity in this order; the OSM row is the predecessor brand" % [k for k in keys if k in page_bound_live][0]
                    elif any(k in conversion_keys for k in keys):
                        cls, why = "SAME_IDENTITY_REBRAND_SUCCESSOR", "same street+postal as %s, different brand, and that row already carries a conversion trace" % keys[0]
                    else:
                        cls, why = "SAME_CAMPUS_DISTINCT_ENTITY", "same street+postal as %s under a different brand family; a dual-brand campus is two hotels unless the founder rules otherwise" % keys[0]
                elif street_signal:
                    cls, why = "PROBABLE_DUPLICATE", "same street+postal as %s but the names are not compatible; proposes, cannot decide" % keys[0]
                else:
                    cls, why = "PROBABLE_DUPLICATE", "shared telephone with %s and incompatible names (a switchboard may serve two hotels); proposes only" % keys[0]
        elif non_lodging:
            cls, why = "NON_LODGING", "name reads as a venue, not lodging"
        elif closed:
            cls, why = "PROPERTY_CLOSED_OR_CONVERTED", "source marks the property closed / the brand page is a soft 404 (delisted)"
        elif no_premises:
            cls, why = "IDENTITY_UNRESOLVED", "a directory or index page with no premises of its own"
        elif not in_market:
            cls, why = "OUTSIDE_MARKET", "postal %s / city %s is outside every corridor and every registered fringe postal" % (pc, s["city"])
        elif name_props:
            # A name proposes; the premises decide. If this row carries its own
            # numbered street + postal and EVERY proposed census row carries a
            # different house number, the proposal is refuted and the row is a
            # distinct premises. If either side lacks a house number, nothing
            # is decided and the row stays a proposal.
            my_num = (re.match(r"\s*(\d+)", s["address"] or "") or [None, ""])[1]
            their_nums = [(re.match(r"\s*(\d+)", by_key[k].get("address") or "") or [None, ""])[1] for k in name_props]
            if sk and my_num and all(n and n != my_num for n in their_nums):
                cls, why = "TRUE_MISSING_IDENTITY", "name proposed %s but every proposed row sits at a different house number (%s vs %s); distinct premises" % (name_props[0], my_num, "/".join(their_nums))
                r["name_proposal_refuted_by_premises"] = name_props[:3]
            else:
                cls, why = "PROBABLE_DUPLICATE", "name proposes %s but no physical signal agrees; a name cannot decide" % name_props[0]
        elif not sk:
            cls, why = "IDENTITY_UNRESOLVED", "no numbered street + postal to register a premises on"
        elif not lodging_name and s["source"] == "openstreetmap":
            cls, why = "IDENTITY_UNRESOLVED", "OSM lodging tag but the name carries no lodging word; needs a page before registration"
        else:
            cls, why = "TRUE_MISSING_IDENTITY", "in-market premises with a numbered street and postal that no registered row shares"
        if closed and cls in ("ALREADY_REGISTERED_EXACT", "ALREADY_REGISTERED_ALIAS"):
            r["closure_signal_on_registered_row"] = True
        r["classification"], r["why"] = cls, why
        ou = owned_new.get(u)
        if ou is not None:
            r["owned_evidence"] = OrderedDict([("artifact", ou["artifact_file"]), ("replay", ou["replay"]), ("quote", (ou.get("reader") or {}).get("pets_allowed_quote"))])
        results.append(r)

    # Coded brand-directory listings whose page refused a plain client (Marriott
    # /Hilton 403): the URL slug still names the property, so a listing may
    # CORROBORATE an OSM-only identity (name compatible + locality token) or a
    # registered row. It never supplies an address and never decides identity.
    listings = []
    hp = os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_brand_directory_harvest_003.json")
    if os.path.exists(hp):
        for c in read_json(hp).get("candidates", []):
            if c.get("selected_by") != "PROPERTY_CODE_PREFIX" or (c.get("page") or {}).get("status") == 200:
                continue
            slug = re.sub(r"/overview/?$", "", c["url"].rstrip("/")).rsplit("/", 1)[-1]
            code, _, rest = slug.partition("-")
            listings.append(OrderedDict([("family", c["family"]), ("url", c["url"]), ("code", code.upper()), ("slug_name", rest.replace("-", " "))]))
    corroborated = 0
    registered_listed = 0
    for r in results:
        if r["classification"] not in ("TRUE_MISSING_IDENTITY", "PROBABLE_DUPLICATE", "IDENTITY_UNRESOLVED"):
            continue
        for l in listings:
            if l["family"] == r["brand_family"] and DEDUP.names_compatible(r["name"], l["slug_name"]):
                r["first_party_directory_listing"] = l
                corroborated += 1
                break
    listed_census = []
    for l in listings:
        for k, row in by_key.items():
            if brand_of(row["canonical_name"]) == l["family"] and DEDUP.names_compatible(row["canonical_name"], l["slug_name"]):
                listed_census.append(OrderedDict([("identity_key", k), ("listing", l)]))
                registered_listed += 1
                break
    directory_summary = OrderedDict([("coded_listings_refusing_plain_client", len(listings)), ("shadow_rows_corroborated", corroborated),
                                     ("registered_rows_listed", registered_listed),
                                     ("listings_matching_nothing", [l for l in listings if not any(r.get("first_party_directory_listing") is l for r in results) and not any(x["listing"] is l for x in listed_census)])])

    # shadow census: prior rows + TRUE_MISSING additions
    additions = []
    for r in results:
        if r["classification"] != "TRUE_MISSING_IDENTITY":
            continue
        key = r["identity_key"]
        if any(a["identity_key"] == key for a in additions):
            continue
        confirmed = bool(r["source"] == "brand_directory" and r["address"] and r["postal_code"])
        if not r["city"]:
            r["city"] = postal_city.get(r["postal_code"], "")
            if not r["city"]:
                continue  # cannot register a premises with no locality
        additions.append(OrderedDict([
            ("identity_key", key), ("canonical_name", r["name"]), ("display_name", r["name"]), ("slug", slugify(r["name"])), ("market_id", MARKET_ID),
            ("address", r["address"]), ("city", r["city"] or ""), ("state", "OH"), ("postal_code", r["postal_code"]), ("phone", r["phone"] or ""),
            ("identity_state", "IDENTITY_CONFIRMED" if confirmed else "IDENTITY_PROVISIONAL"), ("lodging_state", "LODGING_BY_NAME"),
            ("policy_state", "POLICY_NOT_VERIFIED"), ("collision_state", "NONE"), ("official_url", r["website_url"] if r["source"] == "brand_directory" else ""),
            ("corridor", r["corridor"]), ("assignment_basis", "postal_code" if r["corridor"] else "unassigned"), ("assignment_value", r["postal_code"] if r["corridor"] else ""),
            ("source", r["source"]), ("source_id", r["source_id"]), ("observed_at", time.strftime("%Y-%m-%d", time.gmtime())),
            ("provenance", WORK_ORDER + ":" + r["source"].upper()), ("batch", "hardened-recensus-001"),
            ("admission", OrderedDict([("status", "SHADOW_TRUE_MISSING_AWAITING_FOUNDER"), ("basis", r["why"]), ("evidence_url", r["website_url"]),
                                       ("owned_policy_evidence", r.get("owned_evidence"))])),
        ]))
    shadow_doc = copy.deepcopy(census_doc)
    shadow_doc["schema"] = census_doc["schema"]
    shadow_doc["what_this_is"] = ("SHADOW recensus for %s: the pinned %d rows unchanged plus %d TRUE_MISSING additions proposed by %s. Never registered, never deployed; the pinned census is untouched."
                                  % (MARKET_ID, len(census), len(additions), WORK_ORDER))
    shadow_doc["work_order"] = WORK_ORDER
    shadow_doc["captured_at"] = time.strftime("%Y-%m-%d", time.gmtime())
    shadow_doc["hotels"] = census + additions
    shadow_doc["count"] = len(shadow_doc["hotels"])
    shadow_doc["shadow"] = OrderedDict([("pinned_census_touched", False), ("pinned_count", len(census)), ("additions", len(additions)), ("deployment", "NONE")])
    issues = [str(i) for i in CENSUS.validate(shadow_doc, market_states=("OH",))]

    counts = OrderedDict(sorted(Counter(r["classification"] for r in results).items()))
    by_source = OrderedDict()
    for r in results:
        by_source.setdefault(r["source"], Counter())[r["classification"]] += 1
    tm = [r for r in results if r["classification"] == "TRUE_MISSING_IDENTITY"]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("phase", "4 -- reconcile every shadow identity"), ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("inputs", OrderedDict([("osm_candidates", len(shadow_from_osm(OSM_CANDIDATES))), ("brand_directory_pages", len([s for s in shadow if s["source"] == "brand_directory"])),
                                ("shadow_after_self_dedup", len(merged)), ("pinned_census", len(census))])),
        ("classification_counts", counts), ("by_source", OrderedDict((k, OrderedDict(sorted(v.items()))) for k, v in by_source.items())),
        ("true_missing", OrderedDict([("count", len(tm)), ("corroborated_by_first_party_directory_listing", sum(1 for r in tm if r.get("first_party_directory_listing"))), ("by_brand_family", OrderedDict(sorted(Counter(r["brand_family"] for r in tm).items()))),
                                      ("by_corridor", OrderedDict(sorted(Counter(r["corridor"] or "(no corridor)" for r in tm).items()))),
                                      ("by_source", OrderedDict(sorted(Counter(r["source"] for r in tm).items())))])),
        ("census_increase_pct", round(100.0 * len(additions) / len(census), 1)),
        ("coded_brand_directory_listings", directory_summary),
        ("shadow_census", OrderedDict([("path", os.path.relpath(os.path.join(RECENSUS_DIR, f"{MARKET_ID}.json"), _DASH)), ("count", shadow_doc["count"]), ("validation_issues", issues)])),
        ("results", results),
    ]), shadow_doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_shadow_reconciliation_004.json"))
    ap.add_argument("--no-shadow-write", action="store_true")
    args = ap.parse_args(argv)
    rep, shadow_doc = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    if not args.no_shadow_write:
        os.makedirs(RECENSUS_DIR, exist_ok=True)
        with open(os.path.join(RECENSUS_DIR, f"{MARKET_ID}.json"), "wb") as fh:
            fh.write((json.dumps(shadow_doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("inputs:", dict(rep["inputs"]))
    print("classification:", dict(rep["classification_counts"]))
    print("true missing:", json.dumps(rep["true_missing"]))
    print("shadow census:", dict(rep["shadow_census"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phases 10, 13, 20-25 and 29: the machine-readable accounting.

Reads only committed reports and staged documents (nothing fetches) and writes one accounting document with:
headline accounting, holds by class (the order's exact vocabulary), exclusions by class, corridor coverage,
brand-by-brand acquisition accounting, provider-attempt accounting (static, Wyndham, independents' pages, Places,
Firecrawl -- not used, the plan sits at its protected reserve -- and the supported browser), competitor
reconciliation, the Salt Lake City boundary audit (Provo / Orem and Utah County beyond Lehi, Ogden and Davis County
beyond Bountiful, the Heber Valley and Jordanelle, eastern Summit County, the Big and Little Cottonwood Canyon resorts,
Tooele, Logan / Cache Valley / Bear Lake, Moab, St. George / Zion / Bryce, and greater Utah or out of state), the SLC
airport evaluation, the PARK CITY accounting (Park City is its own identity and is never labelled Salt Lake City;
Deer Valley, Canyons Village and Kimball Junction overlays; condominium lodges, residences and timeshares refused or
held), the county / municipality accounting (no Murray, Midvale, Sandy, South Salt Lake or West Valley City premises
flattened into Salt Lake City), negation / parser conflicts, and the remaining unresolved root causes.

Output: launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_source_ready_accounting_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import salt_lake_city_ut_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder.salt_lake_city_ut_nonhotel_rulings_001 import exclusion_class  # noqa: E402

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", "salt-lake-city-ut", "raw_captures")
OUT = os.path.join(R, "salt_lake_city_ut_source_ready_accounting_001.json")
PARTITION = os.path.join(PKG, "markets", "staging", "salt-lake-city-ut", "launch_package", "salt_lake_city_ut_final_partition_001.json")

#: The order's hold vocabulary, and which clean-authority disposition each maps from.
HOLD_CLASSES = OrderedDict([
    ("IDENTITY", ("IDENTITY_MISMATCH_HOLD",)), ("ROUTING", ("ROUTING_HOLD",)), ("ACCESS_BLOCKED", ("ACCESS_BLOCKED",)),
    ("EVIDENCE", ("EVIDENCE_HOLD",)), ("NEGATION", ("NEGATION_HOLD",)), ("BROWSER_CAPTURE", ("BROWSER_CAPTURE_NEEDED",)),
    ("POLICY_NOT_FOUND", ()), ("SOURCE_SILENT", ("SOURCE_SILENT",)), ("MIXED_RESORT", ()), ("CONDO_HOTEL", ()),
    ("PAID", ()), ("GEOGRAPHY", ()), ("FOUNDER", ()), ("OTHER", ()),
])

#: PHOENIX Phase 23 names Kimpton, WoodSpring, Drury and the extended-stay operators as rows of their own, so they
#: are matched BEFORE the parent families (IHG, Choice) that would otherwise absorb them.
FAMILIES = [
    ("KIMPTON", r"kimpton"),
    ("WOODSPRING", r"woodspring"),
    ("DRURY", r"\bdrury\b"),
    ("EXTENDED_STAY_OPERATORS", r"intown suites|extend-a-suites|budget suites|suites of america|uptown suites|"
                                r"siegel|crossland|home towne|hometowne studios|stayapt|waterwalk|flex studios|"
                                r"felx studios|home suites|value place"),
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|studiores|city express|aloft|westin|sheraton|"
                 r"moxy|element|renaissance|delta hotels|autograph|tribute|four points|le meridien|ritz|st\. regis|w south beach|"
                 r"edition|luxury collection|design hotels|gaylord"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|double tree|tru by|tapestry|canopy|spark by|"
               r"signia|waldorf astoria|curio|lxr|motto|tempo|graduate"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|inter continental|kimpton|"
            r"hotel indigo|voco|atwell"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|super8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|"
                r"wingate|tryp"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|quality suites|sleep inn|clarion|cambria|mainstay|suburban|"
               r"econo lodge|rodeway|ascend|everhome|woodspring"),
    ("HYATT", r"hyatt|andaz|thompson|alila"), ("BEST_WESTERN", r"best western|surestay"),
    ("SONESTA", r"sonesta|americas best value|red lion"), ("EXTENDED_STAY_AMERICA", r"extended stay america"),
    ("RED_ROOF", r"red roof"), ("MOTEL6_STUDIO6", r"motel 6|studio 6"), ("RADISSON", r"radisson|country inn"),
    ("LOEWS", r"\bloews\b"), ("FOUR_SEASONS", r"four seasons"), ("ACCOR", r"sofitel|pullman|novotel|ibis|mgallery|fairmont|"
                                                                        r"\bsls\b|mondrian|delano|hyde|\bsbe\b"),
    ("NOBU", r"\bnobu\b"), ("OMNI", r"\bomni\b"),
]
#: Luxury / boutique independents (not a chain family), reported as their own rows by name vocabulary. SALT LAKE
#: CITY's own: downtown's Grand America, Little America and Kimball, and Park City / Deer Valley's luxury lodges.
#: Nothing is inherited from another market.
LUXURY_RX = re.compile(r"\b(grand america|little america|the kimball|montage|stein eriksen|goldener hirsch|pendry|"
                       r"the chateaux|washington school house|evo hotel|kimpton|canopy)\b", re.I)
RESORT_RX = re.compile(r"\bresort\b", re.I)


def L(name, default=None, base=R):
    p = os.path.join(base, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def family(name):
    n = (name or "").lower()
    for fam, rx in FAMILIES:
        if re.search(rx, n):
            return fam
    if LUXURY_RX.search(n):
        return "LUXURY_INDEPENDENT"
    if RESORT_RX.search(n):
        return "RESORT_INDEPENDENT"
    return "INDEPENDENT"


def _jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def main():
    census = json.load(open(os.path.join(PKG, "identity_census_proposed", "salt-lake-city-ut.json"), encoding="utf-8"))
    part = json.load(open(PARTITION, encoding="utf-8"))
    clean = L("salt_lake_city_ut_clean_authority_001.json", {}) or {}
    fc = L("salt_lake_city_ut_firecrawl_pass_001.json", {}) or {}
    fc2 = L("salt_lake_city_ut_firecrawl_pass_002.json", {}) or {}
    fc3 = L("salt_lake_city_ut_firecrawl_pass_003.json", {}) or {}
    bpr = L("salt_lake_city_ut_brand_page_reads_001.json", {}) or {}
    disc = L("salt_lake_city_ut_firecrawl_discovery_001.json", {}) or {}
    static = L("salt_lake_city_ut_free_static_capture_001.json", {}) or {}
    comp = L("salt_lake_city_ut_competitor_challenge_001.json", {}) or {}
    recon = L("salt_lake_city_ut_competitor_reconciliation_001.json", {}) or {}
    # SALT LAKE CITY: no Utah state, county or city lodging register is published in a form this order could read
    # (measured by the registry lane: opendata.utah.gov is not a Socrata catalogue, and the ArcGIS Hub's lodging
    # layers are OSM-derived); the lane yields 0 leads and says so.
    dbpr = L("salt_lake_city_ut_registry_lane_001.json", {}) or {}
    osm = L("salt_lake_city_ut_osm_lane_001.json", {}) or {}
    brand = L("salt_lake_city_ut_brand_inventory_001.json", {}) or {}
    roster = L("salt_lake_city_ut_destination_roster_001.json", {}) or {}
    routing = L("salt_lake_city_ut_routing_001.json", {}) or {}
    wyndham = L("salt_lake_city_ut_wyndham_lane_001.json", {}) or {}
    places = L("salt_lake_city_ut_places_route_discovery_001.json", {}) or {}
    pp = L("policy_pages_rows.json", {}, base=RAW) or {}
    closure_sites = L("closure_static_rows.json", {}, base=RAW) or {}
    browser = _jsonl(os.path.join(RAW, "browser_attempts.jsonl"))
    closure_browser = (L("browser_closure_rows.json", {}, base=RAW) or {}).get("rows", [])
    clean_by_key = {r["identity_key"]: r for r in clean.get("rows", [])}

    items = part["items"]
    n_census = census["count"]
    pf = sum(1 for i in items if i["final_state"] == "PUBLISHED_PET_FRIENDLY")
    npets = sum(1 for i in items if i["final_state"] == "VERIFIED_NO_PETS")
    unres = [i for i in items if not i["resolved"]]
    disp = Counter(i["disposition"] for i in unres)
    holds = OrderedDict((k, sum(disp.get(d, 0) for d in v)) for k, v in HOLD_CLASSES.items())
    holds["OTHER"] = sum(v for k, v in disp.items() if not any(k in ds for ds in HOLD_CLASSES.values()))

    # exact sub-causes inside ROUTING / ACCESS_BLOCKED / SOURCE_SILENT
    sub = OrderedDict()
    for i in unres:
        reason = (clean_by_key.get(i["identity_key"]) or {}).get("hold_reason") or ""
        head = reason.split(" --", 1)[0] if " --" in reason[:60] else ""
        sub.setdefault(i["disposition"], Counter())[head or reason[:70]] += 1
    sub = OrderedDict((k, OrderedDict(v.most_common())) for k, v in sorted(sub.items()))

    non = census["non_admitted"]
    excl = Counter()
    for r in non:
        if r["classification"] == "NON_LODGING":
            excl[exclusion_class(r["classification_reason"])] += 1
    ncls = Counter(r["classification"] for r in non)
    creport = L("salt_lake_city_ut_census_reconciliation_001.json", {}) or {}

    # corridors
    cor = OrderedDict()
    for slug, name, _a, klass, _m, _z, _d, _st in GEO.CORRIDORS:
        cid = "salt-lake-city-ut__" + slug
        rows = [i for i in items if i["corridor"] == cid]
        p = sum(1 for i in rows if i["final_state"] == "PUBLISHED_PET_FRIENDLY")
        n = sum(1 for i in rows if i["final_state"] == "VERIFIED_NO_PETS")
        cor[slug] = OrderedDict([("name", name), ("class", klass), ("census", len(rows)), ("pet_friendly", p),
                                 ("no_pets", n), ("unresolved", len(rows) - p - n),
                                 ("resolution_rate", round((p + n) / len(rows), 4) if rows else None),
                                 ("threshold", "a corridor page publishes with 5 or more pet-friendly profiles; "
                                               "a thinner corridor is never forced"),
                                 ("page_publishes", p >= 5)])

    # providers keyed per identity
    _final = OrderedDict()
    for r in fc.get("rows", []) + fc2.get("rows", []) + fc3.get("rows", []):
        _final[r["identity_key"]] = r
    fc_rows = list(_final.values())
    fc_by_key = Counter()
    fc_ok_by_key = set()
    for r in fc_rows:
        fc_by_key[r["identity_key"]] += 1
        if r.get("firecrawl_class") == "FIRECRAWL_PUBLICATION_GRADE":
            fc_ok_by_key.add(r["identity_key"])
    browser_fams = Counter(b["family"] for b in browser)
    act = L("salt_lake_city_ut_actionability_001.json", {}) or {}
    act_by_key = {r["identity_key"]: r["actionability"] for r in act.get("rows", [])}

    fam_tbl = OrderedDict()
    for i in items:
        fam = family(i["canonical_name"])
        t = fam_tbl.setdefault(fam, Counter())
        t["census"] += 1
        t["pet_friendly"] += i["final_state"] == "PUBLISHED_PET_FRIENDLY"
        t["no_pets"] += i["final_state"] == "VERIFIED_NO_PETS"
        t["unresolved"] += not i["resolved"]
        t["firecrawl_attempted"] += fc_by_key.get(i["identity_key"], 0) > 0
        t["firecrawl_success"] += i["identity_key"] in fc_ok_by_key
        t["access_blocked"] += i["disposition"] == "ACCESS_BLOCKED"
        t["browser_capture_needed"] += i["disposition"] == "BROWSER_CAPTURE_NEEDED"
        t["actionable_remaining"] += act_by_key.get(i["identity_key"]) == "ACTIONABLE_NOW"
    # the attended-browser lane this order actually exercised (salt_lake_city_ut_browser_lane_001),
    # counted per brand family so the brand table reports reads and denials, not a placeholder zero.
    _blp = os.path.join(R, "salt_lake_city_ut_browser_lane_001.json")
    _bl = json.load(open(_blp, encoding="utf-8")) if os.path.exists(_blp) else {}
    _browser_attempts, _browser_reads, _browser_denied = Counter(), Counter(), Counter()
    for _r in _bl.get("rows", []):
        _fam = _r.get("family") or ""
        # the browser lane names two families differently from this table
        _fam = {"ESA": "EXTENDED_STAY_AMERICA", "MOTEL6": "MOTEL6_STUDIO6"}.get(_fam, _fam)
        _browser_attempts[_fam] += 1
        if _r.get("outcome") == "READ":
            _browser_reads[_fam] += 1
        elif _r.get("outcome") in ("CHALLENGE_DENIED_AKAMAI_ACCESS_DENIED", "CHALLENGE_DENIED_DATADOME_CAPTCHA"):
            _browser_denied[_fam] += 1
    brand_tbl = OrderedDict()
    for fam in sorted(fam_tbl):
        t = fam_tbl[fam]
        brand_tbl[fam] = OrderedDict([(k, int(t[k])) for k in (
            "census", "pet_friendly", "no_pets", "unresolved", "firecrawl_attempted", "firecrawl_success",
            "access_blocked", "browser_capture_needed", "actionable_remaining")])
        brand_tbl[fam]["browser_attempted"] = _browser_attempts.get(fam, 0) or browser_fams.get(fam, 0)
        brand_tbl[fam]["browser_read"] = _browser_reads.get(fam, 0)
        brand_tbl[fam]["browser_challenge_denied"] = _browser_denied.get(fam, 0)

    fc_class = Counter(r.get("firecrawl_class") for r in fc_rows)
    fc_cohort = Counter(r.get("cohort") for r in fc_rows)
    credits = fc.get("credits", {}) or {}

    # PHASE 24 -- THE SALT LAKE CITY BOUNDARY AUDIT. Every OUTSIDE graph node is counted by the refused place its OWN
    # postal code or municipality names; every brand card refused by its own address is counted too, so a neighbour
    # that only a brand card reached is SEEN. The refused places and their codes are the geography module's OWN lists
    # (GEO.OUTSIDE, GEO.OUTSIDE_PREFIXES, GEO.MUNICIPALITY_REFUSALS), never retyped here.
    refused_places = OrderedDict()
    for label, _st, zips_, _note in GEO.OUTSIDE:
        head = label.split(" --")[0]
        words = [w.strip().lower() for w in head.replace("(", "/").replace(")", "").split("/") if w.strip()]
        prefixes = tuple(p for p, plabel, _s in GEO.OUTSIDE_PREFIXES if any(w in plabel.lower() for w in words))
        key = re.sub(r"[^A-Z0-9]+", "_", head.upper()).strip("_")
        refused_places[key] = (r"|".join(re.escape(w) for w in words), tuple(zips_), prefixes)

    def _place_of(city, postal, reason):
        # PHOENIX (kept): the place words are matched against the row's own CITY only. A classification reason
        # names counties and pages and would place a row by a word in its reason.
        txt = (city or "").lower()
        z = (postal or "")[:5]
        for label, (rx, codes, prefixes) in refused_places.items():
            if (z and (z in codes or (prefixes and z.startswith(prefixes)))) or (
                    rx and re.search(r"\b(?:%s)\b" % rx, txt)):
                return label
        if z and GEO.state_for_postal(z) != "UT":
            return "GREATER_UTAH_AND_OUT_OF_STATE"
        return ""

    discovered = Counter()
    for r in non:
        if r["classification"] == "OUTSIDE_MARKET":
            lab = _place_of(r.get("city"), r.get("postal_code"), r.get("classification_reason"))
            discovered[lab or "UNPLACED_OUTSIDE"] += 1
    for c in brand.get("brand_cards_refused_by_their_own_address", []) or []:
        lab = _place_of(c.get("city"), c.get("postal_code"), "")
        if lab:
            discovered[lab + "__BRAND_CARD_REFUSED"] += 1
    admitted = Counter()
    for h in census["hotels"]:
        lab = _place_of(h.get("city"), h.get("postal_code"), "")
        if lab:
            admitted[lab] += 1
    _admitted_outside = sum(1 for h in census["hotels"]
                            if GEO.classify_postal(h.get("postal_code"), h.get("city"))[0] == "OUTSIDE")

    _muni = creport.get("municipality_publication") or {}
    _pc_codes = ("84060", "84068", "84098")
    pc_rows = [h for h in census["hotels"] if (h.get("postal_code") or "")[:5] in _pc_codes]
    pc_items = [i for i in items if (i.get("corridor") or "").split("__")[-1] in ("park-city", "canyons-kimball-junction")]
    pc_non = [r for r in non if (r.get("postal_code") or "")[:5] in _pc_codes]
    canyon = [r for r in non if re.search(r"cottonwood-canyons|canyon resort|CANYON_RESORT",
                                          r.get("classification_reason") or "", re.I)]
    boundary = OrderedDict([
        ("method", "Every OUTSIDE graph node counted by the refused place its OWN postal code (or prefix) or "
                   "municipality names, plus every brand city-page card whose own address is a refused neighbour. "
                   "Admission is by the corridor registry over the property's own postal code and nothing else."),
        ("refused_places", OrderedDict((k, OrderedDict([
            ("discovered_as_graph_nodes", discovered.get(k, 0)),
            ("discovered_as_brand_cards", discovered.get(k + "__BRAND_CARD_REFUSED", 0)),
            ("admitted", admitted.get(k, 0))])) for k in list(refused_places) + ["GREATER_UTAH_AND_OUT_OF_STATE"])),
        ("outside_nodes_not_placed_by_name_or_code", discovered.get("UNPLACED_OUTSIDE", 0)),
        ("cottonwood_canyon_resorts", OrderedDict([
            ("rule", "Snowbird and Alta (Little Cottonwood Canyon, 84092) and Solitude and Brighton (Big Cottonwood "
                     "Canyon, 84121) share a postal code with admitted valley suburbs; a canyon resort premises is "
                     "refused by its own name or street (FUTURE_STANDALONE cottonwood-canyons-ut), never admitted by "
                     "the shared code."),
            ("municipality_refusals", [list(x[:2]) for x in GEO.MUNICIPALITY_REFUSALS]),
            ("refused_graph_nodes", sorted("%s (%s)" % (r.get("canonical_name"), r.get("postal_code")) for r in canyon)),
            ("admitted_canyon_resort_rows", sorted(h.get("canonical_name") for h in census["hotels"]
                                                   if GEO.canyon_resort_reason(h.get("canonical_name"),
                                                                               h.get("street") or "")))])),
        ("slc_airport", OrderedDict([
            ("evaluation", GEO.SLC_AIRPORT_EVALUATION),
            ("admitted_rows_slc_airport_west_side", sum(1 for h in census["hotels"]
                                                        if (h.get("corridor") or "").endswith("__slc-airport-west-side"))),
            ("admitted_rows_named_airport_outside_the_airport_corridor", sorted(
                "%s (%s, %s)" % (h.get("canonical_name"), h.get("postal_code"), (h.get("corridor") or "").split("__")[-1])
                for h in census["hotels"]
                if re.search(r"airport", h.get("canonical_name") or "", re.I)
                and not (h.get("corridor") or "").endswith("__slc-airport-west-side"))),
        ])),
        ("counties_and_municipalities_never_flattened", OrderedDict([
            ("admitted_rows_by_county", OrderedDict(sorted(Counter(
                (GEO.POSTAL_COUNTY.get((h.get("postal_code") or "")[:5]) or ("UNKNOWN",))[0]
                for h in census["hotels"]).items()))),
            ("admitted_rows_by_published_municipality", OrderedDict(sorted(Counter(
                (h.get("city") or "").strip() for h in census["hotels"]).items()))),
            ("SALT_LAKE_CITY_WRONG_CITY_IDENTITIES", _muni.get("SALT_LAKE_CITY_WRONG_CITY_IDENTITIES")),
            ("rows_relabelled_to_their_own_municipality", _muni.get("rows_relabelled_count")),
            ("relabelled_rows", _muni.get("rows_relabelled")),
            ("admitted_rows_not_utah", sum(1 for h in census["hotels"]
                                           if GEO.state_for_postal(h.get("postal_code")) != "UT")),
            ("rows_held_for_a_municipality_or_state_or_postal_conflict", sorted(
                "%s (%s)" % (r.get("canonical_name"), r.get("postal_code")) for r in non
                if re.search(r"MUNICIPALITY_|STATE_POSTAL_CONFLICT|POSTAL_CONFLICT", r.get("classification_reason") or ""))),
        ])),
        ("neighbourhood_overlays", OrderedDict(sorted(Counter(
            GEO.route_overlay((h.get("corridor") or "").split("__")[-1], h.get("street"), h.get("latitude"),
                              h.get("longitude"), h.get("postal_code")) or "(corridor name)"
            for h in census["hotels"]).items()))),
        ("outside_nodes_under_market_prefixes", OrderedDict(sorted(Counter(
            (r.get("postal_code") or "")[:5] for r in non if r["classification"] == "OUTSIDE_MARKET"
            and (r.get("postal_code") or "")[:3] in GEO.VALLEY_PREFIXES).items()))),
        ("salt_lake_city_ruling", GEO.SALT_LAKE_CITY_RULING),
        ("rows_admitted_from_a_refused_postal_code", _admitted_outside),
        ("zero_admitted_outside", _admitted_outside == 0),
        ("county_boundary_rules", GEO.COUNTY_BOUNDARY_RULES),
        ("existing_live_markets_named", list(GEO.EXISTING_LIVE_MARKETS)),
        ("future_standalone_markets", list(GEO.FUTURE_MARKETS)),
    ])
    park_city = OrderedDict([
        ("rule", "Park City (84060 / 84068) and the Snyderville Basin (84098, mailing name Park City) are PARK CITY "
                 "identities: their own corridors, their own municipality, never labelled Salt Lake City."),
        ("evaluation", GEO.PARK_CITY_EVALUATION),
        ("condo_hotel_rule", GEO.CONDO_HOTEL_RULE),
        ("admitted_rows", len(pc_rows)),
        ("pet_friendly", sum(1 for i in pc_items if i["final_state"] == "PUBLISHED_PET_FRIENDLY")),
        ("verified_no_pets", sum(1 for i in pc_items if i["final_state"] == "VERIFIED_NO_PETS")),
        ("unresolved", sum(1 for i in pc_items if not i["resolved"])),
        ("by_corridor", OrderedDict(sorted(Counter((i.get("corridor") or "").split("__")[-1] for i in pc_items).items()))),
        ("published_municipality", OrderedDict(sorted(Counter((h.get("city") or "") for h in pc_rows).items()))),
        ("PARK_CITY_PROFILES_LABELED_SALT_LAKE_CITY", sum(
            1 for h in pc_rows if (h.get("city") or "").strip().lower() != "park city")),
        ("PARK_CITY_PROFILES_LABELED_SALT_LAKE_CITY_census_check", _muni.get("PARK_CITY_PROFILES_LABELED_SALT_LAKE_CITY")),
        ("deer_valley_east_village_note",
         "Grand Hyatt Deer Valley and Canopy by Hilton Deer Valley lie at Jordanelle in Wasatch County; both own pages "
         "state Park City, UT 84060, so both are Park City rows by the postal-code rule. The census county field is "
         "derived from the postal code and reads Summit for them; no county is published."),
        ("overlays", OrderedDict(sorted(Counter(
            GEO.route_overlay((h.get("corridor") or "").split("__")[-1], h.get("street"), h.get("latitude"),
                              h.get("longitude"), h.get("postal_code")) or "(corridor name)" for h in pc_rows).items()))),
        ("non_admitted_park_city_rows_by_class", OrderedDict(sorted(Counter(
            (exclusion_class(r.get("classification_reason")) if r["classification"] == "NON_LODGING"
             else r["classification"]) for r in pc_non).items()))),
        ("condo_lodges_residences_and_timeshares_refused_or_held", sorted(
            "%s -- %s" % (r.get("canonical_name"), (r.get("classification_reason") or "")[:140]) for r in pc_non
            if r["classification"] in ("NON_LODGING", "IDENTITY_REVIEW_REQUIRED"))),
        ("canyon_resorts_refused", boundary["cottonwood_canyon_resorts"]["refused_graph_nodes"]),
    ])

    root = OrderedDict([
        ("ROUTING_HOLD", "no first-party route: no brand inventory row, bureau link or map website joined the "
                         "building, Google Places route discovery (run inside the renewed free monthly allowance) "
                         "found no first-party website for it, or the route the census carried is retired, expired "
                         "or a third-party page."),
        ("ACCESS_BLOCKED", "every free / authorized lane attempted (static plain client, Firecrawl where the router "
                           "made the row eligible, the attended browser) was refused or walled."),
        ("SOURCE_SILENT", "the property's own page or site served, bound to the identity, and stated no operative "
                          "pet policy on its home or policy / FAQ pages."),
        ("EVIDENCE_HOLD", "a conditional, chip-only or fee/weight/count-only statement, or a shared-reader "
                          "disagreement; held, never published."),
        ("IDENTITY_MISMATCH_HOLD", "dual-brand buildings awaiting a reviewed shared resolution, or a page that never "
                                   "confirmed this census row's premises."),
    ])

    doc = OrderedDict([
        ("schema", "ptf-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", "salt-lake-city-ut"),
        ("headline", OrderedDict([
            ("total_raw_observations", creport.get("observations_total")),
            ("raw_observations_by_lane", creport.get("lane_yields")),
            ("public_lodging_register_leads", dbpr.get("lead_rows", 0)),
            ("osm_lodging_elements", osm.get("element_count")),
            ("brand_inventory_leads", brand.get("lead_count")),
            # this market's roster names the count `row_count`; the parent's named it `listing_count_total`, and
            # reading only the parent's name published a null into the accounting artifact.
            ("destination_roster_listings", roster.get("row_count", roster.get("listing_count_total"))),
            ("destination_roster_rows_in_admitted_codes", roster.get("rows_in_admitted_postal_codes")),
            ("competitor_leads_normalized", comp.get("normalized_unique")),
            ("graph_nodes", n_census + len(non)),
            ("proposed_census", n_census), ("valid_pet_friendly", pf), ("valid_verified_no_pets", npets),
            ("resolved", pf + npets), ("unresolved", n_census - pf - npets),
            ("resolution_rate", round((pf + npets) / n_census, 4) if n_census else None),
        ])),
        ("holds_by_class", holds),
        ("holds_exact_sub_causes", sub),
        ("exclusions", OrderedDict([
            ("vacation_rental", excl.get("VACATION_RENTAL", 0)), ("timeshare", excl.get("TIMESHARE", 0)),
            ("resort_residence", excl.get("RESORT_RESIDENCE", 0)), ("non_hotel", excl.get("NON_HOTEL", 0)),
            ("closed", len(clean.get("closed_held") or [])),
            ("preopening", len(clean.get("preopening_held") or [])),
            ("converted_to_non_hotel", sum(1 for r in non if r["classification"] == "NON_LODGING"
                                           and "CONVERTED" in (r.get("classification_reason") or ""))),
            ("military_restricted", sum(1 for r in non if "MILITARY_RESTRICTED" in (r.get("classification_reason") or ""))),
            ("outside", ncls.get("OUTSIDE_MARKET", 0)),
            ("duplicate_listing", ncls.get("DUPLICATE_LISTING", 0)),
            ("name_only_unresolved_graph_residue", ncls.get("NAME_ONLY_UNRESOLVED", 0)),
            ("identity_review_required_graph_residue", ncls.get("IDENTITY_REVIEW_REQUIRED", 0)),
            ("same_campus_distinct_entity", ncls.get("SAME_CAMPUS_DISTINCT_ENTITY", 0)),
            ("register_short_term_rental_and_other_rows_never_leads",
             dbpr.get("short_term_rental_and_other_rows_counted_not_leads", 0)),
            ("closed_note", "A row is CLOSED only on the property's own first-party closure statement, held and "
                            "never published; lapsed routes (a parked or retired domain, a brand redirect to its own "
                            "search, a brand directory that no longer lists the building) are ROUTING / ACCESS holds, "
                            "never a closure claim."),
            ("closed_rows", clean.get("closed_held") or []),
            ("preopening_rows", clean.get("preopening_held") or []),
        ])),
        ("corridor_coverage", cor),
        ("uncorridored_rows", sum(1 for i in items if not i.get("corridor"))),
        ("corridor_count", len(cor)),
        ("corridors_publishing", [k for k, v in cor.items() if v["page_publishes"]]),
        ("brand_by_brand", brand_tbl),
        ("providers", OrderedDict([
            ("static_capture", OrderedDict([("targets", len(static.get("rows", []))),
                                            ("free_http_requests", static.get("free_http_requests_this_run", 0)),
                                            ("outcomes", OrderedDict(sorted(Counter(str(r.get("outcome")) for r in static.get("rows", [])).items())))])),
            ("wyndham_property_service", OrderedDict([("selected", wyndham.get("routes_selected")), ("read", wyndham.get("read")),
                                                      ("retired", wyndham.get("retired"))])),
            ("independents_policy_pages", OrderedDict([("targets", len(pp.get("rows", []))),
                                                       ("bound", sum(1 for r in pp.get("rows", []) if r.get("bound"))),
                                                       ("free_http_requests", pp.get("free_http_requests"))])),
            ("places_route_discovery", OrderedDict([("requests", places.get("requests_made")),
                                                    ("route_discovery_bound", places.get("route_discovery_bound")),
                                                    ("with_website", places.get("route_discovery_bound_with_website")),
                                                    ("gap_verdicts", places.get("gap_verdicts")),
                                                    ("enterprise_requests", places.get("enterprise_requests_made")),
                                                    ("pro_requests", places.get("pro_requests_made")),
                                                    ("field_mask_route_discovery", places.get("field_mask_route_discovery")),
                                                    ("field_mask_gap_verification", places.get("field_mask_gap_verification")),
                                                    ("route_discovery_run", places.get("route_discovery_run")),
                                                    ("cost_basis", places.get("route_discovery_capacity_basis"))])),
            ("places_discovered_sites", OrderedDict([("targets", len(closure_sites.get("rows", []))),
                                                     ("bound", sum(1 for r in closure_sites.get("rows", []) if r.get("bound"))),
                                                     ("free_http_requests", closure_sites.get("free_http_requests"))])),
            ("firecrawl", OrderedDict([
                ("eligible_planned", fc.get("planned_rows", 0)),
                ("attempted", fc.get("attempted_rows", 0) + fc2.get("attempted_rows", 0)
                              + fc3.get("attempted_rows", 0) + bpr.get("attempted", 0) + len(disc.get("pages") or [])),
                ("property_page_attempts", fc.get("attempted_rows", 0) + fc2.get("attempted_rows", 0)
                                           + fc3.get("attempted_rows", 0) + bpr.get("attempted", 0)),
                ("first_pass_attempted", fc.get("attempted_rows", 0)),
                ("retry_pass_attempted", fc2.get("attempted_rows", 0)),
                ("probe2_pass_attempted", fc3.get("attempted_rows", 0)),
                ("route_discovery_pages", len(disc.get("pages") or [])),
                ("route_discovery_routes", disc.get("route_count", 0)),
                ("brand_page_reads", OrderedDict([("attempted", bpr.get("attempted", 0)),
                                                  ("answered", bpr.get("answered", 0)),
                                                  ("with_own_address", bpr.get("with_own_address", 0)),
                                                  ("by_family", bpr.get("by_family", {}))])),
                ("not_used_why", "Firecrawl was not used: the plan's balance (60 credits) equals its protected "
                                 "reserve, and this order may not consume below it nor buy new capacity. Every route a "
                                 "Firecrawl pass would have bought was read instead by the attended browser, the "
                                 "Wyndham property service or the free static lanes (pay once per page ever)."),
                ("distinct_identities_attempted", len(fc_rows)),
                ("by_cohort", OrderedDict(sorted((k, v) for k, v in fc_cohort.items() if k))),
                ("publication_grade", fc_class.get("FIRECRAWL_PUBLICATION_GRADE", 0)),
                ("policy_found", sum(1 for r in fc_rows if r.get("firecrawl_class") == "FIRECRAWL_PUBLICATION_GRADE"
                                     and r.get("pets_allowed") is not None)),
                ("failed", sum(v for k, v in fc_class.items() if k and k != "FIRECRAWL_PUBLICATION_GRADE")),
                ("class_counts", OrderedDict(sorted((k, v) for k, v in fc_class.items() if k))),
                ("credits", OrderedDict([("first_pass", credits), ("retry_pass", fc2.get("credits", {})),
                                         ("probe2_pass", fc3.get("credits", {})),
                                         ("route_discovery", disc.get("credits", {})),
                                         ("brand_page_reads", bpr.get("credits", {}))])),
            ])),
            ("supported_browser", OrderedDict([
                ("attended_browser_lane", OrderedDict([
                    ("attempts", _bl.get("attempts")), ("reads", _bl.get("reads")),
                    ("challenge_denied", _bl.get("challenge_denied")), ("unbound", _bl.get("unbound")),
                    ("attempts_by_family", OrderedDict(sorted(_browser_attempts.items()))),
                    ("reads_by_family", OrderedDict(sorted(_browser_reads.items()))),
                    ("akamai_bypassed", False), ("js_exfiltration", False), ("relay", False), ("captcha_solved", False),
                ])),
                ("recorded_attempts", len(closure_browser)),
                ("outcomes", OrderedDict(sorted(Counter(r["outcome"] for r in closure_browser).items()))),
                ("reads", sum(1 for r in closure_browser if r["outcome"] == "READ")),
                ("bindings", OrderedDict(sorted(Counter(
                    (r.get("binding") or "").split(" (")[0][:60] for r in closure_browser if r.get("binding")).items()))),
                ("by_family", OrderedDict(sorted(Counter(
                    r["family"] for r in closure_browser if r["outcome"] == "READ").items()))),
            ])),
            ("other_paid_providers", OrderedDict([("bright_data", 0), ("other", 0)])),
            ("routing_by_state", (routing.get("counts") or {}).get("by_routing_state", {})),
            ("usd_spent", 0.0), ("new_paid_spend", 0.0), ("new_provider_authorization", "NONE"),
        ])),
        ("competitor_reconciliation", OrderedDict([
            ("competitor", "BringFido"), ("cities_challenged", comp.get("cities_challenged", 0)),
            ("competitor_raw_discovery", recon.get("competitor_raw_discovery")),
            ("normalized_unique", recon.get("normalized_unique")),
            ("matched_to_census", recon.get("matched_to_census")),
            ("matched_distinct_identities", recon.get("matched_distinct_identities")),
            ("true_missing_qualifying_candidates", recon.get("true_missing_qualifying_candidates")),
            ("true_missing_verified_by_places", places.get("gap_verdicts")),
            ("true_missing_names", [r["bringfido_name"] for r in recon.get("rows", [])
                                    if r.get("classification") == "TRUE_MISSING"]),
            ("true_missing_disposition",
             "every BringFido lead no census node carried was worked through an authorized identity lane: Google "
             "Places gap verification (existing free allowance) placed each at its own postal code or refused it; a "
             "verified missing hotel became a census identity through the Places lane and its own page decided its "
             "policy. A competitor name never admits an identity and its pet claims are never read."),
            ("excluded_stale_outside", recon.get("excluded_stale_outside")),
            ("review", recon.get("review")),
            ("matched_but_policy_unresolved", recon.get("matched_but_policy_unresolved")),
            ("counts", recon.get("counts")),
        ])),
        ("county_and_border_boundary", boundary),
        ("fees", OrderedDict((k, v) for k, v in (L("salt_lake_city_ut_fee_withholding_001.json", {}) or {}).items()
                             if k not in ("tiered", "unsafe"))),
        ("negation_and_parser_conflicts", clean.get("negation_conflicts_caught", [])),
        ("remaining_unresolved_root_causes", root),
    ])
    doc["park_city_accounting"] = park_city
    # SALT LAKE CITY: the order names a MUNICIPALITY accounting of its own -- the county / municipality publication and
    # the airport evaluation, restated from the boundary section (never recomputed).
    doc["municipality_accounting"] = OrderedDict([
        ("counties_and_municipalities_never_flattened", boundary["counties_and_municipalities_never_flattened"]),
        ("slc_airport", boundary["slc_airport"]),
        ("rule", (creport.get("municipality_publication") or {}).get("rule")),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    # The order names its machine-readable accountings. Each is written as its own document from the
    # SAME sections of this one (never recomputed, so the files cannot disagree); the actionability and competitor
    # reconciliation documents are their own modules' outputs.
    for name, keys in (("source", ("headline", "holds_by_class", "holds_exact_sub_causes", "exclusions",
                                   "remaining_unresolved_root_causes")),
                       ("provider", ("providers",)), ("brand", ("brand_by_brand",)),
                       ("corridor", ("corridor_coverage", "uncorridored_rows", "corridor_count",
                                     "corridors_publishing")),
                       ("boundary", ("county_and_border_boundary",)),
                       ("park_city", ("park_city_accounting",)),
                       ("competitor_reconciliation", ("competitor_reconciliation",)),
                       ("municipality", ("municipality_accounting",))):
        part = OrderedDict([("schema", "ptf-%s-accounting/1.0" % name), ("work_order", WORK_ORDER),
                            ("market_id", "salt-lake-city-ut"),
                            ("derived_from", os.path.relpath(OUT, _DASH).replace("\\", "/"))])
        part.update((k, doc[k]) for k in keys)
        with open(os.path.join(R, "salt_lake_city_ut_%s_accounting_001.json" % name), "w", encoding="utf-8",
                  newline="\n") as fh:
            json.dump(part, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    print("headline:", dict(doc["headline"]))
    print("holds:", dict(doc["holds_by_class"]))
    print("corridors publishing:", doc["corridors_publishing"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

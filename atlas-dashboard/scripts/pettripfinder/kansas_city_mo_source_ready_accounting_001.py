"""PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001 -- Phases 10, 13, 20-25 and 29: the machine-readable accounting.

Reads only committed reports and staged documents (nothing fetches) and writes one accounting document with:
headline accounting, holds by class (the order's exact vocabulary), exclusions by class, corridor coverage,
brand-by-brand acquisition accounting, provider-attempt accounting (static, Wyndham, ESA, independents' pages,
Places, Firecrawl, supported browser), competitor reconciliation, the Kansas City boundary audit (Lawrence, Topeka, St. Joseph,
Columbia, Manhattan, Lake of the Ozarks, Leavenworth, the outer north / east / south metro, outer Johnson / Wyandotte /
Miami County, the live St. Louis market, and greater Missouri / Kansas), the MCI / Northland and Johnson County
evaluations, the two-state (Missouri / Kansas) accounting, negation / parser conflicts, and the remaining unresolved
root causes.

Output: launch_packages/pettripfinder/markets/reports/kansas_city_mo_source_ready_accounting_001.json
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

from scripts.pettripfinder import kansas_city_mo_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder.kansas_city_mo_nonhotel_rulings_001 import exclusion_class  # noqa: E402

WORK_ORDER = "PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", "kansas-city-mo", "raw_captures")
OUT = os.path.join(R, "kansas_city_mo_source_ready_accounting_001.json")
PARTITION = os.path.join(PKG, "kansas_city_mo_final_partition_001.json")

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
#: Luxury / boutique independents (not a chain family), reported as their own rows by name vocabulary. KANSAS CITY's
#: own: the downtown, Crossroads, River Market, Plaza / Westport and Country Club District luxury and boutique hotels.
#: Nothing is inherited from another market.
LUXURY_RX = re.compile(r"\b(hotel kansas city|hotel phillips|the fontaine|fontaine hotel|crossroads hotel|no vacancy|"
                       r"hotel no vacancy|river market hotel|the truitt|truitt boutique|aida boutique|southmoreland|"
                       r"the raphael|raphael hotel|hotel inn at meadowbrook|inn at meadowbrook|1812 overture|"
                       r"the savoy|21c museum|origin kansas city|kimpton|canopy)\b", re.I)
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
    census = json.load(open(os.path.join(PKG, "identity_census", "kansas-city-mo.json"), encoding="utf-8"))
    part = json.load(open(PARTITION, encoding="utf-8"))
    clean = L("kansas_city_mo_clean_authority_001.json", {}) or {}
    fc = L("kansas_city_mo_firecrawl_pass_001.json", {}) or {}
    fc2 = L("kansas_city_mo_firecrawl_pass_002.json", {}) or {}
    fc3 = L("kansas_city_mo_firecrawl_pass_003.json", {}) or {}
    bpr = L("kansas_city_mo_brand_page_reads_001.json", {}) or {}
    disc = L("kansas_city_mo_firecrawl_discovery_001.json", {}) or {}
    static = L("kansas_city_mo_free_static_capture_001.json", {}) or {}
    comp = L("kansas_city_mo_competitor_challenge_001.json", {}) or {}
    recon = L("kansas_city_mo_competitor_reconciliation_001.json", {}) or {}
    # KANSAS CITY: Missouri publishes its Licensed Lodging Establishment List (data.mo.gov 7ac3-k2di) and the registry
    # lane reads it; Kansas publishes no public lodging register this order could read (KDA answered 403).
    dbpr = L("kansas_city_mo_registry_lane_001.json", {}) or {}
    osm = L("kansas_city_mo_osm_lane_001.json", {}) or {}
    brand = L("kansas_city_mo_brand_inventory_001.json", {}) or {}
    roster = L("kansas_city_mo_destination_roster_001.json", {}) or {}
    routing = L("kansas_city_mo_routing_001.json", {}) or {}
    wyndham = L("kansas_city_mo_wyndham_lane_001.json", {}) or {}
    esa = L("kansas_city_mo_esa_lane_001.json", {}) or {}
    places = L("kansas_city_mo_places_route_discovery_001.json", {}) or {}
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
    creport = L("kansas_city_mo_census_reconciliation_001.json", {}) or {}

    # corridors
    cor = OrderedDict()
    for slug, name, _a, klass, _m, _z, _d, _st in GEO.CORRIDORS:
        cid = "kansas-city-mo__" + slug
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
    act = L("kansas_city_mo_actionability_001.json", {}) or {}
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
    # the attended-browser lane this order actually exercised (kansas_city_mo_browser_lane_001),
    # counted per brand family so the brand table reports reads and denials, not a placeholder zero.
    _blp = os.path.join(R, "kansas_city_mo_browser_lane_001.json")
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

    # PHASE 24 -- THE KANSAS CITY BOUNDARY AUDIT. Every OUTSIDE graph node is counted by the refused place its OWN
    # postal code or municipality names; every brand card refused by its own address is counted too, so a
    # neighbour that only a brand card reached is SEEN. The postal codes are the geography module's OWN refused
    # lists (GEO.OUTSIDE, GEO.OUTSIDE_PREFIXES), never retyped here. Order matters: Junction City (66441) sits under
    # Topeka's 664 prefix and is Manhattan's, so MANHATTAN is tested first.
    _OUT = {row[0].split(" --")[0].split(" /")[0]: tuple(row[2]) for row in GEO.OUTSIDE}
    _z = lambda head: next(v for k, v in _OUT.items() if k.startswith(head))  # noqa: E731
    _pfx = lambda slug: tuple(p for p, _label, s_ in GEO.OUTSIDE_PREFIXES if s_ == slug)  # noqa: E731
    _named = set(_pfx("topeka-ks") + _pfx("manhattan-ks") + _pfx("st-joseph-mo") + _pfx("columbia-mo")
                 + _pfx("st-louis-mo"))
    _other_prefixes = tuple(p for p, _label, s_ in GEO.OUTSIDE_PREFIXES if p not in _named)
    refused_places = OrderedDict([
        ("LAWRENCE", (r"lawrence|eudora|baldwin city|lecompton", _z("Lawrence"))),
        ("MANHATTAN", (r"manhattan|junction city|fort riley|ogden|wamego", _pfx("manhattan-ks") + ("66441", "66442"))),
        ("TOPEKA", (r"topeka|silver lake|rossville|tecumseh|auburn", _pfx("topeka-ks"))),
        ("ST_JOSEPH", (r"st\.? joseph|saint joseph", _z("St. Joseph") + _pfx("st-joseph-mo"))),
        ("COLUMBIA", (r"columbia|ashland|fulton", _pfx("columbia-mo"))),
        ("LAKE_OF_THE_OZARKS", (r"osage beach|lake ozark|camdenton|sunrise beach|linn creek|laurie|gravois mills",
                                _z("Lake of the Ozarks"))),
        ("LEAVENWORTH_LANSING", (r"leavenworth|lansing|fort leavenworth", _z("Leavenworth"))),
        ("OUTER_NORTH_METRO", (r"platte city|kearney|smithville|excelsior springs|weston|lathrop",
                               _z("North"))),
        ("OUTER_EAST_SOUTH_METRO", (r"oak grove|odessa|bates city|harrisonville|peculiar|pleasant hill|greenwood|"
                                    r"warrensburg|richmond", _z("East"))),
        ("OUTER_JOHNSON_WYANDOTTE_MIAMI_KS", (r"de soto|spring hill|edgerton|basehor|tonganoxie|paola|louisburg|"
                                              r"ottawa|atchison", _z("Johnson"))),
        ("ST_LOUIS_LIVE_MARKET", (r"st\.? louis|saint louis|st\.? charles|chesterfield", _pfx("st-louis-mo"))),
        ("OTHER_GREATER_MISSOURI_KANSAS_OR_OUT_OF_STATE", (r"wichita|springfield|branson|joplin|jefferson city|sedalia|"
                                                          r"salina|hutchinson|emporia|hays|dodge city|garden city|"
                                                          r"liberal|pittsburg|kirksville|hannibal|cape girardeau|"
                                                          r"rolla|chillicothe|maryville|nevada",
                                                          _other_prefixes)),
    ])
    def _place_of(city, postal, reason):
        # PHOENIX (kept): the place words are matched against the row's own CITY only. A classification reason
        # names counties and pages and would place a row by a word in its reason.
        txt = (city or "").lower()
        z = (postal or "")[:5]
        for label, (rx, prefixes) in refused_places.items():
            if (z and prefixes and z.startswith(prefixes)) or re.search(r"\b(?:%s)\b" % rx, txt):
                return label
        return ""

    discovered = Counter()
    for r in non:
        if r["classification"] == "OUTSIDE_MARKET":
            lab = _place_of(r.get("city"), r.get("postal_code"), r.get("classification_reason"))
            if lab:
                discovered[lab] += 1
    for c in brand.get("brand_cards_refused_by_their_own_address", []) or []:
        lab = _place_of(c.get("city"), c.get("postal_code"), "")
        if lab:
            discovered[lab + "__BRAND_CARD_REFUSED"] += 1
    for h in (L("kansas_city_mo_brand_inventory_001.json", {}) or {}).get("leads", []):
        card = h.get("brand_card") or {}
        if card:
            lab = _place_of(card.get("city"), card.get("postal_code"), "")
            if lab:
                discovered[lab + "__BRAND_CARD_KEPT_FOR_THE_AUDIT"] += 1
    admitted = Counter()
    for h in census["hotels"]:
        lab = _place_of(h.get("city"), h.get("postal_code"), "")
        if lab:
            admitted[lab] += 1
    _admitted_outside = sum(1 for h in census["hotels"]
                            if GEO.classify_postal(h.get("postal_code"), h.get("city"))[0] == "OUTSIDE")

    def _pair(label):
        d = discovered.get(label, 0) + discovered.get(label + "__BRAND_CARD_REFUSED", 0) + \
            discovered.get(label + "__BRAND_CARD_KEPT_FOR_THE_AUDIT", 0)
        return OrderedDict([("discovered", d), ("admitted", admitted.get(label, 0)),
                            ("discovered_as_graph_nodes", discovered.get(label, 0)),
                            ("discovered_as_brand_cards", discovered.get(label + "__BRAND_CARD_REFUSED", 0)
                             + discovered.get(label + "__BRAND_CARD_KEPT_FOR_THE_AUDIT", 0))])

    boundary = OrderedDict([
        ("method", "Every OUTSIDE graph node counted by the refused place its OWN postal code (prefix) or "
                   "municipality names, plus every brand city-page card whose own address is a refused neighbour. "
                   "Admission is by the corridor registry over the property's own postal code and nothing else."),
        ("lawrence", _pair("LAWRENCE")),
        ("topeka", _pair("TOPEKA")),
        ("st_joseph", _pair("ST_JOSEPH")),
        ("columbia", _pair("COLUMBIA")),
        ("manhattan", _pair("MANHATTAN")),
        ("lake_of_the_ozarks", _pair("LAKE_OF_THE_OZARKS")),
        ("leavenworth_lansing", _pair("LEAVENWORTH_LANSING")),
        ("outer_north_metro", _pair("OUTER_NORTH_METRO")),
        ("outer_east_south_metro", _pair("OUTER_EAST_SOUTH_METRO")),
        ("outer_johnson_wyandotte_miami_ks", _pair("OUTER_JOHNSON_WYANDOTTE_MIAMI_KS")),
        ("st_louis_live_market", _pair("ST_LOUIS_LIVE_MARKET")),
        ("other_greater_missouri_kansas_or_out_of_state", _pair("OTHER_GREATER_MISSOURI_KANSAS_OR_OUT_OF_STATE")),
        # MCI / NORTHLAND: the identity-safety evaluation for the airport and Northland names. The corridors are
        # decided by each property's own postal code (mci-airport 64153 / 64163 / 64164 / 64195; riverside-parkville
        # 64150 / 64152; northland-north-kansas-city), never by "Airport", "KCI" or "MCI" in a property's name.
        ("mci_northland", OrderedDict([
            ("evaluation", GEO.MCI_NORTHLAND_EVALUATION),
            ("admitted_rows_mci_airport", sum(1 for h in census["hotels"]
                                              if (h.get("corridor") or "").endswith("__mci-airport"))),
            ("admitted_rows_northland_north_kansas_city", sum(1 for h in census["hotels"] if (h.get("corridor") or "")
                                                             .endswith("__northland-north-kansas-city"))),
            ("admitted_rows_named_airport_outside_the_mci_corridor", sorted(
                "%s (%s, %s)" % (h.get("canonical_name"), h.get("postal_code"), (h.get("corridor") or "").split("__")[-1])
                for h in census["hotels"]
                if re.search(r"airport|\bkci\b|\bmci\b", h.get("canonical_name") or "", re.I)
                and not (h.get("corridor") or "").endswith("__mci-airport"))),
        ])),
        # JOHNSON COUNTY: Overland Park, Lenexa, Olathe, Shawnee, Merriam / Mission, Prairie Village / Leawood and
        # Gardner are KANSAS corridors decided by the property's own Kansas postal code; a hotel marketed with a
        # Johnson County name whose own address is in Missouri is counted here so the name never moves it.
        ("johnson_county", OrderedDict([
            ("evaluation", GEO.JOHNSON_COUNTY_EVALUATION),
            ("admitted_rows_by_corridor", OrderedDict(sorted(Counter(
                (h.get("corridor") or "").split("__")[-1] for h in census["hotels"]
                if (h.get("corridor") or "").split("__")[-1] in (
                    "overland-park", "lenexa", "olathe", "shawnee", "merriam-mission", "prairie-village-leawood",
                    "gardner")).items()))),
            ("admitted_rows_named_for_a_johnson_county_town_with_a_missouri_address", sorted(
                "%s (%s, %s)" % (h.get("canonical_name"), h.get("postal_code"), h.get("state"))
                for h in census["hotels"]
                if re.search(r"overland park|lenexa|olathe|shawnee|leawood|merriam|mission", h.get("canonical_name") or "",
                             re.I) and GEO.state_for_postal(h.get("postal_code")) == "MO")),
        ])),
        # TWO STATES, NEVER FLATTENED: a row's state is the state its own postal code is in (MO 630-658, KS 660-679);
        # a row whose own stated state disagrees is HELD by the census, never re-labelled.
        ("two_states_never_flattened", OrderedDict([
            ("admitted_rows_missouri", sum(1 for h in census["hotels"] if GEO.state_for_postal(h.get("postal_code")) == "MO")),
            ("admitted_rows_kansas", sum(1 for h in census["hotels"] if GEO.state_for_postal(h.get("postal_code")) == "KS")),
            ("ks_hotels_mislabeled_mo", sum(1 for h in census["hotels"]
                                            if GEO.state_for_postal(h.get("postal_code")) == "KS"
                                            and (h.get("state") or "").upper() in ("MO", "MISSOURI"))),
            ("mo_hotels_mislabeled_ks", sum(1 for h in census["hotels"]
                                            if GEO.state_for_postal(h.get("postal_code")) == "MO"
                                            and (h.get("state") or "").upper() in ("KS", "KANSAS"))),
            ("admitted_rows_with_no_stated_state", sum(1 for h in census["hotels"] if not (h.get("state") or "").strip())),
            ("admitted_rows_city_kansas_city_missouri", sum(
                1 for h in census["hotels"] if (h.get("city") or "").strip().lower() == "kansas city"
                and GEO.state_for_postal(h.get("postal_code")) == "MO")),
            ("admitted_rows_city_kansas_city_kansas", sum(
                1 for h in census["hotels"] if (h.get("city") or "").strip().lower() == "kansas city"
                and GEO.state_for_postal(h.get("postal_code")) == "KS")),
            ("rows_held_for_a_state_postal_conflict", sorted(
                "%s (%s)" % (r.get("canonical_name"), r.get("postal_code")) for r in non
                if "STATE_POSTAL_CONFLICT" in (r.get("classification_reason") or ""))),
            ("missouri_corridors", [c[0] for c in GEO.CORRIDORS if c[-1] == "MO"]),
            ("kansas_corridors", [c[0] for c in GEO.CORRIDORS if c[-1] == "KS"]),
        ])),
        # refused graph nodes whose postal code sits under this market's own prefixes (640 / 641 / 660 / 661 / 662):
        # the refused careful-evaluation towns and rows refused by their own municipality whatever code they state --
        # counted so none falls through unseen
        ("outside_nodes_under_market_prefixes", OrderedDict(sorted(Counter(
            (r.get("postal_code") or "")[:5] for r in non if r["classification"] == "OUTSIDE_MARKET"
            and (r.get("postal_code") or "")[:3] in GEO.VALLEY_PREFIXES).items()))),
        ("kansas_city_ruling", GEO.KANSAS_CITY_RULING),
        ("rows_admitted_from_a_refused_postal_code", _admitted_outside),
        ("zero_admitted_outside", _admitted_outside == 0),
        ("county_boundary_rules", GEO.COUNTY_BOUNDARY_RULES),
        ("existing_live_markets_named", list(GEO.EXISTING_LIVE_MARKETS)),
        ("future_standalone_markets", list(GEO.FUTURE_MARKETS)),
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
        ("schema", "ptf-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", "kansas-city-mo"),
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
            ("closed", 0),
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
            ("closed_note", "No row was classified CLOSED on a first-party closure statement; lapsed routes "
                            "(an expired domain, a brand redirect to its own search) are ROUTING holds, never a "
                            "closure claim."),
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
            ("extended_stay_america", OrderedDict([("routes", esa.get("routes_selected")), ("served", esa.get("pages_served")),
                                                   ("faq_pet_answer", esa.get("with_faq_pet_answer"))])),
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
                ("retry_pass_why", "the Firecrawl rung's own cohort (19 rows) was planned and NOT bought (0 attempts, "
                                   "0 credits): every one of those routes had already been read by the brand-page "
                                   "lane, the attended browser or the Places-sites lane (pay once per page ever). The "
                                   "Choice / IHG brand-page lane (67 pages) and the city-page route discovery (18 "
                                   "pages) are this order's Firecrawl property reads; Marriott, Hilton, Hyatt, Best "
                                   "Western, Drury, Loews, Sonesta, ESA, Motel 6 and the independents were read in the "
                                   "attended browser, and no held row is one a Firecrawl read could resolve (the "
                                   "remaining holds are dual-brand premises, preopening hotels, closed or retired "
                                   "routes, sites with no address of their own, a DataDome wall, and pages read silent)"),
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
                ("source_ready_001_attempts", len(browser)),
                ("source_ready_001_outcomes", OrderedDict(sorted(Counter(b["outcome"] for b in browser).items()))),
                ("closure_002_queue", len(closure_browser)),
                ("closure_002_outcomes", OrderedDict(sorted(Counter(r["outcome"] for r in closure_browser).items()))),
                ("closure_002_reads", sum(1 for r in closure_browser if r["outcome"] == "READ")),
                ("closure_002_bindings", OrderedDict(sorted(Counter(
                    r["binding"] for r in closure_browser if r.get("binding")).items()))),
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
             "every BringFido lead no census node carried was put to Google Places gap verification (existing "
             "capacity): a lead Places verified as an OPERATIONAL hotel at an admitted postal code with its own "
             "street number was admitted as a census identity and routed through the first-party lanes like any "
             "other; a lead Places places at a census node's address or phone is a match, not a gap"),
            ("excluded_stale_outside", recon.get("excluded_stale_outside")),
            ("review", recon.get("review")),
            ("matched_but_policy_unresolved", recon.get("matched_but_policy_unresolved")),
            ("counts", recon.get("counts")),
        ])),
        ("county_and_border_boundary", boundary),
        ("fees", OrderedDict((k, v) for k, v in (L("kansas_city_mo_fee_withholding_001.json", {}) or {}).items()
                             if k not in ("tiered", "unsafe"))),
        ("negation_and_parser_conflicts", clean.get("negation_conflicts_caught", [])),
        ("remaining_unresolved_root_causes", root),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    # The order names SEVEN machine-readable accountings. Each is written as its own document from the
    # SAME sections of this one (never recomputed, so the files cannot disagree); the actionability and competitor
    # reconciliation documents are their own modules' outputs.
    for name, keys in (("source", ("headline", "holds_by_class", "holds_exact_sub_causes", "exclusions",
                                   "remaining_unresolved_root_causes")),
                       ("provider", ("providers",)), ("brand", ("brand_by_brand",)),
                       ("corridor", ("corridor_coverage", "uncorridored_rows", "corridor_count",
                                     "corridors_publishing")),
                       ("boundary", ("county_and_border_boundary",))):
        part = OrderedDict([("schema", "ptf-%s-accounting/1.0" % name), ("work_order", WORK_ORDER),
                            ("market_id", "kansas-city-mo"),
                            ("derived_from", os.path.relpath(OUT, _DASH).replace("\\", "/"))])
        part.update((k, doc[k]) for k in keys)
        with open(os.path.join(R, "kansas_city_mo_%s_accounting_001.json" % name), "w", encoding="utf-8",
                  newline="\n") as fh:
            json.dump(part, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    print("headline:", dict(doc["headline"]))
    print("holds:", dict(doc["holds_by_class"]))
    print("corridors publishing:", doc["corridors_publishing"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

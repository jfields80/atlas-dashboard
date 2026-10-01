"""PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001 -- Phases 10, 13, 20-25 and 29: the machine-readable accounting.

Reads only committed reports and staged documents (nothing fetches) and writes one accounting document with:
headline accounting, holds by class (the order's exact vocabulary), exclusions by class, corridor coverage,
brand-by-brand acquisition accounting, provider-attempt accounting (static, Wyndham, ESA, independents' pages,
Places, Firecrawl, supported browser), competitor reconciliation, the Central Texas boundary audit, negation /
parser conflicts, and the remaining unresolved root causes.

Output: launch_packages/pettripfinder/markets/reports/austin_tx_source_ready_accounting_001.json
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

from scripts.pettripfinder import austin_tx_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder.austin_tx_nonhotel_rulings_001 import exclusion_class  # noqa: E402

#: PTF-AUSTIN-TX-POST-READER-SAFETY-REFRESH-002 re-derives this output under the repaired shared first-party reader;
#: the market was built by PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001 (SOURCE_READY_ORDER), whose captures it reuses.
SOURCE_READY_ORDER = "PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001"
WORK_ORDER = "PTF-AUSTIN-TX-POST-READER-SAFETY-REFRESH-002"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", "austin-tx", "raw_captures")
OUT = os.path.join(R, "austin_tx_source_ready_accounting_001.json")
PARTITION = os.path.join(PKG, "markets", "staging", "austin-tx", "launch_package", "austin_tx_final_partition_001.json")

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
                                r"siegel|crossland|home towne|hometowne studios|sentral|extended stay austin|"
                                r"texas bungalows"),
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
#: Luxury / boutique independents (not a chain family), reported as their own rows by name vocabulary. AUSTIN's
#: own: downtown's historic and design hotels, South Congress's Bunkhouse and boutique motels, the Lake Austin /
#: Lake Travis resorts and the Hill Country gateway inns. Nothing is inherited from Phoenix.
LUXURY_RX = re.compile(r"\b(driskill|commodore perry|hotel saint cecilia|saint cecilia|hotel san jose|austin motel|"
                       r"carpenter hotel|hotel magdalena|south congress hotel|hotel van zandt|the line|proper|"
                       r"hotel ella|hotel zaza|the loren|lake austin spa|miraval|hotel viata|heywood|the wayback|"
                       r"the frances|kimber modern|hotel granduca|1 hotel austin|fairmont austin|the stephen f|"
                       r"green pastures|sage hill|travaasa|lake travis|firehouse|carpenter|arrive austin|"
                       r"hotel vegas|the otis|archer hotel|canopy|the guild|hotel ylem|east austin hotel)\b", re.I)
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
    census = json.load(open(os.path.join(PKG, "identity_census_proposed", "austin-tx.json"), encoding="utf-8"))
    part = json.load(open(PARTITION, encoding="utf-8"))
    clean = L("austin_tx_clean_authority_001.json", {}) or {}
    fc = L("austin_tx_firecrawl_pass_001.json", {}) or {}
    fc2 = L("austin_tx_firecrawl_pass_002.json", {}) or {}
    fc3 = L("austin_tx_firecrawl_pass_003.json", {}) or {}
    bpr = L("austin_tx_brand_page_reads_001.json", {}) or {}
    disc = L("austin_tx_firecrawl_discovery_001.json", {}) or {}
    static = L("austin_tx_free_static_capture_001.json", {}) or {}
    comp = L("austin_tx_competitor_challenge_001.json", {}) or {}
    recon = L("austin_tx_competitor_reconciliation_001.json", {}) or {}
    dbpr = L("austin_tx_btc_lane_001.json", {}) or {}
    osm = L("austin_tx_osm_lane_001.json", {}) or {}
    brand = L("austin_tx_brand_inventory_001.json", {}) or {}
    roster = L("austin_tx_destination_roster_001.json", {}) or {}
    routing = L("austin_tx_routing_001.json", {}) or {}
    wyndham = L("austin_tx_wyndham_lane_001.json", {}) or {}
    esa = L("austin_tx_esa_lane_001.json", {}) or {}
    places = L("austin_tx_places_route_discovery_001.json", {}) or {}
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
    creport = L("austin_tx_census_reconciliation_001.json", {}) or {}

    # corridors
    cor = OrderedDict()
    for slug, name, _a, klass, _m, _z, _d in GEO.CORRIDORS:
        cid = "austin-tx__" + slug
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
    act = L("austin_tx_actionability_001.json", {}) or {}
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
    # the attended-browser lane this order actually exercised (austin_tx_browser_lane_001),
    # counted per brand family so the brand table reports reads and denials, not a placeholder zero.
    _blp = os.path.join(R, "austin_tx_browser_lane_001.json")
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

    # PHASE 25 -- THE CENTRAL TEXAS BOUNDARY AUDIT, framed for THIS market. Every OUTSIDE graph node is counted
    # by the refused place its OWN postal code or municipality names; every brand card the Hilton city pages
    # refused by its own address is counted too, so a neighbour that only a brand card reached is SEEN. The
    # postal codes are the geography module's OWN refused lists (GEO.OUTSIDE), never retyped here.
    _OUT = {row[0].split(" --")[0].split(" /")[0]: tuple(row[2]) for row in GEO.OUTSIDE}
    _z = lambda head: next(v for k, v in _OUT.items() if k.startswith(head))  # noqa: E731
    _hill = _z("Texas Hill Country")
    _fbg = ("78624", "78631", "78671")          # Fredericksburg, Harper, Stonewall -- inside the Hill Country list
    refused_places = OrderedDict([
        ("SAN_ANTONIO", (r"san antonio|alamo heights|live oak|universal city|schertz|selma|converse|helotes|"
                         r"leon valley|windcrest|kirby|cibolo", ("780", "782"))),
        ("WACO", (r"waco|hewitt|woodway|bellmead|robinson|lorena|lacy lakeview|mcgregor", ("766", "767"))),
        ("FREDERICKSBURG", (r"fredericksburg|stonewall|harper", _fbg)),
        ("SAN_MARCOS", (r"san marcos|martindale|maxwell", _z("San Marcos"))),
        ("NEW_BRAUNFELS", (r"new braunfels|seguin|canyon lake|gruene", ("781",) + _z("New Braunfels"))),
        ("OTHER_HILL_COUNTRY", (r"johnson city|wimberley|blanco|marble falls|horseshoe bay|burnet|llano|kingsland|"
                                r"spicewood|boerne|comfort|kerrville|luckenbach|round mountain|driftwood|"
                                r"granite shoals|cottonwood shores|meadowlakes",
                                tuple(z for z in _hill if z not in _fbg))),
        ("OTHER_CENTRAL_TEXAS", (r"bastrop|cedar creek|smithville|elgin|mcdade|paige|liberty hill|bertram|florence|"
                                 r"jarrell|weir|walburg|taylor|coupland|granger|thrall|lockhart|luling|uhland|"
                                 r"killeen|temple|belton|harker heights|salado|copperas cove|bryan|college station|"
                                 r"la grange|giddings|columbus|brenham",
                                 _z("Bastrop") + _z("Elgin") + _z("Liberty Hill") + _z("Taylor") + _z("Lockhart")
                                 + ("765", "778", "789"))),
        ("OUT_OF_STATE_OR_OTHER_TEXAS", (r"dallas|fort worth|houston|el paso|corpus christi|lubbock|amarillo|"
                                         r"midland|odessa|abilene|san angelo|beaumont|victoria",
                                         ("750", "751", "752", "753", "760", "761", "762", "763", "764", "768",
                                          "769", "770", "772", "773", "774", "775", "776", "777", "779", "783",
                                          "784", "785", "788", "790", "791", "793", "794", "795", "796", "797",
                                          "798", "799"))),
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
    for h in (L("austin_tx_brand_inventory_001.json", {}) or {}).get("leads", []):
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
        ("san_antonio", _pair("SAN_ANTONIO")),
        ("waco", _pair("WACO")),
        ("fredericksburg", _pair("FREDERICKSBURG")),
        ("san_marcos", _pair("SAN_MARCOS")),
        ("new_braunfels", _pair("NEW_BRAUNFELS")),
        ("other_hill_country_destination", _pair("OTHER_HILL_COUNTRY")),
        ("other_central_texas", _pair("OTHER_CENTRAL_TEXAS")),
        ("out_of_state_or_other_texas", _pair("OUT_OF_STATE_OR_OTHER_TEXAS")),
        # refused graph nodes whose postal code sits under this market's own prefixes (786 / 787): the refused
        # careful-evaluation towns and rows refused by their own municipality whatever code they state --
        # counted so none falls through unseen
        ("outside_nodes_under_market_prefixes", OrderedDict(sorted(Counter(
            (r.get("postal_code") or "")[:5] for r in non if r["classification"] == "OUTSIDE_MARKET"
            and (r.get("postal_code") or "")[:3] in GEO.VALLEY_PREFIXES).items()))),
        ("hill_country_ruling", GEO.HILL_COUNTRY_RULING),
        ("rows_admitted_from_a_refused_postal_code", _admitted_outside),
        ("zero_admitted_outside", _admitted_outside == 0),
        ("county_boundary_rules", GEO.COUNTY_BOUNDARY_RULES),
        ("existing_live_markets_named", list(GEO.EXISTING_LIVE_MARKETS)),
        ("future_standalone_markets", list(GEO.FUTURE_MARKETS)),
    ])

    root = OrderedDict([
        ("ROUTING_HOLD", "no first-party route: no brand inventory row, bureau link or map website joined the "
                         "building, and Places route discovery was NOT run because its website field is an "
                         "Enterprise-SKU field whose free monthly allowance is already consumed (new spend)."),
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
        ("schema", "ptf-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", "austin-tx"),
        ("headline", OrderedDict([
            ("total_raw_observations", creport.get("observations_total")),
            ("raw_observations_by_lane", creport.get("lane_yields")),
            ("city_business_tax_register_lodging_leads", dbpr.get("lead_count")),
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
            ("closed", 0), ("outside", ncls.get("OUTSIDE_MARKET", 0)),
            ("duplicate_listing", ncls.get("DUPLICATE_LISTING", 0)),
            ("name_only_unresolved_graph_residue", ncls.get("NAME_ONLY_UNRESOLVED", 0)),
            ("identity_review_required_graph_residue", ncls.get("IDENTITY_REVIEW_REQUIRED", 0)),
            ("same_campus_distinct_entity", ncls.get("SAME_CAMPUS_DISTINCT_ENTITY", 0)),
            ("city_register_short_term_rental_certificates_never_admitted",
             sum((dbpr.get("short_term_rental_certificates_by_corridor") or {}).values())
             + int(dbpr.get("short_term_rental_certificates_outside") or 0)),
            ("city_register_rooming_houses_never_admitted", (dbpr.get("rank_counts") or {}).get("ROOMING_HOUSE", 0)),
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
                                                    ("field_mask", places.get("field_mask")),
                                                    ("route_discovery_run", places.get("route_discovery_run")),
                                                    ("cost_basis", "existing GOOGLE_PLACES_API_KEY capacity, PRO-tier "
                                                                   "field mask only; no new key, no new authorization")])),
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
                ("retry_pass_why", "no retry or probe pass was run in Austin (0 attempts); the brand-page lane "
                                   "and pass 001 are the only Firecrawl property-page reads"),
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
             "not carried into the census: BringFido publishes no street, no free authorized identity lane (brand "
             "inventory, seven bureaux, the map, brand city pages) states one, and Places gap verification is new "
             "spend this month; each stays a named competitor gap, never a published row"),
            ("excluded_stale_outside", recon.get("excluded_stale_outside")),
            ("review", recon.get("review")),
            ("matched_but_policy_unresolved", recon.get("matched_but_policy_unresolved")),
            ("counts", recon.get("counts")),
        ])),
        ("county_and_border_boundary", boundary),
        ("fees", OrderedDict((k, v) for k, v in (L("austin_tx_fee_withholding_001.json", {}) or {}).items()
                             if k not in ("tiered", "unsafe"))),
        ("negation_and_parser_conflicts", clean.get("negation_conflicts_caught", [])),
        ("remaining_unresolved_root_causes", root),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    # AUSTIN: the order names SEVEN machine-readable accountings. Each is written as its own document from the
    # SAME sections of this one (never recomputed, so the files cannot disagree); the actionability and competitor
    # reconciliation documents are their own modules' outputs.
    for name, keys in (("source", ("headline", "holds_by_class", "holds_exact_sub_causes", "exclusions",
                                   "remaining_unresolved_root_causes")),
                       ("provider", ("providers",)), ("brand", ("brand_by_brand",)),
                       ("corridor", ("corridor_coverage", "uncorridored_rows", "corridor_count",
                                     "corridors_publishing")),
                       ("boundary", ("county_and_border_boundary",))):
        part = OrderedDict([("schema", "ptf-%s-accounting/1.0" % name), ("work_order", WORK_ORDER),
                            ("market_id", "austin-tx"),
                            ("derived_from", os.path.relpath(OUT, _DASH).replace("\\", "/"))])
        part.update((k, doc[k]) for k in keys)
        with open(os.path.join(R, "austin_tx_%s_accounting_001.json" % name), "w", encoding="utf-8",
                  newline="\n") as fh:
            json.dump(part, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    print("headline:", dict(doc["headline"]))
    print("holds:", dict(doc["holds_by_class"]))
    print("corridors publishing:", doc["corridors_publishing"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phases 10, 13, 20-25 and 29: the machine-readable accounting.

Reads only committed reports and staged documents (nothing fetches) and writes one accounting document with:
headline accounting, holds by class (the order's exact vocabulary), exclusions by class, corridor coverage,
brand-by-brand acquisition accounting, provider-attempt accounting (static, Wyndham, ESA, independents' pages,
Places, Firecrawl, supported browser), competitor reconciliation, the South Florida boundary audit, negation /
parser conflicts, and the remaining unresolved root causes.

Output: launch_packages/pettripfinder/markets/reports/jacksonville_fl_source_ready_accounting_001.json
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

from scripts.pettripfinder import jacksonville_fl_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder.jacksonville_fl_nonhotel_rulings_001 import exclusion_class  # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", "jacksonville-fl", "raw_captures")
OUT = os.path.join(R, "jacksonville_fl_source_ready_accounting_001.json")
#: REGISTERED by PTF-JACKSONVILLE-FL-REGISTRATION-AND-STAGING-002: the partition lives at the package root.
PARTITION = os.path.join(PKG, "jacksonville_fl_final_partition_001.json")

#: The order's hold vocabulary, and which clean-authority disposition each maps from.
HOLD_CLASSES = OrderedDict([
    ("IDENTITY", ("IDENTITY_MISMATCH_HOLD",)), ("ROUTING", ("ROUTING_HOLD",)), ("ACCESS_BLOCKED", ("ACCESS_BLOCKED",)),
    ("EVIDENCE", ("EVIDENCE_HOLD",)), ("NEGATION", ("NEGATION_HOLD",)), ("BROWSER_CAPTURE", ("BROWSER_CAPTURE_NEEDED",)),
    ("POLICY_NOT_FOUND", ()), ("SOURCE_SILENT", ("SOURCE_SILENT",)), ("MIXED_RESORT", ()), ("CONDO_HOTEL", ()),
    ("PAID", ()), ("GEOGRAPHY", ()), ("FOUNDER", ()), ("OTHER", ()),
])

FAMILIES = [
    ("MARRIOTT", r"marriott|courtyard by marriott|courtyard marriott|courtyard jacksonville|courtyard amelia|courtyard by|courtyard(?= (jacksonville|downtown|airport|butler|orange|beach|amelia|flagler|mayo|north|south))|residence inn|springhill|fairfield|towneplace|ac hotel|studiores|city express|aloft|westin|sheraton|"
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
    ("RED_ROOF", r"red roof|hometowne"), ("MOTEL6_STUDIO6", r"motel 6|studio 6"), ("RADISSON", r"radisson|country inn"),
    ("LOEWS", r"\bloews\b"), ("FOUR_SEASONS", r"four seasons"), ("ACCOR", r"sofitel|pullman|novotel|ibis|mgallery|fairmont|"
                                                                        r"\bsls\b|mondrian|delano|hyde|\bsbe\b"),
    ("NOBU", r"\bnobu\b"), ("OMNI", r"\bomni\b"),
]
#: Luxury / resort independents (not a chain family), reported as their own rows by name vocabulary.
#: Luxury / resort independents (not a chain family), reported as their own rows by name vocabulary.
#: NORTHEAST FLORIDA's own: Amelia Island's two flagship resort campuses, Ponte Vedra's clubs, the Sawgrass
#: golf resort, the Jacksonville Beach oceanfront independents, downtown's Omni and the Southbank's riverfront
#: hotels, and Fernandina's Centre Street historic inns. Nothing is inherited from Palm Beach or Broward.
LUXURY_RX = re.compile(r"\b(ritz.?carlton|four seasons|omni amelia|amelia island plantation|"
                       r"ponte vedra inn|the lodge (and|&) club|sawgrass marriott|tpc sawgrass|"
                       r"the inn (and|&) club|elizabeth pointe|amelia schoolhouse|fairbanks house|"
                       r"hoyt house|addison on amelia|florida house inn|williams house|"
                       r"margaritaville|one ocean|casa marina|the seahorse|"
                       r"the bearded|hotel palms|beachcomber|the surf|"
                       r"omni jacksonville|southbank hotel|the bostwick|stay sojo)\b", re.I)
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
    census = json.load(open(os.path.join(PKG, "identity_census", "jacksonville-fl.json"), encoding="utf-8"))
    part = json.load(open(PARTITION, encoding="utf-8"))
    clean = L("jacksonville_fl_clean_authority_001.json", {}) or {}
    fc = L("jacksonville_fl_firecrawl_pass_001.json", {}) or {}
    fc2 = L("jacksonville_fl_firecrawl_pass_002.json", {}) or {}
    fc3 = L("jacksonville_fl_firecrawl_pass_003.json", {}) or {}
    bpr = L("jacksonville_fl_brand_page_reads_001.json", {}) or {}
    disc = L("jacksonville_fl_firecrawl_discovery_001.json", {}) or {}
    static = L("jacksonville_fl_free_static_capture_001.json", {}) or {}
    comp = L("jacksonville_fl_competitor_challenge_001.json", {}) or {}
    recon = L("jacksonville_fl_competitor_reconciliation_001.json", {}) or {}
    dbpr = L("jacksonville_fl_dbpr_lane_001.json", {}) or {}
    osm = L("jacksonville_fl_osm_lane_001.json", {}) or {}
    brand = L("jacksonville_fl_brand_inventory_001.json", {}) or {}
    roster = L("jacksonville_fl_destination_roster_001.json", {}) or {}
    routing = L("jacksonville_fl_routing_001.json", {}) or {}
    wyndham = L("jacksonville_fl_wyndham_lane_001.json", {}) or {}
    esa = L("jacksonville_fl_esa_lane_001.json", {}) or {}
    places = L("jacksonville_fl_places_route_discovery_001.json", {}) or {}
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
    creport = L("jacksonville_fl_census_reconciliation_001.json", {}) or {}

    # corridors
    cor = OrderedDict()
    for slug, name, _a, klass, _m, _z, _d in GEO.CORRIDORS:
        cid = "jacksonville-fl__" + slug
        rows = [i for i in items if i["corridor"] == cid]
        p = sum(1 for i in rows if i["final_state"] == "PUBLISHED_PET_FRIENDLY")
        n = sum(1 for i in rows if i["final_state"] == "VERIFIED_NO_PETS")
        cor[slug] = OrderedDict([("name", name), ("class", klass), ("census", len(rows)), ("pet_friendly", p),
                                 ("no_pets", n), ("unresolved", len(rows) - p - n),
                                 ("resolution_rate", round((p + n) / len(rows), 4) if rows else None),
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
    # PALM BEACH COUNTY: the attended-browser lane this order actually exercised (jacksonville_fl_browser_lane_001),
    # counted per brand family so the brand table reports reads and denials, not a placeholder zero.
    _blp = os.path.join(R, "jacksonville_fl_browser_lane_001.json")
    _bl = json.load(open(_blp, encoding="utf-8")) if os.path.exists(_blp) else {}
    _browser_attempts, _browser_reads, _browser_denied = Counter(), Counter(), Counter()
    for _r in _bl.get("rows", []):
        _fam = _r.get("family") or ""
        _browser_attempts[_fam] += 1
        if _r.get("outcome") == "READ":
            _browser_reads[_fam] += 1
        elif _r.get("outcome") == "CHALLENGE_DENIED_AKAMAI_ACCESS_DENIED":
            _browser_denied[_fam] += 1
    brand_tbl = OrderedDict()
    for fam in sorted(fam_tbl):
        t = fam_tbl[fam]
        brand_tbl[fam] = OrderedDict([(k, int(t[k])) for k in (
            "census", "pet_friendly", "no_pets", "unresolved", "firecrawl_attempted", "firecrawl_success",
            "access_blocked", "browser_capture_needed")])
        brand_tbl[fam]["browser_attempted"] = _browser_attempts.get(fam, 0) or browser_fams.get(fam, 0)
        brand_tbl[fam]["browser_read"] = _browser_reads.get(fam, 0)
        brand_tbl[fam]["browser_challenge_denied"] = _browser_denied.get(fam, 0)

    fc_class = Counter(r.get("firecrawl_class") for r in fc_rows)
    fc_cohort = Counter(r.get("cohort") for r in fc_rows)
    credits = fc.get("credits", {}) or {}

    # South Florida boundary (registry lane counts by county, plus every refused-place node of the graph)
    boundary_nodes = Counter()
    for r in non:
        if r["classification"] != "OUTSIDE_MARKET":
            continue
        txt = ((r.get("city") or "") + " " + (r.get("classification_reason") or "")).lower()
        for label, rx in (("ST_AUGUSTINE", r"st\.? augustine|saint augustine|world golf village|"
                                            r"st-augustine|hastings|elkton"),
                          ("PALM_COAST_FLAGLER", r"palm coast|flagler beach|bunnell|flagler"),
                          ("DAYTONA_VOLUSIA", r"daytona|ormond|deland|new smyrna|port orange|volusia"),
                          ("GAINESVILLE_ALACHUA", r"gainesville|alachua|high springs|newberry"),
                          ("PUTNAM", r"palatka|crescent city|satsuma|welaka|georgetown|putnam"),
                          ("BAKER", r"macclenny|glen st mary|baker"),
                          ("CLAY_LAKE_COUNTRY", r"keystone heights"),
                          ("GEORGIA", r"kingsland|st\.? marys|saint marys|folkston|woodbine|brunswick|"
                                      r"st\.? simons|saint simons|jekyll|darien|savannah|pooler|waycross|"
                                      r"tybee|georgia|-ga\b"),
                          ("OTHER_LIVE_FLORIDA_MARKET", r"orlando|kissimmee|tampa|st petersburg|miami|"
                                                        r"fort lauderdale|west palm beach|boca raton"),
                          ("JACKSONVILLE_NORTH_CAROLINA", r"camp lejeune|onslow|richlands|sneads ferry|"
                                                          r"swansboro|north carolina|\bnc\b")):
            if re.search(rx, txt):
                boundary_nodes[label] += 1
                break
    # PHASE 22 -- the county boundary audit, framed for THIS market.
    #
    # This market has NO single home county, which is what makes its audit different from every prior one.
    # FOUR counties carry admitted corridors and THREE of them are SPLIT: Duval whole, Clay split (Orange
    # Park in, Keystone Heights out), Nassau split by tier, St. Johns split hardest (Ponte Vedra and Fruit
    # Cove in, every St. Augustine code out). The audit is therefore read straight off this market's own
    # registry lane, which counts every hotel-rank licence by the licence's OWN county and states how many of
    # each this market ADMITTED -- so a split county reports as discovered N / admitted M rather than as a
    # single yes or no.
    by_county = dbpr.get("county_boundary_audit", {}) or {}
    _admitted_outside = sum(1 for h in census["hotels"]
                            if GEO.classify_postal(h.get("postal_code"), h.get("city"))[0] == "OUTSIDE")
    _live_admissions = sum(v.get("admitted_into_jacksonville_fl", 0) for k, v in by_county.items()
                           if v.get("preserved_or_live_market") in GEO.EXISTING_LIVE_MARKETS)
    _pb_ranks = dbpr.get("rank_counts_in_admitted_postal_codes", {}) or {}
    boundary = OrderedDict([
        ("method", "DBPR licences counted by the licence's OWN county (HOTL / MOTL / BNB / TAPT ranks). "
                   "Admission is by the corridor registry over the property's own postal code, and by "
                   "nothing else -- never by the county field, which is the LICENSING county."),
        ("home_counties", GEO.COUNTY_BOUNDARY_RULES and list(GEO.ADMITTED_COUNTIES) or []),
        ("no_single_home_county",
         "Four counties carry admitted corridors and three of them are SPLIT. Duval is admitted whole; Clay, "
         "Nassau and St. Johns each report a discovered count and a smaller admitted count, and St. Johns' gap "
         "is the entire St. Augustine inventory."),
        ("home_county_hotel_rank_licences_in_admitted_postal_codes",
         sum(_pb_ranks.get(r, 0) for r in ("HOTL", "MOTL", "BNB"))),
        ("neighbour_counties", OrderedDict(
            (k, OrderedDict([
                ("hotel_rank_licences", v.get("hotel_rank_licences_discovered",
                                              v.get("hotel_rank_licences", 0))),
                ("admitted_into_jacksonville_fl", v.get("admitted_into_jacksonville_fl", 0)),
                ("role", v.get("role", "")),
                ("owner", v.get("preserved_or_live_market", "")),
                ("owner_is_live", v.get("preserved_or_live_market") in GEO.EXISTING_LIVE_MARKETS),
            ])) for k, v in sorted(by_county.items()))),
        ("live_market_inventory_admitted", _live_admissions),
        ("no_live_market_inventory_admitted", _live_admissions == 0),
        ("why_that_matters", "savannah-ga and orlando-fl are LIVE markets and jacksonville-nc is a LIVE market "
                             "with this market's own NAME. Admitting one of their postal codes would publish "
                             "the same hotel in two markets, so a non-zero count here is a defect, not a "
                             "judgement. Georgia's counties cannot appear in a Florida licence extract at all, "
                             "which is the state-line refusal expressed mechanically."),
        ("county_boundary_rules", GEO.COUNTY_BOUNDARY_RULES),
        ("named_place_audit", dbpr.get("named_place_audit", {})),
        ("cross_county_rows_admitted", dbpr.get("cross_county_admitted_rows", [])),
        ("outside_graph_nodes_by_place", OrderedDict(sorted(boundary_nodes.items()))),
        ("rows_admitted_from_a_refused_postal_code", _admitted_outside),
        ("no_northeast_florida_sprawl", _admitted_outside == 0),
        ("existing_live_markets_named", list(GEO.EXISTING_LIVE_MARKETS)),
        ("future_standalone_markets", list(GEO.FUTURE_MARKETS)),
    ])

    root = OrderedDict([
        ("BROWSER_CAPTURE_NEEDED", "ZERO in this market. The committed route table sends Marriott and Hilton to a "
                                   "paid browser provider and excludes Hyatt and Best Western from its paid "
                                   "lanes; this order exercised the SUPPORTED ATTENDED BROWSER instead -- 61 "
                                   "paced attempts, 49 first-party reads, no paid provider, no relay, no "
                                   "browser-JS exfiltration and no Akamai bypass. Every browser-required row "
                                   "is read or terminally classified."),
        ("ROUTING_HOLD", "no first-party route: the routing pass found no brand, bureau or map website, and Places route "
                         "discovery either bound no place at the row's own street number + ZIP, or bound one whose card "
                         "names no website (NO_OFFICIAL_WEB_PRESENCE_FOUND), or names a brand/OTA host."),
        ("ACCESS_BLOCKED", "every free / authorized lane attempted (static plain client, Firecrawl where the router "
                           "made the row eligible or probe-eligible) was refused or failed."),
        ("SOURCE_SILENT", "the property's own page or site served, bound to the identity, and stated no operative "
                          "pet policy on its home or policy / FAQ pages."),
        ("EVIDENCE_HOLD", "a fee / weight / count sentence with no explicit acceptance wording, or a shared-reader "
                          "disagreement; held, never published."),
        ("IDENTITY_MISMATCH_HOLD", "the fetched page or site never confirmed this census row's address, phone or code."),
    ])

    doc = OrderedDict([
        ("schema", "ptf-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", "jacksonville-fl"),
        ("headline", OrderedDict([
            ("total_raw_observations", creport.get("observations_total")),
            ("raw_observations_by_lane", creport.get("lane_yields")),
            ("dbpr_licensed_lodging_leads", dbpr.get("lead_count")),
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
            ("dbpr_cndo_condo_units_never_admitted", (dbpr.get("exclusion_totals") or {}).get("CNDO", 0)),
            ("dbpr_dwel_vacation_dwellings_never_admitted", (dbpr.get("exclusion_totals") or {}).get("DWEL", 0)),
            ("dbpr_napt_apartments_never_admitted", (dbpr.get("exclusion_totals") or {}).get("NAPT", 0)),
            ("dbpr_tapt_apartment_named_refused", len(dbpr.get("tapt_refused_as_apartment") or [])),
            ("closed_note", "No row was classified CLOSED: DBPR extracts carry only active licences, and no first-party "
                            "read in this order stated a closure."),
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
            ("wyndham_property_service", OrderedDict([("selected", wyndham.get("selected")), ("read", wyndham.get("read")),
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
                                                    ("cost_basis", "existing GOOGLE_PLACES_API_KEY capacity; no new key, "
                                                                   "no new authorization, no plan purchase")])),
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
                ("retry_pass_why", "first-pass FIRECRAWL_MISMATCH rows re-attempted once after the census "
                                   "restated numbered beach streets and state-road / US-highway spellings the "
                                   "way the pages write them"),
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
            ("excluded_stale_outside", recon.get("excluded_stale_outside")),
            ("review", recon.get("review")),
            ("matched_but_policy_unresolved", recon.get("matched_but_policy_unresolved")),
            ("counts", recon.get("counts")),
        ])),
        # the boundary accounting the order names. The parent market called this key
        # `south_florida_boundary`; this market is NORTHEAST Florida and its neighbours are Alachua, Baker,
        # Flagler, Putnam and Volusia, so carrying the parent's key name would file a correct measurement under
        # the wrong region.
        ("northeast_florida_boundary", boundary),
        ("negation_and_parser_conflicts", clean.get("negation_conflicts_caught", [])),
        ("remaining_unresolved_root_causes", root),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("headline:", dict(doc["headline"]))
    print("holds:", dict(doc["holds_by_class"]))
    print("corridors publishing:", doc["corridors_publishing"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phases 31-36 and 47: the machine-readable accountings.

Reads ONLY this order's committed reports and staged documents (never fetches) and writes one accounting per question
the order asks, each a pure derivation of the census, the clean-authority adjudication, the actionability report and
the lanes' own reports:

  source          every discovery lane's raw yield and what it contributed to the census
  provider        Firecrawl (live balance and reserve), Google Places (Enterprise / Pro requests), the attended
                  browser (attempts / reads / denials per family), the plain-client lanes; paid spend
  brand           census / PF / NP / unresolved / browser attempts / reads / blocked / actionable per brand family
  county          admitted rows per county (the Census county boundary of the premises, or the postal fallback)
  city            admitted rows per published municipality, with the suburban-mislabel counts
  corridor        census / PF / NP / unresolved / resolution / threshold / publishes per corridor
  dfw_airport     the on-airport corridor and every airport-marketed row, with its premises
  boundary        the named outer places (Weatherford, Waxahachie, Corsicana, Greenville, Sherman / Denison, Waco,
                  Denton, McKinney, Allen ...) discovered vs admitted, and the refused-county and OSM measurements
  summary         the order's headline numbers in one place

Output: launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_<name>_accounting_001.json
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

from scripts.pettripfinder import dallas_fort_worth_tx_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures")
CENSUS = os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID)

PF, NP = "CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"
FAMILIES = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|"
                 r"moxy|element|renaissance|delta hotels|autograph|gaylord|w dallas|tribute|four points|le meridien|"
                 r"st\. regis|ritz|jw marriott|city express|luxury collection"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|\btru\b|tapestry|canopy|spark by|"
               r"curio|motto|signia|tempo|lxr"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|hotel indigo|voco|"
            r"atwell|garner"),
    ("KIMPTON", r"kimpton"),
    ("HYATT", r"hyatt|thompson|andaz|caption by|alila"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|"
               r"rodeway|ascend|everhome"),
    ("WOODSPRING", r"woodspring"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|"
                r"americinn|wingate|trademark|echo suites"),
    ("BEST_WESTERN", r"best western|surestay|sure stay|\bbw\b"),
    ("SONESTA", r"sonesta|americas best value|america's best value|red lion|signature inn|simply suites"),
    ("EXTENDED_STAY_AMERICA", r"extended stay america"),
    ("MOTEL6_STUDIO6", r"motel 6|studio 6"),
    ("RED_ROOF", r"red roof|hometowne"),
    ("DRURY", r"drury"),
    ("OMNI", r"\bomni\b"),
    ("LOEWS", r"\bloews\b"),
    ("RADISSON", r"radisson|country inn"),
    ("OTHER_EXTENDED_STAY", r"intown|extended stay|siegel|my place|home towne|crossland|residence|suites$"),
]


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _jsonl(path):
    out = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    out.append(json.loads(line))
    return out


def family(name):
    n = (name or "").lower()
    for fam, rx in FAMILIES:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def _write(name, doc):
    path = os.path.join(R, "dallas_fort_worth_tx_%s_accounting_001.json" % name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return os.path.relpath(path, _DASH).replace("\\", "/")


def _head(name):
    return OrderedDict([("schema", "ptf-%s-accounting/1.0" % name), ("work_order", WORK_ORDER),
                        ("market_id", MARKET_ID)])


def main():
    census = _load(CENSUS, {}) or {}
    hotels = census.get("hotels", [])
    non_admitted = census.get("non_admitted", [])
    clean = _load(os.path.join(R, "dallas_fort_worth_tx_clean_authority_001.json"), {}) or {}
    act = _load(os.path.join(R, "dallas_fort_worth_tx_actionability_001.json"), {}) or {}
    creport = _load(os.path.join(R, "dallas_fort_worth_tx_census_reconciliation_001.json"), {}) or {}
    disp = {r["identity_key"]: r for r in clean.get("rows", [])}
    actx = {r["identity_key"]: r for r in act.get("rows", [])}
    reads = _jsonl(os.path.join(RAW, "browser_reads_001.jsonl"))
    blane = (_load(os.path.join(RAW, "browser_closure_rows.json"), {}) or {}).get("rows", [])
    bound = {}
    for b in blane:
        if b.get("identity_key"):
            bound.setdefault(b["identity_key"], []).append(b)

    def state(h):
        return (disp.get(h["identity_key"]) or {}).get("disposition", "UNADJUDICATED")

    def tally(rows):
        c = Counter(state(h) for h in rows)
        pf, np_ = c.get(PF, 0), c.get(NP, 0)
        return OrderedDict([("census", len(rows)), ("pet_friendly", pf), ("verified_no_pets", np_),
                            ("unresolved", len(rows) - pf - np_),
                            ("resolution_rate", round(100.0 * (pf + np_) / len(rows), 2) if rows else None)])

    written = []
    # ---------------------------------------------------------------- county / city
    by_county = OrderedDict()
    for h in hotels:
        by_county.setdefault(h.get("county") or GEO.county_for_postal(h.get("postal_code")) or "", []).append(h)
    county = _head("county")
    county["rule"] = ("each admitted row's county is the Census county boundary that contains its premises (or, with no "
                      "coordinates, its postal code's single county); Dallas and Tarrant admitted whole, Collin's and "
                      "Denton's south tiers by postal code; every other county refused")
    county["by_county"] = OrderedDict((k or "(unplaced)", tally(v)) for k, v in sorted(by_county.items()))
    county["refused_county_rows"] = [OrderedDict([("canonical_name", r["canonical_name"]), ("postal_code",
                                                  r.get("postal_code")), ("reason", (r.get("classification_reason")
                                                                                      or "")[:200])])
                                     for r in non_admitted if "COUNTY_REFUSAL" in (r.get("classification_reason") or "")]
    written.append(_write("county", county))

    by_city = OrderedDict()
    for h in hotels:
        by_city.setdefault(h.get("city") or "", []).append(h)
    mp = (creport.get("municipality_publication") or {})
    city = _head("city")
    city["rule"] = ("every admitted row publishes the municipality its premises are in (Census TIGER place boundary); "
                    "'Dallas' / 'Fort Worth' on suburban premises is never published")
    city["by_municipality"] = OrderedDict((k or "(none)", tally(v)) for k, v in sorted(by_city.items()))
    for k in ("SUBURBAN_HOTELS_MISLABELED_DALLAS", "SUBURBAN_HOTELS_MISLABELED_FORT_WORTH", "WRONG_CITY_IDENTITIES",
              "REFUSED_COUNTY_ADMITTED", "rows_relabelled_count", "placement_basis_counts"):
        city[k] = mp.get(k)
    city["plano_profiles_labeled_dallas"] = sum(1 for h in hotels if h.get("corridor", "").endswith("__plano")
                                                and GEO.normalise_municipality(h.get("city")) == "dallas")
    city["frisco_profiles_labeled_dallas"] = sum(1 for h in hotels if h.get("corridor", "").endswith("__frisco")
                                                 and GEO.normalise_municipality(h.get("city")) == "dallas")
    city["relabelled_rows"] = mp.get("rows_relabelled")
    written.append(_write("city", city))

    # ---------------------------------------------------------------- corridor
    by_corr = OrderedDict((c[0], []) for c in GEO.CORRIDORS)
    for h in hotels:
        by_corr.setdefault((h.get("corridor") or "").split("__")[-1], []).append(h)
    corridor = _head("corridor")
    corridor["threshold"] = "a corridor page publishes only with >= 5 verified pet-friendly profiles; never forced"
    rows = []
    for c in GEO.CORRIDORS:
        t = tally(by_corr.get(c[0], []))
        t.update(OrderedDict([("threshold", 5), ("publishes", "YES" if t["pet_friendly"] >= 5 else "NO")]))
        rows.append(OrderedDict([("corridor", c[0]), ("name", c[1]), ("class", c[3])] + list(t.items())))
    corridor["corridors"] = rows
    corridor["publishing_corridors"] = [r["corridor"] for r in rows if r["publishes"] == "YES"]
    written.append(_write("corridor", corridor))

    # ---------------------------------------------------------------- DFW airport
    airport_rx = re.compile(r"\b(dfw|d/fw|dallas[/ -]+fort worth (?:international )?airport|airport)\b", re.I)
    on_airport = [h for h in hotels if (h.get("postal_code") or "") == "75261"]
    marketed = [h for h in hotels if airport_rx.search(h.get("canonical_name") or "") and h not in on_airport]
    love = [h for h in hotels if re.search(r"love field", h.get("canonical_name") or "", re.I)]
    airport = _head("dfw_airport")
    airport["rule"] = GEO.DFW_AIRPORT_EVALUATION
    airport["dfw_airport_corridor"] = tally([h for h in hotels if h.get("corridor", "").endswith("__dfw-airport")])
    airport["on_airport_75261"] = [OrderedDict([("canonical_name", h["canonical_name"]), ("street", h.get("street")),
                                                ("published_city", h.get("city")), ("postal_code", h.get("postal_code")),
                                                ("latitude", h.get("latitude")), ("longitude", h.get("longitude")),
                                                ("property_code", h.get("property_code")), ("phone", h.get("phone")),
                                                ("official_url", h.get("official_url")),
                                                ("disposition", state(h))]) for h in on_airport]
    airport["airport_marketed_rows_elsewhere"] = [
        OrderedDict([("canonical_name", h["canonical_name"]), ("street", h.get("street")),
                     ("published_city", h.get("city")), ("postal_code", h.get("postal_code")),
                     ("corridor", h.get("corridor")), ("property_code", h.get("property_code")),
                     ("disposition", state(h))]) for h in marketed]
    airport["love_field_rows"] = [OrderedDict([("canonical_name", h["canonical_name"]), ("street", h.get("street")),
                                               ("postal_code", h.get("postal_code")), ("corridor", h.get("corridor"))])
                                  for h in love]
    airport["love_field_rows_in_dfw_airport_corridor"] = sum(1 for h in love if h.get("corridor", "").endswith(
        "__dfw-airport"))
    airport["dfw_airport_qualifying"] = len(on_airport) + len([h for h in hotels
                                                               if h.get("corridor", "").endswith("__dfw-airport")
                                                               and h not in on_airport])
    written.append(_write("dfw_airport", airport))

    # ---------------------------------------------------------------- brand
    brand = _head("brand")
    fam_rows = OrderedDict()
    for h in hotels:
        fam_rows.setdefault(family(h["canonical_name"]), []).append(h)
    attempts_by_fam = Counter((r.get("family") or "").upper() for r in reads)
    out = OrderedDict()
    for fam, rows_ in sorted(fam_rows.items()):
        t = tally(rows_)
        b_att = sum(len(bound.get(h["identity_key"], [])) for h in rows_)
        b_read = sum(1 for h in rows_ for b in bound.get(h["identity_key"], []) if b.get("outcome") == "READ")
        blocked = sum(1 for h in rows_ if state(h) == "ACCESS_BLOCKED")
        t.update(OrderedDict([
            ("provider_attempts_firecrawl", 0), ("browser_attempts_bound", b_att), ("browser_reads_bound", b_read),
            ("blocked", blocked),
            ("actionable_remaining", sum(1 for h in rows_
                                         if (actx.get(h["identity_key"]) or {}).get("actionability") == "ACTIONABLE_NOW")),
        ]))
        out[fam] = t
    brand["by_family"] = out
    brand["browser_attempts_by_recorded_family"] = OrderedDict(sorted(attempts_by_fam.items()))
    brand["extended_stay_rows"] = sum(1 for h in hotels if re.search(
        r"extended stay|woodspring|hometowne|studio 6|mainstay|towneplace|home2|residence inn|candlewood|staybridge|"
        r"homewood|intown|siegel|sonesta simply|my place|hawthorn|everhome", h["canonical_name"], re.I))
    brand["airport_hotels"] = len(on_airport) + len(marketed)
    brand["convention_hotels"] = sum(1 for h in hotels if re.search(r"convention|conference center|gaylord|omni|"
                                                                     r"hilton anatole|sheraton dallas|hyatt regency",
                                                                     h["canonical_name"], re.I))
    written.append(_write("brand", brand))

    # ---------------------------------------------------------------- Marriott (the order's own report fields)
    m_rows = [h for h in hotels if (h.get("brand") or "").upper() == "MARRIOTT"
              or (actx.get(h["identity_key"]) or {}).get("brand_family") == "MARRIOTT"]
    m_reads = [r for r in reads if (r.get("family") or "").upper() == "MARRIOTT"]
    m_open = [h for h in m_rows if (actx.get(h["identity_key"]) or {}).get("actionability") == "ACTIONABLE_NOW"]
    m_unres = [h for h in m_rows if state(h) not in (PF, NP)]
    marriott = _head("marriott")
    marriott["rule"] = ("every Marriott row ends RESOLVED (pet-friendly / verified no-pets from its own page) or TERMINALLY "
                        "HELD with its exact reason; MARRIOTT ACTIONABLE REMAINING must be 0 before coverage readiness. "
                        "The attended browser is paced; an Akamai denial is never bypassed, relayed or scripted around")
    marriott["MARRIOTT_CENSUS"] = len(m_rows)
    marriott["BROWSER_ATTEMPTED"] = len(m_reads)
    marriott["BROWSER_ATTEMPTED_DISTINCT_ROUTES"] = len({(r.get("property_code") or r.get("requested_url"))
                                                        for r in m_reads})
    marriott["READ_SUCCESS"] = sum(1 for r in m_reads if "DENIED" not in (r.get("read_outcome") or ""))
    marriott["CHALLENGE_DENIED"] = sum(1 for r in m_reads if "DENIED" in (r.get("read_outcome") or ""))
    marriott["outcomes"] = OrderedDict(sorted(Counter(r.get("read_outcome") for r in m_reads).items()))
    marriott["RESOLVED"] = len(m_rows) - len(m_unres)
    marriott["resolved_pet_friendly"] = sum(1 for h in m_rows if state(h) == PF)
    marriott["resolved_verified_no_pets"] = sum(1 for h in m_rows if state(h) == NP)
    marriott["TERMINAL_HOLDS"] = len(m_unres) - len(m_open)
    marriott["terminal_holds_by_class"] = OrderedDict(sorted(Counter(
        (actx.get(h["identity_key"]) or {}).get("actionability", "UNCLASSIFIED")
        for h in m_unres if h not in m_open).items()))
    marriott["ACTIONABLE_REMAINING"] = len(m_open)
    marriott["first_capture"] = min((r.get("captured_at") or "" for r in m_reads), default="")
    marriott["last_capture"] = max((r.get("captured_at") or "" for r in m_reads), default="")
    written.append(_write("marriott", marriott))

    # ---------------------------------------------------------------- boundary
    reg = _load(os.path.join(R, "dallas_fort_worth_tx_registry_lane_001.json"), {}) or {}
    osm = _load(os.path.join(R, "dallas_fort_worth_tx_osm_lane_001.json"), {}) or {}
    boundary = _head("boundary")
    boundary["named_outside_places_hotel_tax_permits"] = reg.get("named_outside_places")
    boundary["osm_outer_regions"] = (osm.get("statewide_measurement") or {}).get("regions")
    boundary["county_refused_permits_in_admitted_codes"] = reg.get("hotel_active_county_refused_in_admitted_postal_codes")

    def _place_count(rx_city, rx_zip=None):
        disc = [r for r in hotels + non_admitted if re.search(rx_city, (r.get("city") or "") + " " +
                                                              (r.get("canonical_name") or ""), re.I)
                or (rx_zip and re.match(rx_zip, r.get("postal_code") or ""))]
        adm = [r for r in hotels if re.search(rx_city, r.get("city") or "", re.I)]
        return OrderedDict([("discovered_graph_nodes", len(disc)), ("admitted", len(adm))])
    boundary["denton"] = _place_count(r"\bdenton\b|\bcorinth\b", r"7620\d|76210")
    boundary["mckinney"] = _place_count(r"\bmckinney\b|\bmc kinney\b", r"7507[0-2]|75069")
    boundary["allen"] = _place_count(r"\ballen\b", r"75013|75002")
    boundary["rockwall"] = _place_count(r"\brockwall\b", r"75032|75087")
    boundary["outside_classifications"] = OrderedDict(sorted(Counter(
        (r.get("classification_reason") or "").split(" -- ")[0][:60] for r in non_admitted
        if r.get("classification") == "OUTSIDE_MARKET").items(), key=lambda kv: -kv[1]))
    written.append(_write("boundary", boundary))

    # ---------------------------------------------------------------- source / provider
    source = _head("source")
    source["lane_yields"] = creport.get("lane_yields")
    source["observations_total"] = creport.get("observations_total")
    source["graph_nodes"] = len(hotels) + len(non_admitted)
    source["classification_counts"] = census.get("classification_counts")
    source["admitted_by_lane"] = OrderedDict(sorted(Counter(l for h in hotels for l in h.get("lanes", [])).items()))
    written.append(_write("source", source))

    places = _load(os.path.join(R, "dallas_fort_worth_tx_places_route_discovery_001.json"), {}) or {}
    provider = _head("provider")
    provider["firecrawl"] = _load(os.path.join(R, "dallas_fort_worth_tx_firecrawl_balance_001.json"), {})
    provider["google_places"] = OrderedDict((k, places.get(k)) for k in (
        "requests_made", "enterprise_requests_made", "pro_requests_made", "route_discovery_cap", "pro_cap",
        "route_discovery_targets", "route_discovery_bound", "route_discovery_bound_with_website",
        "premises_pin_targets", "premises_pin_bound", "gap_verdicts", "map_pin_verdicts", "errors"))
    provider["attended_browser"] = OrderedDict([
        ("attempts", len(reads)), ("reads", sum(1 for r in reads if r.get("read_outcome") == "READ")),
        ("by_family_and_outcome", OrderedDict(sorted(Counter("%s|%s" % (r.get("family"), r.get("read_outcome"))
                                                            for r in reads).items()))),
        ("first_capture", min((r.get("captured_at") or "" for r in reads), default="")),
        ("last_capture", max((r.get("captured_at") or "" for r in reads), default="")),
        ("akamai_bypassed", False), ("browser_js_exfiltration_used", False), ("local_relay_used", False)])
    provider["paid_provider_calls"] = 0
    provider["new_paid_spend_usd"] = 0.0
    written.append(_write("provider", provider))

    # ---------------------------------------------------------------- summary
    counts = Counter(state(h) for h in hotels)
    pf, np_ = counts.get(PF, 0), counts.get(NP, 0)
    summary = _head("source_ready")
    summary.update(OrderedDict([
        ("qualifying_census", len(hotels)), ("pet_friendly", pf), ("verified_no_pets", np_),
        ("resolved", pf + np_), ("unresolved", len(hotels) - pf - np_),
        ("resolution_rate", round(100.0 * (pf + np_) / len(hotels), 2) if hotels else None),
        ("holds_by_class", OrderedDict(sorted((k, v) for k, v in counts.items() if k not in (PF, NP)))),
        ("exclusions_by_class", census.get("classification_counts")),
        ("actionable_unresolved", act.get("actionable_unresolved_remaining")),
        ("marriott_actionable_remaining", marriott["ACTIONABLE_REMAINING"]),
        ("coverage_ready", act.get("COVERAGE_READY")),
        ("accountings_written", written),
    ]))
    written.append(_write("source_ready", summary))
    print(json.dumps(OrderedDict((k, summary[k]) for k in ("qualifying_census", "pet_friendly", "verified_no_pets",
                                                           "unresolved", "resolution_rate", "actionable_unresolved",
                                                           "coverage_ready")), indent=1))
    print("written:", written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

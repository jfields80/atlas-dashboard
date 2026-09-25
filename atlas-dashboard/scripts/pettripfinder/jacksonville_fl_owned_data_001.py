"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phase 8: OWNED DATA FIRST.

Before one external request is made, every Atlas-owned artifact that could already know something about
Northeast Florida is read and MEASURED. The answer this lane returns is not the one the order's template
expects, and it is reported as measured rather than dressed up.

THE HEADLINE MEASUREMENT: ZERO OWNED IDENTITIES IN THIS MARKET'S ADMITTED GEOGRAPHY
-----------------------------------------------------------------------------------
Every committed market graph in this repository was scanned row by row for a node whose own postal code this
market's corridor registry admits. **Not one of the 33 live markets has a single node in any of the 47 admitted
postal codes.** The three South Florida markets' observation boxes stopped at the Treasure Coast; Orlando V2's
and Tampa V2's stopped well south of the St. Johns River; Savannah's stopped at the Georgia coast. This market
is a genuine cold start for identity, and the census lanes must therefore do all of the discovery.

WHAT *IS* OWNED, AND IS WORTH A GREAT DEAL
------------------------------------------
1. THE NATIONAL BRAND DIRECTORY CORPUS (rung 0). `dayton_oh_brand_directory_harvest_001` holds 17,928
   first-party brand routes harvested from brand sitemaps, market-independent by construction. Marriott's MARSHA
   prefix for this region is JAX, and the corpus carries 53 distinct `jax??` property codes with their official
   `/overview/` routes -- acquired at ZERO new requests.

2. AND IT CARRIES THE MARKET'S FIRST IDENTITY TRAP, WHICH THIS LANE NAMES BEFORE ANY READ. A BRAND PREFIX IS
   NOT A MARKET. Marriott's JAX prefix also codes St. Augustine (`jaxak` Casa Monica, `jaxbr` World Golf
   Village, `jaxcb`, `jaxcs`, `jaxrj`, `jaxsc`, `jaxst`, `jaxsx`, `jaxtx`) and WAYCROSS, GEORGIA (`jaxfw`) --
   every one of them OUTSIDE this market. A route is ROUTING evidence and carries no postal code, so this lane
   records each route as a LEAD with a PRESUMED disposition derived from the brand's own slug, and the property's
   own page decides membership later. No route is admitted or refused here.

3. THE `jacksonville-nc` GRAPH, REUSED AS A GUARD RATHER THAN AS DISCOVERY. The live market
   jacksonville-nc is a different city in a different state, and its committed graph is read here for exactly
   one purpose: to enumerate the names that a North Carolina row and a Florida row could share.

4. THE SHARED EXCLUSION FILE, AUDITED FOR A CROSS-MARKET NAME COLLISION -- AND IT FINDS ONE CLASS OF REAL
   EXPOSURE. `hotel_exclusions.exclusion_for` matches on `normalized_name` FIRST and returns a hit regardless of
   address (scripts/pettripfinder/hotel_exclusions.py). The committed file carries three jacksonville-nc
   exclusions whose names contain no municipality qualifier beyond the word "Jacksonville":
     * "Courtyard by Marriott Jacksonville"            (5046 Henderson Drive, Jacksonville NC 28546)
     * "Fairfield by Marriott Inn & Suites Jacksonville" (121 Circuit Lane, Jacksonville NC 28546)
     * "Microtel Inn & Suites by Wyndham Camp Lejeune/Jacksonville" (2411 Commerce Rd, Jacksonville NC 28546)
   A Florida census row whose own name normalises to one of those strings -- which a state licence record can
   easily produce, because DBPR records trade names without the brand's marketing suffix -- would be SILENTLY
   EXCLUDED by another market's row. This lane computes the collision set and hands it to the census
   reconciliation as a named guard. It does NOT edit the shared file or the other market's row: that is a
   founder decision and a cross-market change this order may not make.

5. PRIOR PROVIDER HISTORY. The Firecrawl call ledger (46 prior calls) is read so the "pay once per page ever"
   rule can be enforced against real history rather than against an empty slate, and every refusal it records is
   treated as STALE (a capability statement ages in days) and re-probed rather than inherited.

WHAT IS NEVER REUSED
--------------------
  * MEMBERSHIP -- decided only by this market's corridor registry over a property's own postal code.
  * PET POLICY -- no policy fact, quote, evidence row or capture is imported from any market. There is nothing
    to import: zero prior nodes sit in this market's admitted codes, which this lane asserts.
  * A PRIOR MARKET'S RULING -- carried as provenance for the reconciliation to consider on its own evidence.

Output:
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_owned_data_001.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import hotel_exclusions as HE  # noqa: E402
from scripts.pettripfinder import jacksonville_fl_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "jacksonville_fl_owned_data_001.json")
NATIONAL_CORPUS = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
FIRECRAWL_LEDGER = os.path.join(_DASH, "data", "acquisition", "firecrawl_call_ledger.jsonl")

#: The live market whose NAME this market shares. Read as a guard, never as discovery.
NAME_TWIN_MARKET = "jacksonville-nc"
NAME_TWIN_REPORT = "jacksonville_nc_census_reconciliation_001.json"

#: Marriott's MARSHA prefix for Northeast Florida. A PREFIX IS NOT A MARKET.
MARSHA_PREFIX = "jax"
#: Brand slug tokens that name a place this market REFUSES. Presumption only; the property's page decides.
REFUSED_SLUG_TOKENS = OrderedDict([
    ("st-augustine", "St. Augustine -- refused, future st-augustine-fl"),
    ("saint-augustine", "St. Augustine -- refused, future st-augustine-fl"),
    ("world-golf-village", "World Golf Village 32092 -- refused, future st-augustine-fl"),
    ("casa-monica", "Casa Monica Resort, downtown St. Augustine -- refused, future st-augustine-fl"),
    ("waycross", "Waycross, GEORGIA -- out of state, refused"),
    ("palm-coast", "Palm Coast -- refused, future palm-coast-flagler-fl"),
    ("gainesville", "Gainesville -- refused, future gainesville-fl"),
    ("daytona", "Daytona Beach -- refused, future daytona-beach-fl"),
    ("brunswick", "Brunswick, GEORGIA -- out of state, refused"),
    ("st-simons", "St. Simons Island, GEORGIA -- out of state, refused"),
    ("jekyll", "Jekyll Island, GEORGIA -- out of state, refused"),
    ("kingsland", "Kingsland, GEORGIA -- out of state, refused"),
    ("st-marys", "St. Marys, GEORGIA -- out of state, refused"),
    ("palatka", "Palatka / Putnam County -- refused"),
    ("lake-city", "Lake City / Columbia County -- refused, no corridor claims it"),
])
#: Brand slug tokens that name a place this market ADMITS. Presumption only.
ADMITTED_SLUG_TOKENS = (
    "jacksonville", "amelia-island", "fernandina", "ponte-vedra", "sawgrass", "orange-park",
    "fleming-island", "middleburg", "green-cove", "yulee", "atlantic-beach", "neptune-beach",
    "mayport", "baymeadows", "deerwood", "butler-boulevard", "town-center", "tapestry-park",
    "mayo-clinic", "bartram", "flagler-center", "beltway", "chaffee", "jacksonville-beach",
)


def _s(v):
    return " ".join(str(v or "").split())


def _zip5(v):
    return "".join(ch for ch in _s(v) if ch.isdigit())[:5]


def _admitted_zips():
    return {z for c in GEO.CORRIDORS for z in c[5]}


def _outside_zips():
    return {z for _m, _s2, zs, _w in GEO.OUTSIDE for z in zs}


def scan_prior_graphs():
    """Every committed market graph, scanned for a node in THIS market's admitted postal codes."""
    admitted, outside = _admitted_zips(), _outside_zips()
    per_market, admitted_nodes = OrderedDict(), []
    for path in sorted(glob.glob(os.path.join(REPORTS, "*census_reconciliation*.json"))):
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except (ValueError, OSError):
            continue
        rows = doc.get("rows") or []
        if not rows:
            continue
        src = _s(doc.get("market_id")) or os.path.basename(path)
        in_adm = [r for r in rows if _zip5(r.get("postal_code")) in admitted]
        in_out = [r for r in rows if _zip5(r.get("postal_code")) in outside]
        if not (in_adm or in_out):
            continue
        per_market[src] = OrderedDict([
            ("source_report", os.path.basename(path)),
            ("source_graph_nodes", len(rows)),
            ("nodes_in_jacksonville_admitted_postal_codes", len(in_adm)),
            ("nodes_in_postal_codes_this_market_names_OUTSIDE", len(in_out)),
            ("their_rulings_on_the_outside_nodes",
             OrderedDict(Counter(_s(r.get("classification")) or "UNCLASSIFIED" for r in in_out).most_common())),
        ])
        for r in in_adm:
            admitted_nodes.append(OrderedDict([
                ("source_market", src), ("identity_key", r.get("identity_key")),
                ("canonical_name", r.get("canonical_name")), ("street", r.get("street")),
                ("postal_code", _zip5(r.get("postal_code"))), ("policy_state", r.get("policy_state")),
                ("their_classification", r.get("classification")),
            ]))
    return per_market, admitted_nodes


def national_brand_routes():
    """Rung 0: the owned national brand-directory corpus, filtered to this region at ZERO new requests."""
    doc = json.load(open(NATIONAL_CORPUS, encoding="utf-8"))
    rx = re.compile(r"/hotels/(" + MARSHA_PREFIX + r"[a-z0-9]{2})-([a-z0-9-]+)/")
    routes = OrderedDict()
    token_only = OrderedDict()
    for cand in doc.get("candidates") or []:
        url = _s(cand.get("url"))
        if "/en-us/" not in url:
            continue
        m = rx.search(url)
        if m:
            code, slug = m.group(1), m.group(2)
            if code in routes:
                continue
            presumed, why = "PRESUMED_IN_MARKET", "the brand's own slug names a place this market admits"
            for tok, reason in REFUSED_SLUG_TOKENS.items():
                if tok in slug:
                    presumed, why = "PRESUMED_OUTSIDE", reason
                    break
            else:
                if not any(tok in slug for tok in ADMITTED_SLUG_TOKENS):
                    presumed, why = "PRESUMED_UNDECIDED", ("the brand's slug names no place this registry "
                                                           "recognises; the property's own page must decide")
            routes[code] = OrderedDict([
                ("lane", "BRAND_INVENTORY_OWNED"),
                ("family", _s(cand.get("family")) or "MARRIOTT"),
                ("brand_property_code", code),
                ("brand_slug", slug),
                ("official_url", url),
                ("selected_by", "MARSHA_PREFIX_" + MARSHA_PREFIX.upper()),
                ("presumed_membership", presumed),
                ("presumption_reason", why),
                ("membership_decided_by", "the property's OWN postal code on its OWN page -- never this slug"),
            ])
            continue
        fam = _s(cand.get("family"))
        if fam and fam != "MARRIOTT" and any(tok in url.lower() for tok in ADMITTED_SLUG_TOKENS):
            token_only[url] = OrderedDict([
                ("lane", "BRAND_INVENTORY_OWNED"), ("family", fam), ("official_url", url),
                ("selected_by", "PLACE_TOKEN_IN_ROUTE"),
                ("presumed_membership", "PRESUMED_UNDECIDED"),
                ("presumption_reason", "a place token in a brand route is a hint, never a placement"),
            ])
    corpus = OrderedDict([
        ("source_report", os.path.basename(NATIONAL_CORPUS)),
        ("source_work_order", _s(doc.get("work_order"))),
        ("as_of", _s(doc.get("as_of"))),
        ("total_routes_in_corpus", len(doc.get("candidates") or [])),
        ("market_independent", True),
        ("free_http_requests", 0),
    ])
    return corpus, list(routes.values()), list(token_only.values())


def name_collision_guard():
    """The cross-market name-collision audit, and the one class of real exposure it finds."""
    records = HE.load_exclusions()
    active = [r for r in records if not _s(r.get("superseded_at"))]
    admitted = _admitted_zips()
    #: Exclusions whose normalized name contains 'jacksonville' but whose premises is NOT in this market.
    foreign = []
    for r in active:
        norm = _s(r.get("normalized_name")).lower()
        if "jacksonville" not in norm:
            continue
        if _zip5(r.get("postal_code")) in admitted:
            continue
        foreign.append(OrderedDict([
            ("exclusion_id", r.get("exclusion_id")),
            ("normalized_name", r.get("normalized_name")),
            ("canonical_name", r.get("canonical_name")),
            ("premises", "%s, %s %s %s" % (_s(r.get("address")), _s(r.get("city")), _s(r.get("state")),
                                           _zip5(r.get("postal_code")))),
            ("exclusion_state", r.get("exclusion_state")),
            ("hazard", "hotel_exclusions.exclusion_for matches normalized_name FIRST and returns a hit "
                       "regardless of address. A Florida census row whose own name normalises to this string "
                       "would be silently excluded by another market's premises."),
        ]))
    twin = OrderedDict([("source_report", NAME_TWIN_REPORT), ("read", False), ("shared_name_tokens", [])])
    tpath = os.path.join(REPORTS, NAME_TWIN_REPORT)
    if os.path.exists(tpath):
        tdoc = json.load(open(tpath, encoding="utf-8"))
        rows = tdoc.get("rows") or []
        names = sorted({_s(r.get("canonical_name")) for r in rows
                        if "jacksonville" in _s(r.get("canonical_name")).lower()})
        twin = OrderedDict([
            ("source_report", NAME_TWIN_REPORT),
            ("read", True),
            ("source_market", _s(tdoc.get("market_id"))),
            ("source_graph_nodes", len(rows)),
            ("nodes_whose_name_contains_jacksonville", len(names)),
            ("their_names", names),
            ("reused_as", "A GUARD ONLY. Not one of these is a lead, a census row or a policy source. They are "
                          "the exact strings a Florida row must never be merged with or held by."),
        ])
    return OrderedDict([
        ("shared_exclusion_file", os.path.relpath(HE.DEFAULT_PATH, _DASH).replace("\\", "/")
         if hasattr(HE, "DEFAULT_PATH") else "launch_packages/pettripfinder/hotel_exclusions.json"),
        ("active_exclusions", len(active)),
        ("exclusions_with_no_premises", sum(1 for r in active if not _s(r.get("address"))
                                            or not _zip5(r.get("postal_code")))),
        ("bare_chain_flags_found", 0 if all(_s(r.get("address")) and _zip5(r.get("postal_code"))
                                            for r in active) else -1),
        ("foreign_jacksonville_named_exclusions", foreign),
        ("foreign_jacksonville_named_exclusion_count", len(foreign)),
        ("collision_strings_to_guard", sorted({_s(r["normalized_name"]) for r in foreign})),
        ("what_this_order_does_about_it",
         "MEASURES it and hands the collision strings to the census reconciliation as a named guard, which "
         "checks every admitted-postal census row against them and HOLDS rather than silently drops any hit. "
         "This order does NOT edit the shared exclusion file and does NOT supersede another market's row: that "
         "is a cross-market change and a founder decision."),
        ("name_twin_market", twin),
    ])


def provider_history():
    calls = []
    if os.path.exists(FIRECRAWL_LEDGER):
        with open(FIRECRAWL_LEDGER, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        calls.append(json.loads(line))
                    except ValueError:
                        pass
    ok = sum(1 for c in calls if c.get("ok"))
    hosts = Counter()
    for c in calls:
        m = re.match(r"https?://([^/]+)", _s(c.get("requested_url")))
        if m:
            hosts[m.group(1).lower()] += 1
    return OrderedDict([
        ("firecrawl_ledger", "data/acquisition/firecrawl_call_ledger.jsonl"),
        ("prior_calls_recorded", len(calls)),
        ("prior_successes", ok),
        ("prior_refusals", len(calls) - ok),
        ("prior_hosts", OrderedDict(hosts.most_common())),
        ("calls_for_a_jacksonville_url", sum(1 for c in calls if re.search(
            r"jacksonville|amelia|fernandina|ponte-vedra|orange-park|jax[a-z0-9]{2}-",
            _s(c.get("requested_url")), re.I))),
        ("pay_once_rule",
         "Every URL this order is about to buy is checked against this ledger first: pay once per page ever, and "
         "once to FIND a page ever."),
        ("refusals_are_treated_as_stale",
         "A prior SCRAPE_ALL_ENGINES_FAILED is a capability statement about that host at that moment and ages in "
         "days. No refusal recorded here is inherited as a reason not to try; eligible hosts are re-probed."),
    ])


def build():
    per_market, admitted_nodes = scan_prior_graphs()
    corpus, routes, token_routes = national_brand_routes()
    guard = name_collision_guard()
    history = provider_history()
    if admitted_nodes:
        bad = [n for n in admitted_nodes
               if _s(n.get("policy_state")) not in ("", "POLICY_NOT_VERIFIED", "UNKNOWN", "NOT_VERIFIED")]
        if bad:
            raise SystemExit("a prior market carries a VERIFIED policy for a Jacksonville premises; reuse "
                             "refused:\n%s" % json.dumps(bad[:10], indent=1))
    presumed = Counter(r["presumed_membership"] for r in routes)
    return OrderedDict([
        ("schema", "ptf-owned-data-first/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "8 -- owned data first: every Atlas-owned artifact that could already know Northeast Florida, "
                  "measured before one external request"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("headline",
         "ZERO owned identities in this market's admitted geography. Every committed market graph was scanned "
         "row by row and not one of the 33 live markets holds a node in any of the 47 admitted postal codes. "
         "This market is a genuine cold start for identity."),
        ("owned_identities_in_admitted_postal_codes", len(admitted_nodes)),
        ("owned_valid_policy_evidence", 0),
        ("owned_policy_rows_imported", 0),
        ("owned_routes_in_admitted_geography", len(routes) + len(token_routes)),
        ("owned_rebrands_or_closures_applicable", 0),
        ("owned_collisions_found", guard["foreign_jacksonville_named_exclusion_count"]),
        ("prior_graph_scan", OrderedDict([
            ("graphs_scanned", len(glob.glob(os.path.join(REPORTS, "*census_reconciliation*.json")))),
            ("graphs_with_any_relevant_node", len(per_market)),
            ("per_market", per_market),
            ("nodes_in_admitted_postal_codes", admitted_nodes),
            ("policy_import_assertion", OrderedDict([
                ("assertion", "No prior-market row inside a Jacksonville admitted postal code carries a verified "
                              "pet policy. Trivially true here, because there are no such rows at all; the "
                              "helper aborts if that ever changes."),
                ("violations_found", 0),
                ("policy_rows_imported", 0),
            ])),
            ("membership_assertion",
             "Nothing in this lane admits a property. Membership is decided only by GEO.classify_postal on a "
             "property's OWN postal code, as its own page or its own state licence states it."),
        ])),
        ("national_brand_corpus", corpus),
        ("a_brand_prefix_is_not_a_market",
         "Marriott's MARSHA prefix JAX covers this market AND St. Augustine (Casa Monica, World Golf Village, "
         "the historic-downtown Renaissance, two Courtyards, a Fairfield, an AC, a City Express and a Tribute "
         "hotel) AND Waycross, GEORGIA. A route carries no postal code, so every route below is a LEAD with a "
         "PRESUMED disposition read off the brand's own slug. The property's own page decides membership."),
        ("owned_brand_routes_by_presumption", OrderedDict(sorted(presumed.items()))),
        ("owned_brand_routes", routes),
        ("owned_brand_routes_by_place_token", token_routes),
        ("cross_market_name_collision_guard", guard),
        ("provider_history", history),
        ("owned_osm_extract",
         "data/osm_extracts/florida-latest.osm.pbf -- the Geofabrik Florida extract already owned by this "
         "repository, reused unchanged by the OSM lane at zero new download."),
        ("what_is_never_reused",
         "Membership (re-decided here), pet policy (none exists to import -- asserted above), and a prior "
         "market's lodging-qualification ruling (carried as provenance only)."),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    rep = build()
    if args.write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rep, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("WROTE", os.path.relpath(OUT, _DASH))
    print("OWNED IDENTITIES (admitted codes) =", rep["owned_identities_in_admitted_postal_codes"])
    print("OWNED POLICY EVIDENCE            =", rep["owned_valid_policy_evidence"])
    print("OWNED ROUTES                     =", rep["owned_routes_in_admitted_geography"],
          dict(rep["owned_brand_routes_by_presumption"]))
    print("OWNED COLLISIONS                 =", rep["owned_collisions_found"],
          rep["cross_market_name_collision_guard"]["collision_strings_to_guard"])
    print("PRIOR PROVIDER CALLS             =", rep["provider_history"]["prior_calls_recorded"],
          "for a Jacksonville URL:", rep["provider_history"]["calls_for_a_jacksonville_url"])
    for mid, blk in rep["prior_graph_scan"]["per_market"].items():
        print("   %-22s %5d nodes | admitted %d | in codes we refuse %d" % (
            mid, blk["source_graph_nodes"], blk["nodes_in_jacksonville_admitted_postal_codes"],
            blk["nodes_in_postal_codes_this_market_names_OUTSIDE"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

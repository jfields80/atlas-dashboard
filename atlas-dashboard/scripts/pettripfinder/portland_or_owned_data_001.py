"""PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001 -- Phase 9: OWNED DATA FIRST.

Before new acquisition, every Atlas-owned artifact that could already know something about Portland is read and
MEASURED, and the answer is reported as measured.

THE HEADLINE MEASUREMENT: THE FIRST OREGON MARKET
------------------------------------------------
Every committed market graph in this repository was scanned row by row for a node whose own postal code this
market's corridor registry admits, or any Oregon / south-west Washington (986) code at all. Portland is the first
Oregon market; the one live Pacific Northwest market (seattle-wa) observed a box that ends at 46.95 N, north of
Longview, so the expected answer is ZERO owned identities and zero owned policy -- and the scan proves it rather than
assuming it.

WHAT *IS* OWNED
---------------
1. THE NATIONAL BRAND DIRECTORY CORPUS (rung 0). ``dayton_oh_brand_directory_harvest_001`` holds 17,928
   first-party brand routes harvested from brand sitemaps. Marriott codes the Portland metro PDX** -- and the PDX
   prefix also reaches Salem, Newberg and Vancouver, Washington -- so the corpus is filtered by that prefix and by
   place tokens, and every route is a LEAD with a PRESUMED disposition read off the brand's own slug. The property's
   own page decides membership later. PORTLAND, MAINE is coded PWM** and is NEVER selected: its hotels carry the same
   words ("Courtyard Portland Downtown Waterfront", "Residence Inn Portland Downtown Waterfront", "Courtyard Portland
   Airport") as Oregon hotels, which is the name trap at its sharpest.

2. EVERY LIVE MARKET'S PUBLISHED IDENTITY NAMES, REUSED AS A GUARD, NEVER AS DISCOVERY. No live market has
   Oregon premises, so the cross-market exposure is a NAME: a Portland row published under a bare chain name
   ("Hampton Inn & Suites", "Home2 Suites by Hilton") would claim an identity another market already publishes (the
   Jacksonville rule-G finding). The set of normalised canonical names every registered market publishes is
   collected here and handed to the census as the collision guard.

3. THE SHARED EXCLUSION FILE, audited for exclusions whose normalised name carries a Portland place word but whose
   premises is not in this market (``hotel_exclusions.exclusion_for`` matches the NAME first and returns a hit
   regardless of address -- every Portland, MAINE exclusion would be such a hazard), and for exclusions with no
   premises at all (a bare flag that would hold a row in any market).

4. PRIOR PROVIDER HISTORY. Every worktree's Firecrawl call ledger is read (read only) so "pay once per page ever"
   is enforced against real history; every refusal is treated as STALE and re-probed rather than inherited.

5. OWNED OSM EXTRACT: the Washington extract the Seattle order downloaded is reused (Vancouver / Clark County); no
   Oregon extract was owned, and this order downloaded Geofabrik's Oregon extract once, free (see the OSM lane).

WHAT IS NEVER REUSED
--------------------
  * MEMBERSHIP -- decided only by this market's corridor registry over a property's own postal code.
  * PET POLICY -- no policy fact, quote, evidence row or capture is imported from any market. This lane REFUSES to
    run if any prior market carries a verified policy for a premises in this market's admitted codes.

Output:
  launch_packages/pettripfinder/markets/reports/portland_or_owned_data_001.json
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
from scripts.pettripfinder import portland_or_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001"
MARKET_ID = "portland-or"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS_DIR = os.path.join(PKG, "identity_census")
OUT = os.path.join(REPORTS, "portland_or_owned_data_001.json")
NATIONAL_CORPUS = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
#: Every worktree keeps its own gitignored Firecrawl ledger; the union is the factory's provider history.
LEDGER_GLOB = os.path.join(os.path.dirname(os.path.dirname(_DASH)), "Atlas*", "atlas-dashboard", "data",
                           "acquisition", "firecrawl_call_ledger.jsonl")

MARSHA_PREFIXES = ("pdx",)
REFUSED_SLUG_TOKENS = OrderedDict([
    ("salem", "Salem -- future salem-or"),
    ("keizer", "Keizer -- future salem-or"),
    ("woodburn", "Woodburn -- future salem-or"),
    ("eugene", "Eugene -- future eugene-or"),
    ("springfield", "Springfield, OR -- future eugene-or"),
    ("hood-river", "Hood River -- future columbia-gorge"),
    ("cascade-locks", "Cascade Locks -- future columbia-gorge"),
    ("the-dalles", "The Dalles -- future columbia-gorge"),
    ("stevenson", "Stevenson -- future columbia-gorge"),
    ("washougal", "Washougal -- future columbia-gorge"),
    ("camas", "Camas -- refused after careful evaluation"),
    ("mt-hood", "Mount Hood -- future mount-hood"),
    ("mount-hood", "Mount Hood -- future mount-hood"),
    ("government-camp", "Government Camp -- future mount-hood"),
    ("welches", "Welches -- future mount-hood"),
    ("sandy", "Sandy -- future mount-hood"),
    ("seaside", "Seaside -- future oregon-coast"),
    ("cannon-beach", "Cannon Beach -- future oregon-coast"),
    ("astoria", "Astoria -- future oregon-coast"),
    ("lincoln-city", "Lincoln City -- future oregon-coast"),
    ("newport", "Newport -- future oregon-coast"),
    ("bend", "Bend -- future bend-or"),
    ("redmond", "Redmond, OR -- future bend-or"),
    ("newberg", "Newberg -- refused after careful evaluation"),
    ("mcminnville", "McMinnville -- refused after careful evaluation"),
    ("dundee", "Dundee -- refused after careful evaluation"),
    ("canby", "Canby -- refused after careful evaluation"),
    ("st-helens", "St Helens -- refused after careful evaluation"),
    ("scappoose", "Scappoose -- refused after careful evaluation"),
    ("longview", "Longview -- future longview-kelso"),
    ("kelso", "Kelso -- future longview-kelso"),
    ("battle-ground", "Battle Ground -- refused after careful evaluation"),
    ("ridgefield", "Ridgefield -- refused after careful evaluation"),
    ("albany", "Albany, OR -- refused by prefix"),
    ("corvallis", "Corvallis -- refused by prefix"),
    ("maine", "Portland, MAINE -- not this market"),
])
ADMITTED_SLUG_TOKENS = (
    "portland", "beaverton", "hillsboro", "tigard", "lake-oswego", "oswego", "gresham", "tualatin", "wilsonville",
    "clackamas", "happy-valley", "troutdale", "fairview", "wood-village", "milwaukie", "oregon-city", "west-linn",
    "gladstone", "sherwood", "forest-grove", "cornelius", "vancouver", "pearl", "lloyd", "riverplace",
    "jantzen", "hayden-island", "cascade-station",
)
#: Place words whose appearance in ANOTHER market's exclusion name would be a Portland hazard.
PHX_PLACE_WORDS = ("portland", "beaverton", "hillsboro", "tigard", "lake oswego", "gresham", "tualatin",
                   "wilsonville", "clackamas", "happy valley", "troutdale", "milwaukie", "oregon city", "west linn",
                   "sherwood", "forest grove", "vancouver", "jantzen", "lloyd center", "pearl district")


def _s(v):
    return " ".join(str(v or "").split())


def _zip5(v):
    return "".join(ch for ch in _s(v) if ch.isdigit())[:5]


def _admitted_zips():
    return {z for c in GEO.CORRIDORS for z in c[5]}


def scan_prior_graphs():
    """Every committed market graph, scanned for a node in THIS market's admitted postal codes or its refused
    neighbours (every Oregon prefix and the south-west Washington 986 prefix)."""
    admitted = _admitted_zips()
    ca_prefix = ("97", "986")
    per_market, admitted_nodes = OrderedDict(), []
    graphs = sorted(glob.glob(os.path.join(REPORTS, "*census_reconciliation*.json")))
    for path in graphs:
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except (ValueError, OSError):
            continue
        rows = doc.get("rows") or []
        if not rows:
            continue
        src = _s(doc.get("market_id")) or os.path.basename(path)
        in_adm = [r for r in rows if _zip5(r.get("postal_code")) in admitted]
        in_ca = [r for r in rows if _zip5(r.get("postal_code")).startswith(ca_prefix)]
        if not (in_adm or in_ca):
            continue
        per_market[src] = OrderedDict([
            ("source_report", os.path.basename(path)),
            ("source_graph_nodes", len(rows)),
            ("nodes_in_portland_admitted_postal_codes", len(in_adm)),
            ("nodes_in_oregon_or_sw_washington_codes", len(in_ca)),
        ])
        for r in in_adm:
            admitted_nodes.append(OrderedDict([
                ("source_market", src), ("identity_key", r.get("identity_key")),
                ("source_classification", r.get("classification")),
                ("canonical_name", r.get("canonical_name")), ("street", r.get("street")),
                ("postal_code", _zip5(r.get("postal_code"))), ("policy_state", r.get("policy_state")),
            ]))
    return len(graphs), per_market, admitted_nodes


def national_brand_routes():
    """Rung 0: the owned national brand-directory corpus, filtered to this region at ZERO new requests."""
    doc = json.load(open(NATIONAL_CORPUS, encoding="utf-8"))
    rx = re.compile(r"/hotels/((?:%s)[a-z0-9]{2})-([a-z0-9-]+)/" % "|".join(MARSHA_PREFIXES))
    routes = OrderedDict()
    token_only = OrderedDict()
    for cand in doc.get("candidates") or []:
        url = _s(cand.get("url"))
        m = rx.search(url)
        if m and _s(cand.get("family")) in ("", "MARRIOTT"):
            code, slug = m.group(1), m.group(2)
            if code in routes:
                continue
            if "/en-us/" not in url:
                url = re.sub(r"/[a-z]{2}(-[a-z]{2})?/hotels/", "/en-us/hotels/", url, count=1)
            presumed, why = "PRESUMED_IN_MARKET", "the brand's own slug names a place this market admits"
            refused_tok = next(((t, r) for t, r in REFUSED_SLUG_TOKENS.items() if t in slug), None)
            admitted_city = [t for t in ADMITTED_SLUG_TOKENS if t != "portland" and t in slug]
            if refused_tok and admitted_city:
                # a slug naming both an admitted and a refused city decides nothing -- the property's own page does
                presumed, why = "PRESUMED_UNDECIDED", ("the slug names an admitted place (%s) and a refused one (%s)"
                                                       % (admitted_city[0], refused_tok[0]))
            elif refused_tok:
                presumed, why = "PRESUMED_OUTSIDE", refused_tok[1]
            else:
                if not any(tok in slug for tok in ADMITTED_SLUG_TOKENS):
                    presumed, why = "PRESUMED_UNDECIDED", ("the brand's slug names no place this registry "
                                                           "recognises; the property's own page must decide")
            routes[code] = OrderedDict([
                ("lane", "BRAND_INVENTORY_OWNED"), ("family", "MARRIOTT"), ("brand_property_code", code),
                ("brand_slug", slug), ("official_url", url),
                ("selected_by", "MARSHA_PREFIX_" + "_".join(p.upper() for p in MARSHA_PREFIXES)),
                ("presumed_membership", presumed), ("presumption_reason", why),
                ("membership_decided_by", "the property's OWN postal code on its OWN page -- never this slug"),
            ])
            continue
        fam = _s(cand.get("family"))
        if fam and fam != "MARRIOTT" and (any(tok in url.lower() for tok in ADMITTED_SLUG_TOKENS) and
                                          ("oregon" in url.lower() or "-or" in url.lower() or
                                           "/or/" in url.lower() or "/us/or" in url.lower() or
                                           "vancouver-wa" in url.lower() or "/wa/vancouver" in url.lower() or
                                           "washington/vancouver" in url.lower())):
            token_only[url] = OrderedDict([
                ("lane", "BRAND_INVENTORY_OWNED"), ("family", fam), ("official_url", url),
                ("selected_by", "PLACE_TOKEN_IN_ROUTE"), ("presumed_membership", "PRESUMED_UNDECIDED"),
                ("presumption_reason", "a place token in a brand route is a hint, never a placement"),
            ])
    corpus = OrderedDict([
        ("source_report", os.path.basename(NATIONAL_CORPUS)), ("source_work_order", _s(doc.get("work_order"))),
        ("as_of", _s(doc.get("as_of"))), ("total_routes_in_corpus", len(doc.get("candidates") or [])),
        ("market_independent", True), ("free_http_requests", 0),
    ])
    return corpus, list(routes.values()), list(token_only.values())


def live_identity_names():
    """Every REGISTERED market's published canonical names, normalised -- the cross-market collision guard."""
    names = OrderedDict()
    for path in sorted(glob.glob(os.path.join(CENSUS_DIR, "*.json"))):
        base = os.path.basename(path)[:-5]
        if any(t in base for t in ("proposed", "quarantine", "boundary", "recovery", "policy-capture")):
            continue
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except (ValueError, OSError):
            continue
        rows = doc.get("hotels") or doc.get("rows") or []
        if not isinstance(rows, list):
            continue
        for r in rows:
            if not isinstance(r, dict):
                continue
            nm = _s(r.get("canonical_name") or r.get("name"))
            if not nm:
                continue
            key = normalize_name(nm)
            names.setdefault(key, set()).add(_s(doc.get("market_id")) or base)
    return OrderedDict((k, sorted(v)) for k, v in sorted(names.items()))


def name_collision_guard():
    records = HE.load_exclusions()
    active = [r for r in records if not _s(r.get("superseded_at"))]
    admitted = _admitted_zips()
    foreign = []
    for r in active:
        norm = _s(r.get("normalized_name")).lower()
        if not any(w in norm for w in PHX_PLACE_WORDS):
            continue
        if _zip5(r.get("postal_code")) in admitted:
            continue
        foreign.append(OrderedDict([
            ("exclusion_id", r.get("exclusion_id")), ("normalized_name", r.get("normalized_name")),
            ("premises", "%s, %s %s %s" % (_s(r.get("address")), _s(r.get("city")), _s(r.get("state")),
                                           _zip5(r.get("postal_code")))),
        ]))
    bare = [OrderedDict([("exclusion_id", r.get("exclusion_id")), ("normalized_name", r.get("normalized_name"))])
            for r in active if not _s(r.get("address")) or not _zip5(r.get("postal_code"))]
    live = live_identity_names()
    return OrderedDict([
        ("shared_exclusion_file", "launch_packages/pettripfinder/hotel_exclusions.json"),
        ("active_exclusions", len(active)),
        ("exclusions_with_no_premises", bare),
        ("exclusions_with_no_premises_count", len(bare)),
        ("foreign_portland_named_exclusions", foreign),
        ("foreign_portland_named_exclusion_count", len(foreign)),
        ("collision_strings_to_guard", sorted({_s(r["normalized_name"]) for r in foreign} |
                                              {_s(r["normalized_name"]) for r in bare})),
        ("live_identity_names", OrderedDict([
            ("what_it_is", "The normalised canonical name of every identity every registered market publishes. "
                           "No live market has Oregon or Vancouver premises, so a Portland row can collide with a "
                           "live market ONLY by name; the census holds any Portland row whose own normalised name is "
                           "already published elsewhere."),
            ("markets_read", sorted({m for ms in live.values() for m in ms})),
            ("distinct_names", len(live)),
        ])),
        ("what_this_order_does_about_it",
         "MEASURES it and hands the strings to the census reconciliation as a named guard, which HOLDS rather "
         "than silently drops any hit. This order does NOT edit the shared exclusion file."),
    ]), live


def provider_history():
    calls = []
    ledgers = sorted(glob.glob(LEDGER_GLOB))
    for path in ledgers:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        calls.append(json.loads(line))
                    except ValueError:
                        pass
    ok = sum(1 for c in calls if c.get("ok"))
    return OrderedDict([
        ("firecrawl_ledgers_read", len(ledgers)),
        ("prior_calls_recorded", len(calls)),
        ("prior_successes", ok),
        ("prior_refusals", len(calls) - ok),
        ("calls_for_a_portland_url", sum(1 for c in calls if re.search(
            r"portland(?!-me|-maine)|beaverton|hillsboro|/hotels/pdx[a-z0-9]{2}-|tigard|lake-?oswego|gresham|"
            r"troutdale|clackamas|vancouver-wa", _s(c.get("requested_url")), re.I))),
        ("pay_once_rule", "Every URL this order is about to buy is checked against these ledgers first."),
        ("refusals_are_treated_as_stale", "A prior refusal ages in days and is re-probed, never inherited."),
    ])


def build():
    graphs, per_market, admitted_nodes = scan_prior_graphs()
    corpus, routes, token_routes = national_brand_routes()
    guard, live = name_collision_guard()
    history = provider_history()
    bad = [n for n in admitted_nodes
           if _s(n.get("policy_state")) not in ("", "POLICY_NOT_VERIFIED", "UNKNOWN", "NOT_VERIFIED")]
    if bad:
        raise SystemExit("a prior market carries a VERIFIED policy for a Portland premises; reuse refused")
    presumed = Counter(r["presumed_membership"] for r in routes)
    rep = OrderedDict([
        ("schema", "ptf-owned-data-first/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "9 -- owned data first: every Atlas-owned artifact that could already know Portland, "
                  "measured before new acquisition"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("headline",
         "Every committed market graph was scanned for a node in this market's %d admitted postal codes (count "
         "below). Portland is the first Oregon market and the one Pacific Northwest graph (seattle-wa) ends north of "
         "Longview: owned identities and owned policy are measured, not assumed." % len(_admitted_zips())),
        ("owned_identities_in_admitted_postal_codes", len(admitted_nodes)),
        ("owned_valid_policy_evidence", 0),
        ("owned_policy_rows_imported", 0),
        ("owned_routes_in_admitted_geography", len(routes) + len(token_routes)),
        ("owned_rebrands_or_closures_applicable", 0),
        ("owned_collisions_found", guard["foreign_portland_named_exclusion_count"]
         + guard["exclusions_with_no_premises_count"]),
        ("prior_graph_scan", OrderedDict([
            ("graphs_scanned", graphs), ("graphs_with_any_relevant_node", len(per_market)),
            ("per_market", per_market), ("nodes_in_admitted_postal_codes", admitted_nodes),
            ("policy_rows_imported", 0),
        ])),
        ("national_brand_corpus", corpus),
        ("a_brand_prefix_is_not_a_market",
         "Marriott's PDX prefix covers the whole metro -- and Salem, Newberg and Vancouver, Washington -- and "
         "never decides membership; Portland, MAINE is PWM and never selected. A route "
         "carries no postal code, so every route is a LEAD with a PRESUMED disposition read off the brand's own "
         "slug."),
        ("owned_brand_routes_by_presumption", OrderedDict(sorted(presumed.items()))),
        ("owned_brand_routes", routes),
        ("owned_brand_routes_by_place_token", token_routes),
        ("cross_market_name_collision_guard", guard),
        ("provider_history", history),
        ("owned_osm_extract", "WASHINGTON OWNED (the Seattle order's washington-261002, reused byte-for-byte for "
                              "Vancouver / Clark County); OREGON NOT OWNED -- this order downloaded Geofabrik "
                              "oregon-261002 once, free (see the OSM lane)."),
        ("what_is_never_reused", "Membership (re-decided here) and pet policy (none exists to import: every "
                                  "prior node in these codes was OUTSIDE its own market and unverified)."),
    ])
    return rep, live


LIVE_NAMES_OUT = os.path.join(REPORTS, "portland_or_live_identity_names_001.json")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    rep, live = build()
    if args.write:
        for path, doc in ((OUT, rep), (LIVE_NAMES_OUT, OrderedDict([
                ("schema", "ptf-live-identity-names/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
                ("names", live)]))):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, indent=1, ensure_ascii=False)
                fh.write("\n")
            print("WROTE", os.path.relpath(path, _DASH))
    print("OWNED IDENTITIES (admitted codes) =", rep["owned_identities_in_admitted_postal_codes"])
    print("OWNED POLICY EVIDENCE            =", rep["owned_valid_policy_evidence"])
    print("OWNED ROUTES                     =", rep["owned_routes_in_admitted_geography"],
          dict(rep["owned_brand_routes_by_presumption"]))
    print("OWNED COLLISIONS                 =", rep["owned_collisions_found"])
    print("LIVE IDENTITY NAMES              =", rep["cross_market_name_collision_guard"]["live_identity_names"]
          ["distinct_names"])
    print("PRIOR PROVIDER CALLS             =", rep["provider_history"]["prior_calls_recorded"],
          "ledgers:", rep["provider_history"]["firecrawl_ledgers_read"],
          "for a Portland URL:", rep["provider_history"]["calls_for_a_portland_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

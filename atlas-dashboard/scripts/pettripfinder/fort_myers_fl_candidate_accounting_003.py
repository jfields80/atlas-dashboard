"""PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- the authorized candidate's accounting for the registered
package ``pkg-fort-myers-fl-919f61116936bf5e`` (the founder authorized that package only, bound to commit 6a425592;
the source-ready shadow id ``pkg-fort-myers-fl-68b3cfa8`` and the source-ready order's discarded failed first seal are
not authorized, and the first registration commit 19c47422 is not the binding).

    python -m scripts.pettripfinder.fort_myers_fl_candidate_accounting_003 \\
        --live <live bundle> --candidate C:/t/fm4a [--rebuild C:/t/fm4b] \\
        [--build-log <log>] [--authorization <json>] [--write]

Derived from the previous market's 003 module, every structural gate unchanged. What is Fort Myers' own:

* IDENTITY SAFETY. The founder held all 51 unresolved rows -- the Comfort Suites / MainStay Suites pair at 9455 Old
  Luckett, the Quality Inn at 4760 S Cleveland (Travelodge retired; none of its evidence migrates), the Latitude 26
  Waterfront rows, Pink Shell and Edison Beach House, and the router-exhausted rest -- and published the 34
  verified-no-pets rows only as exclusions, so the BUILT artifact must carry no profile, no file and no sitemap route
  for any of them. Every held row is located by the ROUTE THE SITE FORMS (``release_index.hotel_route`` over the
  row's name), never by census slug; the two founder premises are ALSO checked by address on every built page.
* MUNICIPALITIES, NEVER FLATTENED, AND NO NAPLES. Every published profile page's own structured address must state FL,
  the municipality the census carries and its own postal code, in Lee County; no page may name a Naples / Collier
  locality.
* OPERATING STATUS. Every published profile is a row whose own current page proved it operating; no row with a
  closure, rebuild, preopening or unknown status has a page.
* ROUTE SCHEMES. Every /go/ interstitial of this market redirects to an absolute http(s) URL with a host, a tel: link
  or an internal path; first-party (official-website / booking) routes are absolute http(s).
* FEES, ON THE PAGE: a record whose fee was withheld renders no fee sentence, and a record with a fee renders exactly
  that one amount.
* No Fort Myers page may carry another market's text (another market's city / market name, read from its own
  contract; the clone-residue scan's excused homonyms Cleveland Avenue and Charlotte County stay excused).

THE COLLISION CANARY MEASURES EXPOSURE. The shared registry matches an exclusion by normalized NAME in every market,
so a bare-chain-SHAPED name is a latent hazard; it is a collision only when another building anywhere in the factory
carries that name (every census, every other market's registry row, every live profile).

THE EMPTY-RECEIPT CANARY IS FOUND, NOT NAMED. Every market's FAST receipt whose Rule J build is empty (no files, no
HTML, or the empty-input digest) is located by reading every receipt directory, and the repaired reader must keep each
one ineligible.

Two accounting systems, kept apart on purpose
----------------------------------------------
A. RELEASE-INDEX ROUTES -- the routes a market OWNS, as ``release_index`` enumerates them per market.
B. SERVED SITEMAP ROUTES -- what the composed bundle actually publishes in ``sitemap.xml``.
They are derived from their own sources and never reconciled by arithmetic.

Byte preservation
-----------------
The candidate is compared to the CURRENT VERIFIED LIVE bundle file by file, by sha256, from each bundle's own
``file_hash_manifest.json``. Every changed path is classified; an unclassified change is a failure, not a note.
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re
import sys
from collections import Counter, OrderedDict
from urllib.parse import urlsplit

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import global_deployment as GD        # noqa: E402
from scripts.pettripfinder import release_contracts as RC        # noqa: E402
from scripts.pettripfinder import release_index as RI            # noqa: E402
from scripts.pettripfinder.markets import contract as MC         # noqa: E402

WORK_ORDER = "PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "fort-myers-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PACKAGE_ID = "pkg-fort-myers-fl-919f61116936bf5e"
PACKAGE_PATH = os.path.join(PKG, "markets", "packages", MARKET, PACKAGE_ID + ".json")
SOURCE_PACKAGE = "pkg-fort-myers-fl-68b3cfa8bc4758c5"
SOURCE_DIGEST = "sha256:68b3cfa8bc4758c5b0d935d385fee3404ab01ed569f65ca2dc52d0c1733a2415"
CHECKS_PATH = os.path.join(REPORTS, "fort_myers_fl_registration_checks_002.json")
OUT = os.path.join(REPORTS, "fort_myers_fl_launch_authorization_003.json")
EMPTY_BUNDLE = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

#: the bare CHAIN collision class: a name built only of chain words and words that distinguish nothing names a CHAIN,
#: not a property, and may never reach the registry.
CHAIN_WORDS = frozenset("""
home2 hampton hilton marriott courtyard hyatt holiday comfort quality suburban intown extended woodspring tru
aloft element sheraton westin omni sonesta wyndham baymont ramada days super microtel clarion cambria econo
rodeway sleep candlewood staybridge embassy homewood doubletree springhill fairfield towneplace residence studio
motel red roof quinta radisson country best western surestay delta indigo crowne loews sofitel drury travelodge
mainstay howard johnson
""".split())
GENERIC_WORDS = frozenset("""
by and the a of at on in inn inns suite suites hotel hotels motel resort lodge house place plaza express stay
stays select simply america studios studio garden gardens point pointe club six 6
""".split())

#: set in main(): the candidate bundle directory, for the fragment count.
CANDIDATE_DIR = []

#: paths the composer legitimately regenerates for EVERY release, because they describe the whole site rather than
#: any one market.
GLOBAL_REGENERATED = ("index.html", "sitemap.xml", "llms.txt", "robots.txt",
                      "pet-friendly-hotels/index.html", "_headers", "_redirects")

#: the founder's named held rows and premises (PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003)
OLD_LUCKETT_KEYS = ("comfort suites fort myers east i 75", "mainstay suites fort myers east i 75")
CLEVELAND_REBRAND_KEY = "quality inn fort myers cape coral"
LATITUDE_PREFIX = "latitude 26"
LATITUDE_INN_KEY = "latitude 26 waterfront inn and suites"
SHARED_READER_KEYS = ("edison beach house hotel", "pink shell beach resort and marina")
#: (label, house number, street word): no built profile page may stand at these premises
HELD_PREMISES = (("old_luckett_9455", "9455", "luckett"), ("s_cleveland_4760", "4760", "cleveland"),
                 ("latitude_26_inn_4701_bonita_beach", "4701", "bonita beach"))
RETIRED_IDENTITY_WORD = "travelodge"
NAPLES_WORDS = re.compile(r"\b(naples|marco island|everglades city|immokalee|goodland|ave maria|collier|punta gorda|"
                          r"port charlotte)\b", re.I)
OPERATING = ("CURRENTLY_OPEN", "REOPENED", "PARTIALLY_OPEN", "SEASONAL")
FIRST_PARTY_ACTIONS = ("official-website", "booking")
_LOCALITY = re.compile(r'"addressLocality":\s*"([^"]+)"')
_REGION = re.compile(r'"addressRegion":\s*"([A-Z]{2})"')
_POSTAL = re.compile(r'"postalCode":\s*"(\d{5})')
_STREET = re.compile(r'"streetAddress":\s*"([^"]+)"')
_REFRESH = re.compile(r'http-equiv="refresh"\s+content="\d+;\s*url=([^"]*)"', re.I)
#: the fee sentence a profile page renders ("A $150 fee applies per stay")
_FEE_SENTENCE = re.compile(r"A \$([0-9][0-9,]*(?:\.[0-9]{2})?) fee applies")
_SUMMARY = re.compile(r'<p class="hp-summary">(.*?)</p>', re.S)
_AMOUNT = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)|([0-9]+(?:\.[0-9]{1,2})?)\s*USD")
_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _hashes(bundle_dir):
    return _load(os.path.join(bundle_dir, "file_hash_manifest.json"))["files"]


def _served_routes(bundle_dir):
    """What the bundle actually publishes, read from its own sitemap."""
    with open(os.path.join(bundle_dir, "site", "sitemap.xml"), encoding="utf-8") as fh:
        return set(_LOC.findall(fh.read()))


def _market_of(path, market_ids):
    """The market a bundle path belongs to, or None for the global surface."""
    parts = path.split("/")
    if parts[0] in ("pet-friendly-hotels", "go") and len(parts) > 1 and parts[1] in market_ids:
        return parts[1]
    return None


def _norm(value):
    return " ".join(str(value or "").lower().split())


def _house(street):
    m = re.match(r"\s*(\d+)", str(street or ""))
    return m.group(1) if m else ""


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _exclusion_registry_state(problems):
    """The collision canary: the shared registry after this market's registration."""
    registry = _load(os.path.join(PKG, "hotel_exclusions.json"))
    rows = registry["exclusions"] if isinstance(registry, dict) else registry
    counts = Counter(_norm(r.get("canonical_name") or r.get("name")) for r in rows)
    duplicates = sorted(name for name, n in counts.items() if n > 1)
    if duplicates:
        problems.append("%d duplicate canonical exclusion name(s) across markets: %s"
                        % (len(duplicates), duplicates[:5]))

    def _names_a_chain(value):
        toks = [t for t in re.sub(r"[^a-z0-9 ]", " ", _norm(value)).split() if t]
        if not toks or not any(t in CHAIN_WORDS for t in toks):
            return False
        return all(t in CHAIN_WORDS or t in GENERIC_WORDS for t in toks)

    by_market = {}
    for r in rows:
        by_market.setdefault(r.get("market_id") or r.get("market"), set()).add(
            _norm(r.get("canonical_name") or r.get("name")))
    mine = by_market.get(MARKET, set())
    chain_names = sorted(n for n in mine if _names_a_chain(n))
    exposure = _bare_chain_exposure(chain_names, rows)
    exposed = sorted(n for n, v in exposure.items() if v["OTHER_BUILDINGS_EXPOSED"])
    if exposed:
        problems.append("%s bare-chain-shaped names expose other buildings: %s" % (MARKET, exposed))
    elsewhere = sorted(n for n in mine if any(n in s2 for m2, s2 in by_market.items() if m2 != MARKET))
    if elsewhere:
        problems.append("%s names also held by another market: %s" % (MARKET, elsewhere))
    return OrderedDict((
        ("registry_rows", len(rows)),
        ("fort_myers_registry_rows", len(mine)),
        ("duplicate_canonical_names", len(duplicates)),
        ("duplicate_examples", duplicates[:5]),
        ("bare_chain_names", chain_names),
        ("bare_chain_exposure", exposure),
        ("bare_chain_collisions", exposed),
        ("names_held_by_another_market", elsewhere),
        ("BARE_CHAIN_NAMES", len(chain_names)),
        ("BARE_CHAIN_COLLISIONS", len(exposed)),
        ("DUPLICATE_EXCLUDED_IDENTITIES", len(duplicates)),
        ("CROSS_MARKET_COLLISIONS", len(elsewhere)),
        ("CROSS_MARKET_COLLISION_SAFE",
         "PASS" if not duplicates and not exposed and not elsewhere else "FAIL"),
    ))


def _bare_chain_exposure(names, registry_rows):
    """For each bare-chain-shaped name of this market: every OTHER row in the factory that carries it -- every
    market's census (admitted and non-admitted), every other market's registry row, every live profile. A row of
    another market at this building's own postal code is the same building, not a collision."""
    mine = {_norm(r.get("canonical_name")): r for r in registry_rows if (r.get("market_id") or r.get("market")) == MARKET}
    live_idx, _state, _problems = RI.live_index()
    live_names = {_norm(e.name) for i in live_idx.markets.values() if i.participating for e in i.profiles.values()}
    out = OrderedDict()
    for n in names:
        my_postal = str((mine.get(n) or {}).get("postal_code") or "")
        others = []
        for p in sorted(glob.glob(os.path.join(PKG, "identity_census", "*.json"))):
            market = os.path.splitext(os.path.basename(p))[0]
            if market == MARKET:
                continue
            d = _load(p)
            for h in list(d.get("hotels") or ()) + list(d.get("non_admitted") or ()):
                if _norm(h.get("canonical_name")) == n:
                    others.append(OrderedDict((("market", market), ("classification", h.get("classification")),
                                               ("street", h.get("street")), ("postal_code", h.get("postal_code")),
                                               ("same_building", bool(my_postal)
                                                and str(h.get("postal_code") or "") == my_postal))))
        others += [OrderedDict((("market", r.get("market_id")), ("registry_row", True), ("same_building", False)))
                   for r in registry_rows if (r.get("market_id") or r.get("market")) != MARKET
                   and _norm(r.get("canonical_name")) == n]
        if n in live_names:
            others.append(OrderedDict((("market", "live"), ("live_profile", True), ("same_building", False))))
        out[n] = OrderedDict((("other_rows", others),
                              ("OTHER_BUILDINGS_EXPOSED", sum(1 for o in others if not o["same_building"]))))
    return out


_MARKET_CFG = []


def _site_route(name):
    """The route the site forms for a hotel of this market (the site's slug drops "and" / "&")."""
    if not _MARKET_CFG:
        _MARKET_CFG.append(MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET)), source=MARKET))
    return RI.hotel_route(_MARKET_CFG[0], name)


def _outside_inventory_keys(census):
    """The identities the census holds OUTSIDE hotel inventory, by their own classification (the registration
    checks' cohorts, unchanged). A non-admitted row whose key an ADMITTED row also carries is checked through the
    admitted row's own hold, never as a refusal."""
    from scripts.pettripfinder import fort_myers_fl_nonhotel_rulings_001 as NH
    non = census.get("non_admitted") or ()
    admitted_keys = {h["identity_key"] for h in census["hotels"]}
    timeshare = sorted({h["identity_key"] for h in non if h["identity_key"] not in admitted_keys
                        and h.get("classification") == "NON_LODGING"
                        and NH.exclusion_class(h.get("classification_reason")) == "TIMESHARE"})
    rentals = sorted({h["identity_key"] for h in non
                      if h["identity_key"] not in admitted_keys and (
                          (h.get("classification") == "NON_LODGING"
                           and NH.exclusion_class(h.get("classification_reason")) in ("VACATION_RENTAL",
                                                                                       "RESORT_RESIDENCE"))
                          or "LODGING_QUALIFICATION_UNPROVEN" in (h.get("classification_reason") or "")
                          or "LODGING_CATEGORY_UNCONFIRMED" in (h.get("classification_reason") or "")
                          or "RESORT_RESIDENCE_UNCONFIRMED" in (h.get("classification_reason") or ""))})
    non_hotel = sorted({h["identity_key"] for h in non if h["identity_key"] not in admitted_keys
                        and h.get("classification") == "NON_LODGING"} - set(timeshare) - set(rentals))
    military = sorted({h["identity_key"] for h in non
                       if str(h.get("classification_reason")).startswith("MILITARY_RESTRICTED")})
    return timeshare, rentals, non_hotel, military


def _identity_safety(candidate_dir, proposed, cand_files, cand_sitemap, checks, problems):
    """Fort Myers' canaries, on the BUILT artifact: none of the 51 held rows and none of the 34 verified-no-pets rows
    has a profile page, a sitemap route, a release-index route or a /go/ file; no built page stands at a founder-held
    premises; no withheld fee renders on a page; every page states its own municipality in Lee County, FL."""
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    name_of = {h["identity_key"]: h["canonical_name"] for h in census["hotels"]}
    for h in census.get("non_admitted") or ():
        name_of.setdefault(h["identity_key"], h["canonical_name"])
    actionability = _load(os.path.join(REPORTS, "fort_myers_fl_actionability_001.json"))
    clean = _load(os.path.join(REPORTS, "fort_myers_fl_clean_authority_001.json"))
    name_of.update({r["identity_key"]: r["canonical_name"] for r in clean["rows"]})
    rows = actionability["rows"]
    founder = [r for r in rows if r["actionability"] == "REQUIRES_FOUNDER"]
    unresolved_keys = {r["identity_key"] for r in rows}
    groups = OrderedDict((
        ("dual_brand_rows", [r["identity_key"] for r in founder if r["disposition"] == "IDENTITY_MISMATCH_HOLD"]),
        ("shared_reader_founder_rows", sorted(r["identity_key"] for r in founder
                                              if r["disposition"] != "IDENTITY_MISMATCH_HOLD")),
        ("preopening_rows", [r["identity_key"] for r in rows if r["actionability"] == "HELD_UNTIL_OPENING"]),
        ("founder_named_old_luckett_comfort_suites_and_mainstay", list(OLD_LUCKETT_KEYS)),
        ("founder_named_quality_inn_4760_s_cleveland", [CLEVELAND_REBRAND_KEY]),
        ("founder_named_latitude_26", sorted(k for k in name_of if k.startswith(LATITUDE_PREFIX))),
        ("founder_named_pink_shell_and_edison", [k for k in SHARED_READER_KEYS if k in unresolved_keys]),
        ("router_exhausted_rows", [r["identity_key"] for r in rows if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]),
        ("all_unresolved_rows", [r["identity_key"] for r in rows]),
        ("verified_no_pets_rows", [r["identity_key"] for r in clean["rows"]
                                   if r["disposition"] == "CLEAN_VERIFIED_NO_PETS"]),
    ))
    for disp in sorted({r["disposition"] for r in rows}):
        groups["disposition_" + disp] = [r["identity_key"] for r in rows if r["disposition"] == disp]
    held = checks["held_row_safety"]
    expected = OrderedDict((
        ("dual_brand_rows", held["dual_brand"]["rows"]),
        ("shared_reader_founder_rows", held["shared_reader_refusal_founder"]["rows"]),
        ("preopening_rows", held["preopening"]["rows"]),
        ("founder_named_old_luckett_comfort_suites_and_mainstay", held["founder_ruling_old_luckett_dual_brand"]["rows"]),
        ("founder_named_quality_inn_4760_s_cleveland", held["founder_ruling_4760_cleveland_rebrand"]["rows"]),
        ("founder_named_latitude_26", held["founder_ruling_latitude_26"]["rows"]),
        ("founder_named_pink_shell_and_edison", held["founder_ruling_pink_shell_edison"]["rows"]),
        ("router_exhausted_rows", held["router_exhausted"]["rows"]),
        ("all_unresolved_rows", held["all_unresolved"]["rows"]),
        ("verified_no_pets_rows", 34)))
    for k, n in expected.items():
        if len(groups[k]) != n:
            problems.append("held group %s has %d rows, the registration recorded %d" % (k, len(groups[k]), n))
    if groups["shared_reader_founder_rows"] != sorted(SHARED_READER_KEYS):
        problems.append("the founder-class holds are not Pink Shell and Edison: %s" % groups["shared_reader_founder_rows"])
    for k in list(OLD_LUCKETT_KEYS) + [CLEVELAND_REBRAND_KEY, LATITUDE_INN_KEY] + list(SHARED_READER_KEYS):
        if k not in name_of:
            problems.append("named held row %r is not in the census" % k)
    mine = proposed.markets[MARKET]
    index_routes = {e.route for e in mine.profiles.values()}
    built_routes = {"/" + p[: -len("index.html")] for p in cand_files
                    if p.startswith("pet-friendly-hotels/%s/" % MARKET) and p.endswith("/index.html")}
    go_files = [p for p in cand_files if p.startswith("go/%s/" % MARKET)]
    policy = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET))
    pf_keys = {h.get("identity_key") or h.get("key") for h in policy["hotels"]}
    pf_routes = {_site_route(h["name"]) for h in policy["hotels"]}
    out = OrderedDict()
    for name, keys in groups.items():
        # a held row whose site route coincides with a PUBLISHED record's route is the published record's page
        # (the same name), not the held row's; that coincidence is reported, never hidden
        routes = {_site_route(name_of.get(k, k)) for k in keys}
        shared = sorted(r for r in routes if r in pf_routes)
        routes -= set(shared)
        slugs = {r.rstrip("/").rsplit("/", 1)[-1] for r in routes}
        leaked_records = sorted(set(keys) & pf_keys)
        leaked_pages = sorted(r for r in routes if r in built_routes)
        leaked_routes = sorted(r for r in routes if r in cand_sitemap)
        leaked_index = sorted(r for r in routes if r in index_routes)
        leaked_go = sorted(p for p in go_files if any("/%s/" % x in p for x in slugs))
        leaked = leaked_records + leaked_pages + leaked_routes + leaked_index + leaked_go
        if leaked or shared:
            problems.append("%s publish in the candidate: %s %s" % (name, leaked[:6], shared[:3]))
        out[name] = OrderedDict((("rows", len(keys)), ("pet_friendly_records", len(leaked_records)),
                                 ("profile_pages", len(leaked_pages)),
                                 ("sitemap_routes", len(leaked_routes)), ("release_index_routes", len(leaked_index)),
                                 ("go_files", len(leaked_go)), ("routes_shared_with_a_published_record", shared),
                                 ("published", bool(leaked or shared))))

    # ---- fees, on the page: a withheld fee renders no fee sentence; a published fee renders its one amount ------
    multi, multi_with_fee = 0, []
    for h in policy["hotels"]:
        quotes = " ".join(e.get("quote", "") for e in h.get("evidence", []))
        if len({float(a or b) for a, b in _AMOUNT.findall(quotes)}) > 1:
            multi += 1
            if (h.get("facts") or {}).get("pet_fee"):
                multi_with_fee.append(h.get("identity_key"))
    if multi_with_fee:
        problems.append("%d multi-amount record(s) publish a single fee: %s"
                        % (len(multi_with_fee), multi_with_fee[:5]))
    fees_doc = _load(os.path.join(REPORTS, "fort_myers_fl_fee_withholding_001.json"))
    withheld_quotes = {_norm(e["quote"]) for e in list(fees_doc["tiered"]) + list(fees_doc["unsafe"])}
    fee_pages = OrderedDict((("pages_with_a_fee_record", 0), ("pages_rendering_exactly_that_fee", 0),
                             ("pages_without_a_fee_record", 0), ("pages_without_a_fee_rendering_a_fee", 0),
                             ("withheld_records", 0), ("withheld_records_rendering_a_fee", 0)))
    fee_wrong = []

    # ---- municipalities, Lee County and no Naples: each profile page's own structured address ------------------
    from scripts.pettripfinder import fort_myers_fl_clone_residue_scan_001 as CRS
    from scripts.pettripfinder import fort_myers_fl_geography_001 as GEO
    from scripts.pettripfinder import fort_myers_fl_registration_checks_002 as CHK
    tokens, _zips = CRS.other_markets()
    city_rx = CRS._token_rx(({t for t, (_m, f) in tokens.items() if f != "state_name"} | {
        t.split(",")[0].strip() for t, (_m, f) in tokens.items() if f == "market_name"}) - set(CRS.EXCUSED_WORDS))
    admitted = {h["identity_key"]: h for h in census["hotels"]}
    pages_checked, wrong_pages, residue_pages, naples_pages = 0, [], [], []
    by_county, by_locality = Counter(), Counter()
    premises = OrderedDict((label, []) for label, _h, _w in HELD_PREMISES)
    travelodge_pages = []
    for h in sorted(policy["hotels"], key=lambda x: x.get("identity_key") or ""):
        k = h.get("identity_key") or h.get("key")
        a = admitted.get(k) or {}
        page = os.path.join(candidate_dir, "site", _site_route(h["name"]).lstrip("/"), "index.html")
        if not os.path.isfile(page):
            wrong_pages.append((k, "NO_PAGE"))
            continue
        pages_checked += 1
        text = _read(page)
        regions, postals = set(_REGION.findall(text)), set(_POSTAL.findall(text))
        localities, streets = set(_LOCALITY.findall(text)), set(_STREET.findall(text))
        postal = str(a.get("postal_code") or "")[:5]
        by_county[GEO.county_for_postal(postal) or ""] += 1
        by_locality.update(localities)
        if regions != {"FL"} or postals != {postal} or localities != {a.get("city")} \
                or (GEO.county_for_postal(postal) or "") != "Lee":
            wrong_pages.append((k, "STATE_CITY_ZIP_OR_COUNTY", sorted(regions), sorted(localities), sorted(postals),
                                a.get("city"), a.get("postal_code")))
        if any(NAPLES_WORDS.search(x) for x in localities):
            naples_pages.append((k, sorted(localities)))
        for label, house, word in HELD_PREMISES:
            if any(_house(s) == house and word in _norm(s) for s in streets):
                premises[label].append((k, sorted(streets)))
        if RETIRED_IDENTITY_WORD in _norm(h["name"]):
            travelodge_pages.append(OrderedDict((("identity_key", k), ("street", sorted(streets)),
                                                 ("postal_code", sorted(postals)))))
        hits = CHK._residue(text, city_rx)
        if hits:
            residue_pages.append((k, hits[:2]))
        # the page's own summary sentence
        summary = " ".join(_SUMMARY.findall(text))
        rendered = {x.replace(",", "") for x in _FEE_SENTENCE.findall(summary)}
        fee = (h.get("facts") or {}).get("pet_fee")
        withheld = any(_norm(e.get("quote")) in withheld_quotes for e in h.get("evidence", ())
                       if e.get("field") in ("pet_fee", "pets_allowed"))
        if withheld:
            fee_pages["withheld_records"] += 1
            if rendered:
                fee_pages["withheld_records_rendering_a_fee"] += 1
                fee_wrong.append((k, "WITHHELD_FEE_RENDERED", sorted(rendered)))
        if fee:
            fee_pages["pages_with_a_fee_record"] += 1
            want = "%d" % (fee["amount_cents"] // 100) if fee["amount_cents"] % 100 == 0 \
                else "%.2f" % (fee["amount_cents"] / 100.0)
            if rendered == {want}:
                fee_pages["pages_rendering_exactly_that_fee"] += 1
            else:
                fee_wrong.append((k, "FEE_RENDERED_DIFFERENTLY", want, sorted(rendered)))
        else:
            fee_pages["pages_without_a_fee_record"] += 1
            if rendered:
                fee_pages["pages_without_a_fee_rendering_a_fee"] += 1
                fee_wrong.append((k, "FEE_RENDERED_WITHOUT_A_RECORD", sorted(rendered)))
    if fee_wrong:
        problems.append("fee rendering: %s" % fee_wrong[:5])
    if wrong_pages or residue_pages or naples_pages:
        problems.append("Fort Myers municipality identity: pages %s, residue %s, Naples %s"
                        % (wrong_pages[:5], residue_pages[:3], naples_pages[:3]))
    if any(premises.values()):
        problems.append("a built profile page stands at a founder-held premises: %s" % dict(premises))
    if any(_house(s) == "4760" for t in travelodge_pages for s in t["street"]):
        problems.append("a Travelodge page stands at 4760 S Cleveland: %s" % travelodge_pages)
    identity_resolutions = os.path.join(PKG, "identity_resolutions.json")
    return OrderedDict((
        ("MUNICIPALITY_PAGES", OrderedDict((("profile_pages_checked", pages_checked),
                                            ("profile_pages_by_county", OrderedDict(sorted(by_county.items()))),
                                            ("profile_pages_by_municipality", OrderedDict(sorted(by_locality.items()))),
                                            ("WRONG_STATE_CITY_ZIP_OR_COUNTY_PAGES", len(wrong_pages)),
                                            ("wrong", wrong_pages[:10]),
                                            ("NAPLES_PAGES", len(naples_pages)), ("naples", naples_pages[:10]),
                                            ("OTHER_MARKET_TEXT_PAGES", len(residue_pages)),
                                            ("residue", residue_pages[:10]),
                                            ("other_market_tokens", len(tokens))))),
        ("FOUNDER_PREMISES_PAGES", OrderedDict((label, len(v)) for label, v in premises.items())),
        ("founder_premises_hits", premises),
        ("published_travelodge_pages", travelodge_pages),
        ("TRAVELODGE_PAGES_AT_4760", sum(1 for t in travelodge_pages for s in t["street"] if _house(s) == "4760")),
        ("HELD_ROWS_PUBLISHED", any(v["published"] for k, v in out.items() if k != "verified_no_pets_rows")),
        ("VERIFIED_NO_PETS_PUBLISHED_AS_PROFILES", out["verified_no_pets_rows"]["published"]),
        ("groups", out),
        ("identity_resolutions_ruling_written", os.path.isfile(identity_resolutions)
         and MARKET in _read(identity_resolutions)),
        ("fee_safety", OrderedDict((
            ("fee_withholding", OrderedDict((k, fees_doc[k]) for k in (
                "fees_published", "tiered_fees_withheld", "unsafe_single_fees_withheld",
                "misleading_single_fees_published"))),
            ("multi_amount_rows", multi),
            ("misleading_single_fees_published", len(multi_with_fee)),
            ("on_the_page", fee_pages),
            ("FEES_RENDERED_WRONGLY", len(fee_wrong)),
            ("wrong", fee_wrong[:10])))),
    ))


def _operating_status_safety(candidate_dir, cand_files, problems):
    """Every published profile is a row whose own current page proved it operating; a row with a closure, rebuild,
    preopening or unknown status (or a nonoperating signal) has no page."""
    doc = _load(os.path.join(REPORTS, "fort_myers_fl_operating_status_accounting_001.json"))["operating_status_accounting"]
    policy = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET))
    pf_keys = {h.get("identity_key") for h in policy["hotels"]}
    pf_routes = {_site_route(h["name"]) for h in policy["hotels"]}
    built = {"/" + p[: -len("index.html")] for p in cand_files
             if p.startswith("pet-friendly-hotels/%s/" % MARKET) and p.endswith("/index.html")}
    status_of = {r["identity_key"]: r for r in doc["rows"]}
    published_by_status = Counter((status_of.get(k) or {}).get("status", "NO_STATUS_ROW") for k in pf_keys)
    not_operating = sorted(k for k in pf_keys if (status_of.get(k) or {}).get("status") not in OPERATING)
    signalled = sorted(k for k in pf_keys if (status_of.get(k) or {}).get("signals"))
    nonoperating_rows = [r for r in doc["rows"] if r["status"] not in OPERATING or r.get("signals")]
    with_page = []
    for r in nonoperating_rows:
        route = _site_route(r["canonical_name"])
        if route in built and route not in pf_routes:
            with_page.append((r["identity_key"], r["status"]))
        elif r["identity_key"] in pf_keys:
            with_page.append((r["identity_key"], r["status"]))
    by_status = Counter(r["status"] for r in nonoperating_rows)
    if not_operating or signalled or with_page:
        problems.append("operating status: published not operating %s, signalled %s, pages %s"
                        % (not_operating[:5], signalled[:5], with_page[:5]))
    return OrderedDict((
        ("published_by_status", OrderedDict(sorted(published_by_status.items()))),
        ("held_rows_by_nonoperating_or_unknown_status", OrderedDict(sorted(by_status.items()))),
        ("NONOPERATING_PROFILES", len(not_operating)),
        ("TEMPORARILY_CLOSED_PROFILES", published_by_status.get("TEMPORARILY_CLOSED", 0)),
        ("PERMANENTLY_CLOSED_PROFILES", published_by_status.get("PERMANENTLY_CLOSED", 0)
         + published_by_status.get("DEMOLISHED", 0)),
        ("PREOPENING_PROFILES", published_by_status.get("PREOPENING", 0)),
        ("CLOSED_FOR_REBUILD_PROFILES", published_by_status.get("CLOSED_FOR_REBUILD", 0)),
        ("STATUS_UNKNOWN_PROFILES", published_by_status.get("STATUS_UNKNOWN", 0)),
        ("published_with_a_nonoperating_signal", signalled),
        ("nonoperating_rows_with_a_page", with_page),
        ("unbound_nonoperating_signals", len(doc["nonoperating_signals"])),
        ("unbound_nonoperating_signals_published", sum(1 for s in doc["nonoperating_signals"] if s.get("published"))),
    ))


def _route_scheme_safety(candidate_dir, cand_files, problems):
    """Every /go/ interstitial of this market redirects to an absolute http(s) URL with a host, a tel: link or an
    internal path; a first-party (official-website / booking) route is always absolute http(s). The rule is the one
    FAST rule J applies to a built /go/ page, restated here (a market-local module may not import the shared
    renderer); the shared validator is not touched."""
    pages = sorted(p for p in cand_files if p.startswith("go/%s/" % MARKET) and p.endswith("/index.html"))
    invalid, http_less_first_party, by_kind = [], [], Counter()
    for p in pages:
        m = _REFRESH.search(_read(os.path.join(candidate_dir, "site", p)))
        target = html.unescape(m.group(1)) if m else ""
        action = p.split("/")[-2]
        if target.startswith("tel:"):
            by_kind["tel"] += 1
            continue
        if target.startswith("/") and not target.startswith("//"):
            by_kind["internal"] += 1
            continue
        parts = urlsplit(target)
        ok = parts.scheme in ("http", "https") and bool(parts.hostname)
        by_kind["absolute_http" if ok else "invalid"] += 1
        if not ok:
            invalid.append((p, target))
        if action in FIRST_PARTY_ACTIONS and not ok:
            http_less_first_party.append((p, target))
    if invalid or http_less_first_party or not pages:
        problems.append("route schemes: %d invalid %s, %d http-less first-party"
                        % (len(invalid), invalid[:3], len(http_less_first_party)))
    return OrderedDict((("go_pages_checked", len(pages)), ("by_kind", OrderedDict(sorted(by_kind.items()))),
                        ("INVALID_ROUTE_SCHEMES", len(invalid)), ("invalid", invalid[:10]),
                        ("HTTP_LESS_FIRST_PARTY_ROUTES", len(http_less_first_party)),
                        ("http_less_first_party", http_less_first_party[:10])))


def _held_outside_inventory_safety(candidate_dir, proposed, cand_files, cand_sitemap, checks, problems):
    """The timeshare / vacation-ownership, vacation rental / private condo / residence, other non-hotel and
    military-restricted identities the census holds outside hotel inventory (read from the census by their own
    classification, never typed): no profile, route, release-index entry or /go/ file, no policy record or registry
    row, and no qualifying census row."""
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    non = census.get("non_admitted") or ()
    name_of = {h["identity_key"]: h["canonical_name"] for h in non}
    timeshare, rentals, non_hotel, military = _outside_inventory_keys(census)
    classes = OrderedDict((("timeshare", timeshare), ("private_condo_residence_or_rental", rentals),
                           ("other_non_hotel", non_hotel), ("military_restricted", military)))
    held = checks["held_row_safety"]
    expected = {"timeshare": held["timeshare"]["rows"],
                "private_condo_residence_or_rental": held["private_condo_residence_or_rental"]["rows"]}
    for k, n in expected.items():
        if len(classes[k]) != n:
            problems.append("%s rows: %d, the registration recorded %d" % (k, len(classes[k]), n))
    policy = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET))
    policy_keys = {h.get("identity_key") for h in policy["hotels"]}
    pf_routes = {_site_route(h["name"]) for h in policy["hotels"]}
    registry = _load(os.path.join(PKG, "hotel_exclusions.json"))
    registry_keys = {r.get("identity_key") or _norm(r.get("canonical_name"))
                     for r in (registry["exclusions"] if isinstance(registry, dict) else registry)
                     if r.get("market_id") == MARKET}
    index_routes = {e.route for e in proposed.markets[MARKET].profiles.values()}
    admitted_keys = {h["identity_key"] for h in census["hotels"]}
    out = OrderedDict()
    for cls, keys in classes.items():
        props = OrderedDict()
        for key in keys:
            route = _site_route(name_of.get(key, key))
            slug = route.rstrip("/").rsplit("/", 1)[-1]
            same_name_as_published = route in pf_routes
            row = OrderedDict((
                ("site_route", route),
                ("route_is_a_published_hotels_route", same_name_as_published),
                ("hotel_profile", not same_name_as_published
                 and any(p == route.lstrip("/") + "index.html" for p in cand_files)),
                ("served_route", not same_name_as_published and route in cand_sitemap),
                ("release_index_route", not same_name_as_published and route in index_routes),
                ("go_file", not same_name_as_published
                 and any(p.startswith("go/%s/" % MARKET) and "/%s/" % slug in p for p in cand_files)),
                ("pet_friendly_record", key in policy_keys),
                ("verified_no_pets_hotel_exclusion", key in registry_keys),
                ("qualifying_census_row", key in admitted_keys),
            ))
            leaked = [k for k, v in row.items() if k not in ("site_route", "route_is_a_published_hotels_route") and v]
            if leaked:
                problems.append("%s identity %s is not held out: %s" % (cls, key, leaked))
            props[key] = row
        out[cls] = OrderedDict((("rows", len(keys)),
                                ("PUBLISHED", sum(1 for v in props.values()
                                                  if any(x for k, x in v.items()
                                                         if k not in ("site_route",
                                                                      "route_is_a_published_hotels_route")))),
                                ("routes_shared_with_a_published_hotel",
                                 sorted(k for k, v in props.items() if v["route_is_a_published_hotels_route"])),
                                ("properties", props)))
    return OrderedDict((
        ("TIMESHARE_PROFILES_PUBLISHED", out["timeshare"]["PUBLISHED"]),
        ("PRIVATE_CONDO_RESIDENCE_OR_RENTAL_PUBLISHED", out["private_condo_residence_or_rental"]["PUBLISHED"]),
        ("OTHER_NON_HOTEL_PUBLISHED", out["other_non_hotel"]["PUBLISHED"]),
        ("MILITARY_RESTRICTED_PROFILES_PUBLISHED", out["military_restricted"]["PUBLISHED"]),
        ("classes", out),
    ))


def _reader_safety(problems):
    """The registered documents, judged by the source-ready publication-safety audit's own logic."""
    from scripts.pettripfinder import fort_myers_fl_publication_safety_audit_001 as SAFE
    findings = SAFE.audit(_load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET)),
                          _load(os.path.join(PKG, "fort_myers_fl_proposed_authority_001.json")))
    counts = OrderedDict((k.upper(), len(v)) for k, v in findings.items())
    for k, v in counts.items():
        if v:
            problems.append("%s = %d" % (k, v))
    return counts


def _fast_receipt_safety(package, problems):
    """The receipt a current selection would use, judged by the repaired reader. Only the registered package's
    receipt may qualify: the source-ready shadow digest selects nothing, and every EMPTY receipt anywhere in the
    factory (found by reading every receipt directory, never named) stays ineligible."""
    from scripts.pettripfinder import fast_release_lane as FL
    selected = FL.eligible_receipts(MARKET, package["package_digest"])
    doc = _load(str(selected[-1])) if selected else {}
    detail = ((doc.get("RESULTS") or {}).get("J") or {}).get("detail") or {}
    k_result = ((doc.get("RESULTS") or {}).get("K") or {})
    shadow_selected = FL.eligible_receipts(MARKET, SOURCE_DIGEST)
    on_disk = sorted(os.path.basename(p) for p in glob.glob(os.path.join(str(FL.receipt_dir(MARKET)), "*.json")))
    empty, empty_eligible = [], []
    for mdoc in sorted(glob.glob(os.path.join(PKG, "markets", "*.json"))):
        market = os.path.splitext(os.path.basename(mdoc))[0]
        for p in sorted(glob.glob(os.path.join(str(FL.receipt_dir(market)), "*.json"))):
            try:
                r = _load(p)
            except (ValueError, OSError):
                continue
            j = ((r.get("RESULTS") or {}).get("J") or {}).get("detail") or {}
            if not isinstance(j, dict) or not j:
                continue
            if not j.get("file_count") or not j.get("html_count") or j.get("bundle_sha256") == EMPTY_BUNDLE:
                empty.append(os.path.basename(p))
                if r.get("PACKAGE_DIGEST") and any(os.path.samefile(str(e), p)
                                                   for e in FL.eligible_receipts(market, r["PACKAGE_DIGEST"])):
                    empty_eligible.append(os.path.basename(p))
    ok = (len(selected) == 1 and not FL.receipt_output_defects(doc) and (detail.get("file_count") or 0) > 0
          and (detail.get("html_count") or 0) > 0 and detail.get("bundle_sha256") not in (None, EMPTY_BUNDLE)
          and not shadow_selected and not empty_eligible and on_disk == [os.path.basename(str(selected[-1]))])
    if not ok:
        problems.append("FAST receipt safety failed: selected %s, defects %s, shadow selected %s, empty eligible %s, "
                        "on disk %s" % (selected[-1:], FL.receipt_output_defects(doc), shadow_selected,
                                        empty_eligible, on_disk))
    return OrderedDict((
        ("selected", os.path.basename(str(selected[-1])) if selected else None),
        ("current_eligibility", "YES" if selected else "NO"),
        ("receipts_on_disk_for_this_market", on_disk),
        ("bundle_sha256", detail.get("bundle_sha256")), ("file_count", detail.get("file_count")),
        ("html_count", detail.get("html_count")), ("defects", FL.receipt_output_defects(doc)),
        ("rule_J_status", ((doc.get("RESULTS") or {}).get("J") or {}).get("status")),
        ("rule_K_status", k_result.get("status")),
        ("RULE_J_NONEMPTY", "PASS" if (detail.get("file_count") or 0) > 0 and (detail.get("html_count") or 0) > 0
         and detail.get("bundle_sha256") not in (None, EMPTY_BUNDLE) else "FAIL"),
        ("source_ready_shadow_digest_selects", [os.path.basename(str(p)) for p in shadow_selected]),
        ("FAILED_FIRST_SEAL_RECEIPT_ELIGIBLE",
         "NO" if on_disk == [os.path.basename(str(selected[-1]))] else "UNPROVEN"),
        ("failed_first_seal_note", "the source-ready order's first seal failed FAST rule J and its outputs were "
                                   "discarded; no receipt for it exists, and only the registered receipt is on disk"),
        ("empty_receipts_in_the_factory", empty),
        ("empty_receipts_currently_eligible", empty_eligible),
    ))


def _physical_rendering(build_log, live_idx, proposed):
    """Release-index reuse (every live market's index entry carried unchanged) is one figure; how many market
    fragments the whole-site composer physically rendered is another. They are never merged."""
    live = [m for m, i in live_idx.markets.items() if i.participating]
    reused = [m for m in live if proposed.markets[m] == live_idx.markets[m]]
    scopes = None
    if build_log and os.path.isfile(build_log):
        scopes = len(re.findall(r"Market scope:", _read(build_log).replace("\x00", "")))
    fragments = len(_load(os.path.join(CANDIDATE_DIR[0], "global_bundle_manifest.json"))["fragments"]) \
        if CANDIDATE_DIR else None
    return OrderedDict((
        ("UNCHANGED_BUNDLES_REUSED", len(reused)),
        ("UNCHANGED_MARKETS_REBUILT", len(live) - len(reused)),
        ("FORT_MYERS_BUNDLES_BUILT", 1),
        ("PHYSICAL_FRAGMENTS_RERENDERED", fragments),
        ("market_scopes_in_build_log", scopes),
        ("note", "REUSE counts live market index entries carried into the candidate unchanged. The whole-site composer "
                 "has no populated release store in this worktree, so it physically renders every participating "
                 "market's fragment; that count is PHYSICAL_FRAGMENTS_RERENDERED and is not reuse."),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-log", help="the candidate assembly's log, to count physical re-rendering")
    ap.add_argument("--live", required=True, help="the CURRENT VERIFIED LIVE bundle directory")
    ap.add_argument("--candidate", required=True, help="the authorized candidate bundle directory")
    ap.add_argument("--rebuild", help="an INDEPENDENT second assembly of the same tree; its bundle digest proves "
                                      "candidate determinism by measurement")
    ap.add_argument("--authorization", help="the founder deployment authorization to check for deployment "
                                            "eligibility (it must NOT be consumed)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    package = _load(PACKAGE_PATH)
    checks = _load(CHECKS_PATH)
    CANDIDATE_DIR[:] = [args.candidate]
    live_manifest = _load(os.path.join(args.live, "global_bundle_manifest.json"))
    cand_manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))

    def published(manifest):
        """The bundle's published profile count, DERIVED from its own fragments."""
        return sum(len(f["hotel_routes"]) for f in manifest["fragments"].values())

    live_profiles = published(live_manifest)
    cand_profiles = published(cand_manifest)
    problems = []

    # ---- A. release-index accounting ------------------------------------
    live_idx, live_state, live_problems = RI.live_index()
    if live_manifest["bundle_sha256"] != getattr(live_state, "bundle_sha256", live_manifest["bundle_sha256"]):
        problems.append("the --live bundle is not the verified live bundle")
    sd_index = RI.index_from_package(package, participating=True)
    proposed = RI.compose(live_idx, sd_index, participates=True)
    diff = RI.compare(live_idx, proposed, package_market=MARKET, intended_delta=package["intended_delta"])
    live_routes = {r for i in live_idx.markets.values() if i.participating for r in i.routes}
    sd_routes = set(proposed.markets[MARKET].routes)
    cand_routes = {r for i in proposed.markets.values() if i.participating for r in i.routes}

    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET)), source=MARKET)
    slugs = {c.slug for c in cfg.corridors}
    hub = sorted(r for r in sd_routes if r == "/pet-friendly-hotels/%s/" % MARKET)
    corridor = sorted(r for r in sd_routes if r not in hub and r.rstrip("/").rsplit("/", 1)[-1] in slugs)
    hotel = sorted(r for r in sd_routes if r not in hub and r not in corridor)

    derived = RC.derive_authority(MARKET)
    recon = derived.reconciliation()
    if len(hotel) != derived.published_hotel_profiles:
        problems.append("hotel routes %d != published profiles %d" % (len(hotel), derived.published_hotel_profiles))
    if len(corridor) != derived.corridor_route_count:
        problems.append("corridor routes %d != contract %d" % (len(corridor), derived.corridor_route_count))
    if len(hub) != 1:
        problems.append("expected exactly one hub route, got %d" % len(hub))
    if live_routes & sd_routes:
        problems.append("the joining market claims %d live route(s)" % len(live_routes & sd_routes))
    if not diff["passed"]:
        problems.append("release_index.compare findings: %s" % diff["findings"][:3])

    # ---- B. served sitemap accounting -----------------------------------
    live_sitemap = _served_routes(args.live)
    cand_sitemap = _served_routes(args.candidate)
    live_served = int(live_manifest["sitemap_route_count"])
    cand_served = int(cand_manifest["sitemap_route_count"])
    market_ids = set(live_idx.markets) | {MARKET}
    if len(live_sitemap) != live_served or len(cand_sitemap) != cand_served:
        problems.append("a bundle's sitemap_route_count disagrees with its own sitemap: live %d/%d, candidate %d/%d"
                        % (len(live_sitemap), live_served, len(cand_sitemap), cand_served))
    served_added = sorted(cand_sitemap - live_sitemap)
    served_removed = sorted(live_sitemap - cand_sitemap)
    if served_removed:
        problems.append("%d served route(s) disappeared: %s" % (len(served_removed), served_removed[:5]))
    foreign = [r for r in served_added if "/%s/" % MARKET not in r]
    if foreign:
        problems.append("%d served route(s) added that are not Fort Myers': %s" % (len(foreign), foreign[:5]))
    #: the served delta is the owned-route delta PLUS ONE: a market's policy-comparison page is published but is not
    #: a route the release index counts as owned. Derived here, never assumed.
    comparison_route = (cand_manifest["fragments"][MARKET] or {}).get("comparison_route")
    expected_served_delta = len(sd_routes) + (1 if comparison_route in cand_sitemap else 0)
    if len(served_added) != expected_served_delta:
        problems.append("served delta %d != %d owned routes + the comparison page" % (len(served_added), len(sd_routes)))
    staged = set(checks["projected_accounting"]["fort_myers_served_routes"])
    staging_agreement = OrderedDict((
        ("staged_served_routes", len(staged)), ("candidate_served_routes", len(served_added)),
        ("only_in_candidate", sorted(set(served_added) - staged)), ("only_in_staging", sorted(staged - set(served_added))),
        ("EXACT_ROUTE_SET_AGREEMENT", set(served_added) == staged)))
    if not staging_agreement["EXACT_ROUTE_SET_AGREEMENT"]:
        problems.append("the candidate's Fort Myers routes differ from registration staging: %s"
                        % dict(staging_agreement))
    live_global_served = live_served - len(live_routes)
    cand_global_served = cand_served - len(cand_routes)

    # ---- C. byte / file preservation ------------------------------------
    live_files = _hashes(args.live)
    cand_files = _hashes(args.candidate)
    added = sorted(set(cand_files) - set(live_files))
    removed = sorted(set(live_files) - set(cand_files))
    changed = sorted(p for p in set(live_files) & set(cand_files) if live_files[p] != cand_files[p])

    def classify(paths):
        out = OrderedDict((("fort_myers", []), ("global_regenerated", []), ("prior_market", []), ("unclassified", [])))
        for p in paths:
            owner = _market_of(p, market_ids)
            if owner == MARKET:
                out["fort_myers"].append(p)
            elif p in GLOBAL_REGENERATED:
                out["global_regenerated"].append(p)
            elif owner is not None:
                out["prior_market"].append(p)
            else:
                out["unclassified"].append(p)
        return out

    added_by, removed_by, changed_by = classify(added), classify(removed), classify(changed)
    if removed:
        problems.append("%d file(s) removed from the live bundle: %s" % (len(removed), removed[:5]))
    if changed_by["prior_market"]:
        problems.append("%d prior-market file(s) changed: %s"
                        % (len(changed_by["prior_market"]), changed_by["prior_market"][:5]))
    for bucket, label in ((added_by, "added"), (changed_by, "changed")):
        if bucket["unclassified"]:
            problems.append("%d unclassified %s path(s): %s" % (len(bucket["unclassified"]), label,
                                                                bucket["unclassified"][:5]))
    if added_by["prior_market"]:
        problems.append("%d prior-market file(s) added: %s" % (len(added_by["prior_market"]),
                                                              added_by["prior_market"][:5]))

    # ---- D. hold / exclusion safety -------------------------------------
    policy = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET))
    approved = len(policy["hotels"])
    fm_profile_files = [p for p in cand_files
                        if p.startswith("pet-friendly-hotels/%s/" % MARKET) and p.endswith("/index.html")]
    fm_hotel_pages = [p for p in fm_profile_files
                      if p.split("/")[2] not in ({"index.html", "policy-comparison"} | slugs)]
    fm_profile_slugs = {p.split("/")[2] for p in fm_profile_files}
    approved_routes = {r.rstrip("/").rsplit("/", 1)[-1] for r in hotel}
    #: the hub's own index.html and the market's policy-comparison page are market pages, not hotel profiles
    market_pages = {"index.html", "policy-comparison"}
    unapproved = sorted(fm_profile_slugs - approved_routes - slugs - market_pages)
    if unapproved:
        problems.append("%d Fort Myers page(s) in the candidate are not approved profiles: %s"
                        % (len(unapproved), unapproved[:5]))
    if approved != derived.published_hotel_profiles:
        problems.append("policy package publishes %d, contract derives %d" % (approved, derived.published_hotel_profiles))

    collisions = _exclusion_registry_state(problems)
    identity = _identity_safety(args.candidate, proposed, cand_files, cand_sitemap, checks, problems)
    outside = _held_outside_inventory_safety(args.candidate, proposed, cand_files, cand_sitemap, checks, problems)
    operating = _operating_status_safety(args.candidate, cand_files, problems)
    schemes = _route_scheme_safety(args.candidate, cand_files, problems)
    reader = _reader_safety(problems)
    fast_receipt = _fast_receipt_safety(package, problems)
    rendering = _physical_rendering(args.build_log, live_idx, proposed)

    # ---- E. determinism, measured rather than inherited -----------------
    determinism = OrderedDict((("measured", False),))
    if args.rebuild:
        rebuild_manifest = _load(os.path.join(args.rebuild, "global_bundle_manifest.json"))
        rebuild_files = _hashes(args.rebuild)
        differing = sorted(p for p in set(cand_files) | set(rebuild_files) if cand_files.get(p) != rebuild_files.get(p))
        identical = (rebuild_manifest["bundle_sha256"] == cand_manifest["bundle_sha256"]
                     and rebuild_manifest.get("sitemap_sha256") == cand_manifest.get("sitemap_sha256")
                     and len(rebuild_files) == len(cand_files) and not differing)
        determinism = OrderedDict((
            ("measured", True),
            ("second_assembly", args.rebuild),
            ("candidate_bundle_sha256", cand_manifest["bundle_sha256"]),
            ("rebuild_bundle_sha256", rebuild_manifest["bundle_sha256"]),
            ("candidate_sitemap_sha256", cand_manifest.get("sitemap_sha256")),
            ("rebuild_sitemap_sha256", rebuild_manifest.get("sitemap_sha256")),
            ("candidate_file_count", len(cand_files)),
            ("rebuild_file_count", len(rebuild_files)),
            ("files_compared", len(set(cand_files) | set(rebuild_files))),
            ("files_differing", len(differing)),
            ("examples", differing[:5]),
            ("result", "BYTE_IDENTICAL" if identical else "DIVERGED"),
        ))
        if not identical:
            problems.append("the candidate is not deterministic: %d file(s) differ between two assemblies of the "
                            "same tree" % len(differing))

    # ---- F. deployment eligibility: authorized, deployable, UNCONSUMED ---
    eligibility = OrderedDict((("checked", False),))
    if args.authorization:
        from scripts.pettripfinder import deployment_authorization as DA
        auth = _load(args.authorization)
        gd_manifest = GD.build_manifest(cand_manifest)
        dep_problems = DA.deployability_problems(auth, manifest=gd_manifest)
        auth_problems = DA.verify_authorization(auth, manifest=gd_manifest)
        bound = auth.get("bundle_sha256") == cand_manifest["bundle_sha256"]
        consumed = bool(auth.get("deploy_id")) or auth.get("authorization_status") == DA.DEPLOYED
        eligibility = OrderedDict((
            ("checked", True),
            ("authorization_id", auth.get("authorization_id")),
            ("authorization_status", auth.get("authorization_status")),
            ("bound_to_candidate_bytes", bound),
            ("deployability_problems", dep_problems),
            ("verify_authorization_problems", auth_problems),
            ("deployable", auth.get("authorization_status") in DA.DEPLOYABLE_STATUSES),
            ("consumed", consumed),
            ("deploy_id", auth.get("deploy_id")),
        ))
        if not bound:
            problems.append("the authorization names bundle %r, the candidate is %r"
                            % (auth.get("bundle_sha256"), cand_manifest["bundle_sha256"]))
        if dep_problems or auth_problems:
            problems.append("authorization problems: %s" % (dep_problems + auth_problems)[:3])
        if consumed:
            problems.append("the authorization has been CONSUMED; this order forbids that")

    fm = OrderedDict((
        ("profiles", derived.published_hotel_profiles),
        ("verified_no_pets", recon["verified_no_pets"]),
        ("census", _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))["count"]),
        ("unresolved", recon["unresolved"]),
        ("hub_routes", len(hub)),
        ("corridor_routes", len(corridor)),
        ("hotel_routes", len(hotel)),
        ("other_routes", len(sd_routes) - len(hub) - len(corridor) - len(hotel)),
        ("release_index_routes", len(sd_routes)),
        ("served_routes", len(served_added)),
        ("comparison_route", comparison_route),
        ("publishing_corridors", [r.rstrip("/").rsplit("/", 1)[-1] for r in corridor]),
        ("suppressed_corridors", sorted(slugs - set(r.rstrip("/").rsplit("/", 1)[-1] for r in corridor))),
        ("forced_corridors", 0),
        ("route_set_agreement_with_registration_staging", staging_agreement),
    ))
    expected_totals = OrderedDict((("markets", 46), ("profiles", 4430), ("release_index_routes", 4869),
                                   ("served_routes", 4948), ("fort_myers_profiles", 57),
                                   ("fort_myers_release_index_routes", 62), ("fort_myers_served_routes", 63)))
    measured_totals = OrderedDict((("markets", len(cand_manifest["participating_markets"])),
                                   ("profiles", cand_profiles), ("release_index_routes", len(cand_routes)),
                                   ("served_routes", cand_served), ("fort_myers_profiles", len(hotel)),
                                   ("fort_myers_release_index_routes", len(sd_routes)),
                                   ("fort_myers_served_routes", len(served_added))))
    if measured_totals != expected_totals:
        problems.append("candidate totals %s != the founder's projection %s"
                        % (dict(measured_totals), dict(expected_totals)))

    report = OrderedDict((
        ("schema", "ptf-launch-authorization-accounting/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("authorized_package", PACKAGE_ID),
        ("live_bundle", OrderedDict((
            ("bundle_sha256", live_manifest["bundle_sha256"]),
            ("markets", len(live_manifest["participating_markets"])),
            ("profiles", live_profiles),
            ("served_sitemap_routes", live_served),
            ("release_index_routes", len(live_routes)),
            ("non_market_served_surface", live_global_served),
            ("verified_live", not live_problems),
            ("live_index_problems", live_problems),
        ))),
        ("candidate_bundle", OrderedDict((
            ("bundle_sha256", cand_manifest["bundle_sha256"]),
            ("sitemap_sha256", cand_manifest.get("sitemap_sha256")),
            ("source_commit", cand_manifest.get("generated_from_commit") or cand_manifest.get("source_commit")),
            ("file_count", len(cand_files)),
            ("markets", len(cand_manifest["participating_markets"])),
            ("profiles", cand_profiles),
            ("served_sitemap_routes", cand_served),
            ("release_index_routes", len(cand_routes)),
            ("non_market_served_surface", cand_global_served),
            ("all_gates_pass", cand_manifest.get("all_gates_pass")),
        ))),
        ("totals_against_projection", OrderedDict((("expected", expected_totals), ("measured", measured_totals),
                                                   ("AGREE", measured_totals == expected_totals)))),
        ("route_accounting_note",
         "RELEASE-INDEX routes count what markets OWN; SERVED SITEMAP routes count what the composed bundle publishes. "
         "The difference on each side is the release-global surface no market owns (the apex, the category root, the "
         "editorial and legal pages and the market directory). It is the same set before and after, which is why the "
         "served delta equals Fort Myers' owned-route delta plus its own policy-comparison page."),
        ("fort_myers", fm),
        ("delta_safety", OrderedDict((
            ("release_diff_passed", diff["passed"]),
            ("finding_counts", diff.get("finding_counts") or {}),
            ("findings", diff.get("findings") or []),
            ("PRIOR_MARKETS_LOST", len(set(live_idx.participating) - set(proposed.participating))),
            ("PRIOR_PROFILES_LOST", max(0, live_profiles + derived.published_hotel_profiles - cand_profiles)),
            ("PRIOR_RELEASE_INDEX_ROUTES_LOST", len(live_routes - cand_routes)),
            ("PRIOR_SERVED_ROUTES_LOST", len(served_removed)),
            ("NEW_MARKETS", sorted(set(proposed.participating) - set(live_idx.participating))),
            ("unexpected_market_delta", sorted(set(proposed.participating) - set(live_idx.participating) - {MARKET})),
            ("unexpected_profile_delta", sorted(set(fm_hotel_pages) - {r.lstrip("/") + "index.html" for r in hotel})),
            ("unexpected_route_delta", sorted(r for r in cand_routes - live_routes if r not in sd_routes)),
            ("unexpected_served_route_delta", foreign),
            ("parent_markets_preserved",
             sorted(live_idx.participating) == sorted(m for m in proposed.participating if m != MARKET)),
            ("parent_routes_preserved", live_routes <= cand_routes),
            ("parent_profiles_preserved", live_profiles + derived.published_hotel_profiles == cand_profiles),
        ))),
        ("byte_preservation", OrderedDict((
            ("files_live", len(live_files)),
            ("files_candidate", len(cand_files)),
            ("files_added", len(added)),
            ("files_removed", len(removed)),
            ("files_changed", len(changed)),
            ("added_by_class", OrderedDict((k, len(v)) for k, v in added_by.items())),
            ("removed_by_class", OrderedDict((k, len(v)) for k, v in removed_by.items())),
            ("changed_by_class", OrderedDict((k, len(v)) for k, v in changed_by.items())),
            ("changed_global_artifacts", changed_by["global_regenerated"]),
            ("prior_market_files_changed", changed_by["prior_market"]),
            ("unclassified_paths", added_by["unclassified"] + changed_by["unclassified"]),
        ))),
        ("hold_safety", OrderedDict((
            ("approved_profiles", approved),
            ("fort_myers_pages_in_candidate", len(fm_profile_files)),
            ("fort_myers_hotel_profile_pages", len(fm_hotel_pages)),
            ("UNAPPROVED_FORT_MYERS_PROFILES", len(unapproved)),
            ("unapproved_examples", unapproved[:10]),
            ("unresolved_kept_unpublished", recon["unresolved"]),
            ("verified_no_pets_are_exclusions_not_profiles", recon["verified_no_pets"]),
        ))),
        ("cross_market_collision_safety", collisions),
        ("identity_safety", identity),
        ("outside_hotel_inventory_safety", outside),
        ("operating_status_safety", operating),
        ("route_scheme_safety", schemes),
        ("reader_safety", reader),
        ("fast_receipt_safety", fast_receipt),
        ("release_factory_accounting", rendering),
        ("candidate_determinism", determinism),
        ("deployment_eligibility", eligibility),
        ("problems", problems),
        ("ALL_ACCOUNTING_GATES", "PASS" if not problems else "FAIL"),
        ("nothing_deployed", True),
    ))

    print(json.dumps(OrderedDict((
        ("candidate", {k: v for k, v in report["candidate_bundle"].items()}),
        ("totals_agree", report["totals_against_projection"]["AGREE"]),
        ("fort_myers", {k: v for k, v in fm.items() if k not in ("route_set_agreement_with_registration_staging",)}),
        ("route_set_agreement", staging_agreement["EXACT_ROUTE_SET_AGREEMENT"]),
        ("municipality_pages", identity["MUNICIPALITY_PAGES"]),
        ("founder_premises_pages", identity["FOUNDER_PREMISES_PAGES"]),
        ("travelodge_pages", identity["published_travelodge_pages"]),
        ("fee_safety", {k: v for k, v in identity["fee_safety"].items() if k != "wrong"}),
        ("unapproved_profiles", report["hold_safety"]["UNAPPROVED_FORT_MYERS_PROFILES"]),
        ("files_added", len(added)), ("files_removed", len(removed)), ("files_changed", len(changed)),
        ("changed_global", changed_by["global_regenerated"]),
        ("prior_market_changed", changed_by["prior_market"]),
        ("delta", {k: v for k, v in report["delta_safety"].items() if k not in ("findings",)}),
        ("collisions", {k: v for k, v in collisions.items() if k.isupper()}),
        ("held_rows_published", identity["HELD_ROWS_PUBLISHED"]),
        ("held_groups", OrderedDict((k, "%d rows / %s" % (v["rows"], "PUBLISHED" if v["published"] else "0 published"))
                                    for k, v in identity["groups"].items())),
        ("verified_no_pets_published_as_profiles", identity["VERIFIED_NO_PETS_PUBLISHED_AS_PROFILES"]),
        ("outside_inventory", {k: v for k, v in outside.items() if k != "classes"}),
        ("outside_inventory_rows", {k: v["rows"] for k, v in outside["classes"].items()}),
        ("operating_status", operating),
        ("route_schemes", {k: v for k, v in schemes.items()}),
        ("reader_safety", reader),
        ("fast_receipt", fast_receipt),
        ("rendering", rendering),
        ("determinism", determinism),
        ("eligibility", eligibility),
        ("ALL_ACCOUNTING_GATES", report["ALL_ACCOUNTING_GATES"]),
    )), indent=1))
    for p in problems:
        print("   !", p)

    if args.write:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("written:", os.path.relpath(args.out, _DASH))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

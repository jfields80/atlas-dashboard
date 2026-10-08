"""PTF-FORT-MYERS-FL-REGISTRATION-AND-STAGING-002 -- the bounded staging gates for Fort Myers / Cape Coral /
Sanibel's registration.

    python -m scripts.pettripfinder.fort_myers_fl_registration_checks_002 --site C:/t/fm3/oa/site [--write]

Cloned in shape from the previous registration's checks (002). READ ONLY. Every count is derived from the registered
sealed package, its receipt, the lane report the seal wrote, the site the seal's own FAST build produced, the committed
Fort Myers reports and the committed shared registries. Nothing here publishes, authorizes or deploys, and no held
identity row is resolved.

Fort Myers' own held cohort, checked by name on top of the class counts (the founder's ruling for this order):
  * Comfort Suites and MainStay Suites at 9455 Old Luckett Rd -- two brands on one campus, the shared premises
    unproven -- kept held: neither publishes, and neither is written into identity_resolutions.json;
  * 4760 S Cleveland Ave -- the current identity candidate is Quality Inn, the retired identity is Travelodge -- the
    rebrand successor is held in the sealed package, so nothing publishes at 4760 and no Travelodge policy evidence
    migrates to it (the pet-friendly Travelodge Fort Myers/Cape Coral is the separate 13353 N Cleveland building);
  * Latitude 26 Waterfront Inn & Suites -- ZIP 34134, the State licence names Collier -- held OUTSIDE; every other
    Latitude 26 row stays unpublished;
  * Pink Shell Beach Resort & Marina and Edison Beach House -- refusals the SHARED reader does not read as operative
    -- kept held: never pet-friendly and never verified-no-pets; the shared reader is not touched;
  * every other unresolved row, the timeshare / vacation-ownership identities and the condo / residence / rental rows
    stay unpublished;
  * CAPE CORAL, FORT MYERS BEACH, SANIBEL, CAPTIVA, ESTERO, BONITA SPRINGS, NORTH FORT MYERS AND LEHIGH ACRES keep
    their own municipality; Naples / Collier admits nothing;
  * no other market's text in the registered documents (other markets' names are read from their own committed
    market documents, never spelled here), and the market label is Fort Myers';
  * every fee the staging withheld publishes no single fee; every published route carries a valid scheme.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(__file__).resolve().parents[2]
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import commercial_actions as CA  # noqa: E402
from scripts.pettripfinder import fast_release_lane as FL  # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
from scripts.pettripfinder import fort_myers_fl_census_reconciliation_001 as CR  # noqa: E402
from scripts.pettripfinder import fort_myers_fl_clone_residue_scan_001 as CRS  # noqa: E402
from scripts.pettripfinder import fort_myers_fl_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder import fort_myers_fl_nonhotel_rulings_001 as NH  # noqa: E402
from scripts.pettripfinder import fort_myers_fl_publication_safety_audit_001 as SAFE  # noqa: E402
from scripts.pettripfinder import launch_participation as LP  # noqa: E402
from scripts.pettripfinder import release_contracts as RC  # noqa: E402
from scripts.pettripfinder import release_index as RI  # noqa: E402

WORK_ORDER = "PTF-FORT-MYERS-FL-REGISTRATION-AND-STAGING-002"
MARKET_ID = "fort-myers-fl"
MARKET_LABEL = "Fort Myers, Cape Coral & Sanibel, Florida"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
STAGING = PKG / "markets" / "staging" / MARKET_ID
LANE_REPORT = REPORTS / "fort_myers_fl_registration_release_lane.json"
OUT = REPORTS / "fort_myers_fl_registration_checks_002.json"
SOURCE_PACKAGE = "pkg-fort-myers-fl-68b3cfa8bc4758c5"
SOURCE_DIGEST = "sha256:68b3cfa8bc4758c5b0d935d385fee3404ab01ed569f65ca2dc52d0c1733a2415"
SOURCE_RECEIPT = "pkg-fort-myers-fl-68b3cfa8bc4758c5-4a056b97814fece9.json"
EXPECTED_PROFILES = 57
EXPECTED_VERIFIED_NO_PETS = 34
EXPECTED_CENSUS = 142
EXPECTED_UNRESOLVED = 51
EXPECTED_COUNTIES = OrderedDict((("Lee", 142),))
EXPECTED_FEES = (5, 22, 5)   # single-basis published, tiered withheld, unsafe withheld
#: the founder-class rows the source-ready order held, by class: no dual-brand row among the ADMITTED rows (the Old
#: Luckett pair was never admitted); two refusals the shared reader will not treat as operative; nothing preopening.
EXPECTED_DUAL_BRAND = 0
EXPECTED_SHARED_READER_REFUSAL = 2
EXPECTED_PREOPENING = 0
#: the founder's ruling (PTF-FORT-MYERS-FL-REGISTRATION-AND-STAGING-002): these stay held and unpublished
OLD_LUCKETT_KEYS = ("comfort suites fort myers east i 75", "mainstay suites fort myers east i 75")
OLD_LUCKETT_HOUSE = "9455"
CLEVELAND_REBRAND_KEY = "quality inn fort myers cape coral"
CLEVELAND_REBRAND_HOUSE = "4760"
RETIRED_IDENTITY_WORD = "travelodge"
LATITUDE_26_KEY = "latitude 26 waterfront inn and suites"
SHARED_READER_KEYS = ("edison beach house hotel", "pink shell beach resort and marina")
PREOPENING_KEYS = ()
#: municipalities the source-ready order decided by postal code that are NOT Fort Myers -- never flattened
OWN_MUNICIPALITIES = ("cape coral", "fort myers beach", "sanibel", "captiva", "estero", "bonita springs",
                      "north fort myers", "lehigh acres", "matlacha", "alva")
NAPLES_WORDS = re.compile(r"\b(naples|marco island|everglades city|immokalee|collier)\b", re.I)
#: The lineage sentence the release contract states (the live release this market was built on), and the cross-market
#: collision reasons naming the live market whose identity a row would steal -- the only places another market's name
#: may stand in a registered document.
RESIDUE_ALLOWED = re.compile(r"-live hardened lineage|already published by|already (?:a )?live|"
                             r"CROSS_MARKET_LIVE_IDENTITY_COLLISION|EXISTING_LIVE_MARKETS", re.I)
BOUNDARY_PLACES = ("NAPLES_NORTH_NAPLES_GOLDEN_GATE_EAST_NAPLES", "MARCO_ISLAND_GOODLAND",
                   "EVERGLADES_CITY_CHOKOLOSKEE_OCHOPEE", "IMMOKALEE_AVE_MARIA",
                   "PUNTA_GORDA_BABCOCK_RANCH_HARBOUR_HEIGHTS", "PORT_CHARLOTTE",
                   "ENGLEWOOD_PLACIDA_ROTONDA_BOCA_GRANDE",
                   "PINE_ISLAND_BOKEELIA_ST_JAMES_CITY_PINELAND_AND_CABBAGE_KEY",
                   "LABELLE_CLEWISTON_FELDA_MOORE_HAVEN", "SARASOTA_BRADENTON_VENICE_NORTH_PORT_ARCADIA")
_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")
#: the bare CHAIN collision class (the canary carried from earlier markets): a name built only of chain words and words
#: that distinguish nothing names a chain, not a property, and may never reach the shared registry.
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


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _norm(v):
    return " ".join(str(v or "").lower().split())


def _fold(v):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", _norm(v)).split())


def _house(street):
    m = re.match(r"\s*(\d+)", str(street or ""))
    return m.group(1) if m else ""


def _bare_chain(name):
    toks = [t for t in re.sub(r"[^a-z0-9 ]", " ", _norm(name)).split() if t]
    return bool(toks) and any(t in CHAIN_WORDS for t in toks) and all(t in CHAIN_WORDS or t in GENERIC_WORDS
                                                                       for t in toks)


def _residue(text, rx):
    hits = []
    for line in text.splitlines():
        for m in rx.finditer(line):
            window = line[max(0, m.start() - 80):m.end() + 80]
            if not RESIDUE_ALLOWED.search(window):
                hits.append(window.strip()[:160])
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="the site the seal's own FAST build produced")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    problems = []
    lane = _load(LANE_REPORT)
    sealed = lane["sealed_package"]
    package = _load(_DASH / sealed["path"])
    receipt_rel = lane["fast_lane_receipt"]["path"]
    receipt = _load(_DASH / receipt_rel)
    act = _load(REPORTS / "fort_myers_fl_actionability_001.json")
    clean = _load(REPORTS / "fort_myers_fl_clean_authority_001.json")
    fees = _load(REPORTS / "fort_myers_fl_fee_withholding_001.json")
    accounting = _load(REPORTS / "fort_myers_fl_source_ready_accounting_001.json")
    census = _load(PKG / "identity_census" / ("%s.json" % MARKET_ID))
    site = Path(args.site)

    # ---- package identity: the registered package carries the source-ready package's content -------------
    source = _load(STAGING / "shadow_packages" / MARKET_ID / ("%s.json" % SOURCE_PACKAGE))
    same_content = OrderedDict((k, package[k] == source[k]) for k in (
        "census", "pet_friendly_records", "verified_no_pets_records", "seed_rows", "partition",
        "official_routes", "evidence_references", "unresolved_rows", "founder_holds"))
    if source.get("package_digest") != SOURCE_DIGEST:
        problems.append("the source-ready package on disk is not %s" % SOURCE_DIGEST)
    if not all(same_content.values()):
        problems.append("the registered package's content differs from %s: %s"
                        % (SOURCE_PACKAGE, [k for k, v in same_content.items() if not v]))
    j = receipt["RESULTS"]["J"]["detail"]
    source_bundle = _load(STAGING / "shadow_receipts" / MARKET_ID / SOURCE_RECEIPT)["RESULTS"]["J"]["detail"]["bundle_sha256"]
    same_bundle = j.get("bundle_sha256") == source_bundle
    if not same_bundle:
        problems.append("the registered package builds a different bundle than the source-ready shadow package")
    other_packages = sorted(Path(p).stem for p in glob.glob(str(STAGING / "shadow_packages" / MARKET_ID / "*.json"))
                            if Path(p).stem != SOURCE_PACKAGE)

    # ---- held-row safety, on the BUILT site ---------------------------------------------------------------
    pf_keys = {r["identity_key"] for r in package["pet_friendly_records"]}
    approved = {r["identity_key"] for r in clean["rows"] if r["disposition"] == "CLEAN_PET_FRIENDLY"}
    # Routes are compared as the SITE forms them (release_index.hotel_route over the display name), never by slug.
    from scripts.pettripfinder.markets.contract import parse_market
    market_cfg = parse_market(_load(PKG / "markets" / ("%s.json" % MARKET_ID)), source=MARKET_ID)
    hub_route = "/pet-friendly-hotels/%s/" % MARKET_ID
    corridor_routes = {"%s%s/" % (hub_route, c.slug) for c in market_cfg.corridors}
    built_routes = {"/" + p.relative_to(site).parent.as_posix() + "/"
                    for p in (site / hub_route.strip("/")).glob("*/index.html")} - corridor_routes \
        - {hub_route + "policy-comparison/"}
    sitemap = set(_LOC.findall((site / "sitemap.xml").read_text(encoding="utf-8")))
    approved_routes = set(RI.index_from_package(package, participating=True).hotel_routes)
    unapproved_built = sorted(built_routes - approved_routes)
    if unapproved_built:
        problems.append("built Fort Myers profiles not in the approved cohort: %s" % unapproved_built[:5])
    if pf_keys != approved:
        problems.append("the package's pet-friendly set is not the approved cohort")
    name_of = {h["identity_key"]: h["canonical_name"] for h in census["hotels"]}
    for h in census.get("non_admitted") or ():
        name_of.setdefault(h["identity_key"], h["canonical_name"])
    name_of.update({r["identity_key"]: r["canonical_name"] for r in clean["rows"]})

    def published(keys):
        out = []
        for k in keys:
            route = RI.hotel_route(market_cfg, name_of.get(k, k))
            if k in pf_keys or route in built_routes or route in sitemap or route in approved_routes:
                out.append(k)
        return out

    rows = act["rows"]
    unresolved_keys = {r["identity_key"] for r in rows}
    admitted_keys = {h["identity_key"] for h in census["hotels"]}
    non_admitted_rows = list(census.get("non_admitted") or ())
    TIMESHARE_KEYS = tuple(sorted({h["identity_key"] for h in non_admitted_rows
                                   if h["identity_key"] not in admitted_keys
                                   and h.get("classification") == "NON_LODGING"
                                   and NH.exclusion_class(h.get("classification_reason")) == "TIMESHARE"}))
    # A non-admitted row whose key an ADMITTED row also carries is checked through the admitted row's own hold
    # (all_unresolved), never as a refusal.
    RENTAL_KEYS = tuple(sorted({h["identity_key"] for h in non_admitted_rows
                                if h["identity_key"] not in admitted_keys and (
                                    (h.get("classification") == "NON_LODGING"
                                     and NH.exclusion_class(h.get("classification_reason")) in ("VACATION_RENTAL",
                                                                                                "RESORT_RESIDENCE"))
                                    or "LODGING_QUALIFICATION_UNPROVEN" in (h.get("classification_reason") or "")
                                    or "LODGING_CATEGORY_UNCONFIRMED" in (h.get("classification_reason") or "")
                                    or "RESORT_RESIDENCE_UNCONFIRMED" in (h.get("classification_reason") or ""))}))
    LATITUDE_KEYS = tuple(sorted({k for k in name_of if k.startswith("latitude 26")}))
    groups = OrderedDict((
        ("dual_brand", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"
                        and r["disposition"] == "IDENTITY_MISMATCH_HOLD"]),
        ("shared_reader_refusal_founder", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"
                                           and r["disposition"] != "IDENTITY_MISMATCH_HOLD"]),
        ("preopening", [r["identity_key"] for r in rows if r["actionability"] == "HELD_UNTIL_OPENING"]),
        ("router_exhausted", [r["identity_key"] for r in rows if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]),
        ("founder_ruling_old_luckett_dual_brand", list(OLD_LUCKETT_KEYS)),
        ("founder_ruling_4760_cleveland_rebrand", [CLEVELAND_REBRAND_KEY]),
        ("founder_ruling_latitude_26", list(LATITUDE_KEYS)),
        ("founder_ruling_pink_shell_edison", [k for k in SHARED_READER_KEYS if k in unresolved_keys]),
        ("timeshare", list(TIMESHARE_KEYS)),
        ("private_condo_residence_or_rental", list(RENTAL_KEYS)),
    ))
    for disp, n in sorted(Counter(r["disposition"] for r in rows).items()):
        groups["disposition_" + disp] = [r["identity_key"] for r in rows if r["disposition"] == disp]
    groups["all_unresolved"] = [r["identity_key"] for r in rows]
    held = OrderedDict()
    for name, keys in groups.items():
        leaked = published(keys)
        held[name] = OrderedDict((("rows", len(keys)), ("published", len(leaked)), ("leaked", leaked[:5])))
        if leaked:
            problems.append("%s rows published: %s" % (name, leaked[:5]))
    if groups["dual_brand"]:
        problems.append("founder-class identity holds appeared: %s" % groups["dual_brand"])
    if sorted(groups["preopening"]) != sorted(PREOPENING_KEYS):
        problems.append("preopening holds appeared: %s" % groups["preopening"])
    if sorted(groups["shared_reader_refusal_founder"]) != sorted(SHARED_READER_KEYS):
        problems.append("the shared-reader founder holds are not Pink Shell and Edison Beach House: %s"
                        % groups["shared_reader_refusal_founder"])
    # the founder's ruling, by name: no profile, no release-index route, no served route, no PF / NP record
    np_records = package["verified_no_pets_records"]
    np_keys_all = {r.get("identity_key") or r.get("normalized_name") for r in np_records}
    index_routes = set(package["intended_delta"]["add_routes"])
    disposition_of = {r["identity_key"]: r["disposition"] for r in clean["rows"]}
    non_admitted = {}
    for h in non_admitted_rows:
        non_admitted.setdefault(h["identity_key"], []).append(h)
    absent_rows = OrderedDict()
    ruling_keys = list(OLD_LUCKETT_KEYS) + [CLEVELAND_REBRAND_KEY] + list(LATITUDE_KEYS) + list(SHARED_READER_KEYS)
    for key in ruling_keys + list(PREOPENING_KEYS) + list(TIMESHARE_KEYS) + list(RENTAL_KEYS):
        if key in absent_rows:
            continue
        route = RI.hotel_route(market_cfg, name_of.get(key, key))
        absent_rows[key] = OrderedDict((
            ("census_state", "ADMITTED" if key in admitted_keys else
             ("NOT_ADMITTED:" + "|".join(sorted({h["classification"] for h in non_admitted[key]})))
             if key in non_admitted else "MISSING"),
            ("disposition", disposition_of.get(key)),
            ("route", route),
            ("PROFILE", "present" if key in pf_keys or route in built_routes else "absent"),
            ("VERIFIED_NO_PETS_RECORD", "present" if key in np_keys_all else "absent"),
            ("RELEASE_INDEX_ROUTE", "present" if route in index_routes else "absent"),
            ("SERVED_ROUTE", "present" if route in sitemap else "absent"),
        ))
        if absent_rows[key]["census_state"] == "MISSING" or "present" in absent_rows[key].values():
            problems.append("%s is not safely held: %s" % (key, absent_rows[key]))
    for key in TIMESHARE_KEYS + RENTAL_KEYS:
        if not absent_rows[key]["census_state"].startswith("NOT_ADMITTED"):
            problems.append("%s is no longer refused: %s" % (key, absent_rows[key]["census_state"]))

    # 9455 Old Luckett and 4760 S Cleveland, by ADDRESS: no published record, seed row or route sits at either premises,
    # and no Travelodge evidence is carried to 4760 (the retired identity's policy never migrates to its successor).
    def _at(house, street_word, rows_, field):
        """The rows whose own street is ``house`` on the street named by ``street_word``."""
        return [r.get("name") for r in rows_
                if _house(r.get(field)) == house and street_word in _norm(r.get(field))]
    seed_rows = package["seed_rows"]
    id_records = {r["identity_key"]: r for r in package["identity_records"]}
    pf_streets = [OrderedDict((("name", id_records.get(k, {}).get("canonical_name")),
                               ("street", id_records.get(k, {}).get("street")))) for k in pf_keys]
    np_streets = [OrderedDict((("name", (id_records.get(r.get("identity_key")) or {}).get("canonical_name")),
                               ("street", (id_records.get(r.get("identity_key")) or {}).get("street"))))
                  for r in np_records]
    rebrand = OrderedDict((
        ("census", [OrderedDict((("classification", h.get("classification")), ("street", h.get("street")),
                                 ("postal_code", h.get("postal_code")),
                                 ("reason", (h.get("classification_reason") or "")[:240])))
                    for h in non_admitted.get(CLEVELAND_REBRAND_KEY, ()) if h.get("street")]),
        ("seed_rows_at_4760", _at(CLEVELAND_REBRAND_HOUSE, "cleveland", seed_rows, "address")),
        ("pet_friendly_at_4760", _at(CLEVELAND_REBRAND_HOUSE, "cleveland", pf_streets, "street")),
        ("verified_no_pets_at_4760", _at(CLEVELAND_REBRAND_HOUSE, "cleveland", np_streets, "street")),
        ("travelodge_published_records", [OrderedDict((("name", r.get("name")), ("address", r.get("address")),
                                                       ("postal_code", r.get("postal_code")),
                                                       ("source_url", r.get("source_url"))))
                                          for r in seed_rows if RETIRED_IDENTITY_WORD in _norm(r.get("name"))]),
    ))
    rebrand["TRAVELODGE_EVIDENCE_MIGRATED_TO_4760"] = sum(
        1 for r in rebrand["travelodge_published_records"] if _house(r["address"]) == CLEVELAND_REBRAND_HOUSE)
    rebrand["QUALITY_INN_4760_PROMOTED"] = int(bool(rebrand["seed_rows_at_4760"] or rebrand["pet_friendly_at_4760"]
                                                    or rebrand["verified_no_pets_at_4760"]))
    rebrand_ok = (not rebrand["QUALITY_INN_4760_PROMOTED"] and not rebrand["TRAVELODGE_EVIDENCE_MIGRATED_TO_4760"]
                  and any(c["classification"] == "SAME_IDENTITY_REBRAND_SUCCESSOR" for c in rebrand["census"]))
    if not rebrand_ok:
        problems.append("4760 S Cleveland ruling: %s" % rebrand)
    old_luckett = OrderedDict((
        ("census", [OrderedDict((("identity_key", h["identity_key"]), ("classification", h.get("classification")),
                                 ("street", h.get("street"))))
                    for k in OLD_LUCKETT_KEYS for h in non_admitted.get(k, ()) if h.get("street")]),
        ("seed_rows_at_9455", _at(OLD_LUCKETT_HOUSE, "luckett", seed_rows, "address")),
        ("pet_friendly_at_9455", _at(OLD_LUCKETT_HOUSE, "luckett", pf_streets, "street")),
        ("verified_no_pets_at_9455", _at(OLD_LUCKETT_HOUSE, "luckett", np_streets, "street")),
    ))
    old_luckett_ok = (not old_luckett["seed_rows_at_9455"] and not old_luckett["pet_friendly_at_9455"]
                      and not old_luckett["verified_no_pets_at_9455"] and len(old_luckett["census"]) == 2
                      and all(c["classification"] == "SAME_CAMPUS_DISTINCT_ENTITY" for c in old_luckett["census"]))
    if not old_luckett_ok:
        problems.append("9455 Old Luckett ruling: %s" % old_luckett)
    latitude = OrderedDict((k, absent_rows[k]["census_state"]) for k in LATITUDE_KEYS)
    latitude_ok = (LATITUDE_26_KEY in LATITUDE_KEYS and "OUTSIDE_MARKET" in latitude[LATITUDE_26_KEY]
                   and all("present" not in absent_rows[k].values() for k in LATITUDE_KEYS))
    if not latitude_ok:
        problems.append("Latitude 26 ruling: %s" % latitude)

    # ---- municipalities, Naples and Florida (never flattened) -----------------------------------------------
    by_county = Counter(GEO.county_for_postal(h.get("postal_code")) or "" for h in census["hotels"])
    wrong_city = [(h["identity_key"], h.get("city"), h.get("postal_code")) for h in census["hotels"]
                  if GEO.municipality_conflict(h.get("postal_code"), h.get("city"))]
    not_florida = [h["identity_key"] for h in census["hotels"] if GEO.state_for_postal(h.get("postal_code")) != "FL"
                   or (h.get("state") or "FL").upper() not in ("FL", "FLORIDA")]
    naples_admitted = [h["identity_key"] for h in census["hotels"]
                       if NAPLES_WORDS.search(" ".join(str(h.get(f) or "") for f in ("city", "county")))
                       or (GEO.county_for_postal(h.get("postal_code")) or "") != "Lee"]
    own_muni_flattened = [h["identity_key"] for h in census["hotels"]
                          if GEO.normalise_municipality(h.get("city")) == "fort myers"
                          and GEO.normalise_municipality(GEO.municipality_for_postal(h.get("postal_code"),
                                                                                     h.get("city")))
                          in OWN_MUNICIPALITIES]
    seed_city = OrderedDict()
    admitted_by_key = {h["identity_key"]: h for h in census["hotels"]}
    seed_by_name = {_fold(r.get("name")): r for r in seed_rows}
    for k in pf_keys:
        h = admitted_by_key.get(k) or {}
        r = seed_by_name.get(_fold(id_records.get(k, {}).get("canonical_name"))) or {}
        for field in ("city", "postal_code", "state"):
            v = r.get(field)
            if v and h.get(field) and str(v).strip().lower() != str(h.get(field)).strip().lower():
                seed_city.setdefault(k, []).append((field, v, h.get(field)))
    naples_seed = [r.get("name") for r in seed_rows if NAPLES_WORDS.search(str(r.get("city") or ""))
                   or (GEO.county_for_postal(r.get("postal_code")) or "") != "Lee"]
    env = CR.ADMITTED_PIN_ENVELOPE
    envelope_is_fort_myers = (CRS.UT_LAT[0] < env["min_lat"] < env["max_lat"] < CRS.UT_LAT[1]
                              and CRS.UT_LNG[0] < env["min_lng"] < env["max_lng"] < CRS.UT_LNG[1])
    municipality = OrderedDict((
        ("QUALIFYING_BY_COUNTY", OrderedDict(sorted(by_county.items()))),
        ("rows_in_no_admitted_county", by_county.get("", 0)),
        ("WRONG_CITY_FORT_MYERS_IDENTITIES", len(wrong_city)), ("wrong_city", wrong_city[:5]),
        ("OWN_MUNICIPALITY_FLATTENED_TO_FORT_MYERS", len(own_muni_flattened)),
        ("own_municipality_flattened", own_muni_flattened[:5]),
        ("NAPLES_PROFILES_ADMITTED", len(naples_admitted)), ("naples_admitted", naples_admitted[:5]),
        ("NAPLES_SEED_ROWS", len(naples_seed)),
        ("NOT_FLORIDA", len(not_florida)), ("not_florida", not_florida[:5]),
        ("census_by_municipality", OrderedDict(sorted(Counter(h.get("city") for h in census["hotels"]).items()))),
        ("published_by_municipality", OrderedDict(sorted(Counter(h.get("city") for h in census["hotels"]
                                                                  if h["identity_key"] in pf_keys).items()))),
        ("SEED_ROWS_ADDRESS_REWRITTEN", len(seed_city)), ("seed_conflicts", list(seed_city.items())[:5]),
        ("ADMITTED_PIN_ENVELOPE", env), ("FORT_MYERS_ENVELOPE_AUTHORITATIVE", envelope_is_fort_myers),
    ))
    municipality_ok = (not wrong_city and not own_muni_flattened and not naples_admitted and not naples_seed
                       and not not_florida and not seed_city and envelope_is_fort_myers
                       and OrderedDict(sorted(by_county.items())) == OrderedDict(sorted(EXPECTED_COUNTIES.items())))
    if not municipality_ok:
        problems.append("municipality / Naples safety: %s" % OrderedDict(
            (k, v) for k, v in municipality.items()
            if k not in ("ADMITTED_PIN_ENVELOPE", "census_by_municipality", "published_by_municipality")))

    # ---- market text safety: the REGISTERED documents carry no other market's text -------------------------
    tokens, _zips = CRS.other_markets()
    token_rx = CRS._token_rx(tokens)
    d_text, d_coord, d_zip = CRS.scan_data(token_rx)   # census, market document, policy, authority, partition
    extra_docs = [_DASH / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET_ID)] \
        + sorted((PKG / "markets" / "authority" / MARKET_ID).glob("*"))
    residue = OrderedDict()
    for p in extra_docs:
        hits = _residue(p.read_text(encoding="utf-8"), token_rx)
        if hits:
            residue[p.relative_to(_DASH).as_posix()] = hits[:5]
    lineage_statements = [m.group(0) for m in re.finditer(r"[A-Za-z .]+-live hardened lineage",
                                                          extra_docs[0].read_text(encoding="utf-8"))]
    policy = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET_ID))
    contract_doc = _load(_DASH / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET_ID))
    hub_html = (site / hub_route.strip("/") / "index.html").read_text(encoding="utf-8")
    label_ok = (market_cfg.market_id == MARKET_ID and MARKET_LABEL in contract_doc.get("description", "")
                and _load(PKG / "markets" / ("%s.json" % MARKET_ID)).get("market_name") == MARKET_LABEL)
    boundary = (accounting.get("county_and_border_boundary") or {}).get("refused_places") or {}
    boundary_ok = all(p in boundary and not boundary[p].get("admitted") for p in BOUNDARY_PLACES)
    text_safety = OrderedDict((
        ("CLONE_MARKET_TEXT_RESIDUE", len(d_text) + sum(len(v) for v in residue.values())),
        ("CLONE_COORDINATE_RESIDUE", len(d_coord)),
        ("CLONE_BOUNDARY_RESIDUE", len(d_zip)),
        ("other_market_tokens", len(tokens)),
        ("data_text_hits", d_text[:5]), ("registered_document_hits", residue),
        ("lineage_statement_allowed_by_name", lineage_statements),
        ("documents_scanned", len(CRS.DATA_DOCUMENTS) + len(extra_docs)),
        ("FORT_MYERS_MARKET_LABEL_CORRECT", label_ok), ("market_label", MARKET_LABEL),
        ("hub_page_names_label", MARKET_LABEL.split(",")[0] in hub_html),
        ("policy_package_market_field", policy.get("market")),
        ("BOUNDARY_AUDIT_PLACES", OrderedDict((p, boundary.get(p)) for p in BOUNDARY_PLACES)),
        ("boundary_audit_fort_myers", boundary_ok),
    ))
    if d_text or d_coord or d_zip or residue or not label_ok or not boundary_ok:
        problems.append("market text safety: data %s, docs %s, label %s, boundary %s"
                        % (d_text[:2], list(residue)[:3], label_ok, boundary_ok))

    # Rows the identity graph did not admit must never publish under their names.
    pf_by_name = {_fold(r.get("name")): r["identity_key"] for r in package["pet_friendly_records"]}
    outside = Counter()
    outside_published = []
    same_name_observations = []
    for h in non_admitted_rows:
        outside[h.get("classification")] += 1
        key = pf_by_name.get(_fold(h.get("canonical_name")))
        if key is None:
            continue
        a = admitted_by_key.get(key) or {}
        row = OrderedDict((("classification", h.get("classification")), ("canonical_name", h.get("canonical_name")),
                           ("street", h.get("street") or ""), ("postal_code", h.get("postal_code") or ""),
                           ("lanes", h.get("lanes")), ("published_identity_key", key),
                           ("published_street", a.get("street")), ("published_postal_code", a.get("postal_code"))))
        observation = h.get("classification") in ("IDENTITY_REVIEW_REQUIRED", "NAME_ONLY_UNRESOLVED")
        same_place = not row["postal_code"] or row["postal_code"] == (a.get("postal_code") or "")
        same_building = bool(_house(row["street"]) and _house(row["street"]) == _house(a.get("street"))
                             and row["postal_code"] and row["postal_code"] == (a.get("postal_code") or ""))
        if observation and same_place:
            same_name_observations.append(row)
        elif same_building:
            row["second_sighting"] = "SAME_BUILDING (house number + postal code)"
            same_name_observations.append(row)
        else:
            outside_published.append(row)
    if outside_published:
        problems.append("rows held outside the census publish: %s"
                        % [(r["classification"], r["canonical_name"]) for r in outside_published[:5]])

    # ---- reader and fee safety, over the registered root documents (byte-identical to the sealed copies) ---
    authority = _load(PKG / "fort_myers_fl_proposed_authority_001.json")
    findings = SAFE.audit(policy, authority)
    safety = OrderedDict((k.upper(), len(v)) for k, v in findings.items())
    for k, v in safety.items():
        if v:
            problems.append("%s = %s" % (k, v))
    np_keys = {r.get("identity_key") or r.get("normalized_name") for r in np_records}
    if pf_keys & np_keys:
        problems.append("rows both pet-friendly and verified no-pets: %s" % sorted(pf_keys & np_keys)[:5])
    no_identity_resolutions = not (PKG / "markets" / "authority" / MARKET_ID / "identity_resolutions.json").exists()
    if not no_identity_resolutions:
        problems.append("identity_resolutions.json exists for %s" % MARKET_ID)
    fee_by_quote = {}
    for h in policy["hotels"]:
        for e in h["evidence"]:
            fee_by_quote.setdefault(e["quote"], []).append(h)
    withheld = [("TIERED", x) for x in fees["tiered"]] + [(x["why"].split(" --")[0], x) for x in fees["unsafe"]]
    flattened, matched = [], 0
    for why, x in withheld:
        for h in fee_by_quote.get(x["quote"], ()):
            matched += 1
            if h["facts"].get("pet_fee"):
                flattened.append((why, h["name"], h["facts"]["pet_fee"]))
    published_single = sum(1 for h in policy["hotels"] if h["facts"].get("pet_fee"))
    fee_safety = OrderedDict((
        ("SINGLE_BASIS_FEES_PUBLISHED", published_single),
        ("TIERED_FEES_WITHHELD", len(fees["tiered"])), ("UNSAFE_FEES_WITHHELD", len(fees["unsafe"])),
        ("withheld_entries", len(withheld)), ("records_matched_by_quote", matched),
        ("by_reason", OrderedDict(sorted(Counter(w for w, _ in withheld).items()))),
        ("WITHHELD_FEES_FLATTENED", len(flattened)), ("flattened", flattened[:5]),
        ("MISLEADING_SINGLE_FEES_PUBLISHED", safety["MISLEADING_SINGLE_FEE_PUBLISHED"]),
        ("published_fees", [OrderedDict((("name", h["name"]), ("pet_fee", h["facts"]["pet_fee"])))
                            for h in policy["hotels"] if h["facts"].get("pet_fee")]),
    ))
    if flattened or (published_single, len(fees["tiered"]), len(fees["unsafe"])) != EXPECTED_FEES:
        problems.append("fee safety: %s" % OrderedDict((k, v) for k, v in fee_safety.items()
                                                       if k in ("SINGLE_BASIS_FEES_PUBLISHED", "TIERED_FEES_WITHHELD",
                                                                "UNSAFE_FEES_WITHHELD", "WITHHELD_FEES_FLATTENED")))

    # ---- route schemes: every outbound destination this market publishes is a valid absolute URL -------------
    route_urls = []
    for r in seed_rows:
        for f in ("website_url", "source_url"):
            if r.get(f):
                route_urls.append((r.get("name"), f, r[f]))
    for p in (PKG / "markets" / "authority" / MARKET_ID).glob("*.json"):
        for _path, leaf in CRS._walk(_load(p)):
            if isinstance(leaf, str) and ("://" in leaf or leaf.startswith("www.")):
                route_urls.append((p.name, _path, leaf))
    invalid_routes = [(n, f, u) for n, f, u in route_urls if not CA._validate_destination(u)]
    route_safety = OrderedDict((("destinations_checked", len(route_urls)),
                                ("INVALID_ROUTE_SCHEMES", len(invalid_routes)), ("invalid", invalid_routes[:5])))
    if invalid_routes:
        problems.append("invalid route schemes: %s" % invalid_routes[:5])

    # ---- projected accounting, from candidate SETS ---------------------------------------------------------
    delta = package["intended_delta"]
    fm_index = sorted(delta["add_routes"])
    fm_served = sorted(r for r in sitemap if r.startswith(hub_route))
    live_idx, live_state, live_problems = RI.live_index()
    if live_problems:
        problems.append("current live could not be established: %s" % live_problems[:3])
    candidate = RI.compose(live_idx, RI.index_from_package(package, participating=True), participates=True)
    diff = RI.compare(live_idx, candidate, package_market=MARKET_ID, intended_delta=delta)
    live_routes = {r for i in live_idx.markets.values() if i.participating for r in i.routes}
    cand_routes = {r for i in candidate.markets.values() if i.participating for r in i.routes}
    if not diff["passed"]:
        problems.append("release_index.compare findings: %s" % diff["findings"][:3])
    if not live_routes <= cand_routes:
        problems.append("parent release-index routes lost: %d" % len(live_routes - cand_routes))
    new_markets = sorted(set(candidate.participating) - set(live_idx.participating))
    lost_markets = sorted(set(live_idx.participating) - set(candidate.participating))
    carried = [m for m in live_idx.participating if candidate.markets[m] is live_idx.markets[m]]
    live_manifest = _load(_DASH / "deploy" / "netlify" / "global_deployment_manifest.json")
    live_served = int(live_manifest["sitemap_route_count"])
    cand_served = live_served + len(fm_served)
    profiles = len(package["pet_friendly_records"])
    projected = OrderedDict((
        ("FORT_MYERS_PROJECTED_PROFILES", profiles),
        ("FORT_MYERS_HOTEL_ROUTES", len(candidate.markets[MARKET_ID].hotel_routes)),
        ("FORT_MYERS_CORRIDOR_ROUTES", len(candidate.markets[MARKET_ID].corridor_routes)),
        ("FORT_MYERS_HUB_ROUTES", 1),
        ("FORT_MYERS_RELEASE_INDEX_ROUTES", len(fm_index)),
        ("FORT_MYERS_SERVED_ROUTES", len(fm_served)),
        ("fort_myers_served_not_in_index", sorted(set(fm_served) - set(fm_index))),
        ("fort_myers_served_routes", fm_served),
        ("CANDIDATE_MARKETS", len(candidate.participating)),
        ("CANDIDATE_PROFILES", candidate.total_profiles),
        ("CANDIDATE_RELEASE_INDEX_ROUTES", len(cand_routes)),
        ("CANDIDATE_SERVED_ROUTES", cand_served),
        ("parent", OrderedDict((("deploy_id", live_state.deploy_id), ("markets", len(live_idx.participating)),
                                ("profiles", live_idx.total_profiles),
                                ("release_index_routes", len(live_routes)), ("served_routes", live_served)))),
    ))
    if set(fm_index) - set(fm_served):
        problems.append("declared Fort Myers routes missing from the built sitemap: %s"
                        % sorted(set(fm_index) - set(fm_served))[:5])
    if candidate.total_profiles != live_idx.total_profiles + profiles or profiles != EXPECTED_PROFILES:
        problems.append("profile delta is not exactly +%d" % EXPECTED_PROFILES)
    delta_safety = OrderedDict((
        ("UNEXPECTED_MARKET_DELTA", [m for m in new_markets if m != MARKET_ID] + lost_markets),
        ("UNEXPECTED_PROFILE_DELTA", [] if candidate.total_profiles == live_idx.total_profiles + profiles else
         ["%d != %d + %d" % (candidate.total_profiles, live_idx.total_profiles, profiles)]),
        ("UNEXPECTED_ROUTE_DELTA", sorted(cand_routes - live_routes - set(fm_index))
         + sorted(live_routes - cand_routes)),
        ("PRIOR_MARKETS_LOST", len(lost_markets)),
        ("PRIOR_PROFILES_LOST", sum(len(live_idx.markets[m].profiles) - len(candidate.markets[m].profiles)
                                    for m in live_idx.participating)),
        ("PRIOR_RELEASE_INDEX_ROUTES_LOST", len(live_routes - cand_routes)),
        ("PRIOR_SERVED_ROUTES_LOST", 0),
        ("ONLY_NEW_MARKET", new_markets),
        ("UNCHANGED_BUNDLES_REUSED", len(carried)),
        ("UNCHANGED_MARKETS_REBUILT", len(live_idx.participating) - len(carried)),
        ("release_diff_passed", diff["passed"]), ("finding_counts", diff["finding_counts"]),
    ))
    for k in ("UNEXPECTED_MARKET_DELTA", "UNEXPECTED_PROFILE_DELTA", "UNEXPECTED_ROUTE_DELTA"):
        if delta_safety[k]:
            problems.append("%s = %s" % (k, delta_safety[k][:5]))
    if new_markets != [MARKET_ID]:
        problems.append("Fort Myers is not the only new market: %s" % new_markets)

    # ---- cross-market safety -------------------------------------------------------------------------------
    registry = _load(PKG / "hotel_exclusions.json")["exclusions"]
    by_market = {}
    for r in registry:
        by_market.setdefault(r.get("market_id"), set()).add(_norm(r.get("canonical_name")))
    mine = by_market.get(MARKET_ID, set())
    elsewhere = sorted(n for n in mine if any(n in s for m, s in by_market.items() if m != MARKET_ID))
    dup = sorted(n for n, c in Counter((r.get("market_id"), _norm(r.get("canonical_name"))) for r in registry).items()
                 if c > 1)
    pf_raw = {_norm(r.get("name")) for r in package["pet_friendly_records"]}
    bare = sorted(n for n in mine | pf_raw if _bare_chain(n))
    live_names = {_norm(e.name) for m, i in live_idx.markets.items() if i.participating for e in i.profiles.values()}
    pf_collide = sorted(pf_raw & live_names)
    my_rows = {_norm(r.get("canonical_name")): r for r in registry if r.get("market_id") == MARKET_ID}
    my_seed_names = {_norm(r.get("name")): r for r in package["pet_friendly_records"]}
    bare_exposure = OrderedDict()
    for n in bare:
        mine_row = my_rows.get(n) or my_seed_names.get(n) or {}
        my_postal = str(mine_row.get("postal_code") or "")
        others = []
        for p in sorted(glob.glob(str(PKG / "identity_census" / "*.json"))):
            if Path(p).stem == MARKET_ID:
                continue
            d = _load(p)
            for h in list(d.get("hotels") or ()) + list(d.get("non_admitted") or ()):
                if _norm(h.get("canonical_name")) == n:
                    others.append(OrderedDict((("market", Path(p).stem), ("classification", h.get("classification")),
                                               ("street", h.get("street")), ("postal_code", h.get("postal_code")),
                                               ("same_building", str(h.get("postal_code") or "") == my_postal
                                                and bool(my_postal)))))
        others += [OrderedDict((("market", r.get("market_id")), ("registry_row", True), ("same_building", False)))
                   for r in registry if r.get("market_id") != MARKET_ID and _norm(r.get("canonical_name")) == n]
        others += [OrderedDict((("market", "live"), ("live_profile", True), ("same_building", False)))
                   for x in [n] if x in live_names]
        bare_exposure[n] = OrderedDict((("other_rows", others),
                                        ("OTHER_BUILDINGS_EXPOSED", sum(1 for o in others if not o["same_building"]))))
    bare_exposed = sorted(n for n, v in bare_exposure.items() if v["OTHER_BUILDINGS_EXPOSED"])
    g_findings = [f for f in diff["findings"] if f["code"] in (RI.CROSS_MARKET_IDENTITY_COLLISION,
                                                              RI.OWNERSHIP_MOVEMENT, RI.DUPLICATE_ROUTE)]
    collisions = OrderedDict((
        ("CROSS_MARKET_COLLISIONS", len(elsewhere) + len(pf_collide) + len(g_findings)),
        ("fort_myers_exclusions_named_by_another_market", elsewhere),
        ("fort_myers_profiles_named_by_a_live_market", pf_collide),
        ("identity_or_ownership_findings", g_findings),
        ("BARE_CHAIN_NAMES", len(bare)), ("bare_chain_names", bare),
        ("bare_chain_exposure", bare_exposure),
        ("BARE_CHAIN_COLLISIONS", len(bare_exposed)), ("bare_chain_collisions", bare_exposed),
        ("DUPLICATE_EXCLUDED_IDENTITIES", len(dup)), ("duplicates", dup[:5]),
        ("LIVE_PROPERTIES_MOVED_OR_DISPLACED", len(g_findings)),
    ))
    if collisions["CROSS_MARKET_COLLISIONS"] or bare_exposed or dup:
        problems.append("collision canaries: %s" % OrderedDict((k, v) for k, v in collisions.items() if v))

    # ---- FAST receipt -------------------------------------------------------------------------------------
    eligible = [p.name for p in FL.eligible_receipts(MARKET_ID, package["package_digest"])]
    receipt_ok = (Path(receipt_rel).name in eligible and not FL.receipt_output_defects(receipt)
                  and (j.get("file_count") or 0) > 0 and (j.get("html_count") or 0) > 0
                  and j.get("bundle_sha256") != FL.EMPTY_BUNDLE_SHA256
                  and receipt["RESULTS"]["J"].get("status") == "PASS"
                  and receipt["RESULTS"]["K"]["detail"].get("result") == "BYTE_IDENTICAL")
    if not receipt_ok:
        problems.append("receipt eligibility: selected %s" % eligible)

    # ---- deployment refusal (EXPECTED) ---------------------------------------------------------------------
    netlify = _DASH / "deploy" / "netlify"

    def _naming(directory, id_field):
        out = []
        for path in sorted((netlify / directory).glob("*.json")):
            doc = _load(path)
            names = [m.get("market_id") if isinstance(m, dict) else m for m in (doc.get("participating_markets") or ())]
            if MARKET_ID in names or MARKET_ID in json.dumps(doc):
                out.append(doc.get(id_field) or path.stem)
        return out

    auths = _naming("deployment_authorizations", "authorization_id")
    records = _naming("deployment_records", "deployment_record_id")
    status = LP.launch_status(MARKET_ID)
    refusal = OrderedDict((("authorizations_naming_fort_myers", auths),
                           ("deployment_records_naming_fort_myers", records),
                           ("participation_state", status),
                           ("founder_authorized", status == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
                           ("DEPLOYMENT_REFUSAL", "EXPECTED / PASS" if not auths and not records
                            and status != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH else "FAIL")))
    if refusal["DEPLOYMENT_REFUSAL"] != "EXPECTED / PASS":
        problems.append("Fort Myers is deployable: %s" % refusal)

    contracts = RC.verify_all()
    bad_contracts = {m: p for m, p in contracts.items() if p}
    if bad_contracts:
        problems.append("release contracts disagree: %s" % list(bad_contracts)[:5])
    gate = FPB.evaluate_package(package)

    gates = OrderedDict((
        ("package_identity", all(same_content.values()) and same_bundle and source.get("package_digest") == SOURCE_DIGEST),
        ("registration_lane_eligible", lane["fast_lane_receipt"]["eligible"] == "YES"
         and lane["PACKAGE_REPRODUCIBLE"] == "YES" and lane["CANDIDATE_REPRODUCIBLE"] == "YES"),
        ("fast_receipt_eligibility", receipt_ok),
        ("fast_rules_A_O", lane["fast_lane_receipt"]["rules_passed"] == 15 and not lane["fast_lane_receipt"]["unknown_rules"]),
        ("parent_lookup", not live_problems and package["parent_live_state"]["live_deploy_id"] == live_state.deploy_id),
        ("parent_routes_preserved", live_routes <= cand_routes),
        ("market_preservation", not lost_markets and len(carried) == len(live_idx.participating)),
        ("profile_preservation", not delta_safety["UNEXPECTED_PROFILE_DELTA"]),
        ("route_preservation", not delta_safety["UNEXPECTED_ROUTE_DELTA"]),
        ("candidate_delta", diff["passed"]),
        ("participation_projection", status == "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"),
        ("founder_row_reconciliation", held["dual_brand"]["rows"] == EXPECTED_DUAL_BRAND
         and held["shared_reader_refusal_founder"]["rows"] == EXPECTED_SHARED_READER_REFUSAL
         and held["preopening"]["rows"] == EXPECTED_PREOPENING),
        ("held_cohort_safety", not any(v["published"] for v in held.values()) and not unapproved_built
         and not outside_published and no_identity_resolutions),
        ("founder_ruling_old_luckett_dual_brand_held", old_luckett_ok
         and all("present" not in absent_rows[k].values() for k in OLD_LUCKETT_KEYS)),
        ("founder_ruling_4760_cleveland_quality_inn_held_travelodge_retired", rebrand_ok
         and "present" not in absent_rows[CLEVELAND_REBRAND_KEY].values()),
        ("founder_ruling_latitude_26_held", latitude_ok),
        ("founder_ruling_pink_shell_edison_held", all(
            k in unresolved_keys and "present" not in absent_rows[k].values()
            and absent_rows[k]["disposition"] not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS")
            for k in SHARED_READER_KEYS)),
        ("all_unresolved_unpublished", held["all_unresolved"]["rows"] == EXPECTED_UNRESOLVED
         and not held["all_unresolved"]["published"]),
        ("private_condo_residence_rental_safety", all(absent_rows[k]["census_state"].startswith("NOT_ADMITTED")
                                                      and "present" not in absent_rows[k].values() for k in RENTAL_KEYS)
         and not safety["VACATION_RENTAL_OR_CONDO_PUBLISHED"]),
        ("source_package_selected", sealed["package_id"] not in other_packages
         and package.get("package_id") not in other_packages),
        ("census_counts", census["count"] == EXPECTED_CENSUS and len(pf_keys) == EXPECTED_PROFILES
         and len(np_records) == EXPECTED_VERIFIED_NO_PETS),
        ("municipality_safety", municipality_ok and not safety["WRONG_CITY_LABEL_PUBLISHED"]
         and not safety["OUTSIDE_PARTITION_PUBLISHED"]),
        ("naples_collier_safety", not naples_admitted and not naples_seed and not safety["NAPLES_OR_COLLIER_ADMITTED"]),
        ("boundary_island_safety", not safety["BOUNDARY_ISLAND_PUBLISHED"]),
        ("market_text_safety", not (d_text or d_coord or d_zip or residue) and label_ok and boundary_ok),
        ("operating_status_safety", not safety["NONOPERATING_SIGNAL_PUBLISHED"]
         and not safety["PREOPENING_OR_CLOSED_PUBLISHED"] and not held["preopening"]["published"]),
        ("timeshare_safety", not safety["TIMESHARE_OR_VACATION_OWNERSHIP_PUBLISHED"]
         and all("present" not in absent_rows[k].values() for k in TIMESHARE_KEYS)),
        ("military_safety", not safety["MILITARY_RESTRICTED_PUBLISHED"]),
        ("reader_safety", not safety["PET_FRIENDLY_WITH_EXPLICIT_REFUSAL"] and not safety["QUESTION_ONLY_PET_FRIENDLY"]
         and not safety["SERVICE_ANIMAL_ONLY_PET_FRIENDLY"] and not safety["NO_PETS_QUOTE_WITHOUT_REFUSAL"]
         and not safety["SHARED_READER_DISAGREES"]),
        ("fee_safety", not safety["MISLEADING_SINGLE_FEE_PUBLISHED"] and not flattened
         and (published_single, len(fees["tiered"]), len(fees["unsafe"])) == EXPECTED_FEES),
        ("route_scheme_safety", not invalid_routes and len(route_urls) > 0),
        ("collision_safety", not (collisions["CROSS_MARKET_COLLISIONS"] or bare_exposed or dup)),
        ("first_party_binding", gate["passed"]),
        ("release_contracts", not bad_contracts),
        ("deployment_eligibility_refusal", refusal["DEPLOYMENT_REFUSAL"] == "EXPECTED / PASS"),
    ))
    doc = OrderedDict((
        ("schema", "ptf-registration-staging-checks/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("registered_package", OrderedDict((("package_id", sealed["package_id"]), ("package_digest", sealed["package_digest"]),
                                            ("content_identical_to", SOURCE_PACKAGE), ("content_fields", same_content),
                                            ("same_bundle_as_source", same_bundle),
                                            ("other_source_packages_on_disk", other_packages)))),
        ("held_row_safety", held),
        ("held_rows_absent", absent_rows),
        ("founder_ruling_4760_s_cleveland", rebrand),
        ("founder_ruling_9455_old_luckett", old_luckett),
        ("founder_ruling_latitude_26", latitude),
        ("municipality_safety", municipality),
        ("market_text_safety", text_safety),
        ("UNAPPROVED_FORT_MYERS_PROFILES", len(unapproved_built)),
        ("APPROVED_FORT_MYERS_PROFILES", len(built_routes & approved_routes)),
        ("non_admitted_census_rows", OrderedDict(sorted(outside.items()))),
        ("held_outside_census_published", outside_published),
        ("same_name_observations_of_published_buildings", same_name_observations),
        ("identity_resolutions_written", not no_identity_resolutions),
        ("reader_and_fee_safety", safety),
        ("fee_withholding_preserved", fee_safety),
        ("route_scheme_safety", route_safety),
        ("projected_accounting", projected), ("delta_safety", delta_safety),
        ("cross_market_safety", collisions),
        ("fast_receipt", OrderedDict((("selected", eligible), ("file_count", j.get("file_count")),
                                      ("html_count", j.get("html_count")), ("bundle_sha256", j.get("bundle_sha256")),
                                      ("rule_J", receipt["RESULTS"]["J"].get("status")),
                                      ("rule_K", receipt["RESULTS"]["K"]["detail"].get("result")),
                                      ("defects", FL.receipt_output_defects(receipt))))),
        ("deployment_refusal", refusal),
        ("release_contracts_verified", len(contracts)),
        ("first_party_binding", OrderedDict((k, gate[k]) for k in ("records_evaluated", "eligible", "ineligible", "passed"))),
        ("gates", OrderedDict((k, "PASS" if v else "FAIL") for k, v in gates.items())),
        ("ALL_STAGING_GATES", "PASS" if all(gates.values()) and not problems else "FAIL"),
        ("problems", problems),
        ("nothing_deployed", True), ("nothing_authorized", True),
    ))
    print(json.dumps(OrderedDict((k, doc[k]) for k in ("held_rows_absent", "founder_ruling_4760_s_cleveland",
                                                       "municipality_safety", "fee_withholding_preserved",
                                                       "route_scheme_safety", "delta_safety", "gates",
                                                       "ALL_STAGING_GATES", "problems")),
                     indent=1, default=str)[:16000])
    print(json.dumps(OrderedDict((k, v) for k, v in projected.items() if k != "fort_myers_served_routes"), indent=1))
    if args.write:
        OUT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
        print("written", OUT.relative_to(_DASH).as_posix())
    return 0 if doc["ALL_STAGING_GATES"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

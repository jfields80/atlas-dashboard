"""PTF-KANSAS-CITY-MO-REGISTRATION-AND-STAGING-002 -- the bounded staging gates for Kansas City / Greater Kansas City's
registration.

    python -m scripts.pettripfinder.kansas_city_mo_registration_checks_002 --site C:/t/kc3a/oa/site [--write]

Cloned in shape from Minneapolis's registration checks (002). READ ONLY. Every count is derived from the registered
sealed package, its receipt, the lane report the seal wrote, the site the seal's own FAST build produced, the committed
Kansas City reports and the committed shared registries. Nothing here publishes, authorizes or deploys, and no held
identity row is resolved.

Kansas City's own held cohort, checked by name on top of the class counts (the founder's ruling for this order):
  * three dual-brand buildings, six rows, kept held and unpublished, with no identity_resolutions.json entry --
    Aloft + Element North Kansas City (1875 Diamond Pkwy), AC Hotel + Residence Inn Lenexa City Center (8710 Penrose
    Ln), Courtyard + Residence Inn Kansas City Downtown / Convention Center (1535 Baltimore Ave);
  * two possible rebrands kept held -- Hilton Garden Inn Overland Park (the Wyndham Garden relationship is
    unresolved) and Sleep Inn Olathe (Days Inn evidence at the same address); no rebrand ruling is invented;
  * Extended Stay America Kansas City - Airport - Tiffany Springs (a DataDome CAPTCHA, never bypassed) and the
    Crossland route identity (Extended Stay Kansas City, a fake anti-virus page, never evidence) stay unpublished;
  * the four preopening hotels and the one vacation-ownership identity stay unpublished;
  * two states, never flattened: every registered row keeps the state its own postal code is in (Missouri 630-658,
    Kansas 660-679), and the cross-state name traps the source-ready order decided stay where their codes put them;
  * no Minneapolis / Twin Cities and no Portland / Oregon market text in the registered documents, and the market
    label is Kansas City's;
  * every fee the staging withheld (tiered, basis-less, stay-length -- the three Drury "daily fee" rows among the
    published hotels that carry no fee) publishes no single fee.
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

from scripts.pettripfinder import fast_release_lane as FL  # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
from scripts.pettripfinder import launch_participation as LP  # noqa: E402
from scripts.pettripfinder import release_contracts as RC  # noqa: E402
from scripts.pettripfinder import release_index as RI  # noqa: E402
from scripts.pettripfinder import kansas_city_mo_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder import kansas_city_mo_publication_safety_audit_001 as SAFE  # noqa: E402

WORK_ORDER = "PTF-KANSAS-CITY-MO-REGISTRATION-AND-STAGING-002"
MARKET_ID = "kansas-city-mo"
MARKET_LABEL = "Kansas City / Greater Kansas City, Missouri & Kansas"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
STAGING = PKG / "markets" / "staging" / MARKET_ID
LANE_REPORT = REPORTS / "kansas_city_mo_registration_release_lane.json"
OUT = REPORTS / "kansas_city_mo_registration_checks_002.json"
SOURCE_PACKAGE = "pkg-kansas-city-mo-24718ac004c967b8"
SOURCE_DIGEST = "sha256:24718ac004c967b89e57ccf6215a906465e8edaae97685be5cc6e7258e600402"
SOURCE_RECEIPT = "pkg-kansas-city-mo-24718ac004c967b8-bcbd3d220f61eaa8.json"
EXPECTED_PROFILES = 161
EXPECTED_MISSOURI = 189
EXPECTED_KANSAS = 101
#: the founder rows the source-ready order held, by class: the six REQUIRES_FOUNDER rows are the three dual-brand
#: buildings; no row awaits a shared-reader ruling at founder class; four hotels stated they have not opened.
EXPECTED_DUAL_BRAND = 6
EXPECTED_SHARED_READER_REFUSAL = 0
EXPECTED_PREOPENING = 4
#: the founder's ruling (PTF-KANSAS-CITY-MO-REGISTRATION-AND-STAGING-002): these six stay held and unpublished
DUAL_BRAND_KEYS = (
    "aloft by marriott north kansas city", "element by marriott north kansas city",
    "ac hotel lenexa city center", "residence inn by marriott lenexa city center",
    "courtyard by marriott kansas city downtown convention center",
    "residence inn by marriott kansas city downtown convention center")
#: held outside the admitted census (SAME_IDENTITY_REBRAND_SUCCESSOR): no rebrand ruling is made here
REBRAND_KEYS = ("hilton garden inn overland park", "sleep inn olathe kansas city")
#: admitted and held: the DataDome wall, and the Crossland route identity whose legacy domain served scareware
ESA_TIFFANY_KEY = "extended stay america suites kansas city airport tiffany springs"
CROSSLAND_KEY = "extended stay kansas city"
PREOPENING_KEYS = ("doubletree by hilton kci", "home2 suites by hilton kansas city speedway",
                   "spark by hilton kansas city airport", "the park hotel on the plaza")
TIMESHARE_KEYS = ("worldmark lake of the ozarks",)
#: cross-state name traps the source-ready order decided by postal code: identity_key -> (postal, state, disposition)
FIXED_IDENTITIES = OrderedDict((
    ("sonesta select kansas city south overland park", ("64131", "MO", "CLEAN_PET_FRIENDLY")),
    ("extended stay america suites kansas city shawnee mission", ("66202", "KS", "CLEAN_PET_FRIENDLY")),
    ("drury inn and suites kansas city independence", ("64015", "MO", "CLEAN_PET_FRIENDLY")),
    ("hotel lotus kansas city merriam", ("66203", "KS", "SOURCE_SILENT")),
))
DRURY_KEYS = ("drury inn and suites kansas city airport", "drury inn and suites kansas city independence",
              "drury inn and suites kansas city overland park")
#: another market's words. Allowed only where they are a real Kansas City fact (Minnesota Avenue in Kansas City,
#: Kansas; the Oregon Trail Apartments row), a cross-market collision reason naming the live market whose name a row
#: would steal, or the lineage this market was built on.
RESIDUE = re.compile(r"minneapolis|minnesota|twin cities|st\.? paul|saint paul|portland|oregon", re.I)
RESIDUE_ALLOWED = re.compile(r"minnesota ave|\|minnesota\|66101|oregon[ -]trail|already published by (?:minneapolis-mn|portland-or)|"
                             r"minneapolis-live|\"(?:minneapolis-mn|portland-or)\"", re.I)
BOUNDARY_PLACES = ("lawrence", "topeka", "st_joseph", "columbia", "manhattan", "lake_of_the_ozarks")
_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")
#: the bare CHAIN collision class (the Phoenix / Jacksonville canary): a name built only of chain words and words
#: that distinguish nothing names a chain, not a property, and may never reach the shared registry.
CHAIN_WORDS = frozenset("""
home2 hampton hilton marriott courtyard hyatt holiday comfort quality suburban intown extended woodspring tru
aloft element sheraton westin omni sonesta wyndham baymont ramada days super microtel clarion cambria econo
rodeway sleep candlewood staybridge embassy homewood doubletree springhill fairfield towneplace residence studio
motel red roof quinta radisson country best western surestay delta indigo crowne loews sofitel drury
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


def _bare_chain(name):
    toks = [t for t in re.sub(r"[^a-z0-9 ]", " ", _norm(name)).split() if t]
    return bool(toks) and any(t in CHAIN_WORDS for t in toks) and all(t in CHAIN_WORDS or t in GENERIC_WORDS
                                                                       for t in toks)


def _residue(text):
    hits = []
    for line in text.splitlines():
        for m in RESIDUE.finditer(line):
            window = line[max(0, m.start() - 40):m.end() + 40]
            if not RESIDUE_ALLOWED.search(window):
                hits.append(window.strip()[:120])
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
    act = _load(REPORTS / "kansas_city_mo_actionability_001.json")
    clean = _load(REPORTS / "kansas_city_mo_clean_authority_001.json")
    fees = _load(REPORTS / "kansas_city_mo_fee_withholding_001.json")
    accounting = _load(REPORTS / "kansas_city_mo_source_ready_accounting_001.json")
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
        problems.append("built Kansas City profiles not in the approved cohort: %s" % unapproved_built[:5])
    if pf_keys != approved:
        problems.append("the package's pet-friendly set is not the approved cohort")
    name_of = {h["identity_key"]: h["canonical_name"] for h in census["hotels"]}
    name_of.update({h["identity_key"]: h["canonical_name"] for h in census.get("non_admitted") or ()})
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
    groups = OrderedDict((
        ("dual_brand", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"
                        and r["disposition"] == "IDENTITY_MISMATCH_HOLD"]),
        ("shared_reader_refusal_founder", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"
                                           and r["disposition"] != "IDENTITY_MISMATCH_HOLD"]),
        ("preopening", [r["identity_key"] for r in rows if r["actionability"] == "HELD_UNTIL_OPENING"]),
        ("router_exhausted", [r["identity_key"] for r in rows if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]),
        ("founder_ruling_dual_brand_named", [k for k in DUAL_BRAND_KEYS if k in unresolved_keys]),
        ("founder_ruling_rebrand_holds", list(REBRAND_KEYS)),
        ("esa_tiffany_springs", [k for k in (ESA_TIFFANY_KEY,) if k in unresolved_keys]),
        ("crossland_route_identity", [k for k in (CROSSLAND_KEY,) if k in unresolved_keys]),
        ("timeshare", list(TIMESHARE_KEYS)),
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
    if sorted(groups["dual_brand"]) != sorted(DUAL_BRAND_KEYS):
        problems.append("the founder-class held rows are not exactly the six dual-brand rows: %s" % groups["dual_brand"])
    if sorted(groups["preopening"]) != sorted(PREOPENING_KEYS):
        problems.append("the preopening holds are not the four the source-ready order held: %s" % groups["preopening"])
    for name, keys in (("esa_tiffany_springs", (ESA_TIFFANY_KEY,)), ("crossland_route_identity", (CROSSLAND_KEY,))):
        if groups[name] != list(keys):
            problems.append("%s is no longer held" % name)
    # the founder's ruling, by name: no profile, no release-index route, no served route, no PF / NP record
    np_keys_all = {r.get("identity_key") or r.get("normalized_name") for r in package["verified_no_pets_records"]}
    index_routes = set(package["intended_delta"]["add_routes"])
    disposition_of = {r["identity_key"]: r["disposition"] for r in clean["rows"]}
    admitted_keys = {h["identity_key"] for h in census["hotels"]}
    non_admitted = {h["identity_key"]: h for h in census.get("non_admitted") or ()}
    absent_rows = OrderedDict()
    for key in list(DUAL_BRAND_KEYS) + list(REBRAND_KEYS) + [ESA_TIFFANY_KEY, CROSSLAND_KEY] + list(PREOPENING_KEYS) \
            + list(TIMESHARE_KEYS):
        route = RI.hotel_route(market_cfg, name_of.get(key, key))
        absent_rows[key] = OrderedDict((
            ("census_state", "ADMITTED" if key in admitted_keys else
             ("NOT_ADMITTED:" + non_admitted[key]["classification"]) if key in non_admitted else "MISSING"),
            ("disposition", disposition_of.get(key)),
            ("route", route),
            ("PROFILE", "present" if key in pf_keys or route in built_routes else "absent"),
            ("VERIFIED_NO_PETS_RECORD", "present" if key in np_keys_all else "absent"),
            ("RELEASE_INDEX_ROUTE", "present" if route in index_routes else "absent"),
            ("SERVED_ROUTE", "present" if route in sitemap else "absent"),
        ))
        if absent_rows[key]["census_state"] == "MISSING" or "present" in absent_rows[key].values():
            problems.append("%s is not safely held: %s" % (key, absent_rows[key]))
    for key in REBRAND_KEYS:
        if absent_rows[key]["census_state"] != "NOT_ADMITTED:SAME_IDENTITY_REBRAND_SUCCESSOR":
            problems.append("%s is no longer a held rebrand: %s" % (key, absent_rows[key]["census_state"]))

    # ---- two states, never flattened (Phase 5) --------------------------------------------------------------
    by_state = Counter(GEO.state_for_postal(h.get("postal_code")) for h in census["hotels"])
    ks_as_mo = [h["identity_key"] for h in census["hotels"] if GEO.state_for_postal(h.get("postal_code")) == "KS"
                and (h.get("state") or "").upper() in ("MO", "MISSOURI")]
    mo_as_ks = [h["identity_key"] for h in census["hotels"] if GEO.state_for_postal(h.get("postal_code")) == "MO"
                and (h.get("state") or "").upper() in ("KS", "KANSAS")]
    seed_state = OrderedDict()
    for r in package["seed_rows"]:
        st = GEO.state_for_postal(r.get("postal_code") or r.get("zip") or "")
        stated = (r.get("state") or "").upper()
        if st and stated and stated != st:
            seed_state[r.get("identity_key") or r.get("name")] = (stated, st)
    fixed = OrderedDict()
    admitted_by_key = {h["identity_key"]: h for h in census["hotels"]}
    for key, (postal, state, disp) in FIXED_IDENTITIES.items():
        h = admitted_by_key.get(key) or {}
        fixed[key] = OrderedDict((("admitted", bool(h)), ("postal_code", h.get("postal_code")),
                                  ("state", h.get("state")), ("corridor", h.get("corridor")),
                                  ("disposition", disposition_of.get(key)),
                                  ("correct", bool(h) and h.get("postal_code") == postal
                                   and GEO.state_for_postal(h.get("postal_code")) == state
                                   and (h.get("state") or state).upper() == state and disposition_of.get(key) == disp)))
    from scripts.pettripfinder import kansas_city_mo_census_reconciliation_001 as CR
    env = CR.ADMITTED_PIN_ENVELOPE
    envelope_is_kansas_city = (38.5 < env["min_lat"] < env["max_lat"] < 39.6 and -95.2 < env["min_lng"] < env["max_lng"] < -94.0)
    cross_state = OrderedDict((
        ("MISSOURI_QUALIFYING_HOTELS", by_state.get("MO", 0)), ("KANSAS_QUALIFYING_HOTELS", by_state.get("KS", 0)),
        ("rows_in_neither_state", by_state.get(None, 0) + by_state.get("", 0)),
        ("KS_HOTELS_MISLABELED_MO", len(ks_as_mo)), ("MO_HOTELS_MISLABELED_KS", len(mo_as_ks)),
        ("ks_as_mo", ks_as_mo[:5]), ("mo_as_ks", mo_as_ks[:5]),
        ("SEED_ROWS_STATE_REWRITTEN", len(seed_state)), ("seed_state_conflicts", list(seed_state.items())[:5]),
        ("ADMITTED_PIN_ENVELOPE", env), ("KANSAS_CITY_ENVELOPE_AUTHORITATIVE", envelope_is_kansas_city),
        ("fixed_identities", fixed),
    ))
    if by_state.get("MO", 0) != EXPECTED_MISSOURI or by_state.get("KS", 0) != EXPECTED_KANSAS or ks_as_mo or mo_as_ks \
            or seed_state or not envelope_is_kansas_city or not all(v["correct"] for v in fixed.values()):
        problems.append("cross-state safety: %s" % OrderedDict((k, v) for k, v in cross_state.items()
                                                               if k not in ("ADMITTED_PIN_ENVELOPE", "fixed_identities")))

    # ---- market text safety (Phase 14): the REGISTERED documents carry no other market's text -------------
    registered_docs = [PKG / "identity_census" / ("%s.json" % MARKET_ID), PKG / "markets" / ("%s.json" % MARKET_ID),
                       PKG / ("hotel_policy_facts_%s.json" % MARKET_ID), PKG / "kansas_city_mo_proposed_authority_001.json",
                       PKG / "kansas_city_mo_final_partition_001.json",
                       _DASH / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET_ID)] \
        + sorted((PKG / "markets" / "authority" / MARKET_ID).glob("*")) + [_DASH / sealed["path"]]
    residue = OrderedDict()
    for p in registered_docs:
        hits = _residue(p.read_text(encoding="utf-8"))
        if hits:
            residue[p.relative_to(_DASH).as_posix()] = hits[:5]
    policy = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET_ID))
    contract_doc = _load(_DASH / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET_ID))
    label_ok = (policy.get("market") == MARKET_LABEL and MARKET_LABEL in contract_doc.get("description", "")
                and market_cfg.market_id == MARKET_ID)
    boundary = accounting.get("county_and_border_boundary") or {}
    boundary_ok = all(p in boundary for p in BOUNDARY_PLACES)
    text_safety = OrderedDict((
        ("MINNEAPOLIS_ST_PAUL_MARKET_TEXT_RESIDUE", sum(1 for f, h in residue.items() for x in h
                                                        if re.search(r"minneapolis|minnesota|twin cities|paul", x, re.I))),
        ("OREGON_PORTLAND_TEXT_RESIDUE", sum(1 for f, h in residue.items() for x in h
                                             if re.search(r"portland|oregon", x, re.I))),
        ("residue_hits", residue),
        ("documents_scanned", len(registered_docs)),
        ("KANSAS_CITY_MARKET_LABEL_CORRECT", label_ok), ("policy_package_market", policy.get("market")),
        ("BOUNDARY_AUDIT_PLACES", OrderedDict((p, boundary.get(p)) for p in BOUNDARY_PLACES)),
        ("boundary_audit_kansas_city", boundary_ok),
    ))
    if residue or not label_ok or not boundary_ok:
        problems.append("market text safety: residue %s, label %s, boundary %s" % (list(residue)[:3], label_ok, boundary_ok))

    # Rows the identity graph did not admit must never publish under their names (carried from Minneapolis).
    pf_by_name = {_fold(r.get("name")): r["identity_key"] for r in package["pet_friendly_records"]}
    admitted = {h["identity_key"]: h for h in census["hotels"]}
    outside = Counter()
    outside_published = []
    same_name_observations = []
    for h in census.get("non_admitted") or ():
        outside[h.get("classification")] += 1
        key = pf_by_name.get(_fold(h.get("canonical_name")))
        if key is None:
            continue
        a = admitted.get(key) or {}
        row = OrderedDict((("classification", h.get("classification")), ("canonical_name", h.get("canonical_name")),
                           ("street", h.get("street") or ""), ("postal_code", h.get("postal_code") or ""),
                           ("lanes", h.get("lanes")), ("published_identity_key", key),
                           ("published_street", a.get("street")), ("published_postal_code", a.get("postal_code")),
                           ("published_property_code", a.get("property_code"))))
        observation = h.get("classification") in ("IDENTITY_REVIEW_REQUIRED", "NAME_ONLY_UNRESOLVED")
        same_place = not row["postal_code"] or row["postal_code"] == (a.get("postal_code") or "")
        house = re.match(r"\s*(\d+)", row["street"])
        pub_house = re.match(r"\s*(\d+)", a.get("street") or "")
        same_building = bool(house and pub_house and house.group(1) == pub_house.group(1)
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
    authority = _load(PKG / "kansas_city_mo_proposed_authority_001.json")
    findings = SAFE.audit(policy, authority)
    safety = OrderedDict((k.upper(), len(v)) for k, v in findings.items())
    for k, v in safety.items():
        if v:
            problems.append("%s = %s" % (k, v))
    np_keys = {r.get("identity_key") or r.get("normalized_name") for r in package["verified_no_pets_records"]}
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
    drury = OrderedDict()
    for k in DRURY_KEYS:
        rec = next((h for h in policy["hotels"] if h.get("identity_key") == k), None)
        drury[k] = OrderedDict((("published_record", rec is not None),
                                ("pet_fee", (rec or {}).get("facts", {}).get("pet_fee"))))
    drury_ok = all(v["published_record"] and not v["pet_fee"] for v in drury.values())
    published_single = sum(1 for h in policy["hotels"] if h["facts"].get("pet_fee"))
    fee_safety = OrderedDict((
        ("SINGLE_BASIS_FEES_PUBLISHED", published_single),
        ("TIERED_FEES_WITHHELD", len(fees["tiered"])), ("UNSAFE_FEES_WITHHELD", len(fees["unsafe"])),
        ("withheld_entries", len(withheld)), ("records_matched_by_quote", matched),
        ("by_reason", OrderedDict(sorted(Counter(w for w, _ in withheld).items()))),
        ("WITHHELD_FEES_FLATTENED", len(flattened)), ("flattened", flattened[:5]),
        ("MISLEADING_SINGLE_FEES_PUBLISHED", safety["MISLEADING_SINGLE_FEE_PUBLISHED"]),
        ("DRURY_DAILY_FEES_WITHHELD", drury_ok), ("drury", drury),
    ))
    if flattened or published_single != 25 or len(fees["tiered"]) != 37 or len(fees["unsafe"]) != 17 or not drury_ok:
        problems.append("fee safety: %s" % OrderedDict((k, v) for k, v in fee_safety.items()
                                                       if k in ("SINGLE_BASIS_FEES_PUBLISHED", "TIERED_FEES_WITHHELD",
                                                                "UNSAFE_FEES_WITHHELD", "WITHHELD_FEES_FLATTENED",
                                                                "DRURY_DAILY_FEES_WITHHELD")))

    # ---- projected accounting, from candidate SETS ---------------------------------------------------------
    delta = package["intended_delta"]
    kc_index = sorted(delta["add_routes"])
    kc_served = sorted(r for r in sitemap if r.startswith(hub_route))
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
    cand_served = live_served + len(kc_served)
    profiles = len(package["pet_friendly_records"])
    projected = OrderedDict((
        ("KANSAS_CITY_PROJECTED_PROFILES", profiles),
        ("KANSAS_CITY_HOTEL_ROUTES", len(candidate.markets[MARKET_ID].hotel_routes)),
        ("KANSAS_CITY_CORRIDOR_ROUTES", len(candidate.markets[MARKET_ID].corridor_routes)),
        ("KANSAS_CITY_HUB_ROUTES", 1),
        ("KANSAS_CITY_RELEASE_INDEX_ROUTES", len(kc_index)),
        ("KANSAS_CITY_SERVED_ROUTES", len(kc_served)),
        ("kansas_city_served_not_in_index", sorted(set(kc_served) - set(kc_index))),
        ("CANDIDATE_MARKETS", len(candidate.participating)),
        ("CANDIDATE_PROFILES", candidate.total_profiles),
        ("CANDIDATE_RELEASE_INDEX_ROUTES", len(cand_routes)),
        ("CANDIDATE_SERVED_ROUTES", cand_served),
        ("parent", OrderedDict((("deploy_id", live_state.deploy_id), ("markets", len(live_idx.participating)),
                                ("profiles", live_idx.total_profiles),
                                ("release_index_routes", len(live_routes)), ("served_routes", live_served)))),
    ))
    if set(kc_index) - set(kc_served):
        problems.append("declared Kansas City routes missing from the built sitemap: %s"
                        % sorted(set(kc_index) - set(kc_served))[:5])
    if candidate.total_profiles != live_idx.total_profiles + profiles or profiles != EXPECTED_PROFILES:
        problems.append("profile delta is not exactly +%d" % EXPECTED_PROFILES)
    delta_safety = OrderedDict((
        ("UNEXPECTED_MARKET_DELTA", [m for m in new_markets if m != MARKET_ID] + lost_markets),
        ("UNEXPECTED_PROFILE_DELTA", [] if candidate.total_profiles == live_idx.total_profiles + profiles else
         ["%d != %d + %d" % (candidate.total_profiles, live_idx.total_profiles, profiles)]),
        ("UNEXPECTED_ROUTE_DELTA", sorted(cand_routes - live_routes - set(kc_index))
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
        problems.append("Kansas City is not the only new market: %s" % new_markets)

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
        ("kansas_city_exclusions_named_by_another_market", elsewhere),
        ("kansas_city_profiles_named_by_a_live_market", pf_collide),
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
    refusal = OrderedDict((("authorizations_naming_kansas_city", auths),
                           ("deployment_records_naming_kansas_city", records),
                           ("participation_state", status),
                           ("founder_authorized", status == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
                           ("DEPLOYMENT_REFUSAL", "EXPECTED / PASS" if not auths and not records
                            and status != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH else "FAIL")))
    if refusal["DEPLOYMENT_REFUSAL"] != "EXPECTED / PASS":
        problems.append("Kansas City is deployable: %s" % refusal)

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
        ("founder_ruling_dual_brand_held", sorted(groups["dual_brand"]) == sorted(DUAL_BRAND_KEYS)
         and all(absent_rows[k]["census_state"] == "ADMITTED" and "present" not in absent_rows[k].values()
                 for k in DUAL_BRAND_KEYS)),
        ("founder_ruling_rebrands_held", all(absent_rows[k]["census_state"] == "NOT_ADMITTED:SAME_IDENTITY_REBRAND_SUCCESSOR"
                                             and "present" not in absent_rows[k].values() for k in REBRAND_KEYS)),
        ("founder_ruling_esa_tiffany_springs_held", groups["esa_tiffany_springs"] == [ESA_TIFFANY_KEY]
         and "present" not in absent_rows[ESA_TIFFANY_KEY].values()
         and absent_rows[ESA_TIFFANY_KEY]["disposition"] not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS")),
        ("founder_ruling_crossland_held", groups["crossland_route_identity"] == [CROSSLAND_KEY]
         and "present" not in absent_rows[CROSSLAND_KEY].values()),
        ("cross_state_safety", not ks_as_mo and not mo_as_ks and not seed_state
         and by_state.get("MO", 0) == EXPECTED_MISSOURI and by_state.get("KS", 0) == EXPECTED_KANSAS
         and envelope_is_kansas_city and all(v["correct"] for v in fixed.values())),
        ("market_text_safety", not residue and label_ok and boundary_ok),
        ("drury_daily_fees_withheld", drury_ok),
        ("preopening_safety", not safety["PREOPENING_OR_CLOSED_PUBLISHED"] and not held["preopening"]["published"]
         and all("present" not in absent_rows[k].values() for k in PREOPENING_KEYS)),
        ("timeshare_safety", not safety["TIMESHARE_OR_VACATION_OWNERSHIP_PUBLISHED"]
         and all("present" not in absent_rows[k].values() for k in TIMESHARE_KEYS)),
        ("military_safety", not safety["MILITARY_RESTRICTED_PUBLISHED"]),
        ("reader_safety", not safety["PET_FRIENDLY_WITH_EXPLICIT_REFUSAL"] and not safety["QUESTION_ONLY_PET_FRIENDLY"]
         and not safety["SERVICE_ANIMAL_ONLY_PET_FRIENDLY"] and not safety["NO_PETS_QUOTE_WITHOUT_REFUSAL"]),
        ("fee_safety", not safety["MISLEADING_SINGLE_FEE_PUBLISHED"] and not flattened and published_single == 25
         and len(fees["tiered"]) == 37 and len(fees["unsafe"]) == 17),
        ("collision_safety", not (collisions["CROSS_MARKET_COLLISIONS"] or bare_exposed or dup)),
        ("first_party_binding", gate["passed"]),
        ("release_contracts", not bad_contracts),
        ("deployment_eligibility_refusal", refusal["DEPLOYMENT_REFUSAL"] == "EXPECTED / PASS"),
    ))
    doc = OrderedDict((
        ("schema", "ptf-registration-staging-checks/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("registered_package", OrderedDict((("package_id", sealed["package_id"]), ("package_digest", sealed["package_digest"]),
                                            ("content_identical_to", SOURCE_PACKAGE), ("content_fields", same_content),
                                            ("same_bundle_as_source", same_bundle)))),
        ("held_row_safety", held),
        ("held_rows_absent", absent_rows),
        ("cross_state_safety", cross_state),
        ("market_text_safety", text_safety),
        ("UNAPPROVED_KANSAS_CITY_PROFILES", len(unapproved_built)),
        ("APPROVED_KANSAS_CITY_PROFILES", len(built_routes & approved_routes)),
        ("non_admitted_census_rows", OrderedDict(sorted(outside.items()))),
        ("held_outside_census_published", outside_published),
        ("same_name_observations_of_published_buildings", same_name_observations),
        ("identity_resolutions_written", not no_identity_resolutions),
        ("reader_and_fee_safety", safety),
        ("fee_withholding_preserved", fee_safety),
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
    print(json.dumps(OrderedDict((k, doc[k]) for k in ("held_rows_absent", "cross_state_safety", "market_text_safety",
                                                       "fee_withholding_preserved", "projected_accounting",
                                                       "delta_safety", "gates", "ALL_STAGING_GATES", "problems")),
                     indent=1)[:14000])
    if args.write:
        OUT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("written", OUT.relative_to(_DASH).as_posix())
    return 0 if doc["ALL_STAGING_GATES"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""PTF-SAN-ANTONIO-TX-REGISTRATION-AND-STAGING-003 -- the bounded staging gates for San Antonio's registration.

    python -m scripts.pettripfinder.san_antonio_tx_registration_checks_003 --site C:/t/sa3a/oa/site [--write]

READ ONLY. Every count is derived from the registered sealed package, its receipt, the lane report the seal wrote,
the site the seal's own FAST build produced, the committed San Antonio reports and the committed shared registries.
Nothing here publishes, authorizes or deploys, and no held identity row is resolved.
"""
from __future__ import annotations

import argparse
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
from scripts.pettripfinder import san_antonio_tx_publication_safety_audit_001 as SAFE  # noqa: E402

WORK_ORDER = "PTF-SAN-ANTONIO-TX-REGISTRATION-AND-STAGING-003"
MARKET_ID = "san-antonio-tx"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
STAGING = PKG / "markets" / "staging" / MARKET_ID
LANE_REPORT = REPORTS / "san_antonio_tx_registration_release_lane.json"
OUT = REPORTS / "san_antonio_tx_registration_checks_003.json"
SOURCE_PACKAGE = "pkg-san-antonio-tx-b6018714bcc2bd44"
SOURCE_RECEIPT = "pkg-san-antonio-tx-b6018714bcc2bd44-54a176a91524761e.json"
#: the founder rows the source-ready order held, by class (the writer refuses on any mismatch)
EXPECTED_DUAL_BRAND = 8
EXPECTED_SHARED_READER_REFUSAL = 1
EXPECTED_PREOPENING = 4
EXPECTED_HILTON_BLOCKED = 10
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
    act = _load(REPORTS / "san_antonio_tx_actionability_001.json")
    clean = _load(REPORTS / "san_antonio_tx_clean_authority_001.json")
    hilton = _load(REPORTS / "san_antonio_tx_hilton_paced_retry_002.json")
    census = _load(PKG / "identity_census" / ("%s.json" % MARKET_ID))
    site = Path(args.site)

    # ---- package identity: the registered package carries the source-ready package's content -------------
    source = _load(STAGING / "shadow_packages" / MARKET_ID / ("%s.json" % SOURCE_PACKAGE))
    same_content = OrderedDict((k, package[k] == source[k]) for k in (
        "census", "pet_friendly_records", "verified_no_pets_records", "seed_rows", "partition",
        "official_routes", "evidence_references", "unresolved_rows", "founder_holds"))
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
    # Routes are compared as the SITE forms them (release_index.hotel_route over the display name -- the site's
    # slug drops "and" / "&", so a census slug is not a route), never by census slug.
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
        problems.append("built San Antonio profiles not in the approved cohort: %s" % unapproved_built[:5])
    if pf_keys != approved:
        problems.append("the package's pet-friendly set is not the approved cohort")
    name_of = {h["identity_key"]: h["canonical_name"] for h in census["hotels"]}
    name_of.update({r["identity_key"]: r["canonical_name"] for r in clean["rows"]})

    def published(keys):
        out = []
        for k in keys:
            route = RI.hotel_route(market_cfg, name_of.get(k, k))
            if k in pf_keys or route in built_routes or route in sitemap or route in approved_routes:
                out.append(k)
        return out

    rows = act["rows"]
    by_fold = {}
    for r in rows:
        by_fold.setdefault(_fold(r["canonical_name"]), []).append(r["identity_key"])
    hilton_keys = sorted({k for h in hilton["rows"] for k in by_fold.get(_fold(h["identity"]), ())})
    if len(hilton_keys) != EXPECTED_HILTON_BLOCKED or len(hilton["rows"]) != EXPECTED_HILTON_BLOCKED:
        problems.append("Hilton retry rows did not map one-to-one onto held rows: %d of %d"
                        % (len(hilton_keys), len(hilton["rows"])))
    groups = OrderedDict((
        ("dual_brand", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"
                        and r["disposition"] == "IDENTITY_MISMATCH_HOLD"]),
        ("shared_reader_refusal_founder", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"
                                           and r["disposition"] != "IDENTITY_MISMATCH_HOLD"]),
        ("preopening", [r["identity_key"] for r in rows if r["actionability"] == "HELD_UNTIL_OPENING"]),
        ("hilton_access_blocked", hilton_keys),
        ("router_exhausted", [r["identity_key"] for r in rows if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]),
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
    # Rows the identity graph did not admit must never publish under their names. A DISTINCT entity (outside the
    # market, non-lodging -- timeshare, rentals, apartments, RV parks, military lodging -- or a same-campus building)
    # that shares a published name is a leak outright. An identity-review or name-only row that shares a published
    # name is an OBSERVATION: it is a leak only when it places itself at a different building (a postal code other
    # than the admitted building's); with no address, or inside the admitted building's postal code, it is a
    # second sighting of the published building and is listed, never resolved here.
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
        if observation and same_place:
            same_name_observations.append(row)
        else:
            outside_published.append(row)
    if outside_published:
        problems.append("rows held outside the census publish: %s"
                        % [(r["classification"], r["canonical_name"]) for r in outside_published[:5]])

    # ---- reader and fee safety, over the registered root documents (byte-identical to the sealed copies) ---
    policy = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET_ID))
    authority = _load(PKG / "san_antonio_tx_proposed_authority_001.json")
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

    # ---- projected accounting, from candidate SETS ---------------------------------------------------------
    delta = package["intended_delta"]
    sa_index = sorted(delta["add_routes"])
    sa_served = sorted(r for r in sitemap if r.startswith(hub_route))
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
    # the served surface: the live sitemap plus San Antonio's own served routes (a market's comparison page is
    # served but not owned by the index); every live served route is preserved because no live market is re-rendered
    live_manifest = _load(_DASH / "deploy" / "netlify" / "global_deployment_manifest.json")
    live_served = int(live_manifest["sitemap_route_count"])
    cand_served = live_served + len(sa_served)
    profiles = len(package["pet_friendly_records"])
    accounting = OrderedDict((
        ("SAN_ANTONIO_PROJECTED_PROFILES", profiles),
        ("SAN_ANTONIO_HOTEL_ROUTES", len(candidate.markets[MARKET_ID].hotel_routes)),
        ("SAN_ANTONIO_CORRIDOR_ROUTES", len(candidate.markets[MARKET_ID].corridor_routes)),
        ("SAN_ANTONIO_HUB_ROUTES", 1),
        ("SAN_ANTONIO_RELEASE_INDEX_ROUTES", len(sa_index)),
        ("SAN_ANTONIO_SERVED_ROUTES", len(sa_served)),
        ("san_antonio_served_not_in_index", sorted(set(sa_served) - set(sa_index))),
        ("CANDIDATE_MARKETS", len(candidate.participating)),
        ("CANDIDATE_PROFILES", candidate.total_profiles),
        ("CANDIDATE_RELEASE_INDEX_ROUTES", len(cand_routes)),
        ("CANDIDATE_SERVED_ROUTES", cand_served),
        ("parent", OrderedDict((("deploy_id", live_state.deploy_id), ("markets", len(live_idx.participating)),
                                ("profiles", live_idx.total_profiles),
                                ("release_index_routes", len(live_routes)), ("served_routes", live_served)))),
    ))
    if set(sa_index) - set(sa_served):
        problems.append("declared San Antonio routes missing from the built sitemap: %s"
                        % sorted(set(sa_index) - set(sa_served))[:5])
    if candidate.total_profiles != live_idx.total_profiles + profiles or profiles != 144:
        problems.append("profile delta is not exactly +144")
    delta_safety = OrderedDict((
        ("UNEXPECTED_MARKET_DELTA", [m for m in new_markets if m != MARKET_ID] + lost_markets),
        ("UNEXPECTED_PROFILE_DELTA", [] if candidate.total_profiles == live_idx.total_profiles + profiles else
         ["%d != %d + %d" % (candidate.total_profiles, live_idx.total_profiles, profiles)]),
        ("UNEXPECTED_ROUTE_DELTA", sorted(cand_routes - live_routes - set(sa_index))
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
        problems.append("San Antonio is not the only new market: %s" % new_markets)

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
    # A bare-chain NAME is a latent hazard: the shared registry matches an exclusion by normalized name in EVERY
    # market. It is a collision only when another building somewhere in the factory carries that name -- measured
    # here over every market's census (admitted and non-admitted), every other market's registry row and every live
    # profile. A row of another market at THIS building's own street identity is the same building, not a collision.
    import glob
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
    registry_bare = Counter(r.get("market_id") for r in registry
                            if r.get("market_id") != MARKET_ID and _bare_chain(r.get("canonical_name")))
    g_findings = [f for f in diff["findings"] if f["code"] in (RI.CROSS_MARKET_IDENTITY_COLLISION,
                                                              RI.OWNERSHIP_MOVEMENT, RI.DUPLICATE_ROUTE)]
    collisions = OrderedDict((
        ("CROSS_MARKET_COLLISIONS", len(elsewhere) + len(pf_collide) + len(g_findings)),
        ("san_antonio_exclusions_named_by_another_market", elsewhere),
        ("san_antonio_profiles_named_by_a_live_market", pf_collide),
        ("identity_or_ownership_findings", g_findings),
        ("BARE_CHAIN_NAMES", len(bare)), ("bare_chain_names", bare),
        ("bare_chain_exposure", bare_exposure),
        ("BARE_CHAIN_COLLISIONS", len(bare_exposed)), ("bare_chain_collisions", bare_exposed),
        ("bare_chain_names_already_in_registry_by_market", OrderedDict(sorted(registry_bare.items()))),
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
    # the committed authorization and record documents, read as data (a market-local module imports no deployer)
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
    refusal = OrderedDict((("authorizations_naming_san_antonio", auths),
                           ("deployment_records_naming_san_antonio", records),
                           ("participation_state", status),
                           ("founder_authorized", status == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
                           ("DEPLOYMENT_REFUSAL", "EXPECTED / PASS" if not auths and not records
                            and status != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH else "FAIL")))
    if refusal["DEPLOYMENT_REFUSAL"] != "EXPECTED / PASS":
        problems.append("San Antonio is deployable: %s" % refusal)

    contracts = RC.verify_all()
    bad_contracts = {m: p for m, p in contracts.items() if p}
    if bad_contracts:
        problems.append("release contracts disagree: %s" % list(bad_contracts)[:5])
    gate = FPB.evaluate_package(package)

    gates = OrderedDict((
        ("package_identity", all(same_content.values()) and same_bundle),
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
         and held["preopening"]["rows"] == EXPECTED_PREOPENING
         and held["hilton_access_blocked"]["rows"] == EXPECTED_HILTON_BLOCKED),
        ("held_cohort_safety", not any(v["published"] for v in held.values()) and not unapproved_built
         and not outside_published and no_identity_resolutions),
        ("preopening_safety", not safety["PREOPENING_OR_CLOSED_PUBLISHED"] and not held["preopening"]["published"]),
        ("timeshare_safety", not safety["TIMESHARE_OR_VACATION_OWNERSHIP_PUBLISHED"]),
        ("military_safety", not safety["MILITARY_RESTRICTED_PUBLISHED"]),
        ("reader_safety", not safety["PET_FRIENDLY_WITH_EXPLICIT_REFUSAL"] and not safety["QUESTION_ONLY_PET_FRIENDLY"]
         and not safety["SERVICE_ANIMAL_ONLY_PET_FRIENDLY"] and not safety["NO_PETS_QUOTE_WITHOUT_REFUSAL"]),
        ("fee_safety", not safety["MISLEADING_SINGLE_FEE_PUBLISHED"]),
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
        ("UNAPPROVED_SAN_ANTONIO_PROFILES", len(unapproved_built)),
        ("APPROVED_SAN_ANTONIO_PROFILES", len(built_routes & approved_routes)),
        ("non_admitted_census_rows", OrderedDict(sorted(outside.items()))),
        ("held_outside_census_published", outside_published),
        ("same_name_observations_of_published_buildings", same_name_observations),
        ("identity_resolutions_written", not no_identity_resolutions),
        ("reader_and_fee_safety", safety),
        ("projected_accounting", accounting), ("delta_safety", delta_safety),
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
    print(json.dumps(OrderedDict((k, doc[k]) for k in ("held_row_safety", "projected_accounting", "delta_safety",
                                                       "gates", "ALL_STAGING_GATES", "problems")), indent=1)[:9000])
    if args.write:
        OUT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("written", OUT.relative_to(_DASH).as_posix())
    return 0 if doc["ALL_STAGING_GATES"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

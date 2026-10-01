"""PTF-AUSTIN-TX-REGISTRATION-AND-STAGING-003 -- the bounded staging gates for Austin's registration.

    python -m scripts.pettripfinder.austin_tx_registration_checks_003 --site C:/t/atx3a/oa/site [--write]

READ ONLY. Every count is derived from the registered sealed package, its receipt, the lane report the seal wrote,
the site the seal's own FAST build produced, the committed Austin reports and the committed shared registries.
Nothing here publishes, authorizes or deploys.
"""
from __future__ import annotations

import argparse
import json
import os
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
from scripts.pettripfinder import austin_tx_reader_refresh_002 as REFRESH  # noqa: E402

WORK_ORDER = "PTF-AUSTIN-TX-REGISTRATION-AND-STAGING-003"
MARKET_ID = "austin-tx"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
LANE_REPORT = REPORTS / "austin_tx_registration_release_lane.json"
OUT = REPORTS / "austin_tx_registration_checks_003.json"
STALE_PACKAGE = "pkg-austin-tx-3030caf7703a9c57"
SOURCE_PACKAGE = "pkg-austin-tx-024e6fb46a9e6934"
SETTLED_NO_PETS = ("kalahari resorts and conventions round rock tx", "at and t hotel and conference center",
                   "heywood hotel", "sage hill inn and spa")
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
    act = _load(REPORTS / "austin_tx_actionability_001.json")
    clean = _load(REPORTS / "austin_tx_clean_authority_001.json")
    census = _load(PKG / "identity_census" / ("%s.json" % MARKET_ID))
    site = Path(args.site)

    # ---- package identity: the registered package carries the refreshed package's content -----------------
    source = _load(PKG / "markets" / "staging" / MARKET_ID / "shadow_packages" / MARKET_ID / ("%s.json" % SOURCE_PACKAGE))
    same_content = OrderedDict((k, package[k] == source[k]) for k in (
        "census", "pet_friendly_records", "verified_no_pets_records", "seed_rows", "partition",
        "official_routes", "evidence_references", "unresolved_rows", "founder_holds"))
    if not all(same_content.values()):
        problems.append("the registered package's content differs from %s: %s"
                        % (SOURCE_PACKAGE, [k for k, v in same_content.items() if not v]))
    j = receipt["RESULTS"]["J"]["detail"]
    if j.get("bundle_sha256") != _load(PKG / "markets" / "staging" / MARKET_ID / "shadow_receipts" / MARKET_ID /
                                       "pkg-austin-tx-024e6fb46a9e6934-74e62beb329c179c.json")["RESULTS"]["J"]["detail"]["bundle_sha256"]:
        problems.append("the registered package builds a different bundle than the refreshed shadow package")

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
        problems.append("built Austin profiles not in the approved cohort: %s" % unapproved_built[:5])
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
    groups = OrderedDict((
        ("new_spend", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_NEW_SPEND"]),
        ("dual_brand", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"
                        and r["disposition"] == "IDENTITY_MISMATCH_HOLD"]),
        ("operator_domain", [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"
                             and "two first-party routes" in (r.get("why") or "")]),
        ("mountain_star", ["mountain star lodge and hotel"]),
        ("strickland_arms", ["strickland arms bed and breakfast"]),
        ("router_exhausted_and_other", [r["identity_key"] for r in rows
                                        if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]),
        ("all_unresolved", [r["identity_key"] for r in rows]),
    ))
    held = OrderedDict()
    for name, keys in groups.items():
        leaked = published(keys)
        held[name] = OrderedDict((("rows", len(keys)), ("published", len(leaked)), ("leaked", leaked[:5])))
        if leaked:
            problems.append("%s rows published: %s" % (name, leaked[:5]))
    names_out = {_norm(h["canonical_name"]) for h in census.get("non_admitted") or ()
                 if h.get("classification") == "SAME_CAMPUS_DISTINCT_ENTITY"
                 or "TIMESHARE" in str(h.get("classification_reason") or "").upper()
                 or "sentral" in _norm(h.get("canonical_name"))}
    pf_names = {_norm(r.get("name")) for r in package["pet_friendly_records"]}
    outside_published = sorted(names_out & pf_names)
    if outside_published:
        problems.append("rows held outside the census publish: %s" % outside_published)
    safety = REFRESH.safety(package, census)
    for k in ("PET_FRIENDLY_WITH_EXPLICIT_REFUSAL", "QUESTION_ONLY_PET_FRIENDLY", "PREOPENING_PROFILES_PUBLISHED",
              "VACATION_OWNERSHIP_TIMESHARE_PROFILES_PUBLISHED", "MISLEADING_SINGLE_FEES"):
        if safety[k]:
            problems.append("%s = %s" % (k, safety[k]))
    np_keys = {r.get("identity_key") or r.get("normalized_name") for r in package["verified_no_pets_records"]}
    settled = OrderedDict((k, OrderedDict((("pet_friendly", k in pf_keys), ("verified_no_pets", k in np_keys))))
                          for k in SETTLED_NO_PETS)
    if any(v["pet_friendly"] or not v["verified_no_pets"] for v in settled.values()):
        problems.append("a settled refusal is not verified no-pets: %s" % settled)

    # ---- projected accounting, from candidate SETS ---------------------------------------------------------
    delta = package["intended_delta"]
    austin_index = sorted(delta["add_routes"])
    hub = "/pet-friendly-hotels/%s/" % MARKET_ID
    austin_served = sorted(r for r in sitemap if r.startswith(hub))
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
    # the served surface: the live sitemap plus Austin's own served routes (a market's comparison page is served
    # but not owned by the index); every live served route is preserved because no live market is re-rendered
    live_manifest = _load(_DASH / "deploy" / "netlify" / "global_deployment_manifest.json")
    live_served = int(live_manifest["sitemap_route_count"])
    cand_served = live_served + len(austin_served)
    profiles = len(package["pet_friendly_records"])
    accounting = OrderedDict((
        ("AUSTIN_PROJECTED_PROFILES", profiles),
        ("AUSTIN_HOTEL_ROUTES", len(candidate.markets[MARKET_ID].hotel_routes)),
        ("AUSTIN_CORRIDOR_ROUTES", len(candidate.markets[MARKET_ID].corridor_routes)),
        ("AUSTIN_HUB_ROUTES", 1),
        ("AUSTIN_RELEASE_INDEX_ROUTES", len(austin_index)),
        ("AUSTIN_SERVED_ROUTES", len(austin_served)),
        ("austin_served_not_in_index", sorted(set(austin_served) - set(austin_index))),
        ("CANDIDATE_MARKETS", len(candidate.participating)),
        ("CANDIDATE_PROFILES", candidate.total_profiles),
        ("CANDIDATE_RELEASE_INDEX_ROUTES", len(cand_routes)),
        ("CANDIDATE_SERVED_ROUTES", cand_served),
        ("parent", OrderedDict((("markets", len(live_idx.participating)), ("profiles", live_idx.total_profiles),
                                ("release_index_routes", len(live_routes)), ("served_routes", live_served)))),
    ))
    if set(austin_index) - set(austin_served):
        problems.append("declared Austin routes missing from the built sitemap: %s"
                        % sorted(set(austin_index) - set(austin_served))[:5])
    if candidate.total_profiles != live_idx.total_profiles + profiles or profiles != 190:
        problems.append("profile delta is not exactly +190")
    delta_safety = OrderedDict((
        ("UNEXPECTED_MARKET_DELTA", [m for m in new_markets if m != MARKET_ID] + lost_markets),
        ("UNEXPECTED_PROFILE_DELTA", [] if candidate.total_profiles == live_idx.total_profiles + profiles else
         ["%d != %d + %d" % (candidate.total_profiles, live_idx.total_profiles, profiles)]),
        ("UNEXPECTED_ROUTE_DELTA", sorted(cand_routes - live_routes - set(austin_index))
         + sorted(live_routes - cand_routes)),
        ("PRIOR_MARKETS_LOST", len(lost_markets)),
        ("PRIOR_PROFILES_LOST", sum(len(live_idx.markets[m].profiles) - len(candidate.markets[m].profiles)
                                    for m in live_idx.participating)),
        ("PRIOR_RELEASE_INDEX_ROUTES_LOST", len(live_routes - cand_routes)),
        ("PRIOR_SERVED_ROUTES_LOST", 0),
        ("ONLY_NEW_MARKET", new_markets),
        ("release_diff_passed", diff["passed"]), ("finding_counts", diff["finding_counts"]),
    ))
    for k in ("UNEXPECTED_MARKET_DELTA", "UNEXPECTED_PROFILE_DELTA", "UNEXPECTED_ROUTE_DELTA"):
        if delta_safety[k]:
            problems.append("%s = %s" % (k, delta_safety[k][:5]))
    if new_markets != [MARKET_ID]:
        problems.append("Austin is not the only new market: %s" % new_markets)

    # ---- cross-market safety -------------------------------------------------------------------------------
    registry = _load(PKG / "hotel_exclusions.json")["exclusions"]
    by_market = {}
    for r in registry:
        by_market.setdefault(r.get("market_id"), set()).add(_norm(r.get("canonical_name")))
    mine = by_market.get(MARKET_ID, set())
    elsewhere = sorted(n for n in mine if any(n in s for m, s in by_market.items() if m != MARKET_ID))
    dup = sorted(n for n, c in Counter((r.get("market_id"), _norm(r.get("canonical_name"))) for r in registry).items()
                 if c > 1)
    bare = sorted(n for n in mine | pf_names if _bare_chain(n))
    live_names = {_norm(e.name) for m, i in live_idx.markets.items() if i.participating for e in i.profiles.values()}
    pf_collide = sorted(pf_names & live_names)
    g_findings = [f for f in diff["findings"] if f["code"] in (RI.CROSS_MARKET_IDENTITY_COLLISION,
                                                              RI.OWNERSHIP_MOVEMENT, RI.DUPLICATE_ROUTE)]
    collisions = OrderedDict((
        ("CROSS_MARKET_COLLISIONS", len(elsewhere) + len(pf_collide) + len(g_findings)),
        ("austin_exclusions_named_by_another_market", elsewhere), ("austin_profiles_named_by_a_live_market", pf_collide),
        ("identity_or_ownership_findings", g_findings),
        ("BARE_CHAIN_COLLISIONS", len(bare)), ("bare_chain_names", bare),
        ("DUPLICATE_EXCLUDED_IDENTITIES", len(dup)), ("duplicates", dup[:5]),
        ("LIVE_PROPERTIES_MOVED_OR_DISPLACED", len(g_findings)),
    ))
    if collisions["CROSS_MARKET_COLLISIONS"] or bare or dup:
        problems.append("collision canaries: %s" % OrderedDict((k, v) for k, v in collisions.items() if v))

    # ---- FAST receipt -------------------------------------------------------------------------------------
    eligible = [p.name for p in FL.eligible_receipts(MARKET_ID, package["package_digest"])]
    stale_digest = "sha256:3030caf7703a9c574c14177ebcb072bbd691e94a518f6b68a045506482026331"
    stale_canonical = [p.name for p in FL.eligible_receipts(MARKET_ID, stale_digest)]
    receipt_ok = (Path(receipt_rel).name in eligible and not FL.receipt_output_defects(receipt)
                  and (j.get("file_count") or 0) > 0 and (j.get("html_count") or 0) > 0
                  and j.get("bundle_sha256") != FL.EMPTY_BUNDLE_SHA256
                  and receipt["RESULTS"]["K"]["detail"].get("result") == "BYTE_IDENTICAL")
    if not receipt_ok or stale_canonical:
        problems.append("receipt eligibility: selected %s, stale selectable %s" % (eligible, stale_canonical))

    # ---- deployment refusal (EXPECTED) ---------------------------------------------------------------------
    # the committed authorization and record documents, read as data (a market-local module imports no deployer)
    netlify = _DASH / "deploy" / "netlify"

    def _naming(directory, id_field):
        out = []
        for path in sorted((netlify / directory).glob("*.json")):
            doc = _load(path)
            names = [m.get("market_id") if isinstance(m, dict) else m for m in (doc.get("participating_markets") or ())]
            if MARKET_ID in names:
                out.append(doc.get(id_field) or path.stem)
        return out

    auths = _naming("deployment_authorizations", "authorization_id")
    records = _naming("deployment_records", "deployment_record_id")
    status = LP.launch_status(MARKET_ID)
    refusal = OrderedDict((("authorizations_naming_austin", auths), ("deployment_records_naming_austin", records),
                           ("participation_state", status),
                           ("founder_authorized", status == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
                           ("DEPLOYMENT_REFUSAL", "EXPECTED / PASS" if not auths and not records
                            and status != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH else "FAIL")))
    if refusal["DEPLOYMENT_REFUSAL"] != "EXPECTED / PASS":
        problems.append("Austin is deployable: %s" % refusal)

    contracts = RC.verify_all()
    bad_contracts = {m: p for m, p in contracts.items() if p}
    if bad_contracts:
        problems.append("release contracts disagree: %s" % list(bad_contracts)[:5])
    gate = FPB.evaluate_package(package)

    gates = OrderedDict((
        ("package_identity", all(same_content.values())),
        ("registration_lane_eligible", lane["fast_lane_receipt"]["eligible"] == "YES"
         and lane["PACKAGE_REPRODUCIBLE"] == "YES" and lane["CANDIDATE_REPRODUCIBLE"] == "YES"),
        ("fast_receipt_eligibility", receipt_ok and not stale_canonical),
        ("fast_rules_A_O", lane["fast_lane_receipt"]["rules_passed"] == 15 and not lane["fast_lane_receipt"]["unknown_rules"]),
        ("parent_lookup", not live_problems and package["parent_live_state"]["live_deploy_id"] == live_state.deploy_id),
        ("parent_routes_preserved", live_routes <= cand_routes),
        ("market_preservation", not lost_markets and len(carried) == len(live_idx.participating)),
        ("profile_preservation", not delta_safety["UNEXPECTED_PROFILE_DELTA"]),
        ("route_preservation", not delta_safety["UNEXPECTED_ROUTE_DELTA"]),
        ("candidate_delta", diff["passed"]),
        ("participation_projection", status == "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"),
        ("founder_decision_reconciliation", held["dual_brand"]["rows"] == 18 and held["operator_domain"]["rows"] == 5),
        ("held_cohort_safety", not any(v["published"] for v in held.values()) and not unapproved_built
         and not outside_published),
        ("preopening_safety", not safety["PREOPENING_PROFILES_PUBLISHED"]),
        ("timeshare_safety", not safety["VACATION_OWNERSHIP_TIMESHARE_PROFILES_PUBLISHED"]),
        ("reader_safety", not safety["PET_FRIENDLY_WITH_EXPLICIT_REFUSAL"] and not safety["QUESTION_ONLY_PET_FRIENDLY"]),
        ("fee_safety", not safety["MISLEADING_SINGLE_FEES"]),
        ("collision_safety", not (collisions["CROSS_MARKET_COLLISIONS"] or bare or dup)),
        ("first_party_binding", gate["passed"]),
        ("release_contracts", not bad_contracts),
        ("deployment_eligibility_refusal", refusal["DEPLOYMENT_REFUSAL"] == "EXPECTED / PASS"),
    ))
    doc = OrderedDict((
        ("schema", "ptf-registration-staging-checks/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("registered_package", OrderedDict((("package_id", sealed["package_id"]), ("package_digest", sealed["package_digest"]),
                                            ("content_identical_to", SOURCE_PACKAGE), ("content_fields", same_content)))),
        ("stale_package", OrderedDict((("package_id", STALE_PACKAGE), ("canonical_receipts_selecting_it", stale_canonical),
                                       ("registered", False), ("authorized", False)))),
        ("held_row_safety", held),
        ("UNAPPROVED_AUSTIN_PROFILES", len(unapproved_built)), ("APPROVED_AUSTIN_PROFILES", len(built_routes & approved_routes)),
        ("held_outside_census_published", outside_published),
        ("reader_safety", safety), ("settled_refusals", settled),
        ("projected_accounting", accounting), ("delta_safety", delta_safety),
        ("cross_market_safety", collisions),
        ("fast_receipt", OrderedDict((("selected", eligible), ("file_count", j.get("file_count")),
                                      ("html_count", j.get("html_count")), ("bundle_sha256", j.get("bundle_sha256")),
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
    print(json.dumps(OrderedDict((k, doc[k]) for k in ("projected_accounting", "delta_safety", "gates",
                                                       "ALL_STAGING_GATES", "problems")), indent=1)[:7000])
    if args.write:
        OUT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("written", OUT.relative_to(_DASH).as_posix())
    return 0 if doc["ALL_STAGING_GATES"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

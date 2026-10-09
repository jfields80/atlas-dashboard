"""PTF-FORT-MYERS-FL-PRODUCTION-DEPLOYMENT-004 -- deploy the exact, already-built, founder-authorized Fort Myers /
Cape Coral / Sanibel candidate, then verify the HOST, record the deployment, extend the supersessions chain and move
the pins. One subcommand per step, each refusing unless the step before it holds (derived from Salt Lake City's 004
deployment module, itself New Orleans', Kansas City's, Minneapolis's, Portland's, Seattle's and San Antonio's, every
structural check unchanged):

    predeploy      --candidate C:/t/fm4a --site-info <getSite json> [--write]
    write-manifest --candidate C:/t/fm4a [--write]
    verify-live    --candidate C:/t/fm4a --parent-sitemap ... --market-sweep ... --prior-sweep ...
                   --host-state ... --deployment-id ... [--write]
    record         --deployment-id ... [--write]
    supersessions  --deployment-id ... [--write]
    pin            --deployment-id ... [--write]

The ``netlify deploy`` call itself is run ONCE by hand between ``write-manifest`` and ``verify-live``; this module
never deploys.

THE AUTHORIZATION IS RESOLVED, NEVER TYPED. The founder-facing recap abbreviated the authorization id and the
candidate digests, so the authorization is the ONE record naming fort-myers-fl that the authorizing order
PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 wrote; its package is the one the readiness packet binds, its FAST
receipt is the one the readiness packet binds (by path and digest), and its digests are the committed candidate
manifest's. The record keeps the authorization's own ``work_order`` (the AUTHORIZING order) and names this order as
``deployer.work_order``.

FORT MYERS' OWN LIVE CHECKS. On top of every unpublished census row (the 51 unresolved and the 34 verified-no-pets):
the founder's named held rows -- Comfort Suites and MainStay Suites at 9455 Old Luckett, the Quality Inn at 4760 S
Cleveland AND the retired Travelodge names that building once traded under (none of whose evidence migrates), the
Latitude 26 rows including the Inn & Suites at 4701 Bonita Beach Rd, Pink Shell and Edison Beach House -- are listed
explicitly and must 404 at the census slug and the site route; the published Travelodge at 13353 N Cleveland is a
different building and must be the only Travelodge live. The timeshare, private condo / residence / rental and other
non-hotel identities the census never admitted must 404 and hold no served route. EVERY live Fort Myers profile is
fetched whole and must be byte-identical to the authorized artifact, state FL, the municipality and postal code the
census carries for it, sit in Lee County, name no Naples / Collier / Charlotte County place, stand at no founder-held
premises, and carry exactly the authorized fee (a withheld fee renders none); every published row is CURRENTLY open,
and every Fort Myers Beach / Sanibel / Captiva profile is checked by name. EVERY Fort Myers /go/ page is fetched
whole and must be byte-identical, and its redirect must be tel:, internal, or absolute http(s) with a host.

THE HOST IS THE AUTHORITY, NOT THE DEPLOY COMMAND. Every number is fetched or read; none is typed. If any live check
fails, ROLLBACK_REQUIRED becomes YES -- this module never decides to roll back, it decides whether the evidence
permits recording a success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402
from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import release_index as RI              # noqa: E402

WORK_ORDER = "PTF-FORT-MYERS-FL-PRODUCTION-DEPLOYMENT-004"
AUTHORIZING_ORDER = "PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "fort-myers-fl"
AUTHORIZED_PACKAGE_ID = "pkg-fort-myers-fl-919f61116936bf5e"
REFUSED_PACKAGE_PREFIXES = ("pkg-fort-myers-fl-68b3cfa8",)
SOURCE_READY_DIGEST = "sha256:68b3cfa8bc4758c5b0d935d385fee3404ab01ed569f65ca2dc52d0c1733a2415"
FOUNDER_DECISION_COMMIT = "ab616e2e"
FOUNDER_BINDING_COMMIT = "6a425592"
HOST = "https://pettripfinder.com"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PREDEPLOY = os.path.join(REPORTS, "fort_myers_fl_predeploy_004.json")
VERIFICATION = os.path.join(REPORTS, "fort_myers_fl_live_verification_004.json")
ACCOUNTING = os.path.join(REPORTS, "fort_myers_fl_launch_authorization_003.json")
READINESS = os.path.join(REPORTS, "fort_myers_fl_registration_authorization_readiness.json")
OPERATING_STATUS = os.path.join(REPORTS, "fort_myers_fl_operating_status_accounting_001.json")
CANDIDATE_MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest_candidate_fort_myers_003.json")
SUPERSESSIONS = os.path.join(_DASH, "tests", "pettripfinder", "pins", "supersessions.json")
DEPLOYMENT_STATE = os.path.join(_DASH, "tests", "pettripfinder", "pins", "deployment_state.json")
MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json")
SPOT = ("salt-lake-city-ut", "new-orleans-la", "kansas-city-mo", "minneapolis-mn", "portland-or", "seattle-wa",
        "san-antonio-tx", "austin-tx", "phoenix-az", "denver-co", "san-diego-ca", "jacksonville-fl",
        "west-palm-beach-fl", "fort-lauderdale-fl", "augusta-ga", "miami-fl", "tampa-fl", "orlando-fl")
#: the parent this order deploys over, and the candidate it deploys (markets, profiles, release-index, served)
PARENT_ACCOUNTING = (45, 4373, 4807, 4885)
PARENT_DEPLOY_ID = "6ac6f3d213d002249f9c3e67"
CANDIDATE_ACCOUNTING = (46, 4430, 4869, 4948)
CANDIDATE_FILES = 26724
CANDIDATE_FILES_ADDED = 346
#: Fort Myers' own (profiles, release-index routes, served routes)
MARKET_ACCOUNTING = (57, 62, 63)
GO_PAGES = 283
#: held cohort sizes the registration and the founder decision fixed
HELD_GROUP_ROWS = OrderedDict((
    ("founder_named_old_luckett_comfort_suites_and_mainstay", 2),
    ("founder_named_quality_inn_4760_s_cleveland", 1),
    ("founder_named_latitude_26", 5),
    ("founder_named_pink_shell_and_edison", 2),
    ("router_exhausted_rows", 49),
    ("all_unresolved_rows", 51),
    ("verified_no_pets_rows", 34),
))
OUTSIDE_ROWS = {"timeshare": 5, "private_condo_residence_or_rental": 121, "other_non_hotel": 44,
                "military_restricted": 0}
FEES = (5, 22, 5)            # published, tiered withheld, unsafe single / multi-amount withheld
WITHHELD_FEE_RECORDS = 27
PAGES_BY_COUNTY = {"Lee": 57}
PAGES_BY_MUNICIPALITY = {"Bonita Springs": 6, "Cape Coral": 4, "Captiva": 3, "Estero": 4, "Fort Myers": 34,
                         "Fort Myers Beach": 4, "North Fort Myers": 2}
BEACH_ISLAND_MUNICIPALITIES = ("Fort Myers Beach", "Sanibel", "Captiva")
#: the old brand the 4760 S Cleveland building traded under: retired, held, never live (read from the held row's own
#: identity aliases; these are the alias words that mark it)
RETIRED_BRAND_WORD = "travelodge"
#: the one published Travelodge, a DIFFERENT building
PUBLISHED_TRAVELODGE = ("travelodge by wyndham fort myers cape coral", "13353", "33903")
_FEE_SENTENCE = re.compile(r"A \$([0-9][0-9,]*(?:\.[0-9]{2})?) fee applies")
_SUMMARY = re.compile(r'<p class="hp-summary">(.*?)</p>', re.S)
_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")
_REGION = re.compile(r'"addressRegion":\s*"([A-Z]{2})"')
_POSTAL = re.compile(r'"postalCode":\s*"(\d{5})')
_CITY = re.compile(r'"addressLocality":\s*"([^"]+)"')
_STREET = re.compile(r'"streetAddress":\s*"([^"]+)"')
_REFRESH = re.compile(r'http-equiv="refresh"\s+content="\d+;\s*url=([^"]*)"', re.I)


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _dump(path, doc):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def _routes(path):
    with open(path, encoding="utf-8") as fh:
        return set(_LOC.findall(fh.read()))


def _curl(url):
    return subprocess.run(["curl", "-s", "--max-time", "60", url], capture_output=True).stdout


def _code(url):
    return subprocess.run(["curl", "-s", "--max-time", "60", "-o", os.devnull, "-w", "%{http_code}", url],
                          capture_output=True, text=True).stdout.strip()


def _status_rows(path):
    if not path or not os.path.isfile(path):
        return []
    return [tuple(l.split(None, 1)) for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]


def _market_ids(markets):
    return {m.get("market_id") if isinstance(m, dict) else m for m in (markets or ())}


def _authorization():
    """The ONE authorization naming fort-myers-fl that the authorizing order wrote, resolved from the records."""
    mine = [a for a in DA.list_authorizations()
            if a.get("work_order") == AUTHORIZING_ORDER and MARKET in _market_ids(a.get("participating_markets"))]
    if len(mine) != 1:
        raise SystemExit("expected exactly one %s authorization from %s, found %s"
                         % (MARKET, AUTHORIZING_ORDER, [a.get("authorization_id") for a in mine]))
    return DA.load_authorization(mine[0]["authorization_id"])


def _norm(value):
    return " ".join(str(value or "").lower().split())


def _house(street):
    m = re.match(r"\s*(\d+)", str(street or ""))
    return m.group(1) if m else ""


def _held_cohorts():
    """The held cohorts, built exactly as the authorization accounting built them (actionability + clean authority,
    never typed), as name -> identity keys, plus identity_key -> canonical name and the census rows."""
    from scripts.pettripfinder import fort_myers_fl_candidate_accounting_003 as ACC
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    name_of = {h["identity_key"]: h["canonical_name"] for h in census["hotels"]}
    for h in census.get("non_admitted") or ():
        name_of.setdefault(h["identity_key"], h["canonical_name"])
    actionability = _load(os.path.join(REPORTS, "fort_myers_fl_actionability_001.json"))
    clean = _load(os.path.join(REPORTS, "fort_myers_fl_clean_authority_001.json"))
    name_of.update({r["identity_key"]: r["canonical_name"] for r in clean["rows"]})
    rows = actionability["rows"]
    unresolved_keys = {r["identity_key"] for r in rows}
    groups = OrderedDict((
        ("founder_named_old_luckett_comfort_suites_and_mainstay", list(ACC.OLD_LUCKETT_KEYS)),
        ("founder_named_quality_inn_4760_s_cleveland", [ACC.CLEVELAND_REBRAND_KEY]),
        ("founder_named_latitude_26", sorted(k for k in name_of if k.startswith(ACC.LATITUDE_PREFIX))),
        ("founder_named_pink_shell_and_edison", [k for k in ACC.SHARED_READER_KEYS if k in unresolved_keys]),
        ("router_exhausted_rows", [r["identity_key"] for r in rows if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]),
        ("all_unresolved_rows", [r["identity_key"] for r in rows]),
        ("verified_no_pets_rows", [r["identity_key"] for r in clean["rows"]
                                   if r["disposition"] == "CLEAN_VERIFIED_NO_PETS"]),
    ))
    return groups, name_of, census, ACC


# --------------------------------------------------------------------------- predeploy

def predeploy(args):
    """Everything the order requires BEFORE the deploy, on the exact prebuilt bytes; nothing is rebuilt."""
    from scripts.pettripfinder import fast_release_lane as FL
    from scripts.pettripfinder import launch_participation as LP
    problems = []
    auth = _authorization()
    bundle_manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    gd_manifest = GD.build_manifest(bundle_manifest)
    readiness = _load(READINESS)
    binds = readiness["the_digests_this_readiness_binds"]
    acct = _load(ACCOUNTING)

    # 1. the parent is still live
    live_idx, live_state, live_problems = RI.live_index()
    live_markets = [m for m, i in live_idx.markets.items() if i.participating]
    live_index_routes = sum(len(i.routes) for i in live_idx.markets.values() if i.participating)
    parent = OrderedDict((("deploy_id", live_state.deploy_id), ("source_commit", live_state.source_commit),
                          ("bundle_sha256", live_state.bundle_sha256), ("markets", len(live_markets)),
                          ("profiles", live_idx.total_profiles), ("release_index_routes", live_index_routes),
                          ("served_routes", live_state.sitemap_route_count),
                          ("sitemap_sha256", live_state.sitemap_sha256), ("problems", live_problems)))
    if live_problems or live_state.deploy_id != auth["rollback_target"] or live_state.deploy_id != PARENT_DEPLOY_ID:
        problems.append("live is %s (%s), not the authorized parent %s" % (live_state.deploy_id, live_problems,
                                                                         auth["rollback_target"]))
    if (len(live_markets), live_idx.total_profiles, live_index_routes, live_state.sitemap_route_count) \
            != PARENT_ACCOUNTING:
        problems.append("the parent's accounting moved: %s" % dict(parent))

    # 2. the authorization: exact, AUTHORIZED, unconsumed, deployable, bound to the founder's decision
    site_info = _load(args.site_info)
    package_id = binds["sealed_package_id"]
    binding = OrderedDict((
        ("authorization_id", auth["authorization_id"]), ("work_order", auth.get("work_order")),
        ("status", auth["authorization_status"]),
        ("deploy_id", auth.get("deploy_id")), ("market_in_authorization", MARKET in _market_ids(auth["participating_markets"])),
        ("readiness_status", readiness.get("status")),
        ("readiness_package", package_id), ("readiness_package_digest", binds["sealed_package_digest"]),
        ("package_named_in_authorization_source", package_id in auth["authorization_source"]),
        ("founder_binding_commit_named_in_authorization_source", FOUNDER_BINDING_COMMIT in auth["authorization_source"]),
        ("founder_decision_commit_named_in_authorization_source",
         FOUNDER_DECISION_COMMIT in auth["authorization_source"]),
        ("participation", LP.launch_status(MARKET)),
        ("participation_decision_work_order", LP.load_participation()["decision"]["work_order"]),
        ("participation_decision_binds", FOUNDER_BINDING_COMMIT in LP.load_participation()["decision"]["reason"]),
        ("bundle_sha256", auth["bundle_sha256"]), ("sitemap_sha256", auth["sitemap_sha256"]),
        ("rollback_target", auth["rollback_target"]), ("readiness_parent", binds["parent_live_deploy_id"]),
        ("source_commit", auth["source_commit"]),
        ("total_files", auth["total_files"]), ("total_profiles", auth["total_profiles"]),
        ("sitemap_route_count", auth["sitemap_route_count"]), ("markets", len(auth["participating_markets"])),
    ))
    expected = OrderedDict((("work_order", AUTHORIZING_ORDER), ("status", DA.AUTHORIZED), ("deploy_id", None),
                            ("market_in_authorization", True), ("readiness_status", "AUTHORIZATION_READY"),
                            ("readiness_package", AUTHORIZED_PACKAGE_ID),
                            ("package_named_in_authorization_source", True),
                            ("founder_binding_commit_named_in_authorization_source", True),
                            ("founder_decision_commit_named_in_authorization_source", True),
                            ("participation", LP.FOUNDER_AUTHORIZED_FOR_LAUNCH),
                            ("participation_decision_work_order", AUTHORIZING_ORDER),
                            ("participation_decision_binds", True),
                            # the digests the committed candidate manifest carries (read, never typed): the
                            # authorization must bind exactly these
                            ("bundle_sha256", _load(CANDIDATE_MANIFEST)["bundle_sha256"]),
                            ("sitemap_sha256", _load(CANDIDATE_MANIFEST)["sitemap_sha256"]),
                            ("rollback_target", PARENT_DEPLOY_ID), ("readiness_parent", PARENT_DEPLOY_ID),
                            ("total_files", CANDIDATE_FILES),
                            ("source_commit", _load(CANDIDATE_MANIFEST)["source_commit"]),
                            ("total_profiles", CANDIDATE_ACCOUNTING[1]),
                            ("sitemap_route_count", CANDIDATE_ACCOUNTING[3]), ("markets", CANDIDATE_ACCOUNTING[0])))
    wrong = OrderedDict((k, (binding[k], v)) for k, v in expected.items() if binding[k] != v)
    if wrong:
        problems.append("the authorization does not bind what the order names: %s" % dict(wrong))
    if package_id.startswith(REFUSED_PACKAGE_PREFIXES):
        problems.append("the readiness packet binds a refused package %s" % package_id)
    if not auth["source_commit"].startswith(FOUNDER_DECISION_COMMIT):
        problems.append("the authorization's source commit is %s, not the founder-decision BUILD commit %s"
                        % (auth["source_commit"], FOUNDER_DECISION_COMMIT))
    others = [a["authorization_id"] for a in DA.list_authorizations()
              if a["authorization_id"] != auth["authorization_id"]
              and a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
    if others:
        problems.append("other authorizations are deployable: %s" % others)
    verify = DA.verify_authorization(auth, manifest=gd_manifest)
    deployability = DA.deployability_problems(auth, manifest=gd_manifest)
    target = DA.verify_target(auth, site_info)
    for label, found in (("verify_authorization", verify), ("deployability_problems", deployability),
                         ("verify_target", target)):
        if found:
            problems.append("%s: %s" % (label, found[:3]))

    # 3. the exact prebuilt bytes, re-hashed from disk (never rebuilt)
    directory = DA.verify_bundle_directory(auth, Path(args.candidate) / "site")
    if directory:
        problems.append("verify_bundle_directory: %s" % directory[:3])
    candidate_manifest_bytes_equal = gd_manifest == _load(CANDIDATE_MANIFEST)
    if not candidate_manifest_bytes_equal:
        problems.append("the committed candidate manifest no longer describes the bundle on disk")
    cand_sitemap_path = os.path.join(args.candidate, "site", "sitemap.xml")
    cand_sitemap_sha = hashlib.sha256(open(cand_sitemap_path, "rb").read()).hexdigest()
    cand_routes = _routes(cand_sitemap_path)
    file_count = sum(len(f) for _d, _s, f in os.walk(os.path.join(args.candidate, "site")))
    rehash = OrderedDict((("bundle_sha256", gd_manifest["bundle_sha256"]),
                          ("AUTHORIZED_BUNDLE_MATCH", "PASS" if gd_manifest["bundle_sha256"] == auth["bundle_sha256"]
                           and not directory else "FAIL"),
                          ("sitemap_sha256_from_disk", cand_sitemap_sha),
                          ("AUTHORIZED_SITEMAP_MATCH", "PASS" if cand_sitemap_sha == auth["sitemap_sha256"] else "FAIL"),
                          ("files_on_disk", file_count), ("served_routes", len(cand_routes)),
                          ("fort_myers_served_routes", len([r for r in cand_routes if "/%s/" % MARKET in r]))))
    if rehash["AUTHORIZED_BUNDLE_MATCH"] != "PASS" or rehash["AUTHORIZED_SITEMAP_MATCH"] != "PASS" \
            or file_count != CANDIDATE_FILES or len(cand_routes) != CANDIDATE_ACCOUNTING[3] \
            or rehash["fort_myers_served_routes"] != MARKET_ACCOUNTING[2]:
        problems.append("the bytes on disk are not the authorized candidate: %s" % dict(rehash))

    # 4-12. the accounting the authorization order wrote, re-read
    ident = acct["identity_safety"]
    muni = ident["MUNICIPALITY_PAGES"]
    fees = ident["fee_safety"]
    outside = acct["outside_hotel_inventory_safety"]
    operating = acct["operating_status_safety"]
    schemes = acct["route_scheme_safety"]
    collide = acct["cross_market_collision_safety"]
    preserve = acct["byte_preservation"]
    gates = OrderedDict((
        ("ALL_ACCOUNTING_GATES", acct["ALL_ACCOUNTING_GATES"]),
        ("determinism", acct["candidate_determinism"]["result"]),
        ("files_compared", acct["candidate_determinism"]["files_compared"]),
        ("files_differing", acct["candidate_determinism"]["files_differing"]),
        ("unapproved_profiles", acct["hold_safety"]["UNAPPROVED_FORT_MYERS_PROFILES"]),
        ("held_groups", OrderedDict((k, v["published"]) for k, v in ident["groups"].items())),
        ("held_group_rows", OrderedDict((k, v["rows"]) for k, v in ident["groups"].items())),
        ("held_rows_published", ident["HELD_ROWS_PUBLISHED"]),
        ("verified_no_pets_published_as_profiles", ident["VERIFIED_NO_PETS_PUBLISHED_AS_PROFILES"]),
        ("founder_premises_pages", ident["FOUNDER_PREMISES_PAGES"]),
        ("travelodge_pages_at_4760", ident["TRAVELODGE_PAGES_AT_4760"]),
        ("identity_resolutions_ruling_written", ident["identity_resolutions_ruling_written"]),
        ("outside_published", OrderedDict((k, v["PUBLISHED"]) for k, v in outside["classes"].items())),
        ("outside_rows", OrderedDict((k, v["rows"]) for k, v in outside["classes"].items())),
        ("municipality_pages", OrderedDict((k, muni[k]) for k in (
            "profile_pages_checked", "profile_pages_by_county", "profile_pages_by_municipality",
            "WRONG_STATE_CITY_ZIP_OR_COUNTY_PAGES", "NAPLES_PAGES", "OTHER_MARKET_TEXT_PAGES"))),
        ("operating", OrderedDict((k, operating[k]) for k in (
            "published_by_status", "NONOPERATING_PROFILES", "TEMPORARILY_CLOSED_PROFILES",
            "PERMANENTLY_CLOSED_PROFILES", "PREOPENING_PROFILES", "CLOSED_FOR_REBUILD_PROFILES",
            "STATUS_UNKNOWN_PROFILES", "unbound_nonoperating_signals_published"))),
        ("route_schemes", OrderedDict((k, schemes[k]) for k in (
            "go_pages_checked", "INVALID_ROUTE_SCHEMES", "HTTP_LESS_FIRST_PARTY_ROUTES"))),
        ("reader_safety", acct["reader_safety"]),
        ("misleading_single_fees", fees["misleading_single_fees_published"]),
        ("fee_withholding", fees["fee_withholding"]),
        ("fees_on_the_page", fees["on_the_page"]),
        ("fees_rendered_wrongly", fees["FEES_RENDERED_WRONGLY"]),
        ("cross_market_collision_safe", collide["CROSS_MARKET_COLLISION_SAFE"]),
        ("cross_market_collisions", collide["CROSS_MARKET_COLLISIONS"]),
        ("bare_chain_collisions", collide["BARE_CHAIN_COLLISIONS"]),
        ("duplicate_excluded_identities", collide["DUPLICATE_EXCLUDED_IDENTITIES"]),
        ("files_added", preserve["files_added"]), ("files_removed", preserve["files_removed"]),
        ("added_by_class", preserve["added_by_class"]),
        ("prior_market_files_changed", len(preserve["prior_market_files_changed"])),
        ("unclassified_paths", len(preserve["unclassified_paths"])),
        ("changed_global_artifacts", preserve["changed_global_artifacts"]),
        ("unexpected_market_delta", acct["delta_safety"]["unexpected_market_delta"]),
        ("unexpected_profile_delta", acct["delta_safety"]["unexpected_profile_delta"]),
        ("unexpected_route_delta", acct["delta_safety"]["unexpected_route_delta"]),
        ("unexpected_served_route_delta", acct["delta_safety"]["unexpected_served_route_delta"]),
        ("prior_lost", OrderedDict((k, acct["delta_safety"][k]) for k in (
            "PRIOR_MARKETS_LOST", "PRIOR_PROFILES_LOST", "PRIOR_RELEASE_INDEX_ROUTES_LOST", "PRIOR_SERVED_ROUTES_LOST"))),
        ("candidate", OrderedDict((k, acct["candidate_bundle"][k]) for k in (
            "bundle_sha256", "sitemap_sha256", "file_count", "markets", "profiles", "release_index_routes",
            "served_sitemap_routes"))),
        ("fort_myers", OrderedDict((k, acct["fort_myers"][k]) for k in (
            "profiles", "release_index_routes", "served_routes"))),
        ("route_set_agreement_with_staging",
         acct["fort_myers"]["route_set_agreement_with_registration_staging"]["EXACT_ROUTE_SET_AGREEMENT"]),
    ))
    bad = []
    if gates["ALL_ACCOUNTING_GATES"] != "PASS" or gates["determinism"] != "BYTE_IDENTICAL" \
            or gates["files_differing"] or gates["files_compared"] != CANDIDATE_FILES:
        bad.append("accounting / determinism")
    rows = gates["held_group_rows"]
    if gates["unapproved_profiles"] or any(gates["held_groups"].values()) or gates["held_rows_published"] \
            or gates["verified_no_pets_published_as_profiles"] or any(gates["founder_premises_pages"].values()) \
            or gates["travelodge_pages_at_4760"] or gates["identity_resolutions_ruling_written"] \
            or any(rows.get(k) != n for k, n in HELD_GROUP_ROWS.items()):
        bad.append("held-cohort safety")
    if any(gates["outside_published"].values()) or dict(gates["outside_rows"]) != OUTSIDE_ROWS:
        bad.append("non-hotel safety")
    mp = gates["municipality_pages"]
    if mp["WRONG_STATE_CITY_ZIP_OR_COUNTY_PAGES"] or mp["NAPLES_PAGES"] or mp["OTHER_MARKET_TEXT_PAGES"] \
            or mp["profile_pages_checked"] != MARKET_ACCOUNTING[0] \
            or dict(mp["profile_pages_by_county"]) != PAGES_BY_COUNTY \
            or dict(mp["profile_pages_by_municipality"]) != PAGES_BY_MUNICIPALITY:
        bad.append("municipality / boundary safety")
    op = gates["operating"]
    if dict(op["published_by_status"]) != {"CURRENTLY_OPEN": MARKET_ACCOUNTING[0]} \
            or any(v for k, v in op.items() if k != "published_by_status"):
        bad.append("operating-status safety")
    rs = gates["route_schemes"]
    if rs["go_pages_checked"] != GO_PAGES or rs["INVALID_ROUTE_SCHEMES"] or rs["HTTP_LESS_FIRST_PARTY_ROUTES"]:
        bad.append("route-scheme safety")
    if any(gates["reader_safety"].values()) or gates["misleading_single_fees"]:
        bad.append("reader safety")
    fw, fp = gates["fee_withholding"], gates["fees_on_the_page"]
    if (fw["fees_published"], fw["tiered_fees_withheld"], fw["unsafe_single_fees_withheld"]) != FEES \
            or fw["misleading_single_fees_published"] \
            or fp["pages_rendering_exactly_that_fee"] != FEES[0] or fp["withheld_records"] != WITHHELD_FEE_RECORDS \
            or fp["withheld_records_rendering_a_fee"] or fp["pages_without_a_fee_rendering_a_fee"] \
            or gates["fees_rendered_wrongly"]:
        bad.append("fee safety")
    if gates["cross_market_collision_safe"] != "PASS" or gates["cross_market_collisions"] \
            or gates["bare_chain_collisions"] or gates["duplicate_excluded_identities"]:
        bad.append("collision safety")
    if gates["files_added"] != CANDIDATE_FILES_ADDED or gates["files_removed"] \
            or {k: v for k, v in gates["added_by_class"].items() if v} != {"fort_myers": CANDIDATE_FILES_ADDED} \
            or gates["prior_market_files_changed"] or gates["unclassified_paths"] \
            or gates["changed_global_artifacts"] != ["sitemap.xml"] \
            or gates["unexpected_market_delta"] or gates["unexpected_profile_delta"] \
            or gates["unexpected_route_delta"] or gates["unexpected_served_route_delta"] \
            or any(gates["prior_lost"].values()):
        bad.append("delta safety")
    if (gates["candidate"]["markets"], gates["candidate"]["profiles"], gates["candidate"]["release_index_routes"],
            gates["candidate"]["served_sitemap_routes"]) != CANDIDATE_ACCOUNTING \
            or gates["candidate"]["file_count"] != CANDIDATE_FILES \
            or (gates["fort_myers"]["profiles"], gates["fort_myers"]["release_index_routes"],
                gates["fort_myers"]["served_routes"]) != MARKET_ACCOUNTING \
            or not gates["route_set_agreement_with_staging"] \
            or gates["candidate"]["bundle_sha256"] != auth["bundle_sha256"] \
            or gates["candidate"]["sitemap_sha256"] != auth["sitemap_sha256"]:
        bad.append("candidate accounting")
    if bad:
        problems.append("authorization-order accounting does not hold: %s" % bad)

    # 13. the FAST receipt the readiness packet binds (by path AND digest) is the one currently eligible receipt;
    # the source-ready shadow digest selects nothing from the canonical receipts
    package = _load(os.path.join(PKG, "markets", "packages", MARKET, "%s.json" % AUTHORIZED_PACKAGE_ID))
    receipts = FL.eligible_receipts(MARKET, package["package_digest"])
    bound_receipt = os.path.join(_DASH, *binds["fast_receipt"].split("/"))
    # the receipt digest is the lane's own: canonical JSON of the receipt without its timing / environment blocks,
    # recomputed here and required to equal both the stored RECEIPT_DIGEST and the readiness packet's binding
    bound_doc = _load(bound_receipt)
    recomputed = FL.SMP.sha256_text(FL.SMP.canonical_json(
        OrderedDict((k2, v) for k2, v in bound_doc.items()
                    if k2 not in ("TIMESTAMPS", "ENVIRONMENT", "PERFORMANCE", "RECEIPT_DIGEST"))))
    bound_digest = recomputed if recomputed == bound_doc.get("RECEIPT_DIGEST") else "MISMATCH:%s" % recomputed
    receipt = _load(str(receipts[-1])) if receipts else {}
    j = ((receipt.get("RESULTS") or {}).get("J") or {})
    k = ((receipt.get("RESULTS") or {}).get("K") or {})
    shadow = FL.eligible_receipts(MARKET, SOURCE_READY_DIGEST)
    fast = OrderedDict((("selected", os.path.basename(str(receipts[-1])) if receipts else None),
                        ("readiness_binds", os.path.basename(bound_receipt)),
                        ("readiness_binds_digest", binds["fast_receipt_digest"]),
                        ("receipt_digest_on_disk", bound_digest),
                        ("eligible_receipts", len(receipts)),
                        ("package_digest", package["package_digest"]),
                        ("rule_J", j.get("status")), ("rule_J_file_count", (j.get("detail") or {}).get("file_count")),
                        ("rule_J_html_count", (j.get("detail") or {}).get("html_count")),
                        ("rule_J_bundle_sha256", (j.get("detail") or {}).get("bundle_sha256")),
                        ("rule_K", k.get("status")),
                        ("rule_K_result", (k.get("detail") or {}).get("result")),
                        ("defects", FL.receipt_output_defects(receipt) if receipt else ["no receipt"]),
                        ("source_ready_shadow_digest_selects", [os.path.basename(str(p)) for p in shadow]),
                        ("FAILED_FIRST_SEAL_RECEIPT_ELIGIBLE", "NO" if not shadow else "YES")))
    if len(receipts) != 1 or fast["selected"] != fast["readiness_binds"] or bound_digest != binds["fast_receipt_digest"] \
            or fast["rule_J"] != "PASS" or fast["rule_K"] != "PASS" or fast["defects"] \
            or not (fast["rule_J_file_count"] or 0) or not (fast["rule_J_html_count"] or 0) \
            or fast["rule_J_bundle_sha256"] != binds["changed_market_bundle_sha256"] or shadow:
        problems.append("the FAST receipt is not the one currently eligible receipt: %s" % dict(fast))

    report = OrderedDict((
        ("schema", "ptf-predeploy-verification/1.0"), ("work_order", WORK_ORDER),
        ("authorizing_work_order", AUTHORIZING_ORDER), ("market_id", MARKET),
        ("parent", parent),
        ("host_site", OrderedDict((("name", site_info.get("name")), ("ssl_url", site_info.get("ssl_url")),
                                   ("published_deploy", (site_info.get("published_deploy") or {}).get("id")),
                                   ("state", (site_info.get("published_deploy") or {}).get("state"))))),
        ("authorization", binding), ("verify_authorization", verify), ("deployability_problems", deployability),
        ("verify_target", target), ("verify_bundle_directory", directory), ("rehash", rehash),
        ("candidate_manifest_matches_bundle_on_disk", candidate_manifest_bytes_equal),
        ("authorization_order_accounting", gates), ("fast_receipt", fast),
        ("problems", problems), ("PREDEPLOY", "PASS" if not problems else "FAIL"),
    ))
    print(json.dumps(OrderedDict((k2, report[k2]) for k2 in (
        "parent", "host_site", "authorization", "verify_authorization", "deployability_problems", "verify_target",
        "verify_bundle_directory", "rehash", "fast_receipt", "problems", "PREDEPLOY")), indent=1))
    if args.write:
        _dump(PREDEPLOY, report)
        print("written:", os.path.relpath(PREDEPLOY, _DASH))
    return 0 if not problems else 1


# --------------------------------------------------------------------------- write-manifest

def write_manifest(args):
    """The canonical live manifest, written from the EXACT authorized bytes immediately before the deploy."""
    pre = _load(PREDEPLOY)
    if pre["PREDEPLOY"] != "PASS":
        raise SystemExit("refusing to write the live manifest: predeploy did not pass")
    auth = _authorization()
    bundle_manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    doc = GD.build_manifest(bundle_manifest)
    if doc["bundle_sha256"] != auth["bundle_sha256"] or doc["sitemap_sha256"] != auth["sitemap_sha256"]:
        raise SystemExit("the bundle on disk is not the authorized bundle")
    if doc != _load(CANDIDATE_MANIFEST):
        raise SystemExit("the live manifest would differ from the committed candidate manifest")
    print("manifest -> bundle %s sitemap %s profiles %s routes %s markets %d"
          % (doc["bundle_sha256"][:12], doc["sitemap_sha256"][:12], doc["total_published_profiles"],
             doc["sitemap_route_count"], len(doc["participating_markets"])))
    if args.write:
        GD.write_manifest(bundle_manifest)
        problems = GD.verify_manifest()
        print("verify_manifest:", problems)
        if problems or GD.load_manifest() != doc:
            raise SystemExit("the written live manifest does not verify")
    return 0


# --------------------------------------------------------------------------- verify-live

def _go_target_ok(target):
    """A /go/ redirect is tel:, internal (/...), or absolute http(s) with a host -- never scheme-less."""
    if target.startswith("tel:"):
        return re.fullmatch(r"tel:\+?[0-9-]{7,}", target) is not None
    if target.startswith("/"):
        return not target.startswith("//")
    return re.match(r"https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:[:/?#]|$)", target) is not None


def verify_live(args):
    from scripts.pettripfinder.markets.contract import parse_market
    from scripts.pettripfinder import fort_myers_fl_geography_001 as GEO
    problems = []
    auth = _authorization()
    manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    cand_routes = _routes(os.path.join(args.candidate, "site", "sitemap.xml"))
    parent_routes = _routes(args.parent_sitemap)
    served = _curl(HOST + "/sitemap.xml")
    live_sitemap_sha = hashlib.sha256(served).hexdigest()
    host_match = live_sitemap_sha == manifest["sitemap_sha256"] == auth["sitemap_sha256"]
    if not host_match:
        problems.append("the served sitemap %s is not the authorized %s" % (live_sitemap_sha, auth["sitemap_sha256"]))
    live_routes = set(_LOC.findall(served.decode("utf-8", "replace")))
    if live_routes != cand_routes:
        problems.append("the served route SET differs from the authorized candidate's")
    lost = sorted(parent_routes - live_routes)
    added = sorted(live_routes - parent_routes)
    added_not_mine = [r for r in added if "/%s/" % MARKET not in r]
    if lost:
        problems.append("prior served routes lost: %d" % len(lost))
    if added_not_mine:
        problems.append("routes added that are not %s: %s" % (MARKET, added_not_mine[:5]))
    mine_expected = sorted(r for r in cand_routes if "/%s/" % MARKET in r)
    mine_live = sorted(r for r in live_routes if "/%s/" % MARKET in r)
    fragments = manifest["fragments"]
    markets_live = sorted(m for m, f in fragments.items() if (f.get("hub_route") or "") in live_routes
                          or any(r in live_routes for r in (f.get("hotel_routes") or [])[:1]))

    my_rows = _status_rows(args.market_sweep)
    my_not_200 = [(c, r) for c, r in my_rows if c != "200"]
    if {r.strip() for _c, r in my_rows} != set(mine_expected):
        problems.append("the %s sweep covered %d routes, %d are expected" % (MARKET, len(my_rows), len(mine_expected)))
    if my_not_200:
        problems.append("%s routes not 200: %d" % (MARKET, len(my_not_200)))
    prior_rows = _status_rows(args.prior_sweep)
    prior_bad = [(c, r) for c, r in prior_rows if c != "200"]
    if {r.strip() for _c, r in prior_rows} != parent_routes:
        problems.append("the prior sweep covered %d of %d parent routes" % (len(prior_rows), len(parent_routes)))
    if prior_bad:
        problems.append("prior routes not 200: %d" % len(prior_bad))

    mine = fragments[MARKET]
    sample_rel = ["index.html", "pet-friendly-hotels/index.html", "robots.txt", "llms.txt", "sitemap.xml",
                  mine["hub_route"].strip("/") + "/index.html", mine["comparison_route"].strip("/") + "/index.html"]
    sample_rel += [r.strip("/") + "/index.html" for r in mine["corridor_routes"]]
    for other in SPOT:
        if other in fragments and other != MARKET:
            sample_rel.append(fragments[other]["hub_route"].strip("/") + "/index.html")
    byte_checks, byte_mismatch = OrderedDict(), []
    for rel in sample_rel:
        local = os.path.join(args.candidate, "site", *rel.split("/"))
        if not os.path.isfile(local):
            byte_mismatch.append(rel + " (missing locally)")
            continue
        want = hashlib.sha256(open(local, "rb").read()).hexdigest()
        url = HOST + "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)
        ok = hashlib.sha256(_curl(url)).hexdigest() == want
        byte_checks[rel] = ok
        if not ok:
            byte_mismatch.append(rel)
    if byte_mismatch:
        problems.append("pages whose served bytes are not the authorized bytes: %s" % byte_mismatch[:5])

    cfg = parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET)), source=MARKET)
    policy = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET))
    pf = {(h.get("identity_key") or h.get("key")): h for h in policy["hotels"]}
    pf_routes = {RI.hotel_route(cfg, h["name"]) for h in policy["hotels"]}
    groups, name_of, census, ACC = _held_cohorts()
    admitted = {h["identity_key"]: h for h in census["hotels"]}
    slug_of = {h["identity_key"]: h.get("slug") for h in census.get("non_admitted") or ()}
    slug_of.update({h["identity_key"]: h.get("slug") for h in census["hotels"]})

    def _held_urls(key, extra_names=()):
        names = [name_of.get(key, key)] + list(extra_names)
        urls = {RI.hotel_route(cfg, n) for n in names}
        slug = slug_of.get(key) or re.sub(r"[^a-z0-9]+", "-", key).strip("-")
        urls.add("/pet-friendly-hotels/%s/%s/" % (MARKET, slug))
        # a held row whose URL coincides with a PUBLISHED record's route is that record's page, not the held row's:
        # reported, never probed as a leak
        return sorted(urls - pf_routes), sorted(urls & pf_routes)

    # every UNPUBLISHED census row (51 unresolved + 34 verified-no-pets): the census slug AND the route the site
    # forms from its name; each must 404 and hold no served route
    held_keys = list(OrderedDict.fromkeys(groups["all_unresolved_rows"] + groups["verified_no_pets_rows"]))
    held_codes, held_live, coincident = OrderedDict(), [], OrderedDict()
    for key in held_keys:
        urls, shared = _held_urls(key)
        if shared:
            coincident[key] = shared
        codes = OrderedDict((u, _code(HOST + u)) for u in urls)
        held_codes[key] = codes
        if any(c == "200" for c in codes.values()) or any(u in live_routes for u in urls):
            held_live.append(key)
    not_404 = [k for k, cs in held_codes.items() if any(c != "404" for c in cs.values())]
    if held_live:
        problems.append("HELD identities are LIVE: %s" % held_live[:5])
    if coincident:
        problems.append("held rows share a route with a published record: %s" % dict(coincident))

    # the founder's named held rows, listed explicitly; the 4760 S Cleveland building also under every retired
    # Travelodge name its own census row carries (the founder: Travelodge is retired; nothing of it migrates)
    # the held row is a NON-ADMITTED census row (SAME_IDENTITY_REBRAND_SUCCESSOR); it is read at its own premises
    quality = [h for h in list(census["hotels"]) + list(census.get("non_admitted") or ())
               if h["identity_key"] == ACC.CLEVELAND_REBRAND_KEY and _house(h.get("street")) == "4760"]
    retired_names = sorted({a for h in quality for a in h.get("identity_key_aliases") or ()
                            if RETIRED_BRAND_WORD in a})
    named = OrderedDict()
    for label, keys in (("comfort_suites_9455_old_luckett", [ACC.OLD_LUCKETT_KEYS[0]]),
                        ("mainstay_suites_9455_old_luckett", [ACC.OLD_LUCKETT_KEYS[1]]),
                        ("quality_inn_4760_s_cleveland", [ACC.CLEVELAND_REBRAND_KEY]),
                        ("latitude_26_waterfront_inn_4701_bonita_beach", [ACC.LATITUDE_INN_KEY]),
                        ("latitude_26_all_rows", groups["founder_named_latitude_26"]),
                        ("pink_shell", [k for k in ACC.SHARED_READER_KEYS if "pink shell" in k]),
                        ("edison_beach_house", [k for k in ACC.SHARED_READER_KEYS if "edison" in k])):
        codes = OrderedDict()
        for key in keys:
            urls, shared = _held_urls(key)
            for u in urls:
                codes[u] = held_codes.get(key, {}).get(u) or _code(HOST + u)
            for u in shared:
                codes[u] = "SHARED_WITH_PUBLISHED"
        named[label] = OrderedDict((("identity_keys", keys), ("codes", codes),
                                    ("unpublished", bool(codes) and all(c == "404" for c in codes.values())
                                     and not any(u in live_routes for u in codes))))
    old_codes = OrderedDict()
    for n in retired_names:
        u = RI.hotel_route(cfg, n)
        old_codes[u] = "SHARED_WITH_PUBLISHED" if u in pf_routes else _code(HOST + u)
    named["old_travelodge_4760_s_cleveland"] = OrderedDict((
        ("retired_names", retired_names), ("codes", old_codes),
        ("unpublished", bool(old_codes) and all(c == "404" for c in old_codes.values())
         and not any(u in live_routes for u in old_codes))))
    named_not_unpublished = [k for k, v in named.items() if not v["unpublished"]]
    if named_not_unpublished:
        problems.append("founder-held rows are not safely unpublished: %s" % named_not_unpublished)

    # EVERY live Fort Myers profile, fetched whole
    status_of = {r["identity_key"]: r for r in _load(OPERATING_STATUS)["operating_status_accounting"]["rows"]}
    muni_rows, by_county, by_city, profile_bytes_bad = OrderedDict(), Counter(), Counter(), []
    fee_wrong, fee_counts, premises_hits, naples_hits, not_open = [], Counter(), [], [], []
    travelodges_live = []
    for k in sorted(pf):
        h = admitted.get(k) or {}
        route = RI.hotel_route(cfg, pf[k]["name"])
        raw = _curl(HOST + route)
        local = os.path.join(args.candidate, "site", *route.strip("/").split("/"), "index.html")
        same_bytes = os.path.isfile(local) and hashlib.sha256(raw).hexdigest() == hashlib.sha256(
            open(local, "rb").read()).hexdigest()
        if not same_bytes:
            profile_bytes_bad.append(route)
        body = raw.decode("utf-8", "replace")
        postal = str(h.get("postal_code") or "")[:5]
        county = GEO.county_for_postal(postal) or ""
        by_county[county] += 1
        by_city[h.get("city")] += 1
        regions, postals = set(_REGION.findall(body)), set(_POSTAL.findall(body))
        cities, streets = set(_CITY.findall(body)), set(_STREET.findall(body))
        ok = route in live_routes and regions == {"FL"} and postals == {postal} and cities == {h.get("city")} \
            and county == "Lee"
        if any(ACC.NAPLES_WORDS.search(x) for x in cities):
            naples_hits.append((k, sorted(cities)))
        for label, house, word in ACC.HELD_PREMISES:
            if any(_house(s) == house and word in _norm(s) for s in streets):
                premises_hits.append((k, label, sorted(streets)))
        if RETIRED_BRAND_WORD in _norm(pf[k]["name"]):
            travelodges_live.append(OrderedDict((("identity_key", k), ("street", sorted(streets)),
                                                 ("postal_code", sorted(postals)))))
        status = (status_of.get(k) or {}).get("status")
        if status != "CURRENTLY_OPEN" or (status_of.get(k) or {}).get("signals"):
            not_open.append((k, status))
        muni_rows[k] = OrderedDict((("route", route), ("street", h.get("street")), ("postal_code", h.get("postal_code")),
                                    ("city", h.get("city")), ("county", county),
                                    ("page_region", sorted(regions)), ("page_postal", sorted(postals)),
                                    ("page_city", sorted(cities)), ("page_street", sorted(streets)),
                                    ("operating_status", status),
                                    ("beach_or_island", bool((status_of.get(k) or {}).get("beach_or_island"))),
                                    ("byte_identical_to_artifact", same_bytes), ("municipality_zip_live", ok)))
        rendered = {x.replace(",", "") for x in _FEE_SENTENCE.findall(" ".join(_SUMMARY.findall(body)))}
        fee = (pf[k].get("facts") or {}).get("pet_fee")
        if fee:
            want = "%d" % (fee["amount_cents"] // 100) if fee["amount_cents"] % 100 == 0 \
                else "%.2f" % (fee["amount_cents"] / 100.0)
            fee_counts["fee_records"] += 1
            if rendered == {want}:
                fee_counts["fee_rendered_exactly"] += 1
            else:
                fee_wrong.append((k, want, sorted(rendered)))
        else:
            fee_counts["fee_less_records"] += 1
            if rendered:
                fee_wrong.append((k, None, sorted(rendered)))
    muni_wrong = [k for k, v in muni_rows.items() if not v["municipality_zip_live"]]
    if muni_wrong or dict(by_county) != PAGES_BY_COUNTY or dict(by_city) != PAGES_BY_MUNICIPALITY \
            or len(muni_rows) != MARKET_ACCOUNTING[0]:
        problems.append("Fort Myers profiles without their own municipality / ZIP / county live: %s (%s)"
                        % (muni_wrong[:5], dict(by_city)))
    if naples_hits:
        problems.append("Naples / Collier / Charlotte County places live: %s" % naples_hits)
    if premises_hits:
        problems.append("a live profile stands at a founder-held premises: %s" % premises_hits)
    trav_ok = [t["identity_key"] for t in travelodges_live] == [PUBLISHED_TRAVELODGE[0]] \
        and all(_house(s) == PUBLISHED_TRAVELODGE[1] for t in travelodges_live for s in t["street"]) \
        and all(p == [PUBLISHED_TRAVELODGE[2]] for p in (t["postal_code"] for t in travelodges_live))
    if not trav_ok:
        problems.append("the live Travelodge set is not the 13353 N Cleveland building alone: %s" % travelodges_live)
    if not_open:
        problems.append("published profiles not CURRENTLY open: %s" % not_open)
    if fee_wrong or fee_counts["fee_rendered_exactly"] != FEES[0]:
        problems.append("live fee sentences differ from the authorized records: %s" % fee_wrong[:5])
    if profile_bytes_bad:
        problems.append("live profiles whose bytes are not the authorized bytes: %s" % profile_bytes_bad[:5])

    # Fort Myers Beach / Sanibel / Captiva: every live profile by name, and every nonoperating beach / island row
    beach = OrderedDict((k, OrderedDict((("city", v["city"]), ("operating_status", v["operating_status"]),
                                         ("route", v["route"]))))
                        for k, v in muni_rows.items() if v["city"] in BEACH_ISLAND_MUNICIPALITIES or v["beach_or_island"])
    beach_bad = [k for k, v in beach.items() if v["operating_status"] != "CURRENTLY_OPEN"]
    nonop_rows = [r for r in status_of.values() if r["status"] != "CURRENTLY_OPEN" or r.get("signals")]
    nonop_live = []
    for r in nonop_rows:
        if r["identity_key"] in pf:
            continue
        urls, _shared = _held_urls(r["identity_key"])
        codes = [held_codes.get(r["identity_key"], {}).get(u) or _code(HOST + u) for u in urls]
        if any(c == "200" for c in codes) or any(u in live_routes for u in urls):
            nonop_live.append(r["identity_key"])
    if beach_bad or nonop_live:
        problems.append("nonoperating beach / island or closed rows live: %s %s" % (beach_bad, nonop_live))

    # timeshare / vacation-ownership, private condo / residence / rental and other non-hotel identities: no route,
    # no served route
    timeshare, rentals, non_hotel, military = ACC._outside_inventory_keys(census)
    na_name = {h["identity_key"]: h["canonical_name"] for h in census.get("non_admitted") or ()}
    outside, outside_ok = OrderedDict(), True
    for cls, keys in (("timeshare", timeshare), ("private_condo_residence_or_rental", rentals),
                      ("other_non_hotel", non_hotel), ("military_restricted", military)):
        rows = OrderedDict()
        for key in keys:
            route = RI.hotel_route(cfg, na_name.get(key, key))
            shared = route in pf_routes
            code = "SHARED_WITH_PUBLISHED" if shared else _code(HOST + route)
            ok = code == "404" and route not in live_routes
            outside_ok = outside_ok and ok
            rows[key] = OrderedDict((("name", na_name.get(key, key)), ("route", route), ("code", code), ("absent", ok)))
        outside[cls] = OrderedDict((("rows", len(rows)), ("published", sum(1 for v in rows.values() if not v["absent"])),
                                    ("identities", rows)))
    if not outside_ok or {c: v["rows"] for c, v in outside.items()} != OUTSIDE_ROWS:
        problems.append("a non-hotel identity is visible or the classes moved: %s"
                        % [n for c in outside.values() for n, v in c["identities"].items() if not v["absent"]])

    # EVERY Fort Myers /go/ page, fetched whole: the authorized bytes and a valid redirect scheme
    go_files = []
    for root, _dirs, files in os.walk(os.path.join(args.candidate, "site", "go", MARKET)):
        for f in files:
            go_files.append(os.path.relpath(os.path.join(root, f), os.path.join(args.candidate, "site")).replace(os.sep, "/"))
    go_files.sort()
    go_bad_bytes, go_bad_scheme, go_kinds = [], [], Counter()
    for rel in go_files:
        local = open(os.path.join(args.candidate, "site", *rel.split("/")), "rb").read()
        url = HOST + "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)
        raw = _curl(url)
        if hashlib.sha256(raw).digest() != hashlib.sha256(local).digest():
            go_bad_bytes.append(rel)
        targets = _REFRESH.findall(raw.decode("utf-8", "replace"))
        target = targets[0] if len(targets) == 1 else ""
        go_kinds["tel" if target.startswith("tel:") else "internal" if target.startswith("/") else "absolute_http"
                 if target.startswith("http") else "other"] += 1
        if not _go_target_ok(target):
            go_bad_scheme.append((rel, target))
    if len(go_files) != GO_PAGES or go_bad_bytes or go_bad_scheme:
        problems.append("/go/ pages: %d files, %d byte mismatches, invalid schemes %s"
                        % (len(go_files), len(go_bad_bytes), go_bad_scheme[:5]))

    spot = OrderedDict((m, int(_code("%s/pet-friendly-hotels/%s/" % (HOST, m)) or 0)) for m in SPOT)
    spot[MARKET] = int(_code("%s/pet-friendly-hotels/%s/" % (HOST, MARKET)) or 0)
    spot["detroit-must-be-absent"] = int(_code(HOST + "/pet-friendly-hotels/detroit-ann-arbor-mi/") or 0)
    if spot["detroit-must-be-absent"] != 404:
        problems.append("Detroit is not withheld")
    for m, c in spot.items():
        if m != "detroit-must-be-absent" and c != 200:
            problems.append("%s returned %s" % (m, c))

    host = OrderedDict((("published_deploy_id", None), ("state", None), ("context", None), ("published_at", None),
                        ("previous_deploy_id", None)))
    deploys = _load(args.host_state) if args.host_state and os.path.isfile(args.host_state) else []
    if deploys:
        host.update(OrderedDict((("published_deploy_id", deploys[0].get("id")), ("state", deploys[0].get("state")),
                                 ("context", deploys[0].get("context")), ("published_at", deploys[0].get("published_at")),
                                 ("previous_deploy_id", deploys[1].get("id") if len(deploys) > 1 else None))))
    if host["published_deploy_id"] != args.deployment_id or host["state"] != "ready":
        problems.append("the host publishes %r (%r), not %s" % (host["published_deploy_id"], host["state"],
                                                               args.deployment_id))
    if host["previous_deploy_id"] != auth["rollback_target"]:
        problems.append("the host's previous deploy is %r, not the parent %s" % (host["previous_deploy_id"],
                                                                                auth["rollback_target"]))
    quality = OrderedDict((k, manifest.get(k)) for k in ("broken_links", "collision_count",
                                                          "global_shadowing_count", "canonical_violations"))
    if any(quality.values()):
        problems.append("bundle quality counters are not zero: %s" % dict(quality))
    live_profiles = sum(len(f["hotel_routes"]) for f in fragments.values())
    live_index = sum(len(f["hotel_routes"]) + len(f["corridor_routes"]) + (1 if f.get("hub_route") else 0)
                     for f in fragments.values())
    if (len(markets_live), live_profiles, live_index, len(live_routes)) != CANDIDATE_ACCOUNTING:
        problems.append("live accounting is %s, not %s"
                        % ((len(markets_live), live_profiles, live_index, len(live_routes)), CANDIDATE_ACCOUNTING))
    checks = OrderedDict((
        ("sitemap_is_authorized", host_match),
        ("served_route_set_is_authorized", live_routes == cand_routes),
        ("every_fort_myers_route_200", bool(my_rows) and not my_not_200 and len(my_rows) == MARKET_ACCOUNTING[2]
         and len(mine_expected) == MARKET_ACCOUNTING[2]),
        ("no_parent_route_lost", not lost),
        ("every_prior_route_200", bool(prior_rows) and not prior_bad and len(prior_rows) == len(parent_routes)),
        ("only_fort_myers_added", not added_not_mine),
        ("served_bytes_are_authorized_bytes", not byte_mismatch),
        ("every_live_profile_byte_identical", not profile_bytes_bad and len(muni_rows) == MARKET_ACCOUNTING[0]),
        ("every_unpublished_identity_404", not held_live and not not_404 and not coincident),
        ("founder_held_rows_unpublished", not named_not_unpublished),
        ("only_the_13353_n_cleveland_travelodge_live", trav_ok),
        ("no_profile_at_a_founder_held_premises", not premises_hits),
        ("non_hotel_identities_absent", outside_ok),
        ("municipality_identity_live", not muni_wrong and len(muni_rows) == MARKET_ACCOUNTING[0]
         and dict(by_county) == PAGES_BY_COUNTY and dict(by_city) == PAGES_BY_MUNICIPALITY),
        ("no_naples_live", not naples_hits),
        ("every_live_profile_currently_open", not not_open),
        ("no_nonoperating_beach_island_or_closed_row_live", not beach_bad and not nonop_live),
        ("live_fees_are_authorized_fees", not fee_wrong and fee_counts["fee_rendered_exactly"] == FEES[0]),
        ("every_go_page_byte_identical_and_valid", len(go_files) == GO_PAGES and not go_bad_bytes
         and not go_bad_scheme),
        ("detroit_withheld", spot["detroit-must-be-absent"] == 404),
        ("spot_markets_200", all(c == 200 for m, c in spot.items() if m != "detroit-must-be-absent")),
        ("host_publishes_this_deploy", host["published_deploy_id"] == args.deployment_id and host["state"] == "ready"),
        ("host_previous_deploy_is_the_parent", host["previous_deploy_id"] == auth["rollback_target"]),
        ("bundle_quality_zero", not any(quality.values())),
        ("live_accounting_46_4430_4869_4948",
         (len(markets_live), live_profiles, live_index, len(live_routes)) == CANDIDATE_ACCOUNTING),
    ))
    report = OrderedDict((
        ("schema", "ptf-live-verification/1.0"), ("work_order", WORK_ORDER),
        ("authorizing_work_order", AUTHORIZING_ORDER), ("market_id", MARKET),
        ("authorization_id", auth["authorization_id"]), ("deployment_id", args.deployment_id),
        ("parent_deployment_id", auth["rollback_target"]), ("host", host),
        ("authorized_bundle_sha256", manifest["bundle_sha256"]),
        ("authorized_sitemap_sha256", manifest["sitemap_sha256"]), ("live_sitemap_sha256", live_sitemap_sha),
        ("host_sitemap_match", host_match), ("live_served_routes_unique", len(live_routes)),
        ("authorized_served_routes", len(cand_routes)),
        ("served_route_set_identical_to_authorized", live_routes == cand_routes),
        ("live_markets", len(markets_live)), ("live_profiles", live_profiles),
        ("live_release_index_routes", live_index),
        ("sitemap", OrderedDict((("parent_locs", len(parent_routes)), ("parent_routes_missing", lost),
                                 ("added_routes", len(added)), ("added_routes_not_fort_myers", added_not_mine)))),
        ("fort_myers", OrderedDict((
            ("hotel_routes", len(mine["hotel_routes"])), ("corridor_routes", len(mine["corridor_routes"])),
            ("hub_routes", 1), ("comparison_route", mine["comparison_route"]),
            ("release_index_routes", len(mine["hotel_routes"]) + len(mine["corridor_routes"]) + 1),
            ("expected_served_routes_from_authorized_candidate", len(mine_expected)),
            ("served_routes_in_live_sitemap", len(mine_live)), ("routes_swept", len(my_rows)),
            ("routes_http_200", len(my_rows) - len(my_not_200)), ("routes_missing", [r for _c, r in my_not_200]),
            ("route_results", OrderedDict((r.strip(), c) for c, r in my_rows)),
            ("corridors", sorted(r.rstrip("/").split("/")[-1] for r in mine["corridor_routes"])),
        ))),
        ("holds", OrderedDict((
            ("census_rows", len(census["hotels"])), ("published", len(pf)),
            ("unpublished_rows_probed", len(held_keys)),
            ("unresolved_rows", len(groups["all_unresolved_rows"])),
            ("verified_no_pets_rows", len(groups["verified_no_pets_rows"])),
            ("urls_probed", sum(len(c) for c in held_codes.values())),
            ("unpublished_not_404", not_404), ("unpublished_live", held_live),
            ("routes_shared_with_a_published_record", coincident),
            ("note", "EVERY unpublished census row -- the 51 unresolved (Comfort Suites and MainStay at 9455 Old "
                     "Luckett, the Quality Inn at 4760 S Cleveland, the Latitude 26 rows, Pink Shell, Edison Beach "
                     "House and the 49 router-exhausted rows) and the 34 verified-no-pets -- probed at its census slug "
                     "and at the route the site forms from its name; each must 404."),
        ))),
        ("founder_named_held_rows", named),
        ("travelodge", OrderedDict((("live", travelodges_live), ("ONLY_13353_N_CLEVELAND_LIVE", trav_ok),
                                    ("retired_4760_names_probed", retired_names)))),
        ("founder_premises_live_hits", premises_hits),
        ("municipality_identity", OrderedDict((("profiles_checked", len(muni_rows)),
                                               ("profiles_by_county", OrderedDict(sorted(by_county.items()))),
                                               ("profiles_by_municipality", OrderedDict(sorted(by_city.items()))),
                                               ("WRONG_CITY_STATE_ZIP_OR_COUNTY_PROFILES_LIVE", len(muni_wrong)),
                                               ("wrong", muni_wrong),
                                               ("NAPLES_PROFILES_LIVE", len(naples_hits)), ("naples", naples_hits),
                                               ("PROFILES_BYTE_IDENTICAL_TO_ARTIFACT",
                                                len(muni_rows) - len(profile_bytes_bad)),
                                               ("profile_byte_mismatches", profile_bytes_bad),
                                               ("profiles", muni_rows)))),
        ("operating_status", OrderedDict((("live_profiles_by_status", OrderedDict(sorted(Counter(
            v["operating_status"] for v in muni_rows.values()).items()))),
                                          ("NONOPERATING_PROFILES_LIVE", len(not_open)), ("not_open", not_open),
                                          ("nonoperating_rows", len(nonop_rows)),
                                          ("nonoperating_rows_live", nonop_live)))),
        ("beach_island", OrderedDict((("live_profiles", beach),
                                      ("by_municipality", OrderedDict(sorted(Counter(
                                          v["city"] for v in beach.values()).items()))),
                                      ("NONOPERATING_BEACH_ISLAND_PROFILES", len(beach_bad))))),
        ("fees_live", OrderedDict((("fee_records", fee_counts["fee_records"]),
                                   ("fee_rendered_exactly", fee_counts["fee_rendered_exactly"]),
                                   ("fee_less_records", fee_counts["fee_less_records"]),
                                   ("FEES_RENDERED_WRONGLY", len(fee_wrong)), ("wrong", fee_wrong)))),
        ("go_pages", OrderedDict((("checked", len(go_files)), ("by_kind", OrderedDict(sorted(go_kinds.items()))),
                                  ("byte_mismatches", go_bad_bytes), ("INVALID_GO_LINKS", len(go_bad_scheme)),
                                  ("invalid", go_bad_scheme)))),
        ("outside_hotel_inventory", outside),
        ("prior_routes", OrderedDict((("fetched", len(prior_rows)), ("not_200", prior_bad),
                                      ("prior_routes_lost", len(lost)), ("prior_profiles_lost", 0),
                                      ("prior_markets_lost", 0)))),
        ("byte_identity", OrderedDict((("pages_compared", len(byte_checks)),
                                       ("pages_byte_identical_to_artifact", sum(1 for v in byte_checks.values() if v)),
                                       ("mismatches", byte_mismatch)))),
        ("spot_checks", spot),
        ("quality", quality),
        ("checks", OrderedDict((k, "PASS" if v else "FAIL") for k, v in checks.items())),
        ("problems", problems),
        ("ALL_LIVE_CHECKS", "PASS" if not problems else "FAIL"),
        ("ROLLBACK_REQUIRED", "NO" if not problems else "YES"),
    ))
    print(json.dumps(OrderedDict((k, report[k]) for k in (
        "ALL_LIVE_CHECKS", "ROLLBACK_REQUIRED", "host", "live_markets", "live_profiles", "live_release_index_routes",
        "live_served_routes_unique", "checks", "problems")), indent=1))
    print("held probed %d rows / %d urls; profiles %d/%d; go %d; bytes %d/%d"
          % (len(held_codes), report["holds"]["urls_probed"], len(muni_rows) - len(profile_bytes_bad), len(muni_rows),
             len(go_files), report["byte_identity"]["pages_byte_identical_to_artifact"], len(byte_checks)))
    if args.write:
        _dump(VERIFICATION, report)
        print("written:", os.path.relpath(VERIFICATION, _DASH))
    return 0 if not problems else 1


# --------------------------------------------------------------------------- record

def record(args):
    live = _load(VERIFICATION)
    if live["ALL_LIVE_CHECKS"] != "PASS" or live["ROLLBACK_REQUIRED"] != "NO":
        raise SystemExit("refusing to record a deployment the host verification did not pass")
    host = live["host"]
    if host["published_deploy_id"] != args.deployment_id or host["state"] != "ready":
        raise SystemExit("the host does not publish %s as ready" % args.deployment_id)
    auth = DA.load_authorization(live["authorization_id"])
    if auth["authorization_status"] != DA.AUTHORIZED or auth.get("deploy_id"):
        raise SystemExit("%s is %s; only an AUTHORIZED, unconsumed authorization is consumed"
                         % (auth["authorization_id"], auth["authorization_status"]))
    if host["previous_deploy_id"] != auth["rollback_target"]:
        raise SystemExit("the host's previous deploy is not the authorized parent")
    others = [a["authorization_id"] for a in DA.list_authorizations()
              if MARKET in _market_ids(a.get("participating_markets"))
              and a["authorization_id"] != auth["authorization_id"]
              and a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
    if others:
        raise SystemExit("other deployable authorizations name %s: %s" % (MARKET, others))
    manifest = _load(MANIFEST)
    if manifest["bundle_sha256"] != auth["bundle_sha256"] or manifest["sitemap_sha256"] != auth["sitemap_sha256"]:
        raise SystemExit("the live manifest does not describe the authorized bundle")
    preserved = OrderedDict((m["market_id"], m["published_profiles"])
                            for m in manifest["participating_markets"] if m["market_id"] != MARKET)
    mine, holds, sitemap, prior = live["fort_myers"], live["holds"], live["sitemap"], live["prior_routes"]
    muni = live["municipality_identity"]
    results = OrderedDict([
        ("live_sitemap_sha256", live["live_sitemap_sha256"]), ("authorized_sitemap_sha256", auth["sitemap_sha256"]),
        ("sitemap_matches_authorized_candidate", live["host_sitemap_match"]),
        ("served_route_set_identical_to_authorized", live["served_route_set_identical_to_authorized"]),
        ("live_sitemap_route_count", live["live_served_routes_unique"]),
        ("authorized_sitemap_route_count", auth["sitemap_route_count"]),
        ("host_published_deploy_id", host["published_deploy_id"]), ("host_published_state", host["state"]),
        ("host_published_at", host["published_at"]), ("host_previous_deploy_id", host["previous_deploy_id"]),
        ("live_markets", live["live_markets"]), ("live_published_profiles", live["live_profiles"]),
        ("live_release_index_routes", live["live_release_index_routes"]),
        ("fort_myers_release_index_routes", mine["release_index_routes"]),
        ("fort_myers_served_routes", mine["served_routes_in_live_sitemap"]),
        ("fort_myers_routes_fetched_200", mine["routes_http_200"]),
        ("fort_myers_routes_missing", len(mine["routes_missing"])),
        ("fort_myers_corridors_live", mine["corridors"]),
        ("pages_byte_identical_to_artifact", "%d/%d" % (live["byte_identity"]["pages_byte_identical_to_artifact"],
                                                        live["byte_identity"]["pages_compared"])),
        ("holds_unpublished", OrderedDict([(k, holds[k]) for k in (
            "census_rows", "published", "unpublished_rows_probed", "unresolved_rows", "verified_no_pets_rows",
            "urls_probed", "note")] + [("held_routes_not_404", len(holds["unpublished_not_404"])),
                                       ("identity_resolutions_ruling_written", False)])),
        ("founder_named_held_rows_unpublished", live["checks"]["founder_held_rows_unpublished"] == "PASS"),
        ("only_the_13353_n_cleveland_travelodge_live",
         live["checks"]["only_the_13353_n_cleveland_travelodge_live"] == "PASS"),
        ("non_hotel_identities_absent", live["checks"]["non_hotel_identities_absent"] == "PASS"),
        ("municipality_profiles_checked", muni["profiles_checked"]),
        ("municipality_profiles_by_county", muni["profiles_by_county"]),
        ("municipality_profiles_by_municipality", muni["profiles_by_municipality"]),
        ("profiles_byte_identical_to_artifact", muni["PROFILES_BYTE_IDENTICAL_TO_ARTIFACT"]),
        ("wrong_city_state_zip_or_county_profiles_live", muni["WRONG_CITY_STATE_ZIP_OR_COUNTY_PROFILES_LIVE"]),
        ("naples_profiles_live", muni["NAPLES_PROFILES_LIVE"]),
        ("nonoperating_profiles_live", live["operating_status"]["NONOPERATING_PROFILES_LIVE"]),
        ("beach_island_profiles_live", live["beach_island"]["by_municipality"]),
        ("live_fee_records_rendered_exactly", live["fees_live"]["fee_rendered_exactly"]),
        ("live_fees_rendered_wrongly", live["fees_live"]["FEES_RENDERED_WRONGLY"]),
        ("go_pages_checked", live["go_pages"]["checked"]), ("invalid_go_links", live["go_pages"]["INVALID_GO_LINKS"]),
        ("previously_live_markets_published_profiles_preserved", preserved),
        ("parent_served_routes", sitemap["parent_locs"]), ("parent_routes_refetched", prior["fetched"]),
        ("parent_routes_not_200", len(prior["not_200"])), ("prior_routes_lost", prior["prior_routes_lost"]),
        ("prior_profiles_lost", prior["prior_profiles_lost"]), ("prior_markets_lost", prior["prior_markets_lost"]),
        ("added_routes", sitemap["added_routes"]),
        ("added_routes_not_fort_myers", len(sitemap["added_routes_not_fort_myers"])),
        ("spot_checks", live["spot_checks"]), ("quality", live["quality"]),
        ("unexpected_market_changes", 0), ("unexpected_profile_changes", 0),
        ("unexpected_route_changes", len(sitemap["added_routes_not_fort_myers"]) + len(sitemap["parent_routes_missing"])),
        ("checks", live["checks"]),
        ("first_authorization_and_first_deployment_for_this_market", True),
        ("all_critical_checks_pass", True),
    ])
    rec = DA.build_deployment_record(
        auth, deployment_record_id="ptf-deploy-fort-myers-004-%s" % args.deployment_id,
        deployment_id=args.deployment_id, previous_deployment_id=auth["rollback_target"],
        deployed_at=host["published_at"],
        deployer=OrderedDict([("work_order", WORK_ORDER), ("authorizing_work_order", AUTHORIZING_ORDER),
                              ("authorized_by", "founder"),
                              ("executed_by", "founder-authorized deploy run from the work order")]),
        production_url=HOST,
        deployed_directory=r"%s\site (the authorized candidate; its bundle and sitemap digests were verified "
                           r"against the authorization before the call)" % args.candidate.replace("/", "\\"),
        command=r"netlify deploy --prod --no-build --dir %s\site --site pettripfinder-prod"
                % args.candidate.replace("/", "\\"),
        global_gate_results=OrderedDict((k, True) for k in auth["required_gates"]),
        live_verification_results=results, final_status="DEPLOYED", rollback_used=False, exit_status=0)
    auth = DA.transition(
        auth, DA.DEPLOYED,
        note="Consumed by %s: deployed as %s. The served sitemap hashes to the authorized candidate and the served "
             "route SET is identical to it; %d/%d parent routes refetched 200 with 0 lost; all %d Fort Myers routes "
             "are live, all %d live profiles and %s sampled pages are byte-identical to the artifact, and all %d /go/ "
             "pages are byte-identical with valid schemes; all %d unpublished census rows -- Comfort Suites and "
             "MainStay at 9455 Old Luckett, the Quality Inn at 4760 S Cleveland (and its retired Travelodge names), "
             "the Latitude 26 rows, Pink Shell and Edison Beach House among them -- return 404, the only live "
             "Travelodge is the 13353 N Cleveland building, and the timeshare, private condo / residence / rental and "
             "other non-hotel identities have no route; every live profile states FL, its own municipality and "
             "postal code in Lee County with no Naples / Collier premises, every one is currently open, and every "
             "live fee is exactly the authorized one; Detroit remains withheld."
             % (WORK_ORDER, args.deployment_id, prior["fetched"] - len(prior["not_200"]), prior["fetched"],
                mine["routes_http_200"], results["profiles_byte_identical_to_artifact"],
                results["pages_byte_identical_to_artifact"], live["go_pages"]["checked"],
                holds["unpublished_rows_probed"]),
        consumed_by_work_order=WORK_ORDER, deployment_id=args.deployment_id,
        deployment_record_id=rec["deployment_record_id"])
    problems = DA.verify_record(rec, auth=auth)
    print("record problems:", problems)
    if problems:
        raise SystemExit("refusing to write an inconsistent record")
    if args.write:
        print("authorization:", DA.write_authorization(auth))
        print("record       :", DA.write_record(rec))
    return 0


# --------------------------------------------------------------------------- supersessions

def supersessions(args):
    doc = _load(SUPERSESSIONS)
    chain = doc["authorizations"]
    live = _load(VERIFICATION)
    auth_id = live["authorization_id"]
    auth = DA.load_authorization(auth_id)
    last = (auth.get("status_history") or [{}])[-1]
    if auth["authorization_status"] != DA.DEPLOYED or last.get("deployment_id") != args.deployment_id:
        raise SystemExit("%s is not consumed by %s" % (auth_id, args.deployment_id))
    if auth_id in chain:
        raise SystemExit("%s is already in the chain" % auth_id)
    previous = next(a for a in DA.list_authorizations()
                    if (a.get("status_history") or [{}])[-1].get("deployment_id") == auth["rollback_target"])
    prev_entry = chain[previous["authorization_id"]]
    drift = sorted(c["market_id"] for c in previous["release_contracts"]
                   if DA._sha256_file(Path(_DASH) / c["path"]) != c["sha256"])
    if drift != sorted(prev_entry.get("moved_by_later_work") or {}):
        raise SystemExit("drift under %s is %s but the chain lists %s" % (previous["authorization_id"], drift,
                                                                          list(prev_entry.get("moved_by_later_work") or {})))
    if "Historical." not in prev_entry["note"]:
        prev_entry["note"] = (prev_entry["note"].replace("The CURRENT live authorization.",
                                                         "Was the current live authorization.", 1)
                              + " Historical. It was the current live authorization until deploy %s published "
                                "fort-myers-fl as the forty-sixth market (authorization %s, %s), which this chain "
                                "records as the new CURRENT entry." % (args.deployment_id, auth_id, WORK_ORDER))
    mine = sorted(c["market_id"] for c in auth["release_contracts"]
                  if DA._sha256_file(Path(_DASH) / c["path"]) != c["sha256"])
    if mine:
        raise SystemExit("release-contract drift under the new authorization: %s" % mine)
    chain[auth_id] = OrderedDict((
        ("work_order", AUTHORIZING_ORDER), ("moved_by_later_work", OrderedDict()),
        ("note", "The CURRENT live authorization. It binds all %d release contracts exactly, because production was "
                 "authorized against what source holds and no application order has moved a market since. Registered "
                 "with an EMPTY moved list rather than left unregistered: an unregistered authorization binds "
                 "everything by default, so the two read alike today, and only the explicit entry says that emptiness "
                 "was checked. fort-myers-fl was built from zero by PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001, "
                 "registered by PTF-FORT-MYERS-FL-REGISTRATION-AND-STAGING-002 as COMPOSITE_FRESH_MARKET_DATA_ONLY "
                 "(automatic base and classification, FAST 15/15, 0 broad regression runs), founder-authorized by %s "
                 "(bound to %s) and deployed ONCE by %s. This is the market's FIRST authorization and FIRST "
                 "deployment: nothing was superseded."
                 % (len(auth["release_contracts"]), AUTHORIZING_ORDER, FOUNDER_BINDING_COMMIT, WORK_ORDER)),
    ))
    doc["reviewed_by"] = WORK_ORDER
    print("previous CURRENT:", previous["authorization_id"], "| moved", drift)
    print("new CURRENT     :", auth_id)
    if args.write:
        _dump(SUPERSESSIONS, doc)
    return 0


# --------------------------------------------------------------------------- pin

def pin(args):
    rec = _load(DA.record_path("ptf-deploy-fort-myers-004-%s" % args.deployment_id))
    manifest = _load(MANIFEST)
    state = _load(DEPLOYMENT_STATE)
    previous_record = state["live"]["deployment_record_id"]
    state["reviewed_by"] = WORK_ORDER
    state["live"] = OrderedDict([
        ("deploy_id", rec["deployment_id"]), ("deployed_by", WORK_ORDER),
        ("authorization_id", rec["authorization_id"]), ("deployment_record_id", rec["deployment_record_id"]),
        ("previous_deploy_id", rec["previous_deployment_id"]), ("source_commit", rec["source_commit"]),
        ("bundle_sha256", rec["bundle_sha256"]), ("sitemap_sha256", rec["sitemap_sha256"]),
        ("participating_markets", rec["participating_markets"]), ("profile_counts", rec["profile_counts"]),
        ("total_profiles", rec["total_profiles"]), ("sitemap_route_count", rec["sitemap_route_count"]),
        ("total_html_pages", manifest["total_html_pages"]), ("total_files", manifest["total_files"]),
        ("rollback_target", rec["previous_deployment_id"]),
        ("note", "Fort Myers / Cape Coral / Sanibel, Florida joined as the FORTY-SIXTH market at 57 published "
                 "pet-friendly profiles, all in Lee County (Fort Myers 34, Bonita Springs 6, Cape Coral 4, Estero 4, "
                 "Fort Myers Beach 4, Captiva 3, North Fort Myers 2), every one currently open, over 4 publishing "
                 "corridors, on package %s (founder-authorized by %s, bound to commit %s). The exact authorized "
                 "artifact was deployed with no rebuild; every unpublished census row -- Comfort Suites and MainStay "
                 "at 9455 Old Luckett, the Quality Inn at 4760 S Cleveland, the Latitude 26 rows, Pink Shell and "
                 "Edison Beach House among them -- returns 404, and every live profile is byte-identical to the "
                 "artifact and states its own municipality and postal code with no Naples / Collier premises. "
                 "Rollback is the deployment Fort Myers replaced (Salt Lake City, 45 markets)."
                 % (AUTHORIZED_PACKAGE_ID, AUTHORIZING_ORDER, FOUNDER_BINDING_COMMIT)),
        ("rollback_record", "%s.json" % previous_record),
    ])
    state["source"] = OrderedDict([
        ("ahead_of_production", False), ("moved_by", None),
        ("bundle_sha256", manifest["bundle_sha256"]), ("sitemap_sha256", manifest["sitemap_sha256"]),
        ("participating_markets", manifest["participating_markets"]),
        ("profile_counts", OrderedDict(sorted(rec["profile_counts"].items()))),
        ("total_profiles", manifest["total_published_profiles"]),
        ("sitemap_route_count", manifest["sitemap_route_count"]),
        ("total_html_pages", manifest["total_html_pages"]), ("total_files", manifest["total_files"]),
    ])
    bad = [k for k in ("bundle_sha256", "sitemap_sha256", "total_profiles", "sitemap_route_count",
                       "total_html_pages", "total_files") if state["live"][k] != state["source"][k]]
    if bad or state["live"]["source_commit"] != manifest["source_commit"]:
        raise SystemExit("live and source disagree after a deploy of the source's own bytes: %r / source_commit %s vs %s"
                         % (bad, state["live"]["source_commit"], manifest["source_commit"]))
    print("pin ->", rec["deployment_id"], rec["total_profiles"], rec["sitemap_route_count"])
    if args.write:
        _dump(DEPLOYMENT_STATE, state)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("predeploy")
    p.add_argument("--candidate", default="C:/t/fm4a")
    p.add_argument("--site-info", required=True)
    p.add_argument("--write", action="store_true")
    w = sub.add_parser("write-manifest")
    w.add_argument("--candidate", default="C:/t/fm4a")
    w.add_argument("--write", action="store_true")
    v = sub.add_parser("verify-live")
    v.add_argument("--candidate", required=True)
    v.add_argument("--parent-sitemap", required=True)
    v.add_argument("--market-sweep", required=True)
    v.add_argument("--prior-sweep", required=True)
    v.add_argument("--host-state", required=True)
    v.add_argument("--deployment-id", required=True)
    v.add_argument("--write", action="store_true")
    for name in ("record", "supersessions", "pin"):
        s = sub.add_parser(name)
        s.add_argument("--deployment-id", required=True)
        s.add_argument("--candidate", default="C:/t/fm4a")
        s.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    return {"predeploy": predeploy, "write-manifest": write_manifest, "verify-live": verify_live, "record": record,
            "supersessions": supersessions, "pin": pin}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

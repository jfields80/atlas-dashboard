"""PTF-NEW-ORLEANS-LA-PRODUCTION-DEPLOYMENT-004 -- deploy the exact, already-built, founder-authorized New Orleans
candidate, then verify the HOST, record the deployment, extend the supersessions chain and move the pins. One
subcommand per step, each refusing unless the step before it holds (derived from Kansas City's 004 deployment module,
itself Minneapolis's, Portland's, Seattle's and San Antonio's, every structural check unchanged):

    predeploy      --candidate C:/t/nola4a --site-info <getSite json> [--write]
    write-manifest --candidate C:/t/nola4a [--write]
    verify-live    --candidate C:/t/nola4a --parent-sitemap ... --market-sweep ... --prior-sweep ...
                   --host-state ... --deployment-id ... [--write]
    record         --deployment-id ... [--write]
    supersessions  --deployment-id ... [--write]
    pin            --deployment-id ... [--write]

The ``netlify deploy`` call itself is run ONCE by hand between ``write-manifest`` and ``verify-live``; this module
never deploys.

THE AUTHORIZING ORDER AND THE DEPLOYING ORDER ARE DIFFERENT HERE. The authorization was written by
PTF-NEW-ORLEANS-LA-FOUNDER-LAUNCH-AUTHORIZATION-003; this order (004) consumes it. The record keeps the authorization's
own ``work_order`` (the AUTHORIZING order) and names this order as ``deployer.work_order``.

NEW ORLEANS' OWN LIVE CHECKS. On top of every unpublished census row: the founder's named held rows -- SpringHill
Suites and TownePlace Suites at 1600 Canal St, The Garden District Hotel, Maison DuBois, Maison Dupuy, the preopening
Fairmont and the closed Claiborne Mansion -- are listed explicitly and must 404 at both the census slug and the site
route; the timeshare identities and the private / venue rentals (The Syd, Castle Day, Compass Point), which the census
never admitted, must 404 and be named on no New Orleans page; every live New Orleans profile's own structured address
must state Louisiana, the municipality the census carries for it and its own postal code, and no page outside an
Orleans Parish code may say New Orleans; the municipality traps the source-ready order decided must be live exactly as
committed; and the Wyndham Garden name twin must be live exactly as proven -- the brand-bound Kenner hotel (4535
Williams Blvd, property code 46094) published, the held Metairie map-only row (6401 Veterans Memorial Blvd) named on no
New Orleans page.

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

WORK_ORDER = "PTF-NEW-ORLEANS-LA-PRODUCTION-DEPLOYMENT-004"
AUTHORIZING_ORDER = "PTF-NEW-ORLEANS-LA-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "new-orleans-la"
AUTHORIZATION_ID = "ptf-auth-new-orleans-003-af70e0aa8a64"
AUTHORIZED_PACKAGE_ID = "pkg-new-orleans-la-0e5fef6af3af8339"
HOST = "https://pettripfinder.com"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PREDEPLOY = os.path.join(REPORTS, "new_orleans_la_predeploy_004.json")
VERIFICATION = os.path.join(REPORTS, "new_orleans_la_live_verification_004.json")
ACCOUNTING = os.path.join(REPORTS, "new_orleans_la_launch_authorization_003.json")
READINESS = os.path.join(REPORTS, "new_orleans_la_authorization_readiness_002.json")
CANDIDATE_MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest_candidate_new_orleans_003.json")
SUPERSESSIONS = os.path.join(_DASH, "tests", "pettripfinder", "pins", "supersessions.json")
DEPLOYMENT_STATE = os.path.join(_DASH, "tests", "pettripfinder", "pins", "deployment_state.json")
MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json")
SPOT = ("kansas-city-mo", "minneapolis-mn", "portland-or", "seattle-wa", "san-antonio-tx", "austin-tx", "phoenix-az",
        "denver-co", "san-diego-ca", "jacksonville-fl", "west-palm-beach-fl", "fort-lauderdale-fl", "augusta-ga",
        "miami-fl", "tampa-fl", "orlando-fl")
#: the parent this order deploys over, and the candidate it deploys (markets, profiles, release-index, served)
PARENT_ACCOUNTING = (43, 4136, 4552, 4628)
CANDIDATE_ACCOUNTING = (44, 4240, 4663, 4740)
#: New Orleans' own (profiles, release-index routes, served routes)
MARKET_ACCOUNTING = (104, 111, 112)
#: the founder's named held rows (admitted census rows held in the partition), probed explicitly by name
FOUNDER_HELD_KEYS = (
    "springhill suites new orleans downtown canal street", "towneplace suites new orleans downtown canal street",
    "the garden district hotel", "maison dubois bed and breakfast", "maison dupuy hotel",
    "fairmont new orleans", "claiborne mansion")
#: the private / venue rentals the census refused on their own pages (held outside hotel inventory)
RENTAL_KEYS = ("the syd", "castle day", "compass point events")
#: identity_key -> (whether its profile must be LIVE, the municipality its page must state) -- the municipality traps
#: the source-ready order decided
FIXED_IDENTITIES = OrderedDict((
    ("residence inn by marriott new orleans elmwood", (True, "Elmwood")),
    ("holiday inn new orleans west bank tower", (True, "Gretna")),
    ("red roof inn new orleans westbank", (True, "Harvey")),
    ("wyndham garden new orleans airport", (True, "Kenner")),
    ("clarion hotel and suites new orleans airport", (False, "Metairie")),
    ("hilton new orleans airport", (False, "Kenner")),
    ("brent house hotel", (False, "Jefferson")),
))
#: profile pages by parish (from each row's own postal code) the authorized candidate carries
PAGES_BY_PARISH = {"Orleans": 79, "Jefferson": 24, "Plaquemines": 1}
#: THE WYNDHAM GARDEN NAME TWIN (bounded to this exact proven shape)
WYNDHAM_KEY = "wyndham garden new orleans airport"
WYNDHAM_PUBLISHED_STREET = "4535 Williams Blvd"
WYNDHAM_PUBLISHED_POSTAL = "70065"
WYNDHAM_PROPERTY_CODE = "46094"
WYNDHAM_HELD_MAP_STREET = "6401 Veterans Memorial"
_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")
_REGION = re.compile(r'"addressRegion":\s*"([A-Z]{2})"')
_POSTAL = re.compile(r'"postalCode":\s*"(\d{5})')
_CITY = re.compile(r'"addressLocality":\s*"([^"]+)"')

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
    return DA.load_authorization(AUTHORIZATION_ID)


def _held_outside_inventory():
    """The timeshare / vacation-ownership identities, the private / venue rentals and the military-restricted
    identities, read from the census by their own classification (never typed)."""
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    non = census.get("non_admitted") or ()
    timeshare = sorted({h["canonical_name"] for h in non if h["classification"] == "NON_LODGING"
                        and str(h.get("classification_reason")).startswith("TIMESHARE")})
    rentals = sorted({h["canonical_name"] for h in non if h["identity_key"] in RENTAL_KEYS})
    military = sorted({h["canonical_name"] for h in non
                       if str(h.get("classification_reason")).startswith("MILITARY_RESTRICTED")})
    return OrderedDict((("timeshare", timeshare), ("private_or_venue_rental", rentals),
                        ("military_restricted", military)))


# --------------------------------------------------------------------------- predeploy

def predeploy(args):
    """Everything the order requires BEFORE the deploy, on the exact prebuilt bytes; nothing is rebuilt."""
    from scripts.pettripfinder import fast_release_lane as FL
    problems = []
    auth = _authorization()
    bundle_manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    gd_manifest = GD.build_manifest(bundle_manifest)
    readiness = _load(READINESS)
    acct = _load(ACCOUNTING)

    # 1. the parent is still live
    live_idx, live_state, live_problems = RI.live_index()
    live_markets = [m for m, i in live_idx.markets.items() if i.participating]
    live_index_routes = sum(len(i.routes) for i in live_idx.markets.values() if i.participating)
    parent = OrderedDict((("deploy_id", live_state.deploy_id), ("markets", len(live_markets)),
                          ("profiles", live_idx.total_profiles), ("release_index_routes", live_index_routes),
                          ("served_routes", live_state.sitemap_route_count),
                          ("sitemap_sha256", live_state.sitemap_sha256), ("problems", live_problems)))
    if live_problems or live_state.deploy_id != auth["rollback_target"]:
        problems.append("live is %s (%s), not the authorized parent %s" % (live_state.deploy_id, live_problems,
                                                                         auth["rollback_target"]))
    if (len(live_markets), live_idx.total_profiles, live_index_routes, live_state.sitemap_route_count) \
            != PARENT_ACCOUNTING:
        problems.append("the parent's accounting moved: %s" % dict(parent))

    # 2. the authorization: exact, AUTHORIZED, unconsumed, deployable
    site_info = _load(args.site_info)
    binding = OrderedDict((
        ("authorization_id", auth["authorization_id"]), ("status", auth["authorization_status"]),
        ("deploy_id", auth.get("deploy_id")), ("market_in_authorization", MARKET in _market_ids(auth["participating_markets"])),
        ("readiness_package", readiness["the_digests_this_readiness_binds"]["sealed_package_id"]),
        ("package_named_in_authorization_source", AUTHORIZED_PACKAGE_ID in auth["authorization_source"]),
        ("bundle_sha256", auth["bundle_sha256"]), ("sitemap_sha256", auth["sitemap_sha256"]),
        ("rollback_target", auth["rollback_target"]), ("source_commit", auth["source_commit"]),
        ("total_files", auth["total_files"]), ("total_profiles", auth["total_profiles"]),
        ("sitemap_route_count", auth["sitemap_route_count"]), ("markets", len(auth["participating_markets"])),
    ))
    expected = OrderedDict((("status", DA.AUTHORIZED), ("deploy_id", None), ("market_in_authorization", True),
                            ("readiness_package", AUTHORIZED_PACKAGE_ID), ("package_named_in_authorization_source", True),
                            # the digests the committed candidate manifest carries (read, never typed): the
                            # authorization must bind exactly these
                            ("bundle_sha256", _load(CANDIDATE_MANIFEST)["bundle_sha256"]),
                            ("sitemap_sha256", _load(CANDIDATE_MANIFEST)["sitemap_sha256"]),
                            ("rollback_target", "6ac4dc8a39b0e7274828a32b"), ("total_files", 25580),
                            ("source_commit", _load(CANDIDATE_MANIFEST)["source_commit"]),
                            ("total_profiles", CANDIDATE_ACCOUNTING[1]),
                            ("sitemap_route_count", CANDIDATE_ACCOUNTING[3]), ("markets", CANDIDATE_ACCOUNTING[0])))
    wrong = OrderedDict((k, (binding[k], v)) for k, v in expected.items() if binding[k] != v)
    if wrong:
        problems.append("the authorization does not bind what the order names: %s" % dict(wrong))
    if not auth["source_commit"].startswith("4c7e7b90"):
        problems.append("the authorization's source commit is %s, not the founder-decision BUILD commit 4c7e7b90"
                        % auth["source_commit"])
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
    candidate_manifest_bytes_equal = GD.build_manifest(bundle_manifest) == _load(CANDIDATE_MANIFEST)
    if not candidate_manifest_bytes_equal:
        problems.append("the committed candidate manifest no longer describes the bundle on disk")

    # 4-9. the accounting the authorization order wrote, re-read: delta, held content, municipalities, the Wyndham
    # name twin, reader / fee safety, collisions, determinism
    ident = acct["identity_safety"]
    muni = ident["MUNICIPALITY_PAGES"]
    twin = ident["WYNDHAM_GARDEN_NAME_TWIN"]
    outside = acct["timeshare_rental_and_military_safety"]
    collide = acct["cross_market_collision_safety"]
    gates = OrderedDict((
        ("ALL_ACCOUNTING_GATES", acct["ALL_ACCOUNTING_GATES"]),
        ("determinism", acct["candidate_determinism"]["result"]),
        ("files_compared", acct["candidate_determinism"]["files_compared"]),
        ("files_differing", acct["candidate_determinism"]["files_differing"]),
        ("unapproved_profiles", acct["hold_safety"]["unapproved_profiles_in_candidate"]),
        ("held_groups", OrderedDict((k, v["published"]) for k, v in ident["groups"].items())),
        ("held_group_rows", OrderedDict((k, v["rows"]) for k, v in ident["groups"].items())),
        ("timeshare_published", outside["TIMESHARE_PROFILES_PUBLISHED"]),
        ("rentals_published", outside["PRIVATE_OR_VENUE_RENTALS_PUBLISHED"]),
        ("military_published", outside["MILITARY_RESTRICTED_PROFILES_PUBLISHED"]),
        ("municipality_pages", OrderedDict((k, muni[k]) for k in (
            "profile_pages_checked", "profile_pages_by_parish", "WRONG_STATE_CITY_OR_ZIP_PAGES",
            "OTHER_MARKET_TEXT_PAGES"))),
        ("fixed_identities_correct", all(v["correct"] for v in muni["fixed_identities"].values())),
        ("wyndham_name_twin", OrderedDict((k, twin[k]) for k in (
            "published_street", "published_postal_code", "published_city", "published_property_code",
            "KENNER_PROPERTY_BOUND_TO_FIRST_PARTY_CODE", "built_page_states_kenner_building",
            "METAIRIE_MAP_ROW_PUBLISHED", "held_map_row_shape_exact", "CURRENT_CROSS_BUILDING_COLLISION"))),
        ("reader_safety", acct["reader_safety"]),
        ("misleading_single_fees", ident["fee_safety"]["misleading_single_fees_published"]),
        ("cross_market_collision_safe", collide["CROSS_MARKET_COLLISION_SAFE"]),
        ("bare_chain_collisions", collide["BARE_CHAIN_COLLISIONS"]),
        ("duplicate_excluded_identities", collide["duplicate_canonical_names"]),
        ("prior_files_removed", acct["byte_preservation"]["files_removed"]),
        ("prior_market_files_changed", len(acct["byte_preservation"]["prior_market_files_changed"])),
        ("changed_global_artifacts", acct["byte_preservation"]["changed_global_artifacts"]),
        ("unexpected_market_delta", acct["delta_safety"]["unexpected_market_delta"]),
        ("unexpected_profile_delta", acct["delta_safety"]["unexpected_profile_delta"]),
        ("unexpected_route_delta", acct["delta_safety"]["unexpected_route_delta"]),
        ("unexpected_served_route_delta", acct["delta_safety"]["unexpected_served_route_delta"]),
        ("parent_routes_preserved", acct["delta_safety"]["parent_routes_preserved"]),
        ("parent_markets_preserved", acct["delta_safety"]["parent_markets_preserved"]),
        ("parent_profiles_preserved", acct["delta_safety"]["parent_profiles_preserved"]),
        ("candidate", OrderedDict((k, acct["candidate_bundle"][k]) for k in (
            "bundle_sha256", "sitemap_sha256", "markets", "profiles", "release_index_routes", "served_sitemap_routes"))),
        ("new_orleans", OrderedDict((k, acct["new_orleans"][k]) for k in (
            "hotel_routes", "release_index_routes", "served_routes"))),
    ))
    bad = []
    if gates["ALL_ACCOUNTING_GATES"] != "PASS" or gates["determinism"] != "BYTE_IDENTICAL" \
            or gates["files_differing"] or gates["files_compared"] != 25580:
        bad.append("accounting / determinism")
    if gates["unapproved_profiles"] or any(gates["held_groups"].values()) or gates["timeshare_published"] \
            or gates["rentals_published"] or gates["military_published"] or any(gates["reader_safety"].values()) \
            or gates["misleading_single_fees"] \
            or gates["held_group_rows"].get("all_unresolved_rows") != 179 \
            or gates["held_group_rows"].get("verified_no_pets_rows") != 64:
        bad.append("held content / reader / fee safety")
    if gates["municipality_pages"]["WRONG_STATE_CITY_OR_ZIP_PAGES"] or gates["municipality_pages"]["OTHER_MARKET_TEXT_PAGES"] \
            or gates["municipality_pages"]["profile_pages_checked"] != MARKET_ACCOUNTING[0] \
            or dict(gates["municipality_pages"]["profile_pages_by_parish"]) != PAGES_BY_PARISH \
            or not gates["fixed_identities_correct"]:
        bad.append("municipality safety")
    w = gates["wyndham_name_twin"]
    if w["METAIRIE_MAP_ROW_PUBLISHED"] or w["CURRENT_CROSS_BUILDING_COLLISION"] \
            or not w["KENNER_PROPERTY_BOUND_TO_FIRST_PARTY_CODE"] or not w["built_page_states_kenner_building"] \
            or not w["held_map_row_shape_exact"] or w["published_property_code"] != WYNDHAM_PROPERTY_CODE:
        bad.append("Wyndham Garden name twin")
    if gates["cross_market_collision_safe"] != "PASS" or gates["bare_chain_collisions"] \
            or gates["duplicate_excluded_identities"]:
        bad.append("collision safety")
    if gates["prior_files_removed"] or gates["prior_market_files_changed"] \
            or gates["changed_global_artifacts"] != ["sitemap.xml"] \
            or gates["unexpected_market_delta"] or gates["unexpected_profile_delta"] \
            or gates["unexpected_route_delta"] or gates["unexpected_served_route_delta"] \
            or not (gates["parent_routes_preserved"] and gates["parent_markets_preserved"]
                    and gates["parent_profiles_preserved"]):
        bad.append("delta safety")
    if (gates["candidate"]["markets"], gates["candidate"]["profiles"], gates["candidate"]["release_index_routes"],
            gates["candidate"]["served_sitemap_routes"]) != CANDIDATE_ACCOUNTING \
            or (gates["new_orleans"]["hotel_routes"], gates["new_orleans"]["release_index_routes"],
                gates["new_orleans"]["served_routes"]) != MARKET_ACCOUNTING \
            or gates["candidate"]["bundle_sha256"] != auth["bundle_sha256"] \
            or gates["candidate"]["sitemap_sha256"] != auth["sitemap_sha256"]:
        bad.append("candidate accounting")
    if bad:
        problems.append("authorization-order accounting does not hold: %s" % bad)

    # 13 (pre). the FAST receipt the registration selected is still eligible
    package = _load(os.path.join(PKG, "markets", "packages", MARKET, "%s.json" % AUTHORIZED_PACKAGE_ID))
    receipts = FL.eligible_receipts(MARKET, package["package_digest"])
    receipt = _load(str(receipts[-1])) if receipts else {}
    j = ((receipt.get("RESULTS") or {}).get("J") or {})
    k = ((receipt.get("RESULTS") or {}).get("K") or {})
    fast = OrderedDict((("selected", os.path.basename(str(receipts[-1])) if receipts else None),
                        ("rule_J", j.get("status")), ("rule_K", k.get("status")),
                        ("rule_K_result", (k.get("detail") or {}).get("result")),
                        ("defects", FL.receipt_output_defects(receipt) if receipt else ["no receipt"])))
    if not receipts or fast["rule_J"] != "PASS" or fast["rule_K"] != "PASS" or fast["defects"]:
        problems.append("the FAST receipt is not currently eligible: %s" % dict(fast))

    report = OrderedDict((
        ("schema", "ptf-predeploy-verification/1.0"), ("work_order", WORK_ORDER),
        ("authorizing_work_order", AUTHORIZING_ORDER), ("market_id", MARKET),
        ("parent", parent),
        ("host_site", OrderedDict((("name", site_info.get("name")), ("ssl_url", site_info.get("ssl_url")),
                                   ("published_deploy", (site_info.get("published_deploy") or {}).get("id")),
                                   ("state", (site_info.get("published_deploy") or {}).get("state"))))),
        ("authorization", binding), ("verify_authorization", verify), ("deployability_problems", deployability),
        ("verify_target", target), ("verify_bundle_directory", directory),
        ("candidate_manifest_matches_bundle_on_disk", candidate_manifest_bytes_equal),
        ("authorization_order_accounting", gates), ("fast_receipt", fast),
        ("problems", problems), ("PREDEPLOY", "PASS" if not problems else "FAIL"),
    ))
    print(json.dumps(OrderedDict((k2, report[k2]) for k2 in (
        "parent", "host_site", "verify_authorization", "deployability_problems", "verify_target",
        "verify_bundle_directory", "fast_receipt", "problems", "PREDEPLOY")), indent=1))
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

def verify_live(args):
    from scripts.pettripfinder.markets.contract import parse_market
    problems = []
    auth = _authorization()
    manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    cand_routes = _routes(os.path.join(args.candidate, "site", "sitemap.xml"))
    parent_routes = _routes(args.parent_sitemap)
    served = _curl(HOST + "/sitemap.xml")
    live_sitemap_sha = hashlib.sha256(served).hexdigest()
    host_match = live_sitemap_sha == manifest["sitemap_sha256"]
    if not host_match:
        problems.append("the served sitemap %s is not the authorized %s" % (live_sitemap_sha, manifest["sitemap_sha256"]))
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
    mine_live = sorted(r for r in live_routes if "/%s/" % MARKET in r)
    fragments = manifest["fragments"]
    markets_live = sorted(m for m, f in fragments.items() if (f.get("hub_route") or "") in live_routes
                          or any(r in live_routes for r in (f.get("hotel_routes") or [])[:1]))

    my_rows = _status_rows(args.market_sweep)
    my_not_200 = [(c, r) for c, r in my_rows if c != "200"]
    if {r.strip() for _c, r in my_rows} != set(mine_live):
        problems.append("the %s sweep covered %d routes, %d are served" % (MARKET, len(my_rows), len(mine_live)))
    if my_not_200:
        problems.append("%s routes not 200: %d" % (MARKET, len(my_not_200)))
    prior_rows = _status_rows(args.prior_sweep)
    prior_bad = [(c, r) for c, r in prior_rows if c != "200"]
    if {r.strip() for _c, r in prior_rows} != parent_routes:
        problems.append("the prior sweep covered %d of %d parent routes" % (len(prior_rows), len(parent_routes)))
    if prior_bad:
        problems.append("prior routes not 200: %d" % len(prior_bad))

    mine = fragments[MARKET]
    sample_rel = ["index.html", "pet-friendly-hotels/index.html", "robots.txt", "llms.txt",
                  mine["hub_route"].strip("/") + "/index.html", mine["comparison_route"].strip("/") + "/index.html"]
    sample_rel += [r.strip("/") + "/index.html" for r in mine["corridor_routes"][:3]]
    sample_rel += [r.strip("/") + "/index.html" for r in mine["hotel_routes"][:6]]
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

    # every UNPUBLISHED census row (69 held + 60 verified-no-pets): the census slug AND the route the site forms
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    partition = _load(os.path.join(PKG, "new_orleans_la_final_partition_001.json"))
    cfg = parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET)), source=MARKET)
    hotel = {h["identity_key"]: h for h in census["hotels"]}
    held = [i for i in partition["items"] if i["final_state"] != "PUBLISHED_PET_FRIENDLY"]
    held_codes, held_live = OrderedDict(), []
    for item in held:
        h = hotel.get(item["identity_key"]) or {}
        urls = {RI.hotel_route(cfg, item.get("canonical_name") or h.get("canonical_name") or item["identity_key"])}
        slug = h.get("slug") or re.sub(r"[^a-z0-9]+", "-", item["identity_key"]).strip("-")
        urls.add("/pet-friendly-hotels/%s/%s/" % (MARKET, slug))
        codes = OrderedDict((u, _code(HOST + u)) for u in sorted(urls))
        held_codes[item["identity_key"]] = codes
        if any(c == "200" for c in codes.values()):
            held_live.append(item["identity_key"])
    not_404 = [k for k, cs in held_codes.items() if any(c != "404" for c in cs.values())]
    if held_live:
        problems.append("HELD identities are LIVE: %s" % held_live[:5])
    # the founder's named held rows, listed explicitly: each is a HELD partition row, and every URL must 404
    founder_codes = OrderedDict((k, held_codes.get(k)) for k in FOUNDER_HELD_KEYS)
    founder_not_404 = [k for k, cs in founder_codes.items() if not cs or any(c != "404" for c in cs.values())]
    if founder_not_404:
        problems.append("founder-held rows are not safely unpublished: %s" % founder_not_404)
    # New Orleans' own text pages (hub, comparison, corridors), fetched once: the Wyndham twin and the
    # held-outside-inventory checks read them
    text_pages = [mine["hub_route"], mine["comparison_route"]] + list(mine["corridor_routes"])
    nola_text = OrderedDict((p, _curl(HOST + p).decode("utf-8", "replace")) for p in text_pages)
    # every live New Orleans profile's own structured address states Louisiana, the municipality the census carries
    # for it and its own postal code; no page outside an Orleans Parish code says New Orleans
    from scripts.pettripfinder import new_orleans_la_geography_001 as GEO
    pf_keys = {h.get("identity_key") or h.get("key")
               for h in _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    muni_rows, by_parish, profile_text = OrderedDict(), Counter(), OrderedDict()
    for k in sorted(pf_keys):
        h = hotel.get(k) or {}
        route = RI.hotel_route(cfg, h.get("canonical_name") or k)
        body = _curl(HOST + route).decode("utf-8", "replace")
        profile_text[k] = body
        parish = (GEO.POSTAL_PARISH.get(str(h.get("postal_code"))[:5]) or ("",))[0]
        by_parish[parish] += 1
        regions, postals, cities = set(_REGION.findall(body)), set(_POSTAL.findall(body)), set(_CITY.findall(body))
        wrong_city = parish != "Orleans" and any(GEO.normalise_municipality(c) == "new orleans" for c in cities)
        ok = route in live_routes and regions == {"LA"} and postals == {str(h.get("postal_code"))[:5]} \
            and cities == {h.get("city")} and not wrong_city
        muni_rows[k] = OrderedDict((("route", route), ("postal_code", h.get("postal_code")), ("city", h.get("city")),
                                    ("parish", parish), ("page_region", sorted(regions)),
                                    ("page_postal", sorted(postals)), ("page_city", sorted(cities)),
                                    ("new_orleans_outside_orleans_parish", wrong_city),
                                    ("municipality_zip_live", ok)))
    muni_wrong = [k for k, v in muni_rows.items() if not v["municipality_zip_live"]]
    wrong_city_live = [k for k, v in muni_rows.items() if v["new_orleans_outside_orleans_parish"]]
    if muni_wrong or dict(by_parish) != PAGES_BY_PARISH or len(muni_rows) != MARKET_ACCOUNTING[0]:
        problems.append("New Orleans profiles without their own municipality / ZIP live: %s (by parish %s)"
                        % (muni_wrong[:5], dict(by_parish)))
    # the municipality traps the source-ready order decided, live exactly as committed
    fixed_live = OrderedDict()
    for k, (should_be_live, municipality) in FIXED_IDENTITIES.items():
        h = hotel.get(k) or {}
        route = RI.hotel_route(cfg, h.get("canonical_name") or k)
        code = _code(HOST + route)
        page_city = sorted(set(_CITY.findall(profile_text.get(k, "")))) if should_be_live else []
        fixed_live[k] = OrderedDict((("route", route), ("postal_code", h.get("postal_code")), ("city", h.get("city")),
                                     ("code", code), ("expected", "200" if should_be_live else "404"),
                                     ("page_city", page_city),
                                     ("correct", bool(h) and h.get("city") == municipality
                                      and code == ("200" if should_be_live else "404")
                                      and (not should_be_live or page_city == [municipality]))))
    fixed_wrong = [k for k, v in fixed_live.items() if not v["correct"]]
    if fixed_wrong:
        problems.append("fixed identities are not live as committed: %s" % fixed_wrong)
    # THE WYNDHAM GARDEN NAME TWIN, exactly as proven: the brand-bound Kenner hotel is live and states its own
    # building; the held Metairie map-only row is named on NO New Orleans page (all served New Orleans pages scanned)
    wy = hotel.get(WYNDHAM_KEY) or {}
    wy_route = RI.hotel_route(cfg, wy.get("canonical_name") or WYNDHAM_KEY)
    wy_text = profile_text.get(WYNDHAM_KEY, "")
    held_twin = [h for h in census.get("non_admitted") or () if h["identity_key"] == WYNDHAM_KEY]
    scanned = list(profile_text.values()) + list(nola_text.values())
    metairie_live = sum(1 for body in scanned if WYNDHAM_HELD_MAP_STREET in body)
    twin = OrderedDict((
        ("published_route", wy_route), ("published_route_code", _code(HOST + wy_route)),
        ("published_street", wy.get("street")), ("published_postal_code", wy.get("postal_code")),
        ("published_city", wy.get("city")), ("published_property_code", wy.get("property_code")),
        ("KENNER_PROPERTY_BOUND_TO_FIRST_PARTY_CODE",
         wy.get("property_code") == WYNDHAM_PROPERTY_CODE and wy.get("street") == WYNDHAM_PUBLISHED_STREET
         and wy.get("postal_code") == WYNDHAM_PUBLISHED_POSTAL
         and any(str(l).startswith("PROPERTY_PAGE") for l in wy.get("lanes") or ())),
        ("live_page_states_kenner_building", WYNDHAM_PUBLISHED_STREET in wy_text and WYNDHAM_PUBLISHED_POSTAL in wy_text
         and set(_CITY.findall(wy_text)) == {"Kenner"}),
        ("held_map_rows", [OrderedDict((("street", h.get("street")), ("postal_code", h.get("postal_code")),
                                        ("city", h.get("city")), ("classification", h.get("classification")),
                                        ("lanes", h.get("lanes")))) for h in held_twin]),
        ("held_map_row_shape_exact", len(held_twin) == 1 and held_twin[0].get("classification") == "IDENTITY_REVIEW_REQUIRED"
         and set(held_twin[0].get("lanes") or ()) == {"OSM_OVERPASS"}
         and str(held_twin[0].get("street") or "").startswith(WYNDHAM_HELD_MAP_STREET)
         and held_twin[0].get("postal_code") == "70003"),
        ("new_orleans_pages_scanned", len(scanned)),
        ("METAIRIE_MAP_TWIN_PUBLISHED", metairie_live),
    ))
    twin["CURRENT_CROSS_BUILDING_COLLISION"] = 0 if (
        twin["KENNER_PROPERTY_BOUND_TO_FIRST_PARTY_CODE"] and twin["live_page_states_kenner_building"]
        and twin["published_route_code"] == "200" and not metairie_live and twin["held_map_row_shape_exact"]
        and len(scanned) == MARKET_ACCOUNTING[2]) else 1
    if twin["CURRENT_CROSS_BUILDING_COLLISION"]:
        problems.append("Wyndham Garden name twin: %s" % json.dumps(twin))
    held_states = OrderedDict()
    for item in held:
        held_states[item["final_state"]] = held_states.get(item["final_state"], 0) + 1

    # timeshare / vacation-ownership identities, private / venue rentals and military-restricted identities: no
    # route, not named on New Orleans' pages
    page_text = nola_text
    outside, outside_ok = OrderedDict(), True
    for cls, names in _held_outside_inventory().items():
        rows = OrderedDict()
        for name in names:
            route = RI.hotel_route(cfg, name)
            code = _code(HOST + route)
            hits = [p for p, body in page_text.items() if name in body or name.replace("&", "&amp;") in body]
            ok = code == "404" and route not in live_routes and not hits
            outside_ok = outside_ok and ok
            rows[name] = OrderedDict((("route", route), ("code", code), ("page_text_hits", hits), ("absent", ok)))
        outside[cls] = rows
    if not outside_ok:
        problems.append("a timeshare / rental / military-restricted identity is visible: %s"
                        % [n for c in outside.values() for n, v in c.items() if not v["absent"]])

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
        ("every_new_orleans_route_200", bool(my_rows) and not my_not_200 and len(my_rows) == MARKET_ACCOUNTING[2]),
        ("no_parent_route_lost", not lost),
        ("every_prior_route_200", bool(prior_rows) and not prior_bad and len(prior_rows) == len(parent_routes)),
        ("only_new_orleans_added", not added_not_mine),
        ("served_bytes_are_authorized_bytes", not byte_mismatch),
        ("every_unpublished_identity_404", not held_live and not not_404),
        ("timeshare_rentals_and_military_absent", outside_ok),
        ("founder_held_rows_unpublished", not founder_not_404),
        ("municipality_identity_live", not muni_wrong and not wrong_city_live
         and len(muni_rows) == MARKET_ACCOUNTING[0] and dict(by_parish) == PAGES_BY_PARISH),
        ("fixed_identities_live_as_committed", not fixed_wrong),
        ("wyndham_name_twin_live_as_proven", not twin["CURRENT_CROSS_BUILDING_COLLISION"]),
        ("detroit_withheld", spot["detroit-must-be-absent"] == 404),
        ("spot_markets_200", all(c == 200 for m, c in spot.items() if m != "detroit-must-be-absent")),
        ("host_publishes_this_deploy", host["published_deploy_id"] == args.deployment_id and host["state"] == "ready"),
        ("host_previous_deploy_is_the_parent", host["previous_deploy_id"] == auth["rollback_target"]),
        ("bundle_quality_zero", not any(quality.values())),
        ("live_accounting_44_4240_4663_4740",
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
                                 ("added_routes", len(added)), ("added_routes_not_new_orleans", added_not_mine)))),
        ("new_orleans", OrderedDict((
            ("hotel_routes", len(mine["hotel_routes"])), ("corridor_routes", len(mine["corridor_routes"])),
            ("hub_routes", 1), ("comparison_route", mine["comparison_route"]),
            ("release_index_routes", len(mine["hotel_routes"]) + len(mine["corridor_routes"]) + 1),
            ("expected_served_routes_from_authorized_candidate", len([r for r in cand_routes if "/%s/" % MARKET in r])),
            ("served_routes_in_live_sitemap", len(mine_live)), ("routes_swept", len(my_rows)),
            ("routes_http_200", len(my_rows) - len(my_not_200)), ("routes_missing", [r for _c, r in my_not_200]),
            ("corridors", sorted(r.rstrip("/").split("/")[-1] for r in mine["corridor_routes"])),
        ))),
        ("holds", OrderedDict((
            ("census_rows", len(partition["items"])),
            ("published", len(partition["items"]) - len(held)),
            ("unpublished_census_rows", len(held)), ("unpublished_by_final_state", held_states),
            ("urls_probed", sum(len(c) for c in held_codes.values())),
            ("unpublished_not_404", not_404), ("unpublished_live", held_live),
            ("note", "EVERY unpublished census row (179 held -- including SpringHill Suites and TownePlace Suites at "
                     "1600 Canal St, The Garden District Hotel, Maison DuBois, Maison Dupuy, the preopening Fairmont "
                     "and the closed Claiborne Mansion -- plus 64 verified-no-pets) probed at its census slug and at "
                     "the route the site forms from its name; each must 404."),
        ))),
        ("founder_held_rows", OrderedDict((("rows", len(founder_codes)), ("codes", founder_codes),
                                           ("not_404", founder_not_404)))),
        ("municipality_identity", OrderedDict((("profiles_checked", len(muni_rows)),
                                               ("profiles_by_parish", OrderedDict(sorted(by_parish.items()))),
                                               ("profiles_by_municipality", OrderedDict(sorted(Counter(
                                                   v["city"] for v in muni_rows.values()).items()))),
                                               ("NEW_ORLEANS_WRONG_CITY_IDENTITIES_LIVE", len(wrong_city_live)),
                                               ("WRONG_STATE_MUNICIPALITY_OR_ZIP_PROFILES_LIVE", len(muni_wrong)),
                                               ("wrong", muni_wrong), ("profiles", muni_rows)))),
        ("fixed_identities_live", fixed_live),
        ("wyndham_name_twin", twin),
        ("held_outside_inventory", outside),
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
    print("held probed %d rows / %d urls; bytes %d/%d" % (len(held_codes), report["holds"]["urls_probed"],
                                                         report["byte_identity"]["pages_byte_identical_to_artifact"],
                                                         len(byte_checks)))
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
    mine, holds, sitemap, prior = live["new_orleans"], live["holds"], live["sitemap"], live["prior_routes"]
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
        ("new_orleans_release_index_routes", mine["release_index_routes"]),
        ("new_orleans_served_routes", mine["served_routes_in_live_sitemap"]),
        ("new_orleans_routes_fetched_200", mine["routes_http_200"]),
        ("new_orleans_routes_missing", len(mine["routes_missing"])),
        ("new_orleans_corridors_live", mine["corridors"]),
        ("pages_byte_identical_to_artifact", "%d/%d" % (live["byte_identity"]["pages_byte_identical_to_artifact"],
                                                        live["byte_identity"]["pages_compared"])),
        ("holds_unpublished", OrderedDict([(k, holds[k]) for k in ("census_rows", "published", "unpublished_census_rows",
                                                                   "unpublished_by_final_state", "urls_probed", "note")]
                                          + [("held_routes_not_404", len(holds["unpublished_not_404"])),
                                             ("identity_resolutions_ruling_written", False)])),
        ("timeshare_rentals_and_military_absent", live["checks"]["timeshare_rentals_and_military_absent"] == "PASS"),
        ("founder_held_rows_unpublished", live["checks"]["founder_held_rows_unpublished"] == "PASS"),
        ("municipality_profiles_checked", live["municipality_identity"]["profiles_checked"]),
        ("municipality_profiles_by_parish", live["municipality_identity"]["profiles_by_parish"]),
        ("new_orleans_wrong_city_identities_live", live["municipality_identity"]["NEW_ORLEANS_WRONG_CITY_IDENTITIES_LIVE"]),
        ("wrong_state_municipality_or_zip_profiles_live",
         live["municipality_identity"]["WRONG_STATE_MUNICIPALITY_OR_ZIP_PROFILES_LIVE"]),
        ("fixed_identities_live_as_committed", live["checks"]["fixed_identities_live_as_committed"] == "PASS"),
        ("wyndham_metairie_map_twin_published", live["wyndham_name_twin"]["METAIRIE_MAP_TWIN_PUBLISHED"]),
        ("wyndham_kenner_first_party_code", live["wyndham_name_twin"]["published_property_code"]),
        ("wyndham_current_cross_building_collision", live["wyndham_name_twin"]["CURRENT_CROSS_BUILDING_COLLISION"]),
        ("previously_live_markets_published_profiles_preserved", preserved),
        ("parent_served_routes", sitemap["parent_locs"]), ("parent_routes_refetched", prior["fetched"]),
        ("parent_routes_not_200", len(prior["not_200"])), ("prior_routes_lost", prior["prior_routes_lost"]),
        ("prior_profiles_lost", prior["prior_profiles_lost"]), ("prior_markets_lost", prior["prior_markets_lost"]),
        ("added_routes", sitemap["added_routes"]),
        ("added_routes_not_new_orleans", len(sitemap["added_routes_not_new_orleans"])),
        ("spot_checks", live["spot_checks"]), ("quality", live["quality"]),
        ("unexpected_market_changes", 0), ("unexpected_profile_changes", 0),
        ("unexpected_route_changes", len(sitemap["added_routes_not_new_orleans"]) + len(sitemap["parent_routes_missing"])),
        ("checks", live["checks"]),
        ("first_authorization_and_first_deployment_for_this_market", True),
        ("all_critical_checks_pass", True),
    ])
    rec = DA.build_deployment_record(
        auth, deployment_record_id="ptf-deploy-new-orleans-004-%s" % args.deployment_id,
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
             "route SET is identical to it; %d/%d parent routes refetched 200 with 0 lost; all %d New Orleans routes "
             "are live and %s sampled pages are byte-identical to the artifact; all %d unpublished census rows -- "
             "SpringHill Suites and TownePlace Suites at 1600 Canal St, The Garden District Hotel, Maison DuBois, Maison "
             "Dupuy, the preopening Fairmont and the closed Claiborne Mansion among them -- return 404, and the "
             "timeshare identities and private / venue rentals have no route; every live profile states Louisiana, "
             "its own municipality and postal code (79 Orleans, 24 Jefferson, 1 Plaquemines Parish; 0 written as New "
             "Orleans outside Orleans Parish); the Kenner Wyndham Garden (code 46094) is live and the Metairie "
             "map-only row is named nowhere; Detroit remains withheld."
             % (WORK_ORDER, args.deployment_id, prior["fetched"] - len(prior["not_200"]), prior["fetched"],
                mine["routes_http_200"], results["pages_byte_identical_to_artifact"], holds["unpublished_census_rows"]),
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
                                "new-orleans-la as the forty-fourth market (authorization %s, %s), which this chain "
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
                 "was checked. new-orleans-la was built from zero by PTF-NEW-ORLEANS-LA-HARDENED-SOURCE-READY-001, "
                 "registered by PTF-NEW-ORLEANS-LA-REGISTRATION-AND-STAGING-002 as COMPOSITE_FRESH_MARKET_DATA_ONLY (automatic base "
                 "and classification, FAST 15/15, 0 broad regression runs), founder-authorized by %s and deployed "
                 "ONCE by %s. This is the market's FIRST authorization and FIRST deployment: nothing was superseded."
                 % (len(auth["release_contracts"]), AUTHORIZING_ORDER, WORK_ORDER)),
    ))
    doc["reviewed_by"] = WORK_ORDER
    print("previous CURRENT:", previous["authorization_id"], "| moved", drift)
    print("new CURRENT     :", auth_id)
    if args.write:
        _dump(SUPERSESSIONS, doc)
    return 0


# --------------------------------------------------------------------------- pin

def pin(args):
    rec = _load(DA.record_path("ptf-deploy-new-orleans-004-%s" % args.deployment_id))
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
        ("note", "New Orleans / Greater New Orleans, Louisiana joined as the FORTY-FOURTH market and the first Louisiana "
                 "market, at 104 published pet-friendly profiles (79 Orleans, 24 Jefferson, 1 Plaquemines Parish) over "
                 "6 publishing corridors, on package pkg-new-orleans-la-0e5fef6af3af8339 (founder-authorized by %s, "
                 "bound to registration commit 85e7c13e). The exact authorized artifact was deployed with no rebuild; "
                 "every unpublished census row -- SpringHill Suites and TownePlace Suites at 1600 Canal St, The Garden "
                 "District Hotel, Maison DuBois, Maison Dupuy, the preopening Fairmont and the closed Claiborne Mansion "
                 "among them -- returns 404, every live profile states its own municipality and postal code, and the "
                 "Wyndham Garden name twin is live exactly as proven. Rollback is the deployment New Orleans replaced "
                 "(Kansas City, 43 markets)." % AUTHORIZING_ORDER),
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
    p.add_argument("--candidate", default="C:/t/nola4a")
    p.add_argument("--site-info", required=True)
    p.add_argument("--write", action="store_true")
    w = sub.add_parser("write-manifest")
    w.add_argument("--candidate", default="C:/t/nola4a")
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
        s.add_argument("--candidate", default="C:/t/nola4a")
        s.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    return {"predeploy": predeploy, "write-manifest": write_manifest, "verify-live": verify_live, "record": record,
            "supersessions": supersessions, "pin": pin}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

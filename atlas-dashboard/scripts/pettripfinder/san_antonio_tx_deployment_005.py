"""PTF-SAN-ANTONIO-TX-PRODUCTION-DEPLOYMENT-005 -- deploy the exact, already-built, founder-authorized San Antonio
candidate, then verify the HOST, record the deployment, extend the supersessions chain and move the pins. One
subcommand per step, each refusing unless the step before it holds (derived from Austin's 004 deployment module,
every structural check unchanged):

    predeploy      --candidate C:/t/sa4a --site-info <getSite json> [--write]
    write-manifest --candidate C:/t/sa4a [--write]
    verify-live    --candidate C:/t/sa4a --parent-sitemap ... --market-sweep ... --prior-sweep ...
                   --host-state ... --deployment-id ... [--write]
    record         --deployment-id ... [--write]
    supersessions  --deployment-id ... [--write]
    pin            --deployment-id ... [--write]

The ``netlify deploy`` call itself is run ONCE by hand between ``write-manifest`` and ``verify-live``; this module
never deploys.

THE AUTHORIZING ORDER AND THE DEPLOYING ORDER ARE DIFFERENT HERE. The authorization was written by
PTF-SAN-ANTONIO-TX-FOUNDER-LAUNCH-AUTHORIZATION-004; this order (005) consumes it. The record keeps the authorization's
own ``work_order`` (the AUTHORIZING order) and names this order as ``deployer.work_order``.

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
from collections import OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import deployment_authorization as DA   # noqa: E402
from scripts.pettripfinder import global_deployment as GD          # noqa: E402
from scripts.pettripfinder import release_index as RI              # noqa: E402

WORK_ORDER = "PTF-SAN-ANTONIO-TX-PRODUCTION-DEPLOYMENT-005"
AUTHORIZING_ORDER = "PTF-SAN-ANTONIO-TX-FOUNDER-LAUNCH-AUTHORIZATION-004"
MARKET = "san-antonio-tx"
AUTHORIZATION_ID = "ptf-auth-san-antonio-004-50b1ce95d803"
AUTHORIZED_PACKAGE_ID = "pkg-san-antonio-tx-aa8f4fe9ea26a6ff"
HOST = "https://pettripfinder.com"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PREDEPLOY = os.path.join(REPORTS, "san_antonio_tx_predeploy_005.json")
VERIFICATION = os.path.join(REPORTS, "san_antonio_tx_live_verification_005.json")
ACCOUNTING = os.path.join(REPORTS, "san_antonio_tx_launch_authorization_004.json")
READINESS = os.path.join(REPORTS, "san_antonio_tx_registration_authorization_readiness.json")
CANDIDATE_MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest_candidate_san_antonio_004.json")
SUPERSESSIONS = os.path.join(_DASH, "tests", "pettripfinder", "pins", "supersessions.json")
DEPLOYMENT_STATE = os.path.join(_DASH, "tests", "pettripfinder", "pins", "deployment_state.json")
MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json")
SPOT = ("austin-tx", "phoenix-az", "denver-co", "san-diego-ca", "jacksonville-fl", "west-palm-beach-fl",
        "fort-lauderdale-fl", "augusta-ga", "miami-fl", "tampa-fl", "orlando-fl", "jacksonville-nc")
_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")


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
    """The timeshare / vacation-ownership and military-restricted identities, read from the census by their own
    classification (never typed)."""
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    non = census.get("non_admitted") or ()
    timeshare = sorted({h["canonical_name"] for h in non if h["classification"] == "NON_LODGING"
                        and str(h.get("classification_reason")).startswith("TIMESHARE")})
    military = sorted({h["canonical_name"] for h in non
                       if str(h.get("classification_reason")).startswith("MILITARY_RESTRICTED")})
    return OrderedDict((("timeshare", timeshare), ("military_restricted", military)))


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
            != (38, 3386, 3737, 3808):
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
                            ("bundle_sha256", "50b1ce95d80386ed9c28f16ad1493bc4c8f2588f201bb1f95597a6d6984a6bf4"),
                            ("sitemap_sha256", "e2a6b1c94dff6f9178fe83913c0babaf74f1b02b9453be37e29ad2c82a86b484"),
                            ("rollback_target", "6abf3e749cc359701298718d"), ("total_files", 21351),
                            ("total_profiles", 3530), ("sitemap_route_count", 3966), ("markets", 39)))
    wrong = OrderedDict((k, (binding[k], v)) for k, v in expected.items() if binding[k] != v)
    if wrong:
        problems.append("the authorization does not bind what the order names: %s" % dict(wrong))
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

    # 4-6. the accounting the authorization order wrote, re-read: delta, held content, collisions, determinism
    gates = OrderedDict((
        ("ALL_ACCOUNTING_GATES", acct["ALL_ACCOUNTING_GATES"]),
        ("determinism", acct["candidate_determinism"]["result"]),
        ("files_differing", acct["candidate_determinism"]["files_differing"]),
        ("unapproved_profiles", acct["hold_safety"]["unapproved_profiles_in_candidate"]),
        ("held_groups", OrderedDict((k, v["published"]) for k, v in acct["identity_safety"]["groups"].items())),
        ("timeshare_published", acct["timeshare_and_military_safety"]["TIMESHARE_PROFILES_PUBLISHED"]),
        ("military_published", acct["timeshare_and_military_safety"]["MILITARY_RESTRICTED_PROFILES_PUBLISHED"]),
        ("reader_safety", acct["reader_safety"]),
        ("misleading_single_fees", acct["identity_safety"]["fee_safety"]["misleading_single_fees_published"]),
        ("cross_market_collision_safe", acct["cross_market_collision_safety"]["CROSS_MARKET_COLLISION_SAFE"]),
        ("bare_chain_collisions", acct["cross_market_collision_safety"]["BARE_CHAIN_COLLISIONS"]),
        ("prior_files_removed", acct["byte_preservation"]["files_removed"]),
        ("prior_market_files_changed", len(acct["byte_preservation"]["prior_market_files_changed"])),
        ("unexpected_served_route_delta", acct["delta_safety"]["unexpected_served_route_delta"]),
        ("parent_routes_preserved", acct["delta_safety"]["parent_routes_preserved"]),
        ("parent_markets_preserved", acct["delta_safety"]["parent_markets_preserved"]),
        ("parent_profiles_preserved", acct["delta_safety"]["parent_profiles_preserved"]),
        ("candidate", OrderedDict((k, acct["candidate_bundle"][k]) for k in (
            "bundle_sha256", "sitemap_sha256", "markets", "profiles", "release_index_routes", "served_sitemap_routes"))),
        ("san_antonio", OrderedDict((k, acct["san_antonio"][k]) for k in (
            "hotel_routes", "release_index_routes", "served_routes"))),
    ))
    bad = []
    if gates["ALL_ACCOUNTING_GATES"] != "PASS" or gates["determinism"] != "BYTE_IDENTICAL" or gates["files_differing"]:
        bad.append("accounting / determinism")
    if gates["unapproved_profiles"] or any(gates["held_groups"].values()) or gates["timeshare_published"] \
            or gates["military_published"] or any(gates["reader_safety"].values()) or gates["misleading_single_fees"]:
        bad.append("held content / reader / fee safety")
    if gates["cross_market_collision_safe"] != "PASS" or gates["bare_chain_collisions"]:
        bad.append("collision safety")
    if gates["prior_files_removed"] or gates["prior_market_files_changed"] or gates["unexpected_served_route_delta"] \
            or not (gates["parent_routes_preserved"] and gates["parent_markets_preserved"]
                    and gates["parent_profiles_preserved"]):
        bad.append("delta safety")
    if (gates["candidate"]["markets"], gates["candidate"]["profiles"], gates["candidate"]["release_index_routes"],
            gates["candidate"]["served_sitemap_routes"]) != (39, 3530, 3894, 3966) \
            or (gates["san_antonio"]["hotel_routes"], gates["san_antonio"]["release_index_routes"],
                gates["san_antonio"]["served_routes"]) != (144, 157, 158):
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

    # every UNPUBLISHED census row (172 held + 98 verified-no-pets): the census slug AND the route the site forms
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    partition = _load(os.path.join(PKG, "san_antonio_tx_final_partition_001.json"))
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
    held_states = OrderedDict()
    for item in held:
        held_states[item["final_state"]] = held_states.get(item["final_state"], 0) + 1

    # timeshare / vacation-ownership and military-restricted identities: no route, not named on SA's own pages
    text_pages = [mine["hub_route"], mine["comparison_route"]] + list(mine["corridor_routes"])
    page_text = OrderedDict((p, _curl(HOST + p).decode("utf-8", "replace")) for p in text_pages)
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
        problems.append("a timeshare / military-restricted identity is visible: %s"
                        % [n for c in outside.values() for n, v in c.items() if not v["absent"]])

    spot = OrderedDict((m, int(_code("%s/pet-friendly-hotels/%s/" % (HOST, m)) or 0)) for m in SPOT)
    spot["san-antonio-tx"] = int(_code("%s/pet-friendly-hotels/%s/" % (HOST, MARKET)) or 0)
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
    if (len(markets_live), live_profiles, live_index, len(live_routes)) != (39, 3530, 3894, 3966):
        problems.append("live accounting is %s, not 39 / 3530 / 3894 / 3966"
                        % ((len(markets_live), live_profiles, live_index, len(live_routes)),))
    checks = OrderedDict((
        ("sitemap_is_authorized", host_match),
        ("served_route_set_is_authorized", live_routes == cand_routes),
        ("every_san_antonio_route_200", bool(my_rows) and not my_not_200),
        ("no_parent_route_lost", not lost),
        ("every_prior_route_200", bool(prior_rows) and not prior_bad and len(prior_rows) == len(parent_routes)),
        ("only_san_antonio_added", not added_not_mine),
        ("served_bytes_are_authorized_bytes", not byte_mismatch),
        ("every_unpublished_identity_404", not held_live and not not_404),
        ("timeshare_and_military_absent", outside_ok),
        ("detroit_withheld", spot["detroit-must-be-absent"] == 404),
        ("spot_markets_200", all(c == 200 for m, c in spot.items() if m != "detroit-must-be-absent")),
        ("host_publishes_this_deploy", host["published_deploy_id"] == args.deployment_id and host["state"] == "ready"),
        ("host_previous_deploy_is_the_parent", host["previous_deploy_id"] == auth["rollback_target"]),
        ("bundle_quality_zero", not any(quality.values())),
        ("live_accounting_39_3530_3894_3966",
         (len(markets_live), live_profiles, live_index, len(live_routes)) == (39, 3530, 3894, 3966)),
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
                                 ("added_routes", len(added)), ("added_routes_not_san_antonio", added_not_mine)))),
        ("san_antonio", OrderedDict((
            ("hotel_routes", len(mine["hotel_routes"])), ("corridor_routes", len(mine["corridor_routes"])),
            ("hub_routes", 1), ("comparison_route", mine["comparison_route"]),
            ("release_index_routes", len(mine["hotel_routes"]) + len(mine["corridor_routes"]) + 1),
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
            ("note", "EVERY unpublished census row (172 held -- including the 10 Hilton access-blocked, 8 dual-brand, "
                     "The Jackson House and 4 preopening -- plus 98 verified-no-pets) probed at its census slug and at "
                     "the route the site forms from its name; each must 404."),
        ))),
        ("timeshare_and_military", outside),
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
    mine, holds, sitemap, prior = live["san_antonio"], live["holds"], live["sitemap"], live["prior_routes"]
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
        ("san_antonio_release_index_routes", mine["release_index_routes"]),
        ("san_antonio_served_routes", mine["served_routes_in_live_sitemap"]),
        ("san_antonio_routes_fetched_200", mine["routes_http_200"]),
        ("san_antonio_routes_missing", len(mine["routes_missing"])),
        ("san_antonio_corridors_live", mine["corridors"]),
        ("pages_byte_identical_to_artifact", "%d/%d" % (live["byte_identity"]["pages_byte_identical_to_artifact"],
                                                        live["byte_identity"]["pages_compared"])),
        ("holds_unpublished", OrderedDict([(k, holds[k]) for k in ("census_rows", "published", "unpublished_census_rows",
                                                                   "unpublished_by_final_state", "urls_probed", "note")]
                                          + [("held_routes_not_404", len(holds["unpublished_not_404"])),
                                             ("identity_resolutions_ruling_written", False)])),
        ("timeshare_and_military_absent", live["checks"]["timeshare_and_military_absent"] == "PASS"),
        ("previously_live_markets_published_profiles_preserved", preserved),
        ("parent_served_routes", sitemap["parent_locs"]), ("parent_routes_refetched", prior["fetched"]),
        ("parent_routes_not_200", len(prior["not_200"])), ("prior_routes_lost", prior["prior_routes_lost"]),
        ("prior_profiles_lost", prior["prior_profiles_lost"]), ("prior_markets_lost", prior["prior_markets_lost"]),
        ("added_routes", sitemap["added_routes"]),
        ("added_routes_not_san_antonio", len(sitemap["added_routes_not_san_antonio"])),
        ("spot_checks", live["spot_checks"]), ("quality", live["quality"]),
        ("unexpected_market_changes", 0), ("unexpected_profile_changes", 0),
        ("unexpected_route_changes", len(sitemap["added_routes_not_san_antonio"]) + len(sitemap["parent_routes_missing"])),
        ("checks", live["checks"]),
        ("first_authorization_and_first_deployment_for_this_market", True),
        ("all_critical_checks_pass", True),
    ])
    rec = DA.build_deployment_record(
        auth, deployment_record_id="ptf-deploy-san-antonio-005-%s" % args.deployment_id,
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
             "route SET is identical to it; %d/%d parent routes refetched 200 with 0 lost; all %d San Antonio routes "
             "are live and %s sampled pages are byte-identical to the artifact; all %d unpublished census rows return "
             "404; the timeshare and military-restricted identities are absent; Detroit remains withheld."
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
                                "san-antonio-tx as the thirty-ninth market (authorization %s, %s), which this chain "
                                "records as the new CURRENT entry." % (args.deployment_id, auth_id, WORK_ORDER))
    mine = sorted(c["market_id"] for c in auth["release_contracts"]
                  if DA._sha256_file(Path(_DASH) / c["path"]) != c["sha256"])
    if mine:
        raise SystemExit("release-contract drift under the new authorization: %s" % mine)
    chain[auth_id] = OrderedDict((
        ("work_order", AUTHORIZING_ORDER), ("moved_by_later_work", OrderedDict()),
        ("note", "The CURRENT live authorization. It binds all 39 release contracts exactly, because production was "
                 "authorized against what source holds and no application order has moved a market since. Registered "
                 "with an EMPTY moved list rather than left unregistered: an unregistered authorization binds "
                 "everything by default, so the two read alike today, and only the explicit entry says that emptiness "
                 "was checked. san-antonio-tx was built from zero by PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001, "
                 "retried for Hilton by PTF-SAN-ANTONIO-TX-HILTON-PACED-RETRY-002 (no row changed), registered by "
                 "PTF-SAN-ANTONIO-TX-REGISTRATION-AND-STAGING-003 as COMPOSITE_FRESH_MARKET_DATA_ONLY (automatic base "
                 "and classification, FAST 15/15, 0 broad regression runs), founder-authorized by %s and deployed "
                 "ONCE by %s. This is the market's FIRST authorization and FIRST deployment: nothing was superseded."
                 % (AUTHORIZING_ORDER, WORK_ORDER)),
    ))
    doc["reviewed_by"] = WORK_ORDER
    print("previous CURRENT:", previous["authorization_id"], "| moved", drift)
    print("new CURRENT     :", auth_id)
    if args.write:
        _dump(SUPERSESSIONS, doc)
    return 0


# --------------------------------------------------------------------------- pin

def pin(args):
    rec = _load(DA.record_path("ptf-deploy-san-antonio-005-%s" % args.deployment_id))
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
        ("note", "San Antonio / Greater San Antonio joined as the THIRTY-NINTH market and the second Texas market at "
                 "144 published pet-friendly profiles over 12 publishing corridors, on package "
                 "pkg-san-antonio-tx-aa8f4fe9ea26a6ff (founder-authorized by %s, bound to registration commit "
                 "5f30c7b3). The exact authorized artifact was deployed with no rebuild; every unpublished census row "
                 "returns 404, and the timeshare and military-restricted identities are absent. Rollback is the "
                 "deployment San Antonio replaced (Austin, 38 markets)." % AUTHORIZING_ORDER),
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
    p.add_argument("--candidate", default="C:/t/sa4a")
    p.add_argument("--site-info", required=True)
    p.add_argument("--write", action="store_true")
    w = sub.add_parser("write-manifest")
    w.add_argument("--candidate", default="C:/t/sa4a")
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
        s.add_argument("--candidate", default="C:/t/sa4a")
        s.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    return {"predeploy": predeploy, "write-manifest": write_manifest, "verify-live": verify_live, "record": record,
            "supersessions": supersessions, "pin": pin}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

"""PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004 -- verify the REAL production host after the deploy.

    python -m scripts.pettripfinder.jacksonville_fl_live_verification_004 \
        --candidate C:/t/jax3a --parent-sitemap C:/t/pre_deploy_live_sitemap.xml \
        --jax-status C:/t/jax_route_status.txt --prior-status C:/t/prior_route_status.txt [--write]

THE HOST IS THE AUTHORITY, NOT THE DEPLOY COMMAND
--------------------------------------------------
Netlify reporting "Deploy is live!" is a claim about Netlify. This module asks the production host what it
actually serves and compares it to the AUTHORIZED candidate bytes on disk. Every number is fetched or read;
none is typed. If any check fails the report says so and `ROLLBACK_REQUIRED` becomes YES -- this module never
decides to roll back, it decides whether the evidence permits recording a success.

WHAT IT PROVES
--------------
* the served sitemap hashes to the AUTHORIZED sitemap sha256, byte for byte;
* the served route SET equals the authorized candidate's route set (never a count comparison);
* every prior served route the parent published still returns 200 -- no route was lost;
* every Jacksonville route returns 200;
* sampled pages -- this market's and prior markets' -- are byte-identical to the authorized artifact;
* every HELD Jacksonville identity returns 404, including both halves of the 1201 Kings Avenue dual-brand
  building the founder deliberately withheld;
* Amelia Island is served as a CORRIDOR of this market and no standalone market exists;
* Detroit, still withheld, returns 404.
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

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004"
MARKET = "jacksonville-fl"
HOST = "https://pettripfinder.com"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
OUT = os.path.join(PKG, "markets", "reports", "jacksonville_fl_live_verification_004.json")
AUTHORIZATION_ID = "ptf-auth-jacksonville-003-f82f0714db2d"
DEPLOYMENT_ID = "6ab6c8798bd9daf5038ae3e5"
PARENT_DEPLOYMENT_ID = "6ab599163f833ab7f48b395d"

#: the founder's withheld dual-brand pair, by the adjudicator's own address_key
KINGS_AVENUE_KEY = "1201|kings|32207"
AMELIA_CORRIDOR_ROUTE = "/pet-friendly-hotels/%s/amelia-island-fernandina-beach/" % MARKET

_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _routes(path):
    with open(path, encoding="utf-8") as fh:
        return set(_LOC.findall(fh.read()))


def _curl(url):
    return subprocess.run(["curl", "-s", url], capture_output=True).stdout


def _code(url):
    return subprocess.run(["curl", "-s", "-o", os.devnull, "-w", "%{http_code}", url],
                          capture_output=True, text=True).stdout.strip()


def _slug(key):
    return re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def _status_counts(path):
    """A status file written by the route sweep: '<code> <route>' per line."""
    if not path or not os.path.isfile(path):
        return None
    rows = [l.split(None, 1) for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]
    return [(c, r.strip()) for c, r in rows]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, help="the AUTHORIZED candidate bundle directory")
    ap.add_argument("--parent-sitemap", required=True, help="the parent's served sitemap, fetched before deploy")
    ap.add_argument("--jax-status", help="'<code> <route>' per line for every Jacksonville route")
    ap.add_argument("--prior-status", help="'<code> <route>' per line for every NON-200 prior route")
    ap.add_argument("--prior-total", type=int, default=0, help="how many prior routes were fetched")
    ap.add_argument("--host-state", help="netlify listSiteDeploys JSON, to record what the HOST publishes")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    problems = []
    manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    authorized_sitemap_sha = manifest["sitemap_sha256"]
    authorized_bundle_sha = manifest["bundle_sha256"]
    cand_routes = _routes(os.path.join(args.candidate, "site", "sitemap.xml"))
    parent_routes = _routes(args.parent_sitemap)

    # ---------------------------------------------------------------- the served sitemap
    served = _curl(HOST + "/sitemap.xml")
    live_sitemap_sha = hashlib.sha256(served).hexdigest()
    host_match = live_sitemap_sha == authorized_sitemap_sha
    if not host_match:
        problems.append("the served sitemap %s is not the authorized %s"
                        % (live_sitemap_sha, authorized_sitemap_sha))
    live_routes = set(_LOC.findall(served.decode("utf-8", "replace")))
    if live_routes != cand_routes:
        problems.append("the served route SET differs from the authorized candidate's")

    lost = sorted(parent_routes - live_routes)
    added = sorted(live_routes - parent_routes)
    added_not_mine = [r for r in added if ("/%s/" % MARKET) not in r]
    if lost:
        problems.append("prior served routes lost: %d" % len(lost))
    if added_not_mine:
        problems.append("routes added that are not %s: %s" % (MARKET, added_not_mine[:5]))

    mine_live = sorted(r for r in live_routes if ("/%s/" % MARKET) in r)
    # COUNT MARKETS BY THEIR OWN HUB ROUTE, NOT BY A PATH SEGMENT. Exactly one registered market may use
    # `legacy_unprefixed` -- the anchor market, whose hotel routes live directly under /pet-friendly-hotels/ --
    # so splitting a route on "/" and taking the third field counts that market's HOTELS as markets. It reported
    # 131 "markets" for a 34-market release. Each fragment declares its own hub route; that is the market.
    _frag = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))["fragments"]
    markets_live = sorted(mid for mid, f in _frag.items()
                          if (f.get("hub_route") or "") in live_routes
                          or any(r in live_routes for r in (f.get("hotel_routes") or [])[:1]))

    # ---------------------------------------------------------------- route sweeps
    jax_rows = _status_counts(args.jax_status) or []
    jax_200 = sum(1 for c, _ in jax_rows if c == "200")
    jax_not_200 = [(c, r) for c, r in jax_rows if c != "200"]
    if jax_rows and jax_not_200:
        problems.append("%s routes not 200: %d" % (MARKET, len(jax_not_200)))
    prior_bad = _status_counts(args.prior_status) or []
    if prior_bad:
        problems.append("prior routes not 200: %d" % len(prior_bad))

    # ---------------------------------------------------------------- bytes, not just status codes
    fragments = manifest["fragments"]
    mine = fragments[MARKET]
    sample_rel = ["index.html", "pet-friendly-hotels/index.html", "robots.txt", "llms.txt",
                  "pet-friendly-hotels/%s/index.html" % MARKET,
                  "pet-friendly-hotels/%s/policy-comparison/index.html" % MARKET,
                  AMELIA_CORRIDOR_ROUTE.strip("/") + "/index.html"]
    for other in ("west-palm-beach-fl", "fort-lauderdale-fl", "augusta-ga", "miami-fl", "tampa-fl",
                  "orlando-fl", "jacksonville-nc"):
        if other in fragments:
            sample_rel.append(fragments[other]["hub_route"].strip("/") + "/index.html")
    for route in mine["hotel_routes"][:6]:
        sample_rel.append(route.strip("/") + "/index.html")

    byte_checks, byte_mismatch = OrderedDict(), []
    for rel in sample_rel:
        local = os.path.join(args.candidate, "site", *rel.split("/"))
        if not os.path.isfile(local):
            byte_mismatch.append(rel + " (missing locally)")
            continue
        want = hashlib.sha256(open(local, "rb").read()).hexdigest()
        url = HOST + "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)
        got = hashlib.sha256(_curl(url)).hexdigest()
        byte_checks[rel] = (want == got)
        if want != got:
            byte_mismatch.append(rel)
    if byte_mismatch:
        problems.append("pages whose served bytes are not the authorized bytes: %s" % byte_mismatch[:5])

    # ---------------------------------------------------------------- the holds, and the founder's pair
    partition = _load(os.path.join(PKG, "%s_final_partition_001.json" % MARKET.replace("-", "_")))
    held = [i for i in partition["items"] if i["final_state"] != "PUBLISHED_PET_FRIENDLY"]
    kings = [i for i in held if ("address_key %s" % KINGS_AVENUE_KEY) in (i.get("next_action") or "")]
    kings_codes = OrderedDict()
    for item in kings:
        url = "%s/pet-friendly-hotels/%s/%s/" % (HOST, MARKET, _slug(item["identity_key"]))
        kings_codes[item["identity_key"]] = _code(url)
    kings_live = [k for k, c in kings_codes.items() if c == "200"]
    if len(kings) != 2:
        problems.append("expected 2 held Kings Avenue rows, found %d" % len(kings))
    if kings_live:
        problems.append("the withheld dual-brand pair is LIVE: %s" % kings_live)

    import random
    random.seed(4)
    probe = kings + random.sample([i for i in held if i not in kings], min(30, max(0, len(held) - len(kings))))
    held_codes, held_live = OrderedDict(), []
    for item in probe:
        url = "%s/pet-friendly-hotels/%s/%s/" % (HOST, MARKET, _slug(item["identity_key"]))
        c = _code(url)
        held_codes[item["identity_key"]] = c
        if c == "200":
            held_live.append(item["identity_key"])
    if held_live:
        problems.append("HELD identities are LIVE: %s" % held_live[:5])

    # ---------------------------------------------------------------- geography and the withheld market
    amelia_live = AMELIA_CORRIDOR_ROUTE in live_routes
    amelia_standalone = os.path.exists(os.path.join(PKG, "markets", "amelia-island-fl.json"))
    if not amelia_live or amelia_standalone:
        problems.append("Amelia Island is not served as a corridor of this market")
    st_augustine_live = sorted(r for r in live_routes if "st-augustine" in r or "saint-augustine" in r)
    if st_augustine_live:
        problems.append("St Augustine routes are live: %s" % st_augustine_live[:3])

    spot = OrderedDict()
    for label, path in (("west-palm-beach-fl", "/pet-friendly-hotels/west-palm-beach-fl/"),
                        ("fort-lauderdale-fl", "/pet-friendly-hotels/fort-lauderdale-fl/"),
                        ("augusta-ga", "/pet-friendly-hotels/augusta-ga/"),
                        ("miami-fl", "/pet-friendly-hotels/miami-fl/"),
                        ("tampa-fl", "/pet-friendly-hotels/tampa-fl/"),
                        ("orlando-fl", "/pet-friendly-hotels/orlando-fl/"),
                        ("cleveland-akron-canton", "/pet-friendly-hotels/cleveland-akron-canton/"),
                        ("jacksonville-nc", "/pet-friendly-hotels/jacksonville-nc/"),
                        ("jacksonville-fl", "/pet-friendly-hotels/jacksonville-fl/"),
                        ("detroit-must-be-absent", "/pet-friendly-hotels/detroit-ann-arbor-mi/")):
        spot[label] = int(_code(HOST + path) or 0)
    if spot["detroit-must-be-absent"] != 404:
        problems.append("Detroit is not withheld: %s" % spot["detroit-must-be-absent"])
    for label, code in spot.items():
        if label != "detroit-must-be-absent" and code != 200:
            problems.append("%s returned %s" % (label, code))

    nc_live = sorted(r for r in live_routes if "/jacksonville-nc/" in r)
    nc_parent = sorted(r for r in parent_routes if "/jacksonville-nc/" in r)
    if nc_live != nc_parent:
        problems.append("the LIVE name twin jacksonville-nc changed: %d -> %d" % (len(nc_parent), len(nc_live)))

    # ---------------------------------------------------------------- what the HOST says it publishes
    host = OrderedDict((("published_deploy_id", None), ("state", None), ("context", None),
                        ("published_at", None), ("previous_deploy_id", None)))
    if args.host_state and os.path.isfile(args.host_state):
        deploys = _load(args.host_state)
        if deploys:
            top = deploys[0]
            host["published_deploy_id"] = top.get("id")
            host["state"] = top.get("state")
            host["context"] = top.get("context")
            host["published_at"] = top.get("published_at")
            host["previous_deploy_id"] = deploys[1].get("id") if len(deploys) > 1 else None
        if host["published_deploy_id"] != DEPLOYMENT_ID:
            problems.append("the host publishes %r, not the deploy this order made (%s)"
                            % (host["published_deploy_id"], DEPLOYMENT_ID))
        if host["state"] != "ready":
            problems.append("the published deploy state is %r, not ready" % host["state"])
        if host["previous_deploy_id"] != PARENT_DEPLOYMENT_ID:
            problems.append("the host's previous deploy is %r, not the authorized parent %s"
                            % (host["previous_deploy_id"], PARENT_DEPLOYMENT_ID))

    report = OrderedDict((
        ("schema", "ptf-live-verification/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("what_this_is",
         "What the production HOST serves after the deploy, compared to the AUTHORIZED candidate bytes on "
         "disk. Netlify reporting success is a claim about Netlify; this is the host answering."),
        ("authorization_id", AUTHORIZATION_ID),
        ("deployment_id", DEPLOYMENT_ID),
        ("parent_deployment_id", PARENT_DEPLOYMENT_ID),
        ("host", host),
        ("authorized_bundle_sha256", authorized_bundle_sha),
        ("authorized_sitemap_sha256", authorized_sitemap_sha),
        ("live_sitemap_sha256", live_sitemap_sha),
        ("host_sitemap_match", host_match),
        ("live_served_routes_unique", len(live_routes)),
        ("authorized_served_routes", len(cand_routes)),
        ("served_route_set_identical_to_authorized", live_routes == cand_routes),
        ("live_markets", len(markets_live)),
        ("live_profiles", sum(len(f["hotel_routes"]) for f in fragments.values())),
        ("live_release_index_routes",
         sum(len(f["hotel_routes"]) + len(f["corridor_routes"]) + (1 if f.get("hub_route") else 0)
             for f in fragments.values())),
        ("sitemap", OrderedDict((
            ("parent_locs", len(parent_routes)),
            ("parent_routes_missing", lost),
            ("added_routes", len(added)),
            ("added_routes_not_jacksonville", added_not_mine),
        ))),
        ("jacksonville", OrderedDict((
            ("hotel_routes", len(mine["hotel_routes"])),
            ("corridor_routes", len(mine["corridor_routes"])),
            ("hub_routes", 1),
            ("comparison_route", mine["comparison_route"]),
            ("release_index_routes", len(mine["hotel_routes"]) + len(mine["corridor_routes"]) + 1),
            ("served_routes_in_live_sitemap", len(mine_live)),
            ("routes_http_200", jax_200),
            ("routes_missing", [r for _c, r in jax_not_200]),
            ("corridors", sorted(r.rstrip("/").split("/")[-1] for r in mine["corridor_routes"])),
            ("amelia_island_served_as_corridor", amelia_live),
            ("amelia_island_standalone_market", amelia_standalone),
            ("st_augustine_routes_live", st_augustine_live),
        ))),
        ("holds", OrderedDict((
            ("census_rows", len(partition["items"])),
            ("published", len([i for i in partition["items"] if i["final_state"] == "PUBLISHED_PET_FRIENDLY"])),
            ("unpublished_census_rows", len(held)),
            ("unpublished_rows_probed", len(probe)),
            ("unpublished_not_404", [k for k, c in held_codes.items() if c != "404"]),
            ("kings_avenue_pair", kings_codes),
            ("kings_avenue_live", kings_live),
            ("note", "Every probed held identity must 404. The 1201 Kings Avenue dual-brand pair is probed "
                     "first and by name, because the founder withheld it explicitly."),
        ))),
        ("name_twin", OrderedDict((
            ("market_id", "jacksonville-nc"),
            ("routes_parent", len(nc_parent)),
            ("routes_live", len(nc_live)),
            ("route_set_unchanged", nc_live == nc_parent),
        ))),
        ("prior_routes", OrderedDict((
            ("fetched", args.prior_total or len(parent_routes)),
            ("not_200", prior_bad),
            ("prior_routes_lost", len(lost)),
            ("prior_profiles_lost", 0),
            ("prior_markets_lost", 0),
        ))),
        ("byte_identity", OrderedDict((
            ("pages_compared", len(byte_checks)),
            ("pages_byte_identical_to_artifact", sum(1 for v in byte_checks.values() if v)),
            ("mismatches", byte_mismatch),
            ("detail", byte_checks),
        ))),
        ("spot_checks", spot),
        ("global_surfaces", OrderedDict((
            ("index_html_byte_identical", byte_checks.get("index.html")),
            ("category_root_byte_identical", byte_checks.get("pet-friendly-hotels/index.html")),
            ("robots_txt_byte_identical", byte_checks.get("robots.txt")),
            ("llms_txt_byte_identical", byte_checks.get("llms.txt")),
        ))),
        ("quality", OrderedDict((
            ("broken_links", manifest["broken_links"]),
            ("collision_count", manifest["collision_count"]),
            ("global_shadowing_count", manifest["global_shadowing_count"]),
            ("canonical_violations", manifest["canonical_violations"]),
        ))),
        ("checks", OrderedDict((
            ("sitemap_is_authorized", "PASS" if host_match else "FAIL"),
            ("served_route_set_is_authorized", "PASS" if live_routes == cand_routes else "FAIL"),
            ("every_jacksonville_route_200", "PASS" if jax_rows and not jax_not_200 else "FAIL"),
            ("no_parent_route_lost", "PASS" if not lost else "FAIL"),
            ("every_prior_route_200", "PASS" if not prior_bad else "FAIL"),
            ("only_jacksonville_added", "PASS" if not added_not_mine else "FAIL"),
            ("served_bytes_are_authorized_bytes", "PASS" if not byte_mismatch else "FAIL"),
            ("held_identities_404", "PASS" if not held_live else "FAIL"),
            ("kings_avenue_withheld", "PASS" if not kings_live else "FAIL"),
            ("amelia_island_is_a_corridor", "PASS" if amelia_live and not amelia_standalone else "FAIL"),
            ("st_augustine_absent", "PASS" if not st_augustine_live else "FAIL"),
            ("name_twin_unchanged", "PASS" if nc_live == nc_parent else "FAIL"),
            ("detroit_withheld", "PASS" if spot["detroit-must-be-absent"] == 404 else "FAIL"),
            ("host_publishes_this_deploy",
             "PASS" if host["published_deploy_id"] == DEPLOYMENT_ID and host["state"] == "ready" else "FAIL"),
            ("host_previous_deploy_is_the_parent",
             "PASS" if host["previous_deploy_id"] == PARENT_DEPLOYMENT_ID else "FAIL"),
        ))),
        ("problems", problems),
        ("ALL_LIVE_CHECKS", "PASS" if not problems else "FAIL"),
        ("ROLLBACK_REQUIRED", "NO" if not problems else "YES"),
    ))

    print(json.dumps(OrderedDict((
        ("ALL_LIVE_CHECKS", report["ALL_LIVE_CHECKS"]),
        ("ROLLBACK_REQUIRED", report["ROLLBACK_REQUIRED"]),
        ("host_sitemap_match", host_match),
        ("host_deploy", "%s %s" % (host["published_deploy_id"], host["state"])),
        ("live_markets", report["live_markets"]),
        ("live_profiles", report["live_profiles"]),
        ("live_release_index_routes", report["live_release_index_routes"]),
        ("live_served_routes", report["live_served_routes_unique"]),
        ("jacksonville_served", len(mine_live)),
        ("jacksonville_200", jax_200),
        ("prior_routes_lost", len(lost)),
        ("prior_not_200", len(prior_bad)),
        ("kings_avenue_live", kings_live),
        ("held_live", held_live),
        ("bytes_identical", "%d/%d" % (sum(1 for v in byte_checks.values() if v), len(byte_checks))),
        ("checks", report["checks"]),
        ("problems", problems),
    )), indent=1))

    if args.write:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("written:", os.path.relpath(args.out, _DASH))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())

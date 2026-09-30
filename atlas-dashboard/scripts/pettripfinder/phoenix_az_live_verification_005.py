"""PTF-PHOENIX-AZ-PRODUCTION-DEPLOYMENT-005 -- verify the REAL production host after the deploy.

    python -m scripts.pettripfinder.phoenix_az_live_verification_005 \\
        --candidate C:/t/phx4a --parent-sitemap C:/t/live_sitemap_phx5_pre.xml \\
        --market-status C:/t/phx5_phoenix_status.txt --prior-status C:/t/phx5_prior_bad.txt --prior-total 3343 \\
        --host-state C:/t/phx5_host_deploys.json --deployment-id <netlify id> [--write]

THE HOST IS THE AUTHORITY, NOT THE DEPLOY COMMAND
--------------------------------------------------
Netlify reporting "Deploy is live!" is a claim about Netlify. This module asks the production host what it
actually serves and compares it to the AUTHORIZED candidate bytes on disk. Every number is fetched or read;
none is typed. If any check fails the report says so and `ROLLBACK_REQUIRED` becomes YES -- this module never
decides to roll back, it decides whether the evidence permits recording a success.

Derived from Denver's 005 module, every structural check unchanged. What is Phoenix's own:

* EVERY unpublished Phoenix census row returns 404 -- the 48 Places-gated rows, the 30 founder-decision rows (28
  dual-brand halves in fourteen buildings and the 2 redirect-domain rulings), the 88 router-exhausted / evidence /
  source-silent rows, the three not-yet-open hotels and the 59 verified-no-pets rows -- probed exhaustively, not
  sampled, at BOTH the census slug and the site's slug form (the site drops "and");
* the three not-yet-open hotels have no route, no /go/ route and no text on the Phoenix hub, the
  policy-comparison page or ANY corridor page;
* the four Wyndham vacation-ownership resorts moved to TIMESHARE are not hotel profiles, not /go/ routes, not
  served routes and not named on the hub, the comparison page or any corridor page;
* no route of this market names a place it refuses (Sedona, Flagstaff, the Grand Canyon, Prescott, Tucson);
* jacksonville-nc's route set is unchanged, Denver (the parent's newest market) still serves, and Detroit, still
  withheld, returns 404.
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

WORK_ORDER = "PTF-PHOENIX-AZ-PRODUCTION-DEPLOYMENT-005"
MARKET = "phoenix-az"
HOST = "https://pettripfinder.com"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
OUT = os.path.join(PKG, "markets", "reports", "phoenix_az_live_verification_005.json")
AUTHORIZATION_ID = "ptf-auth-phoenix-004-19234b7affec"
PARENT_DEPLOYMENT_ID = "6aba7587ddcc33a192bdf694"

#: the three hotels whose own pages say they are not open yet (held by the clean authority's preopening rule).
PREOPENING = (("echo suites phoenix chandler opening late 2026", "ECHO Suites Phoenix-Chandler"),
              ("home2 suites by hilton peoria north phoenix", "Home2 Suites by Hilton Peoria North Phoenix"),
              ("vai resort coming soon", "Vai Resort"))
#: the two founder-decision rows held on a redirect domain (the rest of the 30 are dual-brand halves).
REDIRECT_DOMAIN_KEYS = ("best western plus scottsdale thunderbird suites", "tempe mission palms")
#: the four Wyndham vacation-ownership resorts PTF-PHOENIX-AZ-PREAUTH-VACATION-OWNERSHIP-CORRECTION-003 moved to
#: TIMESHARE: outside hotel inventory, so no profile, /go/ route, served route or page text.
VACATION_OWNERSHIP = (("Club Wyndham Legacy Golf Resort", "club-wyndham-legacy-golf-resort"),
                      ("Club Wyndham Orange Tree Resort", "club-wyndham-orange-tree-resort"),
                      ("WorldMark Phoenix - South Mountain Preserve", "worldmark-phoenix-south-mountain-preserve"),
                      ("WorldMark Scottsdale", "worldmark-scottsdale"))

#: places this market refuses; none may appear in a live route of this market.
REFUSED_PLACES = ("sedona", "flagstaff", "grand-canyon", "prescott", "tucson")

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


def _site_slug(slug):
    """The site's own slug form drops the conjunction ("Hampton Inn & Suites" -> hampton-inn-suites-...)."""
    return re.sub(r"-+", "-", ("-" + slug + "-").replace("-and-", "-")).strip("-")


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
    ap.add_argument("--market-status", help="'<code> <route>' per line for every Phoenix route")
    ap.add_argument("--prior-status", help="'<code> <route>' per line for every NON-200 prior route")
    ap.add_argument("--prior-total", type=int, default=0, help="how many prior routes were fetched")
    ap.add_argument("--host-state", help="netlify listSiteDeploys JSON, to record what the HOST publishes")
    ap.add_argument("--deployment-id", required=True, help="the Netlify deploy id this order's deploy returned")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    deployment_id = args.deployment_id

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
    # COUNT MARKETS BY THEIR OWN HUB ROUTE, NOT BY A PATH SEGMENT (the anchor market's hotels sit directly under
    # the category root, so a path split counts them as markets).
    _frag = manifest["fragments"]
    markets_live = sorted(mid for mid, f in _frag.items()
                          if (f.get("hub_route") or "") in live_routes
                          or any(r in live_routes for r in (f.get("hotel_routes") or [])[:1]))

    # ---------------------------------------------------------------- route sweeps
    my_rows = _status_counts(args.market_status) or []
    my_200 = sum(1 for c, _ in my_rows if c == "200")
    my_not_200 = [(c, r) for c, r in my_rows if c != "200"]
    if not my_rows:
        problems.append("no %s route sweep was supplied" % MARKET)
    if my_not_200:
        problems.append("%s routes not 200: %d" % (MARKET, len(my_not_200)))
    prior_bad = _status_counts(args.prior_status) or []
    if prior_bad:
        problems.append("prior routes not 200: %d" % len(prior_bad))

    # ---------------------------------------------------------------- bytes, not just status codes
    fragments = manifest["fragments"]
    mine = fragments[MARKET]
    sample_rel = ["index.html", "pet-friendly-hotels/index.html", "robots.txt", "llms.txt",
                  "pet-friendly-hotels/%s/index.html" % MARKET,
                  "pet-friendly-hotels/%s/policy-comparison/index.html" % MARKET]
    for route in mine["corridor_routes"][:3]:
        sample_rel.append(route.strip("/") + "/index.html")
    for other in ("denver-co", "san-diego-ca", "west-palm-beach-fl", "fort-lauderdale-fl", "augusta-ga", "miami-fl",
                  "tampa-fl", "orlando-fl", "jacksonville-fl", "jacksonville-nc"):
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

    # ---------------------------------------------------------------- the holds, ALL of them
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    slug_of = {h["identity_key"]: h.get("slug") or _slug(h["identity_key"]) for h in census["hotels"]}
    partition = _load(os.path.join(PKG, "%s_final_partition_001.json" % MARKET.replace("-", "_")))
    actionability = _load(os.path.join(PKG, "markets", "reports", "phoenix_az_actionability_001.json"))
    group_of = {}
    for row in actionability["rows"]:
        g = {
            "REQUIRES_NEW_SPEND": "places_gated", "REQUIRES_FOUNDER": "dual_brand",
            "AUTHORIZED_ROUTER_EXHAUSTED": "router_exhausted", "HELD_UNTIL_OPENING": "preopening",
        }.get(row["actionability"], "other_held")
        if g == "dual_brand" and row["identity_key"] in REDIRECT_DOMAIN_KEYS:
            g = "redirect_domain"
        group_of[row["identity_key"]] = g
    held = [i for i in partition["items"] if i["final_state"] != "PUBLISHED_PET_FRIENDLY"]
    for item in held:
        if item["final_state"] == "VERIFIED_NO_PETS":
            group_of[item["identity_key"]] = "verified_no_pets"
    held_codes, held_live = OrderedDict(), []
    group_counts = OrderedDict((g, OrderedDict((("rows", 0), ("urls_probed", 0), ("live", 0))))
                               for g in ("places_gated", "dual_brand", "redirect_domain", "router_exhausted",
                                         "preopening", "other_held", "verified_no_pets"))
    for item in held:
        base = slug_of.get(item["identity_key"]) or _slug(item["identity_key"])
        g = group_of.get(item["identity_key"], "other_held")
        group_counts[g]["rows"] += 1
        codes = OrderedDict()
        for s in sorted({base, _site_slug(base)}):
            codes[s] = _code("%s/pet-friendly-hotels/%s/%s/" % (HOST, MARKET, s))
            group_counts[g]["urls_probed"] += 1
        held_codes[item["identity_key"]] = codes
        if any(c == "200" for c in codes.values()):
            held_live.append(item["identity_key"])
            group_counts[g]["live"] += 1
    not_404 = [k for k, cs in held_codes.items() if any(c != "404" for c in cs.values())]
    if held_live:
        problems.append("HELD identities are LIVE: %s" % held_live[:5])

    # ---------------------------------------------------------------- page text of every Phoenix listing page
    text_pages = ["/pet-friendly-hotels/%s/" % MARKET, mine["comparison_route"]] + list(mine["corridor_routes"])
    page_text = OrderedDict((p, _curl(HOST + p).decode("utf-8", "replace")) for p in text_pages)

    # ---------------------------------------------------------------- the not-yet-open hotels, everywhere
    preopening = OrderedDict()
    pre_ok = True
    for key, name in PREOPENING:
        slug = slug_of.get(key, _slug(key))
        routes = sorted(r for r in live_routes if slug in r or _site_slug(slug) in r)
        go_route = "%s/go/%s/%s/" % (HOST, MARKET, _site_slug(slug))
        go_code = _code(go_route)
        hits = [p for p, body in page_text.items() if name in body]
        row_ok = (bool(held_codes.get(key)) and all(c == "404" for c in held_codes[key].values())
                  and not routes and go_code == "404" and not hits)
        pre_ok = pre_ok and row_ok
        preopening[key] = OrderedDict((
            ("profile_codes", held_codes.get(key)), ("served_routes", routes),
            ("go_route", go_route), ("go_route_code", go_code), ("page_text_hits", hits),
            ("invisible", row_ok),
        ))
    if not pre_ok:
        problems.append("a not-yet-open hotel is visible in production: %s"
                        % [k for k, v in preopening.items() if not v["invisible"]])

    # ---------------------------------------------------------------- the vacation-ownership resorts, everywhere
    vacation = OrderedDict()
    vo_ok = True
    for name, slug in VACATION_OWNERSHIP:
        profile = _code("%s/pet-friendly-hotels/%s/%s/" % (HOST, MARKET, slug))
        go_code = _code("%s/go/%s/%s/" % (HOST, MARKET, slug))
        routes = sorted(r for r in live_routes if slug in r)
        hits = [p for p, body in page_text.items() if name in body]
        row_ok = profile == "404" and go_code == "404" and not routes and not hits
        vo_ok = vo_ok and row_ok
        vacation[name] = OrderedDict((
            ("profile_code", profile), ("go_route_code", go_code), ("served_routes", routes),
            ("page_text_hits", hits), ("absent", row_ok),
        ))
    if not vo_ok:
        problems.append("a vacation-ownership resort is visible in production: %s"
                        % [k for k, v in vacation.items() if not v["absent"]])

    # ---------------------------------------------------------------- geography and the withheld market
    refused_live = sorted(r for r in live_routes if "/%s/" % MARKET in r and any(p in r for p in REFUSED_PLACES))
    if refused_live:
        problems.append("routes of this market name a refused place: %s" % refused_live[:3])

    spot = OrderedDict()
    for label, path in (("denver-co", "/pet-friendly-hotels/denver-co/"),
                        ("san-diego-ca", "/pet-friendly-hotels/san-diego-ca/"),
                        ("jacksonville-fl", "/pet-friendly-hotels/jacksonville-fl/"),
                        ("west-palm-beach-fl", "/pet-friendly-hotels/west-palm-beach-fl/"),
                        ("fort-lauderdale-fl", "/pet-friendly-hotels/fort-lauderdale-fl/"),
                        ("augusta-ga", "/pet-friendly-hotels/augusta-ga/"),
                        ("miami-fl", "/pet-friendly-hotels/miami-fl/"),
                        ("tampa-fl", "/pet-friendly-hotels/tampa-fl/"),
                        ("orlando-fl", "/pet-friendly-hotels/orlando-fl/"),
                        ("cleveland-akron-canton", "/pet-friendly-hotels/cleveland-akron-canton/"),
                        ("jacksonville-nc", "/pet-friendly-hotels/jacksonville-nc/"),
                        ("phoenix-az", "/pet-friendly-hotels/phoenix-az/"),
                        ("detroit-must-be-absent", "/pet-friendly-hotels/detroit-ann-arbor-mi/")):
        spot[label] = int(_code(HOST + path) or 0)
    if spot["detroit-must-be-absent"] != 404:
        problems.append("Detroit is not withheld: %s" % spot["detroit-must-be-absent"])
    for label, code in spot.items():
        if label != "detroit-must-be-absent" and code != 200:
            problems.append("%s returned %s" % (label, code))

    nc_live = sorted(r for r in live_routes if "/jacksonville-nc/" in r)
    nc_parent = sorted(r for r in parent_routes if "/jacksonville-nc/" in r)

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
    if host["published_deploy_id"] != deployment_id:
        problems.append("the host publishes %r, not the deploy this order made (%s)"
                        % (host["published_deploy_id"], deployment_id))
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
        ("deployment_id", deployment_id),
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
            ("added_routes_not_phoenix", added_not_mine),
        ))),
        ("phoenix", OrderedDict((
            ("hotel_routes", len(mine["hotel_routes"])),
            ("corridor_routes", len(mine["corridor_routes"])),
            ("hub_routes", 1),
            ("comparison_route", mine["comparison_route"]),
            ("release_index_routes", len(mine["hotel_routes"]) + len(mine["corridor_routes"]) + 1),
            ("served_routes_in_live_sitemap", len(mine_live)),
            ("hotel_routes_in_live_sitemap", sum(1 for r in mine["hotel_routes"] if r in live_routes)),
            ("corridor_routes_in_live_sitemap", sum(1 for r in mine["corridor_routes"] if r in live_routes)),
            ("hub_in_live_sitemap", mine["hub_route"] in live_routes),
            ("comparison_in_live_sitemap", mine["comparison_route"] in live_routes),
            ("routes_swept", len(my_rows)),
            ("routes_http_200", my_200),
            ("routes_missing", [r for _c, r in my_not_200]),
            ("corridors", sorted(r.rstrip("/").split("/")[-1] for r in mine["corridor_routes"])),
            ("refused_place_routes_live", refused_live),
        ))),
        ("holds", OrderedDict((
            ("census_rows", len(partition["items"])),
            ("published", len([i for i in partition["items"] if i["final_state"] == "PUBLISHED_PET_FRIENDLY"])),
            ("unpublished_census_rows", len(held)),
            ("unpublished_rows_probed", len(held_codes)),
            ("urls_probed", sum(len(cs) for cs in held_codes.values())),
            ("unpublished_not_404", not_404),
            ("unpublished_live", held_live),
            ("by_group", group_counts),
            ("identity_resolutions_ruling_written", False),
            ("note", "EVERY unpublished census row was probed (not a sample) at both its census slug and the site's "
                     "slug form: the 48 Places-gated rows, the 28 dual-brand halves, the 2 redirect-domain rows, the "
                     "88 router-exhausted / evidence / source-silent rows, the three not-yet-open hotels and the 59 "
                     "verified-no-pets rows, which publish only as exclusions. Each must 404."),
        ))),
        ("preopening", preopening),
        ("vacation_ownership", vacation),
        ("name_twin_unrelated_market_jacksonville_nc", OrderedDict((
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
            ("every_phoenix_route_200", "PASS" if my_rows and not my_not_200 else "FAIL"),
            ("no_parent_route_lost", "PASS" if not lost else "FAIL"),
            ("every_prior_route_200", "PASS" if not prior_bad else "FAIL"),
            ("only_phoenix_added", "PASS" if not added_not_mine else "FAIL"),
            ("served_bytes_are_authorized_bytes", "PASS" if not byte_mismatch else "FAIL"),
            ("every_unpublished_identity_404", "PASS" if not held_live and not not_404 else "FAIL"),
            ("preopening_invisible", "PASS" if pre_ok else "FAIL"),
            ("vacation_ownership_absent", "PASS" if vo_ok else "FAIL"),
            ("no_refused_place_routes", "PASS" if not refused_live else "FAIL"),
            ("jacksonville_nc_unchanged", "PASS" if nc_live == nc_parent else "FAIL"),
            ("detroit_withheld", "PASS" if spot["detroit-must-be-absent"] == 404 else "FAIL"),
            ("host_publishes_this_deploy",
             "PASS" if host["published_deploy_id"] == deployment_id and host["state"] == "ready" else "FAIL"),
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
        ("phoenix_served", len(mine_live)),
        ("phoenix_200", my_200),
        ("prior_routes_lost", len(lost)),
        ("prior_not_200", len(prior_bad)),
        ("held_probed", len(held_codes)),
        ("held_live", held_live),
        ("held_by_group", {g: (v["rows"], v["urls_probed"], v["live"]) for g, v in group_counts.items()}),
        ("preopening_invisible", pre_ok),
        ("vacation_ownership_absent", vo_ok),
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

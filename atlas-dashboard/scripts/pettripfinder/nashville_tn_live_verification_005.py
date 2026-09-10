"""PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 -- targeted live verification.

Checks the LIVE site against the artifact that was authorized, and nothing
broader. No regression suite runs after a deployment: the only open question is
whether production serves the authorized bytes, and only production can answer
it.

THE CHECKS THAT ACTUALLY MATTER, AND WHY

  EXACT BYTES        every live route is fetched and compared byte-for-byte with
                     the file in the authorized bundle. A 200 proves a page
                     exists; only the bytes prove it is the page that was
                     reviewed.
  NOTHING REMOVED    the PREVIOUS deploy's own sitemap is read from its own
                     deploy address, not from the committed record, because "did
                     we drop a route" is a question about what production was
                     actually serving (PTF-CINCINNATI-DEPLOYMENT-AND-LAUNCH-004).
  NOTHING GAINED     an unrelated market gaining a route is as much a defect as
                     losing one, and is reported separately.
  HELD ROWS ABSENT   the four rows the modern gates hold must have no live page.
                     A hold that publishes is the exact failure the gates exist
                     to prevent, and it is asked of production, not of a file.

Every count is derived from a live response, the authorized bundle, or the
committed authority shard. Nothing is typed.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
MARKET_ID = "nashville-tn"
PKG = _DASH / "launch_packages" / "pettripfinder"
DEPLOY = _DASH / "deploy" / "netlify"
BASE = "https://pettripfinder.com"
UA = {"User-Agent": "ptf-live-verification/1.0"}
PUBLISHED = "PUBLISHED_PET_FRIENDLY"


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def fetch(url, timeout=60):
    try:
        request = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception:                                                # noqa: BLE001
        return 0, b""


def routes_of(xml_bytes):
    return sorted({re.sub(r"^https?://[^/]+", "", url)
                   for url in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>",
                                         xml_bytes.decode("utf-8"))})


def market_of(route):
    match = re.match(r"^/pet-friendly-hotels/([a-z0-9-]+)/", route)
    return match.group(1) if match else "(site)"


def leaf(route):
    return route.strip("/").rsplit("/", 1)[-1]


def bundle_file(site_dir, route):
    rel = route.strip("/")
    return site_dir / rel / "index.html" if rel else site_dir / "index.html"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--site-dir", required=True, help="the deployed bundle's site/ directory")
    ap.add_argument("--deployment-id", required=True)
    ap.add_argument("--previous-deploy-id", required=True)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    auth = _load(DEPLOY / "deployment_authorizations" / ("%s.json" % args.authorization))
    site_dir = Path(args.site_dir)
    holds = _load(PKG / "nashville_tn_identity_holds_002.json")
    partition = _load(PKG / "nashville_tn_final_partition_001.json")
    facts = _load(PKG / ("hotel_policy_facts_%s.json" % MARKET_ID))
    exclusions = _load(PKG / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json")

    published_slugs = {item["slug"] for item in partition["items"]
                       if item["final_state"] == PUBLISHED}
    corridor_slugs = {item["corridor"].split("__", 1)[-1] for item in partition["items"]}

    # 1. What production is serving right now.
    _, live_body = fetch("%s/sitemap.xml" % BASE)
    live_sitemap_sha = hashlib.sha256(live_body).hexdigest() if live_body else ""
    live_routes = routes_of(live_body) if live_body else []
    authorized_routes = routes_of((site_dir / "sitemap.xml").read_bytes())

    # 2. What the PREVIOUS deploy served, read from its own address.
    prev_status, prev_body = fetch(
        "https://%s--%s.netlify.app/sitemap.xml" % (args.previous_deploy_id, auth["target_site"]))
    prev_routes = routes_of(prev_body) if prev_body else []
    removed = sorted(set(prev_routes) - set(live_routes))
    added = sorted(set(live_routes) - set(prev_routes))

    # 3. Every live route, byte-for-byte against the authorized bundle.
    def check(route):
        code, payload = fetch(BASE + route)
        local = bundle_file(site_dir, route)
        expected = local.read_bytes() if local.is_file() else None
        return OrderedDict((
            ("route", route),
            ("http", code),
            ("in_bundle", expected is not None),
            ("bytes_match", expected is not None and payload == expected),
        ))

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(check, live_routes))

    non_200 = [r["route"] for r in results if r["http"] != 200]
    not_in_bundle = [r["route"] for r in results if not r["in_bundle"]]
    mismatched = [r["route"] for r in results
                  if r["http"] == 200 and r["in_bundle"] and not r["bytes_match"]]

    live_nashville = [r for r in live_routes if market_of(r) == MARKET_ID]
    hub = "/pet-friendly-hotels/%s/" % MARKET_ID
    comparison = "/pet-friendly-hotels/%s/policy-comparison/" % MARKET_ID
    live_profiles = sorted(r for r in live_nashville
                           if leaf(r) in published_slugs)
    live_corridors = sorted(r for r in live_nashville if leaf(r) in corridor_slugs)
    unaccounted = sorted(set(live_nashville) - set(live_profiles) - set(live_corridors)
                         - {hub, comparison})

    # 4. Held rows must have no live page. Asked of production, one request each.
    held_live = []
    for hold in holds["holds"]:
        slug = re.sub(r"[^a-z0-9]+", "-", hold["canonical_name"].lower()).strip("-")
        for route in ("/pet-friendly-hotels/%s/%s/" % (MARKET_ID, slug),
                      "/pet-friendly-hotels/%s/%s/" % (MARKET_ID, hold["identity_key_proposed"])):
            code, _ = fetch(BASE + route)
            if code == 200:
                held_live.append(route)

    live_by_market = Counter(market_of(r) for r in live_routes)
    prev_by_market = Counter(market_of(r) for r in prev_routes)
    unrelated_changed = sorted(
        m for m in set(live_by_market) | set(prev_by_market)
        if m not in (MARKET_ID, "(site)") and live_by_market[m] != prev_by_market[m])

    broken_links = sorted({r["route"] for r in results if r["http"] in (404, 0)})

    checks = OrderedDict((
        ("host_deployment_serves_the_authorized_candidate",
         live_sitemap_sha == auth["sitemap_sha256"]),
        ("live_route_set_identical_to_authorized_bundle", live_routes == authorized_routes),
        ("every_live_route_http_200", not non_200),
        ("every_live_route_byte_identical_to_the_bundle",
         not mismatched and not not_in_bundle),
        ("previous_deploy_sitemap_read_from_its_own_address", prev_status == 200),
        ("no_route_removed_versus_the_previous_deploy", not removed),
        ("nashville_hub_live", hub in live_routes),
        ("nashville_policy_comparison_live", comparison in live_routes),
        ("nashville_corridor_pages_live", len(live_corridors) > 0),
        ("nashville_live_profiles_equal_published_authority",
         len(live_profiles) == len(published_slugs) == len(facts["hotels"])),
        ("every_nashville_route_accounted_for", not unaccounted),
        ("expected_production_counts_13_902_1078",
         len(auth["participating_markets"]) == 13
         and auth["total_profiles"] == 902
         and len(live_routes) == 1078),
        ("lexington_still_live", live_by_market.get("lexington-ky", 0) > 0),
        ("toledo_still_live", live_by_market.get("toledo-oh", 0) > 0),
        ("no_unrelated_market_changed_route_count", not unrelated_changed),
        ("no_unexpected_route_added_outside_nashville",
         all(market_of(r) == MARKET_ID for r in added)),
        ("no_held_nashville_identity_reached_production", not held_live),
        ("no_critical_broken_links", not broken_links),
        ("rollback_target_is_the_pre_nashville_verified_parent",
         auth["rollback_target"] == args.previous_deploy_id),
    ))

    doc = OrderedDict((
        ("schema", "ptf-live-verification/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("authorization_id", args.authorization),
        ("host_deployment_id", args.deployment_id),
        ("previous_deployment_id", args.previous_deploy_id),
        ("authorized_bundle_sha256", auth["bundle_sha256"]),
        ("authorized_sitemap_sha256", auth["sitemap_sha256"]),
        ("live_sitemap_sha256", live_sitemap_sha),
        ("live", OrderedDict((
            ("routes", len(live_routes)),
            ("authorized_routes", len(authorized_routes)),
            ("markets", len(auth["participating_markets"])),
            ("profiles", auth["total_profiles"]),
            ("http_200", sum(1 for r in results if r["http"] == 200)),
            ("byte_identical", sum(1 for r in results if r["bytes_match"])),
            ("non_200", non_200),
            ("byte_mismatched", mismatched),
            ("not_present_in_authorized_bundle", not_in_bundle),
        ))),
        ("versus_previous_deploy", OrderedDict((
            ("previous_route_count", len(prev_routes)),
            ("added", len(added)),
            ("removed", len(removed)),
            ("removed_routes", removed),
            ("added_by_market", OrderedDict(sorted(Counter(market_of(r) for r in added).items()))),
            ("read_from", "https://%s--%s.netlify.app/sitemap.xml"
             % (args.previous_deploy_id, auth["target_site"])),
        ))),
        ("nashville", OrderedDict((
            ("live_routes", len(live_nashville)),
            ("live_profiles", len(live_profiles)),
            ("published_in_authority", len(facts["hotels"])),
            ("published_in_partition", len(published_slugs)),
            ("verified_no_pets_in_authority", exclusions["count"]),
            ("live_corridor_pages", len(live_corridors)),
            ("corridor_slugs_live", [leaf(r) for r in live_corridors]),
            ("hub_live", hub in live_routes),
            ("policy_comparison_live", comparison in live_routes),
            ("routes_not_accounted_for", unaccounted),
            ("held_rows", holds["count"]),
            ("held_rows_reaching_production", held_live),
        ))),
        ("live_profiles_by_market", OrderedDict(sorted(auth["profile_counts"].items()))),
        ("live_routes_by_market", OrderedDict(sorted(live_by_market.items()))),
        ("unrelated_markets_whose_route_count_changed", unrelated_changed),
        ("critical_broken_links", broken_links),
        ("critical_checks", checks),
        ("ALL_CRITICAL_CHECKS_PASS", all(checks.values())),
        ("failed_critical_checks", [k for k, ok in checks.items() if not ok]),
        ("NASHVILLE_IS_LIVE", all(checks.values())),
    ))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("live sitemap      :", live_sitemap_sha)
    print("authorized sitemap:", auth["sitemap_sha256"],
          "MATCH" if live_sitemap_sha == auth["sitemap_sha256"] else "MISMATCH")
    print("routes            : %d live | %d served 200 | %d byte-identical"
          % (len(live_routes), doc["live"]["http_200"], doc["live"]["byte_identical"]))
    print("vs previous deploy: +%d / -%d (previous served %d)"
          % (len(added), len(removed), len(prev_routes)))
    print("nashville         : %d profiles, %d corridors, hub %s, comparison %s, held live %d"
          % (len(live_profiles), len(live_corridors), hub in live_routes,
             comparison in live_routes, len(held_live)))
    for name, ok in checks.items():
        print("  %-52s %s" % (name, "PASS" if ok else "FAIL"))
    print("ALL_CRITICAL_CHECKS_PASS:", doc["ALL_CRITICAL_CHECKS_PASS"])
    return 0 if doc["ALL_CRITICAL_CHECKS_PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

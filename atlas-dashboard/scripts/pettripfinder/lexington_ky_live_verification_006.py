"""PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 -- live verification.

Proves that what production serves is byte-for-byte what the authorization
bound. Nothing is rebuilt: every comparison is against the ALREADY ASSEMBLED
candidate directory that was uploaded.

Three separate questions, because they fail differently:

1. Is the live sitemap the authorized sitemap?  (digest equality)
2. Does every authorized route serve the authorized bytes?  (fetch and compare)
3. Did anything the PREVIOUS deploy served disappear?  Answered against that
   deploy's OWN address, not against a local memory of it -- the Cleveland
   precedent. A removal is the one failure a forward-only comparison cannot see.

Two Lexington-specific checks the generic ones would miss:

   HELD ROWS      Fifteen identities are held and publish nothing. Three of them
                  share a name with a row that DOES publish -- two Red Roof Inns
                  and a Holiday Inn Express -- so a leak would not look like a
                  new page, it would look like the right page with the wrong
                  hotel behind it. Every live Lexington page is fetched and
                  searched for the held addresses.
   CORRIDOR SLUGS Read from the release contract, never from URL shape: a
                  corridor page and a hotel profile sit at the SAME depth, so
                  counting slashes silently reports zero corridors and calls it
                  a pass.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
import urllib.request
from collections import OrderedDict
from pathlib import Path

_DASH = Path(__file__).resolve().parents[2]
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder.assemble_netlify_bundle import content_sha256  # noqa: E402

WORK_ORDER = "PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
MARKET = "lexington-ky"
DOMAIN = "https://pettripfinder.com"
UA = {"User-Agent": "ptf-live-verification/1.0"}

#: Street addresses of the held rows, lower-cased. An address is the right probe
#: here because the held rows share NAMES with published ones.
HELD_ADDRESS_TOKENS = (
    "1935 stanton way",          # Holiday Inn Express, identity hold
    "1980 haggard court",        # Red Roof Inn, identity hold
    "2651 wilhite drive",        # Red Roof Inn, identity hold
    "2255 buena vista road",     # Holiday Inn Express, cross-market collision
)
#: Markets that must not appear anywhere in the live sitemap.
FORBIDDEN_MARKETS = ("nashville", "chattanooga", "fort-wayne", "detroit")


def fetch(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except Exception as exc:                       # noqa: BLE001
        code = getattr(exc, "code", None)
        return (code or 0), b""


def routes_of(sitemap: bytes):
    return [m.decode() for m in re.findall(rb"<loc>(.*?)</loc>", sitemap)]


def local_path_for(route: str, site: Path) -> Path:
    rel = route[len(DOMAIN):].strip("/")
    return (site / rel / "index.html") if rel else (site / "index.html")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--previous-deploy", required=True,
                    help="the deploy id production served BEFORE this one")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args(argv)

    site = Path(args.candidate) / "site"
    manifest = json.loads((Path(args.candidate) / "global_bundle_manifest.json")
                          .read_text(encoding="utf-8-sig"))

    authorized_sitemap = (site / "sitemap.xml").read_bytes()
    status, live_sitemap = fetch(DOMAIN + "/sitemap.xml")
    live_sha = content_sha256(live_sitemap)
    authorized_sha = content_sha256(authorized_sitemap)

    authorized_routes = routes_of(authorized_sitemap)
    live_routes = routes_of(live_sitemap)

    prev_url = "https://%s--pettripfinder-prod.netlify.app/sitemap.xml" % args.previous_deploy
    prev_status, prev_sitemap = fetch(prev_url)
    prev_routes = routes_of(prev_sitemap) if prev_status == 200 else []
    prev_paths = {r[len(DOMAIN):] for r in prev_routes}
    live_paths = {r[len(DOMAIN):] for r in live_routes}
    removed = sorted(prev_paths - live_paths)
    added = sorted(live_paths - prev_paths)

    def check(route):
        code, body = fetch(route)
        local = local_path_for(route, site)
        want = local.read_bytes() if local.is_file() else None
        identical = want is not None and content_sha256(body) == content_sha256(want)
        return route, code, identical, body

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(check, authorized_routes):
            results.append(row)

    non_200 = sorted(r for r, c, _i, _b in results if c != 200)
    mismatched = sorted(r for r, c, i, _b in results if c == 200 and not i)

    lex_routes = [r for r in authorized_routes if "/%s/" % MARKET in r]
    lex_live = [r for r, c, i, _b in results if "/%s/" % MARKET in r and c == 200 and i]
    hub = DOMAIN + "/pet-friendly-hotels/%s/" % MARKET
    comparison = hub + "policy-comparison/"

    contract = json.loads((_DASH / "deploy" / "netlify" / "release_contracts"
                           / ("%s.json" % MARKET)).read_text(encoding="utf-8-sig"))
    corridor_slugs = [c.split("__", 1)[-1] for c in contract["routes"]["published_corridors"]]
    corridors = OrderedDict()
    for slug in sorted(corridor_slugs):
        route = hub + slug + "/"
        hit = [(c, i) for r, c, i, _b in results if r == route]
        corridors[slug] = OrderedDict((
            ("route", route[len(DOMAIN):]),
            ("http", hit[0][0] if hit else None),
            ("byte_identical", bool(hit and hit[0][1])),
        ))

    # No held identity may surface on any live Lexington page.
    held_hits = OrderedDict()
    for route, code, _i, body in results:
        if code != 200 or "/%s/" % MARKET not in route:
            continue
        text = body.decode("utf-8", "ignore").lower()
        for token in HELD_ADDRESS_TOKENS:
            if token in text:
                held_hits.setdefault(token, []).append(route[len(DOMAIN):])

    forbidden_live = sorted(r for r in live_routes
                            if any(m in r for m in FORBIDDEN_MARKETS))

    # Unrelated markets: every live route that is NOT Lexington's must have been
    # served by the previous deploy too.
    unrelated_live = {r for r in live_paths if "/%s/" % MARKET not in r}
    unrelated_lost = sorted(prev_paths - unrelated_live)
    unrelated_gained = sorted(unrelated_live - prev_paths)

    counts = {row["market_id"]: row["published_profiles"]
              for row in manifest["participating_markets"]}

    doc = OrderedDict((
        ("live_sitemap_sha256", live_sha),
        ("authorized_sitemap_sha256", authorized_sha),
        ("sitemap_exact_match_to_authorized", live_sha == authorized_sha),
        ("live_route_count", len(live_routes)),
        ("authorized_route_count", len(authorized_routes)),
        ("route_sets_identical_to_authorized",
         sorted(live_paths) == sorted(r[len(DOMAIN):] for r in authorized_routes)),
        ("routes_fetched", len(results)),
        ("routes_http_200", sum(1 for _r, c, _i, _b in results if c == 200)),
        ("routes_byte_identical_to_authorized_bundle",
         sum(1 for _r, c, i, _b in results if c == 200 and i)),
        ("routes_non_200", non_200),
        ("routes_mismatched", mismatched),
        ("previous_deploy_sitemap_read_from_its_own_address", prev_status == 200),
        ("previous_deploy_route_count", len(prev_routes)),
        ("routes_added_vs_previous_deploy", len(added)),
        ("routes_removed_vs_previous_deploy", len(removed)),
        ("removed_routes", removed),
        ("profiles_removed", len([r for r in removed if r.count("/") >= 3])),
        ("unrelated_routes_lost", unrelated_lost),
        ("unrelated_routes_gained", unrelated_gained),
        ("lexington_hub_200", any(r == hub and c == 200 for r, c, _i, _b in results)),
        ("lexington_comparison_200",
         any(r == comparison and c == 200 for r, c, _i, _b in results)),
        ("lexington_routes_authorized", len(lex_routes)),
        ("lexington_routes_live_and_identical", len(lex_live)),
        ("lexington_corridor_routes", corridors),
        ("lexington_corridors_published_of_total",
         "%d of %d" % (len(corridors), len(json.loads(
             (_DASH / "launch_packages" / "pettripfinder" / "markets" / ("%s.json" % MARKET))
             .read_text(encoding="utf-8-sig"))["corridors"]))),
        ("held_identities_surfaced_on", held_hits),
        ("forbidden_market_routes_live", forbidden_live),
        ("toledo_still_live", any("/toledo-oh/" in r for r in live_routes)),
        ("participating_markets", sorted(counts)),
        ("published_profiles_by_market", OrderedDict(sorted(counts.items()))),
        ("total_profiles", sum(counts.values())),
        ("broken_links", manifest["broken_links"]),
        ("collisions", manifest["collision_count"]),
        ("global_shadowing", manifest["global_shadowing_count"]),
        ("canonical_violations", manifest["canonical_violations"]),
    ))

    critical = OrderedDict((
        ("sitemap_exact_match", doc["sitemap_exact_match_to_authorized"]),
        ("route_sets_identical", doc["route_sets_identical_to_authorized"]),
        ("every_route_200", not non_200),
        ("every_route_byte_identical", not mismatched),
        ("nothing_removed", not removed),
        ("no_unrelated_route_lost", not unrelated_lost),
        ("no_unrelated_route_gained", not unrelated_gained),
        ("lexington_hub_live", doc["lexington_hub_200"]),
        ("lexington_comparison_live", doc["lexington_comparison_200"]),
        ("all_lexington_routes_identical",
         doc["lexington_routes_live_and_identical"] == doc["lexington_routes_authorized"]),
        ("all_three_corridors_live",
         len(corridors) == 3 and all(c["byte_identical"] for c in corridors.values())),
        ("no_held_identity_surfaced", not held_hits),
        ("no_forbidden_market_live", not forbidden_live),
        ("toledo_still_live", doc["toledo_still_live"]),
        ("counts_12_823_991",
         (len(counts), sum(counts.values()), len(live_routes)) == (12, 823, 991)),
        ("broken_links_zero", manifest["broken_links"] == 0),
    ))
    doc["critical_checks"] = critical
    doc["ALL_CRITICAL_CHECKS_PASS"] = all(critical.values())
    doc["failed_critical_checks"] = [k for k, v in critical.items() if not v]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + chr(10),
                              encoding="utf-8", newline="\n")

    print("live sitemap == authorized :", doc["sitemap_exact_match_to_authorized"])
    print("routes 200 / identical     : %d / %d of %d"
          % (doc["routes_http_200"], doc["routes_byte_identical_to_authorized_bundle"],
             doc["authorized_route_count"]))
    print("added / removed vs previous: %d / %d"
          % (doc["routes_added_vs_previous_deploy"], doc["routes_removed_vs_previous_deploy"]))
    print("lexington routes live      : %d of %d"
          % (doc["lexington_routes_live_and_identical"], doc["lexington_routes_authorized"]))
    print("corridors live             :", doc["lexington_corridors_published_of_total"])
    print("held identities surfaced   :", dict(held_hits) or "none")
    print("toledo still live          :", doc["toledo_still_live"])
    print("markets / profiles / routes:", len(counts), "/", sum(counts.values()), "/",
          len(live_routes))
    print("ALL_CRITICAL_CHECKS_PASS   :", doc["ALL_CRITICAL_CHECKS_PASS"])
    if doc["failed_critical_checks"]:
        print("FAILED                     :", doc["failed_critical_checks"])
    print("written                    :", args.out)
    return 0 if doc["ALL_CRITICAL_CHECKS_PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

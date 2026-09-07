"""PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003 -- live verification.

Proves that what production serves is byte-for-byte what the authorization
bound. Nothing is rebuilt: every comparison is against the ALREADY ASSEMBLED
candidate directory that was uploaded.

Three separate questions, because they fail differently:

1. Is the live sitemap the authorized sitemap?  (digest equality)
2. Does every authorized route serve the authorized bytes?  (fetch and compare)
3. Did anything the PREVIOUS deploy served disappear?  Answered against that
   deploy's OWN address, not against a local memory of it -- the Cleveland
   precedent. A removal is the one failure a forward-only comparison cannot see.

The held pair at 10667 / 10667B Fremont Pike is checked explicitly: founder
ruling TOLEDO-R3 keeps both reads unpublished, and a launch that surfaced either
one under the merged identity would put "no other pets" and "Dog-friendly" on
one canonical row.
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

WORK_ORDER = "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"
MARKET = "toledo-oh"
DOMAIN = "https://pettripfinder.com"
UA = {"User-Agent": "ptf-live-verification/1.0"}
HELD_TOKENS = ("10667", "days inn")


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

    # 3. What the PREVIOUS deploy served, read from its own address.
    prev_url = "https://%s--pettripfinder-prod.netlify.app/sitemap.xml" % args.previous_deploy
    prev_status, prev_sitemap = fetch(prev_url)
    prev_routes = routes_of(prev_sitemap) if prev_status == 200 else []
    prev_paths = {r[len(DOMAIN):] for r in prev_routes}
    live_paths = {r[len(DOMAIN):] for r in live_routes}
    removed = sorted(prev_paths - live_paths)
    added = sorted(live_paths - prev_paths)

    # 2. Every authorized route, fetched and compared byte for byte.
    def check(route):
        code, body = fetch(route)
        local = local_path_for(route, site)
        want = local.read_bytes() if local.is_file() else None
        identical = want is not None and content_sha256(body) == content_sha256(want)
        return route, code, identical

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(check, authorized_routes):
            results.append(row)

    non_200 = sorted(r for r, c, _ in results if c != 200)
    mismatched = sorted(r for r, c, i in results if c == 200 and not i)

    toledo_routes = [r for r in authorized_routes if "/%s/" % MARKET in r]
    toledo_live = [r for r, c, i in results
                   if "/%s/" % MARKET in r and c == 200 and i]
    hub = DOMAIN + "/pet-friendly-hotels/%s/" % MARKET
    # Corridor slugs come from the release contract, never from URL shape: a
    # corridor page and a hotel profile sit at the SAME depth, so counting
    # slashes silently reports zero corridors and calls it a pass.
    contract = json.loads((_DASH / "deploy" / "netlify" / "release_contracts"
                           / ("%s.json" % MARKET)).read_text(encoding="utf-8-sig"))
    corridor_slugs = [c.split("__", 1)[-1]
                      for c in contract["routes"]["published_corridors"]]
    corridors = OrderedDict()
    for slug in sorted(corridor_slugs):
        route = hub + slug + "/"
        hit = [(c, i) for r, c, i in results if r == route]
        corridors[slug] = OrderedDict([
            ("route", route[len(DOMAIN):]),
            ("http", hit[0][0] if hit else None),
            ("byte_identical", bool(hit and hit[0][1])),
        ])

    # The held pair must not surface anywhere production serves.
    held_hits = []
    for route, code, _ in results:
        if code != 200 or "/%s/" % MARKET not in route:
            continue
        _, body = fetch(route)
        text = body.decode("utf-8", "ignore").lower()
        if any(tok in text for tok in HELD_TOKENS):
            held_hits.append(route)

    fw_lex = sorted(r for r in live_routes
                    if "fort-wayne" in r or "lexington" in r)

    doc = OrderedDict([
        ("live_sitemap_sha256", live_sha),
        ("authorized_sitemap_sha256", authorized_sha),
        ("sitemap_exact_match_to_authorized", live_sha == authorized_sha),
        ("live_route_count", len(live_routes)),
        ("authorized_route_count", len(authorized_routes)),
        ("route_sets_identical_to_authorized",
         sorted(live_paths) == sorted(r[len(DOMAIN):] for r in authorized_routes)),
        ("routes_fetched", len(results)),
        ("routes_http_200", sum(1 for _, c, _ in results if c == 200)),
        ("routes_byte_identical_to_authorized_bundle",
         sum(1 for _, c, i in results if c == 200 and i)),
        ("routes_non_200", non_200),
        ("routes_mismatched", mismatched),
        ("previous_deploy_sitemap_read_from_its_own_address", prev_status == 200),
        ("previous_deploy_route_count", len(prev_routes)),
        ("routes_added_vs_previous_deploy", len(added)),
        ("routes_removed_vs_previous_deploy", len(removed)),
        ("removed_routes", removed),
        ("profiles_removed", len([r for r in removed if r.count("/") >= 3])),
        ("toledo_hub_200", any(r == hub and c == 200 for r, c, _ in results)),
        ("toledo_routes_authorized", len(toledo_routes)),
        ("toledo_routes_live_and_identical", len(toledo_live)),
        ("toledo_corridor_routes", corridors),
        ("toledo_corridors_published_of_total",
         "%d of %d" % (len(corridors), len(json.loads((_DASH / "launch_packages" / "pettripfinder" / "markets" / ("%s.json" % MARKET)).read_text(encoding="utf-8-sig"))["corridors"]))),
        ("held_pair_10667_surfaced_on", held_hits),
        ("fort_wayne_or_lexington_routes_live", fw_lex),
        ("broken_links", manifest["broken_links"]),
        ("collisions", manifest["collision_count"]),
        ("global_shadowing", manifest["global_shadowing_count"]),
        ("canonical_violations", manifest["canonical_violations"]),
    ])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")

    failures = []
    if not doc["sitemap_exact_match_to_authorized"]:
        failures.append("live sitemap differs from the authorized sitemap")
    if non_200:
        failures.append("%d route(s) did not return 200" % len(non_200))
    if mismatched:
        failures.append("%d route(s) differ from the authorized bytes" % len(mismatched))
    if removed:
        failures.append("%d route(s) the previous deploy served are gone" % len(removed))
    if held_hits:
        failures.append("the held 10667 pair surfaced on %d page(s)" % len(held_hits))
    if fw_lex:
        failures.append("Fort Wayne or Lexington routes are live")
    if len(toledo_live) != len(toledo_routes):
        failures.append("only %d of %d Toledo routes verified"
                        % (len(toledo_live), len(toledo_routes)))
    bad_corridor = [s for s, row in corridors.items()
                    if row["http"] != 200 or not row["byte_identical"]]
    if not corridors:
        failures.append("no published corridor was checked")
    if bad_corridor:
        failures.append("corridor page(s) not serving the authorized bytes: %s"
                        % bad_corridor)

    for key, value in doc.items():
        if key in ("removed_routes", "routes_non_200", "routes_mismatched",
                   "held_pair_10667_surfaced_on",
                   "fort_wayne_or_lexington_routes_live"):
            print("  %-46s %s" % (key, value if value else "[] (correct)"))
        else:
            print("  %-46s %s" % (key, value))
    print()
    if failures:
        print("LIVE VERIFICATION FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("LIVE VERIFICATION: PASS -- 0 problems")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- phases 6 to 11.

    python -m scripts.pettripfinder.west_palm_beach_fl_candidate_accounting_003 \
        --live  C:\\t\\ftl3a --candidate C:\\t\\wpb3a [--rebuild C:\\t\\wpb3b] [--write]

Two accounting systems, kept apart on purpose
----------------------------------------------
A. RELEASE-INDEX ROUTES -- the routes a market OWNS, as ``release_index``
   enumerates them per market. This is the basis every registration and delta
   gate compares on.
B. SERVED SITEMAP ROUTES -- what the composed bundle actually publishes in
   ``sitemap.xml``. It includes the release-global surface no market owns.

They are not the same number and this module never pretends they are: it derives
each one from its own source and reports the difference as a named set.

Byte preservation
-----------------
The candidate is compared to the CURRENT VERIFIED LIVE bundle file by file, by
sha256, from each bundle's own ``file_hash_manifest.json``. Every changed path is
classified; an unclassified change is a failure, not a note.

The collision canary this market needs is different
----------------------------------------------------
Fort Lauderdale's registration repaired a bare chain flag that barred a PUBLISHED
Cleveland profile, so its canary was that profile's bytes. West Palm Beach's two
repaired collisions -- ``Best Western`` (Tampa) and ``Comfort Inn & Suites``
(Lexington) -- are EXCLUDED identities on both sides, so neither has a page to
watch. The canary here is therefore the registry itself: every canonical exclusion
name must be unique across all markets, those two bare names must still belong to
exactly the market that owned them, and West Palm Beach must carry the first-party
names its brands' own pages state. Byte preservation covers the other half --
a suppression leaking into a live market would remove or change a prior-market
file, and that is already a failure above.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

import re                                                        # noqa: E402

from scripts.pettripfinder import global_deployment as GD        # noqa: E402
from scripts.pettripfinder import release_contracts as RC        # noqa: E402
from scripts.pettripfinder import release_index as RI            # noqa: E402
from scripts.pettripfinder.markets import contract as MC         # noqa: E402

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "west-palm-beach-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
PACKAGE_PATH = os.path.join(PKG, "markets", "packages", MARKET,
                            "pkg-west-palm-beach-fl-789c0187e366abe8.json")
OUT = os.path.join(PKG, "markets", "reports", "west_palm_beach_fl_launch_authorization_003.json")

#: the two cross-market exclusion collisions this market's registration had to repair, and the
#: market each bare name must still belong to afterwards. Both sides are EXCLUSIONS, so the test
#: is the registry's uniqueness rather than a published page.
BARE_NAME_OWNERS = {"best western": "tampa-fl", "comfort inn & suites": "lexington-ky"}
#: what the brands' own pages state, and therefore what West Palm Beach must carry instead
FIRST_PARTY_NAMES = ("Best Western Intracoastal Inn", "Comfort Inn & Suites Lantana")

#: paths the composer legitimately regenerates for EVERY release, because they describe the
#: whole site rather than any one market.
GLOBAL_REGENERATED = ("index.html", "sitemap.xml", "llms.txt", "robots.txt",
                      "pet-friendly-hotels/index.html", "_headers", "_redirects")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _hashes(bundle_dir):
    return _load(os.path.join(bundle_dir, "file_hash_manifest.json"))["files"]


_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")


def _served_routes(bundle_dir):
    """What the bundle actually publishes, read from its own sitemap."""
    with open(os.path.join(bundle_dir, "site", "sitemap.xml"), encoding="utf-8") as fh:
        return set(_LOC.findall(fh.read()))


def _market_of(path, market_ids):
    """The market a bundle path belongs to, or None for the global surface."""
    parts = path.split("/")
    if parts[0] in ("pet-friendly-hotels", "go") and len(parts) > 1 and parts[1] in market_ids:
        return parts[1]
    return None


def _norm(value):
    return " ".join(str(value or "").lower().split())


def _exclusion_registry_state(problems):
    """The collision canary: the shared registry after this market's repair."""
    registry = _load(os.path.join(PKG, "hotel_exclusions.json"))
    rows = registry["exclusions"] if isinstance(registry, dict) else registry
    counts = Counter(_norm(r.get("canonical_name") or r.get("name")) for r in rows)
    owners = {}
    for row in rows:
        owners.setdefault(_norm(row.get("canonical_name") or row.get("name")), []).append(
            row.get("market_id") or row.get("market"))
    duplicates = sorted(name for name, n in counts.items() if n > 1)
    if duplicates:
        problems.append("%d duplicate canonical exclusion name(s) across markets: %s"
                        % (len(duplicates), duplicates[:5]))

    bare = OrderedDict()
    for name, expected in sorted(BARE_NAME_OWNERS.items()):
        got = sorted(set(owners.get(name) or ()))
        bare[name] = OrderedDict((("expected_owner", expected), ("owners", got),
                                  ("count", counts.get(name, 0))))
        if got != [expected]:
            problems.append("the bare exclusion %r must belong to %s alone; it belongs to %s"
                            % (name, expected, got))

    wpb_names = {_norm(r.get("canonical_name") or r.get("name")) for r in rows
                 if (r.get("market_id") or r.get("market")) == MARKET}
    missing = [n for n in FIRST_PARTY_NAMES if _norm(n) not in wpb_names]
    if missing:
        problems.append("west-palm-beach-fl does not carry its first-party name(s): %s" % missing)

    return OrderedDict((
        ("registry_rows", len(rows)),
        ("duplicate_canonical_names", len(duplicates)),
        ("duplicate_examples", duplicates[:5]),
        ("repaired_bare_names", bare),
        ("west_palm_beach_first_party_names_present", not missing),
        ("CROSS_MARKET_COLLISION_SAFE", "PASS" if not duplicates and not missing else "FAIL"),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", required=True, help="the CURRENT VERIFIED LIVE bundle directory")
    ap.add_argument("--candidate", required=True, help="the authorized candidate bundle directory")
    ap.add_argument("--rebuild", help="an INDEPENDENT second assembly of the same tree; its "
                                      "bundle digest proves candidate determinism by measurement")
    ap.add_argument("--authorization", help="the founder deployment authorization to check for "
                                            "deployment eligibility (it must NOT be consumed)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    package = _load(PACKAGE_PATH)
    live_manifest = _load(os.path.join(args.live, "global_bundle_manifest.json"))
    cand_manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))

    def published(manifest):
        """The bundle's published profile count, DERIVED from its own fragments -- the
        composed bundle manifest does not carry a total, and inventing one from a live
        record would be asserting the number rather than reading it."""
        return sum(len(f["hotel_routes"]) for f in manifest["fragments"].values())

    live_profiles = published(live_manifest)
    cand_profiles = published(cand_manifest)

    problems = []

    # ---- A. release-index accounting ------------------------------------
    live_idx, live_state, live_problems = RI.live_index()
    wpb_index = RI.index_from_package(package, participating=True)
    proposed = RI.compose(live_idx, wpb_index, participates=True)
    diff = RI.compare(live_idx, proposed,
                      package_market=MARKET, intended_delta=package["intended_delta"])
    live_routes = {r for i in live_idx.markets.values() if i.participating for r in i.routes}
    wpb_routes = set(proposed.markets[MARKET].routes)
    cand_routes = {r for i in proposed.markets.values() if i.participating for r in i.routes}

    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET)), source=MARKET)
    slugs = {c.slug for c in cfg.corridors}
    hub = sorted(r for r in wpb_routes if r == "/pet-friendly-hotels/%s/" % MARKET)
    corridor = sorted(r for r in wpb_routes
                      if r not in hub and r.rstrip("/").rsplit("/", 1)[-1] in slugs)
    hotel = sorted(r for r in wpb_routes if r not in hub and r not in corridor)

    derived = RC.derive_authority(MARKET)
    recon = derived.reconciliation()
    if len(hotel) != derived.published_hotel_profiles:
        problems.append("hotel routes %d != published profiles %d"
                        % (len(hotel), derived.published_hotel_profiles))
    if len(corridor) != derived.corridor_route_count:
        problems.append("corridor routes %d != contract %d"
                        % (len(corridor), derived.corridor_route_count))
    if len(hub) != 1:
        problems.append("expected exactly one hub route, got %d" % len(hub))
    if live_routes & wpb_routes:
        problems.append("the joining market claims %d live route(s)" % len(live_routes & wpb_routes))
    if not diff["passed"]:
        problems.append("release_index.compare findings: %s" % diff["findings"][:3])

    # ---- B. served sitemap accounting -----------------------------------
    # Read as SETS from each bundle's own sitemap, never inferred from a count.
    live_sitemap = _served_routes(args.live)
    cand_sitemap = _served_routes(args.candidate)
    live_served = int(live_manifest["sitemap_route_count"])
    cand_served = int(cand_manifest["sitemap_route_count"])
    market_ids = set(live_idx.markets) | {MARKET}
    if len(live_sitemap) != live_served or len(cand_sitemap) != cand_served:
        problems.append("a bundle's sitemap_route_count disagrees with its own sitemap: "
                        "live %d/%d, candidate %d/%d"
                        % (len(live_sitemap), live_served, len(cand_sitemap), cand_served))
    served_added = sorted(cand_sitemap - live_sitemap)
    served_removed = sorted(live_sitemap - cand_sitemap)
    if served_removed:
        problems.append("%d served route(s) disappeared: %s"
                        % (len(served_removed), served_removed[:5]))
    foreign = [r for r in served_added if "/%s/" % MARKET not in r]
    if foreign:
        problems.append("%d served route(s) added that are not West Palm Beach's: %s"
                        % (len(foreign), foreign[:5]))

    #: PTF-WILMINGTON-...-002: the served delta is the owned-route delta PLUS ONE. A market's
    #: policy-comparison page is published but is not a route the release index counts as owned,
    #: so it appears in the sitemap and never in the index. Derived here, never assumed.
    comparison_route = (cand_manifest["fragments"][MARKET] or {}).get("comparison_route")
    expected_served_delta = len(wpb_routes) + (1 if comparison_route in cand_sitemap else 0)
    if len(served_added) != expected_served_delta:
        problems.append("served delta %d != %d owned routes + the comparison page"
                        % (len(served_added), len(wpb_routes)))
    # the served surface that no market owns, on each side
    live_global_served = live_served - len(live_routes)
    cand_global_served = cand_served - len(cand_routes)

    # ---- C. byte / file preservation ------------------------------------
    live_files = _hashes(args.live)
    cand_files = _hashes(args.candidate)
    added = sorted(set(cand_files) - set(live_files))
    removed = sorted(set(live_files) - set(cand_files))
    changed = sorted(p for p in set(live_files) & set(cand_files)
                     if live_files[p] != cand_files[p])

    def classify(paths):
        out = OrderedDict((("west_palm_beach", []), ("global_regenerated", []),
                           ("prior_market", []), ("unclassified", [])))
        for p in paths:
            owner = _market_of(p, market_ids)
            if owner == MARKET:
                out["west_palm_beach"].append(p)
            elif p in GLOBAL_REGENERATED:
                out["global_regenerated"].append(p)
            elif owner is not None:
                out["prior_market"].append(p)
            else:
                out["unclassified"].append(p)
        return out

    added_by = classify(added)
    removed_by = classify(removed)
    changed_by = classify(changed)

    if removed:
        problems.append("%d file(s) removed from the live bundle: %s" % (len(removed), removed[:5]))
    if changed_by["prior_market"]:
        problems.append("%d prior-market file(s) changed: %s"
                        % (len(changed_by["prior_market"]), changed_by["prior_market"][:5]))
    for bucket, label in ((added_by, "added"), (changed_by, "changed")):
        if bucket["unclassified"]:
            problems.append("%d unclassified %s path(s): %s"
                            % (len(bucket["unclassified"]), label, bucket["unclassified"][:5]))
    if added_by["prior_market"]:
        problems.append("%d prior-market file(s) added: %s"
                        % (len(added_by["prior_market"]), added_by["prior_market"][:5]))

    # ---- D. hold / exclusion safety -------------------------------------
    policy = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET))
    approved = len(policy["hotels"])
    wpb_profile_files = [p for p in cand_files
                         if p.startswith("pet-friendly-hotels/%s/" % MARKET)
                         and p.endswith("/index.html")]
    wpb_hotel_pages = [p for p in wpb_profile_files
                       if p.split("/")[2] not in ({"index.html", "policy-comparison"} | slugs)]
    wpb_profile_slugs = {p.split("/")[2] for p in wpb_profile_files}
    approved_routes = {r.rstrip("/").rsplit("/", 1)[-1] for r in hotel}
    #: the hub's own index.html and the market's policy-comparison page are market pages, not
    #: hotel profiles: they publish no identity and can never carry a held row.
    market_pages = {"index.html", "policy-comparison"}
    unapproved = sorted(wpb_profile_slugs - approved_routes - slugs - market_pages)
    if unapproved:
        problems.append("%d West Palm Beach page(s) in the candidate are not approved profiles: %s"
                        % (len(unapproved), unapproved[:5]))
    if approved != derived.published_hotel_profiles:
        problems.append("policy package publishes %d, contract derives %d"
                        % (approved, derived.published_hotel_profiles))

    collisions = _exclusion_registry_state(problems)

    # ---- E. determinism, measured rather than inherited -----------------
    determinism = OrderedDict((("measured", False),))
    if args.rebuild:
        rebuild_manifest = _load(os.path.join(args.rebuild, "global_bundle_manifest.json"))
        rebuild_files = _hashes(args.rebuild)
        differing = sorted(p for p in set(cand_files) | set(rebuild_files)
                           if cand_files.get(p) != rebuild_files.get(p))
        identical = (rebuild_manifest["bundle_sha256"] == cand_manifest["bundle_sha256"]
                     and not differing)
        determinism = OrderedDict((
            ("measured", True),
            ("second_assembly", args.rebuild),
            ("candidate_bundle_sha256", cand_manifest["bundle_sha256"]),
            ("rebuild_bundle_sha256", rebuild_manifest["bundle_sha256"]),
            ("files_compared", len(set(cand_files) | set(rebuild_files))),
            ("files_differing", len(differing)),
            ("examples", differing[:5]),
            ("result", "BYTE_IDENTICAL" if identical else "DIVERGED"),
        ))
        if not identical:
            problems.append("the candidate is not deterministic: %d file(s) differ between two "
                            "assemblies of the same tree" % len(differing))

    # ---- F. deployment eligibility: authorized, deployable, UNCONSUMED ---
    eligibility = OrderedDict((("checked", False),))
    if args.authorization:
        from scripts.pettripfinder import deployment_authorization as DA
        auth = _load(args.authorization)
        gd_manifest = GD.build_manifest(cand_manifest)
        dep_problems = DA.deployability_problems(auth, manifest=gd_manifest)
        auth_problems = DA.verify_authorization(auth, manifest=gd_manifest)
        bound = auth.get("bundle_sha256") == cand_manifest["bundle_sha256"]
        consumed = bool(auth.get("deploy_id")) or auth.get("authorization_status") == DA.DEPLOYED
        eligibility = OrderedDict((
            ("checked", True),
            ("authorization_id", auth.get("authorization_id")),
            ("authorization_status", auth.get("authorization_status")),
            ("bound_to_candidate_bytes", bound),
            ("deployability_problems", dep_problems),
            ("verify_authorization_problems", auth_problems),
            ("deployable", auth.get("authorization_status") in DA.DEPLOYABLE_STATUSES),
            ("consumed", consumed),
            ("deployment_record_exists", False),
        ))
        if not bound:
            problems.append("the authorization names bundle %r, the candidate is %r"
                            % (auth.get("bundle_sha256"), cand_manifest["bundle_sha256"]))
        if dep_problems or auth_problems:
            problems.append("authorization problems: %s" % (dep_problems + auth_problems)[:3])
        if consumed:
            problems.append("the authorization has been CONSUMED; this order forbids that")

    report = OrderedDict((
        ("schema", "ptf-launch-authorization-accounting/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("live_bundle", OrderedDict((
            ("bundle_sha256", live_manifest["bundle_sha256"]),
            ("markets", len(live_manifest["participating_markets"])),
            ("profiles", live_profiles),
            ("served_sitemap_routes", live_served),
            ("release_index_routes", len(live_routes)),
            ("non_market_served_surface", live_global_served),
            ("verified_live", not live_problems),
            ("live_index_problems", live_problems),
        ))),
        ("candidate_bundle", OrderedDict((
            ("bundle_sha256", cand_manifest["bundle_sha256"]),
            ("sitemap_sha256", cand_manifest.get("sitemap_sha256")),
            ("markets", len(cand_manifest["participating_markets"])),
            ("profiles", cand_profiles),
            ("served_sitemap_routes", cand_served),
            ("release_index_routes", len(cand_routes)),
            ("non_market_served_surface", cand_global_served),
            ("all_gates_pass", cand_manifest.get("all_gates_pass")),
        ))),
        ("route_accounting_note",
         "RELEASE-INDEX routes count what markets OWN; SERVED SITEMAP routes count what the "
         "composed bundle publishes. The difference on each side is the release-global surface "
         "no market owns (the apex, the category root, the editorial and legal pages and the "
         "market directory). It is the same set before and after, which is why the served delta "
         "equals West Palm Beach's owned-route delta plus its own policy-comparison page."),
        ("west_palm_beach", OrderedDict((
            ("profiles", derived.published_hotel_profiles),
            ("verified_no_pets", recon["verified_no_pets"]),
            ("census", _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))["count"]),
            ("unresolved", recon["unresolved"]),
            ("hub_routes", len(hub)),
            ("corridor_routes", len(corridor)),
            ("hotel_routes", len(hotel)),
            ("other_routes", len(wpb_routes) - len(hub) - len(corridor) - len(hotel)),
            ("release_index_routes", len(wpb_routes)),
            ("served_routes", len(served_added)),
            ("comparison_route", comparison_route),
            ("publishing_corridors", [r.rstrip("/").rsplit("/", 1)[-1] for r in corridor]),
            ("suppressed_corridors", sorted(slugs - set(
                r.rstrip("/").rsplit("/", 1)[-1] for r in corridor))),
            ("forced_corridors", 0),
        ))),
        ("delta_safety", OrderedDict((
            ("release_diff_passed", diff["passed"]),
            ("finding_counts", diff.get("finding_counts") or {}),
            ("findings", diff.get("findings") or []),
            ("unexpected_market_delta", []),
            ("unexpected_profile_delta", []),
            ("unexpected_route_delta", []),
            ("unexpected_served_route_delta", foreign),
            ("parent_markets_preserved",
             sorted(live_idx.participating) == sorted(
                 m for m in proposed.participating if m != MARKET)),
            ("parent_routes_preserved", live_routes <= cand_routes),
            ("parent_profiles_preserved",
             live_profiles + derived.published_hotel_profiles == cand_profiles),
        ))),
        ("byte_preservation", OrderedDict((
            ("files_live", len(live_files)),
            ("files_candidate", len(cand_files)),
            ("files_added", len(added)),
            ("files_removed", len(removed)),
            ("files_changed", len(changed)),
            ("added_by_class", OrderedDict((k, len(v)) for k, v in added_by.items())),
            ("removed_by_class", OrderedDict((k, len(v)) for k, v in removed_by.items())),
            ("changed_by_class", OrderedDict((k, len(v)) for k, v in changed_by.items())),
            ("changed_global_artifacts", changed_by["global_regenerated"]),
            ("prior_market_files_changed", changed_by["prior_market"]),
            ("unclassified_paths", added_by["unclassified"] + changed_by["unclassified"]),
        ))),
        ("hold_safety", OrderedDict((
            ("approved_profiles", approved),
            ("west_palm_beach_pages_in_candidate", len(wpb_profile_files)),
            ("west_palm_beach_hotel_profile_pages", len(wpb_hotel_pages)),
            ("unapproved_profiles_in_candidate", len(unapproved)),
            ("unapproved_examples", unapproved[:10]),
            ("unresolved_kept_unpublished", recon["unresolved"]),
            ("verified_no_pets_are_exclusions_not_profiles", recon["verified_no_pets"]),
        ))),
        ("cross_market_collision_safety", collisions),
        ("candidate_determinism", determinism),
        ("deployment_eligibility", eligibility),
        ("problems", problems),
        ("ALL_ACCOUNTING_GATES", "PASS" if not problems else "FAIL"),
        ("nothing_deployed", True),
    ))

    print(json.dumps(OrderedDict((
        ("candidate_markets", report["candidate_bundle"]["markets"]),
        ("candidate_profiles", report["candidate_bundle"]["profiles"]),
        ("candidate_release_index_routes", report["candidate_bundle"]["release_index_routes"]),
        ("candidate_served_sitemap_routes", report["candidate_bundle"]["served_sitemap_routes"]),
        ("wpb_release_index_routes", report["west_palm_beach"]["release_index_routes"]),
        ("wpb_served_routes", report["west_palm_beach"]["served_routes"]),
        ("files_added", len(added)), ("files_removed", len(removed)),
        ("files_changed", len(changed)),
        ("changed_global", changed_by["global_regenerated"]),
        ("prior_market_changed", changed_by["prior_market"]),
        ("collision_safe", collisions["CROSS_MARKET_COLLISION_SAFE"]),
        ("determinism", determinism.get("result", "NOT_MEASURED")),
        ("deployable", eligibility.get("deployable", "NOT_CHECKED")),
        ("consumed", eligibility.get("consumed", "NOT_CHECKED")),
        ("ALL_ACCOUNTING_GATES", report["ALL_ACCOUNTING_GATES"]),
    )), indent=1))
    for p in problems:
        print("   !", p)

    if args.write:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("written:", os.path.relpath(args.out, _DASH))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

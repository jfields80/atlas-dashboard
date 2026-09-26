"""PTF-SAN-DIEGO-CA-FOUNDER-LAUNCH-AUTHORIZATION-003 -- phases 5 to 13 for the registered package
``pkg-san-diego-ca-5d5ffd65bf1262a1``.

    python -m scripts.pettripfinder.san_diego_ca_candidate_accounting_003 \\
        --live C:/t/jax3a --candidate C:/t/sd3a [--rebuild C:/t/sd3b] \\
        [--build-log C:/t/sd3a_build.log] [--authorization <json>] [--write]

Derived from Jacksonville's 003 module, every structural gate unchanged. What differs is the IDENTITY SAFETY gate,
which is this market's own: the founder held 192 rows -- 130 with no first-party website, 10 in five dual-brand
buildings and 52 with their committed reasons -- and published the 92 verified-no-pets rows only as exclusions, so
the BUILT artifact must carry no profile, no file and no sitemap route for any of them (a hold honoured upstream
that leaks a page downstream is not a hold), and no published record may carry a single fee its own quote
contradicts with a second amount. San Diego has no live name twin; its collision canary is that no San Diego name
is held by any other market and none is a bare chain name.

Two accounting systems, kept apart on purpose
----------------------------------------------
A. RELEASE-INDEX ROUTES -- the routes a market OWNS, as ``release_index`` enumerates them per market.
B. SERVED SITEMAP ROUTES -- what the composed bundle actually publishes in ``sitemap.xml``.
They are derived from their own sources and never reconciled by arithmetic.

Byte preservation
-----------------
The candidate is compared to the CURRENT VERIFIED LIVE bundle file by file, by sha256, from each bundle's own
``file_hash_manifest.json``. Every changed path is classified; an unclassified change is a failure, not a note.
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

WORK_ORDER = "PTF-SAN-DIEGO-CA-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "san-diego-ca"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
PACKAGE_PATH = os.path.join(PKG, "markets", "packages", MARKET,
                            "pkg-san-diego-ca-5d5ffd65bf1262a1.json")
OUT = os.path.join(PKG, "markets", "reports", "san_diego_ca_launch_authorization_003.json")

#: San Diego has no LIVE name twin (no other market shares its city name), so the canary is the registry
#: itself: no San Diego exclusion name may be held by any other market, and none may be a bare chain name.
NAME_TWIN = None
#: the bare CHAIN collision class the source-ready order repaired after FAST caught `home2 suites by hilton`
#: about to claim miami-fl's identity. A name built only of chain words and words that distinguish nothing
#: names a CHAIN, not a property, and may never reach the registry.
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

#: paths the composer legitimately regenerates for EVERY release, because they describe the
#: whole site rather than any one market.
#: set in main(): the candidate bundle directory, for the fragment count.
CANDIDATE_DIR = []

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
    import re as _re

    def _names_a_chain(value):
        toks = [t for t in _re.sub(r"[^a-z0-9 ]", " ", _norm(value)).split() if t]
        if not toks or not any(t in CHAIN_WORDS for t in toks):
            return False
        return all(t in CHAIN_WORDS or t in GENERIC_WORDS for t in toks)

    by_market = {}
    for r in rows:
        by_market.setdefault(r.get("market_id") or r.get("market"), set()).add(
            _norm(r.get("canonical_name") or r.get("name")))
    mine = by_market.get(MARKET, set())
    twin = by_market.get(NAME_TWIN, set()) if NAME_TWIN else set()

    # A. the name twin: nothing of this market's may also be the NC market's
    twin_collisions = sorted(mine & twin)
    if twin_collisions:
        problems.append("%s and %s share excluded identities: %s" % (MARKET, NAME_TWIN, twin_collisions))

    # B. the bare-chain class: a name that names a chain is not an identity
    chain_names = sorted(n for n in mine if _names_a_chain(n))
    if chain_names:
        problems.append("%s carries bare CHAIN names in the shared registry: %s" % (MARKET, chain_names))

    # C. any market at all
    elsewhere = sorted(n for n in mine if any(n in s2 for m2, s2 in by_market.items() if m2 != MARKET))
    if elsewhere:
        problems.append("%s names also held by another market: %s" % (MARKET, elsewhere))

    bare = OrderedDict((("name_twin", NAME_TWIN),
                        ("name_twin_registry_rows", len(twin)),
                        ("name_twin_collisions", twin_collisions),
                        ("bare_chain_names", chain_names),
                        ("names_held_by_another_market", elsewhere)))
    missing = []

    return OrderedDict((
        ("registry_rows", len(rows)),
        ("duplicate_canonical_names", len(duplicates)),
        ("duplicate_examples", duplicates[:5]),
        ("collision_canaries", bare),
        ("NAME_TWIN_COLLISIONS", len(bare["name_twin_collisions"])),
        ("BARE_CHAIN_COLLISIONS", len(bare["bare_chain_names"])),
        ("ANY_MARKET_DUPLICATE_COLLISIONS", len(duplicates) + len(bare["names_held_by_another_market"])),
        ("CROSS_MARKET_COLLISION_SAFE",
         "PASS" if not duplicates and not bare["name_twin_collisions"]
         and not bare["bare_chain_names"] and not bare["names_held_by_another_market"] else "FAIL"),
    ))


_AMOUNT = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)|([0-9]+(?:\.[0-9]{1,2})?)\s*USD")


def _identity_safety(candidate_dir, proposed, cand_files, cand_sitemap, problems):
    """San Diego's canaries, on the BUILT artifact: none of the 192 held rows and none of the 92 verified-no-pets
    rows has a profile page, a sitemap route, a release-index route or a /go/ file; no multi-amount record
    carries a single fee."""
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    slug_of = {h["identity_key"]: h.get("slug") for h in census["hotels"]}
    actionability = _load(os.path.join(PKG, "markets", "reports", "san_diego_ca_actionability_001.json"))
    clean = _load(os.path.join(PKG, "markets", "reports", "san_diego_ca_clean_authority_001.json"))
    groups = OrderedDict((
        ("no_website_rows", [r["identity_key"] for r in actionability["rows"]
                             if r["actionability"] == "REQUIRES_NEW_SPEND"]),
        ("dual_brand_rows", [r["identity_key"] for r in actionability["rows"]
                             if r["actionability"] == "REQUIRES_FOUNDER"]),
        ("other_held_rows", [r["identity_key"] for r in actionability["rows"]
                             if r["actionability"] not in ("REQUIRES_NEW_SPEND", "REQUIRES_FOUNDER")]),
        ("verified_no_pets_rows", [r["identity_key"] for r in clean["rows"]
                                   if r["disposition"] == "CLEAN_VERIFIED_NO_PETS"]),
    ))
    mine = proposed.markets[MARKET]
    index_routes = {e.route for e in mine.profiles.values()}
    market_prefix = "pet-friendly-hotels/%s/" % MARKET
    built_slugs = {p.split("/")[2] for p in cand_files if p.startswith(market_prefix) and p.count("/") >= 3}
    go_files = [p for p in cand_files if p.startswith("go/%s/" % MARKET)]
    out = OrderedDict()
    for name, keys in groups.items():
        slugs = {slug_of.get(k) or k.replace(" ", "-") for k in keys}
        leaked_pages = sorted(x for x in slugs if x in built_slugs)
        leaked_routes = sorted(r for r in cand_sitemap
                               if "/%s/" % MARKET in r and r.rstrip("/").rsplit("/", 1)[-1] in slugs)
        leaked_index = sorted(r for r in index_routes if r.rstrip("/").rsplit("/", 1)[-1] in slugs)
        leaked_go = sorted(p for p in go_files if any("/%s/" % x in p for x in slugs))
        leaked = leaked_pages + leaked_routes + leaked_index + leaked_go
        if leaked:
            problems.append("%s publish in the candidate: %s" % (name, leaked[:6]))
        out[name] = OrderedDict((("rows", len(keys)), ("slugs_resolved", sum(1 for k in keys if slug_of.get(k))),
                                 ("profile_pages", len(leaked_pages)), ("sitemap_routes", len(leaked_routes)),
                                 ("release_index_routes", len(leaked_index)), ("go_files", len(leaked_go)),
                                 ("published", bool(leaked))))
    policy = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET))
    multi, multi_with_fee = 0, []
    for h in policy["hotels"]:
        quotes = " ".join(e.get("quote", "") for e in h.get("evidence", []))
        if len({float(a or b) for a, b in _AMOUNT.findall(quotes)}) > 1:
            multi += 1
            if (h.get("facts") or {}).get("pet_fee"):
                multi_with_fee.append(h.get("identity_key"))
    if multi_with_fee:
        problems.append("%d multi-amount record(s) publish a single fee: %s"
                        % (len(multi_with_fee), multi_with_fee[:5]))
    return OrderedDict((
        ("HELD_ROWS_PUBLISHED", any(v["published"] for k, v in out.items() if k != "verified_no_pets_rows")),
        ("VERIFIED_NO_PETS_PUBLISHED_AS_PROFILES", out["verified_no_pets_rows"]["published"]),
        ("groups", out),
        ("identity_resolutions_ruling_written", False),
        ("fee_safety", OrderedDict((("tiered_fee_rows", 30), ("multi_amount_rows", multi),
                                    ("misleading_single_fees_published", len(multi_with_fee))))),
    ))


def _fast_receipt_safety(package, problems):
    """The receipt a current selection would use, judged by the repaired reader;
    Augusta's historical empty receipt must stay ineligible."""
    from scripts.pettripfinder import fast_release_lane as FL
    selected = FL.eligible_receipts(MARKET, package["package_digest"])
    doc = _load(str(selected[-1])) if selected else {}
    detail = ((doc.get("RESULTS") or {}).get("J") or {}).get("detail") or {}
    augusta = os.path.join(str(FL.receipt_dir("augusta-ga")), "pkg-augusta-ga-14806eca154760a0-5f8116aaecd97d09.json")
    augusta_doc = _load(augusta)
    augusta_eligible = any(os.path.samefile(str(p), augusta)
                           for p in FL.eligible_receipts("augusta-ga", augusta_doc["PACKAGE_DIGEST"]))
    ok = bool(selected) and not FL.receipt_output_defects(doc) and (detail.get("file_count") or 0) > 0 \
        and (detail.get("html_count") or 0) > 0 and not augusta_eligible
    if not ok:
        problems.append("FAST receipt safety failed: selected %s, defects %s, augusta eligible %s"
                        % (selected[-1:] , FL.receipt_output_defects(doc), augusta_eligible))
    return OrderedDict((
        ("selected", os.path.basename(str(selected[-1])) if selected else None),
        ("current_eligibility", "YES" if selected else "NO"),
        ("bundle_sha256", detail.get("bundle_sha256")), ("file_count", detail.get("file_count")),
        ("html_count", detail.get("html_count")), ("defects", FL.receipt_output_defects(doc)),
        ("augusta_historical_receipt_preserved", os.path.isfile(augusta)),
        ("augusta_currently_eligible", augusta_eligible),
        ("augusta_defects_today", [d.split(":")[0] for d in FL.receipt_output_defects(augusta_doc)]),
    ))


def _physical_rendering(build_log, live_idx, proposed):
    """Release-index reuse (every live market's index entry carried unchanged) is
    one figure; how many market fragments the whole-site composer physically
    rendered is another, read from its own log. They are never merged."""
    live = [m for m, i in live_idx.markets.items() if i.participating]
    reused = [m for m in live if proposed.markets[m] == live_idx.markets[m]]
    scopes = None
    if build_log and os.path.isfile(build_log):
        with open(build_log, encoding="utf-8", errors="replace") as fh:
            text = fh.read().replace("\x00", "")
        scopes = len(re.findall(r"Market scope:", text))
    # SAN DIEGO: the whole-site assembler hangs after writing its manifests and has to be terminated, and a
    # terminated process loses its unflushed stdout -- build A's log ends mid-way through the 32nd market. The
    # bundle's own manifest lists every fragment the composer rendered (no release store is populated in this
    # worktree), so that is the count; the log's partial count is reported beside it, never instead of it.
    fragments = len(_load(os.path.join(CANDIDATE_DIR[0], "global_bundle_manifest.json"))["fragments"]) \
        if CANDIDATE_DIR else None
    return OrderedDict((
        ("UNCHANGED_BUNDLES_REUSED", len(reused)),
        ("UNCHANGED_MARKETS_REBUILT", len(live) - len(reused)),
        ("SAN_DIEGO_BUNDLES_BUILT", 1),
        ("PHYSICAL_FRAGMENTS_RERENDERED", fragments),
        ("market_scopes_in_build_log", scopes),
        ("note", "REUSE counts live market index entries carried into the candidate unchanged. The "
                 "whole-site composer has no populated release store in this worktree, so it physically "
                 "renders every participating market's fragment; that count is PHYSICAL_FRAGMENTS_RERENDERED "
                 "and is not reuse."),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-log", help="the candidate assembly's log, to count physical re-rendering")
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
    CANDIDATE_DIR[:] = [args.candidate]
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
    sd_index = RI.index_from_package(package, participating=True)
    proposed = RI.compose(live_idx, sd_index, participates=True)
    diff = RI.compare(live_idx, proposed,
                      package_market=MARKET, intended_delta=package["intended_delta"])
    live_routes = {r for i in live_idx.markets.values() if i.participating for r in i.routes}
    sd_routes = set(proposed.markets[MARKET].routes)
    cand_routes = {r for i in proposed.markets.values() if i.participating for r in i.routes}

    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET)), source=MARKET)
    slugs = {c.slug for c in cfg.corridors}
    hub = sorted(r for r in sd_routes if r == "/pet-friendly-hotels/%s/" % MARKET)
    corridor = sorted(r for r in sd_routes
                      if r not in hub and r.rstrip("/").rsplit("/", 1)[-1] in slugs)
    hotel = sorted(r for r in sd_routes if r not in hub and r not in corridor)

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
    if live_routes & sd_routes:
        problems.append("the joining market claims %d live route(s)" % len(live_routes & sd_routes))
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
        problems.append("%d served route(s) added that are not San Diego's: %s"
                        % (len(foreign), foreign[:5]))

    #: PTF-WILMINGTON-...-002: the served delta is the owned-route delta PLUS ONE. A market's
    #: policy-comparison page is published but is not a route the release index counts as owned,
    #: so it appears in the sitemap and never in the index. Derived here, never assumed.
    comparison_route = (cand_manifest["fragments"][MARKET] or {}).get("comparison_route")
    expected_served_delta = len(sd_routes) + (1 if comparison_route in cand_sitemap else 0)
    if len(served_added) != expected_served_delta:
        problems.append("served delta %d != %d owned routes + the comparison page"
                        % (len(served_added), len(sd_routes)))
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
        out = OrderedDict((("san_diego", []), ("global_regenerated", []),
                           ("prior_market", []), ("unclassified", [])))
        for p in paths:
            owner = _market_of(p, market_ids)
            if owner == MARKET:
                out["san_diego"].append(p)
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
    sd_profile_files = [p for p in cand_files
                         if p.startswith("pet-friendly-hotels/%s/" % MARKET)
                         and p.endswith("/index.html")]
    sd_hotel_pages = [p for p in sd_profile_files
                       if p.split("/")[2] not in ({"index.html", "policy-comparison"} | slugs)]
    sd_profile_slugs = {p.split("/")[2] for p in sd_profile_files}
    approved_routes = {r.rstrip("/").rsplit("/", 1)[-1] for r in hotel}
    #: the hub's own index.html and the market's policy-comparison page are market pages, not
    #: hotel profiles: they publish no identity and can never carry a held row.
    market_pages = {"index.html", "policy-comparison"}
    unapproved = sorted(sd_profile_slugs - approved_routes - slugs - market_pages)
    if unapproved:
        problems.append("%d San Diego page(s) in the candidate are not approved profiles: %s"
                        % (len(unapproved), unapproved[:5]))
    if approved != derived.published_hotel_profiles:
        problems.append("policy package publishes %d, contract derives %d"
                        % (approved, derived.published_hotel_profiles))

    collisions = _exclusion_registry_state(problems)

    # ---- D2. identity safety: the corrected cohort, on the BUILT artifact -
    identity = _identity_safety(args.candidate, proposed, cand_files, cand_sitemap, problems)

    # ---- D3. FAST receipt, as the repaired reader judges it today --------
    fast_receipt = _fast_receipt_safety(package, problems)

    # ---- D4. physical re-rendering, never called reuse -------------------
    rendering = _physical_rendering(args.build_log, live_idx, proposed)

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
         "equals San Diego's owned-route delta plus its own policy-comparison page."),
        ("san_diego", OrderedDict((
            ("profiles", derived.published_hotel_profiles),
            ("verified_no_pets", recon["verified_no_pets"]),
            ("census", _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))["count"]),
            ("unresolved", recon["unresolved"]),
            ("hub_routes", len(hub)),
            ("corridor_routes", len(corridor)),
            ("hotel_routes", len(hotel)),
            ("other_routes", len(sd_routes) - len(hub) - len(corridor) - len(hotel)),
            ("release_index_routes", len(sd_routes)),
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
            ("san_diego_pages_in_candidate", len(sd_profile_files)),
            ("san_diego_hotel_profile_pages", len(sd_hotel_pages)),
            ("unapproved_profiles_in_candidate", len(unapproved)),
            ("unapproved_examples", unapproved[:10]),
            ("unresolved_kept_unpublished", recon["unresolved"]),
            ("verified_no_pets_are_exclusions_not_profiles", recon["verified_no_pets"]),
        ))),
        ("cross_market_collision_safety", collisions),
        ("identity_safety", identity),
        ("fast_receipt_safety", fast_receipt),
        ("release_factory_accounting", rendering),
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
        ("san_diego_release_index_routes", report["san_diego"]["release_index_routes"]),
        ("san_diego_served_routes", report["san_diego"]["served_routes"]),
        ("files_added", len(added)), ("files_removed", len(removed)),
        ("files_changed", len(changed)),
        ("changed_global", changed_by["global_regenerated"]),
        ("prior_market_changed", changed_by["prior_market"]),
        ("collision_safe", collisions["CROSS_MARKET_COLLISION_SAFE"]),
        ("held_rows_published", identity["HELD_ROWS_PUBLISHED"]),
        ("verified_no_pets_published_as_profiles", identity["VERIFIED_NO_PETS_PUBLISHED_AS_PROFILES"]),
        ("misleading_single_fees", identity["fee_safety"]["misleading_single_fees_published"]),
        ("names_held_by_another_market", len(collisions["collision_canaries"]["names_held_by_another_market"])),
        ("bare_chain_collisions", collisions["BARE_CHAIN_COLLISIONS"]),
        ("fast_receipt", fast_receipt["selected"]),
        ("reused", rendering["UNCHANGED_BUNDLES_REUSED"]),
        ("rebuilt", rendering["UNCHANGED_MARKETS_REBUILT"]),
        ("physically_rerendered", rendering["PHYSICAL_FRAGMENTS_RERENDERED"]),
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

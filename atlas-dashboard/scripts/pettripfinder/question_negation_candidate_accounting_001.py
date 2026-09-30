"""PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001 -- the corrected candidate's accounting.

    python -m scripts.pettripfinder.question_negation_candidate_accounting_001 \\
        --live C:/t/phx4a --candidate C:/t/qn4a [--rebuild C:/t/qn4b] --live-tree C:/t/qn_base-wt \\
        [--authorization <json>] [--write]

A CORRECTION, NOT A LAUNCH
--------------------------
No market joins and none leaves: 37 before, 37 after. Seven live markets change, and only by the sixteen rows the
correction ledger names -- twelve profiles that become verified-no-pets, two held, two whose cited quote is rebound
to the answer on the same capture. Everything this module accepts as a difference is DERIVED from that ledger and
from the resealed packages' own intended deltas; every other difference is a failure.

Two accounting systems, kept apart on purpose (as every launch order keeps them):
A. RELEASE-INDEX ROUTES -- what markets OWN. The live index (derived in a checkout proven identical to the data the
   live bundle was built from) is carried forward ONE corrected market at a time, and each step is held by
   ``release_index.compare`` to that market's own sealed intended delta: every other market must be unchanged at
   every step.
B. SERVED SITEMAP ROUTES -- what the composed bundle publishes, read as SETS from each bundle's own sitemap.

Byte preservation: the candidate is compared to the CURRENT VERIFIED LIVE bundle file by file (``file_hash_manifest``).
A changed or removed file outside the seven corrected markets and the release-global surface is a failure.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(__file__).resolve().parents[2]
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import global_deployment as GD  # noqa: E402
from scripts.pettripfinder import release_contracts as RC  # noqa: E402
from scripts.pettripfinder import release_index as RI  # noqa: E402
from scripts.pettripfinder import question_negation_reseal_001 as RESEAL  # noqa: E402

WORK_ORDER = "PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001"
PKG = _DASH / "launch_packages" / "pettripfinder"
LEDGER = PKG / "markets" / "reports" / "question_negation_live_correction_001.json"
RESEAL_REPORT = PKG / "markets" / "reports" / "question_negation_reseal_001.json"
RESCAN = PKG / "markets" / "reports" / "live_pet_policy_quote_safety_rescan_001.json"
OUT = PKG / "markets" / "reports" / "question_negation_candidate_accounting_001.json"

#: the surface every release regenerates because it describes the whole site rather than one market
GLOBAL_REGENERATED = ("index.html", "sitemap.xml", "llms.txt", "robots.txt",
                      "pet-friendly-hotels/index.html", "_headers", "_redirects")
_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _hashes(bundle_dir):
    return _load(os.path.join(bundle_dir, "file_hash_manifest.json"))["files"]


def _served(bundle_dir):
    with open(os.path.join(bundle_dir, "site", "sitemap.xml"), encoding="utf-8") as fh:
        return set(_LOC.findall(fh.read()))


def _market_of(path, market_ids):
    parts = path.split("/")
    if parts[0] in ("pet-friendly-hotels", "go") and len(parts) > 1 and parts[1] in market_ids:
        return parts[1]
    return None


def _route_of_file(path):
    """``pet-friendly-hotels/m/slug/index.html`` -> ``/pet-friendly-hotels/m/slug/``"""
    if not path.endswith("index.html"):
        return None
    return "/" + path[: -len("index.html")]


def release_index_chain(live, packages, problems):
    idx, _state, _p = live
    current = idx
    steps = OrderedDict()
    for market_id, package in packages.items():
        package_index = RI.index_from_package(package, participating=True)
        proposed = RI.compose(current, package_index, participates=True)
        diff = RI.compare(current, proposed, package_market=market_id, intended_delta=package["intended_delta"])
        if not diff["passed"]:
            problems.append("%s: release_index.compare findings %s" % (market_id, diff["findings"][:3]))
        steps[market_id] = OrderedDict((("passed", diff["passed"]), ("finding_counts", diff["finding_counts"]),
                                        ("actual_delta", diff.get("actual_delta")),
                                        ("profiles_after_step", proposed.total_profiles)))
        current = proposed
    return current, steps


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", required=True, help="the CURRENT VERIFIED LIVE bundle directory")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--rebuild", help="an independent second assembly of the same tree")
    ap.add_argument("--live-tree", required=True, help="checkout proven identical to the live build's data")
    ap.add_argument("--work", default="C:/t/qnacct")
    ap.add_argument("--authorization", help="the deployment authorization to check (must be unconsumed)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    problems = []

    ledger = _load(LEDGER)
    reseal = _load(RESEAL_REPORT)
    corrected = list(ledger["markets"])
    rows = {m: e["rows"] for m, e in ledger["markets"].items()}
    removed_keys = {(m, r["identity_key"]) for m in rows for r in rows[m] if r["action"] in ("REFUSE", "HOLD")}
    rebound = {(m, r["identity_key"]): r for m in rows for r in rows[m] if r["action"] == "REBIND"}
    packages = OrderedDict()
    for m in corrected:
        entry = reseal["markets"].get(m) or {}
        if not entry.get("RESEAL_PASS"):
            problems.append("%s has no passing reseal" % m)
            continue
        packages[m] = _load(_DASH / entry["package_path"])

    # ---- A. release-index accounting, one corrected market at a time ------
    live, live_doc = RESEAL.live_from_tree(Path(args.live_tree), Path(args.work))
    live_idx, live_state, _lp = live
    proposed, steps = release_index_chain(live, packages, problems)
    live_routes = {r for i in live_idx.markets.values() if i.participating for r in i.routes}
    cand_routes = {r for i in proposed.markets.values() if i.participating for r in i.routes}
    declared_route_removals = set()
    declared_profile_removals = 0
    for m, package in packages.items():
        delta = package["intended_delta"]
        declared_route_removals |= set(delta["remove_routes"])
        declared_profile_removals += len(delta["remove_property_ids"])
        if delta["add_routes"] or delta["add_property_ids"]:
            problems.append("%s declares additions: %s" % (m, (delta["add_routes"] + delta["add_property_ids"])[:3]))
    if live_routes - cand_routes != declared_route_removals:
        problems.append("release-index route removals %s differ from the declared %s"
                        % (sorted(live_routes - cand_routes)[:5], sorted(declared_route_removals)[:5]))
    if cand_routes - live_routes:
        problems.append("release-index routes added: %s" % sorted(cand_routes - live_routes)[:5])
    if sorted(proposed.participating) != sorted(live_idx.participating):
        problems.append("participation moved")
    for m in live_idx.participating:
        if m not in corrected and proposed.markets[m] is not live_idx.markets[m]:
            problems.append("%s is not carried unchanged" % m)
    for m in corrected:
        derived = RC.derive_authority(m)
        if len(proposed.markets[m].profiles) != derived.published_hotel_profiles:
            problems.append("%s: index %d profiles, contract %d" % (m, len(proposed.markets[m].profiles),
                                                                    derived.published_hotel_profiles))

    # ---- B. served sitemap accounting --------------------------------------
    live_manifest = _load(os.path.join(args.live, "global_bundle_manifest.json"))
    cand_manifest = _load(os.path.join(args.candidate, "global_bundle_manifest.json"))
    live_sitemap, cand_sitemap = _served(args.live), _served(args.candidate)
    if len(live_sitemap) != int(live_manifest["sitemap_route_count"]) \
            or len(cand_sitemap) != int(cand_manifest["sitemap_route_count"]):
        problems.append("a bundle's sitemap_route_count disagrees with its own sitemap")
    served_removed = sorted(live_sitemap - cand_sitemap)
    served_added = sorted(cand_sitemap - live_sitemap)
    if set(served_removed) != declared_route_removals:
        problems.append("served routes removed %s != declared %s" % (served_removed[:5],
                                                                     sorted(declared_route_removals)[:5]))
    if served_added:
        problems.append("served routes added: %s" % served_added[:5])
    if live_manifest["bundle_sha256"] != live_state.bundle_sha256:
        problems.append("--live is not the live bundle (%s vs %s)" % (live_manifest["bundle_sha256"],
                                                                     live_state.bundle_sha256))

    def published(manifest):
        return sum(len(f["hotel_routes"]) for f in manifest["fragments"].values())

    live_profiles, cand_profiles = published(live_manifest), published(cand_manifest)
    if live_profiles - cand_profiles != declared_profile_removals:
        problems.append("profiles %d -> %d, declared removals %d" % (live_profiles, cand_profiles,
                                                                   declared_profile_removals))
    cand_markets = sorted(m.get("market_id") if isinstance(m, dict) else m
                          for m in cand_manifest["participating_markets"])
    live_markets = sorted(m.get("market_id") if isinstance(m, dict) else m
                          for m in live_manifest["participating_markets"])
    if cand_markets != live_markets:
        problems.append("participating markets moved: -%s +%s" % (sorted(set(live_markets) - set(cand_markets)),
                                                                   sorted(set(cand_markets) - set(live_markets))))

    # ---- C. byte / file preservation ---------------------------------------
    live_files, cand_files = _hashes(args.live), _hashes(args.candidate)
    added = sorted(set(cand_files) - set(live_files))
    removed = sorted(set(live_files) - set(cand_files))
    changed = sorted(p for p in set(live_files) & set(cand_files) if live_files[p] != cand_files[p])
    market_ids = set(live_markets)

    def classify(paths):
        out = OrderedDict((("corrected_market", []), ("global_regenerated", []), ("unaffected_market", []),
                           ("unclassified", [])))
        for p in paths:
            owner = _market_of(p, market_ids)
            if owner in corrected:
                out["corrected_market"].append(p)
            elif p in GLOBAL_REGENERATED:
                out["global_regenerated"].append(p)
            elif owner is not None:
                out["unaffected_market"].append(p)
            else:
                out["unclassified"].append(p)
        return out

    added_by, removed_by, changed_by = classify(added), classify(removed), classify(changed)
    for label, bucket in (("added", added_by), ("removed", removed_by), ("changed", changed_by)):
        if bucket["unaffected_market"]:
            problems.append("%d unaffected-market file(s) %s: %s" % (len(bucket["unaffected_market"]), label,
                                                                    bucket["unaffected_market"][:5]))
        if bucket["unclassified"]:
            problems.append("%d unclassified file(s) %s: %s" % (len(bucket["unclassified"]), label,
                                                               bucket["unclassified"][:5]))
    if added:
        problems.append("%d file(s) added: %s" % (len(added), added[:5]))
    # every removed page is a declared route's page, or a /go/ page of a removed profile
    removed_pages = {p for p in removed if _route_of_file(p) and not p.startswith("go/")}
    undeclared_pages = sorted(p for p in removed_pages if _route_of_file(p) not in declared_route_removals)
    if undeclared_pages:
        problems.append("removed pages not declared: %s" % undeclared_pages[:5])

    # ---- D. the corrected rows, on the BUILT artifact -----------------------
    rows_out = []
    for m, pkg in packages.items():
        live_profiles_m = live_idx.markets[m].profiles
        for key in sorted(k for mm, k in removed_keys if mm == m):
            entry = next((e for e in live_profiles_m.values() if e.declared_identity_key == key
                          or e.identity_key == key), None)
            route = entry.route if entry else None
            slug = route.rstrip("/").rsplit("/", 1)[-1] if route else None
            pages = [p for p in cand_files if slug and p.startswith("pet-friendly-hotels/%s/%s/" % (m, slug))]
            go = [p for p in cand_files if slug and p.startswith("go/%s/" % m) and "/%s" % slug in p]
            rows_out.append(OrderedDict((("market_id", m), ("identity_key", key), ("live_route", route),
                                         ("route_served", route in cand_sitemap if route else None),
                                         ("profile_pages", len(pages)), ("go_files", len(go)))))
            if not route:
                problems.append("%s/%s had no live route to remove" % (m, key))
            elif route in cand_sitemap or pages or go:
                problems.append("%s/%s still publishes: %s" % (m, key, (pages + go)[:3]))
    for (m, key), row in rebound.items():
        entry = next((e for e in proposed.markets[m].profiles.values() if e.declared_identity_key == key
                      or e.identity_key == key), None)
        page = os.path.join(args.candidate, "site", entry.route.strip("/"), "index.html") if entry else None
        text = open(page, encoding="utf-8").read() if page and os.path.isfile(page) else ""
        flat = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())
        shows_answer = row["rebind_quote"] in flat
        old_question_only = row["quote_before"] in flat
        rows_out.append(OrderedDict((("market_id", m), ("identity_key", key), ("route", entry.route if entry else None),
                                     ("page_shows_rebound_answer", shows_answer),
                                     ("page_still_shows_old_quote", old_question_only))))
        if not shows_answer:
            problems.append("%s/%s: the profile does not show the rebound answer" % (m, key))

    # ---- E. the corrected candidate, re-read by the repaired reader -------
    rescan = _load(RESCAN)
    if rescan["PET_FRIENDLY_RECORDS_WITH_EXPLICIT_REFUSAL"] or rescan["QUESTION_ONLY_PET_FRIENDLY_RECORDS"]:
        problems.append("the corrected candidate still carries %d refusal(s) / %d question-only record(s)"
                        % (rescan["PET_FRIENDLY_RECORDS_WITH_EXPLICIT_REFUSAL"],
                           rescan["QUESTION_ONLY_PET_FRIENDLY_RECORDS"]))
    if rescan["CANDIDATE_PET_FRIENDLY_RECORDS_SCANNED"] != cand_profiles:
        problems.append("rescan read %d records, the candidate publishes %d"
                        % (rescan["CANDIDATE_PET_FRIENDLY_RECORDS_SCANNED"], cand_profiles))

    # ---- F. exclusion registry: no duplicate identities ---------------------
    registry = _load(PKG / "hotel_exclusions.json")["exclusions"]
    names = Counter((r.get("market_id"), " ".join(str(r.get("canonical_name") or "").lower().split()))
                    for r in registry)
    dupes = sorted("%s/%s" % k for k, n in names.items() if n > 1)
    if dupes:
        problems.append("duplicate exclusions: %s" % dupes[:5])

    # ---- G. determinism, measured -------------------------------------------
    determinism = OrderedDict((("measured", False),))
    if args.rebuild:
        rebuild_manifest = _load(os.path.join(args.rebuild, "global_bundle_manifest.json"))
        rebuild_files = _hashes(args.rebuild)
        differing = sorted(p for p in set(cand_files) | set(rebuild_files) if cand_files.get(p) != rebuild_files.get(p))
        identical = rebuild_manifest["bundle_sha256"] == cand_manifest["bundle_sha256"] and not differing
        determinism = OrderedDict((("measured", True), ("second_assembly", args.rebuild),
                                   ("candidate_bundle_sha256", cand_manifest["bundle_sha256"]),
                                   ("rebuild_bundle_sha256", rebuild_manifest["bundle_sha256"]),
                                   ("candidate_sitemap_sha256", cand_manifest.get("sitemap_sha256")),
                                   ("rebuild_sitemap_sha256", rebuild_manifest.get("sitemap_sha256")),
                                   ("files_compared", len(set(cand_files) | set(rebuild_files))),
                                   ("files_differing", len(differing)), ("examples", differing[:5]),
                                   ("result", "BYTE_IDENTICAL" if identical else "DIVERGED")))
        if not identical:
            problems.append("the candidate is not deterministic: %d file(s) differ" % len(differing))

    # ---- H. deployment eligibility ------------------------------------------
    eligibility = OrderedDict((("checked", False),))
    if args.authorization:
        from scripts.pettripfinder import deployment_authorization as DA
        auth = _load(args.authorization)
        gd_manifest = GD.build_manifest(cand_manifest)
        dep = DA.deployability_problems(auth, manifest=gd_manifest)
        ver = DA.verify_authorization(auth, manifest=gd_manifest)
        bound = auth.get("bundle_sha256") == cand_manifest["bundle_sha256"]
        consumed = bool(auth.get("deploy_id")) or auth.get("authorization_status") == DA.DEPLOYED
        eligibility = OrderedDict((("checked", True), ("authorization_id", auth.get("authorization_id")),
                                   ("authorization_status", auth.get("authorization_status")),
                                   ("bound_to_candidate_bytes", bound), ("deployability_problems", dep),
                                   ("verify_authorization_problems", ver),
                                   ("deployable", auth.get("authorization_status") in DA.DEPLOYABLE_STATUSES),
                                   ("consumed", consumed)))
        if not bound or dep or ver or consumed:
            problems.append("authorization not eligible: bound %s, problems %s, consumed %s" % (bound, (dep + ver)[:3],
                                                                                              consumed))

    live_served, cand_served = int(live_manifest["sitemap_route_count"]), int(cand_manifest["sitemap_route_count"])
    report = OrderedDict((
        ("schema", "ptf-live-correction-candidate-accounting/1.0"), ("work_order", WORK_ORDER),
        ("current_verified_live", live_doc),
        ("live_bundle", OrderedDict((("dir", args.live), ("bundle_sha256", live_manifest["bundle_sha256"]),
                                     ("sitemap_sha256", live_manifest.get("sitemap_sha256")),
                                     ("markets", len(live_markets)), ("profiles", live_profiles),
                                     ("release_index_routes", len(live_routes)), ("served_sitemap_routes", live_served),
                                     ("files", len(live_files))))),
        ("candidate_bundle", OrderedDict((("dir", args.candidate), ("bundle_sha256", cand_manifest["bundle_sha256"]),
                                          ("sitemap_sha256", cand_manifest.get("sitemap_sha256")),
                                          ("markets", len(cand_markets)), ("profiles", cand_profiles),
                                          ("release_index_routes", len(cand_routes)),
                                          ("served_sitemap_routes", cand_served), ("files", len(cand_files)),
                                          ("all_gates_pass", cand_manifest.get("all_gates_pass"))))),
        ("per_market", OrderedDict((m, OrderedDict((
            ("live_profiles", len(live_idx.markets[m].profiles)),
            ("candidate_profiles", len(proposed.markets[m].profiles)),
            ("removed_routes", packages[m]["intended_delta"]["remove_routes"]),
            ("updated_property_ids", packages[m]["intended_delta"]["update_property_ids"]),
            ("release_index_step", steps.get(m))))) for m in packages)),
        ("delta", OrderedDict((
            ("MARKETS", "%d -> %d" % (len(live_markets), len(cand_markets))),
            ("PROFILES", "%d -> %d (%+d)" % (live_profiles, cand_profiles, cand_profiles - live_profiles)),
            ("RELEASE_INDEX_ROUTES", "%d -> %d (%+d)" % (len(live_routes), len(cand_routes),
                                                         len(cand_routes) - len(live_routes))),
            ("SERVED_ROUTES", "%d -> %d (%+d)" % (live_served, cand_served, cand_served - live_served)),
            ("declared_route_removals", sorted(declared_route_removals)),
            ("served_routes_removed", served_removed), ("served_routes_added", served_added),
            ("PRIOR_MARKETS_LOST", len(set(live_markets) - set(cand_markets))),
            ("UNEXPECTED_PROFILES_LOST", (live_profiles - cand_profiles) - declared_profile_removals),
            ("UNEXPECTED_ROUTES_LOST", len(set(served_removed) - declared_route_removals)),
        ))),
        ("byte_preservation", OrderedDict((
            ("files_added", len(added)), ("files_removed", len(removed)), ("files_changed", len(changed)),
            ("added_by_class", OrderedDict((k, len(v)) for k, v in added_by.items())),
            ("removed_by_class", OrderedDict((k, len(v)) for k, v in removed_by.items())),
            ("changed_by_class", OrderedDict((k, len(v)) for k, v in changed_by.items())),
            ("changed_by_market", OrderedDict(sorted(Counter(_market_of(p, market_ids) or "(global)"
                                                             for p in changed).items()))),
            ("changed_global_artifacts", changed_by["global_regenerated"]),
            ("UNAFFECTED_MARKET_FILES_CHANGED", len(changed_by["unaffected_market"]) + len(removed_by["unaffected_market"])
             + len(added_by["unaffected_market"])),
        ))),
        ("corrected_rows_on_the_artifact", rows_out),
        ("candidate_rescan", OrderedDict((k, rescan[k]) for k in (
            "CANDIDATE_PET_FRIENDLY_RECORDS_SCANNED", "classes", "PET_FRIENDLY_RECORDS_WITH_EXPLICIT_REFUSAL",
            "QUESTION_ONLY_PET_FRIENDLY_RECORDS", "AMBIGUOUS"))),
        ("exclusion_registry", OrderedDict((("rows", len(registry)), ("duplicates", dupes)))),
        ("candidate_determinism", determinism),
        ("deployment_eligibility", eligibility),
        ("problems", problems),
        ("ALL_ACCOUNTING_GATES", "PASS" if not problems else "FAIL"),
        ("nothing_deployed", True),
    ))
    print(json.dumps(OrderedDict((("delta", report["delta"]), ("byte_preservation", report["byte_preservation"]),
                                  ("determinism", determinism.get("result", "NOT_MEASURED")),
                                  ("eligibility", eligibility), ("ALL_ACCOUNTING_GATES", report["ALL_ACCOUNTING_GATES"]))),
                     indent=1)[:6000])
    for p in problems:
        print("   !", p)
    if args.write:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("written:", os.path.relpath(args.out, str(_DASH)))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

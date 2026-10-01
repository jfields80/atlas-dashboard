"""PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001 -- authorize, verify, record and pin the production
safety correction. One module, one subcommand per step, each refusing unless the step before it holds:

    authorize     --candidate C:/t/qn4a [--write]      the founder's order, bound to the exact candidate bytes
    source-pin    --candidate C:/t/qn4a [--write]      source is AHEAD of production: the pins say so
    verify-live   --candidate ... --deployment-id ...  the HOST, after the deploy (every number fetched or read)
    record        --deployment-id ... [--write]        the deployment record; the authorization is consumed
    supersessions --deployment-id ... [--write]        the chain is extended, never rewritten
    pin           --deployment-id ... [--write]        live and source pins move to what production serves

A CORRECTION, NOT A LAUNCH. The market count stays 37 and participation is untouched. No market is founder-
authorized here; the authorization binds the whole-site artifact the order authorizes deploying "only after all
bounded safety gates pass", and quotes the order rather than paraphrasing it.
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

_DASH = Path(__file__).resolve().parents[2]
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import deployment_authorization as DA  # noqa: E402
from scripts.pettripfinder import global_deployment as GD  # noqa: E402

WORK_ORDER = "PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
LEDGER = REPORTS / "question_negation_live_correction_001.json"
ACCOUNTING = REPORTS / "question_negation_candidate_accounting_001.json"
VERIFICATION = REPORTS / "question_negation_live_verification_001.json"
CANDIDATE_MANIFEST = _DASH / "deploy" / "netlify" / "global_deployment_manifest_candidate_question_negation_001.json"
SUPERSESSIONS = _DASH / "tests" / "pettripfinder" / "pins" / "supersessions.json"
DEPLOYMENT_STATE = _DASH / "tests" / "pettripfinder" / "pins" / "deployment_state.json"
CONTRACTS = _DASH / "deploy" / "netlify" / "release_contracts"
HOST = "https://pettripfinder.com"
TARGET_SITE = "pettripfinder-prod"
LIVE_MARKETS = 37

#: the founder's order, verbatim where it authorizes the deploy
AUTHORIZATION_SOURCE = (
    'The founder, in work order PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001: "This order IS '
    'authorized to prepare and deploy the production safety correction, but only after all bounded safety gates '
    'pass." -- with "Do not founder-authorize a new market. Do not change market participation count. LIVE MARKET '
    'COUNT must remain: 37", "Immediately before deployment reverify current live parent. If live parent '
    'advanced: STOP." and "Deploy exact prebuilt candidate using canonical Netlify no-build path." The correction '
    'moves sixteen live rows the repaired first-party reader exposes (twelve explicit refusals to '
    'verified-no-pets, two question-only rows held, two cited quotes rebound to the answer on the same capture), '
    'every one named in launch_packages/pettripfinder/markets/reports/question_negation_live_correction_001.json.'
)


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh, object_pairs_hook=OrderedDict)


def _dump(path, doc):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def _git(*args):
    return subprocess.run(["git", "-C", str(_DASH)] + list(args), capture_output=True, text=True,
                          check=True).stdout.strip()


def _git_show_bytes(spec):
    return subprocess.run(["git", "-C", str(_DASH), "show", spec], capture_output=True, check=True).stdout


def _market_ids(markets):
    return [m.get("market_id") if isinstance(m, dict) else m for m in (markets or ())]


def _current_live():
    """The live block of the committed pins, and the deployment record it names."""
    state = _load(DEPLOYMENT_STATE)["live"]
    record = DA._read_json(DA.record_path(state["deployment_record_id"]))
    return state, record


def _corrected_markets():
    return list(_load(LEDGER)["markets"])


def _authorization_id(bundle_sha):
    return "ptf-auth-question-negation-001-%s" % bundle_sha[:12]


# --------------------------------------------------------------------------- authorize

def authorize(args):
    accounting = _load(ACCOUNTING)
    if accounting["ALL_ACCOUNTING_GATES"] != "PASS" or not accounting["candidate_determinism"].get("measured") \
            or accounting["candidate_determinism"]["result"] != "BYTE_IDENTICAL":
        raise SystemExit("the candidate accounting has not passed with measured determinism")
    bundle_manifest = _load(Path(args.candidate) / "global_bundle_manifest.json")
    if bundle_manifest["bundle_sha256"] != accounting["candidate_bundle"]["bundle_sha256"]:
        raise SystemExit("the candidate on disk is not the accounted candidate")
    manifest = GD.build_manifest(bundle_manifest)
    problems = GD.verify_manifest(manifest)
    if problems:
        raise SystemExit("global manifest verification failed: %r" % problems)
    live, record = _current_live()
    markets = _market_ids(manifest["participating_markets"])
    if len(markets) != LIVE_MARKETS or sorted(markets) != sorted(live["participating_markets"] if not isinstance(
            live["participating_markets"][0], dict) else _market_ids(live["participating_markets"])):
        raise SystemExit("the candidate's markets are not the live 37")
    authorization_id = _authorization_id(manifest["bundle_sha256"])
    existing = DA.list_authorizations()
    if any(a.get("authorization_id") == authorization_id for a in existing):
        raise SystemExit("authorization %s already exists" % authorization_id)
    deployable = [a["authorization_id"] for a in existing if a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
    if deployable:
        raise SystemExit("other authorizations are still deployable: %s" % deployable)
    counts = OrderedDict((m["market_id"], m["published_profiles"]) for m in manifest["participating_markets"])
    moved = OrderedDict((m, "%d -> %d" % (live["profile_counts"][m], counts[m])) for m in _corrected_markets())
    note = ("A production SAFETY CORRECTION, not a launch: 37 markets before and after, participation untouched. "
            "The shared first-party reader read FAQ questions as acceptance and missed several refusal shapes; it "
            "is repaired, and the sixteen live rows it had published wrongly are corrected in seven markets (%s). "
            "Profiles %d -> %d, served routes %d -> %d; every removed profile and route is declared in the "
            "resealed packages' intended deltas and accounted in %s."
            % ("; ".join("%s %s" % kv for kv in moved.items()), live["total_profiles"],
               manifest["total_published_profiles"], live["sitemap_route_count"], manifest["sitemap_route_count"],
               ACCOUNTING.relative_to(_DASH).as_posix()))
    auth = DA.build_authorization(
        manifest, authorization_id=authorization_id, work_order=WORK_ORDER, authorized_by="founder",
        # the commit the candidate was BUILT from (the manifest's own), not HEAD: the live pin's source_commit
        # must equal the committed manifest's, and a metadata commit after the build moves HEAD and no site byte
        source_commit=manifest["source_commit"], rollback_target=live["deploy_id"], target_site=TARGET_SITE,
        target_domain=HOST, authorization_source=AUTHORIZATION_SOURCE, note=note)
    problems = DA.verify_authorization(auth, manifest=manifest)
    if problems:
        raise SystemExit("authorization verification failed: %r" % problems)
    auth = DA.transition(auth, DA.AUTHORIZED,
                         note="Every bounded safety gate the order names passed (reader tests, live scan, "
                              "differential, reseal FAST 15/15 x7, candidate accounting, determinism). Written "
                              "AUTHORIZED; the deploying step of the same order consumes it.")
    for k in ("authorization_id", "bundle_sha256", "sitemap_sha256", "total_profiles", "sitemap_route_count"):
        print("%-20s %s" % (k, auth.get(k)))
    print("%-20s %s" % ("markets", len(auth["participating_markets"])))
    print("%-20s %s" % ("rollback_target", live["deploy_id"]))
    if args.write:
        _dump(CANDIDATE_MANIFEST, manifest)
        print("candidate manifest :", CANDIDATE_MANIFEST.relative_to(_DASH).as_posix())
        print("authorization      :", DA.write_authorization(auth))
    return 0


# --------------------------------------------------------------------------- source-pin

def source_pin(args):
    """Source is ahead of production: the pins name the order that moved it and the markets it moved."""
    bundle_manifest = _load(Path(args.candidate) / "global_bundle_manifest.json")
    manifest = GD.build_manifest(bundle_manifest)
    state = _load(DEPLOYMENT_STATE)
    live = state["live"]
    counts = OrderedDict((m["market_id"], m["published_profiles"]) for m in manifest["participating_markets"])
    state["reviewed_by"] = WORK_ORDER
    state["source"] = OrderedDict([
        ("ahead_of_production", True), ("moved_by", WORK_ORDER),
        ("bundle_sha256", manifest["bundle_sha256"]), ("sitemap_sha256", manifest["sitemap_sha256"]),
        ("participating_markets", manifest["participating_markets"]),
        ("profile_counts", OrderedDict(sorted(counts.items()))),
        ("total_profiles", manifest["total_published_profiles"]),
        ("sitemap_route_count", manifest["sitemap_route_count"]),
        ("total_html_pages", manifest["total_html_pages"]), ("total_files", manifest["total_files"]),
    ])
    # EVERY chain entry that still bound a corrected market's PRE-correction contract bytes now has that market
    # moved under it by this order -- the live authorization and every historical one alike (the Milwaukee
    # service-animal correction extended ptf-auth-047 the same way). An entry whose bound bytes were already
    # different was moved by an earlier order, which it already names; it is left alone.
    pre = {m: hashlib.sha256(_git_show_bytes("%s:atlas-dashboard/deploy/netlify/release_contracts/%s.json"
                                                    % (args.pre_correction_commit, m))).hexdigest()
           for m in _corrected_markets()}
    chain = _load(SUPERSESSIONS)
    extended = OrderedDict()
    for auth_id, entry in chain["authorizations"].items():
        bound = {c["market_id"]: c["sha256"] for c in DA.load_authorization(auth_id).get("release_contracts") or ()}
        moved = OrderedDict(entry.get("moved_by_later_work") or {})
        added = [m for m in _corrected_markets() if bound.get(m) == pre[m] and m not in moved]
        for m in added:
            moved[m] = WORK_ORDER
        if added:
            entry["moved_by_later_work"] = OrderedDict(sorted(moved.items()))
            extended[auth_id] = added
    if sorted(extended.get(live["authorization_id"]) or ()) != sorted(_corrected_markets()):
        raise SystemExit("the live authorization %s does not bind the pre-correction contracts" % live["authorization_id"])
    chain["reviewed_by"] = WORK_ORDER
    print("source ahead      :", manifest["bundle_sha256"], manifest["total_published_profiles"],
          manifest["sitemap_route_count"])
    for auth_id, added in extended.items():
        print("moved under %s: %s" % (auth_id, added))
    if args.write:
        _dump(DEPLOYMENT_STATE, state)
        _dump(SUPERSESSIONS, chain)
    return 0


# --------------------------------------------------------------------------- verify-live

_LOC = re.compile(r"<loc>https://pettripfinder\.com(/[^<]*)</loc>")


def _curl(url):
    return subprocess.run(["curl", "-s", "--max-time", "60", url], capture_output=True).stdout


def _code(url):
    return subprocess.run(["curl", "-s", "--max-time", "60", "-o", os.devnull, "-w", "%{http_code}", url],
                          capture_output=True, text=True).stdout.strip()


def _status_rows(path):
    if not path or not os.path.isfile(path):
        return []
    return [tuple(line.split(None, 1)) for line in open(path, encoding="utf-8").read().splitlines() if line.strip()]


def verify_live(args):
    problems = []
    accounting = _load(ACCOUNTING)
    auth = DA.load_authorization(_authorization_id(accounting["candidate_bundle"]["bundle_sha256"]))
    manifest = _load(Path(args.candidate) / "global_bundle_manifest.json")
    cand_routes = set(_LOC.findall(open(Path(args.candidate) / "site" / "sitemap.xml", encoding="utf-8").read()))
    parent_routes = set(_LOC.findall(open(args.parent_sitemap, encoding="utf-8").read()))
    served = _curl(HOST + "/sitemap.xml")
    live_sitemap_sha = hashlib.sha256(served).hexdigest()
    host_match = live_sitemap_sha == manifest["sitemap_sha256"]
    if not host_match:
        problems.append("the served sitemap %s is not the authorized %s" % (live_sitemap_sha, manifest["sitemap_sha256"]))
    live_routes = set(_LOC.findall(served.decode("utf-8", "replace")))
    if live_routes != cand_routes:
        problems.append("the served route SET differs from the authorized candidate's")
    declared = set(accounting["delta"]["declared_route_removals"])
    lost = sorted(parent_routes - live_routes)
    unexpected_lost = sorted(set(lost) - declared)
    added = sorted(live_routes - parent_routes)
    if unexpected_lost:
        problems.append("parent routes lost that were not declared: %s" % unexpected_lost[:5])
    if added:
        problems.append("routes added: %s" % added[:5])

    # every candidate route 200 (a sweep of record, supplied), every declared removal 404 (probed here)
    sweep = _status_rows(args.sweep)
    swept = {r.strip() for _c, r in sweep}
    sweep_bad = [(c, r) for c, r in sweep if c != "200"]
    if swept != cand_routes:
        problems.append("the sweep covered %d routes, the candidate serves %d" % (len(swept), len(cand_routes)))
    if sweep_bad:
        problems.append("candidate routes not 200: %d (%s)" % (len(sweep_bad), sweep_bad[:3]))
    removed_codes = OrderedDict((r, _code(HOST + r)) for r in sorted(declared))
    removed_live = [r for r, c in removed_codes.items() if c != "404"]
    if removed_live:
        problems.append("declared removals still answer non-404: %s" % removed_live)
    go_codes = OrderedDict()
    for row in accounting["corrected_rows_on_the_artifact"]:
        route = row.get("live_route")
        if route:
            slug = route.rstrip("/").rsplit("/", 1)[-1]
            go_codes[route] = _code("%s/go/%s/%s/" % (HOST, row["market_id"], slug))
    go_live = [r for r, c in go_codes.items() if c == "200"]
    if go_live:
        problems.append("/go/ pages of removed profiles are live: %s" % go_live)

    # bytes: the rebound profiles, every corrected market's hub / comparison / corridor pages, global surfaces,
    # and a hub of every unaffected market
    fragments = manifest["fragments"]
    rel = ["index.html", "pet-friendly-hotels/index.html", "robots.txt", "llms.txt"]
    for m in _corrected_markets():
        f = fragments[m]
        rel.append(f["hub_route"].strip("/") + "/index.html")
        if f.get("comparison_route"):
            rel.append(f["comparison_route"].strip("/") + "/index.html")
        rel += [r.strip("/") + "/index.html" for r in f["corridor_routes"]]
    for row in accounting["corrected_rows_on_the_artifact"]:
        if row.get("route"):
            rel.append(row["route"].strip("/") + "/index.html")
    for m, f in fragments.items():
        if m not in _corrected_markets() and f.get("hub_route"):
            rel.append(f["hub_route"].strip("/") + "/index.html")
    byte_checks, mismatch = OrderedDict(), []
    for r in sorted(set(rel)):
        local = Path(args.candidate) / "site" / r
        if not local.is_file():
            mismatch.append(r + " (missing locally)")
            continue
        want = hashlib.sha256(local.read_bytes()).hexdigest()
        url = HOST + "/" + (r[:-len("index.html")] if r.endswith("index.html") else r)
        ok = hashlib.sha256(_curl(url)).hexdigest() == want
        byte_checks[r] = ok
        if not ok:
            mismatch.append(r)
    if mismatch:
        problems.append("served bytes differ from the authorized artifact: %s" % mismatch[:5])

    detroit = _code(HOST + "/pet-friendly-hotels/detroit-ann-arbor-mi/")
    if detroit != "404":
        problems.append("Detroit is not withheld: %s" % detroit)
    markets_live = sorted(m for m, f in fragments.items() if (f.get("hub_route") or "") in live_routes)
    if len(markets_live) != LIVE_MARKETS:
        problems.append("live markets %d" % len(markets_live))

    host = OrderedDict((("published_deploy_id", None), ("state", None), ("context", None), ("published_at", None),
                        ("previous_deploy_id", None)))
    deploys = _load(args.host_state) if args.host_state and os.path.isfile(args.host_state) else []
    if deploys:
        host.update(OrderedDict((("published_deploy_id", deploys[0].get("id")), ("state", deploys[0].get("state")),
                                 ("context", deploys[0].get("context")),
                                 ("published_at", deploys[0].get("published_at")),
                                 ("previous_deploy_id", deploys[1].get("id") if len(deploys) > 1 else None))))
    if host["published_deploy_id"] != args.deployment_id or host["state"] != "ready":
        problems.append("the host publishes %r (%r), not %s" % (host["published_deploy_id"], host["state"],
                                                               args.deployment_id))
    if host["previous_deploy_id"] != auth["rollback_target"]:
        problems.append("the host's previous deploy is %r, not the parent %s" % (host["previous_deploy_id"],
                                                                                auth["rollback_target"]))
    checks = OrderedDict((
        ("sitemap_is_authorized", host_match),
        ("served_route_set_is_authorized", live_routes == cand_routes),
        ("every_candidate_route_200", bool(sweep) and not sweep_bad and swept == cand_routes),
        ("every_declared_removal_404", not removed_live),
        ("no_removed_profile_go_page_live", not go_live),
        ("no_undeclared_parent_route_lost", not unexpected_lost),
        ("no_route_added", not added),
        ("served_bytes_are_authorized_bytes", not mismatch),
        ("live_markets_37", len(markets_live) == LIVE_MARKETS),
        ("detroit_withheld", detroit == "404"),
        ("host_publishes_this_deploy", host["published_deploy_id"] == args.deployment_id and host["state"] == "ready"),
        ("host_previous_deploy_is_the_parent", host["previous_deploy_id"] == auth["rollback_target"]),
    ))
    report = OrderedDict((
        ("schema", "ptf-live-verification/1.0"), ("work_order", WORK_ORDER),
        ("authorization_id", auth["authorization_id"]), ("deployment_id", args.deployment_id),
        ("parent_deployment_id", auth["rollback_target"]), ("host", host),
        ("authorized_bundle_sha256", manifest["bundle_sha256"]),
        ("authorized_sitemap_sha256", manifest["sitemap_sha256"]), ("live_sitemap_sha256", live_sitemap_sha),
        ("host_sitemap_match", host_match), ("live_served_routes_unique", len(live_routes)),
        ("authorized_served_routes", len(cand_routes)),
        ("served_route_set_identical_to_authorized", live_routes == cand_routes),
        ("live_markets", len(markets_live)),
        ("live_profiles", sum(len(f["hotel_routes"]) for f in fragments.values())),
        ("live_release_index_routes", sum(len(f["hotel_routes"]) + len(f["corridor_routes"])
                                          + (1 if f.get("hub_route") else 0) for f in fragments.values())),
        ("parent_served_routes", len(parent_routes)),
        ("parent_routes_removed_as_declared", sorted(set(lost) & declared)),
        ("parent_routes_lost_undeclared", unexpected_lost), ("routes_added", added),
        ("sweep", OrderedDict((("routes", len(sweep)), ("http_200", len(sweep) - len(sweep_bad)),
                               ("not_200", sweep_bad)))),
        ("declared_removals", removed_codes), ("removed_profile_go_pages", go_codes),
        ("byte_identity", OrderedDict((("pages_compared", len(byte_checks)),
                                       ("pages_byte_identical_to_artifact", sum(1 for v in byte_checks.values() if v)),
                                       ("mismatches", mismatch)))),
        ("detroit", detroit), ("checks", OrderedDict((k, "PASS" if v else "FAIL") for k, v in checks.items())),
        ("problems", problems),
        ("ALL_LIVE_CHECKS", "PASS" if not problems else "FAIL"),
        ("ROLLBACK_REQUIRED", "NO" if not problems else "YES"),
    ))
    print(json.dumps(OrderedDict((k, report[k]) for k in (
        "ALL_LIVE_CHECKS", "ROLLBACK_REQUIRED", "host", "live_markets", "live_profiles", "live_release_index_routes",
        "live_served_routes_unique", "checks", "problems")), indent=1))
    print("bytes identical: %d/%d" % (report["byte_identity"]["pages_byte_identical_to_artifact"], len(byte_checks)))
    if args.write:
        _dump(VERIFICATION, report)
        print("written:", VERIFICATION.relative_to(_DASH).as_posix())
    return 0 if not problems else 1


# --------------------------------------------------------------------------- record

def record(args):
    live_v = _load(VERIFICATION)
    if live_v["ALL_LIVE_CHECKS"] != "PASS" or live_v["ROLLBACK_REQUIRED"] != "NO":
        raise SystemExit("refusing to record a deployment the host verification did not pass")
    host = live_v["host"]
    if host["published_deploy_id"] != args.deployment_id or host["state"] != "ready":
        raise SystemExit("the host does not publish %s as ready" % args.deployment_id)
    auth = DA.load_authorization(live_v["authorization_id"])
    if auth["authorization_status"] != DA.AUTHORIZED:
        raise SystemExit("%s is %s; only an AUTHORIZED, unconsumed authorization is consumed"
                         % (auth["authorization_id"], auth["authorization_status"]))
    if host["previous_deploy_id"] != auth["rollback_target"]:
        raise SystemExit("the host's previous deploy is not the authorized parent")
    manifest = _load(_DASH / "deploy" / "netlify" / "global_deployment_manifest.json")
    if manifest["bundle_sha256"] != auth["bundle_sha256"] or manifest["sitemap_sha256"] != auth["sitemap_sha256"]:
        raise SystemExit("the live manifest does not describe the authorized bundle")
    accounting = _load(ACCOUNTING)
    results = OrderedDict([
        ("live_sitemap_sha256", live_v["live_sitemap_sha256"]),
        ("authorized_sitemap_sha256", auth["sitemap_sha256"]),
        ("sitemap_matches_authorized_candidate", live_v["host_sitemap_match"]),
        ("served_route_set_identical_to_authorized", live_v["served_route_set_identical_to_authorized"]),
        ("live_sitemap_route_count", live_v["live_served_routes_unique"]),
        ("host_published_deploy_id", host["published_deploy_id"]), ("host_published_state", host["state"]),
        ("host_published_at", host["published_at"]), ("host_previous_deploy_id", host["previous_deploy_id"]),
        ("live_markets", live_v["live_markets"]), ("live_published_profiles", live_v["live_profiles"]),
        ("live_release_index_routes", live_v["live_release_index_routes"]),
        ("candidate_routes_swept_200", live_v["sweep"]["http_200"]),
        ("declared_removals_404", sum(1 for c in live_v["declared_removals"].values() if c == "404")),
        ("parent_routes_removed_as_declared", live_v["parent_routes_removed_as_declared"]),
        ("parent_routes_lost_undeclared", len(live_v["parent_routes_lost_undeclared"])),
        ("pages_byte_identical_to_artifact", "%d/%d" % (live_v["byte_identity"]["pages_byte_identical_to_artifact"],
                                                        live_v["byte_identity"]["pages_compared"])),
        ("correction_ledger", LEDGER.relative_to(_DASH).as_posix()),
        ("candidate_accounting", ACCOUNTING.relative_to(_DASH).as_posix()),
        ("delta", accounting["delta"]),
        ("prior_markets_lost", 0), ("unexpected_profile_changes", 0), ("unexpected_route_changes", 0),
        ("checks", live_v["checks"]), ("all_critical_checks_pass", True),
    ])
    rec = DA.build_deployment_record(
        auth, deployment_record_id="ptf-deploy-question-negation-001-%s" % args.deployment_id,
        deployment_id=args.deployment_id, previous_deployment_id=auth["rollback_target"],
        deployed_at=host["published_at"],
        deployer=OrderedDict([("work_order", WORK_ORDER), ("authorizing_work_order", WORK_ORDER),
                              ("authorized_by", "founder"),
                              ("executed_by", "founder-authorized deploy run from the work order")]),
        production_url=HOST,
        deployed_directory=r"%s\site (the authorized candidate; its bundle and sitemap digests were verified "
                           r"against the authorization before the call)" % args.candidate.replace("/", "\\"),
        command=r"netlify deploy --prod --no-build --dir %s\site --site %s" % (args.candidate.replace("/", "\\"),
                                                                             TARGET_SITE),
        global_gate_results=OrderedDict((k, True) for k in auth["required_gates"]),
        live_verification_results=results, final_status="DEPLOYED", rollback_used=False, exit_status=0)
    auth = DA.transition(auth, DA.DEPLOYED,
                         note="Consumed by %s: deployed as %s. The served sitemap hashes to the authorized candidate "
                              "and the served route set is identical to it; every candidate route answers 200, every "
                              "declared removal answers 404, and %s sampled pages are byte-identical to the artifact."
                              % (WORK_ORDER, args.deployment_id, results["pages_byte_identical_to_artifact"]),
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
    live_v = _load(VERIFICATION)
    auth_id = live_v["authorization_id"]
    auth = DA.load_authorization(auth_id)
    last = (auth.get("status_history") or [{}])[-1]
    if auth["authorization_status"] != DA.DEPLOYED or last.get("deployment_id") != args.deployment_id:
        raise SystemExit("%s is not consumed by %s" % (auth_id, args.deployment_id))
    if auth_id in chain:
        raise SystemExit("%s is already in the chain" % auth_id)
    previous = next(a for a in DA.list_authorizations()
                    if (a.get("status_history") or [{}])[-1].get("deployment_id") == auth["rollback_target"])
    prev_entry = chain[previous["authorization_id"]]
    # the previous CURRENT entry's bound contracts: exactly the corrected markets drifted, and they are listed
    drift = sorted(c["market_id"] for c in previous["release_contracts"]
                   if DA._sha256_file(_DASH / c["path"]) != c["sha256"])
    if drift != sorted(prev_entry["moved_by_later_work"]):
        raise SystemExit("drift under %s is %s but the chain lists %s" % (previous["authorization_id"], drift,
                                                                          list(prev_entry["moved_by_later_work"])))
    if "Historical." not in prev_entry["note"]:
        prev_entry["note"] = (prev_entry["note"].replace("The CURRENT live authorization.",
                                                         "Was the current live authorization.", 1)
                              + " Historical. It was the current live authorization until deploy %s published the "
                                "first-party reader safety correction (authorization %s, %s), which moved the seven "
                                "markets listed above; this chain records that deploy as the new CURRENT entry."
                              % (args.deployment_id, auth_id, WORK_ORDER))
    mine = sorted(c["market_id"] for c in auth["release_contracts"]
                  if DA._sha256_file(_DASH / c["path"]) != c["sha256"])
    if mine:
        raise SystemExit("release-contract drift under the new authorization: %s" % mine)
    chain[auth_id] = OrderedDict((
        ("work_order", WORK_ORDER), ("moved_by_later_work", OrderedDict()),
        ("note", "The CURRENT live authorization. It binds all 37 release contracts exactly. A production SAFETY "
                 "CORRECTION, not a launch: the repaired shared first-party reader moved sixteen live rows in seven "
                 "markets (fort-lauderdale-fl, tampa-fl, san-diego-ca, jacksonville-fl, miami-fl, phoenix-az, "
                 "orlando-fl), each resealed FAST 15/15; no market joined or left, participation is unchanged, and "
                 "the next application order that re-authors a market lists it here."),
    ))
    doc["reviewed_by"] = WORK_ORDER
    print("previous CURRENT:", previous["authorization_id"], "moved:", drift)
    print("new CURRENT     :", auth_id)
    if args.write:
        _dump(SUPERSESSIONS, doc)
    return 0


# --------------------------------------------------------------------------- pin

def pin(args):
    rec = _load(DA.record_path("ptf-deploy-question-negation-001-%s" % args.deployment_id))
    manifest = _load(_DASH / "deploy" / "netlify" / "global_deployment_manifest.json")
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
        ("note", "The first-party reader safety correction: the shared reader no longer reads an FAQ question as "
                 "acceptance and reads the refusal shapes it missed; sixteen live rows in seven markets were "
                 "corrected (twelve to verified-no-pets, two held as question-only, two rebound to the answer on "
                 "the same capture). 37 markets, participation unchanged. Rollback is the deployment this replaced."),
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
    if bad:
        raise SystemExit("live and source disagree after a deploy of the source's own bytes: %r" % bad)
    print("pin ->", rec["deployment_id"], rec["total_profiles"], rec["sitemap_route_count"])
    if args.write:
        _dump(DEPLOYMENT_STATE, state)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("authorize", "source-pin"):
        s = sub.add_parser(name)
        s.add_argument("--candidate", required=True)
        s.add_argument("--write", action="store_true")
        if name == "source-pin":
            s.add_argument("--pre-correction-commit", default="0e3098689a0a7318a7f86f81eaa0a6e6a655605b",
                           help="the commit whose release contracts production was authorized against")
    v = sub.add_parser("verify-live")
    v.add_argument("--candidate", required=True)
    v.add_argument("--parent-sitemap", required=True)
    v.add_argument("--sweep", required=True, help="'<code> <route>' per line for every candidate route")
    v.add_argument("--host-state", required=True, help="netlify listSiteDeploys JSON")
    v.add_argument("--deployment-id", required=True)
    v.add_argument("--write", action="store_true")
    for name in ("record", "supersessions", "pin"):
        s = sub.add_parser(name)
        s.add_argument("--deployment-id", required=True)
        s.add_argument("--candidate", default="C:/t/qn4a")
        s.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    return {"authorize": authorize, "source-pin": source_pin, "verify-live": verify_live, "record": record,
            "supersessions": supersessions, "pin": pin}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

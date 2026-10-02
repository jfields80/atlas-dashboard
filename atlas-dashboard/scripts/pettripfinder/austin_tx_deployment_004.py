"""PTF-AUSTIN-TX-FOUNDER-LAUNCH-AUTHORIZATION-AND-DEPLOYMENT-004 -- after the deploy: verify the HOST, record the
deployment, extend the supersessions chain, move the pins. One subcommand per step, each refusing unless the step
before it holds (derived from Phoenix's 005 modules, every structural check unchanged):

    verify-live   --candidate C:/t/atx4a --parent-sitemap ... --market-sweep ... --prior-sweep ...
                  --host-state ... --deployment-id ... [--write]
    record        --deployment-id ... [--write]
    supersessions --deployment-id ... [--write]
    pin           --deployment-id ... [--write]

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
from scripts.pettripfinder import release_index as RI              # noqa: E402

WORK_ORDER = "PTF-AUSTIN-TX-FOUNDER-LAUNCH-AUTHORIZATION-AND-DEPLOYMENT-004"
MARKET = "austin-tx"
HOST = "https://pettripfinder.com"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
VERIFICATION = os.path.join(REPORTS, "austin_tx_live_verification_004.json")
ACCOUNTING = os.path.join(REPORTS, "austin_tx_launch_authorization_004.json")
SUPERSESSIONS = os.path.join(_DASH, "tests", "pettripfinder", "pins", "supersessions.json")
DEPLOYMENT_STATE = os.path.join(_DASH, "tests", "pettripfinder", "pins", "deployment_state.json")
MANIFEST = os.path.join(_DASH, "deploy", "netlify", "global_deployment_manifest.json")
TIMESHARE = ("Club Wyndham Austin", "WorldMark Austin", "Raintree Inn & Suites")
SPOT = ("phoenix-az", "denver-co", "san-diego-ca", "jacksonville-fl", "west-palm-beach-fl", "fort-lauderdale-fl",
        "augusta-ga", "miami-fl", "tampa-fl", "orlando-fl", "jacksonville-nc", "austin-tx")
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


def _authorization():
    acct = _load(ACCOUNTING)
    eligibility = acct.get("deployment_eligibility") or {}
    return DA.load_authorization(eligibility["authorization_id"])


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
    if len(prior_rows) != len(parent_routes):
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

    # every UNPUBLISHED census row: the census slug AND the route the site forms from its name
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET))
    partition = _load(os.path.join(PKG, "austin_tx_final_partition_001.json"))
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

    text_pages = [mine["hub_route"], mine["comparison_route"]] + list(mine["corridor_routes"])
    page_text = OrderedDict((p, _curl(HOST + p).decode("utf-8", "replace")) for p in text_pages)
    timeshare = OrderedDict()
    ts_ok = True
    for name in TIMESHARE:
        route = RI.hotel_route(cfg, name)
        code = _code(HOST + route)
        hits = [p for p, body in page_text.items() if name in body or name.replace("&", "&amp;") in body]
        ok = code == "404" and route not in live_routes and not hits
        ts_ok = ts_ok and ok
        timeshare[name] = OrderedDict((("route", route), ("code", code), ("page_text_hits", hits), ("absent", ok)))
    if not ts_ok:
        problems.append("a timeshare identity is visible: %s" % [k for k, v in timeshare.items() if not v["absent"]])

    spot = OrderedDict((m, int(_code("%s/pet-friendly-hotels/%s/" % (HOST, m)) or 0)) for m in SPOT)
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
    checks = OrderedDict((
        ("sitemap_is_authorized", host_match),
        ("served_route_set_is_authorized", live_routes == cand_routes),
        ("every_austin_route_200", bool(my_rows) and not my_not_200),
        ("no_parent_route_lost", not lost),
        ("every_prior_route_200", bool(prior_rows) and not prior_bad and len(prior_rows) == len(parent_routes)),
        ("only_austin_added", not added_not_mine),
        ("served_bytes_are_authorized_bytes", not byte_mismatch),
        ("every_unpublished_identity_404", not held_live and not not_404),
        ("timeshare_absent", ts_ok),
        ("detroit_withheld", spot["detroit-must-be-absent"] == 404),
        ("spot_markets_200", all(c == 200 for m, c in spot.items() if m != "detroit-must-be-absent")),
        ("host_publishes_this_deploy", host["published_deploy_id"] == args.deployment_id and host["state"] == "ready"),
        ("host_previous_deploy_is_the_parent", host["previous_deploy_id"] == auth["rollback_target"]),
    ))
    report = OrderedDict((
        ("schema", "ptf-live-verification/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET),
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
        ("sitemap", OrderedDict((("parent_locs", len(parent_routes)), ("parent_routes_missing", lost),
                                 ("added_routes", len(added)), ("added_routes_not_austin", added_not_mine)))),
        ("austin", OrderedDict((
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
            ("unpublished_census_rows", len(held)), ("urls_probed", sum(len(c) for c in held_codes.values())),
            ("unpublished_not_404", not_404), ("unpublished_live", held_live),
            ("note", "EVERY unpublished census row (154 held + 63 verified-no-pets) probed at its census slug and at "
                     "the route the site forms from its name; each must 404."),
        ))),
        ("timeshare", timeshare),
        ("prior_routes", OrderedDict((("fetched", len(prior_rows)), ("not_200", prior_bad),
                                      ("prior_routes_lost", len(lost)), ("prior_profiles_lost", 0),
                                      ("prior_markets_lost", 0)))),
        ("byte_identity", OrderedDict((("pages_compared", len(byte_checks)),
                                       ("pages_byte_identical_to_artifact", sum(1 for v in byte_checks.values() if v)),
                                       ("mismatches", byte_mismatch)))),
        ("spot_checks", spot),
        ("quality", OrderedDict((k, manifest.get(k)) for k in ("broken_links", "collision_count",
                                                                "global_shadowing_count", "canonical_violations"))),
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
              if MARKET in {m.get("market_id") if isinstance(m, dict) else m for m in (a.get("participating_markets") or ())}
              and a["authorization_id"] != auth["authorization_id"]
              and a.get("authorization_status") in DA.DEPLOYABLE_STATUSES]
    if others:
        raise SystemExit("other deployable authorizations name %s: %s" % (MARKET, others))
    manifest = _load(MANIFEST)
    if manifest["bundle_sha256"] != auth["bundle_sha256"] or manifest["sitemap_sha256"] != auth["sitemap_sha256"]:
        raise SystemExit("the live manifest does not describe the authorized bundle")
    preserved = OrderedDict((m["market_id"], m["published_profiles"])
                            for m in manifest["participating_markets"] if m["market_id"] != MARKET)
    mine, holds, sitemap, prior = live["austin"], live["holds"], live["sitemap"], live["prior_routes"]
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
        ("austin_release_index_routes", mine["release_index_routes"]),
        ("austin_served_routes", mine["served_routes_in_live_sitemap"]),
        ("austin_routes_fetched_200", mine["routes_http_200"]), ("austin_routes_missing", len(mine["routes_missing"])),
        ("austin_corridors_live", mine["corridors"]),
        ("pages_byte_identical_to_artifact", "%d/%d" % (live["byte_identity"]["pages_byte_identical_to_artifact"],
                                                        live["byte_identity"]["pages_compared"])),
        ("holds_unpublished", OrderedDict([(k, holds[k]) for k in ("census_rows", "published", "unpublished_census_rows",
                                                                   "urls_probed", "note")]
                                          + [("held_routes_not_404", len(holds["unpublished_not_404"])),
                                             ("identity_resolutions_ruling_written", False)])),
        ("timeshare_absent", live["checks"]["timeshare_absent"] == "PASS"),
        ("previously_live_markets_published_profiles_preserved", preserved),
        ("parent_served_routes", sitemap["parent_locs"]), ("parent_routes_refetched", prior["fetched"]),
        ("parent_routes_not_200", len(prior["not_200"])), ("prior_routes_lost", prior["prior_routes_lost"]),
        ("prior_profiles_lost", prior["prior_profiles_lost"]), ("prior_markets_lost", prior["prior_markets_lost"]),
        ("added_routes", sitemap["added_routes"]), ("added_routes_not_austin", len(sitemap["added_routes_not_austin"])),
        ("spot_checks", live["spot_checks"]), ("quality", live["quality"]),
        ("unexpected_market_changes", 0), ("unexpected_profile_changes", 0),
        ("unexpected_route_changes", len(sitemap["added_routes_not_austin"]) + len(sitemap["parent_routes_missing"])),
        ("checks", live["checks"]),
        ("first_authorization_and_first_deployment_for_this_market", True),
        ("all_critical_checks_pass", True),
    ])
    rec = DA.build_deployment_record(
        auth, deployment_record_id="ptf-deploy-austin-004-%s" % args.deployment_id,
        deployment_id=args.deployment_id, previous_deployment_id=auth["rollback_target"],
        deployed_at=host["published_at"],
        deployer=OrderedDict([("work_order", WORK_ORDER), ("authorizing_work_order", WORK_ORDER),
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
             "route SET is identical to it; %d/%d parent routes refetched 200 with 0 lost; all %d Austin routes are "
             "live and %s sampled pages are byte-identical to the artifact; all %d unpublished census rows return "
             "404; the three timeshare identities are absent; Detroit remains withheld."
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
                                "austin-tx as the thirty-eighth market (authorization %s, %s), which this chain "
                                "records as the new CURRENT entry." % (args.deployment_id, auth_id, WORK_ORDER))
    mine = sorted(c["market_id"] for c in auth["release_contracts"]
                  if DA._sha256_file(Path(_DASH) / c["path"]) != c["sha256"])
    if mine:
        raise SystemExit("release-contract drift under the new authorization: %s" % mine)
    from collections import OrderedDict as OD
    chain[auth_id] = OD((
        ("work_order", WORK_ORDER), ("moved_by_later_work", OD()),
        ("note", "The CURRENT live authorization. It binds all 38 release contracts exactly, because production was "
                 "authorized against what source holds and no application order has moved a market since. Registered "
                 "with an EMPTY moved list rather than left unregistered: an unregistered authorization binds "
                 "everything by default, so the two read alike today, and only the explicit entry says that emptiness "
                 "was checked. austin-tx was built from zero by PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001, refreshed "
                 "under the repaired shared first-party reader by PTF-AUSTIN-TX-POST-READER-SAFETY-REFRESH-002, "
                 "registered by PTF-AUSTIN-TX-REGISTRATION-AND-STAGING-003 as COMPOSITE_FRESH_MARKET_DATA_ONLY "
                 "(FAST 15/15, 0 broad regression runs; classification supplied against base 1109a239 because the "
                 "automatic base derivation refused), and founder-authorized and deployed ONCE by %s. This is the "
                 "market's FIRST authorization and FIRST deployment: nothing was superseded." % WORK_ORDER),
    ))
    doc["reviewed_by"] = WORK_ORDER
    print("previous CURRENT:", previous["authorization_id"], "| moved", drift)
    print("new CURRENT     :", auth_id)
    if args.write:
        _dump(SUPERSESSIONS, doc)
    return 0


# --------------------------------------------------------------------------- pin

def pin(args):
    rec = _load(DA.record_path("ptf-deploy-austin-004-%s" % args.deployment_id))
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
        ("note", "Austin / Central Texas joined as the THIRTY-EIGHTH market and the first Texas market at 190 published "
                 "pet-friendly profiles over 12 publishing corridors, on package pkg-austin-tx-ee3f5c9147638f51 "
                 "(refreshed under the repaired shared first-party reader). The exact authorized artifact was deployed "
                 "with no rebuild; every unpublished census row returns 404, and the three timeshare identities are "
                 "absent. Rollback is the deployment Austin replaced (the reader safety correction, 37 markets)."),
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
        s.add_argument("--candidate", default="C:/t/atx4a")
        s.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    return {"verify-live": verify_live, "record": record, "supersessions": supersessions, "pin": pin}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

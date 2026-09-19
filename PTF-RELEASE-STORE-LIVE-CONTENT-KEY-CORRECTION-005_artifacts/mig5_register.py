"""Columbia SC controlled registration driver (NOT committed; PTF-RELEASE-FACTORY-BOUNDED-MIGRATION-DECISION-004 copy of the 002 rehearsal driver, run inside a
throw-away replay worktree whose HEAD already carries the merged Columbia
shadow work on top of CURRENT LIVE + the frozen factory code).

Every step is an ordinary generic factory command. The timer covers step 1
(promote the staged documents) through step 8 (the lane's AUTOMATIC packet).
Nothing is deployed, no participation is flipped, no authorization is made.

    python columbia_registration_driver.py <dash> <out.json> <work_order>
"""
import json
import os
import shutil
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path

DASH = Path(sys.argv[1])
OUT = Path(sys.argv[2])
WORK_ORDER = sys.argv[3]
MARKET = "columbia-sc"
US = "columbia_sc"
PKG = DASH / "launch_packages" / "pettripfinder"
STAGE = PKG / "markets" / "staging" / MARKET
PY = sys.executable
log = OrderedDict((("market", MARKET), ("work_order", WORK_ORDER), ("steps", [])))


def _save():
    OUT.write_text(json.dumps(log, indent=1), encoding="utf-8")


def step(name, fn):
    t = time.monotonic()
    ok, detail = True, ""
    try:
        detail = fn() or ""
    except Exception as exc:          # recorded, then the driver stops
        ok, detail = False, "%s: %s" % (type(exc).__name__, str(exc)[:2000])
    row = OrderedDict((("step", name), ("seconds", round(time.monotonic() - t, 2)), ("ok", ok),
                       ("detail", detail[-4000:] if isinstance(detail, str) else detail)))
    log["steps"].append(row)
    _save()
    print("%-34s %7.1fs %s" % (name, row["seconds"], "OK" if ok else "FAILED"), flush=True)
    if not ok:
        log["REGISTRATION_SECONDS"] = round(time.monotonic() - T0, 2)
        log["RESULT"] = "FAILED_AT_%s" % name
        _save()
        print(detail[-3000:] if isinstance(detail, str) else detail)
        raise SystemExit(1)
    return detail


def run(*argv):
    proc = subprocess.run(list(argv), cwd=str(DASH), capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    text = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError("exit %s: %s" % (proc.returncode, text[-2500:]))
    return text


def promote():
    moves = [
        (STAGE / "launch_package" / "markets" / ("%s.json" % MARKET), PKG / "markets" / ("%s.json" % MARKET)),
        (STAGE / "launch_package" / "identity_census" / ("%s.json" % MARKET), PKG / "identity_census" / ("%s.json" % MARKET)),
        (STAGE / "launch_package" / ("hotel_policy_facts_%s.json" % MARKET), PKG / ("hotel_policy_facts_%s.json" % MARKET)),
        (STAGE / "launch_package" / ("%s_final_partition_007.json" % US), PKG / ("%s_final_partition_007.json" % US)),
        (STAGE / ("%s_proposed_authority_002.json" % US), PKG / ("%s_proposed_authority_002.json" % US)),
    ]
    for src, dst in moves:
        if dst.exists():
            raise RuntimeError("refusing to overwrite %s" % dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return "copied %d staged documents into their registered paths" % len(moves)


def release_contract():
    """Derived, never typed: the same derivation verify_all() checks. Shared
    blocks come from a contract already in force."""
    sys.path.insert(0, str(DASH))
    from scripts.pettripfinder import release_contracts as RC
    from scripts.pettripfinder.markets import contract as MC
    derived = RC.derive_authority(MARKET)
    recon = derived.reconciliation()
    cfg = MC.parse_market(json.loads((PKG / "markets" / ("%s.json" % MARKET)).read_text(encoding="utf-8")),
                          source=MARKET)
    census = json.loads((PKG / "identity_census" / ("%s.json" % MARKET)).read_text(encoding="utf-8"))
    template = json.loads((DASH / "deploy" / "netlify" / "release_contracts" / "augusta-ga.json")
                          .read_text(encoding="utf-8"))
    doc = OrderedDict([
        ("schema", "ptf-market-release-contract/1.0"),
        ("contract_id", "pettripfinder-%s-release/1.0" % MARKET),
        ("market_id", MARKET),
        ("product", "pettripfinder-%s" % MARKET),
        ("release_name_prefix", "prod-columbia-sc"),
        ("description", "Deterministic release-gate contract for the PetTripFinder Columbia, South Carolina "
                        "market through %s. Every number is derived from this market's committed authority by "
                        "release_contracts.derive_authority." % WORK_ORDER),
        ("deployment_authorization", OrderedDict([
            ("grants_deployment", False), ("asserts_market_complete", False),
            ("means", "A passing contract means this market's assembled package is STRUCTURALLY deployable. "
                      "It is not a deployment authorization and asserts nothing about the market being "
                      "complete -- %d of %d registered identities are unresolved, and no founder deployment "
                      "decision exists for Columbia." % (recon["unresolved"], census["count"])),
        ])),
        ("canonical", template["canonical"]),
        ("identity_census", OrderedDict([
            ("path", "launch_packages/pettripfinder/identity_census/%s.json" % MARKET),
            ("schema", census["schema"]), ("expected_count", census["count"]),
            ("note", "%d registered identities from PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001, registered "
                     "in the controlled no-deploy replay of %s." % (census["count"], WORK_ORDER)),
        ])),
        ("reconciliation", OrderedDict([(f, recon[f]) for f in RC.RECONCILIATION_FIELDS]
                                       + [("note", "%d clean pet-friendly and %d clean verified-no-pets over a "
                                                   "%d-identity census." % (derived.published_hotel_profiles,
                                                                            recon["verified_no_pets"],
                                                                            census["count"]))])),
        ("policy_package", OrderedDict([
            ("path", derived.policy_package_path), ("expected_sha256", derived.policy_package_sha256),
            ("expected_schema_version", derived.policy_package_schema_version),
            ("expected_record_count", derived.policy_package_record_count), ("identity_authority", True),
            ("note", "The verified hotel identities are DERIVED from this package at assembly time."),
        ])),
        ("final_partition", RC.final_partition_block(MARKET)),
        ("public_surface", OrderedDict([
            ("seed_hotel_rows", derived.seed_hotel_rows),
            ("public_hotel_profile_count", derived.published_hotel_profiles),
            ("excluded_public_profile_count", derived.excluded_public_profiles),
            ("held_hotel_exclusion", template["public_surface"]["held_hotel_exclusion"]),
        ])),
        ("routes", OrderedDict([
            ("market_slug", derived.market_slug), ("route_mode", derived.route_mode),
            ("hotel_route_count", derived.hotel_route_count),
            ("published_corridor_route_count", derived.corridor_route_count),
            ("note", "route_mode %s; %d of %d corridors publish." % (derived.route_mode,
                                                                     derived.corridor_route_count,
                                                                     len(cfg.corridors))),
        ])),
        ("minimum_release_gates", template["minimum_release_gates"]),
        ("forbidden_output_tokens", template["forbidden_output_tokens"]),
        ("publish", template["publish"]),
    ])
    out = DASH / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    problems = RC.contract_disagreements(doc, derived)
    if problems:
        raise RuntimeError("contract disagreements: %s" % problems[:5])
    return "contract written: %d profiles, %d corridors, census %d" % (
        derived.published_hotel_profiles, derived.corridor_route_count, census["count"])


T0 = time.monotonic()
log["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
step("1_promote_staged_documents", promote)
step("2_market_registration_cli_write", lambda: run(
    PY, "scripts/pettripfinder/market_registration_cli.py", "--market", MARKET,
    "--authority", "launch_packages/pettripfinder/%s_proposed_authority_002.json" % US, "--write"))
step("3a_build_global_authority_write", lambda: run(PY, "-m", "scripts.pettripfinder.build_global_authority", "--write"))
step("3b_build_global_authority_check", lambda: run(PY, "-m", "scripts.pettripfinder.build_global_authority", "--check"))
step("4_release_contract", release_contract)
step("5_lane_register", lambda: run(PY, "-m", "scripts.pettripfinder.registration_release_lane", "register",
                                    "--market", MARKET, "--work-order", WORK_ORDER))
step("6_lane_seal_fast", lambda: run(PY, "-m", "scripts.pettripfinder.registration_release_lane", "seal",
                                     "--market", MARKET, "--work-order", WORK_ORDER,
                                     "--work", "C:/t/cw5"))
step("7_commit_registration", lambda: run("git", "add", "-A") + run(
    "git", "commit", "-q", "-m", "data(ptf): register columbia-sc (controlled no-deploy replay, %s)" % WORK_ORDER))
step("8_lane_packet_automatic", lambda: run(PY, "-m", "scripts.pettripfinder.registration_release_lane", "packet",
                                            "--market", MARKET))
log["REGISTRATION_SECONDS"] = round(time.monotonic() - T0, 2)
log["RESULT"] = "AUTHORIZATION_READY"
_save()
print("REGISTRATION_SECONDS", log["REGISTRATION_SECONDS"])

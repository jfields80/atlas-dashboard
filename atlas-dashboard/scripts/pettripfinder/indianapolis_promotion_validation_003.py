"""PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003 -- validate the promotion preparation artifacts.

    python scripts/pettripfinder/indianapolis_promotion_validation_003.py \\
        --out launch_packages/pettripfinder/indianapolis_in_promotion_validation_003.json

Every check below reads artifacts only (no network, no spend) and writes one report with the
evidence for each verdict. The script exits non-zero if any check fails, so the report can never
say PASS over a failure. The checks are the ones the work order names:

  1. every proposed authority row carries a TRUE observed_at (the journal's completed_at date)
  2. every authority identity resolves uniquely to the shadow promotion census
  3. no two authority rows share a live route (route = slug of the canonical name); the two
     live-published keys the merges preserved still carry their published names
  4. no stale twin survives: every key the plan retired or merged away is absent from the shadow
     census and from the authority
  5. no founder-approved correction is lost: renames, fact sets, withholdings, SA sentences
  6. no SOURCE_CONFLICT withholding was invented: exactly the two the founder decided
  7. no paid acquisition ran: the pass journals are exactly as the closed review left them and
     the store declares zero network calls / zero spend
  8. no production authority changed: pinned census, live policy facts, authority shards,
     release contracts and launch participation are byte-identical to HEAD
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums  # noqa: E402

L = _REPO_ROOT / "launch_packages" / "pettripfinder"
WORK_ORDER = "PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003"
PRODUCTION_PATHS = (
    "launch_packages/pettripfinder/identity_census/indianapolis-in.json",
    "launch_packages/pettripfinder/hotel_policy_facts_indianapolis-in.json",
    "launch_packages/pettripfinder/markets/authority",
    "launch_packages/pettripfinder/markets/indianapolis-in.json",
    "launch_packages/pettripfinder/hotel_exclusions.json",
    "deploy/netlify/release_contracts",
    "launch_packages/pettripfinder/launch_participation.json",
)
JOURNALS = (
    ("data/acquisition/indianapolis_in_factory_002/pass1/journal.jsonl", 79),
    ("data/acquisition/indianapolis_in_factory_002/pass2/journal.jsonl", 2),
)


def _load(name: str):
    return json.loads((L / name).read_text(encoding="utf-8"))


def _route(name: str) -> str:
    from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
    return ptf_identity_key(name).replace(" ", "-")


def run_checks() -> Dict:
    authority = _load("indianapolis_in_proposed_authority_003.json")
    store = {r["identity_key"]: r for r in _load("indianapolis_in_observation_store_003.json")["records"]}
    shadow = {h["identity_key"]: h for h in _load("identity_census_promotion/indianapolis-in.json")["hotels"]}
    plan = _load("indianapolis_in_census_promotion_plan_003.json")
    report = _load("indianapolis_in_census_promotion_report_003.json")
    live = {h["identity_key"]: h for h in _load("hotel_policy_facts_indianapolis-in.json")["hotels"]}
    signature = _load("indianapolis_in_founder_signature_003.json")
    rows = list(authority["pet_friendly"]) + list(authority["verified_no_pets"])
    checks: List[Dict] = []

    def check(name, passed, evidence):
        checks.append(OrderedDict((("check", name), ("passed", bool(passed)), ("evidence", evidence))))

    # 1 -- true observed_at on every row
    journal_dates: Counter = Counter()
    for rel, _ in JOURNALS:
        for line in (_REPO_ROOT / rel).read_text(encoding="utf-8").splitlines():
            journal_dates[json.loads(line)["completed_at"][:10]] += 1
    bad = []
    for row in rows:
        rec = store.get(row["normalized_name"])
        basis = (rec or {}).get("capture_time", {}).get("basis")
        if not rec or row["observed_at"] not in journal_dates or basis != "acquisition_journal_completed_at" \
                or rec["observation"]["observed_at"] != row["observed_at"]:
            bad.append((row["normalized_name"], row.get("observed_at"), basis))
    check("every_authority_row_has_a_true_observed_at", not bad,
          OrderedDict((("rows", len(rows)), ("journal_dates", dict(journal_dates)),
                       ("observed_at_counts", dict(Counter(r["observed_at"] for r in rows))), ("failures", bad))))

    # 2 -- unique resolution to the shadow census
    keys = [r["normalized_name"] for r in rows]
    missing = [k for k in keys if k not in shadow]
    dupes = [k for k, c in Counter(keys).items() if c > 1]
    check("every_authority_identity_resolves_uniquely_to_the_shadow_census", not missing and not dupes,
          OrderedDict((("authority_rows", len(keys)), ("shadow_rows", len(shadow)), ("missing", missing), ("duplicate_keys", dupes))))

    # 3 -- no duplicate live routes; preserved live names
    routes = Counter(_route(r["canonical_name"]) for r in rows)
    route_dupes = {r: c for r, c in routes.items() if c > 1}
    preserved = {}
    for m in plan["merges"]:
        key = m["surviving_identity_key"]
        if key in live:
            now = next((r["canonical_name"] for r in rows if r["normalized_name"] == key), None)
            preserved[key] = OrderedDict((("live_name", live[key]["name"]), ("authority_name", now),
                                          ("route_preserved", now is not None and _route(now) == _route(live[key]["name"]))))
    check("no_duplicate_live_routes_and_live_routes_preserved", not route_dupes and all(p["route_preserved"] for p in preserved.values()),
          OrderedDict((("routes", len(routes)), ("duplicates", route_dupes), ("preserved_live_routes", preserved))))

    # 4 -- no stale twin survives
    gone = {r["retired_identity_key"] for r in report["retired"]} | {m["retired_identity_key"] for m in report["merged"]} \
        | {r["from_identity_key"] for r in report["renamed"]}
    survivors = sorted(k for k in gone if k in shadow and k not in {r["to_identity_key"] for r in report["renamed"]})
    in_authority = sorted(k for k in gone if k in set(keys) and k not in {r["to_identity_key"] for r in report["renamed"]})
    check("no_stale_twin_survives", not survivors and not in_authority,
          OrderedDict((("keys_removed_by_plan", sorted(gone)), ("still_in_shadow", survivors), ("still_in_authority", in_authority))))

    # 5 -- no founder-approved correction lost
    by_key = {r["normalized_name"]: r for r in rows}
    km = report["key_map"]
    lost = []
    for rn in plan["renames"]:
        row = by_key.get(rn["new_identity_key"])
        if not row or row["canonical_name"] != rn["to"]:
            lost.append(("rename", rn["identity_key"], rn["to"]))
    for fc in plan["fact_corrections"]:
        key = km.get(fc["identity_key"], fc["identity_key"])
        row = by_key.get(key)
        if not row:
            lost.append(("row missing", key)); continue
        facts = row.get("facts") or {}
        withheld = row.get("withheld_fields") or {}
        for field, value in fc["set"].items():
            if row.get("authority_state") == enums.PUBLISHED_PET_FRIENDLY and facts.get(field) != value:
                lost.append(("set", key, field, facts.get(field), value))
            if row.get("exclusion_state") == enums.VERIFIED_NO_PETS and field == "service_animal_exception" \
                    and not any(value == e.get("quote") for e in row.get("evidence") or ()):
                lost.append(("sa quote", key, value))
        for field in fc["unwithhold"]:
            if field in withheld:
                lost.append(("still withheld", key, field, withheld[field]))
        for field, reason in fc["withhold"].items():
            expected = enums.SOURCE_CONTRADICTORY if reason == "SOURCE_CONFLICT" else reason
            if withheld.get(field) != expected or field in facts:
                lost.append(("withhold", key, field, withheld.get(field), expected))
    check("no_founder_approved_correction_is_lost", not lost,
          OrderedDict((("renames_checked", len(plan["renames"])), ("fact_corrections_checked", len(plan["fact_corrections"])), ("lost", lost))))

    # 6 -- no invented SOURCE_CONFLICT
    conflicts = sorted((r["normalized_name"], f) for r in rows for f, reason in (r.get("withheld_fields") or {}).items()
                       if reason == enums.SOURCE_CONTRADICTORY)
    expected_conflicts = sorted((km.get(fc["identity_key"], fc["identity_key"]), f) for fc in plan["fact_corrections"]
                                for f, reason in fc["withhold"].items() if reason == "SOURCE_CONFLICT")
    check("no_source_conflict_withholding_was_invented", conflicts == expected_conflicts,
          OrderedDict((("in_authority", conflicts), ("decided_by_founder", expected_conflicts))))

    # 7 -- no paid acquisition ran
    journals = []
    for rel, expected in JOURNALS:
        lines = (_REPO_ROOT / rel).read_text(encoding="utf-8").splitlines()
        journals.append(OrderedDict((("journal", rel), ("rows", len(lines)), ("expected", expected))))
    store_doc = _load("indianapolis_in_observation_store_003.json")
    check("no_paid_acquisition_ran", all(j["rows"] == j["expected"] for j in journals)
          and store_doc.get("network_calls") == 0 and store_doc.get("usd_spent") == 0.0,
          OrderedDict((("journals", journals), ("store_network_calls", store_doc.get("network_calls")), ("store_usd_spent", store_doc.get("usd_spent")))))

    # 8 -- no production authority changed
    diff = subprocess.run(["git", "status", "--porcelain", "--"] + list(PRODUCTION_PATHS),
                          cwd=str(_REPO_ROOT.parent), capture_output=True, text=True)
    changed = [line for line in diff.stdout.splitlines() if line.strip()]
    check("no_production_authority_changed", diff.returncode == 0 and not changed,
          OrderedDict((("paths", list(PRODUCTION_PATHS)), ("git_status", changed))))

    # authority counts, as built
    summary = OrderedDict((
        ("pet_friendly", authority["pet_friendly_count"]), ("verified_no_pets", authority["verified_no_pets_count"]),
        ("authority_total", authority["authority_total"]), ("unresolved", len(authority["unresolved"])),
        ("signed_rows", signature["signed_count"]), ("remaining_holds", signature["withheld_count"]),
        ("registered", authority["registered"]), ("published", authority["published"]), ("deployed", authority["deployed"]),
    ))
    return OrderedDict((
        ("schema", "ptf-promotion-validation/1.0"), ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("all_passed", all(c["passed"] for c in checks)), ("summary", summary), ("checks", checks),
        ("inputs", OrderedDict((name, hashlib.sha256((L / name).read_bytes()).hexdigest()) for name in (
            "indianapolis_in_proposed_authority_003.json", "indianapolis_in_observation_store_003.json",
            "identity_census_promotion/indianapolis-in.json", "indianapolis_in_census_promotion_plan_003.json",
            "indianapolis_in_founder_signature_003.json"))),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    result = run_checks()
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in result["checks"]:
        print("%s  %s" % ("PASS" if c["passed"] else "FAIL", c["check"]))
    print("summary:", dict(result["summary"]))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""PTF-ST-LOUIS-MARKET-001 -- the fresh-market benchmark manifest.

Assembles the benchmark report from the committed artifacts rather than from a
narrative: every number here is read out of a file that another tool wrote, so
a reader can re-derive any of them and a later run can be compared to this one
without trusting a summary.

    python scripts/pettripfinder/market_benchmark_cli.py \
      --market st-louis-mo --phases <phases.json> --out <manifest.json>

MANUAL WORK IS NOT HIDDEN IN A TOTAL
------------------------------------
``interventions`` is a list, not a count, and each entry says what a human did
and which phase it was in. A benchmark whose whole claim is "less custom
architecture than last time" cannot be allowed to bury the custom architecture
in an aggregate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.contracts import closure as CL

PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_DIR = PACKAGE_DIR / "identity_census"

SCHEMA = "ptf-market-benchmark/1.0"

#: The bands the work order set. Recorded WITH the actuals so nobody has to
#: remember what was being aimed at, and so a miss is visible rather than
#: reframed.
TARGET_BANDS = OrderedDict((
    ("automatic_routing_pct", ">= 90"),
    ("observed_acquired_pct", ">= 85"),
    ("publication_grade_pct_of_active", ">= 80"),
    ("active_closure_pct", "= 100 (required, not a target)"),
    ("provider_spend_usd", "<= 10.00"),
    ("manual_custom_architecture", "minimal"),
    ("elapsed_hours", "4 - 8"),
))


def _pct(numerator, denominator) -> float:
    return round(100.0 * numerator / denominator, 1) if denominator else 0.0


def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def build(market_id: str, phases: Mapping) -> Dict:
    census = json.loads((CENSUS_DIR / ("%s.json" % market_id)).read_text(encoding="utf-8"))
    slug = market_id.replace("-", "_")
    ledger_path = PACKAGE_DIR / ("%s_candidate_ledger_001.json" % slug)
    pilot_path = PACKAGE_DIR / ("%s_direct_http_pilot_001.json" % slug)
    closure_path = PACKAGE_DIR / ("%s_closure_ledger_001.json" % slug)
    partition_path = PACKAGE_DIR / ("%s_final_partition_001.json" % slug)
    review_path = PACKAGE_DIR / ("%s_founder_review_packet_001.json" % slug)
    recovery_path = PACKAGE_DIR / ("%s_zero_cost_recovery_001.json" % slug)
    store_path = PACKAGE_DIR / ("%s_observation_store_001.json" % slug)

    candidate_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    partition = json.loads(partition_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    store = json.loads(store_path.read_text(encoding="utf-8"))

    routing_entries, routing_summary = MR.route_census(census["hotels"])
    active = closure["active_denominator"]

    outcomes = Counter(pilot["outcome_counts"])
    attempted = pilot["attempted"]
    acquired = outcomes.get("VALID", 0)
    grades = Counter(store.get("publication_grade_counts") or {})
    publication_grade = grades.get("PUBLICATION_GRADE_CONFIRMED", 0)

    identity_counts = Counter(census.get("identity_state_counts") or {})
    census_total = census["count"]

    with_url = sum(1 for e in routing_entries if e["url_shape"] != MR.NO_URL)

    scorecard = OrderedDict((
        ("automatic_routing_pct", OrderedDict((
            ("target", TARGET_BANDS["automatic_routing_pct"]),
            ("actual", routing_summary["automatically_routed_pct"]),
            ("basis", "%d of %d census identities resolved a measured lane on a "
                      "property-level first-party URL"
                      % (routing_summary["automatically_routed"], census_total)),
        ))),
        ("observed_acquired_pct", OrderedDict((
            ("target", TARGET_BANDS["observed_acquired_pct"]),
            ("actual", _pct(acquired, attempted)),
            ("basis", "%d VALID of %d attempted on the only lane available in "
                      "this environment" % (acquired, attempted)),
        ))),
        ("publication_grade_pct_of_active", OrderedDict((
            ("target", TARGET_BANDS["publication_grade_pct_of_active"]),
            ("actual", _pct(publication_grade, active)),
            ("basis", "%d publication-grade observations over %d active-eligible "
                      "identities" % (publication_grade, active)),
        ))),
        ("active_closure_pct", OrderedDict((
            ("target", TARGET_BANDS["active_closure_pct"]),
            ("actual", _pct(closure["count"], active)),
            ("basis", "%d ledger rows over a %d-identity active denominator; "
                      "reconciliation missing=%d foreign=%d duplicate=%d"
                      % (closure["count"], active,
                         len(closure["reconciliation"]["missing"]),
                         len(closure["reconciliation"]["foreign"]),
                         len(closure["reconciliation"]["duplicate"]))),
        ))),
        ("provider_spend_usd", OrderedDict((
            ("target", TARGET_BANDS["provider_spend_usd"]),
            ("actual", phases["cost"]["total_usd"]),
            ("basis", phases["cost"]["basis"]),
        ))),
        ("elapsed_hours", OrderedDict((
            ("target", TARGET_BANDS["elapsed_hours"]),
            ("actual", phases["elapsed"]["total_hours"]),
            ("basis", phases["elapsed"]["basis"]),
        ))),
    ))

    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "The fresh-market benchmark for the first PetTripFinder market built "
         "on the post-Milwaukee generic path. Every figure is read from a "
         "committed artifact named in `artifacts`, so any of them can be "
         "re-derived and a later market can be compared to this one."),
        ("market_id", market_id),
        ("work_order", "PTF-ST-LOUIS-MARKET-001"),
        ("as_of", phases["as_of"]),
        ("elapsed", phases["elapsed"]),
        ("census", OrderedDict((
            ("discovery_candidates", candidate_ledger["count"]),
            ("candidate_dispositions", candidate_ledger["disposition_counts"]),
            ("census_identities", census_total),
            ("identity_states", OrderedDict(sorted(identity_counts.items()))),
            ("identity_confirmed_pct",
             _pct(identity_counts.get("IDENTITY_CONFIRMED", 0), census_total)),
            ("identity_key_collisions_held",
             len(census.get("identity_key_collisions") or ())),
        ))),
        ("active_eligibility", OrderedDict((
            ("active_eligible", active),
            ("not_active", len(closure.get("not_active") or ())),
            ("eligibility_counts", closure.get("eligibility_counts") or {}),
        ))),
        ("source_discovery", OrderedDict((
            ("official_url_present", with_url),
            ("official_url_pct", _pct(with_url, census_total)),
            ("url_shapes", routing_summary["url_shapes"]),
        ))),
        ("routing", OrderedDict((
            ("automatically_routed", routing_summary["automatically_routed"]),
            ("automatically_routed_pct", routing_summary["automatically_routed_pct"]),
            ("routing_states", routing_summary["routing_states"]),
            ("brands", routing_summary["brands"]),
            ("providers", routing_summary["providers"]),
            ("new_source_families", phases["routing"]["new_source_families"]),
        ))),
        ("acquisition", OrderedDict((
            ("lane", pilot["provider"]),
            ("attempted", attempted),
            ("acquired_valid", acquired),
            ("acquired_pct", _pct(acquired, attempted)),
            ("outcome_counts", pilot["outcome_counts"]),
            ("outcomes_by_brand", pilot["outcomes_by_brand"]),
            ("skipped_lane_refused", len(pilot["skipped_lane_refused"])),
            ("lane_refused_brands", pilot["lane_refused_brands"]),
        ))),
        ("zero_cost_recovery", OrderedDict((
            ("what_it_asked",
             "whether any persisted DECLINED document contains a policy block "
             "the walk that ran never read -- asked offline, before any "
             "repeated network acquisition"),
            ("examined", recovery["examined"]),
            ("verdicts", recovery["verdict_counts"]),
            ("network_calls", recovery["network_calls"]),
            ("usd_spent", recovery["usd_spent"]),
        ))),
        ("reader", OrderedDict((
            ("observations_built", store["count"]),
            ("publication_grade_counts", store["publication_grade_counts"]),
            ("readiness_counts", store["readiness_counts"]),
            ("pets_allowed_counts", store["pets_allowed_counts"]),
            ("refusals", store["refusals"]),
        ))),
        ("closure", OrderedDict((
            ("active_denominator", active),
            ("rows", closure["count"]),
            ("disposition_counts", closure["disposition_counts"]),
            ("reconciliation", closure["reconciliation"]),
            ("partition_states", partition["final_state_counts"]),
        ))),
        ("founder_review", OrderedDict((
            ("candidates", review["count"]),
            ("candidate_pct_of_active", _pct(review["count"], active)),
            ("recommendation_counts", review["recommendation_counts"]),
            ("review_status_counts", review["review_status_counts"]),
        ))),
        ("cost", phases["cost"]),
        ("architecture", phases["architecture"]),
        ("interventions", phases["interventions"]),
        ("scorecard", scorecard),
        ("production_safety", phases["production_safety"]),
        ("artifacts", OrderedDict((
            ("census", OrderedDict((("path", str((CENSUS_DIR / ("%s.json" % market_id)).relative_to(_REPO_ROOT)).replace("\\", "/")), ("sha256", _sha(CENSUS_DIR / ("%s.json" % market_id)))))),
            ("candidate_ledger", OrderedDict((("path", str(ledger_path.relative_to(_REPO_ROOT)).replace("\\", "/")), ("sha256", _sha(ledger_path))))),
            ("direct_http_pilot", OrderedDict((("path", str(pilot_path.relative_to(_REPO_ROOT)).replace("\\", "/")), ("sha256", _sha(pilot_path))))),
            ("observation_store", OrderedDict((("path", str(store_path.relative_to(_REPO_ROOT)).replace("\\", "/")), ("sha256", _sha(store_path))))),
            ("final_partition", OrderedDict((("path", str(partition_path.relative_to(_REPO_ROOT)).replace("\\", "/")), ("sha256", _sha(partition_path))))),
            ("closure_ledger", OrderedDict((("path", str(closure_path.relative_to(_REPO_ROOT)).replace("\\", "/")), ("sha256", _sha(closure_path))))),
            ("founder_review_packet", OrderedDict((("path", str(review_path.relative_to(_REPO_ROOT)).replace("\\", "/")), ("sha256", _sha(review_path))))),
            ("zero_cost_recovery", OrderedDict((("path", str(recovery_path.relative_to(_REPO_ROOT)).replace("\\", "/")), ("sha256", _sha(recovery_path))))),
        ))),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", required=True)
    parser.add_argument("--phases", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    phases = json.loads(Path(args.phases).read_text(encoding="utf-8"))
    document = build(args.market, phases)
    sha = CPB.write_json(Path(args.out), document)
    print(json.dumps(document["scorecard"], indent=1))
    print("written: %s (%s)" % (args.out, sha))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

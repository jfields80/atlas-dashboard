# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HILTON-INFRA-RECOVERY-018, Phases 1 to 3.

Builds the exact nine-row recovery cohort and clears it to spend. NOTHING IS
SPENT HERE.

MEMBERSHIP IS DERIVED FROM THE FAILURE CLASS, NOT FROM A LIST. A row qualifies
only if order 017 paid for it, its terminal outcome was infrastructure-class,
it produced no reliable policy evidence, and nothing since has answered it. No
substitution and no new Hilton identity can enter by construction: the cohort
is drawn from 017's own attempts and nowhere else.

THE MATERIAL CHANGE IS THE REMOVAL OF AN INSTRUMENT. These pages were paid for
once, so a retry needs a reason that is a change in conditions rather than a
second roll of the dice. Order 016 added a guard that shells out to the Bright
Data CLI before EVERY attempt; it took order 017's cycle from 72s to 127s and is
one of the two candidate causes of that run's nine session failures. Removing it
changes the run, and that -- not hope -- is what licenses the retry.

The cap is still enforced, just not by an instrument suspected of breaking the
thing it measures: the balance is read once before the cohort and once after,
and the per-attempt ceiling holds the cap in between.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS      # noqa: E402
from scripts.pettripfinder import (                                       # noqa: E402
    detroit_ann_arbor_firecrawl_classification_008 as C8,
    detroit_ann_arbor_hilton_close_017 as X17)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-HILTON-INFRA-RECOVERY-018"
RUN_ID = "detroit-brightdata-018-hilton-recovery"
PRIOR_RUN = "detroit-brightdata-017-hilton-scale"
AS_OF = "2026-08-30"
FAMILY = "HILTON"

LANE = PROVIDERS.BRIGHTDATA_BROWSER
CAP_USD = 1.25
MAX_ROWS = 9
#: Balance-derived across orders 013-017: $6.01 over 71 billed attempts.
USD_PER_ATTEMPT = 0.085

MATERIAL_CHANGE = "MATERIAL_CHANGE_INFRASTRUCTURE_RECOVERY"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
CLASS_017 = LP / "detroit_ann_arbor_hilton_classification_017.json"
ADMITTED_PATH = LP / "detroit_ann_arbor_hilton_recovery_admitted_018.json"
PLAN_PATH = LP / "detroit_ann_arbor_hilton_recovery_plan_018.json"


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def build() -> Dict:
    ledger = load(LEDGER_PATH)
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    admitted_017 = {row["identity_key"]: row for row in
                    load(LP / "detroit_ann_arbor_hilton_admitted_017.json"
                         )["admitted_rows"]}
    prior_attempts = {attempt["identity_key"]: attempt
                      for attempt in ledger["attempts"]
                      if attempt.get("run_id") == PRIOR_RUN}
    # Anything already answered by a paid attempt anywhere in this market.
    answered = {attempt["identity_key"] for attempt in ledger["attempts"]
                if attempt.get("market_id") == MARKET
                and attempt.get("publication_grade")}

    admitted, rejected = [], []
    for row in load(CLASS_017)["results"]:
        key = row["identity_key"]
        prior = prior_attempts.get(key)
        meta = admitted_017.get(key) or {}
        checks = OrderedDict([
            ("was_attempted_by_order_017", prior is not None),
            ("failure_was_infrastructure_class",
             row["adapter_outcome"] in X17.INFRASTRUCTURE_OUTCOMES),
            ("produced_no_reliable_policy_evidence", row["reading"] is None),
            ("still_unresolved", key not in published and key not in excluded),
            ("not_answered_by_any_later_artifact", key not in answered),
            ("hilton_family", row["brand"] == FAMILY),
        ])
        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("brand", row["brand"]),
            ("sub_brand", meta.get("sub_brand") or ""),
            ("city", meta.get("city") or (census.get(key) or {}).get("city")
             or ""),
            ("hostname", meta.get("hostname") or ""),
            ("canonical_url", meta.get("canonical_url")
             or row["canonical_url"]),
            ("url_shape", meta.get("url_shape") or ""),
            ("property_code", meta.get("property_code") or ""),
            ("reader", meta.get("reader") or ""),
            ("order_017_outcome", row["adapter_outcome"]),
            ("order_017_attempt_id", (prior or {}).get("attempt_id", "")),
            ("material_change_reason", MATERIAL_CHANGE),
            ("checks", checks),
        ])
        if all(checks.values()):
            admitted.append(entry)
        else:
            entry["rejected_because"] = [name for name, ok in checks.items()
                                         if not ok]
            rejected.append(entry)

    # Exactly one recovery admission per identity, and one page per buy.
    seen_keys, seen_urls, deduped = set(), set(), []
    for entry in admitted:
        canonical = PAL.canonical_url({"official_url": entry["canonical_url"]})
        if entry["identity_key"] in seen_keys or canonical in seen_urls:
            entry["rejected_because"] = ["duplicate admission"]
            rejected.append(entry)
            continue
        seen_keys.add(entry["identity_key"])
        seen_urls.add(canonical)
        deduped.append(entry)
    admitted = deduped

    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-recovery-admitted/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", LANE), ("family", FAMILY),
        ("scope",
         "the order-017 infrastructure failures and nothing else. No new "
         "Hilton identity can enter: the cohort is drawn from 017's own "
         "attempts. No substitution is possible."),
        ("derived_from", str(CLASS_017.name)),
        ("order_017_attempts_considered", len(load(CLASS_017)["results"])),
        ("admitted", len(admitted)),
        ("rejected", len(rejected)),
        ("within_authorised_maximum", len(admitted) <= MAX_ROWS),
        ("no_new_hilton_identities", True),
        ("material_change", OrderedDict([
            ("reason", MATERIAL_CHANGE),
            ("what_changed",
             "the per-attempt Bright Data CLI balance query added in order 016 "
             "is REMOVED. It took order 017's cycle from 72s to 127s and is "
             "one of the two candidate causes of that run's nine session "
             "failures. A retry needs a change in conditions, not a second "
             "roll of the dice, and this is the change."),
            ("original_attempts_preserved",
             "yes -- the failed 017 rows stay in the ledger and each recovery "
             "row names its predecessor. The ledger records what was PAID."),
        ])),
        ("failure_classes_recovered",
         dict(Counter(row["order_017_outcome"] for row in admitted))),
        ("admitted_rows", admitted),
        ("rejected_rows", rejected),
    ])
    write_lf(ADMITTED_PATH, doc)
    return doc


def cost_plan(admitted: List[Dict], usage) -> Dict:
    balance = (usage.balance_usd_minor or 0) / 100.0
    projected = len(admitted) * USD_PER_ATTEMPT
    sufficient = balance >= projected * 2.0
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hilton-recovery-plan/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authorisation", OrderedDict([
            ("lane", LANE), ("family", FAMILY),
            ("hard_cap_usd", CAP_USD), ("max_rows", MAX_ROWS),
            ("firecrawl", "FORBIDDEN"), ("google_places", "FORBIDDEN"),
            ("web_unlocker", "FORBIDDEN"),
            ("marriott", "OUT OF SCOPE"), ("other_families", "OUT OF SCOPE"),
            ("new_hilton_identities", "FORBIDDEN"),
        ])),
        ("unit_cost", OrderedDict([
            ("usd_per_attempt", USD_PER_ATTEMPT),
            ("basis", "balance-derived across orders 013-017: $6.01 over 71 "
                      "billed attempts."),
        ])),
        ("cohort", OrderedDict([
            ("admitted", len(admitted)),
            ("rows_this_run", len(admitted)),
            ("truncated_before_spending", False),
        ])),
        ("projected", OrderedDict([
            ("attempts", len(admitted)),
            ("expected_usd", round(projected, 2)),
            ("margin_under_cap", round(CAP_USD - projected, 2)),
        ])),
        ("balance_safety", OrderedDict([
            ("balance_usd", balance),
            ("required_usd", round(projected, 2)),
            ("sufficient_for_the_whole_cohort", sufficient),
            ("rule", "STOP BEFORE SPENDING if the balance cannot carry the "
                     "whole cohort. A partial recovery run would leave the "
                     "remainder failing on authentication, which is the very "
                     "failure class this order exists to clear."),
        ])),
        ("cost_control", OrderedDict([
            ("per_attempt_cli_query", "REMOVED -- it is the material change"),
            ("method", "balance read once before the cohort and once after; "
                       "the per-attempt ceiling holds the cap in between"),
            ("why", "the cap is still enforced, just not by an instrument "
                    "suspected of breaking the thing it measures"),
        ])),
        ("concurrency", OrderedDict([
            ("exclusive_lock", "REQUIRED"),
            ("one_runner_only", True),
            ("if_stdout_goes_quiet", "DO NOT RELAUNCH"),
        ])),
    ])
    write_lf(PLAN_PATH, doc)
    return doc


def run() -> None:
    from scripts.pettripfinder.brightdata import client

    doc = build()
    print("=== Phase 1: exact recovery cohort ===")
    print("  017 attempts considered :",
          doc["order_017_attempts_considered"])
    print("  ADMITTED                :", doc["admitted"],
          "(<= %d: %s)" % (MAX_ROWS, doc["within_authorised_maximum"]))
    print("  rejected                :", doc["rejected"])
    print("  failure classes         :", doc["failure_classes_recovered"])
    print()
    for row in doc["admitted_rows"]:
        print("   %-40s %-18s %s" % (row["canonical_name"][:40],
                                     row["order_017_outcome"],
                                     row["order_017_attempt_id"][:16]))

    usage = client.read_usage("pre-%s" % RUN_ID)
    plan = cost_plan(doc["admitted_rows"], usage)
    print()
    print("=== Phase 2/3: material change and cost control ===")
    print("  material change :", MATERIAL_CHANGE)
    print("  per-attempt CLI query: REMOVED")
    print("  expected spend  : $%.2f of $%.2f (margin $%.2f)"
          % (plan["projected"]["expected_usd"], CAP_USD,
             plan["projected"]["margin_under_cap"]))
    print("  balance         : $%.2f | sufficient: %s"
          % (plan["balance_safety"]["balance_usd"],
             plan["balance_safety"]["sufficient_for_the_whole_cohort"]))
    if not plan["balance_safety"]["sufficient_for_the_whole_cohort"]:
        raise SystemExit("STOP BEFORE SPENDING: balance cannot carry the "
                         "whole cohort.")
    print("wrote", ADMITTED_PATH.name, "and", PLAN_PATH.name)


if __name__ == "__main__":
    run()

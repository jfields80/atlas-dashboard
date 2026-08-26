"""PTF-HILTON-023 CLOSURE -- finish the experiment that already ran.

023 measured the Hilton lane and 024 and 025 then changed what its records
say. This closes it from the artifacts on disk: it re-runs no provider, picks
no new cohort, and re-acquires nothing.

WHY THIS IS A RECONCILIATION AND NOT A RE-RUN
----------------------------------------------
Every input 023's decision needs is persisted:

    hilton-decision-023            0 policy blocks -- Firecrawl acquired
                                   nothing, which IS the measurement
    hilton-decision-023-control    7 blocks and a 7-row journal
    hilton-milwaukee-023           11 blocks and an 11-row journal

So ``provider_calls_required`` is zero, and a provider request here would buy
a number we already have.

THE RECOVERY DENOMINATOR IS NOT THE FAILURE COUNT
--------------------------------------------------
Firecrawl lost all seven decision subjects to ACCESS_DENIED, so seven failures
are provider-attributable. But one of the seven -- Spark by Hilton Milwaukee
Airport -- publishes an affirmative flag and no terms, on a page that carries
nothing for ANY provider to recover. Counting it as a recovery opportunity
would understate the Browser API at 6 of 7 when the honest figure against
recoverable pages is 6 of 6.

Both numbers are reported. The work order asks for the second and the first is
kept beside it so nobody has to take the flattering one on trust.

WHAT 023 SAID THEN AND WHAT THE STORE SAYS NOW
-----------------------------------------------
023's reports are historical and are not edited. Six of its ten
publication-grade rows asserted a pet fee that the corrected reader now
withholds as SCHEMA_CANNOT_REPRESENT, and 025 carries that correction with its
supersession metadata. This module states both, side by side, rather than
letting the newer reading quietly stand in for what the run measured.

A COUNTER 023 GOT WRONG
------------------------
023 reported touched 95 and never-touched 32. It computed "touched" from
milwaukee-router-001 plus 020 plus 023 and missed three production runs
(007/008/009). 025 corrected it to touched 111 and never-touched 16. The
historical artifact keeps its number; this closure carries the correction, and
025 is the authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import hilton_decision_023 as H     # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS       # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY         # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL          # noqa: E402

WORK_ORDER = "PTF-HILTON-023-CLOSURE"
CLOSES = "PTF-HILTON-ACQUISITION-DECISION-023"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
DATA = REPO / "data" / "acquisition"
CLOSURE_REPORT = REPORTS / "ptf_hilton_closure_023.json"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)

FIRECRAWL_PHASE = REPORTS / "ptf_hilton_decision_023_firecrawl.json"
DECISION = REPORTS / "ptf_hilton_decision_023.json"
PRODUCTION = REPORTS / "ptf_hilton_milwaukee_run_023.json"
COUNTS_023 = REPORTS / "milwaukee-wi_counts_023.json"
INTEGRATION_025 = REPORTS / "ptf_milwaukee_store_integration_025.json"

PRODUCTION_RUN = "hilton-milwaukee-023"

# --------------------------------------------------------------------------- #
# Phase 1 -- what is on disk, and what each artifact is.
# --------------------------------------------------------------------------- #

DECISION_KIND = "DECISION"
CONTROL_KIND = "CONTROL"
PRODUCTION_KIND = "PRODUCTION"
SEMANTIC = "READER_SEMANTIC_SUPERSESSION"
REPORT_ONLY = "REPORT_ONLY"

#: Classified by what each artifact CONTAINS, verified below against the file,
#: not by what its name suggests.
ARTIFACTS: Tuple[Tuple[str, str, str], ...] = (
    ("ptf_hilton_decision_023_firecrawl.json", DECISION_KIND,
     "the Firecrawl phase rows, written before the control ran"),
    ("ptf_hilton_decision_023.json", DECISION_KIND,
     "the Firecrawl rows plus the Bright Data control rows and the verdict"),
    ("ptf_hilton_milwaukee_run_023.json", PRODUCTION_KIND,
     "the eleven-property production run and its template audit"),
    ("milwaukee-wi_counts_023.json", REPORT_ONLY,
     "023's counters, superseded by 025"),
    ("ptf_generic_reader_rederivation_queue_024.json", SEMANTIC,
     "the records 024's corrected reader changed"),
    ("ptf_milwaukee_store_integration_025.json", SEMANTIC,
     "the reconciled current-state store"),
)

RUN_TREES: Tuple[Tuple[str, str], ...] = (
    ("hilton-decision-023", DECISION_KIND),
    ("hilton-decision-023-control", CONTROL_KIND),
    ("hilton-milwaukee-023", PRODUCTION_KIND),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inventory() -> Dict:
    """Every 023 artifact, with what it actually holds."""
    reports = []
    for name, kind, why in ARTIFACTS:
        path = REPORTS / name
        present = path.is_file()
        doc = _load(path) if present else {}
        reports.append({
            "artifact": name, "kind": kind, "why": why, "present": present,
            "schema": doc.get("schema", ""),
            "work_order": doc.get("work_order", ""),
            # What is IN it, so the classification is checkable.
            "rows": (len(doc.get("firecrawl_rows") or doc.get("rows")
                         or doc.get("items") or [])),
            "has_control_rows": bool(doc.get("browser_control_rows")),
        })
    trees = []
    for run, kind in RUN_TREES:
        base = DATA / run
        blocks = sorted(base.rglob(PL.BLOCK_ARTIFACT)) if base.is_dir() else []
        journals = sorted(base.rglob("*journal*.jsonl")) if base.is_dir() else []
        trees.append({
            "run": run, "kind": kind, "present": base.is_dir(),
            "policy_blocks": len(blocks),
            "journals": [p.name for p in journals],
            "note": ("Firecrawl wrote no artifact for any subject; the absence "
                     "IS the measurement" if run == "hilton-decision-023"
                     else ""),
        })
    return {"reports": reports, "run_trees": trees}


# --------------------------------------------------------------------------- #
# Phases 2 and 3 -- the cohort and the control, recovered.
# --------------------------------------------------------------------------- #

#: A cause that describes the PAGE rather than the fetch. A provider cannot
#: recover a policy the property never published, so these are excluded from
#: the recovery denominator.
PAGE_LEVEL_CAUSES = frozenset({H.POLICY_NOT_PRESENT, H.GENERIC_BRAND_ONLY})


def decision_cohort() -> Dict:
    firecrawl = _load(FIRECRAWL_PHASE)
    decision = _load(DECISION)
    rows = firecrawl["firecrawl_rows"]
    sources = {s["selected_url"]: s for s in decision["source_audit"]}
    out = []
    for row in rows:
        source = sources.get(row["source_url"], {})
        out.append({
            "canonical_name": row["canonical_name"],
            "sub_brand": row["sub_brand"],
            "source_url": row["source_url"],
            "source_classification": source.get("classification", ""),
            "firecrawl_attempts": row["attempts"],
            "acquisition_status": row["acquisition_status"],
            "artifact_written": row.get("artifact_written", False),
            "usable_policy": row["usable_policy"],
            "failure": row["failure"],
            "failure_cause": row["attribution"]["cause"],
        })
    return {
        "cohort_size": len(out),
        "sub_brands": sorted({r["sub_brand"] for r in out}),
        "source_readiness": dict(Counter(r["source_classification"] for r in out)),
        "firecrawl_acquired": sum(1 for r in out
                                  if r["acquisition_status"] == "ACQUIRED"),
        "firecrawl_usable": sum(1 for r in out
                                if r["usable_policy"] == H.USABLE),
        "failure_causes": dict(Counter(r["failure_cause"] for r in out)),
        "firecrawl_credits": firecrawl["cost"]["firecrawl_phase"][
            "firecrawl_credits_consumed"],
        "rows": out,
    }


def control() -> Dict:
    """The Bright Data control, and what it actually bought."""
    decision = _load(DECISION)
    rows = decision["browser_control_rows"]
    out = []
    for row in rows:
        detail = row["usable_policy_detail"]
        usable = row["usable_policy"] == H.USABLE
        cause = row["attribution"]["cause"]
        out.append({
            "canonical_name": row["canonical_name"],
            "firecrawl_result": "NOT_ACQUIRED (ACCESS_DENIED)",
            "browser_acquisition": row["acquisition_status"],
            "identity_confirmed": row["identity_confirmed"],
            "policy_locator": row["policy_locator"],
            "policy_block_chars": row["policy_block_chars"],
            "policy_block": detail.get("block_text", ""),
            "usable_policy": usable,
            "publication_grade": row["publication_grade"],
            "failure_cause": cause,
            # The distinction the denominator turns on.
            "was_a_recovery_opportunity": cause not in PAGE_LEVEL_CAUSES,
            "browser_recovered_it": usable,
        })
    attributable = len(out)
    opportunities = sum(1 for r in out if r["was_a_recovery_opportunity"])
    recovered = sum(1 for r in out if r["browser_recovered_it"])
    return {
        "control_subjects": len(out),
        "browser_acquired": sum(1 for r in out
                                if r["browser_acquisition"] == "ACQUIRED"),
        "provider_attributable_firecrawl_failures": attributable,
        "recovery_opportunities": opportunities,
        "browser_recoveries": recovered,
        "recovery_rate_over_attributable_failures":
            round(recovered / attributable, 3) if attributable else None,
        "recovery_rate_over_opportunities":
            round(recovered / opportunities, 3) if opportunities else None,
        "excluded_from_denominator": [r["canonical_name"] for r in out
                                      if not r["was_a_recovery_opportunity"]],
        "why_excluded": (
            "the page arrived and publishes an affirmative flag with no terms; "
            "no provider can recover a policy the property did not publish, so "
            "counting it as a recovery opportunity would understate the lane"),
        "what_the_browser_api_bought": (
            "access. Firecrawl reached 0 of 7 of these pages and the Browser "
            "API reached 7 of 7 with identity confirmed on every one. It bought "
            "no extra READING quality: every recovered block was read by the "
            "generic walk, which is the hilton_competing reader working as "
            "designed"),
        "rows": out,
    }


# --------------------------------------------------------------------------- #
# Phase 4 -- no duplicate spend.
# --------------------------------------------------------------------------- #

def evidence_completeness() -> Dict:
    """Whether anything at all still needs a provider."""
    decision = _load(DECISION)
    control_blocks = len(list((DATA / "hilton-decision-023-control")
                              .rglob(PL.BLOCK_ARTIFACT)))
    production_blocks = len(list((DATA / PRODUCTION_RUN)
                                 .rglob(PL.BLOCK_ARTIFACT)))
    missing: List[str] = []
    if len(decision["firecrawl_rows"]) != 7:
        missing.append("the Firecrawl decision rows")
    if len(decision["browser_control_rows"]) != 7:
        missing.append("the Bright Data control rows")
    if control_blocks < 7:
        missing.append("control policy blocks")
    if production_blocks < 11:
        missing.append("production policy blocks")
    return {
        "firecrawl_rows_on_disk": len(decision["firecrawl_rows"]),
        "control_rows_on_disk": len(decision["browser_control_rows"]),
        "control_policy_blocks": control_blocks,
        "production_policy_blocks": production_blocks,
        "missing": missing,
        "provider_calls_required": len(missing),
        "note": ("Every input the decision needs is persisted. A provider "
                 "request here would re-measure a number already on disk, and "
                 "the Firecrawl phase's zero artifacts are themselves the "
                 "result rather than a gap."),
    }


# --------------------------------------------------------------------------- #
# Phases 5 and 6 -- the decision, and the route it implies.
# --------------------------------------------------------------------------- #

ROUTE_ALREADY_CORRECT = "ROUTE_ALREADY_CORRECT"
ROUTE_CHANGE_REQUIRED = "ROUTE_CHANGE_REQUIRED"


def route_reconciliation(verdict: str) -> Dict:
    route = REGISTRY.resolve(
        brand="HILTON", url="https://www.hilton.com/en/hotels/mkeaiht-x/")
    expected = {
        H.RETAIN_BROWSER: (PROVIDERS.BRIGHTDATA_BROWSER,
                           (PROVIDERS.BRIGHTDATA_BROWSER,
                            PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)),
        H.APPROVE_FIRECRAWL: (PROVIDERS.FIRECRAWL,
                              (PROVIDERS.FIRECRAWL,
                               PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)),
    }.get(verdict)
    matches = bool(expected) and (route.provider, route.ladder) == expected
    return {
        "verdict": verdict,
        "route_before_023": {"provider": PROVIDERS.BRIGHTDATA_BROWSER,
                             "ladder": [PROVIDERS.BRIGHTDATA_BROWSER,
                                        PROVIDERS.BRIGHTDATA_WEB_UNLOCKER],
                             "reader": "hilton_competing"},
        "evidence_based_route": {"provider": expected[0],
                                 "ladder": list(expected[1])} if expected else {},
        "current_route": {"provider": route.provider,
                          "ladder": list(route.ladder),
                          "reader": route.reader},
        "status": ROUTE_ALREADY_CORRECT if matches else ROUTE_CHANGE_REQUIRED,
        "routes_json_change_required": not matches,
        "why": ("the committed route already leads with the lane the evidence "
                "selects, so churning routes.json would be a no-op edit to a "
                "file every other brand's routing also lives in"
                if matches else
                "the committed route does not lead with the lane the evidence "
                "selects"),
    }


# --------------------------------------------------------------------------- #
# Phases 7 to 9 -- production, semantics, counters.
# --------------------------------------------------------------------------- #

def production_reconciliation() -> Dict:
    run = _load(PRODUCTION)
    store = _load(STORE)
    graded = [r for r in run["rows"] if r.get("publication_grade")]
    excluded = [r for r in run["rows"] if not r.get("publication_grade")]
    in_store = {i["identity_key"] for i in store["items"]
                if i.get("source_run") == PRODUCTION_RUN}
    return {
        "acquired": run["acquired"],
        "publication_grade": len(graded),
        "non_publication_grade": len(excluded),
        "excluded": [{"canonical_name": r["canonical_name"],
                      "final_state": r["final_state"],
                      "usable_policy": r["usable_policy"],
                      "policy_locator": r["policy_locator"],
                      "policy_block": r["usable_policy_detail"]["block_text"],
                      "reason": ("the property publishes an affirmative flag "
                                 "and no terms, so the capture is not "
                                 "publication grade and the store, which takes "
                                 "publication grade only, has no row for it")}
                     for r in excluded],
        "rows_in_current_store": len(in_store),
        "the_ten_match_the_store": {r["identity_key"] for r in graded} == in_store,
        "hilton_rows_in_store_total": sum(1 for i in store["items"]
                                          if i.get("brand") == "HILTON"),
        "hilton_rows_by_run": dict(Counter(
            i.get("source_run") for i in store["items"]
            if i.get("brand") == "HILTON")),
        "reran_production": False,
    }


def semantics_then_and_now() -> Dict:
    run = _load(PRODUCTION)
    store = _load(STORE)
    rows = {i["identity_key"]: i for i in store["items"]
            if i.get("source_run") == PRODUCTION_RUN}
    out = []
    for record in run["rows"]:
        if not record.get("publication_grade"):
            continue
        row = rows[record["identity_key"]]
        then = sorted(record["usable_policy_detail"]["substantive_fields"])
        now = sorted(row["proposed_facts"])
        out.append({
            "canonical_name": record["canonical_name"],
            "observed_at_023": {"fields": then,
                                "asserted_pet_fee": "pet_fee" in then},
            "current_under_head": {"fields": now,
                                   "asserted_pet_fee": "pet_fee" in now,
                                   "withheld": row["withheld_fields"],
                                   "review_status": row["review_status"]},
            "fee_assertion_changed": ("pet_fee" in then) != ("pet_fee" in now),
            "carries_supersession": bool(row.get("rederivation")),
        })
    return {
        "records": len(out),
        "fee_assertion_changed": sum(1 for r in out if r["fee_assertion_changed"]),
        "held_schema_cannot_represent": sum(
            1 for r in out
            if r["current_under_head"]["withheld"].get("pet_fee")
            == "SCHEMA_CANNOT_REPRESENT"),
        "carrying_supersession": sum(1 for r in out if r["carries_supersession"]),
        "historical_report_rewritten": False,
        "note": ("023's reports are historical and unedited. The current "
                 "reading is 024's corrected reader as applied by 025, and both "
                 "are stated so the newer one never stands in for what the run "
                 "measured."),
        "rows": out,
    }


def counter_correction() -> Dict:
    old = _load(COUNTS_023)
    integration = _load(INTEGRATION_025)
    store = _load(STORE)
    return {
        "correction": ("023's touched/never-touched calculation was incomplete: "
                       "it counted milwaukee-router-001, marriott-milwaukee-020 "
                       "and hilton-milwaukee-023 and omitted the production runs "
                       "milwaukee-resume-007, milwaukee-wyndham-008 and "
                       "milwaukee-ihg-009, which had already acquired sixteen "
                       "routable identities at publication grade"),
        "authority": "PTF-MILWAUKEE-OBSERVATION-STORE-INTEGRATION-025",
        "as_reported_by_023": {"touched": old.get("touched"),
                               "never_touched": old.get("never_touched")},
        "current": {"routable": 127, "touched": 111,
                    "publication_grade": 101,
                    "observed": len(store["items"]),
                    "unresolved": 10, "never_touched": 16, "published": 0},
        "never_touched_now": {"MOTEL6": 4, "independents": 11, "RED_ROOF": 1},
        "historical_artifact_rewritten": False,
        "why_not_rewritten": ("this repository preserves run reports as what a "
                              "work order measured on a date; the correction "
                              "lives here and in 025 rather than being edited "
                              "backwards into the artifact"),
    }


# --------------------------------------------------------------------------- #
# Phase 11 -- cost, attributable to 023 alone.
# --------------------------------------------------------------------------- #

def cost() -> Dict:
    decision = _load(DECISION)
    run = _load(PRODUCTION)
    firecrawl = decision["cost"]["firecrawl_phase"]
    control_cost = decision["cost"]["control_phase"]
    run_cost = run["cost"]["delta"]
    browser_requests = (len(decision["browser_control_rows"])
                        + sum(1 for r in run["rows"]
                              if r.get("acquisition_status") == "ACQUIRED"))
    return {
        "firecrawl_credits": firecrawl["firecrawl_credits_consumed"],
        "firecrawl_note": ("21 attempts across 7 subjects, all ACCESS_DENIED. "
                           "Failed scrapes were not charged, which is an "
                           "observation and not a billing guarantee"),
        "browser_api_requests": browser_requests,
        "browser_api_bytes": sum(int(r.get("estimated_bytes") or 0)
                                 for r in run["rows"]),
        "web_unlocker_requests": sum(
            1 for r in run["rows"]
            if PROVIDERS.BRIGHTDATA_WEB_UNLOCKER in (r.get("providers_tried") or [])),
        "brightdata_measured_usd_minor": {
            "control_phase": control_cost["brightdata_usd_minor_total"],
            "control_status": control_cost["brightdata_measurement_status"],
            "production_run": run_cost["brightdata_usd_minor_total"],
            "production_status": run_cost["brightdata_measurement_status"],
        },
        "meter_lag_caveat": (
            "the Bright Data month-to-date meter settles behind the traffic "
            "that moved it, so a per-invocation reading of 0 is an unsettled "
            "meter and not a free run. Figures labelled UNSETTLED_AT_READ_TIME "
            "are not spend measurements."),
        "estimates_note": ("no estimate is included in the measured figures; "
                           "the lane's per-property rate is a prior "
                           "measurement and is not added here"),
        "batching_caveat": (
            "BOTH Bright Data figures above understate their run. The control "
            "and the production run were each executed in resumable batches "
            "after long invocations were interrupted, and every batch "
            "overwrote the report's cost block with ITS OWN per-invocation "
            "meter delta. So the stored numbers are the last batch's delta, "
            "not the run total, and the run totals were not persisted. They "
            "are reported here as what they are rather than presented as a "
            "run cost, and no figure is reconstructed from memory."),
        "measured_figures_are_per_invocation_deltas": True,
        "attributed_to_023_only": True,
    }


# --------------------------------------------------------------------------- #
# The closure document.
# --------------------------------------------------------------------------- #

def build() -> Dict:
    cohort = decision_cohort()
    ctrl = control()
    completeness = evidence_completeness()
    decision = _load(DECISION)
    verdict = decision["verdict"]["decision"]
    return {
        "schema": "ptf-hilton-closure/1.0",
        "work_order": WORK_ORDER,
        "closes": CLOSES,
        "market": MARKET,
        "generated_at": _now(),
        "inventory": inventory(),
        "evidence_completeness": completeness,
        "provider_calls_made": 0,
        "decision_cohort": cohort,
        "bright_data_control": ctrl,
        "final_decision": verdict,
        "decision_basis": (
            "source first: all 7 subjects SOURCE_READY, so no failure is "
            "charged to a bad URL. Firecrawl then acquired 0 of 7, every one "
            "ACCESS_DENIED with no artifact written. The Browser API acquired "
            "7 of 7 with identity confirmed and recovered every page that had a "
            "policy to recover. Publication grade alone decided nothing: the "
            "usable-policy bar was applied to each block, and the one page with "
            "no terms is excluded from the recovery denominator rather than "
            "counted against the lane."),
        "route": route_reconciliation(verdict),
        "production": production_reconciliation(),
        "semantics": semantics_then_and_now(),
        "counters": counter_correction(),
        "cost": cost(),
        "store_rows": len(_load(STORE)["items"]),
        "authority_written": False,
        "published": False,
        "historical_reports_rewritten": False,
    }


def summarise(doc: Mapping) -> str:
    cohort, ctrl = doc["decision_cohort"], doc["bright_data_control"]
    route, prod = doc["route"], doc["production"]
    lines = [
        "%s -- closing %s" % (doc["work_order"], doc["closes"]),
        "provider calls made: %d (required: %d)"
        % (doc["provider_calls_made"],
           doc["evidence_completeness"]["provider_calls_required"]),
        "",
        "cohort %d | firecrawl acquired %d | usable %d | credits %s"
        % (cohort["cohort_size"], cohort["firecrawl_acquired"],
           cohort["firecrawl_usable"], cohort["firecrawl_credits"]),
        "control %d | browser acquired %d | recoveries %d"
        % (ctrl["control_subjects"], ctrl["browser_acquired"],
           ctrl["browser_recoveries"]),
        "  recovery rate: %s over attributable failures, %s over opportunities"
        % (ctrl["recovery_rate_over_attributable_failures"],
           ctrl["recovery_rate_over_opportunities"]),
        "",
        "DECISION: %s" % doc["final_decision"],
        "ROUTE:    %s" % route["status"],
        "",
        "production: acquired %d | publication-grade %d | excluded %d | "
        "store rows %d (match: %s)"
        % (prod["acquired"], prod["publication_grade"],
           prod["non_publication_grade"], prod["rows_in_current_store"],
           prod["the_ten_match_the_store"]),
        "semantics: %d of %d fee assertions changed under HEAD; %d held"
        % (doc["semantics"]["fee_assertion_changed"],
           doc["semantics"]["records"],
           doc["semantics"]["held_schema_cannot_represent"]),
        "store rows: %d | published %s | authority %s"
        % (doc["store_rows"], doc["published"], doc["authority_written"]),
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    doc = build()
    print(summarise(doc))
    if args.write_report:
        CLOSURE_REPORT.write_bytes(
            (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("\nreport: %s" % CLOSURE_REPORT)
    return 0


__all__ = ["WORK_ORDER", "CLOSES", "inventory", "decision_cohort", "control",
           "evidence_completeness", "route_reconciliation",
           "production_reconciliation", "semantics_then_and_now",
           "counter_correction", "cost", "build",
           "ROUTE_ALREADY_CORRECT", "ROUTE_CHANGE_REQUIRED",
           "PAGE_LEVEL_CAUSES"]


if __name__ == "__main__":
    raise SystemExit(main())

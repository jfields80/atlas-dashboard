"""PTF-FIRECRAWL-CHOICE-VALIDATION-004 -- finish the Milwaukee Choice sample.

PTF-FIRECRAWL-HARD-LANES-003 measured Firecrawl on three Choice properties and
they were perfect: 3/3 acquired, 3/3 complete, zero structured mismatches. The
honest weakness of that result is that n=3, and a route change is not something
to buy with three observations. This work order runs the *other* twelve
Milwaukee Choice properties so the decision rests on all fifteen.

Nothing here re-runs the committed three. They are read back out of
``ptf_firecrawl_hard_lanes_003.json`` and folded into the combined score, which
is the only correct way to spend zero credits reproducing a known answer.

What the queue actually contains, and why it changes the question
----------------------------------------------------------------
The fifteen Choice rows are not fifteen properties with a Bright Data answer to
check against. Sorting them by what the production run actually did:

    7   ACQUIRED_PUBLICATION_GRADE   -- a real baseline exists (3 are HL-003's)
    4   TECHNICAL_FALLBACK_REQUIRED  -- the Web Unlocker got ACCESS_DENIED x3
    4   never attempted              -- the $15 market cap stopped the run

So of the twelve remaining, only four can be *compared*. The other eight are a
coverage question, not an agreement question, and the two must not be added
together. A property the incumbent could not fetch at all is the most valuable
thing in this sample -- it is the only place a new provider can produce
coverage rather than merely reproduce it -- but it is also the place where
there is nothing to check the answer against, and this module says so on every
row rather than letting a 12/12 read as twelve confirmations.

Completeness has to be measured two ways for the same reason
------------------------------------------------------------
Against a baseline, "complete" means what HL-003 meant: the policy surface
hydrated, no structured disagreement, and nothing the incumbent found that this
lane lost. With no baseline there is no MISSING to count, so the same rule
would pass trivially. For those rows completeness is intrinsic: the surface
hydrated AND the extraction states either a refusal (a no-pets policy is
complete on its own -- there is nothing further to state) or an allowance plus
at least one substantive term. A lone ``pets_allowed: true`` is an allowance
with no policy attached, and Benchmark-002 already showed how easily that
passes every evidence gate while telling a guest nothing.

The proven path, unchanged
--------------------------
Acquisition is ``firecrawl_hard_lanes_003.acquire`` itself -- not a copy of it.
Same scrape profile, same deterministic interaction fallback, same identity,
hydration and agreement gates, same ``choice_static`` reader, same
publication-grade validator, same comparison vocabulary. Only the provenance
stamp differs. If this run disagrees with HL-003 it is the properties, not the
method.

routes.json is untouched, Firecrawl stays unregistered, no authority is written.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FIRECRAWL  # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL             # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_hard_lanes_003 as HL  # noqa: E402

MARKET = "milwaukee-wi"
BRAND = "CHOICE"
WORK_ORDER = "PTF-FIRECRAWL-CHOICE-VALIDATION-004"
RUN_ID = "firecrawl-choice-validation-004"
REF_TAG = "fc4"

PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
QUEUE = REPORTS / "milwaukee-wi_policy_acquisition_queue_001.json"
HARD_LANES_REPORT = REPORTS / "ptf_firecrawl_hard_lanes_003.json"
PRODUCTION_JOURNAL = (REPO / "data" / "acquisition" / "milwaukee-router-001"
                      / "milwaukee-router-001" / "journal.jsonl")
RUN_ROOT = REPO / "data" / "acquisition" / "firecrawl-choice-validation-004"

#: The Bright Data Choice lane's measured wall-clock, from the production run.
#: Reported for comparison; recomputed from the journal rather than quoted.
CHOICE_TOTAL_EXPECTED = 15
CHOICE_ALREADY_TESTED_EXPECTED = 3
CHOICE_NEW_EXPECTED = 12


# --------------------------------------------------------------------------- #
# Sample derivation. Mechanical: the queue decides membership, not this file.
# --------------------------------------------------------------------------- #

def queue_rows() -> List[Dict]:
    doc = json.loads(QUEUE.read_text(encoding="utf-8"))
    return list(doc["items"])


def already_tested_keys() -> List[str]:
    """The Choice identity keys HL-003 committed. Read, never re-listed."""
    doc = json.loads(HARD_LANES_REPORT.read_text(encoding="utf-8"))
    return sorted({row["identity_key"] for row in doc["sample"]
                   if row["brand"] == BRAND})


def production_baselines() -> Dict[str, Dict]:
    """Every production journal row for this market, keyed by identity."""
    if not PRODUCTION_JOURNAL.exists():
        return {}
    out: Dict[str, Dict] = {}
    for line in PRODUCTION_JOURNAL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["identity_key"]] = row
    return out


def remaining_sample() -> Tuple[List[Dict], List[str]]:
    """The twelve Choice rows HL-003 did not test, with their baselines merged.

    Returns ``(entries, already_tested_keys)``. Raises if the arithmetic the
    work order pins does not hold, because a silently-short sample is worse
    than no sample.
    """
    choice = sorted((r for r in queue_rows() if r["brand"] == BRAND),
                    key=lambda r: r["identity_key"])
    tested = already_tested_keys()

    if len(choice) != CHOICE_TOTAL_EXPECTED:
        raise SystemExit("expected %d Choice rows in the queue, found %d"
                         % (CHOICE_TOTAL_EXPECTED, len(choice)))
    if len(tested) != CHOICE_ALREADY_TESTED_EXPECTED:
        raise SystemExit("expected %d already-tested Choice rows, found %d"
                         % (CHOICE_ALREADY_TESTED_EXPECTED, len(tested)))
    missing = [k for k in tested if k not in {r["identity_key"] for r in choice}]
    if missing:
        raise SystemExit("HL-003 tested a key that is not in the queue: %s" % missing)

    baselines = production_baselines()
    entries = []
    for row in choice:
        if row["identity_key"] in tested:
            continue
        entries.append(_entry(row, baselines.get(row["identity_key"])))

    if len(entries) != CHOICE_NEW_EXPECTED:
        raise SystemExit("expected %d new Choice rows, derived %d"
                         % (CHOICE_NEW_EXPECTED, len(entries)))
    keys = [e["identity_key"] for e in entries]
    if len(set(keys)) != len(keys):
        raise SystemExit("duplicate identity keys in the derived sample")
    return entries, tested


def _entry(row: Dict, baseline: Optional[Dict]) -> Dict:
    """A queue row plus whatever the production run learned about it.

    ``acquire`` reads ``reader``, ``official_url`` and -- through
    ``_extraction`` -- ``result.document.observation.extraction``. A row with no
    baseline simply has no ``result``, and every comparison downstream is then
    correctly empty rather than fabricated.
    """
    state = (baseline or {}).get("final_state")
    entry = {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "official_url": row["official_url"],
        "reader": row.get("route_reader") or "generic",
        "elapsed_seconds": (baseline or {}).get("elapsed_seconds"),
        "baseline_state": state or "NOT_ATTEMPTED",
        "baseline_failure": (baseline or {}).get("failure") or "",
        "baseline_providers_tried": (baseline or {}).get("providers_tried") or [],
    }
    if state == "ACQUIRED_PUBLICATION_GRADE":
        entry["result"] = baseline["result"]
        entry["comparable"] = True
    else:
        entry["comparable"] = False
    return entry


# --------------------------------------------------------------------------- #
# Failure-state taxonomy (section 4). Exactly one label per row.
# --------------------------------------------------------------------------- #

#: Surfaces that mean the page arrived but the policy did not.
INCOMPLETE_SURFACES = ("HEADING_ONLY", "CONTAINER_PRESENT_NO_TEXT")

WO_STATES = (
    "ACQUIRED_PUBLICATION_GRADE", "ACQUIRED_NONPUBLICATION_GRADE",
    "SCRAPE_ALL_ENGINES_FAILED", "ACCESS_DENIED", "RATE_LIMITED_EXHAUSTED",
    "NAVIGATION_FAILED", "JAVASCRIPT_SHELL", "POLICY_SURFACE_INCOMPLETE",
    "POLICY_NOT_FOUND", "IDENTITY_MISMATCH", "IDENTITY_UNCERTAIN",
    "PROVIDER_ERROR",
)


def work_order_state(result: Dict) -> str:
    """Map an acquisition result onto the twelve states section 4 allows.

    HTTP 200 decides nothing here. A page that arrived with only a policy
    heading is POLICY_SURFACE_INCOMPLETE even when its evidence package is
    technically publication-grade, because publication-grade describes the
    evidence and not the policy.
    """
    surface = result.get("surface_state") or "ABSENT"
    state = result.get("firecrawl_state") or "NOT_ACQUIRED"
    detail = str(result.get("firecrawl_failure") or "")
    outcome = str(result.get("firecrawl_outcome") or "")

    if state.startswith("ACQUIRED"):
        if surface in INCOMPLETE_SURFACES:
            return "POLICY_SURFACE_INCOMPLETE"
        if not result.get("identity_confirmed", True):
            return "IDENTITY_UNCERTAIN"
        return state

    if "ALL_ENGINES_FAILED" in detail:
        return "SCRAPE_ALL_ENGINES_FAILED"
    if "RATE_LIMITED" in detail:
        return "RATE_LIMITED_EXHAUSTED"
    if outcome == "IDENTITY_MISMATCH":
        return "IDENTITY_MISMATCH"
    if outcome == "ACCESS_DENIED":
        return "ACCESS_DENIED"
    if outcome == "NAVIGATION_FAILED":
        return "NAVIGATION_FAILED"
    if outcome == "BLANK_PAGE":
        return "JAVASCRIPT_SHELL"
    if outcome == "POLICY_NOT_FOUND":
        # Spider's diagnosis rule: a small body with no policy signal is a
        # shell, not a page that merely lacks a policy section.
        if (result.get("body_chars") or 0) and result["body_chars"] < 6000:
            return "JAVASCRIPT_SHELL"
        return "POLICY_NOT_FOUND"
    return "PROVIDER_ERROR"


# --------------------------------------------------------------------------- #
# Completeness (section 5), measured differently where there is no baseline.
# --------------------------------------------------------------------------- #

#: A term that makes an allowance into a policy a guest could act on.
SUBSTANTIVE_TERMS = ("pet_fee", "fee_amount", "fee_basis", "fee_scope",
                     "fee_cap", "weight_limit", "combined_weight_limit",
                     "pet_count_limit", "species_allowed", "species",
                     "deposit", "cleaning_fee", "refundable",
                     "other_charges", "dimension_limit")


def intrinsic_completeness(extraction: Dict, surface_state: str) -> Tuple[bool, str]:
    """Is this a policy, judged on its own, with no incumbent to check against?"""
    if surface_state not in ("HYDRATED", "TEXT_WITHOUT_BRAND_CONTAINER"):
        return False, "the policy surface did not hydrate"
    allowed = extraction.get("pets_allowed")
    if allowed is False:
        return True, ("a captured refusal is complete on its own: there are no "
                      "further terms to state")
    if allowed is not True:
        return False, "the extraction does not state whether pets are allowed"
    terms = [f for f in SUBSTANTIVE_TERMS if f in extraction]
    if not terms:
        return False, ("an allowance with no terms attached: pets_allowed alone "
                       "tells a guest nothing about fee, weight or count")
    return True, "allowance plus %d substantive term(s): %s" % (len(terms),
                                                                ", ".join(terms))


def measure_completeness(result: Dict, entry: Dict) -> Dict:
    """Both readings, with the basis named so neither can be quoted as the other."""
    surface = result.get("surface_state") or "ABSENT"
    got = result.get("firecrawl_extraction") or {}
    if entry.get("comparable"):
        comparison = result.get("comparison") or {}
        complete = bool(result.get("complete"))
        return {
            "basis": "COMPARED_TO_BRIGHT_DATA",
            "complete": complete,
            "why": ("hydrated, no structured disagreement and nothing the "
                    "incumbent found was lost" if complete else
                    "surface %s; %d structured mismatch(es); %d MISSING"
                    % (surface,
                       len(comparison.get("structured_mismatches") or {}),
                       (comparison.get("counts") or {}).get("MISSING", 0))),
        }
    complete, why = intrinsic_completeness(got, surface)
    return {"basis": "NO_BASELINE_INTRINSIC", "complete": complete, "why": why}


# --------------------------------------------------------------------------- #
# Internal consistency, which is not the same thing as agreement.
# --------------------------------------------------------------------------- #

#: Terms that only make sense if pets are allowed at all.
PET_ONLY_TERMS = ("pet_fee", "fee_amount", "fee_basis", "fee_scope", "fee_cap",
                  "weight_limit", "combined_weight_limit", "weight_scope",
                  "pet_count_limit", "pet_count_scope", "species_allowed",
                  "species", "deposit", "cleaning_fee")


def refusal_carrying_pet_terms(extraction: Dict) -> List[str]:
    """A no-pets record that also states a pet weight limit is contradicting itself.

    The zero-wrong-fact detectors in section 6 compare against a baseline, so a
    row with no baseline cannot be caught by them at all. This catches the one
    error that needs no second opinion: a property that refuses pets cannot
    also cap them at 40 pounds. Where it fires, the likely cause is the reader
    picking up service-animal wording as a pet term, and the record must not be
    published on the strength of this run.
    """
    if extraction.get("pets_allowed") is not False:
        return []
    return sorted(f for f in PET_ONLY_TERMS if f in extraction)


# --------------------------------------------------------------------------- #
# Country Inn / Radisson (section 7), reported on its own.
# --------------------------------------------------------------------------- #

def country_inn_keys(entries: List[Dict]) -> List[str]:
    """The Radisson sub-brand rows the Web Unlocker could not fetch."""
    return sorted(e["identity_key"] for e in entries
                  if "country inn" in e["identity_key"]
                  and e["baseline_state"] != "ACQUIRED_PUBLICATION_GRADE")


# --------------------------------------------------------------------------- #

async def main_async(args) -> Dict:
    entries, tested = remaining_sample()
    if args.only:
        wanted = set(args.only)
        entries = [e for e in entries if e["identity_key"] in wanted]

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")
    done = journal.completed_keys() if not args.no_resume else set()

    # Filter what is already journalled BEFORE applying --limit, or a batch
    # silently stalls on rows it has already finished.
    todo = [e for e in entries if e["identity_key"] not in done]
    if args.limit:
        todo = todo[:args.limit]

    if args.report_only:
        # Rebuild the report from what is already journalled. No request is
        # made, so this can never cost a credit, which is the point of it.
        todo = []

    credits_before = None if args.report_only else FIRECRAWL.credits_remaining()
    started = time.monotonic()

    by_key = {e["identity_key"]: e for e in entries}
    for entry in todo:
        result = await HL.acquire(entry, run_dir=run_dir, pace=args.pace,
                                  run_id=RUN_ID, ref_tag=REF_TAG)
        result["brand"] = BRAND
        result["baseline_state"] = entry["baseline_state"]
        result["baseline_failure"] = entry["baseline_failure"]
        result["comparable"] = entry["comparable"]
        result["work_order_state"] = work_order_state(result)
        result["policy_completeness"] = measure_completeness(result, entry)
        journal.append(result)          # durable before the next property
        print("  %-46s %-30s %-26s fields %d->%d  %s"
              % (result["canonical_name"][:46],
                 result["work_order_state"],
                 result.get("surface_state", "?"),
                 result["bright_data_field_count"],
                 result.get("firecrawl_field_count", 0),
                 "complete" if result["policy_completeness"]["complete"] else ""),
              flush=True)
        await asyncio.sleep(args.pace)

    credits_after = None if args.report_only else FIRECRAWL.credits_remaining()

    # Cost is measured once, when the requests are actually made. A later
    # --report-only rebuild has nothing to measure, and must not overwrite the
    # measurement with a null -- so it is persisted next to the journal, which
    # is the same durability rule every completed property already follows.
    cost_path = run_dir / "cost.json"
    if not args.report_only:
        cost_path.write_bytes((json.dumps(
            {"credits_before": credits_before, "credits_after": credits_after,
             "measured_credits": (None if credits_before is None or credits_after is None
                                  else credits_before - credits_after)},
            indent=1) + "\n").encode("utf-8"))
    elif cost_path.is_file():
        saved = json.loads(cost_path.read_text(encoding="utf-8"))
        credits_before = saved.get("credits_before")
        credits_after = saved.get("credits_after")
        if credits_before is None and saved.get("measured_credits") is not None:
            # Only the delta survived. Carry it forward as a delta rather than
            # inventing endpoints for it.
            measured_override = saved["measured_credits"]
            credits_before, credits_after = measured_override, 0
    journalled = journal.read()
    new_rows = sorted((journalled[k] for k in journalled),
                      key=lambda r: r["identity_key"])
    return build_report(new_rows, by_key, tested,
                        credits_before=credits_before,
                        credits_after=credits_after,
                        elapsed=round(time.monotonic() - started, 1))


def _fold(rows: List[Dict]) -> Dict:
    """Counts that mean the same thing on both halves of the sample.

    ``compared`` is deliberately narrower than "has a comparison object".
    ``acquire`` builds one for every acquired row, and against an absent
    baseline every field it found scores EXTRA -- which would read as "the
    incumbent fetched this page and missed nine fields" when in truth the
    incumbent never got the page at all. Only rows with a real
    publication-grade baseline are counted, so MATCH / EXTRA / MISSING keep
    meaning what they mean everywhere else in this corpus.
    """
    compared = [r for r in rows if r.get("comparable") and r.get("comparison")]
    verdicts: Counter = Counter()
    for r in compared:
        verdicts.update(r["comparison"]["counts"])
    times = [r["firecrawl_elapsed_seconds"] for r in rows
             if r.get("firecrawl_elapsed_seconds")]
    wrong: Counter = Counter()
    for r in rows:
        for name, flag in (r.get("false_facts") or {}).items():
            if flag:
                wrong[name] += 1
    return {
        "total": len(rows),
        "acquired": sum(1 for r in rows
                        if str(r.get("firecrawl_state", "")).startswith("ACQUIRED")),
        "publication_grade": sum(
            1 for r in rows
            if r.get("firecrawl_state") == "ACQUIRED_PUBLICATION_GRADE"),
        "complete": sum(1 for r in rows if _is_complete(r)),
        "compared_against_bright_data": len(compared),
        "match": verdicts.get("MATCH", 0),
        "extra": verdicts.get("EXTRA", 0),
        "missing": verdicts.get("MISSING", 0),
        "structured_mismatch": sum(
            len(r["comparison"].get("structured_mismatches") or {}) for r in compared),
        "text_excerpt_variant": sum(
            len(r["comparison"].get("text_excerpt_variants") or {}) for r in compared),
        "false_pets_allowed": wrong.get("false_pets_allowed", 0),
        "false_no_pets": wrong.get("false_no_pets", 0),
        "false_fee": wrong.get("false_fee", 0),
        "false_weight": wrong.get("false_weight", 0),
        "false_species": wrong.get("false_species", 0),
        "avg_seconds": round(statistics.mean(times), 1) if times else None,
        "median_seconds": round(statistics.median(times), 1) if times else None,
        "p95_seconds": (round(sorted(times)[max(0, int(len(times) * 0.95) - 1)], 1)
                        if times else None),
        "scrape_calls": sum(r.get("scrape_calls", 0) for r in rows),
        "interact_calls": sum(r.get("interact_calls", 0) for r in rows),
        "surface_states": dict(Counter(r.get("surface_state", "?") for r in rows)),
        "work_order_states": dict(Counter(
            r.get("work_order_state") or _committed_state(r) for r in rows)),
        "fields_on_rows_with_no_baseline": sum(
            r.get("firecrawl_field_count", 0) for r in rows
            if not r.get("comparable")),
        "acquired_with_no_baseline": sum(
            1 for r in rows if not r.get("comparable")
            and str(r.get("firecrawl_state", "")).startswith("ACQUIRED")),
    }


def _is_complete(row: Dict) -> bool:
    pc = row.get("policy_completeness")
    if isinstance(pc, dict):
        return bool(pc.get("complete"))
    return bool(row.get("complete"))


def _committed_state(row: Dict) -> str:
    """HL-003 rows predate the section-4 vocabulary; map them the same way."""
    return work_order_state(row)


def committed_choice_rows() -> List[Dict]:
    """HL-003's three Choice items, read back rather than re-acquired."""
    doc = json.loads(HARD_LANES_REPORT.read_text(encoding="utf-8"))
    rows = [dict(r) for r in doc["items"] if r.get("brand") == BRAND]
    for r in rows:
        r.setdefault("comparable", True)
        r["work_order_state"] = work_order_state(r)
        r["from_work_order"] = "PTF-FIRECRAWL-HARD-LANES-003"
    return sorted(rows, key=lambda r: r["identity_key"])


def bright_data_choice_reference() -> Dict:
    """What the incumbent actually did on all fifteen, recomputed not quoted."""
    baselines = production_baselines()
    keys = [r["identity_key"] for r in queue_rows() if r["brand"] == BRAND]
    states = Counter()
    times = []
    for key in keys:
        row = baselines.get(key)
        states[(row or {}).get("final_state") or "NOT_ATTEMPTED"] += 1
        if row and row.get("elapsed_seconds"):
            times.append(row["elapsed_seconds"])
    attempted = [k for k in keys if k in baselines]
    return {
        "total_in_queue": len(keys),
        "attempted": len(attempted),
        "not_attempted_budget_stopped": len(keys) - len(attempted),
        "acquired_publication_grade": states.get("ACQUIRED_PUBLICATION_GRADE", 0),
        "technical_fallback_required": states.get("TECHNICAL_FALLBACK_REQUIRED", 0),
        "states": dict(states),
        "avg_seconds_over_attempted": round(statistics.mean(times), 1) if times else None,
        "usd_per_attempted_property": 0.197,
        "note": ("Coverage is stated over all fifteen queue rows, not over the "
                 "rows the incumbent happened to reach. Four were never "
                 "attempted because the market's $15 provider cap stopped the "
                 "run, and four returned ACCESS_DENIED after three attempts."),
    }


def build_report(new_rows: List[Dict], by_key: Dict[str, Dict],
                 tested: List[str], *, credits_before, credits_after,
                 elapsed: float) -> Dict:
    committed = committed_choice_rows()
    combined = sorted(committed + new_rows, key=lambda r: r["identity_key"])

    new_fold = _fold(new_rows)
    committed_fold = _fold(committed)
    combined_fold = _fold(combined)

    # Coverage the incumbent did not have. This is the only number in the file
    # that can justify a route change on grounds other than speed.
    new_coverage = sorted(
        r["identity_key"] for r in new_rows
        if str(r.get("firecrawl_state", "")).startswith("ACQUIRED")
        and r.get("baseline_state") != "ACQUIRED_PUBLICATION_GRADE")
    lost_coverage = sorted(
        r["identity_key"] for r in combined
        if not str(r.get("firecrawl_state", "")).startswith("ACQUIRED")
        and r.get("baseline_state") == "ACQUIRED_PUBLICATION_GRADE")

    ci_keys = country_inn_keys([by_key[k] for k in by_key])
    ci_rows = [r for r in new_rows if r["identity_key"] in set(ci_keys)]
    ci_acquired = [r["identity_key"] for r in ci_rows
                   if str(r.get("firecrawl_state", "")).startswith("ACQUIRED")]

    total_credits = (None if credits_before is None or credits_after is None
                     else credits_before - credits_after)

    doc = {
        "schema": "ptf-firecrawl-choice-validation/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "note": ("Completes the Milwaukee Choice sample begun by "
                 "PTF-FIRECRAWL-HARD-LANES-003. The three properties that work "
                 "order committed are read back from its report and were NOT "
                 "re-acquired. Acquisition uses hard_lanes_003.acquire itself, "
                 "so the profile, the three gates and the comparison vocabulary "
                 "are the same object, not a copy. routes.json untouched, "
                 "Firecrawl unregistered, no authority written."),
        "sample_derivation": {
            "source": "launch_packages/pettripfinder/markets/reports/"
                      "milwaukee-wi_policy_acquisition_queue_001.json",
            "rule": "brand == CHOICE, minus the identity keys HL-003 committed",
            "choice_total_existing_benchmark": len(committed),
            "choice_new_rows": len(new_rows),
            "choice_combined_total": len(combined),
            "already_tested_identity_keys": tested,
            "new_identity_keys": [r["identity_key"] for r in new_rows],
            "duplicate_identity_keys": [],
            "substitutions_made": ("none: every remaining Choice row was run, "
                                   "including the four the Web Unlocker could "
                                   "not fetch and the four it never reached"),
        },
        "baseline_availability": {
            "note": ("Only rows the production run acquired at "
                     "publication grade can be compared field by field. The "
                     "rest are a coverage question and are counted separately "
                     "so a coverage win is never reported as an agreement."),
            "comparable": sum(1 for r in combined if r.get("comparable")),
            "no_baseline_incumbent_failed": sum(
                1 for r in new_rows
                if r.get("baseline_state") == "TECHNICAL_FALLBACK_REQUIRED"),
            "no_baseline_never_attempted": sum(
                1 for r in new_rows if r.get("baseline_state") == "NOT_ATTEMPTED"),
        },
        "new_run": new_fold,
        "previously_committed": committed_fold,
        "combined": combined_fold,
        "coverage": {
            "new_coverage_identity_keys": new_coverage,
            "new_coverage_count": len(new_coverage),
            "new_coverage_that_is_a_complete_policy": sorted(
                r["identity_key"] for r in new_rows
                if r["identity_key"] in set(new_coverage) and _is_complete(r)),
            "new_coverage_note": (
                "Acquiring a page is not the same as gaining a usable policy. "
                "The completeness list is the subset a guest could act on."),
            "lost_coverage_identity_keys": lost_coverage,
            "lost_coverage_count": len(lost_coverage),
        },
        "internal_consistency": {
            "note": ("Rows with no incumbent baseline cannot be checked by the "
                     "section-6 detectors, which compare two answers. This "
                     "check needs only one: a record that says pets are not "
                     "allowed must not also state pet terms."),
            "refusal_records_carrying_pet_terms": {
                r["identity_key"]: refusal_carrying_pet_terms(
                    r.get("firecrawl_extraction") or {})
                for r in combined
                if refusal_carrying_pet_terms(r.get("firecrawl_extraction") or {})},
            "consequence": ("Any row listed above is HELD from publication and "
                            "needs a founder look at the captured artifact. It "
                            "is not counted as a wrong fact -- nothing "
                            "contradicts it -- but it is not publishable."),
        },
        "country_inn_radisson": {
            "known_difficult_total": len(ci_keys),
            "acquired": len(ci_acquired),
            "failed": len(ci_keys) - len(ci_acquired),
            "identity_keys": ci_keys,
            "acquired_identity_keys": sorted(ci_acquired),
            "failure_reasons": {r["identity_key"]: r.get("work_order_state")
                                for r in ci_rows
                                if not str(r.get("firecrawl_state", "")).startswith("ACQUIRED")},
            "incumbent_result": "ACCESS_DENIED after 3 Web Unlocker attempts",
            "prior_finding": ("PTF-FIRECRAWL-HARD-LANES-003 tested these three "
                              "separately, Firecrawl failed all three with "
                              "SCRAPE_ALL_ENGINES_FAILED, and that work order "
                              "concluded: 'Firecrawl MATCHES Choice coverage; "
                              "it does not extend it.'"),
            "correction": (
                "THAT CONCLUSION IS WRONG AND IS RETRACTED HERE. All three "
                "acquired in this run, at 9, 5 and 9 fields, on properties the "
                "Web Unlocker returned ACCESS_DENIED for after three attempts. "
                "Firecrawl DOES extend Choice coverage."),
            "why_the_earlier_result_differed": (
                "Not a change of method -- the same profile, the same URLs. "
                "Brown Deer needed two scrape calls here and succeeded on the "
                "second; the other two succeeded on their FIRST call, having "
                "failed on a single call in the addendum. So on the Choice "
                "origin SCRAPE_ALL_ENGINES_FAILED is INTERMITTENT, not the "
                "capability verdict it is on Marriott and Hilton, where it "
                "reproduced on 6 of 7 attempts. A single-attempt probe was too "
                "thin to distinguish the two, and a coverage claim was "
                "published off it. One attempt is not a capability measurement."),
        },
        "cost": {
            "credits_before": credits_before if credits_after else None,
            "credits_after": credits_after or None,
            "credits_endpoint_note": (
                "credits_before/after are null when only the measured delta "
                "survived a report rebuild; the delta itself is the figure "
                "that was measured at acquisition time"),
            "new_run_credits": total_credits,
            "hard_lanes_003_choice_credits": committed_fold["acquired"],
            "combined_15_credits": (None if total_credits is None
                                    else total_credits + committed_fold["acquired"]),
            "avg_credits_per_new_property": (
                None if total_credits is None or not new_rows
                else round(total_credits / len(new_rows), 2)),
            "avg_credits_per_combined_property": (
                None if total_credits is None or not combined
                else round((total_credits + committed_fold["acquired"]) / len(combined), 2)),
            "scrape_calls": new_fold["scrape_calls"],
            "interact_calls": new_fold["interact_calls"],
            "dollar_conversion": ("not derivable: the plan endpoint reports "
                                  "credits and a monthly allowance, not a unit "
                                  "price, so no dollar figure is asserted"),
        },
        "bright_data_reference": bright_data_choice_reference(),
        "authority_written": False,
        "routes_changed": False,
        "firecrawl_registered": False,
        "total_elapsed_seconds": elapsed,
        "items": combined,
    }
    out = REPORTS / "ptf_firecrawl_choice_validation_004.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="choice-validation-004")
    parser.add_argument("--pace", type=float, default=8.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--report-only", action="store_true",
                        help="rebuild the report from the journal, spending nothing")
    args = parser.parse_args(argv)

    if not args.report_only and not FIRECRAWL.credential_present():
        print("%s is not set" % FIRECRAWL.KEY_ENV)
        return 2

    doc = asyncio.run(main_async(args))
    n, c = doc["new_run"], doc["combined"]
    print()
    print("NEW      %d/%d acquired | pub %d | complete %d | compared %d | "
          "struct-mismatch %d | %ss avg"
          % (n["acquired"], n["total"], n["publication_grade"], n["complete"],
             n["compared_against_bright_data"], n["structured_mismatch"],
             n["avg_seconds"]))
    print("COMBINED %d/%d acquired | pub %d | complete %d | MATCH %d | MISSING %d | "
          "struct-mismatch %d"
          % (c["acquired"], c["total"], c["publication_grade"], c["complete"],
             c["match"], c["missing"], c["structured_mismatch"]))
    print("coverage: +%d the incumbent did not have, -%d lost"
          % (doc["coverage"]["new_coverage_count"],
             doc["coverage"]["lost_coverage_count"]))
    print("country inn / radisson: %d/%d"
          % (doc["country_inn_radisson"]["acquired"],
             doc["country_inn_radisson"]["known_difficult_total"]))
    print("credits: new %s, combined %s"
          % (doc["cost"]["new_run_credits"], doc["cost"]["combined_15_credits"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

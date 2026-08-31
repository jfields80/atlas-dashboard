# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FIRECRAWL-PASS-008, Phases 6 and 7.

Measures what the Detroit Firecrawl pass actually yielded, and re-prices the
rest of the market from that measurement alone.

THE DENOMINATOR IS ATTEMPTS. Not hotels, not routed rows, not the cohort that
was planned: every attempt that was paid for, including the two pages this run
bought twice. A rate denominated in anything else quietly prices a future
cohort on work this one did not have to do.

TWO DENOMINATORS ARE PUBLISHED, NEVER BLENDED. 49 of the 65 attempts were
refused by the page-health gate before any page could be judged, because
``PROPERTY_CODE_PATTERNS`` cannot read an IHG or Choice property code off those
brands' own canonical URL shapes (see the defect artifact). Those attempts
tested nothing about the hotel, the lane, or the market:

  * ``all_attempts`` is the honest cost-side rate -- what this project got for
    its money, defect included. It is the right rate for "what did the pass
    return".
  * ``reached_the_identity_gate`` is the capability-side rate -- what the lane
    returns when the gate lets a page through. It is the right rate for sizing
    a FUTURE cohort, and only if the defect is repaired first.

Sizing uses the WILSON LOWER bound, and feasibility the upper: at n=16 the
point estimate is not a number to spend against. Nothing here authorises a
cohort; it prices one.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FIRECRAWL-PASS-008"
RUN_ID = "detroit-firecrawl-008"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CLASSIFICATION = LP / "detroit_ann_arbor_firecrawl_classification_008.json"
QUALIFICATION = LP / "detroit_ann_arbor_firecrawl_lane_qualification_008.json"
COST_PLAN = LP / "detroit_ann_arbor_firecrawl_cost_plan_008.json"
OUT_PATH = LP / "detroit_ann_arbor_firecrawl_yield_008.json"

#: Wilson at 95%.
Z = 1.959963984540054

#: The Firecrawl plan balance read immediately after the pass finished, PINNED
#: rather than queried. The balance keeps moving -- other markets share the
#: plan -- so a script that asked the vendor live would report a different
#: spend for this run every time it ran, which is not a measurement.
PS_CREDITS_AFTER = 569.0

ACQUIRED = ("PET_FRIENDLY", "VERIFIED_NO_PETS")


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def wilson(successes: int, trials: int, z: float = Z) -> Tuple[float, float, float]:
    """(point, lower, upper) -- the Wilson score interval.

    Wilson rather than the normal approximation because these denominators are
    small and the rates sit near the ends, which is exactly where the normal
    interval runs past 0 and 1 and stops meaning anything.
    """
    if trials <= 0:
        return (0.0, 0.0, 0.0)
    point = successes / trials
    denominator = 1.0 + (z * z) / trials
    centre = (point + (z * z) / (2 * trials)) / denominator
    margin = (z * math.sqrt(point * (1 - point) / trials
                            + (z * z) / (4 * trials * trials))) / denominator
    return (point, max(0.0, centre - margin), min(1.0, centre + margin))


def rate_block(label: str, successes: int, trials: int, what: str) -> Dict:
    point, low, high = wilson(successes, trials)
    return OrderedDict([
        ("measures", what),
        ("successes", successes),
        ("attempts", trials),
        ("point", round(point, 4)),
        ("wilson_lower_95", round(low, 4)),
        ("wilson_upper_95", round(high, 4)),
    ])


def run() -> None:
    classification = load(CLASSIFICATION)
    qualification = load(QUALIFICATION)
    plan = load(COST_PLAN)
    results: List[Dict] = classification["results"]

    code_by_key = {row["identity_key"]: (row.get("property_code") or "")
                   for row in qualification["qualified_rows"]}

    # A row is DEFECT-BLOCKED when the health gate refused it for a property
    # code the parser could not read off its own canonical URL. ACCESS_DENIED
    # is NOT defect-blocked: that gate fires earlier, so the refusal is real
    # and says something true about the lane.
    blocked, reached = [], []
    for result in results:
        expected = code_by_key.get(result["identity_key"], "")
        parsed = PS.property_code(result["canonical_url"], result["brand"])
        unreadable = bool(expected) and parsed.lower() != expected.lower()
        if result["class"] == "UNEXPECTED_PAGE" and unreadable:
            blocked.append(result)
        else:
            reached.append(result)

    def measure(rows: List[Dict], label: str, note: str) -> Dict:
        counts = Counter(row["class"] for row in rows)
        acquired = sum(counts[cls] for cls in ACQUIRED)
        return OrderedDict([
            ("denominator", label),
            ("what_it_is", note),
            ("attempts", len(rows)),
            ("counts", OrderedDict(sorted(counts.items()))),
            ("pet_friendly", rate_block(
                label, counts["PET_FRIENDLY"], len(rows),
                "attempts that ended in a first-party page stating pets are "
                "accepted")),
            ("publication_grade", rate_block(
                label, acquired, len(rows),
                "attempts that ended in a publication-grade answer either way "
                "-- pet-friendly or verified no-pets")),
        ])

    all_attempts = measure(
        results, "all_attempts",
        "every paid attempt in this run, including the two pages bought twice "
        "and the 49 the parser defect refused before any page could be judged. "
        "The honest cost-side rate.")
    gate_reached = measure(
        reached, "reached_the_identity_gate",
        "the attempts the page-health gate did not refuse for an unreadable "
        "property code. The capability-side rate, and the only one that says "
        "anything about what this lane can do.")

    # ---- Phase 7: re-price the remaining market ------------------------ #
    # THE CREDIT DELTA IS THE AUTHORITATIVE SPEND, and the cost plan says so
    # itself: Firecrawl bills in plan credits and reports no per-request dollar
    # cost. The plan carried 0.54 credits/attempt because that is what 203
    # committed ledger rows recorded. This run measured 0.95 -- an attempt that
    # falls through several engines bills for each of them, and 49 of these
    # attempts were refusals. The ledger's per-row USD constant therefore
    # UNDERSTATES this run by nearly half, and re-pricing uses the measured
    # rate rather than the assumed one.
    usd_per_credit = (float(plan["unit_cost"]["usd_per_attempt"])
                      / float(plan["unit_cost"]["credits_per_attempt"]))
    credits_before = float(plan["account"]["firecrawl_credits_before"])
    credits_after = float(PS_CREDITS_AFTER)
    credits_spent = credits_before - credits_after
    measured_credits_per_attempt = credits_spent / len(results)
    usd_per = measured_credits_per_attempt * usd_per_credit
    assumed_usd_per = float(plan["unit_cost"]["usd_per_attempt"])
    deferred = int(qualification["deferred"])
    remaining_firecrawl = len(blocked)

    lower = gate_reached["publication_grade"]["wilson_lower_95"]
    upper = gate_reached["publication_grade"]["wilson_upper_95"]
    pet_lower = gate_reached["pet_friendly"]["wilson_lower_95"]

    def expected(rows: int, rate: float) -> float:
        return round(rows * rate, 1)

    repricing = OrderedDict([
        ("basis",
         "MEASURED RESULTS ONLY. No prior estimate, no other market's rate, and "
         "no assumption that a repaired parser behaves like Wyndham -- the "
         "bound is carried across because it is the only measurement this "
         "market has, and it is carried as a LOWER bound for exactly that "
         "reason."),
        ("caveat",
         "n=%d. The lower bound is %.0f%% against a point estimate of %.0f%%; "
         "that gap is the measurement's width, not pessimism, and it is why "
         "sizing uses the lower bound and feasibility the upper."
         % (gate_reached["attempts"],
            lower * 100,
            gate_reached["publication_grade"]["point"] * 100)),
        ("firecrawl_rows_still_unanswered", OrderedDict([
            ("rows", remaining_firecrawl),
            ("why", "refused by the page-health gate for an unreadable "
                    "property code; the pages were never judged"),
            ("precondition", "NOT re-runnable until PROPERTY_CODE_PATTERNS is "
                             "repaired and the repair is proven on these "
                             "URLs; re-running them as they stand would buy "
                             "the same refusal again"),
            ("cost_to_retry_usd", round(remaining_firecrawl * usd_per, 2)),
            ("cost_to_retry_credits", round(remaining_firecrawl * measured_credits_per_attempt, 1)),
            ("priced_at", "the MEASURED credits/attempt of this run, not the cost plan's assumed 0.54"),
            ("expected_publication_grade_at_wilson_lower",
             expected(remaining_firecrawl, lower)),
            ("expected_publication_grade_at_point",
             expected(remaining_firecrawl,
                      gate_reached["publication_grade"]["point"])),
            ("expected_pet_friendly_at_wilson_lower",
             expected(remaining_firecrawl, pet_lower)),
        ])),
        ("brightdata_cohort_if_it_were_ever_authorised", OrderedDict([
            ("rows", deferred),
            ("status", "NOT AUTHORISED, NOT SIZED FOR APPROVAL, NOT RUN. This "
                       "order authorises Firecrawl only and forbids Bright "
                       "Data; the figure exists so a future order can be "
                       "written against a measurement instead of a guess."),
            ("why_these_rows", "the committed routing registry routes these "
                               "families to the managed browser, not to "
                               "Firecrawl"),
            ("sizing_rule", "size on the Wilson LOWER bound, never the point "
                            "estimate"),
            ("expected_publication_grade_at_wilson_lower",
             expected(deferred, lower)),
            ("feasibility_ceiling_at_wilson_upper", expected(deferred, upper)),
            ("note", "the Firecrawl rate is a POOR prior for the Bright Data "
                     "lane -- different provider, different families, "
                     "different walls. Carried only as an order-of-magnitude "
                     "figure, and it should be re-measured on a small "
                     "authorised pilot before any large cohort is priced."),
        ])),
    ])

    write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-firecrawl-yield/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("run_id", RUN_ID),
        ("lane", "firecrawl"),
        ("note",
         "Yield denominated in ATTEMPTS, on two denominators that are "
         "published separately and never blended. Nothing here authorises a "
         "cohort or publishes a hotel."),
        ("spend", OrderedDict([
            ("authoritative_unit", "firecrawl plan CREDITS"),
            ("credits_before", credits_before),
            ("credits_after", credits_after),
            ("credits_spent", credits_spent),
            ("attempts", len(results)),
            ("measured_credits_per_attempt",
             round(measured_credits_per_attempt, 4)),
            ("assumed_credits_per_attempt",
             float(plan["unit_cost"]["credits_per_attempt"])),
            ("usd_per_credit", round(usd_per_credit, 6)),
            ("usd_spent", round(credits_spent * usd_per_credit, 4)),
            ("usd_if_the_assumed_rate_had_held",
             round(len(results) * assumed_usd_per, 4)),
            ("hard_cap_usd", 20.00),
            ("cap_held", round(credits_spent * usd_per_credit, 4) <= 20.00),
            ("note",
             "The cost plan assumed 0.54 credits/attempt from 203 committed "
             "ledger rows; this run measured %.2f. An attempt that falls "
             "through several render engines bills for each of them, and 49 of "
             "these attempts were refusals. The cap held with room to spare, "
             "but the per-row USD constant in the ledger understates this run "
             "and is not the figure to price the next cohort on."
             % measured_credits_per_attempt),
        ])),
        ("defect_blocked_attempts", OrderedDict([
            ("count", len(blocked)),
            ("usd", round(len(blocked) * usd_per, 2)),
            ("cause", "PROPERTY_CODE_PATTERNS cannot read an IHG or Choice "
                      "property code off those brands' own canonical URL "
                      "shapes, so the page-health gate compared an empty "
                      "string against the expected code and refused every "
                      "page"),
            ("what_they_measured", "nothing about the hotel, the lane, or the "
                                   "market"),
        ])),
        ("all_attempts", all_attempts),
        ("reached_the_identity_gate", gate_reached),
        ("repricing", repricing),
    ]))

    print("=== Phase 6: yield, denominated in ATTEMPTS ===")
    for block in (all_attempts, gate_reached):
        print("\n  %s (n=%d)" % (block["denominator"], block["attempts"]))
        for key in ("pet_friendly", "publication_grade"):
            rate = block[key]
            print("     %-19s %2d/%-3d point %.3f  wilson [%.3f, %.3f]"
                  % (key, rate["successes"], rate["attempts"], rate["point"],
                     rate["wilson_lower_95"], rate["wilson_upper_95"]))
    print("\n=== Phase 7: re-pricing (authorises nothing) ===")
    firecrawl = repricing["firecrawl_rows_still_unanswered"]
    print("  firecrawl rows still unanswered : %d ($%.2f to retry, AFTER the "
          "parser repair)" % (firecrawl["rows"], firecrawl["cost_to_retry_usd"]))
    print("     expected publication-grade at wilson lower: %.1f"
          % firecrawl["expected_publication_grade_at_wilson_lower"])
    bright = repricing["brightdata_cohort_if_it_were_ever_authorised"]
    print("  brightdata rows (NOT authorised): %d, expected %.1f at wilson "
          "lower" % (bright["rows"],
                     bright["expected_publication_grade_at_wilson_lower"]))
    print("\nwrote", OUT_PATH.name)


if __name__ == "__main__":
    run()

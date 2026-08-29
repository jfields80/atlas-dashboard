# -*- coding: utf-8 -*-
"""PTF-...-PARSER-REPAIR-AND-RETRY-009, Phases 7 and 8.

The true Firecrawl yield across Pass 008 and this retry, and what Detroit still
needs.

TWO NUMBERS, AND THE COST OF THE BROKEN PARSER IS NOT ERASED FROM EITHER
DENOMINATOR IT BELONGS IN:

  * RAW PAID ATTEMPT YIELD counts every attempt both passes spent -- 65 + 49 --
    including the 49 the defect wasted and the two pages Pass 008 bought twice.
    This is what Detroit's Firecrawl evidence actually cost.
  * POST-PARSER-CORRECTED CAPABILITY counts UNIQUE PROPERTIES that reached the
    corrected identity gate. A property is counted once no matter how many
    times it was fetched, because the question it answers is "what does this
    lane return when it works", and a page bought twice is one property, not
    two.

A quota refusal is in neither capability numerator nor its denominator. 29
retry rows hit this plan's own request limit and never reached a property; they
billed nothing, and counting them as lane failures would slander the lane with
my own rate limiting. They ARE counted in raw paid attempts, because an attempt
was made -- at zero cost, which the artifact states rather than hides.
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

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-PROPERTY-CODE-PARSER-REPAIR-AND-RETRY-009"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
C008 = LP / "detroit_ann_arbor_firecrawl_classification_008.json"
C009 = LP / "detroit_ann_arbor_retry_classification_009.json"
Y008 = LP / "detroit_ann_arbor_firecrawl_yield_008.json"
QUAL = LP / "detroit_ann_arbor_firecrawl_lane_qualification_008.json"
OUT_PATH = LP / "detroit_ann_arbor_true_firecrawl_yield_009.json"

Z = 1.959963984540054
USD_PER_CREDIT = 0.0721333333333333 / 0.54

#: Credit deltas measured at each pass, the authoritative unit.
CREDITS_008 = 62.0
CREDITS_009 = 20.0

ACQUIRED = ("PET_FRIENDLY", "VERIFIED_NO_PETS")

#: Counted from the committed authority, not estimated. The 177 unanswered
#: confirmed routes split 106 payable / 71 not, and the 71 are 69 Marriott
#: and Hilton rows plus 2 source-silence holds.
BRAND_WALL_ROWS = 69
POLICY_NOT_FOUND_HOLDS = 2
UNEXPECTED_PAGE_ROWS = 2
CENSUS_WITHOUT_ROUTE = 45


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def wilson(successes: int, trials: int) -> Tuple[float, float, float]:
    if trials <= 0:
        return (0.0, 0.0, 0.0)
    point = successes / trials
    denominator = 1.0 + (Z * Z) / trials
    centre = (point + (Z * Z) / (2 * trials)) / denominator
    margin = (Z * math.sqrt(point * (1 - point) / trials
                            + (Z * Z) / (4 * trials * trials))) / denominator
    return (point, max(0.0, centre - margin), min(1.0, centre + margin))


def rate(successes: int, trials: int, what: str) -> Dict:
    point, low, high = wilson(successes, trials)
    return OrderedDict([
        ("measures", what),
        ("successes", successes),
        ("denominator", trials),
        ("point", round(point, 4)),
        ("wilson_lower_95", round(low, 4)),
        ("wilson_upper_95", round(high, 4)),
    ])


def run() -> None:
    pass008 = load(C008)["results"]
    pass009 = load(C009)["results"]
    yield008 = load(Y008)
    qualification = load(QUAL)

    # ---- 1. RAW PAID ATTEMPT YIELD ------------------------------------- #
    raw = pass008 + pass009
    raw_counts = Counter(result["class"] for result in raw)
    raw_acquired = sum(raw_counts[cls] for cls in ACQUIRED)
    credits = CREDITS_008 + CREDITS_009
    raw_block = OrderedDict([
        ("what_it_is",
         "every paid attempt across both passes, including the 49 the parser "
         "defect wasted, the 2 pages Pass 008 bought twice, and the 29 quota "
         "refusals that billed nothing. This is what Detroit's Firecrawl "
         "evidence cost."),
        ("attempts", len(raw)),
        ("attempts_pass_008", len(pass008)),
        ("attempts_pass_009_retry", len(pass009)),
        ("counts", OrderedDict(sorted(raw_counts.items()))),
        ("credits_spent", credits),
        ("usd_spent", round(credits * USD_PER_CREDIT, 2)),
        ("pet_friendly", rate(raw_counts["PET_FRIENDLY"], len(raw),
                              "paid attempts that ended pet-friendly")),
        ("publication_grade", rate(raw_acquired, len(raw),
                                   "paid attempts that ended in a "
                                   "publication-grade answer either way")),
    ])

    # ---- 2. POST-PARSER-CORRECTED CAPABILITY --------------------------- #
    # UNIQUE PROPERTIES that reached the corrected gate. A property is counted
    # once: Pass 008's two double-buys are one property each, and a row the
    # retry answered supersedes the defect-blocked attempt that preceded it.
    corrected: Dict[str, Dict] = {}
    for result in pass008:
        # Pass 008 rows that reached the gate on their own merits -- i.e. were
        # not defect-blocked. The yield artifact already identified those.
        if result["class"] == "UNEXPECTED_PAGE":
            continue          # every Pass 008 UNEXPECTED_PAGE was the defect
        corrected[result["identity_key"]] = result
    for result in pass009:
        if result.get("rate_limited"):
            continue          # never reached a property; not the lane's doing
        corrected[result["identity_key"]] = result

    cap_counts = Counter(result["class"] for result in corrected.values())
    cap_acquired = sum(cap_counts[cls] for cls in ACQUIRED)
    capability = OrderedDict([
        ("what_it_is",
         "UNIQUE PROPERTIES that reached the corrected identity gate. Counted "
         "once each: a page bought twice is one property. Quota refusals are "
         "excluded from both numerator and denominator -- they never reached a "
         "property, and counting them as lane failures would blame the lane "
         "for this run's own rate limiting."),
        ("unique_properties", len(corrected)),
        ("counts", OrderedDict(sorted(cap_counts.items()))),
        ("publication_grade_properties", cap_acquired),
        ("pet_friendly", rate(cap_counts["PET_FRIENDLY"], len(corrected),
                              "unique properties whose own page states pets "
                              "are accepted")),
        ("publication_grade", rate(cap_acquired, len(corrected),
                                   "unique properties that yielded a "
                                   "publication-grade answer either way")),
        ("policy_not_found", cap_counts["POLICY_NOT_FOUND"]),
        ("identity_mismatch", cap_counts["IDENTITY_MISMATCH"]),
        ("unexpected_page", cap_counts["UNEXPECTED_PAGE"]),
        ("holds", cap_counts["HOLD"]),
        ("failures", cap_counts["ACQUISITION_FAILURE"]),
    ])

    # ---- Phase 8: what Detroit still needs ----------------------------- #
    rate_limited = [result for result in pass009 if result.get("rate_limited")]
    deferred = int(qualification["deferred"])
    pet_lower = capability["pet_friendly"]["wilson_lower_95"]
    pet_point = capability["pet_friendly"]["point"]
    pub_lower = capability["publication_grade"]["wilson_lower_95"]

    remaining = OrderedDict([
        ("firecrawl_rerunnable_now", OrderedDict([
            ("rows", len(rate_limited)),
            ("why", "hit this plan's request limit, never reached the "
                    "property, billed nothing"),
            ("cost_to_retry_credits", len(rate_limited) * 1.0),
            ("cost_to_retry_usd",
             round(len(rate_limited) * 1.0 * USD_PER_CREDIT, 2)),
            ("basis", "1.00 credits per BILLED attempt, measured exactly in "
                      "this run: 19 billed attempts consumed 19 credits"),
            ("expected_publication_grade_at_wilson_lower",
             round(len(rate_limited) * pub_lower, 1)),
            ("expected_pet_friendly_at_wilson_lower",
             round(len(rate_limited) * pet_lower, 1)),
            ("note", "this order forbids a second retry of a row, so these "
                     "are left for a future one -- run at a slower pace"),
        ])),
        ("brightdata_required", OrderedDict([
            ("rows", deferred + BRAND_WALL_ROWS),
            ("status", "NOT AUTHORISED AND NOT RUN"),
            ("two_disjoint_populations", OrderedDict([
                ("registry_deferred", OrderedDict([
                    ("rows", deferred),
                    ("why", "the committed routing registry routes these "
                            "families to the managed browser"),
                ])),
                ("brand_wall", OrderedDict([
                    ("rows", BRAND_WALL_ROWS),
                    ("why", "Marriott and Hilton, excluded from the Firecrawl "
                            "cohort by host before the registry was even "
                            "consulted"),
                ])),
            ])),
            ("correction",
             "the PASS 008 report gave this population as 43. That was the "
             "registry-deferred subset only, because it was read off the lane "
             "qualification artifact, which had already had the %d Marriott "
             "and Hilton rows removed by host. The two sets are disjoint and "
             "the full Bright-Data-required population is %d."
             % (BRAND_WALL_ROWS, deferred + BRAND_WALL_ROWS)),
        ])),
        ("policy_not_found_holds", OrderedDict([
            ("rows", POLICY_NOT_FOUND_HOLDS),
            ("why", "every page on each site was checked and states nothing "
                    "about pets. SOURCE SILENCE IS ABSENCE, so these are not "
                    "a negative claim and no lane can resolve them"),
        ])),
        ("url_missing", OrderedDict([
            ("rows", 0),
            ("why", "every confirmed route carries an official property URL; "
                    "ZERO-COST-RECOVERY-007 closed this category"),
        ])),
        ("routing_repair_required", OrderedDict([
            ("rows", UNEXPECTED_PAGE_ROWS),
            ("why", "reached the corrected identity gate and were still "
                    "refused, so the routed URL -- not the parser -- is what "
                    "is wrong for these two"),
        ])),
        ("census_without_a_route", OrderedDict([
            ("rows", CENSUS_WITHOUT_ROUTE),
            ("why", "in the census but never routed; a discovery question, "
                    "not an acquisition one"),
        ])),
    ])

    recommendation = OrderedDict([
        ("question", "are the Bright Data rows still worth buying, given the "
                     "corrected Firecrawl measurement?"),
        ("what_the_measurement_says",
         "the corrected lane is excellent at ANSWERING (%.0f%% publication "
         "grade, Wilson lower %.0f%%) and poor at finding PET-FRIENDLY ones: "
         "%d of %d unique properties, point %.0f%%, Wilson lower %.0f%%. "
         "Detroit's chain inventory is overwhelmingly no-pets -- every one of "
         "the 18 retry reads was an explicit first-party refusal naming the "
         "property."
         % (capability["publication_grade"]["point"] * 100,
            pub_lower * 100, cap_counts["PET_FRIENDLY"], len(corrected),
            pet_point * 100, pet_lower * 100)),
        ("recommendation", "DEFER the Bright Data cohort; run the %d free "
                           "re-runnable Firecrawl rows first"
                           % len(rate_limited)),
        ("reasoning",
         "the %d Bright Data rows are the dearer lane, and the corrected "
         "measurement prices what they would most likely return: %.1f "
         "pet-friendly at the Wilson lower bound, %.1f at the point estimate. "
         "The %d rate-limited Firecrawl rows are the same market at a fraction "
         "of the price and are already qualified, so they should be exhausted "
         "before a managed-browser cohort is priced at all. Buying Bright Data "
         "now would pay the most for the least-known return."
         % (deferred + BRAND_WALL_ROWS,
            (deferred + BRAND_WALL_ROWS) * pet_lower,
            (deferred + BRAND_WALL_ROWS) * pet_point,
            len(rate_limited))),
        ("recommended_next_hard_cap_usd", 5.00),
        ("what_that_buys", "the %d re-runnable Firecrawl rows at 1.00 credit "
                           "each ($%.2f) with margin for retries, at a slower "
                           "request pace"
         % (len(rate_limited), len(rate_limited) * USD_PER_CREDIT)),
        ("not_authorised_here", "this is a recommendation only; no cohort is "
                                "authorised and Bright Data was not run"),
    ])

    write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-true-firecrawl-yield/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("note",
         "Pass 008 and the 009 retry combined. The cost of the broken-parser "
         "attempts is not erased: it is carried in full in the raw denominator "
         "and excluded only from the capability rate, which asks a different "
         "question."),
        ("raw_paid_attempt_yield", raw_block),
        ("post_parser_corrected_capability", capability),
        ("spend", OrderedDict([
            ("pass_008_credits", CREDITS_008),
            ("pass_009_credits", CREDITS_009),
            ("cumulative_credits", credits),
            ("cumulative_usd", round(credits * USD_PER_CREDIT, 2)),
            ("pass_008_cap_usd", 20.00),
            ("pass_009_cap_usd", 7.00),
        ])),
        ("remaining_detroit_need", remaining),
        ("recommendation", recommendation),
        ("prior_yield_artifact_superseded_by_this_one",
         yield008["schema"]),
    ]))

    print("=== Phase 7: true Firecrawl yield ===")
    print("\n  1. RAW PAID ATTEMPT YIELD (n=%d, %.0f credits, $%.2f)"
          % (len(raw), credits, credits * USD_PER_CREDIT))
    for key in ("pet_friendly", "publication_grade"):
        block = raw_block[key]
        print("     %-19s %2d/%-3d point %.3f  wilson [%.3f, %.3f]"
              % (key, block["successes"], block["denominator"], block["point"],
                 block["wilson_lower_95"], block["wilson_upper_95"]))
    print("\n  2. POST-PARSER-CORRECTED CAPABILITY (unique properties n=%d)"
          % len(corrected))
    for key in ("pet_friendly", "publication_grade"):
        block = capability[key]
        print("     %-19s %2d/%-3d point %.3f  wilson [%.3f, %.3f]"
              % (key, block["successes"], block["denominator"], block["point"],
                 block["wilson_lower_95"], block["wilson_upper_95"]))
    print("\n=== Phase 8: remaining need and recommendation ===")
    print("  firecrawl re-runnable now :", len(rate_limited),
          "($%.2f, billed nothing the first time)"
          % remaining["firecrawl_rerunnable_now"]["cost_to_retry_usd"])
    print("  brightdata-required       :", deferred + BRAND_WALL_ROWS,
          "= %d registry-deferred + %d Marriott/Hilton brand wall (NOT authorised)"
          % (deferred, BRAND_WALL_ROWS))
    print("  recommendation            :", recommendation["recommendation"])
    print("wrote", OUT_PATH.name)


if __name__ == "__main__":
    run()

# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-PLACES-BATCH-027 -- the second 20, and the two batches added up.

WHAT IS NEW HERE IS THE ARITHMETIC, NOT THE METHOD
---------------------------------------------------
Every rule that decides whether a lookup binds is imported from
``grand_rapids_holland_places_pilot_026`` and CALLED, not copied: the binder,
the URL acceptability test, the dual-brand refusal, the ledger discipline, the
early stop and the request budget. A second batch measured with a second
implementation would not be comparable with the first, and comparing them is
the whole reason this batch exists.

The cohort comes from the same selector too. It is ledger-aware, so re-running
it after 026 cannot hand back a row 026 already bought -- that is what a ledger
without an expiry date is FOR. 76 url-less identities, 27 excluded (7 held out
for cause, 20 already looked up), 5 deferred as same-doorway, 49 eligible, 20
sampled, 29 left.

WHAT THIS MODULE ADDS
----------------------
Three rates, published side by side and never averaged into one another:

    026 alone      9 of 20      the pilot, on a pool of 63 sampleable rows
    027 alone      ? of 20      this batch, on what the ledger left
    cumulative     ? of 40      the only rate with 40 attempts under it

and then the question the work order actually asks: given the URLs recovered
across BOTH batches, how many pet-friendly profiles can this market expect, and
what is the SMALLEST policy-acquisition cohort that would deliver the eight it
still needs?

That last number is the deliverable. Recovering a URL publishes nothing. Every
recovered URL still has to be fetched by a paid lane, read, reviewed and
signed, and none of that is authorised here.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL  # noqa: E402
from scripts.pettripfinder.discovery import constants as C                     # noqa: E402
from scripts.pettripfinder import grand_rapids_holland_places_cohort_026 as COHORT  # noqa: E402
from scripts.pettripfinder import grand_rapids_holland_places_pilot_026 as PILOT    # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
COHORT_PATH = LP / "grand_rapids_holland_mi_places_batch_cohort_027.json"
REPORT_PATH = LP / "grand_rapids_holland_mi_places_batch_027.json"
PILOT_REPORT = LP / "grand_rapids_holland_mi_places_pilot_026.json"
PILOT_COHORT = LP / "grand_rapids_holland_mi_places_pilot_cohort_026.json"
CACHE_DIR = _REPO_ROOT / "data" / "discovery" / "grand_rapids_places_027" / "cache"

SCHEMA = "ptf-places-batch-rollup/1.0"
WORK_ORDER = "PTF-GRAND-RAPIDS-PLACES-BATCH-027"
RUN_ID = "grand-rapids-holland-mi-places-027"
MARKET = "grand-rapids-holland-mi"
MAX_REQUESTS = 20

PUBLISHED_TODAY = PILOT.PUBLISHED_TODAY          # 35
TARGET = PILOT.TARGET                            # 43
PET_SUCCESSES = PILOT.PET_FRIENDLY_SUCCESSES     # 34
PET_TRIALS = PILOT.PET_FRIENDLY_TRIALS           # 65

READY = "READY_FOR_POLICY_ACQUISITION"
ONE_MORE = "RUN_ONE_MORE_SMALL_PLACES_BATCH"
STOP = "STOP_RECOVERY_AND_LAUNCH_35"


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The cohort
# --------------------------------------------------------------------------- #

def build_cohort() -> Dict:
    """The same selector, over the pool the ledger has already shrunk."""
    return COHORT.build(work_order=WORK_ORDER)


def write_cohort(path: Path = COHORT_PATH) -> Dict:
    document = build_cohort()
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document


# --------------------------------------------------------------------------- #
# The run -- 026's runner, with 027's labels
# --------------------------------------------------------------------------- #

def run(*, live: bool) -> Dict:
    return PILOT.run(live=live, cohort_path=COHORT_PATH, work_order=WORK_ORDER,
                     run_id=RUN_ID, cache_dir=CACHE_DIR)


# --------------------------------------------------------------------------- #
# Two batches, added up
# --------------------------------------------------------------------------- #

def executed_rows(report: Mapping) -> List[Dict]:
    return [row for row in report["rows"] if row.get("requests_made")]


def recovered_urls(report: Mapping) -> List[Dict]:
    return list(report["recovered_urls"])


def rollup(batch: Mapping, pilot: Mapping) -> Dict:
    """The 40-request picture, and what it says about 43.

    The three rates are reported SEPARATELY and the projection is run under
    each of them, because a reader deciding whether to spend again should see
    what the answer depends on. The cumulative rate is the one with 40 attempts
    behind it and the narrowest interval, so it carries the recommendation.
    """
    pilot_rows, batch_rows = executed_rows(pilot), executed_rows(batch)
    pilot_urls, batch_urls = recovered_urls(pilot), recovered_urls(batch)

    cumulative_attempts = len(pilot_rows) + len(batch_rows)
    cumulative_bound = len(pilot_urls) + len(batch_urls)

    rate_026 = PILOT.rate_block(len(pilot_urls), len(pilot_rows),
                                "URLs per lookup, batch 026 alone")
    rate_027 = PILOT.rate_block(len(batch_urls), len(batch_rows),
                                "URLs per lookup, batch 027 alone")
    rate_all = PILOT.rate_block(cumulative_bound, cumulative_attempts,
                                "URLs per lookup, both batches -- the only "
                                "rate with 40 attempts behind it")
    pet_rate = PILOT.rate_block(PET_SUCCESSES, PET_TRIALS,
                                "publication-grade pet-friendly profiles per "
                                "property attempted, this market's own paid "
                                "acquisition run")

    remaining = batch["projection"]["remaining_eligible_identities"]

    def under(rate: Mapping, label: str) -> Dict:
        """What the remaining pool is worth if this rate is the true one."""
        low = int(remaining * rate["wilson_lower_95"] * pet_rate["wilson_lower_95"])
        point = int(remaining * (rate["point"] or 0.0) * (pet_rate["point"] or 0.0))
        high = int(remaining * rate["wilson_upper_95"] * pet_rate["wilson_upper_95"])
        return OrderedDict((
            ("rate_used", label),
            ("urls_expected_low", int(remaining * rate["wilson_lower_95"])),
            ("urls_expected_point", int(remaining * (rate["point"] or 0.0))),
            ("urls_expected_high", int(remaining * rate["wilson_upper_95"])),
            ("additional_profiles_low", low),
            ("additional_profiles_point", point),
            ("additional_profiles_high", high),
        ))

    # ------------------------------------------------------------------ #
    # What the URLs ALREADY IN HAND are worth. This is the number that
    # decides whether more lookups are needed, and it involves no further
    # discovery at all.
    # ------------------------------------------------------------------ #
    in_hand = cumulative_bound
    profiles_in_hand_low = int(in_hand * pet_rate["wilson_lower_95"])
    profiles_in_hand_point = int(in_hand * (pet_rate["point"] or 0.0))
    profiles_in_hand_high = int(in_hand * pet_rate["wilson_upper_95"])
    needed = max(0, TARGET - PUBLISHED_TODAY)

    # The SMALLEST acquisition cohort that delivers the gap. Sized on the
    # conservative pet-friendly rate, per 025's standing rule, and capped at
    # the number of URLs that actually exist to fetch.
    per_property = pet_rate["wilson_lower_95"]
    conservatively_enough = (int(-(-needed // per_property))
                             if per_property > 0 else in_hand)
    minimum_cohort = min(in_hand, conservatively_enough)

    # ------------------------------------------------------------------ #
    # The recommendation.
    # ------------------------------------------------------------------ #
    aborted_on_a_pattern = batch["aborted"] in (
        PILOT.ABORT_PLACE_ID_COLLISION, PILOT.ABORT_PREMISES_DISAGREEMENT)
    gap_covered_conservatively = profiles_in_hand_low >= needed
    gap_covered_at_the_point = profiles_in_hand_point >= needed
    more_would_help = (remaining > 0 and (rate_all["point"] or 0) > 0
                       and not aborted_on_a_pattern)

    if aborted_on_a_pattern:
        decision, why = STOP, (
            "the batch stopped on a false-binding pattern; a rule that binds "
            "the wrong hotel would go on doing it, and no cohort size fixes "
            "that")
    elif gap_covered_at_the_point:
        decision, why = READY, (
            "%d URLs are already in hand and at this market's own measured "
            "pet-friendly rate they are worth %d profiles against a gap of "
            "%d. Buying more lookups before fetching the ones already paid "
            "for spends money to answer a question the evidence on disk can "
            "already answer."
            % (in_hand, profiles_in_hand_point, needed))
    elif more_would_help:
        decision, why = ONE_MORE, (
            "%d URLs in hand are worth about %d profiles against a gap of %d, "
            "so acquisition alone does not close it and %d eligible rows "
            "remain to look up"
            % (in_hand, profiles_in_hand_point, needed, remaining))
    else:
        decision, why = STOP, (
            "no eligible rows remain to look up and the URLs in hand do not "
            "cover the gap")

    next_batch = min(remaining, MAX_REQUESTS) if decision == ONE_MORE else 0

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("run_id", RUN_ID),
        ("batch_027", OrderedDict((
            ("requests_made", batch["requests_made"]),
            ("authorised_cap", MAX_REQUESTS),
            ("cap_held", batch["cap_held"]),
            ("aborted", batch["aborted"]),
            ("abort_detail", batch["abort_detail"]),
            ("urls_recovered", len(batch_urls)),
            ("recovery_rate", rate_027["point"]),
            ("wrong_property_refusals",
             batch["results"]["wrong_property_refusals"]),
            ("ambiguous_or_unbound_with_a_page",
             batch["results"]["ambiguous_or_unbound_with_a_page"]),
            ("no_website_at_all", batch["results"]["no_website_at_all"]),
            ("no_result_at_all", batch["results"]["no_result_at_all"]),
            ("place_id_collisions", batch["results"]["place_id_collisions"]),
            ("premises_disagreements",
             batch["results"]["premises_disagreements"]),
            ("ledger_rows_written", batch["ledger_rows_written"]),
            ("suppressed_duplicate_queries",
             batch["suppressed_duplicate_queries"]),
            ("by_bind_method", batch["results"]["by_bind_method"]),
            ("families_attempted", batch["results"]["families_attempted"]),
            ("families_recovered", batch["results"]["families_recovered"]),
        ))),
        ("cumulative", OrderedDict((
            ("requests", cumulative_attempts),
            ("urls_recovered", cumulative_bound),
            ("recovery_rate", rate_all["point"]),
            ("no_page_exists_to_recover",
             (pilot["why_the_misses_missed"]["no_page_exists_to_recover"]
              + batch["why_the_misses_missed"]["no_page_exists_to_recover"])),
            ("a_page_came_back_and_a_rule_refused_it",
             (pilot["why_the_misses_missed"]["a_page_came_back_and_a_rule_refused_it"]
              + batch["why_the_misses_missed"]["a_page_came_back_and_a_rule_refused_it"])),
            ("place_id_collisions_across_both_batches",
             _collisions(pilot_urls + batch_urls)),
        ))),
        ("rates", OrderedDict((
            ("batch_026", rate_026), ("batch_027", rate_027),
            ("cumulative_40_requests", rate_all),
            ("pet_friendly_per_property", pet_rate),
            ("note", "the three URL rates are published separately and never "
                     "averaged into one another; the cumulative one carries "
                     "the recommendation because it is the one with 40 "
                     "attempts behind it"),
        ))),
        ("projection_of_the_remaining_pool", OrderedDict((
            ("remaining_eligible_identities", remaining),
            ("under_batch_026_rate", under(rate_026, "batch 026 alone")),
            ("under_batch_027_rate", under(rate_027, "batch 027 alone")),
            ("under_the_cumulative_rate", under(rate_all, "both batches")),
        ))),
        ("target_43", OrderedDict((
            ("published_today", PUBLISHED_TODAY), ("target", TARGET),
            ("gap", needed),
            ("urls_in_hand_across_both_batches", in_hand),
            ("expected_additional_routable_hotels", in_hand),
            ("why_routable_equals_urls",
             "every recovered URL passed classify_url_shape against "
             "ROUTABLE_SHAPES and url_names_the_property, which is exactly "
             "what routable means; none needs further discovery to be "
             "fetchable"),
            ("expected_additional_pet_friendly_profiles", OrderedDict((
                ("low", profiles_in_hand_low),
                ("point", profiles_in_hand_point),
                ("high", profiles_in_hand_high),
            ))),
            ("expected_final_published_total", OrderedDict((
                ("low", PUBLISHED_TODAY + profiles_in_hand_low),
                ("point", PUBLISHED_TODAY + profiles_in_hand_point),
                ("high", PUBLISHED_TODAY + profiles_in_hand_high),
            ))),
            ("gap_covered_conservatively", gap_covered_conservatively),
            ("gap_covered_at_the_point_estimate", gap_covered_at_the_point),
            ("caveat", "a recovered URL is not a published profile. Each one "
                       "still has to be fetched by a paid acquisition lane, "
                       "read, reviewed and signed by the founder, and none of "
                       "that is authorised, priced or run here."),
        ))),
        ("minimum_policy_acquisition_cohort", OrderedDict((
            ("size", minimum_cohort),
            ("drawn_from", "the %d URLs recovered across 026 and 027" % in_hand),
            ("sized_on", "the Wilson LOWER bound of this market's own "
                         "pet-friendly rate (%s), per 025's standing rule that "
                         "yield is sized conservatively"
                         % pet_rate["wilson_lower_95"]),
            ("properties_needed_at_that_rate", conservatively_enough),
            ("capped_by_urls_that_exist", in_hand),
            ("covers_the_gap_conservatively", gap_covered_conservatively),
            ("not_priced_here", "no acquisition lane is qualified for these "
                                "families until each URL's host is known to "
                                "the registry; 025 priced a comparable "
                                "Bright Data cohort at 16.0c per property, "
                                "and no cost is committed by this document"),
            ("identity_keys", [row["identity_key"]
                               for row in pilot_urls + batch_urls]),
        ))),
        ("recommendation", OrderedDict((
            ("decision", decision), ("why", why),
            ("next_places_batch_size", next_batch),
            ("this_is_not_an_authorization",
             "no Places request, no acquisition fetch and no deploy may "
             "follow from this document without a separate instruction"),
        ))),
        ("nothing_else_was_run", [
            "Bright Data: not called", "Firecrawl: not called",
            "policy acquisition: not run",
            "premium-domain acquisition: not run",
            "no authority was written, no market assembled, nothing deployed",
        ]),
        ("billing", batch["billing"]),
    ))


def _collisions(rows: Sequence[Mapping]) -> Dict:
    """One Google place bound to two identities, across BOTH batches.

    The single-batch check cannot see a collision that spans them, and a URL
    handed to two hotels is the same defect whichever batch bought it.
    """
    counts = Counter(row["url"] for row in rows if row.get("url"))
    return OrderedDict(sorted((url, n) for url, n in counts.items() if n > 1))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-cohort", action="store_true",
                        help="write the 20-row cohort and stop; makes no "
                             "request")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rebuild-report", action="store_true",
                        help="re-derive the arithmetic from rows already "
                             "bought; makes no request")
    parser.add_argument("--out", default=str(REPORT_PATH))
    args = parser.parse_args(argv)

    if args.build_cohort:
        document = write_cohort()
        population = document["population"]
        print("url-less identities   %d" % population["url_less_identities"])
        print("excluded              %d" % population["excluded"])
        print("deferred (doorway)    %d" % population["deferred_to_a_later_batch"])
        print("eligible              %d" % population["eligible_after_exclusions"])
        print("cohort                %d" % document["sample"]["size"])
        print("families covered      %d of %d"
              % (document["sample"]["families_covered"],
                 document["sample"]["families_in_the_pool"]))
        return 0

    batch_path = Path(args.out).with_name("grand_rapids_holland_mi_places_"
                                          "batch_027_run.json")
    if args.rebuild_report:
        batch = PILOT.rebuild(batch_path, cohort_path=COHORT_PATH)
    else:
        if args.live and not os.environ.get(C.GOOGLE_PLACES_API_KEY_ENV, "").strip():
            raise SystemExit("no %s in the environment"
                             % C.GOOGLE_PLACES_API_KEY_ENV)
        batch = run(live=args.live)
    batch_path.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")

    document = rollup(batch, _load(PILOT_REPORT))
    Path(args.out).write_text(json.dumps(document, indent=2) + "\n",
                              encoding="utf-8")

    b, c = document["batch_027"], document["cumulative"]
    print("batch 027 requests    %d / %d  (cap held: %s)"
          % (b["requests_made"], b["authorised_cap"], b["cap_held"]))
    print("batch 027 aborted     %s" % (b["aborted"] or "no"))
    print("batch 027 URLs        %d   rate=%s" % (b["urls_recovered"],
                                                  b["recovery_rate"]))
    print("cumulative            %d URLs / %d requests   rate=%s"
          % (c["urls_recovered"], c["requests"], c["recovery_rate"]))
    print("no page exists        %d   refused with a page  %d"
          % (c["no_page_exists_to_recover"],
             c["a_page_came_back_and_a_rule_refused_it"]))
    target = document["target_43"]
    print("URLs in hand          %d -> profiles %d..%d..%d  final %d..%d..%d"
          % (target["urls_in_hand_across_both_batches"],
             target["expected_additional_pet_friendly_profiles"]["low"],
             target["expected_additional_pet_friendly_profiles"]["point"],
             target["expected_additional_pet_friendly_profiles"]["high"],
             target["expected_final_published_total"]["low"],
             target["expected_final_published_total"]["point"],
             target["expected_final_published_total"]["high"]))
    print("minimum acq cohort    %d"
          % document["minimum_policy_acquisition_cohort"]["size"])
    print("RECOMMENDATION        %s" % document["recommendation"]["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

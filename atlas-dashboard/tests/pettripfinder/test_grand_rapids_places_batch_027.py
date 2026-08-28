# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-PLACES-BATCH-027 -- the second 20, and the two batches added up.

THE POINT OF A SECOND BATCH IS COMPARABILITY, so the tests are weighted towards
the things that would destroy it. 027 must run 026's code rather than a copy of
it; the ledger, not a list this module keeps, must be what holds 026's rows out;
and the three rates must be published separately rather than blended, because a
reader deciding whether to spend again needs to see what the answer rests on.

THE DECISIVE FACT is that twenty URLs are now in hand and, at this market's own
measured pet-friendly rate, they cover the gap of eight even at the conservative
bound. That is what turns the recommendation from "buy more lookups" into "fetch
the ones already paid for", and it is pinned here.

WHAT DID NOT HAPPEN is pinned too. No rule was widened mid-run. Both at-risk
rows -- the Travelodge and the DoubleTree that each have a qualified twin in
this census -- were answered by the provider and refused by the rule, which is
the wrong-property guard working on the exact cases the cohort sampled it for.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL  # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC         # noqa: E402
from scripts.pettripfinder import grand_rapids_holland_places_cohort_026 as COHORT  # noqa: E402
from scripts.pettripfinder import grand_rapids_holland_places_pilot_026 as PILOT    # noqa: E402
from scripts.pettripfinder import grand_rapids_holland_places_batch_027 as BATCH     # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
COHORT_DOC = LP / "grand_rapids_holland_mi_places_batch_cohort_027.json"
RUN_DOC = LP / "grand_rapids_holland_mi_places_batch_027_run.json"
ROLLUP_DOC = LP / "grand_rapids_holland_mi_places_batch_027.json"
PILOT_DOC = LP / "grand_rapids_holland_mi_places_pilot_026.json"


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def cohort():
    return _load(COHORT_DOC)


@pytest.fixture(scope="module")
def run():
    return _load(RUN_DOC)


@pytest.fixture(scope="module")
def rollup():
    return _load(ROLLUP_DOC)


@pytest.fixture(scope="module")
def pilot():
    return _load(PILOT_DOC)


# --------------------------------------------------------------------------- #
# The method is the SAME method
# --------------------------------------------------------------------------- #

def test_batch_027_calls_the_pilot_rather_than_reimplementing_it():
    """A second batch measured with a second implementation would not be
    comparable with the first, and comparing them is why it exists.

    Read off the AST rather than the text: a rule NAMED in a docstring is
    documentation, and only a rule DEFINED or CALLED here would be a second
    copy of something 026 already proved.
    """
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(BATCH))

    defined = {node.name for node in ast.walk(tree)
               if isinstance(node, ast.FunctionDef)}
    for rule in ("bind_one", "bind_state", "observations", "premises_agreement",
                 "names_may_share_a_url", "classify_url_shape",
                 "url_names_the_property", "why_it_missed"):
        assert rule not in defined, (
            "%r defined here would be a second copy of a rule 026 proved" % rule)

    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                base = func.value
                calls.add("%s.%s" % (getattr(base, "id", "?"), func.attr))
            elif isinstance(func, ast.Name):
                calls.add(func.id)
    assert "PILOT.run" in calls, "the execution must be 026's"
    assert "COHORT.build" in calls, "the selector must be 026's"
    assert "PILOT.rate_block" in calls, "the arithmetic must be 026's"
    # No provider client of its own: the only way to spend is through PILOT.
    assert not {c for c in calls if "GooglePlaces" in c or "client.search" in c}


def test_the_pilots_own_behaviour_is_unchanged_by_the_parameters():
    """The four parameters added to ``PILOT.run`` default to 026's constants,
    so 026 still reproduces byte for byte."""
    import inspect
    signature = inspect.signature(PILOT.run)
    assert signature.parameters["work_order"].default == PILOT.WORK_ORDER
    assert signature.parameters["run_id"].default == PILOT.RUN_ID
    assert signature.parameters["cohort_path"].default is None
    assert signature.parameters["cache_dir"].default is None


def test_the_cap_held(run, rollup):
    assert run["authorised_request_cap"] == BATCH.MAX_REQUESTS == 20
    assert run["requests_made"] == 20
    assert run["cap_held"] is True
    assert rollup["batch_027"]["cap_held"] is True
    assert rollup["batch_027"]["requests_made"] == 20


# --------------------------------------------------------------------------- #
# The ledger, not a hand-kept list, is what holds 026 out
# --------------------------------------------------------------------------- #

def test_no_row_from_026_was_bought_again(cohort, pilot, run):
    already = {r["identity_key"] for r in pilot["rows"] if r.get("requests_made")}
    now = {r["identity_key"] for r in run["rows"] if r.get("requests_made")}
    assert len(already) == 20 and len(now) == 20
    assert not (already & now)


def test_the_ledger_is_what_excluded_them_not_a_list_in_this_module(cohort, pilot):
    already = {r["identity_key"] for r in pilot["rows"] if r.get("requests_made")}
    suppressed = {row["identity_key"] for row in cohort["excluded_rows"]
                  if row["rule"] == COHORT.EXCLUDED_ALREADY_LOOKED_UP}
    assert already <= suppressed
    assert len(suppressed) == 20


def test_every_other_exclusion_still_cites_a_prior_ruling(cohort):
    rules = {row["rule"] for row in cohort["excluded_rows"]}
    assert rules <= {COHORT.EXCLUDED_IDENTITY_HOLD,
                     COHORT.EXCLUDED_DEDUP_SAFE_MERGE,
                     COHORT.EXCLUDED_ALREADY_LOOKED_UP}
    keys = {row["identity_key"] for row in cohort["excluded_rows"]}
    assert "comfort inn" in keys                      # 019 hold
    assert "budgetel inn and suites hotel" in keys    # third switchboard pair
    for row in cohort["deferred_rows"]:
        assert row["rule"] == COHORT.DEFERRED_SHARED_DOORWAY
        assert "rules nothing about whether the two are one hotel" in row["why"]


def test_all_forty_attempts_are_in_the_cross_run_ledger(run, pilot):
    ledger = _load(LP / "ptf_discovery_attempt_ledger_001.json")
    ours = [a for a in ledger["attempts"]
            if a["market_id"] == "grand-rapids-holland-mi"]
    assert len(ours) == 40
    by_order = {}
    for attempt in ours:
        by_order.setdefault(attempt["work_order"], []).append(attempt)
    assert len(by_order[PILOT.WORK_ORDER]) == 20
    assert len(by_order[BATCH.WORK_ORDER]) == 20
    assert run["ledger_rows_written"] == 20


def test_neither_batch_can_run_again(cohort, run, pilot):
    """Both cohorts are now spent. A third batch draws from what is left, and
    the builder cannot hand back either twenty."""
    ledger = DAL.load(LP / "ptf_discovery_attempt_ledger_001.json")
    index = DAL.DiscoveryIndex(ledger)
    spent = ({r["identity_key"] for r in pilot["rows"] if r.get("requests_made")}
             | {r["identity_key"] for r in run["rows"] if r.get("requests_made")})
    for entry in cohort["sample"]["rows"]:
        decision = DAL.decide(PILOT.census_row(entry), index,
                              provider=cohort["provider"],
                              method=cohort["discovery_method"],
                              field_mask=tuple(cohort["field_mask"]))
        assert decision["decision"] not in DAL.ALLOWED_DECISIONS
    again = COHORT.build(work_order="PTF-TEST")
    assert not (spent & {r["identity_key"] for r in again["sample"]["rows"]})


# --------------------------------------------------------------------------- #
# The binding rules were not widened
# --------------------------------------------------------------------------- #

def test_no_false_binding_pattern_appeared(run, rollup):
    assert run["aborted"] == ""
    assert run["results"]["place_id_collisions"] == {}
    assert run["results"]["premises_disagreements"] == []
    assert rollup["cumulative"]["place_id_collisions_across_both_batches"] == {}


def test_a_collision_spanning_the_two_batches_would_be_caught():
    """The single-batch check cannot see a URL handed to two hotels when one
    was bought in each batch, and that is the same defect either way."""
    assert BATCH._collisions([
        {"identity_key": "a", "url": "https://example.com/x"},
        {"identity_key": "b", "url": "https://example.com/x"},
    ]) == {"https://example.com/x": 2}
    assert BATCH._collisions([{"identity_key": "a", "url": "https://e.com/x"}]) == {}


def test_both_at_risk_rows_were_answered_and_refused(run):
    """The Travelodge and the DoubleTree each have a qualified twin in this
    census. Google returned a real brand page for both; the rule refused both.
    That is the wrong-property guard working on the cases it was sampled for."""
    rows = {r["identity_key"]: r for r in run["rows"] if r.get("requests_made")}
    at_risk = [r for r in rows.values()
               if r["expected_binding_method"] == "NAME_AND_POSTAL_CODE_AT_RISK"]
    assert len(at_risk) == 2
    for row in at_risk:
        assert row["bound"] is False
        assert row["returned"], "the provider did answer; the RULE refused it"
        assert row["returned"][0]["website_uri"]


def test_the_dual_brand_and_presentation_rules_are_both_still_wired():
    assert hasattr(URC, "names_may_share_a_url")
    assert hasattr(URC, "presentation_key")
    assert URC.names_may_share_a_url(
        "Comfort Inn", "Comfort Suites Grandville Grand Rapids SW")[0] is False
    key = lambda n: URC.presentation_key(n, state_code="MI", unordered=True)  # noqa: E731
    assert key("Courtyard Grand Rapids Airport") != \
        key("Courtyard Grand Rapids Downtown")


def test_every_recovered_url_is_a_routable_property_page(run):
    from scripts.pettripfinder.acquisition import market_routing as MR
    assert len(run["recovered_urls"]) == 11
    for row in run["recovered_urls"]:
        assert MR.classify_url_shape(row["url"]) in MR.ROUTABLE_SHAPES
        assert row["bind_method"] in (URC.BIND_PHONE, URC.BIND_NAME_POSTAL)
        assert row["premises_agrees"] is True


# --------------------------------------------------------------------------- #
# The numbers
# --------------------------------------------------------------------------- #

def test_batch_027_measured_eleven_of_twenty(rollup):
    batch = rollup["batch_027"]
    assert batch["urls_recovered"] == 11
    assert batch["recovery_rate"] == 0.55
    assert batch["wrong_property_refusals"] == 0
    assert batch["ambiguous_or_unbound_with_a_page"] == 6
    assert batch["no_website_at_all"] == 3
    assert batch["no_result_at_all"] == 0
    assert batch["suppressed_duplicate_queries"] == 0


def test_the_cumulative_rate_is_twenty_of_forty(rollup):
    cumulative = rollup["cumulative"]
    assert cumulative["requests"] == 40
    assert cumulative["urls_recovered"] == 20
    assert cumulative["recovery_rate"] == 0.5


def test_the_three_rates_are_published_separately_and_never_blended(rollup):
    rates = rollup["rates"]
    assert rates["batch_026"]["successes"] == 9 and rates["batch_026"]["trials"] == 20
    assert rates["batch_027"]["successes"] == 11 and rates["batch_027"]["trials"] == 20
    assert rates["cumulative_40_requests"]["successes"] == 20
    assert rates["cumulative_40_requests"]["trials"] == 40
    assert "never averaged into one another" in rates["note"]
    # More attempts, narrower interval. That is why the cumulative one carries
    # the recommendation.
    def width(block):
        return block["wilson_upper_95"] - block["wilson_lower_95"]
    assert width(rates["cumulative_40_requests"]) < width(rates["batch_026"])
    assert width(rates["cumulative_40_requests"]) < width(rates["batch_027"])


def test_the_remaining_pool_is_projected_under_each_rate(rollup):
    projection = rollup["projection_of_the_remaining_pool"]
    assert projection["remaining_eligible_identities"] == 29
    for key in ("under_batch_026_rate", "under_batch_027_rate",
                "under_the_cumulative_rate"):
        block = projection[key]
        assert block["urls_expected_low"] <= block["urls_expected_point"] \
            <= block["urls_expected_high"]
        assert block["additional_profiles_low"] <= block["additional_profiles_point"] \
            <= block["additional_profiles_high"]


def test_the_pet_friendly_rate_is_this_markets_own(rollup):
    pet = rollup["rates"]["pet_friendly_per_property"]
    assert pet["successes"] == 34 and pet["trials"] == 65
    assert "this market's own" in pet["what"]


# --------------------------------------------------------------------------- #
# Target 43
# --------------------------------------------------------------------------- #

def test_the_urls_in_hand_cover_the_gap_even_conservatively(rollup):
    """The decisive fact of this batch, and the reason the recommendation is
    to fetch rather than to buy more lookups."""
    target = rollup["target_43"]
    assert target["published_today"] == 35 and target["target"] == 43
    assert target["gap"] == 8
    assert target["urls_in_hand_across_both_batches"] == 20
    assert target["expected_additional_routable_hotels"] == 20
    profiles = target["expected_additional_pet_friendly_profiles"]
    assert profiles["low"] >= target["gap"], (
        "the conservative bound is what makes this READY rather than a hope")
    assert target["gap_covered_conservatively"] is True
    assert target["expected_final_published_total"]["low"] >= 43


def test_a_recovered_url_is_still_not_a_published_profile(rollup):
    caveat = rollup["target_43"]["caveat"]
    assert "still has to be fetched" in caveat
    assert "none of that is authorised" in caveat


def test_the_minimum_acquisition_cohort_is_sized_conservatively(rollup):
    cohort = rollup["minimum_policy_acquisition_cohort"]
    assert cohort["size"] == 20
    assert cohort["capped_by_urls_that_exist"] == 20
    assert "LOWER bound" in cohort["sized_on"]
    assert cohort["covers_the_gap_conservatively"] is True
    assert len(cohort["identity_keys"]) == 20
    assert len(set(cohort["identity_keys"])) == 20, "one hotel, one fetch"
    assert "no cost is committed" in cohort["not_priced_here"]


def test_the_acquisition_cohort_names_only_rows_with_a_recovered_url(rollup, run,
                                                                    pilot):
    recovered = ({r["identity_key"] for r in pilot["recovered_urls"]}
                 | {r["identity_key"] for r in run["recovered_urls"]})
    assert set(rollup["minimum_policy_acquisition_cohort"]["identity_keys"]) \
        == recovered


# --------------------------------------------------------------------------- #
# The decision
# --------------------------------------------------------------------------- #

def test_exactly_one_recommendation_is_given(rollup):
    decision = rollup["recommendation"]["decision"]
    assert decision in (BATCH.READY, BATCH.ONE_MORE, BATCH.STOP)
    assert decision == BATCH.READY
    assert rollup["recommendation"]["next_places_batch_size"] == 0
    assert rollup["recommendation"]["why"]
    assert "without a separate instruction" in \
        rollup["recommendation"]["this_is_not_an_authorization"]


def test_no_dollar_figure_was_invented(rollup, run):
    billing = rollup["billing"]
    assert billing["usd_observable"] is False
    assert billing["measured_cost_usd"] is None
    assert billing["priced_in"] == "REQUESTS"
    for row in run["rows"]:
        if row.get("requests_made"):
            assert row["measured_cost_usd"] is None


def test_no_other_provider_was_touched(rollup):
    joined = " ".join(rollup["nothing_else_was_run"]).lower()
    for provider in ("bright data", "firecrawl", "policy acquisition",
                     "premium-domain"):
        assert provider in joined


# --------------------------------------------------------------------------- #
# Nothing else moved
# --------------------------------------------------------------------------- #

def test_no_authority_was_written():
    import subprocess
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/identity_census",
         "launch_packages/pettripfinder/hotel_policy_facts_grand-rapids-holland-mi.json",
         "deploy/netlify"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        "a discovery batch writes no authority: %r" % result.stdout)


def test_the_published_count_did_not_move():
    package = _load(LP / "hotel_policy_facts_grand-rapids-holland-mi.json")
    assert package["count"] == 35

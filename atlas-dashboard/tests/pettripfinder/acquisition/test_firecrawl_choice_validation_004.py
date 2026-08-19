"""PTF-FIRECRAWL-CHOICE-VALIDATION-004 -- completing the Milwaukee Choice sample.

Three things are protected here.

First, that the sample is DERIVED rather than curated: fifteen Choice rows in
the committed queue, minus the three PTF-FIRECRAWL-HARD-LANES-003 already paid
for, equals the twelve run here -- including the four the Web Unlocker could not
fetch and the four the market's budget cap never reached. Dropping the awkward
ones would flatter the result, so the arithmetic is asserted.

Second, that the acquisition path is the proven one and not a copy of it. The
whole reason two runs can be folded into one score is that they used the same
profiles, the same gates and the same definition of MISMATCH. These tests
assert object identity, not resemblance.

Third, that agreement and coverage stay separate. Eight of the twelve have no
Bright Data answer to check against. A run that reported "12/12" as twelve
confirmations would be claiming something it did not measure.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import firecrawl_choice_validation_004 as CV
from scripts.pettripfinder.acquisition import firecrawl_hard_lanes_003 as HARD
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
HARD_REPORT = REPORTS / "ptf_firecrawl_hard_lanes_003.json"
VALIDATION_REPORT = REPORTS / "ptf_firecrawl_choice_validation_004.json"
PROPOSAL = REPORTS / "ptf_firecrawl_choice_route_proposal_004.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")


class TestTheSampleIsDerivedNotCurated:
    def test_the_arithmetic_the_work_order_pins_actually_holds(self):
        entries, tested = CV.remaining_sample()
        assert len(tested) == 3
        assert len(entries) == 12
        assert len(tested) + len(entries) == 15

    def test_no_committed_property_is_re_run(self):
        """Re-running the three would spend credits to reproduce a known
        answer, and would let the same property be counted twice."""
        entries, tested = CV.remaining_sample()
        assert not (set(tested) & {e["identity_key"] for e in entries})

    def test_no_duplicate_identity_keys(self):
        entries, _ = CV.remaining_sample()
        keys = [e["identity_key"] for e in entries]
        assert len(set(keys)) == len(keys)

    def test_the_hard_rows_were_not_swapped_for_easier_ones(self):
        """The four the Web Unlocker could not fetch are the whole point of
        running the rest of the lane. They are also the only rows where a new
        provider can produce coverage rather than reproduce it."""
        entries, _ = CV.remaining_sample()
        states = [e["baseline_state"] for e in entries]
        assert states.count("TECHNICAL_FALLBACK_REQUIRED") == 4
        assert states.count("NOT_ATTEMPTED") == 4
        assert states.count("ACQUIRED_PUBLICATION_GRADE") == 4

    def test_membership_comes_from_the_committed_queue(self):
        entries, tested = CV.remaining_sample()
        queue = {r["identity_key"] for r in CV.queue_rows()
                 if r["brand"] == "CHOICE"}
        assert {e["identity_key"] for e in entries} | set(tested) == queue

    def test_the_already_tested_keys_are_read_not_retyped(self):
        """If this file listed them, the two could drift apart and a property
        would be paid for twice."""
        expected = sorted({r["identity_key"] for r in json.loads(
            HARD_REPORT.read_text(encoding="utf-8-sig"))["sample"]
            if r["brand"] == "CHOICE"})
        assert CV.already_tested_keys() == expected

    def test_only_rows_with_a_real_baseline_are_marked_comparable(self):
        entries, _ = CV.remaining_sample()
        for entry in entries:
            if entry["comparable"]:
                assert entry["baseline_state"] == "ACQUIRED_PUBLICATION_GRADE"
                assert entry.get("result")
            else:
                assert "result" not in entry


class TestTheAcquisitionPathIsTheProvenOneNotACopy:
    def test_it_calls_hard_lanes_acquire_itself(self):
        assert CV.HL.acquire is HARD.acquire

    def test_the_profiles_are_the_same_objects(self):
        assert CV.HL.SCRAPE_PROFILE is HARD.SCRAPE_PROFILE
        assert CV.HL.INTERACT_PROFILE is HARD.INTERACT_PROFILE

    def test_the_scrape_profile_still_asks_for_raw_html_and_waits(self):
        """Markdown would drop the class names the brand locators key on, and
        no wait makes a rendering provider a shell renderer with extra steps."""
        assert HARD.SCRAPE_PROFILE["formats"] == ["rawHtml"]
        assert HARD.SCRAPE_PROFILE["waitFor"] >= 6000
        assert HARD.SCRAPE_PROFILE["location"] == {"country": "US"}

    def test_the_interaction_pass_has_no_model_in_it(self):
        actions = HARD.INTERACT_PROFILE["actions"]
        assert not any(a["type"] == "extract" for a in actions)
        assert "prompt" not in json.dumps(actions).lower()

    def test_the_default_provenance_still_reproduces_hard_lanes(self):
        """Parameterising run_id must not have changed what 003 stamps."""
        params = inspect.signature(HARD.acquire).parameters
        assert params["run_id"].default == "firecrawl-hard-lanes-003"
        assert params["ref_tag"].default == "fc3"

    def test_this_work_order_stamps_its_own_provenance(self):
        assert CV.RUN_ID == "firecrawl-choice-validation-004"
        assert CV.REF_TAG == "fc4"

    def test_the_comparison_vocabulary_is_shared(self):
        """Two definitions of MISMATCH would make the runs incomparable, which
        is the only reason to fold them into one score."""
        assert CV.HL.classify is HARD.classify
        assert CV.HL.false_facts is HARD.false_facts
        assert CV.HL.policy_surface_state is HARD.policy_surface_state


class TestTheFailureStateTaxonomy:
    def test_every_state_it_can_emit_was_named_by_the_work_order(self):
        cases = [
            {"firecrawl_state": "ACQUIRED_PUBLICATION_GRADE",
             "surface_state": "HYDRATED", "identity_confirmed": True},
            {"firecrawl_state": "ACQUIRED_NONPUBLICATION_GRADE",
             "surface_state": "HYDRATED", "identity_confirmed": True},
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "ACCESS_DENIED",
             "firecrawl_failure": "ALL_ENGINES_FAILED: x"},
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "ACCESS_DENIED",
             "firecrawl_failure": "RATE_LIMITED: quota"},
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "ACCESS_DENIED"},
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "NAVIGATION_FAILED"},
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "BLANK_PAGE"},
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "IDENTITY_MISMATCH"},
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "POLICY_NOT_FOUND",
             "body_chars": 40000},
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "CAPTURE_FAILED"},
        ]
        for case in cases:
            assert CV.work_order_state(case) in CV.WO_STATES, case

    def test_all_engines_failed_beats_the_generic_access_denied(self):
        """The vendor's own capability verdict must not be filed as a block:
        one says the origin refuses Firecrawl, the other says try again."""
        assert CV.work_order_state(
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "ACCESS_DENIED",
             "firecrawl_failure": "ALL_ENGINES_FAILED: every engine refused"}
        ) == "SCRAPE_ALL_ENGINES_FAILED"

    def test_a_rate_limit_is_not_a_capability_failure(self):
        """Benchmark-002 published 60% for a lane that reaches 100% by making
        exactly this mistake."""
        assert CV.work_order_state(
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "ACCESS_DENIED",
             "firecrawl_failure": "RATE_LIMITED: the plan request limit was hit"}
        ) == "RATE_LIMITED_EXHAUSTED"

    def test_a_small_body_with_no_policy_is_a_javascript_shell(self):
        assert CV.work_order_state(
            {"firecrawl_state": "NOT_ACQUIRED", "firecrawl_outcome": "POLICY_NOT_FOUND",
             "body_chars": 1200}) == "JAVASCRIPT_SHELL"

    def test_a_heading_only_page_is_incomplete_however_good_its_evidence(self):
        """HTTP 200 clears nothing, and neither does a publication-grade
        evidence package wrapped around a heading."""
        assert CV.work_order_state(
            {"firecrawl_state": "ACQUIRED_PUBLICATION_GRADE",
             "surface_state": "HEADING_ONLY", "identity_confirmed": True}
        ) == "POLICY_SURFACE_INCOMPLETE"

    def test_an_unconfirmed_identity_is_not_reported_as_acquired(self):
        assert CV.work_order_state(
            {"firecrawl_state": "ACQUIRED_PUBLICATION_GRADE",
             "surface_state": "HYDRATED", "identity_confirmed": False}
        ) == "IDENTITY_UNCERTAIN"


class TestCompletenessIsMeasuredDifferentlyWithNoBaseline:
    def test_an_allowance_with_no_terms_is_not_a_complete_policy(self):
        """A lone pets_allowed clears every evidence gate and tells a guest
        nothing. Sixteen of the fifty-eight Milwaukee baselines look like this."""
        ok, why = CV.intrinsic_completeness({"pets_allowed": True}, "HYDRATED")
        assert ok is False
        assert "tells a guest nothing" in why

    def test_an_allowance_with_a_fee_is_complete(self):
        ok, _ = CV.intrinsic_completeness(
            {"pets_allowed": True, "pet_fee": 3000, "fee_basis": "per_night"},
            "HYDRATED")
        assert ok is True

    def test_a_captured_refusal_is_complete_on_its_own(self):
        """A no-pets policy has no further terms to state."""
        ok, why = CV.intrinsic_completeness({"pets_allowed": False}, "HYDRATED")
        assert ok is True
        assert "refusal" in why

    def test_silence_about_pets_is_never_complete(self):
        ok, _ = CV.intrinsic_completeness({"pet_fee": 3000}, "HYDRATED")
        assert ok is False

    def test_an_unhydrated_surface_is_never_complete(self):
        for surface in ("HEADING_ONLY", "ABSENT", "CONTAINER_PRESENT_NO_TEXT"):
            ok, _ = CV.intrinsic_completeness(
                {"pets_allowed": True, "pet_fee": 3000}, surface)
            assert ok is False, surface

    def test_the_basis_is_always_named_so_the_two_cannot_be_confused(self):
        compared = CV.measure_completeness(
            {"surface_state": "HYDRATED", "complete": True,
             "comparison": {"counts": {}, "structured_mismatches": {}}},
            {"comparable": True})
        intrinsic = CV.measure_completeness(
            {"surface_state": "HYDRATED",
             "firecrawl_extraction": {"pets_allowed": False}},
            {"comparable": False})
        assert compared["basis"] == "COMPARED_TO_BRIGHT_DATA"
        assert intrinsic["basis"] == "NO_BASELINE_INTRINSIC"

    def test_a_no_baseline_row_cannot_borrow_the_comparison_verdict(self):
        """With no baseline there is no MISSING to count, so the comparison
        rule would pass trivially on an empty extraction."""
        out = CV.measure_completeness(
            {"surface_state": "HYDRATED", "complete": True,
             "firecrawl_extraction": {}}, {"comparable": False})
        assert out["complete"] is False


class TestThisBenchmarkIsWhatEventuallyPromotedIt:
    """When this file was written, measuring Firecrawl had deliberately NOT
    routed it, and these tests asserted so. PTF-CHOICE-FIRECRAWL-ROUTE-
    APPLICATION-006 then applied the change on the strength of this very
    measurement plus PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005.

    The principle the class was written to protect is intact and is what is
    asserted now: a provider reaches a route through a measurement, and only
    the lane it was measured on."""

    def test_firecrawl_is_routable_on_the_lane_this_benchmark_measured(self):
        assert "firecrawl" in PROVIDERS.all_ids()
        assert "firecrawl" not in PROVIDERS.KNOWN_FUTURE_PROVIDERS

    def test_choice_now_leads_with_firecrawl_and_keeps_the_unlocker_behind_it(self):
        for url in ("https://www.choicehotels.com/wisconsin/milwaukee/econo-lodge-hotels/wi423",
                    "https://www.choicehotels.com/wisconsin/milwaukee/cambria-hotels/wi297"):
            route = REGISTRY.resolve(brand="CHOICE", url=url)
            assert route.provider == "firecrawl"
            assert "brightdata_web_unlocker" in route.fallback_providers
            assert "brightdata_browser" in route.forbidden_providers

    def test_no_unmeasured_provider_reached_the_route_table(self):
        """Spider was benchmarked on this same corpus and reached 7 of 25. It
        is still absent, which is the point: measurement is the gate, not
        having an adapter."""
        text = ROUTES_PATH.read_text(encoding="utf-8")
        assert "spider" not in text


class TestTheCommittedChoiceValidation:
    def _doc(self):
        if not VALIDATION_REPORT.is_file():
            pytest.skip("choice validation not run in this worktree")
        return json.loads(VALIDATION_REPORT.read_text(encoding="utf-8-sig"))

    def test_the_combined_sample_is_fifteen(self):
        d = self._doc()["sample_derivation"]
        assert d["choice_total_existing_benchmark"] == 3
        assert d["choice_new_rows"] == 12
        assert d["choice_combined_total"] == 15
        assert d["duplicate_identity_keys"] == []

    def test_no_identity_key_appears_twice_in_the_combined_items(self):
        keys = [r["identity_key"] for r in self._doc()["items"]]
        assert len(keys) == 15
        assert len(set(keys)) == 15

    def test_zero_wrong_facts_across_the_combined_sample(self):
        c = self._doc()["combined"]
        assert c["structured_mismatch"] == 0
        assert c["false_pets_allowed"] == 0
        assert c["false_no_pets"] == 0
        assert c["false_fee"] == 0
        assert c["false_weight"] == 0
        assert c["false_species"] == 0

    def test_agreement_is_only_claimed_where_a_baseline_exists(self):
        """The rows with no incumbent answer must never be counted as
        confirmations. Comparisons can only be fewer than the comparable rows,
        never more: a comparable property that this lane failed to acquire has
        nothing to compare either."""
        doc = self._doc()
        compared = doc["combined"]["compared_against_bright_data"]
        assert compared <= doc["baseline_availability"]["comparable"]
        assert compared < 15

    def test_a_no_baseline_row_never_scores_as_extra(self):
        """Against an absent baseline every field found scores EXTRA, which
        would read as 'the incumbent fetched this page and missed nine fields'
        when the incumbent never got the page at all."""
        doc = self._doc()
        assert doc["combined"]["extra"] == 0
        assert doc["combined"]["acquired_with_no_baseline"] > 0
        assert doc["combined"]["fields_on_rows_with_no_baseline"] > 0

    def test_a_refusal_carrying_pet_terms_is_surfaced_not_published(self):
        """A property that refuses pets cannot also cap them at 40 pounds.
        No baseline exists for these rows, so the section-6 detectors -- which
        compare two answers -- cannot see it. This check needs only one."""
        ic = self._doc()["internal_consistency"]
        assert "refusal_records_carrying_pet_terms" in ic
        assert "HELD from publication" in ic["consequence"]
        for key, fields in ic["refusal_records_carrying_pet_terms"].items():
            assert fields, key

    def test_the_earlier_coverage_claim_is_retracted_in_the_artifact(self):
        """HL-003 published 'Firecrawl MATCHES Choice coverage; it does not
        extend it.' That is now false and the correction has to live in the
        record, not only in a message."""
        ci = self._doc()["country_inn_radisson"]
        assert "RETRACTED" in ci["correction"]
        assert ci["why_the_earlier_result_differed"]

    def test_coverage_gained_is_separated_from_usable_policy_gained(self):
        cov = self._doc()["coverage"]
        assert len(cov["new_coverage_that_is_a_complete_policy"]) <= \
            cov["new_coverage_count"]

    def test_no_credit_endpoint_reading_is_fabricated(self):
        """A carried-forward delta must not be presented as two readings."""
        cost = self._doc()["cost"]
        if cost["credits_before"] is None:
            assert cost["credits_after"] is None
        assert cost["new_run_credits"] is not None

    def test_authority_and_routes_untouched(self):
        doc = self._doc()
        assert doc["authority_written"] is False
        assert doc["routes_changed"] is False
        assert doc["firecrawl_registered"] is False

    def test_no_dollar_figure_was_invented(self):
        assert "not derivable" in self._doc()["cost"]["dollar_conversion"]

    def test_the_country_inn_finding_is_reported_separately(self):
        ci = self._doc()["country_inn_radisson"]
        assert ci["known_difficult_total"] == 3
        assert ci["acquired"] + ci["failed"] == ci["known_difficult_total"]
        assert "ACCESS_DENIED" in ci["incumbent_result"]

    def test_bright_data_coverage_is_stated_over_all_fifteen(self):
        """Comparing only the rows the incumbent reached would hide four
        ACCESS_DENIED and four the budget cap never got to."""
        ref = self._doc()["bright_data_reference"]
        assert ref["total_in_queue"] == 15
        assert (ref["acquired_publication_grade"]
                + ref["technical_fallback_required"]
                + ref["not_attempted_budget_stopped"]) == 15

    def test_every_row_carries_a_state_from_the_named_set(self):
        for row in self._doc()["items"]:
            assert row["work_order_state"] in CV.WO_STATES, row["identity_key"]

    def test_unclassified_fields_would_have_been_surfaced(self):
        for row in self._doc()["items"]:
            comparison = row.get("comparison") or {}
            assert not comparison.get("unclassified_fields_treated_as_structured")


class TestTheChoiceRouteProposalIsStillAProposal:
    def _doc(self):
        if not PROPOSAL.is_file():
            pytest.skip("no choice proposal in this worktree")
        return json.loads(PROPOSAL.read_text(encoding="utf-8-sig"))

    def test_it_is_marked_not_applied(self):
        assert self._doc()["status"] == "PROPOSED_NOT_APPLIED"

    def test_it_names_what_the_measurement_does_not_support(self):
        """A proposal that only lists upside is a pitch."""
        doc = self._doc()
        assert doc["what_the_measurement_does_NOT_support"]

    def test_it_flags_the_tests_that_would_have_to_change(self):
        step = self._doc()["proposed_change"]["step_1_register_the_provider"]
        assert "test_acquisition_router" in step["also_required"]

    def test_it_keeps_the_forbidden_provider_rule(self):
        """Fourteen refusals in fifteen attempts bought that rule and nothing
        measured here touches it."""
        after = self._doc()["proposed_change"]["step_2_route_choice"]["after"]
        assert "brightdata_browser" in after["forbidden_providers"]

    def test_it_keeps_the_incumbent_somewhere_in_the_lane(self):
        after = self._doc()["proposed_change"]["step_2_route_choice"]["after"]
        assert "brightdata_web_unlocker" in (
            [after["provider"]] + list(after["fallback_providers"]))

"""PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005 -- retry, matrix and route proposal.

The route proposal in this work order is the first one marked READY_TO_APPLY
rather than merely PROPOSED, so the things that keep it honest are worth
asserting rather than trusting:

  * it has not been applied -- routes.json still sends Choice to the Web
    Unlocker and Firecrawl is still not a registered provider;
  * every condition it claims is met is a claim the matrix can be checked
    against, not prose;
  * the matrix does not double-count a property that appears in more than one
    of the three source artifacts, and does not quietly gain a complete policy
    when the reader fix took one away.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import choice_coverage_matrix_005 as MATRIX
from scripts.pettripfinder.acquisition import choice_failure_retry_005 as RETRY
from scripts.pettripfinder.acquisition import choice_reader_rederive_005 as RD
from scripts.pettripfinder.acquisition import firecrawl_choice_validation_004 as CV
from scripts.pettripfinder.acquisition import firecrawl_hard_lanes_003 as HARD
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
MATRIX_REPORT = REPORTS / "ptf_choice_coverage_matrix_005.json"
RETRY_REPORT = REPORTS / "ptf_choice_failure_retry_005.json"
ROUTE_CHANGE = REPORTS / "ptf_choice_route_change_005.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")


class TestTheRetryUsedTheProvenPathAndTheRightOrder:
    def test_it_calls_the_same_acquire_as_every_earlier_run(self):
        assert RETRY.HL.acquire is HARD.acquire

    def test_the_attempt_budget_is_three_and_the_default_is_still_two(self):
        """Three because two is where both failures landed. The default must
        not move, or PTF-FIRECRAWL-HARD-LANES-003 stops reproducing."""
        assert RETRY.FIRECRAWL_ATTEMPTS == 3
        assert inspect.signature(HARD.acquire).parameters["max_attempts"].default == 2

    def test_the_unlocker_is_probed_once_and_only_as_a_fallback(self):
        assert RETRY.UNLOCKER_ATTEMPTS == 1

    def test_the_failures_are_read_from_the_committed_report_not_listed(self):
        """A hand-typed list could quietly drop a failure and report a
        cleaner result than the run produced."""
        source = inspect.getsource(RETRY.open_failures)
        assert "VALIDATION_REPORT" in source
        assert "clarion" not in source.lower()
        assert "sleep inn" not in source.lower()


class TestTheReDerivationSpentNothing:
    def test_it_reads_persisted_artifacts_and_makes_no_request(self):
        source = inspect.getsource(RD)
        assert "urllib" not in source
        assert "capture_property" not in source

    def test_the_general_rule_is_not_keyed_to_a_property(self):
        """The fix belongs in the reader, for every Choice page and every
        brand. A name-matched patch would pass this record and leave the next
        one broken."""
        from scripts.pettripfinder.brightdata import policy_reading as PR
        source = inspect.getsource(PR)
        assert "country inn" not in source.lower()
        assert "milwaukee" not in source.lower()
        assert "clarion" not in source.lower()


class TestTheCommittedRetryResult:
    def _doc(self):
        if not RETRY_REPORT.is_file():
            pytest.skip("retry not run in this worktree")
        return json.loads(RETRY_REPORT.read_text(encoding="utf-8-sig"))

    def test_routes_and_authority_were_not_touched(self):
        doc = self._doc()
        assert doc["routes_changed"] is False
        assert doc["authority_written"] is False

    def test_the_unlocker_was_only_probed_where_firecrawl_failed(self):
        for row in self._doc()["items"]:
            acquired = str(row.get("firecrawl_state", "")).startswith("ACQUIRED")
            if acquired:
                assert "unlocker_fallback" not in row, row["identity_key"]

    def test_no_dollar_figure_was_invented(self):
        assert "not derivable" in self._doc()["cost"]["dollar_conversion"]


class TestTheFinalMatrix:
    def _doc(self):
        if not MATRIX_REPORT.is_file():
            pytest.skip("matrix not built in this worktree")
        return json.loads(MATRIX_REPORT.read_text(encoding="utf-8-sig"))

    def test_every_property_appears_exactly_once(self):
        """Three artifacts overlap by design; a fold that double-counted would
        inflate the denominator and the numerator together and look fine."""
        keys = [r["identity_key"] for r in self._doc()["items"]]
        assert len(keys) == 15
        assert len(set(keys)) == 15

    def test_the_totals_are_internally_consistent(self):
        d = self._doc()
        assert d["total"] == len(d["items"])
        assert d["combined_firecrawl_then_unlocker"] == (
            d["firecrawl_acquired"] + d["web_unlocker_unique_recoveries"])
        assert d["publication_grade"] <= d["firecrawl_acquired"]
        assert d["intrinsically_complete"] <= d["publication_grade"]

    def test_the_reader_fix_is_allowed_to_have_cost_a_complete_policy(self):
        """It took one away, and the matrix must show fewer complete policies
        than 15 for that reason. A fold that silently kept the old value would
        be the flattering direction."""
        d = self._doc()
        assert d["internal_contradiction"] >= 1
        assert d["intrinsically_complete"] < d["total"]

    def test_no_refusal_survives_carrying_pet_terms(self):
        """Re-checked on the FINAL extractions rather than trusted from an
        earlier stage, because the fold rewrites extractions."""
        assert self._doc()["residual_refusals_carrying_pet_terms"] == {}

    def test_zero_wrong_facts(self):
        d = self._doc()
        assert d["structured_mismatch"] == 0
        for field in ("false_pets_allowed", "false_no_pets", "false_fee",
                      "false_weight", "false_species"):
            assert d[field] == 0, field

    def test_agreement_is_only_counted_where_a_baseline_exists(self):
        d = self._doc()
        assert d["compared_against_bright_data"] < d["total"]
        assert d["extra"] == 0

    def test_the_untested_fallback_is_reported_as_untested_not_as_zero(self):
        """'Not needed on this sample' and 'adds nothing' are different
        claims, and only one of them was measured."""
        value = self._doc()["web_unlocker_fallback_value"]
        assert value.startswith("UNTESTED_ON_THIS_SAMPLE")

    def test_the_unfixed_reader_gap_is_recorded_not_buried(self):
        defects = self._doc()["known_remaining_defects"]
        assert defects
        gap = defects[0]
        assert gap["caused_by_this_work_order"] is False
        assert "NOT FIXED" in gap["action"]


class TestTheRouteChangeIsReadyButNotApplied:
    def _doc(self):
        if not ROUTE_CHANGE.is_file():
            pytest.skip("no route change in this worktree")
        return json.loads(ROUTE_CHANGE.read_text(encoding="utf-8-sig"))

    def test_it_is_ready_and_explicitly_not_applied(self):
        doc = self._doc()
        assert doc["status"] == "PROPOSED_READY_TO_APPLY"
        assert doc["applied"] is False

    def test_the_live_route_table_is_untouched_by_it(self):
        """The whole point of a proposal is that it has not happened yet."""
        for url in ("https://www.choicehotels.com/wisconsin/milwaukee/clarion-hotels/wi519",
                    "https://www.choicehotels.com/wisconsin/milwaukee/sleep-inn-hotels/wi186"):
            assert REGISTRY.resolve(brand="CHOICE", url=url).provider == \
                "brightdata_web_unlocker"
        assert "firecrawl" not in PROVIDERS.all_ids()
        assert "firecrawl" in PROVIDERS.KNOWN_FUTURE_PROVIDERS
        text = ROUTES_PATH.read_text(encoding="utf-8")
        assert "firecrawl" not in text and "spider" not in text

    def test_every_decision_condition_is_claimed_met_with_evidence(self):
        conditions = self._doc()["decision_conditions"]
        assert len(conditions) == 5
        for name, cond in conditions.items():
            assert cond["met"] is True, name
            assert cond["evidence"].strip(), name

    def test_the_attempt_budget_matches_what_was_measured(self):
        step = self._doc()["proposed_change"]["step_2_route_choice"]
        assert step["max_firecrawl_attempts"] == RETRY.FIRECRAWL_ATTEMPTS
        assert step["after"]["max_attempts_per_provider"] == RETRY.FIRECRAWL_ATTEMPTS

    def test_the_forbidden_provider_rule_survives(self):
        after = self._doc()["proposed_change"]["step_2_route_choice"]["after"]
        assert "brightdata_browser" in after["forbidden_providers"]

    def test_the_incumbent_stays_in_the_lane(self):
        after = self._doc()["proposed_change"]["step_2_route_choice"]["after"]
        assert "brightdata_web_unlocker" in after["fallback_providers"]

    def test_it_says_why_the_weaker_option_was_rejected(self):
        """A decision that only argues for itself is a preference."""
        assert self._doc()["why_not_B"].strip()

    def test_it_carries_its_known_failures_forward(self):
        doc = self._doc()
        assert doc["known_remaining_failures_and_defects"]
        assert doc["before_applying"]

    def test_it_flags_the_tests_that_would_have_to_change(self):
        step = self._doc()["proposed_change"]["step_1_register_the_provider"]
        assert "test_acquisition_router" in step["also_required"]

    def test_no_dollar_comparison_is_asserted(self):
        assert "not asserted" in self._doc()["cost_and_latency_rationale"][
            "dollar_comparison"]

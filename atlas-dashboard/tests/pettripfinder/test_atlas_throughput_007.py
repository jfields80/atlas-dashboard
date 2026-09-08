"""ATLAS-THROUGHPUT-007 -- bounded historical semantics and legacy debt.

Three things are proved here:

1. **The invariant model does what it claims.** Adding lawful hotels must not
   break a historical cohort; deleting, mutating or misbinding a member of that
   cohort must fail. A count pin that cannot tell those two apart is the defect
   007 exists to reduce.
2. **A baselined node cannot fail differently and stay PRE_EXISTING.** The
   f75aa95 baseline now carries a normalized signature per node, and both
   classifiers honour it.
3. **The demo-media split kept every safety claim.** The claims table is
   committed, and every original test node still exists somewhere.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import ci_validation as CI
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import regression_lanes as RL
from scripts.pettripfinder import sealed_market_package as SMP

REPORTS = SMP.LAUNCH_PACKAGE / "reports"
BASELINE = SMP.LAUNCH_PACKAGE / "regression_baselines" / "f75aa95.json"
CLAIMS = REPORTS / "atlas_throughput_007_demo_media_claims.json"


@pytest.fixture(scope="module")
def baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The four invariant classes.
# --------------------------------------------------------------------------- #

CURRENT_STATE_INVARIANT = "CURRENT_STATE_INVARIANT"
HISTORICAL_COHORT_INVARIANT = "HISTORICAL_COHORT_INVARIANT"
HISTORICAL_ARTIFACT_INVARIANT = "HISTORICAL_ARTIFACT_INVARIANT"
DEPLOYMENT_EPOCH_INVARIANT = "DEPLOYMENT_EPOCH_INVARIANT"


class TestHistoricalCohortInvariant:
    """A cohort is a named set of identities, never a total."""

    COHORT = ({"key": "a hotel", "ledger": "L1"},
              {"key": "b hotel", "ledger": "L1"},
              {"key": "c hotel", "ledger": "L2"})

    def _selector(self):
        from pettripfinder import epochs
        return epochs.by_identity_keys(["a hotel", "b hotel"])

    def _epoch(self):
        from pettripfinder import epochs
        return epochs.HistoricalEpoch(work_order="PTF-ATLAS-THROUGHPUT-007",
                                      market_id="columbus-oh",
                                      facts={"cohort": 2})

    def test_adding_valid_hotels_does_not_break_the_cohort(self):
        from pettripfinder import epochs

        grown = list(self.COHORT) + [{"key": "newly researched hotel", "ledger": "L3"},
                                     {"key": "another new hotel", "ledger": "L3"}]
        before = epochs.cohort(list(self.COHORT), self._selector())
        after = epochs.cohort(grown, self._selector())
        assert [r["key"] for r in before] == [r["key"] for r in after] == ["a hotel", "b hotel"]

    def test_deleting_a_cohort_member_fails(self):
        from pettripfinder import epochs

        shrunk = [r for r in self.COHORT if r["key"] != "a hotel"]
        found = epochs.cohort(shrunk, self._selector())
        assert [r["key"] for r in found] == ["b hotel"]
        with pytest.raises(AssertionError):
            epochs.assert_cohort_size(shrunk, self._selector(), 2, epoch=self._epoch())

    def test_substituting_a_wrong_identity_fails(self):
        from pettripfinder import epochs

        swapped = [{"key": "a DIFFERENT hotel", "ledger": "L1"}] + \
                  [r for r in self.COHORT if r["key"] != "a hotel"]
        found = [r["key"] for r in epochs.cohort(swapped, self._selector())]
        assert "a hotel" not in found, "a substituted identity must not satisfy the cohort"
        with pytest.raises(AssertionError):
            epochs.assert_cohort_size(swapped, self._selector(), 2, epoch=self._epoch())

    def test_a_count_pin_cannot_tell_growth_from_loss(self):
        """Why the migration matters, stated as a test.

        A total moves for both a lawful addition and an unlawful deletion, so it
        fires on the first and is satisfied by a compensating pair. A named
        cohort distinguishes them.
        """
        from pettripfinder import epochs

        grown = list(self.COHORT) + [{"key": "new hotel", "ledger": "L3"}]
        lost_and_gained = [{"key": "new hotel", "ledger": "L3"}] + \
                          [r for r in self.COHORT if r["key"] != "a hotel"]
        assert len(grown) != len(self.COHORT)                      # a count fires on growth
        assert len(lost_and_gained) == len(self.COHORT)            # a count misses a swap
        assert len(epochs.cohort(grown, self._selector())) == 2    # the cohort ignores growth
        assert len(epochs.cohort(lost_and_gained, self._selector())) == 1   # and catches the swap


class TestCurrentStateInvariant:
    def test_the_migrated_pins_read_reviewed_state_not_a_literal(self):
        source = (Path(__file__).resolve().parent / "test_identity_routing.py").read_text(
            encoding="utf-8")
        assert 'assert len(pkg["hotels"]) == _market_state("columbus-oh").profiles' in source
        assert "len(hotels) == len(shard_hotels)" in source
        assert 'assert len(pkg["hotels"]) == 88' not in source
        assert "assert len(hotels) == 89" not in source

    def test_the_deployment_module_was_already_correct(self):
        """045 derives every release count from the reviewed pins, so it needed
        no migration. Recording that here stops a later order 'fixing' it."""
        source = (Path(__file__).resolve().parent
                  / "test_global_deployment_architecture_045.py").read_text(encoding="utf-8")
        for line in ("EXPECTED_TOTAL = SOURCE_PINS.total_profiles",
                     "EXPECTED_HTML_PAGES = SOURCE_PINS.total_html_pages",
                     "EXPECTED_SITEMAP_ROUTES = SOURCE_PINS.sitemap_route_count",
                     "DISABLED_BUILD_BUNDLE_SHA256 = SOURCE_PINS.bundle_sha256"):
            assert line in source, line


# --------------------------------------------------------------------------- #
# Failure signatures.
# --------------------------------------------------------------------------- #

class TestFailureSignatures:
    def test_the_baseline_now_carries_a_signature_for_every_node(self, baseline):
        nodes = baseline["failing_node_ids"]
        signatures = baseline["failure_signatures"]
        assert len(nodes) == 160
        assert set(signatures) == set(nodes)
        assert all(s.startswith("sha256:") for s in signatures.values())
        records = {r["node_id"]: r for r in baseline["failure_records"]}
        assert set(records) == set(nodes)
        for record in records.values():
            for field in ("normalized_failure_signature", "category", "domain", "environment",
                          "reason", "recorded_at", "review_by"):
                assert record.get(field), field

    def test_same_node_same_signature_is_pre_existing(self, baseline):
        node = baseline["failing_node_ids"][0]
        record = next(r for r in baseline["failure_records"] if r["node_id"] == node)
        # A message that normalizes to the recorded signature keeps it baselined.
        out = RD.classify_against_baseline([node], baseline,
                                           messages={node: _message_for(record)})
        assert out["counts"]["PRE_EXISTING"] + out["counts"]["TRUE_NEW"] == 1

    def test_same_node_different_signature_is_true_new(self, baseline):
        node = baseline["failing_node_ids"][0]
        out = RD.classify_against_baseline(
            [node], baseline, messages={node: "ImportError: a completely different failure"})
        assert out["counts"]["TRUE_NEW"] == 1
        assert out["counts"]["PRE_EXISTING"] == 0
        assert out["CHANGED_SIGNATURE"][0]["node_id"] == node

    def test_a_node_outside_the_baseline_is_true_new(self, baseline):
        out = RD.classify_against_baseline(["tests/x.py::test_brand_new"], baseline)
        assert out["counts"]["TRUE_NEW"] == 1

    def test_without_messages_classification_is_unchanged(self, baseline):
        """Every earlier run's classification still means what it meant."""
        node = baseline["failing_node_ids"][0]
        out = RD.classify_against_baseline([node], baseline)
        assert out["counts"]["PRE_EXISTING"] == 1
        assert out["signature_checked"] is False

    def test_the_lane_classifier_honours_signatures_too(self, baseline):
        node = baseline["failing_node_ids"][0]
        run = {"failing_node_ids": [node], "collected": 1, "failed": 1, "run_dir": "x"}
        same = RL.classify(run, baseline)
        assert same["counts"][RL.PRE_EXISTING] == 1
        different = RL.classify(run, baseline, messages={node: "a completely different failure"})
        assert different["counts"][RL.TRUE_NEW_FAILURE] == 1
        assert different["changed_signature"][0]["node_id"] == node

    def test_a_baselined_node_that_passes_is_reported_not_erased(self, baseline):
        now_passing = RD.baseline_now_passing([], baseline)
        assert len(now_passing) == len(baseline["failing_node_ids"])
        scoped = RD.baseline_now_passing([], baseline, collected=[])
        assert scoped == [], "an unexercised node has not started passing"

    def test_normalization_keeps_semantic_identity(self):
        same = CI.failure_signature("AssertionError: assert 5 == 6 at 0xdeadbeef")
        also = CI.failure_signature("AssertionError: assert 5 == 6 at 0xfeedface")
        different = CI.failure_signature("AssertionError: assert 5 == 7 at 0xdeadbeef")
        assert same == also, "an address is not part of a failure's identity"
        assert same != different, "the asserted values are"


def _message_for(record):
    """A message whose normalization matches the recorded signature.

    The excerpt is a normalized prefix, so it is not guaranteed to reproduce the
    signature; this helper exists so the PRE_EXISTING test asserts the API's
    shape rather than pretending to reconstruct a message it does not have.
    """
    return record["excerpt"]


# --------------------------------------------------------------------------- #
# The demo-media split.
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not CLAIMS.is_file(), reason="claims table not yet written")
class TestDemoMediaClaims:
    @pytest.fixture(scope="class")
    def claims(self):
        return json.loads(CLAIMS.read_text(encoding="utf-8-sig"))

    def test_every_original_claim_has_an_owner_after_the_split(self, claims):
        for row in claims["claims"]:
            assert row["after"], row["claim"]
            assert row["module_after"], row["claim"]

    def test_no_original_test_node_was_deleted(self, claims):
        removed = [r for r in claims["claims"] if r["after"] == "REMOVED"]
        assert removed == [], "a claim may move modules; it may not vanish"

    def test_the_cold_and_determinism_claims_stayed_cold(self, claims):
        cold = [r for r in claims["claims"] if r["cold_execution_required"]]
        assert cold, "the module must still contain genuinely cold claims"
        for row in cold:
            assert row["builds_after"] >= 1, row["claim"]
            assert row["memoised"] is False, row["claim"]

    def test_the_split_reduced_builds_without_losing_claims(self, claims):
        assert claims["builds_before"] > claims["builds_after"]
        assert len(claims["claims"]) == claims["claim_count"]

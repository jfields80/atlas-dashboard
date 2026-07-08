"""Tests for the deterministic Website Intelligence scoring engine.

Covers: weight validation, category score validation, weighted overall
computation, grade band mapping, launch readiness mapping, stable IDs,
and full-pass determinism.
"""

import pytest

from engines.website_intelligence.constants import (
    CATEGORY_COMMERCIAL,
    CATEGORY_CONTENT,
    CATEGORY_DIRECTORY,
    CATEGORY_MONETIZATION,
    CATEGORY_NAVIGATION,
    CATEGORY_SEO,
    CATEGORY_UX,
    CATEGORY_WEIGHTS,
    ENGINE_NAME,
    ENGINE_VERSION,
    READINESS_NEEDS_WORK,
    READINESS_NOT_READY,
    READINESS_READY,
    READINESS_REVIEW,
    SCORE_CATEGORIES,
)
from engines.website_intelligence.scoring_engine import (
    ScoringEngine,
    ScoringResult,
    compute_overall_score,
    grade_for_score,
    launch_readiness_for_score,
    round_score,
    stable_id,
    validate_category_scores,
    validate_weights,
)


def make_scores(value=80.0, **overrides):
    scores = {category: value for category in SCORE_CATEGORIES}
    scores.update(overrides)
    return scores


# ---------------------------------------------------------------------------
# Constants integrity
# ---------------------------------------------------------------------------


class TestConstants:
    def test_weights_cover_exactly_the_score_categories(self):
        assert set(CATEGORY_WEIGHTS.keys()) == set(SCORE_CATEGORIES)

    def test_weights_sum_to_one(self):
        assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) < 1e-9

    def test_specified_weights(self):
        assert CATEGORY_WEIGHTS[CATEGORY_SEO] == 0.15
        assert CATEGORY_WEIGHTS[CATEGORY_NAVIGATION] == 0.15
        assert CATEGORY_WEIGHTS[CATEGORY_CONTENT] == 0.15
        assert CATEGORY_WEIGHTS[CATEGORY_DIRECTORY] == 0.20
        assert CATEGORY_WEIGHTS[CATEGORY_COMMERCIAL] == 0.15
        assert CATEGORY_WEIGHTS[CATEGORY_MONETIZATION] == 0.10
        assert CATEGORY_WEIGHTS[CATEGORY_UX] == 0.10

    def test_seven_categories_in_stable_order(self):
        assert SCORE_CATEGORIES == (
            CATEGORY_SEO,
            CATEGORY_NAVIGATION,
            CATEGORY_CONTENT,
            CATEGORY_DIRECTORY,
            CATEGORY_COMMERCIAL,
            CATEGORY_MONETIZATION,
            CATEGORY_UX,
        )


# ---------------------------------------------------------------------------
# Weight validation
# ---------------------------------------------------------------------------


class TestWeightValidation:
    def test_default_weights_are_valid(self):
        validate_weights()  # must not raise

    def test_weights_not_summing_to_one_rejected(self):
        bad = dict(CATEGORY_WEIGHTS)
        bad[CATEGORY_SEO] = 0.30  # sum becomes 1.15
        with pytest.raises(ValueError):
            validate_weights(bad)

    def test_missing_category_rejected(self):
        bad = dict(CATEGORY_WEIGHTS)
        del bad[CATEGORY_UX]
        with pytest.raises(ValueError):
            validate_weights(bad)

    def test_unexpected_category_rejected(self):
        bad = dict(CATEGORY_WEIGHTS)
        bad["performance"] = 0.0
        with pytest.raises(ValueError):
            validate_weights(bad)

    def test_zero_weight_rejected(self):
        bad = dict(CATEGORY_WEIGHTS)
        bad[CATEGORY_UX] = 0.0
        bad[CATEGORY_MONETIZATION] = 0.20
        with pytest.raises(ValueError):
            validate_weights(bad)

    def test_negative_weight_rejected(self):
        bad = dict(CATEGORY_WEIGHTS)
        bad[CATEGORY_UX] = -0.10
        bad[CATEGORY_MONETIZATION] = 0.30
        with pytest.raises(ValueError):
            validate_weights(bad)

    def test_non_numeric_weight_rejected(self):
        bad = dict(CATEGORY_WEIGHTS)
        bad[CATEGORY_UX] = "0.10"
        with pytest.raises(ValueError):
            validate_weights(bad)


# ---------------------------------------------------------------------------
# Category score validation
# ---------------------------------------------------------------------------


class TestCategoryScoreValidation:
    def test_valid_scores_pass(self):
        validate_category_scores(make_scores())  # must not raise

    def test_missing_category_rejected(self):
        scores = make_scores()
        del scores[CATEGORY_DIRECTORY]
        with pytest.raises(ValueError):
            validate_category_scores(scores)

    def test_unexpected_category_rejected(self):
        with pytest.raises(ValueError):
            validate_category_scores(make_scores(performance=90.0))

    def test_score_below_range_rejected(self):
        with pytest.raises(ValueError):
            validate_category_scores(make_scores(**{CATEGORY_SEO: -1.0}))

    def test_score_above_range_rejected(self):
        with pytest.raises(ValueError):
            validate_category_scores(make_scores(**{CATEGORY_SEO: 100.5}))

    def test_non_numeric_score_rejected(self):
        with pytest.raises(ValueError):
            validate_category_scores(make_scores(**{CATEGORY_SEO: "90"}))

    def test_boundary_scores_accepted(self):
        validate_category_scores(make_scores(0.0))
        validate_category_scores(make_scores(100.0))


# ---------------------------------------------------------------------------
# Overall score computation
# ---------------------------------------------------------------------------


class TestOverallScore:
    def test_all_hundred_gives_hundred(self):
        assert compute_overall_score(make_scores(100.0)) == 100.0

    def test_all_zero_gives_zero(self):
        assert compute_overall_score(make_scores(0.0)) == 0.0

    def test_uniform_scores_give_that_score(self):
        assert compute_overall_score(make_scores(80.0)) == 80.0

    def test_known_mixed_case(self):
        scores = {
            CATEGORY_SEO: 85.0,          # * 0.15 = 12.75
            CATEGORY_NAVIGATION: 90.0,   # * 0.15 = 13.50
            CATEGORY_CONTENT: 80.0,      # * 0.15 = 12.00
            CATEGORY_DIRECTORY: 88.0,    # * 0.20 = 17.60
            CATEGORY_COMMERCIAL: 75.0,   # * 0.15 = 11.25
            CATEGORY_MONETIZATION: 60.0, # * 0.10 =  6.00
            CATEGORY_UX: 92.0,           # * 0.10 =  9.20
        }
        assert compute_overall_score(scores) == 82.3

    def test_directory_weight_dominates_monetization(self):
        # Same delta applied to directory (0.20) vs monetization (0.10)
        base = make_scores(50.0)
        directory_boosted = compute_overall_score(
            make_scores(50.0, **{CATEGORY_DIRECTORY: 100.0})
        )
        monetization_boosted = compute_overall_score(
            make_scores(50.0, **{CATEGORY_MONETIZATION: 100.0})
        )
        assert compute_overall_score(base) == 50.0
        assert directory_boosted == 60.0
        assert monetization_boosted == 55.0
        assert directory_boosted > monetization_boosted

    def test_result_is_rounded_to_precision(self):
        overall = compute_overall_score(make_scores(33.333333))
        assert overall == round(overall, 2)

    def test_invalid_scores_propagate_error(self):
        with pytest.raises(ValueError):
            compute_overall_score(make_scores(**{CATEGORY_SEO: 101.0}))

    def test_invalid_weights_propagate_error(self):
        bad = dict(CATEGORY_WEIGHTS)
        bad[CATEGORY_SEO] = 0.50
        with pytest.raises(ValueError):
            compute_overall_score(make_scores(), bad)


# ---------------------------------------------------------------------------
# Grade mapping
# ---------------------------------------------------------------------------


class TestGradeMapping:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (100.0, "A"),
            (95.0, "A"),
            (90.0, "A"),
            (89.99, "B"),
            (85.0, "B"),
            (80.0, "B"),
            (79.99, "C"),
            (75.0, "C"),
            (70.0, "C"),
            (69.99, "D"),
            (65.0, "D"),
            (60.0, "D"),
            (59.99, "F"),
            (30.0, "F"),
            (0.0, "F"),
        ],
    )
    def test_grade_bands(self, score, expected):
        assert grade_for_score(score) == expected

    def test_out_of_range_score_rejected(self):
        with pytest.raises(ValueError):
            grade_for_score(100.01)
        with pytest.raises(ValueError):
            grade_for_score(-0.01)


# ---------------------------------------------------------------------------
# Launch readiness mapping
# ---------------------------------------------------------------------------


class TestLaunchReadinessMapping:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (100.0, READINESS_READY),
            (90.0, READINESS_READY),
            (89.99, READINESS_REVIEW),
            (80.0, READINESS_REVIEW),
            (75.0, READINESS_REVIEW),
            (74.99, READINESS_NEEDS_WORK),
            (65.0, READINESS_NEEDS_WORK),
            (60.0, READINESS_NEEDS_WORK),
            (59.99, READINESS_NOT_READY),
            (20.0, READINESS_NOT_READY),
            (0.0, READINESS_NOT_READY),
        ],
    )
    def test_readiness_bands(self, score, expected):
        assert launch_readiness_for_score(score) == expected

    def test_out_of_range_score_rejected(self):
        with pytest.raises(ValueError):
            launch_readiness_for_score(101.0)


# ---------------------------------------------------------------------------
# Stable IDs
# ---------------------------------------------------------------------------


class TestStableIds:
    def test_identical_input_identical_id(self):
        assert stable_id("find", "seo", "missing-meta") == stable_id(
            "find", "seo", "missing-meta"
        )

    def test_different_input_different_id(self):
        assert stable_id("find", "seo", "a") != stable_id("find", "seo", "b")

    def test_prefix_included(self):
        assert stable_id("wo", "x").startswith("wo-")

    def test_part_boundaries_are_unambiguous(self):
        # ("ab", "c") must not collide with ("a", "bc")
        assert stable_id("p", "ab", "c") != stable_id("p", "a", "bc")

    def test_empty_prefix_rejected(self):
        with pytest.raises(ValueError):
            stable_id("", "x")


# ---------------------------------------------------------------------------
# ScoringEngine facade + determinism
# ---------------------------------------------------------------------------


class TestScoringEngine:
    def test_score_returns_full_result(self):
        result = ScoringEngine().score(make_scores(80.0))
        assert isinstance(result, ScoringResult)
        assert result.engine_name == ENGINE_NAME
        assert result.engine_version == ENGINE_VERSION
        assert result.overall_score == 80.0
        assert result.grade == "B"
        assert result.launch_readiness == READINESS_REVIEW

    def test_category_scores_in_stable_order(self):
        result = ScoringEngine().score(make_scores(70.0))
        assert tuple(name for name, _ in result.category_scores) == SCORE_CATEGORIES

    def test_category_scores_dict_helper(self):
        result = ScoringEngine().score(make_scores(70.0))
        as_dict = result.category_scores_dict()
        assert as_dict[CATEGORY_DIRECTORY] == 70.0
        assert set(as_dict.keys()) == set(SCORE_CATEGORIES)

    def test_result_is_immutable(self):
        result = ScoringEngine().score(make_scores(70.0))
        with pytest.raises(AttributeError):
            result.overall_score = 99.0

    def test_identical_input_identical_output(self):
        scores = make_scores(
            77.7,
            **{CATEGORY_DIRECTORY: 91.25, CATEGORY_MONETIZATION: 12.5},
        )
        first = ScoringEngine().score(dict(scores))
        second = ScoringEngine().score(dict(scores))
        assert first == second

    def test_repeated_runs_are_byte_identical(self):
        scores = make_scores(63.19, **{CATEGORY_SEO: 88.88})
        results = {repr(ScoringEngine().score(dict(scores))) for _ in range(50)}
        assert len(results) == 1

    def test_key_insertion_order_does_not_affect_output(self):
        scores = make_scores(45.5)
        reversed_scores = {k: scores[k] for k in reversed(SCORE_CATEGORIES)}
        assert ScoringEngine().score(scores) == ScoringEngine().score(reversed_scores)

    def test_round_score_precision(self):
        assert round_score(82.049999) == 82.05
        assert round_score(100.0) == 100.0

    def test_ready_end_to_end(self):
        result = ScoringEngine().score(make_scores(95.0))
        assert result.grade == "A"
        assert result.launch_readiness == READINESS_READY

    def test_not_ready_end_to_end(self):
        result = ScoringEngine().score(make_scores(40.0))
        assert result.grade == "F"
        assert result.launch_readiness == READINESS_NOT_READY

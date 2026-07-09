"""
atlas/tests/test_learning_memory_metrics.py

Unit tests for the AES-008B fix: LearningMemory.success_rate() and
LearningMemory.average_error() (services/opportunity_v2/learning_memory.py).

These methods were missing entirely, which is why boot_atlas() could
not complete (see AES-008A). Formulas mirror the pre-existing inline
calculation already used in LearningEngine.adjust_weights, so these
tests also serve as a consistency check between the two.

Scope: learning_memory.py only. bootstrap.py and persistence.py are
untouched by this fix and are not exercised here.
"""

from __future__ import annotations

from services.opportunity_v2.learning_memory import LearningMemory, OpportunityOutcome


def _outcome(
    niche_name="niche",
    predicted_score=50.0,
    actual_outcome_score=50.0,
    recommendation="BUILD",
    success=True,
) -> OpportunityOutcome:
    return OpportunityOutcome(
        niche_name=niche_name,
        predicted_score=predicted_score,
        actual_outcome_score=actual_outcome_score,
        recommendation=recommendation,
        success=success,
    )


# ---------------------------------------------------------------------------
# success_rate()
# ---------------------------------------------------------------------------

def test_success_rate_returns_zero_with_no_outcomes():
    memory = LearningMemory()
    assert memory.success_rate() == 0.0


def test_success_rate_all_successful():
    memory = LearningMemory()
    memory.record_outcome(_outcome(success=True))
    memory.record_outcome(_outcome(success=True))

    assert memory.success_rate() == 1.0


def test_success_rate_all_failed():
    memory = LearningMemory()
    memory.record_outcome(_outcome(success=False))
    memory.record_outcome(_outcome(success=False))

    assert memory.success_rate() == 0.0


def test_success_rate_mixed_outcomes():
    memory = LearningMemory()
    memory.record_outcome(_outcome(success=True))
    memory.record_outcome(_outcome(success=True))
    memory.record_outcome(_outcome(success=False))
    memory.record_outcome(_outcome(success=False))

    assert memory.success_rate() == 0.5


def test_success_rate_updates_as_outcomes_are_recorded():
    memory = LearningMemory()
    memory.record_outcome(_outcome(success=True))
    assert memory.success_rate() == 1.0

    memory.record_outcome(_outcome(success=False))
    assert memory.success_rate() == 0.5


# ---------------------------------------------------------------------------
# average_error()
# ---------------------------------------------------------------------------

def test_average_error_returns_zero_with_no_outcomes():
    memory = LearningMemory()
    assert memory.average_error() == 0.0


def test_average_error_zero_when_predictions_are_exact():
    memory = LearningMemory()
    memory.record_outcome(_outcome(predicted_score=70.0, actual_outcome_score=70.0))
    memory.record_outcome(_outcome(predicted_score=40.0, actual_outcome_score=40.0))

    assert memory.average_error() == 0.0


def test_average_error_single_outcome():
    memory = LearningMemory()
    memory.record_outcome(_outcome(predicted_score=80.0, actual_outcome_score=65.0))

    assert memory.average_error() == 15.0


def test_average_error_uses_absolute_difference_regardless_of_direction():
    memory = LearningMemory()
    memory.record_outcome(_outcome(predicted_score=30.0, actual_outcome_score=50.0))  # under-predicted by 20
    memory.record_outcome(_outcome(predicted_score=90.0, actual_outcome_score=70.0))  # over-predicted by 20

    assert memory.average_error() == 20.0


def test_average_error_mean_across_multiple_outcomes():
    memory = LearningMemory()
    memory.record_outcome(_outcome(predicted_score=100.0, actual_outcome_score=90.0))  # error 10
    memory.record_outcome(_outcome(predicted_score=50.0, actual_outcome_score=30.0))   # error 20
    memory.record_outcome(_outcome(predicted_score=0.0, actual_outcome_score=30.0))    # error 30

    assert memory.average_error() == 20.0


# ---------------------------------------------------------------------------
# Regression guard: existing public API untouched
# ---------------------------------------------------------------------------

def test_existing_record_outcome_and_outcomes_still_work():
    memory = LearningMemory()
    assert memory.outcomes == []

    outcome = _outcome(niche_name="pet-friendly-travel")
    memory.record_outcome(outcome)

    assert memory.outcomes == [outcome]


def test_metrics_match_the_inline_formula_used_by_learning_engine():
    """
    LearningEngine.adjust_weights independently recomputes success_rate
    and avg_error inline (a pre-existing duplication left untouched by
    this fix, per "no refactoring" scope). This test asserts the new
    methods agree with that inline formula, since both measure the
    same thing and should never diverge.
    """
    memory = LearningMemory()
    for i in range(5):
        memory.record_outcome(
            _outcome(
                predicted_score=float(50 + i * 5),
                actual_outcome_score=float(40 + i * 5),
                success=(i % 2 == 0),
            )
        )

    inline_success_rate = sum(o.success for o in memory.outcomes) / len(memory.outcomes)
    inline_avg_error = sum(
        abs(o.predicted_score - o.actual_outcome_score) for o in memory.outcomes
    ) / len(memory.outcomes)

    assert memory.success_rate() == inline_success_rate
    assert memory.average_error() == inline_avg_error

"""
learning_memory.py — Atlas Learning System (CLEAN ARCHITECTURE FIX)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from .persistence import save_memory


@dataclass
class OpportunityOutcome:
    niche_name: str
    predicted_score: float
    actual_outcome_score: float
    recommendation: str
    success: bool


@dataclass
class LearningMemory:
    outcomes: List[OpportunityOutcome] = field(default_factory=list)

    def record_outcome(self, outcome: OpportunityOutcome):
        self.outcomes.append(outcome)


# global memory
_global_memory = LearningMemory()


def get_memory():
    return _global_memory


class LearningEngine:

    def __init__(self):
        self.weights = {
            "demand": 0.45,
            "supply": 0.35,
            "competition": 0.20
        }

    def adjust_weights(self, memory=None):

        if memory is None:
            memory = _global_memory

        if len(memory.outcomes) < 5:
            return self.weights

        success_rate = sum(o.success for o in memory.outcomes) / len(memory.outcomes)
        avg_error = sum(
            abs(o.predicted_score - o.actual_outcome_score)
            for o in memory.outcomes
        ) / len(memory.outcomes)

        if success_rate < 0.5:
            self.weights["demand"] += 0.02
            self.weights["supply"] -= 0.01

        if avg_error > 20:
            self.weights["competition"] -= 0.02

        total = sum(self.weights.values())
        for k in self.weights:
            self.weights[k] /= total

        return self.weights


_engine = LearningEngine()


def record_opportunity_result(
    niche_name: str,
    predicted_score: float,
    actual_outcome_score: float,
    recommendation: str
):

    success = actual_outcome_score >= 60

    _global_memory.record_outcome(
        OpportunityOutcome(
            niche_name=niche_name,
            predicted_score=predicted_score,
            actual_outcome_score=actual_outcome_score,
            recommendation=recommendation,
            success=success
        )
    )

    save_memory(_global_memory)


def update_learning_weights():
    return _engine.adjust_weights(_global_memory)
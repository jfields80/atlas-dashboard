"""
decision_engine.py — Atlas Final Decision Layer

This is the top-level brain:
- Consumes Scout + Demand + Market Capacity + Grounding
- Outputs final investment decision
"""

from dataclasses import dataclass


@dataclass
class OpportunityDecision:
    niche_name: str
    final_score: float
    recommendation: str
    confidence: float


class DecisionEngine:

    def evaluate(self, market_capacity_result, grounding_result=None):

        score = market_capacity_result["market_capacity_score"]

        # ─────────────────────────────────────────────
        # APPLY GROUNDING CORRECTION
        # ─────────────────────────────────────────────
        if grounding_result:
            score = (
                score * 0.7 +
                grounding_result.confidence * 0.3
            )

        # ─────────────────────────────────────────────
        # DECISION LOGIC
        # ─────────────────────────────────────────────
        if score >= 75:
            rec = "BUILD"
        elif score >= 60:
            rec = "TEST"
        elif score >= 45:
            rec = "WATCH"
        else:
            rec = "PASS"

        return OpportunityDecision(
            niche_name=market_capacity_result["niche_name"],
            final_score=round(score, 2),
            recommendation=rec,
            confidence=round(score * 0.9, 2),
        )
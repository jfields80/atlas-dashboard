"""
Scout Failure Prediction Engine

This layer does NOT run Scout.
It predicts instability BEFORE it happens using:
- health history
- memory drift
- provider instability
"""

from dataclasses import dataclass
from typing import List


@dataclass
class FailurePrediction:
    opportunity_id: int
    failure_risk: float
    provider_risk: float
    volatility_score: float
    early_warning: bool


class ScoutFailurePredictor:

    def predict(self, runs: List[dict], memory_report, opportunity_id: int) -> FailurePrediction:

        if not runs:
            return FailurePrediction(
                opportunity_id=opportunity_id,
                failure_risk=0.8,
                provider_risk=0.8,
                volatility_score=1.0,
                early_warning=True
            )

        health_scores = []
        provider_instability = 0

        for r in runs:
            findings = r.get("findings_json") or {}

            provider_summaries = findings.get("provider_summaries", [])

            for p in provider_summaries:
                if len(p.get("estimated_fields", [])) > len(p.get("verified_fields", [])):
                    provider_instability += 1

        # Memory signal
        memory_penalty = 0
        if memory_report.degradation_detected:
            memory_penalty = 0.3

        # Base failure risk
        failure_risk = min(1.0,
            (provider_instability * 0.1) + memory_penalty
        )

        provider_risk = min(1.0, provider_instability * 0.05)

        volatility_score = min(1.0,
            failure_risk + provider_risk
        )

        early_warning = volatility_score > 0.6

        return FailurePrediction(
            opportunity_id=opportunity_id,
            failure_risk=round(failure_risk, 2),
            provider_risk=round(provider_risk, 2),
            volatility_score=round(volatility_score, 2),
            early_warning=early_warning
        )
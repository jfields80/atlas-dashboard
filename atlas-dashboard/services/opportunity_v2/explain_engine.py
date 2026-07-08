"""
explain_engine.py — Atlas Decision Explainability Layer

Purpose:
- Converts raw scoring signals into human-readable reasoning
- Produces drivers, risks, and summary for Atlas Opportunity Engine
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


# ─────────────────────────────────────────────
# OUTPUT STRUCTURE
# ─────────────────────────────────────────────

@dataclass
class OpportunityExplanation:
    niche_name: str
    summary: str
    drivers: List[str]
    risks: List[str]
    confidence: float


# ─────────────────────────────────────────────
# EXPLAIN ENGINE
# ─────────────────────────────────────────────

class ExplainEngine:

    def build_explanation(
        self,
        niche_name: str,
        market_capacity_result: Dict[str, Any],
        fused_signal: Optional[Any] = None,
        decision: Optional[Any] = None
    ) -> OpportunityExplanation:

        # ─────────────────────────────
        # SAFE EXTRACTION
        # ─────────────────────────────

        demand = market_capacity_result.get("demand_score", 0)
        supply = market_capacity_result.get("supply_score", 0)
        competition = market_capacity_result.get("competition_score", 0)
        revenue = market_capacity_result.get("revenue_ceiling", 0)

        drivers = []
        risks = []

        # ─────────────────────────────
        # DRIVERS
        # ─────────────────────────────

        if demand >= 70:
            drivers.append("High market demand detected")

        if revenue >= 70:
            drivers.append("Strong revenue potential")

        if competition <= 40:
            drivers.append("Low competition environment")

        if supply >= 60:
            drivers.append("Healthy supply ecosystem")

        # ─────────────────────────────
        # RISKS
        # ─────────────────────────────

        if demand < 40:
            risks.append("Weak demand signal")

        if competition > 70:
            risks.append("High competition risk")

        if revenue < 40:
            risks.append("Low monetization potential")

        # fused signal risk (safe check)
        if fused_signal is not None:
            confidence = getattr(fused_signal, "confidence", None)
            if confidence is not None and confidence < 60:
                risks.append("Low signal confidence")

        # ─────────────────────────────
        # SUMMARY
        # ─────────────────────────────

        summary = (
            f"{niche_name} shows "
            f"{'strong' if demand >= 70 else 'moderate' if demand >= 40 else 'weak'} demand "
            f"with {'low' if competition <= 40 else 'moderate' if competition <= 70 else 'high'} competition."
        )

        # confidence estimate
        confidence = min(
            100,
            max(0, (demand * 0.4) + ((100 - competition) * 0.4) + (revenue * 0.2))
        )

        return OpportunityExplanation(
            niche_name=niche_name,
            summary=summary,
            drivers=drivers,
            risks=risks,
            confidence=confidence
        )
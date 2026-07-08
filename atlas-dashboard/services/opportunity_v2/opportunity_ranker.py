"""
opportunity_ranker.py — Atlas Opportunity Ranking Engine

Takes multiple niches and ranks them using:
- Scout (supply)
- Demand (intent)
- Market Capacity (fusion score)
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class RankedOpportunity:
    niche_name: str
    market_score: float
    demand_score: float
    supply_score: float
    revenue_ceiling: float
    recommendation: str


class OpportunityRanker:

    def __init__(self, market_capacity_engine):
        self.engine = market_capacity_engine

    def evaluate_niches(
        self,
        niches: List[str],
        dna,
        ctx,
        scout_results: Dict[str, Any] = None,
        demand_results: Dict[str, Any] = None,
    ) -> List[RankedOpportunity]:

        ranked = []

        for niche in niches:

            scout = None
            demand = None

            if scout_results:
                scout = scout_results.get(niche)

            if demand_results:
                demand = demand_results.get(niche)

            result = self.engine.evaluate(
                niche_name=niche,
                dna=dna,
                ctx=ctx,
                scout_result=scout,
                demand_result=demand
            )

            score = result["market_capacity_score"]
            demand_score = result["demand_score"]
            supply_score = result["supply_score"]
            revenue = result["estimated_revenue_ceiling"]

            if score >= 75:
                rec = "BUILD"
            elif score >= 60:
                rec = "TEST"
            elif score >= 45:
                rec = "WATCH"
            else:
                rec = "PASS"

            ranked.append(
                RankedOpportunity(
                    niche_name=niche,
                    market_score=score,
                    demand_score=demand_score,
                    supply_score=supply_score,
                    revenue_ceiling=revenue,
                    recommendation=rec,
                )
            )

        ranked.sort(key=lambda x: x.market_score, reverse=True)

        return ranked
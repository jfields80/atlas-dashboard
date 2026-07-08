"""
batch_opportunity_generator.py — Atlas Opportunity Discovery Engine

This module:
- Generates niche candidates
- Runs Scout + Demand + Market Capacity
- Feeds OpportunityRanker
- Returns top business opportunities
"""

from typing import List, Dict, Any

from .opportunity_ranker import OpportunityRanker


class BatchOpportunityGenerator:

    def __init__(self, market_capacity_engine):
        self.rankers = OpportunityRanker(market_capacity_engine)

    def generate(
        self,
        niche_candidates: List[str],
        dna,
        ctx: dict,
        scout_results: Dict[str, Any] = None,
        demand_results: Dict[str, Any] = None,
        top_k: int = 10,
    ):

        # 1. Run ranking engine
        ranked = self.rankers.evaluate_niches(
            niches=niche_candidates,
            dna=dna,
            ctx=ctx,
            scout_results=scout_results,
            demand_results=demand_results,
        )

        # 2. Trim to top K
        top = ranked[:top_k]

        # 3. Format output for UI / API
        return {
            "top_opportunities": [
                {
                    "niche": r.niche_name,
                    "score": r.market_score,
                    "demand": r.demand_score,
                    "supply": r.supply_score,
                    "revenue_ceiling": r.revenue_ceiling,
                    "recommendation": r.recommendation,
                }
                for r in top
            ],
            "total_analyzed": len(niche_candidates),
            "build_candidates": [r.niche_name for r in ranked if r.recommendation == "BUILD"],
        }
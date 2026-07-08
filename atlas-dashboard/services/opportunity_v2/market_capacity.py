"""
market_capacity.py — Atlas Single Source of Truth Scoring Engine (FINAL)

This is the ONLY module allowed to compute:
- demand_score
- supply_score
- competition_score
- final_market_capacity_score

It now includes:
- Demand Intelligence
- Scout Intelligence
- Grounding Layer
- Learning Weight Adaptation (SELF-IMPROVING SYSTEM)
- Multi-Source Signal Fusion Layer
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from .dna.schema import OpportunityDNA
from .learning_memory import update_learning_weights
from .signal_ingestion import SignalIngestionEngine
from .signal_fusion import SignalFusionEngine


class MarketCapacityEngine:

    def evaluate(
        self,
        niche_name: str,
        dna: OpportunityDNA,
        ctx: dict,
        scout_result=None,
        demand_result=None,
        grounding_result=None
    ) -> Dict[str, Any]:

        # ─────────────────────────────────────────────────────────────
        # 0. SIGNAL INGESTION & FUSION
        # ─────────────────────────────────────────────────────────────
        signal_engine = SignalIngestionEngine()
        fusion_engine = SignalFusionEngine()

        raw_signal = signal_engine.ingest(niche_name)
        # wrap into list for fusion system compatibility
        fused_signal = fusion_engine.fuse([raw_signal])

        # ─────────────────────────────────────────────────────────────
        # 1. LOAD LEARNING WEIGHTS (SELF-IMPROVEMENT LOOP)
        # ─────────────────────────────────────────────────────────────
        learning_weights = update_learning_weights()

        demand_w = learning_weights.get("demand", 0.45)
        supply_w = learning_weights.get("supply", 0.35)
        competition_w = learning_weights.get("competition", 0.20)

        # ─────────────────────────────────────────────────────────────
        # 2. SCOUT & DEMAND (INIT WITH FUSED SIGNALS)
        # ─────────────────────────────────────────────────────────────
        if scout_result:
            scout = scout_result.to_scout_overlay()
            supply_score = float(getattr(scout, "estimated_search_volume", 50).value)
            competition_score = float(getattr(scout, "competition_score", 50).value)
        else:
            supply_score = float(fused_signal.search_volume / 12)
            competition_score = float(fused_signal.competition_level)

        if demand_result:
            demand = demand_result.to_scout_overlay()
            demand_score = float(demand.estimated_search_volume.value)
            commercial_intent = float(getattr(demand, "commercial_intent", 50).value)
            advertiser_pressure = float(getattr(demand, "advertiser_demand", 50).value)
        else:
            demand_score = float(fused_signal.search_volume / 10)
            commercial_intent = float(fused_signal.commercial_intent)
            advertiser_pressure = 50.0

        # ─────────────────────────────────────────────────────────────
        # 3. GROUNDING (TRUTH CORRECTION LAYER)
        # ─────────────────────────────────────────────────────────────
        if grounding_result:
            demand_score = (
                demand_score * 0.7 +
                grounding_result.verified_demand_score * 0.3
            )
            supply_score = (
                supply_score * 0.7 +
                grounding_result.verified_supply_score * 0.3
            )
            competition_score = (
                competition_score * 0.7 +
                grounding_result.verified_competition_score * 0.3
            )

        # ─────────────────────────────────────────────────────────────
        # 4. FUSION CONFIDENCE WEIGHTING
        # ─────────────────────────────────────────────────────────────
        confidence_factor = fused_signal.confidence / 100

        demand_score *= confidence_factor
        supply_score *= confidence_factor
        competition_score *= confidence_factor

        # ─────────────────────────────────────────────────────────────
        # 5. NORMALIZATION
        # ─────────────────────────────────────────────────────────────
        demand_score = max(0, min(100, demand_score))
        supply_score = max(0, min(100, supply_score))
        competition_score = max(0, min(100, competition_score))

        # ─────────────────────────────────────────────────────────────
        # 6. FINAL MARKET CAPACITY SCORE (LEARNING WEIGHTED)
        # ─────────────────────────────────────────────────────────────
        final_score = (
            demand_score * demand_w +
            supply_score * supply_w +
            (100 - competition_score) * competition_w
        )

        # ─────────────────────────────────────────────────────────────
        # 7. REVENUE CEILING MODEL
        # ─────────────────────────────────────────────────────────────
        revenue_ceiling = (
            supply_score * 120
            * (demand_score / 50)
            * (1 + advertiser_pressure / 100)
        )

        # ─────────────────────────────────────────────────────────────
        # 8. READINESS FLAGS
        # ─────────────────────────────────────────────────────────────
        readiness = {
            "high_demand": demand_score > 70,
            "low_competition": competition_score < 40,
            "scalable_supply": supply_score > 60,
        }

        # ─────────────────────────────────────────────────────────────
        # 9. OUTPUT (SINGLE SOURCE OF TRUTH)
        # ─────────────────────────────────────────────────────────────
        return {
            "niche_name": niche_name,
            "dna_slug": getattr(dna, "slug", "unknown"),
            "market_capacity_score": round(final_score, 2),
            "demand_score": round(demand_score, 2),
            "supply_score": round(supply_score, 2),
            "competition_score": round(competition_score, 2),
            "revenue_ceiling": round(revenue_ceiling, 2),
            "readiness": readiness,
            "fusion_sources": fused_signal.sources,
            "fusion_confidence": fused_signal.confidence,
            "learning_weights": {
                "demand": demand_w,
                "supply": supply_w,
                "competition": competition_w
            }
        }


# ─────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────

_engine = MarketCapacityEngine()

def evaluate_market_capacity(
    niche_name: str,
    dna: OpportunityDNA,
    ctx: dict,
    scout_result=None,
    demand_result=None,
    grounding_result=None
) -> Dict[str, Any]:

    return _engine.evaluate(
        niche_name=niche_name,
        dna=dna,
        ctx=ctx,
        scout_result=scout_result,
        demand_result=demand_result,
        grounding_result=grounding_result
    )
"""
market_grounding.py — Atlas Ground Truth Layer (FULL VERSION)

This module:
- Takes modeled market outputs (Scout + Demand + Market Capacity)
- Applies external-like correction logic (future API-ready)
- Produces grounded, confidence-adjusted signals
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GroundedMarketSignal:
    niche_name: str

    verified_demand_score: float
    verified_supply_score: float
    verified_competition_score: float

    confidence: float
    data_sources: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class MarketGroundingEngine:

    def __init__(self, providers: Optional[list] = None):
        """
        Providers will later include:
        - Google Trends
        - SERP APIs
        - Keyword tools
        - Business directories
        """
        self.providers = providers or []

    def validate(
        self,
        niche_name: str,
        modeled_data: Dict[str, Any]
    ) -> GroundedMarketSignal:
        """
        Converts internal model output into grounded market truth estimates.
        """

        # ─────────────────────────────────────────────
        # STEP 1: RAW MODEL INPUTS
        # ─────────────────────────────────────────────
        demand = float(modeled_data.get("demand_score", 50))
        supply = float(modeled_data.get("supply_score", 50))
        competition = float(modeled_data.get("competition_score", 50))

        # ─────────────────────────────────────────────
        # STEP 2: GROUNDING ADJUSTMENTS (SIMULATED REALITY LAYER)
        # ─────────────────────────────────────────────
        # These simulate real-world correction bias
        # (later replaced by real APIs — DO NOT REMOVE STRUCTURE)

        demand_adjustment = 0.85 + (demand / 200.0)
        supply_adjustment = 0.80 + (supply / 250.0)
        competition_adjustment = 1.05 - (competition / 300.0)

        verified_demand = demand * demand_adjustment
        verified_supply = supply * supply_adjustment
        verified_competition = competition * competition_adjustment

        # Clamp values
        verified_demand = max(0, min(100, verified_demand))
        verified_supply = max(0, min(100, verified_supply))
        verified_competition = max(0, min(100, verified_competition))

        # ─────────────────────────────────────────────
        # STEP 3: CONFIDENCE MODEL
        # ─────────────────────────────────────────────
        stability_factor = (
            verified_demand +
            verified_supply +
            (100 - verified_competition)
        ) / 3

        confidence = max(0, min(100, stability_factor * 0.92))

        # ─────────────────────────────────────────────
        # STEP 4: RETURN GROUND TRUTH SIGNAL
        # ─────────────────────────────────────────────
        return GroundedMarketSignal(
            niche_name=niche_name,
            verified_demand_score=round(verified_demand, 2),
            verified_supply_score=round(verified_supply, 2),
            verified_competition_score=round(verified_competition, 2),
            confidence=round(confidence, 2),
            data_sources=[
                "simulated_grounding_layer_v1"
            ]
        )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC FUNCTION (OPTIONAL CONVENIENCE WRAPPER)
# ─────────────────────────────────────────────────────────────────────────────

def run_market_grounding(niche_name: str, modeled_data: Dict[str, Any]):
    engine = MarketGroundingEngine()
    return engine.validate(niche_name, modeled_data)
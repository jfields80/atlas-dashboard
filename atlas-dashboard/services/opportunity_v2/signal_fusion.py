"""
signal_fusion.py — Atlas Multi-Source Intelligence Fusion Layer

Purpose:
- Combine multiple market signals into one unified truth
- Resolve contradictions between providers
- Produce weighted “market reality”
"""

from dataclasses import dataclass
from typing import List

from .signal_providers import RawMarketSignal


# ─────────────────────────────────────────────
# FUSED OUTPUT
# ─────────────────────────────────────────────

@dataclass
class FusedMarketSignal:
    search_volume: float
    competition_level: float
    commercial_intent: float
    confidence: float
    sources: List[str]


# ─────────────────────────────────────────────
# FUSION ENGINE
# ─────────────────────────────────────────────

class SignalFusionEngine:

    def fuse(self, signals: List[RawMarketSignal]) -> FusedMarketSignal:
        """
        Combine multiple raw signals into a single intelligence signal.
        """

        if not signals:
            return FusedMarketSignal(
                search_volume=0,
                competition_level=0,
                commercial_intent=0,
                confidence=0,
                sources=[]
            )

        total_weight = 0.0

        volume_sum = 0.0
        competition_sum = 0.0
        intent_sum = 0.0

        sources = []

        for sig in signals:

            # ─────────────────────────────────────────────
            # SOURCE WEIGHTING (TRUST MODEL)
            # ─────────────────────────────────────────────

            if "live" in sig.source:
                weight = 1.2
            elif "google" in sig.source:
                weight = 1.0
            else:
                weight = 0.7

            volume_sum += sig.search_volume * weight
            competition_sum += sig.competition_level * weight
            intent_sum += sig.commercial_intent * weight

            total_weight += weight
            sources.append(sig.source)

        # ─────────────────────────────────────────────
        # NORMALIZATION
        # ─────────────────────────────────────────────

        search_volume = volume_sum / total_weight
        competition_level = competition_sum / total_weight
        commercial_intent = intent_sum / total_weight

        # ─────────────────────────────────────────────
        # CONFIDENCE MODEL
        # ─────────────────────────────────────────────

        consistency_penalty = min(30, len(set(sources)) * 10)
        confidence = max(0, 100 - consistency_penalty)

        return FusedMarketSignal(
            search_volume=search_volume,
            competition_level=competition_level,
            commercial_intent=commercial_intent,
            confidence=confidence,
            sources=sources
        )
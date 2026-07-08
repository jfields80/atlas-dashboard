"""
signal_ingestion.py — Atlas Unified Signal Layer (REAL CONNECTOR READY)
"""

from dataclasses import dataclass

from .signal_providers import SignalProviderEngine


@dataclass
class MarketSignal:
    niche_name: str
    search_volume: float
    competition_level: float
    commercial_intent: float
    source: str
    confidence: float


class SignalIngestionEngine:

    def __init__(self):
        self.provider_engine = SignalProviderEngine()

    def ingest(self, niche_name: str) -> MarketSignal:

        raw = self.provider_engine.fetch_best_signal(niche_name)

        # confidence depends on provider quality (placeholder logic)
        confidence = 70.0 if "google" in raw.source else 55.0

        return MarketSignal(
            niche_name=niche_name,
            search_volume=raw.search_volume,
            competition_level=raw.competition_level,
            commercial_intent=raw.commercial_intent,
            source=raw.source,
            confidence=confidence
        )
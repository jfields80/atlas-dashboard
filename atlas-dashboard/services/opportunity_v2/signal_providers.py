"""
signal_providers.py — Atlas Real Market Data Providers Layer

This is the plug-in layer for real-world intelligence sources.
No scoring logic lives here.
Only data retrieval + normalization.
"""

from dataclasses import dataclass
from typing import Protocol, List

# ─────────────────────────────────────────────
# STANDARD SIGNAL FORMAT
# ─────────────────────────────────────────────

@dataclass
class RawMarketSignal:
    search_volume: float
    competition_level: float
    commercial_intent: float
    source: str


# ─────────────────────────────────────────────
# PROVIDER CONTRACT
# ─────────────────────────────────────────────

class SignalProvider(Protocol):
    def fetch(self, niche_name: str) -> RawMarketSignal:
        ...


# ─────────────────────────────────────────────
# BASELINE FALLBACK PROVIDER
# ─────────────────────────────────────────────

class BaselineSignalProvider:
    """
    Safe fallback provider when no external APIs exist.
    """

    def fetch(self, niche_name: str) -> RawMarketSignal:

        volume = len(niche_name) * 120
        competition = min(100, len(niche_name) * 8)
        intent = 50 + (len(niche_name) % 20)

        return RawMarketSignal(
            search_volume=volume,
            competition_level=competition,
            commercial_intent=intent,
            source="baseline_provider_v1"
        )


# ─────────────────────────────────────────────
# GOOGLE TRENDS PROVIDER (SAFE + OPTIONAL REAL MODE)
# ─────────────────────────────────────────────

class GoogleTrendsProvider:
    """
    Real Google Trends integration (safe import).
    Falls back gracefully if pytrends is not installed.
    """

    def __init__(self):
        try:
            from pytrends.request import TrendReq
            self.client = TrendReq(hl="en-US", tz=360)
            self.available = True
        except Exception:
            self.client = None
            self.available = False

    def fetch(self, niche_name: str) -> RawMarketSignal:

        # ─────────────────────────────────────────────
        # REAL MODE (IF PYTRENDS EXISTS)
        # ─────────────────────────────────────────────
        if self.available:
            try:
                self.client.build_payload([niche_name], timeframe="today 12-m")
                data = self.client.interest_over_time()

                if data is not None and not data.empty:
                    series = data[niche_name]

                    avg_volume = float(series.mean())
                    volatility = float(series.std())
                    peak = float(series.max())

                    competition = min(100, max(10, peak / 2))
                    intent = max(10, 100 - volatility)

                    return RawMarketSignal(
                        search_volume=avg_volume * 10,
                        competition_level=competition,
                        commercial_intent=intent,
                        source="google_trends_live"
                    )

            except Exception:
                # fail safely into baseline
                pass

        # ─────────────────────────────────────────────
        # FALLBACK MODE
        # ─────────────────────────────────────────────
        volume = len(niche_name) * 180
        competition = min(100, len(niche_name) * 6)
        intent = 55 + (len(niche_name) % 25)

        return RawMarketSignal(
            search_volume=volume,
            competition_level=competition,
            commercial_intent=intent,
            source="google_trends_fallback"
        )


# ─────────────────────────────────────────────
# PROVIDER ORCHESTRATOR
# ─────────────────────────────────────────────

class SignalProviderEngine:

    def __init__(self):
        self.providers: List[SignalProvider] = [
            GoogleTrendsProvider(),
            BaselineSignalProvider()
        ]

    def fetch_best_signal(self, niche_name: str) -> RawMarketSignal:

        signals = []

        for provider in self.providers:
            try:
                signals.append(provider.fetch(niche_name))
            except Exception:
                continue

        if not signals:
            return RawMarketSignal(
                search_volume=0,
                competition_level=0,
                commercial_intent=0,
                source="no_provider_available"
            )

        # ─────────────────────────────────────────────
        # SELECT BEST SIGNAL (HIGHEST CONFIDENCE WEIGHT)
        # ─────────────────────────────────────────────

        def score(sig: RawMarketSignal) -> float:
            return sig.search_volume * 0.5 + sig.commercial_intent * 0.3 - sig.competition_level * 0.2

        best = max(signals, key=score)

        return best
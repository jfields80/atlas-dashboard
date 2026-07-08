"""
autonomous_engine.py — Atlas Autonomous Opportunity Generator

Purpose:
- Continuously generate and evaluate new business opportunities
- Run Atlas without manual input
- Feed dashboard + database automatically
"""

import random
import time

from .signal_ingestion import SignalIngestionEngine
from .signal_fusion import SignalFusionEngine
from .market_capacity import evaluate_market_capacity
from .decision_engine import DecisionEngine
from .explain_engine import ExplainEngine
from .product_layer import ProductLayer

from .opportunity_store import save_opportunity


class AutonomousOpportunityEngine:

    def __init__(self):
        self.signal_engine = SignalIngestionEngine()
        self.fusion_engine = SignalFusionEngine()
        self.decision_engine = DecisionEngine()
        self.explain_engine = ExplainEngine()
        self.product_layer = ProductLayer()

        # seed idea space (can be expanded later)
        self.base_niches = [
            "dog training online",
            "meal prep delivery",
            "AI resume builder",
            "pet grooming subscription",
            "credit repair service",
            "fitness coaching app",
            "local HVAC leads",
            "mobile car detailing",
            "AI content generator",
            "tutoring marketplace"
        ]

    def generate_niche(self) -> str:
        """
        Expands base ideas into variations (simple version now)
        """

        base = random.choice(self.base_niches)

        modifiers = [
            "for beginners",
            "near me",
            "subscription",
            "AI powered",
            "low cost",
            "premium",
            "for small business"
        ]

        return f"{base} {random.choice(modifiers)}"

    def run_once(self):

        niche = self.generate_niche()

        # 1. SIGNALS
        raw_signal = self.signal_engine.ingest(niche)
        fused_signal = self.fusion_engine.fuse([raw_signal])

        # 2. MARKET ANALYSIS
        market = evaluate_market_capacity(
            niche_name=niche,
            dna=None,
            ctx={},
            scout_result=None,
            demand_result=None,
            grounding_result=None
        )

        # 3. DECISION
        decision = self.decision_engine.evaluate(market)

        # skip weak ideas early
        if decision.recommendation == "PASS":
            return None

        # 4. EXPLANATION
        explanation = self.explain_engine.build_explanation(
            niche_name=niche,
            market_capacity_result=market,
            fused_signal=fused_signal,
            decision=decision
        )

        # 5. PRODUCT CARD
        card = self.product_layer.build_card(
            market_capacity=market,
            decision=decision,
            explanation=explanation
        )

        result = card.__dict__

        # 6. SAVE TO DATABASE
        save_opportunity(result)

        return result

    def run_loop(self, iterations=10, sleep_time=1):
        """
        Continuous autonomous discovery mode
        """

        results = []

        for _ in range(iterations):

            try:
                result = self.run_once()

                if result:
                    results.append(result)
                    print(f"[Atlas] Found opportunity: {result['niche_name']}")

                time.sleep(sleep_time)

            except Exception as e:
                print("[Atlas Autonomous Error]", str(e))

        return results
"""
batch_opportunity_engine.py — Atlas v3 Opportunity Feed Generator

Purpose:
- Runs multiple niche evaluations in one batch
- Produces ranked opportunity feed (SaaS-style output)
- Foundation for dashboard + productization
"""

from typing import List, Dict, Any


class BatchOpportunityEngine:

    def __init__(self, runner, signal_engine, fusion_engine,
                 market_engine, decision_engine,
                 synergy_engine, committee, snapshot_factory):

        self.runner = runner
        self.signal_engine = signal_engine
        self.fusion_engine = fusion_engine
        self.market_engine = market_engine
        self.decision_engine = decision_engine
        self.synergy_engine = synergy_engine
        self.committee = committee
        self.snapshot_factory = snapshot_factory

    # ─────────────────────────────────────────────
    # MAIN ENTRY
    # ─────────────────────────────────────────────

    def run_batch(self, niches: List[str]) -> List[Dict[str, Any]]:

        results = []

        # shared portfolio snapshot per batch (IMPORTANT for determinism)
        snapshot = self.snapshot_factory.create_snapshot([
            {
                "asset_id": "demo-1",
                "name": "Pet Directory",
                "category": "directory",
                "status": "building",
                "revenue": 0
            }
        ])

        for niche in niches:

            # ─────────────────────────────
            # SIGNAL LAYER
            # ─────────────────────────────

            raw = self.signal_engine.ingest(niche)
            fused = self.fusion_engine.fuse([raw])

            # ─────────────────────────────
            # MARKET LAYER
            # ─────────────────────────────

            market = self.market_engine(
                niche_name=niche,
                dna=None,
                ctx={},
                scout_result=None,
                demand_result=None,
                grounding_result=None
            )

            # ─────────────────────────────
            # V2 DECISION
            # ─────────────────────────────

            v2_decision = self.decision_engine.evaluate(market)

            # ─────────────────────────────
            # V3 SYNERGY
            # ─────────────────────────────

            synergy = self.synergy_engine.score(
                {"category": "AI tools", "revenue_ceiling": 36000},
                snapshot
            )

            # ─────────────────────────────
            # FINAL COMMITTEE DECISION
            # ─────────────────────────────

            final = self.committee.decide(
                v2_decision=v2_decision,
                synergy_report=synergy
            )

            results.append({
                "niche": niche,
                "score": final.final_score,
                "recommendation": final.recommendation,
                "confidence": final.confidence,
                "synergy": final.synergy_score
            })

        # ─────────────────────────────
        # SORTING (PRODUCT FEED STYLE)
        # ─────────────────────────────

        results.sort(key=lambda x: x["score"], reverse=True)

        return results
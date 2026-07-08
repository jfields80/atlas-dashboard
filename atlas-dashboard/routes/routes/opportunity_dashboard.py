"""
opportunity_dashboard.py — Atlas SaaS Dashboard Layer

Purpose:
- Converts backend intelligence into frontend-ready product feed
- Serves Atlas as a usable SaaS interface
"""

from flask import Blueprint, render_template

from services.opportunity_v2.signal_ingestion import SignalIngestionEngine
from services.opportunity_v2.signal_fusion import SignalFusionEngine
from services.opportunity_v2.market_capacity import evaluate_market_capacity
from services.opportunity_v2.decision_engine import DecisionEngine
from services.opportunity_v2.explain_engine import ExplainEngine
from services.opportunity_v2.product_layer import ProductLayer

dashboard_bp = Blueprint("opportunity_dashboard", __name__)


@dashboard_bp.route("/atlas/opportunities")
def opportunity_feed():

    # ─────────────────────────────────────────────
    # CORE SYSTEM INITIALIZATION
    # ─────────────────────────────────────────────

    signal_engine = SignalIngestionEngine()
    fusion_engine = SignalFusionEngine()
    decision_engine = DecisionEngine()
    explain_engine = ExplainEngine()
    product_layer = ProductLayer()

    # ─────────────────────────────────────────────
    # SAMPLE NICHES (TEMP — later replaced by generator)
    # ─────────────────────────────────────────────

    niches = [
        "dog training online",
        "local meal prep service",
        "AI resume builder",
        "pet grooming subscription",
        "credit repair service"
    ]

    results = []

    # ─────────────────────────────────────────────
    # PIPELINE EXECUTION
    # ─────────────────────────────────────────────

    for niche in niches:

        # 1. SIGNAL INGESTION
        raw_signal = signal_engine.ingest(niche)
        fused_signal = fusion_engine.fuse([raw_signal])

        # 2. MARKET CAPACITY
        market = evaluate_market_capacity(
            niche_name=niche,
            dna=None,
            ctx={},
            scout_result=None,
            demand_result=None,
            grounding_result=None
        )

        # 3. DECISION ENGINE
        decision = decision_engine.evaluate(market)

        # 4. EXPLANATION ENGINE
        explanation = explain_engine.build_explanation(
            niche_name=niche,
            market_capacity_result=market,
            fused_signal=fused_signal,
            decision=decision
        )

        # 5. PRODUCT LAYER (FINAL OUTPUT SHAPE)
        card = product_layer.build_card(
            market_capacity=market,
            decision=decision,
            explanation=explanation
        )

        results.append(card.__dict__)

    # ─────────────────────────────────────────────
    # SORT BY INVESTMENT SCORE (DESCENDING)
    # ─────────────────────────────────────────────

    results.sort(key=lambda x: x.get("score", 0), reverse=True)

    return render_template(
        "opportunities_dashboard.html",
        opportunities=results
    )
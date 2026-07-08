from flask import render_template

from services.opportunity_v2.niche_generator import NicheGenerator
from services.opportunity_v2.batch_opportunity_generator import BatchOpportunityGenerator
from services.opportunity_v2.market_capacity import evaluate_market_capacity
from services.opportunity_v2.market_grounding import MarketGroundingEngine
from services.opportunity_v2.decision_engine import DecisionEngine


@opportunities_bp.route("/opportunities/auto", methods=["GET"])
def run_autonomous_opportunity_scan():

    # ─────────────────────────────────────────────
    # 1. GENERATE NICHES
    # ─────────────────────────────────────────────
    niche_candidates = NicheGenerator().generate()

    # ─────────────────────────────────────────────
    # 2. RUN PIPELINE (Scout + Demand + Market Capacity)
    # ─────────────────────────────────────────────
    pipeline = BatchOpportunityGenerator(
        market_capacity_engine=evaluate_market_capacity
    )

    raw_results = pipeline.generate(
        niche_candidates=niche_candidates,
        dna=None,
        ctx={},
        top_k=50
    )

    # ─────────────────────────────────────────────
    # 3. GROUNDING + FINAL DECISION
    # ─────────────────────────────────────────────
    grounding_engine = MarketGroundingEngine()
    decision_engine = DecisionEngine()

    final_opportunities = []

    for opp in raw_results["top_opportunities"]:

        grounding = grounding_engine.validate(
            niche_name=opp["niche"],
            modeled_data={
                "demand_score": opp["demand"],
                "supply_score": opp["supply"],
                "competition_score": 50
            }
        )

        decision = decision_engine.evaluate(
            market_capacity_result={
                "niche_name": opp["niche"],
                "market_capacity_score": opp["score"]
            },
            grounding_result=grounding
        )

        final_opportunities.append({
            "niche": opp["niche"],
            "market_score": opp["score"],
            "final_score": decision.final_score,
            "recommendation": decision.recommendation,
            "demand": opp["demand"],
            "supply": opp["supply"],
            "revenue_ceiling": opp["revenue_ceiling"]
        })

    # ─────────────────────────────────────────────
    # 4. SORT FINAL RESULTS
    # ─────────────────────────────────────────────
    final_opportunities.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    # ─────────────────────────────────────────────
    # 5. RENDER DASHBOARD
    # ─────────────────────────────────────────────
    return render_template(
        "opportunities_dashboard.html",
        data={
            "top_opportunities": final_opportunities[:10],
            "total_analyzed": len(niche_candidates),
            "build_candidates": [
                x for x in final_opportunities if x["recommendation"] == "BUILD"
            ]
        },
        auto_generated=True
    )
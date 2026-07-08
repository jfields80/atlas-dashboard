"""
Atlas v3 FULL SYSTEM TEST — CONNECTED PIPELINE
"""

import os
import sys

# ─────────────────────────────
# FIX IMPORT PATHS
# ─────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from services.opportunity_v2.signal_ingestion import SignalIngestionEngine
from services.opportunity_v2.signal_fusion import SignalFusionEngine
from services.opportunity_v2.market_capacity import evaluate_market_capacity
from services.opportunity_v2.decision_engine import DecisionEngine

from core.engine_versions import EngineVersionSet
from core.snapshots import PortfolioSnapshotFactory

from engines.portfolio_synergy import PortfolioSynergyEngine
from services.investment_committee import InvestmentCommittee
from services.pipeline_runner import PipelineRunner
from repositories.run_repository import RunRepository


# ─────────────────────────────
# MAIN RUN FUNCTION
# ─────────────────────────────

def run():

    print("\n============================")
    print("ATLAS v3 FULL CONNECTED RUN")
    print("============================\n")

    # ─────────────────────────────
    # CORE SYSTEMS
    # ─────────────────────────────

    runner = PipelineRunner()
    version_set = EngineVersionSet()

    snapshot_factory = PortfolioSnapshotFactory()
    synergy_engine = PortfolioSynergyEngine()
    committee = InvestmentCommittee()
    repo = RunRepository()

    # ─────────────────────────────
    # PORTFOLIO SNAPSHOT
    # ─────────────────────────────

    snapshot = snapshot_factory.create_snapshot([
        {
            "asset_id": "demo-1",
            "name": "Pet Directory",
            "category": "directory",
            "status": "building",
            "revenue": 0
        }
    ])

    # ─────────────────────────────
    # START RUN
    # ─────────────────────────────

    context = runner.start_run({
        "niche": "AI resume builder"
    })

    runner.log_stage("SNAPSHOT_CREATED", {"snapshot_id": snapshot.snapshot_id})

    niche = "AI resume builder"

    # ─────────────────────────────
    # SIGNAL INGESTION
    # ─────────────────────────────

    print("[1] Signal ingestion...")
    signal_engine = SignalIngestionEngine()
    raw = signal_engine.ingest(niche)
    print("OK:", raw)

    runner.log_stage("SIGNAL_INGESTED", raw.__dict__)

    # ─────────────────────────────
    # SIGNAL FUSION
    # ─────────────────────────────

    print("\n[2] Signal fusion...")
    fusion_engine = SignalFusionEngine()
    fused = fusion_engine.fuse([raw])
    print("OK:", fused)

    runner.log_stage("SIGNAL_FUSED", fused.__dict__)

    # ─────────────────────────────
    # MARKET CAPACITY
    # ─────────────────────────────

    print("\n[3] Market capacity...")
    market = evaluate_market_capacity(
        niche_name=niche,
        dna=None,
        ctx={},
        scout_result=None,
        demand_result=None,
        grounding_result=None
    )
    print("OK:", market)

    runner.log_stage("MARKET_EVALUATED", market)

    # ─────────────────────────────
    # DECISION ENGINE (v2)
    # ─────────────────────────────

    print("\n[4] Decision engine...")
    decision_engine = DecisionEngine()
    v2_decision = decision_engine.evaluate(market)
    print("OK:", v2_decision)

    runner.log_stage("V2_DECISION", v2_decision.__dict__)

    # ─────────────────────────────
    # SYNERGY ENGINE (v3)
    # ─────────────────────────────

    print("\n[5] Synergy engine...")
    synergy = synergy_engine.score(
        {"category": "AI tools", "revenue_ceiling": 36000},
        snapshot
    )
    print("OK:", synergy)

    runner.log_stage("SYNERGY_CALCULATED", synergy.__dict__)

    # ─────────────────────────────
    # INVESTMENT COMMITTEE (FINAL DECISION)
    # ─────────────────────────────

    print("\n[6] Investment committee...")
    final = committee.decide(
        v2_decision=v2_decision,
        synergy_report=synergy
    )
    print("OK:", final)

    runner.log_stage("FINAL_DECISION", final.__dict__)

    # ─────────────────────────────
    # FINALIZE RUN + PERSIST
    # ─────────────────────────────

    result = runner.finish_run(final.__dict__)
    repo.save_run(runner.current_run, result)

    print("\n============================")
    print("✅ ATLAS FULL CONNECTED RUN COMPLETE")
    print("============================\n")

    print(result)


# ─────────────────────────────
# ENTRY POINT (FIXED INDENTATION)
# ─────────────────────────────

if __name__ == "__main__":
    run()
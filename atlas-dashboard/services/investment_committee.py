"""
services/investment_committee.py

Investment Committee Service — the only place v3 judgment happens.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from core.engine_versions import EngineVersionSet
from services.v2_types import DecisionResult
from engines.portfolio_synergy import SynergyReport
from engines.expansion_classifier import ExpansionClass
from engines.market_liquidity import LiquidityEvidence


_DECISION_RANK: dict[str, int] = {
    "BUILD": 4,
    "TEST": 3,
    "DEFER": 2,
    "REJECT": 1,
}


def _demote_decision(current: str, to: str) -> str:
    """Return the lower-ranked decision. Never promotes."""
    if _DECISION_RANK.get(to, 0) < _DECISION_RANK.get(current, 0):
        return to
    return current


class SynergyReportModel(BaseModel):
    total_score: float
    portfolio_snapshot_id: str
    category: str
    geographic_scope: str
    components: list[dict[str, Any]] = Field(default_factory=list)


class ExpansionClassModel(BaseModel):
    label: str
    confidence: float
    plain_english: str
    synergy_driven: bool
    factors: list[dict[str, Any]] = Field(default_factory=list)


class LiquidityEvidenceModel(BaseModel):
    category: str
    geographic_scope: str
    multiple_lo: float
    multiple_hi: float
    multiple_typical: float
    multiple_source: str
    multiple_confidence: float
    buyer_demand_signal: float
    buyer_demand_source: str
    time_to_exit_lo_months: int
    time_to_exit_hi_months: int
    buyer_depth_estimate: int
    compression_risks: list[str]


class PortfolioDecisionResult(BaseModel):
    run_id: str
    portfolio_snapshot_id: str
    engine_versions: dict[str, str]

    core_decision: DecisionResult

    synergy: SynergyReportModel
    expansion: ExpansionClassModel
    liquidity: LiquidityEvidenceModel

    portfolio_recommendation: str
    portfolio_confidence: float
    honest_wall_binding: bool
    committee_rationale: str

    rank_inputs: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


def _synergy_to_model(r: SynergyReport) -> SynergyReportModel:
    return SynergyReportModel(
        total_score=r.total_score,
        portfolio_snapshot_id=r.portfolio_snapshot_id,
        category=r.category,
        geographic_scope=r.geographic_scope,
        components=[
            {
                "name": c.name,
                "raw_value": c.raw_value,
                "weight": c.weight,
                "contribution": c.contribution,
                "rationale": c.rationale,
            }
            for c in r.components
        ],
    )


def _expansion_to_model(e: ExpansionClass) -> ExpansionClassModel:
    return ExpansionClassModel(
        label=e.label,
        confidence=e.confidence,
        plain_english=e.plain_english,
        synergy_driven=e.synergy_driven,
        factors=[
            {
                "name": f.name,
                "observed_value": f.observed_value,
                "rule_threshold": f.rule_threshold,
                "passed": f.passed,
                "rationale": f.rationale,
            }
            for f in e.factors
        ],
    )


def _liquidity_to_model(liq: LiquidityEvidence) -> LiquidityEvidenceModel:
    tte = liq.time_to_exit_months.value

    return LiquidityEvidenceModel(
        category=liq.category,
        geographic_scope=liq.geographic_scope,
        multiple_lo=liq.revenue_multiple_range.lo,
        multiple_hi=liq.revenue_multiple_range.hi,
        multiple_typical=liq.revenue_multiple_range.typical,
        multiple_source=liq.revenue_multiple_range.source,
        multiple_confidence=liq.revenue_multiple_range.confidence,
        buyer_demand_signal=liq.buyer_demand_signal.value,
        buyer_demand_source=liq.buyer_demand_signal.source,
        time_to_exit_lo_months=tte[0],
        time_to_exit_hi_months=tte[1],
        buyer_depth_estimate=liq.buyer_depth_estimate.value,
        compression_risks=list(liq.compression_risks.value),
    )


def decide(
    *,
    v2_result: DecisionResult,
    synergy_report: SynergyReport,
    expansion_class: ExpansionClass,
    liquidity_evidence: LiquidityEvidence,
    version_set: EngineVersionSet,
    run_id: str,
    portfolio_snapshot_id: str,
) -> PortfolioDecisionResult:
    now = datetime.now(timezone.utc).isoformat()

    base_decision = v2_result.decision
    base_confidence = v2_result.confidence
    honest_wall_binding = v2_result.honest_wall_applied

    cannibal_component = next(
        (c for c in synergy_report.components if c.name == "cannibalization_penalty"),
        None,
    )

    cannibal_penalty = abs(cannibal_component.contribution) if cannibal_component else 0.0
    demotion_reason: str | None = None

    portfolio_decision = base_decision

    if cannibal_penalty >= 0.30:
        if base_decision == "BUILD":
            portfolio_decision = _demote_decision(base_decision, "TEST")
            demotion_reason = (
                f"Cannibalization penalty {cannibal_penalty:.2f} — "
                "candidate directly competes with an owned asset. "
                "Demoted BUILD → TEST pending differentiation strategy."
            )
        elif base_decision == "TEST":
            portfolio_decision = _demote_decision(base_decision, "DEFER")
            demotion_reason = (
                f"Cannibalization penalty {cannibal_penalty:.2f} — "
                "candidate competes with an owned asset. "
                "Demoted TEST → DEFER."
            )

    synergy_bonus = max(0.0, synergy_report.total_score) * 0.08
    expansion_bonus = 0.05 if expansion_class.label in ("Expansion", "Flagship") else 0.0
    raw_portfolio_confidence = base_confidence + synergy_bonus + expansion_bonus

    if honest_wall_binding:
        portfolio_confidence = min(0.45, raw_portfolio_confidence)
    else:
        portfolio_confidence = min(0.95, raw_portfolio_confidence)

    portfolio_confidence = round(portfolio_confidence, 4)

    rationale_parts = [
        f"v2 decision: {base_decision} (confidence {base_confidence:.2f}).",
        f"Expansion class: {expansion_class.label} — {expansion_class.plain_english}",
        f"Portfolio synergy score: {synergy_report.total_score:.3f}.",
        (
            f"Exit multiple range: {liquidity_evidence.revenue_multiple_range.lo}–"
            f"{liquidity_evidence.revenue_multiple_range.hi}× "
            f"(typical {liquidity_evidence.revenue_multiple_range.typical}×)."
        ),
    ]

    if demotion_reason:
        rationale_parts.append(f"Committee demotion applied: {demotion_reason}")

    if honest_wall_binding:
        rationale_parts.append(
            "Honest wall binding: estimated-data confidence cap 0.45 applied. "
            "Verified evidence required to unlock BUILD recommendation."
        )

    committee_rationale = " | ".join(rationale_parts)

    rank_inputs = {
        "v2_score": v2_result.score_breakdown.total_score,
        "synergy_score": synergy_report.total_score,
        "expansion_label": expansion_class.label,
        "expansion_confidence": expansion_class.confidence,
        "liquidity_buyer_demand": liquidity_evidence.buyer_demand_signal.value,
        "portfolio_confidence": portfolio_confidence,
        "cannibalization_penalty": cannibal_penalty,
        "honest_wall_binding": honest_wall_binding,
    }

    return PortfolioDecisionResult(
        run_id=run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        engine_versions=version_set.as_dict(),
        core_decision=v2_result,
        synergy=_synergy_to_model(synergy_report),
        expansion=_expansion_to_model(expansion_class),
        liquidity=_liquidity_to_model(liquidity_evidence),
        portfolio_recommendation=portfolio_decision,
        portfolio_confidence=portfolio_confidence,
        honest_wall_binding=honest_wall_binding,
        committee_rationale=committee_rationale,
        rank_inputs=rank_inputs,
        created_at=now,
    )


class InvestmentCommittee:
    """
    Compatibility wrapper for older Atlas tests/call sites.
    """

    def decide(
        self,
        *,
        v2_result: DecisionResult,
        synergy_report: SynergyReport,
        expansion_class: ExpansionClass,
        liquidity_evidence: LiquidityEvidence,
        version_set: EngineVersionSet,
        run_id: str,
        portfolio_snapshot_id: str,
    ) -> PortfolioDecisionResult:
        return decide(
            v2_result=v2_result,
            synergy_report=synergy_report,
            expansion_class=expansion_class,
            liquidity_evidence=liquidity_evidence,
            version_set=version_set,
            run_id=run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
        )
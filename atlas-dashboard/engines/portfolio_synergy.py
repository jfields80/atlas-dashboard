"""
atlas/engines/portfolio_synergy.py

Portfolio Synergy Engine — MVP implementation.

Pure function: (EvidenceBundle, PortfolioSnapshot) → SynergyReport.

Decomposed into named SynergyComponents with raw_value, weight,
contribution, and plain-English rationale (full explainability rule).

Architecture rules:
  - Zero I/O. Zero database access.
  - Evidence only — produces a report, never a decision.
  - The snapshot is passed pre-loaded; this engine never reads live state.
  - Deterministic: same inputs → same outputs, every time.

Synergy components (v1.0.0):
  1. audience_overlap       — shared demographic/intent with owned assets
  2. data_pipeline_reuse    — existing Scout/provider coverage for this niche
  3. cross_promotion        — owned assets can send referral traffic
  4. operational_reuse      — same monetisation playbook already mastered
  5. cannibalization_penalty — candidate directly competes with an owned asset (negative)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.portfolio_service import PortfolioSnapshot


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SynergyComponent:
    name: str
    raw_value: float        # 0.0–1.0
    weight: float           # contribution weight; sum of positive weights = 1.0
    contribution: float     # raw_value × weight (signed — penalty is negative)
    rationale: str


@dataclass(frozen=True)
class SynergyReport:
    """
    Fully explainable synergy analysis between a candidate opportunity
    and the current portfolio snapshot.

    total_score: signed sum of contributions; clamped to [-1.0, 1.0].
    A score of 0.0 means no meaningful synergy in either direction.
    Negative scores indicate the candidate competes with owned assets.
    """
    components: tuple[SynergyComponent, ...]
    total_score: float          # clamped to [-1.0, 1.0]
    portfolio_snapshot_id: str
    category: str
    geographic_scope: str


# ---------------------------------------------------------------------------
# Component weights (sum of positive weights = 1.0)
# ---------------------------------------------------------------------------

_WEIGHTS = {
    "audience_overlap":     0.35,
    "data_pipeline_reuse":  0.20,
    "cross_promotion":      0.25,
    "operational_reuse":    0.20,
}
_PENALTY_WEIGHT = 0.50   # cannibalization reduces total score by up to 0.50


# ---------------------------------------------------------------------------
# Category affinity tables
# ---------------------------------------------------------------------------

# Categories that share audience/intent overlap — bidirectional
_AUDIENCE_AFFINITY: dict[str, frozenset[str]] = {
    "pet":     frozenset({"pet", "travel", "health", "food"}),
    "travel":  frozenset({"travel", "pet", "food", "health"}),
    "food":    frozenset({"food", "health", "pet", "travel"}),
    "health":  frozenset({"health", "food", "pet"}),
    "trades":  frozenset({"trades", "home", "construction"}),
    "home":    frozenset({"home", "trades", "construction"}),
    "construction": frozenset({"construction", "trades", "home"}),
}

# Categories that share the same Scout/provider pipeline
_PIPELINE_AFFINITY: dict[str, frozenset[str]] = {
    "pet":     frozenset({"pet", "travel"}),    # Google Places covers both
    "travel":  frozenset({"travel", "pet"}),
    "food":    frozenset({"food", "health"}),
    "health":  frozenset({"health", "food"}),
    "trades":  frozenset({"trades", "construction", "home"}),
    "home":    frozenset({"home", "trades", "construction"}),
    "construction": frozenset({"construction", "trades", "home"}),
}

# Categories where cross-promotion traffic makes natural sense
_CROSS_PROMO_AFFINITY: dict[str, frozenset[str]] = {
    "pet":     frozenset({"pet", "travel", "food"}),
    "travel":  frozenset({"travel", "pet", "food"}),
    "food":    frozenset({"food", "pet", "travel", "health"}),
    "health":  frozenset({"health", "food"}),
    "trades":  frozenset({"trades", "home", "construction"}),
    "home":    frozenset({"home", "trades"}),
    "construction": frozenset({"construction", "trades"}),
}


def _affinity_score(
    candidate_category: str,
    owned_categories: frozenset[str],
    affinity_table: dict[str, frozenset[str]],
) -> float:
    """
    Returns 0.0–1.0 based on how many owned categories overlap with
    the candidate's affinity set.  Capped at 1.0.
    """
    cat = candidate_category.lower().split("-")[0].split("_")[0]
    affinity_set = affinity_table.get(cat, frozenset())
    if not affinity_set or not owned_categories:
        return 0.0
    overlap = len(affinity_set & owned_categories)
    return min(1.0, overlap / max(1, len(affinity_set)) * 2.0)


def _operational_reuse_score(
    candidate_monetization: str | None,
    owned_monetization_models: list[str],
) -> float:
    """
    Returns 0.0–1.0 based on how much the candidate's monetisation
    model overlaps with what's already in the portfolio.
    """
    if not candidate_monetization or not owned_monetization_models:
        return 0.0
    candidate_tokens = frozenset(candidate_monetization.lower().replace(",", " ").split())
    matches = sum(
        1 for model in owned_monetization_models
        if candidate_tokens & frozenset(model.lower().replace(",", " ").split())
    )
    return min(1.0, matches / max(1, len(owned_monetization_models)))


def _cannibalization_score(
    candidate_category: str,
    candidate_scope: str,
    owned_assets: tuple,
) -> float:
    """
    Returns 0.0–1.0 where 1.0 = direct competitor to an owned asset.
    A candidate in the exact same category AND geographic scope as an
    owned asset is a cannibalizer.
    """
    cat = candidate_category.lower().split("-")[0].split("_")[0]
    for asset in owned_assets:
        owned_cat = asset.primary_category.lower().split("-")[0].split("_")[0]
        if owned_cat == cat and asset.geographic_scope.lower() == candidate_scope.lower():
            return 1.0
        elif owned_cat == cat:
            return 0.40   # same category, different scope — partial cannibalization
    return 0.0


# ---------------------------------------------------------------------------
# Engine entry point
# ---------------------------------------------------------------------------

def score(
    *,
    candidate_category: str,
    candidate_geographic_scope: str,
    candidate_monetization_model: str | None,
    portfolio_snapshot: "PortfolioSnapshot",
) -> SynergyReport:
    """
    Compute portfolio synergy for a candidate opportunity.

    Args:
        candidate_category:          Primary business category slug.
        candidate_geographic_scope:  Geographic scope string.
        candidate_monetization_model: Comma-separated monetization tags or None.
        portfolio_snapshot:           Immutable snapshot from PortfolioService.

    Returns:
        SynergyReport — fully decomposed, signed total score.
    """
    owned = portfolio_snapshot.owned
    owned_categories = frozenset(
        a.primary_category.lower().split("-")[0].split("_")[0]
        for a in owned
    )
    owned_monetization = [
        a.monetization_model
        for a in owned
        if a.monetization_model
    ]

    components: list[SynergyComponent] = []

    # ------------------------------------------------------------------
    # 1. Audience overlap
    # ------------------------------------------------------------------
    audience_raw = _affinity_score(
        candidate_category, owned_categories, _AUDIENCE_AFFINITY
    )
    audience_contrib = round(audience_raw * _WEIGHTS["audience_overlap"], 4)
    components.append(SynergyComponent(
        name="audience_overlap",
        raw_value=round(audience_raw, 4),
        weight=_WEIGHTS["audience_overlap"],
        contribution=audience_contrib,
        rationale=(
            f"Candidate category '{candidate_category}' shares audience affinity "
            f"with {len(owned_categories & _AUDIENCE_AFFINITY.get(candidate_category.lower().split('-')[0].split('_')[0], frozenset()))} "
            f"of {len(owned_categories)} owned categories."
            if owned_categories else
            "No owned assets in portfolio — audience overlap is zero."
        ),
    ))

    # ------------------------------------------------------------------
    # 2. Data pipeline reuse
    # ------------------------------------------------------------------
    pipeline_raw = _affinity_score(
        candidate_category, owned_categories, _PIPELINE_AFFINITY
    )
    pipeline_contrib = round(pipeline_raw * _WEIGHTS["data_pipeline_reuse"], 4)
    components.append(SynergyComponent(
        name="data_pipeline_reuse",
        raw_value=round(pipeline_raw, 4),
        weight=_WEIGHTS["data_pipeline_reuse"],
        contribution=pipeline_contrib,
        rationale=(
            f"Existing Scout/provider pipelines cover "
            f"{'this category' if pipeline_raw > 0 else 'no overlap with this category'}."
        ),
    ))

    # ------------------------------------------------------------------
    # 3. Cross-promotion
    # ------------------------------------------------------------------
    xpromo_raw = _affinity_score(
        candidate_category, owned_categories, _CROSS_PROMO_AFFINITY
    )
    xpromo_contrib = round(xpromo_raw * _WEIGHTS["cross_promotion"], 4)
    components.append(SynergyComponent(
        name="cross_promotion",
        raw_value=round(xpromo_raw, 4),
        weight=_WEIGHTS["cross_promotion"],
        contribution=xpromo_contrib,
        rationale=(
            f"Owned assets {'can' if xpromo_raw > 0 else 'cannot'} send referral "
            f"traffic to a '{candidate_category}' directory."
        ),
    ))

    # ------------------------------------------------------------------
    # 4. Operational reuse
    # ------------------------------------------------------------------
    ops_raw = _operational_reuse_score(candidate_monetization_model, owned_monetization)
    ops_contrib = round(ops_raw * _WEIGHTS["operational_reuse"], 4)
    components.append(SynergyComponent(
        name="operational_reuse",
        raw_value=round(ops_raw, 4),
        weight=_WEIGHTS["operational_reuse"],
        contribution=ops_contrib,
        rationale=(
            f"Candidate monetisation model '{candidate_monetization_model or 'unknown'}' "
            f"{'overlaps with' if ops_raw > 0 else 'does not overlap with'} "
            f"existing portfolio monetisation playbooks."
        ),
    ))

    # ------------------------------------------------------------------
    # 5. Cannibalization penalty (negative contribution)
    # ------------------------------------------------------------------
    cannibal_raw = _cannibalization_score(
        candidate_category, candidate_geographic_scope, owned
    )
    cannibal_contrib = round(-cannibal_raw * _PENALTY_WEIGHT, 4)
    components.append(SynergyComponent(
        name="cannibalization_penalty",
        raw_value=round(cannibal_raw, 4),
        weight=-_PENALTY_WEIGHT,    # negative weight signals penalty direction
        contribution=cannibal_contrib,
        rationale=(
            f"Candidate {'directly competes with' if cannibal_raw >= 1.0 else 'partially overlaps with' if cannibal_raw > 0 else 'does not compete with'} "
            f"an owned asset in the same category/scope."
        ),
    ))

    # ------------------------------------------------------------------
    # Total score — sum of signed contributions, clamped to [-1.0, 1.0]
    # ------------------------------------------------------------------
    raw_total = sum(c.contribution for c in components)
    total_score = round(max(-1.0, min(1.0, raw_total)), 4)

    return SynergyReport(
        components=tuple(components),
        total_score=total_score,
        portfolio_snapshot_id=portfolio_snapshot.snapshot_id,
        category=candidate_category,
        geographic_scope=candidate_geographic_scope,
    )


# ---------------------------------------------------------------------------
# Compatibility wrapper
#
# Thin class shim for older call sites / tests that expect a
# PortfolioSynergyEngine class instance rather than the module-level
# score() function. Contains zero business logic — it delegates
# every call directly to score() above. The functional API (score())
# remains the canonical entry point and is unchanged.
# ---------------------------------------------------------------------------

class PortfolioSynergyEngine:
    """
    Compatibility wrapper around the module-level score() function.

    Usage:
        engine = PortfolioSynergyEngine()
        report = engine.score(
            candidate_category=...,
            candidate_geographic_scope=...,
            candidate_monetization_model=...,
            portfolio_snapshot=...,
        )

    This class holds no state and performs no logic of its own —
    it exists solely so that code written against a class-based
    interface continues to work unchanged.
    """

    def score(
        self,
        *,
        candidate_category: str,
        candidate_geographic_scope: str,
        candidate_monetization_model: str | None,
        portfolio_snapshot: "PortfolioSnapshot",
    ) -> SynergyReport:
        return score(
            candidate_category=candidate_category,
            candidate_geographic_scope=candidate_geographic_scope,
            candidate_monetization_model=candidate_monetization_model,
            portfolio_snapshot=portfolio_snapshot,
        )

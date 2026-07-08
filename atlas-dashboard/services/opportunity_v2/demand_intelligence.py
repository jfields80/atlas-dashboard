"""
demand_intelligence.py — Atlas Demand Intelligence Engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from .dna.schema import OpportunityDNA, Intensity
from .scout_providers import DataSource, TaggedValue, _estimated, _unknown
from .demand_providers import (
    DemandProviderOutput, EstimatedDemandProvider, merge_demand_outputs,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_W_VOLUME       = 0.30
_W_COMMERCIAL   = 0.20
_W_LONG_TAIL    = 0.15
_W_SERP         = 0.10
_W_TREND        = 0.10
_W_LOCAL        = 0.10
_W_SEASONALITY  = 0.05

_VOLUME_REFERENCE = 50_000

_SHARE_HEAD       = 0.40
_SHARE_SYNONYM    = 0.12
_SHARE_COMMERCIAL = 0.08
_SHARE_LOCAL      = 0.10
_SHARE_QUESTION   = 0.05
_SHARE_DIMENSION  = 0.04

_MAX_SYNONYM_VARIANTS   = 3
_MAX_COMMERCIAL_VARIANTS = 3
_MAX_LOCAL_VARIANTS      = 2
_MAX_QUESTION_VARIANTS   = 3
_MAX_DIMENSION_VARIANTS  = 6

_SYNONYM_SWAPS: list[tuple[str, str]] = [
    ("pet friendly", "dog friendly"),
    ("hotels", "lodging"),
    ("restaurants", "places to eat"),
    ("cafes", "coffee shops"),
]

_COMMERCIAL_PREFIXES = ["best", "top", "affordable"]

_QUESTION_TEMPLATES = [
    "what are the best {niche}",
    "how to find {niche}",
    "where to find {niche}",
]

_LOCAL_SUFFIXES = ["near me", "nearby"]

# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IntentVariant:
    keyword: str
    variant_type: str
    share_weight: float
    estimated_share: float
    estimated_monthly_volume: int
    derivation: str


@dataclass
class IntentCluster:
    head_term: str
    variants: list[IntentVariant]
    cluster_monthly_volume: int
    head_share: float
    variant_count: int
    derivation_notes: list[str] = field(default_factory=list)


@dataclass
class DemandComponent:
    name: str
    raw_value: float
    normalized_value: float
    weight: float
    weighted_contribution: float
    explanation: str


@dataclass
class DemandResult:
    niche_name: str
    dna_slug: str

    search_volume: TaggedValue
    head_term_volume: TaggedValue
    commercial_intent: TaggedValue
    keyword_difficulty: TaggedValue
    cpc: TaggedValue
    seasonality: TaggedValue
    trend_direction: TaggedValue
    long_tail_depth: TaggedValue
    question_demand: TaggedValue
    local_search_strength: TaggedValue
    serp_competition: TaggedValue

    intent_cluster: IntentCluster

    overall_demand_score: float
    demand_components: list[DemandComponent]
    demand_formula: str

    confidence: float
    data_source: str
    providers_used: list[str]
    verified_fields: list[str]
    estimated_fields: list[str]
    unknown_fields: list[str]
    notes: list[str]

    def to_ctx_patch(self) -> dict:
        return {
            "demand_result": self,
            "demand_score": self.overall_demand_score,
            "demand_search_volume": self.search_volume.value,
            "demand_commercial_intent": self.commercial_intent.value,
            "demand_cpc_usd": self.cpc.value,
            "demand_keyword_difficulty": self.keyword_difficulty.value,
            "demand_confidence": self.confidence,
            "demand_data_source": self.data_source,
        }

    def to_scout_overlay(self) -> "_ScoutDemandOverlay":
        return _ScoutDemandOverlay(self)


class _ScoutDemandOverlay:
    def __init__(self, demand: DemandResult):
        self.estimated_search_volume = demand.search_volume
        self.avg_cpc_usd = demand.cpc
        self.commercial_intent = demand.commercial_intent
        self.advertiser_demand = demand.commercial_intent


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class DemandIntelligence:

    def __init__(self, providers: Optional[list] = None):
        self._providers = providers or [EstimatedDemandProvider()]

    def research(self, niche_name: str, dna: OpportunityDNA, ctx: dict) -> DemandResult:
        outputs, used = [], []

        for p in self._providers:
            try:
                outputs.append(p.research(niche_name, dna, ctx))
                used.append(p.name)
            except Exception as e:
                used.append(f"{p.name}[FAILED:{type(e).__name__}]")

        merged = merge_demand_outputs(outputs)
        cluster = self._build_cluster(niche_name, dna, merged)
        return self._synthesise(niche_name, dna, merged, cluster, used)

    def _build_cluster(self, niche_name: str, dna: OpportunityDNA, data: DemandProviderOutput):
        n = niche_name.lower()
        notes = []
        raw = []

        raw.append((n, "head", _SHARE_HEAD, "head term"))

        for src, dst in _SYNONYM_SWAPS:
            if src in n:
                raw.append((n.replace(src, dst), "synonym", _SHARE_SYNONYM, "swap"))

        for p in _COMMERCIAL_PREFIXES:
            raw.append((f"{p} {n}", "commercial", _SHARE_COMMERCIAL, "commercial"))

        head_vol = data.head_term_volume.value if data.head_term_volume else 0
        cluster_vol = int(head_vol / _SHARE_HEAD) if head_vol else 0

        variants = [
            IntentVariant(
                keyword=k,
                variant_type=t,
                share_weight=w,
                estimated_share=w / sum(x[2] for x in raw),
                estimated_monthly_volume=int(cluster_vol * (w / sum(x[2] for x in raw))),
                derivation=d
            )
            for k, t, w, d in raw
        ]

        return IntentCluster(
            head_term=n,
            variants=variants,
            cluster_monthly_volume=cluster_vol,
            head_share=_SHARE_HEAD,
            variant_count=len(variants),
            derivation_notes=notes
        )

    def _synthesise(self, niche_name, dna, data, cluster, used):

        volume = data.search_volume or _estimated(0)
        ci = data.commercial_intent or _estimated(50)
        kd = data.keyword_difficulty or _estimated(50)
        cpc = data.cpc or _estimated(0)

        overall = min(100, volume.value * 0.001 + ci.value * 0.5)

        return DemandResult(
            niche_name=niche_name,
            dna_slug=dna.slug,
            search_volume=volume,
            head_term_volume=data.head_term_volume,
            commercial_intent=ci,
            keyword_difficulty=kd,
            cpc=cpc,
            seasonality=data.seasonality,
            trend_direction=data.trend_direction,
            long_tail_depth=data.long_tail_depth,
            question_demand=data.question_demand,
            local_search_strength=data.local_search_strength,
            serp_competition=data.serp_competition,
            intent_cluster=cluster,
            overall_demand_score=overall,
            demand_components=[],
            demand_formula="simplified",
            confidence=70.0,
            data_source="estimated",
            providers_used=used,
            verified_fields=[],
            estimated_fields=[],
            unknown_fields=[],
            notes=[]
        )


def run_demand_intelligence(niche_name, dna, ctx, providers=None):
    engine = DemandIntelligence(providers)
    return engine.research(niche_name, dna, ctx)


def demand_result_to_dict(result: DemandResult) -> dict:
    return {
        "niche_name": result.niche_name,
        "dna_slug": result.dna_slug,
        "overall_demand_score": result.overall_demand_score,
        "cluster_size": result.intent_cluster.cluster_monthly_volume,
    }
"""
competition_intelligence.py — Competition Intelligence Engine.

One of the independent providers Scout orchestrates:

    Scout
      ├── Business Intelligence
      ├── Demand Intelligence        (not implemented yet — reserved)
      ├── Competition Intelligence   ← this module
      └── Monetization Intelligence

Single responsibility:
    Competition Intelligence answers exactly one question:
        "How contested is this market?"
    It measures competition_score, directory_strength, authority,
    market_saturation, and organic_competition — as raw evidence about
    the current competitive landscape. It NEVER decides whether that
    competition is a good or bad reason to build; that judgement belongs
    to Business Architect and the scoring engines downstream.

    Note: "competition_score" here is a MEASUREMENT (how competitive is
    the space, 0-100) — not an Opportunity Score, Build Score, or
    Investment Grade. Emitting a number called "competition_score" is
    not the same as making an investment decision; it is one observed
    fact among several that a decision-maker downstream will weigh.

Architecture: identical pattern to business_intelligence.py.
    Provider Protocol, ProviderOutput, merge function (VERIFIED >
    ESTIMATED > UNKNOWN), EstimatedCompetitionIntelligenceProvider
    (deterministic today), real providers plug in without touching
    anything downstream.

Future providers (documented, not implemented):
    SemrushProvider  — domain authority, organic competition (VERIFIED)
    AhrefsProvider   — backlink-derived authority, SERP competition
    BrightLocalProvider — local pack saturation, directory strength
    CommonCrawlProvider — incumbent directory census

This module NEVER computes a Build Score, Investment Grade, or any
composite decision-oriented number. It returns evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from .dna.schema import OpportunityDNA, Intensity
from .scout_providers import DataSource, TaggedValue, _estimated, _unknown


# ─────────────────────────────────────────────────────────────────────────────
# Provider output
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CompetitionIntelligenceOutput:
    provider_name: str

    competition_score:    Optional[TaggedValue] = None   # 0-100, higher = harder
    directory_strength:   Optional[TaggedValue] = None   # 0-100, incumbent directory quality
    authority:            Optional[TaggedValue] = None   # 0-100, domain-authority proxy
    market_saturation:    Optional[TaggedValue] = None   # 0-100, how crowded
    organic_competition:  Optional[TaggedValue] = None   # 0-100, SERP-specific difficulty


@runtime_checkable
class CompetitionIntelligenceProvider(Protocol):
    @property
    def name(self) -> str:
        ...

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> CompetitionIntelligenceOutput:
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Merging
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_PRIORITY = {DataSource.VERIFIED: 3, DataSource.ESTIMATED: 2, DataSource.UNKNOWN: 1}


def _best(a: Optional[TaggedValue], b: Optional[TaggedValue]) -> Optional[TaggedValue]:
    if a is None:
        return b
    if b is None:
        return a
    return a if _SOURCE_PRIORITY[a.source] >= _SOURCE_PRIORITY[b.source] else b


def merge_competition_outputs(
        outputs: list[CompetitionIntelligenceOutput]) -> CompetitionIntelligenceOutput:
    merged = CompetitionIntelligenceOutput(provider_name="merged")
    for out in outputs:
        merged.competition_score   = _best(merged.competition_score,   out.competition_score)
        merged.directory_strength  = _best(merged.directory_strength,  out.directory_strength)
        merged.authority           = _best(merged.authority,           out.authority)
        merged.market_saturation   = _best(merged.market_saturation,   out.market_saturation)
        merged.organic_competition = _best(merged.organic_competition, out.organic_competition)
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Estimated provider
# ─────────────────────────────────────────────────────────────────────────────

_INTENSITY_NUM = {
    Intensity.EXTREME:   98, Intensity.VERY_HIGH: 85,
    Intensity.HIGH:      68, Intensity.MEDIUM:    50,
    Intensity.LOW:       30, Intensity.VERY_LOW:  12,
}


def _int(i: Optional[Intensity], default: float = 50.0) -> float:
    return float(_INTENSITY_NUM.get(i, default)) if i is not None else default


# Competition breadth model: broader (fewer-word) niches are more
# contested. Each additional word signals specificity, which relieves
# competition. Aggregator-dominated categories add a fixed penalty.
_BREADTH_BASE       = 78.0
_WORD_RELIEF        = 8.0
_FLOOR              = 12.0
_AGGREGATOR_BOOST   = 14.0
_AGGREGATOR_SIGNALS = [
    "restaurant", "hotel", "dentist", "doctor", "lawyer",
    "attorney", "contractor", "gym", "plumber", "realtor",
]

# Directory strength / authority scale inversely with niche specificity —
# broad categories tend to have more established, higher-authority
# incumbent directories; narrow niches tend to be thin or unserved.
_AUTHORITY_BASE       = 55.0
_AUTHORITY_WORD_DECAY = 7.0
_DIR_STRENGTH_BASE       = 50.0
_DIR_STRENGTH_WORD_DECAY = 6.0

# Market saturation: blends directory strength with review_importance
# (review-dominated categories are typically saturated by Yelp/Google).
_SATURATION_STRENGTH_WEIGHT = 0.60
_SATURATION_REVIEW_WEIGHT   = 0.40


class EstimatedCompetitionIntelligenceProvider:
    """Deterministic inference from niche text + DNA. All outputs ESTIMATED."""

    _NAME = "EstimatedCompetitionIntelligenceProvider"

    @property
    def name(self) -> str:
        return self._NAME

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> CompetitionIntelligenceOutput:
        out = CompetitionIntelligenceOutput(provider_name=self._NAME)
        n  = niche_name.lower()
        wc = len(niche_name.split())
        depth = int(ctx.get("drill_depth", 0))

        # ── Competition score ──────────────────────────────────────────────
        agg_hit = any(s in n for s in _AGGREGATOR_SIGNALS)
        comp = max(_FLOOR, _BREADTH_BASE - (wc - 1) * _WORD_RELIEF)
        if agg_hit:
            comp = min(96.0, comp + _AGGREGATOR_BOOST)
        depth_relief = min(depth * 7.0, 28.0)
        comp = round(max(_FLOOR, comp - depth_relief), 1)
        out.competition_score = _estimated(
            comp, self._NAME,
            f"breadth {_BREADTH_BASE:.0f} − {wc-1}×{_WORD_RELIEF:.0f}"
            f"{' + aggregator ' + format(_AGGREGATOR_BOOST, '.0f') if agg_hit else ''}"
            f" − depth relief {depth_relief:.0f} = {comp}")

        # ── Authority (domain-authority proxy of incumbents) ──────────────
        authority = max(15.0, _AUTHORITY_BASE - (wc - 1) * _AUTHORITY_WORD_DECAY)
        out.authority = _estimated(
            round(authority, 1), self._NAME,
            f"{_AUTHORITY_BASE:.0f} − {wc-1}×{_AUTHORITY_WORD_DECAY:.0f} "
            f"= {authority:.0f}/100 (narrower niches → lower incumbent authority)")

        # ── Directory strength (quality of incumbent directories) ─────────
        dir_strength = max(18.0, _DIR_STRENGTH_BASE - (wc - 1) * _DIR_STRENGTH_WORD_DECAY)
        out.directory_strength = _estimated(
            round(dir_strength, 1), self._NAME,
            f"{_DIR_STRENGTH_BASE:.0f} − {wc-1}×{_DIR_STRENGTH_WORD_DECAY:.0f} "
            f"= {dir_strength:.0f}/100")

        # ── Market saturation ──────────────────────────────────────────────
        ri = _int(dna.intent.review_importance if dna.intent else None)
        saturation = (dir_strength * _SATURATION_STRENGTH_WEIGHT
                       + ri * _SATURATION_REVIEW_WEIGHT)
        out.market_saturation = _estimated(
            round(saturation, 1), self._NAME,
            f"dir_strength {dir_strength:.0f}×{_SATURATION_STRENGTH_WEIGHT} + "
            f"review_importance {ri:.0f}×{_SATURATION_REVIEW_WEIGHT} "
            f"= {saturation:.1f}/100")

        # ── Organic (SERP-specific) competition ────────────────────────────
        # Slightly softer than the raw competition score — directories can
        # rank for long-tail SERP variants faster than head terms.
        organic = round(comp * 0.90, 1)
        out.organic_competition = _estimated(
            organic, self._NAME,
            f"competition_score {comp} × 0.90 (long-tail SERP softener) = {organic}")

        return out


# ─────────────────────────────────────────────────────────────────────────────
# Result — evidence only, no scoring
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CompetitionIntelligenceResult:
    """Pure evidence about the competitive landscape. No scores, grades,
    or recommendations — those belong to Business Architect."""
    competition_score:    TaggedValue
    directory_strength:   TaggedValue
    authority:            TaggedValue
    market_saturation:    TaggedValue
    organic_competition:  TaggedValue

    providers_used:   list[str]
    verified_fields:  list[str]
    estimated_fields: list[str]
    unknown_fields:   list[str]


class CompetitionIntelligence:
    """Stateless orchestrator over registered Competition Intelligence providers."""

    def __init__(self, providers: Optional[list] = None):
        self._providers = providers if providers is not None else [
            EstimatedCompetitionIntelligenceProvider()]

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> CompetitionIntelligenceResult:
        outputs, used = [], []
        for provider in self._providers:
            try:
                outputs.append(provider.research(niche_name, dna, ctx))
                used.append(provider.name)
            except Exception as e:
                used.append(f"{provider.name}[FAILED:{type(e).__name__}]")

        merged = merge_competition_outputs(outputs)
        fields = {
            "competition_score":   merged.competition_score   or _unknown("competition_score"),
            "directory_strength":  merged.directory_strength  or _unknown("directory_strength"),
            "authority":           merged.authority           or _unknown("authority"),
            "market_saturation":   merged.market_saturation   or _unknown("market_saturation"),
            "organic_competition": merged.organic_competition or _unknown("organic_competition"),
        }
        verified_f  = [k for k, v in fields.items() if v.is_verified]
        estimated_f = [k for k, v in fields.items() if v.is_estimated]
        unknown_f   = [k for k, v in fields.items() if v.is_unknown]

        return CompetitionIntelligenceResult(
            competition_score=fields["competition_score"],
            directory_strength=fields["directory_strength"],
            authority=fields["authority"],
            market_saturation=fields["market_saturation"],
            organic_competition=fields["organic_competition"],
            providers_used=used,
            verified_fields=verified_f,
            estimated_fields=estimated_f,
            unknown_fields=unknown_f,
        )


_default_engine = CompetitionIntelligence()


def run_competition_intelligence(niche_name: str, dna: OpportunityDNA, ctx: dict,
                                   providers: Optional[list] = None) -> CompetitionIntelligenceResult:
    """Run Competition Intelligence for one niche. providers=None uses the
    default EstimatedCompetitionIntelligenceProvider."""
    engine = CompetitionIntelligence(providers) if providers is not None else _default_engine
    return engine.research(niche_name, dna, ctx)


def competition_intelligence_to_dict(result: CompetitionIntelligenceResult) -> dict:
    def tv(t: TaggedValue) -> dict:
        return {"value": t.value, "source": t.source.value, "provider": t.provider,
                 "rationale": t.rationale, "confidence": t.confidence}
    return {
        "competition_score": tv(result.competition_score),
        "directory_strength": tv(result.directory_strength),
        "authority": tv(result.authority),
        "market_saturation": tv(result.market_saturation),
        "organic_competition": tv(result.organic_competition),
        "providers_used": result.providers_used,
        "verified_fields": result.verified_fields,
        "estimated_fields": result.estimated_fields,
        "unknown_fields": result.unknown_fields,
    }

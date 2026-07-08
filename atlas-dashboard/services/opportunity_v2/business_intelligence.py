"""
business_intelligence.py — Business Intelligence Engine.

One of the independent providers Scout orchestrates in the Atlas
Investment OS:

    Scout
      ├── Business Intelligence     ← this module
      ├── Demand Intelligence      (not implemented yet — reserved)
      ├── Competition Intelligence
      └── Monetization Intelligence

Single responsibility:
    Business Intelligence answers exactly one question:
        "What does the population of real businesses in this market
         look like?"
    It measures business_count, review_count, rating_average,
    geographic_coverage, and directory_presence. It NEVER scores,
    grades, or recommends anything — those judgements belong to
    Business Architect and the scoring engines downstream.

Architecture:
    Identical pattern to scout_providers.py / demand_providers.py:
    - A provider Protocol other implementations can satisfy.
    - A ProviderOutput dataclass of optional TaggedValue fields.
    - merge_business_outputs() — VERIFIED > ESTIMATED > UNKNOWN per field.
    - EstimatedBusinessIntelligenceProvider — deterministic inference from
      DNA + niche text. Ships today. All outputs ESTIMATED.

Future providers (documented, not implemented):
    GoogleBusinessProvider — Google Business Profile API → business_count,
        review_count, rating_average (VERIFIED)
    GoogleMapsProvider     — Places API / Nearby Search → business_count,
        geographic_coverage (VERIFIED)
    YelpFusionProvider     — Yelp Fusion API → review_count, rating_average
    DataAxleProvider       — Data Axle business database → business_count,
        directory_presence

This module NEVER computes a Build Score, Investment Grade, or any
composite decision-oriented number. It returns evidence only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from .dna.schema import OpportunityDNA, Intensity
from .scout_providers import DataSource, TaggedValue, _estimated, _unknown


# ─────────────────────────────────────────────────────────────────────────────
# Verification Level Logic
# ─────────────────────────────────────────────────────────────────────────────

def compute_verification_level(google_result: Optional[dict]) -> str:
    """
    Converts Google + Scout signals into REAL classification.
    """
    if not google_result:
        return "HEURISTIC"

    business_count = google_result.get("business_count", 0)
    # Note: avg_rating not used in logic but present in Google result dict
    review_count = google_result.get("average_review_count", 0)

    # -----------------------------
    # VERIFIED RULE
    # -----------------------------
    if business_count >= 10 and review_count >= 50:
        return "VERIFIED"

    # -----------------------------
    # BUILD RULE
    # -----------------------------
    if business_count >= 5 and review_count >= 20:
        return "BUILD"

    # -----------------------------
    # DEFAULT SAFETY STATE
    # -----------------------------
    return "HEURISTIC"


# ─────────────────────────────────────────────────────────────────────────────
# Provider output
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BusinessIntelligenceOutput:
    """All fields optional — providers populate only what their data
    source actually covers."""
    provider_name: str

    business_count:        Optional[TaggedValue] = None   # absolute count
    review_count:          Optional[TaggedValue] = None   # avg reviews per business
    rating_average:        Optional[TaggedValue] = None   # 0-5 stars
    geographic_coverage:   Optional[TaggedValue] = None   # 0-100, breadth of geo spread
    directory_presence:    Optional[TaggedValue] = None   # 0-100, how listed businesses
                                                          # already are in directories


@runtime_checkable
class BusinessIntelligenceProvider(Protocol):
    """Interface every Business Intelligence provider implements. Stateless."""

    @property
    def name(self) -> str:
        ...

    def research(self, niche_name: str, dna: OpportunityDNA,
                 ctx: dict) -> BusinessIntelligenceOutput:
        """Return what this provider knows. Fields it cannot populate stay
        None. Must not raise — return an empty output on internal error."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Merging — VERIFIED > ESTIMATED > UNKNOWN, per field
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_PRIORITY = {DataSource.VERIFIED: 3, DataSource.ESTIMATED: 2, DataSource.UNKNOWN: 1}


def _best(a: Optional[TaggedValue], b: Optional[TaggedValue]) -> Optional[TaggedValue]:
    if a is None:
        return b
    if b is None:
        return a
    return a if _SOURCE_PRIORITY[a.source] >= _SOURCE_PRIORITY[b.source] else b


def merge_business_outputs(outputs: list[BusinessIntelligenceOutput]) -> BusinessIntelligenceOutput:
    merged = BusinessIntelligenceOutput(provider_name="merged")
    for out in outputs:
        merged.business_count      = _best(merged.business_count,       out.business_count)
        merged.review_count        = _best(merged.review_count,         out.review_count)
        merged.rating_average      = _best(merged.rating_average,       out.rating_average)
        merged.geographic_coverage = _best(merged.geographic_coverage, out.geographic_coverage)
        merged.directory_presence  = _best(merged.directory_presence,   out.directory_presence)
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Estimated provider — deterministic inference, ships today
# ─────────────────────────────────────────────────────────────────────────────

_INTENSITY_NUM = {
    Intensity.EXTREME:   98, Intensity.VERY_HIGH: 85,
    Intensity.HIGH:      68, Intensity.MEDIUM:    50,
    Intensity.LOW:       30, Intensity.VERY_LOW:  12,
}


def _int(i: Optional[Intensity], default: float = 50.0) -> float:
    return float(_INTENSITY_NUM.get(i, default)) if i is not None else default


# Business count model: DNA ecosystem node supply_intensity → exponential
# count, attenuated by niche specificity (word count).
_SUPPLY_EXPONENT_SCALE    = 2.7
_SUPPLY_SPECIFICITY_DECAY = 0.60
_SUPPLY_FALLBACK_BASE     = 300

# Review volume proxy by DNA review_importance — how many reviews the
# average business in this category tends to carry.
_REVIEWS_BY_IMPORTANCE = {
    Intensity.EXTREME:   180, Intensity.VERY_HIGH: 95,
    Intensity.HIGH:       45, Intensity.MEDIUM:    18,
    Intensity.LOW:         8, Intensity.VERY_LOW:   3,
}

# Rating average proxy: higher review_importance markets tend to be more
# reviewed AND more competitively rated (businesses that survive review
# scrutiny cluster higher).
_RATING_HIGH_REVIEW_MARKET = 4.1
_RATING_LOW_REVIEW_MARKET  = 3.9

# Geographic coverage: driven by whether DNA declares a geography-producing
# search dimension
_GEO_DIMENSION_KEYWORDS = ["destination", "location", "city", "region", "area", "metro"]
_GEO_BASE_WITH_DIMENSION     = 62.0
_GEO_BASE_WITHOUT_DIMENSION = 28.0

# Directory presence: how much of this market is already listed somewhere
_DIRECTORY_PRESENCE_BASE = 35.0
_DIRECTORY_PRESENCE_CI_WEIGHT = 0.55


class EstimatedBusinessIntelligenceProvider:
    """Deterministic inference from niche text + DNA. All outputs ESTIMATED."""

    _NAME = "EstimatedBusinessIntelligenceProvider"

    @property
    def name(self) -> str:
        return self._NAME

    def research(self, niche_name: str, dna: OpportunityDNA,
                 ctx: dict) -> BusinessIntelligenceOutput:
        out = BusinessIntelligenceOutput(provider_name=self._NAME)
        n  = niche_name.lower()
        wc = len(niche_name.split())

        # ── Business count ────────────────────────────────────────────────
        best_node, best_overlap = None, 0
        for node in dna.ecosystem_nodes:
            words = {w for w in node.name.lower().split() if len(w) > 3}
            overlap = sum(1 for w in words if w in n)
            if overlap > best_overlap:
                best_overlap, best_node = overlap, node

        if best_node:
            supply_score = _int(best_node.supply_intensity)
            estimated_count = int(math.pow(10, (supply_score / 100.0) * _SUPPLY_EXPONENT_SCALE))
            specificity = math.pow(_SUPPLY_SPECIFICITY_DECAY, max(0, wc - 2))
            estimated_count = max(5, int(estimated_count * specificity))
            out.business_count = _estimated(
                float(estimated_count), self._NAME,
                f"DNA node '{best_node.name}' supply_intensity="
                f"{best_node.supply_intensity.value} → base count "
                f"× specificity {specificity:.2f} = {estimated_count}",
                confidence=55.0 if best_overlap >= 2 else 40.0)
        else:
            estimated_count = max(5, int(_SUPPLY_FALLBACK_BASE * math.pow(0.55, max(0, wc - 1))))
            out.business_count = _estimated(
                float(estimated_count), self._NAME,
                f"No DNA ecosystem node matched — word-count fallback: "
                f"{_SUPPLY_FALLBACK_BASE} × 0.55^{max(0, wc-1)} ≈ {estimated_count}",
                confidence=25.0)

        # ── Review count (avg per business) ───────────────────────────────
        ri = dna.intent.review_importance if dna.intent else None
        review_count = float(_REVIEWS_BY_IMPORTANCE.get(ri, 18))
        out.review_count = _estimated(
            review_count, self._NAME,
            f"DNA review_importance={ri.value if ri else 'n/a'} → "
            f"{review_count:.0f} reviews/business (category proxy)")

        # ── Rating average ────────────────────────────────────────────────
        rating = _RATING_HIGH_REVIEW_MARKET if review_count >= 45.0 else _RATING_LOW_REVIEW_MARKET
        out.rating_average = _estimated(
            rating, self._NAME,
            f"review_importance-driven proxy: "
            f"{'high' if review_count >= 45.0 else 'low'}-review market → {rating}/5")

        # ── Geographic coverage ────────────────────────────────────────────
        has_geo_dim = any(
            any(kw in d.name.lower() for kw in _GEO_DIMENSION_KEYWORDS)
            or d.typically_produces_asset == "geo_category"
            for d in dna.search_dimensions)
        geo = _GEO_BASE_WITH_DIMENSION if has_geo_dim else _GEO_BASE_WITHOUT_DIMENSION
        out.geographic_coverage = _estimated(
            geo, self._NAME,
            f"DNA {'declares' if has_geo_dim else 'does not declare'} a "
            f"geography-producing search dimension → {geo:.0f}/100 coverage proxy")

        # ── Directory presence ─────────────────────────────────────────────
        ci = _int(dna.intent.commercial_intent if dna.intent else None)
        presence = min(100.0, _DIRECTORY_PRESENCE_BASE + ci * _DIRECTORY_PRESENCE_CI_WEIGHT)
        out.directory_presence = _estimated(
            round(presence, 1), self._NAME,
            f"base {_DIRECTORY_PRESENCE_BASE:.0f} + commercial_intent {ci:.0f} × "
            f"{_DIRECTORY_PRESENCE_CI_WEIGHT} = {presence:.0f}/100 "
            f"(higher commercial intent markets are already better-indexed)")

        return out


# ─────────────────────────────────────────────────────────────────────────────
# Result — evidence only, no scoring
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BusinessIntelligenceResult:
    """
    Pure evidence about the business population in a market.
    Contains no scores, grades, or recommendations.
    """
    business_count:      TaggedValue
    review_count:        TaggedValue
    rating_average:      TaggedValue
    geographic_coverage: TaggedValue
    directory_presence:  TaggedValue

    providers_used:  list[str]
    verified_fields:  list[str]
    estimated_fields: list[str]
    unknown_fields:   list[str]


def _classify_fields(fields: dict[str, TaggedValue]) -> tuple[list[str], list[str], list[str]]:
    verified  = [k for k, v in fields.items() if v.is_verified]
    estimated = [k for k, v in fields.items() if v.is_estimated]
    unknown   = [k for k, v in fields.items() if v.is_unknown]
    return verified, estimated, unknown


class BusinessIntelligence:
    """Stateless orchestrator over registered Business Intelligence providers."""

    def __init__(self, providers: Optional[list] = None):
        self._providers = providers if providers is not None else [
            EstimatedBusinessIntelligenceProvider()]

    def research(self, niche_name: str, dna: OpportunityDNA,
                 ctx: dict) -> BusinessIntelligenceResult:
        outputs, used = [], []
        for provider in self._providers:
            try:
                outputs.append(provider.research(niche_name, dna, ctx))
                used.append(provider.name)
            except Exception as e:
                used.append(f"{provider.name}[FAILED:{type(e).__name__}]")

        merged = merge_business_outputs(outputs)
        fields = {
            "business_count":      merged.business_count       or _unknown("business_count"),
            "review_count":        merged.review_count         or _unknown("review_count"),
            "rating_average":      merged.rating_average       or _unknown("rating_average"),
            "geographic_coverage": merged.geographic_coverage or _unknown("geographic_coverage"),
            "directory_presence":  merged.directory_presence   or _unknown("directory_presence"),
        }
        verified_f, estimated_f, unknown_f = _classify_fields(fields)

        return BusinessIntelligenceResult(
            business_count=fields["business_count"],
            review_count=fields["review_count"],
            rating_average=fields["rating_average"],
            geographic_coverage=fields["geographic_coverage"],
            directory_presence=fields["directory_presence"],
            providers_used=used,
            verified_fields=verified_f,
            estimated_fields=estimated_f,
            unknown_fields=unknown_f,
        )


_default_engine = BusinessIntelligence()


def run_business_intelligence(niche_name: str, dna: OpportunityDNA, ctx: dict,
                              providers: Optional[list] = None) -> BusinessIntelligenceResult:
    """Run Business Intelligence for one niche. providers=None uses the
    default EstimatedBusinessIntelligenceProvider."""
    engine = BusinessIntelligence(providers) if providers is not None else _default_engine
    return engine.research(niche_name, dna, ctx)


def business_intelligence_to_dict(result: BusinessIntelligenceResult) -> dict:
    """Serialize to a plain dict for JSON storage."""
    def tv(t: TaggedValue) -> dict:
        return {"value": t.value, "source": t.source.value, "provider": t.provider,
                 "rationale": t.rationale, "confidence": t.confidence}
    return {
        "business_count": tv(result.business_count),
        "review_count": tv(result.review_count),
        "rating_average": tv(result.rating_average),
        "geographic_coverage": tv(result.geographic_coverage),
        "directory_presence": tv(result.directory_presence),
        "providers_used": result.providers_used,
        "verified_fields": result.verified_fields,
        "estimated_fields": result.estimated_fields,
        "unknown_fields": result.unknown_fields,
    }
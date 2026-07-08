"""
Module 1 — Source Planner
=========================

Recommends and ranks data-acquisition strategies for a directory blueprint.

Deterministic: identical BlueprintInput → identical SourcePlan.
All scoring uses named constants; no randomness, no I/O.
"""

from __future__ import annotations

from engines.directory_ingestion.ingestion_models import (
    ENGINE_VERSION,
    BlueprintInput,
    SourcePlan,
    SourceRecommendation,
    SourceType,
)

# ---------------------------------------------------------------------------
# Base scoring matrix (0–100 per dimension). Difficulty/cost are inverted:
# higher = easier / cheaper. Values are editorial constants, reviewed per
# release and versioned with the engine.
# ---------------------------------------------------------------------------

_BASE_SCORES: dict[SourceType, dict[str, int]] = {
    SourceType.GOOGLE_PLACES: dict(
        quality=90, coverage=95, freshness=90, difficulty=55, cost=40, reliability=90
    ),
    SourceType.GOVERNMENT_OPEN_DATA: dict(
        quality=85, coverage=70, freshness=60, difficulty=75, cost=100, reliability=95
    ),
    SourceType.ASSOCIATION_WEBSITE: dict(
        quality=80, coverage=50, freshness=65, difficulty=60, cost=90, reliability=80
    ),
    SourceType.PUBLIC_DIRECTORY: dict(
        quality=60, coverage=80, freshness=55, difficulty=65, cost=85, reliability=60
    ),
    SourceType.CSV_IMPORT: dict(
        quality=70, coverage=40, freshness=50, difficulty=95, cost=100, reliability=75
    ),
    SourceType.USER_SUBMITTED: dict(
        quality=65, coverage=20, freshness=95, difficulty=85, cost=100, reliability=55
    ),
    SourceType.FUTURE_SCRAPER: dict(
        quality=55, coverage=85, freshness=80, difficulty=25, cost=70, reliability=50
    ),
    SourceType.FUTURE_API: dict(
        quality=80, coverage=75, freshness=90, difficulty=35, cost=45, reliability=80
    ),
}

# Weights for the overall score. Sum = 100.
_WEIGHT_QUALITY = 25
_WEIGHT_COVERAGE = 20
_WEIGHT_FRESHNESS = 10
_WEIGHT_DIFFICULTY = 15
_WEIGHT_COST = 15
_WEIGHT_RELIABILITY = 15

# Niche adjustments: if the blueprint's category keywords suggest a
# regulated / licensed niche, government open data gets a coverage bonus.
_REGULATED_KEYWORDS = frozenset(
    {"license", "licensed", "certified", "inspection", "medical", "childcare",
     "daycare", "contractor", "trade", "school", "clinic", "veterinary"}
)
_REGULATED_COVERAGE_BONUS = 20
_MAX_SCORE = 100

_IMPLEMENTED_SOURCES = frozenset(
    {
        SourceType.GOOGLE_PLACES,
        SourceType.GOVERNMENT_OPEN_DATA,
        SourceType.ASSOCIATION_WEBSITE,
        SourceType.PUBLIC_DIRECTORY,
        SourceType.CSV_IMPORT,
        SourceType.USER_SUBMITTED,
    }
)

_RATIONALES: dict[SourceType, str] = {
    SourceType.GOOGLE_PLACES: "Highest coverage and freshness; per-request cost and ToS limits apply.",
    SourceType.GOVERNMENT_OPEN_DATA: "Free, authoritative records; freshness varies by agency.",
    SourceType.ASSOCIATION_WEBSITE: "High-trust niche membership rosters; limited coverage.",
    SourceType.PUBLIC_DIRECTORY: "Broad but noisy; useful for cross-verification.",
    SourceType.CSV_IMPORT: "Immediate ingestion of owned datasets; zero acquisition cost.",
    SourceType.USER_SUBMITTED: "Freshest possible data; requires moderation, slow to accumulate.",
    SourceType.FUTURE_SCRAPER: "Extension point only — not implemented in Phase 3B.",
    SourceType.FUTURE_API: "Extension point only — not implemented in Phase 3B.",
}


class SourcePlanner:
    """Ranks acquisition sources for a given blueprint. Stateless."""

    def plan(self, blueprint: BlueprintInput) -> SourcePlan:
        keywords = self._keyword_set(blueprint)
        regulated = bool(keywords & _REGULATED_KEYWORDS)

        recommendations: list[SourceRecommendation] = []
        for source_type, base in _BASE_SCORES.items():
            coverage = base["coverage"]
            rationale = _RATIONALES[source_type]
            if regulated and source_type == SourceType.GOVERNMENT_OPEN_DATA:
                coverage = min(_MAX_SCORE, coverage + _REGULATED_COVERAGE_BONUS)
                rationale += " Regulated niche detected: licensing records boost coverage."

            overall = self._overall(
                quality=base["quality"],
                coverage=coverage,
                freshness=base["freshness"],
                difficulty=base["difficulty"],
                cost=base["cost"],
                reliability=base["reliability"],
            )
            recommendations.append(
                SourceRecommendation(
                    source_type=source_type,
                    quality_score=base["quality"],
                    coverage_score=coverage,
                    freshness_score=base["freshness"],
                    difficulty_score=base["difficulty"],
                    cost_score=base["cost"],
                    reliability_score=base["reliability"],
                    overall_score=overall,
                    rank=0,  # assigned below
                    rationale=rationale,
                    implemented=source_type in _IMPLEMENTED_SOURCES,
                )
            )

        # Deterministic ordering: overall desc, then enum value asc as tiebreak.
        recommendations.sort(key=lambda r: (-r.overall_score, r.source_type.value))
        ranked = tuple(
            SourceRecommendation(
                source_type=r.source_type,
                quality_score=r.quality_score,
                coverage_score=r.coverage_score,
                freshness_score=r.freshness_score,
                difficulty_score=r.difficulty_score,
                cost_score=r.cost_score,
                reliability_score=r.reliability_score,
                overall_score=r.overall_score,
                rank=i + 1,
                rationale=r.rationale,
                implemented=r.implemented,
            )
            for i, r in enumerate(recommendations)
        )
        return SourcePlan(
            directory_slug=blueprint.directory_slug,
            recommendations=ranked,
            engine_version=ENGINE_VERSION,
        )

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _keyword_set(blueprint: BlueprintInput) -> set[str]:
        words: set[str] = set()
        for kw in blueprint.search_keywords:
            words.update(kw.lower().split())
        for node in blueprint.category_hierarchy:
            words.update(node.name.lower().split())
            for kw in node.keywords:
                words.update(kw.lower().split())
        return words

    @staticmethod
    def _overall(*, quality: int, coverage: int, freshness: int,
                 difficulty: int, cost: int, reliability: int) -> int:
        weighted = (
            quality * _WEIGHT_QUALITY
            + coverage * _WEIGHT_COVERAGE
            + freshness * _WEIGHT_FRESHNESS
            + difficulty * _WEIGHT_DIFFICULTY
            + cost * _WEIGHT_COST
            + reliability * _WEIGHT_RELIABILITY
        )
        return round(weighted / 100)

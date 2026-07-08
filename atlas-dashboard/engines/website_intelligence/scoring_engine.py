"""Deterministic scoring engine for the Website Intelligence subsystem.

Responsibilities (and nothing more):

- weight validation
- category score validation
- weighted overall score computation
- grade mapping
- launch readiness mapping
- stable deterministic IDs

Guarantees:

- No AI. No I/O. No UUIDs. No timestamps. No randomness.
- Identical input -> identical output, byte for byte.
- Stable iteration ordering (always ``SCORE_CATEGORIES`` order).
"""

import hashlib
from typing import Dict, Mapping, NamedTuple, Tuple

from engines.website_intelligence.constants import (
    CATEGORY_WEIGHTS,
    ENGINE_NAME,
    ENGINE_VERSION,
    GRADE_BANDS,
    GRADE_FLOOR,
    READINESS_BANDS,
    READINESS_FLOOR,
    SCORE_CATEGORIES,
    SCORE_MAX,
    SCORE_MIN,
    SCORE_PRECISION,
    WEIGHT_SUM_TOLERANCE,
)

# ---------------------------------------------------------------------------
# Stable IDs
# ---------------------------------------------------------------------------


def stable_id(prefix: str, *parts: str) -> str:
    """Build a stable deterministic identifier from string parts.

    Uses SHA-256 over the joined parts. Identical inputs always produce the
    identical ID. No UUIDs, timestamps, or randomness are involved.
    """
    if not prefix:
        raise ValueError("stable_id prefix must be a non-empty string")
    material = "\x1f".join(parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_weights(weights: Mapping[str, float] = CATEGORY_WEIGHTS) -> None:
    """Validate a category weight mapping.

    Rules:
    - keys must exactly match ``SCORE_CATEGORIES``
    - every weight must be greater than 0 and at most 1
    - weights must sum to exactly 1.0 (within floating point tolerance)

    Raises ``ValueError`` on any violation.
    """
    expected = set(SCORE_CATEGORIES)
    actual = set(weights.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"Weight categories mismatch. Missing: {missing}. Unexpected: {extra}."
        )

    for category in SCORE_CATEGORIES:
        weight = weights[category]
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            raise ValueError(f"Weight for '{category}' must be numeric, got {weight!r}")
        if weight <= 0.0 or weight > 1.0:
            raise ValueError(
                f"Weight for '{category}' must be in (0.0, 1.0], got {weight!r}"
            )

    total = sum(weights[category] for category in SCORE_CATEGORIES)
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise ValueError(f"Weights must sum to 1.0, got {total!r}")


def validate_category_scores(category_scores: Mapping[str, float]) -> None:
    """Validate a category score mapping.

    Rules:
    - keys must exactly match ``SCORE_CATEGORIES``
    - every score must be numeric and within [SCORE_MIN, SCORE_MAX]

    Raises ``ValueError`` on any violation. Scores are never silently
    clamped — out-of-range input is a caller bug, not data to repair.
    """
    expected = set(SCORE_CATEGORIES)
    actual = set(category_scores.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"Score categories mismatch. Missing: {missing}. Unexpected: {extra}."
        )

    for category in SCORE_CATEGORIES:
        score = category_scores[category]
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError(f"Score for '{category}' must be numeric, got {score!r}")
        if score < SCORE_MIN or score > SCORE_MAX:
            raise ValueError(
                f"Score for '{category}' must be in "
                f"[{SCORE_MIN}, {SCORE_MAX}], got {score!r}"
            )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def round_score(value: float) -> float:
    """Round a score to the engine's fixed precision (deterministic)."""
    return round(float(value), SCORE_PRECISION)


def compute_overall_score(
    category_scores: Mapping[str, float],
    weights: Mapping[str, float] = CATEGORY_WEIGHTS,
) -> float:
    """Compute the weighted overall score across all categories.

    Validates both weights and scores before computing. Iterates in stable
    ``SCORE_CATEGORIES`` order so floating point accumulation is identical
    on every run.
    """
    validate_weights(weights)
    validate_category_scores(category_scores)
    total = 0.0
    for category in SCORE_CATEGORIES:
        total += float(category_scores[category]) * float(weights[category])
    return round_score(total)


def grade_for_score(score: float) -> str:
    """Map an overall score to a letter grade (A/B/C/D/F)."""
    _validate_single_score(score)
    for threshold, grade in GRADE_BANDS:
        if score >= threshold:
            return grade
    return GRADE_FLOOR


def launch_readiness_for_score(score: float) -> str:
    """Map an overall score to a launch readiness tier."""
    _validate_single_score(score)
    for threshold, readiness in READINESS_BANDS:
        if score >= threshold:
            return readiness
    return READINESS_FLOOR


def _validate_single_score(score: float) -> None:
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError(f"Score must be numeric, got {score!r}")
    if score < SCORE_MIN or score > SCORE_MAX:
        raise ValueError(
            f"Score must be in [{SCORE_MIN}, {SCORE_MAX}], got {score!r}"
        )


# ---------------------------------------------------------------------------
# Scoring result + engine facade
# ---------------------------------------------------------------------------


class ScoringResult(NamedTuple):
    """Immutable, deterministic result of one scoring pass."""

    engine_name: str
    engine_version: str
    category_scores: Tuple[Tuple[str, float], ...]
    overall_score: float
    grade: str
    launch_readiness: str

    def category_scores_dict(self) -> Dict[str, float]:
        """Return category scores as a dict (stable insertion order)."""
        return dict(self.category_scores)


class ScoringEngine:
    """Stateless facade over the pure scoring functions.

    The future audit engine (Part 2) extracts raw category scores from a
    ``WebsiteAuditInput`` and hands them to this engine. This engine owns
    all score math, grading, and launch readiness classification.
    """

    engine_name = ENGINE_NAME
    engine_version = ENGINE_VERSION

    def score(
        self,
        category_scores: Mapping[str, float],
        weights: Mapping[str, float] = CATEGORY_WEIGHTS,
    ) -> ScoringResult:
        """Score a website from per-category raw scores.

        Validates input, computes the weighted overall score, and maps it to
        a grade and a launch readiness tier. Identical input always yields an
        identical ``ScoringResult``.
        """
        overall = compute_overall_score(category_scores, weights)
        normalized = tuple(
            (category, round_score(category_scores[category]))
            for category in SCORE_CATEGORIES
        )
        return ScoringResult(
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            category_scores=normalized,
            overall_score=overall,
            grade=grade_for_score(overall),
            launch_readiness=launch_readiness_for_score(overall),
        )

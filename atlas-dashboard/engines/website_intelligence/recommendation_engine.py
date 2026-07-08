"""Deterministic recommendation engine for the Website Intelligence subsystem.

AES-005A Part 2.

Consumes ``WebsiteAuditFinding`` contracts and produces
``WebsiteAuditRecommendation`` contracts. This engine answers
"What should be improved?" — never "How do we automatically improve it?"
Execution belongs to downstream work planning and future employees.

Responsibilities (and nothing more):

- finding validation (severity, category, duplicate finding IDs)
- deterministic severity -> priority mapping
- deterministic merging of equivalent findings into one recommendation
- deterministic recommendation IDs, titles, and descriptions
- stable output ordering

Guarantees:

- No AI. No I/O. No persistence. No side effects.
- No UUIDs. No timestamps. No randomness. No generated prose.
- Identical findings -> identical recommendations, byte for byte.
- Output is independent of input ordering.

Contracts and constants come exclusively from AES-005A Part 1. Nothing in
Part 1 is modified by this module.
"""

from typing import Dict, Iterable, List, Tuple

from engines.website_intelligence.constants import (
    ENGINE_NAME,
    ENGINE_VERSION,
    PRIORITIES,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    SCORE_CATEGORIES,
    SEVERITIES,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)
from engines.website_intelligence.models import (
    WebsiteAuditFinding,
    WebsiteAuditRecommendation,
)
from engines.website_intelligence.scoring_engine import stable_id

# ---------------------------------------------------------------------------
# Deterministic mappings (single source of truth for this engine)
# ---------------------------------------------------------------------------

# The Part 1 contract for WebsiteAuditRecommendation permits exactly three
# priorities: HIGH, MEDIUM, LOW. Critical findings therefore map to the
# highest available priority, HIGH.
SEVERITY_PRIORITY_MAP = {
    SEVERITY_CRITICAL: PRIORITY_HIGH,
    SEVERITY_WARNING: PRIORITY_MEDIUM,
    SEVERITY_INFO: PRIORITY_LOW,
}

# Deterministic recommendation title templates. One fixed template per
# severity — no generated prose, ever.
_TITLE_TEMPLATES = {
    SEVERITY_CRITICAL: "Fix critical issue: {title}",
    SEVERITY_WARNING: "Address warning: {title}",
    SEVERITY_INFO: "Consider improvement: {title}",
}

# Deterministic recommendation description template. The only variable
# parts are the merged finding count, the shared finding title, the
# category, and the severity — all taken verbatim from validated input.
_DESCRIPTION_TEMPLATE = (
    "Resolve {count} occurrence(s) of '{title}' in the '{category}' "
    "category (severity: {severity})."
)

# Prefix for recommendation IDs, following the Part 1 stable_id convention.
_RECOMMENDATION_ID_PREFIX = "rec"

# Precomputed stable rank lookups (avoid repeated .index() scans).
_PRIORITY_RANK = {priority: rank for rank, priority in enumerate(PRIORITIES)}
_CATEGORY_RANK = {category: rank for rank, category in enumerate(SCORE_CATEGORIES)}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_findings(findings: Iterable[WebsiteAuditFinding]) -> None:
    """Validate a collection of findings before recommendation generation.

    Rules:
    - every element must be a ``WebsiteAuditFinding``
    - every severity must be one of ``SEVERITIES``
    - every category must be one of ``SCORE_CATEGORIES``
    - a ``finding_id`` may repeat only if the findings are exact duplicates;
      the same ID with different content is a caller bug

    Raises ``ValueError`` on any violation. Findings are never silently
    repaired — invalid input is a caller bug, not data to fix.
    """
    seen: Dict[str, WebsiteAuditFinding] = {}
    for finding in findings:
        if not isinstance(finding, WebsiteAuditFinding):
            raise ValueError(
                f"Every finding must be a WebsiteAuditFinding, got {finding!r}"
            )
        if finding.severity not in SEVERITIES:
            raise ValueError(
                f"Finding '{finding.finding_id}' has unknown severity "
                f"{finding.severity!r}. Expected one of {SEVERITIES}."
            )
        if finding.category not in SCORE_CATEGORIES:
            raise ValueError(
                f"Finding '{finding.finding_id}' has unknown category "
                f"{finding.category!r}. Expected one of {SCORE_CATEGORIES}."
            )
        previous = seen.get(finding.finding_id)
        if previous is not None and previous != finding:
            raise ValueError(
                f"Conflicting findings share finding_id "
                f"'{finding.finding_id}'. Duplicate IDs are only permitted "
                f"for exact duplicate findings."
            )
        seen[finding.finding_id] = finding


# ---------------------------------------------------------------------------
# Deterministic derivations
# ---------------------------------------------------------------------------


def priority_for_severity(severity: str) -> str:
    """Map a finding severity to a recommendation priority.

    CRITICAL -> HIGH, WARNING -> MEDIUM, INFO -> LOW. The mapping is fixed
    and exhaustive over ``SEVERITIES``.
    """
    try:
        return SEVERITY_PRIORITY_MAP[severity]
    except KeyError:
        raise ValueError(
            f"Unknown severity {severity!r}. Expected one of {SEVERITIES}."
        ) from None


def recommendation_id_for(category: str, severity: str, title: str) -> str:
    """Build the stable deterministic ID for a recommendation.

    The ID is derived only from the merge key (category, severity, finding
    title), so equivalent findings always yield the identical ID regardless
    of how many of them merged or what evidence they carried.
    """
    return stable_id(_RECOMMENDATION_ID_PREFIX, category, severity, title)


def recommendation_title_for(severity: str, finding_title: str) -> str:
    """Build the deterministic recommendation title for a finding title."""
    try:
        template = _TITLE_TEMPLATES[severity]
    except KeyError:
        raise ValueError(
            f"Unknown severity {severity!r}. Expected one of {SEVERITIES}."
        ) from None
    return template.format(title=finding_title)


def recommendation_description_for(
    count: int, finding_title: str, category: str, severity: str
) -> str:
    """Build the deterministic recommendation description."""
    if count < 1:
        raise ValueError(f"Finding count must be >= 1, got {count!r}")
    return _DESCRIPTION_TEMPLATE.format(
        count=count, title=finding_title, category=category, severity=severity
    )


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------


def generate_recommendations(
    findings: Tuple[WebsiteAuditFinding, ...],
) -> Tuple[WebsiteAuditRecommendation, ...]:
    """Transform audit findings into deterministic recommendations.

    Behaviour:

    - Findings are validated first (severity, category, ID conflicts).
    - Exact duplicate findings are collapsed to a single finding.
    - Findings sharing the merge key (category, severity, title) merge into
      one recommendation carrying every contributing finding ID.
    - ``finding_ids`` are sorted ascending, so output is independent of
      input ordering.
    - Recommendations are ordered by priority (HIGH, MEDIUM, LOW), then by
      category in ``SCORE_CATEGORIES`` order, then by title, then by
      recommendation ID. The ordering is total and deterministic.

    Identical findings always produce identical recommendations. Empty
    input produces an empty tuple. No side effects. No persistence. No I/O.
    """
    findings = tuple(findings)
    validate_findings(findings)

    # Collapse exact duplicates, then group by merge key.
    # Keyed insertion is order-insensitive because every derived value
    # depends only on the merge key and the sorted set of finding IDs.
    grouped: Dict[Tuple[str, str, str], Dict[str, WebsiteAuditFinding]] = {}
    for finding in findings:
        merge_key = (finding.category, finding.severity, finding.title)
        grouped.setdefault(merge_key, {})[finding.finding_id] = finding

    recommendations: List[WebsiteAuditRecommendation] = []
    for (category, severity, title), members in grouped.items():
        finding_ids = tuple(sorted(members.keys()))
        recommendations.append(
            WebsiteAuditRecommendation(
                recommendation_id=recommendation_id_for(category, severity, title),
                category=category,
                priority=priority_for_severity(severity),
                title=recommendation_title_for(severity, title),
                description=recommendation_description_for(
                    len(finding_ids), title, category, severity
                ),
                finding_ids=finding_ids,
            )
        )

    recommendations.sort(
        key=lambda rec: (
            _PRIORITY_RANK[rec.priority],
            _CATEGORY_RANK[rec.category],
            rec.title,
            rec.recommendation_id,
        )
    )
    return tuple(recommendations)


# ---------------------------------------------------------------------------
# Engine facade
# ---------------------------------------------------------------------------


class RecommendationEngine:
    """Stateless facade over the pure recommendation functions.

    The future work planning engine consumes the recommendations produced
    here and turns them into ``WebsiteWorkOrder`` contracts for future
    employees to execute under operator approval. This engine owns only the
    deterministic findings -> recommendations transformation.
    """

    engine_name = ENGINE_NAME
    engine_version = ENGINE_VERSION

    def recommend(
        self, findings: Tuple[WebsiteAuditFinding, ...]
    ) -> Tuple[WebsiteAuditRecommendation, ...]:
        """Generate recommendations from audit findings.

        Pure passthrough to ``generate_recommendations``. Identical input
        always yields an identical output tuple.
        """
        return generate_recommendations(findings)

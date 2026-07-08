"""Deterministic work order planner for the Website Intelligence subsystem.

AES-005A Part 4.

Consumes ``WebsiteAuditRecommendation`` contracts and produces
``WebsiteWorkOrder`` contracts. This engine answers
"What exact tasks should be queued for execution?" — never
"How is the task executed?" Execution belongs to future AI Employees,
approval belongs to the operator, and publishing belongs to the publisher.

Responsibilities (and nothing more):

- recommendation validation (priority, category, duplicate recommendation IDs)
- deterministic one-to-one recommendation -> work order planning
- deterministic work order IDs, instructions, and acceptance criteria
- stable output ordering
- attaching planned work orders to an audit report (new immutable report)

Guarantees:

- No AI. No I/O. No persistence. No side effects.
- No UUIDs. No timestamps. No randomness. No generated prose.
- Identical recommendations -> identical work orders, byte for byte.
- Output is independent of input ordering.
- Every work order is created with status PENDING. This planner never
  approves, rejects, executes, or publishes anything.

Contracts and constants come exclusively from AES-005A Part 1. Nothing in
Parts 1-3 is modified by this module.
"""

from typing import Dict, Iterable, List, Tuple

import engines.website_intelligence.constants as _constants
from engines.website_intelligence.constants import (
    ENGINE_NAME,
    ENGINE_VERSION,
    PRIORITIES,
    SCORE_CATEGORIES,
    WORK_ORDER_STATUS_PENDING,
)
from engines.website_intelligence.models import (
    WebsiteAuditRecommendation,
    WebsiteAuditReport,
    WebsiteWorkOrder,
)
from engines.website_intelligence.scoring_engine import stable_id

# ---------------------------------------------------------------------------
# Deterministic templates (single source of truth for this engine)
# ---------------------------------------------------------------------------

# Prefix for work order IDs, following the Part 1 stable_id convention.
_WORK_ORDER_ID_PREFIX = "wo"

# Deterministic instruction template. The only variable parts are fields
# taken verbatim from the validated recommendation — no generated prose.
_INSTRUCTION_TEMPLATE = (
    "Execute recommendation '{recommendation_id}' in the '{category}' "
    "category (priority: {priority}). Task: {title}. {description} "
    "Do not modify anything outside the scope of this work order. "
    "Submit the result for operator approval before publishing."
)

# Deterministic acceptance criteria templates. Criterion 2 is emitted only
# when the recommendation carries linked finding IDs.
_CRITERION_RESOLVED_TEMPLATE = (
    "The recommendation '{title}' is fully resolved in the "
    "'{category}' category."
)
_CRITERION_FINDINGS_TEMPLATE = (
    "A re-audit no longer reports the {count} linked finding(s): {finding_ids}."
)
_CRITERION_NO_REGRESSION = (
    "A re-audit reports no new CRITICAL or WARNING findings introduced "
    "by this change."
)

# Precomputed stable rank lookups (avoid repeated .index() scans).
# These are rebuilt from the live module reference so they track any
# environment-specific constant definitions correctly.
_PRIORITY_RANK: Dict[str, int] = {}
_CATEGORY_RANK: Dict[str, int] = {}


def _refresh_ranks() -> None:
    """Rebuild rank lookups from the live constants module.

    Called at the start of any function that needs ranked ordering. This
    guarantees that PRIORITIES and SCORE_CATEGORIES from the live module
    are used regardless of import ordering in the test runner.
    """
    global _PRIORITY_RANK, _CATEGORY_RANK
    _PRIORITY_RANK = {
        priority: rank
        for rank, priority in enumerate(_constants.PRIORITIES)
    }
    _CATEGORY_RANK = {
        category: rank
        for rank, category in enumerate(_constants.SCORE_CATEGORIES)
    }


# Initialise at import time so module-level callers get a valid dict.
_refresh_ranks()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_recommendations(
    recommendations: Iterable[WebsiteAuditRecommendation],
) -> None:
    """Validate a collection of recommendations before work order planning.

    Rules:
    - every element must be a ``WebsiteAuditRecommendation``
    - every priority must be one of ``PRIORITIES``
    - every category must be one of ``SCORE_CATEGORIES``
    - a ``recommendation_id`` may repeat only if the recommendations are
      exact duplicates; the same ID with different content is a caller bug

    Raises ``ValueError`` on any violation. Recommendations are never
    silently repaired — invalid input is a caller bug, not data to fix.
    """
    # Read constants from the live module at call time to guard against
    # stale module-level bindings under full-suite pytest import ordering.
    valid_priorities = _constants.PRIORITIES
    valid_categories = _constants.SCORE_CATEGORIES

    seen: Dict[str, WebsiteAuditRecommendation] = {}
    for recommendation in recommendations:
        if not isinstance(recommendation, WebsiteAuditRecommendation):
            raise ValueError(
                f"Every recommendation must be a WebsiteAuditRecommendation, "
                f"got {recommendation!r}"
            )
        if recommendation.priority not in valid_priorities:
            raise ValueError(
                f"Recommendation '{recommendation.recommendation_id}' has "
                f"unknown priority {recommendation.priority!r}. "
                f"Expected one of {valid_priorities}."
            )
        if recommendation.category not in valid_categories:
            raise ValueError(
                f"Recommendation '{recommendation.recommendation_id}' has "
                f"unknown category {recommendation.category!r}. "
                f"Expected one of {valid_categories}."
            )
        previous = seen.get(recommendation.recommendation_id)
        if previous is not None and previous != recommendation:
            raise ValueError(
                f"Conflicting recommendations share recommendation_id "
                f"'{recommendation.recommendation_id}'. Duplicate IDs are "
                f"only permitted for exact duplicate recommendations."
            )
        seen[recommendation.recommendation_id] = recommendation


def validate_work_orders(work_orders: Iterable[WebsiteWorkOrder]) -> None:
    """Validate a collection of work orders before report attachment.

    Rules:
    - every element must be a ``WebsiteWorkOrder``
    - every priority must be one of ``PRIORITIES``
    - every category must be one of ``SCORE_CATEGORIES``
    - a ``work_order_id`` may repeat only if the work orders are exact
      duplicates; the same ID with different content is a caller bug

    Raises ``ValueError`` on any violation.
    """
    # Read constants from the live module at call time to guard against
    # stale module-level bindings under full-suite pytest import ordering.
    valid_priorities = _constants.PRIORITIES
    valid_categories = _constants.SCORE_CATEGORIES

    seen: Dict[str, WebsiteWorkOrder] = {}
    for work_order in work_orders:
        if not isinstance(work_order, WebsiteWorkOrder):
            raise ValueError(
                f"Every work order must be a WebsiteWorkOrder, "
                f"got {work_order!r}"
            )
        if work_order.priority not in valid_priorities:
            raise ValueError(
                f"Work order '{work_order.work_order_id}' has unknown "
                f"priority {work_order.priority!r}. "
                f"Expected one of {valid_priorities}."
            )
        if work_order.category not in valid_categories:
            raise ValueError(
                f"Work order '{work_order.work_order_id}' has unknown "
                f"category {work_order.category!r}. "
                f"Expected one of {valid_categories}."
            )
        previous = seen.get(work_order.work_order_id)
        if previous is not None and previous != work_order:
            raise ValueError(
                f"Conflicting work orders share work_order_id "
                f"'{work_order.work_order_id}'. Duplicate IDs are only "
                f"permitted for exact duplicate work orders."
            )
        seen[work_order.work_order_id] = work_order


# ---------------------------------------------------------------------------
# Deterministic derivations
# ---------------------------------------------------------------------------


def work_order_id_for(recommendation_id: str) -> str:
    """Build the stable deterministic ID for a work order.

    The ID is derived only from the fulfilled recommendation's ID, so a
    given recommendation always yields the identical work order ID.
    """
    if not recommendation_id:
        raise ValueError("recommendation_id must be a non-empty string")
    return stable_id(_WORK_ORDER_ID_PREFIX, recommendation_id)


def work_order_instructions_for(
    recommendation: WebsiteAuditRecommendation,
) -> str:
    """Build the deterministic execution instructions for a recommendation.

    Every variable part is taken verbatim from the recommendation. No
    generated prose, ever.
    """
    if not isinstance(recommendation, WebsiteAuditRecommendation):
        raise ValueError(
            f"recommendation must be a WebsiteAuditRecommendation, "
            f"got {recommendation!r}"
        )
    return _INSTRUCTION_TEMPLATE.format(
        recommendation_id=recommendation.recommendation_id,
        category=recommendation.category,
        priority=recommendation.priority,
        title=recommendation.title,
        description=recommendation.description,
    )


def acceptance_criteria_for(
    recommendation: WebsiteAuditRecommendation,
) -> Tuple[str, ...]:
    """Build the deterministic acceptance criteria for a recommendation.

    Criteria (in fixed order):

    1. The recommendation is fully resolved in its category.
    2. Every linked finding no longer occurs on re-audit — emitted only
       when the recommendation carries finding IDs. IDs are listed sorted
       ascending, so output is independent of input ordering.
    3. No new CRITICAL or WARNING findings are introduced.
    """
    if not isinstance(recommendation, WebsiteAuditRecommendation):
        raise ValueError(
            f"recommendation must be a WebsiteAuditRecommendation, "
            f"got {recommendation!r}"
        )
    criteria: List[str] = [
        _CRITERION_RESOLVED_TEMPLATE.format(
            title=recommendation.title, category=recommendation.category
        )
    ]
    if recommendation.finding_ids:
        sorted_ids = tuple(sorted(recommendation.finding_ids))
        criteria.append(
            _CRITERION_FINDINGS_TEMPLATE.format(
                count=len(sorted_ids), finding_ids=", ".join(sorted_ids)
            )
        )
    criteria.append(_CRITERION_NO_REGRESSION)
    return tuple(criteria)


def work_order_for(recommendation: WebsiteAuditRecommendation) -> WebsiteWorkOrder:
    """Build the single deterministic work order for one recommendation.

    Category, priority, and title carry over verbatim. Status is always
    PENDING — approval is an operator decision made downstream.
    """
    if not isinstance(recommendation, WebsiteAuditRecommendation):
        raise ValueError(
            f"recommendation must be a WebsiteAuditRecommendation, "
            f"got {recommendation!r}"
        )
    return WebsiteWorkOrder(
        work_order_id=work_order_id_for(recommendation.recommendation_id),
        recommendation_id=recommendation.recommendation_id,
        category=recommendation.category,
        priority=recommendation.priority,
        title=recommendation.title,
        instructions=work_order_instructions_for(recommendation),
        acceptance_criteria=acceptance_criteria_for(recommendation),
        status=WORK_ORDER_STATUS_PENDING,
    )


# ---------------------------------------------------------------------------
# Work order planning
# ---------------------------------------------------------------------------


def plan_work_orders(
    recommendations: Tuple[WebsiteAuditRecommendation, ...],
) -> Tuple[WebsiteWorkOrder, ...]:
    """Transform recommendations into deterministic work orders.

    Behaviour:

    - Recommendations are validated first (priority, category, ID conflicts).
    - Exact duplicate recommendations collapse to a single work order.
    - Exactly one work order is planned per unique recommendation.
    - Work orders are ordered by priority (HIGH, MEDIUM, LOW), then by
      category in ``SCORE_CATEGORIES`` order, then by title, then by
      work order ID. The ordering is total and deterministic.

    Identical recommendations always produce identical work orders. Empty
    input produces an empty tuple. No side effects. No persistence. No I/O.
    """
    recommendations = tuple(recommendations)
    validate_recommendations(recommendations)
    _refresh_ranks()

    # Collapse exact duplicates. Keyed insertion is order-insensitive
    # because every derived value depends only on the recommendation itself.
    unique: Dict[str, WebsiteAuditRecommendation] = {}
    for recommendation in recommendations:
        unique[recommendation.recommendation_id] = recommendation

    work_orders = [
        work_order_for(recommendation) for recommendation in unique.values()
    ]
    work_orders.sort(
        key=lambda work_order: (
            _PRIORITY_RANK[work_order.priority],
            _CATEGORY_RANK[work_order.category],
            work_order.title,
            work_order.work_order_id,
        )
    )
    return tuple(work_orders)


# ---------------------------------------------------------------------------
# Report attachment
# ---------------------------------------------------------------------------


def attach_work_orders(
    report: WebsiteAuditReport,
    work_orders: Tuple[WebsiteWorkOrder, ...],
) -> WebsiteAuditReport:
    """Return a new report carrying the given work orders.

    The Part 1 report contract is frozen, so attachment never mutates —
    it constructs a new ``WebsiteAuditReport`` with every other field
    (including ``report_id``: same audit, same identity) carried over
    verbatim.

    Rules:
    - the report's existing ``work_orders`` must be empty; this planner is
      the single writer of that field and never silently overwrites
    - every work order must be valid (see ``validate_work_orders``)
    - every work order must fulfil a recommendation present on the report

    Raises ``ValueError`` on any violation.
    """
    if not isinstance(report, WebsiteAuditReport):
        raise ValueError(f"report must be a WebsiteAuditReport, got {report!r}")
    if report.work_orders:
        raise ValueError(
            f"Report '{report.report_id}' already carries "
            f"{len(report.work_orders)} work order(s). Attachment never "
            f"overwrites existing work orders."
        )

    work_orders = tuple(work_orders)
    validate_work_orders(work_orders)

    known_recommendation_ids = {
        recommendation.recommendation_id
        for recommendation in report.recommendations
    }
    for work_order in work_orders:
        if work_order.recommendation_id not in known_recommendation_ids:
            raise ValueError(
                f"Work order '{work_order.work_order_id}' fulfils unknown "
                f"recommendation '{work_order.recommendation_id}'. Every "
                f"work order must fulfil a recommendation on the report."
            )

    return WebsiteAuditReport(
        report_id=report.report_id,
        engine_name=report.engine_name,
        engine_version=report.engine_version,
        seo_score=report.seo_score,
        navigation_score=report.navigation_score,
        content_score=report.content_score,
        directory_score=report.directory_score,
        commercial_score=report.commercial_score,
        monetization_score=report.monetization_score,
        ux_score=report.ux_score,
        overall_score=report.overall_score,
        grade=report.grade,
        launch_readiness=report.launch_readiness,
        findings=report.findings,
        recommendations=report.recommendations,
        work_orders=work_orders,
    )


# ---------------------------------------------------------------------------
# Engine facade
# ---------------------------------------------------------------------------


class WorkOrderPlanner:
    """Stateless facade over the pure work order planning functions.

    Future AI Employees consume the work orders produced here and execute
    them under operator approval. This planner owns only the deterministic
    recommendations -> work orders transformation. It never executes,
    approves, publishes, or persists anything.
    """

    engine_name = ENGINE_NAME
    engine_version = ENGINE_VERSION

    def plan(
        self, recommendations: Tuple[WebsiteAuditRecommendation, ...]
    ) -> Tuple[WebsiteWorkOrder, ...]:
        """Plan work orders from recommendations.

        Pure passthrough to ``plan_work_orders``. Identical input always
        yields an identical output tuple.
        """
        return plan_work_orders(recommendations)

    def plan_report(self, report: WebsiteAuditReport) -> WebsiteAuditReport:
        """Plan work orders from a report's own recommendations and attach.

        Returns a new immutable ``WebsiteAuditReport`` whose ``work_orders``
        field carries exactly one work order per recommendation on the
        report. Every other field, including ``report_id``, carries over
        verbatim. The input report is never modified.
        """
        if not isinstance(report, WebsiteAuditReport):
            raise ValueError(
                f"report must be a WebsiteAuditReport, got {report!r}"
            )
        work_orders = plan_work_orders(report.recommendations)
        return attach_work_orders(report, work_orders)

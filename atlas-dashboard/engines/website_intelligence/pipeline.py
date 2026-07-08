"""Deterministic Website Intelligence Pipeline.

AES-005A Part 5.

The pipeline is the single public entry point for the Website Intelligence
subsystem. External Atlas components (Operator, AI Employees, Publisher,
Opportunity Engine, Dashboard) should integrate ONLY through
``WebsiteIntelligencePipeline.run``, never by calling the internal
``AuditEngine``, ``RecommendationEngine``, or ``WorkOrderPlanner``
directly.

Data flow (all delegated — never re-implemented here):

    WebsiteAuditInput
        |
        v
    AuditEngine.audit()                 # findings + scores + report skeleton
        |                               # (internally composes ScoringEngine
        |                               #  and RecommendationEngine)
        v
    WorkOrderPlanner.plan_report()      # attaches work orders
        |
        v
    WebsiteAuditReport

Responsibilities (and nothing more):

- reject invalid ``WebsiteAuditInput``
- delegate audit to ``AuditEngine`` (which itself delegates scoring to the
  ``ScoringEngine`` and recommendation generation to the
  ``RecommendationEngine``)
- delegate work order planning to ``WorkOrderPlanner``
- reject invalid intermediate contracts returned by the engines
- return the final immutable ``WebsiteAuditReport``

Guarantees:

- No AI. No I/O. No persistence. No HTTP. No filesystem writes. No side
  effects. No UUIDs. No timestamps. No randomness. No threading. No async.
- The pipeline duplicates no logic from ``AuditEngine``,
  ``RecommendationEngine``, or ``WorkOrderPlanner``. If those engines
  change later, the pipeline automatically benefits.
- Input models are never modified.
- Identical input -> identical output, byte for byte.

Contracts come exclusively from AES-005A Parts 1-4. Nothing in Parts 1-4
is modified by this module.
"""

from typing import Optional

from engines.website_intelligence.audit_engine import AuditEngine
from engines.website_intelligence.constants import ENGINE_NAME, ENGINE_VERSION
from engines.website_intelligence.models import (
    WebsiteAuditInput,
    WebsiteAuditReport,
)
from engines.website_intelligence.work_order_planner import WorkOrderPlanner


class WebsiteIntelligencePipeline:
    """Deterministic orchestrator for the Website Intelligence subsystem.

    Composes ``AuditEngine`` (which internally composes ``ScoringEngine``
    and ``RecommendationEngine``) with ``WorkOrderPlanner``. Owns no audit,
    scoring, recommendation, or work order planning logic of its own.

    The optional constructor arguments exist so callers can inject
    already-configured engines (for advanced composition or testing).
    Defaults construct fresh, stateless engines — the standard usage.
    """

    engine_name = ENGINE_NAME
    engine_version = ENGINE_VERSION

    def __init__(
        self,
        audit_engine: Optional[AuditEngine] = None,
        work_order_planner: Optional[WorkOrderPlanner] = None,
    ) -> None:
        self._audit_engine = (
            audit_engine if audit_engine is not None else AuditEngine()
        )
        self._work_order_planner = (
            work_order_planner
            if work_order_planner is not None
            else WorkOrderPlanner()
        )

    def run(self, audit_input: WebsiteAuditInput) -> WebsiteAuditReport:
        """Execute the full Website Intelligence pipeline.

        Behaviour:

        - Rejects any ``audit_input`` that is not a ``WebsiteAuditInput``.
        - Delegates to ``AuditEngine.audit`` for findings, scoring, grade,
          launch readiness, and recommendations.
        - Delegates to ``WorkOrderPlanner.plan_report`` to attach work
          orders to the audited report.
        - Rejects any intermediate value that is not a
          ``WebsiteAuditReport``. Invalid intermediates are a
          contract violation, never silently repaired.

        Returns the final immutable ``WebsiteAuditReport``. Identical
        input always yields an identical report — same findings, same
        recommendations, same work orders, same IDs, byte for byte.
        """
        if not isinstance(audit_input, WebsiteAuditInput):
            raise ValueError(
                f"audit_input must be a WebsiteAuditInput, got {audit_input!r}"
            )

        audited_report = self._audit_engine.audit(audit_input)
        if not isinstance(audited_report, WebsiteAuditReport):
            raise ValueError(
                f"AuditEngine must return a WebsiteAuditReport, "
                f"got {audited_report!r}"
            )

        final_report = self._work_order_planner.plan_report(audited_report)
        if not isinstance(final_report, WebsiteAuditReport):
            raise ValueError(
                f"WorkOrderPlanner must return a WebsiteAuditReport, "
                f"got {final_report!r}"
            )

        return final_report

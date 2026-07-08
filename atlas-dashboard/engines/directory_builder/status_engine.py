"""Section 7 — Project Status Engine.

Rolls quality, validation, and queue state into an operator-facing
status: completion percentage, launch readiness, remaining tasks,
critical warnings, per-dimension build progress, and a summary.
"""

from __future__ import annotations

from engines.directory_builder.models import (
    AiBuildQueue,
    ProjectStatus,
    QualityReport,
    ValidationReport,
)
from engines.directory_builder.constants import (
    LAUNCH_NEEDS_WORK_THRESHOLD,
    LAUNCH_READY_THRESHOLD,
    READINESS_NEEDS_WORK,
    READINESS_NOT_READY,
    READINESS_READY,
    SEVERITY_CRITICAL,
)

ENGINE_VERSION = "1.0.0"

MAX_REMAINING_TASKS_LISTED = 25


class ProjectStatusEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def build(
        project_slug: str,
        quality: QualityReport,
        validation: ValidationReport,
        queue: AiBuildQueue,
    ) -> ProjectStatus:
        completion = quality.overall_score

        if not validation.passed:
            readiness = READINESS_NOT_READY
        elif completion >= LAUNCH_READY_THRESHOLD:
            readiness = READINESS_READY
        elif completion >= LAUNCH_NEEDS_WORK_THRESHOLD:
            readiness = READINESS_NEEDS_WORK
        else:
            readiness = READINESS_NOT_READY

        remaining = tuple(
            f"[P{unit.priority}] {unit.title}" for unit in queue.units[:MAX_REMAINING_TASKS_LISTED]
        )
        critical_warnings = tuple(
            issue.message for issue in validation.issues if issue.severity == SEVERITY_CRITICAL
        )

        build_progress = (
            ("seo", quality.seo_score),
            ("content", quality.content_score),
            ("import", quality.import_score),
            ("completeness", quality.completeness_score),
            ("automation", quality.automation_readiness),
            ("launch", quality.launch_readiness_score),
        )

        summary = (
            f"Project '{project_slug}' assembled at {completion}% overall quality (grade {quality.grade}). "
            f"Readiness: {readiness}. {validation.critical_count} critical issue(s), "
            f"{validation.warning_count} warning(s). {len(queue.units)} AI work unit(s) queued."
        )

        return ProjectStatus(
            project_slug=project_slug,
            completion_percentage=completion,
            launch_readiness=readiness,
            remaining_tasks=remaining,
            critical_warnings=critical_warnings,
            build_progress=build_progress,
            operator_summary=summary,
        )

from __future__ import annotations

from acdis.contracts.placeholders import EvidenceType

from .builder import ReviewReport, build_review_report
from .models import ComparisonObservation, ReviewCaseFile, ReviewObservationState, ReviewQuestionStatus


def _render_list(items: tuple[str, ...]) -> str:
    if not items:
        return "Not supplied"
    return "\n".join(f"- {item}" for item in items)


def _show(value: str | None) -> str:
    if value is None or not value.strip():
        return "Not supplied"
    return value


def _render_research_question_lines(case: ReviewCaseFile) -> list[str]:
    if not case.research_questions:
        return ["Not supplied"]

    lines: list[str] = []
    for question in case.research_questions:
        lines.append(f"- [{question.question_id}] {question.question_text}")
        lines.append(f"  - Status: {question.status.value}")
        lines.append(
            f"  - Related evidence IDs: {', '.join(question.related_evidence_ids) if question.related_evidence_ids else 'Not supplied'}"
        )
        lines.append(
            f"  - Related competitor IDs: {', '.join(question.related_competitor_ids) if question.related_competitor_ids else 'Not supplied'}"
        )
        lines.append(f"  - Notes: {_show(question.operator_notes)}")
    return lines


def _render_matrix(report: ReviewReport) -> list[str]:
    case = report.review_case
    if not case.comparison_dimensions:
        return ["Not supplied"]

    header = ["| Competitor | " + " | ".join(dimension.label for dimension in case.comparison_dimensions) + " |"]
    divider = ["| --- | " + " | ".join("---" for _ in case.comparison_dimensions) + " |"]

    rows: list[str] = []
    for row in report.matrix_rows:
        cells: list[str] = []
        for cell in row.cells:
            if cell.state is None:
                cells.append("Not supplied")
                continue
            evidence = ", ".join(cell.evidence_ids) if cell.evidence_ids else "Not supplied"
            cells.append(f"{cell.state.value}; obs={cell.observation_id}; ev={evidence}")
        rows.append(f"| {row.competitor_id} ({row.competitor_name}) | " + " | ".join(cells) + " |")

    return header + divider + rows


def _render_observation_lines(observations: tuple[ComparisonObservation, ...]) -> list[str]:
    if not observations:
        return ["Not supplied"]

    lines: list[str] = []
    for observation in observations:
        lines.append(
            f"- [{observation.observation_id}] competitor={observation.competitor_id}; dimension={observation.dimension_id}; state={observation.state.value}"
        )
        lines.append(f"  - Statement: {observation.statement}")
        lines.append(
            "  - Supporting evidence IDs: "
            + (", ".join(observation.supporting_evidence_ids) if observation.supporting_evidence_ids else "Not supplied")
        )
        lines.append(f"  - Notes: {_show(observation.operator_notes)}")
    return lines


def _render_coverage(report: ReviewReport) -> list[str]:
    if not report.coverage:
        return ["Not supplied"]

    lines = [
        "| Competitor ID | Dimension ID | Observation supplied | Observation state | FACT basis | Evidence IDs | Coverage |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.coverage:
        lines.append(
            "| "
            + f"{row.competitor_id} | {row.dimension_id} | {'yes' if row.observation_supplied else 'no'} | "
            + f"{row.observation_state or 'Not supplied'} | {'yes' if row.fact_supported else 'no'} | "
            + f"{', '.join(row.evidence_ids) if row.evidence_ids else 'Not supplied'} | {row.coverage_label} |"
        )
    return lines


def _render_evidence_by_type(case: ReviewCaseFile, evidence_type: EvidenceType) -> list[str]:
    matching = [item for item in case.base_case.evidence if item.evidence_type is evidence_type]
    if not matching:
        return ["Not supplied"]

    lines: list[str] = []
    for item in matching:
        lines.append(f"- [{item.evidence_id}] {item.statement}")
        lines.append(
            f"  - Source references: {', '.join(item.source_references) if item.source_references else 'Not supplied'}"
        )
        lines.append(f"  - Related competitors: {', '.join(item.related_competitor_ids) if item.related_competitor_ids else 'Not supplied'}")
        lines.append(
            f"  - Supporting evidence: {', '.join(item.supporting_evidence_ids) if item.supporting_evidence_ids else 'Not supplied'}"
        )
        lines.append(f"  - Notes: {_show(item.operator_notes)}")
    return lines


def _render_wedge_lines(case: ReviewCaseFile) -> list[str]:
    if not case.wedge_candidates:
        return ["Not supplied"]

    lines: list[str] = []
    for wedge in case.wedge_candidates:
        lines.append(f"- [{wedge.wedge_id}] {wedge.title}")
        lines.append(f"  - Target user: {_show(wedge.target_user)}")
        lines.append(f"  - Payer: {_show(wedge.payer)}")
        lines.append(f"  - User pain: {_show(wedge.user_pain)}")
        lines.append(f"  - Proposed advantage: {_show(wedge.proposed_advantage)}")
        lines.append(f"  - Competitor gap addressed: {_show(wedge.competitor_gap)}")
        lines.append(
            "  - Supporting evidence IDs: "
            + (", ".join(wedge.supporting_evidence_ids) if wedge.supporting_evidence_ids else "Not supplied")
        )
        lines.append(
            "  - Hypothesis evidence IDs: "
            + (", ".join(wedge.hypothesis_evidence_ids) if wedge.hypothesis_evidence_ids else "Not supplied")
        )
        lines.append(f"  - Notes: {_show(wedge.operator_notes)}")
    return lines


def _render_readiness(report: ReviewReport) -> list[str]:
    if not report.wedge_readiness:
        return ["Not supplied"]

    lines = ["Structural test readiness - not an ACDIS business recommendation."]
    for readiness in report.wedge_readiness:
        lines.append(f"- [{readiness.wedge_id}] {readiness.status.value}")
        lines.append(
            "  - Missing requirements: "
            + (", ".join(readiness.missing_requirements) if readiness.missing_requirements else "Not supplied")
        )
        lines.append(
            "  - Invalid evidence basis: "
            + (", ".join(readiness.invalid_evidence_basis) if readiness.invalid_evidence_basis else "Not supplied")
        )
    return lines


def _render_experiment_cards(report: ReviewReport) -> list[str]:
    if not report.experiment_cards:
        return ["Not supplied"]

    lines: list[str] = []
    for card in report.experiment_cards:
        wedge = card.wedge
        readiness = card.readiness
        lines.append(f"### Wedge {wedge.wedge_id}: {wedge.title}")
        lines.append(f"- Target user: {_show(wedge.target_user)}")
        lines.append(f"- Payer: {_show(wedge.payer)}")
        lines.append(f"- Pain: {_show(wedge.user_pain)}")
        lines.append(f"- Proposed advantage: {_show(wedge.proposed_advantage)}")
        lines.append(
            f"- Evidence basis: {', '.join(wedge.supporting_evidence_ids) if wedge.supporting_evidence_ids else 'Not supplied'}"
        )
        lines.append(
            f"- Hypothesis basis: {', '.join(wedge.hypothesis_evidence_ids) if wedge.hypothesis_evidence_ids else 'Not supplied'}"
        )
        lines.append(f"- Smallest manual test: {_show(wedge.smallest_manual_test)}")
        lines.append(f"- Timebox: {_show(wedge.test_timebox)}")
        lines.append(f"- Cost cap: {_show(wedge.cost_cap)}")
        lines.append(f"- Success signal: {_show(wedge.success_signal)}")
        lines.append(f"- Invalidating signal: {_show(wedge.invalidating_signal)}")
        lines.append(f"- Target sample: {_show(wedge.test_participants)}")
        lines.append(f"- Dependencies: {', '.join(wedge.dependencies) if wedge.dependencies else 'Not supplied'}")
        lines.append(
            "- Risks and failure reasons: "
            + (", ".join(wedge.reasons_the_wedge_might_fail) if wedge.reasons_the_wedge_might_fail else "Not supplied")
        )
        lines.append(f"- Next operator action: {_show(wedge.next_operator_action)}")
        lines.append(f"- Readiness status: {readiness.status.value}")
        lines.append(
            "- Missing requirements: "
            + (", ".join(readiness.missing_requirements) if readiness.missing_requirements else "Not supplied")
        )
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _render_outstanding_gaps(report: ReviewReport) -> list[str]:
    case = report.review_case
    question_lines: list[str] = []
    for question in case.research_questions:
        if question.status in {ReviewQuestionStatus.OPEN, ReviewQuestionStatus.PARTIAL}:
            question_lines.append(f"- Research question {question.question_id}: {question.status.value}")

    missing_cells: list[str] = []
    for coverage in report.coverage:
        if coverage.coverage_label == "missing":
            missing_cells.append(
                f"- Missing comparison observation for competitor={coverage.competitor_id}, dimension={coverage.dimension_id}"
            )

    if not question_lines and not missing_cells:
        return ["Not supplied"]

    return question_lines + missing_cells


def _render_next_actions(case: ReviewCaseFile) -> list[str]:
    actions: list[str] = list(case.base_case.next_research_actions)
    for wedge in case.wedge_candidates:
        if wedge.next_operator_action:
            actions.append(wedge.next_operator_action)
    if not actions:
        return ["Not supplied"]
    return [f"- {item}" for item in actions]


def render_review_markdown(case: ReviewCaseFile) -> str:
    report = build_review_report(case)

    sections: list[str] = [
        "# Deterministic competitor comparison and wedge experiment review",
        "",
        "## 1. Case identity",
        "",
        f"- Case ID: {case.base_case.case_id}",
        f"- Case title: {case.base_case.case_title}",
        f"- Operator notes: {_show(case.base_case.operator_notes)}",
        "",
        "## 2. Operator recommendation",
        "",
        f"- Operator recommendation: {_show(case.base_case.operator_recommendation)}",
        f"- Rationale: {_show(case.base_case.operator_recommendation_rationale)}",
        "",
        "## 3. Research-question status",
        "",
    ]
    sections.extend(_render_research_question_lines(case))

    sections.extend([
        "",
        "## 4. Competitor comparison matrix",
        "",
    ])
    sections.extend(_render_matrix(report))

    sections.extend([
        "",
        "## 5. Comparison-observation details",
        "",
    ])
    sections.extend(_render_observation_lines(case.comparison_observations))

    sections.extend([
        "",
        "## 6. Evidence coverage audit",
        "",
    ])
    sections.extend(_render_coverage(report))
    sections.extend([
        "",
        f"- Evidence counts: FACT={report.evidence_counts[EvidenceType.FACT]}, INFERENCE={report.evidence_counts[EvidenceType.INFERENCE]}, HYPOTHESIS={report.evidence_counts[EvidenceType.HYPOTHESIS]}, UNKNOWN={report.evidence_counts[EvidenceType.UNKNOWN]}",
        "",
        "## 7. Verified facts",
        "",
    ])
    sections.extend(_render_evidence_by_type(case, EvidenceType.FACT))

    sections.extend([
        "",
        "## 8. Supported inferences",
        "",
    ])
    sections.extend(_render_evidence_by_type(case, EvidenceType.INFERENCE))

    sections.extend([
        "",
        "## 9. Hypotheses requiring validation",
        "",
    ])
    sections.extend(_render_evidence_by_type(case, EvidenceType.HYPOTHESIS))

    sections.extend([
        "",
        "## 10. Unknowns",
        "",
    ])
    sections.extend(_render_evidence_by_type(case, EvidenceType.UNKNOWN))

    sections.extend([
        "",
        "## 11. Wedge candidates",
        "",
    ])
    sections.extend(_render_wedge_lines(case))

    sections.extend([
        "",
        "## 12. Structural test-readiness results",
        "",
    ])
    sections.extend(_render_readiness(report))

    sections.extend([
        "",
        "## 13. Manual experiment cards",
        "",
    ])
    sections.extend(_render_experiment_cards(report))

    sections.extend([
        "",
        "## 14. Reasons not to pursue",
        "",
    ])
    sections.extend([f"- {item}" for item in case.base_case.reasons_not_to_pursue] if case.base_case.reasons_not_to_pursue else ["Not supplied"])

    sections.extend([
        "",
        "## 15. Outstanding research gaps",
        "",
    ])
    sections.extend(_render_outstanding_gaps(report))

    sections.extend([
        "",
        "## 16. Next operator actions",
        "",
    ])
    sections.extend(_render_next_actions(case))

    sections.extend([
        "",
        "## 17. Evidence appendix",
        "",
    ])
    for evidence in case.base_case.evidence:
        sections.append(f"- [{evidence.evidence_id}] ({evidence.evidence_type.value}) {evidence.statement}")
        sections.append(
            f"  - Source references: {', '.join(evidence.source_references) if evidence.source_references else 'Not supplied'}"
        )
        sections.append(
            f"  - Supporting evidence: {', '.join(evidence.supporting_evidence_ids) if evidence.supporting_evidence_ids else 'Not supplied'}"
        )
        sections.append(
            f"  - Related competitors: {', '.join(evidence.related_competitor_ids) if evidence.related_competitor_ids else 'Not supplied'}"
        )

    sections.extend([
        "",
        "## 18. Integrity statement",
        "",
        "- All competitor states in this report were supplied by the operator.",
        "- ACDIS performed validation and organization only.",
        "- Missing research is not automatically a competitor weakness.",
        "- Readiness is structural completeness, not a business recommendation.",
        "- No score, ranking, market estimate, or autonomous recommendation was produced.",
        "",
    ])

    return "\n".join(sections)

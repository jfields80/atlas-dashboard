from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from acdis.casefiles.loader import CaseFileError, load_case_file
from acdis.casefiles.validation import CaseFileValidationError, validate_case_file
from acdis.contracts.placeholders import EvidenceType

from .models import (
    ComparisonDimension,
    ComparisonObservation,
    EvidenceCoverageStatus,
    ResearchQuestion,
    ReviewCaseFile,
    ReviewObservationState,
    ReviewQuestionStatus,
    ReviewWedgeCandidate,
    ReviewWedgeReadiness,
    ReviewWedgeReadinessStatusValue,
)
from .validation import ReviewValidationError, evidence_type_counts, validate_review_case_file


@dataclass(frozen=True)
class ComparisonMatrixCell:
    competitor_id: str
    dimension_id: str
    state: ReviewObservationState | None
    observation_id: str | None
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonMatrixRow:
    competitor_id: str
    competitor_name: str
    cells: tuple[ComparisonMatrixCell, ...]


@dataclass(frozen=True)
class WedgeExperimentCard:
    wedge: ReviewWedgeCandidate
    readiness: ReviewWedgeReadiness


@dataclass(frozen=True)
class ReviewReport:
    review_case: ReviewCaseFile
    matrix_rows: tuple[ComparisonMatrixRow, ...]
    coverage: tuple[EvidenceCoverageStatus, ...]
    wedge_readiness: tuple[ReviewWedgeReadiness, ...]
    experiment_cards: tuple[WedgeExperimentCard, ...]
    evidence_counts: dict[EvidenceType, int]


def _require_object(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReviewValidationError(f"review field {field_name}: expected object")
    return value


def _require_text(value: Any, field_name: str, object_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewValidationError(f"{object_id} field {field_name}: must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ReviewValidationError("optional text fields must be strings when supplied")
    cleaned = value.strip()
    return cleaned or None


def _optional_string_list(value: Any, field_name: str, object_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ReviewValidationError(f"{object_id} field {field_name}: must be a list")
    values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ReviewValidationError(f"{object_id} field {field_name}: contains blank or non-string item")
        values.append(item.strip())
    return tuple(values)


def _parse_question_status(value: Any, question_id: str) -> ReviewQuestionStatus:
    if not isinstance(value, str):
        raise ReviewValidationError(f"research_question {question_id} field status: unknown status")
    try:
        return ReviewQuestionStatus(value)
    except ValueError as exc:
        raise ReviewValidationError(f"research_question {question_id} field status: unknown status {value}") from exc


def _parse_observation_state(value: Any, observation_id: str) -> ReviewObservationState:
    if not isinstance(value, str):
        raise ReviewValidationError(f"comparison_observation {observation_id} field state: unknown state")
    try:
        return ReviewObservationState(value)
    except ValueError as exc:
        raise ReviewValidationError(f"comparison_observation {observation_id} field state: unknown state {value}") from exc


def _parse_research_questions(review_payload: Mapping[str, Any]) -> tuple[ResearchQuestion, ...]:
    raw_questions = review_payload.get("research_questions")
    if raw_questions is None:
        return ()
    if not isinstance(raw_questions, list):
        raise ReviewValidationError("review field research_questions: must be a list")

    parsed: list[ResearchQuestion] = []
    for item in raw_questions:
        payload = _require_object(item, "research_questions item")
        question_id = _require_text(payload.get("question_id"), "question_id", "research_question")
        parsed.append(
            ResearchQuestion(
                question_id=question_id,
                question_text=_require_text(payload.get("question_text"), "question_text", f"research_question {question_id}"),
                status=_parse_question_status(payload.get("status"), question_id),
                related_evidence_ids=_optional_string_list(payload.get("related_evidence_ids"), "related_evidence_ids", f"research_question {question_id}"),
                related_competitor_ids=_optional_string_list(payload.get("related_competitor_ids"), "related_competitor_ids", f"research_question {question_id}"),
                operator_notes=_optional_text(payload.get("operator_notes")),
            )
        )
    return tuple(parsed)


def _parse_dimensions(review_payload: Mapping[str, Any]) -> tuple[ComparisonDimension, ...]:
    raw_dimensions = review_payload.get("comparison_dimensions")
    if raw_dimensions is None:
        return ()
    if not isinstance(raw_dimensions, list):
        raise ReviewValidationError("review field comparison_dimensions: must be a list")

    parsed: list[ComparisonDimension] = []
    for item in raw_dimensions:
        payload = _require_object(item, "comparison_dimensions item")
        dimension_id = _require_text(payload.get("dimension_id"), "dimension_id", "comparison_dimension")
        parsed.append(
            ComparisonDimension(
                dimension_id=dimension_id,
                label=_require_text(payload.get("label"), "label", f"comparison_dimension {dimension_id}"),
                description=_require_text(payload.get("description"), "description", f"comparison_dimension {dimension_id}"),
                why_it_matters=_require_text(payload.get("why_it_matters"), "why_it_matters", f"comparison_dimension {dimension_id}"),
                operator_notes=_optional_text(payload.get("operator_notes")),
            )
        )
    return tuple(parsed)


def _parse_observations(review_payload: Mapping[str, Any]) -> tuple[ComparisonObservation, ...]:
    raw_observations = review_payload.get("comparison_observations")
    if raw_observations is None:
        return ()
    if not isinstance(raw_observations, list):
        raise ReviewValidationError("review field comparison_observations: must be a list")

    parsed: list[ComparisonObservation] = []
    for item in raw_observations:
        payload = _require_object(item, "comparison_observations item")
        observation_id = _require_text(payload.get("observation_id"), "observation_id", "comparison_observation")
        parsed.append(
            ComparisonObservation(
                observation_id=observation_id,
                competitor_id=_require_text(payload.get("competitor_id"), "competitor_id", f"comparison_observation {observation_id}"),
                dimension_id=_require_text(payload.get("dimension_id"), "dimension_id", f"comparison_observation {observation_id}"),
                state=_parse_observation_state(payload.get("state"), observation_id),
                statement=_require_text(payload.get("statement"), "statement", f"comparison_observation {observation_id}"),
                supporting_evidence_ids=_optional_string_list(payload.get("supporting_evidence_ids"), "supporting_evidence_ids", f"comparison_observation {observation_id}"),
                operator_notes=_optional_text(payload.get("operator_notes")),
            )
        )
    return tuple(parsed)


def _parse_wedges(review_payload: Mapping[str, Any]) -> tuple[ReviewWedgeCandidate, ...]:
    raw_wedges = review_payload.get("wedge_candidates")
    if raw_wedges is None:
        return ()
    if not isinstance(raw_wedges, list):
        raise ReviewValidationError("review field wedge_candidates: must be a list")

    parsed: list[ReviewWedgeCandidate] = []
    for item in raw_wedges:
        payload = _require_object(item, "wedge_candidates item")
        wedge_id = _require_text(payload.get("wedge_id"), "wedge_id", "wedge_candidate")
        parsed.append(
            ReviewWedgeCandidate(
                wedge_id=wedge_id,
                title=_require_text(payload.get("title"), "title", f"wedge_candidate {wedge_id}"),
                target_user=_optional_text(payload.get("target_user")),
                payer=_optional_text(payload.get("payer")),
                user_pain=_optional_text(payload.get("user_pain")),
                proposed_advantage=_optional_text(payload.get("proposed_advantage")),
                competitor_gap=_optional_text(payload.get("competitor_gap")),
                supporting_evidence_ids=_optional_string_list(payload.get("supporting_evidence_ids"), "supporting_evidence_ids", f"wedge_candidate {wedge_id}"),
                hypothesis_evidence_ids=_optional_string_list(payload.get("hypothesis_evidence_ids"), "hypothesis_evidence_ids", f"wedge_candidate {wedge_id}"),
                reasons_the_wedge_might_fail=_optional_string_list(payload.get("reasons_the_wedge_might_fail"), "reasons_the_wedge_might_fail", f"wedge_candidate {wedge_id}"),
                smallest_manual_test=_optional_text(payload.get("smallest_manual_test")),
                test_timebox=_optional_text(payload.get("test_timebox")),
                cost_cap=_optional_text(payload.get("cost_cap")),
                success_signal=_optional_text(payload.get("success_signal")),
                invalidating_signal=_optional_text(payload.get("invalidating_signal")),
                test_participants=_optional_text(payload.get("test_participants")),
                dependencies=_optional_string_list(payload.get("dependencies"), "dependencies", f"wedge_candidate {wedge_id}"),
                next_operator_action=_optional_text(payload.get("next_operator_action")),
                operator_notes=_optional_text(payload.get("operator_notes")),
            )
        )
    return tuple(parsed)


def build_review_case(input_path: str | Path) -> ReviewCaseFile:
    path = Path(input_path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CaseFileError(f"Case file not found: {path}") from exc
    except OSError as exc:
        raise CaseFileError(f"Unable to read case file: {path}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CaseFileError(f"Malformed JSON in case file: {path}") from exc

    if not isinstance(payload, dict):
        raise CaseFileError("Case file root must be a JSON object")

    try:
        validate_case_file(payload)
    except CaseFileValidationError as exc:
        raise CaseFileValidationError(str(exc)) from exc

    base_case = load_case_file(path)

    raw_review = payload.get("review")
    if raw_review is None:
        review_payload: Mapping[str, Any] = {}
    else:
        review_payload = _require_object(raw_review, "review")

    review_case = ReviewCaseFile(
        base_case=base_case,
        research_questions=_parse_research_questions(review_payload),
        comparison_dimensions=_parse_dimensions(review_payload),
        comparison_observations=_parse_observations(review_payload),
        wedge_candidates=_parse_wedges(review_payload),
    )

    validate_review_case_file(review_case)
    return review_case


def _observation_map(case: ReviewCaseFile) -> dict[tuple[str, str], ComparisonObservation]:
    lookup: dict[tuple[str, str], ComparisonObservation] = {}
    for observation in case.comparison_observations:
        lookup[(observation.competitor_id, observation.dimension_id)] = observation
    return lookup


def build_competitor_matrix(case: ReviewCaseFile) -> tuple[ComparisonMatrixRow, ...]:
    lookup = _observation_map(case)
    rows: list[ComparisonMatrixRow] = []

    for competitor in case.base_case.competitors:
        cells: list[ComparisonMatrixCell] = []
        for dimension in case.comparison_dimensions:
            observation = lookup.get((competitor.competitor_id, dimension.dimension_id))
            if observation is None:
                cells.append(
                    ComparisonMatrixCell(
                        competitor_id=competitor.competitor_id,
                        dimension_id=dimension.dimension_id,
                        state=None,
                        observation_id=None,
                        evidence_ids=(),
                    )
                )
            else:
                cells.append(
                    ComparisonMatrixCell(
                        competitor_id=competitor.competitor_id,
                        dimension_id=dimension.dimension_id,
                        state=observation.state,
                        observation_id=observation.observation_id,
                        evidence_ids=observation.supporting_evidence_ids,
                    )
                )
        rows.append(
            ComparisonMatrixRow(
                competitor_id=competitor.competitor_id,
                competitor_name=competitor.name,
                cells=tuple(cells),
            )
        )

    return tuple(rows)


def _is_fact_supported(evidence_lookup: dict[str, Any], evidence_ids: tuple[str, ...]) -> bool:
    return any(
        evidence_lookup[evidence_id].evidence_type is EvidenceType.FACT
        for evidence_id in evidence_ids
        if evidence_id in evidence_lookup
    )


def build_evidence_coverage(case: ReviewCaseFile) -> tuple[EvidenceCoverageStatus, ...]:
    observation_lookup = _observation_map(case)
    evidence_lookup = {item.evidence_id: item for item in case.base_case.evidence}

    rows: list[EvidenceCoverageStatus] = []
    for competitor in case.base_case.competitors:
        for dimension in case.comparison_dimensions:
            observation = observation_lookup.get((competitor.competitor_id, dimension.dimension_id))
            if observation is None:
                rows.append(
                    EvidenceCoverageStatus(
                        competitor_id=competitor.competitor_id,
                        dimension_id=dimension.dimension_id,
                        observation_supplied=False,
                        observation_state=None,
                        fact_supported=False,
                        evidence_ids=(),
                        coverage_label="missing",
                    )
                )
                continue

            fact_supported = _is_fact_supported(evidence_lookup, observation.supporting_evidence_ids)
            if observation.state is ReviewObservationState.UNKNOWN:
                coverage_label = "unknown"
            elif observation.state is ReviewObservationState.NOT_APPLICABLE:
                coverage_label = "not applicable"
            elif fact_supported:
                coverage_label = "fact-supported"
            else:
                coverage_label = "insufficient basis"

            rows.append(
                EvidenceCoverageStatus(
                    competitor_id=competitor.competitor_id,
                    dimension_id=dimension.dimension_id,
                    observation_supplied=True,
                    observation_state=observation.state.value,
                    fact_supported=fact_supported,
                    evidence_ids=observation.supporting_evidence_ids,
                    coverage_label=coverage_label,
                )
            )

    return tuple(rows)


def _is_supplied(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def evaluate_wedge_readiness(case: ReviewCaseFile) -> tuple[ReviewWedgeReadiness, ...]:
    evidence_lookup = {item.evidence_id: item for item in case.base_case.evidence}
    readiness: list[ReviewWedgeReadiness] = []

    for wedge in case.wedge_candidates:
        missing: list[str] = []

        if not _is_supplied(wedge.target_user):
            missing.append("target_user")
        if not _is_supplied(wedge.payer):
            missing.append("payer")
        if not _is_supplied(wedge.user_pain):
            missing.append("user_pain")
        if not _is_supplied(wedge.proposed_advantage):
            missing.append("proposed_advantage")
        if not _is_supplied(wedge.competitor_gap):
            missing.append("competitor_gap")
        if not _is_supplied(wedge.smallest_manual_test):
            missing.append("smallest_manual_test")
        if not _is_supplied(wedge.test_timebox):
            missing.append("test_timebox")
        if not _is_supplied(wedge.success_signal):
            missing.append("success_signal")
        if not _is_supplied(wedge.invalidating_signal):
            missing.append("invalidating_signal")
        if not _is_supplied(wedge.next_operator_action):
            missing.append("next_operator_action")

        invalid_basis: list[str] = []
        if not wedge.supporting_evidence_ids:
            missing.append("supporting_evidence_ids")
        else:
            for evidence_id in wedge.supporting_evidence_ids:
                evidence = evidence_lookup.get(evidence_id)
                if evidence is None:
                    invalid_basis.append(f"unknown supporting evidence ID: {evidence_id}")
                    continue
                if evidence.evidence_type is not EvidenceType.FACT:
                    invalid_basis.append(
                        f"supporting evidence {evidence_id} must be FACT, got {evidence.evidence_type.value}"
                    )

        if invalid_basis:
            status = ReviewWedgeReadinessStatusValue.BLOCKED_INVALID_BASIS
        elif missing:
            status = ReviewWedgeReadinessStatusValue.BLOCKED_INCOMPLETE
        else:
            status = ReviewWedgeReadinessStatusValue.READY_FOR_MANUAL_TEST

        readiness.append(
            ReviewWedgeReadiness(
                wedge_id=wedge.wedge_id,
                status=status,
                missing_requirements=tuple(missing),
                invalid_evidence_basis=tuple(invalid_basis),
            )
        )

    return tuple(readiness)


def build_review_report(case: ReviewCaseFile) -> ReviewReport:
    matrix = build_competitor_matrix(case)
    coverage = build_evidence_coverage(case)
    readiness = evaluate_wedge_readiness(case)
    cards = tuple(
        WedgeExperimentCard(wedge=wedge, readiness=ready)
        for wedge, ready in zip(case.wedge_candidates, readiness)
    )
    counts = evidence_type_counts(case)

    return ReviewReport(
        review_case=case,
        matrix_rows=matrix,
        coverage=coverage,
        wedge_readiness=readiness,
        experiment_cards=cards,
        evidence_counts={
            EvidenceType.FACT: counts.get(EvidenceType.FACT, 0),
            EvidenceType.INFERENCE: counts.get(EvidenceType.INFERENCE, 0),
            EvidenceType.HYPOTHESIS: counts.get(EvidenceType.HYPOTHESIS, 0),
            EvidenceType.UNKNOWN: counts.get(EvidenceType.UNKNOWN, 0),
        },
    )

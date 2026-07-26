from __future__ import annotations

from collections import Counter

from acdis.casefiles.models import EvidenceItem
from acdis.contracts.placeholders import EvidenceType

from .models import (
    ComparisonObservation,
    ResearchQuestion,
    ReviewCaseFile,
    ReviewObservationState,
    ReviewQuestionStatus,
    ReviewWedgeCandidate,
)


class ReviewValidationError(ValueError):
    """Raised when a Phase 2 review payload is structurally invalid."""


def _error(kind: str, object_id: str, field_name: str, message: str) -> ReviewValidationError:
    return ReviewValidationError(f"{kind} {object_id} field {field_name}: {message}")


def _validate_evidence_types(case: ReviewCaseFile) -> None:
    for evidence in case.base_case.evidence:
        if not isinstance(evidence.evidence_type, EvidenceType):
            raise _error("evidence", evidence.evidence_id, "evidence_type", "missing or invalid classification")


def _build_competitor_ids(case: ReviewCaseFile) -> set[str]:
    return {item.competitor_id for item in case.base_case.competitors}


def _build_evidence_lookup(case: ReviewCaseFile) -> dict[str, EvidenceItem]:
    return {item.evidence_id: item for item in case.base_case.evidence}


def _build_dimension_ids(case: ReviewCaseFile) -> set[str]:
    return {item.dimension_id for item in case.comparison_dimensions}


def _validate_research_questions(
    case: ReviewCaseFile,
    evidence_lookup: dict[str, EvidenceItem],
    competitor_ids: set[str],
) -> None:
    seen_ids: set[str] = set()
    for question in case.research_questions:
        if question.question_id in seen_ids:
            raise _error("research_question", question.question_id, "question_id", "duplicate ID")
        seen_ids.add(question.question_id)

        if not isinstance(question.status, ReviewQuestionStatus):
            raise _error("research_question", question.question_id, "status", "unknown status")

        for evidence_id in question.related_evidence_ids:
            if evidence_id not in evidence_lookup:
                raise _error("research_question", question.question_id, "related_evidence_ids", f"unknown evidence ID: {evidence_id}")
        for competitor_id in question.related_competitor_ids:
            if competitor_id not in competitor_ids:
                raise _error("research_question", question.question_id, "related_competitor_ids", f"unknown competitor ID: {competitor_id}")

        if question.status is ReviewQuestionStatus.OPEN:
            continue

        if not question.related_evidence_ids:
            raise _error("research_question", question.question_id, "related_evidence_ids", "status requires supporting evidence")

        has_fact = any(
            evidence_lookup[evidence_id].evidence_type is EvidenceType.FACT
            for evidence_id in question.related_evidence_ids
            if evidence_id in evidence_lookup
        )
        if not has_fact:
            raise _error("research_question", question.question_id, "related_evidence_ids", "status requires at least one FACT evidence item")


def _validate_dimensions(case: ReviewCaseFile) -> None:
    seen_ids: set[str] = set()
    for dimension in case.comparison_dimensions:
        if dimension.dimension_id in seen_ids:
            raise _error("comparison_dimension", dimension.dimension_id, "dimension_id", "duplicate ID")
        seen_ids.add(dimension.dimension_id)


def _validate_observations(
    case: ReviewCaseFile,
    evidence_lookup: dict[str, EvidenceItem],
    competitor_ids: set[str],
    dimension_ids: set[str],
) -> None:
    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    fact_required = {
        ReviewObservationState.PRESENT,
        ReviewObservationState.ABSENT,
        ReviewObservationState.PARTIAL,
    }

    for observation in case.comparison_observations:
        if observation.observation_id in seen_ids:
            raise _error("comparison_observation", observation.observation_id, "observation_id", "duplicate ID")
        seen_ids.add(observation.observation_id)

        if not isinstance(observation.state, ReviewObservationState):
            raise _error("comparison_observation", observation.observation_id, "state", "unknown state")

        if observation.competitor_id not in competitor_ids:
            raise _error("comparison_observation", observation.observation_id, "competitor_id", f"unknown competitor ID: {observation.competitor_id}")

        if observation.dimension_id not in dimension_ids:
            raise _error("comparison_observation", observation.observation_id, "dimension_id", f"unknown comparison dimension ID: {observation.dimension_id}")

        pair = (observation.competitor_id, observation.dimension_id)
        if pair in seen_pairs:
            raise _error(
                "comparison_observation",
                observation.observation_id,
                "competitor_id/dimension_id",
                f"duplicate competitor/dimension pair: {observation.competitor_id}/{observation.dimension_id}",
            )
        seen_pairs.add(pair)

        for evidence_id in observation.supporting_evidence_ids:
            if evidence_id not in evidence_lookup:
                raise _error("comparison_observation", observation.observation_id, "supporting_evidence_ids", f"unknown evidence ID: {evidence_id}")

        if observation.state in fact_required:
            if not observation.supporting_evidence_ids:
                raise _error("comparison_observation", observation.observation_id, "supporting_evidence_ids", "state requires supporting evidence")
            has_fact = any(
                evidence_lookup[evidence_id].evidence_type is EvidenceType.FACT
                for evidence_id in observation.supporting_evidence_ids
                if evidence_id in evidence_lookup
            )
            if not has_fact:
                raise _error(
                    "comparison_observation",
                    observation.observation_id,
                    "supporting_evidence_ids",
                    "state requires at least one FACT evidence item",
                )


def _validate_wedges(case: ReviewCaseFile, evidence_lookup: dict[str, EvidenceItem]) -> None:
    seen_ids: set[str] = set()
    for wedge in case.wedge_candidates:
        if wedge.wedge_id in seen_ids:
            raise _error("wedge_candidate", wedge.wedge_id, "wedge_id", "duplicate ID")
        seen_ids.add(wedge.wedge_id)

        _validate_wedge_supporting_evidence(wedge, evidence_lookup)
        _validate_wedge_hypothesis_evidence(wedge, evidence_lookup)


def _validate_wedge_supporting_evidence(wedge: ReviewWedgeCandidate, evidence_lookup: dict[str, EvidenceItem]) -> None:
    for evidence_id in wedge.supporting_evidence_ids:
        if evidence_id not in evidence_lookup:
            raise _error("wedge_candidate", wedge.wedge_id, "supporting_evidence_ids", f"unknown evidence ID: {evidence_id}")


def _validate_wedge_hypothesis_evidence(wedge: ReviewWedgeCandidate, evidence_lookup: dict[str, EvidenceItem]) -> None:
    for evidence_id in wedge.hypothesis_evidence_ids:
        evidence = evidence_lookup.get(evidence_id)
        if evidence is None:
            raise _error("wedge_candidate", wedge.wedge_id, "hypothesis_evidence_ids", f"unknown evidence ID: {evidence_id}")
        if evidence.evidence_type is not EvidenceType.HYPOTHESIS:
            raise _error(
                "wedge_candidate",
                wedge.wedge_id,
                "hypothesis_evidence_ids",
                f"must reference HYPOTHESIS evidence; got {evidence.evidence_type.value} for {evidence_id}",
            )


def validate_review_case_file(case: ReviewCaseFile) -> None:
    _validate_evidence_types(case)
    evidence_lookup = _build_evidence_lookup(case)
    competitor_ids = _build_competitor_ids(case)
    dimension_ids = _build_dimension_ids(case)

    _validate_research_questions(case, evidence_lookup, competitor_ids)
    _validate_dimensions(case)
    _validate_observations(case, evidence_lookup, competitor_ids, dimension_ids)
    _validate_wedges(case, evidence_lookup)


def evidence_type_counts(case: ReviewCaseFile) -> Counter[EvidenceType]:
    counts: Counter[EvidenceType] = Counter()
    for evidence in case.base_case.evidence:
        counts[evidence.evidence_type] += 1
    return counts

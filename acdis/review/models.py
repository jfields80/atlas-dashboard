from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from acdis.casefiles.models import ResearchCaseFile
from acdis.contracts.placeholders import EvidenceType


class ReviewQuestionStatus(str, Enum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    ANSWERED = "ANSWERED"


class ReviewObservationState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReviewWedgeReadinessStatusValue(str, Enum):
    READY_FOR_MANUAL_TEST = "READY_FOR_MANUAL_TEST"
    BLOCKED_INCOMPLETE = "BLOCKED_INCOMPLETE"
    BLOCKED_INVALID_BASIS = "BLOCKED_INVALID_BASIS"


@dataclass(frozen=True)
class ResearchQuestion:
    question_id: str
    question_text: str
    status: ReviewQuestionStatus
    related_evidence_ids: tuple[str, ...] = ()
    related_competitor_ids: tuple[str, ...] = ()
    operator_notes: str | None = None


@dataclass(frozen=True)
class ComparisonDimension:
    dimension_id: str
    label: str
    description: str
    why_it_matters: str
    operator_notes: str | None = None


@dataclass(frozen=True)
class ComparisonObservation:
    observation_id: str
    competitor_id: str
    dimension_id: str
    state: ReviewObservationState
    statement: str
    supporting_evidence_ids: tuple[str, ...] = ()
    operator_notes: str | None = None


@dataclass(frozen=True)
class ReviewWedgeCandidate:
    wedge_id: str
    title: str
    target_user: str | None = None
    payer: str | None = None
    user_pain: str | None = None
    proposed_advantage: str | None = None
    competitor_gap: str | None = None
    supporting_evidence_ids: tuple[str, ...] = ()
    hypothesis_evidence_ids: tuple[str, ...] = ()
    reasons_the_wedge_might_fail: tuple[str, ...] = ()
    smallest_manual_test: str | None = None
    test_timebox: str | None = None
    cost_cap: str | None = None
    success_signal: str | None = None
    invalidating_signal: str | None = None
    test_participants: str | None = None
    dependencies: tuple[str, ...] = ()
    next_operator_action: str | None = None
    operator_notes: str | None = None


@dataclass(frozen=True)
class ReviewWedgeReadiness:
    wedge_id: str
    status: ReviewWedgeReadinessStatusValue
    missing_requirements: tuple[str, ...] = ()
    invalid_evidence_basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewWedgeReadinessSummary:
    wedge_id: str
    status: ReviewWedgeReadinessStatusValue
    missing_requirements: tuple[str, ...] = ()
    invalid_evidence_basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewWedgeReadinessStatus:
    wedge_id: str
    status: ReviewWedgeReadinessStatusValue
    missing_requirements: tuple[str, ...] = ()
    invalid_evidence_basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceCoverageStatus:
    competitor_id: str
    dimension_id: str
    observation_supplied: bool
    observation_state: str | None = None
    fact_supported: bool = False
    evidence_ids: tuple[str, ...] = ()
    coverage_label: str = "missing"


@dataclass(frozen=True)
class ReviewCaseFile:
    base_case: ResearchCaseFile
    research_questions: tuple[ResearchQuestion, ...] = ()
    comparison_dimensions: tuple[ComparisonDimension, ...] = ()
    comparison_observations: tuple[ComparisonObservation, ...] = ()
    wedge_candidates: tuple[ReviewWedgeCandidate, ...] = ()

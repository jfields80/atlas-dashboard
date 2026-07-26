from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from acdis.contracts.placeholders import EvidenceType


@dataclass(frozen=True)
class CompetitorEntry:
    competitor_id: str
    name: str
    supplied_urls: tuple[str, ...] = ()
    artifact_references: tuple[str, ...] = ()
    observed_monetization_methods: tuple[str, ...] = ()
    operator_notes: str | None = None


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    evidence_type: EvidenceType
    statement: str
    source_references: tuple[str, ...] = ()
    excerpt: str | None = None
    related_competitor_ids: tuple[str, ...] = ()
    supporting_evidence_ids: tuple[str, ...] = ()
    operator_notes: str | None = None


@dataclass(frozen=True)
class ResearchCaseFile:
    case_id: str
    case_title: str
    operator_notes: str | None
    opportunity_name: str
    target_market: str
    proposed_directory_category: str
    customer_type: str
    user_problem: str
    proposed_minimum_useful_pilot: str
    likely_monetization_paths: tuple[str, ...]
    potential_data_moat_opportunities: tuple[str, ...]
    reasons_not_to_pursue: tuple[str, ...]
    next_research_actions: tuple[str, ...]
    competitors: tuple[CompetitorEntry, ...]
    evidence: tuple[EvidenceItem, ...]
    proposed_wedge_ideas: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    operator_recommendation: str | None = None
    operator_recommendation_rationale: str | None = None

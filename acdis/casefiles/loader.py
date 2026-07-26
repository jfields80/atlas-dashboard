from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from acdis.casefiles.models import CompetitorEntry, EvidenceItem, ResearchCaseFile
from acdis.casefiles.validation import CaseFileValidationError, validate_case_file
from acdis.contracts.placeholders import EvidenceType


class CaseFileError(ValueError):
    """Raised when a case file cannot be loaded."""


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    cleaned = value.strip()
    return cleaned or None


def _coerce_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CaseFileError("Case file fields must be lists when present")
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def load_case_file(path: str | Path) -> ResearchCaseFile:
    input_path = Path(path)
    try:
        raw_text = input_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CaseFileError(f"Case file not found: {input_path}") from exc
    except OSError as exc:
        raise CaseFileError(f"Unable to read case file: {input_path}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CaseFileError(f"Malformed JSON in case file: {input_path}") from exc

    if not isinstance(payload, dict):
        raise CaseFileError("Case file root must be a JSON object")

    try:
        validate_case_file(payload)
    except CaseFileValidationError as exc:
        raise CaseFileValidationError(str(exc)) from exc

    competitors = tuple(
        CompetitorEntry(
            competitor_id=str(item["competitor_id"]),
            name=str(item["name"]),
            supplied_urls=_coerce_list(item.get("supplied_urls")),
            artifact_references=_coerce_list(item.get("artifact_references")),
            observed_monetization_methods=_coerce_list(item.get("observed_monetization_methods")),
            operator_notes=_coerce_optional_text(item.get("operator_notes")),
        )
        for item in payload["competitors"]
        if isinstance(item, dict)
    )

    evidence_items = tuple(
        EvidenceItem(
            evidence_id=str(item["evidence_id"]),
            evidence_type=EvidenceType(str(item["evidence_type"])),
            statement=str(item["statement"]),
            source_references=_coerce_list(item.get("source_references")),
            excerpt=_coerce_optional_text(item.get("excerpt")),
            related_competitor_ids=_coerce_list(item.get("related_competitor_ids")),
            supporting_evidence_ids=_coerce_list(item.get("supporting_evidence_ids")),
            operator_notes=_coerce_optional_text(item.get("operator_notes")),
        )
        for item in payload["evidence"]
        if isinstance(item, dict)
    )

    return ResearchCaseFile(
        case_id=str(payload["case_id"]),
        case_title=str(payload["case_title"]),
        operator_notes=_coerce_optional_text(payload.get("operator_notes")),
        opportunity_name=str(payload["opportunity_name"]),
        target_market=str(payload["target_market"]),
        proposed_directory_category=str(payload["proposed_directory_category"]),
        customer_type=str(payload["customer_type"]),
        user_problem=str(payload["user_problem"]),
        proposed_minimum_useful_pilot=str(payload["proposed_minimum_useful_pilot"]),
        likely_monetization_paths=_coerce_list(payload.get("likely_monetization_paths")),
        potential_data_moat_opportunities=_coerce_list(payload.get("potential_data_moat_opportunities")),
        reasons_not_to_pursue=_coerce_list(payload.get("reasons_not_to_pursue")),
        next_research_actions=_coerce_list(payload.get("next_research_actions")),
        competitors=competitors,
        evidence=evidence_items,
        proposed_wedge_ideas=_coerce_list(payload.get("proposed_wedge_ideas")),
        unresolved_questions=_coerce_list(payload.get("unresolved_questions")),
        operator_recommendation=_coerce_optional_text(payload.get("operator_recommendation")),
        operator_recommendation_rationale=_coerce_optional_text(payload.get("operator_recommendation_rationale")),
    )

from __future__ import annotations

from typing import Any, Mapping

from acdis.contracts.placeholders import EvidenceType


class CaseFileValidationError(ValueError):
    """Raised when a case file fails manual validation."""


def _require_text(value: Any, field_name: str, item_id: str | None = None) -> str:
    if not isinstance(value, str):
        raise CaseFileValidationError(f"{field_name} must be a non-empty string")
    cleaned = value.strip()
    if not cleaned:
        raise CaseFileValidationError(f"{field_name} must not be blank")
    if item_id:
        return cleaned
    return cleaned


def _require_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise CaseFileValidationError(f"{field_name} must be a list")
    return value


def validate_case_file(data: Mapping[str, Any]) -> None:
    required_text_fields = [
        ("case_id", "case ID"),
        ("case_title", "case title"),
        ("opportunity_name", "opportunity name"),
        ("target_market", "target market"),
        ("proposed_directory_category", "proposed directory category"),
        ("customer_type", "customer type"),
        ("user_problem", "user problem"),
        ("proposed_minimum_useful_pilot", "proposed minimum useful pilot"),
    ]
    for field_name, label in required_text_fields:
        if field_name not in data:
            raise CaseFileValidationError(f"Missing required field: {label}")
        _require_text(data[field_name], label)

    for field_name in [
        "likely_monetization_paths",
        "potential_data_moat_opportunities",
        "reasons_not_to_pursue",
        "next_research_actions",
    ]:
        if field_name not in data:
            raise CaseFileValidationError(f"Missing required field: {field_name}")
        values = _require_list(data[field_name], field_name)
        if not values:
            raise CaseFileValidationError(f"{field_name} must not be empty")
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise CaseFileValidationError(f"{field_name} contains a blank item")

    if "competitors" not in data:
        raise CaseFileValidationError("Missing required field: competitors")
    competitors = _require_list(data["competitors"], "competitors")
    if not competitors:
        raise CaseFileValidationError("competitors must not be empty")

    seen_competitor_ids: set[str] = set()
    for competitor in competitors:
        if not isinstance(competitor, dict):
            raise CaseFileValidationError("Each competitor must be an object")
        competitor_id = _require_text(competitor.get("competitor_id"), "competitor ID")
        if competitor_id in seen_competitor_ids:
            raise CaseFileValidationError(f"duplicate competitor ID: {competitor_id}")
        seen_competitor_ids.add(competitor_id)
        _require_text(competitor.get("name"), "competitor name")

    if "evidence" not in data:
        raise CaseFileValidationError("Missing required field: evidence")
    evidence_items = _require_list(data["evidence"], "evidence")
    if not evidence_items:
        raise CaseFileValidationError("evidence must not be empty")

    seen_evidence_ids: set[str] = set()
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            raise CaseFileValidationError("Each evidence item must be an object")
        evidence_id = _require_text(evidence.get("evidence_id"), "evidence ID")
        if evidence_id in seen_evidence_ids:
            raise CaseFileValidationError(f"Duplicate evidence ID: {evidence_id}")
        seen_evidence_ids.add(evidence_id)

        if "evidence_type" not in evidence:
            raise CaseFileValidationError(f"Evidence item {evidence_id} is missing evidence classification")
        evidence_type_value = evidence["evidence_type"]
        if not isinstance(evidence_type_value, str):
            raise CaseFileValidationError(f"Evidence item {evidence_id} has an invalid evidence classification")
        try:
            evidence_type = EvidenceType(evidence_type_value)
        except ValueError as exc:
            raise CaseFileValidationError(f"Evidence item {evidence_id} has unknown EvidenceType: {evidence_type_value}") from exc

        statement = evidence.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            raise CaseFileValidationError(f"Evidence item {evidence_id} is missing a statement")

        if evidence_type is EvidenceType.FACT:
            source_references = evidence.get("source_references")
            if not isinstance(source_references, list) or not source_references or not any(isinstance(item, str) and item.strip() for item in source_references):
                raise CaseFileValidationError(f"FACT evidence item {evidence_id} requires at least one source reference")
        elif evidence_type is EvidenceType.INFERENCE:
            supporting_ids = evidence.get("supporting_evidence_ids")
            if not isinstance(supporting_ids, list) or not supporting_ids:
                raise CaseFileValidationError(f"INFERENCE evidence item {evidence_id} requires supporting evidence")
            if not any(item in {EvidenceType.FACT.value for item in []} for item in []):
                pass
        elif evidence_type is EvidenceType.HYPOTHESIS:
            pass
        elif evidence_type is EvidenceType.UNKNOWN:
            pass

    competitor_ids = {str(item.get("competitor_id")) for item in competitors if isinstance(item, dict) and isinstance(item.get("competitor_id"), str)}
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            continue
        evidence_id = evidence.get("evidence_id")
        if not isinstance(evidence_id, str):
            continue
        related_ids = evidence.get("related_competitor_ids")
        if isinstance(related_ids, list):
            for related_id in related_ids:
                if isinstance(related_id, str) and related_id not in competitor_ids:
                    raise CaseFileValidationError(f"Evidence item {evidence_id} references unknown competitor ID: {related_id}")
        supporting_ids = evidence.get("supporting_evidence_ids")
        if isinstance(supporting_ids, list):
            for supporting_id in supporting_ids:
                if isinstance(supporting_id, str) and supporting_id not in seen_evidence_ids:
                    raise CaseFileValidationError(f"INFERENCE evidence item {evidence_id} requires supporting evidence from existing evidence IDs; unknown evidence ID: {supporting_id}")

    # Re-check evidence relationships after the full evidence set is known.
    evidence_lookup = {item["evidence_id"]: item for item in evidence_items if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)}
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            continue
        evidence_id = evidence.get("evidence_id")
        if not isinstance(evidence_id, str):
            continue
        evidence_type_value = evidence.get("evidence_type")
        if not isinstance(evidence_type_value, str):
            continue
        try:
            evidence_type = EvidenceType(evidence_type_value)
        except ValueError:
            continue
        if evidence_type is EvidenceType.INFERENCE:
            supporting_ids = evidence.get("supporting_evidence_ids")
            if not isinstance(supporting_ids, list) or not supporting_ids:
                continue
            supporting_items = [evidence_lookup[supporting_id] for supporting_id in supporting_ids if isinstance(supporting_id, str) and supporting_id in evidence_lookup]
            if not supporting_items:
                continue
            if not any(EvidenceType(evidence_item.get("evidence_type")) is EvidenceType.FACT for evidence_item in supporting_items if isinstance(evidence_item.get("evidence_type"), str)):
                raise CaseFileValidationError(f"INFERENCE evidence item {evidence_id} must include at least one FACT supporting evidence item")

    if "operator_recommendation" in data and data["operator_recommendation"] is not None:
        recommendation = data["operator_recommendation"]
        if recommendation not in {"GO", "HOLD", "REJECT"}:
            raise CaseFileValidationError(f"Operator recommendation must be GO, HOLD, or REJECT; got {recommendation}")

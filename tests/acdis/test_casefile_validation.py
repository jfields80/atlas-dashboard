import pytest

from acdis.casefiles.loader import CaseFileValidationError, load_case_file
from acdis.contracts.placeholders import EvidenceType


def _valid_case_data():
    return {
        "case_id": "case-002",
        "case_title": "Example case",
        "opportunity_name": "Example opportunity",
        "target_market": "Example market",
        "proposed_directory_category": "Example category",
        "customer_type": "Example customers",
        "user_problem": "Example problem",
        "proposed_minimum_useful_pilot": "Example pilot",
        "likely_monetization_paths": ["Lead referrals"],
        "potential_data_moat_opportunities": ["Local review data"],
        "reasons_not_to_pursue": ["No funding"],
        "next_research_actions": ["Talk to operators"],
        "competitors": [{"competitor_id": "comp-1", "name": "Example Co"}],
        "evidence": [{
            "evidence_id": "evidence-1",
            "evidence_type": "FACT",
            "statement": "Observed signal",
            "source_references": ["Manual interview"],
        }],
    }


def test_duplicate_competitor_ids_are_rejected(tmp_path):
    data = _valid_case_data()
    data["competitors"].append({"competitor_id": "comp-1", "name": "Dup"})
    input_path = tmp_path / "case.json"
    input_path.write_text(__import__("json").dumps(data), encoding="utf-8")

    with pytest.raises(CaseFileValidationError, match="duplicate competitor ID"):
        load_case_file(input_path)


def test_inference_without_supporting_fact_is_rejected(tmp_path):
    data = _valid_case_data()
    data["evidence"] = [{
        "evidence_id": "evidence-1",
        "evidence_type": "INFERENCE",
        "statement": "The opportunity is attractive.",
        "supporting_evidence_ids": ["evidence-2"],
    }]
    input_path = tmp_path / "case.json"
    input_path.write_text(__import__("json").dumps(data), encoding="utf-8")

    with pytest.raises(CaseFileValidationError, match="supporting evidence"):
        load_case_file(input_path)


def test_invalid_recommendation_is_rejected(tmp_path):
    data = _valid_case_data()
    data["operator_recommendation"] = "MAYBE"
    input_path = tmp_path / "case.json"
    input_path.write_text(__import__("json").dumps(data), encoding="utf-8")

    with pytest.raises(CaseFileValidationError, match="Operator recommendation"):
        load_case_file(input_path)


def test_missing_classification_is_never_defaulted(tmp_path):
    data = _valid_case_data()
    data["evidence"][0].pop("evidence_type")
    input_path = tmp_path / "case.json"
    input_path.write_text(__import__("json").dumps(data), encoding="utf-8")

    with pytest.raises(CaseFileValidationError, match="classification"):
        load_case_file(input_path)

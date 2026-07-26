import json
from pathlib import Path

import pytest

from acdis.casefiles.loader import CaseFileError, load_case_file
from acdis.casefiles.models import ResearchCaseFile
from acdis.contracts.placeholders import EvidenceType


def _valid_case_data():
    return {
        "case_id": "case-001",
        "case_title": "Pet care directory pilot",
        "operator_notes": "Manual research only.",
        "opportunity_name": "Pet care concierge",
        "target_market": "Small pet owners in metro areas",
        "proposed_directory_category": "Pet Services",
        "customer_type": "Pet owners",
        "user_problem": "Finding trustworthy local help when traveling.",
        "proposed_minimum_useful_pilot": "A single curated directory page for 5 neighborhoods.",
        "likely_monetization_paths": ["Lead referrals", "Sponsored listings"],
        "potential_data_moat_opportunities": ["Local service reviews"],
        "reasons_not_to_pursue": ["No clear monetization path"],
        "next_research_actions": ["Interview local operators"],
        "competitors": [
            {
                "competitor_id": "comp-1",
                "name": "Example Directory",
                "supplied_urls": ["https://example.com"],
                "artifact_references": ["screenshot-1.png"],
                "observed_monetization_methods": ["Sponsored listings"],
                "operator_notes": "Manual note",
            }
        ],
        "evidence": [
            {
                "evidence_id": "evidence-1",
                "evidence_type": "FACT",
                "statement": "The directory has a clear local demand signal.",
                "source_references": ["Operator interview"],
                "excerpt": "Demand exists.",
                "related_competitor_ids": ["comp-1"],
                "supporting_evidence_ids": [],
                "operator_notes": "Observed directly",
            }
        ],
        "proposed_wedge_ideas": ["Neighborhood-specific concierge"],
        "unresolved_questions": ["How to validate local demand?"],
        "operator_recommendation": "HOLD",
        "operator_recommendation_rationale": "Need more evidence.",
    }


def test_valid_json_case_loads(tmp_path):
    input_path = tmp_path / "case.json"
    input_path.write_text(json.dumps(_valid_case_data()), encoding="utf-8")

    case = load_case_file(input_path)

    assert isinstance(case, ResearchCaseFile)
    assert case.case_id == "case-001"
    assert case.competitors[0].competitor_id == "comp-1"
    assert case.evidence[0].evidence_type is EvidenceType.FACT


def test_malformed_json_is_rejected(tmp_path):
    input_path = tmp_path / "case.json"
    input_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(CaseFileError, match="Malformed JSON"):
        load_case_file(input_path)

import json
from pathlib import Path

from acdis.casefiles.loader import load_case_file
from acdis.reports.markdown import render_markdown


def _valid_case_data():
    return {
        "case_id": "case-003",
        "case_title": "Manual research report",
        "opportunity_name": "Local support directory",
        "target_market": "Traveling pet owners",
        "proposed_directory_category": "Travel Services",
        "customer_type": "Traveling pet owners",
        "user_problem": "Finding reliable pet-friendly local support",
        "proposed_minimum_useful_pilot": "A curated local directory",
        "likely_monetization_paths": ["Lead referrals"],
        "potential_data_moat_opportunities": ["Local reviews"],
        "reasons_not_to_pursue": ["No clear buyer"],
        "next_research_actions": ["Interview operators"],
        "competitors": [{"competitor_id": "comp-1", "name": "Example Co"}],
        "evidence": [
            {
                "evidence_id": "evidence-1",
                "evidence_type": "FACT",
                "statement": "Fact statement.",
                "source_references": ["Manual interview"],
            },
            {
                "evidence_id": "evidence-2",
                "evidence_type": "INFERENCE",
                "statement": "Inferred pattern.",
                "supporting_evidence_ids": ["evidence-1"],
            },
            {
                "evidence_id": "evidence-3",
                "evidence_type": "HYPOTHESIS",
                "statement": "Hypothesis statement.",
            },
            {
                "evidence_id": "evidence-4",
                "evidence_type": "UNKNOWN",
                "statement": "Unknown statement.",
            },
        ],
    }


def test_renderer_keeps_evidence_categories_separate(tmp_path):
    input_path = tmp_path / "case.json"
    input_path.write_text(json.dumps(_valid_case_data()), encoding="utf-8")
    case = load_case_file(input_path)

    report = render_markdown(case)

    assert "## 6. Verified observations" in report
    assert "## 7. Supported inferences" in report
    assert "## 8. Hypotheses requiring validation" in report
    assert "## 9. Unknowns" in report
    assert "Fact statement." in report
    assert "Inferred pattern." in report
    assert "Hypothesis statement." in report
    assert "Unknown statement." in report


def test_sample_report_matches_fresh_render_of_sample_case():
    repo_root = Path(__file__).resolve().parents[2]
    sample_case_path = repo_root / "docs/acdis/examples/sample_case.json"
    sample_report_path = repo_root / "docs/acdis/examples/sample_report.md"

    case = load_case_file(sample_case_path)
    report = render_markdown(case)
    expected = sample_report_path.read_text(encoding="utf-8")

    assert report == expected


def test_missing_optional_fields_render_as_not_supplied(tmp_path):
    input_path = tmp_path / "case.json"
    input_path.write_text(json.dumps(_valid_case_data()), encoding="utf-8")
    case = load_case_file(input_path)

    report = render_markdown(case)

    assert "Not supplied" in report

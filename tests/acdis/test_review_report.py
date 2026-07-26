import json
from pathlib import Path

from acdis.review.builder import build_review_case
from acdis.review.markdown import render_review_markdown
from review_fixtures import make_review_case_data


def _build_case(tmp_path):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(make_review_case_data()), encoding="utf-8")
    return build_review_case(path)


def test_review_report_contains_all_required_sections(tmp_path):
    case = _build_case(tmp_path)
    report = render_review_markdown(case)

    for heading in [
        "## 1. Case identity",
        "## 2. Operator recommendation",
        "## 3. Research-question status",
        "## 4. Competitor comparison matrix",
        "## 5. Comparison-observation details",
        "## 6. Evidence coverage audit",
        "## 7. Verified facts",
        "## 8. Supported inferences",
        "## 9. Hypotheses requiring validation",
        "## 10. Unknowns",
        "## 11. Wedge candidates",
        "## 12. Structural test-readiness results",
        "## 13. Manual experiment cards",
        "## 14. Reasons not to pursue",
        "## 15. Outstanding research gaps",
        "## 16. Next operator actions",
        "## 17. Evidence appendix",
        "## 18. Integrity statement",
    ]:
        assert heading in report


def test_review_report_is_deterministic_for_identical_input(tmp_path):
    case = _build_case(tmp_path)

    report_a = render_review_markdown(case)
    report_b = render_review_markdown(case)

    assert report_a == report_b


def test_review_report_includes_integrity_statement_and_separated_evidence(tmp_path):
    case = _build_case(tmp_path)
    report = render_review_markdown(case)

    assert "All competitor states in this report were supplied by the operator." in report
    assert "No score, ranking, market estimate, or autonomous recommendation was produced." in report
    assert "## 7. Verified facts" in report
    assert "## 8. Supported inferences" in report
    assert "## 9. Hypotheses requiring validation" in report
    assert "## 10. Unknowns" in report


def test_sample_review_report_matches_fresh_renderer_output():
    repo_root = Path(__file__).resolve().parents[2]
    sample_case = repo_root / "docs" / "acdis" / "examples" / "sample_review_case.json"
    sample_report = repo_root / "docs" / "acdis" / "examples" / "sample_review_report.md"

    case = build_review_case(sample_case)
    rendered = render_review_markdown(case)
    expected = sample_report.read_text(encoding="utf-8")

    assert rendered == expected

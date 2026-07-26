import json

from acdis.review.builder import build_competitor_matrix, build_review_case
from acdis.review.markdown import render_review_markdown
from review_fixtures import make_review_case_data


def _build_case(tmp_path):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(make_review_case_data()), encoding="utf-8")
    return build_review_case(path)


def test_competitor_matrix_preserves_operator_order(tmp_path):
    case = _build_case(tmp_path)

    matrix = build_competitor_matrix(case)

    assert [row.competitor_id for row in matrix] == ["comp-a", "comp-b", "comp-c"]
    assert [cell.dimension_id for cell in matrix[0].cells] == [
        "dim-freshness",
        "dim-verification",
        "dim-monetization",
        "dim-workflow",
    ]


def test_competitor_matrix_does_not_infer_missing_cells(tmp_path):
    case = _build_case(tmp_path)

    matrix = build_competitor_matrix(case)

    # comp-c has only one observation in the supplied payload.
    comp_c_cells = [cell for row in matrix if row.competitor_id == "comp-c" for cell in row.cells]
    assert sum(1 for cell in comp_c_cells if cell.observation_id is None) == 3


def test_matrix_render_uses_not_supplied_and_no_scores_or_rankings(tmp_path):
    case = _build_case(tmp_path)

    report = render_review_markdown(case)

    assert "Not supplied" in report
    # Integrity text may mention excluded outputs; ensure no generated scoring/ranking fields exist.
    assert "Readiness is structural completeness, not a business recommendation." in report
    assert "No score, ranking, market estimate, or autonomous recommendation was produced." in report
    assert "opportunity score" not in report.lower()


def test_all_observation_states_remain_distinct_in_report(tmp_path):
    case = _build_case(tmp_path)

    report = render_review_markdown(case)

    assert "PRESENT" in report
    assert "ABSENT" in report
    assert "PARTIAL" in report
    assert "UNKNOWN" in report
    assert "NOT_APPLICABLE" in report

import json

from acdis.review.builder import build_review_case
from review_fixtures import make_review_case_data


def test_review_case_builds_from_optional_review_section(tmp_path):
    path = tmp_path / "review_case.json"
    path.write_text(json.dumps(make_review_case_data()), encoding="utf-8")

    review_case = build_review_case(path)

    assert review_case.base_case.case_id == "case-review-001"
    assert len(review_case.research_questions) == 3
    assert len(review_case.comparison_dimensions) == 4
    assert len(review_case.comparison_observations) == 5
    assert len(review_case.wedge_candidates) == 2


def test_phase1_case_without_review_section_remains_valid(tmp_path):
    payload = make_review_case_data()
    payload.pop("review")
    path = tmp_path / "phase1_case.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    review_case = build_review_case(path)

    assert review_case.research_questions == ()
    assert review_case.comparison_dimensions == ()
    assert review_case.comparison_observations == ()
    assert review_case.wedge_candidates == ()

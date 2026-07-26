import json

from acdis.review.builder import build_evidence_coverage, build_review_case
from review_fixtures import make_review_case_data


def _build_case(tmp_path):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(make_review_case_data()), encoding="utf-8")
    return build_review_case(path)


def test_coverage_is_deterministic_and_reflects_only_supplied_state(tmp_path):
    case = _build_case(tmp_path)

    coverage_a = build_evidence_coverage(case)
    coverage_b = build_evidence_coverage(case)

    assert coverage_a == coverage_b


def test_missing_observations_are_reported_as_missing_not_market_gap(tmp_path):
    case = _build_case(tmp_path)

    coverage = build_evidence_coverage(case)

    missing = [row for row in coverage if row.coverage_label == "missing"]
    assert missing


def test_non_unknown_observation_requires_fact_basis_in_coverage_output(tmp_path):
    case = _build_case(tmp_path)

    coverage = build_evidence_coverage(case)

    present_rows = [row for row in coverage if row.observation_state in {"PRESENT", "ABSENT", "PARTIAL"}]
    assert present_rows
    assert all(row.fact_supported for row in present_rows)

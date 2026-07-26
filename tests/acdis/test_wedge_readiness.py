import json

from acdis.review.builder import build_review_case, evaluate_wedge_readiness
from review_fixtures import make_review_case_data


def _build_case(tmp_path, payload=None):
    case_payload = payload or make_review_case_data()
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case_payload), encoding="utf-8")
    return build_review_case(path)


def test_complete_wedge_is_ready_for_manual_test(tmp_path):
    case = _build_case(tmp_path)

    readiness = evaluate_wedge_readiness(case)

    assert readiness[0].wedge_id == "wedge-ready"
    assert readiness[0].status.value == "READY_FOR_MANUAL_TEST"


def test_incomplete_wedge_is_blocked_and_lists_missing_fields(tmp_path):
    case = _build_case(tmp_path)

    readiness = evaluate_wedge_readiness(case)

    assert readiness[1].status.value == "BLOCKED_INCOMPLETE"
    assert "payer" in readiness[1].missing_requirements
    assert "smallest_manual_test" in readiness[1].missing_requirements
    assert "supporting_evidence_ids" in readiness[1].missing_requirements


def test_invalid_wedge_basis_is_blocked_invalid_basis(tmp_path):
    payload = make_review_case_data()
    payload["review"]["wedge_candidates"][0]["supporting_evidence_ids"] = ["ev-h1"]
    case = _build_case(tmp_path, payload)

    readiness = evaluate_wedge_readiness(case)

    assert readiness[0].status.value == "BLOCKED_INVALID_BASIS"
    assert any("must be FACT" in msg for msg in readiness[0].invalid_evidence_basis)


def test_readiness_does_not_change_operator_recommendation(tmp_path):
    case = _build_case(tmp_path)

    readiness = evaluate_wedge_readiness(case)

    assert case.base_case.operator_recommendation == "HOLD"
    assert readiness[0].status.value in {"READY_FOR_MANUAL_TEST", "BLOCKED_INCOMPLETE", "BLOCKED_INVALID_BASIS"}

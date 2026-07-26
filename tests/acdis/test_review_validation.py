import json

import pytest

from acdis.casefiles.loader import CaseFileValidationError
from acdis.review import ReviewValidationError
from acdis.review.builder import build_review_case
from review_fixtures import make_review_case_data


def _write_case(tmp_path, payload):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_duplicate_question_ids_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["research_questions"].append(dict(payload["review"]["research_questions"][0]))

    with pytest.raises(ReviewValidationError, match="research_question.*duplicate ID"):
        build_review_case(_write_case(tmp_path, payload))


def test_invalid_question_status_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["research_questions"][0]["status"] = "IN_PROGRESS"

    with pytest.raises(ReviewValidationError, match="unknown status"):
        build_review_case(_write_case(tmp_path, payload))


def test_invalid_observation_state_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["comparison_observations"][0]["state"] = "MIXED"

    with pytest.raises(ReviewValidationError, match="unknown state"):
        build_review_case(_write_case(tmp_path, payload))


def test_unknown_competitor_reference_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["comparison_observations"][0]["competitor_id"] = "comp-missing"

    with pytest.raises(ReviewValidationError, match="unknown competitor ID"):
        build_review_case(_write_case(tmp_path, payload))


def test_unknown_dimension_reference_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["comparison_observations"][0]["dimension_id"] = "dim-missing"

    with pytest.raises(ReviewValidationError, match="unknown comparison dimension ID"):
        build_review_case(_write_case(tmp_path, payload))


def test_unknown_evidence_reference_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["comparison_observations"][0]["supporting_evidence_ids"] = ["ev-missing"]

    with pytest.raises(ReviewValidationError, match="unknown evidence ID"):
        build_review_case(_write_case(tmp_path, payload))


def test_duplicate_competitor_dimension_pair_rejected(tmp_path):
    payload = make_review_case_data()
    duplicate = dict(payload["review"]["comparison_observations"][0])
    duplicate["observation_id"] = "obs-duplicate"
    payload["review"]["comparison_observations"].append(duplicate)

    with pytest.raises(ReviewValidationError, match="duplicate competitor/dimension pair"):
        build_review_case(_write_case(tmp_path, payload))


def test_answered_question_without_fact_support_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["research_questions"][0]["related_evidence_ids"] = ["ev-h1"]

    with pytest.raises(ReviewValidationError, match="requires at least one FACT"):
        build_review_case(_write_case(tmp_path, payload))


def test_partial_question_without_evidence_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["research_questions"][1]["related_evidence_ids"] = []

    with pytest.raises(ReviewValidationError, match="status requires supporting evidence"):
        build_review_case(_write_case(tmp_path, payload))


def test_present_absent_partial_without_fact_support_rejected(tmp_path):
    payload = make_review_case_data()
    payload["review"]["comparison_observations"][2]["supporting_evidence_ids"] = ["ev-h1"]

    with pytest.raises(ReviewValidationError, match="state requires at least one FACT"):
        build_review_case(_write_case(tmp_path, payload))


def test_missing_classification_is_not_defaulted(tmp_path):
    payload = make_review_case_data()
    payload["evidence"][0].pop("evidence_type")

    with pytest.raises(CaseFileValidationError, match="classification"):
        build_review_case(_write_case(tmp_path, payload))

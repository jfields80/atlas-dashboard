"""PTF-DISPLAY-003 -- the display-row review contract.

Every test here is offline and constructs its own rows. Nothing reads the live
register, so these prove the CONTRACT rather than the state of one batch.
"""

from __future__ import annotations

import pytest

from services.research_workers import display_review as DR

ROW = {
    "name": "Example Suites Columbus North",
    "category": "pet-friendly-hotels",
    "address": "1 Example Way", "city": "Columbus", "state": "OH",
    "postal_code": "43215", "phone": "614-555-0100",
    "website_url": "https://www.example.com/en/hotels/exmp1-example-suites",
    "source_url": "https://www.example.com/en/hotels/exmp1-example-suites",
    "source_type": "OFFICIAL_PROPERTY", "observed_at": "2026-08-04",
    "rating": "", "amenities": "",
    "pet_policy": "Dogs and cats are accepted. A $50 non-refundable fee applies.",
    "canonical": "",
}
BOUND = dict(identity_evidence_hash="sha256:aa", policy_source_record_hash="sha256:bb",
             policy_approval_hash="sha256:cc", reviewer_id="jfields80",
             reviewed_at="2026-08-06T00:00:00-04:00")


def _decide(row=None, decision=DR.DISPLAY_APPROVED, **over):
    kwargs = dict(hotel_id="discovery-example", normalized_name="example suites columbus north",
                  row=row or ROW, decision=decision, **BOUND)
    kwargs.update(over)
    return DR.build_decision(**kwargs)


# -- display_row_hash ------------------------------------------------------- #

def test_the_row_hash_is_deterministic_and_key_order_independent():
    reordered = {k: ROW[k] for k in reversed(list(ROW))}
    assert DR.display_row_hash(ROW) == DR.display_row_hash(reordered)


def test_the_row_hash_ignores_bookkeeping_fields():
    """A candidate file carries provenance beside the row. It is not the row."""
    decorated = dict(ROW, _hotel_id="x", _record_hash="y", _approval_hash="z")
    assert DR.display_row_hash(decorated) == DR.display_row_hash(ROW)


@pytest.mark.parametrize("column", ["address", "postal_code", "pet_policy", "source_url"])
def test_changing_any_published_value_changes_the_row_hash(column):
    assert DR.display_row_hash(dict(ROW, **{column: "different"})) != DR.display_row_hash(ROW)


def test_a_row_missing_a_column_cannot_be_hashed():
    with pytest.raises(DR.DisplayReviewError):
        DR.display_row_hash({k: v for k, v in ROW.items() if k != "city"})


# -- approval hash ---------------------------------------------------------- #

def test_an_approval_hash_rederives_from_its_own_content():
    d = _decide()
    assert DR.rederive_approval_hash(d) == d["approval_hash"]


def test_any_edit_after_the_fact_breaks_the_approval_hash():
    d = _decide()
    d["row"]["address"] = "somewhere else"
    assert DR.rederive_approval_hash(d) != d["approval_hash"]


def test_the_reviewer_statement_may_not_be_altered():
    with pytest.raises(DR.DisplayReviewError):
        _decide(statement="I confirm whatever is convenient.")


# -- gates ------------------------------------------------------------------ #

@pytest.mark.parametrize("column", DR.REQUIRED_COLUMNS)
def test_a_row_missing_a_required_value_cannot_be_approved(column):
    with pytest.raises(DR.DisplayReviewError):
        _decide(row=dict(ROW, **{column: ""}))


@pytest.mark.parametrize("column", DR.OPTIONAL_EMPTY_COLUMNS)
def test_an_unevidenced_optional_value_cannot_be_approved(column):
    """A rating invented for display is indistinguishable from one a source stated."""
    with pytest.raises(DR.DisplayReviewError):
        _decide(row=dict(ROW, **{column: "4.5"}))


def test_a_failing_row_may_still_be_HELD():
    """Holding is how a defective row is recorded -- refusal is not silence."""
    d = _decide(row=dict(ROW, city=""), decision=DR.DISPLAY_HELD)
    assert d["decision"] == DR.DISPLAY_HELD


def test_the_category_must_be_the_hotel_surface():
    assert "category_must_be_pet_friendly_hotels" in DR.row_problems(
        dict(ROW, category="pet-friendly-restaurants"))


# -- append-only supersession ----------------------------------------------- #

def test_a_correction_supersedes_without_rewriting_history():
    reg = DR.append_decision(DR.empty_register(), _decide())
    first = reg["decisions"][0]
    fixed = _decide(row=dict(ROW, address="2 Corrected Way"),
                    reviewed_at="2026-08-07T00:00:00-04:00")
    reg = DR.append_decision(reg, fixed)
    assert len(reg["decisions"]) == 2
    assert reg["decisions"][0] == first                      # untouched
    assert DR.current_decisions(reg)["discovery-example"]["approval_hash"] == fixed["approval_hash"]


def test_re_appending_the_same_decision_is_idempotent():
    d = _decide()
    reg = DR.append_decision(DR.append_decision(DR.empty_register(), d), d)
    assert len(reg["decisions"]) == 1


def test_a_decision_whose_hash_does_not_match_its_content_is_refused():
    d = _decide()
    d["notes"] = "quietly edited after signing"
    with pytest.raises(DR.DisplayReviewError):
        DR.append_decision(DR.empty_register(), d)


# -- index: staleness and policy binding ------------------------------------ #

def _candidate(**over):
    return dict(ROW, _hotel_id="discovery-example", **over)


def _state(src="sha256:bb", appr="sha256:cc"):
    return {"discovery-example": {"source_record_hash": src, "approval_hash": appr}}


def test_a_row_edited_after_approval_reports_stale():
    reg = DR.append_decision(DR.empty_register(), _decide())
    idx = DR.build_index(reg, [_candidate(address="9 Changed Rd")], policy_state=_state())
    assert idx["totals"]["stale_approvals"] == 1 and idx["stale"] == ["discovery-example"]


def test_a_display_approval_goes_stale_when_the_POLICY_approval_moves():
    """The display decision certified a row shown beside a specific policy.

    If that policy approval is superseded, the display approval no longer
    describes what a reader would see.
    """
    reg = DR.append_decision(DR.empty_register(), _decide())
    idx = DR.build_index(reg, [_candidate()], policy_state=_state(appr="sha256:NEW"))
    assert idx["totals"]["policy_hash_mismatches"] == 1


def test_a_candidate_with_no_decision_is_reported_not_assumed():
    idx = DR.build_index(DR.empty_register(), [_candidate()], policy_state=_state())
    assert idx["totals"]["candidates_without_a_current_decision"] == 1
    assert idx["totals"]["current_approved"] == 0


def test_a_held_row_is_counted_apart_from_an_approved_one():
    reg = DR.append_decision(DR.empty_register(),
                             _decide(row=dict(ROW, city=""), decision=DR.DISPLAY_HELD))
    idx = DR.build_index(reg, [_candidate(city="")], policy_state=_state())
    assert idx["totals"]["current_held"] == 1 and idx["totals"]["current_approved"] == 0


def test_a_clean_batch_reports_every_candidate_approved():
    reg = DR.append_decision(DR.empty_register(), _decide())
    idx = DR.build_index(reg, [_candidate()], policy_state=_state())
    t = idx["totals"]
    assert (t["current_approved"], t["current_held"], t["stale_approvals"],
            t["policy_hash_mismatches"], t["candidates_without_a_current_decision"]) == (1, 0, 0, 0, 0)

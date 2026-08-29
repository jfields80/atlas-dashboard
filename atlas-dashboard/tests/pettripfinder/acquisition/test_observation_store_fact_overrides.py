"""Founder FACT overrides on the observation store (PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003).

A founder may set, unset, unwithhold or withhold a policy field on a named
row. Anything asserted must cite a quote that is contiguous in the persisted
page; a withholding carries a contract reason; fields outside the observation
vocabulary and quotes the page does not carry refuse the override outright.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.acquisition import market_observation_store as MOS  # noqa: E402
from scripts.pettripfinder.contracts import enums  # noqa: E402

# The block the reader parses (Marriott FAQ shape: pets welcome, count, weight,
# no fee) and the Pet Policy section the page ALSO states, which carries the
# fee the reader never saw -- Indianapolis row 20's shape.
BLOCK = ("Does Fairfield Testville allow pets? Yes, pets are welcome at Fairfield "
         "Testville. Up to 2 pets are allowed per room. Each pet may weigh up to "
         "75.0 lbs.")
SECTION = ("Pet Policy Pets Welcome 2 pets max, 75lbs max Non-refundable fee: "
           "$75 USD Per Stay Maximum Pet Weight: 75.0lbs")
HTML = ("<html><body><h1>Fairfield Testville</h1><p>5905 W 86th Street</p>"
        "<div>%s</div><div>%s</div></body></html>" % (SECTION, BLOCK))


def _attempt(tmp_path: Path) -> Path:
    attempt = tmp_path / "fairfield-testville" / "attempt-01"
    attempt.mkdir(parents=True)
    (attempt / "rendered.html").write_text(HTML, encoding="utf-8")
    (attempt / "page-text.txt").write_text("Fairfield Testville\n5905 W 86th Street\n%s\n%s\n"
                                           % (SECTION, BLOCK), encoding="utf-8")
    (attempt / "policy-block.txt").write_text(BLOCK, encoding="utf-8")
    return attempt


def _result(attempt: Path):
    return {
        "identity_key": "fairfield testville", "canonical_name": "Fairfield Testville",
        "brand": "MARRIOTT", "corridor": "testville__northwest",
        "source_url": "https://www.marriott.com/en-us/hotels/tstfn-fairfield-testville/overview/",
        "final_url": "https://www.marriott.com/en-us/hotels/tstfn-fairfield-testville/overview/",
        "outcome": "VALID", "provider": "brightdata_browser", "reader": "marriott",
        "locator_strategy": "pet_policy_heading_parent", "identity_confirmed": True,
        "artifact_dir": str(attempt), "completed_at": "2026-08-25T19:28:24+00:00",
    }


def _overrides(*records):
    return {"decided_by": "PTF-FOUNDER-001", "decided_at": "2026-08-26",
            "work_order": "PTF-TEST", "fact_overrides": {"founder_ruling": "test", "records": list(records)}}


def _build(attempt, overrides=None):
    records, refusals, _ = MOS.build({"market_id": "testville-xx", "results": [_result(attempt)]},
                                     run_id="testville-001", founder_overrides=overrides)
    assert not refusals, refusals
    return records[0]


def test_without_an_override_the_fee_is_withheld_as_the_reader_left_it(tmp_path):
    record = _build(_attempt(tmp_path))
    assert "pet_fee" not in record["observation"]["extraction"]
    assert record["withheld_fields"].get("pet_fee") == enums.SOURCE_SILENT or "pet_fee" not in record["withheld_fields"]


def test_a_cited_set_becomes_a_fact_with_its_quote_as_evidence(tmp_path):
    record = _build(_attempt(tmp_path), _overrides({
        "identity_key": "fairfield testville", "ledger_row": 20,
        "set": {"pet_fee": 7500, "fee_currency": "USD", "fee_basis": "per_stay"},
        "unwithhold": ["pet_fee"], "cited_quotes": ["Non-refundable fee: $75 USD Per Stay"]}))
    extraction = record["observation"]["extraction"]
    assert extraction["pet_fee"] == 7500 and extraction["fee_basis"] == "per_stay"
    assert "pet_fee" not in record["withheld_fields"]
    cited = [e for e in record["observation"]["evidence"]
             if e["quote"] == "Non-refundable fee: $75 USD Per Stay"]
    assert cited and set(cited[0]["field_refs"]) == {"pet_fee", "fee_currency", "fee_basis"}
    ruling = record["observation"]["founder_overrides"][0]
    assert ruling["kind"] == "FACT" and ruling["ledger_row"] == 20
    assert ruling["decided_by"] == "PTF-FOUNDER-001"
    assert ruling["quotes_found_in"] == {"Non-refundable fee: $75 USD Per Stay": "page-text.txt"}
    assert record["publication_grade"]["verdict"] == "PUBLICATION_GRADE_CONFIRMED"
    assert record["membrane"]["verdict"] == "VALID"


def test_a_quote_the_page_does_not_carry_refuses_the_override(tmp_path):
    with pytest.raises(MOS.FactOverrideError):
        _build(_attempt(tmp_path), _overrides({
            "identity_key": "fairfield testville", "ledger_row": 20,
            "set": {"pet_fee": 7500}, "cited_quotes": ["Non-refundable fee: $95 USD Per Stay"]}))


def test_an_assertion_without_a_quote_is_refused(tmp_path):
    with pytest.raises(MOS.FactOverrideError):
        _build(_attempt(tmp_path), _overrides({
            "identity_key": "fairfield testville", "set": {"pet_fee": 7500}, "cited_quotes": []}))


def test_a_field_outside_the_vocabulary_is_refused(tmp_path):
    with pytest.raises(MOS.FactOverrideError):
        _build(_attempt(tmp_path), _overrides({
            "identity_key": "fairfield testville", "set": {"pet_price": 7500},
            "cited_quotes": ["Non-refundable fee: $75 USD Per Stay"]}))


def test_a_withholding_removes_the_fact_and_records_the_reason(tmp_path):
    record = _build(_attempt(tmp_path), _overrides({
        "identity_key": "fairfield testville", "ledger_row": 49,
        "withhold": {"weight_limit": enums.SOURCE_CONTRADICTORY}, "unset": ["weight_limit"],
        "flag_codes": {"weight_limit": "FLAG_AMBIGUOUS_SCOPE"},
        "cited_quotes": ["Maximum Pet Weight: 75.0lbs", "Each pet may weigh up to 75.0 lbs."]}))
    assert "weight_limit" not in record["observation"]["extraction"]
    assert record["withheld_fields"]["weight_limit"] == enums.SOURCE_CONTRADICTORY
    ruling = record["observation"]["founder_overrides"][0]
    assert ruling["was_facts"] == {"weight_limit": {"value": 75.0, "unit": "lb"}}
    # a withholding asserts nothing, so the conflicting quotes are not evidence
    assert not any(e["quote"] == "Maximum Pet Weight: 75.0lbs" for e in record["observation"]["evidence"])
    # ... but it must carry its sentence, which the policy package reads from the flags
    flag = next(f for f in record["observation"]["flags"] if f["code"] == "FLAG_AMBIGUOUS_SCOPE")
    assert record["membrane"]["verdict"] == "VALID"
    assert "weight_limit withheld as SOURCE_CONTRADICTORY by founder ruling" in flag["detail"]
    assert "Maximum Pet Weight: 75.0lbs" in flag["detail"]


def test_a_withheld_reason_outside_the_contract_is_refused(tmp_path):
    with pytest.raises(MOS.FactOverrideError):
        _build(_attempt(tmp_path), _overrides({
            "identity_key": "fairfield testville", "withhold": {"weight_limit": "SOURCE_CONFLICT"},
            "flag_codes": {"weight_limit": "FLAG_AMBIGUOUS_SCOPE"}}))


def test_a_withholding_must_name_a_flag_from_the_observation_vocabulary(tmp_path):
    with pytest.raises(MOS.FactOverrideError):
        _build(_attempt(tmp_path), _overrides({
            "identity_key": "fairfield testville", "withhold": {"weight_limit": enums.SOURCE_CONTRADICTORY},
            "flag_codes": {"weight_limit": "FLAG_FOUNDER_WITHHELD"}}))


def test_an_override_on_another_row_touches_nothing_here(tmp_path):
    record = _build(_attempt(tmp_path), _overrides({
        "identity_key": "some other hotel", "set": {"pet_fee": 100}, "cited_quotes": ["x"]}))
    assert "pet_fee" not in record["observation"]["extraction"]
    assert "founder_overrides" not in record["observation"]

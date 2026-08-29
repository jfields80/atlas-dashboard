"""PTF-DEFECT-LABEL-VALUE-FIELD-BOUNDARY-001 (P6).

On a ``label: value`` policy surface an amount binds only to the label that
precedes it; a parser must not splice the amount of one field onto the label of
the next. Indianapolis founder-review row 31 (Holiday Inn Express & Suites
Indianapolis Northwest, IHG block captured 2026-08-25) is the fixture: the block
"Pet fee per night: 25 USD  Pet damage deposit: 75 USD ..." was read as a $25
deposit with the quote "25 USD Pet damage deposit".

The tests are marked xfail(strict=True) until the fix lands.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402

FIXTURE = (REPO_ROOT / "tests" / "pettripfinder" / "fixtures" / "label_value_p6"
           / "indianapolis_row31_block.json")
DEFECT = "PTF-DEFECT-LABEL-VALUE-FIELD-BOUNDARY-001"


@pytest.fixture(scope="module")
def row31():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _extract(row31):
    reading = PR.parse(row31["policy_block"], strategy=row31["locator_strategy"])
    return PR.to_extraction(reading, location="fixture")


def test_fixture_reproduces_the_spliced_deposit(row31):
    ex = _extract(row31)
    assert ex.extraction.get("pet_deposit") == 2500
    quotes = {tuple(e["field_refs"]): e["quote"] for e in ex.evidence}
    assert quotes[("pet_deposit",)] == "25 USD Pet damage deposit"
    assert "pet_fee" not in ex.extraction


@pytest.mark.xfail(strict=True, reason=DEFECT + ": the deposit takes the fee's amount")
def test_the_deposit_binds_to_its_own_amount(row31):
    ex = _extract(row31)
    assert ex.extraction.get("pet_deposit") == 7500


@pytest.mark.xfail(strict=True, reason=DEFECT + ": a quote must not start in the previous field")
def test_no_evidence_quote_crosses_a_field_boundary(row31):
    ex = _extract(row31)
    for entry in ex.evidence:
        quote = entry["quote"]
        assert not quote.startswith("25 USD Pet damage"), quote
        assert "Pet damage deposit" not in quote or quote.startswith("Pet damage deposit"), quote


@pytest.mark.xfail(strict=True, reason=DEFECT + ": the fee is lost once its amount is consumed")
def test_the_nightly_fee_survives_beside_the_deposit(row31):
    ex = _extract(row31)
    assert ex.extraction.get("pet_fee") == 2500
    assert ex.extraction.get("fee_basis") == "per_night"

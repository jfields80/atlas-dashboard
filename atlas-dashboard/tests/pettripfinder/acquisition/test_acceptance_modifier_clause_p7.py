"""PTF-DEFECT-ACCEPTANCE-MODIFIER-CLAUSE-001 (P7).

"Up to 2 pets with a maximum weight of 50lbs are welcome ..." states acceptance;
the parser must not withhold ``pets_allowed`` because a modifier sits between
"pets" and "are welcome". Indianapolis founder-review row 48 (Super 8 by Wyndham
Indianapolis South, captured 2026-08-25) is the fixture.

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

FIXTURE = (REPO_ROOT / "tests" / "pettripfinder" / "fixtures" / "acceptance_p7"
           / "indianapolis_row48_block.json")
DEFECT = "PTF-DEFECT-ACCEPTANCE-MODIFIER-CLAUSE-001"


@pytest.fixture(scope="module")
def row48():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _extract(row48):
    reading = PR.parse(row48["policy_block"], strategy=row48["locator_strategy"])
    return PR.to_extraction(reading, location="fixture")


def test_fixture_reproduces_the_withheld_allowance(row48):
    ex = _extract(row48)
    assert "pets_allowed" not in ex.extraction
    assert ex.extraction.get("pet_fee") == 1000
    assert ex.extraction.get("pet_count_limit") == 2
    assert ex.extraction.get("weight_limit", {}).get("value") == 50.0


@pytest.mark.xfail(strict=True, reason=DEFECT + ": 'pets ... are welcome' with a modifier between")
def test_pets_are_welcome_across_a_modifier_clause(row48):
    ex = _extract(row48)
    assert ex.extraction.get("pets_allowed") is True


@pytest.mark.xfail(strict=True, reason=DEFECT + ": the evidence quote must span subject to predicate")
def test_the_acceptance_quote_is_the_whole_sentence_span(row48):
    ex = _extract(row48)
    quotes = [e["quote"] for e in ex.evidence if "pets_allowed" in e["field_refs"]]
    assert quotes and quotes[0].startswith("Up to 2 pets with a maximum weight of 50lbs are welcome")

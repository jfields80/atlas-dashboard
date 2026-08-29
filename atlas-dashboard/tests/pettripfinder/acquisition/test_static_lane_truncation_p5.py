"""PTF-DEFECT-STATIC-LANE-BLOCK-TRUNCATION-001 (P5).

The static lane (``unlocker_capture.locate_policy_in_text``) must keep the
adjacent supported pet-policy facts -- fee tiers, weight, count, species,
deposits, restrictions -- instead of stopping after the first field. Fixtures
are the exact ``html_to_text`` output the lane saw for Indianapolis rows 25
(Hampton Inn NE/Castleton: tiers, count and species lost) and 27 (Hampton Inn
Northwest Park 100: "Max weight 100 lbs" lost).

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

from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "pettripfinder" / "fixtures" / "static_lane_p5"
DEFECT = "PTF-DEFECT-STATIC-LANE-BLOCK-TRUNCATION-001"


@pytest.fixture(scope="module")
def meta():
    return json.loads((FIXTURES / "indianapolis_rows_25_27_fixture.json").read_text(encoding="utf-8"))


def _text(meta, row):
    return (FIXTURES / meta["rows"][str(row)]["static_text_file"]).read_text(encoding="utf-8")


def test_fixtures_reproduce_the_truncation(meta):
    for row in ("25", "27"):
        hit = UC.locate_policy_in_text(_text(meta, row))
        assert hit.found
        assert hit.text == meta["rows"][row]["located_block_as_captured"]
        assert hit.text.endswith("Non-refundable Fee")
        for fact in meta["rows"][row]["facts_the_page_states_after_the_block"]:
            assert fact in _text(meta, row)
            assert fact not in hit.text


@pytest.mark.xfail(strict=True, reason=DEFECT + ": tiers, count and species are cut off (row 25)")
def test_row_25_block_keeps_the_tiers_count_and_species(meta):
    hit = UC.locate_policy_in_text(_text(meta, "25"))
    assert "1-4 night stay $50" in hit.text
    assert "5+ night stay $75" in hit.text
    assert "2 pets max" in hit.text
    assert "dog or cat only" in hit.text


@pytest.mark.xfail(strict=True, reason=DEFECT + ": the weight limit is cut off (row 27)")
def test_row_27_block_keeps_the_weight_limit(meta):
    hit = UC.locate_policy_in_text(_text(meta, "27"))
    assert "100 lbs" in hit.text

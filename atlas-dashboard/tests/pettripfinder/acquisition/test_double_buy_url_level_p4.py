"""PTF-DEFECT-URL-LEVEL-DOUBLE-BUY-001 (P4).

Two census identities that resolve to the same canonical property page must not
both be bought. Indianapolis rows 25/26 (Hampton Inn NE/Castleton, Hilton
``indnehx``) are the fixture: the OSM key was bought in pass 1, the prior-census
key for the SAME URL was bought again in pass 2, and
``cohort_cost_plan.double_buy_check`` reported ``no_property_is_bought_twice``.

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

from scripts.pettripfinder.acquisition import cohort_cost_plan as CCP  # noqa: E402

FIXTURE = (REPO_ROOT / "tests" / "pettripfinder" / "fixtures" / "double_buy_p4"
           / "indianapolis_castleton_pair.json")
DEFECT = "PTF-DEFECT-URL-LEVEL-DOUBLE-BUY-001"


@pytest.fixture(scope="module")
def pair():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _norm(url: str) -> str:
    return url.rstrip("/").lower()


def test_fixture_is_one_page_under_two_keys(pair):
    rows = pair["pass1_cohort_rows"]
    assert len(rows) == 2
    assert len({r["identity_key"] for r in rows}) == 2
    assert len({_norm(r["source_url"]) for r in rows}) == 1
    # pass 2 re-bought the page for the second key after the first key had answered
    answered = [r for r in pair["prior_results_before_pass2"]
                if r["outcome"] in pair["terminal_outcomes"]]
    assert any(r["identity_key"] == "hampton inn indianapolis ne castleton" for r in answered)
    assert pair["pass2_cohort_rows"][0]["identity_key"] == "hampton inn indianapolis northeast castleton"
    assert pair["pass2_double_buy_check_as_recorded"]["no_property_is_bought_twice"] is True


@pytest.mark.xfail(strict=True, reason=DEFECT + ": the check keys on identity, not on the page")
def test_a_page_already_answered_under_another_key_is_not_bought_again(pair, tmp_path):
    prior = {"results": [
        {"identity_key": "hampton inn indianapolis ne castleton",
         "source_url": "https://www.hilton.com/en/hotels/indnehx-hampton-indianapolis-ne-castleton",
         "outcome": "VALID"}]}
    check = CCP.double_buy_check(pair["pass2_cohort_rows"], prior, tmp_path / "journal.jsonl",
                                 pair["terminal_outcomes"])
    assert check["no_property_is_bought_twice"] is False


@pytest.mark.xfail(strict=True, reason=DEFECT + ": two keys for one page inside one cohort")
def test_two_keys_for_one_page_inside_one_cohort_fail_the_proof(pair, tmp_path):
    check = CCP.double_buy_check(pair["pass1_cohort_rows"], {"results": []},
                                 tmp_path / "journal.jsonl", pair["terminal_outcomes"])
    assert check["no_property_is_bought_twice"] is False

"""PTF-DEFECT-LOCATOR-RECOVERY-FACT-LOSS-001 (P3).

``recover_richer_block`` may replace a located policy block with a different
window of the same document only when the replacement is demonstrably
equal-or-better in policy-fact coverage. Indianapolis founder-review row 20
(Fairfield Inn & Suites Indianapolis Northwest, captured 2026-08-25) is the
fixture: the located "Pet Policy" block stated the fee ("Non-refundable fee:
$75 USD Per Stay"), the count and the weight; recovery swapped in the FAQ
block because it carried "75.0 lbs" and the fee was lost, so the record
published "pet_fee: Not stated" against a page that states $75 per stay.

The tests are marked xfail(strict=True) until the fix lands: they document the
defect today and will fail loudly -- forcing the marker off -- once recovery
stops discarding supported facts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402

FIXTURES = (REPO_ROOT / "tests" / "pettripfinder" / "fixtures"
            / "locator_recovery_p3")
DEFECT = "PTF-DEFECT-LOCATOR-RECOVERY-FACT-LOSS-001"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def row20():
    return {
        "block": _read("indianapolis_row20_fairfield_northwest_located_block.txt"),
        "document": _read("indianapolis_row20_fairfield_northwest_document_text.txt"),
        "persisted": _read(
            "indianapolis_row20_fairfield_northwest_recovered_block_as_persisted.txt"),
    }


def test_fixture_reproduces_the_indianapolis_row_20_recovery(row20):
    """The defect is real on this input: recovery fires and drops the fee."""
    rec = PS.recover_richer_block(row20["block"], row20["document"])
    assert rec.recovered, rec.reason
    assert "$75" in row20["block"] and "per stay" in row20["block"].lower()
    assert "$75" not in rec.text
    assert PS.MS.collapse(rec.text) == PS.MS.collapse(row20["persisted"])


@pytest.mark.xfail(strict=True, reason=DEFECT + ": recovery discards the fee")
def test_recovery_never_loses_an_actionable_term_the_located_block_stated(row20):
    rec = PS.recover_richer_block(row20["block"], row20["document"])
    before = PS.actionable_pet_terms(PS.MS.collapse(row20["block"]))
    after = PS.actionable_pet_terms(PS.MS.collapse(rec.text)) if rec.recovered else before
    lost = before - after
    assert not lost, "recovery lost supported policy terms: %s" % sorted(lost)


@pytest.mark.xfail(strict=True, reason=DEFECT + ": the fee sentence must survive")
def test_recovered_block_keeps_the_fee_sentence_or_recovery_declines(row20):
    rec = PS.recover_richer_block(row20["block"], row20["document"])
    kept = row20["block"] if not rec.recovered else rec.text
    assert "$75" in kept and "per stay" in kept.lower()

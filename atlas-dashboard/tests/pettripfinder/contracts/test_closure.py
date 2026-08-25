"""PTF-ST-LOUIS-MARKET-001 -- the market closure-ledger contract.

Two properties matter and neither is arithmetic:

* the vocabulary is the one Milwaukee's 038 was given, so lifting it out of a
  market-specific module cannot have changed a word;
* the ledger reconciles by SET. A ledger that sums to the right total over the
  wrong membership is the exact failure the partition contract already names.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.acquisition import closure_038 as C038
from scripts.pettripfinder.contracts import closure as CL


class TestVocabulary:
    def test_the_generic_vocabulary_is_milwaukees_vocabulary(self):
        """Extraction, not redefinition. If these ever disagree, two markets
        are telling a founder two different stories with the same words."""
        assert CL.DISPOSITIONS == C038.DISPOSITIONS

    def test_every_disposition_has_a_written_meaning(self):
        for name in CL.DISPOSITIONS:
            assert CL.DISPOSITION_MEANINGS.get(name), name

    def test_only_two_dispositions_are_authority(self):
        assert CL.AUTHORITY_DISPOSITIONS == {
            CL.AUTHORITY_PET_FRIENDLY, CL.AUTHORITY_VERIFIED_NO_PETS}


def row(key, disposition=CL.HELD_REVIEW, why="because"):
    return CL.ledger_row(identity_key=key, canonical_name=key.title(),
                         corridor="c", disposition=disposition, why=why)


class TestRow:
    def test_an_unknown_disposition_is_refused(self):
        with pytest.raises(CL.ClosureError):
            row("a", disposition="PROBABLY_FINE")

    def test_other_without_an_explanation_is_refused(self):
        with pytest.raises(CL.ClosureError):
            row("a", disposition=CL.OTHER, why="   ")

    def test_other_with_an_explanation_is_accepted(self):
        assert row("a", disposition=CL.OTHER, why="the census is in question")


class TestReconciliation:
    def test_a_missing_active_identity_fails_closed(self):
        with pytest.raises(CL.ClosureError):
            CL.document("m", [row("a")], work_order="w", as_of="d",
                        active_keys=["a", "b"])

    def test_a_foreign_row_fails_closed(self):
        with pytest.raises(CL.ClosureError):
            CL.document("m", [row("a"), row("z")], work_order="w", as_of="d",
                        active_keys=["a"])

    def test_a_duplicate_row_fails_closed(self):
        with pytest.raises(CL.ClosureError):
            CL.document("m", [row("a"), row("a")], work_order="w", as_of="d",
                        active_keys=["a"])

    def test_wrong_membership_at_the_right_total_still_fails(self):
        """The whole point: two rows, two active identities, one of each
        wrong. Every count matches and the ledger is still a lie."""
        problems = CL.reconcile([row("a"), row("x")], ["a", "b"])
        assert problems["ledger_count"] == problems["active_count"] == 2
        assert problems["missing"] == ["b"]
        assert problems["foreign"] == ["x"]

    def test_a_clean_ledger_reports_its_own_denominator(self):
        doc = CL.document("m", [row("a"), row("b")], work_order="w",
                          as_of="d", active_keys=["a", "b"])
        assert doc["active_denominator"] == 2
        assert doc["count"] == 2
        assert doc["disposition_counts"][CL.HELD_REVIEW] == 2
        assert doc["reconciliation"]["missing"] == []

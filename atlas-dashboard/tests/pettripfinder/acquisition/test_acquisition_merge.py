"""PTF-ST-LOUIS-PAID-ACQUISITION-002 -- folding several passes into one view.

The failure this prevents is quiet, which is why it needs pinning: a property
acquired by the paid lane still reads UNHYDRATED from the free lane's report,
and the closure ledger tells a founder ACCESS_UNRESOLVED about a hotel whose
policy is already on disk.
"""

from __future__ import annotations

from scripts.pettripfinder.acquisition import acquisition_merge as AM
from scripts.pettripfinder.brightdata import outcomes as O


def pass_doc(*rows):
    return {"results": [dict(r) for r in rows]}


def row(key, outcome, **extra):
    out = {"identity_key": key, "outcome": outcome}
    out.update(extra)
    return out


class TestPrecedence:
    def test_a_later_pass_replaces_an_earlier_one_at_equal_rank(self):
        rows, superseded = AM.merge([
            ("first", pass_doc(row("a", O.UNHYDRATED))),
            ("second", pass_doc(row("a", O.ACCESS_DENIED))),
        ])
        assert [r["outcome"] for r in rows] == [O.ACCESS_DENIED]
        assert rows[0]["acquisition_pass"] == "second"
        assert superseded[0]["dropped_outcome"] == O.UNHYDRATED

    def test_a_later_success_replaces_an_earlier_failure(self):
        rows, _ = AM.merge([
            ("first", pass_doc(row("a", O.UNHYDRATED))),
            ("second", pass_doc(row("a", O.VALID))),
        ])
        assert rows[0]["outcome"] == O.VALID

    def test_a_later_transport_failure_never_un_reads_a_policy_on_disk(self):
        rows, superseded = AM.merge([
            ("first", pass_doc(row("a", O.VALID, artifact_dir="d"))),
            ("second", pass_doc(row("a", O.ACCESS_DENIED))),
        ])
        assert rows[0]["outcome"] == O.VALID
        assert rows[0]["artifact_dir"] == "d"
        assert rows[0]["acquisition_pass"] == "first"
        assert superseded[0]["dropped_pass"] == "second"

    def test_a_later_failure_never_erases_an_earlier_finding_about_the_hotel(self):
        # POLICY_NOT_FOUND and IDENTITY_MISMATCH are findings about the
        # PROPERTY; a failure to connect is a finding about us.
        for finding in (O.POLICY_NOT_FOUND, O.IDENTITY_MISMATCH):
            rows, _ = AM.merge([
                ("first", pass_doc(row("a", finding))),
                ("second", pass_doc(row("a", O.NAVIGATION_FAILED))),
            ])
            assert rows[0]["outcome"] == finding

    def test_a_later_valid_still_beats_an_earlier_finding(self):
        rows, _ = AM.merge([
            ("first", pass_doc(row("a", O.POLICY_NOT_FOUND))),
            ("second", pass_doc(row("a", O.VALID))),
        ])
        assert rows[0]["outcome"] == O.VALID


class TestCoverage:
    def test_every_identity_from_every_pass_survives_exactly_once(self):
        rows, _ = AM.merge([
            ("first", pass_doc(row("a", O.VALID), row("b", O.UNHYDRATED))),
            ("second", pass_doc(row("b", O.VALID), row("c", O.ACCESS_DENIED))),
        ])
        assert [r["identity_key"] for r in rows] == ["a", "b", "c"]

    def test_rows_are_sorted_by_identity_so_the_document_is_stable(self):
        rows, _ = AM.merge([("only", pass_doc(row("z", O.VALID),
                                              row("a", O.VALID)))])
        assert [r["identity_key"] for r in rows] == ["a", "z"]

    def test_every_displaced_row_records_the_rule_that_displaced_it(self):
        _rows, superseded = AM.merge([
            ("first", pass_doc(row("a", O.VALID))),
            ("second", pass_doc(row("a", O.ACCESS_DENIED))),
        ])
        assert superseded[0]["kept_pass"] == "first"
        assert "does not un-read" in superseded[0]["why"]

    def test_one_pass_is_returned_unchanged(self):
        rows, superseded = AM.merge([("only", pass_doc(row("a", O.VALID)))])
        assert len(rows) == 1 and superseded == []

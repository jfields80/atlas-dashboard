"""PTF-LOUISVILLE-COVERAGE-EXPANSION-003 -- what the store does with a VALID row
that has no capture.

A market that has been built twice restates its earlier evidence as acquisition
rows, so a later pass derives its cohort by subtraction instead of paying again
for answers the market already owns. Those rows are VALID and carry no capture
of their own. The store is a projection of persisted artifacts: it cannot make an
observation out of a row that has none, and it must not fail the whole closeout
because one exists.
"""

from __future__ import annotations

from scripts.pettripfinder.acquisition import market_observation_store as MOS


def pilot(*results):
    return {"market_id": "louisville-ky", "results": list(results)}


RESTATED = {
    "identity_key": "baymont by wyndham louisville airport south",
    "outcome": "VALID",
    "acquisition_pass": "prior_acquisition_002.json",
    "note": "prior Louisville build recorded a founder-approved pet policy",
}


class TestRestatedPriorEvidence:
    def test_a_valid_row_with_no_capture_is_counted_not_crashed_on(self):
        records, refusals, restated = MOS.build(pilot(RESTATED),
                                                run_id="louisville-003")
        assert records == [] and refusals == []
        assert [r["identity_key"] for r in restated] == [RESTATED["identity_key"]]

    def test_the_reason_it_was_skipped_travels_with_it(self):
        _, _, restated = MOS.build(pilot(RESTATED), run_id="louisville-003")
        assert restated[0]["acquisition_pass"] == "prior_acquisition_002.json"
        assert restated[0]["note"]

    def test_a_row_that_is_not_valid_is_not_counted_as_restated(self):
        _, _, restated = MOS.build(
            pilot(dict(RESTATED, outcome="ACCESS_DENIED")),
            run_id="louisville-003")
        assert restated == []

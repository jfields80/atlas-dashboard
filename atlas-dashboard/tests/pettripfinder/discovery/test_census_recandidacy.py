"""PTF-LOUISVILLE-MARKET-REBUILD-002 -- re-censusing a market that predates the engine.

A market censused before ``census_projection`` existed has a census and no
candidates: the raw discovery output lived under gitignored ``data/`` and is
gone. This module turns that census back into candidates so a rebuild can
reconcile prior work against fresh discovery instead of having to choose between
trusting it and discarding it.

The tests that matter are about what it MUST NOT carry across, and about the one
thing a coordinate-based absorber cannot do for it.
"""

from __future__ import annotations

import pathlib

import pytest

from scripts.pettripfinder.discovery import census_recandidacy as CR


def _census_row(**over):
    row = {
        "identity_key": "the brown hotel",
        "canonical_name": "The Brown Hotel",
        "normalized_name": "the brown hotel",
        "address": "335 W Broadway",
        "city": "Louisville",
        "state": "KY",
        "postal_code": "40202",
        "phone": "5025831234",
        "official_url": "https://www.brownhotel.com/",
        "latitude": None,
        "longitude": None,
        "lodging_state": "LODGING_CONFIRMED",
        "identity_state": "IDENTITY_CONFIRMED",
        "policy_state": "POLICY_NOT_VERIFIED",
        "corridor": "louisville-ky__downtown",
    }
    row.update(over)
    return row


class TestItCarriesObservationNotVerdict:
    def test_it_keeps_what_a_provider_observed(self):
        c = CR.to_candidate(_census_row(), market_id="louisville-ky",
                            observed_at="2026-08-24")
        assert c["name"] == "The Brown Hotel"
        assert c["address_line"] == "335 W Broadway"
        assert c["postal_code"] == "40202"
        assert c["city"] == "Louisville"
        assert c["source_records"][0]["phone"] == "5025831234"
        assert c["website_url"] == "https://www.brownhotel.com/"

    def test_it_drops_every_conclusion_the_rebuild_is_re_deriving(self):
        """Re-importing a verdict as an input is how a census ends up confirming
        only itself."""
        c = CR.to_candidate(_census_row(), market_id="louisville-ky",
                            observed_at="2026-08-24")
        blob = repr(c)
        for verdict in ("IDENTITY_CONFIRMED", "POLICY_NOT_VERIFIED",
                        "louisville-ky__downtown"):
            assert verdict not in blob, verdict
        for key in ("identity_state", "policy_state", "corridor", "lodging_state"):
            assert key not in c

    def test_an_unconfirmed_row_asserts_no_category(self):
        """A prior build that could not confirm lodging must not have its
        uncertainty upgraded on the way back in."""
        confirmed = CR.to_candidate(_census_row(), market_id="m",
                                    observed_at="2026-08-24")
        unconfirmed = CR.to_candidate(_census_row(lodging_state="LODGING_UNCONFIRMED"),
                                      market_id="m", observed_at="2026-08-24")
        assert confirmed["source_records"][0]["provider_categories"] == ["hotel"]
        assert unconfirmed["source_records"][0]["provider_categories"] == []

    def test_a_re_candidated_row_is_labelled_as_one(self):
        c = CR.to_candidate(_census_row(), market_id="m", observed_at="2026-08-24")
        assert CR.is_prior_census_candidate(c)
        assert c["source_records"][0]["provider"] == CR.PRIOR_CENSUS_PROVIDER
        assert not CR.is_prior_census_candidate({"candidate_id": "osm-1"})


class TestStreetAbsorption:
    """The gap: a census written before the engine carries NO coordinates."""

    def _fresh(self, **over):
        c = {"candidate_id": "osm-1", "name": "The Brown Hotel Louisville",
             "address_line": "335 West Broadway", "postal_code": "40202",
             "latitude": 38.2489, "longitude": -85.7605}
        c.update(over)
        return c

    def test_a_coordinateless_prior_row_still_reconciles(self):
        prior = CR.to_candidate(_census_row(), market_id="m",
                                observed_at="2026-08-24")
        assert prior["latitude"] is None, "the premise of this test"
        survivors, absorbed = CR.absorb_prior_by_street([self._fresh()], [prior])
        assert survivors == []
        assert len(absorbed) == 1
        assert absorbed[0]["into_candidate_id"] == "osm-1"

    def test_the_fresh_row_survives_and_remembers_the_prior_key(self):
        fresh = self._fresh()
        prior = CR.to_candidate(_census_row(), market_id="m",
                                observed_at="2026-08-24")
        CR.absorb_prior_by_street([fresh], [prior])
        assert fresh["prior_census_identity_keys"] == ["the brown hotel"]

    def test_a_different_building_is_never_absorbed(self):
        prior = CR.to_candidate(_census_row(), market_id="m",
                                observed_at="2026-08-24")
        other = self._fresh(address_line="140 N Fourth St", postal_code="40202")
        survivors, absorbed = CR.absorb_prior_by_street([other], [prior])
        assert absorbed == []
        assert len(survivors) == 1

    def test_a_row_with_no_usable_address_is_never_absorbed(self):
        """No street identity means no evidence of sameness, and absorbing on
        no evidence is how two hotels become one."""
        prior = CR.to_candidate(_census_row(address="", postal_code=""),
                                market_id="m", observed_at="2026-08-24")
        survivors, absorbed = CR.absorb_prior_by_street([self._fresh()], [prior])
        assert absorbed == []
        assert len(survivors) == 1

    def test_absorption_is_reported_and_never_silent(self):
        prior = CR.to_candidate(_census_row(), market_id="m",
                                observed_at="2026-08-24")
        _s, absorbed = CR.absorb_prior_by_street([self._fresh()], [prior])
        row = absorbed[0]
        for field in ("absorbed_candidate_id", "absorbed_name",
                      "into_candidate_id", "into_name", "street_identity",
                      "basis"):
            assert row.get(field), field


class TestMerge:
    def test_fresh_discovery_comes_first_so_it_outranks(self):
        merged = CR.merge([{"candidate_id": "osm-1"}], [{"candidate_id": "p-1"}])
        assert [c["candidate_id"] for c in merged] == ["osm-1", "p-1"]

    def test_an_id_is_never_duplicated(self):
        merged = CR.merge([{"candidate_id": "a"}],
                          [{"candidate_id": "a"}, {"candidate_id": "b"}])
        assert [c["candidate_id"] for c in merged] == ["a", "b"]


# PTF-DETROIT-ANN-ARBOR-HARDENED-MEMBERSHIP-AND-SHADOW-RECENSUS-002: this
# module was synced onto the Detroit branch as a generic dependency of the
# recensus engine. Its unit tests above are generic and run here; the class
# below reads Louisville's committed census, which lives on the branch that
# owns that market. Skipped rather than deleted, so it lights up unchanged
# the moment the two lineages converge.
@pytest.mark.skipif(
    not (pathlib.Path("launch_packages/pettripfinder/identity_census")
         / "louisville-ky.json").exists(),
    reason="louisville-ky census is not committed on this branch")
class TestTheLouisvilleCensusItProduced:
    """The committed result, as evidence that the module did its job."""

    @staticmethod
    def _census():
        import json
        import pathlib
        return json.loads(pathlib.Path(
            "launch_packages/pettripfinder/identity_census/louisville-ky.json"
        ).read_text(encoding="utf-8"))

    @staticmethod
    def _ledger():
        import json
        import pathlib
        return json.loads(pathlib.Path(
            "launch_packages/pettripfinder/louisville_ky_candidate_ledger_001.json"
        ).read_text(encoding="utf-8"))

    def test_every_candidate_reconciles_to_exactly_one_disposition(self):
        ledger = self._ledger()
        rows = ledger["candidates"]
        assert len(rows) == ledger["count"]
        assert len({r["candidate_id"] for r in rows}) == len(rows)
        assert sum(ledger["disposition_counts"].values()) == len(rows)

    def test_the_admitted_count_is_the_census_count(self):
        ledger, census = self._ledger(), self._census()
        assert ledger["disposition_counts"]["ADMITTED_TO_CENSUS"] == census["count"]
        assert census["count"] == len(census["hotels"]) == 166

    def test_the_rebuild_found_what_the_prior_census_did_not(self):
        """130 -> 166. The prior build's gap was not geography: 36 of these sit
        in postal codes its own corridor registry already claimed."""
        assert self._census()["count"] == 166

    def test_no_census_row_is_missing_its_locality(self):
        for row in self._census()["hotels"]:
            assert row.get("city"), row["identity_key"]
            assert row.get("postal_code"), row["identity_key"]
            assert row.get("corridor"), row["identity_key"]

    def test_identity_keys_are_unique(self):
        keys = [r["identity_key"] for r in self._census()["hotels"]]
        assert len(set(keys)) == len(keys)

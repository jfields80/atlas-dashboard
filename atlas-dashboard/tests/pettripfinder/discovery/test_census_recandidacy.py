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


class TestTheCommand:
    """PTF-INDIANAPOLIS-HARDENED-RECENSUS-002: the second rebuild needed the same
    three calls Louisville made by hand, so they are one command now."""

    def _run(self, tmp_path, fresh_address="335 W Broadway"):
        import json
        census = {"schema": "ptf-market-identity-census/1.1",
                  "market_id": "louisville-ky", "work_order": "PTF-PRIOR-001",
                  "hotels": [_census_row(),
                             _census_row(identity_key="the seelbach",
                                         canonical_name="The Seelbach",
                                         normalized_name="the seelbach",
                                         address="500 S 4th St")]}
        fresh = [{"candidate_id": "dc_fresh", "name": "Brown Hotel",
                  "normalized_name": "brown hotel", "address_line": fresh_address,
                  "postal_code": "40202", "city": "Louisville",
                  "latitude": 38.24, "longitude": -85.75,
                  "category_candidates": ["hotel"], "source_records": []}]
        (tmp_path / "census.json").write_text(json.dumps(census), encoding="utf-8")
        (tmp_path / "fresh.json").write_text(json.dumps(fresh), encoding="utf-8")
        rc = CR.main(["--prior-census", str(tmp_path / "census.json"),
                      "--discovery-candidates", str(tmp_path / "fresh.json"),
                      "--observed-at", "2026-08-25", "--work-order", "PTF-TEST",
                      "--out", str(tmp_path / "out" / "merged.json")])
        assert rc == 0
        merged = json.loads((tmp_path / "out" / "merged.json").read_text(encoding="utf-8"))
        doc = json.loads((tmp_path / "out" / "merged_prior_absorptions.json")
                         .read_text(encoding="utf-8"))
        return merged, doc

    def test_it_absorbs_a_prior_row_into_the_fresh_hit_at_the_same_street(self, tmp_path):
        merged, doc = self._run(tmp_path)
        assert doc["prior_census_rows"] == 2
        assert doc["absorbed_into_fresh"] == 1
        assert doc["prior_rows_surviving_on_their_own_evidence"] == 1
        assert doc["merged_candidates"] == 2 == len(merged)
        ids = [c["candidate_id"] for c in merged]
        assert ids[0] == "dc_fresh", "fresh discovery outranks a re-candidated row"
        assert "prior-census::the seelbach" in ids
        assert "prior-census::the brown hotel" not in ids
        assert merged[0]["prior_census_identity_keys"] == ["the brown hotel"]

    def test_a_prior_row_nobody_rediscovered_survives_on_its_own_evidence(self, tmp_path):
        merged, doc = self._run(tmp_path, fresh_address="1 Somewhere Else")
        assert doc["absorbed_into_fresh"] == 0
        assert doc["merged_candidates"] == 3 == len(merged)

    def test_it_records_where_every_input_came_from(self, tmp_path):
        _merged, doc = self._run(tmp_path)
        assert doc["schema"] == "ptf-census-recandidacy/1.0"
        assert doc["prior_census_work_order"] == "PTF-PRIOR-001"
        assert doc["work_order"] == "PTF-TEST"
        assert doc["inputs"]["prior_census"].endswith("census.json")
        assert doc["inputs"]["discovery_candidates"][0].endswith("fresh.json")


class TestNamesMustBeCompatibleToAbsorb:
    """PTF-INDIANAPOLIS-HARDENED-RECENSUS-002. Street identity alone merged two
    dual-brand buildings into one hotel each and put a Wingate under a stale
    OpenStreetMap "Baymont"; it also replaced 19 specific prior names with the
    provider's bare brand, which is how identity keys collide."""

    def _fresh(self, name, **over):
        c = {"candidate_id": "osm-1", "name": name,
             "address_line": "601 West Washington Street", "postal_code": "46204",
             "latitude": 39.76, "longitude": -86.16}
        c.update(over)
        return c

    def _prior(self, name, **over):
        return CR.to_candidate(_census_row(identity_key=name.lower(), canonical_name=name,
                                           normalized_name=name.lower(),
                                           address="601 W Washington St",
                                           postal_code="46204", **over),
                               market_id="m", observed_at="2026-08-25")

    def test_a_dual_brand_building_keeps_both_hotels(self):
        fresh = self._fresh("Courtyard Indianapolis Downtown")
        prior = self._prior("SpringHill Suites by Marriott Indianapolis Downtown")
        conflicts = []
        survivors, absorbed = CR.absorb_prior_by_street([fresh], [prior], conflicts=conflicts)
        assert absorbed == []
        assert len(survivors) == 1
        assert survivors[0]["street_shared_with"] == ["osm-1"]
        assert fresh["street_shared_with"] == [survivors[0]["candidate_id"]]
        assert conflicts[0]["relation"] == CR.NAME_CONFLICT
        assert conflicts[0]["resolution"].startswith("NOT_ABSORBED")

    def test_a_contained_name_still_absorbs(self):
        fresh = self._fresh("Courtyard Indianapolis Downtown")
        prior = self._prior("Courtyard by Marriott Indianapolis Downtown")
        survivors, absorbed = CR.absorb_prior_by_street([fresh], [prior])
        assert survivors == [] and len(absorbed) == 1

    def test_the_fuller_prior_name_replaces_a_bare_brand_and_says_so(self):
        fresh = self._fresh("Home2 Suites")
        prior = self._prior("Home2 Suites by Hilton Indianapolis Airport")
        _s, absorbed = CR.absorb_prior_by_street([fresh], [prior])
        assert fresh["name"] == "Home2 Suites by Hilton Indianapolis Airport"
        assert fresh["name_before_recandidacy"] == "Home2 Suites"
        assert absorbed[0]["name_taken_from_prior"] == "Home2 Suites by Hilton Indianapolis Airport"
        assert absorbed[0]["name_relation"] == CR.NAME_FRESH_ABBREVIATES_PRIOR

    def test_a_fuller_fresh_name_is_kept(self):
        fresh = self._fresh("Courtyard Indianapolis Downtown")
        prior = self._prior("Courtyard Indianapolis")
        _s, absorbed = CR.absorb_prior_by_street([fresh], [prior])
        assert fresh["name"] == "Courtyard Indianapolis Downtown"
        assert "name_taken_from_prior" not in absorbed[0]
        assert absorbed[0]["name_relation"] == CR.NAME_PRIOR_ABBREVIATES_FRESH

    def test_build_reports_conflicts_and_name_upgrades(self):
        census = {"market_id": "m", "work_order": "OLD", "hotels": [
            _census_row(identity_key="hyatt house downtown", canonical_name="Hyatt House Downtown",
                        normalized_name="hyatt house downtown",
                        address="130 S Pennsylvania St", postal_code="46204"),
            _census_row(identity_key="home2 suites by hilton airport",
                        canonical_name="Home2 Suites by Hilton Airport",
                        normalized_name="home2 suites by hilton airport",
                        address="5905 W Minnesota St", postal_code="46241")]}
        discovery = [
            {"candidate_id": "osm-1", "name": "Hyatt Place Downtown",
             "address_line": "130 South Pennsylvania Street", "postal_code": "46204"},
            {"candidate_id": "osm-2", "name": "Home2 Suites",
             "address_line": "5905 West Minnesota Street", "postal_code": "46241"}]
        merged, doc = CR.build(census=census, discovery=discovery, observed_at="2026-08-25")
        assert doc["street_conflicts_not_absorbed"] == 1
        assert doc["names_taken_from_prior"] == 1
        assert doc["absorbed_into_fresh"] == 1
        assert doc["merged_candidates"] == 3 == len(merged)
        names = {c["candidate_id"]: c["name"] for c in merged}
        assert names["osm-2"] == "Home2 Suites by Hilton Airport"
        assert names["osm-1"] == "Hyatt Place Downtown"
        assert "prior-census::hyatt house downtown" in names


class TestAbsorptionFillsMissingLocality:
    def test_a_host_without_a_city_takes_it_from_the_prior_row(self):
        fresh = {"candidate_id": "osm-1", "name": "Embassy Suites by Hilton Indianapolis North",
                 "address_line": "3912 Vincennes Road", "postal_code": "46268",
                 "city": "", "state": ""}
        prior = CR.to_candidate(_census_row(identity_key="embassy suites by hilton indianapolis north",
                                            canonical_name="Embassy Suites by Hilton Indianapolis North",
                                            address="3912 Vincennes Rd", postal_code="46268",
                                            city="Indianapolis", state="IN"),
                                market_id="m", observed_at="2026-08-25")
        _s, absorbed = CR.absorb_prior_by_street([fresh], [prior])
        assert fresh["city"] == "Indianapolis"
        assert fresh["locality_taken_from_prior"] == ["city"]
        assert absorbed[0]["locality_taken_from_prior"] == ["city"]
        assert absorbed[0]["surviving_name"] == "Embassy Suites by Hilton Indianapolis North"

    def test_a_host_that_states_its_city_keeps_it(self):
        fresh = {"candidate_id": "osm-1", "name": "Brown Hotel",
                 "address_line": "335 West Broadway", "postal_code": "40202",
                 "city": "Louisville"}
        prior = CR.to_candidate(_census_row(city="Somewhere Else"), market_id="m",
                                observed_at="2026-08-25")
        _s, absorbed = CR.absorb_prior_by_street([fresh], [prior])
        assert fresh["city"] == "Louisville"
        assert "locality_taken_from_prior" not in absorbed[0]

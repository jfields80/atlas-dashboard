"""PTF-INDIANAPOLIS-HARDENED-RECENSUS-002 -- every prior row classified once.

A rebuild's candidate ledger says what happened to every CANDIDATE; the founder
asks what happened to every hotel the OLD build had, and whether the old build
still offers anything. Those are different questions and this module answers
the second one -- without ever carrying prior authority forward.
"""

from __future__ import annotations

import json

from scripts.pettripfinder.discovery import census_projection as CP
from scripts.pettripfinder.discovery import census_recandidacy as CR
from scripts.pettripfinder.discovery import prior_build_reconciliation as PBR


def _prior(*rows):
    return {"market_id": "m", "work_order": "OLD", "hotels": list(rows)}


def _row(key, name=None, **over):
    row = {"identity_key": key, "canonical_name": name or key.title(),
           "postal_code": "40202", "corridor": "m__core", "official_url": ""}
    row.update(over)
    return row


def _ledger(*entries):
    return {"candidates": list(entries)}


def _new(*rows):
    return {"market_id": "m", "hotels": list(rows)}


class TestClassification:
    def test_a_prior_row_that_survived_alone_is_matched_existing(self):
        doc = PBR.reconcile(
            prior_census=_prior(_row("brown hotel")),
            new_census=_new({"identity_key": "brown hotel", "official_url": "https://b/"}),
            candidate_ledger=_ledger({"candidate_id": CR.candidate_id_for("brown hotel"),
                                      "disposition": CP.ADMITTED,
                                      "identity_key": "brown hotel"}),
            absorptions={"absorptions": []})
        row = doc["rows"][0]
        assert row["classification"] == PBR.MATCHED_EXISTING
        assert row["new_identity_key"] == "brown hotel"
        assert row["new_census_url"] == "https://b/"

    def test_absorbed_into_a_fresh_hit_with_the_same_key_is_matched(self):
        doc = PBR.reconcile(
            prior_census=_prior(_row("brown hotel", "Brown Hotel")),
            new_census=_new({"identity_key": "brown hotel",
                             "prior_census_identity_keys": ["brown hotel"]}),
            candidate_ledger=_ledger(),
            absorptions={"absorptions": [{
                "absorbed_candidate_id": CR.candidate_id_for("brown hotel"),
                "into_candidate_id": "dc_1", "into_name": "Brown Hotel"}]})
        assert doc["rows"][0]["classification"] == PBR.MATCHED_EXISTING

    def test_absorbed_into_a_fresh_hit_with_a_different_name_is_renamed(self):
        doc = PBR.reconcile(
            prior_census=_prior(_row("brown hotel", "Brown Hotel")),
            new_census=_new({"identity_key": "the brown a hilton hotel",
                             "prior_census_identity_keys": ["brown hotel"]}),
            candidate_ledger=_ledger(),
            absorptions={"absorptions": [{
                "absorbed_candidate_id": CR.candidate_id_for("brown hotel"),
                "into_candidate_id": "dc_1", "into_name": "The Brown, a Hilton Hotel"}]})
        row = doc["rows"][0]
        assert row["classification"] == PBR.RENAMED_REBRANDED
        assert row["new_identity_key"] == "the brown a hilton hotel"

    def test_the_rebuild_dispositions_map_to_geography_duplicate_and_unresolved(self):
        prior = _prior(_row("far inn"), _row("twin inn"), _row("bare brand"), _row("nowhere"))
        ledger = _ledger(
            {"candidate_id": CR.candidate_id_for("far inn"),
             "disposition": CP.OUT_OF_MARKET_BOUNDARY_DECISION, "why": "zip unclaimed"},
            {"candidate_id": CR.candidate_id_for("twin inn"),
             "disposition": CP.ABSORBED, "absorbed_into_name": "Twin Inn Downtown",
             "why": "one building seen twice"},
            {"candidate_id": CR.candidate_id_for("bare brand"),
             "disposition": CP.IDENTITY_COLLISION, "why": "also another building"},
            {"candidate_id": CR.candidate_id_for("nowhere"),
             "disposition": CP.NO_LOCALITY, "why": "no zip"})
        doc = PBR.reconcile(prior_census=prior,
                            new_census=_new({"identity_key": "twin inn downtown"}),
                            candidate_ledger=ledger, absorptions={"absorptions": []})
        by = {r["identity_key"]: r for r in doc["rows"]}
        assert by["far inn"]["classification"] == PBR.OUT_OF_CURRENT_GEOGRAPHY
        assert by["twin inn"]["classification"] == PBR.DUPLICATE
        assert by["twin inn"]["new_identity_key"] == "twin inn downtown"
        assert by["bare brand"]["classification"] == PBR.UNRESOLVED_IDENTITY
        assert by["nowhere"]["classification"] == PBR.UNRESOLVED_IDENTITY
        assert doc["classification_counts"] == {
            PBR.MATCHED_EXISTING: 0, PBR.RENAMED_REBRANDED: 0, PBR.DUPLICATE: 1,
            PBR.OUT_OF_CURRENT_GEOGRAPHY: 1, PBR.UNRESOLVED_IDENTITY: 2}

    def test_every_prior_row_is_classified_exactly_once(self):
        prior = _prior(*[_row("h%d" % i) for i in range(7)])
        doc = PBR.reconcile(prior_census=prior, new_census=_new(),
                            candidate_ledger=_ledger(), absorptions={"absorptions": []})
        assert len(doc["rows"]) == 7 == sum(doc["classification_counts"].values())


class TestWhatThePriorBuildStillOffers:
    def test_a_property_page_url_is_useful_and_a_brand_index_is_not(self):
        prior = _prior(
            _row("a", official_url="https://www.ihg.com/holidayinnexpress/hotels/us/en/plainfield/indsw/hoteldetail"),
            _row("b", official_url="https://www.ihg.com/holidayinnexpress/hotels/us/en/find-hotels/hotel-search?city=indianapolis"))
        doc = PBR.reconcile(prior_census=prior, new_census=_new(),
                            candidate_ledger=_ledger(), absorptions={"absorptions": []})
        by = {r["identity_key"]: r for r in doc["rows"]}
        assert PBR.USEFUL_SOURCE_URL in by["a"]["flags"]
        assert PBR.USEFUL_SOURCE_URL not in by["b"]["flags"]

    def test_prior_evidence_and_prior_authority_are_reported_never_carried(self, tmp_path):
        artifact = tmp_path / "pass1.json"
        artifact.write_text(json.dumps({"results": [
            {"identity_key": "a", "outcome": "CAPTURED"}]}), encoding="utf-8")
        package = {"published": True, "hotels": [{"identity_key": "b", "name": "B"}]}
        prior = _prior(_row("a"), _row("b"), _row("c"))
        doc = PBR.reconcile(prior_census=prior,
                            new_census=_new({"identity_key": "a"}, {"identity_key": "c"}),
                            candidate_ledger=_ledger(), absorptions={"absorptions": []},
                            policy_package=package, evidence_artifacts=[artifact])
        by = {r["identity_key"]: r for r in doc["rows"]}
        assert by["a"]["flags"] == [PBR.USEFUL_POLICY_EVIDENCE]
        assert by["a"]["evidence_artifacts"] == [artifact.as_posix()]
        assert by["b"]["flags"] == [PBR.PRIOR_AUTHORITY_MATCH]
        assert by["c"]["flags"] == []
        assert doc["prior_authority_published"] == 1
        # b is published but NOT in the new census: the match is unmatched, and
        # nothing in the document grants it a place.
        assert doc["prior_authority_matched"] == 0
        assert doc["prior_authority_unmatched"] == ["b"]
        assert "authority" not in json.dumps(doc["rows"]).lower().replace("prior_authority_match", "")

    def test_newly_discovered_identities_are_those_no_prior_row_reaches(self):
        doc = PBR.reconcile(
            prior_census=_prior(_row("old")),
            new_census=_new({"identity_key": "old"},
                            {"identity_key": "renamed", "prior_census_identity_keys": ["old"]},
                            {"identity_key": "brand new"}),
            candidate_ledger=_ledger(), absorptions={"absorptions": []})
        assert doc["newly_discovered_identity_keys"] == ["brand new"]


class TestAnUpgradedHostIsStillAMatch:
    def test_the_host_is_resolved_through_the_ledger_not_its_old_name(self):
        """Recandidacy gave the host the prior's fuller name; the absorption
        record's ``into_name`` is the bare brand it had before."""
        doc = PBR.reconcile(
            prior_census=_prior(_row("home2 suites by hilton indianapolis airport",
                                     "Home2 Suites by Hilton Indianapolis Airport")),
            new_census=_new({"identity_key": "home2 suites by hilton indianapolis airport"}),
            candidate_ledger=_ledger({"candidate_id": "dc_1", "disposition": CP.ADMITTED,
                                      "identity_key": "home2 suites by hilton indianapolis airport"}),
            absorptions={"absorptions": [{
                "absorbed_candidate_id": CR.candidate_id_for("home2 suites by hilton indianapolis airport"),
                "into_candidate_id": "dc_1", "into_name": "Home2 Suites",
                "surviving_name": "Home2 Suites by Hilton Indianapolis Airport"}]})
        assert doc["rows"][0]["classification"] == PBR.MATCHED_EXISTING

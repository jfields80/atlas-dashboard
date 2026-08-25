"""PTF-LOUISVILLE-FOUNDER-FINAL-006 -- what the signed Louisville authority must
be able to say about itself.

The ledger, the authority and the census are three files that can drift apart in
silence, and each of the ways they can is a different kind of wrong: a row in the
authority that no founder signed, a signature over a record that has since
changed, an authority row that names no census identity, and a held row that
entered anyway. These are the assertions that would catch each one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"


def load(name):
    return json.loads((PKG / name).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def census():
    return load("identity_census/louisville-ky.json")


@pytest.fixture(scope="module")
def closure():
    return load("louisville_ky_closure_ledger_006.json")


@pytest.fixture(scope="module")
def store():
    return load("louisville_ky_observation_store_006.json")


@pytest.fixture(scope="module")
def ledger():
    return load("louisville_ky_founder_decisions_006.json")


@pytest.fixture(scope="module")
def authority():
    return load("louisville_ky_proposed_authority_006.json")


def authority_rows(authority):
    return authority["pet_friendly"] + authority["verified_no_pets"]


#: The last row Louisville held, released by one final offline identity check.
CANDLEWOOD = "candlewood suites louisville south fair and expo"


@pytest.fixture(scope="module")
def ruling():
    overrides = load("markets/founder_overrides/louisville-ky.json")
    return next(r for r in overrides["identity_overrides"]["records"]
                if r["identity_key"] == CANDLEWOOD)


class TestTheCensusIsUnchanged:
    def test_the_census_still_holds_exactly_166_identities(self, census):
        assert census["count"] == 166 == len(census["hotels"])

    def test_closure_accounts_for_every_one_of_them(self, census, closure):
        assert closure["count"] == closure["active_denominator"] == 166
        assert {r["identity_key"] for r in closure["rows"]} == \
            {h["identity_key"] for h in census["hotels"]}
        for field in ("missing", "duplicate", "foreign"):
            assert closure["reconciliation"][field] == []


class TestOnlyASignedRowIsAuthority:
    def test_every_authority_row_was_signed_by_the_founder(self, authority, ledger):
        signed = {r["identity_key"] for r in ledger["signed"]}
        assert {r["normalized_name"] for r in authority_rows(authority)} == signed

    def test_the_ledger_signs_only_what_it_was_authorised_to(self, ledger):
        assert ledger["withheld_count"] == 0
        assert set(ledger["signed_by_authority"]) == {"PUBLISHED_PET_FRIENDLY",
                                                      "VERIFIED_NO_PETS"}
        assert ledger["signed_count"] == 63

    def test_who_decided_and_who_typed_are_different_fields(self, ledger):
        assert ledger["decided_by"] == "jfields80"
        assert "claude" in ledger["recorded_by"].lower()
        assert "transcription only" in ledger["recorded_by"]
        assert ledger["authorization"]

    def test_no_row_is_signed_twice(self, ledger):
        keys = [r["identity_key"] for r in ledger["signed"]]
        assert len(keys) == len(set(keys))


class TestTheSignatureStillCoversTheRecord:
    def test_every_signature_binds_the_hash_it_was_shown(self, ledger, store):
        """A signature binds a semantic hash. If the record changes afterwards
        the hash stops matching, and the ledger visibly no longer covers it."""
        hashes = {r["identity_key"]: r["semantic_approval"]["semantic_hash"]
                  for r in load("louisville_ky_founder_review_packet_006.json")
                  ["candidates"]}
        for row in ledger["signed"]:
            assert row["bound_semantic_hash"] == hashes[row["identity_key"]]

    def test_every_authority_row_keeps_its_evidence(self, authority):
        for row in authority_rows(authority):
            assert row["evidence"], row["canonical_name"]
            assert row["snapshot_hash"]
            assert row["source_url"]
            assert "withheld_fields" in row


class TestNothingHeldEnteredAuthority:
    def test_the_authority_is_exactly_the_held_review_population(
            self, authority, closure):
        held = {r["identity_key"] for r in closure["rows"]
                if r["disposition"] == "HELD_REVIEW"}
        assert {r["normalized_name"] for r in authority_rows(authority)} == held

    def test_every_authority_row_names_a_census_identity(self, authority, census):
        keys = {h["identity_key"] for h in census["hotels"]}
        for row in authority_rows(authority):
            assert row["normalized_name"] in keys, row["canonical_name"]

    def test_the_market_is_not_registered_by_any_of_this(self, authority):
        assert authority["registered"] is False
        assert authority["published"] is False
        assert authority["deployed"] is False
        assert not (PKG / "markets" / "authority" / "louisville-ky").exists()
        assert (PKG / "markets" / "pending" / "louisville-ky.json").is_file()


class TestTheCandlewoodIdentity:
    """The last held row, and the evidence that released it."""

    def test_it_rests_on_two_agreeing_signals_and_names_them(self, ruling):
        assert ruling["signals_agreeing"] == 2
        assert ruling["street"]["verdict"] == "EXACT MATCH"
        assert ruling["property_code"]["verdict"] == "EXACT MATCH"
        assert ruling["contradicting_evidence"].startswith("none")

    def test_the_absent_telephone_is_recorded_as_silence_not_agreement(self, ruling):
        assert ruling["telephone"]["census"] == ""
        assert "silence" in ruling["telephone"]["verdict"]

    def test_the_property_code_is_the_pages_own_and_an_independent_source(
            self, ruling):
        code = ruling["property_code"]["code"]
        assert code == "sdfpp"
        assert "canonical" in ruling["property_code"]["page"]
        independent = ruling["property_code"]["independent_source"]
        assert independent["source"] == "goto_louisville"
        assert code in independent["official_url"]

    def test_the_capture_was_not_redirected_to_another_property(self, ruling):
        assert ruling["redirect_check"]["requested"] == \
            ruling["redirect_check"]["final"]

    def test_the_row_is_in_the_authority_under_the_name_its_page_states(
            self, authority):
        row = next(r for r in authority_rows(authority)
                   if r["normalized_name"] == CANDLEWOOD)
        assert row["canonical_name"] == "Candlewood Suites Louisville - Fair/Expo Center"

    def test_the_census_row_itself_was_never_edited(self, census):
        row = next(h for h in census["hotels"] if h["identity_key"] == CANDLEWOOD)
        assert row["canonical_name"] == "Candlewood Suites Louisville South Fair and Expo"

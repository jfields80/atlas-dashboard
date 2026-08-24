"""PTF-ST-LOUIS-FOUNDER-DECISIONS-006 -- a human overruling a gate, on the record.

Two overrides exist here and neither is an inference the readers may make. The
tests that matter are the ones proving the machine still cannot reach them: an
override has to be PLACED in a file by a person, it applies to one named row, and
the gate it overrules is unchanged for every row that has no override.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.acquisition import market_observation_store as MOS
from scripts.pettripfinder.policy import policy_membrane as M
from scripts.pettripfinder.policy import policy_observation as PO

PKG = "launch_packages/pettripfinder/"


def _load(name):
    with open(PKG + name, encoding="utf-8") as handle:
        return json.load(handle)


def observation(**over):
    base = {
        "obs_id": "o", "contract_version": PO.CONTRACT_VERSION,
        "hotel_ref": {"market_id": "m", "canonical_name": "Comfort Inn Pacific",
                      "normalized_name": "comfort inn pacific",
                      "street_identity": "1320 thornton st|63069"},
        "identity_check": {"name_on_page": "Comfort Inn Near Six Flags",
                           "address_on_page": "1320 Thornton St."},
        "source_url": "https://www.choicehotels.com/mo/pacific/x/mo136",
        "source_type": "official_property_page",
        "authority_tier": PO.PT1_OFFICIAL_PROPERTY,
        "observed_at": "2026-08-23", "retrieved_at": "2026-08-23",
        "capture_method": "deterministic_fetch",
        "evidence": [{"quote": "Pets Welcome", "location": "block",
                      "field_refs": ["pets_allowed"]}],
        "extraction": {"pets_allowed": True},
        "extraction_confidence": "EXACT_QUOTE", "flags": [],
    }
    base.update(over)
    return base


class TestTheContractAmendment:
    def test_the_version_moved_and_older_records_still_validate(self):
        assert PO.CONTRACT_VERSION == "1.2.0"
        for older in ("1.0.0", "1.1.0"):
            assert older in PO.ACCEPTED_CONTRACT_VERSIONS

    def test_both_override_fields_are_optional_and_allowed(self):
        assert "founder_overrides" in PO.OPTIONAL_FIELDS
        assert "identity_adjudication" in PO.OPTIONAL_FIELDS
        # Optional means an observation without them is still valid.
        PO.validate_observation(observation())

    def test_an_unknown_field_is_still_refused(self):
        with pytest.raises(PO.PolicyObservationError):
            PO.validate_observation(observation(some_new_field=1))


class TestTheIdentityAdjudication:
    def test_a_name_mismatch_with_no_adjudication_is_still_refused(self):
        # The gate is unchanged for every row nobody ruled on.
        verdict = M.evaluate(observation())
        assert verdict.verdict == M.REJECT_WRONG_PROPERTY
        assert verdict.rule == "M10"

    def test_a_founder_adjudication_admits_that_same_row(self):
        verdict = M.evaluate(observation(identity_adjudication={
            "approved_by": "jfields80", "signals_agreeing": 2}))
        assert verdict.verdict == M.VALID

    def test_an_adjudication_with_no_approver_admits_nothing(self):
        # The field existing is not the ruling; a named human is.
        verdict = M.evaluate(observation(identity_adjudication={
            "approved_by": "", "signals_agreeing": 2}))
        assert verdict.verdict == M.REJECT_WRONG_PROPERTY

    def test_an_adjudication_does_not_excuse_any_other_rule(self):
        # M9: no field without a quote. An identity ruling says nothing about
        # evidence, and must not be read as a general override.
        verdict = M.evaluate(observation(
            identity_adjudication={"approved_by": "jfields80"},
            extraction={"pets_allowed": True, "pet_fee": 2500},
            evidence=[{"quote": "Pets Welcome", "location": "b",
                       "field_refs": ["pets_allowed"]}]))
        assert verdict.verdict == M.REJECT_FIELD_WITHOUT_EVIDENCE


class TestTheAllowanceOverride:
    def _observation(self):
        return {"extraction": {"pet_count_limit": 2},
                "evidence": [{"quote": "maximum of 2 dogs per room",
                              "field_refs": ["pet_count_limit"]},
                             {"quote": "Dogs Only", "field_refs": ["species_allowed"]}]}

    def test_it_sets_the_allowance_and_records_who_ruled(self):
        obs = self._observation()
        MOS._apply_allowance_override(obs, {
            "set_pets_allowed": True, "species_supported_by_the_text": ["dog"],
            "cited_quotes": ["maximum of 2 dogs per room"],
            "decided_by": "jfields80", "decided_at": "2026-08-23",
            "founder_ruling": "YES"})
        assert obs["extraction"]["pets_allowed"] is True
        assert obs["extraction"]["species_allowed"] == ["dog"]
        override = obs["founder_overrides"][0]
        assert override["decided_by"] == "jfields80"
        assert override["was_withheld_as"] == "SOURCE_SILENT"
        assert override["ruling"] == "YES"

    def test_the_cited_quote_is_the_property_s_own_text(self):
        # An evidence quote must stay something a reader can find on the page.
        # The founder's words are recorded, but never as a quote.
        obs = self._observation()
        MOS._apply_allowance_override(obs, {
            "set_pets_allowed": True,
            "cited_quotes": ["maximum of 2 dogs per room"],
            "decided_by": "f", "founder_ruling": "YES"})
        quotes = {e["quote"] for e in obs["evidence"]}
        assert "YES" not in quotes
        assert obs["founder_overrides"][0]["cited_quotes"] == \
            ["maximum of 2 dogs per room"]

    def test_a_quote_not_actually_on_the_page_is_not_cited(self):
        obs = self._observation()
        MOS._apply_allowance_override(obs, {
            "set_pets_allowed": True, "cited_quotes": ["invented text"],
            "decided_by": "f"})
        assert obs["founder_overrides"][0]["cited_quotes"] == []

    def test_the_allowance_becomes_quote_backed_so_m9_is_satisfied(self):
        obs = self._observation()
        MOS._apply_allowance_override(obs, {
            "set_pets_allowed": True,
            "cited_quotes": ["maximum of 2 dogs per room"], "decided_by": "f"})
        refs = [e for e in obs["evidence"] if "pets_allowed" in e["field_refs"]]
        assert refs, "the allowance must carry a quote or M9 refuses it"

    def test_species_are_not_widened_when_the_text_names_none(self):
        obs = {"extraction": {"pet_fee": 1500},
               "evidence": [{"quote": "15USD per pet per night",
                             "field_refs": ["pet_fee"]}]}
        MOS._apply_allowance_override(obs, {
            "set_pets_allowed": True, "species_supported_by_the_text": [],
            "cited_quotes": ["15USD per pet per night"], "decided_by": "f"})
        assert "species_allowed" not in obs["extraction"]


class TestTheCommittedDecisions:
    def test_the_overlay_records_who_decided_and_who_typed(self):
        overlay = _load("markets/founder_overrides/st-louis-mo.json")
        assert overlay["decided_by"] == "jfields80"
        assert "transcription only" in overlay["recorded_by"]
        assert overlay["scope_rule"]

    def test_the_three_allowance_rows_are_the_three_named(self):
        overlay = _load("markets/founder_overrides/st-louis-mo.json")
        keys = {r["identity_key"]
                for r in overlay["allowance_overrides"]["records"]}
        assert keys == {"comfort inn collinsville near st louis",
                        "super 8 by wyndham troy il st louis area",
                        "sonesta es suites st louis chesterfield"}

    def test_every_allowance_row_records_the_five_conditions(self):
        overlay = _load("markets/founder_overrides/st-louis-mo.json")
        for record in overlay["allowance_overrides"]["records"]:
            checked = record["conditions_checked"]
            assert checked["page_is_property_specific"] == "PROPERTY_PAGE"
            assert checked["identity_binding_valid"] == "membrane VALID"
            assert checked["no_contradictory_no_pets_statement"] is True
            assert checked["species_limit"]

    def test_only_dogs_are_asserted_where_only_dogs_are_stated(self):
        store = {r["identity_key"]: r
                 for r in _load("st_louis_mo_observation_store_006.json")["records"]}
        dogs = store["comfort inn collinsville near st louis"]["observation"]
        assert dogs["extraction"]["species_allowed"] == ["dog"]
        generic = store["super 8 by wyndham troy il st louis area"]["observation"]
        assert "species_allowed" not in generic["extraction"]

    def test_three_identities_approved_and_one_refused(self):
        overlay = _load("markets/founder_overrides/st-louis-mo.json")
        approved = {r["identity_key"]
                    for r in overlay["identity_overrides"]["records"]}
        refused = {r["identity_key"]
                   for r in overlay["identity_overrides"]["refused"]}
        assert approved == {"comfort inn pacific st louis",
                            "travelodge st louis airport", "wingate at wyndham"}
        assert refused == {"days inn and suites pontoon beach"}

    def test_every_approved_identity_names_two_agreeing_signals(self):
        overlay = _load("markets/founder_overrides/st-louis-mo.json")
        for record in overlay["identity_overrides"]["records"]:
            assert record["signals_agreeing"] >= 2, record["identity_key"]
            # "none" may carry its reasoning after it -- the Travelodge row
            # explains why a mailing city beside a municipality is not a
            # contradiction. The claim is what matters, not the string length.
            assert record["contradicting_evidence"].lower().startswith("none")

    def test_the_refused_row_names_only_one_agreeing_signal(self):
        overlay = _load("markets/founder_overrides/st-louis-mo.json")
        refused = overlay["identity_overrides"]["refused"][0]
        assert refused["signals_agreeing"] == 1
        assert "DIFFERENT" in refused["telephone"]["verdict"]
        assert refused["what_would_settle_it"]

    def test_the_refused_row_is_still_refused_by_the_membrane(self):
        store = {r["identity_key"]: r
                 for r in _load("st_louis_mo_observation_store_006.json")["records"]}
        row = store["days inn and suites pontoon beach"]
        assert row["membrane"]["verdict"] == M.REJECT_WRONG_PROPERTY
        assert not row["observation"].get("identity_adjudication")

    def test_only_hampton_got_a_name_authorisation(self):
        # Wingate's identity was approved, which surfaces its bare-chain name as
        # a correction. The founder authorised Hampton's name and not Wingate's,
        # so Wingate waits.
        overlay = _load("markets/name_corrections/st-louis-mo.json")
        keys = {r["identity_key"] for r in overlay["records"]}
        assert "hampton" in keys
        assert "wingate at wyndham" not in keys

    def test_the_114_existing_signatures_still_bind(self):
        ledger = _load("st_louis_mo_founder_decisions_005.json")
        packet = {c["identity_key"]: c
                  for c in _load("st_louis_mo_founder_review_packet_006.json")["candidates"]}
        for row in ledger["signed"]:
            current = packet[row["identity_key"]]["semantic_approval"]["semantic_hash"]
            assert current == row["bound_semantic_hash"], row["identity_key"]

    def test_everything_still_reconciles_to_357(self):
        closure = _load("st_louis_mo_closure_ledger_006.json")
        assert closure["count"] == closure["active_denominator"] == 357
        assert closure["reconciliation"]["missing"] == []
        assert closure["reconciliation"]["foreign"] == []
        assert closure["reconciliation"]["duplicate"] == []

    def test_all_122_are_reviewed_exactly_once(self):
        analysis = _load("st_louis_mo_founder_review_analysis_006.json")
        assert analysis["reviewed"] == analysis["candidates_in_packet"] == 122
        assert analysis["each_reviewed_exactly_once"] is True

    def test_the_market_is_still_unregistered(self):
        from pathlib import Path
        assert not (Path(PKG) / "markets" / "authority" / "st-louis-mo").exists()
        assert not (Path(PKG) / "markets" / "st-louis-mo.json").exists()

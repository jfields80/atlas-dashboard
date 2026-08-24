"""PTF-ST-LOUIS-RELEASE-CONTRACT-009 -- projecting an authority into schema 1.2.

The module this tests exists to REFUSE. Reshaping facts for publication is the
last place a wrong number can enter, and the only honest way to reshape is to
run the repository's own validator over every record and write nothing if any of
them raises. These tests are mostly about that refusal, and about the three
non-inferences the projection is forbidden to make.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder import market_policy_package_cli as PP
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import policy_schema as PS


class TestSpeciesIsAnAffirmativeMentionList:
    """PTF-POLICY-PARSER-SEMANTIC-HARDENING-017 retracted the opposite reading."""

    def test_a_named_species_becomes_accepted(self):
        facts, _ = PP.project_facts({"pets_allowed": True,
                                     "species_allowed": ["dog"]})
        assert facts["species"] == {"dogs": enums.SPECIES_ACCEPTED}

    def test_an_unnamed_species_is_not_prohibited(self):
        # The whole point: absence renders as "Not stated". Writing
        # {"cats": "prohibited"} here would invent a refusal.
        facts, _ = PP.project_facts({"pets_allowed": True,
                                     "species_allowed": ["dog"]})
        assert "cats" not in facts["species"]

    def test_an_explicit_refusal_is_carried(self):
        facts, _ = PP.project_facts({"pets_allowed": True,
                                     "cats_allowed": False})
        assert facts["species"] == {"cats": enums.SPECIES_PROHIBITED}

    def test_no_species_mentioned_emits_no_species_block(self):
        facts, _ = PP.project_facts({"pets_allowed": True})
        assert "species" not in facts

    def test_an_unrecognised_token_is_reported_not_guessed(self):
        facts, notes = PP.project_facts({"pets_allowed": True,
                                         "species_allowed": ["ferret"]})
        assert "species" not in facts
        assert notes and "ferret" in notes[0]


class TestWeightLimitKeepsOnlyWhatWasStated:
    def test_operator_and_scope_are_never_defaulted(self):
        # "maximum" / "up to" / "under" are recorded as a value only; defaulting
        # a comparison is a guest-visible error in BOTH directions, and the
        # reader's own non_inferences say so.
        facts, _ = PP.project_facts({"pets_allowed": True,
                                     "weight_limit": {"value": 50.0,
                                                      "unit": "lb"}})
        assert facts["weight_limit"] == {"value": 50.0, "unit": "lb"}
        assert "operator" not in facts["weight_limit"]
        assert "scope" not in facts["weight_limit"]

    def test_a_stated_operator_and_scope_are_carried(self):
        facts, _ = PP.project_facts({"pets_allowed": True, "weight_limit": {
            "value": 50.0, "unit": "lb", "operator": "lte",
            "scope": "per_pet"}})
        assert facts["weight_limit"]["operator"] == "lte"
        assert facts["weight_limit"]["scope"] == "per_pet"

    def test_a_bare_weight_limit_fails_the_1_2_schema(self):
        # This is the blocker, asserted rather than described: the projection is
        # faithful and the schema still refuses it, because 1.2 REQUIRES both.
        facts, _ = PP.project_facts({"pets_allowed": True,
                                     "weight_limit": {"value": 50.0,
                                                      "unit": "lb"}})
        issues = PS.validate_facts(facts)
        paths = {i.path for i in issues}
        assert "facts.weight_limit.scope" in paths
        assert "facts.weight_limit.operator" in paths


class TestFeeAndCap:
    def test_a_flat_fee_carries_only_the_stated_basis_and_scope(self):
        facts, _ = PP.project_facts({"pets_allowed": True, "pet_fee": 2500,
                                     "fee_currency": "USD"})
        assert facts["pet_fee"] == {"amount_cents": 2500, "currency": "USD"}

    def test_tiers_win_over_a_flat_fee(self):
        facts, _ = PP.project_facts({
            "pets_allowed": True, "pet_fee": 2500, "fee_currency": "USD",
            "fee_tiers": [{"amount_cents": 7500, "currency": "USD"}]})
        assert "fee_tiers" in facts and "pet_fee" not in facts

    def test_the_cap_amount_is_renamed_not_converted(self):
        facts, _ = PP.project_facts({
            "pets_allowed": True,
            "fee_cap": {"amount_minor": 7500, "currency": "USD",
                        "basis": "per_stay"}})
        assert facts["fee_cap"]["amount_cents"] == 7500
        assert facts["fee_cap"]["basis"] == "per_stay"

    def test_qualifier_stated_is_never_filled_in_by_the_projection(self):
        # _check_cap exists because a cap whose quote named a pet count and
        # whose structure lost it published a ceiling the hotel never quoted.
        # Asserting "no qualifier" is a claim about the source, not a reshape.
        facts, _ = PP.project_facts({
            "pets_allowed": True,
            "fee_cap": {"amount_minor": 7500, "currency": "USD"}})
        assert "qualifier_stated" not in facts["fee_cap"]
        assert any(i.path == "facts.fee_cap.qualifier_stated"
                   for i in PS.validate_facts(facts))


class TestTheBuilderRefusesRatherThanGuesses:
    def _authority(self, *facts):
        return {"market_id": "m", "schema": "s", "pet_friendly": [
            {"normalized_name": "k%d" % i, "canonical_name": "K%d" % i,
             "facts": f, "evidence": [], "source_url": "https://x",
             "snapshot_hash": "h", "observed_at": "d",
             "capture_method": "deterministic_fetch"}
            for i, f in enumerate(facts)]}

    def test_a_record_that_fails_the_schema_is_refused_not_repaired(self):
        built = PP.build(self._authority({"pets_allowed": True,
                                          "weight_limit": {"value": 50.0,
                                                           "unit": "lb"}}),
                         market_name="M")
        assert built["count"] == 0
        assert len(built["refusals"]) == 1
        assert any("weight_limit" in issue
                   for issue in built["refusals"][0]["issues"])

    def test_a_clean_record_projects(self):
        built = PP.build(self._authority({"pets_allowed": True}),
                         market_name="M")
        assert built["count"] == 1
        assert built["refusals"] == []
        assert built["hotels"][0]["facts"] == {"pets_allowed": True}

    def test_the_package_is_not_published_by_being_built(self):
        built = PP.build(self._authority({"pets_allowed": True}),
                         market_name="M")
        assert built["published"] is False
        # 009 asserted 1.2 because that was the current schema then. 010 made a
        # versioned additive amendment; what 009 actually claimed is that the
        # package targets the CURRENT schema, not that the schema is frozen.
        from scripts.pettripfinder.contracts import enums
        assert built["schema_version"] == enums.POLICY_SCHEMA_VERSION

    def test_the_cli_writes_nothing_when_any_record_is_refused(self, tmp_path):
        source = tmp_path / "auth.json"
        source.write_text(json.dumps(self._authority(
            {"pets_allowed": True, "weight_limit": {"value": 1, "unit": "lb"}})),
            encoding="utf-8")
        out = tmp_path / "package.json"
        with pytest.raises(PP.PolicyPackageError):
            PP.main(["--authority", str(source), "--market-name", "M",
                     "--out", str(out)])
        assert not out.exists(), "a refused projection must write no file"

    def test_a_count_mismatch_also_writes_nothing(self, tmp_path):
        source = tmp_path / "auth.json"
        source.write_text(json.dumps(self._authority({"pets_allowed": True})),
                          encoding="utf-8")
        out = tmp_path / "package.json"
        with pytest.raises(PP.PolicyPackageError):
            PP.main(["--authority", str(source), "--market-name", "M",
                     "--out", str(out), "--expect-count", "99"])
        assert not out.exists()


class TestTheStLouisGapWasReal:
    """009's finding, and what 010 did about it.

    009 measured a genuine gap: under schema 1.2 and the strict projection, only
    19 of 82 rows could be published. PTF-ST-LOUIS-PUBLICATION-SCHEMA-DECISIONS-
    010 closed it with four founder rulings and one additive amendment, so these
    tests now assert the SHAPE of what 009 found -- that the strict default still
    refuses most rows, and that closing it took explicit decisions -- rather than
    freezing the blocked state, which the founder has since unblocked.
    """

    @staticmethod
    def _authority():
        with open("launch_packages/pettripfinder/"
                  "st_louis_mo_proposed_authority_008b.json",
                  encoding="utf-8") as handle:
            return json.load(handle)

    def test_the_strict_default_projection_still_refuses_most_rows(self):
        # No founder ruling applied: this is what 009 measured, and it is still
        # what the projector does unless a caller names a decision.
        built = PP.build(self._authority(), market_name="St. Louis, Missouri")
        assert built["count"] + len(built["refusals"]) == 82
        assert built["count"] < 82, "the strict default must not pass everything"
        assert built["refusals"], "the gap 009 found is still there by default"

    def test_the_founder_rulings_are_what_close_it(self):
        built = PP.build(self._authority(), market_name="St. Louis, Missouri",
                         normalize_weight=True, cap_qualifier_stated=False)
        assert built["count"] == 82
        assert built["refusals"] == []

    def test_the_package_009_refused_to_write_now_exists_and_validates(self):
        # 009 wrote nothing because it could not do so honestly. 010 supplied
        # the decisions that made it honest, and the file is the proof.
        from pathlib import Path
        import json as _json
        from scripts.pettripfinder.contracts import policy_schema as _PS
        path = Path("launch_packages/pettripfinder/"
                    "hotel_policy_facts_st-louis-mo.json")
        assert path.exists()
        package = _json.loads(path.read_text(encoding="utf-8"))
        assert package["count"] == 82 and package["refusals"] == []
        for record in package["hotels"]:
            assert _PS.validate_facts(record["facts"]) == (), record["key"]

    def test_every_live_market_carries_operator_and_scope(self):
        # Why the gap is a decision and not a bug: five live markets all have
        # these fields, so the schema requirement is real and settled.
        for market in ("pittsburgh-pa", "milwaukee-wi", "dayton-oh"):
            with open("launch_packages/pettripfinder/"
                      "hotel_policy_facts_%s.json" % market,
                      encoding="utf-8") as handle:
                package = json.load(handle)
            weights = [h["facts"]["weight_limit"] for h in package["hotels"]
                       if "weight_limit" in h["facts"]]
            assert weights
            assert all("operator" in w and "scope" in w for w in weights)

    def test_no_live_market_carries_a_service_animal_statement_in_facts(self):
        # So dropping it is what the schema implies -- and it is a real loss
        # worth a decision, not a silent omission.
        for market in ("pittsburgh-pa", "milwaukee-wi", "dayton-oh"):
            with open("launch_packages/pettripfinder/"
                      "hotel_policy_facts_%s.json" % market,
                      encoding="utf-8") as handle:
                package = json.load(handle)
            assert not [h for h in package["hotels"]
                        if "service_animal_exception" in h["facts"]]

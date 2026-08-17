"""PTF-CONTRACT-FOUNDATION-001 -- one negative test per frozen rule.

A validator is only worth having if it REFUSES something. Each test below
names a shape that reached the corpus, or that the freeze exists to prevent,
and asserts the contract rejects it.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder import canonical_view
from scripts.pettripfinder.contracts import enums, evidence, withholding
from scripts.pettripfinder.contracts import policy_schema as ps
from scripts.pettripfinder.contracts.policy_schema import money, quantity
from scripts.pettripfinder.hotel_profile import _verified_details


def codes(issues):
    return {i.code for i in issues}


class TestSilenceIsAbsence:
    """No field is ever written as null or a sentinel to mean "unstated"."""

    @pytest.mark.parametrize("value", [None, "", "unknown", "unstated", "N/A"])
    def test_sentinels_rejected(self, value):
        issues = ps.validate_facts({"pet_count_scope": value})
        assert codes(issues) & {"NULL_FOR_SILENCE", "SENTINEL_FOR_SILENCE"}

    def test_absent_field_is_clean(self):
        assert ps.validate_facts({"pets_allowed": True}) == ()

    def test_unknown_field_is_reported(self):
        """A typo'd field name is invisible data, not a harmless extra."""
        assert "UNKNOWN_FIELD" in codes(ps.validate_facts({"fee_scop": "per_room"}))


class TestMoneyAndBooleans:

    def test_display_string_is_not_money(self):
        """"$50.00" is what the corpus stores and what 1.2 refuses."""
        assert codes(ps.validate_facts({"pet_fee": "$50.00"})) \
            & {"NOT_OBJECT", "NOT_MONEY"}

    def test_currency_is_mandatory(self):
        issues = ps.validate_facts({"pet_fee": {"amount_cents": 5000}})
        assert "MISSING_CURRENCY" in codes(issues)

    def test_float_amount_rejected(self):
        issues = ps.validate_facts(
            {"pet_fee": {"amount_cents": 50.0, "currency": "USD"}})
        assert "NOT_INT_CENTS" in codes(issues)

    def test_string_boolean_rejected(self):
        """The corpus stores "true"; 1.2 wants a JSON boolean."""
        assert "NOT_BOOL" in codes(ps.validate_facts({"pets_allowed": "true"}))


class TestFeeScope:

    @pytest.mark.parametrize("scope", ["per room", "per pet", "unknown", "PER_ROOM"])
    def test_legacy_spellings_rejected(self, scope):
        issues = ps.validate_facts(
            {"pet_fee": dict(money(5000), basis="per_night", scope=scope)})
        assert codes(issues) & {"BAD_ENUM", "SENTINEL_FOR_SILENCE"}

    @pytest.mark.parametrize("scope", ["per_room", "per_pet"])
    def test_canonical_accepted(self, scope):
        assert ps.validate_facts(
            {"pet_fee": dict(money(5000), basis="per_night", scope=scope)}) == ()

    def test_compound_basis_rejected(self):
        """"per room per night" is two facts; 1.2 wants them in two fields."""
        issues = ps.validate_facts(
            {"pet_fee": dict(money(5000), basis="per room per night")})
        assert "BAD_ENUM" in codes(issues)

    def test_allowance_needs_room_scope(self):
        """"Covers up to 2 pets" on a per-pet charge is a contradiction."""
        issues = ps.validate_facts({"pet_fee": dict(
            money(5000), basis="per_night", scope="per_pet", scope_pet_allowance=2)})
        assert "ALLOWANCE_WITHOUT_ROOM_SCOPE" in codes(issues)


class TestWeightOverload:
    """The defect that left eleven records with no recoverable comparison."""

    def test_combined_in_operator_slot_rejected(self):
        issues = ps.validate_facts({"weight_limit": dict(
            quantity(75, "lb"), operator="combined", scope="per_pet")})
        assert "SCOPE_IN_OPERATOR_SLOT" in codes(issues)

    def test_combined_in_the_combined_field_operator_also_rejected(self):
        """Dayton got the field right and still put a scope in the operator."""
        issues = ps.validate_facts({"combined_weight_limit": dict(
            quantity(80, "lb"), operator="combined")})
        assert "SCOPE_IN_OPERATOR_SLOT" in codes(issues)

    def test_combined_limit_may_not_carry_a_scope(self):
        """Its field name IS its scope; a scope key is the overload again."""
        issues = ps.validate_facts({"combined_weight_limit": dict(
            quantity(80, "lb"), operator="lte", scope="per_pet")})
        assert "REDUNDANT_SCOPE" in codes(issues)

    def test_weight_string_rejected(self):
        assert codes(ps.validate_facts({"weight_limit": "75 pounds"})) \
            & {"NOT_OBJECT", "NOT_QUANTITY"}

    def test_both_limits_coexist_cleanly(self):
        assert ps.validate_facts({
            "weight_limit": dict(quantity(50, "lb"), operator="lte", scope="per_pet"),
            "combined_weight_limit": dict(quantity(75, "lb"), operator="lte"),
        }) == ()

    def test_stated_none_cannot_coexist_with_a_limit(self):
        issues = ps.validate_facts({
            "weight_limit_stated_none": True,
            "weight_limit": dict(quantity(50, "lb"), operator="lte", scope="per_pet")})
        assert "CONTRADICTS_LIMIT" in codes(issues)

    def test_dimensions_are_not_weights(self):
        """36 inches long must never be storable as a weight."""
        assert ps.validate_facts({"dimension_constraints": [
            dict(quantity(36, "in"), axis="length", operator="lte")]}) == ()
        issues = ps.validate_facts({"dimension_constraints": [
            dict(quantity(36, "lb"), axis="length", operator="lte")]})
        assert "BAD_UNIT" in codes(issues)


class TestFeeCaps:

    def test_qualifier_stated_is_mandatory(self):
        issues = ps.validate_facts({"fee_cap": dict(money(10500), basis="per_stay")})
        assert "MISSING_REQUIRED" in codes(issues)

    def test_fully_qualified_cap_accepted(self):
        assert ps.validate_facts({"fee_cap": dict(
            money(10500), basis="per_stay", scope="per_pet",
            applies_to_pet_ordinal=2, trigger_max_nights=7,
            qualifier_stated=True)}) == ()

    def test_red_roof_shape_round_trips(self):
        """The case that loses four facts under the legacy shape.

        "Second pet $15/night, not to exceed 7 nights or $105 per pet per
        stay." The cap belongs to the SECOND pet, and hanging it at record
        level shows $105 against a first pet that stays free.
        """
        assert ps.validate_facts({
            "pet_count_limit": 2,
            "fee_pet_schedule": {"entries": [
                dict(money(0), pet_ordinal=1, basis="per_stay", additive=False),
                dict(money(1500), pet_ordinal=2, basis="per_night",
                     scope="per_pet", additive=True,
                     cap=dict(money(10500), basis="per_stay", scope="per_pet",
                              applies_to_pet_ordinal=2, trigger_max_nights=7,
                              qualifier_stated=True)),
            ]}}) == ()


class TestTiers:

    def test_role_is_mandatory(self):
        issues = ps.validate_facts({"fee_tiers": [dict(
            money(7500), condition_type="stay_length_range",
            boundary_unit="nights", condition_min=1, condition_max=4,
            basis_stated=False)]})
        assert "MISSING_REQUIRED" in codes(issues)

    def test_legacy_role_rejected(self):
        """Every corpus tier says ONE_TIME_CHARGE, which discriminates nothing."""
        issues = ps.validate_facts({"fee_tiers": [dict(
            money(7500), role="ONE_TIME_CHARGE", condition_type="stay_length_range",
            boundary_unit="nights", condition_min=1, condition_max=4,
            basis_stated=False)]})
        assert "BAD_ENUM" in codes(issues)

    def test_inverted_range_rejected(self):
        issues = ps.validate_facts({"fee_tiers": [dict(
            money(7500), role="REPLACEMENT_PRICE",
            condition_type="stay_length_range", boundary_unit="nights",
            condition_min=5, condition_max=2, basis_stated=True)]})
        assert "INVERTED_RANGE" in codes(issues)


class TestOtherCharges:

    def test_absent_refundability_is_unknown_not_inferred(self):
        """A stated contingent charge may be silent on refundability."""
        assert ps.validate_facts({"other_charges": [dict(
            money(7500), kind="cleaning_fee", conditional=True,
            trigger="A $75 cleaning fee may apply if the room needs extra cleaning.")]}) == ()

    def test_conditional_charge_requires_its_stated_trigger(self):
        issues = ps.validate_facts({"other_charges": [dict(
            money(7500), kind="cleaning_fee", conditional=True)]})
        assert "MISSING_REQUIRED" in codes(issues)

    def test_conditional_cleaning_charge_renders_its_exact_trigger(self):
        trigger = "A $75 cleaning fee may apply if the room needs extra cleaning."
        record = {"schema_version": "1.2", "facts": {"pets_allowed": True,
                  "other_charges": [dict(money(7500), kind="cleaning_fee",
                                           conditional=True, trigger=trigger)]}}
        shown = canonical_view.display_facts(record)
        assert shown["cleaning_fee_condition"] == trigger
        details = _verified_details(shown, record)[0]
        assert ("Conditional cleaning charge", trigger, "") in details
        assert not any(row[0] == "Cleaning fee" for row in details)

    def test_explicit_refundability_accepted(self):
        assert ps.validate_facts({"other_charges": [
            dict(money(7500), kind="non_refundable_fee", refundable=False)]}) == ()


class TestSpecies:

    def test_generic_pets_yields_no_species(self):
        """An empty map is the correct reading of "pets welcome"."""
        assert ps.validate_facts({"pets_allowed": True, "species": {}}) == ()

    def test_third_party_may_restrict(self):
        assert ps.validate_facts({
            "species": {"cats": "prohibited"},
            "species_source_grade": {"cats": "PT3_THIRD_PARTY"}}) == ()

    def test_third_party_may_not_permit(self):
        """An aggregator claiming acceptance would write a fact nobody stated."""
        issues = ps.validate_facts({
            "species": {"cats": "accepted"},
            "species_source_grade": {"cats": "PT3_THIRD_PARTY"}})
        assert "LOW_GRADE_ACCEPTANCE" in codes(issues)

    def test_first_party_may_permit(self):
        assert ps.validate_facts({
            "species": {"dogs": "accepted"},
            "species_source_grade": {"dogs": "PT1_FIRST_PARTY"}}) == ()


class TestServiceAnimals:

    def test_rejected_inside_facts(self):
        """A legal access category must not sit among commercial terms."""
        issues = ps.validate_record({
            "identity_key": "hampton inn dayton", "name": "Hampton Inn Dayton",
            "facts": {"service_animal_exception": "true"}})
        assert "MISPLACED_FIELD" in codes(issues)

    def test_accepted_in_its_own_block(self):
        issues = ps.validate_record({
            "identity_key": "hampton inn dayton", "name": "Hampton Inn Dayton",
            "facts": {"pets_allowed": True},
            "service_animal_statement": {"stated": True,
                                         "charges_stated": "no_charge"}})
        assert issues == ()


class TestWithholding:

    def base(self, **kw):
        record = {"identity_key": "hampton inn dayton", "name": "Hampton Inn Dayton",
                  "facts": {"pets_allowed": True},
                  "evidence": [{"evidence_ref": "ev-1"}]}
        record.update(kw)
        return record

    def test_source_silent_is_refused(self):
        """The rule that gives the structure its meaning."""
        issues = withholding.validate(self.base(withheld_fields={
            "pet_fee": {"reason_code": "SOURCE_SILENT", "reason": "no fee stated",
                        "evidence_refs": ["ev-1"]}}))
        assert "SILENCE_IS_NOT_WITHHOLDING" in codes(issues)

    def test_legacy_prose_entry_is_refused(self):
        """Cleveland's and Dayton's 66 entries have no reason code."""
        issues = withholding.validate(self.base(withheld_fields={
            "species_allowed": "the page names no species"}))
        assert "MISSING_REASON_CODE" in codes(issues)

    def test_evidence_refs_are_mandatory(self):
        issues = withholding.validate(self.base(withheld_fields={
            "pet_fee": {"reason_code": "SOURCE_CONTRADICTORY",
                        "reason": "two amounts", "evidence_refs": []}}))
        assert "MISSING_EVIDENCE_REFS" in codes(issues)

    def test_withheld_field_may_not_also_be_published(self):
        """Present in both, the value leaks into every consumer."""
        issues = withholding.validate(self.base(
            facts={"pet_fee": dict(money(5000))},
            withheld_fields={"pet_fee": {"reason_code": "SOURCE_CONTRADICTORY",
                                         "reason": "two amounts",
                                         "evidence_refs": ["ev-1"]}}))
        assert "WITHHELD_BUT_PRESENT" in codes(issues)

    def test_subfield_withholding_is_allowed(self):
        """Publish the amount, withhold the scope -- the commonest real shape."""
        issues = withholding.validate(self.base(
            facts={"pet_fee": dict(money(5000), basis="per_night")},
            withheld_fields={"pet_fee.scope": {
                "reason_code": "SOURCE_AMBIGUOUS",
                "reason": "the page does not say per pet or per room",
                "evidence_refs": ["ev-1"]}}))
        assert issues == ()

    def test_broken_chain_blocks_the_whole_record(self):
        blockers = withholding.blocks_publication(self.base(withheld_fields={
            "pet_fee": {"reason_code": "ARTIFACT_INSUFFICIENT",
                        "reason": "no page artifact", "evidence_refs": ["ev-1"]}}))
        assert len(blockers) == 1

    def test_render_state_distinguishes_all_three(self):
        record = self.base(
            facts={"pet_fee": dict(money(5000))},
            withheld_fields={"weight_limit": {"reason_code": "SOURCE_AMBIGUOUS",
                                              "reason": "unclear",
                                              "evidence_refs": ["ev-1"]}})
        assert withholding.render_state(record, "pet_fee") == "stated"
        assert withholding.render_state(record, "weight_limit") == "withheld"
        assert withholding.render_state(record, "pet_count_limit") == "not_stated"

    def test_withheld_copy_never_reads_as_silence(self):
        """"Not stated" and "withheld" are different claims about a hotel."""
        for reason, copy in withholding.PUBLIC_COPY.items():
            if copy:
                assert withholding.NOT_STATED_COPY not in copy, reason
        assert withholding.WITHHELD_CSS_CLASS != withholding.NOT_STATED_CSS_CLASS


class TestEvidence:

    def test_transcription_may_never_publish(self):
        """Hashing a transcription binds the typing, not the page."""
        assert not evidence.can("TRANSCRIPTION_ONLY", "publish_facts")
        assert evidence.can("TRANSCRIPTION_ONLY", "propose_facts")
        assert evidence.can("TRANSCRIPTION_ONLY", "propose_routing")
        assert not evidence.can("TRANSCRIPTION_ONLY", "confirm_identity")

    def test_only_publication_grade_publishes(self):
        for cls in enums.ARTIFACT_CLASSES:
            expected = cls == enums.PUBLICATION_GRADE_EVIDENCE
            assert evidence.can(cls, "publish_facts") is expected

    def test_identity_only_cannot_propose_routing(self):
        assert evidence.can("IDENTITY_ONLY", "confirm_identity")
        assert not evidence.can("IDENTITY_ONLY", "propose_routing")

    def test_unacceptable_can_do_nothing(self):
        for capability in evidence.CAPABILITY_MATRIX:
            assert not evidence.can("UNACCEPTABLE_FOR_PUBLICATION", capability)

    def test_publication_grade_requires_every_field(self):
        issues = evidence.validate_entry(
            {"artifact_class": "PUBLICATION_GRADE_EVIDENCE",
             "evidence_ref": "ev-1", "field": "pet_fee"}, 0)
        missing = {i.path.rsplit(".", 1)[-1] for i in issues
                   if i.code == "MISSING_REQUIRED"}
        assert {"quote", "source_url", "artifact_sha256", "artifact_kind"} <= missing

    def test_publication_grade_must_be_first_party(self):
        issues = evidence.validate_entry({
            "artifact_class": "PUBLICATION_GRADE_EVIDENCE", "evidence_ref": "ev-1",
            "field": "pet_fee", "quote": "q", "source_url": "u",
            "source_grade": "PT3_THIRD_PARTY", "artifact_sha256": "a",
            "artifact_kind": "rendered_html", "captured_at": "2026-08-10"}, 0)
        assert "NOT_FIRST_PARTY" in codes(issues)

    def test_capture_metadata_aliases_are_first_party_and_hash_stable(self):
        entry = {
            "artifact_class": "PUBLICATION_GRADE_EVIDENCE", "evidence_ref": "ev-1",
            "field": "pet_fee", "quote": "Pets Welcome", "source_url": "https://example.test",
            "source_grade": "OFFICIAL_PROPERTY", "artifact_sha256": "sha256:abc",
            "artifact_kind": "official_page_rendered_text", "captured_at": "2026-08-17",
            "capture_method": "official_page_retrieval",
        }
        before = dict(entry)
        assert evidence.validate_entry(entry, 0) == ()
        assert entry == before
        parsed = evidence.parse([entry])[0]
        assert parsed.source_grade == enums.GRADE_PT1_FIRST_PARTY
        assert parsed.artifact_kind == enums.ARTIFACT_RENDERED_HTML

    def test_record_with_only_a_transcription_cannot_publish(self):
        blockers = evidence.publication_blockers({
            "facts": {"pet_fee": dict(money(5000))},
            "evidence": [{"evidence_ref": "ev-1", "field": "pet_fee",
                          "artifact_class": "TRANSCRIPTION_ONLY"}]})
        assert any("transcription" in b for b in blockers)

    def test_published_fact_without_evidence_is_reported(self):
        missing = evidence.unevidenced_facts({
            "facts": {"pet_fee": dict(money(5000)), "pet_count_limit": 2},
            "evidence": [{"evidence_ref": "ev-1", "field": "pet_fee"}]})
        assert missing == ("pet_count_limit",)

    def test_declared_derivation_is_exempt(self):
        missing = evidence.unevidenced_facts({
            "facts": {"pet_fee": dict(money(5000)), "pet_count_limit": 2},
            "derived_fields": ["pet_count_limit"],
            "evidence": [{"evidence_ref": "ev-1", "field": "pet_fee"}]})
        assert missing == ()

    def test_a_fact_cited_under_its_legacy_evidence_name_is_covered(self):
        """Schema 1.2 renamed fact keys without renaming their evidence field.

        ``facts.species`` is authored from a ``species_allowed`` entry, so
        matching names literally accused 43 records across two markets of
        publishing an unevidenced fact whose citation was in the same record.
        """
        missing = evidence.unevidenced_facts({
            "facts": {"species": {"dogs": "accepted"}},
            "evidence": [{"evidence_ref": "ev-1", "field": "species_allowed"}]})
        assert missing == ()

    def test_an_alias_never_excuses_an_unrelated_fact(self):
        """The check still fires on what it exists to catch."""
        missing = evidence.unevidenced_facts({
            "facts": {"species": {"dogs": "accepted"}, "weight_limit": {}},
            "evidence": [{"evidence_ref": "ev-1", "field": "cats_allowed"}]})
        assert missing == ("weight_limit",)

    def test_coverage_names_always_includes_the_field_itself(self):
        """An alias is a SECOND acceptable name, never a replacement -- a market
        that authors a direct pointer must keep being credited for it."""
        for field, aliases in evidence.FACT_EVIDENCE_ALIASES.items():
            names = evidence.coverage_names(field)
            assert names[0] == field
            assert set(aliases) < set(names)
        assert evidence.coverage_names("pet_fee") == ("pet_fee",)

    def test_every_alias_target_is_a_distinct_name(self):
        """An alias pointing at the fact's own name would be a silent no-op."""
        for field, aliases in evidence.FACT_EVIDENCE_ALIASES.items():
            assert field not in aliases, field
            assert len(set(aliases)) == len(aliases), field


class TestContiguousQuote:
    """A stitched quote is a forgery."""

    PAGE = ("Pet Policy Pets Welcome. " + "filler " * 200
            + "Non-Refundable Pet Fee Per Night: $50.00")

    def test_contiguous_quote_accepted(self):
        assert evidence.quote_is_contiguous(
            "Non-Refundable Pet Fee Per Night: $50.00", self.PAGE)

    def test_stitched_halves_rejected(self):
        """Both halves are on the page; the sentence never was."""
        assert not evidence.quote_is_contiguous(
            "Pets Welcome. Non-Refundable Pet Fee Per Night: $50.00", self.PAGE)

    def test_whitespace_is_forgiving_but_words_are_not(self):
        assert evidence.quote_is_contiguous(
            "Non-Refundable   Pet Fee\nPer Night: $50.00", self.PAGE)
        assert not evidence.quote_is_contiguous(
            "Non-Refundable Pet Fee Per Stay: $50.00", self.PAGE)

    def test_empty_quote_rejected(self):
        assert not evidence.quote_is_contiguous("   ", self.PAGE)

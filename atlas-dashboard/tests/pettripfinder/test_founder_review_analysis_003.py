"""PTF-ST-LOUIS-FOUNDER-REVIEW-003 -- reviewing 122 candidates without approving any.

The load-bearing property is the one that is easiest to lose: this module
PROPOSES and never ATTESTS. Everything else here is about the two things a
review is for -- refusing to publish a record our own gates reject, and catching
the record that would mislead a guest if published exactly as it stands.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder import founder_review_analysis as FR


def candidate(**over):
    base = {
        "identity_key": "k", "canonical_name": "The Inn At Soulard", "brand": "CHOICE",
        "corridor": "c", "source_url": "https://www.choicehotels.com/mo/x/y/mo123",
        "proposed_facts": {"pets_allowed": True},
        "withheld_fields": {}, "flags": [],
        "membrane": {"verdict": "VALID", "rule": "", "detail": ""},
        "readiness": {"state": "POLICY_CONFIRMED"},
        "publication_grade": {"verdict": "PUBLICATION_GRADE_CONFIRMED",
                              "reasons": []},
        "recommendation": "RECOMMEND_AUTHORITY_PET_FRIENDLY",
        "semantic_approval": {"semantic_hash": "sha256:x", "projection": {
            "identity_check": {"name_on_page": "The Inn At Soulard",
                               "address_on_page": "1 Road",
                               "phone_on_page": "3145551212"}}},
    }
    base.update(over)
    return base


def census_row(**over):
    base = {"identity_key": "k", "canonical_name": "The Inn At Soulard",
            "address": "1 Road", "phone": "3145551212"}
    base.update(over)
    return base


def run(cand, row=None):
    detail = FR.examine(cand, row if row is not None else census_row())
    disposition, reasons, next_action = FR.dispose(cand, detail)
    return disposition, reasons, next_action, detail


class TestItNeverApproves:
    def test_a_review_row_carries_no_founder_attestation_field(self):
        packet = {"count": 1, "candidates": [candidate()], "market_id": "m"}
        out = FR.review_all(packet, {"hotels": [census_row()]},
                            reviewer="Claude (operator)")
        row = out["rows"][0]
        for forbidden in ("founder_decision", "founder_reviewer_id",
                          "founder_reviewed_at"):
            assert forbidden not in row
        assert row["reviewed_by"] == "Claude (operator)"
        assert "not an attestation" in row["review_is_not_an_approval"].lower()

    def test_the_reviewer_is_recorded_and_is_not_the_founder(self):
        out = FR.review_all({"count": 0, "candidates": []}, {"hotels": []},
                            reviewer="somebody")
        assert out["reviewed_by"] == "somebody"

    def test_every_candidate_gets_exactly_one_disposition(self):
        packet = {"count": 2, "candidates": [candidate(identity_key="a"),
                                             candidate(identity_key="b")]}
        out = FR.review_all(packet, {"hotels": [census_row(identity_key="a"),
                                                census_row(identity_key="b")]},
                            reviewer="r")
        assert out["each_reviewed_exactly_once"] is True
        assert all(r["proposed_disposition"] in FR.DISPOSITIONS
                   for r in out["rows"])
        assert sum(out["disposition_counts"].values()) == 2


class TestOurOwnGatesWin:
    def test_a_membrane_refusal_holds_however_good_the_facts_are(self):
        cand = candidate(membrane={"verdict": "REJECT_WRONG_PROPERTY",
                                   "rule": "M10", "detail": "another hotel"})
        disposition, _reasons, action, _d = run(cand)
        assert disposition == FR.HOLD
        assert "No re-fetch" in action

    def test_a_membrane_refusal_on_a_bare_name_names_the_offline_remedy(self):
        """The other half of the same rung: when the census name names no
        building, the membrane is refusing by design and the remedy is a name
        correction, not a person deciding whether two hotels are one."""
        cand = candidate(canonical_name="Hampton",
                         membrane={"verdict": "REJECT_WRONG_PROPERTY",
                                   "rule": "M10", "detail": "another hotel"})
        _d, _r, action, _detail = run(cand, census_row(canonical_name="Hampton"))
        assert "re-derive" in action

    def test_a_malformed_observation_names_the_contract_to_amend(self):
        cand = candidate(membrane={"verdict": "REJECT_MALFORMED_OBSERVATION",
                                   "rule": "", "detail": "unknown flag code"})
        disposition, _reasons, action, _d = run(cand)
        assert disposition == FR.HOLD
        assert "FLAG_CODES" in action

    def test_a_capture_that_is_not_publication_grade_is_held(self):
        cand = candidate(publication_grade={"verdict": "PUBLICATION_GRADE_REJECTED",
                                            "reasons": ["no hash"]})
        assert run(cand)[0] == FR.HOLD

    def test_a_non_property_specific_source_is_held(self):
        cand = candidate(source_url="https://www.choicehotels.com/mo/x/quality-inn-hotels")
        assert run(cand)[0] == FR.HOLD

    def test_an_unstated_allowance_is_held_and_names_one_policy_question(self):
        cand = candidate(proposed_facts={"pet_fee": 1500,
                                         "fee_currency": "USD"},
                         withheld_fields={"pets_allowed": "SOURCE_SILENT"})
        disposition, _reasons, action, _d = run(cand)
        assert disposition == FR.HOLD
        assert "policy decision" in action

    def test_a_no_pets_row_carrying_a_pet_fee_is_held_as_contradictory(self):
        cand = candidate(proposed_facts={"pets_allowed": False,
                                         "pet_fee": 2500})
        assert run(cand)[0] == FR.HOLD


class TestIdentity:
    def test_any_one_agreeing_signal_is_enough_to_proceed(self):
        # A page carries what it carries. WoodSpring prints no address and no
        # telephone and states the property in its title; demanding a fixed
        # pair held three rows whose identity was never in doubt.
        cand = candidate(semantic_approval={"semantic_hash": "", "projection": {
            "identity_check": {"name_on_page":
                               "Extended Stay Hotel in Arnold, MO | The Inn At Soulard"}}})
        disposition, _r, _a, detail = run(cand)
        assert detail["identity"]["signals_agreeing"] == 1
        assert disposition == FR.APPROVE_PET_FRIENDLY

    def test_no_agreeing_signal_at_all_is_blocking(self):
        cand = candidate(semantic_approval={"semantic_hash": "", "projection": {
            "identity_check": {"name_on_page": "Somewhere Else",
                               "address_on_page": "99 Other St",
                               "phone_on_page": "9999999999"}}})
        assert run(cand)[0] == FR.HOLD

    def test_html_entities_do_not_make_a_hotel_a_different_hotel(self):
        # Seven IHG rows were refused because a page said "&amp;".
        assert FR.names_agree("Holiday Inn Express & Suites Edwardsville",
                              "Holiday Inn Express &amp; Suites Edwardsville")

    def test_a_chain_suffix_does_not_make_a_hotel_a_different_hotel(self):
        assert FR.names_agree("Holiday Inn Express & Suites St Peters by IHG",
                              "Holiday Inn Express &amp; Suites St Peters")

    def test_a_title_that_contains_the_name_agrees(self):
        assert FR.names_agree(
            "WoodSpring Suites St Louis Arnold",
            "Extended Stay Hotel in Arnold, MO | WoodSpring Suites St Louis Arnold")

    def test_two_genuinely_different_hotels_do_not_agree(self):
        assert not FR.names_agree("Hampton Inn Collinsville",
                                  "Drury Inn Fenton")
        assert not FR.names_agree("", "Anything")


class TestServiceAnimalContamination:
    """A term inside the service-animal sentence caps SERVICE ANIMALS."""

    def test_pet_terms_glued_to_the_front_are_detected_and_removed(self):
        text = ("with a 40.00 USD, per night, Limit of one pet per room, and "
                "20 pounds max Service animals are permitted, without charge.")
        assert FR.service_animal_contamination(text)
        assert FR.service_animal_correction(text) == \
            "Service animals are permitted, without charge."

    def test_a_weight_glued_to_the_front_is_detected(self):
        text = "Max 50 Pounds Service animals are permitted, without charge."
        assert FR.service_animal_contamination(text)
        assert FR.service_animal_correction(text).startswith("Service animals")

    def test_a_sentence_that_legitimately_names_a_fee_is_not_flagged(self):
        # "service animals are exempt from the $40 fee" is a correct statement
        # ABOUT service animals and must survive untouched.
        text = "Service animals are exempt from the 40.00 USD per night fee."
        assert FR.service_animal_contamination(text) == ""

    def test_a_clean_sentence_is_not_flagged(self):
        assert FR.service_animal_contamination(
            "ADA defined service animals are welcome at this hotel.") == ""

    def test_an_empty_statement_is_not_flagged(self):
        assert FR.service_animal_contamination("") == ""

    def test_contamination_produces_a_change_not_an_approval(self):
        cand = candidate(proposed_facts={
            "pets_allowed": True,
            "service_animal_exception":
                "Max 50 Pounds Service animals are permitted, without charge."})
        disposition, _r, _a, detail = run(cand)
        assert disposition == FR.APPROVE_WITH_CHANGE
        change = detail["changes"][0]
        assert change["field"] == "service_animal_exception"
        assert change["to"] == "Service animals are permitted, without charge."


class TestBareBrandNames:
    def test_a_bare_chain_word_requires_a_name_correction(self):
        cand = candidate(canonical_name="Hampton",
                         semantic_approval={"semantic_hash": "", "projection": {
                             "identity_check": {
                                 "name_on_page": "Hampton Inn Collinsville",
                                 "address_on_page": "1 Road",
                                 "phone_on_page": "3145551212"}}})
        disposition, _r, _a, detail = run(cand, census_row(canonical_name="Hampton"))
        assert disposition == FR.APPROVE_WITH_CHANGE
        assert detail["changes"][0]["to"] == "Hampton Inn Collinsville"

    def test_a_full_property_name_needs_no_correction(self):
        disposition, _r, _a, detail = run(candidate())
        assert disposition == FR.APPROVE_PET_FRIENDLY
        assert detail["changes"] == []

    def test_a_correction_may_only_use_a_value_the_page_states(self):
        cand = candidate(canonical_name="Hampton",
                         semantic_approval={"semantic_hash": "", "projection": {
                             "identity_check": {"name_on_page": ""}}})
        # No replacement on the page -> blocked, never invented.
        assert run(cand, census_row(canonical_name="Hampton"))[0] == FR.HOLD


class TestPlainApprovals:
    def test_a_stated_refusal_proposes_verified_no_pets(self):
        cand = candidate(proposed_facts={"pets_allowed": False},
                         recommendation="RECOMMEND_AUTHORITY_VERIFIED_NO_PETS")
        assert run(cand)[0] == FR.APPROVE_VERIFIED_NO_PETS

    def test_a_stated_allowance_proposes_pet_friendly(self):
        assert run(candidate())[0] == FR.APPROVE_PET_FRIENDLY

    def test_a_service_animal_note_on_a_no_pets_row_is_not_a_contradiction(self):
        # "Only service animals are permitted" is a refusal PLUS an exception,
        # and it is the most useful thing such a row can say.
        cand = candidate(proposed_facts={
            "pets_allowed": False,
            "service_animal_exception": "Only service animals are permitted."})
        assert run(cand)[0] == FR.APPROVE_VERIFIED_NO_PETS

    def test_a_deposit_beside_a_fee_is_reported_but_not_blocking(self):
        cand = candidate(proposed_facts={
            "pets_allowed": True, "pet_fee": 1500, "fee_currency": "USD",
            "fee_basis": "per_night", "pet_deposit": 5000})
        disposition, _r, _a, detail = run(cand)
        assert disposition == FR.APPROVE_PET_FRIENDLY
        assert any(f["code"] == "DEPOSIT_AND_FEE" and f["severity"] == "INFO"
                   for f in detail["findings"])

    def test_a_withheld_basis_is_informational_and_a_missing_one_is_not(self):
        withheld = candidate(
            proposed_facts={"pets_allowed": True, "pet_fee": 1500,
                            "fee_currency": "USD"},
            withheld_fields={"fee_basis": "SOURCE_SILENT"})
        assert run(withheld)[0] == FR.APPROVE_PET_FRIENDLY
        silent = candidate(proposed_facts={"pets_allowed": True,
                                           "pet_fee": 1500,
                                           "fee_currency": "USD"})
        assert run(silent)[0] == FR.HOLD


class TestTheCommittedReview:
    """The artifact this work order actually produced."""

    @pytest.fixture(scope="class")
    @classmethod
    def analysis(cls):
        path = ("launch_packages/pettripfinder/"
                "st_louis_mo_founder_review_analysis_003.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_every_packet_candidate_was_reviewed_exactly_once(self, analysis):
        assert analysis["candidates_in_packet"] == 122
        assert analysis["reviewed"] == 122
        assert analysis["each_reviewed_exactly_once"] is True
        assert len({r["identity_key"] for r in analysis["rows"]}) == 122

    def test_the_dispositions_sum_to_the_population(self, analysis):
        assert sum(analysis["disposition_counts"].values()) == 122

    def test_no_row_carries_a_founder_attestation(self, analysis):
        for row in analysis["rows"]:
            assert "founder_decision" not in row
            assert "founder_reviewer_id" not in row

    def test_every_hold_states_a_reason_and_a_next_action(self, analysis):
        for row in analysis["rows"]:
            if row["proposed_disposition"] == FR.HOLD:
                assert row["reasons"], row["identity_key"]
                assert row["next_action"], row["identity_key"]

    def test_every_change_names_a_field_a_from_and_a_to(self, analysis):
        for row in analysis["rows"]:
            for change in row["required_changes"]:
                assert change["field"] and change["why"]
                assert change["from"] != change["to"]

    def test_no_membrane_refusal_was_approved(self, analysis):
        for row in analysis["rows"]:
            if row["membrane_verdict"] != "VALID":
                assert row["proposed_disposition"] == FR.HOLD

    def test_the_source_of_every_approved_row_is_property_specific(self, analysis):
        from scripts.pettripfinder.acquisition import market_routing as MR
        for row in analysis["rows"]:
            if row["proposed_disposition"].startswith("APPROVE"):
                assert MR.classify_url_shape(row["source_url"]) in \
                    MR.ROUTABLE_SHAPES, row["identity_key"]

    def test_no_approved_row_has_an_uncorroborated_identity(self, analysis):
        for row in analysis["rows"]:
            if row["proposed_disposition"].startswith("APPROVE"):
                assert row["identity_corroboration"]["signals_agreeing"] >= 1

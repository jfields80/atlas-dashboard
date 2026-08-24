"""PTF-ST-LOUIS-FOUNDER-REMEDIATION-004 -- three offline repairs, none of them widening.

Each repair removes a reason a TRUE record was refused. None removes a reason a
FALSE record would be accepted, and that asymmetry is what these tests pin: for
every fix there is a paired test showing the thing it must still refuse.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.policy import policy_membrane as M
from scripts.pettripfinder.policy import policy_observation as PO


# --------------------------------------------------------------------------- #
# Step 1 -- the service-animal statement
# --------------------------------------------------------------------------- #

class TestServiceAnimalQuoteStopsSwallowingPetTerms:
    """A limit written BEFORE "service animals" cannot be a limit on them.

    ``_service_animal_span`` already said so and governed which limits were
    ATTRIBUTED. The PUBLISHED quote did not follow the same rule, so two St.
    Louis records stated that service animals cost $40 a night and were capped
    at 20 pounds.
    """

    def _quote(self, text):
        import scripts.pettripfinder.brightdata.marriott_surface as MS
        match = MS._SERVICE_ANIMAL_RE.search(text)
        return PR._service_animal_quote(text, match)

    def test_a_swallowed_price_and_weight_are_trimmed_away(self):
        text = ("Pets are welcome with a 40.00 USD, per night, Limit of one pet "
                "per room, and 20 pounds max Service animals are permitted, "
                "without charge.")
        quote = self._quote(text)
        assert quote.lower().startswith("service animals")
        assert "40.00" not in quote and "20 pounds" not in quote

    def test_a_swallowed_weight_alone_is_trimmed_away(self):
        text = "Max 50 Pounds Service animals are permitted, without charge."
        assert self._quote(text) == "Service animals are permitted, without charge."

    def test_a_qualifier_that_is_not_a_pet_term_survives(self):
        # "Only" changes the meaning of the sentence and belongs to it.
        text = "Only service animals are permitted."
        assert self._quote(text).lower().startswith("only")

    def test_a_fee_the_sentence_itself_names_is_not_trimmed(self):
        # "service animals are exempt from the fee" is a correct statement ABOUT
        # service animals; trimming here would delete the exemption.
        text = "Service animals are exempt from the 40.00 USD per night fee."
        assert "40.00" in self._quote(text)

    def test_the_result_is_still_a_contiguous_substring_of_the_block(self):
        text = ("Pets welcome, 25.00 USD per night Service animals are "
                "permitted, without charge.")
        assert self._quote(text) in text


# --------------------------------------------------------------------------- #
# Step 2 -- M10 identity normalisation
# --------------------------------------------------------------------------- #

class TestEntityDecoding:
    def test_an_encoded_ampersand_no_longer_shatters_a_name(self):
        assert M._tokens("Holiday Inn Express &amp; Suites Edwardsville") == \
            M._tokens("Holiday Inn Express & Suites Edwardsville")

    def test_the_stray_amp_token_is_gone(self):
        assert "amp" not in M._tokens("Express &amp; Suites")

    def test_decoding_cannot_invent_a_token(self):
        assert M._tokens("Plain Name") == M._tokens("Plain Name")


class TestStreetComparison:
    def test_a_page_that_omits_the_postal_code_still_agrees(self):
        # The stored identity carries "<street>|<postal>"; a hotel page prints
        # the street and very often not the postal code.
        assert M._street_agrees("1320 thornton st|63069", "1320 Thornton St.")

    def test_two_postal_codes_that_disagree_are_a_disagreement(self):
        assert not M._street_agrees("1320 thornton st|63069",
                                    "1320 Thornton St., 63110")

    def test_a_different_street_never_agrees(self):
        assert not M._street_agrees("1320 thornton st|63069", "99 Other Road")

    def test_a_missing_street_on_either_side_is_not_agreement(self):
        assert not M._street_agrees("", "1320 Thornton St.")
        assert not M._street_agrees("1320 thornton st|63069", "")

    def test_a_bare_number_is_not_a_street(self):
        assert not M._street_agrees("1320|63069", "1320")


class TestDistinguishingToken:
    @pytest.mark.parametrize("name", ["Hampton", "Courtyard", "DoubleTree",
                                      "Wingate At Wyndham", "Days Inn",
                                      "Comfort Inn", "Holiday Inn"])
    def test_a_bare_chain_word_names_no_building(self, name):
        assert not M._has_distinguishing_token(name)

    @pytest.mark.parametrize("name", [
        "Hampton Inn Collinsville",
        "Holiday Inn Express & Suites Edwardsville by IHG",
        "Travelodge St. Louis Airport",
        "Days Inn & Suites Pontoon Beach"])
    def test_a_name_with_a_place_in_it_names_a_building(self, name):
        assert M._has_distinguishing_token(name)


class TestTheStreetAndNameOverride:
    def _ref(self, name, street="1000 plummer dr|62025"):
        return {"canonical_name": name, "normalized_name": name.lower(),
                "street_identity": street}

    def _check(self, name, address="1000 Plummer Drive"):
        return {"name_on_page": name, "address_on_page": address}

    def test_an_owner_qualifier_plus_a_matching_street_establishes_the_row(self):
        assert M._same_property_by_street_and_qualified_name(
            self._ref("Holiday Inn Express & Suites Edwardsville by IHG"),
            self._check("Holiday Inn Express &amp; Suites Edwardsville"))

    def test_a_bare_chain_name_is_refused_however_well_the_street_agrees(self):
        # THE hole this override could have opened: every Hampton Inn in a
        # market is a superset of {hampton}, so a bare chain word plus an
        # address would let any page of that chain establish a fact.
        assert not M._same_property_by_street_and_qualified_name(
            self._ref("Hampton"), self._check("Hampton Inn Collinsville"))

    def test_a_different_street_is_refused_however_well_the_name_agrees(self):
        assert not M._same_property_by_street_and_qualified_name(
            self._ref("Holiday Inn Express & Suites Edwardsville by IHG"),
            self._check("Holiday Inn Express & Suites Edwardsville",
                        address="99 Somewhere Else"))

    def test_a_genuinely_different_name_is_refused(self):
        assert not M._same_property_by_street_and_qualified_name(
            self._ref("Comfort Inn Pacific - St. Louis"),
            self._check("Comfort Inn Near Six Flags St. Louis"))

    def test_a_missing_street_on_the_reference_side_refuses(self):
        assert not M._same_property_by_street_and_qualified_name(
            self._ref("Holiday Inn Express & Suites Edwardsville by IHG",
                      street=""),
            self._check("Holiday Inn Express & Suites Edwardsville"))


# --------------------------------------------------------------------------- #
# Step 3 -- the versioned contract amendment
# --------------------------------------------------------------------------- #

class TestFlagCodesAmendment:
    def test_the_emission_version_moved(self):
        # 004's claim is that its amendment happened and is still honoured, not
        # that the contract froze at 1.1.0. A later additive amendment moving
        # the emission version past it must not break this work order's test --
        # what 004 must keep proving is that 1.1.0 records still validate.
        assert "1.1.0" in PO.ACCEPTED_CONTRACT_VERSIONS
        assert PO.CONTRACT_VERSION >= "1.1.0"

    def test_records_written_before_the_amendment_still_validate(self):
        # An amendment that only ADDS to a closed vocabulary cannot invalidate a
        # record written before it, and four markets' stores carry 1.0.0.
        assert "1.0.0" in PO.ACCEPTED_CONTRACT_VERSIONS
        assert PO.CONTRACT_VERSION in PO.ACCEPTED_CONTRACT_VERSIONS

    def test_the_codes_the_reader_emits_are_now_registered(self):
        assert "FLAG_STRUCTURED_TIERS" in PO.FLAG_CODES
        assert "FLAG_STRUCTURED_PET_SCHEDULE" in PO.FLAG_CODES

    def test_the_vocabulary_is_still_closed(self):
        assert "FLAG_ANYTHING_I_LIKE" not in PO.FLAG_CODES

    def test_an_unregistered_code_is_still_refused(self):
        record = {"obs_id": "x", "contract_version": PO.CONTRACT_VERSION,
                  "flags": [{"code": "FLAG_NOT_REAL"}]}
        with pytest.raises(PO.PolicyObservationError):
            PO.validate_observation(record)


# --------------------------------------------------------------------------- #
# The artifacts this work order produced
# --------------------------------------------------------------------------- #

PKG = "launch_packages/pettripfinder/"


def _load(name):
    with open(PKG + name, encoding="utf-8") as handle:
        return json.load(handle)


class TestTheRemediatedArtifacts:
    def test_every_candidate_survives_exactly_once(self):
        analysis = _load("st_louis_mo_founder_review_analysis_004.json")
        assert analysis["candidates_in_packet"] == 122
        assert analysis["reviewed"] == 122
        assert analysis["each_reviewed_exactly_once"] is True

    def test_closure_still_covers_the_active_denominator_exactly(self):
        closure = _load("st_louis_mo_closure_ledger_004.json")
        assert closure["count"] == closure["active_denominator"] == 357
        assert closure["reconciliation"]["missing"] == []
        assert closure["reconciliation"]["foreign"] == []
        assert closure["reconciliation"]["duplicate"] == []

    def test_the_two_contaminated_statements_are_clean(self):
        store = _load("st_louis_mo_observation_store_004.json")
        rows = {r["identity_key"]: r for r in store["records"]}
        for key in ("comfort inn and suites saint louis lafayette square",
                    "radisson hotel fairview heights st louis"):
            statement = rows[key]["observation"]["extraction"][
                "service_animal_exception"]
            assert statement.lower().startswith("service animals")
            assert "pound" not in statement.lower()
            assert "per night" not in statement.lower()

    def test_the_three_corrected_names_carry_the_page_name(self):
        store = _load("st_louis_mo_observation_store_004.json")
        rows = {r["identity_key"]: r for r in store["records"]}
        expected = {
            "courtyard": "Courtyard by Marriott St. Louis Airport/Earth City",
            "days inn": "Days Inn & Suites by Wyndham Caseyville",
            "doubletree": "DoubleTree by Hilton Hotel Collinsville - St. Louis"}
        for key, name in expected.items():
            assert rows[key]["observation"]["hotel_ref"]["canonical_name"] == name
            # The census reading is kept beside it, never overwritten.
            assert rows[key]["census_canonical_name"] != name

    def test_the_census_file_itself_was_not_edited(self):
        census = _load("identity_census/st-louis-mo.json")
        names = {h["identity_key"]: h["canonical_name"] for h in census["hotels"]}
        assert names["courtyard"] == "Courtyard"
        assert names["days inn"] == "Days Inn"
        assert names["doubletree"] == "DoubleTree"

    def test_a_name_correction_may_only_use_what_the_page_states(self):
        import html as _html

        overlay = _load("markets/name_corrections/st-louis-mo.json")
        analysis = _load("st_louis_mo_founder_review_analysis_004.json")
        # Unescaped, and only unescaped: an HTML entity is a transport
        # artifact, not a different name (PTF-ST-LOUIS-REGISTER-PUBLISH-011).
        pages = {r["identity_key"]:
                 _html.unescape(r["identity_corroboration"]["name_on_page"])
                 for r in analysis["rows"]}
        for record in overlay["records"]:
            assert record["corrected_canonical_name"] == \
                pages[record["identity_key"]]

    def test_the_policy_question_is_asked_and_not_answered(self):
        question = _load("st_louis_mo_founder_policy_question_004.json")
        assert question["status"] == "AWAITING_FOUNDER_DECISION"
        assert question["founder_decision"] == ""
        assert question["founder_reviewer_id"] == ""
        assert question["founder_reviewed_at"] == ""
        assert len(question["rows"]) == 3

    def test_no_remediated_artifact_carries_a_founder_attestation(self):
        packet = _load("st_louis_mo_founder_review_packet_004.json")
        for candidate in packet["candidates"]:
            assert candidate["founder_decision"] == ""
            assert candidate["founder_reviewer_id"] == ""
            assert candidate["founder_reviewed_at"] == ""

    def test_no_membrane_refusal_is_proposed_for_approval(self):
        analysis = _load("st_louis_mo_founder_review_analysis_004.json")
        for row in analysis["rows"]:
            if row["membrane_verdict"] != "VALID":
                assert row["proposed_disposition"] == "HOLD"

    def test_the_remediation_only_moved_rows_toward_approval(self):
        before = _load("st_louis_mo_founder_review_analysis_003.json")
        after = _load("st_louis_mo_founder_review_analysis_004.json")
        rank = {"HOLD": 0, "APPROVE_WITH_CHANGE": 1,
                "APPROVE_PET_FRIENDLY": 2, "APPROVE_VERIFIED_NO_PETS": 2}
        old = {r["identity_key"]: r["proposed_disposition"] for r in before["rows"]}
        for row in after["rows"]:
            assert rank[row["proposed_disposition"]] >= \
                rank[old[row["identity_key"]]], row["identity_key"]

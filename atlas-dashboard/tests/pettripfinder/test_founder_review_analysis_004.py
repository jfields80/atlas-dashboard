"""PTF-LOUISVILLE-FOUNDER-REVIEW-004 -- what a review misses when it only reads
the record.

Every check in 003 compares a record against itself: its facts against its own
quotes, its identity against its own census row. A record cannot report the fact
it failed to read, so a reader gap is invisible from the inside -- and it is the
failure a guest actually notices, because the profile says "Not stated" where the
hotel's own page states a weight limit, a pet count, a deposit, or a price.

Louisville's 63 candidates carried five such rows, one implausible value its
source really does state, one sentence published under a service-animal heading
that was about damage charges, and three names that name no building and that a
hand-maintained list of chain words did not contain.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder import founder_review_analysis as FR
from scripts.pettripfinder.brightdata import marriott_surface as MS


def candidate(**over):
    base = {
        "identity_key": "k", "canonical_name": "The Inn At Soulard",
        "brand": "CHOICE", "corridor": "c",
        "source_url": "https://www.choicehotels.com/mo/x/y/mo123",
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


def record_with(tmp_path, block_text):
    path = tmp_path / "policy-block.txt"
    path.write_text(block_text, encoding="utf-8")
    return {"identity_key": "k",
            "observation": {"capture_artifacts": {"policy-block.txt": str(path)}}}


def run(cand, record=None, row=None, names=()):
    detail = FR.examine(cand, row if row is not None else census_row(),
                        census_names=names, record=record)
    disposition, reasons, action = FR.dispose(cand, detail)
    return disposition, detail


def changed_fields(detail):
    return {c["field"] for c in detail["changes"]}


# --------------------------------------------------------------------------- #
# A name that names no building
# --------------------------------------------------------------------------- #

class TestNamesNoBuilding:
    @pytest.mark.parametrize("name", ["Hampton", "Tru", "Quality Suites",
                                      "Holiday Inn", "The Inn"])
    def test_a_name_with_nothing_but_chain_and_lodging_words_names_no_building(
            self, name):
        assert FR.names_no_building(name, []) is True

    def test_a_name_the_market_extends_twice_over_names_no_building(self):
        """The rule a fixed list cannot have: this market's own census says
        "TownePlace Suites" is three buildings."""
        census = ["TownePlace Suites by Marriott Louisville Airport",
                  "TownePlace Suites by Marriott Louisville North",
                  "TownePlace Suites Louisville North"]
        assert FR.names_no_building("TownePlace Suites", census) is True

    def test_one_sibling_extending_a_full_name_is_not_enough(self):
        """"La Quinta Inn & Suites Louisville" is a real hotel whose name is a
        prefix of one neighbour. Refusing it would correct a name that is right."""
        census = ["La Quinta Inn & Suites Louisville East"]
        assert FR.names_no_building("La Quinta Inn & Suites Louisville",
                                    census) is False

    def test_a_name_that_names_a_place_is_left_alone(self):
        assert FR.names_no_building("Hampton Inn Louisville Northeast",
                                    []) is False


class TestPageTitleIsNotAName:
    def test_a_title_is_reduced_to_the_property_it_names(self):
        assert FR.page_property_name(
            "Louisville Hotels | Holiday Inn Louisville Downtown") == \
            "Holiday Inn Louisville Downtown"

    def test_a_plain_name_passes_through_unchanged(self):
        assert FR.page_property_name("Tru By Hilton Louisville East") == \
            "Tru By Hilton Louisville East"

    def test_a_title_that_is_nothing_but_furniture_offers_no_name(self):
        assert FR.page_property_name("Louisville Hotels | Hotels") == ""

    def test_the_correction_uses_the_property_half_of_the_title(self):
        cand = candidate(canonical_name="Holiday Inn",
                         semantic_approval={"semantic_hash": "s", "projection": {
                             "identity_check": {
                                 "name_on_page":
                                     "Louisville Hotels | Holiday Inn Louisville Downtown",
                                 "address_on_page": "1 Road",
                                 "phone_on_page": "3145551212"}}})
        _disposition, detail = run(cand, row=census_row(canonical_name="Holiday Inn"))
        change = [c for c in detail["changes"] if c["field"] == "canonical_name"][0]
        assert change["to"] == "Holiday Inn Louisville Downtown"
        assert change["correction_site"] == "evidence-cited overlay"


# --------------------------------------------------------------------------- #
# The source says more than the record
# --------------------------------------------------------------------------- #

class TestBlockEvidence:
    def test_a_stated_weight_the_record_dropped_becomes_a_correction(self, tmp_path):
        record = record_with(tmp_path, "Pet fee per night: 150 USD "
                                       "Pet weight limit: 80 2 pets allowed")
        _disposition, detail = run(candidate(), record)
        assert "weight_limit" in changed_fields(detail)

    def test_a_stated_count_the_record_dropped_becomes_a_correction(self, tmp_path):
        record = record_with(tmp_path, "One pet is allowed per room, with a "
                                       "maximum weight of 25.0 lbs.")
        cand = candidate(proposed_facts={"pets_allowed": True,
                                         "weight_limit": {"value": 25.0,
                                                          "unit": "lb"}})
        _disposition, detail = run(cand, record)
        assert "pet_count_limit" in changed_fields(detail)

    def test_a_correction_quotes_the_source_and_never_invents_a_value(self, tmp_path):
        record = record_with(tmp_path, "Weight limit 50 lbs, limit of two dogs.")
        _disposition, detail = run(candidate(), record)
        change = [c for c in detail["changes"] if c["field"] == "weight_limit"][0]
        assert change["to"].startswith("as stated:")
        assert change["correction_site"] == "parser logic"

    def test_a_deposit_with_an_amount_is_a_correction(self, tmp_path):
        record = record_with(tmp_path, "Pet fee per night: 40 USD "
                                       "Pet damage deposit: 40 USD")
        cand = candidate(proposed_facts={"pets_allowed": True, "pet_fee": 4000,
                                         "fee_currency": "USD",
                                         "fee_basis": "per_night"})
        _disposition, detail = run(cand, record)
        assert "pet_deposit" in changed_fields(detail)

    def test_a_deposit_with_no_amount_is_reported_and_not_corrected(self, tmp_path):
        """Hilton's amenity table answers "Deposit" with "Yes". Publishing a
        deposit with no amount is how a $75 non-refundable fee once became a
        refundable $75 deposit."""
        record = record_with(tmp_path, "Pets allowed Yes Deposit Yes. "
                                       "$75.00 Non-refundable Fee")
        cand = candidate(proposed_facts={"pets_allowed": True, "pet_fee": 7500,
                                         "fee_currency": "USD",
                                         "fee_basis": "per_stay"})
        _disposition, detail = run(cand, record)
        assert "pet_deposit" not in changed_fields(detail)
        assert "DEPOSIT_STATED_WITHOUT_AN_AMOUNT" in {f["code"]
                                                      for f in detail["findings"]}

    def test_source_silent_is_refused_when_the_block_prices_a_pet(self, tmp_path):
        record = record_with(tmp_path, "Our Pet Policy: 1 to 6 nights: 75 USD")
        cand = candidate(withheld_fields={"pet_fee": "SOURCE_SILENT"})
        _disposition, detail = run(cand, record)
        codes = {f["code"] for f in detail["findings"]}
        assert "WITHHELD_REASON_CONTRADICTED_BY_BLOCK" in codes
        assert "pet_fee" in changed_fields(detail)

    def test_source_silent_stands_when_the_money_is_for_parking(self, tmp_path):
        record = record_with(tmp_path, "Up to 2 pets are allowed per room. The "
                                       "daily valet fee is $50.00 per day.")
        cand = candidate(withheld_fields={"pet_fee": "SOURCE_SILENT"})
        _disposition, detail = run(cand, record)
        assert "WITHHELD_REASON_CONTRADICTED_BY_BLOCK" not in {
            f["code"] for f in detail["findings"]}

    def test_one_page_two_bases_withholds_the_basis(self, tmp_path):
        record = record_with(tmp_path, "Subject to a 75 USD pet fee per stay. "
                                       "Pet fee per night: 75 USD")
        cand = candidate(proposed_facts={"pets_allowed": True, "pet_fee": 7500,
                                         "fee_currency": "USD",
                                         "fee_basis": "per_night"})
        _disposition, detail = run(cand, record)
        change = [c for c in detail["changes"] if c["field"] == "fee_basis"][0]
        assert change["to"] is None
        assert "FEE_BASIS_STATED_BOTH_WAYS" in {f["code"] for f in detail["findings"]}

    def test_a_nightly_fee_with_a_per_stay_cap_is_not_a_contradiction(self, tmp_path):
        record = record_with(tmp_path, "Non-refundable 25 USD nightly for up to "
                                       "2 pets. Max 75 USD per stay.")
        cand = candidate(proposed_facts={
            "pets_allowed": True, "pet_fee": 2500, "fee_currency": "USD",
            "fee_basis": "per_night",
            "fee_cap": {"amount_minor": 7500, "currency": "USD",
                        "basis": "per_stay"}})
        _disposition, detail = run(cand, record)
        assert "FEE_BASIS_STATED_BOTH_WAYS" not in {f["code"]
                                                    for f in detail["findings"]}

    def test_a_weight_no_pet_can_have_is_withheld_not_printed(self, tmp_path):
        record = record_with(tmp_path, "Each pet may weigh up to 900.0 lbs.")
        cand = candidate(proposed_facts={"pets_allowed": True,
                                         "weight_limit": {"value": 900.0,
                                                          "unit": "lb"}})
        _disposition, detail = run(cand, record)
        change = [c for c in detail["changes"] if c["field"] == "weight_limit"][0]
        assert change["from"] == {"value": 900.0, "unit": "lb"}
        assert change["to"] is None

    def test_an_allowance_stated_in_words_is_not_an_unstated_allowance(self, tmp_path):
        """Days Inn Sellersburg: "A maximum of 2 dogs up to 15 lbs each are
        allowed ... Sorry no other pets are allowed." The second sentence
        restricts the species; it does not withdraw the first."""
        record = record_with(tmp_path,
                             "A maximum of 2 dogs up to 15 lbs each are allowed "
                             "for a non-refundable charge of 20.00 USD per pet "
                             "per night. Sorry no other pets are allowed.")
        cand = candidate(proposed_facts={},
                         withheld_fields={"pets_allowed": "SOURCE_CONTRADICTORY"})
        disposition, detail = run(cand, record)
        assert "pets_allowed" in changed_fields(detail)
        assert disposition == FR.APPROVE_WITH_CHANGE

    def test_a_review_without_the_store_still_runs_and_says_so(self):
        _disposition, detail = run(candidate(), None)
        assert detail["changes"] == [] or "weight_limit" not in changed_fields(detail)


# --------------------------------------------------------------------------- #
# A service-animal statement has to be about service animals
# --------------------------------------------------------------------------- #

class TestServiceAnimalStatement:
    @pytest.mark.parametrize("quote", [
        "ADA defined service animals are welcome at this hotel.",
        "Only service animals are permitted, free of charge.",
        "-service animals only",
        "We charge 50.00 per pet, per night, except ADA Service Animals.",
        "Non refundable pet fee 75 USD, not applicable to service animals.",
    ])
    def test_a_statement_about_access_is_kept(self, quote):
        assert MS.states_service_animal_access(quote) is True

    @pytest.mark.parametrize("quote", [
        # Louisville's Comfort Suites East, verbatim.
        "Incidental charges may include, but are not limited to, excessive trash "
        "left in the room, damage to the room or hotel property, missing items, "
        "smoking or vaping in the room, or additional cleaning required due to "
        "the actions of a guest, service animal.",
        "Pet & Service Animal Policy",
        "Violating the hotel's Service Animal and/or Pet Policy",
    ])
    def test_a_sentence_that_merely_contains_the_words_is_refused(self, quote):
        assert MS.states_service_animal_access(quote) is False

    def test_an_off_topic_statement_becomes_a_removal(self):
        cand = candidate(proposed_facts={
            "pets_allowed": False,
            "service_animal_exception":
                "Incidental charges may include damage to the room or hotel "
                "property, or additional cleaning required due to the actions "
                "of a guest, service animal."})
        disposition, detail = run(cand)
        change = [c for c in detail["changes"]
                  if c["field"] == "service_animal_exception"][0]
        assert change["to"] is None
        assert disposition == FR.APPROVE_WITH_CHANGE


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #

class TestProvenance:
    def test_the_review_is_stamped_with_the_work_order_that_ran_it(self):
        packet = {"market_id": "louisville-ky", "count": 0, "candidates": []}
        document = FR.review_all(packet, {"hotels": []}, reviewer="me",
                                 work_order="PTF-LOUISVILLE-FOUNDER-REVIEW-004")
        assert document["work_order"] == "PTF-LOUISVILLE-FOUNDER-REVIEW-004"

    def test_a_review_that_read_no_blocks_says_so(self):
        packet = {"market_id": "m", "count": 0, "candidates": []}
        document = FR.review_all(packet, {"hotels": []}, reviewer="me")
        assert document["block_evidence_read"] is False

    def test_it_still_writes_no_attestation(self):
        packet = {"market_id": "m", "count": 1, "candidates": [candidate()]}
        document = FR.review_all(packet, {"hotels": [census_row()]},
                                 reviewer="me")
        row = document["rows"][0]
        for field in ("founder_decision", "founder_reviewer_id",
                      "founder_reviewed_at"):
            assert field not in row

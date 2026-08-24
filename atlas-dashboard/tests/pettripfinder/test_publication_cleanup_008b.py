"""PTF-ST-LOUIS-PUBLICATION-CLEANUP-008B -- retiring a signature without erasing it.

A signature is a dated act by a named person. Two of them turned out to cover a
building that another row already covered, and the founder retired them. The
whole difficulty is that "retire" must not mean "delete" and must not mean
"edit": the original attestation has to remain readable exactly as written, or
the record loses the only evidence that the founder ever approved it.

So the shape is: the earlier ledgers are untouched, a LATER ledger records the
supersession, and the CURRENT authority is (union of signed) MINUS (withdrawn).
"""

from __future__ import annotations

import json
import re

import pytest

from scripts.pettripfinder import market_proposed_authority_cli as AUTH
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import founder_approval as FA

PKG = "launch_packages/pettripfinder/"


def _load(name):
    with open(PKG + name, encoding="utf-8") as handle:
        return json.load(handle)


def ledger(work_order, *keys, authority=None):
    return {"market_id": "m", "work_order": work_order, "signed": [
        {"identity_key": k, "canonical_name": k, "corridor": "c",
         "founder_decision": FA.CANONICAL_APPROVED,
         "founder_reviewer_id": "f", "founder_reviewed_at": "d",
         "proposes_authority": authority or enums.PUBLISHED_PET_FRIENDLY,
         "bound_semantic_hash": "", "bound_snapshot_hash": ""} for k in keys]}


def store(*keys):
    return {"records": [{"identity_key": k, "observation": {
        "snapshot_hash": "", "evidence": [{"quote": "q"}]}} for k in keys]}


def withdrawal(*retired, surviving="survivor", work_order="WO-W"):
    return {"work_order": work_order, "withdrawals": [
        {"retired_identity_key": k, "surviving_identity_key": surviving,
         "originally_signed_by_work_order": "WO-1",
         "original_ledger": "ledger-1.json",
         "founder_ruling": "keep the full identity"} for k in retired]}


class TestSupersessionMechanics:
    def test_a_withdrawn_row_leaves_the_current_authority(self):
        built = AUTH.build([ledger("WO-1", "a", "b")], store("a", "b"),
                           {"hotels": []}, withdrawals=withdrawal("a"))
        assert built["authority_total"] == 1
        assert built["superseded_count"] == 1
        names = {r["normalized_name"] for r in built["pet_friendly"]}
        assert names == {"b"}

    def test_the_superseded_row_is_reported_not_silently_dropped(self):
        built = AUTH.build([ledger("WO-1", "a", "b")], store("a", "b"),
                           {"hotels": []}, withdrawals=withdrawal("a"))
        row = built["superseded_rows"][0]
        assert row["identity_key"] == "a"
        assert row["now"] == enums.SUPERSEDED
        assert row["was"] == enums.PUBLISHED_PET_FRIENDLY
        assert row["surviving_identity_key"] == "survivor"
        assert row["attestation_preserved_in"] == "ledger-1.json"
        assert row["superseded_by_work_order"] == "WO-W"

    def test_supersession_is_the_existing_vocabulary_not_a_new_one(self):
        assert enums.SUPERSEDED in enums.APPROVAL_DECISIONS
        assert enums.SUPERSEDED in FA.WRITABLE
        assert not FA.is_publishable(enums.SUPERSEDED)
        assert enums.SUPERSEDED not in enums.PUBLISHING_DECISIONS

    def test_no_withdrawals_leaves_the_authority_untouched(self):
        plain = AUTH.build([ledger("WO-1", "a", "b")], store("a", "b"),
                           {"hotels": []})
        assert plain["authority_total"] == 2
        assert plain["superseded_count"] == 0

    def test_a_withdrawal_naming_an_unsigned_row_changes_nothing(self):
        built = AUTH.build([ledger("WO-1", "a")], store("a"), {"hotels": []},
                           withdrawals=withdrawal("never-signed"))
        assert built["authority_total"] == 1
        assert built["superseded_count"] == 0

    def test_withdrawing_a_no_pets_row_reduces_the_exclusion_side(self):
        built = AUTH.build(
            [ledger("WO-1", "a", "b", authority=enums.VERIFIED_NO_PETS)],
            store("a", "b"), {"hotels": []}, withdrawals=withdrawal("a"))
        assert built["verified_no_pets_count"] == 1
        assert built["pet_friendly_count"] == 0


class TestTheCommittedCleanup:
    def test_the_arithmetic_is_121_minus_2(self):
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        assert auth["superseded_count"] == 2
        assert auth["authority_total"] == 119
        assert auth["pet_friendly_count"] == 82
        assert auth["verified_no_pets_count"] == 37
        assert auth["pet_friendly_count"] + auth["verified_no_pets_count"] == 119

    def test_both_original_attestations_are_still_on_file_unedited(self):
        # This is the property the whole work order turns on.
        five = _load("st_louis_mo_founder_decisions_005.json")
        seven = _load("st_louis_mo_founder_decisions_007.json")
        assert five["signed_count"] == 114
        assert seven["signed_count"] == 7
        by_five = {r["identity_key"]: r for r in five["signed"]}
        by_seven = {r["identity_key"]: r for r in seven["signed"]}
        assert by_five["doubletree"]["founder_decision"] == FA.CANONICAL_APPROVED
        assert by_five["doubletree"]["founder_reviewer_id"] == "jfields80"
        assert by_seven["wingate at wyndham"]["founder_decision"] == \
            FA.CANONICAL_APPROVED
        assert by_seven["wingate at wyndham"]["founder_reviewer_id"] == "jfields80"

    def test_the_withdrawal_ledger_names_who_decided_and_who_typed(self):
        w = _load("st_louis_mo_founder_withdrawals_008b.json")
        assert w["decided_by"] == "jfields80"
        assert "transcription only" in w["recorded_by"]
        assert w["superseding_decision"] == enums.SUPERSEDED

    def test_each_withdrawal_records_why_it_is_one_building(self):
        w = _load("st_louis_mo_founder_withdrawals_008b.json")
        assert len(w["withdrawals"]) == 2
        for record in w["withdrawals"]:
            assert len(record["why_one_building"]) >= 3
            assert record["surviving_identity_key"]
            assert record["original_ledger"]
            assert record["original_decision_preserved"]

    def test_the_wingate_telephone_discrepancy_is_recorded_not_hidden(self):
        # The two census rows disagree on the telephone. Retiring one does not
        # resolve that, and the ledger says so rather than implying it did.
        w = _load("st_louis_mo_founder_withdrawals_008b.json")
        wingate = [r for r in w["withdrawals"]
                   if r["retired_identity_key"] == "wingate at wyndham"][0]
        assert "6364921357" in wingate["known_discrepancy"]
        assert "census-hygiene" in wingate["known_discrepancy"]


class TestTheDualBrandConfirmation:
    def test_it_is_persisted_in_the_authority_artifact(self):
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        assert len(auth["identity_confirmations"]) == 1
        confirmation = auth["identity_confirmations"][0]
        assert confirmation["kind"] == "DISTINCT_PROPERTIES_AT_ONE_ADDRESS"
        assert "CONFIRMED AS TWO DISTINCT HOTELS" in confirmation["founder_ruling"]

    def test_it_names_the_discriminator_that_makes_them_distinct(self):
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        codes = {i["marriott_property_code"]
                 for i in auth["identity_confirmations"][0]["identities"]}
        assert codes == {"stlff", "stlsu"}

    def test_both_rows_survive_in_the_authority(self):
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        keys = ({r["normalized_name"] for r in auth["pet_friendly"]}
                | {r["normalized_name"] for r in auth["verified_no_pets"]})
        assert "fairfield by marriott inn and suites st louis chesterfield" in keys
        assert "springhill suites by marriott st louis chesterfield" in keys

    def test_they_carry_opposite_findings_which_only_two_hotels_can(self):
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        pf = {r["normalized_name"] for r in auth["pet_friendly"]}
        np_ = {r["normalized_name"] for r in auth["verified_no_pets"]}
        assert "fairfield by marriott inn and suites st louis chesterfield" in pf
        assert "springhill suites by marriott st louis chesterfield" in np_


class TestPublicationInventoryIsClean:
    @staticmethod
    def _rows():
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        return auth, auth["pet_friendly"] + auth["verified_no_pets"]

    def test_projected_public_hotel_routes_is_82(self):
        auth, _all = self._rows()
        assert auth["pet_friendly_count"] == 82
        assert len({r["canonical_name"] for r in auth["pet_friendly"]}) == 82

    def test_no_slug_collision_remains(self):
        _auth, rows = self._rows()
        slugs = [re.sub(r"[^a-z0-9]+", "-", r["canonical_name"].lower()).strip("-")
                 for r in rows]
        assert len(slugs) == len(set(slugs))

    def test_no_identity_collision_remains(self):
        _auth, rows = self._rows()
        keys = [r["normalized_name"] for r in rows]
        assert len(keys) == len(set(keys))

    def test_no_two_rows_share_a_source_url(self):
        # The sharpest duplicate-building signal: one page published twice.
        _auth, rows = self._rows()
        urls = [r["source_url"] for r in rows]
        assert len(urls) == len(set(urls))

    def test_the_retired_rows_publish_nothing(self):
        _auth, rows = self._rows()
        keys = {r["normalized_name"] for r in rows}
        assert "wingate at wyndham" not in keys
        assert "doubletree" not in keys

    def test_the_surviving_twins_are_present(self):
        _auth, rows = self._rows()
        keys = {r["normalized_name"] for r in rows}
        assert "wingate by wyndham st louis fenton route 66" in keys
        assert "doubletree by hilton hotel collinsville st louis" in keys

    def test_the_held_row_is_still_excluded(self):
        _auth, rows = self._rows()
        keys = {r["normalized_name"] for r in rows}
        assert "days inn and suites pontoon beach" not in keys

    def test_every_row_still_carries_its_citations(self):
        _auth, rows = self._rows()
        for row in rows:
            assert row["evidence"], row["normalized_name"]
            assert row["snapshot_hash"] and row["source_url"]
            assert row["publication_grade"] == "PUBLICATION_GRADE_CONFIRMED"
            assert row["membrane_verdict"] == "VALID"

    def test_the_census_still_reconciles_to_357(self):
        closure = _load("st_louis_mo_closure_ledger_007.json")
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        assert closure["count"] == closure["active_denominator"] == 357
        assert closure["reconciliation"]["missing"] == []
        assert closure["reconciliation"]["foreign"] == []
        assert closure["reconciliation"]["duplicate"] == []
        # 122 held-review rows = 119 current authority + 2 superseded + 1 held
        assert (closure["disposition_counts"]["HELD_REVIEW"]
                == auth["authority_total"] + auth["superseded_count"] + 1
                == 122)

    def test_008b_registered_nothing_and_that_record_is_unedited(self):
        """The three flags describe 008B's OWN act, not today's world.

        PTF-ST-LOUIS-REGISTER-PUBLISH-011 registered and published the market;
        it did not go back and rewrite the ledger that says a cleanup pass
        registered nothing, because that would erase the fact it records. Where
        the market stands NOW is read from the registry, which is the only
        thing that can answer it -- exactly as the 005 and 007 signature
        ledgers still say what they said on the day they were signed.
        """
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        assert auth["registered"] is False
        assert auth["published"] is False
        assert auth["deployed"] is False

    def test_the_registry_and_not_a_ledger_is_what_answers_it_now(self):
        from pathlib import Path

        from scripts.pettripfinder import market_authority as MA

        assert (Path(PKG) / "markets" / "authority" / "st-louis-mo").is_dir()
        assert (Path(PKG) / "markets" / "st-louis-mo.json").is_file()
        assert "st-louis-mo" in MA.registered_market_ids()
        # And the cleanup 008B performed still holds through registration:
        # neither superseded identity has a row in either publication set.
        auth = _load("st_louis_mo_proposed_authority_008b.json")
        retired = {row["identity_key"] for row in auth["superseded_rows"]}
        from scripts.pettripfinder.site_data import normalize_name
        published = {normalize_name(r["name"])
                     for r in MA.load_market_seed_rows("st-louis-mo")}
        excluded = {r["normalized_name"]
                    for r in MA.load_market_exclusions("st-louis-mo")}
        assert not (published | excluded) & retired

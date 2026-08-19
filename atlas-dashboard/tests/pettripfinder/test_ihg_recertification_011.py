"""PTF-IHG-RECERTIFICATION-011 -- re-deriving three records, and nothing else.

A re-certification is the moment a corpus is most exposed: the reader has
changed, and the temptation is to sweep every disagreeing record along with the
three that were scoped. So the tests here are mostly about restraint.

  * exactly three records may move, and the corpus-wide check is re-run rather
    than trusted from the previous work order;
  * every changed field must have a quote from the record's own evidence behind
    it -- a re-read that cannot show its working is a hand edit with extra
    steps;
  * the historical run record must survive. The 009 report keeps the extraction
    it actually produced and gains a pointer to the current one, because
    deleting the old value would delete the evidence that the defect existed.

The Staybridge hold gets its own class. It was placed for one reason -- a
flattened tiered fee -- and it may lift for exactly that reason and no other.
Lifting it must not be read as authorising publication, which is blocked for an
entirely separate reason this market has never satisfied.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import ihg_recertification_011 as REC
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.contracts import enums

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
RECERT = REPORTS / "ptf_ihg_recertification_011.json"
QUEUE = REPORTS / "ptf_reader_migration_queue_010.json"
LIVE_009 = REPORTS / "ptf_ihg_live_run_009.json"


def _doc(path: Path):
    if not path.is_file():
        pytest.skip("%s not present in this worktree" % path.name)
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# Scope
# --------------------------------------------------------------------------- #

class TestExactlyThreeRecordsMoved:
    def test_the_subject_count_is_asserted_before_any_mutation(self):
        import inspect
        source = inspect.getsource(REC.subjects)
        assert "ABORT" in source
        assert "EXPECTED_SUBJECTS" in source
        assert REC.EXPECTED_SUBJECTS == 3

    def test_the_artifact_carries_exactly_three(self):
        doc = _doc(RECERT)
        assert doc["subjects"] == 3
        assert len(doc["records"]) == 3

    def test_no_other_record_in_the_corpus_disagrees_with_the_reader(self):
        """Re-run corpus-wide rather than trusted from work order 010: if a
        fourth record had started disagreeing, sweeping it along silently is
        exactly the failure this check exists for."""
        d = _doc(RECERT)["differential_safety"]
        assert d["other_records_differing_corpus_wide"] == []
        assert d["clean"] is True
        assert d["corpus_unique_texts_scanned"] > 50

    def test_the_subjects_are_the_three_the_queue_named(self):
        recert = {r["slug"] for r in _doc(RECERT)["records"]}
        queued = {c["slug"] for c in _doc(QUEUE)["candidates"]}
        assert recert == queued


# --------------------------------------------------------------------------- #
# The re-derivation itself
# --------------------------------------------------------------------------- #

class TestTheRecordsWereReDerivedNotEdited:
    def test_no_provider_was_called(self):
        """The evidence did not change, only the reading of it. Re-fetching
        would introduce the one variable the comparison removes."""
        doc = _doc(RECERT)
        assert doc["network_requests"] == 0
        assert doc["provider_calls"] == 0
        for record in doc["records"]:
            assert record["network_requests"] == 0

    def test_each_record_names_the_evidence_it_was_read_from(self):
        for record in _doc(RECERT)["records"]:
            assert record["evidence_path"].startswith("data/acquisition") or \
                record["evidence_path"].startswith("data\\acquisition")
            assert record["evidence_block"].strip()

    def test_every_extracted_value_is_reproducible_from_the_evidence(self):
        """The strongest available check that nothing was hand-typed: parse
        the stored evidence again here and require the same answer."""
        for record in _doc(RECERT)["records"]:
            reading = PR.parse(record["evidence_block"], strategy="verify")
            again = dict(PR.to_extraction(reading, location="").extraction)
            assert again == record["new_extraction"], record["slug"]

    def test_every_quote_is_contiguous_within_its_own_block(self):
        for record in _doc(RECERT)["records"]:
            assert record["evidence_quotes"], record["slug"]
            for quote in record["evidence_quotes"]:
                assert quote in record["evidence_block"], (record["slug"], quote)
            assert record["evidence_contiguous"] is True

    def test_the_reader_commit_is_recorded_on_every_record(self):
        doc = _doc(RECERT)
        for record in doc["records"]:
            assert record["reader_commit"] == doc["reader_commit"]
            assert len(record["reader_commit"]) == 40


# --------------------------------------------------------------------------- #
# The three expected outcomes
# --------------------------------------------------------------------------- #

class TestTheExpectedOutcomes:
    def _by_slug(self, fragment):
        for record in _doc(RECERT)["records"]:
            if fragment in record["slug"]:
                return record
        pytest.fail("no record matching %r" % fragment)

    def test_staybridge_no_longer_carries_the_flattened_fee(self):
        record = self._by_slug("staybridge")
        assert record["old_extraction"]["pet_fee"] == 5000
        assert "pet_fee" not in record["new_extraction"]
        assert record["withheld"]["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
        assert record["withheld"]["fee_basis"] == enums.SCHEMA_CANNOT_REPRESENT
        assert "FLAG_TIERED_FEE" in record["flags"]

    def test_staybridge_drops_the_orphaned_currency_with_the_amount(self):
        """A currency with no amount is not a fact about anything."""
        record = self._by_slug("staybridge")
        assert "fee_currency" in record["old_extraction"]
        assert "fee_currency" not in record["new_extraction"]
        assert set(record["fields_changed"]) == {"pet_fee", "fee_currency"}

    def test_staybridge_keeps_every_unrelated_fact(self):
        record = self._by_slug("staybridge")
        new = record["new_extraction"]
        assert new["pets_allowed"] is True
        assert new["weight_limit"] == {"value": 80.0, "unit": enums.UNIT_LB}
        assert new["pet_count_limit"] == 2
        assert new["pet_count_scope"] == enums.SCOPE_PER_ROOM
        assert new["species_allowed"] == ["dog"]

    def test_staybridge_tier_language_survives_in_the_evidence(self):
        record = self._by_slug("staybridge")
        assert "150 USD for stays over 7 nights" in record["evidence_block"]

    def test_holiday_inn_express_gains_the_40lb_limit_and_nothing_else(self):
        record = self._by_slug("holiday-inn-express")
        assert record["fields_changed"] == ["weight_limit"]
        assert record["new_extraction"]["weight_limit"] == {
            "value": 40.0, "unit": enums.UNIT_LB}
        assert "maximum weight of 40lbs" in record["evidence_block"]

    def test_holiday_inn_riverfront_gains_the_50lb_limit_and_nothing_else(self):
        record = self._by_slug("riverfront")
        assert record["fields_changed"] == ["weight_limit"]
        assert record["new_extraction"]["weight_limit"] == {
            "value": 50.0, "unit": enums.UNIT_LB}
        assert "max weight of 50 lbs" in record["evidence_block"]

    def test_no_record_gained_a_fee_it_did_not_have(self):
        """The reader fix may only make the corpus quieter about price."""
        for record in _doc(RECERT)["records"]:
            old_fee = record["old_extraction"].get("pet_fee")
            new_fee = record["new_extraction"].get("pet_fee")
            assert not (old_fee is None and new_fee is not None), record["slug"]


# --------------------------------------------------------------------------- #
# History survives
# --------------------------------------------------------------------------- #

class TestTheHistoricalRecordSurvives:
    def test_the_009_run_keeps_the_extraction_it_actually_produced(self):
        """Deleting the old value would delete the evidence that the defect
        happened at all."""
        doc = _doc(LIVE_009)
        staybridge = [i for i in doc["items"] if "staybridge" in i["identity_key"]][0]
        assert staybridge["extraction"]["pet_fee"] == 5000

    def test_but_it_points_at_the_current_value(self):
        doc = _doc(LIVE_009)
        superseded = [i for i in doc["items"] if "extraction_superseded_by" in i]
        assert len(superseded) == 3
        for item in superseded:
            pointer = item["extraction_superseded_by"]
            assert pointer["work_order"] == "PTF-IHG-RECERTIFICATION-011"
            assert pointer["current_extraction"]
            assert pointer["reader_commit"]
        assert "current value" in doc["supersession_note"]

    def test_the_009_totals_were_not_touched(self):
        """A supersession pointer is not a licence to restate a measurement."""
        doc = _doc(LIVE_009)
        assert doc["totals"]["properties_tested"] == 5
        assert doc["totals"]["publication_grade"] == 5
        assert doc["totals"]["firecrawl_only_successes"] == 5


# --------------------------------------------------------------------------- #
# The hold
# --------------------------------------------------------------------------- #

class TestTheStaybridgeHold:
    def _hold(self):
        return _doc(QUEUE)["publication_holds"][
            "staybridge suites milwaukee airport south"]

    def test_it_lifted_only_with_every_condition_met(self):
        hold = self._hold()
        if hold["state"] == "LIFTED":
            assert all(hold["conditions"].values()), hold["conditions"]
        else:
            assert not all(hold["conditions"].values())

    def test_the_conditions_are_the_ones_the_work_order_set(self):
        conditions = self._hold()["conditions"]
        for key in ("stored_record_no_longer_carries_5000",
                    "tiered_fee_safely_withheld",
                    "evidence_still_attached_and_contiguous",
                    "publication_gates_pass"):
            assert key in conditions, key

    def test_lifting_the_hold_is_not_authorisation_to_publish(self):
        """The hold was placed on a flattened fee. Publication is blocked for
        a different reason this market has never satisfied, and conflating the
        two would turn a correctness fix into a publication event."""
        hold = self._hold()
        assert "does NOT authorise publication" in hold["scope_of_the_lift"]
        blocked = _doc(QUEUE)["publication_blocked_separately"]
        assert blocked["blocked"] is True
        assert "FIRST policy publication" in blocked["why"]

    def test_the_queue_is_marked_applied(self):
        doc = _doc(QUEUE)
        assert doc["status"] == "APPLIED"
        assert doc["applied_by"] == "PTF-IHG-RECERTIFICATION-011"
        assert all(c["recertified"] for c in doc["candidates"])


# --------------------------------------------------------------------------- #
# Authority reality, and the freezes
# --------------------------------------------------------------------------- #

class TestAuthorityWasNotInvented:
    def test_this_market_still_has_no_published_policy_shard(self):
        """The honest reason publication is blocked. If this ever becomes
        True without an authorised publication work order, something wrote
        authority that should not have."""
        state = _doc(RECERT)["authority_state"]
        assert state["exists"] is False
        assert "hotel_policy_facts_milwaukee-wi.json" == \
            state["policy_facts_shard_for_market"]

    def test_the_markets_that_do_publish_are_untouched(self):
        state = _doc(RECERT)["authority_state"]
        for name in ("hotel_policy_facts_cleveland-akron-canton-oh.json",
                     "hotel_policy_facts_dayton-oh.json",
                     "hotel_policy_facts_indianapolis-in.json",
                     "hotel_policy_facts_pittsburgh-pa.json"):
            assert name in state["markets_with_a_published_policy_shard"], name

    def test_the_milwaukee_authority_shard_is_identity_only(self):
        contents = _doc(RECERT)["authority_state"][
            "milwaukee_authority_shard_contents"]
        assert set(contents) == {"hotel_exclusions.json", "identity_routing.json",
                                 "seed_businesses.csv"}


class TestNothingElseMoved:
    def test_routing_is_unchanged(self):
        from scripts.pettripfinder.acquisition import registry as REGISTRY
        from scripts.pettripfinder.acquisition import providers as PROVIDERS
        registry = REGISTRY.load()
        assert registry["version"] == 4
        for brand in ("CHOICE", "WYNDHAM", "IHG"):
            assert registry["brands"][brand]["provider"] == PROVIDERS.FIRECRAWL
        for brand in ("MARRIOTT", "HILTON", "MOTEL6", "RED_ROOF"):
            assert registry["brands"][brand]["provider"] == \
                PROVIDERS.BRIGHTDATA_BROWSER
        assert registry["default"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER

    def test_the_provider_registry_is_unchanged(self):
        from scripts.pettripfinder.acquisition import providers as PROVIDERS
        assert set(PROVIDERS.implemented()) == {
            PROVIDERS.BRIGHTDATA_BROWSER, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER,
            PROVIDERS.FIRECRAWL}

    def test_the_failure_taxonomy_is_unchanged(self):
        from scripts.pettripfinder.acquisition import failures as F
        assert F.ESCALATING | F.TERMINAL == set(F.FAILURES)
        assert not F.may_escalate(F.SOURCE_CONTRADICTORY)
        assert F.may_escalate(F.ACCESS_DENIED)

    def test_re_certifying_writes_nothing_outside_its_own_artifacts(self):
        import inspect
        source = inspect.getsource(REC)
        for forbidden in ("hotel_policy_facts", "seed_businesses",
                          "hotel_exclusions", "identity_routing"):
            assert "%s\"" % forbidden not in source.replace("'", "\"") or \
                "glob" in source, forbidden

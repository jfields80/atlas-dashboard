"""PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 -- the proposal gates.

The proposal builder is a projection, so its job is to carry facts without
changing them and to refuse anything that violates the frozen schema-1.2
semantics. Those refusals are what these tests exercise, because a proposal
that quietly repairs a violation is worse than one that never ran.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP
from . import authority_freeze as AUTHORITY_FREEZE

REPO_ROOT = Path(__file__).resolve().parents[3]
PROPOSALS = (REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
             / "reports" / "milwaukee-wi_policy_proposals_001.json")


class TestFrozenSemanticsAreGatedNotRepaired:
    def test_a_clean_extraction_passes(self):
        assert PROP._gate({"pets_allowed": True,
                           "weight_limit": {"value": 40.0, "unit": "lb"},
                           "pet_count_limit": 2},
                          {"pet_fee": "SOURCE_SILENT"}) == []

    def test_a_fee_basis_outside_the_frozen_set_is_refused(self):
        """per_week is not a basis this schema has. Accepting it would let a
        renderer invent an arithmetic the source never stated."""
        problems = PROP._gate({"pet_fee": {"amount": 75, "basis": "per_week"}}, {})
        assert any("basis" in p for p in problems)

    def test_per_day_and_per_night_both_remain_legal(self):
        """They are different words the source chose, and collapsing one into
        the other is a silent semantic edit."""
        assert PROP._gate({"pet_fee": {"amount": 50, "basis": "per_day"}}, {}) == []
        assert PROP._gate({"pet_fee": {"amount": 50, "basis": "per_night"}}, {}) == []

    def test_scope_collapsed_into_basis_is_refused(self):
        problems = PROP._gate(
            {"pet_fee": {"amount": 50, "basis": "per_night", "scope": "per_night"}}, {})
        assert any("scope and basis" in p for p in problems)

    def test_unknown_must_be_absence_not_a_sentinel(self):
        for sentinel in (None, "unknown", "unstated"):
            problems = PROP._gate({"pets_allowed": True, "species": sentinel}, {})
            assert problems, sentinel

    def test_a_field_cannot_be_withheld_and_asserted_at_once(self):
        problems = PROP._gate({"pet_fee": {"amount": 25, "basis": "per_night"}},
                              {"pet_fee": "SOURCE_SILENT"})
        assert any("withheld and asserted" in p for p in problems)

    def test_individual_weight_is_not_combined_weight(self):
        limit = {"value": 50.0, "unit": "lb"}
        problems = PROP._gate({"weight_limit": limit, "combined_weight_limit": limit}, {})
        assert any("combined" in p for p in problems)

    def test_a_refusal_is_a_finding_not_a_violation(self):
        """missing policy != no pets. A captured refusal is well-formed; it is
        routed to its own reviewer class rather than slandered as malformed,
        and it is never applied as an exclusion here."""
        assert PROP._gate({"pets_allowed": False}, {}) == []
        assert PROP._is_refusal({"pets_allowed": False}) is True
        assert PROP._is_refusal({"pets_allowed": True}) is False
        # absence is not a refusal
        assert PROP._is_refusal({}) is False


class TestTheCommittedProposals:
    def _doc(self):
        if not PROPOSALS.is_file():
            import pytest
            pytest.skip("no proposals committed yet")
        return json.loads(PROPOSALS.read_text(encoding="utf-8-sig"))

    def test_nothing_is_published_or_approved(self):
        doc = self._doc()
        assert doc["authority_written"] is False
        assert doc["founder_approvals_created"] == 0
        for row in doc["items"]:
            assert row["published"] is False, row["identity_key"]
            assert row["founder_approved"] is False, row["identity_key"]

    def test_no_market_policy_authority_file_was_created(self):
        pkg = REPO_ROOT / "launch_packages" / "pettripfinder"
    # NARROWED. This claimed "milwaukee policy proposals 001 created no Milwaukee authority",
    # which was true and still is -- but read against the live filesystem
    # it became "Milwaukee may never have one", and the founder approved
    # 96 records in PTF-MILWAUKEE-FOUNDER-DECISION-036. The historical
    # claim is checked against the commit; the standing claim -- that
    # authority is recorded and never live inventory -- is checked too.
    AUTHORITY_FREEZE.assert_commit_created_no_authority("04dd8ea")
    AUTHORITY_FREEZE.assert_authority_is_recorded_not_live()

    def test_every_proposal_carries_the_quotes_its_facts_rest_on(self):
        for row in self._doc()["items"]:
            if not row["proposed_facts"]:
                continue
            assert row["evidence"], row["identity_key"]
            for item in row["evidence"]:
                assert item["quote"].strip(), row["identity_key"]
                assert item["location"].strip(), row["identity_key"]

    def test_every_proposal_is_first_party_and_publication_grade(self):
        for row in self._doc()["items"]:
            prov = row["provenance"]
            assert prov["source_url"].startswith("http"), row["identity_key"]
            assert prov["snapshot_hash"], row["identity_key"]
            assert prov["retrieved_at"], row["identity_key"]
            assert row["publication_grade"] == "PUBLICATION_GRADE_CONFIRMED", \
                row["identity_key"]

    def test_silence_is_recorded_as_withholding_not_as_a_value(self):
        for row in self._doc()["items"]:
            for field, reason in row["withheld_fields"].items():
                assert field not in row["proposed_facts"], row["identity_key"]
                assert reason.strip(), row["identity_key"]

    def test_the_inferences_deliberately_not_made_are_recorded(self):
        """A non-inference is the most easily lost fact in the pipeline: it
        looks exactly like an omission unless it is written down."""
        doc = self._doc()
        if not doc["items"]:
            return
        assert any(row["non_inferences"] for row in doc["items"])

    def test_no_committed_proposal_violates_the_frozen_semantics(self):
        for row in self._doc()["items"]:
            assert row["frozen_semantics_violations"] == [], (
                row["identity_key"], row["frozen_semantics_violations"])

    def test_a_generic_permission_never_becomes_a_species_map(self):
        """'Pets welcome' is not dogs + cats. The species map stays empty
        unless the surface named a species."""
        for row in self._doc()["items"]:
            species = row["proposed_facts"].get("species")
            if species is not None:
                quotes = " ".join(i["quote"] for i in row["evidence"]).lower()
                assert any(w in quotes for w in ("dog", "cat", "pet type", "breed")), \
                    row["identity_key"]

    def test_no_refusal_becomes_an_exclusion(self):
        """The single most dangerous move in this pipeline: a captured no-pets
        reading silently becoming a VERIFIED_NO_PETS authority record."""
        doc = self._doc()
        refusals = [r for r in doc["items"] if r.get("is_refusal")]
        for row in refusals:
            assert row["published"] is False
            assert row["founder_approved"] is False
            assert row["review_status"] == "REFUSAL_FOUNDER_REVIEW"
            # and it must still carry the words it rests on
            assert row["evidence"], row["identity_key"]
        # NARROWED by PTF-MILWAUKEE-FOUNDER-DECISION-036. What this test is
        # about is that a captured no-pets READING never silently becomes an
        # authority record -- asserted above, on the proposals themselves,
        # which is where the danger was. A Milwaukee exclusion may now exist,
        # because the founder read the evidence and approved twenty-six of
        # them in writing; what may not exist is one that nobody signed.
        pkg = REPO_ROOT / "launch_packages" / "pettripfinder"
        exclusions = json.loads((pkg / "hotel_exclusions.json").read_text(encoding="utf-8-sig"))
        for entry in exclusions["exclusions"]:
            if entry.get("market_id") != "milwaukee-wi":
                continue
            assert entry.get("reviewer_id"), entry["exclusion_id"]
            assert entry.get("reviewed_at"), entry["exclusion_id"]
            assert entry.get("evidence_quote", "").strip(), entry["exclusion_id"]

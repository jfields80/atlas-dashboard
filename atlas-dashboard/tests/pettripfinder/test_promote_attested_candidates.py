"""PTF-CAPTURE-003 -- promoting an APPROVED attestation into a candidate.

The hazard under test is fee binding. A hotel page states many amounts that are
not the pet fee -- the real Hilton Columbus at Easton page carries the $100.00
pet fee alongside a $100.00 early-checkout fee, a $100.00 late-checkout fee and
$12.00/$40.00 parking. Publishing the wrong one would look entirely plausible
and be wrong, so most of these tests are about NOT harvesting a number.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.promote_attested_candidates import (
    PromotionError,
    build_candidate,
    extract_pet_facts,
    find_pet_block,
    write_candidate,
)

# Real normalized shapes, verbatim from the three attested captures.
HILTON = (
    "Parking Self-parking: $12.00 per day Valet parking: $40.00 EV charging: Not "
    "available Airport shuttle John Glenn Columbus International Airport: Not "
    "available Kids services Cribs: Available Smoke-free Smoking rooms available: No "
    "Breakfast Available for a fee Type: Buffet "
    "Pets Non-refundable fee: $100.00 Max weight: 75 lbs Max size: Medium "
    "Pet policy: Pet liability release form required "
    "Our policies Cancellation Check-in/Check-out Minimum age to register 21 "
    "Early checkout-fee $100.00. Any changes to departure date made after check in "
    "are subject to this fee Late checkout-fee $100.00. Any check-outs past 3pm are "
    "subject to a late check out fee Payment"
)
ALOFT = (
    "HOTEL INFORMATION Check-in: 3:00 pm Check-out: 12:00 pm Minimum Age to Check In "
    "21 Smoke Free Property See Accessibility Features Front Desk Staffed "
    "Pet Policy Pets Welcome A signed policy is required at check in "
    "Non-Refundable Pet Fee Per Night: $50.00 Maximum Pet Weight: 40.0lbs "
    "Maximum Number of Pets in Room: 2 "
    "Parking Complimentary On-Site Parking Off-Site Parking Mid Town Garage 0.1 Miles"
)
TOWNEPLACE = (
    "Front Desk Staffed Pet Policy Pets Welcome Pets allowed with USD 100 "
    "non-refundable fee per stay plus tax Non-Refundable Pet Fee Per Stay: $100.00 "
    "Maximum Pet Weight: 60.0lbs Maximum Number of Pets in Room: 2 "
    "Parking Complimentary On-Site Parking Additional Parking Information"
)


def _attestation(**over):
    base = {
        "attestation_id": "attest-test000000000000000000",
        "attestation_hash": "sha256:" + "a" * 64,
        "listing_key": "aloft columbus easton",
        "listing_name": "Aloft Columbus Easton",
        "official_url": "https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/",
        "observed_at": "2026-07-29T14:28:29.492Z",
        "capture_method": "MANUAL_ATTESTATION",
        "source_type": "MANUAL_OFFICIAL_ATTESTATION",
        "affirmation": {"operator_id": "jfields80",
                        "attested_at": "2026-07-29T11:31:00-04:00"},
        "approval": {"state": "APPROVED", "approver_id": "jfields80",
                     "approved_at": "2026-07-29T12:05:00-04:00",
                     "approval_record_id": "APR-0002"},
        "publishable": True,
        "contradictions": ["multiple_fee_amounts:100,25.00,40,50.00"],
        "fee_amounts": ["100", "25.00", "40", "50.00"],
    }
    base.update(over)
    return base


# --------------------------------------------------------------------------- #
# 1. Fee binding -- the whole reason this adapter is careful.
# --------------------------------------------------------------------------- #

class TestFeeBinding:
    def test_hilton_binds_the_pet_fee_not_the_checkout_fee(self):
        """Three $100.00 amounts on the page; only one is the pet fee."""
        facts, _, _ = extract_pet_facts(HILTON)
        assert facts["pet_fee"] == "$100.00"
        assert facts["weight_limit"] == "75 pounds"

    def test_hilton_ignores_parking_amounts(self):
        facts, _, block = extract_pet_facts(HILTON)
        assert "12.00" not in block and "40.00" not in block
        assert facts["pet_fee"] != "$12.00"

    def test_checkout_fees_are_outside_the_block(self):
        block, _ = find_pet_block(HILTON)
        assert "Early checkout-fee" not in block
        assert "Late checkout-fee" not in block
        assert "Our policies" not in block

    def test_aloft_binds_fee_and_basis(self):
        facts, _, _ = extract_pet_facts(ALOFT)
        assert facts["pet_fee"] == "$50.00"
        assert facts["fee_basis"] == "per night"
        assert facts["weight_limit"] == "40.0 pounds"
        assert facts["pet_count_limit"] == "2"

    def test_towneplace_binds_per_stay(self):
        facts, _, _ = extract_pet_facts(TOWNEPLACE)
        assert facts["pet_fee"] == "$100.00"
        assert facts["fee_basis"] == "per stay"
        assert facts["weight_limit"] == "60.0 pounds"

    def test_parking_only_page_yields_no_pet_fee(self):
        """A bare dollar amount is never harvested."""
        with pytest.raises(PromotionError):
            extract_pet_facts("Parking Self-parking: $12.00 per day Valet parking: $40.00")

    def test_two_different_pet_fees_in_one_block_fails_closed(self):
        text = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Night: $50.00 "
                "Pet Fee: $75.00 Maximum Pet Weight: 40.0lbs Parking")
        with pytest.raises(PromotionError, match="multiple_distinct_pet_fees"):
            extract_pet_facts(text)

    def test_same_fee_stated_twice_is_not_a_contradiction(self):
        text = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: $100.00 "
                "Pet Fee: $100.00 Maximum Number of Pets in Room: 2 Parking")
        facts, _, _ = extract_pet_facts(text)
        assert facts["pet_fee"] == "$100.00"

    def test_unlabelled_amount_in_block_is_not_harvested(self):
        text = ("Pet Policy Pets Welcome Fees from $250 may apply elsewhere "
                "Maximum Number of Pets in Room: 2 Parking")
        facts, _, _ = extract_pet_facts(text)
        assert "pet_fee" not in facts
        assert facts["pets_allowed"] == "true"


# --------------------------------------------------------------------------- #
# 2. Block scoping.
# --------------------------------------------------------------------------- #

class TestBlockScoping:
    def test_block_ends_at_the_next_section(self):
        block, _ = find_pet_block(ALOFT)
        assert "Parking" not in block
        assert "Maximum Number of Pets in Room: 2" in block

    def test_prose_mention_of_pets_is_not_the_block(self):
        """A page may mention pets long before the policy card."""
        text = ("Our pets policy is famously friendly and guests love it here. " * 3
                + "Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: $80.00 "
                  "Maximum Number of Pets in Room: 2 Parking")
        facts, _, _ = extract_pet_facts(text)
        assert facts["pet_fee"] == "$80.00"

    def test_no_block_at_all_fails_closed(self):
        with pytest.raises(PromotionError, match="no_labelled_pet_policy_block_found"):
            extract_pet_facts("A lovely hotel with a fitness center and free wifi.")

    def test_block_without_publishable_facts_fails_closed(self):
        with pytest.raises(PromotionError):
            extract_pet_facts("Pets Please contact the hotel for details. Our policies")


# --------------------------------------------------------------------------- #
# 3. Approval gating and the candidate record.
# --------------------------------------------------------------------------- #

class TestCandidateBuild:
    def test_pending_attestation_is_refused(self):
        att = _attestation(approval={"state": "PENDING"}, publishable=False)
        with pytest.raises(PromotionError, match="attestation_not_approved"):
            build_candidate(att, ALOFT)

    def test_rejected_attestation_is_refused(self):
        att = _attestation(approval={"state": "REJECTED"}, publishable=False)
        with pytest.raises(PromotionError, match="attestation_not_approved"):
            build_candidate(att, ALOFT)

    def test_approved_but_not_publishable_is_refused(self):
        with pytest.raises(PromotionError, match="not_publishable"):
            build_candidate(_attestation(publishable=False), ALOFT)

    def test_candidate_is_ready_and_carries_its_basis(self):
        c = build_candidate(_attestation(), ALOFT)
        assert c["recommendation"] == "READY"
        wp = c["worker_provenance"]
        assert wp["promotion_basis"] == "MANUAL_OFFICIAL_ATTESTATION"
        assert wp["attestation_id"] == "attest-test000000000000000000"
        assert wp["approval"]["approval_record_id"] == "APR-0002"
        assert wp["attested_by"] == "jfields80"

    def test_candidate_records_the_full_amount_set_it_did_not_use(self):
        """An auditor must be able to see every amount on the page and check
        that the bound fee was chosen by label, not by luck."""
        c = build_candidate(_attestation(), ALOFT)
        assert c["worker_provenance"]["all_page_fee_amounts"] == [
            "100", "25.00", "40", "50.00"]
        assert c["worker_provenance"]["preserved_contradictions"]
        assert dict(c["pet_facts"])["pet_fee"] == "$50.00"

    def test_every_evidence_quote_is_verbatim_from_the_page(self):
        c = build_candidate(_attestation(), ALOFT)
        flat = " ".join(ALOFT.split())
        for e in c["evidence"]:
            assert e["quote"] in flat, e
            assert e["source_url"] == c["proposed_fields"][1][1]

    def test_pet_policy_field_is_the_verbatim_block(self):
        c = build_candidate(_attestation(), ALOFT)
        policy = dict((k, v) for k, v in
                      (tuple(p) for p in c["proposed_fields"]))["pet_policy"]
        assert policy in " ".join(ALOFT.split())
        assert "Non-Refundable Pet Fee Per Night: $50.00" in policy

    def test_no_fabricated_field_appears(self):
        c = build_candidate(_attestation(), HILTON)
        facts = dict(c["pet_facts"])
        # The Hilton block states no basis and no pet count; neither may be invented.
        assert "fee_basis" not in facts
        assert "pet_count_limit" not in facts
        assert facts["pet_fee"] == "$100.00"


class TestWrite:
    def test_writes_once_and_refuses_to_overwrite(self, tmp_path):
        c = build_candidate(_attestation(), ALOFT)
        p = write_candidate(c, tmp_path)
        assert p.exists()
        written = json.loads(p.read_text(encoding="utf-8"))
        assert written["recommendation"] == "READY"
        with pytest.raises(PromotionError, match="candidate_already_exists"):
            write_candidate(c, tmp_path)

    def test_written_candidate_matches_the_importer_shape(self, tmp_path):
        """The exporter reads these keys; a shape drift would silently drop
        the hotel rather than fail."""
        c = build_candidate(_attestation(), ALOFT)
        written = json.loads(write_candidate(c, tmp_path).read_text(encoding="utf-8"))
        for key in ("candidate_id", "evidence", "pet_facts", "proposed_fields",
                    "recommendation", "snapshot", "source_relationship",
                    "worker_provenance"):
            assert key in written
        assert [f[0] for f in written["proposed_fields"]] == [
            "name", "source_url", "pet_policy"]

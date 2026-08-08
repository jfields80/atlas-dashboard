"""PTF-POLICY-P0-001 -- readiness states, evidence bundle, worker bridge."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.policy import evidence_bundle as EB
from scripts.pettripfinder.policy import readiness as R
from scripts.pettripfinder.policy import worker_bridge as WB
from scripts.pettripfinder.policy.policy_observation import CONTRACT_VERSION


def observation(**overrides):
    base = {
        "obs_id": "obs-1",
        "contract_version": CONTRACT_VERSION,
        "hotel_ref": {"market_id": "columbus-oh",
                      "canonical_name": "Sample Inn Columbus",
                      "normalized_name": "sample inn columbus"},
        "identity_check": {"name_on_page": "Sample Inn Columbus"},
        "source_url": "https://www.sample-brand.com/columbus",
        "source_type": "official_property_page",
        "authority_tier": "PT1",
        "observed_at": "2026-08-01",
        "retrieved_at": "2026-08-08T12:00:00Z",
        "capture_method": "deterministic_fetch",
        "evidence": [{"quote": "Dogs and cats accepted.", "location": "policies",
                      "field_refs": ["pets_allowed"]}],
        "extraction": {"pets_allowed": True},
        "extraction_confidence": "EXACT_QUOTE",
        "flags": [],
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# Readiness states
# --------------------------------------------------------------------------- #

def test_clean_official_observation_confirms():
    assert R.derive([observation()]).state == R.POLICY_CONFIRMED


def test_declared_ambiguity_downgrades_to_with_ambiguity_not_below():
    result = R.derive([observation(
        extraction={"pets_allowed": True, "pet_fee": 5000, "fee_basis": "unknown"},
        evidence=[{"quote": "A $50 pet fee applies.", "location": "l",
                   "field_refs": ["pets_allowed", "pet_fee", "fee_basis"]}],
        flags=[{"code": "FLAG_AMBIGUOUS_BASIS",
                "detail": "the page never says per night or per stay"}])])
    assert result.state == R.POLICY_CONFIRMED_WITH_AMBIGUITY
    assert result.publishable is True
    assert "FLAG_AMBIGUOUS_BASIS" in result.ambiguities


def test_contradiction_outranks_everything():
    a = observation(obs_id="a", extraction={"pets_allowed": True, "pet_fee": 7500},
                    evidence=[{"quote": "$75", "location": "l",
                               "field_refs": ["pets_allowed", "pet_fee"]}])
    b = observation(obs_id="b", extraction={"pets_allowed": True, "pet_fee": 15000},
                    evidence=[{"quote": "$150", "location": "l",
                               "field_refs": ["pets_allowed", "pet_fee"]}])
    result = R.derive([a, b])
    assert result.state == R.POLICY_CONFLICT
    assert result.publishable is False
    assert result.conflicts and result.conflicts[0]["field"] == "pet_fee"


def test_blocked_with_no_evidence_is_source_blocked_not_not_found():
    result = R.derive([], blocked=True)
    assert result.state == R.SOURCE_BLOCKED


def test_all_surfaces_reached_with_nothing_is_not_found():
    result = R.derive([], all_surfaces_reached=True)
    assert result.state == R.POLICY_NOT_FOUND


def test_blocked_and_not_found_are_never_the_same_state():
    assert R.derive([], blocked=True).state != R.derive([], all_surfaces_reached=True).state


def test_inferred_extraction_requires_a_human():
    result = R.derive([observation(extraction_confidence="INFERRED")])
    assert result.state == R.MANUAL_VERIFICATION_REQUIRED
    assert result.publishable is False


def test_negative_policy_routes_to_the_exclusion_authority():
    result = R.derive([observation(
        extraction={"pets_allowed": False},
        evidence=[{"quote": "We do not accept pets.", "location": "l",
                   "field_refs": ["pets_allowed"]}])])
    assert result.state == R.POLICY_NEGATIVE_CONFIRMED
    assert "VERIFIED_NO_PETS" in R.EXISTING_STATE_MAP[result.state]["authority"]


def test_service_animal_only_is_not_found_not_confirmed():
    result = R.derive([observation(
        extraction={"service_animal_exception": "Service animals are welcome."},
        evidence=[{"quote": "Service animals are welcome.", "location": "l",
                   "field_refs": ["service_animal_exception"]}])],
        all_surfaces_reached=True)
    assert result.state == R.POLICY_NOT_FOUND
    assert result.publishable is False


def test_ota_hint_alone_never_confirms():
    result = R.derive([observation(source_type="ota", authority_tier="PT4")],
                      all_surfaces_reached=True)
    assert result.state == R.POLICY_NOT_FOUND
    assert result.hint_observations == ("obs-1",)


def test_archive_only_requires_a_human():
    result = R.derive([observation(source_type="cached_archive",
                                   authority_tier="PT1")])
    # An archive snapshot may not claim PT1; the membrane rejects it, leaving
    # nothing established.
    assert result.state in (R.MANUAL_VERIFICATION_REQUIRED, R.POLICY_NOT_FOUND)


def test_every_state_maps_to_an_existing_mechanism():
    assert set(R.EXISTING_STATE_MAP) == set(R.READINESS_STATES)
    for state, mapping in R.EXISTING_STATE_MAP.items():
        assert mapping["routing"] in ("READY", "REVIEW", "RETRY", "REJECTED")
        assert mapping["authority"].strip()


def test_rejected_observations_are_retained_not_dropped():
    result = R.derive([observation(), {"broken": True}])
    assert len(result.rejected_observations) == 1
    assert result.rejected_observations[0]["verdict"] == "REJECT_MALFORMED_OBSERVATION"


def test_no_numeric_confidence_gates_publication():
    """extraction_confidence is categorical fidelity, never a score."""
    high = R.derive([observation(extraction_confidence="EXACT_QUOTE")])
    para = R.derive([observation(extraction_confidence="PARAPHRASE")])
    assert high.state == R.POLICY_CONFIRMED
    # PARAPHRASE is not rejected by magnitude comparison; it simply is not
    # INFERRED, so it still derives a state rather than a number.
    assert para.state in R.READINESS_STATES


# --------------------------------------------------------------------------- #
# Evidence bundle / ladder transcript
# --------------------------------------------------------------------------- #

def transcript_entry(**overrides):
    base = {"attempt": 1, "step": "A", "source_attempted": "https://x.example/",
            "capture_method": "browser_assisted", "outcome": "SUCCESS"}
    base.update(overrides)
    return base


def test_bundle_builds_and_hashes_deterministically():
    hotel_ref = {"market_id": "columbus-oh", "canonical_name": "Sample Inn Columbus",
                 "normalized_name": "sample inn columbus"}
    kwargs = dict(hotel_ref=hotel_ref, worker_id="w1", assignment_id="a1",
                  transcript=[transcript_entry()], observations=[observation()],
                  artifact_hashes={"png": "a" * 64, "dom": "b" * 64})
    one = EB.build_bundle(**kwargs)
    two = EB.build_bundle(**kwargs)
    assert one["bundle_manifest_sha256"] == two["bundle_manifest_sha256"]
    assert one["observations_count"] == 1


def test_empty_transcript_is_refused():
    with pytest.raises(EB.EvidenceBundleError, match="non-empty"):
        EB.validate_transcript([])


def test_unknown_ladder_step_refused():
    with pytest.raises(EB.EvidenceBundleError, match="ladder step"):
        EB.validate_transcript_entry(transcript_entry(step="Z"))


def test_unknown_outcome_refused():
    with pytest.raises(EB.EvidenceBundleError, match="outcome"):
        EB.validate_transcript_entry(transcript_entry(outcome="PROBABLY_FINE"))


def test_bad_artifact_hash_refused():
    with pytest.raises(EB.EvidenceBundleError, match="64 hex"):
        EB.build_bundle(hotel_ref={"normalized_name": "x"}, worker_id="w",
                        assignment_id="a", transcript=[transcript_entry()],
                        artifact_hashes={"png": "short"})


def test_worker_readiness_proposal_is_marked_advisory():
    bundle = EB.build_bundle(
        hotel_ref={"normalized_name": "x"}, worker_id="w", assignment_id="a",
        transcript=[transcript_entry()], proposed_readiness=R.POLICY_CONFIRMED)
    assert "advisory only" in bundle["proposed_readiness_note"]


def test_exhaustion_requires_every_surface_to_have_answered():
    reached = [transcript_entry(step="A", outcome="NO_POLICY_SECTION"),
               transcript_entry(step="B", outcome="NO_POLICY_SECTION")]
    blocked = [transcript_entry(step="A", outcome="BLOCKED_403"),
               transcript_entry(step="B", outcome="NO_POLICY_SECTION")]
    assert EB.ladder_reached_exhaustion(reached) is True
    assert EB.ladder_reached_exhaustion(blocked) is False
    assert EB.ladder_was_blocked(blocked) is True


def test_budget_cut_short_is_not_exhaustion():
    cut = [transcript_entry(step="A", outcome="NO_POLICY_SECTION"),
           transcript_entry(step="B", outcome="NOT_ATTEMPTED_BUDGET")]
    assert EB.ladder_reached_exhaustion(cut) is False


# --------------------------------------------------------------------------- #
# Worker bridge
# --------------------------------------------------------------------------- #

def test_bridge_maps_a_capture_payload_without_extracting():
    payload = {"final_url": "https://www.sample-brand.com/columbus",
               "identity": {"name": "Sample Inn Columbus", "street": "1 Test St"},
               "text_sha256": "c" * 64, "html_sha256": "d" * 64}
    obs = WB.from_capture_payload(
        payload,
        hotel_ref={"market_id": "columbus-oh", "canonical_name": "Sample Inn Columbus",
                   "normalized_name": "sample inn columbus"},
        obs_id="obs-bridge", observed_at="2026-08-01",
        retrieved_at="2026-08-08T12:00:00Z")
    assert obs["extraction"] == {}          # the bridge never parses prose
    assert obs["identity_check"]["name_on_page"] == "Sample Inn Columbus"
    assert obs["identity_check"]["address_on_page"] == "1 Test St"
    assert obs["snapshot_hash"] == "c" * 64


def test_bridge_refuses_a_payload_with_no_identity_evidence():
    with pytest.raises(WB.WorkerBridgeError, match="identity gate"):
        WB.from_capture_payload(
            {"final_url": "https://x.example/"},
            hotel_ref={"market_id": "m", "canonical_name": "C", "normalized_name": "c"},
            obs_id="o", observed_at="2026-08-01", retrieved_at="2026-08-08T00:00:00Z")


def test_bridge_refuses_a_payload_with_no_url():
    with pytest.raises(WB.WorkerBridgeError, match="final_url"):
        WB.from_capture_payload(
            {"identity": {"name": "X"}},
            hotel_ref={"market_id": "m", "canonical_name": "C", "normalized_name": "c"},
            obs_id="o", observed_at="2026-08-01", retrieved_at="2026-08-08T00:00:00Z")


def test_capture_reasons_map_to_ladder_outcomes():
    assert WB.reason_to_outcome("ACCESS_DENIED") == "BLOCKED_403"
    assert WB.reason_to_outcome("CAPTCHA_OR_CHALLENGE") == "BLOCKED_CHALLENGE"
    assert WB.reason_to_outcome("POLICY_NOT_FOUND") == "NO_POLICY_SECTION"
    assert WB.reason_to_outcome("IDENTITY_MISMATCH") == "WRONG_PROPERTY"
    # An unmapped reason returns "" rather than a default that means "fine".
    assert WB.reason_to_outcome("SOMETHING_NEW") == ""


def test_every_mapped_outcome_is_in_the_closed_ladder_vocabulary():
    assert set(WB.REASON_TO_LADDER_OUTCOME.values()) <= EB.LADDER_OUTCOMES

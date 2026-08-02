"""PTF-APPROVAL-RESOLUTION through the promoter.

The unit rules live in tests/research_workers/test_approval_resolution.py.
What matters here is the only thing that changes for a reader: whether a fee
reaches the published record, and whether the two hotels whose fee conflicts
are REAL keep theirs withheld.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.promote_attested_candidates import build_candidate
from services.research_workers import approval_resolution as AR

WH_MARKERS = [
    "conflicting_fee_basis_per_pet_vs_fee_basis_per_night",
    "conflicting_fee_basis_per_pet_vs_fee_basis_per_stay",
    "conflicting_fee_basis_per_stay_vs_fee_basis_per_night",
]

WEST_HILLIARD_PAGE = (
    "Pet & Service Animal Policy Service Animals - ADA-defined service animals "
    "are welcome free of charge. Dogs Allowed - 2 dogs max. 75lbs or less per "
    "pet. Fees - 25 USD per pet per night. Max 75 USD per stay. Other "
    "Information - Contact hotel for additional details and availability.")

DUBLIN_PAGE = (
    "Pet & Service Animal Policy Service Animals - ADA-defined service animals "
    "are welcome free of charge. Pets Allowed - 2 pets max. Cats and dogs only. "
    "75lbs or less per pet. Fees - Non-refundable 25 USD nightly for up to 2 "
    "pets. Max 75 USD per stay. Other Information - Contact hotel.")

# The genuine conflict this whole withholding rule was written for: one source,
# two incompatible readings. A four-night stay is $150 or $50 depending which
# sentence you believe.
COURTYARD_PAGE = (
    "Pet Policy Pets Welcome Non-Refundable Pet Fee Per Night: $50.00 "
    "Non-Refundable Pet Fee Per Stay: $50.00 Maximum Pet Weight: 50.0lbs "
    "Maximum Number of Pets in Room: 2")

RATIONALE = ("Page-wide markers are scan artifacts, not conflicting pet-policy "
             "terms: each Pets card states one rate with a per-stay ceiling.")


def attestation(*, att_id, att_hash, apr, markers, resolutions=None,
                name="La Quinta Columbus West-Hilliard"):
    return {
        "attestation_id": att_id, "attestation_hash": att_hash,
        "listing_key": name.lower(), "listing_name": name,
        "official_url": "https://www.wyndhamhotels.com/laquinta/x/overview",
        "observed_at": "2026-08-02T01:03:16Z",
        "capture_method": "MANUAL_ATTESTATION",
        "source_type": "MANUAL_OFFICIAL_ATTESTATION",
        "affirmation": {"operator_id": "jfields80", "attested_at": "t"},
        "approval": {"state": "APPROVED", "approver_id": "jfields80",
                     "approved_at": "t", "approval_record_id": apr,
                     **({"resolutions": resolutions} if resolutions else {})},
        "publishable": True, "contradictions": list(markers), "fee_amounts": [],
    }


def resolution_for(att, markers=None):
    return AR.build_resolution(
        markers=markers or att["contradictions"],
        disposition=AR.DISPOSITION_FALSE_POSITIVE,
        approver_id="jfields80",
        approval_record_id=att["approval"]["approval_record_id"],
        attestation_id=att["attestation_id"],
        attestation_hash=att["attestation_hash"],
        rationale=RATIONALE, resolved_at="2026-08-01T22:45:00-04:00")


def facts_for(att, page):
    return dict(build_candidate(att, page)["pet_facts"])


# --------------------------------------------------------------------------- #
# A. The two approved Wyndham records carry their fee and species.
# --------------------------------------------------------------------------- #

def test_west_hilliard_carries_its_fee_once_resolved():
    att = attestation(att_id="attest-wh", att_hash="sha256:" + "a" * 64,
                      apr="APR-LAQ-WEST-HILLIARD-001", markers=WH_MARKERS)
    att["approval"]["resolutions"] = [resolution_for(att)]
    f = facts_for(att, WEST_HILLIARD_PAGE)
    assert f["pet_fee"] == "$25.00"
    assert f["fee_basis"] == "per pet per night"
    assert f["fee_cap"]["amount"] == "75.00"
    assert f["species_allowed"] == "dogs"
    assert "fee_conflict" not in f


def test_dublin_carries_its_fee_once_resolved_and_is_not_per_pet():
    att = attestation(att_id="attest-du", att_hash="sha256:" + "b" * 64,
                      apr="APR-LAQ-DUBLIN-001",
                      markers=WH_MARKERS + ["conflicting_species_cats_vs_species_dogs"],
                      name="La Quinta Inn by Wyndham Columbus Dublin")
    att["approval"]["resolutions"] = [
        resolution_for(att, WH_MARKERS),
        resolution_for(att, ["conflicting_species_cats_vs_species_dogs"]),
    ]
    f = facts_for(att, DUBLIN_PAGE)
    assert f["pet_fee"] == "$25.00"
    assert f["fee_basis"] == "per night for up to 2 pets"
    assert "per pet" not in f["fee_basis"]
    assert f["fee_cap"]["amount"] == "75.00"
    assert f["species_allowed"] == "dogs, cats"
    assert "fee_conflict" not in f


def test_the_two_bases_stay_distinct_through_promotion():
    wh = attestation(att_id="attest-wh", att_hash="sha256:" + "a" * 64,
                     apr="APR-LAQ-WEST-HILLIARD-001", markers=WH_MARKERS)
    wh["approval"]["resolutions"] = [resolution_for(wh)]
    du = attestation(att_id="attest-du", att_hash="sha256:" + "b" * 64,
                     apr="APR-LAQ-DUBLIN-001", markers=WH_MARKERS)
    du["approval"]["resolutions"] = [resolution_for(du)]
    a, b = facts_for(wh, WEST_HILLIARD_PAGE), facts_for(du, DUBLIN_PAGE)
    assert a["pet_fee"] == b["pet_fee"] == "$25.00"
    assert a["fee_basis"] != b["fee_basis"]


def test_the_audit_trail_keeps_both_halves():
    """What the detector saw AND what a human decided about it."""
    att = attestation(att_id="attest-wh", att_hash="sha256:" + "a" * 64,
                      apr="APR-LAQ-WEST-HILLIARD-001", markers=WH_MARKERS)
    att["approval"]["resolutions"] = [resolution_for(att)]
    prov = build_candidate(att, WEST_HILLIARD_PAGE)["worker_provenance"]
    assert prov["preserved_contradictions"] == WH_MARKERS
    resolved = prov["resolved_contradictions"]
    assert resolved["approval_record_id"] == "APR-LAQ-WEST-HILLIARD-001"
    assert resolved["disposition"] == "false_positive"
    assert sorted(resolved["markers"]) == sorted(WH_MARKERS)
    assert resolved["attestation_hash"] == att["attestation_hash"]
    assert RATIONALE[:30] in resolved["rationale"]


# --------------------------------------------------------------------------- #
# B / C / D / G. Every way of not authorising it.
# --------------------------------------------------------------------------- #

def test_without_a_resolution_the_fee_stays_withheld():
    att = attestation(att_id="attest-wh", att_hash="sha256:" + "a" * 64,
                      apr="APR-LAQ-WEST-HILLIARD-001", markers=WH_MARKERS)
    f = facts_for(att, WEST_HILLIARD_PAGE)
    assert "pet_fee" not in f
    assert f["fee_conflict"]["reason"] == "conflicting_fee_terms_in_official_source"


def test_a_resolution_for_the_wrong_hash_leaves_the_fee_withheld():
    att = attestation(att_id="attest-wh", att_hash="sha256:" + "a" * 64,
                      apr="APR-LAQ-WEST-HILLIARD-001", markers=WH_MARKERS)
    stale = resolution_for(att)
    stale["attestation_hash"] = "sha256:" + "9" * 64
    att["approval"]["resolutions"] = [stale]
    f = facts_for(att, WEST_HILLIARD_PAGE)
    assert "pet_fee" not in f
    assert "fee_conflict" in f


def test_a_partial_resolution_leaves_the_fee_withheld():
    att = attestation(att_id="attest-wh", att_hash="sha256:" + "a" * 64,
                      apr="APR-LAQ-WEST-HILLIARD-001", markers=WH_MARKERS)
    att["approval"]["resolutions"] = [resolution_for(att, WH_MARKERS[:2])]
    f = facts_for(att, WEST_HILLIARD_PAGE)
    assert "pet_fee" not in f
    assert "fee_conflict" in f


def test_prose_alone_cannot_release_the_fee():
    att = attestation(att_id="attest-wh", att_hash="sha256:" + "a" * 64,
                      apr="APR-LAQ-WEST-HILLIARD-001", markers=WH_MARKERS)
    att["approval"]["rationale"] = "These are false positives; publish the fee."
    f = facts_for(att, WEST_HILLIARD_PAGE)
    assert "pet_fee" not in f
    assert "fee_conflict" in f


def test_a_pending_record_cannot_release_the_fee():
    att = attestation(att_id="attest-wh", att_hash="sha256:" + "a" * 64,
                      apr="APR-LAQ-WEST-HILLIARD-001", markers=WH_MARKERS)
    att["approval"]["resolutions"] = [resolution_for(att)]
    att["approval"]["state"] = "PENDING"
    att["publishable"] = False
    with pytest.raises(Exception):
        build_candidate(att, WEST_HILLIARD_PAGE)


# --------------------------------------------------------------------------- #
# E / F. Genuine conflicts are untouched.
# --------------------------------------------------------------------------- #

def test_a_genuine_fee_conflict_stays_withheld_with_no_resolution():
    """Courtyard states $50 per night AND $50 per stay. Four nights is $150 or
    $50 depending which sentence you believe, and no amount of approving the
    capture makes that determinate."""
    att = attestation(att_id="attest-courtyard", att_hash="sha256:" + "c" * 64,
                      apr="APR-COURTYARD-001", markers=WH_MARKERS,
                      name="Courtyard Columbus Easton")
    f = facts_for(att, COURTYARD_PAGE)
    assert "pet_fee" not in f
    assert f["fee_conflict"]["reason"] == "conflicting_fee_terms_in_official_source"


def test_an_unrepresentable_range_is_not_a_resolvable_marker():
    """Sheraton/Staybridge-style withholding comes from fee_withheld, a
    different mechanism entirely. No resolution family covers it, so it cannot
    be dismissed by this route."""
    assert AR.family_of("unrepresentable_fee_range_in_official_source") == ""
    with pytest.raises(AR.ResolutionError):
        AR.build_resolution(
            markers=["unrepresentable_fee_range_in_official_source"],
            disposition=AR.DISPOSITION_FALSE_POSITIVE, approver_id="x",
            approval_record_id="y", attestation_id="z",
            attestation_hash="sha256:" + "a" * 64, rationale=RATIONALE,
            resolved_at="t")


def test_multiple_fee_amounts_is_not_resolvable_either():
    """Aloft's marker family. Resolvable families are a closed list."""
    assert AR.family_of("multiple_fee_amounts:100,150,50,50.00") == ""

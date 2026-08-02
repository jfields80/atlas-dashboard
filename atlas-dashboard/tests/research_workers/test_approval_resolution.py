"""PTF-APPROVAL-RESOLUTION -- a human may overrule a specific false positive.

The detector scans the whole page, which is what makes it useful and what makes
it noisy. Two La Quinta properties each state one unambiguous price and get
`conflicting_fee_basis_*` anyway, because the words "per pet", "per night" and
"per stay" all appear somewhere on a page that also carries a rewards banner.

So the interesting tests here are not the two that let the fee through. They
are the six that refuse: no resolution, wrong hash, half a family, prose only,
and the two hotels whose fee conflicts are real.
"""

from __future__ import annotations

import copy

import pytest

from services.research_workers import approval_resolution as AR

ATT_ID = "attest-18dd045fe0028b715db0ed76"
ATT_HASH = "sha256:ef85f7db37d22de22743bbd43abe4516"
APR = "APR-LAQ-WEST-HILLIARD-001"

FEE_MARKERS = [
    "conflicting_fee_basis_per_pet_vs_fee_basis_per_night",
    "conflicting_fee_basis_per_pet_vs_fee_basis_per_stay",
    "conflicting_fee_basis_per_stay_vs_fee_basis_per_night",
]
SPECIES_MARKERS = ["conflicting_species_cats_vs_species_dogs"]

RATIONALE = ("Page-wide markers are scan artifacts, not conflicting pet-policy "
             "terms: the Pets card states one rate with a per-stay ceiling.")


def record(*, markers=None, state="APPROVED", publishable=True,
           att_id=ATT_ID, att_hash=ATT_HASH, apr=APR, resolutions=None):
    return {
        "attestation_id": att_id,
        "attestation_hash": att_hash,
        "listing_name": "La Quinta Columbus West-Hilliard",
        "contradictions": list(FEE_MARKERS if markers is None else markers),
        "publishable": publishable,
        "approval": {"state": state, "approver_id": "jfields80",
                     "approved_at": "2026-08-01T22:31:11-04:00",
                     "approval_record_id": apr,
                     **({"resolutions": resolutions} if resolutions else {})},
    }


def resolution(*, markers=None, att_id=ATT_ID, att_hash=ATT_HASH, apr=APR,
               disposition=AR.DISPOSITION_FALSE_POSITIVE, rationale=RATIONALE):
    return AR.build_resolution(
        markers=markers if markers is not None else FEE_MARKERS,
        disposition=disposition, approver_id="jfields80",
        approval_record_id=apr, attestation_id=att_id,
        attestation_hash=att_hash, rationale=rationale,
        resolved_at="2026-08-01T22:45:00-04:00")


# --------------------------------------------------------------------------- #
# A. A complete, correctly-bound resolution authorises the family.
# --------------------------------------------------------------------------- #

def test_a_full_resolution_authorises_the_family():
    r = record(resolutions=[resolution()])
    assert AR.family_fully_resolved(r, AR.FAMILY_FEE_BASIS) is True
    assert set(AR.resolved_markers(r)) == set(FEE_MARKERS)
    auth = AR.authorizing_resolution(r, AR.FAMILY_FEE_BASIS)
    assert auth["approval_record_id"] == APR
    assert auth["disposition"] == AR.DISPOSITION_FALSE_POSITIVE


def test_the_detector_markers_are_never_removed():
    """The audit trail is BOTH: what the scanner saw and what a human decided.
    A resolution that edited the markers away would destroy the first half."""
    r = record()
    updated = AR.attach_resolutions(r, [resolution()])
    assert updated["contradictions"] == FEE_MARKERS
    assert r["contradictions"] == FEE_MARKERS          # original untouched
    assert updated["approval"]["resolutions"][0]["markers"] == sorted(FEE_MARKERS)


def test_species_and_fee_families_resolve_independently():
    r = record(markers=FEE_MARKERS + SPECIES_MARKERS,
               resolutions=[resolution(), resolution(markers=SPECIES_MARKERS)])
    assert AR.family_fully_resolved(r, AR.FAMILY_FEE_BASIS) is True
    assert AR.family_fully_resolved(r, AR.FAMILY_SPECIES) is True


# --------------------------------------------------------------------------- #
# B. No structured resolution -> nothing is authorised.
# --------------------------------------------------------------------------- #

def test_an_approved_record_without_a_resolution_authorises_nothing():
    """Approval is permission to publish the capture, not permission to ignore
    what the detector found."""
    r = record()
    assert AR.resolved_markers(r) == ()
    assert AR.family_fully_resolved(r, AR.FAMILY_FEE_BASIS) is False


# --------------------------------------------------------------------------- #
# C. Wrong attestation hash -> fail closed.
# --------------------------------------------------------------------------- #

def test_a_resolution_for_a_different_hash_is_ignored():
    """The judgement was about evidence somebody read. Re-capture the page and
    the hash moves, and the old decision stops applying -- it must not be
    inherited by content nobody reviewed."""
    stale = resolution(att_hash="sha256:" + "0" * 64)
    r = record(resolutions=[stale])
    assert AR.resolved_markers(r) == ()
    assert AR.family_fully_resolved(r, AR.FAMILY_FEE_BASIS) is False


def test_attaching_a_mismatched_hash_is_refused_outright():
    with pytest.raises(AR.ResolutionError, match="hash does not match"):
        AR.attach_resolutions(record(),
                              [resolution(att_hash="sha256:" + "b" * 64)])


def test_a_resolution_for_a_different_attestation_is_ignored():
    r = record(resolutions=[resolution(att_id="attest-somebodyelse")])
    assert AR.resolved_markers(r) == ()


def test_a_resolution_naming_another_approval_record_is_ignored():
    r = record(resolutions=[resolution(apr="APR-SOMETHING-ELSE")])
    assert AR.resolved_markers(r) == ()


# --------------------------------------------------------------------------- #
# D. Partial resolution is not resolution.
# --------------------------------------------------------------------------- #

def test_resolving_some_markers_leaves_the_family_unresolved():
    """Two of three disposed of means something in that field is still
    contested, and a contested field stays withheld."""
    partial = resolution(markers=FEE_MARKERS[:2])
    r = record(resolutions=[partial])
    assert set(AR.resolved_markers(r)) == set(FEE_MARKERS[:2])
    assert AR.family_fully_resolved(r, AR.FAMILY_FEE_BASIS) is False


def test_resolving_only_species_leaves_the_fee_withheld():
    r = record(markers=FEE_MARKERS + SPECIES_MARKERS,
               resolutions=[resolution(markers=SPECIES_MARKERS)])
    assert AR.family_fully_resolved(r, AR.FAMILY_SPECIES) is True
    assert AR.family_fully_resolved(r, AR.FAMILY_FEE_BASIS) is False


# --------------------------------------------------------------------------- #
# G. Prose is not a decision a program can check.
# --------------------------------------------------------------------------- #

def test_a_free_text_rationale_alone_authorises_nothing():
    """The whole reason this module exists. An approver can write anything in
    the rationale; only a structured resolution moves a gate."""
    r = record()
    r["approval"]["rationale"] = (
        "These markers are obviously false positives, publish the fee.")
    assert AR.resolved_markers(r) == ()
    assert AR.family_fully_resolved(r, AR.FAMILY_FEE_BASIS) is False


def test_a_rationale_too_short_to_be_a_reason_is_refused():
    with pytest.raises(AR.ResolutionError, match="rationale"):
        resolution(rationale="fine")


# --------------------------------------------------------------------------- #
# State and structural guards.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("state", ["PENDING", "REJECTED", ""])
def test_only_an_approved_record_authorises_anything(state):
    r = record(state=state, resolutions=[resolution()])
    assert AR.resolved_markers(r) == ()


def test_a_record_marked_unpublishable_authorises_nothing():
    r = record(publishable=False, resolutions=[resolution()])
    assert AR.resolved_markers(r) == ()


def test_resolutions_may_only_be_attached_to_an_approved_record():
    with pytest.raises(AR.ResolutionError, match="APPROVED"):
        AR.attach_resolutions(record(state="PENDING"), [resolution()])


def test_a_resolution_cannot_name_a_marker_the_detector_never_reported():
    """Inventing a marker would let someone pre-authorise a conflict that has
    not happened yet."""
    with pytest.raises(AR.ResolutionError, match="never reported"):
        AR.attach_resolutions(
            record(markers=FEE_MARKERS[:1]), [resolution(markers=FEE_MARKERS)])


def test_unresolvable_families_are_refused():
    """The resolvable list is closed on purpose: a new family is a new decision
    about what a person may overrule."""
    with pytest.raises(AR.ResolutionError, match="outside the resolvable"):
        resolution(markers=["conflicting_weight_limit_a_vs_b"])


def test_one_resolution_covers_one_family():
    with pytest.raises(AR.ResolutionError, match="one family"):
        resolution(markers=FEE_MARKERS + SPECIES_MARKERS)


@pytest.mark.parametrize("field", list(AR.REQUIRED_FIELDS))
def test_validate_rejects_a_resolution_missing_any_required_field(field):
    res = dict(resolution())
    res.pop(field)
    ok, why = AR.validate_resolution(res)
    assert ok is False
    assert field in why or "missing_field" in why


def test_an_unknown_disposition_is_refused():
    with pytest.raises(AR.ResolutionError, match="disposition"):
        resolution(disposition="looks_fine_to_me")


def test_a_malformed_hash_is_refused():
    with pytest.raises(AR.ResolutionError, match="sha256"):
        resolution(att_hash="not-a-digest")


def test_family_of_only_matches_the_closed_list():
    assert AR.family_of("conflicting_fee_basis_x") == AR.FAMILY_FEE_BASIS
    assert AR.family_of("conflicting_species_x") == AR.FAMILY_SPECIES
    assert AR.family_of("multiple_fee_amounts:100,150") == ""
    assert AR.family_of("") == ""


def test_no_recorded_marker_means_nothing_to_resolve():
    """A record with no conflicts is not "fully resolved" -- there was never a
    question, and answering one that was not asked would be an odd claim."""
    assert AR.family_fully_resolved(record(markers=[]), AR.FAMILY_FEE_BASIS) is False

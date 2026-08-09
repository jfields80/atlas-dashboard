"""PTF-MACHINE-REVIEW -- the record type for a SUCCESSFUL automated capture.

The operator-attestation contract is a human instrument: Gate 1 admits only a
demonstrated automated FAILURE, and Gate 2 fixes a first-person statement -- "I
personally opened this URL in an ordinary browser..." -- that only a person who
did that can honestly make.

The discovery sweep produced the opposite case, 49 times: automation succeeded.
Routing those through the attestation contract would mean writing, in a named
operator's identity, a claim about an act nobody performed. This record type
exists so that never has to happen, and these tests exist to keep the two paths
from silently becoming one.

Offline: no network, no browser, no production write.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib

import pytest

from services.research_workers import machine_capture_review as MR
from services.research_workers.capture_automation.attestation_bridge import (
    normalized_url,
)

URL = "https://www.example-brand.com/en/hotels/xyzab-test-property/"
PREFIX = "Skip to content Home Rooms Offers "
EXCERPT = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: $100.00 "
           "Maximum Pet Weight: 75.0lbs Maximum Number of Pets in Room: 2")
SUFFIX = " Contact Us Careers"
TEXT = PREFIX + EXCERPT + SUFFIX
HTML = "<html><body><p>%s</p></body></html>" % EXCERPT

IDENTITY = {
    "outcome": "IDENTITY_CONFIRMED",
    "may_proceed": True,
    "keys": {
        "outcome": "IDENTITY_CONFIRMED",
        "has_authoritative_key": True,
        "independent_groups": ["address", "phone"],
        "keys": [
            {"key": "normalized_street_address", "group": "address",
             "basis": "structured_metadata", "authoritative": True, "counts": True,
             "expected": "1 Test Street, Columbus, OH 43219, USA",
             "observed": "1 Test Street"},
            {"key": "property_phone", "group": "phone",
             "basis": "structured_metadata", "authoritative": True, "counts": True,
             "expected": "614-555-0100", "observed": "+1 614-555-0100"},
        ],
    },
}


class _Job:
    def __init__(self):
        self.assignment_id = "discovery:test-property"
        self.listing_key = "test property"
        self.listing_name = "Test Property"
        self.official_url = URL


class _Bridged:
    """The shape ``bridge_capture`` returns, with nothing else attached."""

    def __init__(self, payload, capture, shot, view):
        self.job = _Job()
        self.payload = payload
        self.screenshot_path = shot
        self.view_path = view
        self.normalized_url = normalized_url(URL)
        self.identity_outcome = "IDENTITY_CONFIRMED"
        self.identity_key_groups = ("address", "phone")
        self.policy_excerpt = EXCERPT
        self.verified = ("queue_identity_fields", "artifacts_present",
                         "identity_confirmed", "capture_hashes", "screenshot_hash",
                         "final_url", "policy_block_offsets")
        self.status = "PENDING"

    @property
    def publishable(self):
        return False

    def capture_path_of(self):
        return self._capture

    def set_capture(self, path):
        self._capture = path
        return self


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def evidence(tmp_path):
    """Real files on disk, because every gate re-derives from disk."""
    capture = tmp_path / "capture.json"
    shot = tmp_path / "shot.png"
    view = tmp_path / "view.json"
    payload = {
        "schema": "ptf-official-capture/1.0",
        "extension_version": "ptf-capture-003/1.0.0",
        "captured_at": "2026-08-04T04:10:07.584Z",
        "requested_url": URL, "final_url": URL, "canonical_url": URL,
        "title": "Test Property",
        "text": TEXT, "text_sha256": _sha(TEXT),
        "html": HTML, "html_sha256": _sha(HTML),
        "automation": {"policy": {"text_start": len(PREFIX),
                                  "text_end": len(PREFIX) + len(EXCERPT),
                                  "text_excerpt": EXCERPT, "confidence": "HIGH"}},
    }
    capture.write_text(json.dumps(payload), encoding="utf-8")
    shot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"pixels")
    view.write_text(json.dumps({"viewport_width": 1424, "viewport_height": 905}),
                    encoding="utf-8")
    payload["__capture_path__"] = str(capture)
    return _Bridged(payload, capture, shot, view).set_capture(capture)


def _extract(excerpt):
    from scripts.pettripfinder.promote_attested_candidates import extract_pet_facts
    return extract_pet_facts(excerpt)


def _build(bridged, tmp_path, **kw):
    opts = dict(bridge_result=bridged, identity=copy.deepcopy(IDENTITY),
                extractor=_extract, published_overlap=MR.OVERLAP_NONE,
                capture_commit="abc1234", created_at="2026-08-04T12:00:00Z",
                repo_root=tmp_path, brand="testbrand")
    opts.update(kw)
    return MR.build_machine_review(**opts)


# --------------------------------------------------------------------------- #
# 1-3. A successful capture becomes a PENDING_REVIEW record, with no failure.
# --------------------------------------------------------------------------- #

def test_a_valid_automated_capture_creates_a_pending_review_record(evidence, tmp_path):
    rec = _build(evidence, tmp_path)
    assert rec.schema == "ptf-machine-verified-capture-review/1.0"
    assert rec.status == MR.STATUS_PENDING_REVIEW
    assert rec.identity_outcome == "IDENTITY_CONFIRMED"
    assert rec.facts["pet_fee"] == "$100.00"
    assert rec.policy_offsets == {"text_start": len(PREFIX),
                                  "text_end": len(PREFIX) + len(EXCERPT)}
    assert rec.identity_authoritative_basis == ("structured_metadata",)
    assert rec.capture_sha256 and rec.screenshot_sha256 and rec.view_sha256
    assert rec.rendered_text_sha256 == _sha(TEXT)
    assert rec.html_sha256 == _sha(HTML)


def test_the_record_is_not_publishable(evidence, tmp_path):
    rec = _build(evidence, tmp_path)
    assert rec.publishable is False
    assert rec.to_dict()["publishable"] is False
    assert MR.is_publishable(rec.to_dict(), None) is False


def test_no_automated_failure_is_required_or_recorded(evidence, tmp_path):
    """The whole point: automation SUCCEEDED, so no failure is claimed."""
    body = json.dumps(_build(evidence, tmp_path).to_dict()).lower()
    assert "automated_failure" not in body
    assert "access_blocked" not in body and "render_required" not in body


# --------------------------------------------------------------------------- #
# 4-5. The two contracts stay apart.
# --------------------------------------------------------------------------- #

def test_no_first_person_operator_affirmation_is_generated(evidence, tmp_path):
    record = _build(evidence, tmp_path).to_dict()
    assert "affirmation" not in record and "operator_id" not in record
    assert "address_confirmed" not in record and "phone_confirmed" not in record
    body = json.dumps(record)
    assert "I personally opened" not in body


def test_the_reviewer_statement_disclaims_what_it_cannot_know():
    from services.research_workers.operator_capture import ATTESTATION_STATEMENT
    assert MR.MACHINE_REVIEW_STATEMENT != ATTESTATION_STATEMENT
    assert "I did not open the live page." in MR.MACHINE_REVIEW_STATEMENT
    assert "I do not claim any automated retrieval failed." in MR.MACHINE_REVIEW_STATEMENT
    assert "I observed nothing outside the preserved evidence." in MR.MACHINE_REVIEW_STATEMENT
    assert "personally opened" not in MR.MACHINE_REVIEW_STATEMENT


def test_the_operator_attestation_contract_is_untouched():
    """This module may not import, wrap or soften the human path.

    Checked over the parsed tree rather than the raw text: the module's own
    docstring names the attestation contract in order to explain why it is kept
    separate, and a string scan would flag that explanation as a violation.
    """
    import ast
    import services.research_workers.operator_capture as OC
    tree = ast.parse(pathlib.Path(MR.__file__).read_text(encoding="utf-8"))

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update("%s.%s" % (node.module or "", a.name) for a in node.names)
    assert not any("operator_capture" in name for name in imported), imported

    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for forbidden in ("build_attestation", "OperatorAffirmation", "AutomatedFailure",
                      "approve_attestation"):
        assert forbidden not in used
    # And the human gates still bite exactly as before.
    assert OC.CAPTURE_WORTHY == frozenset(
        {"ACCESS_BLOCKED", "BROWSER_ACCESS_BLOCKED", "PROPERTY_PAGE_NOT_FOUND",
         "RENDER_REQUIRED"})
    with pytest.raises(OC.AttestationError):
        OC.build_attestation(
            ingestion=None, job=None,
            affirmation=OC.OperatorAffirmation(operator_id="x", attested_at="t"),
            automated_failure=OC.AutomatedFailure(status=""), screenshots=(),
            observed_at="t", observed_timezone="UTC")


# --------------------------------------------------------------------------- #
# 6. Identity and evidence gates.
# --------------------------------------------------------------------------- #

def test_an_unconfirmed_identity_is_refused(evidence, tmp_path):
    ident = copy.deepcopy(IDENTITY)
    ident["outcome"] = "IDENTITY_UNVERIFIABLE"
    with pytest.raises(MR.MachineReviewError, match="identity_not_confirmed"):
        _build(evidence, tmp_path, identity=ident)


def test_a_single_identity_group_is_refused(evidence, tmp_path):
    evidence.identity_key_groups = ("address",)
    with pytest.raises(MR.MachineReviewError, match="insufficient_identity_groups"):
        _build(evidence, tmp_path)


def test_no_authoritative_basis_is_refused(evidence, tmp_path):
    ident = copy.deepcopy(IDENTITY)
    for k in ident["keys"]["keys"]:
        k["authoritative"] = False
    with pytest.raises(MR.MachineReviewError, match="no_authoritative_identity_basis"):
        _build(evidence, tmp_path, identity=ident)


@pytest.mark.parametrize("field, expected", [
    ("text_sha256", "rendered_text_hash_mismatch"),
    ("html_sha256", "html_hash_mismatch"),
])
def test_a_hash_mismatch_is_refused(evidence, tmp_path, field, expected):
    evidence.payload[field] = "0" * 64
    with pytest.raises(MR.MachineReviewError, match=expected):
        _build(evidence, tmp_path)


def test_a_final_url_mismatch_is_refused(evidence, tmp_path):
    evidence.payload["final_url"] = "https://www.somewhere-else.com/other/"
    with pytest.raises(MR.MachineReviewError, match="final_url_mismatch"):
        _build(evidence, tmp_path)


@pytest.mark.parametrize("attr, expected", [
    ("screenshot_path", "missing_screenshot_artifact"),
    ("view_path", "missing_view_metadata_artifact"),
])
def test_a_missing_artifact_is_refused(evidence, tmp_path, attr, expected):
    pathlib.Path(getattr(evidence, attr)).unlink()
    with pytest.raises(MR.MachineReviewError, match=expected):
        _build(evidence, tmp_path)


def test_offsets_that_do_not_frame_the_excerpt_are_refused(evidence, tmp_path):
    evidence.payload["automation"]["policy"]["text_start"] = 0
    evidence.payload["automation"]["policy"]["text_end"] = 12
    with pytest.raises(MR.MachineReviewError,
                       match="policy_offsets_do_not_frame_excerpt"):
        _build(evidence, tmp_path)


def test_a_missing_capture_commit_is_refused(evidence, tmp_path):
    with pytest.raises(MR.MachineReviewError, match="missing_capture_commit"):
        _build(evidence, tmp_path, capture_commit="  ")


# --------------------------------------------------------------------------- #
# 7-9. Contradictions, refusals, duplicates.
# --------------------------------------------------------------------------- #

def test_contradictory_facts_are_refused(evidence, tmp_path):
    """A source that contradicts itself is not a clean extraction."""
    def contradicting(_excerpt):
        return ({"pets_allowed": "true",
                 "fee_conflict": {"reason": "conflicting_fee_terms_in_official_source"}},
                [{"field": "fee_conflict", "value": "withheld", "quote": "q"}], "b")
    with pytest.raises(MR.MachineReviewError, match="contradictory_facts_present"):
        _build(evidence, tmp_path, extractor=contradicting)


def test_an_extraction_refusal_is_refused(evidence, tmp_path):
    from scripts.pettripfinder.promote_attested_candidates import PromotionError
    def refusing(_excerpt):
        raise PromotionError("no_labelled_pet_policy_block_found")
    with pytest.raises(MR.MachineReviewError, match="extraction_refused"):
        _build(evidence, tmp_path, extractor=refusing)


def test_an_unreproducible_extraction_is_refused(evidence, tmp_path):
    calls = []
    def flaky(excerpt):
        calls.append(1)
        return ({"pets_allowed": "true", "pet_fee": "$%d" % len(calls)}, [], "b")
    with pytest.raises(MR.MachineReviewError, match="extraction_not_reproducible"):
        _build(evidence, tmp_path, extractor=flaky)


def test_a_duplicate_normalized_url_is_refused(evidence, tmp_path):
    seen = set()
    _build(evidence, tmp_path, seen_urls=seen)
    with pytest.raises(MR.MachineReviewError, match="duplicate_normalized_url"):
        _build(evidence, tmp_path, seen_urls=seen)


def test_a_pets_not_allowed_capture_is_refused_by_this_workflow(evidence, tmp_path):
    """Routing a refusal here would publish "pets welcome" for a hotel that
    refuses them."""
    refusal = "Pet Policy Pets Not Allowed"
    text = PREFIX + refusal + SUFFIX
    evidence.payload["text"] = text
    evidence.payload["text_sha256"] = _sha(text)
    evidence.payload["automation"]["policy"]["text_start"] = len(PREFIX)
    evidence.payload["automation"]["policy"]["text_end"] = len(PREFIX) + len(refusal)
    evidence.policy_excerpt = refusal
    with pytest.raises(MR.MachineReviewError,
                       match="pets_not_allowed_record_in_positive_workflow"):
        _build(evidence, tmp_path)


# --------------------------------------------------------------------------- #
# 10-12. Overlap, determinism, idempotency.
# --------------------------------------------------------------------------- #

def test_a_published_overlap_stays_compare_only(evidence, tmp_path):
    rec = _build(evidence, tmp_path, published_overlap=MR.OVERLAP_COMPARE_ONLY)
    assert rec.published_overlap == "COMPARE_ONLY"
    assert rec.publishable is False


def test_an_unknown_overlap_value_is_refused(evidence, tmp_path):
    with pytest.raises(MR.MachineReviewError, match="unsupported_published_overlap"):
        _build(evidence, tmp_path, published_overlap="OVERWRITE")


def test_deterministic_replay_produces_the_same_record_hash(evidence, tmp_path):
    """Rebuilding at a different moment must not change the hash, or staleness
    could never be told apart from a rebuild."""
    a = _build(evidence, tmp_path, created_at="2026-08-04T12:00:00Z")
    b = _build(evidence, tmp_path, created_at="2026-08-09T23:59:59Z")
    assert a.record_hash() == b.record_hash()
    assert a.created_at != b.created_at


def test_an_idempotent_rerun_creates_no_duplicate(evidence, tmp_path):
    out = tmp_path / "records"
    rec = _build(evidence, tmp_path)
    MR.write_records([rec], out)
    first = (out / ("%s.json" % rec.hotel_id)).read_text(encoding="utf-8")
    MR.write_records([_build(evidence, tmp_path)], out)
    assert len(list(out.glob("*.json"))) == 1
    assert (out / ("%s.json" % rec.hotel_id)).read_text(encoding="utf-8") == first


# --------------------------------------------------------------------------- #
# 13. Review is a separate, authorized act.
# --------------------------------------------------------------------------- #

def test_record_creation_produces_no_review(evidence, tmp_path):
    record = _build(evidence, tmp_path).to_dict()
    assert "reviewer_id" not in record and "decision" not in record
    assert "approval_hash" not in record


def test_a_review_binds_a_named_reviewer_to_this_record(evidence, tmp_path):
    rec = _build(evidence, tmp_path)
    review = MR.record_review(rec, reviewer_id="reviewer1",
                              reviewed_at="2026-08-04T13:00:00Z",
                              decision=MR.DECISION_APPROVED,
                              field_decisions={"pet_fee": "APPROVED"},
                              notes="fee legible in screenshot")
    assert review.source_record_hash == rec.record_hash()
    assert review.approval_hash().startswith("sha256:")
    assert review.approved_fields == ("pet_fee",)
    assert review.statement == MR.MACHINE_REVIEW_STATEMENT


@pytest.mark.parametrize("kw, expected", [
    ({"reviewer_id": " "}, "reviewer_id is required"),
    ({"reviewed_at": ""}, "reviewed_at is required"),
    ({"decision": "MAYBE"}, "APPROVED or REJECTED"),
    ({"statement": "I personally opened this URL."}, "may not be altered"),
    ({"field_decisions": {"pet_fee": "PROBABLY"}}, "has verdict"),
])
def test_an_invalid_review_is_refused(evidence, tmp_path, kw, expected):
    rec = _build(evidence, tmp_path)
    opts = dict(reviewer_id="reviewer1", reviewed_at="2026-08-04T13:00:00Z",
                decision=MR.DECISION_APPROVED)
    opts.update(kw)
    with pytest.raises(MR.MachineReviewError, match=expected):
        MR.record_review(rec, **opts)


# --------------------------------------------------------------------------- #
# 14-15. Promotion safety.
# --------------------------------------------------------------------------- #

def test_promotion_refuses_a_pending_review_record(evidence, tmp_path):
    record = _build(evidence, tmp_path).to_dict()
    with pytest.raises(MR.MachineReviewError, match="no_review_record"):
        MR.promotion_input(record, None)


def test_promotion_refuses_a_rejected_review(evidence, tmp_path):
    rec = _build(evidence, tmp_path)
    review = MR.record_review(rec, reviewer_id="r", reviewed_at="t",
                              decision=MR.DECISION_REJECTED)
    with pytest.raises(MR.MachineReviewError, match="decision=REJECTED"):
        MR.promotion_input(rec.to_dict(), review.to_dict())
    assert MR.is_publishable(rec.to_dict(), review.to_dict()) is False


def test_promotion_refuses_stale_or_mismatched_source_hashes(evidence, tmp_path):
    """Evidence edited after approval must invalidate the approval."""
    rec = _build(evidence, tmp_path)
    review = MR.record_review(rec, reviewer_id="r", reviewed_at="t",
                              decision=MR.DECISION_APPROVED).to_dict()
    tampered = rec.to_dict()
    tampered["facts"] = dict(tampered["facts"], pet_fee="$5.00")
    with pytest.raises(MR.MachineReviewError, match="stale_or_mismatched_source_hash"):
        MR.promotion_input(tampered, review)
    assert MR.is_publishable(tampered, review) is False


def test_an_approved_review_on_unchanged_evidence_may_promote(evidence, tmp_path):
    rec = _build(evidence, tmp_path)
    review = MR.record_review(rec, reviewer_id="r", reviewed_at="t",
                              decision=MR.DECISION_APPROVED).to_dict()
    out = MR.promotion_input(rec.to_dict(), review)
    assert out["facts"]["pet_fee"] == "$100.00"
    assert out["approval_hash"] == review["approval_hash"]
    assert MR.is_publishable(rec.to_dict(), review) is True


def test_a_rejected_field_is_withheld_from_promotion(evidence, tmp_path):
    rec = _build(evidence, tmp_path)
    review = MR.record_review(rec, reviewer_id="r", reviewed_at="t",
                              decision=MR.DECISION_APPROVED,
                              field_decisions={"pet_fee": "REJECTED"}).to_dict()
    out = MR.promotion_input(rec.to_dict(), review)
    assert "pet_fee" not in out["facts"]
    assert out["withheld_fields"] == ["pet_fee"]


def test_a_published_overlap_needs_its_own_approval_before_promotion(evidence, tmp_path):
    """No automatic overwrite of an existing published fact."""
    rec = _build(evidence, tmp_path, published_overlap=MR.OVERLAP_COMPARE_ONLY)
    plain = MR.record_review(rec, reviewer_id="r", reviewed_at="t",
                             decision=MR.DECISION_APPROVED).to_dict()
    with pytest.raises(MR.MachineReviewError,
                       match="published_overlap_not_specifically_approved"):
        MR.promotion_input(rec.to_dict(), plain)
    explicit = MR.record_review(rec, reviewer_id="r", reviewed_at="t",
                                decision=MR.DECISION_APPROVED,
                                overlap_approved=True).to_dict()
    assert MR.promotion_input(rec.to_dict(), explicit)["published_overlap"] == "COMPARE_ONLY"


# --------------------------------------------------------------------------- #
# 16. Nothing published moves.
# --------------------------------------------------------------------------- #

def test_no_production_inventory_or_site_data_is_touched(evidence, tmp_path):
    repo = pathlib.Path(__file__).resolve().parents[2]
    package = repo / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"
    before = package.read_bytes()
    rec = _build(evidence, tmp_path)
    MR.write_records([rec], tmp_path / "records")
    review = MR.record_review(rec, reviewer_id="r", reviewed_at="t",
                              decision=MR.DECISION_APPROVED).to_dict()
    MR.promotion_input(rec.to_dict(), review)
    assert package.read_bytes() == before
    assert len(json.loads(before)["hotels"]) == 80
    source = pathlib.Path(MR.__file__).read_text(encoding="utf-8")
    for forbidden in ("hotel_policy_facts", "assemble_netlify", "netlify deploy",
                      "site/"):
        assert forbidden not in source

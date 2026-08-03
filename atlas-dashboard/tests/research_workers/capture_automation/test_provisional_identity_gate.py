"""PTF-DISCOVERY-001 C-4..C-7 -- provisional capture state through attestation.

The through-line these tests protect: a candidate whose identity was never
established statically may be OPENED in a rendered capture session, because the
static fetcher cannot reach the major chains (reval-001: 5 robots denials, 2
HTTP 403s, 1 of 15 pages carrying JSON-LD). It may not be treated as ready,
verified or publishable on the strength of having been opened.

Each layer enforces one part of that, and each is asserted separately:

  C-4  the queue can express "provisional", and an unknown state fails closed
  C-5  the seam emits it only when identity was never CHECKED -- never when
       identity was checked and FAILED, which FD-5 still blocks outright
  C-6  a capture needs identity evidence AND policy evidence, symmetrically
  C-7  the attestation carries the identity citation, and refuses an operator
       affirmation the capture did not visibly prove
"""

from __future__ import annotations

import dataclasses
import pathlib

import pytest

from services.research_workers.capture_automation import identity_keys as IK
from services.research_workers.capture_automation import queue as Q
from services.research_workers.capture_automation.evidence_completeness import (
    EvidenceIncompleteError, EvidenceView, FieldObservation, REQUIRED_FIELDS,
    assess_evidence, identity_problems, require_complete_capture,
)

from .conftest import make_png

URL = "https://www.marriott.com/en-us/hotels/cmham-columbus-airport-marriott/overview/"


def raw_entry(**overrides):
    base = {
        "hotel_id": "h1", "listing_key": "k1", "hotel_name": "Columbus Airport Marriott",
        "brand": "marriott", "official_url": URL,
        "expected_address": "1375 North Cassady Avenue", "expected_city": "Columbus",
        "expected_state": "OH", "expected_phone": "614-475-7551",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# C-4 -- provisional capture state.
# --------------------------------------------------------------------------- #

class TestC4CaptureState:
    def test_the_default_is_the_historical_ordinary_work_entry(self):
        entry, problems = Q.validate_entry(raw_entry(), 0)
        assert problems == []
        assert entry.capture_state == Q.CAPTURE_STATE_READY == ""
        assert not Q.is_provisional(entry)

    def test_a_provisional_entry_is_accepted_and_marked(self):
        entry, problems = Q.validate_entry(
            raw_entry(capture_state=Q.CAPTURE_STATE_PENDING_IDENTITY), 0)
        assert problems == []
        assert Q.is_provisional(entry)

    def test_an_unknown_capture_state_fails_closed(self):
        """REQUIRED TEST 8. Tolerating an unknown value would let a mistyped or
        future state be read as the ordinary work-entry default."""
        entry, problems = Q.validate_entry(raw_entry(capture_state="TOTALLY_MADE_UP"), 0)
        assert entry is None
        assert any("unknown_capture_state:TOTALLY_MADE_UP" in p for p in problems)

    @pytest.mark.parametrize("bogus", ["pending_capture_identity", "READY", "0", "None"])
    def test_near_misses_also_fail_closed(self, bogus):
        entry, _ = Q.validate_entry(raw_entry(capture_state=bogus), 0)
        assert entry is None

    def test_a_provisional_entry_may_not_request_policy_fields(self):
        """The structural separation: required_fields is the list of policy
        fields the worker is asked to look for. A provisional entry asks for
        none of them, so it cannot be mistaken for ready work."""
        entry, problems = Q.validate_entry(raw_entry(
            capture_state=Q.CAPTURE_STATE_PENDING_IDENTITY,
            required_fields=["pets_allowed"]), 0)
        assert entry is None
        assert any("provisional_entry_must_not_request_policy_fields" in p
                   for p in problems)

    def test_an_ordinary_entry_may_still_request_policy_fields(self):
        entry, problems = Q.validate_entry(
            raw_entry(required_fields=["pets_allowed", "pet_fee"]), 0)
        assert problems == []
        assert entry.required_fields == ("pets_allowed", "pet_fee")

    def test_required_hotel_fields_is_still_nine(self):
        assert len(Q._REQUIRED_HOTEL_FIELDS) == 9

    def test_capture_state_round_trips_through_to_dict(self):
        entry, _ = Q.validate_entry(
            raw_entry(capture_state=Q.CAPTURE_STATE_PENDING_IDENTITY), 0)
        assert entry.to_dict()["capture_state"] == Q.CAPTURE_STATE_PENDING_IDENTITY


class TestC4BackwardCompatibility:
    def test_a_10_queue_without_capture_state_still_loads(self, tmp_path):
        """REQUIRED TEST 6. A file written before this field existed must load
        with exactly its old meaning."""
        import json

        path = tmp_path / "q.json"
        path.write_text(json.dumps({
            "schema": "ptf-capture-queue/1.0", "batch_id": "legacy",
            "hotels": [raw_entry()],
        }), encoding="utf-8")
        queue = Q.load_queue(path)
        assert queue.schema == "ptf-capture-queue/1.0"
        assert queue.entries[0].capture_state == Q.CAPTURE_STATE_READY
        assert not Q.is_provisional(queue.entries[0])

    def test_every_archived_production_queue_still_loads(self):
        """The real files, not a fixture written to agree with the code."""
        import json

        root = pathlib.Path("data/worker_runs/pettripfinder")
        if not root.exists():
            pytest.skip("no archived queues in this checkout")
        found = 0
        for path in sorted(root.rglob("*.json")):
            try:
                blob = json.loads(path.read_text("utf-8"))
            except (ValueError, UnicodeDecodeError, OSError):
                continue
            if not (isinstance(blob, dict)
                    and blob.get("schema") in Q.SUPPORTED_QUEUE_SCHEMAS):
                continue
            found += 1
            Q.load_queue(path)          # raises QueueError if it regressed
        if not found:
            pytest.skip("no archived queue files found")

    def test_the_membrane_still_refuses_a_policy_field_on_the_entry(self):
        from scripts.pettripfinder.discovery.membrane import MembraneViolation

        with pytest.raises(MembraneViolation):
            Q.assert_no_policy_keys({"pets_allowed": True}, context="t",
                                    denylist=Q.POLICY_FIELD_DENYLIST)


# --------------------------------------------------------------------------- #
# C-5 -- PROJECTED_PENDING_IDENTITY at the seam.
# --------------------------------------------------------------------------- #

def _record(**kw):
    """Same shape the existing seam tests use, so this exercises the real
    models rather than a locally-invented approximation."""
    from scripts.pettripfinder.discovery import constants as C
    from scripts.pettripfinder.discovery.models import DiscoveryRecord

    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="gp1",
                canonical_category=C.CATEGORY_HOTEL, name="Columbus Airport Marriott",
                normalized_name="columbus airport marriott",
                address_line="1375 North Cassady Avenue", city="Columbus", state="OH",
                postal_code="43219", phone="614-475-7551", website_url=URL,
                observed_at="2026-08-03", source_query_id="q1")
    base.update(kw)
    return DiscoveryRecord(**base)


def _candidate(**kw):
    from scripts.pettripfinder.discovery import constants as C
    from scripts.pettripfinder.discovery.models import DiscoveryCandidate

    r = kw.pop("record", None) or _record()
    base = dict(candidate_id="dc_marriott0001", source_records=(r,),
                name=r.name, normalized_name=r.normalized_name,
                address_line=r.address_line, city=r.city, state=r.state,
                postal_code=r.postal_code, website_url=r.website_url,
                provider_ids=((r.provider, r.provider_record_id),),
                market_id="columbus-oh", review_state=C.REVIEW_STATE_SINGLE_SOURCE)
    base.update(kw)
    return DiscoveryCandidate(**base)


def _project(candidate=None, **kwargs):
    from scripts.pettripfinder.discovery import constants as C
    from scripts.pettripfinder.discovery import queue_seam as QS

    params = dict(
        resolution_outcome=C.RESOLUTION_READY_FOR_PET_POLICY_IMPORT,
        resolved_url=URL, run_context_ref="run-1")
    params.update(kwargs)
    return QS.project_candidate(candidate or _candidate(), **params)


class TestC5ProjectedPendingIdentity:
    def test_a_confirmed_candidate_still_projects_as_ordinary_work(self):
        from scripts.pettripfinder.discovery import queue_seam as QS

        result = _project(url_confirmed=True)
        assert result.outcome == QS.PROJECTED
        assert result.entry.capture_state == Q.CAPTURE_STATE_READY
        assert result.entry.required_fields, "ready work asks for policy fields"

    def test_never_validated_identity_projects_as_provisional(self):
        from scripts.pettripfinder.discovery import queue_seam as QS

        result = _project(url_revalidation_blocked=True,
                          url_identity_never_validated=True,
                          revalidation_reason="NEVER_VALIDATED")
        assert result.outcome == QS.PROJECTED_PENDING_IDENTITY
        assert result.entry.capture_state == Q.CAPTURE_STATE_PENDING_IDENTITY
        assert result.entry.required_fields == (), "provisional asks for no policy"
        assert "identity_unconfirmed_pending_capture" in result.entry.priority_reasons

    def test_a_failed_identity_check_is_still_blocked_outright(self):
        """FD-5 is NOT weakened. A URL that resolved to a DIFFERENT property
        never becomes an entry, provisional or otherwise."""
        from scripts.pettripfinder.discovery import queue_seam as QS

        result = _project(url_revalidation_blocked=True,
                          revalidation_reason="property_identity_check_failed")
        assert result.outcome == QS.SKIPPED_URL_REVALIDATION
        assert result.entry is None

    def test_an_unsupported_brand_stays_on_the_exception_path(self):
        from scripts.pettripfinder.discovery import queue_seam as QS

        result = _project(resolved_url="https://www.some-independent-inn.com/rooms",
                          url_revalidation_blocked=True,
                          url_identity_never_validated=True)
        assert result.outcome == QS.SKIPPED_UNSUPPORTED_BRAND
        assert result.entry is None

    def test_an_ineligible_resolution_never_becomes_provisional(self):
        from scripts.pettripfinder.discovery import queue_seam as QS

        result = _project(resolution_outcome="REVIEW_IDENTITY",
                          url_revalidation_blocked=True,
                          url_identity_never_validated=True)
        assert result.outcome == QS.SKIPPED_NOT_READY

    def test_repeated_emission_does_not_duplicate_the_entry(self):
        """REQUIRED TEST 5. The idempotency key (candidate_id,
        worker_contract_version) must reproduce the same queue_entry_id, so a
        re-run supersedes in place rather than appending a second entry."""
        from scripts.pettripfinder.discovery import queue_seam as QS

        first = _project(url_revalidation_blocked=True, url_identity_never_validated=True)
        second = _project(url_revalidation_blocked=True, url_identity_never_validated=True)
        assert first.entry.queue_entry_id == second.entry.queue_entry_id
        assert first.entry.hotel_id == second.entry.hotel_id

        payload = QS.build_queue_payload([first, second], batch_id="b1")
        ids = [h["queue_entry_id"] for h in payload["hotels"]]
        assert len(set(ids)) == 1, "the same candidate must not appear twice"

    def test_a_contract_bump_yields_a_legitimately_new_entry_id(self):
        """A new contract version is NOT a duplicate -- it is work that has not
        been verified under the current contract, so it gets its own entry."""
        first = _project(url_revalidation_blocked=True, url_identity_never_validated=True)
        older = _project(url_revalidation_blocked=True, url_identity_never_validated=True,
                         worker_contract_version="1.0.0")
        assert first.entry.worker_contract_version != older.entry.worker_contract_version
        assert first.entry.queue_entry_id != older.entry.queue_entry_id

    def test_a_projected_payload_loads_through_the_real_preflight(self, tmp_path):
        import json

        from scripts.pettripfinder.discovery import queue_seam as QS

        payload = QS.build_queue_payload(
            [_project(url_revalidation_blocked=True, url_identity_never_validated=True)], batch_id="b1")
        path = tmp_path / "q.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        queue = Q.load_queue(path, known_brands=("marriott",))
        assert Q.is_provisional(queue.entries[0])

    def test_ready_entries_sort_before_provisional_ones(self):
        from scripts.pettripfinder.discovery import queue_seam as QS

        ready = _project(url_confirmed=True)
        # A genuinely DIFFERENT property, or the two would share an idempotency
        # key and be collapsed into one entry (which is its own correct rule).
        other = _candidate(candidate_id="dc_marriott0002",
                           name="Columbus Airport Marriott West",
                           normalized_name="columbus airport marriott west")
        pending = _project(other, url_revalidation_blocked=True,
                           url_identity_never_validated=True,
                           resolved_url=URL.replace("cmham", "cmhaw"))
        payload = QS.build_queue_payload([pending, ready], batch_id="b1")
        states = [h["capture_state"] for h in payload["hotels"]]
        assert states == [Q.CAPTURE_STATE_READY, Q.CAPTURE_STATE_PENDING_IDENTITY]

    def test_a_provisional_entry_cannot_publish(self):
        """REQUIRED TEST 1. Publication requires an approved attestation, and an
        attestation requires policy statements. A provisional entry requests no
        policy fields at all, so there is nothing it could publish -- asserted
        structurally rather than by inspection."""
        result = _project(url_revalidation_blocked=True, url_identity_never_validated=True)
        entry = result.entry
        assert entry.required_fields == ()
        assert Q.is_provisional(entry)
        # And it is not silently equal to a ready entry anywhere it matters.
        assert entry.capture_state not in (Q.CAPTURE_STATE_READY,)
        assert entry.capture_state in Q.PROVISIONAL_CAPTURE_STATES


# --------------------------------------------------------------------------- #
# C-6 -- identity evidence AND policy evidence.
# --------------------------------------------------------------------------- #

def _confirmed_identity(groups=("address", "phone"), authoritative=True):
    return {
        "outcome": IK.IDENTITY_CONFIRMED,
        "reason": "2 independent stable keys",
        "may_proceed": True,
        "keys": {
            "outcome": IK.IDENTITY_CONFIRMED,
            "independent_groups": list(groups),
            "has_authoritative_key": authoritative,
            "keys": [
                {"key": "normalized_street_address", "basis": "structured_metadata",
                 "group": "address", "counts": True, "authoritative": authoritative},
                {"key": "property_phone", "basis": "structured_metadata",
                 "group": "phone", "counts": True, "authoritative": authoritative},
            ],
        },
    }


def _view(tmp_path, fields, *, official_url=URL):
    png = tmp_path / "v.png"
    data = make_png(320, 200)
    png.write_bytes(data)
    import hashlib

    return EvidenceView(
        png_path=str(png), png_sha256=hashlib.sha256(data).hexdigest(),
        png_bytes=len(data), png_width=320, png_height=200,
        page_url=official_url, captured_at="2026-08-03T10:00:00Z",
        observations=tuple(
            FieldObservation(field=f, text=t, visible=True, in_frame=True,
                             box={"width": 100, "height": 20})
            for f, t in fields.items()))


ALL_FIELDS = {
    "hotel_name": "Columbus Airport Marriott",
    "street_address": "1375 North Cassady Avenue",
    "city": "Columbus", "state": "OH", "postal_code": "43219",
    "property_phone": "614-475-7551",
    "pet_policy_text": "Pets are welcome. A fee applies.",
}
EXPECTED = {"hotel_name": "Columbus Airport Marriott",
            "street_address": "1375 North Cassady Avenue", "city": "Columbus",
            "state": "OH", "postal_code": "43219", "property_phone": "614-475-7551"}


class TestC6EvidenceCompleteness:
    def test_identity_and_policy_together_are_complete(self, tmp_path):
        report = assess_evidence([_view(tmp_path, ALL_FIELDS)], official_url=URL,
                                 expected=EXPECTED, identity=_confirmed_identity())
        assert report.complete, report.summary_line()
        assert report.held_reasons == ()

    def test_confirmed_identity_with_missing_policy_evidence_fails_closed(self, tmp_path):
        """REQUIRED TEST 2. Identity confirmation alone is insufficient."""
        fields = {k: v for k, v in ALL_FIELDS.items() if k != "pet_policy_text"}
        report = assess_evidence([_view(tmp_path, fields)], official_url=URL,
                                 expected=EXPECTED, identity=_confirmed_identity())
        assert not report.complete
        assert report.missing_policy_evidence == ("pet_policy_text",)
        assert "policy_field_not_proven:pet_policy_text" in report.held_reasons

    def test_policy_evidence_with_incomplete_identity_fails_closed(self, tmp_path):
        """REQUIRED TEST 3. Policy evidence alone is insufficient."""
        incomplete = dict(_confirmed_identity())
        incomplete["outcome"] = IK.IDENTITY_INCOMPLETE
        report = assess_evidence([_view(tmp_path, ALL_FIELDS)], official_url=URL,
                                 expected=EXPECTED, identity=incomplete)
        assert not report.complete
        assert any("identity_outcome_not_confirmed" in r for r in report.held_reasons)

    def test_a_missing_identity_record_fails_closed_under_the_strict_gate(self, tmp_path):
        with pytest.raises(EvidenceIncompleteError) as exc:
            require_complete_capture([_view(tmp_path, ALL_FIELDS)], official_url=URL,
                                     expected=EXPECTED, identity=None)
        assert "identity_evidence_missing" in exc.value.report.identity_issues

    def test_one_independent_key_is_not_enough(self, tmp_path):
        report = assess_evidence([_view(tmp_path, ALL_FIELDS)], official_url=URL,
                                 expected=EXPECTED,
                                 identity=_confirmed_identity(groups=("address",)))
        assert not report.complete
        assert any("below_minimum" in r for r in report.identity_issues)

    def test_no_authoritative_basis_is_not_enough(self, tmp_path):
        report = assess_evidence([_view(tmp_path, ALL_FIELDS)], official_url=URL,
                                 expected=EXPECTED,
                                 identity=_confirmed_identity(authoritative=False))
        assert not report.complete
        assert "identity_no_authoritative_evidence_basis" in report.identity_issues

    def test_omitting_identity_preserves_the_historical_behaviour(self, tmp_path):
        """Captures taken before the gate existed are assessed as they always
        were -- the check is skipped, not silently failed."""
        report = assess_evidence([_view(tmp_path, ALL_FIELDS)], official_url=URL,
                                 expected=EXPECTED)
        assert report.complete
        assert report.identity_issues == ()

    def test_every_held_package_names_its_reasons(self, tmp_path):
        report = assess_evidence([], official_url=URL, expected=EXPECTED,
                                 identity=None)
        assert not report.complete
        assert report.held_reasons, "a held package must always say why"

    @pytest.mark.parametrize("record,want", [
        (None, "identity_evidence_missing"),
        ({}, "identity_outcome_not_confirmed:none"),
        ({"outcome": "ACCESS_BLOCKED"}, "identity_outcome_not_confirmed:ACCESS_BLOCKED"),
        ({"outcome": IK.IDENTITY_CONFIRMED}, "identity_key_evidence_missing"),
    ])
    def test_identity_problems_names_each_failure(self, record, want):
        assert want in identity_problems(record)

    def test_the_required_field_set_is_unchanged(self):
        assert len(REQUIRED_FIELDS) == 7


# --------------------------------------------------------------------------- #
# C-7 -- the attestation carries the identity basis.
# --------------------------------------------------------------------------- #

def _basis(**overrides):
    from services.research_workers.operator_capture import CaptureIdentityBasis

    base = dict(
        identity_outcome="IDENTITY_CONFIRMED",
        independent_key_groups=("address", "phone"),
        authoritative_bases=("structured_metadata",),
        agreeing_keys=("normalized_street_address@structured_metadata",
                       "property_phone@structured_metadata"),
        capture_url=URL, capture_text_hash="a" * 64,
        capture_session_id="batch-001")
    base.update(overrides)
    return CaptureIdentityBasis(**base)


class TestC7AttestationIdentityBasis:
    def test_it_is_built_from_the_runner_identity_record(self):
        from services.research_workers.operator_capture import CaptureIdentityBasis

        basis = CaptureIdentityBasis.from_capture_record(
            _confirmed_identity(), capture_url=URL, capture_text_hash="b" * 64,
            capture_session_id="s1")
        assert basis.confirmed
        assert set(basis.independent_key_groups) == {"address", "phone"}
        assert basis.authoritative_bases == ("structured_metadata",)
        assert "property_phone@structured_metadata" in basis.agreeing_keys
        assert basis.capture_url == URL and basis.capture_session_id == "s1"

    def test_it_preserves_all_five_required_facets(self):
        d = _basis().to_dict()
        for key in ("identity_outcome", "independent_key_groups",
                    "authoritative_bases", "agreeing_keys", "capture_url",
                    "capture_text_hash", "capture_session_id"):
            assert key in d

    def test_non_counting_keys_are_not_recorded_as_agreeing(self):
        from services.research_workers.operator_capture import CaptureIdentityBasis

        record = _confirmed_identity()
        record["keys"]["keys"].append(
            {"key": "official_property_id", "basis": "page_title",
             "group": "property_identifier", "counts": False, "authoritative": False})
        basis = CaptureIdentityBasis.from_capture_record(record)
        assert not any("page_title" in k for k in basis.agreeing_keys)


class TestC7GateRefusesUnprovenAffirmations:
    """These drive ``build_attestation`` through its real gates."""

    def test_an_unconfirmed_basis_is_refused(self):
        from services.research_workers.operator_capture import AttestationError

        with pytest.raises(AttestationError, match="gateI"):
            _build_attestation_with(_basis(identity_outcome="IDENTITY_INCOMPLETE"))

    def test_one_independent_key_is_refused(self):
        from services.research_workers.operator_capture import AttestationError

        with pytest.raises(AttestationError, match="independent stable key"):
            _build_attestation_with(_basis(independent_key_groups=("address",)))

    def test_no_authoritative_basis_is_refused(self):
        from services.research_workers.operator_capture import AttestationError

        with pytest.raises(AttestationError, match="authoritative"):
            _build_attestation_with(_basis(authoritative_bases=()))

    def test_an_unbound_basis_is_refused(self):
        from services.research_workers.operator_capture import AttestationError

        with pytest.raises(AttestationError, match="bound to the capture"):
            _build_attestation_with(_basis(capture_text_hash=""))

    def test_affirming_a_phone_the_capture_never_proved_is_refused(self):
        """THE C-7 requirement: an operator may not affirm an identity fact the
        capture did not visibly prove."""
        from services.research_workers.operator_capture import AttestationError

        with pytest.raises(AttestationError, match="phone_confirmed was affirmed"):
            _build_attestation_with(
                _basis(independent_key_groups=("address", "property_identifier")))

    def test_affirming_an_address_the_capture_never_proved_is_refused(self):
        from services.research_workers.operator_capture import AttestationError

        with pytest.raises(AttestationError, match="address_confirmed was affirmed"):
            _build_attestation_with(
                _basis(independent_key_groups=("phone", "property_identifier")))

    def test_a_fully_proven_basis_is_accepted_and_recorded(self):
        """REQUIRED TEST 4."""
        att = _build_attestation_with(_basis())
        content = att.attested_content()
        assert content["capture_identity"]["identity_outcome"] == "IDENTITY_CONFIRMED"
        assert content["capture_identity"]["independent_key_groups"] == ["address", "phone"]
        assert content["capture_identity"]["authoritative_bases"] == ["structured_metadata"]
        assert content["capture_identity"]["agreeing_keys"]
        assert content["capture_identity"]["capture_text_hash"] == "a" * 64

    def test_approval_is_still_required_to_publish(self):
        att = _build_attestation_with(_basis())
        assert not att.publishable, "a fresh attestation is always PENDING"
        assert att.approval.state != "APPROVED"


class TestC7HashStability:
    def test_omitting_the_basis_leaves_the_attested_content_byte_identical(self):
        """REQUIRED TEST 7. Every attestation written before C-7 must hash to
        exactly what it always did, or the 13 hash-bound approvals break."""
        without = _build_attestation_with(None)
        assert "capture_identity" not in without.attested_content()

    def test_supplying_a_basis_changes_the_hash_only_for_that_record(self):
        without = _build_attestation_with(None)
        with_basis = _build_attestation_with(_basis())
        assert without.attestation_hash() != with_basis.attestation_hash()
        assert "capture_identity" in with_basis.attested_content()

    def test_the_recorded_approvals_still_verify(self):
        """The real production records, re-verified against the live code."""
        import json

        from services.research_workers.operator_capture import verify_attestation_record

        root = pathlib.Path("data/worker_runs/pettripfinder")
        if not root.exists():
            pytest.skip("no worker artifacts in this checkout")
        checked = 0
        for path in sorted(root.rglob("*.json")):
            try:
                blob = json.loads(path.read_text("utf-8"))
            except (ValueError, UnicodeDecodeError, OSError):
                continue
            if not (isinstance(blob, dict)
                    and str(blob.get("schema", "")).startswith("ptf-official-attestation/")):
                continue
            checked += 1
            ok, why = verify_attestation_record(blob)
            assert ok, "%s no longer verifies: %s" % (path.name, why)
        if not checked:
            pytest.skip("no attestation records found")


# --------------------------------------------------------------------------- #
# Shared attestation builder -- the real gate chain, not an imitation.
# --------------------------------------------------------------------------- #

def _build_attestation_with(capture_identity, **affirmation_overrides):
    """Drive the REAL gate chain -- ingest_capture and all six existing gates,
    not a local imitation. Built from the same Staybridge fixture shape the
    existing attestation tests use."""
    from services.research_workers import operator_capture as OC

    official = "https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail"
    prose = ("Pets are welcome at Staybridge Suites Columbus-Dublin. "
             "Up to two friendly pups under 80 lbs are welcome. "
             "Pet fee per pet is $75 plus tax for 1-7 nights. ")
    html = ("<html><head><title>Staybridge Suites Columbus-Dublin</title></head>"
            "<body><h1>Staybridge Suites Columbus-Dublin</h1>"
            "<p>6095 Emerald Parkway, Dublin, OH 43016</p>"
            "<p>Phone: +1-614-734-9882</p><h2>Pet Policy</h2><p>%s</p><p>%s</p>"
            "</body></html>" % (prose, "Extra amenity copy. " * 40))

    job = OC.CaptureJob(
        assignment_id="attest-staybridge",
        listing_key="staybridge suites columbus dublin",
        listing_name="Staybridge Suites Columbus-Dublin",
        expected_address="6095 Emerald Parkway", expected_city="Dublin",
        expected_state="OH", expected_postal_code="43016",
        expected_phone="+1-614-734-9882", official_url=official,
        failure_reason="blocked_source", retrieval_status="ACCESS_BLOCKED")

    ingestion = OC.ingest_capture(
        dict(schema=OC.CAPTURE_SCHEMA, captured_at="2026-07-27T14:05:00-04:00",
             final_url=official, title="Staybridge Suites Columbus-Dublin",
             html=html, text="", extension_version="1.0.0"),
        job, observed_at="2026-07-27")

    affirmation_kw = dict(
        operator_id="jfields80", attested_at="2026-07-27T14:06:00-04:00",
        address_confirmed=True, address_observed="6095 Emerald Parkway",
        phone_confirmed=True, phone_observed="+1-614-734-9882")
    affirmation_kw.update(affirmation_overrides)

    class _Cas:
        def put_bytes(self, data: bytes) -> str:
            import hashlib
            return hashlib.sha256(data).hexdigest()

    return OC.build_attestation(
        ingestion=ingestion, job=job,
        affirmation=OC.OperatorAffirmation(**affirmation_kw),
        automated_failure=OC.AutomatedFailure(
            status="ACCESS_BLOCKED", reason="blocked_source",
            artifact_path="data/worker_runs/.../retr-staybridge.json"),
        screenshots=[OC.store_screenshot(_Cas(), b"\x89PNG fake shot",
                                         width=1440, height=900, note="p.png")],
        observed_at="2026-07-27T14:05:00-04:00",
        observed_timezone="America/New_York",
        capture_identity=capture_identity)

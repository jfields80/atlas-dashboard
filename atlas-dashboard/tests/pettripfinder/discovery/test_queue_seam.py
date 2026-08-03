"""WO-1A Steps 4 + 5 -- the discovery -> verification-queue seam, and the
additive queue schema that carries it.

The seam is the point the whole subsystem exists to reach: discovery stops at
VERIFICATION_QUEUED and hands the existing policy worker an entry it consumes
with zero change to the evidence, routing, approval or publication contracts.

The two properties that must never regress:

  * every projected entry passes the REAL ``validate_entry`` -- there is no
    looser definition of validity in the seam;
  * every 1.0 queue file still loads, because 1.1 adds only optional fields.
"""

from __future__ import annotations

import glob
import json
import pathlib

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.membrane import DISCOVERY_DENYLIST, MembraneViolation
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord
from scripts.pettripfinder.discovery.queue_seam import (
    PROJECTED,
    REJECTED_BY_PREFLIGHT,
    SKIPPED_NO_URL,
    SKIPPED_NOT_READY,
    SKIPPED_UNSUPPORTED_BRAND,
    SKIPPED_URL_REVALIDATION,
    build_queue_payload,
    project_candidate,
    queue_entry_id_for,
    summarize,
)
from services.research_workers import vocabulary as V
from services.research_workers.capture_automation.adapters import known_brands
from services.research_workers.capture_automation.queue import (
    QUEUE_SCHEMA, SUPPORTED_QUEUE_SCHEMAS, _REQUIRED_HOTEL_FIELDS,
    QueueError, load_queue,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

MARRIOTT_URL = ("https://www.marriott.com/en-us/hotels/"
                "cmham-columbus-airport-marriott/overview/")


def _record(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="gp1",
                canonical_category=C.CATEGORY_HOTEL, name="Columbus Airport Marriott",
                normalized_name="columbus airport marriott",
                address_line="1375 North Cassady Avenue", city="Columbus", state="OH",
                postal_code="43219", phone="614-475-7551", website_url=MARRIOTT_URL,
                observed_at="2026-08-02", source_query_id="q1")
    base.update(kw)
    return DiscoveryRecord(**base)


def _candidate(**kw):
    r = kw.pop("record", None) or _record()
    base = dict(candidate_id="dc_marriott0001", source_records=(r,),
                name=r.name, normalized_name=r.normalized_name,
                address_line=r.address_line, city=r.city, state=r.state,
                postal_code=r.postal_code, website_url=r.website_url,
                provider_ids=((r.provider, r.provider_record_id),),
                market_id="columbus-oh", review_state=C.REVIEW_STATE_SINGLE_SOURCE)
    base.update(kw)
    return DiscoveryCandidate(**base)


def _project(**kw):
    base = dict(resolution_outcome=C.RESOLUTION_READY_FOR_PET_POLICY_IMPORT,
                resolved_url=MARRIOTT_URL, url_confirmed=True,
                run_context_ref="run-columbus-001")
    base.update(kw)
    return project_candidate(_candidate(), **base)


# --------------------------------------------------------------------------- #
# Step 5 -- schema compatibility.
# --------------------------------------------------------------------------- #

class TestStep5SchemaCompatibility:
    def test_the_schema_moved_to_1_1(self):
        assert QUEUE_SCHEMA == "ptf-capture-queue/1.1"

    def test_both_versions_are_supported(self):
        assert SUPPORTED_QUEUE_SCHEMAS == {"ptf-capture-queue/1.0", "ptf-capture-queue/1.1"}

    def test_required_fields_are_still_exactly_nine(self):
        """The whole reason every 1.0 file still loads. If this ever grows,
        existing queues break -- rollback trigger R4."""
        assert len(_REQUIRED_HOTEL_FIELDS) == 9

    def test_a_1_0_file_still_loads(self, tmp_path):
        payload = {"schema": "ptf-capture-queue/1.0", "batch_id": "legacy",
                   "hotels": [{
                       "hotel_id": "h1", "listing_key": "k", "hotel_name": "H",
                       "brand": "marriott", "official_url": MARRIOTT_URL,
                       "expected_address": "1 Main St", "expected_city": "Columbus",
                       "expected_state": "OH", "expected_phone": "614-000-0000"}]}
        path = tmp_path / "q.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        queue = load_queue(path, known_brands=known_brands())
        assert len(queue) == 1
        assert queue.schema == "ptf-capture-queue/1.0"   # reported as authored

    def test_an_unknown_schema_is_still_refused(self, tmp_path):
        path = tmp_path / "q.json"
        path.write_text(json.dumps({"schema": "ptf-capture-queue/9.9",
                                    "batch_id": "b", "hotels": []}), encoding="utf-8")
        with pytest.raises(QueueError):
            load_queue(path, known_brands=known_brands())

    def test_new_fields_default_on_a_legacy_entry(self, tmp_path):
        payload = {"schema": "ptf-capture-queue/1.0", "batch_id": "legacy",
                   "hotels": [{
                       "hotel_id": "h1", "listing_key": "k", "hotel_name": "H",
                       "brand": "marriott", "official_url": MARRIOTT_URL,
                       "expected_address": "1 Main St", "expected_city": "Columbus",
                       "expected_state": "OH", "expected_phone": "614-000-0000"}]}
        path = tmp_path / "q.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        e = load_queue(path, known_brands=known_brands()).entries[0]
        assert (e.candidate_id, e.market_id, e.run_context_ref) == ("", "", "")
        assert e.queue_priority == 0 and e.priority_reasons == ()
        assert e.official_url_record is None

    @pytest.mark.parametrize("path", sorted(glob.glob(str(
        REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
        / "capture_batches" / "*queue*.json"))))
    def test_every_real_archived_queue_still_loads(self, path):
        """The backward-compatibility claim, against the real corpus.
        ``data/`` is gitignored so this is empty in a clean clone."""
        try:
            load_queue(path, known_brands=known_brands())
        except QueueError as exc:
            # Tolerated only for pre-existing operational reasons, never for a
            # schema or contract-version rejection.
            assert "unsupported queue schema" not in str(exc)
            assert "worker_contract_version" not in str(exc)


# --------------------------------------------------------------------------- #
# Step 4 -- projection.
# --------------------------------------------------------------------------- #

class TestStep4Projection:
    def test_a_ready_candidate_projects_and_passes_the_real_preflight(self):
        result = _project()
        assert result.outcome == PROJECTED, result.problems
        e = result.entry
        assert e.hotel_id == "columbus-airport-marriott"
        assert e.listing_key == "columbus airport marriott"
        assert e.brand == "marriott"
        assert e.official_url == MARRIOTT_URL
        assert e.candidate_id == "dc_marriott0001"
        assert e.market_id == "columbus-oh"
        assert e.supported_adapter == "marriott"
        assert e.worker_contract_version == V.CONTRACT_VERSION

    def test_identity_fields_are_borrowed_not_reinvented(self):
        """listing_key must match the function that keys the published launch
        package; a second normalizer here would silently fork identity."""
        from scripts.pettripfinder.site_data import normalize_name
        from scripts.pettripfinder.build_capture_queue import hotel_id_for

        e = _project().entry
        assert e.listing_key == normalize_name("Columbus Airport Marriott")
        assert e.hotel_id == hotel_id_for("Columbus Airport Marriott")

    def test_provenance_is_carried(self):
        e = _project().entry
        assert "provider:GOOGLE_PLACES:gp1" in e.discovery_provenance_refs
        assert "query:q1" in e.discovery_provenance_refs
        assert "run:run-columbus-001" in e.discovery_provenance_refs
        assert e.run_context_ref == "run-columbus-001"

    def test_required_fields_names_the_policy_fields_without_any_value(self):
        e = _project().entry
        assert e.required_fields == tuple(V.POLICY_FIELDS)
        assert "pet_fee" in e.required_fields          # a NAME
        assert not any(str(v).startswith("$") for v in e.to_dict().values()
                       if isinstance(v, str))

    def test_the_entry_declares_no_policy_field(self):
        e = _project().entry
        assert not (set(e.to_dict()) & DISCOVERY_DENYLIST)


class TestStep4RefusesWhatItShould:
    def test_an_ineligible_outcome_does_not_project(self):
        r = _project(resolution_outcome=C.RESOLUTION_REVIEW_IDENTITY)
        assert r.outcome == SKIPPED_NOT_READY
        assert r.entry is None

    def test_a_deferred_candidate_does_not_project(self):
        r = _project(resolution_outcome=C.RESOLUTION_DEFER)
        assert r.outcome == SKIPPED_NOT_READY

    def test_no_url_does_not_project(self):
        r = _project(resolved_url="")
        assert r.outcome == SKIPPED_NO_URL

    def test_an_unsupported_brand_goes_to_the_exception_path(self):
        """FD-8 ratified: unsupported brands never enter the auto-queue."""
        r = _project(resolved_url="https://www.someindependenthotel.test/rooms/")
        assert r.outcome == SKIPPED_UNSUPPORTED_BRAND

    def test_hyatt_is_unsupported_because_it_has_no_registered_adapter(self):
        r = _project(resolved_url="https://www.hyatt.com/en-US/hotel/ohio/x/cmhrh")
        assert r.outcome == SKIPPED_UNSUPPORTED_BRAND

    def test_a_blocked_revalidation_stops_the_handoff(self):
        """FD-5: a redirect to a different property identity BLOCKS handoff."""
        r = _project(url_revalidation_blocked=True,
                     revalidation_reason="property_identity_check_failed")
        assert r.outcome == SKIPPED_URL_REVALIDATION
        assert r.entry is None
        assert r.reason == "property_identity_check_failed"

    def test_revalidation_is_checked_before_anything_that_could_look_valid(self):
        """Ordering matters: a blocked URL must not first be accepted on
        brand/adapter grounds."""
        r = _project(resolved_url=MARRIOTT_URL, url_revalidation_blocked=True)
        assert r.outcome == SKIPPED_URL_REVALIDATION

    def test_a_search_shaped_url_is_rejected_by_the_real_preflight(self):
        """The PTF-WORKERS-007 class. The seam does not get to override it."""
        r = _project(resolved_url="https://www.marriott.com/search/findHotels.mi")
        assert r.outcome in (REJECTED_BY_PREFLIGHT, SKIPPED_UNSUPPORTED_BRAND)
        assert r.entry is None

    def test_nothing_is_ever_dropped_silently(self):
        for r in (_project(resolution_outcome=C.RESOLUTION_DEFER),
                  _project(resolved_url=""),
                  _project(url_revalidation_blocked=True)):
            assert r.outcome and r.outcome != PROJECTED
            assert r.reason or r.problems


class TestDeterminismAndAssembly:
    def test_queue_entry_id_is_deterministic_over_the_idempotency_key(self):
        a = queue_entry_id_for("dc_x", "1.1.0")
        assert a == queue_entry_id_for("dc_x", "1.1.0")
        assert a != queue_entry_id_for("dc_x", "1.0.0")
        assert a != queue_entry_id_for("dc_y", "1.1.0")

    def test_a_rerun_under_the_same_contract_reproduces_the_same_entry_id(self):
        assert _project().entry.queue_entry_id == _project().entry.queue_entry_id

    def test_priority_is_explainable(self):
        e = _project().entry
        assert e.priority_reasons
        assert "official_url_confirmed" in e.priority_reasons
        assert "supported_adapter:marriott" in e.priority_reasons

    def test_an_assembled_payload_loads_through_the_real_loader(self, tmp_path):
        """End to end: projected entries -> file -> the worker's own loader."""
        payload = build_queue_payload([_project()], batch_id="seam-test")
        path = tmp_path / "q.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        queue = load_queue(path, known_brands=known_brands())
        assert len(queue) == 1
        assert queue.entries[0].candidate_id == "dc_marriott0001"

    def test_summary_accounts_for_every_candidate(self):
        results = [_project(), _project(resolved_url=""),
                   _project(resolution_outcome=C.RESOLUTION_DEFER)]
        counts = summarize(results)
        assert sum(counts.values()) == 3
        assert counts[PROJECTED] == 1

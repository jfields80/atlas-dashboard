"""WO-1A Step 3 -- worker_contract_version propagation onto the queue entry.

FD-3 rule 2: the worker owns the value; the queue reads and propagates it and
never invents one. FD-3 rule 4: the idempotency key
``(candidate_id, worker_contract_version)`` may only be used once the version
is corrected and actually propagated -- these tests are what make it formable.
"""

from __future__ import annotations

import glob
import json
import pathlib

import pytest

from services.research_workers import vocabulary as V
from services.research_workers.capture_automation.adapters import known_brands
from services.research_workers.capture_automation.queue import (
    QUEUE_SCHEMA, QueueError, load_queue, validate_entry,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

GOOD = {
    "hotel_id": "cmham-columbus-airport-marriott",
    "listing_key": "columbus airport marriott",
    "hotel_name": "Columbus Airport Marriott",
    "brand": "marriott",
    "official_url": "https://www.marriott.com/en-us/hotels/"
                    "cmham-columbus-airport-marriott/overview/",
    "expected_address": "1375 North Cassady Avenue",
    "expected_city": "Columbus",
    "expected_state": "OH",
    "expected_postal_code": "43219",
    "expected_phone": "614-475-7551",
    "expected_property_code": "cmham",
}


def _write(tmp_path, hotels):
    path = tmp_path / "queue.json"
    path.write_text(json.dumps({
        "schema": QUEUE_SCHEMA, "batch_id": "cv-test", "hotels": hotels,
    }), encoding="utf-8")
    return path


class TestPropagation:
    def test_an_entry_stating_nothing_is_stamped_with_the_worker_version(self):
        entry, problems = validate_entry(dict(GOOD), 0, known_brands=known_brands())
        assert problems == []
        assert entry.worker_contract_version == V.CONTRACT_VERSION == "1.1.0"

    def test_an_entry_stating_a_compatible_version_keeps_it(self):
        """A queue authored under 1.0.0 stays labelled 1.0.0 -- the queue
        reports what it was built against, it does not rewrite history."""
        raw = dict(GOOD, worker_contract_version="1.0.0")
        entry, problems = validate_entry(raw, 0, known_brands=known_brands())
        assert problems == []
        assert entry.worker_contract_version == "1.0.0"

    def test_the_version_survives_serialization(self):
        entry, _ = validate_entry(dict(GOOD), 0, known_brands=known_brands())
        assert entry.to_dict()["worker_contract_version"] == V.CONTRACT_VERSION

    def test_the_queue_never_invents_a_version(self):
        """Whatever it carries is either the worker's constant or a value
        that was written in the file -- never a third thing."""
        entry, _ = validate_entry(dict(GOOD), 0, known_brands=known_brands())
        assert entry.worker_contract_version in V.CONTRACT_COMPATIBILITY


class TestIncompatibleVersionsFailClosed:
    def test_an_unknown_version_is_a_preflight_problem(self):
        raw = dict(GOOD, worker_contract_version="9.9.9")
        entry, problems = validate_entry(raw, 0, known_brands=known_brands())
        assert entry is None
        assert any("incompatible_worker_contract_version:9.9.9" in p for p in problems)

    def test_a_future_version_is_refused(self):
        raw = dict(GOOD, worker_contract_version="2.0.0")
        entry, problems = validate_entry(raw, 0, known_brands=known_brands())
        assert entry is None
        assert any("incompatible_worker_contract_version" in p for p in problems)

    def test_a_whole_queue_with_an_incompatible_entry_is_refused(self, tmp_path):
        path = _write(tmp_path, [dict(GOOD, worker_contract_version="2.0.0")])
        with pytest.raises(QueueError) as exc:
            load_queue(path, known_brands=known_brands())
        assert "incompatible_worker_contract_version" in str(exc.value)


class TestIdempotencyKeyIsFormable:
    def test_the_pair_is_available_on_a_loaded_entry(self, tmp_path):
        """FD-3 rule 4. ``candidate_id`` arrives in Step 5; ``hotel_id`` is
        today's stable per-entry identity, and the version half is now real
        rather than a constant that never moved."""
        queue = load_queue(_write(tmp_path, [dict(GOOD)]), known_brands=known_brands())
        e = queue.entries[0]
        key = (e.hotel_id, e.worker_contract_version)
        assert all(part for part in key)
        assert key[1] == V.CONTRACT_VERSION


class TestBackwardCompatibility:
    def test_existing_queues_without_the_field_still_load(self, tmp_path):
        queue = load_queue(_write(tmp_path, [dict(GOOD)]), known_brands=known_brands())
        assert len(queue) == 1

    @pytest.mark.parametrize("path", sorted(glob.glob(str(
        REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
        / "capture_batches" / "*queue*.json"))))
    def test_real_archived_queues_still_load_and_get_stamped(self, path):
        """Real queues predate the field entirely. They must keep loading,
        and each entry must come back stamped with the worker's version.

        ``data/`` is gitignored, so this is empty in a clean clone; a
        ``QueueError`` is tolerated because some archived queues reference
        retrieval artifacts whose paths no longer resolve -- a pre-existing
        operational concern, not a contract-version one.
        """
        try:
            queue = load_queue(path, known_brands=known_brands())
        except QueueError as exc:
            assert "worker_contract_version" not in str(exc)
            return
        for entry in queue.entries:
            assert entry.worker_contract_version == V.CONTRACT_VERSION

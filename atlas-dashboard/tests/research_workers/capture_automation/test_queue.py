"""Queue preflight.

Every check here exists because failing late is worse. A search URL that reaches
the browser costs a navigation; a search URL that reaches a *capture* becomes a
published citation, which is the PTF-WORKERS-007 defect discovered in production.
Catching that class at queue-load costs nothing.
"""

from __future__ import annotations

import json

import pytest

from services.research_workers.capture_automation.adapters import known_brands
from services.research_workers.capture_automation.queue import (
    QUEUE_SCHEMA, CaptureQueue, QueueError, load_queue, remaining_entries,
    validate_entry,
)

GOOD = {
    "hotel_id": "cmham-columbus-airport-marriott",
    "listing_key": "columbus-airport-marriott",
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


def write_queue(tmp_path, hotels, **top):
    payload = {"schema": QUEUE_SCHEMA, "batch_id": "test-batch",
               "hotels": hotels}
    payload.update(top)
    path = tmp_path / "queue.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestAcceptsAGoodQueue:
    def test_loads(self, tmp_path):
        queue = load_queue(write_queue(tmp_path, [GOOD]),
                           known_brands=known_brands())
        assert len(queue) == 1
        assert queue.batch_id == "test-batch"
        assert queue.entries[0].expected_property_code == "cmham"

    def test_optional_fields_default_cleanly(self, tmp_path):
        queue = load_queue(write_queue(tmp_path, [GOOD]),
                           known_brands=known_brands())
        entry = queue.entries[0]
        assert entry.alternate_urls == ()
        assert entry.required_fields == ()
        assert entry.notes == ""


class TestRefusesBadEntries:
    @pytest.mark.parametrize("field", [
        "hotel_id", "listing_key", "hotel_name", "brand", "official_url",
        "expected_address", "expected_city", "expected_state", "expected_phone",
    ])
    def test_missing_required_field(self, field):
        raw = dict(GOOD)
        raw.pop(field)
        entry, problems = validate_entry(raw, 0)
        assert entry is None
        assert any("missing_field:%s" % field in p for p in problems)

    def test_search_url_is_refused_at_load(self):
        """The defect that reached production, caught before a browser opens."""
        raw = dict(GOOD, official_url="https://www.marriott.com/search/"
                                      "findHotels.mi?destination=Columbus")
        entry, problems = validate_entry(raw, 0)
        assert entry is None
        assert any("url_shape_not_property" in p for p in problems)

    def test_http_url_is_refused(self):
        raw = dict(GOOD, official_url=GOOD["official_url"].replace("https", "http"))
        entry, problems = validate_entry(raw, 0)
        assert entry is None
        assert any("url_not_https" in p for p in problems)

    def test_embedded_credentials_are_refused(self):
        raw = dict(GOOD, official_url="https://user:pw@www.marriott.com/en-us/"
                                      "hotels/cmham-columbus-airport-marriott/overview/")
        entry, problems = validate_entry(raw, 0)
        assert entry is None
        assert any("embedded_credentials" in p for p in problems)

    def test_property_code_must_appear_in_the_url(self):
        raw = dict(GOOD, expected_property_code="cmhzz")
        entry, problems = validate_entry(raw, 0)
        assert entry is None
        assert any("property_code_not_in_url" in p for p in problems)

    def test_unknown_brand_is_refused_when_brands_are_supplied(self):
        raw = dict(GOOD, brand="fictional-inns")
        entry, problems = validate_entry(raw, 0, known_brands=known_brands())
        assert entry is None
        assert any("no_adapter_for_brand" in p for p in problems)

    def test_missing_retrieval_artifact_is_refused(self, tmp_path):
        raw = dict(GOOD, retrieval_artifact=str(tmp_path / "nope.json"))
        entry, problems = validate_entry(raw, 0)
        assert entry is None
        assert any("retrieval_artifact_missing" in p for p in problems)

    def test_non_object_entry(self):
        entry, problems = validate_entry(["not", "a", "dict"], 3)
        assert entry is None
        assert any("not_an_object" in p for p in problems)


class TestRefusesBadQueues:
    def test_missing_file(self, tmp_path):
        with pytest.raises(QueueError, match="not found"):
            load_queue(tmp_path / "absent.json")

    def test_bad_json(self, tmp_path):
        p = tmp_path / "q.json"
        p.write_text("{not json", encoding="utf-8")
        with pytest.raises(QueueError, match="not valid JSON"):
            load_queue(p)

    def test_wrong_schema(self, tmp_path):
        p = tmp_path / "q.json"
        p.write_text(json.dumps({"schema": "other/1.0", "batch_id": "b",
                                 "hotels": [GOOD]}), encoding="utf-8")
        with pytest.raises(QueueError, match="unsupported queue schema"):
            load_queue(p)

    def test_empty_hotels(self, tmp_path):
        with pytest.raises(QueueError, match="carries no hotels"):
            load_queue(write_queue(tmp_path, []))

    def test_missing_batch_id(self, tmp_path):
        p = tmp_path / "q.json"
        p.write_text(json.dumps({"schema": QUEUE_SCHEMA, "hotels": [GOOD]}),
                     encoding="utf-8")
        with pytest.raises(QueueError, match="missing batch_id"):
            load_queue(p)

    def test_batch_id_cannot_traverse_paths(self, tmp_path):
        with pytest.raises(QueueError, match="alphanumeric"):
            load_queue(write_queue(tmp_path, [GOOD], batch_id="../../escape"))

    def test_duplicate_hotel_id(self, tmp_path):
        with pytest.raises(QueueError, match="duplicate_hotel_id"):
            load_queue(write_queue(tmp_path, [GOOD, dict(GOOD)]))

    def test_every_problem_is_reported_at_once(self, tmp_path):
        """One pass of fixes, not one run per typo."""
        bad_a = dict(GOOD, hotel_id="a")
        bad_a.pop("expected_phone")
        bad_b = dict(GOOD, hotel_id="b", official_url="http://insecure.example/x")
        with pytest.raises(QueueError) as exc:
            load_queue(write_queue(tmp_path, [bad_a, bad_b]))
        message = str(exc.value)
        assert "missing_field:expected_phone" in message
        assert "url_not_https" in message or "url_shape_not_property" in message

    def test_a_partly_valid_queue_is_not_run(self, tmp_path):
        bad = dict(GOOD, hotel_id="b", brand="")
        with pytest.raises(QueueError):
            load_queue(write_queue(tmp_path, [GOOD, bad]))


class TestResume:
    def test_completed_hotels_are_skipped(self, tmp_path):
        queue = load_queue(write_queue(
            tmp_path, [GOOD, dict(GOOD, hotel_id="second",
                                  listing_key="second")]))
        assert len(remaining_entries(queue, [])) == 2
        assert len(remaining_entries(queue, [GOOD["hotel_id"]])) == 1
        assert remaining_entries(queue, [GOOD["hotel_id"], "second"]) == ()

    def test_unknown_completed_id_changes_nothing(self, tmp_path):
        queue = load_queue(write_queue(tmp_path, [GOOD]))
        assert len(remaining_entries(queue, ["never-queued"])) == 1

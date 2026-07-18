"""AES-DATA-004A discovery -- serialization round-trip tests (Task 1/5)."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.coverage import build_coverage_summary, render_coverage_json
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_records
from scripts.pettripfinder.discovery.serialization import (
    candidate_from_dict,
    candidate_to_dict,
    coverage_from_dict,
    dumps_candidates,
    loads_candidates,
)


def _candidates():
    r = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                        canonical_category=C.CATEGORY_VETERINARY, name="Test Vet",
                        address_line="1 Main St", city="Columbus", state="OH",
                        postal_code="43215", latitude=39.96, longitude=-82.99,
                        phone="6145550100", website_url="https://test.example.com",
                        warnings=("w1",), provenance=(("market_id", "columbus-oh"),))
    return deduplicate(normalize_records((r,)), market_id="columbus-oh")


def test_candidate_round_trip_byte_identical():
    cands = _candidates()
    blob = dumps_candidates(cands)
    restored = loads_candidates(blob)
    assert dumps_candidates(restored) == blob


def test_candidate_round_trip_preserves_nested_records():
    cands = _candidates()
    d = candidate_to_dict(cands[0])
    restored = candidate_from_dict(d)
    assert restored.source_records[0].warnings == ("w1",)
    assert restored.source_records[0].provenance == (("market_id", "columbus-oh"),)


def test_coverage_round_trip_via_json_render():
    m = load_market_config("columbus-oh")
    summary = build_coverage_summary(
        market=m, observed_at="2026-07-18", providers_enabled=(C.PROVIDER_GOOGLE_PLACES,),
        google_key_present=True, foursquare_key_present=False,
        planned_queries=[], query_results=[], candidates=_candidates(),
    )
    import json
    text = render_coverage_json(summary)
    restored = coverage_from_dict(json.loads(text))
    assert restored.market_id == summary.market_id
    assert restored.unique_candidates == summary.unique_candidates
    assert dict(restored.credentials_available) == dict(summary.credentials_available)


def test_deterministic_serialization_sorted_keys():
    cands = _candidates()
    blob = dumps_candidates(cands)
    assert blob == dumps_candidates(_candidates())   # two independent builds -> identical bytes

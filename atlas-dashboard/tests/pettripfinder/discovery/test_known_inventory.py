"""AES-DATA-004B Phase 9 -- known-inventory recall spot-check tests.
Uses a small synthetic CSV fixture, never the real production seed CSV, to
keep the suite hermetic and independent of production data."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.known_inventory import (
    KnownHotel,
    compute_recall,
    load_known_hotels,
    recall_summary_counts,
)
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_business_name


_CSV_HEADER = "name,category,address,city,state,postal_code,phone,website_url,source_url,source_type,observed_at,rating,amenities,pet_policy,canonical\n"


def _write_csv(tmp_path, rows):
    path = tmp_path / "seed.csv"
    lines = [_CSV_HEADER]
    for r in rows:
        lines.append(",".join(r) + "\n")
    path.write_text("".join(lines), encoding="utf-8")
    return path


def test_load_known_hotels_filters_by_category(tmp_path):
    path = _write_csv(tmp_path, [
        ("Test Hotel", "pet-friendly-hotels", "1 Main St", "Columbus", "OH", "43215",
         "", "", "", "", "", "", "", "", ""),
        ("Test Park", "pet-friendly-parks", "2 Park Ave", "Columbus", "OH", "43215",
         "", "", "", "", "", "", "", "", ""),
    ])
    hotels = load_known_hotels(str(path))
    assert len(hotels) == 1
    assert hotels[0].name == "Test Hotel"


def test_missing_csv_returns_empty_not_error(tmp_path):
    assert load_known_hotels(str(tmp_path / "nonexistent.csv")) == ()


def _cand(name, city="Columbus", state="OH", postal_code="43215", candidate_id="dc_1"):
    r = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                        canonical_category=C.CATEGORY_HOTEL, name=name)
    return DiscoveryCandidate(
        candidate_id=candidate_id, source_records=(r,), name=name,
        normalized_name=normalize_business_name(name), city=city, state=state,
        postal_code=postal_code,
    )


def test_recall_found_by_name_and_postal():
    known = (KnownHotel(name="Drury Inn & Suites Columbus Polaris",
                        address_line="8805 Orion Place", city="Columbus", state="OH",
                        postal_code="43240"),)
    candidates = (_cand("Drury Inn & Suites Columbus Polaris", postal_code="43240"),)
    result = compute_recall(known, candidates)
    assert len(result.found) == 1
    assert len(result.missed) == 0
    assert result.discovery_only_count == 0


def test_recall_missed_when_discovery_lacks_it():
    known = (KnownHotel(name="Never Found Inn", address_line="", city="Columbus",
                        state="OH", postal_code="43215"),)
    result = compute_recall(known, ())
    assert len(result.found) == 0
    assert len(result.missed) == 1
    assert result.missed[0].name == "Never Found Inn"


def test_discovery_only_candidates_never_injected_into_known_set():
    known = ()
    candidates = (_cand("Brand New Hotel Discovery Found"),)
    result = compute_recall(known, candidates)
    assert result.discovery_only_count == 1
    assert result.discovery_only_candidate_ids == ("dc_1",)
    assert result.found == () and result.missed == ()


def test_summary_counts_shape():
    known = (KnownHotel(name="Found Hotel", address_line="", city="Columbus", state="OH",
                        postal_code="43215"),)
    candidates = (_cand("Found Hotel", postal_code="43215", candidate_id="dc_a"),
                 _cand("Extra Discovery Hotel", postal_code="43215", candidate_id="dc_b"))
    result = compute_recall(known, candidates)
    counts = dict(recall_summary_counts(result))
    assert counts == {"known_found": 1, "known_missed": 0, "discovery_only": 1}


def test_known_set_never_mutates_candidates_list():
    known = (KnownHotel(name="Some Hotel", address_line="", city="Columbus", state="OH",
                        postal_code="43215"),)
    candidates = ()
    result = compute_recall(known, candidates)
    # confirms compute_recall is purely read-only/analytical -- no candidate
    # list is ever built FROM the known set.
    assert candidates == ()
    assert len(result.missed) == 1

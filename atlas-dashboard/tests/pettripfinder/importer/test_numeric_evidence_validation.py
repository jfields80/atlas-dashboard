"""AES-DATA-004E (Task 6/7) -- numeric pet-policy evidence semantic
validator. Unit tests on the pure validator plus an end-to-end
reproduction of the live AES-DATA-004D InTown Suites defect using static
fixtures (no network, no live provider)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.models import ImportContext
from scripts.pettripfinder.importer.numeric_evidence_validation import (
    REASON_COPYRIGHT_YEAR_PATTERN,
    REASON_NO_FIELD_SEMANTIC_ANCHOR,
    REASON_PHONE_NUMBER_PATTERN,
    REASON_RESERVATION_NUMBER_PATTERN,
    REASON_ROOM_COUNT_PATTERN,
    REASON_ZIP_OR_ADDRESS_PATTERN,
    validate_numeric_plausibility,
)

# --------------------------------------------------------------------------- #
# Pure unit tests: invalid patterns.
# --------------------------------------------------------------------------- #

def test_phone_number_false_pet_count():
    ok, reason = validate_numeric_plausibility("pet_count_limit", "Room Reservations: 1-888-882-0805")
    assert ok is False
    assert reason == REASON_PHONE_NUMBER_PATTERN


def test_zip_false_weight():
    ok, reason = validate_numeric_plausibility("weight_limit", "Located at 1234 Main Street, Columbus, OH 43215")
    assert ok is False
    assert reason == REASON_ZIP_OR_ADDRESS_PATTERN


def test_year_false_fee():
    ok, reason = validate_numeric_plausibility("pet_fee", "Copyright 2026. All rights reserved.")
    assert ok is False
    assert reason == REASON_COPYRIGHT_YEAR_PATTERN


def test_room_count_false_pet_limit():
    ok, reason = validate_numeric_plausibility("pet_count_limit", "Hotel has 250 rooms.")
    assert ok is False
    assert reason == REASON_ROOM_COUNT_PATTERN


def test_reservation_number_false_fee():
    ok, reason = validate_numeric_plausibility("pet_fee", "Your confirmation number is 48213.")
    assert ok is False
    assert reason == REASON_RESERVATION_NUMBER_PATTERN


def test_bare_number_with_no_anchor_at_all():
    ok, reason = validate_numeric_plausibility("pet_count_limit", "Room 42.")
    assert ok is False
    assert reason == REASON_NO_FIELD_SEMANTIC_ANCHOR


# --------------------------------------------------------------------------- #
# Pure unit tests: valid evidence preserved.
# --------------------------------------------------------------------------- #

def test_valid_pet_count_sentence():
    ok, reason = validate_numeric_plausibility("pet_count_limit", "Maximum 2 pets per room.")
    assert ok is True and reason == ""


def test_valid_fee_sentence():
    ok, reason = validate_numeric_plausibility("pet_fee", "$75 nonrefundable pet fee per stay.")
    assert ok is True and reason == ""


def test_valid_weight_limit_sentence():
    ok, reason = validate_numeric_plausibility("weight_limit", "Pets must weigh 50 pounds or less.")
    assert ok is True and reason == ""


def test_valid_deposit_sentence():
    ok, reason = validate_numeric_plausibility("pet_deposit", "A $100 pet deposit is required.")
    assert ok is True and reason == ""


def test_mixed_sentence_with_phone_and_valid_pet_limit_stays_valid():
    # Doctrine: never reject valid evidence merely because it contains
    # another number -- a genuine field anchor wins.
    ok, reason = validate_numeric_plausibility(
        "pet_count_limit",
        "Call 1-888-555-0100 to ask about our pet policy: maximum 2 pets per room.")
    assert ok is True and reason == ""


def test_non_numeric_field_always_plausible():
    ok, reason = validate_numeric_plausibility("breed_restrictions", "Call 1-888-882-0805.")
    assert ok is True and reason == ""


# --------------------------------------------------------------------------- #
# End-to-end reproduction (Task 7 required proof): InTown-shaped candidate.
# --------------------------------------------------------------------------- #

def _run(html, facts, tmp_path, url="https://www.example-hotel.test/"):
    fixture = {
        "url": url,
        "context": {"category": "hotels", "expected_city": "Columbus", "expected_state": "OH"},
        "html": html, "extraction": {"facts": facts},
    }
    fp = Path(tempfile.mkdtemp()) / "fixture.json"
    fp.write_text(json.dumps(fixture), encoding="utf-8")
    fetcher, extractor = _build_static(url, str(fp))
    ctx = ImportContext(**fixture["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at="1970-01-01T00:00:00")


def test_intown_shaped_reproduction_suppresses_phone_derived_pet_count(tmp_path):
    html = (
        "<!doctype html><html><body><h1>Example Extended Stay Columbus</h1>"
        "<p>No pets allowed at Example Extended Stay Columbus OH.</p>"
        "<p>Room Reservations: 1-888-882-0805</p></body></html>"
    )
    c = _run(html, [
        {"field": "pets_allowed", "value": "false",
         "quote": "No pets allowed at Example Extended Stay Columbus OH"},
        {"field": "pet_count_limit", "value": "1", "quote": "Room Reservations: 1-888-882-0805"},
    ], tmp_path)

    # pets_allowed stays false -- the real, evidenced fact is untouched.
    assert dict(c.proposed_fields).get("pets_allowed", "") in ("", "false") or \
        dict(c.pet_facts).get("pets_allowed") == "false"
    assert dict(c.pet_facts).get("pets_allowed") == "false"

    # pet_count_limit never publishes -- absent from pet_facts entirely.
    assert "pet_count_limit" not in dict(c.pet_facts)

    # The evidence entry is preserved (index-preserving suppression), marked
    # UNSUPPORTED with the deterministic warning -- never silently dropped.
    count_evs = [e for e in c.evidence if e.field_name == "pet_count_limit"]
    assert len(count_evs) == 1
    assert count_evs[0].support_state == C.SUPPORT_UNSUPPORTED
    assert C.REASON_IMPLAUSIBLE_NUMERIC_EVIDENCE in count_evs[0].warnings

    # The candidate still correctly REJECTs on the real no-pets evidence.
    assert c.recommendation == C.RECOMMEND_REJECT
    assert C.REASON_NO_PETS in c.recommendation_reasons


def test_evidence_index_preserved_after_suppression(tmp_path):
    html = (
        "<!doctype html><html><body><h1>Example Suites Columbus</h1>"
        "<p>Pets are welcome at Example Suites.</p>"
        "<p>Room Reservations: 1-888-555-0199</p></body></html>"
    )
    c = _run(html, [
        {"field": "pets_allowed", "value": "true", "quote": "Pets are welcome at Example Suites"},
        {"field": "pet_count_limit", "value": "1", "quote": "Room Reservations: 1-888-555-0199"},
    ], tmp_path)
    # The suppressed field is absent from published facts...
    assert "pet_count_limit" not in dict(c.pet_facts)
    # ...but its evidence entry is still present at a stable index, with the
    # correct field name -- nothing shifted or vanished.
    idx = next(i for i, e in enumerate(c.evidence) if e.field_name == "pet_count_limit")
    assert c.evidence[idx].proposed_value == "1"
    assert c.evidence[idx].support_state == C.SUPPORT_UNSUPPORTED


def test_legacy_golden_bytes_unchanged_by_numeric_validator():
    from scripts.pettripfinder.importer.candidate import candidate_from_dict, dumps_candidate
    golden_dir = Path(__file__).resolve().parent / "fixtures" / "golden"
    for name in ("golden_drury", "golden_scioto", "golden_landgrant"):
        text = (golden_dir / (name + ".json")).read_text(encoding="utf-8")
        candidate = candidate_from_dict(json.loads(text))
        assert dumps_candidate(candidate) + "\n" == text

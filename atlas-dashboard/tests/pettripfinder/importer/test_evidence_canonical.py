"""AES-DATA-001 -- canonical evidence relocation (live address-evidence
defect). Evidence location may normalize only harmless comma/whitespace/
line-break presentation differences; it must never accept a content change
(number, street, city, ZIP, missing word, or paraphrase). No network."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.evidence import build_llm_evidence
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext, ProposedFact
from scripts.pettripfinder.importer.normalize import normalize_whitespace

_SNAP = normalize_whitespace(
    "Contact 6170 Parkcenter Circle, Dublin, OH 43017 for reservations.")


def _ev(quote, text=_SNAP):
    return build_llm_evidence(
        ProposedFact("address", "6170 Parkcenter Circle, Dublin, OH 43017", quote),
        text, "https://s.test/")


class TestCanonicalRelocation:
    def test_space_before_comma_matches(self):
        ev = _ev("6170 Parkcenter Circle, Dublin , OH 43017")
        assert ev.support_state == C.SUPPORT_SUPPORTED
        # Original snapshot wording is preserved (not the model's spacing).
        assert ev.snapshot_quote == "6170 Parkcenter Circle, Dublin, OH 43017"
        assert "canonical_whitespace_relocation" in ev.warnings
        assert ev.char_start >= 0 and ev.char_end > ev.char_start

    def test_no_space_comma_matches(self):
        assert _ev("6170 Parkcenter Circle, Dublin,OH 43017").support_state \
            == C.SUPPORT_SUPPORTED

    def test_line_breaks_between_components(self):
        # Snapshot with components split by line breaks (collapsed to spaces,
        # no commas); the model quote uses commas.
        snap = normalize_whitespace("6170 Parkcenter Circle Dublin OH 43017")
        assert _ev("6170 Parkcenter Circle, Dublin, OH 43017", snap).support_state \
            == C.SUPPORT_SUPPORTED

    def test_nonbreaking_spaces(self):
        quote = "6170 Parkcenter Circle, Dublin, OH 43017"
        assert _ev(quote).support_state == C.SUPPORT_SUPPORTED

    def test_punctuation_normalization_preserves_digits(self):
        ev = _ev("6170 Parkcenter Circle, Dublin , OH 43017")
        assert "6170" in ev.snapshot_quote and "43017" in ev.snapshot_quote

    def test_direct_match_needs_no_canonical_marker(self):
        ev = _ev("6170 Parkcenter Circle, Dublin, OH 43017")
        assert ev.support_state == C.SUPPORT_SUPPORTED
        assert "canonical_whitespace_relocation" not in ev.warnings


class TestNegativeSafety:
    def test_changed_zip_fails(self):
        assert _ev("6170 Parkcenter Circle, Dublin, OH 43018").support_state \
            == C.SUPPORT_UNSUPPORTED

    def test_changed_street_number_fails(self):
        assert _ev("6171 Parkcenter Circle, Dublin, OH 43017").support_state \
            == C.SUPPORT_UNSUPPORTED

    def test_changed_city_fails(self):
        assert _ev("6170 Parkcenter Circle, Columbus, OH 43017").support_state \
            == C.SUPPORT_UNSUPPORTED

    def test_changed_street_name_fails(self):
        assert _ev("6170 Riverside Circle, Dublin, OH 43017").support_state \
            == C.SUPPORT_UNSUPPORTED

    def test_missing_word_fails(self):
        # Dropping "Circle" changes token adjacency -> no match.
        assert _ev("6170 Parkcenter, Dublin, OH 43017").support_state \
            == C.SUPPORT_UNSUPPORTED

    def test_paraphrase_fails(self):
        assert _ev("located near Parkcenter in Dublin Ohio").support_state \
            == C.SUPPORT_UNSUPPORTED

    def test_partial_token_not_matched(self):
        # "oh 43017" must not match inside a longer token like "columboh".
        snap = normalize_whitespace("columboh 43017 place")
        ev = build_llm_evidence(ProposedFact("x", "oh 43017", "OH 43017"),
                                snap, "https://s.test/")
        assert ev.support_state == C.SUPPORT_UNSUPPORTED


def test_drury_llm_address_becomes_ready(tmp_path):
    """The full live defect: the address comes from the LLM with a stray
    space before the comma; canonical relocation makes it SUPPORTED and the
    candidate READY with every field populated (mission requirement 8)."""
    url = "https://www.druryhotels.com/locations/columbus-oh/drury-inn-and-suites-columbus-dublin"
    html = (
        "<!doctype html><html><head><title>Drury</title>"
        '<script type="application/ld+json">{"@type":"Hotel",'
        '"name":"Drury Inn & Suites Columbus Dublin","url":"%s"}</script></head>'
        "<body><h1>Drury Inn & Suites Columbus Dublin</h1>"
        "<p>6170 Parkcenter Circle, Dublin, OH 43017</p>"
        "<p>Reservations: 800-DRURYINN (800-378-7946)</p><p>P: 614-798-8802</p>"
        "<p>Dogs and cats welcome. Limit of two pets per room with a combined "
        "weight of 80 pounds.</p></body></html>" % url)
    fetcher = StaticPageFetcher()
    fetcher.add_html(url, html)
    extractor = StaticFactExtractor({"facts": [
        {"field": "pets_allowed", "value": "true", "quote": "Dogs and cats welcome"},
        {"field": "species_allowed", "value": "dogs and cats", "quote": "Dogs and cats welcome"},
        {"field": "name", "value": "Drury Inn & Suites Columbus Dublin",
         "quote": "Drury Inn & Suites Columbus Dublin"},
        {"field": "address", "value": "6170 Parkcenter Circle, Dublin, OH 43017",
         "quote": "6170 Parkcenter Circle, Dublin , OH 43017"},   # stray space
        {"field": "phone", "value": "614-798-8802", "quote": "P: 614-798-8802"},
        {"field": "phone", "value": "800-378-7946", "quote": "800-DRURYINN (800-378-7946)"},
        {"field": "weight_limit", "value": "80 pounds",
         "quote": "Limit of two pets per room with a combined weight of 80 pounds"},
    ]})
    cas = ArtifactStoreRepository(tmp_path / "cas")
    ctx = ImportContext(category="hotels", expected_city="Dublin", expected_state="OH")
    c = run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                   observed_at="2026-07-16", created_at="1970-01-01T00:00:00")
    p = dict(c.proposed_fields)
    assert p["name"] == "Drury Inn & Suites Columbus Dublin"
    assert p["address"] == "6170 Parkcenter Circle"
    assert p["city"] == "Dublin" and p["state"] == "OH"
    assert p["postal_code"] == "43017"
    assert p["phone"] == "614-798-8802"
    assert dict(c.pet_facts)["pet_count_limit"] == "2"
    assert dict(c.pet_facts)["weight_limit"] == "80 lb"
    assert not any(cf.field_name == "phone" for cf in c.conflicts)
    assert c.recommendation == C.RECOMMEND_READY

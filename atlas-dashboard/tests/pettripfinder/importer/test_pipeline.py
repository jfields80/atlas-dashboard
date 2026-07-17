"""AES-DATA-001 -- full pipeline integration via the deterministic static
seams (mission sections 14/18/19/28). No network, no API key."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import dumps_candidate, run_import
from scripts.pettripfinder.importer.models import ImportContext
from scripts.pettripfinder.importer.review_report import render_report_html

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _run(name, tmp_path, created_at="1970-01-01T00:00:00"):
    obj = json.loads((_FIXTURES / (name + ".json")).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(_FIXTURES / (name + ".json")))
    ctx = ImportContext(**obj.get("context", {}))
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-16", created_at=created_at)


@pytest.mark.parametrize("name,expected", [
    ("hotel_01_strong", C.RECOMMEND_READY),
    ("hotel_03_no_pets", C.RECOMMEND_REJECT),
    ("hotel_04_conflict", C.RECOMMEND_REVIEW),
    ("hotel_05_blocked", C.RECOMMEND_REVIEW),
    ("hotel_06_multi_entity", C.RECOMMEND_REVIEW),
    ("hotel_07_brand", C.RECOMMEND_READY),
    ("park_06_pdf", C.RECOMMEND_REVIEW),
    ("park_07_js_only", C.RECOMMEND_REVIEW),
    ("restaurant_08_unsupported_type", C.RECOMMEND_REJECT),
    ("restaurant_10_third_party", C.RECOMMEND_REJECT),
])
def test_recommendation(name, expected, tmp_path):
    c = _run(name, tmp_path)
    assert c.recommendation == expected


def test_ready_candidate_shape(tmp_path):
    c = _run("hotel_01_strong", tmp_path)
    p = dict(c.proposed_fields)
    assert p["name"] == "Drury Inn Columbus Polaris"
    assert p["category"] == "pet-friendly-hotels"
    assert p["address"] == "8805 Orion Place"
    assert p["source_type"] == "OFFICIAL_PROPERTY"
    assert "Dogs and cats are accepted." in p["pet_policy"]
    assert c.source_relationship == C.REL_EXACT_ENTITY_DOMAIN
    assert c.review_status == C.REVIEW_PENDING          # candidate != launch READY


def test_brand_relationship(tmp_path):
    c = _run("hotel_07_brand", tmp_path)
    assert c.source_relationship == C.REL_OFFICIAL_BRAND_DOMAIN
    assert dict(c.proposed_fields)["source_type"] == "OFFICIAL_BRAND"


def test_group_relationship(tmp_path):
    c = _run("restaurant_02_group", tmp_path)
    assert c.source_relationship == C.REL_OFFICIAL_GROUP_DOMAIN
    assert dict(c.proposed_fields)["source_type"] == "OFFICIAL_GROUP"


def test_government_relationship(tmp_path):
    c = _run("park_03_government", tmp_path)
    assert c.source_relationship == C.REL_OFFICIAL_GOVERNMENT_DOMAIN


class TestHostileContainment:
    def test_injection_cannot_publish_or_approve(self, tmp_path):
        c = _run("hotel_08_hostile", tmp_path)
        proposed = dict(c.proposed_fields)
        # Fabricated $0 fee (quote not in page) is never published.
        assert "$0" not in proposed["pet_policy"]
        assert "pet_fee" not in c.pet_facts_dict()
        # Unknown/forbidden fields never appear anywhere.
        fields = {e.field_name for e in c.evidence} | set(dict(c.proposed_fields))
        assert "approve" not in fields and "recommendation" not in fields
        # The model cannot approve: status is PENDING.
        assert c.review_status == C.REVIEW_PENDING
        # The fabricated fee is recorded as an unsupported evidence mismatch.
        mismatches = [e for e in c.evidence
                      if e.field_name == "pet_fee"
                      and C.REASON_EVIDENCE_MISMATCH in e.warnings]
        assert len(mismatches) == 1

    def test_source_url_immutable_by_content(self, tmp_path):
        c = _run("hotel_08_hostile", tmp_path)
        assert c.snapshot.requested_url == "https://www.hostilehotel.test/pets"


def test_determinism(tmp_path):
    c1 = _run("hotel_01_strong", tmp_path / "a")
    c2 = _run("hotel_01_strong", tmp_path / "b")
    assert dumps_candidate(c1) == dumps_candidate(c2)


def test_no_raw_html_inline(tmp_path):
    c = _run("hotel_08_hostile", tmp_path)
    blob = dumps_candidate(c)
    # Raw markup must live in CAS, never inline in the candidate JSON.
    assert "<script" not in blob and "<!doctype" not in blob and "<html" not in blob
    # But the raw bytes are recoverable from CAS by hash.
    assert c.snapshot.raw_content_hash


class TestReviewReport:
    def test_self_contained_and_shows_evidence(self, tmp_path):
        c = _run("hotel_01_strong", tmp_path)
        html = render_report_html(c, "candidate.json")
        assert "<script" not in html          # no JS at all
        assert "<link" not in html and "<img" not in html   # no external assets
        assert "cdn" not in html.lower() and "http://fonts" not in html
        assert "Dogs and cats are welcome" in html          # evidence quote visible
        assert "approve_import_candidate.py" in html         # commands visible

    def test_content_is_html_escaped(self, tmp_path):
        from dataclasses import replace
        c = _run("hotel_01_strong", tmp_path)
        # Force a value containing markup and confirm it is escaped, not rendered.
        fields = dict(c.proposed_fields)
        fields["name"] = "<script>alert(1)</script>"
        c2 = replace(c, proposed_fields=tuple((k, fields[k]) for k in fields))
        html = render_report_html(c2, "candidate.json")
        assert "&lt;script&gt;alert(1)" in html
        assert "<script>alert(1)" not in html

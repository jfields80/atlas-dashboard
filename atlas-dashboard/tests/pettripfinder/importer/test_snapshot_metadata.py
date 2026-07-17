"""AES-DATA-001 -- source snapshot + structured metadata (mission sections
6/7/28)."""

from __future__ import annotations

import hashlib

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import FetchResult
from scripts.pettripfinder.importer.source_snapshot import (
    build_snapshot,
    detect_javascript_only,
    normalize_html_to_text,
    snapshot_has_javascript_warning,
)
from scripts.pettripfinder.importer.structured_metadata import extract_structured_metadata

_HTML = (
    "<!doctype html><html><head><title>Hi</title>"
    "<script>var x=1;</script><style>.a{}</style>"
    "<link rel='canonical' href='https://ex.test/c'>"
    "<script type='application/ld+json'>"
    '{"@type":"Hotel","name":"Ex Hotel","telephone":"614-555-0100",'
    '"url":"https://ex.test/","address":{"@type":"PostalAddress",'
    '"streetAddress":"1 A St","addressLocality":"Columbus","addressRegion":"OH",'
    '"postalCode":"43215"}}</script></head>'
    "<body><nav>menu menu</nav><h1>Ex Hotel</h1>"
    "<p>Dogs   welcome  on  the   patio.</p>"
    "<a href='tel:+16145550100'>call</a><footer>foot</footer></body></html>"
)


def _fetch(body: str) -> FetchResult:
    return FetchResult("https://ex.test/", True, final_url="https://ex.test/",
                       http_status=200, content_type="text/html",
                       body=body.encode("utf-8"))


class TestNormalizeText:
    def test_strips_boilerplate_and_collapses(self):
        text, truncated = normalize_html_to_text(_HTML)
        assert "var x" not in text and ".a{}" not in text
        assert "menu menu" not in text and "foot" not in text
        assert "Dogs welcome on the patio." in text   # whitespace collapsed
        assert truncated is False

    def test_50kb_cap_and_truncation_warning(self, tmp_path):
        big = "<html><body><p>" + ("word " * 40000) + "</p></body></html>"
        text, truncated = normalize_html_to_text(big)
        assert truncated is True
        assert len(text.encode("utf-8")) <= C.NORMALIZED_TEXT_CAP_BYTES
        cas = ArtifactStoreRepository(tmp_path / "cas")
        snap = build_snapshot(_fetch(big), cas, "2026-07-16", C.REL_UNKNOWN)
        assert "normalized_text_truncated_50kb" in snap.fetch_warnings


class TestSnapshot:
    def test_hashes_stable_and_raw_in_cas(self, tmp_path):
        cas = ArtifactStoreRepository(tmp_path / "cas")
        s1 = build_snapshot(_fetch(_HTML), cas, "2026-07-16", C.REL_EXACT_ENTITY_DOMAIN)
        s2 = build_snapshot(_fetch(_HTML), cas, "2026-07-16", C.REL_EXACT_ENTITY_DOMAIN)
        assert s1.raw_content_hash == s2.raw_content_hash
        assert s1.normalized_text_hash == s2.normalized_text_hash
        assert s1.normalized_text_hash == hashlib.sha256(
            s1.normalized_text.encode("utf-8")).hexdigest()
        assert cas.exists_bytes(s1.raw_content_hash)
        assert cas.get_bytes(s1.raw_content_hash) == _HTML.encode("utf-8")

    def test_title_and_canonical(self, tmp_path):
        cas = ArtifactStoreRepository(tmp_path / "cas")
        snap = build_snapshot(_fetch(_HTML), cas, "2026-07-16", C.REL_UNKNOWN)
        assert snap.page_title == "Hi"
        assert snap.canonical_url == "https://ex.test/c"

    def test_javascript_only_flagged(self, tmp_path):
        js = ("<html><head><script src=a></script><script src=b></script>"
              "<script src=c></script></head><body><div id='root'></div></body></html>")
        cas = ArtifactStoreRepository(tmp_path / "cas")
        snap = build_snapshot(_fetch(js), cas, "2026-07-16", C.REL_UNKNOWN)
        assert snapshot_has_javascript_warning(snap)


class TestStructuredMetadata:
    def test_jsonld_entity_and_address(self):
        se = extract_structured_metadata(_HTML)
        by = se.by_field()
        assert by["name"].value == "Ex Hotel"
        assert by["phone"].value == "614-555-0100"
        assert by["address"].value == "1 A St"
        assert by["city"].value == "Columbus"
        assert by["state"].value == "OH"
        assert by["postal_code"].value == "43215"
        assert by["name"].method == C.METHOD_JSON_LD

    def test_multi_entity_detected(self):
        html = (
            "<html><body>"
            '<script type="application/ld+json">{"@type":"Hotel","name":"A"}</script>'
            '<script type="application/ld+json">{"@type":"Hotel","name":"B"}</script>'
            "</body></html>")
        se = extract_structured_metadata(html)
        assert se.multi_entity is True
        assert set(se.entity_names) == {"A", "B"}

    def test_malformed_jsonld_skipped_not_fatal(self):
        html = ('<html><body><script type="application/ld+json">{bad json</script>'
                "<h1>x</h1></body></html>")
        se = extract_structured_metadata(html)   # must not raise
        assert se.multi_entity is False

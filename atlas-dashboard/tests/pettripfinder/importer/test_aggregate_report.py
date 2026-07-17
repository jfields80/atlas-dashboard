"""AES-DATA-002C -- aggregate report rendering: source chips, the Sources
card, the aggregate summary, the richer conflict table, [UNKNOWN SOURCE]
handling, and byte-for-byte backward compatibility for single-source
reports. No network."""

from __future__ import annotations

from dataclasses import replace

from pettripfinder.importer._aggregate_helpers import (
    CONTACT_URL,
    FAQ_URL,
    build_fetcher_extractor,
    contact_facts,
    contact_html,
    default_context,
    faq_facts,
    faq_html,
    make_cas,
)

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static as old_build_static
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.models import ExtractedEvidence, ImportContext
from scripts.pettripfinder.importer.review_report import render_report_html

_FAQ_MARKER = "Beer Garden operations are weather dependent"
_CONTACT_MARKER = "Call the taproom at"


def _aggregate_candidate(tmp_path, urls=None, extra_facts=None):
    urls = urls or [FAQ_URL, CONTACT_URL]
    facts = {_FAQ_MARKER: faq_facts(), _CONTACT_MARKER: contact_facts()}
    if extra_facts:
        facts.update(extra_facts)
    fetcher, extractor = build_fetcher_extractor(
        [(FAQ_URL, faq_html()), (CONTACT_URL, contact_html())], facts)
    return run_multi_import(
        urls, default_context(), fetcher=fetcher, extractor=extractor,
        cas=make_cas(tmp_path), observed_at="2026-07-17",
        created_at="1970-01-01T00:00:00")


class TestSourceChips:
    def test_address_and_phone_chipped_s2_policy_chipped_s1(self, tmp_path):
        c = _aggregate_candidate(tmp_path)
        html_out = render_report_html(c, "candidate.json")
        idx_addr = html_out.find('"fname">address<')
        idx_next_field = html_out.find('"field"', idx_addr + 1)
        addr_block = html_out[idx_addr:idx_next_field]
        assert "[S2]" in addr_block

        idx_phone = html_out.find('"fname">phone<')
        idx_next_field2 = html_out.find('"field"', idx_phone + 1)
        phone_block = html_out[idx_phone:idx_next_field2]
        assert "[S2]" in phone_block

        assert "[S1]" in html_out   # pet-policy evidence is chipped somewhere
        assert "UNKNOWN SOURCE" not in html_out

    def test_unmapped_source_url_shows_unknown_source_and_warns(self, tmp_path):
        c = _aggregate_candidate(tmp_path)
        # Inject an evidence row whose source_url matches no SourceRecord,
        # published to a field the report actually renders (only known
        # proposed/pet-fact fields are shown -- unchanged pre-existing
        # behavior; publish the value too so this path is exercised).
        bogus = ExtractedEvidence(
            field_name="permitted_area", proposed_value="rooftop",
            source_wording="rooftop", source_url="https://not-a-real-source.test/page",
            snapshot_quote="rooftop", char_start=0, char_end=7,
            extraction_method="LLM_TEXT", support_state="SUPPORTED", warnings=())
        c2 = replace(c, evidence=c.evidence + (bogus,),
                    pet_facts=c.pet_facts + (("permitted_area", "rooftop"),))
        html_out = render_report_html(c2, "candidate.json")
        assert "UNKNOWN SOURCE" in html_out
        assert "could not be matched to a known source" in html_out
        # Never crashes, never silently drops the row.
        assert "rooftop" in html_out


class TestSourcesCard:
    def test_every_source_visible_included_and_excluded(self, tmp_path):
        cleveland_html = (
            "<!doctype html><html><head>"
            '<meta property="og:title" content="Land-Grant Brewing">'
            '<meta property="og:url" content="%s">'
            "</head><body>"
            '<script type="application/ld+json">'
            '{"@context": "https://schema.org", "@type": "Restaurant", '
            '"name": "Land-Grant Brewing", '
            '"address": {"streetAddress": "500 Main St", "addressLocality": "Cleveland", '
            '"addressRegion": "OH"}}</script>'
            "<h1>Land-Grant Brewing</h1></body></html>" % "https://landgrantbrewing.com/cleveland/")
        fetcher, extractor = build_fetcher_extractor(
            [(FAQ_URL, faq_html()), ("https://landgrantbrewing.com/cleveland/", cleveland_html)],
            {_FAQ_MARKER: faq_facts(), "Cleveland": {"facts": []}})
        c = run_multi_import(
            [FAQ_URL, "https://landgrantbrewing.com/cleveland/"], default_context(),
            fetcher=fetcher, extractor=extractor, cas=make_cas(tmp_path),
            observed_at="2026-07-17", created_at="1970-01-01T00:00:00")

        html_out = render_report_html(c, "candidate.json")
        assert "Sources</h3>" in html_out
        assert "[S1]" in html_out and "[S2]" in html_out
        assert "INCLUDED" in html_out
        assert "EXCLUDED: %s" % C.REASON_GEOGRAPHY_CONFLICT in html_out
        assert "https://landgrantbrewing.com/cleveland/" in html_out   # never disappears

    def test_blocked_supplemental_visible_with_fetch_reason(self, tmp_path):
        from scripts.pettripfinder.importer.fetch import StaticPageFetcher
        from scripts.pettripfinder.importer.models import FetchResult

        blocked_url = "https://landgrantbrewing.com/blocked/"
        fetcher = StaticPageFetcher()
        fetcher.add_html(FAQ_URL, faq_html())
        fetcher.add_result(blocked_url, FetchResult(
            requested_url=blocked_url, ok=False, http_status=403,
            reason=C.REASON_BLOCKED_SOURCE))
        _, extractor = build_fetcher_extractor([(FAQ_URL, faq_html())], {_FAQ_MARKER: faq_facts()})
        c = run_multi_import(
            [FAQ_URL, blocked_url], default_context(), fetcher=fetcher, extractor=extractor,
            cas=make_cas(tmp_path), observed_at="2026-07-17", created_at="1970-01-01T00:00:00")
        html_out = render_report_html(c, "candidate.json")
        assert "UNUSABLE: %s" % C.REASON_BLOCKED_SOURCE in html_out
        assert blocked_url in html_out


class TestAggregateSummary:
    def test_summary_counts_and_context(self, tmp_path):
        c = _aggregate_candidate(tmp_path)
        html_out = render_report_html(c, "candidate.json")
        assert "Aggregate summary" in html_out
        assert "sources supplied: 2" in html_out
        assert "included: 2" in html_out
        assert "excluded: 0" in html_out
        assert "unusable: 0" in html_out
        assert "Land-Grant Brewing Columbus" in html_out
        assert "Columbus" in html_out and "OH" in html_out
        assert C.AGGREGATION_VERSION in html_out


class TestAggregateConflictTable:
    def test_policy_conflict_shows_both_chips_and_type(self, tmp_path):
        policy_url = "https://landgrantbrewing.com/policy/"
        policy_html = (
            "<!doctype html><html><head>"
            '<meta property="og:title" content="Land-Grant Brewing Columbus">'
            '<meta property="og:url" content="%s">'
            "</head><body><h1>Land-Grant Brewing Columbus</h1>"
            "<p>Pets are not allowed inside the building at any time.</p>"
            "</body></html>" % policy_url)
        fetcher, extractor = build_fetcher_extractor(
            [(FAQ_URL, faq_html()), (policy_url, policy_html)],
            {_FAQ_MARKER: faq_facts(),
             "not allowed inside the building": {"facts": [
                 {"field": "pets_allowed", "value": "false",
                  "quote": "Pets are not allowed inside the building at any time"}]}})
        c = run_multi_import(
            [FAQ_URL, policy_url], default_context(), fetcher=fetcher, extractor=extractor,
            cas=make_cas(tmp_path), observed_at="2026-07-17", created_at="1970-01-01T00:00:00")
        html_out = render_report_html(c, "candidate.json")
        assert "pets_allowed" not in dict(c.pet_facts)
        assert C.REASON_POLICY_CONFLICT in html_out
        assert "[S1]" in html_out and "[S2]" in html_out
        assert "true" in html_out and "false" in html_out


class TestBackwardCompatSingleSource:
    def test_single_source_report_has_no_aggregate_markers(self, tmp_path):
        fetcher, extractor = old_build_static(
            FAQ_URL, str((__import__("pathlib").Path(__file__).parent
                         / "fixtures" / "hotel_01_strong.json")))
        ctx = ImportContext(category="hotels", expected_city="Columbus", expected_state="OH")
        c = run_import(
            "https://www.druryhotels.test/polaris", ctx, fetcher=fetcher, extractor=extractor,
            cas=ArtifactStoreRepository(tmp_path / "cas"), observed_at="2026-07-17",
            created_at="1970-01-01T00:00:00")
        assert c.sources == ()
        html_out = render_report_html(c, "candidate.json")
        assert "Sources</h3>" not in html_out
        assert "Aggregate summary" not in html_out
        assert "chip" not in html_out
        assert "[S1]" not in html_out
        assert "UNKNOWN SOURCE" not in html_out

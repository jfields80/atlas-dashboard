"""AES-DATA-001 -- page-purpose title-segment handling (live Land-Grant FAQ
defect). A page-purpose title segment (FAQ / Hours, Parking & More / Contact
/ ...) is boilerplate, not a distinct entity -- but only as an isolated
separator-delimited segment, never as a word inside a literal entity name.
No network; address is never synthesized."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext


# --------------------------------------------------------------------------- #
# Recognizer unit tests.
# --------------------------------------------------------------------------- #

class TestPagePurposeRecognition:
    @pytest.mark.parametrize("seg", [
        "FAQ", "Frequently Asked Questions", "Hours, Parking & More",
        "Hours and Parking", "Contact", "Locations", "Visit", "About",
    ])
    def test_page_purpose_segments(self, seg):
        assert N.looks_like_page_purpose(seg) is True

    @pytest.mark.parametrize("name", [
        "FAQ Coffee", "The Contact Bar", "About Time Brewing",
        "Visit Columbus Cafe", "Hours Brewing Company",
    ])
    def test_literal_entity_names_not_page_purpose(self, name):
        assert N.looks_like_page_purpose(name) is False
        # And a single-segment literal name is never stripped.
        assert N.clean_entity_name(name) == name

    @pytest.mark.parametrize("entity,title", [
        ("Land-Grant Brewing Columbus",
         "FAQ | Land-Grant Brewing Columbus | Hours, Parking & More"),
        ("Land-Grant Brewing", "Frequently Asked Questions | Land-Grant Brewing"),
        ("Land-Grant Brewing", "Land-Grant Brewing — Hours and Parking"),
    ])
    def test_page_purpose_title_compatible(self, entity, title):
        assert N.names_compatible(entity, title) is True
        assert N.clean_entity_name(title) == entity

    @pytest.mark.parametrize("a,b", [
        ("Land-Grant Brewing", "Seventh Son Brewing"),
        ("Land-Grant Brewing", "Land-Grant Hotel"),
        ("Land-Grant Brewing", "Land-Grant Brewing Cleveland"),
    ])
    def test_genuinely_different_names_still_conflict(self, a, b):
        assert N.names_compatible(a, b) is False

    def test_entity_name_with_faq_word_not_stripped_in_title(self):
        # "FAQ Coffee" as a title segment stays an entity, not boilerplate.
        assert N.clean_entity_name("FAQ Coffee | Home") == "FAQ Coffee"


# --------------------------------------------------------------------------- #
# Full Land-Grant FAQ pipeline.
# --------------------------------------------------------------------------- #

def test_land_grant_faq_review_for_missing_address_only(tmp_path):
    url = "https://landgrantbrewing.com/faq/"
    html = (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="FAQ | Land-Grant Brewing Columbus '
        '| Hours, Parking &amp; More">'
        '<meta property="og:url" content="https://landgrantbrewing.com/">'
        "</head><body><h1>Land-Grant Brewing Columbus</h1>"
        "<p>Dogs are welcome in the beer garden and on the patio. Dogs are not "
        "permitted indoors. Beer Garden operations are weather dependent.</p>"
        "</body></html>")
    fetcher = StaticPageFetcher()
    fetcher.add_html(url, html)
    extractor = StaticFactExtractor({"facts": [
        {"field": "name", "value": "Land-Grant Brewing Columbus",
         "quote": "Land-Grant Brewing Columbus"},
        {"field": "pets_allowed", "value": "true",
         "quote": "Dogs are welcome in the beer garden and on the patio"},
        {"field": "patio_or_outdoor_only", "value": "true",
         "quote": "Dogs are welcome in the beer garden and on the patio"},
        {"field": "permitted_area", "value": "beer garden and patio",
         "quote": "beer garden and on the patio"},
        {"field": "indoor_prohibited", "value": "true",
         "quote": "Dogs are not permitted indoors"},
        {"field": "seasonal_or_weather_caveat",
         "value": "Beer Garden operations are weather dependent",
         "quote": "Beer Garden operations are weather dependent"},
    ]})
    cas = ArtifactStoreRepository(tmp_path / "cas")
    ctx = ImportContext(category="restaurants", expected_city="Columbus",
                        expected_state="OH")
    c = run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                   observed_at="2026-07-16", created_at="1970-01-01T00:00:00")
    p = dict(c.proposed_fields)

    # Name is the clean entity; no name conflict; no title-induced ambiguity.
    assert p["name"] == "Land-Grant Brewing Columbus"
    assert not any(cf.field_name == "name" for cf in c.conflicts)
    assert not any(e.support_state == C.SUPPORT_AMBIGUOUS for e in c.evidence)
    # Both source values preserved.
    name_sources = {w for e in c.evidence if e.field_name == "name" for w in e.warnings}
    assert "name_source:OPEN_GRAPH" in name_sources
    assert "name_source:LLM_TEXT" in name_sources
    # Address is genuinely absent and is NOT synthesized.
    assert p["address"] == ""
    # Supported pet facts are present.
    facts = dict(c.pet_facts)
    assert facts.get("patio_or_outdoor_only") == "true"
    assert facts.get("indoor_prohibited") == "true"
    # Correct outcome: REVIEW solely for the missing required address.
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert c.recommendation_reasons == ("missing_required_field:address",)

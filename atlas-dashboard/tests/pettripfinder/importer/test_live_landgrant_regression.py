"""AES-DATA-001 -- live Land-Grant regression (candidate
landgrantbrewing-com-e70ad5c876). The live Anthropic response proposed a
SINGLE name fact whose value is the brand-short form ("Land-Grant Brewing",
quoted from the h1 "Land-Grant Brewing Columbus"), so the page-derived
resolved name was the SHORT form and the branded OG title -- which
reconciles to the LONGER "Land-Grant Brewing Columbus" -- failed
reconciliation: the expected-city suffix rule only ran in the
resolved-long/alternate-short direction. This test replays the exact live
provider facts and page shape through the production pipeline. No network;
address never synthesized."""

from __future__ import annotations

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import (
    _reconciles_with_resolved,
    run_import,
)
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext

_URL = "https://landgrantbrewing.com/faq/"

# Page shape mirroring the live snapshot: branded OG title, h1 carrying the
# full entity name (the LLM's quote span), the exact live pet-policy
# sentences, and no street address anywhere.
_HTML = (
    "<!doctype html><html><head>"
    '<meta property="og:title" content="FAQ | Land-Grant Brewing Columbus '
    '| Hours, Parking &amp; More">'
    '<meta property="og:url" content="https://landgrantbrewing.com/faq/">'
    "</head><body><h1>Land-Grant Brewing Columbus</h1>"
    "<p>*Beer Garden operations are weather dependent.</p>"
    "<p>Much to Gus and Debbie's excitement, well-behaved dogs are welcome "
    "in our beer garden and on the patio. Dogs must be leashed and remain "
    "under direct control at all times. Water bowls and treats are available "
    "at the bar. While we love having your four-legged friends around, "
    "please note that dogs are not able to join you inside our Wintergarden "
    "Igloos or out on the ice rinks.</p>"
    "</body></html>")

# The exact live LLM facts (from the persisted candidate's LLM_TEXT
# evidence): note the SINGLE name fact with the short-form value.
_LIVE_FACTS = {"facts": [
    {"field": "name", "value": "Land-Grant Brewing",
     "quote": "Land-Grant Brewing Columbus"},
    {"field": "pets_allowed", "value": "true",
     "quote": "well-behaved dogs are welcome in our beer garden and on the patio"},
    {"field": "patio_or_outdoor_only", "value": "true",
     "quote": "well-behaved dogs are welcome in our beer garden and on the patio"},
    {"field": "permitted_area", "value": "beer garden and patio",
     "quote": "well-behaved dogs are welcome in our beer garden and on the patio"},
    {"field": "indoor_prohibited", "value": "true",
     "quote": "dogs are not able to join you inside our Wintergarden Igloos "
              "or out on the ice rinks"},
    {"field": "seasonal_or_weather_caveat",
     "value": "Beer Garden operations are weather dependent",
     "quote": "*Beer Garden operations are weather dependent."},
    {"field": "water_or_treats", "value": "true",
     "quote": "Water bowls and treats are available at the bar."},
]}


def _run_live_replay(tmp_path, *, expected_city="Columbus"):
    fetcher = StaticPageFetcher()
    fetcher.add_html(_URL, _HTML)
    extractor = StaticFactExtractor(_LIVE_FACTS)
    cas = ArtifactStoreRepository(tmp_path / "cas")
    # The exact live CLI context (--candidate-name / --expected-city /
    # --expected-state / --source-relationship).
    ctx = ImportContext(
        category="restaurants", expected_city=expected_city,
        expected_state="OH", candidate_name="Land-Grant Brewing Columbus",
        source_relationship_hint="EXACT_ENTITY_DOMAIN")
    return run_import(_URL, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-16", created_at="2026-07-16T23:43:11")


# --------------------------------------------------------------------------- #
# Reconciler direction unit tests.
# --------------------------------------------------------------------------- #

class TestReconcilerDirection:
    def test_longer_city_form_reconciles_with_short_resolved(self):
        # Live shape: resolved (page-derived) is the SHORT brand form; the
        # OG title reconciles to the longer "<base> <expected_city>".
        assert _reconciles_with_resolved(
            "Land-Grant Brewing",
            "FAQ | Land-Grant Brewing Columbus | Hours, Parking & More",
            "Columbus", True) is True

    def test_short_form_reconciles_with_long_resolved(self):
        assert _reconciles_with_resolved(
            "Land-Grant Brewing Columbus", "Land-Grant Brewing",
            "Columbus", True) is True

    @pytest.mark.parametrize("resolved,candidate", [
        ("Land-Grant Brewing", "Land-Grant Brewing Cleveland"),
        ("Land-Grant Brewing", "Seventh Son Brewing"),
        ("Land-Grant Brewing", "Land-Grant Hotel Columbus"),
        ("Brewing Company", "Columbus Brewing Company"),  # leading city
    ])
    def test_negative_pairs_still_fail_both_directions(self, resolved, candidate):
        assert _reconciles_with_resolved(
            resolved, candidate, "Columbus", True) is False

    def test_reverse_direction_needs_geography_support(self):
        assert _reconciles_with_resolved(
            "Land-Grant Brewing", "Land-Grant Brewing Columbus",
            "Columbus", False) is False

    def test_reverse_direction_needs_correct_expected_city(self):
        assert _reconciles_with_resolved(
            "Land-Grant Brewing", "Land-Grant Brewing Columbus",
            "Dublin", True) is False


# --------------------------------------------------------------------------- #
# Full live replay through the production pipeline.
# --------------------------------------------------------------------------- #

def test_live_landgrant_replay_no_conflict_review_for_address_only(tmp_path):
    """The exact live failure: single short-form LLM name + branded OG title
    + operator hint must yield NO name conflict and exactly the
    missing-address reason."""
    c = _run_live_replay(tmp_path)
    p = dict(c.proposed_fields)

    assert p["name"] == "Land-Grant Brewing Columbus"
    assert p["address"] == ""

    # All live name evidence preserved: the branded OG title, the short
    # brand form, and the full entity name (the LLM evidence's quote).
    name_evidence = [e for e in c.evidence if e.field_name == "name"]
    values = {e.proposed_value for e in name_evidence}
    assert "FAQ | Land-Grant Brewing Columbus | Hours, Parking & More" in values
    assert "Land-Grant Brewing" in values
    wordings = {e.source_wording for e in name_evidence}
    assert "Land-Grant Brewing Columbus" in wordings
    sources = {w for e in name_evidence for w in e.warnings}
    assert "name_source:OPEN_GRAPH" in sources
    assert "name_source:LLM_TEXT" in sources

    # Supported pet facts unchanged from the live run.
    facts = dict(c.pet_facts)
    assert facts.get("pets_allowed") == "true"
    assert facts.get("patio_or_outdoor_only") == "true"
    assert facts.get("permitted_area") == "beer garden and patio"
    assert facts.get("indoor_prohibited") == "true"
    assert facts.get("water_or_treats") == "true"
    assert facts.get("seasonal_or_weather_caveat") == (
        "Beer Garden operations are weather dependent")

    # The repaired semantics.
    assert not any(cf.field_name == "name" for cf in c.conflicts)
    assert not c.conflicts
    assert c.ambiguous_fields == ()
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert c.recommendation_reasons == ("missing_required_field:address",)


def test_live_replay_wrong_expected_city_still_conflicts(tmp_path):
    """Safety: the same live shape with expected_city=Dublin must keep the
    name conflict (the trailing 'Columbus' qualifier is never blessed)."""
    c = _run_live_replay(tmp_path, expected_city="Dublin")
    assert any(cf.field_name == "name" for cf in c.conflicts)
    assert C.REASON_CONFLICTING_EVIDENCE in c.recommendation_reasons

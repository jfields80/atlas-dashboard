"""AES-DATA-001 -- expected-city trailing qualifier and resolved-name
reconciliation (final restaurant-name defect). After the authoritative name
is resolved, every remaining candidate reconciles against THAT name --
branded titles through the page-purpose stripping rules first, and a
brand-short form via the context-bound expected-city suffix rule. The rule
never fires without expected-city/geography context, so genuinely different
names, competing city qualifiers, wrong expected cities, and unsupported
page geography all still conflict. No network; address never synthesized."""

from __future__ import annotations

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext


# --------------------------------------------------------------------------- #
# Context-bound rule unit tests.
# --------------------------------------------------------------------------- #

class TestExpectedCitySuffixRule:
    def test_authoritative_name_plus_expected_city_suffix(self):
        assert N.expected_city_suffix_compatible(
            "Land-Grant Brewing Columbus", "Land-Grant Brewing",
            "Columbus", True) is True

    @pytest.mark.parametrize("resolved,alternate", [
        # Competing city qualifier is never a short form.
        ("Land-Grant Brewing Columbus", "Land-Grant Brewing Cleveland"),
        # Different base entity, same city qualifier.
        ("Land-Grant Brewing Columbus", "Land-Grant Hotel Columbus"),
        # Genuinely different names, no qualifier involved.
        ("Land-Grant Brewing", "Seventh Son Brewing"),
        # Leading city is NOT a trailing qualifier -- no generic stripping.
        ("Columbus Brewing Company", "Brewing Company"),
    ])
    def test_negative_pairs_remain_incompatible(self, resolved, alternate):
        assert N.expected_city_suffix_compatible(
            resolved, alternate, "Columbus", True) is False

    def test_incorrect_expected_city_remains_conflicting(self):
        # expected_city=Dublin never blesses a trailing "Columbus".
        assert N.expected_city_suffix_compatible(
            "Land-Grant Columbus", "Land-Grant", "Dublin", True) is False

    def test_unsupported_geography_remains_conflicting(self):
        assert N.expected_city_suffix_compatible(
            "Land-Grant Brewing Columbus", "Land-Grant Brewing",
            "Columbus", False) is False

    def test_missing_expected_city_context_remains_conflicting(self):
        assert N.expected_city_suffix_compatible(
            "Land-Grant Brewing Columbus", "Land-Grant Brewing",
            "", True) is False

    def test_city_only_resolved_name_never_matches(self):
        # base must be non-empty; a bare city is not a brand.
        assert N.expected_city_suffix_compatible(
            "Columbus", "Columbus", "Columbus", True) is False


# --------------------------------------------------------------------------- #
# Pipeline fixture (live Land-Grant shape: branded OG title + full LLM name
# + shorter LLM brand form).
# --------------------------------------------------------------------------- #

_URL = "https://landgrantbrewing.com/faq/"


def _run(tmp_path, *, second_name="Land-Grant Brewing", expected_city="Columbus",
         extra_body=""):
    html = (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="FAQ | Land-Grant Brewing Columbus '
        '| Hours, Parking &amp; More">'
        '<meta property="og:url" content="https://landgrantbrewing.com/">'
        "</head><body><h1>Land-Grant Brewing Columbus</h1>"
        "<p>%s</p>"
        "<p>Dogs are welcome in the beer garden and on the patio. Dogs are not "
        "permitted indoors.</p>%s"
        "</body></html>" % (second_name, extra_body))
    fetcher = StaticPageFetcher()
    fetcher.add_html(_URL, html)
    facts = [
        {"field": "name", "value": "Land-Grant Brewing Columbus",
         "quote": "Land-Grant Brewing Columbus"},
        {"field": "name", "value": second_name, "quote": second_name},
        {"field": "pets_allowed", "value": "true",
         "quote": "Dogs are welcome in the beer garden and on the patio"},
        {"field": "patio_or_outdoor_only", "value": "true",
         "quote": "Dogs are welcome in the beer garden and on the patio"},
        {"field": "indoor_prohibited", "value": "true",
         "quote": "Dogs are not permitted indoors"},
    ]
    extractor = StaticFactExtractor({"facts": facts})
    cas = ArtifactStoreRepository(tmp_path / "cas")
    ctx = ImportContext(category="restaurants", expected_city=expected_city,
                        expected_state="OH")
    return run_import(_URL, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-16", created_at="1970-01-01T00:00:00")


class TestResolvedNameReconciliation:
    def test_shorter_brand_form_accepted_no_conflict(self, tmp_path):
        c = _run(tmp_path)
        assert dict(c.proposed_fields)["name"] == "Land-Grant Brewing Columbus"
        assert not any(cf.field_name == "name" for cf in c.conflicts)

    def test_raw_branded_og_title_reconciled_through_resolved_name(self, tmp_path):
        # The branded OG title reconciles to the resolved authoritative name
        # via page-purpose stripping; it is never compared raw against the
        # shorter alternate -- so all three candidates coexist conflict-free,
        # with every name_source marker preserved.
        c = _run(tmp_path)
        name_evidence = [e for e in c.evidence if e.field_name == "name"]
        values = {e.proposed_value for e in name_evidence}
        assert "FAQ | Land-Grant Brewing Columbus | Hours, Parking & More" in values
        assert "Land-Grant Brewing Columbus" in values
        assert "Land-Grant Brewing" in values
        sources = {w for e in name_evidence for w in e.warnings}
        assert "name_source:OPEN_GRAPH" in sources
        assert "name_source:LLM_TEXT" in sources
        assert not any(cf.field_name == "name" for cf in c.conflicts)

    def test_different_city_alternate_remains_conflicting(self, tmp_path):
        c = _run(tmp_path, second_name="Land-Grant Brewing Cleveland")
        assert any(cf.field_name == "name" for cf in c.conflicts)
        assert c.recommendation == C.RECOMMEND_REVIEW
        assert C.REASON_CONFLICTING_EVIDENCE in c.recommendation_reasons

    def test_incorrect_expected_city_remains_conflicting(self, tmp_path):
        # Operator expects Dublin; the trailing "Columbus" qualifier is not
        # blessed, so the shorter form still conflicts.
        c = _run(tmp_path, expected_city="Dublin")
        assert any(cf.field_name == "name" for cf in c.conflicts)
        assert c.recommendation == C.RECOMMEND_REVIEW

    def test_conflicting_page_geography_remains_conflicting(self, tmp_path):
        # The page's own structured city contradicts the expected city ->
        # geography support is withdrawn -> the short form is not blessed.
        jsonld = (
            '<script type="application/ld+json">'
            '{"@context": "https://schema.org", "@type": "Restaurant", '
            '"address": {"@type": "PostalAddress", '
            '"addressLocality": "Cleveland", "addressRegion": "OH"}}'
            "</script>")
        c = _run(tmp_path, extra_body=jsonld)
        assert any(cf.field_name == "name" for cf in c.conflicts)
        assert c.recommendation == C.RECOMMEND_REVIEW

    def test_generic_base_leading_city_remains_conflicting(self, tmp_path):
        # "Brewing Company" is not a short form of "Land-Grant Brewing
        # Columbus" -- a partial/generic base never reconciles.
        c = _run(tmp_path, second_name="Brewing Company")
        assert any(cf.field_name == "name" for cf in c.conflicts)


def test_land_grant_full_candidate_review_for_missing_address_only(tmp_path):
    """Expected live rerun result: correct name, no name conflict, no
    ambiguity, address genuinely absent (never synthesized), supported pet
    facts unchanged, REVIEW with the single missing-address reason."""
    c = _run(tmp_path)
    p = dict(c.proposed_fields)
    assert p["name"] == "Land-Grant Brewing Columbus"
    assert p["address"] == ""
    facts = dict(c.pet_facts)
    assert facts.get("pets_allowed") == "true"
    assert facts.get("patio_or_outdoor_only") == "true"
    assert facts.get("indoor_prohibited") == "true"
    assert not c.conflicts
    assert c.ambiguous_fields == ()
    assert not any(e.support_state == C.SUPPORT_AMBIGUOUS for e in c.evidence)
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert c.recommendation_reasons == ("missing_required_field:address",)

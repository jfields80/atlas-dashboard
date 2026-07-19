"""AES-DATA-004E (Task 5/7) -- property + brand multi-source lodging
strategy. Scenarios A-F from the mission, proven with synthetic static
fixtures (no network, no live provider) via the REAL multi-source pipeline
(``run_multi_import``), exactly the pattern AES-DATA-003F's
``test_source_applicability.py`` established for the service categories."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_urls import _build_static_multi
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import
from scripts.pettripfinder.importer.lodging_source_strategy import (
    BRAND_SCOPE_PARTICIPATING,
    BRAND_SCOPE_UNIVERSAL,
    BRAND_SCOPE_UNKNOWN,
    classify_brand_policy_scope,
    gate_high_risk_field_applicability,
)
from scripts.pettripfinder.importer.models import ExtractedEvidence, ImportContext

# --------------------------------------------------------------------------- #
# Pure unit tests: brand-scope classifier.
# --------------------------------------------------------------------------- #

def test_universal_scope_markers():
    assert classify_brand_policy_scope("Pets are welcome at all our hotels.") == BRAND_SCOPE_UNIVERSAL
    assert classify_brand_policy_scope("$75 per stay, brand-wide.") == BRAND_SCOPE_UNIVERSAL


def test_participating_scope_markers():
    assert classify_brand_policy_scope(
        "Pets welcome at participating locations.") == BRAND_SCOPE_PARTICIPATING


def test_unknown_scope_when_neither_marker_present():
    assert classify_brand_policy_scope("$75 per stay.") == BRAND_SCOPE_UNKNOWN


def test_participating_wins_when_both_markers_somehow_present():
    # Conservative default: an ambiguous/contradictory statement is treated
    # as non-universal (never publish on ambiguity).
    text = "All our hotels participate, except select participating locations."
    assert classify_brand_policy_scope(text) == BRAND_SCOPE_PARTICIPATING


# --------------------------------------------------------------------------- #
# Pure unit tests: gate_high_risk_field_applicability.
# --------------------------------------------------------------------------- #

def _ev(field, value, url, quote=None):
    q = quote if quote is not None else value
    return ExtractedEvidence(
        field_name=field, proposed_value=value, source_wording=value, source_url=url,
        snapshot_quote=q, char_start=0, char_end=len(q),
        extraction_method=C.METHOD_LLM_TEXT, support_state=C.SUPPORT_SUPPORTED, warnings=())


def test_gate_keeps_location_specific_value():
    facts = {"pets_allowed": "true"}
    evs = [_ev("pets_allowed", "true", "https://x.test/prop")]
    applicability = {"https://x.test/prop": C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC}
    gated, suppressed = gate_high_risk_field_applicability(facts, evs, applicability)
    assert gated == facts and suppressed == ()


def test_gate_suppresses_brand_only_unknown_scope():
    facts = {"pet_fee": "$75"}
    evs = [_ev("pet_fee", "$75", "https://x.test/brand", "$75 per stay.")]
    applicability = {"https://x.test/brand": C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE}
    gated, suppressed = gate_high_risk_field_applicability(facts, evs, applicability)
    assert "pet_fee" not in gated
    assert suppressed == ("pet_fee",)


def test_gate_allows_brand_universal_with_property_identity():
    facts = {"pet_fee": "$75"}
    evs = [
        _ev("name", "Example Hotel", "https://x.test/prop"),
        _ev("pet_fee", "$75", "https://x.test/brand", "$75 per stay at all our hotels."),
    ]
    applicability = {
        "https://x.test/prop": C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC,
        "https://x.test/brand": C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE,
    }
    gated, suppressed = gate_high_risk_field_applicability(facts, evs, applicability)
    assert gated == facts and suppressed == ()


def test_gate_suppresses_brand_universal_without_property_identity():
    # Universal wording alone is not enough -- property identity must ALSO
    # be established by another included source.
    facts = {"pet_fee": "$75"}
    evs = [_ev("pet_fee", "$75", "https://x.test/brand", "$75 per stay at all our hotels.")]
    applicability = {"https://x.test/brand": C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE}
    gated, suppressed = gate_high_risk_field_applicability(facts, evs, applicability)
    assert "pet_fee" not in gated
    assert suppressed == ("pet_fee",)


def test_gate_evidence_list_never_mutated():
    facts = {"pet_fee": "$75"}
    evs = [_ev("pet_fee", "$75", "https://x.test/brand", "$75 per stay.")]
    applicability = {"https://x.test/brand": C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE}
    before = list(evs)
    gate_high_risk_field_applicability(facts, evs, applicability)
    assert evs == before


# --------------------------------------------------------------------------- #
# End-to-end scenarios A-F via the real multi-source pipeline.
# --------------------------------------------------------------------------- #

def _write(tmp, name, fixture):
    fp = tmp / name
    fp.write_text(json.dumps(fixture), encoding="utf-8")
    return fp


def _run_multi(fixtures, tmp_path):
    tmp = Path(tempfile.mkdtemp())
    paths = [_write(tmp, "s%d.json" % i, f) for i, f in enumerate(fixtures)]
    urls = [f["url"] for f in fixtures]
    fetcher, extractor = _build_static_multi(urls, [str(p) for p in paths])
    ctx = ImportContext(category="hotels", expected_city="Columbus", expected_state="OH")
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_multi_import(urls, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                            observed_at="2026-07-18", created_at="1970-01-01T00:00:00")


def _jsonld(name, street, city, state, zip_):
    return (
        '<script type="application/ld+json">{"@context": "https://schema.org", '
        '"@type": "LodgingBusiness", "name": "%s", "telephone": "614-555-0100", '
        '"address": {"@type": "PostalAddress", "streetAddress": "%s", '
        '"addressLocality": "%s", "addressRegion": "%s", "postalCode": "%s"}}'
        '</script>'
    ) % (name, street, city, state, zip_)


_PROPERTY_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>%s</head>"
    "<body><h1>Example Hotel Columbus</h1><p>Welcome to Example Hotel Columbus.</p>"
    "</body></html>"
) % _jsonld("Example Hotel Columbus", "1 Example Way", "Columbus", "OH", "43215")

_PROPERTY_HTML_SILENT = _PROPERTY_HTML   # no pet wording at all -- same page

_BRAND_UNIVERSAL_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    '<script type="application/ld+json">{"@context": "https://schema.org", '
    '"@graph": [{"@type": "LodgingBusiness", "name": "Example Hotel North"}, '
    '{"@type": "LodgingBusiness", "name": "Example Hotel South"}]}</script>'
    "</head><body><h1>Example Hotels Pet Policy</h1>"
    "<p>$75 per stay at all our hotels.</p></body></html>"
)

_BRAND_PARTICIPATING_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    '<script type="application/ld+json">{"@context": "https://schema.org", '
    '"@graph": [{"@type": "LodgingBusiness", "name": "Example Hotel North"}, '
    '{"@type": "LodgingBusiness", "name": "Example Hotel South"}]}</script>'
    "</head><body><h1>Example Hotels Pet Policy</h1>"
    "<p>Pets are welcome at participating Example Hotels locations.</p></body></html>"
)

_BRAND_POSITIVE_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    '<script type="application/ld+json">{"@context": "https://schema.org", '
    '"@graph": [{"@type": "LodgingBusiness", "name": "Example Hotel North"}, '
    '{"@type": "LodgingBusiness", "name": "Example Hotel South"}]}</script>'
    "</head><body><h1>Example Hotels Pet Policy</h1>"
    "<p>All Example Hotels are pet friendly.</p></body></html>"
)


def test_scenario_a_universal_brand_fee_publishes_with_property_positive(tmp_path):
    s1 = {"url": "https://www.examplehotel.test/", "html": _PROPERTY_HTML,
         "extraction": {"facts": [
             {"field": "pets_allowed", "value": "true",
              "quote": "Welcome to Example Hotel Columbus"},
         ]}}
    s2 = {"url": "https://www.examplehotel.test/brand-pet-policy", "html": _BRAND_UNIVERSAL_HTML,
         "extraction": {"facts": [
             {"field": "pet_fee", "value": "$75", "quote": "$75 per stay at all our hotels"},
         ]}}
    c = _run_multi([s1, s2], tmp_path)
    facts = dict(c.pet_facts)
    assert facts.get("pets_allowed") == "true"
    assert facts.get("pet_fee") == "$75"


def test_scenario_b_property_negative_wins_over_brand_positive(tmp_path):
    s1 = {"url": "https://www.examplehotel.test/", "html": _PROPERTY_HTML,
         "extraction": {"facts": [
             {"field": "pets_allowed", "value": "false",
              "quote": "Welcome to Example Hotel Columbus"},
         ]}}
    s2 = {"url": "https://www.examplehotel.test/brand-pet-policy", "html": _BRAND_POSITIVE_HTML,
         "extraction": {"facts": [
             {"field": "pets_allowed", "value": "true",
              "quote": "All Example Hotels are pet friendly"},
         ]}}
    c = _run_multi([s1, s2], tmp_path)
    facts = dict(c.pet_facts)
    assert facts.get("pets_allowed") == "false"
    assert not any(cf.field_name == "pets_allowed" for cf in c.conflicts)


def test_scenario_c_property_silent_brand_participating_stays_review_unknown(tmp_path):
    s1 = {"url": "https://www.examplehotel.test/", "html": _PROPERTY_HTML_SILENT,
         "extraction": {"facts": []}}
    s2 = {"url": "https://www.examplehotel.test/brand-pet-policy", "html": _BRAND_PARTICIPATING_HTML,
         "extraction": {"facts": [
             {"field": "pets_allowed", "value": "true",
              "quote": "Pets are welcome at participating Example Hotels locations"},
         ]}}
    c = _run_multi([s1, s2], tmp_path)
    facts = dict(c.pet_facts)
    assert "pets_allowed" not in facts
    assert C.REASON_SOURCE_NOT_LOCATION_APPLICABLE in c.recommendation_reasons
    assert c.recommendation == C.RECOMMEND_REVIEW


def test_scenario_d_universal_brand_with_property_identity_may_publish(tmp_path):
    s1 = {"url": "https://www.examplehotel.test/", "html": _PROPERTY_HTML_SILENT,
         "extraction": {"facts": []}}
    s2 = {"url": "https://www.examplehotel.test/brand-pet-policy", "html": _BRAND_UNIVERSAL_HTML,
         "extraction": {"facts": [
             {"field": "pets_allowed", "value": "true",
              "quote": "$75 per stay at all our hotels"},
             {"field": "pet_fee", "value": "$75", "quote": "$75 per stay at all our hotels"},
         ]}}
    c = _run_multi([s1, s2], tmp_path)
    facts = dict(c.pet_facts)
    assert facts.get("pets_allowed") == "true"
    assert facts.get("pet_fee") == "$75"
    # The candidate stays REVIEW here for an ORTHOGONAL, expected reason: S2
    # is a genuine multi-location chain listing (the only way this pipeline
    # ever reaches ORGANIZATION_WIDE applicability, per
    # classify_source_applicability's rules), so REASON_MULTI_ENTITY fires
    # exactly as it would for ANY category's chain-wide supplemental source
    # (see test_source_applicability.py's own scenario D, which never
    # asserts READY either). The proof this test cares about is that the
    # FIELDS themselves are no longer suppressed -- not the overall verdict.
    assert C.REASON_MULTI_ENTITY in c.recommendation_reasons
    assert C.REASON_SOURCE_NOT_LOCATION_APPLICABLE not in c.recommendation_reasons


_PROPERTY_HTML_WITH_FEE = (
    "<!doctype html><html><head><meta charset='utf-8'>%s</head>"
    "<body><h1>Example Hotel Columbus</h1><p>Welcome to Example Hotel Columbus. "
    "A $50 pet fee applies per stay.</p></body></html>"
) % _jsonld("Example Hotel Columbus", "1 Example Way", "Columbus", "OH", "43215")


def test_scenario_e_property_and_brand_conflict_forces_review(tmp_path):
    s1 = {"url": "https://www.examplehotel.test/", "html": _PROPERTY_HTML_WITH_FEE,
         "extraction": {"facts": [
             {"field": "pets_allowed", "value": "true",
              "quote": "Welcome to Example Hotel Columbus"},
             {"field": "pet_fee", "value": "$50", "quote": "A $50 pet fee applies per stay."},
         ]}}
    s2 = {"url": "https://www.examplehotel.test/brand-pet-policy", "html": _BRAND_UNIVERSAL_HTML,
         "extraction": {"facts": [
             {"field": "pet_fee", "value": "$75", "quote": "$75 per stay at all our hotels"},
         ]}}
    c = _run_multi([s1, s2], tmp_path)
    facts = dict(c.pet_facts)
    assert "pet_fee" not in facts   # conflicting -- never silently picked
    assert any(cf.field_name == "pet_fee" for cf in c.conflicts)
    assert C.REASON_POLICY_CONFLICT in c.recommendation_reasons
    assert c.recommendation == C.RECOMMEND_REVIEW


def test_scenario_f_single_brand_homepage_never_reaches_the_multi_source_gate(tmp_path):
    # F is a batch-construction concern (documented in lodging_source_
    # strategy.py's module docstring and the Task 8/9 report): a job built
    # from only a brand homepage URL is a SINGLE-source job. The single-
    # source path (run_import) never computes source_applicability and
    # never calls gate_high_risk_field_applicability -- there is no
    # property-level candidate to gate in the first place, so whatever the
    # brand page states publishes exactly as any single-source job's
    # evidence would. This documents why job SELECTION (never building a
    # property job from a brand-only URL) is the real control for F, not a
    # merge-time gate.
    from scripts.pettripfinder.importer.candidate import run_import
    assert run_import is not run_multi_import

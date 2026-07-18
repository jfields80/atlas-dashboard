"""AES-DATA-003F -- source applicability and high-risk capability gating
(Tasks 1-5, 8-10). Hardens the two recurring live defects found in
AES-DATA-003E: a chain-wide official page contributing a location-specific
high-risk capability without proving applicability, and (covered in
test_entity_name_normalization.py) title-tag marketing suffixes causing
false identity conflicts. All fixtures here are synthetic, inline static
test pages -- no copied live content, no network, no live provider calls."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.import_official_urls import _build_static_multi
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import
from scripts.pettripfinder.importer.candidate import (
    classify_source_applicability,
    run_import,
)
from scripts.pettripfinder.importer.domain_packs.base import CapabilityState
from scripts.pettripfinder.importer.domain_packs.projection import (
    CapabilityProjectionRule,
    has_inapplicable_high_risk_capability,
    project_capabilities,
)
from scripts.pettripfinder.importer.models import ExtractedEvidence, ImportContext
from scripts.pettripfinder.importer.review_report import render_report_html


def _ev(field, value, url):
    return ExtractedEvidence(
        field_name=field, proposed_value=value, source_wording=value, source_url=url,
        snapshot_quote=value, char_start=0, char_end=len(value),
        extraction_method=C.METHOD_LLM_TEXT, support_state=C.SUPPORT_SUPPORTED, warnings=())


# --------------------------------------------------------------------------- #
# Task 9 (applicability): classify_source_applicability unit tests.
# --------------------------------------------------------------------------- #

def test_matching_city_is_location_specific():
    r = classify_source_applicability(
        source_url="https://x.test/loc", accepted={"city": "Columbus", "state": "OH"},
        expected_city="Columbus", expected_state="OH", multi_entity=False)
    assert r == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC


def test_conflicting_address_prevents_applicability():
    r = classify_source_applicability(
        source_url="https://x.test/loc", accepted={"city": "Hilliard", "state": "OH"},
        expected_city="Columbus", expected_state="OH", multi_entity=False)
    assert r == C.SOURCE_APPLICABILITY_UNKNOWN


def test_matching_city_alone_not_always_sufficient_state_must_agree():
    # Same city name, contradicting state -- never LOCATION_SPECIFIC.
    r = classify_source_applicability(
        source_url="https://x.test/loc", accepted={"city": "Columbus", "state": "IN"},
        expected_city="Columbus", expected_state="OH", multi_entity=False)
    assert r == C.SOURCE_APPLICABILITY_UNKNOWN


def test_root_url_alone_does_not_determine_applicability():
    # No city stated, not multi_entity -- the URL shape (root vs subpage)
    # never enters the decision; both resolve the same way.
    root = classify_source_applicability(
        source_url="https://x.test/", accepted={},
        expected_city="Columbus", expected_state="OH", multi_entity=False)
    subpage = classify_source_applicability(
        source_url="https://x.test/emergency", accepted={},
        expected_city="Columbus", expected_state="OH", multi_entity=False)
    assert root == subpage == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC


def test_multi_entity_with_no_matching_city_is_organization_wide():
    r = classify_source_applicability(
        source_url="https://x.test/services", accepted={},
        expected_city="Columbus", expected_state="OH", multi_entity=True)
    assert r == C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE


def test_multi_entity_with_matching_url_path_recovers_location_specific():
    r = classify_source_applicability(
        source_url="https://x.test/columbus/services", accepted={},
        expected_city="Columbus", expected_state="OH", multi_entity=True)
    assert r == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC


def test_applicability_is_deterministic():
    kwargs = dict(source_url="https://x.test/a", accepted={"city": "Columbus", "state": "OH"},
                 expected_city="Columbus", expected_state="OH", multi_entity=False)
    assert classify_source_applicability(**kwargs) == classify_source_applicability(**kwargs)


def test_source_ordering_does_not_change_applicability():
    # The classifier is a pure per-source function -- calling it for two
    # sources in either order never changes either result.
    a = classify_source_applicability(
        source_url="https://x.test/a", accepted={"city": "Columbus", "state": "OH"},
        expected_city="Columbus", expected_state="OH", multi_entity=False)
    b = classify_source_applicability(
        source_url="https://x.test/b", accepted={}, expected_city="Columbus",
        expected_state="OH", multi_entity=True)
    b2 = classify_source_applicability(
        source_url="https://x.test/b", accepted={}, expected_city="Columbus",
        expected_state="OH", multi_entity=True)
    a2 = classify_source_applicability(
        source_url="https://x.test/a", accepted={"city": "Columbus", "state": "OH"},
        expected_city="Columbus", expected_state="OH", multi_entity=False)
    assert (a, b) == (a2, b2)


# --------------------------------------------------------------------------- #
# Task 9: project_capabilities applicability-gate unit tests.
# --------------------------------------------------------------------------- #

_RULES = (
    CapabilityProjectionRule("walk_ins_accepted", "walk_ins_accepted", "bool", high_risk=True),
    CapabilityProjectionRule("grooming_offered", "grooming_offered", "bool", high_risk=False),
)


def test_chain_wide_high_risk_claim_is_suppressed():
    caps = project_capabilities(
        {"walk_ins_accepted": "true"}, (_ev("walk_ins_accepted", "true", "https://x.test/chain"),),
        _RULES, source_applicability={"https://x.test/chain": C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE})
    assert caps[0].state == CapabilityState.UNKNOWN.value
    assert caps[0].high_risk is True
    assert caps[0].evidence_index == 0   # evidence preserved, never dropped
    assert has_inapplicable_high_risk_capability(caps) is True


def test_location_specific_high_risk_claim_is_supported():
    caps = project_capabilities(
        {"walk_ins_accepted": "true"}, (_ev("walk_ins_accepted", "true", "https://x.test/loc"),),
        _RULES, source_applicability={"https://x.test/loc": C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC})
    assert caps[0].state == CapabilityState.SUPPORTED.value
    assert has_inapplicable_high_risk_capability(caps) is False


def test_non_high_risk_capability_never_suppressed():
    caps = project_capabilities(
        {"grooming_offered": "true"}, (_ev("grooming_offered", "true", "https://x.test/chain"),),
        _RULES, source_applicability={"https://x.test/chain": C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE})
    assert caps[0].state == CapabilityState.SUPPORTED.value


def test_unknown_url_in_populated_map_does_not_suppress():
    # A URL simply absent from the map (vs positively classified) must
    # never itself suppress -- only an explicit non-LOCATION_SPECIFIC entry.
    caps = project_capabilities(
        {"walk_ins_accepted": "true"}, (_ev("walk_ins_accepted", "true", "https://x.test/other"),),
        _RULES, source_applicability={"https://different.test/": C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE})
    assert caps[0].state == CapabilityState.SUPPORTED.value


# --------------------------------------------------------------------------- #
# Task 8/9: end-to-end single-source scenarios (fixtures 1, 4, 7, 8).
# --------------------------------------------------------------------------- #

def _run_single(html, facts, category, expected_city, expected_state, tmp_path,
                url="https://www.example-clinic.test/"):
    fixture = {
        "url": url,
        "context": {"category": category, "expected_city": expected_city,
                    "expected_state": expected_state},
        "html": html, "extraction": {"facts": facts},
    }
    fp = Path(tempfile.mkdtemp()) / "fixture.json"
    fp.write_text(json.dumps(fixture), encoding="utf-8")
    fetcher, extractor = _build_static(url, str(fp))
    ctx = ImportContext(**fixture["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at="1970-01-01T00:00:00")


def _jsonld(name, street, city, state, zip_, business_type="LocalBusiness"):
    return (
        '<script type="application/ld+json">{"@context": "https://schema.org", '
        '"@type": "%s", "name": "%s", "telephone": "614-555-0100", '
        '"address": {"@type": "PostalAddress", "streetAddress": "%s", '
        '"addressLocality": "%s", "addressRegion": "%s", "postalCode": "%s"}}'
        '</script>'
    ) % (business_type, name, street, city, state, zip_)


def test_fixture_1_location_specific_grooming_page_supports_walk_ins(tmp_path):
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>%s</head>"
        "<body><h1>Fixed Groom Co</h1><p>We offer dog grooming. Walk-ins are "
        "accepted at this location.</p></body></html>"
    ) % _jsonld("Fixed Groom Co", "1 Fixed St", "Columbus", "OH", "43215")
    c = _run_single(html, [
        {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
        {"field": "walk_ins_accepted", "value": "true",
         "quote": "Walk-ins are accepted at this location"},
    ], "grooming", "Columbus", "OH", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state == "SUPPORTED"
    assert c.recommendation == C.RECOMMEND_READY


def test_fixture_4_independent_single_location_homepage_supports_high_risk(tmp_path):
    # No JSON-LD address at all -- an independent single-location business's
    # homepage, identified only via H1 -- still supports a high-risk claim
    # (Task 3).
    html = (
        "<!doctype html><html><body><h1>Solo Groom Shop</h1>"
        "<p>We offer dog grooming. Walk-ins welcome.</p></body></html>"
    )
    c = _run_single(html, [
        {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
        {"field": "walk_ins_accepted", "value": "true", "quote": "Walk-ins welcome"},
    ], "grooming", "Columbus", "OH", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state == "SUPPORTED"


def test_fixture_7_veterinary_root_homepage_matching_location_supports_high_risk(tmp_path):
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>%s</head>"
        "<body><h1>Columbus Vet Clinic</h1><p>We provide emergency veterinary "
        "services 24 hours a day.</p></body></html>"
    ) % _jsonld("Columbus Vet Clinic", "1 Vet Way", "Columbus", "OH", "43215", "VeterinaryCare")
    c = _run_single(html, [
        {"field": "emergency_service", "value": "true",
         "quote": "We provide emergency veterinary services"},
        {"field": "open_24h", "value": "true", "quote": "24 hours a day"},
    ], "veterinary", "Columbus", "OH", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["emergency_service"].state == "SUPPORTED"
    assert by_id["open_24h"].state == "SUPPORTED"
    assert c.recommendation == C.RECOMMEND_READY


def test_fixture_8_multi_location_root_homepage_no_selected_location_evidence(tmp_path):
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        '<script type="application/ld+json">{"@context": "https://schema.org", '
        '"@graph": [{"@type": "LocalBusiness", "name": "ChainGroom North", '
        '"address": {"@type": "PostalAddress", "streetAddress": "1 North St", '
        '"addressLocality": "Dublin", "addressRegion": "OH"}}, '
        '{"@type": "LocalBusiness", "name": "ChainGroom South", '
        '"address": {"@type": "PostalAddress", "streetAddress": "2 South St", '
        '"addressLocality": "Hilliard", "addressRegion": "OH"}}]}</script>'
        "</head><body><h1>ChainGroom</h1><p>We offer dog grooming. Walk-ins "
        "accepted at all locations.</p></body></html>"
    )
    c = _run_single(html, [
        {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
        {"field": "walk_ins_accepted", "value": "true",
         "quote": "Walk-ins accepted at all locations"},
    ], "grooming", "Columbus", "OH", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["grooming_offered"].state == "SUPPORTED"           # non-high-risk unaffected
    assert by_id["walk_ins_accepted"].state == "UNKNOWN"             # high-risk suppressed
    assert C.REASON_SOURCE_NOT_LOCATION_APPLICABLE in c.recommendation_reasons
    assert c.recommendation == C.RECOMMEND_REVIEW


# --------------------------------------------------------------------------- #
# Task 4/8/9: multi-source scenarios A-E (fixtures 2, 3, 5, 6).
# --------------------------------------------------------------------------- #

def _write(tmp, name, fixture):
    fp = tmp / name
    fp.write_text(json.dumps(fixture), encoding="utf-8")
    return fp


def _run_multi(fixtures, category, expected_city, expected_state, tmp_path):
    tmp = Path(tempfile.mkdtemp())
    paths = [_write(tmp, "s%d.json" % i, f) for i, f in enumerate(fixtures)]
    urls = [f["url"] for f in fixtures]
    fetcher, extractor = _build_static_multi(urls, [str(p) for p in paths])
    ctx = ImportContext(category=category, expected_city=expected_city, expected_state=expected_state)
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_multi_import(urls, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                            observed_at="2026-07-18", created_at="1970-01-01T00:00:00")


_LOCATION_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>%s</head>"
    "<body><h1>Fixed Groom Co</h1><p>We offer dog grooming by appointment.</p>"
    "</body></html>"
) % _jsonld("Fixed Groom Co", "1 Fixed St", "Columbus", "OH", "43215")

_CHAIN_WALKIN_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    '<script type="application/ld+json">{"@context": "https://schema.org", '
    '"@graph": [{"@type": "LocalBusiness", "name": "Fixed Groom North"}, '
    '{"@type": "LocalBusiness", "name": "Fixed Groom South"}]}</script>'
    "</head><body><h1>Fixed Groom Co Services</h1><p>Walk-ins are accepted "
    "company-wide.</p></body></html>"
)

_CHAIN_NO_WALKIN_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    '<script type="application/ld+json">{"@context": "https://schema.org", '
    '"@graph": [{"@type": "LocalBusiness", "name": "Fixed Groom North"}, '
    '{"@type": "LocalBusiness", "name": "Fixed Groom South"}]}</script>'
    "</head><body><h1>Fixed Groom Co Services</h1><p>General service "
    "overview for all our locations.</p></body></html>"
)


def test_scenario_a_chain_wide_positive_does_not_override_silence(tmp_path):
    # Location page: appointment required (no walk-in statement at all).
    # Chain-wide page: walk-ins available. walk_ins_accepted must not
    # become location-supported.
    s1 = {"url": "https://www.fixedgroom.test/", "html": _LOCATION_HTML,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
             {"field": "appointment_required", "value": "true",
              "quote": "We offer dog grooming by appointment"},
         ]}}
    s2 = {"url": "https://www.fixedgroom.test/services", "html": _CHAIN_WALKIN_HTML,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "Walk-ins are accepted company-wide"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state != "SUPPORTED"
    assert by_id["appointment_required"].state == "SUPPORTED"


def test_scenario_b_explicit_location_negative_wins_no_fabricated_conflict(tmp_path):
    s1 = {"url": "https://www.fixedgroom.test/", "html": _LOCATION_HTML,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
             {"field": "walk_ins_accepted", "value": "false",
              "quote": "We offer dog grooming by appointment"},
         ]}}
    s2 = {"url": "https://www.fixedgroom.test/services", "html": _CHAIN_WALKIN_HTML,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "Walk-ins are accepted company-wide"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state == "EXPLICITLY_ABSENT"
    assert not any(cf.field_name == "walk_ins_accepted" for cf in c.conflicts)
    assert C.REASON_GROOMING_CAPABILITY_CONFLICT not in c.recommendation_reasons


def test_scenario_c_location_positive_repeated_by_chain_wide_stays_supported(tmp_path):
    s1 = {"url": "https://www.fixedgroom.test/", "html": _LOCATION_HTML,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "We offer dog grooming by appointment"},
         ]}}
    s2 = {"url": "https://www.fixedgroom.test/services", "html": _CHAIN_WALKIN_HTML,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "Walk-ins are accepted company-wide"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state == "SUPPORTED"


def test_scenario_d_chain_wide_only_evidence_stays_conservative(tmp_path):
    s1 = {"url": "https://www.fixedgroom.test/", "html": _LOCATION_HTML,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
         ]}}
    s2 = {"url": "https://www.fixedgroom.test/services", "html": _CHAIN_WALKIN_HTML,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "Walk-ins are accepted company-wide"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state == "UNKNOWN"
    assert by_id["walk_ins_accepted"].evidence_index >= 0   # evidence preserved


def test_scenario_e_independent_single_location_only_source_supported(tmp_path):
    c = _run_single(
        _LOCATION_HTML, [
            {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
            {"field": "walk_ins_accepted", "value": "true",
             "quote": "We offer dog grooming by appointment"},
        ], "grooming", "Columbus", "OH", tmp_path, url="https://www.fixedgroom.test/")
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state == "SUPPORTED"


def test_excluded_identity_source_contributes_nothing(tmp_path):
    foreign_html = (
        "<!doctype html><html><head><meta charset='utf-8'>%s</head>"
        "<body><h1>Totally Different Groomer</h1><p>Walk-ins welcome.</p>"
        "</body></html>"
    ) % _jsonld("Totally Different Groomer", "9 Other St", "Hilliard", "OH", "43026")
    s1 = {"url": "https://www.fixedgroom.test/", "html": _LOCATION_HTML,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
         ]}}
    s2 = {"url": "https://www.totallydifferentgroomer.test/", "html": foreign_html,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true", "quote": "Walk-ins welcome"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)
    ids = {cap.capability_id for cap in c.capabilities}
    assert "walk_ins_accepted" not in ids
    assert any(s.excluded_reason == C.REASON_DIFFERENT_REGISTRABLE_DOMAIN for s in c.sources)


# --------------------------------------------------------------------------- #
# Task 5: source provenance / candidate serialization / report rendering.
# --------------------------------------------------------------------------- #

def test_source_provenance_remains_intact(tmp_path):
    s1 = {"url": "https://www.fixedgroom.test/", "html": _LOCATION_HTML,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
         ]}}
    s2 = {"url": "https://www.fixedgroom.test/services", "html": _CHAIN_WALKIN_HTML,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "Walk-ins are accepted company-wide"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)
    by_id = {s.source_id: s for s in c.sources}
    assert by_id["S1"].applicability == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC
    assert by_id["S2"].applicability == C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE


def test_candidate_serialization_round_trips(tmp_path):
    from scripts.pettripfinder.importer.candidate import candidate_from_dict, dumps_candidate
    s1 = {"url": "https://www.fixedgroom.test/", "html": _LOCATION_HTML,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
         ]}}
    s2 = {"url": "https://www.fixedgroom.test/services", "html": _CHAIN_WALKIN_HTML,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "Walk-ins are accepted company-wide"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)
    blob = dumps_candidate(c)
    restored = candidate_from_dict(json.loads(blob))
    assert dumps_candidate(restored) == blob
    by_id = {s.source_id: s for s in restored.sources}
    assert by_id["S2"].applicability == C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE


def test_report_renders_applicability_reason_safely(tmp_path):
    s1 = {"url": "https://www.fixedgroom.test/", "html": _LOCATION_HTML,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true", "quote": "We offer dog grooming"},
         ]}}
    s2 = {"url": "https://www.fixedgroom.test/services", "html": _CHAIN_WALKIN_HTML,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "Walk-ins are accepted company-wide"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)
    html_out = render_report_html(c, "candidate.json")
    assert "ORGANIZATION_WIDE" in html_out
    assert "source_not_location_applicable" in html_out
    assert "<script" not in html_out
    assert "UNKNOWN" in html_out


# --------------------------------------------------------------------------- #
# Task 10: live scenario reproduction with static input.
# --------------------------------------------------------------------------- #

def test_task10_designer_paws_shape_reproduction(tmp_path):
    """S1: Upper-Arlington-specific page. S2: same-domain, chain-wide
    grooming services page with an explicit "Walk-In Services" statement
    but no Upper Arlington applicability -- reproduces the exact AES-
    DATA-003E live finding with static input."""
    s1_html = (
        "<!doctype html><html><head><meta charset='utf-8'>%s</head>"
        "<body><h1>Designer Paws Salon - Upper Arlington</h1>"
        "<p>Full-service dog and cat grooming, appointment required.</p>"
        "</body></html>"
    ) % _jsonld("Designer Paws Salon", "2824 Fishinger Road", "Columbus", "OH", "43221")
    s2_html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        '<script type="application/ld+json">{"@context": "https://schema.org", '
        '"@graph": [{"@type": "LocalBusiness", "name": "Designer Paws Salon Upper Arlington"}, '
        '{"@type": "LocalBusiness", "name": "Designer Paws Salon Westerville"}, '
        '{"@type": "LocalBusiness", "name": "Designer Paws Salon Dublin"}]}</script>'
        "</head><body><h1>Dog Grooming Services</h1>"
        "<p>Walk-In Services: nail trims and touch-ups available at all "
        "our salons.</p></body></html>"
    )
    s1 = {"url": "https://designerpawssalon.test/upperarlington/", "html": s1_html,
         "extraction": {"facts": [
             {"field": "grooming_offered", "value": "true",
              "quote": "Full-service dog and cat grooming"},
             {"field": "dog_grooming", "value": "true",
              "quote": "Full-service dog and cat grooming"},
             {"field": "cat_grooming", "value": "true",
              "quote": "Full-service dog and cat grooming"},
             {"field": "appointment_required", "value": "true",
              "quote": "appointment required"},
         ]}}
    s2 = {"url": "https://designerpawssalon.test/our-service/dog-grooming/", "html": s2_html,
         "extraction": {"facts": [
             {"field": "walk_ins_accepted", "value": "true",
              "quote": "Walk-In Services: nail trims and touch-ups available"},
         ]}}
    c = _run_multi([s1, s2], "grooming", "Columbus", "OH", tmp_path)

    # Source identity remains accepted as the same organization (S2 is not
    # excluded -- it is the same business's own official content).
    assert len(c.sources) == 2
    assert all(not s.excluded_reason for s in c.sources)

    # S2 applicability is organization-wide (an explicit multi-location
    # signal), never LOCATION_SPECIFIC.
    by_id = {s.source_id: s for s in c.sources}
    assert by_id["S2"].applicability == C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE

    # walk_ins_accepted never becomes location-supported.
    caps = {cap.capability_id: cap for cap in c.capabilities}
    assert caps["walk_ins_accepted"].state != "SUPPORTED"
    assert caps["walk_ins_accepted"].high_risk is True

    # No high-risk conflict is fabricated (there is no genuine disagreement,
    # only an inapplicable source).
    assert C.REASON_GROOMING_CAPABILITY_CONFLICT not in c.recommendation_reasons
    # A deterministic reason records the applicability issue.
    assert C.REASON_SOURCE_NOT_LOCATION_APPLICABLE in c.recommendation_reasons
    # The candidate remains safe: never READY on the strength of the
    # unproven claim.
    assert c.recommendation != C.RECOMMEND_READY


def test_task10_homedog_title_shape_reproduction(tmp_path):
    """Official title combines the clean business name with a marketing
    tagline -- must not create an identity conflict, and the legitimate
    capability-sounding words in the tagline must never alter identity."""
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        '<meta property="og:title" content="Homedog Resort &amp; Daycare | '
        'Dog Boarding &amp; Dog Daycare">'
        '<script type="application/ld+json">{"@context": "https://schema.org", '
        '"@type": "LocalBusiness", "name": "Homedog Resort & Daycare", '
        '"telephone": "614-555-0200", "url": "https://www.homedogresort.test/", '
        '"address": {"@type": "PostalAddress", "streetAddress": "561 Short St", '
        '"addressLocality": "Columbus", "addressRegion": "OH", '
        '"postalCode": "43215"}}</script></head>'
        "<body><h1>Homedog Resort &amp; Daycare</h1>"
        "<p>We offer overnight dog boarding and dog daycare.</p></body></html>"
    )
    c = _run_single(html, [
        {"field": "boarding_offered", "value": "true", "quote": "We offer overnight dog boarding"},
        {"field": "dog_boarding", "value": "true", "quote": "overnight dog boarding"},
    ], "boarding", "Columbus", "OH", tmp_path, url="https://www.homedogresort.test/")

    assert not any(cf.field_name == "name" for cf in c.conflicts)
    assert C.REASON_IDENTITY_CONFLICT not in c.recommendation_reasons
    assert dict(c.proposed_fields)["name"] == "Homedog Resort & Daycare"
    assert c.recommendation == C.RECOMMEND_READY


# --------------------------------------------------------------------------- #
# Task 11: regression re-proofs specific to this phase.
# --------------------------------------------------------------------------- #

def test_legacy_golden_bytes_unchanged():
    from scripts.pettripfinder.importer.candidate import candidate_from_dict, dumps_candidate
    golden_dir = Path(__file__).resolve().parent / "fixtures" / "golden"
    for name in ("golden_drury", "golden_scioto", "golden_landgrant"):
        text = (golden_dir / (name + ".json")).read_text(encoding="utf-8")
        candidate = candidate_from_dict(json.loads(text))
        assert dumps_candidate(candidate) + "\n" == text


def test_veterinary_scenario_still_ready(tmp_path):
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "veterinary"
    obj = json.loads((fixtures_dir / "vet_a_general_practice.json").read_text(encoding="utf-8"))
    fetcher, extractor = _build_static(obj["url"], str(fixtures_dir / "vet_a_general_practice.json"))
    ctx = ImportContext(**obj["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    c = run_import(obj["url"], ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                   observed_at="2026-07-18", created_at="1970-01-01T00:00:00")
    assert c.recommendation == C.RECOMMEND_READY

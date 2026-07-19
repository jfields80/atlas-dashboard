"""AES-DATA-004E (Task 2/7) -- official lodging source-role model. Pure
classification unit tests; no network."""

from __future__ import annotations

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import ExtractedEvidence
from scripts.pettripfinder.importer.official_source_roles import (
    LODGING_SOURCE_ROLE_BRAND_POLICY,
    LODGING_SOURCE_ROLE_MANAGEMENT_COMPANY,
    LODGING_SOURCE_ROLE_PROPERTY_IDENTITY,
    LODGING_SOURCE_ROLE_PROPERTY_POLICY,
    LODGING_SOURCE_ROLE_SUPPLEMENTAL,
    LODGING_SOURCE_ROLE_UNKNOWN,
    assess_source,
    classify_source_role,
    is_official_domain,
)


def _ev(field, url, state=C.SUPPORT_SUPPORTED):
    return ExtractedEvidence(
        field_name=field, proposed_value="x", source_wording="x", source_url=url,
        snapshot_quote="x", char_start=0, char_end=1,
        extraction_method=C.METHOD_LLM_TEXT, support_state=state, warnings=())


def test_property_identity_page_no_pet_wording():
    role = classify_source_role(
        source_url="https://www.examplehotel.test/",
        evidence_for_source=[_ev("name", "https://www.examplehotel.test/"),
                              _ev("address", "https://www.examplehotel.test/")],
        applicability=C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC, has_snapshot=True)
    assert role == LODGING_SOURCE_ROLE_PROPERTY_IDENTITY


def test_property_pet_policy_page():
    role = classify_source_role(
        source_url="https://www.examplehotel.test/pets",
        evidence_for_source=[_ev("pets_allowed", "https://www.examplehotel.test/pets"),
                              _ev("pet_fee", "https://www.examplehotel.test/pets")],
        applicability=C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC, has_snapshot=True)
    assert role == LODGING_SOURCE_ROLE_PROPERTY_POLICY


def test_brand_wide_universal_policy_page():
    role = classify_source_role(
        source_url="https://www.examplehotel.test/brand-pets",
        evidence_for_source=[_ev("pets_allowed", "https://www.examplehotel.test/brand-pets")],
        applicability=C.SOURCE_APPLICABILITY_ORGANIZATION_WIDE, has_snapshot=True)
    assert role == LODGING_SOURCE_ROLE_BRAND_POLICY


def test_brand_wide_participating_locations_page():
    # Scope (universal vs participating) is a SEPARATE axis
    # (lodging_source_strategy.classify_brand_policy_scope); role
    # classification only cares that it's a policy page not proven
    # location-specific.
    role = classify_source_role(
        source_url="https://www.examplehotel.test/brand-pets",
        evidence_for_source=[_ev("pet_fee", "https://www.examplehotel.test/brand-pets")],
        applicability=C.SOURCE_APPLICABILITY_UNKNOWN, has_snapshot=True)
    assert role == LODGING_SOURCE_ROLE_BRAND_POLICY


def test_management_company_property_page():
    role = classify_source_role(
        source_url="https://www.oyorooms.com/12345/",
        evidence_for_source=[_ev("name", "https://www.oyorooms.com/12345/")],
        applicability=C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC, has_snapshot=True)
    assert role == LODGING_SOURCE_ROLE_MANAGEMENT_COMPANY


def test_brand_homepage_only_no_identity_or_policy_signal():
    role = classify_source_role(
        source_url="https://www.examplebrand.test/",
        evidence_for_source=[], applicability=C.SOURCE_APPLICABILITY_UNKNOWN, has_snapshot=True)
    assert role == LODGING_SOURCE_ROLE_SUPPLEMENTAL


def test_no_snapshot_is_unknown():
    role = classify_source_role(
        source_url="https://www.examplehotel.test/",
        evidence_for_source=[], applicability="", has_snapshot=False)
    assert role == LODGING_SOURCE_ROLE_UNKNOWN


def test_unsupported_evidence_never_counts():
    role = classify_source_role(
        source_url="https://www.examplehotel.test/",
        evidence_for_source=[_ev("pets_allowed", "https://www.examplehotel.test/",
                                  state=C.SUPPORT_UNSUPPORTED)],
        applicability=C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC, has_snapshot=True)
    assert role == LODGING_SOURCE_ROLE_SUPPLEMENTAL


def test_is_official_domain():
    assert is_official_domain(C.REL_OFFICIAL_BRAND_DOMAIN) is True
    assert is_official_domain(C.REL_EXACT_ENTITY_DOMAIN) is True
    assert is_official_domain(C.REL_UNKNOWN) is False
    assert is_official_domain(C.REL_THIRD_PARTY) is False
    assert is_official_domain("") is False


def test_assess_source_full_record():
    a = assess_source(
        source_url="https://www.examplehotel.test/pets",
        evidence_for_source=[_ev("pets_allowed", "https://www.examplehotel.test/pets"),
                              _ev("pet_fee", "https://www.examplehotel.test/pets")],
        applicability=C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC, has_snapshot=True,
        source_relationship=C.REL_EXACT_ENTITY_DOMAIN, fetch_status="FETCHABLE",
        cache_reference="abc123")
    assert a.source_role == LODGING_SOURCE_ROLE_PROPERTY_POLICY
    assert a.official_domain is True
    assert set(a.policy_fields_supported) == {"pets_allowed", "pet_fee"}
    assert a.cache_reference == "abc123"

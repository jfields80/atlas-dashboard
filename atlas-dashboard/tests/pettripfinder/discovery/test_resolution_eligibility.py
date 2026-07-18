"""AES-DATA-004C Tasks 9/10 -- missing-website categorization and final
import-eligibility outcome tests."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord, WebsiteResolution
from scripts.pettripfinder.discovery.resolution_eligibility import (
    categorize_missing_website,
    compute_resolution_outcome,
)


def _record(eligibility_state=""):
    return DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                           canonical_category=C.CATEGORY_HOTEL, name="Test",
                           eligibility_state=eligibility_state)


def _resolution(state, domain="example.com"):
    return WebsiteResolution(candidate_id="dc_1", source_provider=C.PROVIDER_GOOGLE_PLACES,
                             original_url="x", normalized_url="x", registrable_domain=domain,
                             resolution_state=state)


def _candidate(source_records=(), city="Columbus", state="OH"):
    return DiscoveryCandidate(candidate_id="dc_1", source_records=source_records,
                              city=city, state=state)


# --------------------------------------------------------------------------- #
# Task 9
# --------------------------------------------------------------------------- #

def test_missing_website_chain_name_resolves_from_brand_locator():
    c = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Hampton Inn Somewhere",
                           normalized_name="hampton inn somewhere")
    assert categorize_missing_website(c, C.SCOPE_IN_SCOPE) == C.MISSING_ACTION_RESOLVE_FROM_BRAND_LOCATOR


def test_missing_website_independent_name_defers():
    c = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Bob's Motel",
                           normalized_name="bobs motel")
    assert categorize_missing_website(c, C.SCOPE_IN_SCOPE) == C.MISSING_ACTION_DEFER_LOW_PRIORITY


def test_missing_website_out_of_scope():
    c = DiscoveryCandidate(candidate_id="dc_1", source_records=(), name="Test", normalized_name="test")
    assert categorize_missing_website(c, C.SCOPE_OUT_OF_SCOPE) == C.MISSING_ACTION_OUT_OF_SCOPE


def test_missing_website_closed():
    c = DiscoveryCandidate(candidate_id="dc_1", source_records=(_record(C.ELIGIBILITY_PERMANENTLY_CLOSED),),
                           name="Test", normalized_name="test")
    assert categorize_missing_website(c, C.SCOPE_IN_SCOPE) == C.MISSING_ACTION_CLOSED_OR_REBRANDED_REVIEW


# --------------------------------------------------------------------------- #
# Task 10
# --------------------------------------------------------------------------- #

def test_ready_for_pet_policy_import():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_READY_FOR_PET_POLICY_IMPORT


def test_ready_with_brand_supplement():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED, "a.com"),
                             _resolution(C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY, "a.com")))
    assert outcome == C.RESOLUTION_READY_WITH_BRAND_SUPPLEMENT


def test_review_identity():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome=C.IDENTITY_UNRESOLVED,
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_REVIEW_IDENTITY


def test_possible_rebrand_never_proceeds_independently_to_ready():
    # Doctrine: "do not create duplicate import jobs for one location" --
    # a POSSIBLE_REBRAND pair must be held for review, not let both sides
    # become independent READY_FOR_PET_POLICY_IMPORT candidates.
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome=C.IDENTITY_POSSIBLE_REBRAND,
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_REVIEW_IDENTITY


def test_shared_complex_distinct_properties_proceeds_independently():
    # Genuine confidence these are two different bookable locations -- no
    # duplicate-import risk, so each proceeds on its own merits.
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome=C.IDENTITY_SHARED_COMPLEX_DISTINCT_PROPERTIES,
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_READY_FOR_PET_POLICY_IMPORT


def test_review_website_conflicting_domains():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "a.com"),
                             _resolution(C.WEBSITE_RES_PROPERTY_URL_PROBABLE, "b.com")))
    assert outcome == C.RESOLUTION_REVIEW_WEBSITE


def test_review_website_fetch_blocked():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_FETCH_BLOCKED),))
    assert outcome == C.RESOLUTION_REVIEW_WEBSITE


def test_missing_official_website():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_MISSING),))
    assert outcome == C.RESOLUTION_MISSING_OFFICIAL_WEBSITE


def test_exclude_out_of_scope_overrides_everything():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_OUT_OF_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_EXCLUDE_OUT_OF_SCOPE


def test_exclude_closed_overrides_everything():
    c = _candidate(source_records=(_record(C.ELIGIBILITY_PERMANENTLY_CLOSED),))
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_EXCLUDE_CLOSED


def test_defer_for_borderline_scope_even_with_confirmed_website():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_BORDERLINE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_DEFER


def test_defer_for_chain_homepage_only_no_property_url():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY),))
    assert outcome == C.RESOLUTION_DEFER


def test_defer_for_third_party_only():
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_THIRD_PARTY_BOOKING_URL),))
    assert outcome == C.RESOLUTION_DEFER


def test_management_company_page_alone_qualifies_as_ready():
    # A confirmed-identity MANAGEMENT_COMPANY_PAGE (Task 8) is a
    # property-level signal on its own, not merely a brand supplement.
    c = _candidate()
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_MANAGEMENT_COMPANY_PAGE),))
    assert outcome == C.RESOLUTION_READY_FOR_PET_POLICY_IMPORT


def test_missing_city_defers_never_produces_invalid_batch_job():
    # Found live in Wave 1: a geographically IN_SCOPE candidate (via
    # coordinates) whose deduped "best record" had no city/state (an OSM
    # element with no addr:city/addr:state tags) -- the importer's own
    # batch schema requires both non-empty, so this must defer rather than
    # produce an invalid job.
    c = _candidate(city="", state="OH")
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_DEFER


def test_missing_state_defers_never_produces_invalid_batch_job():
    c = _candidate(city="Columbus", state="")
    outcome = compute_resolution_outcome(
        c, scope=C.SCOPE_IN_SCOPE, identity_outcome="",
        website_resolutions=(_resolution(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED),))
    assert outcome == C.RESOLUTION_DEFER


def test_never_marks_pet_friendly_no_such_field_exists():
    # Structural proof: the outcome vocabulary itself has no pet-friendly
    # concept -- confirmed by checking the full outcome set.
    assert not any("PET_FRIENDLY" in o for o in C.RESOLUTION_OUTCOMES)

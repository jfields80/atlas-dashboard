"""AES-DATA-004C Task 3 -- identity-conflict resolution tests."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.identity_resolution import (
    classify_identity_relationship,
    group_conflicting_candidates,
    resolve_identity_conflicts,
)
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_records


def rec(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="id1",
               canonical_category=C.CATEGORY_HOTEL, name="Test Hotel")
    base.update(kw)
    return DiscoveryRecord(**base)


def _conflict_pair(name_a, name_b, category_a=C.CATEGORY_HOTEL, category_b=C.CATEGORY_HOTEL):
    a = rec(provider_record_id="a1", name=name_a, canonical_category=category_a,
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1", name=name_b,
           canonical_category=category_b,
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    return deduplicate(normalize_records((a, b)), market_id="columbus-oh")


def test_marriott_and_residence_inn_shared_complex():
    cands = _conflict_pair("Marriott Columbus OSU", "Residence Inn by Marriott Columbus OSU")
    resolutions = resolve_identity_conflicts(cands)
    assert len(resolutions) == 1
    assert resolutions[0][1] == C.IDENTITY_SHARED_COMPLEX_DISTINCT_PROPERTIES


def test_old_and_current_name_possible_rebrand():
    cands = _conflict_pair("Buckeye Inn near OSU Medical Center, Columbus OH I-71",
                           "Buckeye Inn Express")
    resolutions = resolve_identity_conflicts(cands)
    assert resolutions[0][1] == C.IDENTITY_POSSIBLE_REBRAND


def test_hotel_and_conference_center_different_entity():
    cands = _conflict_pair("Drury Plaza Hotel Columbus Downtown", "Nationwide Conference Center")
    resolutions = resolve_identity_conflicts(cands)
    assert resolutions[0][1] == C.IDENTITY_DIFFERENT_ENTITY


def test_hotel_and_restaurant_different_entity():
    cands = _conflict_pair("Drury Plaza Hotel Columbus Downtown", "Bar Louie Nationwide")
    resolutions = resolve_identity_conflicts(cands)
    assert resolutions[0][1] == C.IDENTITY_DIFFERENT_ENTITY


def test_same_chain_different_address_remains_distinct_no_grouping():
    a = rec(provider_record_id="h1", name="Hampton Inn Columbus Dublin",
           address_line="3920 Tuller Rd", city="Dublin", state="OH", postal_code="43017")
    b = rec(provider_record_id="h2", name="Hampton Inn Columbus Easton",
           address_line="4270 Stelzer Rd", city="Columbus", state="OH", postal_code="43219")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    # Never even NEEDS_REVIEW -- no signal fires at all, so no grouping happens.
    assert group_conflicting_candidates(cands) == ()


def test_exact_provider_id_duplicate_merges_before_reaching_this_module():
    a = rec(provider_record_id="dup1", name="Some Hotel")
    b = rec(provider_record_id="dup1", name="Some Hotel")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 1
    assert group_conflicting_candidates(cands) == ()


def test_unresolved_material_conflict_stays_review_for_three_way_group():
    a = rec(provider_record_id="a1", name="Alpha Hotel",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1", name="Beta Suites",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    c = rec(provider_record_id="c1", name="Gamma Inn",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    cands = deduplicate(normalize_records((a, b, c)), market_id="columbus-oh")
    resolutions = resolve_identity_conflicts(cands)
    assert len(resolutions) == 1
    group, outcome = resolutions[0]
    assert len(group) == 3
    assert outcome == C.IDENTITY_UNRESOLVED
    assert all(cand.review_state == C.REVIEW_STATE_NEEDS_REVIEW for cand in group)


def test_hilton_family_brands_shared_complex():
    cands = _conflict_pair("Home2 Suites by Hilton Grove City Columbus",
                           "Tru by Hilton Grove City Columbus")
    resolutions = resolve_identity_conflicts(cands)
    assert resolutions[0][1] == C.IDENTITY_SHARED_COMPLEX_DISTINCT_PROPERTIES


def test_genuinely_unrelated_names_distinct_locations():
    cands = _conflict_pair("Travel Lodge Motel", "Grove City Travel Inn Columbus South")
    resolutions = resolve_identity_conflicts(cands)
    assert resolutions[0][1] == C.IDENTITY_DISTINCT_LOCATIONS


def test_classify_identity_relationship_pure_function_directly():
    from scripts.pettripfinder.discovery.models import DiscoveryCandidate
    a = DiscoveryCandidate(candidate_id="dc_a", source_records=(), name="Alpha Inn",
                           normalized_name="alpha inn", category_candidates=(C.CATEGORY_HOTEL,))
    b = DiscoveryCandidate(candidate_id="dc_b", source_records=(), name="Alpha Suites",
                           normalized_name="alpha suites", category_candidates=(C.CATEGORY_HOTEL,))
    assert classify_identity_relationship((a, b)) == C.IDENTITY_POSSIBLE_REBRAND

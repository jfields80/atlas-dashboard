"""AES-DATA-004B Phase 10 -- import-planning artifact tests."""

from __future__ import annotations

import json

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.import_plan import (
    build_import_plan,
    dumps_import_plan,
    next_action_counts,
)
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_records


def rec(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="id1",
               canonical_category=C.CATEGORY_HOTEL, name="Test Hotel")
    base.update(kw)
    return DiscoveryRecord(**base)


def _plan_for(*records):
    cands = deduplicate(normalize_records(records), market_id="columbus-oh")
    return build_import_plan(cands)


def test_ready_for_official_site_import():
    entries = _plan_for(rec(website_url="https://example-hotel.com"))
    assert entries[0].recommended_next_action == C.NEXT_ACTION_READY_FOR_OFFICIAL_SITE_IMPORT


def test_missing_website():
    entries = _plan_for(rec(website_url=""))
    assert entries[0].recommended_next_action == C.NEXT_ACTION_MISSING_WEBSITE


def test_resolve_official_website_for_ambiguous():
    # AMBIGUOUS is provably unreachable through the real normalize->dedup
    # pipeline: normalize_record already reduces any URL normalize_url()
    # can't parse down to "" *before* classify_candidate_website ever runs,
    # so an unparseable URL surfaces as MISSING_WEBSITE, not AMBIGUOUS (a
    # disclosed 004A-era design interaction, not a Wave-1 defect -- MISSING
    # is a safe, conservative fallback for this input shape). Exercise
    # compute_next_action's AMBIGUOUS branch directly against a
    # hand-built candidate instead, bypassing normalization.
    from dataclasses import replace
    cands = deduplicate(normalize_records((rec(website_url="https://example.com"),)),
                        market_id="columbus-oh")
    ambiguous_candidate = replace(cands[0], website_state=C.WEBSITE_STATE_AMBIGUOUS)
    from scripts.pettripfinder.discovery.import_plan import compute_next_action
    assert compute_next_action(ambiguous_candidate) == C.NEXT_ACTION_RESOLVE_OFFICIAL_WEBSITE


def test_ambiguous_state_unreachable_through_real_pipeline_falls_back_to_missing():
    entries = _plan_for(rec(website_url="not a real url"))
    assert entries[0].recommended_next_action == C.NEXT_ACTION_MISSING_WEBSITE


def test_resolve_official_website_for_provider_url_only():
    entries = _plan_for(rec(website_url="https://www.facebook.com/somehotel"))
    assert entries[0].recommended_next_action == C.NEXT_ACTION_RESOLVE_OFFICIAL_WEBSITE


def test_review_conflicting_website():
    a = rec(provider_record_id="a1", website_url="https://example-a.com",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1",
           website_url="https://example-b.com",
           address_line="1 Main St", city="Columbus", state="OH", postal_code="43215")
    entries = _plan_for(a, b)
    assert len(entries) == 1
    assert entries[0].recommended_next_action == C.NEXT_ACTION_REVIEW_CONFLICTING_WEBSITE


def test_review_identity_for_rebrand_conflict():
    a = rec(provider_record_id="a1", name="Holiday Inn Columbus Downtown",
           address_line="175 East Town St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1",
           name="Even Hotels Columbus Downtown",
           address_line="175 East Town St", city="Columbus", state="OH", postal_code="43215")
    entries = _plan_for(a, b)
    assert len(entries) == 2
    assert all(e.recommended_next_action == C.NEXT_ACTION_REVIEW_IDENTITY for e in entries)


def test_exclude_closed():
    a = rec(eligibility_state=C.ELIGIBILITY_PERMANENTLY_CLOSED)
    entries = _plan_for(a)
    assert entries[0].recommended_next_action == C.NEXT_ACTION_EXCLUDE_CLOSED


def test_review_out_of_scope():
    a = rec(eligibility_state=C.ELIGIBILITY_OUT_OF_MARKET_BOUNDS)
    entries = _plan_for(a)
    assert entries[0].recommended_next_action == C.NEXT_ACTION_REVIEW_OUT_OF_SCOPE


def test_next_action_counts_tally():
    entries = _plan_for(rec(website_url="https://a.com"))
    counts = next_action_counts(entries)
    assert dict(counts) == {C.NEXT_ACTION_READY_FOR_OFFICIAL_SITE_IMPORT: 1}


def test_serialization_excludes_pet_policy_fields():
    entries = _plan_for(rec(website_url="https://a.com"))
    text = dumps_import_plan(entries)
    data = json.loads(text)
    keys = set(data[0].keys())
    forbidden = {"pet_policy", "rating", "reviews", "hours", "pet_friendly",
                "amenities", "high_risk"}
    assert not (keys & forbidden)


def test_provenance_and_provider_ids_present():
    a = rec(provider_record_id="gp1", source_query_id="q1", website_url="https://a.com")
    entries = _plan_for(a)
    assert entries[0].source_query_ids == ("q1",)
    assert dict(entries[0].provider_ids) == {C.PROVIDER_GOOGLE_PLACES: "gp1"}

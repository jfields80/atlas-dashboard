"""AES-DATA-004A discovery -- deduplication/entity-resolution tests (Task 9).
Pure, synthetic, no network."""

from __future__ import annotations

import random

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.deduplicate import deduplicate, haversine_meters
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_records


def rec(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="id1",
               canonical_category=C.CATEGORY_VETERINARY, name="Test", address_line="",
               city="", state="", postal_code="", latitude=None, longitude=None,
               phone="", website_url="")
    base.update(kw)
    return DiscoveryRecord(**base)


def test_1_same_business_found_by_google_and_osm_merges():
    g = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="g1",
           name="Northside Animal Hospital",
           address_line="123 Main St, Columbus, OH 43215",
           city="Columbus", state="OH", postal_code="43215",
           latitude=39.960, longitude=-82.990)
    o = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/999",
           name="Northside Animal Hospital", address_line="123 Main St",
           latitude=39.9601, longitude=-82.9901)
    cands = deduplicate(normalize_records((g, o)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].review_state == C.REVIEW_STATE_AUTO_MERGED
    assert set(dict(cands[0].provider_ids)) == {C.PROVIDER_GOOGLE_PLACES, C.PROVIDER_OPENSTREETMAP}


def test_2_same_chain_different_addresses_does_not_merge():
    p1 = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1", name="Petco",
            address_line="100 North St", city="Columbus", state="OH", postal_code="43201",
            latitude=40.02, longitude=-83.00)
    p2 = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p2", name="Petco",
            address_line="500 South St", city="Grove City", state="OH", postal_code="43123",
            latitude=39.88, longitude=-83.09)
    cands = deduplicate(normalize_records((p1, p2)), market_id="columbus-oh")
    assert len(cands) == 2


def test_2b_medvet_columbus_vs_hilliard_distinct():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="a1", name="MedVet Columbus",
           address_line="300 E Broad St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="b1", name="MedVet Hilliard",
           address_line="4000 Hilliard-Rome Rd", city="Hilliard", state="OH", postal_code="43026")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_2c_hilton_downtown_vs_easton_distinct():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="h1", name="Hilton Downtown",
           canonical_category=C.CATEGORY_HOTEL,
           address_line="401 N High St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="h2", name="Hilton Easton",
           canonical_category=C.CATEGORY_HOTEL,
           address_line="3900 Chagrin Dr", city="Columbus", state="OH", postal_code="43219")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_3_same_address_different_suite_businesses_conservative():
    # Genuinely different businesses that happen to share a building address
    # (different suite) -- names are not compatible, so no merge signal fires
    # even though the address portion is textually identical.
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="s1", name="Downtown Vet Clinic",
           address_line="55 Suite A Main St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/55", name="City Pet Grooming",
           address_line="55 Suite B Main St", city="Columbus", state="OH", postal_code="43215")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_4_normalized_phone_supports_merge():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="ph1", name="Acme Grooming",
           phone="(614) 555-0100")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1", name="Acme Grooming",
           phone="614.555.0100")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].merge_reason == C.MERGE_REASON_PHONE_PLUS_NAME


def test_5_matching_domain_alone_insufficient():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="d1", name="Alpha Vet",
           website_url="https://samechain.example.com/alpha",
           address_line="1 A St", city="Columbus", state="OH")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/2", name="Beta Vet",
           website_url="https://samechain.example.com/beta",
           address_line="2 B St", city="Dublin", state="OH")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_6_coordinate_proximity_alone_insufficient():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="c1", name="Coffee Shop",
           latitude=39.960, longitude=-82.990)
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/3", name="Bookstore",
           latitude=39.9601, longitude=-82.9901)
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_7_formatting_differences_merge_safely():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="f1", name="O'Brien's Pet Store, LLC.",
           address_line="10 Main St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/4", name="obriens pet store llc",
           address_line="10 Main St", city="Columbus", state="OH", postal_code="43215")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].merge_reason == C.MERGE_REASON_SAME_ADDRESS


def test_8_conflicting_addresses_remain_separate_but_flagged():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="ph1", name="Acme Pet Store",
           phone="614-555-0100", address_line="10 First Ave", city="Columbus", state="OH",
           postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/4", name="Acme Pet Store",
           phone="614-555-0100", address_line="9999 Far Rd", city="Reynoldsburg", state="OH",
           postal_code="43068")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2
    assert all(c.review_state == C.REVIEW_STATE_NEEDS_REVIEW for c in cands)
    assert all(c.conflict_flags == (C.CONFLICT_ADDRESS_MISMATCH,) for c in cands)


def test_9_provider_only_records_preserved():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="g1", name="Google-Only Vet",
           address_line="1 G St", city="Columbus", state="OH")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/5", name="OSM-Only Park")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2
    for c in cands:
        assert len(c.source_records) == 1
        assert c.review_state == C.REVIEW_STATE_SINGLE_SOURCE


def test_10_deterministic_output_regardless_of_source_ordering():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="a1", name="Vet A",
           address_line="1 A St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/6", name="Vet A",
           address_line="1 A St", city="Columbus", state="OH", postal_code="43215")
    c = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="c1", name="Vet C",
           address_line="9 C St", city="Dublin", state="OH")

    order1 = normalize_records((a, b, c))
    order2 = normalize_records((c, a, b))
    order3 = normalize_records((b, c, a))
    ids1 = tuple(sorted(x.candidate_id for x in deduplicate(order1, market_id="columbus-oh")))
    ids2 = tuple(sorted(x.candidate_id for x in deduplicate(order2, market_id="columbus-oh")))
    ids3 = tuple(sorted(x.candidate_id for x in deduplicate(order3, market_id="columbus-oh")))
    assert ids1 == ids2 == ids3


def test_11_same_provider_id_always_merges_even_across_categories():
    # The same query plan can return the same real place from two different
    # Google query text variants for the same cell/category -- same
    # provider_record_id must always collapse to one candidate.
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="dup1", name="Some Vet")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="dup1", name="Some Vet")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].merge_reason == C.MERGE_REASON_SAME_PROVIDER_ID


def test_12_haversine_zero_distance():
    assert haversine_meters(39.96, -82.99, 39.96, -82.99) == 0.0


def test_13_haversine_known_short_distance_reasonable():
    # ~0.01 degree latitude is roughly 1.1km.
    d = haversine_meters(39.96, -82.99, 39.97, -82.99)
    assert 900 < d < 1300


def test_14_single_record_never_merges_with_itself_as_two():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="solo1", name="Solo Business")
    cands = deduplicate(normalize_records((a,)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].review_state == C.REVIEW_STATE_SINGLE_SOURCE


def test_15_empty_input_produces_no_candidates():
    assert deduplicate((), market_id="columbus-oh") == ()

"""AES-DATA-004B Phase 4 -- lodging-specific deduplication safety tests.

Synthetic hotel/motel records exercising identity problems specific to
lodging (chains, shared complexes, rebrands, attached amenities). Pure,
no network. Reuses the exact production ``deduplicate()``/
``normalize_records()`` pipeline -- no separate test-only merge heuristic.
"""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_records


def rec(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="id1",
               canonical_category=C.CATEGORY_HOTEL, name="Test Hotel", address_line="",
               city="", state="", postal_code="", latitude=None, longitude=None,
               phone="", website_url="")
    base.update(kw)
    return DiscoveryRecord(**base)


def test_1_same_hotel_two_google_text_queries_merges_by_place_id():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="ChIJ-drury-polaris",
           name="Drury Inn & Suites Columbus Polaris", source_query_id="q_hotel_0")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="ChIJ-drury-polaris",
           name="Drury Inn & Suites Columbus Polaris", source_query_id="q_lodging_1")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].merge_reason == C.MERGE_REASON_SAME_PROVIDER_ID
    assert cands[0].review_state == C.REVIEW_STATE_AUTO_MERGED


def test_2_same_hotel_google_and_osm_merges_on_name_address_coords():
    g = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="g1",
           name="Hyatt Regency Columbus", address_line="350 North High St",
           city="Columbus", state="OH", postal_code="43215",
           latitude=39.9666, longitude=-83.0000)
    o = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/501",
           name="Hyatt Regency Columbus", address_line="350 North High St",
           latitude=39.9667, longitude=-83.0001)
    cands = deduplicate(normalize_records((g, o)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].review_state == C.REVIEW_STATE_AUTO_MERGED


def test_3_same_chain_two_addresses_remains_separate():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="hi1",
           name="Hampton Inn Columbus Dublin", address_line="3920 Tuller Rd",
           city="Dublin", state="OH", postal_code="43017")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="hi2",
           name="Hampton Inn Columbus Easton", address_line="4270 Stelzer Rd",
           city="Columbus", state="OH", postal_code="43219")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_4_same_chain_same_street_different_building_stays_conservative():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="hs1",
           name="Homewood Suites by Hilton Columbus Dublin North Building",
           address_line="5300 Parkcenter Ave Building A", city="Dublin",
           state="OH", postal_code="43017")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/900",
           name="Homewood Suites by Hilton Columbus Dublin South Building",
           address_line="5300 Parkcenter Ave Building C", city="Dublin",
           state="OH", postal_code="43017")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_5_two_hotels_in_shared_complex_remain_separate_and_flagged():
    # A real dual-branded IHG-style complex: two distinct hotel brands at
    # one shared street address -- must not silently merge just because
    # the address string matches; the name mismatch is flagged instead.
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="sb1",
           name="Staybridge Suites Columbus Dublin", address_line="6095 Emerald Pkwy",
           city="Dublin", state="OH", postal_code="43017")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/700",
           name="Even Hotels Columbus Dublin", address_line="6095 Emerald Pkwy",
           city="Dublin", state="OH", postal_code="43017")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2
    assert all(c.review_state == C.REVIEW_STATE_NEEDS_REVIEW for c in cands)
    assert all(c.conflict_flags == (C.CONFLICT_NAME_MISMATCH,) for c in cands)


def test_6_rebranded_hotel_same_address_becomes_review_not_silent_merge():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="hi3",
           name="Holiday Inn Columbus Downtown", address_line="175 East Town St",
           city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/800",
           name="Even Hotels Columbus Downtown", address_line="175 East Town St",
           city="Columbus", state="OH", postal_code="43215")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2
    assert all(c.review_state == C.REVIEW_STATE_NEEDS_REVIEW for c in cands)
    assert all(c.conflict_flags == (C.CONFLICT_NAME_MISMATCH,) for c in cands)


def test_7_hotel_and_attached_restaurant_do_not_merge():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="dp1",
           name="Drury Plaza Hotel Columbus Downtown", address_line="88 East Nationwide Blvd",
           city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="bl1",
           name="Bar Louie Nationwide Blvd", canonical_category=C.CATEGORY_RESTAURANT,
           address_line="88 East Nationwide Blvd", city="Columbus", state="OH",
           postal_code="43215")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_8_hotel_and_conference_center_share_domain_not_address_no_merge():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="hy1",
           name="Hyatt Regency Columbus", website_url="https://www.hyatt.com/hyatt-regency/columbus",
           address_line="350 North High St", city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="hy2",
           name="Hyatt Conference Center Polaris",
           website_url="https://www.hyatt.com/conference-centers/polaris",
           address_line="8801 Lyra Dr", city="Columbus", state="OH", postal_code="43240")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2
    # different, non-overlapping addresses -- no conflict flag either, just
    # a clean "insufficient signal" outcome.
    assert all(c.conflict_flags == () for c in cands)


def test_9_holiday_inn_express_airport_vs_holiday_inn_downtown_separate():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="hie1",
           name="Holiday Inn Express Columbus Airport", address_line="4400 International Gateway",
           city="Columbus", state="OH", postal_code="43219")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="hid1",
           name="Holiday Inn Columbus Downtown", address_line="175 East Town St",
           city="Columbus", state="OH", postal_code="43215")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_10_red_roof_plus_downtown_vs_red_roof_inn_west_separate():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="rrp1",
           name="Red Roof PLUS+ Columbus Downtown", address_line="111 East Nationwide Blvd",
           city="Columbus", state="OH", postal_code="43215")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="rri1",
           name="Red Roof Inn Columbus West", address_line="5001 Renner Rd",
           city="Columbus", state="OH", postal_code="43228")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_11_formatting_only_address_differences_merge():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="ex1",
           name="Extended Stay America Suites Columbus Dublin",
           address_line="450 Metro Place North", city="Dublin", state="OH", postal_code="43017")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/600",
           name="extended stay america suites columbus dublin",
           address_line="450 METRO PLACE NORTH", city="Dublin", state="OH", postal_code="43017")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 1
    assert cands[0].merge_reason == C.MERGE_REASON_SAME_ADDRESS


def test_12_brand_domain_equality_alone_never_merges():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="la1",
           name="La Quinta Inn Columbus Dublin", website_url="https://www.wyndhamhotels.com/laquinta/dublin",
           address_line="6145 Park Center Circle", city="Dublin", state="OH", postal_code="43017")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/601",
           name="La Quinta Inn Columbus Northeast", website_url="https://www.wyndhamhotels.com/laquinta/northeast",
           address_line="1289 East Dublin Granville Rd", city="Columbus", state="OH",
           postal_code="43229")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2


def test_13_central_reservation_phone_alone_never_merges():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="rr1",
           name="Red Roof PLUS+ Columbus Dublin", phone="800-733-7663",
           address_line="5125 Post Rd", city="Dublin", state="OH", postal_code="43017")
    b = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="rr2",
           name="Red Roof PLUS+ Columbus Worthington", phone="800-733-7663",
           address_line="7480 North High St", city="Columbus", state="OH", postal_code="43235")
    cands = deduplicate(normalize_records((a, b)), market_id="columbus-oh")
    assert len(cands) == 2
    assert all(c.conflict_flags == () for c in cands)   # not even flagged -- no signal fired at all


def test_14_deterministic_results_regardless_of_query_order():
    a = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="d1",
           name="Aloft Columbus University District", address_line="1295 Olentangy River Rd",
           city="Columbus", state="OH", postal_code="43212")
    b = rec(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="node/1",
           name="Aloft Columbus University District", address_line="1295 Olentangy River Rd",
           city="Columbus", state="OH", postal_code="43212")
    c = rec(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="d2",
           name="The Westin Great Southern Columbus", address_line="310 South High St",
           city="Columbus", state="OH", postal_code="43215")

    order1 = normalize_records((a, b, c))
    order2 = normalize_records((c, a, b))
    order3 = normalize_records((b, c, a))
    ids1 = tuple(sorted(x.candidate_id for x in deduplicate(order1, market_id="columbus-oh")))
    ids2 = tuple(sorted(x.candidate_id for x in deduplicate(order2, market_id="columbus-oh")))
    ids3 = tuple(sorted(x.candidate_id for x in deduplicate(order3, market_id="columbus-oh")))
    assert ids1 == ids2 == ids3

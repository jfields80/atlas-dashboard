"""PTF-IDENTITY-ROUTING-P0-001 -- ptf-identity-routing/1.0 and its integration.

The load-bearing claim these tests defend is a NEGATIVE one: a routing record
says where a property speaks for itself, and cannot become publication. Most of
the file is therefore about what does NOT happen.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder import identity_routing as IR
from scripts.pettripfinder.build_capture_queue import build_queue
from scripts.pettripfinder.site_data import normalize_name

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"


def record(**overrides):
    base = {
        "routing_id": "route-columbus-oh-sample-inn",
        "schema_version": IR.CONTRACT_VERSION,
        "hotel_ref": {"market_id": "columbus-oh",
                      "canonical_name": "Sample Inn Columbus",
                      "normalized_name": "sample inn columbus"},
        "market_id": "columbus-oh",
        "official_property_url": "https://www.marriott.com/en-us/hotels/xxxxx-sample/overview/",
        "official_domain": "marriott.com",
        "property_code": "XXXXX",
        "brand": "MARRIOTT",
        "binding_method": IR.BINDING_BRAND_INDEX,
        "binding_sources": ["chamber directory anchor"],
        "identity_signals_matched": ["street", "zip"],
        "observed_at": "2026-08-08",
        "verified_at": "2026-08-08",
        "status": IR.ROUTING_CONFIRMED,
    }
    base.update(overrides)
    return base


def authority(*records):
    return {"schema": IR.SCHEMA, "routes": list(records)}


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

def test_valid_record_round_trips():
    assert IR.validate_record(record())["routing_id"].startswith("route-")


def test_strict_keys_reject_unknown_field():
    with pytest.raises(IR.IdentityRoutingError, match="additionalProperties"):
        IR.validate_record(record(surprise="nope"))


def test_missing_required_field_fails():
    doc = record()
    del doc["binding_sources"]
    with pytest.raises(IR.IdentityRoutingError, match="missing required"):
        IR.validate_record(doc)


def test_policy_fields_are_forbidden():
    with pytest.raises(IR.IdentityRoutingError, match="pet-policy field"):
        IR.validate_record(record(pet_fee=5000))


def test_policy_fields_forbidden_inside_identity_context():
    with pytest.raises(IR.IdentityRoutingError, match="pet-policy field"):
        IR.validate_record(record(identity_context={"pets_allowed": "true"}))


def test_unknown_status_rejected():
    with pytest.raises(IR.IdentityRoutingError, match="status"):
        IR.validate_record(record(status="PROBABLY_FINE"))


def test_binding_method_is_closed_and_never_upgraded():
    with pytest.raises(IR.IdentityRoutingError, match="rendered page"):
        IR.validate_record(record(binding_method="LOOKS_RIGHT"))
    assert IR.validate_record(
        record(binding_method=IR.BINDING_BRAND_INDEX))["binding_method"] \
        == IR.BINDING_BRAND_INDEX


def test_normalized_name_must_be_derivable_not_typed():
    with pytest.raises(IR.IdentityRoutingError, match="derivable"):
        IR.validate_record(record(hotel_ref={
            "market_id": "columbus-oh", "canonical_name": "Sample Inn Columbus",
            "normalized_name": "whatever i felt like"}))


def test_hotel_ref_may_not_carry_a_second_identifier():
    with pytest.raises(IR.IdentityRoutingError, match="never extends it"):
        IR.validate_record(record(hotel_ref={
            "market_id": "columbus-oh", "canonical_name": "Sample Inn Columbus",
            "normalized_name": "sample inn columbus",
            "atlas_hotel_id": "HOTEL-0001"}))


def test_market_id_must_match_identity_market():
    with pytest.raises(IR.IdentityRoutingError, match="does not match hotel_ref"):
        IR.validate_record(record(market_id="cleveland-akron-canton-oh"))


def test_third_party_domain_rejected_as_official():
    with pytest.raises(IR.IdentityRoutingError, match="never BE one"):
        IR.validate_record(record(
            official_property_url="https://www.booking.com/hotel/us/sample.html",
            official_domain="booking.com"))


def test_known_dead_parking_domain_rejected():
    with pytest.raises(IR.IdentityRoutingError, match="never BE one"):
        IR.validate_record(record(
            official_property_url="https://www.comfortsuitesgrovecity.com/",
            official_domain="comfortsuitesgrovecity.com"))


def test_declared_domain_must_match_the_url():
    with pytest.raises(IR.IdentityRoutingError, match="does not match"):
        IR.validate_record(record(official_domain="hilton.com"))


def test_non_https_rejected():
    with pytest.raises(IR.IdentityRoutingError, match="https"):
        IR.validate_record(record(
            official_property_url="http://www.marriott.com/en-us/hotels/x/overview/"))


def test_confirmed_record_must_record_identity_signals():
    with pytest.raises(IR.IdentityRoutingError, match="identity signals"):
        IR.validate_record(record(identity_signals_matched=[]))


def test_binding_sources_must_be_present():
    with pytest.raises(IR.IdentityRoutingError, match="binding_sources"):
        IR.validate_record(record(binding_sources=[]))


# --------------------------------------------------------------------------- #
# Collisions
# --------------------------------------------------------------------------- #

def test_one_active_routing_record_per_identity():
    a = record(routing_id="route-a")
    b = record(routing_id="route-b")
    with pytest.raises(IR.IdentityRoutingError, match="two active routing records"):
        IR.validate_authority(authority(a, b))


def test_a_held_duplicate_is_allowed_beside_one_active():
    a = record(routing_id="route-a")
    b = record(routing_id="route-b", status=IR.ROUTING_HELD)
    assert len(IR.validate_authority(authority(a, b))) == 2


def test_duplicate_property_code_across_identities_rejected():
    a = record()
    b = record(routing_id="route-b",
               hotel_ref={"market_id": "columbus-oh", "canonical_name": "Other Inn",
                          "normalized_name": "other inn"},
               official_property_url="https://www.marriott.com/en-us/hotels/yyyyy-other/overview/")
    with pytest.raises(IR.IdentityRoutingError, match="property code"):
        IR.validate_authority(authority(a, b))


def test_duplicate_url_across_identities_rejected():
    a = record()
    b = record(routing_id="route-b", property_code="YYYYY",
               hotel_ref={"market_id": "columbus-oh", "canonical_name": "Other Inn",
                          "normalized_name": "other inn"})
    with pytest.raises(IR.IdentityRoutingError, match="URL .* binds two"):
        IR.validate_authority(authority(a, b))


# --------------------------------------------------------------------------- #
# The committed Columbus authority
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def routes():
    return IR.load_routes()


def test_committed_authority_validates(routes):
    assert len(routes) == 21


def test_committed_authority_split(routes):
    confirmed = [r for r in routes if r["status"] == IR.ROUTING_CONFIRMED]
    held = [r for r in routes if r["status"] == IR.ROUTING_HELD]
    assert len(confirmed) == 20
    assert len(held) == 1
    assert held[0]["hotel_ref"]["normalized_name"] == "staybridge suites columbus worthington"


def test_every_committed_record_preserves_index_binding(routes):
    assert {r["binding_method"] for r in routes} == {IR.BINDING_BRAND_INDEX}


def test_no_committed_route_is_on_a_third_party_domain(routes):
    for r in routes:
        assert IR.registrable_domain(r["official_property_url"]) \
            not in IR.NEVER_OFFICIAL_DOMAINS


def test_every_committed_route_is_columbus(routes):
    assert {r["market_id"] for r in routes} == {"columbus-oh"}


def test_no_committed_route_is_already_seed_inventory(routes):
    seed = {normalize_name(r["name"]) for r in
            csv.DictReader((LP / "seed_businesses.csv").open(encoding="utf-8"))
            if r["category"] == "pet-friendly-hotels"}
    for r in routes:
        assert r["hotel_ref"]["normalized_name"] not in seed, (
            "%s is seed inventory; the seed remains the source of truth for it"
            % r["hotel_ref"]["normalized_name"])


# --------------------------------------------------------------------------- #
# Authority separation -- the negative guarantees
# --------------------------------------------------------------------------- #

def test_routing_does_not_enter_seed_inventory():
    rows = list(csv.DictReader((LP / "seed_businesses.csv").open(encoding="utf-8")))
    hotels = [r for r in rows if r["category"] == "pet-friendly-hotels"]
    assert len(hotels) == 86, "seed hotel rows must be untouched by routing"


def test_routing_does_not_change_published_count():
    pkg = json.loads((LP / "hotel_policy_facts.json").read_text(encoding="utf-8"))
    assert len(pkg["hotels"]) == 81


def test_routing_does_not_change_the_release_held_count():
    """held is derived from the seed alone, so routing cannot move it."""
    from scripts.pettripfinder.site_data import (
        load_published_hotel_policy_facts, read_production_rows,
        verified_public_hotels,
    )
    contract = json.loads(
        (_REPO / "deploy" / "netlify" / "release_contract.json").read_text(encoding="utf-8"))
    hotel_seed = [r for r in read_production_rows()
                  if r.get("category") == "pet-friendly-hotels"]
    verified = verified_public_hotels(hotel_seed, load_published_hotel_policy_facts())
    held = len(hotel_seed) - len(verified)
    assert held == contract["public_surface"]["excluded_public_profile_count"] == 5


def test_no_publication_module_reads_the_routing_authority():
    """Structural: the publication path must not import routing at all."""
    import ast
    targets = [
        _REPO / "scripts" / "generate_pettripfinder_columbus_site.py",
        _REPO / "scripts" / "pettripfinder" / "assemble_netlify_bundle.py",
        _REPO / "scripts" / "pettripfinder" / "publication_guard.py",
        _REPO / "scripts" / "pettripfinder" / "site_data.py",
    ]
    for path in targets:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        assert not any("identity_routing" in n for n in names), (
            "%s imports identity_routing; routing must never reach publication"
            % path.name)


# --------------------------------------------------------------------------- #
# Capture queue integration
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def queues():
    base = build_queue(batch_id="t-base", require_retrieval_artifact=False,
                       use_identity_routing=False)
    routed = build_queue(batch_id="t-routed", require_retrieval_artifact=False)
    return base, routed


def test_routing_adds_capture_ready_hotels(queues):
    base, routed = queues
    assert len(routed.selected) > len(base.selected)
    # Was 16, then 10. PTF-NEGATIVE-EVIDENCE-P0-001 applied five more
    # VERIFIED_NO_PETS exclusions, and an identity already answered by evidence
    # is no longer capture-worthy -- so routing's remaining contribution is the
    # 5 hotels still genuinely awaiting a policy. The number falling as hotels
    # get ANSWERED is the queue working, not routing regressing.
    assert len(routed.selected) - len(base.selected) == 3


def test_previously_usable_seed_urls_remain_usable(queues):
    base, routed = queues
    base_ids = {h["hotel_id"] for h in base.selected}
    routed_ids = {h["hotel_id"] for h in routed.selected}
    assert base_ids <= routed_ids, "routing must never remove a seed-sourced entry"


def test_seed_url_takes_precedence_over_routing(tmp_path):
    """A seed row that HAS a URL keeps it, even if routing knows another."""
    seed = tmp_path / "seed.csv"
    with seed.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "name", "category", "address", "city", "state", "postal_code",
            "phone", "website_url", "source_url", "source_type", "observed_at",
            "rating", "amenities", "pet_policy", "canonical"])
        w.writeheader()
        w.writerow({"name": "Sample Inn Columbus", "category": "pet-friendly-hotels",
                    "address": "1 Test St", "city": "Columbus", "state": "OH",
                    "postal_code": "43215", "phone": "614-555-0100",
                    "website_url": "https://www.marriott.com/en-us/hotels/seed1-sample/overview/"})
    routing = tmp_path / "routing.json"
    routing.write_text(json.dumps(authority(record(
        official_property_url="https://www.marriott.com/en-us/hotels/route1-sample/overview/",
        property_code="ROUTE1",
        identity_context={"address": "1 Test St", "city": "Columbus",
                          "state": "OH", "postal_code": "43215",
                          "phone": "614-555-0100"}))), encoding="utf-8")
    result = build_queue(batch_id="t", seed_csv=str(seed), routing_path=str(routing),
                         require_retrieval_artifact=False)
    urls = [h["official_url"] for h in result.selected]
    assert urls == ["https://www.marriott.com/en-us/hotels/seed1-sample/overview/"]


def test_routing_fills_in_when_the_seed_url_is_absent(tmp_path):
    seed = tmp_path / "seed.csv"
    with seed.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "name", "category", "address", "city", "state", "postal_code",
            "phone", "website_url", "source_url", "source_type", "observed_at",
            "rating", "amenities", "pet_policy", "canonical"])
        w.writeheader()
        w.writerow({"name": "Sample Inn Columbus", "category": "pet-friendly-hotels",
                    "address": "1 Test St", "city": "Columbus", "state": "OH",
                    "postal_code": "43215", "phone": "614-555-0100",
                    "website_url": ""})
    routing = tmp_path / "routing.json"
    routing.write_text(json.dumps(authority(record())), encoding="utf-8")
    result = build_queue(batch_id="t", seed_csv=str(seed), routing_path=str(routing),
                         require_retrieval_artifact=False)
    assert [h["official_url"] for h in result.selected] == [
        "https://www.marriott.com/en-us/hotels/xxxxx-sample/overview/"]
    assert "identity routing" in result.selected[0]["notes"]


def test_a_held_route_is_never_used(routes, queues):
    _, routed = queues
    held = [r for r in routes if r["status"] != IR.ROUTING_CONFIRMED]
    queued = {h["listing_key"] for h in routed.selected}
    for r in held:
        assert r["hotel_ref"]["normalized_name"] not in queued


def test_a_weak_binding_is_not_confirmed(routes):
    weak = [r for r in routes
            if r["hotel_ref"]["normalized_name"] == "staybridge suites columbus worthington"]
    assert weak and weak[0]["status"] == IR.ROUTING_HELD


def test_routing_record_without_queue_identity_is_excluded_not_invented(tmp_path):
    routing = tmp_path / "routing.json"
    routing.write_text(json.dumps(authority(record(
        identity_context={"city": "Columbus"}))), encoding="utf-8")
    seed = tmp_path / "seed.csv"
    seed.write_text("name,category,address,city,state,postal_code,phone,website_url,"
                    "source_url,source_type,observed_at,rating,amenities,pet_policy,"
                    "canonical\n", encoding="utf-8")
    result = build_queue(batch_id="t", seed_csv=str(seed), routing_path=str(routing),
                         require_retrieval_artifact=False)
    assert result.selected == ()
    assert any("routing_identity_incomplete" in e.reason for e in result.excluded)


def test_queue_entry_from_routing_carries_no_policy_fact(queues):
    _, routed = queues
    for hotel in routed.selected:
        assert "pet_policy" not in hotel
        assert "pets_allowed" not in hotel


def test_disabling_routing_restores_the_prior_queue(queues):
    base, _ = queues
    assert len(base.selected) == 69

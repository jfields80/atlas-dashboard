"""AES-DATA-004I -- lodging reconciliation logic tests. No network; the
planner-level tests run against the real repository/operational data, the
unit tests against synthetic records."""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.importer.lodging_reconciliation import (
    DECISION_BETA_THRESHOLD_REACHED,
    DECISION_ONE_MORE_BATCH,
    DECISION_STRATEGY_REVIEW,
    SOURCE_IMPORTER_READY,
    SOURCE_IMPORTER_REVIEW,
    SOURCE_PRODUCTION_EXISTING,
    choose_canonical,
    duplicate_reason,
    group_duplicates,
    threshold_decision,
    validate_proposed_inventory,
)


def _rec(sid, cls, name, city="Columbus", address="", url="", dedup_url="",
         phone="", verified="2026-07-18", policy=None, rec="", pets=""):
    return {
        "source_id": sid, "source_class": cls, "canonical_name": name,
        "city": city, "state": "OH", "address": address,
        "official_url": url, "dedup_url": dedup_url or url, "phone": phone,
        "verified_at": verified, "policy_fields": policy or {},
        "recommendation": rec, "pets_allowed": pets,
    }


# --------------------------------------------------------------------------- #
# Duplicate signals.
# --------------------------------------------------------------------------- #

def test_same_property_url_merges():
    a = _rec("a", SOURCE_PRODUCTION_EXISTING, "Hyatt Regency Columbus",
             url="https://www.hyatt.com/hyatt-regency/en-US/cmhrc-x?utm=1")
    b = _rec("b", SOURCE_IMPORTER_REVIEW, "Hyatt Regency Columbus",
             url="https://www.hyatt.com/hyatt-regency/en-US/cmhrc-x")
    assert duplicate_reason(a, b) == "same_official_property_url"


def test_shared_chain_hub_canonical_never_merges_sister_properties():
    # Live case: both InTown Suites properties canonicalize their website_url
    # to the same city hub; the property-specific dedup_url keeps them apart,
    # and their contradicting street addresses block the shared-phone signal.
    a = _rec("a", "IMPORTER_REJECT_NO_PETS", "InTown Suites Extended Stay Columbus OH",
             address="100 Hamilton Rd", phone="1-888-882-0805",
             url="https://www.intownsuites.com/extended-stay-hotels/ohio/columbus/",
             dedup_url="https://www.intownsuites.com/extended-stay-hotels/ohio/columbus/i70e-hamilton-rd/")
    b = _rec("b", "IMPORTER_REJECT_NO_PETS", "InTown Suites Extended Stay Columbus OH",
             address="200 Dublin Center Dr", phone="1-888-882-0805",
             url="https://www.intownsuites.com/extended-stay-hotels/ohio/columbus/",
             dedup_url="https://www.intownsuites.com/extended-stay-hotels/ohio/columbus/dublin/")
    assert duplicate_reason(a, b) == ""


def test_punctuation_and_brand_qualifier_variants_merge():
    a = _rec("a", SOURCE_PRODUCTION_EXISTING, "Aloft Columbus University District",
             address="1 Campus Way")
    b = _rec("b", SOURCE_IMPORTER_READY, "Aloft by Marriott Columbus University District",
             address="1 Campus Way")
    assert duplicate_reason(a, b) == "same_normalized_address_and_compatible_name"


def test_same_chain_same_city_different_address_never_merges():
    a = _rec("a", SOURCE_IMPORTER_READY, "Red Roof Inn Columbus North", address="1 North St")
    b = _rec("b", SOURCE_IMPORTER_READY, "Red Roof Inn Columbus South", address="9 South St")
    assert duplicate_reason(a, b) == ""


def test_exact_name_and_city_merges_across_different_domains():
    # Westin Great Southern: production row on marriott.com vs candidate on
    # westincolumbus.com -- same property, no address on one side.
    a = _rec("a", SOURCE_PRODUCTION_EXISTING, "The Westin Great Southern Columbus",
             url="https://www.marriott.com/en-us/hotels/cmhwi-x/overview/")
    b = _rec("b", SOURCE_IMPORTER_REVIEW, "The Westin Great Southern Columbus",
             url="https://www.westincolumbus.com/")
    assert duplicate_reason(a, b) == "same_exact_name_and_city"


def test_similar_but_not_equal_names_never_merge_alone():
    a = _rec("a", SOURCE_PRODUCTION_EXISTING, "Hampton Inn Columbus Dublin")
    b = _rec("b", SOURCE_IMPORTER_READY, "Hampton Inn & Suites Columbus Polaris")
    assert duplicate_reason(a, b) == ""


# --------------------------------------------------------------------------- #
# Precedence.
# --------------------------------------------------------------------------- #

def test_production_continuity_beats_equal_or_older_candidate():
    prod = _rec("prod_001", SOURCE_PRODUCTION_EXISTING, "X Hotel",
                verified="2026-05-01", policy={"pet_policy": "text"})
    cand = _rec("w:c1", SOURCE_IMPORTER_READY, "X Hotel",
                verified="2026-05-01", policy={"pets_allowed": "true"})
    canonical, superseded, reason = choose_canonical([prod, cand])
    assert canonical["source_id"] == "prod_001"
    assert reason == "production_continuity_retained"


def test_newer_richer_ready_candidate_supersedes_production():
    prod = _rec("prod_001", SOURCE_PRODUCTION_EXISTING, "X Hotel",
                verified="2026-01-01", policy={"pet_policy": "old"})
    cand = _rec("w:c1", SOURCE_IMPORTER_READY, "X Hotel",
                verified="2026-07-18",
                policy={"pets_allowed": "true", "pet_fee": "$50"})
    canonical, _, reason = choose_canonical([prod, cand])
    assert canonical["source_id"] == "w:c1"
    assert reason == "newer_ready_candidate_supersedes_production"


def test_older_candidate_never_overwrites_newer_production():
    prod = _rec("prod_001", SOURCE_PRODUCTION_EXISTING, "X Hotel",
                verified="2026-07-01")
    cand = _rec("w:c1", SOURCE_IMPORTER_READY, "X Hotel", verified="2026-01-01",
                policy={"pets_allowed": "true", "pet_fee": "$50"})
    canonical, _, reason = choose_canonical([prod, cand])
    assert canonical["source_id"] == "prod_001"


def test_ready_beats_review_variant_of_same_property():
    ready = _rec("a:r", SOURCE_IMPORTER_READY, "X Hotel", verified="2026-07-18")
    review = _rec("b:v", SOURCE_IMPORTER_REVIEW, "X Hotel", verified="2026-07-19")
    canonical, _, reason = choose_canonical([ready, review])
    assert canonical["source_id"] == "a:r"
    assert reason == "ready_candidate_over_non_promotable_variant"


# --------------------------------------------------------------------------- #
# Threshold (fixed rule).
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("n,decision", [
    (25, DECISION_BETA_THRESHOLD_REACHED), (30, DECISION_BETA_THRESHOLD_REACHED),
    (24, DECISION_ONE_MORE_BATCH), (15, DECISION_ONE_MORE_BATCH),
    (14, DECISION_STRATEGY_REVIEW), (0, DECISION_STRATEGY_REVIEW),
])
def test_threshold_decision_rule(n, decision):
    assert threshold_decision(n) == decision


# --------------------------------------------------------------------------- #
# Proposed-inventory validation.
# --------------------------------------------------------------------------- #

def test_validation_rejects_review_promotion():
    prod = [_rec("prod_001", SOURCE_PRODUCTION_EXISTING, "A Hotel", address="1 A St",
                 url="https://a.test/x")]
    promo = [_rec("w:c1", SOURCE_IMPORTER_REVIEW, "B Hotel", address="2 B St",
                  url="https://b.test/x", rec="REVIEW", pets="true")]
    errors = validate_proposed_inventory(prod, promo)
    assert any(e.startswith("non_ready_promotion") for e in errors)


def test_validation_rejects_missing_pets_allowed():
    promo = [_rec("w:c1", SOURCE_IMPORTER_READY, "B Hotel", address="2 B St",
                  url="https://b.test/x", rec="READY", pets="")]
    errors = validate_proposed_inventory([], promo)
    assert any(e.startswith("pet_friendly_promotion_without_pets_allowed") for e in errors)


def test_validation_rejects_duplicate_name_city():
    prod = [_rec("prod_001", SOURCE_PRODUCTION_EXISTING, "Same Hotel", address="1 A St",
                 url="https://a.test/x")]
    promo = [_rec("w:c1", SOURCE_IMPORTER_READY, "Same Hotel", address="1 A St",
                  url="https://b.test/y", rec="READY", pets="true")]
    errors = validate_proposed_inventory(prod, promo)
    assert any(e.startswith("duplicate_property") for e in errors)


def test_group_duplicates_deterministic():
    recs = [
        _rec("b", SOURCE_IMPORTER_READY, "X", url="https://x.test/p"),
        _rec("a", SOURCE_PRODUCTION_EXISTING, "X", url="https://x.test/p"),
        _rec("c", SOURCE_IMPORTER_READY, "Y", url="https://y.test/p"),
    ]
    g1 = group_duplicates(recs)
    g2 = group_duplicates(list(reversed(recs)))
    assert g1 == g2
    assert g1[0]["members"] == ["a", "b"]


# --------------------------------------------------------------------------- #
# End-to-end over the real repository data.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.lodging_reconciliation_cli import build_reconciliation  # noqa: E402


@pytest.fixture(scope="module")
def result():
    return build_reconciliation()


def test_real_production_baseline_matches_live_csv(result):
    # Phase-stable: the baseline must equal whatever the live seed CSV holds
    # (20 before the AES-DATA-004I promotion, 25 after) -- the reconciliation
    # is re-runnable and must always reflect current production truth.
    import csv
    from scripts.pettripfinder.lodging_reconciliation_cli import PRODUCTION_CSV
    with PRODUCTION_CSV.open(encoding="utf-8") as f:
        live = sum(1 for r in csv.DictReader(f) if r["category"] == "pet-friendly-hotels")
    assert result["report"]["production_pet_friendly"] == live


def test_real_promotions_are_all_clean_ready(result):
    # Every proposed promotion (zero once the 004I set is already promoted --
    # each READY candidate then duplicates its own production row and is
    # correctly superseded by production continuity) must be clean READY.
    for p in result["promotions"]:
        assert p["recommendation"] == "READY"
        assert p["pets_allowed"] == "true"
        assert p["source_class"] == SOURCE_IMPORTER_READY


def test_real_no_pets_catalog_is_separate(result):
    names = {n["canonical_name"] for n in result["no_pets"]}
    promoted = {p["canonical_name"] for p in result["promotions"]}
    assert len(result["no_pets"]) == 3
    assert not (names & promoted)


def test_real_review_candidates_never_promoted(result):
    review_ids = {r["source_id"] for r in result["review"]}
    promoted_ids = {p["source_id"] for p in result["promotions"]}
    assert not (review_ids & promoted_ids)


def test_real_projection_and_decision(result):
    r = result["report"]
    assert r["projected_verified_pet_friendly_total"] == 25
    assert r["beta_threshold_decision"] == DECISION_BETA_THRESHOLD_REACHED
    assert r["validation_errors"] == []


def test_real_sister_properties_not_merged(result):
    ids = {n["source_id"] for n in result["no_pets"]}
    assert any("intownsuites-com-3deca9da3c" in i for i in ids)      # I-70E
    assert any("intownsuites-com-f8ea21b85e" in i for i in ids)      # Dublin


def test_real_output_is_deterministic():
    a = build_reconciliation()
    b = build_reconciliation()
    assert json.dumps(a["report"], sort_keys=True) == json.dumps(b["report"], sort_keys=True)
    assert json.dumps(a["promotions"], sort_keys=True) == json.dumps(b["promotions"], sort_keys=True)

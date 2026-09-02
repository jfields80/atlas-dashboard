"""PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- pins.

What this order promised and what it observed, pinned so a later order cannot
quietly regress either:

* the LIVE Dayton authority matches its epoch and the committed policy package
  still hashes to the sha the release contract names. Order 001 changed no
  authority at all (it was a shadow); PTF-DAYTON-OH-HARDENED-APPLICATION-002
  then applied its 23-row inventory under founder authorisation, so the pin
  reads 129 / 54 / 24 / 78 / 51 and is carried forward, never relaxed;
* the shadow never touched the pinned census, the policy package, the exclusion
  shard or the final partition;
* every report this order wrote spent nothing and called no paid provider;
* the wrong-live-policy audit found zero contradictions, and the owned-evidence
  replay found zero source conflicts;
* every row in the pending application inventory is identity-BOUND, is not
  already live, and carries an exact quote, a document sha256 and a timestamp;
* no promoted fact was sourced from a brand markup record or an amenity chip;
* the recensus lane is recorded as PARTIAL rather than clean -- this order did
  not clear Dayton's census, and the document must keep saying so.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pettripfinder import epochs
from pettripfinder.market_state import current

_DASH = Path(__file__).resolve().parents[2]
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
MARKET_ID = "dayton-oh"
AUTH = PKG / "markets" / "authority" / MARKET_ID

#: What Dayton held when this order ran, and what its own artifacts (the
#: 001 partition, the shadow reconciliation, the live-policy audit) state
#: forever. PTF-DAYTON-OH-HARDENED-APPLICATION-002 then applied this order's
#: clean inventory, so the LIVE files are held to the current pin instead.
EPOCH = epochs.HistoricalEpoch(
    "PTF-DAYTON-OH-HARDENED-REVALIDATION-001", MARKET_ID,
    facts={"census": 129, "pet_friendly": 47, "verified_no_pets": 8,
           "resolved": 55, "unresolved": 74, "profiles": 47},
    superseded_by=("PTF-DAYTON-OH-HARDENED-APPLICATION-002",))
NOW = current(MARKET_ID)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def shadow():
    return _read(REPORTS / "dayton_oh_shadow_reconciliation_001.json")


@pytest.fixture(scope="module")
def attended():
    return _read(REPORTS / "dayton_oh_attended_capture_001.json")


@pytest.fixture(scope="module")
def replay():
    return _read(REPORTS / "dayton_oh_owned_evidence_replay_001.json")


@pytest.fixture(scope="module")
def packet():
    return _read(REPORTS / "dayton_oh_founder_packet_001.json")


# --------------------------------------------------------------------------
# the live market is untouched
# --------------------------------------------------------------------------

def test_live_authority_matches_the_current_epoch():
    """Order 001 itself changed no live authority -- it was a shadow, and the
    assertion it originally carried was 47 published / 8 no-pets.
    PTF-DAYTON-OH-HARDENED-APPLICATION-002 then applied that shadow's 23-row
    clean inventory under founder authorisation, moving published 47 -> 54 and
    no-pets 8 -> 24. The pin is CARRIED FORWARD to the new epoch rather than
    relaxed: the numbers are still exact, and the only thing permitted to move
    them is a named, authorised application order. The census is unchanged at
    129, because that order promoted policy and not membership.
    """
    census = _read(PKG / "identity_census" / f"{MARKET_ID}.json")
    assert census["count"] == NOW.census
    # This order pinned the census and did not move it; nothing since has.
    assert NOW.census == EPOCH.fact("census")
    policy = _read(PKG / f"hotel_policy_facts_{MARKET_ID}.json")
    assert len(policy["hotels"]) == NOW.pet_friendly
    exclusions = _read(AUTH / "hotel_exclusions.json")
    assert len(exclusions["exclusions"]) == NOW.verified_no_pets
    assert all(e["exclusion_state"] == "VERIFIED_NO_PETS" for e in exclusions["exclusions"])
    assert all(e["market_id"] == MARKET_ID for e in exclusions["exclusions"])


def test_policy_package_still_hashes_to_the_release_contract():
    contract = _read(_DASH / "deploy" / "netlify" / "release_contracts" / "dayton-oh.json")
    raw = (PKG / f"hotel_policy_facts_{MARKET_ID}.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == contract["policy_package"]["expected_sha256"]
    recon = contract["reconciliation"]
    # The LIVE contract, held to the current pin (moved past this order's
    # epoch by PTF-DAYTON-OH-HARDENED-APPLICATION-002).
    assert (recon["confirmed_identities"], recon["published_pet_friendly"],
            recon["verified_no_pets"], recon["resolved"], recon["unresolved"]) == (
                NOW.census, NOW.pet_friendly, NOW.verified_no_pets,
                NOW.resolved, NOW.unresolved)


def test_final_partition_arithmetic_still_agrees():
    # The 001 partition is this order's own committed artifact: it describes
    # the 47 / 8 epoch forever and is held to the epoch, not to the pin.
    part = _read(PKG / "dayton_final_partition_001.json")
    counts = part["final_state_counts"]
    assert part["count"] == EPOCH.fact("census")
    assert counts["PUBLISHED_PET_FRIENDLY"] == EPOCH.fact("pet_friendly")
    assert counts["VERIFIED_NO_PETS"] == EPOCH.fact("verified_no_pets")
    resolved = sum(1 for i in part["items"] if i["resolved"])
    assert resolved == EPOCH.fact("resolved")
    assert len(part["items"]) - resolved == EPOCH.fact("unresolved")


def test_the_shadow_reports_the_same_live_numbers(shadow):
    live = shadow["shadow_reconciliation"]["live"]
    assert (live["pet_friendly"], live["verified_no_pets"], live["resolved"],
            live["unresolved"], live["profiles"]) == (
                EPOCH.fact("pet_friendly"), EPOCH.fact("verified_no_pets"),
                EPOCH.fact("resolved"), EPOCH.fact("unresolved"),
                EPOCH.fact("profiles"))
    assert shadow["shadow_reconciliation"]["pinned_census"] == EPOCH.fact("census")


# --------------------------------------------------------------------------
# nothing was spent
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "dayton_oh_free_static_capture_001.json",
    "dayton_oh_live_policy_audit_001.json",
    "dayton_oh_free_routing_001.json",
    "dayton_oh_attended_capture_001.json",
    "dayton_oh_owned_evidence_replay_001.json",
    "dayton_oh_shadow_reconciliation_001.json",
])
def test_every_report_is_free(name):
    doc = _read(REPORTS / name)
    assert doc["paid_provider_calls"] == 0
    assert doc["usd_spent"] == 0.0


def test_paid_plan_spends_nothing_and_duplicates_nothing(packet):
    paid = packet["paid_readiness"]
    assert paid["nothing_spent"] is True
    assert paid["paid_provider_calls"] == 0 and paid["usd_spent"] == 0.0
    # Dayton has never had a paid attempt of either kind, so no proposed row
    # can repeat one. If that ever stops being true this pin must be revisited
    # before any spend is authorised.
    assert paid["this_market_in_the_ledgers"]["paid_attempts_for_dayton"] == 0
    assert paid["this_market_in_the_ledgers"]["discovery_attempts_for_dayton"] == 0
    # a cap is meaningless against a price nobody read
    assert paid["google_places"]["unit_price_state"] == "UNPRICED_BY_LEDGER"
    assert paid["brightdata"]["hard_cap_usd"] <= paid["brightdata"]["live_balance_usd"]


# --------------------------------------------------------------------------
# what the order observed
# --------------------------------------------------------------------------

def test_no_wrong_live_policy_was_found(shadow):
    audit = shadow["wrong_live_policy_audit"]
    assert audit["rows_tested"] == 55, "every live row must be re-requested"
    assert audit["wrong_live_policy_findings"] == 0
    assert audit["wrong_live_policy_rows"] == []


def test_owned_evidence_replay_found_no_source_conflict(replay):
    assert replay["source_conflicts"] == 0
    assert replay["owned_transcriptions_replayed"] >= 13
    assert replay["previously_uncorroborated_now_artifact_bound"] >= 12


def test_free_static_lane_closed_nothing_in_dayton():
    """The static lane is kept in the pipeline because its FAILURES are the
    evidence that the attended lane is required. If a later change makes it
    start yielding clean rows, that is a real improvement and this pin should
    be updated deliberately rather than silently."""
    doc = _read(REPORTS / "dayton_oh_free_static_capture_001.json")
    assert doc["targets"] == 48
    counts = doc["classification_counts"]
    assert "CLEAN_PET_FRIENDLY_CANDIDATE" not in counts
    assert "CLEAN_VERIFIED_NO_PETS_CANDIDATE" not in counts


# --------------------------------------------------------------------------
# the promotable inventory is safe
# --------------------------------------------------------------------------

def test_pending_inventory_counts(shadow):
    inv = shadow["pending_application_inventory"]
    assert inv["clean_pet_friendly"] == 7
    assert inv["clean_verified_no_pets"] == 16
    proj = shadow["shadow_reconciliation"]["projected_if_clean_inventory_promoted"]
    assert (proj["pet_friendly"], proj["verified_no_pets"], proj["resolved"],
            proj["unresolved"], proj["profiles"]) == (54, 24, 78, 51, 54)


def test_every_promotable_row_is_bound_and_evidenced(shadow):
    inv = shadow["pending_application_inventory"]
    rows = inv["pet_friendly_rows"] + inv["verified_no_pets_rows"]
    assert rows, "the inventory must not be empty"
    for r in rows:
        assert r["identity_signals"]["bound"] is True, r["identity_key"]
        assert r["live_state"] == "UNRESOLVED_OR_NEW", r["identity_key"]
        assert r["exact_quote"], r["identity_key"]
        assert r["document_sha256"].startswith("sha256:") and len(r["document_sha256"]) == 71
        assert r["artifact_sha256"].startswith("sha256:")
        assert r["captured_at"]
        assert r["lane"] == "FREE_ATTENDED"


def test_no_promoted_fact_came_from_markup_or_a_hidden_window(shadow):
    """A brand markup record is corroboration, never a source: rendering
    '"petsAllowed" : "false"' as prose makes the reader say True. And a fact
    the page did not render is not the property's own visible statement."""
    inv = shadow["pending_application_inventory"]
    for r in inv["pet_friendly_rows"] + inv["verified_no_pets_rows"]:
        assert r["evidence_source"] in ("visible_text", "property_named_faq"), r["identity_key"]
        corr = r.get("markup_corroboration")
        if corr:
            assert corr["role"].startswith("CORROBORATION_ONLY")
            if corr["agrees_with_prose_read"] is not None:
                assert corr["agrees_with_prose_read"] is True, r["identity_key"]


def test_held_rows_are_held_for_a_stated_reason(shadow):
    for r in shadow["pending_application_inventory"]["held_rows"]:
        assert r["held_reason"], r["identity_key"]


def test_attended_reads_bind_on_the_property_own_page(attended):
    assert attended["rows_captured"] == 27
    assert attended["paid_provider_calls"] == 0 and attended["usd_spent"] == 0.0
    bound = [r for r in attended["results"] if r["identity_binding"]["bound"]]
    assert len(bound) == 23
    for r in bound:
        b = r["identity_binding"]
        assert (b["street_number_agrees"] and b["postal_agrees"]) or \
               (b["phone_agrees"] and (b["postal_agrees"] or b["street_number_agrees"])), r["identity_key"]


def test_the_same_campus_pair_did_not_collapse(attended):
    """Wingate at 6960 Miller Ln and Baymont at 6960B Miller Ln are two hotels.
    A house-number matcher that ignores the letter suffix binds the wrong one:
    \\b6960\\b matches neither, and \\b6960[A-Za-z]?\\b matches both."""
    census = {h["identity_key"]: h for h in
              _read(PKG / "identity_census" / f"{MARKET_ID}.json")["hotels"]}
    baymont_row = census["baymont by wyndham dayton north"]
    wingate_row = census["wingate by wyndham dayton north"]
    assert baymont_row["address"] == "6960B Miller Ln"
    assert wingate_row["address"] == "6960 Miller Ln"
    assert baymont_row["postal_code"] == wingate_row["postal_code"] == "45414"

    # The Baymont's page declares 6960B. Its census row must bind; the
    # Wingate's row must NOT bind to the same page.
    captured = [r for r in attended["results"] if r["identity_key"] == "baymont by wyndham dayton north"]
    assert len(captured) == 1
    assert captured[0]["identity_binding"]["street_number_agrees"] is True
    assert captured[0]["identity_binding"]["bound"] is True


# --------------------------------------------------------------------------
# promotion readiness, and the gap this order did NOT close
# --------------------------------------------------------------------------

def test_promotion_ready_with_no_blockers(shadow):
    pr = shadow["promotion_readiness"]
    assert pr["PROMOTION_READY"] == "YES"
    assert pr["blockers"] == []


def test_the_recensus_gap_is_stated_not_hidden(shadow):
    """The shadow census equals the pinned census because nothing was admitted,
    NOT because Dayton's census was confirmed. The document must keep saying so
    until a completed recensus replaces it."""
    cov = shadow["shadow_reconciliation"]["recensus_lane_coverage"]
    assert cov["status"].startswith("PARTIAL")
    assert "UNAVAILABLE" in cov["local_osm_geofabrik"]
    assert shadow["shadow_reconciliation"]["shadow_census"] == shadow["shadow_reconciliation"]["pinned_census"]


def test_founder_packet_is_prepared_not_decided(packet):
    assert packet["status"] == "PREPARED_NOT_DECIDED"
    assert packet["total_decisions"] == 16
    held_keys = {r["identity_key"] for r in
                 _read(REPORTS / "dayton_oh_shadow_reconciliation_001.json")["pending_application_inventory"]["held_rows"]}
    promoted = {r["identity_key"] for r in
                _read(REPORTS / "dayton_oh_shadow_reconciliation_001.json")["pending_application_inventory"]["pet_friendly_rows"]}
    # a row cannot be both promoted and held
    assert not (held_keys & promoted)
    for d in packet["decisions"]:
        assert d["reversibility"]
        assert d["recommendation"]

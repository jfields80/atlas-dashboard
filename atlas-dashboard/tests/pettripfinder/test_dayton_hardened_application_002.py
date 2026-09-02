"""PTF-DAYTON-OH-HARDENED-APPLICATION-002 -- pins.

What this order changed and what it deliberately did not, pinned so a later
order cannot quietly regress either:

* Dayton moved 47 -> 54 published and 8 -> 24 verified-no-pets, and its census
  did NOT move: it is still 129. This order promoted POLICY, not membership;
* the partition partitions -- 129 = 54 + 24 + 51, with no overlap and no
  identity missing;
* every applied record is identity-bound on the property's own premises, and the
  two same-street hazards (6960/6960B Miller Ln, 1190/1195 Russ Road) bound to
  distinct rows;
* no published fact came from a brand markup record or an amenity chip;
* ``service_animal_statement`` is the STRUCTURED committed shape and never a
  bare quote -- a string there crashes the production renderer;
* the seed inventory is exactly one row per published identity, and no excluded
  identity appears in it;
* every held founder decision is outside the applied cohort;
* census COVERAGE is still not confirmed, and the contract still says so.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

_DASH = Path(__file__).resolve().parents[2]
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
MARKET = "dayton-oh"
AUTH = PKG / "markets" / "authority" / MARKET


def _read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def policy():
    return _read(PKG / ("hotel_policy_facts_%s.json" % MARKET))


@pytest.fixture(scope="module")
def exclusions():
    return _read(AUTH / "hotel_exclusions.json")


@pytest.fixture(scope="module")
def partition():
    return _read(PKG / "dayton_final_partition_002.json")


@pytest.fixture(scope="module")
def census():
    return _read(PKG / "identity_census" / ("%s.json" % MARKET))


@pytest.fixture(scope="module")
def contract():
    return _read(_DASH / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET))


@pytest.fixture(scope="module")
def application():
    return _read(REPORTS / "dayton_oh_application_002.json")


# ------------------------------------------------------------------ counts

def test_the_application_moved_exactly_what_it_claimed(application):
    assert application["mode"] == "APPLIED"
    assert application["cohort_size"] == 23
    assert application["verdict_counts"] == {"APPLIED_PET_FRIENDLY": 7,
                                             "APPLIED_VERIFIED_NO_PETS": 16}
    assert application["policy_rows_added"] == 7
    assert application["exclusions_added"] == 16
    assert application["paid_provider_calls"] == 0 and application["usd_spent"] == 0.0


def test_authority_counts(policy, exclusions, census):
    assert len(policy["hotels"]) == 54
    assert len(exclusions["exclusions"]) == 24 == exclusions["count"]
    assert all(e["exclusion_state"] == "VERIFIED_NO_PETS" for e in exclusions["exclusions"])
    assert all(e["market_id"] == MARKET for e in exclusions["exclusions"])
    # the census did NOT move
    assert census["count"] == 129 == len(census["hotels"])


def test_the_partition_partitions(partition):
    items = partition["items"]
    assert partition["count"] == 129 == len(items)
    counts = {}
    for i in items:
        counts[i["final_state"]] = counts.get(i["final_state"], 0) + 1
    assert counts["PUBLISHED_PET_FRIENDLY"] == 54
    assert counts["VERIFIED_NO_PETS"] == 24
    resolved = sum(1 for i in items if i["resolved"])
    assert resolved == 78
    assert len(items) - resolved == 51
    assert 129 == 54 + 24 + 51
    keys = [i["identity_key"] for i in items]
    assert len(keys) == len(set(keys)), "an identity appears twice in the partition"


def test_no_identity_is_both_published_and_excluded(policy, exclusions, census):
    from scripts.pettripfinder import hotel_exclusions as HX
    rows = {h["identity_key"]: h for h in census["hotels"]}
    excluded_names = {e["normalized_name"] for e in exclusions["exclusions"]}
    excluded = {k for k, h in rows.items()
                if HX.normalize_name(h["canonical_name"]) in excluded_names}
    published = {r["identity_key"] for r in policy["hotels"]}
    assert not (published & excluded)
    assert published <= set(rows), "a published identity is absent from the pinned census"
    assert excluded <= set(rows), "an excluded identity is absent from the pinned census"


# ------------------------------------------------------- evidence integrity

def test_every_applied_row_is_identity_bound(application):
    applied = [r for r in application["rows"] if r["verdict"].startswith("APPLIED_")]
    assert len(applied) == 23
    for r in applied:
        b = r["identity_binding"]
        assert b["bound"] is True, r["identity_key"]
        assert (b["street_number_agrees"] and b["postal_agrees"]) or \
               (b["phone_agrees"] and (b["postal_agrees"] or b["street_number_agrees"])), r["identity_key"]


def test_the_two_same_street_hazards_bound_distinctly(application):
    """6960 Miller Ln (Wingate) vs 6960B (Baymont), and 1190 Russ Rd (Quality
    Inn Greenville) vs 1195 (Holiday Inn Express Greenville). A house-number
    matcher that ignores the suffix, or that matches a prefix, binds the wrong
    hotel -- silently, and with a confident-looking result."""
    tokens = {r["identity_key"]: r["identity_binding"]["census_house_token"]
              for r in application["rows"] if r["verdict"].startswith("APPLIED_")}
    assert tokens["baymont by wyndham dayton north"] == "6960B"
    assert tokens["holiday inn express and suites greenville"] == "1195"
    assert tokens["quality inn greenville"] == "1190"


def test_no_two_applied_rows_share_an_address_fingerprint(application):
    """The SPA guard: a batched browser read that returned the previous
    property's DOM shows up as two rows carrying identical address lines."""
    assert "SPA_PREVIOUS_PROPERTY" in application["guards"]
    assert not [r for r in application["rows"]
                if r["verdict"] == "REJECTED_SPA_PREVIOUS_PROPERTY_SUSPECTED"]


def test_published_records_carry_publication_grade_evidence(policy):
    new = [r for r in policy["hotels"]
           if any("HARDENED-APPLICATION-002" in c
                  for c in ((r.get("approval") or {}).get("caveats") or []))]
    assert len(new) == 7
    for r in new:
        assert r["verification_state"] == "VERIFIED_PET_FRIENDLY"
        assert r["facts"].get("pets_allowed") is True
        assert r["evidence"], r["identity_key"]
        for e in r["evidence"]:
            assert e["artifact_class"] == "PUBLICATION_GRADE_EVIDENCE"
            assert e["artifact_sha256"].startswith("sha256:")
            assert e["source_grade"] == "PT1_FIRST_PARTY"
            assert e["quote"]
        assert r["worker_result_hash"]
        assert (r.get("approval") or {}).get("record_hash", "").startswith("sha256:")


def test_service_animal_statement_is_the_structured_shape(policy):
    """canonical_view reads ``service_animal.get("stated")``. A bare quote string
    there raises AttributeError inside the production renderer, which is how this
    was caught: the assembly crashed rather than shipping a wrong page."""
    from scripts.pettripfinder.contracts import enums
    for r in policy["hotels"]:
        sa = r.get("service_animal_statement")
        if sa is None:
            continue
        assert isinstance(sa, dict), r["identity_key"]
        assert sa.get("stated") is True
        assert sa.get("charges_stated") in enums.SERVICE_ANIMAL_CHARGE_STATES


def test_a_fee_the_prose_never_stated_is_absent_not_withheld(policy):
    """Silence is not a withholding, and markup is not a source.

    Both IHG pages say "Pets are welcome at <property>" and name no price. The
    fee exists only in the brand's markup record, which this order treats as
    corroboration and never as a source, so the published facts carry
    pets_allowed alone.

    It is NOT recorded as a withheld field either. A withholding says a decision
    was made about something the source stated; recording one for a field the
    page never addressed would tell a reader the hotel withheld something it
    never had -- the same reason PTF-POLICY-SCHEMA-MIGRATION-001 dropped its 110
    silence restatements rather than recoding them.
    """
    ihg = [r for r in policy["hotels"]
           if r["identity_key"] in ("holiday inn express and suites dayton huber heights",
                                    "holiday inn express and suites washington court house")]
    assert len(ihg) == 2
    for r in ihg:
        assert r["facts"] == {"pets_allowed": True}, "only what the prose stated"
        assert "pet_fee" not in (r.get("withheld_fields") or {}), r["identity_key"]
        assert "withheld_facts" not in r, "the committed key is withheld_fields"


def test_every_withholding_carries_a_code_and_cites_evidence(policy):
    """Where a withholding IS recorded, it must be groupable and checkable."""
    from scripts.pettripfinder.contracts import enums
    seen = 0
    for r in policy["hotels"]:
        for field, decision in (r.get("withheld_fields") or {}).items():
            seen += 1
            assert decision["reason_code"] in enums.WITHHELD_FIELD_REASONS, field
            assert decision["reason"]
            assert decision.get("evidence_refs"), (r["identity_key"], field)
    assert seen, "Dayton carries withholdings; this must not silently pass on zero"


def test_exclusions_are_property_specific_and_hashed(exclusions):
    new = [e for e in exclusions["exclusions"] if "APPLICATION-002" in (e.get("notes") or "")]
    assert len(new) == 16
    for e in new:
        assert e["exclusion_state"] == "VERIFIED_NO_PETS"
        assert e["evidence_quote"] and e["source_url"] and e["source_hash"]
        assert e["record_hash"].startswith("sha256:")
        assert e["approval_hash"].startswith("sha256:")
        assert re.search(r"not allowed|no pets|not permitted|do not allow", e["evidence_quote"], re.I), \
            e["exclusion_id"]


# --------------------------------------------------------- surface & contract

def test_seed_inventory_is_one_row_per_published_identity(policy):
    import csv
    from scripts.pettripfinder.site_data import normalize_name
    rows = list(csv.DictReader((AUTH / "seed_businesses.csv").open(encoding="utf-8-sig")))
    names = [normalize_name(r["name"]) for r in rows]
    assert len(names) == len(set(names)) == 54
    assert set(names) == {r["identity_key"] for r in policy["hotels"]}
    premises = [(r["address"].strip().lower(), r["postal_code"].strip())
                for r in rows if r["address"].strip()]
    assert len(premises) == len(set(premises)), "two seed rows share one premises"


def test_the_contract_states_the_applied_authority(contract, policy):
    raw = (PKG / ("hotel_policy_facts_%s.json" % MARKET)).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == contract["policy_package"]["expected_sha256"]
    assert contract["policy_package"]["expected_record_count"] == 54
    r = contract["reconciliation"]
    assert (r["confirmed_identities"], r["published_pet_friendly"], r["verified_no_pets"],
            r["resolved"], r["unresolved"]) == (129, 54, 24, 78, 51)
    assert contract["public_surface"]["public_hotel_profile_count"] == 54
    assert contract["public_surface"]["seed_hotel_rows"] == 54
    assert contract["routes"]["hotel_route_count"] == 54
    assert contract["routes"]["published_corridor_route_count"] == 13
    assert contract["deployment_authorization"]["grants_deployment"] is False


def test_the_contract_still_refuses_to_claim_census_completeness(contract):
    note = contract["identity_census"]["note"]
    assert "CENSUS COVERAGE IS NOT CONFIRMED" in note
    assert "OSM" in note and "Marriott" in note


def test_the_recovery_view_still_partitions_the_unresolved_total(contract):
    doc = _read(PKG / "identity_census" / "dayton-recovery-002-proposed-authority.json")
    total = len(doc["candidates_still_proposed"]) + len(doc["remaining_unresolved"])
    assert total == contract["reconciliation"]["unresolved"] == 51
    assert len(doc["candidates"]) == 14, "the historical candidate record must not be edited"


# ------------------------------------------------------------ founder holds

def test_no_held_founder_decision_blocks_the_application(application):
    packet = _read(REPORTS / "dayton_oh_founder_packet_002.json")
    assert packet["status"] == "PREPARED_NOT_DECIDED"
    assert packet["blocks_application"] is False
    applied = {r["identity_key"] for r in application["rows"]
               if r["verdict"].startswith("APPLIED_")}
    held = [d for d in packet["decisions"] if d["status"] == "HELD"]
    assert not (applied & {d["identity_key"] for d in held})
    assert packet["counts"]["carried_in"] == 16
    assert packet["counts"]["still_held"] == 10

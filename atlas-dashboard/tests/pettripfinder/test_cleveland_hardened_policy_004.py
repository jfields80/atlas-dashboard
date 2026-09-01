"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-004 -- pins.

* live authority still byte-identical to the Order-001 snapshot;
* the shadow census v004 is the Order-003 shadow plus the one row admitted
  after a first-party postal proof, with no duplicate key, no duplicate
  premises beyond the recorded Copley campus, and the held identities
  (successors, same-campus, non-lodging) NOT applied;
* every clean policy result binds on the page's own premises and quotes a
  property sentence; a reader false negative is a founder exception with the
  page's own words, never a silent page;
* the Richfield question is determined as two identities and held, not merged;
* every document this order wrote spent nothing and touched nothing live.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

_DASH = Path(__file__).resolve().parents[2]
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _exists(p: Path):
    if not p.exists():
        pytest.skip("%s not written in this checkout" % p.name)
    return _read(p)


def test_live_authority_unchanged_since_order_001_snapshot():
    if (PKG / "cleveland_akron_canton_oh_promotion_report_005.json").exists():
        pytest.skip("epoch pin: PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005 promoted the live "
                    "state under founder authorization (pinned by test_cleveland_hardened_application_005.py)")
    snapshot = _read(PKG / f"{M}_hardened_snapshot_001.json")
    changed = [rel for rel, meta in snapshot["protected_files"].items() if hashlib.sha256((_DASH / rel).read_bytes()).hexdigest() != meta["sha256"]]
    assert changed == [], changed


def test_shadow_v004_is_v003_plus_the_postal_proven_row_and_holds_are_not_applied():
    shadow = _exists(PKG / "identity_census_admission" / f"{MARKET_ID}.json")
    assert "admission_004" in shadow and "admission_003" in shadow
    adm = shadow["admission_004"]
    assert adm["pinned_census_touched"] is False and adm["deployment"] == "NONE"
    keys = [h["identity_key"] for h in shadow["hotels"]]
    assert len(keys) == len(set(keys)) and shadow["count"] == len(keys)
    assert shadow["count"] == adm["supersedes_003"]["count"] + len(adm["added_after_postal_proof"])
    by = {h["identity_key"]: h for h in shadow["hotels"]}
    for key in adm["added_after_postal_proof"]:
        h = by[key]
        assert h["batch"] == "hardened-policy-004" and h["admission"]["status"] == "SHADOW_ADMITTED_004"
        assert h["admission"]["classification"] == "CONFIRMED_TRUE_MISSING" and h["admission"]["document_sha256"]
        assert re.match(r"^\d+\s", h["address"]) and re.match(r"^44\d{3}$", h["postal_code"]) and h["policy_state"] == "POLICY_NOT_VERIFIED"
    # held identities: the successor keys are not renamed, the HIE is not admitted, the non-lodging rows are still rows
    assert "cambria hotel and suites avon" in by and "wyndham avon" not in by
    assert "woodspring suites cleveland" in by and "extended stay america select suites cleveland airport" not in by
    assert "holiday inn express and suites cleveland richfield" not in by and "motel 6 richfield" in by
    for key in ("harbor inn", "hopp inn", "villa croatia at the american croatian lodge"):
        assert key in by
    prem = Counter()
    for h in shadow["hotels"]:
        toks = [t for t in re.findall(r"[a-z0-9]+", h["address"].lower()) if t not in ("e", "w", "n", "s", "east", "west", "north", "south", "ne", "nw", "se", "sw")]
        if toks and toks[0].isdigit():
            prem[(toks[0], toks[1][:4] if len(toks) > 1 else "", h["postal_code"])] += 1
    assert {k for k, v in prem.items() if v > 1} <= {("130", "mont", "44321")}


def test_policy_reads_004_clean_rows_are_bound_and_quoted_and_exceptions_carry_the_page_words():
    doc = _exists(REPORTS / f"{M}_policy_reads_004.json")
    assert doc["paid_provider_calls"] == 0 and doc["usd_spent"] == 0.0
    rows = {r["identity_key"]: r for r in doc["rows"]}
    counts = doc["classification_counts"]
    assert sum(counts.values()) == doc["targets"] == doc["cohort_size"]
    for c in doc["classification"]:
        r = rows.get(c["identity_key"])
        if c["classification"] in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"):
            if r["lane"] == "STATIC":
                assert str(r["observation"]["publication_grade"].get("verdict", "")).endswith("CONFIRMED")
                assert any(len((e.get("quote") or "").split()) > 2 for e in r["observation"]["evidence"]), c["identity_key"]
            else:
                assert r["identity_binding"]["bound"] is True, c["identity_key"]
                assert r["reader_source"] == "visible_text"
                assert len((r["reader"].get("pets_allowed_quote") or "").split()) >= 2, c["identity_key"]
                assert r["reader"]["pets_allowed"] is (c["classification"] == "CLEAN_PET_FRIENDLY")
            assert c["evidence"]["document_sha256"], c["identity_key"]
        elif c["classification"] == "FOUNDER_EXCEPTION":
            assert "page states" in c["why"] or "bare phrase" in c["why"], c["why"]
        elif c["classification"] == "CAPTURE_FAILED":
            assert "hilton.com" in c["why"]
    # the reader false negatives are exceptions, never silence
    assert counts.get("SOURCE_SILENT", 0) == 0 and counts.get("POLICY_NOT_FOUND", 0) == 0
    # the owned-evidence reuse loaded no page
    lq = rows["la quinta inn and suites by wyndham cleveland airport west"]
    assert lq["lane"] == "OWNED_EVIDENCE_REUSE" and lq["source_artifact"].startswith("data/worker_runs/pettripfinder/cleveland-attended-capture-003/")


def test_state_004_richfield_is_two_identities_held_and_inventory_is_consistent():
    doc = _exists(REPORTS / f"{M}_policy_state_004.json")
    reads = _exists(REPORTS / f"{M}_policy_reads_004.json")
    assert doc["live_authority_touched"] is False and doc["pinned_census_touched"] is False and doc["deployment"] == "NONE"
    p6 = doc["phase_6_richfield"]
    assert p6["determination"].startswith("A. TWO_DISTINCT_IDENTITIES_SAME_ADDRESS")
    assert p6["signals"]["same_phone"] is False and p6["signals"]["same_brand_family"] is False
    assert p6["status"].startswith("DETERMINED_HELD")
    holds = {h["n"]: h for h in doc["phase_7_holds"]}
    assert len(holds) == 7
    assert holds[3]["status"] == "RESOLVED_MECHANICALLY" and holds[3]["exact_evidence"]["page_property_data"]["postalCode"] == "44312"
    assert all(holds[n]["status"] != "RESOLVED_MECHANICALLY" for n in (1, 2, 4, 5, 6, 7))
    inv = doc["phase_10_pending_application"]
    assert inv["LIVE"] == {"pet_friendly": 99, "verified_no_pets": 40}
    assert inv["live_policy_package_written"] is False and inv["live_exclusions_written"] is False
    pend = inv["PENDING_SHADOW"]
    clean_pf = {c["identity_key"] for c in reads["classification"] if c["classification"] == "CLEAN_PET_FRIENDLY"}
    clean_np = {c["identity_key"] for c in reads["classification"] if c["classification"] == "CLEAN_VERIFIED_NO_PETS"}
    held = set(pend["held_with_evidence"])
    assert clean_pf - held <= set(pend["pet_friendly"]) and clean_np - held <= set(pend["verified_no_pets"])
    assert not (set(pend["pet_friendly"]) & set(pend["verified_no_pets"]))
    assert "holiday inn express and suites cleveland richfield" in held and "extended stay america select suites cleveland airport" in held
    proj = inv["PROJECTED_IF_APPLIED"]
    assert proj["pet_friendly"] == 99 + len(pend["pet_friendly"]) and proj["verified_no_pets"] == 40 + len(pend["verified_no_pets"])
    pilot = doc["phase_12_paid_readiness"]["pilot_plan_not_executed"]
    assert pilot["executed"] is False and pilot["authorized"] is False
    ready = doc["phase_13_promotion_readiness"]
    assert ready["PROMOTION_READY"] is True and ready["further_coverage"].startswith("OPTIONAL")
    assert doc["phase_14_factory_performance"]["paid_spend_usd"] == 0.0


@pytest.mark.parametrize("name", ["policy_reads_004", "policy_state_004"])
def test_every_004_report_spent_nothing(name):
    doc = _exists(REPORTS / f"{M}_{name}.json")
    text = json.dumps(doc)
    assert doc.get("provider_calls", doc.get("paid_provider_calls", 0)) == 0
    assert float(doc.get("usd_spent", 0.0)) == 0.0
    assert "C:\\\\Atlas" not in text and "C:/Atlas" not in text and "AppData" not in text


def test_grouped_packet_004_groups_what_remains_with_effects_and_reversibility():
    pk = _exists(PKG / f"{M}_grouped_founder_packet_004.json")
    assert pk["nothing_was_spent"] is True and pk["nothing_was_published"] is True
    assert set(pk["groups"]) == {"A_identity_successor_or_same_campus", "B_non_lodging_retirements", "C_reader_exceptions_with_exact_quotes"}
    for items in pk["groups"].values():
        for it in items:
            for field in ("current_identity", "proposed_action", "exact_evidence", "conflicting_evidence", "recommendation", "census_effect", "authority_effect", "route_effect", "reversibility"):
                assert it.get(field) not in (None, ""), (it.get("identity_key"), field)
    assert "red roof inn akron" in pk["resolved_mechanically_this_order"]
    assert "red roof inn akron" not in pk["held"]

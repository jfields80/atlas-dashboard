"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-003 -- pins.

* live authority still byte-identical to the Order-001 snapshot;
* the shadow census v003 is the Order-002 shadow plus explicitly assigned
  Oakwood rows and brand-locator rows only, with no duplicate key, no
  duplicate premises beyond the recorded Copley campus, and identity keys
  preserved under the full-name overlays;
* every clean policy result binds on the page's own street + postal and
  quotes a property sentence; a bare phrase never counts as clean;
* every document this order wrote spent nothing.
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


def test_shadow_v003_composition_and_uniqueness():
    shadow = _exists(PKG / "identity_census_admission" / f"{MARKET_ID}.json")
    assert "admission_003" in shadow
    keys = [h["identity_key"] for h in shadow["hotels"]]
    assert len(keys) == len(set(keys))
    assert shadow["count"] == len(keys)
    batches = Counter(h.get("batch") for h in shadow["hotels"])
    assert batches["hardened-policy-003"] == shadow["admission_003"]["added_oakwood_explicit"] + shadow["admission_003"]["added_locator_leads"]
    for h in shadow["hotels"]:
        if h.get("batch") != "hardened-policy-003":
            continue
        assert re.match(r"^\d+\s", h["address"]) and re.match(r"^44\d{3}$", h["postal_code"])
        assert h["policy_state"] == "POLICY_NOT_VERIFIED"
        assert h["admission"]["classification"] == "CONFIRMED_TRUE_MISSING"
        if h["postal_code"] == "44146":
            assert h["assignment_basis"] == "explicit" and h["corridor"].endswith("cleveland-east-beachwood")
    prem = Counter()
    for h in shadow["hotels"]:
        toks = [t for t in re.findall(r"[a-z0-9]+", h["address"].lower()) if t not in ("e", "w", "n", "s", "east", "west", "north", "south", "ne", "nw", "se", "sw")]
        if toks and toks[0].isdigit():
            prem[(toks[0], toks[1][:4] if len(toks) > 1 else "", h["postal_code"])] += 1
    dups = {k for k, v in prem.items() if v > 1}
    assert dups <= {("130", "mont", "44321")}, dups  # the recorded Copley same-campus pair


def test_full_name_overlays_preserve_identity_keys():
    shadow = _exists(PKG / "identity_census_admission" / f"{MARKET_ID}.json")
    by = {h["identity_key"]: h for h in shadow["hotels"]}
    for key, full in (("the westin", "The Westin Cleveland Downtown"), ("towneplace suites by marriott", "TownePlace Suites by Marriott Cleveland Solon"), ("sonesta es suites cleveland westlake", "Sonesta Simply Suites Cleveland Westlake")):
        assert key in by, key
        assert by[key]["display_name"] == full
        assert by[key]["display_name_overlay_003"]["identity_key_preserved"] is True
        assert by[key]["canonical_name"] == _read(PKG / "identity_census" / f"{MARKET_ID}.json")["hotels"][[h["identity_key"] for h in _read(PKG / "identity_census" / f"{MARKET_ID}.json")["hotels"]].index(key)]["canonical_name"]


def test_policy_reads_clean_rows_are_bound_and_quoted():
    doc = _exists(REPORTS / f"{M}_policy_reads_003.json")
    assert doc["paid_provider_calls"] == 0 and doc["usd_spent"] == 0.0
    rows = {r["identity_key"]: r for r in doc["rows"]}
    for c in doc["classification"]:
        if c["classification"] in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"):
            r = rows[c["identity_key"]]
            if r["lane"] == "ATTENDED":
                assert r["identity_binding"]["bound"] is True
                assert len((r["reader"].get("pets_allowed_quote") or "").split()) >= 2, c["identity_key"]
                assert r["reader"]["pets_allowed"] is (c["classification"] == "CLEAN_PET_FRIENDLY")
            else:
                assert str(r["observation"]["publication_grade"].get("verdict", "")).endswith("CONFIRMED")
                assert any(len((e.get("quote") or "").split()) > 2 for e in r["observation"]["evidence"]), c["identity_key"]
    counts = doc["classification_counts"]
    assert sum(counts.values()) == doc["targets"] == 23


@pytest.mark.parametrize("name", ["policy_reads_003", "policy_state_003"])
def test_every_003_report_spent_nothing(name):
    doc = _exists(REPORTS / f"{M}_{name}.json")
    text = json.dumps(doc)
    assert doc.get("provider_calls", doc.get("paid_provider_calls", 0)) == 0
    assert float(doc.get("usd_spent", 0.0)) == 0.0
    assert "C:\\\\Atlas" not in text and "C:/Atlas" not in text and "AppData" not in text


def test_state_003_keeps_live_and_projected_apart_and_promotion_not_ready():
    doc = _exists(REPORTS / f"{M}_policy_state_003.json")
    inv = doc["phase_12_policy_inventory"]
    assert inv["LIVE"] == {"pet_friendly": 99, "verified_no_pets": 40}
    assert inv["live_policy_package_written"] is False and inv["live_exclusions_written"] is False
    assert inv["PROJECTED_IF_APPLIED"]["pet_friendly"] == 99 + len(inv["PENDING_SHADOW"]["pet_friendly"])
    assert doc["phase_15_promotion_readiness"]["PROMOTION_READY"] is False
    assert doc["phase_14_pilot_plan_not_executed"]["executed"] is False

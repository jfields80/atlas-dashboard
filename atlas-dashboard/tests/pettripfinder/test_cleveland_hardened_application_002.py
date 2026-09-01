"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-002 -- pins.

* live authority, pinned census, release contract and deployment manifest are
  still byte-identical to the Order-001 snapshot;
* the shadow admission census is pinned - retired + admitted, with the
  Studio 6 supersession carrying its predecessor, and every admitted row
  first-party confirmed on a numbered street + postal, unique, in market;
* the three no-pets and the successor PF rows rest on artifacts whose sha256
  re-derives, and nothing was written to the live package or exclusions;
* every document this order wrote spent nothing.
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
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _exists(path: Path):
    if not path.exists():
        pytest.skip("%s not written in this checkout" % path.name)
    return _read(path)


def test_live_authority_unchanged_since_order_001_snapshot():
    snapshot = _read(PKG / f"{M}_hardened_snapshot_001.json")
    changed = [rel for rel, meta in snapshot["protected_files"].items()
               if hashlib.sha256((_DASH / rel).read_bytes()).hexdigest() != meta["sha256"]]
    assert changed == [], changed


def test_shadow_admission_is_pinned_minus_retired_plus_admitted():
    shadow = _exists(PKG / "identity_census_admission" / f"{MARKET_ID}.json")
    pinned = _read(PKG / "identity_census" / f"{MARKET_ID}.json")
    app = _read(PKG / f"{M}_shadow_application_002.json")
    retired = {r["identity_key"] for r in app["C_non_lodging_retirements"]}
    admitted = [h for h in shadow["hotels"] if str((h.get("admission") or {}).get("status", "")).startswith("SHADOW_ADMITTED")]
    assert shadow["admission"]["pinned_census_touched"] is False
    assert shadow["count"] == len(shadow["hotels"]) == len(pinned["hotels"]) - len(retired) + len(admitted)
    assert len(retired) == 3 and len(shadow["retired_non_lodging_002"]) == 3
    keys = [h["identity_key"] for h in shadow["hotels"]]
    assert len(keys) == len(set(keys)), "duplicate identity key in the shadow"
    assert not retired & set(keys), "a retired row is still a hotel identity"
    # every pinned, non-retired, non-superseded row survives unchanged
    superseded = {s["from"] for s in shadow["supersessions_002"]}
    shadow_by = {h["identity_key"]: h for h in shadow["hotels"]}
    # A later order may overlay a pinned row (display name, address supersession, lodging
    # confirmation) but must say so with a marker field; anything else must be byte-identical.
    overlay_markers = ("display_name_overlay_003", "address_supersession_003", "lodging_confirmation_003")
    overlay_fields = {"display_name", "official_url", "has_official_link", "address", "lodging_state"}
    for h in pinned["hotels"]:
        if h["identity_key"] in retired or h["identity_key"] in superseded:
            continue
        got = shadow_by[h["identity_key"]]
        if any(m in got for m in overlay_markers):
            stripped = {k: v for k, v in got.items() if k not in overlay_fields and k not in overlay_markers}
            assert stripped == {k: v for k, v in h.items() if k not in overlay_fields}, h["identity_key"]
        else:
            assert got == h, h["identity_key"]


def test_supersession_keeps_its_predecessor_and_is_one_hotel():
    shadow = _exists(PKG / "identity_census_admission" / f"{MARKET_ID}.json")
    succ = [h for h in shadow["hotels"] if h.get("superseded_from")]
    assert len(succ) == 1
    row = succ[0]
    assert row["superseded_from"]["identity_key"] == "studio 6 extended stay hotel mentor"
    assert row["superseded_from"]["resolution"] == "SAME_IDENTITY_REBRAND_SUCCESSOR"
    assert row["identity_key"] == "suburban studios mentor cleveland northeast"
    assert "studio 6 extended stay hotel mentor" not in {h["identity_key"] for h in shadow["hotels"]}
    assert row["address"].startswith("7677 ") and row["postal_code"] == "44060"


def test_every_admitted_row_is_first_party_confirmed_and_unique():
    shadow = _exists(PKG / "identity_census_admission" / f"{MARKET_ID}.json")
    market = _read(PKG / "markets" / f"{MARKET_ID}.json")
    declared = {pc for c in market["corridors"] for pc in (c.get("included_postal_codes") or [])}
    pinned_postals = {(h.get("postal_code") or "")[:5] for h in _read(PKG / "identity_census" / f"{MARKET_ID}.json")["hotels"]}
    premises = set()
    for h in shadow["hotels"]:
        adm = h.get("admission") or {}
        if adm.get("status") != "SHADOW_ADMITTED_002":
            continue
        assert adm["classification"] == "CONFIRMED_TRUE_MISSING"
        assert re.match(r"^\d+\s", h["address"]), h
        assert re.match(r"^44\d{3}$", h["postal_code"]), h
        assert h["postal_code"] in declared | pinned_postals, h
        assert h["policy_state"] == "POLICY_NOT_VERIFIED"
        key = (re.match(r"(\d+)", h["address"]).group(1), h["postal_code"])
        assert key not in premises, "two admitted rows share a premises"
        premises.add(key)
        assert adm["document_sha256"] or adm["read_method"] == "ATTENDED", h


def test_shadow_application_rests_on_rederivable_artifacts_and_touches_nothing_live():
    app = _exists(PKG / f"{M}_shadow_application_002.json")
    raw = _DASH / "data" / "worker_runs" / "pettripfinder" / "cleveland-hardened-attended-001" / "raw"
    assert app["live_authority_touched"] is False and app["pinned_census_touched"] is False
    assert app["provider_calls"] == 0 and app["usd_spent"] == 0.0
    assert len(app["A_clean_verified_no_pets"]) == 3
    live_pf = {p["identity_key"] for p in _read(PKG / f"hotel_policy_facts_{MARKET_ID}.json")["hotels"]}
    for row in app["A_clean_verified_no_pets"]:
        assert row["exclusion_state"] == "VERIFIED_NO_PETS" and row["identity_key"] not in live_pf
        assert row["checks"]["refusal_is_property_specific"] and row["checks"]["identity_bound_street_and_postal"]
        art = raw / row["artifact_file"]
        if art.exists():
            assert hashlib.sha256(art.read_bytes()).hexdigest() == row["artifact_sha256"]
    b = app["B_successor_pet_friendly"]
    assert b["one_hotel_not_two"] is True and b["policy"]["pets_allowed"] is True
    assert b["policy"]["pet_fee"]["amount_cents"] == 1000 and b["policy"]["weight_limit"]["value"] == 30 and b["policy"]["pet_count_limit"] == 2
    assert app["D_same_campus_resolution"]["resolution_type"] == "same_campus_distinct_entity"
    assert app["F_kimpton_schofield"]["authority_touched"] is False and app["F_kimpton_schofield"]["shared_reader_modified"] is False


@pytest.mark.parametrize("name", ["application_rulings_002", "identity_read_cohort_002", "identity_reads_002", "shadow_state_002"])
def test_every_002_report_spent_nothing(name):
    doc = _exists(REPORTS / f"{M}_{name}.json")
    text = json.dumps(doc)
    assert doc.get("provider_calls", doc.get("paid_provider_calls", 0)) == 0
    assert float(doc.get("usd_spent", 0.0)) == 0.0
    assert "C:\\\\Atlas" not in text and "C:/Atlas" not in text and "AppData" not in text


def test_identity_reads_never_admit_on_a_name_alone():
    doc = _exists(REPORTS / f"{M}_identity_reads_002.json")
    for r in doc["classification"]:
        if r["classification"] == "CONFIRMED_TRUE_MISSING":
            pi = r["page_identity"]
            assert re.match(r"^\d+", pi.get("street") or ""), r["cohort_id"]
            assert re.match(r"^44\d{3}$", pi.get("postal_code") or ""), r["cohort_id"]
            assert not r.get("registered_rows_sharing_premises"), r["cohort_id"]
            assert not r.get("cross_market_collisions"), r["cohort_id"]

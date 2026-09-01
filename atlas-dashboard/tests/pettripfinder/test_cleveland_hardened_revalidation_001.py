"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- pins.

What this order promised and what it observed, pinned so a later order cannot
quietly regress either:

* the LIVE Cleveland authority is byte-identical to the phase-1 snapshot;
* the shadow recensus never touched the pinned census;
* the new discovery config covers every included municipality;
* every report this order wrote spent nothing;
* a name never decided an identity match in the reconciliation;
* the generic reader defect the replay exposed (negation adjacency across
  list items) is recorded as a STRICT xfail -- the reader is unchanged under
  the factory freeze, and the day it is fixed this test will fail loudly and
  must be flipped.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import pytest

_DASH = Path(__file__).resolve().parents[2]
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def snapshot():
    return _read(PKG / f"{M}_hardened_snapshot_001.json")


def test_snapshot_counts_are_the_live_market(snapshot):
    c = snapshot["counts"]
    assert c["census_identities"] == 188
    assert c["policy_package_rows"] == 99
    assert c["verified_no_pets_exclusions"] == 40
    assert c["unresolved_manifest_items"] == 49
    assert c["hotel_routes"] == 99
    assert snapshot["release_contract"]["policy_package_sha256_matches"] is True
    assert snapshot["release_contract"]["grants_deployment"] is False


def test_every_protected_live_file_is_byte_identical_to_the_snapshot(snapshot):
    if (PKG / "cleveland_akron_canton_oh_promotion_report_005.json").exists():
        pytest.skip("epoch pin: the 001 snapshot froze the PRE-promotion live state; "
                    "PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005 promoted it under founder "
                    "authorization and the promoted state is pinned by test_cleveland_hardened_application_005.py")
    changed = []
    for rel, meta in snapshot["protected_files"].items():
        now = hashlib.sha256((_DASH / rel).read_bytes()).hexdigest()
        if now != meta["sha256"]:
            changed.append(rel)
    assert changed == [], "this order must not change live Cleveland authority: %s" % changed


def test_owned_evidence_custody_has_no_disagreement(snapshot):
    ev = snapshot["owned_evidence"]
    assert ev["custody_disagrees"] == 0
    assert ev["artifacts"] == 173


def test_shadow_recensus_never_touches_the_pinned_census():
    if (PKG / "cleveland_akron_canton_oh_promotion_report_005.json").exists():
        pytest.skip("epoch pin: the pinned census was 188 while this order ran; "
                    "PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005 promoted it to 220 under founder "
                    "authorization (pinned by test_cleveland_hardened_application_005.py)")
    shadow_path = PKG / "identity_census" / "recensus" / f"{MARKET_ID}.json"
    if not shadow_path.exists():
        pytest.skip("shadow recensus not written in this checkout")
    pinned = _read(PKG / "identity_census" / f"{MARKET_ID}.json")
    shadow = _read(shadow_path)
    assert shadow["shadow"]["pinned_census_touched"] is False
    assert shadow["hotels"][: len(pinned["hotels"])] == pinned["hotels"]
    assert shadow["count"] == len(shadow["hotels"]) >= 188
    for row in shadow["hotels"][188:]:
        assert row["policy_state"] == "POLICY_NOT_VERIFIED"
        assert row["admission"]["status"].startswith("SHADOW_")


def test_discovery_config_loads_and_every_municipality_is_inside_a_cell():
    from scripts.pettripfinder.discovery.market_config import load_market_config

    cfg = load_market_config(MARKET_ID)
    raw = _read(_DASH / "scripts" / "pettripfinder" / "discovery" / "config" / "cleveland_akron_canton_oh.json")
    points = raw["municipality_reference_points"]
    assert len(cfg.cells) == 24
    for name in raw["included_municipalities"]:
        pt = points[name]
        inside = False
        for cell in cfg.cells:
            d_lat = (cell.center_lat - pt["lat"]) * 111_000
            d_lng = (cell.center_lng - pt["lng"]) * 111_000 * math.cos(math.radians(pt["lat"]))
            if math.hypot(d_lat, d_lng) <= cell.radius_meters:
                inside = True
                break
        assert inside, "%s is outside every discovery cell" % name


def test_ohio_extract_is_registered_for_cleveland():
    reg = _read(_DASH / "scripts" / "pettripfinder" / "discovery" / "config" / "osm_extracts.json")
    rows = [r for r in reg["extracts"] if MARKET_ID in r["markets"]]
    assert len(rows) == 1 and rows[0]["extract_id"] == "geofabrik-ohio"


@pytest.mark.parametrize("name", [
    "census_audit_005", "evidence_replay_006", "unresolved_rebuild_007", "routing_recovery_008",
    "free_static_capture_009", "live_audit_010", "shadow_reconciliation_004", "paid_readiness_014",
    "brand_directory_harvest_003", "geography_002", "hardened_projection_013",
])
def test_every_report_spent_nothing(name):
    path = REPORTS / f"{M}_{name}.json"
    if not path.exists():
        pytest.skip("%s not written in this checkout" % name)
    doc = _read(path)
    text = json.dumps(doc)
    assert doc.get("paid_provider_calls", 0) == 0
    assert float(doc.get("usd_spent", 0.0)) == 0.0
    assert "C:\\\\Atlas" not in text and "C:/Atlas" not in text, "no machine path may leak into a committed report"


def test_a_name_never_decided_a_match_in_the_reconciliation():
    path = REPORTS / f"{M}_shadow_reconciliation_004.json"
    if not path.exists():
        pytest.skip("reconciliation not written in this checkout")
    doc = _read(path)
    for r in doc["results"]:
        if r["classification"] == "ALREADY_REGISTERED_ALIAS":
            assert r.get("deciding_matches") or r.get("proposing_signals"), r
        if r["classification"] == "TRUE_MISSING_IDENTITY":
            assert r["in_market"] and r["address"] and r["postal_code"], r


def test_replay_found_no_unexplained_live_contradiction():
    path = REPORTS / f"{M}_evidence_replay_006.json"
    if not path.exists():
        pytest.skip("replay not written in this checkout")
    doc = _read(path)
    # The one contradiction the replay raised is the reader defect pinned
    # below (Kimpton Schofield); anything else is a genuine regression.
    keys = {c["identity_key"] for c in doc["live_contradictions"]}
    assert keys <= {"kimpton schofield hotel"}, keys


@pytest.mark.xfail(strict=True, reason=(
    "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 observed: in a list block "
    "'... No limit on number of pets allowed / No deposit or cleaning fees charged' the "
    "generic reader lets the following item's 'No' negate 'pets allowed' and reads "
    "pets_allowed=False on a page that states pets are welcome. Reader unchanged under the "
    "factory freeze; flip this test when the adjacency rule is fixed."))
def test_reader_negation_adjacency_across_list_items():
    from scripts.pettripfinder.brightdata import policy_reading as PR

    block = "No limit on number of pets allowed No deposit or cleaning fees charged"
    reading = PR.parse(block, strategy="pin")
    result = PR.to_extraction(reading, location=MARKET_ID)
    assert result.extraction.get("pets_allowed") is not False

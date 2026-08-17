"""PTF-INDIANAPOLIS-DECISION-APPLICATION-001 — executed, unpublished."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts import policy_schema
from scripts.pettripfinder.hotel_exclusions import validate as validate_exclusions
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash
from scripts.pettripfinder.site_data import load_published_hotel_policy_facts

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_application_wrote_four_no_pets_and_eight_live_governed_facts():
    app = _json(PACKAGE / "indianapolis_decision_application_001.json")
    assert app["executed"] is True
    assert app["published"] is True
    assert app["status"] == "LIVE_PUBLISHED"
    facts = _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")
    assert facts["published"] is True
    assert len(facts["hotels"]) == 8
    keys = {h["identity_key"] for h in facts["hotels"]}
    assert len(keys) == 8
    assert "hilton garden inn indianapolis airport" in keys
    hgi = next(h for h in facts["hotels"]
               if h["identity_key"] == "hilton garden inn indianapolis airport")
    assert "species" not in hgi["facts"]
    west = next(h for h in facts["hotels"]
                if h["identity_key"] == "hampton inn and suites indianapolis west speedway")
    cents = sorted(t["amount_cents"] for t in west["facts"]["fee_tiers"])
    assert cents == [9320, 15530]
    mer = next(h for h in facts["hotels"]
               if h["identity_key"] == "le meridien indianapolis")
    assert "scope" not in mer["facts"]["weight_limit"]
    assert mer["facts"]["pet_fee"]["amount_cents"] == 0
    hie = next(h for h in facts["hotels"]
               if h["identity_key"] == "holiday inn express plainfield")
    assert hie["facts"]["species"] == {"dogs": "accepted"}
    assert "pet_count_scope" not in hie["facts"]
    residence = next(h for h in facts["hotels"]
                     if h["identity_key"] == "residence inn by marriott indianapolis airport")
    assert "reservation_requirement" not in residence["facts"]
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        assert hotel["published"] is True
        assert approval["decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
        assert approval["operator"] == "jfields80"
        assert approval["founder_decision_id"]
        assert approval["founder_decision_source"].endswith(".json")
        signed = dict(hotel)
        signed.pop("approval")
        assert approval["record_hash"] == record_hash(signed)
        assert approval["evidence_hash"] == evidence_hash(hotel["evidence"])
    issues = [i for i in policy_schema.validate_package(facts)
              if not (i.code == "MISSING_REQUIRED" and "weight_limit.scope" in i.path)]
    assert issues == []
    excl = validate_exclusions(_json(PACKAGE / "hotel_exclusions.json"))
    indy = [e for e in excl if e.get("market_id") == "indianapolis-in"]
    assert len(indy) == 4
    downtown = next(e for e in indy if "downtown" in e["exclusion_id"])
    assert "Airport" not in downtown["evidence_quote"]
    assert set(load_published_hotel_policy_facts("indianapolis-in")) == keys

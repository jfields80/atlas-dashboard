"""PTF-INDIANAPOLIS-DECISION-APPLICATION-001 — executed, unpublished."""

from __future__ import annotations

import json
from pathlib import Path

from pettripfinder.indianapolis_promoted_state import (
    PROMOTED_PET_FRIENDLY, PROMOTED_SEED_ROWS, PROMOTED_VERIFIED_NO_PETS)

from scripts.pettripfinder.contracts import policy_schema
from scripts.pettripfinder.hotel_exclusions import validate as validate_exclusions
from scripts.pettripfinder.site_data import load_published_hotel_policy_facts

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_application_wrote_four_no_pets_and_eight_live_governed_facts():
    """The 001 application record is unchanged; the LIVE package it once governed was
    superseded by PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004 (24 founder-signed profiles, 24 exclusions)."""
    app = _json(PACKAGE / "indianapolis_decision_application_001.json")
    assert app["executed"] is True
    assert app["published"] is True
    assert app["status"] == "LIVE_PUBLISHED"
    facts = _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")
    assert facts["published"] is True
    assert len(facts["hotels"]) == PROMOTED_PET_FRIENDLY
    keys = {h["identity_key"] for h in facts["hotels"]}
    assert len(keys) == PROMOTED_PET_FRIENDLY
    # Retired at 004 for lack of fresh publication-grade evidence
    # (BUDGET_DEFERRED / ALTERNATE_LANE). Hilton Garden Inn Airport stopped
    # being retired when PTF-INDIANAPOLIS-BACKLOG-ACQUISITION-016 bought its
    # page and the founder signed it, so the guard now covers only the row
    # that is still unevidenced.
    assert "residence inn by marriott indianapolis airport" not in keys
    west = next(h for h in facts["hotels"]
                if h["identity_key"] == "hampton inn and suites indianapolis west speedway")
    cents = sorted(t["amount_cents"] for t in west["facts"]["fee_tiers"])
    assert cents == [9320, 15530]
    mer = next(h for h in facts["hotels"]
               if h["identity_key"] == "le meridien indianapolis")
    # founder decision 1: an unqualified blanket maximum publishes as lte / per_pet
    assert mer["facts"]["weight_limit"] == {"value": 50.0, "unit": "lb", "operator": "lte", "scope": "per_pet"}
    # the stale live facts (fee $0, 40 lb) were superseded by the fresh page
    assert mer["facts"]["pet_fee"] == {"amount_cents": 2500, "currency": "USD", "basis": "per_stay", "scope": "per_room"}
    hie = next(h for h in facts["hotels"]
               if h["identity_key"] == "holiday inn express plainfield")
    assert hie["facts"]["species"] == {"dogs": "accepted"}
    assert "pet_count_scope" not in hie["facts"]
    for hotel in facts["hotels"]:
        assert hotel["founder_decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
        assert hotel["founder_reviewer_id"] == "PTF-FOUNDER-001"
        assert hotel["founder_reviewed_at"]
    assert list(policy_schema.validate_package(facts)) == []
    excl = validate_exclusions(_json(PACKAGE / "hotel_exclusions.json"))
    indy = [e for e in excl if e.get("market_id") == "indianapolis-in"]
    assert len(indy) == PROMOTED_VERIFIED_NO_PETS
    downtown = next(e for e in indy
                    if e["exclusion_id"] == "ii-crowne-plaza-indianapolis-downtown-union-station")
    assert "Airport" not in downtown["evidence_quote"]
    # load_published_hotel_policy_facts keys by the package's ROUTE key,
    # which is derived from the canonical NAME; `keys` above is the set of
    # census identity keys. The two diverge wherever a canonical-name
    # correction has been applied -- Louisville carries eight such rows and
    # St. Louis four, and PTF-INDIANAPOLIS-FINAL-ZERO-COST-CLEANUP-018 gave
    # Indianapolis its first ("Tru" -> "Tru by Hilton Indianapolis
    # Downtown"). Comparing the two fields only ever passed because this
    # market had no corrections; compare like for like.
    published = load_published_hotel_policy_facts("indianapolis-in")
    assert set(published) == {h["key"] for h in facts["hotels"]}
    assert {h["identity_key"] for h in facts["hotels"]} == keys

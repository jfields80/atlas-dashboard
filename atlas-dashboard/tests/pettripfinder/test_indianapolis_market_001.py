"""PTF-INDIANAPOLIS-MARKET-REVALIDATION-001 -- Indianapolis factory gates."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from scripts.pettripfinder.assemble_production_site import (
    market_eligibility, select_markets,
)
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.markets import load_markets, market_by_id
from scripts.pettripfinder.normalize_census_geography import recompute
from scripts.pettripfinder.release_contracts import available_market_ids

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = PACKAGE / "identity_census" / "indianapolis-in.json"
PARTITION_PATH = PACKAGE / "indianapolis_final_partition_001.json"
QUEUE_DIR = (
    ROOT / "data" / "operator_evidence" / "indianapolis-founder-review-001"
    / "outgoing" / "work-browser-pass-001"
)
UTIL_DIR = ROOT / "data" / "market_research" / "indianapolis" / "utilities"
MARKET = "indianapolis-in"
COMMITTED = (
    "columbus-oh", "cleveland-akron-canton-oh", "dayton-oh", "cincinnati-oh",
)
EXPECTED_CORRIDORS = {
    "indianapolis-in__downtown": 34,
    "indianapolis-in__airport": 19,
    "indianapolis-in__keystone-castleton": 15,
    "indianapolis-in__carmel": 10,
    "indianapolis-in__plainfield": 10,
    "indianapolis-in__greenwood": 10,
    "indianapolis-in__northwest": 9,
    "indianapolis-in__fishers": 9,
    "indianapolis-in__east-i70": 9,
    "indianapolis-in__hendricks-west": 6,
    "indianapolis-in__south": 6,
    "indianapolis-in__westfield": 4,
    "indianapolis-in__noblesville": 4,
    "indianapolis-in__speedway": 4,
    "indianapolis-in__broad-ripple": 2,
    "indianapolis-in__mass-ave": 1,
    "indianapolis-in__north-central": 1,
}


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_census_schema_and_count():
    doc = _json(CENSUS_PATH)
    assert doc["schema"] == enums.CENSUS_SCHEMA
    assert doc["market_id"] == MARKET
    assert doc["count"] == len(doc["hotels"]) == 153
    assert doc["base_commit"] == "fea73de1ec699289cf04b88fd7069cf23fa4d735"
    assert census.validate(doc, market_states=["IN"]) == ()


def test_partition_reconciles_by_set():
    census_doc = _json(CENSUS_PATH)
    part = _json(PARTITION_PATH)
    rec = partition.reconcile(census.identity_keys(census_doc), part,
                              market_id=MARKET)
    assert rec.agrees
    assert rec.published == 8
    assert rec.verified_no_pets == 4
    assert rec.out_of_category == 0
    assert rec.unresolved == 141
    assert rec.published + rec.verified_no_pets + rec.out_of_category + rec.unresolved \
        == rec.census_count
    assert partition.validate(part) == ()


NO_PETS = {
    "crowne plaza indianapolis airport",
    "courtyard by marriott indianapolis castleton",
    "crowne plaza indianapolis downtown union station",
    "fairfield inn and suites indianapolis airport",
}
CONFIRMED = {
    "holiday inn express plainfield",
    "le meridien indianapolis",
    "residence inn by marriott indianapolis airport",
    "hampton inn and suites indianapolis airport",
    "hampton inn and suites indianapolis keystone",
    "hampton inn and suites indianapolis west speedway",
    "hampton inn indianapolis northeast castleton",
    "hilton garden inn indianapolis airport",
}


def test_every_policy_state_is_not_verified_except_applied_rows():
    refused = []
    confirmed = []
    for row in _json(CENSUS_PATH)["hotels"]:
        assert row["market_id"] == MARKET
        assert row["state"] == "IN"
        if row["identity_key"] in NO_PETS:
            assert row["policy_state"] == enums.VERIFIED_NO_PETS
            refused.append(row["identity_key"])
        elif row["identity_key"] in CONFIRMED:
            assert row["policy_state"] == enums.POLICY_CONFIRMED
            confirmed.append(row["identity_key"])
        else:
            assert row["policy_state"] == enums.POLICY_NOT_VERIFIED
    assert set(refused) == NO_PETS
    assert set(confirmed) == CONFIRMED


def test_no_identity_shared_with_committed_markets():
    indy = {r["identity_key"] for r in _json(CENSUS_PATH)["hotels"]}
    census_dir = PACKAGE / "identity_census"
    for path in sorted(census_dir.glob("*.json")):
        if path.name.startswith("indianapolis"):
            continue
        if "proposed" in path.name:
            continue
        document = _json(path)
        # Current main also carries review/quarantine sidecars in this
        # directory; only a census document has hotel identities to compare.
        if "hotels" not in document:
            continue
        foreign = {r["identity_key"] for r in document["hotels"]
                   if r.get("identity_key")}
        assert indy.isdisjoint(foreign), "%s: %s" % (
            path.name, sorted(indy & foreign)[:8])
    for market_id in COMMITTED:
        assert (census_dir / ("%s.json" % market_id)).is_file()


def test_cincinnati_indiana_identities_are_absent():
    indy = {r["identity_key"] for r in _json(CENSUS_PATH)["hotels"]}
    cincinnati = _json(PACKAGE / "identity_census" / "cincinnati-oh.json")
    cin_in = {r["identity_key"] for r in cincinnati["hotels"] if r["state"] == "IN"}
    assert cin_in
    assert indy.isdisjoint(cin_in)
    forbidden_zips = {"47001", "47025", "47040", "47012"}
    assert not {r["postal_code"][:5] for r in _json(CENSUS_PATH)["hotels"]} \
        & forbidden_zips


def test_every_canonical_lodging_has_one_corridor():
    market = market_by_id(load_markets(), MARKET)
    corridors = {c.corridor_id for c in market.corridors}
    for row in _json(CENSUS_PATH)["hotels"]:
        assert row["corridor"] in corridors
        assert row["assignment_basis"] in (
            "explicit", "postal_code", "city_state")


def test_corridor_counts_match_measured_table():
    counts = Counter(r["corridor"] for r in _json(CENSUS_PATH)["hotels"])
    assert dict(counts) == EXPECTED_CORRIDORS
    assert sum(counts.values()) == 153


def test_assignment_is_reproducible():
    _document, changes = recompute(MARKET)
    assert changes == []


def test_no_zip_is_registered_twice():
    market = market_by_id(load_markets(), MARKET)
    owners = {}
    for corridor in market.corridors:
        for code in corridor.included_postal_codes:
            owners.setdefault(code, []).append(corridor.corridor_id)
    for code, matched in owners.items():
        assert len(matched) == 1, (code, matched)


def test_queue_equals_unresolved_partition():
    rollup = QUEUE_DIR / "work-browser-pass-001-review.csv"
    if not rollup.is_file():
        raise AssertionError("founder-review outgoing package missing: %s" % QUEUE_DIR)
    census_doc = _json(CENSUS_PATH)
    part = _json(PARTITION_PATH)
    census_by_key = {r["identity_key"]: r for r in census_doc["hotels"]}
    part_by_key = {i["identity_key"]: i for i in part["items"]}
    unresolved = {i["identity_key"] for i in part["items"]
                  if i["final_state"] not in enums.TERMINAL_STATES}
    with rollup.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    keys = [r["identity_key"] for r in rows]
    assert len(unresolved) == 141
    assert unresolved == set(census_by_key) - NO_PETS - CONFIRMED
    assert set(keys) >= unresolved
    assert len(keys) == len(set(keys)) == 152
    for row in rows:
        key = row["identity_key"]
        assert key in census_by_key
        assert key in part_by_key
        assert census_by_key[key]["identity_key"] == key
        assert part_by_key[key]["identity_key"] == key
        if row.get("hotel_id"):
            assert row["hotel_id"] == key
        assert row["next_action"].strip()
        assert row["review_status"] == "NOT_STARTED"
        assert row["batch_id"].startswith("batch-")


def test_queue_batches_are_about_ten():
    batches = list(QUEUE_DIR.glob("batch-*-review.csv"))
    assert batches
    for path in batches:
        with path.open(encoding="utf-8", newline="") as fh:
            n = sum(1 for _ in csv.DictReader(fh))
        assert 1 <= n <= 10


def test_live_production_authority_is_complete_and_holds_stay_non_public():
    facts = PACKAGE / "hotel_policy_facts_indianapolis-in.json"
    assert facts.is_file()
    doc = _json(facts)
    assert doc["published"] is True
    assert doc["market_id"] == MARKET
    assert len(doc["hotels"]) == 8
    assert MARKET in available_market_ids()
    routing = json.loads((PACKAGE / "identity_routing.json").read_text(
        encoding="utf-8-sig"))
    assert not [r for r in routing["routes"] if r.get("market_id") == MARKET]
    seed = (PACKAGE / "seed_businesses.csv").read_text(encoding="utf-8")
    assert seed.count(",indianapolis-in") == 8
    exclusions = json.loads((PACKAGE / "hotel_exclusions.json").read_text(
        encoding="utf-8-sig"))
    records = exclusions["exclusions"] if isinstance(exclusions, dict) else exclusions
    indy_ex = [e for e in records if e.get("market_id") == MARKET]
    assert {e["exclusion_id"] for e in indy_ex} == {
        "indy-crowne-plaza-indianapolis-airport",
        "indy-courtyard-indianapolis-castleton",
        "indy-crowne-plaza-indianapolis-downtown-union-station",
        "indy-fairfield-inn-suites-indianapolis-airport",
    }
    assert all(e["exclusion_state"] == enums.VERIFIED_NO_PETS for e in indy_ex)
    release = ROOT / "deploy" / "netlify" / "release_contracts" / "indianapolis-in.json"
    assert release.exists()


def test_assembler_finds_indianapolis_source_ready_after_live_authority_application():
    """Source readiness is unchanged by PTF-046: every assembly condition
    holds. Whether the market JOINS the composed bundle is the founder's
    separate launch decision (deploy/netlify/launch_participation.json),
    which withheld Indianapolis from the first multi-market launch on
    coverage, not correctness -- so it is source-ready and not selected."""
    markets = load_markets()
    row = market_eligibility(market_by_id(markets, MARKET))
    assert row["assemblable"] is True
    assert all(row["conditions"].values())
    assert row["launch_status"] == \
        "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"
    assert row["participates"] is False
    chosen, _rows = select_markets(markets)
    assert MARKET not in [m.market_id for m in chosen]


def test_utilities_have_provenance_and_revalidation():
    files = list(UTIL_DIR.glob("*.json"))
    assert files, "utility inventory missing"
    for path in files:
        doc = _json(path)
        assert doc.get("as_of")
        assert "needs_reverification" in doc
        for item in doc.get("items") or ():
            assert item.get("evidence_url"), item.get("name")
            assert item.get("verification_status")
            hours = (item.get("operating_hours") or "").lower()
            if "24/7" in hours or "24-hour" in hours or item.get("is_24_7"):
                quote = (item.get("evidence_quote") or "").lower()
                assert "24" in quote, item.get("name")


def test_identity_keys_derive_from_names():
    for row in _json(CENSUS_PATH)["hotels"]:
        assert row["identity_key"] == ptf_identity_key(row["canonical_name"])


def test_identity_state_counts_are_preserved():
    counts = _json(CENSUS_PATH)["identity_state_counts"]
    assert counts == {
        "IDENTITY_CONFIRMED": 64,
        "IDENTITY_PROVISIONAL": 86,
        "IDENTITY_UNRESOLVED": 3,
    }


def test_pass1_identity_repair_bound_url_property_codes():
    by_key = {r["identity_key"]: r for r in _json(CENSUS_PATH)["hotels"]}
    expected = {
        "comfort inn indianapolis airport plainfield": "in082",
        "comfort suites indianapolis airport": "in293",
        "courtyard by marriott indianapolis airport": "indca",
        "courtyard by marriott indianapolis castleton": "indcs",
        "crowne plaza indianapolis airport": "indap",
        "crowne plaza indianapolis downtown union station": "inddt",
        "delta hotels by marriott indianapolis airport": "indde",
        "embassy suites by hilton indianapolis downtown": "indwses",
    }
    for key, code in expected.items():
        assert by_key[key]["property_code"] == code
    assert by_key["baymont by wyndham plainfield indianapolis airport area"]["property_code"] == ""
    assert by_key["best western plus indianapolis northwest"]["property_code"] == ""

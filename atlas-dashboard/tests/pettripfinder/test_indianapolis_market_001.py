"""PTF-INDIANAPOLIS-MARKET-REVALIDATION-001 -- Indianapolis factory gates."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from pettripfinder.indianapolis_promoted_state import (  # noqa: F401
    EXCLUSION_IDS,
    PROMOTED_PET_FRIENDLY, PROMOTED_SEED_ROWS, PROMOTED_VERIFIED_NO_PETS, CENSUS)

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
# 004 until PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 rebuilt the partition over the promoted 263-identity census.
# The CURRENT partition. Repointed 014 -> 023 by
# PTF-INDIANAPOLIS-PROMOTION-AND-APPLICATION-004, which rebuilt it over the
# 264-identity census. PARTITION_001_PATH below is this order's OWN historical
# artifact and stays where it is -- the two are deliberately different things.
PARTITION_PATH = PACKAGE / "indianapolis_in_final_partition_023.json"
PARTITION_001_PATH = PACKAGE / "indianapolis_final_partition_001.json"
QUEUE_DIR = (
    ROOT / "data" / "operator_evidence" / "indianapolis-founder-review-001"
    / "outgoing" / "work-browser-pass-001"
)
UTIL_DIR = ROOT / "data" / "market_research" / "indianapolis" / "utilities"
MARKET = "indianapolis-in"
COMMITTED = (
    "columbus-oh", "cleveland-akron-canton-oh", "dayton-oh", "cincinnati-oh",
)
# PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: corridor counts of the promoted 257-identity census.
EXPECTED_CORRIDORS = {
    # Measured on the 257-identity census of PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004;
    # re-measured on the 263-identity census promoted by PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 (twelve admissions,
    # five retirements, one rebrand-successor rename, and Airport South assigned
    # explicitly to the airport corridor at ZIP 46221).
    "indianapolis-in__downtown": 40,
    "indianapolis-in__northwest": 29,
    "indianapolis-in__airport": 27,
    "indianapolis-in__keystone-castleton": 25,
    "indianapolis-in__east-i70": 23,
    "indianapolis-in__plainfield": 22,
    "indianapolis-in__south": 19,
    "indianapolis-in__carmel": 15,
    "indianapolis-in__fishers": 14,
    "indianapolis-in__greenwood": 13,
    "indianapolis-in__speedway": 10,
    "indianapolis-in__hendricks-west": 8,
    "indianapolis-in__noblesville": 7,
    "indianapolis-in__westfield": 5,
    "indianapolis-in__broad-ripple": 3,
    "indianapolis-in__north-central": 2,
    "indianapolis-in__mass-ave": 1,
}


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_census_schema_and_count():
    doc = _json(CENSUS_PATH)
    assert doc["schema"] == enums.CENSUS_SCHEMA
    assert doc["market_id"] == MARKET
    assert doc["count"] == len(doc["hotels"]) == CENSUS  # 257 (004) -> 263 (014)
    assert doc["promotion"]["plan_work_order"] == "PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014"
    assert doc["promotion_history"][0]["plan_work_order"] == "PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003"
    assert census.validate(doc, market_states=["IN"]) == ()


def test_partition_reconciles_by_set():
    census_doc = _json(CENSUS_PATH)
    part = _json(PARTITION_PATH)
    rec = partition.reconcile(census.identity_keys(census_doc), part,
                              market_id=MARKET)
    assert rec.agrees
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: the generic-path partition is a factory artifact (AWAITING_* states);
    # the authority is pinned below from the package and the exclusion shard.
    # -> the 014 partition carries the promoted authority as terminal states.
    assert rec.published == PROMOTED_PET_FRIENDLY
    assert rec.verified_no_pets == PROMOTED_VERIFIED_NO_PETS
    assert rec.out_of_category == 0
    assert rec.unresolved == CENSUS - PROMOTED_PET_FRIENDLY - PROMOTED_VERIFIED_NO_PETS
    assert rec.published + rec.verified_no_pets + rec.out_of_category + rec.unresolved \
        == rec.census_count
    assert partition.validate(part) == ()


# The 001 authority (kept for the historical queue tests below).
NO_PETS_001 = {
    "crowne plaza indianapolis airport",
    "courtyard by marriott indianapolis castleton",
    "crowne plaza indianapolis downtown union station",
    "fairfield inn and suites indianapolis airport",
}
CONFIRMED_001 = {
    "holiday inn express plainfield",
    "le meridien indianapolis",
    "residence inn by marriott indianapolis airport",
    "hampton inn and suites indianapolis airport",
    "hampton inn and suites indianapolis keystone",
    "hampton inn and suites indianapolis west speedway",
    "hampton inn indianapolis northeast castleton",
    "hilton garden inn indianapolis airport",
}
# PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: the promoted authority, 24 + 24.
NO_PETS = {
    "comfort inn indianapolis airport plainfield",
    "courtyard by marriott indianapolis airport",
    "courtyard by marriott indianapolis at the capitol",
    "courtyard by marriott indianapolis downtown",
    "courtyard by marriott indianapolis fishers",
    "courtyard indianapolis noblesville",
    "courtyard indianapolis plainfield",
    "courtyard indianapolis west speedway",
    "crowne plaza indianapolis airport",
    "crowne plaza indianapolis downtown union station",
    "fairfield inn and suites indianapolis carmel",
    "fairfield inn and suites indianapolis downtown",
    "fairfield inn and suites indianapolis east",
    "holiday inn express and suites greenwood",
    "holiday inn express and suites indianapolis north carmel",
    "holiday inn express and suites indianapolis w airport area",
    "holiday inn express indianapolis downtown",
    "holiday inn express indianapolis fishers an ihg hotel",
    "holiday inn indianapolis downtown",
    "jw marriott indianapolis",
    "springhill suites by marriott indianapolis carmel",
    "springhill suites by marriott indianapolis westfield",
    "springhill suites indianapolis airport plainfield",
    "springhill suites indianapolis downtown",
}
CONFIRMED = {
    "baymont indianapolis south",
    "baymont noblesville",
    "candlewood suites indianapolis medical district",
    "days inn and suites by wyndham indianapolis airport east",
    "embassy suites by hilton indianapolis downtown",
    "embassy suites by hilton indianapolis north",
    "fairfield inn and suites indianapolis northwest",
    "hampton inn and suites indianapolis airport",
    "hampton inn and suites indianapolis keystone",
    "hampton inn and suites indianapolis west speedway",
    "hampton inn indianapolis downtown across from circle centre",
    "hampton inn indianapolis northeast castleton",
    "hampton inn indianapolis northwest park 100",
    "holiday inn express and suites carmel north westfield",
    "holiday inn express and suites indianapolis northwest",
    "holiday inn express plainfield",
    "la quinta inn and suites by wyndham indianapolis downtown",
    "la quinta inn indianapolis airport executive dr",
    "le meridien indianapolis",
    "residence inn by marriott indianapolis downtown on the canal",
    "staybridge suites indianapolis airport plainfield",
    "super 8 by wyndham indianapolis south",
    "the alexander autograph collection",
    "the westin indianapolis",
}


def test_every_policy_state_is_not_verified_except_applied_rows():
    """PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: on the generic path the census carries no policy annotation
    (POLICY_NOT_VERIFIED everywhere, as Louisville and St. Louis do); the
    authority lives in the package and the exclusion shard, whose identities
    must all be census rows."""
    keys = set()
    for row in _json(CENSUS_PATH)["hotels"]:
        assert row["market_id"] == MARKET
        assert row["state"] == "IN"
        assert row["policy_state"] == enums.POLICY_NOT_VERIFIED
        keys.add(row["identity_key"])
    assert NO_PETS <= keys
    assert CONFIRMED <= keys
    assert not (NO_PETS & CONFIRMED)


def test_no_identity_shared_with_committed_markets():
    """PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: the identities that PUBLISH (package + exclusions) are unique across
    markets. Bare chain names in the unresolved census cohort ("home2 suites by
    hilton") can recur across generic-path censuses and never reach authority."""
    indy = NO_PETS | CONFIRMED
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
    """The measured corridor table of this order, held as a floor.

    PTF-INDIANAPOLIS-PROMOTION-REMEDIATION-005 scoped this. Exact equality made
    the table a ceiling as well as a floor, so admitting ONE identity to a
    corridor read as the corridor assignment being wrong. What the measurement
    was actually for is that no corridor silently LOSES hotels and none of them
    disappears -- both still asserted, exactly, below. A later admission is
    allowed to raise a count and nothing else is.
    """
    counts = Counter(r["corridor"] for r in _json(CENSUS_PATH)["hotels"])
    for corridor, measured in EXPECTED_CORRIDORS.items():
        assert corridor in counts, "%s lost every hotel it had" % corridor
        assert counts[corridor] >= measured, (
            "%s fell from %d to %d" % (corridor, measured, counts[corridor]))
    assert set(counts) == set(EXPECTED_CORRIDORS), (
        "a corridor appeared or vanished since the measurement")
    assert sum(counts.values()) == len(_json(CENSUS_PATH)["hotels"])
    assert sum(counts.values()) == CENSUS


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
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: this queue was cut from the 001 partition, which stays committed.
    part = _json(PARTITION_001_PATH)
    part_by_key = {i["identity_key"]: i for i in part["items"]}
    unresolved = {i["identity_key"] for i in part["items"]
                  if i["final_state"] not in enums.TERMINAL_STATES}
    with rollup.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    keys = [r["identity_key"] for r in rows]
    assert len(unresolved) == 141
    assert unresolved == set(part_by_key) - NO_PETS_001 - CONFIRMED_001
    assert set(keys) >= unresolved
    assert len(keys) == len(set(keys)) == 152
    for row in rows:
        key = row["identity_key"]
        assert key in part_by_key
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
    assert len(doc["hotels"]) == PROMOTED_PET_FRIENDLY
    assert MARKET in available_market_ids()
    routing = json.loads((PACKAGE / "identity_routing.json").read_text(
        encoding="utf-8-sig"))
    assert not [r for r in routing["routes"] if r.get("market_id") == MARKET]
    seed = (PACKAGE / "seed_businesses.csv").read_text(encoding="utf-8")
    assert seed.count(",indianapolis-in") == PROMOTED_SEED_ROWS
    exclusions = json.loads((PACKAGE / "hotel_exclusions.json").read_text(
        encoding="utf-8-sig"))
    records = exclusions["exclusions"] if isinstance(exclusions, dict) else exclusions
    indy_ex = [e for e in records if e.get("market_id") == MARKET]
    # The exclusion ids this order established, held as a cohort rather than as
    # the whole set: every refusal it recorded must still be recorded, under the
    # same id. A later order may add refusals; it may not drop one of these.
    assert set(EXCLUSION_IDS) <= {e["exclusion_id"] for e in indy_ex}
    assert all(e["exclusion_state"] == enums.VERIFIED_NO_PETS for e in indy_ex)
    release = ROOT / "deploy" / "netlify" / "release_contracts" / "indianapolis-in.json"
    assert release.exists()


def test_assembler_finds_indianapolis_source_ready_and_now_selected():
    """Source readiness was never what PTF-046 withheld.

    Every assembly condition held throughout: 046 withheld the market on
    COVERAGE, and whether it joins the composed bundle has always been the
    founder's separate launch decision in
    deploy/netlify/launch_participation.json. PTF-INDIANAPOLIS-LAUNCH-
    PARTICIPATION-019 reversed that decision, and not one byte of the market's
    source had to change for the reversal to take effect -- which is the whole
    point of keeping participation out of the authority."""
    markets = load_markets()
    row = market_eligibility(market_by_id(markets, MARKET))
    assert row["assemblable"] is True
    assert all(row["conditions"].values())
    assert row["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"
    assert row["participates"] is True
    chosen, _rows = select_markets(markets)
    assert MARKET in [m.market_id for m in chosen]


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
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: every promoted row is IDENTITY_CONFIRMED (the recensus re-derived identity).
    assert counts == {"IDENTITY_CONFIRMED": CENSUS}


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
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: the generic census carries the code inside the official URL,
    # read brand-scoped by the exclusion contract's own extractor.
    from scripts.pettripfinder.hotel_exclusions import brand_scoped_property_identity
    expected["embassy suites by hilton indianapolis downtown"] = "indwwes"   # the page's own code
    for key, code in expected.items():
        assert brand_scoped_property_identity(by_key[key]["official_url"])[1] == code, key
    # This row USED to carry a Wyndham URL, and the assertion proved the
    # extractor reads brand WYNDHAM with no property code from it -- a Wyndham
    # URL that names no code must not silently become a code.
    # PTF-INDIANAPOLIS-PROMOTION-AND-APPLICATION-004 REMOVED that route: the
    # page it pointed at states 6010 Gateway Drive and 317-203-9321, which are
    # the census street and telephone of "baymont inn and suites plainfield
    # indianapolis airport" -- a different building. Publishing against it would
    # have put another hotel's pet policy on this row's page.
    # The guarantee is kept on the URL it was written about rather than deleted,
    # and the row's own state is asserted directly.
    assert by_key["baymont by wyndham plainfield indianapolis airport area"]["official_url"] == "", (
        "the mis-bound Plainfield Baymont route must stay removed until a correct one is found")
    assert brand_scoped_property_identity(
        "https://www.wyndhamhotels.com/baymont/plainfield-indiana/"
        "baymont-inn-and-suites-plainfield-indianapolis-arpt-area/overview") == ("WYNDHAM", "")
    assert brand_scoped_property_identity(
        by_key["best western plus indianapolis northwest"]["official_url"]) == ("BEST_WESTERN", "15116")

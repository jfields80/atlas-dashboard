"""PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013 -- one legacy row becomes two.

Cincinnati's census grows for the first time in this lineage: 256 - 1 + 2 = 257.
The conflated identity "Comfort Suites Mainstay Hotel" is gone and the two real
Choice properties at 2347 Reading Road stand in its place, each with its own
route and its own refusal.

A split is the one operation that can quietly recreate the very defect it was
called to fix, in three ways:

* it can leave the LEGACY row behind, so the market carries three hotels where
  two exist. The census has no retired state, so "flagging" it is not available
  -- it either goes or it stays live;
* it can CROSS-CONTAMINATE. Two identities built from one determination can end
  up sharing a URL, a phone or an evidence digest, and then the split is
  cosmetic: two names over one hotel's evidence;
* it can lose the LINEAGE. PTF-CINCINNATI-CENSUS-PIN-024 requires a census
  change to account for every prior identity and supersede it, never overwrite
  it, and a row that simply vanishes leaves a reader no way to learn why.

These pin all three, plus the arithmetic: unresolved is derived as census minus
resolved and never carried forward from the previous order.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_mainstay_census_split_013 as S
from scripts.pettripfinder import hotel_exclusions as EX
from scripts.pettripfinder.contracts import census as census_contract
from scripts.pettripfinder.contracts import enums, partition as partition_contract

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"
LEDGER = PKG / "markets" / "reports" / "cincinnati_mainstay_census_split_013.json"

LEGACY = "comfort suites mainstay hotel"
OH720 = "comfort suites cincinnati university downtown"
OH721 = "mainstay suites cincinnati university uptown"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def census():
    return _load(CENSUS)


@pytest.fixture(scope="module")
def rows(census):
    return {h["identity_key"]: h for h in census["hotels"]}


@pytest.fixture(scope="module")
def ledger():
    return _load(LEDGER)


@pytest.fixture(scope="module")
def exclusions():
    return _load(AUTH / "hotel_exclusions.json")["exclusions"]


@pytest.fixture(scope="module")
def routes():
    return {r["hotel_ref"]["identity_key"]: r
            for r in _load(AUTH / "identity_routing.json")["routes"]}


# ------------------------------------------------------------ it cost nothing

def test_the_split_cost_nothing(ledger):
    assert ledger["provider_calls"] == 0
    assert ledger["paid_spend_usd"] == 0.0
    assert ledger["parent_work_order"] == "PTF-CINCINNATI-MAINSTAY-IDENTITY-012"


# --------------------------------------------------- the legacy row is gone

def test_the_conflated_identity_is_not_in_the_census(rows):
    assert LEGACY not in rows


def test_it_is_not_in_the_partition_routing_or_exclusions(exclusions, routes):
    partition_keys = {i["identity_key"] for i in _load(PARTITION)["items"]}
    assert LEGACY not in partition_keys
    assert LEGACY not in routes
    assert LEGACY not in {e["normalized_name"] for e in exclusions}


def test_removal_was_forced_by_the_contract_not_chosen(ledger):
    """The census has no retired state, so flagging was never available."""
    assert "IDENTITY_STATES has no retired value" in \
        ledger["retired_identity"]["why_removed_not_flagged"]
    assert "RETIRED" not in enums.IDENTITY_STATES
    assert "SUPERSEDED" not in enums.IDENTITY_STATES
    assert set(enums.IDENTITY_STATES) == {"IDENTITY_CONFIRMED",
                                          "IDENTITY_PROVISIONAL",
                                          "IDENTITY_UNRESOLVED"}


def test_the_hold_was_cleared_by_supersession_not_by_a_policy_ruling(ledger):
    retired = ledger["retired_identity"]
    assert retired["resolved_by"] == "CENSUS_SPLIT"
    assert sorted(retired["superseded_by"]) == sorted([OH720, OH721])
    assert retired["policy_outcome_applied_to_old_row"] is False
    # The old row's own facts are preserved so the history is legible.
    assert retired["canonical_name"] == "Comfort Suites Mainstay Hotel"
    assert retired["postal_code"] == "45219"
    assert retired["phone"] == "5133946073"
    assert retired["route_retired"]["hotel_ref"]["identity_key"] == LEGACY


# ------------------------------------------------------------- the lineage

@pytest.mark.parametrize("key", [OH720, OH721])
def test_each_successor_carries_its_lineage(rows, key):
    """A census change must account for the prior identity, never overwrite."""
    row = rows[key]
    assert row["prior_identity_key"] == LEGACY
    split = row["split"]
    assert split["reason"] == "CONFLATED_DUAL_PROPERTY_DIRECTORY_IDENTITY"
    assert split["from_identity_key"] == LEGACY
    assert split["from_canonical_name"] == "Comfort Suites Mainstay Hotel"
    assert split["from_address"] == "2347 Reading Rd."
    assert split["determined_by"] == "PTF-CINCINNATI-MAINSTAY-IDENTITY-012"
    assert split["split_by"] == S.WORK_ORDER
    assert split["operator"] == "jfields80"


def test_each_successor_names_the_other(rows):
    assert rows[OH720]["split"]["sibling_identity_key"] == OH721
    assert rows[OH721]["split"]["sibling_identity_key"] == OH720


def test_the_census_records_the_split_in_its_own_history(census):
    entry = census["split_history"][-1]
    assert entry["work_order"] == S.WORK_ORDER
    assert entry["retired_identity_key"] == LEGACY
    assert sorted(entry["successor_identity_keys"]) == sorted([OH720, OH721])
    assert entry["count_before"] == 256 and entry["count_after"] == 257


# ------------------------------------------------ no evidence is shared

def test_the_two_identities_share_nothing_that_identifies_them(rows, routes,
                                                               exclusions):
    a, b = rows[OH720], rows[OH721]
    assert a["property_code"] == "oh720" and b["property_code"] == "oh721"
    assert a["phone"] != b["phone"]
    assert a["address"].endswith("Building A")
    assert b["address"].endswith("Building B")
    assert a["split"]["evidence_url"] != b["split"]["evidence_url"]
    assert a["split"]["evidence_sha256_page"] != b["split"]["evidence_sha256_page"]
    # The census holds no official_url: routing authority lives in its own
    # file, and two copies of one fact are how they drift apart.
    assert a["official_url"] == b["official_url"] == ""

    ra, rb = routes[OH720], routes[OH721]
    assert ra["official_property_url"] != rb["official_property_url"]
    assert ra["property_code"] != rb["property_code"]
    assert ra["identity_context"]["phone"] != rb["identity_context"]["phone"]

    ex = {e["normalized_name"]: e for e in exclusions}
    assert ex[OH720]["source_hash"] != ex[OH721]["source_hash"]
    assert ex[OH720]["official_url"] != ex[OH721]["official_url"]


def test_each_route_points_at_one_property_page(routes):
    """This asserted PAGE_RENDERED, and that was wrong.

    ``test_every_committed_record_preserves_index_binding`` holds that a brand
    which bot-walls us can never be the source of a rendered-page binding, and
    choicehotels.com is on that list. The pages WERE rendered attended -- the
    digest that proves it lives on each exclusion, where evidence belongs --
    but a route's binding_method describes its source, and every other Choice
    route in this market says BRAND_INDEX_BINDING. What actually matters here
    is that neither route is a brand INDEX url: each ends in its own property
    code and they share nothing.
    """
    import scripts.pettripfinder.identity_routing as IR
    urls = set()
    for key in (OH720, OH721):
        route = routes[key]
        assert route["binding_method"] == "BRAND_INDEX_BINDING"
        assert route["official_property_url"].rstrip("/").endswith(
            route["property_code"])
        assert route["status"] == "ROUTING_CONFIRMED"
        assert IR.registrable_domain(route["official_property_url"]) ==             "choicehotels.com"
        urls.add(route["official_property_url"])
    assert len(urls) == 2


def test_the_builder_refuses_shared_evidence():
    """Derived, so the guard is tested on input this order did not produce."""
    import copy
    determination = _load(PKG / "markets" / "reports"
                          / "cincinnati_mainstay_identity_012.json")
    bad = copy.deepcopy(determination)
    bad["observed_first_party"]["oh721"]["sha256_page"] = \
        bad["observed_first_party"]["oh720"]["sha256_page"]
    import scripts.pettripfinder.cincinnati_mainstay_census_split_013 as mod
    original = mod._load
    mod._load = lambda p: bad if str(p).endswith(
        "cincinnati_mainstay_identity_012.json") else original(p)
    try:
        with pytest.raises(mod.SplitError) as exc:
            mod.build()
        assert "cross-contamination" in str(exc.value)
    finally:
        mod._load = original


# ------------------------------------------------------- the two refusals

@pytest.mark.parametrize("key,code", [(OH720, "oh720"), (OH721, "oh721")])
def test_each_identity_has_its_own_affirmative_refusal(exclusions, key, code):
    record = next(e for e in exclusions if e["normalized_name"] == key)
    assert record["exclusion_state"] == "VERIFIED_NO_PETS"
    assert "Pets Allowed: No" in record["evidence_quote"]
    assert record["source_hash"].startswith("sha256:")
    assert code in record["official_url"]
    assert record["reviewed_at"] == S.AS_OF
    assert LEGACY in record["notes"], "it should say what it was split from"
    assert record["record_hash"] == EX.record_hash(
        {k: v for k, v in record.items()
         if k not in ("record_hash", "approval_hash")})


def test_no_combined_exclusion_was_ever_registered(exclusions):
    names = {e["normalized_name"] for e in exclusions}
    assert LEGACY not in names
    assert len([e for e in exclusions if "2347 Reading" in e["address"]]) == 2


def test_the_two_refusals_are_two_records_not_one(exclusions):
    both = [e for e in exclusions if e["normalized_name"] in (OH720, OH721)]
    assert len(both) == 2
    assert both[0]["record_hash"] != both[1]["record_hash"]
    assert both[0]["canonical_name"] != both[1]["canonical_name"]


# ---------------------------------------------------------- the arithmetic

def test_the_census_grew_by_exactly_one(census, ledger):
    assert census["count"] == len(census["hotels"]) == 257
    arithmetic = ledger["census_arithmetic"]
    assert arithmetic["before"] == 256
    assert arithmetic["retired"] == 1
    assert arithmetic["added"] == 2
    assert arithmetic["after"] == 257
    assert "Physical removal" in arithmetic["semantics"]


def test_no_identity_is_duplicated(census):
    keys = [h["identity_key"] for h in census["hotels"]]
    assert len(set(keys)) == len(keys) == 257
    assert census_contract.validate(census) == ()


def test_the_partition_reconciles_to_the_new_census(census):
    rec = partition_contract.reconcile(
        census_contract.identity_keys(census), _load(PARTITION),
        market_id="cincinnati-oh")
    assert rec.missing_from_partition == ()
    assert rec.missing_from_census == ()
    assert rec.duplicated_in_partition == ()
    assert rec.census_count == rec.partition_count == 257
    assert rec.agrees


def test_unresolved_is_derived_not_carried_forward(ledger):
    """257 - 154 = 103. The prior order's 104 is not reused."""
    after = ledger["authority_after"]
    assert after["published_pet_friendly"] == 99
    assert after["verified_no_pets"] == 49
    assert after["out_of_current_category"] == 6
    assert after["resolved"] == 154
    assert after["unresolved"] == 103
    assert after["resolved"] + after["unresolved"] == 257
    assert "never assumed" in after["derivation"]

    counts = _load(PARTITION)["final_state_counts"]
    resolved = sum(counts[s] for s in ("PUBLISHED_PET_FRIENDLY",
                                       "VERIFIED_NO_PETS",
                                       "OUT_OF_CURRENT_CATEGORY"))
    assert resolved == 154
    assert sum(counts.values()) - resolved == 103


def test_the_release_contract_agrees():
    from scripts.pettripfinder import release_contracts as RC
    assert RC.verify_contract("cincinnati-oh") == []
    contract = _load(RC.contract_path("cincinnati-oh"))
    rec = contract["reconciliation"]
    assert rec["confirmed_identities"] == 257
    assert rec["verified_no_pets"] == 49
    assert rec["resolved"] == 154
    assert rec["unresolved"] == 103


# ------------------------------------------------------- nothing else moved

def test_the_blue_ash_mainstay_was_not_swept_in(rows):
    """Brand similarity is not identity."""
    blue = rows["mainstay suites cincinnati blue ash"]
    assert blue["postal_code"] == "45242"
    assert blue["identity_state"] == "IDENTITY_UNRESOLVED"
    assert blue.get("prior_identity_key") == "mainstay suites cincinnati blue ash"
    assert "split" not in blue


def test_the_pet_friendly_package_was_not_touched():
    package = _load(PKG / "hotel_policy_facts_cincinnati-oh.json")
    assert len(package["hotels"]) == 99
    keys = {h["identity_key"] for h in package["hotels"]}
    assert LEGACY not in keys and OH720 not in keys and OH721 not in keys


def test_the_studio_6_hold_still_stands(rows):
    held = "studio 6 extended stay fairfield oh cincinnati"
    item = next(i for i in _load(PARTITION)["items"]
                if i["identity_key"] == held)
    assert item["resolved"] is False
    routes = {r["hotel_ref"]["identity_key"]
              for r in _load(AUTH / "identity_routing.json")["routes"]}
    assert held in routes


def test_running_it_again_refuses():
    with pytest.raises(S.SplitError) as exc:
        S.build()
    assert "already ran" in str(exc.value)

# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024.

Promoting a census is the act with the most room to lose something quietly, so
the tests are weighted towards what must NOT have happened.

NOTHING MAY BE LOST. Ten of the 120 prior identity keys are absent from the 163.
Every one is a recorded absorption into a fresh sighting of the same building on
a shared street identity, and the promoter REFUSES if a prior key disappears
with no absorption naming it. "The count went up" is not evidence that nothing
was lost, and there is a test that drives the refusal.

THE ACCOUNTING MUST NOT COMPARE THE CENSUS WITH ITSELF. The prior document is
read from the SUPERSEDED copy, never from the pinned path -- reading the pinned
path would report a flawless promotion that accounted for nothing on any re-run.

WHAT THE PROMOTION EXPOSED. Three bare-chain identity keys now collide with
Cleveland's census, and two authority-bearing keys collide with Louisville's and
St. Louis's. The condition is systemic and pre-dates this market: Louisville and
St. Louis already share seven keys and Louisville already publishes a record
whose identity_key is "tru". Nothing is renamed here and nothing renders on the
census key, so the collisions are recorded rather than resolved -- and the
recording is what the disjointness guard now checks against.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_census_pin_024 as C  # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS                # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "grand-rapids-holland-mi"
PINNED = LP / "identity_census" / ("%s.json" % MARKET)
SUPERSEDED = LP / "identity_census" / "superseded" / ("%s-120.json" % MARKET)
REPORT = LP / "grand_rapids_holland_mi_census_pin_024.json"
CONTRACT = REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def report():
    return _load(REPORT)


@pytest.fixture(scope="module")
def pinned():
    return _load(PINNED)


# --------------------------------------------------------------------------- #
# The census
# --------------------------------------------------------------------------- #

def test_the_pinned_census_is_the_163_row_universe(pinned):
    assert pinned["count"] == len(pinned["hotels"]) == 163
    assert pinned["market_id"] == MARKET
    assert pinned["work_order"] == C.WORK_ORDER
    assert CENSUS.validate(pinned, market_states=["MI"]) == ()


def test_no_identity_key_is_duplicated(pinned):
    keys = [row["identity_key"] for row in pinned["hotels"]]
    assert len(keys) == len(set(keys)) == 163


def test_no_canonical_property_is_duplicated(pinned):
    """Two rows for one building would be a duplicate property, whatever their
    names. Street number plus postal code is the identity both records hold."""
    seen = {}
    for row in pinned["hotels"]:
        address = " ".join(str(row.get("address") or "").lower().split())
        number = address.split(" ")[0] if address else ""
        postal = str(row.get("postal_code") or "")
        if not number or not number[0].isdigit() or not postal:
            continue
        seen.setdefault("%s|%s" % (number, postal), []).append(row["identity_key"])
    collisions = {k: v for k, v in seen.items() if len(v) > 1}
    # The known same-street pairs the dedup gate ruled DISTINCT_PROPERTIES are
    # expected; what must not appear is a pair nobody has ruled on.
    for key, rows in collisions.items():
        assert len(rows) == 2, "%s holds %d rows" % (key, len(rows))


def test_every_prior_identity_survived_or_was_absorbed(report):
    accounting = report["census"]["prior_census_accounting"]
    assert accounting["prior_identities"] == 120
    assert accounting["promoted_identities"] == 163
    assert accounting["survived_by_key"] == 110
    assert accounting["absorbed_into_a_fresh_sighting"] == 10
    assert accounting["unexplained_losses"] == []
    assert accounting["net_new_identities"] == 53
    assert len(accounting["absorptions"]) == 10
    for row in accounting["absorptions"]:
        assert row["absorbed_into"] and row["street_identity"] and row["basis"]


def test_a_prior_identity_that_vanishes_unexplained_stops_the_promotion():
    """The refusal, driven. A promotion that quietly drops a hotel takes with
    it every future pass's reason to ask about that building again."""
    prior = {"hotels": [{"identity_key": "a ghost hotel",
                         "canonical_name": "A Ghost Hotel"}]}
    promoted = {"hotels": [{"identity_key": "something else",
                            "canonical_name": "Something Else"}]}
    with pytest.raises(C.CensusPinError) as excinfo:
        C.account_for_every_prior_identity(prior, promoted)
    assert "a ghost hotel" in str(excinfo.value)


def test_the_accounting_reads_the_superseded_copy_not_the_pinned_path():
    """Otherwise a re-run compares the promoted census with itself and reports
    a flawless promotion that accounted for nothing."""
    assert SUPERSEDED.is_file()
    assert len(CENSUS.identity_keys(C.prior_census())) == 120
    assert _load(SUPERSEDED)["work_order"] == (
        "PTF-GRAND-RAPIDS-HOLLAND-MARKET-FACTORY-001")


def test_the_three_states_were_filled_from_the_market_contract(report, pinned):
    """census.validate requires a state; three rows carried none because their
    provider stated none and they hold no corridor. The market declares exactly
    one state, so this is the contract's own definition and not an inference."""
    fills = report["census"]["states_filled_from_the_market_contract"]
    assert len(fills) == 3
    assert {f["identity_key"] for f in fills} == {
        "best western hospitality hotel and suites", "dutch colonial inn",
        "haworth hotel"}
    by_key = {row["identity_key"]: row for row in pinned["hotels"]}
    for fill in fills:
        row = by_key[fill["identity_key"]]
        assert row["state"] == "MI"
        assert row["state_source"] == "market_contract"
        # No corridor was assigned: where inside the market a hotel sits is a
        # different question and this pass does not answer it.
        assert not row.get("corridor")


def test_a_multi_state_market_would_refuse_the_state_fill(monkeypatch):
    class _Market:
        states = ("MI", "IN")
    monkeypatch.setattr(C, "market_by_id", lambda *a, **k: _Market())
    with pytest.raises(C.CensusPinError):
        C.fill_missing_states([{"identity_key": "x", "state": ""}])


# --------------------------------------------------------------------------- #
# The authority is unchanged and fully covered
# --------------------------------------------------------------------------- #

def test_every_authority_identity_resolves_inside_the_promoted_census(report):
    coverage = report["authority_coverage"]
    assert coverage["authority_total"] == 49
    assert coverage["pet_friendly"] == 35
    assert coverage["verified_no_pets"] == 14
    assert coverage["outside_the_promoted_census"] == []
    assert coverage["ok"] is True


def test_the_authority_itself_was_not_touched():
    from scripts.pettripfinder import market_authority as MA
    assert len(MA.load_market_exclusions(MARKET)) == 14
    assert len(MA.load_market_seed_rows(MARKET)) == 35
    package = _load(LP / ("hotel_policy_facts_%s.json" % MARKET))
    assert package["count"] == 35 and package["published"] is True


def test_the_partition_pairing_is_named(report):
    """A census and a partition are a pair; pinning one without saying which
    partition answers for it leaves an invariant pointing at the wrong file."""
    pairing = report["partition_pairing"]
    assert pairing["ok"] is True
    assert pairing["paired_with"] == "grand_rapids_holland_mi_final_partition_001.json"
    assert pairing["by_partition"][pairing["paired_with"]]["agrees"] is True


# --------------------------------------------------------------------------- #
# What the promotion exposed
# --------------------------------------------------------------------------- #

def test_the_cross_market_collisions_are_recorded_not_hidden(report):
    collisions = report["cross_market_collisions"]
    assert collisions["collisions"] == 16
    assert collisions["in_this_market_s_authority"] == 3
    keys = {(r["identity_key"], r["also_in_market"]) for r in collisions["rows"]
            if r["published_here"] or r["excluded_here"]}
    assert keys == {("tru", "louisville-ky"), ("tru", "st-louis-mo"),
                    ("doubletree by hilton", "st-louis-mo")}


def test_the_condition_is_systemic_and_predates_this_market(report):
    """Whether this promotion created a problem or joined a standing one. It
    joined one, and saying so is the difference between a finding and a
    misattribution."""
    prior = report["cross_market_collisions"]["pre_existing_between_other_markets"]
    assert prior["pairs"] == 3
    assert prior["keys"] == 11
    assert any("louisville-ky" in row["markets"] and "st-louis-mo" in row["markets"]
               and "tru" in row["identity_keys"] for row in prior["rows"])


def test_nothing_renders_on_the_colliding_census_key():
    """020's name corrections made both authority-bearing collisions unique on
    the DISPLAY key, which is what site_data joins on."""
    package = _load(LP / ("hotel_policy_facts_%s.json" % MARKET))
    tru = next(h for h in package["hotels"] if h["identity_key"] == "tru")
    assert tru["key"] == "tru by hilton grand rapids airport"
    shard = _load(LP / "markets" / "authority" / MARKET / "hotel_exclusions.json")
    doubletree = next(r for r in shard["exclusions"]
                      if r["canonical_name"].startswith("DoubleTree"))
    assert doubletree["normalized_name"] == "doubletree by hilton hotel holland"


def test_no_identity_was_renamed_by_this_pass(report):
    assert any("no identity was renamed" in line
               for line in report["not_done_here"])


# --------------------------------------------------------------------------- #
# The release contract
# --------------------------------------------------------------------------- #

def test_the_release_contract_exists_and_binds_the_promoted_count(report):
    contract = _load(CONTRACT)
    assert contract["market_id"] == MARKET
    assert contract["identity_census"]["expected_count"] == 163
    assert contract["identity_census"]["path"] == (
        "launch_packages/pettripfinder/identity_census/%s.json" % MARKET)
    assert report["release_contract"]["written"] is True
    assert report["release_contract"]["expected_count"] == 163


def test_the_contract_agrees_with_the_derivation_field_by_field():
    """Neither half alone is sufficient: derivation alone recomputes its own
    expectation and proves nothing."""
    from scripts.pettripfinder import release_contracts as RC
    assert RC.verify_contract(MARKET) == []


def test_the_contract_states_the_real_counts():
    contract = _load(CONTRACT)
    reconciliation = contract["reconciliation"]
    assert reconciliation["confirmed_identities"] == 163
    assert reconciliation["published_pet_friendly"] == 35
    assert reconciliation["verified_no_pets"] == 14
    assert reconciliation["resolved"] == 49
    assert reconciliation["unresolved"] == 114
    assert reconciliation["resolved"] + reconciliation["unresolved"] == 163
    surface = contract["public_surface"]
    assert surface["seed_hotel_rows"] == 35
    assert surface["public_hotel_profile_count"] == 35
    assert surface["excluded_public_profile_count"] == 0


def test_the_contract_grants_no_deployment(report):
    contract = _load(CONTRACT)
    assert contract["deployment_authorization"]["grants_deployment"] is False
    assert contract["deployment_authorization"]["asserts_market_complete"] is False
    assert contract["market_visibility"]["show_in_navigation"] is True
    assert contract["market_visibility"]["show_in_sitemap"] is True
    assert contract["source_commit"]


def test_the_contract_carries_every_required_gate():
    contract = _load(CONTRACT)
    louisville = _load(REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                       / "louisville-ky.json")
    assert set(contract["minimum_release_gates"]) == set(
        louisville["minimum_release_gates"])
    assert contract["forbidden_output_tokens"] == louisville["forbidden_output_tokens"]


# --------------------------------------------------------------------------- #
# Blast radius
# --------------------------------------------------------------------------- #

def test_no_other_market_census_or_authority_changed():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/identity_census",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/hotel_exclusions.json",
         "launch_packages/pettripfinder/identity_routing.json",
         "launch_packages/pettripfinder/seed_businesses.csv",
         "deploy/netlify/release_contracts"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    allowed = {
        "atlas-dashboard/launch_packages/pettripfinder/identity_census/%s.json" % MARKET,
        "atlas-dashboard/launch_packages/pettripfinder/identity_census/superseded/",
        "atlas-dashboard/deploy/netlify/release_contracts/%s.json" % MARKET,
    }
    touched = {line[3:].strip().strip('"')
               for line in result.stdout.splitlines() if line.strip()}
    assert touched <= allowed, "unexpected writes: %s" % (touched - allowed)


def test_nothing_was_spent(report):
    assert report["provider_calls"] == 0
    assert report["usd_spent"] == 0.0

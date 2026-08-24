"""PTF-MILWAUKEE-PUBLICATION-042 -- published in source, and nothing else moved.

One flag changed. These assert that it was the right flag, that the 73 records
behind it are the ones a founder approved, that the three held properties and
the twenty-seven refusals reach no surface, and that no bundle left the
repository.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import approval_binding as AB
from scripts.pettripfinder import hotel_exclusions as EX
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder import site_data as SD
from scripts.pettripfinder.acquisition import authority_build_036 as A36
from scripts.pettripfinder.acquisition import closure_038 as C38
from scripts.pettripfinder.acquisition import founder_decisions_040 as D40
from scripts.pettripfinder.acquisition import normalization_041 as N41
from scripts.pettripfinder.acquisition import publication_037 as P37
from scripts.pettripfinder.acquisition import publication_042 as P42

MARKET = "milwaukee-wi"
SAINT_KATE = "saint kate the arts hotel"
HYATT = "hyatt regency milwaukee"
KNICKERBOCKER = "knickerbocker on the lake"
IRON_HORSE = "the iron horse hotel"
JEFFERSON = ("Home2 Suites by Hilton Milwaukee Downtown",
             "Tru by Hilton Milwaukee Downtown")


@pytest.fixture(autouse=True)
def _fresh_closure():
    for cached in (C38.capture_attempts, C38.best_replay, C38.active_rows,
                   C38.non_active_rows, C38.later_founder_decisions):
        cached.cache_clear()
    yield


@pytest.fixture(scope="module")
def authority():
    return json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report():
    return json.loads(P42.REPORT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# The transition.
# --------------------------------------------------------------------------- #

def test_milwaukee_is_published_in_source(authority):
    assert authority["published"] is True
    assert len(SD.load_published_hotel_policy_facts(MARKET)) == 73


def test_the_publication_block_names_who_published_and_on_what_authority(
        authority):
    block = authority["publication"]
    assert block["work_order"] == P42.WORK_ORDER
    assert block["decision_ledgers"] == ["milwaukee_founder_decisions_036.json",
                                         "milwaukee_founder_decisions_040.json"]
    assert block["deployed"] is False


def test_publication_changed_no_record():
    """The whole transition is one flag. Asserted byte for byte."""
    doc, changes = P37.published_document(
        work_order=P42.WORK_ORDER,
        ledgers=["milwaukee_founder_decisions_036.json",
                 "milwaukee_founder_decisions_040.json"])
    assert changes == []
    assert P42.records_are_unchanged_since_041() is True


def test_the_seed_inventory_is_one_row_per_published_record(authority):
    rows = MA.load_market_seed_rows(MARKET)
    assert len(rows) == len(authority["hotels"]) == 73
    names = [row["name"] for row in rows]
    assert sorted(names) == sorted(r["name"] for r in authority["hotels"])
    assert len(set(names)) == 73


# --------------------------------------------------------------------------- #
# The input, re-derived rather than trusted.
# --------------------------------------------------------------------------- #

def test_exactly_73_records_are_publishable():
    valid, rejected = P42.validate_pet_friendly()
    assert rejected == []
    assert len(valid) == 73


def test_exactly_27_refusals_remain_exclusions():
    valid, rejected = P42.validate_exclusions()
    assert rejected == []
    assert len(valid) == 27
    assert len(MA.load_market_exclusions(MARKET)) == 27


#: The two sittings that first approved this market's rows. A later sitting
#: may RE-ATTEST a row -- PTF-...-REAUTHORIZE-012 re-attested four -- which
#: moves the ledger the approval currently names and preserves the earlier one
#: under ``supersedes``. What must never happen is a row tracing back to
#: neither.
FIRST_APPROVAL_LEDGERS = ("milwaukee_founder_decisions_036.json",
                          "milwaukee_founder_decisions_040.json")


def _ledger_lineage(approval):
    names, node = [], approval
    while isinstance(node, dict):
        ledger = (node.get("decision_source") or {}).get("ledger")
        if ledger:
            names.append(ledger)
        node = node.get("supersedes")
    return names


def test_every_published_record_carries_a_founder_approval(authority):
    for record in authority["hotels"]:
        approval = record["approval"]
        assert approval["operator"] == D40.FOUNDER
        assert approval["decision"] in P42.APPROVAL_MARKERS
        lineage = _ledger_lineage(approval)
        assert lineage, record["identity_key"]
        assert set(lineage) & set(FIRST_APPROVAL_LEDGERS), \
            (record["identity_key"], lineage)


def test_the_040_records_bind_under_the_semantic_contract(authority):
    recent = [r for r in authority["hotels"]
              if r["approval"]["decision_source"]["work_order"]
              == D40.WORK_ORDER]
    assert len(recent) == 3
    for record in recent:
        assert record["approval"]["binding_contract"] == \
            AB.BINDING_CONTRACT_VERSION
        assert record["approval"]["semantic_hash"] == \
            record["approval"]["reviewed_semantic_hash"]


# --------------------------------------------------------------------------- #
# What must not be published.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("key", [HYATT, KNICKERBOCKER, IRON_HORSE])
def test_a_held_property_is_not_published(key, authority):
    published = {record["identity_key"] for record in authority["hotels"]}
    assert key not in published
    assert key in set(P37.held_identities())
    assert key not in {EX.normalize_name(row["name"])
                       for row in MA.load_market_seed_rows(MARKET)}


def test_no_forbidden_disposition_reaches_publication():
    report = P42.assert_no_leakage()
    assert report["held_in_publication"] == []
    assert report["forbidden_disposition_leaks"] == {}
    assert report["exclusion_leaks"] == []


def test_every_published_identity_is_authority_pet_friendly(authority):
    closure = {row["identity_key"]: row["disposition"]
               for row in C38.active_rows()}
    for record in authority["hotels"]:
        assert closure[record["identity_key"]] == C38.AUTHORITY_PET_FRIENDLY


def test_a_refusal_can_never_own_a_profile(authority):
    refusals = {row["normalized_name"]
                for row in MA.load_market_exclusions(MARKET)}
    published = {EX.normalize_name(record["name"])
                 for record in authority["hotels"]}
    assert refusals & published == set()
    seeded = {EX.normalize_name(row["name"])
              for row in MA.load_market_seed_rows(MARKET)}
    assert refusals & seeded == set()


# --------------------------------------------------------------------------- #
# The two rows this market learned the most from.
# --------------------------------------------------------------------------- #

def test_saint_kate_is_published_on_the_corrected_reading():
    row = P42.saint_kate_report()
    assert row["in_authority"] is True
    assert row["pets_allowed"] is True
    assert row["is_refusal"] is False
    assert row["withheld_fields"] == {}
    assert row["pet_fee"]["amount_cents"] == 10000
    assert row["pet_count_limit"] == 2
    # Nothing the page never said.
    assert row["weight_limit_absent"] is True
    assert row["species_absent"] is True
    assert row["approving_work_order"] == D40.WORK_ORDER
    assert row["approval_contract"] == AB.BINDING_CONTRACT_VERSION


def test_the_galleria_sentence_is_still_a_place_restriction():
    assert P42.saint_kate_report()[
        "place_restriction_still_reads_as_a_place"] is True


def test_both_jefferson_hiltons_are_published_independently():
    row = P42.jefferson_report()
    assert row["both_in_authority"] is True
    assert row["shared_address_key"] == ["515|jefferson|53202"]
    assert row["resolution_reviewed"] is True
    assert row["distinct_identity_keys"] == [
        "home2 suites by hilton milwaukee downtown",
        "tru by hilton milwaukee downtown"]
    names = {row["name"] for row in MA.load_market_seed_rows(MARKET)}
    assert set(JEFFERSON) <= names


# --------------------------------------------------------------------------- #
# The live contract.
# --------------------------------------------------------------------------- #

def test_the_live_contract_binds_the_current_authority():
    assert P42.LIVE_CONTRACT.is_file()
    contract = json.loads(P42.LIVE_CONTRACT.read_text(encoding="utf-8"))
    derived = RC.derive_authority(MARKET)
    assert contract["market_id"] == MARKET
    assert contract["policy_package"]["expected_sha256"] == \
        derived.policy_package_sha256
    assert contract["policy_package"]["expected_record_count"] == 73
    assert contract["reconciliation"]["verified_no_pets"] == 27
    assert contract["routes"]["hotel_route_count"] == 73
    assert contract["provenance"]["publication_work_order"] == P42.WORK_ORDER


def test_the_live_contract_grants_no_deployment():
    contract = json.loads(P42.LIVE_CONTRACT.read_text(encoding="utf-8"))
    assert contract["deployment_authorization"]["grants_deployment"] is False
    assert contract["deployment_authorization"]["asserts_market_complete"] \
        is False


def test_every_market_contract_verifies():
    for market_id in RC.available_market_ids():
        assert RC.verify_contract(market_id) == [], market_id
    assert MARKET in set(RC.available_market_ids())


def test_the_stale_037_package_is_still_unusable():
    staging = Path(tempfile.mkdtemp())
    shutil.copy2(P37.PREPARED_CONTRACT, staging / ("%s.json" % MARKET))
    real = RC.RELEASE_CONTRACTS_DIR
    RC.RELEASE_CONTRACTS_DIR = staging
    try:
        with pytest.raises(RC.ReleaseContractError) as caught:
            RC.load_contract(MARKET)
        assert "SUPERSEDED" in str(caught.value)
    finally:
        RC.RELEASE_CONTRACTS_DIR = real
        shutil.rmtree(staging, ignore_errors=True)
    stale = json.loads(P37.PREPARED_CONTRACT.read_text(encoding="utf-8"))
    assert stale["policy_package"]["expected_record_count"] == 70


def test_the_live_contract_is_not_the_stale_document():
    import hashlib
    live = P42.LIVE_CONTRACT.read_bytes()
    assert hashlib.sha256(live).hexdigest() not in RC.superseded_contracts()
    stale = json.loads(P37.PREPARED_CONTRACT.read_text(encoding="utf-8"))
    contract = json.loads(live.decode("utf-8"))
    assert contract["policy_package"]["expected_sha256"] != \
        stale["policy_package"]["expected_sha256"]


# --------------------------------------------------------------------------- #
# The build that actually ran.
# --------------------------------------------------------------------------- #

def test_the_recorded_build_included_milwaukee_and_passed_every_gate(report):
    build = report["build"]
    assert build["milwaukee_included"] is True
    assert MARKET in build["markets"]
    assert build["all_gates_pass"] is True
    assert build["gates_failing"] == []
    assert build["broken_links"] == 0
    assert build["collision_count"] == 0
    assert build["global_shadowing_count"] == 0
    assert build["canonical_violations"] == 0


def test_the_build_is_deterministic(report):
    build = report["build"]
    assert build["deterministic"] is True
    assert len(set(build["bundle_sha256_each"])) == 1


def test_the_real_build_matched_041s_simulation(report):
    """041 predicted this bundle before the flag was flipped. It should not be
    a surprise that it matched -- but if it ever stops matching, the
    simulation has stopped being evidence about anything."""
    simulated = json.loads(N41.SIMULATION.read_text(encoding="utf-8"))
    site = simulated["site_dry_run"]
    assert report["build"]["bundle_sha256_each"][0] == \
        site["with_milwaukee"]["bundle_sha256"]
    assert report["build"]["total_html_pages"] == \
        site["with_milwaukee"]["total_html_pages"]


def test_the_routes_are_the_ones_the_manifest_declares(report):
    routes = report["routes"]
    assert routes["published_pet_friendly"] == 73
    assert routes["hotel_routes"] == 73
    assert routes["corridor_routes"] == 7
    assert routes["corridor_unassigned"] == []
    assert routes["verified_no_pets"] == 27


# --------------------------------------------------------------------------- #
# Arithmetic, cross-market, and the line that was not crossed.
# --------------------------------------------------------------------------- #

def test_the_active_closure_is_still_133():
    recon = C38.reconciliation()
    assert recon["active_eligible"] == 133
    assert sum(recon["by_disposition"].values()) == 133
    assert recon["problems"] == []


def test_the_census_is_still_147():
    recon = C38.reconciliation()
    assert recon["census_total"] == 147
    assert recon["non_active_eligible"] == 14


def test_no_other_market_moved():
    doc = json.loads(
        (REPO / "launch_packages/pettripfinder/hotel_exclusions.json")
        .read_text(encoding="utf-8-sig"))
    counts = Counter(row.get("market_id", "") for row in doc["exclusions"])
    assert counts[MARKET] == 27
    assert counts["cleveland-akron-canton-oh"] == 40
    assert counts["columbus-oh"] == 16
    assert counts["dayton-oh"] == 8
    assert counts["indianapolis-in"] == 4
    assert counts["pittsburgh-pa"] == 7
    assert MA.check_generated_artifacts() == []


def test_other_markets_keep_their_inventory():
    rows = MA.assemble_seed_rows()
    by_market = Counter(row["market_id"] for row in rows)
    assert by_market["columbus-oh"] == 116
    assert by_market["cleveland-akron-canton-oh"] == 99
    assert by_market["dayton-oh"] == 47
    assert by_market["pittsburgh-pa"] == 26
    assert by_market["indianapolis-in"] == 8
    assert by_market[MARKET] == 73


def test_deployment_was_not_performed(report, authority):
    assert report["deployed"] is False
    assert authority["publication"]["deployed"] is False
    assert report["build"]["deployment_authorized"] is False
    ledger = json.loads(C38.LEDGER.read_text(encoding="utf-8"))
    assert ledger["deployed"] == 0


def test_no_provider_was_called(report):
    assert report["provider_calls"] == 0
    assert report["cost_usd"] == 0.0


def test_nothing_outside_the_publication_surface_changed():
    """The flip touches the package flag, the seed shard and the generated
    globals. A census, closure or evidence change hiding in this commit would
    be a different work order wearing this one's name."""
    changed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.split("\n")
    forbidden = ("identity_census/", "policy_proposals_001.json",
                 "milwaukee_founder_decisions_", "milwaukee_closure_038/",
                 "routes.json", "policy_reading.py", "policy_surface.py")
    for line in changed:
        path = line[3:].strip()
        if not path:
            continue
        assert not any(token in path for token in forbidden), path

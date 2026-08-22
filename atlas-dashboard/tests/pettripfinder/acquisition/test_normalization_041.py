"""PTF-MILWAUKEE-FINAL-PREPUBLICATION-NORMALIZATION-041 -- no deferred state left.

Two debts came into this work order and neither is allowed out of it: a store
the repository knew was behind its own reader, and a release contract prepared
against a market that no longer exists. These assert both are closed, that
closing them moved no approved meaning nobody agreed to, and that the fresh
simulation contains exactly the population a founder approved.
"""

from __future__ import annotations

import copy
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
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.acquisition import approval_rebinding_039 as R39
from scripts.pettripfinder.acquisition import authority_build_036 as A36
from scripts.pettripfinder.acquisition import closure_038 as C38
from scripts.pettripfinder.acquisition import founder_decisions_040 as D40
from scripts.pettripfinder.acquisition import normalization_041 as N41
from scripts.pettripfinder.acquisition import publication_037 as P37
from scripts.pettripfinder.policy_migration import record_hash

SAINT_KATE = "saint kate the arts hotel"
KNICKERBOCKER = "knickerbocker on the lake"
IRON_HORSE = "the iron horse hotel"
HYATT = "hyatt regency milwaukee"


@pytest.fixture(autouse=True)
def _fresh_closure():
    for cached in (C38.capture_attempts, C38.best_replay, C38.active_rows,
                   C38.non_active_rows, C38.later_founder_decisions):
        cached.cache_clear()
    yield


@pytest.fixture(scope="module")
def projection():
    return N41.projection_summary()


@pytest.fixture(scope="module")
def simulation():
    return N41.simulate()


@pytest.fixture(scope="module")
def contract():
    return json.loads(N41.FRESH_CONTRACT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# The projection debt is paid.
# --------------------------------------------------------------------------- #

def test_the_store_and_the_reader_now_agree(projection):
    """The whole point of the work order: nothing is deferred any more.

    Measured live, after normalization -- so every row must now be identical.
    What the projection MOVED is a separate claim, asserted from the committed
    report below, which was written before the store changed.
    """
    assert projection["by_classification"] == {
        N41.SEMANTICS_IDENTICAL: projection["store_rows"]}
    assert projection["blocked"] == []
    assert projection["requires_founder_review"] == []


def test_no_row_is_left_pending():
    register = json.loads(C38.PENDING.read_text(encoding="utf-8"))
    assert register["status"] == "RESOLVED"
    assert register["rows_pending_after_041"] == 0
    assert register["resolved_by"] == N41.WORK_ORDER


def test_the_retired_register_keeps_its_history():
    """A debt that vanishes leaves nobody able to check whether it was paid or
    just forgotten."""
    register = json.loads(C38.PENDING.read_text(encoding="utf-8"))
    assert register["original_population"] == [SAINT_KATE]
    assert register["work_order"].endswith("FULL-CLOSURE-038")
    assert "sixteen founder decisions" in json.dumps(register)
    assert register["rows"][SAINT_KATE]["why"]


def test_the_projection_report_names_every_row():
    doc = json.loads(N41.PROJECTION_REPORT.read_text(encoding="utf-8"))
    assert len(doc["rows"]) == doc["summary"]["store_rows"] == 117
    assert Counter(row["classification"] for row in doc["rows"]) == {
        N41.SEMANTICS_IDENTICAL: 98,
        N41.PROVENANCE_ONLY: 18,
        N41.SEMANTICS_CHANGED_ALREADY_APPROVED: 1,
    }
    keys = [row["identity_key"] for row in doc["rows"]]
    assert len(set(keys)) == len(keys)
    for row in doc["rows"]:
        assert row["classification"]
        assert row["why"].strip()


def test_the_one_semantic_change_was_the_one_a_founder_approved():
    """Recorded in the committed report, because the live store now agrees
    with the reader and the difference is no longer observable from it."""
    doc = json.loads(N41.PROJECTION_REPORT.read_text(encoding="utf-8"))
    assert doc["classified_before_normalizing"] is True
    changed = [row for row in doc["rows"]
               if row["classification"] == N41.SEMANTICS_CHANGED_ALREADY_APPROVED]
    assert [row["identity_key"] for row in changed] == [SAINT_KATE]
    assert changed[0]["founder_approved_this_reading"] is True
    assert D40.WORK_ORDER in changed[0]["why"]
    assert sorted(changed[0]["semantic_difference"]) == [
        "evidence", "proposed_facts", "withheld_fields"]


def test_the_store_row_now_says_what_the_founder_approved():
    from scripts.pettripfinder.acquisition import authority_build_040 as A40
    row = R39.store_rows()[SAINT_KATE]
    approved = A40.candidate_for(SAINT_KATE)
    assert row["proposed_facts"] == approved["proposed_publication_facts"]
    assert row["withheld_fields"] == approved["withheld_fields"]
    assert row["proposed_facts"]["pets_allowed"] is True


def test_a_second_projection_would_change_nothing():
    """Idempotent: the store IS the current reader epoch now."""
    result = N41.normalize_store(apply=False)
    assert result["changed_facts"] == []
    assert result["added"] == [] and result["removed"] == []


# --------------------------------------------------------------------------- #
# Normalizing did not cost an approval, and would not hide one.
# --------------------------------------------------------------------------- #

def test_every_founder_decision_still_binds():
    applicable, refused = A36.bound_decisions()
    assert refused == []
    assert len(applicable) == 97
    superseded = A36.superseded_decisions()
    assert SAINT_KATE in superseded
    assert superseded[SAINT_KATE]["decision"] == D40.APPROVE


def test_a_provenance_only_change_still_does_not_invalidate():
    row = copy.deepcopy(R39.store_rows()["avid hotels milwaukee west waukesha"])
    moved = copy.deepcopy(row)
    moved["rederivation"]["reader_commit"] = "0" * 40
    assert AB.semantic_hash(moved) == AB.semantic_hash(row)
    assert record_hash(moved) != record_hash(row)


def test_a_semantic_change_still_requires_review():
    row = copy.deepcopy(R39.store_rows()["avid hotels milwaukee west waukesha"])
    moved = copy.deepcopy(row)
    moved["proposed_facts"] = dict(moved["proposed_facts"], pets_allowed=False)
    assert AB.semantic_hash(moved) != AB.semantic_hash(row)


def test_normalization_refuses_an_unapproved_semantic_change(monkeypatch):
    """The stop condition, exercised: a row whose meaning moved with no
    founder behind it must halt this work order, not be normalized away."""
    real = N41.classify_projection
    monkeypatch.setattr(N41, "classify_projection", lambda: [
        {"identity_key": "somewhere", "classification": N41.SEMANTICS_CHANGED,
         "safe_to_apply": False}])
    with pytest.raises(N41.NormalizationError):
        N41.assert_safe_to_normalize()
    monkeypatch.setattr(N41, "classify_projection", real)


# --------------------------------------------------------------------------- #
# The stale package cannot come back.
# --------------------------------------------------------------------------- #

def test_the_037_package_is_registered_as_superseded():
    registry = RC.superseded_contracts()
    assert len(registry) == 1
    record = list(registry.values())[0]
    assert record["superseded_by"] == N41.WORK_ORDER
    assert record["stale_assertions"]["expected_record_count"] == 70
    assert record["replacement"].endswith("prepared-041.json")


def test_the_stale_contract_is_refused_even_if_copied_into_the_live_directory():
    staging = Path(tempfile.mkdtemp())
    shutil.copy2(P37.PREPARED_CONTRACT, staging / "milwaukee-wi.json")
    real = RC.RELEASE_CONTRACTS_DIR
    RC.RELEASE_CONTRACTS_DIR = staging
    try:
        with pytest.raises(RC.ReleaseContractError) as caught:
            RC.load_contract("milwaukee-wi")
        assert "SUPERSEDED" in str(caught.value)
    finally:
        RC.RELEASE_CONTRACTS_DIR = real
        shutil.rmtree(staging, ignore_errors=True)


def test_the_historical_037_artifact_was_not_edited():
    """Superseded by content hash, so the original must still BE the original:
    editing 70 to 73 in a historical document is the failure this avoids."""
    stale = json.loads(P37.PREPARED_CONTRACT.read_text(encoding="utf-8"))
    assert stale["policy_package"]["expected_record_count"] == 70
    assert stale["provenance"]["held_identities"] == [HYATT, SAINT_KATE]


def test_milwaukee_has_no_live_release_contract():
    assert "milwaukee-wi" not in set(RC.available_market_ids())
    assert not P37.CONTRACT.is_file()


# --------------------------------------------------------------------------- #
# The fresh preparation.
# --------------------------------------------------------------------------- #

def test_the_fresh_contract_binds_to_the_current_authority(contract):
    from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
    _doc, payload = N41.prospective_package()
    assert contract["policy_package"]["expected_record_count"] == 73
    assert contract["policy_package"]["expected_sha256"] == content_sha256(payload)
    assert contract["public_surface"]["verified_no_pets"] == 27
    assert contract["status"] == "PREPARED_NOT_LIVE"
    assert contract["publish"]["published"] is False
    assert contract["deployment_authorization"]["grants_deployment"] is False


def test_the_fresh_contract_does_not_reuse_the_stale_sha(contract):
    stale = json.loads(P37.PREPARED_CONTRACT.read_text(encoding="utf-8"))
    assert contract["policy_package"]["expected_sha256"] != \
        stale["policy_package"]["expected_sha256"]
    assert contract["supersedes"]["contract_id"] == stale["contract_id"]


def test_the_simulation_derives_73_and_27(simulation):
    assert simulation["pet_friendly_profiles"] == 73
    assert simulation["policy_package_record_count"] == 73
    assert simulation["listings_built"] == 73
    assert simulation["hotel_routes"] == 73
    assert simulation["verified_no_pets"] == 27


def test_saint_kate_is_eligible(simulation):
    assert simulation["saint_kate_present"] is True


def test_the_dual_brand_hiltons_are_both_publishable(simulation):
    assert simulation["dual_brand_jefferson_present"] == [
        "Home2 Suites by Hilton Milwaukee Downtown",
        "Tru by Hilton Milwaukee Downtown"]
    assert simulation["rejected_duplicates"] == []


def test_no_held_or_unresolved_row_leaks(simulation):
    assert simulation["held_identities"] == [HYATT, KNICKERBOCKER, IRON_HORSE] \
        or sorted(simulation["held_identities"]) == sorted(
            [HYATT, KNICKERBOCKER, IRON_HORSE])
    assert simulation["held_leaked_into_inventory"] == []
    assert simulation["exclusion_leaked_into_inventory"] == []
    assert simulation["non_authority_leaked_into_inventory"] == []


def test_only_authority_pet_friendly_rows_reach_the_inventory():
    """Stated as a set relation rather than a count: every published name is a
    row the closure calls AUTHORITY_PET_FRIENDLY, and nothing else is."""
    rows, refused = P37.seed_rows()
    assert refused == []
    authority = {row["identity_key"] for row in C38.active_rows()
                 if row["disposition"] == C38.AUTHORITY_PET_FRIENDLY}
    package = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    assert {record["identity_key"] for record in package["hotels"]} == authority
    assert len(rows) == len(authority) == 73


def test_no_schema_or_evidence_limited_row_is_publishable():
    forbidden = {C38.SCHEMA_UNREPRESENTABLE, C38.INSUFFICIENT_EVIDENCE,
                 C38.ACCESS_UNRESOLVED, C38.POLICY_NOT_FOUND,
                 C38.IDENTITY_UNRESOLVED, C38.SOURCE_CONFLICT,
                 C38.HELD_REVIEW}
    package = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    published = {record["identity_key"] for record in package["hotels"]}
    for row in C38.active_rows():
        if row["disposition"] in forbidden:
            assert row["identity_key"] not in published, row["identity_key"]


# --------------------------------------------------------------------------- #
# Arithmetic and cross-market safety.
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


def test_the_authority_is_still_73_and_27():
    package = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    assert len(package["hotels"]) == 73
    assert len(MA.load_market_exclusions("milwaukee-wi")) == 27


def test_no_other_market_moved():
    doc = json.loads(
        (REPO / "launch_packages/pettripfinder/hotel_exclusions.json")
        .read_text(encoding="utf-8-sig"))
    counts = Counter(row.get("market_id", "") for row in doc["exclusions"])
    assert counts["milwaukee-wi"] == 27
    assert counts["cleveland-akron-canton-oh"] == 40
    assert counts["columbus-oh"] == 16
    assert counts["dayton-oh"] == 8
    assert counts["indianapolis-in"] == 4
    assert counts["pittsburgh-pa"] == 7
    assert MA.check_generated_artifacts() == []


def test_every_other_markets_release_contract_still_verifies():
    for market_id in RC.available_market_ids():
        assert RC.verify_contract(market_id) == [], market_id


def test_milwaukee_is_not_published():
    package = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    assert package["published"] is False
    from scripts.pettripfinder import site_data as SD
    assert SD.load_published_hotel_policy_facts("milwaukee-wi") == {}
    assert len(MA.load_market_seed_rows("milwaukee-wi")) == 0
    ledger = json.loads(C38.LEDGER.read_text(encoding="utf-8"))
    assert ledger["published"] == 0 and ledger["deployed"] == 0


def test_the_simulation_wrote_nothing_to_the_repository():
    """It substitutes the readers in process. A simulation that leaves state
    behind is a publication with a softer name."""
    before = subprocess.run(["git", "status", "--porcelain"],
                            cwd=str(REPO.parent), capture_output=True,
                            text=True).stdout
    N41.simulate()
    after = subprocess.run(["git", "status", "--porcelain"],
                           cwd=str(REPO.parent), capture_output=True,
                           text=True).stdout
    assert before == after


def test_the_recorded_site_dry_run_is_deterministic_and_clean():
    doc = json.loads(N41.SIMULATION.read_text(encoding="utf-8"))
    site = doc["simulation"]["site_dry_run"] if "site_dry_run" in \
        doc["simulation"] else doc["site_dry_run"]
    assert site["deterministic"] is True
    assert len(set(site["bundle_sha256_each"])) == 1
    assert site["gates_failing"] == []
    with_mke = site["with_milwaukee"]
    assert "milwaukee-wi" in with_mke["markets"]
    assert with_mke["broken_links"] == 0
    assert with_mke["collision_count"] == 0
    assert with_mke["global_shadowing_count"] == 0
    assert with_mke["canonical_violations"] == 0
    assert with_mke["deployment_authorized"] is False
    assert site["added_by_milwaukee"]["html_pages"] == 438


def test_the_recorded_simulation_publishes_and_deploys_nothing():
    doc = json.loads(N41.SIMULATION.read_text(encoding="utf-8"))
    assert doc["published"] == 0
    assert doc["deployed"] == 0
    assert doc["provider_calls"] == 0
    assert doc["cost_usd"] == 0.0

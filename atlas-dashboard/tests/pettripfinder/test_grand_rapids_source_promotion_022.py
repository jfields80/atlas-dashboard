# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022, completed under RULING-023.

Two acts, and each gets its own assertions because each is a different way this
pass could have gone wrong.

THE WITHDRAWAL. avid hotel Zeeland leaves the CURRENT authority and its
signature and its identity ruling both survive. Deleting the attestation would
destroy the only record that the founder ever approved it; editing it in place
would rewrite a dated act by a named person. The builder's withdrawal channel
does neither, and the preservation is asserted as hard as the removal.

THE PROMOTION. 35 profiles published, 14 exclusions written to the shard, the
market contract revealed, the globals regenerated from the shards by their own
assembler. What matters as much as the counts is the BLAST RADIUS: the tests
read git rather than a flag in the report, and the only tracked source files
this promotion may have touched are this market's shard, this market's contract
and the generated globals its rows are part of.
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

from scripts.pettripfinder import grand_rapids_holland_source_promotion_022 as P  # noqa: E402
from scripts.pettripfinder.contracts import enums                                 # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "grand-rapids-holland-mi"
PREFIX = "grand_rapids_holland_mi"

WITHDRAWAL = LP / ("%s_founder_withdrawal_022.json" % PREFIX)
AUTHORITY = LP / ("%s_proposed_authority_022.json" % PREFIX)
STORE_022 = LP / ("%s_observation_store_022.json" % PREFIX)
REPORT = LP / ("%s_source_promotion_022.json" % PREFIX)
LEDGER_021 = LP / ("%s_founder_decision_ledger_021.json" % PREFIX)
PACKAGE = LP / ("hotel_policy_facts_%s.json" % MARKET)
SHARD = LP / "markets" / "authority" / MARKET / "hotel_exclusions.json"
CONTRACT = LP / "markets" / ("%s.json" % MARKET)


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def authority():
    return _load(AUTHORITY)


@pytest.fixture(scope="module")
def report():
    return _load(REPORT)


@pytest.fixture(scope="module")
def withdrawal():
    return _load(WITHDRAWAL)


# --------------------------------------------------------------------------- #
# The founder's withdrawal ruling
# --------------------------------------------------------------------------- #

def test_avid_hotel_zeeland_left_the_authority(authority):
    keys = {r["normalized_name"] for r in
            authority["pet_friendly"] + authority["verified_no_pets"]}
    assert P.WITHHELD not in keys
    assert authority["superseded_count"] == 1
    assert authority["superseded_rows"][0]["identity_key"] == P.WITHHELD
    assert authority["superseded_rows"][0]["now"] == enums.SUPERSEDED


def test_the_authority_rebuilt_at_the_expected_counts(authority):
    assert authority["pet_friendly_count"] == 35
    assert authority["verified_no_pets_count"] == 14
    assert authority["authority_total"] == 49
    assert authority["unresolved"] == []
    assert authority["registered"] is False


def test_the_signature_and_the_identity_ruling_both_survive(withdrawal,
                                                            authority):
    """A withdrawal removes a row from the CURRENT authority. It does not
    unmake a dated act by a named person."""
    row = withdrawal["withdrawals"][0]
    assert row["retired_identity_key"] == P.WITHHELD
    assert row["signature_preserved"] is True
    assert row["identity_ruling_preserved"] is True
    assert row["readiness_state_at_withdrawal"] == "POLICY_NOT_FOUND"
    assert row["returns_to"] == "unresolved, pending actual policy evidence"

    signed = {r["identity_key"] for r in _load(LEDGER_021)["signed"]}
    assert P.WITHHELD in signed, "the 021 attestation must be untouched"
    confirmations = {c["identity_key"]
                     for c in authority["identity_confirmations"]}
    assert P.WITHHELD in confirmations, "the 020 identity ruling travels on"


def test_the_withdrawal_refuses_to_name_a_row_that_is_not_there():
    """A withdrawal that names an absent row would misdescribe the act."""
    with pytest.raises(P.PromotionError):
        P.withdrawal_ledger({}, {"pet_friendly": [], "verified_no_pets": []})


def test_the_ruling_is_recorded_with_its_reason(report):
    ruling = report["founder_ruling"]
    assert ruling["identity_key"] == P.WITHHELD
    assert ruling["ruled_by"] == "PTF-FOUNDER-001"
    assert ruling["signature_preserved"] is True
    assert "publishable pet-policy fact" in ruling["why"]


# --------------------------------------------------------------------------- #
# The promotion
# --------------------------------------------------------------------------- #

def test_source_promotion_completed(report):
    assert report["source_promoted"] is True
    assert report["assembled"] is False
    assert report["deployed"] is False
    counts = report["counts"]
    assert counts["pet_friendly"] == 35
    assert counts["verified_no_pets"] == 14
    assert counts["authority_total"] == 49
    assert counts["profiles_published"] == 35
    assert counts["exclusions_written"] == 14
    assert counts["withdrawn"] == 1


def test_the_policy_package_is_published_in_source():
    package = _load(PACKAGE)
    assert package["published"] is True
    assert package["count"] == 35
    assert package["refusals"] == []
    assert package["publication"]["deployed"] is False
    assert package["publication"]["work_order"] == (
        "PTF-GRAND-RAPIDS-WEIGHT-SEMANTICS-RULING-023")


def test_the_exclusions_shard_holds_the_fourteen():
    shard = _load(SHARD)
    assert shard["count"] == 14
    assert len(shard["exclusions"]) == 14
    for row in shard["exclusions"]:
        assert row["exclusion_state"] == enums.VERIFIED_NO_PETS
        assert row["evidence_quote"].strip()
        assert row["reviewer_id"] == "PTF-FOUNDER-001"
        assert row["record_hash"] and row["approval_hash"]


def test_a_corrected_name_flows_through_to_the_exclusion():
    """The contract derives normalized_name from canonical_name, so 020's name
    correction moves both. The row still carries the founder decision it
    restates, which is what ties it back to the census identity signed."""
    shard = _load(SHARD)
    row = next(r for r in shard["exclusions"]
               if r["canonical_name"] == "DoubleTree by Hilton Hotel Holland")
    assert row["normalized_name"] == "doubletree by hilton hotel holland"
    assert row["decision_source"]["decided_by"] == "PTF-FOUNDER-001"
    assert row["decision_source"]["work_order"] == (
        "PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-021")


def test_the_market_contract_was_revealed(report):
    contract = _load(CONTRACT)
    assert contract["show_in_navigation"] is True
    assert contract["show_in_sitemap"] is True
    assert P.contract_still_denies_policy(contract) == []
    # The END state, not the delta: a re-run over an already-promoted tree
    # changes nothing and would report zero changes while being perfectly
    # correct.
    end = report["contract_end_state"]
    assert end["show_in_navigation"] is True
    assert end["show_in_sitemap"] is True
    assert "discovery-stage" not in end["introductory_copy"].lower()


def test_the_globals_gained_only_grand_rapids_rows(report):
    check = report["validation"]["globals_gained_only_grand_rapids_rows"]
    assert check["ok"] is True
    exclusions = check["by_artifact"]["hotel_exclusions.json"]
    assert exclusions["removed"] == 0
    assert exclusions["added_from_another_market"] == []
    assert exclusions["rows_for_this_market_in_the_end_state"] == 14
    routing = check["by_artifact"]["identity_routing.json"]
    # Publication withdraws this market's answered routes, which is a real
    # removal of ITS OWN rows. What must be zero in either direction is any
    # movement of somebody else's.
    assert routing["added_from_another_market"] == []
    assert routing["removed_from_another_market"] == []
    assert routing["changed_in_another_market"] == []


def test_no_other_market_shard_changed(report):
    check = report["validation"]["no_other_market_shard_changes"]
    assert check["ok"] is True
    assert check["changed"] == []
    assert check["files_checked"] >= 40


def test_the_four_ohio_markets_are_unchanged(report):
    check = report["validation"]["the_four_ohio_markets_are_unchanged"]
    assert check["ok"] is True
    assert "--write" in check["note"]


def test_every_validation_check_passes(report):
    validation = report["validation"]
    for name, check in validation.items():
        if name == "all_pass":
            continue
        assert check["ok"] is True, "%s: %r" % (name, check)
    assert validation["all_pass"] is True


# --------------------------------------------------------------------------- #
# The blast radius
# --------------------------------------------------------------------------- #

def test_only_this_markets_source_was_written():
    """Read from git, not from a flag in the report. The only tracked source
    files this promotion may touch are this market's shard, this market's
    contract, and the generated globals its rows are part of."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/hotel_exclusions.json",
         "launch_packages/pettripfinder/identity_routing.json",
         "launch_packages/pettripfinder/seed_businesses.csv",
         "launch_packages/pettripfinder/ptf_global_authority_manifest.json",
         "launch_packages/pettripfinder/identity_census"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    allowed = {
        "atlas-dashboard/launch_packages/pettripfinder/markets/authority/%s/hotel_exclusions.json" % MARKET,
        "atlas-dashboard/launch_packages/pettripfinder/markets/%s.json" % MARKET,
        "atlas-dashboard/launch_packages/pettripfinder/hotel_exclusions.json",
        "atlas-dashboard/launch_packages/pettripfinder/ptf_global_authority_manifest.json",
    }
    touched = {line[3:].strip().strip('"')
               for line in result.stdout.splitlines() if line.strip()}
    assert touched <= allowed, "unexpected source writes: %s" % (touched - allowed)


def test_no_census_was_touched():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/identity_census"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.stdout.strip() == ""


def test_the_seed_inventory_was_written_by_the_sanctioned_installer():
    """A published record with no seed row FAILS CLOSED in
    site_data.verified_public_hotels, so the display rows are not decoration --
    without them this market raises rather than publishes."""
    from scripts.pettripfinder import market_authority as MA
    assert len(MA.load_market_seed_rows(MARKET)) == 35


def test_the_routing_shard_was_not_wiped_only_answered(report):
    """Two different things had to be true of the routing shard.

    market_registration_cli.write() would have rewritten it as EMPTY -- right
    for a market with no routes and destructive for this one, which carries 110
    from an earlier repair. That write is refused.

    Publication then legitimately WITHDRAWS the 31 routes it answered: a route
    exists to find a hotel's page, and once the hotel is seed inventory the
    seed is the source of truth for it. Every other published market carries no
    route for a published identity. The withdrawn records are archived whole so
    nothing leaves the record."""
    from scripts.pettripfinder import market_authority as MA
    assert len(MA.load_market_routes(MARKET)) == 79
    guard = report["routing_shard_not_wiped"]
    assert guard["routes_before"] == guard["routes_after"], (
        "the installer's empty-routing write must never have run")
    withdrawn = report["routes_withdrawn_by_publication"]
    # The END state, which any re-run reproduces. "withdrawn" and
    # "routes_before" describe the run that made the change.
    assert withdrawn["routes_after"] == 79
    assert withdrawn["routes_for_a_published_identity_in_the_end_state"] == 0
    assert len(report["withdrawn_route_records"]) in (0, 31)
    assert all(r.get("official_property_url")
               for r in report["withdrawn_route_records"]), (
        "the archive must carry the whole record, not a list of names")


def test_the_census_gap_that_blocked_the_release_contract_is_closed(report):
    """This pass could not write a release contract: nine of the 49 promoted
    identities were absent from the market's pinned 120-identity census, and
    stating 120 beside 49 resolved would have passed the gate by asserting
    something untrue. PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024
    promoted the 163-row recensus and closed it, so the report now describes
    the world it actually finds rather than the one it first ran in."""
    contract = report["release_contract"]
    assert contract["blocked_when_this_pass_first_ran"] is True
    assert contract["pinned_census"]["count"] == 163
    assert contract["promoted_identities"] == 49
    assert contract["promoted_identities_absent_from_the_pinned_census"] == []
    assert contract["unblocked_by"] == (
        "PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024")
    assert contract["written"] is True
    assert (REPO_ROOT / "deploy" / "netlify" / "release_contracts"
            / ("%s.json" % MARKET)).exists()


def test_nothing_was_assembled_or_deployed(report):
    assert report["not_done_here"]
    assert report["next_step_for_production_assembly"]
    joined = " ".join(report["next_step_for_production_assembly"])
    for expected in ("release_contracts", "launch_participation",
                     "global_deployment_manifest"):
        assert expected in joined


# --------------------------------------------------------------------------- #
# The repair 021 needed
# --------------------------------------------------------------------------- #

def test_a_corrected_fact_got_the_evidence_entry_that_cites_it():
    """021 applied 020's weight-limit correction to the extraction and stopped
    there, so the projector could find no quote for the field and declined to
    publish it. The quote is not invented -- 020 read it off the saved policy
    block and checked it against that block before allowing the correction."""
    store = _load(STORE_022)
    repairs = store["correction_evidence_repaired"]
    assert len(repairs) == 1
    assert repairs[0]["identity_key"] == "baymont by wyndham holland"
    assert repairs[0]["field"] == "weight_limit"
    record = next(r for r in store["records"]
                  if r["identity_key"] == "baymont by wyndham holland")
    refs = [e.get("field_refs") for e in record["observation"]["evidence"]]
    assert ["weight_limit"] in refs


def test_the_repair_is_idempotent_and_scoped_to_facts():
    """A name is not a policy fact, so the repair never touches one."""
    ledger = _load(LP / ("%s_founder_decision_ledger_020.json" % PREFIX))
    _store, repairs = P.repair_correction_evidence(_load(STORE_022), ledger)
    assert repairs == []
    names = [c for c in ledger["corrections"] if c["field"] == "canonical_name"]
    assert len(names) == 3


def test_nothing_was_spent(report, withdrawal):
    for document in (report, withdrawal, _load(STORE_022)):
        assert document.get("provider_calls", 0) == 0
        assert document.get("usd_spent", 0.0) == 0.0

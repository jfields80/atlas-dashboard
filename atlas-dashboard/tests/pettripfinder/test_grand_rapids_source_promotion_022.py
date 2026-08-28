# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022.

The founder's withdrawal ruling landed and the authority rebuilt at 49. Source
promotion did NOT happen, and the tests below pin both halves of that, because
each is a different way this pass could have been wrong.

THE WITHDRAWAL. avid hotel Zeeland leaves the CURRENT authority and its
signature and its identity ruling both survive. Deleting the attestation would
destroy the only record that the founder ever approved it; editing it in place
would rewrite a dated act by a named person. The builder's withdrawal channel
does neither, and the tests assert the preservation as hard as the removal.

THE PROMOTION THAT DID NOT HAPPEN. 25 of 35 profiles carry a weight limit the
schema will not publish without a comparison the source never stated, and the
only thing that changes that is a FOUNDER decision this market has not made --
020 established that another market's precedent is not inherited. Promotion is
all-or-nothing here: a market made visible with 14 exclusions and no profiles is
worse than one left alone. So nothing was written into markets/ or the globals,
and the tests assert the source tree is untouched rather than merely that a flag
says so.

Both readings were MEASURED into scratch rather than argued about: strict
refuses 25, the lte/per-pet ruling refuses 1. That last one is a phrase the
projector's maximal-wording list does not recognise, and widening that list
inside the pass whose count it raises is exactly how a measurement stops being
one -- so it is reported and not fixed.
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
AUTHORITY_021 = LP / ("%s_proposed_authority_021.json" % PREFIX)
LEDGER_021 = LP / ("%s_founder_decision_ledger_021.json" % PREFIX)


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
# The founder's ruling
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
    assert authority["published"] is False
    assert authority["deployed"] is False


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
    ruling = report["founder_ruling_applied"]
    assert ruling["identity_key"] == P.WITHHELD
    assert ruling["ruled_by"] == "PTF-FOUNDER-001"
    assert "does not establish a publishable pet-policy fact" in ruling["why"] \
        or "did not establish a publishable" in ruling["why"]


# --------------------------------------------------------------------------- #
# The promotion that did not happen
# --------------------------------------------------------------------------- #

def test_source_promotion_is_reported_as_blocked(report):
    assert report["source_promoted"] is False
    assert report["assembled"] is False
    assert report["deployed"] is False
    assert report["blocker"]["blocked"] is True
    assert report["blocker"]["rows_blocked"] == 25
    assert report["blocker"]["pet_friendly_total"] == 35


def test_both_readings_were_measured_not_argued(report):
    measured = report["blocker"]["measured_both_readings"]
    assert measured["strict_refused"] == 25
    assert measured["with_the_lte_per_pet_ruling_refused"] == 1


def test_the_blocker_names_why_this_pass_will_not_decide_it(report):
    blocker = report["blocker"]
    assert "not inherited automatically" in blocker["why_this_pass_will_not_supply_them"]
    assert blocker["why_the_reader_did_not_supply_them"]
    assert len(blocker["what_would_unblock_it"]) == 3


def test_a_blanket_rule_is_not_obviously_right_for_this_data(report):
    """One source says "under", which is lt. Publishing it as lte would tell a
    guest with a dog at exactly the limit that it is welcome."""
    stated = report["blocker"]["comparison_the_sources_actually_state"]
    assert stated["lte"] == 23
    assert stated["lt"] == 1
    assert stated["NONE_STATED"] == 1
    assert sum(stated.values()) == 25


def test_the_residual_row_is_reported_and_not_fixed(report):
    """Widening the projector's phrase list inside the pass whose count it
    raises is how a measurement stops being one."""
    residual = report["blocker"]["residual_after_the_ruling"]
    assert residual["identity_key"] == "baymont by wyndham holland"
    assert residual["quote"] == "must not weigh more than 100 lbs each"
    assert residual["not_fixed_here"]


# --------------------------------------------------------------------------- #
# Nothing was written into source
# --------------------------------------------------------------------------- #

def test_no_market_contract_shard_or_global_was_written():
    """Asserted from git, not from a flag in the report."""
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
    assert result.stdout.strip() == "", (
        "source was written despite a blocked promotion: %r" % result.stdout)


def test_the_market_contract_still_describes_a_discovery_stage_market():
    contract = _load(LP / "markets" / ("%s.json" % MARKET))
    assert contract["show_in_navigation"] is False
    assert contract["show_in_sitemap"] is False
    assert P.contract_still_denies_policy(contract), (
        "the contract must not have been revealed while promotion is blocked")


def test_no_policy_package_was_created():
    assert not (LP / ("hotel_policy_facts_%s.json" % MARKET)).exists()


def test_the_exclusions_shard_is_still_empty():
    shard = _load(LP / "markets" / "authority" / MARKET / "hotel_exclusions.json")
    assert shard["count"] == 0
    assert shard["exclusions"] == []


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


def test_a_name_correction_needs_no_evidence_entry():
    """A name is not a policy fact, so the repair is scoped to facts."""
    ledger = _load(LP / ("%s_founder_decision_ledger_020.json" % PREFIX))
    store, repairs = P.repair_correction_evidence(_load(STORE_022), ledger)
    assert repairs == [], "the repair must be idempotent"
    names = [c for c in ledger["corrections"] if c["field"] == "canonical_name"]
    assert len(names) == 3


# --------------------------------------------------------------------------- #
# What comes next
# --------------------------------------------------------------------------- #

def test_the_report_says_what_is_ready_and_what_is_waiting(report):
    assert report["nothing_was_written_into_source"]
    assert report["what_is_ready_and_waiting"]
    assert report["authority_rebuilt"]["matches_the_expected_counts"] is True


def test_nothing_was_spent(report, withdrawal):
    for document in (report, withdrawal, _load(STORE_022)):
        assert document.get("provider_calls", 0) == 0
        assert document.get("usd_spent", 0.0) == 0.0

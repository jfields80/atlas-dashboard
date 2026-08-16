"""PTF-DAYTON-RECERTIFICATION-001 Pass A -- committed-state tests.

These validate the COMMITTED outcome of the artifact-verification pass: the
upgraded facts package, the verification report, the re-attestation packet and
the release-contract pin. They deliberately do not read the gitignored worker
tree, so they run in every worktree; the on-disk hash verification itself is the
script's job and its verdicts are recorded in the committed report.

The governance assertions are the point of this file. A pass that adds artifact
bindings moves every record_hash, and the failure mode worth guarding against is
not a wrong hash -- it is a human name left sitting on a machine's work.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as evidence_contract
from scripts.pettripfinder.dayton_pass_a_artifact_verification import (
    AGENT_IDENTITY, FACT_EVIDENCE_ALIASES, alias_covered_facts,
)
from scripts.pettripfinder.policy_migration import (
    evidence_hash, evidence_ref_for, record_hash,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / "hotel_policy_facts_dayton-oh.json"
REPORT_PATH = LP / "dayton_artifact_verification_001.json"
PACKET_PATH = LP / "dayton_passA_reauth_packet.json"
CENSUS_PATH = LP / "identity_census" / "dayton-oh.json"
CONTRACT_PATH = (REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / "dayton-oh.json")

EXPECTED_RECORDS = 47
EXPECTED_ENTRIES = 256


@pytest.fixture(scope="module")
def facts():
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report():
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def packet():
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Coverage.
# --------------------------------------------------------------------------- #

def test_report_covers_every_published_record(facts, report):
    assert report["schema"] == "ptf-dayton-artifact-verification/1.0"
    assert report["market_id"] == "dayton-oh"
    assert len(facts["hotels"]) == EXPECTED_RECORDS
    assert report["records_checked"] == EXPECTED_RECORDS
    assert {row["identity_key"] for row in report["records"]} == \
        {hotel["identity_key"] for hotel in facts["hotels"]}


def test_every_record_verified_complete(report):
    """No failures of any kind survived the pass.

    The audit that commissioned Pass A expected 35 complete and 12 partial,
    splitting on whether a screenshot existed. The contract does not ask for a
    screenshot, so that split is reported as capture_grade and the twelve
    deterministic fetches verify complete on their retained page HTML.
    """
    assert report["classification_counts"] == {
        "ARTIFACT_VERIFIED_COMPLETE": EXPECTED_RECORDS,
    }
    assert report["capture_grade_counts"] == {
        "BROWSER_ASSISTED_WITH_SCREENSHOT": 35,
        "DETERMINISTIC_FETCH_NO_SCREENSHOT": 12,
    }
    for row in report["records"]:
        assert row["quote_contiguity_failures"] == []
        assert all(row["checks"][name] for name in (
            "html_sha256_agrees",
            "source_url_agrees_with_capture",
            "quotes_contiguous_in_capture_text",
            "captured_at_recorded_by_the_run",
        )), row["identity_key"]


def test_screenshot_absence_never_blocked_a_promotion(report):
    """A screenshot is evidence of capture strength, not a contract requirement.

    Guarding the inference directly: every record without one still promoted,
    and the report says in prose why that is correct.
    """
    for row in report["records"]:
        if row["capture_grade"] == "DETERMINISTIC_FETCH_NO_SCREENSHOT":
            assert row["checks"]["screenshot_present"] is False
            assert row["classification"] == "ARTIFACT_VERIFIED_COMPLETE"
            assert row["entries_upgraded"] > 0
    assert "PUBLICATION_GRADE_REQUIRED does not name a screenshot" \
        in report["screenshot_rule"]


# --------------------------------------------------------------------------- #
# The evidence contract.
# --------------------------------------------------------------------------- #

def test_every_entry_is_publication_grade(facts):
    total = 0
    for hotel in facts["hotels"]:
        for entry in hotel["evidence"]:
            total += 1
            assert entry["artifact_class"] == enums.PUBLICATION_GRADE_EVIDENCE
            assert entry["artifact_kind"] == enums.ARTIFACT_RENDERED_HTML
            assert entry["source_grade"] == enums.GRADE_PT1_FIRST_PARTY
            assert entry["captured_at"]
            assert entry["capture_method"] in ("browser_assisted",
                                               "deterministic_fetch")
            # The binding names the page the authority's own result hash names.
            assert entry["artifact_sha256"] == \
                "sha256:%s" % hotel["worker_result_hash"]
        assert not evidence_contract.validate(hotel)
    assert total == EXPECTED_ENTRIES


def test_required_fields_are_present_on_every_entry(facts):
    for hotel in facts["hotels"]:
        for entry in hotel["evidence"]:
            for required in evidence_contract.PUBLICATION_GRADE_REQUIRED:
                assert entry.get(required), (hotel["identity_key"], required)


def test_upgrade_did_not_touch_quotes_or_the_evidence_set(facts):
    """Refs derive from field+quote+url, so identical refs prove the upgrade
    changed bindings only -- never the words a fact rests on."""
    for hotel in facts["hotels"]:
        haystack = " ".join(hotel["evidence_quote"].split())
        for entry in hotel["evidence"]:
            assert entry["evidence_ref"] == evidence_ref_for(entry)
            assert evidence_contract.quote_is_contiguous(
                entry["quote"], haystack) or entry["field"] in (
                    "general_restrictions",)


def test_no_published_fact_is_uncited_under_either_name(facts):
    """Pass A asserts alias coverage rather than assuming it.

    ``unevidenced_facts`` matches fact keys to evidence field names literally,
    and schema 1.2 renamed several fact keys without renaming their evidence
    field. Every such report must resolve through the alias map; a fact cited
    under neither name raises.
    """
    reported = set()
    for hotel in facts["hotels"]:
        reported.update(alias_covered_facts(hotel))
    assert reported <= set(FACT_EVIDENCE_ALIASES)


def test_alias_inventory_is_reported_not_hidden(facts, report):
    section = report["facts_cited_under_an_aliased_evidence_field"]
    counted = {}
    for hotel in facts["hotels"]:
        for fact in alias_covered_facts(hotel):
            counted[fact] = counted.get(fact, 0) + 1
    assert section["counts_by_fact"] == counted
    assert section["records_affected"] == \
        sum(1 for h in facts["hotels"] if alias_covered_facts(h))


# --------------------------------------------------------------------------- #
# Governance.
# --------------------------------------------------------------------------- #

def test_no_human_name_carries_a_machine_decision(facts):
    """The rule this whole pass is shaped around.

    An attestation needs the human. Pass A verified hashes; it did not review
    anything, so the live decision is machine-reviewed-pending-operator and the
    operator field names the agent -- never jfields80.
    """
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        assert approval["decision"] == enums.MACHINE_REVIEWED_PENDING_OPERATOR
        assert approval["operator"] == AGENT_IDENTITY
        assert approval["operator"] != "jfields80"
        assert approval["decision"] not in enums.PUBLISHING_DECISIONS


def test_prior_human_approval_is_preserved_verbatim_and_unbound(facts):
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        prior = approval["supersedes"]
        assert prior["operator"] == "jfields80"
        assert prior["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert prior["record_hash"]
        # Provably no longer binding: the record moved underneath it.
        assert prior["record_hash"] != approval["record_hash"]
        # ...but the evidence set did not, which is what makes the upgrade safe.
        assert prior["evidence_hash"] == approval["evidence_hash"]


def test_every_approval_binds_the_record_it_signs(facts):
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        assert approval["record_hash"] == record_hash(hotel)
        assert approval["evidence_hash"] == evidence_hash(hotel["evidence"])


def test_reattestation_packet_matches_the_committed_records(facts, packet):
    assert packet["schema"] == "ptf-dayton-passA-reauth-packet/1.0"
    assert packet["records_awaiting_reattestation"] == EXPECTED_RECORDS
    by_key = {hotel["identity_key"]: hotel for hotel in facts["hotels"]}
    assert len(packet["records"]) == EXPECTED_RECORDS
    for row in packet["records"]:
        hotel = by_key[row["identity_key"]]
        assert row["reattestation_required"] is True
        assert row["record_hash_to_attest"] == hotel["approval"]["record_hash"]
        assert row["evidence_hash_unchanged"] == \
            hotel["approval"]["evidence_hash"]
        assert row["prior_record_hash"] == \
            hotel["approval"]["supersedes"]["record_hash"]
        assert row["prior_operator"] == "jfields80"


# --------------------------------------------------------------------------- #
# Scope: Pass A changed bindings and nothing else.
# --------------------------------------------------------------------------- #

def test_pass_a_left_every_fact_untouched(facts):
    """The thirteen policy corrections belong to Pass B.

    Asserted against the conditions the audit named, so a Pass-A run that
    quietly repaired one would fail here rather than pass silently.
    """
    by_key = {hotel["identity_key"]: hotel for hotel in facts["hotels"]}
    # The six general_restrictions monetary leaks are still present, verbatim.
    # Pinned to the exact committed strings rather than to "contains a currency
    # marker": Staybridge states its ladder in bare numerals, which is part of
    # why the leak is hard to see, and a looser assertion missed it.
    leaks = {
        "springhill suites troy dayton":
            "Dogs only, no cats. 1-7 Nights - $75, 8-14 Nights - $150, "
            "15+ Nights - $250",
        "towneplace suites by marriott dayton beavercreek":
            "Non-Refundable Pet Fee Per Stay: $100.00 Non-Refundable Pet Fee "
            "Per Night: $20.00",
        "hilton garden inn dayton beavercreek":
            "$75(1-5 nights) additional $75(5+ night) dogs & cats only. "
            "Two pets max per room.",
        "home2 suites by hilton dayton beavercreek":
            "75.00(1-4n),$125(5+n) 2petsMax,dog/cat on",
        "staybridge suites miamisburg":
            "Fee is nonrefundable. Guests will be charged 50 per pet for one "
            "to six night stays and 150 per pet for seven plus nights.",
        "courtyard by marriott springfield downtown":
            "Pets allowed with USD 75 + 17.25% tax, non-refundable fee per "
            "stay ($87.94)",
    }
    for key, stated in leaks.items():
        assert by_key[key]["facts"]["general_restrictions"] == stated, key
    # The five missing service-animal statements are still missing.
    for key in ("days inn by wyndham sidney",
                "extended stay america suites dayton fairborn",
                "extended stay america suites dayton south",
                "extended stay america suites dayton north",
                "extended stay america select suites dayton miamisburg"):
        assert "service_animal_statement" not in by_key[key]
    # The two La Quinta fee-scope pointers are still absent.
    for key in ("la quinta inn and suites by wyndham fairborn wright patterson",
                "la quinta inn and suites by wyndham miamisburg dayton south"):
        assert by_key[key]["facts"]["pet_fee"]["scope"] == "per_room"
        assert "fee_scope" not in {e["field"] for e in by_key[key]["evidence"]}


def test_withholding_decisions_survived_untouched(facts):
    withheld = {h["identity_key"]: h["withheld_fields"]
                for h in facts["hotels"] if h.get("withheld_fields")}
    assert len(withheld) == 15
    codes = [decision["reason_code"]
             for decisions in withheld.values()
             for decision in decisions.values()]
    assert len(codes) == 21
    assert set(codes) == {"SOURCE_AMBIGUOUS", "SOURCE_CONTRADICTORY"}
    assert "SOURCE_SILENT" not in codes


def test_schema_and_record_count_are_unchanged(facts):
    assert facts["schema_version"] == "1.2"
    assert facts["market_id"] == "dayton-oh"
    assert all(hotel["schema_version"] == "1.2" for hotel in facts["hotels"])
    assert all(hotel["verification_state"] == "VERIFIED_PET_FRIENDLY"
               for hotel in facts["hotels"])


# --------------------------------------------------------------------------- #
# Census hygiene: prepared, not applied.
# --------------------------------------------------------------------------- #

def test_census_hygiene_is_a_proposal_and_the_census_is_untouched(report):
    section = report["census_hygiene"]
    assert section["status"] == "PROPOSED_NOT_APPLIED"
    assert section["authorised_by_the_census_contract"] is False
    assert section["identities_in_registry_and_partition_but_not_annotated"] \
        == ["best western celina"]
    assert section["registry_verified_no_pets"] == 8
    assert section["partition_verified_no_pets"] == 8
    assert section["census_policy_state_verified_no_pets"] == 7

    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    by_key = {row["identity_key"]: row for row in census["hotels"]}
    # Untouched: still the pre-Pass-A annotation and the pre-Pass-A rollup.
    assert by_key["best western celina"]["policy_state"] == "POLICY_NOT_VERIFIED"
    assert census["no_pets_count"] == 7


# --------------------------------------------------------------------------- #
# Release contract.
# --------------------------------------------------------------------------- #

def test_release_contract_pins_the_upgraded_package(report):
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    actual = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest()
    assert contract["policy_package"]["expected_sha256"] == actual
    assert report["facts_sha256_after_apply"] == actual
    assert report["facts_sha256_before_apply"] != actual
    assert contract["policy_package"]["expected_record_count"] == \
        EXPECTED_RECORDS


def test_package_file_is_lf_and_utf8():
    """The pin is over the file's BYTES; a CRLF translation would make it lie."""
    raw = FACTS_PATH.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")
    raw.decode("utf-8")


def test_no_captured_page_bytes_were_committed(report):
    """Captured brand pages embed third-party credentials and never enter git."""
    assert "never committed" in report["artifact_custody"]
    for row in report["records"]:
        for path in row["artifact_paths"].values():
            assert path.startswith("data/worker_runs/")
            assert not (REPO_ROOT / path).exists()

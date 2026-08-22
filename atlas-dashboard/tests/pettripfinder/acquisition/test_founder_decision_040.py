"""PTF-MILWAUKEE-FOUNDER-DECISION-040 -- the founder answered, and only that.

Four rows entered authority because a person said so. These assert that what
went in is what they said, that the two holds went nowhere, and that none of
the rules the earlier work orders put up were quietly stepped over to get
there.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import approval_binding as AB
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.acquisition import authority_build_036 as A36
from scripts.pettripfinder.acquisition import authority_build_040 as A40
from scripts.pettripfinder.acquisition import closure_038 as C38
from scripts.pettripfinder.acquisition import founder_decisions_036 as D36
from scripts.pettripfinder.acquisition import founder_decisions_040 as D40
from scripts.pettripfinder.acquisition import founder_review_036 as F36
from scripts.pettripfinder.acquisition import founder_review_039 as V39

BROWN_DEER = "country inn and suites by radisson brown deer milwaukee north"
BROOKFIELD = ("country inn and suites by radisson milwaukee west "
              "brookfield wi")
ECONO = "econo lodge milwaukee airport"
KNICKERBOCKER = "knickerbocker on the lake"
SAINT_KATE = "saint kate the arts hotel"
IRON_HORSE = "the iron horse hotel"


def files_changed_by_this_work_order():
    """What 040 touched: its own commit once made, the working set before."""
    marker = "atlas-dashboard/scripts/pettripfinder/acquisition/authority_build_040.py"
    commit = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", marker],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.split()
    if commit:
        return subprocess.run(
            ["git", "show", "--name-only", "--format=", commit[-1]],
            cwd=str(REPO.parent), capture_output=True, text=True).stdout.split()
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.splitlines()
    return [line[3:].strip().strip('"') for line in porcelain if line[3:].strip()]


@pytest.fixture(scope="module")
def ledger():
    return D40.load_ledger()


@pytest.fixture(scope="module")
def authority():
    return json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def records(authority):
    return {record["identity_key"]: record for record in authority["hotels"]}


@pytest.fixture(scope="module")
def exclusions():
    return {row["normalized_name"]: row
            for row in MA.load_market_exclusions(C38.MARKET)}


@pytest.fixture(autouse=True)
def _fresh_closure():
    for cached in (C38.capture_attempts, C38.best_replay, C38.active_rows,
                   C38.non_active_rows, C38.later_founder_decisions):
        cached.cache_clear()
    yield


# --------------------------------------------------------------------------- #
# The six decisions.
# --------------------------------------------------------------------------- #

EXPECTED = [
    (BROWN_DEER, D40.APPROVE),
    (BROOKFIELD, D40.APPROVE),
    (ECONO, D40.APPROVE_REFUSAL),
    (KNICKERBOCKER, D40.HOLD),
    (SAINT_KATE, D40.APPROVE),
    (IRON_HORSE, D40.HOLD),
]


def test_exactly_six_decisions_are_recorded(ledger):
    assert len(ledger["decisions"]) == 6
    assert [(row["identity_key"], row["decision"])
            for row in ledger["decisions"]] == EXPECTED


def test_the_transcript_and_the_ledger_agree():
    assert D40.assert_matches_the_decision_order()["decisions_in_order"] == [
        verdict for _key, verdict in EXPECTED]


def test_every_decision_names_a_person_and_a_time(ledger):
    for row in ledger["decisions"]:
        assert row["decided_by"] == D40.FOUNDER
        assert row["decided_at"] == D40.DECIDED_AT
        assert row["decision_basis"].strip()
        assert row["reason"].strip()
        assert row["prior_review_status"] == "AWAITING_FOUNDER_DECISION"
        assert row["originating_work_order"].endswith("FULL-CLOSURE-038")
        assert row["candidate_package"] == V39.REVIEW_JSON.name


def test_the_ledger_is_bound_under_the_039_contract(ledger):
    assert ledger["binding_contract"] == AB.BINDING_CONTRACT_VERSION
    for row in ledger["decisions"]:
        assert row["binding_contract"] == AB.BINDING_CONTRACT_VERSION
        assert row["semantic_hash"].startswith("sha256:")


def test_the_036_ledger_is_untouched():
    """036 is history. 040 sits beside it and does not edit it."""
    assert D40.LEDGER != F36.LEDGER
    assert not [path for path in files_changed_by_this_work_order()
                if path.endswith("milwaukee_founder_decisions_036.json")]
    assert len(F36.load_ledger()["decisions"]) == 98


def test_the_ledger_refuses_a_missing_decision(monkeypatch):
    monkeypatch.setattr(D40, "ANSWERS", D40.ANSWERS[:-1])
    with pytest.raises(D40.DecisionError):
        D40.assert_writable()


def test_the_ledger_refuses_a_duplicate_decision(monkeypatch):
    monkeypatch.setattr(D40, "ANSWERS",
                        D40.ANSWERS[:-1] + (("Saint Kate", D40.HOLD),))
    with pytest.raises(D40.DecisionError):
        D40.assert_writable()


def test_an_ambiguous_shorthand_is_refused():
    """The two Country Inn properties differ by a single word. A founder
    decision must name exactly one row, and a near miss must not resolve."""
    candidates = D40.committed_package()["candidates"]
    with pytest.raises(D40.DecisionError):
        D40.resolve("Country Inn & Suites by Radisson", candidates)


def test_a_moved_candidate_breaks_the_binding():
    package = copy.deepcopy(D40.committed_package())
    target = next(row for row in package["candidates"]
                  if row["identity_key"] == BROWN_DEER)
    target["proposed_publication_facts"]["pet_fee"] = 9999
    moved = A40.semantic_row(target)
    decision = next(row for row in D40.load_ledger()["decisions"]
                    if row["identity_key"] == BROWN_DEER)
    assert AB.semantic_hash(moved) != decision["semantic_hash"]


# --------------------------------------------------------------------------- #
# What entered authority.
# --------------------------------------------------------------------------- #

def test_brown_deer_is_approved_with_the_facts_the_founder_saw(records):
    facts = records[BROWN_DEER]["facts"]
    assert facts["pets_allowed"] is True
    assert facts["pet_fee"]["amount_cents"] == 3000
    assert facts["pet_fee"]["currency"] == "USD"
    assert facts["pet_fee"]["basis"] == "per_night"
    assert facts["pet_fee"]["scope"] == "per_pet"
    assert facts["weight_limit"]["value"] == 65.0
    assert facts["weight_limit"]["unit"] == "lb"
    assert facts["pet_count_limit"] == 2
    assert records[BROWN_DEER]["verification_state"] == "VERIFIED_PET_FRIENDLY"


def test_brookfield_is_approved_and_keeps_the_non_refundable_wording(records):
    facts = records[BROOKFIELD]["facts"]
    assert facts["pets_allowed"] is True
    assert facts["pet_fee"]["amount_cents"] == 10000
    assert facts["pet_fee"]["basis"] == "per_stay"
    assert facts["pet_fee"]["scope"] == "per_pet"
    assert facts["pet_fee"]["refundable"] is False
    assert facts["weight_limit"]["value"] == 50.0
    assert facts["pet_count_limit"] == 2


def test_refundability_is_read_from_the_fee_sentence_and_nowhere_else():
    """A refundable DEPOSIT in the next sentence must not qualify a pet FEE."""
    block = ("Refundable deposit taken at check-in. Pet Charge 50.00 USD "
             "Per Stay. Pets welcome.")
    assert A40._sentence_around(block, "50.00 USD Per Stay").startswith(
        "Pet Charge")
    assert "Refundable deposit" not in A40._sentence_around(
        block, "50.00 USD Per Stay")


def test_brown_deer_states_no_refundability_so_none_is_recorded(records):
    """The source does not say. Silence stays silence."""
    assert "refundable" not in records[BROWN_DEER]["facts"]["pet_fee"]


def test_saint_kate_is_approved_on_the_corrected_reading(records):
    facts = records[SAINT_KATE]["facts"]
    assert facts["pets_allowed"] is True
    assert facts["pet_fee"]["amount_cents"] == 10000
    assert facts["pet_fee"]["basis"] == "per_stay"
    assert facts["pet_count_limit"] == 2
    # Nothing invented that the page never stated.
    assert "weight_limit" not in facts
    assert "species" not in facts


def test_no_service_animal_language_became_a_pet_fact(records):
    for key in (BROWN_DEER, BROOKFIELD, SAINT_KATE):
        assert "service_animal_exception" not in records[key]["facts"]


def test_an_over_captured_service_animal_sentence_was_trimmed(records):
    """039 flagged it; publishing it verbatim would put another fact's words
    into the access statement a guest reads. Only a prefix is removed."""
    statement = records[BROWN_DEER]["service_animal_statement"]
    assert statement["quote"] == "Service animals are permitted, without charge."
    assert any("trimmed to its own sentence" in note for note in
               records[BROWN_DEER]["approval"]["conversion_notes"])


def test_econo_lodge_is_a_verified_no_pets_exclusion(exclusions):
    from scripts.pettripfinder import hotel_exclusions as EX
    row = exclusions[EX.normalize_name("Econo Lodge Milwaukee Airport")]
    assert row["exclusion_state"] == "VERIFIED_NO_PETS"
    assert "Pets Allowed: No" in row["evidence_quote"]
    assert row["reviewer_id"] == D40.FOUNDER
    assert row["market_id"] == C38.MARKET
    assert row["record_hash"] and row["approval_hash"]


def test_the_refusal_did_not_become_a_pet_allowance(records, exclusions):
    assert ECONO not in records
    from scripts.pettripfinder import hotel_exclusions as EX
    row = exclusions[EX.normalize_name("Econo Lodge Milwaukee Airport")]
    assert "only service animals" in row["evidence_context"].lower()


def test_every_new_authority_row_is_bound_under_the_039_contract(records):
    for key in (BROWN_DEER, BROOKFIELD, SAINT_KATE):
        approval = records[key]["approval"]
        assert approval["binding_contract"] == AB.BINDING_CONTRACT_VERSION
        assert approval["semantic_hash"] == approval["reviewed_semantic_hash"]
        assert approval["decision_source"]["ledger"] == D40.LEDGER.name
        assert approval["decision_source"]["work_order"] == D40.WORK_ORDER
        assert approval["operator"] == D40.FOUNDER


def test_the_036_half_of_the_authority_is_unchanged(authority):
    """Two founder sittings, one file, and the older half byte-identical."""
    base = A36.authority_document()["hotels"]
    assert authority["hotels"][:len(base)] == base
    assert len(base) == 70
    sittings = authority["provenance"]["founder_sittings"]
    assert [entry["records"] for entry in sittings] == [70, 3]


# --------------------------------------------------------------------------- #
# The holds.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("key", [KNICKERBOCKER, IRON_HORSE])
def test_a_held_row_is_in_no_authority(key, records, exclusions):
    from scripts.pettripfinder import hotel_exclusions as EX
    assert key not in records
    assert EX.normalize_name(key) not in exclusions


@pytest.mark.parametrize("key", [KNICKERBOCKER, IRON_HORSE])
def test_a_held_row_keeps_its_evidence_and_its_history(key):
    row = next(r for r in C38.active_rows() if r["identity_key"] == key)
    assert row["disposition"] == C38.HELD_REVIEW
    assert row["founder_review_status"].startswith("HOLD_BY_FOUNDER")
    assert row["evidence_status"] == "DECLINED_ON_IDENTITY"
    assert row["lineage"]["attempt_dir"]
    assert "subpage-binding" in row["reason"]


def test_nothing_is_awaiting_a_founder_any_more():
    assert C38.new_candidates() == []


def test_hyatt_regency_is_still_held_without_allowance_evidence(records):
    assert "hyatt regency milwaukee" not in records
    row = next(r for r in C38.active_rows()
               if r["identity_key"] == "hyatt regency milwaukee")
    assert row["disposition"] == C38.HELD_REVIEW
    assert "price" in row["reason"]


# --------------------------------------------------------------------------- #
# Arithmetic.
# --------------------------------------------------------------------------- #

def test_the_authority_counts_derive_to_73_and_27():
    counters = A40.counters()
    assert counters["pet_friendly"] == 73
    assert counters["verified_no_pets"] == 27
    assert counters["total_founder_decided_authority"] == 100
    assert counters["held_from_039"] == 2


def test_the_active_denominator_is_still_133():
    recon = C38.reconciliation()
    assert recon["active_eligible"] == 133
    assert sum(recon["by_disposition"].values()) == 133
    assert recon["problems"] == []


def test_the_census_denominator_is_still_147():
    recon = C38.reconciliation()
    assert recon["census_total"] == 147
    assert recon["non_active_eligible"] == 14


def test_the_expected_movement_and_nothing_else():
    """Three into pet-friendly, one into no-pets, and every other bucket
    exactly where 039 left it."""
    assert C38.reconciliation()["by_disposition"] == {
        "AUTHORITY_PET_FRIENDLY": 73,
        "AUTHORITY_VERIFIED_NO_PETS": 27,
        "HELD_REVIEW": 3,
        "IDENTITY_UNRESOLVED": 2,
        "ACCESS_UNRESOLVED": 4,
        "POLICY_NOT_FOUND": 4,
        "INSUFFICIENT_EVIDENCE": 7,
        "SCHEMA_UNREPRESENTABLE": 12,
        "SOURCE_CONFLICT": 1,
    }


def test_every_active_identity_appears_exactly_once():
    keys = [row["identity_key"] for row in C38.active_rows()]
    assert len(keys) == len(set(keys)) == 133


# --------------------------------------------------------------------------- #
# What 040 must not have done.
# --------------------------------------------------------------------------- #

def test_040_published_nothing_itself(authority):
    """SUCCEEDED by PTF-MILWAUKEE-PUBLICATION-042. 040 decided and stopped;
    what it must never have done is publish, and the package records which
    work order actually did."""
    if authority["published"]:
        assert authority["publication"]["work_order"] != D40.WORK_ORDER
        assert authority["publication"]["deployed"] is False


def test_the_seed_inventory_was_not_touched():
    """Authority is not publication. Admitting a record does not put a row on
    the site, and 040 is authority only."""
    assert not [path for path in files_changed_by_this_work_order()
                if path.endswith("seed_businesses.csv")]


def test_no_other_market_changed():
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


def test_only_milwaukees_shard_was_written():
    changed = files_changed_by_this_work_order()
    shards = [path for path in changed
              if "markets/authority/" in path and path.endswith(
                  "hotel_exclusions.json")]
    assert all("milwaukee-wi" in path for path in shards), shards


def test_the_global_registry_is_generated_not_hand_written():
    """The globals are assembled from the shards by their own builder. A
    market work order writes its shard; anything else is the thing the
    sharding work order forbids."""
    from scripts.pettripfinder import hotel_exclusions as EX
    doc = json.loads(
        (REPO / "launch_packages/pettripfinder/hotel_exclusions.json")
        .read_text(encoding="utf-8-sig"))
    EX.validate(doc)
    shard = json.loads(A40.EXCLUSION_SHARD.read_text(encoding="utf-8-sig"))
    milwaukee = [row for row in doc["exclusions"]
                 if row.get("market_id") == C38.MARKET]
    assert len(milwaukee) == len(shard["exclusions"]) == 27


def test_the_identity_gate_is_unchanged():
    for path in files_changed_by_this_work_order():
        assert "policy_surface.py" not in path, path
        assert "identity_binding" not in path, path
        assert "publication_guard" not in path, path


def test_the_reader_is_unchanged():
    """040 decided; it did not re-read. No reader or locator experimentation."""
    for path in files_changed_by_this_work_order():
        assert "policy_reading.py" not in path, path
        assert "marriott_surface.py" not in path, path
        assert "policy_locator.py" not in path, path


def test_the_schema_is_unchanged():
    from scripts.pettripfinder.contracts import enums
    assert enums.POLICY_SCHEMA_VERSION == "1.2"
    for path in files_changed_by_this_work_order():
        assert "policy_schema.py" not in path, path


def test_the_schema_unrepresentable_rows_were_left_alone():
    rows = [row for row in C38.active_rows()
            if row["disposition"] == C38.SCHEMA_UNREPRESENTABLE]
    assert len(rows) == 12
    for row in rows:
        assert row["authority_status"] == "NONE"


def test_no_provider_was_called():
    """040 records a decision. The candidates' evidence was already on disk."""
    run_dir = REPO / "data" / "acquisition"
    for path in files_changed_by_this_work_order():
        assert "data/acquisition" not in path, path
    assert V39.document()["provider_calls_in_039"] == 0


# --------------------------------------------------------------------------- #
# Saint Kate's reader guards, still standing.
# --------------------------------------------------------------------------- #

def _read(text):
    from scripts.pettripfinder.brightdata import policy_reading as PR
    return PR.to_extraction(PR.parse(text, strategy="test"), location="test")


def test_a_place_restriction_is_not_a_hotel_wide_refusal():
    result = _read("Yes, this is a pet-friendly hotel, with a maximum of two "
                   "pets allowed. Pets are not allowed in the shopping "
                   "galleria.")
    assert result.extraction.get("pets_allowed") is True
    assert "pets_allowed" not in result.withheld


def test_a_refusal_naming_the_guest_room_is_still_a_refusal():
    assert _read("Pets are not allowed in guest rooms.").extraction.get(
        "pets_allowed") is False
    assert _read("Pets are not allowed in the guest rooms or suites."
                 ).extraction.get("pets_allowed") is False


def test_an_unqualified_refusal_is_untouched():
    assert _read("No pets allowed.").extraction.get("pets_allowed") is False

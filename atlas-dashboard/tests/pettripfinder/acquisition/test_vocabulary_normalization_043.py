"""PTF-...-APPROVAL-VOCABULARY-NORMALIZATION-043 -- one spelling, history intact.

The contract already existed; what was missing was a version, a shared
resolver, and a rule about what new code may write. These assert all three,
that the legacy spelling still reads, that nothing was re-hashed to achieve
it, and that the site output did not move by a single byte.
"""

from __future__ import annotations

import copy
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
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder import site_data as SD
from scripts.pettripfinder.acquisition import authority_build_036 as A36
from scripts.pettripfinder.acquisition import closure_038 as C38
from scripts.pettripfinder.acquisition import founder_review_036 as F36
from scripts.pettripfinder.acquisition import publication_042 as P42
from scripts.pettripfinder.acquisition import vocabulary_normalization_043 as V43
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import founder_approval as FA
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash

MARKET = "milwaukee-wi"

#: The bundle PTF-MILWAUKEE-PUBLICATION-042 produced. A vocabulary change that
#: is genuinely internal must not move it.
BUNDLE_042 = "90088e0bfeb8da587943c5102a10ec0448153f5f449a9147517a07e999af75ea"


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
    return json.loads(V43.REPORT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# One canonical value, derived rather than declared.
# --------------------------------------------------------------------------- #

def test_there_is_exactly_one_canonical_approved_value():
    assert FA.CANONICAL_APPROVED == enums.APPROVED_AFTER_CURRENT_REVIEW
    approved_states = [s for s in FA.STATES if s.startswith("APPROVED")]
    assert approved_states == [FA.CANONICAL_APPROVED]


def test_the_contract_is_versioned():
    assert FA.VOCABULARY_VERSION == "founder-approval-vocabulary/1.0"


def test_the_canonical_value_is_the_one_the_repository_already_used():
    """Derived, not preferred. Promoting the shorter spelling would have made
    almost every committed record the exception."""
    spellings: Counter = Counter()
    for path in sorted(F36.PKG.glob("hotel_policy_facts*.json")):
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        spellings.update((r.get("approval") or {}).get("decision")
                         for r in doc.get("hotels") or ())
    assert spellings[FA.CANONICAL_APPROVED] > 300
    assert "APPROVED" not in spellings, \
        "no live approval record may still carry the legacy spelling"


def test_the_states_are_not_collapsed():
    """Six genuinely different things. Only two of them may publish."""
    assert set(FA.STATES) == {
        "APPROVED_AFTER_CURRENT_REVIEW", "LEGACY_BASELINE_REVIEWED",
        "MACHINE_REVIEWED_PENDING_OPERATOR", "HELD_FOR_REVIEW",
        "REJECTED", "SUPERSEDED"}
    assert FA.PUBLISHING_STATES == frozenset(
        {"APPROVED_AFTER_CURRENT_REVIEW", "LEGACY_BASELINE_REVIEWED"})
    for state in ("HELD_FOR_REVIEW", "REJECTED", "SUPERSEDED",
                  "MACHINE_REVIEWED_PENDING_OPERATOR"):
        assert not FA.is_publishable(state), state


def test_a_legacy_baseline_is_not_spelled_as_an_approval_nobody_gave():
    """It publishes, and it is deliberately a different word."""
    assert FA.is_publishable("LEGACY_BASELINE_REVIEWED")
    assert FA.normalize("LEGACY_BASELINE_REVIEWED") == "LEGACY_BASELINE_REVIEWED"
    assert FA.normalize("LEGACY_BASELINE_REVIEWED") != FA.CANONICAL_APPROVED


# --------------------------------------------------------------------------- #
# Legacy reads, canonical writes.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("legacy", sorted(FA.LEGACY_INPUTS))
def test_every_legacy_spelling_still_reads(legacy):
    assert FA.normalize(legacy) == FA.CANONICAL_APPROVED
    assert FA.is_publishable(legacy)


def test_the_036_and_040_spellings_resolve_to_the_same_state():
    assert FA.normalize("APPROVED_AFTER_CURRENT_REVIEW") == \
        FA.normalize("APPROVED") == FA.CANONICAL_APPROVED


def test_a_qualified_legacy_spelling_keeps_what_it_said():
    """Two of them carry information beyond the state; it migrates into a
    caveat rather than being flattened away."""
    assert FA.caveat_for("APPROVED_TIERED_FEE_OMITTED") == "tiered_fee_omitted"
    assert FA.caveat_for("APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT") == \
        "diagnostic_acknowledged"
    assert FA.caveat_for(FA.CANONICAL_APPROVED) == ""


@pytest.mark.parametrize("legacy", sorted(FA.LEGACY_INPUTS))
def test_new_code_may_not_write_a_legacy_spelling(legacy):
    with pytest.raises(FA.ApprovalVocabularyError):
        FA.assert_writable(legacy, where="a new builder")


def test_new_code_may_write_every_canonical_state():
    for state in FA.STATES:
        assert FA.assert_writable(state, where="a new builder") == state


def test_an_unrecognised_approval_is_refused_rather_than_guessed():
    with pytest.raises(FA.ApprovalVocabularyError):
        FA.normalize("APPROVED_PROBABLY")
    assert FA.normalize("APPROVED_PROBABLY", strict=False) == "APPROVED_PROBABLY"


def test_no_module_emits_a_legacy_spelling_as_a_new_approval():
    """The guard that would have caught 040. No exemption list: the five older
    market modules that wrote the legacy spelling were fixed rather than
    excused, because an exemption list is how the next one slips in."""
    assert V43.modules_emitting_a_legacy_spelling() == []


# --------------------------------------------------------------------------- #
# What was normalized, and what was refused.
# --------------------------------------------------------------------------- #

def test_exactly_the_three_040_records_were_normalized(report):
    plan = report["normalized_records"]
    assert len(plan) == 3
    for row in plan:
        assert row["stored_decision"] == "APPROVED"
        assert row["canonical_decision"] == FA.CANONICAL_APPROVED
        assert row["approval_work_order"] == "PTF-MILWAUKEE-FOUNDER-DECISION-040"


def test_a_normalized_record_says_what_it_used_to_say(authority):
    normalized = [r for r in authority["hotels"]
                  if "decision_normalization" in r["approval"]]
    assert len(normalized) == 3
    for record in normalized:
        note = record["approval"]["decision_normalization"]
        assert note["previous_decision"] == "APPROVED"
        assert note["work_order"] == V43.WORK_ORDER
        assert note["vocabulary"] == FA.VOCABULARY_VERSION
        assert record["approval"]["decision"] == FA.CANONICAL_APPROVED


def test_the_founder_decision_ledgers_were_not_touched():
    """A different axis, and history besides. Both sittings already agreed."""
    for name in ("milwaukee_founder_decisions_036.json",
                 "milwaukee_founder_decisions_040.json"):
        doc = json.loads((F36.PKG / name).read_text(encoding="utf-8-sig"))
        assert set(d["decision"] for d in doc["decisions"]) <= {
            "APPROVE", "APPROVE_REFUSAL", "HOLD"}
    changed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout
    assert "founder_decisions_036.json" not in changed
    assert "founder_decisions_040.json" not in changed


def test_superseded_approvals_stay_verbatim():
    """All four registered legacy spellings live in superseded blocks across
    Columbus, Cleveland and Dayton. Those are history and are not rewritten."""
    found: Counter = Counter()
    for path in sorted(F36.PKG.glob("hotel_policy_facts*.json")):
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        for record in doc.get("hotels") or ():
            prior = (record.get("approval") or {}).get("supersedes") or {}
            if prior.get("decision"):
                found[prior["decision"]] += 1
    assert found["APPROVED"] > 0, \
        "the legacy spelling must survive in superseded history"
    for spelling in found:
        assert FA.normalize(spelling) in FA.STATES


# --------------------------------------------------------------------------- #
# Hash safety -- the claim a silent re-hash would hide behind.
# --------------------------------------------------------------------------- #

def test_approval_is_outside_the_semantic_binding():
    assert "approval" not in AB.SEMANTIC_TOP_LEVEL
    assert "approval" not in AB.PROVENANCE_TOP_LEVEL


def test_changing_the_spelling_moves_no_hash(authority):
    record = authority["hotels"][0]
    moved = copy.deepcopy(record)
    moved["approval"]["decision"] = "APPROVED"
    assert record_hash(moved) == record_hash(record)
    assert evidence_hash(moved.get("evidence") or ()) == \
        evidence_hash(record.get("evidence") or ())


def test_no_migration_was_performed(report):
    assert report["hash_safety"]["migration_performed"] is False
    assert report["hash_safety"]["record_hash_excludes_approval"] is True


def test_every_stored_approval_hash_still_verifies(authority):
    for record in authority["hotels"]:
        approval = record["approval"]
        assert approval["record_hash"] == record_hash(record)
        assert approval["evidence_hash"] == evidence_hash(record["evidence"])


def test_the_semantic_binding_still_holds_for_every_decision():
    applicable, refused = A36.bound_decisions()
    assert refused == []
    assert len(applicable) == 97


# --------------------------------------------------------------------------- #
# Nothing else moved.
# --------------------------------------------------------------------------- #

def test_the_authority_is_still_73_and_27(authority):
    assert len(authority["hotels"]) == 73
    assert len(MA.load_market_exclusions(MARKET)) == 27


def test_milwaukee_is_still_published_and_still_not_deployed(authority):
    assert authority["published"] is True
    assert authority["publication"]["deployed"] is False
    assert len(SD.load_published_hotel_policy_facts(MARKET)) == 73
    assert len(MA.load_market_seed_rows(MARKET)) == 73


def test_the_closure_is_unchanged():
    recon = C38.reconciliation()
    assert recon["active_eligible"] == 133
    assert recon["census_total"] == 147
    assert recon["problems"] == []


def test_the_live_contract_still_verifies():
    assert RC.verify_contract(MARKET) == []
    contract = json.loads(P42.LIVE_CONTRACT.read_text(encoding="utf-8"))
    assert contract["policy_package"]["expected_record_count"] == 73
    assert contract["deployment_authorization"]["grants_deployment"] is False


def test_every_other_market_still_verifies_and_is_untouched():
    for market_id in RC.available_market_ids():
        assert RC.verify_contract(market_id) == [], market_id
    doc = json.loads(
        (REPO / "launch_packages/pettripfinder/hotel_exclusions.json")
        .read_text(encoding="utf-8-sig"))
    counts = Counter(row.get("market_id", "") for row in doc["exclusions"])
    assert counts[MARKET] == 27
    assert counts["cleveland-akron-canton-oh"] == 40
    assert counts["columbus-oh"] == 16
    assert counts["dayton-oh"] == 8
    assert counts["indianapolis-in"] == 24  # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: 4 -> 24
    assert counts["pittsburgh-pa"] == 7
    assert MA.check_generated_artifacts() == []


def test_no_other_markets_policy_package_changed():
    changed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout
    for market in ("columbus", "cleveland", "dayton", "indianapolis",
                   "pittsburgh"):
        assert "hotel_policy_facts_%s" % market not in changed, market


def test_the_site_output_did_not_move(report):
    """A vocabulary that reaches no page must not change a page. Byte-identical
    to the bundle 042 built."""
    build = report["build"]
    assert build["bundle_sha256_each"][0] == BUNDLE_042
    assert build["deterministic"] is True
    assert build["total_html_pages"] == 2195
    assert build["sitemap_route_count"] == 428
    assert build["broken_links"] == 0
    assert build["collision_count"] == 0
    assert build["global_shadowing_count"] == 0
    assert build["canonical_violations"] == 0
    assert build["all_gates_pass"] is True
    assert build["deployment_authorized"] is False


def test_the_run_cost_nothing(report):
    assert report["provider_calls"] == 0
    assert report["cost_usd"] == 0.0

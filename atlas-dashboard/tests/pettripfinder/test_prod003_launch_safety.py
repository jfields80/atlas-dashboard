"""PETTRIPFINDER-PROD-003 (Gate 1) -- tests for the offline launch-safety replay.

Proves the deterministic re-derivation under the FROZEN AW-006 authority behaves
correctly and, critically, that runtime worker artifacts can NEVER become
production authority automatically. The core-logic tests are self-contained
(they build synthetic assignments/results, so they pass in a clean clone where
the gitignored v2 runtime data is absent); the replay-over-real-data test skips
gracefully when that data is not present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.pettripfinder.prod003_launch_safety_replay import (
    COMMITTED_LAUNCH_PACKAGE, DEFAULT_PILOT_DIR, classify_record, run,
)
from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.contracts import Assignment, SourceDocument, WorkerResult, content_hash

_URL = "https://official.example/pets"
_MULTI = "Pets are welcome. A pet fee of $50 per night applies, up to a maximum of $150 per stay."
_SINGLE = "Pets are welcome. A pet fee of $50 per night applies."


def _assignment(content: str) -> Assignment:
    doc = SourceDocument(_URL, V.SOURCE_OFFICIAL_PROPERTY, "2026-07-15", "t",
                         content, content_hash(content), V.RETRIEVAL_OK)
    return Assignment("aid-1", "columbus-oh", "test hotel", "Test Hotel", "1 Main St",
                      _URL, (_URL,), (doc,), V.POLICY_FIELDS, "tester")


def _result(status: str, facts, *, contradictions=(), warnings=()) -> WorkerResult:
    pf = [{"field_name": f, "state": V.SUPPORTED, "value": v, "evidence_quote": q,
           "source_url": _URL, "source_type": V.SOURCE_OFFICIAL_PROPERTY, "warnings": []}
          for (f, v, q) in facts]
    return WorkerResult.from_dict({
        "assignment_id": "aid-1", "listing_key": "test hotel", "status": status,
        "selected_source_url": _URL, "selected_source_type": V.SOURCE_OFFICIAL_PROPERTY,
        "evidence_quotes": [q for (_, _, q) in facts], "proposed_facts": pf,
        "unknown_fields": [], "contradictions": list(contradictions),
        "warnings": list(warnings), "provider": "openai",
        "model": "gpt-5.4-nano-2026-03-17", "contract_version": V.CONTRACT_VERSION,
    })


def _classify(assignment: Assignment, result: WorkerResult) -> dict:
    return classify_record(
        assignment, result, extraction_prompt_version="1.4.0",
        extraction_validator_version="1.3.0", verification_date="2026-07-15",
        v2_result_hash="sha256:test", assignment_hash="aid-1")


# --------------------------------------------------------------------------- #
# 1. Frozen backstop demotes a previously-READY multi-amount record.
# --------------------------------------------------------------------------- #

def test_multi_amount_completed_is_demoted_by_frozen_backstop():
    rec = _classify(_assignment(_MULTI), _result(
        V.STATUS_COMPLETED,
        [("pets_allowed", "true", "Pets are welcome"),
         ("pet_fee", "$50", "pet fee of $50 per night")]))
    assert rec["launch_safe"] is False
    assert rec["final_route"] == RT.ROUTE_REVIEW
    assert RT.STRUCTURED_FEE_REQUIRED in rec["reason_codes"]
    assert rec["multi_amount_detected"] is True
    # The misleading scalar pet_fee is never carried on a launch record.
    assert all(f["field_name"] != "pet_fee" for f in rec["supported_facts"])


# --------------------------------------------------------------------------- #
# 2. A genuinely simple single fee stays launch-safe (no regression).
# --------------------------------------------------------------------------- #

def test_simple_single_fee_completed_is_launch_safe():
    rec = _classify(_assignment(_SINGLE), _result(
        V.STATUS_COMPLETED,
        [("pets_allowed", "true", "Pets are welcome"),
         ("pet_fee", "$50", "pet fee of $50 per night")]))
    assert rec["launch_safe"] is True
    assert rec["final_route"] == RT.ROUTE_READY
    assert rec["multi_amount_detected"] is False


# --------------------------------------------------------------------------- #
# 3. A v2 gate is never upgraded; a contradiction is not fee-augmented.
# --------------------------------------------------------------------------- #

def test_contradictory_is_never_upgraded_and_not_fee_augmented():
    rec = _classify(_assignment(_MULTI), _result(
        V.STATUS_CONTRADICTORY,
        [("pets_allowed", "true", "Pets are welcome")],
        contradictions=["pet_fee: $150 vs $50"]))
    assert rec["launch_safe"] is False
    # _decide short-circuits a contradiction to CONTRADICTORY_OFFICIAL_SOURCES only.
    assert rec["reason_codes"] == [RT.CONTRADICTORY_OFFICIAL_SOURCES]


# --------------------------------------------------------------------------- #
# 4. A NEEDS_REVIEW record with multi-amount evidence is backstop-augmented.
# --------------------------------------------------------------------------- #

def test_needs_review_multi_amount_is_backstop_augmented():
    rec = _classify(_assignment(_MULTI), _result(
        V.STATUS_NEEDS_REVIEW,
        [("pets_allowed", "true", "Pets are welcome")],
        warnings=["rejected_refundable_deposit:number_not_in_quote"]))
    assert rec["launch_safe"] is False
    assert RT.STRUCTURED_FEE_REQUIRED in rec["reason_codes"]
    assert RT.INCOMPLETE_EXTRACTION in rec["reason_codes"]


# --------------------------------------------------------------------------- #
# 5. Runtime artifacts can never become production authority automatically:
#    no production/site-generation module reads the worker runtime tree.
# --------------------------------------------------------------------------- #

_PRODUCTION_MODULES = (
    "scripts/generate_pettripfinder_columbus_site.py",
    "scripts/pettripfinder/site_data.py",
    "scripts/pettripfinder/export_hotel_policy_facts.py",
    "scripts/pettripfinder/hotel_profile_page.py",
    "scripts/pettripfinder/hotel_profile.py",
    "scripts/pettripfinder/site_pages.py",
    "scripts/pettripfinder/site_enrichment.py",
    "scripts/pettripfinder/listing_dataset_builder.py",
    "scripts/pettripfinder/structured_data.py",
    "scripts/pettripfinder/media_ingestion.py",
)


def test_no_production_module_reads_worker_runs():
    root = Path(__file__).resolve().parents[2]
    for rel in _PRODUCTION_MODULES:
        path = root / rel
        if not path.exists():
            continue
        assert "worker_runs" not in path.read_text(encoding="utf-8"), (
            "%s references the gitignored worker runtime tree; runtime artifacts "
            "must never become production authority automatically" % rel)


# --------------------------------------------------------------------------- #
# 6. The replay writes ONLY to its review dir, leaves the committed launch
#    package byte-identical, and is deterministic (skips without the v2 data).
# --------------------------------------------------------------------------- #

def test_replay_writes_only_to_review_dir_and_leaves_authority_untouched(tmp_path):
    if not (DEFAULT_PILOT_DIR / "validated_results").exists():
        pytest.skip("v2 runtime artifacts absent (gitignored); real-data replay skipped")
    before = COMMITTED_LAUNCH_PACKAGE.read_bytes() if COMMITTED_LAUNCH_PACKAGE.exists() else None

    out = tmp_path / "review"
    manifest = run(DEFAULT_PILOT_DIR, out)

    after = COMMITTED_LAUNCH_PACKAGE.read_bytes() if COMMITTED_LAUNCH_PACKAGE.exists() else None
    assert before == after                                   # production authority untouched
    for name in ("launch_safe_manifest.json", "review_packet.md", "exclusion_report.json"):
        assert (out / name).exists()
    counts = manifest["counts"]
    assert counts["launch_safe"] + counts["manual_review"] == counts["total"]
    assert manifest["auto_import"] is False and manifest["non_production"] is True

    # Deterministic: a second run into a fresh dir yields byte-identical output.
    out2 = tmp_path / "review2"
    run(DEFAULT_PILOT_DIR, out2)
    assert (out / "launch_safe_manifest.json").read_bytes() == (out2 / "launch_safe_manifest.json").read_bytes()


def test_real_pilot_split_is_fifteen_launch_safe(tmp_path):
    if not (DEFAULT_PILOT_DIR / "validated_results").exists():
        pytest.skip("v2 runtime artifacts absent (gitignored); real-data replay skipped")
    manifest = run(DEFAULT_PILOT_DIR, tmp_path / "review")
    # The two Red Roof recurring-fee-plus-cap records are demoted from the
    # historical 17 v2 READY by the frozen AW-006 backstop.
    assert manifest["counts"] == {"total": 25, "launch_safe": 15, "manual_review": 10}

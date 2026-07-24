"""PETTRIPFINDER-PROD-003 Gate 2 (Stage G) -- schema-1.1 exporter + package preview.

Proves the additive schema-1.0 -> 1.1 upgrade and the zero-write 14-record
preview: the nine worker records gain provenance + verbatim evidence + approval
metadata, the five importer records keep their schema-1.0 fields untouched, the
committed package is never written, and output is deterministic. Data-dependent
checks skip when the gitignored operational promotion corpus is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import export_hotel_policy_facts as EX
from scripts.pettripfinder import prod003_approvals as PA
from scripts.pettripfinder import site_data as SD

_REPO = Path(SD.__file__).resolve().parents[2]
_COMMITTED = _REPO / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"
_APPROVALS = _REPO / "launch_packages" / "pettripfinder" / "hotel_worker_approvals.json"

_NINE = {
    "drury inn and suites columbus dublin", "drury inn and suites columbus polaris",
    "hampton inn columbus dublin", "home2 suites by hilton columbus dublin",
    "homewood suites by hilton columbus dublin", "hyatt place columbus osu",
    "hyatt regency columbus", "the westin great southern columbus",
    "towneplace suites columbus dublin",
}
_SCHEMA_1_1_FIELDS = ("verification_date", "worker_result_hash", "worker_model_id",
                      "worker_prompt_version", "worker_validator_version",
                      "worker_routing_version", "evidence", "approval")


def _corpus_ready() -> bool:
    facts = SD.load_hotel_policy_facts()
    worker = {k for k, v in facts.items() if str(v.get("candidate_id", "")).startswith("worker-promotion-")}
    return worker == _NINE


def _skip_unless_ready():
    if not _corpus_ready():
        pytest.skip("operational promotion corpus absent (gitignored); package preview skipped")


# --------------------------------------------------------------------------- #
# Schema version (data-independent).
# --------------------------------------------------------------------------- #

def test_schema_version_is_1_1():
    assert EX.SCHEMA_VERSION == "1.1"
    assert EX.build_package()["schema_version"] == "1.1"


# --------------------------------------------------------------------------- #
# Projection: 14 records, 9 additions, 5 preserved.
# --------------------------------------------------------------------------- #

def test_preview_projects_fourteen_with_nine_additions():
    _skip_unless_ready()
    r = EX.build_preview()["report"]
    assert r["old_count"] == 5 and r["new_count"] == 14
    assert r["additions_count"] == 9 and r["removals_count"] == 0
    assert set(r["additions"]) == _NINE
    assert r["committed_would_become_stale"] is True
    assert r["wrote_committed_package"] is False


def test_five_existing_records_preserved_unchanged():
    _skip_unless_ready()
    committed = {h["key"]: h for h in json.loads(_COMMITTED.read_text(encoding="utf-8"))["hotels"]}
    new = {h["key"]: h for h in EX.build_package()["hotels"]}
    for k, rec in committed.items():
        assert new[k] == rec                         # byte-for-byte preserved, no worker fields
    assert EX.build_preview()["report"]["unintended_updates_count"] == 0


def test_drury_plaza_excluded_from_package():
    _skip_unless_ready()
    keys = {h["key"] for h in EX.build_package()["hotels"]}
    assert "drury plaza hotel columbus downtown" not in keys


# --------------------------------------------------------------------------- #
# Provenance / evidence / approval preserved exactly (worker records).
# --------------------------------------------------------------------------- #

def _worker_records():
    return {h["key"]: h for h in EX.build_package()["hotels"] if "worker_result_hash" in h}


def test_worker_provenance_matches_approval_manifest():
    _skip_unless_ready()
    approvals = {a["listing_key"]: a for a in json.loads(_APPROVALS.read_text(encoding="utf-8"))["approvals"]}
    for key, h in _worker_records().items():
        a = approvals[key]
        assert h["worker_result_hash"] == a["result_hash"]         # exact hash
        assert h["worker_model_id"] == "gpt-5.4-nano-2026-03-17"
        assert h["worker_prompt_version"] == "1.4.0"
        assert h["worker_validator_version"] == "1.5.0"
        assert h["worker_routing_version"] == "1.2.0"
        assert h["approval"] == {"decision": "APPROVED_FOR_PROMOTION",
                                 "operator": "Jonathan Fields", "approval_date": "2026-07-23"}
        assert h["verification_date"] == "2026-07-15"


def test_worker_evidence_is_verbatim_from_the_corpus_candidate():
    _skip_unless_ready()
    for key, h in _worker_records().items():
        cand_id = SD.load_hotel_policy_facts()[key]["candidate_id"]
        cand = json.loads((SD.WORKER_PROMOTION_ROOT / "candidates" / (cand_id + ".json")).read_text(encoding="utf-8"))
        assert h["evidence"] == cand["evidence"]                   # verbatim, unchanged
        for ev in h["evidence"]:
            assert set(ev) == {"field", "value", "quote", "source_url"}


def test_importer_records_have_no_worker_fields():
    _skip_unless_ready()
    worker_keys = _NINE
    for h in EX.build_package()["hotels"]:
        if h["key"] in worker_keys:
            continue
        for f in _SCHEMA_1_1_FIELDS:
            assert f not in h                         # no fabricated worker provenance on importer rows


# --------------------------------------------------------------------------- #
# Safety: no tiered fee, no credentials, deterministic, backward-compatible.
# --------------------------------------------------------------------------- #

def test_no_tiered_or_structured_fee_record_included():
    _skip_unless_ready()
    for h in EX.build_package()["hotels"]:
        assert "fee_terms" not in h and "fee_policy" not in h
        assert "fee_terms" not in h["facts"]          # scalar facts only; never a flattened tier


def test_preview_contains_no_credentials():
    _skip_unless_ready()
    blob = json.dumps(EX.build_package()).lower()
    for secret in ("sk-", "api_key", "apikey", "bearer ", "password", "authorization"):
        assert secret not in blob


def test_package_output_is_deterministic():
    _skip_unless_ready()
    assert EX.serialize(EX.build_package()) == EX.serialize(EX.build_package())


def test_new_package_is_backward_compatible_for_readers():
    _skip_unless_ready()
    # Every record (incl. schema-1.1 worker records) still carries the exact keys
    # the committed-package reader consumes; unknown additive keys are ignored.
    reader_keys = {"key", "facts", "verified_at", "evidence_count", "source_type",
                   "source_url", "evidence_quote"}
    for h in EX.build_package()["hotels"]:
        assert reader_keys <= set(h)
    assert len(SD.load_published_hotel_policy_facts()) == 5        # committed file still reads 5


# --------------------------------------------------------------------------- #
# Zero committed-package write.
# --------------------------------------------------------------------------- #

def test_preview_writes_only_to_review_dir(tmp_path):
    _skip_unless_ready()
    committed_before = _COMMITTED.read_bytes()
    out = tmp_path / "preview"
    report = EX.write_preview(out)
    assert _COMMITTED.read_bytes() == committed_before             # committed package untouched
    assert sorted(p.name for p in out.iterdir()) == [
        "hotel_policy_facts.preview.json", "package_diff.md", "package_validation_report.json"]
    assert report["new_count"] == 14 and report["wrote_committed_package"] is False
    # deterministic: a second preview into a fresh dir is byte-identical
    out2 = tmp_path / "preview2"
    EX.write_preview(out2)
    assert ((out / "hotel_policy_facts.preview.json").read_bytes()
            == (out2 / "hotel_policy_facts.preview.json").read_bytes())

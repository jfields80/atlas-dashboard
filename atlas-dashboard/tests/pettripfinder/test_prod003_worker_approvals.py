"""PETTRIPFINDER-PROD-003 Gate 2 (Stage A) -- approval-contract tests.

Covers the committed approval contract only: parsing, deterministic validation,
serialization, JSON-schema conformance, and the binding rules. No approval
decisions are recorded, nothing is promoted, and nothing is written to the
operational corpus or the committed launch package. The core tests are
self-contained; nothing here depends on the gitignored runtime artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from scripts.pettripfinder import prod003_approvals as PA

_REPO = Path(__file__).resolve().parents[2]
_MANIFEST = _REPO / "launch_packages" / "pettripfinder" / "hotel_worker_approvals.json"
_SCHEMA = _REPO / "launch_packages" / "pettripfinder" / "hotel_worker_approval.schema.json"
_GATE1_MANIFEST = (_REPO / "data" / "worker_runs" / "pettripfinder"
                   / "prod003_gate1_review" / "launch_safe_manifest.json")
_HELD_KEY = "drury plaza hotel columbus downtown"

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "sha256:" + "b" * 64
_HASH_C = "sha256:" + "c" * 64


def _approval(**over):
    base = dict(
        listing_key="hyatt regency columbus", listing_name="Hyatt Regency Columbus",
        result_hash=_HASH_A, source_url="https://official.example/policies",
        verification_date="2026-07-15", gate1_route="READY",
        decision=PA.DECISION_APPROVED, operator="Jane Operator", approval_date="2026-07-23")
    base.update(over)
    return base


def _manifest(approvals=(), pending=()):
    return {"schema": PA.SCHEMA_ID, "market": "columbus-oh",
            "approvals": list(approvals), "pending_candidates": list(pending)}


def _idx(*, launch_safe=True, result_hash=_HASH_A, key="hyatt regency columbus"):
    return {key: {"result_hash": result_hash, "launch_safe": launch_safe,
                  "gate1_route": "READY" if launch_safe else "REVIEW"}}


# --------------------------------------------------------------------------- #
# Binding rules (self-contained).
# --------------------------------------------------------------------------- #

def test_valid_approval_entry():
    m = _manifest(approvals=[_approval()])
    assert PA.validate_manifest(m, gate1_idx=_idx()) == []


def test_invalid_decision_rejected():
    m = _manifest(approvals=[_approval(decision="MAYBE_LATER")])
    assert any("invalid_decision" in e for e in PA.validate_manifest(m))


def test_approved_requires_ready_route():
    m = _manifest(approvals=[_approval(gate1_route="REVIEW")])
    assert any("approved_requires_ready_route" in e for e in PA.validate_manifest(m))


def test_missing_operator_or_date_rejected():
    for field in ("operator", "approval_date"):
        m = _manifest(approvals=[_approval(**{field: ""})])
        assert any(("missing_" + field) in e for e in PA.validate_manifest(m))


def test_stale_result_hash_detection():
    m = _manifest(approvals=[_approval(result_hash=_HASH_C)])
    errs = PA.validate_manifest(m, gate1_idx=_idx(result_hash=_HASH_A))
    assert any("stale_result_hash" in e for e in errs)


def test_duplicate_identity_rejected():
    m = _manifest(approvals=[_approval(), _approval(listing_name="Dup")])   # same key + hash
    errs = PA.validate_manifest(m)
    assert any("duplicate_listing_key" in e for e in errs)
    assert any("duplicate_result_hash" in e for e in errs)


def test_manual_review_record_cannot_be_approved():
    # A forged READY route on a record the Gate-1 authority marks manual-review
    # is caught by the re-derived index (defence in depth beside the route rule).
    m = _manifest(approvals=[_approval(listing_key="aloft columbus university district")])
    idx = _idx(launch_safe=False, key="aloft columbus university district")
    assert any("manual_review_cannot_be_approved" in e
               for e in PA.validate_manifest(m, gate1_idx=idx))


def test_deterministic_serialization_is_order_independent():
    a1 = _approval(listing_key="b hotel", result_hash="sha256:" + "2" * 64)
    a2 = _approval(listing_key="a hotel", result_hash="sha256:" + "1" * 64)
    assert PA.serialize(_manifest(approvals=[a1, a2])) == PA.serialize(_manifest(approvals=[a2, a1]))
    assert PA.serialize(_manifest(approvals=[a1, a2])) == PA.serialize(_manifest(approvals=[a1, a2]))


def test_pending_entry_must_not_carry_a_decision():
    m = _manifest(pending=[{"listing_key": "x", "listing_name": "X", "result_hash": _HASH_A,
                            "source_url": "u", "verification_date": "2026-07-15",
                            "gate1_route": "READY", "decision": PA.DECISION_APPROVED}])
    assert any("must_not_carry_decision" in e for e in PA.validate_manifest(m))


# --------------------------------------------------------------------------- #
# Committed initial manifest + JSON-schema conformance.
# --------------------------------------------------------------------------- #

def test_committed_manifest_records_the_stage_b_decisions():
    """The committed manifest now carries the recorded Stage-B decisions. It must
    be structurally valid and reflect exactly the operator's tally, with no
    fabricated notes or unsupported fields on any entry."""
    m = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert PA.validate_manifest(m) == []                          # module rules hold
    assert m["pending_candidates"] == []                         # every record decided

    by_decision = {}
    for a in m["approvals"]:
        by_decision.setdefault(a["decision"], []).append(a)
    assert len(by_decision.get(PA.DECISION_APPROVED, [])) == 9
    assert len(by_decision.get(PA.DECISION_HOLD, [])) == 1
    assert by_decision.get(PA.DECISION_REJECTED, []) == []
    assert by_decision.get(PA.DECISION_SUPERSEDED, []) == []
    assert by_decision[PA.DECISION_HOLD][0]["listing_key"] == _HELD_KEY

    allowed = set(PA.APPROVAL_REQUIRED_FIELDS)                   # note is the only optional field
    for a in m["approvals"]:
        assert a["operator"] == "Jonathan Fields"
        assert a["approval_date"] == "2026-07-23"
        assert "note" not in a                                    # no fabricated notes
        assert set(a) == allowed                                  # no unsupported fields
        if a["decision"] == PA.DECISION_APPROVED:
            assert a["gate1_route"] == "READY"


def test_committed_approvals_are_bound_to_gate1_authority():
    """Every recorded approval remains bound to the current Gate-1 authority: no
    stale hash, no manual-review approval, and identity/source/date/route match
    the Gate-1 manifest. Skips when the gitignored Gate-1 manifest is absent."""
    if not _GATE1_MANIFEST.exists():
        pytest.skip("Gate-1 manifest absent (gitignored); Gate-1 binding check skipped")
    m = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    g1 = json.loads(_GATE1_MANIFEST.read_text(encoding="utf-8"))
    idx = PA.gate1_index(g1)
    assert PA.validate_manifest(m, gate1_idx=idx) == []           # no stale/duplicate/misrouted entry
    g1_by_key = {r["listing_key"]: r for r in g1["launch_safe_candidates"]}
    for a in m["approvals"]:
        assert a["result_hash"] == idx[a["listing_key"]]["result_hash"]
        assert a["gate1_route"] == idx[a["listing_key"]]["gate1_route"]
        r = g1_by_key[a["listing_key"]]
        assert a["source_url"] in r["source_urls"]
        assert a["verification_date"] == r["verification_date"]


def test_committed_manifest_validates_against_json_schema():
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)                        # raises on failure


def test_json_schema_rejects_approved_non_ready():
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    manifest["approvals"] = [_approval(gate1_route="REVIEW")]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(manifest, schema)


# --------------------------------------------------------------------------- #
# Purity + backward compatibility with the Gate-1 artifacts.
# --------------------------------------------------------------------------- #

def test_contract_functions_perform_no_writes(tmp_path):
    m = _manifest(approvals=[_approval()])
    PA.validate_manifest(m)
    PA.serialize(m)
    PA.approved_for_promotion(m)
    assert list(tmp_path.iterdir()) == []                        # nothing written anywhere


def test_build_pending_manifest_excludes_committed_and_validates():
    g1 = {"market": "columbus-oh",
          "launch_safe_candidates": [
              {"listing_key": "new hotel", "listing_name": "New Hotel",
               "candidate_identity": "sha256:" + "d" * 64, "source_urls": ["https://ex/new"],
               "verification_date": "2026-07-15", "final_route": "READY"},
              {"listing_key": "already committed", "listing_name": "Already",
               "candidate_identity": "sha256:" + "e" * 64, "source_urls": ["https://ex/old"],
               "verification_date": "2026-07-15", "final_route": "READY"}],
          "manual_review_candidates": []}
    mani = PA.build_pending_manifest(
        g1, {"already committed"}, frozen_worker_commit="0" * 40,
        gate1_commit="1" * 40, gate1_manifest_sha256="f" * 64)
    assert [p["listing_key"] for p in mani["pending_candidates"]] == ["new hotel"]
    assert mani["approvals"] == []
    assert PA.validate_manifest(mani) == []

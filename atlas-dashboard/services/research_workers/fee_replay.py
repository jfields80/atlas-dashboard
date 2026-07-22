"""ATLAS-WORKERS-006 -- zero-network offline replay of the tiered-fee V2 records.

Reinterprets ONLY persisted V2 candidate-export data under the new structured-fee
lens. It never calls a model, never invents a raw claim, and never overwrites the
V1 or V2 baselines -- any persisted replay report is written to a SEPARATE
gitignored directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Sequence

# Deterministic classifications of a stored V2 record under the AW-006 contract.
REPLAY_RECOVERABLE = "RECOVERABLE_FROM_STORED_DATA"
REPLAY_NEEDS_NEW_MODEL = "REQUIRES_NEW_MODEL_RESPONSE"
REPLAY_GENUINE_CONTRADICTION = "GENUINE_CONTRADICTION"
REPLAY_RESEARCH_COMPLETE_DOWNSTREAM = "RESEARCH_COMPLETE_DOWNSTREAM_UNSUPPORTED"

# The five tiered/conditional-fee hotels identified by the AW-005 v2 pilot.
TIERED_FEE_HOTELS = (
    "Aloft Columbus University District",
    "Extended Stay America Suites Columbus Dublin",
    "Hyatt House Columbus OSU Short North",
    "Sonesta Simply Suites Dublin Columbus",
    "Staybridge Suites Columbus Dublin",
)


def _index(export: Dict) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for bucket in ("ready_candidates", "review_candidates", "retry_candidates", "rejected_candidates"):
        for h in export.get(bucket, []):
            out[h["listing_name"]] = h
    return out


def classify_record(rec: Dict) -> str:
    """Deterministic classification from stored data alone."""
    if rec.get("fee_policy"):
        return REPLAY_RESEARCH_COMPLETE_DOWNSTREAM          # already carries structured terms
    fee_contra = [c for c in rec.get("contradictions", []) if c.startswith("pet_fee")]
    if fee_contra:
        # A pet_fee contradiction with NO stored structured terms: the V2 run
        # predates the fee_terms contract, so the model never emitted (and the
        # store never captured) the raw terms. Reinterpretation from stored data
        # alone is impossible -- a fresh model response under the new prompt is
        # required. No raw claim is invented.
        return REPLAY_NEEDS_NEW_MODEL
    return REPLAY_RECOVERABLE


def replay_tiered_fee_records(v2_candidate_export_path: str,
                              hotels: Sequence[str] = TIERED_FEE_HOTELS) -> Dict:
    """Read the persisted V2 candidate export and classify each tiered-fee hotel.
    Pure file read -- performs zero network calls and writes nothing."""
    export = json.loads(Path(v2_candidate_export_path).read_text(encoding="utf-8"))
    idx = _index(export)
    records = []
    for name in hotels:
        rec = idx.get(name)
        if rec is None:
            records.append({"hotel": name, "classification": "NOT_FOUND"})
            continue
        records.append({
            "hotel": name, "classification": classify_record(rec),
            "v2_route": rec.get("route"), "v2_reason_codes": rec.get("reason_codes", []),
            "pet_fee_contradictions": [c for c in rec.get("contradictions", []) if c.startswith("pet_fee")],
            "has_stored_fee_policy": bool(rec.get("fee_policy")),
        })
    counts: Dict[str, int] = {}
    for r in records:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    return {"replay_kind": "aw006_tiered_fee_offline_replay", "network_calls": 0,
            "records": records, "counts": dict(sorted(counts.items()))}

"""AES-DATA-001 -- CLI: operator approval for an import candidate.

    python scripts/approve_import_candidate.py \\
      --candidate data/import/candidates/<candidate>.json \\
      --decision approve

Decisions: approve | reject | approve-with-edits. Approval re-runs
deterministic validation, refuses when unsupported material claims remain,
never calls the LLM again, and exports approved candidates to the staging
CSV only (never the tracked production seed CSV).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import (
    apply_operator_edits,
    dumps_candidate,
    has_unsupported_published_claim,
    load_candidate,
    persist_candidate,
)
from scripts.pettripfinder.importer.csv_export import export_to_staging
from scripts.pettripfinder.importer.models import CandidateListing
from scripts.pettripfinder.importer.rejection_log import append_rejection


def approve_candidate(
    candidate_path,
    decision: str,
    *,
    output_root: str,
    edits: Optional[Dict[str, str]] = None,
    operator_reason: str = "",
    decided_at: str,
) -> Dict[str, object]:
    """Apply an operator decision. Returns a result dict with the outcome.
    Pure of network/LLM; deterministic given the same candidate + inputs."""
    root = Path(output_root)
    candidate = load_candidate(candidate_path)
    candidates_dir = Path(candidate_path).parent

    # Item 11/25 guard: a candidate already finalized (rejected, exported, or
    # promoted) is never re-decided -- prevents stale re-approval and a
    # rejected candidate ever becoming promotable.
    _TERMINAL = (C.REVIEW_REJECTED, C.REVIEW_EXPORTED_TO_STAGING, C.REVIEW_PROMOTED)
    if candidate.review_status in _TERMINAL:
        return {"ok": False, "reason": "already_finalized",
                "review_status": candidate.review_status}

    if decision == "reject":
        updated = replace(candidate, review_status=C.REVIEW_REJECTED,
                          approval_metadata=candidate.approval_metadata
                          + (("decided_at", decided_at), ("decision", "reject")))
        persist_candidate(updated, candidates_dir)
        append_rejection(updated, root / C.REJECTIONS_NAME,
                         operator_reason=operator_reason)
        return {"ok": True, "decision": "reject", "review_status": updated.review_status}

    # Rejected-recommendation candidates are never promotable/approvable.
    if candidate.recommendation == C.RECOMMEND_REJECT:
        return {"ok": False, "reason": "candidate_recommendation_is_reject",
                "review_status": candidate.review_status}

    diffs = ()
    if decision == "approve-with-edits":
        candidate, diffs = apply_operator_edits(
            candidate, dict(edits or {}), decided_at=decided_at)
        status = C.REVIEW_EDITED_AND_APPROVED
    elif decision == "approve":
        status = C.REVIEW_APPROVED
    else:
        return {"ok": False, "reason": "unknown_decision"}

    # Refuse approval when unsupported material claims remain.
    if has_unsupported_published_claim(candidate):
        return {"ok": False, "reason": "unsupported_material_claim_remains"}
    if candidate.missing_required:
        return {"ok": False, "reason": C.REASON_MISSING_REQUIRED_FIELD,
                "missing": list(candidate.missing_required)}

    approved = replace(candidate, review_status=status,
                       approval_metadata=candidate.approval_metadata
                       + (("decided_at", decided_at), ("decision", decision)))

    ok, reason, row = export_to_staging(approved, root, exported_at=decided_at)
    if not ok:
        persist_candidate(approved, candidates_dir)
        return {"ok": False, "reason": reason, "review_status": approved.review_status}

    staged = replace(approved, review_status=C.REVIEW_EXPORTED_TO_STAGING)
    persist_candidate(staged, candidates_dir)
    return {"ok": True, "decision": decision, "review_status": staged.review_status,
            "staged_row": row, "edits": list(diffs)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Approve/reject an import candidate.")
    p.add_argument("--candidate", required=True)
    p.add_argument("--decision", required=True,
                   choices=("approve", "reject", "approve-with-edits"))
    p.add_argument("--edited-candidate", default="",
                   help="Path to an edited candidate JSON (approve-with-edits).")
    p.add_argument("--set", action="append", default=[],
                   help="field=value override (approve-with-edits); repeatable.")
    p.add_argument("--operator-reason", default="")
    p.add_argument("--output-root", default=C.DEFAULT_OUTPUT_ROOT)
    args = p.parse_args(argv)

    edits: Dict[str, str] = {}
    if args.edited_candidate:
        edited = json.loads(Path(args.edited_candidate).read_text(encoding="utf-8"))
        edits = dict(edited.get("proposed_fields", []))
    for item in args.set:
        if "=" in item:
            k, v = item.split("=", 1)
            edits[k.strip()] = v.strip()

    result = approve_candidate(
        args.candidate, args.decision, output_root=args.output_root,
        edits=edits, operator_reason=args.operator_reason,
        decided_at=datetime.now().isoformat(timespec="seconds"))
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

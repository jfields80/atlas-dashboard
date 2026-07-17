"""AES-DATA-001 importer -- deterministic staging-CSV export (mission
sections 21/23). Approved candidates append to a gitignored staging CSV
using the exact 15-column seed schema. An audit sidecar (outside the
production schema) preserves the candidate->row link and enables duplicate
detection. Production ``seed_businesses.csv`` is never touched here.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import CandidateListing


def candidate_to_csv_row(c: CandidateListing) -> Dict[str, str]:
    """The candidate's 15-column production row (deterministic)."""
    proposed = dict(c.proposed_fields)
    return {col: proposed.get(col, "") for col in C.SEED_CSV_COLUMNS}


def _row_identity(row: Dict[str, str]) -> str:
    return "|".join([
        (row.get("name") or "").strip().lower(),
        (row.get("city") or "").strip().lower(),
        (row.get("state") or "").strip().lower(),
    ])


def _read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _read_audit(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _write_all_rows(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(C.SEED_CSV_COLUMNS),
                                lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in C.SEED_CSV_COLUMNS})


def export_to_staging(
    c: CandidateListing, staging_dir, *, exported_at: str,
) -> Tuple[bool, str, Optional[Dict[str, str]]]:
    """Append an approved candidate's row to the staging CSV. Returns
    ``(ok, reason, row)``. Refuses non-approved candidates and duplicates."""
    if c.review_status not in C.APPROVED_REVIEW_STATES:
        return (False, "not_approved", None)

    staging_dir = Path(staging_dir)
    csv_path = staging_dir / C.STAGING_CSV_NAME
    audit_path = staging_dir / C.STAGING_AUDIT_NAME

    audit = _read_audit(audit_path)
    if any(a.get("candidate_id") == c.candidate_id for a in audit):
        return (False, C.REASON_DUPLICATE_CANDIDATE, None)

    row = candidate_to_csv_row(c)
    existing = _read_rows(csv_path)
    identity = _row_identity(row)
    if any(_row_identity(r) == identity for r in existing):
        return (False, C.REASON_DUPLICATE_INVENTORY_ROW, None)

    existing.append(row)
    _write_all_rows(csv_path, existing)

    row_hash = hashlib.sha256(
        json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    audit_record = {
        "candidate_id": c.candidate_id, "row_hash": row_hash,
        "exported_at": exported_at, "name": row["name"],
        "city": row["city"], "state": row["state"],
        "source_url": row["source_url"], "review_status": c.review_status,
    }
    staging_dir.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(audit_record, sort_keys=True, ensure_ascii=False) + "\n")
    return (True, "", row)

"""AES-DATA-001 importer -- append-only rejection history (mission section
24). Smallest useful record; gitignored JSONL. No CRM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from scripts.pettripfinder.importer.models import CandidateListing


def append_rejection(
    c: CandidateListing, path, *, operator_reason: str = "",
) -> None:
    """Append one deterministic JSONL rejection record."""
    proposed = dict(c.proposed_fields)
    record = {
        "requested_url": c.snapshot.requested_url,
        "final_url": c.snapshot.final_url,
        "candidate_id": c.candidate_id,
        "entity_name": proposed.get("name", ""),
        "reason_slug": (c.recommendation_reasons[0] if c.recommendation_reasons else ""),
        "observed_at": c.snapshot.observed_at,
        "snapshot_hash": c.snapshot.raw_content_hash,
        "operator_reason": operator_reason,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

"""
atlas/core/input_hash.py

Deterministic input fingerprinting for pipeline run idempotency.

The input_hash is computed over:
  (opportunity_id, portfolio_snapshot_id, EngineVersionSet fingerprint)

Same hash = same logical run.  The Pipeline Runner uses this to
detect duplicate submissions and skip or return the existing result
rather than creating a duplicate ledger entry.
"""

from __future__ import annotations

import hashlib
import json

from core.engine_versions import EngineVersionSet


def compute_input_hash(
    opportunity_id: str,
    portfolio_snapshot_id: str,
    version_set: EngineVersionSet,
) -> str:
    """
    Returns a 64-character hex SHA-256 hash uniquely identifying this
    combination of inputs + engine versions.

    Deterministic: identical arguments always produce the identical hash.
    """
    payload = json.dumps(
        {
            "opportunity_id": opportunity_id,
            "portfolio_snapshot_id": portfolio_snapshot_id,
            "engine_versions": version_set.as_dict(),
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()

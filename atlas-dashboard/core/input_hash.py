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


def _stable_json_default(obj: object) -> object:
    """
    Fallback serializer for ``compute_pipeline_input_hash``'s seed
    payload, which may legitimately contain non-JSON-native values
    (Pydantic models, dataclasses, a live ``sqlite3.Connection``, etc.)

    Must be deterministic given the same *logical* value, since its
    output feeds directly into an idempotency hash — unlike a generic
    "don't crash" fallback, ``str(obj)`` is not safe here: many objects
    (e.g. ``sqlite3.Connection``) include a memory address in their
    default ``repr``/``str``, which would make the hash — and therefore
    idempotency — non-deterministic across otherwise-identical calls.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "_asdict"):
        return obj._asdict()
    if hasattr(obj, "__dict__"):
        return vars(obj)
    # No stable field-level representation available (e.g. a live
    # connection or other opaque handle) — the object's identity is an
    # execution-context detail, not part of the pipeline's logical
    # input, so only its type name is hashed.
    return type(obj).__name__


def compute_pipeline_input_hash(
    pipeline_name: str,
    pipeline_version: str,
    seed_payload: dict,
    version_set: EngineVersionSet,
) -> str:
    """
    Returns a 64-character hex SHA-256 hash uniquely identifying this
    combination of pipeline identity + seed payload + engine versions.

    Generalizes ``compute_input_hash`` for the Atlas Orchestrator
    (AES-006). Unlike ``compute_input_hash``, ``seed_payload`` is not
    guaranteed to be a plain JSON-native dict — it may carry Pydantic
    models, dataclasses, or a live connection object — so
    ``_stable_json_default`` is used as a deterministic fallback.
    Deterministic: identical arguments always produce the identical
    hash.
    """
    payload = json.dumps(
        {
            "pipeline_name": pipeline_name,
            "pipeline_version": pipeline_version,
            "seed_payload": seed_payload,
            "engine_versions": version_set.as_dict(),
        },
        default=_stable_json_default,
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()

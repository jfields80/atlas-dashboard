"""Build-state repository for the WGE (AES-WEB-001 §9.2).

SQLite persistence only: builds, append-only transition history,
checkpoints, escalations, and the overrides table foundation. Typed
persistence methods returning plain dicts (the established Atlas
repository convention — see ``repositories/orchestrator_run_repository``).

Boundaries (per Atlas architecture contract and Sprint 1 directive):

* no orchestration logic;
* no retries inside the repository;
* no state-transition decisions — the pure state machine owns the law,
  the (future) service shell applies it and is the sole writer;
* no clock reads — every timestamp enters as an explicit parameter so
  callers stay deterministic in tests and replay;
* deterministic serialization of stored hash/version collections
  (canonical sorted-key JSON via the shared contracts helper).

Transition history is append-only: this class exposes no update or
delete methods for transition rows, and tests assert reload stability.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from engines.website_generation.contracts.artifacts import canonical_json
from engines.website_generation.contracts.errors import (
    RepositoryCorruptionError,
)

_BUILD_STATE_DDL = """
CREATE TABLE IF NOT EXISTS wge_builds (
    build_id          TEXT PRIMARY KEY,
    spec_hash         TEXT NOT NULL,
    pipeline_version  TEXT NOT NULL,
    current_state     TEXT NOT NULL,
    attempt           INTEGER NOT NULL DEFAULT 1,
    cancelled         INTEGER NOT NULL DEFAULT 0,
    cancel_reason     TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wge_transitions (
    transition_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id          TEXT NOT NULL REFERENCES wge_builds(build_id),
    from_state        TEXT NOT NULL,
    to_state          TEXT NOT NULL,
    outcome           TEXT NOT NULL,
    attempt           INTEGER NOT NULL DEFAULT 1,
    transitioned_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wge_transitions_build
    ON wge_transitions(build_id);

CREATE TABLE IF NOT EXISTS wge_checkpoints (
    checkpoint_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id              TEXT NOT NULL REFERENCES wge_builds(build_id),
    state                 TEXT NOT NULL,
    attempt               INTEGER NOT NULL DEFAULT 1,
    artifact_hashes_json  TEXT NOT NULL,
    engine_versions_json  TEXT NOT NULL,
    transitioned_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wge_checkpoints_build
    ON wge_checkpoints(build_id);

CREATE TABLE IF NOT EXISTS wge_escalations (
    escalation_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id          TEXT NOT NULL REFERENCES wge_builds(build_id),
    stage             TEXT NOT NULL,
    reason            TEXT NOT NULL,
    details_json      TEXT NOT NULL,
    resolved          INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wge_escalations_build
    ON wge_escalations(build_id);

CREATE TABLE IF NOT EXISTS wge_overrides (
    override_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id          TEXT NOT NULL REFERENCES wge_builds(build_id),
    escalation_id     INTEGER REFERENCES wge_escalations(escalation_id),
    justification     TEXT NOT NULL,
    created_at        TEXT NOT NULL
);
"""


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class BuildStateRepository:
    """SQLite persistence for build rows, transitions, and checkpoints."""

    def __init__(self, db_path: Union[str, Path]) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_BUILD_STATE_DDL)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- builds ---------------------------------------------------------

    def create_build(
        self,
        build_id: str,
        spec_hash: str,
        pipeline_version: str,
        initial_state: str,
        created_at: str,
    ) -> Dict[str, Any]:
        self._conn.execute(
            "INSERT INTO wge_builds "
            "(build_id, spec_hash, pipeline_version, current_state, "
            " attempt, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (build_id, spec_hash, pipeline_version, initial_state, created_at),
        )
        self._conn.commit()
        build = self.get_build(build_id)
        assert build is not None
        return build

    def get_build(self, build_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM wge_builds WHERE build_id = ?", (build_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None

    def set_current_state(
        self, build_id: str, state: str, attempt: int = 1
    ) -> None:
        self._conn.execute(
            "UPDATE wge_builds SET current_state = ?, attempt = ? "
            "WHERE build_id = ?",
            (state, attempt, build_id),
        )
        self._conn.commit()

    def mark_cancelled(self, build_id: str, reason: str) -> None:
        """Cancellation-state storage (§6.5): flag only, no orchestration."""
        self._conn.execute(
            "UPDATE wge_builds SET cancelled = 1, cancel_reason = ? "
            "WHERE build_id = ?",
            (reason, build_id),
        )
        self._conn.commit()

    # -- transitions (append-only) ---------------------------------------

    def append_transition(
        self,
        build_id: str,
        from_state: str,
        to_state: str,
        outcome: str,
        attempt: int,
        transitioned_at: str,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO wge_transitions "
            "(build_id, from_state, to_state, outcome, attempt, "
            " transitioned_at) VALUES (?, ?, ?, ?, ?, ?)",
            (build_id, from_state, to_state, outcome, attempt, transitioned_at),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def list_transitions(self, build_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM wge_transitions WHERE build_id = ? "
            "ORDER BY transition_id ASC",
            (build_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    # -- checkpoints ------------------------------------------------------

    def record_checkpoint(
        self,
        build_id: str,
        state: str,
        attempt: int,
        artifact_hashes: Dict[str, str],
        engine_versions: Dict[str, str],
        transitioned_at: str,
    ) -> int:
        """Persist a checkpoint (§6.4) with deterministic collections."""
        cursor = self._conn.execute(
            "INSERT INTO wge_checkpoints "
            "(build_id, state, attempt, artifact_hashes_json, "
            " engine_versions_json, transitioned_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                build_id,
                state,
                attempt,
                canonical_json(dict(artifact_hashes)),
                canonical_json(dict(engine_versions)),
                transitioned_at,
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def latest_checkpoint(self, build_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM wge_checkpoints WHERE build_id = ? "
            "ORDER BY checkpoint_id DESC LIMIT 1",
            (build_id,),
        ).fetchone()
        if row is None:
            return None
        record = _row_to_dict(row)
        try:
            record["artifact_hashes"] = json.loads(
                record.pop("artifact_hashes_json")
            )
            record["engine_versions"] = json.loads(
                record.pop("engine_versions_json")
            )
        except ValueError as exc:
            raise RepositoryCorruptionError(
                "stored checkpoint JSON is corrupt: %s" % exc,
                stage="build_state_repository",
                diagnostics={"build_id": build_id},
            )
        return record

    # -- escalations and overrides (table foundation, §6.8) ---------------

    def record_escalation(
        self,
        build_id: str,
        stage: str,
        reason: str,
        details: Dict[str, Any],
        created_at: str,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO wge_escalations "
            "(build_id, stage, reason, details_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (build_id, stage, reason, canonical_json(dict(details)), created_at),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def list_escalations(self, build_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM wge_escalations WHERE build_id = ? "
            "ORDER BY escalation_id ASC",
            (build_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def record_override(
        self,
        build_id: str,
        escalation_id: Optional[int],
        justification: str,
        created_at: str,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO wge_overrides "
            "(build_id, escalation_id, justification, created_at) "
            "VALUES (?, ?, ?, ?)",
            (build_id, escalation_id, justification, created_at),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def list_overrides(self, build_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM wge_overrides WHERE build_id = ? "
            "ORDER BY override_id ASC",
            (build_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

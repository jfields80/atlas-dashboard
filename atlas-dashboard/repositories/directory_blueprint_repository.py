"""Raw-SQL repository for directory blueprints.

Atlas contract:
    * Raw SQL only (sqlite3), no ORM
    * No business logic, no scoring, no Flask
    * Callers own the connection lifecycle; every function takes a connection

The canonical API is the module-level functions. ``DirectoryBlueprintRepository``
is a compatibility shim only.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional

_SCHEMA_FILENAME = "directory_blueprint_schema.sql"


def _schema_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "models", _SCHEMA_FILENAME)


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the blueprint table and indexes if they do not exist."""
    with open(_schema_path(), "r", encoding="utf-8") as handle:
        conn.executescript(handle.read())
    conn.commit()


def insert_blueprint(
    conn: sqlite3.Connection,
    project_slug: str,
    engine_version: str,
    input_hash: str,
    committee_recommendation: str,
    data_confidence_tag: str,
    blueprint_json: str,
) -> Optional[int]:
    """Insert a blueprint row. Idempotent on (slug, input_hash, engine_version).

    Returns the new row id, or None if an identical blueprint already exists.
    """
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO directory_blueprints
            (project_slug, engine_version, input_hash,
             committee_recommendation, data_confidence_tag, blueprint_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            project_slug,
            engine_version,
            input_hash,
            committee_recommendation,
            data_confidence_tag,
            blueprint_json,
        ),
    )
    conn.commit()
    if cursor.rowcount == 0:
        return None
    return int(cursor.lastrowid)


def get_blueprint_by_id(conn: sqlite3.Connection, blueprint_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, project_slug, engine_version, input_hash,
               committee_recommendation, data_confidence_tag,
               blueprint_json, created_at
        FROM directory_blueprints
        WHERE id = ?
        """,
        (blueprint_id,),
    ).fetchone()
    return _row_to_dict(row)


def get_latest_blueprint_for_slug(
    conn: sqlite3.Connection, project_slug: str
) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, project_slug, engine_version, input_hash,
               committee_recommendation, data_confidence_tag,
               blueprint_json, created_at
        FROM directory_blueprints
        WHERE project_slug = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (project_slug,),
    ).fetchone()
    return _row_to_dict(row)


def find_by_input_hash(
    conn: sqlite3.Connection, input_hash: str, engine_version: str
) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, project_slug, engine_version, input_hash,
               committee_recommendation, data_confidence_tag,
               blueprint_json, created_at
        FROM directory_blueprints
        WHERE input_hash = ? AND engine_version = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (input_hash, engine_version),
    ).fetchone()
    return _row_to_dict(row)


def list_blueprints(conn: sqlite3.Connection, limit: int = 50) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, project_slug, engine_version, input_hash,
               committee_recommendation, data_confidence_tag,
               blueprint_json, created_at
        FROM directory_blueprints
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows if row is not None]


_COLUMNS = (
    "id",
    "project_slug",
    "engine_version",
    "input_hash",
    "committee_recommendation",
    "data_confidence_tag",
    "blueprint_json",
    "created_at",
)


def _row_to_dict(row) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(zip(_COLUMNS, row))


class DirectoryBlueprintRepository:
    """Compatibility shim over the canonical functional API."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def ensure_schema(self) -> None:
        ensure_schema(self._conn)

    def insert(self, **kwargs) -> Optional[int]:
        return insert_blueprint(self._conn, **kwargs)

    def get_by_id(self, blueprint_id: int) -> Optional[Dict[str, Any]]:
        return get_blueprint_by_id(self._conn, blueprint_id)

    def latest_for_slug(self, project_slug: str) -> Optional[Dict[str, Any]]:
        return get_latest_blueprint_for_slug(self._conn, project_slug)

    def find_by_hash(self, input_hash: str, engine_version: str) -> Optional[Dict[str, Any]]:
        return find_by_input_hash(self._conn, input_hash, engine_version)

    def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list_blueprints(self._conn, limit)

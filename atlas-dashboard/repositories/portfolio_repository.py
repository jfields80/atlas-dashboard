"""
atlas/repositories/portfolio_repository.py

Raw SQL repository for portfolio assets and snapshots.

Rules (per Atlas architecture contract):
  - Raw SQL only. No ORM, no SQLAlchemy.
  - Zero business logic. No scoring, no status-transition validation.
  - Returns plain dicts or None. Callers (services) own deserialization.
  - All writes go through the Pipeline Runner's single-writer discipline
    in production; this module may be called directly in tests/CLI only.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

_SCHEMA_PATH = Path(__file__).parent.parent / "models" / "portfolio_schema.sql"


def init_portfolio_schema(conn: sqlite3.Connection) -> None:
    """Idempotent schema application.  Safe to call on every startup."""
    sql = _SCHEMA_PATH.read_text()
    conn.executescript(sql)
    conn.commit()


# ---------------------------------------------------------------------------
# Asset CRUD
# ---------------------------------------------------------------------------

def insert_asset(conn: sqlite3.Connection, asset: dict[str, Any]) -> None:
    """Insert a new portfolio asset row.  Caller must supply all required fields."""
    conn.execute(
        """
        INSERT INTO portfolio_assets (
            asset_id, niche_slug, display_name, domain, dna_profile_json,
            primary_category, geographic_scope, monetization_model, status,
            revenue_value, revenue_source, revenue_provider,
            revenue_rationale, revenue_confidence,
            created_at, updated_at, exited_at, notes
        ) VALUES (
            :asset_id, :niche_slug, :display_name, :domain, :dna_profile_json,
            :primary_category, :geographic_scope, :monetization_model, :status,
            :revenue_value, :revenue_source, :revenue_provider,
            :revenue_rationale, :revenue_confidence,
            :created_at, :updated_at, :exited_at, :notes
        )
        """,
        asset,
    )


def update_asset_status(
    conn: sqlite3.Connection,
    asset_id: str,
    new_status: str,
    updated_at: str,
    exited_at: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE portfolio_assets
           SET status = :status,
               updated_at = :updated_at,
               exited_at = :exited_at
         WHERE asset_id = :asset_id
        """,
        {
            "asset_id": asset_id,
            "status": new_status,
            "updated_at": updated_at,
            "exited_at": exited_at,
        },
    )


def update_asset_revenue(
    conn: sqlite3.Connection,
    asset_id: str,
    revenue_value: float,
    revenue_source: str,
    revenue_confidence: float,
    revenue_provider: str | None,
    revenue_rationale: str | None,
    updated_at: str,
) -> None:
    conn.execute(
        """
        UPDATE portfolio_assets
           SET revenue_value      = :revenue_value,
               revenue_source     = :revenue_source,
               revenue_confidence = :revenue_confidence,
               revenue_provider   = :revenue_provider,
               revenue_rationale  = :revenue_rationale,
               updated_at         = :updated_at
         WHERE asset_id = :asset_id
        """,
        {
            "asset_id": asset_id,
            "revenue_value": revenue_value,
            "revenue_source": revenue_source,
            "revenue_confidence": revenue_confidence,
            "revenue_provider": revenue_provider,
            "revenue_rationale": revenue_rationale,
            "updated_at": updated_at,
        },
    )


def get_asset_by_id(
    conn: sqlite3.Connection, asset_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM portfolio_assets WHERE asset_id = ?", (asset_id,)
    ).fetchone()
    return dict(row) if row else None


def get_asset_by_domain(
    conn: sqlite3.Connection, domain: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM portfolio_assets WHERE domain = ?", (domain,)
    ).fetchone()
    return dict(row) if row else None


def list_assets_by_status(
    conn: sqlite3.Connection, status: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM portfolio_assets WHERE status = ? ORDER BY created_at",
        (status,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_all_active_assets(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Returns all assets that are not exited or dead."""
    rows = conn.execute(
        """
        SELECT * FROM portfolio_assets
         WHERE status NOT IN ('exited', 'dead')
         ORDER BY created_at
        """,
    ).fetchall()
    return [dict(r) for r in rows]


def list_all_assets(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM portfolio_assets ORDER BY created_at"
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Asset history
# ---------------------------------------------------------------------------

def insert_asset_history(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO portfolio_asset_history
            (history_id, asset_id, previous_status, new_status, changed_at, changed_by, notes)
        VALUES
            (:history_id, :asset_id, :previous_status, :new_status, :changed_at, :changed_by, :notes)
        """,
        record,
    )


def get_asset_history(
    conn: sqlite3.Connection, asset_id: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM portfolio_asset_history
         WHERE asset_id = ?
         ORDER BY changed_at
        """,
        (asset_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def insert_snapshot(conn: sqlite3.Connection, snapshot: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO portfolio_snapshots
            (snapshot_id, created_at, asset_count, owned_count,
             building_count, candidate_count, status, notes)
        VALUES
            (:snapshot_id, :created_at, :asset_count, :owned_count,
             :building_count, :candidate_count, :status, :notes)
        """,
        snapshot,
    )


def insert_snapshot_asset(
    conn: sqlite3.Connection, snapshot_id: str, asset_id: str, asset_state: dict[str, Any]
) -> None:
    conn.execute(
        """
        INSERT INTO portfolio_snapshot_assets (snapshot_id, asset_id, asset_state_json)
        VALUES (?, ?, ?)
        """,
        (snapshot_id, asset_id, json.dumps(asset_state)),
    )


def get_snapshot_by_id(
    conn: sqlite3.Connection, snapshot_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM portfolio_snapshots WHERE snapshot_id = ?", (snapshot_id,)
    ).fetchone()
    return dict(row) if row else None


def get_snapshot_assets(
    conn: sqlite3.Connection, snapshot_id: str
) -> list[dict[str, Any]]:
    """Returns the asset states as they were at snapshot creation time."""
    rows = conn.execute(
        """
        SELECT asset_state_json FROM portfolio_snapshot_assets
         WHERE snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    return [json.loads(r["asset_state_json"]) for r in rows]


def get_latest_snapshot(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM portfolio_snapshots
         WHERE status = 'active'
         ORDER BY created_at DESC
         LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def supersede_previous_snapshots(
    conn: sqlite3.Connection, except_snapshot_id: str
) -> None:
    """Mark all active snapshots except the given one as superseded.
    Called after a new snapshot is committed."""
    conn.execute(
        """
        UPDATE portfolio_snapshots
           SET status = 'superseded'
         WHERE status = 'active'
           AND snapshot_id != ?
        """,
        (except_snapshot_id,),
    )


# ---------------------------------------------------------------------------
# Compatibility wrapper
#
# Thin class shim for older call sites / tests that expect a
# PortfolioRepository class instance rather than module-level
# functions. Contains zero SQL of its own and zero business logic —
# every method delegates directly to the function of the same name
# above. The functional API remains canonical; all raw SQL lives
# only in the functions above, unchanged.
# ---------------------------------------------------------------------------

class PortfolioRepository:
    """
    Compatibility wrapper around the module-level repository functions.

    Usage:
        repo = PortfolioRepository()
        repo.insert_asset(conn, asset_dict)
        row = repo.get_asset_by_id(conn, asset_id)

    This class holds no state and performs no logic of its own —
    it exists solely so that code written against a class-based
    interface continues to work unchanged.
    """

    def init_schema(self, conn: sqlite3.Connection) -> None:
        return init_portfolio_schema(conn)

    def insert_asset(self, conn: sqlite3.Connection, asset: dict[str, Any]) -> None:
        return insert_asset(conn, asset)

    def update_asset_status(
        self,
        conn: sqlite3.Connection,
        asset_id: str,
        new_status: str,
        updated_at: str,
        exited_at: str | None = None,
    ) -> None:
        return update_asset_status(conn, asset_id, new_status, updated_at, exited_at)

    def update_asset_revenue(
        self,
        conn: sqlite3.Connection,
        asset_id: str,
        revenue_value: float,
        revenue_source: str,
        revenue_confidence: float,
        revenue_provider: str | None,
        revenue_rationale: str | None,
        updated_at: str,
    ) -> None:
        return update_asset_revenue(
            conn, asset_id, revenue_value, revenue_source,
            revenue_confidence, revenue_provider, revenue_rationale, updated_at,
        )

    def get_asset_by_id(self, conn: sqlite3.Connection, asset_id: str) -> dict[str, Any] | None:
        return get_asset_by_id(conn, asset_id)

    def get_asset_by_domain(self, conn: sqlite3.Connection, domain: str) -> dict[str, Any] | None:
        return get_asset_by_domain(conn, domain)

    def list_assets_by_status(self, conn: sqlite3.Connection, status: str) -> list[dict[str, Any]]:
        return list_assets_by_status(conn, status)

    def list_all_active_assets(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        return list_all_active_assets(conn)

    def list_all_assets(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        return list_all_assets(conn)

    def insert_asset_history(self, conn: sqlite3.Connection, record: dict[str, Any]) -> None:
        return insert_asset_history(conn, record)

    def get_asset_history(self, conn: sqlite3.Connection, asset_id: str) -> list[dict[str, Any]]:
        return get_asset_history(conn, asset_id)

    def insert_snapshot(self, conn: sqlite3.Connection, snapshot: dict[str, Any]) -> None:
        return insert_snapshot(conn, snapshot)

    def insert_snapshot_asset(
        self,
        conn: sqlite3.Connection,
        snapshot_id: str,
        asset_id: str,
        asset_state: dict[str, Any],
    ) -> None:
        return insert_snapshot_asset(conn, snapshot_id, asset_id, asset_state)

    def get_snapshot_by_id(self, conn: sqlite3.Connection, snapshot_id: str) -> dict[str, Any] | None:
        return get_snapshot_by_id(conn, snapshot_id)

    def get_snapshot_assets(self, conn: sqlite3.Connection, snapshot_id: str) -> list[dict[str, Any]]:
        return get_snapshot_assets(conn, snapshot_id)

    def get_latest_snapshot(self, conn: sqlite3.Connection) -> dict[str, Any] | None:
        return get_latest_snapshot(conn)

    def supersede_previous_snapshots(self, conn: sqlite3.Connection, except_snapshot_id: str) -> None:
        return supersede_previous_snapshots(conn, except_snapshot_id)

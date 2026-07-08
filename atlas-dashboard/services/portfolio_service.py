"""
atlas/services/portfolio_service.py

Portfolio State Service — the authoritative manager for:
  1. Asset lifecycle (candidate → building → owned → exited / dead)
  2. Revenue tracking (TaggedValue-aware: VERIFIED / ESTIMATED / UNKNOWN)
  3. Immutable snapshot creation (PortfolioSnapshot consumed by
     Synergy Engine, Expansion Classifier, Investment Committee)

Architecture rules enforced here:
  - Zero SQL. All persistence delegated to portfolio_repository.
  - Zero scoring / no investment decisions.
  - Returns dataclasses (not dicts); callers own further transformation.
  - Snapshots are the ONLY safe way for downstream engines to read
    portfolio state — never pass a live connection to an engine.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from repositories import portfolio_repository as repo

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

VALID_STATUSES = frozenset({"candidate", "building", "owned", "exited", "dead"})
VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "candidate": frozenset({"building", "dead"}),
    "building":  frozenset({"owned", "dead"}),
    "owned":     frozenset({"exited", "dead"}),
    "exited":    frozenset(),                    # terminal
    "dead":      frozenset(),                    # terminal
}

VALID_DATA_SOURCES = frozenset({"VERIFIED", "ESTIMATED", "UNKNOWN"})


@dataclass(frozen=True)
class RevenueTaggedValue:
    """Honesty primitive for monthly revenue, per TaggedValue contract."""
    value: float                    # monthly USD
    source: str                     # VERIFIED | ESTIMATED | UNKNOWN
    confidence: float               # 0.0–1.0
    provider: str | None = None
    rationale: str | None = None

    def __post_init__(self) -> None:
        if self.source not in VALID_DATA_SOURCES:
            raise ValueError(f"Invalid revenue source: {self.source!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be 0.0–1.0, got {self.confidence}")


@dataclass(frozen=True)
class PortfolioAsset:
    """Immutable view of a portfolio asset — used inside snapshots."""
    asset_id: str
    niche_slug: str
    display_name: str
    domain: str | None
    primary_category: str
    geographic_scope: str           # local | regional | national | global
    monetization_model: str | None
    status: str                     # candidate | building | owned | exited | dead
    revenue: RevenueTaggedValue
    created_at: str
    updated_at: str
    exited_at: str | None = None
    notes: str | None = None
    dna_profile: dict[str, Any] | None = None   # deserialised DNA YAML


@dataclass(frozen=True)
class PortfolioSnapshot:
    """
    Immutable, self-contained point-in-time view of the portfolio.

    This is the ONLY type that Synergy Engine, Expansion Classifier,
    and Investment Committee should ever receive.  They must never
    read live portfolio state from a database connection.

    Determinism guarantee:
        same opportunity_inputs + same snapshot_id → same outputs.
    """
    snapshot_id: str
    created_at: str
    assets: tuple[PortfolioAsset, ...]

    # Convenient computed views (set at construction time, immutable)
    owned: tuple[PortfolioAsset, ...]    = field(default_factory=tuple)
    building: tuple[PortfolioAsset, ...]= field(default_factory=tuple)
    candidates: tuple[PortfolioAsset, ...]= field(default_factory=tuple)

    @property
    def active_assets(self) -> tuple[PortfolioAsset, ...]:
        """Assets that are not exited or dead."""
        return tuple(a for a in self.assets if a.status not in ("exited", "dead"))

    @property
    def total_verified_monthly_revenue(self) -> float:
        return sum(
            a.revenue.value
            for a in self.owned
            if a.revenue.source == "VERIFIED"
        )

    @property
    def categories_represented(self) -> frozenset[str]:
        return frozenset(a.primary_category for a in self.active_assets)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _asset_from_row(row: dict[str, Any]) -> PortfolioAsset:
    revenue = RevenueTaggedValue(
        value=row["revenue_value"],
        source=row["revenue_source"],
        confidence=row["revenue_confidence"],
        provider=row.get("revenue_provider"),
        rationale=row.get("revenue_rationale"),
    )
    dna_raw = row.get("dna_profile_json")
    return PortfolioAsset(
        asset_id=row["asset_id"],
        niche_slug=row["niche_slug"],
        display_name=row["display_name"],
        domain=row.get("domain"),
        primary_category=row["primary_category"],
        geographic_scope=row["geographic_scope"],
        monetization_model=row.get("monetization_model"),
        status=row["status"],
        revenue=revenue,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        exited_at=row.get("exited_at"),
        notes=row.get("notes"),
        dna_profile=json.loads(dna_raw) if dna_raw else None,
    )


def _asset_to_persist_dict(asset: PortfolioAsset) -> dict[str, Any]:
    """Flat dict ready for the repository insert."""
    return {
        "asset_id": asset.asset_id,
        "niche_slug": asset.niche_slug,
        "display_name": asset.display_name,
        "domain": asset.domain,
        "dna_profile_json": json.dumps(asset.dna_profile) if asset.dna_profile else None,
        "primary_category": asset.primary_category,
        "geographic_scope": asset.geographic_scope,
        "monetization_model": asset.monetization_model,
        "status": asset.status,
        "revenue_value": asset.revenue.value,
        "revenue_source": asset.revenue.source,
        "revenue_provider": asset.revenue.provider,
        "revenue_rationale": asset.revenue.rationale,
        "revenue_confidence": asset.revenue.confidence,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
        "exited_at": asset.exited_at,
        "notes": asset.notes,
    }


# ---------------------------------------------------------------------------
# Schema init (delegates to repository)
# ---------------------------------------------------------------------------

def init_schema(conn: sqlite3.Connection) -> None:
    """Idempotent.  Call on application startup."""
    repo.init_portfolio_schema(conn)


# ---------------------------------------------------------------------------
# Asset management
# ---------------------------------------------------------------------------

def register_asset(
    conn: sqlite3.Connection,
    *,
    niche_slug: str,
    display_name: str,
    primary_category: str,
    geographic_scope: str = "national",
    domain: str | None = None,
    monetization_model: str | None = None,
    revenue: RevenueTaggedValue | None = None,
    dna_profile: dict[str, Any] | None = None,
    notes: str | None = None,
    initial_status: str = "candidate",
) -> PortfolioAsset:
    """
    Register a new asset.  Returns the PortfolioAsset dataclass.

    Revenue defaults to UNKNOWN $0 if not supplied — this is intentional:
    fabricating an ESTIMATED value for a new candidate violates the
    honesty contract.
    """
    if initial_status not in VALID_STATUSES:
        raise ValueError(f"Invalid initial status: {initial_status!r}")

    if revenue is None:
        revenue = RevenueTaggedValue(
            value=0.0, source="UNKNOWN", confidence=0.0,
            rationale="No revenue data at registration time."
        )

    now = _now_iso()
    asset = PortfolioAsset(
        asset_id=_new_id(),
        niche_slug=niche_slug,
        display_name=display_name,
        domain=domain,
        primary_category=primary_category,
        geographic_scope=geographic_scope,
        monetization_model=monetization_model,
        status=initial_status,
        revenue=revenue,
        created_at=now,
        updated_at=now,
        dna_profile=dna_profile,
        notes=notes,
    )
    repo.insert_asset(conn, _asset_to_persist_dict(asset))
    conn.commit()
    return asset


def transition_status(
    conn: sqlite3.Connection,
    asset_id: str,
    new_status: str,
    changed_by: str = "manual",
    notes: str | None = None,
) -> PortfolioAsset:
    """
    Move an asset through its lifecycle.  Enforces valid transitions.

    Valid paths:
        candidate → building | dead
        building  → owned    | dead
        owned     → exited   | dead
        exited    → (terminal)
        dead      → (terminal)
    """
    row = repo.get_asset_by_id(conn, asset_id)
    if row is None:
        raise ValueError(f"Asset not found: {asset_id!r}")

    current_status = row["status"]
    if new_status not in VALID_TRANSITIONS.get(current_status, frozenset()):
        raise ValueError(
            f"Invalid transition {current_status!r} → {new_status!r} "
            f"for asset {asset_id!r}. "
            f"Valid next states: {VALID_TRANSITIONS.get(current_status, frozenset())}"
        )

    now = _now_iso()
    exited_at = now if new_status == "exited" else row.get("exited_at")

    repo.update_asset_status(conn, asset_id, new_status, now, exited_at)
    repo.insert_asset_history(conn, {
        "history_id": _new_id(),
        "asset_id": asset_id,
        "previous_status": current_status,
        "new_status": new_status,
        "changed_at": now,
        "changed_by": changed_by,
        "notes": notes,
    })
    conn.commit()

    updated_row = repo.get_asset_by_id(conn, asset_id)
    return _asset_from_row(updated_row)


def update_revenue(
    conn: sqlite3.Connection,
    asset_id: str,
    revenue: RevenueTaggedValue,
    changed_by: str = "manual",
) -> PortfolioAsset:
    """
    Update the revenue TaggedValue for an asset.

    The caller is responsible for honesty:
      - VERIFIED only if you have a real bank / payment processor figure.
      - ESTIMATED for modelled projections.
      - UNKNOWN when you genuinely don't know.
    This service does not re-label sources.
    """
    row = repo.get_asset_by_id(conn, asset_id)
    if row is None:
        raise ValueError(f"Asset not found: {asset_id!r}")

    now = _now_iso()
    repo.update_asset_revenue(
        conn,
        asset_id=asset_id,
        revenue_value=revenue.value,
        revenue_source=revenue.source,
        revenue_confidence=revenue.confidence,
        revenue_provider=revenue.provider,
        revenue_rationale=revenue.rationale,
        updated_at=now,
    )
    conn.commit()

    updated_row = repo.get_asset_by_id(conn, asset_id)
    return _asset_from_row(updated_row)


def get_asset(conn: sqlite3.Connection, asset_id: str) -> PortfolioAsset | None:
    row = repo.get_asset_by_id(conn, asset_id)
    return _asset_from_row(row) if row else None


def list_assets(
    conn: sqlite3.Connection,
    status: str | None = None,
    active_only: bool = False,
) -> list[PortfolioAsset]:
    if status:
        rows = repo.list_assets_by_status(conn, status)
    elif active_only:
        rows = repo.list_all_active_assets(conn)
    else:
        rows = repo.list_all_assets(conn)
    return [_asset_from_row(r) for r in rows]


def get_asset_history(conn: sqlite3.Connection, asset_id: str) -> list[dict[str, Any]]:
    return repo.get_asset_history(conn, asset_id)


# ---------------------------------------------------------------------------
# Snapshot creation — the critical v3 primitive
# ---------------------------------------------------------------------------

def create_snapshot(
    conn: sqlite3.Connection,
    include_statuses: tuple[str, ...] = ("candidate", "building", "owned"),
    notes: str | None = None,
) -> PortfolioSnapshot:
    """
    Create an immutable, persisted PortfolioSnapshot.

    The snapshot captures all active assets (default: candidate, building,
    owned) at the moment of this call.  The returned object is what every
    downstream engine (Synergy, Classifier, Committee) must receive.

    Design: the snapshot_assets join table serialises each asset's full
    state as JSON, so the snapshot is self-contained — even if live asset
    data is later mutated or deleted, replaying a historical run against
    its original snapshot_id returns the identical state.
    """
    now = _now_iso()
    snapshot_id = _new_id()

    # Collect assets included in this snapshot
    all_rows: list[dict[str, Any]] = []
    for status in include_statuses:
        all_rows.extend(repo.list_assets_by_status(conn, status))

    assets: list[PortfolioAsset] = [_asset_from_row(r) for r in all_rows]

    # Convenience groupings
    owned    = tuple(a for a in assets if a.status == "owned")
    building = tuple(a for a in assets if a.status == "building")
    candidates = tuple(a for a in assets if a.status == "candidate")

    snapshot = PortfolioSnapshot(
        snapshot_id=snapshot_id,
        created_at=now,
        assets=tuple(assets),
        owned=owned,
        building=building,
        candidates=candidates,
    )

    # Persist snapshot header
    repo.insert_snapshot(conn, {
        "snapshot_id": snapshot_id,
        "created_at": now,
        "asset_count": len(assets),
        "owned_count": len(owned),
        "building_count": len(building),
        "candidate_count": len(candidates),
        "status": "active",
        "notes": notes,
    })

    # Persist each asset's state at snapshot time
    for asset in assets:
        asset_state = _asset_to_persist_dict(asset)
        # Also store revenue as structured sub-dict for readability
        asset_state["_revenue"] = {
            "value": asset.revenue.value,
            "source": asset.revenue.source,
            "confidence": asset.revenue.confidence,
        }
        repo.insert_snapshot_asset(conn, snapshot_id, asset.asset_id, asset_state)

    # Mark previous active snapshots as superseded
    repo.supersede_previous_snapshots(conn, except_snapshot_id=snapshot_id)

    conn.commit()
    return snapshot


def load_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> PortfolioSnapshot | None:
    """
    Reload a previously persisted snapshot from its stored asset states.
    Used for run replay — reconstructs the exact portfolio view from
    snapshot time, regardless of any subsequent live mutations.
    """
    header = repo.get_snapshot_by_id(conn, snapshot_id)
    if header is None:
        return None

    asset_dicts = repo.get_snapshot_assets(conn, snapshot_id)
    assets = [_asset_from_row(d) for d in asset_dicts]

    owned    = tuple(a for a in assets if a.status == "owned")
    building = tuple(a for a in assets if a.status == "building")
    candidates = tuple(a for a in assets if a.status == "candidate")

    return PortfolioSnapshot(
        snapshot_id=snapshot_id,
        created_at=header["created_at"],
        assets=tuple(assets),
        owned=owned,
        building=building,
        candidates=candidates,
    )


def get_latest_snapshot(conn: sqlite3.Connection) -> PortfolioSnapshot | None:
    header = repo.get_latest_snapshot(conn)
    if header is None:
        return None
    return load_snapshot(conn, header["snapshot_id"])
class PortfolioStateService:
    def init_schema(self, conn):
        return init_schema(conn)

    def register_asset(self, conn, **kwargs):
        return register_asset(conn, **kwargs)

    def transition_status(self, conn, asset_id, new_status, changed_by="manual", notes=None):
        return transition_status(conn, asset_id, new_status, changed_by, notes)

    def update_revenue(self, conn, asset_id, revenue, changed_by="manual"):
        return update_revenue(conn, asset_id, revenue, changed_by)

    def get_asset(self, conn, asset_id):
        return get_asset(conn, asset_id)

    def list_assets(self, conn, status=None, active_only=False):
        return list_assets(conn, status, active_only)

    def get_asset_history(self, conn, asset_id):
        return get_asset_history(conn, asset_id)

    def create_snapshot(self, conn, include_statuses=("candidate", "building", "owned"), notes=None):
        return create_snapshot(conn, include_statuses, notes)

    def load_snapshot(self, conn, snapshot_id):
        return load_snapshot(conn, snapshot_id)

    def get_latest_snapshot(self, conn):
        return get_latest_snapshot(conn)
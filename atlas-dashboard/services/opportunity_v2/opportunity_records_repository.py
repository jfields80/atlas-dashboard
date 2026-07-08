"""
opportunity_records_repository.py — persistence for Opportunity Records.

Design rules for this module:
- ZERO scoring logic. Reads / writes only.
- ZERO Flask coupling. Takes plain arguments, returns plain dicts or
  domain objects. Routes/UI live elsewhere.
- Idempotent operations. `upsert_opportunity` is the entry point for a
  fresh drill result — it either creates the record or finds the existing
  one and returns the same id. No duplicate records for the same niche
  under the same DNA.
- Explicit run_number and version_number, computed inside a transaction
  so concurrent writes don't collide.
- Snapshot the DNA at decision time so historical decisions stay
  interpretable when the DNA profile is edited later.

Public API (this is the entire surface — Flask calls these later):

    Opportunity Record lifecycle
        get_or_create_opportunity(dna_slug, display_name, ...) -> opportunity_id
        get_opportunity(opportunity_id) -> dict | None
        list_opportunities(...) -> list[dict]
        update_status(opportunity_id, status)
        archive_opportunity(opportunity_id)

    Decisions
        save_decision(opportunity_id, decision_result, dna, ...) -> decision_id
        get_decision(decision_id) -> dict
        list_decisions_for_opportunity(opportunity_id) -> list[dict]  (newest first)
        latest_decision(opportunity_id) -> dict | None
        compare_decisions(decision_a_id, decision_b_id) -> dict

    Blueprints
        save_blueprint_version(opportunity_id, blueprint) -> version_id
        list_blueprint_versions(opportunity_id) -> list[dict]
        get_blueprint_version(version_id) -> dict

    Scout runs
        create_scout_run(opportunity_id) -> scout_run_id
        finish_scout_run(scout_run_id, ...)
        save_competitor_observation(scout_run_id, ...) -> obs_id
        list_scout_runs(opportunity_id) -> list[dict]

    Revenue history
        record_revenue_estimate(opportunity_id, decision_id, ...) -> row_id
        revenue_history(opportunity_id) -> list[dict]

    Notes
        add_note(opportunity_id, body, decision_id=None) -> note_id
        list_notes(opportunity_id) -> list[dict]

    Schema / bulk
        init_schema(db_path=None)
        opportunity_history(opportunity_id) -> dict  (the "everything" view)
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "atlas.db"
SCHEMA_PATH = PROJECT_ROOT / "models" / "opportunity_records_schema.sql"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@contextmanager
def get_connection(db_path=None):
    conn = sqlite3.connect(db_path or DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema(db_path=None):
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _canonical(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _serialize(obj: Any) -> str:
    """JSON-serialize dataclasses, enums, Pydantic-style objects,
    and nested structures.
    """
    def default(o):
        if is_dataclass(o):
            return asdict(o)

        if hasattr(o, "value") and hasattr(o, "name"):
            return o.value

        if hasattr(o, "model_dump"):
            return o.model_dump(mode="json")

        if hasattr(o, "dict"):
            return o.dict()

        if hasattr(o, "__dict__"):
            return {
                key: value
                for key, value in vars(o).items()
                if not key.startswith("_")
            }

        raise TypeError(f"Cannot serialize {type(o).__name__}")

    return json.dumps(obj, default=default)


def _row(r) -> dict | None:
    return dict(r) if r else None

# ---------------------------------------------------------------------------
# Opportunity Record lifecycle
# ---------------------------------------------------------------------------

def get_or_create_opportunity(dna_slug: str, display_name: str,
                                asset_type: str | None = None,
                                ecosystem_node_name: str | None = None,
                                db_path=None) -> int:
    """Return the opportunity_records.id for this (dna_slug, canonical_name),
    creating the row if it doesn't exist. This is the entry point when a
    drill run wants to persist a new decision — it never duplicates."""
    canonical = _canonical(display_name)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM opportunity_records WHERE dna_slug=? AND canonical_name=?",
            (dna_slug, canonical)).fetchone()
        if row:
            # Bump last_analyzed_at; leave asset_type/ecosystem alone (they
            # were set at first-seen and are the record's identity fields).
            conn.execute(
                "UPDATE opportunity_records SET last_analyzed_at=CURRENT_TIMESTAMP "
                "WHERE id=?", (row["id"],))
            return row["id"]
        cur = conn.execute(
            """INSERT INTO opportunity_records
               (canonical_name, display_name, dna_slug, asset_type,
                ecosystem_node_name)
               VALUES (?, ?, ?, ?, ?)""",
            (canonical, display_name, dna_slug, asset_type, ecosystem_node_name))
        return cur.lastrowid


def get_opportunity(opportunity_id: int, db_path=None) -> dict | None:
    with get_connection(db_path) as conn:
        return _row(conn.execute(
            "SELECT * FROM opportunity_records WHERE id=?",
            (opportunity_id,)).fetchone())


def find_opportunity(dna_slug: str, display_name: str, db_path=None) -> dict | None:
    canonical = _canonical(display_name)
    with get_connection(db_path) as conn:
        return _row(conn.execute(
            "SELECT * FROM opportunity_records WHERE dna_slug=? AND canonical_name=?",
            (dna_slug, canonical)).fetchone())


def list_opportunities(dna_slug: str | None = None,
                        status: str | None = None,
                        recommendation: str | None = None,
                        min_confidence: float | None = None,
                        limit: int = 200,
                        db_path=None) -> list[dict]:
    """List opportunities with optional filters. Denormalized latest_*
    fields make this a single-table query without joining decisions."""
    where, params = [], []
    if dna_slug:
        where.append("dna_slug=?"); params.append(dna_slug)
    if status:
        where.append("current_status=?"); params.append(status)
    if recommendation:
        where.append("latest_recommendation=?"); params.append(recommendation)
    if min_confidence is not None:
        where.append("latest_confidence >= ?"); params.append(min_confidence)
    sql = "SELECT * FROM opportunity_records"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY last_analyzed_at DESC LIMIT ?"
    params.append(limit)
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def update_status(opportunity_id: int, status: str, db_path=None):
    valid = {"unreviewed", "tracking", "building", "live", "archived"}
    if status not in valid:
        raise ValueError(f"status must be one of {valid}")
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE opportunity_records SET current_status=? WHERE id=?",
            (status, opportunity_id))


def archive_opportunity(opportunity_id: int, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE opportunity_records "
            "SET current_status='archived', archived_at=CURRENT_TIMESTAMP "
            "WHERE id=?", (opportunity_id,))


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

def save_decision(opportunity_id: int,
                   decision_result,                  # Pydantic DecisionResult
                   dna=None,                         # OpportunityDNA (snapshot)
                   scout_run_id: int | None = None,
                   blueprint_version_id: int | None = None,
                   triggered_by: str = "manual",
                   db_path=None) -> int:
    """Persist a DecisionResult, atomically assigning the next run_number
    for the opportunity, and update the opportunity_records denormalized
    caches so listing queries stay fast."""
    result_json = decision_result.model_dump_json() \
        if hasattr(decision_result, "model_dump_json") \
        else _serialize(decision_result)
    dna_version = getattr(dna, "version", None) if dna else None
    dna_snapshot = _serialize(dna) if dna else None

    with get_connection(db_path) as conn:
        # Reserve next run number under a transaction (SQLite serializes
        # writes so this is atomic against concurrent save_decision calls
        # to the same opportunity).
        row = conn.execute(
            "SELECT COALESCE(MAX(run_number), 0) + 1 AS next FROM decisions "
            "WHERE opportunity_id=?", (opportunity_id,)).fetchone()
        run_number = row["next"]

        cur = conn.execute(
            """INSERT INTO decisions
               (opportunity_id, run_number, data_quality, recommendation,
                confidence_score, result_json, dna_profile_version,
                dna_profile_snapshot_json, scout_run_id, blueprint_version_id,
                triggered_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (opportunity_id, run_number,
             decision_result.data_quality, decision_result.recommendation,
             decision_result.confidence_score, result_json, dna_version,
             dna_snapshot, scout_run_id, blueprint_version_id, triggered_by))
        decision_id = cur.lastrowid

        # Denormalized cache on the record
        conn.execute(
            """UPDATE opportunity_records
               SET latest_recommendation=?, latest_confidence=?,
                   latest_data_quality=?, last_analyzed_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (decision_result.recommendation, decision_result.confidence_score,
             decision_result.data_quality, opportunity_id))

        # Also stamp revenue history alongside the decision — cheap trend queries later
        conn.execute(
            """INSERT INTO revenue_estimate_history
               (opportunity_id, decision_id, revenue_low, revenue_high,
                confidence, data_quality)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (opportunity_id, decision_id,
             decision_result.estimated_revenue_low,
             decision_result.estimated_revenue_high,
             decision_result.confidence_score,
             decision_result.data_quality))
    return decision_id


def get_decision(decision_id: int, db_path=None) -> dict | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM decisions WHERE id=?",
                            (decision_id,)).fetchone()
        return _row(row)


def list_decisions_for_opportunity(opportunity_id: int, db_path=None) -> list[dict]:
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM decisions WHERE opportunity_id=? "
            "ORDER BY run_number DESC", (opportunity_id,)).fetchall()]


def latest_decision(opportunity_id: int, db_path=None) -> dict | None:
    with get_connection(db_path) as conn:
        return _row(conn.execute(
            "SELECT * FROM decisions WHERE opportunity_id=? "
            "ORDER BY run_number DESC LIMIT 1", (opportunity_id,)).fetchone())


def compare_decisions(decision_a_id: int, decision_b_id: int,
                       db_path=None) -> dict:
    """Return a diff-ready structure comparing two decisions. Pure read;
    the actual diff formatting is a UI concern. This just packages both
    rows and highlights the field-level deltas that matter most for UI
    rendering (recommendation, confidence, revenue)."""
    a = get_decision(decision_a_id, db_path)
    b = get_decision(decision_b_id, db_path)
    if not a or not b:
        raise ValueError("both decisions must exist")
    if a["opportunity_id"] != b["opportunity_id"]:
        raise ValueError("cannot compare decisions from different opportunities")
    a_full = json.loads(a["result_json"])
    b_full = json.loads(b["result_json"])
    return {
        "opportunity_id": a["opportunity_id"],
        "a": {"run_number": a["run_number"], "created_at": a["created_at"],
               "result": a_full},
        "b": {"run_number": b["run_number"], "created_at": b["created_at"],
               "result": b_full},
        "deltas": {
            "recommendation": (a_full["recommendation"], b_full["recommendation"]),
            "confidence_score": (a_full["confidence_score"], b_full["confidence_score"]),
            "data_quality": (a_full["data_quality"], b_full["data_quality"]),
            "estimated_revenue_low": (a_full["estimated_revenue_low"],
                                       b_full["estimated_revenue_low"]),
            "estimated_revenue_high": (a_full["estimated_revenue_high"],
                                        b_full["estimated_revenue_high"]),
        },
    }


# ---------------------------------------------------------------------------
# Blueprint versions
# ---------------------------------------------------------------------------

def save_blueprint_version(opportunity_id: int, blueprint, db_path=None) -> int:
    """`blueprint` is a SiteBlueprint dataclass from services/opportunity_v2/blueprint.py.
    We snapshot the full assets list; this module doesn't inspect its shape."""
    bp_dict = asdict(blueprint) if is_dataclass(blueprint) else blueprint
    counts = blueprint.counts() if hasattr(blueprint, "counts") else {}
    total = blueprint.total_pages() if hasattr(blueprint, "total_pages") else None

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 AS next "
            "FROM blueprint_versions WHERE opportunity_id=?",
            (opportunity_id,)).fetchone()
        version_number = row["next"]
        cur = conn.execute(
            """INSERT INTO blueprint_versions
               (opportunity_id, version_number, directory_name, lineage,
                total_pages, counts_json, assets_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (opportunity_id, version_number,
             bp_dict.get("directory_name"), bp_dict.get("lineage"),
             total, json.dumps(counts), json.dumps(bp_dict)))
        return cur.lastrowid


def list_blueprint_versions(opportunity_id: int, db_path=None) -> list[dict]:
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, version_number, directory_name, total_pages, "
            "counts_json, created_at FROM blueprint_versions "
            "WHERE opportunity_id=? ORDER BY version_number DESC",
            (opportunity_id,)).fetchall()]


def get_blueprint_version(version_id: int, db_path=None) -> dict | None:
    with get_connection(db_path) as conn:
        return _row(conn.execute(
            "SELECT * FROM blueprint_versions WHERE id=?",
            (version_id,)).fetchone())


# ---------------------------------------------------------------------------
# Scout runs (forward-declared; Scout module to fill in later)
# ---------------------------------------------------------------------------

def create_scout_run(opportunity_id: int, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO scout_runs (opportunity_id, status) VALUES (?, 'running')",
            (opportunity_id,))
        return cur.lastrowid


def finish_scout_run(scout_run_id: int, status: str,
                      verified_business_count: int | None = None,
                      verified_competitor_count: int | None = None,
                      findings: Any = None, error: str | None = None,
                      db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            """UPDATE scout_runs
               SET status=?, finished_at=CURRENT_TIMESTAMP,
                   verified_business_count=?, verified_competitor_count=?,
                   findings_json=?, error=?
               WHERE id=?""",
            (status, verified_business_count, verified_competitor_count,
             _serialize(findings) if findings is not None else None,
             error, scout_run_id))


def save_competitor_observation(scout_run_id: int, url: str,
                                  domain: str | None = None,
                                  category: str | None = None,
                                  quality_score: float | None = None,
                                  quality_grade: str | None = None,
                                  monetization: Any = None,
                                  audit_signals: Any = None,
                                  audit_notes: Any = None,
                                  db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO competitor_observations
               (scout_run_id, url, domain, category, quality_score, quality_grade,
                monetization_json, audit_signals_json, audit_notes_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (scout_run_id, url, domain, category, quality_score, quality_grade,
             _serialize(monetization) if monetization is not None else None,
             _serialize(audit_signals) if audit_signals is not None else None,
             _serialize(audit_notes) if audit_notes is not None else None))
        return cur.lastrowid


def list_scout_runs(opportunity_id: int, db_path=None) -> list[dict]:
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM scout_runs WHERE opportunity_id=? "
            "ORDER BY started_at DESC", (opportunity_id,)).fetchall()]


# ---------------------------------------------------------------------------
# Revenue history
# ---------------------------------------------------------------------------

def revenue_history(opportunity_id: int, db_path=None) -> list[dict]:
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM revenue_estimate_history WHERE opportunity_id=? "
            "ORDER BY estimated_at ASC, id ASC", (opportunity_id,)).fetchall()]


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

def add_note(opportunity_id: int, body: str,
              decision_id: int | None = None, author: str = "user",
              db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO opportunity_notes (opportunity_id, decision_id, author, body) "
            "VALUES (?, ?, ?, ?)",
            (opportunity_id, decision_id, author, body))
        return cur.lastrowid


def list_notes(opportunity_id: int, db_path=None) -> list[dict]:
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM opportunity_notes WHERE opportunity_id=? "
            "ORDER BY created_at DESC", (opportunity_id,)).fetchall()]


# ---------------------------------------------------------------------------
# The "everything" view — what the UI will need for /opportunity/<id>
# ---------------------------------------------------------------------------

def opportunity_history(opportunity_id: int, db_path=None) -> dict:
    """Return the complete history of an opportunity for UI rendering.
    A single call — cheaper than five separate ones. Read-only."""
    record = get_opportunity(opportunity_id, db_path)
    if not record:
        return {}
    return {
        "record": record,
        "decisions": list_decisions_for_opportunity(opportunity_id, db_path),
        "blueprint_versions": list_blueprint_versions(opportunity_id, db_path),
        "scout_runs": list_scout_runs(opportunity_id, db_path),
        "revenue_history": revenue_history(opportunity_id, db_path),
        "notes": list_notes(opportunity_id, db_path),
    }

"""
opportunity_store.py — Atlas SaaS Persistence Layer

Purpose:
- Save generated opportunities
- Allow retrieval for dashboards
- Foundation for multi-user SaaS
"""

import sqlite3
import json
from typing import List, Dict, Any


DB_PATH = "atlas_opportunities.db"


# ─────────────────────────────────────────────
# INIT DB
# ─────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niche_name TEXT,
            score REAL,
            recommendation TEXT,
            confidence REAL,
            data TEXT
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# SAVE OPPORTUNITY
# ─────────────────────────────────────────────

def save_opportunity(opportunity: Dict[str, Any]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        INSERT INTO opportunities (
            niche_name,
            score,
            recommendation,
            confidence,
            data
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        opportunity["niche_name"],
        opportunity["score"],
        opportunity["recommendation"],
        opportunity["confidence"],
        json.dumps(opportunity)
    ))

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# LOAD OPPORTUNITIES
# ─────────────────────────────────────────────

def load_opportunities(limit: int = 50) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT data FROM opportunities
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = c.fetchall()
    conn.close()

    return [json.loads(r[0]) for r in rows]


# ─────────────────────────────────────────────
# CLEAR DB (DEV ONLY)
# ─────────────────────────────────────────────

def clear_opportunities():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DELETE FROM opportunities")

    conn.commit()
    conn.close()
-- Opportunity Engine v2 schema (drill runs, node tree, competitors, audits)
-- Coexists with v1 tables; safe to re-run.

CREATE TABLE IF NOT EXISTS drill_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seed_niche TEXT NOT NULL,
    mode TEXT DEFAULT 'heuristic',        -- heuristic | real
    config_json TEXT,                      -- serialized DrillConfig
    nodes_analyzed INTEGER,
    opportunities_found INTEGER,
    status TEXT DEFAULT 'running',
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS drill_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    parent_id INTEGER,                     -- REAL tree linkage (used in v2)
    niche_name TEXT NOT NULL,
    depth INTEGER,
    dimensions_json TEXT,                  -- {"geography":"Columbus","specialty":"birria",...}
    verdict TEXT,                          -- opportunity | drill_deeper | dead_end | budget_stopped
    verdict_reasons_json TEXT,

    competition REAL,
    business_count INTEGER,
    search_demand REAL,
    directory_weakness REAL,
    monetization REAL,
    automation_fit REAL,
    data_quality TEXT,                     -- heuristic | partial | verified

    opportunity_score REAL,
    revenue_low INTEGER,
    revenue_high INTEGER,
    revenue_confidence REAL,
    recommendation TEXT,
    revenue_streams_json TEXT,
    evidence_json TEXT,

    status TEXT DEFAULT 'new',             -- new | scouted | archived
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES drill_runs(id),
    FOREIGN KEY (parent_id) REFERENCES drill_nodes(id)
);

CREATE TABLE IF NOT EXISTS node_competitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    url TEXT, domain TEXT, title TEXT, snippet TEXT,
    category TEXT,                         -- platform_giant | independent | chamber_or_gov | listicle | other
    found_via_query TEXT,
    quality_score REAL,
    quality_grade TEXT,                    -- weak | moderate | strong | unknown
    audit_signals_json TEXT,
    monetization_json TEXT,
    audit_notes_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES drill_nodes(id)
);

CREATE INDEX IF NOT EXISTS idx_drill_nodes_run ON drill_nodes(run_id);
CREATE INDEX IF NOT EXISTS idx_drill_nodes_parent ON drill_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_drill_nodes_verdict ON drill_nodes(verdict);
CREATE INDEX IF NOT EXISTS idx_node_competitors_node ON node_competitors(node_id);

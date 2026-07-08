-- Opportunity Records persistence schema.
-- The opportunity is the permanent noun; decisions, blueprints, scout runs,
-- notes are all versioned children pointing at it.
-- Idempotent: safe to run repeatedly alongside existing Atlas tables.

-- =============================================================================
-- OPPORTUNITY RECORD: the permanent identity for a discovered opportunity
-- =============================================================================
CREATE TABLE IF NOT EXISTS opportunity_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,              -- lowercased, whitespace-normalized
    display_name TEXT NOT NULL,                -- original casing/spacing
    dna_slug TEXT NOT NULL,                    -- FK-in-spirit to opportunity_dna_profiles.slug
    asset_type TEXT,                           -- directory | category | lead_gen | ...
    ecosystem_node_name TEXT,                  -- if this maps to a DNA ecosystem node
    current_status TEXT DEFAULT 'unreviewed',  -- unreviewed | tracking | building | live | archived
    latest_recommendation TEXT,                -- BUILD | TEST | DEFER | REJECT (denormalized cache)
    latest_confidence REAL,                    -- denormalized cache of the most recent decision
    latest_data_quality TEXT,                  -- heuristic | verified | mixed
    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT,
    UNIQUE (dna_slug, canonical_name)
);
CREATE INDEX IF NOT EXISTS idx_opp_records_dna ON opportunity_records(dna_slug);
CREATE INDEX IF NOT EXISTS idx_opp_records_status ON opportunity_records(current_status);
CREATE INDEX IF NOT EXISTS idx_opp_records_last_analyzed ON opportunity_records(last_analyzed_at DESC);

-- =============================================================================
-- DECISIONS: every DecisionResult ever produced for the opportunity
-- Heuristic and verified coexist; latest is derived by ORDER BY created_at DESC.
-- =============================================================================
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    run_number INTEGER NOT NULL,               -- monotonically increasing per opportunity
    data_quality TEXT NOT NULL,                -- heuristic | verified | mixed
    recommendation TEXT NOT NULL,              -- BUILD | TEST | DEFER | REJECT
    confidence_score REAL NOT NULL,
    result_json TEXT NOT NULL,                 -- full DecisionResult (Pydantic model_dump_json)
    -- Snapshotted context so historical decisions stay interpretable even if
    -- the DNA profile is edited later:
    dna_profile_version TEXT,                  -- e.g. "1.0"
    dna_profile_snapshot_json TEXT,            -- full DNA at decision time
    scout_run_id INTEGER,                      -- FK to scout_runs when it exists
    blueprint_version_id INTEGER,              -- FK to blueprint_versions
    triggered_by TEXT DEFAULT 'manual',        -- manual | scheduled | scout_completed | dna_change
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (opportunity_id) REFERENCES opportunity_records(id)
);
CREATE INDEX IF NOT EXISTS idx_decisions_opp ON decisions(opportunity_id, run_number DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_recommendation ON decisions(recommendation);
CREATE INDEX IF NOT EXISTS idx_decisions_data_quality ON decisions(data_quality);
CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at DESC);

-- =============================================================================
-- BLUEPRINT VERSIONS: every SiteBlueprint ever generated for the opportunity
-- =============================================================================
CREATE TABLE IF NOT EXISTS blueprint_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    directory_name TEXT,
    lineage TEXT,
    total_pages INTEGER,
    counts_json TEXT,                          -- {"geo_categories": N, "categories": N, ...}
    assets_json TEXT NOT NULL,                 -- full serialized SiteBlueprint (all assets)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (opportunity_id) REFERENCES opportunity_records(id)
);
CREATE INDEX IF NOT EXISTS idx_bp_versions_opp ON blueprint_versions(opportunity_id, version_number DESC);

-- =============================================================================
-- SCOUT RUNS: forward-declared. Scout module doesn't exist yet, but its
-- linkage does — so when Scout lands, decisions can point at scout_runs.id
-- without a migration. Kept minimal on purpose.
-- =============================================================================
CREATE TABLE IF NOT EXISTS scout_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',             -- pending | running | complete | failed
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    verified_business_count INTEGER,
    verified_competitor_count INTEGER,
    findings_json TEXT,                        -- Scout's own output shape (TBD by that module)
    error TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunity_records(id)
);
CREATE INDEX IF NOT EXISTS idx_scout_runs_opp ON scout_runs(opportunity_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scout_runs_status ON scout_runs(status);

-- =============================================================================
-- COMPETITOR OBSERVATIONS: per scout run, competitors + quality audits.
-- Also forward-declared; matches the shape Phase 2/3 already produces.
-- =============================================================================
CREATE TABLE IF NOT EXISTS competitor_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scout_run_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    domain TEXT,
    category TEXT,                             -- independent | platform_giant | listicle | chamber_or_gov | other
    quality_score REAL,
    quality_grade TEXT,
    monetization_json TEXT,
    audit_signals_json TEXT,
    audit_notes_json TEXT,
    observed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scout_run_id) REFERENCES scout_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_competitor_obs_run ON competitor_observations(scout_run_id);

-- =============================================================================
-- REVENUE ESTIMATE HISTORY: track how the revenue estimate moves over time
-- as data quality improves. Decisions carry the full estimate too, but this
-- table makes trend queries cheap.
-- =============================================================================
CREATE TABLE IF NOT EXISTS revenue_estimate_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    decision_id INTEGER,
    revenue_low REAL,
    revenue_high REAL,
    confidence REAL,
    data_quality TEXT,
    estimated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (opportunity_id) REFERENCES opportunity_records(id),
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);
CREATE INDEX IF NOT EXISTS idx_rev_hist_opp ON revenue_estimate_history(opportunity_id, estimated_at DESC);

-- =============================================================================
-- NOTES: manual annotations on an opportunity (or on a specific decision)
-- =============================================================================
CREATE TABLE IF NOT EXISTS opportunity_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    decision_id INTEGER,                       -- optional: note about a specific decision
    author TEXT DEFAULT 'user',
    body TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (opportunity_id) REFERENCES opportunity_records(id),
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);
CREATE INDEX IF NOT EXISTS idx_notes_opp ON opportunity_notes(opportunity_id, created_at DESC);

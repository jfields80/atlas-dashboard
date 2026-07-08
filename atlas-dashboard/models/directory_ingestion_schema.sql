-- =====================================================================
-- Atlas Directory Data Ingestion & Seeding Engine — Schema (Phase 3B)
-- =====================================================================
-- Layered ON TOP of the existing Atlas schema. No existing table is
-- modified. All tables are namespaced with the di_ prefix
-- (directory ingestion) to avoid collisions.
--
-- JSON columns hold nested value objects (payloads, reports, provenance).
-- Business logic never lives here — repositories run raw SQL only.
-- =====================================================================

-- One row per ingestion run (mirrors PipelineRunner run semantics;
-- idempotency key = deterministic package hash).
CREATE TABLE IF NOT EXISTS di_ingestion_runs (
    run_id          TEXT PRIMARY KEY,
    directory_slug  TEXT NOT NULL,
    engine_name     TEXT NOT NULL,
    engine_version  TEXT NOT NULL,
    package_id      TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',   -- pending|complete|failed
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_di_runs_slug ON di_ingestion_runs (directory_slug);

-- Raw listings exactly as acquired.
CREATE TABLE IF NOT EXISTS di_raw_listings (
    raw_id          TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES di_ingestion_runs (run_id),
    source_type     TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    source_url      TEXT,
    payload_json    TEXT NOT NULL,          -- ordered field/value pairs
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_di_raw_run ON di_raw_listings (run_id);

-- Normalized listings (canonical Atlas format).
CREATE TABLE IF NOT EXISTS di_normalized_listings (
    listing_id      TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES di_ingestion_runs (run_id),
    raw_id          TEXT NOT NULL REFERENCES di_raw_listings (raw_id),
    business_name   TEXT NOT NULL,
    address         TEXT,
    city            TEXT,
    state           TEXT,
    zip_code        TEXT,
    country         TEXT,
    phone           TEXT,
    website         TEXT,
    email           TEXT,
    categories_json TEXT NOT NULL DEFAULT '[]',
    subcategories_json TEXT NOT NULL DEFAULT '[]',
    hours           TEXT,
    latitude        REAL,
    longitude       REAL,
    amenities_json  TEXT NOT NULL DEFAULT '[]',
    services_json   TEXT NOT NULL DEFAULT '[]',
    pricing_notes   TEXT,
    description     TEXT,
    seo_summary     TEXT,
    provenance_json TEXT NOT NULL DEFAULT '{}',   -- honesty layer tags
    source_type     TEXT NOT NULL,
    source_url      TEXT,
    confidence      REAL NOT NULL DEFAULT 0.0,
    verified        INTEGER NOT NULL DEFAULT 0,
    is_canonical    INTEGER NOT NULL DEFAULT 1,   -- 0 when merged away
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_di_norm_run   ON di_normalized_listings (run_id);
CREATE INDEX IF NOT EXISTS idx_di_norm_state ON di_normalized_listings (state, city);
CREATE INDEX IF NOT EXISTS idx_di_norm_canon ON di_normalized_listings (is_canonical);

-- Duplicate clusters.
CREATE TABLE IF NOT EXISTS di_duplicate_clusters (
    cluster_id              TEXT PRIMARY KEY,
    run_id                  TEXT NOT NULL REFERENCES di_ingestion_runs (run_id),
    canonical_listing_id    TEXT NOT NULL,
    confidence              REAL NOT NULL,
    merge_recommendation    TEXT NOT NULL,        -- AUTO_MERGE|REVIEW|KEEP_SEPARATE
    pairs_json              TEXT NOT NULL DEFAULT '[]',
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS di_duplicate_cluster_members (
    cluster_id  TEXT NOT NULL REFERENCES di_duplicate_clusters (cluster_id),
    listing_id  TEXT NOT NULL REFERENCES di_normalized_listings (listing_id),
    PRIMARY KEY (cluster_id, listing_id)
);

-- Quality scores, one per listing per run.
CREATE TABLE IF NOT EXISTS di_quality_scores (
    listing_id              TEXT NOT NULL REFERENCES di_normalized_listings (listing_id),
    run_id                  TEXT NOT NULL REFERENCES di_ingestion_runs (run_id),
    completeness            INTEGER NOT NULL,
    contact_quality         INTEGER NOT NULL,
    location_accuracy       INTEGER NOT NULL,
    seo_readiness           INTEGER NOT NULL,
    monetization_readiness  INTEGER NOT NULL,
    verification_quality    INTEGER NOT NULL,
    freshness               INTEGER NOT NULL,
    overall                 INTEGER NOT NULL,
    explanations_json       TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (listing_id, run_id)
);

CREATE INDEX IF NOT EXISTS idx_di_quality_overall ON di_quality_scores (overall);

-- Enrichment queue (future AI Employee jobs).
CREATE TABLE IF NOT EXISTS di_enrichment_tasks (
    task_id     TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES di_ingestion_runs (run_id),
    listing_id  TEXT NOT NULL REFERENCES di_normalized_listings (listing_id),
    task_type   TEXT NOT NULL,
    priority    TEXT NOT NULL,                    -- high|medium|low
    rationale   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending|in_progress|done|failed
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_di_tasks_status   ON di_enrichment_tasks (status, priority);
CREATE INDEX IF NOT EXISTS idx_di_tasks_listing  ON di_enrichment_tasks (listing_id);

-- Seed packages (immutable snapshots — Prediction Ledger style).
CREATE TABLE IF NOT EXISTS di_seed_packages (
    package_id      TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES di_ingestion_runs (run_id),
    directory_slug  TEXT NOT NULL,
    engine_name     TEXT NOT NULL,
    engine_version  TEXT NOT NULL,
    statistics_json TEXT NOT NULL,
    package_json    TEXT NOT NULL,                -- full serialized package
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_di_packages_slug ON di_seed_packages (directory_slug);

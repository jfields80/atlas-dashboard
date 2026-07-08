-- Atlas v3: Portfolio State Schema
-- Convention: additive only. Never ALTER existing tables destructively.
-- Applied via init_portfolio_schema() in portfolio_repository.py.

-- Asset lifecycle table.
-- status values: candidate | building | owned | exited | dead
-- revenue_value / revenue_confidence: persist the TaggedValue primitive.
--   source: VERIFIED | ESTIMATED | UNKNOWN  (mirrors DataSource enum)
CREATE TABLE IF NOT EXISTS portfolio_assets (
    asset_id            TEXT PRIMARY KEY,          -- UUID, assigned at creation
    niche_slug          TEXT NOT NULL,             -- e.g. "pet-friendly-travel"
    display_name        TEXT NOT NULL,             -- e.g. "PetTripFinder"
    domain              TEXT,                      -- e.g. "pettripfinder.com"
    dna_profile_json    TEXT,                      -- full DNA YAML serialised as JSON (nullable)
    primary_category    TEXT NOT NULL,             -- business category slug
    geographic_scope    TEXT NOT NULL DEFAULT 'national', -- local | regional | national | global
    monetization_model  TEXT,                      -- e.g. "listing_fees,lead_gen"
    status              TEXT NOT NULL DEFAULT 'candidate',
    -- TaggedValue for monthly revenue
    revenue_value       REAL NOT NULL DEFAULT 0.0,
    revenue_source      TEXT NOT NULL DEFAULT 'UNKNOWN',  -- VERIFIED|ESTIMATED|UNKNOWN
    revenue_provider    TEXT,
    revenue_rationale   TEXT,
    revenue_confidence  REAL NOT NULL DEFAULT 0.0,
    -- Timestamps (ISO-8601)
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    exited_at           TEXT,
    -- Free-form notes (investment committee memos, etc.)
    notes               TEXT
);

-- Immutable portfolio snapshots.
-- Once a row exists here it is never updated. status column is
-- informational only (active | superseded).
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    snapshot_id         TEXT PRIMARY KEY,          -- UUID
    created_at          TEXT NOT NULL,
    asset_count         INTEGER NOT NULL DEFAULT 0,
    owned_count         INTEGER NOT NULL DEFAULT 0,
    building_count      INTEGER NOT NULL DEFAULT 0,
    candidate_count     INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'active',  -- active | superseded
    notes               TEXT
);

-- Snapshot ↔ asset join — the record of exactly which assets (and their
-- state at snapshot time) belonged to each snapshot.
-- asset_state_json captures a serialised PortfolioAsset at snapshot time
-- so the snapshot is truly self-contained even if the live asset is mutated.
CREATE TABLE IF NOT EXISTS portfolio_snapshot_assets (
    snapshot_id         TEXT NOT NULL REFERENCES portfolio_snapshots(snapshot_id),
    asset_id            TEXT NOT NULL REFERENCES portfolio_assets(asset_id),
    asset_state_json    TEXT NOT NULL,             -- serialised PortfolioAsset at snapshot time
    PRIMARY KEY (snapshot_id, asset_id)
);

-- Asset status history — forward-only append log.
CREATE TABLE IF NOT EXISTS portfolio_asset_history (
    history_id          TEXT PRIMARY KEY,
    asset_id            TEXT NOT NULL REFERENCES portfolio_assets(asset_id),
    previous_status     TEXT,
    new_status          TEXT NOT NULL,
    changed_at          TEXT NOT NULL,
    changed_by          TEXT,                      -- run_id or 'manual'
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_portfolio_assets_status
    ON portfolio_assets(status);

CREATE INDEX IF NOT EXISTS idx_portfolio_assets_category
    ON portfolio_assets(primary_category);

CREATE INDEX IF NOT EXISTS idx_snapshot_assets_snapshot
    ON portfolio_snapshot_assets(snapshot_id);

CREATE INDEX IF NOT EXISTS idx_asset_history_asset
    ON portfolio_asset_history(asset_id);

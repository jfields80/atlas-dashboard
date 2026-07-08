-- Directory Blueprint storage schema (Atlas Phase 3)
-- Stores generated blueprints as immutable, versioned JSON documents.
-- This is the ONLY SQL in the subsystem, used exclusively by
-- repositories/directory_blueprint_repository.py.

CREATE TABLE IF NOT EXISTS directory_blueprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_slug TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    committee_recommendation TEXT NOT NULL,        -- BUILD or TEST
    data_confidence_tag TEXT NOT NULL,             -- VERIFIED / ESTIMATED / UNKNOWN
    blueprint_json TEXT NOT NULL,                  -- full DirectoryBlueprint document
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (project_slug, input_hash, engine_version)  -- idempotent writes
);

CREATE INDEX IF NOT EXISTS idx_directory_blueprints_slug
    ON directory_blueprints (project_slug);

CREATE INDEX IF NOT EXISTS idx_directory_blueprints_hash
    ON directory_blueprints (input_hash);

CREATE INDEX IF NOT EXISTS idx_directory_blueprints_created
    ON directory_blueprints (created_at);

# Migration Notes — Phase 3B

## Zero-touch guarantee

Phase 3B is **purely additive**. Verified against the frozen contract:

| Frozen asset | Status |
|---|---|
| `services/opportunity_v2/` | Untouched |
| `PipelineRunner` | Untouched |
| Existing repository pattern | Untouched (new repository added alongside) |
| Existing tables | Untouched — all new tables are `di_`-prefixed |
| 25/25 Phase 2 integration tests | Unaffected (no shared modules imported) |

`integration_changes/` is therefore intentionally empty: no existing file
requires modification for this subsystem to function.

## New files

```
engines/directory_ingestion/__init__.py
engines/directory_ingestion/ingestion_models.py
engines/directory_ingestion/source_planner.py
engines/directory_ingestion/listing_normalizer.py
engines/directory_ingestion/duplicate_detector.py
engines/directory_ingestion/quality_engine.py
engines/directory_ingestion/enrichment_generator.py
engines/directory_ingestion/seed_package_builder.py
engines/directory_ingestion/import_preparer.py
engines/directory_ingestion/extension_points.py
services/directory_ingestion_service.py
repositories/directory_ingestion_repository.py
models/directory_ingestion_schema.sql
tests/test_directory_ingestion.py
docs/directory_ingestion_engine.md
docs/directory_ingestion_README.md
docs/directory_ingestion_developer_guide.md
docs/directory_ingestion_migration_notes.md
docs/directory_ingestion_integration_guide.md
```

## Database migration

Run once against the existing Atlas SQLite database (idempotent —
every statement is `CREATE ... IF NOT EXISTS`):

```python
repo = DirectoryIngestionRepository(conn)
repo.ensure_schema()
```

or apply `models/directory_ingestion_schema.sql` with the sqlite3 CLI.
Eight new tables, all `di_`-prefixed:

`di_ingestion_runs`, `di_raw_listings`, `di_normalized_listings`,
`di_duplicate_clusters`, `di_duplicate_cluster_members`,
`di_quality_scores`, `di_enrichment_tasks`, `di_seed_packages`.

Rollback: `DROP TABLE` the eight `di_` tables. No other table references
them, so rollback is clean.

## Dependencies

None added. Standard library only (`sqlite3`, `json`, `csv`, `hashlib`,
`re`, `math`, `dataclasses`). Tests require `pytest` (already a dev
dependency).

## Notes for the pending Blueprint Engine integration

The ingestion engine consumes `BlueprintInput` — a deliberately small,
frozen contract — rather than importing Blueprint modules directly.
When the Blueprint Engine lands in this repo, write a one-way adapter
(Blueprint output → `BlueprintInput`) in the service layer. This keeps
the two subsystems decoupled and lets either version independently.
See `directory_ingestion_integration_guide.md`.

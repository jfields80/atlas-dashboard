# Directory Data Ingestion & Seeding Engine — README

Phase 3B subsystem for `atlas-dashboard`. Zero new dependencies
(standard library + pytest for tests). Python 3.10+.

## What extracts where

Extract the ZIP directly into `C:\Atlas\atlas-dashboard`:

```
engines/directory_ingestion/     ← 8 pure engine modules (new directory)
services/directory_ingestion_service.py
repositories/directory_ingestion_repository.py
models/directory_ingestion_schema.sql
tests/test_directory_ingestion.py
docs/directory_ingestion_*.md
```

No existing file is modified. `integration_changes/` is empty by design —
see `directory_ingestion_migration_notes.md`.

## Quickstart

```python
import sqlite3

from engines.directory_ingestion import (
    BlueprintInput, CategoryNode, LocationNode, RawListing, SourceType,
)
from repositories.directory_ingestion_repository import DirectoryIngestionRepository
from services.directory_ingestion_service import DirectoryIngestionService

# 1. Wire up (future: PipelineRunner owns this)
conn = sqlite3.connect("atlas.db")
repo = DirectoryIngestionRepository(conn)
repo.ensure_schema()                      # idempotent, additive
service = DirectoryIngestionService(repo)

# 2. Blueprint contract (adapter from real Blueprint Engine output)
blueprint = BlueprintInput(
    directory_slug="oh-dog-groomers",
    directory_name="Ohio Dog Groomers",
    category_hierarchy=(CategoryNode(slug="grooming", name="Grooming"),),
    location_hierarchy=(LocationNode(slug="oh", name="Ohio", level="state", state_code="OH"),),
    profile_schema_fields=("business_name", "address", "phone", "website"),
    search_keywords=("dog groomer ohio",),
)

# 3. Rank acquisition sources
plan = service.plan_sources(blueprint)
for rec in plan.recommendations[:3]:
    print(rec.rank, rec.source_type.value, rec.overall_score)

# 4. Ingest raw listings (from CSV, gov data, rosters, ...)
raws = [
    RawListing(
        raw_id="csv_0001",
        source_type=SourceType.CSV_IMPORT,
        source_name="ohio_groomers.csv",
        source_url=None,
        payload=(
            ("name", "Paws Club Grooming"),
            ("address", "123 Main St"), ("city", "Columbus"),
            ("state", "OH"), ("zip", "43004"),
            ("phone", "614-555-0101"), ("website", "pawsclub.com"),
        ),
    ),
]
result = service.run_ingestion(blueprint, raws)

print(result.package.package_id)
print(result.package.statistics)
print(len(result.package.enrichment_queue), "enrichment tasks queued")

# 5. Export import-ready artifacts
json_pkg = service.prepare_import(result.package, "json")
csv_pkg = service.prepare_import(result.package, "csv")
sql_pkg = service.prepare_import(result.package, "sqlite_staging")
```

## Running tests

```
cd C:\Atlas\atlas-dashboard
pytest tests/test_directory_ingestion.py -v
```

Expected: 49 passed. Fully offline — no APIs, no scraping.

## Import rules (repo convention)

```python
from engines.directory_ingestion import ListingNormalizer   # correct
from services.directory_ingestion_service import ...        # correct
from atlas.engines...                                       # NEVER
```

## Documentation index

| File | Contents |
|---|---|
| `directory_ingestion_engine.md` | Full engine reference + architecture/sequence/class diagrams |
| `directory_ingestion_developer_guide.md` | Extending mappings, rules, providers |
| `directory_ingestion_migration_notes.md` | Schema additions, zero-touch guarantee |
| `directory_ingestion_integration_guide.md` | PipelineRunner / Blueprint / Directory Builder wiring |

# Future Integration Guide

How the ingestion engine wires into the rest of Atlas, present and future.

## The pipeline position

```
Evaluate Opportunity      (Opportunity Engine v2 — DONE)
        ↓
Design Directory          (Blueprint Engine — DONE, integration pending)
        ↓
Acquire Business Data     (THIS SUBSYSTEM — Source Planner + providers)
        ↓
Normalize Listings        (THIS SUBSYSTEM)
        ↓
Prepare Import Package    (THIS SUBSYSTEM — SeedPackage + ImportPreparer)
        ↓
Future Directory Builder
        ↓
Future Website Generator
        ↓
Launch Business
```

## 1. Blueprint Engine → Ingestion (next integration step)

The ingestion engine's input contract is `BlueprintInput`
(`ingestion_models.py`). It intentionally does **not** import Blueprint
modules. When the Blueprint Engine lands in `atlas-dashboard`, add an
adapter in the service layer:

```python
# services/blueprint_ingestion_adapter.py  (future file)
def blueprint_to_ingestion_input(blueprint_output) -> BlueprintInput:
    return BlueprintInput(
        directory_slug=blueprint_output.slug,
        directory_name=blueprint_output.name,
        category_hierarchy=tuple(
            CategoryNode(slug=c.slug, name=c.name, parent_slug=c.parent,
                         keywords=tuple(c.keywords))
            for c in blueprint_output.categories
        ),
        location_hierarchy=tuple(
            LocationNode(slug=l.slug, name=l.name, level=l.level,
                         parent_slug=l.parent, state_code=l.state_code)
            for l in blueprint_output.locations
        ),
        profile_schema_fields=tuple(blueprint_output.profile_schema.fields),
        search_keywords=tuple(blueprint_output.search_blueprint.keywords),
        monetization_fields=tuple(blueprint_output.monetization.fields),
    )
```

One-way, pure, trivially testable. Field names above are illustrative —
map from whatever the canonical Blueprint payload exposes.

## 2. PipelineRunner integration

PipelineRunner remains the **sole orchestrator and database writer**.
`DirectoryIngestionService.run_ingestion` is designed to slot in as a
pipeline stage:

* Deterministic `run_id` (content hash of slug + raw ids).
* Idempotent replay: identical inputs short-circuit to the persisted run
  (`IngestionResult.replayed=True`) — same semantics as existing stages.
* Returns a frozen `IngestionResult` snapshot suitable for the
  Prediction Ledger.
* Connection lifecycle is injected (repository takes an open
  `sqlite3.Connection`), so PipelineRunner keeps ownership of
  transactions and the single-writer invariant.

Registration: add `("directory_ingestion", ENGINE_VERSION)` to the
Engine Version Registry when wiring the stage.

## 3. Ingestion → Future Directory Builder

The Directory Builder consumes a `SeedPackage` (or its persisted JSON via
`load_seed_package_json`). Contract highlights:

* `businesses` are canonical (duplicates already collapsed) and carry
  per-field provenance — the Builder must not display UNKNOWN fields as
  facts.
* `categories` / `locations` mirror the Blueprint hierarchies, so Builder
  page trees map 1:1.
* `quality_report` lets the Builder gate which listings ship at launch
  (suggested: `overall >= QUALITY_THRESHOLD`).
* `statistics.verified_count` feeds the Investment Committee's honest
  wall — a directory seeded entirely from ESTIMATED data should not
  unlock BUILD-grade confidence on its own.

## 4. Ingestion → Future AI Employees

`di_enrichment_tasks` **is** the AI Employee job queue:

* Workers claim `status='pending'` tasks (ordered priority → type).
* `EnrichmentTaskType` is the job type contract; `rationale` is the
  work order.
* Workers implement `LLMEnrichmentProvider` (`extension_points.py`) and
  return proposed field updates tagged **ESTIMATED only**. Promotion to
  VERIFIED requires an authoritative source or human confirmation —
  the honest wall extends into enrichment.
* Status transitions via `repository.update_task_status`
  (pending → in_progress → done|failed).

## 5. Future providers (Google Places, OSM, Yelp, ...)

Implement the reserved interfaces in `extension_points.py`. Providers:

1. return verbatim `RawListing` payloads (no in-provider cleaning),
2. never touch the database,
3. declare `ProviderCapabilities` so a future SourcePlanner v2 can rank
   from declared capabilities instead of editorial base scores.

Everything downstream of `RawListing` already works unchanged — a new
provider is a data faucet, not an architecture change.

## 6. Future Website Generator

The Website Generator never reads ingestion tables directly. It consumes
Directory Builder output, which consumes SeedPackages. Keep that chain:
each stage's contract is the previous stage's output artifact, exactly
like the existing Opportunity → Committee pipeline.

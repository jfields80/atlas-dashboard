# Directory Builder — Developer Guide

## Architectural contract

This subsystem follows the standing Atlas rules without exception:

- **Repositories: persistence only.** `LaunchPackageRepository` reads and parses launch package files into validated models. `ProjectAssemblyRepository` serializes validated models to deterministic CSV/JSON. Neither contains business logic. Launch packages and assemblies are file artifacts by contract, so no SQL exists in this subsystem; if a database-backed repository is ever added, raw SQL belongs there and nowhere else.
- **Services: orchestration only.** `DirectoryBuilderService` wires repositories and engines in a fixed order. It contains no computation and no serialization. No Flask objects.
- **Engines: pure deterministic computation.** No I/O, no clocks, no randomness, no framework imports. Every engine exposes a `VERSION` constant and a static `build(...)` that maps validated models to validated models.
- **Models: Pydantic, frozen.** Inputs (`engines/directory_builder/models.py`, Launch Package section) and outputs (same file, Project Assembly section) are immutable, so an assembly can be trusted end-to-end.
- **Imports are flat**: `from engines...`, `from services...`, `from repositories...`, `from core...`. Never `from atlas....`

## Pipeline order

The service executes engines in strict dependency order:

1. `ProjectStructureEngine` — directory plan from `PROJECT_DIRECTORIES`.
2. `ImportPackageEngine` — normalizes seeds into records. Dedup key is `(name, city, state)` case-insensitive; input is sorted before deduplication so the winner is order-independent. Unresolvable category/location references become empty-string IDs — resolved honestly by validation rather than guessed.
3. `SeoBuildEngine` — category, location, category×location, landing, and FAQ pages; internal linking (home → hubs, hubs ↔ cat×loc); trailing-slash 301 redirects; breadcrumbs; per-page-type sitemap plan; robots recommendations. Titles/meta truncated at named-constant lengths.
4. `ImagePackageEngine` — specifications only. Dimensions from `IMAGE_DIMENSIONS`, file names from `IMAGE_NAMING_STANDARD`.
5. `ContentBuildEngine` — planned editorial items + derived gaps: a description item per undescribed business, a metadata item per SEO page, an ALT-text item per image spec. Consumes the image package, so it runs after it.
6. `ImportValidationEngine` — duplicates, missing categories/locations (CRITICAL), broken relationships (CRITICAL), missing business metadata (INFO), missing SEO coverage (WARNING). `passed` is true iff zero criticals.
7. `AiBuildQueueEngine` — flattens planned tasks, content items, listing verification, and image collection into priority-sorted work units with `depends_on` references.
8. `QualityReportEngine` — six 0–100 sub-scores combined with explicit weights (sum to 1.0, asserted by test). Import score deducts fixed constants per critical/warning. Launch score is capped below `LAUNCH_NEEDS_WORK_THRESHOLD` while validation fails.
9. `ProjectStatusEngine` — readiness banding, remaining tasks (top 25 by priority), critical warnings, per-dimension progress, operator summary.
10. `BuildManifestEngine` — input fingerprint (sha256 of the canonical launch package JSON), clock-independent `build_id`, hash inventory of written files. The manifest is written *after* the artifacts it inventories and does not include itself.

## Determinism rules for contributors

- New IDs must go through `deterministic.deterministic_id(prefix, *parts)` with a canonical, lowercase key. Register the prefix in `constants.py`.
- Any collection that reaches a serializer must be sorted on a stable key first.
- Never read the clock inside an engine. Timestamps are injected by the service and appear only in the manifest.
- Every threshold, weight, deduction, and dimension is a named constant. If a reviewer can't point to the constant that produced a number, the change is wrong.
- Bumping behavior requires bumping the affected engine's `VERSION` and the subsystem `ENGINE_VERSION` if outputs change shape.

## Testing

```
pytest tests/directory_builder          # full suite (43 tests)
pytest tests/directory_builder/test_integration.py -k replay   # replay determinism only
```

The shared fixture (`conftest.write_demo_launch_package`) intentionally contains one duplicate business and one business with an undefined category so the validation and gating paths are always exercised. When adding an engine, add: a unit test for its happy path, a determinism test (`build(x) == build(x)`), and an integration assertion that its artifact lands on disk.

## Adding a new artifact type

1. Model it in `engines/directory_builder/models.py` (frozen).
2. Compute it in a new or existing engine (pure).
3. Serialize it in `ProjectAssemblyRepository.write_assembly` via the `w(...)` helper so it enters the manifest automatically.
4. Test all three layers.

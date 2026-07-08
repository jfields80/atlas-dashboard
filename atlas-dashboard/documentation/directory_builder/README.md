# Directory Builder Engine

The Directory Builder is Atlas's deterministic Project Manufacturing Engine. It consumes a Launch Package produced by the (frozen) Launch Kit Generator and assembles a complete Project Assembly — import-ready data, a full SEO surface, content and image work specifications, validation and quality reports, and an executable AI build queue — without generating a website and without knowing which framework will eventually consume the output.

```
Launch Package → Directory Builder → Project Assembly → Website Generator (future)
```

The Builder is completely business-agnostic. PetTripFinder, DirectBeef, SkilledTradePathway, and any other Atlas project are validation datasets only; nothing about any specific business is hardcoded anywhere in this subsystem.

## Quick start

```python
from repositories.directory_builder import LaunchPackageRepository, ProjectAssemblyRepository
from services.directory_builder_service import DirectoryBuilderService

service = DirectoryBuilderService(
    LaunchPackageRepository(),
    ProjectAssemblyRepository("projects"),
)
result = service.build_project("launch_packages/my-directory")

print(result.project_path)                       # projects/my-directory
print(result.assembly.quality.overall_score)     # 0–100, fully explained
print(result.assembly.status.launch_readiness)   # READY / NEEDS_WORK / NOT_READY
```

Run the tests from the repository root:

```
pytest tests/directory_builder
```

43 tests: unit coverage per engine plus full-pipeline integration tests including a byte-identical replay test.

## Input: the Launch Package

A directory containing `blueprint.json` (mandatory) and up to ten optional files: `seed_businesses.json`, `categories.json`, `locations.json`, `url_map.csv`, `seo_pages.csv`, `content_plan.csv`, `monetization_plan.json`, `ai_task_queue.csv`, `launch_checklist.md`, `operator_notes.md`. Missing optional files are never fatal — they are recorded in `LaunchPackage.missing_files` and lower the completeness score honestly rather than being silently ignored.

## Output: the Project Assembly

Written under `projects/<project_slug>/`:

```
projects/<slug>/
  config/project.json
  database/                      (reserved for the future Website Generator)
  imports/                      businesses, categories, locations, relationships,
                                tags, amenities + 9 header-only scaffold tables
                                (reviews, claims, premium_listings, articles,
                                events, coupons, jobs, faqs, media_references)
  seo/                          pages.csv, internal_links.csv, redirects.csv,
                                breadcrumbs.json, sitemap_plan.json,
                                robots_recommendations.md
  content/content_queue.csv     deterministic AI content work items
  assets/images/                image_specifications.csv (specs only, no images)
  tasks/ai_build_queue.{csv,json}
  reports/                      validation_report, quality_report, project_status
  logs/  exports/  assets/templates/  documentation/
  build_manifest.json           hash-verified inventory of every artifact
  project_summary.json
  launch_status.json
```

## Determinism guarantees

- Every ID is derived from a sha256 of a canonical key (`BIZ-`, `CAT-`, `PAGE-`, `WU-`, …). Never positional, never random.
- All collections are sorted on stable keys before serialization; JSON is written with sorted keys, LF newlines, UTF-8.
- `build_id` is derived from the input fingerprint plus engine version and is clock-independent. Passing a fixed `built_at` to `build_project` reproduces byte-identical builds — this is asserted by an integration test.
- Every quality score is computed from named constants in `engines/directory_builder/constants.py` and ships with a plain-English explanation.

## Honesty layer

Validation findings never block a build; they are surfaced and enforced downstream: any critical finding fails validation, caps the launch readiness score below the NEEDS_WORK threshold, and forces project status to NOT_READY. Problems reduce scores; they are never hidden.

## Layout in the repository

```
engines/directory_builder/models.py       Pydantic models (frozen, validated)
engines/directory_builder/         pure deterministic computation
repositories/directory_builder/    file persistence only
services/directory_builder_service.py   orchestration only
tests/directory_builder/           43 unit + integration tests
documentation/directory_builder/   this file, developer guide, diagrams
```

See `DEVELOPER_GUIDE.md` for engine-by-engine detail, `ARCHITECTURE.md` for diagrams, and `EXTENSION_POINTS.md` for how the future Website Generator plugs in without modifying the Builder.

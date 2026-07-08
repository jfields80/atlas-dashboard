# Directory Intelligence & Blueprint Engine

**Atlas Phase 3 — subsystem developer guide**
Engine: `directory_blueprint` · Version: `1.0.0`

## What this subsystem does

Atlas Phase 2 answers *"Should we build this?"* This subsystem answers *"Here is exactly how this directory should be structured, launched, monetized, and scaled."*

Given the outputs of the existing pipeline — opportunity evaluation, market capacity, portfolio context, expansion classification, and the Investment Committee recommendation — it generates a complete, validated, persistable **Directory Blueprint** with twelve sections: project profile, directory architecture, database blueprint, business profile schema, search experience, monetization plan, SEO blueprint, content strategy, AI content task definitions, implementation roadmap, risk analysis, and project scorecard.

It does **not** build websites, write listing SQL, call AI models, or touch the frozen v3 pipeline. It is a planning engine that a future execution subsystem consumes.

## The gate

Blueprints are generated **only** when the committee recommendation is `BUILD` or `TEST`. The gate is enforced twice, deliberately:

1. **Engine boundary** — `generate_blueprint()` raises `ValueError` for any other recommendation. The engine cannot be tricked into planning an unapproved build.
2. **Service boundary** — `generate_and_store_blueprint()` returns a `NOT_ELIGIBLE` result without raising, so pipeline callers can log the decision cleanly.

This mirrors the honest-wall philosophy: unverified market data doesn't block blueprint generation (a `TEST` build is exactly how data gets verified), but it is surfaced everywhere — the blueprint carries a `data_confidence_tag`, the risk analyzer raises monetization and data-acquisition risk for non-`VERIFIED` inputs, the scorecard applies an unverified-data readiness penalty, and `generation_notes` states it in plain language.

## Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │       services/directory_blueprint_service   │
                         │  gate → validate → generate → persist        │
                         │  (zero SQL, no Flask)                        │
                         └───────┬─────────────────────────┬───────────┘
                                 │                         │
              engine call        │                         │  raw SQL only
                                 ▼                         ▼
        ┌────────────────────────────────┐   ┌──────────────────────────────────┐
        │ engines/directory_blueprint/   │   │ repositories/                    │
        │   blueprint_generator          │   │   directory_blueprint_repository │
        │   (pure, deterministic, no IO) │   │   (sqlite3, idempotent inserts)  │
        └───────┬────────────────────────┘   └──────────────┬───────────────────┘
                │ orchestrates                              │
                ▼                                           ▼
   category_planner   seo_planner              models/directory_blueprint_schema.sql
   monetization_planner   roadmap_planner
   risk_analyzer      (all pure functions)
```

### Class / model diagram (abridged)

```
BlueprintRequest
 ├── OpportunityInput          (name, niche, score, scope, competition, ...)
 ├── MarketCapacityInput       (listings, liquidity, data_tag ∈ {VERIFIED,ESTIMATED,UNKNOWN})
 ├── PortfolioContextInput     (existing_assets[], synergy_score)
 ├── ExpansionClassificationInput (NEW_MARKET | ADJACENT | CLONE, template_asset?)
 └── CommitteeInput            (BUILD | TEST | WATCH | PASS, confidence, rationale)

DirectoryBlueprint
 ├── engine_version, input_hash, data_confidence_tag, generation_notes[]
 ├── ProjectProfile            (slug, domains, type, monetization, complexity)
 ├── DirectoryArchitecture     (CategoryNode tree, LocationHierarchy, NavigationNode tree,
 │                              url_hierarchy, canonical_strategy, tags/amenities/attributes)
 ├── DatabaseBlueprint         (TableSpec[14+], RepositoryInterfaceSpec[])
 ├── BusinessProfileSchema     (FieldSpec[21])
 ├── SearchExperiencePlan
 ├── MonetizationPlan          (13 ranked MonetizationOption)
 ├── SEOBlueprint              (KeywordCluster[], programmatic opportunities)
 ├── ContentStrategy
 ├── AIContentTaskPlan         (10 AIContentTask definitions — no implementation)
 ├── ImplementationRoadmap     (8 RoadmapPhase, dependency-ordered)
 ├── RiskAnalysis              (7 RiskAssessment + overall)
 └── ProjectScorecard          (10 scores, 1-10, with explanations dict)
```

### Sequence — generate and store

```
Caller                Service                     Engine                    Repository
  │  payload/request     │                           │                          │
  ├─────────────────────►│                           │                          │
  │                      │ is_blueprint_eligible?    │                          │
  │                      ├──────────────────────────►│                          │
  │                      │  (WATCH/PASS → NOT_ELIGIBLE result, stop)            │
  │                      │ generate_blueprint(req)   │                          │
  │                      ├──────────────────────────►│                          │
  │                      │        DirectoryBlueprint │                          │
  │                      │◄──────────────────────────┤                          │
  │                      │ ensure_schema / find_by_input_hash                   │
  │                      ├─────────────────────────────────────────────────────►│
  │                      │  (hash match → DUPLICATE result with stored doc)     │
  │                      │ insert_blueprint (INSERT OR IGNORE)                  │
  │                      ├─────────────────────────────────────────────────────►│
  │   GENERATED result   │                           │                          │
  │◄─────────────────────┤                           │                          │
```

## Determinism and explainability

- **No randomness anywhere.** Identical `BlueprintRequest` → byte-identical blueprint JSON (covered by `TestDeterminism`).
- **Input hash.** SHA-256 over the canonical sorted-key JSON of the request, computed by `blueprint_generator.compute_input_hash`. This is a local implementation so the subsystem runs standalone; at integration time it can be swapped for `core.input_hash` if the signatures align.
- **Named constants only.** Every score adjustment (liquidity penalties, competition boosts, scope multipliers, clone discounts, risk bands) is a module-level constant, and every monetization option and scorecard entry carries a rationale/explanation string reconstructing its arithmetic.
- **Idempotent persistence.** `UNIQUE(project_slug, input_hash, engine_version)` plus `INSERT OR IGNORE` means replays are safe; the service surfaces replays as `DUPLICATE` results carrying the originally stored document.

## Public API

```python
from engines.directory_blueprint import (
    BlueprintRequest, OpportunityInput, MarketCapacityInput,
    PortfolioContextInput, ExpansionClassificationInput,
    CommitteeInput, CommitteeRecommendation,
    generate_blueprint, is_blueprint_eligible,
)
from services import directory_blueprint_service as blueprint_service

request = BlueprintRequest(
    opportunity=OpportunityInput(
        name="Ohio Dog Groomer Finder",
        niche="dog grooming services",
        score=72.0,
        confidence=0.45,
    ),
    committee=CommitteeInput(recommendation=CommitteeRecommendation.TEST, confidence=0.45),
)

# Pure engine call (no persistence):
blueprint = generate_blueprint(request)

# Full orchestration (persistence, idempotency):
import sqlite3
conn = sqlite3.connect("atlas.db")
result = blueprint_service.generate_and_store_blueprint(conn, request)
if result.generated:
    print(result.blueprint.project_profile.suggested_domains)
```

Raw pipeline dicts can go straight to `blueprint_service.generate_and_store_from_payload(conn, payload)`; Pydantic validation happens at the boundary.

Functional APIs are canonical. `BlueprintGenerator`, `DirectoryBlueprintService`, and `DirectoryBlueprintRepository` classes exist only as compatibility shims.

## Pydantic v1/v2 compatibility

All version-sensitive operations are isolated in `engines/directory_blueprint/pydantic_compat.py` (`model_to_dict`, `model_to_json`, `model_from_dict`, `model_from_json`, forward-ref rebuilding). The rest of the subsystem never calls `.dict()`/`.model_dump()` directly and never uses validators, so it runs unmodified on either major version.

## Architecture contract compliance

| Rule | How it's met |
|---|---|
| Raw SQL only in repositories | Single repository module; sqlite3 + schema file; no SQL anywhere else |
| Services: zero SQL, no Flask | Service imports only engine + repository functions |
| Engines: deterministic, no DB writes, no Flask | All planners are pure functions of their inputs |
| No modification to `services/opportunity_v2/` or `pipeline_runner.py` | Zero imports from, and zero changes to, frozen modules |
| Functional APIs canonical | Class wrappers documented as shims |
| Complete files, no placeholders | Everything ships runnable; 48 tests pass |

## Running the tests

```
python -m pytest tests\test_directory_blueprint.py -v
```

No Flask, no PipelineRunner, no network. Requires only `pydantic` and `pytest`.

## Future extension points

1. **PipelineRunner integration.** Add a Phase-3 step after the Investment Committee: build the payload from pipeline outputs, call `generate_and_store_from_payload`, and record the returned `blueprint_id` in the Prediction Ledger snapshot. No engine changes required.
2. **Engine version registry.** Register `directory_blueprint == 1.0.0` in `core/engine_versions.py` (see `integration_changes/README.md`). Bump the version on any constant change so old blueprints remain attributable.
3. **v2 type adapter.** A thin `services/blueprint_input_adapter.py` mapping `v2_types` outputs onto `BlueprintRequest` fields keeps this subsystem decoupled from committee internals.
4. **Execution subsystem.** The `DatabaseBlueprint` table specs and `AIContentTaskPlan` task definitions are deliberately machine-readable so a future "Directory Builder" can consume them directly.
5. **Template learning.** For `CLONE` classifications, a future enhancement can load the template asset's stored blueprint and diff rather than regenerate from scratch.
6. **Blueprint diffing.** Because blueprints are immutable and hash-keyed, a `compare_blueprints(a, b)` utility can show exactly how a re-scored opportunity changed the plan.

# Directory Builder — Future Extension Points

The Builder's job ends at the Project Assembly. A future Website Generator consumes that assembly without any change to the Builder. These are the designed seams.

## 1. The Project Assembly is the contract

The on-disk layout under `projects/<slug>/` — plus `build_manifest.json` — is the sole interface between Builder and Generator. A Website Generator should:

1. Read `build_manifest.json`, verify every file hash, and refuse to build from a tampered or partial assembly.
2. Read `launch_status.json` and refuse to generate while `launch_readiness == "NOT_READY"` (mirrors the honesty-layer gate: no builds on unvalidated data).
3. Consume `imports/*.csv` for data, `seo/seo_build_package.json` for routes/canonicals/breadcrumbs, `content/` and `tasks/` for remaining work, and `assets/images/image_specifications.csv` for media expectations.

Because the contract is files + manifest, the Generator can be Flask, Django, Next.js, a static-site generator, or an external tool in another language — the Builder neither knows nor cares.

## 2. Reserved directories

`database/`, `exports/`, `logs/`, `assets/templates/`, and `documentation/` are created empty by the structure plan and reserved for downstream stages (e.g., the Generator materializes `database/` from `imports/`, renders templates into `assets/templates/`). The Builder will never write into them, so downstream ownership is unambiguous.

## 3. Stable, versioned IDs

Every record and page carries a deterministic ID derived from content, not position. A Generator (or an incremental re-generator) can diff two assemblies of the same project and update only changed records — IDs survive re-builds as long as the underlying entity is unchanged. `build_manifest.json.input_fingerprint` tells the Generator instantly whether anything upstream changed at all.

## 4. Adding new artifact types without breaking consumers

New artifacts are additive: new files under existing directories plus new manifest entries. Consumers that verify by manifest and read only the files they understand remain forward-compatible. Removing or renaming an artifact is a breaking change and requires bumping `ENGINE_VERSION` (major) and coordinating with Generator versions via the Engine Version Registry entries exposed in `engines.directory_builder.ENGINE_VERSIONS`.

## 5. Alternate persistence backends

`ProjectAssemblyRepository` is the only component that knows the assembly lives on a local filesystem. A future S3/object-store repository can implement the same two methods (`write_assembly`, `write_manifest`) and be injected into `DirectoryBuilderService` unchanged — the service depends only on the repository interface, never on paths.

## 6. Alternate launch package sources

Symmetrically, `LaunchPackageRepository.load` is the only reader. A repository that assembles a `LaunchPackage` from the Atlas database (via existing frozen pipelines) instead of files can be injected without touching engines or service.

## 7. Work queue executors

`tasks/ai_build_queue.json` is designed as an executor contract: each unit is self-contained (`unit_id`, `unit_type`, `instructions`, `priority`, `depends_on`). A future AI Task Executor can claim units, execute them, and write results back into the project's `content/` and `assets/` areas — then a Builder re-run will detect the filled gaps (fewer missing descriptions, fewer validation infos) and quality scores rise deterministically. The Builder itself needs no changes to support this loop.

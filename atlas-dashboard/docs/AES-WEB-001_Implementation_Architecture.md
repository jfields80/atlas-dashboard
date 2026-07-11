
/
Atlas Website Builder
Atlas Website Builder







Recents
Environment verification and phase 1 deployment
12 hours ago
Phase 1 implementation starting
13 hours ago
Atlas dashboard repository structure investigation
14 hours ago
AES-WEB-001 attachment missing from uploads
16 hours ago
Implementation architecture design decisions
16 hours ago
Ten-plane architectural blueprint
16 hours ago
Instructions
Add instructions to tailor Claude’s responses

Memory
Only you
Purpose & context Jon is the Chief Architect / principal authority for Atlas Investment OS, a platform for managing niche directory websites as investment assets. His current focus is the Website Generation Engine (WGE) — a system for autonomously generating commercially viable directory websites at portfolio scale. The first target is a pet travel directory. Atlas follows a strict engineering governance model: formal architectural specification documents (AES-WEB-00x series), Investment Committee oversight, binding LaunchCertificates before deployment, and a constitutional separation between deterministic subsystems (routing, linking, compilation, quality gates — never AI) and AI cognition cells (writers, designers, reviewers — sealed, replayable, versioned, artifact-only collaboration). Jon communicates in formal engineering-governance style: precise document IDs, version references, and directive instruction blocks. He expects compliance without paraphrase or improvisation, and verification over inference. Current state The WGE implementation is mid-stream in its multi-wave architecture: AES-WEB-001 (Implementation Architecture) — produced and used as the binding upstream authority document. Defines the Phase 1 foundation: contracts package, constants, speccompiler, pipeline state machine, artifact store, build state repository. AES-WEB-002 (Commercial Component System Architecture) — produced (~20,500 words, sections 0–35). Approved by Jon. Defines 72 MVP components across seven waves, full gate catalog, accessibility severity policy (serious failures = BLOCKING), and four required AES-WEB-001 amendments (batched as v1.1.0): A1 (SelectionTrace embedded in ComponentManifest), A2 (accessibility gate severity elevation), A3 (import-audit whitelist extension), A4 (Phase 2 roadmap clarification). Phase 1 implementation — executed in a GitHub Actions / Claude Code environment against jfields80/atlas-dashboard. Produced 35 new files, 135 tests, 912 passing, golden BuildManifest hash reproduced byte-identically. Delivered as patch file + ZIP. Pre-AES-WEB-002A amendments (A1–A4) — preflight run; environment mismatch blocked execution (Linux sandbox, no access to C:\Atlas\atlas-dashboard Windows repo). Analytical implementation plans were completed for all four amendments: A1 uses typed Pydantic SelectionTrace with plain int scores (additive only, per §14.2); A3 scope is authorization-only, physical file creation deferred to AES-WEB-002A. Awaiting proper environment (Claude Code with direct filesystem access, or zip upload). On the horizon Execute A1–A4 amendments in a compatible environment (Claude Code session with C:\Atlas\atlas-dashboard access, or zip upload workflow) AES-WEB-002A — Contracts and Registry Foundation (first coding task post-amendments) AES-WEB-003 through AES-WEB-006 — recommended next specification documents in the series Key learnings & principles Verification over inference: Claude must explicitly verify file uploads, repository access, and environment state rather than assuming success from prior messages. Silent failures have occurred (e.g., uploads that appeared sent but weren't). Stop rules are binding: Preflight checklists define hard stop conditions; Claude halted and reported rather than fabricating git output or test results when the environment didn't match. Determinism airlock: AI output enters the pipeline only as validated, hashed artifacts — never as raw generation directly influencing deterministic subsystems. No fabrication of completions: Unimplemented pipeline stages are recorded as NOTEXECUTED, not fabricated. pydantic v1/v2 isolation: The codebase targets pydantic 1.10.x; a v2 environment mismatch was resolved by version downgrade. The v1/v2 isolation shim lives within contracts, not crossing engine boundaries. external: prefix exemption: Artifact store upstream source hashes use this prefix policy for external dependencies. AES-005A gate lesson: Quality gates require both good and bad fixtures per gate to avoid false positives — baked into testing strategy. Revenue before capability: A recurring strategic caution — the engine's most dangerous failure mode is manufacturing capability that outruns market contact (grounded in Atlas's $0-revenue first directory history). Phases 1–3 produce revenue-capable output from fixture content before AI cognition is activated in Phase 4. Approach & patterns All work is grounded in cited authority sections from formal AES-WEB-00x documents; amendments reference exact section numbers. Architecture documents are produced in two-pass review cycles (first half for directional approval, second half completed without interruption once approved). Large file delivery uses sequential heredoc appends (~2,000–4,000 word chunks) to a working path, then copied to outputs at completion. Internal consistency is verified via inline Python regex scripts before delivery. Repository navigation note: cloning jfields80/atlas-dashboard produces a nested structure (atlas-dashboard/atlas-dashboard/); the actual project root is one level deeper than expected. Jon issues instructions as bracketed COPY TO CLAUDE blocks and expects literal compliance. Tools & resources Repository: jfields80/atlas-dashboard (GitHub, public) Local codebase: C:\Atlas\atlas-dashboard (Windows) Execution environments: Claude Code (preferred for filesystem tasks), GitHub-connected sandbox Core documents: AES-WEB-001ImplementationArchitecture.md, AES-WEB-002 (Commercial Component System), AtlasWebsiteGenerationArchitecture_Index.md Stack: Python, Pydantic 1.10.x, SQLite, pytest

Last updated 9 hours ago

Context
38% of project capacity used
Search mode

jfields80/atlas-dashboard
main

GITHUB



website_generation_engine_architecture (2).md
726 lines

md



AES-WEB-002 — Commercial Component System Architecture (1).md
1,479 lines

md



AES-WEB-001_Implementation_Architecture.md
718 lines

md



Atlas Website Generation Architecture Index.md
631 lines

md


Scheduled
Set up recurring tasks for this project.

AES-WEB-001_Implementation_Architecture.md


Atlas Investment OS
AES-WEB-001 — Website Generation Engine
Implementation Architecture Specification
Field	Value
Document ID	AES-WEB-001-IMPL
Status	Design Authority — Implementation Specification
Version	1.0.0
Date	2026-07-10
Supersedes	None
Governs	All future Website Generation Engine coding tasks
Upstream Authorities	Website Generation Engine Master Blueprint; Atlas Platform Architecture; Opportunity Intelligence Engine; Directory Builder Engine; Investment Committee; Project Assembly System
Downstream Consumers	Claude Code implementation sessions; regression suite; operator runbooks
Authority statement. This document converts the Master Architectural Blueprint into an engineering-ready specification. Where the Master Blueprint defines what the Website Generation Engine (WGE) is, this document defines how it is built inside Atlas. In any conflict between this document and an implementation session, this document wins. In any conflict between this document and the Master Blueprint's intent, the Master Blueprint's intent wins and this document must be amended by version bump — never silently.

Binding Atlas invariants (restated, non-negotiable). Everything below inherits the established Atlas engineering discipline:

Flat imports only: from engines..., from repositories..., from services....
Engines are pure and deterministic: no AI calls, no I/O, no network, no UUIDs, no wall-clock reads. All time enters as an explicit parameter (generated_at); all identity is content-derived (SHA-256).
Repositories own persistence (SQL and file storage) and nothing else.
Services own orchestration, I/O sequencing, and AI invocation and nothing else.
All models are frozen Pydantic, compatible with the pydantic_compat.py isolation layer.
Zero-touch on existing files unless a task explicitly authorizes modification.
Complete files only; ZIP delivery staged in a temp directory and zipped from within it; delivery is not "confirmed" until extraction is confirmed.
Every part ships with tests; the full regression suite gates every delivery; zero regressions tolerated.
Part 1 — Engineering Philosophy
1.1 Architectural principles
Determinism as the spine, cognition as an organ. The WGE is a deterministic manufacturing pipeline into which AI-produced material is admitted only as validated, immutable artifacts. The pipeline never "talks to" a model mid-flight. A model produces a candidate artifact; the artifact is validated, hashed, and persisted; only then does the deterministic pipeline consume it. This single rule is what makes builds replayable, testable, and auditable, and it is the most important sentence in this document.

Artifact-driven architecture. Every stage boundary is an artifact boundary. Stages communicate exclusively through versioned, schema-validated, content-addressed artifacts — never through shared mutable state, never through side channels. If two stages need to exchange information, that information is an artifact with a contract, an owner, and a hash.

Contract-first design. Contracts (Pydantic models plus semantic rules) are written, reviewed, and frozen before the engines that produce or consume them. A contract change is a versioned event (§4.6), never an in-place edit.

Replayability. Given the same input artifacts, the same engine versions, and the same recorded AI transcripts, a build must reproduce byte-identical output with an identical BuildManifest hash. Replayability is not a testing convenience; it is the audit mechanism that lets Atlas certify what was actually built for each directory asset.

Smallest viable increments. The Master Blueprint spans a decade. Implementation proceeds in phases (Part 13) where every phase ends with a working, gated, regression-protected system. No phase may depend on a future phase to be correct.

1.2 Separation of concerns
Four vertical layers, mirroring the rest of Atlas:

Layer	Owns	Forbidden
Engines (engines/website_generation/...)	Pure transformation: artifact in → artifact out	I/O, SQL, AI calls, Flask, clocks, randomness
Repositories (repositories/...)	SQLite tables, file layout, content-addressable store, manifests, caching	Business logic, orchestration, AI
Services (services/...)	Orchestration, sequencing, AI cognition cells, retries, escalation	SQL, rendering logic, scoring logic
Scripts (scripts/...)	Operator entry points (CLI runners)	Anything beyond argument parsing + service invocation
1.3 Deterministic vs AI responsibilities
Deterministic (engines): spec compilation, brand token resolution, IA planning from spec rules, component selection, layout composition, rendering, SEO metadata assembly, quality gating, bundle assembly, manifest generation.

AI (cognition cells, in services): copywriting, content enrichment, tone adaptation, alt-text drafting, meta-description drafting, and checker-cell review. AI output is always a candidate; determinism resumes at validation.

The litmus test for any new capability: if it must produce the same output twice, it is an engine; if it may legitimately vary, it is a cognition cell, and its output must be frozen into an artifact before the pipeline proceeds.

1.4 Dependency inversion
Engines depend on contracts, never on repositories or services. Services depend on engine public interfaces and repository public interfaces. Repositories depend only on contracts and the standard library / storage driver. Deployment targets and AI model providers are reached through abstract adapter interfaces defined in contracts and implemented at the edges. Nothing in the core imports a vendor SDK.

1.5 Repository pattern and service pattern
As already established across Atlas (Phase 3, 3B, 4, AES-005A): each repository class owns exactly one storage concern and exposes typed methods returning frozen models; each service class owns exactly one workflow and composes engines + repositories. The WGE adds one pattern refinement: the content-addressable artifact store (§9.3), a repository whose keys are SHA-256 hashes of canonical artifact serializations, giving deduplication, integrity verification, and cache correctness for free.

1.6 Testability
Every engine is testable with in-memory fixtures and no mocks. Every repository is testable against a temp directory / temp SQLite file. Every service is testable with recorded AI transcripts (replay mode, §7.6) so the entire pipeline runs in CI with zero network access and zero model cost. Golden builds (§11.5) pin end-to-end byte-identity.

Part 2 — Complete Package Layout
The WGE does not introduce a new top-level tree. It lives inside the established Atlas layout so flat imports remain uniform. Layout below is normative; deviations require a version bump of this document.

atlas-dashboard/
├── engines/
│   └── website_generation/
│       ├── __init__.py                  # Public surface: pipeline + engine classes only
│       ├── contracts/
│       │   ├── __init__.py
│       │   ├── artifacts.py             # All artifact models (frozen Pydantic)
│       │   ├── interfaces.py            # Abstract engine/adapter interfaces (Protocols/ABCs)
│       │   ├── enums.py                 # BuildState, GateSeverity, ArtifactKind, etc.
│       │   ├── errors.py                # Typed exception hierarchy
│       │   └── versions.py              # SCHEMA_VERSIONS registry, ENGINE_VERSIONS registry
│       ├── constants/
│       │   ├── __init__.py
│       │   ├── build.py                 # Stage order, retry ceilings, size limits
│       │   ├── brand.py                 # Token taxonomies, default scales
│       │   ├── seo.py                   # Metadata length limits, schema.org types
│       │   └── gates.py                 # Gate IDs, thresholds, severities
│       ├── speccompiler/
│       │   ├── __init__.py
│       │   └── business_spec_compiler.py    # Upstream Atlas outputs → BusinessSpec
│       ├── brand/
│       │   ├── __init__.py
│       │   ├── brand_engine.py              # BusinessSpec → BrandPackage
│       │   └── token_resolver.py            # Palette/typography/spacing resolution
│       ├── ia/
│       │   ├── __init__.py
│       │   └── information_architecture_engine.py  # Spec+Brand → SiteArchitecture
│       ├── content/
│       │   ├── __init__.py
│       │   ├── content_engine.py            # Deterministic content assembly/normalization
│       │   └── content_validators.py        # Structural + policy validation of ContentPackage
│       ├── components/
│       │   ├── __init__.py
│       │   ├── component_engine.py          # IA+Content → ComponentManifest
│       │   └── registry.py                  # Component catalog (data, not code-gen)
│       ├── layouts/
│       │   ├── __init__.py
│       │   └── layout_engine.py             # ComponentManifest → LayoutPlan per page
│       ├── rendering/
│       │   ├── __init__.py
│       │   ├── renderer.py                  # LayoutPlan+Brand+Content → rendered pages
│       │   ├── html_emitter.py              # Escaped, deterministic HTML emission
│       │   └── css_emitter.py               # Token-driven stylesheet emission
│       ├── seo/
│       │   ├── __init__.py
│       │   └── seo_engine.py                # SiteArchitecture+Content → SEOPackage
│       ├── assembly/
│       │   ├── __init__.py
│       │   └── assembly_engine.py           # Pages+assets+SEO → SiteBundle
│       ├── gates/
│       │   ├── __init__.py
│       │   ├── quality_gate_engine.py       # Runs all gates → QualityReport
│       │   └── checks/                      # One module per gate family
│       │       ├── structural_checks.py
│       │       ├── content_checks.py
│       │       ├── seo_checks.py
│       │       ├── accessibility_checks.py
│       │       └── integrity_checks.py
│       └── pipeline/
│           ├── __init__.py
│           ├── website_generation_pipeline.py   # Single public deterministic entry point
│           └── state_machine.py                 # Pure transition function + state tables
│
├── repositories/
│   ├── artifact_store_repository.py     # Content-addressable store (CAS) for all artifacts
│   ├── build_state_repository.py        # Build rows, checkpoints, audit trail (SQLite)
│   ├── site_bundle_repository.py        # Rendered bundle file layout + bundle manifests
│   └── cognition_transcript_repository.py  # Recorded AI request/response transcripts
│
├── services/
│   ├── website_generation_service.py    # Orchestrates full build: states, retries, escalation
│   ├── cognition/
│   │   ├── __init__.py
│   │   ├── cognition_router.py          # PromptContract execution + model abstraction
│   │   ├── content_cells.py             # Maker cells (copy, meta, alt text)
│   │   ├── checker_cells.py             # Checker cells (review/score candidate content)
│   │   └── replay_provider.py           # Transcript-backed provider for tests/replay
│   └── deployment/
│       ├── __init__.py
│       ├── deployment_service.py        # Promotion, rollback, verification workflow
│       └── adapters/                    # DeploymentAdapter implementations
│           ├── local_preview_adapter.py
│           └── static_host_adapter.py
│
├── scripts/
│   └── generate_website.py              # Operator CLI (mirrors generate_launch_kit.py pattern)
│
└── tests/
    └── website_generation/              # Structure mirrors package tree (see Part 11)
Responsibility summary per package.

contracts/ — the only package every other package may import. Artifacts, interfaces, enums, errors, version registries. No logic beyond validators attached to models.
constants/ — named constants only. No computation. Every magic number in the WGE lives here or does not exist.
speccompiler/ — the sole ingestion point from the rest of Atlas. Consumes Directory Builder / Project Assembly / Launch Kit outputs and compiles the canonical BusinessSpec. Nothing downstream ever reads upstream Atlas models directly.
brand/, ia/, content/, components/, layouts/, rendering/, seo/, assembly/ — one engine each, one transformation each, detailed in Part 5.
gates/ — the Quality Gate Engine and its check modules; the only package allowed to declare a build unfit.
pipeline/ — WebsiteGenerationPipeline, the single public deterministic entry point (the AES-005A WebsiteIntelligencePipeline pattern), plus the pure state machine.
repositories/ — four new repositories; each owns one storage concern (§9).
services/ — the orchestration service, the AI cognition layer (§7), and deployment (§12).
scripts/ — thin operator runner, following the generate_launch_kit.py precedent exactly.
Deliberate exclusions. There is no ai/ package inside engines/ — AI lives only in services/cognition/. There is no analytics/ package in MVP — analytics hooks are a deferred phase (Part 13) and will attach at the deployment layer, not inside the build pipeline. There is no testing/ package inside the engine — test utilities live under tests/website_generation/fixtures/.

Part 3 — Dependency Architecture
3.1 Dependency direction
Dependencies point in exactly one direction: inward toward contracts.

scripts ──▶ services ──▶ engines ──▶ contracts ◀── repositories ◀── services
contracts/ imports: standard library, pydantic_compat only.
constants/ imports: nothing but the standard library.
Every engine package imports: contracts/, constants/, and sibling engine contracts — never sibling engine implementations, except through the pipeline, which composes them.
pipeline/ imports every engine's public class. It is the only engine-layer module allowed to do so.
repositories/ import: contracts/ and storage drivers (sqlite3, pathlib, hashlib, json, zipfile).
services/ import: engine public classes, repository classes, contracts/. Only services/cognition/ may import the Anthropic API client. Only services/deployment/adapters/ may import host-specific transport.
scripts/ import: one service, argparse, sys. Nothing else.
3.2 Allowed and forbidden dependencies (matrix)
From \ To	contracts	constants	engine pkgs	pipeline	repositories	services	scripts	vendor SDKs
contracts	—	✅	❌	❌	❌	❌	❌	❌
constants	❌	—	❌	❌	❌	❌	❌	❌
engine pkgs	✅	✅	❌*	❌	❌	❌	❌	❌
pipeline	✅	✅	✅	—	❌	❌	❌	❌
repositories	✅	✅	❌	❌	—	❌	❌	storage only
services	✅	✅	✅ (public)	✅	✅	✅	❌	cognition/deploy only
scripts	✅	❌	❌	❌	❌	✅ (one)	—	❌
* Engines communicate through artifacts, not imports. component_engine never imports layout_engine; it consumes a ComponentManifest produced earlier and emits an artifact consumed later.

3.3 Circular dependency prevention
Three mechanical safeguards, all enforced by tests (not by convention):

Import audit test. A regression test walks the AST of every module under engines/website_generation/ and asserts the import matrix above. Any new import outside the matrix fails the suite. (Same technique as the AES-005A flat-import audit.)
Contracts are leaf-only. contracts/ importing anything above it is structurally impossible to miss because the audit test whitelists its imports explicitly.
Pipeline as sole composer. Because engines never import each other, cycles between stages cannot form; the only composition point is pipeline/, which is acyclic by construction (a linear stage table).
3.4 Public interfaces vs internal modules
The public surface of the WGE is exactly what engines/website_generation/__init__.py exports:

WebsiteGenerationPipeline
The ten engine classes (Part 5)
The artifact models and enums from contracts/
The exception hierarchy from contracts/errors.py
Everything else (token_resolver, html_emitter, checks/*, state_machine internals) is internal. Internal modules may be refactored freely between versions provided public behavior and artifacts are unchanged and the regression suite passes. Tests may only import the public surface plus fixtures — never internal helpers — so the suite defends the boundary.

3.5 Shared contracts and extension points
Cross-engine sharing happens only via contracts/artifacts.py. Extension points are declared as abstract interfaces in contracts/interfaces.py:

DeploymentAdapter — implemented in services/deployment/adapters/
CognitionProvider — implemented by the live Anthropic-backed provider and by replay_provider
GateCheck — implemented by each module under gates/checks/; the Quality Gate Engine discovers checks from an explicit registered list in constants/gates.py (no dynamic scanning — deterministic ordering is mandatory)
New site component types, new gates, and new deployment targets are added by implementing an interface and registering it in constants — never by modifying the pipeline.

Part 4 — Artifact Pipeline
4.1 Artifact catalog
Twelve artifacts. Every artifact is a frozen Pydantic model with three mandatory header fields: schema_version: str, artifact_kind: ArtifactKind, and source_hashes: dict[str, str] (the SHA-256 of every input artifact that produced it — this forms the provenance chain).

#	Artifact	Producer (owner)	Consumers	Contents (summary)
1	BusinessSpec	BusinessSpec Compiler	Brand, IA, Content, SEO engines	Canonical business identity: niche, audience, value proposition, directory taxonomy, monetization model, geography, legal footer facts
2	BrandPackage	Brand Engine	Layout, Rendering, Assembly	Design tokens (palette, type scale, spacing, radii), voice profile, logo/asset references by content hash
3	SiteArchitecture	IA Engine	Content, Component, SEO, Assembly	Page inventory, routes, nav trees, internal-link topology, sitemap plan
4	ContentCandidate	Cognition cells (via service)	Content Engine (validation only)	Raw AI-drafted copy blocks keyed to IA slots; never consumed downstream directly
5	ContentPackage	Content Engine	Component, Rendering, SEO	Validated, normalized, policy-checked content blocks; the only content downstream stages may see
6	ComponentManifest	Component Engine	Layout Engine	Per-page component instances with bound content refs and props
7	LayoutPlan	Layout Engine	Renderer	Deterministic page composition: ordered regions, grid placement, responsive rules by token
8	RenderedPageSet	Renderer	Assembly, Gates	Emitted HTML/CSS per page, content-hashed
9	SEOPackage	SEO Engine	Assembly, Gates	Titles, meta descriptions, canonical URLs, structured data, robots directives, sitemap.xml plan
10	SiteBundle	Assembly Engine	Gates, Deployment	Complete static site: file map (path → content hash), asset set, bundle manifest
11	QualityReport / LaunchCertificate	Quality Gate Engine	Deployment, Investment Committee	Gate results, severities, pass/fail; certificate issued only on full pass
12	BuildManifest	Pipeline	Everyone; the audit record	Ordered record of every stage: engine versions, artifact hashes, state transitions, transcript hashes
4.2 Creation and ownership
Exactly one producer per artifact kind. A stage may not mutate an artifact it did not produce — and cannot, because all models are frozen. "Updating" an artifact means producing a new artifact with a new hash and recording the supersession in the BuildManifest.

4.3 Serialization
Canonical serialization is UTF-8 JSON with sorted keys, no insignificant whitespace, and explicit null handling — produced by a single shared helper in contracts/ so every engine and repository serializes identically. The artifact's identity is sha256(canonical_json). Binary assets (images, fonts) are stored as raw bytes in the CAS and referenced from artifacts by hash; artifacts themselves never embed binary data.

4.4 Validation
Three validation rings, applied at persistence time by the artifact store repository:

Schema — Pydantic parse against the registered model for the declared schema_version.
Semantic — engine-owned validators (e.g., every ComponentManifest content ref must resolve to a block in the ContentPackage; every route in SEOPackage must exist in SiteArchitecture).
Integrity — recomputed hash must match the declared identity; all source_hashes must already exist in the CAS (no orphan provenance).
An artifact failing any ring is rejected and never enters the store; the producing stage fails with a typed error (§6.7).

4.5 Lifecycle and immutability
Artifacts are immutable from the moment of persistence. Lifecycle states are tracked about artifacts in the build state repository, never inside them: PRODUCED → VALIDATED → CONSUMED → SUPERSEDED | ARCHIVED. Garbage collection of unreferenced artifacts is a deferred capability (Part 13); in MVP nothing is deleted, which is acceptable at directory-portfolio scale and maximizes auditability.

4.6 Versioning
Two independent version axes, both recorded in every BuildManifest:

Schema versions (contracts/versions.py): semver per artifact kind. Minor = additive optional fields (old readers still parse); major = breaking, requires a registered migration function or an explicit "no migration, rebuild required" declaration. The registry maps (artifact_kind, schema_version) → model class.
Engine versions: semver per engine class, bumped whenever output could differ for identical input. This is the replayability contract: same inputs + same engine versions ⇒ same output hash. A golden-build test (§11.5) enforces it.
Part 5 — Engine Interfaces
General contract shared by all ten engines: a single public class per engine; a single public method (compile, plan, render, evaluate — one verb per engine); frozen artifact in, frozen artifact out; no side effects; failures raised as typed exceptions from contracts/errors.py, never returned as sentinel values; every output artifact carries source_hashes and the engine's version string. Engines never log, never print, never touch the clock.

5.1 BusinessSpec Compiler
Class	BusinessSpecCompiler (speccompiler/)
Input	Upstream Atlas outputs: Directory Builder project record, Project Assembly outputs, Launch Kit metadata (passed in as already-loaded frozen models — the service fetches them)
Output	BusinessSpec
Contract	Total function over valid upstream inputs; every downstream-required field either resolved or defaulted from constants/; no field silently invented — unresolvable required fields raise SpecCompilationError listing every missing field at once (batch error reporting, not first-failure)
Failure	SpecCompilationError (terminal — human input needed)
Versioning	Bumped when compilation rules change; the compiler is the only module that knows upstream Atlas schemas, isolating the WGE from upstream drift
5.2 Brand Engine
Class	BrandEngine (brand/)
Input	BusinessSpec
Output	BrandPackage
Contract	Deterministic token derivation: palette selection, type scale, spacing scale seeded from stable spec attributes (niche category, tone flags) — same spec, same brand, always. Contrast ratios computed and embedded so the accessibility gate can verify without recomputing
Failure	BrandResolutionError (retryable only if inputs change)
Versioning	Token taxonomy changes are major bumps (they alter every downstream render)
5.3 Information Architecture Engine
Class	InformationArchitectureEngine (ia/)
Input	BusinessSpec, BrandPackage
Output	SiteArchitecture
Contract	Emits page inventory, route map, nav trees, and internal-link topology from spec taxonomy rules. Routes are normalized, unique, and stable-sorted. Every page declares its content slots (typed placeholders the content stage must fill)
Failure	ArchitecturePlanningError
Versioning	Route-generation changes are major (URLs are public commitments)
5.4 Content Engine
Class	ContentEngine (content/)
Input	SiteArchitecture, zero or more ContentCandidate artifacts, BusinessSpec
Output	ContentPackage
Contract	The determinism airlock. Validates candidates against slot schemas, normalizes whitespace/encoding, HTML-escapes all text destined for markup (the AES-005A HTML-injection fix is a permanent design rule here), enforces length and policy constraints, and rejects any slot left unfilled. AI text enters here or not at all
Failure	ContentValidationError carrying per-slot diagnostics → routed to cognition retry or human escalation (§6.8)
Versioning	Validation-rule changes are minor if stricter, major if they alter accepted content
5.5 Component Engine
Class	ComponentEngine (components/)
Input	SiteArchitecture, ContentPackage
Output	ComponentManifest
Contract	Maps each page's slots to component instances from the registry (a declarative catalog in components/registry.py — data tables, not generated code). Prop binding is exhaustive: a component instance with an unbound required prop is a compile error here, not a render error later
Failure	ComponentResolutionError
Versioning	Registry additions minor; component prop-contract changes major
5.6 Layout Engine
Class	LayoutEngine (layouts/)
Input	ComponentManifest, BrandPackage
Output	LayoutPlan
Contract	Composes ordered page regions and responsive behavior expressed purely in design tokens. Produces no markup — only a composition tree the renderer walks
Failure	LayoutCompositionError
5.7 Renderer
Class	Renderer (rendering/)
Input	LayoutPlan, ContentPackage, BrandPackage
Output	RenderedPageSet
Contract	Deterministic emission: stable attribute ordering, stable class-name generation (token-derived, not hashed-random), byte-identical output for identical input. All interpolated text arrives pre-escaped from the Content Engine; the emitter escapes again at the boundary (defense in depth). CSS emitted once from tokens, shared across pages
Failure	RenderError
Versioning	Any markup change is at least minor; snapshot tests (§11.4) catch unintended drift
5.8 SEO Engine
Class	SEOEngine (seo/)
Input	SiteArchitecture, ContentPackage, BusinessSpec
Output	SEOPackage
Contract	Derives titles, meta descriptions (AI-drafted candidates arrive via ContentPackage slots; the engine enforces limits from constants/seo.py), canonical URLs, structured data (schema.org types keyed to directory entity types), robots directives, and the sitemap plan. Truncation rules are deterministic and documented
Failure	SEOCompilationError
5.9 Assembly Engine
Class	AssemblyEngine (assembly/)
Input	RenderedPageSet, SEOPackage, BrandPackage (assets)
Output	SiteBundle
Contract	Produces the complete static site as a file map (route path → content hash), injects SEO metadata into rendered pages, emits sitemap.xml/robots.txt, and computes the bundle-level hash (hash of the sorted file map). No file I/O — the repository materializes the bundle to disk
Failure	AssemblyError
5.10 Quality Gate Engine
Class	QualityGateEngine (gates/)
Input	SiteBundle, SEOPackage, ContentPackage, SiteArchitecture
Output	QualityReport; LaunchCertificate iff all blocking gates pass
Contract	Executes the registered gate list in declared order (Part 10). Every gate returns a typed result — never raises for a content failure (raising is reserved for gate malfunction). The AES-005A quality-gate false-positive lesson is codified: every gate must ship with at least one known-good and one known-bad fixture proving it fires correctly in both directions
Failure	GateExecutionError (gate malfunction only)
Part 6 — State Machine
6.1 Design
The state machine is split into two parts, per Atlas doctrine:

Pure core (pipeline/state_machine.py): a transition function — (BuildState, StageOutcome) → BuildState — plus static tables of states, allowed transitions, and per-state retry policy. Fully unit-testable, zero I/O.
Effectful shell (services/website_generation_service.py): reads/writes checkpoints via build_state_repository, invokes engines and cognition cells, applies the pure transition function, and persists every transition as an audit row.
6.2 States
INITIALIZED
  → SPEC_COMPILED
  → BRAND_RESOLVED
  → IA_PLANNED
  → CONTENT_DRAFTING        (cognition boundary — the only non-deterministic region)
  → CONTENT_VALIDATED
  → COMPONENTS_RESOLVED
  → LAYOUT_COMPOSED
  → RENDERED
  → SEO_COMPILED
  → ASSEMBLED
  → GATED
  → CERTIFIED
  → PACKAGED
  → DEPLOY_READY            (terminal success)

Failure/exception states (reachable from any active state):
  FAILED_RETRYABLE → (re-enter prior state, attempt++)
  FAILED_TERMINAL           (terminal failure)
  ESCALATED_HUMAN           (paused pending operator decision)
  CANCELLED                 (terminal, operator-initiated)
  GATE_REJECTED → ESCALATED_HUMAN | CONTENT_DRAFTING (targeted rework)
Transitions are legal only if present in the static transition table. An illegal transition raises IllegalTransitionError and moves the build to FAILED_TERMINAL — a corrupted build never limps forward.

6.3 Retry policy
Per-state, declared in constants/build.py:

State family	Retryable failures	Max attempts	Backoff
Deterministic stages	None by definition — same input yields same failure. A deterministic stage failure is immediately FAILED_TERMINAL (retrying identical math is self-deception)	1	n/a
CONTENT_DRAFTING (cognition)	Model errors, timeout, schema-invalid output, checker rejection	3 per cell	Fixed ladder (owned by service, injected — never time.sleep inside logic)
GATED	Content-family gate failures route to targeted redrafting of failing slots only	2 rework cycles	n/a
Deployment verification	Transient transport errors	3	Fixed ladder
Attempt counters live in the build state row, never in artifacts.

6.4 Checkpointing and resume
A checkpoint is written after every successful state transition: (build_id, state, attempt, artifact_hashes_so_far, transcript_hashes_so_far, engine_versions, transitioned_at). build_id is content-derived: sha256(BusinessSpec hash + pipeline version + explicit build_salt) — no UUIDs. Resume loads the latest checkpoint, verifies every recorded artifact hash still resolves in the CAS (integrity re-check), and re-enters at the recorded state. Because artifacts are immutable and stages are pure, resume is trivially safe: nothing is half-written, ever.

6.5 Cancellation
Cancellation is honored only at state boundaries — the service checks a cancellation flag between stages, never interrupts a stage mid-flight. A cancelled build's artifacts remain in the CAS (they are content-addressed and may be reused by a future build of the same spec — free warm-start).

6.6 Rollback
Build-level rollback does not exist and is not needed: builds are append-only. "Rolling back" means starting a new build or promoting a previously certified bundle (§12.4). This is a deliberate simplification bought by immutability.

6.7 Failure routing
Every typed error carries (stage, error_class, retryable: bool, diagnostics). The service routes: retryable → retry ladder; non-retryable deterministic → FAILED_TERMINAL with full diagnostics in the audit trail; content/gate failures with rework potential → targeted CONTENT_DRAFTING re-entry scoped to failing slots; everything unresolvable → ESCALATED_HUMAN.

6.8 Human escalation
ESCALATED_HUMAN persists an escalation record: what failed, the exact artifacts involved (by hash), attempted remedies, and the decision options (rework / override with justification / cancel). Overrides are recorded in the BuildManifest permanently — a certified site with a human override says so on its certificate. In MVP the escalation queue is surfaced by the operator CLI; no UI is built for it.

6.9 Audit trail
Every transition, every retry, every escalation, and every override is an append-only row keyed to build_id. The BuildManifest is the compiled, human-readable projection of this trail plus the artifact provenance chain. The manifest is itself an artifact — hashed, immutable, and the thing the Investment Committee cites when it evaluates the asset.

Part 7 — AI Cognition Layer
7.1 Placement and posture
All cognition lives in services/cognition/. Engines cannot reach it; it cannot reach engines except by producing artifacts the pipeline consumes. The cognition layer's entire job is to turn an information need (defined by empty SiteArchitecture slots) into ContentCandidate artifacts, and to review them.

7.2 Cognition cells
A cell is the unit of AI work: one responsibility, one prompt contract, one output schema. MVP cells:

Cell	Kind	Produces
page_copy_cell	Maker	Body copy blocks per IA slot
meta_description_cell	Maker	Meta description candidates
alt_text_cell	Maker	Image alt text candidates
content_checker_cell	Checker	Structured review verdict per candidate
7.3 Prompt contracts
Each cell is governed by a PromptContract — a frozen model registered in constants:

cell_id, contract_version, model_id, prompt_template_version, input_schema (what context fields the cell may receive), output_schema (the JSON the model must return), max_input_tokens, max_output_tokens, temperature (0 for all MVP cells), max_attempts.

Prompt templates are versioned files, hashed, and the hash is recorded in every transcript. Changing a template without bumping its version is a build-breaking offense caught by the contract test that hashes templates against the registry.

7.4 Context packaging and input limits
The cognition router assembles context only from artifact fields whitelisted in the cell's input_schema — never from raw upstream Atlas data, never from the database. Context is serialized canonically, measured against max_input_tokens, and truncated by documented priority rules (never silently). What the model saw is exactly reconstructible from the transcript.

7.5 Output validation
Model output must parse as the cell's output_schema (after fence-stripping). Parse failure → retry with a repair instruction, up to max_attempts. Parsed output is wrapped into a ContentCandidate artifact with the transcript hash in source_hashes — provenance from model response to published page is unbroken.

7.6 Replay and model abstraction
CognitionProvider is the abstract interface; two implementations:

Live provider — calls the Anthropic API. The only module in the WGE permitted to import the API client.
Replay provider — serves recorded transcripts from cognition_transcript_repository keyed by (cell_id, contract_version, input_hash). Used by all tests and by audit replays. A replay miss in test mode is a hard failure (a test that silently goes live is a broken test).
This makes the entire pipeline, cognition included, deterministic under replay — the property that lets golden builds cover end-to-end behavior.

7.7 Maker/checker model
Every maker candidate passes two reviews before the Content Engine sees it: (1) the checker cell scores it against a structured rubric (accuracy vs spec facts, tone vs brand voice, slot-fit) and returns approve / revise-with-notes / reject; (2) deterministic validation in the Content Engine (§5.4). Checker approval never bypasses deterministic validation — the checker is advisory, the engine is law. Revise-with-notes feeds the notes back into a bounded redraft loop (max attempts from the contract), then escalates.

7.8 Cost controls
Per-build token budget declared in constants/build.py; the router meters every call against it and fails to ESCALATED_HUMAN when exceeded (never silently degrades). All costs recorded per transcript and rolled up in the BuildManifest, so cost-per-directory-site is a first-class portfolio metric for the Investment Committee.

7.9 Failure recovery
Cell failure exhausting retries scopes the failure to its slots: the build proceeds drafting other slots, then parks in ESCALATED_HUMAN listing exactly the unfilled slots. The operator can supply manual content (entered as a human-authored ContentCandidate, flagged as such in provenance) — the pipeline does not care who wrote the candidate, only that it validates.

Part 8 — Rendering Architecture
8.1 Component system
Components are declarative catalog entries, not code generators: each registry entry declares component_id, version, required/optional props with types, content-slot bindings, allowed regions, and the token classes it consumes. The renderer holds the (only) markup knowledge for each component in html_emitter.py as pure emission functions. Adding a component = registry entry + emitter function + fixture pair + snapshot test.

8.2 Layout engine
Layouts compose components into regions (header / hero / body sections / footer) using rules keyed to page type from the IA. Responsive behavior is expressed exclusively through token-defined breakpoints — no component may carry bespoke breakpoints. The layout output is a composition tree; nothing about pixels or markup.

8.3 Design token usage
BrandPackage tokens are the single source of visual truth. The CSS emitter compiles tokens to custom properties once per build; component emitters reference token classes only. A component referencing an undeclared token fails at render time with a named-token diagnostic (integrity gate also re-verifies at bundle level).

8.4 Page composition and rendering pipeline
Per page: LayoutPlan tree → walk → emit component HTML (content pre-escaped, escaped again at emission) → wrap in page shell → inject SEO metadata at assembly. Cross-page: shared CSS emitted once; assets referenced by content hash for cache-perfect immutable URLs.

8.5 Static compilation
Output is fully static HTML/CSS: no client framework, no build-time JS toolchain, no bundler. This is deliberate — static output is deterministic, auditable byte-for-byte, trivially hostable, and fast. Progressive enhancement via small vanilla JS snippets is permitted only as versioned, hashed assets emitted like any other.

8.6 Future server-side extensions
The seam for future dynamic behavior is the SiteBundle contract: a future DynamicSiteBundle (major version) could add server route descriptors while the entire pipeline upstream of assembly is unchanged. No provision beyond the seam is built now (deferred, Part 13).

Part 9 — Repository Layer
9.1 artifact_store_repository (CAS)
The content-addressable store for every artifact and binary asset. Layout:

data/wge/cas/
    objects/<first2>/<sha256>          # canonical JSON or raw bytes
    kinds/<artifact_kind>/<sha256>     # symlink-free index rows in SQLite, not FS links
API surface: put(artifact) → hash (validates rings 1–3, idempotent — putting an existing hash is a no-op), get(hash, expected_kind) → artifact, exists(hash), list_by_kind(kind). Hashing uses the shared canonical serializer only; the repository refuses any object whose recomputed hash mismatches. Caching falls out of content addressing: identical inputs are naturally deduplicated, and a rebuilt stage whose inputs are unchanged can skip execution by hash lookup (warm-start optimization, enabled per-stage in constants).

9.2 build_state_repository
SQLite tables: builds (build row, current state, attempt counters), transitions (append-only audit rows), escalations, overrides. Written by exactly one writer — the website generation service — honoring the Atlas v3 single-writer doctrine established for PipelineRunner. No other module issues SQL against these tables.

9.3 site_bundle_repository
Materializes a SiteBundle from the CAS to a real directory tree for preview/packaging: writes files per the bundle file map, verifies every file's hash after write, emits bundle_manifest.json (the file map + bundle hash + build id), and produces the deployment ZIP using the established staging discipline: stage into a temp directory with the exact final hierarchy, cd into it, zip from within. The ZIP is not reported as deliverable until its own manifest verification pass reads it back and matches every hash.

9.4 cognition_transcript_repository
Append-only store of every AI exchange: (cell_id, contract_version, prompt_template_hash, input_hash, request, response, token_counts, recorded_at) → transcript_hash. Serves the replay provider; retention is indefinite in MVP (transcripts are the audit spine of the non-deterministic region).

9.5 Version management
The CAS never migrates objects — an object is its hash, forever. Schema migrations produce new artifacts from old ones via registered migration functions, recorded as ordinary provenance (source_hashes pointing at the pre-migration artifact). Manifest generation is repository-owned and mechanical; manifests are themselves CAS objects.

Part 10 — Quality Gates
10.1 Execution model
Gates run inside the deterministic pipeline at the GATED state against the assembled SiteBundle plus upstream artifacts. The gate list, order, thresholds, and severities are declared in constants/gates.py. Severities: BLOCKING (certification impossible), WARNING (recorded, certification allowed), INFO. Severity assignments map one-to-one to the Master Blueprint's gate definitions; this document adds only execution mechanics.

10.2 Gate families (MVP set)
Family	Examples	Severity
Structural	Every IA route present in bundle; no orphan files; all internal links resolve; nav integrity	BLOCKING
Content	No unfilled slots; no placeholder tokens ({{, TODO, lorem); length bounds; escaped output verification	BLOCKING
SEO	Title/description present and within limits on every page; canonical correctness; sitemap ↔ routes parity; structured-data schema validity	BLOCKING (presence) / WARNING (optimization)
Accessibility	Contrast ratios from BrandPackage verified in emitted CSS; alt text present; heading hierarchy sanity; landmark presence	BLOCKING (alt text, contrast) / WARNING
Integrity	Every file hash matches CAS; every provenance hash resolves; manifest completeness; engine-version consistency	BLOCKING
10.3 Failure propagation and certification
Gate results aggregate into the QualityReport. Any BLOCKING failure → GATE_REJECTED, routed per §6.7 (targeted content rework where applicable, else escalation). Full pass → the engine issues the LaunchCertificate: bundle hash, build id, gate results digest, engine versions, override record (normally empty), and the manifest hash. The certificate is the only token the Deployment Service accepts — an uncertified bundle is undeployable by construction, and the Investment Committee consumes the certificate as evidence when scoring the asset.

10.4 Gate integrity discipline
Inherited from the AES-005A false-positive incident: every gate ships with a known-good fixture it must pass and a known-bad fixture it must fail. A gate lacking either fixture cannot be registered (the registration test enforces it). Gates are pure functions and individually unit-tested like any engine code.

Part 11 — Testing Strategy
11.1 Structure
tests/website_generation/ mirrors the package tree exactly: one test module per source module, plus fixtures/ (frozen input artifacts, recorded transcripts, golden bundles) and integration/. The suite extends the existing Atlas regression suite; the WGE's suite plus the platform's existing suites must all pass for any delivery — the established zero-regression gate applies without exception.

11.2 Unit tests
Every engine method, validator, emitter, gate check, and the pure state-machine transition function. Deterministic engines are tested with property-style assertions where valuable: idempotence (f(x) == f(x)), hash stability across process restarts, and sorted-output invariants.

11.3 Integration and pipeline tests
Repository tests against temp SQLite/temp dirs. Service tests run the full pipeline with the replay provider — no network, no cost. The import-audit test (§3.3) and the prompt-template hash test (§7.3) run in this tier.

11.4 Snapshot tests
Rendered HTML/CSS per component and per page type is snapshot-pinned. Snapshot updates require an explicit engine version bump in the same delivery — a diff without a bump fails.

11.5 Golden builds
The end-to-end anchor: fixture BusinessSpec (PetTripFinder-shaped) + recorded transcripts → full pipeline → assert the final SiteBundle hash and BuildManifest hash byte-for-byte. Two golden specs in MVP (one simple, one exercising every component). A golden hash change is legitimate only alongside the version bumps that explain it.

11.6 Replay testing
Any historical build can be replayed from its manifest: fetch artifacts + transcripts by hash, re-run, compare hashes. A scripts/-level replay verification is part of the operator toolkit from Phase 3 onward.

11.7 Performance and regression
Performance tests are budget assertions, not benchmarks: full golden build under a declared wall-clock ceiling on reference hardware; CAS operations under declared per-op ceilings. Visual regression (screenshot diffing) is explicitly deferred (Part 13) — HTML/CSS snapshots carry that weight in MVP at zero tooling cost.

Part 12 — Deployment Architecture
12.1 Build packaging
site_bundle_repository produces the deployment ZIP (staging discipline per §9.3) containing the static site, bundle_manifest.json, and the LaunchCertificate. The ZIP is the unit of deployment; its hash is the unit of identity.

12.2 Deployment interfaces
DeploymentAdapter (contract): deploy(bundle_ref, target) → DeploymentReceipt, verify(receipt) → VerificationResult, activate(receipt), current(target). MVP adapters: local_preview_adapter (materialize + serve locally for operator review — reusing the Phase 4 Static Site Preview Engine seam) and static_host_adapter (single static host target). Adapters are the only modules that know transport details.

12.3 Environment isolation and version promotion
Three logical targets per site: preview → staging → production, each holding a pointer to a certified bundle hash. Promotion moves the pointer; it never rebuilds, never re-uploads a different byte. The promotion record (who, when, from-hash, to-hash, certificate) appends to the audit trail.

12.4 Rollback strategy
Rollback = pointing production back at any previously certified bundle hash. Because bundles are immutable and content-addressed, rollback is exact, instant, and needs no special machinery — it is promotion in reverse, with the same audit record.

12.5 Production verification
Post-activation, the deployment service fetches a sampled file set from the live target and verifies hashes against the manifest (full verification for MVP-scale sites). Verification failure auto-rolls back to the prior pointer and escalates. A deployment is not "done" until verification passes — the same "not delivered until confirmed" discipline that governs ZIP delivery.

Part 13 — MVP Implementation Roadmap
The Master Blueprint is a decade-scale vision; this roadmap is the manufacturing schedule. Each phase is independently shippable, ends with the full regression suite green, and follows the established part-by-part delivery cadence (complete files, ZIP staging, extraction confirmation, zero-touch).

Phase 1 — Contracts, spine, and golden skeleton. contracts/, constants/, BusinessSpecCompiler, artifact_store_repository, build_state_repository, the pure state machine, and a skeleton pipeline that runs SPEC_COMPILED → PACKAGED using fixture content (no AI, no real rendering — pass-through stages). Deliverable proof: a golden BuildManifest hash reproduced twice. Everything after Phase 1 is filling in stages behind stable contracts. Estimated suite: ~45–55 tests.

Phase 2 — Deterministic manufacturing core. Brand Engine, IA Engine, Component/Layout/Renderer with a minimal component registry (header, hero, listing grid, detail block, text section, footer), CSS emitter, Assembly Engine, site_bundle_repository. Deliverable proof: fixture spec → real static site on disk, byte-stable across runs. ~60–80 tests added.

Phase 3 — Gates, SEO, certification, operator runner. SEO Engine, Quality Gate Engine with the full MVP gate set (each with good/bad fixture pairs), LaunchCertificate, scripts/generate_website.py (modeled on generate_launch_kit.py), replay-verification script. Deliverable proof: a certified bundle for the PetTripFinder-shaped golden spec. ~50–70 tests added.

Phase 4 — Cognition layer. CognitionProvider pair (live + replay), prompt contracts, the four MVP cells, maker/checker loop, transcript repository, token budgeting, escalation queue surfaced in the CLI. Deliverable proof: a full build with recorded transcripts, then replayed to identical hashes with the network disabled. ~40–60 tests added.

Phase 5 — Deployment. Both adapters, promotion/rollback/verification workflow, production verification with auto-rollback. Deliverable proof: preview-to-production promotion and a rollback exercised end-to-end against the golden bundle. ~30–40 tests added.

Explicitly deferred (in the Blueprint, not in MVP): server-side rendering and dynamic bundles; analytics package; visual (screenshot) regression tooling; CAS garbage collection; multi-build concurrency/build-farm; cost dashboards beyond manifest rollups; CMS-style post-launch editing; additional deployment adapters; multi-model cognition routing; A/B variant generation. Each deferral has a named seam in this document where it will attach without disturbing the core.

Sequencing rationale. AI arrives in Phase 4, not Phase 1, on purpose: the deterministic pipeline must be provably correct with fixture content before any non-deterministic input is admitted. This mirrors how AES-005A and the Directory Builder were built and de-risks the largest unknown (cognition quality) against a stable, gated substrate. It also means Phases 1–3 already produce deployable directory sites from operator-authored content — revenue-capable output arrives before the architecture is finished, not after.

End of AES-WEB-001 Implementation Architecture, v1.0.0. Amendments by version bump only.


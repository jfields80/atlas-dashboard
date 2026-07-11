
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

Atlas Website Generation Architecture Index.md


Atlas Investment OS
Atlas Website Generation Architecture Index
AES-WEB-INDEX-001 — Navigation Aid — Non-Authority
1. Document Metadata
Field	Value
Document ID	AES-WEB-INDEX-001
Title	Atlas Website Generation Architecture Index
Status	Navigation Aid — Non-Authority
Version	1.0.0
Date	2026-07-10
Purpose	Make the Website Generation Engine documentation set fast to navigate: map every concern, artifact, engine, gate, contract, phase, and amendment to its owning authority and exact section
Governs	Nothing. This document has zero normative force
Does Not Govern	Architecture, contracts, requirements, implementation decisions, gate definitions, phase scope — all of which belong exclusively to the source authorities
Source Authorities	(1) Website Generation Engine Master Architectural Blueprint v1.0 ("Blueprint" — design authority for AES-006 planning); (2) AES-WEB-001 — Website Generation Engine Implementation Architecture Specification v1.0.0 (doc ID AES-WEB-001-IMPL); (3) AES-WEB-002 — Commercial Component System Architecture v1.0.0
Intended Readers	Claude Code implementation sessions (AES-WEB-002A…K and WGE Phases 1–5), future engineers, reviewers, the Atlas operator (Chief Architect)
Maintenance Owner	Atlas Chief Architect (operator); updates authored by documentation sessions under the rules in §17
Update Policy	Update only after an authority document changes, in the same documentation change. Index version bumps are independent and non-authoritative. See §17
Non-authority statement (binding on every reader of this index). This index cannot override the Master Blueprint, AES-WEB-001, or AES-WEB-002. If this index and a source authority disagree, the source authority is correct and the index is defective — file an index correction; never act on the index entry. New rules are added to the appropriate authority document by version bump, never to this index. Implementation sessions making architecture-sensitive changes must cite the source authority section, not this index (§17).

How to use this index. Find your concern in §5, your artifact in §6, your engine in §7, your gate in §11, or your question in §15 — each entry points to the controlling section. Read the pointed-to section before acting; the index summaries are deliberately lossy.

2. The Documentation Set at a Glance
Document	One-line role	Structure
Master Blueprint	What the WGE is and why — ten-year intent, ten-plane system model, AI-employee model, content/SEO/UX philosophy, gate doctrine, learning loop	Parts 0–10 + Closing Note; Plane subsystems numbered (e.g., Plane 4.2); pipeline Phases 0–12 with Gates 0–12
AES-WEB-001	How the WGE is built inside Atlas — packages, dependency matrix, 12-artifact pipeline, engines, state machine, cognition boundary, repositories, gates, testing, deployment, MVP Phases 1–5	Parts 1–13; sections cited as §N.M
AES-WEB-002	What the WGE manufactures with — the commercial component system: contracts, taxonomy, page-role law, selection, variants, gates, 72-component MVP, phases 002A–K	§0–§35; ADR-01…14 in §32
Scope note (not a conflict): the Blueprint's plane-level artifacts (PositioningMap, IAGraph, DemandMap, NavigationSpec, RouteSpec, LinkGraph, FactSheet, VoiceSpec, BrandCore, TrustPackage, etc.) are intent-level constructs. AES-WEB-001 deliberately scopes the MVP to a 12-artifact catalog (AES-WEB-001 §4.1) in which several Blueprint constructs are collapsed (e.g., BrandPackage carries token + voice-profile duties of Blueprint Plane 2; SiteArchitecture carries IA/nav/route/link-topology duties of Blueprint Plane 3). The Blueprint itself declares implementation phasing and contract schemas out of its scope ("Closing Note" / status header), so this collapse is authorized scoping, not a deviation. Blueprint subsystems with no MVP implementation home yet (Demand Mapping, Positioning, Compliance Screener, Originality/Gain Engine, Learning Plane, Experimentation, etc.) remain Blueprint-owned intent awaiting future authority documents (see AES-WEB-002 §34.4 for the recommended next documents).

3. Authority Hierarchy
Conflict rule, verbatim doctrine: Blueprint intent > AES-WEB-001 > AES-WEB-002 > implementation tasks. A lower level requiring a change in a higher level records the required amendment (AES-WEB-002 §34.3 is the live example) and does not act as if the change were already made (AES-WEB-002 §0.1). Amendments happen by version bump only, never silently (AES-WEB-001 authority statement; AES-WEB-002 §0 amendment policy).

Level 1 — Intent Authority: Master Architectural Blueprint (v1.0)
Owns: long-term vision (Part 10); commercial intent and mission (Part 1); system purpose decomposition (Part 1.1); strategic doctrine — data asset as moat, deterministic skeleton / sealed cognition cells, trust manufactured not simulated (Part 0, Plane 2.4, Part 5); ten-year direction and anti-goals (Parts 1.3, 6.2, 10); conceptual capability boundaries — the ten-plane model and which subsystems are constitutionally deterministic vs cognition cells (Part 2, Plane 10.3); gate doctrine and the conceptual gate battery (Part 8); content/SEO/UX philosophy (Parts 5–7); the AI-employee collaboration model (Part 3); the learning loop (Part 9); prediction-registration and T+90 truth-telling doctrine (Part 4 Gates 1/12, Closing Note).

In conflict: Blueprint intent wins; the lower document is amended by version bump (AES-WEB-001 authority statement; AES-WEB-002 §0.1).

Level 2 — WGE Implementation Authority: AES-WEB-001 (v1.0.0)
Owns: package architecture and normative tree (Part 2); dependency direction and import matrix (Part 3); the 12-artifact catalog, serialization, validation rings, lifecycle, versioning (Part 4); the ten engine interfaces + pipeline (Part 5); state machine, retries, checkpointing, escalation, audit (Part 6); the cognition boundary — cells, prompt contracts, replay, maker/checker, cost controls (Part 7); rendering architecture and static-first law (Part 8); the four repositories including the CAS (Part 9); quality-gate execution authority and gate-integrity discipline (Part 10); testing strategy incl. golden builds (Part 11); deployment architecture (Part 12); WGE foundation Phases 1–5 and deliberate deferrals (Part 13).

In conflict with AES-WEB-002 or an implementation session: AES-WEB-001 wins (AES-WEB-002 §0.1).

Level 3 — Component-System Authority: AES-WEB-002 (v1.0.0)
Owns: component contract (ComponentDefinition, §3) and single-source ownership map (§3.1–3.2); naming grammar, identity, namespaces (§4); taxonomy — 16 families (§5; see discrepancy D2 in §13); page-role composition law and ListingKind semantics (§6); variants and complexity budget (§7); props and slots (§8); nesting/composition (§9); token dependencies (§10); responsive contracts (§11); accessibility contracts (§12); component SEO behavior (§13); deterministic selection + trace (§14); registry architecture (§15); conversion contracts (§16); monetization contracts (§17); analytics hooks (§18); security owner map (§19); rendering integration (§20); component quality gates (§21); versioning/deprecation (§22); lifecycle (§23); JS policy (§24); performance thresholds (§25); recipes (§26); 72-component MVP inventory (§27); library expansion doctrine (§28); package refinements (§29); test/fixture architecture (§30); phases AES-WEB-002A–K (§31); ADRs (§32); risks (§33); binding/deferred decisions and required amendments (§34).

Operates inside AES-WEB-001's architecture; MUST NOT redefine artifacts, dependency direction, state machine, cognition placement, or repository ownership (§0.1).

Level 4 — Implementation Tasks (AES-WEB-002A…K; WGE Phases 1–5 deliveries)
Own: exact file creation; explicitly authorized file modifications (enumerated per phase — AES-WEB-002 §31; zero-touch otherwise); production code; tests and fixtures; delivery ZIPs (staging discipline AES-WEB-001 §9.3); regression commands (python -m pytest tests/ -q full-suite gate, AES-WEB-002 §31); extraction verification (delivery unconfirmed until extraction is confirmed — Atlas invariant 7).

Implementation tasks do not create architecture. Any contract ambiguity or need to modify an unauthorized file is a stop condition: halt and request an authority amendment or a §34-style clarification (AES-WEB-002 §31 universal stop conditions). In any conflict between AES-WEB-002 and an implementation session, AES-WEB-002 wins (§0.1).

Cross-level doctrine inherited everywhere
Atlas Platform Architecture invariants (restated in AES-WEB-001 header and AES-WEB-002 §0.2): flat imports; pure deterministic engines (no AI/I-O/network/UUIDs/clock; time as explicit generated_at, identity as content SHA-256); repositories own persistence only; services own orchestration/AI only; frozen Pydantic + pydantic_compat; zero-touch; complete files only; ZIP staging + extraction confirmation; full regression gating, zero regressions; replayability (same inputs + versions ⇒ byte-identical output, identical BuildManifest hash).

4. Blueprint Plane → Implementation Coverage Map
Quick orientation for "where did this Blueprint subsystem land?" (intent → MVP mapping; non-normative summary).

Blueprint plane / subsystem	MVP implementation home	Status
Plane 1.1 Business Strategy Compiler	BusinessSpecCompiler (AES-WEB-001 §5.1)	Implemented in MVP scope
Plane 1.2 Positioning / 1.3 Monetization Architect / 1.4 Compliance Screener	BusinessSpec fields only (monetization config, legal facts); no dedicated engines	Deferred intent; monetization rendering rules live in AES-WEB-002 §17
Plane 2.1–2.3 Brand / Voice / Visual	BrandEngine → BrandPackage (AES-WEB-001 §5.2); token contract surface AES-WEB-002 §10	Implemented (collapsed); full derivation depth → AES-WEB-004 (AES-WEB-002 §34.4)
Plane 2.4 Trust Identity	Trust component family + legal family (AES-WEB-002 §5.6, §5.15) + evidence_ref doctrine (§2.6 E2)	Partial; operational-truth backend → AES-WEB-005
Plane 3.1 IA / 3.3 Nav / 3.4 URL / 3.5 Linking	InformationArchitectureEngine → SiteArchitecture (AES-WEB-001 §5.3); linking floors gated per AES-WEB-002 §6.2	Implemented (collapsed)
Plane 3.2 Demand Mapping	—	Deferred intent (no MVP home)
Plane 4 Content (4.1–4.7)	Cognition cells (AES-WEB-001 §7.2) + ContentEngine airlock (§5.4); typed content models AES-WEB-002 §8.4	Partial; content strategy/variation → AES-WEB-003; originality/gain engine deferred
Plane 5.1 Component Library	AES-WEB-002 in its entirety	This is AES-WEB-002
Plane 5.2 Layout / 5.3 Conversion / 5.4 A11y / 5.5 Performance	LayoutEngine (AES-WEB-001 §5.6); AES-WEB-002 §16 / §12 / §25	Implemented as contracts + gates
Plane 6 Machine-Readability	SEOEngine (AES-WEB-001 §5.8) + AES-WEB-002 §13; citability/feeds/llms.txt	SEO core implemented; citability/feeds deferred intent
Plane 7 Assembly	Renderer, AssemblyEngine, repositories (AES-WEB-001 §5.7, §5.9, Part 9)	Implemented
Plane 8 Assurance	QualityGateEngine (AES-WEB-001 §5.10, Part 10) + AES-WEB-002 §21; red team / simulation	Gates implemented; red-team & simulation deferred intent
Plane 9 Operations & Learning	Analytics identifiers only (AES-WEB-002 §18); deployment verification (AES-WEB-001 §12.5)	Deferred → AES-WEB-006 (post-revenue, AES-WEB-002 §34.4)
Plane 10 Governance	WebsiteGenerationPipeline + state machine + contracts/versions registries + escalation (AES-WEB-001 Parts 3, 4.6, 6)	Implemented
5. Master Concern-Ownership Matrix
Legend: MB = Master Blueprint; W1 = AES-WEB-001; W2 = AES-WEB-002. Phases: P1–P5 = WGE Phases (W1 Part 13); A–K = AES-WEB-002A–K (W2 §31). "—" = not applicable / owned by no artifact-engine pair.

Concern	Primary Authority	Exact Section	Secondary Reference	Owning Artifact	Owning Engine / Service	Owning Package	Impl Phase	Notes / Restrictions
Business identity	W1	§5.1, §4.1 #1	MB Plane 1.1	BusinessSpec	BusinessSpecCompiler	speccompiler/	P1	Sole ingestion point from upstream Atlas; nothing downstream reads upstream models
BusinessSpec compilation	W1	§5.1	MB Plane 1.1	BusinessSpec	BusinessSpecCompiler	speccompiler/	P1	Batch error reporting; SpecCompilationError is terminal
Brand generation	W1	§5.2	MB Plane 2.1–2.3	BrandPackage	BrandEngine	brand/	P2	Deterministic token derivation; contrast ratios embedded
Design tokens (values)	W1	§5.2, §8.3	W2 §10 (consumption law)	BrandPackage	BrandEngine / CSS emitter	brand/, rendering/	P2	W2 §10.2 defines the semantic-token contract surface components may depend on
Design tokens (component consumption)	W2	§10	W1 §8.3	registry design_token_dependencies	Renderer	components/, rendering/	B+	Semantic tokens only; no runtime fallbacks (§10.3)
Information architecture	W1	§5.3	MB Plane 3.1	SiteArchitecture	InformationArchitectureEngine	ia/	P2	Routes are public commitments; route changes are major
Page roles	W2	§6 (enum in §3.2)	W1 §5.3 (SiteArchitecture assigns)	SiteArchitecture (assignment); PageRole enum in contracts/enums.py	IA Engine assigns; Component Engine selects against	contracts/, ia/	A (enum), P2	Closed 18-role enum; exactly one role per page
Content candidates (AI drafts)	W1	§4.1 #4, Part 7	MB Plane 4.3	ContentCandidate	Cognition cells (service layer)	services/cognition/	P4	Never consumed downstream directly; enters pipeline only via Content Engine
Validated content	W1	§5.4	W2 §8.4 (typed block models)	ContentPackage	ContentEngine	content/	P2 (engine), P4 (AI feed)	The determinism airlock; HTML-escape is a permanent design rule
Typed content block models	W2	§8.4	W1 §5.4	ContentPackage block schemas in contracts/artifacts.py	ContentEngine validates; components consume	contracts/	A	Components consume, never define
Component definitions	W2	§3	§15 (registry mechanics)	Registry data (not an artifact)	— (declarative data)	components/catalog/, components/registry.py	A (schema), B–H (entries)	Frozen declarative structures; never generate code
Component instances / bound props / content refs	W2	§3.1	W1 §4.1 #6, §5.5	ComponentManifest	ComponentEngine	components/	P2, D+	Exhaustive prop binding at bind time (compile error, not render error)
Selection trace	W2	§14.3 (ADR-14)	§34.3-A1 (required W1 amendment)	selection_trace block inside ComponentManifest	ComponentEngine (selection/trace.py)	components/selection/	A	New artifact / BuildManifest embedding / side metadata all rejected; Layout Engine ignores the block
Component registry	W2	§15	W1 §8.1 (data-not-code mandate)	registry data + registry_version/registry_hash	—	components/registry.py	A	Explicit ordered tuple, lexicographic; import-time validation; no dynamic scanning
Variants	W2	§7	§3 (supported_variants)	Registry VariantSpec	ComponentEngine (variant selection §14.2.8)	components/catalog/	B–H	Complexity budget §7.3 is BLOCKING at registration
Props	W2	§8.1	§3	Registry PropSpec; values in ComponentManifest	ComponentEngine (bind)	contracts/, components/	A	Closed type set; no free-form string props (ADR-02)
Content slots	W2	§8.2	§8.4	Registry SlotSpec; bindings in ComponentManifest	ComponentEngine	contracts/, components/	A	Props configure structure; slots carry substance
Page composition (which components, in tree)	W2	§9, §26	W1 §5.6	ComponentManifest (instances) + LayoutPlan (order)	Component + Layout Engines	components/, layouts/	P2, D+	Depth ≤ 6; parental spacing; prohibited compositions §9.4
Layout placement (regions, order, grid)	W1	§5.6, §4.1 #7	W2 §3.1, §26 (flexible zones)	LayoutPlan	LayoutEngine	layouts/	P2	Reorders only within recipe flexible zones (W2 §26)
Rendering	W1	§5.7, Part 8	W2 §20	RenderedPageSet	Renderer	rendering/	P2	Byte-identical for identical input; content escaped again at boundary
HTML emission	W1	§8.1, §5.7	W2 §20.1	— (emitter functions)	Renderer emitters	rendering/html_emitter.py	P2, B–H	The only location of markup knowledge (W2 §3.1); 1:1 ACTIVE-definition↔emitter mapping
CSS emission	W1	§8.3	W2 §20.2, §11.2	—	CSS emitter	rendering/css_emitter.py	P2	Once per build from tokens; manifest-driven tree-shaking; owns media queries
SEO metadata (titles, meta, canonicals, robots, sitemap)	W1	§5.8	W2 §13.1 (authority split), MB Plane 6.1	SEOPackage	SEOEngine	seo/	P3	Components never declare canonicals/robots
Structured data	W2	§13.2 (fragments-as-data)	W1 §5.8 (compilation)	fragments recorded in ComponentManifest; compiled into SEOPackage	SEO Engine compiles; Assembly injects	seo/, assembly/	P3, D+	Components never emit JSON-LD; schema-content parity gated (CG-SEO-005/006; MB Plane 6.2 parity doctrine)
Quality gates (execution, pass/fail)	W1	§5.10, Part 10	W2 §21 (component gate catalog); MB Part 8 (doctrine)	QualityReport / LaunchCertificate	QualityGateEngine	gates/	P3, I	The only authority that may declare a build unfit; two-fixture law §10.4
Accessibility	W2	§12	MB Plane 5.4; W1 §10.2 (as amended by A2)	contracts in registry; verified in QualityReport	Quality Gate Engine (CG-A11Y)	gates/checks/accessibility_checks.py	B+ (fixtures), I (gates)	WCAG 2.2 AA floor; no commercial exception (E7)
Responsive behavior	W2	§11	W1 §8.2	registry ResponsiveContract; instance choice in LayoutPlan	Renderer/CSS emitter; CG-RSP gates	rendering/, gates/checks/responsive_checks.py	B+, I	Breakpoints exist only as breakpoint.* tokens (§11.1)
Conversion rules	W2	§16	MB Plane 5.3	registry ConversionContract; recipe primary_goal	ComponentEngine resolution §16.6; CG-COM/CG-CMP-007	components/, constants/components.py	F, I	Repetition limits, friction budgets, honest urgency only
Monetization disclosure	W2	§17	§2.6 (E5), §6.3 non-confusion rule	DisclosureBlock in ContentPackage; bindings in ComponentManifest	Renderer emits; CG-COM-001/002/012 enforce	components/, gates/	E, H, I	Four disclosures: visible + semantic + machine-readable + analytic
Analytics hooks	W2	§18	W1 Part 2 deliberate exclusions	registry AnalyticsContract → data-atlas-* attributes	Renderer emits; consumed at deployment layer	constants/analytics.py, rendering/	A (names), B+	Zero SDKs/scripts/network in core; identifiers describe the interface, never the visitor
Artifacts & provenance	W1	Part 4	W2 §0.2 inv. 2	all 12 artifacts; source_hashes chains	artifact store repository (validation rings)	contracts/, repositories/artifact_store_repository.py	P1	Immutable; content-addressed; three validation rings §4.4
Build state	W1	§9.2, Part 6	—	build rows (not artifacts)	website_generation_service (sole writer)	repositories/build_state_repository.py	P1	Single-writer doctrine; attempt counters never in artifacts
Retries	W1	§6.3	§7.5 (cognition attempts)	—	website_generation_service	constants/build.py	P1	Deterministic stages never retry (terminal on failure)
Escalation	W1	§6.8	MB Plane 10.5	escalation records; overrides in BuildManifest	website_generation_service	repositories/build_state_repository.py	P1, P4 (queue in CLI)	Overrides permanently recorded on the certificate
Checkpointing / resume	W1	§6.4	—	checkpoints (build state rows)	website_generation_service	repositories/build_state_repository.py	P1	build_id content-derived, no UUIDs; resume re-verifies CAS hashes
Replay	W1	§1.1, §7.6, §11.6	W2 §22.3, §0.2 inv. 8	BuildManifest + transcripts + pinned versions	replay provider; replay-verification script	services/cognition/replay_provider.py, scripts/	P3–P4	Certified builds reproducible forever; replay miss in tests = hard failure
Deployment	W1	Part 12	MB Plane 7.3	SiteBundle + DeploymentReceipts	deployment_service + adapters	services/deployment/	P5	Certificate is the only accepted token; promotion = pointer move
Certification	W1	§10.3	MB Part 8.2; W2 §21 (extended gate list)	LaunchCertificate	QualityGateEngine	gates/	P3, K	Uncertified bundles undeployable by construction
Versioning (schemas + engines)	W1	§4.6	W2 §22 (component axes; extends §4.6 additively)	contracts/versions.py registries; recorded in BuildManifest	—	contracts/versions.py	P1, A	Two W1 axes + W2 component axes (§22.1) — see amendment IMP-1 in §13
Deprecation (components)	W2	§22.4, §23	§14.2 step 3 (selection exclusion)	registry DeprecationInfo + replacement_component_id	registry-integrity tests; selection filter	components/registry.py	Post-K governance	Sunset ≥ 2 registry minors; deprecated IDs never reused
Security & content safety	W2	§19	W1 §5.4/§5.7 (escape + re-escape); §8.1 (no smuggling prop types)	— (owner map per threat)	per §19.1 owner column	multiple	All	Emitters must be incapable of un-escaping (§19.2)
Performance budgets	W2	§25	W1 §11.7 (budget-assertion tests); MB Plane 5.5	thresholds in constants	budget tests; bundle gates	constants/components.py, constants/build.py	J+	Every numeric lives in constants — scattering is review-rejectable
Testing	W1	Part 11	W2 §30 (component test/fixture architecture)	fixtures (frozen artifacts)	—	tests/website_generation/	All	Suite mirrors package tree; tests import public surface only
Golden builds	W1	§11.5	W2 §31 (002J/K golden sites)	golden SiteBundle + BuildManifest hashes	—	tests/website_generation/fixtures/	P2–P3, J–K	Two golden specs (simple + every-component); hash change legal only with explaining bumps
Cognition / prompt contracts	W1	Part 7	MB Plane 10.3 (determinism boundary), Part 3 (maker/checker)	PromptContracts; transcripts	cognition_router + cells	services/cognition/	P4	Engines cannot reach cognition; checker is advisory, engine is law (§7.7)
State machine	W1	Part 6	MB Plane 10.1	transitions (audit rows); states in contracts/enums.py	pure core + effectful shell	pipeline/state_machine.py, services/	P1	Illegal transition ⇒ FAILED_TERMINAL; cancellation at state boundaries only
Recipes (default composition per role)	W2	§26	§6.1–6.2	recipe tables (data in constants)	Component Engine (slot needs) + Layout Engine (order)	constants/components.py	A–H (13 in doc; 5 in G/H)	Defaults with flexible zones, not rigid templates
Component lifecycle	W2	§23	§15.2 (integrity tests)	registry lifecycle_status	Chief Architect approvals as data	components/registry.py	B+	PREFERRED is curation (drives +100 selection score)
JS / progressive enhancement	W2	§24	W1 §8.5 (static-first law)	versioned hashed snippets (assets)	Renderer; CG-RND-005/006/007	rendering/	B+	0 KB required JS; ≤ 30 KB deferred enhancement; page must pass all gates with snippets deleted
Concern rows mapped: 48.

6. Artifact Quick-Reference
All twelve artifacts are frozen Pydantic models with mandatory schema_version, artifact_kind, source_hashes headers (AES-WEB-001 §4.1). Canonical serialization + SHA-256 identity: AES-WEB-001 §4.3. Validation rings: §4.4. Lifecycle (tracked about, never inside): §4.5. Schema-version authority for every artifact: the (artifact_kind, schema_version) → model class registry in contracts/versions.py (AES-WEB-001 §4.6). Exactly one producer per kind; "updating" = new artifact + supersession record (§4.2).

#	Artifact	Producer (owner)	Consumers	Primary purpose	Governing source & section	Key invariants	Impl phase
1	BusinessSpec	BusinessSpecCompiler	Brand, IA, Content, SEO engines	Canonical business identity: niche, audience, value prop, directory taxonomy, monetization model, geography, legal facts	W1 §4.1/§5.1; MB Plane 1.1	Every downstream-required field resolved or defaulted; nothing invented	P1
2	BrandPackage	BrandEngine	Layout, Rendering, Assembly (+ components via tokens)	Design tokens, voice profile, asset refs by hash	W1 §4.1/§5.2; token contract surface W2 §10.2	Same spec ⇒ same brand; contrast ratios embedded; token-schema version pinned (W2 §10.3)	P2
3	SiteArchitecture	IA Engine	Content, Component, SEO, Assembly	Page inventory, routes, nav trees, internal-link topology, sitemap plan; assigns one PageRole per page	W1 §4.1/§5.3; W2 §6 (role law)	Routes normalized, unique, stable-sorted; every page declares typed content slots	P2
4	ContentCandidate	Cognition cells (via service)	Content Engine only (validation)	Raw AI-drafted copy keyed to IA slots	W1 §4.1/Part 7	Never consumed downstream directly; transcript hash in source_hashes (§7.5); human-authored candidates allowed, flagged (§7.9)	P4
5	ContentPackage	ContentEngine	Component, Rendering, SEO	Validated, normalized, escaped, policy-checked content blocks — the only content downstream sees	W1 §4.1/§5.4; block schemas W2 §8.4	Escaped at engine, re-escaped at emission; unfilled slots rejected; carries listing_kind, evidence_ref, disclosure blocks (W2 §6.3, §17.3)	P2/P4
6	ComponentManifest	ComponentEngine	LayoutEngine	Per-page component instances with bound content refs and props	W1 §4.1/§5.5; W2 §3.1, §14	Exhaustive prop binding; canonically sorted props (W2 §8.1); records registry_version + registry_hash (W2 §15.2)	P2, D+
6a	↳ selection_trace block	ComponentEngine (selection/trace.py)	Audit/replay readers only — Layout Engine ignores it	Per-slot candidates, eliminations, scores, tie-breaks, chosen (id, version, variant)	W2 §14.3 (ADR-14)	Embedded in ComponentManifest, schema-versioned, optional, deterministic, size-bounded (top-5 + per-filter counts); requires W1 §4.1 amendment A1 — recorded in §13 of this index; PROPOSED until the AES-WEB-001 v1.1.0 delivery ships	A
7	LayoutPlan	LayoutEngine	Renderer	Deterministic page composition: ordered regions, grid placement, token-expressed responsive rules	W1 §4.1/§5.6; W2 §11.2 (responsive adaptation choice)	No markup, no pixels; reorders only within recipe flexible zones (W2 §26)	P2
8	RenderedPageSet	Renderer	Assembly, Gates	Emitted HTML/CSS per page, content-hashed	W1 §4.1/§5.7	Stable attribute order and class names; byte-identical replay	P2
9	SEOPackage	SEOEngine	Assembly, Gates	Titles, metas, canonicals, structured data, robots, sitemap plan; link-attribute policy from LinkSpecs (W2 §17.3)	W1 §4.1/§5.8; W2 §13	Deterministic truncation rules; compiled JSON-LD deduplicated and schema-validated (W2 §13.2)	P3
10	SiteBundle	AssemblyEngine	Gates, Deployment	Complete static site: file map (path → hash), asset set, bundle manifest	W1 §4.1/§5.9	Bundle hash = hash of sorted file map; engine does no file I/O — repository materializes (§9.3); no internal metadata in bundle (CG-RND-008)	P2
11	QualityReport / LaunchCertificate	QualityGateEngine	Deployment, Investment Committee	Gate results + severities; certificate iff all blocking gates pass	W1 §4.1/§10.3; MB Part 8.2	Certificate = bundle hash + build id + gate digest + engine versions + override record + manifest hash; sole deployment token	P3, K
12	BuildManifest	Pipeline	Everyone — the audit record	Ordered record of every stage: engine versions, artifact hashes, transitions, transcript hashes, costs (§7.8)	W1 §4.1/§6.9	Itself a hashed CAS artifact; records all version axes (W2 §22.1 — see IMP-1, §13)	P1
Binary assets: raw bytes in the CAS, referenced by hash; artifacts never embed binary (W1 §4.3).

7. Engine and Service Quick-Reference
7.1 Engines
Shared contract for all engines (W1 Part 5 preamble): one public class, one public verb-method, frozen artifact in → frozen artifact out, no side effects, typed exceptions from contracts/errors.py, output carries source_hashes + engine version; never log/print/touch the clock. Universal forbidden behavior (W1 §1.2, W2 §2.3): I/O, SQL, AI calls, network, Flask, clocks, randomness, UUIDs, vendor SDKs.

Public class	Input artifacts	Output artifact	Responsibility	Engine-specific forbidden behavior	Governing doc & section	Package	Main tests	Phase
BusinessSpecCompiler	Upstream Atlas outputs (loaded by the service)	BusinessSpec	Compile upstream models into the canonical spec; the only module knowing upstream schemas	Inventing unresolvable fields (batch SpecCompilationError instead)	W1 §5.1	speccompiler/	Unit + Phase-1 golden skeleton	P1
BrandEngine	BusinessSpec	BrandPackage	Deterministic token/voice derivation; embeds contrast ratios	Non-seeded variation	W1 §5.2	brand/	Unit; contrast fixtures	P2
InformationArchitectureEngine	BusinessSpec, BrandPackage	SiteArchitecture	Page inventory, routes, nav trees, link topology, typed slots per page	Ad-hoc/unstable routes (major bump territory)	W1 §5.3	ia/	Unit; route-determinism	P2
ContentEngine	SiteArchitecture, ContentCandidate*, BusinessSpec	ContentPackage	The determinism airlock: validate, normalize, escape, enforce policy; reject unfilled slots	Letting AI text in any other way	W1 §5.4	content/	Unit; validator fixtures; malicious-content	P2/P4
ComponentEngine	SiteArchitecture, ContentPackage	ComponentManifest	Deterministic selection (W2 §14 pipeline) + exhaustive prop/slot binding + trace	Heuristic/AI selection (ADR-03); unbound required props reaching render	W1 §5.5; W2 §14–15	components/ (+ selection/, validation/, compatibility/)	Selection, binding, trace, compatibility suites (W2 §30.1)	P2, A, D+
LayoutEngine	ComponentManifest, BrandPackage	LayoutPlan	Compose ordered regions + token-expressed responsive behavior	Producing markup; reordering outside flexible zones	W1 §5.6; W2 §11.2, §26	layouts/	Unit; composition fixtures	P2
Renderer	LayoutPlan, ContentPackage, BrandPackage	RenderedPageSet	Deterministic emission; escape-at-boundary; emitter table keyed (component_id, major_version)	Unstable attributes/classes; reading anything not passed in	W1 §5.7, Part 8; W2 §20	rendering/	Snapshot per component×variant×width; double-render hash	P2, B–H
SEOEngine	SiteArchitecture, ContentPackage, BusinessSpec	SEOPackage	Titles/metas/canonicals/robots/sitemap; compile schema fragments to page JSON-LD	Accepting component-emitted JSON-LD (structurally impossible — fragments only)	W1 §5.8; W2 §13	seo/	Unit; limit/truncation fixtures; schema validity	P3
AssemblyEngine	RenderedPageSet, SEOPackage, BrandPackage	SiteBundle	File map + SEO injection at stable marked positions + sitemap/robots emission + bundle hash	File I/O (repository's job); string-searched injection	W1 §5.9; W2 §13.1	assembly/	Unit; bundle-hash stability	P2
QualityGateEngine	SiteBundle, SEOPackage, ContentPackage, SiteArchitecture (+ ComponentManifest + registry for W2 gates)	QualityReport; LaunchCertificate	Execute registered gate list in declared order; typed results; certify	Raising on content failures (raising = gate malfunction only); dynamic gate discovery	W1 §5.10, Part 10; W2 §21	gates/	Gate-integrity suite: every gate fires both directions on its fixture pair	P3, I
WebsiteGenerationPipeline	(composes all engines)	BuildManifest	Single public deterministic entry point + pure state machine	Everything engines are forbidden; it is the only engine-layer module importing engine classes (W1 §3.1)	W1 Part 2 (pipeline/), Part 6	pipeline/	State-machine unit tests; golden BuildManifest hash	P1
* zero or more.

7.2 Services, cognition, and repositories
Component	Kind	Responsibility	Governing section	Package / module	Phase
website_generation_service	Service	Full-build orchestration: states, retries, escalation, checkpoints; sole writer of build-state tables	W1 §6.1, §9.2	services/website_generation_service.py	P1+
cognition_router	Service (cognition)	PromptContract execution, context packaging from whitelisted artifact fields only, token metering vs budget	W1 §7.3–7.4, §7.8	services/cognition/cognition_router.py	P4
Maker cells (page_copy_cell, meta_description_cell, alt_text_cell)	Cognition cells	Produce ContentCandidates per slot; temperature 0; bounded attempts	W1 §7.2–7.5	services/cognition/content_cells.py	P4
content_checker_cell	Cognition cell	Structured review verdict; advisory — never bypasses deterministic validation	W1 §7.2, §7.7	services/cognition/checker_cells.py	P4
replay_provider	Cognition provider	Transcript-backed provider; used by all tests and audit replays; replay miss in test mode = hard failure	W1 §7.6	services/cognition/replay_provider.py	P4
Live provider	Cognition provider	Anthropic-backed; the only WGE module permitted to import the API client	W1 §7.6, §3.1	services/cognition/	P4
deployment_service + adapters (local_preview_adapter, static_host_adapter)	Service + adapters	Promotion/rollback/verification; pointer-move promotion; auto-rollback on verification failure	W1 Part 12	services/deployment/	P5
artifact_store_repository	Repository (CAS)	Content-addressable store for all artifacts/assets; validation rings at put; warm-start by hash	W1 §9.1, §4.4	repositories/artifact_store_repository.py	P1
build_state_repository	Repository	builds, transitions, escalations, overrides tables (SQLite); single-writer doctrine	W1 §9.2	repositories/build_state_repository.py	P1
site_bundle_repository	Repository	Materialize bundle to disk, verify hashes, emit bundle_manifest.json, produce deployment ZIP via staging discipline	W1 §9.3, §12.1	repositories/site_bundle_repository.py	P2
cognition_transcript_repository	Repository	Append-only AI exchange store; serves replay; indefinite MVP retention	W1 §9.4	repositories/cognition_transcript_repository.py	P4
scripts/generate_website.py	Operator script	CLI runner (argparse + one service), generate_launch_kit.py pattern; replay-verification script alongside	W1 Part 2, §11.6, P3 roadmap	scripts/	P3
Indexed: 11 engine classes (10 engines + pipeline), 3 services + 4 cognition modules + 2 adapters, 4 repositories, 1 operator script. Counting engines/services/repositories as the brief's unit: 10 engines + 1 pipeline + 3 services + 4 repositories = 18 (cognition cells and adapters indexed as sub-modules of their services).

8. Package and File Map
Consolidated from AES-WEB-001 Part 2 (normative tree) + AES-WEB-002 §29.1 (additive extension, pending amendment A3). This index proposes no tree of its own — it reconciles and presents the two approved trees. Import law: AES-WEB-001 §3.1–3.2 matrix + AES-WEB-002 §29.2 extensions, enforced by the import-audit test (W1 §3.3). Dependency direction: inward toward contracts/.

Public surface (W1 §3.4): exactly what engines/website_generation/__init__.py exports — WebsiteGenerationPipeline, the ten engine classes, artifact models + enums, the exception hierarchy. Everything else is internal; tests import public surface + fixtures only.

Package / file	Purpose	Authority	Allowed imports	Forbidden imports (highlights)	Phase	Visibility
engines/website_generation/contracts/ (artifacts.py, interfaces.py, enums.py, errors.py, versions.py)	Artifacts, protocols, enums, errors, version registries — the only package everyone may import	W1 Part 2; W2 §3.2 additions	stdlib, pydantic_compat only	Everything else (leaf-only, audit-whitelisted)	P1; A (component additions, authorized edits)	Public (via __init__)
constants/ (build.py, brand.py, seo.py, gates.py; new components.py, analytics.py)	Named constants only — every magic number, gate registration, scoring table, recipe table, threshold	W1 Part 2; W2 §29.1 (A3)	stdlib only	Any computation, any package	P1; A	Internal data
speccompiler/	BusinessSpecCompiler	W1 Part 2, §5.1	contracts, constants	sibling engine implementations, repos, services	P1	Public class
brand/ (brand_engine.py, token_resolver.py)	Brand Engine + token resolution	W1 Part 2, §5.2	contracts, constants	same	P2	Class public; resolver internal
ia/	IA Engine	W1 §5.3	contracts, constants	same	P2	Public class
content/ (content_engine.py, content_validators.py)	Content airlock + validators	W1 §5.4	contracts, constants	same	P2	Class public; validators internal
components/ (component_engine.py, registry.py)	Component Engine + registry	W1 §5.5; W2 §15, §29	contracts, constants (+ per-subpackage rules below)	never rendering/, gates/, repositories, services (W2 §29.2)	P2; A	Engine + registry-view accessor public
components/catalog/ (7 family modules, Waves 1–7)	ComponentDefinition data	W2 §29.1	contracts + constants only	everything else, incl. registry	B–H	Internal data
components/selection/ (selector.py, trace.py)	§14 selection pipeline + trace assembly	W2 §29.1	contracts, constants, registry (read-only view)	rendering, gates, repos, services	A	Internal
components/validation/ (binding_validators.py)	Bind-time semantic rules	W2 §29.1	same as selection	same	A	Internal
components/compatibility/ (ranges.py)	Pure semver range evaluation	W2 §29.1	same	same	A	Internal
layouts/	Layout Engine	W1 §5.6	contracts, constants	siblings, repos, services	P2	Public class
rendering/ (renderer.py, html_emitter.py, css_emitter.py, per-family emitter modules internal)	The only markup knowledge in the system; emitter table; CSS emission	W1 §5.7, Part 8; W2 §20, §29.1	contracts, constants	never imports components/ — emitters receive resolved instances, table keyed by id string (W2 §29.2)	P2; B–H	Renderer public; emitters internal
seo/	SEO Engine	W1 §5.8	contracts, constants	siblings	P3	Public class
assembly/	Assembly Engine	W1 §5.9	contracts, constants	siblings	P2	Public class
gates/ (quality_gate_engine.py, checks/ incl. new component_checks.py, composition_checks.py, rendering_checks.py, commercial_checks.py, responsive_checks.py)	Gate engine + check modules; only package allowed to declare a build unfit	W1 §5.10, Part 10; W2 §21, §29.1 (A3)	contracts, constants	siblings, repos, services; checks discovered from explicit list in constants/gates.py, never scanned (W1 §3.5)	P3; I	Engine public; checks internal
pipeline/ (website_generation_pipeline.py, state_machine.py)	Sole composer of engines; pure state machine	W1 Part 2, Part 6	contracts, constants, every engine public class (only module allowed)	repos, services	P1	Pipeline public; state machine internal
repositories/ (4 WGE repos)	Persistence only	W1 Part 9	contracts + storage drivers (sqlite3, pathlib, hashlib, json, zipfile)	engines, services, business logic	P1–P4	Repository classes
services/ (website_generation_service.py, cognition/, deployment/)	Orchestration, AI, deployment	W1 Parts 6–7, 12	engine public classes, repositories, contracts; API client in cognition/ only; transport in deployment/adapters/ only	SQL, rendering logic, scoring logic	P1, P4, P5	Service classes
scripts/generate_website.py	Operator CLI	W1 Part 2	one service, argparse, sys	everything else	P3	Operator entry
tests/website_generation/ (+ fixtures/, fixtures/components/, integration/)	Mirrors package tree; frozen fixtures; golden bundles	W1 Part 11; W2 §29.2 (fixture ownership), §30	public surface + fixtures only	internal helpers	All	Test tier
Deliberate exclusions (W1 Part 2): no ai/ inside engines; no analytics/ package in MVP; no testing/ package inside the engine. Migration ownership (W2 §29.2): migration notes with catalog modules; schema-level migration functions in contracts/versions.py registrations (W1 §4.6).

9. Component-System Quick-Reference
Every row points to the controlling AES-WEB-002 section; values shown for orientation only — the cited section is normative.

9.1 Enumerations
Set	Members (count)	Controlling section
Component families	nav, hero, directory.discovery, listing, profile, trust, cta, content, seo, monetization, social, commerce, form, status, legal + foundation families layout/atom (16 total — see discrepancy D2, §13)	§5.1–§5.16; count bound at §34.1 item 3
PageRole	home, category, city, city-category, search-results, business-profile, comparison, best-of, editorial-guide, collection, service-area, lead-gen-landing, claim-listing, sponsor-page, submission, correction, verification, regional-hub (18)	§6, §6.1
ListingKind	ORGANIC, FEATURED, SPONSORED, VERIFIED, EDITORIAL_PICK, RANKED, CURATED, RECENTLY_ADDED, INCOMPLETE (9)	§6.3 (incl. non-confusion rule)
LifecycleStatus	PROPOSED, EXPERIMENTAL, ACTIVE, PREFERRED, DEPRECATED, RETIRED, BLOCKED (7)	§23
CommercialPurpose	ORIENT … SYSTEM_STATUS (21)	§2.1
ConversionGoal	PHONE_CALL, EMAIL, QUOTE_REQUEST, BOOKING, LISTING_CLAIM, LISTING_SUBMISSION, NEWSLETTER_SIGNUP, SPONSORSHIP_INQUIRY, PAID_UPGRADE, AFFILIATE_CLICK, PURCHASE, COMPARE, SAVE, SHARE, CORRECTION_REQUEST, PROFILE_COMPLETION (16)	§16.2
RegionKind	SKIP, ANNOUNCEMENT, HEADER, BREADCRUMB, HERO, BODY, STICKY_MOBILE, FOOTER (8)	§9.1
Prop types (PropSpec)	STR_ENUM, INT_BOUNDED, BOOL, TOKEN_REF, ASSET_REF, ROUTE_REF, CONTENT_BLOCK_REF, LISTING_REF, COLLECTION_REF, ANALYTICS_LABEL, A11Y_LABEL — no STR type, deliberately (11)	§8.1
Gate families (component)	CG-CON, CG-CMP, CG-RND, CG-A11Y, CG-SEO, CG-COM, CG-RSP (7) — plus 5 inherited W1 families (Structural, Content, SEO, Accessibility, Integrity)	§21.1–21.7; W1 §10.2
Namespaces	bare (shared library), x. (experimental, never certifiable), ext. (reserved, empty), site. (prohibited); reserved family words atlas, internal, test	§4.3
Ethical prohibitions	E1–E11 (false urgency, fabricated reviews, fake scarcity, hidden fees, disguised ads, misleading rankings, a11y-as-friction, manipulative consent, bait-and-switch, fake verification, fake popularity)	§2.6 (enforcement gate per row)
9.2 Budgets and limits
Limit	Value (default)	Controlling section
Complexity budget (BLOCKING at registration)	required_props ≤ 6; optional_props ≤ 10; variants ≤ 6 (excl. density axis); boolean props ≤ 2; score = RP + 0.5·OP + 2·V ≤ 20	§7.3
Composition depth	≤ 6 (shell=1 … atom=6)	§9.2
Sections per BODY	role ceiling, default 12	§9.2 (CG-CMP-011)
Grid columns	≤ 4 desktop, defined collapse	§9.2, §11
Carousels	prohibited except profile.gallery.standard scroll-snap, ≤ 10 items	§9.2
Concurrent sticky regions	≤ 2	§9.2 (CG-CMP-009)
DOM nodes / instance	150 (listing cards 60; shell exempt)	§25
Instances / page	40 (profile 45; lead-gen 20)	§25
Page DOM nodes (bundle gate)	2,500	§25
JS	0 KB required; ≤ 30 KB deferred enhancement; 0 third-party scripts; 0 external requests	§24, §25
Images / page	40 (gallery pages 60)	§25
Fonts	≤ 2 families / ≤ 4 faces, font-display: swap, self-hosted	§25
SEO link blocks	≤ 24 links/block, ≤ 2 blocks/page; footer links ≤ 40	§5.9, §5.15
Sponsored per page	≤ 3 inventory pages; 1 home; 2 search-results; 0 best-of ranked / editorial / correction / verification	§6.2, §17.2, §26.5
Form friction	quote/lead ≤ 6, newsletter ≤ 2, claim step-1 ≤ 5, correction ≤ 5, sponsor ≤ 6; required fields ≤ 4	§16.5 (CG-COM-010)
CTA repetition	1 primary per region; primary goal ≤ 3× per page	§16.3 (CG-CMP-007)
CTA hierarchy conflicts	recipe primary_goal wins; recipe-declared order resolves the rest	§16.6 (CG-COM-011)
9.3 Cross-cutting contracts
Topic	Rule locus	Controlling section
Breakpoints	only `breakpoint.sm	md
Responsive support matrix	320/375/768/1024/1440/1920 px; 200% zoom reflow; landscape; +100% text; touch-only & keyboard-only	§11.4
Canonical responsive transformations	header→drawer, filters→drawer, sticky CTA <md, table scroll-x/stacked, density compaction, ToC jump-select	§11.5
Accessibility severity levels	BLOCKING / WARNING / INFO — full defect mapping	§12.7 (elevations require W1 amendment A2)
Interactive state machines	drawer, accordion, tabs, gallery, dialog (P3), pagination, rating (P3)	§12.6
Token taxonomy	domain.role.qualifier — color/typography/spacing/layout/shape/icon/motion/interaction/responsive/media/density	§10.2
Selection scoring	PREFERRED +100; intent +50; monetization +30; brand affinity +20; asset availability +10; tie-break score → lexicographic id → highest version	§14.2 steps 6–7
Analytics attributes	data-atlas-c/-v/-var/-e/-l/-k (+ reserved -x); event registry names-only in MVP	§18.1–18.3
Variant vs new component decisions	governance decision table	§7.2
Component vs not-a-component	classification discipline	§28.3
10. Page-Role Reference
Summarized from the §6.1 matrix, §6.2 normative details, and §26 recipes — the cited sections are the law; this table is the map. Implicit on every role: layout.shell.page, nav.skip.link, nav.header.standard, legal.footer.directory (§6.1 preamble); breadcrumbs required except home and lead-gen-landing (§6.2). Wave = first AES-WEB-002 phase at which the role's recipe can resolve end-to-end (recipes fill from selection, so a role needs its components' waves delivered).

PageRole	Recipe §	Required major groups (beyond implicit)	Primary conversion goal	Monetization allowance	SEO expectations	Trust requirement	Required status/empty state	Wave/phase
home	26.1	hero.search.directory; category grid	Search-mediated discovery (no form goal)	1 featured zone max	WebSite (+SearchAction), Organization; links to all top categories/cities	REC value/trust strip	F (none)	D
category	26.2	Compact category hero; filters/sort/results summary; listing cards	Listing click	≤ 3 sponsored interleaved	ItemList + BreadcrumbList; linking floors §6.2	O	R zero-results (CG-STR-006)	E
city	26.3	Local hero; category-in-city navigator; listing cards	Category/listing click	O	City-hub link role; nearby cities + parent region	O local facts	R zero-results	E
city-category	26.4	Compact local hero; filters/results; listing cards	QUOTE_REQUEST or PHONE_CALL per spec	≤ 3 sponsored	Programmatic workhorse; floors strictly gated (CG-SEO-004)	O	R zero-results / sparse variant	F (quote CTA)
search-results	26.5	Results header (no hero); filters/sort; compact rows	Listing click	≤ 2 sponsored, disclosed	Typically noindex (SEO Engine); crawl-safe regardless	F	R zero-results	E
business-profile	26.6	Profile header (H1 owner); contact panel; profile cluster; review summary; contact/call/quote CTA cluster + cta.sticky.mobile	PHONE_CALL (default; spec may set QUOTE_REQUEST)	Premium sections after core facts only	LocalBusiness + Breadcrumb (+AggregateRating genuine only); NAP parity (CG-SEO-008)	R review summary	R unavailable/closed/pending	F–H (states in H)
comparison	26.7	Comparison hero; methodology (E6); comparison table; per-row + page CTA	COMPARE → outbound/profile click	O affiliate P3 only	Row headers; scroll-x/stacked (CG-RSP-004)	R methodology	R empty-comparison	G
best-of	26.8	Editorial hero; ranking methodology; ranked cards + per-rank rationale	Listing click	F sponsored in ranked list; O separated featured block	Article/ItemList	R methodology (E6)	O	G
editorial-guide	26 preamble (deferred → G/H); §6.1 row	Editorial hero; related guides + categories	Contextual	O	Article; related-link obligations	R author/source disclosure	F	G/H
collection	deferred → G/H; §6.1 row	Collection hero; collection cards	O	O	CollectionPage	O	R empty state	G/H
service-area	deferred → G/H; §6.1 row	Local hero; providers serving area; area + parent links	REC quote	O	areaServed via LocalBusiness	O	R zero-results	G/H
lead-gen-landing	26.11	Condensed header (only reduced-nav role); offer hero; form.lead.quote single goal	QUOTE_REQUEST (all other goals forbidden)	F	Typically noindex; F SEO links	R trust adjacent to form (CG-COM-009)	R form success/error	F
claim-listing	26.10	Explainer hero; verification explanation; form.claim.standard	LISTING_CLAIM	O upgrade preview, disclosed, after form (E10 adjacency)	—	R verification explanation	R states	F
sponsor-page	26.9	Offer hero; evidenced audience statistics; pricing; inquiry form; paid-placement disclosure	SPONSORSHIP_INQUIRY	R paid-placement disclosure	—	R evidenced statistics (CG-COM-003)	R states	H
submission	26.12	Compact hero; submission form; equal-weight free path	LISTING_SUBMISSION	O paid fast-track, disclosed	—	REC editorial standards link	R states	F
correction	26.13	Minimal hero; listing summary; correction form	CORRECTION_REQUEST	F — no monetization of any kind	—	REC data-source disclosure	R states	F
verification	deferred → G/H; §6.1 row	Minimal hero; listing summary; verify CTA	Verify	F	—	R verification methodology	R pending state	G/H
regional-hub	deferred → G/H; §6.1 row	Regional hero; region navigator; child-region link grids	O	O	Child-region linking	O regional statistics	R sparse-region state	G/H
Per-role internal-linking floors/ceilings, structured-data assignments, mobile behavior, and per-role accessibility/performance ceilings: §6.2 (numeric values live in constants/components.py). Five deferred recipe tables close in AES-WEB-002G/H under §26's rules (§34.2).

11. Quality-Gate Index
Execution authority, ordering, severities, and the two-fixture law: AES-WEB-001 Part 10. Component gate catalog: AES-WEB-002 §21. Gate registration: explicit list in constants/gates.py — never scanned (W1 §3.5). Universal, all gates: known-good + known-bad fixture pair required or the gate cannot register (W1 §10.4); fixture IDs fx-<gate_id>-good|bad (W2 §21); failure diagnostics must name page route, instance path, component id/version, violating value (W2 §21). Severity semantics: BLOCKING = certification impossible; WARNING = recorded, certification allowed; INFO = advisory (W1 §10.1). Blueprint tier mapping (MB Part 8.0 ↔ W1 §10.1): hard → BLOCKING, soft → WARNING (waivable via escalation, logged), advisory → INFO.

11.1 Inherited AES-WEB-001 gate families (W1 §10.2; MVP set, Phase 3)
Family	Examples	Severity	Owning module
Structural	route presence, no orphans, internal links resolve, nav integrity, zero-state rule (CG-STR-006, cited by W2 — see D3 in §13)	BLOCKING	gates/checks/structural_checks.py
Content	no unfilled slots/placeholders, length bounds, escaped-output verification	BLOCKING	content_checks.py
SEO	title/description presence + limits, canonical correctness, sitemap↔routes parity, schema validity	BLOCKING (presence) / WARNING (optimization)	seo_checks.py
Accessibility	contrast, alt text, heading sanity, landmarks	BLOCKING (alt, contrast) / WARNING — elevated by amendment A2: heading-hierarchy + landmark defects become BLOCKING	accessibility_checks.py
Integrity	file hashes vs CAS, provenance resolution, manifest completeness, engine-version consistency	BLOCKING	integrity_checks.py
11.2 Component gate families (W2 §21; fixtures accumulate in phases B–H, registration assembled in phase I)
Shared per family below: input artifacts = ComponentManifest + registry + rendered output + upstream artifacts as applicable (W2 §21 preamble); implementation phase = 002I (registration) with fixtures from the component's own wave; fixture pair required per gate. Remediation owners per gate: see the cited table (R=registry, CE=Component Engine, CT=content, RN=renderer, RC=recipe/LayoutPlan).

Family	Module	Governing §	Gates (severity; all BLOCKING unless noted)
CG-CON — Contract	component_checks.py	§21.1	CG-CON-001…010 (10)
CG-CMP — Composition	composition_checks.py	§21.2	CG-CMP-001…010; CG-CMP-011 W (11)
CG-RND — Rendering	rendering_checks.py (extends structural_checks.py)	§21.3	CG-RND-001…010 (10)
CG-A11Y — Accessibility	accessibility_checks.py extensions	§21.4	CG-A11Y-001…011 B; CG-A11Y-012 B/W split (summary/association B, autocomplete W); CG-A11Y-013 W (13)
CG-SEO — SEO	seo_checks.py extensions	§21.5	CG-SEO-001…003, 005, 006, 008, 009 B; CG-SEO-004 B/W split (floors B, ceilings W); CG-SEO-007 W (9)
CG-COM — Commercial	commercial_checks.py	§21.6	CG-COM-001…008, 011, 012 B; CG-COM-009 W (elevation deferred, §34.2); CG-COM-010 W (12)
CG-RSP — Responsive	responsive_checks.py	§21.7	CG-RSP-001…008 (8)
Enumerated component gates: 10+11+10+13+9+12+8 = 73 individually defined gate IDs. AES-WEB-002 §21's closing line states "63 component gates" — an internal count discrepancy recorded as D1 in §13; the enumerated tables are the operative list pending authority clarification. Do not create new gate IDs; do not renumber existing ones (this index included).

Failure routing (W2 §21 close; W1 §10.3/§6.7): any BLOCKING failure → GATE_REJECTED; commercial/content failures → targeted rework (CONTENT_DRAFTING re-entry scoped to failing slots); contract/composition failures → deterministic-stage terminal, fix-and-rebuild.

11.3 Blueprint gate battery (intent level)
The full conceptual battery — strategy/integrity, content, structural, machine-readability, experience, trust/compliance, assembly/deployment, adversarial — is MB Part 8.1. It exceeds the MVP set (e.g., information-gain gates, prediction registration, red-team clearance, AI-retrieval simulation). Unimplemented Blueprint gates are intent, not open defects; they enter implementation only through an authority document. Gate-suite versioning and re-certification doctrine: MB Part 8.0 items (3)–(5).

12. Implementation Roadmap Index
12.1 Consolidated phase catalog
Global rules for every phase (both roadmaps): full regression suite green, zero regressions; complete files; ZIP staging + extraction confirmation; zero-touch outside authorized modifications; stop on regression / import-audit failure / unauthorized-file need / contract ambiguity (W1 Part 13 preamble; W2 §31 preamble). Regression command: python -m pytest tests/ -q (fast loop: tests/website_generation/components/).

Phase	Deliverable core	Contracts frozen at exit	Artifacts introduced/amended	Key packages touched	Major acceptance criteria	Governing §
W1-P1 Contracts, spine, golden skeleton	contracts/, constants/, BusinessSpecCompiler, CAS repo, build-state repo, pure state machine, pass-through skeleton pipeline	All artifact schemas v1; state/transition tables	All 12 artifact schemas; BusinessSpec live	contracts, constants, speccompiler, repositories, pipeline	Golden BuildManifest hash reproduced twice; ~45–55 tests	W1 Part 13
W1-P2 Deterministic manufacturing core	Brand/IA/Component/Layout/Renderer + minimal registry, CSS emitter, Assembly, bundle repo	Engine interfaces	BrandPackage…SiteBundle live	brand, ia, components, layouts, rendering, assembly, repositories	Fixture spec → real static site, byte-stable; ~60–80 tests. Scope note A4: the "minimal component registry" is superseded by the 002 wave structure; P2's proof lands at 002D exit, completes through 002J	W1 Part 13; W2 §34.3-A4
W1-P3 Gates, SEO, certification, runner	SEO Engine, Quality Gate Engine + full MVP gate set, LaunchCertificate, generate_website.py, replay-verification script	Gate registration mechanism	SEOPackage, QualityReport/LaunchCertificate	seo, gates, scripts	Certified bundle for PetTripFinder-shaped golden spec; ~50–70 tests	W1 Part 13
W1-P4 Cognition layer	Provider pair, prompt contracts, 4 cells, maker/checker, transcript repo, budgets, CLI escalation queue	PromptContracts	ContentCandidate live; transcripts	services/cognition, repositories	Full build with transcripts, replayed to identical hashes network-disabled; ~40–60 tests	W1 Part 13
W1-P5 Deployment	Both adapters, promotion/rollback/verification	DeploymentAdapter usage	DeploymentReceipts	services/deployment	Preview→production promotion + rollback exercised on golden bundle; ~30–40 tests	W1 Part 13
Pre-A AES-WEB-001 v1.1.0 amendment delivery	Apply A1–A4 (§13)	—	ComponentManifest schema 1.0.0→1.1.0 registered	contracts (authorized edits)	Amendments applied by version bump before 002A ships	W2 §34.3, §35 Q8
002A Contracts & registry foundation	Component-contract schema frozen; empty governed registry; selector skeleton; validation/compatibility subpackages	ComponentDefinition schema, naming grammar, enums, ComponentRegistryView	ComponentManifest + selection_trace (minor bump)	contracts*, constants (components, analytics), components/*	Registry loads/validates empty + 2 synthetic defs; deterministic selection + traces; import audit green; manifest round-trips with/without trace	W2 §31
002B Wave 1 primitives (15)	catalog/layout_atoms.py + 15 emitters + fixtures + snapshots; fixture authoring generators (§35 Q10)	—	—	catalog, rendering*, registry tuple*	All 15 ACTIVE-eligible; double-render hash equality; CSS emitter handles token deps	W2 §31
002C Wave 2 nav & shell (8)	catalog/navigation.py, drawer SM tests, skip-link/landmark fixtures	—	—	catalog, rendering	Fixture page: shell+header+drawer baseline+footer passes CG-CMP-005/006, CG-A11Y-002/009/011 fixtures	W2 §31
002D Wave 3 discovery (9)	catalog/discovery.py, facet crawl-safety + zero-results fixtures	—	—	catalog, rendering	Home + category pages compose from recipes §26.1–26.2 via real selection (not hand-pinned) — also W1-P2 proof point (A4)	W2 §31
002E Wave 4 listings & profiles (12)	catalog/listings_profiles.py, all 9 ListingKind fixtures, stretched-link tests	—	—	catalog, rendering	Profile page passes composition + NAP parity; sponsored/featured distinguishable (CG-COM-001 fixtures)	W2 §31
002F Wave 5 trust/conversion/forms (13)	catalog/trust_conversion.py, friction-budget + CTA hierarchy fixtures	—	—	catalog, rendering	Lead-gen + claim pages resolve; every E1–E11 rule has a failing fixture proving enforcement	W2 §31
002G Wave 6 SEO/editorial (7)	catalog/seo_editorial.py, linking floor/ceiling fixtures, 5 remaining recipe tables	Remaining recipes	—	catalog, rendering, constants	≥ 20 generated city-category fixture pages pass CG-SEO-004/007	W2 §31
002H Wave 7 monetization/legal/status (8)	catalog/monetization_status.py, disclosure fixtures	—	—	catalog, rendering	Every §6.1 monetization cell exercisable; every role's required states resolvable	W2 §31
002I Gate families	5 new check modules; all component gates registered + fixture pairs	Gate IDs + severities	—	gates/checks, constants/gates*	Gate-integrity suite: every gate fires both directions; QGE runs extended list deterministically. Integration, not greenfield (fixtures accumulated B–H)	W2 §31
002J MVP integration	All recipes end-to-end from PetTripFinder-shaped fixture spec	—	—	(integration)	Two full fixture sites (simple + every-component) build byte-stably; performance budgets pass; cognition untouched	W2 §31
002K Certification & goldens	Golden bundles + golden manifests (with traces) pinned; registry manifest snapshot; full W1+W2 gate stack → LaunchCertificate	Golden anchors	—	tests/fixtures	Certificate issued; replay reproduces identical hashes; registry-hash → golden-hash linkage documented. Exit: component system DONE for MVP	W2 §31
* = authorized modification of an existing file (zero-touch exception explicitly granted by the phase; see W2 §31 per-phase lists).

12.2 Dependency chain (approved order)
text
W1-P1  Contracts, spine, golden skeleton  (AES-WEB-001 Phase 1)
    ↓
AES-WEB-001 v1.1.0 amendment delivery  (A1–A4, batched — §35 Q8)
    ↓
AES-WEB-002A  Component contracts & registry foundation
    ↓
AES-WEB-002B  Wave 1 primitives            ──┐
    ↓                                        │  W1-P2 engines (Brand/IA/Layout/
AES-WEB-002C  Wave 2 navigation & shell      │  Renderer/Assembly) proceed in
    ↓                                        │  parallel; P2's deliverable proof
AES-WEB-002D  Wave 3 discovery  ◄────────────┘  lands at 002D exit (A4)
    ↓
AES-WEB-002E  Wave 4 listings & profiles
    ↓
AES-WEB-002F  Wave 5 trust, conversion, forms
    ↓
AES-WEB-002G  Wave 6 local SEO & editorial (+ 5 recipes)
    ↓
AES-WEB-002H  Wave 7 monetization, legal, status
    ↓
AES-WEB-002I  Gate families (integration of B–H fixtures)   ← requires W1-P3 Quality Gate Engine
    ↓
AES-WEB-002J  MVP integration (two fixture sites)
    ↓
AES-WEB-002K  Certification & golden fixtures                ← full-regression boundary anchor
    ↓
W1-P4  Cognition layer          (real content replaces fixture content)
    ↓
W1-P5  Deployment               (certified golden bundle promoted/rolled back)
Full-regression boundary: every phase above ends with the entire Atlas suite green (WGE suite + all existing platform suites — W1 §11.1); 002K additionally pins the permanent golden anchors. Minimum path to first real directory (W2 §35 Q2): Waves 1–5 + Wave-7 disclosure/status/legal + six primary recipes + CG-CON/CMP/RND/A11Y + CG-SEO-002/003/004 + CG-COM-001/003/004.
13. Amendment and Conflict Map
13.1 Required AES-WEB-001 amendments (authority: AES-WEB-002 §34.3)
All four are proposed as one batched AES-WEB-001 v1.1.0 delivery before AES-WEB-002A ships (§34.3, §35 Q8). Status is Proposed for all — the source documents establish approval of the underlying decisions (A1, A2 marked "approved" as decisions) but do not establish that the v1.1.0 delivery has shipped; per §0.1, AES-WEB-002 does not act as if the change were already made, and neither does this index.

Amendment ID	AES-WEB-002 source	AES-WEB-001 section affected	Change type	Required action	Impl blocker	Recommended timing	Status
A1 — ComponentManifest.selection_trace	§14.3 (ADR-14), §34.3-A1	§4.1 artifact #6 description; contracts/versions.py schema registry	Additive minor (schema 1.0.0 → 1.1.0, no migration)	Append trace description to artifact #6 Contents; register minor bump	Yes — 002A modifies contracts/artifacts.py under this authorization	In v1.1.0 delivery, before 002A	Proposed (decision approved)
A2 — Accessibility gate severity elevations	§12.7, §21.4, §34.3-A2	§10.2 Accessibility row	Additive minor (strengthens severities; weakens nothing)	Move heading-hierarchy + landmark defects from WARNING to BLOCKING; reference §21.4 family registration under §3.5 mechanism	Yes — 002I gate severities depend on it	v1.1.0, before 002A	Proposed (decision approved)
A3 — Part 2 normative tree extension	§29.1, §34.3-A3	Part 2 package tree; §3.2/§3.3 import-audit whitelist	Additive minor	Authorize components/{catalog,selection,validation,compatibility}/, five new gates/checks/ modules, constants/components.py, constants/analytics.py; extend import-audit whitelist per §29.2	Yes — 002A creates these files	v1.1.0, before 002A	Proposed
A4 — Part 13 Phase 2 scope note	§34.3-A4	Part 13 Phase 2 wording	Clarification (no contract change)	Note that P2's "minimal component registry" is superseded in scope by the 002 wave structure; P2 proof achieved at 002D exit, completed through 002J	No (prevents roadmap misreading)	v1.1.0	Proposed
13.2 Implied amendments identified by this index (not formally enumerated in §34.3)
ID	Source	Affected	Change type	Note	Status
IMP-1 — BuildManifest version-axes + registry identity recording	W2 §22.1 ("extends AES-WEB-001 §4.6's two-axis recording with component axes — additive"); §15.2 (registry_version/registry_hash recorded in every ComponentManifest and BuildManifest)	W1 §4.6 (BuildManifest recorded axes), §4.1 artifact #12 description	Additive minor	The ComponentManifest half is arguably covered by A1's schema bump; the BuildManifest half is not listed in §34.3. Recommend the operator fold it into the v1.1.0 delivery so §22.1's "additive" claim is formally authorized rather than assumed	Identified — needs Chief Architect disposition
13.3 Resolved-without-amendment clarification (recorded in W2 §34.3 closing)
ID	Ambiguity	Resolution	Authority
CL-1	W1 §5.5 "Registry additions minor" — do variant additions and definition-version majors force registry version changes?	Variant additions are also registry-minor; a component-definition major does not force a registry major	W2 §22.2, §34.3 closing paragraph (consistent clarification, no W1 change needed)
13.4 Internal discrepancies (recorded, not resolved — consult the controlling authority)
Per the brief for this index: conflicts are recorded, never silently resolved. Each row names the operative reading pending an authority-side fix (a patch/minor bump of AES-WEB-002).

ID	Discrepancy	Locations	Operative reading (and why)	Needed fix
D1	"63 component gates" stated vs 73 gates enumerated (10+11+10+13+9+12+8)	W2 §21 closing line vs §21.1–21.7 tables	The enumerated gate tables — they are the normative definitions with IDs, severities, and owners; the prose count is a summary figure	W2 patch: correct the count (or identify which gates the count excludes)
D2	"Fourteen top-level families" stated vs 16 families defined and bound	W2 §5 preamble vs §5.1–5.16 + §34.1 item 3 ("Sixteen-family taxonomy")	16 — §5.16 explicitly adds layout/atom beyond the original brief's list, and §34.1's binding-decision list says sixteen	W2 patch: update the §5 preamble
D3	CG-STR-006 (zero-state rule) cited as an existing AES-WEB-001 structural-family gate, but W1 defines gate families only — no individual gate IDs appear in AES-WEB-001	W2 §6.2, §21.2 (CG-CMP-010 note), §27.4/§27.8 vs W1 §10.2	CG-STR-006 is a W1-Phase-3 gate ID to be registered in constants/gates.py; W2 references it prospectively. Its ID reservation is covered by 002A's authorized constants/gates.py edit ("gate ID reservations")	None strictly required; W1-P3 delivery must register CG-STR-006 (and the rest of the structural IDs) consistently with W2's citations
D4	Blueprint gate tiers (hard/soft/advisory) vs W1 severities (BLOCKING/WARNING/INFO)	MB Part 8.0 vs W1 §10.1	Not a conflict: W1 §10.1 declares one-to-one mapping (hard→BLOCKING, soft→WARNING, advisory→INFO); recorded here so nobody re-derives it	None
13.5 Cross-document conflict scan result
No conflict requiring a weakening of AES-WEB-001 was identified by AES-WEB-002 (§34.3 closing), and this index's own pass found none between the Blueprint and AES-WEB-001 — the Blueprint's broader plane/artifact set is authorized MVP scoping, not contradiction (see §2 scope note and §4 coverage map). All live issues are the amendments and discrepancies tabulated above. Amendments identified: 4 formal (A1–A4) + 1 implied (IMP-1) = 5, plus 1 clarification (CL-1) and 4 recorded discrepancies (D1–D4).

14. Frozen-Contract Register
Contracts implementation sessions must not alter without an authority amendment. "Additive OK?" = may an implementation session extend it additively under an explicitly authorized modification in its phase scope; "Change?" = may implementation change existing semantics (always No — that is what "frozen" means; the amendment process column is the only path).

#	Contract	Owning authority & section	Version locus	Amendment process	Additive OK?	Change by implementation?
1	Artifact schemas (all 12)	W1 §4.1, §4.6	contracts/versions.py per-kind semver	Minor = additive optional fields; major = registered migration or declared rebuild	Only via schema minor authorized in-phase (e.g., A1 in 002A)	No
2	Canonical serialization + hash identity	W1 §4.3	shared helper in contracts/	W1 version bump	No	No
3	Dependency matrix / import law	W1 §3.1–3.2 (+ W2 §29.2 extension)	import-audit test	W1 amendment (A3 pattern)	Only via authorized whitelist extension	No
4	Engine public interfaces (one class, one verb, typed errors)	W1 Part 5	ENGINE_VERSIONS registry	Engine-version bump rules W1 §4.6	No	No
5	State machine states + transition table	W1 §6.2	static tables in pipeline/state_machine.py	W1 amendment	No	No
6	Cognition boundary + PromptContracts	W1 Part 7	contract_version, template hashes	Template change without version bump is a build-breaking offense (§7.3)	New cells via registration in constants	No
7	ComponentDefinition schema (§3 field set)	W2 §3; frozen at 002A exit (§31)	component-contract schema version (contracts/versions.py)	W2 §0 policy: normative-rule change ≥ minor; frozen-contract change = major	No	No
8	Component naming grammar + namespaces + permanent IDs	W2 §4	— (grammar constants)	W2 major (§0 amendment policy)	No	No
9	Registry identity, explicit tuple, lexicographic ordering, registry_hash	W2 §15.2	registry_version	W2 amendment; entries added via governed delivery (§15.2 extension process)	Entries yes (that is the extension process); mechanics no	No
10	Ownership map (single source of truth per concern)	W2 §3.1	—	W2 amendment	No	No
11	Selection pipeline order, static scoring tables, tie-breaking	W2 §14.2 (ADR-03)	scoring tables in constants/components.py	W2 major (selection determinism)	No	No
12	selection_trace placement + bounding	W2 §14.3 (ADR-14)	ComponentManifest schema	W2 amendment + schema bump	No	No
13	PageRole enum (18) + §6.1 composition matrix	W2 §6	contracts/enums.py	W2 amendment	No	No
14	ListingKind semantics + non-confusion rule	W2 §6.3	contracts/enums.py	W2 amendment (doctrine-adjacent: E-series)	No	No
15	Prop type system (no STR) + slot cardinality model	W2 §8 (ADR-02)	component-contract schema	W2 amendment	No	No
16	Composition/nesting limits (depth 6, parental spacing, prohibited compositions)	W2 §9 (ADR-11)	constants/components.py	W2 amendment (revisit trigger: ≥3 recipes blocked by same rule)	No	No
17	Accessibility severity map	W2 §12.7 (+ W1 A2)	gate severities in constants/gates.py	W2 + W1 amendment pair	No	No
18	SEO authority split (components declare, SEO Engine compiles)	W2 §13.1	—	W2 amendment	No	No
19	Ethical-conversion rules E1–E11	W2 §2.6 (ADR-12: "Never" revisit)	gate enforcement table	Doctrine — tactics reviewed within E1–E11 only	No	No
20	Lifecycle states + promotion criteria + approval authority	W2 §23	LifecycleStatus enum	W2 amendment; transitions are Chief Architect acts recorded as data	No	No
21	Versioning classes + eternal replay guarantees (definitions never edited in place)	W2 §22; W1 §4.6	pinning tests per released version	W2/W1 amendment; ADR-10	No	No
22	Gate IDs + severities (component catalog)	W2 §21	constants/gates.py	W2 amendment; no new gate IDs from sessions; 002I registers, never invents	Fixture pairs yes; IDs/severities no	No
23	Implementation-phase boundaries + authorized-modification lists	W2 §31; W1 Part 13	phase definitions	Authority amendment; exceeding scope is a universal stop condition	No	No
24	Performance thresholds + JS budget	W2 §24–25	constants/build.py, constants/components.py	W2 amendment (ADR-07 revisit: dynamic-bundle seam)	No	No
25	Fixture minimums per ACTIVE component	W2 §30.2	registration test	W2 amendment; fixtures frozen at generation, never silently regenerated (§35 Q10)	Additional fixtures yes; minimums no	No
Frozen contracts registered: 25.

15. Engineer Lookup Guide — "Where do I look?"
Question	Read first	Then read
Where should this code live?	W1 Part 2 package layout	W2 §29.1 refinements + §29.2 placement rules
Can this file import that one?	W1 §3.2 dependency matrix	W2 §29.2 forbidden-imports extension; import-audit test W1 §3.3
Is this a prop or a content slot?	W2 §8.2 (the copywriter test)	W2 §3.1 ownership map; §8.1 type set
Can this component contain another component?	W2 §9 (esp. §9.4 prohibitions)	The component's registry allowed_child_components / forbidden_child_components (§3)
Which components may appear on this page role?	W2 §6.1 matrix	§26 recipe for the role; §27 inventory role columns
Who owns structured data?	W2 §13.1–13.2 (declare vs compile)	W1 §5.8 SEO Engine; CG-SEO-005/006/008
Can AI choose a component?	W2 §14 (No — ADR-03)	W1 §1.3 litmus test; Part 7 cognition boundary
Where does selection reasoning live?	W2 §14.3 (in-manifest trace)	Amendment A1 (§13 of this index); W1 §4.1 #6
Is this accessibility defect blocking?	W2 §12.7 severity map	§21.4 gate table; amendment A2 status (§13)
Can we retry this failure?	W1 §6.3 retry policy	§6.7 failure routing; §6.2 state machine
Does this require a new artifact?	W1 §4.1–4.2 (one producer per kind)	W2 §14.3 rejected-alternatives reasoning (the anti-casual-artifact precedent); §28.1(b)
How do I add a component?	W2 §2.2 (entry + emitter + fixtures + tests + gates)	§15.2 extension process; §23 promotion criteria; §30.2 fixture minimums
Variant, prop, or new component?	W2 §7.2 governance decision table	§7.3 complexity budget
Which token may I use?	W2 §10.2 taxonomy	§10.3 policy (no fallbacks); component's declared design_token_dependencies
Where do breakpoints live?	W2 §11.1 (tokens only)	§11.3 ResponsiveContract fields; §11.5 canonical transformations
What must a form look like?	W2 §12.3 + §16.5 budgets	§5.13 family rules; CG-A11Y-012, CG-COM-007/010
How is sponsored content rendered?	W2 §6.3 non-confusion rule	§17 disclosure architecture; CG-COM-001/002/012; §26.8 best-of prohibition
What may a CTA say?	W2 §16.2 goal→label table (E9)	§16.3 repetition; §16.6 conflict resolution; CG-COM-008/011
Where do numbers/thresholds go?	W2 §25 close ("every numeric lives in constants")	W1 Part 2 constants/ doctrine
How do I ship this delivery?	W2 §31 global rules (ZIP staging, regression command)	W1 §9.3 staging discipline; Atlas invariants (W1 header)
A gate seems wrong — can I edit it?	W2 §14 of this index row 22: No	W1 §10.4 two-fixture law; escalate per stop conditions W2 §31
What changed between certified builds?	BuildManifest (W1 §6.9)	LaunchCertificate (§10.3); replay verification §11.6
Can I read the clock / generate a UUID?	Never in engines — W1 invariants, W2 §0.2	Time as generated_at; identity as content SHA-256 (W2 §4.2 instance IDs)
Why does this doc say X and that doc say Y?	§13 of this index (amendments + discrepancies)	The controlling authority per §3 hierarchy — then file an index/authority correction
What comes after MVP?	W2 §28 expansion doctrine, §34.4 next documents	MB Parts 9–10 (learning loop, ten-year vision); W2 §35 Q9 deferral list
16. Terminology Glossary
Definitions are one-line orientations; the cited section is authoritative.

Term	Meaning	Controlling section
Artifact	Frozen, versioned, content-addressed Pydantic model crossing a stage boundary; the only inter-stage channel	W1 §1.1, Part 4
Provenance	The source_hashes chain from every artifact to every input that produced it, back to model transcripts	W1 §4.1, §7.5
Content-addressed storage (CAS)	Store keyed by SHA-256 of canonical serialization; dedup, integrity, warm-start for free	W1 §1.5, §9.1
Canonical serialization	UTF-8 JSON, sorted keys, no insignificant whitespace, explicit nulls, one shared helper	W1 §4.3
Deterministic	Same inputs + same versions ⇒ byte-identical output; no AI/I-O/clock/randomness/UUIDs	W1 §1.1; W2 §2.4
Replay	Re-running a historical build from manifest + transcripts to identical hashes; the audit mechanism	W1 §1.1, §7.6, §11.6; W2 §22.3
Component definition	Declarative frozen registry entry describing one component's identity + contracts	W2 §3
Component instance	A definition bound to props/content/variant on one page, identified by content-derived hash	W2 §4.2; artifact #6
Prop	Typed structural configuration ("how should this render?"); never free-form text	W2 §8.1–8.2
Content slot	Typed binding to ContentPackage blocks ("what does it say/show?") with cardinality	W2 §8.2
Variant	Named, registered, contract-complete rendering mode of one component (id::variant)	W2 §7.1, §4.2
Page role	Closed-enum commercial page type; one per page; drives composition law	W2 §6
Region	Structural page zone (RegionKind); parent constraint for placement	W2 §9.1
Selection trace	Deterministic per-slot record of candidates/eliminations/scores/choice, embedded in ComponentManifest	W2 §14.3
Registry hash	SHA-256 of the canonical serialization of all definitions in registered order; replay anchor for selection	W2 §15.2
Commercial purpose	The closed-enum reason a component exists; "it looks nice" is not one	W2 §2.1
Conversion goal	Closed-enum outcome a conversion-bearing component drives; maps to permitted labels/targets/events	W2 §16.2
ListingKind	Closed enum on every listing block declaring organic/paid/verified/etc. semantics	W2 §6.3
Quality gate	Registered, ordered, typed pass/fail check with mandatory good+bad fixtures; only path to certification	W1 Part 10; W2 §21
LaunchCertificate	Signed certification token — the only thing deployment accepts	W1 §10.3; MB Part 8.2
Golden build	Pinned end-to-end fixture build whose bundle + manifest hashes anchor regression	W1 §11.5; W2 002K
Lifecycle state	Registry-tracked component maturity (PROPOSED…RETIRED, BLOCKED) — never a variant	W2 §23, §7.1
Compatibility range	Per-definition semver ranges vs renderer/token-schema/registry versions, checked at bind (CG-CON-008)	W2 §3, §22.1
Cognition cell	Sealed unit of AI work: one responsibility, one PromptContract, one output schema	W1 §7.2; MB Plane 10.3
Maker/checker	Independent producer/reviewer cells; a model never approves its own work; checker advisory, engine law	W1 §7.7; MB Part 3.0
Escalation	ESCALATED_HUMAN pause with recorded options (rework/override/cancel); the designed 5%	W1 §6.8; MB Plane 10.5
Override	Human-authorized gate bypass, permanently recorded in manifest + certificate, studied as a gate-design bug report	W1 §6.8, §10.3; MB Part 8.0
Recipe	Declarative default component sequence per page role, with flexible zones	W2 §26
Ethical-conversion doctrine	E1–E11 prohibitions enforced as BLOCKING gates; trust as asset value	W2 §2.6 (ADR-12)
Determinism airlock	The Content Engine boundary where AI candidates become validated, escaped, frozen content	W1 §5.4
Zero-touch	No modification of existing files without explicit per-phase authorization	Atlas invariant; W1 header; W2 §31
Glossary terms: 30.

17. Document Maintenance Rules
Update only after an authority document changes. An index edit with no corresponding authority version bump is invalid (exception: fixing an index defect against the current authorities).
Never use this index to establish a new rule. New rules go into the appropriate authority by version bump; the index then maps them.
Every index entry must point to an authority source. An entry without a section citation is a defect.
Renumbering: if an authority section is renumbered, this index is updated in the same documentation change.
Versioning: index version bumps are independent and non-authoritative; the index header records which authority versions it was built against (currently Blueprint v1.0, AES-WEB-001 v1.0.0, AES-WEB-002 v1.0.0).
An index inconsistency never overrides a source document. Discrepancies between index and authority are index defects by definition.
Implementation citations: implementation sessions must cite the source authority (document + section), not only this index, when making architecture-sensitive changes.
Amendment tracking: when the AES-WEB-001 v1.1.0 delivery ships, §13 statuses A1–A4 move Proposed → Applied in the same index update; IMP-1 and D1–D3 are closed when the operator dispositions them.
18. Final Validation
Every major concern has one identified primary authority — §5: 48 concern rows, each with a single primary authority and exact section. ✔
Every artifact has a producer and consumer map — §6: all 12 artifacts + the selection_trace sub-block, each with producer, consumers, invariants, phase. ✔
Every engine has clear inputs, outputs, and ownership — §7.1: 10 engines + pipeline; §7.2: services, cognition modules, repositories, script. ✔
Every implementation phase appears in the roadmap — §12: W1 Phases 1–5, the v1.1.0 amendment delivery, and AES-WEB-002A–K, with dependencies, frozen contracts, acceptance criteria, and execution order. ✔
Every explicit AES-WEB-002 amendment to AES-WEB-001 appears in the amendment map — §13: A1–A4, plus implied IMP-1, clarification CL-1, and discrepancies D1–D4. ✔
No new architecture was introduced — this index adds zero contracts, zero rules, zero gate IDs, zero components, zero packages; §4's coverage map and §13's discrepancy rows describe, they do not decide. ✔
No authority rule was weakened or silently resolved — all conflicts and count discrepancies are recorded in §13 with the controlling authority named; none is resolved by this index. ✔
Section references checked against the source documents — every citation was verified against Blueprint v1.0 (Parts 0–10), AES-WEB-001 v1.0.0 (Parts 1–13), and AES-WEB-002 v1.0.0 (§0–35) during authoring. ✔
Useful as a daily navigation tool — organized as lookup tables (§5–§16) with a question-driven guide (§15); narrative is confined to orientation notes. ✔
End of AES-WEB-INDEX-001 v1.0.0 — Navigation Aid, Non-Authority. In any doubt, read the source. Built against: Master Blueprint v1.0 · AES-WEB-001 v1.0.0 · AES-WEB-002 v1.0.0.


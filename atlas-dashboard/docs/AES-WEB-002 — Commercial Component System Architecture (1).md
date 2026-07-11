
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

AES-WEB-002 — Commercial Component System Architecture (1).md


Atlas Investment OS
AES-WEB-002 — Commercial Component System Architecture
Master Architectural Blueprint and Implementation Authority
0. Document Authority
Field	Value
Document ID	AES-WEB-002
Title	Commercial Component System Architecture
Status	Design Authority — Master Architecture and Implementation Authority
Version	1.0.0
Date	2026-07-10
Supersedes	None
Governs	All design, implementation, extension, and governance of the WGE component system: registry, contracts, taxonomy, selection, variants, composition, component-level quality gates, and the component library roadmap
Upstream authorities	Website Generation Engine Master Blueprint; AES-WEB-001 — Website Generation Engine Implementation Architecture Specification (v1.0.0); Atlas Platform Architecture; Opportunity Intelligence Engine; Directory Builder Engine; Project Assembly System; Investment Committee doctrine
Downstream consumers	Claude Code implementation sessions (AES-WEB-002A…K); Component Engine; Layout Engine; Renderer; SEO Engine; Quality Gate Engine; Deployment Service; regression suite; operator runbooks; Investment Committee (via LaunchCertificate evidence)
Primary implementation packages	engines/website_generation/components/, engines/website_generation/rendering/ (emitters only), engines/website_generation/constants/ (component + gate constants), engines/website_generation/gates/checks/ (component gate families), tests/website_generation/components/
Approval authority	Atlas Chief Architect (operator). Lifecycle transitions per §23.
Amendment policy	Amendments by version bump only, never silently. Any change altering a normative MUST/SHALL rule is at least a minor version. Any change altering a frozen contract, naming grammar, or selection determinism is a major version.
0.1 Authority statement
AES-WEB-001 defines how the Website Generation Engine is built: its packages, artifacts, state machine, cognition boundary, gates, and deployment. AES-WEB-002 defines what the WGE manufactures with: the commercial component system that turns validated content, brand tokens, and site architecture into professional, conversion-capable directory websites.

The relationship to sibling authorities is strict:

Master Blueprint — intent authority. In any conflict, Blueprint intent wins and this document is amended by version bump.
AES-WEB-001 — implementation authority for the pipeline. AES-WEB-002 operates inside AES-WEB-001's architecture. It MUST NOT redefine artifacts, dependency direction, state machine, cognition placement, or repository ownership. Where this document requires an upstream change, it says so explicitly in §34 and does not act as if the change were already made.
Atlas Platform Architecture — flat imports, frozen Pydantic, pure engines, single-writer persistence, zero-touch, complete files, zero regressions. Inherited without exception.
Opportunity Intelligence / Directory Builder / Project Assembly — upstream producers whose outputs reach this system only via BusinessSpecCompiler. No component ever sees a raw upstream model (AES-WEB-001 §2, §7.4).
Component Engine / Layout Engine / Renderer / SEO Engine / Quality Gate Engine — the engines this document programs. Their public interfaces remain as defined in AES-WEB-001 Part 5; this document defines the data, contracts, and rules those engines execute.
Deployment Service / Investment Committee — consumers of certified output. Component-level analytics identifiers (§18) are hooks for the deployment layer; component certification evidence flows to the Committee through the QualityReport/LaunchCertificate exactly as AES-WEB-001 §10.3 defines.
In any conflict between this document and an implementation session, this document wins. In any conflict between this document and AES-WEB-001, AES-WEB-001 wins and §34 records the required amendment.

0.2 Inherited invariants (restated, non-negotiable)
Every rule below is inherited from AES-WEB-001 and Atlas doctrine and applies to every sentence of this document:

Engines are pure and deterministic: no AI calls, no I/O, no network, no UUIDs, no wall-clock reads. Time enters as explicit generated_at; identity is content-derived SHA-256.
Artifact-driven architecture: stage boundaries are artifact boundaries; artifacts are frozen Pydantic models, canonically serialized, content-addressed, immutable, provenance-chained via source_hashes.
Flat imports; dependency direction inward toward contracts/; the import-audit test is law.
The registry is data, not code generation (AES-WEB-001 §8.1). Markup knowledge lives only in rendering/html_emitter.py emitter functions.
AI output enters the pipeline only as validated ContentCandidate → ContentPackage artifacts. Components never invoke, embed, or assume cognition.
The Quality Gate Engine is the only authority that may declare a build unfit; every gate ships with known-good and known-bad fixtures (AES-WEB-001 §10.4).
Zero-touch on existing files; complete files only; ZIP staging discipline; extraction-confirmed delivery; full regression gating; zero regressions tolerated.
Replayability: same inputs + same engine versions + same registry version ⇒ byte-identical output and identical BuildManifest hash.
1. Document Purpose
AES-WEB-002 defines the reusable, versioned, testable, deterministic commercial component ecosystem the WGE uses to assemble directory businesses and other commercial websites.

The component system MUST support websites that: look professionally designed; behave consistently; are responsive from 320px to wide desktop; meet WCAG 2.2 AA; are SEO-safe; are conversion-oriented; support local, regional, national, and niche directory business models; are assembled deterministically; are validated before rendering; evolve without breaking certified builds; are measurable and improvable over time; disclose sponsorship and monetization transparently; remain replayable and auditable; and are reusable across the entire Atlas directory portfolio.

The component system is not a template folder. It is an industrial manufacturing system composed of: component families, normative contracts, governed variants, typed props, typed content slots, semantic roles, layout capabilities, responsive contracts, token requirements, accessibility contracts, SEO contracts, analytics hooks, conversion intent, monetization behavior, nesting rules, validation rules, quality gates, compatibility ranges, versioning rules, deprecation rules, migration rules, and registry governance.

A future Claude Code session implementing any part of this system MUST be able to do so from this document plus AES-WEB-001 alone — without improvising architecture, inventing contracts, or violating Atlas doctrine. Where this document leaves a decision open, it says so explicitly in §34 (Deferred Decisions).

2. Core Design Doctrine
2.1 Components are commercial primitives
A component is a unit of commercial intent rendered as a unit of markup. Every registered component MUST declare exactly one commercial_purpose (primary) and MAY declare secondary purposes, drawn from the closed enum CommercialPurpose:

ORIENT (orient the visitor), COMMUNICATE_VALUE, ESTABLISH_TRUST, SUPPORT_DISCOVERY, REDUCE_UNCERTAINTY, CREATE_LEGITIMATE_URGENCY, COLLECT_LEAD, DRIVE_CALL, SUPPORT_COMPARISON, EXPOSE_INVENTORY, STRENGTHEN_INTERNAL_LINKING, SUPPORT_LOCAL_SEO, IMPROVE_ACCESSIBILITY, INCREASE_ENGAGEMENT, PREPARE_MONETIZATION, IMPROVE_CONVERSION, ENCOURAGE_CLAIM, ENCOURAGE_SPONSORSHIP, ENCOURAGE_SUBMISSION, SATISFY_LEGAL, SYSTEM_STATUS.

A proposed component with no defensible commercial purpose MUST be rejected at PROPOSED lifecycle state (§23). "It looks nice" is not a purpose.

2.2 Components are declarative
The registry (components/registry.py) contains declarative component definitions: frozen data structures describing identity, contracts, and metadata. The registry MUST NOT generate code, import emitters, scan the filesystem, or contain conditional logic. Behavior is expressed through contracts; execution is expressed through registered emitter functions in the Renderer, keyed by (component_id, major_version). Adding a component = registry entry + emitter function + fixture pair + snapshot test (AES-WEB-001 §8.1) — this document adds: + contract tests + gate fixtures per §21/§30.

2.3 Components consume validated artifacts only
Component instances bind only: validated ContentPackage blocks (by block reference), CAS asset references (by content hash), routes declared in SiteArchitecture, and semantic tokens declared in BrandPackage. Components MUST NEVER: call AI models; query databases; perform network requests; read clocks; generate random identifiers; import vendor SDKs; mutate artifacts; read raw upstream Atlas models; accept arbitrary HTML, CSS, or JavaScript; or carry raw database rows.

2.4 Components are deterministic
Given identical: component definition version, prop values, content references, asset references, design tokens, layout context, renderer version, and registry version — output MUST be byte-identical. Class names are token-derived and stable (AES-WEB-001 §5.7). Attribute order is stable. Iteration order over collections is stable-sorted. There is no randomness anywhere in the component system, including in "decorative" choices — decorative variation is a selected variant, never a roll of dice.

2.5 Components are independently testable
Every ACTIVE component and every registered variant MUST ship with: contract-validation tests, known-good fixtures, known-bad fixtures, responsive-contract tests, accessibility tests, semantic-HTML tests, snapshot tests, deterministic-rendering tests (f(x) == f(x) across process restarts), security tests (malicious-content fixtures where the component renders user-influenced content), and quality-gate fixtures. Fixture inventory is normative in §30.

2.6 Ethical-conversion doctrine (binding)
The component system optimizes commercial outcomes within a hard ethical boundary. The following are PROHIBITED by contract and enforced by commercial gates (§21.6); no prop, variant, or content value may produce them:

#	Prohibited pattern	Enforcement
E1	False urgency (countdowns, "only today" without a real, spec-backed offer)	urgency_policy contract: urgency claims MUST reference a BusinessSpec offer field with an expiry; otherwise gate CG-COM-005 blocks
E2	Fabricated reviews or testimonials	Review components accept only ContentPackage review blocks carrying evidence_ref provenance; gate CG-COM-003 blocks unreferenced review content
E3	Deceptive scarcity / fake inventory counts	No component exposes a count prop without a data_source reference; live counts are deferred (no dynamic data in MVP), so scarcity counts are structurally impossible
E4	Hidden fees	Pricing components MUST render disclaimer slots when `pricing_kind = estimate
E5	Disguised advertisements	Every monetized component carries mandatory visible + semantic disclosure (§17); gate CG-COM-001 blocks
E6	Misleading rankings	Ranked lists MUST bind a ranking_rationale content slot or a methodology link; sponsored position is never presented as rank; gate CG-COM-002
E7	Inaccessible interactions as friction	Accessibility gates are BLOCKING; there is no "conversion exception" to accessibility
E8	Manipulative consent patterns	Consent controls MUST present equal-weight accept/decline actions; pre-checked marketing consent is prohibited; gate CG-COM-007
E9	Bait-and-switch copy	CTA label must match conversion_goal action class; gate CG-COM-008 (label/action class table in constants)
E10	Fake verification badges	Verification indicators render only when the listing's verification_state in ContentPackage is VERIFIED; gate CG-COM-004
E11	Fake popularity indicators	Same rule as E3: no unreferenced counters
Rationale: Atlas directories are portfolio assets whose exit value depends on durable trust and clean SEO standing. Dark patterns are short-term revenue borrowed against asset value. The Investment Committee's honest-wall doctrine applies to the websites themselves.

3. Normative Component Contract
Every registered component MUST be described by a ComponentDefinition — a frozen, declarative structure in the registry. The normative field set:

Field	Type (conceptual)	Meaning
component_id	str, naming grammar §4	Permanent stable identity, e.g. hero.split.value-proposition
component_family	enum ComponentFamily	Top-level taxonomy family (§5)
component_version	semver str	Definition version; rules in §22
lifecycle_status	enum LifecycleStatus	PROPOSED…RETIRED (§23)
display_name	str	Human name for catalogs and diagnostics
description	str	One-paragraph purpose statement
commercial_purpose	CommercialPurpose + optional secondary list	§2.1
supported_page_roles	frozenset of PageRole	Which SiteArchitecture page roles may host it
required_props / optional_props	ordered mapping name → PropSpec	§8
required_content_slots / optional_content_slots	ordered mapping name → SlotSpec	§8
supported_asset_roles	frozenset of AssetRole	e.g. LOGO, HERO_IMAGE, GALLERY_IMAGE, ICON
supported_variants	ordered mapping variant name → VariantSpec	§7
default_variant	str	Deterministic fallback
semantic_element	enum	Root element/landmark: section, nav, header, footer, aside, article, form, div
allowed_parent_regions	frozenset of RegionKind	§9 composition model
allowed_child_components	frozenset of component_id patterns	§9; empty = leaf
forbidden_child_components	frozenset of component_id patterns	Explicit denials override allowances
design_token_dependencies	frozenset of semantic token IDs	§10; render fails on undeclared token use
responsive_contract	ResponsiveContract	§11
accessibility_contract	AccessibilityContract	§12: roles, states, focus behavior, labels
seo_contract	SEOContract	§13: heading capability, link semantics, schema capability
analytics_contract	AnalyticsContract	§18: impression/interaction identifiers
conversion_contract	ConversionContract or None	§16: goal, actions, placement, repetition
directory_contract	DirectoryContract or None	§6: listing-kind semantics, disclosure needs
monetization_contract	MonetizationContract or None	§17: disclosure, link attributes, analytics separation
validation_rules	list of rule IDs	Semantic validators the Component Engine runs at bind time
rendering_contract	RenderingContract	Emitter key, stable-class prefix, DOM budget (§25)
compatibility_range	mapping axis → semver range	Renderer, token-schema, registry-schema compatibility (§22)
deprecation_status	DeprecationInfo or None	Since-version, sunset policy
replacement_component_id	str or None	Required when DEPRECATED
quality_gate_requirements	frozenset of gate IDs	Gates that MUST run for instances of this component
example_fixture_ids	frozenset	Registered fixtures (§30); registration test enforces minimum set
3.1 Single source of truth per concern
Authority MUST NOT be duplicated. The binding ownership map:

Concern	Single source of truth	Never in
Component identity, contracts, variants, capabilities	Registry (components/registry.py data + constants/components.py)	Emitters, manifests
Per-instance selection: which component, which variant, bound props, content refs	ComponentManifest (artifact #6)	LayoutPlan, renderer
Selection explainability	selection_trace block inside ComponentManifest (§14; ADR-14)	New artifact (rejected), BuildManifest body
Placement: page regions, order, grid position	LayoutPlan (artifact #7)	ComponentManifest, registry
Visual values: colors, type, spacing, radii, motion	BrandPackage semantic tokens (artifact #2)	Registry, emitters, props
Text/media content	ContentPackage blocks (artifact #5)	Props, registry, emitters
Output markup	Renderer emitters (html_emitter.py) only	Registry, engines, artifacts
Pass/fail authority	QualityReport from Quality Gate Engine	Any engine self-assessment
Analytics identifiers	Registry analytics_contract (declared) → emitted as data- attributes → consumed at deployment layer	Any SDK anywhere in core
Deployment metadata	SiteBundle manifest + deployment receipts	Component system entirely
3.2 Contract placement in code
contracts/artifacts.py: ComponentManifest model incl. ComponentInstance, BoundProp, SlotBinding, selection_trace (schema-versioned).
contracts/enums.py: ComponentFamily, PageRole, RegionKind, CommercialPurpose, LifecycleStatus, ListingKind, ConversionGoal, GateSeverity reuse.
contracts/interfaces.py: ComponentRegistryView (read-only protocol the Component Engine consumes), GateCheck reuse.
constants/components.py (new): naming grammar constants, complexity budgets, repetition limits, DOM budgets, selection scoring tables, CTA label/action table.
components/registry.py: the ComponentDefinition data tables + pure lookup/index functions.
Emitter internals stay internal to rendering/ per AES-WEB-001 §3.4.
4. Component Identity and Naming
4.1 Naming grammar (normative)
component_id  := family "." pattern "." intent
family        := lowercase kebab token from ComponentFamily registry
pattern       := lowercase kebab token (structural/visual pattern)
intent        := lowercase kebab token (commercial/functional intent)
Exactly three segments. Segments are [a-z][a-z0-9-]*, each ≤ 24 chars, full ID ≤ 64 chars. Examples (all real IDs in §27): hero.split.value-proposition, directory.search.primary, listing.card.standard, listing.card.sponsored, profile.header.business, trust.reviews.summary, cta.call.primary, nav.header.standard, seo.local-links.grid, monetization.sponsor.featured, form.lead.quote, status.listing.unavailable.

4.2 Identity rules
Stability. component_id is permanent. Internal implementation, emitter, markup, and even family reassignment (major event) never change the ID. Renaming = new component + deprecation mapping.
Registry key. The registry is keyed by component_id; duplicate registration fails the registry-integrity test at import time.
Variant naming. Variants are single kebab tokens scoped to the component: listing.card.standard::compact. :: is the variant delimiter; variants never appear in component_id.
Version naming. component_id@1.4.0 denotes a definition version. ComponentManifest pins the exact version per instance; the registry serves the version index.
Instance IDs. Per-instance identity inside a manifest is content-derived: sha256(page_route + region_path + component_id + ordinal) truncated per the shared Atlas short-hash helper — no UUIDs. Ordinal = stable index within region.
Human display names live only in display_name and never participate in identity.
4.3 Namespaces
Namespace	Rule
Bare three-segment IDs	The shared Atlas library. Only this document's governance process may add to it.
x. prefix (x.hero.animated.seasonal)	Experimental. May only be selected when the build's experimental_allowed flag is true (default false). Never eligible for LaunchCertificate builds.
ext. prefix	Reserved extension namespace for future non-core packs. Empty in MVP; contracts identical.
site. prefix	PROHIBITED in the shared registry. Site-specific one-offs are not components (§28 distinction); they are application modules or content.
Deprecated components	Keep their ID and namespace forever; lifecycle status marks them. Deprecated IDs are never reused.
Reserved words	atlas, internal, test may not appear as a family segment.
5. Complete Component Taxonomy
Fourteen top-level families. Family membership is permanent per component. For each family the table defines: purpose, permitted page roles (ALL = every role), common variants, required content, forbidden uses, conversion role, SEO/accessibility/monetization notes, and implementation priority (P1 = MVP wave 1–4, P2 = MVP wave 5–7, P3 = post-MVP).

5.1 nav — Navigation and orientation
Covers: announcement bars, utility navigation, main headers, mobile navigation, breadcrumbs, tab navigation, side navigation, footer navigation, mega menus, jump links, skip links.

Aspect	Rule
Purpose	ORIENT, STRENGTHEN_INTERNAL_LINKING
Page roles	ALL (header/footer nav MUST appear on every page; breadcrumbs on all non-home pages)
Common variants	standard, condensed, transparent-over-hero (header); drawer (mobile); mega (P3)
Required content	Nav trees come only from SiteArchitecture nav topology — never hand-authored per page
Forbidden uses	No promotional CTAs inside breadcrumbs; no more than one nav.header.* per page; mega menus forbidden until P3
Conversion role	Indirect; header MAY host exactly one cta.* slot
SEO	Crawlable <a href> links only; breadcrumb schema capability; duplicated nav landmarks forbidden (aria-label disambiguation required when >1 <nav>)
Accessibility	Skip link mandatory as first focusable element on every page; drawer focus trap contract §12
Monetization	None. Nav is never sold.
Priority	P1
5.2 hero — Hero and value communication
Covers: centered, split, search-first, directory, local, editorial, lead-generation, offer, category, city, provider, comparison heroes.

Aspect	Rule
Purpose	COMMUNICATE_VALUE, ORIENT; search-first heroes also SUPPORT_DISCOVERY
Page roles	One hero maximum per page, always first body region
Common variants	centered, split, search-first, compact
Required content	H1 slot (exactly one per page, owned by hero on hero pages), subheading, optional hero asset
Forbidden uses	Multiple heroes; hero on search-results pages (use directory.results.summary header instead); carousel heroes (prohibited entirely — motion + LCP hazard)
Conversion role	Primary above-the-fold action or search
SEO	H1 ownership; hero copy is crawlable text, never text-in-image
Accessibility	Contrast tokens over imagery require overlay.scrim token; text over images MUST pass contrast gate
Monetization	None directly
Priority	P1
5.3 directory.discovery — Directory discovery
Covers: primary search, autocomplete search (P3 — requires JS budget), category navigator, location selector, radius selector (P3), filter panel, filter chips, sort control, results summary, map/list toggle (P3 with map), zero-results state, saved/recent/popular searches (P3 — requires state).

Aspect	Rule
Purpose	SUPPORT_DISCOVERY, EXPOSE_INVENTORY
Page roles	home, category, city, city-category, search-results
Common variants	search: hero-embedded, standalone, condensed; filters: sidebar, top-bar, drawer (mobile)
Required content	Category/location option sets from BusinessSpec directory taxonomy via SiteArchitecture — never free-typed
Forbidden uses	Filters that submit nowhere (MVP filters are crawlable link-based facets, not client state); autocomplete before P3
Conversion role	Discovery → listing click is the top-of-funnel conversion
SEO	Facet links MUST follow crawl-safety rules §13 (indexable facet whitelist; the rest rel="nofollow" + robots rules from SEO Engine)
Accessibility	Filter groups are labeled fieldsets; results summary is a polite live region in future dynamic mode, static text in MVP
Monetization	None inside controls; sponsored results are a listing concern
Priority	P1
5.4 listing — Directory inventory
Covers: listing cards, sponsored listing cards, compact result rows, comparison rows, profile summaries, map markers (P3), category tiles, city tiles, collection cards, featured blocks, recently-added, verified badges, claim-status indicators, availability indicators.

Aspect	Rule
Purpose	EXPOSE_INVENTORY, SUPPORT_COMPARISON
Page roles	home, category, city, city-category, search-results, profile (related), collection, best-of
Common variants	card: standard, compact, featured; row: comparison
Required content	Listing blocks from ContentPackage with listing_kind (§6.3) explicitly set
Forbidden uses	A sponsored listing rendered through listing.card.standard is a gate-blocked violation; badges without matching content state (E10)
Conversion role	Listing click, call click, profile visit
SEO	Card title links are the internal-link backbone; ItemList schema capability at collection level
Accessibility	Whole-card click uses the pseudo-content link pattern; nested interactive controls inside the primary link are forbidden (§9.4)
Monetization	listing.card.sponsored and listing.card.featured carry mandatory disclosure (§17)
Priority	P1
5.5 profile — Business profile components
Covers: profile header, contact panel, hours, service areas, pricing, gallery, amenities, credentials, review summaries, review lists, FAQs, related businesses, claim listing, owner response, booking/contact CTA, map and directions, availability (P3), insurance/payment details, team members (P3), services offered, business description, correction request.

Aspect	Rule
Purpose	REDUCE_UNCERTAINTY, ESTABLISH_TRUST, DRIVE_CALL/COLLECT_LEAD
Page roles	business-profile only (profile summaries elsewhere are listing family)
Common variants	contact panel: sidebar, inline, sticky-mobile
Required content	All facts from ContentPackage listing detail blocks; hours in structured HoursSpec, never free text; phone/email as typed values
Forbidden uses	Rendering unverified claims as verified; pricing without disclaimer slot when estimated
Conversion role	Call/quote/booking on-page conversion cluster
SEO	LocalBusiness schema capability; NAP consistency sourced from single content block
Accessibility	Hours tables are real tables with headers; galleries have per-image alt from content; map has text-directions alternative
Monetization	Premium-profile sections (§17) extend, never gate, core facts — contact info is never paywalled
Priority	P1–P2
5.6 trust — Trust and authority
Covers: review summary, testimonials, logos, statistics, credentials, editorial methodology, verification explanations, guarantees, trust badges, media mentions (P3), author profiles (P3), expert review blocks (P3), data-source disclosure, ranking methodology.

Purpose ESTABLISH_TRUST; roles ALL except legal-only pages; variants strip, grid, inline; required content: every claim binds evidence_ref provenance (E2); forbidden: self-declared badges with no methodology link; conversion role: trust adjacency to CTAs (§16.4); SEO: aggregate-rating schema only when review data is genuine and on-page; accessibility: statistics not conveyed by color alone; monetization: none — trust components are never sold, ever (BLOCKING gate); priority P2.

5.7 cta — Conversion
Covers: primary/secondary CTA, call CTA, email CTA, quote request, sticky mobile CTA, inline signup, newsletter capture, comparison CTA, claim-listing CTA, sponsor CTA, upgrade CTA, submit-listing CTA, correction CTA. (Forms themselves are form family; a CTA is an action affordance.)

Purpose per conversion_contract §16; roles per goal table §16.2; variants primary, secondary, ghost; required content: label + action target (route ref or tel:/mailto: from typed content); forbidden: >1 primary CTA per region, >3 primary CTA instances of same goal per page (repetition limits §16.3), label/goal mismatch (E9); priority P1 (primitives) / P2 (goal-specific).

5.8 content — Content and education
Covers: text section, rich content, feature list, icon list, process steps, FAQ, accordion, glossary, resource cards, related guides, table of contents, editorial callouts, pros and cons, comparison tables, statistics blocks, expert tips, checklist, warning/notice blocks.

Purpose REDUCE_UNCERTAINTY, SUPPORT_LOCAL_SEO (editorial); roles ALL content-bearing; variants density comfortable|compact; required content: RichTextBlock slots (§8.4 safe model); forbidden: accordions hiding primary page content (§13.3), comparison tables without header rows; conversion role: supportive; SEO: FAQ schema capability on content.faq.standard; accessibility: accordion/tabs state machines §12.6; priority P1 (text section) / P2 (rest).

5.9 seo — Local and programmatic SEO
Covers: nearby-city links, related-category links, service-area links, neighborhood grids (P3), regional navigation, local facts, location introduction, category introduction, dynamic FAQ, directory statistics, structured-data support, crawl-safe pagination, canonical guidance (SEO Engine concern — components only declare), related locations, nearby listings, parent-region links.

Purpose SUPPORT_LOCAL_SEO, STRENGTHEN_INTERNAL_LINKING; roles category/city/city-category/profile/home; variants grid, inline-list, columns; required content: link sets derived from SiteArchitecture internal-link topology — components never invent URLs; forbidden: hidden link blocks, link stuffing beyond constants-declared per-block ceilings (default: 24 links per block, ≤2 blocks per page); conversion: none; accessibility: link lists are real lists with a labeled heading; monetization: PROHIBITED — paid links never appear in SEO link blocks; priority P2.

5.10 monetization — Monetization
Covers: featured listing, sponsored placement, promoted card, sponsor ribbon, premium profile section, advertising disclosure, native ad block (P3), upgrade prompt, lead-purchase block (P3), affiliate comparison (P3), partner offer (P3), membership pricing, sponsor inquiry, paid-placement disclosure.

Purpose PREPARE_MONETIZATION, ENCOURAGE_SPONSORSHIP; roles per §17; every component in this family has a non-null monetization_contract — the registry-integrity test enforces this; forbidden: any rendering path without visible disclosure; priority P2 (disclosure + sponsored/featured) / P3 (affiliate, native, lead-purchase).

5.11 social — Social proof and engagement
Covers: review carousel (P3 — carousels restricted §9.4), user ratings display, favorites/save/share controls (P3 — require state or JS), vote/helpfulness (P3), recently viewed (P3), popular searches (P3), trending categories (P3), social proof counters (P3, E11-constrained), user-submitted photos (P3).

MVP includes only static rating display (trust.reviews.summary covers it). Everything interactive/stateful in this family is P3 by decree — Atlas MVP output is static (AES-WEB-001 §8.5). Priority P3.

5.12 commerce — Commerce and pricing
Covers: pricing cards, service pricing, package comparison, quote ranges, pricing disclaimers, plan selectors (P3), purchase CTA, checkout handoff (P3), lead pricing (P3), sponsorship pricing.

Purpose PREPARE_MONETIZATION, REDUCE_UNCERTAINTY; roles sponsor-acquisition, profile, lead-gen landing; required content: typed PriceSpec (§8.4) with currency, kind (exact|from|range|estimate), and mandatory disclaimer slot for non-exact kinds (E4); forbidden: checkout logic (Atlas MVP hands off to external URLs with correct link attributes); priority P2 (sponsorship pricing, disclaimers) / P3 (rest).

5.13 form — Forms and input
Covers: contact form, quote form, claim form, listing submission, correction request, newsletter form, multi-step intake (P3), search filters (rendered under directory.discovery), consent controls, validation messaging, success/error states, spam-protection state, file-upload placeholder architecture (P3).

Aspect	Rule
Purpose	COLLECT_LEAD, ENCOURAGE_CLAIM, ENCOURAGE_SUBMISSION
Page roles	profile, lead-gen landing, claim, submission, correction, sponsor pages
Required structure	Field primitives from Wave 1 only; every field labeled; error summary region; success/error state variants; honeypot + time-trap spam architecture (server-agnostic, static-compatible)
Forbidden uses	Fields beyond friction budget (§16.5: quote ≤ 6 fields, newsletter ≤ 2, claim ≤ 5 at first step); pre-checked consent (E8); forms without declared action_route
MVP posture	Static HTML forms posting to an endpoint declared in BusinessSpec.form_endpoint (external form handler); no client-side hydration required; enhancement JS optional and budgeted
Priority	P2
5.14 status — System and status
Covers: empty states, loading states (P3 — static sites don't load asynchronously in MVP), error states, maintenance notice, unavailable listing, closed business, pending verification, pagination (shared with nav), notification banners, stale listing notice, archived listing notice, no-JavaScript fallback (default — the site IS the no-JS fallback).

Purpose SYSTEM_STATUS, REDUCE_UNCERTAINTY; roles ALL; zero-results and unavailable/closed/pending states are MVP-mandatory (P2) because directories always have inventory gaps; forbidden: dead-end states (every status component MUST bind at least one recovery action — link to parent category/city); priority P2.

5.15 legal — Footer and legal
Covers: standard footer, directory footer, local footer variant, disclosure block, copyright block, privacy links, terms links, accessibility statement, advertising disclosure, editorial standards, data-source disclosure, contact links.

Purpose SATISFY_LEGAL, ESTABLISH_TRUST; roles ALL (footer mandatory everywhere); required content: legal facts from BusinessSpec legal footer fields; forbidden: footer link farms (footer SEO links capped at constants ceiling, default 40), hiding mandatory disclosures below fold-only visibility tricks; priority P1 (footer) / P2 (statements).

5.16 layout / atom — Structural and atomic primitives (foundation families)
Not in the original brief's family list but required as the composition substrate (§9): page shell, section container, grid, stack, split, card shell, plus atom primitives (button, link, image, icon, badge, alert, form-field). These are the Wave 1 primitives. They carry no commercial purpose beyond ORIENT/IMPROVE_ACCESSIBILITY and exist to make every other family deterministic and consistent. Priority P1.

6. Directory-Specific Component System
Atlas manufactures directory businesses. This section is the commercial heart of the document: it defines page-role composition law for the eighteen directory page types. PageRole is a closed enum in contracts/enums.py; SiteArchitecture assigns exactly one role per page; the Component Engine selects against that role.

6.1 Page-role composition matrix
Legend: R required, REC recommended, O optional, F forbidden. Component groups reference §5 families and §27 IDs. Every page implicitly requires: layout.shell.page, nav.skip.link, nav.header.standard, legal.footer.directory (R on all roles; not repeated below).

PageRole	Hero	Discovery	Listings	Profile	Trust	CTA cluster	SEO links	Monetization	Status
home	R hero.search.directory	R category grid, REC location grid	REC featured (disclosed)	F	REC value/trust strip	REC claim + submit CTAs, REC newsletter	REC nearby cities	O featured block	F
category	R hero.category.standard (compact)	R filters/sort links, R results summary	R listing cards	F	O	REC claim CTA	R related categories + cities	O sponsored cards inline	R zero-results
city	R hero.city.standard	R category-in-city navigator	R listing cards	F	O local facts	REC	R nearby cities + parent region	O	R zero-results
city-category	R compact local hero	R filter links, results summary	R listing cards	F	O	REC quote CTA	R nearby city-category links	O sponsored	R zero-results
search-results	F (results header instead)	R results summary, filters, sort	R compact rows or cards	F	F	O	O related searches	O sponsored (disclosed, capped)	R zero-results
business-profile	F (profile header instead)	O related search	REC related listings	R full profile cluster	R review summary	R contact/call/quote cluster, REC claim if unclaimed	REC nearby same-category	O premium sections	R unavailable/closed/pending states
comparison	R comparison hero	O	R comparison rows/table	F	R methodology	R per-row CTA + one page CTA	REC	O affiliate (P3, disclosed)	R empty-comparison
best-of	R editorial hero	O	R ranked listing cards + rationale	F	R ranking methodology (E6)	REC	R related best-of links	F sponsored inside ranked list; O clearly-separated featured block	O
editorial-guide	R editorial hero	O	O embedded listings	F	R author/source disclosure	O contextual	R related guides + categories	O	F
collection	R collection hero	O	R collection cards	F	O	O	REC	O	R empty state
service-area	R local hero	O	R providers serving area	F	O	REC quote	R area + parent links	O	R zero-results
lead-gen-landing	R hero.leadgen.offer	F	O social proof listings	F	R trust adjacent to form	R form.lead.quote (single goal)	F (minimal nav variant)	F	R form success/error
claim-listing	R compact explainer hero	F	O preview of listing	F	R verification explanation	R form.claim.standard	F	O upgrade preview (disclosed)	R states
sponsor-page	R offer hero	F	O example placements	F	R audience statistics (evidenced)	R sponsor inquiry form, R sponsorship pricing	F	R paid-placement disclosure	R states
submission	R compact hero	F	F	F	REC editorial standards link	R form.submission.listing	F	O paid-fast-track (disclosed)	R states
correction	R minimal hero	F	R listing being corrected (summary)	F	REC data-source disclosure	R form.correction.standard	F	F	R states
verification	R minimal hero	F	R listing summary	F	R verification methodology	R verify CTA	F	F	R pending state
regional-hub	R regional hero	R region navigator	REC top listings per child region	F	O regional statistics	O	R child-region link grids	O	R sparse-region state
6.2 Per-role normative details
For every role the following are binding (values in constants/components.py where numeric):

Component order. Default sequence per role is a recipe (§26). LayoutPlan MAY reorder only within the recipe's declared flexible zones.
Navigation expectations. Breadcrumbs required on every role except home and lead-gen-landing. Lead-gen landing uses nav.header.condensed (logo + one exit link) to protect conversion focus — the only role where reduced nav is permitted.
Internal linking. Category pages MUST link: parent taxonomy, sibling categories (≤12), top cities (≤12). City pages MUST link: parent region, nearby cities (≤12), categories in city (≤16). Profile pages MUST link: category page, city page, ≥3 related profiles when inventory permits. These floors/ceilings live in constants and are gate-checked (CG-SEO-004).
Structured data. home: WebSite (+SearchAction when search exists); category/city/city-category/search-results: ItemList + BreadcrumbList; profile: LocalBusiness (+AggregateRating only when genuine on-page reviews exist) + BreadcrumbList; best-of/editorial: Article/CollectionPage + ItemList; all: Organization on home only. Components declare capability; SEO Engine compiles (§13.1).
Monetization opportunities. Declared per role above; global rule: sponsored slots per page ≤ constants ceiling (default 3 on inventory pages, 1 on home, 0 on best-of ranked lists, editorial, correction, verification).
Trust requirements. Any page with a lead form MUST place a trust component within the same or adjacent region (gate CG-COM-009, WARNING in MVP).
Conversion goals. Exactly one primary conversion_goal per role (recipe-declared); competing goals resolve per §16.6.
Empty/error states. Every inventory-rendering role MUST bind its zero-results/sparse-state component with a recovery action; a category page that would render zero listings and no state component fails gate CG-STR-006 (BLOCKING).
Mobile behavior. Contact/quote cluster on business-profile MUST include cta.sticky.mobile bound to the role's primary goal; filter panels transform to drawer (§11.5).
Accessibility. Role-specific: search-results summary text MUST announce result count; comparison tables MUST provide row headers; profile hours MUST be a <table> with scope attributes.
Performance. Per-role component-count ceilings (§25): inventory pages ≤ 40 instances, profile ≤ 45, lead-gen ≤ 20.
6.3 Listing-kind semantics (binding)
ListingKind is a closed enum carried on every listing content block and consumed by the directory_contract:

Kind	Meaning	Visual/semantic requirements
ORGANIC	Ranked by the directory's deterministic ordering rules	No badge; default treatment
FEATURED	Paid placement in a dedicated featured zone	"Featured" label token + disclosure ribbon; rendered only via listing.card.featured; never interleaved into organic rank order
SPONSORED	Paid placement interleaved with results	"Sponsored" label, distinct surface token color.surface.sponsored, rel="sponsored" on outbound links, capped per page
VERIFIED	Ownership/facts verified per methodology	Badge renders only when content verification_state = VERIFIED (E10); verification is orthogonal to payment and MUST never be sold as a bundle with placement
EDITORIAL_PICK	Chosen by stated editorial methodology	Requires methodology link binding (E6)
RANKED	Position derives from disclosed algorithmic ranking	Requires ranking_rationale slot
CURATED	Manually curated collection membership	Collection context discloses curation
RECENTLY_ADDED	Recency-ordered	Date sourced from content block, rendered as static text (no clock reads)
INCOMPLETE	Missing required profile facts	Muted treatment, "unclaimed/limited info" state, claim CTA attached
Non-confusion rule (BLOCKING, CG-COM-001/002): paid kinds (FEATURED, SPONSORED) MUST be visually and semantically distinguishable from organic results at a glance — distinct surface token, textual label, and machine-readable data-listing-kind attribute. A paid listing rendered indistinguishably from organic is a certification-blocking defect, not a style choice.

7. Component Variants
7.1 Variant taxonomy
A variant is a named, registered, contract-complete rendering mode of one component. Distinct concepts, each with its own mechanism — conflating them is the root cause of design-system rot:

Concept	Mechanism	Example
Visual variant	supported_variants entry	hero.split.value-proposition::image-right
Density variant	Shared density axis (`comfortable	compact`) — one axis, globally defined
Behavioral variant	Separate variant only when interaction contract differs	nav.mobile.drawer vs inline
Commercial-intent variant	Usually a separate component, not a variant (a sponsored card is a different contract)	listing.card.sponsored ≠ listing.card.standard::sponsored
Page-role variant	Prop context_role when only labeling differs; separate component when structure differs	city hero vs category hero share hero.local.standard with role prop
Responsive adaptation	NOT a variant — owned by responsive_contract (§11)	card grid collapse
Content-driven state	NOT a variant — deterministic function of bound content	claimed vs unclaimed profile header
Lifecycle state	NOT a variant — registry lifecycle_status	—
Experimental variant	x.-namespace component or variant flagged experimental	x.hero.animated.seasonal
7.2 Governance decision table (normative)
Situation	Action
New optional presentation detail, same markup skeleton	Add optional prop (enum, never boolean pairs)
Same contract, meaningfully different arrangement	Add variant
Different required props/slots, different accessibility state machine, or different commercial/monetization contract	New component
≥3 components sharing a pattern grammar with no family	New family (Chief Architect approval; family list is a versioned enum)
Variant unused across portfolio for 2 registry minor versions	Deprecate variant
One component serving two page roles with divergent contracts	Split
Two components whose contracts converged to identical	Merge (new component, deprecate both with replacement mapping)
Experimental variant passes promotion criteria §23	Promote (rename out of x., i.e., register new + deprecate experimental)
Proposed variant fails complexity budget or duplicates an existing variant's outcome	Reject with recorded rationale
7.3 Complexity budget (BLOCKING at registration)
Per component: required_props ≤ 6; optional_props ≤ 10; variants ≤ 6 (excluding the global density axis); boolean props ≤ 2 (prefer enums); complexity score = required_props + 0.5·optional_props + 2·variants ≤ 20. Exceeding the budget fails the registry-integrity test; the remedy is splitting the component, and the split requires the formal review recorded as an ADR appendix entry. Mega-components are a prohibited failure mode, not a tolerated smell.

8. Prop and Content-Slot Architecture
8.1 Prop type system
PropSpec types form a closed set: STR_ENUM (registered enum only), INT_BOUNDED, BOOL (budget-limited), TOKEN_REF (semantic token ID, validated against BrandPackage token schema), ASSET_REF (CAS hash + AssetRole), ROUTE_REF (must exist in SiteArchitecture), CONTENT_BLOCK_REF, LISTING_REF, COLLECTION_REF, ANALYTICS_LABEL (grammar-constrained slug), A11Y_LABEL (non-empty str, length-bounded). Free-form strings are prohibited as props — any human-readable text is content and belongs in a slot. There is no STR prop type, deliberately.

Rules: optional means "may be omitted, default applies"; nullable is prohibited (absence is the only null); every optional prop declares a default in the registry; defaults are deterministic constants; validation occurs at Component Engine bind time (compile error, not render error — AES-WEB-001 §5.5); prop serialization in ComponentManifest is canonically sorted; unknown props are a bind error.

8.2 Props vs content slots
Props configure structure; slots carry substance. A prop answers "how should this render?" (variant axis, column count, which token). A slot answers "what does it say/show?" (heading text, review blocks, images). The test: if a copywriter would ever want to change it, it is a slot; if only an architect would, it is a prop. Slots bind ContentPackage block references with declared block types and cardinality (exactly_one, zero_or_one, one_to_n(max)).

8.3 Ownership rules (binding)
Content → ContentPackage. Structural configuration → ComponentManifest. Placement → LayoutPlan. Visual styling → BrandPackage semantic tokens. Output markup → Renderer only.
Assets referenced by content hash only. Components MUST NOT embed arbitrary HTML, accept arbitrary CSS, accept unvalidated JavaScript, carry raw database rows, or perform business queries. (Restates §2.3 as prop-layer law: there is no prop type that could smuggle any of these in.)
8.4 Typed content models (safe-by-construction)
These block types are Content Engine contracts (defined in contracts/artifacts.py as ContentPackage block schemas); components consume, never define them:

Data	Model rule
Rich text	RichTextBlock: constrained node tree (paragraph, h2–h4, list, link, em/strong, blockquote) — never raw HTML; escaped at Content Engine, re-escaped at emission
Links	LinkSpec: route ref or validated absolute URL + link kind (`internal
Lists/tables	Typed row/cell structures with mandatory header declarations
Reviews/ratings	ReviewBlock (author display, rating 1–5, body RichText, date-as-data, evidence_ref); RatingSummary (count, mean, distribution)
Contact info	ContactSpec: E.164 phone, validated email, address struct — rendered by emitters into tel:/mailto: deterministic formats
Business hours	HoursSpec: per-day open/close/closed structures; "open now" computation is PROHIBITED (clock read) — hours render as stated schedule
Prices	PriceSpec: decimal-as-string, ISO currency, kind (`exact
Geographic data	GeoSpec: lat/lng decimals-as-strings, service-area region refs
Credentials	CredentialBlock with issuer + evidence_ref
Sponsorship disclosure	DisclosureBlock: disclosure kind enum + RichText body from constants-registered templates
Ranking rationale	RationaleBlock: methodology link + RichText summary
9. Allowed Nesting and Composition
9.1 Composition model
The page is a tree: Page Shell → Regions → Section Containers → Layout primitives (grid/stack/split) → Components → Atoms. RegionKind closed enum: SKIP, ANNOUNCEMENT, HEADER, BREADCRUMB, HERO, BODY (ordered section list), STICKY_MOBILE, FOOTER. Overlays/drawers/modals are projected regions owned by their triggering component's contract (MVP: mobile nav drawer and filter drawer only; modal dialogs are P3 and modal-from-modal is permanently forbidden).

9.2 Depth and structure limits (constants, gate-checked)
Max composition depth 6 (shell=1 … atom=6). Max sections per BODY: role-dependent ceiling (default 12). Grids: max 4 columns desktop, defined collapse (§11). Carousels: MVP prohibits all carousels except profile.gallery.standard in scroll-snap (CSS-only) mode, max 10 items. Sticky elements: max 2 concurrent per viewport (nav.header + one of {cta.sticky.mobile, filter bar}) — gate CG-CMP-009.

9.3 Ownership within composition
Heading hierarchy: page shell owns H1 delegation (hero or profile header); section containers own H2; components own H3+ internally; skipping levels is gate-blocked. Landmarks: shell emits header/main/footer; nav components emit <nav> with aria-label when multiple. Section labels: section container binds optional heading slot; child components MUST NOT duplicate it. Grid/padding/background: layout primitives own spacing tokens and surface tokens — child components are surface-agnostic and MUST NOT set outer margins (spacing is parental, the single most important anti-drift rule in the visual system). Interaction & focus: the component that opens an overlay owns its focus management contract.

9.4 Prohibited compositions (gate-enforced)
Cards inside cards (unless the outer is layout.card.shell acting as pure surface — flagged exception in registry); multiple H1s; primary-CTA duplication beyond repetition limits; >1 carousel per page; content hidden from crawlers to manipulate ranking; tabs/accordions without their accessibility state machine; arbitrary spacing overrides (no spacing props except from the parental scale); nested interactive controls (a link/button inside a clickable container is BLOCKING — cards use the stretched-link pattern with sibling interactive elements outside the link's DOM subtree); duplicated nav landmarks without labels; competing sticky regions; recursion (a component family may not appear within its own subtree except layout.* primitives, which may nest to the depth limit).

10. Design Token Dependencies
10.1 Token consumption law
Components consume semantic tokens only — never hard-coded values, never raw palette entries. The CSS emitter compiles BrandPackage tokens to custom properties once per build (AES-WEB-001 §8.3); component emitters reference token classes only. A component referencing an undeclared token fails at render with a named-token diagnostic, and the integrity gate re-verifies at bundle level.

10.2 Semantic token taxonomy (the contract surface)
Token IDs follow domain.role.qualifier. The component system depends on these domains (full scale values are BrandPackage's concern, from AES-WEB-001's Brand Engine):

Color roles: color.action.primary|secondary, color.action.primary.hover|active|disabled, color.surface.page|raised|elevated|sponsored|featured|inverse, color.text.default|muted|inverse|link|error|success, color.border.default|strong, color.focus.ring, color.overlay.scrim.
Typography roles: typography.heading.display|1|2|3, typography.body.default|small, typography.label.default, typography.price.default.
Spacing scale: spacing.0…spacing.12 plus semantic spacing.section.small|medium|large, spacing.stack.default, spacing.inline.default.
Layout: container.width.narrow|default|wide, grid.columns.2|3|4, grid.gap.default.
Shape/elevation: radius.card|control|badge|full, border.default, shadow.raised|elevated|sticky.
Iconography: icon.size.sm|md|lg; icons are registered SVG assets by hash, referenced via ASSET_REF with AssetRole.ICON.
Motion: motion.duration.fast|base, motion.easing.standard; every motion token has a reduced-motion resolution (§10.4).
Interaction: focus.ring.default (mandatory dependency for every interactive component), state tokens above.
Responsive: breakpoint.sm|md|lg|xl — the ONLY breakpoint authority (§11.1).
Media: aspect.card|hero|gallery, image.treatment.default (object-fit/position policy), overlay.scrim.
Density: density.comfortable|compact multipliers applied by the CSS emitter, never per-component.
10.3 Token policy
Each ComponentDefinition declares design_token_dependencies exhaustively; the registry-integrity test cross-checks declarations against the emitter's stable-class output for the component's fixtures. Fallback policy: there are no runtime fallbacks — an unresolvable token is a build failure, not a degraded render (determinism forbids "best effort"). Compatibility: compatibility_range pins the token-schema version; a BrandPackage produced under an incompatible token schema fails component binding with a named diagnostic. Contrast: Brand Engine embeds computed contrast ratios (AES-WEB-001 §5.2); the accessibility gate verifies every text/surface token pairing a component declares meets WCAG 2.2 AA (4.5:1 body, 3:1 large text/UI).

10.4 Mode readiness (contract-level, not MVP implementation)
Dark mode, high-contrast, and forced-colors are NOT built in MVP, and the contracts guarantee they can be later without component changes: components reference roles, so a future dark BrandPackage is purely a token recompilation; emitters MUST NOT use color values in markup; focus rings and borders use tokens so forced-colors degradation is systematic; motion.* tokens compile with a prefers-reduced-motion block zeroing durations — reduced motion IS in MVP because it costs one emitter rule.

11. Responsive Architecture
11.1 Authority
Breakpoints exist in exactly one place: breakpoint.* tokens (defaults: sm 480, md 768, lg 1024, xl 1440 — values in BrandPackage token defaults, seeded from constants/brand.py). No component may carry bespoke breakpoints (restating AES-WEB-001 §8.2 as component law). Everything is mobile-first: base styles are the 320px render; enhancements apply upward.

11.2 Ownership split
Concern	Owner
Which adaptations a component supports (ResponsiveContract: collapse mode, stacking order, truncation policy, sticky capability)	Registry
Which adaptation an instance uses on a given page	LayoutPlan (within contract)
Breakpoint values, density multipliers	BrandPackage tokens
Media-query emission, stable responsive classes	Renderer/CSS emitter
Verification (no horizontal overflow, touch targets, order sanity)	Quality gates (CG-RSP-*)
11.3 ResponsiveContract fields
collapse_behavior (grid → 1-col stack point per grid token), mobile_order (explicit ordinal or dom-order — visual reorder without DOM reorder is prohibited above the section level to keep focus order sane), content_priority (which optional slots hide at sm — hidden-at-breakpoint content MUST be non-essential and is gate-checked against SEO hidden-content rules), truncation (none|line-clamp(n) with full text in DOM), sticky (none|top|bottom + z-token), table_adaptation (scroll-x|stacked-rows — data loss prohibited), image_behavior (aspect token + responsive srcset policy emitted by renderer from CAS asset renditions), touch_target (min 44×44 CSS px for all interactive elements — token-derived, gate-verified).

11.4 Mandatory support matrix
Every ACTIVE component MUST hold its contract at: 320px, 375px, 768px, 1024px, 1440px, 1920px; 200% browser zoom (WCAG 1.4.10 reflow: no 2-D scrolling at 320 CSS px equivalent); landscape phone; dynamic text resize +100% without clipping; touch-only and keyboard-only operation. MVP verification is deterministic (emitted CSS analysis + contract assertions + fixture snapshots at each width class), not screenshot diffing (deferred per AES-WEB-001 Part 13).

11.5 Canonical transformations
Navigation: header inlines ≥ md, drawer < md (drawer markup always present, CSS/<details>-driven or minimal budgeted JS). Filter panel: sidebar ≥ lg, top-bar md, drawer < md with result-count affordance. Sticky CTA: cta.sticky.mobile renders < md only, bottom-anchored, single instance, never overlapping footer legal text (scroll-margin rule). Tables: comparison tables scroll-x with sticky first column ≥ md, stacked label/value rows < md. Cards: density auto-compacts < sm via density multiplier. Long content: content.toc.standard collapses to jump-select < md.

12. Accessibility Architecture
Baseline: WCAG 2.2 AA, binding for every ACTIVE component. Accessibility contracts are registry data; verification is gate-enforced; there is no commercial exception (E7).

12.1 Structural requirements
Semantic HTML per semantic_element; landmark set exactly one main, one page header/footer, labeled navs; heading hierarchy per §9.3 (no skips, one H1); skip link first-focusable on every page; reading order equals DOM order.

12.2 Interaction requirements
Full keyboard operability for every interactive contract; visible focus (focus.ring.default, ≥3:1 contrast, never outline:none without replacement); focus order follows DOM; touch targets ≥44px (WCAG 2.5.8 exceeds AA minimum — Atlas adopts 44 anyway as constants-declared policy); no keyboard traps except managed dialog/drawer traps with Escape release.

12.3 Forms
Every field has a programmatic <label>; grouped controls use fieldset/legend; instructions precede fields and are aria-describedby-linked; error summary region at form top linking to fields; inline errors programmatically associated; autocomplete attributes on identity fields (name, email, tel, postal) per HTML spec; success/error status components use role="status"/role="alert" appropriately; disabled controls remain perceivable (contrast-compliant disabled tokens) and are never the only path forward; recovery: submitted data is never destroyed by validation failure (static form pattern preserves via standard browser behavior; enhancement JS must not break it).

12.4 Content requirements
Contrast per §10.3; images: alt from content slots (alt-text cell drafts, Content Engine validates non-empty for informative images; decorative images declared decorative=true render alt=""); icon-only controls carry A11Y_LABEL props (required, not optional); rating displays render text equivalents ("4.6 out of 5, 128 reviews") with stars aria-hidden; maps ship text directions + address as the primary accessible path; no information by color alone; video/audio contracts (P3) pre-committed to captions/transcript slots.

12.5 Live regions and status
MVP static sites have minimal live-region needs; contracts still declare them for enhancement mode: form async status role="status", filter result updates polite live region (P3 dynamic mode). Status components (§5.14) use role="status"; blocking errors use role="alert".

12.6 Interactive state machines (registry-declared, test-enforced)
Every interactive component family declares its accessibility state machine in accessibility_contract; fixtures assert emitted ARIA:

Family	State machine (normative summary)
Drawer (nav/filter)	closed→open: focus moves in, trap active, aria-expanded on trigger, aria-modal on drawer; Escape/close→trigger refocused
Accordion	Buttons with aria-expanded + aria-controls; panels labeled by headers; arrow-key optional, Tab mandatory
Tabs	tablist/tab/tabpanel roles, roving tabindex, arrow-key switching, aria-selected
Gallery (scroll-snap)	List semantics, each image alt-labeled, visible next/prev links (not hover-only), no autoplay
Dialog (P3)	role="dialog" + label, trap, Escape, return focus; no dialog-from-dialog
Pagination	nav labeled "Pagination", aria-current="page" on current
Rating input (P3)	Radio-group pattern with labeled options
12.7 Severity mapping
BLOCKING: missing alt on informative images; contrast failures; missing labels; keyboard inoperability; missing skip link; heading-hierarchy violations; nested interactive controls; touch-target violations; landmark duplication without labels; broken dialog/drawer state machine. WARNING: suboptimal reading order within a section; missing autocomplete; verbose alt text (> length ceiling); redundant link text. INFO: enhancement opportunities. Elevating heading/landmark defects to BLOCKING strengthens AES-WEB-001 §10.2 (which lists them as sanity/warning-tier) — recorded as required amendment §34.3.

Every accessibility gate ships known-good + known-bad fixtures per AES-WEB-001 §10.4; §30 lists the mandatory accessibility fixture per component.

13. SEO Architecture
13.1 Authority split (binding)
Components declare SEO capability; the SEO Engine remains authoritative for site-wide compilation (titles, meta, canonicals, robots, sitemap — AES-WEB-001 §5.8). A component's seo_contract declares: heading capability (which levels it may emit), link semantics it emits (internal|outbound|sponsored|nofollow per bound LinkSpec), schema capability (which schema.org fragments it can contribute), and content-visibility class (always-visible|progressive-disclosure). The SEO Engine consumes SiteArchitecture + ContentPackage; the Assembly Engine injects compiled SEO metadata into rendered pages (AES-WEB-001 §5.9) — deterministic because both inputs are hashed artifacts and injection points are stable marked positions in the page shell (<head> block, JSON-LD block before </body>), never string-searched.

13.2 Structured-data compilation
Components contribute schema fragments as data (declared capability + bound content refs recorded in ComponentManifest); the SEO Engine compiles fragments into page-level JSON-LD, deduplicates, validates against the constants/seo.py schema-type registry, and emits into SEOPackage. Components never emit JSON-LD themselves — this prevents duplicate/conflicting markup by construction. Supported MVP types: WebSite (+SearchAction only where a real query route exists), Organization (home only), BreadcrumbList, ItemList, LocalBusiness, AggregateRating (genuine on-page reviews only), FAQPage (visible FAQ content only), Article, CollectionPage, ProfilePage, service-area via areaServed on LocalBusiness.

13.3 Component SEO rules (gate-enforced)
Headings: per §9.3 ownership; no hidden keyword headings.
Links: internal links are plain crawlable <a href>; paid outbound links carry rel="sponsored" (CG-SEO-002, BLOCKING); user-influenced outbound links rel="nofollow ugc"; affiliate (P3) rel="sponsored nofollow".
Pagination: crawl-safe numbered <a> links; self-canonical pages; no infinite scroll in MVP; page=1 canonicalizes to the base route (SEO Engine rule).
Canonicals: components never declare canonicals; facet views beyond the indexable-facet whitelist are canonicalized/robots-managed by the SEO Engine from SiteArchitecture route metadata.
Hidden content: accordion/tab content is in-DOM and crawlable; components MUST NOT diverge user-visible and crawler-visible content (CG-SEO-006); primary page content MUST NOT sit solely inside collapsed disclosure on load.
Duplicate blocks: the same content block bound on more than a constants-declared page count triggers WARNING CG-SEO-007 — the tripwire against lazy programmatic templating.
Local-business info: NAP renders from the single ContactSpec block; visible NAP ↔ LocalBusiness markup parity is gate-checked (CG-SEO-008).
Robots/pagination metadata: never component-level; SEO Engine only.
14. Deterministic Component-Selection Logic
14.1 Selection function
Selection inside the Component Engine is a pure function:

select(page, slot_needs, registry_view, spec, brand, build_flags)
    -> (component_instances, selection_trace)
Inputs, all from artifacts: SiteArchitecture page role and content-slot types; BusinessSpec business model, directory taxonomy, monetization configuration, geography; BrandPackage voice/design profile flags; available asset roles; recipe-declared conversion objective; registry lifecycle/compatibility data; implementation-phase capability flags from constants. No randomness anywhere.

14.2 Selection pipeline (normative order)
Candidate filtering — supported_page_roles includes the role AND slot signature satisfiable.
Compatibility filtering — compatibility_range satisfied against renderer / token-schema / registry versions.
Lifecycle filtering — ACTIVE/PREFERRED eligible; DEPRECATED only with explicit recorded build allowance; x. only when experimental_allowed (never certifiable).
Required-capability matching — recipe slot capabilities (e.g. "hero-with-embedded-search") all present.
Commercial-purpose matching — candidate purpose matches the recipe slot's declared purpose.
Stable scoring — additive integers from static tables in constants/components.py: PREFERRED +100; exact intent match +50; monetization-config alignment +30; brand-profile affinity (registry profile tags × BrandPackage flags) +20; optional-asset availability +10. Integer arithmetic only.
Deterministic tie-breaking — highest score → lexicographic component_id → highest version. Total order guaranteed.
Variant selection — same pipeline over VariantSpecs; default_variant is the terminal fallback.
Fallback and failure — every recipe slot declares a guaranteed-satisfiable fallback (Wave 1/2 primitive). If even the fallback is filtered out, raise ComponentResolutionError naming the slot, every candidate, and the eliminating filter per candidate. Selection never silently drops a required slot; optional slots eliminate silently but traced.
14.3 Selection trace (binding decision, ADR-14)
Every decision is recorded in a selection_trace block embedded in ComponentManifest as a schema-versioned optional section: per slot — candidates considered, eliminations (filter ID each), scores, tie-break application, chosen (component_id, version, variant). Alternatives rejected: a new artifact (expands AES-WEB-001's 12-artifact catalog for data no downstream stage consumes — a casual artifact addition); BuildManifest embedding (the manifest is the pipeline's audit projection, not a carrier of engine-internal reasoning); audit-only side metadata (breaks replay-verifiability by leaving the CAS provenance chain). The embedded trace is deterministic (a pure function of a deterministic selection), hashes with the manifest, and travels with provenance. Size is bounded: beyond the top 5 named candidates per slot, eliminations compress to per-filter counts. The Layout Engine ignores the block — an additive optional field, hence a minor ComponentManifest schema bump, which touches AES-WEB-001 §4.1's artifact description and is recorded as a required amendment in §34.3.

Result: for any certified build, forever, Atlas can answer "why this component, this variant, on this page" from the manifest alone.

15. Component Registry Architecture
15.1 Registry as a governed system
The registry is declarative frozen data plus pure index functions in engines/website_generation/components/ (§29 file layout). It is loaded at import time, validated at import time, and never mutated at runtime. No dynamic filesystem scanning. No plugin magic. No nondeterministic registration. (Restates AES-WEB-001 §3.5's gate-registration doctrine as component law.)

15.2 Structure and mechanics
Registration mechanism: every ComponentDefinition lives in a family module under components/catalog/ and is listed in an explicit, ordered REGISTERED_COMPONENTS tuple in components/registry.py. Order in the tuple is lexicographic by component_id — enforced by test, so merge conflicts are visible and ordering is deterministic.
Import/build-time validation: the registry-integrity test suite asserts: unique IDs; naming grammar; complexity budget (§7.3); schema compatibility of every ComponentDefinition against the registry schema version; every DEPRECATED entry has replacement_component_id; every monetization-family entry has a monetization_contract; every interactive contract declares its accessibility state machine; every entry's example_fixture_ids resolve; every entry's emitter key resolves in the renderer's emitter table; token dependencies resolve against the token schema.
Indexes (pure, precomputed): by family; by page role; by capability; by lifecycle state; by compatibility range; variant lookup (component_id, variant); deprecation lookup; replacement lookup.
Registry identity: registry_version (semver, in contracts/versions.py ENGINE/SCHEMA registries) and registry_hash = SHA-256 of the canonical serialization of all definitions in registered order. Both are recorded in every ComponentManifest and BuildManifest — the replay anchor for selection.
Registry manifest: a derived, serializable catalog listing (id, version, lifecycle, family, hash) — emitted for operator tooling and pinned by a snapshot test.
Extension process: adding a component is a governed delivery (registry entry + emitter + fixtures + tests + gates per §2.2), shipped under zero-touch rules as a new catalog module plus one-line tuple additions in explicitly authorized files.
15.3 Conceptual public interface (language-neutral pseudocode — not production code)
interface ComponentRegistryView:
    get(component_id, version_req=None) -> ComponentDefinition        # raises UnknownComponentError
    resolve_variant(component_id, variant) -> VariantSpec
    candidates_for(page_role, slot_need) -> ordered list[ComponentDefinition]
    by_family(family) -> ordered list
    lifecycle(component_id) -> LifecycleStatus
    replacement_for(component_id) -> component_id | None
    registry_version() -> semver
    registry_hash() -> sha256
The Component Engine depends only on ComponentRegistryView (declared in contracts/interfaces.py); the concrete registry implements it. Tests may exercise the view with reduced fixture registries.

16. Conversion Architecture
16.1 ConversionContract (normative fields)
Every conversion-bearing component declares: conversion_goal (enum §16.2); primary_action (action class + target type); secondary_action (optional, visually subordinate); persuasion_role (initiate|reinforce|close); evidence_requirements (trust content that MUST be bindable nearby — §16.4); urgency_policy (none|spec-backed-offer-only — nothing else exists, per E1); disclosure_requirements (kinds from §17 when monetized); placement_constraints (allowed regions, e.g. sticky-mobile only in STICKY_MOBILE); repetition_limits (per-page, per-region); mobile_behavior (sticky eligibility, order priority); analytics_event (from §18 event registry); success_state / failure_state (bound status components for form goals); accessibility_requirements (inherits §12; forms per §12.3); trust_requirements (adjacency rule reference).

16.2 Conversion goals (closed enum)
PHONE_CALL, EMAIL, QUOTE_REQUEST, BOOKING (P3), LISTING_CLAIM, LISTING_SUBMISSION, NEWSLETTER_SIGNUP, SPONSORSHIP_INQUIRY, PAID_UPGRADE, AFFILIATE_CLICK (P3), PURCHASE (P3 handoff), COMPARE, SAVE (P3), SHARE (P3), CORRECTION_REQUEST, PROFILE_COMPLETION. Each goal maps in constants/components.py to: permitted CTA label classes (E9 enforcement table), permitted action target types (tel:, mailto:, route, external URL + rel policy), and its analytics event name.

16.3 CTA hierarchy and repetition (constants; gate CG-CMP-007)
Exactly one primary CTA style instance per region; the page's primary conversion_goal (recipe-declared) may repeat at most 3 times per page (hero/inline/sticky-or-footer); secondary goals render only in secondary/ghost visual weight; two different goals MUST NOT both render primary weight within one region. cta.sticky.mobile binds only the page's primary goal.

16.4 Trust adjacency and disclosure placement
Any COLLECT_LEAD-class component (quote/lead/claim/sponsor forms) SHOULD have a trust component in the same or adjacent region (CG-COM-009, WARNING in MVP; candidate for BLOCKING post-launch data). Monetization disclosures MUST render before or at the monetized element, never after the fold of it. Phone links render as real tel: anchors with the visible number (no "click to reveal" — friction theater is prohibited).

16.5 Form friction budgets (constants; gate CG-COM-010 WARNING)
Quote/lead ≤ 6 fields; newsletter ≤ 2; claim step one ≤ 5; correction ≤ 5; sponsor inquiry ≤ 6. Required-field count ≤ 4 on any MVP form. Every form: error summary + inline errors + preserved input + explicit success state. Multi-step intake is P3.

16.6 Conversion conflict resolution
When a page hosts multiple goals, the recipe's primary_goal wins primary visual weight and sticky placement; remaining goals are ranked by the recipe's declared order; the Component Engine resolves conflicts deterministically from that order — never by heuristics. A page whose bound instances violate the resolved hierarchy fails CG-COM-011 (BLOCKING).

17. Monetization and Sponsorship Architecture
17.1 Doctrine
Revenue components are first-class and honest. Every monetized surface satisfies four disclosures: visible (human-readable label from the constants-registered disclosure text set), semantic (distinct surface token + data-listing-kind/data-monetized attributes), machine-readable (rel="sponsored" on paid outbound links; JSON-LD never claims paid placement as editorial), and analytic (paid interactions carry separated event identifiers — §18).

17.2 Monetization surface rules
Surface	Rules
Sponsored listings	Interleaved cap per page (constants, default 3); listing.card.sponsored only; never in best-of ranked lists
Featured listings	Dedicated labeled zone only; never interleaved into organic order
Paid upgrades / premium profiles	Extend profile with premium sections; core facts (name, address, phone, hours) never paywalled
Affiliate links (P3)	rel="sponsored nofollow", disclosure block on page, comparison tables mark affiliate rows
Lead-generation forms	Disclose lead handling ("your request is sent to providers…") via mandatory disclosure slot
Sponsor blocks / partner offers	monetization.* family only; native-ad block (P3) requires "Advertisement" label — no exceptions
Membership/sponsorship pricing	commerce.pricing.sponsorship with PriceSpec + disclaimer rules (E4)
Claim upsells	Upgrade prompts appear only after claim flow context; never disguised as verification requirements (E10 adjacency)
17.3 Monetization state ownership
BusinessSpec declares the site's monetization configuration (which programs are on). ContentPackage carries per-listing listing_kind and disclosure blocks. ComponentManifest binds monetized components + disclosure slots. SEOPackage receives link-attribute policy compiled from LinkSpecs. Analytics hooks separate paid identifiers (§18). Quality gates CG-COM-001/002 + CG-SEO-002 enforce end-to-end. No component invents monetization state; it renders what content declares.

18. Analytics and Experimentation Hooks
AES-WEB-001 defers analytics implementation to the deployment layer (Part 2 deliberate exclusions). This section defines the component-level contract only — declared identifiers emitted as inert data- attributes, consumable by future deployment-layer instrumentation. No analytics SDK, script, or network call exists anywhere in the Component Engine or Renderer core.

18.1 AnalyticsContract
Each component declares: impression_id (stable slug = component_id with dots → dashes), interaction_events (subset of the event registry it can emit), and per-instance analytics_label prop (grammar-constrained slug) for disambiguation. Emitters render data-atlas-c (component id), data-atlas-v (component version), data-atlas-var (variant), data-atlas-e (event name on interactive elements), data-atlas-l (label), data-atlas-k (listing kind where applicable — the paid/organic separator). Attribute order stable; values deterministic.

18.2 Event registry (constants/analytics.py — names only in MVP)
component_impression, component_interaction, cta_click, form_start, form_complete, form_fail, phone_click, outbound_click, listing_click, sponsored_listing_click, filter_use, search_submit, zero_results_view, pagination_click, map_interaction (P3), save/share (P3), review_expand, claim_start, sponsor_inquiry_start, submission_start, correction_start. Payload field names are registered now (event, component id/version/variant, label, listing kind, page role, registry version, build id) so future instrumentation binds without markup changes.

18.3 Privacy and experimentation constraints
No personally identifying data appears in any declared identifier or payload field — identifiers describe the interface, never the visitor. Experiment/variant/exposure identifiers (data-atlas-x, experiment id + arm) are contract-reserved but UNUSED in MVP (experimentation engine is a future authority document). Performance-outcome linkage happens downstream by joining events to BuildManifest via build id + registry version — both already emitted.

19. Security and Content Safety
19.1 Threat table and owner map
Threat	Primary owner	Component-system obligation
HTML/script injection	Content Engine (escape) + Renderer (re-escape at boundary — AES-WEB-001 §5.7 defense in depth)	No prop/slot type can carry raw markup (§8.1); RichText is a constrained node tree
CSS injection	Token system	No CSS-bearing props exist; classes are emitter-generated
Unvalidated JavaScript	Renderer	Only versioned, hashed, registry-declared enhancement snippets (§24); zero inline scripts (CG-RND-005)
Malicious/unsafe URLs, open redirects	Content validators	LinkSpec scheme whitelist (https, http, tel:, mailto:); no javascript:/data: URLs; redirects don't exist (static links only)
data-URI abuse	Asset pipeline	Assets by CAS hash only; artifacts never embed binary (AES-WEB-001 §4.3)
Malicious SVG	Asset validation (Content Engine ring)	Icon/inline SVG assets sanitized at candidate validation; emitters treat SVG refs as opaque assets
Unsafe iframes/embeds	Registry	No embed component exists in MVP; future embeds get a provider whitelist contract (deferred)
Malformed structured data	SEO Engine + gate CG-SEO-005	Components emit fragments as data, never JSON-LD strings
Untrusted rich text / malicious listing content	Content Engine	Components consume only post-airlock ContentPackage; malicious-content fixtures (§30) prove emitter neutrality
Tracking-pixel injection	Import audit + CG-RND-007 (external request scan)	Bundle-level scan: zero third-party requests in MVP
Form spam	Form architecture	Honeypot + time-trap fields standard in form.*; endpoint is spec-declared
Deceptive outbound links	LinkSpec + CG-SEO-002	Visible host must not contradict target host for outbound links (gate check)
Exposed private data / internal metadata	Assembly + integrity gates	Manifests published are the bundle manifest only; selection traces stay in artifacts, never in the bundle (CG-RND-008 scans for internal markers)
19.2 Boundary restatement
Components are the last place security is improvised and the first place it is contractual: everything reaching an emitter is already validated, typed, escaped, and hashed. The emitter's job is to be incapable of un-escaping it.

20. Rendering Integration
20.1 Emitter architecture
For every (component_id, major_version) the renderer's emitter table (explicit registered dict in rendering/html_emitter.py internals) maps to one pure emission function: (instance, resolved_content, tokens, layout_ctx) -> HtmlFragment. Emitters: escape at the boundary (always, even though content arrives pre-escaped); emit stable attribute order (alphabetical) and stable token-derived classes with the component's registered class prefix (ac- + family, e.g. ac-listing-card); emit the §18 data attributes; never read anything not passed in. The registry-integrity test asserts a 1:1 mapping between ACTIVE definitions and emitter-table entries.

20.2 CSS emission
Component styles compile once per build from token references declared per component (CSS emitter owns media queries per §11.2). Class name generation is deterministic (never hashed-random — AES-WEB-001 §5.7). Unused-component styles are excluded by emitting only for components present in the build's manifests (deterministic tree-shaking by manifest, not by scanning).

20.3 Progressive-enhancement seam
Interactive contracts render functional-without-JS baselines (CSS-only drawer via checked pattern or <details>, scroll-snap gallery, real links for filters). Enhancement snippets are versioned hashed assets (§24) attached per component contract — the bundle works with all of them deleted, and gate CG-RND-006 verifies the no-JS baseline paths exist.

21. Component Quality Gates
Component gates extend the AES-WEB-001 gate architecture: registered in constants/gates.py, executed by the Quality Gate Engine in declared order, typed results, and every gate ships a known-good and known-bad fixture or cannot register (AES-WEB-001 §10.4). New check modules (§29) join gates/checks/. Severities: B = BLOCKING, W = WARNING, I = INFO. Remediation owner (RO): R registry/definition, CE Component Engine binding, CT content, RN renderer/emitter, RC recipe/LayoutPlan.

Columns: gate_id | pass condition (inputs implied: ComponentManifest + registry + rendered output + upstream artifacts per family) | Sev | RO. Failure diagnostics for every gate MUST name the page route, instance path, component id/version, and the specific violating value. Fixture pair IDs follow fx-<gate_id>-good|bad.

21.1 Contract gates (CG-CON, module component_checks.py)
gate_id	Pass condition	Sev	RO
CG-CON-001	Every instance's component_id exists in registry	B	CE
CG-CON-002	Instance version within registry's supported versions	B	CE
CG-CON-003	All required props bound; types valid	B	CE
CG-CON-004	No unknown props	B	CE
CG-CON-005	All required content slots bound; cardinality respected	B	CE/CT
CG-CON-006	Variant exists in supported_variants	B	CE
CG-CON-007	No DEPRECATED component without recorded build allowance; no RETIRED/BLOCKED ever; no x. in certifiable builds	B	CE
CG-CON-008	compatibility_range satisfied vs renderer/token/registry versions	B	R
CG-CON-009	Every ASSET_REF resolves in CAS with correct AssetRole	B	CT
CG-CON-010	Every ROUTE_REF exists in SiteArchitecture	B	CE
21.2 Composition gates (CG-CMP, module composition_checks.py)
gate_id	Pass condition	Sev	RO
CG-CMP-001	Every instance's parent region ∈ allowed_parent_regions	B	RC
CG-CMP-002	All children ∈ allowed_child_components, none in forbidden set	B	RC
CG-CMP-003	Composition depth ≤ 6	B	RC
CG-CMP-004	No recursive composition (family within own subtree, layout.*/atom.* exempt)	B	RC
CG-CMP-005	Heading hierarchy: exactly one H1, no level skips, ownership per §9.3	B	RN/RC
CG-CMP-006	Landmark hierarchy: one main/header/footer; multi-nav labeled	B	RN
CG-CMP-007	CTA hierarchy + repetition within §16.3 policy	B	RC
CG-CMP-008	No nested interactive controls	B	RN
CG-CMP-009	≤ 2 concurrent sticky regions; no sticky overlap	B	RC
CG-CMP-010	Required role components present per §6.1 matrix (extends AES-WEB-001 structural family; registered alongside CG-STR-006 zero-state rule)	B	RC
CG-CMP-011	Section count ≤ role ceiling	W	RC
21.3 Rendering gates (CG-RND, extends structural_checks.py/new rendering_checks.py)
gate_id	Pass condition	Sev	RO
CG-RND-001	Deterministic output: double-render hash equality per page	B	RN
CG-RND-002	Valid HTML (deterministic conformance checker over emitted set)	B	RN
CG-RND-003	All interpolated content escaped (marker-probe fixtures)	B	RN
CG-RND-004	Stable attribute order + stable class names across builds	B	RN
CG-RND-005	Zero inline scripts; zero unapproved inline styles	B	RN
CG-RND-006	No-JS baseline paths present for every interactive contract	B	RN
CG-RND-007	Zero external requests in bundle (MVP); asset refs resolve	B	RN
CG-RND-008	No duplicate DOM ids; no internal-metadata markers in output	B	RN
CG-RND-009	No unsafe URLs (scheme whitelist) anywhere in emitted markup	B	RN/CT
CG-RND-010	Structured-data fragments well-formed pre-compilation	B	CE
21.4 Accessibility gates (CG-A11Y, module accessibility_checks.py extensions)
Per approved decision, all defects affecting keyboard access, focus management, semantic structure, form completion, or core interaction are BLOCKING.

gate_id	Pass condition	Sev	RO
CG-A11Y-001	Labels: every control programmatically labeled; icon-only controls have A11Y_LABEL	B	CE/RN
CG-A11Y-002	Declared keyboard behavior present (state-machine markup assertions §12.6)	B	RN
CG-A11Y-003	Focus: visible ring token wired; no outline:none without replacement; trap contracts valid	B	RN
CG-A11Y-004	Contrast: every declared text/surface pairing meets AA (Brand-embedded ratios)	B	R/RN
CG-A11Y-005	Touch targets ≥ 44px via tokens	B	RN
CG-A11Y-006	Reduced-motion resolution exists for all motion tokens used	B	RN
CG-A11Y-007	Semantic roles correct per semantic_element + state machines	B	RN
CG-A11Y-008	Live-region declarations valid where contracted	B	RN
CG-A11Y-009	Dialog/drawer behavior markup valid (trap, escape, labeling)	B	RN
CG-A11Y-010	Informative images have non-empty alt; decorative are alt=""	B	CT
CG-A11Y-011	Skip link first-focusable on every page	B	RC
CG-A11Y-012	Form error summary + inline association + autocomplete attrs	B (summary/association) / W (autocomplete)	RN
CG-A11Y-013	Alt length ≤ ceiling; non-redundant link text	W	CT
21.5 SEO gates (CG-SEO, extends seo_checks.py)
gate_id	Pass condition	Sev	RO
CG-SEO-001	Heading rules (crawl view = §9.3 result; no hidden headings)	B	RN
CG-SEO-002	Paid outbound links carry rel="sponsored"; UGC outbound nofollow ugc	B	RN/CT
CG-SEO-003	All internal links crawlable <a href> resolving to SiteArchitecture routes	B	RN
CG-SEO-004	Internal-linking floors/ceilings per role (§6.2)	B (floors) / W (ceilings)	RC
CG-SEO-005	Compiled structured data schema-valid; no conflicting duplicate entities	B	CE (fragments)
CG-SEO-006	User-visible content = crawler-visible content	B	RN
CG-SEO-007	Duplicate content-block reuse ≤ page ceiling	W	CT
CG-SEO-008	Visible NAP ↔ LocalBusiness markup parity	B	CT
CG-SEO-009	Pagination markup crawl-safe; breadcrumb rules per role	B	RC
21.6 Commercial gates (CG-COM, module commercial_checks.py)
gate_id	Pass condition	Sev	RO
CG-COM-001	Every SPONSORED/FEATURED render carries visible + semantic disclosure (E5)	B	RN/CE
CG-COM-002	Ranked lists bind rationale/methodology; sponsored never presented as rank (E6)	B	CT/RC
CG-COM-003	Every review/testimonial block carries evidence_ref (E2)	B	CT
CG-COM-004	Verification badges render only on VERIFIED content state (E10)	B	CE
CG-COM-005	Urgency claims reference spec-backed offer with expiry (E1)	B	CT
CG-COM-006	Non-exact PriceSpec renders bound disclaimer (E4)	B	CE
CG-COM-007	Consent controls equal-weight; no pre-checked marketing consent (E8)	B	RN
CG-COM-008	CTA label class matches conversion goal (E9 table)	B	CE
CG-COM-009	Trust component adjacent to lead forms	W	RC
CG-COM-010	Form friction budgets (§16.5)	W	R/RC
CG-COM-011	Page conversion hierarchy matches recipe resolution (§16.6)	B	RC
CG-COM-012	Monetization blocks appear only on roles permitted by §6.1; per-page sponsored caps	B	RC
21.7 Responsive gates (CG-RSP, module responsive_checks.py)
gate_id	Pass condition	Sev	RO
CG-RSP-001	Every instance has a valid resolved ResponsiveContract	B	R/CE
CG-RSP-002	No prohibited horizontal overflow (deterministic CSS analysis: fixed widths > container at 320)	B	RN
CG-RSP-003	Mobile order defined; visual-vs-DOM reorder within §11.3 rule	B	RC
CG-RSP-004	Tables declare adaptation; no data loss mode	B	R
CG-RSP-005	Image behavior: aspect token + srcset policy present	B	RN
CG-RSP-006	Sticky behavior bounded (offsets, z-tokens, footer clearance)	B	RN
CG-RSP-007	Reflow-safe at 200% zoom (CSS analysis of absolute units)	B	RN
CG-RSP-008	Touch-target verification at sm breakpoint	B	RN
Gate count: 63 component gates + inherited AES-WEB-001 families. Any BLOCKING failure → GATE_REJECTED per AES-WEB-001 §10.3; commercial/content failures route to targeted rework; contract/composition failures are deterministic-stage failures (terminal, fix-and-rebuild).

22. Versioning, Compatibility, and Deprecation
22.1 Independent version axes (all registered in contracts/versions.py)
component-contract schema (the ComponentDefinition shape); each component definition; each family (informational roll-up); registry version; renderer compatibility; design-token schema; analytics contract; accessibility contract; SEO contract; responsive contract. Every BuildManifest records all axes in play (extends AES-WEB-001 §4.6's two-axis recording with component axes — additive).

22.2 Change classification (normative)
Change	Class
Additive optional prop (with default), new variant, new fixture	Minor (component) + minor (registry)
Markup change altering emitted bytes	Minor at minimum + snapshot update + engine-version bump in same delivery (AES-WEB-001 §11.4)
Accessibility fix changing markup	Minor (it changes bytes) even though behaviorally "patch" in spirit — bytes rule wins
Diagnostics/description text only (no serialized contract or bytes)	Patch
Semantic change to existing prop meaning; renamed/removed prop; default change; required-slot change	Major (new definition version; old version remains registered for replay)
Design-token schema change	Major on token axis; components re-pin compatibility ranges
SEO/analytics/conversion-policy contract change altering output or attributes	Minor if additive, major if altering existing emissions
Behavior change to interaction state machine	Major
22.3 Replay and certification guarantees (binding)
Existing certified builds MUST remain reproducible forever: old definition versions are never edited in place (prohibited change class — enforced by a definitions-hash pinning test per released version); registry snapshots per registry version are retained fixtures; old-renderer emitter functions for released major versions are retained until the version is RETIRED with a recorded end-of-life and no live certified bundle depends on it; frozen fixtures for released versions are never modified, only superseded. Migration policy: a major definition bump ships a documented migration note (prop/slot mapping) and a replacement_component_id where the component itself is replaced; the Component Engine never auto-migrates a manifest — migration produces a new build.

22.4 Deprecation and end-of-life
DEPRECATED at registry-minor with warning diagnostics in selection traces; selection excludes deprecated by default (§14.2 step 3); sunset ≥ 2 registry minor versions; RETIRED only when portfolio scan shows no certified production bundle references it; replacement mapping mandatory from deprecation moment; deprecated fixtures preserved permanently (replay).

23. Component Lifecycle
States (closed enum): PROPOSED → EXPERIMENTAL (x.) → ACTIVE → PREFERRED; exits: DEPRECATED → RETIRED; emergency: BLOCKED (selection-excluded immediately; reachable from any state; reserved for discovered security/legal defects; requires incident note in registry entry).

Promotion to ACTIVE requires all of: contract complete (every §3 field populated); emitter complete; full fixture set (§30) complete; responsive contract verified at §11.4 matrix; accessibility state machine verified; SEO contract verified; deterministic snapshot pinned; commercial purpose documented; all §21 gates registered for it passing on fixtures; full regression suite green; security review (malicious-content fixtures where relevant) passing; DOM/performance budget (§25) passing.

Promotion to PREFERRED additionally requires: shipped in ≥ 1 certified production build; no WARNING-tier defects open against it; Chief Architect designation (PREFERRED is the "reach for this first" signal that drives +100 selection score, so it is a curation act, not an automatic one).

Approval authority: PROPOSED→EXPERIMENTAL: any implementation session may register x. components under experimental rules. EXPERIMENTAL→ACTIVE and ACTIVE→PREFERRED: Chief Architect (operator) approval recorded in the registry entry (approved_by, approved_at as data — supplied at authoring time, not clock-read). ACTIVE→DEPRECATED: Chief Architect. DEPRECATED→RETIRED: automated eligibility check (no live references) + Chief Architect confirmation. →BLOCKED: Chief Architect, immediately, with incident note.

24. JavaScript and Progressive-Enhancement Policy
Static-first is law (AES-WEB-001 §8.5). MVP client-side interaction budget: 0 KB required JS; ≤ 30 KB total (pre-compression) deferred enhancement JS per page, composed only of versioned hashed snippets registered per component contract (mobile drawer focus trap, form UX enhancement, gallery affordances). Snippets: no dependencies, no globals beyond one namespaced object, no network calls, no storage, executed deferred, and the page MUST pass every gate with all snippets removed (CG-RND-006). Third-party scripts: zero in MVP (CG-RND-007); the future analytics attachment point is the deployment layer, outside the certified bundle's gate scope but inside deployment verification scope (deferred to the analytics authority document).

25. Performance Architecture
Principles: static rendering; single shared CSS file per build (token-compiled, manifest-tree-shaken §20.2); minimal JS per §24; progressive enhancement; responsive images from CAS renditions with explicit width/height (CLS-safe); lazy loading below the fold (loading="lazy" policy owned by emitters, first hero/LCP image eager); self-hosted fonts (≤ 2 families, ≤ 4 faces, font-display: swap); hashed immutable asset URLs (AES-WEB-001 §8.4); above-the-fold priority ordering in recipes; DOM discipline.

Thresholds (all in constants/components.py / constants/build.py; budget-assertion tests per AES-WEB-001 §11.7):

Threshold	Default
Max DOM nodes per component instance	150 (listing cards 60; shell exempt)
Max component instances per page	40 (profile 45; lead-gen 20)
Max nesting depth	6
Max initial (blocking) JS	0 KB
Max deferred JS per page	30 KB
Max images per page	40 (gallery pages 60)
Max gallery (scroll-snap) items	10
Max font families / faces	2 / 4
Max external requests	0 (MVP)
Map loading	Static map image + text directions in MVP; interactive maps P3, click-to-load only
Max page DOM nodes (bundle gate)	2,500
Third-party scripts	0
Every numeric lives in constants; scattering a threshold into an implementation file is a review-rejectable defect.

26. Default Commercial Composition Recipes
Recipes are declarative default sequences per PageRole, stored as data in constants/components.py (recipe tables) and consumed by the Component Engine (slot needs) and Layout Engine (default order). Recipes declare: required regions, component sequence (slot purposes, not hard component pins — selection fills them), variant guidance, primary_goal, monetization slots, SEO role, internal-linking obligations (§6.2), structured-data role, mobile adjustments, accessibility notes, anti-patterns, and fallback behavior. They are defaults with declared flexible zones, not rigid templates — LayoutPlan may reorder within flexible zones only.

Common frame for all recipes (implicit, not repeated): skip link → header → breadcrumb (where required) → [recipe body] → footer. Fallback behavior for all: any optional slot with no eligible component is dropped and traced; any required slot failure is ComponentResolutionError (§14.2.9).

26.1 Directory homepage (home)
Sequence: disclosure/utility bar (O) → hero.search.directory → category discovery grid → location discovery grid → featured listings zone (O, disclosed) → value/trust strip → editorial resources (O) → claim-your-listing CTA band → newsletter capture (O) → footer. Primary goal: search-mediated discovery (no form goal); secondary: LISTING_CLAIM, NEWSLETTER_SIGNUP. Monetization: 1 featured zone max. SEO: WebSite+Organization; links to all top categories/cities. Mobile: search hero first paint; category grid 2-col. Anti-patterns: hero carousel; >2 CTA bands; featured zone before category discovery. Flexible zone: order of trust strip / editorial / location grid.

26.2 Category page (category)
Compact category hero (intro slot) → filter links + sort + results summary → listing cards (paginated) → related categories → top cities in category → claim CTA band. Goal: listing click; monetization ≤ 3 sponsored interleaved; SEO: ItemList+Breadcrumb, linking floors §6.2; mobile: filters → drawer; anti-pattern: editorial essay above listings (intro ≤ 2 short paragraphs above, long-form below listings); zero-results state mandatory with recovery links.

26.3 City page (city)
Local hero → categories-in-city navigator → listing cards → local facts (O) → nearby cities → parent region link. Goal: category/listing click; SEO: city-hub internal-link role; mobile: navigator as chip row; anti-pattern: thin duplicated city intro (CG-SEO-007 tripwire).

26.4 City-category page (city-category)
Compact local hero → filter links/results summary → listing cards → quote CTA band → nearby city-category links → parent city + parent category links. Goal: QUOTE_REQUEST or PHONE_CALL per spec; monetization ≤ 3 sponsored; SEO: the programmatic-page workhorse — linking floors strictly gated; anti-pattern: rendering when inventory = 0 without the sparse-state recipe variant (state component + nearby alternatives).

26.5 Search-results page (search-results)
Results header (query echo + count) → filters/sort → compact rows or cards → pagination → related searches (O). No hero, no trust, minimal chrome. Goal: listing click; sponsored ≤ 2, disclosed; SEO: typically noindex per SEO Engine policy (components stay crawl-safe regardless); zero-results mandatory.

26.6 Business-profile page (business-profile)
Profile header (name, rating summary, kind badges) → contact panel (sidebar ≥ lg / inline + sticky CTA < md) → description → services → hours → service areas → gallery (O) → credentials (O) → reviews (summary + list) → FAQs (O) → map + directions → related listings → claim CTA (if unclaimed) → correction link. Goal: PHONE_CALL (default; spec may set QUOTE_REQUEST). Monetization: premium sections extend after core facts. SEO: LocalBusiness + Breadcrumb (+AggregateRating when genuine). Mobile: sticky call CTA; hours table native. Anti-patterns: contact behind interaction; premium interleaved before core facts; reviews without evidence refs. States: unavailable/closed/pending variants replace the CTA cluster.

26.7 Comparison page (comparison)
Comparison hero → methodology block (E6) → comparison table (sticky first column ≥ md; stacked < md) → per-row CTA → page CTA band → related links. Goal: COMPARE→outbound/profile click; affiliate is P3 and forbidden until then.

26.8 Best-of editorial page (best-of)
Editorial hero → ranking methodology → ranked listing cards with per-rank rationale slots → related best-of links → category link band. Sponsored inside the ranked list: forbidden (CG-COM-012); a clearly separated, labeled featured block MAY follow the list. SEO: Article/ItemList; the page type that most builds trust — treat methodology as required content, not boilerplate.

26.9 Sponsor-acquisition page (sponsor-page)
Offer hero → audience statistics (evidenced) → example placements (labeled specimens) → sponsorship pricing → sponsor inquiry form → paid-placement disclosure. Goal: SPONSORSHIP_INQUIRY. Anti-pattern: traffic claims without evidence_ref (CG-COM-003 applies to statistics blocks).

26.10 Listing-claim page (claim-listing)
Compact explainer hero → listing preview → verification explanation → claim form (≤ 5 fields step one) → upgrade preview (O, disclosed, after form). Goal: LISTING_CLAIM. Anti-pattern: upgrade offer positioned as claim requirement (E10 adjacency).

26.11 Lead-generation landing page (lead-gen-landing)
Condensed header (logo + exit) → offer hero → lead/quote form (≤ 6 fields) → trust adjacent to form → social-proof listings (O) → minimal footer. Goal: QUOTE_REQUEST, single-goal page; all other CTA goals forbidden. SEO: typically noindex (SEO Engine); accessibility: form-first tab order.

26.12 Listing-submission page (submission)
Compact hero → editorial standards link → submission form → paid fast-track option (O, disclosed, equal-weight free path) → success/error states. Goal: LISTING_SUBMISSION. Anti-pattern: hiding the free path (E8-adjacent, gate CG-COM-007 equal-weight rule applies).

26.13 Correction-request page (correction)
Minimal hero → listing summary → data-source disclosure → correction form → states. Goal: CORRECTION_REQUEST. No monetization of any kind (§6.1).

(editorial-guide, collection, service-area, verification, regional-hub recipes derive from §6.1 rows using the same frame; their full recipe tables are authored in AES-WEB-002G/H phase deliveries under this section's rules — recorded as a bounded deferral in §34.2.)

27. MVP Component Inventory
27.1 Sizing rationale
The recommendation is 72 components across seven waves. Reasoning: the §6.1 matrix requires roughly 45 distinct commercial components to satisfy every MVP page role without gaps; the composition substrate requires 15 primitives to make those deterministic and consistent; 4 status/legal components close the certification requirements. Below 50 total, page roles start sharing components past their contracts (the mega-component failure mode); above ~80, Atlas is building library instead of launching directories. 72 is the smallest count at which every §26 recipe — including its disclosure, status, and legal obligations — resolves with zero improvisation. Waves are dependency-ordered: each wave's components compose only from earlier waves.

Table columns: ID | roles (abbrev.: ALL, home, cat, city, cc=city-category, sr=search-results, prof=profile, lg=lead-gen, claim, spon=sponsor, sub=submission, corr=correction, cmp=comparison, bo=best-of) | required props (RP) / required slots (RS) — representative, full lists are registry data | variants | notes (A11y / SEO / Conversion / Monetization) | major gates.

27.2 Wave 1 — Foundation primitives (15)
ID	Roles	RP / RS	Variants	Notes	Major gates
layout.shell.page	ALL	RP: page_role / RS: —	—	Owns landmarks, H1 delegation, head/JSON-LD injection points	CG-CMP-005/006
layout.section.container	ALL	RP: width token, spacing token / RS: heading (O)	standard, band (full-bleed surface)	Owns H2 + section spacing	CG-CMP-005
layout.grid.standard	ALL	RP: columns enum(2,3,4), gap token	—	Collapse per §11; owns child spacing	CG-RSP-002
layout.stack.standard	ALL	RP: gap token	—	Vertical rhythm owner	—
layout.split.standard	ALL	RP: ratio enum, mobile_order	media-left, media-right	Stack < md	CG-RSP-003
layout.card.shell	ALL	RP: surface token, radius token	raised, flat	Pure surface; card-in-card exception holder	CG-CMP-004
atom.button.action	ALL	RP: weight enum(primary, secondary, ghost) / RS: label	—	44px targets; focus ring	CG-A11Y-003/005
atom.link.standard	ALL	RP: LinkSpec ref	inline, standalone	rel attrs from LinkSpec	CG-SEO-002/003
atom.image.responsive	ALL	RP: ASSET_REF, aspect token, loading	—	width/height, srcset; alt from content	CG-A11Y-010, CG-RSP-005
atom.icon.standard	ALL	RP: ASSET_REF(ICON), size token, A11Y_LABEL or decorative	—	aria-hidden when decorative	CG-A11Y-001
atom.badge.status	ALL	RP: kind enum / RS: label	—	Kind → surface token; never fakes states	CG-COM-004
atom.alert.notice	ALL	RP: severity enum / RS: body	—	role=status/alert by severity	CG-A11Y-008
atom.field.text	forms	RP: input kind enum, autocomplete, required / RS: label, instructions (O), error	—	Label association; described-by	CG-A11Y-001/012
atom.field.select	forms	RP: options ref, required / RS: label, error	—	Native select	CG-A11Y-001
atom.field.choice	forms	RP: mode enum(radio, checkbox), options ref / RS: legend, error	—	fieldset/legend; equal-weight consent	CG-COM-007
27.3 Wave 2 — Navigation and shell (8)
ID	Roles	RP / RS	Variants	Notes	Major gates
nav.skip.link	ALL	—	—	First focusable	CG-A11Y-011
nav.header.standard	ALL	RP: nav tree ref / RS: logo asset	standard, condensed (lg only)	One CTA slot max; drawer trigger < md	CG-CMP-006
nav.mobile.drawer	ALL	RP: nav tree ref	—	Focus trap SM §12.6; no-JS baseline	CG-A11Y-002/009, CG-RND-006
nav.breadcrumbs.standard	all except home, lg	RP: trail ref	—	BreadcrumbList capability	CG-SEO-009
nav.utility.bar	home, cat, city	RS: message, link (O)	announce, disclosure	Dismissal is P3 (state)	—
nav.pagination.standard	cat, city, cc, sr	RP: page ctx ref	—	aria-current; crawl-safe links	CG-SEO-009
legal.footer.directory	ALL	RP: nav tree ref / RS: legal facts, disclosures	standard, minimal (lg)	Link ceiling 40; mandatory disclosures visible	CG-CMP-006
status.banner.notification	ALL	RP: severity / RS: body, action (O)	—	Recovery action rule	CG-A11Y-008
27.4 Wave 3 — Directory discovery (9)
ID	Roles	RP / RS	Variants	Notes	Major gates
hero.search.directory	home	RS: h1, subhead, search embed	centered, split	H1 owner; LCP-eager media	CG-CMP-005
hero.local.standard	cat, city, cc, service-area	RP: context_role / RS: h1, intro	standard, compact	Programmatic intro slots (variation via content layer)	CG-SEO-007
directory.search.primary	home, cat, city, sr	RP: action route, scope enum / RS: labels	hero-embedded, standalone, condensed	Real GET form; labeled	CG-A11Y-001
directory.categories.grid	home, city	RP: source ref, columns / RS: tile content	tiles, chips	Link backbone	CG-SEO-003/004
directory.locations.grid	home, cat, regional-hub	RP: source ref	tiles, columns	Link backbone	CG-SEO-004
directory.filters.panel	cat, cc, sr	RP: facet set ref	sidebar, top-bar, drawer, chips	Link-based facets; indexable whitelist; drawer SM	CG-A11Y-002, CG-SEO-006
directory.sort.control	cat, cc, sr	RP: sort options ref	—	Link-based; self-canonical handling by SEO Engine	CG-SEO-003
directory.results.summary	cat, cc, sr	RS: summary text	—	Count announcement text	—
status.results.zero	cat, city, cc, sr	RS: message, recovery links (1..n)	—	Recovery mandatory	CG-STR-006
27.5 Wave 4 — Listings and profiles (12)
ID	Roles	RP / RS	Variants	Notes	Major gates
listing.card.standard	home, cat, city, cc, sr, prof, collection	RP: LISTING_REF, density / RS: via listing block	standard, minimal	Stretched-link; kind=ORGANIC only	CG-CMP-008, CG-COM-001
listing.card.featured	home, cat, city	RP: LISTING_REF / RS: disclosure	—	FEATURED zone only; label + surface token	CG-COM-001
listing.card.sponsored	cat, cc, sr	RP: LISTING_REF / RS: disclosure	—	Interleave cap; rel=sponsored outbound	CG-COM-001, CG-SEO-002
listing.row.compact	sr, cmp	RP: LISTING_REF	result, comparison	Table-adjacent semantics	CG-RSP-004
profile.header.business	prof	RP: LISTING_REF / RS: name(h1), rating summary (O), badges	claimed, unclaimed	H1 owner on profiles; INCOMPLETE state styling	CG-CMP-005, CG-COM-004
profile.contact.panel	prof	RS: ContactSpec, CTA cluster	sidebar, inline	tel:/mailto: real links; NAP source	CG-SEO-008
profile.hours.table	prof	RS: HoursSpec	—	Real table + scope; no clock reads	CG-A11Y-007
profile.areas.served	prof	RS: area links	list, map-adjacent	areaServed capability	CG-SEO-005
profile.map.directions	prof	RS: GeoSpec, address, directions text	static-image	Text directions primary; interactive P3	CG-A11Y-010
profile.credentials.list	prof	RS: CredentialBlock (1..n)	—	evidence_ref each	CG-COM-003
profile.gallery.standard	prof	RS: images (1..10)	scroll-snap	Only permitted "carousel"; per-image alt	CG-A11Y-010, CG-CMP (carousel cap)
content.description.business	prof	RS: RichTextBlock	—	H3-scoped internals	CG-CMP-005
27.6 Wave 5 — Trust, conversion, and forms (13)
ID	Roles	RP / RS	Variants	Notes	Major gates
trust.reviews.summary	prof, listing contexts	RS: RatingSummary	inline, block	Text equivalent; stars aria-hidden; AggregateRating capability (genuine only)	CG-COM-003, CG-SEO-005
trust.reviews.list	prof	RS: ReviewBlock (1..n)	comfortable, compact	evidence_ref each; expand SM if truncated	CG-COM-003
trust.statistics.strip	home, spon, lg	RS: stat blocks with evidence_ref	strip, grid	Not color-only	CG-COM-003
content.faq.standard	prof, cat, city, guides	RS: QA pairs (1..12)	accordion, open-list	FAQPage capability (visible only); accordion SM	CG-A11Y-002, CG-SEO-006
form.lead.quote	lg, prof, cc	RP: action route / RS: fields (≤6), disclosure, states	—	Friction budget; lead-handling disclosure	CG-COM-010, CG-A11Y-012
form.claim.standard	claim	RP: action route / RS: fields (≤5), states	—	Verification explanation adjacency	CG-COM-004/010
form.submission.listing	sub	RP: action route / RS: fields, standards link, states	—	Free path equal-weight	CG-COM-007
form.correction.standard	corr	RP: action route / RS: fields (≤5), states	—	Listing summary adjacency	CG-A11Y-012
form.capture.newsletter	home, guides	RP: action route / RS: label, consent	inline, band	≤2 fields; unchecked consent	CG-COM-007/010
cta.claim.listing	prof, home, cat	RP: target route / RS: label	band, inline	Goal LISTING_CLAIM; label table	CG-COM-008
cta.sticky.mobile	prof, lg, cc	RP: goal (page primary), target	—	<md only; single instance; footer clearance	CG-CMP-009, CG-RSP-006
cta.sponsor.inquiry	spon, footer contexts	RP: target route / RS: label	—	Goal SPONSORSHIP_INQUIRY	CG-COM-008
cta.submit.listing	home, cat, sub	RP: target route / RS: label	—	Goal LISTING_SUBMISSION	CG-COM-008
27.7 Wave 6 — Local SEO and editorial (7)
ID	Roles	RP / RS	Variants	Notes	Major gates
seo.local-links.cities	city, cc, home, regional-hub	RP: link set ref (≤24)	grid, inline-list	From SiteArchitecture topology only	CG-SEO-003/004
seo.local-links.categories	cat, cc, city	RP: link set ref (≤24)	grid, inline-list	Same	CG-SEO-004
content.intro.contextual	cat, city, cc	RP: context_role / RS: RichText intro	above-listings (short), below-listings (long)	The programmatic-variation surface; CG-SEO-007 watchdog	CG-SEO-007
content.section.editorial	guides, bo, prof	RS: RichTextBlock	standard, callout	H2/H3 discipline	CG-CMP-005
content.toc.standard	guides, bo	RP: derived heading refs	sidebar, top	Jump-select < md	CG-RSP-003
content.table.comparison	cmp, bo, guides	RS: typed table	—	Header rows; scroll-x/stacked	CG-RSP-004
content.resources.grid	home, guides	RS: resource cards (≤12)	—	Internal-link support	CG-SEO-003
27.8 Wave 7 — Monetization, legal, and status (0 + 8 = 8)
ID	Roles	RP / RS	Variants	Notes	Major gates
monetization.disclosure.advertising	any page hosting paid units	RS: DisclosureBlock	page-level, inline	Registered disclosure text set	CG-COM-001
monetization.ribbon.sponsor	listing/zone contexts	RS: label	—	The visible paid marker; surface token	CG-COM-001
monetization.section.premium-profile	prof	RS: premium blocks	—	After core facts only	CG-COM-012
commerce.pricing.sponsorship	spon	RS: PriceSpec set, disclaimer	cards, table	E4 disclaimers	CG-COM-006
status.listing.unavailable	prof	RP: reason enum(unavailable, closed, stale, archived) / RS: message, recovery links	—	Replaces CTA cluster	CG-STR-006
status.listing.pending	prof, claim	RS: message, expectation text	—	Never fakes VERIFIED	CG-COM-004
legal.statement.standard	dedicated legal pages, footer links	RP: kind enum(privacy, terms, accessibility, editorial-standards, advertising, data-source) / RS: RichText	—	Kind-specific required sections validated by content rules	—
monetization.prompt.upgrade	claim, prof (owner contexts P3)	RS: offer, disclosure	—	Never positioned as requirement	CG-COM-004
Total: 15 + 8 + 9 + 12 + 13 + 7 + 8 = 72 registered definitions — the recommended MVP count is 72. The §6.1 role matrix derives a hard floor of 64 (recipes cannot all resolve below it); the remaining 8 — the wave-7 disclosure, status, and legal components — are not optional polish but certification prerequisites (CG-COM-001, CG-STR-006, and the legal-role recipes fail without them), so they belong inside MVP rather than after it. 72 sits comfortably inside the 40–80 realistic band: below it, page roles start sharing components past their contracts (the mega-component failure mode); above ~80, Atlas is building a library instead of launching directories. First-directory certification requires all seven waves ACTIVE.

28. Long-Term Component Library
28.1 Expansion doctrine
Growth from 72 to a mature 200–500-definition ecosystem is organized by capability, never by count. A capability enters the library only when: (a) ≥ 2 portfolio directories need it, or one directory's revenue depends on it; (b) its contracts fit §3 without new artifact kinds, or the required upstream amendment is authored first; (c) it survives the §7.2 governance table (many "components" are actually variants, content patterns, or not components at all).

28.2 Capability roadmap (unordered backlog; sequencing is a business decision made against verified revenue data)
Capability	Component implications	Precondition
Advanced comparison	Weighted matrices, spec filters	Comparison-page traffic evidence
Interactive maps	Click-to-load map region, marker components	JS-budget amendment; provider adapter at deployment edge
Saved searches / favorites / alerts	Stateful controls	Dynamic-bundle seam (AES-WEB-001 §8.6) — a major undertaking, not a component patch
Advanced review systems	Submission, moderation states, owner responses	UGC pipeline + moderation authority document
Scheduling / availability / booking integrations	Booking CTA handoff → embedded flows	Partner adapter contracts; verified-transaction doctrine
Ecommerce / membership / lead routing	Checkout handoff, plan selectors, routed lead forms	Payment adapter at deployment edge; never in core
Personalization / localization / multilingual	Locale-variant content slots; hreflang in SEO Engine	Content system authority (AES-WEB-003)
Calculators / quizzes / recommendation flows	Budgeted interactive widgets	Per-widget JS budget review
Data visualizations / editorial scoring	Static-rendered chart components	Deterministic chart emitter design
Community contributions / user photos	UGC display components	Moderation + legal review
Owner dashboards / admin interfaces	Not components — application modules outside the WGE	Separate authority document
28.3 Classification discipline (binding)
Thing	Is it a component?
Reusable rendering unit with a §3 contract	Yes
Site-specific feature used by exactly one directory	No — content pattern or rejected; the site. namespace stays empty
Application module (dashboards, auth, moderation)	No — lives outside engines/website_generation/
Embedded external service (booking widget, payment)	No — adapter at the deployment edge + a thin handoff component at most
Admin interface	No
Deployment integration	No — DeploymentAdapter territory
29. Package and File Architecture
29.1 Normative tree (extends AES-WEB-001 Part 2; additive — recorded as amendment §34.3-A3)
engines/website_generation/
├── components/
│   ├── __init__.py                  # Public: ComponentEngine, registry view accessor
│   ├── component_engine.py          # Selection + binding (AES-WEB-001 §5.5) — unchanged role
│   ├── registry.py                  # REGISTERED_COMPONENTS tuple, RegistryView impl, indexes, registry_hash
│   ├── catalog/                     # ComponentDefinition data, one module per family
│   │   ├── __init__.py
│   │   ├── layout_atoms.py          # layout.* + atom.* (Wave 1)
│   │   ├── navigation.py            # nav.* + legal.footer.* (Wave 2)
│   │   ├── discovery.py             # hero.* + directory.* (Wave 3)
│   │   ├── listings_profiles.py     # listing.* + profile.* + content.description (Wave 4)
│   │   ├── trust_conversion.py      # trust.* + cta.* + form.* (Wave 5)
│   │   ├── seo_editorial.py         # seo.* + content.* (Wave 6)
│   │   └── monetization_status.py   # monetization.* + commerce.* + status.* + legal.statement (Wave 7)
│   ├── selection/
│   │   ├── __init__.py
│   │   ├── selector.py              # §14 pipeline (pure)
│   │   └── trace.py                 # selection_trace assembly + compression
│   ├── validation/
│   │   ├── __init__.py
│   │   └── binding_validators.py    # Bind-time semantic rules (§21.1 sources)
│   └── compatibility/
│       ├── __init__.py
│       └── ranges.py                # Compatibility-range evaluation (pure semver logic)
├── rendering/                       # (existing) html_emitter grows per-family emitter modules internally
├── gates/checks/                    # + component_checks.py, composition_checks.py,
│                                    #   rendering_checks.py, commercial_checks.py, responsive_checks.py
└── constants/
    ├── components.py                # NEW: grammar, budgets, scoring tables, recipes, CTA/label table, thresholds
    └── analytics.py                 # NEW: event + payload-field name registry (names only)
29.2 Placement rules (single source per concern, code edition)
Belongs in	Contents
contracts/artifacts.py	ComponentManifest (+ComponentInstance, BoundProp, SlotBinding, selection_trace block) — frozen models only
contracts/interfaces.py	ComponentRegistryView protocol; GateCheck (existing)
contracts/enums.py	ComponentFamily, PageRole, RegionKind, CommercialPurpose, LifecycleStatus, ListingKind, ConversionGoal, AssetRole
contracts/versions.py	Component-contract schema version; registry version registration
constants/components.py, constants/analytics.py, constants/gates.py	Every number, table, recipe, gate registration in this document
components/registry.py + catalog/	Definitions as data; pure lookups
component_engine.py + selection/ + validation/	Selection, binding, trace
rendering/ internals	Emitter functions + emitter table + CSS emission — the only markup knowledge
gates/checks/*	§21 gate families
tests/website_generation/components/	Everything in §30
Forbidden imports (extends the AES-WEB-001 §3.2 matrix, enforced by the same import-audit test): catalog/ imports only contracts/ + constants/; registry.py imports contracts/, constants/, catalog/; selection//validation//compatibility/ import contracts/, constants/, registry (read-only view); components/ never imports rendering/, gates/, repositories, or services; emitters never import components/ (they receive resolved instances — the emitter table is keyed by id string). Registry ownership: components/registry.py. Fixture ownership: tests/website_generation/fixtures/components/. Migration ownership: migration notes live with catalog modules; migration functions (schema-level) live in contracts/versions.py registrations per AES-WEB-001 §4.6.

30. Test Architecture
30.1 Test categories → tier mapping
Category	Tier	What it asserts
Contract tests	Unit	Every definition parses, budget-complies, grammar-complies
Registry tests	Unit	Uniqueness, ordering, indexes, registry_hash stability, 1:1 emitter mapping, lifecycle rules
Selection tests	Unit	§14 pipeline: filters, scoring, tie-breaks, fallbacks, failure diagnostics, trace correctness
Compatibility tests	Unit	Range evaluation truth table
Snapshot tests	Snapshot	Per component × variant × width-class emitted HTML; per-build CSS
Golden-rendering tests	Golden-build	Full-page renders for every §26 recipe from fixture manifests
Semantic-HTML tests	Unit	Landmark/heading/element assertions per emitter
Accessibility tests	Unit + integration	State-machine markup, labels, contrast pairings, focus wiring
Responsive-contract tests	Unit	Emitted CSS satisfies ResponsiveContract at §11.4 matrix
SEO-behavior tests	Unit	rel attrs, crawlable links, fragment validity, parity checks
Quality-gate tests	Unit	Every §21 gate fires correctly on its good/bad fixture pair
Deprecation tests	Unit	Deprecated exclusion, replacement mapping, allowance path
Replay tests	Full-regression	Fixture manifests re-select/re-render to identical hashes
Malicious-content tests	Unit	Injection fixtures render inert
Performance-budget tests	Integration	§25 thresholds against golden bundles
Import-audit tests	Integration	§29.2 matrix (extends AES-WEB-001 §3.3)
Monetization-disclosure tests	Unit	CG-COM-001/002/012 fixtures
Deterministic-ordering tests	Unit	Sorted invariants, double-run hash equality
30.2 Fixture architecture (per ACTIVE component — registration-enforced minimums)
fx-<id>-min (minimal valid), fx-<id>-full (every optional bound), fx-<id>-bad-prop (missing required prop), fx-<id>-bad-slot (invalid slot binding), fx-<id>-mobile (sm-width snapshot context), fx-<id>-long (long-content stress), fx-<id>-a11y (state-machine/label assertions), plus where relevant: fx-<id>-malicious (any user-influenced content), fx-<id>-sponsored (monetized components), fx-<id>-deprecated-vN (frozen forever per released version). Fixtures are frozen artifacts under tests/website_generation/fixtures/components/, serialized canonically, hashed; the registration test walks example_fixture_ids and fails any ACTIVE component missing its minimum set. Estimated suite impact: ~7–9 fixtures and ~10–14 assertions per component ⇒ the component system adds on the order of 700–900 tests at full MVP — planned, phased (§31), and the reason wave discipline exists.

31. Phased Implementation Roadmap
Global rules for every phase: independently useful; ends with the full Atlas regression suite green (zero regressions); no dependence on unfinished phases; complete files only; ZIP staging + extraction confirmation; zero-touch except explicitly authorized modifications; regression command for all phases: python -m pytest tests/ -q (full suite — the only accepted gate) with phase-scoped fast loop python -m pytest tests/website_generation/components/ -q. Delivery artifact for every phase: ZIP staged per AES-WEB-001 §9.3 discipline. Universal stop conditions: any regression; any import-audit failure; any need to modify an unauthorized file (stop and request amendment); any contract ambiguity (stop and record §34 clarification). Universal forbidden expansion: no production emitters before their wave; no AI integration anywhere (cognition is AES-WEB-001 Phase 4's concern); no new artifact kinds.

AES-WEB-002A — Contracts and Registry Foundation. Objective: freeze the component-contract schema and stand up the empty-but-governed registry. New files: contracts additions via authorized edits (see below), constants/components.py, constants/analytics.py, components/registry.py, components/catalog/__init__.py, components/selection/ (selector skeleton returning trace for empty registry), components/validation/, components/compatibility/, test modules + registry-integrity suite. Authorized modifications: contracts/enums.py (+new enums), contracts/artifacts.py (ComponentManifest minor bump: selection_trace), contracts/versions.py, constants/gates.py (gate ID reservations), engines/website_generation/__init__.py (exports). Contracts frozen at exit: ComponentDefinition schema, naming grammar, enums, ComponentRegistryView. Acceptance: registry loads/validates empty + 2 synthetic test definitions; selection returns deterministic results + traces on synthetic registry; import audit green; ComponentManifest round-trips with and without trace (schema minor compat proven). Risks: schema over-freeze — mitigated by synthetic-definition stress tests before freeze. Dependencies: AES-WEB-001 Phase 1 delivered.

AES-WEB-002B — Component Primitives (Wave 1). New: catalog/layout_atoms.py, 15 emitters (renderer-internal modules), full fixture sets, snapshot suites. Authorized mods: emitter-table registration point in rendering/, registry.py tuple. Acceptance: all 15 ACTIVE-eligible (every §23 criterion except "shipped in certified build"); double-render hash equality; CSS emitter handles token deps. Stop: any markup knowledge leaking outside emitters.

AES-WEB-002C — Navigation and Page Shell (Wave 2). New: catalog/navigation.py, emitters, drawer state-machine tests, skip-link/landmark gate fixtures. Acceptance: a fixture page renders shell + header + drawer baseline + footer passing CG-CMP-005/006, CG-A11Y-002/009/011 on fixtures.

AES-WEB-002D — Directory Discovery (Wave 3). New: catalog/discovery.py, emitters, facet-link crawl-safety fixtures, zero-results fixtures. Acceptance: home + category fixture pages compose from recipes §26.1–26.2 with real selection (not hand-pinned manifests).

AES-WEB-002E — Listing and Profile (Wave 4). New: catalog/listings_profiles.py, emitters, ListingKind fixtures (all nine kinds), stretched-link pattern tests. Acceptance: profile fixture page passes composition + NAP parity fixtures; sponsored/featured render distinguishably (CG-COM-001 fixtures).

AES-WEB-002F — Trust and Conversion (Wave 5). New: catalog/trust_conversion.py, form primitives integration, friction-budget tests, CTA hierarchy fixtures. Acceptance: lead-gen and claim fixture pages resolve; every E1–E11 doctrine rule has at least one failing fixture proving enforcement.

AES-WEB-002G — Local SEO and Editorial (Wave 6). New: catalog/seo_editorial.py, emitters, linking floor/ceiling fixtures, remaining recipe tables (editorial-guide, collection, service-area, verification, regional-hub — closing §26's bounded deferral). Acceptance: city-category programmatic fixture set (≥ 20 generated fixture pages) passes CG-SEO-004/007.

AES-WEB-002H — Monetization, Legal, and Status (Wave 7). New: catalog/monetization_status.py, emitters, disclosure fixtures. Acceptance: every §6.1 monetization cell exercisable; every role's required-status components resolvable.

AES-WEB-002I — Component Gate Families. New: gates/checks/component_checks.py, composition_checks.py, rendering_checks.py, commercial_checks.py, responsive_checks.py; all 63 gates + good/bad fixture pairs; constants/gates.py registrations. Authorized mods: constants/gates.py. Acceptance: gate-integrity suite (every gate fires both directions); Quality Gate Engine runs the extended list deterministically. Note: gate fixtures accumulate in B–H alongside components; I assembles them into registered gates — so I is integration, not greenfield.

AES-WEB-002J — MVP Integration. Objective: all §26 recipes resolve end-to-end from a PetTripFinder-shaped fixture BusinessSpec through selection → manifests → layout → render → assembly on fixture content. Acceptance: two full fixture sites (simple + every-component, mirroring AES-WEB-001 §11.5's two golden specs) build byte-stably; performance budgets pass. Forbidden: touching cognition.

AES-WEB-002K — Certification and Golden Fixtures. Objective: pin golden bundles + golden ComponentManifests (with traces) as the permanent regression anchor; produce the component-registry manifest snapshot; run the full AES-WEB-001 gate + AES-WEB-002 gate stack to a LaunchCertificate on the golden spec. Acceptance: certificate issued; replay reproduces identical hashes; documentation of the registry-hash → golden-hash linkage. Exit state: the component system is DONE for MVP; the next build input is a real directory spec.

32. Architecture Decision Record Summary
#	Decision	Rationale	Alternatives rejected	Consequences	Revisit trigger
ADR-01	Declarative registry, not generated code	Deterministic, auditable, testable as data; AES-WEB-001 §8.1 mandate	Code-gen templates; runtime component classes	Emitters carry all markup; registry stays inspectable	Never (doctrine)
ADR-02	Props configure, slots carry content; no free-form string props	Keeps copy in the content airlock; kills injection-by-prop	Stringly-typed props	Slight prop-modeling overhead	Never
ADR-03	Deterministic selection with static scoring; no AI selection	Replayability; explainability; AES-WEB-001 §1.3 litmus test	AI-ranked selection; weighted heuristics with floats	Recipes must be authored; taste is encoded, not generated	If selection quality proves the binding constraint on site quality after ≥ 3 launches
ADR-04	Semantic tokens only; no hard-coded styles	Portfolio-wide rebranding = token recompilation; contrast verifiable	Per-component styles; utility-class free-for-all	Token schema becomes a critical contract	Token schema major bump
ADR-05	Variants governed by budget; commercial-intent differences become components	Prevents mega-components; keeps contracts honest	Boolean-flag accretion	More definitions, each simpler	Budget shown too tight/loose across 2 waves
ADR-06	Registry constants + explicit tuple; no dynamic discovery	Deterministic ordering; merge-visible; AES-WEB-001 §3.5	Filesystem scanning; entry-point plugins	One-line tuple edits per addition	Never
ADR-07	Static HTML, 0 KB required JS, ≤ 30 KB enhancement	Determinism, auditability, speed, hosting cost (AES-WEB-001 §8.5)	Client-side rendering; hydration frameworks	Interactive capabilities gated to P3 seams	Dynamic-bundle seam activation
ADR-08	Analytics as declared data-attributes; no embedded analytics	Honors AES-WEB-001 deferral; keeps core vendor-free	GA snippet in emitters	Instrumentation waits for deployment layer	Analytics authority doc
ADR-09	Directory-specialized components over generic blocks	Atlas manufactures directories; specificity is the moat	Generic page-builder blocks	Less reuse outside directories — acceptable	New non-directory business line
ADR-10	Immutable definition versions; migration = new build	Certified-build replay forever	In-place upgrades	Registry grows monotonically	CAS/registry size at scale
ADR-11	Strict composition rules, depth-6, parental spacing	Systematic pages; prevents design drift	Arbitrary nesting freedom	Occasional legitimate layouts need new primitives	≥ 3 recipes blocked by the same rule
ADR-12	Ethical-conversion doctrine as BLOCKING gates	Trust is asset value; SEO safety; exit-multiple protection	"Growth" dark patterns	Some short-term CRO tactics unavailable	Never (doctrine); tactics reviewed within E1–E11
ADR-13	Sponsored-content disclosure: visible + semantic + machine-readable + analytic	Regulatory and search-policy alignment; non-confusion rule	Label-only disclosure	Paid units are unmistakable	Regulatory change
ADR-14	Selection trace embedded in ComponentManifest (minor schema bump)	Provenance travels with the artifact; no casual artifact; replay-verifiable	New artifact; BuildManifest embedding; side metadata	Manifest size (bounded by compression)	Trace size in practice > manifest-size budget
33. Risk Register
P/I: L/M/H probability and impact. Owner: CA = Chief Architect, IS = implementation session, RS = regression suite (mechanical).

Risk	P	I	Early warning	Mitigation	Owner	Phase
Component-library explosion	M	H	Catalog PRs adding components not demanded by a recipe	§28 capability doctrine; §7.2 governance table	CA	Post-K
Uncontrolled variants	M	M	Complexity scores nearing 20	§7.3 budget is BLOCKING at registration	RS	B–H
Generic-looking websites	H	H	Golden sites feel templated	Brand-profile scoring inputs (§14.2.6); content variation via AES-WEB-003; treat as top post-launch review item	CA	J+
Rigid templates	M	M	Recipes blocking legitimate pages	Flexible zones; recipe amendment path	CA	G+
Accessibility regressions	L	H	Snapshot diffs touching ARIA	BLOCKING gates + per-version frozen fixtures	RS	All
SEO regressions	M	H	CG-SEO-007 warnings clustering	Linking gates; programmatic fixture set (G)	RS	G+
Rendering drift	L	H	Golden hash changes without bumps	AES-WEB-001 §11.4/11.5 discipline	RS	All
Content overflow / long-content breakage	M	M	fx-long failures	Mandatory long-content fixtures	IS	B–H
Mobile failures	M	H	CG-RSP failures late	Mobile fixtures from Wave 1, not retrofitted	IS	B+
Sponsored-content confusion	L	H	CG-COM-001 near-misses in review	Non-confusion rule; distinct tokens; gate fixtures	RS	E, H
Deprecation debt	M	M	DEPRECATED count rising, RETIRED = 0	§22.4 sunset ritual per registry minor	CA	Post-K
Registry incompatibility	L	H	Compatibility-range failures	§22 axes + CG-CON-008	RS	All
Slow build times	L	M	Golden-build wall-clock creep	AES-WEB-001 §11.7 budget assertions	RS	J+
Excessive DOM / JS	L	M	§25 threshold warnings	Budgets in constants; gate-enforced	RS	All
AI content not fitting component contracts	M	H	ContentValidationError rates in Phase-4 cognition	Slot schemas published to prompt contracts; §8.4 typed models designed for draftability	CA	WGE Phase 4
Design-token mismatch	M	M	Undeclared-token render failures	Registry token-dependency cross-check	RS	B+
Quality-gate false positives	M	M	Good fixtures failing after gate edits	AES-WEB-001 §10.4 two-fixture law (the AES-005A lesson)	RS	I
Overengineering before launch	H	H	Phases stretching; no certified real site	§31 phase stop conditions; Assessment Q5/Q9 discipline	CA	All
Insufficient MVP breadth	L	M	Recipe slots with no eligible component	72-count derived from §6.1 matrix, not vibes	CA	J
Excessive implementation time	M	H	Fixture burden dominating deliveries	Fixture generators as test utilities (fixtures stay frozen data; generators aid authoring)	IS	B–H
Too many primitives, too few commercial components	M	M	Wave 1–2 gold-plating	Wave exit criteria are recipe-resolution, not primitive polish	CA	B–C
Fragmented authority registry vs renderer	L	H	Markup decisions appearing in catalog data	§3.1 ownership map; import audit; review rule	RS	All
34. Binding Decisions, Deferred Decisions, and Required Amendments
34.1 Binding decisions resolved by this document
Component contract shape (§3) and single-source ownership map (§3.1).
Naming grammar, namespaces, permanent IDs (§4). 3. Sixteen-family taxonomy (§5). 4. Eighteen-role composition law + ListingKind semantics + non-confusion rule (§6). 5. Variant governance + complexity budget (§7). 6. No free-form string props; typed content models (§8). 7. Depth-6 composition + parental spacing + prohibited compositions (§9). 8. Semantic-token-only consumption; no runtime fallbacks (§10). 9. Single breakpoint authority; responsive ownership split (§11). 10. WCAG 2.2 AA with approved BLOCKING elevations (§12, per operator approval). 11. SEO capability-declaration / SEO-Engine-authority split (§13). 12. Deterministic selection pipeline + embedded selection trace (§14, ADR-14, approved). 13. Registry governance, explicit tuple, registry hash (§15). 14. Conversion contract, goal enum, repetition limits, friction budgets (§16). 15. Four-part monetization disclosure (§17). 16. Data-attribute analytics contract, zero SDKs (§18). 17. Security owner map (§19). 18. Emitter architecture + manifest-driven CSS tree-shaking (§20). 19. 63-gate component catalog (§21). 20. Versioning classes + eternal replay guarantees (§22). 21. Lifecycle states + promotion criteria + approval authority (§23). 22. 0 KB required JS / ≤ 30 KB enhancement (§24). 23. Performance thresholds in constants (§25). 24. Recipe system with flexible zones (§26). 25. 72-component MVP across 7 waves (§27). 26. Capability-based expansion + classification discipline (§28). 27. Package layout + import rules (§29). 28. Fixture minimums + test-tier mapping (§30). 29. Phase plan A–K (§31).
34.2 Deferred decisions (intentional, with owners)
Deferral	Deferred to
Five secondary recipe tables (editorial-guide, collection, service-area, verification, regional-hub) — rules already bound by §6.1	AES-WEB-002G/H deliveries
Dark mode / high-contrast token packs (contracts ready §10.4)	Design System Authority
Interactive maps, autocomplete, saved searches, favorites, dialogs, multi-step intake, affiliate/native/lead-purchase monetization	P3 per §5/§28 preconditions
Analytics instrumentation + experimentation engine (identifiers reserved)	Analytics authority document, post-revenue
Trust-adjacency gate CG-COM-009 elevation W→B	After conversion data from first launches
Visual/screenshot regression	AES-WEB-001 Part 13 deferral stands
Dynamic bundles / stateful components	AES-WEB-001 §8.6 seam
Fixture-generator tooling design	AES-WEB-002B, as test utilities
34.3 Required AES-WEB-001 Clarifications or Future Amendments
All four are minor (additive), proposed as AES-WEB-001 v1.1.0 in one amendment delivery before AES-WEB-002A ships:

A1 — ComponentManifest schema (approved). §4.1 artifact #6: append to Contents — "optionally carries a schema-versioned selection_trace block recording per-slot candidate filtering, scoring, and tie-breaking; produced deterministically by the Component Engine; ignored by the Layout Engine." contracts/versions.py: ComponentManifest schema minor bump (e.g. 1.0.0 → 1.1.0) registered with no migration required (additive optional field).
A2 — Accessibility gate severities (approved). §10.2 Accessibility row: move heading-hierarchy and landmark defects from the WARNING clause into BLOCKING, and note that AES-WEB-002 §21.4 registers the expanded accessibility gate family under the §3.5 registration mechanism. Wording: severity column becomes "BLOCKING (alt text, contrast, labels, keyboard/focus/semantic-structure/form-completion per AES-WEB-002 §12.7) / WARNING (optimization-tier)".
A3 — Part 2 normative tree. Authorize the components/ subpackages (catalog/, selection/, validation/, compatibility/), the five new gates/checks/ modules, and constants/components.py + constants/analytics.py. Additive; dependency matrix unchanged; import-audit whitelist extended per AES-WEB-002 §29.2.
A4 — Part 13 Phase 2 scope note. The Phase 2 "minimal component registry (header, hero, listing grid, detail block, text section, footer)" is superseded in scope by the AES-WEB-002 wave structure; AES-WEB-001 Phase 2's deliverable proof (fixture spec → byte-stable static site) is achieved at AES-WEB-002D exit using Waves 1–3 plus a provisional listing card, and completed through 002J. No contract change — a scope-mapping clarification so the two roadmaps cannot be read as competing.
No contradiction requiring a weakening of AES-WEB-001 was identified. One genuine ambiguity resolved without amendment: AES-WEB-001 §5.5 says "Registry additions minor" — this document clarifies (consistently) that variant additions are also minor and definition-version majors do not force a registry major (§22.2).

34.4 Recommended next authority documents
AES-WEB-003 — Commercial Content System Architecture. Programmatic content variation, slot schemas ↔ prompt contracts, per-role content depth requirements, thin-content policy. This is the highest-leverage next document: the generic-looking-site risk (§33 top risk) is a content problem more than a component problem.
AES-WEB-004 — Atlas Design System Authority. Brand-profile taxonomy, token scale generation rules, palette/typography derivation depth for the Brand Engine, dark/high-contrast packs. Needed before the portfolio exceeds ~3 visually distinct directories.
AES-WEB-005 — Directory Data Operations Authority. Listing data sourcing, freshness, verification methodology, correction workflow backend — the operational truth behind §6.3's ListingKind states.
(Post-revenue only) AES-WEB-006 — Analytics and Experimentation Engine. Activates §18's reserved identifiers. Deliberately last: instrumenting zero-revenue sites is measurement theater.
No further documents are recommended; a Conversion Optimization Engine document would be premature before AES-WEB-006 data exists.

35. Final Chief Architect Assessment
Candid answers, in order.

1. Is AES-WEB-001 sufficient to begin coding the WGE foundation? Yes, with the four minor amendments in §34.3 batched first. Its contracts, dependency matrix, state machine, and testing strategy are implementation-ready; nothing in this document required weakening it, which is the strongest signal of its quality.

2. Which portions of the component system must exist before the first real Atlas directory can be generated? Waves 1–5 plus the wave-7 disclosure/status/legal components, the recipe tables for home, category, city, city-category, search-results, business-profile, and the gate families CG-CON/CMP/RND/A11Y plus CG-SEO-002/003/004 and CG-COM-001/003/004. Wave 6 editorial and the remaining recipes improve the asset but do not block first generation.

3. Smallest commercially credible MVP component count? Honestly: about 45 could certify a first directory (the subset in Q2). The recommended 72 is the smallest count at which all MVP recipes resolve without contract-sharing hacks. If schedule pressure bites, cut Wave 6 and the secondary recipes — never cut gates, disclosure, or status components.
S
4. Strongest long-term competitive moat? Not the components themselves — any team can build cards and heroes. The moat is the combination: deterministic selection with permanent traces, the certification gate stack, and the ListingKind trust semantics. That triad produces portfolio-scale directories that are auditable, replayable, rebrandable by token swap, and trustworthy in a way scraped-and-templated competitors cannot cheaply copy. Second moat: §6's directory-specific composition law — encoded operator judgment.

5. What should not be built yet? Everything in §34.2's P3 list; the analytics engine; dark mode; the ext. namespace; fixture tooling beyond simple generators; any component not demanded by a §26 recipe. Also: resist building AES-WEB-003 before 002E — content architecture designed against unbuilt components will churn.

6. Most damaging architectural mistake at this stage? Letting markup knowledge leak out of emitters — into catalog data, props, or content. It is the one violation that quietly breaks determinism, security, versioning, and the registry model simultaneously, and it is the hardest to unwind after 72 components exist. The import audit and §3.1 ownership map exist to make it structurally difficult; reviews must make it culturally unthinkable.

7. Too ambitious, appropriately ambitious, or not ambitious enough? Appropriately ambitious in architecture, deliberately restrained in scope — with one honest caveat: the fixture burden (§30.2, ~700–900 tests) is the real cost center, and Atlas's history says the risk is polishing the machine instead of shipping the product. The mitigations are the phase stop conditions and Q9 below. The architecture is not under-ambitious anywhere that matters for directories; it is intentionally under-ambitious about interactivity, which is correct for static-first assets.

8. What should Claude Code implement first after approval? The AES-WEB-001 v1.1.0 amendment delivery (§34.3), then AES-WEB-002A exactly as scoped in §31 — contracts and registry foundation, frozen before any catalog entry exists.

9. What should Atlas intentionally defer until after its first revenue-producing directory launches? Wave-6 breadth beyond the linking components; all P3 capabilities; AES-WEB-006 analytics; PREFERRED-tier curation; the 200–500 library path entirely; and — bluntly — any further authority documents beyond AES-WEB-003. The portfolio thesis is validated by a directory that earns money, not by a component system that could theoretically build five hundred of them. PetTripFinder's revenue history is the standing reminder.

10. What part of this architecture is most likely to slow implementation unnecessarily? The per-component fixture minimums. They are also the part that has repeatedly saved Atlas (the AES-005A gate false-positive incident). Keep them — but implement fixture authoring generators in 002B so the minimums cost minutes per component, not hours, and hold the line that generated fixtures are frozen at generation time, never regenerated silently.

End of AES-WEB-002 — Commercial Component System Architecture, v1.0.0. Amendments by version bump only.


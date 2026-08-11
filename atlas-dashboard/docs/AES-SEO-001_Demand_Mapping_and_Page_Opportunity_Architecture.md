# AES-SEO-001 — Demand Mapping & Page Opportunity Architecture

| Field | Value |
|---|---|
| Document ID | AES-SEO-001 |
| Version | 1.0.0 |
| Date | 2026-08-09 |
| Status | **APPROVED — ACTIVE AUTHORITY** (operator-approved 2026-08-09) |
| Governs | All implementation of the Atlas Demand Mapping subsystem: `engines/demand_mapping/`, `services/demand_research/`, `repositories/demand_research/`, and their tests |
| Upstream authorities | Website Generation Engine Master Blueprint (intent, esp. Plane 3.2); Atlas Platform Architecture (CLAUDE.md architectural rules); AES-WEB-001; AES-WEB-002 (both boundary-defining, not superiors within this territory — see §0) |
| First validation fixture | PetTripFinder / Columbus (fixture only — never a dependency of generic code) |
| Amendment policy | Amendments by version bump only, never silently. Any change to a normative MUST/SHALL rule is at least a minor version. Any change to a frozen contract, provenance semantics, gate determinism, or the WGE boundary is a major version. |

Normative language: **MUST**, **MUST NOT**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **MAY** are used per their conventional (RFC-2119-style) meanings. Non-normative rationale appears as indented *Rationale* notes.

Operator decisions incorporated as fixed inputs to this document (no longer open): AMB-1 (this document is the authority vehicle), AMB-2 (name = Demand Mapping; packages as in §3), AMB-3 (new canonical five-state provenance model), AMB-4 (integer-only numerics in canonical artifacts).

---

## 0. Document Authority and Precedence

0.1 **Precedence order.** For any question touching Demand Mapping, the binding order is:

1. **Master Blueprint intent** (`docs/website_generation_engine_architecture (2).md`) — supreme intent authority. Plane 3.2 (Demand Mapping Engine, DemandMap, gap list, orphan list, "Pages without demand justification require explicit strategic exemption") is the intent this document implements. In any conflict between this document and Blueprint intent, Blueprint intent wins and this document MUST be amended by version bump — never silently.
2. **AES-SEO-001 (this document)** — implementation authority for the Demand Mapping subsystem and its three packages.
3. **ADRs filed under this document** — subordinate clarifications within this territory; an ADR SHALL NOT contradict a normative rule here.
4. **Implementation phases/prompts** — Level 4. Implementation tasks do not create architecture. Any contract ambiguity, or any need to modify a file this document does not authorize, is a stop condition: halt and request an AES-SEO-001 amendment or clarification.

0.2 **Boundary with AES-WEB authority.** AES-WEB-001 and AES-WEB-002 are not superiors of this document; they are **adjacent authorities whose territory this document MUST NOT enter**. Everything inside `engines/website_generation/` — the 13-ArtifactKind catalog, the `PageRole` enum, `PagePlan`, `SiteArchitecture`, `SEOEngine`, the state machine, the frozen-contract register — remains exclusively under AES-WEB authority. Where Demand Mapping output must eventually touch the WGE (the IA handoff), the change is made **by AES-WEB-001 amendment under AES-WEB authority**, following the ADR-WEB-LISTING-DATASET precedent (a new input ArtifactKind introduced by explicit amendment). This document resolves the prior authority gap (the Index's "Plane 3.2 Demand Mapping — Deferred intent (no MVP home)") **without modifying AES-WEB-001**.

0.3 **AES-WEB-001 amendment is deferred.** No AES-WEB-001 amendment is proposed, drafted, or implied by this document. The amendment SHALL be authored and separately operator-approved only when Demand Mapping output is actually introduced as an Information Architecture input (Phase F, §23). Until then, zero WGE files change (§21).

0.4 The Atlas Website Generation Architecture Index has zero normative force with respect to this document, as with all others. If the Index later maps this subsystem, that mapping is navigational only.

0.5 **Note on AES-WEB-002 §34.4.** That section's closing remark ("No further documents are recommended") predates the operator's AMB-1 decision and is superseded by it for this subsystem. This is recorded here as an explicit, non-silent divergence; AES-WEB-002 itself is not modified.

---

## 1. Purpose

1.1 **The problem.** Atlas can deterministically manufacture websites but has no system that decides, from evidence, *which pages deserve to exist*. The repository holds the proof: `SEOEngine` compiles metadata only for pages already in `SiteArchitecture`; IA derives pages solely from `BusinessSpec.directory_taxonomy`, a `ListingDataset`, and caller-supplied editorial tuples; the launch-kit planning CSVs (`seo_pages.csv`, `content_plan.csv`) are structurally empty and read by no production code; and no demand, SERP, or keyword evidence exists anywhere in the repository. Demand Mapping fills exactly this gap: it answers *"Given a business concept, its inventory/data, and available demand/search/competition evidence, what page opportunities may deserve to exist, what evidence supports them, and which ideas should explicitly be rejected or deferred?"*

1.2 **How it differs from SEOEngine.** `SEOEngine` (AES-WEB-001 §5.8) answers a downstream question — *"for a page that already exists, what deterministic metadata does it receive?"* Demand Mapping answers the upstream question — *"what pages might deserve to exist, and on what evidence?"* The two subsystems SHALL never call each other; they meet only at the operator-approved handoff artifact (§21). SEOEngine remains unchanged for all initial phases.

1.3 **How it differs from opportunity_v2 niche scoring.** `services/opportunity_v2/` answers *"which business/niche/market should Atlas enter?"* — a business-selection question, scored at niche granularity with float weights. Demand Mapping operates **after** that decision, at **page** granularity, inside an already-chosen business, under integer-only, versioned, deterministic contracts. Demand Mapping MUST NOT import opportunity_v2 code or its divergent TaggedValue variants (AMB-3); it MAY reuse its *patterns* (provider protocol, evidence-only doctrine) by reimplementation.

1.4 **How it differs from directory_blueprint template SEO.** `engines/directory_blueprint/seo_planner.py` emits static, hard-coded template strings with no evidence input and no ability to reject anything. Demand Mapping is evidence-driven, inventory-aware, and produces explicit negative decisions. The template planner is legacy and SHALL NOT be extended to serve this purpose.

1.5 **Why "do not create this page" is a first-class outcome.** The Blueprint requires an orphan list ("pages with no demand — candidates for cutting") and demand justification for every indexable URL. The repository also contains the cautionary counter-example: `SeoBuildEngine` generates every category×location page unconditionally. Thin programmatic pages destroy directory businesses; therefore a rejected or deferred opportunity is a *deliverable*, carried with machine-readable reasons — not a silent absence (§11).

---

## 2. Scope

2.1 **IN SCOPE** (this subsystem SHALL provide):
- Evidence modeling: canonical, provenance-tagged observations and immutable snapshots (§5, §6)
- Inventory dimension profiling: domain-agnostic discovery of a project's data dimensions (§7)
- Search/demand evidence, SERP evidence, competition evidence — via the provider architecture (§16)
- Search-intent classification (§9)
- Page-opportunity generation (§8, §10)
- Hard rejection/defer gates and page-explosion prevention (§11)
- Conceptual content and cluster planning (§14, §15)
- Operator approval workflow (§13)
- Evidence provenance, versioning, reproducibility (§5, §18, §19)
- Budgeted, fail-closed provider architecture (§16, §17)

2.2 **OUT OF SCOPE** (this subsystem SHALL NOT provide):
- URL, route, or slug generation of any kind
- IA route materialization, `PagePlan`, `SiteArchitecture`
- SEO metadata generation (titles, metas, canonicals, robots, sitemaps)
- Content prose generation
- Rendering, assembly, publishing, deployment
- Autonomous mass page creation
- Ranking tracking (initial phases; §23 Phase H governs later measurement)
- Structured-data implementation

---

## 3. Architecture Layers

3.1 **Three packages, one dependency direction.**

```
services/demand_research/            (I/O world: providers, adapters, budget,
        │                             approval orchestration)
        │ imports contracts of ▼      persists via ▼
engines/demand_mapping/       repositories/demand_research/
(deterministic core + contracts)     (append-only persistence)
```

3.2 **`engines/demand_mapping/`** — the deterministic core. SHALL contain: `contracts/` (frozen models: provenance, evidence, dimensions, opportunities, decisions, versions), `profiling/` (inventory records → DimensionProfile), `opportunities/` (profiles × families × evidence → PageOpportunitySet), `gates/` (hard gates, dedupe, reasons). One public class per engine module; one public verb per engine (`profile`, `generate`, `evaluate`). Frozen artifact in, frozen artifact out. Engines SHALL NOT log, print, or touch the clock.

3.3 **`engines/demand_mapping/` MUST NOT import:** `services/`, `repositories/`, `routes/`, `engines/website_generation/` (or any other engine package), Flask, network libraries (`requests`, `urllib`, `urllib3`, `http`, `httpx`, `socket`), model APIs (`anthropic`, `openai`), or clock/random/identity libraries (`time`, `datetime`, `random`, `secrets`, `uuid`), or `logging`. This list mirrors the WGE import audit and SHALL be enforced by an equivalent AST-walking test from Phase A onward. Allowed imports: stdlib (minus the banned modules), pydantic via the repo's v1/v2-compatibility pattern, and the package's own modules.

3.4 **`services/demand_research/`** — the only home for external work. SHALL contain: `providers/` (the EvidenceProvider protocol and all adapters, §16), `adapters/` (per-project inventory adapters — the **only** place project/domain names may appear, §22), evidence capture/freezing, budget enforcement (§17), and approval orchestration (§13). Services MAY import `engines/demand_mapping/` contracts, `requests` (the dependency baseline's sanctioned HTTP client), and `repositories/demand_research/`. All network, credential, clock, and environment access lives here and only here.

3.5 **`repositories/demand_research/`** — persistence only. Zero planning logic, zero scoring, zero Flask. Owns the content-addressed evidence store, snapshot registry, decision records, and run records (§18).

3.6 **Composition.** Services compose engine calls; engines never compose services. Routes (if any are ever added) orchestrate only, per Atlas platform law. There SHALL be no module outside `services/demand_research/` that chains engine stages.

3.7 **WGE isolation is bidirectional.** `engines/website_generation/` MUST NOT import any Demand Mapping package, and vice versa. The subsystems meet only at artifacts, and only after the Phase-F AES-WEB-001 amendment (§21).

---

## 4. Determinism Contract

4.1 **Core law.** Given the same frozen inputs (inventory snapshot, EvidenceSnapshot, operator directives, engine versions), every deterministic engine SHALL produce byte-identical canonical output with an identical content hash. This is the replayability contract.

4.2 Inside `engines/demand_mapping/` there SHALL be: no wall-clock reads (all time enters as explicit `*_at` string parameters), no network, no randomness, no environment-variable reads, no filesystem access, no model calls, no mutable module-level state, no logging. Identity is content-derived (SHA-256 of canonical serialization), never a UUID or random value.

4.3 **Deterministic ordering.** All collections in canonical artifacts are tuples with defined, stable sort orders. Diagnostics and gate results SHALL have fixed bucket ordering. Output MUST NOT depend on input iteration order.

4.4 **Canonical serialization.** UTF-8 JSON, sorted keys, compact separators; artifact identity = SHA-256 of the canonical JSON. Canonicalization SHALL reject `float` values outright (AMB-4): all numerics are integers, using declared scales where fractional precision is needed (basis points, integer cents, micro-degrees, hundredths — following the WGE's `rating_hundredths`/`lat_micro` precedent). Internal float arithmetic inside a pure function MAY exist only if provably platform-stable and only integer results escape into any model.

4.5 **Engine versioning.** Every engine declares a version; the version SHALL be bumped whenever output could differ for identical input. Every output artifact records the versions that produced it (§19).

4.6 **The I/O frontier.** External evidence collection is non-deterministic-world I/O and lives in services. The contract is: **collection may vary; planning may not.** Once observations are frozen into an EvidenceSnapshot, every downstream computation is deterministic and replayable. A planner run therefore binds to snapshot hashes, and replaying it against the same snapshots and versions MUST reproduce identical output hashes.

---

## 5. Provenance Model

5.1 **Canonical five-state provenance** (AMB-3). Defined once, in `engines/demand_mapping/contracts/`, as a closed frozen enum. No existing Atlas TaggedValue variant is imported or retrofitted.

| State | Meaning |
|---|---|
| `VERIFIED` | The value came from a live external provider call or an authoritative external record; a real source returned this specific value. |
| `ESTIMATED` | The value came from a deterministic model with no external call; reproducible from its inputs; honest about being a model output. |
| `DERIVED` | The value was computed from other tagged observations; it MUST reference every input observation it was derived from. |
| `OPERATOR` | The value is explicit human-supplied evidence or attestation, identified to its operator submission. |
| `UNKNOWN` | No honest basis exists for a value. UNKNOWN is a representable state, never an error. |

5.2 **Rules (all binding):**
- (a) `ESTIMATED` MUST NEVER be represented, upgraded, merged, or displayed as `VERIFIED`. Where values from multiple sources are merged, the merge SHALL be provenance-aware with a single, versioned priority order defined once in contracts (no copy-pasted priority tables).
- (b) `DERIVED` MUST carry references to its source observations; a `DERIVED` value whose inputs include `ESTIMATED` or `UNKNOWN` data MUST NOT present higher provenance than its weakest load-bearing input.
- (c) `OPERATOR` evidence MUST identify its submission (operator record reference); it represents human attestation, not machine inference.
- (d) `UNKNOWN` MUST be preferred over fabrication. No fallback, default, or synthesized value may masquerade under any other state (see also §17.6, §20).
- (e) Provider/source identity (`provider_id`, `provider_version`) MUST be retained on every observation and survive every transformation.
- (f) Observation timestamps (`observed_at`) are explicit input data captured at the service layer; the deterministic core MUST NOT create them.
- (g) Stale evidence MUST remain identifiable: staleness is computed by gate policy from `observed_at` versus a policy-declared reference time supplied as an explicit input — never by the core reading a clock. Stale observations degrade in gate evaluation (§11) rather than being silently reused as fresh.

5.3 **Confidence.** Confidence SHALL be represented as an integer scale — basis points (0–10000) unless a contract declares another integer scale. `UNKNOWN` observations carry no confidence value. Confidence is metadata about an observation; it never substitutes for provenance.

---

## 6. Evidence Observation / Snapshot

6.1 **`EvidenceObservation`** — the atomic unit of external knowledge. Minimum conceptual contract (exact schema fixed in Phase A):

- `observation_id` — content-derived hash
- `observation_type` — closed, versioned vocabulary (e.g. demand volume, query suggestion, SERP composition, competitor presence, question demand, page-performance metric)
- `provider_id`, `provider_version`
- `query` / topic and full `query_params` (everything needed to reproduce the request)
- `market_scope` — market/geographic scope descriptor (conceptual, not a URL)
- `observed_at` — explicit ISO-8601 string, supplied by the service layer
- `provenance` — §5 state
- `confidence` — integer basis points (absent for UNKNOWN)
- `value` — typed, integer-numeric payload per observation type
- `raw_ref` — content hash referencing the raw external response in the content-addressed store (§18)
- `derived_from` — tuple of observation IDs (required when provenance = DERIVED, forbidden otherwise)

6.2 Raw external response bodies SHALL NOT be embedded inside immutable artifacts; a content-addressed repository reference (`raw_ref`) is the required mechanism. Raw payloads are stored once, hashed, and referenced.

6.3 **`EvidenceSnapshot`** — an immutable, content-addressed set of observations frozen at a point in time. Identity = hash of its canonical form (sorted observation IDs plus snapshot metadata). Snapshots are append-only in the store: a "newer" snapshot is a new snapshot, never a mutation (§18). Every planner run, gate evaluation, and operator decision binds to a snapshot hash (§4.6, §13).

6.4 An empty or partial snapshot is legal. Absent evidence types evaluate as `UNKNOWN` in gates — the system MUST function honestly with no external evidence at all (this is the Phase-B/D reality).

---

## 7. Domain-Agnostic Inventory Model

7.1 **The adapter wall.** Project-specific inventory (files, schemas, field names) SHALL be converted into a **generic record form** by a per-project adapter in `services/demand_research/adapters/`. Generic engine logic MUST NOT contain project or domain field names, and MUST NOT branch on domain semantics. This mirrors the ADR-WEB-LISTING-DATASET rule that mapping from legacy/external models is a service-layer concern outside the contract.

7.2 **Generic record form.** A neutral entity-record representation: entity ID, entity-kind label (opaque string to the engine), and a set of field values with per-field provenance tags where the source data carries them. The engine treats field names as opaque identifiers.

7.3 **`DimensionKind`** — closed enum, minimum members: `CATEGORICAL`, `NUMERIC`, `BOOLEAN`, `GEOGRAPHIC`, `ENTITY_REF`, `TEXT`. New kinds require a contracts version bump.

7.4 **`DimensionProfile`** — the deterministic profiler's output, per discovered dimension:
- dimension identity: `dimension_id`, source field path (opaque), kind
- `entity_count` (population), `coverage_count` (entities with a value), `missing_count`, `distinct_count` (cardinality)
- frequency distribution (top-N value/count pairs, deterministic ordering)
- numeric range and distribution summary, integer-encoded with declared scale (NUMERIC kind)
- provenance coverage: counts of values per §5 state
- relationships/co-occurrence: which dimensions are conditioned on or co-present with others, where computable

7.5 **No domain-specific branch logic.** Generic planning and gating rules SHALL be expressed only in profile terms ("a CATEGORICAL dimension with distinct_count 3 and coverage ≥ X%"), never in value terms. Enforcement: a domain-neutrality test (§22.3) fails the build if project/domain literals appear under `engines/demand_mapping/`.

---

## 8. Page Opportunity Contract

8.1 **`PageOpportunity` is PRE-IA.** It represents a *reason a page might deserve to exist* — never a page. It MUST NOT contain: a production URL, a route, a slug, or a canonical URL. No field of any Demand Mapping contract may hold a route-shaped value; contracts SHALL be designed so the subsystem cannot mint a URL even by defect.

8.2 **Required conceptual contents** (exact schema fixed in Phase A):

| Group | Fields |
|---|---|
| Identity | `opportunity_id` (content-derived, stable), schema version |
| Intent | `intent_class` (§9) |
| Target | target concept: dimension/value references into DimensionProfiles; geographic scope **concept** (market/area descriptor, not a route) |
| Queries | candidate queries/topics, each with evidence references |
| Evidence | demand evidence refs, SERP evidence refs, competition evidence refs — all observation/snapshot references, provenance-tagged |
| Inventory | inventory support: entity count, differentiated count, coverage on the defining dimensions |
| Feasibility | content feasibility: which required facts exist at what coverage |
| Assessment | confidence (integer basis points, derived from provenance mix), risk flags (thin-content, cannibalization-candidate, stale-evidence, overlap) |
| Shape | recommended `opportunity_family` (§10), cluster relationships (§15) |
| Decision | gate results (per-gate outcome + machine-readable reason codes), `decision_state` (§10.4/§11.4/§13), decision reasons |
| Reproducibility | `evidence_snapshot_hash`, inventory snapshot hash, planner engine version, gate-policy version |

8.3 **PageOpportunity vs WGE PagePlan — explicit differentiation.** `PagePlan` (`route, page_type, title, content_slots`) is an IA-owned WGE artifact describing a page that *will exist* at a *specific route*. `PageOpportunity` is an evidence-bearing proposal with no route, no title, no slots, produced upstream of `BusinessSpec` consumption. IA remains the single arbiter of what pages exist and at which routes; route generation stays a major-version event under AES-WEB-001 §5.3 ("URLs are public commitments"). Demand Mapping proposes; IA disposes.

8.4 **`PageOpportunitySet`** — the run-level artifact: an immutable, versioned, content-hashed collection of PageOpportunity records (including DEFERRED and REJECTED ones, §11.5), bound to its input snapshot hashes.

---

## 9. Intent Classification

9.1 The initial intent vocabulary is a **closed enum of five values**, adopted from the Master Blueprint's intent classification: `INFORMATIONAL`, `COMMERCIAL`, `TRANSACTIONAL`, `NAVIGATIONAL`, `LOCAL`.

9.2 Every PageOpportunity SHALL carry exactly one primary intent class. Secondary intents MAY be represented as an ordered tuple if Phase-A contract design finds it necessary; if so, the primary remains single-valued.

9.3 **Versioning.** Adding, removing, or re-defining an intent value is a contracts **minor** version (additive value) or **major** version (semantic change/removal), recorded in the contracts version registry (§19). Implementation phases MUST NOT add values ad hoc.

---

## 10. Opportunity Families

10.1 **`OpportunityFamily`** — a closed, generic vocabulary describing the *shape* of a proposed page, defined in Demand Mapping contracts (not imported from the WGE). Initial members:

`GEOGRAPHIC_LANDING`, `CATEGORY`, `CATEGORY_GEOGRAPHIC`, `ENTITY_PROFILE`, `FACET_COLLECTION` (attribute/facet), `COMPARISON`, `BEST_OF`, `COLLECTION`, `EDITORIAL_GUIDE`, `FAQ_INFORMATIONAL`, `REGIONAL_HUB`.

10.2 The family vocabulary is deliberately **not** 1:1 with the WGE `PageRole` enum. Two families (`FACET_COLLECTION`, `FAQ_INFORMATIONAL`) have no crisp PageRole today; several PageRoles (submission, claim-listing, verification, …) are conversion/operational pages that are not demand opportunities.

10.3 **Mapping to PageRole is a future handoff concern.** A static, declared OpportunityFamily→PageRole mapping SHALL be authored as part of Phase F, under AES-WEB authority, and MAY require an AES-WEB-002 §6 amendment (e.g., if a facet role is warranted). Until Phase F, any such mapping in Demand Mapping code is advisory documentation at most; it MUST reference PageRole values as plain strings, never by importing `engines/website_generation`.

10.4 New families require a contracts version bump (§19). Families carry no rendering semantics; they are planning vocabulary only.

---

## 11. Page-Explosion Prevention

11.1 **This section is load-bearing.** The subsystem's defining risk is generating thousands of weak pages. Prevention is deterministic-first, operator-final.

11.2 **Hard gates (deterministic, fail-closed).** Gate policy is versioned data (§19). The initial gate set SHALL include:

| Gate | Rule |
|---|---|
| Minimum inventory support | An opportunity MUST be backed by at least a policy-declared count of supporting entities. |
| Minimum differentiated inventory | The defining dimension(s) MUST actually differentiate: at least a policy-declared number of entities differing on the dimension. A facet on which nearly all inventory is identical fails. |
| Minimum factual/content coverage | The facts a page of this family would need MUST exist at or above policy-declared coverage. A field existing in a schema is not coverage; values must be present. |
| Duplicate-intent collapse | Opportunities with the same intent class and overlapping target concept SHALL be deterministically collapsed to one before decisioning; the collapsed-away candidates are recorded with reason `DUPLICATE_INTENT`. |
| Combination-depth limit | Dimension combinations are capped; the default depth is **1** (single-dimension pages). Greater depth requires an explicit, recorded operator directive per project. |
| Unsupported evidence states | Gates whose required evidence is `UNKNOWN` or stale evaluate as not-passed for that gate; they MUST NOT be skipped or assumed passed. |
| Prohibited thin combinations | Combinations failing any of the above at any depth are barred from generation entirely, not merely flagged. |

11.3 **Advisory signals** (rank and warn, never create): demand thresholds, SERP differentiation, cannibalization risk against existing/approved opportunities, geographic overlap, evidence staleness. The dividing rule: **inventory- and data-derived facts are hard gates; demand/SERP-derived judgments are signals; creation is always operator-owned.**

11.4 **Decision states.** Every opportunity carries exactly one of: `PROPOSED`, `APPROVED`, `DEFERRED`, `REJECTED` (closed enum; §13 governs transitions).

11.5 **No silent disappearance.** A candidate failing hard gates MUST NOT vanish. It SHALL be emitted in the PageOpportunitySet as `DEFERRED` (failure is remediable — e.g., coverage below threshold) or `REJECTED` (failure is structural — e.g., no differentiation), with machine-readable reason codes. Rejection is a first-class, citable output.

11.6 **No automatic production-page creation.** Under no configuration does any Demand Mapping component create, schedule, or trigger creation of a production page. Structurally guaranteed by §8.1 (no routes) and §21 (no WGE access).

---

## 12. Scoring Policy

12.1 The initial implementation **SHALL NOT** require, define, or compute a composite PageOpportunityScore.

12.2 Phase-1 prioritization SHALL use only: gate state, provenance quality of supporting evidence, inventory support, confidence (integer basis points), and deterministic tie-breaking sort order. This is sufficient for ranked operator review.

12.3 If weighted scoring is later introduced (Phase G, separately authorized): scoring parameters MUST be authority-approved by amendment to this document; versioned as data with a `scoring_version`; integer-based (numerator/denominator or basis points); recorded on every output artifact; and immutable at runtime — **no self-mutating parameters, no learning loops inside scoring, no unversioned hidden heuristics**.

> *Rationale (non-normative):* AES-WEB-002 ADR-03 rejected float-based weighted heuristics for component selection; `services/opportunity_v2` demonstrates the failure mode this section forbids — multiple competing float scorers with runtime-mutated, unversioned parameters.

---

## 13. Human Approval

13.1 Operator approval is **mandatory** before any opportunity may be consumed by IA. Research output never flows downstream un-adjudicated.

13.2 **Binding.** Every operator decision SHALL record: the decision (`APPROVED` / `DEFERRED` / `REJECTED`), reasons, the `PageOpportunitySet` version and content hash decided against, and the `EvidenceSnapshot` hash(es) that set was computed from. (Precedent: PetTripFinder's hash-bound worker-approval contract.)

13.3 **Staleness.** If the opportunity's underlying snapshot or plan version is superseded, the prior approval MUST NOT carry forward automatically. The opportunity returns to `PROPOSED` (flagged as previously-approved-against-stale-evidence) for re-review. Stale approval is detectable by hash mismatch, never by convention.

13.4 **Append-only.** Approval records are append-only (§18). A change of mind is a new record superseding the old, with lineage preserved.

13.5 Research MUST NOT directly create `SiteArchitecture` pages, `PagePlan`s, routes, or any WGE artifact. The only artifact that crosses the boundary — after Phase F's separate AES-WEB amendment — is the approved-opportunity handoff artifact, and IA remains free to decline or reshape any of it under its own authority.

---

## 14. Content Planning Boundary

14.1 Demand Mapping MAY (in Phase F, not earlier) emit a `ContentPlan` / `ContentPlanEntry` artifact derived from APPROVED opportunities, specifying: search intent; questions to answer (from question-demand evidence); required factual inputs (dimension references + minimum coverage); section concepts at a semantic level; evidence requirements; comparison dimensions (for COMPARISON family); FAQ opportunities; internal-link **concepts** (§15).

14.2 It MUST NOT write final prose, draft copy, titles, meta descriptions, or any renderable text. Content authorship remains outside this subsystem (per AES-WEB-001, generation is sealed-cognition-cell territory; the WGE ContentEngine remains a validation airlock). A plan says *what must be answered and with which facts* — never *how the sentence reads*.

14.3 The legacy `content_plan.csv` (launch-kit) is not the contract and SHALL NOT be extended; the ContentPlan artifact supersedes it conceptually. The legacy file is left inert.

---

## 15. Internal Link / Cluster Boundary

15.1 Demand Mapping MAY propose conceptual relationships between opportunities: hub→spoke, topic cluster, geographic cluster, comparison relation, related-intent relation — expressed exclusively as edges between opportunity IDs / concept references.

15.2 It MUST NOT generate route-level `InternalLinkIntent`, link graphs over routes, or anchor text. IA remains the sole authority for the route graph and actual internal-link topology (`SiteArchitecture.internal_link_topology`), including the per-role linking floors/ceilings of AES-WEB-002 §6.2.

15.3 Cluster edges ride on the handoff artifact as advisory input. When a future amended IA materializes approved opportunities, it maps concept edges to route edges under its own rules. ("Employees propose weightings; the graph is computed." — Blueprint.)

---

## 16. Provider Architecture

16.1 **`EvidenceProvider` protocol** (service layer). One protocol: a provider accepts a typed evidence request and returns `EvidenceObservation`s, each fully tagged per §5–§6. Providers are stateless adapters; a new vendor is one new class — "a data faucet, not an architecture change."

16.2 Provider adapters MAY later include: Google Search Console, Google Keyword Planner, Google Trends, DataForSEO, Semrush, Ahrefs, a SERP/search provider, an operator/manual provider, and a static/test provider. This list is illustrative, not normative; **no specific vendor may become architectural authority**, appear in contract names, or shape the observation schema beyond the generic contract.

16.3 **Manual and static providers SHOULD exist before any paid live provider**, and MUST exist before any paid live provider is enabled by default. Operator-supplied evidence is a provider (`OPERATOR` provenance), not a special case.

16.4 Every provider SHALL declare: `provider_id`, `provider_version`, the observation types it can produce, and the provenance state its outputs legitimately carry. A provider MUST NOT emit provenance above its declared ceiling (a deterministic model provider can never emit `VERIFIED`).

16.5 A provider that cannot answer returns nothing or `UNKNOWN`-typed absence — never a synthesized fallback value (§17.6). Silent pseudo-data fallbacks (the pytrends string-length precedent in opportunity_v2) are the named anti-pattern and are prohibited.

---

## 17. Cost / Rate / Failure Governance

17.1 **Per-run budget.** Every research run SHALL carry a budget object: maximum provider calls and, where money is involved, an integer-cent spend ceiling. Budget exhaustion ends collection; it never loosens rules.

17.2 Provider-specific rate limits and retry/backoff (including `Retry-After` honoring) live in each adapter. Retries are bounded; retry exhaustion is a recorded failure, not a loop.

17.3 **Content-addressed caching.** Raw responses are stored content-addressed with TTL policy; within TTL, identical requests are served from cache at zero spend. Re-planning over frozen snapshots costs nothing.

17.4 **Fail-closed.** Any provider failure, quota exhaustion, or budget stop terminates that provider's collection cleanly. Partial evidence already collected is preserved and frozen as-is.

17.5 Evidence not collected — for any reason — is represented as `UNKNOWN` in downstream evaluation. **Never fabricate fallback evidence.**

17.6 Live paid providers sit behind an explicit per-run operator spend gate, disabled by default.

17.7 **Credentials** are read at the service edge (environment/config) and MUST stay outside immutable artifacts, snapshots, raw stores, and logs. Artifacts carry `provider_id`, never keys. The evidence store boundary SHOULD reject credential-shaped content defensively.

---

## 18. Repository / Persistence Model

18.1 **Immutable, content-addressed, append-only:** raw evidence payloads (keyed by content hash), `EvidenceObservation`s, `EvidenceSnapshot`s, `PageOpportunitySet`s and planner run records, operator decision records. None of these is ever edited in place; supersession is a new record with lineage.

18.2 **Mutable state is confined to:** operational indexes/caches over the immutable stores, TTL bookkeeping, and budget ledgers. Mutable state MUST be reconstructible from the immutable record; it is never load-bearing for reproducibility.

18.3 Repositories perform reads and writes only — zero planning, scoring, gating, or provenance logic. Integrity checking (hash verification on read) SHOULD be performed at the repository boundary.

18.4 Storage technology is an implementation choice within Atlas platform norms; the append-only and content-addressing guarantees are the normative requirements, not the backend.

---

## 19. Versioning

19.1 **Independent version axes**, each recorded where relevant on outputs:

| Axis | Bump required when… |
|---|---|
| Contracts/schema version (per artifact kind) | any field/semantic change; additive-optional = minor, breaking = major with declared migration or explicit "rebuild required" |
| Provider version (per adapter) | the adapter's request shape, parsing, or emitted observation semantics change |
| Evidence-model version | observation-type vocabulary or provenance semantics change |
| Planner engine version | any change that could alter output for identical input (replayability contract) |
| Gate-policy version | any threshold, gate set, or reason-code change |
| Scoring-policy version (future, Phase G) | any parameter or formula change |
| Content-plan schema version (Phase F) | as contracts |
| Approval-record schema version | as contracts |

19.2 Duplicate registration of a schema version SHALL fail loudly; schema changes are versioned events, never in-place edits (the WGE registry precedent).

19.3 Every `PageOpportunitySet` records: contracts version, planner version, gate-policy version, evidence-model version, and its input snapshot hashes — sufficient to fully reproduce or fully explain any historical run.

---

## 20. Security / Truth Rules

The following are absolute:

- No fabricated demand, search volume, SERP evidence, or competitors — ever, under any failure mode.
- No inference of `VERIFIED` state: VERIFIED exists only when a real external source returned the specific value, with the raw payload content-addressed and referenced.
- No credential leakage into artifacts, snapshots, raw stores, logs, or error messages.
- No hidden network access from the deterministic engine — enforced structurally by the §3.3 import ban and its AST test, not by convention.
- Raw external evidence is **untrusted input**: parsed defensively at the service boundary, size-bounded, schema-validated before any observation is minted from it; provider text is data, never instructions.
- Estimation models MUST be labeled as such in their rationale fields; a reader of any artifact can always distinguish measurement from modeling.

---

## 21. WGE Boundary

21.1 Initial Demand Mapping phases (A through E, and G/H) **MUST NOT modify**: `engines/website_generation/` (any file), SEOEngine, InformationArchitectureEngine, ContentEngine, ComponentEngine, AssemblyEngine, the WGE ArtifactKind catalog, `PageRole`, recipes, constants, or any WGE test.

21.2 The future IA handoff (Phase F) requires a **separate AES-WEB-001 amendment** — authored under AES-WEB authority, following the ADR-WEB-LISTING-DATASET precedent (new optional input artifact by explicit amendment), operator-approved **before** any implementation touches a WGE file. Any accompanying PageRole or SEO-constants change is likewise AES-WEB amendment territory (§10.3).

21.3 SEOEngine requires no modification for the initial phases; its inputs contain nothing Demand Mapping produces. Any later role-table extension is additive, minor-versioned, and Phase-F-gated.

21.4 Neither subsystem imports the other, ever (§3.7). The boundary is artifact-only, and only post-amendment.

---

## 22. PetTripFinder Validation Fixture

22.1 PetTripFinder / Columbus is the **first acceptance fixture only** — the dataset against which profiling, generation, and gating are validated. It is never a dependency, special case, or vocabulary source for generic code.

22.2 A project-specific adapter MAY exist under `services/demand_research/adapters/` (e.g., mapping the PTF seed CSV and policy-facts store into the generic record form). That adapter directory is the **only** place project or domain names may appear in this subsystem.

22.3 **Domain-neutrality enforcement.** A test SHALL fail the build if project/domain literals (at minimum: the project name, and the fixture's domain nouns) appear anywhere under `engines/demand_mapping/`, case-insensitively, in code or strings. The banned-marker list is data in the test, extensible per fixture (the ADR-PTF-AUTOMATED-BROWSING doctrine-as-data precedent).

22.4 **Portability proof.** The architecture is validated only when the same generic engine, unchanged, can profile and plan over structurally different domains. Acceptance SHALL include, alongside the PTF fixture, at least one synthetic fixture from an unrelated domain (e.g., a martial-arts directory, farm directory, or equivalent) demonstrating: dimensions discovered, opportunities generated, gates applied — with zero generic-engine changes between fixtures.

---

## 23. Phased Delivery Authority

23.1 Implementation proceeds in the phases below. **No phase implicitly authorizes the next**; each ends at a hard stop/review boundary requiring explicit operator instruction to proceed. Universal rules for every phase: full-suite regression must pass; any need to modify an unauthorized file is a stop condition; stop before commit for operator review.

| Phase | Authorized scope | Forbidden scope | Stop/review boundary |
|---|---|---|---|
| **A — Contracts + evidence model** | `engines/demand_mapping/contracts/` (provenance, evidence, dimensions, opportunities, decisions, versions); canonicalization with float rejection; contract tests incl. import audit and domain-neutrality test | Any engine behavior beyond validation/canonicalization; any service/repository/provider code; any existing-file modification; any WGE file | Contracts + tests green; operator reviews full contract surface before anything consumes it |
| **B — Inventory dimension discovery** | `engines/demand_mapping/profiling/`; the generic record form's first consumer; PTF inventory adapter under `services/demand_research/adapters/`; golden-profile tests on PTF + one synthetic unrelated-domain fixture | Opportunity generation, gates, providers, persistence, approval; WGE files | Profiles reproduce the fixture's known dimensions without naming them; portability proof (§22.4) demonstrated |
| **C — Provider abstraction + manual/static evidence + repository** | `services/demand_research/providers/` (protocol + Manual/Static providers only), evidence capture/freezing, budget object; `repositories/demand_research/` (content-addressed store, snapshot registry) | Any live/paid/vendor provider adapter; opportunity generation; approval; WGE files | Evidence can be recorded, frozen, hashed, replayed; $0 external spend to date |
| **D — Opportunity generation + hard gates** | `engines/demand_mapping/opportunities/` and `gates/`; PageOpportunitySet emission with DEFERRED/REJECTED as first-class outputs; dedupe; determinism tests over frozen snapshots; Columbus dry-run | Approval workflow; any handoff artifact; scoring; WGE files | A fixture run yields create-candidates **and** rejections with machine-readable reasons; operator reviews the set |
| **E — Approval workflow** | `services/demand_research/` approval orchestration + decision repository; hash binding; stale-decision detection/re-queue | IA handoff; ContentPlan; WGE files | Operator can adjudicate a real fixture set end-to-end; decisions provably hash-bound |
| **F — WGE handoff + content plan** | **Only after a separate, operator-approved AES-WEB-001 amendment** (§21.2): the approved-opportunity handoff artifact as an optional IA input; ContentPlan artifact (§14); OpportunityFamily→PageRole mapping; any authorized IA/SEO minor versions | Any WGE change not named in the approved amendment; route generation inside Demand Mapping (never authorized) | Amendment approved first; full WGE regression green with and without the new input |
| **G — Scoring (optional)** | Only under a versioned amendment to §12 with authority-approved integer parameters | Self-mutating parameters; unversioned heuristics | Amendment approved before any scoring code |
| **H — Live / Search Console / paid providers + measurement** | Live provider adapters behind §17 spend gates, Search Console first (free, VERIFIED); measurement-driven re-evaluation as ordinary planner runs over fresher snapshots | Ranking-tracker productization; autonomous acting on measurements | Spend-gate review per provider; operator enables each vendor explicitly |

23.2 Phases A–E create new packages and tests only; the first modification of any existing Atlas file is deferred to Phase F behind its own amendment.

---

## 24. Acceptance Principles

The subsystem is acceptable only while all of the following hold:

1. **Domain neutrality** — generic engine code contains no project/domain knowledge; enforced by test, proven by multi-domain fixtures.
2. **Determinism over frozen evidence** — identical snapshots + versions ⇒ identical output hashes, replayable at any time.
3. **Provenance honesty** — every value carries its true epistemic state; ESTIMATED never masquerades; UNKNOWN is preferred over invention.
4. **Rejection and deferral are first-class outputs** — with machine-readable reasons; nothing fails silently.
5. **No route ownership** — no URL/route/slug exists anywhere in the subsystem's contracts.
6. **No autonomous publishing** — no configuration can create a production page.
7. **Operator approval** — mandatory, hash-bound, append-only, staleness-detecting.
8. **Reproducibility** — every historical run fully explainable from recorded versions and hashes.
9. **Budget safety** — external collection cannot run away; failure is closed, partial evidence honest.
10. **Zero WGE impact before Phase F** — bidirectional import isolation; no WGE file touched.
11. **Reusability** — the same subsystem serves any future Atlas product via a new service-layer adapter and nothing else.

---

## 25. Architectural Non-Goals

This architecture is **NOT**:

- an SEO title/meta engine (that is SEOEngine, downstream and unchanged)
- an article or prose generator (content authorship is cognition-cell territory outside this subsystem)
- a ranking tracker (measurement is Phase-H evidence input, and productized tracking is Plane-9/AES-WEB-006 territory)
- a link-building or outreach system
- a crawler (competitor page evidence enters via providers under the same governance as all evidence)
- an autonomous publisher
- a keyword-volume vendor wrapper (vendors are replaceable adapters; the contract is vendor-neutral)
- a PetTripFinder-specific planner (PTF is a fixture behind an adapter wall)
- a replacement for IA (IA remains the single arbiter of what pages exist and where)
- a replacement for the Content plane
- a replacement for SEOEngine

---

## 26. Amendment / Change Process

26.1 AES-SEO-001 governs all Demand Mapping implementation. Where this document is silent, implementation stops and requests clarification; silence is not permission.

26.2 Changes to this document's contracts, provenance semantics, gate determinism, phase authorizations, or boundaries require versioned amendments to this document — proposed explicitly, approved by the operator, applied by version bump, never silently.

26.3 Any change to WGE artifacts, `PageRole` behavior, IA inputs, SEOEngine, or anything else inside `engines/website_generation/` remains under AES-WEB authority and requires an explicit AES-WEB amendment (AES-WEB-001 and/or AES-WEB-002 as applicable). This document cannot authorize such changes and does not attempt to.

26.4 Implementation prompts and sessions cannot alter architecture (Level 4, §0.1). A prompt conflicting with this document is defective; the conflict is recorded and resolved by amendment, not by execution.

26.5 ADRs MAY be filed under this document for narrow clarifications within its territory; each must cite the section it clarifies and cannot contradict a normative rule.

---

## 27. Implementation Readiness — Binding Checklist

Phase A MAY begin only when every item below is affirmatively true:

| # | Gate | Status |
|---|---|---|
| 1 | This authority document is operator-approved at v1.0.0 | ☑ **Approved by operator, 2026-08-09** |
| 2 | Package names approved: `engines/demand_mapping/`, `services/demand_research/`, `repositories/demand_research/` | ☑ Approved (AMB-2) |
| 3 | Provenance model approved: VERIFIED / ESTIMATED / DERIVED / OPERATOR / UNKNOWN, newly defined, no legacy retrofit | ☑ Approved (AMB-3) |
| 4 | Integer-only numeric policy approved for canonical artifacts | ☑ Approved (AMB-4) |
| 5 | Confirmation that Phase A modifies **no** WGE file and **no** existing Atlas file | ☐ Verified at each execution preflight |
| 6 | Baseline regression green: full suite passes, exit 0, no collection errors | ☐ Verified at each execution preflight |
| 7 | Exact Phase A scope defined and bounded (Appendix A) with explicit prohibitions | ☑ Defined below; binding |
| 8 | Stop-before-commit review required and acknowledged: no commit, no push, operator reviews contract surface | ☑ Mandatory per §23.1 |

---

## Appendix A — Phase A Implementation Prompt (Historical Record)

**STATUS: APPROVED PHASE-A IMPLEMENTATION CONTRACT — EXECUTED 2026-08-09.**
This appendix is retained as the historical execution authority for Phase A. The
execution completed under it on 2026-08-09 (17 new files; 109 contract tests; full
suite 10331 passed / 20 skipped, exit 0; zero existing files modified) and **stopped
before commit** per its own stop boundary — the Phase-A result is uncommitted pending
operator commit approval. It is not an authorization to re-execute; re-running Phase A
or beginning any later phase requires explicit operator instruction (§23.1).

```
AES-SEO-001 / PHASE A — DEMAND MAPPING: CONTRACTS + EVIDENCE MODEL

Repository: C:\Atlas\atlas-dashboard        Branch: main
Governing authority: AES-SEO-001 v1.0.0 (must be operator-approved; if it is
not, STOP immediately — §27 item 1).

MANDATORY PREFLIGHT
- Report repo root, branch, HEAD, git status, latest 5 commits.
- Confirm AES-SEO-001 v1.0.0 is operator-approved. STOP if not.
- Confirm baseline regression: python -m pytest tests/ -q → all tests pass,
  exit 0, no collection errors. Record the passing count. STOP on any failure.
- Confirm python -m compileall engines → clean.
- Confirm engines/demand_mapping/, services/demand_research/, and
  repositories/demand_research/ do not already exist. STOP if any exists.

EXACT SCOPE — new files only (AES-SEO-001 §23.1 Phase A)
1. engines/demand_mapping/__init__.py and engines/demand_mapping/contracts/:
   - provenance.py — closed Provenance enum: VERIFIED, ESTIMATED, DERIVED,
     OPERATOR, UNKNOWN (§5.1); the single provenance-priority order (§5.2a);
     TaggedObservation-style value carrier with provider_id, provider_version,
     rationale, confidence_bp: int (absent/None for UNKNOWN), observed_at: str
     (explicit input, never generated — §5.2f).
   - evidence.py — EvidenceObservation (§6.1: observation_id content-derived;
     observation_type from a closed versioned vocabulary; query + query_params;
     market_scope concept; provenance; confidence_bp; integer-typed value;
     raw_ref content hash; derived_from tuple required iff provenance=DERIVED,
     forbidden otherwise — enforce by validator) and EvidenceSnapshot (§6.3:
     content-hash identity over canonical form; observations as sorted tuples).
     Raw response bodies MUST NOT be embeddable (§6.2) — no body field exists.
   - dimensions.py — DimensionKind enum: CATEGORICAL, NUMERIC, BOOLEAN,
     GEOGRAPHIC, ENTITY_REF, TEXT (§7.3); DimensionProfile (§7.4) with
     integer-only statistics (entity_count, coverage_count, missing_count,
     distinct_count, deterministic top-N frequency tuples, integer-scaled
     numeric range, provenance-coverage counts, co-occurrence refs).
   - opportunities.py — IntentClass enum: INFORMATIONAL, COMMERCIAL,
     TRANSACTIONAL, NAVIGATIONAL, LOCAL (§9); OpportunityFamily enum per
     §10.1 (11 members); PageOpportunity per §8.2 — MUST NOT declare any
     url/route/slug field (add a test asserting no field name matches
     url|route|slug|canonical, §8.1); PageOpportunitySet (§8.4);
     GateResult with machine-readable reason codes; DecisionState enum:
     PROPOSED, APPROVED, DEFERRED, REJECTED (§11.4).
   - versions.py — per-artifact schema-version registry with loud duplicate-
     registration failure (§19.2); CONTRACTS_VERSION; evidence-model version.
   - Canonicalization: frozen models via the repository's established
     pydantic v1/v2 compatibility pattern (frozen=True / allow_mutation=False,
     extra="forbid", tuple collections); canonical JSON = UTF-8, sorted keys,
     compact separators; SHA-256 identity; canonicalization REJECTS float
     values with a dedicated error (§4.4).
2. tests/demand_mapping/:
   - Round-trip + hash-stability tests for every contract (construct twice →
     byte-identical canonical JSON, equal SHA-256).
   - Float-rejection tests (a float anywhere in any contract payload raises).
   - Validator tests: derived_from required iff DERIVED; UNKNOWN carries no
     confidence; ESTIMATED can never be constructed as VERIFIED via any merge
     helper shipped in contracts.
   - test_import_audit.py — AST walk over engines/demand_mapping/ forbidding:
     flask, requests, urllib, urllib3, http, httpx, socket, anthropic, openai,
     uuid, random, secrets, time, datetime, logging; and any import of
     repositories, services, routes, or engines.website_generation (§3.3).
   - test_domain_neutrality.py — data-driven banned-marker scan (§22.3): the
     fixture project name and domain nouns appear nowhere under
     engines/demand_mapping/, case-insensitive, code or strings. Marker list
     is test data, extensible.

EXPLICITLY PROHIBITED (STOP CONDITIONS IF NEEDED)
- No profiling, opportunity-generation, gate, provider, service, repository,
  approval, or persistence logic (Phases B+ are NOT authorized by this task).
- No modification of ANY existing file anywhere in the repository. Zero
  changes under engines/website_generation/, services/, repositories/,
  routes/, scripts/, launch_packages/, docs/, tests/ (existing files).
- No network access, no LLM calls, no new dependencies (pydantic stays on
  the v1 baseline per docs/development/environment.md; do NOT install
  pydantic 2.x), no filesystem access inside contracts.
- No float fields; no url/route/slug fields on any contract; no
  clock reads; no environment reads; no randomness; no UUIDs.
- No PageRole import, no WGE ArtifactKind change, no PageRole string mapping
  shipped as code in this phase (§10.3).

FILES LIKELY CREATED
- engines/demand_mapping/__init__.py
- engines/demand_mapping/contracts/{__init__.py, provenance.py, evidence.py,
  dimensions.py, opportunities.py, versions.py}
- tests/demand_mapping/{__init__.py, test_provenance.py, test_evidence.py,
  test_dimensions.py, test_opportunities.py, test_canonicalization.py,
  test_import_audit.py, test_domain_neutrality.py}

ARCHITECTURE RULES (BINDING)
- AES-SEO-001 §3 (layers/imports), §4 (determinism), §5 (provenance),
  §6 (evidence), §8 (opportunity, URL-free), §19 (versioning) govern.
- Contracts-first: this phase ships ZERO behavior beyond validation and
  canonicalization.
- Any ambiguity in a contract field: STOP and record the question for an
  AES-SEO-001 clarification. Do not improvise schema.

TESTS / ACCEPTANCE CRITERIA
- python -m pytest tests/demand_mapping/ -q → all pass.
- python -m pytest tests/ -q → full suite passes, exit 0, no collection
  errors, count ≥ the preflight baseline (proves zero impact on existing code).
- python -m compileall engines/demand_mapping → clean.
- Deterministic-hash demonstration included in test output.

STOP BEFORE COMMIT
- Do NOT commit. Do NOT push. Present for operator review: the file
  inventory, full test results, and the complete contract surface (every
  class, field, enum value). Wait for explicit operator approval before any
  commit is considered.
```

Execution notes of record (2026-08-09): the executed Phase A additionally created
`engines/demand_mapping/contracts/canonical.py` (the single-responsibility home for
the frozen base model, canonicalization, and error types this appendix's scope
requires) and `tests/demand_mapping/test_versions.py` (§19.2 registry coverage);
both fall within the appendix's expressly non-exhaustive "files likely created"
latitude and were reported to the operator in the Phase-A review.

---

AUTHORITY STATUS: APPROVED — ACTIVE AUTHORITY (v1.0.0, operator-approved 2026-08-09)
IMPLEMENTATION STATUS: Phase A executed 2026-08-09, result uncommitted pending operator commit approval. Phases B–H NOT authorized.

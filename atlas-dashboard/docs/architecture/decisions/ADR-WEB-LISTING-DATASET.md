# ADR-WEB-LISTING-DATASET — ListingDataset Input Artifact Contract

| Field | Value |
|---|---|
| Status | Accepted |
| Scope | AES-WEB-001 §4.1 artifact catalog — a new artifact kind (`engines/website_generation/contracts/`) |
| Decided in | AES-WEB-002J.17 (ListingDataset Contract) |
| Supersedes | Nothing |
| Governs | The shape, boundaries, and ownership of listing data as it enters the Website Generation Engine |

## Context

The AES-WEB-002J.16 value-binding preflight found that the real
`ComponentEngine`/`Renderer` chain cannot bind `LISTING_REF` props or any
listing-shaped content (names, ratings, hours, contact, sponsorship state)
because **no listing data model exists anywhere in the Website Generation
Engine** — only the `ListingKind` enum (§6.3), which describes a listing's
*commercial kind*, never its identity or facts. The twelve AES-WEB-001 §4.1
artifacts carry no listing corpus, and the Component Engine's own docstring
already records value-layer binding (including `LISTING_REF`) as deferred
for exactly this reason.

AES-WEB-002 names a **future authority for this domain directly**: "AES-WEB-005
— Directory Data Operations Authority. Listing data sourcing, freshness,
verification methodology, correction workflow backend — the operational
truth behind §6.3's `ListingKind` states." That document does not exist yet.
This ADR must therefore define an artifact that supplies the Website
Generation Engine's listing-data *input* without pre-empting AES-WEB-005's
future operational authority, and without coupling the Website Generation
Engine's independent contract layer (§3.1's import matrix) to the legacy
`engines/directory_builder`/`engines/directory_ingestion` models that
already model a similar (but persistence-shaped, float-bearing) domain.

## Decision

Add a thirteenth `ArtifactKind`, **`ListingDataset`** (schema 1.0.0), to
`contracts/artifacts.py`, registered in `contracts/versions.py` alongside the
existing twelve. It is a frozen, canonically-serialized, content-addressed
**input** artifact: a normalized corpus of listings plus their categories
and locations, in the same doctrine as every other WGE artifact (immutable,
`extra="forbid"`, tuples not sets, deterministic, no floats).

### Normative rules

1. **`ListingDataset` is WGE input state, not the operational data
   authority.** It stores the deterministic facts a build consumes
   (identity, category/location membership, contact, rating, hours,
   sponsorship, verification *status*). It never computes, infers, or
   fabricates any of these values.
2. **AES-WEB-005 (when written) owns the operations behind this data**:
   sourcing methodology, freshness/refresh policy, verification
   *methodology*, and the correction workflow. `ListingDataset` records only
   the *output state* of those processes (e.g. `verification.status`,
   `verification.verified_at` as a supplied string) — it carries no sourcing
   logic, no freshness computation, no correction workflow, and no billing
   or payment state.
3. **No legacy coupling.** `contracts/` may import only stdlib, pydantic,
   and other `contracts/` modules (§3.1's import matrix, unchanged by this
   ADR). `ListingDataset` and its nested models do not import
   `engines/directory_builder`, `engines/directory_ingestion`, or any other
   engine package. Any future mapping from those legacy/external models into
   `ListingDataset` is a **service-layer adapter**, outside this contract,
   and outside this delivery's scope.
4. **Immutable, deterministic, content-addressed.** Built on the same
   `FrozenModel` / `canonical_json` / `artifact_sha256` machinery every
   other artifact uses. No new hashing algorithm.
5. **No floats anywhere.** Per §4.3's existing float prohibition (enforced
   today by `_canonicalize` raising `ArtifactCanonicalizationError`),
   ratings and coordinates are integer-encoded: `rating_hundredths` (the
   `ContrastEvidence.contrast_ratio_hundredths` precedent) and
   `lat_micro`/`long_micro` (micro-degree integers).
6. **Routes are not stored.** `ListingDataset` stores `slug` plus
   `category_id`/`location_id` references; deriving a canonical route from
   those references is IA/Component-binding policy, decided later
   (AES-WEB-002J.18/J.19), never duplicated here. Storing a
   `canonical_route` field would create two competing sources of route
   truth.
7. **Stays structured until Component Engine Phase B projects it into
   content.** Every field is typed, not opaque text. The Renderer never
   consumes `ListingDataset` directly and gains no new input — a future
   Component Engine binding phase (§5.5; not part of this delivery) is the
   only place structured listing facts become `(route, slot_id)`-keyed
   `ContentBlock` text, preserving the Renderer's existing purity contract
   (AES-WEB-001 §5.7: "never invents content").
8. **Empty datasets are valid.** `listings=()`, `categories=()`,
   `locations=()` is a legal `ListingDataset` — this artifact makes no
   claim about whether any listing exists.
9. **No build-time timestamps.** No field is populated from the wall clock
   during construction or validation. Externally supplied timestamps
   (`ListingProvenance.observed_at`, `ListingVerification.verified_at`) may
   be *preserved* because they are input data, not generated.
10. **No unrestricted dictionaries.** Every nested structure is a typed
    `FrozenModel`; there is no `Dict[str, Any]` anywhere in the artifact.
11. **No repository, service, network, or AI dependency.** `ListingDataset`
    and its validator are pure contract-layer code — no I/O, no imports
    outside stdlib/pydantic/intra-contracts.

### Field scope (§27.5 catalog-driven, not directory-convention-driven)

The record shape is deliberately the smallest set the **current 72-component
catalog's emitters actually consume** (AES-WEB-002J.17 preflight §3, §7–§10):
identity, one category, zero-or-one location, description, `listing_kind`,
optional contact/address/geo/rating/hours/sponsorship/verification/
credentials/assets/CTA/provenance. Amenities, price level, booking models,
claim/ownership state, and raw review corpora are *not* added — no current
component or emitter reads them, and adding them would be undocumented
"directories commonly have X" speculation, which AES-WEB-001's determinism
and no-invented-metadata doctrine (§1.1, §5.5) forbids.

## Explicit non-goals (deferred, unchanged by this ADR)

Component Engine binding (`LISTING_REF` resolution, Phase B projection into
`ContentBlock`s — AES-WEB-002J.19); Renderer/emitter changes to render
structured fields distinctly (cards still show one text heading; hours
still render as one schedule cell; images still carry `alt=""` — carried
gaps, unchanged); a listing/gallery `AssetPackage` artifact (asset
references stay optional and unresolved without one); IA/Content
slot-vocabulary expansion and the component-slot → content-source mapping
contract (AES-WEB-002J.18); the AES-WEB-005 sourcing/freshness/verification-
methodology/correction-workflow authority itself; producer adapters,
ingestion wiring, and pipeline wiring (all out of scope — this is a
contract-only sprint).

## Consequences

`contracts/enums.py` gains `ArtifactKind.LISTING_DATASET`,
`VerificationStatus`, and `Weekday`. `contracts/artifacts.py` gains
`ListingDataset` and its thirteen nested models. `contracts/versions.py`
registers `(LISTING_DATASET, "1.0.0")`. No existing artifact schema,
engine version, pipeline stage, or component lifecycle status changes. The
Component Engine, Renderer, Assembly Engine, Quality Gate Engine, Site
Bundle Repository, pipeline, services, and routes are all unmodified by
this delivery — this ADR authorizes only the contract, not its consumption.

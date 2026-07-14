# ADR-WEB-CONTENT-BINDING-MAP — Semantic Content-Slot Vocabulary and Component Binding Map

| Field | Value |
|---|---|
| Status | Accepted |
| Scope | AES-WEB-001 §5.4/§5.5 — the declarative source map the future Component Engine Phase-B binder consumes (`engines/website_generation/constants/`, `engines/website_generation/components/`) |
| Decided in | AES-WEB-002J.18 (IA/Content Slot Vocabulary and Component Binding Map) |
| Supersedes | Nothing |
| Governs | Which semantic content slots exist, which source artifact/derivation owns each, and how each component's declared content slots and reference props map to those sources |

## Context

The AES-WEB-002J.16 value-binding preflight established that the real
`ComponentEngine → Renderer` chain fails because the Component Engine leaves
required content slots and value-layer props unbound, and — critically —
**no authority-defined mapping exists between a component's declared slot/prop
names and a source of truth**. AES-WEB-001 §5.5 assigns *binding* to the
Component Engine ("an unbound required prop is a compile error here"), and
gates CG-CON-003/CG-CON-005 name the Component Engine (CE) as the remediation
owner, but neither §5.5 nor §26's recipes say *what fills* a slot named
`h1`, `category_tiles`, `nav_tree`, or `listing_ref`.

AES-WEB-002J.17 added the `ListingDataset` artifact (structured listing input
data). AES-WEB-002J.18 (this delivery) supplies the remaining missing piece:
the **declarative source map** that tells a future Phase-B binder, for every
required component field, which artifact field or deterministic derivation
owns it. This is a contract/declaration sprint only — it implements no
binding, mutates no engine, and changes no artifact schema.

Two structural constraints shape the design (both from J.16/J.18 preflights):

1. **`ContentBlock` is flat `(page_route, slot_id, text)`.** Several §8.4
   block types a component may declare (`LinkSpec`, `HoursSpec`,
   `RatingSummary`, `ContactSpec`, `GeoSpec`, `QAPair`, `ReviewBlock`,
   `ComparisonTableBlock`, `PriceSpec`, `AssetRef`) carry structure a single
   text string cannot honestly represent.
2. **Emitters render a `LinkSpec`'s text as both the `href` and the visible
   label** (`_link_items`), so real navigation/tile *labels* distinct from
   their hrefs are impossible without a `ContentBlock` evolution *and* an
   emitter change — both out of this sprint's scope.

## Decision

Introduce a two-part declarative layer, plus a validator:

* **`constants/content_slots.py`** — the canonical **semantic slot
  vocabulary**: one frozen entry per semantic slot recording its source
  owner, source/derivation key, expected block type, scope, cardinality,
  `flat_ok`, `structured_deferred`, and availability. `constants/` may import
  only stdlib (§3.2 import matrix), so its enums are plain `enum.Enum`
  classes, not the `contracts/` enums.
* **`components/binding_rules.py`** — the **component-field → semantic-slot
  map**: one frozen rule per (component_id, field_kind, field_name) recording
  the semantic slot it aliases to, the source rule, required/optional state,
  expected block type or `PropType`, scope, and a `BindingState`
  (`FULLY_BINDABLE` / `FLAT_PROJECTION_ONLY` / `STRUCTURED_DEFERRED` /
  `SOURCE_UNAVAILABLE`).
* **`components/binding_map_validator.py`** — a deterministic, batch-reporting
  validator that checks the map against the live component registry.

### Normative rules

1. **Binding is owned by the Component Engine (§5.5).** J.18 defines only the
   declarative source map; it performs no binding.
2. **The map is not an artifact.** It is engine-adjacent declarative data —
   no `ArtifactKind`, no schema, no `source_hashes`.
3. **The map is deterministic and complete.** Every required component
   content slot, every required `CONTENT_BLOCK_REF` prop, and every required
   `LISTING_REF` prop across all 72 components is mapped; iteration order is
   canonical.
4. **Component slot/prop names are unchanged.** The frozen `ComponentDefinition`
   contracts are not touched; the map *references* their existing field names.
5. **Semantic slot names are the canonical source vocabulary**; component
   field names map explicitly to them (e.g. component slot `h1` → semantic
   `page_h1`; component prop `nav_tree` → semantic `primary_navigation`).
6. **No hidden string conventions, no fuzzy matching, no AI matching.** Every
   alias is an explicit table entry.
7. **No placeholder source values.** A field with no real source is marked
   `SOURCE_UNAVAILABLE`, never mapped to a fabricated or `"Resolved …"` value.
8. **The Content Engine remains a validation airlock** (§5.4). It validates
   editorial `ContentCandidate` text; it does not read `ListingDataset` or
   synthesize derived blocks.
9. **`ListingDataset` remains structured input data**; the future Phase-B
   binder (not this sprint) projects selected listing fields into
   `ContentBlock`s.
10. **The Renderer remains pure** and resolves no source artifacts; it is
    unchanged.
11. **Structured content that flat `ContentBlock.text` cannot honestly carry
    is marked `structured_deferred`** and classified `STRUCTURED_DEFERRED`;
    it is accounted for but never reported as fully bindable.
12. **No raw-route labels may be claimed as real navigation labels.**
    `primary_navigation`/`footer_navigation`/tile slots are
    `STRUCTURED_DEFERRED` for their label+href structure; a future
    emitter/`ContentBlock` sprint owns real labels.
13. **A narrow flat projection is allowed only where it stays honest**
    (`FLAT_PROJECTION_ONLY`): e.g. `listing_rating` → one formatted string,
    `listing_contact` → one NAP string, `listing_hours` → one schedule
    string, `result_summary` → a deterministic count string. Such a rule
    never claims the underlying structured type is fully supported.
14. **No new artifact, no schema change, no engine-version change** occurs in
    J.18.
15. **Validation is deterministic and batch-reported** (reusing the existing
    `ArtifactValidationError`; no new engine error) and never silently
    repairs or falls back to a placeholder.

### The four binding states

| State | Meaning |
|---|---|
| `FULLY_BINDABLE` | A real source exists and flat `ContentBlock.text` (or a literal prop value) represents it honestly and completely (RichText copy, disclosures, route/enum/int/bool/token/asset/a11y literals). |
| `FLAT_PROJECTION_ONLY` | A real source exists; the binder may emit one honest flat string, but the underlying block type is structured and richer rendering is deferred. |
| `STRUCTURED_DEFERRED` | A real source may exist, but flat text cannot represent the block type honestly (links with labels, per-day hours, galleries); binding waits for a `ContentBlock`/emitter sprint. |
| `SOURCE_UNAVAILABLE` | No producing artifact exists yet (e.g. facet/sort/pagination content, gallery media). |

## Explicit non-goals (deferred, unchanged by this ADR)

Component Engine Phase-B binding itself; any `ContentBlock`/`ContentPackage`
schema evolution to carry structured payloads; emitter changes to render
label+href navigation, per-day hours, tel:/mailto: links, gallery media, or
nested form fields; a listing/gallery `AssetPackage` artifact; expanding the
Component Engine's input signature (a J.19 decision); and the AES-WEB-005
directory-data operations authority.

## Consequences

Three new declarative modules (`constants/content_slots.py`,
`components/binding_rules.py`, `components/binding_map_validator.py`) plus
additive expansions of `constants/ia.py` (per-role semantic content
requirements) and `constants/content.py` (editorial slot vocabulary/length
policy for the new text slots). No artifact schema, engine version, pipeline
stage, Renderer/emitter, or component lifecycle status changes. The map is
validated against the live registry by an architecture test, so it cannot
silently drift from the catalog. J.19 (Component Engine Phase B) consumes
this map to bind real values.

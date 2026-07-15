"""Schema-version and engine-version registries (AES-WEB-001 §4.6).

Two independent version axes, both recorded in every ``BuildManifest``:

* **Schema versions** — semver per artifact kind. The registry maps
  ``(artifact_kind, schema_version) → model class``.
* **Engine versions** — semver per engine class, bumped whenever output
  could differ for identical input (the replayability contract).

Phase 1 registered all twelve artifact kinds at v1.0.0. Amendment A1
(AES-WEB-001 v1.1.0; AES-WEB-002 §14.3, ADR-14) adds the additive-minor
``ComponentManifest`` schema 1.1.0 (optional ``selection_trace``): the
current version is 1.1.0, and both 1.0.0 (the field-less
:class:`ComponentManifestV1`) and 1.1.0 stay registered so pre-amendment
manifests remain replayable. No migration is required (additive optional
field — old readers still parse).

AES-WEB-002J.2 (AES-WEB-001 §5.2 / Part 2 / Part 13 Phase 2) adds the
analogous additive-minor ``BrandPackage`` schema 1.1.0 (``radius_scale``,
``extended_tokens``, ``contrast_evidence``): both 1.0.0 (the field-less
:class:`BrandPackageV1`) and 1.1.0 stay registered, again with no migration.

AES-WEB-002J.3 (AES-WEB-001 §5.3 / Part 2 / Part 13 Phase 2) adds the
analogous additive-minor ``SiteArchitecture`` schema 1.1.0 (``page_ids``,
``page_hierarchy``, ``internal_link_topology``): both 1.0.0 (the
field-less :class:`SiteArchitectureV1`) and 1.1.0 stay registered, again
with no migration. The Information Architecture Engine is not wired into
pipeline execution.

AES-WEB-002J.4 (AES-WEB-001 §5.4 / Part 2) adds the ``content_engine``
entry to ``ENGINE_VERSIONS`` at 1.0.0. ``ContentCandidate`` and
``ContentPackage`` are unchanged -- both stay at schema 1.0.0, the shape
registered since Phase 1 -- so no new schema registration is added here.
The Content Engine is not wired into pipeline execution; ``content_drafting``
and ``content_validation`` both remain ``NOT_EXECUTED``.

AES-WEB-002J.5 (AES-WEB-001 §5.8 / Part 2) adds the ``seo_engine`` entry to
``ENGINE_VERSIONS`` at 1.0.0. ``SEOPackage`` is unchanged -- it stays at
schema 1.0.0, the shape registered since Phase 1 -- so no new schema
registration is added here. The SEO Engine is not wired into pipeline
execution; ``seo_compilation`` remains ``NOT_EXECUTED``.

AES-WEB-002J.7 (AES-WEB-001 §5.6 / Part 2) adds the analogous
additive-minor ``LayoutPlan`` schema 1.1.0 (``region_details``): both 1.0.0
(the field-less :class:`LayoutPlanV1`) and 1.1.0 stay registered, again
with no migration. Adds the ``layout_engine`` entry to ``ENGINE_VERSIONS``
at 1.0.0. The Layout Engine is not wired into pipeline execution;
``layout_composition`` remains ``NOT_EXECUTED``.

AES-WEB-002J.8 (AES-WEB-001 §5.7 / Part 2) adds the analogous
additive-minor ``RenderedPageSet`` schema 1.1.0 (``page_details``,
``shared_css``): both 1.0.0 (the hash-only :class:`RenderedPageSetV1`) and
1.1.0 stay registered, again with no migration. Adds the ``renderer`` entry
to ``ENGINE_VERSIONS`` at 1.0.0. The Renderer is not wired into pipeline
execution; ``rendering`` remains ``NOT_EXECUTED``.

AES-WEB-002J.10 (AES-WEB-001 §5.9 / Part 2) adds the analogous
additive-minor ``SiteBundle`` schema 1.1.0 (``files``): both 1.0.0 (the
hash-only :class:`SiteBundleV1`) and 1.1.0 stay registered, again with no
migration. Adds the ``assembly`` entry to ``ENGINE_VERSIONS`` at 1.0.0. The
Assembly Engine is not wired into pipeline execution; ``assembly`` remains
``NOT_EXECUTED``.

AES-WEB-002J.11 (AES-WEB-001 §5.10 / Part 2) adds the analogous
additive-minor ``QualityReport`` schema 1.1.0 (``deferred_gate_ids``): both
1.0.0 (the field-less :class:`QualityReportV1`) and 1.1.0 stay registered,
again with no migration. Adds the ``quality_gate_engine`` entry to
``ENGINE_VERSIONS`` at 1.0.0. The Quality Gate Engine is not wired into
pipeline execution; ``gating`` remains ``NOT_EXECUTED``.

AES-WEB-002J.17 (ADR-WEB-LISTING-DATASET) adds ``ArtifactKind.LISTING_DATASET``
as the additive thirteenth artifact kind, registered directly at schema
1.0.0 (there is no prior shape to be additive over -- unlike every other
entry above, this is a brand-new artifact, not a schema bump of an existing
one). Contract-only: no engine consumes ``ListingDataset`` yet, so no
``ENGINE_VERSIONS`` entry is added or changed by this delivery.
"""

from __future__ import annotations

from typing import Dict, Tuple, Type

from engines.website_generation.contracts.artifacts import (
    ArtifactHeader,
    BrandPackage,
    BrandPackageV1,
    BuildManifest,
    BusinessSpec,
    ComponentManifest,
    ComponentManifestV1,
    ContentCandidate,
    ContentPackage,
    LayoutPlan,
    LayoutPlanV1,
    ListingDataset,
    QualityReport,
    QualityReportV1,
    RenderedPageSet,
    RenderedPageSetV1,
    SEOPackage,
    SiteArchitecture,
    SiteArchitectureV1,
    SiteBundle,
    SiteBundleV1,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import (
    SchemaRegistrationError,
    UnsupportedSchemaVersionError,
)

# Current schema version per artifact kind (AES-WEB-001 v1.0.0 catalog).
SCHEMA_VERSIONS: Dict[ArtifactKind, str] = {
    ArtifactKind.BUSINESS_SPEC: "1.0.0",
    # AES-WEB-002J.2: additive-minor bump to 1.1.0 (radius_scale,
    # extended_tokens, contrast_evidence).
    ArtifactKind.BRAND_PACKAGE: "1.1.0",
    # AES-WEB-002J.3: additive-minor bump to 1.1.0 (page_ids,
    # page_hierarchy, internal_link_topology).
    ArtifactKind.SITE_ARCHITECTURE: "1.1.0",
    ArtifactKind.CONTENT_CANDIDATE: "1.0.0",
    ArtifactKind.CONTENT_PACKAGE: "1.0.0",
    # Amendment A1: additive-minor bump to 1.1.0 (optional selection_trace).
    ArtifactKind.COMPONENT_MANIFEST: "1.1.0",
    # AES-WEB-002J.7: additive-minor bump to 1.1.0 (region_details).
    ArtifactKind.LAYOUT_PLAN: "1.1.0",
    # AES-WEB-002J.8: additive-minor bump to 1.1.0 (page_details, shared_css).
    ArtifactKind.RENDERED_PAGE_SET: "1.1.0",
    ArtifactKind.SEO_PACKAGE: "1.0.0",
    # AES-WEB-002J.10: additive-minor bump to 1.1.0 (files).
    ArtifactKind.SITE_BUNDLE: "1.1.0",
    # AES-WEB-002J.11: additive-minor bump to 1.1.0 (deferred_gate_ids).
    ArtifactKind.QUALITY_REPORT: "1.1.0",
    ArtifactKind.BUILD_MANIFEST: "1.0.0",
    # AES-WEB-002J.17 (ADR-WEB-LISTING-DATASET): the additive thirteenth
    # artifact kind, introduced directly at schema 1.0.0 (no prior shape to
    # be additive over).
    ArtifactKind.LISTING_DATASET: "1.0.0",
}

# Engine versions — Phase 1 engines only. Later phases append; they never
# rewrite existing entries in place (bump-by-version doctrine).
ENGINE_VERSIONS: Dict[str, str] = {
    "business_spec_compiler": "1.0.0",
    "state_machine": "1.0.0",
    "website_generation_pipeline": "1.0.0",
    # AES-WEB-002J.2 (AES-WEB-001 §5.2/Part 2/Part 13 Phase 2): initial
    # Brand Engine version. Not wired into pipeline execution (§6:
    # brand_resolution remains NOT_EXECUTED in the BuildManifest).
    # AES-WEB-002K.2 bumps 1.0.0 -> 1.1.0: three additive type-scale roles
    # (heading.hero, body.large, wordmark) and one additive spacing role
    # (section.xsmall) per family/shared scale -- resolve() now returns a
    # BrandPackage with more populated type_scale/spacing_scale entries for
    # the identical BusinessSpec input, a real §5.2 output change. (A fourth
    # candidate role, "eyebrow", was authored then removed before this
    # merge -- no visual_styles.py rule or catalog dependency ended up
    # consuming it, since no page-role/emitter has a real, non-fabricated
    # eyebrow-copy source; adding an unused token would fail the brand
    # token-coverage suite's "no accidental drift" invariant honestly.)
    "brand_engine": "1.1.0",
    # AES-WEB-002J.3 (AES-WEB-001 §5.3/Part 2/Part 13 Phase 2): initial
    # Information Architecture Engine version. Not wired into pipeline
    # execution (§6: ia_planning remains NOT_EXECUTED in the BuildManifest).
    # AES-WEB-002K.1 bumps 1.0.0 -> 1.1.0: plan() now accepts an optional
    # listing_dataset input, emitting one business-profile PagePlan per
    # ListingRecord plus real page titles (previously always "") -- a §5.3
    # behavior change requiring an explicit bump. Omitting listing_dataset
    # is not byte-identical to pre-K.1 output either, since titles are now
    # always populated -- see the K.1 implementation report §15.
    # PILOT-PTF-1 bumps 1.1.0 -> 1.2.0: plan() now accepts an optional
    # editorial_pages input, emitting one real PageRole.EDITORIAL_GUIDE page
    # per (route, title) pair -- a §5.3 behavior change requiring an
    # explicit bump. Omitting editorial_pages (the default, ()) is
    # byte-identical to pre-PTF-1 output.
    "information_architecture_engine": "1.2.0",
    # AES-WEB-002J.4 (AES-WEB-001 §5.4/Part 2): initial Content Engine
    # version. Not wired into pipeline execution (§6: content_drafting and
    # content_validation both remain NOT_EXECUTED in the BuildManifest).
    "content_engine": "1.0.0",
    # AES-WEB-002J.5 (AES-WEB-001 §5.8/Part 2): initial SEO Engine version.
    # Not wired into pipeline execution (§6: seo_compilation remains
    # NOT_EXECUTED in the BuildManifest).
    # AES-WEB-002K.1 bumps 1.0.0 -> 1.1.0: compile() now accepts an optional
    # base_url input; empty (default) preserves the exact pre-K.1
    # self-canonical (route-relative) output byte-for-byte, but the method
    # signature itself changed and a supplied base_url is a real §5.8
    # behavior change, so the bump is explicit rather than silent.
    "seo_engine": "1.1.0",
    # AES-WEB-002J.6 (AES-WEB-001 §5.5/Part 2; AES-WEB-002 §14/§26): initial
    # Component Engine version. Not wired into pipeline execution (§6:
    # component_resolution remains NOT_EXECUTED in the BuildManifest).
    # AES-WEB-002J.19 (ADR-WEB-CONTENT-BINDING-MAP) bumps 1.0.0 -> 1.1.0: the
    # Component Engine now performs Phase-B value binding (bindability-aware
    # selection plus real prop/content binding via the J.18 map), a §5.5
    # behavior change requiring an explicit engine-version bump -- output can
    # now differ for an identical (SiteArchitecture, ContentPackage) pair
    # depending on the additive listing_dataset/brand_package inputs.
    # AES-WEB-002J.20 (ADR-WEB-CONTENT-BINDING-MAP) bumps 1.1.0 -> 1.2.0: the
    # Component Engine now expands a recipe slot into N concrete instances
    # (one per matching ListingRecord, per components/composition_rules.py)
    # between Phase A selection and Phase B binding, and LISTING_DATASET-
    # sourced ref-prop projections use listing-aware generated slot ids
    # (bind.<semantic_slot>.<listing_id>) instead of the J.19 positional
    # form -- both are §5.5 behavior changes requiring an explicit bump.
    # AES-WEB-002K.1 (ADR-WEB-CONTENT-BINDING-MAP) bumps 1.2.0 -> 1.3.0: the
    # Component Engine now additionally produces a RenderDataBundle
    # (contracts/render_data.py) in Phase B -- real nav/footer links,
    # enriched listing-card/contact/hours data -- and two required fields
    # (nav.header.standard/legal.footer.directory's nav_tree) move from
    # categorically-unbindable STRUCTURED_DEFERRED to the new RENDER_DATA
    # binding state, changing which components Phase A can select.
    # PILOT-PTF-1 bumps 1.3.0 -> 1.4.0: directory.categories.grid's
    # category_tiles/category_source_ref fields move from
    # STRUCTURED_DEFERRED to RENDER_DATA (a real tile-link producer now
    # exists), the CONTENT_SLOT binding loop gained a RENDER_DATA branch
    # (previously PROP-only), and an optional recipe slot whose selected
    # instance cannot bind its data is now honestly omitted instead of
    # batch-failing the whole compile -- three §5.5 behavior changes.
    "component_engine": "1.4.0",
    # AES-WEB-002J.7 (AES-WEB-001 §5.6/Part 2): initial Layout Engine
    # version. Not wired into pipeline execution (§6: layout_composition
    # remains NOT_EXECUTED in the BuildManifest).
    "layout_engine": "1.0.0",
    # AES-WEB-002J.8 (AES-WEB-001 §5.7/Part 2): initial Renderer version.
    # Not wired into pipeline execution (§6: rendering remains NOT_EXECUTED
    # in the BuildManifest). AES-WEB-002J.15 (AES-WEB-001 §8.3;
    # ADR-WEB-VISUAL-TOKEN-APPLICATION) bumps 1.0.0 -> 1.1.0: the Renderer now
    # emits an applied token-driven visual CSS layer (new shared_css output),
    # a §11.4 snapshot-level change requiring an explicit engine-version bump.
    # Additive and backward-compatible -- every component's compatibility
    # range is renderer >=1.0.0,<2.0.0.
    # AES-WEB-002K.1 bumps 1.1.0 -> 1.2.0: render() now accepts an optional
    # RenderDataBundle, threaded per-instance into LayoutContext so
    # render-data-aware emitters (nav/footer/cards/contact/hours) can emit
    # real hyperlinks; a required render-data-backed prop's generated key
    # is now recognized and excluded from the ContentPackage-lookup
    # missing-content check -- a §5.7 behavior change requiring an explicit
    # bump. Omitting render_data (None) is byte-identical to pre-K.1 output.
    # AES-WEB-002K.2 bumps 1.2.0 -> 1.3.0: link_html() now accepts an
    # optional css_class, applied at the listing-card CTA and profile
    # website-link call sites (a real markup change -- those anchors now
    # carry a class attribute they did not before), and
    # hero.search.directory's emitter gained a real, static, in-page CTA
    # anchor to #main -- both §5.7 markup-level behavior changes requiring
    # an explicit bump, mirroring the J.15 "snapshot-level change" precedent.
    "renderer": "1.3.0",
    # AES-WEB-002J.10 (AES-WEB-001 §5.9/Part 2): initial Assembly Engine
    # version. Not wired into pipeline execution (§6: assembly remains
    # NOT_EXECUTED in the BuildManifest).
    "assembly": "1.0.0",
    # AES-WEB-002J.11 (AES-WEB-001 §5.10/Part 2): initial Quality Gate Engine
    # version. Not wired into pipeline execution (§6: gating remains
    # NOT_EXECUTED in the BuildManifest).
    "quality_gate_engine": "1.0.0",
}

# Component-system version axes (AES-WEB-002 §22.1; AES-WEB-002A). Additive
# to the two AES-WEB-001 axes above; recorded in the BuildManifest when the
# component system is in play. The ``contracts/`` layer owns versions and
# may not import ``constants/``, so the literals live here.
# AES-WEB-002E: registry-minor bump (§22.2; Index CL-1 "registry additions
# are registry-minor") for the eleven Wave-4 components added to
# REGISTERED_COMPONENTS alongside the amendment-A4 provisional
# listing.card.standard.
# AES-WEB-002F: registry-minor bump for the thirteen Wave 5 components
# (§27.6) added to REGISTERED_COMPONENTS.
# AES-WEB-002G: registry-minor bump for the seven Wave 6 components (§27.7)
# added to REGISTERED_COMPONENTS.
# AES-WEB-002H: registry-minor bump for the eight Wave 7 components (§27.8)
# added to REGISTERED_COMPONENTS, closing the 72-component MVP catalog.
COMPONENT_CONTRACT_SCHEMA_VERSION: str = "1.0.0"
REGISTRY_VERSION: str = "1.4.0"
# Version of the registry-fingerprint algorithm (SHA-256 over the canonical
# serialization of registered definitions in lexicographic component_id
# order).
REGISTRY_FINGERPRINT_VERSION: str = "1.0.0"

COMPONENT_SYSTEM_VERSIONS: Dict[str, str] = {
    "component_contract_schema": COMPONENT_CONTRACT_SCHEMA_VERSION,
    "registry": REGISTRY_VERSION,
    "registry_fingerprint": REGISTRY_FINGERPRINT_VERSION,
}


_MODEL_REGISTRY: Dict[Tuple[ArtifactKind, str], Type[ArtifactHeader]] = {}


def register_artifact_model(
    kind: ArtifactKind, schema_version: str, model_cls: Type[ArtifactHeader]
) -> None:
    """Register the model class for ``(kind, schema_version)``.

    Duplicate registration is a :class:`SchemaRegistrationError` — schema
    changes are versioned events, never in-place edits (§4.6).
    """
    key = (ArtifactKind(kind), str(schema_version))
    existing = _MODEL_REGISTRY.get(key)
    if existing is not None and existing is not model_cls:
        raise SchemaRegistrationError(
            "duplicate schema registration for %s %s"
            % (key[0].value, key[1]),
            stage="schema_registry",
            diagnostics={"artifact_kind": key[0].value, "schema_version": key[1]},
        )
    if not issubclass(model_cls, ArtifactHeader):
        raise SchemaRegistrationError(
            "artifact models must derive from ArtifactHeader",
            stage="schema_registry",
            diagnostics={"artifact_kind": key[0].value, "schema_version": key[1]},
        )
    _MODEL_REGISTRY[key] = model_cls


def registered_artifact_model(
    kind: ArtifactKind, schema_version: str
) -> Type[ArtifactHeader]:
    """Look up the registered model class for ``(kind, schema_version)``."""
    key = (ArtifactKind(kind), str(schema_version))
    model_cls = _MODEL_REGISTRY.get(key)
    if model_cls is None:
        raise UnsupportedSchemaVersionError(
            "no registered model for %s schema %s" % (key[0].value, key[1]),
            stage="schema_registry",
            diagnostics={"artifact_kind": key[0].value, "schema_version": key[1]},
        )
    return model_cls


def registered_schema_versions() -> Dict[ArtifactKind, Tuple[str, ...]]:
    """All registered schema versions per kind, stable-sorted."""
    out: Dict[ArtifactKind, Tuple[str, ...]] = {}
    for kind, version in sorted(
        _MODEL_REGISTRY, key=lambda k: (k[0].value, k[1])
    ):
        out.setdefault(kind, ())
        out[kind] = out[kind] + (version,)
    return out


# ---------------------------------------------------------------------------
# Catalog registration (executed once at import)
# ---------------------------------------------------------------------------

# The v1.0.0 baseline: every artifact kind at schema 1.0.0. For
# ComponentManifest the 1.0.0 shape is the field-less ComponentManifestV1,
# so pre-amendment manifests remain byte-identical and replayable. Likewise
# for BrandPackage: the 1.0.0 shape is the field-less BrandPackageV1
# (AES-WEB-002J.2).
_V1_0_0_CATALOG: Dict[ArtifactKind, Type[ArtifactHeader]] = {
    ArtifactKind.BUSINESS_SPEC: BusinessSpec,
    ArtifactKind.BRAND_PACKAGE: BrandPackageV1,
    ArtifactKind.SITE_ARCHITECTURE: SiteArchitectureV1,
    ArtifactKind.CONTENT_CANDIDATE: ContentCandidate,
    ArtifactKind.CONTENT_PACKAGE: ContentPackage,
    ArtifactKind.COMPONENT_MANIFEST: ComponentManifestV1,
    ArtifactKind.LAYOUT_PLAN: LayoutPlanV1,
    ArtifactKind.RENDERED_PAGE_SET: RenderedPageSetV1,
    ArtifactKind.SEO_PACKAGE: SEOPackage,
    ArtifactKind.SITE_BUNDLE: SiteBundleV1,
    ArtifactKind.QUALITY_REPORT: QualityReportV1,
    ArtifactKind.BUILD_MANIFEST: BuildManifest,
    # AES-WEB-002J.17: ListingDataset has no pre-1.0.0 shape to be additive
    # over -- it registers its current (and only) shape directly.
    ArtifactKind.LISTING_DATASET: ListingDataset,
}

for _kind, _cls in _V1_0_0_CATALOG.items():
    register_artifact_model(_kind, "1.0.0", _cls)

# Amendment A1 (AES-WEB-002 §14.3, ADR-14): ComponentManifest additive-minor
# schema 1.1.0 carrying the optional selection_trace block. Registered
# alongside 1.0.0 with no migration required (additive optional field).
register_artifact_model(
    ArtifactKind.COMPONENT_MANIFEST, "1.1.0", ComponentManifest
)

# AES-WEB-002J.2 (AES-WEB-001 §5.2/Part 2/Part 13 Phase 2): BrandPackage
# additive-minor schema 1.1.0 carrying radius_scale, extended_tokens, and
# contrast_evidence. Registered alongside 1.0.0 with no migration required.
register_artifact_model(
    ArtifactKind.BRAND_PACKAGE, "1.1.0", BrandPackage
)

# AES-WEB-002J.3 (AES-WEB-001 §5.3/Part 2/Part 13 Phase 2): SiteArchitecture
# additive-minor schema 1.1.0 carrying page_ids, page_hierarchy, and
# internal_link_topology. Registered alongside 1.0.0 with no migration
# required.
register_artifact_model(
    ArtifactKind.SITE_ARCHITECTURE, "1.1.0", SiteArchitecture
)

# AES-WEB-002J.7 (AES-WEB-001 §5.6/Part 2/Part 13 Phase 2): LayoutPlan
# additive-minor schema 1.1.0 carrying region_details (typed region identity
# plus deterministic grid/responsive placement). Registered alongside 1.0.0
# with no migration required.
register_artifact_model(
    ArtifactKind.LAYOUT_PLAN, "1.1.0", LayoutPlan
)

# AES-WEB-002J.8 (AES-WEB-001 §5.7/Part 2/Part 13 Phase 2): RenderedPageSet
# additive-minor schema 1.1.0 carrying page_details (per-page HTML text) and
# shared_css (shared CSS text payload). Registered alongside 1.0.0 with no
# migration required.
register_artifact_model(
    ArtifactKind.RENDERED_PAGE_SET, "1.1.0", RenderedPageSet
)

# AES-WEB-002J.10 (AES-WEB-001 §5.9/Part 2/Part 13 Phase 2): SiteBundle
# additive-minor schema 1.1.0 carrying files (per-file UTF-8 text content).
# Registered alongside 1.0.0 with no migration required.
register_artifact_model(
    ArtifactKind.SITE_BUNDLE, "1.1.0", SiteBundle
)

# AES-WEB-002J.11 (AES-WEB-001 §5.10/Part 2/Part 13 Phase 3): QualityReport
# additive-minor schema 1.1.0 carrying deferred_gate_ids (the gates the
# Quality Gate Engine did not evaluate this run). Registered alongside 1.0.0
# with no migration required.
register_artifact_model(
    ArtifactKind.QUALITY_REPORT, "1.1.0", QualityReport
)

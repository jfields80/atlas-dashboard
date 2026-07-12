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
    QualityReport,
    RenderedPageSet,
    SEOPackage,
    SiteArchitecture,
    SiteBundle,
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
    ArtifactKind.SITE_ARCHITECTURE: "1.0.0",
    ArtifactKind.CONTENT_CANDIDATE: "1.0.0",
    ArtifactKind.CONTENT_PACKAGE: "1.0.0",
    # Amendment A1: additive-minor bump to 1.1.0 (optional selection_trace).
    ArtifactKind.COMPONENT_MANIFEST: "1.1.0",
    ArtifactKind.LAYOUT_PLAN: "1.0.0",
    ArtifactKind.RENDERED_PAGE_SET: "1.0.0",
    ArtifactKind.SEO_PACKAGE: "1.0.0",
    ArtifactKind.SITE_BUNDLE: "1.0.0",
    ArtifactKind.QUALITY_REPORT: "1.0.0",
    ArtifactKind.BUILD_MANIFEST: "1.0.0",
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
    "brand_engine": "1.0.0",
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
    ArtifactKind.SITE_ARCHITECTURE: SiteArchitecture,
    ArtifactKind.CONTENT_CANDIDATE: ContentCandidate,
    ArtifactKind.CONTENT_PACKAGE: ContentPackage,
    ArtifactKind.COMPONENT_MANIFEST: ComponentManifestV1,
    ArtifactKind.LAYOUT_PLAN: LayoutPlan,
    ArtifactKind.RENDERED_PAGE_SET: RenderedPageSet,
    ArtifactKind.SEO_PACKAGE: SEOPackage,
    ArtifactKind.SITE_BUNDLE: SiteBundle,
    ArtifactKind.QUALITY_REPORT: QualityReport,
    ArtifactKind.BUILD_MANIFEST: BuildManifest,
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

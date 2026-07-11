"""Schema-version and engine-version registries (AES-WEB-001 §4.6).

Two independent version axes, both recorded in every ``BuildManifest``:

* **Schema versions** — semver per artifact kind. The registry maps
  ``(artifact_kind, schema_version) → model class``.
* **Engine versions** — semver per engine class, bumped whenever output
  could differ for identical input (the replayability contract).

Phase 1 registers all twelve artifact kinds at v1.0.0. ComponentManifest
remains 1.0.0 (no AES-WEB-002 ``selection_trace`` amendment).
"""

from __future__ import annotations

from typing import Dict, Tuple, Type

from engines.website_generation.contracts.artifacts import (
    ArtifactHeader,
    BrandPackage,
    BuildManifest,
    BusinessSpec,
    ComponentManifest,
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
    ArtifactKind.BRAND_PACKAGE: "1.0.0",
    ArtifactKind.SITE_ARCHITECTURE: "1.0.0",
    ArtifactKind.CONTENT_CANDIDATE: "1.0.0",
    ArtifactKind.CONTENT_PACKAGE: "1.0.0",
    ArtifactKind.COMPONENT_MANIFEST: "1.0.0",
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
# v1.0.0 catalog registration (executed once at import)
# ---------------------------------------------------------------------------

_V1_CATALOG: Dict[ArtifactKind, Type[ArtifactHeader]] = {
    ArtifactKind.BUSINESS_SPEC: BusinessSpec,
    ArtifactKind.BRAND_PACKAGE: BrandPackage,
    ArtifactKind.SITE_ARCHITECTURE: SiteArchitecture,
    ArtifactKind.CONTENT_CANDIDATE: ContentCandidate,
    ArtifactKind.CONTENT_PACKAGE: ContentPackage,
    ArtifactKind.COMPONENT_MANIFEST: ComponentManifest,
    ArtifactKind.LAYOUT_PLAN: LayoutPlan,
    ArtifactKind.RENDERED_PAGE_SET: RenderedPageSet,
    ArtifactKind.SEO_PACKAGE: SEOPackage,
    ArtifactKind.SITE_BUNDLE: SiteBundle,
    ArtifactKind.QUALITY_REPORT: QualityReport,
    ArtifactKind.BUILD_MANIFEST: BuildManifest,
}

for _kind, _cls in _V1_CATALOG.items():
    register_artifact_model(_kind, SCHEMA_VERSIONS[_kind], _cls)

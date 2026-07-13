"""Layout Engine tests (AES-WEB-002J.7).

Shared fixture builders so layout tests construct well-formed
``ComponentManifest``/``BrandPackage``/``ComponentRegistry`` inputs without
repeating the full field set. ``make_definition`` is the established
component-system fixture builder (``tests/website_generation/components``),
reused here per the ``tests/website_generation/gates`` cross-package
precedent.
"""

from __future__ import annotations

from typing import Iterable

from engines.website_generation.components import ComponentRegistry
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    ComponentInstance,
    ComponentManifest,
    PageComponents,
)
from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

from ..components import make_definition

__all__ = [
    "make_definition",
    "make_manifest",
    "make_brand_package",
    "make_registry",
    "instance",
    "page",
]


def instance(**overrides) -> ComponentInstance:
    fields = dict(component_id="hero.split.value-proposition", component_version="1.0.0")
    fields.update(overrides)
    return ComponentInstance(**fields)


def page(route="/", components=()) -> PageComponents:
    return PageComponents(route=route, components=tuple(components))


def make_manifest(pages=(), **overrides) -> ComponentManifest:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST],
        artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
        source_hashes={},
        pages=tuple(pages),
    )
    fields.update(overrides)
    return ComponentManifest(**fields)


def make_brand_package(**overrides) -> BrandPackage:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BRAND_PACKAGE],
        artifact_kind=ArtifactKind.BRAND_PACKAGE,
        source_hashes={},
        extended_tokens={
            "grid.columns.2": "repeat(2, minmax(0, 1fr))",
            "grid.columns.3": "repeat(3, minmax(0, 1fr))",
            "grid.columns.4": "repeat(4, minmax(0, 1fr))",
            "grid.gap.default": "24px",
        },
    )
    fields.update(overrides)
    return BrandPackage(**fields)


def make_registry(definitions: Iterable[ComponentDefinition]) -> ComponentRegistry:
    return ComponentRegistry(definitions)

"""Renderer tests (AES-WEB-002J.8).

Shared fixture builders so rendering tests construct well-formed
``LayoutPlan``/``ComponentManifest``/``ContentPackage``/``BrandPackage``
inputs without repeating the full field set, mirroring the
``tests/website_generation/layouts`` cross-package precedent.

Unlike the Layout Engine tests (which drive synthetic minimal component
definitions), these helpers drive the *real* 72-component catalog via
``build_default_registry()`` -- the deliverable this suite verifies is the
32 real J.8 emitters wired to the real registered contracts, not a
stand-in. ``render_single_component`` auto-derives a minimal valid
``ComponentInstance``/content/placement for any registered component from
its own contract (required props/slots), the same mechanism the
AES-WEB-002J.8 implementation's own smoke tests used, so every one of the
32 components can be exercised in isolation with a few lines per test.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components.registry import (
    ComponentRegistry,
    build_default_registry,
)
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    ComponentInstance,
    ComponentManifest,
    ComponentPlacement,
    ContentBlock,
    ContentPackage,
    GridPlacement,
    LayoutPlan,
    LayoutRegion,
    PageComponents,
    PageLayout,
    RegionLayoutDetail,
    ResponsiveSelection,
)
from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.contracts.enums import ArtifactKind, PropType, RegionKind
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS
from engines.website_generation.rendering.renderer import EMITTER_TABLE, Renderer

__all__ = [
    "J8_COMPONENT_IDS",
    "real_registry",
    "real_brand_package",
    "make_layout_plan",
    "make_component_manifest",
    "make_content_package",
    "sample_prop_value",
    "minimal_fixture_for",
    "render_single_component",
    "render_page",
]

# The 32 J.8-authorized component ids, derived from the emitter table
# itself (never hand-copied) so this list can never silently drift from
# what the Renderer actually registers.
J8_COMPONENT_IDS: Tuple[str, ...] = tuple(
    sorted(key.rsplit("@", 1)[0] for key in EMITTER_TABLE)
)


def real_registry() -> ComponentRegistry:
    """The real 72-component MVP catalog -- the actual deliverable, not a
    synthetic stand-in."""
    return build_default_registry()


def real_brand_package() -> BrandPackage:
    """A fully token-populated BrandPackage from the real Brand Engine
    (every token any J.8 component's ``design_token_dependencies``
    references resolves against this)."""
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="PetTripFinder",
        niche="pet travel",
        audience="pet owners",
        value_proposition="find pet-friendly travel",
    )
    return BrandEngine().resolve(spec)


def make_layout_plan(pages=(), region_details=(), **overrides) -> LayoutPlan:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LAYOUT_PLAN],
        artifact_kind=ArtifactKind.LAYOUT_PLAN,
        source_hashes={},
        pages=tuple(pages),
        region_details=tuple(region_details),
    )
    fields.update(overrides)
    return LayoutPlan(**fields)


def make_component_manifest(pages=(), **overrides) -> ComponentManifest:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST],
        artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
        source_hashes={},
        pages=tuple(pages),
    )
    fields.update(overrides)
    return ComponentManifest(**fields)


def make_content_package(blocks=(), **overrides) -> ContentPackage:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )
    fields.update(overrides)
    return ContentPackage(**fields)


def sample_prop_value(prop_spec, *, text: str = "value") -> str:
    """A deterministic, valid sample value for any ``PropSpec`` -- the same
    per-``PropType`` rule the AES-WEB-002J.8 implementation's own
    verification smoke tests used."""
    if prop_spec.prop_type is PropType.STR_ENUM:
        return prop_spec.enum_values[0] if prop_spec.enum_values else text
    if prop_spec.prop_type is PropType.BOOL:
        return "false"
    if prop_spec.prop_type is PropType.INT_BOUNDED:
        return str(prop_spec.int_min if prop_spec.int_min is not None else 1)
    if prop_spec.prop_type is PropType.CONTENT_BLOCK_REF:
        return "ref-" + text
    if prop_spec.prop_type is PropType.ROUTE_REF:
        return "/target"
    if prop_spec.prop_type is PropType.ASSET_REF:
        return "/assets/x.png"
    if prop_spec.prop_type is PropType.A11Y_LABEL:
        return "Accessible label"
    return text


def minimal_fixture_for(
    definition: ComponentDefinition,
    route: str,
    *,
    prop_overrides: Optional[Dict[str, str]] = None,
    content_overrides: Optional[Dict[str, str]] = None,
    include_optional: bool = False,
) -> Tuple[ComponentInstance, Tuple[ContentBlock, ...]]:
    """A minimal, contract-valid ``(ComponentInstance, content blocks)`` pair
    for ``definition`` -- every required prop bound to a deterministic
    sample value, every required content slot (and, if
    ``include_optional``, every optional one) bound to a resolvable
    ``ContentBlock``. ``prop_overrides``/``content_overrides`` key by
    prop/slot name and take precedence over the generated sample."""
    prop_overrides = prop_overrides or {}
    content_overrides = content_overrides or {}

    props: Dict[str, str] = {}
    blocks = []
    for name, spec in definition.required_props.items():
        value = prop_overrides.get(name, sample_prop_value(spec, text=name))
        props[name] = value
        if spec.prop_type is PropType.CONTENT_BLOCK_REF:
            blocks.append(
                ContentBlock(
                    page_route=route,
                    slot_id=value,
                    text=content_overrides.get(name, "Resolved %s" % name),
                )
            )

    content_refs = []
    slot_sets = [definition.required_content_slots]
    if include_optional:
        slot_sets.append(definition.optional_content_slots)
    for slots in slot_sets:
        for slot_id in slots:
            content_refs.append(slot_id)
            blocks.append(
                ContentBlock(
                    page_route=route,
                    slot_id=slot_id,
                    text=content_overrides.get(slot_id, "Resolved %s" % slot_id),
                )
            )

    instance = ComponentInstance(
        component_id=definition.component_id,
        component_version=definition.component_version,
        props=props,
        content_refs=tuple(content_refs),
    )
    return instance, tuple(blocks)


def render_page(
    registry: ComponentRegistry,
    brand: BrandPackage,
    route: str,
    instances: Iterable[ComponentInstance],
    content_blocks: Iterable[ContentBlock],
    region_kind: RegionKind = RegionKind.BODY,
):
    """Render one page carrying every instance in ``instances``, all placed
    (in order) into a single ``region_kind`` region. Returns the
    ``RenderedPageSet``."""
    instances = tuple(instances)
    manifest = make_component_manifest(
        pages=(PageComponents(route=route, components=instances),)
    )
    content = make_content_package(blocks=tuple(content_blocks))
    indexes = tuple(range(len(instances)))
    layout = make_layout_plan(
        pages=(
            PageLayout(
                route=route,
                regions=(
                    LayoutRegion(region_id=region_kind.value, component_indexes=indexes),
                ),
            ),
        ),
        region_details=(
            RegionLayoutDetail(
                route=route,
                region_id=region_kind.value,
                region_kind=region_kind,
                placements=tuple(
                    ComponentPlacement(
                        component_index=i,
                        grid=GridPlacement(),
                        responsive=ResponsiveSelection(),
                    )
                    for i in indexes
                ),
            ),
        ),
    )
    return Renderer(registry).render(layout, manifest, content, brand)


def render_single_component(
    registry: ComponentRegistry,
    brand: BrandPackage,
    component_id: str,
    *,
    route: str = "/",
    prop_overrides: Optional[Dict[str, str]] = None,
    content_overrides: Optional[Dict[str, str]] = None,
    include_optional: bool = False,
):
    """Render a page containing exactly one instance of ``component_id``,
    auto-deriving a minimal valid fixture from its own registered contract.
    Returns the ``RenderedPageSet``."""
    definition = registry.get(component_id)
    region_kind = (
        definition.allowed_parent_regions[0]
        if definition.allowed_parent_regions
        else RegionKind.BODY
    )
    instance, blocks = minimal_fixture_for(
        definition,
        route,
        prop_overrides=prop_overrides,
        content_overrides=content_overrides,
        include_optional=include_optional,
    )
    return render_page(registry, brand, route, (instance,), blocks, region_kind)

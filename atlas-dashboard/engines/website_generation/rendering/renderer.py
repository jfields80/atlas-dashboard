"""Renderer -- (LayoutPlan, ComponentManifest, ContentPackage, BrandPackage)
-> RenderedPageSet (AES-WEB-001 §5.7 / Part 2).

Internal sequencing label: AES-WEB-002J.8. Walks the LayoutPlan's already-
fixed region/component order (never reordering), resolves each placed
component's definition and content from the injected registry and the
supplied artifacts, and hands each instance to its registered pure emitter
function (``EMITTER_TABLE``, assembled below from the three per-family
tables). Wraps every page's assembled region markup in the document shell
(``layout.shell.page``'s emitter) and compiles the shared CSS once from
every component actually present across the whole build (manifest-driven
tree-shaking, §20.2).

Deterministic, pure, serializable, byte-stable: the same (LayoutPlan,
ComponentManifest, ContentPackage, BrandPackage, registry, Renderer
version) always produces the same RenderedPageSet (or the same batch of
diagnostics). No network access, no filesystem access, no CAS access, no
model calls, no randomness, no clock/UUID reads. Not wired into pipeline
execution -- ``rendering`` remains ``NOT_EXECUTED`` in the ``BuildManifest``
(``PHASE1_EXECUTED_STAGES`` is unchanged by this module).

Registry as a required constructor-injected dependency (mirroring
``LayoutEngine``'s AES-WEB-002J.7 decision D-3): ``rendering/`` may import
only ``contracts/`` and ``constants/`` (§3.2/§29.2 matrix) -- it has no
legal import path to the concrete ``components/`` registry, so the registry
is a required constructor argument, never a self-constructed default.

D-1 (approved operator decision): the Renderer's public ``render`` method
takes four artifacts, not the three §5.7's summary table names.
``LayoutPlan.RegionLayoutDetail.placements[].component_index`` names an
index into ``ComponentManifest`` page components (§4.1 artifact #7's own
description: "LayoutPlan ... region, grid placement"; the manifest holds
the actual bound ``ComponentInstance`` -- id, version, props, content
refs). The Renderer only *indexes* the manifest; it never reorders or
mutates it.

Emitter-table placement (documented deviation from a literal reading of
§20.1's "explicit registered dict in rendering/html_emitter.py internals"):
the merged ``EMITTER_TABLE`` is assembled here, in ``renderer.py``, not in
``html_emitter.py``. ``html_emitter.py`` holds only primitives (escaping,
element serialization) that every ``emitters_*.py`` module imports;
``emitters_*.py`` modules import ``html_emitter`` but must never import each
other or ``renderer.py`` (no sibling-family coupling). Building the merged
table therefore has to happen at the one module that legitimately imports
all three family tables -- ``renderer.py``, the orchestrator -- rather than
inside ``html_emitter.py``, which would otherwise need to import "downward"
into every ``emitters_*.py`` module and create an import cycle
(``emitters_*`` -> ``html_emitter`` -> ``emitters_*``). The table itself is
still exactly what §20.1 requires: one explicit, duplicate-checked dict, no
dynamic scanning, no decorators.

Content-resolution convention (AES-WEB-002J.8, documented decision -- the
authorities specify no exact ``ComponentInstance.content_refs``/
``CONTENT_BLOCK_REF``-prop string format, and the production Component
Engine always leaves ``content_refs`` empty this wave, so no runtime
precedent exists to follow). This module treats:

* a declared content slot (``required_content_slots``/
  ``optional_content_slots``) as bound when its slot id appears in
  ``instance.content_refs``; its resolved value is every ``ContentBlock``
  in the ``ContentPackage`` sharing ``(route, slot_id)``, in the package's
  own order (never re-sorted) -- a tuple, so ``EXACTLY_ONE`` and
  ``ONE_TO_N`` slots share one uniform shape.
* a ``CONTENT_BLOCK_REF``-typed prop's string *value* as itself a slot id,
  resolved the same way against ``(route, value)`` -- not read from
  ``content_refs`` (props and slots are separate binding mechanisms per the
  contract shape, §8.1/§8.2).
* a ``ROUTE_REF``/``ASSET_REF``/``A11Y_LABEL``-typed prop's string value as
  already the literal value to use -- no resolution, matching what each
  type name says: a route reference, an asset reference, or literal label
  text.

Never fuzzy matching, never inferred from a component id -- always an exact
``(route, slot_id)`` key lookup.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from engines.website_generation.constants.build import STAGE_RENDERING
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    ComponentInstance,
    ComponentManifest,
    ComponentPlacement,
    ContentPackage,
    GridPlacement,
    LayoutPlan,
    PageComponents,
    RenderedPage,
    RenderedPageDetail,
    RenderedPageSet,
    ResponsiveSelection,
    artifact_sha256,
    sha256_of_text,
)
from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.contracts.enums import ArtifactKind, PropType, RegionKind
from engines.website_generation.contracts.errors import ComponentSystemError, RenderError
from engines.website_generation.contracts.interfaces import (
    ComponentRegistryView,
    RendererInterface,
)
from engines.website_generation.contracts.versions import ENGINE_VERSIONS, SCHEMA_VERSIONS
from engines.website_generation.rendering.css_emitter import compile_shared_css
from engines.website_generation.rendering.emitters_discovery import DISCOVERY_EMITTERS
from engines.website_generation.rendering.emitters_layout_atoms import LAYOUT_ATOMS_EMITTERS
from engines.website_generation.rendering.emitters_listings_profiles import (
    LISTINGS_PROFILES_EMITTERS,
)
from engines.website_generation.rendering.emitters_monetization_status import (
    MONETIZATION_STATUS_EMITTERS,
)
from engines.website_generation.rendering.emitters_navigation import NAVIGATION_EMITTERS
from engines.website_generation.rendering.emitters_seo_editorial import (
    SEO_EDITORIAL_EMITTERS,
)
from engines.website_generation.rendering.emitters_trust_conversion import (
    TRUST_CONVERSION_EMITTERS,
)
from engines.website_generation.rendering.html_emitter import (
    EmitterFn,
    LayoutContext,
    ResolvedContent,
    TokenMap,
    is_safe_url,
)

# ---------------------------------------------------------------------------
# The explicit, duplicate-checked emitter table (§20.1) -- see module
# docstring "Emitter-table placement" for why this assembly lives here
# rather than textually inside html_emitter.py.
# ---------------------------------------------------------------------------


def _build_emitter_table() -> Dict[str, EmitterFn]:
    table: Dict[str, EmitterFn] = {}
    for family_table in (
        # J.8 Renderer Foundation families (32).
        LAYOUT_ATOMS_EMITTERS,
        NAVIGATION_EMITTERS,
        DISCOVERY_EMITTERS,
        # AES-WEB-002J.9 remaining families (40), closing the 72-component
        # emitter table.
        LISTINGS_PROFILES_EMITTERS,
        TRUST_CONVERSION_EMITTERS,
        SEO_EDITORIAL_EMITTERS,
        MONETIZATION_STATUS_EMITTERS,
    ):
        for key, fn in family_table.items():
            if key in table:
                raise RenderError(
                    "duplicate emitter registration for %r" % key,
                    stage="rendering",
                    diagnostics={"emitter_key": key},
                )
            table[key] = fn
    return table


EMITTER_TABLE: Dict[str, EmitterFn] = _build_emitter_table()

# AES-WEB-002J.9 implements every remaining family emitter, so the emitter
# table is now complete at 72 keys and no emitter key is expected-absent.
# The set is retained (empty) so the J.8 integrity tests that consumed it as
# the "provably intentional absence" invariant continue to import it and now
# assert emptiness -- the invariant they enforce is preserved, its value has
# simply gone to zero as the catalog's emitter coverage reached 100%.
J9_EXPECTED_ABSENT_EMITTER_KEYS: frozenset = frozenset()

_SHELL_EMITTER_KEY = "layout.shell.page@1"
_SHELL_COMPONENT_ID = "layout.shell.page"
_SHELL_COMPONENT_VERSION = "1.0.0"
_SHELL_BODY_SLOT = "__shell_body__"

# Regions the document shell wraps in their own landmark (§9.1/CG-CMP-006).
_LANDMARK_TAGS: Dict[RegionKind, str] = {
    RegionKind.HEADER: "header",
    RegionKind.BODY: "main",
    RegionKind.FOOTER: "footer",
}

_HREF_ATTR_RE = re.compile(r'\b(?:href|action|src)="([^"]*)"')
_ID_ATTR_RE = re.compile(r'\bid="([^"]*)"')


def _flatten_tokens(brand_package: BrandPackage) -> TokenMap:
    """Merge every BrandPackage token domain into one lookup keyed by the
    bare dotted token id (§8.3) -- the same id space
    ``design_token_dependencies``/``GridPlacement.columns_token`` reference."""
    tokens: TokenMap = {}
    tokens.update(brand_package.palette)
    tokens.update(brand_package.type_scale)
    tokens.update(brand_package.spacing_scale)
    tokens.update(brand_package.radius_scale)
    tokens.update(brand_package.extended_tokens)
    return tokens


# Prop types whose string value names a ContentPackage block to resolve
# (via ``(route, value)``), exactly like a declared content slot -- as
# opposed to ROUTE_REF/ASSET_REF/A11Y_LABEL/STR_ENUM props, whose value is
# already the literal to use. CONTENT_BLOCK_REF is the J.8 case;
# AES-WEB-002J.9 adds LISTING_REF, the mechanism every listing.*/profile.*/
# claim-form component uses to reach its bound listing's ContentPackage data
# ("resolves the ... 'via listing block' content -- no separate content
# slot is declared", listings_profiles.py). No J.8 component declares a
# LISTING_REF prop, so extending the set here changes no J.8 output.
_CONTENT_REF_PROP_TYPES = frozenset(
    {PropType.CONTENT_BLOCK_REF, PropType.LISTING_REF}
)


def _content_block_ref_prop_names(definition: ComponentDefinition) -> Tuple[str, ...]:
    names = []
    for name, spec in sorted(definition.required_props.items()):
        if spec.prop_type in _CONTENT_REF_PROP_TYPES:
            names.append(name)
    for name, spec in sorted(definition.optional_props.items()):
        if spec.prop_type in _CONTENT_REF_PROP_TYPES:
            names.append(name)
    return tuple(names)


class Renderer(RendererInterface):
    """Emit a deterministic ``RenderedPageSet`` from a ``LayoutPlan``,
    ``ComponentManifest``, ``ContentPackage``, and ``BrandPackage``
    (AES-WEB-001 §5.7; AES-WEB-002 §8, §20)."""

    version = ENGINE_VERSIONS["renderer"]

    def __init__(self, registry: ComponentRegistryView) -> None:
        self._registry = registry

    def render(
        self,
        layout_plan: LayoutPlan,
        component_manifest: ComponentManifest,
        content_package: ContentPackage,
        brand_package: BrandPackage,
    ) -> RenderedPageSet:
        """Total function over structurally valid inputs; batch-fails
        otherwise (mirrors ``LayoutEngine.compose``'s batch-reporting
        discipline). Neither input is mutated (all are frozen); page order,
        region order, and component order are pure functions of
        ``layout_plan``'s declared order -- never of dict/set iteration
        order (AES-WEB-001 §1.1 replayability contract). No partial
        ``RenderedPageSet`` is ever returned when diagnostics exist.
        """
        tokens = _flatten_tokens(brand_package)
        manifest_by_route: Dict[str, PageComponents] = {
            page.route: page for page in component_manifest.pages
        }
        content_index: Dict[Tuple[str, str], Tuple[str, ...]] = {}
        for block in content_package.blocks:
            key = (block.page_route, block.slot_id)
            content_index[key] = content_index.get(key, ()) + (block.text,)

        diagnostics: Dict[str, List[Dict[str, object]]] = {}
        rendered_pages: List[RenderedPage] = []
        page_details: List[RenderedPageDetail] = []
        present_definitions: Dict[Tuple[str, str], ComponentDefinition] = {}

        for page in layout_plan.pages:
            route = page.route
            page_diagnostics: Dict[str, List[Dict[str, object]]] = {}
            page_components = manifest_by_route.get(route)
            if page_components is None:
                self._add(page_diagnostics, "unresolved_routes", {"route": route})
                self._merge(diagnostics, page_diagnostics)
                continue

            region_detail_by_id = {
                detail.region_id: detail
                for detail in layout_plan.region_details
                if detail.route == route
            }

            region_html_parts: List[str] = []
            for region in page.regions:
                try:
                    region_kind = RegionKind(region.region_id)
                except ValueError:
                    self._add(
                        page_diagnostics,
                        "malformed_layout_indexes",
                        {"route": route, "reason": "unknown_region_id", "region_id": region.region_id},
                    )
                    continue
                detail = region_detail_by_id.get(region.region_id)
                fragments = self._render_region(
                    route=route,
                    region_kind=region_kind,
                    component_indexes=region.component_indexes,
                    placements=detail.placements if detail is not None else (),
                    page_components=page_components,
                    content_index=content_index,
                    tokens=tokens,
                    present_definitions=present_definitions,
                    diagnostics=page_diagnostics,
                )
                joined = "".join(fragments)
                landmark = _LANDMARK_TAGS.get(region_kind)
                if landmark == "main":
                    region_html_parts.append('<main id="main">%s</main>' % joined)
                elif landmark:
                    region_html_parts.append("<%s>%s</%s>" % (landmark, joined, landmark))
                else:
                    region_html_parts.append(joined)

            if page_diagnostics:
                self._merge(diagnostics, page_diagnostics)
                continue  # do not assemble a shell around a page with errors

            body_html = "".join(region_html_parts)
            full_html = self._wrap_in_shell(body_html, tokens, present_definitions)

            unsafe = self._scan_unsafe_urls(full_html)
            if unsafe:
                self._add(
                    page_diagnostics,
                    "unsafe_urls",
                    {"route": route, "urls": sorted(set(unsafe))},
                )
            duplicate_ids = self._scan_duplicate_ids(full_html)
            if duplicate_ids:
                self._add(
                    page_diagnostics,
                    "duplicate_dom_ids",
                    {"route": route, "ids": sorted(set(duplicate_ids))},
                )

            if page_diagnostics:
                self._merge(diagnostics, page_diagnostics)
                continue

            html_hash = sha256_of_text(full_html)
            rendered_pages.append(
                RenderedPage(route=route, html_hash=html_hash, css_hash="")
            )
            page_details.append(RenderedPageDetail(route=route, html=full_html))

        if diagnostics:
            raise RenderError(
                "RenderedPageSet emission failed; see diagnostics",
                stage=STAGE_RENDERING,
                diagnostics=diagnostics,
            )

        shared_css = compile_shared_css(present_definitions.values(), tokens)
        shared_css_hash = sha256_of_text(shared_css)

        return RenderedPageSet(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.RENDERED_PAGE_SET],
            artifact_kind=ArtifactKind.RENDERED_PAGE_SET,
            source_hashes=self._build_source_hashes(
                layout_plan, component_manifest, content_package, brand_package
            ),
            pages=tuple(rendered_pages),
            shared_css_hash=shared_css_hash,
            page_details=tuple(page_details),
            shared_css=shared_css,
        )

    # -- per-region walk -----------------------------------------------

    def _render_region(
        self,
        *,
        route: str,
        region_kind: RegionKind,
        component_indexes: Tuple[int, ...],
        placements: Tuple[ComponentPlacement, ...],
        page_components: PageComponents,
        content_index: Dict[Tuple[str, str], Tuple[str, ...]],
        tokens: TokenMap,
        present_definitions: Dict[Tuple[str, str], ComponentDefinition],
        diagnostics: Dict[str, List[Dict[str, object]]],
    ) -> List[str]:
        fragments: List[str] = []
        placement_by_index = {p.component_index: p for p in placements}

        for component_index in component_indexes:
            if component_index < 0 or component_index >= len(page_components.components):
                self._add(
                    diagnostics,
                    "malformed_layout_indexes",
                    {
                        "route": route,
                        "reason": "component_index_out_of_range",
                        "component_index": component_index,
                    },
                )
                continue
            instance = page_components.components[component_index]

            try:
                definition = self._registry.get(
                    instance.component_id, instance.component_version
                )
            except ComponentSystemError:
                self._add(
                    diagnostics,
                    "unresolved_components",
                    {
                        "route": route,
                        "component_index": component_index,
                        "component_id": instance.component_id,
                        "component_version": instance.component_version,
                    },
                )
                continue

            emitter_key = definition.rendering_contract.emitter_key
            emitter = EMITTER_TABLE.get(emitter_key)
            if emitter is None:
                self._add(
                    diagnostics,
                    "missing_emitters",
                    {
                        "route": route,
                        "component_index": component_index,
                        "component_id": instance.component_id,
                        "emitter_key": emitter_key,
                    },
                )
                continue

            missing_props = [
                name
                for name, spec in definition.required_props.items()
                if name not in instance.props and spec.default is None
            ]
            if missing_props:
                self._add(
                    diagnostics,
                    "missing_required_props",
                    {
                        "route": route,
                        "component_index": component_index,
                        "component_id": instance.component_id,
                        "props": sorted(missing_props),
                    },
                )
                continue

            resolved, missing_content = self._resolve_content(
                route=route,
                instance=instance,
                definition=definition,
                content_index=content_index,
            )
            if missing_content:
                self._add(
                    diagnostics,
                    "missing_required_content",
                    {
                        "route": route,
                        "component_index": component_index,
                        "component_id": instance.component_id,
                        "slots": sorted(missing_content),
                    },
                )
                continue

            for token_id in definition.design_token_dependencies:
                if token_id not in tokens:
                    self._add(
                        diagnostics,
                        "missing_tokens",
                        {
                            "route": route,
                            "component_index": component_index,
                            "component_id": instance.component_id,
                            "token_id": token_id,
                        },
                    )

            placement = placement_by_index.get(component_index)
            grid = placement.grid if placement is not None else GridPlacement()
            responsive = (
                placement.responsive if placement is not None else ResponsiveSelection()
            )
            layout_ctx = LayoutContext(
                region_kind=region_kind,
                component_index=component_index,
                grid=grid,
                responsive=responsive,
            )

            present_definitions.setdefault(
                (definition.component_id, definition.component_version), definition
            )
            fragments.append(emitter(instance, resolved, tokens, layout_ctx))

        return fragments

    # -- content resolution ----------------------------------------------

    @staticmethod
    def _resolve_content(
        *,
        route: str,
        instance: ComponentInstance,
        definition: ComponentDefinition,
        content_index: Dict[Tuple[str, str], Tuple[str, ...]],
    ) -> Tuple[ResolvedContent, List[str]]:
        resolved: ResolvedContent = {}
        missing_required: List[str] = []

        all_slots = dict(definition.required_content_slots)
        all_slots.update(definition.optional_content_slots)
        for slot_id in sorted(all_slots):
            if slot_id not in instance.content_refs:
                if slot_id in definition.required_content_slots:
                    missing_required.append(slot_id)
                continue
            values = content_index.get((route, slot_id), ())
            if not values and slot_id in definition.required_content_slots:
                missing_required.append(slot_id)
                continue
            resolved[slot_id] = values

        for prop_name in _content_block_ref_prop_names(definition):
            raw_value = instance.props.get(prop_name)
            if not raw_value:
                continue
            values = content_index.get((route, raw_value), ())
            if not values and prop_name in definition.required_props:
                missing_required.append(prop_name)
                continue
            resolved[prop_name] = values

        return resolved, missing_required

    # -- shell wrapping ----------------------------------------------------

    def _wrap_in_shell(
        self,
        body_html: str,
        tokens: TokenMap,
        present_definitions: Dict[Tuple[str, str], ComponentDefinition],
    ) -> str:
        """Wrap assembled region markup in the document shell (§9.1/§9.3).
        ``layout.shell.page`` never appears in a ``ComponentManifest`` (its
        own ``allowed_parent_regions`` is empty -- it is the composition
        root, never a region member -- see the AES-WEB-002J.8
        implementation report's documented finding), so its emitter is
        invoked directly here with a synthesized instance rather than
        resolved via the normal per-region walk."""
        try:
            shell_definition = self._registry.get(
                _SHELL_COMPONENT_ID, _SHELL_COMPONENT_VERSION
            )
        except ComponentSystemError as exc:
            raise RenderError(
                "layout.shell.page@1.0.0 is not registered",
                stage=STAGE_RENDERING,
                diagnostics={"component_id": _SHELL_COMPONENT_ID},
            ) from exc
        present_definitions.setdefault(
            (shell_definition.component_id, shell_definition.component_version),
            shell_definition,
        )
        shell_instance = ComponentInstance(
            component_id=_SHELL_COMPONENT_ID,
            component_version=_SHELL_COMPONENT_VERSION,
        )
        shell_resolved: ResolvedContent = {_SHELL_BODY_SLOT: (body_html,)}
        shell_ctx = LayoutContext(
            region_kind=RegionKind.BODY,
            component_index=-1,
            grid=GridPlacement(),
            responsive=ResponsiveSelection(),
        )
        return EMITTER_TABLE[_SHELL_EMITTER_KEY](
            shell_instance, shell_resolved, tokens, shell_ctx
        )

    # -- post-processing safety scans --------------------------------------

    @staticmethod
    def _scan_unsafe_urls(html_text: str) -> List[str]:
        """Scheme-validate every ``href``/``action``/``src`` value in the
        fully-assembled page (CG-RND-009) -- a deterministic post-processing
        pass over the final markup, catching every URL-bearing attribute any
        of the 32 emitters produced, uniformly, without threading
        per-component "this prop is a URL" metadata through the emitter
        signature."""
        return [
            value
            for value in _HREF_ATTR_RE.findall(html_text)
            if value and not is_safe_url(value)
        ]

    @staticmethod
    def _scan_duplicate_ids(html_text: str) -> List[str]:
        """Every ``id`` attribute value appearing more than once
        (CG-RND-008)."""
        seen: set = set()
        duplicates: List[str] = []
        for value in _ID_ATTR_RE.findall(html_text):
            if value in seen:
                duplicates.append(value)
            seen.add(value)
        return duplicates

    # -- diagnostics / provenance -------------------------------------------

    @staticmethod
    def _add(
        diagnostics: Dict[str, List[Dict[str, object]]], bucket: str, entry: Dict[str, object]
    ) -> None:
        diagnostics.setdefault(bucket, [])
        diagnostics[bucket].append(entry)

    @staticmethod
    def _merge(
        target: Dict[str, List[Dict[str, object]]],
        source: Dict[str, List[Dict[str, object]]],
    ) -> None:
        for bucket, entries in source.items():
            target.setdefault(bucket, [])
            target[bucket].extend(entries)

    @staticmethod
    def _build_source_hashes(
        layout_plan: LayoutPlan,
        component_manifest: ComponentManifest,
        content_package: ContentPackage,
        brand_package: BrandPackage,
    ) -> Dict[str, str]:
        return {
            "layout_plan": artifact_sha256(layout_plan),
            "component_manifest": artifact_sha256(component_manifest),
            "content_package": artifact_sha256(content_package),
            "brand_package": artifact_sha256(brand_package),
        }

"""LayoutEngine -- (ComponentManifest, BrandPackage) -> LayoutPlan
(AES-WEB-001 §5.6 / Part 2).

Internal sequencing label: AES-WEB-002J.7. Groups every selected component
instance into a ``RegionKind`` region, preserving the page order and
component order already fixed by the ``ComponentManifest`` (§6.1: "LayoutPlan
MAY reorder only within the recipe's declared flexible zones" -- no
machine-readable flexible-zone contract exists yet, so manifest order is
authoritative, per AES-WEB-002J.7 decision "Ordering"). Records deterministic
grid and responsive placement drawn only from each component's own registry
contract and the injected ``BrandPackage`` design tokens (§8.3, §10, §11). It
selects no component, generates no markup, CSS, or media queries, and
performs no filesystem, network, AI, clock, UUID, or randomness access.

Deterministic, pure, serializable, byte-stable: the same
``(ComponentManifest, BrandPackage, registry)`` triple always produces the
same ``LayoutPlan`` (or the same batch of diagnostics), regardless of
dict/set iteration order. Not wired into pipeline execution --
``layout_composition`` remains ``NOT_EXECUTED`` in the ``BuildManifest``
(``PHASE1_EXECUTED_STAGES`` is unchanged by this module).

Registry as a required constructor-injected dependency (AES-WEB-002J.7
decision D-3). Unlike ``ComponentEngine`` (whose concrete class lives inside
``components/`` and may therefore default the registry via
``build_default_registry()``), ``layouts/`` may import only ``contracts/``
and ``constants/`` (§3.2 matrix) -- it has no legal import path to the
concrete catalog. The registry is therefore a required constructor argument,
never a self-constructed default; production callers (the future pipeline
wiring) and tests both supply it explicitly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from engines.website_generation.constants.build import STAGE_LAYOUT_COMPOSITION
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    ComponentManifest,
    ComponentPlacement,
    GridPlacement,
    LayoutPlan,
    LayoutRegion,
    PageLayout,
    RegionLayoutDetail,
    ResponsiveSelection,
    artifact_sha256,
)
from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.contracts.enums import ArtifactKind, RegionKind
from engines.website_generation.contracts.errors import (
    ComponentSystemError,
    LayoutCompositionError,
)
from engines.website_generation.contracts.interfaces import (
    ComponentRegistryView,
    LayoutEngineInterface,
)
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)

# Fixed diagnostics key order (readability/debugging only -- dict equality
# does not depend on key order), mirroring
# component_engine._DIAGNOSTIC_BUCKET_ORDER.
_DIAGNOSTIC_BUCKET_ORDER = (
    "unresolved_components",
    "illegal_placements",
    "repetition_limit_violations",
    "invalid_grid_references",
)

# The BrandPackage extended-token prefix a grid-columns dependency uses
# (AES-WEB-002 §10.2 layout token domain; constants/brand.py
# SHARED_EXTENDED_TOKENS: "grid.columns.2", "grid.columns.3", "grid.columns.4").
_GRID_COLUMNS_TOKEN_PREFIX = "grid.columns."


def _grid_token_for(definition: ComponentDefinition) -> str:
    """The first ``grid.columns.*`` token the definition declares (§10.3
    declared-order tie-break), or ``""`` when it declares none -- the
    deterministic single-column/flow default. Never guessed from the
    component's name or family."""
    for token in definition.design_token_dependencies:
        if token.startswith(_GRID_COLUMNS_TOKEN_PREFIX):
            return token
    return ""


def _responsive_selection_for(definition: ComponentDefinition) -> ResponsiveSelection:
    """Mirror the definition's ``ResponsiveContract`` verbatim (§11.2): the
    Layout Engine chooses only among adaptations the registry already
    authorizes, and every component declares exactly one, so this is a
    deterministic copy, never an invented behavior."""
    contract = definition.responsive_contract
    return ResponsiveSelection(
        collapse_behavior=contract.collapse_behavior,
        mobile_order=contract.mobile_order,
        content_priority=contract.content_priority,
        truncation=contract.truncation,
        sticky=contract.sticky,
        table_adaptation=contract.table_adaptation,
        image_behavior=contract.image_behavior,
    )


class LayoutEngine(LayoutEngineInterface):
    """Compose a deterministic ``LayoutPlan`` from a ``ComponentManifest``
    and a ``BrandPackage`` (AES-WEB-001 §5.6; AES-WEB-002 §9.1, §11, §16)."""

    version = ENGINE_VERSIONS["layout_engine"]

    def __init__(self, registry: ComponentRegistryView) -> None:
        self._registry = registry

    def compose(
        self,
        component_manifest: ComponentManifest,
        brand_package: BrandPackage,
    ) -> LayoutPlan:
        """Total function over structurally valid inputs; batch-fails otherwise.

        For every page in ``component_manifest.pages`` (in declared order),
        resolves each component instance's definition from the injected
        registry, assigns it to the first legal ``RegionKind`` in its
        definition's declared ``allowed_parent_regions`` order -- narrowed by
        ``conversion_contract.placement_regions`` when the component declares
        one (§16.1 placement_constraints, e.g. "sticky-mobile only in
        STICKY_MOBILE") -- validates any declared ``conversion_contract``
        repetition limit, and validates any declared grid-columns token
        dependency against ``brand_package.extended_tokens`` (§10.3: an
        unresolvable token is a build failure, never a degraded render).

        Regions are emitted in the fixed semantic ``RegionKind`` declaration
        order (skip, announcement, header, breadcrumb, hero, body,
        sticky-mobile, footer -- AES-WEB-002 §9.1); only regions holding at
        least one component are emitted -- no placeholder components fill
        absent regions. Component order within a region is exactly the
        manifest's own relative order -- never reordered, never renumbered;
        ``component_index`` always names the original position in
        ``page.components``.

        Failures across all pages are collected and reported together
        (batch reporting, not first-failure) as one ``LayoutCompositionError``
        whose diagnostics name every unresolved component, illegal
        placement, repetition-limit violation, and invalid grid reference.
        No partial ``LayoutPlan`` is ever returned when diagnostics exist.

        Determinism: neither input is mutated (both are frozen); page order,
        region order, and component order are pure functions of
        ``component_manifest``'s declared order and each component
        definition's own declared contracts -- never of dict/set iteration
        order (AES-WEB-001 §1.1 replayability contract).
        """
        registry = self._registry

        pages: List[PageLayout] = []
        region_details: List[RegionLayoutDetail] = []
        unresolved: List[Dict[str, Any]] = []
        illegal_placements: List[Dict[str, Any]] = []
        repetition_violations: List[Dict[str, Any]] = []
        invalid_grid: List[Dict[str, Any]] = []

        for page in component_manifest.pages:
            by_region: Dict[
                RegionKind, List[Tuple[int, GridPlacement, ResponsiveSelection]]
            ] = {}
            repetition_counts: Dict[str, int] = {}

            for index, instance in enumerate(page.components):
                try:
                    definition = registry.get(
                        instance.component_id, instance.component_version
                    )
                except ComponentSystemError:
                    unresolved.append(
                        {
                            "route": page.route,
                            "component_index": index,
                            "component_id": instance.component_id,
                            "component_version": instance.component_version,
                            "rule": "component_not_resolvable",
                        }
                    )
                    continue

                conversion = definition.conversion_contract
                legal_regions = list(definition.allowed_parent_regions)
                if conversion is not None and conversion.placement_regions:
                    legal_regions = [
                        region
                        for region in legal_regions
                        if region in conversion.placement_regions
                    ]
                if not legal_regions:
                    illegal_placements.append(
                        {
                            "route": page.route,
                            "component_index": index,
                            "component_id": instance.component_id,
                            "rule": "no_legal_region",
                            "allowed_parent_regions": [
                                r.value for r in definition.allowed_parent_regions
                            ],
                            "conversion_placement_regions": (
                                [r.value for r in conversion.placement_regions]
                                if conversion is not None
                                else []
                            ),
                        }
                    )
                    continue
                region_kind = legal_regions[0]

                if (
                    conversion is not None
                    and conversion.repetition_limit_per_page is not None
                ):
                    occurrence = repetition_counts.get(instance.component_id, 0) + 1
                    repetition_counts[instance.component_id] = occurrence
                    if occurrence > conversion.repetition_limit_per_page:
                        repetition_violations.append(
                            {
                                "route": page.route,
                                "component_index": index,
                                "component_id": instance.component_id,
                                "region": region_kind.value,
                                "rule": "repetition_limit_exceeded",
                                "limit": conversion.repetition_limit_per_page,
                                "occurrence": occurrence,
                            }
                        )
                        continue

                grid_token = _grid_token_for(definition)
                if grid_token and grid_token not in brand_package.extended_tokens:
                    invalid_grid.append(
                        {
                            "route": page.route,
                            "component_index": index,
                            "component_id": instance.component_id,
                            "region": region_kind.value,
                            "rule": "invalid_grid_reference",
                            "grid_token": grid_token,
                        }
                    )
                    continue

                grid = GridPlacement(columns_token=grid_token, column_span=1)
                responsive = _responsive_selection_for(definition)
                by_region.setdefault(region_kind, []).append((index, grid, responsive))

            regions_out: List[LayoutRegion] = []
            for region_kind in RegionKind:
                items = by_region.get(region_kind)
                if not items:
                    continue
                regions_out.append(
                    LayoutRegion(
                        region_id=region_kind.value,
                        component_indexes=tuple(i for i, _, _ in items),
                    )
                )
                region_details.append(
                    RegionLayoutDetail(
                        route=page.route,
                        region_id=region_kind.value,
                        region_kind=region_kind,
                        placements=tuple(
                            ComponentPlacement(
                                component_index=i, grid=grid, responsive=responsive
                            )
                            for i, grid, responsive in items
                        ),
                    )
                )
            pages.append(PageLayout(route=page.route, regions=tuple(regions_out)))

        diagnostics = self._collect_diagnostics(
            unresolved, illegal_placements, repetition_violations, invalid_grid
        )
        if diagnostics:
            raise LayoutCompositionError(
                "LayoutPlan composition failed; see diagnostics",
                stage=STAGE_LAYOUT_COMPOSITION,
                diagnostics=diagnostics,
            )

        return LayoutPlan(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.LAYOUT_PLAN],
            artifact_kind=ArtifactKind.LAYOUT_PLAN,
            source_hashes={
                "component_manifest": artifact_sha256(component_manifest),
                "brand_package": artifact_sha256(brand_package),
                "component_registry": registry.registry_hash(),
            },
            pages=tuple(pages),
            region_details=tuple(region_details),
        )

    @staticmethod
    def _collect_diagnostics(
        unresolved: List[Dict[str, Any]],
        illegal_placements: List[Dict[str, Any]],
        repetition_violations: List[Dict[str, Any]],
        invalid_grid: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Assemble the deterministically ordered, deterministically sorted
        batch-failure diagnostics (empty dict => success)."""
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        if unresolved:
            buckets["unresolved_components"] = sorted(
                unresolved, key=lambda item: (item["route"], item["component_index"])
            )
        if illegal_placements:
            buckets["illegal_placements"] = sorted(
                illegal_placements,
                key=lambda item: (item["route"], item["component_index"]),
            )
        if repetition_violations:
            buckets["repetition_limit_violations"] = sorted(
                repetition_violations,
                key=lambda item: (item["route"], item["component_index"]),
            )
        if invalid_grid:
            buckets["invalid_grid_references"] = sorted(
                invalid_grid, key=lambda item: (item["route"], item["component_index"])
            )
        return {
            key: buckets[key] for key in _DIAGNOSTIC_BUCKET_ORDER if key in buckets
        }

"""ComponentEngine -- (SiteArchitecture, ContentPackage) -> ComponentManifest
(AES-WEB-001 §5.5 / Part 2).

Internal sequencing label: AES-WEB-002J.6. This is the §5.5 pipeline-stage
facade over the machinery earlier waves already built: it maps each
``SiteArchitecture`` page to its PageRole recipe (AES-WEB-002 §26,
``constants.components.RECIPE_SLOTS_BY_PAGE_ROLE``), runs the deterministic
§14.2 selection pipeline (``components.selection.ComponentSelector``) per
page, binds the props it can source deterministically, and assembles a
``ComponentManifest`` (artifact #6) carrying an embedded, size-bounded
``selection_trace`` (§14.3, ADR-14). "It selects commercial components. It
does not render HTML, build layouts, generate CSS, or perform AI inference."

Deterministic, pure, serializable, byte-stable: the same
``(SiteArchitecture, ContentPackage)`` pair always produces the same
``ComponentManifest`` (or the same batch of diagnostics), regardless of
``ContentPackage.blocks`` input order -- content is consumed only for
provenance (``source_hashes``) this wave; see "Binding scope" below. No
network access, no filesystem access, no model calls, no randomness, no
clock/UUID reads. Not wired into pipeline execution -- ``component_resolution``
remains ``NOT_EXECUTED`` in the ``BuildManifest`` (``PHASE1_EXECUTED_STAGES``
is unchanged by this module).

Registry as an injected dependency (§15.3). The registry is a read-only
``ComponentRegistryView``, not an artifact input; ``compile`` takes it as an
optional keyword defaulting to ``build_default_registry()`` so production
uses the real catalog while tests may drive the engine with a reduced fixture
registry. ``compatibility_versions`` and ``lifecycle_flags`` are likewise
injected build configuration (defaults from ``constants.components``); no
component is ACTIVE/PREFERRED yet, so the default flags allow PROPOSED
participation (``DEFAULT_LIFECYCLE_ALLOW_PROPOSED``) without touching any
component's registered ``lifecycle_status`` or §23 certification semantics.

Binding scope (AES-WEB-002J.6, operator-confirmed). §5.5 makes prop binding
the Component Engine's job ("an unbound required prop is a compile error
here"). The catalog's required props fall into two classes:

* Role-derivable ``STR_ENUM`` props whose enum values are exactly PageRole
  values (e.g. ``hero.local.standard.context_role``,
  ``content.intro.contextual.context_role``, ``layout.shell.page.page_role``):
  bound deterministically to the hosting page's role. If a chosen component
  declares such a prop but its enum omits the hosting role, that is a genuine
  compile-time contradiction and raises ``ComponentResolutionError`` -- the
  §5.5 "compile error here, not a render error later" guarantee, realized.
* Value-layer props (``CONTENT_BLOCK_REF``, ``LISTING_REF``, ``ROUTE_REF``,
  ``ASSET_REF``, ``TOKEN_REF``, ``INT_BOUNDED``, ...): their values come from
  a content-slot/block, listing, route-topology, asset, or brand-token
  binding contract that is *not yet authorized* (no mapping between a
  component's declared content-slot names and ``ContentPackage`` block ids
  exists). Per the "no invented metadata / do not guess" doctrine, these are
  left unbound this wave and ``content_refs`` stays empty -- the documented
  deferred surface, mirroring how the SEO Engine (AES-WEB-002J.5) deferred
  structured data. A ``ComponentInstance`` therefore pins the selected
  ``(component_id, component_version)`` plus any role-derived props; the
  chosen variant is recorded in the ``selection_trace`` (§14.3).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.website_generation.constants.components import (
    DEFAULT_COMPATIBILITY_VERSIONS,
    DEFAULT_LIFECYCLE_ALLOW_DEPRECATED,
    DEFAULT_LIFECYCLE_ALLOW_EXPERIMENTAL,
    DEFAULT_LIFECYCLE_ALLOW_PROPOSED,
    RECIPE_SLOTS_BY_PAGE_ROLE,
)
from engines.website_generation.contracts.artifacts import (
    ComponentInstance,
    ComponentManifest,
    ContentPackage,
    PageComponents,
    SelectionTrace,
    SiteArchitecture,
    artifact_sha256,
)
from engines.website_generation.contracts.components import PropSpec
from engines.website_generation.contracts.enums import (
    ArtifactKind,
    CommercialPurpose,
    PageRole,
    PropType,
    RegionKind,
)
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.contracts.interfaces import (
    ComponentEngineInterface,
    ComponentRegistryView,
)
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)
from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.components.selection import (
    ComponentSelector,
    LifecycleBuildFlags,
    SlotSelectionRequest,
)

# Every PageRole value, precomputed once. A required STR_ENUM prop whose enum
# is a subset of these is "role-typed" and deterministically bindable to the
# hosting page's role (see the module docstring's "Binding scope").
_PAGE_ROLE_VALUES = frozenset(role.value for role in PageRole)

# The route/slot delimiter used to qualify a recipe slot id with its page
# route inside the aggregated ``selection_trace`` (§14.3). ``ComponentManifest``
# embeds a single flat ``SelectionTrace`` across all pages, so bare recipe
# slot ids (``"hero"`` appears on many roles) would be ambiguous; qualifying
# them keeps §14.3's "why this component, this variant, on this page"
# answerable from the manifest alone. ``#`` never appears in a route or a
# recipe slot id, so the qualification is unambiguous and reversible.
_TRACE_SLOT_DELIMITER = "#"

# Fixed diagnostics key order (readability/debugging only -- dict equality
# does not depend on key order), mirroring seo_engine._DIAGNOSTIC_BUCKET_ORDER.
_DIAGNOSTIC_BUCKET_ORDER = (
    "unsupported_page_roles",
    "unresolved_required_slots",
    "unbindable_required_props",
)


class _UnbindableRoleProp(Exception):
    """Internal: a chosen component declares a role-typed required prop whose
    enum omits the hosting page role (§5.5 compile error). Never escapes the
    module -- converted into a batched ``ComponentResolutionError`` diagnostic."""

    def __init__(self, prop_name: str) -> None:
        super().__init__(prop_name)
        self.prop_name = prop_name


def _is_role_typed(spec: PropSpec) -> bool:
    """True when ``spec`` is a ``STR_ENUM`` whose values are all PageRole
    values -- the only class of required prop this wave binds (deterministic,
    derived from the hosting page role; see the module docstring)."""
    return (
        spec.prop_type is PropType.STR_ENUM
        and bool(spec.enum_values)
        and set(spec.enum_values) <= _PAGE_ROLE_VALUES
    )


class ComponentEngine(ComponentEngineInterface):
    """Compile a deterministic ``ComponentManifest`` from a ``SiteArchitecture``
    and ``ContentPackage`` (AES-WEB-001 §5.5; AES-WEB-002 §14, §26)."""

    version = ENGINE_VERSIONS["component_engine"]

    def compile(
        self,
        site_architecture: SiteArchitecture,
        content_package: ContentPackage,
        *,
        registry: Optional[ComponentRegistryView] = None,
        compatibility_versions: Optional[Dict[str, str]] = None,
        lifecycle_flags: Optional[LifecycleBuildFlags] = None,
    ) -> ComponentManifest:
        """Total function over structurally valid inputs; batch-fails otherwise.

        For every page in ``site_architecture`` (in declared order), resolves
        the page's PageRole recipe (§26), runs the §14.2 selection pipeline,
        binds role-derivable props, and emits its ``PageComponents``. All
        per-page selection traces aggregate into the manifest's single
        ``selection_trace`` (§14.3), with each slot id qualified by its page
        route. Failures across all pages are collected and reported together
        (batch reporting, not first-failure) as one ``ComponentResolutionError``
        whose diagnostics name every unsupported role, unresolved required
        slot, and unbindable required prop.

        Determinism: neither input is mutated (both are frozen); page order,
        slot order, selection, and binding are pure functions of
        ``site_architecture``'s declared page order and each page's recipe --
        never of ``content_package.blocks`` order (AES-WEB-001 §1.1
        replayability contract).
        """
        registry = registry if registry is not None else build_default_registry()
        compatibility = (
            dict(compatibility_versions)
            if compatibility_versions is not None
            else dict(DEFAULT_COMPATIBILITY_VERSIONS)
        )
        flags = (
            lifecycle_flags
            if lifecycle_flags is not None
            else LifecycleBuildFlags(
                allow_proposed=DEFAULT_LIFECYCLE_ALLOW_PROPOSED,
                allow_experimental=DEFAULT_LIFECYCLE_ALLOW_EXPERIMENTAL,
                allow_deprecated=DEFAULT_LIFECYCLE_ALLOW_DEPRECATED,
            )
        )
        selector = ComponentSelector()

        page_components: List[PageComponents] = []
        trace_slots: List[Any] = []
        unsupported: List[Dict[str, str]] = []
        unresolved: List[Dict[str, Any]] = []
        unbindable: List[Dict[str, str]] = []

        for page in site_architecture.pages:
            recipe = RECIPE_SLOTS_BY_PAGE_ROLE.get(page.page_type)
            if recipe is None:
                unsupported.append(
                    {"route": page.route, "page_type": page.page_type}
                )
                continue
            role = PageRole(page.page_type)  # key existed => valid role value
            requests = [self._slot_request(page.route, slot) for slot in recipe]

            try:
                trace = selector.select(
                    registry,
                    requests,
                    compatibility_versions=compatibility,
                    lifecycle_flags=flags,
                    available_asset_roles=(),
                )
            except ComponentResolutionError as exc:
                unresolved.append({"route": page.route, "diagnostics": exc.diagnostics})
                continue

            trace_slots.extend(trace.slots)
            instances: List[ComponentInstance] = []
            for slot_trace in trace.slots:
                if not slot_trace.chosen_component_id:
                    continue  # optional slot dropped, silently but traced (§26)
                try:
                    props = self._bind_role_props(
                        registry, slot_trace.chosen_component_id, role
                    )
                except _UnbindableRoleProp as ub:
                    unbindable.append(
                        {
                            "route": page.route,
                            "slot_id": slot_trace.slot_id,
                            "component_id": slot_trace.chosen_component_id,
                            "prop": ub.prop_name,
                        }
                    )
                    continue
                instances.append(
                    ComponentInstance(
                        component_id=slot_trace.chosen_component_id,
                        component_version=slot_trace.chosen_component_version,
                        props=props,
                        content_refs=(),  # value-layer binding deferred (docstring)
                    )
                )
            page_components.append(
                PageComponents(route=page.route, components=tuple(instances))
            )

        diagnostics = self._collect_diagnostics(unsupported, unresolved, unbindable)
        if diagnostics:
            raise ComponentResolutionError(
                "ComponentManifest compilation failed; see diagnostics",
                stage="component_resolution",
                diagnostics=diagnostics,
            )

        return ComponentManifest(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST],
            artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
            source_hashes={
                "site_architecture": artifact_sha256(site_architecture),
                "content_package": artifact_sha256(content_package),
            },
            pages=tuple(page_components),
            selection_trace=SelectionTrace(slots=tuple(trace_slots)),
        )

    @staticmethod
    def _slot_request(route: str, slot: Dict[str, Any]) -> SlotSelectionRequest:
        """Build one ``SlotSelectionRequest`` from a recipe slot dict (§26),
        qualifying the slot id with its page route for the aggregated trace.

        Enum coercion mirrors the established recipe-resolution pattern:
        empty ``purpose``/``required_region`` strings become ``None``; every
        other value is a valid enum member (guaranteed by the recipe-table
        tests). ``required_slot_names`` may carry the unbuilt-family sentinel
        tuple verbatim -- the selector's slot-signature check eliminates it,
        dropping the (optional) slot exactly as intended."""
        return SlotSelectionRequest(
            slot_id="%s%s%s" % (route, _TRACE_SLOT_DELIMITER, slot["slot_id"]),
            page_role=PageRole(slot["page_role"]),
            purpose=(
                CommercialPurpose(slot["purpose"]) if slot["purpose"] else None
            ),
            required_region=(
                RegionKind(slot["required_region"])
                if slot["required_region"]
                else None
            ),
            required_prop_names=tuple(slot["required_prop_names"]),
            required_slot_names=tuple(slot["required_slot_names"]),
            monetization_eligible=slot["monetization_eligible"],
            fallback_component_id=slot["fallback_component_id"],
            required=slot["required"],
        )

    @staticmethod
    def _bind_role_props(
        registry: ComponentRegistryView, component_id: str, role: PageRole
    ) -> Dict[str, str]:
        """Bind the chosen component's role-derivable required props to the
        hosting page role (§5.5). Value-layer required props are left unbound
        this wave (deferred; see the module docstring). Raises
        :class:`_UnbindableRoleProp` when a role-typed required prop's enum
        omits ``role`` -- the §5.5 compile-time contradiction.

        Iterates ``required_props`` in declared order; the returned dict's key
        order does not affect the manifest hash (canonical serialization sorts
        keys), so binding is order-independent and deterministic."""
        definition = registry.get(component_id)
        props: Dict[str, str] = {}
        for name, spec in definition.required_props.items():
            if not _is_role_typed(spec):
                continue
            if role.value not in spec.enum_values:
                raise _UnbindableRoleProp(name)
            props[name] = role.value
        return props

    @staticmethod
    def _collect_diagnostics(
        unsupported: List[Dict[str, str]],
        unresolved: List[Dict[str, Any]],
        unbindable: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Assemble the deterministically ordered, deterministically sorted
        batch-failure diagnostics (empty dict => success)."""
        diagnostics: Dict[str, Any] = {}
        if unsupported:
            diagnostics["unsupported_page_roles"] = sorted(
                unsupported, key=lambda item: item["route"]
            )
        if unresolved:
            diagnostics["unresolved_required_slots"] = sorted(
                unresolved, key=lambda item: item["route"]
            )
        if unbindable:
            diagnostics["unbindable_required_props"] = sorted(
                unbindable,
                key=lambda item: (item["route"], item["slot_id"], item["prop"]),
            )
        return {
            key: diagnostics[key]
            for key in _DIAGNOSTIC_BUCKET_ORDER
            if key in diagnostics
        }

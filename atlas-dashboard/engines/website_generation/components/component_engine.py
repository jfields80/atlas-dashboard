"""ComponentEngine -- (SiteArchitecture, ContentPackage, ListingDataset?,
BrandPackage?) -> ComponentCompilationResult (AES-WEB-001 §5.5 / Part 2;
AES-WEB-002J.19 Phase B; ADR-WEB-CONTENT-BINDING-MAP).

Internal sequencing label: AES-WEB-002J.6 (Phase A: selection) +
AES-WEB-002J.19 (Phase B: value binding). This is the §5.5 pipeline-stage
facade over the machinery earlier waves already built: it maps each
``SiteArchitecture`` page to its PageRole recipe (AES-WEB-002 §26,
``constants.components.RECIPE_SLOTS_BY_PAGE_ROLE``), runs the deterministic
§14.2 selection pipeline (``components.selection.ComponentSelector``) --
extended by J.19 with an additive bindability-filtering step -- per page,
then binds every honestly-bindable required prop and content slot (J.19
Phase B, via the J.18 declarative map: ``components.binding_rules``,
``components.value_binding``, ``components.content_projection``), and
assembles a ``ComponentCompilationResult`` bundling the bound
``ComponentManifest`` (artifact #6, carrying an embedded, size-bounded
``selection_trace``, §14.3/ADR-14) with its companion ``ContentPackage``
(original blocks plus every Phase-B-projected block). "It selects and binds
commercial components. It does not render HTML, build layouts, generate
CSS, or perform AI inference."

Deterministic, pure, serializable, byte-stable: the same
``(SiteArchitecture, ContentPackage, ListingDataset, BrandPackage)`` tuple
always produces the same ``ComponentCompilationResult`` (or the same batch
of diagnostics). No network access, no filesystem access, no model calls,
no randomness, no clock/UUID reads. Not wired into pipeline execution --
``component_resolution`` remains ``NOT_EXECUTED`` in the ``BuildManifest``
(``PHASE1_EXECUTED_STAGES`` is unchanged by this module).

Registry as an injected dependency (§15.3). The registry is a read-only
``ComponentRegistryView``, not an artifact input; ``compile`` takes it as an
optional keyword defaulting to ``build_default_registry()`` so production
uses the real catalog while tests may drive the engine with a reduced fixture
registry. ``compatibility_versions`` and ``lifecycle_flags`` are likewise
injected build configuration (defaults from ``constants.components``); no
component is ACTIVE/PREFERRED yet, so the default flags allow PROPOSED
participation (``DEFAULT_LIFECYCLE_ALLOW_PROPOSED``) without touching any
component's registered ``lifecycle_status`` or §23 certification semantics.

Binding scope (AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "Option A
deferred" scope). §5.5 makes prop *and content* binding the Component
Engine's job ("an unbound required prop is a compile error here"). Every
required field's binding is now resolved from the J.18 declarative map:

* **Bindability-aware selection (Phase A extension)**: a candidate whose
  required fields include one categorically ``STRUCTURED_DEFERRED`` or
  ``SOURCE_UNAVAILABLE`` binding state (``binding_rules.
  is_categorically_bindable``) is eliminated before scoring -- never
  silently bound with a fabricated value, and never a component the
  Renderer would later reject. A required recipe slot with no bindable
  candidate *and* no bindable fallback still raises ``ComponentResolutionError``
  honestly (§26 doctrine, unchanged).
* **Phase B**: for every finally-selected instance, every required prop
  (literal, via ``value_binding``; or a content reference, via
  ``content_projection``) and every required content slot is bound to a
  real value or the whole compile batch-fails -- Phase B never changes
  *which* components were selected, never picks its own fallback, never
  reorders, and never synthesizes extra instances (that remains Phase A's
  exclusive concern).

Batch-fail-only (§5.10 "no partial output" doctrine, extended to this
engine): if any page fails to resolve its recipe, or any selected instance
fails to bind any required field, **no** ``ComponentCompilationResult`` is
ever returned -- one ``ComponentResolutionError`` names every failure across
every page in one deterministic, sorted diagnostics dict.

Repetition (AES-WEB-002J.20; ADR-WEB-CONTENT-BINDING-MAP). A third step sits
between Phase A and Phase B: once a recipe slot's component definition is
selected, ``components.composition_rules.repetition_rule_for(page_role,
recipe_slot_id)`` decides whether it is emitted once (no rule -- the J.19
default, unchanged byte-for-byte) or expanded into one concrete instance per
matching ``ListingRecord`` (a rule present). Expansion never changes *which*
definition Phase A chose, never invents a fallback, and never touches
Layout/Renderer, which remain unaware repetition exists -- they see only the
resulting flat, ordered list of ``ComponentInstance``s, exactly as they
already handle any other multi-instance page. Each expanded instance is
bound independently in Phase B against its own assigned listing (never a
shared, route-wide assignment); one repeated item's binding failure
batch-fails the whole compile, same as any other instance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from engines.website_generation.constants.components import (
    DEFAULT_COMPATIBILITY_VERSIONS,
    DEFAULT_LIFECYCLE_ALLOW_DEPRECATED,
    DEFAULT_LIFECYCLE_ALLOW_EXPERIMENTAL,
    DEFAULT_LIFECYCLE_ALLOW_PROPOSED,
    RECIPE_SLOTS_BY_PAGE_ROLE,
)
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    ComponentCompilationResult,
    ComponentInstance,
    ComponentManifest,
    ContentPackage,
    ListingDataset,
    ListingRecord,
    PageComponents,
    SelectionTrace,
    SiteArchitecture,
    artifact_sha256,
)
from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.contracts.enums import (
    ArtifactKind,
    CommercialPurpose,
    ListingKind,
    PageRole,
    PropType,
    RegionKind,
)
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.contracts.interfaces import (
    ComponentEngineInterface,
    ComponentRegistryView,
)
from engines.website_generation.contracts.render_data import (
    RENDER_DATA_VERSION,
    ComponentRenderData,
    ContactData,
    HoursData,
    HoursRow,
    LinkSpec,
    ListingCardData,
    NavigationData,
    RenderDataBundle,
    RenderDataEntry,
    generated_render_data_key,
    is_safe_url,
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
from engines.website_generation.components.binding_rules import (
    BINDING_MAP_VERSION,
    BINDING_RULES_BY_KEY,
    BindingState,
    FieldKind,
    is_categorically_bindable,
)
from engines.website_generation.components.composition_rules import (
    COMPOSITION_RULES_VERSION,
    RepetitionRule,
    repetition_rule_for,
)
from engines.website_generation.components.value_binding import (
    UnboundLiteralProp,
    bind_literal_prop,
)
from engines.website_generation.components.content_projection import (
    ProjectedSlotCollision,
    ProjectionAccumulator,
    RouteScope,
    UnboundContentField,
    assign_listing,
    bind_content_slot,
    bind_ref_prop,
    listing_route,
    resolve_route_scope,
)

# The route/slot delimiter used to qualify a recipe slot id with its page
# route inside the aggregated ``selection_trace`` (§14.3). ``ComponentManifest``
# embeds a single flat ``SelectionTrace`` across all pages, so bare recipe
# slot ids (``"hero"`` appears on many roles) would be ambiguous; qualifying
# them keeps §14.3's "why this component, this variant, on this page"
# answerable from the manifest alone. ``#`` never appears in a route or a
# recipe slot id, so the qualification is unambiguous and reversible.
_TRACE_SLOT_DELIMITER = "#"

# Prop types whose bound value is a content-reference slot id rather than a
# literal string (§8.1) -- resolved via content_projection, never
# value_binding.
_REF_PROP_TYPES = frozenset({PropType.CONTENT_BLOCK_REF, PropType.LISTING_REF})

# Fixed diagnostics key order (readability/debugging only -- dict equality
# does not depend on key order), mirroring seo_engine._DIAGNOSTIC_BUCKET_ORDER.
_DIAGNOSTIC_BUCKET_ORDER = (
    "unsupported_page_roles",
    "unresolved_required_slots",
    "unbindable_required_props",
    "unbindable_required_content",
    "projected_slot_collisions",
    "repetition_failures",
    "render_data_failures",
)

# AES-WEB-002K.1: the component ids the render-data producer knows how to
# enrich. A plain, explicit dispatch (no "listing.*"/"nav.*" prefix
# inference, per the composition_rules.py "no invented metadata" precedent)
# -- Wave 1's exact, narrow scope, nothing more.
_NAV_RENDER_DATA_COMPONENT_IDS = frozenset({"nav.header.standard", "legal.footer.directory"})
_CARD_RENDER_DATA_COMPONENT_IDS = frozenset({"listing.card.standard", "listing.row.compact"})
_CONTACT_RENDER_DATA_COMPONENT_ID = "profile.contact.panel"
_HOURS_RENDER_DATA_COMPONENT_ID = "profile.hours.table"

_WEEKDAY_ORDER: Tuple[str, ...] = (
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY",
)
_WEEKDAY_LABEL: Dict[str, str] = {
    "MONDAY": "Monday", "TUESDAY": "Tuesday", "WEDNESDAY": "Wednesday",
    "THURSDAY": "Thursday", "FRIDAY": "Friday", "SATURDAY": "Saturday", "SUNDAY": "Sunday",
}

# ListingKind -> human badge label (AES-WEB-002K.1 D6 "badge" allowlist
# entry). ORGANIC carries no badge at all (the default, unmarked case) --
# never invented for a kind this table doesn't name.
_BADGE_LABELS: Dict[str, str] = {
    ListingKind.FEATURED.value: "Featured",
    ListingKind.SPONSORED.value: "Sponsored",
    ListingKind.VERIFIED.value: "Verified",
    ListingKind.EDITORIAL_PICK.value: "Editorial Pick",
    ListingKind.RANKED.value: "Ranked",
    ListingKind.CURATED.value: "Curated",
    ListingKind.RECENTLY_ADDED.value: "Recently Added",
    ListingKind.INCOMPLETE.value: "Incomplete",
}


class ComponentEngine(ComponentEngineInterface):
    """Compile a deterministic ``ComponentCompilationResult`` from a
    ``SiteArchitecture``, ``ContentPackage``, and the optional
    ``ListingDataset``/``BrandPackage`` Phase-B binding inputs
    (AES-WEB-001 §5.5; AES-WEB-002 §14, §26; AES-WEB-002J.19)."""

    version = ENGINE_VERSIONS["component_engine"]

    def compile(
        self,
        site_architecture: SiteArchitecture,
        content_package: ContentPackage,
        listing_dataset: Optional[ListingDataset] = None,
        brand_package: Optional[BrandPackage] = None,
        *,
        registry: Optional[ComponentRegistryView] = None,
        compatibility_versions: Optional[Dict[str, str]] = None,
        lifecycle_flags: Optional[LifecycleBuildFlags] = None,
    ) -> ComponentCompilationResult:
        """Total function over structurally valid inputs; batch-fails otherwise.

        For every page in ``site_architecture`` (in declared order), resolves
        the page's PageRole recipe (§26), runs the bindability-aware §14.2
        selection pipeline, binds every required prop and content slot for
        each selected instance (Phase B), and emits its ``PageComponents``.
        All per-page selection traces aggregate into the manifest's single
        ``selection_trace`` (§14.3), with each slot id qualified by its page
        route. Failures across all pages and all instances are collected and
        reported together (batch reporting, not first-failure) as one
        ``ComponentResolutionError``.

        Determinism: no input is mutated (all are frozen); page order, slot
        order, selection, and binding are pure functions of
        ``site_architecture``'s declared page order, each page's recipe, and
        the supplied ``content_package``/``listing_dataset``/``brand_package``
        contents -- never of ``content_package.blocks`` input order
        (AES-WEB-001 §1.1 replayability contract).
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
        content_index = self._build_content_index(content_package)
        projection = ProjectionAccumulator()

        page_components: List[PageComponents] = []
        trace_slots: List[Any] = []
        unsupported: List[Dict[str, str]] = []
        unresolved: List[Dict[str, Any]] = []
        unbindable_props: List[Dict[str, str]] = []
        unbindable_content: List[Dict[str, str]] = []
        collisions: List[Dict[str, str]] = []
        repetition_failures: List[Dict[str, str]] = []
        render_data_failures: List[Dict[str, str]] = []
        render_data_entries: List[RenderDataEntry] = []

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
                    bindability_check=is_categorically_bindable,
                )
            except ComponentResolutionError as exc:
                unresolved.append({"route": page.route, "diagnostics": exc.diagnostics})
                continue

            trace_slots.extend(trace.slots)
            route_scope = resolve_route_scope(page.route, listing_dataset)
            instances: List[ComponentInstance] = []
            for slot, slot_trace in zip(recipe, trace.slots):
                if not slot_trace.chosen_component_id:
                    continue  # optional slot dropped, silently but traced (§26)
                definition = registry.get(
                    slot_trace.chosen_component_id, slot_trace.chosen_component_version
                )

                rule = repetition_rule_for(role.value, slot["slot_id"])
                if rule is None:
                    # No repetition rule for this recipe slot: exactly the
                    # J.19 single-instance path, unchanged byte-for-byte.
                    assignments: List[Optional[ListingRecord]] = [None]
                else:
                    matches = self._resolve_repetition_matches(
                        rule, route_scope, listing_dataset
                    )
                    if matches is None:
                        repetition_failures.append({
                            "route": page.route,
                            "component_id": slot_trace.chosen_component_id,
                            "recipe_slot_id": slot["slot_id"],
                            "reason": (
                                "repeat_scope_unresolved: no category resolved "
                                "for route %r" % page.route
                            ),
                        })
                        continue
                    if len(matches) < rule.min_items:
                        repetition_failures.append({
                            "route": page.route,
                            "component_id": slot_trace.chosen_component_id,
                            "recipe_slot_id": slot["slot_id"],
                            "reason": (
                                "no_matching_items: %d matched, minimum %d required"
                                % (len(matches), rule.min_items)
                            ),
                        })
                        continue
                    if rule.max_items is not None and len(matches) > rule.max_items:
                        repetition_failures.append({
                            "route": page.route,
                            "component_id": slot_trace.chosen_component_id,
                            "recipe_slot_id": slot["slot_id"],
                            "reason": (
                                "repeat_limit_exceeded: %d matched, maximum %d allowed"
                                % (len(matches), rule.max_items)
                            ),
                        })
                        continue
                    # RepetitionOrdering.DATASET_ORDER: ListingDataset tuple
                    # order preserved verbatim -- never re-sorted (§7/ADR-
                    # WEB-LISTING-DATASET "producers sort, artifacts preserve").
                    assignments = list(matches)

                for assigned_listing in assignments:
                    component_index = len(instances)
                    props, content_refs, failures = self._bind_instance(
                        definition,
                        role=role,
                        route=page.route,
                        component_index=component_index,
                        site_architecture=site_architecture,
                        content_index=content_index,
                        listing_dataset=listing_dataset,
                        brand_package=brand_package,
                        route_scope=route_scope,
                        projection=projection,
                        assigned_listing=assigned_listing,
                    )
                    for failure in failures:
                        bucket, entry = failure
                        entry = dict(entry)
                        entry["route"] = page.route
                        if bucket == "prop":
                            unbindable_props.append(entry)
                        elif bucket == "content":
                            unbindable_content.append(entry)
                        else:
                            collisions.append(entry)
                    if failures:
                        continue
                    instances.append(
                        ComponentInstance(
                            component_id=slot_trace.chosen_component_id,
                            component_version=slot_trace.chosen_component_version,
                            props=props,
                            content_refs=tuple(content_refs),
                        )
                    )
                    render_data, render_data_failure = self._produce_render_data(
                        definition,
                        route=page.route,
                        site_architecture=site_architecture,
                        listing_dataset=listing_dataset,
                        route_scope=route_scope,
                        assigned_listing=assigned_listing,
                    )
                    if render_data_failure is not None:
                        entry = dict(render_data_failure)
                        entry["route"] = page.route
                        entry["component_id"] = definition.component_id
                        render_data_failures.append(entry)
                    elif render_data is not None:
                        render_data_entries.append(
                            RenderDataEntry(
                                route=page.route,
                                component_index=component_index,
                                data=render_data,
                            )
                        )
            page_components.append(
                PageComponents(route=page.route, components=tuple(instances))
            )

        diagnostics = self._collect_diagnostics(
            unsupported, unresolved, unbindable_props, unbindable_content,
            collisions, repetition_failures, render_data_failures,
        )
        if diagnostics:
            raise ComponentResolutionError(
                "ComponentManifest compilation failed; see diagnostics",
                stage="component_resolution",
                diagnostics=diagnostics,
            )

        source_hashes = {
            "site_architecture": artifact_sha256(site_architecture),
            "content_package": artifact_sha256(content_package),
            "binding_map_version": BINDING_MAP_VERSION,
            "composition_rules_version": COMPOSITION_RULES_VERSION,
            "render_data_version": RENDER_DATA_VERSION,
        }
        if listing_dataset is not None:
            source_hashes["listing_dataset"] = artifact_sha256(listing_dataset)
        if brand_package is not None:
            source_hashes["brand_package"] = artifact_sha256(brand_package)

        manifest = ComponentManifest(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST],
            artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
            source_hashes=source_hashes,
            pages=tuple(page_components),
            selection_trace=SelectionTrace(slots=tuple(trace_slots)),
        )
        augmented_content = ContentPackage(
            schema_version=content_package.schema_version,
            artifact_kind=content_package.artifact_kind,
            source_hashes=content_package.source_hashes,
            blocks=content_package.blocks + projection.blocks(),
        )
        return ComponentCompilationResult(
            component_manifest=manifest,
            content_package=augmented_content,
            render_data=RenderDataBundle(entries=tuple(render_data_entries)),
        )

    # -- Phase B: one instance's full binding attempt -----------------------

    @staticmethod
    def _bind_instance(
        definition: ComponentDefinition,
        *,
        role: PageRole,
        route: str,
        component_index: int,
        site_architecture: SiteArchitecture,
        content_index: Dict[Tuple[str, str], Tuple[str, ...]],
        listing_dataset: Optional[ListingDataset],
        brand_package: Optional[BrandPackage],
        route_scope,
        projection: ProjectionAccumulator,
        assigned_listing: Optional[ListingRecord] = None,
    ) -> Tuple[Dict[str, str], List[str], List[Tuple[str, Dict[str, str]]]]:
        """Bind every required prop and content slot of one selected
        instance. Returns ``(props, content_refs, failures)`` --
        ``failures`` is empty on success; the caller discards ``props``/
        ``content_refs`` and records each failure when non-empty (batch
        discipline: a partially-bound instance never becomes a
        ``ComponentInstance``).

        ``assigned_listing`` (AES-WEB-002J.20 repetition) is threaded to
        every ``LISTING_REF``/``CONTENT_BLOCK_REF`` prop binding, taking
        precedence there over the J.19 route-scope fallback -- this is what
        lets each expanded instance bind to its own record. ``None`` (every
        non-repeated call site) reproduces J.19 behavior exactly."""
        props: Dict[str, str] = {}
        content_refs: List[str] = []
        failures: List[Tuple[str, Dict[str, str]]] = []

        for name, spec in sorted(definition.required_props.items()):
            is_ref = spec.prop_type in _REF_PROP_TYPES
            field_kind = FieldKind.PROP_REF if is_ref else FieldKind.PROP_LITERAL
            rule = BINDING_RULES_BY_KEY.get(
                (definition.component_id, field_kind.value, name)
            )
            if rule is None:
                failures.append((
                    "prop",
                    {
                        "component_id": definition.component_id,
                        "prop": name,
                        "reason": "unmapped_binding_rule: no J.18 rule for this field",
                    },
                ))
                continue
            if rule.binding_state is BindingState.RENDER_DATA:
                # AES-WEB-002K.1: the real value lives in the RenderDataBundle
                # this instance's (route, component_index) key produces
                # (this compile() call's own render-data producer, invoked
                # by the caller right after this instance is appended) --
                # never a ContentPackage-resolvable slot id. The prop is
                # bound to a stable, deterministic, positional key purely so
                # every required prop has *some* value (never a JSON string,
                # never structured data inside props); the Renderer
                # recognizes the "render:" prefix and skips the
                # ContentPackage-lookup/missing-content check for it.
                props[name] = generated_render_data_key(rule.semantic_slot, component_index)
                continue
            try:
                if is_ref:
                    value = bind_ref_prop(
                        rule, name, route, component_index,
                        content_index=content_index,
                        listing_dataset=listing_dataset,
                        route_scope=route_scope,
                        projection=projection,
                        assigned_listing=assigned_listing,
                    )
                else:
                    value = bind_literal_prop(
                        rule, spec,
                        role=role, route=route,
                        site_architecture=site_architecture,
                        brand_package=brand_package,
                    )
                props[name] = value
            except (UnboundLiteralProp, UnboundContentField) as exc:
                failures.append((
                    "prop",
                    {
                        "component_id": definition.component_id,
                        "prop": name,
                        "reason": exc.reason,
                    },
                ))
            except ProjectedSlotCollision as exc:
                failures.append((
                    "collision",
                    {"component_id": definition.component_id, "slot_id": exc.slot_id},
                ))

        for slot_name, slot_spec in sorted(definition.required_content_slots.items()):
            rule = BINDING_RULES_BY_KEY.get(
                (definition.component_id, FieldKind.CONTENT_SLOT.value, slot_name)
            )
            if rule is None:
                failures.append((
                    "content",
                    {
                        "component_id": definition.component_id,
                        "slot": slot_name,
                        "reason": "unmapped_binding_rule: no J.18 rule for this field",
                    },
                ))
                continue
            try:
                token = bind_content_slot(
                    rule, slot_name, route,
                    content_index=content_index,
                    listing_dataset=listing_dataset,
                    route_scope=route_scope,
                    projection=projection,
                )
                content_refs.append(token)
            except UnboundContentField as exc:
                failures.append((
                    "content",
                    {
                        "component_id": definition.component_id,
                        "slot": slot_name,
                        "reason": exc.reason,
                    },
                ))
            except ProjectedSlotCollision as exc:
                failures.append((
                    "collision",
                    {"component_id": definition.component_id, "slot_id": exc.slot_id},
                ))

        return props, content_refs, failures

    # -- Render-data production (AES-WEB-002K.1) -----------------------------
    #
    # Pure projections of the same inputs Phase B already has in hand
    # (SiteArchitecture, ListingDataset, route_scope, assigned_listing) into
    # the typed contracts/render_data.py shapes the Renderer/emitters need
    # for real hyperlinks and enriched listing cards. Dispatched by
    # component_id, not by prefix/family inference (the composition_rules.py
    # "no invented metadata" precedent) -- exactly the narrow Wave 1 set:
    # nav.header.standard/legal.footer.directory (navigation),
    # listing.card.standard/listing.row.compact (card enrichment),
    # profile.contact.panel (contact), profile.hours.table (hours). Every
    # other component_id produces no render data at all (``(None, None)``).
    #
    # Returns ``(ComponentRenderData_or_None, failure_or_None)`` -- a
    # failure (unsafe URL, unresolvable category) batch-fails the whole
    # compile via the ``render_data_failures`` diagnostics bucket, exactly
    # like every other Phase-B failure mode; a missing *optional* value
    # (no rating, no CTA, no hours) is never a failure, only an omission
    # (D6 allowlist).

    @classmethod
    def _produce_render_data(
        cls,
        definition: ComponentDefinition,
        *,
        route: str,
        site_architecture: SiteArchitecture,
        listing_dataset: Optional[ListingDataset],
        route_scope: RouteScope,
        assigned_listing: Optional[ListingRecord],
    ) -> Tuple[Optional[ComponentRenderData], Optional[Dict[str, str]]]:
        cid = definition.component_id
        if cid in _NAV_RENDER_DATA_COMPONENT_IDS:
            return ComponentRenderData(nav=cls._build_navigation_data(site_architecture)), None
        if cid in _CARD_RENDER_DATA_COMPONENT_IDS:
            return cls._build_card_data(assigned_listing, listing_dataset)
        if cid in (_CONTACT_RENDER_DATA_COMPONENT_ID, _HOURS_RENDER_DATA_COMPONENT_ID):
            listing = (
                assigned_listing
                if assigned_listing is not None
                else assign_listing(route_scope, listing_dataset)
            )
            if cid == _CONTACT_RENDER_DATA_COMPONENT_ID:
                return cls._build_contact_data(listing)
            return cls._build_hours_data(listing), None
        return None, None

    @staticmethod
    def _build_navigation_data(site_architecture: SiteArchitecture) -> NavigationData:
        """One ``LinkSpec`` per ``nav_routes`` entry with a real, non-empty
        page title -- routes with no title (``PagePlan.title == ""``, the
        pre-K.1 default many hand-built fixtures still use) are silently
        omitted, never rendered with a raw route string as the label. Never
        fails: an empty or partially-titled ``nav_routes`` yields a
        shorter-than-expected but honest ``NavigationData``, not a compile
        error -- this is what keeps every pre-K.1 SiteArchitecture fixture
        still compiling. Header and footer navigation share this exact same
        link set in Wave 1 (no trust/editorial routes exist yet to
        differentiate them, per the K.1 preflight)."""
        title_by_route = {page.route: page.title for page in site_architecture.pages}
        links = tuple(
            LinkSpec(label=title_by_route[route], href=route, external=False)
            for route in site_architecture.nav_routes
            if title_by_route.get(route, "").strip()
        )
        return NavigationData(links=links)

    @staticmethod
    def _build_card_data(
        assigned_listing: Optional[ListingRecord],
        listing_dataset: Optional[ListingDataset],
    ) -> Tuple[Optional[ComponentRenderData], Optional[Dict[str, str]]]:
        if assigned_listing is None or listing_dataset is None:
            # Unreachable in Wave 1's real recipes (listing.card.standard/
            # listing.row.compact are only ever instantiated through a J.20
            # repetition rule, which always supplies assigned_listing) --
            # graceful no-op rather than a crash if that ever changes.
            return None, None
        categories_by_id = {c.category_id: c for c in listing_dataset.categories}
        category = categories_by_id.get(assigned_listing.category_id)
        if category is None:
            return None, {
                "reason": (
                    "missing_category: listing %r names category_id %r, "
                    "not present in ListingDataset.categories"
                    % (assigned_listing.listing_id, assigned_listing.category_id)
                ),
            }
        profile_href = listing_route(category, assigned_listing)

        area_label = ""
        if assigned_listing.address is not None and assigned_listing.address.city:
            area_label = assigned_listing.address.city
            if assigned_listing.address.state:
                area_label = "%s, %s" % (area_label, assigned_listing.address.state)

        rating_text = ""
        review_count: Optional[int] = None
        if assigned_listing.rating is not None:
            whole, remainder = divmod(assigned_listing.rating.rating_hundredths, 100)
            rating_text = "%d.%d" % (whole, remainder // 10)
            review_count = assigned_listing.rating.review_count

        badge_label = _BADGE_LABELS.get(assigned_listing.listing_kind.value, "")
        badge_kind = assigned_listing.listing_kind.value.lower() if badge_label else ""

        cta: Optional[LinkSpec] = None
        if assigned_listing.cta is not None and assigned_listing.cta.label and assigned_listing.cta.target_route:
            target = assigned_listing.cta.target_route
            if not is_safe_url(target):
                return None, {
                    "reason": "unsafe_url: listing %r cta.target_route %r is unsafe"
                    % (assigned_listing.listing_id, target),
                }
            external = target.startswith("http://") or target.startswith("https://")
            cta = LinkSpec(
                label=assigned_listing.cta.label, href=target, external=external,
                rel="noopener" if external else "",
            )

        card = ListingCardData(
            listing_id=assigned_listing.listing_id,
            name=assigned_listing.business_name,
            profile_href=profile_href,
            area_label=area_label,
            rating_text=rating_text,
            review_count=review_count,
            badge_kind=badge_kind,
            badge_label=badge_label,
            cta=cta,
        )
        return ComponentRenderData(card=card), None

    @staticmethod
    def _build_contact_data(
        listing: Optional[ListingRecord],
    ) -> Tuple[Optional[ComponentRenderData], Optional[Dict[str, str]]]:
        if listing is None:
            return None, None

        address_text = ""
        if listing.address is not None:
            parts = [
                p for p in (
                    listing.address.street, listing.address.city,
                    listing.address.state, listing.address.postal_code,
                )
                if p
            ]
            address_text = ", ".join(parts)

        phone: Optional[LinkSpec] = None
        email: Optional[LinkSpec] = None
        website: Optional[LinkSpec] = None
        if listing.contact is not None:
            c = listing.contact
            if c.phone:
                digits = "".join(ch for ch in c.phone if ch.isdigit() or ch == "+")
                phone = LinkSpec(label=c.phone, href="tel:%s" % digits)
            if c.email:
                email = LinkSpec(label=c.email, href="mailto:%s" % c.email)
            if c.website_url:
                if not is_safe_url(c.website_url):
                    return None, {
                        "reason": "unsafe_url: listing %r contact.website_url %r is unsafe"
                        % (listing.listing_id, c.website_url),
                    }
                website = LinkSpec(
                    label="Visit website", href=c.website_url, external=True, rel="noopener",
                )

        if not address_text and phone is None and email is None and website is None:
            return None, None
        return ComponentRenderData(
            contact=ContactData(
                address_text=address_text, phone=phone, email=email, website=website,
            ),
        ), None

    @staticmethod
    def _build_hours_data(listing: Optional[ListingRecord]) -> Optional[ComponentRenderData]:
        if listing is None or not listing.hours:
            return None
        by_day = {entry.day.value: entry for entry in listing.hours}
        rows = tuple(
            HoursRow(
                day=_WEEKDAY_LABEL[day], opens=by_day[day].opens, closes=by_day[day].closes,
                closed=by_day[day].closed,
            )
            for day in _WEEKDAY_ORDER
            if day in by_day
        )
        if not rows:
            return None
        return ComponentRenderData(hours=HoursData(rows=rows))

    # -- Repetition: resolve one rule's matching ListingRecords -------------

    @staticmethod
    def _resolve_repetition_matches(
        rule: RepetitionRule,
        route_scope,
        listing_dataset: Optional[ListingDataset],
    ) -> Optional[List[ListingRecord]]:
        """The ordered, filtered list of listings a repetition rule matches
        on this page, or ``None`` when the route's scope cannot be resolved
        at all (no dataset supplied, or the route names no category --
        ``repeat_scope_unresolved``, distinct from a real, resolvable
        category that simply has zero/too-few/too-many matching listings).

        Exact, deterministic matching only (§7 ADR-WEB-LISTING-DATASET
        route convention, already applied by ``resolve_route_scope``): a
        listing matches when its ``category_id`` equals the resolved
        category's, minus the hosting page's own listing when
        ``rule.exclude_self`` and the route resolves one (a no-op on
        category routes, which resolve no ``route_scope.listing``).
        Dataset tuple order is preserved verbatim -- never re-sorted.
        """
        if listing_dataset is None or route_scope.category is None:
            return None
        return [
            listing
            for listing in listing_dataset.listings
            if listing.category_id == route_scope.category.category_id
            and not (
                rule.exclude_self
                and route_scope.listing is not None
                and listing.listing_id == route_scope.listing.listing_id
            )
        ]

    @staticmethod
    def _build_content_index(
        content_package: ContentPackage,
    ) -> Dict[Tuple[str, str], Tuple[str, ...]]:
        """The same ``(route, slot_id) -> texts`` index the Renderer builds
        (``rendering.renderer.Renderer.render``), reproduced here so Phase B
        resolves existing editorial content by the identical exact-match
        contract the Renderer will later consume it with."""
        index: Dict[Tuple[str, str], Tuple[str, ...]] = {}
        for block in content_package.blocks:
            key = (block.page_route, block.slot_id)
            index[key] = index.get(key, ()) + (block.text,)
        return index

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
    def _collect_diagnostics(
        unsupported: List[Dict[str, str]],
        unresolved: List[Dict[str, Any]],
        unbindable_props: List[Dict[str, str]],
        unbindable_content: List[Dict[str, str]],
        collisions: List[Dict[str, str]],
        repetition_failures: List[Dict[str, str]],
        render_data_failures: List[Dict[str, str]],
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
        if unbindable_props:
            diagnostics["unbindable_required_props"] = sorted(
                unbindable_props,
                key=lambda item: (item["route"], item["component_id"], item["prop"]),
            )
        if unbindable_content:
            diagnostics["unbindable_required_content"] = sorted(
                unbindable_content,
                key=lambda item: (item["route"], item["component_id"], item["slot"]),
            )
        if collisions:
            diagnostics["projected_slot_collisions"] = sorted(
                collisions,
                key=lambda item: (item["route"], item["component_id"], item["slot_id"]),
            )
        if repetition_failures:
            diagnostics["repetition_failures"] = sorted(
                repetition_failures,
                key=lambda item: (item["route"], item["component_id"], item["recipe_slot_id"]),
            )
        if render_data_failures:
            diagnostics["render_data_failures"] = sorted(
                render_data_failures,
                key=lambda item: (item["route"], item["component_id"], item["reason"]),
            )
        return {
            key: diagnostics[key]
            for key in _DIAGNOSTIC_BUCKET_ORDER
            if key in diagnostics
        }

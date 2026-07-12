"""Deterministic component registry (AES-WEB-002A; AES-WEB-002 §15).

The registry is **declarative frozen data plus pure index functions**. It is
constructed with an explicit, ordered set of :class:`ComponentDefinition`
objects, validated at construction time (§15.2 registry-integrity), and
never mutated afterward. There is:

* no filesystem scanning, no plugin discovery, no network discovery;
* no mutable global singleton — every :class:`ComponentRegistry` instance is
  isolated;
* deterministic ordering (lexicographic by ``component_id`` then version);
* a deterministic ``registry_hash`` fingerprint (SHA-256 over the canonical
  serialization of the registered definitions in sorted order), independent
  of insertion order;
* immutable returned collections (tuples).

The registry stores declarative definitions only. It never registers or
executes emitters, CSS, JavaScript, renderers, layouts, selection or scoring
functions, AI prompts, or analytics SDKs (§2.2). Candidate *selection*
(the §14 pipeline: filtering, scoring, tie-breaking, ``selection_trace``) is
a later wave; the lookups here are pure indexes, not selection.

Import matrix (§29.2): this module imports only ``contracts/``,
``constants/``, and the component ``catalog/`` — never renderer, gates,
repositories, or services.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

from engines.website_generation.constants.components import (
    COMPATIBILITY_AXES,
    COMPLEXITY_SCORE_DOUBLED_CEILING,
    COMPONENT_ID_MAX_LENGTH,
    COMPONENT_ID_SEGMENT_COUNT,
    COMPONENT_ID_SEGMENT_MAX_LENGTH,
    COMPONENT_ID_SEGMENT_PATTERN,
    COMPONENT_ID_SEPARATOR,
    EXPERIMENTAL_PREFIX,
    EXTENSION_PREFIX,
    MAX_BOOL_PROPS,
    MAX_OPTIONAL_PROPS,
    MAX_REQUIRED_PROPS,
    MAX_VARIANTS,
    PROHIBITED_SITE_PREFIX,
    RESERVED_FAMILY_WORDS,
    SEMVER_PATTERN,
)
from engines.website_generation.contracts.artifacts import (
    FrozenModel,
    canonical_json,
    model_to_dict,
    sha256_of_text,
)
from engines.website_generation.contracts.components import (
    ComponentDefinition,
    PropSpec,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
)
from engines.website_generation.contracts.errors import (
    ComponentNotFoundError,
    ConflictingComponentError,
    DuplicateComponentError,
    InvalidCompatibilityDeclarationError,
    InvalidComponentDefinitionError,
    UnsupportedComponentVersionError,
)
from engines.website_generation.contracts.interfaces import (
    ComponentRegistryView,
)
from engines.website_generation.contracts.versions import (
    REGISTRY_FINGERPRINT_VERSION,
    REGISTRY_VERSION,
)

_SEGMENT_RE = re.compile(COMPONENT_ID_SEGMENT_PATTERN)
_SEMVER_RE = re.compile(SEMVER_PATTERN)


# ---------------------------------------------------------------------------
# Derived, serializable registry inventory (§15.2 "registry manifest")
# ---------------------------------------------------------------------------

class RegistryInventoryEntry(FrozenModel):
    """One row of the derived registry catalog (id, version, family,
    lifecycle, definition hash)."""

    component_id: str
    component_version: str
    component_family: ComponentFamily
    lifecycle_status: LifecycleStatus
    definition_hash: str


def definition_fingerprint(definition: ComponentDefinition) -> str:
    """Content identity of a single definition: sha256(canonical_json)."""
    return sha256_of_text(canonical_json(model_to_dict(definition)))


# ---------------------------------------------------------------------------
# Definition validation (AES-WEB-002 §4, §7.3, §15.2, §22)
# ---------------------------------------------------------------------------

def _strip_namespace(component_id: str) -> str:
    """Return the bare three-segment id, rejecting the prohibited ``site.``
    namespace (§4.3)."""
    if component_id.startswith(PROHIBITED_SITE_PREFIX):
        raise InvalidComponentDefinitionError(
            "component_id uses the prohibited 'site.' namespace: %r"
            % component_id,
            stage="component_registry",
            diagnostics={"component_id": component_id},
        )
    for prefix in (EXPERIMENTAL_PREFIX, EXTENSION_PREFIX):
        if component_id.startswith(prefix):
            return component_id[len(prefix):]
    return component_id


def _validate_component_id(component_id: str) -> str:
    """Validate the naming grammar (§4.1/§4.3); return the family segment."""
    if not component_id or len(component_id) > COMPONENT_ID_MAX_LENGTH:
        raise InvalidComponentDefinitionError(
            "component_id length out of range: %r" % component_id,
            stage="component_registry",
            diagnostics={"component_id": component_id},
        )
    bare = _strip_namespace(component_id)
    segments = bare.split(COMPONENT_ID_SEPARATOR)
    if len(segments) != COMPONENT_ID_SEGMENT_COUNT:
        raise InvalidComponentDefinitionError(
            "component_id must have exactly %d segments: %r"
            % (COMPONENT_ID_SEGMENT_COUNT, component_id),
            stage="component_registry",
            diagnostics={"component_id": component_id},
        )
    for segment in segments:
        if len(segment) > COMPONENT_ID_SEGMENT_MAX_LENGTH:
            raise InvalidComponentDefinitionError(
                "component_id segment too long: %r" % segment,
                stage="component_registry",
                diagnostics={"component_id": component_id, "segment": segment},
            )
        if not _SEGMENT_RE.match(segment):
            raise InvalidComponentDefinitionError(
                "component_id segment violates grammar: %r" % segment,
                stage="component_registry",
                diagnostics={"component_id": component_id, "segment": segment},
            )
    family_segment = segments[0]
    if family_segment in RESERVED_FAMILY_WORDS:
        raise InvalidComponentDefinitionError(
            "reserved word used as family segment: %r" % family_segment,
            stage="component_registry",
            diagnostics={"component_id": component_id},
        )
    return family_segment


def _validate_semver(version: str, component_id: str) -> None:
    if not _SEMVER_RE.match(version):
        raise InvalidComponentDefinitionError(
            "component_version is not semver: %r" % version,
            stage="component_registry",
            diagnostics={"component_id": component_id, "version": version},
        )


def _count_bool_props(props: Dict[str, PropSpec]) -> int:
    return sum(1 for spec in props.values() if spec.prop_type is PropType.BOOL)


def _validate_complexity(definition: ComponentDefinition) -> None:
    """Enforce the §7.3 complexity budget (BLOCKING at registration)."""
    n_required = len(definition.required_props)
    n_optional = len(definition.optional_props)
    n_variants = len(definition.supported_variants)
    n_bool = _count_bool_props(definition.required_props) + _count_bool_props(
        definition.optional_props
    )
    cid = definition.component_id
    if n_required > MAX_REQUIRED_PROPS:
        raise InvalidComponentDefinitionError(
            "required_props exceeds budget (%d > %d): %s"
            % (n_required, MAX_REQUIRED_PROPS, cid),
            stage="component_registry",
            diagnostics={"component_id": cid},
        )
    if n_optional > MAX_OPTIONAL_PROPS:
        raise InvalidComponentDefinitionError(
            "optional_props exceeds budget (%d > %d): %s"
            % (n_optional, MAX_OPTIONAL_PROPS, cid),
            stage="component_registry",
            diagnostics={"component_id": cid},
        )
    if n_variants > MAX_VARIANTS:
        raise InvalidComponentDefinitionError(
            "supported_variants exceeds budget (%d > %d): %s"
            % (n_variants, MAX_VARIANTS, cid),
            stage="component_registry",
            diagnostics={"component_id": cid},
        )
    if n_bool > MAX_BOOL_PROPS:
        raise InvalidComponentDefinitionError(
            "boolean props exceed budget (%d > %d): %s"
            % (n_bool, MAX_BOOL_PROPS, cid),
            stage="component_registry",
            diagnostics={"component_id": cid},
        )
    # complexity score = required + 0.5*optional + 2*variants <= 20.
    # Computed doubled to stay in integer arithmetic (no floats).
    score_doubled = 2 * n_required + n_optional + 4 * n_variants
    if score_doubled > COMPLEXITY_SCORE_DOUBLED_CEILING:
        raise InvalidComponentDefinitionError(
            "complexity score exceeds budget for %s" % cid,
            stage="component_registry",
            diagnostics={"component_id": cid},
        )


def _validate_compatibility(definition: ComponentDefinition) -> None:
    for axis in definition.compatibility_range:
        if axis not in COMPATIBILITY_AXES:
            raise InvalidCompatibilityDeclarationError(
                "unknown compatibility axis %r for %s"
                % (axis, definition.component_id),
                stage="component_registry",
                diagnostics={
                    "component_id": definition.component_id,
                    "axis": axis,
                },
            )


def validate_definition(definition: ComponentDefinition) -> None:
    """Run every registry-integrity check checkable at 002A (§15.2).

    Checks: naming grammar (§4), family-segment/family agreement (§5),
    semver (§22), complexity budget (§7.3), DEPRECATED → replacement
    mapping (§22.4), monetization family → monetization_contract (§5.10),
    and compatibility axes (§22.1). Checks that require emitters, fixtures,
    or a token schema (emitter-key resolution, fixture resolution, token
    cross-check) belong to later waves and are not performed here.
    """
    family_segment = _validate_component_id(definition.component_id)
    if family_segment != definition.component_family.value:
        raise ConflictingComponentError(
            "component_id family segment %r conflicts with component_family "
            "%r" % (family_segment, definition.component_family.value),
            stage="component_registry",
            diagnostics={"component_id": definition.component_id},
        )
    _validate_semver(definition.component_version, definition.component_id)
    _validate_complexity(definition)
    _validate_compatibility(definition)

    if definition.lifecycle_status is LifecycleStatus.DEPRECATED:
        if not definition.replacement_component_id:
            raise InvalidComponentDefinitionError(
                "DEPRECATED component requires replacement_component_id: %s"
                % definition.component_id,
                stage="component_registry",
                diagnostics={"component_id": definition.component_id},
            )
    if definition.component_family is ComponentFamily.MONETIZATION:
        if definition.monetization_contract is None:
            raise InvalidComponentDefinitionError(
                "monetization-family component requires a "
                "monetization_contract: %s" % definition.component_id,
                stage="component_registry",
                diagnostics={"component_id": definition.component_id},
            )
    if definition.default_variant and (
        definition.default_variant not in definition.supported_variants
    ):
        raise InvalidComponentDefinitionError(
            "default_variant %r not in supported_variants: %s"
            % (definition.default_variant, definition.component_id),
            stage="component_registry",
            diagnostics={"component_id": definition.component_id},
        )


def _semver_key(version: str) -> Tuple[int, int, int]:
    parts = version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


# ---------------------------------------------------------------------------
# ComponentRegistry
# ---------------------------------------------------------------------------

class ComponentRegistry(ComponentRegistryView):
    """An isolated, deterministic, immutable component registry (§15)."""

    def __init__(
        self, definitions: Iterable[ComponentDefinition] = ()
    ) -> None:
        by_id: Dict[str, Dict[str, ComponentDefinition]] = {}
        families: Dict[str, ComponentFamily] = {}
        # Cross-definition uniqueness (AES-REVIEW-001A finding #2): distinct
        # component_ids must never share a rendering emitter_key or an
        # analytics impression_id. §20.1 keys the renderer's emitter table by
        # (component_id, major_version), so different *versions* of the SAME
        # id are expected to reuse the same emitter_key/impression_id; only a
        # collision across DIFFERENT ids is a conflict (e.g. a copy-pasted
        # definition whose component_id was updated but whose emitter_key /
        # impression_id literals were not).
        emitter_key_owners: Dict[str, str] = {}
        impression_id_owners: Dict[str, str] = {}
        for definition in definitions:
            validate_definition(definition)
            cid = definition.component_id
            version = definition.component_version
            # A component's family is permanent (§5): the same id across
            # versions must not change family.
            if cid in families and families[cid] is not definition.component_family:
                raise ConflictingComponentError(
                    "component_id %s registered with conflicting families "
                    "%r and %r"
                    % (cid, families[cid].value, definition.component_family.value),
                    stage="component_registry",
                    diagnostics={"component_id": cid},
                )
            families[cid] = definition.component_family
            versions = by_id.setdefault(cid, {})
            if version in versions:
                raise DuplicateComponentError(
                    "duplicate registration for %s@%s" % (cid, version),
                    stage="component_registry",
                    diagnostics={"component_id": cid, "version": version},
                )
            versions[version] = definition

            emitter_key = definition.rendering_contract.emitter_key
            owner = emitter_key_owners.setdefault(emitter_key, cid)
            if owner != cid:
                raise ConflictingComponentError(
                    "emitter_key %r is shared by component_ids %s and %s"
                    % (emitter_key, owner, cid),
                    stage="component_registry",
                    diagnostics={
                        "emitter_key": emitter_key,
                        "component_id": cid,
                        "conflicts_with": owner,
                    },
                )

            impression_id = definition.analytics_contract.impression_id
            owner = impression_id_owners.setdefault(impression_id, cid)
            if owner != cid:
                raise ConflictingComponentError(
                    "impression_id %r is shared by component_ids %s and %s"
                    % (impression_id, owner, cid),
                    stage="component_registry",
                    diagnostics={
                        "impression_id": impression_id,
                        "component_id": cid,
                        "conflicts_with": owner,
                    },
                )

        # Freeze the ordered inventory (lexicographic by id, then semver).
        ordered: List[ComponentDefinition] = []
        for cid in sorted(by_id):
            for version in sorted(by_id[cid], key=_semver_key):
                ordered.append(by_id[cid][version])
        self._by_id: Dict[str, Dict[str, ComponentDefinition]] = by_id
        self._ordered: Tuple[ComponentDefinition, ...] = tuple(ordered)
        self._hash: str = self._compute_hash(self._ordered)

        # Deterministic secondary indexes (AES-REVIEW-001A finding #3),
        # precomputed once from the frozen, sorted inventory — never
        # recomputed per lookup. Building from self._ordered (already
        # lexicographically sorted) means insertion order of `definitions`
        # cannot affect index contents, matching the registry_hash guarantee.
        page_role_index: Dict[PageRole, List[ComponentDefinition]] = {}
        family_index: Dict[ComponentFamily, List[ComponentDefinition]] = {}
        for d in self._ordered:
            for role in d.supported_page_roles:
                page_role_index.setdefault(role, []).append(d)
            family_index.setdefault(d.component_family, []).append(d)
        self._page_role_index: Dict[PageRole, Tuple[ComponentDefinition, ...]] = {
            role: tuple(defs) for role, defs in page_role_index.items()
        }
        self._family_index: Dict[ComponentFamily, Tuple[ComponentDefinition, ...]] = {
            family: tuple(defs) for family, defs in family_index.items()
        }

    # -- fingerprint --------------------------------------------------------

    @staticmethod
    def _compute_hash(
        ordered: Tuple[ComponentDefinition, ...]
    ) -> str:
        payload = {
            "fingerprint_version": REGISTRY_FINGERPRINT_VERSION,
            "definitions": [model_to_dict(d) for d in ordered],
        }
        return sha256_of_text(canonical_json(payload))

    # -- ComponentRegistryView ---------------------------------------------

    def get(
        self, component_id: str, version_req: Optional[str] = None
    ) -> ComponentDefinition:
        versions = self._by_id.get(component_id)
        if versions is None:
            raise ComponentNotFoundError(
                "no component registered under id %r" % component_id,
                stage="component_registry",
                diagnostics={"component_id": component_id},
            )
        if version_req is None:
            latest = max(versions, key=_semver_key)
            return versions[latest]
        definition = versions.get(version_req)
        if definition is None:
            raise UnsupportedComponentVersionError(
                "component %s has no version %r" % (component_id, version_req),
                stage="component_registry",
                diagnostics={
                    "component_id": component_id,
                    "version": version_req,
                },
            )
        return definition

    def resolve_variant(
        self, component_id: str, variant: str
    ) -> VariantSpec:
        definition = self.get(component_id)
        spec = definition.supported_variants.get(variant)
        if spec is None:
            raise ComponentNotFoundError(
                "component %s has no variant %r" % (component_id, variant),
                stage="component_registry",
                diagnostics={"component_id": component_id, "variant": variant},
            )
        return spec

    def candidates_for(
        self, page_role: PageRole, slot_need: Optional[str] = None
    ) -> Tuple[ComponentDefinition, ...]:
        candidates = self._page_role_index.get(page_role, ())
        if slot_need is None:
            return candidates
        return tuple(
            d for d in candidates if self._declares_slot(d, slot_need)
        )

    @staticmethod
    def _declares_slot(
        definition: ComponentDefinition, block_type: str
    ) -> bool:
        for slots in (
            definition.required_content_slots,
            definition.optional_content_slots,
        ):
            for spec in slots.values():
                if spec.block_type == block_type:
                    return True
        return False

    def by_family(
        self, family: ComponentFamily
    ) -> Tuple[ComponentDefinition, ...]:
        return self._family_index.get(family, ())

    def lifecycle(self, component_id: str) -> LifecycleStatus:
        return self.get(component_id).lifecycle_status

    def replacement_for(self, component_id: str) -> Optional[str]:
        return self.get(component_id).replacement_component_id

    def registry_version(self) -> str:
        return REGISTRY_VERSION

    def registry_hash(self) -> str:
        return self._hash

    # -- extra deterministic accessors -------------------------------------

    def inventory(self) -> Tuple[RegistryInventoryEntry, ...]:
        """Derived, serializable catalog (§15.2), deterministically ordered."""
        return tuple(
            RegistryInventoryEntry(
                component_id=d.component_id,
                component_version=d.component_version,
                component_family=d.component_family,
                lifecycle_status=d.lifecycle_status,
                definition_hash=definition_fingerprint(d),
            )
            for d in self._ordered
        )

    def all_definitions(self) -> Tuple[ComponentDefinition, ...]:
        """Every registered definition, deterministically ordered (immutable)."""
        return self._ordered

    def __len__(self) -> int:
        return len(self._ordered)

    def __contains__(self, component_id: object) -> bool:
        return component_id in self._by_id


# The shared Atlas library's registered components: an explicit, ordered
# tuple sourced from the catalog family modules (§15.2). Order is
# lexicographic by component_id — enforced by test — so merge conflicts are
# visible and ordering is deterministic. No dynamic scanning.
#
# AES-WEB-002B populated Wave 1 (§27.2: the fifteen layout/atom foundation
# primitives). AES-WEB-002C appends Wave 2 (§27.3: the eight navigation/
# legal/status components). AES-WEB-002D appends Wave 3 (§27.4: the nine
# hero/directory/status.results.zero discovery components) plus, per
# amendment A4, exactly one provisional Wave 4 component
# (listing.card.standard). AES-WEB-002E completes Wave 4 (§27.5: the full
# twelve-component listing/profile inventory — see
# catalog/listings_profiles.py, whose WAVE4_COMPONENTS tuple now carries
# listing.card.standard alongside its eleven Wave-4 siblings). Later waves
# append their family modules here.
#
# Each wave module's own WAVE*_COMPONENTS tuple is internally lexicographic
# (§15.2, asserted per-wave by each test_catalog_waveN.py), but simple
# concatenation across waves is NOT globally lexicographic in general — Wave
# 1 (atom.*/layout.*) and Wave 2 (legal.*/nav.*/status.*) happened to
# concatenate correctly only because every Wave-1 family segment sorts
# before every Wave-2 one; Wave 3's directory.*/hero.* segments sort between
# them. The final tuple is therefore explicitly re-sorted here so the §15.2
# ordering law holds regardless of which family segments future waves add.
from engines.website_generation.components.catalog.layout_atoms import (
    WAVE1_COMPONENTS,
)
from engines.website_generation.components.catalog.navigation import (
    WAVE2_COMPONENTS,
)
from engines.website_generation.components.catalog.discovery import (
    WAVE3_COMPONENTS,
)
from engines.website_generation.components.catalog.listings_profiles import (
    WAVE4_COMPONENTS,
)

REGISTERED_COMPONENTS: Tuple[ComponentDefinition, ...] = tuple(
    sorted(
        WAVE1_COMPONENTS
        + WAVE2_COMPONENTS
        + WAVE3_COMPONENTS
        + WAVE4_COMPONENTS,
        key=lambda d: d.component_id,
    )
)


def build_default_registry() -> ComponentRegistry:
    """Construct a registry from the shared ``REGISTERED_COMPONENTS`` tuple.

    Returns a fresh, isolated instance on every call — there is no mutable
    global singleton (§15).
    """
    return ComponentRegistry(REGISTERED_COMPONENTS)

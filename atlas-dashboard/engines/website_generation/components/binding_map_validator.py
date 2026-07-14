"""Deterministic validator for the content binding map (AES-WEB-002J.18;
ADR-WEB-CONTENT-BINDING-MAP).

Checks the declarative map (``binding_rules.BINDING_RULES``) and the semantic
vocabulary (``constants/content_slots.py``) against the live component
registry: completeness (every required content slot / ``CONTENT_BLOCK_REF`` /
``LISTING_REF`` / literal prop mapped), field existence, type/scope/cardinality
compatibility, and the ADR honesty invariants (no placeholder source, a
``structured_deferred`` slot may not be ``FULLY_BINDABLE``, an ``UNAVAILABLE``
source may not be marked bindable).

Pure and deterministic: no I/O, no clock, no randomness, no AI, no registry
mutation. Reuses the existing :class:`ArtifactValidationError` (no new engine
error) and batch-reports every violation in a stable order -- never repairs,
never returns a partial result.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from engines.website_generation.constants.content_slots import (
    SEMANTIC_SLOTS,
    Availability,
    SemanticSlot,
    VALID_CARDINALITIES,
)
from engines.website_generation.contracts.enums import PropType
from engines.website_generation.contracts.errors import ArtifactValidationError
from engines.website_generation.contracts.interfaces import ComponentRegistryView
from engines.website_generation.components.binding_rules import (
    BINDING_RULES,
    BindingRule,
    BindingState,
    FieldKind,
)
from engines.website_generation.components.registry import build_default_registry

# Prop types whose value resolves to a content-slot reference (bound as a
# PROP_REF rule), versus literal props (bound as a PROP_LITERAL rule).
_REF_PROP_TYPES = frozenset({PropType.CONTENT_BLOCK_REF, PropType.LISTING_REF})

_DIAGNOSTIC_BUCKET_ORDER = (
    "duplicate_semantic_slots",
    "duplicate_field_mappings",
    "unknown_components",
    "unknown_component_fields",
    "unknown_semantic_slots",
    "unmapped_required_content_slots",
    "unmapped_required_ref_props",
    "unmapped_required_literal_props",
    "field_kind_mismatch",
    "block_type_mismatch",
    "prop_type_mismatch",
    "invalid_cardinality",
    "placeholder_sources",
    "structured_marked_fully_bindable",
    "unavailable_marked_bindable",
    "availability_state_mismatch",
)


def _key(rule: BindingRule):
    return (rule.component_id, rule.field_kind.value, rule.field_name)


def validate_binding_map(
    registry: Optional[ComponentRegistryView] = None,
) -> None:
    """Validate the whole binding map against ``registry`` (the default MVP
    registry when omitted). Raise one batched
    :class:`ArtifactValidationError` naming every violation, or return
    ``None`` when the map is complete and consistent.
    """
    registry = registry if registry is not None else build_default_registry()
    diagnostics: Dict[str, List[Dict[str, str]]] = {}

    # -- vocabulary integrity: no duplicate semantic slot names ---------
    # (SEMANTIC_SLOTS is a dict so keys are unique; guard against a name
    # colliding via case/whitespace by checking the canonical set size is the
    # count of declared entries -- exposed for the completeness test.)
    # Handled in the vocabulary test; here we only rely on SEMANTIC_SLOTS.

    # -- duplicate component-field mappings -----------------------------
    seen: Dict[tuple, int] = {}
    for rule in BINDING_RULES:
        seen[_key(rule)] = seen.get(_key(rule), 0) + 1
    dupes = sorted(k for k, n in seen.items() if n > 1)
    if dupes:
        diagnostics["duplicate_field_mappings"] = [
            {"component_id": c, "field_kind": fk, "field_name": fn}
            for (c, fk, fn) in dupes
        ]

    # -- build registry views -------------------------------------------
    all_defs = {d.component_id: d for d in registry.all_definitions()}

    # -- per-rule structural + honesty checks ---------------------------
    unknown_components: List[Dict[str, str]] = []
    unknown_fields: List[Dict[str, str]] = []
    unknown_slots: List[Dict[str, str]] = []
    kind_mismatch: List[Dict[str, str]] = []
    block_mismatch: List[Dict[str, str]] = []
    prop_mismatch: List[Dict[str, str]] = []
    bad_card: List[Dict[str, str]] = []
    placeholder: List[Dict[str, str]] = []
    structured_full: List[Dict[str, str]] = []
    unavailable_bindable: List[Dict[str, str]] = []
    avail_mismatch: List[Dict[str, str]] = []

    for rule in BINDING_RULES:
        d = all_defs.get(rule.component_id)
        if d is None:
            unknown_components.append({"component_id": rule.component_id})
            continue

        # field existence + field-kind correctness
        slot_spec = None
        prop_spec = None
        if rule.field_kind is FieldKind.CONTENT_SLOT:
            slot_spec = d.required_content_slots.get(rule.field_name) or \
                d.optional_content_slots.get(rule.field_name)
            if slot_spec is None:
                unknown_fields.append(
                    {"component_id": rule.component_id, "field_name": rule.field_name,
                     "field_kind": rule.field_kind.value})
        else:  # PROP_REF or PROP_LITERAL
            prop_spec = d.required_props.get(rule.field_name) or \
                d.optional_props.get(rule.field_name)
            if prop_spec is None:
                unknown_fields.append(
                    {"component_id": rule.component_id, "field_name": rule.field_name,
                     "field_kind": rule.field_kind.value})
            else:
                is_ref = prop_spec.prop_type in _REF_PROP_TYPES
                if is_ref and rule.field_kind is not FieldKind.PROP_REF:
                    kind_mismatch.append(
                        {"component_id": rule.component_id, "field_name": rule.field_name,
                         "reason": "ref_prop_not_marked_PROP_REF"})
                if not is_ref and rule.field_kind is FieldKind.PROP_REF:
                    kind_mismatch.append(
                        {"component_id": rule.component_id, "field_name": rule.field_name,
                         "reason": "literal_prop_marked_PROP_REF"})

        # placeholder / empty source rule
        sr = rule.source_rule.strip()
        if not sr or "resolved " in sr.lower() or sr.lower().startswith("resolved"):
            placeholder.append(
                {"component_id": rule.component_id, "field_name": rule.field_name,
                 "source_rule": rule.source_rule})

        # type compatibility
        if slot_spec is not None and rule.expected_type != slot_spec.block_type:
            block_mismatch.append(
                {"component_id": rule.component_id, "field_name": rule.field_name,
                 "rule_type": rule.expected_type, "declared": slot_spec.block_type})
        if prop_spec is not None and rule.expected_type != prop_spec.prop_type.value:
            prop_mismatch.append(
                {"component_id": rule.component_id, "field_name": rule.field_name,
                 "rule_type": rule.expected_type, "declared": prop_spec.prop_type.value})

        # semantic-slot resolution + honesty invariants (non-literal rules)
        if rule.field_kind is not FieldKind.PROP_LITERAL:
            slot: Optional[SemanticSlot] = SEMANTIC_SLOTS.get(rule.semantic_slot)
            if slot is None:
                unknown_slots.append(
                    {"component_id": rule.component_id, "field_name": rule.field_name,
                     "semantic_slot": rule.semantic_slot})
            else:
                if slot.cardinality not in VALID_CARDINALITIES:
                    bad_card.append(
                        {"semantic_slot": slot.name, "cardinality": slot.cardinality})
                # structured_deferred slot may never be FULLY_BINDABLE
                if slot.structured_deferred and rule.binding_state is BindingState.FULLY_BINDABLE:
                    structured_full.append(
                        {"component_id": rule.component_id, "field_name": rule.field_name,
                         "semantic_slot": slot.name})
                # UNAVAILABLE source may not be marked bindable
                if slot.availability is Availability.UNAVAILABLE and \
                        rule.binding_state is not BindingState.SOURCE_UNAVAILABLE:
                    unavailable_bindable.append(
                        {"component_id": rule.component_id, "field_name": rule.field_name,
                         "semantic_slot": slot.name, "state": rule.binding_state.value})
                # SOURCE_UNAVAILABLE state must point at an UNAVAILABLE slot
                if rule.binding_state is BindingState.SOURCE_UNAVAILABLE and \
                        slot.availability is not Availability.UNAVAILABLE:
                    avail_mismatch.append(
                        {"component_id": rule.component_id, "field_name": rule.field_name,
                         "semantic_slot": slot.name, "availability": slot.availability.value})
                # FULLY_BINDABLE requires an AVAILABLE/DERIVABLE, flat slot
                if rule.binding_state is BindingState.FULLY_BINDABLE and (
                    slot.availability not in (Availability.AVAILABLE, Availability.DERIVABLE)
                    or not slot.flat_ok
                ):
                    avail_mismatch.append(
                        {"component_id": rule.component_id, "field_name": rule.field_name,
                         "semantic_slot": slot.name, "availability": slot.availability.value,
                         "reason": "fully_bindable_requires_available_flat_slot"})

    # -- completeness against the registry ------------------------------
    mapped_keys = {_key(r) for r in BINDING_RULES}
    unmapped_slots: List[Dict[str, str]] = []
    unmapped_refs: List[Dict[str, str]] = []
    unmapped_literals: List[Dict[str, str]] = []
    for d in registry.all_definitions():
        for name in d.required_content_slots:
            if (d.component_id, FieldKind.CONTENT_SLOT.value, name) not in mapped_keys:
                unmapped_slots.append({"component_id": d.component_id, "field_name": name})
        for name, spec in d.required_props.items():
            if spec.prop_type in _REF_PROP_TYPES:
                if (d.component_id, FieldKind.PROP_REF.value, name) not in mapped_keys:
                    unmapped_refs.append(
                        {"component_id": d.component_id, "field_name": name,
                         "prop_type": spec.prop_type.value})
            else:
                if (d.component_id, FieldKind.PROP_LITERAL.value, name) not in mapped_keys:
                    unmapped_literals.append(
                        {"component_id": d.component_id, "field_name": name,
                         "prop_type": spec.prop_type.value})

    # -- assemble (sorted, deterministic) -------------------------------
    def _put(bucket: str, rows: List[Dict[str, str]]) -> None:
        if rows:
            diagnostics[bucket] = sorted(
                rows, key=lambda e: tuple(sorted(e.items()))
            )

    _put("unknown_components", unknown_components)
    _put("unknown_component_fields", unknown_fields)
    _put("unknown_semantic_slots", unknown_slots)
    _put("unmapped_required_content_slots", unmapped_slots)
    _put("unmapped_required_ref_props", unmapped_refs)
    _put("unmapped_required_literal_props", unmapped_literals)
    _put("field_kind_mismatch", kind_mismatch)
    _put("block_type_mismatch", block_mismatch)
    _put("prop_type_mismatch", prop_mismatch)
    _put("invalid_cardinality", bad_card)
    _put("placeholder_sources", placeholder)
    _put("structured_marked_fully_bindable", structured_full)
    _put("unavailable_marked_bindable", unavailable_bindable)
    _put("availability_state_mismatch", avail_mismatch)

    if not diagnostics:
        return

    ordered = {k: diagnostics[k] for k in _DIAGNOSTIC_BUCKET_ORDER if k in diagnostics}
    raise ArtifactValidationError(
        "Content binding map validation failed; see diagnostics",
        stage="binding_map_validation",
        diagnostics=ordered,
    )

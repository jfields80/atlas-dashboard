"""CG-CON — Contract gates (AES-WEB-002 §21.1).

Ten gates checking that a bound component instance honors its
``ComponentDefinition``'s contract: identity, version, props, slots,
variant, lifecycle, compatibility range, asset refs, and route refs.

Every check here operates on real, frozen contract data
(:class:`~engines.website_generation.contracts.components.ComponentDefinition`
and its sub-contracts) wrapped by the synthetic
:class:`~engines.website_generation.gates.checks.SyntheticInstance` binding
facts (AMB-002I-01/03) — no rendered output is required for this family,
so nothing here is a synthetic rendering stand-in.

Remediation owner key (AES-WEB-002 §21 preamble): CE = Component Engine
binding, R = registry/definition, CT = content.
"""

from __future__ import annotations

from engines.website_generation.contracts.enums import LifecycleStatus, PropType
from engines.website_generation.gates.checks import CheckOutcome, SyntheticInstance


def _instance_ref(instance: SyntheticInstance) -> str:
    return (
        f"route={instance.page_route!r} instance={instance.instance_path!r} "
        f"component={instance.definition.component_id}@"
        f"{instance.definition.component_version}"
    )


def check_cg_con_001(
    instance: SyntheticInstance,
) -> CheckOutcome:
    """CG-CON-001: every instance's component_id exists in registry."""
    if instance.definition.component_id in instance.registry_known_ids:
        return CheckOutcome(True, f"{_instance_ref(instance)}: id registered")
    return CheckOutcome(
        False,
        f"{_instance_ref(instance)}: component_id "
        f"{instance.definition.component_id!r} not found in registry "
        f"{sorted(instance.registry_known_ids)!r}",
    )


def check_cg_con_002(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-002: instance version within registry's supported versions."""
    requested = instance.requested_version or instance.definition.component_version
    if requested == instance.definition.component_version:
        return CheckOutcome(True, f"{_instance_ref(instance)}: version matches")
    return CheckOutcome(
        False,
        f"{_instance_ref(instance)}: requested version {requested!r} is not "
        f"the registry-supported version {instance.definition.component_version!r}",
    )


def check_cg_con_003(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-003: all required props bound; types valid."""
    for name, spec in instance.definition.required_props.items():
        if name not in instance.bound_required_props:
            return CheckOutcome(
                False, f"{_instance_ref(instance)}: required prop {name!r} unbound"
            )
        value = instance.bound_required_props[name]
        if spec.prop_type == PropType.STR_ENUM and value not in spec.enum_values:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: prop {name!r} value {value!r} not in "
                f"enum_values {spec.enum_values!r}",
            )
        if spec.prop_type == PropType.INT_BOUNDED:
            try:
                int_value = int(value)
            except ValueError:
                return CheckOutcome(
                    False,
                    f"{_instance_ref(instance)}: prop {name!r} value {value!r} "
                    "is not an integer",
                )
            if spec.int_min is not None and int_value < spec.int_min:
                return CheckOutcome(
                    False,
                    f"{_instance_ref(instance)}: prop {name!r} value {int_value} "
                    f"below int_min {spec.int_min}",
                )
            if spec.int_max is not None and int_value > spec.int_max:
                return CheckOutcome(
                    False,
                    f"{_instance_ref(instance)}: prop {name!r} value {int_value} "
                    f"above int_max {spec.int_max}",
                )
        if spec.prop_type == PropType.BOOL and value not in ("true", "false"):
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: prop {name!r} value {value!r} is "
                "not a valid BOOL literal",
            )
    return CheckOutcome(True, f"{_instance_ref(instance)}: required props bound and valid")


def check_cg_con_004(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-004: no unknown props."""
    known = set(instance.definition.required_props) | set(
        instance.definition.optional_props
    )
    bound = set(instance.bound_required_props) | set(instance.bound_optional_props)
    unknown = sorted(bound - known)
    if unknown:
        return CheckOutcome(
            False, f"{_instance_ref(instance)}: unknown prop(s) {unknown!r}"
        )
    return CheckOutcome(True, f"{_instance_ref(instance)}: no unknown props")


def check_cg_con_005(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-005: all required content slots bound; cardinality respected."""
    for slot_id, spec in instance.definition.required_content_slots.items():
        refs = instance.bound_required_slots.get(slot_id)
        if not refs:
            return CheckOutcome(
                False, f"{_instance_ref(instance)}: required slot {slot_id!r} unbound"
            )
        count = len(refs)
        if spec.cardinality.value == "exactly_one" and count != 1:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: slot {slot_id!r} requires exactly one "
                f"ref, got {count}",
            )
        if spec.cardinality.value == "zero_or_one" and count > 1:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: slot {slot_id!r} allows at most one "
                f"ref, got {count}",
            )
        if (
            spec.cardinality.value == "one_to_n"
            and spec.max_count is not None
            and count > spec.max_count
        ):
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: slot {slot_id!r} exceeds max_count "
                f"{spec.max_count}, got {count}",
            )
    return CheckOutcome(
        True, f"{_instance_ref(instance)}: required slots bound with valid cardinality"
    )


def check_cg_con_006(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-006: variant exists in supported_variants."""
    if not instance.variant:
        return CheckOutcome(True, f"{_instance_ref(instance)}: default variant used")
    if instance.variant in instance.definition.supported_variants:
        return CheckOutcome(
            True, f"{_instance_ref(instance)}: variant {instance.variant!r} supported"
        )
    return CheckOutcome(
        False,
        f"{_instance_ref(instance)}: variant {instance.variant!r} not in "
        f"supported_variants {sorted(instance.definition.supported_variants)!r}",
    )


def check_cg_con_007(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-007: no DEPRECATED without recorded build allowance; no
    RETIRED/BLOCKED ever; no ``x.`` prefix in certifiable builds."""
    status = instance.definition.lifecycle_status
    if status in (LifecycleStatus.RETIRED, LifecycleStatus.BLOCKED):
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: lifecycle_status {status.value} is never "
            "certifiable",
        )
    if status == LifecycleStatus.DEPRECATED and not instance.build_allows_deprecated:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: DEPRECATED component used without a "
            "recorded build allowance",
        )
    if instance.definition.component_id.startswith("x."):
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: experimental id "
            f"{instance.definition.component_id!r} is never certifiable",
        )
    return CheckOutcome(True, f"{_instance_ref(instance)}: lifecycle status certifiable")


def check_cg_con_008(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-008: compatibility_range satisfied vs renderer/token/registry
    versions (current environment supplied as ``compatibility_environment``)."""
    for axis, current_version in instance.compatibility_environment.items():
        declared_range = instance.definition.compatibility_range.get(axis)
        if declared_range is None:
            continue
        if current_version != declared_range:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: axis {axis!r} current version "
                f"{current_version!r} does not satisfy declared range "
                f"{declared_range!r}",
            )
    return CheckOutcome(True, f"{_instance_ref(instance)}: compatibility range satisfied")


def check_cg_con_009(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-009: every ASSET_REF resolves in CAS with correct AssetRole."""
    asset_prop_specs = {
        name: spec
        for name, spec in {
            **instance.definition.required_props,
            **instance.definition.optional_props,
        }.items()
        if spec.prop_type == PropType.ASSET_REF
    }
    bound = {**instance.bound_required_props, **instance.bound_optional_props}
    for name in asset_prop_specs:
        ref = bound.get(name)
        if ref is None:
            continue
        resolved_role = instance.asset_ref_roles.get(ref, "")
        if not resolved_role:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: asset ref {ref!r} (prop {name!r}) "
                "does not resolve in the CAS",
            )
        if resolved_role not in {r.value for r in instance.definition.supported_asset_roles}:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: asset ref {ref!r} resolved role "
                f"{resolved_role!r} not in supported_asset_roles "
                f"{[r.value for r in instance.definition.supported_asset_roles]!r}",
            )
    return CheckOutcome(True, f"{_instance_ref(instance)}: asset refs resolve correctly")


def check_cg_con_010(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CON-010: every ROUTE_REF exists in SiteArchitecture."""
    unresolved = sorted(set(instance.route_refs) - set(instance.resolved_routes))
    if unresolved:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: route ref(s) {unresolved!r} do not exist "
            "in SiteArchitecture",
        )
    return CheckOutcome(True, f"{_instance_ref(instance)}: route refs resolve")


CHECKS = {
    "CG-CON-001": check_cg_con_001,
    "CG-CON-002": check_cg_con_002,
    "CG-CON-003": check_cg_con_003,
    "CG-CON-004": check_cg_con_004,
    "CG-CON-005": check_cg_con_005,
    "CG-CON-006": check_cg_con_006,
    "CG-CON-007": check_cg_con_007,
    "CG-CON-008": check_cg_con_008,
    "CG-CON-009": check_cg_con_009,
    "CG-CON-010": check_cg_con_010,
}

"""CG-RSP — Responsive gates (AES-WEB-002 §21.7).

Eight gates checking responsive-contract resolution and its emitted
consequences: overflow, mobile ordering, table adaptation, image
behavior, sticky bounds, 200% zoom reflow, and touch-target sizing at
the ``sm`` breakpoint.

Declared-contract checks (CG-RSP-001, -003, -004) run against the real,
frozen
:class:`~engines.website_generation.contracts.components.ResponsiveContract`.
Emitted-consequence checks (CG-RSP-002, -005, -006, -007, -008)
fundamentally require CSS/layout analysis of real output and therefore
run against the synthetic
:class:`~engines.website_generation.gates.checks.SyntheticRenderedPage`
stand-in (AMB-002I-01/03) — not real CSS analysis.

Remediation owner key: R = registry/definition, CE = Component Engine,
RN = renderer/emitter, RC = recipe/LayoutPlan.
"""

from __future__ import annotations

from engines.website_generation.gates.checks import (
    CheckOutcome,
    SyntheticInstance,
    SyntheticRenderedPage,
)

_TABLE_ADAPTATIONS = {"scroll-x", "stacked-rows"}


def _instance_ref(instance: SyntheticInstance) -> str:
    return f"instance={instance.instance_path!r} component={instance.definition.component_id}"


def _page_ref(page: SyntheticRenderedPage) -> str:
    return f"route={page.route!r}"


def check_cg_rsp_001(instance: SyntheticInstance) -> CheckOutcome:
    """CG-RSP-001: every instance has a valid resolved
    ResponsiveContract."""
    contract = instance.definition.responsive_contract
    if contract.touch_target:
        return CheckOutcome(True, f"{_instance_ref(instance)}: responsive contract resolved")
    return CheckOutcome(
        False, f"{_instance_ref(instance)}: responsive contract missing a resolved touch_target"
    )


def check_cg_rsp_002(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RSP-002: no prohibited horizontal overflow at 320px (fixed
    widths > container)."""
    if page.horizontal_overflow_at_320:
        return CheckOutcome(False, f"{_page_ref(page)}: horizontal overflow at 320px")
    return CheckOutcome(True, f"{_page_ref(page)}: no horizontal overflow at 320px")


def check_cg_rsp_003(instance: SyntheticInstance) -> CheckOutcome:
    """CG-RSP-003: mobile order defined; visual-vs-DOM reorder within
    §11.3 rule."""
    contract = instance.definition.responsive_contract
    if not contract.mobile_order:
        return CheckOutcome(False, f"{_instance_ref(instance)}: mobile_order undefined")
    if not instance.mobile_reorder_compliant:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: visual-vs-DOM reorder violates the §11.3 rule",
        )
    return CheckOutcome(True, f"{_instance_ref(instance)}: mobile order defined and compliant")


def check_cg_rsp_004(instance: SyntheticInstance) -> CheckOutcome:
    """CG-RSP-004: tables declare adaptation; no data loss mode."""
    is_table_like = "table" in instance.definition.component_id
    if not is_table_like:
        return CheckOutcome(True, f"{_instance_ref(instance)}: not a table-like component")
    contract = instance.definition.responsive_contract
    if contract.table_adaptation not in _TABLE_ADAPTATIONS:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: table_adaptation "
            f"{contract.table_adaptation!r} not in {sorted(_TABLE_ADAPTATIONS)!r}",
        )
    if instance.table_data_loss:
        return CheckOutcome(False, f"{_instance_ref(instance)}: table adaptation loses data")
    return CheckOutcome(True, f"{_instance_ref(instance)}: table adaptation declared, no data loss")


def check_cg_rsp_005(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RSP-005: image behavior — aspect token + srcset policy
    present."""
    if page.image_aspect_and_srcset_declared:
        return CheckOutcome(True, f"{_page_ref(page)}: image aspect token and srcset declared")
    return CheckOutcome(False, f"{_page_ref(page)}: image aspect token or srcset policy missing")


def check_cg_rsp_006(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RSP-006: sticky behavior bounded (offsets, z-tokens, footer
    clearance)."""
    if page.sticky_bounds_declared:
        return CheckOutcome(True, f"{_page_ref(page)}: sticky behavior bounded")
    return CheckOutcome(False, f"{_page_ref(page)}: sticky behavior not bounded")


def check_cg_rsp_007(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RSP-007: reflow-safe at 200% zoom (CSS analysis of absolute
    units)."""
    if page.reflow_safe_at_200pct:
        return CheckOutcome(True, f"{_page_ref(page)}: reflow-safe at 200% zoom")
    return CheckOutcome(False, f"{_page_ref(page)}: not reflow-safe at 200% zoom")


def check_cg_rsp_008(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RSP-008: touch-target verification at the sm breakpoint."""
    if page.touch_targets_ge_44px_at_sm:
        return CheckOutcome(True, f"{_page_ref(page)}: touch targets >= 44px at sm")
    return CheckOutcome(False, f"{_page_ref(page)}: touch target(s) below 44px at sm")


CHECKS = {
    "CG-RSP-001": check_cg_rsp_001,
    "CG-RSP-002": check_cg_rsp_002,
    "CG-RSP-003": check_cg_rsp_003,
    "CG-RSP-004": check_cg_rsp_004,
    "CG-RSP-005": check_cg_rsp_005,
    "CG-RSP-006": check_cg_rsp_006,
    "CG-RSP-007": check_cg_rsp_007,
    "CG-RSP-008": check_cg_rsp_008,
}

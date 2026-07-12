"""CG-CMP — Composition gates (AES-WEB-002 §21.2).

Eleven gates checking whole-page composition: region placement,
parent/child legality, nesting depth, recursive-family prohibition,
heading/landmark structure, CTA hierarchy, sticky-region limits, and
per-role required-component/section-count ceilings.

CG-CMP-005/006/008 are structural facts (heading order, landmark
uniqueness, nested-interactive prohibition) that AES-WEB-002 §21.2 places
in this family even though their remediation owner is often the renderer
(RN) — they are checked here against the synthetic
:class:`~engines.website_generation.gates.checks.SyntheticPage`'s
composition-level structure snapshot, distinct from the rendering-level
snapshot :mod:`rendering_checks` inspects (AMB-002I-01/03: both are
synthetic stand-ins, not real emitted markup).

Remediation owner key: RC = recipe/LayoutPlan, RN = renderer/emitter.
"""

from __future__ import annotations

from typing import Tuple

from engines.website_generation.constants.components import MAX_COMPOSITION_DEPTH
from engines.website_generation.gates.checks import (
    CheckOutcome,
    SyntheticInstance,
    SyntheticPage,
)

_COMPOSITION_DEPTH_CEILING = MAX_COMPOSITION_DEPTH  # AES-WEB-002 §9.2
_EXEMPT_RECURSIVE_FAMILIES = {"layout", "atom"}  # AES-WEB-002 §9.2 exemption
_MAX_CONCURRENT_STICKY_REGIONS = 2  # AES-WEB-002 §9.2 (CG-CMP-009); not yet
# centralized in constants/components.py and this delivery is not authorized
# to add it there (only constants/gates.py may be modified) — see the
# AES-WEB-002I delivery report.


def _page_ref(page: SyntheticPage) -> str:
    return f"route={page.route!r} role={page.page_role!r}"


def _instance_ref(instance: SyntheticInstance) -> str:
    return f"instance={instance.instance_path!r} component={instance.definition.component_id}"


def check_cg_cmp_001(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CMP-001: every instance's parent region is an allowed region."""
    if instance.region is None:
        return CheckOutcome(False, f"{_instance_ref(instance)}: no parent region set")
    if instance.region in instance.definition.allowed_parent_regions:
        return CheckOutcome(
            True, f"{_instance_ref(instance)}: region {instance.region.value} allowed"
        )
    return CheckOutcome(
        False,
        f"{_instance_ref(instance)}: region {instance.region.value} not in "
        f"allowed_parent_regions "
        f"{[r.value for r in instance.definition.allowed_parent_regions]!r}",
    )


def check_cg_cmp_002(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CMP-002: all children in allowed_child_components, none forbidden."""
    allowed = instance.definition.allowed_child_components
    forbidden = set(instance.definition.forbidden_child_components)
    for child in instance.children:
        child_id = child.definition.component_id
        if child_id in forbidden:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: child {child_id!r} is in "
                "forbidden_child_components",
            )
        if allowed and child_id not in allowed:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: child {child_id!r} not in "
                f"allowed_child_components {allowed!r}",
            )
    return CheckOutcome(True, f"{_instance_ref(instance)}: children legal")


def _max_depth(instance: SyntheticInstance, depth: int = 1) -> int:
    if not instance.children:
        return depth
    return max(_max_depth(c, depth + 1) for c in instance.children)


def check_cg_cmp_003(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CMP-003: composition depth <= 6 (shell=1 ... atom=6, §9.2)."""
    depth = _max_depth(instance)
    if depth <= _COMPOSITION_DEPTH_CEILING:
        return CheckOutcome(True, f"{_instance_ref(instance)}: depth {depth} within ceiling")
    return CheckOutcome(
        False,
        f"{_instance_ref(instance)}: depth {depth} exceeds ceiling "
        f"{_COMPOSITION_DEPTH_CEILING}",
    )


def _find_recursive_family(
    instance: SyntheticInstance, ancestors: Tuple[str, ...]
) -> str:
    family = instance.definition.component_family.value
    if family not in _EXEMPT_RECURSIVE_FAMILIES and family in ancestors:
        return family
    next_ancestors = ancestors + (family,)
    for child in instance.children:
        found = _find_recursive_family(child, next_ancestors)
        if found:
            return found
    return ""


def check_cg_cmp_004(instance: SyntheticInstance) -> CheckOutcome:
    """CG-CMP-004: no recursive composition (family within own subtree,
    layout.*/atom.* exempt)."""
    found = _find_recursive_family(instance, ())
    if found:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: family {found!r} recurs within its own "
            "subtree",
        )
    return CheckOutcome(True, f"{_instance_ref(instance)}: no recursive family composition")


def check_cg_cmp_005(page: SyntheticPage) -> CheckOutcome:
    """CG-CMP-005: exactly one H1, no heading-level skips (§9.3 ownership)."""
    seq = page.heading_sequence
    h1_count = seq.count(1)
    if h1_count != 1:
        return CheckOutcome(
            False, f"{_page_ref(page)}: expected exactly one H1, found {h1_count}"
        )
    for prev, cur in zip(seq, seq[1:]):
        if cur > prev and cur - prev > 1:
            return CheckOutcome(
                False,
                f"{_page_ref(page)}: heading level skip from H{prev} to H{cur} "
                f"in sequence {seq!r}",
            )
    return CheckOutcome(True, f"{_page_ref(page)}: heading hierarchy valid")


def check_cg_cmp_006(page: SyntheticPage) -> CheckOutcome:
    """CG-CMP-006: one main/header/footer; multi-nav labeled."""
    for role in ("main", "header", "footer"):
        count = page.landmark_roles.count(role)
        if count != 1:
            return CheckOutcome(
                False,
                f"{_page_ref(page)}: expected exactly one {role!r} landmark, "
                f"found {count}",
            )
    if page.unlabeled_nav_count > 0:
        nav_count = page.landmark_roles.count("nav")
        if nav_count > 1:
            return CheckOutcome(
                False,
                f"{_page_ref(page)}: {page.unlabeled_nav_count} of {nav_count} "
                "multiple <nav> landmarks are unlabeled",
            )
    return CheckOutcome(True, f"{_page_ref(page)}: landmark hierarchy valid")


def check_cg_cmp_007(page: SyntheticPage) -> CheckOutcome:
    """CG-CMP-007: CTA hierarchy + repetition within §16.3 policy."""
    regions = page.cta_primary_weight_regions
    duplicates = {r for r in regions if regions.count(r) > 1}
    if duplicates:
        return CheckOutcome(
            False,
            f"{_page_ref(page)}: region(s) {sorted(duplicates)!r} carry more than "
            "one primary-weight CTA",
        )
    if page.primary_goal_repetitions > page.primary_goal_repetition_ceiling:
        return CheckOutcome(
            False,
            f"{_page_ref(page)}: primary goal repeats "
            f"{page.primary_goal_repetitions} times, exceeds ceiling "
            f"{page.primary_goal_repetition_ceiling}",
        )
    return CheckOutcome(True, f"{_page_ref(page)}: CTA hierarchy within policy")


def check_cg_cmp_008(page: SyntheticPage) -> CheckOutcome:
    """CG-CMP-008: no nested interactive controls."""
    if page.nested_interactive_controls:
        return CheckOutcome(
            False,
            f"{_page_ref(page)}: nested interactive control(s) "
            f"{page.nested_interactive_controls!r}",
        )
    return CheckOutcome(True, f"{_page_ref(page)}: no nested interactive controls")


def check_cg_cmp_009(page: SyntheticPage) -> CheckOutcome:
    """CG-CMP-009: <= 2 concurrent sticky regions; no sticky overlap."""
    if page.sticky_region_count > _MAX_CONCURRENT_STICKY_REGIONS:
        return CheckOutcome(
            False,
            f"{_page_ref(page)}: {page.sticky_region_count} concurrent sticky "
            f"regions exceeds ceiling {_MAX_CONCURRENT_STICKY_REGIONS}",
        )
    if page.sticky_regions_overlap:
        return CheckOutcome(False, f"{_page_ref(page)}: sticky regions overlap")
    return CheckOutcome(True, f"{_page_ref(page)}: sticky region count and overlap within policy")


def check_cg_cmp_010(page: SyntheticPage) -> CheckOutcome:
    """CG-CMP-010: required role components present per §6.1 matrix
    (extends AES-WEB-001 structural family; registered alongside
    CG-STR-006 zero-state rule)."""
    if page.required_role_components_present:
        return CheckOutcome(True, f"{_page_ref(page)}: required role components present")
    return CheckOutcome(
        False,
        f"{_page_ref(page)}: one or more §6.1-required components missing for "
        f"role {page.page_role!r}",
    )


def check_cg_cmp_011(page: SyntheticPage) -> CheckOutcome:
    """CG-CMP-011 (WARNING): section count <= role ceiling."""
    if page.section_count <= page.section_ceiling:
        return CheckOutcome(
            True,
            f"{_page_ref(page)}: {page.section_count} sections within ceiling "
            f"{page.section_ceiling}",
        )
    return CheckOutcome(
        False,
        f"{_page_ref(page)}: {page.section_count} sections exceeds ceiling "
        f"{page.section_ceiling}",
    )


CHECKS = {
    "CG-CMP-001": check_cg_cmp_001,
    "CG-CMP-002": check_cg_cmp_002,
    "CG-CMP-003": check_cg_cmp_003,
    "CG-CMP-004": check_cg_cmp_004,
    "CG-CMP-005": check_cg_cmp_005,
    "CG-CMP-006": check_cg_cmp_006,
    "CG-CMP-007": check_cg_cmp_007,
    "CG-CMP-008": check_cg_cmp_008,
    "CG-CMP-009": check_cg_cmp_009,
    "CG-CMP-010": check_cg_cmp_010,
    "CG-CMP-011": check_cg_cmp_011,
}

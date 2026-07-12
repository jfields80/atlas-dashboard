"""CG-COM — Commercial gates (AES-WEB-002 §21.6).

Twelve gates enforcing the E1-E11 ethical-conversion doctrine (AES-WEB-002
§2.6, ADR-12) and the monetization/conversion architecture (§16, §17):
sponsored/featured disclosure, ranked-list rationale, review evidence,
verification-badge honesty, urgency honesty, price-disclaimer honesty,
consent fairness, CTA label/goal alignment, trust adjacency, form
friction budgets, conversion-hierarchy resolution, and monetization
role/cap permission.

Checks run against the synthetic
:class:`~engines.website_generation.gates.checks.SyntheticInstance`
binding facts (AMB-002I-01/03) layered on the real, frozen
:class:`~engines.website_generation.contracts.components.ConversionContract`
/ :class:`~engines.website_generation.contracts.components.MonetizationContract`.
Threshold data (CTA label classes, form friction budgets, primary-goal
repetition ceiling) is imported from ``constants/components.py`` rather
than reinvented, per that module's own §16/§16.5 declarations (several of
which already cite "enforcement is gate work... AES-WEB-002I" in their
comments).

Remediation owner key: RN = renderer/emitter, CE = Component Engine,
CT = content, RC = recipe/LayoutPlan, R = registry/definition.
"""

from __future__ import annotations

from engines.website_generation.constants.components import (
    CTA_GOAL_LABEL_CLASSES,
    FORM_FRICTION_BUDGET_MAX_REQUIRED_FIELDS,
)
from engines.website_generation.gates.checks import CheckOutcome, SyntheticInstance

_SPONSORED_LISTING_KINDS = {"SPONSORED", "FEATURED"}
_RANKED_LISTING_KINDS = {"RANKED", "EDITORIAL_PICK", "CURATED"}


def _instance_ref(instance: SyntheticInstance) -> str:
    return f"instance={instance.instance_path!r} component={instance.definition.component_id}"


def check_cg_com_001(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-001: every SPONSORED/FEATURED render carries visible +
    semantic disclosure (E5)."""
    if instance.listing_kind not in _SPONSORED_LISTING_KINDS:
        return CheckOutcome(True, f"{_instance_ref(instance)}: not sponsored/featured")
    if not instance.disclosure_visible:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: {instance.listing_kind} listing missing "
            "visible disclosure",
        )
    if not instance.disclosure_semantic_attrs:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: {instance.listing_kind} listing missing "
            "semantic disclosure attributes",
        )
    return CheckOutcome(True, f"{_instance_ref(instance)}: sponsored/featured disclosure present")


def check_cg_com_002(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-002: ranked lists bind rationale/methodology; sponsored
    never presented as rank (E6)."""
    if instance.listing_kind == "SPONSORED" and instance.rank_position is not None:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: SPONSORED listing presented at rank "
            f"{instance.rank_position}",
        )
    if instance.listing_kind in _RANKED_LISTING_KINDS and instance.rank_position is not None:
        if not instance.rank_rationale_bound:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: ranked listing at position "
                f"{instance.rank_position} has no bound rationale",
            )
    return CheckOutcome(True, f"{_instance_ref(instance)}: ranking/rationale rules satisfied")


def check_cg_com_003(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-003: every review/testimonial block carries evidence_ref (E2)."""
    is_review_like = instance.definition.component_id.startswith(
        ("trust.review", "trust.testimonial")
    )
    if not is_review_like:
        return CheckOutcome(True, f"{_instance_ref(instance)}: not a review/testimonial block")
    if instance.evidence_ref:
        return CheckOutcome(True, f"{_instance_ref(instance)}: evidence_ref bound")
    return CheckOutcome(False, f"{_instance_ref(instance)}: review/testimonial missing evidence_ref")


def check_cg_com_004(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-004: verification badges render only on VERIFIED content
    state (E10)."""
    if instance.verification_badge_rendered and instance.verification_state != "VERIFIED":
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: verification badge rendered on state "
            f"{instance.verification_state!r}, not VERIFIED",
        )
    return CheckOutcome(True, f"{_instance_ref(instance)}: verification badge state honest")


def check_cg_com_005(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-005: urgency claims reference a spec-backed offer with
    expiry (E1)."""
    if not instance.urgency_claim:
        return CheckOutcome(True, f"{_instance_ref(instance)}: no urgency claim")
    if instance.urgency_offer_expiry:
        return CheckOutcome(True, f"{_instance_ref(instance)}: urgency claim has bound expiry")
    return CheckOutcome(
        False, f"{_instance_ref(instance)}: urgency claim without a spec-backed offer expiry"
    )


def check_cg_com_006(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-006: non-exact PriceSpec renders bound disclaimer (E4)."""
    if instance.price_exact:
        return CheckOutcome(True, f"{_instance_ref(instance)}: price is exact, no disclaimer needed")
    if instance.price_disclaimer_bound:
        return CheckOutcome(True, f"{_instance_ref(instance)}: non-exact price has bound disclaimer")
    return CheckOutcome(False, f"{_instance_ref(instance)}: non-exact price missing bound disclaimer")


def check_cg_com_007(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-007: consent controls equal-weight; no pre-checked marketing
    consent (E8)."""
    if instance.consent_prechecked_marketing:
        return CheckOutcome(False, f"{_instance_ref(instance)}: marketing consent pre-checked")
    if not instance.consent_equal_weight:
        return CheckOutcome(False, f"{_instance_ref(instance)}: consent controls not equal-weight")
    return CheckOutcome(True, f"{_instance_ref(instance)}: consent controls honest")


def check_cg_com_008(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-008: CTA label class matches conversion goal (E9 table)."""
    contract = instance.definition.conversion_contract
    if contract is None:
        return CheckOutcome(True, f"{_instance_ref(instance)}: not conversion-bearing")
    allowed = CTA_GOAL_LABEL_CLASSES.get(contract.conversion_goal.value)
    if allowed is None:
        return CheckOutcome(
            True,
            f"{_instance_ref(instance)}: goal {contract.conversion_goal.value} has no "
            "registered label-class table entry",
        )
    if instance.cta_label_class in allowed:
        return CheckOutcome(True, f"{_instance_ref(instance)}: CTA label class matches goal")
    return CheckOutcome(
        False,
        f"{_instance_ref(instance)}: CTA label class {instance.cta_label_class!r} not in "
        f"{allowed!r} for goal {contract.conversion_goal.value}",
    )


def check_cg_com_009(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-009 (WARNING): trust component adjacent to lead forms."""
    is_lead_form = instance.definition.commercial_purpose.value == "COLLECT_LEAD"
    if not is_lead_form:
        return CheckOutcome(True, f"{_instance_ref(instance)}: not a lead-collecting component")
    if instance.trust_adjacent:
        return CheckOutcome(True, f"{_instance_ref(instance)}: trust component adjacent")
    return CheckOutcome(False, f"{_instance_ref(instance)}: lead form has no adjacent trust component")


def check_cg_com_010(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-010 (WARNING): form friction budgets (§16.5) — required-field
    ceiling."""
    if instance.bound_field_count <= FORM_FRICTION_BUDGET_MAX_REQUIRED_FIELDS:
        return CheckOutcome(
            True,
            f"{_instance_ref(instance)}: {instance.bound_field_count} required fields "
            f"within ceiling {FORM_FRICTION_BUDGET_MAX_REQUIRED_FIELDS}",
        )
    return CheckOutcome(
        False,
        f"{_instance_ref(instance)}: {instance.bound_field_count} required fields exceeds "
        f"ceiling {FORM_FRICTION_BUDGET_MAX_REQUIRED_FIELDS}",
    )


def check_cg_com_011(instance: SyntheticInstance) -> CheckOutcome:
    """CG-COM-011: page conversion hierarchy matches recipe resolution
    (§16.6)."""
    if instance.conversion_hierarchy_rank is None or instance.recipe_hierarchy_rank is None:
        return CheckOutcome(True, f"{_instance_ref(instance)}: no declared hierarchy rank")
    if instance.conversion_hierarchy_rank == instance.recipe_hierarchy_rank:
        return CheckOutcome(True, f"{_instance_ref(instance)}: hierarchy matches recipe resolution")
    return CheckOutcome(
        False,
        f"{_instance_ref(instance)}: rendered hierarchy rank "
        f"{instance.conversion_hierarchy_rank} does not match recipe-resolved rank "
        f"{instance.recipe_hierarchy_rank}",
    )


def check_cg_com_012(
    instance: SyntheticInstance, permitted_roles: frozenset
) -> CheckOutcome:
    """CG-COM-012: monetization blocks appear only on roles permitted by
    §6.1; per-page sponsored caps."""
    if instance.definition.monetization_contract is not None:
        if instance.page_role and instance.page_role not in permitted_roles:
            return CheckOutcome(
                False,
                f"{_instance_ref(instance)}: monetization block on disallowed role "
                f"{instance.page_role!r}",
            )
    if instance.page_sponsored_count > instance.page_sponsored_cap:
        return CheckOutcome(
            False,
            f"{_instance_ref(instance)}: page sponsored count "
            f"{instance.page_sponsored_count} exceeds cap {instance.page_sponsored_cap}",
        )
    return CheckOutcome(True, f"{_instance_ref(instance)}: monetization role and cap rules satisfied")


CHECKS = {
    "CG-COM-001": check_cg_com_001,
    "CG-COM-002": check_cg_com_002,
    "CG-COM-003": check_cg_com_003,
    "CG-COM-004": check_cg_com_004,
    "CG-COM-005": check_cg_com_005,
    "CG-COM-006": check_cg_com_006,
    "CG-COM-007": check_cg_com_007,
    "CG-COM-008": check_cg_com_008,
    "CG-COM-009": check_cg_com_009,
    "CG-COM-010": check_cg_com_010,
    "CG-COM-011": check_cg_com_011,
    "CG-COM-012": check_cg_com_012,
}

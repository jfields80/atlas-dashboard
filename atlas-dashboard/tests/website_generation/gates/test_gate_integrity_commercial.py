"""Two-fixture law tests for CG-COM (AES-WEB-002 §21.6; 12 gates).

Enforces the E1-E11 ethical-conversion doctrine (AES-WEB-002 §2.6,
ADR-12) against synthetic :class:`SyntheticInstance` binding facts
(AMB-002I-01/03).
"""

from __future__ import annotations

from engines.website_generation.contracts.components import ConversionContract
from engines.website_generation.contracts.enums import CommercialPurpose, ConversionGoal
from engines.website_generation.gates.checks import commercial_checks

from ..components import make_definition
from .test_gate_integrity import assert_two_fixture_law, instance

TESTED_GATE_IDS = frozenset(commercial_checks.CHECKS)


class TestCGCom001SponsoredDisclosure:
    def test_two_fixture_law(self):
        good = instance(
            listing_kind="SPONSORED",
            disclosure_visible=True,
            disclosure_semantic_attrs={"data-listing-kind": "sponsored"},
        )
        bad = instance(listing_kind="SPONSORED", disclosure_visible=False)
        assert_two_fixture_law(commercial_checks.check_cg_com_001, good, bad)

    def test_organic_listing_needs_no_disclosure(self):
        good = instance(listing_kind="ORGANIC", disclosure_visible=False)
        assert commercial_checks.check_cg_com_001(good).passed is True


class TestCGCom002RankedListRationale:
    def test_two_fixture_law(self):
        good = instance(listing_kind="RANKED", rank_position=1, rank_rationale_bound=True)
        bad = instance(listing_kind="SPONSORED", rank_position=2)
        assert_two_fixture_law(commercial_checks.check_cg_com_002, good, bad)

    def test_ranked_without_rationale_fails(self):
        bad = instance(listing_kind="RANKED", rank_position=1, rank_rationale_bound=False)
        assert commercial_checks.check_cg_com_002(bad).passed is False


class TestCGCom003ReviewEvidenceRef:
    def test_two_fixture_law(self):
        d = make_definition(component_id="trust.review.summary")
        good = instance(definition=d, evidence_ref="review-src-42")
        bad = instance(definition=d, evidence_ref="")
        assert_two_fixture_law(commercial_checks.check_cg_com_003, good, bad)

    def test_non_review_component_exempt(self):
        good = instance(definition=make_definition(component_id="hero.split.value-proposition"))
        assert commercial_checks.check_cg_com_003(good).passed is True


class TestCGCom004VerificationBadgeHonest:
    def test_two_fixture_law(self):
        good = instance(verification_badge_rendered=True, verification_state="VERIFIED")
        bad = instance(verification_badge_rendered=True, verification_state="PENDING")
        assert_two_fixture_law(commercial_checks.check_cg_com_004, good, bad)


class TestCGCom005UrgencyClaimExpiry:
    def test_two_fixture_law(self):
        good = instance(urgency_claim=True, urgency_offer_expiry="2026-08-01")
        bad = instance(urgency_claim=True, urgency_offer_expiry="")
        assert_two_fixture_law(commercial_checks.check_cg_com_005, good, bad)


class TestCGCom006PriceDisclaimer:
    def test_two_fixture_law(self):
        good = instance(price_exact=False, price_disclaimer_bound=True)
        bad = instance(price_exact=False, price_disclaimer_bound=False)
        assert_two_fixture_law(commercial_checks.check_cg_com_006, good, bad)


class TestCGCom007ConsentFairness:
    def test_two_fixture_law(self):
        good = instance(consent_prechecked_marketing=False, consent_equal_weight=True)
        bad = instance(consent_prechecked_marketing=True, consent_equal_weight=True)
        assert_two_fixture_law(commercial_checks.check_cg_com_007, good, bad)


class TestCGCom008CtaLabelMatchesGoal:
    def test_two_fixture_law(self):
        d = make_definition(
            conversion_contract=ConversionContract(conversion_goal=ConversionGoal.LISTING_CLAIM)
        )
        good = instance(definition=d, cta_label_class="claim")
        bad = instance(definition=d, cta_label_class="subscribe")
        assert_two_fixture_law(commercial_checks.check_cg_com_008, good, bad)

    def test_non_conversion_component_exempt(self):
        good = instance(definition=make_definition(conversion_contract=None))
        assert commercial_checks.check_cg_com_008(good).passed is True


class TestCGCom009TrustAdjacentToLeadForms:
    def test_two_fixture_law(self):
        d = make_definition(commercial_purpose=CommercialPurpose.COLLECT_LEAD)
        good = instance(definition=d, trust_adjacent=True)
        bad = instance(definition=d, trust_adjacent=False)
        assert_two_fixture_law(commercial_checks.check_cg_com_009, good, bad)


class TestCGCom010FormFrictionBudget:
    def test_two_fixture_law(self):
        good = instance(bound_field_count=4)
        bad = instance(bound_field_count=6)
        assert_two_fixture_law(commercial_checks.check_cg_com_010, good, bad)


class TestCGCom011ConversionHierarchyMatchesRecipe:
    def test_two_fixture_law(self):
        good = instance(conversion_hierarchy_rank=1, recipe_hierarchy_rank=1)
        bad = instance(conversion_hierarchy_rank=2, recipe_hierarchy_rank=1)
        assert_two_fixture_law(commercial_checks.check_cg_com_011, good, bad)


class TestCGCom012MonetizationRoleAndCap:
    def test_two_fixture_law(self):
        from engines.website_generation.contracts.components import MonetizationContract

        d = make_definition(monetization_contract=MonetizationContract())
        good = instance(
            definition=d, page_role="category", page_sponsored_count=2, page_sponsored_cap=3
        )
        bad = instance(definition=d, page_role="verification")
        assert_two_fixture_law(
            lambda i: commercial_checks.check_cg_com_012(
                i, permitted_roles=frozenset({"category", "home"})
            ),
            good,
            bad,
        )

    def test_sponsored_cap_exceeded_fails(self):
        bad = instance(page_sponsored_count=5, page_sponsored_cap=3)
        outcome = commercial_checks.check_cg_com_012(bad, permitted_roles=frozenset({"home"}))
        assert outcome.passed is False

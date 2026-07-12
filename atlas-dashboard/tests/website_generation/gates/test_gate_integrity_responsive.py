"""Two-fixture law tests for CG-RSP (AES-WEB-002 §21.7; 8 gates).

CG-RSP-001/003/004 operate on the real, frozen
:class:`~engines.website_generation.contracts.components.ResponsiveContract`
via :class:`SyntheticInstance`; CG-RSP-002/005/006/007/008 require
CSS/layout analysis of real output and run against the synthetic
:class:`SyntheticRenderedPage` stand-in (AMB-002I-01/03).
"""

from __future__ import annotations

from engines.website_generation.contracts.components import ResponsiveContract
from engines.website_generation.gates.checks import responsive_checks

from ..components import make_definition
from .test_gate_integrity import assert_two_fixture_law, instance, rendered_page

TESTED_GATE_IDS = frozenset(responsive_checks.CHECKS)


class TestCGRsp001ResponsiveContractResolved:
    def test_two_fixture_law(self):
        good = instance(
            definition=make_definition(
                responsive_contract=ResponsiveContract(touch_target="44px")
            )
        )
        bad = instance(
            definition=make_definition(responsive_contract=ResponsiveContract(touch_target=""))
        )
        assert_two_fixture_law(responsive_checks.check_cg_rsp_001, good, bad)


class TestCGRsp002NoHorizontalOverflow:
    def test_two_fixture_law(self):
        good = rendered_page(horizontal_overflow_at_320=False)
        bad = rendered_page(horizontal_overflow_at_320=True)
        assert_two_fixture_law(responsive_checks.check_cg_rsp_002, good, bad)


class TestCGRsp003MobileOrderDefined:
    def test_two_fixture_law(self):
        good = instance(
            definition=make_definition(
                responsive_contract=ResponsiveContract(mobile_order="priority-1")
            ),
            mobile_reorder_compliant=True,
        )
        bad = instance(
            definition=make_definition(
                responsive_contract=ResponsiveContract(mobile_order="priority-1")
            ),
            mobile_reorder_compliant=False,
        )
        assert_two_fixture_law(responsive_checks.check_cg_rsp_003, good, bad)


class TestCGRsp004TablesDeclareAdaptation:
    def test_two_fixture_law(self):
        d = make_definition(
            component_id="content.table.comparison",
            responsive_contract=ResponsiveContract(table_adaptation="scroll-x"),
        )
        good = instance(definition=d, table_data_loss=False)
        bad_def = make_definition(
            component_id="content.table.comparison",
            responsive_contract=ResponsiveContract(table_adaptation=""),
        )
        bad = instance(definition=bad_def)
        assert_two_fixture_law(responsive_checks.check_cg_rsp_004, good, bad)

    def test_non_table_component_exempt(self):
        good = instance(definition=make_definition(component_id="hero.split.value-proposition"))
        assert responsive_checks.check_cg_rsp_004(good).passed is True


class TestCGRsp005ImageAspectAndSrcset:
    def test_two_fixture_law(self):
        good = rendered_page(image_aspect_and_srcset_declared=True)
        bad = rendered_page(image_aspect_and_srcset_declared=False)
        assert_two_fixture_law(responsive_checks.check_cg_rsp_005, good, bad)


class TestCGRsp006StickyBoundsDeclared:
    def test_two_fixture_law(self):
        good = rendered_page(sticky_bounds_declared=True)
        bad = rendered_page(sticky_bounds_declared=False)
        assert_two_fixture_law(responsive_checks.check_cg_rsp_006, good, bad)


class TestCGRsp007ReflowSafeAt200Percent:
    def test_two_fixture_law(self):
        good = rendered_page(reflow_safe_at_200pct=True)
        bad = rendered_page(reflow_safe_at_200pct=False)
        assert_two_fixture_law(responsive_checks.check_cg_rsp_007, good, bad)


class TestCGRsp008TouchTargetsAtSm:
    def test_two_fixture_law(self):
        good = rendered_page(touch_targets_ge_44px_at_sm=True)
        bad = rendered_page(touch_targets_ge_44px_at_sm=False)
        assert_two_fixture_law(responsive_checks.check_cg_rsp_008, good, bad)

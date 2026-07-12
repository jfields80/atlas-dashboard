"""Two-fixture law tests for CG-CMP (AES-WEB-002 §21.2; 11 gates).

CG-CMP-001-004 operate on a :class:`SyntheticInstance` tree (parent
region, children, depth, recursion); CG-CMP-005-011 operate on a
:class:`SyntheticPage` (heading/landmark/CTA/sticky/section facts).
"""

from __future__ import annotations

from engines.website_generation.contracts.enums import ComponentFamily, RegionKind
from engines.website_generation.gates.checks import composition_checks

from ..components import make_definition
from .test_gate_integrity import assert_two_fixture_law, instance, page

TESTED_GATE_IDS = frozenset(composition_checks.CHECKS)


def _def(**overrides):
    return make_definition(**overrides)


class TestCGCmp001ParentRegionAllowed:
    def test_two_fixture_law(self):
        d = _def(allowed_parent_regions=(RegionKind.BODY,))
        good = instance(definition=d, region=RegionKind.BODY)
        bad = instance(definition=d, region=RegionKind.HEADER)
        assert_two_fixture_law(composition_checks.check_cg_cmp_001, good, bad)


class TestCGCmp002ChildrenLegal:
    def test_two_fixture_law(self):
        d = _def(
            allowed_child_components=("listing.card.standard",),
            forbidden_child_components=("monetization.ribbon.sponsor",),
        )
        child_ok = instance(
            instance_path="child-1",
            definition=_def(component_id="listing.card.standard"),
        )
        child_forbidden = instance(
            instance_path="child-2",
            definition=_def(component_id="monetization.ribbon.sponsor"),
        )
        good = instance(definition=d, children=(child_ok,))
        bad = instance(definition=d, children=(child_forbidden,))
        assert_two_fixture_law(composition_checks.check_cg_cmp_002, good, bad)


class TestCGCmp003CompositionDepth:
    def test_two_fixture_law(self):
        leaf = instance(instance_path="leaf")
        shallow = instance(instance_path="root", children=(leaf,))

        deep = leaf
        for i in range(7):
            deep = instance(instance_path=f"nest-{i}", children=(deep,))

        assert_two_fixture_law(composition_checks.check_cg_cmp_003, shallow, deep)


class TestCGCmp004NoRecursiveFamily:
    def test_two_fixture_law(self):
        inner_ok = instance(
            instance_path="inner", definition=_def(component_family=ComponentFamily.TRUST)
        )
        good = instance(
            instance_path="outer",
            definition=_def(component_family=ComponentFamily.HERO),
            children=(inner_ok,),
        )

        inner_recursive = instance(
            instance_path="inner", definition=_def(component_family=ComponentFamily.HERO)
        )
        bad = instance(
            instance_path="outer",
            definition=_def(component_family=ComponentFamily.HERO),
            children=(inner_recursive,),
        )
        assert_two_fixture_law(composition_checks.check_cg_cmp_004, good, bad)

    def test_layout_family_exempt_from_recursion_rule(self):
        inner = instance(
            instance_path="inner", definition=_def(component_family=ComponentFamily.LAYOUT)
        )
        exempt = instance(
            instance_path="outer",
            definition=_def(component_family=ComponentFamily.LAYOUT),
            children=(inner,),
        )
        assert composition_checks.check_cg_cmp_004(exempt).passed is True


class TestCGCmp005HeadingHierarchy:
    def test_two_fixture_law(self):
        good = page(heading_sequence=(1, 2, 2, 3))
        bad = page(heading_sequence=(1, 3))  # skips H2
        assert_two_fixture_law(composition_checks.check_cg_cmp_005, good, bad)

    def test_multiple_h1_fails(self):
        bad = page(heading_sequence=(1, 1, 2))
        assert composition_checks.check_cg_cmp_005(bad).passed is False


class TestCGCmp006LandmarkHierarchy:
    def test_two_fixture_law(self):
        good = page(landmark_roles=("header", "main", "footer"))
        bad = page(landmark_roles=("header", "header", "main", "footer"))
        assert_two_fixture_law(composition_checks.check_cg_cmp_006, good, bad)

    def test_multiple_unlabeled_nav_fails(self):
        bad = page(
            landmark_roles=("header", "main", "footer", "nav", "nav"),
            unlabeled_nav_count=1,
        )
        assert composition_checks.check_cg_cmp_006(bad).passed is False


class TestCGCmp007CtaHierarchy:
    def test_two_fixture_law(self):
        good = page(cta_primary_weight_regions=("HERO", "STICKY_MOBILE"), primary_goal_repetitions=2)
        bad = page(cta_primary_weight_regions=("HERO", "HERO"), primary_goal_repetitions=2)
        assert_two_fixture_law(composition_checks.check_cg_cmp_007, good, bad)

    def test_repetition_ceiling_exceeded_fails(self):
        bad = page(primary_goal_repetitions=4, primary_goal_repetition_ceiling=3)
        assert composition_checks.check_cg_cmp_007(bad).passed is False


class TestCGCmp008NoNestedInteractive:
    def test_two_fixture_law(self):
        good = page(nested_interactive_controls=())
        bad = page(nested_interactive_controls=("button-inside-anchor",))
        assert_two_fixture_law(composition_checks.check_cg_cmp_008, good, bad)


class TestCGCmp009StickyRegionLimit:
    def test_two_fixture_law(self):
        good = page(sticky_region_count=2, sticky_regions_overlap=False)
        bad = page(sticky_region_count=3, sticky_regions_overlap=False)
        assert_two_fixture_law(composition_checks.check_cg_cmp_009, good, bad)

    def test_overlap_fails_even_under_count_ceiling(self):
        bad = page(sticky_region_count=1, sticky_regions_overlap=True)
        assert composition_checks.check_cg_cmp_009(bad).passed is False


class TestCGCmp010RequiredRoleComponentsPresent:
    def test_two_fixture_law(self):
        good = page(required_role_components_present=True)
        bad = page(required_role_components_present=False)
        assert_two_fixture_law(composition_checks.check_cg_cmp_010, good, bad)


class TestCGCmp011SectionCountCeiling:
    def test_two_fixture_law(self):
        good = page(section_count=10, section_ceiling=12)
        bad = page(section_count=13, section_ceiling=12)
        assert_two_fixture_law(composition_checks.check_cg_cmp_011, good, bad)

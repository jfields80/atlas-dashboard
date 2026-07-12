"""Two-fixture law tests for CG-CON (AES-WEB-002 §21.1; 10 gates).

Each test builds one good and one bad :class:`SyntheticInstance` fixture
and asserts ``component_checks.check_cg_con_NNN`` passes the good fixture
and fails the bad one (AES-WEB-001 §10.4). Fixtures are frozen, in-code,
synthetic data (AMB-002I-03) — see test_gate_integrity.py for shared
helpers.
"""

from __future__ import annotations

from engines.website_generation.contracts.components import (
    PropSpec,
    SlotSpec,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    AssetRole,
    LifecycleStatus,
    PropType,
    SlotCardinality,
)
from engines.website_generation.gates.checks import component_checks

from ..components import make_definition
from .test_gate_integrity import assert_two_fixture_law, instance

TESTED_GATE_IDS = frozenset(component_checks.CHECKS)


def _rich_definition(**overrides):
    fields = dict(
        required_props={
            "layout": PropSpec(prop_type=PropType.STR_ENUM, enum_values=("split", "stacked")),
            "priority": PropSpec(prop_type=PropType.INT_BOUNDED, int_min=1, int_max=5),
            "logo": PropSpec(prop_type=PropType.ASSET_REF),
        },
        optional_props={
            "featured": PropSpec(prop_type=PropType.BOOL),
        },
        required_content_slots={
            "headline": SlotSpec(
                block_type="richtext", cardinality=SlotCardinality.EXACTLY_ONE
            ),
        },
        supported_variants={"compact": VariantSpec(display_name="Compact")},
        supported_asset_roles=(AssetRole.LOGO,),
        compatibility_range={"renderer": "1.x"},
    )
    fields.update(overrides)
    return make_definition(**fields)


class TestCGCon001IdInRegistry:
    def test_two_fixture_law(self):
        good = instance(registry_known_ids=("hero.split.value-proposition",))
        bad = instance(registry_known_ids=("some.other.component",))
        assert_two_fixture_law(component_checks.check_cg_con_001, good, bad)


class TestCGCon002VersionSupported:
    def test_two_fixture_law(self):
        good = instance(requested_version="")
        bad = instance(requested_version="9.9.9")
        assert_two_fixture_law(component_checks.check_cg_con_002, good, bad)


class TestCGCon003RequiredPropsBoundAndValid:
    def test_two_fixture_law(self):
        good = instance(
            definition=_rich_definition(),
            bound_required_props={"layout": "split", "priority": "3", "logo": "asset://logo"},
        )
        bad = instance(
            definition=_rich_definition(),
            bound_required_props={"layout": "grid", "priority": "3", "logo": "asset://logo"},
        )
        assert_two_fixture_law(component_checks.check_cg_con_003, good, bad)

    def test_out_of_bounds_int_fails(self):
        bad = instance(
            definition=_rich_definition(),
            bound_required_props={"layout": "split", "priority": "99", "logo": "asset://logo"},
        )
        assert component_checks.check_cg_con_003(bad).passed is False


class TestCGCon004NoUnknownProps:
    def test_two_fixture_law(self):
        good = instance(
            definition=_rich_definition(),
            bound_required_props={"layout": "split", "priority": "3", "logo": "asset://logo"},
        )
        bad = instance(
            definition=_rich_definition(),
            bound_required_props={"layout": "split", "priority": "3", "logo": "asset://logo"},
            bound_optional_props={"color": "red"},
        )
        assert_two_fixture_law(component_checks.check_cg_con_004, good, bad)


class TestCGCon005RequiredSlotsBound:
    def test_two_fixture_law(self):
        good = instance(
            definition=_rich_definition(),
            bound_required_slots={"headline": ("content-block-1",)},
        )
        bad = instance(definition=_rich_definition(), bound_required_slots={})
        assert_two_fixture_law(component_checks.check_cg_con_005, good, bad)

    def test_cardinality_violation_fails(self):
        bad = instance(
            definition=_rich_definition(),
            bound_required_slots={"headline": ("block-1", "block-2")},
        )
        assert component_checks.check_cg_con_005(bad).passed is False


class TestCGCon006VariantSupported:
    def test_two_fixture_law(self):
        good = instance(definition=_rich_definition(), variant="compact")
        bad = instance(definition=_rich_definition(), variant="ultra-wide")
        assert_two_fixture_law(component_checks.check_cg_con_006, good, bad)


class TestCGCon007LifecycleCertifiable:
    def test_two_fixture_law(self):
        good = instance(definition=make_definition(lifecycle_status=LifecycleStatus.PROPOSED))
        bad = instance(
            definition=make_definition(lifecycle_status=LifecycleStatus.DEPRECATED),
            build_allows_deprecated=False,
        )
        assert_two_fixture_law(component_checks.check_cg_con_007, good, bad)

    def test_deprecated_with_allowance_passes(self):
        good = instance(
            definition=make_definition(lifecycle_status=LifecycleStatus.DEPRECATED),
            build_allows_deprecated=True,
        )
        assert component_checks.check_cg_con_007(good).passed is True

    def test_retired_never_passes_even_with_allowance(self):
        bad = instance(
            definition=make_definition(lifecycle_status=LifecycleStatus.RETIRED),
            build_allows_deprecated=True,
        )
        assert component_checks.check_cg_con_007(bad).passed is False

    def test_experimental_prefix_never_certifiable(self):
        bad = instance(
            definition=make_definition(
                component_id="x.hero.split.value-proposition",
                lifecycle_status=LifecycleStatus.EXPERIMENTAL,
            )
        )
        assert component_checks.check_cg_con_007(bad).passed is False


class TestCGCon008CompatibilityRangeSatisfied:
    def test_two_fixture_law(self):
        good = instance(
            definition=_rich_definition(),
            compatibility_environment={"renderer": "1.x"},
        )
        bad = instance(
            definition=_rich_definition(),
            compatibility_environment={"renderer": "2.x"},
        )
        assert_two_fixture_law(component_checks.check_cg_con_008, good, bad)


class TestCGCon009AssetRefsResolve:
    def test_two_fixture_law(self):
        good = instance(
            definition=_rich_definition(),
            bound_required_props={"layout": "split", "priority": "3", "logo": "asset://logo"},
            asset_ref_roles={"asset://logo": AssetRole.LOGO.value},
        )
        bad = instance(
            definition=_rich_definition(),
            bound_required_props={"layout": "split", "priority": "3", "logo": "asset://logo"},
            asset_ref_roles={},
        )
        assert_two_fixture_law(component_checks.check_cg_con_009, good, bad)

    def test_wrong_asset_role_fails(self):
        bad = instance(
            definition=_rich_definition(),
            bound_required_props={"layout": "split", "priority": "3", "logo": "asset://logo"},
            asset_ref_roles={"asset://logo": AssetRole.GALLERY_IMAGE.value},
        )
        assert component_checks.check_cg_con_009(bad).passed is False


class TestCGCon010RouteRefsResolve:
    def test_two_fixture_law(self):
        good = instance(
            route_refs=("/category/parks",), resolved_routes=("/category/parks",)
        )
        bad = instance(route_refs=("/category/parks",), resolved_routes=())
        assert_two_fixture_law(component_checks.check_cg_con_010, good, bad)

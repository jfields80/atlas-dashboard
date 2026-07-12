"""Gate-integrity suite: shared fixture helpers + completeness check
(AES-WEB-002I; AES-WEB-001 §10.4 two-fixture law).

Per-gate good/bad fixture tests live in the five sibling
``test_gate_integrity_<family>.py`` modules (one per authorized check
module), split out for readability given the AES-WEB-002 §21 catalog's
size (AMB-002I-01/03; operator instruction: "additional narrowly focused
test files under tests/website_generation/gates/ ... to keep the test
suite readable"). This module holds the fixture-building helpers they
share and the final completeness assertion: every executable gate ID
registered in ``constants/gates.py`` has a two-fixture test somewhere in
this package.

Fixtures are frozen, deterministic, in-code synthetic Python objects
(AMB-002I-03) — not files under ``tests/website_generation/fixtures/``.
"""

from __future__ import annotations

from engines.website_generation.contracts.components import (
    AccessibilityContract,
    AnalyticsContract,
    ComponentDefinition,
    ConversionContract,
    MonetizationContract,
    PropSpec,
    RenderingContract,
    ResponsiveContract,
    SlotSpec,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    ConversionGoal,
    LifecycleStatus,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
)
from engines.website_generation.constants.gates import EXECUTABLE_COMPONENT_GATE_IDS
from engines.website_generation.gates.checks import (
    SyntheticInstance,
    SyntheticPage,
    SyntheticRenderedPage,
)

from ..components import make_definition


def instance(**overrides) -> SyntheticInstance:
    """Build a valid SyntheticInstance baseline; ``overrides`` vary one facet."""
    fields = dict(
        instance_path="home#fixture-1",
        definition=make_definition(),
        page_route="/",
        page_role="home",
        region=RegionKind.BODY,
        registry_known_ids=("hero.split.value-proposition",),
    )
    fields.update(overrides)
    return SyntheticInstance(**fields)


def page(**overrides) -> SyntheticPage:
    """Build a valid SyntheticPage baseline; ``overrides`` vary one facet."""
    fields = dict(
        route="/",
        page_role="home",
        heading_sequence=(1, 2, 2, 3),
        landmark_roles=("header", "main", "footer"),
    )
    fields.update(overrides)
    return SyntheticPage(**fields)


def rendered_page(**overrides) -> SyntheticRenderedPage:
    """Build a valid SyntheticRenderedPage baseline; ``overrides`` vary one
    facet."""
    fields = dict(route="/")
    fields.update(overrides)
    return SyntheticRenderedPage(**fields)


def assert_two_fixture_law(check_fn, good, bad) -> None:
    """The AES-WEB-001 §10.4 two-fixture law: a gate's check function must
    pass its good fixture and fail its bad fixture."""
    good_outcome = check_fn(good)
    assert good_outcome.passed, f"good fixture unexpectedly failed: {good_outcome.details}"
    bad_outcome = check_fn(bad)
    assert not bad_outcome.passed, "bad fixture unexpectedly passed"
    assert bad_outcome.details, "failing outcome must carry diagnostic details (§21 preamble)"


class TestGateIntegrityCompleteness:
    """Confirms every executable gate has a two-fixture test somewhere in
    this package — imported here, at collection time, from each sibling
    family module's own ``TESTED_GATE_IDS`` self-declaration."""

    def test_every_executable_gate_is_tested(self):
        from .test_gate_integrity_contract import TESTED_GATE_IDS as contract_ids
        from .test_gate_integrity_composition import (
            TESTED_GATE_IDS as composition_ids,
        )
        from .test_gate_integrity_rendering import TESTED_GATE_IDS as rendering_ids
        from .test_gate_integrity_commercial import (
            TESTED_GATE_IDS as commercial_ids,
        )
        from .test_gate_integrity_responsive import (
            TESTED_GATE_IDS as responsive_ids,
        )

        tested = (
            contract_ids
            | composition_ids
            | rendering_ids
            | commercial_ids
            | responsive_ids
        )
        expected = set(EXECUTABLE_COMPONENT_GATE_IDS)
        missing = expected - tested
        extra = tested - expected
        assert not missing, f"executable gate(s) with no two-fixture test: {sorted(missing)}"
        assert not extra, f"tested gate(s) not in the executable registration: {sorted(extra)}"

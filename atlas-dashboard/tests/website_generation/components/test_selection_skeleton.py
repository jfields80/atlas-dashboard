"""Selection-skeleton tests (AES-WEB-002A; AES-WEB-002 §31 acceptance).

Proves the minimal deterministic selector: empty-registry behavior,
deterministic synthetic-registry behavior, deterministic trace output,
idempotence, no-selection-without-a-candidate, and that no production
scoring/filtering/tie-breaking was introduced. Import-matrix compliance of
the selection package is asserted here and by the architecture audit.
"""

from __future__ import annotations

import ast
from pathlib import Path

from engines.website_generation.contracts.artifacts import (
    SelectionTrace,
    canonical_json,
    model_to_dict,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    PageRole,
)
from engines.website_generation.components.registry import ComponentRegistry
from engines.website_generation.components.selection import (
    SelectionSkeleton,
    SlotRequest,
)

from . import make_definition

_HERO_REQUEST = SlotRequest(slot_id="hero", page_role=PageRole.HOME)


def _synthetic_registry() -> ComponentRegistry:
    hero = make_definition(supported_page_roles=(PageRole.HOME,))
    listing = make_definition(
        component_id="listing.card.standard",
        component_family=ComponentFamily.LISTING,
        commercial_purpose=CommercialPurpose.EXPOSE_INVENTORY,
        supported_page_roles=(PageRole.HOME,),
    )
    return ComponentRegistry([hero, listing])


class TestEmptyRegistry:
    def test_empty_registry_selects_nothing(self):
        trace = SelectionSkeleton().select(ComponentRegistry(), [_HERO_REQUEST])
        assert isinstance(trace, SelectionTrace)
        assert len(trace.slots) == 1
        slot = trace.slots[0]
        assert slot.slot_id == "hero"
        assert slot.candidates == ()
        assert slot.chosen_component_id == ""  # nothing selected

    def test_no_requests_yields_empty_trace(self):
        trace = SelectionSkeleton().select(ComponentRegistry(), [])
        assert trace.slots == ()


class TestSyntheticRegistry:
    def test_deterministic_selection(self):
        registry = _synthetic_registry()
        trace = SelectionSkeleton().select(registry, [_HERO_REQUEST])
        slot = trace.slots[0]
        # Two candidates support HOME; the lexicographically-first is chosen.
        assert [c.component_id for c in slot.candidates] == [
            "hero.split.value-proposition",
            "listing.card.standard",
        ]
        assert slot.chosen_component_id == "hero.split.value-proposition"

    def test_no_candidate_for_unsupported_role(self):
        registry = _synthetic_registry()
        trace = SelectionSkeleton().select(
            registry, [SlotRequest(slot_id="x", page_role=PageRole.SPONSOR_PAGE)]
        )
        assert trace.slots[0].candidates == ()
        assert trace.slots[0].chosen_component_id == ""

    def test_idempotent_result_and_trace(self):
        registry = _synthetic_registry()
        selector = SelectionSkeleton()
        a = selector.select(registry, [_HERO_REQUEST])
        b = selector.select(registry, [_HERO_REQUEST])
        assert canonical_json(model_to_dict(a)) == canonical_json(
            model_to_dict(b)
        )

    def test_trace_output_is_deterministic_across_instances(self):
        registry = _synthetic_registry()
        a = SelectionSkeleton().select(registry, [_HERO_REQUEST])
        b = SelectionSkeleton().select(registry, [_HERO_REQUEST])
        assert canonical_json(model_to_dict(a)) == canonical_json(
            model_to_dict(b)
        )


class TestNoProductionSelection:
    def test_skeleton_records_no_scores_or_tiebreak(self):
        # A production scoring/tie-break pipeline would populate scores and
        # tie_break_basis; the skeleton must not.
        trace = SelectionSkeleton().select(_synthetic_registry(), [_HERO_REQUEST])
        slot = trace.slots[0]
        assert slot.tie_break_basis == ""
        assert slot.elimination_counts == {}
        for candidate in slot.candidates:
            assert candidate.score is None
            assert candidate.score_components == ()
            assert candidate.eliminated_by == ""

    def test_selection_module_imports_contracts_only(self):
        # Import-matrix compliance (§29.2): the selection skeleton depends
        # only on contracts/ (plus stdlib) — no rendering/gates/registry/
        # scoring-table imports.
        path = (
            Path(__file__).resolve().parents[3]
            / "engines"
            / "website_generation"
            / "components"
            / "selection"
            / "selector.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        wge_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("engines.website_generation"):
                    wge_imports.append(node.module)
        assert wge_imports, "expected some intra-package imports"
        for module in wge_imports:
            assert module.startswith("engines.website_generation.contracts"), (
                "selection skeleton imports non-contracts module %r" % module
            )

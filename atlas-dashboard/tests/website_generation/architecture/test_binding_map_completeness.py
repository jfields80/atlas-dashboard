"""Binding-map completeness, determinism, and architecture tests
(AES-WEB-002J.18; ADR-WEB-CONTENT-BINDING-MAP).

Covers group B (registry-wide completeness), G (determinism), and H
(architecture/import boundaries). The map is validated against the *live*
registry so it cannot silently drift from the 72-component catalog.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.components.binding_rules import (
    BINDING_RULES,
    BINDING_RULES_BY_KEY,
    FieldKind,
)
from engines.website_generation.components.binding_map_validator import (
    validate_binding_map,
)
from engines.website_generation.contracts.enums import PropType
from engines.website_generation.contracts.errors import ArtifactValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
BINDING_RULES_PATH = (
    REPO_ROOT / "engines" / "website_generation" / "components" / "binding_rules.py"
)
VALIDATOR_PATH = (
    REPO_ROOT / "engines" / "website_generation" / "components" / "binding_map_validator.py"
)
VOCAB_PATH = (
    REPO_ROOT / "engines" / "website_generation" / "constants" / "content_slots.py"
)
_REF_TYPES = (PropType.CONTENT_BLOCK_REF, PropType.LISTING_REF)


# --------------------------------------------------------------------------- #
# B. Mapping completeness against the live registry
# --------------------------------------------------------------------------- #

class TestCompleteness:
    def test_validator_passes_against_default_registry(self):
        # The single source of truth: the validator raises on any gap.
        validate_binding_map()

    def test_every_required_content_slot_mapped(self):
        registry = build_default_registry()
        for d in registry.all_definitions():
            for name in d.required_content_slots:
                key = (d.component_id, FieldKind.CONTENT_SLOT.value, name)
                assert key in BINDING_RULES_BY_KEY, key

    def test_every_required_content_block_ref_mapped(self):
        registry = build_default_registry()
        for d in registry.all_definitions():
            for name, spec in d.required_props.items():
                if spec.prop_type is PropType.CONTENT_BLOCK_REF:
                    key = (d.component_id, FieldKind.PROP_REF.value, name)
                    assert key in BINDING_RULES_BY_KEY, key

    def test_every_required_listing_ref_mapped(self):
        registry = build_default_registry()
        for d in registry.all_definitions():
            for name, spec in d.required_props.items():
                if spec.prop_type is PropType.LISTING_REF:
                    key = (d.component_id, FieldKind.PROP_REF.value, name)
                    assert key in BINDING_RULES_BY_KEY, key

    def test_every_required_literal_prop_mapped(self):
        registry = build_default_registry()
        for d in registry.all_definitions():
            for name, spec in d.required_props.items():
                if spec.prop_type not in _REF_TYPES:
                    key = (d.component_id, FieldKind.PROP_LITERAL.value, name)
                    assert key in BINDING_RULES_BY_KEY, key

    def test_no_rule_references_unknown_component_or_field(self):
        registry = build_default_registry()
        defs = {d.component_id: d for d in registry.all_definitions()}
        for r in BINDING_RULES:
            assert r.component_id in defs, r.component_id
            d = defs[r.component_id]
            if r.field_kind is FieldKind.CONTENT_SLOT:
                assert (r.field_name in d.required_content_slots
                        or r.field_name in d.optional_content_slots), r
            else:
                assert (r.field_name in d.required_props
                        or r.field_name in d.optional_props), r

    def test_missing_mapping_is_detected(self):
        # Adversarial: a registry with an extra required slot the map does not
        # cover must fail validation (proves completeness is really checked).
        registry = build_default_registry()

        class _Wrapper:
            def __init__(self, inner):
                self._inner = inner
                self._extra = self._make_extra(inner)

            @staticmethod
            def _make_extra(inner):
                base = next(iter(inner.all_definitions()))
                # a fake definition with an unmapped required content slot
                from engines.website_generation.contracts.components import SlotSpec
                return base.copy(update={
                    "component_id": "test.unmapped.component",
                    "required_content_slots": {"totally_unmapped": SlotSpec(block_type="RichTextBlock")},
                })

            def all_definitions(self):
                return tuple(self._inner.all_definitions()) + (self._extra,)

            def __getattr__(self, item):
                return getattr(self._inner, item)

        with pytest.raises(ArtifactValidationError) as exc:
            validate_binding_map(_Wrapper(registry))
        assert "unmapped_required_content_slots" in exc.value.diagnostics


# --------------------------------------------------------------------------- #
# G. Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_validator_is_idempotent(self):
        validate_binding_map()
        validate_binding_map()  # second call, same result (no state)

    def test_rule_iteration_order_stable(self):
        a = [(r.component_id, r.field_name) for r in BINDING_RULES]
        b = [(r.component_id, r.field_name) for r in BINDING_RULES]
        assert a == b

    def test_diagnostics_ordering_stable(self):
        # Build a wrapper that triggers several buckets, twice, and compare.
        registry = build_default_registry()

        def _run():
            from engines.website_generation.contracts.components import SlotSpec

            class _W:
                def __init__(self, inner):
                    self._inner = inner
                    base = next(iter(inner.all_definitions()))
                    self._extra = base.copy(update={
                        "component_id": "z.unmapped",
                        "required_content_slots": {"zzz": SlotSpec(block_type="RichTextBlock")},
                    })

                def all_definitions(self):
                    return tuple(self._inner.all_definitions()) + (self._extra,)

                def __getattr__(self, item):
                    return getattr(self._inner, item)

            try:
                validate_binding_map(_W(registry))
                return None
            except ArtifactValidationError as e:
                return list(e.diagnostics)

        assert _run() == _run()


# --------------------------------------------------------------------------- #
# H. Architecture
# --------------------------------------------------------------------------- #

class TestArchitecture:
    def _imports(self, path: Path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    mods.add(a.name)
        return mods

    def test_binding_rules_imports_only_stdlib_and_constants(self):
        for mod in self._imports(BINDING_RULES_PATH):
            assert (
                mod in ("__future__", "dataclasses", "enum", "typing")
                or mod.startswith("engines.website_generation.constants")
            ), mod

    def test_vocabulary_imports_only_stdlib(self):
        for mod in self._imports(VOCAB_PATH):
            assert mod in ("__future__", "dataclasses", "enum", "typing"), mod

    def test_no_renderer_emitter_service_repository_imports(self):
        for path in (BINDING_RULES_PATH, VALIDATOR_PATH, VOCAB_PATH):
            src = path.read_text(encoding="utf-8")
            for banned in ("rendering", "emitters", "services", "repositories",
                           "assembly", "gates", "pipeline"):
                assert banned not in src, (path.name, banned)

    def test_no_forbidden_runtime_facilities(self):
        for path in (BINDING_RULES_PATH, VALIDATOR_PATH, VOCAB_PATH):
            src = path.read_text(encoding="utf-8")
            for banned in ("import socket", "import urllib", "import requests",
                           "import uuid", "import random", "import datetime",
                           "os.environ", "http.server", "import subprocess",
                           "time.time", "anthropic", "import time"):
                assert banned not in src, (path.name, banned)

    def test_no_dict_str_any(self):
        for path in (BINDING_RULES_PATH, VOCAB_PATH):
            assert "Dict[str, Any]" not in path.read_text(encoding="utf-8")

    def test_pipeline_remains_unwired(self):
        from engines.website_generation.constants.build import (
            PHASE1_EXECUTED_STAGES,
            STAGE_SPEC_COMPILATION,
        )

        assert PHASE1_EXECUTED_STAGES == (STAGE_SPEC_COMPILATION,)

    def test_all_components_remain_proposed(self):
        registry = build_default_registry()
        ids = [d.component_id for d in registry.all_definitions()]
        assert {str(registry.lifecycle(c)) for c in ids} == {"LifecycleStatus.PROPOSED"}

    def test_no_engine_version_added(self):
        # AES-WEB-002K.1 supersedes this test's original per-value check
        # (every engine == "1.0.0" or renderer == "1.1.0") -- every
        # subsequent sprint through J.19/J.20/K.1 has legitimately bumped
        # multiple real engine versions (see contracts/versions.py's own
        # inline history), so a hardcoded version-string assertion is no
        # longer a meaningful proxy for "no engine version added". The
        # real, still-true invariant this test protects -- no *new engine
        # key* was ever added for the J.18 binding map (it is data, not an
        # engine) -- is checked directly instead.
        from engines.website_generation.contracts.versions import ENGINE_VERSIONS

        assert set(ENGINE_VERSIONS) == {
            "business_spec_compiler", "state_machine", "website_generation_pipeline",
            "brand_engine", "information_architecture_engine", "content_engine",
            "seo_engine", "component_engine", "layout_engine", "renderer",
            "assembly", "quality_gate_engine",
        }
        # No binding-map engine exists.
        assert "binding_map" not in ENGINE_VERSIONS
        assert "content_binding" not in ENGINE_VERSIONS

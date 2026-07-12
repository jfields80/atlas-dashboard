"""Gate registration tests (AES-WEB-002I; AES-WEB-002 §21, §34.1 item 19).

Verifies ``constants/gates.py``'s ``COMPONENT_GATE_REGISTRATIONS`` data:
identity, ordering, completeness against the 73 AES-WEB-002 §21 gate IDs
plus the CG-STR-006 reservation (AMB-002I-02/04), executable/check-module
integrity, and — the operator-mandated consistency test — that every gate
ID any of the 72 registered components declares in
``quality_gate_requirements`` resolves to a registered gate ID.
"""

from __future__ import annotations

import importlib

import pytest

from engines.website_generation.components.registry import REGISTERED_COMPONENTS
from engines.website_generation.constants.gates import (
    AES_WEB_002_SECTION_21_ENUMERATED_GATE_COUNT,
    COMPONENT_GATE_BY_ID,
    COMPONENT_GATE_FAMILIES,
    COMPONENT_GATE_IDS,
    COMPONENT_GATE_REGISTRATIONS,
    EXECUTABLE_COMPONENT_GATE_IDS,
    GATE_SEVERITY_BLOCKING,
    GATE_SEVERITY_INFO,
    GATE_SEVERITY_WARNING,
    RESERVED_ONLY_GATE_IDS,
)

_VALID_SEVERITIES = {GATE_SEVERITY_BLOCKING, GATE_SEVERITY_WARNING, GATE_SEVERITY_INFO}

# Per-family expected counts, AES-WEB-002 §21.1-21.7 (10+11+10+13+9+12+8=73).
_EXPECTED_FAMILY_TABLE_COUNTS = {
    "CG-CON": 10,
    "CG-CMP": 11,
    "CG-RND": 10,
    "CG-A11Y": 13,
    "CG-SEO": 9,
    "CG-COM": 12,
    "CG-RSP": 8,
}


class TestRegistrationCompleteness:
    def test_total_registration_count(self):
        # 73 AES-WEB-002 §21 gates + 1 CG-STR-006 reservation (AMB-002I-04).
        assert len(COMPONENT_GATE_REGISTRATIONS) == 74

    def test_unique_gate_ids(self):
        ids = [reg.gate_id for reg in COMPONENT_GATE_REGISTRATIONS]
        assert len(ids) == len(set(ids)), "duplicate gate_id in registration"

    def test_lexicographic_order(self):
        # Mirrors REGISTERED_COMPONENTS' own lexicographic convention
        # (AES-WEB-002 §15.2) so merge conflicts stay visible.
        ids = [reg.gate_id for reg in COMPONENT_GATE_REGISTRATIONS]
        assert ids == sorted(ids)

    def test_per_family_table_counts_match_section_21(self):
        for prefix, expected in _EXPECTED_FAMILY_TABLE_COUNTS.items():
            actual = sum(
                1
                for reg in COMPONENT_GATE_REGISTRATIONS
                if reg.gate_id.startswith(prefix + "-")
            )
            assert actual == expected, (prefix, actual, expected)

    def test_enumerated_count_constant_matches_73(self):
        section_21_subsections = {
            f"§21.{n}" for n in range(1, 8)
        }
        w2_ids = [
            reg
            for reg in COMPONENT_GATE_REGISTRATIONS
            if reg.source_section in section_21_subsections
        ]
        assert len(w2_ids) == AES_WEB_002_SECTION_21_ENUMERATED_GATE_COUNT == 73

    def test_cg_str_006_present_as_reservation(self):
        reg = COMPONENT_GATE_BY_ID["CG-STR-006"]
        assert reg.executable is False
        assert reg.check_module == ""
        assert reg.family == "structural"

    def test_reserved_only_ids_are_exactly_a11y_seo_and_str006(self):
        expected = {f"CG-A11Y-{i:03d}" for i in range(1, 14)}
        expected |= {f"CG-SEO-{i:03d}" for i in range(1, 10)}
        expected.add("CG-STR-006")
        assert set(RESERVED_ONLY_GATE_IDS) == expected

    def test_executable_count_is_51(self):
        # 73 W2 gates minus the 22 CG-A11Y/CG-SEO gates deferred alongside
        # CG-STR-006 (no accessibility_checks.py/seo_checks.py this sprint
        # — see constants/gates.py's module docstring).
        assert len(EXECUTABLE_COMPONENT_GATE_IDS) == 51


class TestRegistrationFieldIntegrity:
    @pytest.mark.parametrize(
        "reg", COMPONENT_GATE_REGISTRATIONS, ids=lambda r: r.gate_id
    )
    def test_severity_is_valid(self, reg):
        assert reg.severity in _VALID_SEVERITIES

    @pytest.mark.parametrize(
        "reg", COMPONENT_GATE_REGISTRATIONS, ids=lambda r: r.gate_id
    )
    def test_remediation_owner_is_declared(self, reg):
        assert reg.remediation_owner, reg.gate_id

    @pytest.mark.parametrize(
        "reg", COMPONENT_GATE_REGISTRATIONS, ids=lambda r: r.gate_id
    )
    def test_family_is_registered_family(self, reg):
        # Structural is inherited from AES-WEB-001 (CG-STR-006 only); every
        # other registration's family must be one of the seven component
        # families this delivery introduces or extends.
        assert reg.family in COMPONENT_GATE_FAMILIES or reg.family == "structural"

    @pytest.mark.parametrize(
        "reg",
        [r for r in COMPONENT_GATE_REGISTRATIONS if r.executable],
        ids=lambda r: r.gate_id,
    )
    def test_executable_registration_has_importable_check_module(self, reg):
        module = importlib.import_module(reg.check_module)
        assert reg.gate_id in module.CHECKS, (
            f"{reg.gate_id} not found in {reg.check_module}.CHECKS"
        )

    @pytest.mark.parametrize(
        "reg",
        [r for r in COMPONENT_GATE_REGISTRATIONS if not r.executable],
        ids=lambda r: r.gate_id,
    )
    def test_non_executable_registration_has_no_check_module(self, reg):
        assert reg.check_module == ""


class TestCatalogGateReferenceConsistency:
    """The operator-mandated consistency test: every gate ID any of the 72
    registered components declares in ``quality_gate_requirements`` must
    resolve to a registered gate ID. A component referencing an
    unregistered ID (other than the approved CG-STR-006 reservation, which
    IS registered) is a stop condition — this test fails loudly rather
    than silently tolerating the gap, and this delivery does not edit any
    component to make it pass."""

    def test_all_72_components_registered(self):
        assert len(REGISTERED_COMPONENTS) == 72

    def test_every_referenced_gate_id_is_registered(self):
        unresolved = []
        for definition in REGISTERED_COMPONENTS:
            for gate_id in definition.quality_gate_requirements:
                if gate_id not in COMPONENT_GATE_IDS:
                    unresolved.append((definition.component_id, gate_id))
        assert not unresolved, (
            "component(s) reference unregistered gate id(s): %r" % unresolved
        )

    def test_at_least_one_component_references_each_referenced_family(self):
        # Sanity check that the consistency test above is not vacuous.
        referenced = {
            gate_id
            for definition in REGISTERED_COMPONENTS
            for gate_id in definition.quality_gate_requirements
        }
        assert referenced, "no component declares any quality_gate_requirements"
        assert "CG-STR-006" in referenced

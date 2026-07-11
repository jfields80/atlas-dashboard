"""Accessibility gate severity policy tests (AES-WEB-001 v1.1.0 amendment A2).

Proves the AES-WEB-002 §12.7 / §21.4 severity elevation registered under the
AES-WEB-001 §3.5 mechanism: keyboard/focus, semantic-structure, heading-
hierarchy, landmark, label, alt-text, contrast, and form-completion defects
are BLOCKING; only optimization-tier findings remain WARNING. No severity is
weakened.
"""

from __future__ import annotations

from engines.website_generation.constants import gates


class TestAccessibilityGateSeverities:
    def test_heading_hierarchy_is_blocking(self):
        assert (
            gates.ACCESSIBILITY_GATE_SEVERITIES[
                gates.ACCESSIBILITY_DEFECT_HEADING_HIERARCHY
            ]
            == gates.GATE_SEVERITY_BLOCKING
        )

    def test_landmark_defects_are_blocking(self):
        assert (
            gates.ACCESSIBILITY_GATE_SEVERITIES[
                gates.ACCESSIBILITY_DEFECT_LANDMARK
            ]
            == gates.GATE_SEVERITY_BLOCKING
        )

    def test_all_eight_categories_are_blocking(self):
        # The eight categories named by amendment A2 / AES-WEB-002 §12.7.
        expected = {
            "missing_or_invalid_alt_text",
            "contrast_failure",
            "missing_labels",
            "keyboard_focus_failure",
            "semantic_structure_failure",
            "heading_hierarchy_defect",
            "landmark_defect",
            "form_completion_accessibility_failure",
        }
        assert set(gates.ACCESSIBILITY_BLOCKING_DEFECTS) == expected
        for defect in gates.ACCESSIBILITY_BLOCKING_DEFECTS:
            assert (
                gates.ACCESSIBILITY_GATE_SEVERITIES[defect]
                == gates.GATE_SEVERITY_BLOCKING
            )

    def test_optimization_tier_remains_warning(self):
        assert gates.ACCESSIBILITY_WARNING_DEFECTS  # non-empty
        for defect in gates.ACCESSIBILITY_WARNING_DEFECTS:
            assert (
                gates.ACCESSIBILITY_GATE_SEVERITIES[defect]
                == gates.GATE_SEVERITY_WARNING
            )

    def test_no_severity_weakening(self):
        # No blocking category is (mis)registered as WARNING/INFO — the
        # amendment only strengthens severities.
        for defect in gates.ACCESSIBILITY_BLOCKING_DEFECTS:
            assert (
                gates.ACCESSIBILITY_GATE_SEVERITIES[defect]
                != gates.GATE_SEVERITY_WARNING
            )
            assert (
                gates.ACCESSIBILITY_GATE_SEVERITIES[defect]
                != gates.GATE_SEVERITY_INFO
            )
        # Blocking and warning sets are disjoint.
        assert not (
            set(gates.ACCESSIBILITY_BLOCKING_DEFECTS)
            & set(gates.ACCESSIBILITY_WARNING_DEFECTS)
        )

    def test_accessibility_family_registered(self):
        # The expanded family is registered under the §3.5 mechanism (an
        # explicit list in constants — no dynamic scanning).
        assert gates.GATE_FAMILY_ACCESSIBILITY in gates.GATE_FAMILIES
        assert set(gates.ACCESSIBILITY_GATE_SEVERITIES) == (
            set(gates.ACCESSIBILITY_BLOCKING_DEFECTS)
            | set(gates.ACCESSIBILITY_WARNING_DEFECTS)
        )

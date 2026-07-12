"""Compatibility-range evaluation tests (AES-WEB-002D; AES-WEB-002 §22,
§30.1 "Compatibility tests: Range evaluation truth table").

Pure semver range logic: parsing, per-clause evaluation, AND-composition of
comma-separated clauses, the wildcard, malformed-input rejection, and the
real catalog's ``_COMPAT`` declaration against representative build
versions.
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.errors import (
    InvalidCompatibilityDeclarationError,
)
from engines.website_generation.components.compatibility.ranges import (
    evaluate_compatibility,
    is_compatible,
    parse_version,
    satisfies_range,
)


class TestParseVersion:
    def test_valid_version(self):
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("0.0.0") == (0, 0, 0)
        assert parse_version("10.20.30") == (10, 20, 30)

    @pytest.mark.parametrize(
        "bad",
        ["1.2", "1.2.3.4", "a.b.c", "", "1.2.x", "v1.2.3", "1.2.3 "],
    )
    def test_malformed_version_rejected(self, bad):
        with pytest.raises(InvalidCompatibilityDeclarationError):
            parse_version(bad)


class TestSatisfiesRangeTruthTable:
    @pytest.mark.parametrize(
        "range_expr,version,expected",
        [
            (">=1.0.0", "1.0.0", True),
            (">=1.0.0", "0.9.9", False),
            (">=1.0.0", "2.0.0", True),
            ("<=1.0.0", "1.0.0", True),
            ("<=1.0.0", "1.0.1", False),
            (">1.0.0", "1.0.0", False),
            (">1.0.0", "1.0.1", True),
            ("<2.0.0", "2.0.0", False),
            ("<2.0.0", "1.9.9", True),
            ("==1.0.0", "1.0.0", True),
            ("==1.0.0", "1.0.1", False),
            (">=1.0.0,<2.0.0", "1.0.0", True),
            (">=1.0.0,<2.0.0", "1.5.0", True),
            (">=1.0.0,<2.0.0", "2.0.0", False),
            (">=1.0.0,<2.0.0", "0.9.0", False),
            ("*", "0.0.1", True),
            ("*", "99.99.99", True),
        ],
    )
    def test_truth_table(self, range_expr, version, expected):
        assert satisfies_range(range_expr, version) is expected

    def test_wildcard_only_valid_alone(self):
        # "*" combined with other clauses is not a supported grammar form.
        with pytest.raises(InvalidCompatibilityDeclarationError):
            satisfies_range("*,>=1.0.0", "1.0.0")

    @pytest.mark.parametrize(
        "bad_range",
        [">=1.0", "~1.0.0", ">=1.0.0,", ",>=1.0.0", "", ">= 1.0.0", "!=1.0.0"],
    )
    def test_malformed_range_rejected(self, bad_range):
        with pytest.raises(InvalidCompatibilityDeclarationError):
            satisfies_range(bad_range, "1.0.0")


class TestEvaluateCompatibility:
    def test_only_shared_axes_are_checked(self):
        compatible, failing = evaluate_compatibility(
            {"renderer": ">=1.0.0,<2.0.0", "token_schema": ">=1.0.0,<2.0.0"},
            {"renderer": "1.0.0"},  # token_schema not supplied by caller
        )
        assert compatible is True
        assert failing == ()

    def test_failing_axis_named(self):
        compatible, failing = evaluate_compatibility(
            {"renderer": ">=2.0.0"},
            {"renderer": "1.0.0"},
        )
        assert compatible is False
        assert failing == ("renderer",)

    def test_multiple_failing_axes_sorted(self):
        compatible, failing = evaluate_compatibility(
            {"renderer": ">=2.0.0", "token_schema": ">=2.0.0"},
            {"renderer": "1.0.0", "token_schema": "1.0.0"},
        )
        assert compatible is False
        assert failing == ("renderer", "token_schema")

    def test_empty_range_is_always_compatible(self):
        compatible, failing = evaluate_compatibility({}, {"renderer": "1.0.0"})
        assert compatible is True
        assert failing == ()

    def test_is_compatible_wrapper(self):
        assert is_compatible(
            {"renderer": ">=1.0.0,<2.0.0"}, {"renderer": "1.0.0"}
        ) is True
        assert is_compatible(
            {"renderer": ">=1.0.0,<2.0.0"}, {"renderer": "2.0.0"}
        ) is False


class TestRealCatalogCompatibilityRange:
    def test_wave_compat_declaration_satisfied_at_1_0_0(self):
        # Every Wave 1-3 + provisional component declares this exact range
        # (layout_atoms._COMPAT); the pipeline's default build versions must
        # satisfy it.
        compat_range = {
            "renderer": ">=1.0.0,<2.0.0",
            "token_schema": ">=1.0.0,<2.0.0",
            "registry_schema": ">=1.0.0,<2.0.0",
        }
        versions = {
            "renderer": "1.0.0",
            "token_schema": "1.0.0",
            "registry_schema": "1.0.0",
        }
        assert is_compatible(compat_range, versions) is True

    def test_wave_compat_declaration_rejects_major_bump(self):
        compat_range = {"renderer": ">=1.0.0,<2.0.0"}
        assert is_compatible(compat_range, {"renderer": "2.0.0"}) is False

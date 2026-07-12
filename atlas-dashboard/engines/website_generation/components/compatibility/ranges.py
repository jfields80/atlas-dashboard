"""Component compatibility-range evaluation (AES-WEB-002D; AES-WEB-002 §22).

Pure semver range logic consumed by the §14.2 step-2 compatibility filter at
selection time. A ``compatibility_range`` (``ComponentDefinition``'s existing
``Dict[str, str]`` field, §22.1) pins zero or more axes — e.g.
``{"renderer": ">=1.0.0,<2.0.0"}`` — each value a comma-separated list of
clauses. This module adds no new axes, no new contract fields, and no new
registry concepts: it only evaluates the strings the existing contract
already carries (§29.1 "Compatibility-range evaluation (pure semver logic)").

Grammar (informal): ``range := clause ("," clause)*``;
``clause := "*" | operator version``; ``operator := ">=" | "<=" | ">" | "<" |
"=="``; ``version := \\d+.\\d+.\\d+``. All clauses in a range must hold for the
range to be satisfied (AND semantics) — this matches every existing
``_COMPAT`` declaration in the catalog (``">=1.0.0,<2.0.0"`` = both bounds
hold).
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

from engines.website_generation.contracts.errors import (
    InvalidCompatibilityDeclarationError,
)

_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_CLAUSE_PATTERN = re.compile(r"^(>=|<=|==|>|<)(\d+\.\d+\.\d+)$")
_WILDCARD = "*"


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse a strict ``MAJOR.MINOR.PATCH`` version string.

    Raises :class:`InvalidCompatibilityDeclarationError` on malformed input
    — this module never guesses at a version's meaning.
    """
    match = _VERSION_PATTERN.match(version)
    if not match:
        raise InvalidCompatibilityDeclarationError(
            "not a valid MAJOR.MINOR.PATCH version: %r" % version,
            stage="compatibility_ranges",
            diagnostics={"version": version},
        )
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _evaluate_clause(operator: str, clause_version: str, version: Tuple[int, int, int]) -> bool:
    target = parse_version(clause_version)
    if operator == ">=":
        return version >= target
    if operator == "<=":
        return version <= target
    if operator == ">":
        return version > target
    if operator == "<":
        return version < target
    if operator == "==":
        return version == target
    raise InvalidCompatibilityDeclarationError(
        "unknown range operator: %r" % operator,
        stage="compatibility_ranges",
        diagnostics={"operator": operator},
    )


def satisfies_range(range_expr: str, version: str) -> bool:
    """Return whether ``version`` satisfies every comma-separated clause.

    ``"*"`` (exactly, with no other clauses) matches every syntactically
    valid version. Raises :class:`InvalidCompatibilityDeclarationError` on a
    malformed range expression or version — a range never "fails closed"
    silently; malformed data is always an explicit error.
    """
    parsed_version = parse_version(version)
    clauses = [c.strip() for c in range_expr.split(",")]
    if not clauses or any(not c for c in clauses):
        raise InvalidCompatibilityDeclarationError(
            "empty clause in range expression: %r" % range_expr,
            stage="compatibility_ranges",
            diagnostics={"range_expr": range_expr},
        )
    if clauses == [_WILDCARD]:
        return True
    for clause in clauses:
        match = _CLAUSE_PATTERN.match(clause)
        if not match:
            raise InvalidCompatibilityDeclarationError(
                "malformed compatibility clause: %r" % clause,
                stage="compatibility_ranges",
                diagnostics={"clause": clause, "range_expr": range_expr},
            )
        operator, clause_version = match.group(1), match.group(2)
        if not _evaluate_clause(operator, clause_version, parsed_version):
            return False
    return True


def evaluate_compatibility(
    compatibility_range: Dict[str, str], versions: Dict[str, str]
) -> Tuple[bool, Tuple[str, ...]]:
    """Check a definition's ``compatibility_range`` against build versions.

    Only axes present in *both* ``compatibility_range`` and ``versions`` are
    evaluated — an axis the definition does not pin is unconstrained, and an
    axis the caller does not supply a current version for cannot be checked
    (§14.1's ``build_flags``/version inputs are supplied by the caller, not
    invented here). Returns ``(is_compatible, failing_axes)`` where
    ``failing_axes`` is the deterministically sorted tuple of axis names
    whose declared range rejected the supplied version — empty when
    compatible, so a caller can name the exact failure per §14.2 step 9's
    "eliminating filter per candidate" diagnostic requirement.
    """
    failing = sorted(
        axis
        for axis, range_expr in compatibility_range.items()
        if axis in versions and not satisfies_range(range_expr, versions[axis])
    )
    return (not failing, tuple(failing))


def is_compatible(
    compatibility_range: Dict[str, str], versions: Dict[str, str]
) -> bool:
    """Boolean-only convenience wrapper over :func:`evaluate_compatibility`."""
    compatible, _ = evaluate_compatibility(compatibility_range, versions)
    return compatible

"""BusinessSpecCompiler — the sole ingestion point into the WGE.

AES-WEB-001 §5.1. Pure and deterministic: no I/O, no repository access,
no AI, no network, no clock, no UUIDs. Consumes the frozen
:class:`SpecCompilerInput` contract (see the contract-boundary decision
recorded on that model) and emits a :class:`BusinessSpec`.

Failure contract: every missing required field is reported at once in a
single :class:`SpecCompilationError` (batch error reporting, never
first-failure). Unresolved required values are never silently invented.
"""

from __future__ import annotations

from typing import List, Tuple

from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    SpecCompilerInput,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import SpecCompilationError
from engines.website_generation.contracts.interfaces import (
    SpecCompilerInterface,
)
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

# Fields that must be resolved for a spec to compile. Optional fields
# (monetization_model, geography, taxonomy, legal facts) may be empty in
# Phase 1; the compiler never invents values for them.
_REQUIRED_FIELDS: Tuple[str, ...] = (
    "business_name",
    "niche",
    "audience",
    "value_proposition",
)

COMPILER_VERSION = "1.0.0"


def _normalized(value: str) -> str:
    """Whitespace-normalized scalar text: stripped, inner runs collapsed."""
    return " ".join(str(value).split())


def _normalized_tuple(values: Tuple[str, ...]) -> Tuple[str, ...]:
    """Normalize each entry, drop empties, preserve caller order."""
    out: List[str] = []
    for value in values:
        text = _normalized(value)
        if text:
            out.append(text)
    return tuple(out)


class BusinessSpecCompiler(SpecCompilerInterface):
    """Compile upstream Atlas values into the canonical BusinessSpec."""

    version = COMPILER_VERSION

    def compile(self, compiler_input: SpecCompilerInput) -> BusinessSpec:
        """Total function over valid inputs; batch-fails otherwise.

        Deterministic guarantees:
        * the input is never mutated (it is frozen; nothing is copied
          back into it);
        * ``directory_taxonomy`` is emitted stable-sorted (taxonomy is a
          classification set, not an ordered narrative);
        * ``legal_footer_facts`` preserves the caller's order (legal
          copy order is meaningful) after normalization;
        * ``source_hashes`` is copied key-sorted from ``upstream_hashes``.
        """
        if not isinstance(compiler_input, SpecCompilerInput):
            raise SpecCompilationError(
                "compiler input must be a SpecCompilerInput contract",
                missing_fields=(),
            )

        missing: List[str] = []
        for field_name in _REQUIRED_FIELDS:
            if not _normalized(getattr(compiler_input, field_name, "")):
                missing.append(field_name)
        if missing:
            raise SpecCompilationError(
                "BusinessSpec compilation failed; missing required fields: "
                + ", ".join(missing),
                missing_fields=tuple(missing),
            )

        source_hashes = {
            key: compiler_input.upstream_hashes[key]
            for key in sorted(compiler_input.upstream_hashes)
        }

        return BusinessSpec(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
            artifact_kind=ArtifactKind.BUSINESS_SPEC,
            source_hashes=source_hashes,
            business_name=_normalized(compiler_input.business_name),
            niche=_normalized(compiler_input.niche),
            audience=_normalized(compiler_input.audience),
            value_proposition=_normalized(compiler_input.value_proposition),
            directory_taxonomy=tuple(
                sorted(_normalized_tuple(compiler_input.directory_taxonomy))
            ),
            monetization_model=_normalized(compiler_input.monetization_model),
            geography=_normalized(compiler_input.geography),
            legal_footer_facts=_normalized_tuple(
                compiler_input.legal_footer_facts
            ),
        )

"""Typed exception hierarchy for the Website Generation Engine.

AES-WEB-001 Phase 1 subset. Every error carries structured diagnostics so
the (future) service shell can route failures per §6.7 without string
parsing. Errors are raised, never returned as sentinel values (§ Part 5).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple


class WebsiteGenerationError(Exception):
    """Base class for every typed WGE error.

    Carries ``(stage, retryable, diagnostics)`` per AES-WEB-001 §6.7.
    """

    def __init__(
        self,
        message: str,
        stage: str = "",
        retryable: bool = False,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.retryable = retryable
        self.diagnostics: Dict[str, Any] = dict(diagnostics or {})


class ArtifactValidationError(WebsiteGenerationError):
    """An artifact failed schema or semantic validation (rings 1-2, §4.4)."""


class SchemaRegistrationError(WebsiteGenerationError):
    """A schema registration conflict or invalid registration (§4.6)."""


class UnsupportedSchemaVersionError(WebsiteGenerationError):
    """No registered model for the declared (artifact_kind, schema_version)."""


class ArtifactIntegrityError(WebsiteGenerationError):
    """Recomputed content hash does not match declared identity (ring 3)."""


class ArtifactNotFoundError(WebsiteGenerationError):
    """A requested artifact hash does not resolve in the artifact store."""


class SpecCompilationError(WebsiteGenerationError):
    """BusinessSpec compilation failed.

    Batch-reports every missing required field at once (AES-WEB-001 §5.1)
    via ``missing_fields`` — never first-failure-only.
    """

    def __init__(
        self,
        message: str,
        missing_fields: Sequence[str] = (),
        stage: str = "spec_compilation",
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged: Dict[str, Any] = dict(diagnostics or {})
        merged["missing_fields"] = list(missing_fields)
        super().__init__(
            message, stage=stage, retryable=False, diagnostics=merged
        )
        self.missing_fields: Tuple[str, ...] = tuple(missing_fields)


class IllegalTransitionError(WebsiteGenerationError):
    """A state transition not present in the static transition table (§6.2)."""

    def __init__(
        self,
        message: str,
        from_state: str = "",
        outcome: str = "",
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged: Dict[str, Any] = dict(diagnostics or {})
        merged.update({"from_state": from_state, "outcome": outcome})
        super().__init__(
            message, stage="state_machine", retryable=False, diagnostics=merged
        )
        self.from_state = from_state
        self.outcome = outcome


class RepositoryCorruptionError(WebsiteGenerationError):
    """Stored repository data failed an integrity or parse check."""


# ---------------------------------------------------------------------------
# Component-system errors (AES-WEB-002A; AES-WEB-002 §15)
# ---------------------------------------------------------------------------

class ComponentSystemError(WebsiteGenerationError):
    """Base class for every component-registry / component-contract error."""


class InvalidComponentDefinitionError(ComponentSystemError):
    """A component definition is malformed (naming grammar, complexity
    budget, semver, lifecycle rules, or missing required contracts) —
    AES-WEB-002 §15.2."""


class DuplicateComponentError(ComponentSystemError):
    """A ``(component_id, component_version)`` was registered more than once
    (§4.2 registry-integrity: duplicate registration fails at import time)."""


class ConflictingComponentError(ComponentSystemError):
    """Two definitions share a key but differ, or otherwise conflict."""


class UnsupportedComponentVersionError(ComponentSystemError):
    """A requested component version is not registered (§15)."""


class ComponentNotFoundError(ComponentSystemError):
    """No component is registered under the requested ``component_id`` (§15.3
    ``UnknownComponentError``)."""


class InvalidCompatibilityDeclarationError(ComponentSystemError):
    """A ``compatibility_range`` declares an unknown axis or malformed range
    (AES-WEB-002 §22.1)."""


class ComponentResolutionError(ComponentSystemError):
    """A required recipe slot could not be filled, even by its declared
    fallback (AES-WEB-002 §14.2 step 9). Diagnostics name the slot, every
    candidate considered, and the filter that eliminated each one —
    selection never silently drops a required slot."""

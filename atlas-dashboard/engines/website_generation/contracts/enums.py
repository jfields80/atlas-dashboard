"""Core enumerations for the Website Generation Engine (AES-WEB-001 Phase 1).

Every enum is a ``str`` subclass so canonical JSON serialization is stable
under both Pydantic v1 and v2 and across process runs.

Authority: AES-WEB-001 §4.1 (ArtifactKind), §6.2 (BuildState), §6.7
(StageOutcome routing), §10.1 (GateSeverity), §4.5 (artifact lifecycle).
"""

from __future__ import annotations

from enum import Enum


class ArtifactKind(str, Enum):
    """The twelve artifact kinds of the AES-WEB-001 catalog (§4.1)."""

    BUSINESS_SPEC = "BUSINESS_SPEC"
    BRAND_PACKAGE = "BRAND_PACKAGE"
    SITE_ARCHITECTURE = "SITE_ARCHITECTURE"
    CONTENT_CANDIDATE = "CONTENT_CANDIDATE"
    CONTENT_PACKAGE = "CONTENT_PACKAGE"
    COMPONENT_MANIFEST = "COMPONENT_MANIFEST"
    LAYOUT_PLAN = "LAYOUT_PLAN"
    RENDERED_PAGE_SET = "RENDERED_PAGE_SET"
    SEO_PACKAGE = "SEO_PACKAGE"
    SITE_BUNDLE = "SITE_BUNDLE"
    QUALITY_REPORT = "QUALITY_REPORT"
    BUILD_MANIFEST = "BUILD_MANIFEST"


class BuildState(str, Enum):
    """Build lifecycle states (AES-WEB-001 §6.2)."""

    INITIALIZED = "INITIALIZED"
    SPEC_COMPILED = "SPEC_COMPILED"
    BRAND_RESOLVED = "BRAND_RESOLVED"
    IA_PLANNED = "IA_PLANNED"
    CONTENT_DRAFTING = "CONTENT_DRAFTING"
    CONTENT_VALIDATED = "CONTENT_VALIDATED"
    COMPONENTS_RESOLVED = "COMPONENTS_RESOLVED"
    LAYOUT_COMPOSED = "LAYOUT_COMPOSED"
    RENDERED = "RENDERED"
    SEO_COMPILED = "SEO_COMPILED"
    ASSEMBLED = "ASSEMBLED"
    GATED = "GATED"
    CERTIFIED = "CERTIFIED"
    PACKAGED = "PACKAGED"
    DEPLOY_READY = "DEPLOY_READY"

    # Failure / control states (reachable from any active state).
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    ESCALATED_HUMAN = "ESCALATED_HUMAN"
    CANCELLED = "CANCELLED"
    GATE_REJECTED = "GATE_REJECTED"


class StageOutcome(str, Enum):
    """Outcomes the effectful shell reports to the pure transition law.

    Routing semantics follow AES-WEB-001 §6.2, §6.7 and §6.8.
    """

    SUCCESS = "SUCCESS"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    ESCALATE = "ESCALATE"
    CANCEL = "CANCEL"
    GATE_REJECT = "GATE_REJECT"
    REWORK = "REWORK"
    RETRY = "RETRY"


class GateSeverity(str, Enum):
    """Quality gate severities (AES-WEB-001 §10.1)."""

    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


class ArtifactLifecycleState(str, Enum):
    """Lifecycle tracked *about* artifacts, never inside them (§4.5)."""

    PRODUCED = "PRODUCED"
    VALIDATED = "VALIDATED"
    CONSUMED = "CONSUMED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class StageExecutionStatus(str, Enum):
    """Execution status of a pipeline stage as recorded in the BuildManifest.

    Phase 1 records unimplemented future stages as ``NOT_EXECUTED`` —
    never as successful (Sprint 1 directive; AES-WEB-001 Part 13 Phase 1).
    """

    EXECUTED = "EXECUTED"
    NOT_EXECUTED = "NOT_EXECUTED"

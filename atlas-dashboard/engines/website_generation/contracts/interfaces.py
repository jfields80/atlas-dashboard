"""Abstract interfaces for the Website Generation Engine (Phase 1 subset).

AES-WEB-001 §3.5 declares extension points as abstract interfaces in
``contracts/interfaces.py``. Phase 1 needs only the typed stage boundary
the skeleton pipeline composes against; DeploymentAdapter, GateCheck, and
CognitionProvider interfaces arrive with their implementing phases (never
before — no interface is declared here until a phase consumes it).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    SpecCompilerInput,
)
from engines.website_generation.contracts.components import (
    ComponentDefinition,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    ComponentFamily,
    LifecycleStatus,
    PageRole,
)


class SpecCompilerInterface(ABC):
    """The sole ingestion boundary into the WGE (AES-WEB-001 §5.1)."""

    @abstractmethod
    def compile(self, compiler_input: SpecCompilerInput) -> BusinessSpec:
        """Compile upstream values into a canonical BusinessSpec."""
        raise NotImplementedError


class BrandEngineInterface(ABC):
    """The Brand Engine's sole entry point (AES-WEB-001 §5.2 / Part 2)."""

    @abstractmethod
    def resolve(self, spec: BusinessSpec) -> BrandPackage:
        """Resolve a BusinessSpec into a deterministic BrandPackage."""
        raise NotImplementedError


class ComponentRegistryView(ABC):
    """Read-only registry protocol the Component Engine consumes (§15.3).

    The concrete registry implements this. Every accessor is a pure,
    deterministic lookup or index over declarative data — no selection,
    scoring, or ranking lives here (that is the §14 pipeline, a later wave).
    Returned collections are immutable tuples.
    """

    @abstractmethod
    def get(
        self, component_id: str, version_req: Optional[str] = None
    ) -> ComponentDefinition:
        """Return the definition for ``component_id`` (optionally a specific
        version). Raises ``ComponentNotFoundError`` /
        ``UnsupportedComponentVersionError``."""
        raise NotImplementedError

    @abstractmethod
    def resolve_variant(
        self, component_id: str, variant: str
    ) -> VariantSpec:
        """Return the ``VariantSpec`` for ``(component_id, variant)``."""
        raise NotImplementedError

    @abstractmethod
    def candidates_for(
        self, page_role: PageRole, slot_need: Optional[str] = None
    ) -> Tuple[ComponentDefinition, ...]:
        """Deterministic index lookup of components declaring support for
        ``page_role`` (sorted by ``component_id``). This is a registry index,
        not selection: no filtering pipeline, scoring, or tie-breaking."""
        raise NotImplementedError

    @abstractmethod
    def by_family(
        self, family: ComponentFamily
    ) -> Tuple[ComponentDefinition, ...]:
        """All definitions in ``family``, ordered by ``component_id``."""
        raise NotImplementedError

    @abstractmethod
    def lifecycle(self, component_id: str) -> LifecycleStatus:
        """The lifecycle status of ``component_id``."""
        raise NotImplementedError

    @abstractmethod
    def replacement_for(self, component_id: str) -> Optional[str]:
        """The replacement component id for a deprecated component, or None."""
        raise NotImplementedError

    @abstractmethod
    def registry_version(self) -> str:
        """The registry semantic version."""
        raise NotImplementedError

    @abstractmethod
    def registry_hash(self) -> str:
        """The SHA-256 registry fingerprint over all definitions."""
        raise NotImplementedError

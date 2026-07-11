"""Abstract interfaces for the Website Generation Engine (Phase 1 subset).

AES-WEB-001 §3.5 declares extension points as abstract interfaces in
``contracts/interfaces.py``. Phase 1 needs only the typed stage boundary
the skeleton pipeline composes against; DeploymentAdapter, GateCheck, and
CognitionProvider interfaces arrive with their implementing phases (never
before — no interface is declared here until a phase consumes it).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    SpecCompilerInput,
)


class SpecCompilerInterface(ABC):
    """The sole ingestion boundary into the WGE (AES-WEB-001 §5.1)."""

    @abstractmethod
    def compile(self, compiler_input: SpecCompilerInput) -> BusinessSpec:
        """Compile upstream values into a canonical BusinessSpec."""
        raise NotImplementedError

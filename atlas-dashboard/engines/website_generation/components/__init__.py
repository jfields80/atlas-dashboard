"""Component system package (AES-WEB-002A — Contracts and Registry;
AES-WEB-002J.6 — Component Engine).

Public surface for the component system: the deterministic
:class:`ComponentRegistry` and its helpers (002A), and the
:class:`ComponentEngine` §5.5 pipeline-stage facade (002J.6) that selects
components against each page's recipe and emits a ``ComponentManifest``.
This package contains no emitters or rendering (markup lives only in the
future ``rendering/`` package, AES-WEB-001 §8.1).
"""

from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    RegistryInventoryEntry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)
from engines.website_generation.components.component_engine import ComponentEngine

__all__ = [
    "ComponentEngine",
    "ComponentRegistry",
    "RegistryInventoryEntry",
    "REGISTERED_COMPONENTS",
    "build_default_registry",
    "definition_fingerprint",
    "validate_definition",
]

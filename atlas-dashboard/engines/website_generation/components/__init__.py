"""Component system package (AES-WEB-002A — Contracts and Registry).

Public surface for the component system at 002A exit: the deterministic
:class:`ComponentRegistry` and its helpers. The Component Engine (selection
and binding) and the component ``catalog/`` entries arrive in later waves
(AES-WEB-002B+); this package intentionally contains no emitters, selection
logic, or rendering.
"""

from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    RegistryInventoryEntry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)

__all__ = [
    "ComponentRegistry",
    "RegistryInventoryEntry",
    "REGISTERED_COMPONENTS",
    "build_default_registry",
    "definition_fingerprint",
    "validate_definition",
]

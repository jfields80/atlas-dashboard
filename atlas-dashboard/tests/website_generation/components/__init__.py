"""Component-system tests (AES-WEB-002A).

Shared valid-definition builder so registry and contract tests construct
well-formed :class:`ComponentDefinition` objects without repeating the full
field set. Overrides let each test vary exactly one facet.
"""

from __future__ import annotations

from engines.website_generation.contracts.components import (
    AnalyticsContract,
    ComponentDefinition,
    RenderingContract,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    SemanticElement,
)


def make_definition(**overrides) -> ComponentDefinition:
    """Build a valid ComponentDefinition; ``overrides`` replace fields."""
    fields = dict(
        component_id="hero.split.value-proposition",
        component_family=ComponentFamily.HERO,
        component_version="1.0.0",
        lifecycle_status=LifecycleStatus.ACTIVE,
        display_name="Split Hero",
        description="Value-proposition hero.",
        commercial_purpose=CommercialPurpose.COMMUNICATE_VALUE,
        supported_page_roles=(PageRole.HOME,),
        semantic_element=SemanticElement.SECTION,
        analytics_contract=AnalyticsContract(
            impression_id="hero-split-value-proposition"
        ),
        rendering_contract=RenderingContract(
            emitter_key="hero.split.value-proposition@1",
            class_prefix="ac-hero",
        ),
    )
    fields.update(overrides)
    return ComponentDefinition(**fields)

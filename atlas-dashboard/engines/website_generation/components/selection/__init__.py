"""Component selection (AES-WEB-002A skeleton + AES-WEB-002D production
pipeline; AES-WEB-002 §14, §31).

002A shipped the minimal deterministic selection skeleton required by the
§31 acceptance criterion. AES-WEB-002D adds the production §14.2 selection
pipeline (filtering, scoring, tie-breaking, variant selection, fallback) —
see :mod:`.selector` for both.
"""

from engines.website_generation.components.selection.selector import (
    ComponentSelector,
    LifecycleBuildFlags,
    SelectionSkeleton,
    SlotRequest,
    SlotSelectionRequest,
)

__all__ = [
    "ComponentSelector",
    "LifecycleBuildFlags",
    "SelectionSkeleton",
    "SlotRequest",
    "SlotSelectionRequest",
]

"""Component selection (AES-WEB-002A skeleton; AES-WEB-002 §14, §31).

002A ships only the minimal deterministic selection skeleton required by the
§31 acceptance criterion (see :mod:`.selector`). The production selection
pipeline (§14.2 filtering, scoring, tie-breaking, variant selection,
fallback) is a later wave (AES-WEB-002D) and is not implemented here.
"""

from engines.website_generation.components.selection.selector import (
    SelectionSkeleton,
    SlotRequest,
)

__all__ = [
    "SelectionSkeleton",
    "SlotRequest",
]

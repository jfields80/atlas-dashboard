"""Minimal deterministic selection skeleton (AES-WEB-002A; AES-WEB-002 §31).

This is an **interface/skeleton proof only** — it satisfies the §31 002A
acceptance criterion ("selection returns deterministic results + traces on
[an empty/]synthetic registry") without being the production Component
Engine. The full §14 selection pipeline (candidate capability filtering,
compatibility/lifecycle filtering, commercial-purpose matching, additive
integer scoring, deterministic tie-breaking, variant selection, fallback
handling) is assigned to a later wave (AES-WEB-002D) and is **not** here.

What this skeleton deliberately does NOT do (per the 002A scope):
no commercial scoring tables, no production filtering pipeline, no
tie-breaking, no brand-aware logic, no layout composition, no rendering, no
catalog population, no filesystem discovery, no global mutable state, no
clock/UUID/randomness/AI/IO. It is pure and deterministic.

What it does: for each requested slot it reads the registry's deterministic
page-role index (``candidates_for`` — an index lookup, not selection),
records every candidate into the already-authorized typed
:class:`SelectionTrace` (amendment A1, §14.3), and, when at least one
candidate exists, records the first candidate in the registry's existing
lexicographic order as the chosen result. "First of a pre-sorted index" is a
placeholder resolution, explicitly not the §14.2 scoring/tie-break pipeline;
``tie_break_basis`` is therefore left empty. When no candidate exists,
nothing is selected (empty ``chosen_*`` fields).
"""

from __future__ import annotations

from typing import Iterable, List

from engines.website_generation.contracts.artifacts import (
    FrozenModel,
    SelectionCandidate,
    SelectionTrace,
    SlotSelectionTrace,
)
from engines.website_generation.contracts.enums import PageRole
from engines.website_generation.contracts.interfaces import (
    ComponentRegistryView,
)


class SlotRequest(FrozenModel):
    """A typed request to fill one page slot (skeleton input).

    Minimal by design: the production selector consumes richer slot-need
    signatures (recipe capabilities, conversion objective, etc.) in a later
    wave. Here a request is just the slot id and the page role to index by.
    """

    slot_id: str
    page_role: PageRole


class SelectionSkeleton:
    """Deterministic, pure selection-skeleton proof (see module docstring)."""

    version = "0.0.0-skeleton"

    def select(
        self,
        registry: ComponentRegistryView,
        slot_requests: Iterable[SlotRequest],
    ) -> SelectionTrace:
        """Return a deterministic :class:`SelectionTrace` over ``registry``.

        Pure function of ``(registry contents, slot_requests)`` — identical
        inputs always yield an identical trace. Never raises for an empty
        result; an unfillable slot simply records no chosen component.
        """
        slots: List[SlotSelectionTrace] = []
        for request in slot_requests:
            candidates = registry.candidates_for(request.page_role)
            traced = tuple(
                SelectionCandidate(
                    component_id=definition.component_id,
                    component_version=definition.component_version,
                )
                for definition in candidates
            )
            if candidates:
                chosen = candidates[0]  # first of the registry's lexicographic
                # index — a placeholder, NOT §14.2 scoring/tie-breaking.
                slots.append(
                    SlotSelectionTrace(
                        slot_id=request.slot_id,
                        candidates=traced,
                        chosen_component_id=chosen.component_id,
                        chosen_component_version=chosen.component_version,
                    )
                )
            else:
                slots.append(
                    SlotSelectionTrace(
                        slot_id=request.slot_id,
                        candidates=(),
                    )
                )
        return SelectionTrace(slots=tuple(slots))

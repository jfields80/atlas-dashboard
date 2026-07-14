"""Declarative listing-repetition rules (AES-WEB-002J.20;
ADR-WEB-CONTENT-BINDING-MAP; AES-WEB-001 §5.5/§26).

The explicit, deterministic table telling the Component Engine's repetition
step (``component_engine.py``, between Phase A selection and Phase B
binding) whether a just-selected recipe slot's component definition should
be emitted as a single instance (no rule -- the AES-WEB-002J.19 default,
unchanged) or expanded into one concrete instance per matching
``ListingRecord`` (a rule present).

This module is data only: no selection logic, no binding logic, no I/O, no
clock/UUID/randomness/AI. It does not infer repetition from a component id
prefix (``"listing.*"``) or from a prop's ``LISTING_REF`` type -- both would
be implicit, undocumented conventions; a recipe slot repeats only when a
rule explicitly names its ``(page_role, recipe_slot_id)`` key, mirroring the
explicit-mapping doctrine ``binding_rules.py`` already established for
value binding (§14.2's "no invented metadata" discipline, extended).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class RepetitionSource(str, Enum):
    """Where a repeatable slot's matching records come from."""

    LISTING_CATEGORY_MATCH = "LISTING_CATEGORY_MATCH"


class RepetitionOrdering(str, Enum):
    """Deterministic ordering applied to matched records -- never a silent
    sort. ``DATASET_ORDER`` preserves ``ListingDataset.listings`` tuple
    order verbatim (the J.17 "producers sort, artifacts preserve" doctrine)."""

    DATASET_ORDER = "DATASET_ORDER"


@dataclass(frozen=True)
class RepetitionRule:
    """One recipe slot's repetition contract.

    ``page_role``/``recipe_slot_id`` are the same plain strings
    ``RECIPE_SLOTS_BY_PAGE_ROLE``/its slot dicts already use (no enum
    coercion needed at this layer). ``min_items`` is the honest-failure
    floor (0 = an empty collection is legal and yields zero instances; >=1
    = zero matches is a compile error naming ``no_matching_items``, never a
    fabricated record). ``max_items`` is ``None`` in every v1 rule (render
    all matches -- no pagination semantics invented); the field exists so a
    future deterministic cap is a one-line rule edit, not an engine change.
    ``exclude_self`` drops the hosting page's own listing from the match set
    (meaningful only when the route resolves a listing, e.g. a
    business-profile's ``related_listings``; a no-op on category routes,
    which resolve no ``route_scope.listing``).
    """

    page_role: str
    recipe_slot_id: str
    source: RepetitionSource
    min_items: int
    max_items: Optional[int]
    ordering: RepetitionOrdering
    exclude_self: bool


# AES-WEB-002J.20: the repetition rule table's own version, independent of
# component_engine's ENGINE_VERSIONS entry. Recorded in Phase-B provenance
# (ComponentManifest.source_hashes) so a manifest is replay-verifiable
# against the exact rule revision that produced it -- the BINDING_MAP_VERSION
# precedent. Bumped whenever COMPOSITION_RULES changes in a way that could
# change repetition output for identical artifact inputs -- never a timestamp.
COMPOSITION_RULES_VERSION: str = "1.0.0"


# v1 scope (operator-approved): listing collections only, two rules.
COMPOSITION_RULES: Tuple[RepetitionRule, ...] = (
    RepetitionRule(
        page_role="business-profile",
        recipe_slot_id="related_listings",
        source=RepetitionSource.LISTING_CATEGORY_MATCH,
        min_items=0,
        max_items=None,
        ordering=RepetitionOrdering.DATASET_ORDER,
        exclude_self=True,
    ),
    RepetitionRule(
        page_role="category",
        recipe_slot_id="listing_cards",
        source=RepetitionSource.LISTING_CATEGORY_MATCH,
        min_items=1,
        max_items=None,
        ordering=RepetitionOrdering.DATASET_ORDER,
        exclude_self=False,
    ),
)

COMPOSITION_RULES_BY_KEY: Dict[Tuple[str, str], RepetitionRule] = {
    (rule.page_role, rule.recipe_slot_id): rule for rule in COMPOSITION_RULES
}


def repetition_rule_for(page_role: str, recipe_slot_id: str) -> Optional[RepetitionRule]:
    """The declared :class:`RepetitionRule` for this recipe slot, or
    ``None`` when the slot is not repeatable (the J.19 single-instance path
    applies unchanged)."""
    return COMPOSITION_RULES_BY_KEY.get((page_role, recipe_slot_id))

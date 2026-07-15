"""Commercial strategy classification and strategy-aware recipe resolution
(AES-WEB-002L.1; EXTEND_EXISTING_RECIPE_SYSTEM verdict).

Two small, pure, deterministic functions -- no I/O, no clock, no
randomness, no AI, no network:

* :func:`classify_commercial_strategy` -- ``BusinessSpec`` -> a
  ``constants.commercial_strategy`` strategy id. Mirrors
  ``brand/token_resolver.resolve_family``'s exact shape (a lower-cased,
  space-joined keyword bag over the same kind of stable spec fields,
  substring-matched against a keyword table), because it is the same kind
  of problem the Brand Engine already solved once for family classification
  -- reusing the pattern, not re-deriving it.
* :func:`get_recipe_slots` -- ``(commercial_strategy, page_role)`` -> the
  recipe slot tuple to compose that page with, or ``None`` for an
  unsupported combination (the caller -- ``ComponentEngine.compile()`` --
  turns ``None`` into the same ``unsupported_page_roles`` diagnostic an
  unknown bare page role already produces; no new error type).

This module is the small amount of *logic* the constants-are-stdlib-only
doctrine forbids ``constants/commercial_strategy.py``/``constants/
components.py`` from containing themselves (classification needs
``BusinessSpec``, a ``contracts/`` model; recipe resolution needs both
constants modules, which may not cross-import each other) -- the same
constants-hold-data/components-hold-logic split ``composition_rules.py``
(J.20) already established for repetition rules.

Deliberately not a "Commercial Presentation Engine": no plan artifact, no
new registered schema, no business-goal reasoning. The Component Engine
consumes this module's output as declarative data exactly the way it
already consumes ``composition_rules.repetition_rule_for`` -- it does not
gain any new judgment of its own.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from engines.website_generation.constants.commercial_strategy import (
    STRATEGY_FALLBACK,
    STRATEGY_KEYWORDS,
)
from engines.website_generation.constants.components import (
    RECIPE_SLOTS_BY_STRATEGY_AND_ROLE,
)
from engines.website_generation.contracts.artifacts import BusinessSpec


def _keyword_bag(spec: BusinessSpec) -> str:
    """Lower-case, space-joined classification text -- the same field set
    and exclusion (never ``business_name``) as
    ``brand/token_resolver.build_keyword_bag``, plus ``monetization_model``
    (AES-WEB-002L.1 operator decision 9 names it as a preferred input for
    *this* classification specifically -- brand-family classification
    deliberately excludes it, but commercial strategy is precisely about
    monetization/conversion intent)."""
    parts = [spec.niche, spec.audience, spec.value_proposition, spec.monetization_model]
    parts.extend(sorted(spec.directory_taxonomy))
    return " ".join(parts).lower()


def classify_commercial_strategy(spec: BusinessSpec) -> str:
    """Classify ``spec`` into a commercial strategy id.

    Conservative by construction: DIRECTORY carries no keywords of its own
    (see ``constants/commercial_strategy.py``'s module docstring) and is
    returned whenever no LEAD_GENERATION phrase is present -- generic
    monetization language (e.g. ``"affiliate_booking_links"``) never
    contains one of the multi-word direct-response phrases
    ``STRATEGY_KEYWORDS`` declares, so it can never false-positive into
    LEAD_GENERATION merely because money is involved. This mirrors
    ``resolve_family``'s fallback rule and is architecturally justified the
    same way: this engine already assumes directory composition as the
    default archetype throughout (IA's page universe, ListingDataset,
    every existing recipe table)."""
    text = _keyword_bag(spec)
    for strategy, keywords in STRATEGY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return strategy
    return STRATEGY_FALLBACK


def get_recipe_slots(
    commercial_strategy: str, page_role: str
) -> Optional[Tuple[Dict[str, object], ...]]:
    """The recipe slot tuple for ``(commercial_strategy, page_role)``, or
    ``None`` if either the strategy or the (strategy, role) combination is
    unsupported -- never a silent fallback across strategies (AES-WEB-002L.1
    §17 error-model requirement)."""
    by_role = RECIPE_SLOTS_BY_STRATEGY_AND_ROLE.get(commercial_strategy)
    if by_role is None:
        return None
    return by_role.get(page_role)

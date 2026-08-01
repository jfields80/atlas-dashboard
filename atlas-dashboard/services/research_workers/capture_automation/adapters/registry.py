"""Brand slug -> adapter.

Phase 1 refuses unknown brands outright rather than falling back to a generic
heuristic. The generic adapter is Phase 3 work, and shipping a half-tuned one
early would turn "we have no adapter for this brand" -- a clear, actionable
exception -- into a quiet stream of low-confidence captures.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from .base import BaseAdapter
from .hilton import HiltonAdapter
from .marriott import MarriottAdapter

_REGISTRY: Dict[str, BaseAdapter] = {}


def register(adapter: BaseAdapter) -> None:
    _REGISTRY[adapter.brand.lower()] = adapter


def adapter_for(brand: str) -> Optional[BaseAdapter]:
    """The adapter for a brand, or None. None is a real answer here -- the
    runner turns it into ADAPTER_UNAVAILABLE and moves to the next hotel."""
    return _REGISTRY.get((brand or "").strip().lower())


def known_brands() -> Tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


register(MarriottAdapter())
register(HiltonAdapter())

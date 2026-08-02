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
from .ihg import IhgAdapter
from .marriott import MarriottAdapter
from .wyndham import WyndhamAdapter

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
register(IhgAdapter())
register(WyndhamAdapter())

# Deliberately NOT registered: Hyatt. hyatt.com serves a Kasada bot-defence
# interstitial to our visible Chrome -- an 811-byte shell containing only
# window.KPSDK and an ips.js challenge loader, which never resolves (measured
# unchanged across 15 seconds, readyState complete, 858 bytes transferred, page
# blank). Reaching the real page would mean satisfying that challenge, which
# ADR-PTF-AUTOMATED-BROWSING forbids by name. An adapter would be dead code
# whose only use would be to invite someone to try.
#
# Wyndham WAS on that list, for a reason that turned out to be half right:
# its pages do return HTTP 200 with EXACT_MATCH identity. What the note missed
# is that the 200 does not carry the policy. "Pet & Service Animal Policy"
# ships in the static markup; "Dogs Allowed - 2 dogs max. 75lbs or less per
# pet. Fees - 25 USD per pet per night." does not, and appears only once the
# page renders and the visible "Hotel Policies" control is opened. So the
# automated path could reach the page and never the policy, and the RETRIEVED
# status forbade anyone else from trying. PTF-CAPTURE-004A gave that state its
# own classification (RENDER_REQUIRED, reason policy_values_require_rendering)
# and 004B registers the adapter it licenses.

"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- the paid census fallback, as a contract.

Public Overpass being temporarily unavailable is not a reason to spend money.
The factory may REPORT that a paid discovery source (Google Places) could fill
the remaining cells -- ``PAID_DISCOVERY_FALLBACK_AVAILABLE`` -- but it may only
USE one under an explicit, authored authorisation that names the market, a
request cap, and the cost plan that priced it. There is no code path from
"Overpass is down" to "call Google".
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Mapping, Optional

SCHEMA = "ptf-paid-discovery-authorization/1.0"

PAID_DISCOVERY_FALLBACK_AVAILABLE = "PAID_DISCOVERY_FALLBACK_AVAILABLE"
PAID_DISCOVERY_FALLBACK_UNAVAILABLE = "PAID_DISCOVERY_FALLBACK_UNAVAILABLE"


class PaidFallbackError(ValueError):
    """The authorisation does not say who, why, how much, or for which market."""


def load(path: Path) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(document: Optional[Mapping], *, market_id: str) -> Dict:
    """Fail closed. Returns the normalised authorisation."""
    if document is None:
        raise PaidFallbackError("no paid-discovery authorisation was given; a "
                                "paid census source may not run without one")
    if document.get("schema") != SCHEMA:
        raise PaidFallbackError("authorisation schema is %r, not %s"
                                % (document.get("schema"), SCHEMA))
    if str(document.get("market_id") or "") != market_id:
        raise PaidFallbackError("authorisation is for %r, not %r"
                                % (document.get("market_id"), market_id))
    for field in ("authorised_by", "why", "cost_plan"):
        if not str(document.get(field) or "").strip():
            raise PaidFallbackError("authorisation lacks %s" % field)
    cap = int(document.get("max_google_requests") or 0)
    if cap <= 0:
        raise PaidFallbackError("authorisation must cap Google requests above 0")
    return OrderedDict((
        ("schema", SCHEMA), ("market_id", market_id),
        ("authorised_by", str(document["authorised_by"])),
        ("why", str(document["why"])),
        ("cost_plan", str(document["cost_plan"])),
        ("max_google_requests", cap),
        ("authorised_on", str(document.get("authorised_on") or "")),
    ))


def availability(*, google_key_present: bool, remaining_cells: int) -> Dict:
    available = bool(google_key_present and remaining_cells > 0)
    return OrderedDict((
        ("state", PAID_DISCOVERY_FALLBACK_AVAILABLE if available
                  else PAID_DISCOVERY_FALLBACK_UNAVAILABLE),
        ("google_key_present", bool(google_key_present)),
        ("remaining_cells", int(remaining_cells)),
        ("requires", "an explicit %s document naming the market, an author, a "
                     "reason, a Google request cap and a cost plan; never runs "
                     "because public Overpass is unavailable" % SCHEMA),
    ))


__all__ = ["SCHEMA", "PAID_DISCOVERY_FALLBACK_AVAILABLE",
           "PAID_DISCOVERY_FALLBACK_UNAVAILABLE", "PaidFallbackError", "load",
           "validate", "availability"]

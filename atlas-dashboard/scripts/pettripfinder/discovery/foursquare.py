"""AES-DATA-004A discovery -- reserved Foursquare adapter seam (Task 5).

No live Foursquare integration ships in this phase, and no endpoint is
assumed -- Foursquare's current API surface was not confirmed against
official documentation as part of this mission (doctrine #18/#19: do not
invent endpoints, do not add Yelp/Data Axle either). This module exists so
the query planner and CLI can refer to ``PROVIDER_FOURSQUARE`` uniformly
without special-casing it, and so a real adapter can be dropped in later
without changing any caller's shape.

Absence of ``FOURSQUARE_API_KEY`` must never fail Google or Overpass
discovery -- ``query_plan.plan_queries`` already emits every Foursquare
query with ``enabled=False``, and ``FoursquareClient.search`` always
returns a clean ``DISABLED``/``SKIPPED_NO_CREDENTIAL`` result rather than
raising, so a caller that (incorrectly) invoked it anyway still degrades
safely.
"""

from __future__ import annotations

import os

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult


class ProviderUnavailable(Exception):
    """Raised only by ``require_available`` -- an explicit opt-in check for
    callers that want a hard failure instead of a soft DISABLED result."""


def api_key_present(env_var: str = C.FOURSQUARE_API_KEY_ENV) -> bool:
    return bool(os.environ.get(env_var, "").strip())


class FoursquareClient:
    """Stub. Never makes a network call in this phase."""

    def __init__(self, api_key_env: str = C.FOURSQUARE_API_KEY_ENV):
        self._api_key_env = api_key_env

    def search(self, query, *, cache=None, budget=None, observed_at: str = "",
               bounds=None) -> ProviderQueryResult:
        if not query.enabled:
            return ProviderQueryResult(query_id=query.query_id, provider=C.PROVIDER_FOURSQUARE,
                                       state=C.QUERY_STATE_DISABLED)
        if not api_key_present(self._api_key_env):
            return ProviderQueryResult(query_id=query.query_id, provider=C.PROVIDER_FOURSQUARE,
                                       state=C.QUERY_STATE_SKIPPED_NO_CREDENTIAL,
                                       error=C.PROVIDER_ERROR_UNAVAILABLE)
        # A credential could theoretically be present with no implementation
        # behind it yet -- still refuse cleanly rather than fabricate data.
        return ProviderQueryResult(query_id=query.query_id, provider=C.PROVIDER_FOURSQUARE,
                                   state=C.QUERY_STATE_SKIPPED_NO_CREDENTIAL,
                                   error=C.PROVIDER_ERROR_UNAVAILABLE,
                                   warnings=("foursquare_adapter_not_implemented",))

    def require_available(self) -> None:
        raise ProviderUnavailable(
            "Foursquare adapter is a reserved seam in AES-DATA-004A -- no live "
            "client is implemented; see foursquare.py module docstring.")

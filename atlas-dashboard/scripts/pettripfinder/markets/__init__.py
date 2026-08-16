"""PTF-MARKETS -- national market/corridor configuration layer.

The single shared authority for market and corridor semantics across the
PetTripFinder build chain (PTF-CORRIDORS-002). Markets and corridors are
DATA (versioned ``ptf-market/1.1`` JSON under
``launch_packages/pettripfinder/markets/``); this package supplies the
deterministic, market-agnostic machinery:

- ``contract``   -- schema constants, fail-closed parsing/validation, loading
- ``assignment`` -- deterministic hotel->corridor assignment + reporting
- ``routes``     -- market/corridor/hotel route construction, duplicate
                    routes fail closed
- ``navigation`` -- published-corridor navigation + sitemap entries
- ``display``    -- the unified corridor display labels used by hotel
                    profiles and related cards

No module here may special-case a market: adding a market is a data change
only. Pure functions; reading the committed config files is the only IO.
"""

from scripts.pettripfinder.markets.assignment import (
    CorridorAssignment,
    MarketAssignmentError,
    assign_hotels,
)
from scripts.pettripfinder.markets.contract import (
    DEFAULT_MINIMUM_HOTEL_COUNT,
    HOMEPAGE_FIELDS,
    MARKETS_DIR,
    ROUTE_MODE_LEGACY_UNPREFIXED,
    ROUTE_MODE_MARKET_PREFIXED,
    SCHEMA_VERSION,
    CorridorConfig,
    HomepageConfig,
    MarketConfig,
    MarketContractError,
    default_market,
    derive_homepage,
    homepage_config,
    load_markets,
    market_by_id,
    parse_market,
    slugify,
)
from scripts.pettripfinder.markets.display import (
    corridor_display_area,
    corridor_display_label,
)
from scripts.pettripfinder.markets.navigation import (
    NavEntry,
    corridor_href_for,
    corridor_navigation,
    sitemap_corridor_routes,
)
from scripts.pettripfinder.markets.routes import (
    MarketRouteError,
    build_route_table,
    corridor_route,
    hotel_route,
    market_route,
)

__all__ = [
    "CorridorAssignment",
    "CorridorConfig",
    "DEFAULT_MINIMUM_HOTEL_COUNT",
    "HOMEPAGE_FIELDS",
    "HomepageConfig",
    "MARKETS_DIR",
    "MarketAssignmentError",
    "MarketConfig",
    "MarketContractError",
    "MarketRouteError",
    "NavEntry",
    "ROUTE_MODE_LEGACY_UNPREFIXED",
    "ROUTE_MODE_MARKET_PREFIXED",
    "SCHEMA_VERSION",
    "assign_hotels",
    "build_route_table",
    "corridor_display_area",
    "corridor_display_label",
    "corridor_href_for",
    "corridor_navigation",
    "corridor_route",
    "default_market",
    "derive_homepage",
    "homepage_config",
    "hotel_route",
    "load_markets",
    "market_by_id",
    "market_route",
    "parse_market",
    "sitemap_corridor_routes",
    "slugify",
]

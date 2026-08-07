"""PTF-MULTIMARKET-001 -- the explicit market context of the PetTripFinder build.

``scripts/pettripfinder/markets`` is deliberately market-agnostic: no module
in it may name a real market. But the code in *this* package is not agnostic
-- it generates, assembles, and reports one specific published site, whose
seed inventory, policy package, release contract, and live routes are all
Columbus. Until this build learns to generate a second site, that fact is
better stated once, here, than inferred at seven call sites from "whichever
market happens to be the only one configured".

That inference was the single-market assumption. It made registering a
second market -- a pure data addition -- break the Columbus build, because
``default_market`` (correctly) refuses to guess between two configs. Naming
the market removes the coupling in the honest direction: the production path
now says which market it is building, so configuring market N+1 cannot
change what market N publishes.

``default_market`` keeps its fail-closed guard for genuinely single-market
callers; nothing here weakens it.
"""

from __future__ import annotations

from scripts.pettripfinder.markets import MarketConfig, load_markets, market_by_id

#: The market this repository's production site publishes. Every production
#: build-path caller resolves through this id rather than through positional
#: or count-based selection.
PRODUCTION_MARKET_ID = "columbus-oh"


def production_market() -> MarketConfig:
    """The committed configuration for ``PRODUCTION_MARKET_ID``.

    Fails closed if that market is not configured -- a build must never fall
    back to a different market's corridors because the expected config file
    was missing or renamed."""
    return market_by_id(load_markets(), PRODUCTION_MARKET_ID)


def resolve_market(market: MarketConfig = None, market_id: str = None) -> MarketConfig:
    """Resolve the market a build-path caller should use.

    Accepts an already-resolved ``MarketConfig`` (the preferred form: the
    caller threads its context down), or a ``market_id`` to look up, or
    neither -- in which case this build's production market is used. In no
    case is the market chosen by how many configs exist."""
    if market is not None:
        return market
    return market_by_id(load_markets(), market_id or PRODUCTION_MARKET_ID)


__all__ = ["PRODUCTION_MARKET_ID", "production_market", "resolve_market"]

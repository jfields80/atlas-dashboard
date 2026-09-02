"""PTF-FACTORY-THROUGHPUT-HARDENING-001 -- the CURRENT market and deployment
state, read from ONE reviewed pin file each.

WHY THIS EXISTS
---------------
PTF-DAYTON-OH-HARDENED-APPLICATION-002 published seven records and broke 85
tests across 19 modules. None of them had found a defect: each module carried
its own private copy of "Dayton has 47 records", and every copy went stale at
once. A number that dozens of files restate is not a pin, it is a tax on every
future market.

So the current state is pinned ONCE, in ``pins/market_state.json`` and
``pins/deployment_state.json``, and tests whose meaning is "the market as it
stands now" read it from here. The pin files are explicit, reviewed documents
-- written by the work order that moved the market, never computed from the
files they describe. The single place they are held to the source is
``contracts/test_market_state_pins.py``; every other consumer trusts the pin,
which is what makes a legitimate move a one-file edit instead of a nineteen-
module hunt.

WHAT THIS IS NOT
----------------
It is not a derivation. Nothing here opens a policy package, a census or a
manifest. A test that wants to know whether the pin is TRUE runs the contract
test; a test that wants to know what the pin SAYS calls :func:`current`.

Historical numbers -- what a market held when a closed work order ran -- do not
belong here. They belong to that order's own epoch, declared in its suite with
:class:`pettripfinder.epochs.HistoricalEpoch`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

PINS_DIR = Path(__file__).resolve().parent / "pins"
MARKET_STATE_PATH = PINS_DIR / "market_state.json"
DEPLOYMENT_STATE_PATH = PINS_DIR / "deployment_state.json"

MARKET_STATE_SCHEMA = "ptf-market-state-pins/1.0"
DEPLOYMENT_STATE_SCHEMA = "ptf-deployment-state-pins/1.0"

#: The counts a market pin must state. ``resolved`` and ``unresolved`` are
#: stated rather than derived so that a swap that leaves a total unchanged
#: still has to be written down somewhere a reviewer reads.
MARKET_FIELDS: Tuple[str, ...] = (
    "census", "pet_friendly", "verified_no_pets", "resolved", "unresolved",
    "out_of_category", "profiles", "corridor_routes", "last_moved_by",
)


@dataclass(frozen=True)
class MarketState:
    """One market's current source state, as pinned."""

    market_id: str
    census: int
    pet_friendly: int
    verified_no_pets: int
    resolved: int
    unresolved: int
    out_of_category: int
    profiles: int
    corridor_routes: int
    last_moved_by: str

    @property
    def published(self) -> int:
        """Alias: the older suites say ``published`` for ``pet_friendly``."""
        return self.pet_friendly

    @property
    def no_pets(self) -> int:
        """Alias: the older suites say ``no_pets`` for ``verified_no_pets``."""
        return self.verified_no_pets

    def as_dict(self) -> Dict[str, object]:
        return {field: getattr(self, field) for field in MARKET_FIELDS}


@dataclass(frozen=True)
class DeploymentState:
    """One block of the deployment pin: ``live`` or ``source``."""

    kind: str
    bundle_sha256: str
    sitemap_sha256: str
    participating_markets: Tuple[str, ...]
    profile_counts: Mapping[str, int]
    total_profiles: int
    sitemap_route_count: int
    total_html_pages: int
    total_files: int
    #: ``live`` only.
    deploy_id: Optional[str] = None
    deployed_by: Optional[str] = None
    authorization_id: Optional[str] = None
    deployment_record_id: Optional[str] = None
    source_commit: Optional[str] = None
    previous_deploy_id: Optional[str] = None
    rollback_target: Optional[str] = None
    #: ``source`` only.
    ahead_of_production: Optional[bool] = None
    moved_by: Optional[str] = None


def _read(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def market_state_document() -> Dict:
    doc = _read(MARKET_STATE_PATH)
    if doc.get("schema") != MARKET_STATE_SCHEMA:
        raise ValueError("%s: expected schema %s, found %r"
                         % (MARKET_STATE_PATH.name, MARKET_STATE_SCHEMA,
                            doc.get("schema")))
    return doc


def deployment_state_document() -> Dict:
    doc = _read(DEPLOYMENT_STATE_PATH)
    if doc.get("schema") != DEPLOYMENT_STATE_SCHEMA:
        raise ValueError("%s: expected schema %s, found %r"
                         % (DEPLOYMENT_STATE_PATH.name, DEPLOYMENT_STATE_SCHEMA,
                            doc.get("schema")))
    return doc


def market_ids() -> Tuple[str, ...]:
    """Every market the pin file describes, in file order."""
    return tuple(market_state_document()["markets"].keys())


def current(market_id: str) -> MarketState:
    """The pinned current state of one market.

    Raises ``KeyError`` for a market the pin file does not describe: a test
    asking about a market nobody has reviewed must fail, not default.
    """
    markets = market_state_document()["markets"]
    if market_id not in markets:
        raise KeyError("%s is not pinned in %s" % (market_id, MARKET_STATE_PATH.name))
    row = markets[market_id]
    missing = [f for f in MARKET_FIELDS if f not in row]
    if missing:
        raise ValueError("%s: pin for %s lacks %s"
                         % (MARKET_STATE_PATH.name, market_id, missing))
    return MarketState(market_id=market_id, **{f: row[f] for f in MARKET_FIELDS})


def all_current() -> Dict[str, MarketState]:
    return {m: current(m) for m in market_ids()}


def _block(kind: str) -> DeploymentState:
    doc = deployment_state_document()
    block = doc[kind]
    return DeploymentState(
        kind=kind,
        bundle_sha256=block["bundle_sha256"],
        sitemap_sha256=block["sitemap_sha256"],
        participating_markets=tuple(block["participating_markets"]),
        profile_counts=dict(block["profile_counts"]),
        total_profiles=block["total_profiles"],
        sitemap_route_count=block["sitemap_route_count"],
        total_html_pages=block["total_html_pages"],
        total_files=block["total_files"],
        deploy_id=block.get("deploy_id"),
        deployed_by=block.get("deployed_by"),
        authorization_id=block.get("authorization_id"),
        deployment_record_id=block.get("deployment_record_id"),
        source_commit=block.get("source_commit"),
        previous_deploy_id=block.get("previous_deploy_id"),
        rollback_target=block.get("rollback_target"),
        ahead_of_production=block.get("ahead_of_production"),
        moved_by=block.get("moved_by"),
    )


def live() -> DeploymentState:
    """What production serves. Moved only by a deployment-authorization order."""
    return _block("live")


def source_assembly() -> DeploymentState:
    """What a FRESH assembly of the committed source produces.

    Equal to :func:`live` except while an application order has put source
    ahead of production, in which case ``ahead_of_production`` is true and
    ``moved_by`` names the order.
    """
    return _block("source")


__all__ = [
    "PINS_DIR", "MARKET_STATE_PATH", "DEPLOYMENT_STATE_PATH",
    "MARKET_STATE_SCHEMA", "DEPLOYMENT_STATE_SCHEMA", "MARKET_FIELDS",
    "MarketState", "DeploymentState", "market_state_document",
    "deployment_state_document", "market_ids", "current", "all_current",
    "live", "source_assembly",
]

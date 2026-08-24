"""How a page is FETCHED. Nothing here knows how it will be understood.

An :class:`AcquisitionProvider` is a capability description plus one coroutine.
The router talks to capabilities -- can this lane run JavaScript, can it click,
does it produce a screenshot, what does it cost -- and never to a vendor name.
That is the difference between a router and a Bright Data wrapper.

WHAT IS AND IS NOT IMPLEMENTED
------------------------------
Two providers are implemented because two are configured and measured. The
plug-in point for the rest is real -- :func:`register` takes any object
satisfying the protocol -- and it is deliberately empty. A provider stub that
makes no network call teaches nothing and a provider stub that makes one
without credentials is a speculative call this work order forbids.
:data:`KNOWN_FUTURE_PROVIDERS` documents the candidates without pretending.

DIRECT_HTTP IS RESERVED, NOT BUILT
----------------------------------
The long-term goal is that PetTripFinder owns acquisition for easy pages and
pays a vendor only for hard ones. That slot is declared here so the router's
ladder can already express "cheapest first" honestly, and it is declared
UNAVAILABLE so nothing routes to it by accident.

The wrapped modules are the ones the pilots measured. Reusing them rather than
reimplementing is what keeps this layer a router: every capture rule already
proven -- three fresh attempts, one outcome each, only VALID writes an
artifact, blank crops refused, quotes contiguous -- stays exactly where it was
proven.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, FrozenSet, List, Mapping, Optional, Protocol, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import readers as READERS_MOD  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC    # noqa: E402
from scripts.pettripfinder.brightdata import client                   # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_capture as CBC  # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC   # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_capture as FC  # noqa: E402

# --------------------------------------------------------------------------- #
# Capabilities. What a lane can do, not who sells it.
# --------------------------------------------------------------------------- #

RUNS_JAVASCRIPT = "runs_javascript"
CAN_INTERACT = "can_interact"
TAKES_SCREENSHOTS = "takes_screenshots"
READS_UNRENDERED_DOM = "reads_unrendered_dom"
BYPASSES_BOT_PROTECTION = "bypasses_bot_protection"
GEO_PINNABLE = "geo_pinnable"

CAPABILITIES: Tuple[str, ...] = (
    RUNS_JAVASCRIPT, CAN_INTERACT, TAKES_SCREENSHOTS, READS_UNRENDERED_DOM,
    BYPASSES_BOT_PROTECTION, GEO_PINNABLE,
)


@dataclass(frozen=True)
class CostMetadata:
    """What a lane costs, as measured -- never as advertised.

    Two currencies, never mixed. Bright Data bills dollars and Firecrawl bills
    plan credits, and the Firecrawl plan endpoint reports an allowance rather
    than a unit price -- so there is no honest exchange rate between them.
    A lane fills in the field it is actually billed in and leaves the other
    ``None``; summing the two would invent a number nobody measured.
    """

    usd_minor_per_property: Optional[float]
    basis: str
    measured_by: str
    #: Plan credits per property, for lanes billed in credits rather than money.
    credits_per_property: Optional[float] = None

    @property
    def currency(self) -> str:
        if self.usd_minor_per_property is not None:
            return "usd_minor"
        if self.credits_per_property is not None:
            return "plan_credits"
        return "none"

    def to_dict(self) -> Dict:
        return {"usd_minor_per_property": self.usd_minor_per_property,
                "credits_per_property": self.credits_per_property,
                "currency": self.currency,
                "basis": self.basis, "measured_by": self.measured_by}


@dataclass(frozen=True)
class ProviderHealth:
    available: bool
    detail: str = ""

    def to_dict(self) -> Dict:
        return {"available": self.available, "detail": self.detail}


class AcquisitionProvider(Protocol):
    """The interface a lane must satisfy to be routable."""

    provider_id: str
    product: str
    capabilities: FrozenSet[str]

    def health_check(self) -> ProviderHealth: ...

    def cost_metadata(self) -> CostMetadata: ...

    def supported_failure_recovery(self) -> FrozenSet[str]: ...

    async def acquire(self, target, *, run_dir: Path, reader_id: str,
                      max_attempts: int): ...


@dataclass(frozen=True)
class _WrappedProvider:
    """A provider backed by one of the measured capture modules.

    The wrapper is thin on purpose. It selects the reader's preferred container
    and hands the capture module the same arguments the pilots used, so the
    behaviour the reports describe is the behaviour the router gets.
    """

    provider_id: str
    product: str
    capabilities: FrozenSet[str]
    module: object
    cost: CostMetadata
    recovers: FrozenSet[str]
    health: Callable[[], ProviderHealth]
    #: Extra keyword arguments the capture module accepts. Firecrawl takes a
    #: request profile, and the routed lane must use the SAME profile the
    #: benchmarks used or the measurement stops describing production.
    capture_kwargs: Mapping = field(default_factory=dict)

    def health_check(self) -> ProviderHealth:
        return self.health()

    def cost_metadata(self) -> CostMetadata:
        return self.cost

    def supported_failure_recovery(self) -> FrozenSet[str]:
        return self.recovers

    async def acquire(self, target, *, run_dir: Path, reader_id: str,
                      max_attempts: int = BC.MAX_ATTEMPTS):
        """Run this lane. Returns (attempt records, payload or None).

        ``reader_id`` selects the locator preference; the capture module's own
        competition rule decides whether that preference wins.
        """
        brand = READERS_MOD.locator_brand_for(reader_id)
        return await self.module.capture_property(
            target, run_dir=run_dir, brand=brand, max_attempts=max_attempts,
            **dict(self.capture_kwargs))


def _browser_health() -> ProviderHealth:
    if not client.credential_present():
        return ProviderHealth(False, "%s is not set" % client.AUTH_ENV)
    return ProviderHealth(True, "Browser API credential present; exit "
                                "geography pinned to %r"
                                % client.DEFAULT_COUNTRY)


def _firecrawl_health() -> ProviderHealth:
    if not FC.credential_present():
        return ProviderHealth(False, "%s is not set" % FC.KEY_ENV)
    return ProviderHealth(True, "Firecrawl credential present; exit geography "
                                "pinned to %r"
                                % FC.ROUTED_PROFILE["location"]["country"])


def _unlocker_health() -> ProviderHealth:
    import shutil
    if not shutil.which(client.CLI_NAME):
        return ProviderHealth(False, "the %r CLI is not on PATH"
                              % client.CLI_NAME)
    if not client.credential_present():
        return ProviderHealth(False, "%s is not set" % client.AUTH_ENV)
    return ProviderHealth(True, "unlocker zones %s"
                          % (", ".join(UC.UNLOCKER_ZONES)))


BRIGHTDATA_BROWSER = "brightdata_browser"
BRIGHTDATA_WEB_UNLOCKER = "brightdata_web_unlocker"
FIRECRAWL = "firecrawl"
DIRECT_HTTP = "direct_http"

_PROVIDERS: Dict[str, AcquisitionProvider] = {}


def register(provider: AcquisitionProvider) -> None:
    """Add a provider. The plug-in point, and it is genuinely open."""
    _PROVIDERS[provider.provider_id] = provider


register(_WrappedProvider(
    provider_id=BRIGHTDATA_BROWSER,
    product="Bright Data Browser API",
    capabilities=frozenset({RUNS_JAVASCRIPT, CAN_INTERACT, TAKES_SCREENSHOTS,
                            READS_UNRENDERED_DOM, GEO_PINNABLE}),
    module=CBC,
    cost=CostMetadata(usd_minor_per_property=16.0,
                      basis="zone delta / properties attempted",
                      measured_by="PTF-ACQUISITION-BRAND-REPAIR-003"),
    # A managed browser survives a shell or a challenge that a plain fetch
    # cannot, and can wait for JavaScript that never ran for the unlocker.
    recovers=frozenset({"BLANK_PAGE", "UNHYDRATED", "TIMEOUT",
                        "NAVIGATION_FAILED", "IDENTITY_UNCERTAIN"}),
    health=_browser_health))

register(_WrappedProvider(
    provider_id=BRIGHTDATA_WEB_UNLOCKER,
    product="Bright Data Web Unlocker",
    capabilities=frozenset({BYPASSES_BOT_PROTECTION, GEO_PINNABLE}),
    module=UC,
    cost=CostMetadata(usd_minor_per_property=5.0,
                      basis="zone delta / properties attempted on the Choice "
                            "lane",
                      measured_by="PTF-ACQUISITION-BRAND-REPAIR-003"),
    # It answered Choice where the managed browser was refused fifteen times.
    recovers=frozenset({"ACCESS_DENIED", "UNEXPECTED_PAGE", "GEO_MISMATCH"}),
    health=_unlocker_health))


register(_WrappedProvider(
    provider_id=FIRECRAWL,
    product="Firecrawl scrape API",
    # Measured capabilities only. It renders JavaScript before returning and
    # its exit geography is pinnable, both of which were exercised. It is NOT
    # given CAN_INTERACT: the routed lane runs a plain scrape, and the
    # deterministic interaction pass belongs to the benchmarks, not here.
    capabilities=frozenset({RUNS_JAVASCRIPT, GEO_PINNABLE}),
    module=FC,
    # Billed in plan credits. The plan endpoint reports an allowance and not a
    # unit price, so no dollar figure is asserted and none may be inferred.
    cost=CostMetadata(usd_minor_per_property=None,
                      basis="plan credits / properties acquired across 17 "
                            "Milwaukee Choice acquisitions; failed scrape "
                            "calls were not charged, which is an observation "
                            "and not a billing guarantee",
                      measured_by="PTF-FIRECRAWL-CHOICE-VALIDATION-004, "
                                  "PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005",
                      credits_per_property=1.0),
    # What it demonstrably survived that the incumbent did not: four Choice
    # properties the Web Unlocker returned ACCESS_DENIED on, and the heading-
    # only surfaces the Browser API returned where this lane waits for the
    # policy node to paint.
    recovers=frozenset({"ACCESS_DENIED", "UNHYDRATED", "BLANK_PAGE"}),
    health=_firecrawl_health,
    # The profile the decision was measured with. Not a default, not a copy.
    capture_kwargs={"profile": FC.ROUTED_PROFILE}))


#: Reserved so the ladder can say "cheapest first" honestly today. Declared
#: UNAVAILABLE, and nothing routes to it until somebody builds it.
@dataclass(frozen=True)
class _ReservedProvider:
    provider_id: str
    product: str
    capabilities: FrozenSet[str] = frozenset()
    reason: str = ""

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(False, self.reason)

    def cost_metadata(self) -> CostMetadata:
        return CostMetadata(None, "not implemented", "n/a")

    def supported_failure_recovery(self) -> FrozenSet[str]:
        return frozenset()

    async def acquire(self, target, *, run_dir: Path, reader_id: str,
                      max_attempts: int = BC.MAX_ATTEMPTS):
        raise RuntimeError("%s is reserved and not implemented" % self.provider_id)


register(_ReservedProvider(
    provider_id=DIRECT_HTTP,
    product="PetTripFinder direct fetch",
    reason="reserved slot: PTF-owned acquisition for pages that need no "
           "vendor. Declared so the ladder can express cheapest-first, and "
           "unavailable so nothing routes to it by accident."))


#: Documented, not implemented, and not called. Each would need credentials and
#: a measured benchmark before it could earn a row in the routing registry.
#: ``firecrawl`` was removed from this list by
#: PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006: it earned its row the way this
#: comment always said it would have to, with a benchmark against the same
#: properties (15/15 against the incumbent's 7/15 on the Milwaukee Choice
#: queue). ``spider`` stays: it was benchmarked and it FAILED, 7/25.
KNOWN_FUTURE_PROVIDERS: Dict[str, str] = {
    "spider": "benchmarked in PTF-SPIDER-BENCHMARK-001 and not adopted: it "
              "returned JavaScript shells and reached 7 of 25 properties",
    "apify": "no credential configured; same requirement",
    "playwright_local": "no managed exit geography; would reintroduce the "
                        "locale-redirect failure the US pin exists to prevent",
}


class ProviderError(KeyError):
    """No such provider."""


def get(provider_id: str) -> AcquisitionProvider:
    try:
        return _PROVIDERS[provider_id]
    except KeyError:
        raise ProviderError(
            "unknown provider %r; registered providers are %s"
            % (provider_id, sorted(_PROVIDERS)))


def available() -> Tuple[str, ...]:
    """Providers whose health check passes right now."""
    return tuple(sorted(pid for pid, p in _PROVIDERS.items()
                        if p.health_check().available))


def implemented() -> Tuple[str, ...]:
    """Providers that can actually run, reserved slots excluded."""
    return tuple(sorted(pid for pid, p in _PROVIDERS.items()
                        if not isinstance(p, _ReservedProvider)))


def all_ids() -> Tuple[str, ...]:
    return tuple(sorted(_PROVIDERS))


def describe() -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for pid, provider in sorted(_PROVIDERS.items()):
        out[pid] = {"product": provider.product,
                    "capabilities": sorted(provider.capabilities),
                    "cost": provider.cost_metadata().to_dict(),
                    "recovers": sorted(provider.supported_failure_recovery()),
                    "health": provider.health_check().to_dict(),
                    "implemented": not isinstance(provider, _ReservedProvider)}
    return out


__all__ = [
    "RUNS_JAVASCRIPT", "CAN_INTERACT", "TAKES_SCREENSHOTS",
    "READS_UNRENDERED_DOM", "BYPASSES_BOT_PROTECTION", "GEO_PINNABLE",
    "CAPABILITIES", "CostMetadata", "ProviderHealth", "AcquisitionProvider",
    "BRIGHTDATA_BROWSER", "BRIGHTDATA_WEB_UNLOCKER", "FIRECRAWL", "DIRECT_HTTP",
    "KNOWN_FUTURE_PROVIDERS", "ProviderError", "register", "get", "available",
    "implemented", "all_ids", "describe",
]

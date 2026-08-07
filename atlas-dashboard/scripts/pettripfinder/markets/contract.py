"""ptf-market/1.0 -- market/corridor configuration contract.

Fail-closed parsing and validation for the committed market configuration
files under ``launch_packages/pettripfinder/markets/``. A malformed or
ambiguous configuration NEVER degrades silently: every violation raises
``MarketContractError`` naming the offending field, so a bad config can
never generate a partially-wrong public site.

Design constraints (PTF-CORRIDORS-002):

- Markets and corridors are pure data. Nothing in this module (or this
  package) may name a real market: adding market N+1 is a config file, not
  a code change.
- Designed for the United States now (five-digit postal codes are enforced
  for ``country_code == "US"``) without preventing other countries later
  (non-US postal codes only need to be non-empty strings).
- Hotel identity in ``explicit_hotel_ids`` / ``excluded_hotel_ids`` is the
  normalized-name key used by every existing PetTripFinder join
  (``site_data.normalize_name``) -- the same key the committed policy
  package and the display-review decisions resolve through. Ids must
  already be in normalized form; a non-normalized id is a config error.
- No coordinates: the production schema carries none, and the contract must
  not require what the data cannot honestly supply.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.pettripfinder.site_data import normalize_name

SCHEMA_VERSION = "ptf-market/1.0"

REPO_ROOT = Path(__file__).resolve().parents[3]
MARKETS_DIR = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"

#: Default per-corridor publication minimum (the historical Task-7 threshold,
#: unchanged). A corridor config may override it per corridor.
DEFAULT_MINIMUM_HOTEL_COUNT = 5

#: Target national route architecture: /pet-friendly-hotels/{market_slug}/...
ROUTE_MODE_MARKET_PREFIXED = "market_prefixed"
#: Backward-compatibility mode for a market launched BEFORE the national
#: route architecture (Columbus): routes stay unprefixed under
#: /pet-friendly-hotels/ until an explicitly approved URL migration.
ROUTE_MODE_LEGACY_UNPREFIXED = "legacy_unprefixed"
_ROUTE_MODES = (ROUTE_MODE_MARKET_PREFIXED, ROUTE_MODE_LEGACY_UNPREFIXED)

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_STATE_CODE_RE = re.compile(r"^[A-Z]{2}$")
_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")
_US_POSTAL_RE = re.compile(r"^\d{5}$")


class MarketContractError(ValueError):
    """A market configuration violates the ptf-market contract (fail closed)."""


def slugify(text: str) -> str:
    """The shared route-slug rule (identical to the site generator's)."""
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


@dataclass(frozen=True)
class CorridorConfig:
    corridor_id: str
    market_id: str
    name: str
    slug: str
    title: str
    meta_description: str
    description: str
    included_cities: Tuple[str, ...]
    included_postal_codes: Tuple[str, ...]
    explicit_hotel_ids: Tuple[str, ...]
    excluded_hotel_ids: Tuple[str, ...]
    minimum_hotel_count: int
    show_in_navigation: bool
    show_in_sitemap: bool
    allow_multi_corridor: bool
    display_order: int
    #: Short area label for hotel-profile chips ("Downtown", "West Hilliard").
    #: Defaults to ``name``; presentation only, never used for assignment.
    display_area: str


@dataclass(frozen=True)
class MarketConfig:
    market_id: str
    market_name: str
    market_slug: str
    state_name: str
    state_code: str
    primary_city: str
    country_code: str
    title: str
    meta_description: str
    introductory_copy: str
    navigation_label: str
    show_in_navigation: bool
    show_in_sitemap: bool
    minimum_published_hotels: int
    route_mode: str
    corridors: Tuple[CorridorConfig, ...] = field(default_factory=tuple)

    def corridor_by_id(self, corridor_id: str) -> CorridorConfig:
        for corridor in self.corridors:
            if corridor.corridor_id == corridor_id:
                return corridor
        raise KeyError(corridor_id)


def _require(data: Dict, key: str, kind, source: str, *, allow_empty: bool = False):
    if key not in data:
        raise MarketContractError("%s: missing required field %r" % (source, key))
    value = data[key]
    if kind is bool:
        if not isinstance(value, bool):
            raise MarketContractError("%s: field %r must be a boolean" % (source, key))
        return value
    if kind is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise MarketContractError("%s: field %r must be an integer" % (source, key))
        return value
    if kind is str:
        if not isinstance(value, str):
            raise MarketContractError("%s: field %r must be a string" % (source, key))
        if not allow_empty and not value.strip():
            raise MarketContractError("%s: field %r must be non-empty" % (source, key))
        return value
    if kind is list:
        if not isinstance(value, list):
            raise MarketContractError("%s: field %r must be a list" % (source, key))
        return value
    raise AssertionError("unknown kind %r" % kind)


def _string_tuple(data: Dict, key: str, source: str) -> Tuple[str, ...]:
    items = _require(data, key, list, source)
    out: List[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise MarketContractError(
                "%s: field %r entries must be non-empty strings (got %r)" % (source, key, item))
        out.append(item.strip())
    if len(set(out)) != len(out):
        raise MarketContractError("%s: field %r contains duplicates" % (source, key))
    return tuple(out)


def _parse_corridor(data: Dict, market_id: str, country_code: str, source: str) -> CorridorConfig:
    corridor_id = _require(data, "corridor_id", str, source)
    src = "%s corridor %r" % (source, corridor_id)
    cm = _require(data, "market_id", str, src)
    if cm != market_id:
        raise MarketContractError(
            "%s: corridor market_id %r does not match its market %r" % (src, cm, market_id))
    slug = _require(data, "slug", str, src)
    if not _SLUG_RE.match(slug):
        raise MarketContractError("%s: invalid slug %r" % (src, slug))
    postal_codes = _string_tuple(data, "included_postal_codes", src)
    if country_code == "US":
        for code in postal_codes:
            if not _US_POSTAL_RE.match(code):
                raise MarketContractError(
                    "%s: US postal codes must be exactly five digits (got %r)" % (src, code))
    explicit = _string_tuple(data, "explicit_hotel_ids", src)
    excluded = _string_tuple(data, "excluded_hotel_ids", src)
    for label, ids in (("explicit_hotel_ids", explicit), ("excluded_hotel_ids", excluded)):
        for hotel_id in ids:
            if normalize_name(hotel_id) != hotel_id:
                raise MarketContractError(
                    "%s: %s entry %r is not a normalized-name key" % (src, label, hotel_id))
    contradictory = sorted(set(explicit) & set(excluded))
    if contradictory:
        raise MarketContractError(
            "%s: hotel ids listed as both explicit and excluded: %s" % (src, contradictory))
    minimum = _require(data, "minimum_hotel_count", int, src)
    if minimum < 1:
        raise MarketContractError(
            "%s: minimum_hotel_count must be >= 1 (empty corridors never publish)" % src)
    display_area = data.get("display_area", data["name"] if isinstance(data.get("name"), str) else "")
    if not isinstance(display_area, str) or not display_area.strip():
        raise MarketContractError("%s: display_area must be a non-empty string" % src)
    return CorridorConfig(
        corridor_id=corridor_id,
        market_id=cm,
        name=_require(data, "name", str, src),
        slug=slug,
        title=_require(data, "title", str, src),
        meta_description=_require(data, "meta_description", str, src),
        description=_require(data, "description", str, src, allow_empty=True),
        included_cities=_string_tuple(data, "included_cities", src),
        included_postal_codes=postal_codes,
        explicit_hotel_ids=explicit,
        excluded_hotel_ids=excluded,
        minimum_hotel_count=minimum,
        show_in_navigation=_require(data, "show_in_navigation", bool, src),
        show_in_sitemap=_require(data, "show_in_sitemap", bool, src),
        allow_multi_corridor=_require(data, "allow_multi_corridor", bool, src),
        display_order=_require(data, "display_order", int, src),
        display_area=display_area.strip(),
    )


def parse_market(data: Dict, source: str = "<inline>") -> MarketConfig:
    """Validate one market document (fail closed) and return its config."""
    if not isinstance(data, dict):
        raise MarketContractError("%s: market document must be a JSON object" % source)
    schema = data.get("schema")
    if schema != SCHEMA_VERSION:
        raise MarketContractError(
            "%s: unsupported schema %r (expected %r)" % (source, schema, SCHEMA_VERSION))
    market_id = _require(data, "market_id", str, source)
    src = "%s market %r" % (source, market_id)
    market_slug = _require(data, "market_slug", str, src)
    if not _SLUG_RE.match(market_slug):
        raise MarketContractError("%s: invalid market_slug %r" % (src, market_slug))
    state_code = _require(data, "state_code", str, src)
    if not _STATE_CODE_RE.match(state_code):
        raise MarketContractError("%s: state_code must be two uppercase letters" % src)
    country_code = _require(data, "country_code", str, src)
    if not _COUNTRY_CODE_RE.match(country_code):
        raise MarketContractError("%s: country_code must be two uppercase letters" % src)
    route_mode = data.get("route_mode", ROUTE_MODE_MARKET_PREFIXED)
    if route_mode not in _ROUTE_MODES:
        raise MarketContractError("%s: route_mode must be one of %s" % (src, list(_ROUTE_MODES)))
    minimum_published = _require(data, "minimum_published_hotels", int, src)
    if minimum_published < 1:
        raise MarketContractError("%s: minimum_published_hotels must be >= 1" % src)

    corridors_raw = _require(data, "corridors", list, src)
    corridors = tuple(
        _parse_corridor(c, market_id, country_code, src) for c in corridors_raw)
    seen_ids: Dict[str, str] = {}
    seen_slugs: Dict[str, str] = {}
    seen_orders: Dict[int, str] = {}
    for corridor in corridors:
        if corridor.corridor_id in seen_ids:
            raise MarketContractError(
                "%s: duplicate corridor_id %r" % (src, corridor.corridor_id))
        if corridor.slug in seen_slugs:
            raise MarketContractError(
                "%s: duplicate corridor slug %r (corridor slugs must be unique "
                "within their market)" % (src, corridor.slug))
        if corridor.display_order in seen_orders:
            raise MarketContractError(
                "%s: duplicate display_order %d (corridors %r and %r) -- ordering "
                "must be deterministic" % (src, corridor.display_order,
                                           seen_orders[corridor.display_order],
                                           corridor.corridor_id))
        seen_ids[corridor.corridor_id] = corridor.corridor_id
        seen_slugs[corridor.slug] = corridor.corridor_id
        seen_orders[corridor.display_order] = corridor.corridor_id

    return MarketConfig(
        market_id=market_id,
        market_name=_require(data, "market_name", str, src),
        market_slug=market_slug,
        state_name=_require(data, "state_name", str, src),
        state_code=state_code,
        primary_city=_require(data, "primary_city", str, src),
        country_code=country_code,
        title=_require(data, "title", str, src),
        meta_description=_require(data, "meta_description", str, src),
        introductory_copy=_require(data, "introductory_copy", str, src, allow_empty=True),
        navigation_label=_require(data, "navigation_label", str, src),
        show_in_navigation=_require(data, "show_in_navigation", bool, src),
        show_in_sitemap=_require(data, "show_in_sitemap", bool, src),
        minimum_published_hotels=minimum_published,
        route_mode=route_mode,
        corridors=corridors,
    )


def validate_markets(markets: Tuple[MarketConfig, ...]) -> Tuple[MarketConfig, ...]:
    """Cross-market invariants: globally unique market ids/slugs and corridor
    ids. Corridor SLUGS only need to be unique inside their market (two
    markets may both have a 'downtown' corridor)."""
    seen_market_ids: Dict[str, str] = {}
    seen_market_slugs: Dict[str, str] = {}
    seen_corridor_ids: Dict[str, str] = {}
    for market in markets:
        if market.market_id in seen_market_ids:
            raise MarketContractError("duplicate market_id %r" % market.market_id)
        if market.market_slug in seen_market_slugs:
            raise MarketContractError(
                "duplicate market_slug %r (market slugs are globally unique)"
                % market.market_slug)
        seen_market_ids[market.market_id] = market.market_id
        seen_market_slugs[market.market_slug] = market.market_id
        for corridor in market.corridors:
            if corridor.corridor_id in seen_corridor_ids:
                raise MarketContractError(
                    "duplicate corridor_id %r (corridor ids are globally unique; "
                    "already defined by market %r)"
                    % (corridor.corridor_id, seen_corridor_ids[corridor.corridor_id]))
            seen_corridor_ids[corridor.corridor_id] = market.market_id
    return markets


def load_markets(markets_dir: Optional[Path] = None) -> Tuple[MarketConfig, ...]:
    """Load and validate every committed market config, sorted by market_id.
    Missing directory fails closed -- a build must never silently run with
    zero markets because of a path typo."""
    directory = Path(markets_dir) if markets_dir is not None else MARKETS_DIR
    if not directory.is_dir():
        raise MarketContractError("markets directory does not exist: %s" % directory)
    markets: List[MarketConfig] = []
    for path in sorted(directory.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as exc:
                raise MarketContractError("%s: invalid JSON: %s" % (path.name, exc))
        markets.append(parse_market(data, source=path.name))
    markets.sort(key=lambda m: m.market_id)
    return validate_markets(tuple(markets))


def default_market(markets: Tuple[MarketConfig, ...]) -> MarketConfig:
    """The implied market for genuinely single-market callers. With more than
    one market configured there is no honest default: callers must then name
    the market explicitly, so this fails closed.

    PTF-MULTIMARKET-001: the production build path no longer relies on this.
    Site generation, assembly, rendering, and reporting resolve their market
    by id through ``market_by_id`` so that registering market N+1 cannot
    change what an existing market publishes. This helper remains for
    one-market tools (ad-hoc scripts, config inspection) where ambiguity is
    impossible -- and it must keep failing closed for them."""
    if len(markets) != 1:
        raise MarketContractError(
            "default_market requires exactly one configured market, found %d (%s); "
            "pass the market explicitly" % (len(markets), [m.market_id for m in markets]))
    return markets[0]


def market_by_id(markets: Tuple[MarketConfig, ...], market_id: str) -> MarketConfig:
    """The named market, regardless of how many others are configured.

    The explicit counterpart to ``default_market``: a caller that knows which
    market it is building states so, and an unknown id fails closed rather
    than falling back to whatever happens to be configured."""
    for market in markets:
        if market.market_id == market_id:
            return market
    raise MarketContractError(
        "no configured market with market_id %r (configured: %s)"
        % (market_id, [m.market_id for m in markets]))

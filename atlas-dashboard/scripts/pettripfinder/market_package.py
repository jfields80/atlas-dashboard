"""PTF-MULTI-MARKET-INVENTORY-SCOPING-001 -- market packages and their assembly.

Two things are deliberately kept apart here, because conflating them is how a
second market silently rewrites the first one's release:

  MARKET PACKAGE   what one market owns -- its hotel routes, its corridor
                   routes, its reconciliation counts, and the hashes of the
                   files it produced.
  PRODUCTION SITE  several validated market packages plus global pages and
                   shared assets.

Adding Cleveland legitimately changes the production site. It must not change
one byte of Columbus's owned files, nor Columbus's reconciliation. The assembly
function below is what makes that checkable rather than hoped for: it refuses a
combination whose packages collide, and it reports each market's hashes
unchanged through the merge.

The manifest is a description of a build, never an input to one. It is written
outside the generated site directory on purpose -- a manifest placed inside the
bundle would change the bundle it claims to describe.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

MARKET_PACKAGE_SCHEMA = "ptf-market-package/1.0"


class MarketPackageError(ValueError):
    """Two market packages cannot be combined without losing information."""


@dataclass(frozen=True)
class MarketPackage:
    """One market's owned slice of a build.

    ``file_hashes`` covers only files this market owns. Shared and global
    artifacts (the home page, sitemap, stylesheet) are excluded, because every
    market would otherwise claim them and any combination would look like a
    collision.
    """

    market_id: str
    authority_commit: str
    #: ``None`` means the committed authority does not state it. Columbus's
    #: confirmed universe lives in work-order reports, not in a committed
    #: census, and emitting 0 would read as "no identities confirmed" -- a
    #: false statement that a reconciliation gate would happily compare
    #: against. Absent is a fact; zero is a claim.
    confirmed_identity_count: Optional[int]
    published_pet_friendly_count: int
    verified_no_pets_count: int
    unresolved_count: Optional[int]
    hotel_routes: Tuple[str, ...]
    corridor_routes: Tuple[str, ...]
    corridor_unassigned_hotels: Tuple[str, ...]
    file_hashes: Mapping[str, str] = field(default_factory=dict)
    schema: str = MARKET_PACKAGE_SCHEMA

    def owned_routes(self) -> Tuple[str, ...]:
        return tuple(self.hotel_routes) + tuple(self.corridor_routes)

    def reconciliation(self) -> Tuple[Optional[int], int, int, int, Optional[int]]:
        """(confirmed, published, no-pets, resolved, unresolved)."""
        resolved = self.published_pet_friendly_count + self.verified_no_pets_count
        return (self.confirmed_identity_count, self.published_pet_friendly_count,
                self.verified_no_pets_count, resolved, self.unresolved_count)

    def to_manifest(self) -> OrderedDict:
        c, p, n, r, u = self.reconciliation()
        return OrderedDict([
            ("schema", self.schema),
            ("market_id", self.market_id),
            ("authority_commit", self.authority_commit),
            ("reconciliation", OrderedDict([
                ("confirmed_identities", c), ("published_pet_friendly", p),
                ("verified_no_pets", n), ("resolved", r), ("unresolved", u)])),
            ("owned_hotel_routes", len(self.hotel_routes)),
            ("owned_corridor_routes", len(self.corridor_routes)),
            ("corridor_unassigned_but_published", len(self.corridor_unassigned_hotels)),
            ("corridor_unassigned_hotels", list(self.corridor_unassigned_hotels)),
            ("hotel_routes", list(self.hotel_routes)),
            ("corridor_routes", list(self.corridor_routes)),
            ("owned_file_count", len(self.file_hashes)),
            ("owned_file_hashes", OrderedDict(sorted(self.file_hashes.items()))),
        ])


def hash_owned_files(site_root: Path, routes: Sequence[str]) -> Dict[str, str]:
    """sha256 of the ``index.html`` behind each owned route.

    A missing file is an error rather than a skipped entry: a package that
    claims a route it did not produce would pass a hash comparison by having
    nothing to compare.
    """
    out: Dict[str, str] = {}
    for route in routes:
        path = site_root / route.strip("/") / "index.html"
        if not path.is_file():
            raise MarketPackageError(
                "market package claims route %r but %s does not exist" % (route, path))
        out[route] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def assemble_market_packages(packages: Sequence[MarketPackage], *,
                             global_routes: Sequence[str] = ()) -> OrderedDict:
    """Combine validated market packages into one production-site description.

    Refuses, rather than resolving, four failure modes:

      route collision      two markets claiming the same route -- whoever wrote
                           last would win, and the loser would vanish
      duplicate market     the same market id supplied twice
      corridor crossover   a corridor route claimed by a market that does not
                           own it (shared corridor NAMES are fine; shared
                           ROUTES are not)
      global shadowing     a market claiming a route the shared site owns

    Every market's hashes and reconciliation pass through untouched. That is
    the property the caller actually needs: combining packages is additive, so
    a market's output cannot be altered by the presence of another market.
    """
    if not packages:
        raise MarketPackageError("no market packages supplied")

    seen_markets: Dict[str, MarketPackage] = {}
    for pkg in packages:
        if pkg.market_id in seen_markets:
            raise MarketPackageError("market %r supplied twice" % pkg.market_id)
        seen_markets[pkg.market_id] = pkg

    owner: Dict[str, str] = {}
    collisions: List[str] = []
    for pkg in packages:
        for route in pkg.owned_routes():
            prior = owner.get(route)
            if prior is not None and prior != pkg.market_id:
                collisions.append("%s claimed by %r and %r" % (route, prior, pkg.market_id))
            owner[route] = pkg.market_id
    if collisions:
        raise MarketPackageError("route collision between market packages: %s"
                                 % sorted(collisions))

    shadowed = sorted(set(owner) & set(global_routes))
    if shadowed:
        raise MarketPackageError(
            "market package claims globally-owned route(s): %s" % shadowed)

    combined_hashes: Dict[str, str] = {}
    for pkg in packages:
        combined_hashes.update(pkg.file_hashes)

    return OrderedDict([
        ("schema", "ptf-production-site-assembly/1.0"),
        ("market_count", len(packages)),
        ("markets", [p.market_id for p in packages]),
        ("total_owned_routes", len(owner)),
        ("global_routes", list(global_routes)),
        ("route_owner", OrderedDict(sorted(owner.items()))),
        ("per_market", OrderedDict(
            (p.market_id, OrderedDict([
                ("reconciliation", p.to_manifest()["reconciliation"]),
                ("owned_hotel_routes", len(p.hotel_routes)),
                ("owned_corridor_routes", len(p.corridor_routes)),
                ("corridor_unassigned_but_published",
                 len(p.corridor_unassigned_hotels)),
                ("owned_file_hashes", OrderedDict(sorted(p.file_hashes.items()))),
            ])) for p in packages)),
        ("combined_owned_file_count", len(combined_hashes)),
    ])


def write_manifest(package: MarketPackage, destination: Path) -> Path:
    """Write one market's manifest OUTSIDE any generated site directory."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(package.to_manifest(), indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    return destination

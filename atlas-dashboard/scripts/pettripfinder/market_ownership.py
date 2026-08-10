"""PTF-MULTI-MARKET-INVENTORY-SCOPING-001 -- explicit primary market ownership.

Atlas was built as a one-market product. Nothing in the inventory schema said
which market a row belonged to, because there was only ever one answer, and the
generator selected *every* approved row. That is fine until a second market's
inventory exists, at which point Cleveland hotels silently appear in the
Columbus package.

The obvious fix is wrong, and this module exists because of why.

Corridor membership is NOT market ownership. Corridor assignment has a fifth
tier -- "unassigned: published normally, reported, never dropped" -- and twelve
live Columbus hotels sit in it deliberately (Westerville, New Albany, Gahanna,
Canal Winchester and the Easton cluster, none of which is inside a published
corridor). Selecting "hotels some corridor claims" would delete those twelve
from production. Ownership therefore has to be its own fact, recorded on the
row, independent of whether any corridor happens to claim it.

The contract:

  * every inventory row carries exactly one ``market_id``
  * that id must exist in the committed market registry
  * missing, blank, or unknown ownership FAILS CLOSED -- it never defaults to
    the market being built, because defaulting is precisely how a foreign row
    would slip into a package
  * ownership is independent of corridor assignment in both directions
  * one identity may not hold primary ownership in two markets

Fail-closed is the whole point. A silent default would reintroduce the bug this
module was written to remove, one release after someone forgets the column.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

from scripts.pettripfinder.markets import load_markets

#: The inventory column carrying primary market ownership.
MARKET_ID_FIELD = "market_id"


class MarketOwnershipError(ValueError):
    """Inventory ownership is missing, unknown, or contradictory.

    Raised rather than warned. A build that cannot say which market owns a row
    must not guess which package the row belongs in.
    """


def _normalize_identity(name: str) -> str:
    """Identity key for duplicate-ownership detection.

    Deliberately the same normalization the rest of the pipeline joins on, so a
    row that would collide during the publication join collides here too.
    """
    from scripts.pettripfinder.site_data import normalize_name

    return normalize_name(name)


def registered_market_ids(markets: Optional[Sequence] = None) -> Set[str]:
    """The market ids the committed registry actually defines.

    The registry -- not a constant in this module -- is the authority. Hard-
    coding the list here would let code and configuration disagree, and the
    disagreement would only surface as a wrongly-scoped package.
    """
    configs = load_markets() if markets is None else markets
    return {m.market_id for m in configs}


def ownership_of(row: Mapping) -> str:
    """The single market id a row claims, or "" when it claims none."""
    return str(row.get(MARKET_ID_FIELD, "") or "").strip()


def validate_ownership(rows: Iterable[Mapping], *,
                       registered: Optional[Set[str]] = None,
                       context: str = "inventory") -> Dict[str, str]:
    """Check every row's ownership; return {identity_key: market_id}.

    Three separate failures, reported together rather than one at a time, so a
    migration sees the whole picture in one run instead of peeling it off row
    by row:

      missing   -- no ``market_id`` at all (the pre-migration state)
      unknown   -- an id the market registry does not define (typo, or a market
                   whose config was never committed)
      conflict  -- one identity claiming two different markets
    """
    known = registered_market_ids() if registered is None else registered
    missing: List[str] = []
    unknown: List[str] = []
    owner: Dict[str, str] = {}
    conflict: List[str] = []

    for row in rows:
        name = str(row.get("name", "") or "")
        market_id = ownership_of(row)
        if not market_id:
            missing.append(name)
            continue
        if market_id not in known:
            unknown.append("%s -> %r" % (name, market_id))
            continue
        key = _normalize_identity(name)
        prior = owner.get(key)
        if prior is not None and prior != market_id:
            conflict.append("%s -> %r and %r" % (name, prior, market_id))
            continue
        owner[key] = market_id

    if missing or unknown or conflict:
        parts = []
        if missing:
            parts.append("no %s on %d row(s): %s"
                         % (MARKET_ID_FIELD, len(missing), sorted(missing)[:10]))
        if unknown:
            parts.append("market id not in the committed registry (known=%s): %s"
                         % (sorted(known), sorted(unknown)[:10]))
        if conflict:
            parts.append("identity claims two primary markets: %s" % sorted(conflict)[:10])
        raise MarketOwnershipError(
            "%s ownership is not publishable (fail-closed): %s" % (context, "; ".join(parts)))
    return owner


def owned_by(rows: Iterable[Mapping], market_id: str, *,
             registered: Optional[Set[str]] = None,
             context: str = "inventory") -> List[Mapping]:
    """The rows this market owns, in input order.

    Validation runs over EVERY row first, not only the ones being selected. A
    filter that ignored malformed foreign rows would happily build a correct
    Columbus package on top of an inventory file that cannot produce a correct
    Cleveland one -- and the error would surface in the wrong market's release.
    """
    known = registered_market_ids() if registered is None else registered
    target = str(market_id or "").strip()
    if target not in known:
        raise MarketOwnershipError(
            "cannot build a package for unregistered market %r (known=%s)"
            % (market_id, sorted(known)))
    materialized = list(rows)
    validate_ownership(materialized, registered=known, context=context)
    return [r for r in materialized if ownership_of(r) == target]


def ownership_summary(rows: Iterable[Mapping]) -> Dict[str, int]:
    """Row counts per market id, for migration audits and reports."""
    out: Dict[str, int] = {}
    for row in rows:
        out[ownership_of(row) or "<missing>"] = out.get(ownership_of(row) or "<missing>", 0) + 1
    return dict(sorted(out.items()))

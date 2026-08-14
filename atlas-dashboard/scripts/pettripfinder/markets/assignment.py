"""Deterministic hotel -> corridor assignment (PTF-CORRIDORS-002).

The ONE assignment authority for every corridor surface: corridor pages,
sitemap routes, hotel-profile display labels, breadcrumbs, category card
tags, and /go/ metadata all derive from the result produced here.

Assignment order (each hotel independently, first matching tier wins):

    1. explicit exclusion   (removes the hotel from that corridor entirely)
    2. explicit assignment  (``explicit_hotel_ids``)
    3. exact five-digit ZIP match
    4. exact (city, state) match  (case-insensitive city, exact state)
    5. unassigned           (published normally, reported -- never dropped)

PTF-GEOGRAPHY-NORMALIZATION-001 changed two things about that order.

POSTAL CODE NOW OUTRANKS CITY. A ZIP is a smaller unit than a mailing city,
and mailing cities routinely span corridors while ZIPs rarely do. Four
Cincinnati properties in ZIP 45255 carry the mailing city "Cincinnati" and sit
about fifteen miles east in Eastgate; under city-first they resolved to
Downtown Cincinnati, which is not where a traveller would find them. Someone
had already noticed and hand-placed them -- and then labelled the placement
``postal_code``, because the honest basis was not available to them.

CITY MATCHING IS STATE-AWARE. Matching a bare city string means Dayton,
Kentucky matches a Dayton, Ohio corridor. That has never fired only because no
market spanned two states; Cincinnati spans three.

Every assignment records the basis that ACTUALLY fired and the value that fired
it, and a validator proves the claim: a ZIP basis requires that ZIP in the
corridor's registry, a city_state basis requires that exact pair, an explicit
basis requires the identity key in the list. No human judgement may be labelled
``postal_code``.

Rules enforced:

- No fuzzy matching, and hotel NAMES are never read for assignment (only
  the normalized name as an identity KEY for explicit lists).
- A hotel matching more than one corridor in the same tier is AMBIGUOUS:
  it fails closed unless every matched corridor sets
  ``allow_multi_corridor`` (in which case it belongs to all of them).
- A corridor below its ``minimum_hotel_count`` (or empty) does not publish;
  its members are still assigned (labels may render) but no route, nav
  entry, or sitemap entry is produced for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from scripts.pettripfinder.markets.contract import CorridorConfig, MarketConfig
from scripts.pettripfinder.site_data import normalize_name

#: The canonical basis vocabulary. These are the values a census row records,
#: so they are the contract's names rather than the tier's internal ones.
TIER_EXPLICIT = "explicit"
TIER_ZIP = "postal_code"
TIER_CITY = "city_state"
TIER_UNASSIGNED = "unassigned"

#: Legacy basis spellings found in committed censuses, and what they became.
#: ``county_name`` is NOT here: no county tier exists, so a row claiming it was
#: unreproducible by construction and had to be resolved against evidence
#: rather than translated.
LEGACY_BASES = {"city_name": TIER_CITY, "postal_code": TIER_ZIP,
                "explicit": TIER_EXPLICIT, "unassigned": TIER_UNASSIGNED}

SUPPRESS_EMPTY = "empty"
SUPPRESS_BELOW_MINIMUM = "below_minimum"


class MarketAssignmentError(ValueError):
    """Ambiguous or invalid assignment state (fail closed)."""


@dataclass(frozen=True)
class CorridorAssignment:
    """Deterministic assignment result for one market over one row set."""

    market: MarketConfig
    #: corridor_id -> member rows (sorted by normalized name)
    members: Mapping[str, Tuple[Dict, ...]]
    #: normalized hotel key -> corridor_ids it belongs to (config order)
    corridor_of: Mapping[str, Tuple[str, ...]]
    #: normalized hotel key -> tier that assigned it
    tier_of: Mapping[str, str]
    #: normalized hotel key -> (basis, the exact value that fired it). This is
    #: what a census row records, and what the validator proves against the
    #: registry -- a basis nobody can check is a basis that will be wrong.
    basis_of: Mapping[str, Tuple[str, str]]
    #: corridor_id -> normalized keys explicitly assigned
    explicit_members: Mapping[str, Tuple[str, ...]]
    #: corridor_id -> normalized keys of rows in the input that were excluded
    excluded_members: Mapping[str, Tuple[str, ...]]
    #: rows assigned to no corridor (published normally, reported)
    unassigned: Tuple[Dict, ...]
    #: unauthorized multi-corridor matches: (hotel key, tier, corridor_ids)
    conflicts: Tuple[Dict, ...]
    #: corridor_ids that publish (member count >= corridor minimum)
    published: Tuple[str, ...]
    #: suppressed corridors: {corridor_id, reason, member_count}
    suppressed: Tuple[Dict, ...]

    def published_corridors(self) -> Tuple[CorridorConfig, ...]:
        published = set(self.published)
        return tuple(c for c in self.market.corridors if c.corridor_id in published)

    def members_of(self, corridor_id: str) -> Tuple[Dict, ...]:
        return self.members.get(corridor_id, ())


def _row_city(row: Dict) -> str:
    return (row.get("city", "") or "").strip().lower()


def _row_state(row: Dict) -> str:
    return (row.get("state", "") or "").strip().upper()


def _row_zip(row: Dict) -> str:
    return (row.get("postal_code", "") or "").strip()[:5]


def _match_tier(corridors: Sequence[CorridorConfig], key: str, city: str,
                state: str, zip5: str) -> Tuple[str, str, List[CorridorConfig]]:
    """The first tier that matches, the value that fired it, and its corridors."""
    explicit = [c for c in corridors if key in c.explicit_hotel_ids]
    if explicit:
        return TIER_EXPLICIT, key, explicit
    by_zip = [c for c in corridors if zip5 and zip5 in c.included_postal_codes]
    if by_zip:
        return TIER_ZIP, zip5, by_zip
    by_city = [c for c in corridors
               if city and city in tuple(x.lower() for x in c.included_cities)
               # A corridor with no declared state belongs to a single-state
               # market and matches within it; one that declares a state must
               # agree with the property's own.
               and (not c.state_code or not state or c.state_code == state)]
    if by_city:
        return TIER_CITY, "%s, %s" % (city, state) if state else city, by_city
    return "", "", []


def assignment_basis(assignment: "CorridorAssignment", key: str) -> Tuple[str, str]:
    """``(basis, value)`` for one hotel: what fired, and what fired it.

    ``(unassigned, "")`` where nothing matched -- which is a legitimate result,
    not a failure. A hotel with no corridor still publishes; it simply does not
    appear on a corridor page until its geography is strong enough to place it.
    """
    return assignment.basis_of.get(key, (TIER_UNASSIGNED, ""))


def assign_hotels(market: MarketConfig, hotel_rows: Sequence[Dict], *,
                  fail_closed: bool = True) -> CorridorAssignment:
    """Assign every row deterministically. ``fail_closed=True`` (the build
    default) raises on any unauthorized multi-corridor match;
    ``fail_closed=False`` records the conflicts instead (review tooling
    only -- the affected hotels stay UNASSIGNED, never guessed)."""
    members: Dict[str, List[Dict]] = {c.corridor_id: [] for c in market.corridors}
    corridor_of: Dict[str, Tuple[str, ...]] = {}
    tier_of: Dict[str, str] = {}
    basis_of: Dict[str, Tuple[str, str]] = {}
    explicit_members: Dict[str, List[str]] = {c.corridor_id: [] for c in market.corridors}
    excluded_members: Dict[str, List[str]] = {c.corridor_id: [] for c in market.corridors}
    unassigned: List[Dict] = []
    conflicts: List[Dict] = []

    seen_keys: set = set()
    for row in sorted(hotel_rows, key=lambda r: normalize_name(r.get("name", ""))):
        key = normalize_name(row.get("name", ""))
        if not key:
            raise MarketAssignmentError("hotel row without a name cannot be assigned: %r" % row)
        if key in seen_keys:
            raise MarketAssignmentError(
                "duplicate hotel key %r in assignment input (hotel routes must be "
                "unique inside their market)" % key)
        seen_keys.add(key)
        for corridor in market.corridors:
            if key in corridor.excluded_hotel_ids:
                excluded_members[corridor.corridor_id].append(key)
        eligible = [c for c in market.corridors if key not in c.excluded_hotel_ids]
        tier, value, matched = _match_tier(
            eligible, key, _row_city(row), _row_state(row), _row_zip(row))
        if not matched:
            unassigned.append(row)
            continue
        if len(matched) > 1 and not all(c.allow_multi_corridor for c in matched):
            conflicts.append({
                "hotel": key,
                "tier": tier,
                "corridor_ids": tuple(c.corridor_id for c in matched),
            })
            unassigned.append(row)
            continue
        corridor_of[key] = tuple(c.corridor_id for c in matched)
        tier_of[key] = tier
        basis_of[key] = (tier, value)
        for corridor in matched:
            members[corridor.corridor_id].append(row)
            if tier == TIER_EXPLICIT:
                explicit_members[corridor.corridor_id].append(key)

    if conflicts and fail_closed:
        raise MarketAssignmentError(
            "ambiguous multi-corridor assignment in market %r (fail closed; "
            "authorize via allow_multi_corridor on every matched corridor, or "
            "resolve with explicit assignment/exclusion): %s"
            % (market.market_id,
               ["%s -> %s (%s tier)" % (c["hotel"], list(c["corridor_ids"]), c["tier"])
                for c in conflicts]))

    published: List[str] = []
    suppressed: List[Dict] = []
    for corridor in market.corridors:
        count = len(members[corridor.corridor_id])
        if count == 0:
            suppressed.append({"corridor_id": corridor.corridor_id,
                               "reason": SUPPRESS_EMPTY, "member_count": 0})
        elif count < corridor.minimum_hotel_count:
            suppressed.append({"corridor_id": corridor.corridor_id,
                               "reason": SUPPRESS_BELOW_MINIMUM, "member_count": count})
        else:
            published.append(corridor.corridor_id)

    return CorridorAssignment(
        market=market,
        members={cid: tuple(rows) for cid, rows in members.items()},
        corridor_of=dict(corridor_of),
        tier_of=dict(tier_of),
        basis_of=dict(basis_of),
        explicit_members={cid: tuple(keys) for cid, keys in explicit_members.items()},
        excluded_members={cid: tuple(keys) for cid, keys in excluded_members.items()},
        unassigned=tuple(unassigned),
        conflicts=tuple(conflicts),
        published=tuple(published),
        suppressed=tuple(suppressed),
    )

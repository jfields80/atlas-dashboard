"""PTF-ST-LOUIS-MARKET-001 -- discovery candidates -> market identity census.

The gap this closes
-------------------
Atlas could already discover a market (``discovery_cli run``) and it could
already rebuild a census from committed authority
(``census_partition_builder``). Between the two there was nothing: every market
built before this one turned a candidate list into a
``ptf-market-identity-census/1.1`` by hand, in a market-specific script
(``build_milwaukee_market_001.py``, ``indianapolis_market_factory.py``,
``build_pittsburgh_market_001.py``, ``build_detroit_ann_arbor_market_001.py`` --
four scripts, ~4,600 lines, doing the same four things).

This module is those four things, once, generically:

    1. category      -- is this candidate lodging in our current category?
    2. membership    -- is it in the market, on the basis the market's
                        contract declares (see discovery.market_membership)?
    3. identity      -- is it a distinct property, or a second sighting of one
                        we already have?
    4. projection    -- emit a census row through the canonical constructors.

Nothing here fetches. It reads a persisted candidate file and a committed
market contract and returns a census plus a ledger; the ledger is the point,
because every candidate that does NOT become a census row has to say why.

How membership is decided
-------------------------
A bounding box is a query fence: it decides which provider calls to make. It is
a bad market boundary, because a name collision (there is a Belleville in
Illinois, in Kansas and in Michigan) and a provider's location bias both put
rows inside a box that no traveller would call this market. For a market whose
corridors were reviewed as a postal-code partition, the corridor registry is a
better boundary -- a candidate is in the market when a corridor claims its ZIP
-- and that remains the default.

It is not the only one, because it is not universally answerable.
PTF-GENERIC-CENSUS-MEMBERSHIP-HARDENING-001: a market may declare corridors
that classify by explicit hotel id or by city and claim no postal code at all,
and asking a ZIP-keyed registry about such a market can only ever answer 'no'.
So the basis is a field the market contract STATES
(``census_membership_basis``), the decision itself lives in
``discovery.market_membership``, and corridor assignment is a separate step
that runs afterwards and cannot evict a row. Every candidate that does not
become a census row is still recorded with a reason rather than dropped.

Why under-named candidates are reconciled here and not in the deduplicator
--------------------------------------------------------------------------
``discovery.deduplicate`` merges on provider id, normalised address, phone,
domain, or coordinates-plus-name-plus-address. Every one of those rules needs
an address or a phone, which OpenStreetMap frequently does not carry, and the
address it does carry is a bare street line with no city or state, which does
not normalise onto a fully-formed provider address. So one building arrives
twice: "Red Roof Inn" from the free provider and "Red Roof Inn St. Louis -
Westport" from the paid one, thirty metres apart.

That is not a deduplicator bug. Weakening the shared merge rules to join on
coordinates plus a fuzzy name would be wrong: two real hotels do sit 150m
apart, and those rules are load-bearing for every other discovery category.

It is, however, fatal if left alone, and the failure is silent in the worst
possible way. A bare brand name is a VALID identity key, so "Red Roof Inn",
"Comfort Inn" and "Drury Inn & Suites" each arrive as ONE key shared by three
or four different buildings. Deduplicating a census by identity key then
deletes real hotels -- which is exactly what the first run of this module did:
22 keys collided and 25 distinct properties, at 25 distinct street addresses,
were about to be reduced to 3.

So the reconciliation happens HERE, where it can be conservative and
reviewable. Candidate A is absorbed into candidate B when A's identity tokens
are a SUBSET of B's (an unqualified name is a prefix of a qualified one, never
the reverse) and the two sit within ``ABSORB_RADIUS_METERS``. Rank breaks ties
so the outcome does not depend on input order. Every absorption is written to
the ledger with both candidate ids and the measured distance; a candidate that
matches nothing survives on its own; and two survivors that STILL share an
identity key are a census-review finding, never a silent collapse.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import market_membership as MM
from scripts.pettripfinder.discovery.census_recandidacy import (is_prior_census_candidate)
from scripts.pettripfinder.markets.assignment import assign_hotels, assignment_basis
from scripts.pettripfinder.markets.contract import MarketConfig as ContractMarket

#: How close an address-less candidate must be to an addressed one before their
#: compatible names are allowed to mean "the same building". 250m is a city
#: block plus a parking lot: wide enough for a provider pin dropped on a hotel's
#: entrance versus its parcel centroid, narrow enough that two hotels on
#: opposite sides of an interchange stay separate.
ABSORB_RADIUS_METERS = 250.0

#: Provider category tokens that state the candidate is NOT lodging in our
#: current category. Bed-and-breakfasts and guest houses are on this list on
#: purpose: ``partition.STATE_MEANINGS[OUT_OF_CURRENT_CATEGORY]`` names them
#: explicitly as confirmed identities that are simply not what we publish.
NON_LODGING_CATEGORY_TOKENS = frozenset({
    "apartment_building", "apartment_complex", "bed_and_breakfast",
    "camping_cabin", "campground", "caravan_park", "condominium_complex",
    "cottage", "farmstay", "guest_house", "hostel", "housing_complex",
    "japanese_inn", "mobile_home_park", "real_estate_agency", "rv_park",
    "self_catering_accommodation",
})

#: Provider category tokens that affirm lodging in our current category.
LODGING_CATEGORY_TOKENS = frozenset({
    "hotel", "motel", "inn", "lodging", "extended_stay_hotel", "resort_hotel",
})

#: Name tokens that mean the row is a venue, an office or a service that merely
#: has a lodging word in its name. Checked only when no provider category
#: affirms lodging, so "Hotel Saint Louis" is never mistaken for a restaurant.
NON_LODGING_NAME_TOKENS = frozenset({
    "apartments", "banquet", "campground", "catering", "condominiums",
    "hostel", "realty", "rv", "spa", "storage", "timeshare",
})

# Ledger dispositions. Every discovery candidate gets exactly one.
ADMITTED = "ADMITTED_TO_CENSUS"
ABSORBED = "ABSORBED_INTO_ANOTHER_IDENTITY"
NOT_LODGING = "NOT_LODGING_CATEGORY"
OUT_OF_MARKET_GEOGRAPHY = "OUT_OF_MARKET_GEOGRAPHY"
OUT_OF_MARKET_BOUNDARY_DECISION = "OUT_OF_MARKET_BOUNDARY_DECISION"
PERMANENTLY_CLOSED = "PERMANENTLY_CLOSED"
UNNAMED = "UNNAMED_CANDIDATE"
IDENTITY_COLLISION = "IDENTITY_COLLISION_REQUIRES_REVIEW"
NO_LOCALITY = "IDENTITY_NO_LOCALITY"
#: PTF-GENERIC-CENSUS-MEMBERSHIP-HARDENING-001. The evidence cannot settle
#: whether this candidate is in the market. An honest hold: the alternative
#: was asserting it lay outside bounds nobody measured it against, which is
#: how a re-census evicted 103 committed identities.
MEMBERSHIP_UNRESOLVED = MM.UNRESOLVED

LEDGER_DISPOSITIONS: Tuple[str, ...] = (
    ADMITTED, ABSORBED, NOT_LODGING, OUT_OF_MARKET_GEOGRAPHY,
    OUT_OF_MARKET_BOUNDARY_DECISION, PERMANENTLY_CLOSED, UNNAMED,
    IDENTITY_COLLISION, NO_LOCALITY, MEMBERSHIP_UNRESOLVED,
)

_METERS_PER_DEGREE_LAT = 111_320.0


class CensusProjectionError(ValueError):
    """The candidate set does not support a deterministic census (fail closed)."""


# --------------------------------------------------------------------------- #
# Small pure helpers.
# --------------------------------------------------------------------------- #

def haversine_meters(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    """Great-circle distance. Equirectangular would be accurate enough at this
    radius, but distance is the evidence an absorption is recorded on, so it is
    computed properly rather than approximated."""
    phi_a, phi_b = math.radians(lat_a), math.radians(lat_b)
    d_phi = phi_b - phi_a
    d_lambda = math.radians(lng_b - lng_a)
    h = (math.sin(d_phi / 2) ** 2
         + math.cos(phi_a) * math.cos(phi_b) * math.sin(d_lambda / 2) ** 2)
    return 2 * 6_371_000.0 * math.asin(min(1.0, math.sqrt(h)))


def _tokens(name: str) -> Tuple[str, ...]:
    """Identity tokens, or ``()`` for a name that has none. The key contract
    refuses to mint an empty key -- correctly, because an empty key matches
    every other empty key -- so a nameless row is filtered upstream and this
    helper must not raise on the way there."""
    try:
        return tuple(t for t in ptf_identity_key(name).split() if t)
    except Exception:
        return ()


def absorption_direction(a_name: str, b_name: str) -> int:
    """``1`` when a is a strict abbreviation of b, ``-1`` for the reverse,
    ``0`` when the names are equal or unrelated.

    Token CONTAINMENT, not similarity. An unqualified brand name is a subset of
    its qualified form -- "red roof inn" of "red roof inn st louis westport" --
    and never the other way round. Both names must carry at least two tokens so
    a one-word row ("Motel", "Hotel") can never be absorbed into anything: it
    would match half the market.
    """
    a, b = set(_tokens(a_name)), set(_tokens(b_name))
    if len(a) < 2 or len(b) < 2 or a == b:
        return 0
    if a < b:
        return 1
    if b < a:
        return -1
    return 0


def names_equal_for_absorption(a_name: str, b_name: str) -> bool:
    """Two sightings spelled identically after normalisation. Absorbed by rank
    when they are close enough, because one building mapped twice is the
    commonest shape of an open-data duplicate."""
    a, b = set(_tokens(a_name)), set(_tokens(b_name))
    return len(a) >= 2 and a == b


def candidate_rank(candidate: Mapping) -> Tuple:
    """Which of two sightings of one building is the better identity.

    Deterministic and total: postal code first (it is what places a row in a
    corridor), then a street address, then an official URL, then the number of
    providers that saw it, then the number of identity tokens, then the
    candidate id. Sorts DESCENDING -- higher is better.
    """
    return (
        1 if (candidate.get("postal_code") or "").strip() else 0,
        1 if (candidate.get("address_line") or "").strip() else 0,
        1 if _official_url(candidate) else 0,
        len(_providers(candidate)),
        len(_tokens(candidate.get("name") or "")),
        candidate.get("candidate_id") or "",
    )


def _categories(candidate: Mapping) -> frozenset:
    """The provider's OWN category vocabulary for this candidate.

    ``category_candidates`` is deliberately NOT included. That field records
    which of OUR query categories returned the row, so on a lodging discovery
    run it reads {"hotel"} or {"hotel", "motel"} on literally every candidate --
    including the RV park and the wedding barn. Reading it here makes the
    non-lodging veto unreachable, which is exactly what it did on this module's
    first run: 565 candidates, 0 classified NOT_LODGING.
    """
    out = set()
    for record in candidate.get("source_records") or ():
        out |= set(record.get("provider_categories") or ())
    return frozenset(out)


def _business_statuses(candidate: Mapping) -> frozenset:
    return frozenset(
        (r.get("business_status") or "").strip().upper()
        for r in candidate.get("source_records") or ()
        if r.get("business_status"))


def classify_category(candidate: Mapping) -> Tuple[str, str]:
    """``(lodging_state, why)`` for one candidate. Pure and deterministic."""
    categories = _categories(candidate)
    non_lodging = sorted(categories & NON_LODGING_CATEGORY_TOKENS)
    affirms = sorted(categories & LODGING_CATEGORY_TOKENS)
    if non_lodging and not (categories & {"hotel", "motel", "extended_stay_hotel"}):
        return (enums.NOT_LODGING,
                "provider categories state a non-lodging accommodation type: %s"
                % ", ".join(non_lodging))
    if affirms:
        return (enums.LODGING_CONFIRMED,
                "provider categories affirm lodging: %s" % ", ".join(affirms))
    name_hits = sorted(set(_tokens(candidate.get("name") or "")) & NON_LODGING_NAME_TOKENS)
    if name_hits:
        return (enums.NOT_LODGING,
                "no provider category affirms lodging and the name states "
                "another business type: %s" % ", ".join(name_hits))
    return (enums.LODGING_BY_NAME,
            "no provider category affirms or denies lodging; the candidate was "
            "returned by a hotel/motel query and its name does not state "
            "another business type")


def _coords(candidate: Mapping) -> Tuple[Optional[float], Optional[float]]:
    lat, lng = candidate.get("latitude"), candidate.get("longitude")
    if lat is None or lng is None:
        return (None, None)
    return (float(lat), float(lng))


def _official_url(candidate: Mapping) -> str:
    if candidate.get("website_state") == C.WEBSITE_STATE_OFFICIAL_PRESENT:
        return candidate.get("website_url") or ""
    return ""


def _phone(candidate: Mapping) -> str:
    for record in candidate.get("source_records") or ():
        phone = "".join(ch for ch in (record.get("phone") or "") if ch.isdigit())
        if phone:
            return phone[-10:] if len(phone) > 10 else phone
    return ""


def _cells(candidate: Mapping) -> Tuple[str, ...]:
    out = set()
    for record in candidate.get("source_records") or ():
        for key, value in record.get("provenance") or ():
            if key == "cell_id" and value:
                out.add(value)
    return tuple(sorted(out))


def _providers(candidate: Mapping) -> Tuple[str, ...]:
    return tuple(sorted({r.get("provider", "") for r in candidate.get("source_records") or ()} - {""}))


def corridor_zips(market: ContractMarket) -> Dict[str, str]:
    """ZIP -> corridor_id over the whole registry. The market's boundary."""
    out: Dict[str, str] = {}
    for corridor in market.corridors:
        for code in corridor.included_postal_codes:
            out[code] = corridor.corridor_id
    return out


# --------------------------------------------------------------------------- #
# Projection.
# --------------------------------------------------------------------------- #

def _ledger_entry(candidate: Mapping, disposition: str, why: str,
                  **extra) -> "OrderedDict":
    entry = OrderedDict((
        ("candidate_id", candidate.get("candidate_id", "")),
        ("name", candidate.get("name", "")),
        ("address_line", candidate.get("address_line", "")),
        ("city", candidate.get("city", "")),
        ("state", candidate.get("state", "")),
        ("postal_code", candidate.get("postal_code", "")),
        ("providers", list(_providers(candidate))),
        ("cells", list(_cells(candidate))),
        ("disposition", disposition),
        ("why", why),
    ))
    for key in sorted(extra):
        entry[key] = extra[key]
    return entry


def project(candidates: Sequence[Mapping], market: ContractMarket, *,
            observed_at: str, work_order: str,
            in_bounds: Optional[Mapping[str, Optional[bool]]] = None,
            geography=None,
            ) -> Tuple[List[Dict], List[Dict]]:
    """``(census_rows, ledger)`` -- every candidate appears in the ledger once.

    ``geography`` is the committed discovery ``MarketConfig`` (bounds plus
    included municipalities). It is REQUIRED for a market whose contract
    declares MARKET_GEOGRAPHY membership and unused otherwise.

    ``in_bounds`` maps candidate_id -> whether the candidate's own coordinates
    fall inside the discovery bounding box. It separates two very different
    "not in a corridor" cases: a row 600 miles away that a name collision
    dragged in (OUT_OF_MARKET_GEOGRAPHY) from a row inside the metro that the
    corridor registry deliberately does not claim
    (OUT_OF_MARKET_BOUNDARY_DECISION). Omit it and everything unclaimed reads
    as a boundary decision, which is the safer of the two to have to review.

    Its values are THREE-valued: ``None`` means the candidate stated no
    coordinates, and that is not the same fact as coordinates measured outside
    the box. Reading a missing value as False is what let a re-census stamp
    "the candidate own coordinates fall outside the market geographic bounds"
    on 103 committed identities, none of which carries a coordinate at all.

    Order matters and is fixed: name, closure, category, ABSORPTION, then
    membership. Absorption runs before membership because the candidates that
    need absorbing are exactly the ones that cannot be tested for membership --
    an OpenStreetMap row with coordinates and no address has no postal code for
    a corridor to claim, so a membership-first pipeline discards the duplicate
    it was supposed to reconcile and calls it an out-of-market row.
    """
    zips = corridor_zips(market)
    ledger: List[Dict] = []

    ordered = sorted(candidates, key=lambda c: (c.get("candidate_id") or ""))

    # Pass 1 -- is this a nameable, open, in-category lodging candidate?
    kept: List[Tuple[Mapping, str, str]] = []
    for candidate in ordered:
        if not _tokens(candidate.get("name") or ""):
            # A row with no name that survives normalisation cannot be an
            # identity: ptf_identity_key refuses to mint an empty key, and an
            # empty key would match every other empty key.
            ledger.append(_ledger_entry(
                candidate, UNNAMED,
                "the candidate carries no name that yields an identity key"))
            continue
        if "CLOSED_PERMANENTLY" in _business_statuses(candidate):
            ledger.append(_ledger_entry(
                candidate, PERMANENTLY_CLOSED,
                "the provider reports the business permanently closed"))
            continue
        lodging_state, why = classify_category(candidate)
        if lodging_state == enums.NOT_LODGING:
            ledger.append(_ledger_entry(candidate, NOT_LODGING, why))
            continue
        kept.append((candidate, lodging_state, why))

    # Pass 2 -- absorb one building seen twice.
    #
    # Ranked first, so the decision never depends on input order, and so a
    # chain ("A into B into C") cannot form: only a candidate that is itself
    # unabsorbed may absorb another.
    ranked = sorted(kept, key=lambda k: candidate_rank(k[0]), reverse=True)
    absorbed_by: Dict[str, Tuple[Mapping, float]] = {}
    for index, (candidate, _state, _why) in enumerate(ranked):
        cid = candidate.get("candidate_id", "")
        if cid in absorbed_by:
            continue
        lat, lng = _coords(candidate)
        if lat is None:
            continue
        name = candidate.get("name") or ""
        for other, _s2, _w2 in ranked[index + 1:]:
            other_id = other.get("candidate_id", "")
            if other_id in absorbed_by:
                continue
            o_lat, o_lng = _coords(other)
            if o_lat is None:
                continue
            other_name = other.get("name") or ""
            # ``other`` ranks at or below ``candidate``, so absorption can only
            # run downward: either the lower-ranked name is a strict subset of
            # the higher-ranked one, or the two names are identical.
            if not (absorption_direction(other_name, name) == 1
                    or names_equal_for_absorption(other_name, name)):
                continue
            distance = haversine_meters(lat, lng, o_lat, o_lng)
            if distance > ABSORB_RADIUS_METERS:
                continue
            absorbed_by[other_id] = (candidate, distance)

    survivors: List[Tuple[Mapping, str, str]] = []
    for candidate, state, why in kept:
        cid = candidate.get("candidate_id", "")
        if cid not in absorbed_by:
            survivors.append((candidate, state, why))
            continue
        into, distance = absorbed_by[cid]
        ledger.append(_ledger_entry(
            candidate, ABSORBED,
            "one building seen twice: absorbed into a better-identified "
            "candidate %.0fm away whose name contains this one" % distance,
            absorbed_into_candidate_id=into.get("candidate_id", ""),
            absorbed_into_name=into.get("name", ""),
            distance_meters=round(distance, 1)))

    # Pass 3 -- membership, then rows.
    #
    # PTF-INDIANAPOLIS-HARDENED-RECENSUS-002: a corridor may name a hotel
    # EXPLICITLY (``explicit_hotel_ids``) precisely because its ZIP is shared
    # or unclaimed -- Indianapolis leaves 46202 to no corridor and places its
    # five hotels by name. Membership used to be decided by ZIP alone, so
    # every explicitly placed hotel was rejected as out of market, and the
    # coordinate-less ones were rejected with a reason about coordinates.
    explicit_corridor: Dict[str, str] = {}
    for contract_corridor in market.corridors:
        for explicit_key in contract_corridor.explicit_hotel_ids:
            explicit_corridor.setdefault(explicit_key, contract_corridor.corridor_id)
    admitted: List[Dict] = []
    for candidate, lodging_state, why in survivors:
        candidate_id = candidate.get("candidate_id", "")
        # Three-valued on purpose. ``None`` means the candidate stated no
        # coordinates, which is NOT the same as coordinates that were measured
        # and fell outside; see market_membership. A market with no committed
        # discovery geography supplies no map at all, and everything it holds
        # is treated as inside the box exactly as it was before.
        coords_in_bounds = True if in_bounds is None else in_bounds.get(candidate_id)
        # A candidate that states NO coordinates was never measured against
        # the box, so a verdict carried in ``in_bounds`` for it is not a
        # measurement and must not become an assertion that it fell outside.
        # Three-valued on purpose; see market_membership.
        if in_bounds is not None and _coords(candidate)[0] is None:
            coords_in_bounds = None
        zip5 = (candidate.get("postal_code") or "").strip()[:5]
        has_address = bool((candidate.get("address_line") or "").strip())

        outcome, membership_why, corridor = MM.decide(
            candidate, basis=market.census_membership_basis,
            corridor_of_zip=zips, coords_in_bounds=coords_in_bounds,
            geography=geography,
            is_prior_identity=is_prior_census_candidate(candidate))

        # PTF-INDIANAPOLIS-HARDENED-RECENSUS-002, preserved across this
        # commit's membership refactor. A corridor may name a hotel
        # EXPLICITLY (``explicit_hotel_ids``) precisely because its ZIP is
        # shared or unclaimed -- Indianapolis leaves 46202 to no corridor
        # and places its five hotels by name. An explicit naming is a
        # deliberate registry act, so it outranks the ZIP/bounds verdict
        # exactly as it did before membership moved into market_membership;
        # without this the five would return to OUT_OF_MARKET_BOUNDARY_DECISION.
        #
        # Scoped to CORRIDOR_REGISTRY markets on purpose. Where the registry IS
        # the boundary, naming a hotel speaks to membership AND to display, so
        # it settles both. Under MARKET_GEOGRAPHY the registry is only a display
        # taxonomy -- geography already decided membership -- so classification
        # stays where this commit put it, in assign_hotels.
        if (not corridor and explicit_corridor
                and market.census_membership_basis
                == MM.MC.MEMBERSHIP_CORRIDOR_REGISTRY):
            named_keys = [ptf_identity_key(candidate.get("name") or "")]
            named_keys += [ptf_identity_key(alias) for alias
                           in candidate.get("prior_census_identity_keys") or ()]
            explicit_hit = next((explicit_corridor[k] for k in named_keys
                                 if k in explicit_corridor), "")
            if explicit_hit:
                corridor = explicit_hit
                outcome = MM.IN_MARKET
                membership_why = ("named explicitly by corridor %r in the "
                                  "market registry" % corridor)

        if outcome == MM.OUT_OF_GEOGRAPHY:
            ledger.append(_ledger_entry(
                candidate, OUT_OF_MARKET_GEOGRAPHY, membership_why))
            continue
        if outcome == MM.BOUNDARY_DECISION:
            ledger.append(_ledger_entry(
                candidate, OUT_OF_MARKET_BOUNDARY_DECISION, membership_why))
            continue
        if outcome == MM.UNRESOLVED:
            ledger.append(_ledger_entry(
                candidate, MEMBERSHIP_UNRESOLVED, membership_why,
                latitude=candidate.get("latitude"),
                longitude=candidate.get("longitude"),
                city_seen=(candidate.get("city") or ""),
                state_seen=(candidate.get("state") or ""),
                postal_code_seen=zip5))
            continue

        if not corridor:
            # In the market, displayed by no corridor. The census contract
            # still requires a city and a state on every row, and an
            # OpenStreetMap node with a name and a coordinate has neither.
            # Held in the ledger with its coordinates rather than admitted as
            # a row that cannot say where it is.
            if not zip5 and not ((candidate.get("city") or "").strip()
                                 and (candidate.get("state") or "").strip()):
                ledger.append(_ledger_entry(
                    candidate, NO_LOCALITY,
                    "the candidate states no postal code, no city and no "
                    "state; a census row that cannot say where it is cannot "
                    "be assigned, joined or published. Its coordinates are "
                    "kept here for a reverse-geocode or a manual placement.",
                    latitude=candidate.get("latitude"),
                    longitude=candidate.get("longitude")))
                continue
            why = "%s; %s" % (why, membership_why)
        if not (candidate.get("city") or "").strip():
            # The census contract requires a city on every row, and a corridor's
            # display area is not one: it names a traveller area, not the
            # municipality a building stands in.
            ledger.append(_ledger_entry(
                candidate, NO_LOCALITY,
                "the candidate states no city; a census row that cannot name "
                "its municipality cannot be joined or published, and a "
                "corridor display area is not a municipality",
                latitude=candidate.get("latitude"),
                longitude=candidate.get("longitude"),
                postal_code_seen=zip5))
            continue
        name = (candidate.get("name") or "").strip()
        identity_state = (enums.IDENTITY_CONFIRMED if has_address and zip5
                          else enums.IDENTITY_UNRESOLVED)
        admitted.append(OrderedDict((
            ("identity_key", ptf_identity_key(name)),
            ("canonical_name", name),
            ("candidate", candidate),
            ("lodging_state", lodging_state),
            ("lodging_why", why),
            ("identity_state", identity_state),
            ("corridor", corridor),
        )))

    for row in admitted:
        ledger.append(_ledger_entry(
            row["candidate"], ADMITTED, row["lodging_why"],
            identity_key=row["identity_key"],
            corridor=row["corridor"],
            identity_state=row["identity_state"]))

    return (admitted, ledger)


def resolve_identity_key_collisions(admitted: Sequence[Mapping]
                                    ) -> Tuple[List[Dict], List[Dict]]:
    """``(unique_rows, collisions)`` for candidates that STILL share a key.

    Two survivors sharing an identity key have already refused to absorb into
    each other -- they are too far apart, or one name is not contained in the
    other -- so the key is doing something the key contract cannot do: naming
    two buildings. "Comfort Inn" at 8 Commerce Drive, Collinsville and "Comfort
    Inn" at 12031 Lackland Road, Maryland Heights are both real, both correct,
    and both spelled the same.

    A census cannot hold two rows with one key, so the best-ranked survivor
    keeps it and the rest are HELD for review with their addresses intact. That
    is a market whose census says "three buildings here need names", which a
    human can fix in one sitting -- as against a census that quietly published
    one of them and forgot the other two.
    """
    groups: Dict[str, List[Mapping]] = {}
    for row in admitted:
        groups.setdefault(row["identity_key"], []).append(row)
    unique: List[Dict] = []
    collisions: List[Dict] = []
    for key in sorted(groups):
        rows = groups[key]
        if len(rows) == 1:
            unique.append(dict(rows[0]))
            continue
        ordered = sorted(rows, key=lambda r: candidate_rank(r["candidate"]), reverse=True)
        unique.append(dict(ordered[0]))
        collisions.append(OrderedDict((
            ("identity_key", key),
            ("kept_candidate_id", ordered[0]["candidate"].get("candidate_id", "")),
            ("kept_address", ordered[0]["candidate"].get("address_line", "")),
            ("held_for_review", [OrderedDict((
                ("candidate_id", r["candidate"].get("candidate_id", "")),
                ("name", r["candidate"].get("name", "")),
                ("address_line", r["candidate"].get("address_line", "")),
                ("city", r["candidate"].get("city", "")),
                ("state", r["candidate"].get("state", "")),
                ("postal_code", r["candidate"].get("postal_code", "")),
                ("latitude", r["candidate"].get("latitude")),
                ("longitude", r["candidate"].get("longitude")),
                ("providers", list(_providers(r["candidate"]))),
            )) for r in ordered[1:]]),
        )))
    return (unique, collisions)


#: A token carried by more than this share of a market's names is not an
#: identity signal. Measured, not guessed: at 5% over the 375-row St. Louis
#: census this removes exactly the words the market is made of -- st, louis,
#: inn, suites, hotel, by, wyndham -- and keeps Ritz-Carlton, Travelodge and
#: Wingate.
DISTINCTIVE_TOKEN_MAX_SHARE = 0.05


def distinctive_tokens(rows: Sequence[Mapping], *,
                       max_share: float = DISTINCTIVE_TOKEN_MAX_SHARE) -> frozenset:
    """Tokens rare enough in this corpus to say WHICH building a row is."""
    counts: Dict[str, int] = {}
    total = 0
    for row in rows:
        total += 1
        for token in set(_tokens(row.get("canonical_name") or "")):
            counts[token] = counts.get(token, 0) + 1
    if not total:
        return frozenset()
    ceiling = max(1, int(total * max_share))
    return frozenset(t for t, n in counts.items() if n <= ceiling)


def suspected_duplicates(rows: Sequence[Mapping], *,
                         radius_meters: float = ABSORB_RADIUS_METERS,
                         min_shared_tokens: int = 2) -> List[Dict]:
    """Census rows that look like one building under two names.

    Reported, never merged. Absorption requires token CONTAINMENT, and two real
    names for one hotel often share most tokens without either containing the
    other -- "The Ritz-Carlton, St. Louis" and "Ritz-Carlton Hotel St. Louis".
    Loosening containment to a share threshold would merge "Hampton Inn" into
    "Hampton Inn & Suites" across a car park, which is two hotels, so the rule
    stays strict and the leftovers become a review list.

    The agreement has to be on DISTINCTIVE tokens. Two hotels 90m apart in this
    market share "st", "louis", "inn" and "suites" and are still two hotels; a
    rule that counted those reported a third of the market as duplicates.
    """
    out: List[Dict] = []
    ordered = sorted(rows, key=lambda r: r.get("identity_key", ""))
    distinctive = distinctive_tokens(ordered)
    for i, left in enumerate(ordered):
        lat_a, lng_a = left.get("latitude"), left.get("longitude")
        if lat_a is None or lng_a is None:
            continue
        left_tokens = set(_tokens(left.get("canonical_name") or "")) & distinctive
        if len(left_tokens) < min_shared_tokens:
            continue
        for right in ordered[i + 1:]:
            lat_b, lng_b = right.get("latitude"), right.get("longitude")
            if lat_b is None or lng_b is None:
                continue
            shared = left_tokens & set(_tokens(right.get("canonical_name") or ""))
            if len(shared) < min_shared_tokens:
                continue
            distance = haversine_meters(float(lat_a), float(lng_a),
                                        float(lat_b), float(lng_b))
            if distance > radius_meters:
                continue
            out.append(OrderedDict((
                ("identity_key_a", left.get("identity_key", "")),
                ("identity_key_b", right.get("identity_key", "")),
                ("name_a", left.get("canonical_name", "")),
                ("name_b", right.get("canonical_name", "")),
                ("address_a", left.get("address", "")),
                ("address_b", right.get("address", "")),
                ("shared_distinctive_tokens", sorted(shared)),
                ("distance_meters", round(distance, 1)),
                ("why", "two census rows within %.0fm agreeing on %d "
                        "distinctive identity tokens; neither name contains "
                        "the other, so the absorption rule left both standing"
                        % (radius_meters, len(shared))),
            )))
    return out


#: Kept so a caller written against the first draft of this module still runs.
collapse_duplicate_keys = resolve_identity_key_collisions


def assign_corridors(rows: Sequence[Mapping], market: ContractMarket) -> Dict[str, Tuple[str, str, str]]:
    """identity_key -> (corridor_id, basis, value), via the ONE assignment
    authority. Never re-implements the tier order."""
    hotel_rows = [{
        "name": r["canonical_name"],
        "city": r["candidate"].get("city", ""),
        "state": r["candidate"].get("state", ""),
        "postal_code": r["candidate"].get("postal_code", ""),
        "identity_key": r["identity_key"],
    } for r in rows]
    assignment = assign_hotels(market, hotel_rows, fail_closed=False)
    from scripts.pettripfinder.site_data import normalize_name
    out: Dict[str, Tuple[str, str, str]] = {}
    for row in rows:
        key = normalize_name(row["canonical_name"])
        corridors = assignment.corridor_of.get(key, ())
        basis, value = assignment_basis(assignment, key)
        out[row["identity_key"]] = (corridors[0] if corridors else "", basis, value)
    return out

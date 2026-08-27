"""PTF-GENERIC-CENSUS-MEMBERSHIP-HARDENING-001 -- does this candidate belong
to this market?

The gap this closes
-------------------
``census_projection`` used to answer market membership with one line::

    corridor = corridor_zips(market).get(zip5, "")

which made the corridor ZIP registry both the market's boundary AND its
display taxonomy. For the nine markets whose corridors were reviewed as a
postal-code partition that is correct and stays correct. For a market whose
corridors classify by ``explicit_hotel_ids`` (Grand Rapids-Holland: 119 ids, 0
postal codes) or by city (Detroit-Ann Arbor: 22 cities, 0 postal codes), the
ZIP map is EMPTY, so the test could only ever answer "no" -- and a re-census
of Grand Rapids-Holland projected 120 committed identities plus 113 fresh
discovery candidates down to FOUR rows. The four that survived were not
selected; they were the residue that happened to carry no postal code and so
fell past the branch that rejects one.

Two separable questions
-----------------------
1. MEMBERSHIP -- is this property in the market at all? Decided here, from the
   market's own geography or from its corridor registry, per the basis the
   market contract DECLARES (``census_membership_basis``).
2. CLASSIFICATION -- which corridor should display it? Decided afterwards by
   ``markets.assignment.assign_hotels``, the one assignment authority, which
   already understands explicit ids, cities and ZIPs in a reviewed tier order.

A property that is in the market but that no corridor claims is a normal
outcome: it is a census row with no corridor, not a rejection. Membership is
never revoked for want of a display area.

Missing evidence is not contrary evidence
-----------------------------------------
The rule this module exists to enforce: a candidate that states no coordinates
has not been shown to be outside the bounds. All 120 committed Grand
Rapids-Holland census rows carry ``latitude: null``, and the old code read that
absence as ``in_bounds -> False`` and wrote "the candidate own coordinates fall
outside the market geographic bounds" into the ledger for every one of them --
an assertion about coordinates that do not exist. Where the evidence cannot
settle the question, the honest disposition is UNRESOLVED, which a human
reviews, and never OUT_OF_MARKET_GEOGRAPHY, which a human trusts.
"""

from __future__ import annotations

from typing import Mapping, Optional, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.lodging_scope import classify_scope_fields
from scripts.pettripfinder.markets import contract as MC

#: The candidate belongs to this market.
IN_MARKET = "IN_MARKET"
#: Affirmative evidence places the candidate outside the market: its own
#: coordinates fall outside the bounds, or it states a locality the market
#: excludes. Never returned on absent evidence.
OUT_OF_GEOGRAPHY = "OUT_OF_MARKET_GEOGRAPHY"
#: Inside the discovery box, but the corridor registry -- which for this market
#: IS the boundary -- deliberately claims no corridor for its postal code.
BOUNDARY_DECISION = "OUT_OF_MARKET_BOUNDARY_DECISION"
#: The available evidence cannot settle membership either way. A hold for
#: review, carrying whatever geography the candidate did state.
UNRESOLVED = "MARKET_MEMBERSHIP_UNRESOLVED"


def _text(candidate: Mapping, key: str) -> str:
    return (candidate.get(key) or "").strip()


def decide_by_corridor_registry(candidate: Mapping, *,
                                corridor_of_zip: Mapping[str, str],
                                coords_in_bounds: Optional[bool],
                                ) -> Tuple[str, str, str]:
    """``(outcome, why, corridor_id)`` for a CORRIDOR_REGISTRY market.

    Preserved exactly as it behaved before this module existed, with one
    correction that applies to every basis: ``coords_in_bounds`` is now
    three-valued, so a candidate that states NO coordinates is UNRESOLVED
    rather than asserted to be outside the bounds it was never measured
    against.
    """
    zip5 = _text(candidate, "postal_code")[:5]
    corridor = corridor_of_zip.get(zip5, "")
    if corridor:
        return (IN_MARKET, "postal code %r is claimed by corridor %r"
                % (zip5, corridor), corridor)
    if coords_in_bounds is False:
        return (OUT_OF_GEOGRAPHY,
                "the candidate own coordinates fall outside the market "
                "geographic bounds (postal code %r)" % zip5, "")
    if coords_in_bounds is None and not zip5:
        return (UNRESOLVED,
                "the candidate states neither coordinates nor a postal code, "
                "so the corridor registry cannot be asked whether this market "
                "claims it", "")
    if zip5:
        if coords_in_bounds is None:
            # Inside no box we ever measured. Saying the coordinates fell
            # outside would be a claim about a measurement that never
            # happened, so the reason says what is actually true.
            return (BOUNDARY_DECISION,
                    "postal code %r is claimed by no corridor in the market "
                    "registry and no corridor names this hotel explicitly; the "
                    "candidate carries no coordinates, so the bounding box "
                    "cannot place it either" % zip5, "")
        return (BOUNDARY_DECISION,
                "postal code %r is inside the discovery bounding box and is "
                "claimed by no corridor in the market registry" % zip5, "")
    # Inside the box, no postal code. Admitted with no corridor; the caller
    # still requires a city before it will emit a census row.
    return (IN_MARKET,
            "admitted with no corridor because the candidate states no "
            "postal code", "")


def decide_by_market_geography(candidate: Mapping, *, geography,
                               is_prior_identity: bool = False,
                               ) -> Tuple[str, str, str]:
    """``(outcome, why, corridor_id)`` for a MARKET_GEOGRAPHY market.

    ``geography`` is the committed discovery ``MarketConfig`` -- bounds plus
    ``included_municipalities``. Corridors are not consulted: this basis exists
    precisely for markets whose corridors cannot answer the question.

    ``is_prior_identity`` marks a row recandidated out of the market's own
    committed census. Such a row was admitted once already, by a reviewed
    build, so absent geography must not evict it: prior census continuity is
    evidence, and the only thing that overrides it is AFFIRMATIVE evidence
    that the property is outside.
    """
    scope = classify_scope_fields(
        city=candidate.get("city"), state=candidate.get("state"),
        latitude=candidate.get("latitude"), longitude=candidate.get("longitude"),
        market=geography)

    if scope == C.SCOPE_IN_SCOPE:
        return (IN_MARKET,
                "the candidate own geography places it in the market "
                "(municipality or coordinates inside the market bounds)", "")
    if scope == C.SCOPE_OUT_OF_SCOPE:
        # The one path that rejects, and it is reached only on evidence the
        # candidate itself supplied: coordinates measured outside the bounds
        # and their borderline buffer, or a stated locality in another state.
        return (OUT_OF_GEOGRAPHY,
                "the candidate own stated geography places it outside the "
                "market (city %r, state %r)"
                % (_text(candidate, "city"), _text(candidate, "state")), "")
    if is_prior_identity:
        return (IN_MARKET,
                "carried forward: this identity is already in the market's "
                "committed census and its recandidated row states no geography "
                "that contradicts that (scope %s)" % scope, "")
    return (UNRESOLVED,
            "the candidate geography cannot settle market membership either "
            "way (scope %s); held for review rather than asserted to be "
            "outside bounds it was never measured against" % scope, "")


def decide(candidate: Mapping, *, basis: str,
           corridor_of_zip: Mapping[str, str],
           coords_in_bounds: Optional[bool],
           geography=None,
           is_prior_identity: bool = False) -> Tuple[str, str, str]:
    """``(outcome, why, corridor_id)``. The single membership entry point.

    ``basis`` comes from the market contract and is never inferred from the
    shape of the corridor registry.
    """
    if basis == MC.MEMBERSHIP_MARKET_GEOGRAPHY:
        if geography is None:
            # Fail closed and loudly. Silently falling back to the corridor
            # registry would empty the census of exactly the markets this
            # basis was added for.
            raise ValueError(
                "census_membership_basis is %s but no discovery market "
                "geography was supplied to decide membership"
                % MC.MEMBERSHIP_MARKET_GEOGRAPHY)
        return decide_by_market_geography(
            candidate, geography=geography, is_prior_identity=is_prior_identity)
    if basis == MC.MEMBERSHIP_CORRIDOR_REGISTRY:
        return decide_by_corridor_registry(
            candidate, corridor_of_zip=corridor_of_zip,
            coords_in_bounds=coords_in_bounds)
    raise ValueError("unknown census_membership_basis %r" % basis)

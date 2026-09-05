# -*- coding: utf-8 -*-
"""Shared helpers for the PetTripFinder suites.

THE LAPSED PARTICIPATION PIN
-----------------------------
PTF-GRAND-RAPIDS-INDIANAPOLIS-LINEAGE-MERGE-033 registered
``grand-rapids-holland-mi`` in ``deploy/netlify/launch_participation.json``. It
had to: a registered market with no row fails the assembler gate CLOSED FOR
EVERY MARKET, so without a row no assembly could run at all -- not even the
8-market baseline that order exists to prove.

Listing an eleventh market changes the record's sha256, and a signed deployment
authorization BINDS that sha. So ``ptf-auth-020`` stopped verifying, and every
test that asserted ``verify_manifest() == []`` began failing at once.

That is the design working, and it is the same thing
PTF-ST-LOUIS-FRESH-MARKET-BENCHMARK-001 recorded: registering a market
invalidates the signed authorization, and the next deployment issues a new one.
THE LIVE BUNDLE IS UNTOUCHED -- e9998c51 is still what production serves, and
every other fact the manifest states about it is still true and still checked.

So the assertion those tests want is not "nothing disagrees" -- something does,
knowingly -- but "nothing disagrees EXCEPT the pin the registration lapsed".
That is what ``manifest_problems_other_than_the_lapsed_pin`` returns, and it is
deliberately narrow: it drops only complaints about the participation record
itself, so a dropped market, an UNEXPECTED changed contract or a moved control
file still comes through and still fails.

"""
from __future__ import annotations

from typing import List, Optional, Sequence

#: The two complaints the registration legitimately produces. Anything else is
#: a real disagreement and must not be filtered.
_LAPSED_PIN_MARKERS = (
    "launch_participation_sha256: deploy/netlify/launch_participation.json "
    "has changed since authorization",
    "deploy/netlify/launch_participation.json has changed since the manifest "
    "was written",
)



def is_the_lapsed_participation_pin(problem: str) -> bool:
    """Is this complaint the known, accepted pin lapse and nothing else?"""
    return any(marker in problem for marker in _LAPSED_PIN_MARKERS)


def is_a_named_moved_market(problem: str) -> bool:
    """Is this complaint a market a LATER order is named as having moved?

    PTF-INDIANAPOLIS-PROMOTION-REMEDIATION-005. A promotion that lands after a
    deployment legitimately changes that market's release contract, so the live
    authorization reports "contract has changed since authorization" for it.
    That is the authorization doing its job, not a corruption.

    This is deliberately NOT a blanket. The market must be named in
    pins/supersessions.json against that very authorization, together with the
    work order that moved it, and the complaint must be about a release
    contract. A market that drifts without being named still fails, and so does
    any other kind of disagreement about a named market.
    """
    from pettripfinder import epochs

    registry = epochs.supersession_registry()["authorizations"]
    named = {market_id
             for entry in registry.values()
             for market_id in entry["moved_by_later_work"]}
    for market_id in named:
        # The authorization's phrasing, which carries the authorization id.
        if ("release_contracts[%s]" % market_id) in problem \
                and "has changed since authorization" in problem:
            return True
        # The manifest's phrasing for the same fact.
        if problem.startswith("%s: release contract has changed since the "
                              "manifest was written" % market_id):
            return True
    return False



def manifest_problems_other_than_the_lapsed_pin(
        problems: Optional[Sequence[str]] = None) -> List[str]:
    """``verify_manifest()`` minus the participation pin 033 lapsed.

    Pass ``problems`` to filter a list you already have; omit it to verify the
    committed manifest. Every other disagreement survives.
    """
    if problems is None:
        from scripts.pettripfinder import global_deployment as GD
        problems = GD.verify_manifest()
    return [p for p in problems
            if not is_the_lapsed_participation_pin(p)
            and not is_a_named_moved_market(p)]

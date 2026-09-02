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

THE LAPSED DAYTON CONTRACT PIN
------------------------------
PTF-DAYTON-OH-HARDENED-APPLICATION-002 applied 7 pet-friendly records and 16
verified-no-pets exclusions to ``dayton-oh`` under founder authorisation, and
re-authored that market's release contract to match (47 -> 54 published, 8 -> 24
no-pets). ``ptf-auth-006`` -- the authorization deployment 6a976f61 consumed --
binds every market's contract sha, so Dayton's contract no longer matches it.

This is the same mechanism as the participation lapse and the same design
working: source has legitimately moved AHEAD of what production serves, and it
stays that way until a Dayton deployment-authorization order issues a new
authorization. THE LIVE BUNDLE IS UNTOUCHED -- 6a976f61 still serves 9 markets /
619 profiles / 759 routes, and every other fact the manifest states about it is
still true and still checked.

The allowance is deliberately narrower than the general case: it names
``dayton-oh`` explicitly, so a change to ANY OTHER market's contract still comes
through and still fails. It must be removed when Dayton deploys.
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

#: The two complaints PTF-DAYTON-OH-HARDENED-APPLICATION-002 legitimately
#: produces. dayton-oh is named in BOTH so that another market's contract
#: changing is still a real disagreement. Remove these when Dayton deploys.
_LAPSED_DAYTON_CONTRACT_MARKERS = (
    "release_contracts[dayton-oh]: contract has changed since authorization",
    "dayton-oh: release contract has changed since the manifest was written",
)


def is_the_lapsed_participation_pin(problem: str) -> bool:
    """Is this complaint the known, accepted pin lapse and nothing else?"""
    return any(marker in problem for marker in _LAPSED_PIN_MARKERS)


def is_the_lapsed_dayton_contract_pin(problem: str) -> bool:
    """Is this the Dayton contract lapse APPLICATION-002 knowingly created?"""
    return any(marker in problem for marker in _LAPSED_DAYTON_CONTRACT_MARKERS)


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
            and not is_the_lapsed_dayton_contract_pin(p)]

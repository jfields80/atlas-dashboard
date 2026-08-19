"""Why an acquisition stopped, and whether trying elsewhere could help.

THE DISTINCTION THIS FILE EXISTS FOR
------------------------------------
A better crawler cannot fix an ambiguous source. That one sentence is the whole
design: failures split into those a DIFFERENT PROVIDER might survive, and those
where the surface already answered and the answer was unusable.

Sending a contradictory page to a second provider buys the same contradiction
twice. Sending a refused page to a second provider is exactly how Choice went
from 0/5 to 5/5. Collapsing the two into "failed" is what makes a router
expensive and dishonest at the same time.

So :data:`ESCALATING` is a closed set, and everything outside it stops the
ladder. ``POLICY_NOT_FOUND`` sits outside it deliberately: the page rendered,
the identity matched, and it said nothing about pets. That is a FINDING about
the property, and re-fetching it through a costlier lane will find the same
nothing.

RELATIONSHIP TO THE CAPTURE VOCABULARY
--------------------------------------
``brightdata.outcomes`` holds nine per-attempt outcomes and is unchanged --
committed pilot reports are keyed to it. This vocabulary is wider because a
router sees things one attempt cannot: a provider that is not configured, a
budget that ran out, a source whose words the schema cannot hold.
:func:`from_capture_outcome` is the one translation point between them.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, FrozenSet, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import outcomes as CAPTURE  # noqa: E402

# --------------------------------------------------------------------------- #
# Technical -- the page never arrived, or arrived as something else.
# --------------------------------------------------------------------------- #

ACCESS_DENIED = "ACCESS_DENIED"
BLANK_PAGE = "BLANK_PAGE"
UNHYDRATED = "UNHYDRATED"
NAVIGATION_FAILED = "NAVIGATION_FAILED"
CAPTURE_FAILED = "CAPTURE_FAILED"
UNEXPECTED_PAGE = "UNEXPECTED_PAGE"
GEO_MISMATCH = "GEO_MISMATCH"
PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
TIMEOUT = "TIMEOUT"

TECHNICAL: Tuple[str, ...] = (
    ACCESS_DENIED, BLANK_PAGE, UNHYDRATED, NAVIGATION_FAILED, CAPTURE_FAILED,
    UNEXPECTED_PAGE, GEO_MISMATCH, PROVIDER_UNAVAILABLE, TIMEOUT,
)

# --------------------------------------------------------------------------- #
# Identity -- a page arrived and it is not demonstrably this property.
# --------------------------------------------------------------------------- #

IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
IDENTITY_UNCERTAIN = "IDENTITY_UNCERTAIN"

IDENTITY: Tuple[str, ...] = (IDENTITY_MISMATCH, IDENTITY_UNCERTAIN)

# --------------------------------------------------------------------------- #
# Policy -- the right page, with no usable policy surface on it.
# --------------------------------------------------------------------------- #

POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
POLICY_SURFACE_INCOMPLETE = "POLICY_SURFACE_INCOMPLETE"

POLICY: Tuple[str, ...] = (POLICY_NOT_FOUND, POLICY_SURFACE_INCOMPLETE)

# --------------------------------------------------------------------------- #
# Source -- the property said something we may not publish.
# --------------------------------------------------------------------------- #

SOURCE_AMBIGUOUS = "SOURCE_AMBIGUOUS"
SOURCE_CONTRADICTORY = "SOURCE_CONTRADICTORY"
UNSUPPORTED_DURATION = "UNSUPPORTED_DURATION"
UNSUPPORTED_SCHEMA_SHAPE = "UNSUPPORTED_SCHEMA_SHAPE"

SOURCE: Tuple[str, ...] = (SOURCE_AMBIGUOUS, SOURCE_CONTRADICTORY,
                           UNSUPPORTED_DURATION, UNSUPPORTED_SCHEMA_SHAPE)

# --------------------------------------------------------------------------- #
# Budget -- we stopped ourselves.
# --------------------------------------------------------------------------- #

BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
ATTEMPTS_EXHAUSTED = "ATTEMPTS_EXHAUSTED"

BUDGET: Tuple[str, ...] = (BUDGET_EXHAUSTED, ATTEMPTS_EXHAUSTED)

FAILURES: Tuple[str, ...] = TECHNICAL + IDENTITY + POLICY + SOURCE + BUDGET

CLASSES: Dict[str, Tuple[str, ...]] = {
    "TECHNICAL": TECHNICAL, "IDENTITY": IDENTITY, "POLICY": POLICY,
    "SOURCE": SOURCE, "BUDGET": BUDGET,
}

#: Failures a DIFFERENT PROVIDER might survive. Nothing else escalates.
#:
#: Every member is a statement about the CHANNEL: a refusal, an interstitial, a
#: shell, a redirect, a provider that is not configured. Identity, policy and
#: source failures are statements about the PAGE, and the page does not change
#: because the fetch did.
#:
#: ``IDENTITY_UNCERTAIN`` is the one borderline member and it escalates on
#: purpose: "we could not read enough of this page to bind it" is a property of
#: what arrived, and a fuller render can settle it. ``IDENTITY_MISMATCH`` --
#: "this is a different hotel" -- never escalates, because it will be a
#: different hotel through every provider.
ESCALATING: FrozenSet[str] = frozenset({
    ACCESS_DENIED, BLANK_PAGE, UNHYDRATED, NAVIGATION_FAILED, CAPTURE_FAILED,
    UNEXPECTED_PAGE, GEO_MISMATCH, PROVIDER_UNAVAILABLE, TIMEOUT,
    IDENTITY_UNCERTAIN,
})

#: Failures where escalation is waste. Named as its own set so the reason is
#: readable at the call site rather than inferred from a negation.
TERMINAL: FrozenSet[str] = frozenset(FAILURES) - ESCALATING

#: Per-attempt capture outcome -> router failure. The only translation point
#: between the frozen nine and this wider vocabulary.
_FROM_CAPTURE: Dict[str, str] = {
    CAPTURE.ACCESS_DENIED: ACCESS_DENIED,
    CAPTURE.BLANK_PAGE: BLANK_PAGE,
    CAPTURE.UNHYDRATED: UNHYDRATED,
    CAPTURE.NAVIGATION_FAILED: NAVIGATION_FAILED,
    CAPTURE.CAPTURE_FAILED: CAPTURE_FAILED,
    CAPTURE.UNEXPECTED_PAGE: UNEXPECTED_PAGE,
    CAPTURE.IDENTITY_MISMATCH: IDENTITY_MISMATCH,
    CAPTURE.POLICY_NOT_FOUND: POLICY_NOT_FOUND,
}

#: Withholding reasons the reader emits -> the source failure they represent.
#: A record whose every publishable field was withheld is not a record that
#: failed to load; it is a record whose SOURCE could not be published, and the
#: router must not answer it with another fetch.
_FROM_WITHHOLDING: Dict[str, str] = {
    "SOURCE_AMBIGUOUS": SOURCE_AMBIGUOUS,
    "SOURCE_CONTRADICTORY": SOURCE_CONTRADICTORY,
    "SCHEMA_CANNOT_REPRESENT": UNSUPPORTED_SCHEMA_SHAPE,
}


def is_failure(value: str) -> bool:
    return value in FAILURES


def classify(failure: str) -> str:
    """Which family a failure belongs to, for reporting."""
    for name, members in CLASSES.items():
        if failure in members:
            return name
    return "UNKNOWN"


def may_escalate(failure: str) -> bool:
    """Whether trying a different provider could plausibly change the answer.

        >>> may_escalate("ACCESS_DENIED")
        True
        >>> may_escalate("SOURCE_CONTRADICTORY")
        False
        >>> may_escalate("POLICY_NOT_FOUND")
        False
    """
    return failure in ESCALATING


def from_capture_outcome(outcome: str) -> str:
    """Translate a per-attempt capture outcome into a router failure."""
    if outcome == CAPTURE.VALID:
        raise ValueError("VALID is not a failure; the router handles success "
                         "on its own path")
    try:
        return _FROM_CAPTURE[outcome]
    except KeyError:
        raise ValueError("unknown capture outcome %r; the capture vocabulary "
                         "is closed and this one is not in it" % (outcome,))


def from_withholding(reason: str) -> str:
    """Translate a reader withholding reason into a source failure, or ""."""
    return _FROM_WITHHOLDING.get(reason, "")


__all__ = [
    "ACCESS_DENIED", "BLANK_PAGE", "UNHYDRATED", "NAVIGATION_FAILED",
    "CAPTURE_FAILED", "UNEXPECTED_PAGE", "GEO_MISMATCH", "PROVIDER_UNAVAILABLE",
    "TIMEOUT", "IDENTITY_MISMATCH", "IDENTITY_UNCERTAIN", "POLICY_NOT_FOUND",
    "POLICY_SURFACE_INCOMPLETE", "SOURCE_AMBIGUOUS", "SOURCE_CONTRADICTORY",
    "UNSUPPORTED_DURATION", "UNSUPPORTED_SCHEMA_SHAPE", "BUDGET_EXHAUSTED",
    "ATTEMPTS_EXHAUSTED", "TECHNICAL", "IDENTITY", "POLICY", "SOURCE", "BUDGET",
    "FAILURES", "CLASSES", "ESCALATING", "TERMINAL", "is_failure", "classify",
    "may_escalate", "from_capture_outcome", "from_withholding",
]

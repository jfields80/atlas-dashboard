"""How one Bright Data attempt is allowed to end. Closed vocabulary.

Nine outcomes, exactly one per attempt. The set is closed for the same reason
``contracts/enums`` is closed: four markets independently invented six spellings
of one concept and a system that never checked accepted all of them.

The distinction this vocabulary exists to protect is the one the capture worker
already refuses to blur -- ``POLICY_NOT_FOUND`` (the page rendered and said
nothing about pets) is a FINDING, while ``ACCESS_DENIED`` (the page pushed
back) is a TO-DO. Collapsing them into "failed" would let a blocked property
look like a property with no pet policy.

Exactly one outcome is VALID. The other eight are failure or hold states and
NONE of them may become evidence, a publication candidate, or a
verified-no-pets candidate. That rule is enforced in code by
:data:`EVIDENCE_BEARING_OUTCOMES` being a one-member set rather than by
remembering.
"""

from __future__ import annotations

from typing import FrozenSet, Tuple

#: The page rendered, is the property we asked for, and carries a located
#: pet-policy surface. The only outcome that may produce evidence.
VALID = "VALID"

#: The origin or an intermediary refused us: 403, bot challenge, interstitial.
ACCESS_DENIED = "ACCESS_DENIED"

#: No title and no meaningful body. The session produced nothing at all.
BLANK_PAGE = "BLANK_PAGE"

#: An identity shell arrived -- correct title, correct URL -- with a body that
#: never hydrated. Observed repeatedly against Marriott during the single-page
#: proof, which is why it is its own outcome and not folded into BLANK_PAGE.
UNHYDRATED = "UNHYDRATED"

#: The page hydrated and is a property page, but not THIS property.
IDENTITY_MISMATCH = "IDENTITY_MISMATCH"

#: The right property, fully rendered, with no pet-policy surface on it.
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"

#: The session or the navigation itself failed: connect error, timeout, crash.
NAVIGATION_FAILED = "NAVIGATION_FAILED"

#: The page was fine and persisting the artifacts was not.
CAPTURE_FAILED = "CAPTURE_FAILED"

#: We landed somewhere else entirely -- a brand landing page, a search results
#: page, a redirect off the first-party domain.
UNEXPECTED_PAGE = "UNEXPECTED_PAGE"

OUTCOMES: Tuple[str, ...] = (
    VALID, ACCESS_DENIED, BLANK_PAGE, UNHYDRATED, IDENTITY_MISMATCH,
    POLICY_NOT_FOUND, NAVIGATION_FAILED, CAPTURE_FAILED, UNEXPECTED_PAGE,
)

#: The outcomes from which evidence may be built. Deliberately one member.
EVIDENCE_BEARING_OUTCOMES: FrozenSet[str] = frozenset({VALID})

#: Outcomes that mean the surface pushed back rather than answered. These map
#: to ``readiness.SOURCE_BLOCKED`` downstream, never to "no policy".
BLOCKED_OUTCOMES: FrozenSet[str] = frozenset({
    ACCESS_DENIED, BLANK_PAGE, UNHYDRATED, NAVIGATION_FAILED, UNEXPECTED_PAGE,
})

#: Outcomes that mean the surface answered and the answer was "nothing here".
EXHAUSTED_OUTCOMES: FrozenSet[str] = frozenset({POLICY_NOT_FOUND})

#: Where each outcome lands in the existing ladder-transcript vocabulary
#: (``policy/evidence_bundle.LADDER_OUTCOMES``). The pilot does not invent a
#: parallel scale; it translates into the one the repository already has.
LADDER_OUTCOME_MAP = {
    VALID: "SUCCESS",
    ACCESS_DENIED: "BLOCKED_403",
    BLANK_PAGE: "BLOCKED_CHALLENGE",
    UNHYDRATED: "BLOCKED_CHALLENGE",
    IDENTITY_MISMATCH: "WRONG_PROPERTY",
    POLICY_NOT_FOUND: "NO_POLICY_SECTION",
    NAVIGATION_FAILED: "TIMEOUT",
    CAPTURE_FAILED: "TIMEOUT",
    UNEXPECTED_PAGE: "WRONG_PROPERTY",
}


def is_outcome(value: str) -> bool:
    return value in OUTCOMES


def may_bear_evidence(outcome: str) -> bool:
    """The single gate every artifact-writing path must pass.

        >>> may_bear_evidence("VALID")
        True
        >>> may_bear_evidence("ACCESS_DENIED")
        False
    """
    return outcome in EVIDENCE_BEARING_OUTCOMES


__all__ = [
    "VALID", "ACCESS_DENIED", "BLANK_PAGE", "UNHYDRATED", "IDENTITY_MISMATCH",
    "POLICY_NOT_FOUND", "NAVIGATION_FAILED", "CAPTURE_FAILED",
    "UNEXPECTED_PAGE", "OUTCOMES", "EVIDENCE_BEARING_OUTCOMES",
    "BLOCKED_OUTCOMES", "EXHAUSTED_OUTCOMES", "LADDER_OUTCOME_MAP",
    "is_outcome", "may_bear_evidence",
]

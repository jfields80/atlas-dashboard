"""PTF-POLICY-P0-001 -- explicit policy readiness states.

States, not a score. A single number would hide exactly the distinctions that
decide what an operator does next: blocked is not absent, absent is not
conflicted, and conflicted is not partial. Three of those want a different
action and one of them wants a phone call. The repository already proves the
pattern -- ``routing`` has READY/REVIEW/RETRY/REJECTED, ``reasons`` has a
closed terminal vocabulary -- so this module adds the policy-readiness layer in
the same idiom and maps onto what exists rather than replacing it.

No numeric confidence appears anywhere in this module, and
``extraction_confidence`` is consulted only as a categorical gate (INFERRED
never publishes), never compared by magnitude.

DERIVATION IS ADVISORY
----------------------
``derive()`` returns a state and its reasons. It does not publish, hold,
promote, or write. Publication authority remains exactly where it is: the
committed policy facts package, the operator approval flow and the publication
guard. A derived state is an input to a human decision, in the same way the
coverage audit is advisory on the identity side.

Pure and deterministic: same observations in, same state out.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.policy import policy_membrane as M          # noqa: E402
from scripts.pettripfinder.policy.policy_observation import (          # noqa: E402
    ESTABLISHING_TIERS,
    asserted_fields,
    establishing_fields,
)

POLICY_CONFIRMED = "POLICY_CONFIRMED"
POLICY_CONFIRMED_WITH_AMBIGUITY = "POLICY_CONFIRMED_WITH_AMBIGUITY"
POLICY_PARTIAL = "POLICY_PARTIAL"
POLICY_NEGATIVE_CONFIRMED = "POLICY_NEGATIVE_CONFIRMED"
POLICY_CONFLICT = "POLICY_CONFLICT"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
SOURCE_BLOCKED = "SOURCE_BLOCKED"
MANUAL_VERIFICATION_REQUIRED = "MANUAL_VERIFICATION_REQUIRED"

READINESS_STATES = (
    POLICY_CONFIRMED, POLICY_CONFIRMED_WITH_AMBIGUITY, POLICY_PARTIAL,
    POLICY_NEGATIVE_CONFIRMED, POLICY_CONFLICT, POLICY_NOT_FOUND,
    SOURCE_BLOCKED, MANUAL_VERIFICATION_REQUIRED,
)

#: The states that could ever accompany a published listing. Being in this set
#: is NECESSARY and nowhere near SUFFICIENT -- publication still requires the
#: existing operator approval and publication guard.
PUBLISHABLE_STATES = frozenset({POLICY_CONFIRMED, POLICY_CONFIRMED_WITH_AMBIGUITY})

#: How each new state maps onto mechanisms Atlas already has. This is the
#: ADAPT decision from the compatibility review, written as code so it is
#: testable instead of prose that drifts.
#:
#: ``routing`` values are the worker-routing states; ``capture_reason`` values
#: are the capture worker's terminal reasons; ``authority`` says which existing
#: authority ultimately owns the outcome.
EXISTING_STATE_MAP: Dict[str, Dict[str, str]] = {
    POLICY_CONFIRMED: {
        "routing": "READY",
        "capture_reason": "",
        "authority": "hotel_policy_facts (via operator approval)",
    },
    POLICY_CONFIRMED_WITH_AMBIGUITY: {
        "routing": "READY",
        "capture_reason": "",
        "authority": "hotel_policy_facts (via operator approval); the ambiguity "
                     "renders as the site's existing 'Not stated' doctrine",
    },
    POLICY_PARTIAL: {
        "routing": "REVIEW",
        "capture_reason": "",
        "authority": "held; operator rules whether the partial shape publishes",
    },
    POLICY_NEGATIVE_CONFIRMED: {
        "routing": "READY",
        "capture_reason": "POLICY_ABSENT_CONFIRMED",
        "authority": "hotel_exclusions (VERIFIED_NO_PETS)",
    },
    POLICY_CONFLICT: {
        "routing": "REVIEW",
        "capture_reason": "FEE_TERMS_CONFLICT",
        "authority": "approval_resolution (contradiction override is gated)",
    },
    POLICY_NOT_FOUND: {
        "routing": "REVIEW",
        "capture_reason": "POLICY_NOT_FOUND",
        "authority": "none yet; eligible for operator attestation",
    },
    SOURCE_BLOCKED: {
        "routing": "RETRY",
        "capture_reason": "ACCESS_DENIED",
        "authority": "none yet; eligible for attended capture",
    },
    MANUAL_VERIFICATION_REQUIRED: {
        "routing": "REVIEW",
        "capture_reason": "IDENTITY_UNVERIFIABLE",
        "authority": "none yet; a human must confirm before anything proceeds",
    },
}

#: Flags that declare an ambiguity the operator may publish honestly, because
#: the site already renders an unstated value as "Not stated" rather than
#: guessing. They downgrade CONFIRMED to CONFIRMED_WITH_AMBIGUITY, never below.
AMBIGUITY_FLAGS = frozenset({
    "FLAG_AMBIGUOUS_BASIS", "FLAG_AMBIGUOUS_SCOPE", "FLAG_MULTI_POLICY_BLOCKS",
})

#: Flags that mean a human must look before anything is believed.
MANUAL_FLAGS = frozenset({
    "FLAG_OCR_GRADE", "FLAG_UNSUPPORTED_SPECIES_WORDING", "FLAG_PDF_UNDATED",
})

#: The fields that make a record a usable pet policy at all. Absence of the
#: rest is ordinary and renders honestly; absence of pets_allowed is not a
#: policy.
CORE_FIELD = "pets_allowed"


@dataclass(frozen=True)
class ReadinessResult:
    state: str
    reasons: Tuple[str, ...] = ()
    ambiguities: Tuple[str, ...] = ()
    conflicts: Tuple[Dict, ...] = ()
    establishing_observations: Tuple[str, ...] = ()
    hint_observations: Tuple[str, ...] = ()
    rejected_observations: Tuple[Dict, ...] = ()

    @property
    def publishable(self) -> bool:
        """Necessary, never sufficient: the existing approval flow and
        publication guard still decide."""
        return self.state in PUBLISHABLE_STATES

    def to_dict(self) -> Dict:
        return {
            "state": self.state,
            "reasons": list(self.reasons),
            "ambiguities": list(self.ambiguities),
            "conflicts": [dict(c) for c in self.conflicts],
            "establishing_observations": list(self.establishing_observations),
            "hint_observations": list(self.hint_observations),
            "rejected_observations": [dict(r) for r in self.rejected_observations],
            "maps_to": EXISTING_STATE_MAP.get(self.state, {}),
            "publishable_subject_to_existing_gates": self.publishable,
        }


def derive(observations: Sequence[Mapping], *,
           blocked: bool = False,
           all_surfaces_reached: bool = False) -> ReadinessResult:
    """Derive one hotel's readiness state from its observation set.

    ``blocked`` says the acquisition ladder ended with official surfaces
    unreadable (403/challenge/timeout); ``all_surfaces_reached`` says every
    official surface rendered and simply stated nothing. The two are opposite
    operational situations that a naive "no facts found" would merge, which is
    precisely the distinction the capture worker already refuses to blur.
    """
    verdicts = [M.evaluate(o) for o in observations]
    paired = list(zip(observations, verdicts))

    rejected = tuple({"obs_id": o.get("obs_id", ""), **v.to_dict()}
                     for o, v in paired if v.rejected)
    surviving = [(o, v) for o, v in paired if not v.rejected]
    # "Establishing" means the membrane allows it to establish AND it actually
    # asserts something establishing. An observation carrying only
    # service-animal text passes the membrane and still establishes nothing;
    # counting it here would turn "no pet policy stated" into "partial record".
    establishing = [o for o, v in surviving
                    if v.may_establish and establishing_fields(o.get("extraction") or {})]
    hints = [o for o, v in surviving if v.hint_only]

    reasons: List[str] = []
    ambiguities: List[str] = []

    # M8 first: an unresolved contradiction outranks everything, including a
    # record that would otherwise look complete. A conflict discovered after
    # publication is how a fee change surfaces.
    conflicts = tuple(M.contradicting_pairs(establishing))
    if conflicts:
        reasons.append("contradictory official observations on field(s) %s; "
                       "this layer never selects a winner"
                       % sorted({c["field"] for c in conflicts}))
        return ReadinessResult(POLICY_CONFLICT, tuple(reasons), (), conflicts,
                               tuple(o.get("obs_id", "") for o in establishing),
                               tuple(o.get("obs_id", "") for o in hints),
                               rejected)

    if blocked and not establishing:
        reasons.append("official surfaces could not be read")
        return ReadinessResult(SOURCE_BLOCKED, tuple(reasons), (), (), (),
                               tuple(o.get("obs_id", "") for o in hints), rejected)

    # M7 + manual flags: evidence exists but below the mechanical bar.
    for obs in establishing:
        if M.infers_without_publishing(obs):
            reasons.append("observation %s is INFERRED; inference never publishes"
                           % obs.get("obs_id", ""))
        for flag in obs.get("flags") or ():
            if flag.get("code") in MANUAL_FLAGS:
                reasons.append("observation %s carries %s"
                               % (obs.get("obs_id", ""), flag["code"]))
    if reasons:
        return ReadinessResult(MANUAL_VERIFICATION_REQUIRED, tuple(reasons), (), (),
                               tuple(o.get("obs_id", "") for o in establishing),
                               tuple(o.get("obs_id", "") for o in hints), rejected)

    # M5: an archive can corroborate, never carry a live claim alone.
    if establishing and M.archive_only(establishing):
        reasons.append("every establishing observation is an archive snapshot")
        return ReadinessResult(MANUAL_VERIFICATION_REQUIRED, tuple(reasons), (), (),
                               tuple(o.get("obs_id", "") for o in establishing),
                               tuple(o.get("obs_id", "") for o in hints), rejected)

    if not establishing:
        # Nothing established. Which nothing is it?
        if any(M.service_animal_only(o) for o, _ in surviving):
            reasons.append("only service-animal language was stated; ADA access "
                           "is never a pet policy (M6)")
            return ReadinessResult(POLICY_NOT_FOUND, tuple(reasons), (), (), (),
                                   tuple(o.get("obs_id", "") for o in hints), rejected)
        reasons.append("no official surface stated a pet policy"
                       if all_surfaces_reached else
                       "no establishing observation was produced")
        state = POLICY_NOT_FOUND if all_surfaces_reached else MANUAL_VERIFICATION_REQUIRED
        return ReadinessResult(state, tuple(reasons), (), (), (),
                               tuple(o.get("obs_id", "") for o in hints), rejected)

    # Something was established. Negative facts route to the exclusion authority.
    merged: Dict[str, object] = {}
    for obs in establishing:
        for k, v in (obs.get("extraction") or {}).items():
            if k in asserted_fields(obs.get("extraction") or {}):
                merged.setdefault(k, v)
    if merged.get(CORE_FIELD) is False:
        reasons.append("official evidence states pets are not accepted; routes "
                       "to the existing exclusion authority (VERIFIED_NO_PETS)")
        return ReadinessResult(POLICY_NEGATIVE_CONFIRMED, tuple(reasons), (), (),
                               tuple(o.get("obs_id", "") for o in establishing),
                               tuple(o.get("obs_id", "") for o in hints), rejected)

    for obs in establishing:
        for flag in obs.get("flags") or ():
            code = flag.get("code")
            if code in AMBIGUITY_FLAGS:
                ambiguities.append(code)
            if code == "FLAG_MARKETING_ONLY":
                reasons.append("observation %s is marketing language without a "
                               "stated policy" % obs.get("obs_id", ""))

    if CORE_FIELD not in merged:
        reasons.append("no observation established whether pets are accepted")
        return ReadinessResult(POLICY_PARTIAL, tuple(reasons), tuple(sorted(set(ambiguities))),
                               (), tuple(o.get("obs_id", "") for o in establishing),
                               tuple(o.get("obs_id", "") for o in hints), rejected)
    if reasons:      # marketing-only, or any other non-fatal gap
        return ReadinessResult(POLICY_PARTIAL, tuple(reasons), tuple(sorted(set(ambiguities))),
                               (), tuple(o.get("obs_id", "") for o in establishing),
                               tuple(o.get("obs_id", "") for o in hints), rejected)

    state = POLICY_CONFIRMED_WITH_AMBIGUITY if ambiguities else POLICY_CONFIRMED
    return ReadinessResult(state, (), tuple(sorted(set(ambiguities))), (),
                           tuple(o.get("obs_id", "") for o in establishing),
                           tuple(o.get("obs_id", "") for o in hints), rejected)


__all__ = [
    "POLICY_CONFIRMED", "POLICY_CONFIRMED_WITH_AMBIGUITY", "POLICY_PARTIAL",
    "POLICY_NEGATIVE_CONFIRMED", "POLICY_CONFLICT", "POLICY_NOT_FOUND",
    "SOURCE_BLOCKED", "MANUAL_VERIFICATION_REQUIRED",
    "READINESS_STATES", "PUBLISHABLE_STATES", "EXISTING_STATE_MAP",
    "AMBIGUITY_FLAGS", "MANUAL_FLAGS", "ReadinessResult", "derive",
]

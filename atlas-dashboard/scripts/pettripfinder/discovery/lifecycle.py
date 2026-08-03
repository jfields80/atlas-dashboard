"""PTF-DISCOVERY-001 WO-1A Step 8 -- property lifecycle handling.

Amendment v1.1 §A6/§B6 and ``INV-LIFECYCLE-REVIEW``. Discovery may **propose** a
lifecycle state; it may never apply a destructive one to a published property.

FD-4: the destructive-change review owner is Jonathan Fields (founder/operator).
Destructive proposals require explicit human approval before a published record
changes. Non-destructive proposals may be staged for review, but are never
silently published either.

The two existing signals are MAPPED, not re-derived:

  * ``ELIGIBILITY_PERMANENTLY_CLOSED`` (set from Google ``businessStatus``)
    -> ``PERMANENTLY_CLOSED``;
  * ``IDENTITY_POSSIBLE_REBRAND`` (``identity_resolution``) -> proposes
    ``REBRANDED``.

``resolution_eligibility`` already holds BOTH sides of a possible rebrand at
``REVIEW_IDENTITY`` so neither proceeds independently and no duplicate import
job is created. That conservative behavior is preserved, not replaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.membrane import assert_dataclasses_clean
from scripts.pettripfinder.discovery.models import DiscoveryCandidate

# --------------------------------------------------------------------------- #
# PropertyLifecycleState (amendment §B6).
# --------------------------------------------------------------------------- #

ACTIVE = "ACTIVE"
TEMPORARILY_CLOSED = "TEMPORARILY_CLOSED"
PERMANENTLY_CLOSED = "PERMANENTLY_CLOSED"
REBRANDED = "REBRANDED"
RENAMED = "RENAMED"
CONVERTED_TO_NEW_BRAND = "CONVERTED_TO_NEW_BRAND"
DEMOLISHED_OR_NO_LONGER_HOTEL = "DEMOLISHED_OR_NO_LONGER_HOTEL"
STATUS_UNKNOWN = "STATUS_UNKNOWN"

LIFECYCLE_STATES = frozenset({
    ACTIVE, TEMPORARILY_CLOSED, PERMANENTLY_CLOSED, REBRANDED, RENAMED,
    CONVERTED_TO_NEW_BRAND, DEMOLISHED_OR_NO_LONGER_HOTEL, STATUS_UNKNOWN,
})

#: FD-4: states whose application to a PUBLISHED record requires explicit
#: human approval. These remove or redefine a live listing -- getting one wrong
#: deletes real published inventory.
DESTRUCTIVE_STATES = frozenset({
    PERMANENTLY_CLOSED,
    DEMOLISHED_OR_NO_LONGER_HOTEL,
    CONVERTED_TO_NEW_BRAND,
})

#: FD-4 also names identity-changing rebrand/merge as destructive, which is a
#: property of the CHANGE rather than of the target state alone.
IDENTITY_CHANGING_STATES = frozenset({REBRANDED})

#: Review dispositions.
DISPOSITION_AUTO_APPLIED = "AUTO_APPLIED"           # non-published, non-destructive
DISPOSITION_STAGED_FOR_REVIEW = "STAGED_FOR_REVIEW"  # visible, not applied
DISPOSITION_REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"
DISPOSITIONS = frozenset({
    DISPOSITION_AUTO_APPLIED, DISPOSITION_STAGED_FOR_REVIEW,
    DISPOSITION_REQUIRES_HUMAN_APPROVAL,
})

REVIEW_OWNER = "Jonathan Fields (founder/operator)"   # FD-4


class LifecycleError(ValueError):
    """Raised when a lifecycle proposal is malformed or would be applied unsafely."""


@dataclass(frozen=True)
class LifecycleProposal:
    """A PROPOSED state change. Never itself an applied change."""

    candidate_id: str
    proposed_state: str
    evidence: Tuple[str, ...]
    is_published: bool = False
    identity_changing: bool = False
    disposition: str = DISPOSITION_STAGED_FOR_REVIEW
    review_owner: str = ""
    note: str = ""

    def validate(self) -> None:
        if self.proposed_state not in LIFECYCLE_STATES:
            raise LifecycleError("unknown lifecycle state: %r" % self.proposed_state)
        if self.disposition not in DISPOSITIONS:
            raise LifecycleError("unknown disposition: %r" % self.disposition)
        if not self.evidence:
            raise LifecycleError(
                "a lifecycle proposal states the evidence behind it "
                "(candidate %s)" % self.candidate_id)

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id, "proposed_state": self.proposed_state,
            "evidence": list(self.evidence), "is_published": self.is_published,
            "identity_changing": self.identity_changing,
            "disposition": self.disposition, "review_owner": self.review_owner,
            "note": self.note,
        }


def is_destructive(proposed_state: str, *, identity_changing: bool = False) -> bool:
    """FD-4's definition, which has two independent halves:

    * the target state itself removes or redefines a live listing
      (PERMANENTLY_CLOSED / DEMOLISHED_OR_NO_LONGER_HOTEL /
      CONVERTED_TO_NEW_BRAND); or
    * the change is an identity-changing rebrand or merge -- destructive
      because of what it does to identity, not because of the target state.

    A plain RENAMED with no identity change is NOT destructive: amendment §A6
    is explicit that a name change alone never creates or destroys a hotel.
    """
    if proposed_state in DESTRUCTIVE_STATES:
        return True
    return identity_changing and proposed_state in IDENTITY_CHANGING_STATES


def disposition_for(proposed_state: str, *, is_published: bool,
                    identity_changing: bool = False) -> str:
    """Deterministic routing of a proposal.

    A destructive change to a PUBLISHED property requires explicit human
    approval. Everything else is staged for review -- never silently applied to
    a published record. Only a non-published, non-destructive proposal may be
    applied automatically.
    """
    if is_published and is_destructive(proposed_state, identity_changing=identity_changing):
        return DISPOSITION_REQUIRES_HUMAN_APPROVAL
    if is_published:
        return DISPOSITION_STAGED_FOR_REVIEW
    if is_destructive(proposed_state, identity_changing=identity_changing):
        return DISPOSITION_STAGED_FOR_REVIEW
    return DISPOSITION_AUTO_APPLIED


def propose_lifecycle(candidate: DiscoveryCandidate, *, is_published: bool = False,
                      identity_outcome: str = "") -> LifecycleProposal:
    """Map the signals discovery ALREADY produces onto a proposed state.

    Nothing is inferred beyond those signals; absence of a signal is
    ``STATUS_UNKNOWN``, never an assumption that a property is fine.
    """
    eligibility = {r.eligibility_state for r in candidate.source_records if r.eligibility_state}
    evidence: list = []
    identity_changing = False

    if C.ELIGIBILITY_PERMANENTLY_CLOSED in eligibility:
        state = PERMANENTLY_CLOSED
        evidence.append("provider_business_status:CLOSED_PERMANENTLY")
    elif identity_outcome == C.IDENTITY_POSSIBLE_REBRAND:
        state = REBRANDED
        identity_changing = True
        evidence.append("identity_resolution:%s" % C.IDENTITY_POSSIBLE_REBRAND)
    elif identity_outcome == C.IDENTITY_UNRESOLVED:
        state = STATUS_UNKNOWN
        evidence.append("identity_resolution:%s" % C.IDENTITY_UNRESOLVED)
    elif C.ELIGIBILITY_ELIGIBLE in eligibility:
        state = ACTIVE
        evidence.append("provider_eligibility:ELIGIBLE")
    else:
        state = STATUS_UNKNOWN
        evidence.append("no_lifecycle_signal")

    disposition = disposition_for(state, is_published=is_published,
                                  identity_changing=identity_changing)
    proposal = LifecycleProposal(
        candidate_id=candidate.candidate_id, proposed_state=state,
        evidence=tuple(evidence), is_published=is_published,
        identity_changing=identity_changing, disposition=disposition,
        review_owner=(REVIEW_OWNER
                      if disposition == DISPOSITION_REQUIRES_HUMAN_APPROVAL else ""))
    proposal.validate()
    return proposal


def assert_not_silently_applied(proposal: LifecycleProposal) -> None:
    """Guard for any future apply path: a proposal needing approval must not be
    applied by code. Raises rather than returning a boolean so it cannot be
    ignored at a call site."""
    if proposal.disposition == DISPOSITION_REQUIRES_HUMAN_APPROVAL:
        raise LifecycleError(
            "%s on published candidate %s requires explicit approval from %s"
            % (proposal.proposed_state, proposal.candidate_id, REVIEW_OWNER))


# --------------------------------------------------------------------------- #
# Rebrand preservation (amendment §A6).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RebrandPreservation:
    """What a rebrand must keep. A name/brand change ALONE never creates a new
    hotel -- the internal identity survives and the old identifiers become
    aliases."""

    candidate_id: str
    preserved_names: Tuple[str, ...]
    preserved_urls: Tuple[str, ...]
    historical_provider_ids: Tuple[str, ...]
    redirect_evidence: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "preserved_names": list(self.preserved_names),
            "preserved_urls": list(self.preserved_urls),
            "historical_provider_ids": list(self.historical_provider_ids),
            "redirect_evidence": list(self.redirect_evidence),
        }


def preserve_through_rebrand(candidate: DiscoveryCandidate, *, new_name: str = "",
                             redirect_evidence: Sequence[str] = ()) -> RebrandPreservation:
    names = {r.name for r in candidate.source_records if r.name}
    if candidate.name:
        names.add(candidate.name)
    if new_name:
        names.add(new_name)
    urls = {r.website_url for r in candidate.source_records if r.website_url}
    if candidate.website_url:
        urls.add(candidate.website_url)
    provider_ids = {"%s:%s" % (p, rid) for p, rid in candidate.provider_ids if rid}
    return RebrandPreservation(
        candidate_id=candidate.candidate_id,
        preserved_names=tuple(sorted(names)),
        preserved_urls=tuple(sorted(urls)),
        historical_provider_ids=tuple(sorted(provider_ids)),
        redirect_evidence=tuple(redirect_evidence))


def summarize_proposals(proposals: Sequence[LifecycleProposal]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for p in proposals:
        counts[p.proposed_state] = counts.get(p.proposed_state, 0) + 1
        counts["disposition_%s" % p.disposition] = counts.get(
            "disposition_%s" % p.disposition, 0) + 1
    return dict(sorted(counts.items()))


assert_dataclasses_clean(LifecycleProposal, RebrandPreservation,
                         context="discovery.lifecycle")

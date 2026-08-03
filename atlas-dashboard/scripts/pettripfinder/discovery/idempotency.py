"""PTF-DISCOVERY-001 WO-1A Step 6 -- cross-run idempotency and the requeue guard.

Implements ``INV-IDEM-SINGLE-ACTIVE`` and ``INV-REQUEUE-GUARD`` (amendment
v1.1 §A5), plus the FD-2 re-verification reason taxonomy.

Three single-active rules:

  1. one current provider record per ``(provider, provider_record_id)`` --
     already true in practice via dedup's Level-1 rule; asserted here;
  2. one active canonical candidate per resolved real-world hotel;
  3. one active queue entry per ``(candidate_id, worker_contract_version)``.

Re-runs **supersede or merge**; they never duplicate. Rule 3 is why a contract
bump legitimately produces a NEW active entry instead of silently overwriting
work that was verified under the old contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery.membrane import assert_dataclasses_clean
from scripts.pettripfinder.discovery.models import DiscoveryCandidate

# --------------------------------------------------------------------------- #
# FD-2 -- the closed re-verification reason taxonomy.
#
# A VERIFIED / PUBLISHED / HELD / actively-queued hotel is never requeued
# without exactly one of these. Free text may SUPPLEMENT a reason; it may never
# replace one, because a free-text-only reason cannot be counted, audited, or
# reasoned about across runs.
# --------------------------------------------------------------------------- #

POLICY_STALE = "POLICY_STALE"
OFFICIAL_URL_CHANGED = "OFFICIAL_URL_CHANGED"
PROPERTY_IDENTITY_CHANGED = "PROPERTY_IDENTITY_CHANGED"
PROPERTY_REBRANDED = "PROPERTY_REBRANDED"
PROPERTY_RENAMED = "PROPERTY_RENAMED"
PROPERTY_LIFECYCLE_CHANGED = "PROPERTY_LIFECYCLE_CHANGED"
SOURCE_CONTRADICTION = "SOURCE_CONTRADICTION"
HUMAN_CORRECTION = "HUMAN_CORRECTION"
CONTRACT_VERSION_CHANGED = "CONTRACT_VERSION_CHANGED"
SCHEDULED_REVERIFICATION = "SCHEDULED_REVERIFICATION"
PROVIDER_RECORD_CHANGED = "PROVIDER_RECORD_CHANGED"

REVERIFICATION_REASONS = frozenset({
    POLICY_STALE, OFFICIAL_URL_CHANGED, PROPERTY_IDENTITY_CHANGED,
    PROPERTY_REBRANDED, PROPERTY_RENAMED, PROPERTY_LIFECYCLE_CHANGED,
    SOURCE_CONTRADICTION, HUMAN_CORRECTION, CONTRACT_VERSION_CHANGED,
    SCHEDULED_REVERIFICATION, PROVIDER_RECORD_CHANGED,
})

#: Hotel states protected by the requeue guard.
PROTECTED_STATES = frozenset({"VERIFIED", "PUBLISHED", "HELD", "QUEUED"})


class IdempotencyError(ValueError):
    """Raised when a requeue or activation would violate a single-active rule."""


class RequeueBlocked(IdempotencyError):
    """Raised when a protected hotel would be requeued without a valid reason."""


# --------------------------------------------------------------------------- #
# The requeue guard (INV-REQUEUE-GUARD).
# --------------------------------------------------------------------------- #

def assert_requeue_allowed(listing_state: str, *, reason: str = "",
                           explanation: str = "") -> None:
    """Fail closed unless a protected hotel carries exactly one valid reason.

    ``explanation`` is free text that SUPPLEMENTS ``reason``; supplying it
    without a reason is precisely the case FD-2 rules out.
    """
    state = (listing_state or "").strip().upper()
    if state not in PROTECTED_STATES:
        return                                  # unprotected: nothing to guard

    if not reason:
        raise RequeueBlocked(
            "%s hotel may not be requeued without a recorded re-verification "
            "reason%s" % (state, " (free-text explanation is not a substitute)"
                          if explanation else ""))
    if reason not in REVERIFICATION_REASONS:
        raise RequeueBlocked("unknown re-verification reason: %r" % reason)


def requeue_allowed(listing_state: str, *, reason: str = "",
                    explanation: str = "") -> bool:
    """Non-raising form for reporting paths."""
    try:
        assert_requeue_allowed(listing_state, reason=reason, explanation=explanation)
        return True
    except RequeueBlocked:
        return False


#: Signals that may NEVER be promoted into a re-verification reason. Discovery
#: cannot manufacture a reason to re-open a verified hotel out of a third-party
#: pet hint -- that is the Membrane restated at the requeue boundary (FD-2).
FORBIDDEN_REASON_SOURCES = frozenset({
    "pet_friendly", "allows_dogs", "dog_friendly", "pets_allowed",
    "directory_tag", "provider_pet_tag",
})


def assert_reason_not_from_discovery_signal(source: str) -> None:
    if (source or "").strip().lower() in FORBIDDEN_REASON_SOURCES:
        raise RequeueBlocked(
            "a discovery pet signal (%s) can never justify re-verification; "
            "only the official-source pipeline establishes policy facts" % source)


# --------------------------------------------------------------------------- #
# Single-active rules (INV-IDEM-SINGLE-ACTIVE).
# --------------------------------------------------------------------------- #

def provider_record_key(provider: str, provider_record_id: str) -> Tuple[str, str]:
    return (provider, provider_record_id)


def queue_entry_key(candidate_id: str, worker_contract_version: str) -> Tuple[str, str]:
    """THE queue idempotency key (amendment §A5, FD-3 rule 4)."""
    return (candidate_id, worker_contract_version)


@dataclass(frozen=True)
class ActivationPlan:
    """What a re-run should do, decided deterministically and explainably."""
    new_entries: Tuple[str, ...] = ()           # queue_entry_ids to create
    unchanged_entries: Tuple[str, ...] = ()     # already active, same key
    superseded_entries: Tuple[Tuple[str, str], ...] = ()   # (old_id, new_id)

    def to_dict(self) -> dict:
        return {
            "new_entries": list(self.new_entries),
            "unchanged_entries": list(self.unchanged_entries),
            "superseded_entries": [list(p) for p in self.superseded_entries],
        }


def assert_single_active_provider_records(records: Iterable) -> None:
    seen: Dict[Tuple[str, str], int] = {}
    for r in records:
        if not getattr(r, "provider_record_id", ""):
            continue
        key = provider_record_key(r.provider, r.provider_record_id)
        seen[key] = seen.get(key, 0) + 1
    dupes = sorted(k for k, n in seen.items() if n > 1)
    if dupes:
        raise IdempotencyError(
            "more than one current record per (provider, provider_record_id): %s" % (dupes,))


def assert_single_active_candidates(candidates: Sequence[DiscoveryCandidate]) -> None:
    """One ACTIVE candidate per resolved hotel. A candidate marked
    ``superseded_by`` is history, not an active record, and is excluded."""
    active = [c for c in candidates if not c.superseded_by]
    seen: Dict[str, int] = {}
    for c in active:
        seen[c.candidate_id] = seen.get(c.candidate_id, 0) + 1
    dupes = sorted(cid for cid, n in seen.items() if n > 1)
    if dupes:
        raise IdempotencyError("more than one active candidate for: %s" % (dupes,))


def plan_activation(existing_entry_ids_by_key: Dict[Tuple[str, str], str],
                    incoming: Sequence[Tuple[str, str, str]]) -> ActivationPlan:
    """Decide create / keep / supersede for a re-run.

    ``existing_entry_ids_by_key`` maps ``(candidate_id, contract_version)`` to
    the currently active queue_entry_id. ``incoming`` is
    ``(candidate_id, contract_version, queue_entry_id)``.

    A second run over the same market with the same contract yields the same
    key AND the same deterministic entry id, so it lands in ``unchanged`` --
    it updates in place rather than duplicating. A contract bump changes the
    key, which is what makes it a legitimately NEW active entry rather than a
    silent overwrite of work verified under the old contract.
    """
    new: List[str] = []
    unchanged: List[str] = []
    superseded: List[Tuple[str, str]] = []

    for candidate_id, contract_version, entry_id in incoming:
        key = queue_entry_key(candidate_id, contract_version)
        current = existing_entry_ids_by_key.get(key)
        if current is None:
            new.append(entry_id)
        elif current == entry_id:
            unchanged.append(entry_id)
        else:
            superseded.append((current, entry_id))

    return ActivationPlan(
        new_entries=tuple(sorted(new)),
        unchanged_entries=tuple(sorted(unchanged)),
        superseded_entries=tuple(sorted(superseded)))


assert_dataclasses_clean(ActivationPlan, context="discovery.idempotency")

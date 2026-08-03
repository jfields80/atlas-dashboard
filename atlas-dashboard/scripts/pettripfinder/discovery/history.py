"""PTF-DISCOVERY-001 WO-1A Step 7 -- supersession and merge history.

Amendment v1.1 §B9. Two immutable record types that make "what replaced what,
and why" reconstructable from records alone rather than from someone's memory
of a run.

**Component evidence is captured, never recomputed.** ``deduplicate.py``
already decides merges and already records *why* on each candidate --
``merge_reason`` (e.g. ``phone_plus_compatible_name``) and ``conflict_flags``.
``MergeHistoryRecord`` stores those existing values verbatim. Building a second,
parallel merge-explanation mechanism here would be the classic way for two
explanations of the same decision to drift apart, and ``deduplicate.py`` is a
frozen module for exactly that reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery.membrane import assert_dataclasses_clean
from scripts.pettripfinder.discovery.models import DiscoveryCandidate
from scripts.pettripfinder.discovery.run_context import DiscoveryRunContext

# --------------------------------------------------------------------------- #
# Supersession reasons. Closed set -- a supersession with no stated reason is
# exactly the silent overwrite this record exists to prevent.
# --------------------------------------------------------------------------- #

SUPERSEDED_BY_RERUN = "SUPERSEDED_BY_RERUN"
SUPERSEDED_BY_MERGE = "SUPERSEDED_BY_MERGE"
SUPERSEDED_BY_CONTRACT_VERSION = "SUPERSEDED_BY_CONTRACT_VERSION"
SUPERSEDED_BY_URL_CHANGE = "SUPERSEDED_BY_URL_CHANGE"
SUPERSEDED_BY_LIFECYCLE_CHANGE = "SUPERSEDED_BY_LIFECYCLE_CHANGE"
SUPERSEDED_BY_OPERATOR = "SUPERSEDED_BY_OPERATOR"

SUPERSESSION_REASONS = frozenset({
    SUPERSEDED_BY_RERUN, SUPERSEDED_BY_MERGE, SUPERSEDED_BY_CONTRACT_VERSION,
    SUPERSEDED_BY_URL_CHANGE, SUPERSEDED_BY_LIFECYCLE_CHANGE, SUPERSEDED_BY_OPERATOR,
})


class HistoryError(ValueError):
    """Raised when a supersession or merge record would be unexplainable."""


@dataclass(frozen=True)
class SupersessionRecord:
    """One entry replacing another (amendment §B9)."""

    superseded_entry_id: str
    superseding_entry_id: str
    reason: str
    run_id: str
    effective_time: str
    note: str = ""          # may SUPPLEMENT the reason, never replace it

    def validate(self) -> None:
        if not self.superseded_entry_id or not self.superseding_entry_id:
            raise HistoryError("a supersession names both entries")
        if self.superseded_entry_id == self.superseding_entry_id:
            raise HistoryError("an entry cannot supersede itself: %s"
                               % self.superseded_entry_id)
        if self.reason not in SUPERSESSION_REASONS:
            raise HistoryError("unknown supersession reason: %r" % self.reason)
        if not self.run_id or not self.effective_time:
            raise HistoryError("a supersession is bound to a run and an effective time")

    def to_dict(self) -> dict:
        return {
            "superseded_entry_id": self.superseded_entry_id,
            "superseding_entry_id": self.superseding_entry_id,
            "reason": self.reason, "run_id": self.run_id,
            "effective_time": self.effective_time, "note": self.note,
        }


@dataclass(frozen=True)
class MergeHistoryRecord:
    """Which candidates were folded into a survivor, and the evidence that
    justified it -- copied from what ``deduplicate`` already decided."""

    surviving_candidate_id: str
    merged_candidate_ids: Tuple[str, ...]
    component_evidence: Tuple[str, ...]     # deduplicate's merge_reason components
    conflict_flags: Tuple[str, ...] = ()
    run_id: str = ""

    def validate(self) -> None:
        if not self.surviving_candidate_id:
            raise HistoryError("a merge names its survivor")
        if not self.merged_candidate_ids:
            raise HistoryError("a merge names what was merged")
        if self.surviving_candidate_id in self.merged_candidate_ids:
            raise HistoryError("the survivor cannot also be a merged candidate")
        if not self.component_evidence:
            # A merge with no recorded evidence is exactly the opaque decision
            # base §I forbids ("store every component so a human can read why").
            raise HistoryError("a merge records the component evidence that justified it")

    def to_dict(self) -> dict:
        return {
            "surviving_candidate_id": self.surviving_candidate_id,
            "merged_candidate_ids": list(self.merged_candidate_ids),
            "component_evidence": list(self.component_evidence),
            "conflict_flags": list(self.conflict_flags),
            "run_id": self.run_id,
        }


def merge_record_for(candidate: DiscoveryCandidate, *, run_id: str = "") -> Optional[MergeHistoryRecord]:
    """Build the merge record for a candidate that dedup actually merged.

    Returns ``None`` for a single-source candidate -- there is nothing to
    explain. The merged ids are the per-provider record identities that were
    folded together; the evidence is ``merge_reason`` split back into its
    components, exactly as ``deduplicate`` wrote it.
    """
    if len(candidate.source_records) < 2:
        return None
    components = tuple(part for part in (candidate.merge_reason or "").split(",") if part)
    if not components:
        return None
    merged = tuple(sorted(
        "%s:%s" % (r.provider, r.provider_record_id)
        for r in candidate.source_records if r.provider_record_id))
    record = MergeHistoryRecord(
        surviving_candidate_id=candidate.candidate_id,
        merged_candidate_ids=merged,
        component_evidence=components,
        conflict_flags=tuple(candidate.conflict_flags),
        run_id=run_id)
    record.validate()
    return record


def supersede(previous_entry_id: str, current_entry_id: str, *, reason: str,
              context: DiscoveryRunContext, note: str = "") -> SupersessionRecord:
    """Record that ``current`` replaces ``previous``. Validated on construction
    so an unexplainable supersession cannot be persisted."""
    record = SupersessionRecord(
        superseded_entry_id=previous_entry_id,
        superseding_entry_id=current_entry_id,
        reason=reason, run_id=context.run_id,
        effective_time=context.effective_time, note=note)
    record.validate()
    return record


def merge_history_ref(record: MergeHistoryRecord) -> str:
    """Stable pointer stored on the surviving candidate."""
    return "mh_%s" % record.surviving_candidate_id


def summarize_history(supersessions: Sequence[SupersessionRecord],
                      merges: Sequence[MergeHistoryRecord]) -> Dict[str, int]:
    by_reason: Dict[str, int] = {}
    for s in supersessions:
        by_reason[s.reason] = by_reason.get(s.reason, 0) + 1
    return {
        "supersessions": len(supersessions),
        "merges": len(merges),
        "candidates_merged_away": sum(len(m.merged_candidate_ids) for m in merges),
        **{("reason_%s" % k): v for k, v in sorted(by_reason.items())},
    }


assert_dataclasses_clean(SupersessionRecord, MergeHistoryRecord,
                         context="discovery.history")

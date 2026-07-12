"""Selection-trace assembly and compression (AES-WEB-002D; AES-WEB-002 §14.3).

Pure function only: bounds the ``SlotSelectionTrace.candidates`` size by
naming the first ``limit`` candidates in the caller's already-deterministic
order and compressing the remainder to per-filter elimination counts, per
ADR-14's "size is bounded: beyond the top 5 named candidates per slot,
eliminations compress to per-filter counts."

The caller (``selector.ComponentSelector``) supplies candidates with
survivors first in final §14.2 step-7 ranking order — so the chosen winner
is always the first named candidate, with its score and score breakdown
preserved in the trace (audit remediation W-1) — followed by eliminated
candidates in the pool's registry-index order (lexicographic
``component_id``, §15.2). This module does not re-order; it only slices
and counts.
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from engines.website_generation.contracts.artifacts import SelectionCandidate


def compress_candidates(
    evaluated: Sequence[SelectionCandidate], limit: int
) -> Tuple[Tuple[SelectionCandidate, ...], Dict[str, int]]:
    """Split ``evaluated`` into ``(named, elimination_counts)``.

    ``named`` is the first ``limit`` entries, verbatim. Only candidates
    beyond that point contribute to ``elimination_counts`` (keyed by
    ``eliminated_by``); a beyond-the-limit candidate that was never
    eliminated (e.g. the eventual winner, when it does not fall inside the
    first ``limit``) contributes nothing here — its identity still reaches
    the caller via ``chosen_component_id`` on ``SlotSelectionTrace``, not via
    this list.
    """
    named = tuple(evaluated[:limit])
    counts: Dict[str, int] = {}
    for candidate in evaluated[limit:]:
        if candidate.eliminated_by:
            counts[candidate.eliminated_by] = counts.get(candidate.eliminated_by, 0) + 1
    return named, counts

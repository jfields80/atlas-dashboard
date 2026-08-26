"""PTF-PITTSBURGH-HARDENED-RECENSUS-001 -- the minimum-forward-progress gate.

WHY
---
The circuit breaker paces ONE process. Nothing paced the thing that started
the processes: an outer supervisor re-ran Pittsburgh's discovery every two
minutes for four hours, each run restoring the endpoint ledger, probing every
endpoint again, completing nothing, and exiting -- 47 resume cycles, one cell
gained, and a health ledger with 158 consecutive failures on one endpoint.
The client could not see that it was being supervised, and the supervisor
could not see that it was making no progress.

WHAT THIS IS
------------
A small ledger beside the discovery cache, ``discovery_progress.json``
(``ptf-discovery-progress/1.0``), that records every resume cycle which
ATTEMPTED live free discovery and how many cells it newly completed. When
``stall_cycles`` consecutive cycles complete nothing, free discovery is
STALLED: the state document reports WAITING_FOR_FREE_DISCOVERY even if an
endpoint looks available, and the runner makes no live request until a human
overrides the gate for one run (``--override-progress-gate``). One cycle that
completes a cell clears it. Cycles that made no attempt (cache-only, nothing
remaining, gated) are counted separately and never advance the stall.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional

SCHEMA = "ptf-discovery-progress/1.0"
FILENAME = "discovery_progress.json"

#: Consecutive attempting cycles with zero newly completed cells before the
#: gate closes. Three is one cooldown's worth of retries on the committed
#: registry: enough to survive a flap, too few to spend a night on an outage.
DEFAULT_STALL_CYCLES = 3

#: Cycle rows kept in the ledger (the counters are what the gate reads).
HISTORY_LIMIT = 50

#: The warning a gated query carries in place of a live request.
WARNING_PROGRESS_GATE = "overpass_forward_progress_gate"

STALLED = "STALLED"
PROGRESSING = "PROGRESSING"
NO_CYCLES = "NO_CYCLES"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def empty_document() -> Dict:
    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Every discovery resume cycle that attempted live free discovery and "
         "the cells it newly completed. Consecutive attempting cycles that "
         "complete nothing close the gate: the runner stops asking and the "
         "state reads WAITING_FOR_FREE_DISCOVERY until a human overrides one "
         "run or a cycle completes a cell."),
        ("attempting_cycles", 0),
        ("consecutive_zero_progress_cycles", 0),
        ("gated_runs", 0),
        ("last_progress_at", ""),
        ("last_cycle_at", ""),
        ("cycles", []),
    ))


def load(path: Optional[Path]) -> Dict:
    if path is None or not Path(path).is_file():
        return empty_document()
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return empty_document()
    if document.get("schema") != SCHEMA:
        return empty_document()
    merged = empty_document()
    merged.update(document)
    return merged


def write(document: Mapping, path: Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return path.as_posix()


def is_stalled(document: Mapping, stall_cycles: int = DEFAULT_STALL_CYCLES) -> bool:
    return int(document.get("consecutive_zero_progress_cycles") or 0) >= max(1, int(stall_cycles))


def status(document: Mapping, stall_cycles: int = DEFAULT_STALL_CYCLES) -> str:
    if not int(document.get("attempting_cycles") or 0):
        return NO_CYCLES
    return STALLED if is_stalled(document, stall_cycles) else PROGRESSING


def record_cycle(path: Path, *, newly_completed: int, requests_made: int,
                 remaining_after: int, override: bool = False,
                 clock: Callable[[], datetime] = _now) -> Dict:
    """One resume cycle that ATTEMPTED live discovery finished."""
    document = load(path)
    now = clock().astimezone(timezone.utc).isoformat()
    document["attempting_cycles"] = int(document["attempting_cycles"]) + 1
    if newly_completed > 0:
        document["consecutive_zero_progress_cycles"] = 0
        document["last_progress_at"] = now
    else:
        document["consecutive_zero_progress_cycles"] = (
            int(document["consecutive_zero_progress_cycles"]) + 1)
    document["last_cycle_at"] = now
    cycles = list(document.get("cycles") or [])
    cycles.append(OrderedDict((
        ("at", now), ("newly_completed_cells", int(newly_completed)),
        ("requests_made", int(requests_made)),
        ("remaining_after", int(remaining_after)), ("override", bool(override)),
    )))
    document["cycles"] = cycles[-HISTORY_LIMIT:]
    write(document, path)
    return document


def record_gated_run(path: Path, *, clock: Callable[[], datetime] = _now) -> Dict:
    """A run refused to make live requests because the gate was closed."""
    document = load(path)
    document["gated_runs"] = int(document.get("gated_runs") or 0) + 1
    document["last_gated_at"] = clock().astimezone(timezone.utc).isoformat()
    write(document, path)
    return document


def summary(document: Mapping, stall_cycles: int = DEFAULT_STALL_CYCLES) -> Dict:
    """What a state document or a run report says about forward progress."""
    return OrderedDict((
        ("status", status(document, stall_cycles)),
        ("stall_cycles", int(stall_cycles)),
        ("attempting_cycles", int(document.get("attempting_cycles") or 0)),
        ("consecutive_zero_progress_cycles",
         int(document.get("consecutive_zero_progress_cycles") or 0)),
        ("gated_runs", int(document.get("gated_runs") or 0)),
        ("last_progress_at", str(document.get("last_progress_at") or "")),
        ("last_cycle_at", str(document.get("last_cycle_at") or "")),
    ))


__all__ = ["SCHEMA", "FILENAME", "DEFAULT_STALL_CYCLES", "WARNING_PROGRESS_GATE",
           "STALLED", "PROGRESSING", "NO_CYCLES", "empty_document", "load", "write",
           "is_stalled", "status", "record_cycle", "record_gated_run", "summary"]

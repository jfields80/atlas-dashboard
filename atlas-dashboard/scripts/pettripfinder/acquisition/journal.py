"""Never hold a paid capture only in memory.

The lesson is expensive and specific. PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002 was
killed by the process budget at nineteen completed captures, every one of them
paid for, every one of them lost, because the results existed only in a Python
list. The second attempt journalled each property the moment it finished and
survived four more kills without losing anything.

So: append-only, one line per property, flushed and fsynced before the caller
is told the property is done. A run must survive a kill, a timeout, a closed
terminal and a dead machine.

IDEMPOTENCY
-----------
Re-running the same work order must not re-acquire what is already acquired.
The journal is keyed by IDENTITY, not by position, so resume is mechanical
rather than a matter of counting. A completed identity is skipped; a
half-written last line is discarded on read rather than mistaken for a result.

CONCURRENCY
-----------
Bounded parallelism is future work, but the durability layer has to be ready
for it or it will be retrofitted wrongly. Two guards are here now:

* an append under an exclusive lock, so interleaved writers cannot tear a line;
* a claim registry, so two workers cannot acquire the same property at once.

Neither costs anything in the single-worker case that runs today.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence, Set

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import client  # noqa: E402

_PROCESS_LOCK = threading.Lock()


class JournalError(RuntimeError):
    """The journal could not be read or written."""


class ClaimConflict(RuntimeError):
    """Another worker holds this property."""


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """An exclusive lock around one append.

    ``msvcrt`` on Windows, ``fcntl`` elsewhere, and a thread lock alone if
    neither is importable -- the last is still correct for the single-process
    case and is the only case that runs today.
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+b")
    try:
        try:
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            locked = "msvcrt"
        except (ImportError, OSError):
            try:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                locked = "fcntl"
            except (ImportError, OSError):
                locked = ""
        try:
            yield
        finally:
            if locked == "msvcrt":
                try:
                    handle.seek(0)
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            elif locked == "fcntl":
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


@dataclass
class Journal:
    """An append-only record of completed properties, keyed by identity."""

    path: Path

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self._claims: Set[str] = set()

    # -- reading ---------------------------------------------------------- #

    def read(self) -> Dict[str, Dict]:
        """Every completed property, by identity key.

        A trailing partial line -- the signature of a kill mid-write -- is
        discarded rather than parsed. Losing the last property is correct;
        inventing half of one is not.
        """
        if not self.path.exists():
            return {}
        out: Dict[str, Dict] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            key = entry.get("identity_key") or entry.get("slug")
            if key:
                out[str(key)] = entry
        return out

    def completed_keys(self) -> Set[str]:
        return set(self.read())

    def has(self, identity_key: str) -> bool:
        return identity_key in self.completed_keys()

    def count(self) -> int:
        return len(self.read())

    # -- writing ---------------------------------------------------------- #

    def append(self, entry: Mapping) -> None:
        """Record one completed property, durably, before the caller moves on."""
        key = entry.get("identity_key") or entry.get("slug")
        if not key:
            raise JournalError("a journal entry needs an identity_key")
        payload = json.dumps(client.redact(entry), ensure_ascii=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _PROCESS_LOCK:
            with _file_lock(self.path):
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(payload + chr(10))
                    handle.flush()
                    os.fsync(handle.fileno())

    def rewrite(self, entries: Sequence[Mapping]) -> None:
        """Replace the journal wholesale. Only for offline re-derivation."""
        with _PROCESS_LOCK:
            with _file_lock(self.path):
                self.path.write_text(
                    "".join(json.dumps(client.redact(e), ensure_ascii=False)
                            + chr(10) for e in entries), encoding="utf-8")

    # -- claims ----------------------------------------------------------- #

    @contextmanager
    def claim(self, identity_key: str) -> Iterator[None]:
        """Hold one property for the duration of its acquisition.

        Two workers acquiring the same property would pay twice for one answer
        and race to journal it. In-process today, because concurrency is not
        enabled yet; the call site is what matters, and it is already here.
        """
        with _PROCESS_LOCK:
            if identity_key in self._claims:
                raise ClaimConflict(
                    "%r is already being acquired by another worker"
                    % identity_key)
            self._claims.add(identity_key)
        try:
            yield
        finally:
            with _PROCESS_LOCK:
                self._claims.discard(identity_key)

    def held(self) -> Set[str]:
        return set(self._claims)


def reconcile(journal: Journal, expected_keys: Sequence[str]) -> Dict:
    """Does the journal hold exactly what the run was asked to acquire?

    Checked before any metric is trusted. A summary computed from a journal
    that lost or gained a property is arithmetic on the wrong set.
    """
    entries = journal.read()
    have = set(entries)
    want = set(expected_keys)
    duplicates: List[str] = []
    if journal.path.exists():
        seen: Dict[str, int] = {}
        for line in journal.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                key = json.loads(line).get("identity_key")
            except ValueError:
                continue
            if key:
                seen[key] = seen.get(key, 0) + 1
        duplicates = sorted(k for k, n in seen.items() if n > 1)

    missing = sorted(want - have)
    unexpected = sorted(have - want)
    return {"expected": len(want), "journalled": len(have),
            "missing": missing, "unexpected": unexpected,
            "duplicate_identities": duplicates,
            "passed": not missing and not unexpected and not duplicates}


__all__ = ["JournalError", "ClaimConflict", "Journal", "reconcile"]

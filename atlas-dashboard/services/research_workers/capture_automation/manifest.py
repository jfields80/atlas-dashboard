"""Append-only journal, and the manifest derived from it.

The journal is the truth. It is written one line at a time and flushed to disk
before the runner advances, so a crash, a Ctrl-C or Chrome dying mid-batch all
resume identically: read the journal, skip every hotel that already has a
terminal record, continue.

The manifest is *derived*. Rebuilding it from the journal at the end means a
corrupt manifest is repairable and a missing one is regenerable -- neither is a
reason to re-run a batch that already did the work.
"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .reasons import EXCEPTION_REASONS, explain, retry_for
from .state_machine import CAPTURED, EXCEPTION, HotelOutcome

JOURNAL_NAME = "journal.jsonl"
MANIFEST_NAME = "manifest.json"
MANIFEST_SCHEMA = "ptf-capture-batch-manifest/1.0"


class JournalError(RuntimeError):
    """Raised when the journal cannot be trusted."""


@dataclass
class Journal:
    """Append-only record of terminal hotel outcomes."""

    path: pathlib.Path

    @classmethod
    def open(cls, batch_dir) -> "Journal":
        root = pathlib.Path(batch_dir)
        root.mkdir(parents=True, exist_ok=True)
        return cls(path=root / JOURNAL_NAME)

    def append(self, outcome: HotelOutcome, *, at: str = "") -> None:
        """Write one terminal outcome and force it to disk.

        The fsync is not ceremony. Without it a crash loses the last few
        outcomes, and resume then re-captures hotels that already succeeded --
        which shows up later as duplicate captures nobody can explain.
        """
        record = dict(outcome.to_dict())
        record["at"] = at
        line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def records(self) -> Tuple[dict, ...]:
        """Every record, in order. A malformed line is fatal rather than
        skipped -- silently dropping journal lines would make resume lie."""
        if not self.path.exists():
            return ()
        out: List[dict] = []
        for n, raw in enumerate(self.path.read_text("utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except ValueError as exc:
                raise JournalError("journal line %d is not valid JSON: %s" % (n, exc))
            if not isinstance(rec, dict) or "hotel_id" not in rec:
                raise JournalError("journal line %d is not an outcome record" % n)
            out.append(rec)
        return tuple(out)

    def completed_hotel_ids(self) -> Tuple[str, ...]:
        """Hotels with any terminal record. Both CAPTURED and EXCEPTION count:
        a hotel that failed is done for this batch, and re-attempting it inside
        the same run is exactly the retry storm the design forbids.

        NOTE: this is the WITHIN-RUN notion of "done". It must not be used to
        decide what a *resumed* run may skip -- an EXCEPTION is unfinished work,
        not a completed capture. Use ``completed_capture_ids`` for that.
        """
        return tuple(dict.fromkeys(
            str(r.get("hotel_id")) for r in self.records()
            if r.get("state") in (CAPTURED, EXCEPTION)))

    # ----------------------------------------------------------------- #
    # Resume support.
    #
    # Resume asks a different question from "did we reach a terminal state".
    # It asks "does a complete, valid capture already exist". Those diverge
    # for every EXCEPTION, and conflating them is how a resumed run silently
    # abandons an IDENTITY_FAILED or a retryable POLICY_OFF_SCREEN.
    # ----------------------------------------------------------------- #

    def completed_capture_ids(self) -> Tuple[str, ...]:
        """Hotels with a COMPLETE, VALID capture -- the only ones a resumed run
        may skip.

        A record qualifies only when all of the following hold:
          * state is CAPTURED;
          * it carries an artifacts mapping;
          * that mapping names both a json_path and a png_path;
          * both files still exist on disk;
          * a png_sha256 is recorded.

        Anything short of that FAILS CLOSED -- the hotel is re-attempted. A
        half-written or hand-edited record must never be able to make a resumed
        run believe evidence exists that does not.
        """
        out: List[str] = []
        for r in self.records():
            if r.get("state") != CAPTURED:
                continue
            art = r.get("artifacts")
            if not isinstance(art, dict):
                continue
            json_path = str(art.get("json_path") or "")
            png_path = str(art.get("png_path") or "")
            if not json_path or not png_path:
                continue
            if not str(art.get("png_sha256") or ""):
                continue
            try:
                if not (pathlib.Path(json_path).exists() and pathlib.Path(png_path).exists()):
                    continue
            except OSError:
                continue
            out.append(str(r.get("hotel_id")))
        return tuple(dict.fromkeys(out))

    def incomplete_hotel_ids(self) -> Tuple[str, ...]:
        """Hotels with a terminal record that is NOT a complete capture.

        These are exactly the ones a resumed run must re-attempt rather than
        skip: identity failures, unverifiable pages, missing policy anchors,
        framing failures, and any CAPTURED record whose artifacts cannot be
        verified.
        """
        complete = set(self.completed_capture_ids())
        return tuple(dict.fromkeys(
            str(r.get("hotel_id")) for r in self.records()
            if r.get("state") in (CAPTURED, EXCEPTION)
            and str(r.get("hotel_id")) not in complete))

    def last_reason_by_hotel(self) -> Dict[str, str]:
        """Most recent terminal reason per hotel, for the resume summary."""
        out: Dict[str, str] = {}
        for r in self.records():
            if r.get("state") in (CAPTURED, EXCEPTION):
                out[str(r.get("hotel_id"))] = str(r.get("reason") or "")
        return out

    def captured_text_hashes(self) -> Dict[str, str]:
        """``text_sha256 -> hotel_id`` for everything captured so far."""
        out: Dict[str, str] = {}
        for r in self.records():
            if r.get("state") != CAPTURED:
                continue
            # A malformed artifacts value (anything that is not a mapping) used
            # to raise AttributeError here and take the whole run down. It is
            # treated as "no usable hash" instead: duplicate detection loses one
            # data point, which is strictly safer than crashing, and the record
            # is separately refused a resume skip by completed_capture_ids.
            art = r.get("artifacts")
            if not isinstance(art, dict):
                continue
            digest = str(art.get("text_sha256") or "")
            if digest:
                out.setdefault(digest, str(r.get("hotel_id") or ""))
        return out


def archived_text_hashes(*corpus_dirs) -> Dict[str, str]:
    """Text hashes of captures already archived from earlier batches.

    Cheap cross-batch duplicate detection: a page we captured last week should
    not silently become a second capture this week.
    """
    out: Dict[str, str] = {}
    for d in corpus_dirs:
        root = pathlib.Path(d)
        if not root.exists():
            continue
        for f in sorted(root.rglob("*.json")):
            try:
                payload = json.loads(f.read_text("utf-8"))
            except (ValueError, UnicodeDecodeError, OSError):
                continue
            if not isinstance(payload, dict):
                continue
            digest = str(payload.get("text_sha256") or "")
            if digest:
                out.setdefault(digest, "archived:%s" % f.name)
    return out


def _artifacts(record: dict) -> dict:
    """The artifacts mapping of a journal record, or an empty one.

    A record whose ``artifacts`` value is not a mapping (hand-edited, truncated
    mid-write, or written by an older shape) previously reached ``.get`` on a
    string and raised AttributeError, taking the whole manifest build down. It
    degrades to "no artifacts" instead -- which is also what makes
    ``completed_capture_ids`` refuse it a resume skip.
    """
    art = record.get("artifacts")
    return art if isinstance(art, dict) else {}


def build_manifest(*, batch_id: str, queue_size: int, journal: Journal,
                   started_at: str = "", finished_at: str = "",
                   aborted_reason: str = "",
                   skipped_hotel_ids: Sequence[str] = ()) -> dict:
    """Derive the batch manifest from the journal."""
    records = journal.records()

    successes, exceptions, duplicates = [], [], []
    for r in records:
        if r.get("state") == CAPTURED:
            successes.append(r)
        elif r.get("reason") == "DUPLICATE_CAPTURE":
            duplicates.append(r)
        else:
            exceptions.append(r)

    by_reason: Dict[str, int] = {}
    for r in exceptions + duplicates:
        reason = str(r.get("reason") or "UNKNOWN")
        by_reason[reason] = by_reason.get(reason, 0) + 1

    attempted = len(records)
    rate = (len(successes) / attempted) if attempted else 0.0

    return {
        "schema": MANIFEST_SCHEMA,
        "batch_id": batch_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "aborted_reason": aborted_reason,
        "counts": {
            "queued": queue_size,
            "attempted": attempted,
            "captured": len(successes),
            "exceptions": len(exceptions),
            "duplicates": len(duplicates),
            "skipped": len(skipped_hotel_ids),
        },
        "unattended_success_rate": round(rate, 4),
        "exceptions_by_reason": dict(sorted(by_reason.items())),
        "successful_captures": [
            {"hotel_id": r.get("hotel_id"),
             "json_path": _artifacts(r).get("json_path", ""),
             "png_path": _artifacts(r).get("png_path", ""),
             "text_sha256": _artifacts(r).get("text_sha256", ""),
             "png_sha256": _artifacts(r).get("png_sha256", ""),
             "png_width": _artifacts(r).get("png_width", 0),
             "png_height": _artifacts(r).get("png_height", 0),
             "citable_url": _artifacts(r).get("citable_url", ""),
             "policy_confidence": (_artifacts(r).get("policy") or {})
                                  .get("confidence", ""),
             "warnings": _artifacts(r).get("warnings", [])}
            for r in successes],
        "exceptions": [
            {"hotel_id": r.get("hotel_id"), "reason": r.get("reason"),
             "detail": r.get("detail", []), "retry": r.get("retry", ""),
             "explanation": explain(str(r.get("reason") or ""))}
            for r in exceptions],
        # Failure diagnostics are listed SEPARATELY from successful_captures,
        # and carry their labels on every entry, so nothing downstream can read
        # this section and mistake it for capture evidence.
        "failure_diagnostics": [
            {"hotel_id": r.get("hotel_id"),
             "terminal_reason": r.get("reason"),
             "diagnostic_level": _artifacts(r).get("diagnostic_level", ""),
             "relative_dir": _artifacts(r).get("relative_dir", ""),
             "collection_status": _artifacts(r).get("collection_status", ""),
             "labels": _artifacts(r).get("labels", []),
             "artifacts": _artifacts(r).get("artifacts", [])}
            for r in exceptions
            if _artifacts(r).get("schema") == "ptf-capture-diagnostic/1.0"],
        "duplicate_captures": [
            {"hotel_id": r.get("hotel_id"), "duplicate_of": r.get("duplicate_of", ""),
             "detail": r.get("detail", [])}
            for r in duplicates],
        "skipped_hotels": list(skipped_hotel_ids),
        "retry_recommendations": {
            "now": sorted(str(r.get("hotel_id")) for r in exceptions
                          if r.get("retry") == "now"),
            "manual": sorted(str(r.get("hotel_id")) for r in exceptions
                             if r.get("retry") == "manual"),
            "never": sorted(str(r.get("hotel_id")) for r in exceptions
                            if r.get("retry") == "never"),
        },
        "note": ("Captures only. Nothing here is attested, approved, promoted "
                 "or published; a human must run attest-official-page for each."),
    }


def write_manifest(manifest: dict, batch_dir) -> pathlib.Path:
    root = pathlib.Path(batch_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=False,
                               ensure_ascii=False), encoding="utf-8")
    return path

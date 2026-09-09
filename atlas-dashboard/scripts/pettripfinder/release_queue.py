"""ATLAS-THROUGHPUT-006 -- the release-ready queue and the activation lease.

005 proved a release can be composed from the current live release plus one
authorized package delta, and that a candidate staged on a superseded parent is
refused. What it did not provide is anywhere for the SECOND ready market to
wait, or anything that stops two operators activating at the same moment.

This is deliberately not a distributed orchestrator. It is a durable JSON
queue plus a single-holder lease, because the thing being protected is one
transition -- CURRENT LIVE to NEXT LIVE -- and everything else in the factory
is meant to stay parallel. Market research, package sealing, cache lookups and
candidate planning all continue while a release is activating; only the flip
serialises.

Two properties matter more than features:

* **Idempotence.** A market worker that submits the same sealed package twice
  has said one thing twice, not two things. Entries are keyed by
  ``(market_id, package_digest)``.
* **Explicit supersession.** A newer package for the same market does not
  silently replace an older one. It supersedes it only when the caller says so,
  and only while the older entry has not started work.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = SMP.REPO_ROOT
DEFAULT_QUEUE_ROOT = REPO_ROOT / "data" / "release_queue"
QUEUE_ENV = "PTF_RELEASE_QUEUE_ROOT"

QUEUE_SCHEMA = "ptf-release-queue-entry/1.0"
LEASE_SCHEMA = "ptf-activation-lease/1.0"

QUEUED = "QUEUED"
VALIDATING = "VALIDATING"
NEEDS_REPAIR = "NEEDS_REPAIR"
CANDIDATE_STAGED = "CANDIDATE_STAGED"
AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
AUTHORIZED = "AUTHORIZED"
ACTIVATING = "ACTIVATING"
VERIFYING = "VERIFYING"
LIVE = "LIVE"
FAILED = "FAILED"
ABANDONED = "ABANDONED"
SUPERSEDED = "SUPERSEDED"

STATES = (QUEUED, VALIDATING, NEEDS_REPAIR, CANDIDATE_STAGED, AWAITING_AUTHORIZATION,
          AUTHORIZED, ACTIVATING, VERIFYING, LIVE, FAILED, ABANDONED, SUPERSEDED)

#: Where an entry may go next. A state machine, so a queue cannot be walked
#: backwards into a state its evidence no longer supports.
TRANSITIONS: "OrderedDict[str, Tuple[str, ...]]" = OrderedDict((
    (QUEUED, (VALIDATING, SUPERSEDED, ABANDONED)),
    (VALIDATING, (CANDIDATE_STAGED, NEEDS_REPAIR, FAILED, ABANDONED)),
    (NEEDS_REPAIR, (VALIDATING, SUPERSEDED, ABANDONED)),
    (CANDIDATE_STAGED, (AWAITING_AUTHORIZATION, VALIDATING, FAILED, ABANDONED)),
    (AWAITING_AUTHORIZATION, (AUTHORIZED, CANDIDATE_STAGED, ABANDONED, FAILED)),
    # CANDIDATE_STAGED is reachable again from AUTHORIZED: that is a restage
    # after the live parent moved, and it invalidates the authorization.
    (AUTHORIZED, (ACTIVATING, CANDIDATE_STAGED, ABANDONED, FAILED)),
    (ACTIVATING, (VERIFYING, FAILED, AUTHORIZED)),
    (VERIFYING, (LIVE, FAILED)),
    (LIVE, ()),
    (FAILED, (VALIDATING, ABANDONED)),
    (ABANDONED, ()),
    (SUPERSEDED, ()),
))

#: An entry that has begun real work is not superseded silently.
STARTED_STATES = (VALIDATING, CANDIDATE_STAGED, AWAITING_AUTHORIZATION, AUTHORIZED,
                  ACTIVATING, VERIFYING, LIVE)

ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
LEASE_HELD = "LEASE_HELD"
LEASE_NOT_HELD = "LEASE_NOT_HELD"
LEASE_EXPIRED = "LEASE_EXPIRED"
SUPERSEDE_REFUSED = "SUPERSEDE_REFUSED"


class QueueError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code = code
        self.detail = detail


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path: Path, doc: Mapping) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-%s" % uuid.uuid4().hex[:8])
    tmp.write_text(SMP.canonical_json(doc) + "\n", encoding="utf-8", newline="\n")
    os.replace(str(tmp), str(path))
    return path


def entry_id(market_id: str, package_digest: str) -> str:
    """The identity a submission has. Two submissions of the same package are
    the same entry, which is what makes submit idempotent."""
    return "%s-%s" % (market_id, str(package_digest).split(":")[-1][:16])


class ReleaseQueue:
    """A durable, idempotent queue of markets ready to release."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root is not None else Path(
            os.environ.get(QUEUE_ENV) or DEFAULT_QUEUE_ROOT)
        (self.root / "entries").mkdir(parents=True, exist_ok=True)

    # ---- entries ---------------------------------------------------------- #
    def _path(self, entry: str) -> Path:
        return self.root / "entries" / ("%s.json" % entry)

    def get(self, entry: str) -> Optional["OrderedDict[str, Any]"]:
        path = self._path(entry)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)

    def entries(self) -> List["OrderedDict[str, Any]"]:
        return [json.loads(p.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
                for p in sorted((self.root / "entries").glob("*.json"))]

    def submit(self, *, market_id: str, package_digest: str, package_id: str = "",
               required_validation: Optional[Mapping] = None,
               submitted_by: str = "", note: str = "") -> "OrderedDict[str, Any]":
        """Idempotent. The same package submitted twice is one entry."""
        eid = entry_id(market_id, package_digest)
        existing = self.get(eid)
        if existing is not None:
            existing["resubmissions"] = int(existing.get("resubmissions") or 0) + 1
            existing["last_submitted_at"] = _now()
            _write_json(self._path(eid), existing)
            return existing
        doc = OrderedDict((
            ("schema", QUEUE_SCHEMA),
            ("entry_id", eid),
            ("market_id", market_id),
            ("package_digest", package_digest),
            ("package_id", package_id),
            ("state", QUEUED),
            ("submitted_at", _now()),
            ("last_submitted_at", _now()),
            ("submitted_by", submitted_by),
            ("resubmissions", 0),
            ("parent_at_stage", None),
            ("candidate_digest", None),
            ("required_validation", OrderedDict(required_validation or {})),
            ("ci_run", None),
            ("authorization", None),
            ("result", None),
            ("supersedes", None),
            ("superseded_by", None),
            ("history", [OrderedDict((("state", QUEUED), ("at", _now()), ("note", note)))]),
        ))
        _write_json(self._path(eid), doc)
        return doc

    def transition(self, entry: str, to_state: str, **fields: Any) -> "OrderedDict[str, Any]":
        doc = self.get(entry)
        if doc is None:
            raise QueueError("NO_SUCH_ENTRY", entry)
        current = str(doc["state"])
        if to_state != current and to_state not in TRANSITIONS.get(current, ()):
            raise QueueError(ILLEGAL_TRANSITION, "%s -> %s" % (current, to_state))
        doc["state"] = to_state
        for key, value in fields.items():
            doc[key] = value
        doc.setdefault("history", []).append(
            OrderedDict((("state", to_state), ("at", _now()),
                         ("note", str(fields.get("note") or "")))))
        _write_json(self._path(entry), doc)
        return doc

    def supersede(self, *, old_entry: str, new_entry: str, reason: str = ""
                  ) -> "OrderedDict[str, Any]":
        """Explicit only, and only while the old entry has not started work."""
        old = self.get(old_entry)
        new = self.get(new_entry)
        if old is None or new is None:
            raise QueueError("NO_SUCH_ENTRY", "%s / %s" % (old_entry, new_entry))
        if old["market_id"] != new["market_id"]:
            raise QueueError(SUPERSEDE_REFUSED, "different markets")
        if old["state"] in STARTED_STATES:
            raise QueueError(SUPERSEDE_REFUSED,
                             "%s is %s: a started entry is finished or abandoned explicitly, "
                             "never superseded out from under itself" % (old_entry, old["state"]))
        old = self.transition(old_entry, SUPERSEDED, superseded_by=new_entry, note=reason)
        new["supersedes"] = old_entry
        _write_json(self._path(new_entry), new)
        return old

    def ready(self) -> List["OrderedDict[str, Any]"]:
        return [e for e in self.entries() if e["state"] in (QUEUED, NEEDS_REPAIR)]

    def in_flight(self) -> List["OrderedDict[str, Any]"]:
        return [e for e in self.entries()
                if e["state"] in (VALIDATING, CANDIDATE_STAGED, AWAITING_AUTHORIZATION,
                                  AUTHORIZED, ACTIVATING, VERIFYING)]

    def summary(self) -> "OrderedDict[str, Any]":
        counts: "OrderedDict[str, int]" = OrderedDict((s, 0) for s in STATES)
        for e in self.entries():
            counts[str(e["state"])] = counts.get(str(e["state"]), 0) + 1
        return OrderedDict((
            ("root", str(self.root)),
            ("entries", sum(counts.values())),
            ("by_state", counts),
            ("ready", [e["entry_id"] for e in self.ready()]),
            ("in_flight", [e["entry_id"] for e in self.in_flight()]),
        ))

    # ---- the activation lease --------------------------------------------- #
    @property
    def _lease_path(self) -> Path:
        return self.root / "activation.lease"

    def acquire_activation(self, holder: str, *, ttl_seconds: int = 1800,
                           now: Optional[float] = None) -> "OrderedDict[str, Any]":
        """One holder at a time for the CURRENT LIVE -> NEXT LIVE transition.

        The lease protects the flip, not the preparation: another market may be
        sealing, validating and staging while this one is held. It carries a
        TTL so a crashed holder cannot block the factory forever, and expiry is
        recorded rather than silent.
        """
        now = time.time() if now is None else now
        current = self.read_activation()
        if current and not current["expired"]:
            if current["holder"] == holder:
                return current
            raise QueueError(LEASE_HELD, "held by %s until %s"
                             % (current["holder"], current["expires_at"]))
        doc = OrderedDict((
            ("schema", LEASE_SCHEMA),
            ("holder", holder),
            ("acquired_at", _now()),
            ("acquired_epoch", round(now, 3)),
            ("ttl_seconds", int(ttl_seconds)),
            ("expires_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + ttl_seconds))),
            ("expires_epoch", round(now + ttl_seconds, 3)),
            ("took_over_from", current["holder"] if current else None),
        ))
        _write_json(self._lease_path, doc)
        out = OrderedDict(doc)
        out["expired"] = False
        return out

    def read_activation(self, now: Optional[float] = None) -> Optional["OrderedDict[str, Any]"]:
        if not self._lease_path.is_file():
            return None
        doc = json.loads(self._lease_path.read_text(encoding="utf-8-sig"),
                         object_pairs_hook=OrderedDict)
        now = time.time() if now is None else now
        doc["expired"] = now >= float(doc.get("expires_epoch") or 0)
        return doc

    def release_activation(self, holder: str) -> None:
        current = self.read_activation()
        if current is None:
            return
        if current["holder"] != holder and not current["expired"]:
            raise QueueError(LEASE_NOT_HELD, "%s does not hold the lease" % holder)
        self._lease_path.unlink(missing_ok=True)


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover - CLI
    parser = argparse.ArgumentParser(description="ATLAS-THROUGHPUT-006 -- the release-ready queue")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    p = sub.add_parser("submit")
    p.add_argument("--market", required=True)
    p.add_argument("--package-digest", required=True)
    p.add_argument("--package-id", default="")
    p = sub.add_parser("transition")
    p.add_argument("--entry", required=True)
    p.add_argument("--to", required=True, choices=STATES)
    args = parser.parse_args(argv)
    queue = ReleaseQueue()
    if args.command == "list":
        print(SMP.canonical_json(queue.summary()))
        return 0
    if args.command == "submit":
        print(SMP.canonical_json(queue.submit(market_id=args.market,
                                              package_digest=args.package_digest,
                                              package_id=args.package_id)))
        return 0
    if args.command == "transition":
        print(SMP.canonical_json(queue.transition(args.entry, args.to)))
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

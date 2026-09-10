"""Which registered markets the founder has authorized for a production launch.

WHY THIS EXISTS
---------------
``select_markets`` asks whether a market CAN assemble: census present, final
partition present, policy authority present, minimum published met. Those are
source facts. Whether a source-ready market SHOULD be in a launch is a founder
decision, and until PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046 nothing
recorded one: Indianapolis, with eight approved profiles, joined the composed
bundle the moment it cleared its own five-hotel floor. The founder withdrew it
from the first multi-market launch -- coverage, not correctness -- and every
lever that existed (its release contract, its market contract, its data) was
source authority that a participation decision must not touch.

This file is the missing lever. It is read at assembly time, it states a
status for EVERY registered market, and only ``FOUNDER_AUTHORIZED_FOR_LAUNCH``
admits a market into the composed production bundle. Source readiness is still
reported on its own (``assemblable``), so a withdrawn market reads as
``SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`` rather than as broken,
and its own per-market assembly (``assemble_netlify_bundle --market``) is not
affected at all.

Fail closed. A registered market with no row is not authorized, and the
assembler gate ``global.launch_participation_explicit`` refuses a bundle built
while any registered market is unlisted, so an omission is loud rather than a
silent exclusion. A second gate refuses a record whose statuses disagree with
what the source actually says (a market marked source-ready that is not, or
the reverse), so the record cannot drift into fiction.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
PARTICIPATION_PATH = (REPO_ROOT / "deploy" / "netlify"
                      / "launch_participation.json")
PARTICIPATION_SCHEMA = "ptf-launch-participation/1.0"

#: Where a documented, time-boxed gap in the decision chain is recorded. See
#: :func:`decision_problems`.
LINEAGE_REPAIR_PATH = (REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
                       / "reports"
                       / "nashville_tn_participation_lineage_defect_005.json")

#: What every decision block must carry. The first four were always checked.
#: ``supersedes`` and ``lineage`` were not, and
#: PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 dropped them by
#: rebuilding the block from scratch instead of extending the committed one.
#: Nothing complained, because nothing asked -- which is the actual defect.
DECISION_REQUIRED = ("work_order", "decided_by", "decided_on", "reason")
DECISION_CHAIN_REQUIRED = ("supersedes", "lineage")

LINEAGE_NOTE = (
    "Every participation record this one descends from, oldest first, so a "
    "deployment authorization can still be matched to the record it signed "
    "after more than one reissue. supersedes names only the immediate "
    "predecessor, which stops being enough at the second reissue.")

#: The founder has authorized this market for the composed production bundle.
#: The ONLY status that admits a market.
FOUNDER_AUTHORIZED_FOR_LAUNCH = "FOUNDER_AUTHORIZED_FOR_LAUNCH"
#: The market's source passes every assembly condition; the founder has not
#: authorized it for this launch. Nothing about the market is wrong.
SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH = (
    "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH")
#: The market's source does not pass every assembly condition. A founder
#: authorization would not admit it either; the source has to be ready first.
NOT_SOURCE_READY = "NOT_SOURCE_READY"
#: Not a status anyone may write: what an unlisted registered market reads as.
UNLISTED = "UNLISTED"

LAUNCH_STATUSES = (
    FOUNDER_AUTHORIZED_FOR_LAUNCH,
    SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH,
    NOT_SOURCE_READY,
)
#: Which statuses claim the market's source is ready, for the agreement gate.
_CLAIMS_SOURCE_READY = {
    FOUNDER_AUTHORIZED_FOR_LAUNCH: True,
    SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH: True,
    NOT_SOURCE_READY: False,
}


class LaunchParticipationError(RuntimeError):
    """The record is missing, malformed, or names a market nobody registered."""


def participation_sha256(path: Optional[Path] = None) -> str:
    return hashlib.sha256((path or PARTICIPATION_PATH).read_bytes()).hexdigest()


def load_participation(path: Optional[Path] = None) -> Dict:
    """The committed record, validated for shape. Registration is checked
    separately by :func:`verify_participation` because it needs the registry."""
    path = path or PARTICIPATION_PATH
    if not path.is_file():
        raise LaunchParticipationError(
            "no launch participation record at %s -- without it no market is "
            "founder-authorized and the composed bundle is empty" % path)
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != PARTICIPATION_SCHEMA:
        raise LaunchParticipationError(
            "%s: schema is %r, expected %r"
            % (path.name, doc.get("schema"), PARTICIPATION_SCHEMA))
    rows = doc.get("markets")
    if not isinstance(rows, list) or not rows:
        raise LaunchParticipationError("%s: markets must be a non-empty list" % path.name)
    seen = set()
    for row in rows:
        mid = row.get("market_id")
        status = row.get("launch_status")
        if not isinstance(mid, str) or not mid:
            raise LaunchParticipationError("%s: a row has no market_id" % path.name)
        if mid in seen:
            raise LaunchParticipationError("%s: %s listed twice" % (path.name, mid))
        seen.add(mid)
        if status not in LAUNCH_STATUSES:
            raise LaunchParticipationError(
                "%s: %s has launch_status %r, expected one of %s"
                % (path.name, mid, status, list(LAUNCH_STATUSES)))
    decision = doc.get("decision") or {}
    for key in DECISION_REQUIRED:
        if not decision.get(key):
            raise LaunchParticipationError(
                "%s: decision.%s is required -- a participation set with no "
                "recorded decision is a list nobody owns" % (path.name, key))
    problems = decision_problems(doc, path=path)
    if problems:
        raise LaunchParticipationError(
            "%s: the decision chain is broken:\n  %s" % (path.name, "\n  ".join(problems)))
    return doc


# --------------------------------------------------------------------------- #
# The decision chain.
# --------------------------------------------------------------------------- #

def _authorized_of(doc: Mapping) -> List[str]:
    return sorted(row["market_id"] for row in doc["markets"]
                  if row["launch_status"] == FOUNDER_AUTHORIZED_FOR_LAUNCH)


def decision_record(doc: Mapping, sha256: str) -> "OrderedDict[str, object]":
    """One lineage record for the decision ``doc`` holds, pinned at ``sha256``.

    The sha is the hash of the participation file AS THAT DECISION WROTE IT,
    which is what a deployment authorization signed. It is never recomputed
    from a later state of the file.
    """
    return OrderedDict((
        ("work_order", doc["decision"]["work_order"]),
        ("sha256", sha256),
        ("founder_authorized", _authorized_of(doc)),
    ))


def extend_decision(previous: Mapping, previous_sha256: str, *, work_order: str,
                    decided_by: str, decided_on: str, reason: str,
                    path: Optional[Path] = None,
                    **extra: object) -> "OrderedDict[str, object]":
    """The next decision block, built by EXTENDING ``previous`` -- never afresh.

    This exists because writing the block from scratch is exactly how
    ``supersedes`` and ``lineage`` were lost. A writer that calls this cannot
    drop them: the predecessor becomes the newest ancestor and the chain it
    carried comes forward whole. ``extra`` keys are the decision's own fields
    (which markets moved, what was withheld) and are written between the reason
    and the chain, so the chain is always the last thing in the block and is
    visibly not the writer's to invent.

    Pass ``path`` when extending a record on disk. If that record is the one a
    repair record covers -- because an earlier launch dropped its chain -- the
    ancestors come from the repair, so the very next write puts the chain back
    instead of starting a new one-link chain that quietly loses eight orders.
    """
    prior = previous.get("decision") or {}
    ancestors = (prior.get("lineage") or {}).get("records")
    if ancestors is None and path is not None and _repair_covers(path) is not None:
        ancestors = decision_chain(previous, path)["records"]
    records = [OrderedDict(r) for r in (ancestors or [])]
    predecessor = decision_record(previous, previous_sha256)
    if any(r["sha256"] == predecessor["sha256"] for r in records):
        raise LaunchParticipationError(
            "the predecessor %s is already an ancestor; a decision may not "
            "supersede itself" % predecessor["sha256"])
    records.append(predecessor)

    block: "OrderedDict[str, object]" = OrderedDict((
        ("work_order", work_order),
        ("decided_by", decided_by),
        ("decided_on", decided_on),
        ("reason", reason),
    ))
    for key, value in extra.items():
        block[key] = value
    block["supersedes"] = predecessor
    block["lineage"] = OrderedDict((
        ("what_this_is", (prior.get("lineage") or {}).get("what_this_is") or LINEAGE_NOTE),
        ("records", records),
    ))
    return block


def _repair_covers(path: Path) -> Optional[Dict]:
    """The repair record, when it describes exactly the file at ``path``.

    A repair record is the ONE way a decision block may lack its chain: the
    participation record is sha256-bound into the live deployment
    authorization, so a block dropped by an already-shipped launch cannot be
    put back until the next write. The repair must name the exact record it
    covers -- a stale one proves nothing and is treated as absent.
    """
    if not LINEAGE_REPAIR_PATH.is_file():
        return None
    doc = json.loads(LINEAGE_REPAIR_PATH.read_text(encoding="utf-8-sig"))
    if doc.get("current_participation_sha256") != participation_sha256(path):
        return None
    should = doc.get("what_the_current_file_should_have_carried") or {}
    if not should.get("supersedes") or not (should.get("lineage") or {}).get("records"):
        return None
    return doc


def decision_chain(doc: Optional[Mapping] = None, path: Optional[Path] = None) -> Dict:
    """``{"supersedes", "records", "carried_by"}`` for the current decision.

    Reads whichever file currently carries the chain, so what callers assert
    does not depend on which one that is.
    """
    path = path or PARTICIPATION_PATH
    doc = doc if doc is not None else json.loads(path.read_text(encoding="utf-8-sig"))
    decision = doc.get("decision") or {}
    if decision.get("supersedes") and (decision.get("lineage") or {}).get("records"):
        return {"supersedes": decision["supersedes"],
                "records": decision["lineage"]["records"],
                "carried_by": path.name}
    repair = _repair_covers(path)
    if repair is None:
        raise LaunchParticipationError(
            "%s carries no decision chain and no repair record covers it" % path.name)
    should = repair["what_the_current_file_should_have_carried"]
    return {"supersedes": should["supersedes"],
            "records": should["lineage"]["records"],
            "carried_by": LINEAGE_REPAIR_PATH.name}


def decision_problems(doc: Mapping, path: Optional[Path] = None) -> List[str]:
    """Everything wrong with the decision chain, or an empty list.

    The FIRST decision has no predecessor and needs no chain. Every later one
    does, and these are the rules a deployment authorization relies on when it
    matches itself to the record it signed several reissues back.
    """
    path = path or PARTICIPATION_PATH
    decision = doc.get("decision") or {}
    problems: List[str] = []
    carried = bool(decision.get("supersedes")) and bool(
        (decision.get("lineage") or {}).get("records"))
    if not carried:
        if _repair_covers(path) is None:
            missing = [k for k in DECISION_CHAIN_REQUIRED if not decision.get(k)]
            return ["decision.%s is missing and no repair record covers this "
                    "participation record -- an authorization signed before the "
                    "last reissue can no longer be matched to what it bound" % key
                    for key in missing]
        return []

    supersedes = decision["supersedes"]
    records = decision["lineage"]["records"]
    shas = [r.get("sha256") for r in records]
    if len(shas) != len(set(shas)):
        problems.append("decision.lineage repeats a record")
    if any(not isinstance(s, str) or len(s) != 64 for s in shas):
        problems.append("decision.lineage has a record with no sha256")
    counts = [len(r.get("founder_authorized") or []) for r in records]
    if counts != sorted(counts):
        problems.append("decision.lineage shrinks the authorized set: %s" % counts)
    if path.is_file() and participation_sha256(path) in shas:
        problems.append("decision.lineage contains the CURRENT record; a decision "
                        "may not be its own ancestor")
    if shas and supersedes.get("sha256") != shas[-1]:
        problems.append("decision.supersedes names %r but the newest ancestor is %r"
                        % (supersedes.get("sha256"), shas[-1]))
    lost = set(supersedes.get("founder_authorized") or []) - set(_authorized_of(doc))
    if lost:
        problems.append("this decision drops market(s) the previous one authorized: %s"
                        % sorted(lost))
    return problems


def launch_status(market_id: str, doc: Optional[Mapping] = None) -> str:
    """The recorded status, or ``UNLISTED`` (never authorized) when absent."""
    doc = doc if doc is not None else load_participation()
    for row in doc["markets"]:
        if row["market_id"] == market_id:
            return row["launch_status"]
    return UNLISTED


def is_founder_authorized(market_id: str, doc: Optional[Mapping] = None) -> bool:
    return launch_status(market_id, doc) == FOUNDER_AUTHORIZED_FOR_LAUNCH


def authorized_market_ids(doc: Optional[Mapping] = None) -> List[str]:
    doc = doc if doc is not None else load_participation()
    return sorted(row["market_id"] for row in doc["markets"]
                  if row["launch_status"] == FOUNDER_AUTHORIZED_FOR_LAUNCH)


def verify_participation(registered_market_ids: Iterable[str],
                         source_ready: Mapping[str, bool],
                         doc: Optional[Mapping] = None) -> "OrderedDict[str, List[str]]":
    """What the record disagrees with, per check, each ``[]`` when clean.

    ``unlisted``: registered markets with no row (fail closed -- they are not
    authorized, but the silence is what the gate refuses).
    ``unregistered``: rows naming a market the registry does not know.
    ``source_disagreement``: rows whose status claims a source readiness the
    assembler did not find (``source_ready`` is ``assemblable`` per market).
    """
    doc = doc if doc is not None else load_participation()
    registered = sorted(set(registered_market_ids))
    listed = {row["market_id"]: row["launch_status"] for row in doc["markets"]}
    unlisted = [mid for mid in registered if mid not in listed]
    unregistered = sorted(mid for mid in listed if mid not in set(registered))
    disagreement = []
    for mid in registered:
        status = listed.get(mid)
        if status is None or mid not in source_ready:
            continue
        if _CLAIMS_SOURCE_READY[status] != bool(source_ready[mid]):
            disagreement.append(
                "%s: recorded %s but source %s assemblable"
                % (mid, status, "IS" if source_ready[mid] else "is NOT"))
    return OrderedDict([
        ("unlisted", unlisted),
        ("unregistered", unregistered),
        ("source_disagreement", disagreement),
    ])


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover
    doc = load_participation()
    print(json.dumps(OrderedDict([
        ("schema", doc["schema"]),
        ("sha256", participation_sha256()),
        ("decision", doc["decision"]),
        ("authorized", authorized_market_ids(doc)),
        ("markets", [(r["market_id"], r["launch_status"]) for r in doc["markets"]]),
    ]), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

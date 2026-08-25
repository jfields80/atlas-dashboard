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
    for key in ("work_order", "decided_by", "decided_on", "reason"):
        if not decision.get(key):
            raise LaunchParticipationError(
                "%s: decision.%s is required -- a participation set with no "
                "recorded decision is a list nobody owns" % (path.name, key))
    return doc


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

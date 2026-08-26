"""Does each paid lane actually authenticate, right now?

WHY A LIVE PROBE AND NOT A HEALTH CHECK
---------------------------------------
:mod:`providers` already exposes ``health_check``, and every one of them asks
the same question: is the credential PRESENT. That question was the right one
while the environment held no credential at all, and it is the wrong one the
moment a credential exists but is wrong. PTF-ST-LOUIS-PAID-ACQUISITION-002 ran
into exactly that gap: all three lanes reported healthy, and one of them
answered ``407 Auth Failed (wrong_password)`` on its first real connection.

So each probe here makes ONE cheap authenticated call to the vendor and reports
what the vendor said.

THE THREE LANES DO NOT SHARE A SECRET
-------------------------------------
This is the fact that makes a per-lane probe necessary rather than tidy.

* Firecrawl authenticates with ``FIRECRAWL_API_KEY``.
* The Bright Data **Browser API** authenticates with the zone username and
  password in ``BRIGHTDATA_BROWSER_AUTH``, presented to ``brd.superproxy.io``.
* The Bright Data **Web Unlocker** authenticates with the ``brightdata`` CLI's
  own stored API token and never reads ``BRIGHTDATA_BROWSER_AUTH`` at all --
  verified by running it with that variable removed from the environment.

Both Bright Data lanes are billed to one account, which is what invites the
assumption that one working proves the other. It does not. A passing Web
Unlocker probe is evidence about the CLI token and about nothing else.

COST
----
Firecrawl's credit endpoint is free and consumes no credit. The Browser API
probe opens a session and loads Bright Data's own geolocation echo, a few
kilobytes. The Web Unlocker probe fetches the same document. The whole
preflight is a rounding error against any capture budget, and it is metered
anyway: a balance snapshot is taken before and after so the run reports what it
actually cost rather than asserting that it was free.

NOTHING HERE PRINTS A CREDENTIAL. Every vendor string passes through
``client.redact`` before it reaches a dict, and a test asserts the report is
clean.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS   # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC     # noqa: E402
from scripts.pettripfinder.brightdata import client                    # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC    # noqa: E402

CONTRACT = "ptf-lane-preflight/1.0"

#: The lanes a market work order is allowed to spend money on.
PAID_LANES: Tuple[str, ...] = (PROVIDERS.FIRECRAWL,
                               PROVIDERS.BRIGHTDATA_BROWSER,
                               PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)

#: Which environment secret each lane actually presents. Recorded by NAME only.
LANE_SECRET: Dict[str, str] = {
    PROVIDERS.FIRECRAWL: FC.KEY_ENV,
    PROVIDERS.BRIGHTDATA_BROWSER: client.AUTH_ENV,
    PROVIDERS.BRIGHTDATA_WEB_UNLOCKER:
        "%s CLI stored token (independent of %s)" % (client.CLI_NAME,
                                                     client.AUTH_ENV),
}

PASS = "AUTHENTICATED"
FAIL_AUTH = "AUTHENTICATION_REJECTED"
FAIL_UNREACHABLE = "LANE_UNREACHABLE"
FAIL_ABSENT = "CREDENTIAL_ABSENT"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LaneProbe:
    """One lane, one live call, one verdict."""

    lane: str
    verdict: str
    detail: str = ""
    seconds: float = 0.0
    #: Whatever the lane can honestly say about itself: credits, exit country.
    observed: Dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.verdict == PASS

    def to_dict(self) -> Dict:
        return client.redact({
            "lane": self.lane,
            "presents_secret": LANE_SECRET.get(self.lane, "unknown"),
            "verdict": self.verdict,
            "ok": self.ok,
            "detail": self.detail,
            "seconds": round(self.seconds, 2),
            "observed": self.observed,
        })


# --------------------------------------------------------------------------- #
# The three probes.
# --------------------------------------------------------------------------- #

def probe_firecrawl() -> LaneProbe:
    """Read the team credit balance. Authenticated, free, consumes no credit."""
    started = time.monotonic()
    if not FC.credential_present():
        return LaneProbe(PROVIDERS.FIRECRAWL, FAIL_ABSENT,
                         "%s is not set" % FC.KEY_ENV,
                         time.monotonic() - started)
    try:
        credits = FC.credits_remaining()
    except Exception as exc:                                     # noqa: BLE001
        message = FC.redact("%s: %s" % (type(exc).__name__, exc))[:400]
        verdict = (FAIL_AUTH if _looks_like_auth_rejection(message)
                   else FAIL_UNREACHABLE)
        return LaneProbe(PROVIDERS.FIRECRAWL, verdict, message,
                         time.monotonic() - started)
    if credits is None:
        return LaneProbe(PROVIDERS.FIRECRAWL, FAIL_UNREACHABLE,
                         "the credit endpoint returned no figure",
                         time.monotonic() - started)
    return LaneProbe(PROVIDERS.FIRECRAWL, PASS,
                     "credit endpoint answered",
                     time.monotonic() - started,
                     {"credits_remaining": credits,
                      "endpoint": FC.CREDITS_URL})


def probe_brightdata_browser() -> LaneProbe:
    """Open one real session and read Bright Data's own geolocation echo.

    Uses :func:`browser_capture.probe_exit_country`, which is the same call
    every capture batch makes before it spends anything, so a pass here is a
    pass on the path that matters. One successful read is enough to answer the
    authentication question; proving the exit geography is a separate concern
    with a stricter setting.
    """
    started = time.monotonic()
    if not client.credential_present():
        return LaneProbe(PROVIDERS.BRIGHTDATA_BROWSER, FAIL_ABSENT,
                         "%s is not set" % client.AUTH_ENV,
                         time.monotonic() - started)
    try:
        probe = asyncio.run(BC.probe_exit_country(reads=1, max_sessions=3))
    except Exception as exc:                                     # noqa: BLE001
        return LaneProbe(PROVIDERS.BRIGHTDATA_BROWSER, FAIL_UNREACHABLE,
                         client.redact("%s: %s" % (type(exc).__name__, exc))[:400],
                         time.monotonic() - started)
    detail = client.redact(probe.detail)[:600]
    if probe.ok:
        return LaneProbe(PROVIDERS.BRIGHTDATA_BROWSER, PASS,
                         "session opened and reported its exit country",
                         time.monotonic() - started,
                         {"exit_country": probe.country,
                          "expected": probe.expected})
    verdict = FAIL_AUTH if _looks_like_auth_rejection(detail) else FAIL_UNREACHABLE
    return LaneProbe(PROVIDERS.BRIGHTDATA_BROWSER, verdict, detail,
                     time.monotonic() - started,
                     {"expected": probe.expected})


def probe_brightdata_web_unlocker() -> LaneProbe:
    """One CLI fetch of the same echo document, through the first zone."""
    started = time.monotonic()
    import shutil
    if not shutil.which(client.CLI_NAME):
        return LaneProbe(PROVIDERS.BRIGHTDATA_WEB_UNLOCKER, FAIL_ABSENT,
                         "the %r CLI is not on PATH" % client.CLI_NAME,
                         time.monotonic() - started)
    zone = UC.UNLOCKER_ZONES[0]
    with tempfile.TemporaryDirectory() as staging:
        destination = Path(staging) / "preflight.json"
        ok, detail = UC._run_scrape(client.GEO_PROBE_URL, zone, destination)
        body = (destination.read_text(encoding="utf-8", errors="replace")
                if destination.exists() else "")
    detail = client.redact(detail)[:400]
    if not ok or not body.strip():
        verdict = FAIL_AUTH if _looks_like_auth_rejection(detail) else FAIL_UNREACHABLE
        return LaneProbe(PROVIDERS.BRIGHTDATA_WEB_UNLOCKER, verdict,
                         detail or "the zone returned an empty document",
                         time.monotonic() - started, {"zone": zone})
    observed: Dict = {"zone": zone, "bytes": len(body)}
    try:
        payload = json.loads(body)
        if isinstance(payload, dict):
            observed["exit_country"] = str(payload.get("country", "")).lower()
    except Exception:                                            # noqa: BLE001
        pass
    return LaneProbe(PROVIDERS.BRIGHTDATA_WEB_UNLOCKER, PASS,
                     "zone %s returned a document" % zone,
                     time.monotonic() - started, observed)


_AUTH_MARKERS: Tuple[str, ...] = (
    "auth failed", "wrong_password", "wrong customer password", "unauthorized",
    "invalid api key", "invalid token", "forbidden", " 401", " 403", " 407",
    "authentication", "payment required", " 402",
)


def _looks_like_auth_rejection(detail: str) -> bool:
    """Whether the vendor refused the CREDENTIAL rather than the request.

    A distinction worth drawing, because the two have different owners: an
    authentication rejection is fixed by whoever holds the secret and a lane
    that is merely unreachable may fix itself.
    """
    low = (detail or "").lower()
    return any(marker in low for marker in _AUTH_MARKERS)


# --------------------------------------------------------------------------- #
# The whole preflight.
# --------------------------------------------------------------------------- #

_PROBES = {
    PROVIDERS.FIRECRAWL: probe_firecrawl,
    PROVIDERS.BRIGHTDATA_BROWSER: probe_brightdata_browser,
    PROVIDERS.BRIGHTDATA_WEB_UNLOCKER: probe_brightdata_web_unlocker,
}


def run(lanes: Tuple[str, ...] = PAID_LANES, *, label: str = "lane preflight") -> Dict:
    """Probe every lane and meter what the probing itself cost.

    The balance is read before and after because the account balance is the
    hard ceiling on any paid work order, and because a preflight that claims
    to be free without measuring is the same class of statement this module
    exists to stop making.
    """
    before = client.read_usage("%s (before)" % label)
    probes: List[LaneProbe] = [_PROBES[lane]() for lane in lanes]
    after = client.read_usage("%s (after)" % label)

    failures = [p for p in probes if not p.ok]
    return client.redact({
        "contract": CONTRACT,
        "label": label,
        "probed_at": _now(),
        "lanes": [p.to_dict() for p in probes],
        "all_lanes_authenticated": not failures,
        "failed_lanes": [p.lane for p in failures],
        "authentication_rejections": [p.lane for p in probes
                                      if p.verdict == FAIL_AUTH],
        "account": {
            "before": before.to_dict(),
            "after": after.to_dict(),
            "delta": client.delta(before, after),
        },
    })


def gate(report: Dict, *, required: Tuple[str, ...] = PAID_LANES) -> Tuple[bool, str]:
    """May a paid cohort start? Returns (may_start, reason).

    Fails CLOSED: a lane that could not be probed is not a lane that may be
    spent on.
    """
    by_lane = {row["lane"]: row for row in report.get("lanes", ())}
    missing = [lane for lane in required if lane not in by_lane]
    if missing:
        return False, "not probed: %s" % ", ".join(sorted(missing))
    bad = [lane for lane in required if not by_lane[lane]["ok"]]
    if bad:
        return False, "; ".join("%s: %s -- %s" % (lane, by_lane[lane]["verdict"],
                                                  by_lane[lane]["detail"][:160])
                                for lane in bad)
    return True, "all %d required lanes authenticated" % len(required)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=None,
                        help="write the report here as JSON")
    parser.add_argument("--label", default="lane preflight")
    parser.add_argument("--lane", action="append", choices=list(PAID_LANES),
                        help="probe only this lane; repeatable")
    args = parser.parse_args(argv)

    lanes = tuple(args.lane) if args.lane else PAID_LANES
    report = run(lanes, label=args.label)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)

    may_start, reason = gate(report, required=lanes)
    print("\nGATE: %s -- %s" % ("PASS" if may_start else "STOP", reason),
          file=sys.stderr)
    return 0 if may_start else 1


__all__ = ["CONTRACT", "PAID_LANES", "LANE_SECRET", "PASS", "FAIL_AUTH",
           "FAIL_UNREACHABLE", "FAIL_ABSENT", "LaneProbe", "probe_firecrawl",
           "probe_brightdata_browser", "probe_brightdata_web_unlocker",
           "run", "gate", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

"""The Bright Data credential, the endpoint it builds, and the usage meter.

THE CREDENTIAL NEVER LEAVES THIS MODULE AS PLAINTEXT
----------------------------------------------------
``BRIGHTDATA_BROWSER_AUTH`` holds the Browser API userinfo and host in the form
``wss://<auth>`` expects. It is read here and nowhere else, and everything this
package writes to disk passes through :func:`redact` first.

That is not decoration. Playwright puts the endpoint it failed to reach into
the exception message, so an unredacted ``str(exc)`` in an attempt record
commits the password to git. :func:`redact` removes the whole auth string, the
userinfo half, and the user and password independently, longest fragment
first, so a partially-quoted endpoint is caught as well as a whole one.

WHAT THIS MODULE WILL NOT RUN
-----------------------------
``brightdata zones info <zone>`` returns the zone's password in its JSON. This
module therefore holds an ALLOWLIST of CLI invocations and that command is not
on it. Metering needs cost and bandwidth, which ``budget`` reports without ever
naming a secret.

BILLING LAG IS REPORTED, NEVER GUESSED
--------------------------------------
Bright Data's zone statistics are month-to-date and do not update instantly. A
snapshot therefore records what the API actually said at a moment, and the
caller compares two snapshots. When the two are equal the honest report is
PENDING, not "$0.00 spent".

Money is integer minor units (cents) everywhere, matching the house rule in
``policy_observation._money_is_integer``: a float cost that later gets summed
is a rounding error with a dollar sign in front of it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence, Tuple

#: The environment variable holding the Browser API auth + endpoint.
AUTH_ENV = "BRIGHTDATA_BROWSER_AUTH"

#: The Browser API zone this pilot bills against.
ZONE = "scraping_browser1"

CLI_NAME = "brightdata"

#: CLI invocations this module may make. ``zones info`` is deliberately absent:
#: it returns the zone password. An allowlist rather than a denylist, because a
#: future subcommand that leaks a secret should fail closed here rather than
#: silently work.
ALLOWED_CLI_ARGS: Tuple[Tuple[str, ...], ...] = (
    ("budget", "balance"),
    ("budget", "zone"),
)

REDACTED = "<redacted:brightdata-credential>"

#: Decimal units, which is how Bright Data's console reports bandwidth.
_UNIT_BYTES: Dict[str, int] = {
    "B": 1, "KB": 10 ** 3, "MB": 10 ** 6, "GB": 10 ** 9, "TB": 10 ** 12,
}

_MONEY_RE = re.compile(r"\$\s*(-?[\d,]+(?:\.\d+)?)")
_BW_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(TB|GB|MB|KB|B)\b", re.IGNORECASE)


class BrightDataCredentialError(RuntimeError):
    """The Browser API credential is absent or unusable."""


class BrightDataUsageError(RuntimeError):
    """A metering call was refused. Never raised into a capture batch."""


# --------------------------------------------------------------------------- #
# Credential handling.
# --------------------------------------------------------------------------- #

def credential_present() -> bool:
    """Whether the credential is available, without revealing anything."""
    return bool((os.environ.get(AUTH_ENV) or "").strip())


def _secret_fragments() -> Tuple[str, ...]:
    """Every substring whose appearance in output would be a leak.

    Longest first, so that redacting the userinfo does not leave a bare
    password behind, and vice versa.
    """
    auth = (os.environ.get(AUTH_ENV) or "").strip()
    if not auth:
        return ()
    fragments = {auth, "wss://" + auth}
    userinfo = auth.split("@", 1)[0]
    if userinfo:
        fragments.add(userinfo)
        if ":" in userinfo:
            user, password = userinfo.rsplit(":", 1)
            for part in (user, password):
                # Very short fragments would redact ordinary prose instead.
                if len(part) > 3:
                    fragments.add(part)
    return tuple(sorted((f for f in fragments if f), key=len, reverse=True))


def redact(value):
    """Remove every credential fragment from a string, recursing into
    containers. Anything this package writes to disk goes through here."""
    if isinstance(value, str):
        out = value
        for fragment in _secret_fragments():
            out = out.replace(fragment, REDACTED)
        return out
    if isinstance(value, dict):
        return {redact(k): redact(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(redact(v) for v in value)
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def contains_credential(value) -> bool:
    """Whether any credential fragment survives in ``value``.

    Used by the tests that guard every manifest and report before it is
    staged.
    """
    fragments = _secret_fragments()
    if not fragments:
        return False
    if isinstance(value, str):
        return any(f in value for f in fragments)
    if isinstance(value, dict):
        return any(contains_credential(k) or contains_credential(v)
                   for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(contains_credential(v) for v in value)
    return False


def browser_endpoint() -> str:
    """The ``wss://`` endpoint Playwright connects to.

    Returned as a value and never logged. Callers must not put it into an
    exception message, a manifest, or a print.
    """
    auth = (os.environ.get(AUTH_ENV) or "").strip()
    if not auth:
        raise BrightDataCredentialError(
            "%s is not set; this pilot cannot reach the Browser API. The "
            "credential is read from the environment and is never written to "
            "a file in this repository." % AUTH_ENV)
    if auth.startswith("wss://") or auth.startswith("ws://"):
        return auth
    return "wss://" + auth


# --------------------------------------------------------------------------- #
# Usage metering.
# --------------------------------------------------------------------------- #

def money_to_minor(text: str) -> Optional[int]:
    """``"$0.95"`` -> ``95``. ``None`` when no amount is present.

    Rounded to the nearest cent rather than truncated: Bright Data reports
    dollars to two places, so this is a parse and not an estimate.
    """
    match = _MONEY_RE.search(text or "")
    if not match:
        return None
    return int(round(float(match.group(1).replace(",", "")) * 100))


def bandwidth_to_bytes(text: str) -> Optional[int]:
    """``"107.4 MB"`` -> ``107400000``, using DECIMAL units.

    The console's own convention. Recorded everywhere alongside the raw display
    string, so a reader can check the conversion rather than trust it.
    """
    match = _BW_RE.search(text or "")
    if not match:
        return None
    value = float(match.group(1).replace(",", ""))
    return int(round(value * _UNIT_BYTES[match.group(2).upper()]))


def _line_after(text: str, label: str) -> str:
    """The remainder of the first line whose start matches ``label``."""
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(label.lower()):
            return stripped[len(label):].strip()
    return ""


def parse_zone_budget(text: str) -> Dict[str, object]:
    """Read ``brightdata budget zone <name>`` human output.

    The installed CLI (0.3.5) ignores ``--json`` for this subcommand, so the
    human table is the only surface available. Parsed by LABEL rather than by
    line position, so a reordered or extended table still reads correctly and a
    missing label yields ``None`` instead of a wrong number.
    """
    cost_line = _line_after(text, "Cost (this month):")
    bandwidth_line = _line_after(text, "Bandwidth used:")
    return {
        "cost_month_usd_minor": money_to_minor(cost_line),
        "bandwidth_bytes": bandwidth_to_bytes(bandwidth_line),
        "bandwidth_display": bandwidth_line,
        "cost_display": cost_line,
    }


def parse_balance(text: str) -> Dict[str, object]:
    """Read ``brightdata budget balance`` human output."""
    return {
        "balance_usd_minor": money_to_minor(_line_after(text, "Balance")),
        "pending_charge_usd_minor": money_to_minor(
            _line_after(text, "Pending charge")),
    }


@dataclass(frozen=True)
class UsageSnapshot:
    """What Bright Data reported about the zone at one instant.

    ``available`` is False when the CLI could not be reached or the numbers
    could not be parsed. A failed snapshot still exists and still carries its
    notes: "we could not measure" is a result and is reported as one.
    """

    label: str
    captured_at: str
    zone: str
    available: bool
    cost_month_usd_minor: Optional[int] = None
    bandwidth_bytes: Optional[int] = None
    bandwidth_display: str = ""
    cost_display: str = ""
    balance_usd_minor: Optional[int] = None
    pending_charge_usd_minor: Optional[int] = None
    notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "captured_at": self.captured_at,
            "zone": self.zone,
            "available": self.available,
            "cost_month_usd_minor": self.cost_month_usd_minor,
            "bandwidth_bytes": self.bandwidth_bytes,
            "bandwidth_display": self.bandwidth_display,
            "cost_display": self.cost_display,
            "balance_usd_minor": self.balance_usd_minor,
            "pending_charge_usd_minor": self.pending_charge_usd_minor,
            "notes": list(self.notes),
            "unit_convention": ("bandwidth parsed with decimal units "
                                "(1 MB = 1e6 bytes); money in integer cents"),
        }


CliRunner = Callable[[Sequence[str]], Tuple[int, str]]


def _default_runner(args: Sequence[str]) -> Tuple[int, str]:
    """Run the Bright Data CLI, allowlist-checked.

    ``shutil.which`` is required on Windows: the npm global is a ``.CMD`` shim
    and ``CreateProcess`` will not find it from a bare name.
    """
    head = tuple(args[:2])
    if head not in ALLOWED_CLI_ARGS:
        raise BrightDataUsageError(
            "refusing to run 'brightdata %s'; only %s are allowed, because "
            "other subcommands (notably 'zones info') return the zone password"
            % (" ".join(args), [" ".join(a) for a in ALLOWED_CLI_ARGS]))
    executable = shutil.which(CLI_NAME)
    if not executable:
        raise BrightDataUsageError("the %r CLI is not on PATH" % CLI_NAME)
    completed = subprocess.run([executable, *args], capture_output=True,
                               text=True, timeout=120)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def read_usage(label: str, *, zone: str = ZONE,
               runner: Optional[CliRunner] = None,
               now: Optional[Callable[[], datetime]] = None) -> UsageSnapshot:
    """One usage snapshot. Never raises into a capture batch.

    ``runner`` and ``now`` are injected so the parsing is testable without the
    network and without the clock.
    """
    run = runner or _default_runner
    clock = now or (lambda: datetime.now(timezone.utc))
    captured_at = clock().isoformat()
    notes: List[str] = []
    fields: Dict[str, object] = {}

    try:
        code, output = run(["budget", "zone", zone])
        if code != 0:
            notes.append("budget zone exited %d" % code)
        fields.update(parse_zone_budget(output))
    except Exception as exc:                                     # noqa: BLE001
        notes.append("budget zone unavailable: %s"
                     % redact("%s: %s" % (type(exc).__name__, exc)))

    try:
        code, output = run(["budget", "balance"])
        if code != 0:
            notes.append("budget balance exited %d" % code)
        fields.update(parse_balance(output))
    except Exception as exc:                                     # noqa: BLE001
        notes.append("budget balance unavailable: %s"
                     % redact("%s: %s" % (type(exc).__name__, exc)))

    available = (fields.get("cost_month_usd_minor") is not None
                 or fields.get("bandwidth_bytes") is not None)
    if not available:
        notes.append("no cost or bandwidth figure could be read")

    return UsageSnapshot(
        label=label, captured_at=captured_at, zone=zone, available=available,
        cost_month_usd_minor=fields.get("cost_month_usd_minor"),
        bandwidth_bytes=fields.get("bandwidth_bytes"),
        bandwidth_display=str(fields.get("bandwidth_display") or ""),
        cost_display=str(fields.get("cost_display") or ""),
        balance_usd_minor=fields.get("balance_usd_minor"),
        pending_charge_usd_minor=fields.get("pending_charge_usd_minor"),
        notes=tuple(notes))


def implied_rate_usd_minor_per_gb(snapshot: UsageSnapshot) -> Optional[float]:
    """Zone month-to-date cost divided by month-to-date bandwidth.

    Arithmetic on two numbers Bright Data itself reported, not a price looked
    up from anywhere, and the only basis on which this package will ESTIMATE
    the cost of traffic that billing has not yet reported. ``None`` when either
    input is missing or zero, because a rate derived from nothing is a made-up
    number.
    """
    if not snapshot.available:
        return None
    cost = snapshot.cost_month_usd_minor
    used = snapshot.bandwidth_bytes
    if not cost or not used:
        return None
    return cost / (used / float(_UNIT_BYTES["GB"]))


def delta(before: UsageSnapshot, after: UsageSnapshot) -> Dict:
    """The difference between two snapshots, with the lag question answered.

    ``cost_status`` is FINAL only when the reported cost actually moved.
    Equality means the billing system has not caught up, and that is PENDING --
    never "it cost nothing".
    """
    out: Dict = {
        "before": before.to_dict(),
        "after": after.to_dict(),
        "cost_delta_usd_minor": None,
        "bandwidth_delta_bytes": None,
        "cost_status": "UNAVAILABLE",
    }
    if not (before.available and after.available):
        out["note"] = ("at least one snapshot could not be read; Bright Data "
                       "reported cost is unavailable for this run")
        return out

    if (before.cost_month_usd_minor is not None
            and after.cost_month_usd_minor is not None):
        out["cost_delta_usd_minor"] = (after.cost_month_usd_minor
                                       - before.cost_month_usd_minor)
    if before.bandwidth_bytes is not None and after.bandwidth_bytes is not None:
        out["bandwidth_delta_bytes"] = (after.bandwidth_bytes
                                        - before.bandwidth_bytes)

    moved_cost = bool(out["cost_delta_usd_minor"])
    moved_bandwidth = bool(out["bandwidth_delta_bytes"])
    if moved_cost:
        out["cost_status"] = "FINAL"
    elif moved_bandwidth:
        out["cost_status"] = "PARTIAL"
        out["note"] = ("zone bandwidth moved but reported cost did not; "
                       "Bright Data cost accounting lags bandwidth accounting")
    else:
        out["cost_status"] = "PENDING"
        out["note"] = ("neither reported figure moved. Bright Data zone "
                       "statistics lag; this is NOT evidence that the run was "
                       "free. Read the ESTIMATED traffic figures instead.")
    return out


__all__ = [
    "AUTH_ENV", "ZONE", "CLI_NAME", "ALLOWED_CLI_ARGS", "REDACTED",
    "BrightDataCredentialError", "BrightDataUsageError",
    "credential_present", "redact", "contains_credential", "browser_endpoint",
    "money_to_minor", "bandwidth_to_bytes", "parse_zone_budget",
    "parse_balance", "UsageSnapshot", "read_usage",
    "implied_rate_usd_minor_per_gb", "delta",
]

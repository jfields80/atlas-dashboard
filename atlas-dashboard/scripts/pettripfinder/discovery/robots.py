"""PTF-DISCOVERY-001 WO-1A Step 11 -- fail-closed robots.txt compliance.

Base architecture §C.2: *"if robots.txt is unreachable or unparseable, the host
is treated as ROBOTS_DENIED, not allowed."* WO-0 recorded this as UNKNOWN;
reading ``website_fetcher.py`` -> ``importer/fetch.py`` in full confirmed it was
simply MISSING. FD-6 directed implementing it rather than isolating it in an ADR.

Design (FD-6 requirements, in order):

  * consult robots.txt BEFORE any compliant discovery fetch;
  * cache the decision together with its retrieval metadata;
  * respect the identified user agent and the applicable path;
  * DISALLOW blocks retrieval;
  * unavailable / malformed / indeterminate state produces a diagnosable
    HELD-style outcome rather than silently permitting access;
  * no stealth, bypass, alternate identity or proxy workaround exists here --
    there is deliberately no code path that retries a denial under a different
    name, and adding one would be the thing this module is for preventing;
  * deterministic offline tests (see ``test_robots.py``);
  * **Provider Zero remains cache-only and issues no network request** -- the
    ``robots_fetcher=None`` default cannot reach the network at all.

This module is pure policy plus an injected fetcher. It never imports
``requests`` and never opens a socket by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.membrane import assert_dataclasses_clean

#: The identity we present. Never rotated, never disguised (base §C.2).
DISCOVERY_USER_AGENT = C.GOOGLE_USER_AGENT.split("/")[0] or "AtlasDiscovery"

# Decisions.
ALLOWED = "ROBOTS_ALLOWED"
DENIED = "ROBOTS_DENIED"
INDETERMINATE = "ROBOTS_INDETERMINATE"
DECISIONS = frozenset({ALLOWED, DENIED, INDETERMINATE})

# Why a decision came out the way it did -- diagnosable, never a bare boolean.
REASON_EXPLICIT_ALLOW = "explicit_allow_rule"
REASON_EXPLICIT_DISALLOW = "explicit_disallow_rule"
REASON_NO_MATCHING_RULE = "no_matching_rule"
REASON_EMPTY_ROBOTS = "empty_robots_permits_all"
REASON_UNREACHABLE = "robots_unreachable"
REASON_MALFORMED = "robots_malformed"
REASON_NOT_FETCHED = "robots_not_fetched"
REASON_HTTP_ERROR = "robots_http_error"

#: Decisions that must NOT proceed to retrieval. INDETERMINATE is separated
#: from DENIED on purpose: both block, but only one means "the host told us no".
BLOCKING_DECISIONS = frozenset({DENIED, INDETERMINATE})


class RobotsError(ValueError):
    """Raised when a retrieval is attempted against a blocking robots decision."""


@dataclass(frozen=True)
class RobotsDecision:
    """One host+path decision, with the metadata that produced it."""

    host: str
    path: str
    user_agent: str
    decision: str
    reason: str
    matched_rule: str = ""
    http_status: Optional[int] = None
    retrieved_at: str = ""
    source_url: str = ""

    @property
    def allows_retrieval(self) -> bool:
        return self.decision == ALLOWED

    def to_dict(self) -> dict:
        return {
            "host": self.host, "path": self.path, "user_agent": self.user_agent,
            "decision": self.decision, "reason": self.reason,
            "matched_rule": self.matched_rule, "http_status": self.http_status,
            "retrieved_at": self.retrieved_at, "source_url": self.source_url,
        }


# --------------------------------------------------------------------------- #
# Parsing.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RobotsRules:
    """Rules that apply to ONE user agent, most specific group wins."""
    allow: Tuple[str, ...] = ()
    disallow: Tuple[str, ...] = ()
    matched_group: str = ""


def _agent_matches(group_agent: str, user_agent: str) -> bool:
    group_agent = group_agent.strip().lower()
    if group_agent == "*":
        return True
    return group_agent and group_agent in user_agent.strip().lower()


def parse_robots(text: str, *, user_agent: str) -> Optional[RobotsRules]:
    """Parse robots.txt into the rules applying to ``user_agent``.

    Returns ``None`` when the document cannot be understood as robots.txt at
    all -- the caller turns that into INDETERMINATE, never into "allowed".
    A specific agent group always beats the ``*`` group.
    """
    if text is None:
        return None
    # A document with no directive lines at all is not a parse failure -- an
    # empty robots.txt is a valid document that permits everything.
    stripped = [ln.split("#", 1)[0].strip() for ln in text.splitlines()]
    lines = [ln for ln in stripped if ln]
    if not lines:
        return RobotsRules(matched_group="")

    recognized = 0
    groups: Dict[str, Dict[str, list]] = {}
    current: list = []
    last_was_agent = False

    for line in lines:
        if ":" not in line:
            continue
        field, value = line.split(":", 1)
        field = field.strip().lower()
        value = value.strip()

        if field == "user-agent":
            recognized += 1
            if not last_was_agent:
                current = []
            current.append(value)
            groups.setdefault(value, {"allow": [], "disallow": []})
            last_was_agent = True
        elif field in ("allow", "disallow"):
            recognized += 1
            last_was_agent = False
            for agent in current or ["*"]:
                groups.setdefault(agent, {"allow": [], "disallow": []})
                groups[agent][field].append(value)
        else:
            # sitemap:, crawl-delay:, host: etc. -- known-but-unused directives.
            last_was_agent = False

    if recognized == 0:
        return None                      # not robots.txt at all -> INDETERMINATE

    specific = [a for a in groups if a.strip() != "*" and _agent_matches(a, user_agent)]
    chosen = sorted(specific, key=len, reverse=True)[0] if specific else (
        "*" if "*" in groups else None)
    if chosen is None:
        return RobotsRules(matched_group="")

    rules = groups[chosen]
    return RobotsRules(allow=tuple(rules["allow"]), disallow=tuple(rules["disallow"]),
                       matched_group=chosen)


def _rule_matches(pattern: str, path: str) -> bool:
    if pattern == "":
        return False                      # "Disallow:" with no value allows all
    if pattern.endswith("$"):
        return path == pattern[:-1]
    return path.startswith(pattern)


def evaluate_path(rules: RobotsRules, path: str) -> Tuple[str, str, str]:
    """Return ``(decision, reason, matched_rule)`` for one path.

    Longest match wins; an Allow of equal-or-greater length beats a Disallow,
    which is the standard precedence and the one that avoids over-blocking a
    host that explicitly carved out a path for us.
    """
    path = path or "/"
    best_disallow = max((p for p in rules.disallow if _rule_matches(p, path)),
                        key=len, default=None)
    best_allow = max((p for p in rules.allow if _rule_matches(p, path)),
                     key=len, default=None)

    if best_disallow is None:
        if best_allow is not None:
            return (ALLOWED, REASON_EXPLICIT_ALLOW, "Allow: %s" % best_allow)
        return (ALLOWED, REASON_NO_MATCHING_RULE, "")
    if best_allow is not None and len(best_allow) >= len(best_disallow):
        return (ALLOWED, REASON_EXPLICIT_ALLOW, "Allow: %s" % best_allow)
    return (DENIED, REASON_EXPLICIT_DISALLOW, "Disallow: %s" % best_disallow)


# --------------------------------------------------------------------------- #
# The gate.
# --------------------------------------------------------------------------- #

def robots_url_for(url: str) -> str:
    parts = urlsplit(url)
    return "%s://%s/robots.txt" % (parts.scheme or "https", parts.netloc)


@dataclass(frozen=True)
class RobotsFetchResult:
    """What an injected fetcher returns. Deliberately minimal so tests can
    construct one without touching the network."""
    ok: bool
    text: Optional[str] = None
    http_status: Optional[int] = None
    retrieved_at: str = ""


class RobotsCache:
    """Per-host decision cache, holding the retrieval metadata alongside the
    decision (FD-6). In-memory and explicit -- one robots fetch per host per
    run, never one per candidate URL."""

    def __init__(self):
        self._by_host: Dict[str, RobotsFetchResult] = {}

    def get(self, host: str) -> Optional[RobotsFetchResult]:
        return self._by_host.get(host)

    def put(self, host: str, result: RobotsFetchResult) -> None:
        self._by_host[host] = result

    def hosts(self) -> Tuple[str, ...]:
        return tuple(sorted(self._by_host))


def check_url(url: str, *, cache: RobotsCache,
              robots_fetcher: Optional[Callable[[str], RobotsFetchResult]] = None,
              user_agent: str = DISCOVERY_USER_AGENT,
              as_of: str = "") -> RobotsDecision:
    """Decide whether ``url`` may be retrieved. FAIL-CLOSED.

    ``robots_fetcher=None`` means "never go to the network": an uncached host
    is INDETERMINATE, which blocks. That is exactly the Provider Zero posture --
    cache-only, zero network calls -- and it is the default, so a caller has to
    opt IN to fetching rather than opt out.
    """
    parts = urlsplit(url)
    host = parts.netloc
    path = parts.path or "/"

    if not host:
        return RobotsDecision(host="", path=path, user_agent=user_agent,
                              decision=INDETERMINATE, reason=REASON_MALFORMED,
                              source_url=url)

    cached = cache.get(host)
    if cached is None:
        if robots_fetcher is None:
            return RobotsDecision(
                host=host, path=path, user_agent=user_agent,
                decision=INDETERMINATE, reason=REASON_NOT_FETCHED,
                retrieved_at=as_of, source_url=robots_url_for(url))
        cached = robots_fetcher(robots_url_for(url))
        cache.put(host, cached)

    if not cached.ok:
        # Unreachable robots.txt denies the host (base §C.2 fail-closed rule).
        return RobotsDecision(
            host=host, path=path, user_agent=user_agent, decision=DENIED,
            reason=(REASON_HTTP_ERROR if cached.http_status else REASON_UNREACHABLE),
            http_status=cached.http_status, retrieved_at=cached.retrieved_at,
            source_url=robots_url_for(url))

    rules = parse_robots(cached.text or "", user_agent=user_agent)
    if rules is None:
        return RobotsDecision(
            host=host, path=path, user_agent=user_agent, decision=INDETERMINATE,
            reason=REASON_MALFORMED, http_status=cached.http_status,
            retrieved_at=cached.retrieved_at, source_url=robots_url_for(url))

    if not rules.allow and not rules.disallow:
        return RobotsDecision(
            host=host, path=path, user_agent=user_agent, decision=ALLOWED,
            reason=REASON_EMPTY_ROBOTS, http_status=cached.http_status,
            retrieved_at=cached.retrieved_at, source_url=robots_url_for(url))

    decision, reason, matched = evaluate_path(rules, path)
    return RobotsDecision(
        host=host, path=path, user_agent=user_agent, decision=decision,
        reason=reason, matched_rule=matched, http_status=cached.http_status,
        retrieved_at=cached.retrieved_at, source_url=robots_url_for(url))


def assert_retrieval_permitted(decision: RobotsDecision) -> None:
    """Raise unless retrieval may proceed. Raising rather than returning a
    boolean so a call site cannot quietly ignore a denial."""
    if decision.decision in BLOCKING_DECISIONS:
        raise RobotsError(
            "robots %s for %s%s (%s)" % (decision.decision, decision.host,
                                         decision.path, decision.reason))


def summarize_decisions(decisions: Sequence[RobotsDecision]) -> Dict[str, int]:
    counts = {d: 0 for d in sorted(DECISIONS)}
    for d in decisions:
        counts[d.decision] = counts.get(d.decision, 0) + 1
        counts["reason_%s" % d.reason] = counts.get("reason_%s" % d.reason, 0) + 1
    return dict(sorted(counts.items()))


assert_dataclasses_clean(RobotsDecision, RobotsRules, RobotsFetchResult,
                         context="discovery.robots")

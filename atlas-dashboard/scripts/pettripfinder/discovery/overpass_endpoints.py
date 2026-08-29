"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- approved Overpass endpoints, their
health, and the circuit that keeps a dead one from being asked thirty times.

WHY
---
Pittsburgh's discovery had 30 queries, 8 safely cached, 22 remaining, and one
public Overpass endpoint that began timing out at the TCP layer. Nothing else
was wrong, no data was lost and no money was spent -- and the market waited for
hours, because the only endpoint the client knew was the one that had stopped
answering, and it was asked again for every remaining cell.

WHAT THIS IS NOT
----------------
Not a way around a provider block. Rotation here survives an OUTAGE. An endpoint
that rate-limits (429) or refuses the client is placed in cooldown for a long
time rather than cycled back to, and every endpoint is queried at concurrency 1
with spacing between requests. The registry is an APPROVED list read from a
committed JSON file; nothing here discovers endpoints or adds one at runtime.

THE PIECES
----------
``EndpointRegistry``   the approved endpoints, in preference order, with each
                       one's timeouts, spacing, cooldown and failure threshold.
``classify_probe``     one health-check outcome -> HEALTHY / TIMEOUT /
                       CONNECTION_REFUSED / HTTP_RATE_LIMITED /
                       HTTP_SERVER_ERROR / OTHER_FAILURE.
``EndpointCircuit``    per-endpoint failure count, open/closed state and
                       ``cooldown_until``; persisted in a small ledger so a
                       RESUMED run remembers which endpoint was dead an hour ago.
``EndpointSelector``   "which approved endpoint do I use now?": walks the
                       registry in order, skips disabled and cooling-down
                       endpoints, probes the rest, returns the first HEALTHY one.
                       Raises ``NoHealthyEndpoint`` -- carrying every endpoint's
                       state and the earliest cooldown expiry -- when none is.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C

REGISTRY_SCHEMA = "ptf-overpass-endpoints/1.0"
HEALTH_LEDGER_SCHEMA = "ptf-overpass-endpoint-health/1.0"
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "config" / "overpass_endpoints.json"
HEALTH_LEDGER_FILENAME = "overpass_endpoint_health.json"

# Health classifications.
HEALTHY = "HEALTHY"
TIMEOUT = "TIMEOUT"
CONNECTION_REFUSED = "CONNECTION_REFUSED"
HTTP_RATE_LIMITED = "HTTP_RATE_LIMITED"
HTTP_SERVER_ERROR = "HTTP_SERVER_ERROR"
OTHER_FAILURE = "OTHER_FAILURE"
HEALTH_STATES: Tuple[str, ...] = (HEALTHY, TIMEOUT, CONNECTION_REFUSED,
                                  HTTP_RATE_LIMITED, HTTP_SERVER_ERROR,
                                  OTHER_FAILURE)

#: A refusal or a rate limit is not a blip to be re-tried in a moment. The
#: endpoint is telling us to go away; we go away for the whole cooldown.
OPEN_IMMEDIATELY = frozenset({HTTP_RATE_LIMITED})

# Circuit states. Only CLOSED and OPEN are persisted; HALF_OPEN is what an
# OPEN circuit whose cooldown has expired is called in a report -- it gets one
# trial probe, and a failure there re-arms the cooldown (PTF-PITTSBURGH-
# HARDENED-RECENSUS-001: without the re-arm an expired circuit was re-probed on
# every run and reported an expiry hours in the past).
CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"


class EndpointRegistryError(ValueError):
    """The approved-endpoint registry is malformed (fail closed)."""


class NoHealthyEndpoint(RuntimeError):
    """Every approved endpoint is disabled, cooling down or unhealthy."""

    def __init__(self, message: str, *, states: Mapping[str, Mapping],
                 earliest_cooldown_expiry: str) -> None:
        super().__init__(message)
        self.states = dict(states)
        self.earliest_cooldown_expiry = earliest_cooldown_expiry


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(when: datetime) -> str:
    return when.astimezone(timezone.utc).isoformat()


def _parse(when: str) -> Optional[datetime]:
    if not when:
        return None
    try:
        parsed = datetime.fromisoformat(when)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class EndpointRecord:
    endpoint_id: str
    base_url: str
    enabled: bool
    health_check_path: str
    timeout_seconds: float
    connect_timeout_seconds: float
    min_request_spacing_seconds: float
    cooldown_seconds: float
    failure_threshold: int
    notes: str = ""
    #: Endpoints that share backend infrastructure share a failure domain: when
    #: one opens, its siblings open with it, and they count as ONE available
    #: endpoint. Empty means the endpoint is its own domain.
    failure_domain: str = ""

    @property
    def domain(self) -> str:
        return self.failure_domain or self.endpoint_id

    @property
    def health_check_url(self) -> str:
        """``.../api/interpreter`` -> ``.../api/status`` (or whatever the record
        names); a health check must never be a real query."""
        base = self.base_url
        marker = "/api/interpreter"
        if base.endswith(marker):
            base = base[:-len(marker)]
        return base.rstrip("/") + "/" + self.health_check_path.lstrip("/")

    def to_dict(self) -> Dict:
        return OrderedDict((
            ("endpoint_id", self.endpoint_id), ("base_url", self.base_url),
            ("enabled", self.enabled), ("health_check_url", self.health_check_url),
            ("timeout_seconds", self.timeout_seconds),
            ("connect_timeout_seconds", self.connect_timeout_seconds),
            ("min_request_spacing_seconds", self.min_request_spacing_seconds),
            ("cooldown_seconds", self.cooldown_seconds),
            ("failure_threshold", self.failure_threshold), ("notes", self.notes),
            ("failure_domain", self.domain),
        ))


@dataclass(frozen=True)
class EndpointRegistry:
    endpoints: Tuple[EndpointRecord, ...]
    concurrency: int = 1
    source: str = ""

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "EndpointRegistry":
        source = Path(path or DEFAULT_REGISTRY_PATH)
        if not source.is_file():
            raise EndpointRegistryError("no endpoint registry at %s" % source)
        return cls.from_document(json.loads(source.read_text(encoding="utf-8")),
                                 source=source.as_posix())

    @classmethod
    def from_document(cls, document: Mapping, *, source: str = "") -> "EndpointRegistry":
        if document.get("schema") != REGISTRY_SCHEMA:
            raise EndpointRegistryError("registry schema is %r, not %s"
                                        % (document.get("schema"), REGISTRY_SCHEMA))
        defaults = dict(document.get("defaults") or {})
        records: List[EndpointRecord] = []
        seen: set = set()
        for row in document.get("endpoints") or ():
            endpoint_id = str(row.get("endpoint_id") or "").strip()
            base_url = str(row.get("base_url") or "").strip()
            if not endpoint_id or not base_url:
                raise EndpointRegistryError("an endpoint row lacks endpoint_id or base_url")
            if not base_url.startswith("https://"):
                raise EndpointRegistryError("%s: base_url must be https" % endpoint_id)
            if endpoint_id in seen:
                raise EndpointRegistryError("duplicate endpoint_id %r" % endpoint_id)
            seen.add(endpoint_id)

            def pick(key, cast):
                value = row.get(key, defaults.get(key))
                if value is None:
                    raise EndpointRegistryError("%s: no %s and no default" % (endpoint_id, key))
                return cast(value)

            threshold = pick("failure_threshold", int)
            if threshold < 1:
                raise EndpointRegistryError("%s: failure_threshold must be >= 1" % endpoint_id)
            records.append(EndpointRecord(
                endpoint_id=endpoint_id, base_url=base_url,
                enabled=bool(row.get("enabled", True)),
                health_check_path=str(pick("health_check_path", str)),
                timeout_seconds=pick("timeout_seconds", float),
                connect_timeout_seconds=pick("connect_timeout_seconds", float),
                min_request_spacing_seconds=pick("min_request_spacing_seconds", float),
                cooldown_seconds=pick("cooldown_seconds", float),
                failure_threshold=threshold,
                notes=str(row.get("notes") or ""),
                failure_domain=str(row.get("failure_domain") or "").strip()))
        if not records:
            raise EndpointRegistryError("the registry names no endpoint")
        concurrency = int(defaults.get("concurrency", 1))
        if concurrency != 1:
            raise EndpointRegistryError(
                "concurrency is %d; public Overpass discovery runs at 1 unless a "
                "registry explicitly documents why it may not" % concurrency)
        return cls(endpoints=tuple(records), concurrency=concurrency, source=source)

    @classmethod
    def single(cls, base_url: str, *, endpoint_id: str = "") -> "EndpointRegistry":
        """One endpoint, for callers that name one explicitly (the legacy
        ``OverpassClient(endpoint=...)`` form)."""
        host = base_url.split("//", 1)[-1].split("/", 1)[0]
        return cls(endpoints=(EndpointRecord(
            endpoint_id=endpoint_id or host, base_url=base_url, enabled=True,
            health_check_path="/api/status",
            timeout_seconds=float(C.OVERPASS_CLIENT_TIMEOUT_SECONDS),
            connect_timeout_seconds=float(C.CONNECT_TIMEOUT_SECONDS),
            min_request_spacing_seconds=0.0, cooldown_seconds=900.0,
            failure_threshold=3, notes="named explicitly by the caller"),),
            source="explicit")

    def enabled_endpoints(self) -> Tuple[EndpointRecord, ...]:
        return tuple(e for e in self.endpoints if e.enabled)

    def enabled_failure_domains(self) -> Tuple[str, ...]:
        """Distinct backends among the enabled endpoints, in registry order."""
        out: List[str] = []
        for endpoint in self.enabled_endpoints():
            if endpoint.domain not in out:
                out.append(endpoint.domain)
        return tuple(out)

    def siblings(self, endpoint: EndpointRecord) -> Tuple[EndpointRecord, ...]:
        """The OTHER enabled endpoints in ``endpoint``'s failure domain."""
        return tuple(e for e in self.enabled_endpoints()
                     if e.domain == endpoint.domain and e.endpoint_id != endpoint.endpoint_id)

    def by_id(self, endpoint_id: str) -> EndpointRecord:
        for endpoint in self.endpoints:
            if endpoint.endpoint_id == endpoint_id:
                return endpoint
        raise KeyError(endpoint_id)

    def base_urls(self) -> Tuple[str, ...]:
        return tuple(e.base_url for e in self.endpoints)


# --------------------------------------------------------------------------- #
# Health classification
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ProbeOutcome:
    """What one health check observed. ``exception`` is the exception CLASS
    name, never its text (a URL with a token could sit in the text)."""
    http_status: Optional[int] = None
    exception: str = ""
    elapsed_seconds: float = 0.0


def classify_probe(outcome: ProbeOutcome) -> str:
    """One probe -> one of ``HEALTH_STATES``."""
    if outcome.exception:
        name = outcome.exception.lower()
        if "timeout" in name:
            return TIMEOUT
        if "connection" in name or "refused" in name:
            return CONNECTION_REFUSED
        return OTHER_FAILURE
    status = outcome.http_status
    if status is None:
        return OTHER_FAILURE
    if status == 429:
        return HTTP_RATE_LIMITED
    if 500 <= status <= 599:
        return HTTP_SERVER_ERROR
    if 200 <= status <= 299:
        return HEALTHY
    return OTHER_FAILURE


def classify_request_error(error: str, *, http_status: Optional[int] = None) -> str:
    """A live-query failure (``constants.PROVIDER_ERROR_*``) in health terms."""
    if error == C.PROVIDER_ERROR_TIMEOUT:
        return TIMEOUT
    if error == C.PROVIDER_ERROR_RATE_LIMITED:
        return HTTP_RATE_LIMITED
    if http_status is not None and 500 <= http_status <= 599:
        return HTTP_SERVER_ERROR
    if error == C.PROVIDER_ERROR_TRANSIENT and http_status is None:
        return CONNECTION_REFUSED
    return OTHER_FAILURE


def probe_with_requests(endpoint: EndpointRecord, session=None) -> ProbeOutcome:
    """The real health check: one GET of the endpoint's status page."""
    import time
    if session is None:
        import requests
        session = requests.Session()
    began = time.monotonic()
    try:
        response = session.get(
            endpoint.health_check_url,
            headers={"User-Agent": C.OVERPASS_USER_AGENT},
            timeout=(endpoint.connect_timeout_seconds, endpoint.timeout_seconds))
    except Exception as exc:                                        # noqa: BLE001
        return ProbeOutcome(exception=type(exc).__name__,
                            elapsed_seconds=round(time.monotonic() - began, 3))
    return ProbeOutcome(http_status=int(getattr(response, "status_code", 0) or 0),
                        elapsed_seconds=round(time.monotonic() - began, 3))


# --------------------------------------------------------------------------- #
# Circuit breaker
# --------------------------------------------------------------------------- #

@dataclass
class EndpointCircuit:
    endpoint_id: str
    state: str = CLOSED
    consecutive_failures: int = 0
    cooldown_until: str = ""
    last_classification: str = ""
    last_checked_at: str = ""
    opened_at: str = ""
    opened_because: str = ""
    successes: int = 0
    failures: int = 0

    def is_cooling_down(self, now: datetime) -> bool:
        until = _parse(self.cooldown_until)
        return self.state == OPEN and until is not None and now < until

    def is_half_open(self, now: datetime) -> bool:
        """OPEN, cooldown expired, awaiting one trial probe."""
        return self.state == OPEN and not self.is_cooling_down(now)

    def open_as_sibling(self, *, endpoint: EndpointRecord, now: datetime,
                        because: str) -> None:
        """Open alongside a failing endpoint in the same failure domain. The
        counts are untouched: this endpoint was not asked, its backend was."""
        if self.is_cooling_down(now):
            return
        self.state = OPEN
        self.opened_at = _iso(now)
        self.cooldown_until = _iso(now + timedelta(seconds=endpoint.cooldown_seconds))
        self.opened_because = because

    def record(self, classification: str, *, endpoint: EndpointRecord,
               now: datetime, probe: bool = False) -> None:
        self.last_classification = classification
        self.last_checked_at = _iso(now)
        if classification == HEALTHY:
            self.successes += 1
            # A status page can answer 200 while the interpreter fails every
            # query (observed live on overpass.kumi.systems during
            # PTF-PITTSBURGH-HARDENED-RECENSUS-001: 36 straight request
            # failures, zero circuit opens, zero failovers, because the probe
            # before each select() reset this count). Only a real request
            # success clears the failure streak; a healthy probe may still
            # close a cooled-down circuit, whose surviving streak then re-opens
            # it on the next failure (half-open).
            if not probe:
                self.consecutive_failures = 0
            if self.state == OPEN and not self.is_cooling_down(now):
                self.state = CLOSED
                self.cooldown_until = ""
            return
        self.failures += 1
        self.consecutive_failures += 1
        threshold = 1 if classification in OPEN_IMMEDIATELY else endpoint.failure_threshold
        # A HALF_OPEN circuit (OPEN, cooldown expired) is on its one trial: any
        # failure re-arms the cooldown, whatever the count says -- a circuit
        # opened as a domain sibling may carry no failures of its own.
        half_open = self.is_half_open(now)
        if half_open or (self.state != OPEN and self.consecutive_failures >= threshold):
            self.state = OPEN
            self.opened_at = _iso(now)
            self.cooldown_until = _iso(now + timedelta(seconds=endpoint.cooldown_seconds))
            self.opened_because = (
                "%s (%d consecutive failure%s; threshold %d)"
                % (classification, self.consecutive_failures,
                   "" if self.consecutive_failures == 1 else "s", threshold))

    def to_dict(self) -> Dict:
        return OrderedDict((
            ("endpoint_id", self.endpoint_id), ("state", self.state),
            ("consecutive_failures", self.consecutive_failures),
            ("cooldown_until", self.cooldown_until),
            ("last_classification", self.last_classification),
            ("last_checked_at", self.last_checked_at),
            ("opened_at", self.opened_at), ("opened_because", self.opened_because),
            ("successes", self.successes), ("failures", self.failures),
        ))

    @classmethod
    def from_dict(cls, row: Mapping) -> "EndpointCircuit":
        return cls(endpoint_id=str(row.get("endpoint_id") or ""),
                   state=str(row.get("state") or CLOSED),
                   consecutive_failures=int(row.get("consecutive_failures") or 0),
                   cooldown_until=str(row.get("cooldown_until") or ""),
                   last_classification=str(row.get("last_classification") or ""),
                   last_checked_at=str(row.get("last_checked_at") or ""),
                   opened_at=str(row.get("opened_at") or ""),
                   opened_because=str(row.get("opened_because") or ""),
                   successes=int(row.get("successes") or 0),
                   failures=int(row.get("failures") or 0))


# --------------------------------------------------------------------------- #
# Selector
# --------------------------------------------------------------------------- #

@dataclass
class EndpointSelector:
    """Which approved endpoint to use right now, and the memory behind it.

    ``probe`` is injectable (tests never touch the network); ``clock`` too, so
    a cooldown can be tested without waiting fifteen minutes. ``ledger_path``
    persists the circuits between processes: a resumed run must not rediscover
    an outage the last run already paid for.
    """

    registry: EndpointRegistry
    probe: Callable[[EndpointRecord], ProbeOutcome] = probe_with_requests
    clock: Callable[[], datetime] = _now
    ledger_path: Optional[Path] = None
    circuits: Dict[str, EndpointCircuit] = field(default_factory=OrderedDict)
    current_id: str = ""
    switches: int = 0
    probes: List[Dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        for endpoint in self.registry.endpoints:
            self.circuits.setdefault(endpoint.endpoint_id,
                                     EndpointCircuit(endpoint_id=endpoint.endpoint_id))
        if self.ledger_path is not None and Path(self.ledger_path).is_file():
            self._load_ledger()

    # -- persistence ------------------------------------------------------- #

    def _load_ledger(self) -> None:
        try:
            document = json.loads(Path(self.ledger_path).read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return
        for row in document.get("circuits") or ():
            circuit = EndpointCircuit.from_dict(row)
            if circuit.endpoint_id in self.circuits:
                self.circuits[circuit.endpoint_id] = circuit
        # The last endpoint actually selected, and the switch count, live
        # across processes too: a resumed run that selects nothing must not
        # blank the one and a run of one selection must not zero the other.
        current = str(document.get("current_endpoint_id") or "")
        if current in self.circuits:
            self.current_id = current
        self.switches = int(document.get("endpoint_switches") or 0)

    def save(self) -> Optional[str]:
        if self.ledger_path is None:
            return None
        path = Path(self.ledger_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.ledger_document(), indent=1) + "\n",
                        encoding="utf-8")
        return path.as_posix()

    def ledger_document(self) -> Dict:
        return OrderedDict((
            ("schema", HEALTH_LEDGER_SCHEMA),
            ("registry", self.registry.source),
            ("written_at", _iso(self.clock())),
            ("current_endpoint_id", self.current_id),
            ("endpoint_switches", self.switches),
            ("circuits", [c.to_dict() for c in self.circuits.values()]),
            ("probes", list(self.probes)),
        ))

    # -- state ------------------------------------------------------------- #

    def states(self) -> Dict[str, Dict]:
        """Every endpoint's availability right now, for a report."""
        now = self.clock()
        out: "OrderedDict[str, Dict]" = OrderedDict()
        for endpoint in self.registry.endpoints:
            circuit = self.circuits[endpoint.endpoint_id]
            if not endpoint.enabled:
                availability = "DISABLED"
            elif circuit.is_cooling_down(now):
                availability = "COOLING_DOWN"
            elif self._domain_cooling_down(endpoint, now):
                availability = "COOLING_DOWN_SIBLING"
            elif circuit.is_half_open(now):
                availability = HALF_OPEN
            elif circuit.last_classification and circuit.last_classification != HEALTHY:
                # Failed its last probe but the circuit has not tripped: still
                # worth one more probe, and said so rather than called healthy.
                availability = "UNHEALTHY_LAST_PROBE"
            else:
                availability = "AVAILABLE"
            row = circuit.to_dict()
            row["enabled"] = endpoint.enabled
            row["availability"] = availability
            out[endpoint.endpoint_id] = row
        return out

    def _domain_cooling_down(self, endpoint: EndpointRecord, now: datetime) -> bool:
        """A sibling on the same backend is cooling down: so, in effect, is this."""
        return any(self.circuits[s.endpoint_id].is_cooling_down(now)
                   for s in self.registry.siblings(endpoint))

    def _suppressed(self, endpoint: EndpointRecord, now: datetime) -> bool:
        return (self.circuits[endpoint.endpoint_id].is_cooling_down(now)
                or self._domain_cooling_down(endpoint, now))

    def available_endpoints(self) -> Tuple[EndpointRecord, ...]:
        """Enabled endpoints neither cooling down nor sharing a backend with
        one that is -- BEFORE any probe. What free discovery could still try."""
        now = self.clock()
        return tuple(e for e in self.registry.enabled_endpoints()
                     if not self._suppressed(e, now))

    def available_failure_domains(self) -> Tuple[str, ...]:
        """Distinct backends free discovery could still try."""
        out: List[str] = []
        for endpoint in self.available_endpoints():
            if endpoint.domain not in out:
                out.append(endpoint.domain)
        return tuple(out)

    def _open_siblings(self, endpoint: EndpointRecord, now: datetime) -> None:
        because = ("sibling %s opened: shared failure domain %s"
                   % (endpoint.endpoint_id, endpoint.domain))
        for sibling in self.registry.siblings(endpoint):
            self.circuits[sibling.endpoint_id].open_as_sibling(
                endpoint=sibling, now=now, because=because)

    def earliest_cooldown_expiry(self) -> str:
        """The soonest a cooling-down endpoint becomes HALF_OPEN; empty when
        none is cooling down (an expired cooldown is not a wait)."""
        now = self.clock()
        expiries = [self.circuits[e.endpoint_id].cooldown_until
                    for e in self.registry.enabled_endpoints()
                    if self.circuits[e.endpoint_id].is_cooling_down(now)]
        return min(expiries) if expiries else ""

    # -- selection --------------------------------------------------------- #

    def _record_probe(self, endpoint: EndpointRecord, outcome: ProbeOutcome,
                      classification: str, now: datetime) -> None:
        self.probes.append(OrderedDict((
            ("endpoint_id", endpoint.endpoint_id), ("at", _iso(now)),
            ("http_status", outcome.http_status), ("exception", outcome.exception),
            ("elapsed_seconds", outcome.elapsed_seconds),
            ("classification", classification),
        )))

    def select(self) -> EndpointRecord:
        """The first approved endpoint, in registry order, that is enabled, not
        cooling down, and answers its health check HEALTHY.

        The current endpoint is kept while it stays healthy -- selection is not
        round-robin. Every probe and every state change is recorded, and the
        ledger is saved before this returns or raises, so a run that dies a
        moment later still leaves the outage on disk.
        """
        now = self.clock()
        ordered = list(self.registry.enabled_endpoints())
        if self.current_id:
            ordered.sort(key=lambda e: 0 if e.endpoint_id == self.current_id else 1)
        failed_domains: List[str] = []
        for endpoint in ordered:
            circuit = self.circuits[endpoint.endpoint_id]
            if self._suppressed(endpoint, now) or endpoint.domain in failed_domains:
                # Cooling down, sharing a backend with one that is, or sharing
                # a backend with one that just failed its probe in this walk:
                # the same server is not asked twice.
                continue
            outcome = self.probe(endpoint)
            classification = classify_probe(outcome)
            circuit.record(classification, endpoint=endpoint, now=now, probe=True)
            self._record_probe(endpoint, outcome, classification, now)
            if classification != HEALTHY:
                failed_domains.append(endpoint.domain)
                if circuit.state == OPEN:
                    self._open_siblings(endpoint, now)
            if classification == HEALTHY:
                if self.current_id and self.current_id != endpoint.endpoint_id:
                    self.switches += 1
                self.current_id = endpoint.endpoint_id
                self.save()
                return endpoint
        self.save()
        raise NoHealthyEndpoint(
            "no approved Overpass endpoint is healthy: %s"
            % ", ".join("%s=%s" % (k, v["availability"] if v["availability"] != "AVAILABLE"
                                   else v["last_classification"])
                        for k, v in self.states().items()),
            states=self.states(),
            earliest_cooldown_expiry=self.earliest_cooldown_expiry())

    def record_request_failure(self, endpoint: EndpointRecord, classification: str) -> bool:
        """A live query failed on ``endpoint``. Returns True when the circuit
        is now OPEN -- the caller must select again rather than retry here."""
        now = self.clock()
        circuit = self.circuits[endpoint.endpoint_id]
        circuit.record(classification, endpoint=endpoint, now=now)
        if circuit.state == OPEN:
            self._open_siblings(endpoint, now)
        self.save()
        return circuit.state == OPEN

    def record_request_success(self, endpoint: EndpointRecord) -> None:
        self.circuits[endpoint.endpoint_id].record(HEALTHY, endpoint=endpoint,
                                                   now=self.clock())

    def current(self) -> Optional[EndpointRecord]:
        return self.registry.by_id(self.current_id) if self.current_id else None


__all__ = [
    "REGISTRY_SCHEMA", "HEALTH_LEDGER_SCHEMA", "DEFAULT_REGISTRY_PATH",
    "HEALTH_LEDGER_FILENAME", "HEALTHY", "TIMEOUT", "CONNECTION_REFUSED",
    "HTTP_RATE_LIMITED", "HTTP_SERVER_ERROR", "OTHER_FAILURE", "HEALTH_STATES",
    "CLOSED", "OPEN", "HALF_OPEN", "EndpointRegistryError", "NoHealthyEndpoint",
    "EndpointRecord", "EndpointRegistry", "ProbeOutcome", "classify_probe",
    "classify_request_error", "probe_with_requests", "EndpointCircuit",
    "EndpointSelector",
]

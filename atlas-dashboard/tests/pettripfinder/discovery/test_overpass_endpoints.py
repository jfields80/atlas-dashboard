"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- the approved-endpoint registry, health
classification, the circuit breaker and cooldown, and endpoint selection.
No network: every probe is a fake."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import overpass_endpoints as OE


def registry_doc(*endpoints, threshold=3, cooldown=900):
    return {
        "schema": OE.REGISTRY_SCHEMA,
        "defaults": {"health_check_path": "/api/status", "timeout_seconds": 5,
                     "connect_timeout_seconds": 2, "min_request_spacing_seconds": 0,
                     "cooldown_seconds": cooldown, "failure_threshold": threshold,
                     "concurrency": 1},
        "endpoints": [{"endpoint_id": e, "base_url": "https://%s/api/interpreter" % e,
                       "enabled": True} for e in endpoints],
    }


class Clock:
    def __init__(self, start=None):
        self.now = start or datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now = self.now + timedelta(seconds=seconds)


class FakeProbe:
    """endpoint_id -> a list of outcomes, consumed in order (last repeats)."""

    def __init__(self, **outcomes):
        self.outcomes = {k: list(v) for k, v in outcomes.items()}
        self.calls = []

    def __call__(self, endpoint):
        self.calls.append(endpoint.endpoint_id)
        queue = self.outcomes[endpoint.endpoint_id]
        return queue.pop(0) if len(queue) > 1 else queue[0]


OK = OE.ProbeOutcome(http_status=200)
TIMEOUT = OE.ProbeOutcome(exception="ReadTimeout")
REFUSED = OE.ProbeOutcome(exception="ConnectionError")
RATE = OE.ProbeOutcome(http_status=429)
DOWN = OE.ProbeOutcome(http_status=503)


class TestRegistry:
    def test_the_committed_registry_loads_and_is_conservative(self):
        registry = OE.EndpointRegistry.load()
        assert registry.concurrency == 1
        enabled = registry.enabled_endpoints()
        assert enabled[0].endpoint_id == "overpass-api.de"
        assert len(enabled) >= 2
        for endpoint in registry.endpoints:
            assert endpoint.base_url.startswith("https://")
            assert endpoint.min_request_spacing_seconds >= 1.0
            assert endpoint.cooldown_seconds >= 600
            assert endpoint.failure_threshold >= 2
            assert endpoint.health_check_url.endswith("/api/status")
            assert endpoint.notes

    def test_the_swiss_only_instance_is_disabled_with_a_reason(self):
        registry = OE.EndpointRegistry.load()
        swiss = registry.by_id("overpass.osm.ch")
        assert swiss.enabled is False
        assert "SWITZERLAND" in swiss.notes

    def test_every_endpoint_record_carries_the_required_fields(self):
        record = OE.EndpointRegistry.load().endpoints[0].to_dict()
        for field in ("endpoint_id", "base_url", "enabled", "health_check_url",
                      "timeout_seconds", "min_request_spacing_seconds",
                      "cooldown_seconds", "failure_threshold", "notes"):
            assert field in record

    @pytest.mark.parametrize("mutate", [
        lambda d: d.update(schema="something-else"),
        lambda d: d["endpoints"].clear(),
        lambda d: d["endpoints"][0].update(base_url="http://insecure/api/interpreter"),
        lambda d: d["endpoints"].append(dict(d["endpoints"][0])),
        lambda d: d["defaults"].update(concurrency=4),
        lambda d: d["defaults"].update(failure_threshold=0),
    ])
    def test_a_malformed_registry_fails_closed(self, mutate):
        doc = registry_doc("a.example", "b.example")
        mutate(doc)
        with pytest.raises(OE.EndpointRegistryError):
            OE.EndpointRegistry.from_document(doc)

    def test_a_single_explicit_endpoint_is_a_one_row_registry(self):
        registry = OE.EndpointRegistry.single("https://mirror.example/api/interpreter")
        assert [e.endpoint_id for e in registry.endpoints] == ["mirror.example"]

    def test_a_failure_domain_defaults_to_the_endpoint_itself(self):
        doc = registry_doc("a.example", "b.example", "c.example")
        doc["endpoints"][1]["failure_domain"] = "shared.backend"
        doc["endpoints"][2]["failure_domain"] = "shared.backend"
        registry = OE.EndpointRegistry.from_document(doc)
        a, b, c = registry.endpoints
        assert a.domain == "a.example" and b.domain == c.domain == "shared.backend"
        assert registry.enabled_failure_domains() == ("a.example", "shared.backend")
        assert registry.siblings(b) == (c,) and registry.siblings(a) == ()
        assert a.to_dict()["failure_domain"] == "a.example"

    def test_kumi_and_private_coffee_are_one_failure_domain_in_the_committed_registry(self):
        # PTF-PITTSBURGH-HARDENED-RECENSUS-001 Q6: overpass.kumi.systems is a
        # DNS CNAME to flanders.servers.private.coffee -- the host that serves
        # overpass.private.coffee. Failing over between them asks the same
        # box twice, and counting both as available overstates the registry.
        registry = OE.EndpointRegistry.load()
        kumi = registry.by_id("overpass.kumi.systems")
        coffee = registry.by_id("overpass.private.coffee")
        assert kumi.domain == coffee.domain == "flanders.servers.private.coffee"
        assert "CNAME" in kumi.notes
        assert registry.by_id("overpass-api.de").domain == "overpass-api.de"
        assert len(registry.enabled_failure_domains()) == len(registry.enabled_endpoints()) - 1


class TestHealthClassification:
    @pytest.mark.parametrize("outcome, expected", [
        (OK, OE.HEALTHY),
        (TIMEOUT, OE.TIMEOUT),
        (OE.ProbeOutcome(exception="ConnectTimeout"), OE.TIMEOUT),
        (REFUSED, OE.CONNECTION_REFUSED),
        (OE.ProbeOutcome(exception="ConnectionRefusedError"), OE.CONNECTION_REFUSED),
        (RATE, OE.HTTP_RATE_LIMITED),
        (DOWN, OE.HTTP_SERVER_ERROR),
        (OE.ProbeOutcome(http_status=502), OE.HTTP_SERVER_ERROR),
        (OE.ProbeOutcome(http_status=404), OE.OTHER_FAILURE),
        (OE.ProbeOutcome(exception="ValueError"), OE.OTHER_FAILURE),
        (OE.ProbeOutcome(), OE.OTHER_FAILURE),
    ])
    def test_probe_outcomes_classify(self, outcome, expected):
        assert OE.classify_probe(outcome) == expected

    def test_live_request_errors_classify_in_the_same_vocabulary(self):
        assert OE.classify_request_error(C.PROVIDER_ERROR_TIMEOUT) == OE.TIMEOUT
        assert OE.classify_request_error(C.PROVIDER_ERROR_RATE_LIMITED) == OE.HTTP_RATE_LIMITED
        assert OE.classify_request_error(C.PROVIDER_ERROR_TRANSIENT, http_status=503) == OE.HTTP_SERVER_ERROR
        assert OE.classify_request_error(C.PROVIDER_ERROR_TRANSIENT) == OE.CONNECTION_REFUSED
        assert OE.classify_request_error(C.PROVIDER_ERROR_INVALID_REQUEST) == OE.OTHER_FAILURE

    def test_a_probe_never_records_exception_text(self):
        outcome = OE.ProbeOutcome(exception="ReadTimeout")
        assert "http" not in outcome.exception.lower()


class TestCircuitBreaker:
    def _endpoint(self, threshold=3, cooldown=900):
        return OE.EndpointRegistry.from_document(
            registry_doc("a.example", threshold=threshold, cooldown=cooldown)).endpoints[0]

    def test_it_opens_after_the_threshold_and_records_a_cooldown(self):
        clock = Clock()
        endpoint = self._endpoint(threshold=3, cooldown=600)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        for _ in range(2):
            circuit.record(OE.TIMEOUT, endpoint=endpoint, now=clock())
            assert circuit.state == OE.CLOSED
        circuit.record(OE.TIMEOUT, endpoint=endpoint, now=clock())
        assert circuit.state == OE.OPEN
        assert circuit.cooldown_until == (clock.now + timedelta(seconds=600)).isoformat()
        assert "3 consecutive failures" in circuit.opened_because
        assert circuit.is_cooling_down(clock())

    def test_a_rate_limit_opens_the_circuit_immediately(self):
        clock = Clock()
        endpoint = self._endpoint(threshold=3)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        circuit.record(OE.HTTP_RATE_LIMITED, endpoint=endpoint, now=clock())
        assert circuit.state == OE.OPEN
        assert circuit.is_cooling_down(clock())

    def test_a_success_resets_the_consecutive_count(self):
        clock = Clock()
        endpoint = self._endpoint(threshold=3)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        circuit.record(OE.TIMEOUT, endpoint=endpoint, now=clock())
        circuit.record(OE.TIMEOUT, endpoint=endpoint, now=clock())
        circuit.record(OE.HEALTHY, endpoint=endpoint, now=clock())
        circuit.record(OE.TIMEOUT, endpoint=endpoint, now=clock())
        assert circuit.state == OE.CLOSED and circuit.consecutive_failures == 1
        assert circuit.failures == 3 and circuit.successes == 1

    def test_a_healthy_probe_does_not_clear_the_request_failure_streak(self):
        # Observed live (PTF-PITTSBURGH-HARDENED-RECENSUS-001): a status page
        # answering 200 while the interpreter 500s every query. The probe
        # before each select() must not reset the streak, or the circuit can
        # never open and the run never fails over.
        clock = Clock()
        endpoint = self._endpoint(threshold=3)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock())
        circuit.record(OE.HEALTHY, endpoint=endpoint, now=clock(), probe=True)
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock())
        circuit.record(OE.HEALTHY, endpoint=endpoint, now=clock(), probe=True)
        assert circuit.consecutive_failures == 2
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock())
        assert circuit.state == OE.OPEN

    def test_a_healthy_probe_after_cooldown_half_opens(self):
        # The probe may close a cooled-down circuit, but the surviving streak
        # re-opens it on the very next failure rather than granting a fresh
        # threshold's worth of failing queries.
        clock = Clock()
        endpoint = self._endpoint(threshold=2, cooldown=300)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock())
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock())
        assert circuit.state == OE.OPEN
        clock.advance(301)
        circuit.record(OE.HEALTHY, endpoint=endpoint, now=clock(), probe=True)
        assert circuit.state == OE.CLOSED
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock())
        assert circuit.state == OE.OPEN

    def test_a_request_success_still_clears_the_streak(self):
        clock = Clock()
        endpoint = self._endpoint(threshold=3)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock())
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock())
        circuit.record(OE.HEALTHY, endpoint=endpoint, now=clock())
        assert circuit.consecutive_failures == 0

    def test_the_cooldown_expires_with_the_clock(self):
        clock = Clock()
        endpoint = self._endpoint(threshold=1, cooldown=300)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        circuit.record(OE.TIMEOUT, endpoint=endpoint, now=clock())
        assert circuit.is_cooling_down(clock())
        clock.advance(299)
        assert circuit.is_cooling_down(clock())
        clock.advance(2)
        assert not circuit.is_cooling_down(clock())
        circuit.record(OE.HEALTHY, endpoint=endpoint, now=clock())
        assert circuit.state == OE.CLOSED and circuit.cooldown_until == ""

    def test_an_expired_cooldown_is_half_open_and_a_failed_trial_re_arms_it(self):
        # PTF-PITTSBURGH-HARDENED-RECENSUS-001 Q1: an OPEN circuit past its
        # cooldown used to stay OPEN with a stale expiry, so it was re-probed
        # on every run (158 failures on one endpoint) and the waiting report
        # quoted an expiry hours in the past.
        clock = Clock()
        endpoint = self._endpoint(threshold=1, cooldown=300)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        circuit.record(OE.TIMEOUT, endpoint=endpoint, now=clock())
        first_expiry = circuit.cooldown_until
        clock.advance(301)
        assert circuit.is_half_open(clock())
        circuit.record(OE.TIMEOUT, endpoint=endpoint, now=clock(), probe=True)
        assert circuit.state == OE.OPEN and circuit.is_cooling_down(clock())
        assert circuit.cooldown_until > first_expiry
        assert circuit.cooldown_until == (clock.now + timedelta(seconds=300)).isoformat()

    def test_a_sibling_opened_circuit_re_arms_on_its_first_failed_trial(self):
        # Opened for its backend, not for its own failures: the count is 0,
        # and one failed trial after the cooldown must still re-open it.
        clock = Clock()
        endpoint = self._endpoint(threshold=3, cooldown=300)
        circuit = OE.EndpointCircuit(endpoint_id="a.example")
        circuit.open_as_sibling(endpoint=endpoint, now=clock(), because="sibling b opened")
        assert circuit.state == OE.OPEN and circuit.consecutive_failures == 0
        clock.advance(301)
        circuit.record(OE.HTTP_SERVER_ERROR, endpoint=endpoint, now=clock(), probe=True)
        assert circuit.is_cooling_down(clock())

    def test_it_round_trips_through_the_ledger_shape(self):
        circuit = OE.EndpointCircuit(endpoint_id="a.example", state=OE.OPEN,
                                     consecutive_failures=3, cooldown_until="2026-08-25T13:00:00+00:00")
        again = OE.EndpointCircuit.from_dict(circuit.to_dict())
        assert again == circuit


class TestSelector:
    def _selector(self, probe, clock=None, ledger=None, threshold=3, cooldown=900):
        registry = OE.EndpointRegistry.from_document(
            registry_doc("a.example", "b.example", threshold=threshold, cooldown=cooldown))
        return OE.EndpointSelector(registry=registry, probe=probe, clock=clock or Clock(),
                                   ledger_path=ledger)

    def test_the_first_healthy_endpoint_in_registry_order_is_chosen(self):
        probe = FakeProbe(**{"a.example": [OK], "b.example": [OK]})
        selector = self._selector(probe)
        assert selector.select().endpoint_id == "a.example"
        assert probe.calls == ["a.example"]          # b was never asked

    def test_an_unhealthy_primary_yields_the_secondary(self):
        probe = FakeProbe(**{"a.example": [TIMEOUT], "b.example": [OK]})
        selector = self._selector(probe)
        assert selector.select().endpoint_id == "b.example"
        assert selector.circuits["a.example"].consecutive_failures == 1

    def test_the_current_endpoint_is_kept_while_healthy_not_rotated(self):
        probe = FakeProbe(**{"a.example": [TIMEOUT, OK], "b.example": [OK]})
        selector = self._selector(probe)
        assert selector.select().endpoint_id == "b.example"
        assert selector.select().endpoint_id == "b.example"     # a is not re-probed
        assert probe.calls == ["a.example", "b.example", "b.example"]
        assert selector.switches == 0

    def test_a_cooling_down_endpoint_is_skipped_without_a_probe(self):
        clock = Clock()
        probe = FakeProbe(**{"a.example": [TIMEOUT], "b.example": [OK]})
        selector = self._selector(probe, clock=clock, threshold=1)
        selector.select()
        assert selector.circuits["a.example"].state == OE.OPEN
        probe.calls.clear()
        selector.select()
        assert probe.calls == ["b.example"]
        assert selector.states()["a.example"]["availability"] == "COOLING_DOWN"

    def test_no_healthy_endpoint_raises_with_states_and_the_earliest_expiry(self):
        clock = Clock()
        probe = FakeProbe(**{"a.example": [TIMEOUT], "b.example": [DOWN]})
        selector = self._selector(probe, clock=clock, threshold=1, cooldown=600)
        with pytest.raises(OE.NoHealthyEndpoint) as raised:
            selector.select()
        assert set(raised.value.states) == {"a.example", "b.example"}
        assert raised.value.earliest_cooldown_expiry == (
            clock.now + timedelta(seconds=600)).isoformat()
        assert selector.available_endpoints() == ()

    def test_a_dead_registry_costs_one_threshold_of_probes_per_cooldown(self):
        # PTF-PITTSBURGH-HARDENED-RECENSUS-001 Q4: with every endpoint down,
        # each select() used to re-probe every endpoint whose stale cooldown
        # had expired, so a supervised run accumulated hundreds of failures.
        clock = Clock()
        probe = FakeProbe(**{"a.example": [TIMEOUT], "b.example": [DOWN]})
        selector = self._selector(probe, clock=clock, threshold=3, cooldown=900)
        for _ in range(10):
            with pytest.raises(OE.NoHealthyEndpoint):
                selector.select()
            clock.advance(30)
        assert probe.calls.count("a.example") == 3 and probe.calls.count("b.example") == 3
        assert selector.states()["a.example"]["availability"] == "COOLING_DOWN"
        clock.advance(900)                      # past the cooldown: ONE trial each
        assert selector.states()["a.example"]["availability"] == OE.HALF_OPEN
        with pytest.raises(OE.NoHealthyEndpoint) as raised:
            selector.select()
        assert probe.calls.count("a.example") == 4 and probe.calls.count("b.example") == 4
        # ...and the trial's failure re-armed the cooldown, with a fresh expiry.
        assert raised.value.earliest_cooldown_expiry > clock.now.isoformat()
        with pytest.raises(OE.NoHealthyEndpoint):
            selector.select()
        assert probe.calls.count("a.example") == 4

    def test_the_ledger_carries_the_current_endpoint_and_switches_across_processes(self, tmp_path):
        # PTF-PITTSBURGH-HARDENED-RECENSUS-001 Q2/Q3: a fresh process started
        # with no current endpoint and zero switches, so a run that selected
        # nothing blanked the ledger's current_endpoint_id and a run of one
        # selection could never count a switch.
        ledger = tmp_path / "health.json"
        first = self._selector(FakeProbe(**{"a.example": [TIMEOUT], "b.example": [OK]}),
                               ledger=ledger)
        assert first.select().endpoint_id == "b.example"
        second = self._selector(FakeProbe(**{"a.example": [OK], "b.example": [DOWN]}),
                                ledger=ledger, threshold=1)
        assert second.current_id == "b.example"
        assert second.select().endpoint_id == "a.example"
        assert second.switches == 1
        third = self._selector(FakeProbe(**{"a.example": [TIMEOUT], "b.example": [DOWN]}),
                               ledger=ledger, threshold=1)
        assert third.current_id == "a.example" and third.switches == 1
        with pytest.raises(OE.NoHealthyEndpoint):
            third.select()
        persisted = json.loads(ledger.read_text(encoding="utf-8"))
        assert persisted["current_endpoint_id"] == "a.example"
        assert persisted["endpoint_switches"] == 1

    def test_a_failure_domain_opens_and_is_skipped_together(self):
        # Q6: b and c share a backend. b's probe fails to the threshold: c
        # opens with it, is never probed in that walk, and the pair count as
        # one available endpoint before and none after.
        doc = registry_doc("a.example", "b.example", "c.example", threshold=1, cooldown=900)
        doc["endpoints"][1]["failure_domain"] = "shared.backend"
        doc["endpoints"][2]["failure_domain"] = "shared.backend"
        registry = OE.EndpointRegistry.from_document(doc)
        clock = Clock()
        probe = FakeProbe(**{"a.example": [TIMEOUT], "b.example": [DOWN], "c.example": [OK]})
        selector = OE.EndpointSelector(registry=registry, probe=probe, clock=clock)
        assert selector.available_failure_domains() == ("a.example", "shared.backend")
        with pytest.raises(OE.NoHealthyEndpoint):
            selector.select()
        assert probe.calls == ["a.example", "b.example"]
        states = selector.states()
        assert states["b.example"]["availability"] == "COOLING_DOWN"
        # c's own circuit is OPEN now, with the same cooldown, and says why.
        assert states["c.example"]["availability"] == "COOLING_DOWN"
        assert states["c.example"]["cooldown_until"] == states["b.example"]["cooldown_until"]
        assert selector.circuits["c.example"].state == OE.OPEN
        assert "shared.backend" in selector.circuits["c.example"].opened_because
        assert selector.available_endpoints() == () and selector.available_failure_domains() == ()

    def test_a_request_failure_that_opens_a_circuit_opens_its_siblings(self):
        doc = registry_doc("b.example", "c.example", threshold=1)
        for row in doc["endpoints"]:
            row["failure_domain"] = "shared.backend"
        registry = OE.EndpointRegistry.from_document(doc)
        selector = OE.EndpointSelector(registry=registry, probe=FakeProbe(**{
            "b.example": [OK], "c.example": [OK]}), clock=Clock())
        b = selector.select()
        assert selector.record_request_failure(b, OE.HTTP_SERVER_ERROR) is True
        assert selector.circuits["c.example"].state == OE.OPEN

    def test_a_dead_endpoint_is_not_re_probed_for_every_cell(self):
        # Twenty selections (one per cell) after the primary failed once: the
        # secondary is kept while healthy and the primary is asked once, not
        # twenty times.
        probe = FakeProbe(**{"a.example": [TIMEOUT], "b.example": [OK]})
        selector = self._selector(probe, threshold=2)
        for _ in range(20):
            assert selector.select().endpoint_id == "b.example"
        assert probe.calls.count("a.example") == 1
        assert probe.calls.count("b.example") == 20

    def test_an_open_circuit_is_skipped_for_the_whole_cooldown(self):
        clock = Clock()
        probe = FakeProbe(**{"a.example": [TIMEOUT], "b.example": [OK]})
        selector = self._selector(probe, clock=clock, threshold=1, cooldown=900)
        for _ in range(20):
            selector.select()
            clock.advance(30)                    # ten minutes of cells
        assert probe.calls.count("a.example") == 1
        clock.advance(600)                       # past the cooldown
        probe.outcomes["a.example"] = [OK]
        selector.current_id = ""                 # a fresh run prefers registry order
        assert selector.select().endpoint_id == "a.example"

    def test_a_disabled_endpoint_is_never_probed(self):
        doc = registry_doc("a.example", "b.example")
        doc["endpoints"][0]["enabled"] = False
        registry = OE.EndpointRegistry.from_document(doc)
        probe = FakeProbe(**{"a.example": [OK], "b.example": [OK]})
        selector = OE.EndpointSelector(registry=registry, probe=probe, clock=Clock())
        assert selector.select().endpoint_id == "b.example"
        assert "a.example" not in probe.calls

    def test_the_ledger_persists_an_open_circuit_across_processes(self, tmp_path):
        ledger = tmp_path / "health.json"
        clock = Clock()
        probe = FakeProbe(**{"a.example": [TIMEOUT], "b.example": [OK]})
        first = self._selector(probe, clock=clock, ledger=ledger, threshold=1)
        first.select()
        document = json.loads(ledger.read_text(encoding="utf-8"))
        assert document["schema"] == OE.HEALTH_LEDGER_SCHEMA
        # A new selector (a resumed run) remembers the cooldown and skips a.
        probe2 = FakeProbe(**{"a.example": [OK], "b.example": [OK]})
        second = self._selector(probe2, clock=clock, ledger=ledger, threshold=1)
        assert second.circuits["a.example"].state == OE.OPEN
        assert second.select().endpoint_id == "b.example"
        assert probe2.calls == ["b.example"]

    def test_a_request_failure_after_selection_counts_toward_the_circuit(self):
        probe = FakeProbe(**{"a.example": [OK], "b.example": [OK]})
        selector = self._selector(probe, threshold=2)
        endpoint = selector.select()
        assert selector.record_request_failure(endpoint, OE.TIMEOUT) is False
        assert selector.record_request_failure(endpoint, OE.TIMEOUT) is True
        assert selector.circuits["a.example"].state == OE.OPEN

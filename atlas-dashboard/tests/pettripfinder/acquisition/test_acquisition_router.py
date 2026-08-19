"""PTF-ACQUISITION-ROUTER-001 -- the router's guarantees, tested.

The router's job is to choose, stop and account. So these tests are about
choosing (the right lane, the right reader, in the right precedence), stopping
(escalate a refusal, never escalate a silence, never exceed a budget) and
accounting (attempts, cost, a journal that survives a kill).

The extraction guarantees the three pilots established are re-asserted here
too, because the router is now the thing that runs them and a regression would
surface as a routing result rather than a reader test.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import budget as BUDGET
from scripts.pettripfinder.acquisition import envelope as ENV
from scripts.pettripfinder.acquisition import failures as F
from scripts.pettripfinder.acquisition import journal as JOURNAL
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import readers as READERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.acquisition import router as ROUTER
from scripts.pettripfinder.acquisition import router_smoke_001 as SMOKE
from scripts.pettripfinder.brightdata import browser_capture as BC
from scripts.pettripfinder.brightdata import client
from scripts.pettripfinder.brightdata import corpus as CORPUS
from scripts.pettripfinder.brightdata import outcomes as CAPTURE
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.contracts import enums

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# --------------------------------------------------------------------------- #
# Failure vocabulary: the escalation rule.
# --------------------------------------------------------------------------- #

def test_the_failure_vocabulary_is_closed_and_partitioned():
    families = [F.TECHNICAL, F.IDENTITY, F.POLICY, F.SOURCE, F.BUDGET]
    flat = [f for family in families for f in family]
    assert sorted(flat) == sorted(F.FAILURES)
    assert len(flat) == len(set(flat)), "a failure belongs to one family"


def test_escalating_and_terminal_partition_the_vocabulary():
    assert F.ESCALATING | F.TERMINAL == set(F.FAILURES)
    assert not (F.ESCALATING & F.TERMINAL)


@pytest.mark.parametrize("failure", [
    F.ACCESS_DENIED, F.BLANK_PAGE, F.UNHYDRATED, F.NAVIGATION_FAILED,
    F.CAPTURE_FAILED, F.UNEXPECTED_PAGE, F.GEO_MISMATCH,
    F.PROVIDER_UNAVAILABLE, F.TIMEOUT,
])
def test_technical_failures_escalate(failure):
    """A refusal is about the channel, and another channel may answer."""
    assert F.may_escalate(failure)


@pytest.mark.parametrize("failure", [
    F.POLICY_NOT_FOUND, F.SOURCE_AMBIGUOUS, F.SOURCE_CONTRADICTORY,
    F.UNSUPPORTED_SCHEMA_SHAPE, F.UNSUPPORTED_DURATION, F.IDENTITY_MISMATCH,
    F.BUDGET_EXHAUSTED, F.ATTEMPTS_EXHAUSTED, F.POLICY_SURFACE_INCOMPLETE,
])
def test_semantic_and_source_failures_never_escalate(failure):
    """A better crawler cannot fix what the source itself left unclear."""
    assert not F.may_escalate(failure)


def test_identity_mismatch_and_identity_uncertain_are_not_the_same():
    """One says 'a different hotel'; the other says 'we could not tell'."""
    assert not F.may_escalate(F.IDENTITY_MISMATCH)
    assert F.may_escalate(F.IDENTITY_UNCERTAIN)


def test_every_capture_outcome_translates():
    for outcome in CAPTURE.OUTCOMES:
        if outcome == CAPTURE.VALID:
            with pytest.raises(ValueError):
                F.from_capture_outcome(outcome)
            continue
        assert F.is_failure(F.from_capture_outcome(outcome))


def test_an_unknown_capture_outcome_is_refused():
    with pytest.raises(ValueError):
        F.from_capture_outcome("SOMETHING_NEW")


def test_withholding_reasons_map_to_source_failures():
    assert F.from_withholding("SOURCE_CONTRADICTORY") == F.SOURCE_CONTRADICTORY
    assert F.from_withholding("SCHEMA_CANNOT_REPRESENT") == \
        F.UNSUPPORTED_SCHEMA_SHAPE
    assert F.from_withholding("SOURCE_SILENT") == ""


# --------------------------------------------------------------------------- #
# Providers.
# --------------------------------------------------------------------------- #

def test_three_providers_are_implemented_and_one_slot_is_reserved():
    """Firecrawl was added by PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006.

    This assertion previously read "two", deliberately, because an adapter
    existing is not grounds to route to it. It reads "three" now because
    Firecrawl earned the row the way that comment always required: 15/15 on
    the Milwaukee Choice queue against the incumbent's 7/15. The change is a
    decision, not a maintenance edit.
    """
    assert set(PROVIDERS.implemented()) == {PROVIDERS.BRIGHTDATA_BROWSER,
                                            PROVIDERS.BRIGHTDATA_WEB_UNLOCKER,
                                            PROVIDERS.FIRECRAWL}
    assert PROVIDERS.DIRECT_HTTP in PROVIDERS.all_ids()
    assert PROVIDERS.DIRECT_HTTP not in PROVIDERS.implemented()


def test_the_reserved_slot_is_unavailable_and_refuses_to_run():
    reserved = PROVIDERS.get(PROVIDERS.DIRECT_HTTP)
    assert not reserved.health_check().available
    with pytest.raises(RuntimeError):
        asyncio.run(reserved.acquire(None, run_dir=Path("."),
                                     reader_id="generic", max_attempts=1))


def test_future_providers_are_documented_and_not_implemented():
    """Firecrawl is no longer on this list; spider still is, and on purpose.

    Spider was benchmarked and FAILED -- 7 of 25 properties, returning
    JavaScript shells. Being measured is what gets a provider onto a route;
    being measured is not the same as passing.
    """
    for name in ("spider", "apify", "playwright_local"):
        assert name in PROVIDERS.KNOWN_FUTURE_PROVIDERS
        assert name not in PROVIDERS.all_ids()
    assert "firecrawl" not in PROVIDERS.KNOWN_FUTURE_PROVIDERS
    assert "firecrawl" in PROVIDERS.all_ids()


def test_providers_are_described_by_capability_not_by_vendor():
    browser = PROVIDERS.get(PROVIDERS.BRIGHTDATA_BROWSER)
    unlocker = PROVIDERS.get(PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    assert PROVIDERS.RUNS_JAVASCRIPT in browser.capabilities
    assert PROVIDERS.CAN_INTERACT in browser.capabilities
    assert PROVIDERS.RUNS_JAVASCRIPT not in unlocker.capabilities
    assert PROVIDERS.BYPASSES_BOT_PROTECTION in unlocker.capabilities


def test_the_unlocker_is_the_cheaper_lane_as_measured():
    browser = PROVIDERS.get(PROVIDERS.BRIGHTDATA_BROWSER).cost_metadata()
    unlocker = PROVIDERS.get(PROVIDERS.BRIGHTDATA_WEB_UNLOCKER).cost_metadata()
    assert unlocker.usd_minor_per_property < browser.usd_minor_per_property
    for cost in (browser, unlocker):
        assert cost.measured_by, "a cost with no measurement is a guess"


def test_the_plug_in_point_is_real():
    class _Fake:
        provider_id = "fake_provider_for_test"
        product = "test"
        capabilities = frozenset()

        def health_check(self):
            return PROVIDERS.ProviderHealth(False, "test only")

        def cost_metadata(self):
            return PROVIDERS.CostMetadata(None, "n/a", "n/a")

        def supported_failure_recovery(self):
            return frozenset()

        async def acquire(self, *a, **k):
            raise AssertionError("never called")

    try:
        PROVIDERS.register(_Fake())
        assert "fake_provider_for_test" in PROVIDERS.all_ids()
    finally:
        PROVIDERS._PROVIDERS.pop("fake_provider_for_test", None)


# --------------------------------------------------------------------------- #
# Readers, and their separation from providers.
# --------------------------------------------------------------------------- #

def test_reader_selection_is_independent_of_provider_selection():
    """One provider serves several readers; one reader will serve several
    providers. Coupling them makes every new provider a reader rewrite."""
    source = inspect.getsource(READERS)
    assert "brightdata" not in source.lower().replace(
        "scripts.pettripfinder.brightdata", "")
    registry = REGISTRY.load()
    marriott = REGISTRY.resolve(brand="MARRIOTT",
                                url="https://www.marriott.com/en-us/hotels/x/",
                                registry=registry)
    wyndham = REGISTRY.resolve(brand="WYNDHAM",
                               url="https://www.wyndhamhotels.com/x",
                               registry=registry)
    assert marriott.provider == wyndham.provider
    assert marriott.reader != wyndham.reader


def test_every_registry_reader_exists():
    registry = REGISTRY.load()
    for entry in list((registry.get("brands") or {}).values()) + \
            list((registry.get("domains") or {}).values()) + \
            [registry.get("default") or {}]:
        if entry.get("reader"):
            READERS.get(entry["reader"])


def test_an_unknown_reader_is_refused():
    with pytest.raises(READERS.ReaderError):
        READERS.get("no_such_reader")


def test_wyndham_reader_names_the_container_the_page_never_paints():
    assert READERS.locator_brand_for("wyndham") == "WYNDHAM"
    assert READERS.brand_locator_exists("wyndham")


def test_the_generic_reader_names_no_container():
    assert READERS.locator_brand_for("generic") == ""
    assert not READERS.brand_locator_exists("generic")


# --------------------------------------------------------------------------- #
# The routing registry.
# --------------------------------------------------------------------------- #

def test_choice_never_defaults_to_the_browser_api():
    """15 attempts, 14 ACCESS_DENIED, 0 captures. The lane is measured shut.

    The Choice PRIMARY changed to Firecrawl in
    PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006. This rule did not, and it must
    not: the Browser API stays off the Choice ladder entirely, whoever leads
    it. A route change is not an occasion to relitigate a separate measurement.
    """
    route = REGISTRY.resolve(
        brand="CHOICE",
        url="https://www.choicehotels.com/ohio/canton/comfort-inn-hotels/oh440")
    assert route.provider == PROVIDERS.FIRECRAWL
    assert PROVIDERS.BRIGHTDATA_WEB_UNLOCKER in route.ladder
    assert PROVIDERS.BRIGHTDATA_BROWSER not in route.ladder
    assert PROVIDERS.BRIGHTDATA_BROWSER in route.forbidden_providers


def test_a_forbidden_provider_is_removed_from_the_ladder_entirely():
    route = REGISTRY.Route(
        provider="brightdata_web_unlocker",
        fallback_providers=("brightdata_browser",), reader="choice_static",
        max_attempts_per_provider=3, resolved_by="test", why="t",
        measured_by="t", forbidden_providers=("brightdata_browser",))
    assert route.ladder == ("brightdata_web_unlocker",)


def test_a_route_may_not_both_prefer_and_forbid_a_provider():
    registry = {"default": {}, "brands": {"X": {
        "provider": "brightdata_browser",
        "forbidden_providers": ["brightdata_browser"],
        "why": "t", "measured_by": "t"}}}
    with pytest.raises(REGISTRY.RegistryError):
        REGISTRY.resolve(brand="X", url="https://x.test/y", registry=registry)


@pytest.mark.parametrize("brand,provider,reader", [
    ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER, "marriott"),
    ("HILTON", PROVIDERS.BRIGHTDATA_BROWSER, "hilton_competing"),
    ("IHG", PROVIDERS.BRIGHTDATA_BROWSER, "ihg"),
    ("WYNDHAM", PROVIDERS.BRIGHTDATA_BROWSER, "wyndham"),
    ("CHOICE", PROVIDERS.FIRECRAWL, "choice_static"),
])
def test_brand_routes_match_what_the_pilots_measured(brand, provider, reader):
    hosts = {"MARRIOTT": "www.marriott.com", "HILTON": "www.hilton.com",
             "IHG": "www.ihg.com", "WYNDHAM": "www.wyndhamhotels.com",
             "CHOICE": "www.choicehotels.com"}
    route = REGISTRY.resolve(brand=brand,
                             url="https://%s/property" % hosts[brand])
    assert route.provider == provider
    assert route.reader == reader


def test_an_unknown_brand_gets_the_default_lane():
    route = REGISTRY.resolve(brand="NEVER_HEARD_OF_IT",
                             url="https://www.example-inn.test/a/b/c")
    assert route.resolved_by == "default"
    assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
    assert route.reader == "generic"


def test_override_precedence_is_property_then_domain_then_brand():
    registry = {
        "default": {"provider": "brightdata_browser", "reader": "generic"},
        "brands": {"MARRIOTT": {"provider": "brightdata_browser",
                                "reader": "marriott", "why": "t",
                                "measured_by": "t"}},
        "domains": {"www.marriott.com": {"reader": "generic", "why": "t",
                                         "measured_by": "t"}},
        "properties": {"the one hotel": {
            "provider": "brightdata_web_unlocker", "reader": "choice_static",
            "why": "t", "measured_by": "t"}},
    }
    url = "https://www.marriott.com/en-us/hotels/x/overview/"
    brand_only = REGISTRY.resolve(brand="MARRIOTT", url="https://other.test/x",
                                  registry=registry)
    assert brand_only.resolved_by.startswith("brand:")
    assert brand_only.reader == "marriott"

    domain_wins = REGISTRY.resolve(brand="MARRIOTT", url=url, registry=registry)
    assert domain_wins.resolved_by.startswith("domain:")
    assert domain_wins.reader == "generic"

    property_wins = REGISTRY.resolve(brand="MARRIOTT", url=url,
                                     identity_key="the one hotel",
                                     registry=registry)
    assert property_wins.resolved_by.startswith("property:")
    assert property_wins.provider == PROVIDERS.BRIGHTDATA_WEB_UNLOCKER


def test_a_route_must_cite_the_run_that_set_it(tmp_path):
    """A route that cannot name its benchmark is an opinion."""
    path = tmp_path / "routes.json"
    path.write_text(json.dumps({
        "schema": "ptf-acquisition-routes/1.0", "version": 1,
        "default": {"provider": "brightdata_browser", "reader": "generic"},
        "brands": {"X": {"provider": "brightdata_browser",
                         "reader": "generic"}},
        "domains": {}, "properties": {}}), encoding="utf-8")
    with pytest.raises(REGISTRY.RegistryError) as caught:
        REGISTRY.load(path)
    assert "measured_by" in str(caught.value)


def test_a_route_naming_an_unregistered_provider_is_refused(tmp_path):
    path = tmp_path / "routes.json"
    path.write_text(json.dumps({
        "schema": "ptf-acquisition-routes/1.0", "version": 1,
        "default": {"provider": "brightdata_browser", "reader": "generic"},
        "brands": {"X": {"provider": "some_vendor_nobody_built",
                         "reader": "generic", "why": "t",
                         "measured_by": "t"}},
        "domains": {}, "properties": {}}), encoding="utf-8")
    with pytest.raises(REGISTRY.RegistryError):
        REGISTRY.load(path)


def test_the_committed_registry_loads_and_validates():
    data = REGISTRY.load()
    assert data["schema"] == "ptf-acquisition-routes/1.0"
    assert REGISTRY.brands()
    for brand in REGISTRY.brands():
        entry = data["brands"][brand]
        assert entry.get("why") and entry.get("measured_by")


def test_premium_brands_stay_excluded():
    excluded = REGISTRY.excluded_brands()
    assert "HYATT" in excluded and "BEST_WESTERN" in excluded
    assert REGISTRY.is_excluded("hyatt")
    assert not REGISTRY.is_excluded("MARRIOTT")


# --------------------------------------------------------------------------- #
# Budgets.
# --------------------------------------------------------------------------- #

def test_a_budget_stops_before_the_money_does():
    ledger = BUDGET.BudgetLedger(budget=BUDGET.Budget(max_total_attempts=4))
    assert not ledger.exhausted()
    ledger.record(attempts=4, elapsed_seconds=1.0)
    assert "total attempts" in ledger.exhausted()


def test_a_cost_ceiling_is_checked_before_spending_more():
    ledger = BUDGET.BudgetLedger(
        budget=BUDGET.Budget(max_property_cost_usd_minor=10.0))
    ledger.record(attempts=1, elapsed_seconds=1.0, estimated_usd_minor=10.5)
    assert "estimated cost" in ledger.exhausted()


def test_an_elapsed_ceiling_is_enforced():
    ledger = BUDGET.BudgetLedger(
        budget=BUDGET.Budget(max_elapsed_seconds=30.0))
    ledger.record(attempts=1, elapsed_seconds=31.0)
    assert "elapsed" in ledger.exhausted()


def test_the_last_provider_cannot_overrun_the_total():
    ledger = BUDGET.BudgetLedger(
        budget=BUDGET.Budget(max_attempts_per_provider=3,
                             max_total_attempts=4))
    ledger.record(attempts=3, elapsed_seconds=1.0)
    assert ledger.attempts_for_next_provider() == 1


# --------------------------------------------------------------------------- #
# The journal: durability, resume, idempotency, claims.
# --------------------------------------------------------------------------- #

def test_a_completed_property_is_durable_immediately(tmp_path):
    book = JOURNAL.Journal(tmp_path / "progress.jsonl")
    book.append({"identity_key": "a hotel", "state": "ACQUIRED"})
    assert JOURNAL.Journal(tmp_path / "progress.jsonl").has("a hotel")


def test_a_torn_last_line_is_discarded_not_parsed(tmp_path):
    """The signature of a kill mid-write. Losing one is right; inventing is not."""
    path = tmp_path / "progress.jsonl"
    path.write_text('{"identity_key": "good", "state": "ACQUIRED"}\n'
                    '{"identity_key": "half', encoding="utf-8")
    book = JOURNAL.Journal(path)
    assert set(book.read()) == {"good"}


def test_resume_skips_completed_identities(tmp_path):
    book = JOURNAL.Journal(tmp_path / "p.jsonl")
    for key in ("one", "two"):
        book.append({"identity_key": key})
    remaining = [k for k in ("one", "two", "three")
                 if k not in book.completed_keys()]
    assert remaining == ["three"]


def test_re_running_does_not_duplicate_an_acquisition(tmp_path):
    book = JOURNAL.Journal(tmp_path / "p.jsonl")
    book.append({"identity_key": "same", "run": 1})
    book.append({"identity_key": "same", "run": 2})
    # Keyed by identity, so the journal holds one property however many times
    # it was written, and reconciliation reports the duplicate.
    assert len(book.read()) == 1
    report = JOURNAL.reconcile(book, ["same"])
    assert report["duplicate_identities"] == ["same"]
    assert not report["passed"]


def test_reconciliation_catches_a_missing_or_extra_property(tmp_path):
    book = JOURNAL.Journal(tmp_path / "p.jsonl")
    book.append({"identity_key": "one"})
    assert JOURNAL.reconcile(book, ["one"])["passed"]
    assert JOURNAL.reconcile(book, ["one", "two"])["missing"] == ["two"]
    assert JOURNAL.reconcile(book, [])["unexpected"] == ["one"]


def test_two_workers_cannot_acquire_the_same_property(tmp_path):
    book = JOURNAL.Journal(tmp_path / "p.jsonl")
    with book.claim("one hotel"):
        assert "one hotel" in book.held()
        with pytest.raises(JOURNAL.ClaimConflict):
            with book.claim("one hotel"):
                pass
    assert not book.held()


def test_the_journal_redacts_before_writing(tmp_path, monkeypatch):
    monkeypatch.setenv(client.AUTH_ENV, "brd-customer-a-zone-z:pw@h:9222")
    book = JOURNAL.Journal(tmp_path / "p.jsonl")
    book.append({"identity_key": "x",
                 "detail": "wss://brd-customer-a-zone-z:pw@h:9222 failed"})
    text = (tmp_path / "p.jsonl").read_text(encoding="utf-8")
    assert not client.contains_credential(text)


# --------------------------------------------------------------------------- #
# The router's decisions, driven by scripted providers.
# --------------------------------------------------------------------------- #

def _record(brand="MARRIOTT", key="test hotel"):
    return CORPUS.BenchmarkRecord(
        identity_key=key, name="Test Hotel", market_id="m", brand=brand,
        bucket=brand, source_url="https://www.marriott.com/en-us/hotels/x/",
        pets_allowed=True, facts={"pets_allowed": True}, quotes=(),
        withheld_fields={}, service_animal_statement="",
        categories=frozenset(), origin="policy_record")


def _target():
    return BC.CaptureTarget(
        slug="t", hotel="Test Hotel",
        requested_url="https://www.marriott.com/en-us/hotels/x/",
        property_code="", market_id="m", normalized_name="test hotel")


def _capture(attempt, outcome):
    return BC.AttemptRecord(
        attempt=attempt, outcome=outcome,
        started_at="2026-08-18T00:00:00+00:00",
        ended_at="2026-08-18T00:00:05+00:00", elapsed_seconds=5.0,
        requested_url="https://www.marriott.com/en-us/hotels/x/",
        network={"encoded_bytes": 1000})


class _ScriptedProvider:
    """A provider that returns a fixed sequence of outcomes, no network."""

    def __init__(self, provider_id, outcomes):
        self.provider_id = provider_id
        self.product = provider_id
        self.capabilities = frozenset()
        self._outcomes = outcomes
        self.calls = 0

    def health_check(self):
        return PROVIDERS.ProviderHealth(True, "scripted")

    def cost_metadata(self):
        return PROVIDERS.CostMetadata(1.0, "test", "test")

    def supported_failure_recovery(self):
        return frozenset()

    async def acquire(self, target, *, run_dir, reader_id, max_attempts):
        self.calls += 1
        taken = self._outcomes[:max_attempts]
        return [_capture(i + 1, o) for i, o in enumerate(taken)], None


def _route_with(monkeypatch, registry, providers):
    for provider in providers.values():
        monkeypatch.setitem(PROVIDERS._PROVIDERS, provider.provider_id,
                            provider)
    return asyncio.run(ROUTER.route_property(
        _record(brand="TESTBRAND"), _target(), run_dir=Path("."),
        run_id="test", registry=registry))


def _registry(provider, fallbacks=(), forbidden=()):
    return {"default": {"provider": provider, "reader": "generic",
                        "fallback_providers": list(fallbacks),
                        "forbidden_providers": list(forbidden)},
            "brands": {}, "domains": {}, "properties": {}}


def test_a_technical_refusal_escalates_to_the_next_provider(monkeypatch):
    first = _ScriptedProvider("p_first", [CAPTURE.ACCESS_DENIED] * 3)
    second = _ScriptedProvider("p_second", [CAPTURE.ACCESS_DENIED] * 3)
    result = _route_with(monkeypatch,
                         _registry("p_first", ["p_second"]),
                         {"a": first, "b": second})
    assert first.calls == 1 and second.calls == 1
    assert result.providers_tried == ("p_first", "p_second")
    assert result.state == ENV.PROVIDER_EXHAUSTED


def test_a_silence_does_not_escalate(monkeypatch):
    """POLICY_NOT_FOUND means the page answered. A second lane finds the same
    nothing, at the same price."""
    first = _ScriptedProvider("p_first", [CAPTURE.POLICY_NOT_FOUND])
    second = _ScriptedProvider("p_second", [CAPTURE.ACCESS_DENIED])
    result = _route_with(monkeypatch,
                         _registry("p_first", ["p_second"]),
                         {"a": first, "b": second})
    assert second.calls == 0, "escalating a silence is waste"
    assert result.state == ENV.POLICY_NOT_FOUND
    assert "terminal" in result.escalation_stopped_because


def test_an_identity_mismatch_does_not_escalate(monkeypatch):
    """It will be a different hotel through every provider."""
    first = _ScriptedProvider("p_first", [CAPTURE.IDENTITY_MISMATCH])
    second = _ScriptedProvider("p_second", [CAPTURE.ACCESS_DENIED])
    result = _route_with(monkeypatch,
                         _registry("p_first", ["p_second"]),
                         {"a": first, "b": second})
    assert second.calls == 0
    assert result.state == ENV.IDENTITY_REVIEW


def test_a_forbidden_provider_is_never_called(monkeypatch):
    allowed = _ScriptedProvider("p_allowed", [CAPTURE.ACCESS_DENIED] * 3)
    forbidden = _ScriptedProvider("p_forbidden", [CAPTURE.ACCESS_DENIED])
    result = _route_with(
        monkeypatch,
        _registry("p_allowed", ["p_forbidden"], forbidden=["p_forbidden"]),
        {"a": allowed, "b": forbidden})
    assert forbidden.calls == 0
    assert "p_forbidden" not in result.providers_tried


def test_the_total_attempt_budget_stops_escalation(monkeypatch):
    first = _ScriptedProvider("p_first", [CAPTURE.ACCESS_DENIED] * 3)
    second = _ScriptedProvider("p_second", [CAPTURE.ACCESS_DENIED] * 3)
    for provider in (first, second):
        monkeypatch.setitem(PROVIDERS._PROVIDERS, provider.provider_id,
                            provider)
    config = ROUTER.RouterConfig(budget=BUDGET.Budget(
        max_attempts_per_provider=3, max_total_attempts=3))
    result = asyncio.run(ROUTER.route_property(
        _record(brand="TESTBRAND"), _target(), run_dir=Path("."),
        run_id="test", config=config,
        registry=_registry("p_first", ["p_second"])))
    assert second.calls == 0
    assert result.state == ENV.BUDGET_EXHAUSTED
    assert "budget" in result.escalation_stopped_because


def test_an_unavailable_provider_is_skipped_not_crashed_into(monkeypatch):
    class _Down(_ScriptedProvider):
        def health_check(self):
            return PROVIDERS.ProviderHealth(False, "no credential")

    down = _Down("p_down", [])
    up = _ScriptedProvider("p_up", [CAPTURE.ACCESS_DENIED] * 3)
    result = _route_with(monkeypatch, _registry("p_down", ["p_up"]),
                         {"a": down, "b": up})
    assert up.calls == 1
    assert any(a.failure == F.PROVIDER_UNAVAILABLE for a in result.attempts)


def test_every_result_carries_exactly_one_state_from_the_closed_set(monkeypatch):
    for outcome in (CAPTURE.ACCESS_DENIED, CAPTURE.POLICY_NOT_FOUND,
                    CAPTURE.IDENTITY_MISMATCH, CAPTURE.UNHYDRATED):
        provider = _ScriptedProvider("p_only", [outcome])
        result = _route_with(monkeypatch, _registry("p_only"),
                             {"a": provider})
        assert result.state in ENV.ROUTER_STATES
        assert not result.acquired


def test_no_property_is_silently_dropped(monkeypatch):
    provider = _ScriptedProvider("p_only", [CAPTURE.ACCESS_DENIED] * 3)
    result = _route_with(monkeypatch, _registry("p_only"), {"a": provider})
    assert result.state
    assert result.failure
    assert result.failure_class == "TECHNICAL"


# --------------------------------------------------------------------------- #
# Provider success is not evidence success.
# --------------------------------------------------------------------------- #

def test_acquired_and_publication_grade_are_different_fields():
    assert ENV.ACQUIRED_NONPUBLICATION_GRADE in ENV.ACQUIRED_STATES
    assert ENV.ACQUIRED_NONPUBLICATION_GRADE not in ENV.PUBLICATION_GRADE_STATES
    assert ENV.PUBLICATION_GRADE_STATES == {ENV.ACQUIRED_PUBLICATION_GRADE}


def test_the_router_never_decides_publication_grade_itself():
    source = inspect.getsource(ROUTER)
    assert "PG.assess" in source
    assert "PUBLICATION_GRADE_CONFIRMED" not in source.replace(
        'get(\n            "verdict") == "PUBLICATION_GRADE_CONFIRMED"', "")


def test_a_document_reads_its_grade_from_the_contract():
    doc = ENV.SourceDocument(
        identity_key="k", brand="B", source_url="u", final_url="u",
        provider="p", provider_product="pp", reader="generic",
        capture_method="browser_assisted", fetched_at="t", status="VALID",
        publication_grade={"verdict": "PUBLICATION_GRADE_REJECTED"})
    assert not doc.is_publication_grade


# --------------------------------------------------------------------------- #
# Extraction guarantees the router now runs.
# --------------------------------------------------------------------------- #

def test_money_safety_survives_the_router_layer():
    for block, expect_fee in (
        ("1 King Bed 4 Guests No Pets Allowed Discounted rate: $160 USD /night",
         None),
        ("General: Pets are Allowed. 25.00 USD Per Pet per night. "
         "100.00 USD refundable deposit required.", 2500),
        ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: $150.00",
         15000),
    ):
        result = PR.to_extraction(PR.parse(block), location="b")
        assert result.extraction.get("pet_fee") == expect_fee, block


def test_a_deposit_is_still_never_the_fee():
    result = PR.to_extraction(PR.parse(
        "General: Pets are Allowed. 25.00 USD Per Pet per night. "
        "100.00 USD refundable deposit required."), location="b")
    assert result.extraction["pet_deposit"] == 10000
    assert result.extraction["pet_fee"] == 2500


def test_the_pet_refusal_qualifier_still_holds():
    assert PR.parse("Pets are welcome. Pets are not allowed to be left alone "
                    "in room.").pets_allowed is True
    assert PR.parse("Sorry no other pets are allowed.").pets_allowed is False


def test_an_unsupported_conditional_charge_is_still_withheld():
    result = PR.to_extraction(PR.parse(
        "Pets Welcome Dogs/Cats only - max 2 per room. $50 pet fee/per pet "
        "40lbs or over. Maximum Pet Weight: 40.0lbs"), location="b")
    assert "pet_fee" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_a_contradiction_is_still_a_contradiction():
    result = PR.to_extraction(PR.parse(
        "Pet Policy Pets Welcome Pet fee $20/day with $100/stay nonrefundable "
        "clean fee Non-Refundable Pet Fee Per Stay: $100.00 "
        "Non-Refundable Pet Fee Per Night: $20.00"), location="b")
    assert result.extraction["pet_fee"] == 2000
    assert result.withheld["fee_basis"] == enums.SOURCE_CONTRADICTORY


def test_no_unsupported_inference_survives_the_router_layer():
    result = PR.to_extraction(PR.parse(
        "Pets welcome. Maximum Pet Weight: 50.0lbs"), location="b")
    limit = result.extraction["weight_limit"]
    assert "operator" not in limit and "scope" not in limit


# --------------------------------------------------------------------------- #
# The smoke benchmark's own shape.
# --------------------------------------------------------------------------- #

def test_the_smoke_sample_is_twelve_two_per_bucket():
    sample = SMOKE.build_sample()
    assert len(sample) == SMOKE.SMOKE_SIZE == 12
    counts = {}
    for record in sample:
        counts[record.bucket] = counts.get(record.bucket, 0) + 1
    assert all(counts[b] == SMOKE.PER_BUCKET for b in CORPUS.BUCKETS)


def test_the_smoke_sample_comes_from_pilot_002():
    from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2
    known = {r.identity_key for r in P2.build_sample()}
    assert all(r.identity_key in known for r in SMOKE.build_sample())


def test_expected_routes_are_asserted_not_read_back():
    """A registry edit that re-routes Choice must FAIL this benchmark.

    The pinned value moved to Firecrawl in
    PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006. The mechanism did not: the
    expectation is still hard-coded here rather than read from the registry,
    so the NEXT unannounced re-route still fails this test instead of passing
    it. That, and not the particular provider, is what this test protects.
    """
    assert SMOKE.EXPECTED_ROUTE["CHOICE"][0] == PROVIDERS.FIRECRAWL
    assert SMOKE.EXPECTED_ROUTE["CHOICE"][0] != PROVIDERS.BRIGHTDATA_BROWSER
    source = inspect.getsource(SMOKE)
    assert "EXPECTED_ROUTE: Dict" in source


def test_every_smoke_property_routes_as_expected():
    registry = REGISTRY.load()
    from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2
    for record in SMOKE.build_sample():
        target = P2.target_for(record)
        route = REGISTRY.resolve(brand=record.brand, url=target.requested_url,
                                 identity_key=record.identity_key,
                                 registry=registry)
        want_provider, want_reader = SMOKE.expected_route_for(record)
        assert (route.provider, route.reader) == (want_provider, want_reader), \
            record.name


def test_the_gate_fails_when_a_gate_fails():
    summary = {"route_selection_accuracy": 11, "wrong_provider_default": 1,
               "false_identity_acceptance": 0, "false_verified_no_pets": 0,
               "unsupported_inference": 0,
               "publication_grade_among_valid": 100.0,
               "choice_browser_default_calls": 0,
               "journal_reconciliation": {"passed": True},
               "lanes": {lane: {"critical_recall_percent": 100.0}
                         for lane in SMOKE.RECALL_FLOORS}}
    result = SMOKE.gate(summary)
    assert not result["passed"]
    assert "route_selection_accuracy_12_of_12" in result["failed"]


# --------------------------------------------------------------------------- #
# Authority and credentials.
# --------------------------------------------------------------------------- #

def test_the_router_writes_no_authority():
    for module in (ROUTER, REGISTRY, PROVIDERS, READERS, JOURNAL, SMOKE,
                   BUDGET, ENV, F):
        source = inspect.getsource(module)
        for forbidden in ("promote_", "publication_guard", "apply_decisions",
                          "PUBLISHED_PET_FRIENDLY", "hotel_exclusions",
                          "identity_routing", "seed_businesses"):
            assert forbidden not in source, (module.__name__, forbidden)


def test_the_router_writes_only_to_its_own_raw_tree_and_reports():
    assert SMOKE.RAW_ROOT.parts[-4:] == ("worker_runs", "pettripfinder",
                                         "ptf-acquisition-router-001", "raw")
    for path in (SMOKE.SUMMARY_REPORT, SMOKE.ROUTES_REPORT,
                 SMOKE.COMPARISON_REPORT):
        assert path.parent == SMOKE.REPORT_DIR


def test_no_module_prints_a_credential():
    for module in (ROUTER, REGISTRY, PROVIDERS, JOURNAL, SMOKE):
        source = inspect.getsource(module)
        assert "browser_endpoint()" not in source or "print" not in source


# --------------------------------------------------------------------------- #
# Committed outputs.
# --------------------------------------------------------------------------- #

def _load(path):
    if not path.exists():
        pytest.skip("%s has not been produced yet" % path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_router_reports_carry_no_credential():
    for path in (SMOKE.SUMMARY_REPORT, SMOKE.ROUTES_REPORT,
                 SMOKE.COMPARISON_REPORT):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert not client.contains_credential(text), path.name
        for shape in ("brd-customer", "superproxy", "wss://"):
            assert shape not in text, (path.name, shape)


def test_committed_router_summary_freezes_authority():
    summary = _load(SMOKE.SUMMARY_REPORT)
    for key in ("policy_authority_changed", "exclusions_changed",
                "seeds_changed", "approvals_changed",
                "routing_authority_changed", "partition_changed",
                "promotion_performed"):
        assert summary[key] is False, key
    assert summary["total"] == SMOKE.SMOKE_SIZE
    assert summary["choice_browser_default_calls"] == 0
    assert summary["false_verified_no_pets"] == 0
    assert summary["unsupported_inference"] == 0


def test_committed_router_routed_everything_correctly():
    summary = _load(SMOKE.SUMMARY_REPORT)
    assert summary["route_selection_accuracy"] == SMOKE.SMOKE_SIZE
    assert summary["wrong_provider_default"] == 0


def test_committed_router_results_carry_one_state_each():
    report = _load(SMOKE.ROUTES_REPORT)
    for result in report["results"]:
        assert result["state"] in ENV.ROUTER_STATES
        assert result["authority_changed"] is False
        assert result["route_selected_correctly"] is True


def test_committed_router_artifacts_hash():
    report = _load(SMOKE.ROUTES_REPORT)
    checked = 0
    for result in report["results"]:
        document = result.get("document")
        if not document:
            continue
        for name, entry in (document.get("artifacts", {}).get("files")
                            or {}).items():
            if not isinstance(entry, dict) or "sha256" not in entry:
                continue
            assert _SHA256_RE.match(entry["sha256"])
            path = Path(entry["path"])
            if path.exists():
                assert BC.sha256_file(path) == entry["sha256"], path
                checked += 1
    if checked == 0:
        pytest.skip("the gitignored raw tree is not present here")


# --------------------------------------------------------------------------- #
# No retry waste: the capture layer and the router layer must agree.
# --------------------------------------------------------------------------- #

def test_the_capture_layer_and_the_router_layer_agree_on_what_is_terminal():
    """Two vocabularies that must match, declared apart, checked here.

    ``outcomes.NO_RETRY_OUTCOMES`` lives in the capture layer so it need not
    import the router; that independence is only safe while a test asserts they
    say the same thing.
    """
    mapped = {F.from_capture_outcome(o) for o in CAPTURE.NO_RETRY_OUTCOMES}
    assert mapped <= F.TERMINAL, "the capture layer would retry what the "
    retryable = {o for o in CAPTURE.OUTCOMES
                 if o != CAPTURE.VALID and CAPTURE.worth_retrying(o)}
    assert {F.from_capture_outcome(o) for o in retryable} <= F.ESCALATING


@pytest.mark.parametrize("outcome,retry", [
    (CAPTURE.ACCESS_DENIED, True),
    (CAPTURE.BLANK_PAGE, True),
    (CAPTURE.UNHYDRATED, True),
    (CAPTURE.NAVIGATION_FAILED, True),
    (CAPTURE.UNEXPECTED_PAGE, True),
    (CAPTURE.CAPTURE_FAILED, True),
    (CAPTURE.IDENTITY_MISMATCH, False),
    (CAPTURE.POLICY_NOT_FOUND, False),
])
def test_only_channel_failures_are_worth_retrying(outcome, retry):
    """A fresh session re-fetches the same page. Only the channel can differ."""
    assert CAPTURE.worth_retrying(outcome) is retry


def test_a_terminal_outcome_stops_the_capture_loop(monkeypatch, tmp_path):
    """Three sessions were spent re-confirming one identity mismatch."""
    from scripts.pettripfinder.brightdata import cross_brand_capture as CBC
    calls = {"n": 0}

    async def fake_attempt(target, attempt, *, run_dir, brand):
        calls["n"] += 1
        return _capture(attempt, CAPTURE.IDENTITY_MISMATCH), None

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(CBC, "run_attempt", fake_attempt)
    monkeypatch.setattr(CBC.asyncio, "sleep", no_sleep)
    records, payload = asyncio.run(CBC.capture_property(
        _target(), run_dir=tmp_path, brand="", max_attempts=3))
    assert calls["n"] == 1, "an identity mismatch must not be retried"
    assert len(records) == 1
    assert payload is None


def test_a_channel_failure_still_uses_its_attempts(monkeypatch, tmp_path):
    from scripts.pettripfinder.brightdata import cross_brand_capture as CBC
    calls = {"n": 0}

    async def fake_attempt(target, attempt, *, run_dir, brand):
        calls["n"] += 1
        return _capture(attempt, CAPTURE.ACCESS_DENIED), None

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(CBC, "run_attempt", fake_attempt)
    monkeypatch.setattr(CBC.asyncio, "sleep", no_sleep)
    records, _ = asyncio.run(CBC.capture_property(
        _target(), run_dir=tmp_path, brand="", max_attempts=3))
    assert calls["n"] == 3, "a refusal may differ on a fresh session"
    assert len(records) == 3

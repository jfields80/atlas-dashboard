"""PTF-WORKERS-004 -- offline tests for the OpenAI web-research provider.

Every test here is offline. The transport is injected (``post_json``), so no
test in this file can reach the network, and the airlock tests assert on the
REFUSAL rather than on a call. The two properties that actually protect
production are covered directly:

  * a model research report can never become official evidence, and
  * a result resting on one can never route READY.
"""

from __future__ import annotations

import os

import pytest

from services.research_workers import research_escalation as ESC
from services.research_workers import routing as R
from services.research_workers import vocabulary as V
from services.research_workers import web_research as WR
from services.research_workers.contracts import (
    Assignment, ProposedField, SourceDocument, WorkerResult, content_hash,
)
from services.research_workers.providers import (
    SPEND_AUTH_ENV, SPEND_AUTH_MAX_USD,
    WEB_RESEARCH_SPEND_AUTH_ENV as WR_ENV,
    WEB_RESEARCH_SPEND_MAX_USD as WR_SPEND_MAX,
    LiveAuthorization, SpendingAirlockError,
    require_web_research_spend_authorization, web_research_spend_authorization_present,
)

STAYBRIDGE = dict(
    listing_key="staybridge suites columbus polaris",
    listing_name="Staybridge Suites Columbus Polaris",
    address="8400 Lyra Dr", city="Columbus", state="OH",
)
ALLOWED = ("ihg.com",)
AUTH = LiveAuthorization(live=True, confirm_spend=True, provider="openai-web-research",
                         model=WR.APPROVED_MODEL, api_key_env="TEST_FAKE_KEY_ENV")
CAPS = WR.WebResearchCaps(max_tool_calls=3, max_output_tokens=2000,
                          assumed_prompt_tokens=1000, assumed_tokens_per_search_call=10000)
PRICING = WR.WebResearchPricing(input_per_1k=0.00125, output_per_1k=0.010,
                                per_tool_call_usd=0.01)


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setenv("TEST_FAKE_KEY_ENV", "sk-not-a-real-key")
    return "TEST_FAKE_KEY_ENV"


def _payload(*, text="Report body.", citations=(), sources=(), searches=1,
             inp=5000, out=800, cached=0):
    output = []
    for _ in range(searches):
        output.append({"type": "web_search_call", "status": "completed",
                       "action": {"type": "search", "sources": list(sources)}})
    output.append({
        "type": "message", "role": "assistant",
        "content": [{"type": "output_text", "text": text,
                     "annotations": [{"type": "url_citation", "url": u, "title": t}
                                     for u, t in citations]}],
    })
    return {"model": WR.APPROVED_MODEL, "output": output,
            "usage": {"input_tokens": inp, "output_tokens": out,
                      "input_tokens_details": {"cached_tokens": cached}}}


def _transport(payload, latency_ms=1234):
    calls = []

    def post_json(url, data, headers, timeout):
        import json
        calls.append({"url": url, "body": json.loads(data.decode()),
                      "headers": headers, "timeout": timeout})
        return payload, latency_ms, "req_test"

    post_json.calls = calls
    return post_json


# --------------------------------------------------------------------------- #
# Escalation gate: web research is never the first move.
# --------------------------------------------------------------------------- #

def _retrieval(**over):
    base = {"listing_key": STAYBRIDGE["listing_key"], "status": "NOT_FOUND",
            "ready_for_extraction": False, "policy_applicable": False,
            "failure_reason": "http_404"}
    base.update(over)
    return base


def test_escalation_is_refused_when_direct_retrieval_succeeded():
    good = _retrieval(status="RETRIEVED", ready_for_extraction=True, policy_applicable=True,
                      failure_reason="")
    permitted, reason = ESC.escalation_permitted(good, listing_key=STAYBRIDGE["listing_key"])
    assert permitted is False
    assert reason == "direct_retrieval_succeeded"
    with pytest.raises(ESC.EscalationBlocked):
        ESC.require_escalation(good, listing_key=STAYBRIDGE["listing_key"])


def test_escalation_is_refused_when_retrieval_was_never_attempted():
    for missing in (None, {}):
        with pytest.raises(ESC.EscalationBlocked):
            ESC.require_escalation(missing, listing_key=STAYBRIDGE["listing_key"])


def test_escalation_is_refused_on_another_hotels_retrieval_artifact():
    """A cross-property escalation would be a silent authorization transfer."""
    other = _retrieval(listing_key="hampton inn dublin")
    with pytest.raises(ESC.EscalationBlocked):
        ESC.require_escalation(other, listing_key=STAYBRIDGE["listing_key"])


@pytest.mark.parametrize("status,failure", [
    ("NOT_FOUND", "http_404"),
    ("ACCESS_BLOCKED", "http_403_blocked"),
    ("RENDER_REQUIRED", "javascript_rendered"),
    ("ENTITY_MISMATCH", "identity_mismatch"),
    ("NETWORK_ERROR", "fetch_timeout"),
])
def test_escalation_is_permitted_on_a_genuine_retrieval_failure(status, failure):
    reason = ESC.require_escalation(_retrieval(status=status, failure_reason=failure),
                                    listing_key=STAYBRIDGE["listing_key"])
    assert reason == "direct_retrieval_failed:%s" % failure


def test_escalation_is_permitted_when_the_page_was_fetched_but_does_not_apply():
    """A directory page or a non-universal brand policy fetches fine and still
    recovers no usable evidence for THIS property."""
    fetched = _retrieval(status="RETRIEVED", ready_for_extraction=False,
                         policy_applicable=False, failure_reason="")
    reason = ESC.require_escalation(fetched, listing_key=STAYBRIDGE["listing_key"])
    assert reason.startswith("retrieved_but_not_applicable")


def test_escalation_blocked_is_an_airlock_error():
    """So the CLI's existing airlock handling reports it and exits non-zero."""
    assert issubclass(ESC.EscalationBlocked, SpendingAirlockError)


# --------------------------------------------------------------------------- #
# Provider ladder: cheapest qualified tier, flagship last.
# --------------------------------------------------------------------------- #

def test_flagship_is_the_final_fallback_not_the_default():
    assert ESC.TIER_FLAGSHIP.model == "gpt-5.4"
    assert ESC.PROVIDER_LADDER[-1] is ESC.TIER_FLAGSHIP
    assert "final research fallback" in ESC.TIER_FLAGSHIP.note


def test_cheaper_tiers_are_not_selectable_until_benchmarked():
    assert ESC.TIER_MINI.model == "gpt-5.4-mini"
    assert ESC.TIER_SEARCH_API.model == "gpt-5-search-api"
    for tier in (ESC.TIER_MINI, ESC.TIER_SEARCH_API):
        assert tier.qualification == ESC.PENDING_BENCHMARK
        assert tier.selectable is False
    assert {t.model for t in ESC.PENDING_BENCHMARK_TIERS} == {"gpt-5.4-mini", "gpt-5-search-api"}


def test_selection_falls_to_the_flagship_while_it_is_the_only_qualified_tier():
    tier, cost = ESC.select_research_tier(
        pricing_by_tier={ESC.TIER_FLAGSHIP.key: PRICING}, caps=CAPS)
    assert tier is ESC.TIER_FLAGSHIP
    assert cost == WR.exact_max_cost_usd(CAPS, PRICING)


def test_a_qualified_cheaper_tier_wins_on_computed_cost():
    """The router picks by real computed cost, not by a hardcoded ranking."""
    cheap = ESC.ProviderTier(key="web_research_mini", model="gpt-5.4-mini",
                             qualification=ESC.QUALIFIED, note="benchmarked")
    cheap_pricing = WR.WebResearchPricing(input_per_1k=0.0001, output_per_1k=0.0008)
    tier, cost = ESC.select_research_tier(
        pricing_by_tier={cheap.key: cheap_pricing, ESC.TIER_FLAGSHIP.key: PRICING},
        caps=CAPS, ladder=(cheap, ESC.TIER_FLAGSHIP))
    assert tier is cheap
    assert cost < WR.exact_max_cost_usd(CAPS, PRICING)


def test_an_unpriced_tier_is_skipped_rather_than_guessed_at():
    with pytest.raises(ESC.EscalationBlocked):
        ESC.select_research_tier(pricing_by_tier={}, caps=CAPS)


def test_an_unqualified_tier_is_never_selected_even_if_it_is_cheapest():
    dirt_cheap = WR.WebResearchPricing(input_per_1k=0.0, output_per_1k=0.0)
    tier, _ = ESC.select_research_tier(
        pricing_by_tier={ESC.TIER_MINI.key: dirt_cheap, ESC.TIER_FLAGSHIP.key: PRICING},
        caps=CAPS)
    assert tier is ESC.TIER_FLAGSHIP          # mini is free but not benchmarked


# --------------------------------------------------------------------------- #
# Naming discipline.
# --------------------------------------------------------------------------- #

def test_module_never_claims_to_be_a_deep_research_provider():
    """The dedicated deep-research models are 404 on this project, so no
    identifier here may imply we are calling that product."""
    # Comments AND docstrings stripped: the module docstring legitimately
    # explains what deep research is and why this is not it, so a raw
    # substring scan would flag the very paragraph that disclaims it.
    # (Defined locally rather than imported -- tests/ is not a package.)
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(WR))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                body.pop(0)
    code = ast.unparse(tree)
    for banned in ("DeepResearch", "deep_research", "DEEP_RESEARCH", "deep-research"):
        assert banned not in code, "identifier %r implies an unavailable product" % banned
    assert WR.APPROVED_MODEL == "gpt-5.4"


# --------------------------------------------------------------------------- #
# Domain allowlist.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw,expected", [
    ("IHG.com", "ihg.com"),
    ("https://www.ihg.com/staybridge/hotels/", "ihg.com"),
    ("www.ihg.com:443", "ihg.com"),
    ("  ihg.com/  ", "ihg.com"),
    ("", ""),
])
def test_normalize_domain(raw, expected):
    assert WR.normalize_domain(raw) == expected


@pytest.mark.parametrize("host,ok", [
    ("ihg.com", True),
    ("www.ihg.com", True),
    ("staybridge.ihg.com", True),
    ("evil-ihg.com", False),          # the bug a bare endswith() would introduce
    ("ihg.com.attacker.net", False),
    ("tripadvisor.com", False),
    ("", False),
])
def test_host_in_allowlist_is_dot_anchored(host, ok):
    assert WR.host_in_allowlist(host, ALLOWED) is ok


def test_official_domains_come_from_the_seed_not_from_brand_guessing():
    got = WR.official_domains_for("https://www.ihg.com/staybridge/hotels/us/en/columbus/",
                                  ["marriott.com", "ihg.com"])
    assert got == ("ihg.com", "marriott.com")     # deduped, seed domain first


# --------------------------------------------------------------------------- #
# Cost ceiling.
# --------------------------------------------------------------------------- #

def test_exact_max_cost_is_the_worst_case_and_rounds_up():
    caps = WR.WebResearchCaps(max_tool_calls=3, max_output_tokens=2000,
                              assumed_prompt_tokens=1000,
                              assumed_tokens_per_search_call=10000)
    assert caps.max_input_tokens == 31000
    # 31.0*0.00125 + 2.0*0.010 + 3*0.01 = 0.03875 + 0.02 + 0.03 = 0.08875 -> 0.09
    assert WR.exact_max_cost_usd(caps, PRICING) == 0.09


def test_cost_ceiling_never_rounds_down_below_the_true_maximum():
    caps = WR.WebResearchCaps(max_tool_calls=1, max_output_tokens=100,
                              assumed_prompt_tokens=0, assumed_tokens_per_search_call=0)
    pricing = WR.WebResearchPricing(input_per_1k=0.0, output_per_1k=0.011,
                                    per_tool_call_usd=0.0)
    raw = 100 / 1000.0 * 0.011                     # 0.0011
    assert WR.exact_max_cost_usd(caps, pricing) >= raw


def test_actual_cost_excludes_cached_input_tokens():
    usage = WR.WebResearchUsage(input_tokens=10000, output_tokens=1000,
                                cached_input_tokens=4000, search_calls=2)
    # billable 6000 in, 1000 out, 2 searches
    expected = 6.0 * 0.00125 + 1.0 * 0.010 + 2 * 0.01
    assert WR.actual_cost_usd(usage, PRICING) == pytest.approx(expected)


def test_caps_reject_values_the_api_itself_rejects():
    with pytest.raises(SpendingAirlockError):
        WR.WebResearchCaps(max_output_tokens=1).validate()      # API floor is 16
    with pytest.raises(SpendingAirlockError):
        WR.WebResearchCaps(max_tool_calls=0).validate()         # API floor is 1
    with pytest.raises(SpendingAirlockError):
        WR.WebResearchCaps(search_context_size="enormous").validate()
    with pytest.raises(SpendingAirlockError):
        WR.WebResearchCaps(reasoning_effort="turbo").validate()


# --------------------------------------------------------------------------- #
# The $5 airlock, and its independence from the $1 benchmark airlock.
# --------------------------------------------------------------------------- #

def test_web_research_spend_gate_requires_the_exact_token(monkeypatch):
    monkeypatch.delenv(WR_ENV, raising=False)
    assert web_research_spend_authorization_present() is False
    with pytest.raises(SpendingAirlockError):
        require_web_research_spend_authorization(0.01)
    monkeypatch.setenv(WR_ENV, "YES_MAX_50_USD")               # near miss
    with pytest.raises(SpendingAirlockError):
        require_web_research_spend_authorization(0.01)
    monkeypatch.setenv(WR_ENV, "YES_MAX_5_USD")
    require_web_research_spend_authorization(0.01)              # no raise


def test_web_research_ceiling_is_five_dollars(monkeypatch):
    monkeypatch.setenv(WR_ENV, "YES_MAX_5_USD")
    require_web_research_spend_authorization(5.00)
    with pytest.raises(SpendingAirlockError):
        require_web_research_spend_authorization(5.01)


def test_the_two_airlocks_are_independent(monkeypatch):
    """Holding one token must grant nothing on the other path, and the $1
    benchmark ceiling must not have moved."""
    assert SPEND_AUTH_MAX_USD == 1.00
    assert WR_SPEND_MAX == 5.00
    assert SPEND_AUTH_ENV != WR_ENV

    monkeypatch.setenv(WR_ENV, "YES_MAX_5_USD")
    monkeypatch.delenv(SPEND_AUTH_ENV, raising=False)
    from services.research_workers.providers import (
        require_spend_authorization, spend_authorization_present,
    )
    assert spend_authorization_present() is False          # web token grants no benchmark
    with pytest.raises(SpendingAirlockError):
        require_spend_authorization(0.50)

    monkeypatch.setenv(SPEND_AUTH_ENV, "YES_MAX_1_USD")
    monkeypatch.delenv(WR_ENV, raising=False)
    assert web_research_spend_authorization_present() is False   # and not the reverse
    with pytest.raises(SpendingAirlockError):
        require_web_research_spend_authorization(0.50)


def test_provider_construction_requires_the_full_live_airlock(fake_key, monkeypatch):
    monkeypatch.setenv(WR_ENV, "YES_MAX_5_USD")
    for bad in (LiveAuthorization(live=False, confirm_spend=True, provider="x",
                                  model=WR.APPROVED_MODEL, api_key_env=fake_key),
                LiveAuthorization(live=True, confirm_spend=False, provider="x",
                                  model=WR.APPROVED_MODEL, api_key_env=fake_key)):
        with pytest.raises(SpendingAirlockError):
            WR.build_web_research_provider(bad, caps=CAPS, pricing=PRICING)


def test_provider_refuses_any_model_but_the_approved_one(fake_key, monkeypatch):
    monkeypatch.setenv(WR_ENV, "YES_MAX_5_USD")
    auth = LiveAuthorization(live=True, confirm_spend=True, provider="openai-web-research",
                             model="gpt-5.5-pro", api_key_env=fake_key)
    with pytest.raises(SpendingAirlockError):
        WR.build_web_research_provider(auth, caps=CAPS, pricing=PRICING)


def test_spend_gate_blocks_construction_when_the_ceiling_is_exceeded(fake_key, monkeypatch):
    monkeypatch.setenv(WR_ENV, "YES_MAX_5_USD")
    auth = LiveAuthorization(live=True, confirm_spend=True, provider="openai-web-research",
                             model=WR.APPROVED_MODEL, api_key_env=fake_key)
    greedy = WR.WebResearchCaps(max_tool_calls=50, max_output_tokens=100000,
                                assumed_tokens_per_search_call=100000)
    with pytest.raises(SpendingAirlockError):
        WR.build_web_research_provider(auth, caps=greedy, pricing=PRICING)


# --------------------------------------------------------------------------- #
# Request shape -- the bounds are verified, not assumed.
# --------------------------------------------------------------------------- #

def test_request_body_carries_every_bound_and_the_allowlist(fake_key):
    provider = WR.WebResearchProvider(AUTH)
    body = provider.build_request_body(
        listing_name=STAYBRIDGE["listing_name"], address=STAYBRIDGE["address"],
        city=STAYBRIDGE["city"], state=STAYBRIDGE["state"],
        allowed_domains=ALLOWED, caps=CAPS)

    assert body["model"] == "gpt-5.4"
    assert body["max_tool_calls"] == 3               # server-enforced search cap
    assert body["max_output_tokens"] == 2000         # server-enforced output cap
    assert body["store"] is False
    tool = body["tools"][0]
    assert tool["type"] == "web_search"
    assert tool["filters"]["allowed_domains"] == ["ihg.com"]
    assert tool["search_context_size"] == "medium"
    assert body["reasoning"]["effort"] == "medium"
    assert "web_search_call.action.sources" in body["include"]


def test_request_body_is_deterministic(fake_key):
    provider = WR.WebResearchProvider(AUTH)
    kw = dict(listing_name="H", address="A", city="C", state="S",
              allowed_domains=ALLOWED, caps=CAPS)
    assert provider.build_request_body(**kw) == provider.build_request_body(**kw)


def test_unrestricted_web_search_is_refused(fake_key):
    """An empty allowlist would mean searching the whole web -- not approved."""
    provider = WR.WebResearchProvider(AUTH)
    with pytest.raises(SpendingAirlockError):
        provider.build_request_body(listing_name="H", address="A", city="C", state="S",
                                    allowed_domains=(), caps=CAPS)


# --------------------------------------------------------------------------- #
# Response parsing + the local allowlist re-check.
# --------------------------------------------------------------------------- #

def test_discovered_urls_come_only_from_tool_citations_never_from_prose(fake_key):
    """A URL the model TYPES is not a citation. Only tool-emitted URLs count."""
    prose = ("See https://www.ihg.com/invented-by-the-model/pet-policy for details, "
             "and also http://ihg.com/another-made-up-page.")
    payload = _payload(text=prose,
                       citations=[("https://www.ihg.com/real-cited-page", "Real")])
    provider = WR.WebResearchProvider(AUTH)
    report = provider.research(listing_key=STAYBRIDGE["listing_key"],
                               listing_name=STAYBRIDGE["listing_name"],
                               address="", city="", state="", allowed_domains=ALLOWED,
                               caps=CAPS, observed_at="2026-07-27",
                               post_json=_transport(payload))
    assert [d.url for d in report.discovered_urls] == ["https://www.ihg.com/real-cited-page"]
    assert "invented-by-the-model" in report.report_text      # prose kept verbatim...
    assert all("invented" not in d.url for d in report.discovered_urls)   # ...but not trusted


def test_off_allowlist_citations_are_rejected_locally(fake_key):
    """The server-side filter is not verifiable from here, so re-check locally."""
    payload = _payload(citations=[
        ("https://www.ihg.com/ok", "ok"),
        ("https://www.tripadvisor.com/not-ok", "third party"),
        ("https://evil-ihg.com/spoof", "lookalike"),
        ("ftp://ihg.com/file", "bad scheme"),
    ])
    provider = WR.WebResearchProvider(AUTH)
    report = provider.research(listing_key="k", listing_name="n", address="", city="",
                               state="", allowed_domains=ALLOWED, caps=CAPS,
                               observed_at="2026-07-27", post_json=_transport(payload))
    assert [d.url for d in report.discovered_urls] == ["https://www.ihg.com/ok"]
    reasons = {r["url"]: r["reason"] for r in report.rejected_urls}
    assert reasons["https://www.tripadvisor.com/not-ok"] == "domain_not_in_allowlist"
    assert reasons["https://evil-ihg.com/spoof"] == "domain_not_in_allowlist"
    assert reasons["ftp://ihg.com/file"] == "non_http_scheme"


def test_search_sources_are_also_harvested(fake_key):
    payload = _payload(citations=[("https://www.ihg.com/cited", "c")],
                       sources=[{"url": "https://www.ihg.com/searched", "title": "s"}])
    provider = WR.WebResearchProvider(AUTH)
    report = provider.research(listing_key="k", listing_name="n", address="", city="",
                               state="", allowed_domains=ALLOWED, caps=CAPS,
                               observed_at="2026-07-27", post_json=_transport(payload))
    origins = {d.url: d.origin for d in report.discovered_urls}
    assert origins["https://www.ihg.com/cited"] == "url_citation"
    assert origins["https://www.ihg.com/searched"] == "search_sources"


def test_usage_uses_the_responses_dialect_not_chat_completions(fake_key):
    """Reading prompt_tokens/completion_tokens here would meter every call as 0."""
    payload = _payload(inp=41234, out=1777, cached=900, searches=2)
    provider = WR.WebResearchProvider(AUTH)
    report = provider.research(listing_key="k", listing_name="n", address="", city="",
                               state="", allowed_domains=ALLOWED, caps=CAPS,
                               observed_at="2026-07-27", post_json=_transport(payload))
    assert (report.usage.input_tokens, report.usage.output_tokens) == (41234, 1777)
    assert report.usage.cached_input_tokens == 900
    assert report.usage.search_calls == 2
    assert report.usage.latency_ms == 1234


def test_transport_failure_is_classified_and_never_raises(fake_key):
    def boom(url, data, headers, timeout):
        raise OSError("connection reset")

    provider = WR.WebResearchProvider(AUTH)
    report = provider.research(listing_key="k", listing_name="n", address="", city="",
                               state="", allowed_domains=ALLOWED, caps=CAPS,
                               observed_at="2026-07-27", post_json=boom)
    assert report.ok is False
    assert report.error.startswith("provider_error:")
    assert report.discovered_urls == ()


def test_the_api_key_never_enters_the_report(fake_key):
    payload = _payload()
    transport = _transport(payload)
    provider = WR.WebResearchProvider(AUTH)
    report = provider.research(listing_key="k", listing_name="n", address="", city="",
                               state="", allowed_domains=ALLOWED, caps=CAPS,
                               observed_at="2026-07-27", post_json=transport)
    blob = repr(report.to_dict())
    assert os.environ["TEST_FAKE_KEY_ENV"] not in blob
    assert "Authorization" not in blob
    # the key IS sent on the wire, and only there
    assert transport.calls[0]["headers"]["Authorization"].startswith("Bearer ")


# --------------------------------------------------------------------------- #
# Provenance: MODEL_RESEARCH_REPORT is never official evidence.
# --------------------------------------------------------------------------- #

def test_model_research_report_is_a_known_but_non_official_source_type():
    assert V.SOURCE_MODEL_RESEARCH_REPORT in V.SOURCE_TYPES
    assert V.SOURCE_MODEL_RESEARCH_REPORT not in V.OFFICIAL_SOURCE_TYPES
    assert V.SOURCE_MODEL_RESEARCH_REPORT in V.NON_PUBLISHABLE_SOURCE_TYPES
    # Asserted as a PROPERTY rather than an exact enumeration. The official set
    # legitimately grows (PTF-WORKERS-005 added OFFICIAL_PROPERTY_INHERITED,
    # -006 added MANUAL_OFFICIAL_ATTESTATION), and a hardcoded set turns every
    # such addition into a test edit that says nothing. What must never change
    # is that model research is not official evidence, and that everything in
    # the official set is a real page someone obtained.
    assert V.SOURCE_MODEL_RESEARCH_REPORT not in V.OFFICIAL_SOURCE_TYPES
    assert V.OFFICIAL_SOURCE_TYPES.isdisjoint(V.NON_PUBLISHABLE_SOURCE_TYPES)
    assert V.SOURCE_OTHER not in V.OFFICIAL_SOURCE_TYPES
    for t in V.OFFICIAL_SOURCE_TYPES:
        assert t.startswith("OFFICIAL_") or t == V.SOURCE_MANUAL_OFFICIAL_ATTESTATION
        assert t in V.SOURCE_TYPES


def _report_doc(text="Staybridge Suites charges a $75 pet fee per stay."):
    report = WR.WebResearchReport(
        listing_key=STAYBRIDGE["listing_key"], listing_name=STAYBRIDGE["listing_name"],
        ok=True, model=WR.APPROVED_MODEL, allowed_domains=ALLOWED,
        report_text=text, observed_at="2026-07-27")
    return WR.research_report_document(report)


def test_research_document_is_valid_but_never_usable_official():
    doc = _report_doc()
    doc.validate()                                   # a well-formed SourceDocument...
    assert doc.source_type == V.SOURCE_MODEL_RESEARCH_REPORT
    assert doc.is_usable_official is False           # ...that the validator will skip
    assert doc.content_hash == content_hash(doc.content_text)


def test_research_document_url_is_a_urn_not_a_hotel_url():
    """Labelling model prose with a hotel's URL is the exact confusion this
    module exists to prevent."""
    doc = _report_doc()
    assert doc.source_url.startswith("urn:atlas:model-research-report:")
    assert "ihg.com" not in doc.source_url
    assert _report_doc().source_url == doc.source_url        # content-addressed


def test_research_document_content_is_capped():
    huge = "x" * (V.SOURCE_CONTENT_CAP_BYTES + 5000)
    doc = _report_doc(huge)
    doc.validate()
    assert len(doc.content_text.encode("utf-8")) <= V.SOURCE_CONTENT_CAP_BYTES


def test_evidence_validator_draws_no_fact_from_a_research_report():
    from services.research_workers.evidence_validator import _usable_official_docs
    doc = _report_doc()
    assignment = Assignment(
        assignment_id="a1", market_slug="columbus", listing_key=STAYBRIDGE["listing_key"],
        listing_name=STAYBRIDGE["listing_name"], address="", official_website="",
        allowed_source_urls=(doc.source_url,), source_documents=(doc,),
        requested_fields=(V.FIELD_PET_FEE,), created_by="test")
    assignment.validate()
    assert _usable_official_docs(assignment) == []


# --------------------------------------------------------------------------- #
# Forced REVIEW routing.
# --------------------------------------------------------------------------- #

def _assignment_with(doc):
    return Assignment(
        assignment_id="a1", market_slug="columbus", listing_key=STAYBRIDGE["listing_key"],
        listing_name=STAYBRIDGE["listing_name"], address="", official_website="",
        allowed_source_urls=(doc.source_url,), source_documents=(doc,),
        requested_fields=(V.FIELD_PETS_ALLOWED,), created_by="test")


def _completed_result(doc, *, source_type):
    return WorkerResult(
        assignment_id="a1", listing_key=STAYBRIDGE["listing_key"],
        status=V.STATUS_COMPLETED, selected_source_url=doc.source_url,
        selected_source_type=source_type, evidence_quotes=("pets are welcome",),
        proposed_facts=(ProposedField(
            field_name=V.FIELD_PETS_ALLOWED, state=V.SUPPORTED, value="true",
            evidence_quote="pets are welcome", source_url=doc.source_url,
            source_type=source_type),),
        unknown_fields=(), contradictions=(), warnings=(),
        provider="openai-web-research", model=WR.APPROVED_MODEL).with_hash()


def test_a_result_selecting_a_research_report_is_forced_to_review():
    doc = _report_doc("Pets are welcome at this property.")
    result = _completed_result(doc, source_type=V.SOURCE_MODEL_RESEARCH_REPORT)
    env = R.route_result(_assignment_with(doc), result, observed_at="2026-07-27")
    assert env.route == R.ROUTE_REVIEW
    assert env.reason_codes == (R.MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE,)
    assert env.publication_eligible is False


def test_a_fact_citing_a_research_report_is_forced_to_review_even_with_an_official_selection():
    """The result points at a real official page, but one fact's evidence is the
    model report. Selection alone is not enough to clear it."""
    doc = _report_doc("Pets are welcome at this property.")
    official = SourceDocument(
        source_url="https://www.ihg.com/staybridge/real-page", source_type=V.SOURCE_OFFICIAL_PROPERTY,
        retrieved_at="2026-07-27", title="Real", content_text="Pets are welcome.",
        content_hash=content_hash("Pets are welcome."), retrieval_status=V.RETRIEVAL_OK)
    assignment = Assignment(
        assignment_id="a1", market_slug="columbus", listing_key=STAYBRIDGE["listing_key"],
        listing_name=STAYBRIDGE["listing_name"], address="", official_website="",
        allowed_source_urls=(doc.source_url, official.source_url),
        source_documents=(doc, official), requested_fields=(V.FIELD_PETS_ALLOWED,),
        created_by="test")
    result = WorkerResult(
        assignment_id="a1", listing_key=STAYBRIDGE["listing_key"], status=V.STATUS_COMPLETED,
        selected_source_url=official.source_url,
        selected_source_type=V.SOURCE_OFFICIAL_PROPERTY,
        evidence_quotes=("Pets are welcome.",),
        proposed_facts=(ProposedField(
            field_name=V.FIELD_PETS_ALLOWED, state=V.SUPPORTED, value="true",
            evidence_quote="Pets are welcome.", source_url=doc.source_url,
            source_type=V.SOURCE_MODEL_RESEARCH_REPORT),),
        unknown_fields=(), contradictions=(), warnings=(),
        provider="openai-web-research", model=WR.APPROVED_MODEL).with_hash()
    env = R.route_result(assignment, result, observed_at="2026-07-27")
    assert env.route == R.ROUTE_REVIEW
    assert R.MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE in env.reason_codes


@pytest.mark.parametrize("fact_source_type", ["", V.SOURCE_OFFICIAL_PROPERTY])
def test_research_provenance_survives_a_misdeclared_fact_source_type(fact_source_type):
    """Audit finding A, applied to model research. This rule was already
    URL-resolved and was NOT bypassable; the test locks that in."""
    doc = _report_doc("Pets are welcome.")
    result = WorkerResult(
        assignment_id="a1", listing_key=STAYBRIDGE["listing_key"],
        status=V.STATUS_COMPLETED, selected_source_url=doc.source_url,
        selected_source_type=V.SOURCE_OFFICIAL_PROPERTY,
        evidence_quotes=("Pets are welcome.",),
        proposed_facts=(ProposedField(
            field_name=V.FIELD_PETS_ALLOWED, state=V.SUPPORTED, value="true",
            evidence_quote="Pets are welcome.", source_url=doc.source_url,
            source_type=fact_source_type),),
        unknown_fields=(), contradictions=(), warnings=(),
        provider="openai-web-research", model=WR.APPROVED_MODEL).with_hash()
    env = R.route_result(_assignment_with(doc), result, observed_at="2026-07-27")
    assert env.route == R.ROUTE_REVIEW
    assert R.MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE in env.reason_codes


def test_research_provenance_can_never_reach_ready():
    """Exhaustive over result status: no status yields READY once model-research
    provenance is present."""
    doc = _report_doc("Pets are welcome.")
    assignment = _assignment_with(doc)
    for status in sorted(V.RESULT_STATUSES):
        result = WorkerResult(
            assignment_id="a1", listing_key=STAYBRIDGE["listing_key"], status=status,
            selected_source_url=doc.source_url,
            selected_source_type=V.SOURCE_MODEL_RESEARCH_REPORT,
            evidence_quotes=(), proposed_facts=(), unknown_fields=(),
            contradictions=(), warnings=(), provider="openai-web-research",
            model=WR.APPROVED_MODEL).with_hash()
        env = R.route_result(assignment, result, observed_at="2026-07-27")
        assert env.route != R.ROUTE_READY, status
        assert env.publication_eligible is False, status


def test_the_new_reason_code_is_a_review_reason_only():
    assert R.MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE in R.REVIEW_REASONS
    assert R.MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE not in R.READY_REASONS
    assert R.READY_REASONS == frozenset({R.PUBLICATION_ELIGIBLE})


def test_ordinary_official_routing_is_completely_unaffected():
    """The backstop must be inert for every result that carries no research
    provenance -- an official, clean result still routes READY."""
    official = SourceDocument(
        source_url="https://www.ihg.com/staybridge/real-page",
        source_type=V.SOURCE_OFFICIAL_PROPERTY, retrieved_at="2026-07-27", title="Real",
        content_text="Pets are welcome.", content_hash=content_hash("Pets are welcome."),
        retrieval_status=V.RETRIEVAL_OK)
    assignment = Assignment(
        assignment_id="a1", market_slug="columbus", listing_key="k", listing_name="n",
        address="", official_website="", allowed_source_urls=(official.source_url,),
        source_documents=(official,), requested_fields=(V.FIELD_PETS_ALLOWED,),
        created_by="test")
    result = WorkerResult(
        assignment_id="a1", listing_key="k", status=V.STATUS_COMPLETED,
        selected_source_url=official.source_url,
        selected_source_type=V.SOURCE_OFFICIAL_PROPERTY,
        evidence_quotes=("Pets are welcome.",),
        proposed_facts=(ProposedField(
            field_name=V.FIELD_PETS_ALLOWED, state=V.SUPPORTED, value="true",
            evidence_quote="Pets are welcome.", source_url=official.source_url,
            source_type=V.SOURCE_OFFICIAL_PROPERTY),),
        unknown_fields=(), contradictions=(), warnings=(), provider="fake",
        model="m").with_hash()
    env = R.route_result(assignment, result, observed_at="2026-07-27")
    assert env.route == R.ROUTE_READY
    assert env.reason_codes == (R.PUBLICATION_ELIGIBLE,)

"""AES-DATA-001 -- AnthropicFactExtractor unit tests (mission sections
9/26/28). No live network and no API key: the missing-key path is exercised
directly, and the retry state machine is tested by overriding the provider's
own call method (not by monkeypatching the SDK network client as the
architecture seam -- the FactExtractor Protocol + StaticFactExtractor remain
the primary seam)."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.category_templates import allowed_fields
from scripts.pettripfinder.importer.extraction_anthropic import (
    AnthropicExtractorError,
    AnthropicFactExtractor,
)

_GOOD = '{"facts": [{"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"}]}'
_BAD = "sorry, I cannot comply"


class _FakeAnthropic(AnthropicFactExtractor):
    """Overrides only the provider's own client + single-call methods so the
    retry logic runs with canned outputs and zero network."""

    def __init__(self, responses, **kw):
        super().__init__(**kw)
        self._responses = list(responses)
        self._i = 0

    def _client(self):
        return object()

    def _call_once(self, client, system, user):
        r = self._responses[self._i]
        self._i += 1
        return r


class TestMissingKey:
    def test_missing_key_fails_clearly(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ext = AnthropicFactExtractor(model="claude-sonnet-5")
        with pytest.raises(AnthropicExtractorError):
            ext.extract("text", "hotels", allowed_fields("hotels"))


class TestRetryStateMachine:
    def test_first_call_good(self):
        ext = _FakeAnthropic([_GOOD], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok and res.retries == 0
        assert res.provider == "anthropic" and res.model == "m"
        assert {f.field_name for f in res.facts} == {"pets_allowed"}

    def test_malformed_then_good_retries_once(self):
        ext = _FakeAnthropic([_BAD, _GOOD], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok and res.retries == 1

    def test_two_malformed_is_unparseable(self):
        ext = _FakeAnthropic([_BAD, _BAD], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok is False
        assert res.error == C.REASON_EXTRACTION_UNPARSEABLE
        assert res.retries == 1
        assert res.provider == "anthropic"

    def test_unknown_fields_dropped_in_provider_output(self):
        payload = ('{"facts": [{"field": "approve", "value": "true", "quote": "x"},'
                   '{"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"}]}')
        ext = _FakeAnthropic([payload], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert {f.field_name for f in res.facts} == {"pets_allowed"}


# --------------------------------------------------------------------------- #
# Sampling parameters (the temperature-deprecation defect).
# --------------------------------------------------------------------------- #

class _CaptureMessages:
    def __init__(self, payload='{"facts": []}'):
        self.kwargs = None
        self._payload = payload

    def create(self, **kw):
        self.kwargs = kw
        block = type("B", (), {"text": self._payload})()
        return type("M", (), {"content": [block]})()


class _CaptureClient:
    def __init__(self):
        self.messages = _CaptureMessages()


class TestSamplingParameters:
    def test_temperature_omitted_for_current_model(self):
        # Sonnet 5 rejects temperature -> the request must not include it.
        ext = AnthropicFactExtractor(model="claude-sonnet-5")
        client = _CaptureClient()
        ext._call_once(client, "sys", "user")
        assert "temperature" not in client.messages.kwargs

    def test_no_unsupported_sampling_parameter_sent(self):
        ext = AnthropicFactExtractor(model="claude-sonnet-5")
        client = _CaptureClient()
        ext._call_once(client, "sys", "user")
        for banned in ("temperature", "top_p", "top_k"):
            assert banned not in client.messages.kwargs
        assert set(client.messages.kwargs) == {"model", "max_tokens", "system", "messages"}

    def test_temperature_included_for_legacy_claude3(self):
        # The legacy family explicitly accepts temperature -> still sent as 0.
        ext = AnthropicFactExtractor(model="claude-3-5-sonnet-20241022")
        client = _CaptureClient()
        ext._call_once(client, "sys", "user")
        assert client.messages.kwargs.get("temperature") == 0

    def test_extract_builds_request_without_temperature(self):
        # End-to-end via a capturing client injected as _client.
        class _Ext(AnthropicFactExtractor):
            captured = None
            def _client(self_inner):
                c = _CaptureClient()
                _Ext.captured = c
                return c
        _Ext(model="claude-sonnet-5").extract("t", "hotels", allowed_fields("hotels"))
        assert "temperature" not in _Ext.captured.messages.kwargs


# --------------------------------------------------------------------------- #
# Provider API error handling -> stable importer failures, no raw traceback.
# --------------------------------------------------------------------------- #

class _RaisingClient:
    def __init__(self, exc):
        self.messages = type("M", (), {"create": lambda _self, **kw: (_ for _ in ()).throw(exc)})()


class TestApiErrorHandling:
    def _errs(self):
        anthropic = pytest.importorskip("anthropic")
        httpx = pytest.importorskip("httpx")
        req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

        def status(cls, code):
            return cls("boom", response=httpx.Response(code, request=req), body=None)

        return {
            "provider_authentication_failed": status(anthropic.AuthenticationError, 401),
            "provider_invalid_request": status(anthropic.BadRequestError, 400),
            "provider_rate_limited": status(anthropic.RateLimitError, 429),
            "provider_connection_failed": anthropic.APIConnectionError(message="c", request=req),
            "provider_timeout": anthropic.APITimeoutError(request=req),
        }

    def test_each_api_error_maps_to_stable_reason(self):
        ext = AnthropicFactExtractor(model="claude-sonnet-5")
        for expected_reason, exc in self._errs().items():
            with pytest.raises(AnthropicExtractorError) as ei:
                ext._call_once(_RaisingClient(exc), "sys", "user")
            assert ei.value.reason == expected_reason
            # The controlled message never contains the API key.
            assert "ANTHROPIC_API_KEY" not in str(ei.value) or expected_reason == \
                "provider_authentication_failed"

    def test_invalid_request_does_not_retry(self):
        # A BadRequest (e.g. the temperature defect) raises immediately; it is
        # not swallowed into the malformed-output retry path.
        anthropic = pytest.importorskip("anthropic")
        httpx = pytest.importorskip("httpx")
        req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        exc = anthropic.BadRequestError(
            "temperature is deprecated for this model",
            response=httpx.Response(400, request=req), body=None)

        calls = {"n": 0}

        class _Counting(AnthropicFactExtractor):
            def _client(self_inner):
                return object()
            def _call_once(self_inner, client, system, user):
                calls["n"] += 1
                raise self_inner._map_api_error(exc)

        with pytest.raises(AnthropicExtractorError) as ei:
            _Counting(model="claude-sonnet-5").extract("t", "hotels", allowed_fields("hotels"))
        assert ei.value.reason == "provider_invalid_request"
        assert calls["n"] == 1          # no retry on a bad request

    def test_non_anthropic_exception_propagates(self):
        ext = AnthropicFactExtractor(model="claude-sonnet-5")
        with pytest.raises(ValueError):
            ext._call_once(_RaisingClient(ValueError("other")), "s", "u")

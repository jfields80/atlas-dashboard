"""AES-DATA-001 importer -- live Anthropic fact extractor (mission sections
8/9/26).

Lazy-imports the ``anthropic`` SDK inside the call so this module imports
(and the whole pytest suite runs) with the SDK absent and no
``ANTHROPIC_API_KEY``. One bounded call per snapshot, strict JSON, one retry
on malformed output, no tools, no streaming, no chain-of-thought retained.
The API key is read from the environment and never written to logs, JSON,
reports, or snapshots.

AES-WORK-001C: real provider usage (``message.usage.input_tokens`` /
``output_tokens``) is captured via a private ``_last_usage`` side channel
set by ``_call_once`` after each real SDK call, deliberately WITHOUT
changing ``_call_once``'s ``-> str`` return type (existing tests override
``_call_once`` to return canned strings; changing its signature would break
that seam). ``extract`` reads ``_last_usage`` immediately after each call
and accumulates it into the returned ``ExtractionResult`` -- across BOTH
calls when a malformed-output retry happens, never only the final one.
Usage extraction failure (missing/malformed ``.usage``) never fails
extraction: it degrades to ``(0, 0)``, exactly like a static extractor.

Sampling: ``temperature`` is OMITTED by default. Newer models (Sonnet 5 and
the current 4.x/5.x line) reject ``temperature`` ("deprecated for this
model"); only the legacy ``claude-3*`` family is explicitly known to accept
it, so the request includes ``temperature=0`` for those models alone and no
sampling parameter otherwise. No other sampling parameter (top_p/top_k) is
ever sent -- downstream evidence-span validation, not decoding settings, is
what makes the pipeline safe.

Provider/transport errors (auth, invalid request, rate limit, connection,
timeout) are converted to a stable, importer-specific
:class:`AnthropicExtractorError` carrying a ``reason`` slug -- never an
uncontrolled SDK traceback, and never containing the API key.
"""

from __future__ import annotations

import os
from dataclasses import replace
from typing import FrozenSet, Optional, Tuple

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.category_templates import allowed_field_order
from scripts.pettripfinder.importer.extraction import (
    build_extraction_prompt,
    parse_extraction_payload,
)
from scripts.pettripfinder.importer.models import ExtractionResult

# Provider-boundary failure reason slugs (raised via AnthropicExtractorError;
# these are transport/config failures, distinct from the pipeline's
# content-level slugs in constants.py which flow into candidate reasons).
REASON_PROVIDER_MISSING_SDK = "provider_sdk_missing"
REASON_PROVIDER_MISSING_API_KEY = "provider_missing_api_key"
REASON_PROVIDER_AUTH_FAILED = "provider_authentication_failed"
REASON_PROVIDER_INVALID_REQUEST = "provider_invalid_request"
REASON_PROVIDER_RATE_LIMITED = "provider_rate_limited"
REASON_PROVIDER_CONNECTION_FAILED = "provider_connection_failed"
REASON_PROVIDER_TIMEOUT = "provider_timeout"
REASON_PROVIDER_ERROR = "provider_error"

# Only the legacy claude-3* family is explicitly known to accept temperature.
_TEMPERATURE_SUPPORTED_PREFIXES = ("claude-3",)


class AnthropicExtractorError(RuntimeError):
    """A clean, importer-specific provider failure. Carries a stable
    ``reason`` slug and never contains secret material."""

    def __init__(self, message: str, reason: str = ""):
        super().__init__(message)
        self.reason = reason


class AnthropicFactExtractor:
    """Live provider. Constructing it is cheap and does not touch the
    network or require the key; ``extract`` performs the single call."""

    def __init__(
        self,
        model: str = C.DEFAULT_ANTHROPIC_MODEL,
        api_key_env: str = "ANTHROPIC_API_KEY",
        max_tokens: int = C.LLM_MAX_TOKENS,
        timeout_seconds: int = C.READ_TIMEOUT_SECONDS,
    ):
        self._model = model
        self._api_key_env = api_key_env
        self._max_tokens = max_tokens
        self._timeout = timeout_seconds
        # Side channel: the (input_tokens, output_tokens) of the most recent
        # real ``_call_once``, or None when no real call has completed yet
        # (a subclass overriding ``_call_once`` for tests never sets this --
        # ``extract`` treats None as (0, 0), never as an error).
        self._last_usage: Optional[Tuple[int, int]] = None

    def _client(self):
        try:
            import anthropic  # lazy: not needed for the deterministic suite
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise AnthropicExtractorError(
                "anthropic SDK not installed; run pip install -r requirements.txt",
                reason=REASON_PROVIDER_MISSING_SDK,
            ) from exc
        api_key = os.environ.get(self._api_key_env)
        if not api_key:
            raise AnthropicExtractorError(
                "%s is not set; the live extractor requires an API key"
                % self._api_key_env,
                reason=REASON_PROVIDER_MISSING_API_KEY,
            )
        return anthropic.Anthropic(api_key=api_key, timeout=self._timeout)

    def _supports_temperature(self) -> bool:
        model = (self._model or "").lower()
        return any(model.startswith(p) for p in _TEMPERATURE_SUPPORTED_PREFIXES)

    def _request_kwargs(self, system: str, user: str) -> dict:
        kwargs = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        # Include temperature ONLY for the legacy family that accepts it;
        # omit entirely for every other (current/unknown) model. No other
        # sampling parameter is ever sent.
        if self._supports_temperature():
            kwargs["temperature"] = 0
        return kwargs

    def _map_api_error(self, exc: Exception) -> Optional[AnthropicExtractorError]:
        """Convert an anthropic SDK error into a clean importer error, or
        ``None`` if ``exc`` is not an anthropic error (caller re-raises)."""
        try:
            import anthropic
        except ImportError:  # pragma: no cover
            return None
        # Order matters: check the most specific subclasses first.
        if isinstance(exc, anthropic.APITimeoutError):
            return AnthropicExtractorError(
                "anthropic request timed out", reason=REASON_PROVIDER_TIMEOUT)
        if isinstance(exc, anthropic.APIConnectionError):
            return AnthropicExtractorError(
                "anthropic connection failed", reason=REASON_PROVIDER_CONNECTION_FAILED)
        if isinstance(exc, (anthropic.AuthenticationError,
                            anthropic.PermissionDeniedError)):
            return AnthropicExtractorError(
                "anthropic authentication failed; check %s" % self._api_key_env,
                reason=REASON_PROVIDER_AUTH_FAILED)
        if isinstance(exc, anthropic.RateLimitError):
            return AnthropicExtractorError(
                "anthropic rate limit reached", reason=REASON_PROVIDER_RATE_LIMITED)
        if isinstance(exc, anthropic.BadRequestError):
            return AnthropicExtractorError(
                "anthropic rejected the request: %s" % _safe_message(exc),
                reason=REASON_PROVIDER_INVALID_REQUEST)
        if isinstance(exc, anthropic.APIError):
            return AnthropicExtractorError(
                "anthropic API error", reason=REASON_PROVIDER_ERROR)
        return None

    def _call_once(self, client, system: str, user: str) -> str:
        self._last_usage = None
        try:
            message = client.messages.create(**self._request_kwargs(system, user))
        except Exception as exc:  # noqa: BLE001 - mapped to a controlled error
            mapped = self._map_api_error(exc)
            if mapped is not None:
                raise mapped from None      # suppress the raw SDK traceback
            raise
        self._last_usage = _extract_usage(message)
        parts = []
        for block in getattr(message, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts).strip()

    def extract(
        self, normalized_text: str, category: str, allowed_fields: FrozenSet[str],
    ) -> ExtractionResult:
        system, user = build_extraction_prompt(
            normalized_text, category, allowed_field_order(category))
        client = self._client()

        # A provider/transport error (auth/invalid-request/rate/connection/
        # timeout) raises a clean AnthropicExtractorError and never reaches
        # the malformed-output retry (a bad request will not succeed on
        # retry) -- that path never returns an ExtractionResult at all, so
        # its usage cannot be attached here; see the module docstring and
        # the WORK-001C final report for this disclosed limitation.
        raw = self._call_once(client, system, user)
        in1, out1 = self._last_usage or (0, 0)
        result = parse_extraction_payload(
            _extract_json_object(raw), allowed_fields, "anthropic", self._model)
        if result.ok:
            return replace(
                result, input_tokens=in1, output_tokens=out1, provider_request_count=1)

        raw = self._call_once(client, system, user)
        in2, out2 = self._last_usage or (0, 0)
        # Real usage from BOTH calls is kept, even though only the retry's
        # facts (or neither, on a second malformed output) are used -- the
        # first call was a real, billed provider request too.
        total_in, total_out = in1 + in2, out1 + out2
        result = parse_extraction_payload(
            _extract_json_object(raw), allowed_fields, "anthropic", self._model)
        if result.ok:
            return ExtractionResult(
                facts=result.facts, provider="anthropic", model=self._model,
                prompt_version=C.PROMPT_VERSION, ok=True, retries=1,
                input_tokens=total_in, output_tokens=total_out, provider_request_count=2)
        # Second malformed output -> honest unparseable result (candidate REVIEW).
        return ExtractionResult(
            provider="anthropic", model=self._model,
            prompt_version=C.PROMPT_VERSION, ok=False, retries=1,
            error=C.REASON_EXTRACTION_UNPARSEABLE,
            input_tokens=total_in, output_tokens=total_out, provider_request_count=2)


def _extract_usage(message) -> Tuple[int, int]:
    """Best-effort ``(input_tokens, output_tokens)`` from one real SDK
    response. Never raises and never infers from text length -- any
    missing/malformed ``.usage`` degrades to ``(0, 0)``, exactly like a
    static extractor (AES-WORK-001C Task 7: usage capture failure never
    fails extraction)."""
    try:
        usage = getattr(message, "usage", None)
        if usage is None:
            return (0, 0)
        return (int(getattr(usage, "input_tokens", 0) or 0),
                int(getattr(usage, "output_tokens", 0) or 0))
    except Exception:
        return (0, 0)


def _safe_message(exc: Exception) -> str:
    """A short, secret-free string form of an SDK error message."""
    msg = str(getattr(exc, "message", "") or exc) or exc.__class__.__name__
    return msg[:200]


def _extract_json_object(raw: str) -> str:
    """Return the first top-level ``{...}`` JSON object substring, tolerating
    accidental prose or code fences around it. The strict parser still
    validates the result; this only trims obvious wrappers."""
    if not raw:
        return ""
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        return raw[start:end + 1]
    return raw

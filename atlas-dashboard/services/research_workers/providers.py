"""ATLAS-WORKERS-001 -- provider interface + deterministic fake + spending
airlock (Stage 5).

The worker is provider-neutral. The default is the deterministic ``FakeProvider``
(no network, no key, no cost) used by every test and the offline benchmark. A
live OpenAI-compatible adapter exists but CANNOT be constructed -- let alone make
a network call -- unless the spending airlock is fully satisfied: --live,
--confirm-spend, an explicit provider and model, and a matching API credential
present in the environment. API keys are never printed and the model is never
silently switched.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import List, Optional, Protocol, Tuple

from services.research_workers import vocabulary as V
from services.research_workers.contracts import Assignment, SourceDocument
from services.research_workers.proposal import ModelProposal, ProviderErrorDetail, RawFactClaim


class ResearchProvider(Protocol):
    name: str
    def propose(self, assignment: Assignment, *, model: str, output_token_cap: int,
                timeout_s: float, max_retries: int) -> ModelProposal: ...


# --------------------------------------------------------------------------- #
# Spending airlock.
# --------------------------------------------------------------------------- #

class SpendingAirlockError(RuntimeError):
    """Raised when a live/paid path is requested without full authorization."""


@dataclass(frozen=True)
class LiveAuthorization:
    live: bool = False
    confirm_spend: bool = False
    provider: str = ""
    model: str = ""
    api_key_env: str = "OPENAI_API_KEY"


def require_live_authorization(auth: LiveAuthorization) -> str:
    """Enforce ALL airlock conditions before any network client can exist.
    Returns the resolved credential env-var NAME (never the value). Never logs
    or returns the key itself."""
    if not auth.live:
        raise SpendingAirlockError("live mode requires --live")
    if not auth.confirm_spend:
        raise SpendingAirlockError("live mode requires --confirm-spend")
    if not auth.provider:
        raise SpendingAirlockError("live mode requires an explicit --provider")
    if not auth.model:
        raise SpendingAirlockError("live mode requires an explicit --model")
    if not os.environ.get(auth.api_key_env):
        raise SpendingAirlockError(
            "live mode requires the API credential in environment variable %s "
            "(value never read into logs)" % auth.api_key_env)
    return auth.api_key_env


# ATLAS-WORKERS-002: an additional, explicit paid-benchmark authorization gate.
# A live model bakeoff also requires the operator to set an exact environment
# token AND a total estimated cost within a hard $1.00 ceiling. The token value
# is compared but never printed, persisted, or hashed.
SPEND_AUTH_ENV = "ATLAS_BENCHMARK_SPEND_AUTHORIZATION"
SPEND_AUTH_TOKEN = "YES_MAX_1_USD"
SPEND_AUTH_MAX_USD = 1.00


def spend_authorization_present() -> bool:
    """True iff the exact spend-authorization token is set. Boolean only."""
    return os.environ.get(SPEND_AUTH_ENV) == SPEND_AUTH_TOKEN


def require_spend_authorization(max_estimated_cost: float) -> None:
    """Gate the paid benchmark: the exact env token must be present and the
    configured maximum estimated cost must not exceed the $1.00 ceiling. Raises
    before any network client is built."""
    if not spend_authorization_present():
        raise SpendingAirlockError(
            "paid benchmark requires environment %s=%s (value never logged)"
            % (SPEND_AUTH_ENV, SPEND_AUTH_TOKEN))
    if max_estimated_cost is None or max_estimated_cost > SPEND_AUTH_MAX_USD + 1e-9:
        raise SpendingAirlockError(
            "configured max estimated cost %s exceeds the $%.2f ceiling"
            % (max_estimated_cost, SPEND_AUTH_MAX_USD))


# --------------------------------------------------------------------------- #
# Deterministic fake provider (rule-based extractor over supplied text).
# --------------------------------------------------------------------------- #

_NEG_PETS = re.compile(
    r"no pets|pets are not (?:allowed|permitted|accepted)|do(?:es)? not (?:allow|permit|accept) pets"
    r"|cannot accommodate pets|not (?:a )?pet[- ]friendly", re.I)
_POS_PETS = re.compile(
    r"pets?\s+(?:(?:is|are)\s+)?(?:welcome|allowed|permitted|accepted)|pet[- ]friendly"
    r"|we welcome (?:dogs|cats|pets)"
    # A species-specific acceptance also proves pets are allowed (dogs/cats are
    # pets); this is directional -- it never runs the other way.
    r"|(?:dogs?|cats?)\s+(?:and\s+(?:dogs?|cats?)\s+)?(?:(?:is|are)\s+)?(?:welcome|accepted|allowed|permitted)", re.I)
_DOGS = re.compile(r"dogs?[^.\n]{0,40}(?:welcome|accepted|allowed|permitted)|dogs and cats", re.I)
_CATS = re.compile(r"cats?[^.\n]{0,40}(?:welcome|accepted|allowed|permitted)|dogs and cats", re.I)
_FEE = re.compile(r"(\$\s?\d[\d,\.]*)[^.\n]{0,60}?(?:fee|charge)|(?:fee|charge)[^.\n]{0,40}?(\$\s?\d[\d,\.]*)", re.I)
_DEPOSIT = re.compile(r"(\$\s?\d[\d,\.]*)[^.\n]{0,40}?deposit|deposit[^.\n]{0,40}?(\$\s?\d[\d,\.]*)", re.I)
_MAXPETS = re.compile(r"(?:maximum|max\.?|up to|limit of|no more than|a maximum of)\s+(?:of\s+)?(\d+)\s+pets?"
                      r"|(\d+)\s+pets?\s+(?:maximum|per room|allowed|permitted)", re.I)
_WEIGHT = re.compile(r"(\d+)\s?(lbs?|pounds?|kg|kilograms?)", re.I)
_BREED = re.compile(r"breed[^.\n]{0,60}(?:restrict|not permitted|not allowed|prohibited)"
                    r"|(?:aggressive|certain|restricted) breeds", re.I)
_UNATTENDED = re.compile(r"[^.\n]*unattended[^.\n]*|pets? (?:may not|must not) be left (?:alone|unattended)[^.\n]*", re.I)
_SERVICE = re.compile(r"[^.\n]*service animals?[^.\n]*", re.I)

_FEE_BASIS = (
    # Specific "per room per X" first, so a broader value never matches instead.
    (V.FEE_BASIS_PER_ROOM_PER_DAY, re.compile(r"per room[ ,]+per day|per room/day|room per day", re.I)),
    (V.FEE_BASIS_PER_ROOM_PER_NIGHT, re.compile(r"per room[ ,]+per night|per room/night|room per night", re.I)),
    (V.FEE_BASIS_PER_NIGHT, re.compile(r"per night|nightly|/night|a night", re.I)),
    (V.FEE_BASIS_PER_STAY, re.compile(r"per stay|each stay|/stay|a stay", re.I)),
    (V.FEE_BASIS_PER_ROOM, re.compile(r"per room", re.I)),
)


def _sentence_around(text: str, start: int, end: int, cap: int = V.EVIDENCE_QUOTE_CAP) -> str:
    """A verbatim substring of ``text`` covering the sentence around [start,end)."""
    left = max(text.rfind(". ", 0, start), text.rfind("\n", 0, start))
    left = left + 1 if left != -1 else 0
    right_dot = text.find(". ", end)
    right_nl = text.find("\n", end)
    candidates = [r for r in (right_dot, right_nl) if r != -1]
    right = (min(candidates) + 1) if candidates else len(text)
    snippet = text[left:right].strip()
    if len(snippet) > cap:
        # keep it verbatim: clamp to a window that still contains the match
        s2 = max(left, start - 40)
        snippet = text[s2:s2 + cap].strip()
    return snippet


def _first(regex, text: str) -> Optional[Tuple[str, int, int]]:
    m = regex.search(text)
    if not m:
        return None
    return (m.group(0), m.start(), m.end())


def _fake_claims_for_doc(doc: SourceDocument, requested: frozenset) -> List[RawFactClaim]:
    text = doc.content_text
    url = doc.source_url
    out: List[RawFactClaim] = []

    def add(field, value, span):
        if requested and field not in requested:
            return
        quote = _sentence_around(text, span[0], span[1])
        out.append(RawFactClaim(field_name=field, value=value, evidence_quote=quote, source_url=url))

    # pets_allowed (negatives win over positives).
    neg = _NEG_PETS.search(text)
    if neg:
        add(V.FIELD_PETS_ALLOWED, "false", (neg.start(), neg.end()))
    else:
        pos = _POS_PETS.search(text)
        if pos:
            add(V.FIELD_PETS_ALLOWED, "true", (pos.start(), pos.end()))
    # dogs / cats -- only when the species word actually appears (never inferred
    # from a generic pets-welcome statement).
    if not neg:
        d = _DOGS.search(text)
        if d:
            add(V.FIELD_DOGS_ACCEPTED, "true", (d.start(), d.end()))
        c = _CATS.search(text)
        if c:
            add(V.FIELD_CATS_ACCEPTED, "true", (c.start(), c.end()))
    # pet fee + currency + basis. The basis is read ONLY from the sentence that
    # states the pet fee -- never from unrelated dollar/time noise elsewhere on
    # the page (e.g. a room rate "per night") -- so realistic surrounding text
    # cannot corrupt the fee basis.
    fee = _FEE.search(text)
    if fee:
        amount = (fee.group(1) or fee.group(2) or "").replace(" ", "")
        add(V.FIELD_PET_FEE, amount, (fee.start(), fee.end()))
        if "$" in amount:
            add(V.FIELD_FEE_CURRENCY, "USD", (fee.start(), fee.end()))
        fee_sentence = _sentence_around(text, fee.start(), fee.end())
        for basis, rx in _FEE_BASIS:
            if rx.search(fee_sentence):
                add(V.FIELD_FEE_BASIS, basis, (fee.start(), fee.end()))
                break
    # refundable deposit (distinct sentence from the fee)
    dep = _DEPOSIT.search(text)
    if dep:
        amount = (dep.group(1) or dep.group(2) or "").replace(" ", "")
        add(V.FIELD_REFUNDABLE_DEPOSIT, amount, (dep.start(), dep.end()))
    # maximum pets
    mp = _MAXPETS.search(text)
    if mp:
        num = mp.group(1) or mp.group(2)
        add(V.FIELD_MAXIMUM_PETS, num, (mp.start(), mp.end()))
    # weight limit
    wl = _WEIGHT.search(text)
    if wl:
        add(V.FIELD_WEIGHT_LIMIT, "%s %s" % (wl.group(1), wl.group(2)), (wl.start(), wl.end()))
    # free-text policy notes (value == verbatim stated wording). The regexes are
    # already bounded to a single sentence via [^.\n]*, so use the matched span
    # verbatim rather than expanding to neighbouring sentences.
    for field, rx in ((V.FIELD_BREED_RESTRICTIONS, _BREED),
                      (V.FIELD_UNATTENDED_PET_RULE, _UNATTENDED),
                      (V.FIELD_SERVICE_ANIMAL_NOTE, _SERVICE)):
        if requested and field not in requested:
            continue
        hit = _first(rx, text)
        if hit:
            quote = hit[0].strip()[:V.EVIDENCE_QUOTE_CAP]
            out.append(RawFactClaim(field_name=field, value=quote, evidence_quote=quote, source_url=url))
    return out


class FakeProvider:
    """Deterministic, offline extractor. Proposes facts ONLY from the exact
    supplied official text (verbatim quotes), never invents a value, and never
    touches the network. Its claims are still untrusted -- the validator checks
    them exactly as it would a real model's."""

    name = "fake"

    def propose(self, assignment: Assignment, *, model: str = "fake-extractor-v1",
                output_token_cap: int = V.DEFAULT_OUTPUT_TOKEN_CAP,
                timeout_s: float = 0.0, max_retries: int = 0) -> ModelProposal:
        requested = frozenset(assignment.requested_fields) or frozenset(V.POLICY_FIELDS)
        official = [d for d in assignment.source_documents if d.is_usable_official]
        claims: List[RawFactClaim] = []
        for doc in sorted(official, key=lambda d: (-V.SOURCE_TYPE_RANK.get(d.source_type, 0), d.source_url)):
            claims.extend(_fake_claims_for_doc(doc, requested))
        return ModelProposal(
            claims=tuple(claims), ok=True, structured_output_valid=True,
            provider=self.name, model=model, input_tokens=0, output_tokens=0,
            cached_input_tokens=0, latency_ms=0, attempt_count=1)


# --------------------------------------------------------------------------- #
# Provider-error sanitization + classification (ATLAS-WORKERS-002 repair).
# --------------------------------------------------------------------------- #

# Applied to EVERY provider error message before it can enter a proposal,
# report, or log: bearer tokens, API-key-shaped strings, and Authorization
# header dumps are redacted, and the message is length-capped. The request
# body is never used as an error source, so a prompt cannot leak either.
PROVIDER_ERROR_MESSAGE_CAP = 300
# The scheme word is absorbed by the header pattern so "Authorization: Bearer
# <token>" loses the token, not just the word "Bearer". Bearer redaction runs
# FIRST as a second line of defence for bare "Bearer <token>" fragments.
_REDACT_BEARER = re.compile(r"\bbearer\s+[^\s\"']+", re.I)
_REDACT_AUTH_HEADER = re.compile(r"(authorization\b\s*[:=]\s*)(bearer\s+)?[^\s\"']+", re.I)
_REDACT_KEY = re.compile(r"\bsk-[A-Za-z0-9_\-]{4,}")


def sanitize_error_message(message: str, cap: int = PROVIDER_ERROR_MESSAGE_CAP) -> str:
    msg = _REDACT_BEARER.sub("bearer [REDACTED]", message or "")
    msg = _REDACT_AUTH_HEADER.sub(r"\1[REDACTED]", msg)
    msg = _REDACT_KEY.sub("[REDACTED_KEY]", msg)
    return msg[:cap]


# HTTP statuses where a retry may genuinely succeed. Everything else (400/401/
# 403/404/422 ...) is deterministic: re-sending the identical request can only
# repeat the failure and burn budget.
TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


def classify_provider_error(exc: BaseException, attempt_count: int) -> ProviderErrorDetail:
    """Convert a transport/HTTP exception into a sanitized ProviderErrorDetail.
    Reads ONLY the response side (status, provider error JSON, headers) -- never
    the request, so no credential or request body can enter the detail."""
    import json as _json
    import urllib.error as _ue
    if isinstance(exc, _ue.HTTPError):
        status = int(exc.code)
        rid = ""
        try:
            rid = exc.headers.get("x-request-id") or exc.headers.get("x-goog-request-id") or ""
        except Exception:
            rid = ""
        error_type = error_code = ""
        message = sanitize_error_message(str(exc.reason or ""))
        try:
            err = _json.loads(exc.read().decode("utf-8", "replace")).get("error") or {}
            error_type = str(err.get("type") or "")
            error_code = str(err.get("code") or "")
            if err.get("message"):
                message = sanitize_error_message(str(err["message"]))
        except Exception:
            pass                        # unreadable error body: keep the status-line message
        return ProviderErrorDetail(
            http_status=status, error_type=error_type, error_code=error_code,
            message=message, request_id=rid, transient=status in TRANSIENT_HTTP_STATUSES,
            attempt_count=attempt_count)
    # No HTTP response at all (DNS/timeout/connection reset): a bounded retry
    # is worthwhile.
    return ProviderErrorDetail(
        http_status=0, error_type=type(exc).__name__, error_code="",
        message=sanitize_error_message(str(exc)), request_id="", transient=True,
        attempt_count=attempt_count)


# --------------------------------------------------------------------------- #
# Live OpenAI-compatible adapter (constructed ONLY behind the airlock).
# --------------------------------------------------------------------------- #

_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
}
# Which providers speak the OpenAI chat-completions dialect.
_OPENAI_COMPATIBLE = {"openai", "deepseek", "openai-compatible"}


@dataclass(frozen=True)
class ChatRequestOptions:
    """Per-model chat-completions request shape (ATLAS-WORKERS-002 repair).

    The GPT-5 family rejects the legacy ``max_tokens`` parameter (it requires
    ``max_completion_tokens``) and rejects any non-default ``temperature`` --
    exactly the two parameters that made every gpt-5.4-nano benchmark call
    fail with HTTP 400 invalid_request_error before a model response existed.
    The verified direct canary sent neither legacy parameter. Defaults keep
    the legacy dialect for endpoints that still speak it (e.g. DeepSeek)."""

    token_limit_param: str = "max_tokens"   # "max_completion_tokens" for the GPT-5 family
    send_temperature: bool = True           # False where only the API default is accepted
    temperature: float = 0.0


DEFAULT_CHAT_REQUEST_OPTIONS = ChatRequestOptions()


def normalize_usage(style: str, usage: dict) -> tuple:
    """Return (input_tokens, output_tokens, cached_input_tokens) from any
    provider's usage block, so every adapter yields the same internal shape."""
    usage = usage or {}
    if style == "gemini":
        return (int(usage.get("promptTokenCount", 0)),
                int(usage.get("candidatesTokenCount", 0)),
                int(usage.get("cachedContentTokenCount", 0)))
    # openai + deepseek chat-completions usage. prompt_tokens_details may be
    # absent OR explicitly null (as in a minimal canary response) -- both mean
    # zero cached tokens, never a parse failure.
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    if cached is None:
        cached = usage.get("prompt_cache_hit_tokens", 0)   # deepseek naming
    return (int(usage.get("prompt_tokens", 0)),
            int(usage.get("completion_tokens", 0)), int(cached or 0))


def _post_json(url: str, data: bytes, headers: dict, timeout: float):
    """One HTTP POST returning (payload_dict, latency_ms, request_id). stdlib
    only. Raises on transport/HTTP error (bounded retry handled by the caller)."""
    import json as _json
    import urllib.request as _rq
    req = _rq.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    with _rq.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        rid = ""
        try:
            rid = resp.headers.get("x-request-id") or resp.headers.get("x-goog-request-id") or ""
        except Exception:
            rid = ""
    return _json.loads(raw), int((time.time() - t0) * 1000), rid


class _LiveProviderBase:
    """Shared airlock + bounded-retry machinery for every live adapter."""

    def __init__(self, auth: LiveAuthorization, name: str, base_url: str):
        self._api_key_env = require_live_authorization(auth)   # raises unless fully authorized
        self._auth = auth
        self.name = name
        self._base_url = base_url.rstrip("/")

    def _guard_model(self, model: str) -> None:
        if model != self._auth.model:
            raise SpendingAirlockError(
                "model %r was not the authorized model %r" % (model, self._auth.model))

    def _run(self, assignment: Assignment, model: str, url: str, body: dict, headers: dict,
             timeout_s: float, max_retries: int, extract_text, usage_style: str) -> ModelProposal:
        import json as _json
        from services.research_workers.prompt import parse_worker_payload
        data = _json.dumps(body).encode("utf-8")
        detail: Optional[ProviderErrorDetail] = None
        attempts = 0
        for _attempt in range(max(1, max_retries + 1)):
            attempts += 1
            try:
                payload, latency_ms, _rid = _post_json(url, data, headers, timeout_s)
            except Exception as exc:                    # noqa: BLE001 -- classified, never swallowed
                detail = classify_provider_error(exc, attempts)
                if not detail.transient:
                    break               # deterministic failure: never re-send the same request
                continue
            try:
                text = extract_text(payload)
                inp, out, cached = normalize_usage(usage_style, payload.get("usage")
                                                   or payload.get("usageMetadata"))
            except Exception as exc:                    # noqa: BLE001 -- HTTP 200, unusable shape
                detail = ProviderErrorDetail(
                    http_status=200, error_type="malformed_response",
                    error_code=type(exc).__name__,
                    message=sanitize_error_message(str(exc)), request_id=_rid,
                    transient=False, attempt_count=attempts)
                break
            claims, ok = parse_worker_payload(text, assignment)
            return ModelProposal(
                claims=tuple(claims), ok=ok, structured_output_valid=ok,
                error="" if ok else "unparseable_output", provider=self.name, model=model,
                input_tokens=inp, output_tokens=out, cached_input_tokens=cached,
                latency_ms=latency_ms, attempt_count=attempts)
        # A provider failure NEVER triggers automatic fallback -- it is reported,
        # with the sanitized detail preserved for diagnosis (status, error type/
        # code, message, request id, transient flag, attempts).
        slug = detail.error_code or detail.error_type or ("http_%d" % detail.http_status)
        return ModelProposal(ok=False, error="provider_error:%s" % slug,
                             structured_output_valid=False, provider=self.name, model=model,
                             attempt_count=attempts, provider_error=detail)


class OpenAICompatibleProvider(_LiveProviderBase):
    """OpenAI chat-completions adapter, also serving DeepSeek's OpenAI-compatible
    endpoint (different base URL, credential env, and cached-token field).
    Constructed only behind the airlock; stdlib urllib only."""

    def __init__(self, auth: LiveAuthorization, *, name: str = "openai",
                 base_url: Optional[str] = None, usage_style: Optional[str] = None,
                 request_options: Optional[ChatRequestOptions] = None):
        super().__init__(auth, name, base_url or _DEFAULT_BASE_URLS.get(name, _DEFAULT_BASE_URLS["openai"]))
        self._usage_style = usage_style or name
        self._request_options = request_options or DEFAULT_CHAT_REQUEST_OPTIONS

    def propose(self, assignment: Assignment, *, model: str, output_token_cap: int,
                timeout_s: float, max_retries: int) -> ModelProposal:
        self._guard_model(model)
        from services.research_workers.prompt import build_worker_prompt
        system, user = build_worker_prompt(assignment)
        key = os.environ[self._api_key_env]                    # read at call time only
        opts = self._request_options
        # response_format json_object (no json_schema/strict, so no schema-
        # keyword incompatibility is possible); json_object mode requires the
        # word "JSON" in the messages, which the system prompt states.
        body = {"model": model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                opts.token_limit_param: int(output_token_cap),
                "response_format": {"type": "json_object"}}
        if opts.send_temperature:
            body["temperature"] = opts.temperature
        headers = {"Authorization": "Bearer %s" % key, "Content-Type": "application/json"}
        return self._run(assignment, model, self._base_url + "/chat/completions", body, headers,
                         timeout_s, max_retries,
                         extract_text=lambda p: p["choices"][0]["message"]["content"],
                         usage_style="openai" if self.name != "deepseek" else "deepseek")


class GeminiProvider(_LiveProviderBase):
    """Native Google Generative Language adapter (generateContent). The API key
    is sent as the x-goog-api-key header (never in the URL). Structured output
    via responseMimeType application/json. Constructed only behind the airlock."""

    def __init__(self, auth: LiveAuthorization, *, base_url: Optional[str] = None):
        super().__init__(auth, "gemini", base_url or _DEFAULT_BASE_URLS["gemini"])

    def propose(self, assignment: Assignment, *, model: str, output_token_cap: int,
                timeout_s: float, max_retries: int) -> ModelProposal:
        self._guard_model(model)
        from services.research_workers.prompt import build_worker_prompt
        system, user = build_worker_prompt(assignment)
        key = os.environ[self._api_key_env]
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0, "maxOutputTokens": int(output_token_cap),
                                     "responseMimeType": "application/json"}}
        headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
        url = "%s/models/%s:generateContent" % (self._base_url, model)

        def _extract(p):
            return p["candidates"][0]["content"]["parts"][0]["text"]
        return self._run(assignment, model, url, body, headers, timeout_s, max_retries,
                         extract_text=_extract, usage_style="gemini")


def build_provider(name: str, *, auth: Optional[LiveAuthorization] = None,
                   base_url: Optional[str] = None,
                   request_options: Optional[ChatRequestOptions] = None) -> ResearchProvider:
    """Factory. ``fake`` needs nothing and never networks. Any live provider must
    pass the airlock at construction time. ``request_options`` shapes the chat-
    completions body per model family; Gemini has its own native dialect."""
    if name == "fake":
        return FakeProvider()
    if auth is None:
        raise SpendingAirlockError("live provider %r requires a LiveAuthorization" % name)
    if name in _OPENAI_COMPATIBLE:
        return OpenAICompatibleProvider(auth, name=("deepseek" if name == "deepseek" else "openai"),
                                        base_url=base_url, request_options=request_options)
    if name == "gemini":
        return GeminiProvider(auth, base_url=base_url)
    raise SpendingAirlockError("unknown provider: %r" % name)

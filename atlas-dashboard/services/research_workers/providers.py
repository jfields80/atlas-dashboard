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
from services.research_workers.proposal import ModelProposal, RawFactClaim


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
    (V.FEE_BASIS_PER_ROOM_PER_DAY, re.compile(r"per room[ ,]+per day|per room/day|room per day", re.I)),
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
# Live OpenAI-compatible adapter (constructed ONLY behind the airlock).
# --------------------------------------------------------------------------- #

class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible chat-completions adapter. It cannot be built
    without passing the spending airlock, and it uses only the Python stdlib
    (urllib) so no package install is required. Not exercised in this phase --
    no paid call is made."""

    name = "openai"

    def __init__(self, auth: LiveAuthorization, *, base_url: str = "https://api.openai.com/v1"):
        self._api_key_env = require_live_authorization(auth)   # raises unless fully authorized
        self._auth = auth
        self._base_url = base_url.rstrip("/")

    def propose(self, assignment: Assignment, *, model: str, output_token_cap: int,
                timeout_s: float, max_retries: int) -> ModelProposal:
        if model != self._auth.model:
            # Never silently switch models away from what was authorized.
            raise SpendingAirlockError("model %r was not the authorized model %r"
                                       % (model, self._auth.model))
        import json as _json
        import urllib.request as _rq
        from services.research_workers.prompt import build_worker_prompt, parse_worker_payload

        system, user = build_worker_prompt(assignment)
        key = os.environ[self._api_key_env]                    # read at call time only
        body = _json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": int(output_token_cap),
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        last_err = ""
        attempts = 0
        for attempt in range(max(1, max_retries + 1)):
            attempts = attempt + 1
            t0 = time.time()
            try:
                req = _rq.Request(self._base_url + "/chat/completions", data=body, headers={
                    "Authorization": "Bearer %s" % key, "Content-Type": "application/json"})
                with _rq.urlopen(req, timeout=timeout_s) as resp:
                    payload = _json.loads(resp.read().decode("utf-8"))
                latency_ms = int((time.time() - t0) * 1000)
                text = payload["choices"][0]["message"]["content"]
                usage = payload.get("usage", {})
                claims, ok = parse_worker_payload(text, assignment)
                return ModelProposal(
                    claims=tuple(claims), ok=ok, structured_output_valid=ok,
                    error="" if ok else "unparseable_output", provider=self.name, model=model,
                    input_tokens=int(usage.get("prompt_tokens", 0)),
                    output_tokens=int(usage.get("completion_tokens", 0)),
                    cached_input_tokens=int(usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)),
                    latency_ms=latency_ms, attempt_count=attempts)
            except Exception as exc:                            # noqa: BLE001 -- bounded retry
                last_err = type(exc).__name__
        return ModelProposal(ok=False, error="request_failed:%s" % last_err,
                             structured_output_valid=False, provider=self.name, model=model,
                             attempt_count=attempts)


def build_provider(name: str, *, auth: Optional[LiveAuthorization] = None) -> ResearchProvider:
    """Factory. ``fake`` needs nothing and never networks. Any live provider
    must pass the airlock at construction time."""
    if name == "fake":
        return FakeProvider()
    if name in ("openai", "openai-compatible"):
        if auth is None:
            raise SpendingAirlockError("live provider %r requires a LiveAuthorization" % name)
        return OpenAICompatibleProvider(auth)
    raise SpendingAirlockError("unknown provider: %r" % name)

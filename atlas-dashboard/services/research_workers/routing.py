"""ATLAS-WORKERS-003 -- deterministic publication routing airlock.

Converts a validated HOTEL_POLICY_RESEARCH result into exactly one safe
operational destination -- READY / REVIEW / RETRY / REJECTED -- plus canonical
reason codes, and packages the decision into an immutable, typed routing
envelope for a gitignored operator queue.

Design authority and boundaries:

* The worker/model NEVER selects its own route. ``vocabulary`` states this
  explicitly ("The worker NEVER emits READY/REVIEW/REJECT -- those are Atlas's
  decision"). This module IS that Atlas decision layer. Every route is derived
  deterministically from the validated ``WorkerResult`` (and, when available,
  the sanitized provider-error detail on the ``ModelProposal``) -- never from a
  free-form model explanation and never from benchmark expected answers (there
  are none in production).
* READY is FAIL-CLOSED. A result reaches READY only when every applicable
  publication requirement passes; a missing, unknown, or unrecognized condition
  can never default to READY.
* This module never publishes, never writes to production inventory, never
  calls a model, and never reads the wall clock. Any observed/decision time is
  an explicit input, so identical inputs produce byte-identical envelopes.
* It only ever WITHHOLDS more (fail-closed): it adds routing-layer safety
  backstops (prompt-injection-in-evidence, un-named-species inference,
  non-verbatim evidence) on top of the deterministic validator, and never
  loosens an evidence or publication gate.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, WorkerResult, canonical_json,
)
from services.research_workers.proposal import ModelProposal, is_provider_error

# Routing-contract revision, recorded in every envelope so envelopes produced
# under different routing logic are never silently conflated (the same
# discipline as prompt_version / validator_version).
ROUTING_VERSION = "1.0.0"


class RoutingError(RuntimeError):
    """Raised for a routing-layer safety failure (e.g. a disabled escalation)."""


# --------------------------------------------------------------------------- #
# Route states. The worker's own statuses (COMPLETED/NEEDS_REVIEW/...) describe
# what it FOUND; these four describe what Atlas DOES with it.
# --------------------------------------------------------------------------- #

ROUTE_READY = "READY"          # eligible to proceed toward publication
ROUTE_REVIEW = "REVIEW"        # safely withheld for human review / Tier-2
ROUTE_RETRY = "RETRY"          # bounded transient failure; may be retried
ROUTE_REJECTED = "REJECTED"    # structurally unsafe / permanently invalid
ROUTE_STATES = (ROUTE_READY, ROUTE_REVIEW, ROUTE_RETRY, ROUTE_REJECTED)


# --------------------------------------------------------------------------- #
# Canonical reason codes. Every route carries at least one; they are derived
# deterministically from result fields, never from model prose.
# --------------------------------------------------------------------------- #

# READY.
PUBLICATION_ELIGIBLE = "PUBLICATION_ELIGIBLE"

# REVIEW.
CONTRADICTORY_OFFICIAL_SOURCES = "CONTRADICTORY_OFFICIAL_SOURCES"
NO_OFFICIAL_SOURCE = "NO_OFFICIAL_SOURCE"
EXACT_EVIDENCE_MISMATCH = "EXACT_EVIDENCE_MISMATCH"
INCOMPLETE_EXTRACTION = "INCOMPLETE_EXTRACTION"
UNSUPPORTED_INFERENCE = "UNSUPPORTED_INFERENCE"
FORBIDDEN_INFERENCE = "FORBIDDEN_INFERENCE"
VALIDATOR_WARNING = "VALIDATOR_WARNING"
MODEL_QUALITY_FAILURE = "MODEL_QUALITY_FAILURE"
PROMPT_INJECTION_RISK = "PROMPT_INJECTION_RISK"
SOURCE_AUTHORITY_AMBIGUITY = "SOURCE_AUTHORITY_AMBIGUITY"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"

# RETRY.
PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
PROVIDER_SERVER_ERROR = "PROVIDER_SERVER_ERROR"
TRANSPORT_FAILURE = "TRANSPORT_FAILURE"

# REJECTED.
INVALID_WORKER_CONTRACT = "INVALID_WORKER_CONTRACT"
INVALID_ROUTING_ENVELOPE = "INVALID_ROUTING_ENVELOPE"
PROVIDER_CONFIG_ERROR = "PROVIDER_CONFIG_ERROR"
PROVIDER_AUTH_ERROR = "PROVIDER_AUTH_ERROR"
NON_TRANSIENT_PROVIDER_ERROR = "NON_TRANSIENT_PROVIDER_ERROR"
CORRUPT_EVIDENCE_BUNDLE = "CORRUPT_EVIDENCE_BUNDLE"
UNSAFE_RESULT = "UNSAFE_RESULT"

READY_REASONS = frozenset({PUBLICATION_ELIGIBLE})
REVIEW_REASONS = frozenset({
    CONTRADICTORY_OFFICIAL_SOURCES, NO_OFFICIAL_SOURCE, EXACT_EVIDENCE_MISMATCH,
    INCOMPLETE_EXTRACTION, UNSUPPORTED_INFERENCE, FORBIDDEN_INFERENCE,
    VALIDATOR_WARNING, MODEL_QUALITY_FAILURE, PROMPT_INJECTION_RISK,
    SOURCE_AUTHORITY_AMBIGUITY, HUMAN_REVIEW_REQUIRED,
})
RETRY_REASONS = frozenset({
    PROVIDER_TIMEOUT, PROVIDER_RATE_LIMITED, PROVIDER_SERVER_ERROR, TRANSPORT_FAILURE,
})
REJECTED_REASONS = frozenset({
    INVALID_WORKER_CONTRACT, INVALID_ROUTING_ENVELOPE, PROVIDER_CONFIG_ERROR,
    PROVIDER_AUTH_ERROR, NON_TRANSIENT_PROVIDER_ERROR, CORRUPT_EVIDENCE_BUNDLE,
    UNSAFE_RESULT,
})
_REASONS_FOR_ROUTE = {
    ROUTE_READY: READY_REASONS, ROUTE_REVIEW: REVIEW_REASONS,
    ROUTE_RETRY: RETRY_REASONS, ROUTE_REJECTED: REJECTED_REASONS,
}
ALL_REASONS = READY_REASONS | REVIEW_REASONS | RETRY_REASONS | REJECTED_REASONS


# --------------------------------------------------------------------------- #
# Routing-layer safety patterns (fail-closed backstops applied to a COMPLETED
# result BEFORE it can reach READY -- these only ever withhold more).
# --------------------------------------------------------------------------- #

# Known prompt-injection / instruction-override phrasing. If a SUPPORTED fact's
# own evidence quote IS injected instruction text, the model may have obeyed the
# document instead of reading policy -- withhold regardless of what the validator
# accepted (the validator checks the quote is verbatim, not that it is policy).
_INJECTION_RE = re.compile(
    r"ignore (?:all )?previous instructions"
    r"|disregard (?:all )?(?:previous|prior) (?:instructions|text)"
    r"|mark every"
    r"|you are now"
    r"|system message"
    r"|\bassistant\s*:"
    r"|new instructions\s*:",
    re.I)


# --------------------------------------------------------------------------- #
# The immutable routing envelope.
# --------------------------------------------------------------------------- #

# Excluded from content_hash + route_id: caller-supplied correlation inputs and
# the derived hashes themselves. route_id/content_hash therefore identify the
# ROUTING DECISION content, independent of when it was observed or which run
# correlated it -- so idempotent re-routing of the same validated result under
# the same contract versions is byte-stable.
_ENVELOPE_VOLATILE = frozenset({"observed_at", "run_id", "content_hash"})


@dataclass(frozen=True)
class RoutingEnvelope:
    route_id: str
    route: str
    reason_codes: Tuple[str, ...]
    assignment_id: str
    listing_key: str
    worker_type: str
    worker_contract_version: str
    prompt_version: str
    validator_version: str
    routing_version: str
    provider: str
    model: str
    research_status: str
    publication_eligible: bool
    selected_source_url: str
    selected_source_type: str
    source_identities: Tuple[Dict[str, str], ...]
    supported_facts: Tuple[Dict[str, str], ...]
    contradictions: Tuple[str, ...]
    provider_error: Optional[Dict] = None
    result_hash: str = ""
    run_id: str = ""
    observed_at: str = ""
    content_hash: str = ""

    # -- serialization ----------------------------------------------------- #
    def to_dict(self) -> Dict:
        return {
            "route_id": self.route_id,
            "route": self.route,
            "reason_codes": list(self.reason_codes),
            "assignment_id": self.assignment_id,
            "listing_key": self.listing_key,
            "worker_type": self.worker_type,
            "worker_contract_version": self.worker_contract_version,
            "prompt_version": self.prompt_version,
            "validator_version": self.validator_version,
            "routing_version": self.routing_version,
            "provider": self.provider,
            "model": self.model,
            "research_status": self.research_status,
            "publication_eligible": self.publication_eligible,
            "selected_source_url": self.selected_source_url,
            "selected_source_type": self.selected_source_type,
            "source_identities": [dict(s) for s in self.source_identities],
            "supported_facts": [dict(f) for f in self.supported_facts],
            "contradictions": list(self.contradictions),
            "provider_error": self.provider_error,
            "result_hash": self.result_hash,
            "run_id": self.run_id,
            "observed_at": self.observed_at,
            "content_hash": self.content_hash,
        }

    @staticmethod
    def from_dict(d: Dict) -> "RoutingEnvelope":
        return RoutingEnvelope(
            route_id=str(d["route_id"]), route=str(d["route"]),
            reason_codes=tuple(str(r) for r in d.get("reason_codes", [])),
            assignment_id=str(d["assignment_id"]), listing_key=str(d.get("listing_key", "")),
            worker_type=str(d.get("worker_type", "")),
            worker_contract_version=str(d.get("worker_contract_version", "")),
            prompt_version=str(d.get("prompt_version", "")),
            validator_version=str(d.get("validator_version", "")),
            routing_version=str(d.get("routing_version", "")),
            provider=str(d.get("provider", "")), model=str(d.get("model", "")),
            research_status=str(d.get("research_status", "")),
            publication_eligible=bool(d.get("publication_eligible", False)),
            selected_source_url=str(d.get("selected_source_url", "")),
            selected_source_type=str(d.get("selected_source_type", "")),
            source_identities=tuple(dict((str(k), str(v)) for k, v in s.items())
                                    for s in d.get("source_identities", [])),
            supported_facts=tuple(dict((str(k), str(v)) for k, v in f.items())
                                  for f in d.get("supported_facts", [])),
            contradictions=tuple(str(c) for c in d.get("contradictions", [])),
            provider_error=d.get("provider_error"),
            result_hash=str(d.get("result_hash", "")),
            run_id=str(d.get("run_id", "")), observed_at=str(d.get("observed_at", "")),
            content_hash=str(d.get("content_hash", "")))

    # -- identity ---------------------------------------------------------- #
    def _content_for_hash(self) -> Dict:
        return {k: v for k, v in self.to_dict().items() if k not in _ENVELOPE_VOLATILE}

    def compute_content_hash(self) -> str:
        return "sha256:" + hashlib.sha256(
            canonical_json(self._content_for_hash()).encode("utf-8")).hexdigest()

    def queue_filename(self) -> str:
        # route_id is "route:<hex>"; ':' is not a safe filename char, so the
        # queue file is "route_<hex>.json" (deterministic, collision-free).
        return self.route_id.replace("route:", "route_") + ".json"

    def validate(self) -> None:
        if self.route not in ROUTE_STATES:
            raise RoutingError("unknown route: %r" % self.route)
        if not self.reason_codes:
            raise RoutingError("a routing envelope must carry at least one reason code")
        allowed = _REASONS_FOR_ROUTE[self.route]
        for r in self.reason_codes:
            if r not in allowed:
                raise RoutingError("reason %r is not valid for route %s" % (r, self.route))
        if self.publication_eligible and self.route != ROUTE_READY:
            raise RoutingError("publication_eligible is only ever true for READY")
        if self.content_hash and self.content_hash != self.compute_content_hash():
            raise RoutingError("content_hash mismatch for route_id %s" % self.route_id)


# --------------------------------------------------------------------------- #
# Deterministic decision helpers.
# --------------------------------------------------------------------------- #

def _transient_reason(status: int) -> str:
    if status == 408:
        return PROVIDER_TIMEOUT
    if status == 429:
        return PROVIDER_RATE_LIMITED
    if status in (500, 502, 503, 504):
        return PROVIDER_SERVER_ERROR
    return TRANSPORT_FAILURE          # status 0 == no HTTP response (transport)


def _non_transient_reason(status: int) -> str:
    if status in (401, 403):
        return PROVIDER_AUTH_ERROR
    if status in (400, 404, 422):
        return PROVIDER_CONFIG_ERROR
    return NON_TRANSIENT_PROVIDER_ERROR


def _integrity_blockers(assignment: Assignment, result: WorkerResult) -> set:
    """REJECTED conditions: the request/contract/evidence itself is unsafe or
    corrupt (as opposed to a model that merely produced a weak answer)."""
    blockers: set = set()
    if (assignment.worker_type != V.WORKER_TYPE_HOTEL_POLICY
            or result.worker_type != V.WORKER_TYPE_HOTEL_POLICY):
        blockers.add(INVALID_WORKER_CONTRACT)
    if result.contract_version != assignment.contract_version:
        blockers.add(INVALID_WORKER_CONTRACT)
    if result.assignment_id != assignment.assignment_id:
        blockers.add(INVALID_ROUTING_ENVELOPE)
    # Corrupt evidence bundle: every SUPPORTED fact must cite a usable official
    # document from THIS assignment and quote it verbatim. The validator already
    # guarantees this; re-checking here keeps routing fail-closed against a
    # malformed or tampered result it did not itself produce.
    usable = {d.source_url: d for d in assignment.source_documents if d.is_usable_official}
    for f in result.proposed_facts:
        if f.state != V.SUPPORTED:
            continue
        doc = usable.get(f.source_url)
        if doc is None or not f.evidence_quote or f.evidence_quote not in doc.content_text:
            blockers.add(CORRUPT_EVIDENCE_BUNDLE)
    return blockers


def _safety_blockers(result: WorkerResult) -> set:
    """Routing-layer backstops that force a COMPLETED result to REVIEW (never
    READY). Independent of the validator: a fact can be verbatim-valid yet still
    unsafe to auto-publish (its evidence is injected instructions, or a species
    claim whose quote does not name the species slipped through)."""
    blockers: set = set()
    for f in result.proposed_facts:
        if f.state != V.SUPPORTED:
            continue
        quote = f.evidence_quote or ""
        if _INJECTION_RE.search(quote):
            blockers.add(PROMPT_INJECTION_RISK)
        if f.field_name == V.FIELD_DOGS_ACCEPTED and "dog" not in quote.lower():
            blockers.add(FORBIDDEN_INFERENCE)
        if f.field_name == V.FIELD_CATS_ACCEPTED and "cat" not in quote.lower():
            blockers.add(FORBIDDEN_INFERENCE)
    return blockers


def _ready_blockers(result: WorkerResult) -> set:
    """Publication-airlock conditions for a COMPLETED result. Any blocker means
    REVIEW, never READY (fail-closed)."""
    blockers: set = set()
    if not result.selected_source_url or result.selected_source_type not in V.OFFICIAL_SOURCE_TYPES:
        blockers.add(NO_OFFICIAL_SOURCE)
    if result.contradictions:
        blockers.add(CONTRADICTORY_OFFICIAL_SOURCES)
    if any(w.startswith("rejected_") or w.startswith("brand_disagrees_with_property")
           for w in result.warnings):
        blockers.add(VALIDATOR_WARNING)
    if not any(f.state == V.SUPPORTED for f in result.proposed_facts):
        blockers.add(INCOMPLETE_EXTRACTION)     # nothing to publish
    return blockers


def _warning_reasons(result: WorkerResult) -> set:
    """Map validator warnings on a NEEDS_REVIEW result to canonical reasons."""
    reasons: set = set()
    for w in result.warnings:
        tail = w.split(":", 1)[1] if ":" in w else ""
        if w.startswith("rejected_"):
            if tail == "species_not_in_quote":
                reasons.add(UNSUPPORTED_INFERENCE)
            elif tail == "quote_not_verbatim":
                reasons.add(EXACT_EVIDENCE_MISMATCH)
            elif tail in ("non_boolean_value", "fee_basis_phrase_absent",
                          "number_not_in_quote", "deposit_word_absent",
                          "empty_value_or_quote"):
                reasons.add(INCOMPLETE_EXTRACTION)
            elif tail == "source_not_official":
                reasons.add(SOURCE_AUTHORITY_AMBIGUITY)
            else:
                reasons.add(VALIDATOR_WARNING)
        elif w.startswith("brand_disagrees_with_property"):
            reasons.add(SOURCE_AUTHORITY_AMBIGUITY)
        elif w == "no_usable_official_source":
            reasons.add(NO_OFFICIAL_SOURCE)
        else:
            reasons.add(VALIDATOR_WARNING)
    return reasons


def _decide(assignment: Assignment, result: WorkerResult,
            proposal: Optional[ModelProposal]) -> Tuple[str, List[str], Optional[Dict]]:
    """Return (route, sorted reason codes, sanitized provider_error dict|None).

    Precedence is fail-closed: provider/transport failure, then unparseable
    model output, then contract/evidence integrity, then the result status. An
    unknown status falls through to REJECTED, never READY."""
    # 1) Provider / transport failure -- the model never produced a usable
    #    response. RETRY only for a KNOWN bounded transient signal; REJECTED for a
    #    deterministic (non-transient) provider/config/auth error.
    if proposal is not None and is_provider_error(proposal):
        detail = proposal.provider_error
        if detail is not None:
            pe = detail.to_dict()
            if detail.transient:
                return ROUTE_RETRY, [_transient_reason(detail.http_status)], pe
            return ROUTE_REJECTED, [_non_transient_reason(detail.http_status)], pe
        # No structured detail (legacy/synthetic slug). A transport failure
        # ("request_failed:") had no HTTP response -> transient; anything else is
        # not confirmably transient -> fail-closed to REJECTED, never RETRY.
        if (proposal.error or "").startswith("request_failed:"):
            return ROUTE_RETRY, [TRANSPORT_FAILURE], None
        return ROUTE_REJECTED, [NON_TRANSIENT_PROVIDER_ERROR], None

    # 2) The model responded but its output could not be parsed into the worker
    #    contract. Safely withheld (a stronger tier / human may re-extract) --
    #    never RETRY (not a transport failure) and never READY.
    if proposal is not None and not proposal.ok:
        return ROUTE_REVIEW, [MODEL_QUALITY_FAILURE], None

    # 3) Contract / envelope / evidence integrity -> REJECTED.
    integrity = _integrity_blockers(assignment, result)
    if integrity:
        return ROUTE_REJECTED, sorted(integrity), None

    # 4) Status-driven routing over a structurally-sound result.
    status = result.status
    if status == V.STATUS_FAILED:
        # Reached here only without a proposal to classify (fail-closed): a bare
        # FAILED result is withheld, never retried or published.
        return ROUTE_REVIEW, [MODEL_QUALITY_FAILURE], None
    if result.contradictions or status == V.STATUS_CONTRADICTORY:
        return ROUTE_REVIEW, [CONTRADICTORY_OFFICIAL_SOURCES], None
    if status == V.STATUS_NO_OFFICIAL_SOURCE:
        return ROUTE_REVIEW, [NO_OFFICIAL_SOURCE], None
    if status == V.STATUS_NEEDS_REVIEW:
        reasons = _warning_reasons(result) or {HUMAN_REVIEW_REQUIRED}
        return ROUTE_REVIEW, sorted(reasons), None
    if status == V.STATUS_COMPLETED:
        blockers = _safety_blockers(result) | _ready_blockers(result)
        if blockers:
            return ROUTE_REVIEW, sorted(blockers), None
        return ROUTE_READY, [PUBLICATION_ELIGIBLE], None

    return ROUTE_REJECTED, [UNSAFE_RESULT], None


# --------------------------------------------------------------------------- #
# Public entry point.
# --------------------------------------------------------------------------- #

def _source_identities(assignment: Assignment) -> Tuple[Dict[str, str], ...]:
    docs = sorted((d for d in assignment.source_documents if d.is_usable_official),
                  key=lambda d: (-V.SOURCE_TYPE_RANK.get(d.source_type, 0), d.source_url))
    return tuple({"source_url": d.source_url, "source_type": d.source_type} for d in docs)


def _supported_facts(result: WorkerResult) -> Tuple[Dict[str, str], ...]:
    return tuple({"field_name": f.field_name, "value": f.value,
                  "evidence_quote": f.evidence_quote, "source_url": f.source_url,
                  "source_type": f.source_type}
                 for f in result.proposed_facts if f.state == V.SUPPORTED)


def route_result(assignment: Assignment, result: WorkerResult,
                 proposal: Optional[ModelProposal] = None, *,
                 prompt_version: str = "", validator_version: str = "",
                 observed_at: str = "", run_id: str = "") -> RoutingEnvelope:
    """Deterministically route ONE validated worker result into the
    READY/REVIEW/RETRY/REJECTED airlock and return an immutable envelope.

    ``proposal`` (when supplied) carries the sanitized provider-error detail used
    to distinguish RETRY (transient) from REJECTED (non-transient); routing works
    without it, but a bare FAILED result is then withheld to REVIEW rather than
    retried. ``observed_at`` / ``run_id`` are explicit correlation inputs -- no
    wall clock is read, so identical inputs yield a byte-identical envelope."""
    route, reasons, provider_error = _decide(assignment, result, proposal)
    provider = result.provider or (proposal.provider if proposal is not None else "")
    model = result.model or (proposal.model if proposal is not None else "")

    identity = {
        "assignment_id": assignment.assignment_id,
        "result_hash": result.result_hash or result.compute_hash(),
        "worker_type": result.worker_type,
        "worker_contract_version": result.contract_version,
        "prompt_version": prompt_version,
        "validator_version": validator_version,
        "routing_version": ROUTING_VERSION,
        "provider": provider, "model": model,
        "route": route, "reason_codes": list(reasons),
    }
    route_id = "route:" + hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()

    env = RoutingEnvelope(
        route_id=route_id, route=route, reason_codes=tuple(reasons),
        assignment_id=assignment.assignment_id, listing_key=result.listing_key,
        worker_type=result.worker_type, worker_contract_version=result.contract_version,
        prompt_version=prompt_version, validator_version=validator_version,
        routing_version=ROUTING_VERSION, provider=provider, model=model,
        research_status=result.status, publication_eligible=(route == ROUTE_READY),
        selected_source_url=result.selected_source_url,
        selected_source_type=result.selected_source_type,
        source_identities=_source_identities(assignment),
        supported_facts=_supported_facts(result),
        contradictions=tuple(result.contradictions),
        provider_error=provider_error,
        result_hash=result.result_hash or result.compute_hash(),
        run_id=run_id, observed_at=observed_at)
    env = _with_content_hash(env)
    env.validate()
    return env


def _with_content_hash(env: RoutingEnvelope) -> RoutingEnvelope:
    from dataclasses import replace
    return replace(env, content_hash=env.compute_content_hash())


def summarize_envelopes(envelopes: Sequence[RoutingEnvelope]) -> Dict:
    """Deterministic route + reason counts for an operator summary."""
    routes = {r: 0 for r in ROUTE_STATES}
    reasons: Dict[str, int] = {}
    for e in envelopes:
        routes[e.route] = routes.get(e.route, 0) + 1
        for r in e.reason_codes:
            reasons[r] = reasons.get(r, 0) + 1
    return {"total": len(envelopes), "routes": routes,
            "reasons": dict(sorted(reasons.items()))}


# --------------------------------------------------------------------------- #
# Tier-2 escalation contract (DEFINED, never executed this sprint).
# --------------------------------------------------------------------------- #

# Hard off-switch. Tier-2 escalation is a CONTRACT only in ATLAS-WORKERS-003:
# no live model call is authorized, no provider/model is ever inferred from
# availability, and a contradictory-source or no-source case must never become
# publishable merely because a Tier-2 model would return an answer.
TIER2_ENABLED = False


@dataclass(frozen=True)
class Tier2EscalationRequest:
    """A typed request to re-run a withheld assignment on an operator-authorized
    stronger model. Building one is pure and side-effect-free; executing one is
    disabled (see ``escalate_tier2``)."""

    routing_envelope_id: str
    assignment_id: str
    worker_type: str
    escalation_reasons: Tuple[str, ...]
    allowed_source_urls: Tuple[str, ...]
    disputed_fields: Tuple[str, ...]
    prior_provider: str
    prior_model: str
    prior_supported_claims: Tuple[Dict[str, str], ...]
    contradictions: Tuple[str, ...]
    validator_warnings: Tuple[str, ...]
    max_spend_usd: float
    tier2_provider: str                 # operator-supplied ONLY; "" == none authorized
    tier2_model: str                    # operator-supplied ONLY; "" == none authorized
    require_human_review_after: bool

    def to_dict(self) -> Dict:
        return {
            "routing_envelope_id": self.routing_envelope_id,
            "assignment_id": self.assignment_id, "worker_type": self.worker_type,
            "escalation_reasons": list(self.escalation_reasons),
            "allowed_source_urls": list(self.allowed_source_urls),
            "disputed_fields": list(self.disputed_fields),
            "prior_provider": self.prior_provider, "prior_model": self.prior_model,
            "prior_supported_claims": [dict(c) for c in self.prior_supported_claims],
            "contradictions": list(self.contradictions),
            "validator_warnings": list(self.validator_warnings),
            "max_spend_usd": self.max_spend_usd,
            "tier2_provider": self.tier2_provider, "tier2_model": self.tier2_model,
            "require_human_review_after": self.require_human_review_after,
            "tier2_enabled": TIER2_ENABLED,
        }


def build_tier2_escalation(assignment: Assignment, envelope: RoutingEnvelope,
                           result: WorkerResult, *, max_spend_usd: float = 0.0,
                           tier2_provider: str = "", tier2_model: str = "",
                           require_human_review_after: bool = True) -> Tier2EscalationRequest:
    """Construct a Tier-2 escalation request from a withheld routing decision.
    Pure: it selects NO model, calls NO model, and never infers a provider from
    availability. ``tier2_provider`` / ``tier2_model`` are honored ONLY when an
    operator supplies them explicitly."""
    supported_names = {f.field_name for f in result.proposed_facts if f.state == V.SUPPORTED}
    disputed = tuple(f for f in assignment.requested_fields if f not in supported_names)
    return Tier2EscalationRequest(
        routing_envelope_id=envelope.route_id, assignment_id=assignment.assignment_id,
        worker_type=result.worker_type, escalation_reasons=tuple(envelope.reason_codes),
        allowed_source_urls=tuple(assignment.allowed_source_urls), disputed_fields=disputed,
        prior_provider=envelope.provider, prior_model=envelope.model,
        prior_supported_claims=envelope.supported_facts,
        contradictions=tuple(result.contradictions), validator_warnings=tuple(result.warnings),
        max_spend_usd=max_spend_usd, tier2_provider=tier2_provider, tier2_model=tier2_model,
        require_human_review_after=require_human_review_after)


def escalate_tier2(request: Tier2EscalationRequest) -> None:
    """Executing a Tier-2 escalation is DISABLED in ATLAS-WORKERS-003. Always
    raises -- no live model call, no silent fallback, no availability-based model
    inference is permitted in this sprint."""
    raise RoutingError(
        "Tier-2 escalation is disabled (TIER2_ENABLED is False): no live model "
        "call is authorized in ATLAS-WORKERS-003; an operator must explicitly "
        "enable and authorize a Tier-2 model in a later sprint")

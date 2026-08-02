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
from services.research_workers.fee_terms import downstream_fee_schema_support
from services.research_workers.proposal import ModelProposal, is_provider_error

# Routing-contract revision, recorded in every envelope so envelopes produced
# under different routing logic are never silently conflated (the same
# discipline as prompt_version / validator_version).
#   1.1.0 -- ATLAS-WORKERS-006: a validated structured PetFeePolicy (a tiered/
#            capped/conditional fee) is carried additively on the envelope, and a
#            result bearing one can never route READY while the production
#            importer/renderer remain single-value -- it routes REVIEW with the
#            deterministic DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED reason (fail-closed).
#   1.2.0 -- ATLAS-WORKERS-006 Stage-D fail-closed safety remediation: the
#            STRUCTURED_FEE_REQUIRED review reason. When the evidence states
#            multiple distinct pet-fee amounts but no validated structured policy
#            exists (the model flattened to a single scalar), the validator
#            withholds the scalar and the result routes REVIEW -- a misleading
#            single fee can never reach READY.
#   1.3.0 -- PTF-WORKERS: the MODEL_OVERCLAIM review reason. A rejected claim
#            for a field the SOURCE never states is an invention the airlock
#            caught, not a fact we failed to extract, and only the latter
#            deserves the never-waivable INCOMPLETE_EXTRACTION. Additive:
#            diagnostic-only warnings stop becoming reason codes, and an
#            overclaim-only reason set on a record with nothing publishable
#            still reports INCOMPLETE_EXTRACTION. No route decision changes for
#            any record in the frozen corpus -- proven by replaying it: the 15
#            launch-safe result_hashes are byte-identical, so every existing
#            approval stays bound and only gate1_manifest_sha256 is re-pinned.
#   1.4.0 -- PTF-WORKERS: DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED becomes a
#            CAPABILITY check. It withheld every structured fee on the grounds
#            that the production chain was single-value; fee_tiers shipped and
#            three published profiles render a stay-length ladder today, so the
#            rule was answering "is there a structured fee?" instead of "can we
#            render THIS one honestly?". A shape the chain cannot carry -- a
#            gap, an overlap, a non-final open tier, a cap or deposit role, a
#            currency the renderer cannot format -- is still withheld, now with
#            the exact reason. Same replay proof: routes and result_hashes
#            byte-identical across the frozen corpus.
ROUTING_VERSION = "1.4.0"


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
# The model asserted a fact the authoritative source never states, and the
# validator rejected it. That is the airlock WORKING, not a gap in extraction:
# nothing was missed, because there was nothing there. Kept as its own reason so
# a reviewer can see the difference between "we failed to read the page" and
# "the model made something up and we caught it" (PTF-WORKERS).
MODEL_OVERCLAIM = "MODEL_OVERCLAIM"
UNSUPPORTED_INFERENCE = "UNSUPPORTED_INFERENCE"
FORBIDDEN_INFERENCE = "FORBIDDEN_INFERENCE"
VALIDATOR_WARNING = "VALIDATOR_WARNING"
MODEL_QUALITY_FAILURE = "MODEL_QUALITY_FAILURE"
PROMPT_INJECTION_RISK = "PROMPT_INJECTION_RISK"
SOURCE_AUTHORITY_AMBIGUITY = "SOURCE_AUTHORITY_AMBIGUITY"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
# The worker fully represented a structured (tiered/capped/conditional) fee, but
# the current single-value production importer/renderer cannot consume it, so it
# is withheld -- research-complete, not publication-eligible (ATLAS-WORKERS-006).
DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED = "DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED"
# The evidence states multiple distinct pet-fee amounts but no validated
# structured policy was produced (the model flattened to a single scalar) -- the
# deterministic backstop withholds the misleading scalar and blocks READY
# (ATLAS-WORKERS-006 Stage-D fail-closed safety remediation).
STRUCTURED_FEE_REQUIRED = "STRUCTURED_FEE_REQUIRED"
# PTF-WORKERS-004. The result rests on a model-generated research report rather
# than on a page this system fetched and hashed. Research-useful, never
# publication-eligible: a report can paraphrase, conflate two properties, or
# summarize a page it only partly read, and a verbatim-quote check cannot catch
# any of that (the quote is verbatim in the REPORT). Withheld for a human.
MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE = "MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE"
# PTF-WORKERS-005. Real official evidence whose PROPERTY IDENTITY was inherited
# from a parent page rather than proven on the page itself. The bytes are
# sound; the "this page is about this hotel" link is inferential, and that link
# is exactly what a wrong pet policy on the wrong property would turn on. A
# human confirms it before publication -- never automatic.
INHERITED_IDENTITY_REQUIRES_REVIEW = "INHERITED_IDENTITY_REQUIRES_REVIEW"
# PTF-WORKERS-007. Real official evidence whose POLICY TEXT came from a search
# surface bound to a separately-captured property page. Every strong signal
# matched and the binding is recorded -- but "these two official pages describe
# the same hotel" remains an inference drawn across two documents, and a search
# surface re-queried tomorrow may show something else entirely. Publishable
# only through an explicit, hash-bound approval; never automatically.
PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW = "PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW"

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
    MODEL_OVERCLAIM,
    VALIDATOR_WARNING, MODEL_QUALITY_FAILURE, PROMPT_INJECTION_RISK,
    SOURCE_AUTHORITY_AMBIGUITY, HUMAN_REVIEW_REQUIRED,
    DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED, STRUCTURED_FEE_REQUIRED,
    MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE, INHERITED_IDENTITY_REQUIRES_REVIEW,
    PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW,
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
    fee_policy: Optional[Dict] = None       # ATLAS-WORKERS-006 structured pet-fee terms (additive)
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
            "fee_policy": self.fee_policy,
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
            fee_policy=d.get("fee_policy"),
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


def _model_research_provenance(assignment: Assignment, result: WorkerResult) -> bool:
    """True iff this result leans on model-research provenance anywhere.

    Two independent signals, because the two failure modes differ: the result
    SELECTED a research report as its source, or an individual supported fact
    cites one (directly by type, or by pointing at a research document supplied
    in the assignment).
    """
    research_urls = {d.source_url for d in assignment.source_documents
                     if d.source_type in V.NON_PUBLISHABLE_SOURCE_TYPES}
    if (result.selected_source_type in V.NON_PUBLISHABLE_SOURCE_TYPES
            or result.selected_source_url in research_urls):
        return True
    for f in result.proposed_facts:
        if f.state != V.SUPPORTED:
            continue
        if f.source_type in V.NON_PUBLISHABLE_SOURCE_TYPES or f.source_url in research_urls:
            return True
    return False


def _non_automatic_urls(assignment: Assignment) -> set:
    """URLs of every supplied document whose provenance cannot auto-publish."""
    return {d.source_url for d in assignment.source_documents
            if d.source_type in V.NON_AUTOMATIC_SOURCE_TYPES}


def _ready_blockers(assignment: Assignment, result: WorkerResult) -> set:
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
    # PTF-WORKERS. This once withheld EVERY structured fee, on the grounds that
    # the production chain was single-value. That stopped being true when
    # fee_tiers shipped -- three published profiles render a stay-length ladder
    # today -- so the rule was answering "is there a structured fee?" when the
    # question is "can we render THIS one honestly?". It now asks the second.
    # A shape the chain cannot carry is still withheld, with the exact reason.
    supported, _why = downstream_fee_schema_support(result.fee_policy)
    if not supported:
        blockers.add(DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED)
    # PTF-WORKERS-005/006: inherited identity and manual attestation may support
    # extraction but never publish automatically. Checked on the selected source
    # AND on each supported fact, because a result can select a self-identifying
    # page while an individual fact still rests on a non-automatic document.
    #
    # Resolved by source_URL against the assignment, not by the source_type the
    # result declares. An audit of the combined branch proved the type-only form
    # was bypassable: a fact citing a MANUAL_OFFICIAL_ATTESTATION document while
    # declaring a blank or spoofed OFFICIAL_PROPERTY type routed READY. A
    # backstop that believes the layer it is backstopping is not a backstop --
    # the document's own provenance is the only trustworthy answer. This mirrors
    # _model_research_provenance, which was already URL-resolved and was not
    # bypassable under the same attack.
    non_automatic = _non_automatic_urls(assignment)
    if (result.selected_source_type in V.NON_AUTOMATIC_SOURCE_TYPES
            or result.selected_source_url in non_automatic):
        blockers.add(INHERITED_IDENTITY_REQUIRES_REVIEW)
    for f in result.proposed_facts:
        if f.state != V.SUPPORTED:
            continue
        if (f.source_type in V.NON_AUTOMATIC_SOURCE_TYPES
                or f.source_url in non_automatic):
            blockers.add(INHERITED_IDENTITY_REQUIRES_REVIEW)
    return blockers


#: Warnings that RECORD what the validator did rather than reporting a fault.
#: They belong in provenance, never in a reason code -- a record must not be
#: held for review because we wrote down how we read its evidence. The
#: multi-amount companion warning established this treatment; the ladder and
#: sentinel diagnostics are the same kind of thing.
_DIAGNOSTIC_WARNING_PREFIXES = (
    "multi_term_fee_amounts",
    "stay_length_ladder_read_from_source",
    "stay_length_ladder_supersedes_scalar",
)


def _warning_reasons(result: WorkerResult) -> set:
    """Map validator warnings on a NEEDS_REVIEW result to canonical reasons."""
    reasons: set = set()
    for w in result.warnings:
        if w.startswith(_DIAGNOSTIC_WARNING_PREFIXES):
            continue                              # diagnostic-only companion warning
        tail = w.split(":", 1)[1] if ":" in w else ""
        # A rejection may carry provenance after its classification --
        # "unsupported_model_claim:species_not_in_quote:value=true" records the
        # rule that fired and what was refused. The classification leads, so
        # read that; the remainder is for a human, not for routing.
        tail = tail.split(":", 1)[0]
        if w.startswith("rejected_"):
            if tail == "multi_term_fee_unrepresented":
                reasons.add(STRUCTURED_FEE_REQUIRED)
            elif tail == "species_not_in_quote":
                reasons.add(UNSUPPORTED_INFERENCE)
            elif tail == "quote_not_verbatim":
                reasons.add(EXACT_EVIDENCE_MISMATCH)
            elif tail == "unsupported_model_claim":
                # The source states nothing about this field, so nothing was
                # missed. The model invented a value and the validator rejected
                # it -- the airlock working, not an extraction gap.
                reasons.add(MODEL_OVERCLAIM)
            elif tail == "overclaim_against_explicit_negation":
                # The source explicitly states this field is UNRESTRICTED and
                # the model proposed a restriction anyway. Same family as an
                # unsupported claim -- the model asserted something the evidence
                # does not carry -- so it reports under the same reason. The
                # fact IS extracted ("there is no limit"), which is why this was
                # never an INCOMPLETE_EXTRACTION.
                reasons.add(MODEL_OVERCLAIM)
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
        elif w.startswith("negated_field_sent_as_numeric_sentinel"):
            # The model put an absence into a field that holds quantities. The
            # claim was normalized away, not rejected; it is still an assertion
            # the evidence does not carry, so it reports as an overclaim.
            reasons.add(MODEL_OVERCLAIM)
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

    # 3) PTF-WORKERS-004 provenance backstop. Checked BEFORE integrity because
    #    the two would otherwise disagree on a result built from a model
    #    research report: _integrity_blockers looks a supported fact's source up
    #    among the USABLE OFFICIAL documents, finds a research report absent
    #    from that set, and rejects the whole bundle as corrupt. Rejection is
    #    not the intent -- model research is meant to be reviewed by a human,
    #    not discarded -- so the named, narrower rule runs first.
    #
    #    This weakens nothing. The condition is strictly "source_type is a
    #    non-publishable provenance", a source type that did not exist before
    #    this sprint, so no previously-routable result can reach it and every
    #    existing envelope routes byte-identically. Its outcome is REVIEW:
    #    fail-closed, never READY.
    if _model_research_provenance(assignment, result):
        return ROUTE_REVIEW, [MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE], None

    # 4) Contract / envelope / evidence integrity -> REJECTED.
    integrity = _integrity_blockers(assignment, result)
    if integrity:
        return ROUTE_REJECTED, sorted(integrity), None

    # 5) Status-driven routing over a structurally-sound result.
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
        # MODEL_OVERCLAIM explains why a claim was DISCARDED. It can never be
        # the whole story for a record that has nothing left to publish: an
        # empty candidate is incomplete no matter what was thrown away to get
        # there. Scoped to an overclaim-only reason set so the specific faults
        # (unsupported inference, evidence mismatch, human review) keep
        # reporting themselves exactly as before.
        if (reasons == {MODEL_OVERCLAIM}
                and not any(f.state == V.SUPPORTED for f in result.proposed_facts)):
            reasons.add(INCOMPLETE_EXTRACTION)
        return ROUTE_REVIEW, sorted(reasons), None
    if status == V.STATUS_COMPLETED:
        blockers = _safety_blockers(result) | _ready_blockers(assignment, result)
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
        fee_policy=(result.fee_policy.to_dict() if result.fee_policy is not None else None),
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

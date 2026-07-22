"""ATLAS-WORKERS-001 -- immutable worker input/output contracts.

Frozen dataclasses with deterministic ``to_dict``/``from_dict`` and canonical
JSON, mirroring the importer's frozen-model discipline
(scripts/pettripfinder/importer/models.py). Pure contracts: no I/O, no network,
no third-party imports. Fail-closed construction validates every enum against
services.research_workers.vocabulary so a malformed assignment/result cannot be
built silently.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

from services.research_workers import vocabulary as V


class ContractError(ValueError):
    """Raised when an assignment/result violates its schema (fail-closed)."""


# --------------------------------------------------------------------------- #
# Canonical JSON (single source of truth for serialization + hashing).
# --------------------------------------------------------------------------- #

def canonical_json(payload: Dict) -> str:
    """Compact, sorted, UTF-8 JSON used for hashing (stable across runs)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def pretty_json(payload: Dict) -> str:
    """Human/diff-friendly form used when persisting; sorted keys, LF, one
    trailing newline (deterministic bytes)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    """The canonical content hash for a source document's ``content_text``."""
    return "sha256:" + _sha256(text)


# --------------------------------------------------------------------------- #
# Assignment (worker INPUT).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SourceDocument:
    source_url: str
    source_type: str
    retrieved_at: str
    title: str
    content_text: str
    content_hash: str
    retrieval_status: str

    def to_dict(self) -> Dict:
        return dict(sorted(asdict(self).items()))

    @staticmethod
    def from_dict(d: Dict) -> "SourceDocument":
        return SourceDocument(
            source_url=str(d["source_url"]), source_type=str(d["source_type"]),
            retrieved_at=str(d.get("retrieved_at", "")), title=str(d.get("title", "")),
            content_text=str(d.get("content_text", "")),
            content_hash=str(d.get("content_hash", "")),
            retrieval_status=str(d["retrieval_status"]))

    def validate(self) -> None:
        if self.source_type not in V.SOURCE_TYPES:
            raise ContractError("unknown source_type: %r" % self.source_type)
        if self.retrieval_status not in V.RETRIEVAL_STATUSES:
            raise ContractError("unknown retrieval_status: %r" % self.retrieval_status)
        if len(self.content_text.encode("utf-8")) > V.SOURCE_CONTENT_CAP_BYTES:
            raise ContractError("source content_text exceeds cap for %r" % self.source_url)
        # A document that claims OK must actually carry content + a matching hash.
        if self.retrieval_status == V.RETRIEVAL_OK:
            if not self.content_text:
                raise ContractError("OK source has empty content_text: %r" % self.source_url)
            if self.content_hash and self.content_hash != content_hash(self.content_text):
                raise ContractError("content_hash mismatch: %r" % self.source_url)

    @property
    def is_usable_official(self) -> bool:
        return (self.retrieval_status == V.RETRIEVAL_OK
                and self.source_type in V.OFFICIAL_SOURCE_TYPES
                and bool(self.content_text))


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    market_slug: str
    listing_key: str
    listing_name: str
    address: str
    official_website: str
    allowed_source_urls: Tuple[str, ...]
    source_documents: Tuple[SourceDocument, ...]
    requested_fields: Tuple[str, ...]
    created_by: str
    contract_version: str = V.CONTRACT_VERSION
    worker_type: str = V.WORKER_TYPE_HOTEL_POLICY

    def to_dict(self) -> Dict:
        return {
            "assignment_id": self.assignment_id,
            "contract_version": self.contract_version,
            "worker_type": self.worker_type,
            "market_slug": self.market_slug,
            "listing_key": self.listing_key,
            "listing_name": self.listing_name,
            "address": self.address,
            "official_website": self.official_website,
            "allowed_source_urls": list(self.allowed_source_urls),
            "requested_fields": list(self.requested_fields),
            "created_by": self.created_by,
            "source_documents": [d.to_dict() for d in self.source_documents],
        }

    @staticmethod
    def from_dict(d: Dict) -> "Assignment":
        return Assignment(
            assignment_id=str(d["assignment_id"]),
            contract_version=str(d.get("contract_version", V.CONTRACT_VERSION)),
            worker_type=str(d.get("worker_type", V.WORKER_TYPE_HOTEL_POLICY)),
            market_slug=str(d["market_slug"]), listing_key=str(d["listing_key"]),
            listing_name=str(d.get("listing_name", "")), address=str(d.get("address", "")),
            official_website=str(d.get("official_website", "")),
            allowed_source_urls=tuple(str(u) for u in d.get("allowed_source_urls", [])),
            requested_fields=tuple(str(f) for f in d.get("requested_fields", [])),
            created_by=str(d.get("created_by", "")),
            source_documents=tuple(SourceDocument.from_dict(x)
                                   for x in d.get("source_documents", [])))

    def validate(self) -> None:
        if not self.assignment_id:
            raise ContractError("assignment_id is required")
        if self.worker_type != V.WORKER_TYPE_HOTEL_POLICY:
            raise ContractError("unsupported worker_type: %r" % self.worker_type)
        for f in self.requested_fields:
            if f not in V.POLICY_FIELD_SET:
                raise ContractError("requested field not in vocabulary: %r" % f)
        if len(self.source_documents) > V.MAX_SOURCE_DOCUMENTS:
            raise ContractError("too many source_documents")
        allowed = set(self.allowed_source_urls)
        for doc in self.source_documents:
            doc.validate()
            # A supplied document must be from the assignment's allowlist -- a
            # worker never analyzes a URL it was not authorized to see.
            if doc.source_url not in allowed:
                raise ContractError("source_document URL not in allowed_source_urls: %r"
                                    % doc.source_url)


# --------------------------------------------------------------------------- #
# Result (worker OUTPUT).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ProposedField:
    field_name: str
    state: str                        # SUPPORTED | NOT_STATED | CONTRADICTORY
    value: str = ""                   # "" unless SUPPORTED
    evidence_quote: str = ""          # "" unless SUPPORTED; verbatim in source
    source_url: str = ""              # which supplied doc supports it
    source_type: str = ""
    warnings: Tuple[str, ...] = ()

    def to_dict(self) -> Dict:
        return {
            "field_name": self.field_name, "state": self.state, "value": self.value,
            "evidence_quote": self.evidence_quote, "source_url": self.source_url,
            "source_type": self.source_type, "warnings": list(self.warnings),
        }

    @staticmethod
    def from_dict(d: Dict) -> "ProposedField":
        return ProposedField(
            field_name=str(d["field_name"]), state=str(d["state"]),
            value=str(d.get("value", "")), evidence_quote=str(d.get("evidence_quote", "")),
            source_url=str(d.get("source_url", "")), source_type=str(d.get("source_type", "")),
            warnings=tuple(str(w) for w in d.get("warnings", [])))


@dataclass(frozen=True)
class PetFeeTerm:
    """One typed pet-fee term (ATLAS-WORKERS-006). ROLE, BASIS, and SCOPE are
    DISTINCT dimensions -- never folded into a combinatorial value. ``amount`` is
    a canonical decimal string (e.g. "50.00"), never a float and never a raw
    source fragment like "$50"; the exact wording lives in ``evidence_quote``.
    Condition boundaries are typed integers (or None)."""

    role: str                                  # V.FEE_TERM_ROLES
    amount: str                                # canonical decimal string, e.g. "50.00"
    currency: str                              # canonical currency, e.g. "USD"
    basis: str                                 # V.FEE_TERM_BASES (rate unit only)
    scope: str = ""                            # V.FEE_TERM_SCOPES (independent dimension)
    condition_type: str = ""                   # V.FEE_CONDITION_TYPES
    condition_min: Optional[int] = None        # typed integer or None
    condition_max: Optional[int] = None
    boundary_unit: str = ""                    # V.BOUNDARY_UNITS or "" when unconditional
    evidence_quote: str = ""                   # verbatim substring of the cited source
    source_url: str = ""
    source_type: str = ""

    def to_dict(self) -> Dict:
        return {
            "role": self.role, "amount": self.amount, "currency": self.currency,
            "basis": self.basis, "scope": self.scope, "condition_type": self.condition_type,
            "condition_min": self.condition_min, "condition_max": self.condition_max,
            "boundary_unit": self.boundary_unit, "evidence_quote": self.evidence_quote,
            "source_url": self.source_url, "source_type": self.source_type,
        }

    @staticmethod
    def from_dict(d: Dict) -> "PetFeeTerm":
        def _int(v):
            return int(v) if isinstance(v, int) or (isinstance(v, str) and v.strip().isdigit()) else None
        return PetFeeTerm(
            role=str(d["role"]), amount=str(d["amount"]), currency=str(d.get("currency", "")),
            basis=str(d.get("basis", "")), scope=str(d.get("scope", "")),
            condition_type=str(d.get("condition_type", "")),
            condition_min=_int(d.get("condition_min")), condition_max=_int(d.get("condition_max")),
            boundary_unit=str(d.get("boundary_unit", "")),
            evidence_quote=str(d.get("evidence_quote", "")),
            source_url=str(d.get("source_url", "")), source_type=str(d.get("source_type", "")))

    def sort_key(self) -> Tuple:
        return (self.role, self.condition_min if self.condition_min is not None else -1,
                self.condition_max if self.condition_max is not None else 10 ** 9,
                self.amount, self.basis, self.scope, self.evidence_quote, self.source_url)

    def identity(self) -> Tuple:
        """Semantic identity for deduplication: role + amount + basis + scope +
        condition, INDEPENDENT of the exact quote wording (so two differently
        worded quotes for the same term deduplicate)."""
        return (self.role, self.amount, self.currency, self.basis, self.scope,
                self.condition_type, self.condition_min, self.condition_max, self.boundary_unit)


@dataclass(frozen=True)
class PetFeePolicy:
    """An ordered, deterministic set of pet-fee terms with a content identity."""

    terms: Tuple[PetFeeTerm, ...]
    fee_policy_version: str = ""

    def _sorted_terms(self) -> Tuple[PetFeeTerm, ...]:
        return tuple(sorted(self.terms, key=lambda t: t.sort_key()))

    def to_dict(self) -> Dict:
        return {
            "fee_policy_version": self.fee_policy_version,
            "terms": [t.to_dict() for t in self._sorted_terms()],
            "content_hash": self.content_hash(),
        }

    @staticmethod
    def from_dict(d: Dict) -> "PetFeePolicy":
        return PetFeePolicy(
            terms=tuple(PetFeeTerm.from_dict(t) for t in d.get("terms", [])),
            fee_policy_version=str(d.get("fee_policy_version", "")))

    def content_hash(self) -> str:
        payload = {"fee_policy_version": self.fee_policy_version,
                   "terms": [t.to_dict() for t in self._sorted_terms()]}
        return "sha256:" + _sha256(canonical_json(payload))


# Fields excluded from result_hash: the volatile provider metering/timing, and
# the hash itself. result_hash therefore identifies the RESULT CONTENT (status,
# facts, evidence, source selection, provenance) independent of how it was
# metered -- deterministic under the fake provider, stable across reruns.
_HASH_EXCLUDED = frozenset({
    "result_hash", "input_tokens", "output_tokens", "cached_input_tokens",
    "latency_ms", "attempt_count",
})


@dataclass(frozen=True)
class WorkerResult:
    assignment_id: str
    listing_key: str
    status: str
    selected_source_url: str
    selected_source_type: str
    evidence_quotes: Tuple[str, ...]
    proposed_facts: Tuple[ProposedField, ...]
    unknown_fields: Tuple[str, ...]
    contradictions: Tuple[str, ...]
    warnings: Tuple[str, ...]
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    latency_ms: int = 0
    attempt_count: int = 1
    contract_version: str = V.CONTRACT_VERSION
    worker_type: str = V.WORKER_TYPE_HOTEL_POLICY
    # ATLAS-WORKERS-006 additive structured pet-fee policy. None for a simple
    # policy (which keeps the scalar pet_fee/fee_currency/fee_basis facts); a
    # PetFeePolicy for a multi-term policy. Omitted from the content/hash when
    # None, so every prior serialized result and the committed benchmark keep
    # their exact result_hash (backward-compatible extension).
    fee_policy: Optional[PetFeePolicy] = None
    result_hash: str = ""

    def _content(self) -> Dict:
        content = {
            "assignment_id": self.assignment_id, "contract_version": self.contract_version,
            "worker_type": self.worker_type, "listing_key": self.listing_key,
            "status": self.status, "selected_source_url": self.selected_source_url,
            "selected_source_type": self.selected_source_type,
            "evidence_quotes": list(self.evidence_quotes),
            "proposed_facts": [f.to_dict() for f in self.proposed_facts],
            "unknown_fields": list(self.unknown_fields),
            "contradictions": list(self.contradictions), "warnings": list(self.warnings),
            "provider": self.provider, "model": self.model,
        }
        if self.fee_policy is not None:
            content["fee_policy"] = self.fee_policy.to_dict()
        return content

    def compute_hash(self) -> str:
        content = {k: v for k, v in self._content().items() if k not in _HASH_EXCLUDED}
        return "sha256:" + _sha256(canonical_json(content))

    def with_hash(self) -> "WorkerResult":
        from dataclasses import replace
        return replace(self, result_hash=self.compute_hash())

    def to_dict(self) -> Dict:
        d = self._content()
        d.update({
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens, "latency_ms": self.latency_ms,
            "attempt_count": self.attempt_count,
            "result_hash": self.result_hash or self.compute_hash(),
        })
        return d

    @staticmethod
    def from_dict(d: Dict) -> "WorkerResult":
        return WorkerResult(
            assignment_id=str(d["assignment_id"]),
            contract_version=str(d.get("contract_version", V.CONTRACT_VERSION)),
            worker_type=str(d.get("worker_type", V.WORKER_TYPE_HOTEL_POLICY)),
            listing_key=str(d["listing_key"]), status=str(d["status"]),
            selected_source_url=str(d.get("selected_source_url", "")),
            selected_source_type=str(d.get("selected_source_type", "")),
            evidence_quotes=tuple(str(q) for q in d.get("evidence_quotes", [])),
            proposed_facts=tuple(ProposedField.from_dict(x) for x in d.get("proposed_facts", [])),
            unknown_fields=tuple(str(f) for f in d.get("unknown_fields", [])),
            contradictions=tuple(str(c) for c in d.get("contradictions", [])),
            warnings=tuple(str(w) for w in d.get("warnings", [])),
            provider=str(d.get("provider", "")), model=str(d.get("model", "")),
            input_tokens=int(d.get("input_tokens", 0)),
            output_tokens=int(d.get("output_tokens", 0)),
            cached_input_tokens=int(d.get("cached_input_tokens", 0)),
            latency_ms=int(d.get("latency_ms", 0)),
            attempt_count=int(d.get("attempt_count", 1)),
            fee_policy=(PetFeePolicy.from_dict(d["fee_policy"]) if d.get("fee_policy") else None),
            result_hash=str(d.get("result_hash", "")))

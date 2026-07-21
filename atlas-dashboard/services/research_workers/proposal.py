"""ATLAS-WORKERS-001 -- the raw, UNTRUSTED model proposal.

A provider returns a ``ModelProposal``: the facts the model *claims*, plus real
usage/timing. Nothing here is authoritative -- the deterministic evidence
validator (services.research_workers.evidence_validator) re-derives every
SUPPORTED fact from the supplied source text before it can enter a result. Pure
data, so both the provider layer and the validator can import it without pulling
in any network code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class RawFactClaim:
    """One field the model proposes. The model may propose the SAME field from
    more than one source (that is how a genuine contradiction is surfaced); the
    validator groups by field and verifies each claim independently."""

    field_name: str
    value: str
    evidence_quote: str
    source_url: str


@dataclass(frozen=True)
class ProviderErrorDetail:
    """Sanitized record of a provider/transport failure (ATLAS-WORKERS-002).

    Built ONLY from the response side of a failed call -- HTTP status line,
    the provider's error JSON, and response headers. The request (API key,
    Authorization header, body) is never a source, so a credential or prompt
    can never enter a report through this record. ``transient`` drives the
    retry and fail-fast policy: a non-transient error is deterministic, so
    re-sending the identical request can only burn money."""

    http_status: int = 0               # 0 == no HTTP response (transport-level failure)
    error_type: str = ""               # provider error type, e.g. "invalid_request_error"
    error_code: str = ""               # provider error code, e.g. "unsupported_parameter"
    message: str = ""                  # sanitized, length-capped provider message
    request_id: str = ""               # provider request-id header when available
    transient: bool = False            # True == retry may succeed (429/5xx/transport)
    attempt_count: int = 0             # attempts consumed when this was recorded

    @property
    def signature(self) -> str:
        """Stable identity of the failure KIND, for repeated-error detection."""
        return "%s:%s:%s" % (self.http_status, self.error_type, self.error_code)

    def to_dict(self) -> Dict:
        return {
            "http_status": self.http_status, "error_type": self.error_type,
            "error_code": self.error_code, "message": self.message,
            "request_id": self.request_id, "transient": self.transient,
            "attempt_count": self.attempt_count,
        }


@dataclass(frozen=True)
class ModelProposal:
    claims: Tuple[RawFactClaim, ...] = ()
    ok: bool = True
    error: str = ""                    # reason slug when ok is False
    structured_output_valid: bool = True
    provider: str = ""
    model: str = ""
    # Real provider metering only -- the fake provider leaves these at 0; an
    # adapter captures actual usage. Never inferred from text length.
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    latency_ms: int = 0
    attempt_count: int = 1
    # Present ONLY when the provider/transport failed (the model never returned
    # a usable response). A model that responds with unparseable output leaves
    # this None -- that is a model-quality failure, not a provider failure.
    provider_error: Optional[ProviderErrorDetail] = None


def is_provider_error(proposal: ModelProposal) -> bool:
    """True when the proposal records a provider/transport failure -- the model
    never produced a usable response. False for model-quality failures such as
    unparseable output (the model DID respond). The slug prefixes cover
    proposals built before ProviderErrorDetail existed."""
    if proposal.provider_error is not None:
        return True
    return (not proposal.ok) and (proposal.error or "").startswith(
        ("provider_error:", "request_failed:"))

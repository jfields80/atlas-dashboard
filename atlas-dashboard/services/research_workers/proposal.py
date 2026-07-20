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
from typing import Tuple


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

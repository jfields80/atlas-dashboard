"""ATLAS-WORKERS-001 -- the HOTEL_POLICY_RESEARCH worker (Stage 2).

The thin orchestration that runs ONE assignment: hand the supplied documents to
a provider, then hand the untrusted proposal to the deterministic validator. The
worker never fetches, never approves, never publishes, and never writes
production data -- it only turns an assignment into a validated WorkerResult.
"""

from __future__ import annotations

from typing import Optional

from services.research_workers import vocabulary as V
from services.research_workers.contracts import Assignment, WorkerResult
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.providers import ResearchProvider


def run_assignment(
    assignment: Assignment, provider: ResearchProvider, *, model: str,
    output_token_cap: int = V.DEFAULT_OUTPUT_TOKEN_CAP,
    timeout_s: float = V.DEFAULT_TIMEOUT_SECONDS, max_retries: int = V.DEFAULT_MAX_RETRIES,
) -> WorkerResult:
    """Run one assignment end to end (extraction proposal -> deterministic
    validation). Pure with respect to the filesystem -- persistence is the
    caller's choice (WorkerRepository)."""
    assignment.validate()
    proposal = provider.propose(
        assignment, model=model, output_token_cap=output_token_cap,
        timeout_s=timeout_s, max_retries=max_retries)
    return validate_proposal(assignment, proposal, provider=provider.name, model=model)

"""The orchestrator. Chooses a lane, runs it, judges what came back.

    PROPERTY -> ROUTE -> PROVIDER -> IDENTITY -> POLICY -> EVIDENCE -> STATE

Every one of those steps already existed and was measured. What did not exist
was anything that chose between lanes, stopped escalating when escalation was
waste, counted what it spent, and survived being killed. That is this file.

WHAT THE ROUTER DECIDES AND WHAT IT DOES NOT
--------------------------------------------
It decides HOW to fetch and WHEN to stop. It decides nothing about a hotel.
``publication_grade`` is carried from the existing contract, never computed
here, and the router's own success is reported in a different field from the
contract's -- because a provider that worked and evidence that did not is an
ordinary outcome and the two words must never merge.

THE ESCALATION RULE, ONCE
-------------------------
A refusal escalates. A silence does not. ``ACCESS_DENIED`` means the channel
said no and another channel might say yes; ``POLICY_NOT_FOUND`` means the page
answered and had nothing to say about pets, and a costlier lane will find the
same nothing. ``SOURCE_CONTRADICTORY`` is the sharpest case: the property
contradicted itself, and no crawler on earth fixes that.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import budget as BUDGET        # noqa: E402
from scripts.pettripfinder.acquisition import envelope as ENV         # noqa: E402
from scripts.pettripfinder.acquisition import failures as F           # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL      # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS  # noqa: E402
from scripts.pettripfinder.acquisition import readers as READERS      # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY    # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC    # noqa: E402
from scripts.pettripfinder.brightdata import client                   # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as CAPTURE      # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG  # noqa: E402

#: Withholding reasons that mean the SOURCE, not the fetch, blocked publication.
#: Present here so the router can tell "we could not get the page" from "the
#: page said something we may not publish" without re-deriving either.
_SOURCE_BLOCKING = ("SOURCE_AMBIGUOUS", "SOURCE_CONTRADICTORY",
                    "SCHEMA_CANNOT_REPRESENT")


@dataclass(frozen=True)
class RouterConfig:
    budget: BUDGET.Budget = field(default_factory=BUDGET.Budget)
    registry_path: Optional[Path] = None
    #: Cents per gigabyte, used only to ESTIMATE a property's spend against its
    #: ceiling. Never reported as a billed figure.
    rate_usd_minor_per_gb: Optional[float] = None

    def to_dict(self) -> Dict:
        return {"budget": self.budget.to_dict(),
                "registry_path": str(self.registry_path or REGISTRY.ROUTES_PATH),
                "rate_usd_minor_per_gb": self.rate_usd_minor_per_gb}


def _estimated_cost(bytes_moved: int, rate: Optional[float]) -> float:
    if not rate or not bytes_moved:
        return 0.0
    return (bytes_moved / 1e9) * rate


def _source_failure(withheld: Mapping) -> str:
    """The source failure a reading implies, or "".

    Only fires when the reading produced NO publishable fact and the reason it
    produced none is the source. A record with a fee and one withheld basis is
    a good record with a caveat, not a source failure.
    """
    reasons = [str(v) for v in (withheld or {}).values()]
    for reason in _SOURCE_BLOCKING:
        if reason in reasons:
            return F.from_withholding(reason)
    return ""


def _seconds_by_provider(attempts: Sequence[ENV.ProviderAttempt]) -> Dict[str, float]:
    """Wall-clock per lane, so a fallback's latency is visible on its own."""
    out: Dict[str, float] = {}
    for attempt in attempts:
        out[attempt.provider] = out.get(attempt.provider, 0.0) + (
            attempt.elapsed_seconds or 0.0)
    return out


def _credits_consumed(attempts: Sequence[ENV.ProviderAttempt]) -> Optional[float]:
    """Plan credits, for lanes billed in them. Never mixed with dollars.

    Counted from SUCCESSFUL attempts only, because that is what the billing
    was observed to charge for across roughly forty calls -- an observation,
    not a guarantee, and it is recorded as a measurement of this run rather
    than as a price.
    """
    total = 0.0
    seen = False
    for attempt in attempts:
        try:
            cost = PROVIDERS.get(attempt.provider).cost_metadata()
        except PROVIDERS.ProviderError:
            continue
        if cost.credits_per_property is None:
            continue
        seen = True
        if attempt.outcome == CAPTURE.VALID:
            total += cost.credits_per_property
    return total if seen else None


def _final_state(*, document: Optional[ENV.SourceDocument],
                 failure: str) -> str:
    """Exactly one state, and never silence."""
    if document is not None:
        return (ENV.ACQUIRED_PUBLICATION_GRADE if document.is_publication_grade
                else ENV.ACQUIRED_NONPUBLICATION_GRADE)
    if failure == F.POLICY_NOT_FOUND:
        return ENV.POLICY_NOT_FOUND
    if failure in (F.IDENTITY_MISMATCH, F.IDENTITY_UNCERTAIN):
        return ENV.IDENTITY_REVIEW
    if failure == F.SOURCE_CONTRADICTORY:
        return ENV.SOURCE_CONTRADICTORY
    if failure in (F.SOURCE_AMBIGUOUS, F.UNSUPPORTED_SCHEMA_SHAPE,
                   F.UNSUPPORTED_DURATION):
        return ENV.SOURCE_AMBIGUOUS
    if failure in (F.BUDGET_EXHAUSTED, F.ATTEMPTS_EXHAUSTED):
        return ENV.BUDGET_EXHAUSTED
    if failure == F.POLICY_SURFACE_INCOMPLETE:
        return ENV.POLICY_NOT_FOUND
    return ENV.TECHNICAL_FALLBACK_REQUIRED


async def route_property(record, target, *, run_dir: Path, run_id: str,
                         config: Optional[RouterConfig] = None,
                         registry: Optional[Mapping] = None,
                         route_url: str = "") -> ENV.RoutingResult:
    """Acquire one property through its resolved lane, with escalation.

    ``record`` is a corpus benchmark row (identity and brand); ``target`` is the
    capture target built from it. Neither carries a policy value -- the
    structural guarantee the pilots established is unchanged here.

    ``route_url`` names the URL the LANE is resolved from, and defaults to the
    one being fetched, which is what every caller before source resolution
    existed meant. A caller that reads a different page of the same property --
    a discovered policy URL instead of the census homepage -- passes the census
    URL here, so choosing a better page cannot silently move the property to
    another provider: ``registry.resolve`` keys on the URL's host, and those are
    two separate decisions.
    """
    config = config or RouterConfig()
    route = REGISTRY.resolve(brand=record.brand,
                             url=route_url or target.requested_url,
                             identity_key=record.identity_key,
                             registry=registry)
    ledger = BUDGET.BudgetLedger(budget=config.budget)
    attempts: List[ENV.ProviderAttempt] = []
    tried: List[str] = []
    failure = ""
    stopped_because = ""
    document: Optional[ENV.SourceDocument] = None
    began = time.monotonic()

    for provider_id in route.ladder:
        exhausted = ledger.exhausted()
        if exhausted:
            failure = F.BUDGET_EXHAUSTED
            stopped_because = "budget: %s" % exhausted
            break

        allowance = min(ledger.attempts_for_next_provider(),
                        route.max_attempts_per_provider)
        if allowance <= 0:
            failure = F.ATTEMPTS_EXHAUSTED
            stopped_because = "no attempts left within the total budget"
            break

        provider = PROVIDERS.get(provider_id)
        health = provider.health_check()
        tried.append(provider_id)
        if not health.available:
            attempts.append(ENV.ProviderAttempt(
                provider=provider_id, provider_product=provider.product,
                attempt=0, outcome="PROVIDER_UNAVAILABLE",
                failure=F.PROVIDER_UNAVAILABLE, detail=health.detail))
            failure = F.PROVIDER_UNAVAILABLE
            continue

        records, payload = await provider.acquire(
            target, run_dir=run_dir, reader_id=route.reader,
            max_attempts=allowance)

        moved = 0
        for capture in records:
            estimated = int((capture.network or {}).get("encoded_bytes") or 0)
            moved += estimated
            attempts.append(ENV.ProviderAttempt(
                provider=provider_id, provider_product=provider.product,
                attempt=capture.attempt, outcome=capture.outcome,
                failure=("" if capture.outcome == CAPTURE.VALID
                         else F.from_capture_outcome(capture.outcome)),
                started_at=capture.started_at, ended_at=capture.ended_at,
                elapsed_seconds=capture.elapsed_seconds,
                final_url=capture.final_url, title=capture.title,
                body_chars=capture.body_chars, detail=capture.detail,
                estimated_bytes=estimated,
                interactions=tuple(capture.interactions)))
        ledger.record(attempts=len(records),
                      elapsed_seconds=sum(r.elapsed_seconds for r in records),
                      estimated_usd_minor=_estimated_cost(
                          moved, config.rate_usd_minor_per_gb))

        successful = next((r for r in records if r.outcome == CAPTURE.VALID),
                          None)
        if successful is None:
            failure = F.from_capture_outcome(records[-1].outcome)
            if not F.may_escalate(failure):
                stopped_because = (
                    "%s is terminal: the surface answered and a different "
                    "provider would receive the same answer" % failure)
                break
            continue

        document, source_failure = _build_document(
            record=record, target=target, attempt=successful, payload=payload,
            provider=provider, route=route, run_id=run_id)
        if source_failure:
            # The page arrived and the property said something unpublishable.
            # This is not a fetch problem and must not become one.
            failure = source_failure
            stopped_because = (
                "%s is terminal: a better crawler cannot resolve what the "
                "source itself left unclear" % source_failure)
        break
    else:
        if not failure:
            failure = F.PROVIDER_EXHAUSTED
            stopped_because = "every permitted provider was tried"

    if document is None and failure and F.may_escalate(failure) \
            and not stopped_because:
        stopped_because = "every permitted provider was tried"

    state = _final_state(document=document, failure=failure)
    if document is None and state == ENV.TECHNICAL_FALLBACK_REQUIRED \
            and len(tried) > 1:
        state = ENV.PROVIDER_EXHAUSTED

    return ENV.RoutingResult(
        identity_key=record.identity_key, hotel=record.name,
        brand=record.brand, requested_url=target.requested_url,
        state=state, route=route.to_dict(), attempts=tuple(attempts),
        providers_tried=tuple(tried), failure=failure,
        failure_class=F.classify(failure) if failure else "",
        escalation_stopped_because=stopped_because, document=document,
        cost=ENV.AcquisitionCost(
            attempts=ledger.attempts,
            failed_attempts=sum(1 for a in attempts
                                if a.outcome != CAPTURE.VALID),
            elapsed_seconds=time.monotonic() - began,
            estimated_bytes=sum(a.estimated_bytes for a in attempts),
            estimated_usd_minor=(ledger.estimated_usd_minor
                                 if config.rate_usd_minor_per_gb else None),
            reported_credits=_credits_consumed(attempts),
            seconds_by_provider=_seconds_by_provider(attempts),
            # The ladder moved past its primary. Recorded as a fact rather
            # than inferred later from the length of providers_tried, which
            # also grows when a provider is merely unhealthy.
            fallback_invoked=len([p for p in tried if p != route.provider]) > 0,
            cost_status=("ESTIMATED" if config.rate_usd_minor_per_gb
                         else "UNAVAILABLE")),
        run_id=run_id)


def _build_document(*, record, target, attempt, payload, provider, route,
                    run_id) -> Tuple[Optional[ENV.SourceDocument], str]:
    """Turn a successful capture into the normalised envelope.

    Reuses the pilot's observation builder, contract evaluation and
    publication-grade assessment verbatim -- the router adds routing, not a
    second interpretation.
    """
    reader = READERS.get(route.reader)
    observation, result = P2.build_observation(
        record, target, attempt, payload, run_id=run_id)
    capture_method = ("deterministic_fetch"
                      if PROVIDERS.BYPASSES_BOT_PROTECTION in provider.capabilities
                      and PROVIDERS.RUNS_JAVASCRIPT not in provider.capabilities
                      else PG.CAPTURE_METHOD)
    observation["capture_method"] = capture_method

    contracts = P2.evaluate_contracts(observation, [attempt])
    artifacts = payload["artifacts"]
    files = artifacts.get("files") or {}
    html_entry = files.get(PG.PRIMARY_ARTIFACT) or {}
    grade = PG.assess(
        evidence_items=observation["evidence"],
        extraction=observation["extraction"],
        source_url=observation["source_url"],
        captured_at=attempt.started_at,
        ref_prefix="%s::%s" % (run_id, record.identity_key),
        artifact_path=P2._artifact_path(artifacts, PG.PRIMARY_ARTIFACT),
        recorded_sha256=str(html_entry.get("sha256") or ""),
        page_text_path=P2._artifact_path(artifacts, "page-text.txt"),
        identity_confirmed=bool((attempt.identity or {}).get("confirmed")))

    surface = payload["surface"]
    document = ENV.SourceDocument(
        identity_key=record.identity_key, brand=record.brand,
        source_url=target.requested_url, final_url=attempt.final_url,
        provider=provider.provider_id, provider_product=provider.product,
        reader=reader.reader_id, capture_method=capture_method,
        fetched_at=attempt.started_at, status=CAPTURE.VALID,
        policy_text=payload["reading"].block_text,
        policy_locator=getattr(surface, "strategy", ""),
        rendered=bool(getattr(surface, "rendered", True)),
        rendered_html_path=str(html_entry.get("path") or ""),
        text_path=str((files.get("page-text.txt") or {}).get("path") or ""),
        screenshot_path=str((files.get("policy-section.png") or {}).get("path")
                            or ""),
        content_hash=str(html_entry.get("sha256") or ""),
        artifacts=artifacts, identity=(attempt.identity or {}),
        observation=observation, withheld_fields=dict(result.withheld),
        non_inferences=tuple(result.non_inferences),
        publication_grade=grade.to_dict(), contracts=contracts)

    source_failure = ""
    if not observation["extraction"]:
        source_failure = _source_failure(result.withheld)
    return document, source_failure


__all__ = ["RouterConfig", "route_property"]

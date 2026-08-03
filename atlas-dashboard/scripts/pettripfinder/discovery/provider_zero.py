"""PTF-DISCOVERY-001 WO-1A -- the Provider Zero checkpoint.

Provider Zero is a **configuration of the existing discovery engine**, not a
new build. It runs the whole governance chain over candidates already on disk:

  * **cache-only** -- reads committed/gitignored artifacts only;
  * **zero network calls** -- no provider client is constructed, and the robots
    gate is invoked with no fetcher, which has no code path to a socket;
  * **zero spend**;
  * **no new provider**;
  * **no modification of verified policy facts** -- nothing here writes the
    seed, the launch package, an approval, or a promotion;
  * **no automatic approval, promotion, assembly or deployment.**

It answers one question honestly: *does this pipeline produce a verification
queue that saves real manual effort, without letting a discovery attribute
cross the Membrane?* -- including when the answer is "fewer than you'd hope".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import idempotency, lifecycle, robots
from scripts.pettripfinder.discovery import terms_registry as TR
from scripts.pettripfinder.discovery import url_record as U
from scripts.pettripfinder.discovery.history import merge_history_ref, merge_record_for
from scripts.pettripfinder.discovery.models import DiscoveryCandidate
from scripts.pettripfinder.discovery.queue_seam import (
    PROJECTED, PROJECTED_PENDING_IDENTITY, SEAM_OUTCOMES_WITH_ENTRY,
    build_queue_payload, entries_with_identity, project_candidate, summarize,
)
from scripts.pettripfinder.discovery.run_context import DiscoveryRunContext
from scripts.pettripfinder.discovery.serialization import candidate_from_dict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = REPO_ROOT / "data" / "discovery" / "columbus_wave1_lodging"


# --------------------------------------------------------------------------- #
# Cache-only inputs.
# --------------------------------------------------------------------------- #

def load_candidates(root: Path = None) -> Tuple[DiscoveryCandidate, ...]:
    """Every deduplicated candidate already on disk. Read-only."""
    base = Path(root) if root else DEFAULT_ROOT
    out: List[DiscoveryCandidate] = []
    for category in ("hotel", "motel"):
        path = base / category / "candidates" / "columbus-oh_candidates.json"
        if not path.exists():
            continue
        for raw in json.loads(path.read_text(encoding="utf-8")):
            out.append(candidate_from_dict(raw))
    return tuple(sorted(out, key=lambda c: c.candidate_id))


def load_resolutions(root: Path = None) -> Dict[str, dict]:
    base = Path(root) if root else DEFAULT_ROOT
    path = base / "resolution" / "resolved_candidates.json"
    if not path.exists():
        return {}
    return {r["candidate_id"]: r for r in json.loads(path.read_text(encoding="utf-8"))}


def load_fetch_cache(root: Path = None) -> Dict[str, dict]:
    """URL -> the identity snapshot actually fetched during AES-DATA-004C.

    This is the ONLY source of a real validation date. A URL absent from here
    was never fetched, which is exactly what FD-5 must act on.
    """
    base = Path(root) if root else DEFAULT_ROOT
    cache_dir = base / "resolution" / "resolution_cache"
    out: Dict[str, dict] = {}
    if not cache_dir.exists():
        return out
    for path in sorted(cache_dir.glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry.get("url"):
            out[entry["url"]] = entry
    return out


# --------------------------------------------------------------------------- #
# Per-candidate governance.
# --------------------------------------------------------------------------- #

def build_url_record(resolved_url: str, cache: Dict[str, dict],
                     *, is_confirmed: bool) -> U.OfficialUrlRecord:
    """Project the cached fetch evidence (if any) into an OfficialUrlRecord.

    A URL that was never fetched gets ``last_validated_at=""`` and
    ``property_identity_check=UNCHECKED`` -- stated plainly rather than
    optimistically defaulted, because an unfetched URL genuinely has not been
    shown to point at the property we think it does.
    """
    entry = cache.get(resolved_url)
    if entry is None:
        return U.OfficialUrlRecord(
            url=resolved_url, status=C.WEBSITE_RES_PROPERTY_URL_PROBABLE,
            last_validated_at="", property_identity_check=U.IDENTITY_UNCHECKED,
            identity_explanation="url was never fetched; static classification only")

    chain = entry.get("redirect_chain") or []
    hops = tuple(U.RedirectHop(from_url=chain[i - 1] if i else entry.get("url", ""),
                               to_url=chain[i]) for i in range(len(chain)))
    canonical = entry.get("canonical_url") or entry.get("final_url") or ""

    if is_confirmed:
        check, why = U.same_property_identity(U.IdentityKeyAgreement(
            agreeing_keys=(U.KEY_NORMALIZED_STREET_ADDRESS,
                           U.KEY_STABLE_CHAIN_IDENTIFIER)))
        status = C.WEBSITE_RES_PROPERTY_URL_CONFIRMED
    else:
        check, why = U.same_property_identity(U.IdentityKeyAgreement(
            non_identity_signals_seen=("name", "page_title")))
        status = C.WEBSITE_RES_PROPERTY_URL_PROBABLE

    return U.OfficialUrlRecord(
        url=resolved_url, status=status,
        last_validated_at=entry.get("retrieved_at", ""),
        redirect_history=hops, canonical_destination=canonical,
        property_identity_check=check, identity_explanation=why)


@dataclass
class CheckpointReport:
    run_id: str = ""
    effective_time: str = ""
    candidates_loaded: int = 0
    resolutions_loaded: int = 0
    provider_records: int = 0
    duplicates_prevented: int = 0
    merge_records: int = 0
    identity_conflicts: int = 0
    identity_outcomes: Dict[str, int] = field(default_factory=dict)
    resolution_outcomes: Dict[str, int] = field(default_factory=dict)
    lifecycle: Dict[str, int] = field(default_factory=dict)
    url_decisions: Dict[str, int] = field(default_factory=dict)
    urls_blocked_by_revalidation: int = 0
    urls_never_fetched: int = 0
    robots: Dict[str, int] = field(default_factory=dict)
    robots_hosts: int = 0
    seam: Dict[str, int] = field(default_factory=dict)
    queued: int = 0
    #: C-5. Provisional entries: eligible, adapter-supported, and awaiting
    #: capture-session identity proof. Counted SEPARATELY from ``queued`` --
    #: folding them together would report unproven work as ready work, which
    #: is the exact illusion the Provider Zero checkpoint exists to catch.
    queued_pending_identity: int = 0
    #: Entries actually written to the payload, after collapsing repeats of the
    #: same idempotency key and withholding hotel_id collisions.
    entries_emitted: int = 0
    #: Distinct candidates whose names slugify to one ``hotel_id``. Withheld
    #: rather than merged: a queue cannot carry two entries under one id, and
    #: merging two properties on a name match is the false-merge FD-5 forbids.
    withheld_hotel_id_collisions: Tuple[str, ...] = ()
    activation: Dict[str, list] = field(default_factory=dict)
    terms: Dict[str, int] = field(default_factory=dict)
    membrane_violations: int = 0
    network_calls: int = 0
    spend_usd: float = 0.0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def run_checkpoint(*, run_id: str, effective_time: str,
                   root: Path = None) -> Tuple[CheckpointReport, dict, List]:
    """Execute Provider Zero. Returns ``(report, queue_payload, seam_results)``.

    Makes zero network calls: no provider client is built, and every robots
    check runs with ``robots_fetcher=None``.
    """
    context = DiscoveryRunContext(run_id=run_id, effective_time=effective_time)
    candidates = load_candidates(root)
    resolutions = load_resolutions(root)
    fetch_cache = load_fetch_cache(root)

    report = CheckpointReport(run_id=run_id, effective_time=effective_time,
                              candidates_loaded=len(candidates),
                              resolutions_loaded=len(resolutions))

    # --- dedup / merge accounting (from what dedup ALREADY decided) -------- #
    provider_records = sum(len(c.source_records) for c in candidates)
    report.provider_records = provider_records
    report.duplicates_prevented = provider_records - len(candidates)
    merge_records = [m for m in (merge_record_for(c, run_id=run_id) for c in candidates)
                     if m is not None]
    report.merge_records = len(merge_records)
    report.identity_conflicts = sum(1 for c in candidates if c.conflict_flags)

    for r in resolutions.values():
        key = r.get("identity_outcome") or "(none)"
        report.identity_outcomes[key] = report.identity_outcomes.get(key, 0) + 1
        okey = r.get("resolution_outcome") or "(none)"
        report.resolution_outcomes[okey] = report.resolution_outcomes.get(okey, 0) + 1

    # --- terms registry ---------------------------------------------------- #
    registry = TR.load_registry()
    report.terms = TR.summarize(registry)
    # Provider Zero is permitted precisely because it makes no third-party call.
    TR.assert_live_use_permitted(TR.PROVIDER_ZERO, registry=registry,
                                 as_of=effective_time)

    # --- per-candidate chain ---------------------------------------------- #
    robots_cache = robots.RobotsCache()
    robots_decisions = []
    url_decisions = []
    seam_results = []
    seen_hosts = set()

    for candidate in candidates:
        resolved = resolutions.get(candidate.candidate_id, {})
        outcome = resolved.get("resolution_outcome", "")
        resolved_url = resolved.get("resolved_url", "") or ""
        identity_outcome = resolved.get("identity_outcome", "") or ""
        is_confirmed = bool(resolved.get("is_confirmed"))

        proposal = lifecycle.propose_lifecycle(
            candidate, is_published=False, identity_outcome=identity_outcome)
        report.lifecycle[proposal.proposed_state] = \
            report.lifecycle.get(proposal.proposed_state, 0) + 1

        url_rec = None
        blocked = False
        block_reason = ""
        never_validated = False
        if resolved_url:
            url_rec = build_url_record(resolved_url, fetch_cache,
                                       is_confirmed=is_confirmed)
            if not url_rec.last_validated_at:
                report.urls_never_fetched += 1
            decision = U.evaluate_handoff(
                url_rec, as_of=effective_time,
                rebrand_or_rename_proposed=(identity_outcome == C.IDENTITY_POSSIBLE_REBRAND),
                identity_conflict=bool(candidate.conflict_flags))
            url_decisions.append(decision)
            blocked = not decision.allowed
            block_reason = decision.reason
            # C-5. "Never validated" and "validated and REFUTED" are different
            # facts. Only the first may become a provisional entry for the
            # capture session to prove; a FAILED identity check stays blocked,
            # so the two URLs that actually failed at the checkpoint remain
            # exactly as blocked as they were.
            never_validated = (
                blocked
                and url_rec.property_identity_check != U.IDENTITY_FAIL
                and U.TRIGGER_NEVER_VALIDATED in decision.triggers)
            if blocked:
                report.urls_blocked_by_revalidation += 1

            # Robots is evaluated for the DISCOVERY fetch path. Provider Zero
            # performs no fetch, so this demonstrates the fail-closed posture
            # rather than gating the queue.
            host = resolved_url.split("/")[2] if "://" in resolved_url else ""
            if host and host not in seen_hosts:
                seen_hosts.add(host)
                robots_decisions.append(
                    robots.check_url(resolved_url, cache=robots_cache,
                                     robots_fetcher=None, as_of=effective_time))

        seam_results.append(project_candidate(
            candidate,
            resolution_outcome=outcome,
            resolved_url=resolved_url,
            url_confirmed=is_confirmed,
            identity_confidence=candidate.review_state,
            run_context_ref=context.ref(),
            official_url_record=url_rec.to_dict() if url_rec else None,
            url_revalidation_blocked=blocked,
            revalidation_reason=block_reason,
            url_identity_never_validated=never_validated))

    report.seam = summarize(seam_results)
    report.queued = report.seam.get(PROJECTED, 0)
    report.queued_pending_identity = report.seam.get(PROJECTED_PENDING_IDENTITY, 0)
    emittable, withheld = entries_with_identity(seam_results)
    report.entries_emitted = len(emittable)
    report.withheld_hotel_id_collisions = tuple(
        "%s:%s" % (hotel_id, ",".join(cands)) for hotel_id, cands in withheld)
    report.url_decisions = U.summarize_decisions(url_decisions)
    report.robots = robots.summarize_decisions(robots_decisions)
    report.robots_hosts = len(seen_hosts)

    # Both kinds are ACTIVE queue entries, so both take part in idempotency:
    # a re-run must supersede a provisional entry in place, never append a
    # second one for the same candidate.
    projected = [r for r in seam_results
                 if r.outcome in SEAM_OUTCOMES_WITH_ENTRY and r.entry]
    plan = idempotency.plan_activation({}, [
        (r.entry.candidate_id, r.entry.worker_contract_version, r.entry.queue_entry_id)
        for r in projected])
    report.activation = plan.to_dict()

    payload = build_queue_payload(seam_results, batch_id="provider-zero-001",
                                 created_at=effective_time)
    return (report, payload, seam_results)

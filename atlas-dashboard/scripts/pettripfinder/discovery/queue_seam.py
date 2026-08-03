"""PTF-DISCOVERY-001 WO-1A Step 4 -- the discovery -> verification-queue seam.

ONE file, additive, exactly as base architecture §U prescribes: discovery stops
at VERIFICATION_QUEUED and hands the existing policy worker a queue entry it
consumes with **zero** change to the approved evidence, routing, approval or
publication contracts.

Three rules this module exists to enforce:

1. **The real preflight decides.** Every projected entry is handed to
   ``capture_automation.queue.validate_entry`` -- the same function the
   hand-authored path uses. There is deliberately no second, looser definition
   of "valid queue entry" living here. (``build_capture_queue.py`` states the
   same rule for the seed-driven path; this is the discovery-driven twin.)

2. **Borrow, never re-derive.** ``hotel_id`` comes from
   ``build_capture_queue.hotel_id_for`` and ``listing_key`` from
   ``site_data.normalize_name`` -- the function that keys the published launch
   package. A second normalizer here would silently fork identity.

3. **Only genuinely ready candidates project.** Only
   ``RESOLUTION_READY_FOR_PET_POLICY_IMPORT`` and
   ``RESOLUTION_READY_WITH_BRAND_SUPPLEMENT`` are eligible
   (``constants.RESOLUTION_ELIGIBLE_FOR_BATCH``). Everything else stays in the
   review/exception path where a human can see it.

The Membrane applies here as everywhere: a projected entry carries identity,
URL, adapter and provenance, and no pet-policy field. ``required_fields`` names
the policy fields the worker should go LOOK FOR; it carries no policy value.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.membrane import assert_no_policy_keys
from scripts.pettripfinder.discovery.models import DiscoveryCandidate

# The worker owns its contract version; discovery reads it (FD-3 rule 2).
from services.research_workers import vocabulary as V
from services.research_workers.capture_automation.adapters import adapter_for, known_brands
from services.research_workers.capture_automation.queue import (
    QUEUE_SCHEMA, QueueEntry, validate_entry,
)

# Reuse the seed path's identity helpers rather than re-deriving them.
from scripts.pettripfinder.build_capture_queue import brand_for_url, hotel_id_for
from scripts.pettripfinder.site_data import normalize_name


# --------------------------------------------------------------------------- #
# Outcomes.
# --------------------------------------------------------------------------- #

PROJECTED = "PROJECTED"                       # became a valid queue entry
SKIPPED_NOT_READY = "SKIPPED_NOT_READY"       # resolution outcome not eligible
SKIPPED_NO_URL = "SKIPPED_NO_URL"             # no usable official property URL
SKIPPED_UNSUPPORTED_BRAND = "SKIPPED_UNSUPPORTED_BRAND"   # exception list (FD-8)
SKIPPED_URL_REVALIDATION = "SKIPPED_URL_REVALIDATION"     # FD-5 identity check failed
REJECTED_BY_PREFLIGHT = "REJECTED_BY_PREFLIGHT"           # real validate_entry said no

SEAM_OUTCOMES = frozenset({
    PROJECTED, SKIPPED_NOT_READY, SKIPPED_NO_URL, SKIPPED_UNSUPPORTED_BRAND,
    SKIPPED_URL_REVALIDATION, REJECTED_BY_PREFLIGHT,
})


@dataclass(frozen=True)
class SeamResult:
    """What happened to one candidate at the seam. Never a silent skip."""
    candidate_id: str
    outcome: str
    entry: Optional[QueueEntry] = None
    problems: Tuple[str, ...] = ()
    reason: str = ""


def queue_entry_id_for(candidate_id: str, worker_contract_version: str) -> str:
    """Deterministic id over the idempotency key
    ``(candidate_id, worker_contract_version)`` -- so a re-run under the same
    contract reproduces the same entry id (and therefore supersedes rather
    than duplicates), while a contract bump legitimately yields a new one."""
    digest = hashlib.sha256(
        ("%s|%s" % (candidate_id, worker_contract_version)).encode("utf-8")).hexdigest()
    return "qe_" + digest[:16]


def _priority(candidate: DiscoveryCandidate, *, brand: str, confirmed: bool) -> Tuple[int, Tuple[str, ...]]:
    """Deterministic, explainable, and subordinate to safety (base §M).

    Commercial value never decides WHETHER something is verified -- this only
    orders candidates that have already cleared the eligibility gate. Lower
    number sorts first.
    """
    reasons: List[str] = []
    score = 100
    if confirmed:
        score -= 40
        reasons.append("official_url_confirmed")
    if brand and adapter_for(brand) is not None:
        score -= 30
        reasons.append("supported_adapter:%s" % brand)
    if candidate.review_state == C.REVIEW_STATE_AUTO_MERGED:
        score -= 10
        reasons.append("corroborated_by_multiple_providers")
    if candidate.postal_code and _phone_for(candidate):
        score -= 10
        reasons.append("complete_address_and_phone")
    if candidate.conflict_flags:
        score += 25
        reasons.append("identity_conflict_flagged")
    return (score, tuple(reasons))


def _phone_for(candidate: DiscoveryCandidate) -> str:
    for record in candidate.source_records:
        if (record.phone or "").strip():
            return record.phone.strip()
    return ""


def _provenance_refs(candidate: DiscoveryCandidate, run_context_ref: str) -> Tuple[str, ...]:
    refs = {"provider:%s:%s" % (p, rid) for p, rid in candidate.provider_ids if rid}
    refs |= {"query:%s" % r.source_query_id for r in candidate.source_records if r.source_query_id}
    if run_context_ref:
        refs.add("run:%s" % run_context_ref)
    return tuple(sorted(refs))


def project_candidate(
    candidate: DiscoveryCandidate,
    *,
    resolution_outcome: str,
    resolved_url: str,
    url_confirmed: bool = False,
    identity_confidence: str = "",
    run_context_ref: str = "",
    official_url_record: Optional[dict] = None,
    worker_contract_version: str = "",
    url_revalidation_blocked: bool = False,
    revalidation_reason: str = "",
) -> SeamResult:
    """Project ONE candidate onto a queue entry, or explain why it did not.

    Every rejection is a structured outcome; nothing is dropped silently.
    """
    contract_version = worker_contract_version or V.CONTRACT_VERSION

    if resolution_outcome not in C.RESOLUTION_ELIGIBLE_FOR_BATCH:
        return SeamResult(candidate.candidate_id, SKIPPED_NOT_READY,
                          reason=resolution_outcome or "no_resolution_outcome")

    # FD-5: a redirect resolving to a different property identity BLOCKS the
    # handoff. Checked before anything else that could make the entry look
    # legitimate.
    if url_revalidation_blocked:
        return SeamResult(candidate.candidate_id, SKIPPED_URL_REVALIDATION,
                          reason=revalidation_reason or "property_identity_check_failed")

    url = (resolved_url or "").strip()
    if not url:
        return SeamResult(candidate.candidate_id, SKIPPED_NO_URL, reason="no_resolved_url")

    brand = brand_for_url(url)
    if not brand or adapter_for(brand) is None:
        # FD-8 ratified: unsupported brands route through the existing
        # exception-list mechanism, never into the auto-queue.
        return SeamResult(candidate.candidate_id, SKIPPED_UNSUPPORTED_BRAND,
                          reason=brand or "no_recognized_brand_domain")

    priority, priority_reasons = _priority(candidate, brand=brand, confirmed=url_confirmed)

    raw = {
        "hotel_id": hotel_id_for(candidate.name),
        "listing_key": normalize_name(candidate.name),
        "hotel_name": candidate.name,
        "brand": brand,
        "official_url": url,
        "expected_address": candidate.address_line,
        "expected_city": candidate.city,
        "expected_state": candidate.state,
        "expected_postal_code": candidate.postal_code,
        "expected_phone": _phone_for(candidate),
        "required_fields": list(V.POLICY_FIELDS),
        "worker_contract_version": contract_version,
        "queue_entry_id": queue_entry_id_for(candidate.candidate_id, contract_version),
        "candidate_id": candidate.candidate_id,
        "market_id": candidate.market_id,
        "supported_adapter": brand,
        "queue_priority": priority,
        "priority_reasons": list(priority_reasons),
        "identity_confidence": identity_confidence or candidate.review_state,
        "discovery_provenance_refs": list(_provenance_refs(candidate, run_context_ref)),
        "run_context_ref": run_context_ref,
        "official_url_record": official_url_record,
        "notes": "projected from discovery candidate %s" % candidate.candidate_id,
    }

    # Membrane gate before the entry can exist at all.
    assert_no_policy_keys(raw, context="projected queue entry")

    # THE real preflight -- no second definition of validity here.
    entry, problems = validate_entry(raw, 0, known_brands=known_brands())
    if entry is None:
        return SeamResult(candidate.candidate_id, REJECTED_BY_PREFLIGHT,
                          problems=tuple(problems))
    return SeamResult(candidate.candidate_id, PROJECTED, entry=entry)


def build_queue_payload(results: Sequence[SeamResult], *, batch_id: str,
                        created_at: str = "") -> dict:
    """Assemble projected entries into a loadable queue file payload.

    Ordering is by ``queue_priority`` then ``hotel_id`` -- deterministic, and
    explainable from ``priority_reasons`` on every entry.
    """
    entries = [r.entry for r in results if r.outcome == PROJECTED and r.entry is not None]
    entries.sort(key=lambda e: (e.queue_priority, e.hotel_id))
    return {
        "schema": QUEUE_SCHEMA,
        "batch_id": batch_id,
        "created_at": created_at,
        "hotels": [e.to_dict() for e in entries],
    }


def summarize(results: Sequence[SeamResult]) -> Dict[str, int]:
    counts = {outcome: 0 for outcome in sorted(SEAM_OUTCOMES)}
    for r in results:
        counts[r.outcome] = counts.get(r.outcome, 0) + 1
    return counts

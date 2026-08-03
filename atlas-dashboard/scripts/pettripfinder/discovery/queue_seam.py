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
from services.research_workers.source_retrieval import extract_property_code_from_url
from services.research_workers.capture_automation.queue import (
    CAPTURE_STATE_PENDING_IDENTITY, CAPTURE_STATE_READY, QUEUE_SCHEMA, QueueEntry,
    is_provisional, validate_entry,
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
SKIPPED_URL_REVALIDATION = "SKIPPED_URL_REVALIDATION"     # FD-5 identity check FAILED
REJECTED_BY_PREFLIGHT = "REJECTED_BY_PREFLIGHT"           # real validate_entry said no

#: C-5. Eligible, adapter-supported, and NOT statically identity-confirmed --
#: emitted as a PROVISIONAL entry so the rendered capture session can prove
#: identity on hosts the static fetcher cannot reach (reval-001 measured 5
#: robots denials and 2 HTTP 403s across the major chains).
#:
#: This is NOT a relaxation of FD-5. FD-5 blocks a handoff whose URL resolves to
#: a DIFFERENT property; that case still returns SKIPPED_URL_REVALIDATION and
#: never becomes an entry. What changes is the separate case of an identity that
#: was never *checked* -- 251 of the 253 blocked candidates at the Provider Zero
#: checkpoint -- which is deferred to the capture session rather than discarded.
#: The proof requirement is unchanged; only the place it is discharged moves.
PROJECTED_PENDING_IDENTITY = "PROJECTED_PENDING_IDENTITY"

SEAM_OUTCOMES = frozenset({
    PROJECTED, PROJECTED_PENDING_IDENTITY, SKIPPED_NOT_READY, SKIPPED_NO_URL,
    SKIPPED_UNSUPPORTED_BRAND, SKIPPED_URL_REVALIDATION, REJECTED_BY_PREFLIGHT,
})

#: Outcomes that produce a queue entry. Provisional entries are included --
#: they are real work for the capture runner -- which is exactly why they must
#: be structurally distinguishable, never merely annotated.
SEAM_OUTCOMES_WITH_ENTRY = frozenset({PROJECTED, PROJECTED_PENDING_IDENTITY})


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


def _property_code_for(candidate: DiscoveryCandidate, url: str) -> str:
    """The stable chain property code, or "" when the URL does not carry one.

    Deliberately thin. Every guarantee comes from
    ``source_retrieval.extract_property_code_from_url``, which fails closed and
    was itself hardened against two real defects found on live captures (a
    locale segment letting the pattern match the wrong slug, and a bare
    substring match confusing Marriott's "cmhap" with Hilton's "cmhaphx").
    Re-deriving that logic here would be a second definition of "property
    code" -- exactly the fork this seam avoids everywhere else.

    No brand special-casing: a shape that carries no code simply returns "",
    and the candidate keeps confirming on address + phone.
    """
    return extract_property_code_from_url(url or "")


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
    url_identity_never_validated: bool = False,
) -> SeamResult:
    """Project ONE candidate onto a queue entry, or explain why it did not.

    Every rejection is a structured outcome; nothing is dropped silently.

    ``url_revalidation_blocked`` still BLOCKS by default. C-5 adds one narrow
    exception, and it is opt-in for a reason: the caller must state positively
    that identity was never *checked*, via ``url_identity_never_validated``.

      * blocked, nothing else said        -> SKIPPED_URL_REVALIDATION (as before)
      * blocked + never validated         -> PROJECTED_PENDING_IDENTITY
      * blocked because identity FAILED   -> SKIPPED_URL_REVALIDATION

    Defaulting the other way would have been a fail-OPEN default: every
    existing caller signalling a genuine identity failure would silently start
    producing provisional entries. An unchecked identity and a refuted one look
    identical in a boolean, so the permissive path has to be asked for.
    """
    contract_version = worker_contract_version or V.CONTRACT_VERSION

    if resolution_outcome not in C.RESOLUTION_ELIGIBLE_FOR_BATCH:
        return SeamResult(candidate.candidate_id, SKIPPED_NOT_READY,
                          reason=resolution_outcome or "no_resolution_outcome")

    # FD-5, unchanged: a URL that is not cleared for handoff BLOCKS, and a
    # redirect resolving to a DIFFERENT property blocks unconditionally.
    # Checked before anything else that could make the entry look legitimate.
    if url_revalidation_blocked and not url_identity_never_validated:
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

    # C-5. Provisional when identity was never established statically.
    provisional = bool(url_revalidation_blocked and url_identity_never_validated)
    if provisional:
        priority_reasons = priority_reasons + ("identity_unconfirmed_pending_capture",)

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
        # Stable chain property code, when the official URL already carries one
        # deterministically. Reuses source_retrieval.extract_property_code_from_url
        # -- the SAME extractor build_capture_queue.py uses for the seed path, so
        # the two paths cannot disagree about what a code is.
        #
        # It fails CLOSED by construction: anything not recognisably a code
        # returns "", so nothing is inferred where none exists. Wyndham URLs
        # carry no code segment and correctly stay empty; that is a supported
        # shape, not a defect, and those properties still confirm on
        # address + phone exactly as the pilot measured (2/2 wyndham confirmed).
        #
        # This is added for DETECTION STRENGTH, not coverage. The pilot showed
        # address+phone already confirms 10/10, so the code adds no yield. What
        # it adds is the one signal that catches a silent redirect to a SIBLING
        # property: a sibling publishes its own valid address and phone, so both
        # keys would agree with the wrong hotel. A mismatched code is the only
        # thing that turns that into IDENTITY_FAILED.
        "expected_property_code": _property_code_for(candidate, url),
        # A provisional entry asks for NO policy fields. It is a request to
        # prove identity, not to extract policy, and the empty list is what
        # makes that structurally true rather than merely stated.
        "required_fields": [] if provisional else list(V.POLICY_FIELDS),
        "capture_state": (CAPTURE_STATE_PENDING_IDENTITY if provisional
                          else CAPTURE_STATE_READY),
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
        "notes": ("projected from discovery candidate %s%s"
                  % (candidate.candidate_id,
                     "; identity pending capture-session proof" if provisional else "")),
    }

    # Membrane gate before the entry can exist at all.
    assert_no_policy_keys(raw, context="projected queue entry")

    # THE real preflight -- no second definition of validity here.
    entry, problems = validate_entry(raw, 0, known_brands=known_brands())
    if entry is None:
        return SeamResult(candidate.candidate_id, REJECTED_BY_PREFLIGHT,
                          problems=tuple(problems))
    if provisional:
        return SeamResult(candidate.candidate_id, PROJECTED_PENDING_IDENTITY,
                          entry=entry,
                          reason=revalidation_reason or "identity_never_validated")
    return SeamResult(candidate.candidate_id, PROJECTED, entry=entry)


def entries_with_identity(results: Sequence[SeamResult]) -> Tuple[
        Tuple[QueueEntry, ...], Tuple[Tuple[str, Tuple[str, ...]], ...]]:
    """Split projected entries into ``(emittable, withheld_hotel_id_collisions)``.

    Two different failures hide behind the same symptom -- a repeated key in the
    payload -- and they must not be treated the same way.

    **Same ``queue_entry_id``** means the same candidate under the same worker
    contract. That is the idempotency key, so a repeat is genuinely one entry
    and is collapsed. (The Columbus corpus contains two candidates recorded
    twice; before C-5 this never surfaced because nothing was ever emitted.)

    **Different candidates sharing a ``hotel_id``** is the opposite problem.
    ``hotel_id`` is slugified from the property NAME, and two distinct
    properties can slugify identically. Collapsing those would merge two real
    hotels on a name match alone -- the precise false-merge this architecture
    forbids everywhere else. They are WITHHELD with a reason instead, because a
    queue cannot carry two entries under one id and we may not guess which one
    is wanted.
    """
    by_entry_id: Dict[str, QueueEntry] = {}
    for r in results:
        if r.outcome in SEAM_OUTCOMES_WITH_ENTRY and r.entry is not None:
            by_entry_id.setdefault(r.entry.queue_entry_id, r.entry)

    by_hotel_id: Dict[str, List[QueueEntry]] = {}
    for entry in by_entry_id.values():
        by_hotel_id.setdefault(entry.hotel_id, []).append(entry)

    emittable: List[QueueEntry] = []
    withheld: List[Tuple[str, Tuple[str, ...]]] = []
    for hotel_id, group in by_hotel_id.items():
        if len(group) == 1:
            emittable.append(group[0])
        else:
            withheld.append((hotel_id, tuple(sorted(e.candidate_id for e in group))))

    emittable.sort(key=lambda e: (is_provisional(e), e.queue_priority, e.hotel_id))
    return (tuple(emittable), tuple(sorted(withheld)))


def build_queue_payload(results: Sequence[SeamResult], *, batch_id: str,
                        created_at: str = "") -> dict:
    """Assemble projected entries into a loadable queue file payload.

    Ordering is deterministic and explainable from ``priority_reasons`` on every
    entry: statically-confirmed entries first, then provisional ones, then by
    ``queue_priority`` and ``hotel_id``. Provisional entries sort last because
    an operator working the queue top-down should reach proven work first.

    Both kinds are included -- a provisional entry IS work for the capture
    runner -- and they stay distinguishable by ``capture_state`` and by their
    empty ``required_fields``, never by their position in this list.

    The payload this returns always LOADS: duplicates are collapsed and
    hotel_id collisions withheld by ``entries_with_identity``, so the seam
    cannot emit a file the real preflight would refuse.
    """
    entries, _withheld = entries_with_identity(results)
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

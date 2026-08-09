"""The batch queue, and the preflight that refuses a bad one before Chrome
ever launches.

Preflight is strict on purpose. Every check here is one that would otherwise
fail late -- after a navigation, or worse, after a capture that looks fine and
cites a search URL. PTF-WORKERS-007 was exactly that defect discovered in
production; catching the same class at queue-load costs nothing.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.discovery.membrane import (
    POLICY_FIELD_DENYLIST, assert_dataclasses_clean, assert_no_policy_keys,
)

from .. import vocabulary as V
from ..source_retrieval import (
    URL_SHAPE_PROPERTY, classify_url_shape, extract_property_code_from_url,
)

QUEUE_SCHEMA = "ptf-capture-queue/1.1"

#: Explicit, enumerated compatibility allowlist (WO-1A Step 5). Loading used to
#: accept exactly one string, which made any additive field a breaking change.
#: 1.1 adds only OPTIONAL fields -- ``_REQUIRED_HOTEL_FIELDS`` is untouched at
#: nine -- so a 1.0 file remains fully valid and is read unchanged. Same
#: discipline as the worker's CONTRACT_COMPATIBILITY: named versions only, no
#: range parsing, unknown values still refused.
SUPPORTED_QUEUE_SCHEMAS = frozenset({"ptf-capture-queue/1.0", "ptf-capture-queue/1.1"})

_REQUIRED_HOTEL_FIELDS = (
    "hotel_id", "listing_key", "hotel_name", "brand", "official_url",
    "expected_address", "expected_city", "expected_state", "expected_phone",
)

#: PTF-COLUMBUS-INTEGRATE-UNRESOLVED-001. ``expected_phone`` is the one required
#: field the capture-time doctrine does not actually insist on, and requiring it
#: here was refusing hotels the gate itself would have confirmed.
#:
#: ``identity_keys`` decides identity on TWO INDEPENDENT KEY GROUPS -- address,
#: phone, property_identifier -- with at least one authoritative basis. Phone is
#: one of three, not a floor. A queue entry carrying a street address, a postal
#: code and a property code offers the gate address + property_identifier, which
#: is the same two-group standard it applies everywhere else; this batch's own
#: Fairfield Polaris capture reported exactly that pair.
#:
#: So the phone may be omitted, and ONLY when both substitutes are present. This
#: does not touch capture-time verification: the gate still has to find and agree
#: with two independent keys on the rendered page, and a queue entry that names
#: fewer facts gives it less to work with, never more.
_PHONE_SUBSTITUTE_FIELDS = ("expected_address", "expected_postal_code",
                            "expected_property_code")

# --------------------------------------------------------------------------- #
# PTF-DISCOVERY-001 C-4 -- provisional capture state.
#
# An entry whose identity could not be confirmed statically may still be worth
# opening in the rendered capture session, which reaches hosts the static
# fetcher cannot. Such an entry is NOT a request to extract policy: it is a
# request to PROVE IDENTITY first. The distinction has to be structural, not a
# note, because everything downstream treats a queue entry as work to do.
#
# Three properties make it safe:
#   1. the state is a small CLOSED vocabulary, and an unrecognised value is a
#      preflight failure -- never a silently-tolerated unknown;
#   2. the empty string is the historical value and means "an ordinary work
#      entry", so every queue written before this existed is unchanged;
#   3. a provisional entry must carry NO ``required_fields``. That is the
#      structural separation: ``required_fields`` is the list of policy fields
#      the worker is being asked to look for, and a provisional entry is not
#      asking for any of them yet.
# --------------------------------------------------------------------------- #

CAPTURE_STATE_READY = ""                                   # ordinary work entry
CAPTURE_STATE_PENDING_IDENTITY = "PENDING_CAPTURE_IDENTITY"

CAPTURE_STATES = frozenset({CAPTURE_STATE_READY, CAPTURE_STATE_PENDING_IDENTITY})

#: States that are NOT yet a request to extract policy, and may never be
#: treated as ready, verified or publishable.
PROVISIONAL_CAPTURE_STATES = frozenset({CAPTURE_STATE_PENDING_IDENTITY})


def is_provisional(entry: "QueueEntry") -> bool:
    """Is this entry awaiting capture-time identity proof rather than policy?"""
    return entry.capture_state in PROVISIONAL_CAPTURE_STATES


class QueueError(ValueError):
    """Raised when a queue cannot be trusted to drive a batch."""


@dataclass(frozen=True)
class QueueEntry:
    """One hotel awaiting capture. Field-for-field compatible with what
    ``CaptureJob`` needs, so the runner never has to invent anything."""

    hotel_id: str
    listing_key: str
    hotel_name: str
    brand: str
    official_url: str
    expected_address: str = ""
    expected_city: str = ""
    expected_state: str = ""
    expected_postal_code: str = ""
    expected_phone: str = ""
    expected_property_code: str = ""
    alternate_urls: Tuple[str, ...] = ()
    required_fields: Tuple[str, ...] = ()
    retrieval_artifact: str = ""
    notes: str = ""
    # PTF-DISCOVERY-001 WO-1A Step 3 / FD-3 rule 3. The contract version this
    # entry is to be processed under. The WORKER owns the value
    # (``vocabulary.CONTRACT_VERSION``); the queue only reads and carries it,
    # and never invents one. Defaulted empty on the dataclass so any code
    # constructing a QueueEntry directly is unaffected; ``validate_entry``
    # fills it from the worker's constant.
    #
    # This is the second half of the idempotency key
    # ``(candidate_id, worker_contract_version)``: a new contract version
    # legitimately produces a NEW active queue entry rather than silently
    # overwriting work verified under the old one.
    worker_contract_version: str = ""
    # --- WO-1A Step 5: discovery-seam fields (all OPTIONAL) ----------------- #
    # Every one is defaulted, and none is added to _REQUIRED_HOTEL_FIELDS, so
    # a queue file written before they existed loads unchanged. They exist so a
    # discovery-produced entry can carry its own provenance and priority
    # without the worker having to infer anything.
    queue_entry_id: str = ""             # stable id for THIS queue entry
    candidate_id: str = ""               # -> DiscoveryCandidate.candidate_id
    market_id: str = ""                  # -> MarketConfig.market_id
    supported_adapter: str = ""          # brand slug resolved via adapters.registry
    queue_priority: int = 0              # 0 == unprioritized (today's file order)
    priority_reasons: Tuple[str, ...] = ()
    identity_confidence: str = ""        # IdentityTier-style label, explainable
    discovery_provenance_refs: Tuple[str, ...] = ()   # raw ids + run_id, for audit
    run_context_ref: str = ""            # -> DiscoveryRunContext.run_id
    # OfficialUrlRecord as a plain JSON-able mapping. Deliberately not a typed
    # import: the queue lives in the policy domain and must not depend on a
    # discovery class to be loadable.
    official_url_record: Optional[dict] = None
    # --- C-4: provisional capture state (OPTIONAL, defaulted) --------------- #
    # "" is the historical value and means an ordinary work entry, so a queue
    # written before this field existed loads with exactly its old meaning.
    capture_state: str = CAPTURE_STATE_READY

    def to_dict(self) -> dict:
        return {
            "hotel_id": self.hotel_id, "listing_key": self.listing_key,
            "hotel_name": self.hotel_name, "brand": self.brand,
            "official_url": self.official_url,
            "expected_address": self.expected_address,
            "expected_city": self.expected_city,
            "expected_state": self.expected_state,
            "expected_postal_code": self.expected_postal_code,
            "expected_phone": self.expected_phone,
            "expected_property_code": self.expected_property_code,
            "alternate_urls": list(self.alternate_urls),
            "required_fields": list(self.required_fields),
            "retrieval_artifact": self.retrieval_artifact,
            "notes": self.notes,
            "worker_contract_version": self.worker_contract_version,
            "queue_entry_id": self.queue_entry_id,
            "candidate_id": self.candidate_id,
            "market_id": self.market_id,
            "supported_adapter": self.supported_adapter,
            "queue_priority": self.queue_priority,
            "priority_reasons": list(self.priority_reasons),
            "identity_confidence": self.identity_confidence,
            "discovery_provenance_refs": list(self.discovery_provenance_refs),
            "run_context_ref": self.run_context_ref,
            "official_url_record": self.official_url_record,
            "capture_state": self.capture_state,
        }


@dataclass(frozen=True)
class CaptureQueue:
    batch_id: str
    entries: Tuple[QueueEntry, ...]
    created_at: str = ""
    schema: str = QUEUE_SCHEMA

    def __len__(self) -> int:
        return len(self.entries)


def _problem(index: int, hotel_id: str, slug: str) -> str:
    return "hotel[%d]%s: %s" % (index, (" %s" % hotel_id) if hotel_id else "", slug)


def validate_entry(raw: dict, index: int,
                   *, known_brands: Sequence[str] = ()) -> Tuple[Optional[QueueEntry], List[str]]:
    """Validate one raw entry. Returns ``(entry_or_None, problems)``.

    Never raises: the caller collects every problem across the whole queue so
    an operator fixes them in one pass rather than one run per typo.
    """
    problems: List[str] = []
    if not isinstance(raw, dict):
        return (None, [_problem(index, "", "not_an_object")])

    hotel_id = str(raw.get("hotel_id") or "").strip()

    has = lambda f: bool(str(raw.get(f) or "").strip())          # noqa: E731
    phone_substituted = not has("expected_phone") and all(
        has(f) for f in _PHONE_SUBSTITUTE_FIELDS)
    for f in _REQUIRED_HOTEL_FIELDS:
        if f == "expected_phone" and phone_substituted:
            # Address + postal code + property code: two independent key groups
            # under the capture-time doctrine, so the gate is not weakened.
            continue
        if not has(f):
            problems.append(_problem(index, hotel_id, "missing_field:%s" % f))
    if problems:
        return (None, problems)

    url = str(raw["official_url"]).strip()
    parts = urlsplit(url)
    if parts.scheme != "https":
        problems.append(_problem(index, hotel_id, "url_not_https:%s" % (parts.scheme or "none")))
    if "@" in (parts.netloc or ""):
        problems.append(_problem(index, hotel_id, "url_embedded_credentials"))

    # The PTF-WORKERS-007 class, caught before a browser opens. A search URL is
    # never a stable citation whatever the page happens to say.
    shape = classify_url_shape(url)
    if shape != URL_SHAPE_PROPERTY:
        problems.append(_problem(index, hotel_id, "url_shape_not_property:%s" % shape))

    brand = str(raw["brand"]).strip().lower()
    if known_brands and brand not in known_brands:
        problems.append(_problem(index, hotel_id, "no_adapter_for_brand:%s" % brand))

    expected_code = str(raw.get("expected_property_code") or "").strip().lower()
    if expected_code:
        found = extract_property_code_from_url(url, [expected_code])
        if found.lower() != expected_code:
            problems.append(_problem(
                index, hotel_id,
                "property_code_not_in_url:%s" % expected_code))

    # FD-3 rules 2/6. An entry may state the contract version it was authored
    # under; if it does, that version is accepted ONLY when the explicit
    # allowlist says work under it may be processed by the current worker.
    # An entry that states nothing is stamped with the worker's current
    # version -- reading the worker's constant, never inventing a value.
    stated_contract = str(raw.get("worker_contract_version") or "").strip()
    if stated_contract and not V.contract_versions_compatible(
            V.CONTRACT_VERSION, stated_contract):
        problems.append(_problem(
            index, hotel_id,
            "incompatible_worker_contract_version:%s" % stated_contract))

    # Gate 1 refuses any attestation with no demonstrated automated failure, so
    # a queue entry that cannot produce one is work that can never be published.
    artifact = str(raw.get("retrieval_artifact") or "").strip()
    if artifact and not pathlib.Path(artifact).exists():
        problems.append(_problem(index, hotel_id, "retrieval_artifact_missing"))

    # C-4. An unrecognised capture state FAILS CLOSED. Tolerating an unknown
    # value would let a future or mistyped state be read as the ordinary
    # work-entry default, which is the one reading that must never happen by
    # accident.
    capture_state = str(raw.get("capture_state") or "").strip()
    required_raw = tuple(str(f).strip() for f in (raw.get("required_fields") or [])
                         if str(f).strip())
    if capture_state not in CAPTURE_STATES:
        problems.append(_problem(index, hotel_id,
                                 "unknown_capture_state:%s" % capture_state))
    elif capture_state in PROVISIONAL_CAPTURE_STATES and required_raw:
        # The structural separation from a policy-work entry. A provisional
        # entry that also asked for policy fields would be indistinguishable
        # from ready work to everything downstream.
        problems.append(_problem(
            index, hotel_id,
            "provisional_entry_must_not_request_policy_fields:%s" % capture_state))

    if problems:
        return (None, problems)

    alternates = tuple(str(u).strip() for u in (raw.get("alternate_urls") or [])
                       if str(u).strip())
    required = required_raw

    return (QueueEntry(
        hotel_id=hotel_id,
        listing_key=str(raw["listing_key"]).strip(),
        hotel_name=str(raw["hotel_name"]).strip(),
        brand=brand,
        official_url=url,
        expected_address=str(raw.get("expected_address") or "").strip(),
        expected_city=str(raw.get("expected_city") or "").strip(),
        expected_state=str(raw.get("expected_state") or "").strip(),
        expected_postal_code=str(raw.get("expected_postal_code") or "").strip(),
        expected_phone=str(raw.get("expected_phone") or "").strip(),
        expected_property_code=expected_code,
        alternate_urls=alternates,
        required_fields=required,
        retrieval_artifact=artifact,
        notes=str(raw.get("notes") or "").strip(),
        worker_contract_version=stated_contract or V.CONTRACT_VERSION,
        # WO-1A Step 5 discovery-seam fields. Absent in a 1.0 file, which is
        # why every one defaults rather than being required.
        queue_entry_id=str(raw.get("queue_entry_id") or "").strip(),
        candidate_id=str(raw.get("candidate_id") or "").strip(),
        market_id=str(raw.get("market_id") or "").strip(),
        supported_adapter=str(raw.get("supported_adapter") or "").strip(),
        queue_priority=int(raw.get("queue_priority") or 0),
        priority_reasons=tuple(str(r).strip() for r in (raw.get("priority_reasons") or [])
                               if str(r).strip()),
        identity_confidence=str(raw.get("identity_confidence") or "").strip(),
        discovery_provenance_refs=tuple(
            str(r).strip() for r in (raw.get("discovery_provenance_refs") or [])
            if str(r).strip()),
        run_context_ref=str(raw.get("run_context_ref") or "").strip(),
        official_url_record=(raw.get("official_url_record")
                             if isinstance(raw.get("official_url_record"), dict) else None),
        capture_state=capture_state,
    ), [])


def load_queue(path, *, known_brands: Sequence[str] = ()) -> CaptureQueue:
    """Load and fully validate a queue file. Raises ``QueueError`` listing
    every problem found -- a partly-valid queue is not run."""
    p = pathlib.Path(path)
    if not p.exists():
        raise QueueError("queue file not found: %s" % p)
    try:
        raw = json.loads(p.read_text("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise QueueError("queue file is not valid JSON: %s" % exc)

    if not isinstance(raw, dict):
        raise QueueError("queue file must contain an object")
    if raw.get("schema") not in SUPPORTED_QUEUE_SCHEMAS:
        raise QueueError("unsupported queue schema: %s" % raw.get("schema"))

    batch_id = str(raw.get("batch_id") or "").strip()
    if not batch_id:
        raise QueueError("queue is missing batch_id")
    if not all(c.isalnum() or c in "-_" for c in batch_id):
        raise QueueError("batch_id must be alphanumeric with - or _: %s" % batch_id)

    hotels = raw.get("hotels")
    if not isinstance(hotels, list) or not hotels:
        raise QueueError("queue carries no hotels")

    # INV-MEMBRANE-FIELD-DENYLIST at the read side (PTF-DISCOVERY-001 WO-1A
    # Step 1). A queue entry is the VerificationQueueEntry of this system, so
    # it may not DECLARE a pet-policy field -- the official-source worker is
    # the sole producer of policy facts.
    #
    # Two deliberate scoping choices, both load-bearing:
    #
    #  1. KEYS ONLY, never values. ``required_fields`` legitimately carries
    #     every denylisted token as a value (it is the list of fields the
    #     worker should go look for on the official page, populated from
    #     ``vocabulary.POLICY_FIELDS``). A value scan would reject every
    #     valid production queue.
    #  2. The normative 14-name amendment §C set, not discovery's extended
    #     set. This is the queue contract governed by the amendment; the
    #     extra discovery-only names (allows_dogs / pet_friendly /
    #     pet_policy) govern discovery records, not this file.
    #
    # Fails closed and totally: a violating queue is never partly run.
    for item in hotels:
        if isinstance(item, dict):
            assert_no_policy_keys(item, context="queue entry",
                                  denylist=POLICY_FIELD_DENYLIST)

    entries: List[QueueEntry] = []
    problems: List[str] = []
    seen: Dict[str, int] = {}

    for i, item in enumerate(hotels):
        entry, probs = validate_entry(item, i, known_brands=known_brands)
        problems.extend(probs)
        if entry is None:
            continue
        if entry.hotel_id in seen:
            problems.append(_problem(i, entry.hotel_id,
                                     "duplicate_hotel_id_of_index:%d" % seen[entry.hotel_id]))
            continue
        seen[entry.hotel_id] = i
        entries.append(entry)

    if problems:
        raise QueueError("queue failed preflight (%d problem(s)):\n  %s"
                         % (len(problems), "\n  ".join(problems)))

    # Report the schema the FILE declared, not the current constant: a 1.0
    # queue is a 1.0 queue, and silently relabelling it would erase the
    # distinction the allowlist exists to make visible.
    return CaptureQueue(batch_id=batch_id, entries=tuple(entries),
                        created_at=str(raw.get("created_at") or ""),
                        schema=str(raw.get("schema")))


def round_robin_by_brand(entries: Sequence[QueueEntry]) -> Tuple[QueueEntry, ...]:
    """Interleave by brand so long same-brand runs do not occur.

    Sorting by ``(queue_priority, hotel_id)`` groups brands together, because
    hotel ids begin with the brand's own naming. On the real 79-candidate queue
    that produced a run of ELEVEN consecutive IHG requests and a run of ten
    Hilton -- and Hilton began refusing us five hotels into such a run.
    Interleaving is the cheapest thing that stops asking one brand for
    everything at once.

    The algorithm, and nothing more:

      1. start from the existing deterministic sort ``(queue_priority,
         hotel_id)`` -- unchanged, and still the only thing that decides order
         WITHIN a brand;
      2. partition into one bucket per brand, preserving that order;
      3. bucket order is first appearance in the sorted input;
      4. emit one candidate from each non-empty bucket per round, in bucket
         order, until every bucket is empty.

    Pure and total: no clock, no randomness, no brand knowledge beyond the
    ``brand`` field already on the entry. Identical input always produces
    identical output, so a replay orders identically.

    ``queue_priority`` keeps its exact meaning -- it decides which candidate a
    brand offers next, not which brand goes next. A skewed queue therefore ends
    with a tail of whichever brand has the most entries; that is arithmetic, not
    a defect, and it is what the same-brand floor exists to cover.
    """
    buckets: Dict[str, List[QueueEntry]] = {}
    order: List[str] = []
    for entry in sorted(entries, key=lambda e: (e.queue_priority, e.hotel_id)):
        if entry.brand not in buckets:
            buckets[entry.brand] = []
            order.append(entry.brand)
        buckets[entry.brand].append(entry)

    out: List[QueueEntry] = []
    while any(buckets[b] for b in order):
        for brand in order:
            if buckets[brand]:
                out.append(buckets[brand].pop(0))
    return tuple(out)


def remaining_entries(queue: CaptureQueue,
                      completed_hotel_ids: Sequence[str]) -> Tuple[QueueEntry, ...]:
    """Entries with no terminal journal record yet. This is the whole of resume:
    the journal is the truth, the queue is just the plan."""
    done = frozenset(completed_hotel_ids)
    return tuple(e for e in queue.entries if e.hotel_id not in done)


# Structural half of INV-MEMBRANE-FIELD-DENYLIST for the queue contract
# (WO-1A Step 1): checked once at import, so a QueueEntry that declared a
# policy field could not be imported, let alone constructed.
assert_dataclasses_clean(QueueEntry, CaptureQueue,
                         context="capture_automation.queue",
                         denylist=POLICY_FIELD_DENYLIST)

"""PTF-DISCOVERY-001 -- the discovery capture -> attestation input bridge.

WHY THIS EXISTS
---------------
The whole downstream chain already works: ingestion, evidence completeness,
attestation, hash-bound approval, block-scoped extraction, promotion, assembly.
It has run on live evidence and published 38 hotels. Exactly one link was
missing, and it is a plumbing link rather than a doctrine one --
``attest-official-page`` resolves its hotel against the legacy seed CSV, and 62
captured properties came from DISCOVERY entries that were never seeded. There
was no way in.

This module is that way in, and nothing more. It converts a discovery queue
entry plus the capture package the runner already wrote into the existing
``CaptureJob``, which every later stage consumes unchanged. It adds no
extraction rule, no vocabulary, no validation, and no authority.

WHAT IT REFUSES
---------------
A bridge is a place where evidence changes hands, so every claim is re-derived
rather than believed:

  * identity must be exactly IDENTITY_CONFIRMED -- not "ok", not "probably";
  * the capture's own text and html hashes are recomputed from the bytes;
  * the screenshot's sha256 is recomputed from the file on disk;
  * the final URL must match the queue entry's official URL;
  * the recorded policy-block offsets must actually fall inside the captured
    text, and must still frame the recorded excerpt;
  * the queue entry must carry the identity fields the operator will be asked
    to affirm.

Anything short of that is a refusal with a named reason. The output is a
PENDING, approval-ready input -- this module never approves, never promotes,
never writes published data, and never touches the seed.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from .identity_keys import IDENTITY_CONFIRMED

#: The queue fields an operator is later asked to affirm. A capture whose entry
#: cannot state them produces an attestation prompt nobody can honestly answer,
#: which is the failure PTF-CAPTURE-003E exists to prevent.
REQUIRED_IDENTITY_FIELDS = ("listing_key", "hotel_id", "hotel_name", "brand",
                            "official_url", "expected_address", "expected_city",
                            "expected_state", "expected_phone")

#: Optional, carried when present. Absence is recorded, never invented.
OPTIONAL_IDENTITY_FIELDS = ("expected_postal_code", "expected_property_code")


class BridgeRefusal(ValueError):
    """The capture may not cross into the attestation chain, and why."""


def normalized_url(url: str) -> str:
    """Query and trailing slash removed, lowercased.

    The same property reaches us under several URLs -- a bare path, the same
    path with ``?SEO_id=``, the same path with a trailing slash -- because the
    discovery corpus contains duplicate entries for one hotel. Deduplication
    has to compare what the URLs MEAN, not how they were written.
    """
    parts = urlsplit((url or "").strip())
    host = (parts.hostname or "").lower()
    path = (parts.path or "").rstrip("/").lower()
    return "%s://%s%s" % (parts.scheme.lower() or "https", host, path)


def _sha256_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class BridgeInput:
    """One discovery capture, ready to be checked.

    ``identity`` comes from the JOURNAL, not the capture. The runner records the
    identity assessment on the terminal outcome's artifacts -- the capture
    payload carries hydration, policy and interaction state but no identity
    block. Reading it from the capture would have refused every real capture,
    which is exactly what a dry run against the 67 on disk showed.
    """

    entry: Mapping                      # the queue entry, as written
    capture_path: pathlib.Path
    screenshot_path: pathlib.Path
    view_path: pathlib.Path
    identity: Mapping                   # journal artifacts["identity"]

    @staticmethod
    def from_capture(entry: Mapping, capture_path, identity: Mapping = None,
                     screenshot_path=None) -> "BridgeInput":
        """Locate the sidecars the runner writes beside a capture."""
        p = pathlib.Path(capture_path)
        stem = str(p.with_suffix(""))
        png = pathlib.Path(screenshot_path) if screenshot_path else pathlib.Path(stem + ".png")
        return BridgeInput(entry=entry, capture_path=p, screenshot_path=png,
                           view_path=pathlib.Path(stem + ".view.json"),
                           identity=dict(identity or {}))


def inputs_from_batch(batch_dir, entries_by_url: Mapping) -> Tuple[
        Tuple["BridgeInput", ...], Tuple[Tuple[str, str], ...]]:
    """Pair every CAPTURED journal record with its capture package.

    The journal is the authority for what happened; the capture files are the
    evidence it happened to. ``artifacts.json_path`` is the link between them,
    written by the runner, so nothing here has to guess at a filename.

    Returns ``(inputs, unpairable)`` -- a record whose queue entry or capture
    file cannot be found is reported, never silently skipped.
    """
    root = pathlib.Path(batch_dir)
    journal = root / "journal.jsonl"
    inputs: List[BridgeInput] = []
    unpairable: List[Tuple[str, str]] = []
    if not journal.exists():
        return ((), (("*", "missing_journal:%s" % journal),))

    for line in journal.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("state") != "CAPTURED":
            continue
        hotel_id = str(record.get("hotel_id") or "?")
        artifacts = record.get("artifacts") or {}
        capture = artifacts.get("json_path") or ""
        if not capture or not pathlib.Path(capture).exists():
            unpairable.append((hotel_id, "capture_file_not_found"))
            continue
        try:
            payload = json.loads(pathlib.Path(capture).read_text("utf-8"))
        except (OSError, ValueError):
            unpairable.append((hotel_id, "capture_unreadable"))
            continue
        entry = entries_by_url.get(normalized_url(str(payload.get("final_url") or "")))
        if entry is None:
            unpairable.append((hotel_id, "no_queue_entry_for_url"))
            continue
        inputs.append(BridgeInput.from_capture(
            entry, capture, identity=artifacts.get("identity") or {},
            screenshot_path=artifacts.get("png_path") or None))
    return (tuple(inputs), tuple(unpairable))


@dataclass(frozen=True)
class BridgeResult:
    """A verified crossing. ``job`` is the existing CaptureJob, untouched."""

    job: object                          # operator_capture.CaptureJob
    payload: dict                        # the capture, as loaded
    screenshot_path: pathlib.Path
    view_path: pathlib.Path
    normalized_url: str
    identity_outcome: str
    identity_key_groups: Tuple[str, ...]
    policy_excerpt: str
    verified: Tuple[str, ...]            # what was re-derived, for the record
    status: str = "PENDING"

    @property
    def publishable(self) -> bool:
        """Always false. Approval is a separate act by a separate person, and
        this module is not it."""
        return False

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "publishable": self.publishable,
            "hotel_id": self.job.listing_key,
            "listing_name": self.job.listing_name,
            "official_url": self.job.official_url,
            "normalized_url": self.normalized_url,
            "identity_outcome": self.identity_outcome,
            "identity_key_groups": list(self.identity_key_groups),
            "capture_path": str(self.capture_path_of()),
            "screenshot_path": str(self.screenshot_path),
            "view_path": str(self.view_path),
            "policy_excerpt_chars": len(self.policy_excerpt),
            "verified": list(self.verified),
        }

    def capture_path_of(self) -> pathlib.Path:
        return pathlib.Path(self.payload.get("__capture_path__", ""))


def bridge_capture(item: BridgeInput, *, required_fields: Sequence[str] = ()) -> BridgeResult:
    """Verify one discovery capture and build its attestation input.

    Raises ``BridgeRefusal`` rather than returning a partial result: a capture
    that cannot prove itself does not get a weaker crossing, it gets none.
    """
    from ..operator_capture import CaptureJob

    entry = dict(item.entry or {})
    verified: List[str] = []

    # -- 1. the queue entry can state what the operator must affirm --------- #
    missing = [f for f in REQUIRED_IDENTITY_FIELDS if not str(entry.get(f) or "").strip()]
    if missing:
        raise BridgeRefusal("missing_queue_identity_fields:%s" % ",".join(sorted(missing)))
    verified.append("queue_identity_fields")

    # -- 2. the files exist ------------------------------------------------- #
    for label, path in (("capture", item.capture_path),
                        ("screenshot", item.screenshot_path),
                        ("view_metadata", item.view_path)):
        if not path.exists():
            raise BridgeRefusal("missing_%s:%s" % (label, path.name))
    verified.append("artifacts_present")

    payload = json.loads(item.capture_path.read_text("utf-8"))

    # -- 3. identity was CONFIRMED, exactly --------------------------------- #
    # From the JOURNAL record, which is where the runner writes it.
    identity = dict(item.identity or {})
    outcome = str(identity.get("outcome") or "")
    if outcome != IDENTITY_CONFIRMED:
        raise BridgeRefusal("identity_not_confirmed:%s" % (outcome or "none_recorded"))
    keys = identity.get("keys") or {}
    groups = tuple(str(g) for g in (keys.get("independent_groups") or ()))
    if len(set(groups)) < 2 or not keys.get("has_authoritative_key"):
        raise BridgeRefusal(
            "identity_evidence_insufficient:groups=%d,authoritative=%s"
            % (len(set(groups)), bool(keys.get("has_authoritative_key"))))
    verified.append("identity_confirmed")

    # -- 4. the capture's own hashes, recomputed from the bytes -------------- #
    for field, source in (("text_sha256", payload.get("text")),
                          ("html_sha256", payload.get("html"))):
        recorded = str(payload.get(field) or "")
        actual = _sha256_text(source or "")
        if not recorded:
            raise BridgeRefusal("capture_missing_%s" % field)
        if recorded != actual:
            raise BridgeRefusal("capture_hash_mismatch:%s" % field)
    verified.append("capture_hashes")

    # -- 5. the screenshot on disk is the one the sidecar names -------------- #
    sidecar = json.loads(item.view_path.read_text("utf-8"))
    recorded_png = str(sidecar.get("png_sha256") or "")
    if not recorded_png:
        raise BridgeRefusal("view_missing_png_sha256")
    if recorded_png != _sha256_file(item.screenshot_path):
        raise BridgeRefusal("screenshot_hash_mismatch")
    verified.append("screenshot_hash")

    # -- 6. the capture is of the page the queue asked for ------------------- #
    captured = normalized_url(str(payload.get("final_url") or ""))
    expected = normalized_url(str(entry.get("official_url") or ""))
    if not captured or captured != expected:
        raise BridgeRefusal("final_url_mismatch:%s!=%s" % (captured or "none", expected))
    verified.append("final_url")

    # -- 7. the policy block still frames what it claims --------------------- #
    policy = (payload.get("automation") or {}).get("policy") or {}
    text = payload.get("text") or ""
    excerpt = str(policy.get("text_excerpt") or "")
    start, end = policy.get("text_start"), policy.get("text_end")
    if not excerpt:
        raise BridgeRefusal("policy_block_absent")
    if not isinstance(start, int) or not isinstance(end, int):
        raise BridgeRefusal("policy_offsets_missing")
    if start < 0 or end > len(text) or start >= end:
        raise BridgeRefusal("policy_offsets_outside_text:%s-%s/%d" % (start, end, len(text)))
    # The excerpt is the span with trailing whitespace trimmed -- measured on
    # the 67 real captures: 9 match byte-for-byte, 58 are the span minus a
    # trailing "\n\n", and none is anything else. Demanding exact equality
    # refused 57 sound captures. What must still hold is that the offsets frame
    # THIS block and not some other part of the page, so the excerpt has to
    # begin the span rather than merely appear somewhere in it.
    span = text[start:end]
    if not span.strip() or not span.strip().startswith(excerpt.strip()):
        raise BridgeRefusal("policy_offsets_do_not_frame_excerpt")
    verified.append("policy_block_offsets")

    # -- 8. build the EXISTING contract. No new shape, no seed lookup ------- #
    job = CaptureJob(
        assignment_id="discovery-%s" % str(entry["hotel_id"]),
        listing_key=str(entry["listing_key"]),
        listing_name=str(entry["hotel_name"]),
        expected_address=str(entry["expected_address"]),
        expected_city=str(entry["expected_city"]),
        expected_state=str(entry["expected_state"]),
        expected_postal_code=str(entry.get("expected_postal_code") or ""),
        expected_phone=str(entry["expected_phone"]),
        official_url=str(entry["official_url"]),
        alternate_urls=tuple(str(u) for u in (entry.get("alternate_urls") or [])),
        failure_reason="discovery_capture",
        retrieval_status="ACCESS_BLOCKED",
        required_fields=tuple(required_fields),
    )
    payload["__capture_path__"] = str(item.capture_path)
    return BridgeResult(
        job=job, payload=payload, screenshot_path=item.screenshot_path,
        view_path=item.view_path, normalized_url=captured,
        identity_outcome=outcome, identity_key_groups=groups,
        policy_excerpt=excerpt, verified=tuple(verified))


@dataclass(frozen=True)
class BridgeBatch:
    """What a set of captures produced. Never a silent drop."""

    bridged: Tuple[BridgeResult, ...] = ()
    refused: Tuple[Tuple[str, str], ...] = ()        # (hotel_id, reason)
    duplicates: Tuple[Tuple[str, str], ...] = ()     # (hotel_id, normalized_url)

    def summary(self) -> dict:
        return {"bridged": len(self.bridged), "refused": len(self.refused),
                "duplicates": len(self.duplicates)}


def bridge_many(items: Sequence[BridgeInput], *,
                required_fields: Sequence[str] = ()) -> BridgeBatch:
    """Bridge a set, deduplicating by NORMALIZED final URL.

    Deduplication happens here rather than downstream because the discovery
    corpus genuinely contains one property under several hotel_ids -- five URLs
    were captured twice across the two batches. Two candidates for one hotel
    would become two attestations and two publishable records for the same
    property. First occurrence wins, in the order given, which is deterministic
    for a deterministically ordered input.
    """
    bridged: List[BridgeResult] = []
    refused: List[Tuple[str, str]] = []
    duplicates: List[Tuple[str, str]] = []
    seen: Dict[str, str] = {}

    for item in items:
        hotel_id = str((item.entry or {}).get("hotel_id") or "?")
        key = normalized_url(str((item.entry or {}).get("official_url") or ""))
        if key and key in seen:
            duplicates.append((hotel_id, key))
            continue
        try:
            result = bridge_capture(item, required_fields=required_fields)
        except BridgeRefusal as exc:
            refused.append((hotel_id, str(exc)))
            continue
        seen[result.normalized_url] = hotel_id
        bridged.append(result)

    return BridgeBatch(tuple(bridged), tuple(refused), tuple(duplicates))


# --------------------------------------------------------------------------- #
# Published-overlap reporting. Comparison only -- this module never writes.
# --------------------------------------------------------------------------- #

def published_overlaps(results: Sequence[BridgeResult],
                       published: Sequence[Mapping]) -> Tuple[dict, ...]:
    """Which bridged captures describe an already-published hotel.

    Reported so a reviewer can COMPARE, never so anything can be replaced. Some
    published records were reached deliberately -- one carries ``fee_conflict``,
    another ``fee_withheld`` -- and a re-extraction that silently overwrote
    either would undo a decision, not correct one.
    """
    by_url = {}
    for record in published:
        key = normalized_url(str(record.get("source_url") or ""))
        if key:
            by_url[key] = record
    out = []
    for r in results:
        match = by_url.get(r.normalized_url)
        if match is None:
            continue
        out.append({
            "hotel_id": r.job.listing_key,
            "published_name": match.get("name"),
            "published_facts": sorted((match.get("facts") or {})),
            "action": "COMPARE_ONLY",
        })
    return tuple(out)

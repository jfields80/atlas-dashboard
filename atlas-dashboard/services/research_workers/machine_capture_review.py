"""PTF-MACHINE-REVIEW -- a review record for a SUCCESSFUL automated capture.

Why this exists as its own contract
-----------------------------------
``operator_capture.build_attestation`` is a human instrument. Gate 1 admits only
a demonstrated automated retrieval FAILURE, Gate 2 fixes an immutable first-
person statement -- "I personally opened this URL in an ordinary browser..." --
and Gate 3 requires that a person confirmed address and phone on screen.

The discovery capture sweep produced the opposite case: automation SUCCEEDED. A
visible browser reached the official page, hydrated it, expanded the policy card,
screenshotted it, and proved the property's identity from structured metadata.
There is no retrieval failure to record and nobody opened the page by hand.

Pushing those captures through the attestation contract would mean writing, in a
named operator's identity, a first-person claim about an act nobody performed,
beside a failure that did not occur. That is not a schema mismatch to paper over;
it is the exact substitution the gates exist to prevent. So this is a separate
record type that states ONLY what the machine can prove, and asks a reviewer for
a different, smaller, honest claim: that the preserved evidence supports the
proposed facts.

The two paths never substitute for each other. Nothing here imports, edits,
weakens or reuses the attestation contract, and an attestation is never derived
from a machine review or the reverse.

What the record asserts
-----------------------
Everything in it is re-derived at build time from artifacts on disk: the capture
JSON and its hash, the rendered text and HTML hashes, the screenshot and view
metadata, the final URL, the policy excerpt and the offsets that frame it, the
identity keys with their expected and observed values, and the extracted facts
together with a hash proving the extraction is reproducible.

What the record does NOT assert
-------------------------------
That anybody opened the live page. That automation failed. That any human
observed anything outside the preserved evidence. Those claims have no field
here, so they cannot be made by accident.

Status begins at PENDING_REVIEW and publishable begins false. Approval is a
separate act recorded separately, and promotion re-derives the record hash so
that evidence changing underneath an approval invalidates it.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA = "ptf-machine-verified-capture-review/1.0"

STATUS_PENDING_REVIEW = "PENDING_REVIEW"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"

DECISION_APPROVED = "APPROVED"
DECISION_REJECTED = "REJECTED"

OVERLAP_NONE = "NONE"
OVERLAP_COMPARE_ONLY = "COMPARE_ONLY"

IDENTITY_CONFIRMED = "IDENTITY_CONFIRMED"

#: The reviewer's claim. Deliberately smaller than the operator attestation's,
#: and it disclaims the three things a reviewer of preserved evidence cannot
#: honestly say. It is immutable for the same reason the attestation statement
#: is: a claim nobody can edit is a claim a record can be held to.
MACHINE_REVIEW_STATEMENT = (
    "I reviewed the preserved capture evidence for this property -- the recorded "
    "official URL, the screenshot, the visible policy excerpt, the machine-verified "
    "identity evidence, and the proposed facts -- and I judge the proposed facts to "
    "be supported by that evidence. I did not open the live page. I do not claim any "
    "automated retrieval failed. I observed nothing outside the preserved evidence."
)

#: Minimum independent identity key groups (FD-5). Two is the floor everywhere
#: else in this pipeline and is not softened here.
MIN_IDENTITY_GROUPS = 2

#: A capture whose policy block states refusal belongs to the negative-policy
#: workflow. Handing one to this positive-policy contract is a routing error, and
#: an error that would publish "pets welcome" for a hotel that refuses them.
NEGATIVE_POLICY_MARKERS = (
    "pets not allowed", "no pets", "does not allow pets", "not pet friendly",
    "pets are not permitted", "not allow pets",
)

#: Facts that mean the source contradicts itself. Such a record is not a clean
#: extraction and does not belong in this workflow.
CONTRADICTION_KEYS = ("fee_conflict", "fee_withheld")


class MachineReviewError(ValueError):
    """Refusal to build or use a machine-review record. Carries the reason."""


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #

def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _repo_relative(path, repo_root: pathlib.Path) -> str:
    """Paths are stored relative to the repository so a record hashes the same
    on another machine. An absolute path would make the hash machine-specific."""
    p = pathlib.Path(path)
    try:
        return p.resolve().relative_to(pathlib.Path(repo_root).resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def _normalize_ws(text: str) -> str:
    return " ".join((text or "").split())


# --------------------------------------------------------------------------- #
# The record.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class MachineCaptureReview:
    """One successful automated capture, ready for a reviewer. Immutable."""

    hotel_id: str
    listing_key: str
    hotel_name: str
    brand: str
    normalized_url: str
    source_url: str

    capture_path: str
    screenshot_path: str
    view_path: str

    capture_sha256: str
    rendered_text_sha256: str
    html_sha256: str
    screenshot_sha256: str
    view_sha256: str

    identity_outcome: str
    identity_key_groups: Tuple[str, ...]
    identity_authoritative_basis: Tuple[str, ...]
    identity_evidence: Tuple[Mapping, ...]

    policy_excerpt: str
    policy_offsets: Mapping
    evidence_quotes: Tuple[Mapping, ...]
    facts: Mapping
    extraction_result_hash: str

    bridge_verified: Tuple[str, ...]
    published_overlap: str
    capture_commit: str
    created_at: str

    schema: str = SCHEMA
    status: str = STATUS_PENDING_REVIEW
    publishable: bool = False

    def hashed_content(self) -> dict:
        """Everything the record asserts, minus when it happened to be written.

        ``created_at`` is excluded so a deterministic replay of the same evidence
        produces the same hash. A record that changes only because it was rebuilt
        would make staleness undetectable, which is the one thing the hash is for.
        """
        return {
            "schema": self.schema,
            "hotel_id": self.hotel_id,
            "listing_key": self.listing_key,
            "hotel_name": self.hotel_name,
            "brand": self.brand,
            "normalized_url": self.normalized_url,
            "source_url": self.source_url,
            "capture_path": self.capture_path,
            "screenshot_path": self.screenshot_path,
            "view_path": self.view_path,
            "capture_sha256": self.capture_sha256,
            "rendered_text_sha256": self.rendered_text_sha256,
            "html_sha256": self.html_sha256,
            "screenshot_sha256": self.screenshot_sha256,
            "view_sha256": self.view_sha256,
            "identity_outcome": self.identity_outcome,
            "identity_key_groups": list(self.identity_key_groups),
            "identity_authoritative_basis": list(self.identity_authoritative_basis),
            "identity_evidence": [dict(k) for k in self.identity_evidence],
            "policy_excerpt": self.policy_excerpt,
            "policy_offsets": dict(self.policy_offsets),
            "evidence_quotes": [dict(q) for q in self.evidence_quotes],
            "facts": dict(self.facts),
            "extraction_result_hash": self.extraction_result_hash,
            "bridge_verified": list(self.bridge_verified),
            "published_overlap": self.published_overlap,
            "capture_commit": self.capture_commit,
            "status": self.status,
            "publishable": self.publishable,
        }

    def record_hash(self) -> str:
        return "sha256:" + hashlib.sha256(
            _canonical(self.hashed_content()).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        out = self.hashed_content()
        out["created_at"] = self.created_at
        out["record_hash"] = self.record_hash()
        return out


# --------------------------------------------------------------------------- #
# Building, with every gate.
# --------------------------------------------------------------------------- #

def build_machine_review(*, bridge_result, identity: Mapping,
                         extractor: Callable, published_overlap: str,
                         capture_commit: str, created_at: str,
                         repo_root, brand: str = "",
                         seen_urls: Optional[set] = None) -> MachineCaptureReview:
    """Re-derive everything from disk and refuse on any disagreement.

    ``extractor`` is called TWICE on the policy excerpt. A result that does not
    reproduce is not a result: it would make the recorded extraction hash a
    statement about one lucky run rather than about the evidence.
    """
    repo_root = pathlib.Path(repo_root)

    # Gate -- identity must be confirmed, on enough independent evidence.
    outcome = str((identity or {}).get("outcome") or bridge_result.identity_outcome or "")
    if outcome != IDENTITY_CONFIRMED:
        raise MachineReviewError("identity_not_confirmed:%s" % (outcome or "missing"))

    # A bare postcode is not an address. One property's expected address is the
    # five digits "43221", which matches an observed "43221" trivially and
    # distinguishes nothing -- a ZIP covers many hotels. It stays RECORDED as
    # evidence, but it does not count toward the independent-group floor.
    keys_seen = tuple((identity or {}).get("keys", {}).get("keys") or ())
    weak = {k.get("group") for k in keys_seen
            if k.get("group") == "address"
            and re.fullmatch(r"\s*[0-9]{5}(?:-[0-9]{4})?\s*", str(k.get("expected") or ""))}
    groups = tuple(g for g in (bridge_result.identity_key_groups or ()) if g not in weak)
    if len(groups) < MIN_IDENTITY_GROUPS:
        raise MachineReviewError(
            "insufficient_identity_groups:%d<%d" % (len(groups), MIN_IDENTITY_GROUPS))

    keys = tuple((identity or {}).get("keys", {}).get("keys") or ())
    bases = tuple(sorted({str(k.get("basis") or "") for k in keys
                          if k.get("authoritative")} - {""}))
    if not bases:
        raise MachineReviewError("no_authoritative_identity_basis")

    # Gate -- every artifact must exist before anything is hashed.
    capture_path = pathlib.Path(bridge_result.capture_path_of())
    screenshot_path = pathlib.Path(bridge_result.screenshot_path or "")
    view_path = pathlib.Path(bridge_result.view_path or "")
    for label, path in (("capture", capture_path), ("screenshot", screenshot_path),
                        ("view_metadata", view_path)):
        if not str(path) or not path.exists():
            raise MachineReviewError("missing_%s_artifact" % label)

    payload = bridge_result.payload or {}

    # Gate -- the rendered text and HTML must still hash to what was recorded.
    text_hash = _sha256_text(payload.get("text", ""))
    if text_hash != str(payload.get("text_sha256") or ""):
        raise MachineReviewError("rendered_text_hash_mismatch")
    html_hash = _sha256_text(payload.get("html", ""))
    if html_hash != str(payload.get("html_sha256") or ""):
        raise MachineReviewError("html_hash_mismatch")

    # Gate -- the final URL the capture reached must be the URL being recorded.
    from services.research_workers.capture_automation.attestation_bridge import (
        normalized_url,
    )
    final_url = str(payload.get("final_url") or "")
    if not final_url:
        raise MachineReviewError("missing_final_url")
    if normalized_url(final_url) != bridge_result.normalized_url:
        raise MachineReviewError("final_url_mismatch")

    # Gate -- one property, one record.
    if seen_urls is not None:
        if bridge_result.normalized_url in seen_urls:
            raise MachineReviewError("duplicate_normalized_url:%s"
                                     % bridge_result.normalized_url)

    # Gate -- the offsets must actually frame the excerpt they claim to.
    automation = payload.get("automation") or {}
    policy = automation.get("policy") or {}
    start, end = policy.get("text_start"), policy.get("text_end")
    excerpt = bridge_result.policy_excerpt or ""
    if start is None or end is None:
        raise MachineReviewError("missing_policy_offsets")
    span = (payload.get("text") or "")[int(start):int(end)]
    if not span.strip() or not span.strip().startswith(excerpt.strip()[:80]):
        raise MachineReviewError("policy_offsets_do_not_frame_excerpt")

    # Gate -- a refusal belongs to the negative-policy workflow, not here.
    lowered = _normalize_ws(excerpt).lower()
    if any(marker in lowered for marker in NEGATIVE_POLICY_MARKERS):
        raise MachineReviewError("pets_not_allowed_record_in_positive_workflow")

    # Gate -- extraction must succeed, reproduce, and be free of contradictions.
    try:
        facts, evidence, _block = extractor(excerpt)
        facts_again, evidence_again, _b2 = extractor(excerpt)
    except Exception as exc:                                        # noqa: BLE001
        raise MachineReviewError("extraction_refused:%s" % exc)
    first = _canonical({"facts": facts, "evidence": evidence})
    if first != _canonical({"facts": facts_again, "evidence": evidence_again}):
        raise MachineReviewError("extraction_not_reproducible")
    contradictions = sorted(k for k in CONTRADICTION_KEYS if facts.get(k))
    if contradictions:
        raise MachineReviewError("contradictory_facts_present:%s"
                                 % ",".join(contradictions))

    if published_overlap not in (OVERLAP_NONE, OVERLAP_COMPARE_ONLY):
        raise MachineReviewError("unsupported_published_overlap:%s" % published_overlap)
    if not str(capture_commit or "").strip():
        raise MachineReviewError("missing_capture_commit")

    if seen_urls is not None:
        seen_urls.add(bridge_result.normalized_url)

    return MachineCaptureReview(
        hotel_id=str(bridge_result.job.assignment_id).split(":")[-1],
        listing_key=bridge_result.job.listing_key,
        hotel_name=bridge_result.job.listing_name,
        brand=brand,
        normalized_url=bridge_result.normalized_url,
        source_url=bridge_result.job.official_url,
        capture_path=_repo_relative(capture_path, repo_root),
        screenshot_path=_repo_relative(screenshot_path, repo_root),
        view_path=_repo_relative(view_path, repo_root),
        capture_sha256=_sha256_file(capture_path),
        rendered_text_sha256=text_hash,
        html_sha256=html_hash,
        screenshot_sha256=_sha256_file(screenshot_path),
        view_sha256=_sha256_file(view_path),
        identity_outcome=outcome,
        identity_key_groups=groups,
        identity_authoritative_basis=bases,
        identity_evidence=tuple(
            {"key": k.get("key", ""), "group": k.get("group", ""),
             "basis": k.get("basis", ""), "authoritative": bool(k.get("authoritative")),
             "expected": k.get("expected", ""), "observed": k.get("observed", "")}
            for k in keys),
        policy_excerpt=excerpt,
        policy_offsets={"text_start": int(start), "text_end": int(end)},
        evidence_quotes=tuple(dict(e) for e in evidence),
        facts=dict(facts),
        extraction_result_hash="sha256:" + hashlib.sha256(
            first.encode("utf-8")).hexdigest(),
        bridge_verified=tuple(bridge_result.verified or ()),
        published_overlap=published_overlap,
        capture_commit=capture_commit,
        created_at=created_at,
    )


def write_records(records: Sequence[MachineCaptureReview], out_dir) -> List[pathlib.Path]:
    """Write one file per hotel_id. Idempotent: a rerun over identical evidence
    rewrites identical bytes rather than adding a second record."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for record in records:
        path = out / ("%s.json" % record.hotel_id)
        path.write_text(json.dumps(record.to_dict(), indent=1, sort_keys=True,
                                   ensure_ascii=False), encoding="utf-8")
        written.append(path)
    return written


# --------------------------------------------------------------------------- #
# Review -- a separate act, by a separate person, on a separate record.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class MachineReviewDecision:
    """A reviewer's verdict on ONE machine record, bound to that record's hash."""

    reviewer_id: str
    reviewed_at: str
    decision: str
    source_record_hash: str
    field_decisions: Mapping[str, str] = field(default_factory=dict)
    notes: str = ""
    overlap_approved: bool = False
    statement: str = MACHINE_REVIEW_STATEMENT

    def hashed_content(self) -> dict:
        return {
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at,
            "decision": self.decision,
            "source_record_hash": self.source_record_hash,
            "field_decisions": dict(self.field_decisions),
            "notes": self.notes,
            "overlap_approved": self.overlap_approved,
            "statement": self.statement,
        }

    def approval_hash(self) -> str:
        return "sha256:" + hashlib.sha256(
            _canonical(self.hashed_content()).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        out = self.hashed_content()
        out["approval_hash"] = self.approval_hash()
        return out

    @property
    def approved_fields(self) -> Tuple[str, ...]:
        return tuple(sorted(k for k, v in self.field_decisions.items()
                            if v == DECISION_APPROVED))


def record_review(record: MachineCaptureReview, *, reviewer_id: str,
                  reviewed_at: str, decision: str,
                  field_decisions: Optional[Mapping[str, str]] = None,
                  notes: str = "", overlap_approved: bool = False,
                  statement: str = MACHINE_REVIEW_STATEMENT) -> MachineReviewDecision:
    """Record a reviewer's verdict. Never called by record creation."""
    if not str(reviewer_id or "").strip():
        raise MachineReviewError("review: reviewer_id is required")
    if not str(reviewed_at or "").strip():
        raise MachineReviewError("review: reviewed_at is required")
    if decision not in (DECISION_APPROVED, DECISION_REJECTED):
        raise MachineReviewError("review: decision must be APPROVED or REJECTED")
    if statement != MACHINE_REVIEW_STATEMENT:
        raise MachineReviewError("review: the reviewer statement may not be altered")
    for name, verdict in (field_decisions or {}).items():
        if verdict not in (DECISION_APPROVED, DECISION_REJECTED):
            raise MachineReviewError("review: field %r has verdict %r" % (name, verdict))
    return MachineReviewDecision(
        reviewer_id=reviewer_id.strip(), reviewed_at=reviewed_at.strip(),
        decision=decision, source_record_hash=record.record_hash(),
        field_decisions=dict(field_decisions or {}), notes=notes,
        overlap_approved=bool(overlap_approved), statement=statement)


# --------------------------------------------------------------------------- #
# Promotion safety.
# --------------------------------------------------------------------------- #

def _refuse_if_excluded(record: Mapping) -> None:
    """Raise ``MachineReviewError`` if this record's identity is excluded.

    Imported lazily: the review service must not take a hard import dependency
    on the publication layer just to be constructed, and a missing authority
    file is not an excuse to publish -- the guard's own loader fails closed.
    The block detail is preserved in the message so a refusal is diagnosable
    without re-running the guard by hand.
    """
    from scripts.pettripfinder.publication_guard import (
        PublicationBlockedError, assert_publishable)

    name = str(record.get("hotel_name") or record.get("listing_key") or "").strip()
    if not name:
        return
    try:
        assert_publishable([name], check_collisions=False)
    except PublicationBlockedError as exc:
        block = exc.blocks[0]
        raise MachineReviewError(
            "promotion_refused:excluded_identity:%s:%s"
            % (block.get("exclusion_state", ""), block.get("exclusion_id", ""))) from exc


def promotion_input(record: Mapping, review: Optional[Mapping]) -> dict:
    """The facts promotion may use, or a refusal.

    Re-derives the record hash from the record's own content rather than trusting
    the stored value, so evidence edited after an approval invalidates it instead
    of travelling under it.
    """
    # PTF-EXCLUSIONS-002. The exclusion authority outranks an approval: a
    # reviewer approving the evidence does not overturn a recorded decision that
    # this identity must never publish. Checked first, so an excluded record is
    # refused before any facts are assembled from it.
    _refuse_if_excluded(record)

    if not review:
        raise MachineReviewError("promotion_refused:no_review_record")
    if review.get("decision") != DECISION_APPROVED:
        raise MachineReviewError("promotion_refused:decision=%s"
                                 % (review.get("decision") or record.get("status")))

    rebuilt = {k: v for k, v in dict(record).items()
               if k not in ("created_at", "record_hash")}
    rebuilt_hash = "sha256:" + hashlib.sha256(
        _canonical(rebuilt).encode("utf-8")).hexdigest()
    if review.get("source_record_hash") != rebuilt_hash:
        raise MachineReviewError("promotion_refused:stale_or_mismatched_source_hash")

    if record.get("published_overlap") == OVERLAP_COMPARE_ONLY \
            and not review.get("overlap_approved"):
        raise MachineReviewError(
            "promotion_refused:published_overlap_not_specifically_approved")

    rejected = {k for k, v in (review.get("field_decisions") or {}).items()
                if v == DECISION_REJECTED}
    facts = {k: v for k, v in (record.get("facts") or {}).items() if k not in rejected}
    return {
        "hotel_id": record.get("hotel_id"),
        "listing_key": record.get("listing_key"),
        "normalized_url": record.get("normalized_url"),
        "facts": facts,
        "withheld_fields": sorted(rejected),
        "source_record_hash": rebuilt_hash,
        "approval_hash": review.get("approval_hash"),
        "published_overlap": record.get("published_overlap"),
    }


def is_publishable(record: Mapping, review: Optional[Mapping]) -> bool:
    """True only for an APPROVED review still bound to unchanged evidence."""
    try:
        promotion_input(record, review)
    except MachineReviewError:
        return False
    return True

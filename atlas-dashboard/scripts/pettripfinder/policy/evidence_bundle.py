"""PTF-POLICY-P0-001 -- the ladder transcript and evidence bundle.

A policy attempt is rarely one fetch. It is a walk down an ordered ladder of
official surfaces -- property page, policies page, booking flow, brand-hosted
property page, PDF, and finally a human contacting the property -- and the
thing worth keeping is not just the answer but the WALK: which surfaces were
tried, in what order, what each one did, and where the budget ran out.

Without that record two very different outcomes look identical in a report:
"we asked everywhere and this hotel states no pet policy" and "the first page
403'd and we stopped". The first is a finding. The second is a to-do. The
capture worker already refuses to blur that distinction for a single page
(``POLICY_NOT_FOUND`` vs ``ACCESS_DENIED``); this contract carries the same
honesty across a multi-surface attempt.

WHAT THE WORKER DOES AND DOES NOT DECIDE
----------------------------------------
The worker collects. It may PROPOSE a readiness state -- it is the only
component that knows the ladder ran dry rather than was cut short -- but the
proposal is advisory and is recomputed downstream by ``readiness.derive``.
Nothing here publishes, promotes, or writes a policy fact.

Pure and deterministic: no network, no clock, no file reads. Hashing is over
supplied bytes only.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.policy.policy_observation import (  # noqa: E402
    PolicyObservationError,
    validate_emission_batch,
)
from scripts.pettripfinder.policy.readiness import READINESS_STATES  # noqa: E402

BUNDLE_SCHEMA = "ptf-policy-evidence-bundle/1.0"
WORKER_CONTRACT_VERSION = "0.1.0"

#: The acquisition ladder, in order. A step is a SURFACE CLASS, not a URL.
LADDER_STEPS = ("A", "B", "C", "D", "E", "F", "G")

LADDER_STEP_MEANING = {
    "A": "official property page",
    "B": "official property policies/amenities page",
    "C": "official booking flow policy panel",
    "D": "brand-hosted property policy surface",
    "E": "official property PDF or fact sheet",
    "F": "other official property surface",
    "G": "direct contact with the property (human, attested)",
}

#: Every way a ladder step can end. Closed: an outcome not here cannot be
#: recorded, which is what keeps a transcript aggregatable.
LADDER_OUTCOMES = frozenset({
    "SUCCESS", "NO_POLICY_SECTION", "BLOCKED_403", "BLOCKED_CHALLENGE",
    "TIMEOUT", "WRONG_PROPERTY", "POLICY_BEHIND_BOOKING_FLOW",
    "STRUCTURED_FIELDS_ABSENT", "PDF_UNDATED", "PDF_IMAGE_ONLY",
    "NO_OTHER_OFFICIAL_SURFACE", "CONTACT_NO_ANSWER", "CONTACT_REFUSED",
    "NOT_ATTEMPTED_BUDGET", "NOT_IN_SCOPE",
})

#: Outcomes that mean the surface pushed back rather than answered. These are
#: what distinguish SOURCE_BLOCKED from POLICY_NOT_FOUND downstream.
BLOCKED_OUTCOMES = frozenset({"BLOCKED_403", "BLOCKED_CHALLENGE", "TIMEOUT"})

#: Outcomes that mean the surface answered, and the answer was "nothing here".
EXHAUSTED_OUTCOMES = frozenset({
    "NO_POLICY_SECTION", "STRUCTURED_FIELDS_ABSENT", "NO_OTHER_OFFICIAL_SURFACE",
})

WORKER_FAILURES = frozenset({
    "BLOCKED_ALL_SOURCES", "WRONG_PROPERTY_ABORT", "NO_POLICY_ANY_SURFACE",
    "BUDGET_EXHAUSTED", "ENVIRONMENT_UNAVAILABLE", "CONTRACT_VALIDATION_FAILED",
})

CAPTURE_METHODS = ("deterministic_fetch", "browser_assisted", "human_manual",
                   "phone_contact")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

#: Required by the adopted contract. Deliberately the SAME two fields the
#: research package's worker-result schema requires -- a step and what it did.
#: The work order asks an attempt to record much more than this, and it should;
#: but making the richer fields mandatory would have rejected the package's own
#: verified fixtures for being terse, which is a contract disagreement invented
#: by this integration rather than found in it. So: required minimum, validated
#: whenever present, and always emitted by ``build_bundle``.
TRANSCRIPT_REQUIRED = ("step", "outcome")
TRANSCRIPT_OPTIONAL = ("attempt", "source_attempted", "capture_method",
                       "timestamp", "page_url", "resulting_url",
                       "source_classification", "evidence_quotes",
                       "field_observations", "screenshot_ref", "dom_ref",
                       "text_ref", "contradiction_markers", "failure_reason",
                       "diagnostic_reason", "human_review_required", "detail",
                       "artifact_hashes")
TRANSCRIPT_ALLOWED = frozenset(TRANSCRIPT_REQUIRED) | frozenset(TRANSCRIPT_OPTIONAL)


class EvidenceBundleError(ValueError):
    """A transcript or bundle is malformed."""


@dataclass(frozen=True)
class LadderAttempt:
    """One step of one attempt against one hotel.

    Every field the work order asks a policy attempt to record lives here.
    Artifact references are POINTERS (paths/hashes), never payloads: a bundle
    stays readable and diffable, and the heavy artifacts stay where the capture
    worker already writes them.
    """

    attempt: int
    step: str
    source_attempted: str
    capture_method: str
    outcome: str
    timestamp: str = ""
    page_url: str = ""
    resulting_url: str = ""
    source_classification: str = ""
    evidence_quotes: Tuple[str, ...] = ()
    field_observations: Tuple[str, ...] = ()
    screenshot_ref: str = ""
    dom_ref: str = ""
    text_ref: str = ""
    contradiction_markers: Tuple[str, ...] = ()
    failure_reason: str = ""
    diagnostic_reason: str = ""
    human_review_required: bool = False
    detail: str = ""

    def to_dict(self) -> Dict:
        return {
            "attempt": self.attempt, "step": self.step,
            "source_attempted": self.source_attempted,
            "capture_method": self.capture_method, "outcome": self.outcome,
            "timestamp": self.timestamp, "page_url": self.page_url,
            "resulting_url": self.resulting_url,
            "source_classification": self.source_classification,
            "evidence_quotes": list(self.evidence_quotes),
            "field_observations": list(self.field_observations),
            "screenshot_ref": self.screenshot_ref, "dom_ref": self.dom_ref,
            "text_ref": self.text_ref,
            "contradiction_markers": list(self.contradiction_markers),
            "failure_reason": self.failure_reason,
            "diagnostic_reason": self.diagnostic_reason,
            "human_review_required": self.human_review_required,
            "detail": self.detail,
        }


def validate_transcript_entry(entry: Mapping) -> Dict:
    if not isinstance(entry, Mapping):
        raise EvidenceBundleError("a transcript entry must be a mapping, got %r"
                                  % type(entry).__name__)
    unknown = sorted(set(map(str, entry.keys())) - TRANSCRIPT_ALLOWED)
    if unknown:
        raise EvidenceBundleError("transcript entry carries unknown key(s) %s" % unknown)
    missing = [f for f in TRANSCRIPT_REQUIRED if f not in entry]
    if missing:
        raise EvidenceBundleError("transcript entry missing %s" % missing)
    if entry["step"] not in LADDER_STEPS:
        raise EvidenceBundleError(
            "unknown ladder step %r (steps: %s)" % (entry["step"], list(LADDER_STEPS)))
    if entry["outcome"] not in LADDER_OUTCOMES:
        raise EvidenceBundleError(
            "unknown ladder outcome %r" % (entry["outcome"],))
    if "capture_method" in entry and entry["capture_method"] not in CAPTURE_METHODS:
        raise EvidenceBundleError(
            "unknown capture_method %r" % (entry["capture_method"],))
    if "attempt" in entry:
        attempt = entry["attempt"]
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise EvidenceBundleError(
                "attempt must be a positive integer, got %r" % (attempt,))
    if "source_attempted" in entry and not str(entry["source_attempted"]).strip():
        raise EvidenceBundleError("source_attempted must be non-empty when present")
    if "human_review_required" in entry and \
            not isinstance(entry["human_review_required"], bool):
        raise EvidenceBundleError("human_review_required must be a boolean")
    return dict(entry)


def validate_transcript(transcript: Sequence[Mapping]) -> List[Dict]:
    """A transcript is ordered and non-empty: an attempt that recorded nothing
    is indistinguishable from an attempt that never ran."""
    if isinstance(transcript, Mapping) or not isinstance(transcript, (list, tuple)):
        raise EvidenceBundleError("ladder_transcript must be an array")
    if not transcript:
        raise EvidenceBundleError(
            "ladder_transcript must be non-empty -- a walk that recorded no step "
            "cannot be told apart from a walk that never happened")
    return [validate_transcript_entry(e) for e in transcript]


def manifest_sha256(artifact_hashes: Mapping[str, str]) -> str:
    """Deterministic manifest hash over {artifact_ref: sha256}. Sorted, so two
    runs producing the same artifacts produce the same manifest hash."""
    payload = "".join("%s:%s\n" % (k, artifact_hashes[k])
                      for k in sorted(artifact_hashes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_bundle(*, hotel_ref: Mapping, worker_id: str, assignment_id: str,
                 transcript: Sequence[Mapping],
                 observations: Sequence[Mapping] = (),
                 artifact_hashes: Mapping[str, str] = None,
                 proposed_readiness: str = "",
                 failure: str = "") -> Dict:
    """Assemble one attempt's evidence bundle.

    ``proposed_readiness`` is explicitly a PROPOSAL. The worker is the only
    component that knows whether the ladder ran dry or was cut short, so its
    opinion is worth recording -- and it is recomputed downstream by
    ``readiness.derive`` from the observations, which is what actually counts.
    """
    if not isinstance(hotel_ref, Mapping) or not str(hotel_ref.get("normalized_name", "")).strip():
        raise EvidenceBundleError(
            "bundle requires a hotel_ref carrying normalized_name -- the join "
            "key into the existing identity authority")
    entries = validate_transcript(transcript)
    observations = validate_emission_batch(list(observations))
    if proposed_readiness and proposed_readiness not in READINESS_STATES:
        raise EvidenceBundleError("unknown proposed_readiness %r" % proposed_readiness)
    if failure and failure not in WORKER_FAILURES:
        raise EvidenceBundleError("unknown failure state %r" % failure)

    hashes = dict(artifact_hashes or {})
    for ref, digest in hashes.items():
        if not _SHA256.match(str(digest)):
            raise EvidenceBundleError(
                "artifact %r hash must be 64 hex chars, got %r" % (ref, digest))

    bundle = {
        "schema": BUNDLE_SCHEMA,
        "contract_version": WORKER_CONTRACT_VERSION,
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "hotel_ref": dict(hotel_ref),
        "ladder_transcript": entries,
        "observations": observations,
        "observations_count": len(observations),
        "artifact_hashes": hashes,
        "bundle_manifest_sha256": manifest_sha256(hashes),
        "surfaces_blocked": sorted({e["outcome"] for e in entries
                                    if e["outcome"] in BLOCKED_OUTCOMES}),
        "surfaces_exhausted": sorted({e["outcome"] for e in entries
                                      if e["outcome"] in EXHAUSTED_OUTCOMES}),
        "human_review_required": any(e.get("human_review_required") for e in entries),
    }
    if proposed_readiness:
        bundle["proposed_readiness"] = proposed_readiness
        bundle["proposed_readiness_note"] = (
            "advisory only; recomputed downstream by readiness.derive from the "
            "observations. The worker collects; adjudication is downstream.")
    if failure:
        bundle["failure"] = failure
    return bundle


def ladder_reached_exhaustion(transcript: Sequence[Mapping]) -> bool:
    """True when every official surface actually rendered and stated nothing.

    This is the difference between POLICY_NOT_FOUND and SOURCE_BLOCKED, and it
    is computed rather than asserted so a worker cannot claim exhaustion it did
    not achieve.
    """
    entries = validate_transcript(transcript)
    attempted = [e for e in entries if e["outcome"] != "NOT_IN_SCOPE"]
    if not attempted:
        return False
    if any(e["outcome"] in BLOCKED_OUTCOMES for e in attempted):
        return False
    if any(e["outcome"] == "NOT_ATTEMPTED_BUDGET" for e in attempted):
        return False
    return all(e["outcome"] in EXHAUSTED_OUTCOMES or e["outcome"] == "SUCCESS"
               for e in attempted)


def ladder_was_blocked(transcript: Sequence[Mapping]) -> bool:
    """True when at least one surface pushed back and none succeeded."""
    entries = validate_transcript(transcript)
    if any(e["outcome"] == "SUCCESS" for e in entries):
        return False
    return any(e["outcome"] in BLOCKED_OUTCOMES for e in entries)


__all__ = [
    "BUNDLE_SCHEMA", "WORKER_CONTRACT_VERSION", "LADDER_STEPS",
    "LADDER_STEP_MEANING", "LADDER_OUTCOMES", "BLOCKED_OUTCOMES",
    "EXHAUSTED_OUTCOMES", "WORKER_FAILURES", "EvidenceBundleError",
    "LadderAttempt", "validate_transcript_entry", "validate_transcript",
    "manifest_sha256", "build_bundle", "ladder_reached_exhaustion",
    "ladder_was_blocked",
]

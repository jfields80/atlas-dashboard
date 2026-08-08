"""PTF-POLICY-P0-001 -- read-only bridge from the existing capture worker.

The browser-assisted capture worker in ``services/research_workers/
capture_automation`` already does the hard part: it navigates, gates identity
at capture time, locates the policy block, proves it was on screen, and writes
a ``ptf-official-capture/1.0`` payload with html/text/png hashes. This module
is the seam that turns one of those payloads into a
``ptf-policy-observation/1.0`` record.

DELIBERATELY ONE-DIRECTIONAL AND ADDITIVE
-----------------------------------------
Nothing in this module imports into the worker, and the worker does not import
this. Its navigation, browser lifecycle, diagnostics and failure artifacts are
untouched -- the work order requires additive integration, and a bridge that
made the worker depend on the policy layer would not be additive, it would be
a rewrite with a smaller diff.

The bridge maps rather than duplicates. Where the worker already records a
field, the observation references it:

    capture payload / CaptureArtifacts   ->  observation
    final_url                                source_url
    observed identity (name/address/code)    identity_check
    policy text excerpt                      evidence[].quote
    policy selector / section                evidence[].location
    html_sha256 / text_sha256 / png_sha256   capture_artifacts, snapshot_hash
    capture reason (ACCESS_DENIED etc.)      ladder outcome, via reason_to_outcome

WHAT THE BRIDGE REFUSES TO DO
-----------------------------
It does not extract. Turning prose into fields is the extractor's job and is
brand-specific; a bridge that guessed would be inventing facts at exactly the
point where nobody is looking. ``from_capture_payload`` produces an observation
whose ``extraction`` is EMPTY unless an adapter supplied one, and an empty
extraction is an honest statement that this capture proved a page existed and
said something, not that anyone has parsed it.

Pure and deterministic: no network, no clock. It reads only the payload handed
to it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.policy.policy_observation import (  # noqa: E402
    CONTRACT_VERSION,
    PT1_OFFICIAL_PROPERTY,
    PolicyObservationError,
    validate_observation,
)

#: Capture-worker terminal reason -> ladder outcome. The worker's vocabulary is
#: already closed and already draws the distinctions that matter; this table is
#: a translation, not a second taxonomy. A reason with no entry maps to nothing
#: and the caller must say what happened explicitly, which is safer than a
#: default that quietly means "fine".
REASON_TO_LADDER_OUTCOME = {
    "ACCESS_DENIED": "BLOCKED_403",
    "CAPTCHA_OR_CHALLENGE": "BLOCKED_CHALLENGE",
    "NAVIGATION_TIMEOUT": "TIMEOUT",
    "NAVIGATION_FAILED": "TIMEOUT",
    "CONSENT_INTERACTION_UNSUPPORTED": "BLOCKED_CHALLENGE",
    "IDENTITY_MISMATCH": "WRONG_PROPERTY",
    "PROPERTY_CODE_MISMATCH": "WRONG_PROPERTY",
    "REDIRECTED_OFF_PROPERTY": "WRONG_PROPERTY",
    "POLICY_NOT_FOUND": "NO_POLICY_SECTION",
    "POLICY_ABSENT_CONFIRMED": "SUCCESS",
    "INTERACTION_UNSUPPORTED": "POLICY_BEHIND_BOOKING_FLOW",
    "POLICY_OFF_SCREEN": "STRUCTURED_FIELDS_ABSENT",
    "INSUFFICIENT_TEXT": "STRUCTURED_FIELDS_ABSENT",
    "FEE_TERMS_CONFLICT": "SUCCESS",
}


class WorkerBridgeError(ValueError):
    """The capture payload cannot be expressed as an observation."""


def reason_to_outcome(reason: str) -> str:
    """Ladder outcome for a capture-worker terminal reason, or "" when the
    reason has no honest mapping."""
    return REASON_TO_LADDER_OUTCOME.get(reason or "", "")


def from_capture_payload(payload: Mapping, *, hotel_ref: Mapping, obs_id: str,
                         observed_at: str, retrieved_at: str,
                         source_type: str = "official_property_page",
                         authority_tier: str = PT1_OFFICIAL_PROPERTY,
                         evidence_quote: str = "", evidence_location: str = "",
                         evidence_field_refs: Sequence[str] = (),
                         extraction: Optional[Mapping] = None,
                         extraction_confidence: str = "EXACT_QUOTE",
                         flags: Sequence[Mapping] = ()) -> Dict:
    """One capture payload -> one validated policy observation.

    ``payload`` is a ``ptf-official-capture/1.0`` mapping as the existing
    worker writes it (the same shape ``DomSnapshot.from_capture_payload``
    consumes). Everything the observation asserts about the page comes from the
    payload; everything it asserts about POLICY must be supplied by the caller,
    because this module does not parse prose.
    """
    if not isinstance(payload, Mapping):
        raise WorkerBridgeError("capture payload must be a mapping, got %r"
                                % type(payload).__name__)
    final_url = str(payload.get("final_url") or payload.get("citable_url") or "").strip()
    if not final_url:
        raise WorkerBridgeError(
            "capture payload carries no final_url/citable_url; an observation "
            "without a re-findable source URL is not evidence")

    identity = payload.get("identity") or payload.get("observed_identity") or {}
    name_on_page = str(identity.get("name") or payload.get("title") or "").strip()
    if not name_on_page:
        raise WorkerBridgeError(
            "capture payload carries no page-observed name; the capture-time "
            "identity gate cannot be serialized and the observation would be "
            "unverifiable (M10)")

    identity_check: Dict[str, str] = {"name_on_page": name_on_page}
    street = str(identity.get("street") or "").strip()
    if street:
        identity_check["address_on_page"] = street
    code = str(identity.get("property_code") or "").strip()
    if code:
        identity_check["property_code"] = code
    phone = str(identity.get("phone") or "").strip()
    if phone:
        identity_check["phone_on_page"] = phone

    evidence = []
    if evidence_quote:
        evidence.append({
            "quote": evidence_quote,
            "location": evidence_location or "policy section",
            "field_refs": list(evidence_field_refs),
        })

    artifacts = {k: payload[k] for k in
                 ("html_sha256", "text_sha256", "png_sha256", "json_path",
                  "png_path")
                 if payload.get(k)}

    observation = {
        "obs_id": obs_id,
        "contract_version": CONTRACT_VERSION,
        "hotel_ref": dict(hotel_ref),
        "identity_check": identity_check,
        "source_url": final_url,
        "source_type": source_type,
        "authority_tier": authority_tier,
        "observed_at": observed_at,
        "retrieved_at": retrieved_at,
        "capture_method": "browser_assisted",
        "evidence": evidence,
        "extraction": dict(extraction or {}),
        "extraction_confidence": extraction_confidence,
        "flags": [dict(f) for f in flags],
    }
    snapshot = payload.get("text_sha256") or payload.get("html_sha256")
    if snapshot:
        observation["snapshot_hash"] = str(snapshot)
    if artifacts:
        observation["capture_artifacts"] = artifacts
    return validate_observation(observation)


__all__ = ["WorkerBridgeError", "REASON_TO_LADDER_OUTCOME", "reason_to_outcome",
           "from_capture_payload"]

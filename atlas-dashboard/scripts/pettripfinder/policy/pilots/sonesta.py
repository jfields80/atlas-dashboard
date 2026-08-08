"""PTF-POLICY-P0-001 -- Sonesta 10-property pilot FRAMEWORK.

The framework, and deliberately nothing else. This module can plan a bounded
pilot and summarise one; it cannot run one, and there is no Sonesta adapter
here. That is the point of the work order's wording ("framework only ... do not
build a full Sonesta adapter based only on research assumptions"): an adapter
written from research assumptions is a guess with a regex in it, and the whole
value of a pilot is finding out whether the guess was right.

WHAT A PILOT IS FOR
-------------------
Ten properties is enough to learn three things and not enough to do damage:

1. Does the official surface render the policy at all, or is it behind a
   booking flow?
2. Is the wording consistent enough across properties for a deterministic
   adapter, or does every property phrase it differently?
3. What fraction ends BLOCKED rather than answered?

A pilot that answers those licenses an adapter. A pilot that does not is also
a result, and the honest response is to leave the brand on the human path.

WHAT THIS FRAMEWORK GUARANTEES
------------------------------
* Fixed inputs: the identity list is supplied and frozen into the manifest, so
  a pilot cannot quietly widen mid-run.
* Deterministic attempt manifest: same inputs, same plan, same order.
* Zero automatic promotion: ``summarize`` reports readiness states and never
  writes anything. There is no promotion function in this module, and the
  summary explicitly carries ``promotion_performed: False``.

Pure and deterministic: no network, no clock, no file reads.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.policy import readiness as R                 # noqa: E402
from scripts.pettripfinder.policy.evidence_bundle import (              # noqa: E402
    LADDER_STEPS,
    EvidenceBundleError,
)
from scripts.pettripfinder.site_data import normalize_name              # noqa: E402

PILOT_ID = "sonesta-policy-pilot-001"
BRAND = "sonesta"
PILOT_SIZE = 10

#: The ladder this pilot is permitted to walk. Deliberately short: a pilot that
#: escalates to human contact (step G) is measuring the operator's patience,
#: not the brand's surfaces.
PILOT_LADDER = ("A", "B", "D")


class PilotError(ValueError):
    """The pilot plan is invalid."""


@dataclass(frozen=True)
class PilotTarget:
    """One property in the pilot. ``normalized_name`` is the join key into the
    existing identity authority -- the pilot mints no ids of its own."""

    market_id: str
    canonical_name: str
    normalized_name: str
    official_url: str = ""
    street_identity: str = ""

    def hotel_ref(self) -> Dict[str, str]:
        ref = {"market_id": self.market_id,
               "canonical_name": self.canonical_name,
               "normalized_name": self.normalized_name}
        if self.official_url:
            ref["official_url"] = self.official_url
        if self.street_identity:
            ref["street_identity"] = self.street_identity
        return ref


def build_targets(rows: Sequence[Mapping], *, market_id: str) -> Tuple[PilotTarget, ...]:
    """Turn supplied identity rows into pilot targets, deterministically.

    Sorted by normalized name so two planners produce the same manifest, and
    capped at ``PILOT_SIZE`` -- a "10-property pilot" that quietly ran 40 is
    not the thing that was authorised.
    """
    targets = []
    seen = set()
    for row in rows:
        name = str(row.get("canonical_name") or row.get("name") or "").strip()
        if not name:
            raise PilotError("a pilot target needs a canonical name: %r" % (row,))
        key = normalize_name(name)
        if key in seen:
            continue
        seen.add(key)
        targets.append(PilotTarget(
            market_id=market_id, canonical_name=name, normalized_name=key,
            official_url=str(row.get("official_url") or row.get("source_url") or ""),
            street_identity=str(row.get("street_identity") or "")))
    targets.sort(key=lambda t: t.normalized_name)
    if len(targets) > PILOT_SIZE:
        raise PilotError(
            "pilot is bounded at %d properties; %d supplied. Widening a pilot "
            "is a new authorisation, not a parameter." % (PILOT_SIZE, len(targets)))
    return tuple(targets)


def plan(targets: Sequence[PilotTarget]) -> Dict:
    """The deterministic attempt manifest. Planning is not running."""
    if not targets:
        raise PilotError("a pilot needs at least one target")
    attempts: List[Dict] = []
    for target in targets:
        for i, step in enumerate(PILOT_LADDER, start=1):
            attempts.append({
                "hotel_ref": target.hotel_ref(),
                "attempt": i,
                "step": step,
                "capture_method": "browser_assisted",
                "source_attempted": target.official_url or "(official surface tbd)",
            })
    return {
        "schema": "ptf-policy-pilot-plan/1.0",
        "pilot_id": PILOT_ID,
        "brand": BRAND,
        "target_count": len(targets),
        "ladder": list(PILOT_LADDER),
        "attempts_planned": len(attempts),
        "attempts": attempts,
        "authorisation_note": (
            "PLAN ONLY. This work order created the framework and did not run "
            "the pilot. Running it requires explicit operator authorisation, "
            "and running it still promotes nothing."),
    }


def summarize(bundles: Sequence[Mapping]) -> Dict:
    """Success/failure summary over completed bundles.

    Recomputes readiness from each bundle's observations rather than trusting
    the worker's proposal, and reports promotion as what it is: not performed,
    not attempted, not available from here.
    """
    per_hotel: List[Dict] = []
    state_counts: Dict[str, int] = {s: 0 for s in R.READINESS_STATES}
    for bundle in bundles:
        observations = bundle.get("observations") or []
        transcript = bundle.get("ladder_transcript") or []
        blocked = any(e.get("outcome") in ("BLOCKED_403", "BLOCKED_CHALLENGE",
                                           "TIMEOUT") for e in transcript)
        exhausted = bool(transcript) and all(
            e.get("outcome") in ("NO_POLICY_SECTION", "STRUCTURED_FIELDS_ABSENT",
                                 "NO_OTHER_OFFICIAL_SURFACE", "SUCCESS")
            for e in transcript)
        result = R.derive(observations, blocked=blocked,
                          all_surfaces_reached=exhausted)
        state_counts[result.state] = state_counts.get(result.state, 0) + 1
        per_hotel.append({
            "hotel_ref": bundle.get("hotel_ref", {}),
            "derived_state": result.state,
            "worker_proposed": bundle.get("proposed_readiness", ""),
            "reasons": list(result.reasons),
            "observations": bundle.get("observations_count", len(observations)),
        })
    return {
        "schema": "ptf-policy-pilot-summary/1.0",
        "pilot_id": PILOT_ID,
        "brand": BRAND,
        "hotels": len(per_hotel),
        "state_counts": state_counts,
        "per_hotel": per_hotel,
        "promotion_performed": False,
        "promotion_note": (
            "This framework has no promotion path. Publishing any of these "
            "would go through the existing operator approval flow and the "
            "publication guard, unchanged."),
        "adapter_decision_note": (
            "An adapter is licensed only if the surfaces rendered and the "
            "wording proved consistent. A blocked or inconsistent pilot leaves "
            "the brand on the human path, which is a result, not a failure."),
    }


__all__ = ["PILOT_ID", "BRAND", "PILOT_SIZE", "PILOT_LADDER", "PilotError",
           "PilotTarget", "build_targets", "plan", "summarize"]

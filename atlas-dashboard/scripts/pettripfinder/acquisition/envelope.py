"""The normalised acquisition result, and the states a routed property can end in.

WHY AN ENVELOPE
---------------
Interpretation should not know how a page was fetched. A Choice policy read
from Web Unlocker HTML and a Marriott policy read from a driven browser are the
same kind of thing to everything downstream: a first-party page, at a URL, at a
time, with hashed artifacts and a bounded quote. :class:`SourceDocument` is
that shape, and it is the only thing the router hands on.

Provider-specific facts still travel -- ``provider``, ``provider_product``,
``capture_method``, ``rendered`` -- because a reviewer needs to know what
fetched a record. They travel as DATA in a named field rather than as a
difference in structure.

PROVIDER SUCCESS IS NOT EVIDENCE SUCCESS
----------------------------------------
The two are separate fields here for the same reason they are separate ideas.
``status`` says the fetch worked. ``publication_grade`` says the CURRENT
evidence contract accepted it, and the router never sets that itself -- it
carries whatever ``publication_grade.assess`` returned. A provider that
succeeded and evidence that failed is an ordinary, expected outcome.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --------------------------------------------------------------------------- #
# Final router states. Exactly one per property, and none of them is silence.
# --------------------------------------------------------------------------- #

ACQUIRED_PUBLICATION_GRADE = "ACQUIRED_PUBLICATION_GRADE"
ACQUIRED_NONPUBLICATION_GRADE = "ACQUIRED_NONPUBLICATION_GRADE"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
IDENTITY_REVIEW = "IDENTITY_REVIEW"
SOURCE_AMBIGUOUS = "SOURCE_AMBIGUOUS"
SOURCE_CONTRADICTORY = "SOURCE_CONTRADICTORY"
TECHNICAL_FALLBACK_REQUIRED = "TECHNICAL_FALLBACK_REQUIRED"
PROVIDER_EXHAUSTED = "PROVIDER_EXHAUSTED"
BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"

ROUTER_STATES: Tuple[str, ...] = (
    ACQUIRED_PUBLICATION_GRADE, ACQUIRED_NONPUBLICATION_GRADE,
    POLICY_NOT_FOUND, IDENTITY_REVIEW, SOURCE_AMBIGUOUS, SOURCE_CONTRADICTORY,
    TECHNICAL_FALLBACK_REQUIRED, PROVIDER_EXHAUSTED, BUDGET_EXHAUSTED,
)

#: States in which a page was successfully acquired. Neither of them is a
#: decision about the hotel, and neither may be read as one.
ACQUIRED_STATES = frozenset({ACQUIRED_PUBLICATION_GRADE,
                             ACQUIRED_NONPUBLICATION_GRADE})

#: The only state whose evidence the existing publication path may consider.
PUBLICATION_GRADE_STATES = frozenset({ACQUIRED_PUBLICATION_GRADE})


@dataclass(frozen=True)
class ProviderAttempt:
    """One attempt by one provider, with what it cost."""

    provider: str
    provider_product: str
    attempt: int
    outcome: str
    failure: str = ""
    started_at: str = ""
    ended_at: str = ""
    elapsed_seconds: float = 0.0
    final_url: str = ""
    title: str = ""
    body_chars: int = 0
    detail: str = ""
    estimated_bytes: int = 0
    interactions: Tuple[str, ...] = ()

    def to_dict(self) -> Dict:
        return {"provider": self.provider,
                "provider_product": self.provider_product,
                "attempt": self.attempt, "outcome": self.outcome,
                "failure": self.failure, "started_at": self.started_at,
                "ended_at": self.ended_at,
                "elapsed_seconds": round(self.elapsed_seconds, 3),
                "final_url": self.final_url, "title": self.title,
                "body_chars": self.body_chars, "detail": self.detail,
                "estimated_bytes": self.estimated_bytes,
                "interactions": list(self.interactions)}


@dataclass(frozen=True)
class AcquisitionCost:
    """What one property's acquisition consumed.

    ``reported`` is what the provider's own billing said; ``estimated`` is
    arithmetic on measured traffic. They are separate fields because conflating
    a billed figure with a derived one is how a cost report stops being one.

    Credits live in their own field for the same reason, one step further out.
    Bright Data bills dollars and Firecrawl bills plan credits, and the plan
    endpoint reports an allowance rather than a unit price -- so there is no
    exchange rate between them that anyone has measured. A ladder that fell
    through from Firecrawl to the Web Unlocker consumed BOTH, and the honest
    record of that is two numbers, not one invented total.
    """

    attempts: int = 0
    failed_attempts: int = 0
    elapsed_seconds: float = 0.0
    estimated_bytes: int = 0
    reported_usd_minor: Optional[int] = None
    estimated_usd_minor: Optional[float] = None
    cost_status: str = "UNAVAILABLE"
    #: Plan credits consumed by credit-billed lanes. Never added to dollars.
    reported_credits: Optional[float] = None
    #: Seconds spent in each provider, so a fallback's latency cost is visible
    #: rather than hidden inside one total.
    seconds_by_provider: Mapping[str, float] = field(default_factory=dict)
    #: True when the ladder moved past its primary provider.
    fallback_invoked: bool = False

    def to_dict(self) -> Dict:
        return {"attempts": self.attempts,
                "failed_attempts": self.failed_attempts,
                "elapsed_seconds": round(self.elapsed_seconds, 3),
                "estimated_bytes": self.estimated_bytes,
                "reported_usd_minor": self.reported_usd_minor,
                "estimated_usd_minor": (round(self.estimated_usd_minor, 2)
                                        if self.estimated_usd_minor is not None
                                        else None),
                "reported_credits": self.reported_credits,
                "seconds_by_provider": {k: round(v, 3) for k, v
                                        in dict(self.seconds_by_provider).items()},
                "fallback_invoked": self.fallback_invoked,
                "currencies_are_not_combined": (
                    "usd_minor and plan credits are separate measurements of "
                    "separate vendors; no total spans them"),
                "cost_status": self.cost_status}


@dataclass(frozen=True)
class SourceDocument:
    """One acquired page, normalised. The acquisition/interpretation boundary.

    Everything an interpreter needs and nothing about how it was fetched beyond
    named provenance fields.
    """

    identity_key: str
    brand: str
    source_url: str
    final_url: str
    provider: str
    provider_product: str
    reader: str
    capture_method: str
    fetched_at: str
    status: str
    policy_text: str = ""
    policy_locator: str = ""
    rendered: bool = True
    rendered_html_path: str = ""
    text_path: str = ""
    screenshot_path: str = ""
    content_hash: str = ""
    artifacts: Mapping = field(default_factory=dict)
    identity: Mapping = field(default_factory=dict)
    observation: Mapping = field(default_factory=dict)
    withheld_fields: Mapping = field(default_factory=dict)
    non_inferences: Tuple[str, ...] = ()
    publication_grade: Mapping = field(default_factory=dict)
    contracts: Mapping = field(default_factory=dict)

    @property
    def is_publication_grade(self) -> bool:
        """Carried from the contract, never decided here."""
        return (self.publication_grade or {}).get(
            "verdict") == "PUBLICATION_GRADE_CONFIRMED"

    def to_dict(self) -> Dict:
        return {
            "identity_key": self.identity_key, "brand": self.brand,
            "source_url": self.source_url, "final_url": self.final_url,
            "provider": self.provider,
            "provider_product": self.provider_product,
            "reader": self.reader, "capture_method": self.capture_method,
            "fetched_at": self.fetched_at, "status": self.status,
            "policy_text": self.policy_text,
            "policy_locator": self.policy_locator,
            "rendered": self.rendered,
            "rendered_html_path": self.rendered_html_path,
            "text_path": self.text_path,
            "screenshot_path": self.screenshot_path,
            "content_hash": self.content_hash,
            "artifacts": dict(self.artifacts),
            "identity": dict(self.identity),
            "observation": dict(self.observation),
            "withheld_fields": dict(self.withheld_fields),
            "non_inferences": list(self.non_inferences),
            "publication_grade": dict(self.publication_grade),
            "contracts": dict(self.contracts),
        }


@dataclass(frozen=True)
class RoutingResult:
    """What the router decided, did, and spent, for one property."""

    identity_key: str
    hotel: str
    brand: str
    requested_url: str
    state: str
    route: Mapping
    attempts: Tuple[ProviderAttempt, ...] = ()
    providers_tried: Tuple[str, ...] = ()
    failure: str = ""
    failure_class: str = ""
    escalation_stopped_because: str = ""
    document: Optional[SourceDocument] = None
    cost: AcquisitionCost = field(default_factory=AcquisitionCost)
    run_id: str = ""

    @property
    def acquired(self) -> bool:
        return self.state in ACQUIRED_STATES

    def to_dict(self) -> Dict:
        return {
            "identity_key": self.identity_key, "hotel": self.hotel,
            "brand": self.brand, "requested_url": self.requested_url,
            "state": self.state, "route": dict(self.route),
            "attempts": [a.to_dict() for a in self.attempts],
            "providers_tried": list(self.providers_tried),
            "failure": self.failure, "failure_class": self.failure_class,
            "escalation_stopped_because": self.escalation_stopped_because,
            "document": self.document.to_dict() if self.document else None,
            "cost": self.cost.to_dict(), "run_id": self.run_id,
            "acquired": self.acquired,
            "authority_changed": False,
        }


__all__ = [
    "ACQUIRED_PUBLICATION_GRADE", "ACQUIRED_NONPUBLICATION_GRADE",
    "POLICY_NOT_FOUND", "IDENTITY_REVIEW", "SOURCE_AMBIGUOUS",
    "SOURCE_CONTRADICTORY", "TECHNICAL_FALLBACK_REQUIRED", "PROVIDER_EXHAUSTED",
    "BUDGET_EXHAUSTED", "ROUTER_STATES", "ACQUIRED_STATES",
    "PUBLICATION_GRADE_STATES", "ProviderAttempt", "AcquisitionCost",
    "SourceDocument", "RoutingResult",
]

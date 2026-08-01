"""Immutable data passed between the browser seam and the pure core.

``DomSnapshot`` is the whole interface between "what the browser saw" and
everything that reasons about it. Adapters, the locator, the identity check and
the validators accept snapshots and nothing else, which is why they can be
tested against saved capture files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class DomSnapshot:
    """One reading of a rendered page. Carries no browser handle, so it can be
    built from a saved capture file as easily as from a live tab."""

    final_url: str
    title: str = ""
    canonical_url: str = ""
    html: str = ""
    text: str = ""
    jsonld: Tuple[dict, ...] = ()
    viewport_width: int = 0
    viewport_height: int = 0

    @classmethod
    def from_capture_payload(cls, payload: dict) -> "DomSnapshot":
        """Build from a ``ptf-official-capture/1.0`` payload. This is what lets
        the retained corpus serve as the offline fixture set."""
        blocks = payload.get("jsonld") or []
        return cls(
            final_url=str(payload.get("final_url") or ""),
            title=str(payload.get("title") or ""),
            canonical_url=str(payload.get("canonical_url") or ""),
            html=str(payload.get("html") or ""),
            text=str(payload.get("text") or ""),
            jsonld=tuple(b for b in blocks if isinstance(b, dict)),
        )


@dataclass(frozen=True)
class ObservedIdentity:
    """What the page says about itself. Every field is optional because pages
    differ in what they expose; the identity check decides whether what is
    present is enough."""

    name: str = ""
    phone: str = ""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    property_code: str = ""
    sources: Tuple[str, ...] = ()   # e.g. ("jsonld", "url", "title")

    def to_dict(self) -> dict:
        return {"name": self.name, "phone": self.phone, "street": self.street,
                "city": self.city, "state": self.state,
                "postal_code": self.postal_code,
                "property_code": self.property_code,
                "sources": list(self.sources)}


@dataclass(frozen=True)
class InteractionStep:
    """One thing to do to the page. Adapters return these; only the driver
    performs them, and every one performed is recorded in the capture.

    ``click_text`` exists because CSS cannot select on text and some brands
    need it. Hilton keeps the pet policy in a tab panel that is ``display:none``
    until its "Pets" tab is clicked, and which tab index that is varies by
    property -- so the durable handle is the tab's label, not its id.
    """

    action: str                 # "click" | "click_text" | "scroll_into_view" | "wait"
    selector: str = ""
    reason: str = ""
    optional: bool = True
    wait_seconds: float = 0.0
    text: str = ""              # click_text only: the label to match

    def to_dict(self) -> dict:
        return {"action": self.action, "selector": self.selector,
                "reason": self.reason, "optional": self.optional,
                "wait_seconds": self.wait_seconds, "text": self.text}


CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"


@dataclass(frozen=True)
class PolicyLocation:
    """Where the pet policy is, and how sure we are.

    ``text_start``/``text_end`` index into ``DomSnapshot.text`` so a test can
    assert on the exact block without a browser. ``selector`` is what the
    driver scrolls to.
    """

    selector: str
    matched_anchors: Tuple[str, ...]
    score: int
    text_excerpt: str
    text_start: int = -1
    text_end: int = -1
    confidence: str = CONFIDENCE_MEDIUM

    def to_dict(self) -> dict:
        return {"selector": self.selector,
                "matched_anchors": list(self.matched_anchors),
                "score": self.score, "text_excerpt": self.text_excerpt,
                "text_start": self.text_start, "text_end": self.text_end,
                "confidence": self.confidence}


@dataclass(frozen=True)
class BoxModel:
    """An element's position in page coordinates, plus the scroll offset in
    force when it was read. Geometry, not image analysis, is how this sprint
    proves the policy was in frame."""

    x: float
    y: float
    width: float
    height: float
    scroll_x: float = 0.0
    scroll_y: float = 0.0

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width,
                "height": self.height,
                "scroll_x": self.scroll_x, "scroll_y": self.scroll_y}

    def viewport_rect(self) -> Tuple[float, float]:
        """Top and bottom of this box relative to the visible viewport."""
        top = self.y - self.scroll_y
        return (top, top + self.height)


@dataclass(frozen=True)
class CaptureArtifacts:
    """What one successful hotel produced."""

    hotel_id: str
    json_path: str
    png_path: str
    html_sha256: str
    text_sha256: str
    png_sha256: str
    png_width: int = 0
    png_height: int = 0
    citable_url: str = ""
    policy: Optional[PolicyLocation] = None
    policy_box: Optional[BoxModel] = None
    interaction_log: Tuple[dict, ...] = ()
    warnings: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "hotel_id": self.hotel_id,
            "json_path": self.json_path, "png_path": self.png_path,
            "html_sha256": self.html_sha256, "text_sha256": self.text_sha256,
            "png_sha256": self.png_sha256,
            "png_width": self.png_width, "png_height": self.png_height,
            "citable_url": self.citable_url,
            "policy": self.policy.to_dict() if self.policy else None,
            "policy_box": self.policy_box.to_dict() if self.policy_box else None,
            "interaction_log": [dict(s) for s in self.interaction_log],
            "warnings": list(self.warnings),
        }

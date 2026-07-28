"""PTF-WORKERS-005 -- browser-rendered capture orchestration.

Converts an exact official URL (typically one PTF-WORKERS-004 discovered) into
hash-bound, verbatim-quotable official evidence, by driving
``BrowserPageFetcher`` through the unchanged ``retrieve_official_source`` seam.

Two responsibilities live here and nowhere else:

1. **Parent-then-child capture.** A policy sub-page such as ``/amenities``
   frequently states the pet policy while naming neither the street address nor
   the phone number, so ``assess_identity`` cannot confirm it in isolation. We
   therefore capture the PARENT property page first, and offer it as an
   identity anchor only if it independently classifies EXACT_MATCH. All eight
   approved inheritance conditions are then re-checked inside
   ``source_retrieval.evaluate_inherited_identity`` -- this module supplies
   evidence, it does not grant permission.

2. **Contradiction preservation.** Official pages disagree with themselves more
   often than is comfortable: the Staybridge Columbus-Dublin policy states a
   pet fee "per pet" in one sentence and "per stay" in another, and quotes both
   a $75 and a $150 amount for different stay lengths. Nothing here resolves
   that. ``collect_statements`` returns EVERY match with its offsets, in
   document order, and there is deliberately no first-match-wins path anywhere
   in this module. A single flattened answer is precisely the failure the
   gpt-5.4 research proof produced, and it is what a human reviewer needs to
   see un-flattened.

No model is called, no credential is read, and no production file is written.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.browser_fetch import (
    CAPTURE_METHOD_BROWSER_RENDERED, MODEL_RESEARCH_URN_PREFIX, BrowserCapture,
    BrowserPageFetcher,
)
from scripts.pettripfinder.importer.models import ImportContext
from services.research_workers import source_retrieval as SR

RENDERED_CAPTURE_VERSION = "ptf-workers-005-capture/1.0.0"


# --------------------------------------------------------------------------- #
# Property code.
# --------------------------------------------------------------------------- #

# IHG property URLs carry a five-character property code
# (".../dublin/cmhtc/hoteldetail"). Extracting it deterministically is what
# makes inheritance condition 3 ("same property identifier") checkable rather
# than assumed.
_IHG_CODE_RE = re.compile(r"/hotels/[a-z]{2}/[a-z]{2}/[^/]+/([a-z0-9]{5})/", re.I)


def extract_property_code(url: str) -> str:
    """Deterministic property code from a property URL, or "" when absent.

    Returns "" rather than guessing. An empty code fails inheritance condition
    3, which is the safe direction: no code means no proof the two pages
    describe the same property.
    """
    m = _IHG_CODE_RE.search(url or "")
    return m.group(1).lower() if m else ""


def parent_url_for(child_url: str) -> str:
    """The property page a policy sub-page hangs beneath.

    ``/hoteldetail/amenities`` -> ``/hoteldetail``. Returns "" when the child is
    not beneath a recognizable property page, which correctly prevents any
    inheritance attempt.
    """
    parts = urlsplit(child_url or "")
    path = (parts.path or "").rstrip("/")
    marker = "/hoteldetail"
    idx = path.lower().rfind(marker)
    if idx < 0 or path.lower().endswith(marker):
        return ""
    return "%s://%s%s" % (parts.scheme, parts.netloc, path[:idx + len(marker)])


# --------------------------------------------------------------------------- #
# Contradiction-preserving statement collection.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Statement:
    """One matched policy statement, with its position in the normalized text.

    Offsets are kept so a reviewer can locate the sentence in the exact text
    that was hashed, and so two statements can be shown in document order
    rather than in match order.
    """

    topic: str
    quote: str
    char_start: int
    char_end: int

    def to_dict(self) -> Dict:
        return {"topic": self.topic, "quote": self.quote,
                "char_start": self.char_start, "char_end": self.char_end}


# Topic patterns. Each captures a bounded sentence-ish window around the match
# so the quote stays readable and stays under the 300-char evidence cap.
_TOPIC_PATTERNS: Tuple[Tuple[str, "re.Pattern"], ...] = (
    ("fee_basis_per_pet", re.compile(r"[^.]{0,120}\bper\s+pet\b[^.]{0,120}\.", re.I)),
    ("fee_basis_per_stay", re.compile(r"[^.]{0,120}\bper\s+stay\b[^.]{0,120}\.", re.I)),
    ("fee_basis_per_night", re.compile(r"[^.]{0,120}\bper\s+night\b[^.]{0,120}\.", re.I)),
    # Both money forms matter: official pages write "$75" and "75 dollars"
    # interchangeably, sometimes in the same paragraph, and missing one form
    # would silently hide half of a tiered fee.
    ("fee_amount", re.compile(r"[^.]{0,120}\$\s?\d[\d,\.]*[^.]{0,120}\.", re.I)),
    ("fee_amount", re.compile(r"[^.]{0,120}\b\d[\d,\.]*\s*dollars\b[^.]{0,120}\.", re.I)),
    ("stay_length_tier",
     re.compile(r"[^.]{0,120}\b\d+\s*(?:-|to|–|through)\s*\d+\s*nights?\b[^.]{0,120}\.", re.I)),
    ("stay_length_tier",
     re.compile(r"[^.]{0,120}\b\d+\s*(?:or\s+more|\+)\s*nights?\b[^.]{0,120}\.", re.I)),
    ("nonrefundable", re.compile(r"[^.]{0,120}\bnon-?refundable\b[^.]{0,120}\.", re.I)),
    ("species_dogs", re.compile(r"[^.]{0,120}\bdogs?\b[^.]{0,120}\.", re.I)),
    ("species_cats", re.compile(r"[^.]{0,120}\bcats?\b[^.]{0,120}\.", re.I)),
    ("weight_limit", re.compile(r"[^.]{0,120}\b\d+\s*(?:lbs?|pounds?)\b[^.]{0,120}\.", re.I)),
    ("max_pets", re.compile(r"[^.]{0,120}\b(?:up\s+to|maximum\s+of|no\s+more\s+than)\s+"
                            r"(?:\d+|one|two|three)\b[^.]{0,120}\.", re.I)),
    ("tax", re.compile(r"[^.]{0,120}\bplus\s+tax\b[^.]{0,120}\.", re.I)),
)


def collect_statements(text: str) -> Tuple[Statement, ...]:
    """EVERY matching statement for every topic, in document order.

    No deduplication by topic and no first-match-wins: if a page says "per pet"
    in one place and "per stay" in another, both are returned, and the
    contradiction survives into the artifact where a human can see it.
    """
    found: List[Statement] = []
    seen = set()
    for topic, pattern in _TOPIC_PATTERNS:
        for m in pattern.finditer(text or ""):
            quote = m.group(0).strip()
            if len(quote) > C.EVIDENCE_QUOTE_CAP:
                quote = quote[:C.EVIDENCE_QUOTE_CAP].rstrip()
            key = (topic, m.start(), quote)
            if key in seen:
                continue
            seen.add(key)
            found.append(Statement(topic, quote, m.start(), m.start() + len(quote)))
    return tuple(sorted(found, key=lambda s: (s.char_start, s.topic, s.quote)))


# Topic pairs that are contradictory when both appear. Reported, never resolved.
_CONTRADICTORY_PAIRS = (
    ("fee_basis_per_pet", "fee_basis_per_stay"),
    ("fee_basis_per_pet", "fee_basis_per_night"),
    ("fee_basis_per_stay", "fee_basis_per_night"),
    ("species_cats", "species_dogs"),
)


def detect_contradictions(statements: Sequence[Statement]) -> Tuple[str, ...]:
    """Name every co-occurring contradictory topic pair, plus multi-amount fees.

    Returning a NAME rather than a resolution is the entire point: routing
    turns these into CONTRADICTORY_OFFICIAL_SOURCES and withholds, instead of
    publishing whichever reading happened to be found first.
    """
    topics = {s.topic for s in statements}
    out: List[str] = []
    for a, b in _CONTRADICTORY_PAIRS:
        if a in topics and b in topics:
            out.append("conflicting_%s_vs_%s" % (a, b))
    if len(fee_amounts(statements)) > 1:
        out.append("multiple_fee_amounts:%s" % ",".join(sorted(fee_amounts(statements))))
    return tuple(sorted(set(out)))


_AMOUNT_PATTERNS = (
    re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)"),
    re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\s*dollars\b", re.I),
)


def fee_amounts(statements: Sequence[Statement]) -> Tuple[str, ...]:
    """Every distinct fee amount mentioned, normalized.

    More than one means a tiered or conditional fee. Reporting the SET rather
    than a single number is what stops "$75 for 1-7 nights, $150 for 8+" from
    being flattened into one misleading scalar -- the exact error the model
    research proof made.
    """
    found = set()
    for s in statements:
        if s.topic != "fee_amount":
            continue
        for pattern in _AMOUNT_PATTERNS:
            for m in pattern.findall(s.quote):
                found.add(m.replace(",", "").rstrip("."))
    return tuple(sorted(found))


# --------------------------------------------------------------------------- #
# Capture result.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RenderedCaptureResult:
    listing_key: str
    listing_name: str
    child_url: str
    parent_url: str = ""
    parent_identity: str = ""
    outcome: Optional[SR.RetrievalOutcome] = None
    parent_outcome: Optional[SR.RetrievalOutcome] = None
    child_capture: Optional[BrowserCapture] = None
    parent_capture: Optional[BrowserCapture] = None
    statements: Tuple[Statement, ...] = ()
    contradictions: Tuple[str, ...] = ()
    inheritance_failures: Tuple[str, ...] = ()
    observed_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "rendered_capture_version": RENDERED_CAPTURE_VERSION,
            "listing_key": self.listing_key,
            "listing_name": self.listing_name,
            "child_url": self.child_url,
            "parent_url": self.parent_url,
            "parent_identity": self.parent_identity,
            "capture_method": CAPTURE_METHOD_BROWSER_RENDERED,
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "parent_outcome": self.parent_outcome.to_dict() if self.parent_outcome else None,
            "child_capture": self.child_capture.to_dict() if self.child_capture else None,
            "parent_capture": self.parent_capture.to_dict() if self.parent_capture else None,
            "statements": [s.to_dict() for s in self.statements],
            "contradictions": list(self.contradictions),
            "inheritance_failures": list(self.inheritance_failures),
            "observed_at": self.observed_at,
            "hash_notes": {
                "raw_transport_hash": "sha256 of the pre-JavaScript response body",
                "rendered_dom_hash":
                    "sha256 of the post-JavaScript DOM -- a POINT-IN-TIME "
                    "ATTESTATION, not a reproducibility guarantee",
                "normalized_text_hash":
                    "sha256 of bounded visible text; the evidence anchor every "
                    "quote is validated against",
            },
        }


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #

def capture_rendered_source(
    *,
    expected: SR.ExpectedEntity,
    child_url: str,
    fetcher: BrowserPageFetcher,
    cas,
    observed_at: str,
    assignment_id: str,
    attempt_parent_inheritance: bool = True,
    context: Optional[ImportContext] = None,
) -> RenderedCaptureResult:
    """Capture ONE policy URL, with a parent capture when identity needs it.

    Both pages are fetched through the same ``fetcher`` instance, which is what
    makes "same browser context and run" a fact rather than a claim.
    """
    if child_url.startswith(MODEL_RESEARCH_URN_PREFIX):
        raise ValueError(
            "a MODEL_RESEARCH_REPORT urn is not a page and may not be rendered: %r"
            % child_url)

    base = dict(expected=expected, fetcher=fetcher, cas=cas, observed_at=observed_at,
                context=context, capture_method=SR.CAPTURE_METHOD_BROWSER_RENDERED)

    child = SR.retrieve_official_source(
        assignment_id=assignment_id, source_url=child_url, **base)
    child_capture = fetcher.last_capture

    parent_outcome = None
    parent_capture = None
    parent_identity = ""
    inheritance_failures: Tuple[str, ...] = ()
    resolved_parent_url = ""

    needs_parent = (attempt_parent_inheritance
                    and child.status == SR.ENTITY_MISMATCH
                    and child.identity in (SR.AMBIGUOUS, SR.NOT_ENOUGH_INFORMATION))
    if needs_parent:
        resolved_parent_url = parent_url_for(child.final_url or child_url)
        if resolved_parent_url:
            parent_outcome = SR.retrieve_official_source(
                assignment_id=assignment_id + "-parent",
                source_url=resolved_parent_url, **base)
            parent_capture = fetcher.last_capture
            parent_identity = parent_outcome.identity

            code = (extract_property_code(resolved_parent_url)
                    or extract_property_code(child.final_url or child_url))
            anchor = SR.ParentIdentity(
                parent_url=parent_outcome.final_url or resolved_parent_url,
                parent_identity=parent_outcome.identity,
                property_code=code,
                parent_redirect_chain=parent_outcome.redirect_chain,
                # True by construction: the same fetcher, hence the same browser
                # context, performed both captures inside this one call.
                same_browser_context=True, same_run=True)

            retried = SR.retrieve_official_source(
                assignment_id=assignment_id, source_url=child_url,
                inherited_from=anchor, **base)
            if retried.identity == SR.INHERITED_FROM_PARENT:
                child = retried
                child_capture = fetcher.last_capture
            else:
                _permitted, inheritance_failures = SR.evaluate_inherited_identity(
                    parent=anchor, child_final_url=child.final_url or child_url,
                    child_text="", child_redirect_chain=child.redirect_chain)
        else:
            inheritance_failures = ("child_not_beneath_parent_path",)

    text = ""
    if child.source_document is not None:
        text = child.source_document.content_text
    statements = collect_statements(text)

    return RenderedCaptureResult(
        listing_key=expected.listing_key, listing_name=expected.listing_name,
        child_url=child_url, parent_url=resolved_parent_url,
        parent_identity=parent_identity, outcome=child, parent_outcome=parent_outcome,
        child_capture=child_capture, parent_capture=parent_capture,
        statements=statements, contradictions=detect_contradictions(statements),
        inheritance_failures=inheritance_failures, observed_at=observed_at)

"""Is this page the hotel the queue asked for?

Reuses ``assess_identity`` rather than restating it. There is one definition of
"right hotel" in this codebase and automated capture does not get its own,
looser copy -- a capture is a different *transport* for official page bytes,
never a lower bar.

What this module adds on top is the cheap structural evidence a rendered page
offers that a fetched one may not: JSON-LD ``Hotel`` blocks, and the property
code sitting in the URL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from ..source_retrieval import (
    EXACT_MATCH, IDENTITY_ACCEPTABLE, MISMATCH, URL_SHAPE_PROPERTY,
    URL_SHAPE_SEARCH, ExpectedEntity, assess_identity, classify_url_shape,
    extract_property_code_from_url,
)
from .contracts import DomSnapshot, ObservedIdentity
from .queue import QueueEntry

_HOTEL_TYPES = ("hotel", "lodgingbusiness", "resort", "motel",
                "bedandbreakfast", "hostel")


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _flatten_jsonld(blocks: Sequence[dict]) -> List[dict]:
    """JSON-LD arrives nested in @graph, in arrays, and occasionally both."""
    out: List[dict] = []
    stack: List[object] = list(blocks)
    seen = 0
    while stack and seen < 200:
        node = stack.pop(0)
        seen += 1
        if isinstance(node, dict):
            out.append(node)
            graph = node.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)
        elif isinstance(node, list):
            stack.extend(node)
    return out


def _is_hotel_block(block: dict) -> bool:
    t = block.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(str(x or "").lower().replace(" ", "") in _HOTEL_TYPES for x in types)


def identity_from_jsonld(blocks: Sequence[dict]) -> ObservedIdentity:
    """Pull name / phone / address out of the first Hotel-ish JSON-LD block.

    Defensive throughout: a site that publishes a malformed block should cost us
    the block, not the capture.
    """
    for block in _flatten_jsonld(blocks):
        if not _is_hotel_block(block):
            continue
        addr = block.get("address")
        if not isinstance(addr, dict):
            addr = {}
        return ObservedIdentity(
            name=str(block.get("name") or "").strip(),
            phone=str(block.get("telephone") or "").strip(),
            street=str(addr.get("streetAddress") or "").strip(),
            city=str(addr.get("addressLocality") or "").strip(),
            state=str(addr.get("addressRegion") or "").strip(),
            postal_code=str(addr.get("postalCode") or "").strip(),
            sources=("jsonld",))
    return ObservedIdentity()


def observe_identity(dom: DomSnapshot, *, known_codes: Sequence[str] = ()) -> ObservedIdentity:
    """Everything the page says about which hotel it is.

    The page ``<title>`` is deliberately the weakest source and never overrides
    JSON-LD. A real Hilton capture in the fixture corpus carries the title
    "Embassy Suites by Hilton Columbus Airport" on the Hilton Garden Inn
    Columbus Airport property page -- a stale tag the brand never fixed. Trusting
    titles would have failed that hotel, or worse, mislabelled it.
    """
    observed = identity_from_jsonld(dom.jsonld)
    code = extract_property_code_from_url(dom.final_url, known_codes)
    sources = list(observed.sources)
    if code:
        sources.append("url")
    name = observed.name
    if not name and dom.title:
        name = dom.title.split("|")[0].strip()
        sources.append("title")
    return ObservedIdentity(
        name=name, phone=observed.phone, street=observed.street,
        city=observed.city, state=observed.state,
        postal_code=observed.postal_code, property_code=code,
        sources=tuple(sources))


@dataclass(frozen=True)
class IdentityVerdict:
    ok: bool
    reason: str = ""                 # an EXCEPTION_REASONS key when not ok
    classification: str = ""
    detail: Tuple[str, ...] = ()
    observed: Optional[ObservedIdentity] = None

    def to_dict(self) -> dict:
        return {"ok": self.ok, "reason": self.reason,
                "classification": self.classification,
                "detail": list(self.detail),
                "observed": self.observed.to_dict() if self.observed else None}


def verify_identity(dom: DomSnapshot, entry: QueueEntry,
                    *, observed_at: str = "") -> IdentityVerdict:
    """Full identity gate for one navigated page.

    Order matters: URL shape is judged before content, because a query-driven
    URL is never a stable citation whatever the page says. That ordering is the
    fix PTF-WORKERS-007 established and it is preserved here deliberately.
    """
    known = [entry.expected_property_code] if entry.expected_property_code else []
    observed = observe_identity(dom, known_codes=known)

    shape = classify_url_shape(dom.final_url)
    if shape == URL_SHAPE_SEARCH:
        return IdentityVerdict(False, "SEARCH_URL", detail=("final_url_is_search",),
                               observed=observed)
    if shape != URL_SHAPE_PROPERTY:
        return IdentityVerdict(False, "REDIRECTED_OFF_PROPERTY",
                               detail=("url_shape:%s" % shape,), observed=observed)

    if entry.expected_property_code:
        if observed.property_code.lower() != entry.expected_property_code.lower():
            return IdentityVerdict(
                False, "PROPERTY_CODE_MISMATCH",
                detail=("expected:%s" % entry.expected_property_code,
                        "found:%s" % (observed.property_code or "none")),
                observed=observed)

    # Hand the page to the same assessor automatic retrieval uses.
    expected = ExpectedEntity(
        listing_key=entry.listing_key, listing_name=entry.hotel_name,
        address=entry.expected_address, city=entry.expected_city,
        state=entry.expected_state, postal_code=entry.expected_postal_code,
        phone=entry.expected_phone, website_url=entry.official_url)

    from scripts.pettripfinder.importer import constants as C
    from scripts.pettripfinder.importer.models import SourceSnapshot

    pseudo = SourceSnapshot(
        requested_url=entry.official_url, final_url=dom.final_url,
        observed_at=observed_at, http_status=200, content_type="text/html",
        redirect_chain=(), page_title=dom.title,
        canonical_url=dom.canonical_url, response_header_subset=(),
        raw_content_hash="", normalized_text_hash="",
        normalized_text=dom.text, extraction_version=C.EXTRACTION_VERSION,
        fetch_warnings=(), source_relationship=C.REL_EXACT_ENTITY_DOMAIN)
    assessed = assess_identity(pseudo, expected)

    if assessed.classification not in IDENTITY_ACCEPTABLE:
        # Distinguish "this is a different hotel" from "this page did not say
        # enough to tell" -- the first is never worth a retry, the second is
        # exactly what a human with the extension can resolve.
        #
        # The signal is the classification, not whether we scraped a name.
        # MISMATCH is the assessor actively contradicting the queue; AMBIGUOUS
        # and NOT_ENOUGH_INFORMATION are it declining to commit. Hilton's
        # /hotel-info/ pages land in the second group -- their JSON-LD carries
        # a name but no address or phone -- and calling that a mismatch would
        # tell the operator we had proof of the wrong hotel when we had none.
        reason = ("IDENTITY_MISMATCH" if assessed.classification == MISMATCH
                  else "IDENTITY_UNVERIFIABLE")
        return IdentityVerdict(False, reason,
                               classification=assessed.classification,
                               detail=tuple(assessed.reasons), observed=observed)

    return IdentityVerdict(True, "", classification=assessed.classification,
                           detail=tuple(assessed.reasons), observed=observed)

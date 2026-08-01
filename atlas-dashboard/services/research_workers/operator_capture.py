"""PTF-WORKERS-003 -- operator-assisted official-page capture.

Why this exists. Tier-1 static retrieval reaches Sonesta but not Red Roof,
IHG or Hilton property pages: those sit behind Akamai edge protection that
returns 403 to any non-browser-fingerprinted client (Red Roof and IHG refuse
even ``/robots.txt``). A probe confirmed an ordinary headless Chromium is
blocked identically, and every technique that would defeat the fingerprint --
stealth plugins, UA/TLS spoofing, proxy rotation, challenge solving -- is
forbidden by the mission and by the importer's own "no browser fingerprint,
no stealth" doctrine.

The lawful route is a human. A founder opening a hotel page in their everyday
Chrome is an ordinary visitor, not an automated client, and no access control
is touched. This module accepts what that browser already rendered and feeds
it into the SAME pipeline automatic retrieval uses -- importer normalization
and hashing, property-identity verification, brand-vs-property applicability,
SourceDocument, validator, routing, operator approval. The operator supplies
*pages*, never facts: no policy value is ever typed by a human here.

Nothing in this module fetches anything. It has no network code at all.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.source_snapshot import (
    detect_javascript_only, extract_canonical, extract_title, normalize_html_to_text,
)
from services.research_workers import vocabulary as V
from services.research_workers.contracts import SourceDocument
from services.research_workers.contracts import content_hash as contract_content_hash
from services.research_workers.source_retrieval import (
    EXACT_MATCH, IDENTITY_ACCEPTABLE, URL_SHAPE_PROPERTY, URL_SHAPE_SEARCH,
    ExpectedEntity, PolicyCandidate, assess_identity, classify_url_shape,
    discover_policy_candidates, extract_property_code_from_url,
    looks_like_directory_page,
)

CAPTURE_SCHEMA = "ptf-official-capture/1.0"
CAPTURE_MODULE_VERSION = "ptf-workers-003-capture/1.0.0"

# What a captured page IS, relative to the hotel being evidenced. Promoted from
# bare string literals to named constants in PTF-WORKERS-007, when a fourth
# role was added and the set stopped being self-evident at the call site.
SOURCE_ROLE_PROPERTY = "PROPERTY_POLICY_SOURCE"
SOURCE_ROLE_BRAND = "BRAND_POLICY_SOURCE"
SOURCE_ROLE_SEARCH_SURFACE = "SEARCH_RESULTS_SURFACE"
# A search surface that has been BOUND to a property-page identity capture. It
# is not promoted to PROPERTY: the distinction stays visible in every artifact,
# so a reader can always tell a page that identified itself from one that
# borrowed its identity.
SOURCE_ROLE_PAIRED_POLICY = "PAIRED_POLICY_SURFACE"

# Queue directory names (under the gitignored worker-run root).
OPERATOR_CAPTURE = "operator_capture"
QUEUE = "queue"
INCOMING = "incoming"
ACCEPTED = "accepted"
REJECTED = "rejected"
CAPTURE_SUBDIRS = (QUEUE, INCOMING, ACCEPTED, REJECTED)

# Capture statuses.
PENDING_CAPTURE = "PENDING_CAPTURE"
CAPTURE_RECEIVED = "CAPTURE_RECEIVED"
CAPTURE_ACCEPTED = "CAPTURE_ACCEPTED"
CAPTURE_REJECTED = "CAPTURE_REJECTED"
ENTITY_MISMATCH = "ENTITY_MISMATCH"
NOT_USEFUL = "NOT_USEFUL"
SUPERSEDED = "SUPERSEDED"
CAPTURE_STATUSES = frozenset({
    PENDING_CAPTURE, CAPTURE_RECEIVED, CAPTURE_ACCEPTED, CAPTURE_REJECTED,
    ENTITY_MISMATCH, NOT_USEFUL, SUPERSEDED,
})

# Retrieval outcomes that justify asking a human to open the page. Anything
# else -- an unsafe URL, an unrelated domain, an entity mismatch -- must never
# become a capture job: we would be asking the operator to legitimise evidence
# the automatic gates already refused.
CAPTURE_WORTHY = frozenset({"ACCESS_BLOCKED", "RENDER_REQUIRED",
                            "BROWSER_ACCESS_BLOCKED", "PROPERTY_PAGE_NOT_FOUND"})
NEVER_CAPTURE = frozenset({"REJECTED_UNSAFE_URL", "ENTITY_MISMATCH",
                           "UNSUPPORTED_CONTENT"})

# Minimum rendered text for a capture to carry any policy signal at all. A
# 32-byte JS shell (the Homewood case) must not pass as evidence.
MIN_USEFUL_TEXT_BYTES = 400

# Deterministic markers for pages a capture must never be accepted from. These
# detect a blocked/interstitial page the operator captured by accident; they
# are NOT used to work around anything.
_DENIED_MARKERS = ("access denied", "you don't have permission",
                   "request blocked", "403 forbidden", "error 403")
_CHALLENGE_MARKERS = ("captcha", "recaptcha", "hcaptcha", "are you a human",
                      "verify you are human", "unusual traffic",
                      "security check", "please enable javascript and cookies")
_LOGIN_MARKERS = ("sign in to continue", "please sign in", "log in to continue",
                  "enter your password", "member sign in", "create an account to view")

# Keys a capture file must never contain. The extension is written not to
# collect them; ingestion refuses the file if any appear anyway, so a
# hand-edited or future-modified capture cannot smuggle them in.
FORBIDDEN_CAPTURE_KEYS = ("cookies", "cookie", "localstorage", "local_storage",
                          "sessionstorage", "session_storage", "headers",
                          "authorization", "token", "tokens", "password",
                          "passwords", "formdata", "form_data", "formvalues",
                          "history", "credentials", "payment", "autofill")


class CaptureError(ValueError):
    """Raised when a capture file is structurally unusable."""


# --------------------------------------------------------------------------- #
# Queue records.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CaptureJob:
    """One hotel awaiting an operator capture. Carries only what the operator
    needs to find and visually confirm the right page."""

    assignment_id: str
    listing_key: str
    listing_name: str
    expected_address: str
    expected_city: str
    expected_state: str
    expected_postal_code: str
    expected_phone: str
    official_url: str
    alternate_urls: Tuple[str, ...] = ()
    failure_reason: str = ""
    retrieval_status: str = ""
    required_fields: Tuple[str, ...] = ()
    status: str = PENDING_CAPTURE
    schema: str = CAPTURE_SCHEMA

    def to_dict(self) -> dict:
        d = asdict(self)
        d["alternate_urls"] = list(self.alternate_urls)
        d["required_fields"] = list(self.required_fields)
        return dict(sorted(d.items()))


def build_capture_job(outcome, expected: ExpectedEntity,
                      required_fields: Sequence[str] = ()) -> Optional[CaptureJob]:
    """Turn a failed retrieval into a capture job -- or refuse to.

    Returns None when the failure is one a human must not be asked to work
    around (unsafe URL, wrong entity, unsupported content).
    """
    status = getattr(outcome, "status", "")
    if status in NEVER_CAPTURE or status not in CAPTURE_WORTHY:
        return None
    alternates = tuple(c.url for c in getattr(outcome, "policy_candidates", ())[:5])
    return CaptureJob(
        assignment_id=outcome.assignment_id,
        listing_key=expected.listing_key,
        listing_name=expected.listing_name,
        expected_address=expected.address,
        expected_city=expected.city,
        expected_state=expected.state,
        expected_postal_code=expected.postal_code,
        expected_phone=expected.phone,
        official_url=expected.website_url or outcome.initial_url,
        alternate_urls=alternates,
        failure_reason=outcome.failure_reason or outcome.importer_reason,
        retrieval_status=status,
        required_fields=tuple(required_fields or V.POLICY_FIELDS),
        status=PENDING_CAPTURE,
    )


# --------------------------------------------------------------------------- #
# Capture file validation.
# --------------------------------------------------------------------------- #

_REQUIRED_CAPTURE_FIELDS = ("schema", "captured_at", "final_url", "title",
                            "html", "text", "extension_version")


def _scan_forbidden(node, path="") -> List[str]:
    """Depth-first search for any forbidden key anywhere in the capture."""
    found: List[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            kl = str(k).lower().replace("-", "").replace("_", "")
            for bad in FORBIDDEN_CAPTURE_KEYS:
                if kl == bad.replace("_", ""):
                    found.append("%s%s" % (path, k))
            found.extend(_scan_forbidden(v, "%s%s." % (path, k)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found.extend(_scan_forbidden(v, "%s[%d]." % (path, i)))
    return found


def validate_capture(payload: dict) -> Tuple[bool, str]:
    """Structural + privacy validation. Returns ``(ok, reason)``."""
    if not isinstance(payload, dict):
        return (False, "capture_not_an_object")
    if payload.get("schema") != CAPTURE_SCHEMA:
        return (False, "unsupported_schema:%s" % payload.get("schema"))
    for f in _REQUIRED_CAPTURE_FIELDS:
        if f not in payload:
            return (False, "missing_field:%s" % f)
    if not str(payload.get("html") or "").strip():
        return (False, "empty_html")
    forbidden = _scan_forbidden(payload)
    if forbidden:
        return (False, "forbidden_keys:%s" % ",".join(sorted(forbidden)[:5]))
    url = str(payload.get("final_url") or "")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return (False, "unsafe_scheme:%s" % (parts.scheme or "none"))
    if "@" in (parts.netloc or ""):
        return (False, "embedded_credentials")
    if not parts.hostname:
        return (False, "no_host")
    return (True, "")


def _registrable(host: str) -> str:
    bits = (host or "").lower().split(".")
    return ".".join(bits[-2:]) if len(bits) >= 2 else (host or "").lower()


def host_is_authorized(captured_url: str, authorized_urls: Sequence[str]) -> bool:
    """The capture must come from the same registrable domain as an authorized
    official URL. This is what stops an aggregator page (or any unrelated site)
    entering the pipeline as official evidence."""
    got = _registrable(urlsplit(captured_url).hostname or "")
    if not got:
        return False
    return any(got == _registrable(urlsplit(u).hostname or "")
               for u in authorized_urls if u)


def _page_block_reason(text: str) -> str:
    low = " ".join((text or "").lower().split())
    for m in _CHALLENGE_MARKERS:
        if m in low:
            return "captcha_or_challenge_page"
    for m in _DENIED_MARKERS:
        if m in low:
            return "access_denied_page"
    for m in _LOGIN_MARKERS:
        if m in low:
            return "login_required_page"
    return ""


#: A visible-text field shorter than this is not a rendered page. Below it the
#: normalized HTML is the only usable evidence, so the check falls back.
MIN_VISIBLE_TEXT_BYTES_FOR_BLOCK_CHECK = 200


def page_block_reason_for_capture(visible_text: str, normalized_text: str) -> Tuple[str, str]:
    """Decide whether a captured page is a wall, and say which text decided it.

    PTF-CAPTURE-003D. This used to run over the NORMALIZED HTML only, which
    includes markup a visitor never sees. IHG ships a dormant sign-in widget in
    every page's chrome -- "your session has expired. please sign in to your
    profile" -- so a fully public property page, whose pet policy, address and
    phone were all plainly rendered and photographed, was rejected as
    ``login_required_page``. The string was in the document; it was never on
    the screen.

    A wall is a thing a *reader* is shown. So when the capture carries rendered
    visible text, that is what decides. The normalized HTML remains the
    fallback for captures that have no usable rendered text -- where it is the
    only evidence there is, and where erring toward rejection is correct.

    Returns ``(reason, source)``; ``reason`` is "" when the page is not a wall.
    """
    visible = visible_text or ""
    usable = len(visible.strip().encode("utf-8")) >= MIN_VISIBLE_TEXT_BYTES_FOR_BLOCK_CHECK
    if usable:
        return (_page_block_reason(visible), "visible_text")
    return (_page_block_reason(normalized_text or ""), "normalized_html_fallback")


# --------------------------------------------------------------------------- #
# Ingestion result.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class IngestionOutcome:
    assignment_id: str
    listing_key: str
    listing_name: str
    status: str
    captured_url: str = ""
    canonical_url: str = ""
    title: str = ""
    identity: str = ""
    identity_reasons: Tuple[str, ...] = ()
    source_role: str = ""
    policy_applicable: bool = False
    raw_content_hash: str = ""
    normalized_text_hash: str = ""
    normalized_text_bytes: int = 0
    jsonld_blocks: int = 0
    policy_candidates: Tuple[PolicyCandidate, ...] = ()
    warnings: Tuple[str, ...] = ()
    failure_reason: str = ""
    source_document: Optional[SourceDocument] = None

    @property
    def accepted(self) -> bool:
        return self.status == CAPTURE_ACCEPTED and self.source_document is not None

    def to_dict(self) -> dict:
        """Sanitized artifact. Records hashes, classifications and sizes --
        never the captured HTML or page text."""
        return {
            "capture_module_version": CAPTURE_MODULE_VERSION,
            "assignment_id": self.assignment_id,
            "listing_key": self.listing_key,
            "listing_name": self.listing_name,
            "status": self.status,
            "captured_url": self.captured_url,
            "canonical_url": self.canonical_url,
            "title": self.title,
            "identity": self.identity,
            "identity_reasons": list(self.identity_reasons),
            "source_role": self.source_role,
            "policy_applicable": self.policy_applicable,
            "raw_content_hash": self.raw_content_hash,
            "normalized_text_hash": self.normalized_text_hash,
            "normalized_text_bytes": self.normalized_text_bytes,
            "jsonld_blocks": self.jsonld_blocks,
            "policy_candidates": [
                {"url": c.url, "score": c.score, "matched_terms": list(c.matched_terms),
                 "anchor_text": c.anchor_text} for c in self.policy_candidates],
            "warnings": list(self.warnings),
            "failure_reason": self.failure_reason,
            "accepted": self.accepted,
            "source_document": ({
                "source_url": self.source_document.source_url,
                "source_type": self.source_document.source_type,
                "retrieved_at": self.source_document.retrieved_at,
                "title": self.source_document.title,
                "content_hash": self.source_document.content_hash,
                "retrieval_status": self.source_document.retrieval_status,
                "content_text_bytes": len(
                    (self.source_document.content_text or "").encode("utf-8")),
            } if self.source_document is not None else None),
        }


# Query parameters that must never reach a published citation: a browsing
# session identifier, and advertising click ids that say how the operator got
# there rather than what the page is.
_PRIVATE_QUERY_KEYS = ("sessiontoken", "gclid", "gbraid", "wbraid", "fbclid",
                       "msclkid", "wt.mc_id", "gclsrc", "gad_source",
                       "gad_campaignid", "utm_source", "utm_medium",
                       "utm_campaign", "utm_term", "utm_content")


def url_carries_private_params(url: str) -> bool:
    """Does this URL carry a session or ad-tracking parameter?"""
    query = (urlsplit(url or "").query or "").lower()
    return any(("%s=" % k) in query or query.startswith("%s=" % k)
               for k in _PRIVATE_QUERY_KEYS)


def _citable_url(captured_url: str, canonical_url: str) -> str:
    """The URL safe to publish as this page's official source.

    Prefers the page's own canonical URL, which is clean by construction. Falls
    back to the captured URL when no canonical is offered or when the canonical
    names a DIFFERENT path -- borrowing another page's address to tidy a query
    string would misstate which page was actually read.
    """
    cap, can = urlsplit(captured_url or ""), urlsplit(canonical_url or "")
    if not canonical_url:
        return captured_url
    same_place = (cap.hostname or "").lower() == (can.hostname or "").lower() and \
        (cap.path or "/").rstrip("/") == (can.path or "/").rstrip("/")
    return canonical_url if same_place else captured_url


def _fail(job: CaptureJob, status: str, reason: str, **kw) -> IngestionOutcome:
    return IngestionOutcome(
        assignment_id=job.assignment_id, listing_key=job.listing_key,
        listing_name=job.listing_name, status=status, failure_reason=reason, **kw)


def ingest_capture(payload: dict, job: CaptureJob,
                   *, observed_at: str = "") -> IngestionOutcome:
    """Validate an operator capture and convert it into a SourceDocument.

    Every gate automatic retrieval applies is applied here too. A capture is
    a different *transport* for official page bytes -- never a lower bar.
    """
    ok, reason = validate_capture(payload)
    if not ok:
        return _fail(job, CAPTURE_REJECTED, reason)

    captured_url = str(payload["final_url"])
    authorized = [job.official_url] + list(job.alternate_urls)
    if not host_is_authorized(captured_url, authorized):
        return _fail(job, CAPTURE_REJECTED,
                     "unauthorized_domain:%s" % (urlsplit(captured_url).hostname or "?"),
                     captured_url=captured_url)

    html = str(payload["html"])
    raw_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
    normalized_text, truncated = normalize_html_to_text(html)
    text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    text_bytes = len(normalized_text.encode("utf-8"))

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup) or str(payload.get("title") or "")
    canonical = extract_canonical(soup) or str(payload.get("canonical_url") or "")
    jsonld = payload.get("jsonld") or []

    warnings: List[str] = []
    if truncated:
        warnings.append("normalized_text_truncated_50kb")

    common = dict(captured_url=captured_url, canonical_url=canonical, title=title,
                  raw_content_hash=raw_hash, normalized_text_hash=text_hash,
                  normalized_text_bytes=text_bytes,
                  jsonld_blocks=len(jsonld) if isinstance(jsonld, list) else 0)

    # PTF-CAPTURE-003D. Judge the page a reader saw, not the markup shipped
    # with it. The capture's own rendered text decides when it is usable; the
    # normalized HTML remains the fallback when it is not.
    blocked, block_source = page_block_reason_for_capture(
        str(payload.get("text") or ""), normalized_text)
    if blocked:
        return _fail(job, CAPTURE_REJECTED, blocked, **common)
    if block_source == "normalized_html_fallback":
        warnings.append("block_check_used_normalized_html")

    if text_bytes < MIN_USEFUL_TEXT_BYTES or detect_javascript_only(soup, normalized_text):
        return _fail(job, NOT_USEFUL,
                     "insufficient_rendered_text:%d_bytes" % text_bytes, **common)

    expected = ExpectedEntity(
        listing_key=job.listing_key, listing_name=job.listing_name,
        address=job.expected_address, city=job.expected_city,
        state=job.expected_state, postal_code=job.expected_postal_code,
        phone=job.expected_phone, website_url=job.official_url)

    # Reuse the retrieval seam's identity assessment verbatim -- one definition
    # of "is this the right hotel", shared by both transports.
    from scripts.pettripfinder.importer.models import SourceSnapshot
    pseudo = SourceSnapshot(
        requested_url=captured_url, final_url=captured_url,
        observed_at=observed_at or str(payload.get("captured_at") or ""),
        http_status=200, content_type="text/html", redirect_chain=(),
        page_title=title, canonical_url=canonical, response_header_subset=(),
        raw_content_hash=raw_hash, normalized_text_hash=text_hash,
        normalized_text=normalized_text, extraction_version=C.EXTRACTION_VERSION,
        fetch_warnings=tuple(warnings), source_relationship=C.REL_EXACT_ENTITY_DOMAIN)
    identity = assess_identity(pseudo, expected)

    candidates = discover_policy_candidates(html, captured_url)
    directory = looks_like_directory_page(captured_url, candidates)

    common.update(identity=identity.classification,
                  identity_reasons=identity.reasons,
                  policy_candidates=candidates)

    if identity.classification not in IDENTITY_ACCEPTABLE:
        return _fail(job, ENTITY_MISMATCH,
                     "identity_%s" % identity.classification.lower(), **common)

    # Same brand-vs-property rule as automatic retrieval, plus the URL-shape
    # check (PTF-WORKERS-007). The link-graph test alone passed a search page:
    # /search/findHotels.mi links to /en-us/hotels/..., which is not beneath
    # /search, so no siblings were counted and a card carrying one hotel's
    # name, address and phone classified EXACT_MATCH. The search URL then
    # became the cited official source for that hotel's policy. Shape is
    # judged first because a query-driven URL is never a stable citation,
    # whatever its content happens to say.
    shape = classify_url_shape(captured_url)
    if shape == URL_SHAPE_SEARCH:
        role = SOURCE_ROLE_SEARCH_SURFACE
        applicable = False
        warnings.append("search_results_page")
    elif identity.classification == EXACT_MATCH and not directory:
        role = SOURCE_ROLE_PROPERTY
        applicable = True
    else:
        role = SOURCE_ROLE_BRAND
        applicable = False
        warnings.append("directory_listing_page" if directory else "not_property_specific")

    if not applicable:
        return IngestionOutcome(
            assignment_id=job.assignment_id, listing_key=job.listing_key,
            listing_name=job.listing_name, status=NOT_USEFUL,
            source_role=role, policy_applicable=False,
            warnings=tuple(warnings),
            failure_reason="capture_is_not_property_specific", **common)

    # PTF-WORKERS-006 defect fixes, both found by finally calling validate():
    #   * source_type carried the IMPORTER's relationship slug
    #     (C.REL_EXACT_ENTITY_DOMAIN), which is not in V.SOURCE_TYPES; and
    #   * content_hash carried a BARE hex digest where the contract's canonical
    #     form is "sha256:<hex>".
    # Either alone raised ContractError the first time a real assignment was
    # built from a capture. The type is now MANUAL_OFFICIAL_ATTESTATION, which
    # is what an operator-transported page has always actually been.
    # PTF-CAPTURE-004. CITE the canonical URL, not the address bar. A capture's
    # final_url carries whatever took the operator to the page -- Hilton
    # captures arrived with sessionToken=<uuid> from the operator's own browsing
    # session and gclid/gbraid Google Ads click ids. That URL becomes the
    # public "official source" citation and the /go/official-website target, so
    # publishing it would leak a personal session identifier and a marketing
    # click id onto a consumer page.
    #
    # The canonical URL is the page's own statement of its address, and it is
    # used ONLY when it points at the same property -- a canonical that
    # redirects elsewhere is exactly the brand-vs-property confusion this
    # pipeline refuses, so it falls back to the captured URL rather than
    # trusting a mismatch.
    cite_url = _citable_url(captured_url, canonical)
    doc = SourceDocument(
        source_url=cite_url, source_type=V.SOURCE_MANUAL_OFFICIAL_ATTESTATION,
        retrieved_at=observed_at or str(payload.get("captured_at") or ""),
        title=title, content_text=normalized_text,
        content_hash=contract_content_hash(normalized_text),
        retrieval_status=V.RETRIEVAL_OK)

    return IngestionOutcome(
        assignment_id=job.assignment_id, listing_key=job.listing_key,
        listing_name=job.listing_name, status=CAPTURE_ACCEPTED,
        source_role=role, policy_applicable=True, warnings=tuple(warnings),
        source_document=doc, **common)


# --------------------------------------------------------------------------- #
# PTF-WORKERS-007 -- PAIRED OFFICIAL EVIDENCE.
#
# Some brands put a property's identity on one official page and its pet policy
# on another. Marriott is the case in hand: the property page at
# /en-us/hotels/<code>-<slug>/overview/ proves WHO the hotel is, while the
# expanded card on /search/findHotels.mi states the policy in a form an
# operator can read and photograph in seconds.
#
# Neither capture is an attestation by itself. The search page cannot identify
# a property (its URL is a query, and it lists dozens of hotels); the property
# page identifies one but may not show the policy above the fold. What makes
# the pair usable is the BINDING between them -- and the binding, not the
# operator's say-so, is what this module records and re-checks.
#
# The binding is deliberately expensive to satisfy: all four strong signals
# must match, the policy must be contiguous with the identity inside a single
# expanded card, and exactly one card may be open. Anything less fails closed.
# Even when it succeeds the result is never READY -- it routes REVIEW and needs
# an explicit, hash-bound approval, because "these two pages are about the same
# hotel" is an inference, and an inference is exactly what a wrong pet policy
# on the wrong property would turn on.
# --------------------------------------------------------------------------- #

# Every condition, mapped to the slug recorded when it FAILS. Data rather than
# a chain of ifs, so an artifact can state exactly what blocked a pairing.
PAIRING_CONDITIONS = (
    "identity_capture_not_property_specific",
    "identity_capture_not_exact_match",
    "different_source_family",
    "name_not_matched",
    "address_not_matched",
    "phone_not_matched",
    "property_code_unconfirmed",
    "policy_not_contiguous_with_identity",
    "multiple_expanded_cards",
    "captures_not_same_session",
    "duplicate_capture",
    "policy_capture_has_no_policy_text",
)

# The four signals that must ALL be present. No scoring, no "three of four":
# each one alone is forgeable or coincidental, and a hotel chain reuses names
# and phone formats across properties.
REQUIRED_BINDING_SIGNALS = ("name_exact", "address_exact", "phone_exact", "property_code")

# A bound card must hold identity and policy within this many characters of one
# another. Sized from the real Marriott card (address at ~730, pet block at
# ~1094 -- a span of ~360). Two thousand leaves generous headroom while still
# excluding "somewhere else on a 9,900-character page".
MAX_CARD_SPAN_CHARS = 2000
# Captures further apart than this are not one session. Half an hour is long
# enough for a careful operator and short enough that the page cannot have been
# re-queried into a different result set unnoticed.
MAX_CAPTURE_GAP_SECONDS = 1800


def _digits(value: str) -> str:
    """Phone comparison ignores punctuation and a leading country code."""
    d = re.sub(r"\D", "", value or "")
    return d[1:] if len(d) == 11 and d.startswith("1") else d


def _squash(value: str) -> str:
    """Collapse whitespace and case for tolerant-but-exact text matching.

    'Drive' vs 'Dr' is NOT normalized away: an address that differs in wording
    is an address the operator should look at, not one this code should guess
    about.
    """
    return " ".join((value or "").split()).lower()


def _parse_iso_seconds(stamp: str) -> Optional[int]:
    """Seconds since epoch from an ISO-8601 stamp, or None if unparseable."""
    from datetime import datetime
    s = (stamp or "").strip().replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(s).timestamp())
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class PairedEvidence:
    """The recorded binding between an identity capture and a policy capture.

    This is evidence, not permission: every field is re-derivable from the two
    capture files, and ``bind_paired_captures`` re-checks all of it rather than
    trusting anything asserted here.
    """

    identity_capture_url: str
    identity_text_hash: str
    policy_capture_url: str
    policy_text_hash: str
    matched_signals: Tuple[str, ...] = ()
    property_code: str = ""
    card_span_chars: int = 0
    capture_gap_seconds: int = 0
    binding_note: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["matched_signals"] = list(self.matched_signals)
        return dict(sorted(d.items()))


def _one_expanded_card(policy_text: str, listing_name: str) -> Tuple[bool, int]:
    """Is exactly one property card expanded in this search capture?

    An expanded card carries a 'Property Information' block. Two of them means
    the operator had two hotels open and the screenshot cannot say which one
    the policy belonged to.
    """
    blocks = len(re.findall(r"property information", policy_text, re.I))
    return (blocks == 1, blocks)


def bind_paired_captures(*, identity: IngestionOutcome, policy_payload: dict,
                         job: CaptureJob,
                         identity_captured_at: str = "",
                         policy_captured_at: str = "") -> Tuple[Optional[PairedEvidence],
                                                                Tuple[str, ...]]:
    """Bind a policy capture to an identity capture, or explain why not.

    Fail-closed and TOTAL: every condition is evaluated and every failure is
    returned, so an operator sees the complete reason a pairing was refused
    rather than only the first problem found.
    """
    failures: List[str] = []

    # -- Capture A must be a property page that proved its own identity.
    id_url = identity.captured_url or ""
    if classify_url_shape(id_url) != URL_SHAPE_PROPERTY:
        failures.append("identity_capture_not_property_specific")
    if identity.identity != EXACT_MATCH:
        failures.append("identity_capture_not_exact_match")

    # -- Capture B: normalize once, then test everything against it.
    policy_html = str(policy_payload.get("html") or "")
    policy_url = str(policy_payload.get("final_url") or "")
    policy_text, _ = normalize_html_to_text(policy_html)
    policy_hash = hashlib.sha256(policy_text.encode("utf-8")).hexdigest()
    flat = _squash(policy_text)

    if _registrable(urlsplit(id_url).hostname or "") != _registrable(
            urlsplit(policy_url).hostname or ""):
        failures.append("different_source_family")

    if identity.normalized_text_hash and identity.normalized_text_hash == policy_hash:
        # The same file passed twice is not corroboration.
        failures.append("duplicate_capture")

    # -- The four strong signals, all required.
    signals: List[str] = []
    name = _squash(job.listing_name)
    if name and name in flat:
        signals.append("name_exact")
    else:
        failures.append("name_not_matched")

    address = _squash(job.expected_address)
    if address and address in flat:
        signals.append("address_exact")
    else:
        failures.append("address_not_matched")

    phone = _digits(job.expected_phone)
    if phone and phone in _digits(policy_text):
        signals.append("phone_exact")
    else:
        failures.append("phone_not_matched")

    known = [c for c in (extract_property_code_from_url(id_url),) if c]
    code = extract_property_code_from_url(id_url)
    in_policy = bool(code) and (code in policy_url.lower() or code in flat)
    if code and in_policy:
        signals.append("property_code")
    else:
        failures.append("property_code_unconfirmed")

    # -- Exactly one card open, and the policy contiguous with the identity.
    single, blocks = _one_expanded_card(policy_text, job.listing_name)
    if not single:
        failures.append("multiple_expanded_cards")

    span = 0
    pet_at = flat.find("pet policy")
    if pet_at < 0:
        failures.append("policy_capture_has_no_policy_text")
    else:
        anchors = [flat.find(address) if address else -1,
                   flat.find(name) if name else -1]
        anchors = [a for a in anchors if a >= 0]
        if not anchors:
            failures.append("policy_not_contiguous_with_identity")
        else:
            span = max(abs(pet_at - a) for a in anchors)
            if span > MAX_CARD_SPAN_CHARS:
                failures.append("policy_not_contiguous_with_identity")

    # -- Same session.
    gap = 0
    t_a = _parse_iso_seconds(identity_captured_at)
    t_b = _parse_iso_seconds(policy_captured_at)
    if t_a is None or t_b is None:
        failures.append("captures_not_same_session")
    else:
        gap = abs(t_b - t_a)
        if gap > MAX_CAPTURE_GAP_SECONDS:
            failures.append("captures_not_same_session")

    if failures:
        return (None, tuple(sorted(set(failures))))

    note = (
        "Policy text captured from %s and bound to the property identity proved at "
        "%s. Binding signals: %s. Identity and policy appear within %d characters "
        "of one another inside a single expanded card; captures are %d seconds "
        "apart in one session." % (
            policy_url, id_url, ", ".join(sorted(signals)), span, gap)
    )
    return (PairedEvidence(
        identity_capture_url=id_url,
        identity_text_hash=identity.normalized_text_hash,
        policy_capture_url=policy_url,
        policy_text_hash=policy_hash,
        matched_signals=tuple(sorted(signals)),
        property_code=code,
        card_span_chars=span,
        capture_gap_seconds=gap,
        binding_note=note), ())


def ingest_paired_capture(*, identity_payload: dict, policy_payload: dict,
                          job: CaptureJob,
                          observed_at: str = "") -> Tuple[IngestionOutcome,
                                                          Optional[PairedEvidence],
                                                          Tuple[str, ...]]:
    """Ingest an identity capture + a policy capture as ONE evidence package.

    Returns ``(outcome, paired_evidence, failures)``. The outcome's source
    document carries the POLICY text (that is the evidence being attested) but
    cites the PROPERTY url (that is what identifies the hotel) -- so nothing
    downstream ever publishes a search link, and the policy still routes REVIEW
    behind an explicit approval.
    """
    identity = ingest_capture(identity_payload, job, observed_at=observed_at)
    if not identity.accepted:
        # A property page that cannot carry its own identity cannot lend one.
        return (identity, None, ("identity_capture_not_accepted:%s"
                                 % (identity.failure_reason or identity.status),))

    ok, reason = validate_capture(policy_payload)
    if not ok:
        return (identity, None, ("policy_capture_invalid:%s" % reason,))

    policy_url = str(policy_payload.get("final_url") or "")
    authorized = [job.official_url] + list(job.alternate_urls)
    if not host_is_authorized(policy_url, authorized):
        return (identity, None, ("policy_capture_unauthorized_domain:%s"
                                 % (urlsplit(policy_url).hostname or "?"),))

    policy_html = str(policy_payload.get("html") or "")
    policy_text, truncated = normalize_html_to_text(policy_html)
    blocked = _page_block_reason(policy_text)
    if blocked:
        return (identity, None, ("policy_capture_%s" % blocked,))

    paired, failures = bind_paired_captures(
        identity=identity, policy_payload=policy_payload, job=job,
        identity_captured_at=str(identity_payload.get("captured_at") or ""),
        policy_captured_at=str(policy_payload.get("captured_at") or ""))
    if paired is None:
        return (identity, None, failures)

    warnings = list(identity.warnings) + ["paired_policy_surface"]
    if truncated:
        warnings.append("policy_normalized_text_truncated_50kb")

    doc = SourceDocument(
        source_url=identity.captured_url,          # cite the PROPERTY, never the query
        source_type=V.SOURCE_MANUAL_OFFICIAL_ATTESTATION,
        retrieved_at=observed_at or str(policy_payload.get("captured_at") or ""),
        title=identity.title, content_text=policy_text,
        content_hash=contract_content_hash(policy_text),
        retrieval_status=V.RETRIEVAL_OK)

    outcome = IngestionOutcome(
        assignment_id=job.assignment_id, listing_key=job.listing_key,
        listing_name=job.listing_name, status=CAPTURE_ACCEPTED,
        captured_url=identity.captured_url, canonical_url=identity.canonical_url,
        title=identity.title, identity=identity.identity,
        identity_reasons=identity.identity_reasons,
        source_role=SOURCE_ROLE_PAIRED_POLICY, policy_applicable=True,
        raw_content_hash=identity.raw_content_hash,
        normalized_text_hash=paired.policy_text_hash,
        normalized_text_bytes=len(policy_text.encode("utf-8")),
        jsonld_blocks=identity.jsonld_blocks,
        warnings=tuple(warnings), source_document=doc)
    return (outcome, paired, ())


# --------------------------------------------------------------------------- #
# PTF-WORKERS-006 -- MANUAL_OFFICIAL_ATTESTATION.
#
# An accepted capture is page BYTES. An attestation is those bytes plus the
# human accountability that justifies trusting a non-machine transport: who
# looked, when, what they confirmed on screen, what they photographed, and
# which automated failure made a person necessary in the first place.
#
# The two are separate on purpose. Ingestion answers "is this the right
# official page"; attestation answers "is there a named person standing behind
# it". Publication needs both, plus a third, later act -- approval.
# --------------------------------------------------------------------------- #

CAPTURE_METHOD_MANUAL_ATTESTATION = "MANUAL_ATTESTATION"
ATTESTATION_SCHEMA = "ptf-official-attestation/1.0"

APPROVAL_PENDING = "PENDING"
APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"
APPROVAL_STATES = frozenset({APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED})

# The fixed sentence an operator affirms. Fixed rather than free-text so every
# attestation means the same thing and no one can attest to something weaker.
ATTESTATION_STATEMENT = (
    "I personally opened this URL in an ordinary browser as a member of the "
    "public, confirmed it is the official page for this property, and confirm "
    "the captured page content and screenshots are what I saw.")


class AttestationError(ValueError):
    """Raised when an attestation fails one of the six mandatory gates."""


@dataclass(frozen=True)
class AutomatedFailure:
    """Why a human was needed. Gate 1 -- an attestation with no demonstrated
    automated failure is refused, so this path can never become a shortcut
    around retrieval that would have worked."""

    status: str
    reason: str = ""
    artifact_path: str = ""

    def to_dict(self) -> dict:
        return {"status": self.status, "reason": self.reason,
                "artifact_path": self.artifact_path}


@dataclass(frozen=True)
class OperatorAffirmation:
    """Gates 2 and 3. Deliberately a short, non-sensitive handle: no legal
    name, no email, no IP, no machine name. Accountability needs an identifier
    that a person can be held to, not their identity documents."""

    operator_id: str
    attested_at: str
    address_confirmed: bool = False
    address_observed: str = ""
    phone_confirmed: bool = False
    phone_observed: str = ""
    statement: str = ATTESTATION_STATEMENT

    def to_dict(self) -> dict:
        return {"operator_id": self.operator_id, "attested_at": self.attested_at,
                "address_confirmed": self.address_confirmed,
                "address_observed": self.address_observed,
                "phone_confirmed": self.phone_confirmed,
                "phone_observed": self.phone_observed, "statement": self.statement}


@dataclass(frozen=True)
class Screenshot:
    """Gate 4. Bytes live in the CAS; only the hash and shape live here, so an
    attestation JSON can never carry image data."""

    sha256: str
    byte_length: int
    width: int = 0
    height: int = 0
    note: str = ""

    def to_dict(self) -> dict:
        return {"sha256": self.sha256, "byte_length": self.byte_length,
                "width": self.width, "height": self.height, "note": self.note}


@dataclass(frozen=True)
class ModelResearchRef:
    """Gate 5. A POINTER to prior model research, never a source of content.

    Recorded because it is useful to know a model pointed us here, and
    dangerous to let that fact drift into meaning the model's prose was
    evidence. ``build_attestation`` enforces the difference.
    """

    urn: str
    report_hash: str = ""

    def to_dict(self) -> dict:
        return {"urn": self.urn, "report_hash": self.report_hash,
                "is_evidence": False,
                "note": "reference only; model prose is never attested content"}


@dataclass(frozen=True)
class ApprovalRecord:
    """Gate 6. A separate action, by a separately named person, at its own
    time, with its own record id -- even when the handle matches the
    operator's. Attesting and approving are different decisions."""

    state: str = APPROVAL_PENDING
    approver_id: str = ""
    approved_at: str = ""
    approval_record_id: str = ""

    def to_dict(self) -> dict:
        return {"state": self.state, "approver_id": self.approver_id,
                "approved_at": self.approved_at,
                "approval_record_id": self.approval_record_id}


def store_screenshot(cas, data: bytes, *, width: int = 0, height: int = 0,
                     note: str = "") -> Screenshot:
    """Put screenshot bytes in the CAS and return the reference.

    Retention: screenshots are kept indefinitely for now as audit evidence, and
    no automatic deletion exists in this phase. Retention is a STORAGE policy --
    changing it later cannot change an attestation's identity or provenance,
    because ``attestation_hash`` covers the screenshot hashes, not the bytes.
    """
    if not data:
        raise AttestationError("screenshot has no bytes")
    digest = cas.put_bytes(data)
    return Screenshot(sha256=digest, byte_length=len(data), width=width,
                      height=height, note=note)


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


@dataclass(frozen=True)
class OfficialAttestation:
    attestation_id: str
    listing_key: str
    listing_name: str
    official_url: str
    observed_at: str
    observed_timezone: str
    ingestion: IngestionOutcome
    affirmation: OperatorAffirmation
    automated_failure: AutomatedFailure
    screenshots: Tuple[Screenshot, ...]
    statements: Tuple[dict, ...] = ()
    contradictions: Tuple[str, ...] = ()
    fee_amounts: Tuple[str, ...] = ()
    model_research_ref: Optional[ModelResearchRef] = None
    approval: ApprovalRecord = field(default_factory=ApprovalRecord)
    paired_evidence: Optional[PairedEvidence] = None
    schema: str = ATTESTATION_SCHEMA
    capture_method: str = CAPTURE_METHOD_MANUAL_ATTESTATION

    @property
    def source_type(self) -> str:
        return V.SOURCE_MANUAL_OFFICIAL_ATTESTATION

    @property
    def publishable(self) -> bool:
        """Only an explicit APPROVED record makes this publishable. PENDING and
        REJECTED both mean no, and routing withholds it regardless."""
        return self.approval.state == APPROVAL_APPROVED

    def attested_content(self) -> dict:
        """The immutable part: everything EXCEPT the approval record.

        Approval is a later, separate act. If it were inside the hash, the
        attestation's identity would change the moment someone approved it --
        and the whole point of the hash is to prove the attested content did
        NOT change between attestation and approval.
        """
        content = {
            "schema": self.schema,
            "attestation_id": self.attestation_id,
            "capture_method": self.capture_method,
            "source_type": self.source_type,
            "listing_key": self.listing_key,
            "listing_name": self.listing_name,
            "official_url": self.official_url,
            "observed_at": self.observed_at,
            "observed_timezone": self.observed_timezone,
            "affirmation": self.affirmation.to_dict(),
            "automated_failure": self.automated_failure.to_dict(),
            "screenshots": [s.to_dict() for s in self.screenshots],
            "statements": [dict(s) for s in self.statements],
            "contradictions": list(self.contradictions),
            "fee_amounts": list(self.fee_amounts),
            "model_research_ref": (self.model_research_ref.to_dict()
                                   if self.model_research_ref else None),
            "ingestion": self.ingestion.to_dict(),
        }
        # Added ONLY when the evidence is paired, so a single-capture record's
        # attested content -- and therefore its hash -- is byte-identical to
        # what it was before PTF-WORKERS-007 existed. A schema change that
        # silently re-hashed every prior attestation would invalidate exactly
        # the records this system exists to keep verifiable.
        if self.paired_evidence is not None:
            content["paired_evidence"] = self.paired_evidence.to_dict()
        return content

    def attestation_hash(self) -> str:
        return "sha256:" + hashlib.sha256(
            _canonical(self.attested_content()).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        d = self.attested_content()
        d["attestation_hash"] = self.attestation_hash()
        d["approval"] = self.approval.to_dict()
        d["publishable"] = self.publishable
        d["retention"] = ("screenshots retained indefinitely as audit evidence; "
                          "no automatic deletion in this phase")
        return d


def build_attestation(*, ingestion: IngestionOutcome, job: CaptureJob,
                      affirmation: OperatorAffirmation,
                      automated_failure: AutomatedFailure,
                      screenshots: Sequence[Screenshot],
                      observed_at: str, observed_timezone: str,
                      model_research_ref: Optional[ModelResearchRef] = None,
                      paired_evidence: Optional[PairedEvidence] = None,
                      ) -> OfficialAttestation:
    """Apply all six gates and build an immutable, PENDING attestation.

    Every gate raises rather than warns. A partially-satisfied attestation is
    not a weaker attestation, it is not an attestation.

    ``paired_evidence`` adds Gate P (PTF-WORKERS-007). Passing it is the only
    way a policy capture taken from a search surface may be attested, and it
    must carry all four strong binding signals.
    """
    # Gate 1 -- a human is only justified where automation demonstrably failed.
    if not automated_failure or not automated_failure.status:
        raise AttestationError("gate1: an automated retrieval failure must be recorded")
    if automated_failure.status not in CAPTURE_WORTHY:
        raise AttestationError(
            "gate1: retrieval status %r does not justify a manual attestation"
            % automated_failure.status)

    # Gate 2 -- named operator and a real timestamp.
    if not affirmation or not affirmation.operator_id.strip():
        raise AttestationError("gate2: operator_id is required")
    if not affirmation.attested_at.strip():
        raise AttestationError("gate2: attested_at is required")
    if not observed_at.strip() or not observed_timezone.strip():
        raise AttestationError("gate2: observed_at and observed_timezone are required")
    if affirmation.statement != ATTESTATION_STATEMENT:
        raise AttestationError("gate2: the attestation statement may not be altered")

    # Gate 3 -- the operator confirmed identity on screen, not just the machine.
    if not affirmation.address_confirmed:
        raise AttestationError("gate3: address_confirmed is required")
    if not affirmation.phone_confirmed:
        raise AttestationError("gate3: phone_confirmed is required")

    # Gate 4 -- at least one CAS-backed screenshot.
    shots = tuple(screenshots or ())
    if not shots:
        raise AttestationError("gate4: at least one screenshot is required")
    for s in shots:
        if not re.fullmatch(r"[0-9a-f]{64}", s.sha256 or ""):
            raise AttestationError("gate4: screenshot sha256 is not a CAS digest")
        if s.byte_length <= 0:
            raise AttestationError("gate4: screenshot has no bytes")

    # Gate 5 -- the model-research firewall.
    if ingestion is None or not ingestion.accepted or ingestion.source_document is None:
        raise AttestationError("gate5: only an ACCEPTED page capture may be attested")
    doc = ingestion.source_document
    if doc.source_url.startswith("urn:atlas:model-research-report:"):
        raise AttestationError("gate5: a model research report is not an official page")
    if doc.source_type != V.SOURCE_MANUAL_OFFICIAL_ATTESTATION:
        raise AttestationError("gate5: unexpected source_type %r" % doc.source_type)
    if not doc.content_text.strip():
        raise AttestationError("gate5: attested content is empty")
    # PTF-CAPTURE-004. The cited URL is published as this hotel's official
    # source. A session identifier or ad click id in it would put the
    # operator's own browsing trail on a consumer page, so this refuses rather
    # than silently stripping -- a citation that needs editing is one a human
    # should look at.
    if url_carries_private_params(doc.source_url):
        raise AttestationError(
            "gate5: cited url carries a session or ad-tracking parameter; "
            "recapture or cite the canonical url: %s" % doc.source_url)
    if model_research_ref is not None:
        ref_hash = (model_research_ref.report_hash or "").split(":")[-1]
        if ref_hash and ref_hash in (ingestion.normalized_text_hash,
                                     doc.content_hash.split(":")[-1]):
            raise AttestationError(
                "gate5: attested content is identical to the model research report; "
                "a report may be referenced but never attested as the official page")

    # Gate P -- paired evidence. The role and the pairing must agree in BOTH
    # directions: a paired role without recorded binding evidence would be an
    # unexplained search-surface attestation, and binding evidence attached to
    # an ordinary single capture would be a claim nothing re-checked.
    paired_role = ingestion.source_role == SOURCE_ROLE_PAIRED_POLICY
    if paired_role and paired_evidence is None:
        raise AttestationError(
            "gateP: a paired policy surface requires recorded binding evidence")
    if paired_evidence is not None:
        if not paired_role:
            raise AttestationError(
                "gateP: binding evidence supplied for a non-paired capture")
        missing = [s for s in REQUIRED_BINDING_SIGNALS
                   if s not in paired_evidence.matched_signals]
        if missing:
            raise AttestationError(
                "gateP: binding requires all four strong signals; missing %s"
                % ",".join(sorted(missing)))
        if classify_url_shape(paired_evidence.identity_capture_url) != URL_SHAPE_PROPERTY:
            raise AttestationError("gateP: identity capture is not a property URL")
        if paired_evidence.identity_text_hash == paired_evidence.policy_text_hash:
            raise AttestationError("gateP: identity and policy captures are the same page")
        if doc.source_url != paired_evidence.identity_capture_url:
            raise AttestationError(
                "gateP: a paired attestation must cite the property URL, not the "
                "policy surface")

    # Privacy: the same forbidden-key scan ingestion applies, re-run over the
    # assembled record so nothing sensitive enters via the attestation fields.
    probe = {"affirmation": affirmation.to_dict(),
             "screenshots": [s.to_dict() for s in shots],
             "automated_failure": automated_failure.to_dict()}
    forbidden = _scan_forbidden(probe)
    if forbidden:
        raise AttestationError("forbidden_keys:%s" % ",".join(sorted(forbidden)[:5]))

    # Contradiction preservation -- reuse the PTF-WORKERS-005 collector so
    # there is ONE definition of "every statement, nothing resolved".
    from services.research_workers.rendered_capture import (
        collect_statements, detect_contradictions, fee_amounts,
    )
    statements = collect_statements(doc.content_text)
    attestation_id = "attest-%s" % hashlib.sha256(
        ("%s|%s|%s" % (job.listing_key, doc.source_url, observed_at)).encode("utf-8")
    ).hexdigest()[:24]

    return OfficialAttestation(
        attestation_id=attestation_id, listing_key=job.listing_key,
        listing_name=job.listing_name, official_url=doc.source_url,
        observed_at=observed_at, observed_timezone=observed_timezone,
        ingestion=ingestion, affirmation=affirmation,
        automated_failure=automated_failure, screenshots=shots,
        statements=tuple(s.to_dict() for s in statements),
        contradictions=detect_contradictions(statements),
        fee_amounts=fee_amounts(statements),
        model_research_ref=model_research_ref,
        paired_evidence=paired_evidence,
        approval=ApprovalRecord())          # gate 6: always begins PENDING


def approve_attestation(attestation: OfficialAttestation, *, approver_id: str,
                        approved_at: str, approval_record_id: str
                        ) -> OfficialAttestation:
    """Gate 6. A separate, recorded act -- never inferable from attestation.

    The attested content is untouched, so ``attestation_hash()`` is identical
    before and after: the approval provably applies to exactly what was
    attested, and cannot be moved onto different content.
    """
    from dataclasses import replace
    if attestation.approval.state != APPROVAL_PENDING:
        raise AttestationError("attestation is already %s" % attestation.approval.state)
    for name, value in (("approver_id", approver_id), ("approved_at", approved_at),
                        ("approval_record_id", approval_record_id)):
        if not (value or "").strip():
            raise AttestationError("gate6: %s is required to approve" % name)
    return replace(attestation, approval=ApprovalRecord(
        state=APPROVAL_APPROVED, approver_id=approver_id, approved_at=approved_at,
        approval_record_id=approval_record_id))


# Exactly the keys ``OfficialAttestation.attested_content`` hashes. Kept beside
# it so the stored-artifact path and the in-memory path can never drift into
# hashing different things.
_ATTESTED_CONTENT_KEYS = (
    "schema", "attestation_id", "capture_method", "source_type", "listing_key",
    "listing_name", "official_url", "observed_at", "observed_timezone",
    "affirmation", "automated_failure", "screenshots", "statements",
    "contradictions", "fee_amounts", "model_research_ref", "ingestion",
)


def attested_content_from_record(record: dict) -> dict:
    """Rebuild the exact hashed payload from a stored attestation artifact."""
    missing = [k for k in _ATTESTED_CONTENT_KEYS if k not in record]
    if missing:
        raise AttestationError("attestation record is missing %s" % ",".join(missing))
    return {k: record[k] for k in _ATTESTED_CONTENT_KEYS}


def verify_attestation_record(record: dict) -> Tuple[bool, str]:
    """Recompute the attestation hash from the record's own content.

    An approval that does not re-verify is an approval of whatever the file
    happens to say now. Because ``attestation_hash`` deliberately excludes the
    approval block, it can be checked before AND after approval, and any edit
    to the attested content between attestation and approval is detected here.
    """
    try:
        payload = attested_content_from_record(record)
    except AttestationError as exc:
        return (False, str(exc))
    recomputed = "sha256:" + hashlib.sha256(
        _canonical(payload).encode("utf-8")).hexdigest()
    stored = str(record.get("attestation_hash") or "")
    if not stored:
        return (False, "attestation record carries no attestation_hash")
    if stored != recomputed:
        return (False, "attestation_hash mismatch: the attested content has been "
                       "modified since it was attested")
    return (True, "")


def approve_attestation_record(record: dict, *, approver_id: str, approved_at: str,
                               approval_record_id: str, reject: bool = False) -> dict:
    """Approve (or reject) a STORED attestation artifact.

    The CLI used to hand-edit the JSON, which meant the guards written and
    tested in ``approve_attestation`` were not the guards that actually ran.
    This is the one implementation for the stored-artifact path: it verifies
    the hash first, applies the same gate-6 rules, and returns a NEW record --
    the attested content is never touched, so the hash is unchanged and the
    approval provably applies to exactly what was attested.
    """
    ok, reason = verify_attestation_record(record)
    if not ok:
        raise AttestationError(reason)

    state = (record.get("approval") or {}).get("state")
    if state != APPROVAL_PENDING:
        raise AttestationError("attestation is not PENDING (state=%s)" % state)
    for name, value in (("approver_id", approver_id), ("approved_at", approved_at),
                        ("approval_record_id", approval_record_id)):
        if not (value or "").strip():
            raise AttestationError("gate6: %s is required to approve" % name)

    new_state = APPROVAL_REJECTED if reject else APPROVAL_APPROVED
    updated = dict(record)
    updated["approval"] = {
        "state": new_state, "approver_id": approver_id,
        "approved_at": approved_at, "approval_record_id": approval_record_id,
    }
    updated["publishable"] = new_state == APPROVAL_APPROVED
    # Re-verify: the attested content -- and therefore the hash -- must be
    # byte-identical after approval.
    ok, reason = verify_attestation_record(updated)
    if not ok:                                  # unreachable by construction
        raise AttestationError("approval altered attested content: %s" % reason)
    return updated


def reject_attestation(attestation: OfficialAttestation, *, approver_id: str,
                       approved_at: str, approval_record_id: str
                       ) -> OfficialAttestation:
    from dataclasses import replace
    return replace(attestation, approval=ApprovalRecord(
        state=APPROVAL_REJECTED, approver_id=approver_id, approved_at=approved_at,
        approval_record_id=approval_record_id))

"""AES-DATA-001 importer -- immutable source snapshot (mission section 6).

Deterministic: raw bytes -> CAS (content-addressed, gitignored), HTML ->
bounded normalized text (<= 50 KB) -> sha256. The candidate records exactly
which normalized text the extractor received. No network here (the fetch
already happened); the only side effect is the CAS ``put_bytes`` write.
"""

from __future__ import annotations

import hashlib
from typing import Optional, Tuple

from bs4 import BeautifulSoup

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import FetchResult, SourceSnapshot
from scripts.pettripfinder.importer.normalize import normalize_whitespace

# Tags whose text is boilerplate/unsafe and removed before normalization.
_STRIP_TAGS = ("script", "style", "form", "nav", "footer", "noscript",
               "template", "svg", "iframe")


def _decode(body: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", "ignore")


def normalize_html_to_text(html: str) -> Tuple[str, bool]:
    """Deterministic readable-text extraction: strip script/style/form/nav/
    footer/etc., join visible text in source order, collapse whitespace, and
    cap at 50 KB of UTF-8. Returns ``(text, truncated)``."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()
    raw = soup.get_text(separator=" ")
    text = normalize_whitespace(raw)
    encoded = text.encode("utf-8")
    if len(encoded) <= C.NORMALIZED_TEXT_CAP_BYTES:
        return (text, False)
    clipped = encoded[: C.NORMALIZED_TEXT_CAP_BYTES].decode("utf-8", "ignore")
    return (clipped, True)


def extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return normalize_whitespace(soup.title.string)
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return normalize_whitespace(og["content"])
    return ""


def extract_canonical(soup: BeautifulSoup) -> str:
    link = soup.find("link", attrs={"rel": lambda v: v and "canonical" in (
        v if isinstance(v, list) else [v])})
    if link and link.get("href"):
        return link["href"].strip()
    og = soup.find("meta", attrs={"property": "og:url"})
    if og and og.get("content"):
        return og["content"].strip()
    return ""


def detect_javascript_only(soup: BeautifulSoup, normalized_text: str) -> bool:
    """Heuristic JS-rendered classification: near-empty visible text plus an
    app-shell marker or heavy scripting. Conservative -- only fires when
    there is essentially no readable content to extract from."""
    if len(normalized_text) >= 400:
        return False
    scripts = soup.find_all("script")
    app_roots = soup.select("#root, #app, [ng-app], [data-reactroot], #__next")
    return len(normalized_text) < 200 and (len(scripts) >= 3 or bool(app_roots))


def build_snapshot(
    fetch_result: FetchResult,
    cas,
    observed_at: str,
    source_relationship: str,
) -> SourceSnapshot:
    """Assemble the immutable snapshot from a successful fetch. Raw bytes go
    to the CAS; only the hash is retained."""
    html = _decode(fetch_result.body)
    soup = BeautifulSoup(html, "html.parser")
    normalized_text, truncated = normalize_html_to_text(html)

    warnings = list(fetch_result.warnings)
    if truncated:
        warnings.append("normalized_text_truncated_50kb")
    if detect_javascript_only(soup, normalized_text):
        warnings.append(C.REASON_JAVASCRIPT_RENDERED)

    raw_hash = cas.put_bytes(fetch_result.body)
    text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    return SourceSnapshot(
        requested_url=fetch_result.requested_url,
        final_url=fetch_result.final_url or fetch_result.requested_url,
        observed_at=observed_at,
        http_status=fetch_result.http_status,
        content_type=fetch_result.content_type,
        redirect_chain=fetch_result.redirect_chain,
        page_title=extract_title(soup),
        canonical_url=extract_canonical(soup),
        response_header_subset=fetch_result.response_headers,
        raw_content_hash=raw_hash,
        normalized_text_hash=text_hash,
        normalized_text=normalized_text,
        extraction_version=C.EXTRACTION_VERSION,
        fetch_warnings=tuple(warnings),
        source_relationship=source_relationship,
    )


def snapshot_has_javascript_warning(snapshot: SourceSnapshot) -> bool:
    return C.REASON_JAVASCRIPT_RENDERED in snapshot.fetch_warnings

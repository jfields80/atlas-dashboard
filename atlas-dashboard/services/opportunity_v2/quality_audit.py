"""
quality_audit.py — Phase 3: Directory Quality Audit.

Fetches a competitor directory's page and scores it 0-100 on signals
that are CONCRETELY DETECTABLE from HTML. Honesty note baked into the
design: things like "looks outdated" or "poor branding" are subjective —
instead we detect proxies that correlate with them (no viewport meta =
pre-2015 era site; no CSS framework/modern markup = likely dated; last
copyright year; etc.) and we report WHICH signals fired so the score is
auditable, never a vibe.

14 signal checks, each worth points toward 100:

  STRUCTURE (max 35)
    mobile_viewport (7)      — <meta name=viewport> present
    has_search (7)           — search input/form detected
    has_filtering (7)        — filter/sort controls detected
    has_categories (7)       — category nav/links detected
    has_map (7)              — Google Maps / Leaflet / Mapbox embed

  CONTENT (max 35)
    listing_count (10)       — scaled: 0 pts <10 listings, full ≥75
    has_descriptions (7)     — listings carry real text, not bare names
    has_images (6)           — images beyond logo/icons
    has_reviews (6)          — review/rating markup or schema
    has_social_links (6)     — outbound social profile links

  FRESHNESS & TRUST (max 15)
    fresh_copyright (8)      — © year within last 2 years
    https (4)                — served over TLS
    schema_markup (3)        — LocalBusiness/ItemList structured data

  MONETIZATION (max 15)
    monetization_present (15)— ads/affiliate/premium-listing signals
                                (also feeds Phase 4 revenue estimation)

Low score = weak incumbent = OUR opportunity. The spec's
"Directory Quality 18/100 — Opportunity detected" comes from here.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 AtlasAudit/1.0")

AD_NETWORK_PATTERNS = {
    "google_adsense": ["adsbygoogle", "googlesyndication.com"],
    "mediavine": ["mediavine"],
    "raptive_adthrive": ["adthrive", "raptive"],
    "ezoic": ["ezoic"],
    "monumetric": ["monumetric"],
}
AFFILIATE_PATTERNS = ["amzn.to", "amazon.com/dp", "tag=", "awin", "shareasale",
                       "cj.com", "impact.com", "partnerize", "avantlink",
                       "booking.com/searchresults", "expedia.com", "?ref=", "&aff"]
PREMIUM_LISTING_PATTERNS = ["featured listing", "premium listing", "claim your",
                              "claim this", "add your business", "get listed",
                              "advertise with", "sponsor", "upgrade your listing"]
MAP_PATTERNS = ["maps.googleapis.com", "maps.google.com/maps", "leaflet",
                 "mapbox", "openstreetmap"]
LISTING_SELECTORS = ["[class*=listing]", "[class*=result]", "[class*=card]",
                      "[class*=business]", "[itemtype*=LocalBusiness]",
                      "article", "[class*=item]"]
SOCIAL_DOMAINS = ["facebook.com/", "instagram.com/", "twitter.com/", "x.com/",
                   "tiktok.com/@", "youtube.com/", "linkedin.com/"]


@dataclass
class AuditResult:
    url: str
    fetched: bool
    quality_score: float = 0.0
    grade: str = "unknown"           # weak | moderate | strong
    signals: dict = field(default_factory=dict)      # signal -> bool/number
    monetization_detected: list = field(default_factory=list)
    listing_count_estimate: int = 0
    notes: list = field(default_factory=list)
    error: str | None = None


def fetch_page(url: str, timeout: int = 15) -> tuple[str | None, str | None]:
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout,
                             allow_redirects=True)
        if resp.status_code >= 400:
            return None, f"HTTP {resp.status_code}"
        return resp.text, None
    except requests.RequestException as e:
        return None, f"{type(e).__name__}: {e}"


def audit_html(url: str, html: str) -> AuditResult:
    """Pure function: HTML in, audit out. Separated from fetch_page so it's
    unit-testable with fixture files and reusable on cached pages."""
    result = AuditResult(url=url, fetched=True)
    soup = BeautifulSoup(html, "html.parser")
    lowered = html.lower()
    s = result.signals

    # --- STRUCTURE ----------------------------------------------------------
    s["mobile_viewport"] = bool(soup.find("meta", attrs={"name": "viewport"}))
    s["has_search"] = bool(
        soup.find("input", attrs={"type": "search"})
        or soup.select_one("input[name*=search], input[placeholder*=earch], form[class*=search]"))
    s["has_filtering"] = bool(
        soup.select_one("select[class*=filter], [class*=filter] select, "
                         "[class*=filters], [data-filter], [class*=sort-by]"))
    cat_links = soup.select("a[href*=category], a[href*=categories], nav a")
    s["has_categories"] = len(cat_links) >= 5
    s["has_map"] = any(p in lowered for p in MAP_PATTERNS)

    # --- CONTENT -------------------------------------------------------------
    listing_counts = [len(soup.select(sel)) for sel in LISTING_SELECTORS]
    result.listing_count_estimate = max(listing_counts) if listing_counts else 0
    s["listing_count"] = result.listing_count_estimate

    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
    substantial = [p for p in paragraphs if len(p) > 80]
    s["has_descriptions"] = len(substantial) >= 3

    content_imgs = [img for img in soup.find_all("img")
                     if not re.search(r"logo|icon|sprite|pixel", str(img.get("src", "")) +
                                        str(img.get("class", "")), re.I)]
    s["has_images"] = len(content_imgs) >= 3

    s["has_reviews"] = bool(re.search(r"aggregaterating|reviewcount|star-rating|"
                                        r"\breviews?\b.{0,30}\d", lowered))
    s["has_social_links"] = any(d in lowered for d in SOCIAL_DOMAINS)

    # --- FRESHNESS & TRUST ---------------------------------------------------
    year_now = datetime.date.today().year
    copyright_years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(\d{4})", lowered)]
    latest = max(copyright_years) if copyright_years else None
    s["copyright_year"] = latest
    s["fresh_copyright"] = latest is not None and latest >= year_now - 1
    s["https"] = url.startswith("https://")
    s["schema_markup"] = bool(re.search(r'"@type"\s*:\s*"(localbusiness|itemlist|'
                                          r'restaurant|store)"', lowered))

    # --- MONETIZATION --------------------------------------------------------
    for network, patterns in AD_NETWORK_PATTERNS.items():
        if any(p in lowered for p in patterns):
            result.monetization_detected.append(f"ads:{network}")
    if any(p in lowered for p in AFFILIATE_PATTERNS):
        result.monetization_detected.append("affiliate_links")
    for p in PREMIUM_LISTING_PATTERNS:
        if p in lowered:
            result.monetization_detected.append(f"premium_listings ('{p}')")
            break
    s["monetization_present"] = bool(result.monetization_detected)

    # --- SCORING -------------------------------------------------------------
    score = 0.0
    score += 7 if s["mobile_viewport"] else 0
    score += 7 if s["has_search"] else 0
    score += 7 if s["has_filtering"] else 0
    score += 7 if s["has_categories"] else 0
    score += 7 if s["has_map"] else 0

    lc = result.listing_count_estimate
    score += 10 if lc >= 75 else 7 if lc >= 40 else 4 if lc >= 15 else 1 if lc >= 10 else 0
    score += 7 if s["has_descriptions"] else 0
    score += 6 if s["has_images"] else 0
    score += 6 if s["has_reviews"] else 0
    score += 6 if s["has_social_links"] else 0

    score += 8 if s["fresh_copyright"] else 0
    score += 4 if s["https"] else 0
    score += 3 if s["schema_markup"] else 0

    score += 15 if s["monetization_present"] else 0

    result.quality_score = round(score, 1)
    result.grade = ("strong" if score >= 65 else
                     "moderate" if score >= 40 else "weak")

    # Human-readable notes for the UI
    if not s["mobile_viewport"]:
        result.notes.append("No mobile viewport meta — likely pre-2015-era or unmaintained.")
    if latest and latest < year_now - 1:
        result.notes.append(f"Copyright stuck at {latest} — stale site.")
    if lc < 15:
        result.notes.append(f"Only ~{lc} listing-like elements on page — thin coverage.")
    if not s["has_search"] and not s["has_filtering"]:
        result.notes.append("No search or filtering — poor UX for visitors.")
    if not result.monetization_detected:
        result.notes.append("No monetization detected — incumbent isn't defending revenue.")
    else:
        result.notes.append("Monetizing via: " + ", ".join(result.monetization_detected))

    return result


def audit_url(url: str) -> AuditResult:
    html, err = fetch_page(url)
    if html is None:
        r = AuditResult(url=url, fetched=False, error=err, grade="unknown")
        r.notes.append(f"Could not fetch: {err}")
        return r
    return audit_html(url, html)

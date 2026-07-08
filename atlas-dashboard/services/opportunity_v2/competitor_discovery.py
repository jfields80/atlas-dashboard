"""
competitor_discovery.py — Phase 2: find existing DIRECTORIES per niche node.

Per the spec: "Not restaurants. Directories."

Given a niche node, run directory-hunting query patterns through the
search provider, then classify what comes back:

  platform_giant   — Yelp/TripAdvisor/Google Maps/etc. Always present,
                      basically unbeatable head-on, but their PRESENCE
                      isn't disqualifying — their category pages are
                      often thin for deep niches. Tracked separately.
  independent      — the ones we actually care about. Standalone niche
                      directories: these are the incumbents we audit
                      in Phase 3 and potentially replace.
  chamber_or_gov   — chambers of commerce, city sites, tourism boards.
  listicle         — "17 Best X in Y" blog posts. Beatable content, not
                      real directories, but they hold SERP real estate.
  other            — everything else (individual business sites, news).

Independent-directory scarcity + listicle-heavy SERPs is exactly the
"weak incumbent" signal the spec wants to detect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .search_provider import SearchProvider, SearchResult

PLATFORM_DOMAINS = {
    "yelp.com": "Yelp", "tripadvisor.com": "TripAdvisor",
    "google.com": "Google", "facebook.com": "Facebook",
    "opentable.com": "OpenTable", "grubhub.com": "Grubhub",
    "doordash.com": "DoorDash", "ubereats.com": "UberEats",
    "yellowpages.com": "YellowPages", "bbb.org": "BBB",
    "angi.com": "Angi", "thumbtack.com": "Thumbtack",
    "nextdoor.com": "Nextdoor", "foursquare.com": "Foursquare",
    "zomato.com": "Zomato", "restaurantji.com": "Restaurantji",
    "mapquest.com": "MapQuest", "instagram.com": "Instagram",
    "reddit.com": "Reddit", "tiktok.com": "TikTok",
}

CHAMBER_HINTS = ["chamber", ".gov", "visit", "tourism", "cityof", "experience"]
LISTICLE_TITLE_RE = re.compile(r"^\s*(the\s+)?\d+\s+(best|top|greatest)", re.I)
BEST_TITLE_RE = re.compile(r"\b(best|top)\b.*\b(in|near)\b", re.I)
DIRECTORY_HINTS = ["directory", "guide", "listings", "finder", "locator"]

QUERY_TEMPLATES = [
    "{niche} directory",
    "{niche} guide",
    "best {niche}",
    "{niche} listings",
]


@dataclass
class Competitor:
    url: str
    domain: str
    title: str
    snippet: str
    category: str            # platform_giant | independent | chamber_or_gov | listicle | other
    found_via_query: str
    quality_audit: dict | None = None   # filled by Phase 3


@dataclass
class CompetitorReport:
    niche_name: str
    competitors: list[Competitor] = field(default_factory=list)
    queries_run: list[str] = field(default_factory=list)

    @property
    def independents(self) -> list[Competitor]:
        return [c for c in self.competitors if c.category == "independent"]

    @property
    def listicles(self) -> list[Competitor]:
        return [c for c in self.competitors if c.category == "listicle"]

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for c in self.competitors:
            counts[c.category] = counts.get(c.category, 0) + 1
        return counts


def classify(result: SearchResult) -> str:
    domain = urlparse(result.url).netloc.lower().removeprefix("www.")
    for pd, _name in PLATFORM_DOMAINS.items():
        if domain == pd or domain.endswith("." + pd):
            return "platform_giant"
    if any(h in domain for h in CHAMBER_HINTS):
        return "chamber_or_gov"
    text = f"{result.title} {result.snippet}".lower()
    if LISTICLE_TITLE_RE.search(result.title) or (
            BEST_TITLE_RE.search(result.title) and "directory" not in text):
        return "listicle"
    if any(h in domain for h in DIRECTORY_HINTS) or any(h in text for h in DIRECTORY_HINTS):
        return "independent"
    return "other"


def discover_competitors(niche_name: str, provider: SearchProvider,
                          results_per_query: int = 10) -> CompetitorReport:
    report = CompetitorReport(niche_name=niche_name)
    seen_domains: set[str] = set()

    for template in QUERY_TEMPLATES:
        query = template.format(niche=niche_name)
        report.queries_run.append(query)
        for r in provider.search(query, num=results_per_query):
            domain = urlparse(r.url).netloc.lower().removeprefix("www.")
            if not domain or domain in seen_domains:
                continue
            seen_domains.add(domain)
            report.competitors.append(Competitor(
                url=r.url, domain=domain, title=r.title,
                snippet=r.snippet, category=classify(r),
                found_via_query=query,
            ))
    return report

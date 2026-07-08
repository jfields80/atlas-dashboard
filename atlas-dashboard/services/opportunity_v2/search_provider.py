"""
search_provider.py — Phase 2 foundation: pluggable web search.

Competitor discovery needs real web search. Scraping Google directly
from a server gets blocked fast, so this module defines a provider
interface with three implementations:

1. GoogleCustomSearchProvider — production. Uses Google's Custom Search
   JSON API. Free tier: 100 queries/day, then $5 per 1,000 queries.
   Setup (5 minutes):
     a. https://programmablesearchengine.google.com -> create engine,
        enable "Search the entire web", copy the Search Engine ID (cx)
     b. https://console.cloud.google.com -> enable "Custom Search API",
        create an API key
     c. export GOOGLE_CSE_KEY=... ; export GOOGLE_CSE_CX=...

2. StaticProvider — testing/dev. You hand it canned results; nothing
   leaves your machine. Also the seam for unit tests.

3. ManualProvider — no-API fallback. Prints the queries it WOULD run
   so you can execute them by hand and paste competitor URLs into the
   UI. Ugly but $0 and honest.

The rest of the pipeline only ever sees SearchResult objects, so adding
Bing/Brave/SerpAPI later = one new class here, nothing else changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import requests


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    query: str


class SearchProvider(Protocol):
    def search(self, query: str, num: int = 10) -> list[SearchResult]: ...


class GoogleCustomSearchProvider:
    ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str | None = None, cx: str | None = None):
        self.api_key = api_key or os.environ.get("GOOGLE_CSE_KEY")
        self.cx = cx or os.environ.get("GOOGLE_CSE_CX")
        if not (self.api_key and self.cx):
            raise ValueError(
                "GoogleCustomSearchProvider needs GOOGLE_CSE_KEY and GOOGLE_CSE_CX "
                "(env vars or constructor args). See module docstring for setup.")
        self.queries_used = 0

    def search(self, query: str, num: int = 10) -> list[SearchResult]:
        resp = requests.get(self.ENDPOINT, params={
            "key": self.api_key, "cx": self.cx, "q": query, "num": min(num, 10),
        }, timeout=15)
        resp.raise_for_status()
        self.queries_used += 1
        items = resp.json().get("items", [])
        return [SearchResult(i.get("title", ""), i.get("link", ""),
                              i.get("snippet", ""), query) for i in items]


class StaticProvider:
    """Deterministic canned results, keyed by substring match on query."""

    def __init__(self, canned: dict[str, list[SearchResult]] | None = None):
        self.canned = canned or {}
        self.queries_seen: list[str] = []

    def add(self, query_substring: str, results: list[tuple[str, str, str]]):
        self.canned[query_substring] = [
            SearchResult(t, u, s, query_substring) for t, u, s in results]

    def search(self, query: str, num: int = 10) -> list[SearchResult]:
        self.queries_seen.append(query)
        for key, results in self.canned.items():
            if key.lower() in query.lower():
                return results[:num]
        return []


class ManualProvider:
    """Zero-API mode: records the queries the pipeline wanted to run."""

    def __init__(self):
        self.pending_queries: list[str] = []

    def search(self, query: str, num: int = 10) -> list[SearchResult]:
        self.pending_queries.append(query)
        return []

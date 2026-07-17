"""AES-DATA-002B -- shared static fixture builders for the aggregate test
files (not itself a test module: no ``test_`` prefix, so pytest never
collects it). Realistic Land-Grant-shaped pages (FAQ policy page + location/
contact page) built from the same live-payload shape validated in the
AES-DATA-001/002A sessions. No network."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext

FAQ_URL = "https://landgrantbrewing.com/faq/"
CONTACT_URL = "https://landgrantbrewing.com/contact/"


def faq_html(url: str = FAQ_URL, title: str = "Land-Grant Brewing Columbus") -> str:
    return (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="FAQ | %s | Hours, Parking &amp; More">'
        '<meta property="og:url" content="%s">'
        "</head><body><h1>%s</h1>"
        "<p>Well-behaved dogs are welcome in our beer garden and on the "
        "patio. Dogs are not able to join you inside our Wintergarden "
        "Igloos. *Beer Garden operations are weather dependent. Water bowls "
        "and treats are available at the bar.</p>"
        "</body></html>" % (title, url, title))


def faq_facts() -> dict:
    return {"facts": [
        {"field": "name", "value": "Land-Grant Brewing", "quote": "Land-Grant Brewing Columbus"},
        {"field": "pets_allowed", "value": "true",
         "quote": "Well-behaved dogs are welcome in our beer garden and on the patio"},
        {"field": "patio_or_outdoor_only", "value": "true",
         "quote": "Well-behaved dogs are welcome in our beer garden and on the patio"},
        {"field": "indoor_prohibited", "value": "true",
         "quote": "Dogs are not able to join you inside our Wintergarden Igloos"},
        {"field": "seasonal_or_weather_caveat",
         "value": "Beer Garden operations are weather dependent",
         "quote": "*Beer Garden operations are weather dependent."},
        {"field": "water_or_treats", "value": "true",
         "quote": "Water bowls and treats are available at the bar."},
    ]}


def contact_html(
    url: str = CONTACT_URL, title: str = "Land-Grant Brewing Columbus",
    street: str = "424 W Town St", city: str = "Columbus", state: str = "OH",
    postal: str = "43215", phone: str = "614-586-0413",
) -> str:
    return (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="Contact | %s">'
        '<meta property="og:url" content="%s">'
        "</head><body>"
        '<script type="application/ld+json">'
        '{"@context": "https://schema.org", "@type": "Restaurant", '
        '"name": "%s", "telephone": "%s", '
        '"address": {"@type": "PostalAddress", "streetAddress": "%s", '
        '"addressLocality": "%s", "addressRegion": "%s", "postalCode": "%s"}}'
        "</script>"
        "<h1>%s</h1>"
        "<p>Visit us at %s, %s, %s. Call the taproom at %s.</p>"
        "</body></html>" % (
            title, url, title, phone, street, city, state, postal,
            title, street, city, state, phone))


def contact_facts() -> dict:
    return {"facts": []}


def build_fetcher_extractor(
    pages: List[Tuple[str, str]], facts_by_marker: Dict[str, dict],
) -> Tuple[StaticPageFetcher, StaticFactExtractor]:
    """``pages`` is ``[(url, html), ...]``. ``facts_by_marker`` maps a literal
    substring expected in that page's normalized text -> its facts payload;
    the extractor dispatches on the actual ``normalized_text`` it receives
    (content-based, so it is robust to URL dedup/reordering, unlike a
    call-count-based dispatch)."""
    fetcher = StaticPageFetcher()
    for u, h in pages:
        fetcher.add_html(u, h)

    def payload(normalized_text, _category, _allowed):
        for marker, facts in facts_by_marker.items():
            if marker in normalized_text:
                return facts
        return {"facts": []}

    extractor = StaticFactExtractor(payload)
    return (fetcher, extractor)


def default_context(**overrides) -> ImportContext:
    base = dict(
        category="restaurants", expected_city="Columbus", expected_state="OH",
        candidate_name="Land-Grant Brewing Columbus",
        source_relationship_hint="EXACT_ENTITY_DOMAIN")
    base.update(overrides)
    return ImportContext(**base)


def make_cas(tmp_path) -> ArtifactStoreRepository:
    return ArtifactStoreRepository(tmp_path / "cas")

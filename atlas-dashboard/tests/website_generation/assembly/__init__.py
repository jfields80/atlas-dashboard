"""Assembly Engine tests (AES-WEB-002J.10).

Shared fixture builders so assembly tests construct well-formed
``RenderedPageSet``/``SEOPackage``/``BrandPackage`` inputs without repeating
the full field set. ``rendered_page_set`` builds a schema-1.1.0
``RenderedPageSet`` whose per-page ``html_hash``/``shared_css_hash`` match
their payloads (so the integrity check passes by default), mirroring what a
real Renderer emits.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    RenderedPage,
    RenderedPageDetail,
    RenderedPageSet,
    SEOEntry,
    SEOPackage,
    sha256_of_text,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

__all__ = [
    "DOC",
    "brand_package",
    "rendered_page_set",
    "seo_package",
    "seo_entry",
    "assemble",
]

# A minimal, valid full HTML document with exactly one <head>...</head>, the
# shape the Renderer's layout.shell.page emitter produces.
DOC = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "</head><body>content</body></html>"
)


def brand_package(**overrides) -> BrandPackage:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BRAND_PACKAGE],
        artifact_kind=ArtifactKind.BRAND_PACKAGE,
        source_hashes={},
    )
    fields.update(overrides)
    return BrandPackage(**fields)


def rendered_page_set(
    pages: Iterable[Tuple[str, str]] = ((("/"), DOC),),
    shared_css: str = ":root{}",
    *,
    tamper_html_hash: Dict[str, str] = None,
    tamper_css_hash: str = None,
    **overrides,
) -> RenderedPageSet:
    """Build a RenderedPageSet from ``(route, html)`` pairs, computing each
    ``html_hash`` from the html so the Assembly integrity check passes.
    ``tamper_*`` overrides let a test force a hash mismatch."""
    tamper_html_hash = tamper_html_hash or {}
    page_records = tuple(
        RenderedPage(
            route=route,
            html_hash=tamper_html_hash.get(route, sha256_of_text(html)),
        )
        for route, html in pages
    )
    details = tuple(RenderedPageDetail(route=route, html=html) for route, html in pages)
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.RENDERED_PAGE_SET],
        artifact_kind=ArtifactKind.RENDERED_PAGE_SET,
        source_hashes={},
        pages=page_records,
        shared_css_hash=(
            tamper_css_hash if tamper_css_hash is not None else sha256_of_text(shared_css)
        ),
        page_details=details,
        shared_css=shared_css,
    )
    fields.update(overrides)
    return RenderedPageSet(**fields)


def seo_entry(route: str, *, title: str = "", meta: str = "", canonical: str = None) -> SEOEntry:
    return SEOEntry(
        route=route,
        title=title or ("Title " + route),
        meta_description=meta or ("Meta " + route),
        canonical_url=canonical if canonical is not None else route,
    )


def seo_package(
    entries: Iterable[SEOEntry] = None,
    sitemap_routes: Tuple[str, ...] = ("/",),
    robots_directives: Tuple[str, ...] = ("User-agent: *", "Allow: /"),
    **overrides,
) -> SEOPackage:
    if entries is None:
        entries = (seo_entry("/"),)
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SEO_PACKAGE],
        artifact_kind=ArtifactKind.SEO_PACKAGE,
        source_hashes={},
        entries=tuple(entries),
        sitemap_routes=tuple(sitemap_routes),
        robots_directives=tuple(robots_directives),
    )
    fields.update(overrides)
    return SEOPackage(**fields)


def assemble(rps=None, seo=None, brand=None):
    """Convenience: assemble with sensible matching defaults."""
    from engines.website_generation.assembly.assembly_engine import AssemblyEngine

    rps = rps if rps is not None else rendered_page_set()
    seo = seo if seo is not None else seo_package()
    brand = brand if brand is not None else brand_package()
    return AssemblyEngine().assemble(rps, seo, brand)

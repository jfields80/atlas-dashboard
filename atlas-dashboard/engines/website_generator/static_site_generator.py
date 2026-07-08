"""Static Site Generator.

Consumes a Directory Builder ProjectAssembly and produces an in-memory,
deterministic static website package.

No Flask.
No database.
No filesystem writes.
No external assets.
"""

from __future__ import annotations

import hashlib
from html import escape
from typing import Iterable

from engines.directory_builder.models import (
    BusinessRecord,
    CategoryRecord,
    LocationRecord,
    ProjectAssembly,
)
from engines.website_generator.constants import (
    DEFAULT_TEMPLATE_NAME,
    ENGINE_NAME,
    ENGINE_VERSION,
)
from engines.website_generator.models import (
    StaticAsset,
    StaticFileHash,
    StaticPage,
    StaticSiteManifest,
    StaticSitePackage,
    WebsiteQualityReport,
)
from engines.website_generator.quality_gate import WebsiteQualityGate
from engines.website_generator.template_engine import render_page


class StaticSiteGenerator:
    """Generate a deterministic static directory website from ProjectAssembly."""

    def __init__(self, quality_gate: WebsiteQualityGate | None = None) -> None:
        self._quality_gate = quality_gate or WebsiteQualityGate()

    def generate(self, assembly: ProjectAssembly) -> StaticSitePackage:
        project_slug = assembly.project_slug
        site_name = self._site_name(assembly)

        categories = tuple(
            sorted(
                assembly.import_package.categories,
                key=lambda c: (c.slug, c.category_id),
            )
        )

        locations = tuple(
            sorted(
                assembly.import_package.locations,
                key=lambda l: (l.slug, l.location_id),
            )
        )

        businesses = tuple(
            sorted(
                assembly.import_package.businesses,
                key=lambda b: (b.slug, b.business_id),
            )
        )

        pages: list[StaticPage] = []

        pages.append(
            self._homepage(
                site_name=site_name,
                categories=categories,
                locations=locations,
                businesses=businesses,
            )
        )

        pages.extend(
            self._category_pages(
                site_name=site_name,
                categories=categories,
                businesses=businesses,
            )
        )

        pages.extend(
            self._location_pages(
                site_name=site_name,
                locations=locations,
                businesses=businesses,
            )
        )

        pages.extend(
            self._category_location_pages(
                site_name=site_name,
                categories=categories,
                locations=locations,
                businesses=businesses,
            )
        )

        pages.extend(
            self._business_pages(
                site_name=site_name,
                businesses=businesses,
                categories=categories,
                locations=locations,
            )
        )

        pages.append(self._about_page(site_name))
        pages.append(self._contact_page(site_name))

        sorted_pages = tuple(sorted(pages, key=lambda p: p.path))

        assets = (
            StaticAsset(
                path="assets/css/site.css",
                content=self._site_css(),
                asset_type="css",
            ),
        )

        system_files = (
            StaticAsset(
                path="robots.txt",
                content=self._robots_txt(),
                asset_type="text",
            ),
            StaticAsset(
                path="sitemap.xml",
                content=self._sitemap_xml(sorted_pages),
                asset_type="xml",
            ),
        )

        manifest = self._manifest(
            project_slug=project_slug,
            pages=sorted_pages,
            assets=assets,
            system_files=system_files,
        )

        placeholder_report = WebsiteQualityReport(
            passed=True,
            critical_count=0,
            warning_count=0,
            issues=(),
        )

        package = StaticSitePackage(
            project_slug=project_slug,
            template_name=DEFAULT_TEMPLATE_NAME,
            pages=sorted_pages,
            assets=assets,
            system_files=system_files,
            manifest=manifest,
            quality_report=placeholder_report,
        )

        quality_report = self._quality_gate.validate(package)

        return StaticSitePackage(
            project_slug=project_slug,
            template_name=DEFAULT_TEMPLATE_NAME,
            pages=sorted_pages,
            assets=assets,
            system_files=system_files,
            manifest=manifest,
            quality_report=quality_report,
        )

    def _homepage(
        self,
        site_name: str,
        categories: tuple[CategoryRecord, ...],
        locations: tuple[LocationRecord, ...],
        businesses: tuple[BusinessRecord, ...],
    ) -> StaticPage:
        body = f"""
<main class="page">
<section class="hero">
<h2>{escape(site_name)} Directory</h2>
<p>Find trusted businesses, organized by category and location.</p>
</section>
<section>
<h2>Categories</h2>
{self._category_links(categories)}
</section>
<section>
<h2>Locations</h2>
{self._location_links(locations)}
</section>
<section>
<h2>Featured Listings</h2>
{self._business_cards(businesses[:12])}
</section>
</main>
"""

        return StaticPage(
            path="/",
            title=f"{site_name} Directory",
            html=render_page(f"{site_name} Directory", site_name, body),
            page_type="home",
            source_id="home",
        )

    def _category_pages(
        self,
        site_name: str,
        categories: tuple[CategoryRecord, ...],
        businesses: tuple[BusinessRecord, ...],
    ) -> tuple[StaticPage, ...]:
        pages: list[StaticPage] = []

        for category in categories:
            matched = tuple(
                business
                for business in businesses
                if business.category_id == category.category_id
            )

            title = f"{category.name} Directory"
            body = f"""
<main class="page">
<h2>{escape(title)}</h2>
<p>{escape(category.description or "Browse businesses in this category.")}</p>
{self._business_cards(matched)}
</main>
"""

            pages.append(
                StaticPage(
                    path=f"/categories/{category.slug}/",
                    title=title,
                    html=render_page(title, site_name, body),
                    page_type="category",
                    source_id=category.category_id,
                )
            )

        return tuple(pages)

    def _location_pages(
        self,
        site_name: str,
        locations: tuple[LocationRecord, ...],
        businesses: tuple[BusinessRecord, ...],
    ) -> tuple[StaticPage, ...]:
        pages: list[StaticPage] = []

        for location in locations:
            matched = tuple(
                business
                for business in businesses
                if business.location_id == location.location_id
            )

            title = f"{location.city}, {location.state} Directory"
            body = f"""
<main class="page">
<h2>{escape(title)}</h2>
<p>Browse businesses in {escape(location.city)}, {escape(location.state)}.</p>
{self._business_cards(matched)}
</main>
"""

            pages.append(
                StaticPage(
                    path=f"/locations/{location.slug}/",
                    title=title,
                    html=render_page(title, site_name, body),
                    page_type="location",
                    source_id=location.location_id,
                )
            )

        return tuple(pages)

    def _category_location_pages(
        self,
        site_name: str,
        categories: tuple[CategoryRecord, ...],
        locations: tuple[LocationRecord, ...],
        businesses: tuple[BusinessRecord, ...],
    ) -> tuple[StaticPage, ...]:
        pages: list[StaticPage] = []

        for category in categories:
            for location in locations:
                matched = tuple(
                    business
                    for business in businesses
                    if business.category_id == category.category_id
                    and business.location_id == location.location_id
                )

                title = f"{category.name} in {location.city}, {location.state}"
                body = f"""
<main class="page">
<h2>{escape(title)}</h2>
<p>Browse {escape(category.name)} listings in {escape(location.city)}, {escape(location.state)}.</p>
{self._business_cards(matched)}
</main>
"""

                pages.append(
                    StaticPage(
                        path=f"/categories/{category.slug}/locations/{location.slug}/",
                        title=title,
                        html=render_page(title, site_name, body),
                        page_type="category_location",
                        source_id=f"{category.category_id}:{location.location_id}",
                    )
                )

        return tuple(pages)

    def _business_pages(
        self,
        site_name: str,
        businesses: tuple[BusinessRecord, ...],
        categories: tuple[CategoryRecord, ...],
        locations: tuple[LocationRecord, ...],
    ) -> tuple[StaticPage, ...]:
        category_by_id = {category.category_id: category for category in categories}
        location_by_id = {location.location_id: location for location in locations}

        pages: list[StaticPage] = []

        for business in businesses:
            category = category_by_id.get(business.category_id)
            location = location_by_id.get(business.location_id)

            category_name = category.name if category else "Uncategorized"
            location_name = (
                f"{location.city}, {location.state}"
                if location
                else "Location unavailable"
            )

            body = f"""
<main class="page">
<article class="listing-detail">
<h2>{escape(business.name)}</h2>
<p class="muted">{escape(category_name)} · {escape(location_name)}</p>
<p>{escape(business.description or "No description available yet.")}</p>
{self._contact_block(business)}
</article>
</main>
"""

            pages.append(
                StaticPage(
                    path=f"/businesses/{business.slug}/",
                    title=business.name,
                    html=render_page(business.name, site_name, body),
                    page_type="business",
                    source_id=business.business_id,
                )
            )

        return tuple(pages)

    def _about_page(self, site_name: str) -> StaticPage:
        title = f"About {site_name}"
        body = f"""
<main class="page">
<h2>{escape(title)}</h2>
<p>{escape(site_name)} helps visitors find organized, useful directory listings.</p>
</main>
"""

        return StaticPage(
            path="/about/",
            title=title,
            html=render_page(title, site_name, body),
            page_type="about",
            source_id="about",
        )

    def _contact_page(self, site_name: str) -> StaticPage:
        title = f"Contact {site_name}"
        body = f"""
<main class="page">
<h2>{escape(title)}</h2>
<p>Contact information can be added by the site operator before launch.</p>
</main>
"""

        return StaticPage(
            path="/contact/",
            title=title,
            html=render_page(title, site_name, body),
            page_type="contact",
            source_id="contact",
        )

    def _category_links(self, categories: tuple[CategoryRecord, ...]) -> str:
        if not categories:
            return '<p class="empty">No categories available yet.</p>'

        links = [
            f'<a class="pill" href="/categories/{escape(category.slug)}/">{escape(category.name)}</a>'
            for category in categories
        ]

        return '<div class="pill-grid">' + "".join(links) + "</div>"

    def _location_links(self, locations: tuple[LocationRecord, ...]) -> str:
        if not locations:
            return '<p class="empty">No locations available yet.</p>'

        links = [
            f'<a class="pill" href="/locations/{escape(location.slug)}/">{escape(location.city)}, {escape(location.state)}</a>'
            for location in locations
        ]

        return '<div class="pill-grid">' + "".join(links) + "</div>"

    def _business_cards(self, businesses: Iterable[BusinessRecord]) -> str:
        cards = []

        for business in businesses:
            cards.append(
                f"""
<article class="card">
<h3><a href="/businesses/{escape(business.slug)}/">{escape(business.name)}</a></h3>
<p>{escape(business.description or "Directory listing.")}</p>
</article>
"""
            )

        if not cards:
            return '<p class="empty">No listings available yet.</p>'

        return '<div class="card-grid">' + "".join(cards) + "</div>"

    def _contact_block(self, business: BusinessRecord) -> str:
        rows = []

        if business.phone:
            rows.append(f"<p><strong>Phone:</strong> {escape(business.phone)}</p>")

        if business.website:
            rows.append(f"<p><strong>Website:</strong> {escape(business.website)}</p>")

        if not rows:
            return '<p class="empty">Contact details not available yet.</p>'

        return "\n".join(rows)

    def _robots_txt(self) -> str:
        return "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"

    def _sitemap_xml(self, pages: tuple[StaticPage, ...]) -> str:
        urls = "\n".join(
            f"<url><loc>{escape(page.path)}</loc></url>"
            for page in pages
        )

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}\n"
            "</urlset>\n"
        )

    def _site_css(self) -> str:
        return """* {
box-sizing: border-box;
}

body {
margin: 0;
font-family: Arial, sans-serif;
line-height: 1.5;
color: #172033;
background: #f7f8fb;
}

a {
color: inherit;
}

.site-header,
.site-footer {
background: #172033;
color: #ffffff;
padding: 24px;
}

.site-nav {
background: #ffffff;
border-bottom: 1px solid #dde2ea;
padding: 12px 24px;
}

.site-nav a {
font-weight: 700;
text-decoration: none;
}

.page {
max-width: 1100px;
margin: 0 auto;
padding: 32px 20px;
}

.hero {
background: #ffffff;
border: 1px solid #dde2ea;
border-radius: 12px;
padding: 28px;
margin-bottom: 28px;
}

.card-grid {
display: grid;
grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
gap: 16px;
}

.card {
background: #ffffff;
border: 1px solid #dde2ea;
border-radius: 12px;
padding: 18px;
}

.pill-grid {
display: flex;
flex-wrap: wrap;
gap: 10px;
}

.pill {
background: #ffffff;
border: 1px solid #dde2ea;
border-radius: 999px;
padding: 8px 14px;
text-decoration: none;
}

.empty,
.muted {
color: #667085;
}
"""

    def _manifest(
        self,
        project_slug: str,
        pages: tuple[StaticPage, ...],
        assets: tuple[StaticAsset, ...],
        system_files: tuple[StaticAsset, ...],
    ) -> StaticSiteManifest:
        files: list[StaticFileHash] = []

        for page in pages:
            files.append(self._file_hash(page.path, page.html))

        for asset in assets:
            files.append(self._file_hash(asset.path, asset.content))

        for system_file in system_files:
            files.append(self._file_hash(system_file.path, system_file.content))

        files = sorted(files, key=lambda f: f.path)

        fingerprint_source = "\n".join(
            f"{file.path}:{file.sha256}:{file.size_bytes}"
            for file in files
        )

        build_fingerprint = hashlib.sha256(
            fingerprint_source.encode("utf-8")
        ).hexdigest()

        site_id = hashlib.sha256(
            f"{project_slug}:{build_fingerprint}".encode("utf-8")
        ).hexdigest()[:16]

        return StaticSiteManifest(
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            template_name=DEFAULT_TEMPLATE_NAME,
            project_slug=project_slug,
            site_id=site_id,
            build_fingerprint=build_fingerprint,
            page_count=len(pages),
            asset_count=len(assets) + len(system_files),
            files=tuple(files),
        )

    @staticmethod
    def _file_hash(path: str, content: str) -> StaticFileHash:
        encoded = content.encode("utf-8")

        return StaticFileHash(
            path=path,
            sha256=hashlib.sha256(encoded).hexdigest(),
            size_bytes=len(encoded),
        )

    @staticmethod
    def _site_name(assembly: ProjectAssembly) -> str:
        return assembly.project_slug.replace("-", " ").title()

"""Section 3 — SEO Build Package Engine.

Deterministically derives the complete SEO surface from the import
package and blueprint: category pages, location pages, category ×
location pages, landing pages, FAQ pages, internal links, canonicals,
redirects, breadcrumbs, sitemap plan, and robots.txt recommendations.
"""

from __future__ import annotations

from engines.directory_builder.models import (
    ImportPackage,
    InternalLink,
    RedirectEntry,
    SeoBuildPackage,
    SeoPage,
    SitemapSection,
)
from engines.directory_builder.models import LaunchPackage
from engines.directory_builder.constants import (
    ID_PREFIX_PAGE,
    META_DESCRIPTION_MAX_LENGTH,
    PAGE_TYPE_CATEGORY,
    PAGE_TYPE_CATEGORY_LOCATION,
    PAGE_TYPE_FAQ,
    PAGE_TYPE_LANDING,
    PAGE_TYPE_LOCATION,
    REDIRECT_STATUS_CODE,
    ROBOTS_RECOMMENDATIONS,
    TITLE_MAX_LENGTH,
    URL_CATEGORY_PREFIX,
    URL_FAQ_PREFIX,
    URL_LOCATION_PREFIX,
)
from engines.directory_builder.deterministic import deterministic_id, truncate

ENGINE_VERSION = "1.0.0"


class SeoBuildEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def build(package: LaunchPackage, imports: ImportPackage) -> SeoBuildPackage:
        domain = package.blueprint.domain.rstrip("/")
        site_name = package.blueprint.project_name

        pages: list[SeoPage] = []
        links: list[InternalLink] = []

        def page(page_type: str, path: str, title: str, meta: str, crumbs: tuple[str, ...],
                 category_id: str = "", location_id: str = "") -> SeoPage:
            return SeoPage(
                page_id=deterministic_id(ID_PREFIX_PAGE, page_type, path),
                page_type=page_type,
                url_path=path,
                title=truncate(title, TITLE_MAX_LENGTH),
                meta_description=truncate(meta, META_DESCRIPTION_MAX_LENGTH),
                canonical_url=f"{domain}{path}" if domain else path,
                breadcrumbs=crumbs,
                category_id=category_id,
                location_id=location_id,
            )

        # Category pages
        for cat in imports.categories:
            path = f"{URL_CATEGORY_PREFIX}/{cat.slug}"
            pages.append(
                page(
                    PAGE_TYPE_CATEGORY,
                    path,
                    f"{cat.name} | {site_name}",
                    cat.description or f"Browse {cat.name} listings on {site_name}.",
                    ("Home", cat.name),
                    category_id=cat.category_id,
                )
            )
            links.append(InternalLink(from_path="/", to_path=path, anchor_text=cat.name))

        # Location pages
        for loc in imports.locations:
            path = f"{URL_LOCATION_PREFIX}/{loc.slug}"
            label = f"{loc.city}, {loc.state}"
            pages.append(
                page(
                    PAGE_TYPE_LOCATION,
                    path,
                    f"{label} | {site_name}",
                    f"Explore listings in {label} on {site_name}.",
                    ("Home", label),
                    location_id=loc.location_id,
                )
            )
            links.append(InternalLink(from_path="/", to_path=path, anchor_text=label))

        # Category × Location pages
        for cat in imports.categories:
            cat_path = f"{URL_CATEGORY_PREFIX}/{cat.slug}"
            for loc in imports.locations:
                loc_path = f"{URL_LOCATION_PREFIX}/{loc.slug}"
                path = f"{URL_CATEGORY_PREFIX}/{cat.slug}/{loc.slug}"
                label = f"{cat.name} in {loc.city}, {loc.state}"
                pages.append(
                    page(
                        PAGE_TYPE_CATEGORY_LOCATION,
                        path,
                        f"{label} | {site_name}",
                        f"Find {cat.name} in {loc.city}, {loc.state} on {site_name}.",
                        ("Home", cat.name, f"{loc.city}, {loc.state}"),
                        category_id=cat.category_id,
                        location_id=loc.location_id,
                    )
                )
                links.append(InternalLink(from_path=cat_path, to_path=path, anchor_text=label))
                links.append(InternalLink(from_path=loc_path, to_path=path, anchor_text=label))
                links.append(InternalLink(from_path=path, to_path=cat_path, anchor_text=cat.name))
                links.append(
                    InternalLink(from_path=path, to_path=loc_path, anchor_text=f"{loc.city}, {loc.state}")
                )

        # Landing pages from the launch package URL map (non-directory paths only)
        directory_paths = {p.url_path for p in pages}
        for entry in sorted(package.url_map, key=lambda e: e.path):
            if entry.path in directory_paths or entry.path == "/":
                continue
            pages.append(
                page(
                    PAGE_TYPE_LANDING,
                    entry.path,
                    (entry.title or entry.path.strip("/").replace("-", " ").title()) + f" | {site_name}",
                    f"{entry.title or site_name} — {package.blueprint.description or site_name}",
                    ("Home", entry.title or entry.path.strip("/")),
                )
            )

        # FAQ pages from the launch package SEO page list
        for entry in sorted(package.seo_pages, key=lambda e: e.slug):
            if entry.page_type != PAGE_TYPE_FAQ:
                continue
            path = f"{URL_FAQ_PREFIX}/{entry.slug}"
            if path in {p.url_path for p in pages}:
                continue
            pages.append(
                page(
                    PAGE_TYPE_FAQ,
                    path,
                    (entry.title or entry.slug.replace("-", " ").title()) + f" | {site_name}",
                    entry.meta_description or f"Frequently asked questions about {site_name}.",
                    ("Home", "FAQ", entry.title or entry.slug),
                )
            )

        pages.sort(key=lambda p: p.url_path)
        links.sort(key=lambda l: (l.from_path, l.to_path))

        # Redirects: trailing-slash canonicalization for every page.
        redirects = tuple(
            RedirectEntry(from_path=p.url_path + "/", to_path=p.url_path, status_code=REDIRECT_STATUS_CODE)
            for p in pages
            if p.url_path != "/"
        )

        sitemap_plan = SeoBuildEngine._sitemap_plan(pages)

        return SeoBuildPackage(
            pages=tuple(pages),
            internal_links=tuple(links),
            redirects=redirects,
            sitemap_plan=sitemap_plan,
            robots_recommendations=tuple(ROBOTS_RECOMMENDATIONS),
        )

    @staticmethod
    def _sitemap_plan(pages: list[SeoPage]) -> tuple[SitemapSection, ...]:
        sections: dict[str, list[str]] = {}
        for p in pages:
            sections.setdefault(p.page_type, []).append(p.url_path)
        return tuple(
            SitemapSection(name=f"sitemap-{name}.xml", paths=tuple(sorted(paths)))
            for name, paths in sorted(sections.items())
        )

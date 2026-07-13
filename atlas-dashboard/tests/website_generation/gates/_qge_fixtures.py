"""Shared builders for the AES-WEB-002J.11 Quality Gate Engine tests.

Two paths are exercised:

* ``real_bundle`` builds a genuine SiteBundle by driving the real
  Renderer + Assembly over hand-composed component instances -- the honest
  end-to-end integration input.
* ``bundle_from_html`` wraps arbitrary HTML in a minimal valid SiteBundle so
  the two-fixture law (good page + each single-defect page) can be exercised
  per gate without re-driving the whole pipeline.

Kept in a ``_``-prefixed module (not this package's ``__init__``) so it is
importable by the gate tests without altering the existing
``tests/website_generation/gates`` package surface.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from engines.website_generation.assembly.assembly_engine import AssemblyEngine
from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BundleFile,
    BusinessSpec,
    ComponentInstance,
    ComponentManifest,
    ComponentPlacement,
    ContentBlock,
    ContentPackage,
    LayoutPlan,
    LayoutRegion,
    PageComponents,
    PageLayout,
    RegionLayoutDetail,
    SEOEntry,
    SEOPackage,
    SiteArchitecture,
    SiteBundle,
    canonical_json,
    sha256_of_text,
)
from engines.website_generation.contracts.enums import ArtifactKind, RegionKind
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS
from engines.website_generation.rendering.renderer import Renderer

# A complete, clean single page: doctype, exactly one html/head/body, a
# labeled nav in a <header>, one <main id="main"> with a correct heading
# order and a single (non-nested) control, and a <footer>. Passes all eight
# evaluated gates.
GOOD_PAGE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    "<title>Clean</title></head>"
    '<body class="ac-layout ac-layout--shell-page">'
    '<header><nav aria-label="Main"><a href="/about">About</a></nav></header>'
    '<main id="main"><h1>Heading</h1><h2>Sub</h2>'
    '<button type="button">Go</button></main>'
    "<footer><p>Legal</p></footer></body></html>"
)


def brand_package(**overrides) -> BrandPackage:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BRAND_PACKAGE],
        artifact_kind=ArtifactKind.BRAND_PACKAGE,
        source_hashes={},
    )
    fields.update(overrides)
    return BrandPackage(**fields)


def seo_package(entries=None, sitemap=("/",), robots=("User-agent: *", "Allow: /")) -> SEOPackage:
    if entries is None:
        entries = (SEOEntry(route="/", title="T", meta_description="M", canonical_url="/"),)
    return SEOPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SEO_PACKAGE],
        artifact_kind=ArtifactKind.SEO_PACKAGE,
        source_hashes={},
        entries=tuple(entries),
        sitemap_routes=tuple(sitemap),
        robots_directives=tuple(robots),
    )


def content_package(blocks=()) -> ContentPackage:
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )


def site_architecture() -> SiteArchitecture:
    return SiteArchitecture(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
    )


def bundle_from_html(pages: Dict[str, str], shared_css: str = ":root{}") -> SiteBundle:
    """Wrap ``{output_path: html}`` (plus a styles.css) in a valid
    SiteBundle whose file_map hashes match the content."""
    files = [BundleFile(path=path, content=html) for path, html in sorted(pages.items())]
    files.append(BundleFile(path="styles.css", content=shared_css))
    file_map = {bf.path: sha256_of_text(bf.content) for bf in files}
    return SiteBundle(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_BUNDLE],
        artifact_kind=ArtifactKind.SITE_BUNDLE,
        source_hashes={},
        file_map=file_map,
        bundle_hash=sha256_of_text(canonical_json(file_map)),
        files=tuple(files),
    )


def real_bundle(routes: Iterable[str] = ("/",)) -> Tuple[SiteBundle, SEOPackage, ContentPackage, SiteArchitecture]:
    """Drive the real Renderer + Assembly over a hand-composed page per route
    (skip link + labeled header nav + hero H1 + body button + footer), so
    every evaluated gate sees genuine emitted-and-assembled HTML. Returns the
    four §5.10 QualityGateEngine inputs."""
    registry = build_default_registry()
    brand = BrandEngine().resolve(
        BusinessSpec(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.BUSINESS_SPEC,
            source_hashes={},
            business_name="PetTripFinder",
            niche="pet travel",
            audience="pet owners",
            value_proposition="find stays",
        )
    )  # the resolved BrandPackage instance, reused by Renderer and Assembly
    # Reuse the rendering suite's contract-driven fixture builder so every
    # component instance is bound exactly as its registered contract
    # requires (props/slots), rather than hand-binding each one here.
    from website_generation.rendering import minimal_fixture_for

    # (component_id, RegionKind) for a page that yields header/main/footer
    # landmarks, a single H1, a skip link, and a non-nested control.
    _LAYOUT = (
        ("nav.skip.link", RegionKind.SKIP),
        ("nav.header.standard", RegionKind.HEADER),
        ("hero.local.standard", RegionKind.HERO),
        ("atom.button.action", RegionKind.BODY),
        ("legal.footer.directory", RegionKind.FOOTER),
    )
    routes = tuple(routes)
    m_pages, l_pages, c_blocks, r_details, seo_entries = [], [], [], [], []
    for route in routes:
        instances, regions, details = [], [], []
        for idx, (component_id, kind) in enumerate(_LAYOUT):
            definition = registry.get(component_id)
            instance, blocks = minimal_fixture_for(definition, route)
            instances.append(instance)
            c_blocks.extend(blocks)
            regions.append(LayoutRegion(region_id=kind.value, component_indexes=(idx,)))
            details.append(
                RegionLayoutDetail(
                    route=route,
                    region_id=kind.value,
                    region_kind=kind,
                    placements=(ComponentPlacement(component_index=idx),),
                )
            )
        m_pages.append(PageComponents(route=route, components=tuple(instances)))
        l_pages.append(PageLayout(route=route, regions=tuple(regions)))
        r_details.extend(details)
        seo_entries.append(
            SEOEntry(route=route, title="Title " + route, meta_description="Meta", canonical_url=route)
        )

    manifest = ComponentManifest(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST],
        artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
        source_hashes={},
        pages=tuple(m_pages),
    )
    content = content_package(c_blocks)
    layout = LayoutPlan(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LAYOUT_PLAN],
        artifact_kind=ArtifactKind.LAYOUT_PLAN,
        source_hashes={},
        pages=tuple(l_pages),
        region_details=tuple(r_details),
    )
    rendered = Renderer(registry).render(layout, manifest, content, brand)
    seo = seo_package(entries=seo_entries, sitemap=routes)
    bundle = AssemblyEngine().assemble(rendered, seo, brand)
    return bundle, seo, content, site_architecture()

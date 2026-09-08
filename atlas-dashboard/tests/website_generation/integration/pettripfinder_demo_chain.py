"""The real PetTripFinder demo-media chain, shared by the demo-media modules.

ATLAS-THROUGHPUT-007. This is test SUPPORT, not a test module: it holds the one
implementation of the runner's chain (load -> optional ingest -> build -> IA ->
compile -> render -> assemble) so the three demo-media modules assert against
the same code rather than three copies of it.

Why the modules are split at all: ATLAS-THROUGHPUT-006 measured this chain at
about 265 s per execution, and the single module that held every claim ran it
FIVE times for 1,375.7 s -- 38% of the whole broad suite, and the floor under
every sharded remote run, since no split into jobs can finish faster than its
slowest indivisible module.

The split is by CLAIM, not by filename:

* ``test_pettripfinder_demo_media.py`` -- manifest validation, ingestion, HTML,
  bundle and request safety. Every one of those asserts about the RESULT of one
  chain, so they share one module-scoped build.
* ``test_pettripfinder_demo_media_determinism.py`` -- the determinism claim,
  which needs two genuinely independent executions and therefore keeps both.
* ``test_pettripfinder_demo_media_fallback.py`` -- the zero-image claim, whose
  input (no media manifest) is genuinely different.

Splitting only helps when the modules do NOT each rebuild the same fixture. Here
they do not: the three modules build three DIFFERENT things (one with-media
chain shared by its consumers, two independent chains whose comparison is the
claim, and one no-media chain).
"""

from __future__ import annotations

import pathlib
import re
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.website_generation.assembly.assembly_engine import AssemblyEngine  # noqa: E402
from engines.website_generation.brand.brand_engine import BrandEngine  # noqa: E402
from engines.website_generation.components.component_engine import ComponentEngine  # noqa: E402
from engines.website_generation.components.registry import build_default_registry  # noqa: E402
from engines.website_generation.contracts.artifacts import (  # noqa: E402
    ArtifactKind,
    BusinessSpec,
)
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS  # noqa: E402
from engines.website_generation.ia.information_architecture_engine import (  # noqa: E402
    InformationArchitectureEngine,
)
from engines.website_generation.layouts.layout_engine import LayoutEngine  # noqa: E402
from engines.website_generation.rendering.renderer import Renderer  # noqa: E402
from engines.website_generation.seo.seo_engine import SEOEngine  # noqa: E402
from repositories.artifact_store_repository import ArtifactStoreRepository  # noqa: E402
from scripts.generate_pettripfinder_pilot import (  # noqa: E402
    LAUNCH_PACKAGE_DIR,
    build_content_package,
    load_launch_package,
)
from scripts.pettripfinder import market_authority as MA  # noqa: E402
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset  # noqa: E402
from scripts.pettripfinder.media_ingestion import (  # noqa: E402
    ingest_demo_media,
    load_demo_media_manifest,
)
from scripts.pettripfinder.publication_guard import distinct_entity_groups  # noqa: E402

IMG_TAG_RE = re.compile(r"<img [^>]*>")
SRC_RE = re.compile(r'src="([^"]*)"')

# The committed manifest's intent (kept in sync with demo_media.json -- these
# tests fail loudly if the manifest and this expectation diverge).
IMAGED_SLUGS = {"scioto-audubon-metro-park", "land-grant-brewing-company"}
IMAGELESS_SLUG = "hyatt-regency-columbus"


def expected_by_category():
    """Seeded listings per category, summed from the per-market authority
    shards (PTF-MARKET-AUTHORITY-SHARDING-001)."""
    counts = {}
    for market_id in MA.sharded_market_ids():
        for row in MA.load_market_seed_rows(market_id):
            counts[row["category"]] = counts.get(row["category"], 0) + 1
    return counts


def real_chain(tmp_path, *, with_media: bool):
    """The runner's exact chain, media-optional.

    Returns ``(dataset, rendered, bundle, cas)``. Every execution is a genuine
    cold run of the real engines over the committed launch package: nothing
    here consults a cache, so a caller that needs an independent execution gets
    one by calling again.
    """
    package = load_launch_package()
    media_by_key = {}
    cas = None
    if with_media:
        entries = load_demo_media_manifest(LAUNCH_PACKAGE_DIR)
        cas = ArtifactStoreRepository(tmp_path / "cas")
        media_by_key = ingest_demo_media(entries, LAUNCH_PACKAGE_DIR, cas)
    result = build_listing_dataset(
        seed_businesses=package["seed_businesses"],
        categories=package["categories"],
        locations=package["locations"],
        media_by_key=media_by_key,
        distinct_entity_groups=distinct_entity_groups(),
    )
    assert result.ok
    dataset = result.dataset

    pilot_config = package["pilot_config"]
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name=pilot_config["project_name"],
        niche=pilot_config["niche"],
        audience=pilot_config["audience"],
        value_proposition=pilot_config["value_proposition"],
        directory_taxonomy=tuple(c["name"] for c in pilot_config["launch_categories"]),
        monetization_model=pilot_config["monetization_model"],
        geography=pilot_config["geography"],
    )
    brand = BrandEngine().resolve(spec)
    editorial_pages = tuple((p["route"], p["title"]) for p in pilot_config["editorial_pages"])
    site = InformationArchitectureEngine().plan(
        spec, brand, listing_dataset=dataset, editorial_pages=editorial_pages,
    )
    category_routes = {c.slug: "/%s/" % c.slug for c in dataset.categories}
    content = build_content_package(
        package["pilot_content"], category_routes, dataset, dict(editorial_pages),
    )
    registry = build_default_registry()
    compilation = ComponentEngine().compile(
        site, content, listing_dataset=dataset, brand_package=brand, registry=registry,
    )
    layout = LayoutEngine(registry).compose(compilation.component_manifest, brand)
    rendered = Renderer(registry).render(
        layout, compilation.component_manifest, compilation.content_package, brand,
        render_data=compilation.render_data,
    )
    seo = SEOEngine().compile(site, compilation.content_package, spec,
                              base_url=pilot_config["base_url"])
    bundle = AssemblyEngine().assemble(rendered, seo, brand, listing_dataset=dataset)
    return dataset, rendered, bundle, cas

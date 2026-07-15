"""
scripts/generate_pettripfinder_pilot.py

================================================================================
PILOT-PTF-1 PILOT GENERATION RUNNER
NOT PRODUCTION PIPELINE WIRING
================================================================================

Drives the full real Website Generation Engine chain (BrandEngine -> IA ->
Component Engine -> LayoutEngine -> Renderer -> SEOEngine -> AssemblyEngine
-> QualityGateEngine -> SiteBundleRepository) against real PetTripFinder
launch-package inputs (``launch_packages/pettripfinder/``), converting real
seed data through ``scripts/pettripfinder/listing_dataset_builder.py`` into
a ``ListingDataset`` -- never a hand-built or fabricated one.

No network. No LLM calls. No production pipeline wiring (``component_
resolution``/``ia_planning``/etc. all remain ``NOT_EXECUTED`` in any
``BuildManifest`` -- this script never touches the state machine). Never
mutates any file under ``launch_packages/``.

Two modes:

* Default (production-intent) mode: computes inventory readiness against
  the approved launch thresholds (``pilot_config.json``'s
  ``inventory_thresholds``) and FAILS CLOSED -- refuses to materialize a
  site and prints an honest "NOT LAUNCH READY" readiness report -- when the
  real launch-package inventory does not meet them. The current real sample
  package (3 unique listings) always fails this check; that is the correct,
  honest behavior, not a bug.
* ``--allow-sample``: explicitly bypasses the fail-closed gate to generate
  a technical/demo site from the (currently insufficient) real sample
  package anyway, for local visual inspection only. Always prints
  "NOT LAUNCH READY" even when it proceeds. Never silently bypasses the
  check -- the flag must be passed explicitly.

Run from:

    C:\\Atlas\\atlas-dashboard

Example:

    python scripts\\generate_pettripfinder_pilot.py --allow-sample
    python scripts\\generate_pettripfinder_pilot.py --allow-sample --output generated-sites/pettripfinder-pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.website_generation.assembly.assembly_engine import AssemblyEngine
from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components.component_engine import ComponentEngine
from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.contracts.artifacts import (
    ArtifactKind,
    BusinessSpec,
    ContentBlock,
    ContentPackage,
)
from engines.website_generation.contracts.enums import GateSeverity
from engines.website_generation.contracts.errors import (
    ArchitecturePlanningError,
    AssemblyError,
    ComponentResolutionError,
    GateExecutionError,
    RenderError,
    SEOCompilationError,
    SiteBundleRepositoryError,
)
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS
from engines.website_generation.gates.quality_gate_engine import QualityGateEngine
from engines.website_generation.ia.information_architecture_engine import (
    InformationArchitectureEngine,
)
from engines.website_generation.layouts.layout_engine import LayoutEngine
from engines.website_generation.rendering.renderer import Renderer
from engines.website_generation.seo.seo_engine import SEOEngine
from repositories.site_bundle_repository import SiteBundleRepository
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset

RUNNER_NAME = "PILOT-PTF-1 PetTripFinder Pilot Generation Runner (NOT production pipeline wiring)"
DEFAULT_OUTPUT = "generated-sites/pettripfinder-pilot"
LAUNCH_PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_launch_package() -> Dict[str, Any]:
    """Read the real launch-package files. File I/O lives here, never in
    the pure converter/engine layers."""
    return {
        "blueprint": _read_json(LAUNCH_PACKAGE_DIR / "blueprint.json"),
        "seed_businesses": _read_json(LAUNCH_PACKAGE_DIR / "seed_businesses.json"),
        "categories": _read_json(LAUNCH_PACKAGE_DIR / "categories.json"),
        "locations": _read_json(LAUNCH_PACKAGE_DIR / "locations.json"),
        "pilot_config": _read_json(LAUNCH_PACKAGE_DIR / "pilot_config.json"),
        "pilot_content": _read_json(LAUNCH_PACKAGE_DIR / "pilot_content.json"),
    }


def compute_inventory_readiness(dataset, thresholds: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic readiness report -- never blocks the automated
    acceptance fixture (that fixture never calls this function; it is
    exclusively a production/real-package concern)."""
    counts: Dict[str, int] = {}
    for listing in dataset.listings:
        counts[listing.category_id] = counts.get(listing.category_id, 0) + 1
    slug_by_id = {c.category_id: c.slug for c in dataset.categories}
    counts_by_slug = {slug_by_id.get(cid, cid): n for cid, n in counts.items()}

    total = len(dataset.listings)
    min_total = thresholds["minimum_total_listings"]
    min_per_category = thresholds["minimum_per_category"]
    required_categories = thresholds["required_categories"]

    below_target = sorted(
        cat for cat in required_categories if counts_by_slug.get(cat, 0) < min_per_category
    )
    ready = total >= min_total and not below_target

    return {
        "total_unique_listings": total,
        "counts_by_category": counts_by_slug,
        "minimum_total_listings": min_total,
        "minimum_per_category": min_per_category,
        "categories_below_target": below_target,
        "launch_inventory_ready": ready,
    }


def build_content_package(
    pilot_content: Dict[str, Any], category_routes: Dict[str, str], listing_dataset,
    editorial_routes: Dict[str, str],
) -> ContentPackage:
    blocks: List[ContentBlock] = []
    home = pilot_content["home"]
    blocks.append(ContentBlock(page_route="/", slot_id="hero_h1", text=home["hero_h1"]))
    blocks.append(ContentBlock(page_route="/", slot_id="intro", text=home["intro"]))
    blocks.append(ContentBlock(page_route="/", slot_id="subhead", text=home["subhead"]))
    blocks.append(ContentBlock(page_route="/", slot_id="message", text=home["message"]))

    for slug, route in category_routes.items():
        cat_content = pilot_content["categories"].get(slug)
        if cat_content is None:
            continue
        blocks.append(ContentBlock(page_route=route, slot_id="hero_h1", text=cat_content["hero_h1"]))
        blocks.append(ContentBlock(page_route=route, slot_id="intro", text=cat_content["intro"]))

    for listing in listing_dataset.listings:
        cat_slug = next(
            (c.slug for c in listing_dataset.categories if c.category_id == listing.category_id), ""
        )
        route = "%s%s/" % (category_routes[cat_slug], listing.slug)
        blocks.append(ContentBlock(page_route=route, slot_id="hero_h1", text=listing.business_name))
        blocks.append(ContentBlock(page_route=route, slot_id="intro", text=listing.description or listing.business_name))

    for route, page_content in pilot_content["editorial_pages"].items():
        blocks.append(ContentBlock(page_route=route, slot_id="hero_h1", text=page_content["hero_h1"]))
        blocks.append(ContentBlock(page_route=route, slot_id="intro", text=page_content["intro"]))
        blocks.append(ContentBlock(page_route=route, slot_id="body", text=page_content["body"]))

    footer = pilot_content["footer"]
    all_routes = ["/"] + list(category_routes.values()) + [
        "%s%s/" % (category_routes[next(c.slug for c in listing_dataset.categories if c.category_id == l.category_id)], l.slug)
        for l in listing_dataset.listings
    ] + list(pilot_content["editorial_pages"].keys())
    for route in all_routes:
        blocks.append(ContentBlock(page_route=route, slot_id="footer_legal", text=footer["legal_text"]))
        blocks.append(ContentBlock(page_route=route, slot_id="disclosures", text=footer["disclosures"]))

    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )


def run_pilot(*, allow_sample: bool, output: str, build_id: Optional[str]) -> int:
    print(RUNNER_NAME)
    print("=" * len(RUNNER_NAME))

    package = load_launch_package()
    pilot_config = package["pilot_config"]

    result = build_listing_dataset(
        seed_businesses=package["seed_businesses"],
        categories=package["categories"],
        locations=package["locations"],
    )
    if result.rejected_duplicates:
        print("Deduplicated %d duplicate record(s): %s" % (
            len(result.rejected_duplicates), ", ".join(result.rejected_duplicates),
        ))
    if not result.ok:
        print("ListingDataset conversion FAILED:")
        for err in result.errors:
            print("  - %s" % err)
        return 2

    dataset = result.dataset
    readiness = compute_inventory_readiness(dataset, pilot_config["inventory_thresholds"])
    print("Inventory readiness:")
    print("  total unique listings: %d" % readiness["total_unique_listings"])
    print("  counts by category: %s" % readiness["counts_by_category"])
    print("  categories below target: %s" % readiness["categories_below_target"])
    print("  launch_inventory_ready: %s" % readiness["launch_inventory_ready"])

    if not readiness["launch_inventory_ready"]:
        print()
        print("NOT LAUNCH READY: real inventory is below the approved launch threshold.")
        if not allow_sample:
            print("Refusing to generate a production site (fail-closed). "
                  "Pass --allow-sample to generate a technical/demo site anyway.")
            return 1
        print("--allow-sample supplied: generating a technical/demo site anyway. "
              "This output is NOT LAUNCH READY and must not be published.")

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

    editorial_pages = tuple(
        (p["route"], p["title"]) for p in pilot_config["editorial_pages"]
    )
    try:
        site_architecture = InformationArchitectureEngine().plan(
            spec, brand, listing_dataset=dataset, editorial_pages=editorial_pages,
        )
    except ArchitecturePlanningError as exc:
        print("Site architecture planning FAILED: %s" % exc.diagnostics)
        return 2

    category_routes = {c.slug: "/%s/" % c.slug for c in dataset.categories}
    content_package = build_content_package(
        package["pilot_content"], category_routes, dataset,
        {r: t for r, t in editorial_pages},
    )

    registry = build_default_registry()
    try:
        compilation = ComponentEngine().compile(
            site_architecture, content_package,
            listing_dataset=dataset, brand_package=brand, registry=registry,
        )
    except ComponentResolutionError as exc:
        print("Component compilation FAILED: %s" % exc.diagnostics)
        return 2

    layout = LayoutEngine(registry).compose(compilation.component_manifest, brand)
    try:
        rendered = Renderer(registry).render(
            layout, compilation.component_manifest, compilation.content_package, brand,
            render_data=compilation.render_data,
        )
    except RenderError as exc:
        print("Rendering FAILED: %s" % exc.diagnostics)
        return 2

    try:
        seo_package = SEOEngine().compile(
            site_architecture, compilation.content_package, spec, base_url=pilot_config["base_url"],
        )
    except SEOCompilationError as exc:
        print("SEO compilation FAILED: %s" % exc.diagnostics)
        return 2

    try:
        # AES-WEB-002M.2: the dataset flows into assembly so any bundle-
        # authorized listing assets enter the bundle's asset map (M.1). The
        # current sample package carries no media, so this adds only the
        # listing_dataset source-hash provenance -- file_map/bundle_hash
        # are byte-identical to pre-M.2 output.
        bundle = AssemblyEngine().assemble(
            rendered, seo_package, brand, listing_dataset=dataset,
        )
    except AssemblyError as exc:
        print("Assembly FAILED: %s" % exc.diagnostics)
        return 2

    try:
        report = QualityGateEngine().evaluate(bundle, seo_package, compilation.content_package, site_architecture)
    except GateExecutionError as exc:
        print("Quality gate evaluation FAILED: %s" % exc.diagnostics)
        return 2

    blocking = [g for g in report.gate_results if g.severity == GateSeverity.BLOCKING and not g.passed]

    if bundle.assets:
        # Fail-closed (AES-WEB-002M.2): the sample runner has no CAS to
        # fetch asset bytes from -- a media-carrying dataset can only reach
        # this runner through a future operator-ingestion path that also
        # supplies the byte source. Refuse loudly rather than let the
        # repository fail deeper with a less actionable message.
        print("Materialization REFUSED: bundle declares %d media asset(s) but this "
              "runner has no asset byte source wired (operator media ingestion is "
              "not part of the sample path)." % len(bundle.assets))
        return 2

    try:
        materialization = SiteBundleRepository().materialize(bundle, output, build_id=build_id)
    except SiteBundleRepositoryError as exc:
        print("Materialization FAILED: %s" % exc.diagnostics)
        return 2

    print()
    print("Run summary:")
    print("  route count: %d" % len(rendered.page_details))
    print("  listing count: %d" % len(dataset.listings))
    print("  category counts: %s" % readiness["counts_by_category"])
    print("  launch_inventory_ready: %s" % readiness["launch_inventory_ready"])
    print("  blocking gate count: %d" % len(blocking))
    print("  bundle hash: %s" % materialization.bundle_hash)
    print("  output path: %s" % materialization.destination)
    if not readiness["launch_inventory_ready"]:
        print()
        print("NOT LAUNCH READY. This output must not be published.")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=RUNNER_NAME)
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output directory for the materialized site.")
    parser.add_argument("--build-id", default=None, help="Optional build id recorded in the bundle manifest.")
    parser.add_argument(
        "--allow-sample", action="store_true",
        help="Generate a technical/demo site even though real inventory is below the launch threshold. "
             "Output is always printed as NOT LAUNCH READY.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    return run_pilot(allow_sample=args.allow_sample, output=args.output, build_id=args.build_id)


if __name__ == "__main__":
    raise SystemExit(main())

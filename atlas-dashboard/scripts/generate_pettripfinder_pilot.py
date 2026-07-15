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
from repositories.artifact_store_repository import ArtifactStoreRepository
from repositories.site_bundle_repository import SiteBundleRepository
from scripts.pettripfinder.inventory_validation import (
    assess_inventory,
    compute_launch_readiness,
    format_readiness_report,
)
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset
from scripts.pettripfinder.media_ingestion import (
    MediaIngestionError,
    ingest_demo_media,
    load_demo_media_manifest,
)

RUNNER_NAME = "PILOT-PTF-1 PetTripFinder Pilot Generation Runner (NOT production pipeline wiring)"
DEFAULT_OUTPUT = "generated-sites/pettripfinder-pilot"
LAUNCH_PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_amenities(cell: str) -> List[str]:
    """Amenities cell: semicolon-separated tokens (the operator-friendly
    form), with the legacy JSON-array-in-cell form still accepted."""
    cell = (cell or "").strip()
    if not cell:
        return []
    if cell.startswith("["):
        return [str(a).strip() for a in json.loads(cell) if str(a).strip()]
    return [token.strip() for token in cell.split(";") if token.strip()]


def read_seed_businesses_csv(path: Path) -> List[Dict[str, Any]]:
    """Read the primary operator-editable inventory input (AES-WEB-002N.1:
    the launch package CSV is the seed authority -- one spreadsheet row per
    candidate listing). Empty cells become absent fields; the pure builder
    performs all semantic validation."""
    import csv

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row: Dict[str, Any] = {
                key: value.strip()
                for key, value in raw.items()
                if key is not None and value is not None and value.strip()
            }
            row["amenities"] = _parse_amenities(str(raw.get("amenities", "")))
            rows.append(row)
    return rows


def load_launch_package() -> Dict[str, Any]:
    """Read the real launch-package files. File I/O lives here, never in
    the pure converter/engine layers. AES-WEB-002N.1: seed businesses come
    from the operator-editable CSV (the promoted primary inventory input --
    the legacy seed_businesses.json was removed with it)."""
    return {
        "blueprint": _read_json(LAUNCH_PACKAGE_DIR / "blueprint.json"),
        "seed_businesses": read_seed_businesses_csv(LAUNCH_PACKAGE_DIR / "seed_businesses.csv"),
        "categories": _read_json(LAUNCH_PACKAGE_DIR / "categories.json"),
        "locations": _read_json(LAUNCH_PACKAGE_DIR / "locations.json"),
        "pilot_config": _read_json(LAUNCH_PACKAGE_DIR / "pilot_config.json"),
        "pilot_content": _read_json(LAUNCH_PACKAGE_DIR / "pilot_content.json"),
    }


def compute_inventory_readiness(
    dataset, thresholds: Dict[str, Any], reference_date: str = "",
) -> Dict[str, Any]:
    """Deterministic readiness verdict (AES-WEB-002N.1): per-listing
    publish-grade assessment (READY / READY_WITH_WARNINGS / NOT_READY) via
    ``inventory_validation.assess_inventory``, with the strict launch
    threshold counting **READY listings only** and any NOT_READY listing
    blocking launch (operator decisions 1/2/8/9). ``reference_date``
    (ISO date) enables staleness warnings; empty skips them --
    deterministic tests pass fixed dates, the runner passes today
    (console-report-only; no durable artifact carries it)."""
    assessments = assess_inventory(dataset, reference_date=reference_date)
    readiness = compute_launch_readiness(assessments, thresholds)

    counts: Dict[str, int] = {}
    slug_by_id = {c.category_id: c.slug for c in dataset.categories}
    for listing in dataset.listings:
        slug = slug_by_id.get(listing.category_id, listing.category_id)
        counts[slug] = counts.get(slug, 0) + 1

    readiness["total_unique_listings"] = len(dataset.listings)
    readiness["counts_by_category"] = counts
    readiness["assessments"] = assessments
    return readiness


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

    # AES-WEB-002M.3: optional repository-owned demo media. A missing
    # demo_media.json means a zero-media pilot (media activation is
    # optional configuration, never mandatory architecture); a present
    # manifest ingests each image through the real M.2 path (signature
    # validation -> dimension parse -> CAS.put_bytes) into the builder's
    # media_by_key overlay. The CAS lives at the §9.1 layout root
    # (data/wge/cas -- content-addressed local storage, never committed).
    demo_media_cas = None
    media_by_key = {}
    try:
        demo_entries = load_demo_media_manifest(LAUNCH_PACKAGE_DIR)
        if demo_entries:
            demo_media_cas = ArtifactStoreRepository(_REPO_ROOT / "data" / "wge" / "cas")
            media_by_key = ingest_demo_media(demo_entries, LAUNCH_PACKAGE_DIR, demo_media_cas)
            print("Demo media: ingested %d image(s) for %d listing key(s)." % (
                sum(len(refs) for refs in media_by_key.values()), len(media_by_key),
            ))
    except MediaIngestionError as exc:
        print("Demo media ingestion FAILED (%s): %s" % (exc.reason, exc))
        return 2

    result = build_listing_dataset(
        seed_businesses=package["seed_businesses"],
        categories=package["categories"],
        locations=package["locations"],
        media_by_key=media_by_key,
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
    # Staleness is assessed against today's calendar date -- a script-layer
    # console-report concern only; no durable artifact carries it, so build
    # output determinism is unaffected (inventory_validation docstring).
    from datetime import date as _date

    readiness = compute_inventory_readiness(
        dataset, pilot_config["inventory_thresholds"],
        reference_date=_date.today().isoformat(),
    )
    print(format_readiness_report(
        readiness["assessments"], readiness, result.rejected_duplicates,
    ))

    if not readiness["launch_inventory_ready"]:
        print()
        print("NOT LAUNCH READY: validated READY inventory is below the approved launch threshold.")
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

    asset_bytes = None
    if bundle.assets:
        if demo_media_cas is None:
            # Fail-closed: a media-carrying bundle with no byte source is a
            # wiring defect -- refuse loudly rather than let the repository
            # fail deeper with a less actionable message.
            print("Materialization REFUSED: bundle declares %d media asset(s) but "
                  "no asset byte source is wired." % len(bundle.assets))
            return 2
        # AES-WEB-002M.3: compose the M.1 asset_bytes mapping from the same
        # CAS ingestion just wrote to -- get_bytes re-verifies each hash.
        asset_bytes = {
            asset.asset_hash: demo_media_cas.get_bytes(asset.asset_hash)
            for asset in bundle.assets
        }

    try:
        materialization = SiteBundleRepository().materialize(
            bundle, output, build_id=build_id, asset_bytes=asset_bytes,
        )
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
    print("  bundled media assets: %d" % len(bundle.assets))
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

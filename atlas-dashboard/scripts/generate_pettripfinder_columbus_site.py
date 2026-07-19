"""AES-SITE-001 -- PetTripFinder Columbus PUBLIC SITE BUILD runner.

Real production entrypoint (unlike ``scripts/generate_pettripfinder_pilot.py``,
which is explicitly "NOT PRODUCTION PIPELINE WIRING" and exists for local
visual inspection of arbitrary/sample data). This script:

1. Runs the exact same proven AES-WEB chain the pilot script does, against
   the REAL, launch-ready Columbus inventory (52 READY listings; refuses to
   proceed if the fail-closed inventory gate does not pass -- no
   ``--allow-sample`` seam exists here at all).
2. Materializes the base bundle via the real ``SiteBundleRepository``.
3. Applies the ``site_enrichment``/``site_pages`` layer: pet-policy fact
   tables, verification badges, JSON-LD, breadcrumbs, nearby relationships,
   the ``/go/`` commercial-action layer, the comparison page, corridor
   pages, and a rewritten hub/methodology page.
4. Regenerates ``sitemap.xml``/``robots.txt``/``llms.txt`` to cover the
   enriched route set.
5. Writes a build report, a quality report, and a broken-link report.

No network. No LLM calls. Never mutates ``launch_packages/`` or any
importer/discovery operational data -- reads them, never writes them.

Run from C:\\Atlas\\atlas-dashboard:

    python scripts\\generate_pettripfinder_columbus_site.py
        [--output data/site_builds/pettripfinder_columbus]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.website_generation.assembly.assembly_engine import AssemblyEngine
from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components.component_engine import ComponentEngine
from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.contracts.artifacts import ArtifactKind, BusinessSpec
from engines.website_generation.contracts.enums import GateSeverity
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS
from engines.website_generation.gates.quality_gate_engine import QualityGateEngine
from engines.website_generation.ia.information_architecture_engine import (
    InformationArchitectureEngine,
)
from engines.website_generation.layouts.layout_engine import LayoutEngine
from engines.website_generation.rendering.renderer import Renderer
from engines.website_generation.seo.seo_engine import SEOEngine
from repositories.site_bundle_repository import SiteBundleRepository
from scripts.generate_pettripfinder_pilot import (
    LAUNCH_PACKAGE_DIR,
    build_content_package,
    compute_inventory_readiness,
    load_launch_package,
)
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset
from scripts.pettripfinder.site_data import (
    CORRIDOR_MIN_PROPERTIES,
    assign_corridor,
    group_by_corridor,
    load_hotel_policy_facts,
    normalize_name,
    read_production_rows,
)
from scripts.pettripfinder.site_enrichment import (
    BASE_URL,
    build_go_pages_for_listing,
    enrich_hotel_category_page,
    enrich_hotel_profile,
    enrich_hub_page,
    enrich_place_profile,
    render_hub_intro,
)
from scripts.pettripfinder.site_pages import (
    PTF_EXTRA_CSS,
    build_comparison_page,
    build_corridor_page,
    build_methodology_page,
)

_SKIP_LINK = '<a class="ptf-skip-link" href="#main">Skip to main content</a>'
_BODY_OPEN_RE = re.compile(r"(<body[^>]*>)")

DEFAULT_OUTPUT = "data/site_builds/pettripfinder_columbus"

_LLMS_TXT = """\
# PetTripFinder Columbus

PetTripFinder verifies pet policies directly from each business's own
official website. See /methodology/ for the full verification standard.

- Verified pet-friendly hotels: /pet-friendly-hotels/
- Hotel pet-policy comparison: /pet-friendly-hotels/policy-comparison/
- Pet-friendly parks: /pet-friendly-parks/
- Pet-friendly restaurants: /pet-friendly-restaurants/
- Verification methodology: /methodology/

This file is informational only; it does not guarantee inclusion in any
AI system's output.
"""

_ROBOTS_TXT = """\
User-agent: *
Allow: /
Disallow: /go/

User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

Sitemap: %s/sitemap.xml
""" % BASE_URL


def _run_base_chain(package: Dict) -> Tuple[object, object, object, Dict]:
    """The proven chain, unchanged from the pilot script -- fails loudly
    (raises) rather than silently degrading if any stage errors."""
    pilot_config = package["pilot_config"]
    result = build_listing_dataset(
        seed_businesses=package["seed_businesses"], categories=package["categories"],
        locations=package["locations"])
    if not result.ok:
        raise SystemExit("ListingDataset conversion FAILED: %s" % result.errors)
    dataset = result.dataset

    readiness = compute_inventory_readiness(
        dataset, pilot_config["inventory_thresholds"], reference_date=date.today().isoformat())
    if not readiness["launch_inventory_ready"]:
        raise SystemExit(
            "NOT LAUNCH READY: real inventory is below the approved launch threshold "
            "(%s). Refusing to build the public site." % readiness)

    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC, source_hashes={},
        business_name=pilot_config["project_name"], niche=pilot_config["niche"],
        audience=pilot_config["audience"], value_proposition=pilot_config["value_proposition"],
        directory_taxonomy=tuple(c["name"] for c in pilot_config["launch_categories"]),
        monetization_model=pilot_config["monetization_model"], geography=pilot_config["geography"])
    brand = BrandEngine().resolve(spec)
    editorial_pages = tuple((p["route"], p["title"]) for p in pilot_config["editorial_pages"])
    site_architecture = InformationArchitectureEngine().plan(
        spec, brand, listing_dataset=dataset, editorial_pages=editorial_pages)
    category_routes = {c.slug: "/%s/" % c.slug for c in dataset.categories}
    content_package = build_content_package(
        package["pilot_content"], category_routes, dataset, {r: t for r, t in editorial_pages})
    registry = build_default_registry()
    compilation = ComponentEngine().compile(
        site_architecture, content_package, listing_dataset=dataset, brand_package=brand, registry=registry)
    layout = LayoutEngine(registry).compose(compilation.component_manifest, brand)
    rendered = Renderer(registry).render(
        layout, compilation.component_manifest, compilation.content_package, brand,
        render_data=compilation.render_data)
    seo_package = SEOEngine().compile(
        site_architecture, compilation.content_package, spec, base_url=pilot_config["base_url"])
    bundle = AssemblyEngine().assemble(rendered, seo_package, brand, listing_dataset=dataset)
    report = QualityGateEngine().evaluate(bundle, seo_package, compilation.content_package, site_architecture)
    blocking = [g for g in report.gate_results if g.severity == GateSeverity.BLOCKING and not g.passed]
    if blocking:
        raise SystemExit("Base pipeline quality gates FAILED (blocking): %s" % blocking)
    return bundle, seo_package, report, readiness


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def run(output: str) -> int:
    print("PetTripFinder Columbus -- AES-SITE-001 public site build")
    package = load_launch_package()
    bundle, seo_package, gate_report, readiness = _run_base_chain(package)

    materialization = SiteBundleRepository().materialize(bundle, output, build_id=None)
    out_dir = Path(materialization.destination)
    print("Base bundle materialized: %d files, hash %s" % (
        len(bundle.file_map), materialization.bundle_hash))

    # --- load real production/verification data (zero network) -----------
    all_rows = read_production_rows()
    hotel_rows = [r for r in all_rows if r["category"] == "pet-friendly-hotels"]
    park_rows = [r for r in all_rows if r["category"] == "pet-friendly-parks"]
    restaurant_rows = [r for r in all_rows if r["category"] == "pet-friendly-restaurants"]
    policy_facts = load_hotel_policy_facts()
    corridor_groups = group_by_corridor(hotel_rows)

    warnings: List[str] = []
    go_pages: Dict[str, str] = {}

    def _listing_id(name: str) -> str:
        return _slug(name)

    # --- hotel profiles -----------------------------------------------------
    for row in hotel_rows:
        listing_id = _listing_id(row["name"])
        profile_path = out_dir / "pet-friendly-hotels" / listing_id / "index.html"
        if not profile_path.exists():
            warnings.append("missing hotel profile file for %s" % row["name"])
            continue
        facts_entry = policy_facts.get(normalize_name(row["name"]))
        corridor = assign_corridor(row.get("address", ""), row.get("city", ""))
        html_text = profile_path.read_text(encoding="utf-8")
        enriched = enrich_hotel_profile(
            html_text=html_text, row=row, listing_id=listing_id, corridor=corridor,
            facts_entry=facts_entry, all_rows=all_rows)
        profile_path.write_text(enriched, encoding="utf-8", newline="\n")
        verification_status = (
            "POLICY_UNVERIFIED" if not facts_entry else
            "VERIFIED_NO_PETS" if facts_entry["facts"].get("pets_allowed") == "false" else
            "VERIFIED_PET_FRIENDLY")
        go_pages.update(build_go_pages_for_listing(
            listing_id=listing_id, name=row["name"], official_url=row.get("website_url", ""),
            phone=row.get("phone", ""), address=row.get("address", ""), city=row.get("city", ""),
            state=row.get("state", ""), category_slug="pet-friendly-hotels", corridor=corridor,
            verification_status=verification_status))

    # --- park / restaurant profiles -----------------------------------------
    for rows, slug, place_type in ((park_rows, "pet-friendly-parks", "Park"),
                                   (restaurant_rows, "pet-friendly-restaurants", "Restaurant")):
        for row in rows:
            listing_id = _listing_id(row["name"])
            profile_path = out_dir / slug / listing_id / "index.html"
            if not profile_path.exists():
                warnings.append("missing %s profile file for %s" % (slug, row["name"]))
                continue
            html_text = profile_path.read_text(encoding="utf-8")
            enriched = enrich_place_profile(
                html_text=html_text, row=row, listing_id=listing_id, category_slug=slug,
                place_type=place_type, all_rows=all_rows)
            profile_path.write_text(enriched, encoding="utf-8", newline="\n")
            go_pages.update(build_go_pages_for_listing(
                listing_id=listing_id, name=row["name"], official_url=row.get("website_url", ""),
                phone=row.get("phone", ""), address=row.get("address", ""), city=row.get("city", ""),
                state=row.get("state", ""), category_slug=slug, corridor="",
                verification_status="POLICY_UNVERIFIED"))

    # --- hotel category page -------------------------------------------------
    hotel_cat_path = out_dir / "pet-friendly-hotels" / "index.html"
    corridor_by_route = {
        "/pet-friendly-hotels/%s/" % _listing_id(r["name"]): corridor
        for corridor, members in corridor_groups.items() for r in members
    }
    hotel_cat_html = hotel_cat_path.read_text(encoding="utf-8")
    hotel_cat_html = enrich_hotel_category_page(
        hotel_cat_html, sorted(corridor_groups.keys()), corridor_by_route)
    hotel_cat_path.write_text(hotel_cat_html, encoding="utf-8", newline="\n")

    # --- hub page --------------------------------------------------------------
    hub_path = out_dir / "index.html"
    latest_verified = max(
        (e["verified_at"] for e in policy_facts.values() if e["verified_at"]), default="")
    hub_html = hub_path.read_text(encoding="utf-8")
    hub_html = enrich_hub_page(hub_html, render_hub_intro(
        hotel_count=len(hotel_rows), park_count=len(park_rows),
        restaurant_count=len(restaurant_rows), latest_verified_date=latest_verified))
    hub_path.write_text(hub_html, encoding="utf-8", newline="\n")

    # --- methodology page rewrite ------------------------------------------
    (out_dir / "methodology").mkdir(exist_ok=True)
    (out_dir / "methodology" / "index.html").write_text(
        build_methodology_page(), encoding="utf-8", newline="\n")

    # --- comparison page -----------------------------------------------------
    comparison_rows = []
    for row in hotel_rows:
        entry = policy_facts.get(normalize_name(row["name"]))
        listing_id = _listing_id(row["name"])
        if entry and entry["facts"].get("pets_allowed") == "false":
            continue   # comparison page is pet-FRIENDLY policies only
        f = entry["facts"] if entry else {}
        comparison_rows.append({
            "name": row["name"], "route": "/pet-friendly-hotels/%s/" % listing_id,
            "area": "%s, %s" % (row.get("city", ""), row.get("state", "")),
            "species_allowed": f.get("species_allowed", ""), "pet_fee": f.get("pet_fee", ""),
            "fee_basis": f.get("fee_basis", ""), "pet_count_limit": f.get("pet_count_limit", ""),
            "weight_limit": f.get("weight_limit", ""),
            "verified_at": entry["verified_at"] if entry else "",
        })
    (out_dir / "pet-friendly-hotels" / "policy-comparison").mkdir(exist_ok=True)
    (out_dir / "pet-friendly-hotels" / "policy-comparison" / "index.html").write_text(
        build_comparison_page(comparison_rows), encoding="utf-8", newline="\n")

    # --- corridor pages --------------------------------------------------------
    corridor_routes: List[str] = []
    for corridor_name, members in corridor_groups.items():
        corridor_slug = _slug(corridor_name)
        corridor_hotel_rows = [
            {"name": r["name"], "route": "/pet-friendly-hotels/%s/" % _listing_id(r["name"]),
             "city": r.get("city", "")}
            for r in members
        ]
        page_html = build_corridor_page(corridor_name, corridor_slug, corridor_hotel_rows)
        (out_dir / "pet-friendly-hotels" / corridor_slug).mkdir(exist_ok=True)
        (out_dir / "pet-friendly-hotels" / corridor_slug / "index.html").write_text(
            page_html, encoding="utf-8", newline="\n")
        corridor_routes.append("/pet-friendly-hotels/%s/" % corridor_slug)

    # --- /go/ redirect pages ----------------------------------------------
    for route, page_html in go_pages.items():
        path = out_dir / route.lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_html, encoding="utf-8", newline="\n")

    # --- sitemap / robots / llms.txt ---------------------------------------
    indexable_routes = sorted(set(bundle.file_map.keys()) - {"sitemap.xml", "robots.txt", "styles.css"})
    indexable_routes = [r for r in bundle.file_map if r.endswith("/index.html")]
    base_sitemap_routes = ["/" + r.rsplit("index.html", 1)[0] for r in indexable_routes]
    base_sitemap_routes = [r if r != "//" else "/" for r in base_sitemap_routes]
    new_routes = ["/pet-friendly-hotels/policy-comparison/"] + corridor_routes
    all_sitemap_routes = sorted(set(base_sitemap_routes) | set(new_routes))
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join("<url><loc>%s%s</loc></url>" % (BASE_URL, r) for r in all_sitemap_routes)
        + "</urlset>"
    )
    (out_dir / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8", newline="\n")
    (out_dir / "robots.txt").write_text(_ROBOTS_TXT, encoding="utf-8", newline="\n")
    (out_dir / "llms.txt").write_text(_LLMS_TXT, encoding="utf-8", newline="\n")

    # --- CSS + skip link (Task 15/17): applied uniformly to every page, ---
    # base-pipeline-rendered or custom-built here, after all content is in
    # its final place.
    styles_path = out_dir / "styles.css"
    styles_path.write_text(
        styles_path.read_text(encoding="utf-8") + "\n" + PTF_EXTRA_CSS,
        encoding="utf-8", newline="\n")
    for html_path in out_dir.rglob("index.html"):
        if "go" in html_path.relative_to(out_dir).parts[:1]:
            continue   # noindex redirect pages: no <main>, nothing to skip to
        text = html_path.read_text(encoding="utf-8")
        if "ptf-skip-link" in text or "<body" not in text:
            continue
        text = _BODY_OPEN_RE.sub(r"\1" + _SKIP_LINK, text, count=1)
        html_path.write_text(text, encoding="utf-8", newline="\n")

    # --- reports -----------------------------------------------------------
    build_report = {
        "build_tool": "AES-SITE-001 generate_pettripfinder_columbus_site.py",
        "base_bundle_hash": materialization.bundle_hash,
        "base_route_count": len(bundle.file_map),
        "hotel_count": len(hotel_rows), "park_count": len(park_rows),
        "restaurant_count": len(restaurant_rows),
        "hotels_with_structured_facts": len(policy_facts),
        "corridors_built": sorted(corridor_groups.keys()),
        "go_pages_built": len(go_pages),
        "new_pages_built": 2 + len(corridor_routes),  # comparison + methodology + corridors
        "warnings": warnings,
        "launch_inventory_ready": readiness["launch_inventory_ready"],
    }
    (out_dir / "_build_report.json").write_text(
        json.dumps(build_report, indent=2), encoding="utf-8", newline="\n")

    broken = _check_internal_links(out_dir, set(all_sitemap_routes) | {r for r, _ in go_pages.items()})
    (out_dir / "_broken_link_report.json").write_text(
        json.dumps({"broken_links": broken}, indent=2), encoding="utf-8", newline="\n")

    quality_report = _run_quality_checks(out_dir, hotel_rows, corridor_groups, policy_facts)
    (out_dir / "_quality_report.json").write_text(
        json.dumps(quality_report, indent=2), encoding="utf-8", newline="\n")

    print()
    print("Enrichment complete.")
    print("  hotel profiles enriched: %d" % len(hotel_rows))
    print("  park/restaurant profiles enriched: %d" % (len(park_rows) + len(restaurant_rows)))
    print("  /go/ pages: %d" % len(go_pages))
    print("  corridor pages: %s" % corridor_routes)
    print("  comparison page: /pet-friendly-hotels/policy-comparison/")
    print("  warnings: %d" % len(warnings))
    print("  broken internal links: %d" % len(broken))
    print("  quality gate failures: %d" % len(quality_report.get("failures", [])))
    print("  output path: %s" % out_dir)
    return 0


def _check_internal_links(out_dir: Path, known_routes: set) -> List[str]:
    broken = []
    href_re = re.compile(r'href="(/[^"]*)"')
    for html_path in out_dir.rglob("index.html"):
        text = html_path.read_text(encoding="utf-8")
        for href in href_re.findall(text):
            if href.startswith("//") or href.startswith("/#"):
                continue
            target = out_dir / href.lstrip("/").rstrip("/")
            target_file = target / "index.html" if href.endswith("/") or href == "" else target
            if href == "/":
                target_file = out_dir / "index.html"
            if not target_file.exists() and not (out_dir / href.lstrip("/")).exists():
                broken.append("%s -> %s" % (html_path.relative_to(out_dir), href))
    return broken


_CANONICAL_RE = re.compile(
    r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"|<link[^>]*href="([^"]+)"[^>]*rel="canonical"')
_LD_SCRIPT_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>')
_H1_RE = re.compile(r"<h1[^>]*>")


def _run_quality_checks(out_dir: Path, hotel_rows: List[Dict], corridor_groups: Dict,
                        policy_facts: Dict) -> Dict:
    failures: List[str] = []
    for corridor, members in corridor_groups.items():
        if len(members) < CORRIDOR_MIN_PROPERTIES:
            failures.append("corridor %r below minimum threshold" % corridor)

    canonicals: Dict[str, str] = {}
    real_routes: List[str] = []
    for html_path in out_dir.rglob("index.html"):
        rel = html_path.relative_to(out_dir)
        is_go_page = "go" in rel.parts[:1]
        text = html_path.read_text(encoding="utf-8")

        if "<title>" not in text:
            failures.append("missing title: %s" % rel)
        if 'name="description"' not in text and not is_go_page:
            failures.append("missing meta description: %s" % rel)

        m = _CANONICAL_RE.search(text)
        if is_go_page:
            if m:
                failures.append("go-redirect page unexpectedly has a canonical: %s" % rel)
        else:
            real_routes.append(str(rel))
            if not m:
                failures.append("missing canonical on real content page: %s" % rel)
            else:
                url = m.group(1) or m.group(2)
                if url in canonicals:
                    failures.append("duplicate canonical %r: %s and %s" % (url, canonicals[url], rel))
                canonicals[url] = str(rel)
            if 'name="robots" content="noindex' in text:
                failures.append("real content page unexpectedly noindex: %s" % rel)
            if len(_H1_RE.findall(text)) != 1:
                failures.append("page does not have exactly one <h1>: %s" % rel)
            if "<html" not in text or 'lang="en"' not in text:
                failures.append("missing lang attribute: %s" % rel)

        for ld in _LD_SCRIPT_RE.findall(text):
            try:
                json.loads(ld.replace("<\\/", "</"))
            except json.JSONDecodeError as exc:
                failures.append("invalid JSON-LD on %s: %s" % (rel, exc))

    return {
        "failures": failures,
        "checked_files": sum(1 for _ in out_dir.rglob("index.html")),
        "real_content_pages": len(real_routes),
        "unique_canonicals": len(canonicals),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    return run(args.output)


if __name__ == "__main__":
    raise SystemExit(main())

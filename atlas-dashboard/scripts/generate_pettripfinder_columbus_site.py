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
from scripts.pettripfinder.markets import (
    CorridorAssignment,
    MarketConfig,
    assign_hotels,
    corridor_href_for,
    corridor_navigation,
    corridor_route,
    market_route,
    sitemap_corridor_routes,
)
from scripts.pettripfinder.market_context import PRODUCTION_MARKET_ID, resolve_market
from scripts.pettripfinder.market_ownership import owned_by
from scripts.pettripfinder.site_data import (
    load_published_hotel_policy_facts,
    normalize_name,
    read_production_rows,
    verified_public_hotels,
)
from scripts.pettripfinder.approved_hotel_profile import set_market_labels
from scripts.pettripfinder import canonical_view
from scripts.pettripfinder.hotel_profile import (
    cap_qualifier_note,
    fee_qualifier_phrase,
    fee_scope_display,
)
from scripts.pettripfinder.hotel_profile_page import (
    build_hotel_go_pages,
    render_production_hotel_profile,
)
from scripts.pettripfinder.site_enrichment import (
    BASE_URL,
    build_go_pages_for_listing,
    enrich_hotel_category_page,
    enrich_hub_page,
    enrich_place_profile,
    render_hub_intro,
)
from scripts.pettripfinder.site_pages import (
    PTF_EXTRA_CSS,
    set_published_categories,
    build_comparison_page,
    build_corridor_page,
    build_methodology_page,
)

_SKIP_LINK = '<a class="ptf-skip-link" href="#main">Skip to main content</a>'
_BODY_OPEN_RE = re.compile(r"(<body[^>]*>)")

DEFAULT_OUTPUT = "data/site_builds/pettripfinder_columbus"

_LLMS_TXT_TEMPLATE = """\
# PetTripFinder %(market_name)s

PetTripFinder verifies pet policies directly from each business's own
official website. See /methodology/ for the full verification standard.

%(links)s

This file is informational only; it does not guarantee inclusion in any
AI system's output.
"""

#: (label, route) for every section llms.txt may advertise, in emission order.
#: The comparison entry carries no fixed route: its path depends on the
#: market's route_mode, so the builder supplies the one it actually wrote.
#:
#: PTF-CLEVELAND-DAYTON-WORKER-INTEGRATION-001: these used to be hard-coded
#: into the template, which meant every market published Columbus's route list
#: whether or not it had those pages. Dayton advertised /pet-friendly-parks/
#: and /pet-friendly-restaurants/ (it publishes neither) and pointed at
#: /pet-friendly-hotels/policy-comparison/ when its comparison page is really
#: at /pet-friendly-hotels/dayton-oh/policy-comparison/ -- three dead links on
#: the one file whose entire audience is machines. The internal-link checker
#: never caught it because it reads HTML, and llms.txt is text.
#:
#: The list is now filtered against the routes the build actually produced, so
#: it is correct for any market by construction rather than by naming one.
_LLMS_SECTIONS = (
    ("Verified pet-friendly hotels", "/pet-friendly-hotels/"),
    ("Hotel pet-policy comparison", None),
    ("Pet-friendly parks", "/pet-friendly-parks/"),
    ("Pet-friendly restaurants", "/pet-friendly-restaurants/"),
    ("Verification methodology", "/methodology/"),
)


def _llms_txt(market_name: str, published_routes, comparison_route: str) -> str:
    """llms.txt naming only routes this build really wrote."""
    available = set(published_routes) | {comparison_route}
    lines = []
    for label, route in _LLMS_SECTIONS:
        target = comparison_route if route is None else route
        if target in available:
            lines.append("- %s: %s" % (label, target))
    return _LLMS_TXT_TEMPLATE % {"market_name": market_name,
                                 "links": "\n".join(lines)}


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


def _market_inventory_thresholds(market: MarketConfig, package: Dict) -> Dict:
    """The launch bar for the market being built.

    Columbus keeps the pilot config's bar verbatim -- 30 listings, 10 per
    category, across hotels/parks/restaurants -- so its build is untouched.

    That bar cannot be applied to every market, because it encodes a
    three-category consumer product. Cleveland-Akron-Canton is a hotels-only
    regional market: judged by Columbus's bar it fails for having no parks and
    no restaurants, which is not a quality finding about its hotels.

    So for any other market the bar comes from what the market itself already
    declares -- ``minimum_published_hotels`` in its committed ptf-market
    config, authored before any of its inventory existed -- applied to the
    categories that market actually carries. The bar still bites: a market
    with fewer ready listings than its own declared minimum still refuses to
    build. What it no longer does is demand categories the market never
    claimed to offer.
    """
    thresholds = package["pilot_config"]["inventory_thresholds"]
    if market.market_id == PRODUCTION_MARKET_ID:
        return thresholds
    present = sorted({row.get("category") for row in package["seed_businesses"]
                      if row.get("category")})
    floor = int(market.minimum_published_hotels)
    return {"minimum_total_listings": floor, "minimum_per_category": floor,
            "required_categories": present}


def _run_base_chain(package: Dict, thresholds: Dict = None) -> Tuple[object, object, object, Dict]:
    """The proven chain, unchanged from the pilot script -- fails loudly
    (raises) rather than silently degrading if any stage errors."""
    pilot_config = package["pilot_config"]
    # PTF-BREWDOG-PROMOTION-001: hand the builder the reviewed same-campus
    # exceptions, so two businesses sharing one street address keep two listings
    # instead of one silently winning the address dedup.
    from scripts.pettripfinder.publication_guard import distinct_entity_groups

    result = build_listing_dataset(
        seed_businesses=package["seed_businesses"], categories=package["categories"],
        locations=package["locations"],
        distinct_entity_groups=distinct_entity_groups())
    if not result.ok:
        raise SystemExit("ListingDataset conversion FAILED: %s" % result.errors)
    dataset = result.dataset

    readiness = compute_inventory_readiness(
        dataset, thresholds or pilot_config["inventory_thresholds"],
        reference_date=date.today().isoformat())
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


def run(output: str, *, market: MarketConfig = None) -> int:
    # PTF-MULTIMARKET-001: the market being built is explicit context, not a
    # count-based inference. Callers may thread a resolved MarketConfig in;
    # otherwise this build's named production market is used.
    market = resolve_market(market)
    print("PetTripFinder Columbus -- AES-SITE-001 public site build")
    package = load_launch_package()

    # PTF-MULTI-MARKET-INVENTORY-SCOPING-001. Market selection happens HERE,
    # before anything else looks at inventory, and it is explicit ownership --
    # not "every approved row", which is what this build used to select and
    # which would have pulled a second market's hotels into this package the
    # moment their rows landed in the seed file.
    #
    # It runs before corridor assignment on purpose. Corridors subdivide a
    # market; they do not decide who belongs to it, and twelve published
    # Columbus hotels belong to no corridor at all.
    package = dict(package, seed_businesses=owned_by(
        package["seed_businesses"], market.market_id,
        context="launch-package seed inventory"))

    # A market publishes the categories it actually carries. The category list
    # is global, so an inventory with no parks still planned a /pet-friendly-
    # parks/ page, and that page then failed component compilation for having
    # zero cards -- correctly: an empty directory page is a broken promise to a
    # reader, not a thin one. Columbus carries all three categories and is
    # unaffected.
    _present = {row.get("category") for row in package["seed_businesses"]}
    package = dict(package, categories=[c for c in package["categories"]
                                        if c.get("slug") in _present])
    # The information architecture plans category ROUTES from the business
    # spec's taxonomy, not from the dataset, so the taxonomy has to be scoped
    # too or the empty routes come back at the next stage.
    _config = dict(package["pilot_config"])
    _config["launch_categories"] = [c for c in _config["launch_categories"]
                                    if c.get("slug") in _present]
    package = dict(package, pilot_config=_config)
    set_published_categories(sorted(_present),
                             market_route(market) + "policy-comparison/")
    # The approved hotel-profile renderer carried "Columbus" in its brand
    # lockup, footer, tagline, title and meta description. Unset, a Cleveland
    # profile would announce itself as PetTripFinder Columbus.
    set_market_labels(label=market.market_name, state=market.state_name,
                      metro_default="%s, %s" % (market.primary_city, market.state_code),
                      categories=sorted(_present))
    print("Market scope: %s -- %d owned inventory rows, %d categor%s" % (
        market.market_id, len(package["seed_businesses"]),
        len(package["categories"]), "y" if len(package["categories"]) == 1 else "ies"))

    policy_facts = load_published_hotel_policy_facts(market.market_id)   # this market's policy authority

    # VERIFIED-ONLY PUBLIC GENERATION (PROD-004): only hotels present in the
    # committed hotel-policy package receive public routes. Seed hotel rows absent
    # from the package (held / manual-review) are excluded from the base bundle and
    # every downstream hotel surface; parks/restaurants are untouched. The join is
    # deterministic and fails closed (verified_public_hotels raises) rather than
    # silently dropping a verified hotel.
    verified_names = {normalize_name(r["name"]) for r in verified_public_hotels(
        [b for b in package["seed_businesses"] if b.get("category") == "pet-friendly-hotels"],
        policy_facts)}

    def _verified_only(rows):
        return [r for r in rows if r.get("category") != "pet-friendly-hotels"
                or normalize_name(r.get("name", "")) in verified_names]

    package = dict(package, seed_businesses=_verified_only(package["seed_businesses"]))
    bundle, seo_package, gate_report, readiness = _run_base_chain(
        package, _market_inventory_thresholds(market, package))

    materialization = SiteBundleRepository().materialize(bundle, output, build_id=None)
    out_dir = Path(materialization.destination)
    print("Base bundle materialized: %d files, hash %s" % (
        len(bundle.file_map), materialization.bundle_hash))

    # --- load real production/verification data (zero network) -----------
    # Same market scope as the base package above -- the two inventory reads
    # must never disagree about who owns a row, or the base bundle and the
    # enriched surfaces would publish different hotel sets.
    all_rows = _verified_only(owned_by(read_production_rows(), market.market_id,
                                       context="production seed inventory"))
    hotel_rows = [r for r in all_rows if r["category"] == "pet-friendly-hotels"]
    park_rows = [r for r in all_rows if r["category"] == "pet-friendly-parks"]
    restaurant_rows = [r for r in all_rows if r["category"] == "pet-friendly-restaurants"]

    # PTF-CORRIDORS-002: the committed ptf-market config is the ONE corridor
    # authority. Assignment is deterministic (exclusion > explicit > city >
    # ZIP) and fails closed on ambiguity; unassigned hotels stay published
    # and are REPORTED below, never silently dropped.
    assignment = assign_hotels(market, hotel_rows)
    corridor_groups = {market.corridor_by_id(cid).name: list(assignment.members_of(cid))
                       for cid in assignment.published}

    def _corridor_name_for(row: Dict) -> str:
        ids = assignment.corridor_of.get(normalize_name(row.get("name", "")), ())
        return market.corridor_by_id(ids[0]).name if ids else ""

    warnings: List[str] = []
    go_pages: Dict[str, str] = {}

    def _listing_id(name: str) -> str:
        return _slug(name)

    # --- hotel profiles (PTF-PROD-002: APPROVED renderer) -------------------
    # The hotel profile is now produced by the approved hotel-profile renderer
    # (scripts/pettripfinder/hotel_profile_page.render_production_hotel_profile),
    # fully replacing the base AES-WEB profile layout + enrich_hotel_profile body
    # surgery for hotels. The base bundle still materialized a placeholder file
    # at this route; we overwrite it with the approved page (self-canonical +
    # breadcrumb/LodgingBusiness JSON-LD injected). Parks/restaurants are
    # unchanged. render_production_hotel_profile passes market_home="/" so the
    # renderer's Columbus links resolve to the real hub.
    for row in hotel_rows:
        listing_id = _listing_id(row["name"])
        profile_path = out_dir / "pet-friendly-hotels" / listing_id / "index.html"
        if not profile_path.exists():
            warnings.append("missing hotel profile file for %s" % row["name"])
            continue
        facts_entry = policy_facts.get(normalize_name(row["name"]))
        corridor = _corridor_name_for(row)
        # Corridor breadcrumb/see-all links resolve only to corridor pages
        # that actually PUBLISH (corridor_href_for returns None for a
        # suppressed corridor -- never a broken link).
        corridor_href = corridor_href_for(market, assignment, row["name"])
        page_html = render_production_hotel_profile(
            row, facts_entry, hotel_rows, policy_facts,
            park_rows=park_rows, restaurant_rows=restaurant_rows,
            corridor_href=corridor_href, market_id=market.market_id)
        profile_path.write_text(page_html, encoding="utf-8", newline="\n")
        go_pages.update(build_hotel_go_pages(row, listing_id, corridor, facts_entry,
                                             market=market.market_id))

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
                verification_status="POLICY_UNVERIFIED", market=market.market_id))

    # --- hotel category page -------------------------------------------------
    hotel_cat_path = out_dir / "pet-friendly-hotels" / "index.html"
    corridor_by_route = {
        "/pet-friendly-hotels/%s/" % _listing_id(r["name"]): corridor
        for corridor, members in corridor_groups.items() for r in members
    }
    hotel_cat_html = hotel_cat_path.read_text(encoding="utf-8")
    hotel_cat_html = enrich_hotel_category_page(
        hotel_cat_html, sorted(corridor_groups.keys()), corridor_by_route,
        market=market.market_id)
    hotel_cat_path.write_text(hotel_cat_html, encoding="utf-8", newline="\n")

    # --- homepage (PETTRIPFINDER approved coded prototype) --------------------
    # The founder-approved coded homepage (pettripfinder_exact_prototype_v3)
    # fully replaces the base hub page. It is wired to the real verified hotel
    # records, the real inventory counts, and live routes; its temporary review
    # imagery is copied into the site's /assets/ (Google Places media is a
    # separate later phase). Every other page/route is unchanged.
    #
    # PTF-MULTI-MARKET-HOMEPAGE-AWARENESS-001: the market is passed EXPLICITLY.
    # The renderer used to carry Columbus's identity as literals, so this page
    # was the one surface a non-Columbus build still published as Columbus --
    # title, wordmark, headline, search location, vet query, footer, and the
    # Scioto riverfront photograph. It also links only to the directories this
    # market builds, and city photography ships only where it belongs.
    from scripts.pettripfinder.approved_home import render as approved_home
    _homepage = approved_home.resolve_homepage(market)
    (out_dir / "index.html").write_text(
        approved_home.render_home(
            hotel_rows, policy_facts, hotel_count=len(hotel_rows),
            park_count=len(park_rows), restaurant_count=len(restaurant_rows),
            corridor_nav=[(e.label, e.route)
                          for e in corridor_navigation(market, assignment)],
            market=market, published_categories=sorted(_present)),
        encoding="utf-8", newline="\n")
    approved_home.copy_assets(
        out_dir, include_city_photography=bool(_homepage.hero_image))

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
        # PTF-RENDERER-FIDELITY-001. The canonical view answers the questions
        # the legacy facts dict cannot: what scope this fee actually has,
        # whether a single printed amount is the whole story, and whether an
        # explicit species refusal is on record.
        view = canonical_view.build(entry) if entry else None
        comparison_rows.append({
            "name": row["name"], "route": "/pet-friendly-hotels/%s/" % listing_id,
            "area": "%s, %s" % (row.get("city", ""), row.get("state", "")),
            "species_allowed": f.get("species_allowed", ""), "pet_fee": f.get("pet_fee", ""),
            # The basis cell carries the scope with it, so "$15" beside "per
            # night" can no longer read as the price for however many pets.
            "fee_basis": fee_qualifier_phrase(f) or f.get("fee_basis", ""),
            "fee_scope_display": fee_scope_display(f),
            "cats_state": view.cats_state if view else "",
            "fee_cap_qualifier": cap_qualifier_note(f),
            "fee_scalar_suppressed": bool(
                view and view.fee_display_mode == "withhold_scalar" and f.get("pet_fee")),
            "pet_count_limit": f.get("pet_count_limit", ""),
            "weight_limit": f.get("weight_limit", ""),
            "weight_limit_operator": f.get("weight_limit_operator", ""),
            # PTF-COLUMBUS-HYATT-002. Without these the comparison table
            # showed a Hyatt's 50 lb individual limit and no sign of the 75 lb
            # combined one -- the surface where a reader is deciding between
            # hotels is the last place to drop half a rule.
            "weight_limit_combined": f.get("weight_limit_combined", ""),
            "weight_limit_combined_operator": f.get("weight_limit_combined_operator", ""),
            # A stay-length ladder has no single fee; the table renders its
            # range plus a note instead of one misleading number. A capped fee
            # carries its ceiling, and a conflicted source carries neither.
            "fee_tiers": f.get("fee_tiers") or [],
            "fee_cap": f.get("fee_cap") or {},
            "fee_conflict": f.get("fee_conflict") or None,
            "fee_withheld": f.get("fee_withheld") or None,
            "verified_at": entry["verified_at"] if entry else "",
        })
    # The route comes from the market (Cleveland is market_prefixed, Columbus
    # legacy_unprefixed). Writing to a hard-coded path put the file at
    # /pet-friendly-hotels/policy-comparison/ while every link pointed at the
    # prefixed route -- one broken link, and in a combined production site a
    # collision with Columbus's comparison page at the very same address.
    _cmp_route = market_route(market) + "policy-comparison/"
    _cmp_dir = out_dir / _cmp_route.strip("/")
    _cmp_dir.mkdir(parents=True, exist_ok=True)
    (_cmp_dir / "index.html").write_text(
        build_comparison_page(comparison_rows, market), encoding="utf-8", newline="\n")

    # --- corridor pages (published corridors only, display order) -------------
    corridor_routes: List[str] = []
    for corridor_cfg in sorted(assignment.published_corridors(),
                               key=lambda c: (c.display_order, c.slug)):
        members = assignment.members_of(corridor_cfg.corridor_id)
        corridor_hotel_rows = [
            {"name": r["name"], "route": "/pet-friendly-hotels/%s/" % _listing_id(r["name"]),
             "city": r.get("city", "")}
            for r in members
        ]
        page_html = build_corridor_page(corridor_cfg, market, corridor_hotel_rows)
        route = corridor_route(market, corridor_cfg)
        page_dir = out_dir / route.strip("/")
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(page_html, encoding="utf-8", newline="\n")
        corridor_routes.append(route)

    # --- /go/ redirect pages ----------------------------------------------
    for route, page_html in go_pages.items():
        path = out_dir / route.lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_html, encoding="utf-8", newline="\n")

    # --- sitemap / robots / llms.txt ---------------------------------------
    # Bundle keys are relative, so the homepage is keyed "index.html" with no
    # directory prefix and a bare endswith("/index.html") test silently drops
    # it -- the site's most important URL was missing from the sitemap. Match
    # the root explicitly alongside the nested pages; the normalisation below
    # already maps "index.html" to "/". Only *.../index.html content pages
    # qualify, so assets, robots/sitemap themselves and the separately written
    # /go/ interstitials stay out.
    indexable_routes = [r for r in bundle.file_map
                        if r == "index.html" or r.endswith("/index.html")]
    base_sitemap_routes = ["/" + r.rsplit("index.html", 1)[0] for r in indexable_routes]
    base_sitemap_routes = [r if r != "//" else "/" for r in base_sitemap_routes]
    # Sitemap corridors respect per-corridor show_in_sitemap (a published,
    # sitemap-hidden corridor still renders but is not advertised).
    new_routes = ([_cmp_route] + list(sitemap_corridor_routes(market, assignment)))
    all_sitemap_routes = sorted(set(base_sitemap_routes) | set(new_routes))
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join("<url><loc>%s%s</loc></url>" % (BASE_URL, r) for r in all_sitemap_routes)
        + "</urlset>"
    )
    (out_dir / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8", newline="\n")
    (out_dir / "robots.txt").write_text(_ROBOTS_TXT, encoding="utf-8", newline="\n")
    (out_dir / "llms.txt").write_text(
        _llms_txt(market.market_name, all_sitemap_routes, _cmp_route),
        encoding="utf-8", newline="\n")

    # --- CSS + skip link (Task 15/17): applied uniformly to every page, ---
    # base-pipeline-rendered or custom-built here, after all content is in
    # its final place.
    styles_path = out_dir / "styles.css"
    styles_path.write_text(
        styles_path.read_text(encoding="utf-8") + "\n" + PTF_EXTRA_CSS,
        encoding="utf-8", newline="\n")
    # Approved hotel-profile stylesheet, emitted once as /hotel-profile.css and
    # referenced absolutely by every hotel page. DESIGN-004: the founder-approved
    # profile design (hp-* namespace, approved_hotel_profile.css) replaces the
    # earlier fh-* sheet; still self-contained, no collision with styles.css.
    (out_dir / "hotel-profile.css").write_text(
        (_REPO_ROOT / "scripts" / "pettripfinder" / "approved_hotel_profile.css").read_text(encoding="utf-8"),
        encoding="utf-8", newline="\n")
    for html_path in out_dir.rglob("index.html"):
        if "go" in html_path.relative_to(out_dir).parts[:1]:
            continue   # noindex redirect pages: no <main>, nothing to skip to
        text = html_path.read_text(encoding="utf-8")
        # Skip pages that already carry a skip link -- the base pages get the
        # "ptf-skip-link" injected here; approved hotel pages already ship their
        # own "skip-link" (substring of "ptf-skip-link"), so this matches both.
        if "skip-link" in text or "<body" not in text:
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
        "market_id": market.market_id,
        "market_schema": "ptf-market/1.0",
        "corridors_built": sorted(corridor_groups.keys()),
        # PTF-CORRIDORS-002 honesty surface: what did NOT publish, and which
        # published hotels belong to no corridor (they keep their routes).
        "corridors_suppressed": [
            {"corridor": market.corridor_by_id(s["corridor_id"]).name,
             "reason": s["reason"], "member_count": s["member_count"]}
            for s in assignment.suppressed],
        "unassigned_hotels": sorted(r["name"] for r in assignment.unassigned),
        "assignment_conflicts": list(assignment.conflicts),
        "go_pages_built": len(go_pages),
        "new_pages_built": 2 + len(corridor_routes),  # comparison + methodology + corridors
        "warnings": warnings,
        "launch_inventory_ready": readiness["launch_inventory_ready"],
    }
    (out_dir / "_build_report.json").write_text(
        json.dumps(build_report, indent=2), encoding="utf-8", newline="\n")

    # PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001. A market PACKAGE owns its hotel,
    # corridor, category and comparison routes. The home page and the editorial
    # pages are GLOBAL: one production site has one of each, and they are
    # contributed by the site assembly, not by whichever market happens to build
    # last. For a non-production market they are therefore emitted for local
    # review but excluded from the package's own surface -- the global home page
    # is the approved Columbus design and legitimately links to directories that
    # a hotels-only market does not build.
    _global_pages = ("index.html", "about/index.html", "contact/index.html")
    _package_only = market.market_id != PRODUCTION_MARKET_ID
    broken = _check_internal_links(
        out_dir, set(all_sitemap_routes) | {r for r, _ in go_pages.items()},
        skip_pages=_global_pages if _package_only else ())
    (out_dir / "_broken_link_report.json").write_text(
        json.dumps({"broken_links": broken}, indent=2), encoding="utf-8", newline="\n")

    quality_report = _run_quality_checks(out_dir, hotel_rows, market, assignment, policy_facts)
    (out_dir / "_quality_report.json").write_text(
        json.dumps(quality_report, indent=2), encoding="utf-8", newline="\n")

    print()
    print("Enrichment complete.")
    print("  hotel profiles enriched: %d" % len(hotel_rows))
    print("  park/restaurant profiles enriched: %d" % (len(park_rows) + len(restaurant_rows)))
    print("  /go/ pages: %d" % len(go_pages))
    print("  corridor pages: %s" % corridor_routes)
    print("  comparison page: %s" % _cmp_route)
    print("  warnings: %d" % len(warnings))
    print("  broken internal links: %d" % len(broken))
    print("  quality gate failures: %d" % len(quality_report.get("failures", [])))
    print("  output path: %s" % out_dir)
    return 0


def _check_internal_links(out_dir: Path, known_routes: set,
                          skip_pages: Tuple[str, ...] = ()) -> List[str]:
    """Report links that resolve to no file in this output.

    ``skip_pages`` names GLOBAL pages that are not part of a market package's
    owned surface. They are skipped as SOURCES only -- a broken link on an
    owned page is still reported no matter where it points.
    """
    broken = []
    skip = {s.replace("/", "\\") for s in skip_pages} | set(skip_pages)
    href_re = re.compile(r'href="(/[^"]*)"')
    for html_path in out_dir.rglob("index.html"):
        if str(html_path.relative_to(out_dir)).replace("\\", "/") in {
                s.replace("\\", "/") for s in skip}:
            continue
        text = html_path.read_text(encoding="utf-8")
        for href in href_re.findall(text):
            # A URL fragment (#anchor) points WITHIN a page, not to a separate
            # file -- strip it before resolving the file target, so a valid link
            # like /methodology/#photos resolves to /methodology/ (which exists)
            # rather than being falsely reported as broken.
            path = href.split("#", 1)[0]
            if not path or path.startswith("//"):
                continue
            target = out_dir / path.lstrip("/").rstrip("/")
            target_file = target / "index.html" if path.endswith("/") or path == "" else target
            if path == "/":
                target_file = out_dir / "index.html"
            if not target_file.exists() and not (out_dir / path.lstrip("/")).exists():
                broken.append("%s -> %s" % (html_path.relative_to(out_dir), href))
    return broken


_CANONICAL_RE = re.compile(
    r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"|<link[^>]*href="([^"]+)"[^>]*rel="canonical"')
_LD_SCRIPT_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>')
_H1_RE = re.compile(r"<h1[^>]*>")


def _run_quality_checks(out_dir: Path, hotel_rows: List[Dict], market: MarketConfig,
                        assignment: CorridorAssignment, policy_facts: Dict) -> Dict:
    failures: List[str] = []
    for cid in assignment.published:
        corridor = market.corridor_by_id(cid)
        if len(assignment.members_of(cid)) < corridor.minimum_hotel_count:
            failures.append("corridor %r below its configured minimum" % corridor.name)
    if assignment.conflicts:
        failures.append("unresolved corridor assignment conflicts: %s"
                        % list(assignment.conflicts))

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


SAMPLE_OUTPUT = "data/site_builds/ptf_prod_002_sample"

# The three controlled review records (PTF-PROD-002), by production-name prefix.
# rich + sparse + a third verified hotel demonstrating the branded no-photo
# placeholder on its own real route (never a duplicate canonical of the rich
# page). All three are verified pet-friendly; no no-pets/unverified record
# enters this sample.
_SAMPLE_SELECTION = (
    ("rich", "Drury Inn & Suites Columbus Grove City"),
    ("sparse", "Days Inn by Wyndham Grove City"),
    ("no-photo", "Sonesta Columbus Downtown"),
)


def _sample_facts_map(use_fixture_facts: bool) -> Tuple[Dict, str]:
    """Returns (facts_map, source_label). Default reads the tracked publishable
    launch package (the normal production source -- committed, no operational
    dependency, works in a clean checkout). ``use_fixture_facts`` reads the
    committed review fixture instead -- a test/review convenience only, never
    the normal production source."""
    if use_fixture_facts:
        data = json.loads(
            (_REPO_ROOT / "scripts" / "pettripfinder" / "hotel_profile_fixtures.json")
            .read_text(encoding="utf-8"))
        return data["verified_facts"], "committed_review_fixture"
    return load_published_hotel_policy_facts(), "published_launch_package"


def run_sample(output: str, *, use_fixture_facts: bool = False,
               market: MarketConfig = None) -> int:
    """Generate ONLY the three controlled hotel-profile review pages through the
    approved renderer, into an isolated (gitignored) directory. Does NOT run the
    base AES-WEB chain, does NOT touch the full market, and never mutates
    inventory. Emits the real hotel routes + their /go/ interstitials + the
    approved stylesheet + a review robots.txt/sitemap + a sample report."""
    out_dir = Path(output)
    if not out_dir.is_absolute():
        out_dir = _REPO_ROOT / output
    out_dir.mkdir(parents=True, exist_ok=True)

    market = resolve_market(market)
    rows = owned_by(read_production_rows(), market.market_id,
                    context="production seed inventory (sample build)")
    hotel_rows = [r for r in rows if r["category"] == "pet-friendly-hotels"]
    facts_map, facts_source = _sample_facts_map(use_fixture_facts)
    assignment = assign_hotels(market, hotel_rows)

    selected: List[Dict] = []
    go_pages: Dict[str, str] = {}
    hotel_routes: List[str] = []
    for state_label, prefix in _SAMPLE_SELECTION:
        row = next((r for r in hotel_rows if r["name"].startswith(prefix)), None)
        if row is None:
            raise SystemExit("PTF-PROD-002 sample hotel not found in inventory: %r" % prefix)
        listing_id = _slug(row["name"])
        facts_entry = facts_map.get(normalize_name(row["name"]))
        corridor_ids = assignment.corridor_of.get(normalize_name(row["name"]), ())
        corridor = market.corridor_by_id(corridor_ids[0]).name if corridor_ids else ""
        page_html = render_production_hotel_profile(row, facts_entry, hotel_rows, facts_map)
        profile_path = out_dir / "pet-friendly-hotels" / listing_id / "index.html"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(page_html, encoding="utf-8", newline="\n")
        route = "/pet-friendly-hotels/%s/" % listing_id
        hotel_routes.append(route)
        for gr, gh in build_hotel_go_pages(row, listing_id, corridor, facts_entry).items():
            go_pages[gr] = gh
        selected.append({
            "state": state_label, "name": row["name"], "route": route,
            "listing_id": listing_id,
            "verification_status": ("VERIFIED_PET_FRIENDLY" if facts_entry else "POLICY_UNVERIFIED"),
            "has_verified_facts": bool(facts_entry),
        })

    for route, page_html in go_pages.items():
        path = out_dir / route.lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_html, encoding="utf-8", newline="\n")

    (out_dir / "hotel-profile.css").write_text(
        (_REPO_ROOT / "scripts" / "pettripfinder" / "approved_hotel_profile.css").read_text(encoding="utf-8"),
        encoding="utf-8", newline="\n")

    # Review output: keep it out of any index (Disallow all); sitemap lists only
    # the verified hotel pages, never the /go/ interstitials.
    (out_dir / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n", encoding="utf-8", newline="\n")
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join("<url><loc>%s%s</loc></url>" % (BASE_URL, r) for r in sorted(hotel_routes))
        + "</urlset>")
    (out_dir / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8", newline="\n")

    report = {
        "build_tool": "PTF-PROD-002 run_sample",
        "renderer": "scripts/pettripfinder/hotel_profile_page.render_production_hotel_profile",
        "facts_source": facts_source,
        "hotel_pages": len(selected),
        "go_pages": len(go_pages),
        "selected": selected,
        "output_path": str(out_dir),
    }
    (out_dir / "_sample_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8", newline="\n")

    print("PTF-PROD-002 three-hotel review sample")
    print("  facts source: %s" % facts_source)
    for s in selected:
        print("  %-9s %-52s %s" % (s["state"], s["listing_id"], s["verification_status"]))
    print("  /go/ pages: %d" % len(go_pages))
    print("  output: %s" % out_dir)
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    p.add_argument("--sample-hotel-profiles", action="store_true",
                   help="generate ONLY the 3-hotel PTF-PROD-002 review sample (approved renderer), "
                        "into an isolated gitignored directory; does not build the full market")
    p.add_argument("--sample-output", default=SAMPLE_OUTPUT,
                   help="output directory for --sample-hotel-profiles")
    p.add_argument("--fixture-facts", action="store_true",
                   help="sample mode only: use the committed review fixture instead of the "
                        "operational corpus (for clean-clone reproduction)")
    p.add_argument("--market", default=PRODUCTION_MARKET_ID,
                   help="market_id to build (PTF-MULTIMARKET-001: explicit, never "
                        "inferred from how many markets are configured)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    market = resolve_market(market_id=args.market)
    if args.sample_hotel_profiles:
        return run_sample(args.sample_output, use_fixture_facts=args.fixture_facts,
                          market=market)
    return run(args.output, market=market)


if __name__ == "__main__":
    raise SystemExit(main())

"""Component Engine tests (AES-WEB-002J.6/J.19; AES-WEB-001 §5.5,
AES-WEB-002 §14/§26; ADR-WEB-CONTENT-BINDING-MAP).

Deterministic throughout: no clock/UUID/randomness. Covers the public
surface and version, golden recipe resolution against the real registered
catalog (now bindability-aware, AES-WEB-002J.19), the embedded §14.3
SelectionTrace (ADR-14), full Phase-B value/content binding and the §5.5
unbound-required-field compile error, selection-pipeline integration
through the engine (lifecycle/compatibility/injected-registry), the
role->recipe map, batch error reporting, and edge cases.

AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "Option A deferred" binding
scope: ``compile()`` now returns a ``ComponentCompilationResult`` (bound
``ComponentManifest`` + companion ``ContentPackage``), and the previously
golden ``home``/``category`` recipe outputs change because bindability-aware
selection now excludes architecturally-unbindable candidates
(``directory.categories.grid``, ``directory.filters.panel``, ...) in favor
of their declared fallbacks -- or, where a required recipe slot has *no*
fallback and its only real candidate is architecturally unbindable
(``category``'s ``pagination``/``zero_results``), the whole compile now
honestly fails rather than silently leaving props/content unbound. Tests
that previously exercised ``category`` are updated to either supply the
bindable ``business-profile`` role instead, or to assert the new honest
failure directly (see ``TestGoldenRealCatalog.
test_category_recipe_honestly_fails_pagination_and_zero_results_unbindable``).

Tests exercise only the public surface (``engines.website_generation`` /
``components``) plus the shared ``make_definition`` fixture, per AES-WEB-001
§3.4 -- never the engine's internal helpers.
"""

from __future__ import annotations

import pytest

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components import (
    ComponentEngine,
    ComponentRegistry,
    build_default_registry,
)
from engines.website_generation.components.selection import LifecycleBuildFlags
from engines.website_generation.constants.components import (
    DEFAULT_COMPATIBILITY_VERSIONS,
    RECIPE_SLOTS_BY_PAGE_ROLE,
)
from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    ComponentCompilationResult,
    ComponentManifest,
    ContentBlock,
    ContentPackage,
    ListingCategory,
    ListingDataset,
    ListingRecord,
    PagePlan,
    SiteArchitecture,
    artifact_sha256,
    canonical_artifact_json,
)
from engines.website_generation.contracts.components import PropSpec
from engines.website_generation.contracts.enums import (
    ArtifactKind,
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
)
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.contracts.interfaces import ComponentEngineInterface
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)

from engines.website_generation.contracts.components import (
    AnalyticsContract,
    RenderingContract,
)

from . import make_definition


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #

def _sa(pages, **overrides) -> SiteArchitecture:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
        pages=tuple(pages),
        nav_routes=(),
        sitemap_routes=tuple(p.route for p in pages),
    )
    fields.update(overrides)
    return SiteArchitecture(**fields)


_HOME_PAGE = PagePlan(route="/", page_type="home", title="Home")
_CATEGORY_PAGE = PagePlan(route="/c/vets", page_type="category", title="Vets")
_BUSINESS_PROFILE_PAGE = PagePlan(
    route="/hotels/lakeview-lodge/", page_type="business-profile", title=""
)

# AES-WEB-002K.1: nav.header.standard/legal.footer.directory are now
# categorically bindable (RENDER_DATA), so Phase A always selects them once
# eligible (region + nav_tree signature) regardless of the site_header/
# site_footer recipe slot's own optional status -- Phase B then requires
# real footer_legal/disclosures content for legal.footer.directory's two
# required content slots. _cp() below unconditionally supplies both for
# every one of this file's three fixed page-constant routes -- harmless,
# unused extra blocks for whichever route a given test doesn't compile.
_FOOTER_LEGAL_TEXT = "(c) 2026 Test Directory. All rights reserved."
_FOOTER_DISCLOSURES_TEXT = "Some listings may be sponsored placements, clearly labeled."
_STANDARD_FOOTER_ROUTES = (_HOME_PAGE.route, _CATEGORY_PAGE.route, _BUSINESS_PROFILE_PAGE.route)


def _cp(blocks=()) -> ContentPackage:
    footer_blocks = []
    for route in _STANDARD_FOOTER_ROUTES:
        footer_blocks.append(ContentBlock(page_route=route, slot_id="footer_legal", text=_FOOTER_LEGAL_TEXT))
        footer_blocks.append(ContentBlock(page_route=route, slot_id="disclosures", text=_FOOTER_DISCLOSURES_TEXT))
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks) + tuple(footer_blocks),
    )


def _ids(page_components):
    return [inst.component_id for inst in page_components.components]


def _page(manifest, route):
    return next(p for p in manifest.pages if p.route == route)


def _brand():
    """A real, deterministic BrandPackage (AES-WEB-002J.19 Phase-B input) --
    the pure Brand Engine over a fixed inline spec, mirroring the
    established local-demo-fixture precedent."""
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="Test Directory",
        niche="test niche",
        audience="test audience",
        value_proposition="test value proposition",
    )
    return BrandEngine().resolve(spec)


def _home_blocks():
    """Every editorial block a bindability-aware home-recipe compile needs
    (hero.search.directory's h1/subhead, nav.utility.bar's message; "intro"
    is unused by the components home currently selects but included for
    parity with the IA vocabulary)."""
    return [
        ContentBlock(page_route="/", slot_id="hero_h1", text="Find pet-friendly places to stay"),
        ContentBlock(page_route="/", slot_id="intro", text="Browse trusted, pet-welcoming businesses."),
        ContentBlock(page_route="/", slot_id="subhead", text="Verified hotels, parks, and restaurants."),
        ContentBlock(page_route="/", slot_id="message", text="Some listings are sponsored and labeled."),
    ]


def _listing_dataset():
    """One real, fully-populated listing (AES-WEB-002J.19 Phase-B input) --
    enough to satisfy every currently-bindable business-profile field
    (name, description, contact, hours, rating, credentials)."""
    from engines.website_generation.contracts.artifacts import (
        ListingAddress,
        ListingContact,
        ListingHoursEntry,
        ListingRating,
    )
    from engines.website_generation.contracts.enums import Weekday

    category = ListingCategory(category_id="cat-hotels", label="Hotels", slug="hotels")
    listing = ListingRecord(
        listing_id="lakeview-lodge",
        business_name="Lakeview Lodge",
        slug="lakeview-lodge",
        category_id="cat-hotels",
        description="A lakeside lodge that welcomes pets.",
        contact=ListingContact(phone="555-0100", email="stay@lakeview.example"),
        address=ListingAddress(city="Austin", state="TX"),
        hours=(ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),),
        rating=ListingRating(rating_hundredths=450, review_count=27),
        credentials=("Licensed pet boarding operator",),
    )
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
        listings=(listing,),
        categories=(category,),
        locations=(),
    )


def _listing_dataset_with_related():
    """AES-WEB-002J.20: :func:`_listing_dataset` plus one companion listing
    in the same category, so business-profile's ``related_listings`` slot
    (``exclude_self=True``) has a real non-self match to expand into a
    ``listing.card.standard`` instance -- a single-listing dataset legally
    yields zero related instances (§14 min_items=0), which is exactly what
    :func:`_listing_dataset` alone now proves elsewhere in this file."""
    base = _listing_dataset()
    companion = base.listings[0].copy(update={
        "listing_id": "riverside-inn",
        "slug": "riverside-inn",
        "business_name": "Riverside Inn",
    })
    return base.copy(update={"listings": base.listings + (companion,)})


# --------------------------------------------------------------------------- #
# Public surface + version
# --------------------------------------------------------------------------- #

class TestPublicSurfaceAndVersion:
    def test_is_interface_subclass(self):
        assert issubclass(ComponentEngine, ComponentEngineInterface)

    def test_version_pinned(self):
        # AES-WEB-002J.19: 1.0.0 -> 1.1.0 (Phase-B binding). AES-WEB-002J.20:
        # 1.1.0 -> 1.2.0 (listing repetition). AES-WEB-002K.1: 1.2.0 -> 1.3.0
        # (render-data production; see contracts/versions.py). PILOT-PTF-1:
        # 1.3.0 -> 1.4.0 (category-tile render-data, honest optional-slot
        # omission). AES-WEB-002L.1: 1.4.0 -> 1.5.0 (strategy-keyed recipe
        # lookup, hero CTA render-data production).
        assert ComponentEngine.version == ENGINE_VERSIONS["component_engine"]
        # AES-WEB-002M.2: 1.5.0 -> 1.6.0 (listing primary-image render data).
        assert ComponentEngine.version == "1.6.0"

    def test_compile_returns_component_compilation_result(self):
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        assert isinstance(result, ComponentCompilationResult)
        assert isinstance(result.component_manifest, ComponentManifest)
        assert isinstance(result.content_package, ContentPackage)


# --------------------------------------------------------------------------- #
# Golden output — real registered catalog
# --------------------------------------------------------------------------- #

class TestGoldenRealCatalog:
    def test_home_recipe_resolves_expected_components(self):
        # AES-WEB-002J.19: directory.categories.grid originally declared a
        # required STRUCTURED_DEFERRED field (category_source_ref/
        # category_tiles), so bindability-aware selection excluded it in
        # favor of its declared fallback, layout.grid.standard.
        # PILOT-PTF-1: category_tiles/category_source_ref move to
        # RENDER_DATA (a real tile-link producer now exists -- the
        # TileLinks contract K.1 declared but left unwired), so
        # directory.categories.grid is now categorically bindable and wins
        # its slot for real, never the empty fallback.
        # directory.locations.grid is still excluded (location_tiles
        # remains STRUCTURED_DEFERRED, unchanged), and -- because its
        # recipe slot is optional with no fallback -- silently dropped
        # (unchanged §26 doctrine for a slot with no bindable winner).
        # AES-WEB-002K.1: site_header/site_footer (nav.header.standard/
        # legal.footer.directory) are now categorically bindable
        # (RENDER_DATA) and _cp() supplies real footer_legal/disclosures
        # content, so both shell slots resolve too -- first and last, per
        # HOME_RECIPE_SLOTS' declared order.
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        assert _ids(_page(result.component_manifest, "/")) == [
            "nav.header.standard",
            "nav.utility.bar",
            "hero.search.directory",
            "directory.categories.grid",
            "legal.footer.directory",
        ]

    def test_category_recipe_succeeds_via_honest_pagination_fallback(self):
        # AES-WEB-002J.19 found (preflight §17/§28) that the category
        # recipe's "pagination" and "zero_results" slots were both required
        # with NO declared fallback, and their only real candidates
        # (nav.pagination.standard: page_context is SOURCE_UNAVAILABLE;
        # status.results.zero: recovery_links is STRUCTURED_DEFERRED) were
        # both categorically unbindable -- an architectural gap, not a data
        # gap, that made every category-page compile fail before Phase B
        # ever ran.
        #
        # AES-WEB-002J.20 authorized a structural fallback
        # (fallback_component_id="layout.stack.standard") on exactly those
        # two slots. AES-WEB-002K.1 (§26 category-control cleanup)
        # supersedes that fallback in turn: both slots are now optional
        # with no fallback at all -- an empty structural <div> was worse
        # for a publishable page than honestly omitting a control that
        # doesn't exist yet. This test now proves the omission is honest
        # (no component chosen at all, never a fabricated "fake
        # pagination"/"fake zero-state" component) and that a category page
        # with real listing data compiles end-to-end regardless, with
        # listing_cards expanded into one listing.card.standard instance
        # per matching listing (the P2 repetition proof, at the unit level).
        category = ListingCategory(category_id="cat-vets", label="Vets", slug="vets")
        listings = tuple(
            ListingRecord(
                listing_id="vet-clinic-%d" % i,
                business_name="Vet Clinic %d" % i,
                slug="vet-clinic-%d" % i,
                category_id="cat-vets",
            )
            for i in range(1, 4)
        )
        dataset = ListingDataset(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
            artifact_kind=ArtifactKind.LISTING_DATASET,
            source_hashes={},
            listings=listings,
            categories=(category,),
            locations=(),
        )
        category_page = PagePlan(route="/vets/", page_type="category", title="Vets")
        result = ComponentEngine().compile(
            _sa([category_page]),
            _cp([
                ContentBlock(page_route="/vets/", slot_id="hero_h1", text="Pet-friendly vets"),
                ContentBlock(page_route="/vets/", slot_id="intro", text="Vets that welcome your pets warmly."),
                ContentBlock(page_route="/vets/", slot_id="footer_legal", text=_FOOTER_LEGAL_TEXT),
                ContentBlock(page_route="/vets/", slot_id="disclosures", text=_FOOTER_DISCLOSURES_TEXT),
            ]),
            listing_dataset=dataset,
            brand_package=_brand(),
        )
        page = _page(result.component_manifest, "/vets/")

        # No fabricated "fake pagination"/"fake zero-state" component --
        # both slots are honestly omitted (AES-WEB-002K.1).
        pagination_trace = next(
            t for t in result.component_manifest.selection_trace.slots
            if t.slot_id == "/vets/#pagination"
        )
        zero_results_trace = next(
            t for t in result.component_manifest.selection_trace.slots
            if t.slot_id == "/vets/#zero_results"
        )
        assert pagination_trace.chosen_component_id == ""
        assert zero_results_trace.chosen_component_id == ""

        # listing_cards repeats: one listing.card.standard instance per
        # matching listing, in ListingDataset tuple order (§14, no sorting).
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        assert len(cards) == 3
        bound_listing_ids = [c.props["listing_ref"].split(".")[-1] for c in cards]
        assert bound_listing_ids == ["vet-clinic-1", "vet-clinic-2", "vet-clinic-3"]

    def test_manifest_header_and_provenance(self):
        sa, cp, brand = _sa([_HOME_PAGE]), _cp(_home_blocks()), _brand()
        result = ComponentEngine().compile(sa, cp, brand_package=brand)
        manifest = result.component_manifest
        assert manifest.artifact_kind is ArtifactKind.COMPONENT_MANIFEST
        assert manifest.schema_version == SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST]
        assert manifest.schema_version == "1.1.0"
        assert manifest.source_hashes == {
            "site_architecture": artifact_sha256(sa),
            "content_package": artifact_sha256(cp),
            "brand_package": artifact_sha256(brand),
            "binding_map_version": "1.2.0",
            "composition_rules_version": "1.0.0",
            # AES-WEB-002M.2: 1.0.0 -> 1.1.0 (ImageData + card/profile
            # image members).
            "render_data_version": "1.1.0",
            "commercial_strategy": "directory",
            "commercial_strategy_version": "1.0.0",
        }

    def test_content_refs_populated_when_bindable(self):
        # AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "Option A deferred"
        # scope this test used to pin (content_refs always empty). Every
        # selected instance's required content slots are now bound to real
        # ContentBlocks -- content_refs is non-empty exactly where a
        # component declares required content slots. PILOT-PTF-1:
        # directory.categories.grid's "category_tiles" content slot is now
        # RENDER_DATA-backed too, so its content_refs marker is the
        # generated "render:category_tiles.<component_index>" key, not a
        # plain ContentPackage slot id (component_index 3: nav.header.
        # standard, nav.utility.bar, hero.search.directory, directory.
        # categories.grid, legal.footer.directory).
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        page = _page(result.component_manifest, "/")
        with_slots = {
            inst.component_id: inst.content_refs
            for inst in page.components
            if inst.content_refs
        }
        assert with_slots == {
            "nav.utility.bar": ("message",),
            "hero.search.directory": ("h1", "subhead"),
            "directory.categories.grid": ("render:category_tiles.3",),
            "legal.footer.directory": ("disclosures", "legal_facts"),
        }

    def test_all_eighteen_roles_with_no_binding_inputs_honestly_fails(self):
        # AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "every role at least
        # partially resolves" premise: Phase B now requires real data for
        # every selected required field. With no ContentPackage blocks, no
        # ListingDataset, and no BrandPackage, essentially every role's
        # selected components have some required field with no source --
        # proving Phase B is honestly enforced (no placeholder fallback),
        # never a silent partial success.
        pages = tuple(
            PagePlan(route="/r/%d" % i, page_type=role.value, title=role.value)
            for i, role in enumerate(PageRole)
        )
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa(pages), _cp())
        assert exc.value.diagnostics  # at least one failure bucket populated

    def test_page_order_preserved(self):
        pages = [_BUSINESS_PROFILE_PAGE, _HOME_PAGE]  # deliberately not sorted
        result = ComponentEngine().compile(
            _sa(pages), _cp(_home_blocks()),
            listing_dataset=_listing_dataset(), brand_package=_brand(),
        )
        assert [p.route for p in result.component_manifest.pages] == [
            "/hotels/lakeview-lodge/", "/",
        ]


# --------------------------------------------------------------------------- #
# SelectionTrace (§14.3, ADR-14)
# --------------------------------------------------------------------------- #

class TestSelectionTrace:
    def test_trace_embedded(self):
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        manifest = result.component_manifest
        assert manifest.selection_trace is not None
        assert manifest.selection_trace.slots  # non-empty

    def test_trace_slot_ids_route_qualified(self):
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE, _BUSINESS_PROFILE_PAGE]), _cp(_home_blocks()),
            listing_dataset=_listing_dataset(), brand_package=_brand(),
        )
        slot_ids = [s.slot_id for s in result.component_manifest.selection_trace.slots]
        # Every slot id carries its page route, so same-named slots across
        # pages ("hero") are disambiguated -- "why this component on this page".
        assert "/#hero" in slot_ids
        assert "/hotels/lakeview-lodge/#profile_header" in slot_ids
        assert all("#" in sid for sid in slot_ids)

    def test_trace_chosen_matches_instances(self):
        # AES-WEB-002J.20: one selection decision may now expand into N
        # concrete instances (repetition), so the trace's per-slot chosen
        # ids no longer map 1:1 onto manifest instances by position -- the
        # truthful invariant is set equality (every chosen id is realized by
        # at least one instance; no instance names a component the trace
        # never chose), never a fake duplicated selection decision.
        result = ComponentEngine().compile(
            _sa([_BUSINESS_PROFILE_PAGE]), _cp(),
            listing_dataset=_listing_dataset_with_related(), brand_package=_brand(),
        )
        manifest = result.component_manifest
        page = _page(manifest, "/hotels/lakeview-lodge/")
        chosen_ids = {
            s.chosen_component_id
            for s in manifest.selection_trace.slots
            if s.slot_id.startswith("/hotels/lakeview-lodge/#") and s.chosen_component_id
        }
        instance_ids = {inst.component_id for inst in page.components}
        assert chosen_ids == instance_ids
        # related_listings (repeatable) expanded to exactly one instance here
        # (2 listings, 1 excluded as self -- see _listing_dataset_with_related).
        assert sum(
            1 for i in page.components if i.component_id == "listing.card.standard"
        ) == 1

    def test_trace_records_score_and_tiebreak(self):
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        hero = next(
            s for s in result.component_manifest.selection_trace.slots
            if s.slot_id == "/#hero"
        )
        assert hero.chosen_component_id == "hero.search.directory"
        assert hero.tie_break_basis  # a survivor ranked => basis recorded
        winner = next(
            c for c in hero.candidates
            if c.component_id == "hero.search.directory"
        )
        assert winner.score is not None

    def test_trace_hashes_with_manifest(self):
        # §14.3: the embedded trace "hashes with the manifest". Dropping it
        # must change the artifact hash.
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        manifest = result.component_manifest
        without_trace = ComponentManifest(
            schema_version=manifest.schema_version,
            artifact_kind=manifest.artifact_kind,
            source_hashes=manifest.source_hashes,
            pages=manifest.pages,
        )
        assert manifest.selection_trace is not None
        assert without_trace.selection_trace is None
        assert artifact_sha256(manifest) != artifact_sha256(without_trace)
        assert "selection_trace" in canonical_artifact_json(manifest)


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_identical_inputs_identical_output(self):
        sa = _sa([_HOME_PAGE, _BUSINESS_PROFILE_PAGE])
        cp = _cp(_home_blocks())
        ld, brand = _listing_dataset(), _brand()
        a = ComponentEngine().compile(sa, cp, listing_dataset=ld, brand_package=brand)
        b = ComponentEngine().compile(sa, cp, listing_dataset=ld, brand_package=brand)  # fresh engine instance
        assert artifact_sha256(a.component_manifest) == artifact_sha256(b.component_manifest)
        assert artifact_sha256(a.content_package) == artifact_sha256(b.content_package)

    def test_content_block_order_independence(self):
        sa = _sa([_HOME_PAGE])
        reorderable = [
            ContentBlock(page_route="/", slot_id="hero_h1", text="A"),
            ContentBlock(page_route="/", slot_id="intro", text="B"),
        ]
        fixed = [
            ContentBlock(page_route="/", slot_id="subhead", text="C"),
            ContentBlock(page_route="/", slot_id="message", text="D"),
        ]
        brand = _brand()
        forward = ComponentEngine().compile(
            sa, _cp(reorderable + fixed), brand_package=brand
        )
        reverse = ComponentEngine().compile(
            sa, _cp(list(reversed(reorderable)) + fixed), brand_package=brand
        )
        # ContentPackage input order must not affect the manifest (it is only
        # hashed for provenance) — but the two ContentPackages differ, so the
        # content_package source hash differs; compare the pages + trace only.
        assert forward.component_manifest.pages == reverse.component_manifest.pages
        assert forward.component_manifest.selection_trace == reverse.component_manifest.selection_trace


# --------------------------------------------------------------------------- #
# Prop binding (§5.5) -- literal, reference, and the compile-time
# role-typed-enum contradiction
# --------------------------------------------------------------------------- #

class TestPropBinding:
    def test_value_layer_props_bound_when_data_supplied(self):
        # AES-WEB-002J.19 supersedes the AES-WEB-002J.6 "left unbound" scope
        # this test used to pin. listing.card.standard's listing_ref
        # (LISTING_REF) and density (STR_ENUM) are now both bound.
        # AES-WEB-002J.20: related_listings excludes the page's own listing
        # (Lakeview Lodge), so the one expanded card binds to the companion
        # listing (Riverside Inn) via a listing-aware generated slot id.
        result = ComponentEngine().compile(
            _sa([_BUSINESS_PROFILE_PAGE]), _cp(),
            listing_dataset=_listing_dataset_with_related(), brand_package=_brand(),
        )
        card = next(
            inst for inst in _page(result.component_manifest, "/hotels/lakeview-lodge/").components
            if inst.component_id == "listing.card.standard"
        )
        assert card.props["density"] in ("comfortable", "compact")
        assert card.props["listing_ref"] == "bind.listing_name.riverside-inn"
        block = next(
            b for b in result.content_package.blocks if b.slot_id == card.props["listing_ref"]
        )
        assert block.text == "Riverside Inn"

    def test_unbindable_required_role_prop_is_compile_error(self):
        # §5.5: an unbound required prop is a compile error *here*. Craft a
        # layout.section.container-shaped fallback that carries a role-typed
        # required prop whose enum excludes "submission"; both required
        # submission slots fall back to it, so binding runs and must raise.
        bad = make_definition(
            component_id="layout.section.container",
            component_family=ComponentFamily.LAYOUT,
            lifecycle_status=LifecycleStatus.ACTIVE,
            rendering_contract=RenderingContract(
                emitter_key="layout.section.container@1", class_prefix="ac-layout"
            ),
            analytics_contract=AnalyticsContract(
                impression_id="layout-section-container"
            ),
            required_props={
                "ctx": PropSpec(
                    prop_type=PropType.STR_ENUM,
                    enum_values=("home",),  # excludes "submission"
                    description="role-typed prop whose enum omits the host role",
                ),
            },
        )
        registry = ComponentRegistry([bad])
        page = PagePlan(route="/submit", page_type="submission", title="Submit")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa([page]), _cp(), registry=registry)
        diagnostics = exc.value.diagnostics
        assert "unbindable_required_props" in diagnostics
        offenders = diagnostics["unbindable_required_props"]
        assert any(
            o["component_id"] == "layout.section.container" and o["prop"] == "ctx"
            for o in offenders
        )


# --------------------------------------------------------------------------- #
# Selection-pipeline integration through the engine
# --------------------------------------------------------------------------- #

class TestSelectionIntegration:
    def test_injected_registry_is_used(self):
        # An empty registry cannot fill the home required slots -> failure,
        # proving the injected registry (not the default catalog) is consulted.
        with pytest.raises(ComponentResolutionError):
            ComponentEngine().compile(
                _sa([_HOME_PAGE]), _cp(), registry=ComponentRegistry([])
            )

    def test_strict_lifecycle_flags_reject_proposed_catalog(self):
        # Every registered component is PROPOSED; strict flags (no PROPOSED)
        # eliminate all candidates and fallbacks -> required slots unresolved.
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_HOME_PAGE]), _cp(),
                lifecycle_flags=LifecycleBuildFlags(),
            )
        assert "unresolved_required_slots" in exc.value.diagnostics

    def test_incompatible_versions_reject_catalog(self):
        # Definitions pin renderer <2.0.0; a 2.x renderer fails compatibility.
        bad_versions = dict(DEFAULT_COMPATIBILITY_VERSIONS, renderer="2.0.0")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_HOME_PAGE]), _cp(),
                compatibility_versions=bad_versions,
            )
        assert "unresolved_required_slots" in exc.value.diagnostics

    def test_default_flags_allow_proposed(self):
        # The default lifecycle flags allow PROPOSED, so the all-PROPOSED
        # catalog resolves (selection succeeds) without explicit flags --
        # Phase B then honestly fails for lack of content/brand data, which
        # is a distinct, expected concern from lifecycle filtering.
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa([_HOME_PAGE]), _cp())
        # Proves selection (not lifecycle filtering) reached Phase B:
        # the failure is a binding gap, not "unresolved_required_slots".
        assert "unresolved_required_slots" not in exc.value.diagnostics


# --------------------------------------------------------------------------- #
# Role -> recipe map + unsupported roles
# --------------------------------------------------------------------------- #

class TestRecipeRoleMapping:
    def test_map_covers_every_page_role(self):
        assert set(RECIPE_SLOTS_BY_PAGE_ROLE) == {r.value for r in PageRole}

    def test_unknown_page_type_reported(self):
        page = PagePlan(route="/x", page_type="not-a-role", title="X")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa([page]), _cp())
        diagnostics = exc.value.diagnostics
        assert "unsupported_page_roles" in diagnostics
        assert diagnostics["unsupported_page_roles"] == [
            {"route": "/x", "page_type": "not-a-role", "commercial_strategy": "directory"}
        ]


# --------------------------------------------------------------------------- #
# Batch error reporting
# --------------------------------------------------------------------------- #

class TestBatchErrorReporting:
    def test_multiple_unsupported_pages_batched_and_sorted(self):
        pages = [
            PagePlan(route="/z", page_type="bogus", title="Z"),
            PagePlan(route="/a", page_type="bogus", title="A"),
        ]
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa(pages), _cp())
        reported = exc.value.diagnostics["unsupported_page_roles"]
        assert [r["route"] for r in reported] == ["/a", "/z"]  # sorted by route

    def test_diagnostics_stage_label(self):
        page = PagePlan(route="/x", page_type="bogus", title="X")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa([page]), _cp())
        assert exc.value.stage == "component_resolution"


# --------------------------------------------------------------------------- #
# Edge cases
# --------------------------------------------------------------------------- #

class TestEdgeCases:
    def test_empty_site_architecture(self):
        result = ComponentEngine().compile(_sa([]), _cp())
        manifest = result.component_manifest
        assert manifest.pages == ()
        assert manifest.selection_trace is not None
        assert manifest.selection_trace.slots == ()

    def test_optional_unbuilt_slots_dropped_but_traced(self):
        # home's featured_zone is optional and points at an unbuilt family;
        # it must not become an instance, but it is still traced (with no
        # chosen component) per §26 / §14.2 step 9.
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        manifest = result.component_manifest
        assert "monetization.sponsor.featured" not in _ids(_page(manifest, "/"))
        featured = next(
            s for s in manifest.selection_trace.slots
            if s.slot_id == "/#featured_zone"
        )
        assert featured.chosen_component_id == ""

    def test_optional_architecturally_unbindable_slot_dropped_but_traced(self):
        # AES-WEB-002J.19: home's locations_grid slot is optional with no
        # fallback; directory.locations.grid is categorically unbindable
        # (location_source_ref/location_tiles are STRUCTURED_DEFERRED), so
        # bindability-aware selection drops it exactly like an unbuilt-family
        # slot -- no instance, but still traced with no chosen component.
        result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_home_blocks()), brand_package=_brand()
        )
        manifest = result.component_manifest
        assert "directory.locations.grid" not in _ids(_page(manifest, "/"))
        locations = next(
            s for s in manifest.selection_trace.slots
            if s.slot_id == "/#locations_grid"
        )
        assert locations.chosen_component_id == ""

    def test_empty_page_source_hashes_still_present(self):
        result = ComponentEngine().compile(_sa([]), _cp())
        assert set(result.component_manifest.source_hashes) == {
            "site_architecture", "content_package", "binding_map_version",
            "composition_rules_version", "render_data_version",
            "commercial_strategy", "commercial_strategy_version",
        }

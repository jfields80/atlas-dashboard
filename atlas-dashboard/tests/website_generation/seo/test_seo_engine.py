"""SEOEngine behavior: determinism, PetTripFinder golden validation, route/
content/length/uniqueness failures, scope protection, artifact-store
integration, and contracts/architecture invariants (AES-WEB-001 §5.8;
AES-WEB-002J.5).
"""

from __future__ import annotations

import inspect
from typing import Tuple

import pytest

from engines.website_generation import (
    ArtifactKind,
    BrandPackage,
    BusinessSpec,
    ComponentManifest,
    ContentPackage,
    SEOEngine,
    SEOPackage,
    SiteArchitecture,
    WebsiteGenerationError,
)
from engines.website_generation.brand import BrandEngine
from engines.website_generation.content import ContentEngine
from engines.website_generation.contracts.artifacts import (
    ContentBlock,
    ContentCandidate,
    PagePlan,
    artifact_sha256,
    canonical_artifact_json,
)
from engines.website_generation.contracts.errors import (
    ArtifactValidationError,
    SEOCompilationError,
)
from engines.website_generation.contracts.interfaces import SEOEngineInterface
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)
from engines.website_generation.ia import InformationArchitectureEngine
from engines.website_generation.speccompiler.business_spec_compiler import (
    BusinessSpecCompiler,
)
from repositories.artifact_store_repository import ArtifactStoreRepository

# ---------------------------------------------------------------------------
# PetTripFinder golden fixture -- byte-identical to
# tests/website_generation/content/test_content_engine.py's fixture, so the
# SEO Engine's golden entries compose from the exact same validated content
# the Content Engine already proves valid.
# ---------------------------------------------------------------------------

HOME_HERO_H1 = "Find Pet-Friendly Stays Across the US"
HOME_INTRO = (
    "Pet Trip Finder helps traveling pet owners find verified "
    "pet-friendly hotels, parks, and restaurants across the United "
    "States, with details checked before they go live."
)
HOTELS_HERO_H1 = "Pet-Friendly Hotels Worth Booking"
HOTELS_INTRO = (
    "Browse pet-friendly hotels with clear pet policies, so you can "
    "book a stay that welcomes your dog or cat without any "
    "last-minute surprises at the front desk."
)
PARKS_HERO_H1 = "Parks Where Pets Are Welcome"
PARKS_INTRO = (
    "Explore parks that allow leashed pets, from quiet neighborhood "
    "greenspaces to larger regional trails, each one noted with the "
    "specific rules that apply on site."
)
RESTAURANTS_HERO_H1 = "Restaurants With Pet-Friendly Patios"
RESTAURANTS_INTRO = (
    "Find restaurants with pet-friendly patios and outdoor seating, "
    "so your next meal out does not mean leaving your pet behind in "
    "the car or at home."
)


def _candidate(route: str, slot_id: str, body: str) -> ContentCandidate:
    return ContentCandidate(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_CANDIDATE],
        artifact_kind=ArtifactKind.CONTENT_CANDIDATE,
        source_hashes={},
        page_route=route,
        slot_id=slot_id,
        body=body,
    )


def _pettripfinder_candidates() -> Tuple[ContentCandidate, ...]:
    return (
        _candidate("/", "hero_h1", HOME_HERO_H1),
        _candidate("/", "intro", HOME_INTRO),
        _candidate("/hotels/", "hero_h1", HOTELS_HERO_H1),
        _candidate("/hotels/", "intro", HOTELS_INTRO),
        _candidate("/parks/", "hero_h1", PARKS_HERO_H1),
        _candidate("/parks/", "intro", PARKS_INTRO),
        _candidate("/restaurants/", "hero_h1", RESTAURANTS_HERO_H1),
        _candidate("/restaurants/", "intro", RESTAURANTS_INTRO),
    )


def _spec(golden_compiler_input) -> BusinessSpec:
    return BusinessSpecCompiler().compile(golden_compiler_input)


def _site_for(spec: BusinessSpec) -> SiteArchitecture:
    brand = BrandEngine().resolve(spec)
    return InformationArchitectureEngine().plan(spec, brand)


def _content_for(site: SiteArchitecture, spec: BusinessSpec) -> ContentPackage:
    return ContentEngine().validate(site, _pettripfinder_candidates(), spec)


def _raw_spec(**overrides) -> BusinessSpec:
    fields = dict(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="Pet Trip Finder",
        niche="pet travel",
        audience="pet owners",
        value_proposition="verified pet-friendly stays",
        directory_taxonomy=(),
    )
    fields.update(overrides)
    return BusinessSpec(**fields)


def _site_with_pages(*pages: PagePlan) -> SiteArchitecture:
    """Hand-built SiteArchitecture for structural edge cases the real IA
    Engine output cannot exercise, mirroring test_content_engine.py's
    ``_site_with_pages`` precedent."""
    routes = tuple(page.route for page in pages)
    return SiteArchitecture(
        schema_version="1.1.0",
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
        pages=tuple(pages),
        nav_routes=routes,
        sitemap_routes=routes,
        page_ids={},
        page_hierarchy=(),
        internal_link_topology=(),
    )


def _content_with_blocks(*blocks: ContentBlock) -> ContentPackage:
    return ContentPackage(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )


class TestDeterminism:
    def test_deterministic_equality(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        engine = SEOEngine()
        first = engine.compile(site, content, spec)
        second = engine.compile(site, content, spec)
        assert canonical_artifact_json(first) == canonical_artifact_json(second)

    def test_identical_artifact_hashes_across_repeated_calls(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        engine = SEOEngine()
        hashes = {
            artifact_sha256(engine.compile(site, content, spec)) for _ in range(3)
        }
        assert len(hashes) == 1

    def test_identical_results_across_fresh_engine_instances(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        hashes = {
            artifact_sha256(SEOEngine().compile(site, content, spec))
            for _ in range(3)
        }
        assert len(hashes) == 1

    def test_shuffled_content_block_order_does_not_alter_computed_entries(
        self, golden_compiler_input
    ):
        # Shuffling ContentPackage.blocks changes the ContentPackage's OWN
        # canonical hash (tuple order is part of its identity), so
        # source_hashes["content_package"] legitimately differs between the
        # two calls below -- that is correct content-addressing, not a
        # determinism bug. The invariant this test protects is narrower and
        # more important: the SEO Engine's own lookup is by (page_route,
        # slot_id), never by position, so the *computed* entries, sitemap
        # routes, and robots plan must be identical regardless of block
        # order.
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        shuffled_blocks = content.blocks[5:] + content.blocks[:5]
        shuffled_content = ContentPackage(
            schema_version=content.schema_version,
            artifact_kind=content.artifact_kind,
            source_hashes=content.source_hashes,
            blocks=shuffled_blocks,
        )
        forward = SEOEngine().compile(site, content, spec)
        shuffled = SEOEngine().compile(site, shuffled_content, spec)
        assert forward.entries == shuffled.entries
        assert forward.sitemap_routes == shuffled.sitemap_routes
        assert forward.robots_directives == shuffled.robots_directives
        assert forward.schema_version == shuffled.schema_version
        assert forward.artifact_kind == shuffled.artifact_kind

    def test_diagnostic_ordering_is_deterministic_regardless_of_input_order(self):
        site = _site_with_pages(
            PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro")),
        )
        spec = _raw_spec()
        # Exercises two diagnostic categories at once: an orphaned block
        # (unknown_routes) and a page missing its intro (missing_content).
        content = _content_with_blocks(
            ContentBlock(page_route="/nonexistent/", slot_id="hero_h1", text="Orphan"),
            ContentBlock(page_route="/", slot_id="hero_h1", text="Home Hero"),
        )
        reversed_content = _content_with_blocks(*tuple(reversed(content.blocks)))
        with pytest.raises(SEOCompilationError) as first:
            SEOEngine().compile(site, content, spec)
        with pytest.raises(SEOCompilationError) as second:
            SEOEngine().compile(site, reversed_content, spec)
        assert first.value.diagnostics == second.value.diagnostics


class TestPetTripFinderGolden:
    EXPECTED_TITLES = {
        "/": "Find Pet-Friendly Stays Across the US | Pet Trip Finder",
        "/hotels/": "Pet-Friendly Hotels Worth Booking | Pet Trip Finder",
        "/parks/": "Parks Where Pets Are Welcome | Pet Trip Finder",
        "/restaurants/": "Restaurants With Pet-Friendly Patios | Pet Trip Finder",
    }

    EXPECTED_HOME_META = (
        "Pet Trip Finder helps traveling pet owners find verified "
        "pet-friendly hotels, parks, and restaurants across the United "
        "States, with details checked before they"
    )

    def test_home_intro_exceeds_160_code_points(self):
        assert len(HOME_INTRO) > 160

    def test_exactly_four_entries(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        assert len(package.entries) == 4

    def test_entries_sorted_by_route(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        routes = [entry.route for entry in package.entries]
        assert routes == ["/", "/hotels/", "/parks/", "/restaurants/"]

    def test_expected_titles(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        titles = {entry.route: entry.title for entry in package.entries}
        assert titles == self.EXPECTED_TITLES

    def test_all_titles_fit_within_60_characters_without_truncation(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        for entry in package.entries:
            assert len(entry.title) <= 60

    def test_home_meta_is_word_boundary_truncated_exactly_per_d1(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        home_entry = next(e for e in package.entries if e.route == "/")
        assert home_entry.meta_description == self.EXPECTED_HOME_META
        assert len(home_entry.meta_description) == 159

    def test_other_pages_meta_equals_intro_verbatim(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        by_route = {entry.route: entry.meta_description for entry in package.entries}
        assert by_route["/hotels/"] == HOTELS_INTRO
        assert by_route["/parks/"] == PARKS_INTRO
        assert by_route["/restaurants/"] == RESTAURANTS_INTRO

    def test_every_meta_length_is_between_50_and_160_inclusive(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        for entry in package.entries:
            assert 50 <= len(entry.meta_description) <= 160

    def test_canonical_url_equals_route_for_every_entry(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        for entry in package.entries:
            assert entry.canonical_url == entry.route

    def test_expected_sitemap_routes(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        assert package.sitemap_routes == ("/", "/hotels/", "/parks/", "/restaurants/")

    def test_expected_robots_directives(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        assert package.robots_directives == ("User-agent: *", "Allow: /")

    def test_source_hashes_contain_exactly_the_three_inputs(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        assert set(package.source_hashes) == {
            "site_architecture",
            "content_package",
            "business_spec",
        }

    def test_source_hashes_match_correct_input_artifacts(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        assert package.source_hashes["site_architecture"] == artifact_sha256(site)
        assert package.source_hashes["content_package"] == artifact_sha256(content)
        assert package.source_hashes["business_spec"] == artifact_sha256(spec)

    def test_schema_version_and_artifact_kind_are_enforced(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        assert package.schema_version == "1.0.0"
        assert package.artifact_kind == ArtifactKind.SEO_PACKAGE


class TestValidation:
    def test_content_route_not_in_site_architecture_rejected(self):
        site = _site_with_pages(
            PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro")),
        )
        content = _content_with_blocks(
            ContentBlock(page_route="/", slot_id="hero_h1", text="A Fine Hero"),
            ContentBlock(page_route="/", slot_id="intro", text="I" * 60),
            ContentBlock(page_route="/orphan/", slot_id="hero_h1", text="Orphan Hero"),
        )
        spec = _raw_spec()
        with pytest.raises(SEOCompilationError) as excinfo:
            SEOEngine().compile(site, content, spec)
        assert excinfo.value.stage == "seo_compilation"
        assert excinfo.value.diagnostics["unknown_routes"] == ["/orphan/"]

    def test_page_missing_hero_h1_rejected(self):
        site = _site_with_pages(
            PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro")),
        )
        content = _content_with_blocks(
            ContentBlock(page_route="/", slot_id="intro", text="I" * 60),
        )
        spec = _raw_spec()
        with pytest.raises(SEOCompilationError) as excinfo:
            SEOEngine().compile(site, content, spec)
        assert excinfo.value.stage == "seo_compilation"
        assert {"route": "/", "slot_id": "hero_h1"} in excinfo.value.diagnostics[
            "missing_content"
        ]

    def test_page_missing_intro_rejected(self):
        site = _site_with_pages(
            PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro")),
        )
        content = _content_with_blocks(
            ContentBlock(page_route="/", slot_id="hero_h1", text="A Fine Hero"),
        )
        spec = _raw_spec()
        with pytest.raises(SEOCompilationError) as excinfo:
            SEOEngine().compile(site, content, spec)
        assert {"route": "/", "slot_id": "intro"} in excinfo.value.diagnostics[
            "missing_content"
        ]

    def test_intro_length_between_40_and_49_rejected(self):
        # Passes the Content Engine's own floor (40) but fails the SEO
        # Engine's stricter floor (50) -- exercising the gap between the
        # two independently declared policies.
        site = _site_with_pages(
            PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro")),
        )
        content = _content_with_blocks(
            ContentBlock(page_route="/", slot_id="hero_h1", text="A Fine Hero"),
            ContentBlock(page_route="/", slot_id="intro", text="I" * 45),
        )
        spec = _raw_spec()
        with pytest.raises(SEOCompilationError) as excinfo:
            SEOEngine().compile(site, content, spec)
        assert excinfo.value.diagnostics["meta_length_violations"] == [
            {"route": "/", "length": 45, "limit": 50}
        ]

    def test_duplicate_title_rejected(self):
        site = _site_with_pages(
            PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro")),
            PagePlan(
                route="/hotels/",
                page_type="category",
                content_slots=("hero_h1", "intro"),
            ),
        )
        content = _content_with_blocks(
            ContentBlock(page_route="/", slot_id="hero_h1", text="Same Title"),
            ContentBlock(page_route="/", slot_id="intro", text="I" * 60),
            ContentBlock(page_route="/hotels/", slot_id="hero_h1", text="Same Title"),
            ContentBlock(page_route="/hotels/", slot_id="intro", text="I" * 60),
        )
        spec = _raw_spec()
        with pytest.raises(SEOCompilationError) as excinfo:
            SEOEngine().compile(site, content, spec)
        assert excinfo.value.diagnostics["title_uniqueness_violations"] == [
            {"title": "Same Title | Pet Trip Finder", "routes": ("/", "/hotels/")}
        ]

    def test_unsupported_page_type_rejected(self):
        site = _site_with_pages(
            PagePlan(route="/mystery/", page_type="mystery-role", content_slots=()),
        )
        content = _content_with_blocks()
        spec = _raw_spec()
        with pytest.raises(SEOCompilationError) as excinfo:
            SEOEngine().compile(site, content, spec)
        assert excinfo.value.diagnostics["unsupported_page_types"] == [
            {"route": "/mystery/", "page_type": "mystery-role"}
        ]

    def test_empty_site_architecture_rejects_orphaned_content(self):
        # An empty SiteArchitecture has no known routes at all, so any
        # content block -- however innocuous -- is by definition orphaned.
        site = _site_with_pages()
        content = _content_with_blocks(
            ContentBlock(page_route="/", slot_id="hero_h1", text="Orphaned Hero"),
        )
        spec = _raw_spec()
        with pytest.raises(SEOCompilationError) as excinfo:
            SEOEngine().compile(site, content, spec)
        assert excinfo.value.diagnostics["unknown_routes"] == ["/"]

    def test_empty_site_architecture_with_no_content_succeeds_trivially(self):
        site = _site_with_pages()
        content = _content_with_blocks()
        spec = _raw_spec()
        package = SEOEngine().compile(site, content, spec)
        assert package.entries == ()
        assert package.sitemap_routes == ()

    def test_home_only_site_architecture_succeeds_with_exactly_one_entry(self):
        site = _site_with_pages(
            PagePlan(route="/", page_type="home", content_slots=("hero_h1", "intro")),
        )
        content = _content_with_blocks(
            ContentBlock(page_route="/", slot_id="hero_h1", text="A Fine Hero"),
            ContentBlock(page_route="/", slot_id="intro", text="I" * 60),
        )
        spec = _raw_spec()
        package = SEOEngine().compile(site, content, spec)
        assert len(package.entries) == 1
        assert package.entries[0].route == "/"


class TestScopeProtection:
    def test_only_compile_is_a_public_method(self):
        public_methods = {
            name
            for name in vars(SEOEngine)
            if not name.startswith("_") and callable(getattr(SEOEngine, name))
        }
        assert public_methods == {"compile"}

    def test_compile_signature_has_no_brand_package_parameter(self):
        signature = inspect.signature(SEOEngine.compile)
        assert list(signature.parameters) == [
            "self",
            "site_architecture",
            "content_package",
            "business_spec",
        ]
        for parameter in signature.parameters.values():
            assert parameter.annotation is not BrandPackage
            assert "BrandPackage" not in str(parameter.annotation)

    def test_compile_signature_has_no_component_manifest_parameter(self):
        signature = inspect.signature(SEOEngine.compile)
        for parameter in signature.parameters.values():
            assert parameter.annotation is not ComponentManifest
            assert "ComponentManifest" not in str(parameter.annotation)

    def test_no_structured_data_fields_are_populated(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        assert not hasattr(package, "structured_data")
        assert not hasattr(package, "json_ld")
        assert not hasattr(package, "schema_types")
        for entry in package.entries:
            assert not hasattr(entry, "structured_data")
            assert not hasattr(entry, "json_ld")


class TestArtifactStoreIntegration:
    def test_seo_package_stores_after_storing_every_source(
        self, golden_compiler_input, tmp_path
    ):
        store = ArtifactStoreRepository(tmp_path / "cas")
        spec = _spec(golden_compiler_input)
        spec_hash = store.put(spec)

        brand = BrandEngine().resolve(spec)
        store.put(brand)  # required for the SiteArchitecture's own provenance

        site = InformationArchitectureEngine().plan(spec, brand)
        site_hash = store.put(site)

        candidates = _pettripfinder_candidates()
        for candidate in candidates:
            store.put(candidate)

        content = ContentEngine().validate(site, candidates, spec)
        content_hash = store.put(content)

        package = SEOEngine().compile(site, content, spec)
        assert package.source_hashes["site_architecture"] == site_hash
        assert package.source_hashes["content_package"] == content_hash
        assert package.source_hashes["business_spec"] == spec_hash

        package_hash = store.put(package)
        assert package_hash == artifact_sha256(package)
        assert store.exists(package_hash)

        loaded = store.get(package_hash, ArtifactKind.SEO_PACKAGE)
        assert isinstance(loaded, SEOPackage)
        assert loaded.entries == package.entries

    def test_seo_package_rejects_storage_without_its_sources(
        self, golden_compiler_input, tmp_path
    ):
        store = ArtifactStoreRepository(tmp_path / "cas")
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        content = _content_for(site, spec)
        package = SEOEngine().compile(site, content, spec)
        with pytest.raises(ArtifactValidationError):
            store.put(package)


class TestContractsAndArchitecture:
    def test_schema_versions_unchanged(self):
        assert SCHEMA_VERSIONS == {
            ArtifactKind.BUSINESS_SPEC: "1.0.0",
            ArtifactKind.BRAND_PACKAGE: "1.1.0",
            ArtifactKind.SITE_ARCHITECTURE: "1.1.0",
            ArtifactKind.CONTENT_CANDIDATE: "1.0.0",
            ArtifactKind.CONTENT_PACKAGE: "1.0.0",
            ArtifactKind.COMPONENT_MANIFEST: "1.1.0",
            ArtifactKind.LAYOUT_PLAN: "1.0.0",
            ArtifactKind.RENDERED_PAGE_SET: "1.0.0",
            ArtifactKind.SEO_PACKAGE: "1.0.0",
            ArtifactKind.SITE_BUNDLE: "1.0.0",
            ArtifactKind.QUALITY_REPORT: "1.0.0",
            ArtifactKind.BUILD_MANIFEST: "1.0.0",
        }

    def test_seo_package_schema_remains_1_0_0(self):
        assert SCHEMA_VERSIONS[ArtifactKind.SEO_PACKAGE] == "1.0.0"

    def test_no_new_artifact_kind_was_added(self):
        assert {kind.value for kind in ArtifactKind} == {
            "BUSINESS_SPEC",
            "BRAND_PACKAGE",
            "SITE_ARCHITECTURE",
            "CONTENT_CANDIDATE",
            "CONTENT_PACKAGE",
            "COMPONENT_MANIFEST",
            "LAYOUT_PLAN",
            "RENDERED_PAGE_SET",
            "SEO_PACKAGE",
            "SITE_BUNDLE",
            "QUALITY_REPORT",
            "BUILD_MANIFEST",
        }

    def test_engine_versions_contains_seo_engine_1_0_0(self):
        assert ENGINE_VERSIONS["seo_engine"] == "1.0.0"

    def test_seo_engine_version_equals_engine_versions_entry(self):
        assert SEOEngine.version == ENGINE_VERSIONS["seo_engine"]

    def test_seo_compilation_error_hierarchy_and_defaults(self):
        assert issubclass(SEOCompilationError, WebsiteGenerationError)
        error = SEOCompilationError("boom", diagnostics={"x": 1})
        assert error.stage == "seo_compilation"
        assert error.retryable is False
        assert error.diagnostics == {"x": 1}

    def test_seo_engine_interface_is_abstract(self):
        assert issubclass(SEOEngine, SEOEngineInterface)
        with pytest.raises(TypeError):
            SEOEngineInterface()  # abstract; cannot be instantiated

    def test_seo_engine_is_publicly_exported(self):
        import engines.website_generation as wge

        assert "SEOEngine" in wge.__all__
        assert wge.SEOEngine is SEOEngine

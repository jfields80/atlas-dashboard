"""InformationArchitectureEngine behavior: determinism, page-inventory
golden expectations, validation, and artifact-store integration
(AES-WEB-001 §5.3 / Part 2 / Part 13 Phase 2).
"""

from __future__ import annotations

import pytest

from engines.website_generation import (
    ArtifactKind,
    BrandPackage,
    BusinessSpec,
    SiteArchitecture,
)
from engines.website_generation.brand import BrandEngine
from engines.website_generation.contracts.artifacts import (
    InternalLinkIntent,
    PageHierarchyEntry,
    PagePlan,
    SpecCompilerInput,
    artifact_sha256,
    canonical_artifact_json,
)
from engines.website_generation.contracts.errors import (
    ArchitecturePlanningError,
    ArtifactValidationError,
)
from engines.website_generation.ia import InformationArchitectureEngine
from engines.website_generation.ia.information_architecture_engine import (
    _validate_site_graph,
    slugify,
)
from engines.website_generation.speccompiler.business_spec_compiler import (
    BusinessSpecCompiler,
)
from repositories.artifact_store_repository import ArtifactStoreRepository


def _brand_for(spec: BusinessSpec) -> BrandPackage:
    return BrandEngine().resolve(spec)


def _compiled_spec(**overrides) -> BusinessSpec:
    fields = dict(
        business_name="Summit Legal Advisors",
        niche="professional legal services",
        audience="B2B clients seeking counsel",
        value_proposition="Reliable professional legal services for growing firms",
        directory_taxonomy=("contracts", "compliance"),
        monetization_model="retainer",
        upstream_hashes={},
    )
    fields.update(overrides)
    return BusinessSpecCompiler().compile(SpecCompilerInput(**fields))


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


def _raw_brand() -> BrandPackage:
    return BrandPackage(
        schema_version="1.1.0",
        artifact_kind=ArtifactKind.BRAND_PACKAGE,
        source_hashes={},
    )


class TestDeterminism:
    def test_deterministic_equality(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        engine = InformationArchitectureEngine()
        first = engine.plan(spec, brand)
        second = engine.plan(spec, brand)
        assert canonical_artifact_json(first) == canonical_artifact_json(second)

    def test_identical_artifact_hashes_across_repeated_calls(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        engine = InformationArchitectureEngine()
        hashes = {artifact_sha256(engine.plan(spec, brand)) for _ in range(3)}
        assert len(hashes) == 1

    def test_identical_results_across_fresh_engine_instances(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        hashes = {
            artifact_sha256(InformationArchitectureEngine().plan(spec, brand))
            for _ in range(3)
        }
        assert len(hashes) == 1


class TestPetTripFinderGolden:
    def test_page_inventory_is_home_plus_one_category_per_taxonomy_entry(
        self, golden_compiler_input
    ):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        routes = [page.route for page in site.pages]
        assert routes == ["/", "/hotels/", "/parks/", "/restaurants/"]
        roles = {page.route: page.page_type for page in site.pages}
        assert roles["/"] == "home"
        assert roles["/hotels/"] == "category"
        assert roles["/parks/"] == "category"
        assert roles["/restaurants/"] == "category"

    def test_multiple_page_roles_present(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        assert {page.page_type for page in site.pages} == {"home", "category"}

    def test_nav_and_sitemap_routes_cover_every_page(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        all_routes = tuple(sorted(page.route for page in site.pages))
        assert site.nav_routes == all_routes
        assert site.sitemap_routes == all_routes

    def test_hierarchy_is_home_rooted_two_levels(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        by_route = {entry.route: entry.parent_route for entry in site.page_hierarchy}
        assert by_route["/"] == ""
        assert by_route["/hotels/"] == "/"
        assert by_route["/parks/"] == "/"
        assert by_route["/restaurants/"] == "/"

    def test_internal_link_topology_is_parent_child_only(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        by_source = {
            link.from_route: link.to_routes for link in site.internal_link_topology
        }
        assert by_source["/"] == ("/hotels/", "/parks/", "/restaurants/")
        assert by_source["/hotels/"] == ("/",)
        assert by_source["/parks/"] == ("/",)
        assert by_source["/restaurants/"] == ("/",)

    def test_no_geography_or_profile_pages_fabricated(self, golden_compiler_input):
        # BusinessSpec.geography is a single free-form string and there is
        # no listing-inventory input; the approved page universe is
        # home + one category page per taxonomy entry only.
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        assert len(site.pages) == 4
        for page in site.pages:
            assert page.page_type in ("home", "category")

    def test_page_ids_are_stable_and_unique(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        assert len(site.page_ids) == len(site.pages)
        assert len(set(site.page_ids.values())) == len(site.page_ids)
        site2 = InformationArchitectureEngine().plan(spec, brand)
        assert site.page_ids == site2.page_ids

    def test_source_hashes_reference_both_inputs(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        assert site.source_hashes == {
            "business_spec": artifact_sha256(spec),
            "brand_package": artifact_sha256(brand),
        }

    def test_content_slots_declared_for_every_page(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        for page in site.pages:
            assert page.content_slots == ("hero_h1", "intro")

    def test_titles_are_real_not_empty(self, golden_compiler_input):
        # AES-WEB-002K.1 supersedes this test's original premise: real
        # navigation labels need real page titles, so IA now always
        # populates them -- spec.business_name for home, the taxonomy
        # entry's own text for each category. This does not cross into
        # content/SEO generation (§5.3's boundary is unchanged) -- IA
        # already has both values in hand from its own inputs, nothing is
        # drafted or authored.
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        by_route = {page.route: page.title for page in site.pages}
        assert by_route["/"] == spec.business_name
        assert by_route["/hotels/"] == "hotels"
        assert by_route["/parks/"] == "parks"
        assert by_route["/restaurants/"] == "restaurants"
        for page in site.pages:
            assert page.title != ""


class TestEmptyTaxonomy:
    def test_empty_taxonomy_yields_home_only_site(self):
        spec = _compiled_spec(directory_taxonomy=())
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        assert [page.route for page in site.pages] == ["/"]
        assert site.page_hierarchy == (
            PageHierarchyEntry(route="/", parent_route=""),
        )
        assert site.internal_link_topology == ()
        assert site.nav_routes == ("/",)
        assert site.sitemap_routes == ("/",)


class TestValidation:
    def test_invalid_spec_raises_architecture_planning_error(self):
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            InformationArchitectureEngine().plan(
                _raw_spec(
                    business_name="",
                    niche="",
                    audience="valid audience",
                    value_proposition="   ",
                ),
                _raw_brand(),
            )
        missing = excinfo.value.diagnostics["missing_fields"]
        assert "business_name" in missing
        assert "niche" in missing
        assert "value_proposition" in missing
        assert "audience" not in missing
        assert excinfo.value.stage == "ia_planning"
        assert excinfo.value.retryable is False

    def test_duplicate_taxonomy_collision_names_every_offender(self):
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            InformationArchitectureEngine().plan(
                _raw_spec(directory_taxonomy=("Parks", "parks", "Hotels")),
                _raw_brand(),
            )
        duplicates = excinfo.value.diagnostics["duplicate_routes"]
        assert duplicates == {"/parks/": ["Parks", "parks"]}

    def test_unsluggable_taxonomy_entry_is_reported(self):
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            InformationArchitectureEngine().plan(
                _raw_spec(directory_taxonomy=("!!!", "hotels")),
                _raw_brand(),
            )
        assert excinfo.value.diagnostics["unsluggable_taxonomy_entries"] == ["!!!"]

    def test_both_taxonomy_problems_batch_reported_together(self):
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            InformationArchitectureEngine().plan(
                _raw_spec(directory_taxonomy=("!!!", "Parks", "parks")),
                _raw_brand(),
            )
        diagnostics = excinfo.value.diagnostics
        assert diagnostics["unsluggable_taxonomy_entries"] == ["!!!"]
        assert diagnostics["duplicate_routes"] == {"/parks/": ["Parks", "parks"]}


class TestSlugify:
    def test_lowercases_and_hyphenates(self):
        assert slugify("Pet-Friendly Parks!") == "pet-friendly-parks"

    def test_strips_surrounding_whitespace_and_punctuation(self):
        assert slugify("  Hotels  ") == "hotels"
        assert slugify("...Restaurants...") == "restaurants"

    def test_punctuation_only_yields_empty_slug(self):
        assert slugify("!!!") == ""

    def test_deterministic(self):
        assert slugify("Parks") == slugify("Parks")


class TestStructuralInvariantsDirectly:
    """Hand-built graphs exercising ``_validate_site_graph`` directly.

    ``InformationArchitectureEngine.plan()`` always constructs a valid
    two-level tree, so these violations are unreachable through the public
    API; this proves the defense-in-depth validator itself catches each
    one (AES-WEB-001 §5.3 enforcement requirements).
    """

    @staticmethod
    def _pages(*routes):
        return tuple(PagePlan(route=route, page_type="category") for route in routes)

    def test_detects_cycle(self):
        pages = self._pages("/a/", "/b/")
        hierarchy = (
            PageHierarchyEntry(route="/a/", parent_route="/b/"),
            PageHierarchyEntry(route="/b/", parent_route="/a/"),
        )
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            _validate_site_graph(pages, hierarchy, (), {"/a/": "x", "/b/": "y"})
        assert set(excinfo.value.diagnostics["cyclic_pages"]) == {"/a/", "/b/"}

    def test_detects_orphan_with_missing_parent(self):
        pages = self._pages("/a/", "/b/")
        hierarchy = (
            PageHierarchyEntry(route="/a/", parent_route=""),
            PageHierarchyEntry(route="/b/", parent_route="/missing/"),
        )
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            _validate_site_graph(pages, hierarchy, (), {"/a/": "x", "/b/": "y"})
        assert excinfo.value.diagnostics["orphan_pages"] == ["/b/"]
        assert excinfo.value.diagnostics["invalid_parents"] == ["/b/"]

    def test_detects_duplicate_root(self):
        pages = self._pages("/a/", "/b/")
        hierarchy = (
            PageHierarchyEntry(route="/a/", parent_route=""),
            PageHierarchyEntry(route="/b/", parent_route=""),
        )
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            _validate_site_graph(pages, hierarchy, (), {"/a/": "x", "/b/": "y"})
        assert excinfo.value.diagnostics["root_count"] == 2

    def test_detects_zero_roots(self):
        pages = self._pages("/a/")
        hierarchy = (PageHierarchyEntry(route="/a/", parent_route="/a/"),)
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            _validate_site_graph(pages, hierarchy, (), {"/a/": "x"})
        assert excinfo.value.diagnostics["root_count"] == 0

    def test_detects_invalid_link_target(self):
        pages = self._pages("/a/", "/b/")
        hierarchy = (
            PageHierarchyEntry(route="/a/", parent_route=""),
            PageHierarchyEntry(route="/b/", parent_route="/a/"),
        )
        links = (InternalLinkIntent(from_route="/a/", to_routes=("/nonexistent/",)),)
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            _validate_site_graph(pages, hierarchy, links, {"/a/": "x", "/b/": "y"})
        assert excinfo.value.diagnostics["invalid_link_targets"] == ["/nonexistent/"]

    def test_detects_duplicate_page_routes(self):
        pages = (
            PagePlan(route="/a/", page_type="category"),
            PagePlan(route="/a/", page_type="category"),
        )
        hierarchy = (PageHierarchyEntry(route="/a/", parent_route=""),)
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            _validate_site_graph(pages, hierarchy, (), {"/a/": "x"})
        assert excinfo.value.diagnostics["duplicate_page_routes"] == ["/a/"]

    def test_detects_duplicate_page_ids(self):
        pages = self._pages("/a/", "/b/")
        hierarchy = (
            PageHierarchyEntry(route="/a/", parent_route=""),
            PageHierarchyEntry(route="/b/", parent_route="/a/"),
        )
        with pytest.raises(ArchitecturePlanningError) as excinfo:
            _validate_site_graph(pages, hierarchy, (), {"/a/": "same", "/b/": "same"})
        assert excinfo.value.diagnostics["duplicate_page_ids"] == ["same"]

    def test_valid_graph_raises_nothing(self):
        pages = self._pages("/a/", "/b/")
        hierarchy = (
            PageHierarchyEntry(route="/a/", parent_route=""),
            PageHierarchyEntry(route="/b/", parent_route="/a/"),
        )
        links = (InternalLinkIntent(from_route="/a/", to_routes=("/b/",)),)
        _validate_site_graph(pages, hierarchy, links, {"/a/": "x", "/b/": "y"})


class TestArtifactStoreIntegration:
    def test_site_architecture_stores_after_storing_both_sources(
        self, golden_compiler_input, tmp_path
    ):
        store = ArtifactStoreRepository(tmp_path / "cas")
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        spec_hash = store.put(spec)

        brand = _brand_for(spec)
        brand_hash = store.put(brand)

        site = InformationArchitectureEngine().plan(spec, brand)
        assert site.source_hashes == {
            "business_spec": spec_hash,
            "brand_package": brand_hash,
        }

        site_hash = store.put(site)
        assert site_hash == artifact_sha256(site)
        assert store.exists(site_hash)

        loaded = store.get(site_hash, ArtifactKind.SITE_ARCHITECTURE)
        assert isinstance(loaded, SiteArchitecture)
        assert loaded.pages == site.pages
        assert loaded.page_hierarchy == site.page_hierarchy
        assert loaded.internal_link_topology == site.internal_link_topology

    def test_site_architecture_rejects_storage_without_its_sources(
        self, golden_compiler_input, tmp_path
    ):
        store = ArtifactStoreRepository(tmp_path / "cas")
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        brand = _brand_for(spec)
        site = InformationArchitectureEngine().plan(spec, brand)
        with pytest.raises(ArtifactValidationError):
            store.put(site)

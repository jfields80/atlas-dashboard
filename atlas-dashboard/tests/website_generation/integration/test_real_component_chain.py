"""Real Component-Engine-to-Repository chain integration test
(AES-WEB-002J.19; ADR-WEB-CONTENT-BINDING-MAP; AES-WEB-001 §5.5).

Proves the mission's end-to-end success criterion: using the curated,
honestly-bindable fixture (``fixtures.component_binding_fixture`` -- home +
one real business-profile route), the REAL

    ComponentEngine Phase A -> Phase B
    -> LayoutEngine
    -> Renderer
    -> AssemblyEngine
    -> QualityGateEngine
    -> SiteBundleRepository

chain succeeds with **no** handcrafted post-``compile()`` repairs, **no**
``"Resolved ..."`` placeholder values, and **no** manual insertion of
required props or content_refs. Distinct from the J.13 local demo harness
(``scripts/generate_local_demo_site.py`` / ``fixtures/local_demo_site.py``),
which hand-binds every ``ComponentInstance`` because the Component Engine
could not yet bind anything -- this test proves the Component Engine itself
now performs that binding, on the subset the current catalog can honestly
support (see the module docstring of ``component_binding_fixture.py`` for
exactly why the "category" family of page roles is excluded this delivery).

Explicitly NOT proven here (see the J.19 implementation report's Level-C
truth check): the full category/city/search-results recipe families (still
architecturally blocked on "pagination"/"zero_results"), real navigation
labels, real category/location tile labels, repeated listing collections,
multi-field listing cards, structured per-day hours, or gallery images.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_TESTS_ROOT = _REPO_ROOT / "tests"
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

from website_generation.fixtures.component_binding_fixture import (  # noqa: E402
    build_binding_fixture_inputs,
)

from engines.website_generation.assembly.assembly_engine import AssemblyEngine  # noqa: E402
from engines.website_generation.components.component_engine import ComponentEngine  # noqa: E402
from engines.website_generation.components.registry import build_default_registry  # noqa: E402
from engines.website_generation.contracts.artifacts import QualityReport, SiteBundle  # noqa: E402
from engines.website_generation.gates.quality_gate_engine import QualityGateEngine  # noqa: E402
from engines.website_generation.layouts.layout_engine import LayoutEngine  # noqa: E402
from engines.website_generation.rendering.renderer import Renderer  # noqa: E402
from repositories.site_bundle_repository import SiteBundleRepository  # noqa: E402


def _run_real_chain():
    """Drive every real engine in sequence -- no hand-repair anywhere."""
    fixture = build_binding_fixture_inputs()
    registry = build_default_registry()

    compilation = ComponentEngine().compile(
        fixture.site_architecture,
        fixture.content_package,
        listing_dataset=fixture.listing_dataset,
        brand_package=fixture.brand_package,
        registry=registry,
    )
    layout = LayoutEngine(registry).compose(
        compilation.component_manifest, fixture.brand_package
    )
    rendered = Renderer(registry).render(
        layout, compilation.component_manifest, compilation.content_package, fixture.brand_package
    )
    bundle = AssemblyEngine().assemble(rendered, fixture.seo_package, fixture.brand_package)
    report = QualityGateEngine().evaluate(
        bundle, fixture.seo_package, compilation.content_package, fixture.site_architecture
    )
    return fixture, compilation, layout, rendered, bundle, report


class TestRealChainSucceeds:
    def test_component_engine_output_is_renderer_consumable(self):
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        assert compilation.component_manifest.pages
        assert rendered.pages  # the Renderer accepted the real, bound manifest

    def test_projected_content_package_is_what_renderer_consumed(self):
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        assert len(compilation.content_package.blocks) > len(fixture.content_package.blocks)

    def test_original_fixture_content_package_unmodified(self):
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        fixture2 = build_binding_fixture_inputs()
        assert fixture.content_package.blocks == fixture2.content_package.blocks

    def test_assembly_succeeds(self):
        _, _, _, _, bundle, _ = _run_real_chain()
        assert isinstance(bundle, SiteBundle)
        assert bundle.files and bundle.bundle_hash

    def test_quality_gates_execute(self):
        _, _, _, _, _, report = _run_real_chain()
        assert isinstance(report, QualityReport)
        assert report.gate_results  # at least one gate actually ran

    def test_repository_materializes(self, tmp_path):
        _, _, _, _, bundle, _ = _run_real_chain()
        result = SiteBundleRepository().materialize(bundle, str(tmp_path / "site"))
        assert result.written_paths
        for path in result.written_paths:
            assert (tmp_path / "site" / path).is_file()

    def test_real_listing_name_appears_in_rendered_html(self):
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        profile_page = next(p for p in rendered.page_details if p.route == fixture.routes[1])
        assert "Lakeview Lodge" in profile_page.html

    def test_no_resolved_placeholder_in_rendered_html(self):
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        for page in rendered.page_details:
            assert "Resolved " not in page.html
            assert "TODO" not in page.html

    def test_no_absolute_local_path_leaks(self, tmp_path):
        _, _, _, _, bundle, _ = _run_real_chain()
        needle = str(_REPO_ROOT)
        for f in bundle.files:
            assert needle not in f.content

    def test_pipeline_remains_unwired(self):
        from engines.website_generation.constants.build import (
            PHASE1_EXECUTED_STAGES,
            STAGE_SPEC_COMPILATION,
        )

        assert PHASE1_EXECUTED_STAGES == (STAGE_SPEC_COMPILATION,)

    def test_all_components_remain_proposed(self):
        registry = build_default_registry()
        ids = [d.component_id for d in registry.all_definitions()]
        assert {str(registry.lifecycle(c)) for c in ids} == {"LifecycleStatus.PROPOSED"}


class TestDeterminism:
    def test_two_runs_byte_identical_bundle_hash(self):
        _, _, _, _, bundle_a, _ = _run_real_chain()
        _, _, _, _, bundle_b, _ = _run_real_chain()
        assert bundle_a.bundle_hash == bundle_b.bundle_hash

    def test_two_materializations_byte_identical(self, tmp_path):
        _, _, _, _, bundle, _ = _run_real_chain()
        a, b = tmp_path / "a", tmp_path / "b"
        ra = SiteBundleRepository().materialize(bundle, str(a))
        rb = SiteBundleRepository().materialize(bundle, str(b))
        for rel in ra.written_paths:
            assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


class TestForbiddenScope:
    def test_no_forbidden_runtime_facilities(self):
        # Only the fixture module is checked -- this test file's own source
        # legitimately *names* the banned strings (in this very list, and in
        # its module docstring describing what the fixture must not do), so
        # scanning it would self-trigger on quoted prose, not real usage.
        fixture_src = (
            _REPO_ROOT / "tests" / "website_generation" / "fixtures" / "component_binding_fixture.py"
        ).read_text(encoding="utf-8")
        for banned in (
            "import socket", "import urllib", "import requests", "import uuid",
            "import random", "import datetime", "os.environ", "import webbrowser",
            "http.server", "import subprocess", "time.time", "anthropic",
        ):
            assert banned not in fixture_src, banned

    def test_j13_local_demo_fixture_untouched(self):
        # This test file must never *import* the J.13 harness/fixture module
        # -- the two are independent proofs (hand-bound vs. really-bound).
        # An AST import check (not a substring search) avoids self-triggering
        # on this very module's docstring, which names the J.13 modules for
        # documentation purposes.
        import ast

        tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            elif isinstance(node, ast.Import):
                imported_modules.update(a.name for a in node.names)
        assert not any("local_demo_site" in m for m in imported_modules)
        assert not any("generate_local_demo_site" in m for m in imported_modules)

    def test_category_role_still_honestly_fails_for_an_unmatched_category(self):
        # AES-WEB-002J.19 found the category recipe unconditionally
        # unbindable (pagination/zero_results required, no fallback, both
        # categorically unbindable). AES-WEB-002J.20's operator-authorized
        # recipe amendment (a structural fallback on exactly those two
        # slots) changed that -- see test_component_engine.py::
        # TestGoldenRealCatalog::
        # test_category_recipe_succeeds_via_honest_pagination_fallback for
        # the now-succeeding proof with a real, matching category.
        #
        # This fixture's ListingDataset only has a "hotels" category, so a
        # route naming an unrelated category slug still fails honestly --
        # now for the true reason (listing_cards' repetition rule cannot
        # resolve any matching category for the route), not the old
        # pagination architectural gap.
        from engines.website_generation.contracts.artifacts import (
            ContentBlock,
            PagePlan,
            SiteArchitecture,
        )
        from engines.website_generation.contracts.artifacts import ContentPackage as CP
        from engines.website_generation.contracts.enums import ArtifactKind as AK
        from engines.website_generation.contracts.errors import ComponentResolutionError
        from engines.website_generation.contracts.versions import SCHEMA_VERSIONS as SV

        fixture = build_binding_fixture_inputs()
        sa = SiteArchitecture(
            schema_version=SV[AK.SITE_ARCHITECTURE], artifact_kind=AK.SITE_ARCHITECTURE,
            source_hashes={}, pages=(PagePlan(route="/vets/", page_type="category", title=""),),
            nav_routes=(), sitemap_routes=("/vets/",),
        )
        cp = CP(
            schema_version=SV[AK.CONTENT_PACKAGE], artifact_kind=AK.CONTENT_PACKAGE, source_hashes={},
            blocks=(
                ContentBlock(page_route="/vets/", slot_id="hero_h1", text="Pet-friendly vets"),
                ContentBlock(page_route="/vets/", slot_id="intro", text="Vets that welcome pets."),
            ),
        )
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                sa, cp, listing_dataset=fixture.listing_dataset, brand_package=fixture.brand_package,
            )
        failures = exc.value.diagnostics["repetition_failures"]
        entry = next(f for f in failures if f["recipe_slot_id"] == "listing_cards")
        assert "repeat_scope_unresolved" in entry["reason"]

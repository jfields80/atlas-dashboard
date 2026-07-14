"""Listing repetition and collection composition real-chain integration test
(AES-WEB-002J.20; ADR-WEB-CONTENT-BINDING-MAP; AES-WEB-001 §5.5).

Proves the mission's P1/P2 end-to-end success criteria, using the curated,
honestly-bindable fixture (``fixtures.listing_collection_fixture`` -- home +
one real category route + one real business-profile route, five listings)
through the REAL

    ComponentEngine Phase A -> Repetition -> Phase B
    -> LayoutEngine
    -> Renderer
    -> AssemblyEngine
    -> QualityGateEngine
    -> SiteBundleRepository

chain, with **no** handcrafted post-``compile()`` repairs and **no**
manual insertion of required props, content_refs, or extra instances.

* **P1** (business-profile ``related_listings``): the profile route's own
  listing (Alpine Lantern Lodge) is excluded from its own "related" set
  (``exclude_self=True``) -- the other four listings each produce one
  ``listing.card.standard`` instance.
* **P2** (category ``listing_cards``, only reachable after the
  AES-WEB-002J.20 operator-authorized category recipe amendment): all five
  listings in the "hotels" category each produce one ``listing.card.standard``
  instance -- proving the category recipe now compiles end to end, not just
  that its previously-unfallback-able ``pagination``/``zero_results`` slots
  now resolve to a structural fallback.

Known, pre-existing, unrelated quality-gate findings (CG-CMP-005 heading
hierarchy, CG-CMP-006 landmark hierarchy -- see the J.19 implementation
report) are expected and asserted honestly here, never hidden behind a
false ``certified=True``.
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

from website_generation.fixtures.listing_collection_fixture import (  # noqa: E402
    build_listing_collection_fixture_inputs,
)

from engines.website_generation.assembly.assembly_engine import AssemblyEngine  # noqa: E402
from engines.website_generation.components.component_engine import ComponentEngine  # noqa: E402
from engines.website_generation.components.registry import build_default_registry  # noqa: E402
from engines.website_generation.contracts.artifacts import QualityReport, SiteBundle  # noqa: E402
from engines.website_generation.contracts.enums import GateSeverity  # noqa: E402
from engines.website_generation.gates.quality_gate_engine import QualityGateEngine  # noqa: E402
from engines.website_generation.layouts.layout_engine import LayoutEngine  # noqa: E402
from engines.website_generation.rendering.renderer import Renderer  # noqa: E402
from repositories.site_bundle_repository import SiteBundleRepository  # noqa: E402

# The only quality-gate findings this fixture is known and expected to
# produce -- pre-existing (J.19), unrelated to repetition (see module
# docstring). Any OTHER blocking failure is a real regression, not a known
# gap, and must fail the test loudly rather than be swallowed.
_KNOWN_BLOCKING_GATE_IDS = frozenset({"CG-CMP-005", "CG-CMP-006"})


def _run_real_chain():
    """Drive every real engine in sequence -- no hand-repair anywhere."""
    fixture = build_listing_collection_fixture_inputs()
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


class TestP1RelatedListingsRepetition:
    def test_related_listings_excludes_hosting_listing(self):
        fixture, compilation, *_ = _run_real_chain()
        page = next(
            p for p in compilation.component_manifest.pages if p.route == fixture.profile_route
        )
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        bound_ids = {c.props["listing_ref"].split(".")[-1] for c in cards}
        assert fixture.hosting_listing_slug not in bound_ids

    def test_related_listings_expands_to_every_other_matching_listing(self):
        fixture, compilation, *_ = _run_real_chain()
        page = next(
            p for p in compilation.component_manifest.pages if p.route == fixture.profile_route
        )
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        bound_ids = [c.props["listing_ref"].split(".")[-1] for c in cards]
        assert bound_ids == [
            "cedar-harbor-inn", "maple-ridge-retreat", "northstar-guest-house", "willow-creek-suites",
        ]

    def test_related_listing_names_appear_in_rendered_html(self):
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        page = next(p for p in rendered.page_details if p.route == fixture.profile_route)
        assert "Cedar Harbor Inn" in page.html
        assert "Maple Ridge Retreat" in page.html
        assert "Northstar Guest House" in page.html
        assert "Willow Creek Suites" in page.html

    def test_hosting_listings_own_name_still_appears_once_via_profile_header(self):
        # The page's own listing is excluded from related_listings, but it
        # is still the profile's subject -- its name must still appear
        # (via profile.header.business), just not as a "related" card.
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        page = next(p for p in rendered.page_details if p.route == fixture.profile_route)
        assert "Alpine Lantern Lodge" in page.html


class TestP2CategoryListingCardsRepetition:
    def test_category_recipe_compiles_after_amendment(self):
        fixture, compilation, *_ = _run_real_chain()
        page = next(
            p for p in compilation.component_manifest.pages if p.route == fixture.category_route
        )
        assert page.components  # the category recipe fully resolved and bound

    def test_listing_cards_expands_to_all_five_listings_in_dataset_order(self):
        fixture, compilation, *_ = _run_real_chain()
        page = next(
            p for p in compilation.component_manifest.pages if p.route == fixture.category_route
        )
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        bound_ids = [c.props["listing_ref"].split(".")[-1] for c in cards]
        assert bound_ids == [
            "alpine-lantern-lodge", "cedar-harbor-inn", "maple-ridge-retreat",
            "northstar-guest-house", "willow-creek-suites",
        ]

    def test_pagination_and_zero_results_are_honestly_omitted(self):
        # AES-WEB-002K.1 (§26 category-control cleanup) supersedes the
        # AES-WEB-002J.20 structural fallback proved here previously:
        # pagination/zero_results are now optional with no fallback (no
        # pagination/zero-state source artifact exists yet, unchanged) --
        # an empty meaningless <div> is worse for a publishable page than
        # honestly omitting the slot. No control UI is invented either way.
        fixture, compilation, *_ = _run_real_chain()
        pagination_trace = next(
            s for s in compilation.component_manifest.selection_trace.slots
            if s.slot_id == "%s#pagination" % fixture.category_route
        )
        zero_results_trace = next(
            s for s in compilation.component_manifest.selection_trace.slots
            if s.slot_id == "%s#zero_results" % fixture.category_route
        )
        assert pagination_trace.chosen_component_id == ""
        assert zero_results_trace.chosen_component_id == ""

    def test_all_five_listing_names_appear_in_rendered_html(self):
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        page = next(p for p in rendered.page_details if p.route == fixture.category_route)
        for name in (
            "Alpine Lantern Lodge", "Cedar Harbor Inn", "Maple Ridge Retreat",
            "Northstar Guest House", "Willow Creek Suites",
        ):
            assert name in page.html


class TestEndToEndChainSucceeds:
    def test_assembly_succeeds(self):
        _, _, _, _, bundle, _ = _run_real_chain()
        assert isinstance(bundle, SiteBundle)
        assert bundle.files and bundle.bundle_hash

    def test_quality_gates_execute(self):
        _, _, _, _, _, report = _run_real_chain()
        assert isinstance(report, QualityReport)
        assert report.gate_results

    def test_repository_materializes(self, tmp_path):
        _, _, _, _, bundle, _ = _run_real_chain()
        result = SiteBundleRepository().materialize(bundle, str(tmp_path / "site"))
        assert result.written_paths
        for path in result.written_paths:
            assert (tmp_path / "site" / path).is_file()

    def test_no_resolved_placeholder_in_rendered_html(self):
        fixture, compilation, layout, rendered, bundle, report = _run_real_chain()
        for page in rendered.page_details:
            assert "Resolved " not in page.html
            assert "TODO" not in page.html
            assert "placeholder" not in page.html.lower()

    def test_no_absolute_local_path_leaks(self, tmp_path):
        _, _, _, _, bundle, _ = _run_real_chain()
        needle = str(_REPO_ROOT)
        for f in bundle.files:
            assert needle not in f.content


class TestKnownGateFindingsHandledHonestly:
    def test_certified_is_honestly_false(self):
        # This fixture never claims a false-positive certification -- the
        # two pre-existing, unrelated findings still block it, exactly as
        # they do on the J.19 real chain.
        _, _, _, _, _, report = _run_real_chain()
        assert report.certified is False

    def test_no_blocking_findings_remain(self):
        # AES-WEB-002K.1 retires both of the two findings that were
        # "known" here (CG-CMP-005 heading hierarchy, CG-CMP-006 landmark
        # hierarchy) -- this fixture now has a real site header/footer
        # landmark and h2-level listing cards, so neither fires anymore.
        # certified still isn't True (66 gates remain deferred, unrelated),
        # but zero *blocking* findings remain for this fixture.
        _, _, _, _, _, report = _run_real_chain()
        blocking_failures = {
            g.gate_id for g in report.gate_results
            if not g.passed and g.severity == GateSeverity.BLOCKING
        }
        assert blocking_failures == set()

    def test_repetition_introduces_no_new_gate_failures(self):
        # Every gate that isn't one of the two known findings must pass --
        # repetition-specific output (N-instance category/related-listing
        # pages) must not trip any OTHER gate the single-instance J.19
        # fixture didn't already trip.
        _, _, _, _, _, report = _run_real_chain()
        for gate in report.gate_results:
            if gate.gate_id not in _KNOWN_BLOCKING_GATE_IDS:
                assert gate.passed, (gate.gate_id, gate.severity)


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
        # its module docstring), so scanning it would self-trigger on quoted
        # prose, not real usage.
        fixture_src = (
            _REPO_ROOT / "tests" / "website_generation" / "fixtures" / "listing_collection_fixture.py"
        ).read_text(encoding="utf-8")
        for banned in (
            "import socket", "import urllib", "import requests", "import uuid",
            "import random", "import datetime", "os.environ", "import webbrowser",
            "http.server", "import subprocess", "time.time", "anthropic",
        ):
            assert banned not in fixture_src, banned

    def test_j13_local_demo_fixture_untouched(self):
        # This test file must never *import* the J.13 harness/fixture module
        # -- independent proofs (hand-bound vs. really-bound). An AST import
        # check (not a substring search) avoids self-triggering on this
        # module's docstring, which names related modules for documentation.
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

    def test_pipeline_remains_unwired(self):
        from engines.website_generation.constants.build import (
            PHASE1_EXECUTED_STAGES,
            STAGE_SPEC_COMPILATION,
        )

        assert PHASE1_EXECUTED_STAGES == (STAGE_SPEC_COMPILATION,)

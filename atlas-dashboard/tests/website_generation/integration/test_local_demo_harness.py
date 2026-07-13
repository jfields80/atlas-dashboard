"""Local Demo Website Harness tests (AES-WEB-002J.13).

Exercises the Level-B harness end to end: the handcrafted, fully-bound demo
fixture driving the REAL Renderer -> Assembly -> Quality Gate ->
SiteBundleRepository, plus the CLI harness' summary/failure/determinism
behavior and its production boundary. All output goes to ``tmp_path`` -- the
suite never writes into the source tree or the default ``generated-sites/``.
"""

from __future__ import annotations

import io
import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import scripts.generate_local_demo_site as harness  # noqa: E402

from engines.website_generation.assembly.assembly_engine import AssemblyEngine  # noqa: E402
from engines.website_generation.components.registry import build_default_registry  # noqa: E402
from engines.website_generation.contracts.artifacts import (  # noqa: E402
    GateResult,
    QualityReport,
    SiteBundle,
    artifact_sha256,
)
from engines.website_generation.contracts.enums import GateSeverity  # noqa: E402
from engines.website_generation.contracts.errors import (  # noqa: E402
    GateExecutionError,
    RenderError,
)
from engines.website_generation.gates.quality_gate_engine import QualityGateEngine  # noqa: E402
from engines.website_generation.rendering.renderer import Renderer  # noqa: E402


HTML_ROUTES = (
    "index.html",
    "hotels/index.html",
    "hotels/lakeview-lodge/index.html",
    "about/index.html",
    "contact/index.html",
)
SYSTEM_FILES = ("styles.css", "sitemap.xml", "robots.txt")


@pytest.fixture(scope="module")
def demo_module():
    return harness.load_demo_fixture()


@pytest.fixture()
def demo_inputs(demo_module):
    return demo_module.build_local_demo_inputs()


# --------------------------------------------------------------------------- #
# A. Fixture integrity
# --------------------------------------------------------------------------- #

class TestFixtureIntegrity:
    def test_only_registered_component_keys(self, demo_inputs):
        registry = build_default_registry()
        registered = {d.component_id for d in registry.all_definitions()}
        for page in demo_inputs.manifest.pages:
            for inst in page.components:
                assert inst.component_id in registered, inst.component_id

    def test_every_required_prop_and_content_ref_bound(self, demo_inputs):
        registry = build_default_registry()
        block_index = {
            (b.page_route, b.slot_id) for b in demo_inputs.content.blocks
        }
        from engines.website_generation.contracts.enums import PropType

        for page in demo_inputs.manifest.pages:
            for inst in page.components:
                d = registry.get(inst.component_id)
                # every required prop present
                for prop_name in d.required_props:
                    assert prop_name in inst.props, (inst.component_id, prop_name)
                # every required content slot bound to a resolvable block
                for slot in d.required_content_slots:
                    assert slot in inst.content_refs
                    assert (page.route, slot) in block_index
                # ref-typed props resolve to a block too
                for name, spec in d.required_props.items():
                    if spec.prop_type in (PropType.CONTENT_BLOCK_REF, PropType.LISTING_REF):
                        assert (page.route, inst.props[name]) in block_index

    def test_stable_route_set(self, demo_inputs):
        assert demo_inputs.routes == (
            "/", "/hotels/", "/hotels/lakeview-lodge/", "/about/", "/contact/",
        )
        assert tuple(p.route for p in demo_inputs.manifest.pages) == demo_inputs.routes
        assert tuple(p.route for p in demo_inputs.layout.pages) == demo_inputs.routes

    def test_layout_placements_align_with_manifest(self, demo_inputs):
        for m_page, l_page in zip(demo_inputs.manifest.pages, demo_inputs.layout.pages):
            n = len(m_page.components)
            placed = [
                idx
                for region in l_page.regions
                for idx in region.component_indexes
            ]
            assert sorted(placed) == list(range(n))

    def test_no_listing_card_components_in_default_demo(self, demo_inputs):
        # The H3-emitting listing.card.* are intentionally excluded so the
        # default build stays heading-hierarchy (CG-CMP-005) clean.
        used = {
            inst.component_id
            for page in demo_inputs.manifest.pages
            for inst in page.components
        }
        assert not (used & {"listing.card.standard", "listing.card.sponsored", "listing.card.featured"})

    def test_fixture_is_deterministic(self, demo_module):
        a = demo_module.build_local_demo_inputs()
        b = demo_module.build_local_demo_inputs()
        for field in ("brand", "content", "seo", "manifest", "layout", "site_architecture"):
            assert artifact_sha256(getattr(a, field)) == artifact_sha256(getattr(b, field))


# --------------------------------------------------------------------------- #
# B. Real engine execution (no mocks replacing the four core objects)
# --------------------------------------------------------------------------- #

class TestRealEngines:
    def test_harness_binds_the_real_engine_classes(self):
        from engines.website_generation.rendering.renderer import Renderer as R
        from engines.website_generation.assembly.assembly_engine import AssemblyEngine as A
        from engines.website_generation.gates.quality_gate_engine import QualityGateEngine as Q
        from repositories.site_bundle_repository import SiteBundleRepository as S

        assert harness.Renderer is R
        assert harness.AssemblyEngine is A
        assert harness.QualityGateEngine is Q
        assert harness.SiteBundleRepository is S

    def test_render_assemble_gate_produces_real_artifacts(self, demo_module):
        bundle, report, inputs = harness.render_assemble_gate(demo_module)
        assert isinstance(bundle, SiteBundle)
        assert isinstance(report, QualityReport)
        assert bundle.files and bundle.bundle_hash


# --------------------------------------------------------------------------- #
# C. Output
# --------------------------------------------------------------------------- #

class TestOutput:
    def test_all_expected_files_written(self, tmp_path):
        dest = tmp_path / "site"
        code, result = harness.run(str(dest), stream=io.StringIO())
        assert code == 0 and result is not None
        for rel in HTML_ROUTES + SYSTEM_FILES + (harness.MANIFEST_FILENAME,):
            assert (dest / rel).is_file(), rel

    def test_root_and_nested_stylesheet_depth(self, tmp_path):
        dest = tmp_path / "site"
        harness.run(str(dest), stream=io.StringIO())
        assert 'href="styles.css"' in (dest / "index.html").read_text(encoding="utf-8")
        assert 'href="../styles.css"' in (dest / "hotels/index.html").read_text(encoding="utf-8")
        assert 'href="../../styles.css"' in (
            dest / "hotels/lakeview-lodge/index.html"
        ).read_text(encoding="utf-8")

    def test_expected_markup_present(self, tmp_path):
        dest = tmp_path / "site"
        harness.run(str(dest), stream=io.StringIO())
        home = (dest / "index.html").read_text(encoding="utf-8")
        assert "<main" in home and "<footer" in home
        assert 'aria-label="Main"' in home  # labeled nav
        assert "Find pet-friendly places to stay" in home  # hero H1
        assert "Sponsored" in home  # sponsorship label/disclosure
        contact = (dest / "contact/index.html").read_text(encoding="utf-8")
        assert "<form" in contact

    def test_no_absolute_local_path_leaks(self, tmp_path):
        dest = tmp_path / "site"
        harness.run(str(dest), stream=io.StringIO())
        needle = str(tmp_path)
        for rel in HTML_ROUTES + SYSTEM_FILES:
            assert needle not in (dest / rel).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# D. Quality reporting
# --------------------------------------------------------------------------- #

class TestQualityReporting:
    def test_gate_counts_and_certified(self, demo_module):
        _bundle, report, _inputs = harness.render_assemble_gate(demo_module)
        assert len(report.gate_results) == 8
        assert all(g.passed for g in report.gate_results)
        assert len(report.deferred_gate_ids) == 66
        assert report.certified is False
        assert report.certificate is None

    def test_summary_printed_without_certification_claim(self, tmp_path):
        dest = tmp_path / "site"
        stream = io.StringIO()
        harness.run(str(dest), stream=stream)
        text = stream.getvalue().lower()
        assert "evaluated gates : 8" in text
        assert "deferred gates  : 66" in text
        assert "certified       : false" in text
        for banned in ("certified website", "production ready", "deployment ready",
                       "end-to-end success", "business brief"):
            assert banned not in text

    def test_sidecar_only_with_flag(self, tmp_path):
        dest_off = tmp_path / "off"
        harness.run(str(dest_off), stream=io.StringIO())
        assert not (dest_off / harness.QUALITY_REPORT_FILENAME).exists()

        dest_on = tmp_path / "on"
        harness.run(str(dest_on), write_quality_report=True, stream=io.StringIO())
        assert (dest_on / harness.QUALITY_REPORT_FILENAME).is_file()

    def test_sidecar_is_deterministic_and_not_a_certificate(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        harness.run(str(a), write_quality_report=True, stream=io.StringIO())
        harness.run(str(b), write_quality_report=True, stream=io.StringIO())
        ab = (a / harness.QUALITY_REPORT_FILENAME).read_bytes()
        bb = (b / harness.QUALITY_REPORT_FILENAME).read_bytes()
        assert ab == bb
        assert ab.endswith(b"\n") and b"\r\n" not in ab
        # It is a report, not a certificate: certification is explicitly withheld
        # (the QualityReport carries a null certificate field and certified=false).
        assert b'"certified": false' in ab
        assert b'"certificate": null' in ab

    def test_sidecar_not_in_bundle_manifest(self, tmp_path):
        dest = tmp_path / "site"
        harness.run(str(dest), write_quality_report=True, stream=io.StringIO())
        manifest = (dest / harness.MANIFEST_FILENAME).read_text(encoding="utf-8")
        assert harness.QUALITY_REPORT_FILENAME not in manifest


# --------------------------------------------------------------------------- #
# E. Failure behavior
# --------------------------------------------------------------------------- #

class TestFailureBehavior:
    def test_non_empty_destination_rejected(self, tmp_path):
        dest = tmp_path / "site"
        dest.mkdir()
        (dest / "preexisting.txt").write_text("keep me")
        code, result = harness.run(str(dest), stream=io.StringIO())
        assert code == 1 and result is None
        assert (dest / "preexisting.txt").read_text() == "keep me"
        assert not (dest / "index.html").exists()

    def test_renderer_malfunction_exits_nonzero(self, tmp_path, monkeypatch):
        def _boom(self, *a, **k):
            raise RenderError("simulated render malfunction")

        monkeypatch.setattr(Renderer, "render", _boom)
        dest = tmp_path / "site"
        code, result = harness.run(str(dest), stream=io.StringIO())
        assert code == 1 and result is None
        assert not dest.exists()

    def test_gate_execution_error_exits_nonzero(self, tmp_path, monkeypatch):
        def _boom(self, *a, **k):
            raise GateExecutionError("simulated gate malfunction", diagnostics={})

        monkeypatch.setattr(QualityGateEngine, "evaluate", _boom)
        dest = tmp_path / "site"
        code, result = harness.run(str(dest), stream=io.StringIO())
        assert code == 1 and result is None
        assert not dest.exists()

    def test_blocking_gate_failure_blocks_materialization(self, tmp_path, monkeypatch, demo_module):
        real_bundle, real_report, inputs = harness.render_assemble_gate(demo_module)
        failing = real_report.copy(
            update={
                "gate_results": real_report.gate_results
                + (
                    GateResult(
                        gate_id="CG-XXX-999",
                        severity=GateSeverity.BLOCKING,
                        passed=False,
                        details="injected blocking failure",
                    ),
                )
            }
        )
        monkeypatch.setattr(
            harness, "render_assemble_gate", lambda _m: (real_bundle, failing, inputs)
        )
        dest = tmp_path / "site"
        stream = io.StringIO()
        code, result = harness.run(str(dest), stream=stream)
        assert code == 1 and result is None
        assert not dest.exists()  # not materialized
        assert "REJECTED" in stream.getvalue()


# --------------------------------------------------------------------------- #
# F. Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_two_destinations_byte_identical(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        _, ra = harness.run(str(a), build_id="fixed", stream=io.StringIO())
        _, rb = harness.run(str(b), build_id="fixed", stream=io.StringIO())
        assert ra.bundle_hash == rb.bundle_hash
        for rel in HTML_ROUTES + SYSTEM_FILES + (harness.MANIFEST_FILENAME,):
            assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel

    def test_summary_stable_except_destination(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        _, ra = harness.run(str(a), stream=io.StringIO())
        _, rb = harness.run(str(b), stream=io.StringIO())
        assert ra.bundle_hash == rb.bundle_hash
        assert (ra.page_count, ra.file_count, ra.evaluated_gate_count,
                ra.deferred_gate_count, ra.certified) == (
                rb.page_count, rb.file_count, rb.evaluated_gate_count,
                rb.deferred_gate_count, rb.certified)

    def test_fixture_not_mutated_by_a_build(self, demo_module):
        inputs = demo_module.build_local_demo_inputs()
        before = artifact_sha256(inputs.manifest)
        AssemblyEngine()  # touch engines
        harness.render_assemble_gate(demo_module)
        assert artifact_sha256(demo_module.build_local_demo_inputs().manifest) == before


# --------------------------------------------------------------------------- #
# G. Production boundary
# --------------------------------------------------------------------------- #

class TestProductionBoundary:
    def _sources(self):
        harness_src = pathlib.Path(harness.__file__).read_text(encoding="utf-8")
        fixture_src = (
            _REPO_ROOT / "tests" / "website_generation" / "fixtures" / "local_demo_site.py"
        ).read_text(encoding="utf-8")
        return harness_src, fixture_src

    def test_no_forbidden_runtime_facilities(self):
        for src in self._sources():
            for banned in (
                "import socket", "import urllib", "import requests", "import uuid",
                "import random", "import datetime", "os.environ", "import webbrowser",
                "http.server", "import subprocess", "time.time", "anthropic",
            ):
                assert banned not in src, banned

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

    def test_harness_and_fixture_not_a_wge_public_export(self):
        import engines.website_generation as wge

        for name in ("build_local_demo_inputs", "LocalDemoInputs", "HarnessResult"):
            assert name not in getattr(wge, "__all__", ())

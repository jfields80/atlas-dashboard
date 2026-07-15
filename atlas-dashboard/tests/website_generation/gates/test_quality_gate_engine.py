"""Quality Gate Engine tests (AES-WEB-002J.11; AES-WEB-001 §5.10).

Covers the §20 matrix: public interface, gate inventory, real-output
two-fixture-law evaluation per gate, pass/fail + certification semantics,
execution-error vs finding distinction, real end-to-end integration,
security, determinism, and the architectural boundary.
"""

from __future__ import annotations

import pytest

import engines.website_generation as wge
from engines.website_generation.constants.gates import COMPONENT_GATE_REGISTRATIONS
from engines.website_generation.contracts.artifacts import (
    BundleFile,
    QualityReport,
    SiteBundle,
    artifact_sha256,
    canonical_artifact_json,
    sha256_of_text,
)
from engines.website_generation.contracts.enums import ArtifactKind, GateSeverity
from engines.website_generation.contracts.errors import (
    GateExecutionError,
    WebsiteGenerationError,
)
from engines.website_generation.contracts.interfaces import QualityGateEngineInterface
from engines.website_generation.gates.quality_gate_engine import (
    QualityGateEngine,
    _ALL_REGISTERED_GATE_IDS,
    _EVALUATED_GATE_IDS,
)

from ._qge_fixtures import (
    GOOD_PAGE,
    bundle_from_html,
    content_package,
    real_bundle,
    seo_package,
    site_architecture,
)


def _report_for(html: str) -> QualityReport:
    return QualityGateEngine().evaluate(
        bundle_from_html({"index.html": html}),
        seo_package(),
        content_package(),
        site_architecture(),
    )


def _fails(report: QualityReport):
    return {g.gate_id for g in report.gate_results if not g.passed}


# --------------------------------------------------------------------------- #
# A. Public interface
# --------------------------------------------------------------------------- #

class TestPublicInterface:
    def test_engine_exported(self):
        assert "QualityGateEngine" in wge.__all__
        assert wge.QualityGateEngine is QualityGateEngine

    def test_interface_and_error_internal(self):
        for name in ("QualityGateEngineInterface", "GateExecutionError", "QualityReportV1"):
            assert name not in wge.__all__

    def test_implements_interface(self):
        assert issubclass(QualityGateEngine, QualityGateEngineInterface)
        assert isinstance(QualityGateEngine(), QualityGateEngineInterface)

    def test_engine_version_registered(self):
        # AES-WEB-002L.2 bumps 1.0.0 -> 1.1.0: evaluate() gained an optional
        # component_manifest input that moves CG-CMP-010 from deferred to
        # evaluated (contracts/versions.py).
        assert wge.ENGINE_VERSIONS["quality_gate_engine"] == "1.1.0"
        assert QualityGateEngine.version == "1.1.0"

    def test_error_shape(self):
        err = GateExecutionError("boom", diagnostics={"x": 1})
        assert isinstance(err, WebsiteGenerationError)
        assert err.stage == "gating"
        assert err.retryable is False


# --------------------------------------------------------------------------- #
# B. Gate inventory
# --------------------------------------------------------------------------- #

class TestGateInventory:
    def test_registered_gate_ids_unique(self):
        ids = [reg.gate_id for reg in COMPONENT_GATE_REGISTRATIONS]
        assert len(ids) == len(set(ids)) == 74

    def test_evaluated_set_is_eight_and_registered(self):
        assert len(_EVALUATED_GATE_IDS) == 8
        assert _EVALUATED_GATE_IDS <= set(_ALL_REGISTERED_GATE_IDS)

    def test_evaluated_plus_deferred_covers_every_registered_gate(self):
        report = _report_for(GOOD_PAGE)
        evaluated = {g.gate_id for g in report.gate_results}
        covered = evaluated | set(report.deferred_gate_ids)
        assert covered == set(_ALL_REGISTERED_GATE_IDS)
        assert len(covered) == 74

    def test_no_gate_both_evaluated_and_deferred(self):
        report = _report_for(GOOD_PAGE)
        evaluated = {g.gate_id for g in report.gate_results}
        assert not (evaluated & set(report.deferred_gate_ids))

    def test_deferred_count_is_66(self):
        report = _report_for(GOOD_PAGE)
        assert len(report.deferred_gate_ids) == 66

    def test_every_evaluated_gate_id_is_registered(self):
        registered = set(_ALL_REGISTERED_GATE_IDS)
        report = _report_for(GOOD_PAGE)
        for g in report.gate_results:
            assert g.gate_id in registered


# --------------------------------------------------------------------------- #
# C. Two-fixture law per evaluated gate (good page + single-defect page)
# --------------------------------------------------------------------------- #

class TestGoodPagePasses:
    def test_clean_page_passes_all_evaluated_gates(self):
        assert _fails(_report_for(GOOD_PAGE)) == set()


class TestEachGateFiresOnItsDefect:
    def test_cg_rnd_002_missing_doctype(self):
        assert "CG-RND-002" in _fails(_report_for(GOOD_PAGE.replace("<!doctype html>", "")))

    def test_cg_rnd_005_inline_script(self):
        fails = _fails(_report_for(GOOD_PAGE.replace("</body>", "<script>x()</script></body>")))
        assert "CG-RND-005" in fails

    def test_cg_rnd_005_inline_style(self):
        fails = _fails(_report_for(GOOD_PAGE.replace("<h1>Heading</h1>", '<h1 style="x">Heading</h1>')))
        assert "CG-RND-005" in fails

    def test_cg_rnd_006_script_breaks_no_js_baseline(self):
        fails = _fails(_report_for(GOOD_PAGE.replace("</body>", "<script>x()</script></body>")))
        assert "CG-RND-006" in fails

    def test_external_script_fires_no_js_baseline_only_not_inline_gate(self):
        # An external <script src> defeats the no-JS baseline (CG-RND-006) but
        # is not an inline script (CG-RND-005 must NOT fire on it).
        fails = _fails(_report_for(GOOD_PAGE.replace("</body>", '<script src="/a.js"></script></body>')))
        assert "CG-RND-006" in fails
        assert "CG-RND-005" not in fails

    def test_cg_rnd_008_duplicate_dom_id(self):
        html = GOOD_PAGE.replace('<main id="main">', '<main id="main"><span id="main">d</span>')
        assert "CG-RND-008" in _fails(_report_for(html))

    def test_cg_rnd_008_metadata_leak(self):
        html = GOOD_PAGE.replace("<h1>Heading</h1>", "<h1>Heading</h1><!--registry_version-->")
        assert "CG-RND-008" in _fails(_report_for(html))

    def test_cg_rnd_009_unsafe_url(self):
        html = GOOD_PAGE.replace('href="/about"', 'href="javascript:evil()"')
        assert "CG-RND-009" in _fails(_report_for(html))

    def test_cg_cmp_005_two_h1(self):
        html = GOOD_PAGE.replace("<h2>Sub</h2>", "<h1>Second</h1>")
        assert "CG-CMP-005" in _fails(_report_for(html))

    def test_cg_cmp_005_heading_skip(self):
        html = GOOD_PAGE.replace("<h2>Sub</h2>", "<h4>Skip</h4>")
        assert "CG-CMP-005" in _fails(_report_for(html))

    def test_cg_cmp_006_missing_footer(self):
        html = GOOD_PAGE.replace("<footer><p>Legal</p></footer>", "")
        assert "CG-CMP-006" in _fails(_report_for(html))

    def test_cg_cmp_006_unlabeled_second_nav(self):
        # A labeled nav plus an unlabeled second nav -> multi-nav unlabeled.
        html = GOOD_PAGE.replace(
            "<h1>Heading</h1>", '<nav><a href="/z">Z</a></nav><h1>Heading</h1>'
        )
        assert "CG-CMP-006" in _fails(_report_for(html))

    def test_cg_cmp_008_nested_interactive(self):
        html = GOOD_PAGE.replace(
            '<button type="button">Go</button>', '<button type="button"><a href="/y">Y</a></button>'
        )
        assert "CG-CMP-008" in _fails(_report_for(html))


# --------------------------------------------------------------------------- #
# D. Pass/fail + certification semantics
# --------------------------------------------------------------------------- #

class TestSemantics:
    def test_blocking_finding_does_not_certify(self):
        report = _report_for(GOOD_PAGE.replace('href="/about"', 'href="javascript:x"'))
        assert report.certified is False

    def test_never_certifies_while_blocking_gates_deferred(self):
        # Even a fully-clean page cannot be certified this sprint: blocking
        # gates remain deferred, so certification is honestly withheld.
        report = _report_for(GOOD_PAGE)
        assert _fails(report) == set()
        assert report.certified is False
        assert report.certificate is None

    def test_gate_result_carries_severity_and_details(self):
        report = _report_for(GOOD_PAGE)
        for g in report.gate_results:
            assert isinstance(g.severity, GateSeverity)
            assert g.details

    def test_failure_details_name_the_route(self):
        report = _report_for(GOOD_PAGE.replace('href="/about"', 'href="javascript:x"'))
        rnd009 = next(g for g in report.gate_results if g.gate_id == "CG-RND-009")
        assert "index.html" in rnd009.details


# --------------------------------------------------------------------------- #
# E. Execution error vs finding
# --------------------------------------------------------------------------- #

class TestExecutionErrors:
    def test_no_html_pages_raises(self):
        bundle = SiteBundle(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.SITE_BUNDLE,
            source_hashes={},
            file_map={"styles.css": sha256_of_text("x")},
            bundle_hash="h",
            files=(BundleFile(path="styles.css", content="x"),),
        )
        with pytest.raises(GateExecutionError) as exc:
            QualityGateEngine().evaluate(bundle, seo_package(), content_package(), site_architecture())
        assert "file_count" in exc.value.diagnostics

    def test_content_failure_is_never_an_exception(self):
        # A page riddled with violations returns a report (findings), not an
        # exception (§5.10).
        bad = "<html><body><script>x</script><a href='javascript:x'></a></body></html>"
        report = _report_for(bad)
        assert isinstance(report, QualityReport)
        assert _fails(report)  # some gates failed, but as findings


# --------------------------------------------------------------------------- #
# F. Real end-to-end integration
# --------------------------------------------------------------------------- #

class TestRealIntegration:
    def test_real_rendered_and_assembled_page_passes(self):
        bundle, seo, content, site = real_bundle(("/",))
        report = QualityGateEngine().evaluate(bundle, seo, content, site)
        assert _fails(report) == set()
        assert len(report.gate_results) == 8

    def test_real_multi_page_bundle_evaluated_per_page(self):
        bundle, seo, content, site = real_bundle(("/", "/hotels", "/parks"))
        report = QualityGateEngine().evaluate(bundle, seo, content, site)
        assert _fails(report) == set()
        # every gate's details reflect the 4 html pages (3 routes -> 3 index.html)
        rnd = next(g for g in report.gate_results if g.gate_id == "CG-RND-009")
        assert "3 page(s)" in rnd.details

    def test_source_hashes_complete(self):
        bundle, seo, content, site = real_bundle(("/",))
        report = QualityGateEngine().evaluate(bundle, seo, content, site)
        assert report.source_hashes == {
            "site_bundle": artifact_sha256(bundle),
            "seo_package": artifact_sha256(seo),
            "content_package": artifact_sha256(content),
            "site_architecture": artifact_sha256(site),
        }


# --------------------------------------------------------------------------- #
# G. Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_equal_reports_json_and_hash(self):
        bundle, seo, content, site = real_bundle(("/", "/hotels"))
        a = QualityGateEngine().evaluate(bundle, seo, content, site)
        b = QualityGateEngine().evaluate(bundle, seo, content, site)
        assert a == b
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_gate_result_order_is_stable(self):
        report = _report_for(GOOD_PAGE)
        ids = [g.gate_id for g in report.gate_results]
        assert ids == sorted(ids)  # declared (lexicographic) order

    def test_deferred_ids_sorted_and_stable(self):
        a = _report_for(GOOD_PAGE).deferred_gate_ids
        b = _report_for(GOOD_PAGE).deferred_gate_ids
        assert a == b
        assert list(a) == sorted(a)

    def test_report_frozen(self):
        report = _report_for(GOOD_PAGE)
        with pytest.raises(Exception):
            report.certified = True


# --------------------------------------------------------------------------- #
# H. Security
# --------------------------------------------------------------------------- #

class TestSecurity:
    def test_script_injection_detected(self):
        assert "CG-RND-005" in _fails(_report_for(GOOD_PAGE.replace("</main>", "<script>x</script></main>")))

    def test_event_handler_via_unsafe_is_not_missed_by_url_gate(self):
        # An href with javascript: is caught by CG-RND-009.
        assert "CG-RND-009" in _fails(_report_for(GOOD_PAGE.replace('href="/about"', 'href="javascript:go()"')))

    def test_protocol_relative_url_flagged(self):
        assert "CG-RND-009" in _fails(_report_for(GOOD_PAGE.replace('href="/about"', 'href="//evil.example/x"')))

    def test_selection_trace_leak_detected(self):
        html = GOOD_PAGE.replace("<h1>Heading</h1>", '<h1 data-x="selection_trace">Heading</h1>')
        assert "CG-RND-008" in _fails(_report_for(html))

    def test_engine_does_not_mutate_inputs(self):
        bundle, seo, content, site = real_bundle(("/",))
        before = (artifact_sha256(bundle), artifact_sha256(seo), artifact_sha256(content), artifact_sha256(site))
        QualityGateEngine().evaluate(bundle, seo, content, site)
        after = (artifact_sha256(bundle), artifact_sha256(seo), artifact_sha256(content), artifact_sha256(site))
        assert before == after

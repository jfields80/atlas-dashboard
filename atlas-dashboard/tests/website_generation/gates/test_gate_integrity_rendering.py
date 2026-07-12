"""Two-fixture law tests for CG-RND (AES-WEB-002 §21.3; 10 gates).

Every gate in this family operates on a synthetic
:class:`SyntheticRenderedPage` stand-in (AMB-002I-01/03) — no real
Renderer exists in this repository.
"""

from __future__ import annotations

from engines.website_generation.gates.checks import rendering_checks

from tests.website_generation.gates.test_gate_integrity import (
    assert_two_fixture_law,
    rendered_page,
)

TESTED_GATE_IDS = frozenset(rendering_checks.CHECKS)


class TestCGRnd001DoubleRenderHash:
    def test_two_fixture_law(self):
        good = rendered_page(render_hash_a="abc123", render_hash_b="abc123")
        bad = rendered_page(render_hash_a="abc123", render_hash_b="def456")
        assert_two_fixture_law(rendering_checks.check_cg_rnd_001, good, bad)


class TestCGRnd002ValidHtml:
    def test_two_fixture_law(self):
        good = rendered_page(html_conformant=True, conformance_errors=())
        bad = rendered_page(html_conformant=False, conformance_errors=("unclosed <div>",))
        assert_two_fixture_law(rendering_checks.check_cg_rnd_002, good, bad)


class TestCGRnd003EscapedContent:
    def test_two_fixture_law(self):
        good = rendered_page(escaped_probe_leaks=())
        bad = rendered_page(escaped_probe_leaks=("<script>probe</script>",))
        assert_two_fixture_law(rendering_checks.check_cg_rnd_003, good, bad)


class TestCGRnd004StableAttributesAndClasses:
    def test_two_fixture_law(self):
        good = rendered_page(attribute_order_stable=True, class_names_stable=True)
        bad = rendered_page(attribute_order_stable=False, class_names_stable=True)
        assert_two_fixture_law(rendering_checks.check_cg_rnd_004, good, bad)


class TestCGRnd005NoInlineScriptsOrStyles:
    def test_two_fixture_law(self):
        good = rendered_page(inline_script_count=0, unapproved_inline_style_count=0)
        bad = rendered_page(inline_script_count=1, unapproved_inline_style_count=0)
        assert_two_fixture_law(rendering_checks.check_cg_rnd_005, good, bad)


class TestCGRnd006NoJsBaseline:
    def test_two_fixture_law(self):
        good = rendered_page(no_js_baseline_present=True)
        bad = rendered_page(no_js_baseline_present=False)
        assert_two_fixture_law(rendering_checks.check_cg_rnd_006, good, bad)


class TestCGRnd007NoExternalRequests:
    def test_two_fixture_law(self):
        good = rendered_page(external_request_hosts=(), unresolved_asset_refs=())
        bad = rendered_page(external_request_hosts=("cdn.example.com",), unresolved_asset_refs=())
        assert_two_fixture_law(rendering_checks.check_cg_rnd_007, good, bad)

    def test_unresolved_asset_ref_fails(self):
        bad = rendered_page(unresolved_asset_refs=("asset://missing",))
        assert rendering_checks.check_cg_rnd_007(bad).passed is False


class TestCGRnd008NoDuplicateIdsOrMetadata:
    def test_two_fixture_law(self):
        good = rendered_page(dom_ids=("a", "b", "c"), internal_metadata_markers=())
        bad = rendered_page(dom_ids=("a", "b", "b"), internal_metadata_markers=())
        assert_two_fixture_law(rendering_checks.check_cg_rnd_008, good, bad)

    def test_internal_metadata_marker_fails(self):
        bad = rendered_page(dom_ids=("a",), internal_metadata_markers=("selection_trace",))
        assert rendering_checks.check_cg_rnd_008(bad).passed is False


class TestCGRnd009NoUnsafeUrls:
    def test_two_fixture_law(self):
        good = rendered_page(unsafe_urls=())
        bad = rendered_page(unsafe_urls=("javascript:alert(1)",))
        assert_two_fixture_law(rendering_checks.check_cg_rnd_009, good, bad)


class TestCGRnd010StructuredDataWellFormed:
    def test_two_fixture_law(self):
        good = rendered_page(structured_data_fragments_well_formed=True)
        bad = rendered_page(structured_data_fragments_well_formed=False)
        assert_two_fixture_law(rendering_checks.check_cg_rnd_010, good, bad)

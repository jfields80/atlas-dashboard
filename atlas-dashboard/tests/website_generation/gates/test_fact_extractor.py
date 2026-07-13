"""Fact-extraction tests for the Quality Gate Engine (AES-WEB-002J.11).

Verifies the deterministic static HTML analysis in
``gates/fact_extractor.py`` derives exactly the gate-read facts a real
``SiteBundle`` document supplies -- dom ids, heading sequence, landmarks,
unlabeled navs, inline scripts/styles, unsafe URLs, nested interactive
controls, internal-metadata markers, structural conformance -- and nothing
it cannot honestly derive.
"""

from __future__ import annotations

from engines.website_generation.gates.fact_extractor import (
    extract_page_composition_facts,
    extract_rendered_page_facts,
    _is_safe_url,
)

_DOC = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    "<title>T</title></head>"
    '<body><header><nav aria-label="Main"><a href="/a">A</a></nav></header>'
    '<main id="main"><h1>H</h1><h2>S</h2><button type="button">B</button></main>'
    "<footer><p>f</p></footer></body></html>"
)


class TestRenderedFacts:
    def test_clean_document_is_conformant(self):
        f = extract_rendered_page_facts("index.html", _DOC)
        assert f.html_conformant is True
        assert f.conformance_errors == ()

    def test_dom_ids_collected(self):
        f = extract_rendered_page_facts(
            "index.html", _DOC.replace('<main id="main">', '<main id="main"><span id="x">')
        )
        assert "main" in f.dom_ids
        assert "x" in f.dom_ids

    def test_duplicate_dom_ids_visible(self):
        html = _DOC.replace('<main id="main">', '<main id="main"><span id="main">d</span>')
        f = extract_rendered_page_facts("index.html", html)
        assert f.dom_ids.count("main") == 2

    def test_inline_script_counted(self):
        f = extract_rendered_page_facts("index.html", _DOC.replace("</body>", "<script>x()</script></body>"))
        assert f.inline_script_count == 1
        assert f.no_js_baseline_present is False

    def test_no_js_baseline_when_no_scripts(self):
        f = extract_rendered_page_facts("index.html", _DOC)
        assert f.inline_script_count == 0
        assert f.no_js_baseline_present is True

    def test_external_script_is_not_inline_but_breaks_no_js_baseline(self):
        # An external <script src> is not an *inline* script (CG-RND-005), yet
        # it does defeat the no-JS baseline (CG-RND-006). Attribution must be
        # honest: inline_script_count stays 0; no_js_baseline_present is False.
        html = _DOC.replace("</body>", '<script src="/app.js"></script></body>')
        f = extract_rendered_page_facts("index.html", html)
        assert f.inline_script_count == 0
        assert f.no_js_baseline_present is False

    def test_inline_style_attribute_counted(self):
        f = extract_rendered_page_facts("index.html", _DOC.replace("<h1>H</h1>", '<h1 style="x">H</h1>'))
        assert f.unapproved_inline_style_count == 1

    def test_style_tag_counted(self):
        f = extract_rendered_page_facts("index.html", _DOC.replace("</head>", "<style>.x{}</style></head>"))
        assert f.unapproved_inline_style_count == 1

    def test_unsafe_urls_detected(self):
        html = _DOC.replace('href="/a"', 'href="javascript:evil()"')
        f = extract_rendered_page_facts("index.html", html)
        assert "javascript:evil()" in f.unsafe_urls

    def test_safe_urls_not_flagged(self):
        f = extract_rendered_page_facts("index.html", _DOC)
        assert f.unsafe_urls == ()

    def test_internal_metadata_markers_detected(self):
        html = _DOC.replace("<h1>H</h1>", "<h1>H</h1><!--selection_trace-->")
        f = extract_rendered_page_facts("index.html", html)
        assert "selection_trace" in f.internal_metadata_markers

    def test_missing_doctype_is_nonconformant(self):
        f = extract_rendered_page_facts("index.html", _DOC.replace("<!doctype html>", ""))
        assert f.html_conformant is False
        assert any("doctype" in e for e in f.conformance_errors)

    def test_duplicate_body_is_nonconformant(self):
        f = extract_rendered_page_facts("index.html", _DOC.replace("</body>", "</body><body>x</body>"))
        assert f.html_conformant is False


class TestCompositionFacts:
    def test_heading_sequence_in_order(self):
        f = extract_page_composition_facts("index.html", _DOC)
        assert f.heading_sequence == (1, 2)

    def test_landmark_roles_from_tags(self):
        f = extract_page_composition_facts("index.html", _DOC)
        assert f.landmark_roles.count("header") == 1
        assert f.landmark_roles.count("main") == 1
        assert f.landmark_roles.count("footer") == 1
        assert f.landmark_roles.count("nav") == 1

    def test_landmark_roles_from_aria_role(self):
        html = _DOC.replace("<header>", '<div role="banner">').replace("</header>", "</div>")
        f = extract_page_composition_facts("index.html", html)
        assert f.landmark_roles.count("header") == 1

    def test_labeled_nav_not_counted_unlabeled(self):
        f = extract_page_composition_facts("index.html", _DOC)
        assert f.unlabeled_nav_count == 0

    def test_unlabeled_nav_counted(self):
        html = _DOC.replace('<nav aria-label="Main">', "<nav>")
        f = extract_page_composition_facts("index.html", html)
        assert f.unlabeled_nav_count == 1

    def test_nested_interactive_detected(self):
        html = _DOC.replace('<button type="button">B</button>', '<button type="button"><a href="/y">Y</a></button>')
        f = extract_page_composition_facts("index.html", html)
        assert "a" in f.nested_interactive_controls

    def test_input_in_label_not_nested(self):
        # An <input> inside a <label> is correct markup, not a nested control.
        html = _DOC.replace(
            '<button type="button">B</button>', "<label>Name<input type=\"text\"></label>"
        )
        f = extract_page_composition_facts("index.html", html)
        assert f.nested_interactive_controls == ()


class TestSafeUrlPrimitive:
    def test_safe_and_unsafe(self):
        assert _is_safe_url("/ok") is True
        assert _is_safe_url("#frag") is True
        assert _is_safe_url("https://x.example") is True
        assert _is_safe_url("mailto:a@b.com") is True
        assert _is_safe_url("javascript:x") is False
        assert _is_safe_url("data:text/html,x") is False
        assert _is_safe_url("//host/path") is False


class TestDeterminism:
    def test_extraction_is_deterministic(self):
        a = extract_rendered_page_facts("index.html", _DOC)
        b = extract_rendered_page_facts("index.html", _DOC)
        assert a == b
        c = extract_page_composition_facts("index.html", _DOC)
        d = extract_page_composition_facts("index.html", _DOC)
        assert c == d

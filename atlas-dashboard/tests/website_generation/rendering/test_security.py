"""Security tests (AES-WEB-002J.8; AES-WEB-001 §5.7, CG-RND-003/005/007/008/009).

Covers: script/HTML injection escaped, attribute-quote injection escaped,
unsafe URL schemes rejected (javascript:/data:/vbscript:/protocol-relative),
event-handler-attribute injection impossible, inline script/style
prohibition, no duplicate DOM ids, no internal-metadata leakage, and the
documented single-canonical-escape boundary rule (no double-visible-
escaping, no under-escaping) with the exact fixture set the operator
specified: raw ``<script>`` text, raw ampersand, raw quotes in attributes,
already-represented ``&amp;``, already-represented ``&lt;``, and mixed
hostile text with entities.
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.artifacts import ComponentInstance, ContentBlock
from engines.website_generation.contracts.errors import RenderError
from engines.website_generation.rendering.html_emitter import escape, is_safe_url

from . import real_brand_package, real_registry, render_page, render_single_component


class TestEscapingBoundaryRule:
    """The exact fixture matrix the operator required for the documented
    single-canonical-escape boundary decision."""

    def test_raw_script_tag_text_is_escaped(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            content_overrides={"label": "<script>alert(1)</script>"},
        )
        html = result.page_details[0].html
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    def test_raw_ampersand_is_escaped(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            content_overrides={"label": "Books & Travel"},
        )
        html = result.page_details[0].html
        assert "Books & Travel" not in html
        assert "Books &amp; Travel" in html

    def test_raw_quotes_in_attribute_context_are_escaped(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.field.text",
            content_overrides={"label": 'Say "hello"'},
        )
        html = result.page_details[0].html
        assert '"hello"' not in html.split(">", 1)[-1] or "&quot;hello&quot;" in html
        assert "&quot;hello&quot;" in html

    def test_already_represented_amp_entity_is_escaped_once_more(self):
        # Content arrives raw from ContentBlock.text (documented boundary
        # decision) -- a literal "&amp;" in the raw text is ordinary text
        # characters (an ampersand followed by "amp;"), not markup, and is
        # escaped exactly like any other "&": once, faithfully.
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            content_overrides={"label": "Terms &amp; Conditions"},
        )
        html = result.page_details[0].html
        assert "Terms &amp;amp; Conditions" in html

    def test_already_represented_lt_entity_is_escaped_once_more(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            content_overrides={"label": "5 &lt; 10"},
        )
        html = result.page_details[0].html
        assert "5 &amp;lt; 10" in html

    def test_mixed_hostile_text_and_entities(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            content_overrides={"label": '<b>Bold</b> & "quoted" &amp; done'},
        )
        html = result.page_details[0].html
        assert "<b>Bold</b>" not in html
        assert (
            "&lt;b&gt;Bold&lt;/b&gt; &amp; &quot;quoted&quot; &amp;amp; done" in html
        )

    def test_escape_function_is_idempotent_safe_not_decoding(self):
        # escape() never decodes existing entities first -- verified
        # directly against the primitive, independent of any emitter.
        assert escape("&amp;") == "&amp;amp;"
        assert escape("<script>") == "&lt;script&gt;"
        assert escape('"quoted"') == "&quot;quoted&quot;"
        assert escape("it's") == "it&#x27;s"

    def test_no_double_visible_escaping_for_plain_text(self):
        # Plain, non-entity text must render exactly once-escaped -- never
        # doubled -- so ordinary marketing copy displays correctly.
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            content_overrides={"label": "Book your trip today"},
        )
        assert "Book your trip today" in result.page_details[0].html

    def test_no_under_escaping_html_is_never_passed_through_raw(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            content_overrides={"label": "<img src=x onerror=alert(1)>"},
        )
        html = result.page_details[0].html
        assert "<img src=x onerror=alert(1)>" not in html
        assert "&lt;img src=x onerror=alert(1)&gt;" in html


class TestUnsafeUrlRejection:
    @pytest.mark.parametrize(
        "scheme_url",
        [
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "vbscript:msgbox(1)",
            "//evil.example.com/phish",
        ],
    )
    def test_unsafe_scheme_rejected(self, scheme_url):
        registry = real_registry()
        brand = real_brand_package()
        instance = ComponentInstance(
            component_id="atom.link.standard",
            component_version="1.0.0",
            props={"link": "linkref"},
        )
        with pytest.raises(RenderError) as exc_info:
            render_page(
                registry, brand, "/", (instance,),
                (ContentBlock(page_route="/", slot_id="linkref", text=scheme_url),),
            )
        assert "unsafe_urls" in exc_info.value.diagnostics

    @pytest.mark.parametrize(
        "safe_url",
        ["/relative/path", "#fragment", "https://example.com/x", "mailto:a@b.com", "tel:+15551234567"],
    )
    def test_safe_url_accepted(self, safe_url):
        registry = real_registry()
        brand = real_brand_package()
        instance = ComponentInstance(
            component_id="atom.link.standard",
            component_version="1.0.0",
            props={"link": "linkref"},
        )
        result = render_page(
            registry, brand, "/", (instance,),
            (ContentBlock(page_route="/", slot_id="linkref", text=safe_url),),
        )
        assert 'href="%s"' % safe_url in result.page_details[0].html

    def test_is_safe_url_primitive_directly(self):
        assert is_safe_url("javascript:alert(1)") is False
        assert is_safe_url("data:text/html,x") is False
        assert is_safe_url("//host/path") is False
        assert is_safe_url("") is False
        assert is_safe_url("/ok") is True
        assert is_safe_url("https://ok.example") is True


class TestEventHandlerInjectionImpossible:
    def test_no_emitter_ever_produces_an_on_attribute(self):
        # Structural guarantee: no emitter in this delivery ever constructs
        # an "on*" attribute name -- verified by scanning every rendered
        # output across all 32 components for the on-handler pattern.
        from . import J8_COMPONENT_IDS

        registry = real_registry()
        brand = real_brand_package()
        for component_id in J8_COMPONENT_IDS:
            result = render_single_component(registry, brand, component_id)
            html = result.page_details[0].html
            assert not __import__("re").search(r'\son[a-z]+="', html), component_id


class TestNoDuplicateDomIds:
    def test_two_field_instances_on_one_page_get_distinct_ids(self):
        registry = real_registry()
        brand = real_brand_package()
        instances = (
            ComponentInstance(
                component_id="atom.field.text", component_version="1.0.0",
                props={"input_kind": "email", "autocomplete": "email", "required": "false"},
                content_refs=("label", "error"),
            ),
            ComponentInstance(
                component_id="atom.field.text", component_version="1.0.0",
                props={"input_kind": "tel", "autocomplete": "tel", "required": "false"},
                content_refs=("label", "error"),
            ),
        )
        blocks = (
            ContentBlock(page_route="/", slot_id="label", text="Email"),
            ContentBlock(page_route="/", slot_id="error", text="Required"),
        )
        result = render_page(registry, brand, "/", instances, blocks)
        html = result.page_details[0].html
        ids = __import__("re").findall(r'id="([^"]*)"', html)
        assert len(ids) == len(set(ids)), ids


class TestNoInternalMetadataLeakage:
    def test_no_analytics_payload_fields_leak_as_attributes(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "atom.button.action")
        html = result.page_details[0].html
        assert "registry_version" not in html
        assert "build_id" not in html
        assert "page_role" not in html

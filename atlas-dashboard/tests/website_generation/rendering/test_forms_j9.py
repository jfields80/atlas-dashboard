"""Form-behavior tests for the five J.9 ``form.*`` emitters (AES-WEB-002J.9;
AES-WEB-002 §5.13, §16.5, §17.2, CG-A11Y-012, D-5 no-JS).

Covers: native ``<form method="post">``, contract-grounded safe action URL,
submit button type, no-JS operability (zero scripts), mandatory disclosure
where the contract requires it, missing required action/content diagnostics,
and the "no fabricated endpoint" guarantee.
"""

from __future__ import annotations

import re

import pytest

from engines.website_generation.contracts.artifacts import ComponentInstance, ContentBlock
from engines.website_generation.contracts.errors import RenderError

from . import (
    minimal_fixture_for,
    real_brand_package,
    real_registry,
    render_page,
    render_single_component,
)

_FORM_IDS = (
    "form.lead.quote",
    "form.claim.standard",
    "form.submission.listing",
    "form.correction.standard",
    "form.capture.newsletter",
)


def _region_for(registry, component_id):
    return registry.get(component_id).allowed_parent_regions[0]


class TestFormShell:
    @pytest.mark.parametrize("component_id", _FORM_IDS)
    def test_is_native_post_form(self, component_id):
        html = render_single_component(
            real_registry(), real_brand_package(), component_id, include_optional=True
        ).page_details[0].html
        assert "<form " in html
        assert 'method="post"' in html

    @pytest.mark.parametrize("component_id", _FORM_IDS)
    def test_has_submit_button(self, component_id):
        html = render_single_component(
            real_registry(), real_brand_package(), component_id, include_optional=True
        ).page_details[0].html
        assert '<button type="submit">Submit</button>' in html

    @pytest.mark.parametrize("component_id", _FORM_IDS)
    def test_action_is_the_bound_route(self, component_id):
        registry = real_registry()
        html = render_single_component(
            registry,
            real_brand_package(),
            component_id,
            prop_overrides={"action_route": "/submit-here"},
            include_optional=True,
        ).page_details[0].html
        assert 'action="/submit-here"' in html

    @pytest.mark.parametrize("component_id", _FORM_IDS)
    def test_no_javascript_dependency(self, component_id):
        html = render_single_component(
            real_registry(), real_brand_package(), component_id, include_optional=True
        ).page_details[0].html
        assert "<script" not in html
        assert not re.search(r"\son[a-z]+=", html)
        assert not re.search(r"\.js[\"'\s>]", html)


class TestFormSafety:
    @pytest.mark.parametrize("component_id", _FORM_IDS)
    def test_unsafe_action_rejected(self, component_id):
        registry = real_registry()
        definition = registry.get(component_id)
        instance, blocks = minimal_fixture_for(
            definition,
            "/",
            prop_overrides={"action_route": "javascript:alert(1)"},
            include_optional=True,
        )
        with pytest.raises(RenderError) as exc_info:
            render_page(
                registry,
                real_brand_package(),
                "/",
                (instance,),
                blocks,
                _region_for(registry, component_id),
            )
        assert "unsafe_urls" in exc_info.value.diagnostics

    def test_missing_action_route_is_a_diagnostic_not_a_fabricated_endpoint(self):
        # form.lead.quote requires action_route; omitting it must fail
        # deterministically rather than emit a form with an invented action.
        registry = real_registry()
        instance = ComponentInstance(
            component_id="form.lead.quote",
            component_version="1.0.0",
            content_refs=("disclosure",),
        )
        blocks = (ContentBlock(page_route="/", slot_id="disclosure", text="D"),)
        with pytest.raises(RenderError) as exc_info:
            render_page(
                registry, real_brand_package(), "/", (instance,), blocks,
                _region_for(registry, "form.lead.quote"),
            )
        assert "missing_required_props" in exc_info.value.diagnostics


class TestFormContractContent:
    def test_lead_quote_requires_disclosure(self):
        registry = real_registry()
        instance = ComponentInstance(
            component_id="form.lead.quote",
            component_version="1.0.0",
            props={"action_route": "/x"},
        )
        with pytest.raises(RenderError) as exc_info:
            render_page(
                registry, real_brand_package(), "/", (instance,), (),
                _region_for(registry, "form.lead.quote"),
            )
        assert "missing_required_content" in exc_info.value.diagnostics

    def test_lead_quote_disclosure_is_visible(self):
        html = render_single_component(
            real_registry(),
            real_brand_package(),
            "form.lead.quote",
            content_overrides={"disclosure": "Your request is sent to providers"},
        ).page_details[0].html
        assert "Your request is sent to providers" in html
        assert "ac-form--disclosure" in html

    def test_submission_listing_renders_standards_link(self):
        html = render_single_component(
            real_registry(),
            real_brand_package(),
            "form.submission.listing",
            prop_overrides={"action_route": "/submit"},
            content_overrides={"standards_link": "/editorial-standards"},
        ).page_details[0].html
        assert '<a href="/editorial-standards">/editorial-standards</a>' in html

    def test_newsletter_renders_prompt_label(self):
        html = render_single_component(
            real_registry(),
            real_brand_package(),
            "form.capture.newsletter",
            prop_overrides={"action_route": "/subscribe"},
            content_overrides={"label": "Get our newsletter"},
        ).page_details[0].html
        assert "Get our newsletter" in html

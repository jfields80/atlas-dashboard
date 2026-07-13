"""Security tests across all 40 J.9 components (AES-WEB-002J.9;
CG-RND-003/005/007/008/009, prompt §19.F).

Covers: hostile content in every text surface (legal, reviews, business
description, table cells, disclosures) is escaped; unsafe URLs (form action,
CTA target, listing/recovery links) are rejected; no emitter produces an
event-handler or inline-style attribute; no duplicate DOM ids; no internal
metadata / selection_trace / registry-build id leakage.
"""

from __future__ import annotations

import re

import pytest

from engines.website_generation.contracts.artifacts import ComponentInstance, ContentBlock
from engines.website_generation.contracts.errors import RenderError

from . import (
    J9_COMPONENT_IDS,
    minimal_fixture_for,
    real_brand_package,
    real_registry,
    render_page,
    render_single_component,
)

_HOSTILE = '<script>alert(1)</script> & "x" <img src=y onerror=z>'


class TestHostileContentEscaped:
    @pytest.mark.parametrize(
        "component_id,slot",
        [
            ("legal.statement.standard", "body"),
            ("trust.reviews.list", "reviews"),
            ("content.description.business", "description"),
            ("content.table.comparison", "table"),
            ("monetization.disclosure.advertising", "disclosure"),
            ("trust.statistics.strip", "statistics"),
            ("content.section.editorial", "body"),
            ("status.listing.pending", "message"),
        ],
    )
    def test_hostile_text_never_leaks_raw(self, component_id, slot):
        registry = real_registry()
        overrides = {slot: _HOSTILE}
        # components with extra required content need those filled too
        html = render_single_component(
            registry,
            real_brand_package(),
            component_id,
            content_overrides={
                slot: _HOSTILE,
                "expectation_text": _HOSTILE,
                "disclaimer": _HOSTILE,
            },
            include_optional=False,
            prop_overrides=_prop_defaults(registry, component_id),
        ).page_details[0].html
        assert "<script>alert(1)</script>" not in html
        assert "onerror=z>" not in html
        assert "&lt;script&gt;" in html


def _prop_defaults(registry, component_id):
    # density/reason/kind enums need a concrete value; pull the first.
    from engines.website_generation.contracts.enums import PropType

    out = {}
    for name, spec in registry.get(component_id).required_props.items():
        if spec.prop_type is PropType.STR_ENUM and spec.enum_values:
            out[name] = spec.enum_values[0]
    return out


class TestUnsafeUrlRejection:
    @pytest.mark.parametrize(
        "component_id,url_prop",
        [
            ("cta.claim.listing", "target_route"),
            ("cta.submit.listing", "target_route"),
            ("cta.sponsor.inquiry", "target_route"),
            ("cta.sticky.mobile", "target_route"),
            ("form.lead.quote", "action_route"),
        ],
    )
    def test_unsafe_url_prop_rejected(self, component_id, url_prop):
        registry = real_registry()
        definition = registry.get(component_id)
        instance, blocks = minimal_fixture_for(
            definition, "/", prop_overrides={url_prop: "javascript:alert(1)"}
        )
        with pytest.raises(RenderError) as exc_info:
            render_page(
                registry, real_brand_package(), "/", (instance,), blocks,
                definition.allowed_parent_regions[0],
            )
        assert "unsafe_urls" in exc_info.value.diagnostics

    def test_unsafe_recovery_link_rejected(self):
        registry = real_registry()
        instance = ComponentInstance(
            component_id="status.listing.unavailable",
            component_version="1.0.0",
            props={"reason": "closed"},
            content_refs=("message", "recovery_links"),
        )
        blocks = (
            ContentBlock(page_route="/", slot_id="message", text="Closed"),
            ContentBlock(page_route="/", slot_id="recovery_links", text="data:text/html,x"),
        )
        with pytest.raises(RenderError) as exc_info:
            render_page(
                registry, real_brand_package(), "/", (instance,), blocks,
                registry.get("status.listing.unavailable").allowed_parent_regions[0],
            )
        assert "unsafe_urls" in exc_info.value.diagnostics


class TestNoInjectionSurfaces:
    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_no_event_handler_attribute(self, component_id):
        html = render_single_component(
            real_registry(), real_brand_package(), component_id, include_optional=True
        ).page_details[0].html
        assert not re.search(r'\son[a-z]+="', html), component_id

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_no_inline_style_attribute(self, component_id):
        html = render_single_component(
            real_registry(), real_brand_package(), component_id, include_optional=True
        ).page_details[0].html
        assert " style=" not in html, component_id

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_no_metadata_leakage(self, component_id):
        html = render_single_component(
            real_registry(), real_brand_package(), component_id, include_optional=True
        ).page_details[0].html
        for marker in ("selection_trace", "registry_version", "build_id"):
            assert marker not in html, (component_id, marker)


class TestNoDuplicateDomIds:
    def test_two_forms_on_one_page_produce_no_duplicate_ids(self):
        # Forms carry no author-supplied ids in J.9, but two instances on one
        # page must still pass the duplicate-id scan (CG-RND-008).
        registry = real_registry()
        brand = real_brand_package()
        insts = []
        blocks = []
        for i in range(2):
            inst = ComponentInstance(
                component_id="form.correction.standard",
                component_version="1.0.0",
                props={"action_route": "/c", "listing_ref": "L%d" % i},
                content_refs=(),
            )
            insts.append(inst)
            blocks.append(ContentBlock(page_route="/", slot_id="L%d" % i, text="x"))
        # bind the listing_ref content each instance points at
        result = render_page(registry, brand, "/", insts, blocks,
                             registry.get("form.correction.standard").allowed_parent_regions[0])
        html = result.page_details[0].html
        ids = re.findall(r'id="([^"]*)"', html)
        assert len(ids) == len(set(ids))

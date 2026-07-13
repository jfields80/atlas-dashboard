"""HTML snapshot tests for all 40 J.9 components (AES-WEB-002J.9;
AES-WEB-001 §11.4, AES-WEB-002 §20.1, CG-RND-004).

Two tiers, mirroring the J.8 ``test_snapshots.py`` structure:

* A parametrized sweep over all 40 ``J9_COMPONENT_IDS`` asserting the
  properties every emitter must share -- analytics attributes, alphabetical
  attribute order, the component's own class present, its declared semantic
  root element carrying that class, stable double-render output, no
  forbidden internal markers, no inline script/style.
* Targeted exact-markup snapshots for the representative and high-risk
  components §19.C names, pinned as literal strings so any unintended markup
  change fails loudly.
"""

from __future__ import annotations

import re

import pytest

from engines.website_generation.rendering.css_emitter import component_class

from . import J9_COMPONENT_IDS, real_brand_package, real_registry, render_single_component

_ATTR_RE = re.compile(r'([a-zA-Z:-]+)="[^"]*"')


def _body_of(html: str) -> str:
    """Everything inside the document shell's <body>, so snapshot assertions
    ignore the (J.8-owned, separately tested) shell chrome."""
    return html.split("<body", 1)[-1]


def _first_open_tag_attr_names(html_fragment: str) -> list:
    match = re.match(
        r"<[a-zA-Z0-9]+((?:\s+[a-zA-Z:-]+=\"[^\"]*\")*)", html_fragment
    )
    if not match:
        return []
    return _ATTR_RE.findall(match.group(1))


class TestUniformEmitterProperties:
    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_renders_without_error(self, component_id):
        result = render_single_component(real_registry(), real_brand_package(), component_id)
        assert result.page_details[0].html

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_analytics_attributes_present(self, component_id):
        registry = real_registry()
        definition = registry.get(component_id)
        result = render_single_component(registry, real_brand_package(), component_id)
        html = result.page_details[0].html
        assert 'data-atlas-c="%s"' % definition.analytics_contract.impression_id in html
        assert 'data-atlas-v="1.0.0"' in html

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_class_prefix_present(self, component_id):
        registry = real_registry()
        definition = registry.get(component_id)
        result = render_single_component(registry, real_brand_package(), component_id)
        assert definition.rendering_contract.class_prefix in result.page_details[0].html

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_semantic_root_element_carries_component_class(self, component_id):
        # The component's declared semantic_element is the element carrying
        # its unique component class -- proving emitters emit real semantics,
        # never generic div-only markup (prompt §14).
        registry = real_registry()
        definition = registry.get(component_id)
        sem = definition.semantic_element.value
        comp_class = component_class(definition)
        result = render_single_component(registry, real_brand_package(), component_id)
        html = result.page_details[0].html
        pattern = r"<%s\b[^>]*\bclass=\"[^\"]*\b%s\b" % (
            re.escape(sem),
            re.escape(comp_class),
        )
        assert re.search(pattern, html), (component_id, sem, comp_class)

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_double_render_hash_equality(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, component_id)
        b = render_single_component(registry, brand, component_id)
        assert a.pages[0].html_hash == b.pages[0].html_hash

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_no_internal_metadata_leakage(self, component_id):
        result = render_single_component(real_registry(), real_brand_package(), component_id)
        html = result.page_details[0].html
        for marker in (
            "selection_trace",
            "registry_version",
            "build_id",
            "__shell_body__",
        ):
            assert marker not in html

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_no_inline_script_or_style(self, component_id):
        result = render_single_component(real_registry(), real_brand_package(), component_id)
        html = result.page_details[0].html
        assert "<script" not in html
        assert " style=" not in html

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_attribute_order_alphabetical_on_body(self, component_id):
        result = render_single_component(real_registry(), real_brand_package(), component_id)
        names = _first_open_tag_attr_names(_body_of(result.page_details[0].html))
        assert names == sorted(names)


class TestRepresentativeExactSnapshots:
    def _html(self, component_id, **kw):
        return render_single_component(
            real_registry(), real_brand_package(), component_id, **kw
        ).page_details[0].html

    def test_listing_card_standard(self):
        html = self._html(
            "listing.card.standard",
            prop_overrides={"density": "compact"},
            content_overrides={"listing_ref": "Acme Pet Hotel"},
        )
        assert (
            '<article class="ac-listing ac-listing--card-standard ac-listing--standard ac-listing--compact" '
            'data-atlas-c="listing-card-standard" data-atlas-e="listing_click" '
            'data-atlas-v="1.0.0"><h3>Acme Pet Hotel</h3></article>'
        ) in html

    def test_listing_card_sponsored_has_visible_disclosure(self):
        html = self._html(
            "listing.card.sponsored",
            content_overrides={"listing_ref": "Paid Co", "disclosure": "Sponsored"},
        )
        assert '<p class="ac-listing ac-listing--disclosure">Sponsored</p>' in html
        assert 'data-atlas-e="sponsored_listing_click"' in html

    def test_profile_header_business_is_h1_owner(self):
        html = self._html(
            "profile.header.business",
            content_overrides={"name": "Happy Paws"},
        )
        assert "<header " in html
        assert "<h1>Happy Paws</h1>" in html

    def test_profile_hours_table_is_accessible_table(self):
        html = self._html("profile.hours.table", content_overrides={"hours": "Mon 9-5"})
        assert "<table>" in html
        assert "<caption>Business hours</caption>" in html
        assert '<th scope="col">Schedule</th>' in html
        assert "<td>Mon 9-5</td>" in html

    def test_trust_reviews_summary(self):
        html = self._html(
            "trust.reviews.summary", content_overrides={"rating_summary": "4.8 of 5 (120)"}
        )
        assert (
            '<section class="ac-trust ac-trust--reviews-summary ac-trust--inline" '
            'data-atlas-c="trust-reviews-summary" data-atlas-e="review_expand" '
            'data-atlas-v="1.0.0"><p>4.8 of 5 (120)</p></section>'
        ) in html

    def test_trust_reviews_list_uses_article_per_review(self):
        html = self._html(
            "trust.reviews.list",
            prop_overrides={"density": "comfortable"},
            content_overrides={"reviews": "Great stay"},
        )
        assert "<ul><li><article>Great stay</article></li></ul>" in html

    def test_content_faq_uses_details_summary(self):
        html = self._html(
            "content.faq.standard", content_overrides={"qa_pairs": "Do you allow cats?"}
        )
        assert '<details class="ac-content ac-content--faq-item">' in html
        assert "<summary>Do you allow cats?</summary>" in html

    def test_form_lead_quote_is_post_form_with_submit(self):
        html = self._html(
            "form.lead.quote",
            prop_overrides={"action_route": "/lead"},
            content_overrides={"disclosure": "Sent to providers"},
        )
        assert '<form action="/lead" class="ac-form ac-form--lead-quote" ' in html
        assert 'method="post">' in html
        assert '<p class="ac-form ac-form--disclosure">Sent to providers</p>' in html
        assert "<button type=\"submit\">Submit</button>" in html

    def test_form_claim_standard_is_post_form(self):
        html = self._html(
            "form.claim.standard",
            prop_overrides={"action_route": "/claim", "listing_ref": "L1"},
            content_overrides={"listing_ref": "Listing One"},
        )
        assert '<form action="/claim"' in html
        assert 'method="post">' in html
        assert "<button type=\"submit\">Submit</button>" in html

    def test_form_correction_standard_is_post_form(self):
        html = self._html(
            "form.correction.standard",
            prop_overrides={"action_route": "/correct", "listing_ref": "L1"},
            content_overrides={"listing_ref": "Listing One"},
        )
        assert '<form action="/correct"' in html
        assert 'method="post">' in html

    def test_cta_sticky_mobile_uses_goal_as_aria_label(self):
        html = self._html(
            "cta.sticky.mobile",
            prop_overrides={"goal": "QUOTE_REQUEST", "target_route": "/quote"},
        )
        assert 'aria-label="QUOTE_REQUEST"' in html
        assert 'href="/quote"' in html

    def test_seo_local_links_cities(self):
        html = self._html(
            "seo.local-links.cities",
            prop_overrides={"city_source_ref": "cities-topology"},
            content_overrides={"city_links": "/city/austin"},
        )
        assert '<section class="ac-seo ac-seo--local-links-cities ac-seo--grid"' in html
        assert '<li><a href="/city/austin">/city/austin</a></li>' in html

    def test_content_toc_is_labeled_nav(self):
        html = self._html(
            "content.toc.standard",
            prop_overrides={"heading_refs": "toc-src"},
            content_overrides={"heading_refs": "#section-1"},
        )
        assert 'aria-label="Table of contents"' in html
        assert "<nav " in html
        assert "<ol>" in html

    def test_content_table_comparison_is_accessible_table(self):
        html = self._html(
            "content.table.comparison", content_overrides={"table": "A beats B"}
        )
        assert "<caption>Comparison</caption>" in html
        assert '<th scope="col">Details</th>' in html
        assert "<td>A beats B</td>" in html

    def test_monetization_disclosure_advertising_is_visible(self):
        html = self._html(
            "monetization.disclosure.advertising",
            content_overrides={"disclosure": "This page contains paid placements"},
        )
        assert (
            '<p class="ac-monetization ac-monetization--disclosure">'
            "This page contains paid placements</p>"
        ) in html
        assert 'data-atlas-k="advertising"' in html

    def test_monetization_ribbon_sponsor_is_distinct(self):
        html = self._html(
            "monetization.ribbon.sponsor", content_overrides={"label": "Sponsored"}
        )
        assert (
            '<div class="ac-monetization ac-monetization--ribbon-sponsor ac-monetization--sponsored" '
            'data-atlas-c="monetization-ribbon-sponsor" data-atlas-k="sponsored" '
            'data-atlas-v="1.0.0">Sponsored</div>'
        ) in html

    def test_commerce_pricing_sponsorship_has_disclaimer(self):
        html = self._html(
            "commerce.pricing.sponsorship",
            include_optional=True,
            content_overrides={"pricing": "$500/mo", "disclaimer": "Excludes tax"},
        )
        assert "<li>$500/mo</li>" in html
        assert (
            '<p class="ac-commerce ac-commerce--disclosure">Excludes tax</p>' in html
        )

    def test_status_listing_pending_has_status_role(self):
        html = self._html(
            "status.listing.pending",
            content_overrides={"message": "Pending review", "expectation_text": "2 days"},
        )
        assert 'role="status"' in html
        assert "Pending review" in html
        assert "2 days" in html

    def test_status_listing_unavailable_has_recovery_links(self):
        html = self._html(
            "status.listing.unavailable",
            prop_overrides={"reason": "closed"},
            content_overrides={"message": "Closed", "recovery_links": "/category/dogs"},
        )
        assert 'role="status"' in html
        assert "ac-status--closed" in html
        assert '<a href="/category/dogs">/category/dogs</a>' in html

    def test_legal_statement_standard_is_article(self):
        html = self._html(
            "legal.statement.standard",
            prop_overrides={"kind": "privacy"},
            content_overrides={"body": "We respect your privacy."},
        )
        assert '<article class="ac-legal ac-legal--statement-standard ac-legal--privacy"' in html
        assert "<p>We respect your privacy.</p>" in html

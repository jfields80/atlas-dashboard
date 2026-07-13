"""Disclosure and monetization tests (AES-WEB-002J.9; AES-WEB-002 §6.3,
§17.1, §17.2, E4/E5, CG-COM-001/006).

Covers: advertising disclosure is visible, sponsor markers are
distinguishable, sponsored listing cards cannot silently render as ordinary
listings, premium-profile markers are present, pricing never invents
amounts, the E4 pricing disclaimer renders, legal statements are escaped,
analytics attributes are present, and no external ad request is emitted.
"""

from __future__ import annotations

from . import real_brand_package, real_registry, render_single_component


def _html(component_id, **kw):
    return render_single_component(
        real_registry(), real_brand_package(), component_id, **kw
    ).page_details[0].html


class TestAdvertisingDisclosureVisible:
    def test_disclosure_text_renders_in_flow(self):
        html = _html(
            "monetization.disclosure.advertising",
            content_overrides={"disclosure": "Contains paid placements"},
        )
        assert "Contains paid placements" in html
        assert "ac-monetization--disclosure" in html
        # never visually suppressed
        assert "display:none" not in html
        assert "hidden" not in html

    def test_disclosure_kind_is_machine_readable(self):
        html = _html(
            "monetization.disclosure.advertising",
            content_overrides={"disclosure": "x"},
        )
        assert 'data-atlas-k="advertising"' in html


class TestSponsorMarkersDistinguishable:
    def test_ribbon_has_distinct_sponsored_class_and_marker(self):
        html = _html("monetization.ribbon.sponsor", content_overrides={"label": "Sponsored"})
        assert "ac-monetization--sponsored" in html
        assert 'data-atlas-k="sponsored"' in html
        assert "Sponsored" in html

    def test_sponsored_listing_card_cannot_render_as_organic(self):
        # A sponsored card carries the sponsored surface class, a mandatory
        # visible disclosure, and the sponsored analytics event -- none of
        # which the organic listing.card.standard emits.
        sponsored = _html(
            "listing.card.sponsored",
            content_overrides={"listing_ref": "Paid Co", "disclosure": "Sponsored"},
        )
        organic = _html(
            "listing.card.standard",
            content_overrides={"listing_ref": "Paid Co"},
        )
        assert "ac-listing--sponsored" in sponsored
        assert "ac-listing--disclosure" in sponsored
        assert 'data-atlas-e="sponsored_listing_click"' in sponsored
        assert "ac-listing--sponsored" not in organic
        assert "ac-listing--disclosure" not in organic

    def test_featured_card_has_mandatory_disclosure(self):
        html = _html(
            "listing.card.featured",
            content_overrides={"listing_ref": "Feat", "disclosure": "Featured placement"},
        )
        assert "Featured placement" in html
        assert "ac-listing--featured" in html


class TestPremiumAndUpgrade:
    def test_premium_profile_marker_present(self):
        html = _html(
            "monetization.section.premium-profile",
            content_overrides={"premium_blocks": "Extended details"},
        )
        assert 'data-atlas-k="premium"' in html
        assert "Extended details" in html

    def test_upgrade_prompt_has_optional_disclosure(self):
        html = _html(
            "monetization.prompt.upgrade",
            content_overrides={"offer": "Upgrade now", "disclosure": "Optional upgrade"},
        )
        assert "Optional upgrade" in html
        assert "ac-monetization--disclosure" in html


class TestPricing:
    def test_pricing_renders_only_bound_amounts(self):
        html = _html(
            "commerce.pricing.sponsorship",
            include_optional=True,
            content_overrides={"pricing": "$500/mo", "disclaimer": "Excludes tax"},
        )
        assert "$500/mo" in html
        # no invented currency/amounts beyond what was bound
        assert html.count("$") == 1

    def test_pricing_always_renders_e4_disclaimer(self):
        html = _html(
            "commerce.pricing.sponsorship",
            include_optional=True,
            content_overrides={"pricing": "Custom", "disclaimer": "Final price on inquiry"},
        )
        assert "Final price on inquiry" in html
        assert "ac-commerce--disclosure" in html

    def test_no_external_ad_or_payment_request(self):
        html = _html(
            "commerce.pricing.sponsorship",
            include_optional=True,
            content_overrides={"pricing": "$1", "disclaimer": "d"},
        )
        assert "http://" not in html
        assert "https://" not in html
        assert "checkout" not in html.lower()


class TestLegalEscaping:
    def test_legal_statement_body_is_escaped(self):
        html = _html(
            "legal.statement.standard",
            prop_overrides={"kind": "terms"},
            content_overrides={"body": "<script>evil()</script> & terms"},
        )
        assert "<script>evil()</script>" not in html
        assert "&lt;script&gt;evil()&lt;/script&gt; &amp; terms" in html

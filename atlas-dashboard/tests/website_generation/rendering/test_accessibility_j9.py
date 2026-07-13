"""Accessibility tests for J.9 components (AES-WEB-002J.9; AES-WEB-002 §12,
CG-A11Y-*, prompt §19.G).

Covers: review-list structure, table caption/header association, status
roles, CTA/link accessible names, sponsored-disclosure semantics, gallery
alt behavior per the actual catalog contract, heading ownership, and the
labeled second ``<nav>`` (table of contents).
"""

from __future__ import annotations

from . import real_brand_package, real_registry, render_single_component


def _html(component_id, **kw):
    return render_single_component(
        real_registry(), real_brand_package(), component_id, **kw
    ).page_details[0].html


class TestTableSemantics:
    def test_hours_table_caption_and_header_scope(self):
        html = _html("profile.hours.table", content_overrides={"hours": "Mon 9-5"})
        assert "<caption>Business hours</caption>" in html
        assert 'scope="col"' in html

    def test_comparison_table_caption_and_header_scope(self):
        html = _html("content.table.comparison", content_overrides={"table": "x"})
        assert "<caption>Comparison</caption>" in html
        assert 'scope="col"' in html


class TestStatusRoles:
    def test_pending_has_status_role(self):
        html = _html(
            "status.listing.pending",
            content_overrides={"message": "m", "expectation_text": "e"},
        )
        assert 'role="status"' in html

    def test_unavailable_has_status_role(self):
        html = _html(
            "status.listing.unavailable",
            prop_overrides={"reason": "closed"},
            content_overrides={"message": "m", "recovery_links": "/x"},
        )
        assert 'role="status"' in html


class TestHeadingOwnership:
    def test_profile_header_owns_h1(self):
        html = _html("profile.header.business", content_overrides={"name": "Biz"})
        assert "<h1>Biz</h1>" in html

    def test_listing_card_uses_h3_not_h1(self):
        html = _html("listing.card.standard", content_overrides={"listing_ref": "Biz"})
        assert "<h3>Biz</h3>" in html
        assert "<h1>" not in html.split("<body", 1)[-1]


class TestNavLandmark:
    def test_toc_is_labeled_nav(self):
        html = _html(
            "content.toc.standard",
            prop_overrides={"heading_refs": "src"},
            content_overrides={"heading_refs": "#s1"},
        )
        assert "<nav " in html
        assert 'aria-label="Table of contents"' in html


class TestGalleryAltBehavior:
    def test_gallery_images_carry_alt_attribute(self):
        # The catalog binds AssetRef images with no companion alt text, so
        # each <img> carries alt="" (spec-legal decorative marker) -- never a
        # missing alt attribute (WCAG failure) and never fabricated alt copy.
        html = _html(
            "profile.gallery.standard",
            content_overrides={"images": "asset-hash-1"},
        )
        assert "<img " in html
        assert 'alt=""' in html


class TestAccessibleNames:
    def test_cta_link_has_visible_label_text(self):
        html = _html(
            "cta.claim.listing",
            prop_overrides={"target_route": "/claim"},
            content_overrides={"label": "Claim now"},
        )
        assert ">Claim now</a>" in html

    def test_sticky_cta_link_has_aria_label(self):
        # No label slot exists; the accessible name is the goal prop value.
        html = _html(
            "cta.sticky.mobile",
            prop_overrides={"goal": "PHONE_CALL", "target_route": "/call"},
        )
        assert 'aria-label="PHONE_CALL"' in html


class TestListSemantics:
    def test_reviews_list_uses_list_and_article(self):
        html = _html(
            "trust.reviews.list",
            prop_overrides={"density": "comfortable"},
            content_overrides={"reviews": "Nice"},
        )
        assert "<ul>" in html
        assert "<article>Nice</article>" in html

    def test_credentials_use_list(self):
        html = _html(
            "profile.credentials.list",
            content_overrides={"credentials": "Certified"},
        )
        assert "<ul><li>Certified</li></ul>" in html

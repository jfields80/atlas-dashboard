"""AES-SITE-001 -- commercial action layer / analytics contract tests. No
network."""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.commercial_actions import (
    ACTION_BOOKING,
    ACTION_CALL,
    ACTION_DIRECTIONS,
    ACTION_OFFICIAL_WEBSITE,
    ACTION_REPORT_CHANGE,
    AffiliateConfig,
    apply_affiliate_params,
    build_go_page,
    build_redirect_target,
    go_route,
)


def test_go_route_shape():
    assert go_route("drury-inn-suites-columbus-grove-city", ACTION_OFFICIAL_WEBSITE) == \
        "/go/drury-inn-suites-columbus-grove-city/official-website/"


def test_go_route_rejects_unsafe_listing_id():
    with pytest.raises(ValueError):
        go_route("../../etc/passwd", ACTION_OFFICIAL_WEBSITE)
    with pytest.raises(ValueError):
        go_route("<script>", ACTION_OFFICIAL_WEBSITE)


def test_go_route_rejects_unknown_action():
    with pytest.raises(ValueError):
        go_route("x", "delete-everything")


def test_official_website_target_is_the_real_url():
    target = build_redirect_target(
        ACTION_OFFICIAL_WEBSITE, official_url="https://example-hotel.test/", phone="")
    assert target == "https://example-hotel.test/"


def test_booking_falls_back_to_official_url_without_affiliate_config():
    target = build_redirect_target(
        ACTION_BOOKING, official_url="https://example-hotel.test/", phone="")
    assert target == "https://example-hotel.test/"


def test_affiliate_params_applied_only_when_configured():
    cfg = AffiliateConfig(network="acme", campaign="ptf", param_name="aff", param_value="123")
    assert apply_affiliate_params("https://x.test/?a=1", cfg) == "https://x.test/?a=1&aff=123"
    assert apply_affiliate_params("https://x.test/", cfg) == "https://x.test/?aff=123"
    assert apply_affiliate_params("https://x.test/", AffiliateConfig()) == "https://x.test/"


def test_call_target_is_tel_link():
    target = build_redirect_target(ACTION_CALL, official_url="", phone="614-875-7000")
    assert target == "tel:6148757000"


def test_call_target_empty_without_phone():
    assert build_redirect_target(ACTION_CALL, official_url="", phone="") == ""


def test_report_change_targets_contact_page():
    assert build_redirect_target(ACTION_REPORT_CHANGE, official_url="", phone="") == "/contact/"


def test_directions_target_left_to_caller():
    assert build_redirect_target(ACTION_DIRECTIONS, official_url="", phone="") == ""


def test_build_go_page_happy_path():
    route, html_out = build_go_page(
        listing_id="drury-inn-suites-columbus-grove-city",
        listing_name="Drury Inn & Suites Columbus Grove City",
        action=ACTION_OFFICIAL_WEBSITE,
        destination="https://www.druryhotels.com/locations/columbus-oh/x",
        page_type="hotel_profile", category="pet-friendly-hotels",
        corridor="", verification_status="VERIFIED_PET_FRIENDLY")
    assert route == "/go/drury-inn-suites-columbus-grove-city/official-website/"
    assert "noindex" in html_out
    assert "https://www.druryhotels.com/locations/columbus-oh/x" in html_out
    assert "<script>" in html_out
    assert "outbound_official_click" in html_out


def test_build_go_page_refuses_javascript_scheme():
    with pytest.raises(ValueError):
        build_go_page(
            listing_id="x", listing_name="X", action=ACTION_OFFICIAL_WEBSITE,
            destination="javascript:alert(1)", page_type="hotel_profile",
            category="pet-friendly-hotels")


def test_build_go_page_refuses_relative_parent_traversal():
    with pytest.raises(ValueError):
        build_go_page(
            listing_id="x", listing_name="X", action=ACTION_OFFICIAL_WEBSITE,
            destination="../../admin", page_type="hotel_profile",
            category="pet-friendly-hotels")


def test_build_go_page_refuses_empty_destination():
    with pytest.raises(ValueError):
        build_go_page(
            listing_id="x", listing_name="X", action=ACTION_DIRECTIONS,
            destination="", page_type="hotel_profile", category="pet-friendly-hotels")


def test_build_go_page_allows_tel():
    route, html_out = build_go_page(
        listing_id="drury-inn-suites-columbus-grove-city", listing_name="Drury",
        action=ACTION_CALL, destination="tel:6148757000", page_type="hotel_profile",
        category="pet-friendly-hotels")
    assert "tel:6148757000" in html_out


def test_build_go_page_allows_internal_path():
    route, html_out = build_go_page(
        listing_id="x", listing_name="X", action=ACTION_REPORT_CHANGE,
        destination="/contact/", page_type="hotel_profile", category="pet-friendly-hotels")
    assert route == "/go/x/report-change/"


def test_go_page_destination_json_escaped_safely():
    # A malicious-looking but otherwise valid URL must not break out of the
    # JS string literal.
    dest = "https://example.test/?x=</script><script>alert(1)</script>"
    route, html_out = build_go_page(
        listing_id="x", listing_name="X", action=ACTION_OFFICIAL_WEBSITE,
        destination=dest, page_type="hotel_profile", category="pet-friendly-hotels")
    assert "<script>alert(1)</script>" not in html_out

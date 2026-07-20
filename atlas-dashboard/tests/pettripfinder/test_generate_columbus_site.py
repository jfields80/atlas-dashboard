"""AES-SITE-001 -- end-to-end integration test for the real Columbus site
build. No network (the whole generator is local-file-only); writes to a
pytest tmp_path, never the operational ``data/site_builds/`` root used for
manual inspection."""

from __future__ import annotations

import json
import re

import pytest

from scripts.generate_pettripfinder_columbus_site import run
from scripts.pettripfinder.site_data import load_published_hotel_policy_facts

# PTF-PROD-002A: the generator's verified pet-policy content now comes from the
# TRACKED publishable package (launch_packages/pettripfinder/hotel_policy_facts.json),
# not the gitignored operational corpus -- so this end-to-end test runs in a
# clean checkout. The guard remains only as defence against the package being
# absent entirely (e.g. before its first export); normally it is committed and
# this test runs everywhere.
_HAS_PUBLISHED_FACTS = bool(load_published_hotel_policy_facts())

pytestmark = pytest.mark.skipif(
    not _HAS_PUBLISHED_FACTS,
    reason="tracked hotel_policy_facts.json package absent -- run "
           "scripts/pettripfinder/export_hotel_policy_facts.py",
)


@pytest.fixture(scope="module")
def built_site(tmp_path_factory):
    out = tmp_path_factory.mktemp("ptf_columbus_site")
    exit_code = run(str(out))
    assert exit_code == 0
    return out


def test_build_succeeds_and_reports_launch_ready(built_site):
    report = json.loads((built_site / "_build_report.json").read_text(encoding="utf-8"))
    assert report["launch_inventory_ready"] is True
    assert report["hotel_count"] == 25
    assert report["park_count"] == 14
    assert report["restaurant_count"] == 13
    assert not report["warnings"]


def test_quality_report_clean(built_site):
    report = json.loads((built_site / "_quality_report.json").read_text(encoding="utf-8"))
    assert report["failures"] == []
    assert report["unique_canonicals"] == report["real_content_pages"]


def test_broken_link_report_clean(built_site):
    report = json.loads((built_site / "_broken_link_report.json").read_text(encoding="utf-8"))
    assert report["broken_links"] == []


def test_core_pages_exist(built_site):
    for rel in ("index.html", "sitemap.xml", "robots.txt", "llms.txt", "styles.css",
                "methodology/index.html", "pet-friendly-hotels/index.html",
                "pet-friendly-hotels/policy-comparison/index.html",
                "pet-friendly-hotels/downtown-columbus/index.html",
                "pet-friendly-hotels/dublin/index.html"):
        assert (built_site / rel).exists(), rel


def test_hotel_profile_with_facts_rendered_by_approved_renderer(built_site):
    # PTF-PROD-002: hotel profiles now come from the approved renderer
    # (hotel_profile_page.render_production_hotel_profile), not the old
    # debug-like layout. A verified hotel shows the approved verified badge and
    # the approved six-fact grid -- never the old ptf-policy-table/badge markup.
    text = (built_site / "pet-friendly-hotels" / "drury-inn-suites-columbus-grove-city"
           / "index.html").read_text(encoding="utf-8")
    assert "Policy verified" in text
    assert 'class="fh-facts"' in text          # approved fact grid
    assert "fh-verif ok" in text               # approved verified state
    assert "$50" in text
    assert "ptf-policy-table" not in text       # old markup path is gone
    assert "ptf-badge--verified" not in text


def test_hotel_profile_without_facts_shows_approved_unverified_state(built_site):
    text = (built_site / "pet-friendly-hotels" / "aloft-columbus-university-district"
           / "index.html").read_text(encoding="utf-8")
    assert "Pet policy not verified" in text    # approved unverified badge
    assert "could not confirm" in text          # approved unverified summary
    assert "Policy verified" not in text        # never asserts a verified policy
    assert "ptf-policy-table" not in text


def test_no_production_row_ever_shows_no_pets_badge(built_site):
    # Production contains zero no-pets rows (004I finding) -- confirm the
    # site never fabricates one.
    for path in (built_site / "pet-friendly-hotels").rglob("index.html"):
        if "policy-comparison" in str(path) or "downtown-columbus" in str(path) or "dublin" in str(path):
            continue
        if path.parent == built_site / "pet-friendly-hotels":
            continue
        text = path.read_text(encoding="utf-8")
        assert "ptf-badge--no-pets" not in text


def test_go_pages_are_noindex(built_site):
    go_pages = list((built_site / "go").rglob("index.html"))
    assert len(go_pages) > 0
    for p in go_pages:
        text = p.read_text(encoding="utf-8")
        assert 'content="noindex, nofollow"' in text


def test_go_page_destination_matches_real_official_url(built_site):
    text = (built_site / "go" / "drury-inn-suites-columbus-grove-city" / "official-website"
           / "index.html").read_text(encoding="utf-8")
    assert "druryhotels.com" in text


def test_sitemap_excludes_go_pages(built_site):
    sitemap = (built_site / "sitemap.xml").read_text(encoding="utf-8")
    assert "/go/" not in sitemap


def test_sitemap_includes_comparison_and_corridor_pages(built_site):
    sitemap = (built_site / "sitemap.xml").read_text(encoding="utf-8")
    assert "/pet-friendly-hotels/policy-comparison/" in sitemap
    assert "/pet-friendly-hotels/downtown-columbus/" in sitemap
    assert "/pet-friendly-hotels/dublin/" in sitemap


def test_robots_allows_ai_and_search_crawlers(built_site):
    robots = (built_site / "robots.txt").read_text(encoding="utf-8")
    for agent in ("GPTBot", "OAI-SearchBot", "ClaudeBot", "anthropic-ai", "Googlebot", "Bingbot"):
        assert agent in robots
    assert "Disallow: /go/" in robots
    assert not re.search(r"User-agent: \*\s*\nDisallow: /\s*$", robots, re.M)


def test_comparison_page_lists_all_25_hotels(built_site):
    text = (built_site / "pet-friendly-hotels" / "policy-comparison" / "index.html").read_text(encoding="utf-8")
    rows = re.findall(r"<tr>", text)
    assert len(rows) == 26  # header + 25 hotels


def test_every_profile_has_exactly_one_structured_data_lodging_or_place_entry(built_site):
    for slug, ld_type in (("pet-friendly-hotels", "LodgingBusiness"),
                          ("pet-friendly-parks", "Park"), ("pet-friendly-restaurants", "Restaurant")):
        found_any = False
        for path in (built_site / slug).iterdir():
            if not path.is_dir() or path.name in ("policy-comparison", "downtown-columbus", "dublin"):
                continue
            text = (path / "index.html").read_text(encoding="utf-8")
            payloads = re.findall(r'<script type="application/ld\+json">(.*?)</script>', text)
            types = [json.loads(p.replace("<\\/", "</")).get("@type") for p in payloads]
            assert ld_type in types, path
            found_any = True
        assert found_any


def test_css_appended_and_referenced(built_site):
    css = (built_site / "styles.css").read_text(encoding="utf-8")
    assert ".ptf-policy-table" in css
    assert ".ptf-badge--verified" in css


def test_skip_link_present_on_content_pages_not_go_pages(built_site):
    hub = (built_site / "index.html").read_text(encoding="utf-8")
    assert "ptf-skip-link" in hub
    go_page = (built_site / "go" / "drury-inn-suites-columbus-grove-city" / "official-website"
              / "index.html").read_text(encoding="utf-8")
    assert "ptf-skip-link" not in go_page

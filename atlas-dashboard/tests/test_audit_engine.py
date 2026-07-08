"""Tests for the deterministic Website Intelligence audit engine.

AES-005A Part 3.

Covers: payload normalization, every audit check, empty and complete
websites, score integration with the Part 1 scoring engine, recommendation
integration with the Part 2 recommendation engine, determinism, ordering,
Pydantic compatibility, and regression safety.
"""

import pytest

from engines.website_intelligence.audit_engine import (
    AFFILIATE_PLACEHOLDER_TOKENS,
    AuditEngine,
    BusinessView,
    HOMEPAGE_PATHS,
    PLACEHOLDER_TOKENS,
    PageView,
    SCORE_IMPACTS,
    SiteView,
    THIN_CONTENT_MIN_CHARS,
    category_scores_from_findings,
    generate_findings,
    normalize_input,
)
from engines.website_intelligence.constants import (
    CATEGORY_COMMERCIAL,
    CATEGORY_CONTENT,
    CATEGORY_DIRECTORY,
    CATEGORY_MONETIZATION,
    CATEGORY_NAVIGATION,
    CATEGORY_SEO,
    CATEGORY_UX,
    ENGINE_NAME,
    ENGINE_VERSION,
    READINESS_READY,
    SCORE_CATEGORIES,
    SEVERITIES,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)
from engines.website_intelligence.models import (
    PYDANTIC_V2,
    WebsiteAuditFinding,
    WebsiteAuditInput,
    WebsiteAuditReport,
)
from engines.website_intelligence.recommendation_engine import RecommendationEngine
from engines.website_intelligence.scoring_engine import ScoringEngine

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

LONG_CONTENT = "Verified directory content for real visitors. " * 10  # > 200 chars


def make_page(path, **overrides):
    data = {
        "path": path,
        "title": f"Title for {path}",
        "meta_description": f"Meta description for {path}",
        "h1": f"Heading for {path}",
        "content": LONG_CONTENT + path,
        "links": ["/"] if path != "/" else [],
        "canonical": path,
        "breadcrumbs": [] if path == "/" else ["Home", path],
    }
    data.update(overrides)
    return data


def make_business(name, **overrides):
    data = {
        "name": name,
        "category": "Coffee",
        "location": "Austin",
        "description": f"Unique description for {name}",
    }
    data.update(overrides)
    return data


def healthy_pages():
    paths = ("/", "/about", "/contact", "/austin", "/austin/coffee")
    pages = []
    for path in paths:
        page = make_page(path)
        if path == "/":
            page["links"] = [p for p in paths if p != "/"]
        pages.append(page)
    return pages


def make_input(pages=None, businesses=None, package_overrides=None, assembly_overrides=None):
    pages = healthy_pages() if pages is None else pages
    if businesses is None:
        businesses = [make_business("Alpha Cafe"), make_business("Bravo Cafe")]
    package = {
        "pages": pages,
        "sitemap_paths": [page["path"] for page in pages],
        "robots": "User-agent: *\nAllow: /",
        "cta_blocks": ["hero-cta"],
        "monetization_sections": ["featured-listings"],
        "contact_info": "hello@example-directory.test",
    }
    package.update(package_overrides or {})
    assembly = {
        "slug": "pettripfinder",
        "businesses": businesses,
        "categories": ["Coffee", "Bakery"],
        "locations": ["Austin", "Dublin"],
    }
    assembly.update(assembly_overrides or {})
    return WebsiteAuditInput(
        project_assembly=assembly,
        static_site_package=package,
        preview_build={"pages": []},
    )


def audit(**kwargs):
    return AuditEngine().audit(make_input(**kwargs))


def findings_with(report, check_title):
    return [f for f in report.findings if f.title == check_title]


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_mapping_payloads_normalize(self):
        site = normalize_input(make_input())
        assert isinstance(site, SiteView)
        assert site.site_name == "pettripfinder"
        assert len(site.pages) == 5
        assert all(isinstance(page, PageView) for page in site.pages)
        assert all(isinstance(b, BusinessView) for b in site.businesses)

    def test_attribute_payloads_normalize(self):
        class Page:
            path = "/"
            title = "Home"
            meta_description = "Meta"
            h1 = "H1"
            content = LONG_CONTENT
            links = ()
            canonical = "/"
            breadcrumbs = ()

        class Package:
            pages = (Page(),)
            sitemap_paths = ("/",)
            robots = "User-agent: *"
            cta_blocks = ("cta",)
            monetization_sections = ("ads",)
            contact_info = "x@y.test"

        class Assembly:
            slug = "directbeef"
            businesses = ()
            categories = ()
            locations = ()

        audit_input = WebsiteAuditInput(
            project_assembly=Assembly(),
            static_site_package=Package(),
            preview_build=None,
        )
        site = normalize_input(audit_input)
        assert site.site_name == "directbeef"
        assert site.pages[0].path == "/"
        assert site.pages[0].title == "Home"

    def test_preview_build_pages_used_when_package_has_none(self):
        audit_input = WebsiteAuditInput(
            project_assembly={"slug": "x"},
            static_site_package={"pages": []},
            preview_build={"pages": [make_page("/")]},
        )
        site = normalize_input(audit_input)
        assert len(site.pages) == 1

    def test_missing_fields_normalize_to_empty(self):
        audit_input = WebsiteAuditInput(
            project_assembly={},
            static_site_package={},
            preview_build={},
        )
        site = normalize_input(audit_input)
        assert site.pages == ()
        assert site.businesses == ()
        assert site.robots == ""

    def test_non_input_rejected(self):
        with pytest.raises(ValueError):
            normalize_input({"project_assembly": {}})


# ---------------------------------------------------------------------------
# Complete website
# ---------------------------------------------------------------------------


class TestCompleteWebsite:
    def test_healthy_site_has_no_findings(self):
        report = audit()
        assert report.findings == ()

    def test_healthy_site_scores_hundred(self):
        report = audit()
        assert report.overall_score == 100.0
        assert report.seo_score == 100.0
        assert report.directory_score == 100.0

    def test_healthy_site_grade_and_readiness(self):
        report = audit()
        assert report.grade == "A"
        assert report.launch_readiness == READINESS_READY

    def test_healthy_site_has_no_recommendations(self):
        report = audit()
        assert report.recommendations == ()


# ---------------------------------------------------------------------------
# Empty website
# ---------------------------------------------------------------------------


class TestEmptyWebsite:
    def test_empty_site_flags_missing_homepage(self):
        audit_input = WebsiteAuditInput(
            project_assembly={}, static_site_package={}, preview_build={}
        )
        report = AuditEngine().audit(audit_input)
        assert findings_with(report, "Missing homepage")
        assert report.navigation_score < 100.0

    def test_empty_site_report_is_valid_contract(self):
        audit_input = WebsiteAuditInput(
            project_assembly={}, static_site_package={}, preview_build={}
        )
        report = AuditEngine().audit(audit_input)
        assert isinstance(report, WebsiteAuditReport)
        assert report.work_orders == ()

    def test_site_level_checks_skip_when_no_pages(self):
        audit_input = WebsiteAuditInput(
            project_assembly={}, static_site_package={}, preview_build={}
        )
        report = AuditEngine().audit(audit_input)
        # robots/cta/monetization/contact checks require pages to exist
        assert not findings_with(report, "Missing robots directives")
        assert not findings_with(report, "Missing CTA blocks")
        assert not findings_with(report, "Missing monetization sections")
        assert not findings_with(report, "Missing contact information")


# ---------------------------------------------------------------------------
# SEO checks
# ---------------------------------------------------------------------------


class TestSeoChecks:
    def test_missing_title_flagged(self):
        pages = healthy_pages()
        pages[1]["title"] = ""
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Missing page title")
        assert finding.category == CATEGORY_SEO
        assert finding.severity == SEVERITY_WARNING
        assert "/about" in finding.evidence

    def test_missing_meta_description_flagged(self):
        pages = healthy_pages()
        pages[1]["meta_description"] = ""
        report = audit(pages=pages)
        assert len(findings_with(report, "Missing meta description")) == 1

    def test_missing_h1_flagged(self):
        pages = healthy_pages()
        pages[2]["h1"] = ""
        report = audit(pages=pages)
        assert len(findings_with(report, "Missing H1 heading")) == 1

    def test_duplicate_titles_flagged_once_per_value(self):
        pages = healthy_pages()
        pages[1]["title"] = "Shared title"
        pages[2]["title"] = "Shared title"
        pages[3]["title"] = "Shared title"
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Duplicate page titles")
        assert "/about" in finding.evidence and "/contact" in finding.evidence

    def test_duplicate_meta_descriptions_flagged(self):
        pages = healthy_pages()
        pages[1]["meta_description"] = "Shared meta"
        pages[2]["meta_description"] = "Shared meta"
        report = audit(pages=pages)
        assert len(findings_with(report, "Duplicate meta descriptions")) == 1

    def test_broken_canonical_flagged(self):
        pages = healthy_pages()
        pages[1]["canonical"] = "/nowhere"
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Broken canonical reference")
        assert "/nowhere" in finding.evidence

    def test_absolute_canonical_not_flagged(self):
        pages = healthy_pages()
        pages[1]["canonical"] = "https://example.test/about"
        report = audit(pages=pages)
        assert not findings_with(report, "Broken canonical reference")

    def test_duplicate_paths_flagged_critical(self):
        pages = healthy_pages() + [make_page("/about")]
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Duplicate page paths")
        assert finding.severity == SEVERITY_CRITICAL

    def test_broken_sitemap_reference_flagged(self):
        report = audit(package_overrides={"sitemap_paths": ["/", "/ghost"]})
        (finding,) = findings_with(report, "Broken sitemap reference")
        assert "/ghost" in finding.evidence

    def test_missing_robots_flagged_info(self):
        report = audit(package_overrides={"robots": ""})
        (finding,) = findings_with(report, "Missing robots directives")
        assert finding.severity == SEVERITY_INFO


# ---------------------------------------------------------------------------
# Navigation checks
# ---------------------------------------------------------------------------


class TestNavigationChecks:
    def test_missing_homepage_flagged_critical(self):
        pages = [make_page("/about", links=["/contact"]), make_page("/contact", links=["/about"])]
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Missing homepage")
        assert finding.severity == SEVERITY_CRITICAL

    def test_homepage_alias_paths_accepted(self):
        for home in HOMEPAGE_PATHS:
            pages = [make_page(home, links=[])]
            report = audit(pages=pages)
            assert not findings_with(report, "Missing homepage")

    def test_broken_internal_link_flagged(self):
        pages = healthy_pages()
        pages[1]["links"] = ["/", "/ghost"]
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Broken internal link")
        assert "/ghost" in finding.evidence

    def test_external_links_ignored(self):
        pages = healthy_pages()
        pages[1]["links"] = ["/", "https://example.test", "mailto:x@y.test", "#top"]
        report = audit(pages=pages)
        assert not findings_with(report, "Broken internal link")

    def test_orphan_page_flagged(self):
        pages = healthy_pages()
        pages[0]["links"] = ["/about", "/contact", "/austin"]  # /austin/coffee orphaned
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Orphan page")
        assert "/austin/coffee" in finding.evidence

    def test_homepage_never_orphan(self):
        pages = healthy_pages()
        for page in pages:
            if page["path"] != "/":
                page["links"] = []
        pages[0]["links"] = ["/about", "/contact", "/austin", "/austin/coffee"]
        report = audit(pages=pages)
        assert all("(site)" not in f.evidence or f.title != "Orphan page" for f in report.findings)
        assert not any(
            f.title == "Orphan page" and "path: /;" in f.evidence for f in report.findings
        )

    def test_missing_breadcrumbs_flagged(self):
        pages = healthy_pages()
        pages[1]["breadcrumbs"] = []
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Missing breadcrumbs")
        assert finding.severity == SEVERITY_INFO

    def test_homepage_exempt_from_breadcrumbs(self):
        report = audit()  # healthy homepage has no breadcrumbs
        assert not findings_with(report, "Missing breadcrumbs")

    def test_duplicate_navigation_paths_flagged(self):
        pages = healthy_pages()
        pages[1]["links"] = ["/", "/"]
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Duplicate navigation paths")
        assert finding.severity == SEVERITY_INFO


# ---------------------------------------------------------------------------
# Content checks
# ---------------------------------------------------------------------------


class TestContentChecks:
    def test_empty_page_flagged_critical(self):
        pages = healthy_pages()
        pages[1]["content"] = ""
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Empty page")
        assert finding.severity == SEVERITY_CRITICAL

    def test_thin_page_flagged(self):
        pages = healthy_pages()
        pages[1]["content"] = "short"
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Thin page content")
        assert str(THIN_CONTENT_MIN_CHARS) in finding.evidence

    def test_placeholder_content_flagged(self):
        pages = healthy_pages()
        pages[1]["content"] = LONG_CONTENT + " lorem ipsum dolor"
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Placeholder content")
        assert "lorem ipsum" in finding.evidence

    def test_every_placeholder_token_detected(self):
        for token in PLACEHOLDER_TOKENS:
            pages = healthy_pages()
            pages[1]["content"] = LONG_CONTENT + " " + token
            report = audit(pages=pages)
            assert findings_with(report, "Placeholder content"), token

    def test_missing_business_description_flagged(self):
        businesses = [make_business("Alpha Cafe", description="")]
        report = audit(businesses=businesses)
        (finding,) = findings_with(report, "Missing business description")
        assert "Alpha Cafe" in finding.evidence

    def test_duplicate_business_descriptions_flagged(self):
        businesses = [
            make_business("Alpha Cafe", description="Same words"),
            make_business("Bravo Cafe", description="Same words"),
        ]
        report = audit(businesses=businesses)
        (finding,) = findings_with(report, "Duplicate business descriptions")
        assert "Alpha Cafe" in finding.evidence and "Bravo Cafe" in finding.evidence


# ---------------------------------------------------------------------------
# Directory checks
# ---------------------------------------------------------------------------


class TestDirectoryChecks:
    def test_business_without_category_flagged(self):
        report = audit(businesses=[make_business("Alpha Cafe", category="")])
        assert len(findings_with(report, "Business without category")) == 1

    def test_business_without_location_flagged(self):
        report = audit(businesses=[make_business("Alpha Cafe", location="")])
        assert len(findings_with(report, "Business without location")) == 1

    def test_duplicate_businesses_flagged(self):
        businesses = [make_business("Alpha Cafe"), make_business("alpha cafe")]
        report = audit(businesses=businesses)
        (finding,) = findings_with(report, "Duplicate businesses")
        assert "alpha cafe" in finding.evidence

    def test_broken_category_relationship_flagged(self):
        report = audit(businesses=[make_business("Alpha Cafe", category="Ghost")])
        (finding,) = findings_with(report, "Broken category relationship")
        assert "Ghost" in finding.evidence

    def test_broken_location_relationship_flagged(self):
        report = audit(businesses=[make_business("Alpha Cafe", location="Nowhere")])
        (finding,) = findings_with(report, "Broken location relationship")
        assert "Nowhere" in finding.evidence

    def test_relationship_checks_skip_without_declared_lists(self):
        report = audit(
            businesses=[make_business("Alpha Cafe", category="Anything", location="Anywhere")],
            assembly_overrides={"categories": [], "locations": []},
        )
        assert not findings_with(report, "Broken category relationship")
        assert not findings_with(report, "Broken location relationship")


# ---------------------------------------------------------------------------
# Commercial / monetization / UX checks
# ---------------------------------------------------------------------------


class TestCommercialMonetizationUx:
    def test_affiliate_placeholder_flagged(self):
        for token in AFFILIATE_PLACEHOLDER_TOKENS:
            pages = healthy_pages()
            pages[1]["content"] = LONG_CONTENT + " " + token
            report = audit(pages=pages)
            assert findings_with(report, "Unresolved affiliate placeholder"), token

    def test_missing_cta_blocks_flagged(self):
        report = audit(package_overrides={"cta_blocks": []})
        (finding,) = findings_with(report, "Missing CTA blocks")
        assert finding.category == CATEGORY_COMMERCIAL

    def test_missing_monetization_sections_flagged(self):
        report = audit(package_overrides={"monetization_sections": []})
        (finding,) = findings_with(report, "Missing monetization sections")
        assert finding.category == CATEGORY_MONETIZATION

    def test_missing_contact_information_flagged(self):
        pages = [make_page("/", links=["/about"]), make_page("/about")]
        report = audit(pages=pages, package_overrides={"contact_info": ""})
        (finding,) = findings_with(report, "Missing contact information")
        assert finding.category == CATEGORY_UX

    def test_contact_page_satisfies_contact_check(self):
        report = audit(package_overrides={"contact_info": ""})  # /contact exists
        assert not findings_with(report, "Missing contact information")

    def test_broken_page_hierarchy_flagged(self):
        pages = healthy_pages()
        pages = [p for p in pages if p["path"] != "/austin"]
        pages[0]["links"] = ["/about", "/contact", "/austin/coffee"]
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Broken page hierarchy")
        assert "/austin" in finding.evidence

    def test_self_link_flagged(self):
        pages = healthy_pages()
        pages[1]["links"] = ["/", "/about"]
        report = audit(pages=pages)
        (finding,) = findings_with(report, "Navigation inconsistency")
        assert "/about" in finding.evidence


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------


class TestFindingShape:
    def _broken_report(self):
        pages = [make_page("/about", title="", content="short", breadcrumbs=[])]
        return audit(pages=pages, businesses=[make_business("Alpha Cafe", category="")])

    def test_finding_ids_use_find_prefix(self):
        report = self._broken_report()
        assert report.findings
        assert all(f.finding_id.startswith("find-") for f in report.findings)

    def test_evidence_encodes_path_and_impact(self):
        report = self._broken_report()
        for finding in report.findings:
            assert finding.evidence.startswith("path: ")
            assert "impact: " in finding.evidence

    def test_categories_and_severities_are_valid(self):
        report = self._broken_report()
        for finding in report.findings:
            assert finding.category in SCORE_CATEGORIES
            assert finding.severity in SEVERITIES

    def test_score_impacts_cover_every_severity(self):
        assert set(SCORE_IMPACTS.keys()) == set(SEVERITIES)


# ---------------------------------------------------------------------------
# Score integration
# ---------------------------------------------------------------------------


class TestScoreIntegration:
    def test_single_warning_deducts_fixed_impact(self):
        pages = healthy_pages()
        pages[1]["title"] = ""
        report = audit(pages=pages)
        assert report.seo_score == 100.0 - SCORE_IMPACTS[SEVERITY_WARNING]

    def test_category_score_floors_at_zero(self):
        findings = tuple(
            WebsiteAuditFinding(
                finding_id=f"find-{i}",
                category=CATEGORY_DIRECTORY,
                severity=SEVERITY_CRITICAL,
                title="Duplicate businesses",
            )
            for i in range(10)
        )
        scores = category_scores_from_findings(findings)
        assert scores[CATEGORY_DIRECTORY] == 0.0

    def test_untouched_categories_stay_at_hundred(self):
        pages = healthy_pages()
        pages[1]["title"] = ""
        report = audit(pages=pages)
        assert report.ux_score == 100.0
        assert report.monetization_score == 100.0

    def test_overall_matches_scoring_engine(self):
        pages = healthy_pages()
        pages[1]["title"] = ""
        pages[2]["content"] = ""
        report = audit(pages=pages)
        expected = ScoringEngine().score(
            {
                CATEGORY_SEO: report.seo_score,
                CATEGORY_NAVIGATION: report.navigation_score,
                CATEGORY_CONTENT: report.content_score,
                CATEGORY_DIRECTORY: report.directory_score,
                CATEGORY_COMMERCIAL: report.commercial_score,
                CATEGORY_MONETIZATION: report.monetization_score,
                CATEGORY_UX: report.ux_score,
            }
        )
        assert report.overall_score == expected.overall_score
        assert report.grade == expected.grade
        assert report.launch_readiness == expected.launch_readiness


# ---------------------------------------------------------------------------
# Recommendation integration
# ---------------------------------------------------------------------------


class TestRecommendationIntegration:
    def test_recommendations_match_recommendation_engine(self):
        pages = healthy_pages()
        pages[1]["title"] = ""
        pages[2]["title"] = ""
        report = audit(pages=pages)
        assert report.recommendations == RecommendationEngine().recommend(
            report.findings
        )

    def test_equivalent_findings_merge_into_one_recommendation(self):
        pages = healthy_pages()
        pages[1]["title"] = ""
        pages[2]["title"] = ""
        pages[3]["title"] = ""
        report = audit(pages=pages)
        titles = [rec.title for rec in report.recommendations]
        assert titles.count("Address warning: Missing page title") == 1

    def test_recommendation_finding_ids_reference_report_findings(self):
        pages = healthy_pages()
        pages[1]["title"] = ""
        report = audit(pages=pages)
        finding_ids = {f.finding_id for f in report.findings}
        for rec in report.recommendations:
            assert set(rec.finding_ids) <= finding_ids


# ---------------------------------------------------------------------------
# Ordering + determinism
# ---------------------------------------------------------------------------


class TestOrderingAndDeterminism:
    def _messy_input(self, reverse=False):
        pages = healthy_pages()
        pages[1]["title"] = ""
        pages[2]["content"] = ""
        pages[3]["breadcrumbs"] = []
        businesses = [
            make_business("Alpha Cafe", category=""),
            make_business("Bravo Cafe", description=""),
        ]
        if reverse:
            pages = list(reversed(pages))
            businesses = list(reversed(businesses))
        return make_input(pages=pages, businesses=businesses)

    def test_findings_ordered_by_category_then_severity(self):
        report = AuditEngine().audit(self._messy_input())
        keys = [
            (SCORE_CATEGORIES.index(f.category), SEVERITIES.index(f.severity), f.title, f.finding_id)
            for f in report.findings
        ]
        assert keys == sorted(keys)

    def test_input_order_does_not_change_report(self):
        first = AuditEngine().audit(self._messy_input(reverse=False))
        second = AuditEngine().audit(self._messy_input(reverse=True))
        assert first == second

    def test_identical_input_identical_report(self):
        assert AuditEngine().audit(self._messy_input()) == AuditEngine().audit(
            self._messy_input()
        )

    def test_repeated_runs_are_byte_identical(self):
        results = {
            repr(AuditEngine().audit(self._messy_input())) for _ in range(25)
        }
        assert len(results) == 1

    def test_report_id_is_stable_with_rpt_prefix(self):
        first = AuditEngine().audit(self._messy_input())
        second = AuditEngine().audit(self._messy_input())
        assert first.report_id.startswith("rpt-")
        assert first.report_id == second.report_id

    def test_different_sites_different_report_ids(self):
        healthy = audit()
        messy = AuditEngine().audit(self._messy_input())
        assert healthy.report_id != messy.report_id


# ---------------------------------------------------------------------------
# Engine facade, Pydantic compatibility, regression safety
# ---------------------------------------------------------------------------


class TestFacadeAndCompatibility:
    def test_engine_identity(self):
        engine = AuditEngine()
        assert engine.engine_name == ENGINE_NAME
        assert engine.engine_version == ENGINE_VERSION

    def test_report_is_immutable(self):
        report = audit()
        with pytest.raises(Exception):
            report.overall_score = 0.0

    def test_report_serialization_round_trip(self):
        pages = healthy_pages()
        pages[1]["title"] = ""
        report = audit(pages=pages)
        if PYDANTIC_V2:
            rebuilt = WebsiteAuditReport(**report.model_dump())
        else:  # pragma: no cover - Pydantic v1 runtime
            rebuilt = WebsiteAuditReport(**report.dict())
        assert rebuilt == report


class TestRegressionSafety:
    def test_part1_scoring_engine_unaffected(self):
        scores = {category: 80.0 for category in SCORE_CATEGORIES}
        assert ScoringEngine().score(scores).overall_score == 80.0

    def test_part2_recommendation_engine_unaffected(self):
        finding = WebsiteAuditFinding(
            finding_id="f1",
            category=CATEGORY_SEO,
            severity=SEVERITY_WARNING,
            title="Missing meta descriptions",
        )
        (rec,) = RecommendationEngine().recommend((finding,))
        assert rec.title == "Address warning: Missing meta descriptions"

    def test_generate_findings_pure_function_matches_facade(self):
        audit_input = make_input()
        site = normalize_input(audit_input)
        assert generate_findings(site) == AuditEngine().audit(audit_input).findings

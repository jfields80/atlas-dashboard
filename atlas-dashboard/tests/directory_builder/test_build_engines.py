"""Unit tests: SeoBuildEngine, ContentBuildEngine, ImagePackageEngine."""

import pytest

from engines.directory_builder.constants import (
    PAGE_TYPE_CATEGORY,
    PAGE_TYPE_CATEGORY_LOCATION,
    PAGE_TYPE_FAQ,
    PAGE_TYPE_LANDING,
    PAGE_TYPE_LOCATION,
    WORK_TYPE_BUSINESS_DESCRIPTION,
    WORK_TYPE_IMAGE_ALT_TEXT,
    WORK_TYPE_SEO_METADATA,
)
from engines.directory_builder.content_build_engine import ContentBuildEngine
from engines.directory_builder.image_package_engine import ImagePackageEngine
from engines.directory_builder.import_package_engine import ImportPackageEngine
from engines.directory_builder.seo_build_engine import SeoBuildEngine


@pytest.fixture
def imports(launch_package):
    return ImportPackageEngine.build(launch_package)


@pytest.fixture
def seo(launch_package, imports):
    return SeoBuildEngine.build(launch_package, imports)


@pytest.fixture
def images(launch_package, imports):
    return ImagePackageEngine.build(launch_package, imports)


def _count(pages, page_type):
    return sum(1 for p in pages if p.page_type == page_type)


def test_seo_page_counts(seo):
    assert _count(seo.pages, PAGE_TYPE_CATEGORY) == 2
    assert _count(seo.pages, PAGE_TYPE_LOCATION) == 2
    assert _count(seo.pages, PAGE_TYPE_CATEGORY_LOCATION) == 4  # 2 cats × 2 locs
    assert _count(seo.pages, PAGE_TYPE_LANDING) == 2
    assert _count(seo.pages, PAGE_TYPE_FAQ) == 1


def test_canonical_urls_use_blueprint_domain(seo):
    for page in seo.pages:
        assert page.canonical_url == f"https://demo-directory.example{page.url_path}"


def test_breadcrumbs_start_at_home(seo):
    assert all(p.breadcrumbs[0] == "Home" for p in seo.pages)
    cat_loc = next(p for p in seo.pages if p.page_type == PAGE_TYPE_CATEGORY_LOCATION)
    assert len(cat_loc.breadcrumbs) == 3


def test_internal_links_are_bidirectional_for_cat_loc(seo):
    cat_loc = next(p for p in seo.pages if p.page_type == PAGE_TYPE_CATEGORY_LOCATION)
    inbound = [l for l in seo.internal_links if l.to_path == cat_loc.url_path]
    outbound = [l for l in seo.internal_links if l.from_path == cat_loc.url_path]
    assert len(inbound) == 2  # from category page and location page
    assert len(outbound) == 2  # back to category page and location page


def test_redirects_canonicalize_trailing_slash(seo):
    assert seo.redirects
    assert all(r.from_path.endswith("/") and not r.to_path.endswith("/") for r in seo.redirects)
    assert all(r.status_code == 301 for r in seo.redirects)


def test_sitemap_plan_covers_every_page(seo):
    sitemap_paths = {path for section in seo.sitemap_plan for path in section.paths}
    assert sitemap_paths == {p.url_path for p in seo.pages}


def test_seo_build_is_deterministic(launch_package, imports):
    assert SeoBuildEngine.build(launch_package, imports) == SeoBuildEngine.build(launch_package, imports)


def test_content_items_cover_all_gaps(launch_package, imports, seo, images):
    content = ContentBuildEngine.build(launch_package, imports, seo, images)
    metadata_items = [i for i in content.items if i.work_type == WORK_TYPE_SEO_METADATA]
    assert len(metadata_items) == len(seo.pages)
    description_items = [i for i in content.items if i.work_type == WORK_TYPE_BUSINESS_DESCRIPTION]
    undescribed = [b for b in imports.businesses if not b.description.strip()]
    assert len(description_items) == len(undescribed)
    alt_items = [i for i in content.items if i.work_type == WORK_TYPE_IMAGE_ALT_TEXT]
    assert len(alt_items) == len(images.specs)


def test_content_items_sorted_by_priority(launch_package, imports, seo, images):
    content = ContentBuildEngine.build(launch_package, imports, seo, images)
    priorities = [i.priority for i in content.items]
    assert priorities == sorted(priorities)


def test_image_specs_cover_entities(imports, images):
    by_type = {}
    for spec in images.specs:
        by_type.setdefault(spec.image_type, []).append(spec)
    assert len(by_type["category"]) == len(imports.categories)
    assert len(by_type["location"]) == len(imports.locations)
    assert len(by_type["business"]) == len(imports.businesses)
    for required in ("hero", "logo", "icon", "placeholder"):
        assert required in by_type


def test_image_file_names_follow_naming_standard(images):
    for spec in images.specs:
        assert spec.file_name == (
            f"{spec.image_type}--{spec.subject_slug}--{spec.width}x{spec.height}.{spec.image_format}"
        )


def test_no_images_generated_only_specs(images):
    # The package is pure specification: every entry is metadata, no binary payloads.
    assert all(isinstance(s.file_name, str) for s in images.specs)
    assert images.naming_standard
    assert images.dimension_standards

"""Tests for the Static Site Repository (Phase 4)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from engines.website_generator.models import (
    StaticAsset,
    StaticFileHash,
    StaticPage,
    StaticSiteManifest,
    StaticSitePackage,
    WebsiteQualityReport,
)
from repositories.static_site_repository import (
    MANIFEST_FILENAME,
    StaticSiteRepository,
    StaticSiteRepositoryError,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _dump(model) -> dict:
    """Dump a model under Pydantic v1 or v2 (capability-detected)."""
    if hasattr(model, "model_dump"):
        return model.model_dump()

    return model.dict()


def _file_hash(path: str, content: str) -> StaticFileHash:
    encoded = content.encode("utf-8")

    return StaticFileHash(
        path=path,
        sha256=hashlib.sha256(encoded).hexdigest(),
        size_bytes=len(encoded),
    )


def _html(title: str) -> str:
    return f"<!DOCTYPE html>\n<html><head><title>{title}</title></head><body><h1>{title}</h1></body></html>\n"


def build_package(
    project_slug: str = "pet-trip-finder",
    corrupt_hash: bool = False,
    duplicate_page: bool = False,
) -> StaticSitePackage:
    """Build a small, fully consistent StaticSitePackage.

    Hashing mirrors StaticSiteGenerator._file_hash exactly: SHA-256 over
    UTF-8 bytes, keyed by the site path.
    """
    pages = [
        StaticPage(
            path="/",
            title="Home",
            html=_html("Pet Trip Finder Directory"),
            page_type="home",
            source_id="home",
        ),
        StaticPage(
            path="/about/",
            title="About",
            html=_html("About Pet Trip Finder"),
            page_type="about",
            source_id="about",
        ),
        StaticPage(
            path="/contact/",
            title="Contact",
            html=_html("Contact Pet Trip Finder"),
            page_type="contact",
            source_id="contact",
        ),
        StaticPage(
            path="/categories/pet-stores/",
            title="Pet Stores",
            html=_html("Pet Stores Directory"),
            page_type="category",
            source_id="cat-001",
        ),
        StaticPage(
            path="/locations/columbus-oh/",
            title="Columbus, OH",
            html=_html("Columbus, OH Directory"),
            page_type="location",
            source_id="loc-001",
        ),
        StaticPage(
            path="/businesses/barks-and-rec/",
            title="Barks and Rec",
            html=_html("Barks and Rec"),
            page_type="business",
            source_id="biz-001",
        ),
    ]

    if duplicate_page:
        pages.append(
            StaticPage(
                path="/about/",
                title="About Duplicate",
                html=_html("Duplicate"),
                page_type="about",
                source_id="about-dup",
            )
        )

    pages = sorted(pages, key=lambda p: p.path)

    assets = (
        StaticAsset(
            path="assets/css/site.css",
            content="body { margin: 0; }\n",
            asset_type="css",
        ),
    )

    system_files = (
        StaticAsset(
            path="robots.txt",
            content="User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n",
            asset_type="text",
        ),
        StaticAsset(
            path="sitemap.xml",
            content='<?xml version="1.0" encoding="UTF-8"?>\n<urlset></urlset>\n',
            asset_type="xml",
        ),
    )

    files = sorted(
        [_file_hash(page.path, page.html) for page in pages]
        + [_file_hash(asset.path, asset.content) for asset in assets]
        + [_file_hash(sf.path, sf.content) for sf in system_files],
        key=lambda f: f.path,
    )

    if corrupt_hash:
        first = files[0]
        files[0] = StaticFileHash(
            path=first.path,
            sha256="0" * 64,
            size_bytes=first.size_bytes,
        )

    fingerprint_source = "\n".join(
        f"{f.path}:{f.sha256}:{f.size_bytes}" for f in files
    )
    build_fingerprint = hashlib.sha256(
        fingerprint_source.encode("utf-8")
    ).hexdigest()
    site_id = hashlib.sha256(
        f"{project_slug}:{build_fingerprint}".encode("utf-8")
    ).hexdigest()[:16]

    manifest = StaticSiteManifest(
        engine_name="website_generator",
        engine_version="1.0.0",
        template_name="atlas-directory-default",
        project_slug=project_slug,
        site_id=site_id,
        build_fingerprint=build_fingerprint,
        page_count=len(pages),
        asset_count=len(assets) + len(system_files),
        files=tuple(files),
    )

    return StaticSitePackage(
        project_slug=project_slug,
        template_name="atlas-directory-default",
        pages=tuple(pages),
        assets=assets,
        system_files=system_files,
        manifest=manifest,
        quality_report=WebsiteQualityReport(
            passed=True,
            critical_count=0,
            warning_count=0,
            issues=(),
        ),
    )


def _read_tree(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# ---------------------------------------------------------------------------
# Required coverage
# ---------------------------------------------------------------------------

def test_writes_homepage(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    written = StaticSiteRepository().write(package, root)

    assert "index.html" in written
    assert (root / "index.html").is_file()
    assert (
        (root / "index.html").read_bytes()
        == package.pages[0].html.encode("utf-8")
        or b"Pet Trip Finder Directory" in (root / "index.html").read_bytes()
    )


def test_writes_category_pages(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    written = StaticSiteRepository().write(package, root)

    assert "categories/pet-stores/index.html" in written
    assert (root / "categories" / "pet-stores" / "index.html").is_file()


def test_writes_location_pages(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    written = StaticSiteRepository().write(package, root)

    assert "locations/columbus-oh/index.html" in written
    assert (root / "locations" / "columbus-oh" / "index.html").is_file()


def test_writes_business_pages(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    written = StaticSiteRepository().write(package, root)

    assert "businesses/barks-and-rec/index.html" in written
    assert (root / "businesses" / "barks-and-rec" / "index.html").is_file()


def test_writes_assets(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    written = StaticSiteRepository().write(package, root)

    assert "assets/css/site.css" in written
    target = root / "assets" / "css" / "site.css"
    assert target.is_file()
    assert target.read_bytes() == package.assets[0].content.encode("utf-8")


def test_writes_sitemap(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    written = StaticSiteRepository().write(package, root)

    assert "sitemap.xml" in written
    assert (root / "sitemap.xml").is_file()


def test_writes_robots(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    written = StaticSiteRepository().write(package, root)

    assert "robots.txt" in written
    content = (root / "robots.txt").read_bytes()
    assert content == package.system_files[0].content.encode("utf-8")
    assert b"\r\n" not in content


def test_writes_manifest(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    written = StaticSiteRepository().write(package, root)

    assert MANIFEST_FILENAME in written
    manifest_bytes = (root / MANIFEST_FILENAME).read_bytes()
    assert manifest_bytes == StaticSiteRepository.serialize_manifest(
        package.manifest
    )
    assert package.manifest.build_fingerprint.encode("utf-8") in manifest_bytes
    assert b"\r\n" not in manifest_bytes


def test_deterministic_output(tmp_path: Path) -> None:
    package = build_package()
    repository = StaticSiteRepository()

    root_a = tmp_path / "site_a"
    root_b = tmp_path / "site_b"

    written_a = repository.write(package, root_a)
    written_b = repository.write(package, root_b)

    assert written_a == written_b
    assert _read_tree(root_a) == _read_tree(root_b)

    # Re-writing the same root reproduces byte-identical output.
    first_tree = _read_tree(root_a)
    repository.write(package, root_a)
    assert _read_tree(root_a) == first_tree


# ---------------------------------------------------------------------------
# Additional Phase 4 guarantees
# ---------------------------------------------------------------------------

def test_overwrites_existing_build_safely(tmp_path: Path) -> None:
    package = build_package()
    repository = StaticSiteRepository()
    root = tmp_path / "site"

    repository.write(package, root)

    stale = root / "stale" / "leftover.html"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b"stale content")

    repository.write(package, root)

    assert not stale.exists()
    assert (root / "index.html").is_file()
    assert repository.verify(package, root) == ()


def test_manifest_hashes_verify(tmp_path: Path) -> None:
    package = build_package()
    repository = StaticSiteRepository()
    root = tmp_path / "site"

    repository.write(package, root)

    assert repository.verify(package, root) == ()


def test_verify_detects_tampered_file(tmp_path: Path) -> None:
    package = build_package()
    repository = StaticSiteRepository()
    root = tmp_path / "site"

    repository.write(package, root)
    (root / "robots.txt").write_bytes(b"tampered")

    issues = repository.verify(package, root)

    assert issues
    assert any("robots.txt" in issue for issue in issues)


def test_duplicate_paths_rejected(tmp_path: Path) -> None:
    package = build_package(duplicate_page=True)

    with pytest.raises(StaticSiteRepositoryError):
        StaticSiteRepository().write(package, tmp_path / "site")


def test_unsafe_paths_rejected() -> None:
    with pytest.raises(StaticSiteRepositoryError):
        StaticSiteRepository.relative_file_path("/../escape/")

    with pytest.raises(StaticSiteRepositoryError):
        StaticSiteRepository.relative_file_path("assets/..\\windows")


def test_does_not_mutate_package(tmp_path: Path) -> None:
    package = build_package()
    snapshot = _dump(package)

    StaticSiteRepository().write(package, tmp_path / "site")

    assert _dump(package) == snapshot


def test_utf8_lf_output(tmp_path: Path) -> None:
    package = build_package()
    root = tmp_path / "site"

    StaticSiteRepository().write(package, root)

    for path in root.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            assert b"\r\n" not in content, f"CRLF found in {path}"
            content.decode("utf-8")  # must be valid UTF-8

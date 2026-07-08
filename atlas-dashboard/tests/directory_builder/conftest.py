"""Shared fixtures for Directory Builder tests.

The fixture launch package is intentionally generic ("demo-directory")
— the Builder is business-agnostic and no Atlas project may be
hardcoded. It deliberately includes one duplicate business and one
business with an undefined category so validation paths are exercised.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engines.directory_builder.models import LaunchPackage
from repositories.directory_builder.launch_package_repository import LaunchPackageRepository
from repositories.directory_builder.project_assembly_repository import ProjectAssemblyRepository
from services.directory_builder_service import DirectoryBuilderService

FIXED_BUILT_AT = "2026-01-01T00:00:00+00:00"


def write_demo_launch_package(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    (root / "blueprint.json").write_text(
        json.dumps(
            {
                "project_name": "Demo Directory",
                "project_slug": "demo-directory",
                "niche": "demo services",
                "domain": "https://demo-directory.example",
                "description": "A demonstration directory for engine validation.",
                "target_audience": "demo users",
            }
        ),
        encoding="utf-8",
    )

    (root / "seed_businesses.json").write_text(
        json.dumps(
            [
                {
                    "name": "Alpha Services",
                    "category": "Repair",
                    "city": "Springfield",
                    "state": "OH",
                    "website": "https://alpha.example",
                    "phone": "555-0100",
                    "description": "Established repair provider.",
                    "tags": ["licensed", "insured"],
                    "amenities": ["parking"],
                },
                {
                    "name": "Alpha Services",
                    "category": "Repair",
                    "city": "Springfield",
                    "state": "OH",
                    "website": "https://alpha-dupe.example",
                },
                {
                    "name": "Beta Workshop",
                    "category": "Repair",
                    "city": "Rivertown",
                    "state": "OH",
                    "tags": ["mobile"],
                },
                {
                    "name": "Gamma Studio",
                    "category": "Training",
                    "city": "Springfield",
                    "state": "OH",
                    "description": "Hands-on training studio.",
                },
                {
                    "name": "Delta Undefined",
                    "category": "Ghost Category",
                    "city": "Springfield",
                    "state": "OH",
                },
            ]
        ),
        encoding="utf-8",
    )

    (root / "categories.json").write_text(
        json.dumps(
            [
                {"name": "Repair", "slug": "repair", "description": "Repair providers."},
                {"name": "Training", "slug": "training"},
            ]
        ),
        encoding="utf-8",
    )

    (root / "locations.json").write_text(
        json.dumps(
            [
                {"city": "Springfield", "state": "OH", "slug": "springfield-oh"},
                {"city": "Rivertown", "state": "OH", "slug": "rivertown-oh"},
            ]
        ),
        encoding="utf-8",
    )

    (root / "url_map.csv").write_text(
        "path,page_type,title\n/about,landing,About Us\n/contact,landing,Contact\n",
        encoding="utf-8",
    )
    (root / "seo_pages.csv").write_text(
        "page_type,slug,title,meta_description\nfaq,general,General FAQ,Common questions answered.\n",
        encoding="utf-8",
    )
    (root / "content_plan.csv").write_text(
        "content_type,title,target_keyword,priority\n"
        "article,Choosing a Repair Provider,repair provider,1\n"
        "guide,Getting Started Guide,getting started,2\n",
        encoding="utf-8",
    )
    (root / "monetization_plan.json").write_text(
        json.dumps({"models": [{"name": "Premium Listings", "model_type": "subscription"}]}),
        encoding="utf-8",
    )
    (root / "ai_task_queue.csv").write_text(
        "task_type,description,priority\nverify_domain,Confirm DNS configuration,1\n",
        encoding="utf-8",
    )
    (root / "launch_checklist.md").write_text("# Launch Checklist\n- [ ] DNS\n", encoding="utf-8")
    (root / "operator_notes.md").write_text("# Notes\nDemo package.\n", encoding="utf-8")
    return root


@pytest.fixture
def package_dir(tmp_path: Path) -> Path:
    return write_demo_launch_package(tmp_path / "launch_package")


@pytest.fixture
def launch_package(package_dir: Path) -> LaunchPackage:
    return LaunchPackageRepository().load(package_dir)


@pytest.fixture
def service(tmp_path: Path) -> DirectoryBuilderService:
    return DirectoryBuilderService(
        LaunchPackageRepository(),
        ProjectAssemblyRepository(tmp_path / "projects"),
    )


@pytest.fixture
def fixed_built_at() -> str:
    return FIXED_BUILT_AT


@pytest.fixture
def demo_package_factory():
    """Factory fixture so test modules never import from conftest directly."""
    return write_demo_launch_package

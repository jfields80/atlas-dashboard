"""Unit tests: validation, AI queue, quality, status, and manifest engines."""

import pytest

from engines.directory_builder.ai_queue_engine import AiBuildQueueEngine
from engines.directory_builder.constants import (
    READINESS_NOT_READY,
    SEVERITY_CRITICAL,
    VALIDATION_DUPLICATE_BUSINESS,
    VALIDATION_MISSING_CATEGORY,
)
from engines.directory_builder.content_build_engine import ContentBuildEngine
from engines.directory_builder.image_package_engine import ImagePackageEngine
from engines.directory_builder.import_package_engine import ImportPackageEngine
from engines.directory_builder.manifest_engine import BuildManifestEngine
from engines.directory_builder.quality_engine import QualityReportEngine
from engines.directory_builder.seo_build_engine import SeoBuildEngine
from engines.directory_builder.status_engine import ProjectStatusEngine
from engines.directory_builder.validation_engine import ImportValidationEngine


@pytest.fixture
def pipeline(launch_package):
    imports = ImportPackageEngine.build(launch_package)
    seo = SeoBuildEngine.build(launch_package, imports)
    images = ImagePackageEngine.build(launch_package, imports)
    content = ContentBuildEngine.build(launch_package, imports, seo, images)
    validation = ImportValidationEngine.build(imports, seo)
    queue = AiBuildQueueEngine.build(launch_package, imports, content, images)
    quality = QualityReportEngine.build(launch_package, imports, seo, content, images, validation)
    status = ProjectStatusEngine.build("demo-directory", quality, validation, queue)
    return {
        "imports": imports, "seo": seo, "images": images, "content": content,
        "validation": validation, "queue": queue, "quality": quality, "status": status,
    }


def test_validation_detects_duplicate(pipeline):
    checks = {i.check for i in pipeline["validation"].issues}
    assert VALIDATION_DUPLICATE_BUSINESS in checks


def test_validation_detects_missing_category_as_critical(pipeline):
    critical = [i for i in pipeline["validation"].issues if i.severity == SEVERITY_CRITICAL]
    assert any(i.check == VALIDATION_MISSING_CATEGORY for i in critical)
    assert pipeline["validation"].passed is False


def test_validation_counts_consistent(pipeline):
    report = pipeline["validation"]
    assert report.critical_count + report.warning_count + report.info_count == len(report.issues)


def test_queue_contains_all_unit_families(pipeline):
    types = {u.unit_type for u in pipeline["queue"].units}
    assert types == {"content", "verify_listing", "collect_image", "planned_task"}


def test_queue_verify_units_per_business(pipeline):
    verify = [u for u in pipeline["queue"].units if u.unit_type == "verify_listing"]
    assert len(verify) == len(pipeline["imports"].businesses)


def test_queue_deterministic_ordering(launch_package, pipeline):
    rebuilt = AiBuildQueueEngine.build(
        launch_package, pipeline["imports"], pipeline["content"], pipeline["images"]
    )
    assert rebuilt == pipeline["queue"]


def test_quality_scores_within_bounds(pipeline):
    q = pipeline["quality"]
    for score in (q.seo_score, q.content_score, q.import_score, q.completeness_score,
                  q.automation_readiness, q.launch_readiness_score, q.overall_score):
        assert 0 <= score <= 100
    assert q.grade in {"A", "B", "C", "D", "F"}
    assert len(q.explanations) >= 6


def test_quality_weights_sum_to_one():
    from engines.directory_builder import constants as c
    total = (c.QUALITY_WEIGHT_SEO + c.QUALITY_WEIGHT_CONTENT + c.QUALITY_WEIGHT_IMPORT
             + c.QUALITY_WEIGHT_COMPLETENESS + c.QUALITY_WEIGHT_AUTOMATION + c.QUALITY_WEIGHT_LAUNCH)
    assert abs(total - 1.0) < 1e-9


def test_launch_score_capped_when_validation_fails(pipeline):
    # Fixture package fails validation (Ghost Category) -> launch capped below 60.
    assert pipeline["quality"].launch_readiness_score < 60


def test_status_not_ready_with_critical_issues(pipeline):
    status = pipeline["status"]
    assert status.launch_readiness == READINESS_NOT_READY
    assert status.critical_warnings
    assert status.completion_percentage == pipeline["quality"].overall_score
    assert "demo-directory" in status.operator_summary


def test_status_build_progress_dimensions(pipeline):
    dims = dict(pipeline["status"].build_progress)
    assert set(dims) == {"seo", "content", "import", "completeness", "automation", "launch"}


def test_manifest_build_id_deterministic(launch_package):
    fp1 = BuildManifestEngine.input_fingerprint(launch_package)
    fp2 = BuildManifestEngine.input_fingerprint(launch_package)
    assert fp1 == fp2
    m1 = BuildManifestEngine.build(launch_package, "demo-directory", "2026-01-01T00:00:00+00:00", ())
    m2 = BuildManifestEngine.build(launch_package, "demo-directory", "2026-06-01T00:00:00+00:00", ())
    assert m1.build_id == m2.build_id  # clock-independent
    assert m1.input_fingerprint == fp1

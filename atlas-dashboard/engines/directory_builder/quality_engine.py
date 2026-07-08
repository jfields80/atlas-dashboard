"""Section 9 — Quality Report Engine.

Deterministic, explainable 0–100 scoring across six dimensions with an
explicitly weighted overall score. Every score ships with a plain-English
explanation so an operator can see exactly why a number is what it is.
"""

from __future__ import annotations

from engines.directory_builder.models import (
    ContentBuildPackage,
    ImagePackage,
    ImportPackage,
    QualityReport,
    SeoBuildPackage,
    ValidationReport,
)
from engines.directory_builder.models import LaunchPackage
from engines.directory_builder.constants import (
    GRADE_BANDS,
    IMPORT_SCORE_DEDUCTION_CRITICAL,
    IMPORT_SCORE_DEDUCTION_WARNING,
    LAUNCH_NEEDS_WORK_THRESHOLD,
    QUALITY_WEIGHT_AUTOMATION,
    QUALITY_WEIGHT_COMPLETENESS,
    QUALITY_WEIGHT_CONTENT,
    QUALITY_WEIGHT_IMPORT,
    QUALITY_WEIGHT_LAUNCH,
    QUALITY_WEIGHT_SEO,
    SCORE_MAX,
)
from engines.directory_builder.deterministic import clamp_score

ENGINE_VERSION = "1.0.0"


class QualityReportEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def build(
        package: LaunchPackage,
        imports: ImportPackage,
        seo: SeoBuildPackage,
        content: ContentBuildPackage,
        images: ImagePackage,
        validation: ValidationReport,
    ) -> QualityReport:
        explanations: list[str] = []

        # SEO score: share of pages with both title and meta description present.
        if seo.pages:
            complete_pages = sum(1 for p in seo.pages if p.title.strip() and p.meta_description.strip())
            seo_score = clamp_score(SCORE_MAX * complete_pages / len(seo.pages))
            explanations.append(f"SEO: {complete_pages}/{len(seo.pages)} pages have full metadata.")
        else:
            seo_score = 0
            explanations.append("SEO: no pages generated.")

        # Content score: share of businesses that already have descriptions
        # (remaining ones exist as queued work, not finished content).
        if imports.businesses:
            described = sum(1 for b in imports.businesses if b.description.strip())
            content_score = clamp_score(SCORE_MAX * described / len(imports.businesses))
            explanations.append(f"Content: {described}/{len(imports.businesses)} businesses have descriptions.")
        else:
            content_score = 0
            explanations.append("Content: no businesses imported.")

        # Import score: perfect minus fixed deductions per validation finding.
        import_score = clamp_score(
            SCORE_MAX
            - validation.critical_count * IMPORT_SCORE_DEDUCTION_CRITICAL
            - validation.warning_count * IMPORT_SCORE_DEDUCTION_WARNING
        )
        explanations.append(
            f"Import: {validation.critical_count} critical (-{IMPORT_SCORE_DEDUCTION_CRITICAL} each), "
            f"{validation.warning_count} warnings (-{IMPORT_SCORE_DEDUCTION_WARNING} each)."
        )

        # Completeness: share of launch package inputs actually provided.
        expected_inputs = 11  # canonical launch package file count
        provided = expected_inputs - len(package.missing_files)
        completeness_score = clamp_score(SCORE_MAX * provided / expected_inputs)
        explanations.append(f"Completeness: {provided}/{expected_inputs} launch package inputs provided.")

        # Automation readiness: share of content items with executable instructions
        # plus image specs fully specified (always true by construction, so this
        # measures whether the queues are non-empty and well-formed).
        automatable = [i for i in content.items if i.instructions.strip()]
        if content.items or images.specs:
            automation_readiness = clamp_score(
                SCORE_MAX
                * (len(automatable) + len(images.specs))
                / (len(content.items) + len(images.specs))
            )
            explanations.append(
                f"Automation: {len(automatable)}/{len(content.items)} content items executable; "
                f"{len(images.specs)} image specs fully specified."
            )
        else:
            automation_readiness = 0
            explanations.append("Automation: no work items generated.")

        # Launch readiness score: gated by validation passing.
        base_launch = (seo_score + content_score + import_score) / 3
        launch_readiness_score = clamp_score(base_launch if validation.passed else min(base_launch, LAUNCH_NEEDS_WORK_THRESHOLD - 1))
        explanations.append(
            "Launch: validation passed." if validation.passed
            else f"Launch: capped below {LAUNCH_NEEDS_WORK_THRESHOLD} until critical validation issues are resolved."
        )

        overall = clamp_score(
            seo_score * QUALITY_WEIGHT_SEO
            + content_score * QUALITY_WEIGHT_CONTENT
            + import_score * QUALITY_WEIGHT_IMPORT
            + completeness_score * QUALITY_WEIGHT_COMPLETENESS
            + automation_readiness * QUALITY_WEIGHT_AUTOMATION
            + launch_readiness_score * QUALITY_WEIGHT_LAUNCH
        )
        grade = next(band_grade for threshold, band_grade in GRADE_BANDS if overall >= threshold)

        return QualityReport(
            seo_score=seo_score,
            content_score=content_score,
            import_score=import_score,
            completeness_score=completeness_score,
            automation_readiness=automation_readiness,
            launch_readiness_score=launch_readiness_score,
            overall_score=overall,
            grade=grade,
            explanations=tuple(explanations),
        )

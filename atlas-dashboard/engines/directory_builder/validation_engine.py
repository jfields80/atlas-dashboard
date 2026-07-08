"""Section 6 — Import Validation Engine.

Deterministic validation of the assembled import + SEO packages:
duplicates, missing categories/locations, broken relationships, missing
metadata, missing SEO coverage. Findings never block the build; they are
reported and feed the status and quality engines (honesty layer style —
problems are surfaced, not hidden).
"""

from __future__ import annotations

from engines.directory_builder.models import (
    ImportPackage,
    SeoBuildPackage,
    ValidationIssue,
    ValidationReport,
)
from engines.directory_builder.constants import (
    ID_PREFIX_VALIDATION,
    PAGE_TYPE_CATEGORY,
    PAGE_TYPE_LOCATION,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    VALIDATION_BROKEN_RELATIONSHIP,
    VALIDATION_DUPLICATE_BUSINESS,
    VALIDATION_MISSING_CATEGORY,
    VALIDATION_MISSING_LOCATION,
    VALIDATION_MISSING_METADATA,
    VALIDATION_MISSING_SEO,
)
from engines.directory_builder.deterministic import deterministic_id

ENGINE_VERSION = "1.0.0"


class ImportValidationEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def build(imports: ImportPackage, seo: SeoBuildPackage) -> ValidationReport:
        issues: list[ValidationIssue] = []

        def issue(severity: str, check: str, message: str, subject: str = "") -> None:
            issues.append(
                ValidationIssue(
                    issue_id=deterministic_id(ID_PREFIX_VALIDATION, check, subject or message),
                    severity=severity,
                    check=check,
                    message=message,
                    subject=subject,
                )
            )

        # Duplicates removed during normalization are reported for the operator.
        for dup in imports.duplicates_removed:
            issue(SEVERITY_WARNING, VALIDATION_DUPLICATE_BUSINESS, f"Duplicate business removed: {dup}", dup)

        # Businesses referencing categories/locations not present in the package.
        for biz in imports.businesses:
            if not biz.category_id:
                issue(
                    SEVERITY_CRITICAL,
                    VALIDATION_MISSING_CATEGORY,
                    f"Business '{biz.name}' references a category not defined in categories.json.",
                    biz.business_id,
                )
            if not biz.location_id:
                issue(
                    SEVERITY_CRITICAL,
                    VALIDATION_MISSING_LOCATION,
                    f"Business '{biz.name}' references a location not defined in locations.json.",
                    biz.business_id,
                )

        # Relationship integrity.
        business_ids = {b.business_id for b in imports.businesses}
        category_ids = {c.category_id for c in imports.categories}
        location_ids = {l.location_id for l in imports.locations}
        for rel in imports.relationships:
            if (
                rel.business_id not in business_ids
                or rel.category_id not in category_ids
                or rel.location_id not in location_ids
            ):
                issue(
                    SEVERITY_CRITICAL,
                    VALIDATION_BROKEN_RELATIONSHIP,
                    f"Relationship {rel.relationship_id} references a missing record.",
                    rel.relationship_id,
                )

        # Missing metadata on businesses.
        for biz in imports.businesses:
            missing = [
                field
                for field, value in (("website", biz.website), ("phone", biz.phone), ("description", biz.description))
                if not value.strip()
            ]
            if missing:
                issue(
                    SEVERITY_INFO,
                    VALIDATION_MISSING_METADATA,
                    f"Business '{biz.name}' missing: {', '.join(missing)}.",
                    biz.business_id,
                )

        # SEO coverage: every category and location must have a page.
        covered_categories = {p.category_id for p in seo.pages if p.page_type == PAGE_TYPE_CATEGORY}
        covered_locations = {p.location_id for p in seo.pages if p.page_type == PAGE_TYPE_LOCATION}
        for cat in imports.categories:
            if cat.category_id not in covered_categories:
                issue(SEVERITY_WARNING, VALIDATION_MISSING_SEO, f"No SEO page for category '{cat.name}'.", cat.category_id)
        for loc in imports.locations:
            if loc.location_id not in covered_locations:
                issue(
                    SEVERITY_WARNING,
                    VALIDATION_MISSING_SEO,
                    f"No SEO page for location '{loc.city}, {loc.state}'.",
                    loc.location_id,
                )
        for page in seo.pages:
            if not page.title.strip() or not page.meta_description.strip():
                issue(SEVERITY_WARNING, VALIDATION_MISSING_SEO, f"Page {page.url_path} missing title or meta description.", page.page_id)

        issues.sort(key=lambda i: (i.severity, i.check, i.issue_id))
        critical = sum(1 for i in issues if i.severity == SEVERITY_CRITICAL)
        warning = sum(1 for i in issues if i.severity == SEVERITY_WARNING)
        info = sum(1 for i in issues if i.severity == SEVERITY_INFO)

        return ValidationReport(
            issues=tuple(issues),
            critical_count=critical,
            warning_count=warning,
            info_count=info,
            passed=critical == 0,
        )

"""Website quality gate.

Every generated website passes through this validator before it can be
exported.

The validator never modifies content. It only reports issues.

Checks performed:
- homepage exists
- no duplicate page paths
- no empty page titles
- no empty HTML output
- no forbidden HTML patterns (scripts, unresolved placeholders)
- no external asset references in pages, assets, or system files
- required static assets present
- required system files present
"""

from __future__ import annotations

import hashlib
import re

from engines.website_generator.constants import (
    EXTERNAL_ASSET_PATTERNS,
    FORBIDDEN_HTML_PATTERNS,
    REQUIRED_STATIC_ASSETS,
    REQUIRED_SYSTEM_FILES,
)
from engines.website_generator.models import (
    StaticSitePackage,
    WebsiteQualityIssue,
    WebsiteQualityReport,
)

_EXTERNAL_ASSET_RES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in EXTERNAL_ASSET_PATTERNS
)


class WebsiteQualityGate:

    def validate(self, package: StaticSitePackage) -> WebsiteQualityReport:
        issues: list[WebsiteQualityIssue] = []

        page_paths = [page.path for page in package.pages]

        if "/" not in page_paths:
            issues.append(
                WebsiteQualityIssue(
                    issue_id="missing-homepage",
                    severity="critical",
                    check="homepage",
                    message="Homepage was not generated.",
                )
            )

        seen: set[str] = set()
        reported_duplicates: set[str] = set()
        for path in page_paths:
            if path in seen and path not in reported_duplicates:
                reported_duplicates.add(path)
                issues.append(
                    WebsiteQualityIssue(
                        issue_id=self._id(path, "duplicate-path"),
                        severity="critical",
                        check="duplicate-path",
                        message="Multiple pages generated for the same path.",
                        path=path,
                    )
                )
            seen.add(path)

        for page in package.pages:
            if not page.title.strip():
                issues.append(
                    WebsiteQualityIssue(
                        issue_id=self._id(page.path, "title"),
                        severity="critical",
                        check="title",
                        message="Page title is empty.",
                        path=page.path,
                    )
                )

            if not page.html.strip():
                issues.append(
                    WebsiteQualityIssue(
                        issue_id=self._id(page.path, "html"),
                        severity="critical",
                        check="html",
                        message="HTML output is empty.",
                        path=page.path,
                    )
                )

            lowered = page.html.lower()

            for forbidden in FORBIDDEN_HTML_PATTERNS:
                if forbidden in lowered:
                    issues.append(
                        WebsiteQualityIssue(
                            issue_id=self._id(page.path, forbidden),
                            severity="critical",
                            check="forbidden-pattern",
                            message=f"Found forbidden HTML pattern: {forbidden}",
                            path=page.path,
                        )
                    )

            for pattern in _EXTERNAL_ASSET_RES:
                if pattern.search(page.html):
                    issues.append(
                        WebsiteQualityIssue(
                            issue_id=self._id(page.path, pattern.pattern),
                            severity="critical",
                            check="external-asset",
                            message=(
                                "Page references an external asset: "
                                f"pattern {pattern.pattern!r} matched."
                            ),
                            path=page.path,
                        )
                    )

        asset_paths = {asset.path for asset in package.assets}
        for required in REQUIRED_STATIC_ASSETS:
            if required not in asset_paths:
                issues.append(
                    WebsiteQualityIssue(
                        issue_id=self._id(required, "missing-asset"),
                        severity="critical",
                        check="required-asset",
                        message=f"Required static asset is missing: {required}",
                        path=required,
                    )
                )

        system_paths = {system.path for system in package.system_files}
        for required in REQUIRED_SYSTEM_FILES:
            if required not in system_paths:
                issues.append(
                    WebsiteQualityIssue(
                        issue_id=self._id(required, "missing-system-file"),
                        severity="critical",
                        check="required-system-file",
                        message=f"Required system file is missing: {required}",
                        path=required,
                    )
                )

        for asset in package.assets + package.system_files:
            for pattern in _EXTERNAL_ASSET_RES:
                if pattern.search(asset.content):
                    issues.append(
                        WebsiteQualityIssue(
                            issue_id=self._id(asset.path, pattern.pattern),
                            severity="critical",
                            check="external-asset",
                            message=(
                                "Asset references an external resource: "
                                f"pattern {pattern.pattern!r} matched."
                            ),
                            path=asset.path,
                        )
                    )

        critical = sum(1 for issue in issues if issue.severity == "critical")
        warnings = sum(1 for issue in issues if issue.severity == "warning")

        return WebsiteQualityReport(
            passed=critical == 0,
            critical_count=critical,
            warning_count=warnings,
            issues=tuple(issues),
        )

    @staticmethod
    def _id(path: str, check: str) -> str:
        return hashlib.sha256(f"{path}:{check}".encode("utf-8")).hexdigest()[:16]

"""Website Generator v1.

Deterministic static-site generation for Atlas Project Assemblies.

This package is intentionally framework-free:
- no Flask
- no database
- no filesystem writes
- no publishing
"""

from engines.website_generator.models import (
    StaticAsset,
    StaticPage,
    StaticSiteManifest,
    StaticSitePackage,
    WebsiteQualityIssue,
    WebsiteQualityReport,
)

__all__ = [
    "StaticAsset",
    "StaticPage",
    "StaticSiteManifest",
    "StaticSitePackage",
    "WebsiteQualityIssue",
    "WebsiteQualityReport",
]

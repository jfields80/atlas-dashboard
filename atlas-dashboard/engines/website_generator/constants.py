"""Constants for Website Generator v1."""

from __future__ import annotations

ENGINE_NAME = "website_generator"
ENGINE_VERSION = "1.0.0"

DEFAULT_TEMPLATE_NAME = "clean_directory_v1"

REQUIRED_STATIC_ASSETS: tuple[str, ...] = (
    "assets/css/site.css",
)

REQUIRED_SYSTEM_FILES: tuple[str, ...] = (
    "robots.txt",
    "sitemap.xml",
)

# Substrings that must never appear anywhere in generated page HTML.
# These are unconditional: scripts and unresolved template placeholders
# are never legitimate page content in v1.
FORBIDDEN_HTML_PATTERNS: tuple[str, ...] = (
    "<script",
    "{{",
    "}}",
)

# Regex patterns (case-insensitive) that detect external *asset references*:
# scripts, stylesheets, images, or CSS imports loaded from another origin.
#
# These are deliberately targeted at attribute/CSS contexts rather than bare
# "http://" substrings. Plain-text URLs are legitimate directory content
# (e.g. a business listing displaying its website), and must not fail the
# quality gate. Only loading a resource from an external origin is forbidden.
EXTERNAL_ASSET_PATTERNS: tuple[str, ...] = (
    r"""src\s*=\s*["'](?:https?:)?//""",
    r"""<link\b[^>]*href\s*=\s*["'](?:https?:)?//""",
    r"""url\(\s*["']?(?:https?:)?//""",
    r"""@import\s+["'](?:https?:)?//""",
)

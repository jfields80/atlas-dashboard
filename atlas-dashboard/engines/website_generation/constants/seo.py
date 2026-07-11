"""SEO metadata limits (AES-WEB-001 §5.8, constants/seo.py).

Deterministic truncation rules consume these limits from Phase 3 onward;
Phase 1 pins the named limits so contracts and tests share one source.
"""

TITLE_MAX_LENGTH = 60
META_DESCRIPTION_MAX_LENGTH = 160
META_DESCRIPTION_MIN_LENGTH = 50
CANONICAL_URL_MAX_LENGTH = 2048
SITEMAP_FILENAME = "sitemap.xml"
ROBOTS_FILENAME = "robots.txt"

"""Named constants for the Directory Builder Engine.

Atlas contract: all scoring is deterministic and explainable, driven by
named constants. No magic numbers inside engine logic.
"""

ENGINE_NAME = "directory_builder"
ENGINE_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Deterministic ID prefixes
# ---------------------------------------------------------------------------
ID_PREFIX_BUSINESS = "BIZ"
ID_PREFIX_CATEGORY = "CAT"
ID_PREFIX_LOCATION = "LOC"
ID_PREFIX_RELATIONSHIP = "REL"
ID_PREFIX_TAG = "TAG"
ID_PREFIX_AMENITY = "AMN"
ID_PREFIX_PAGE = "PAGE"
ID_PREFIX_CONTENT_ITEM = "CWI"
ID_PREFIX_IMAGE_SPEC = "IMG"
ID_PREFIX_VALIDATION = "VAL"
ID_PREFIX_WORK_UNIT = "WU"

ID_HASH_LENGTH = 10  # hex chars taken from sha256 of the canonical key

# ---------------------------------------------------------------------------
# Project structure (relative to projects/<project_slug>/)
# ---------------------------------------------------------------------------
PROJECT_DIRECTORIES = (
    "config",
    "database",
    "imports",
    "content",
    "seo",
    "tasks",
    "reports",
    "logs",
    "exports",
    "assets",
    "assets/images",
    "assets/templates",
    "documentation",
)

# ---------------------------------------------------------------------------
# Import package: scaffold tables that ship as empty, header-only artifacts
# ---------------------------------------------------------------------------
SCAFFOLD_TABLES = (
    "reviews",
    "claims",
    "premium_listings",
    "articles",
    "events",
    "coupons",
    "jobs",
    "faqs",
    "media_references",
)

SCAFFOLD_TABLE_HEADERS = {
    "reviews": ("review_id", "business_id", "rating", "title", "body", "author", "created_at"),
    "claims": ("claim_id", "business_id", "claimant_name", "claimant_email", "status", "created_at"),
    "premium_listings": ("premium_id", "business_id", "tier", "starts_at", "ends_at", "status"),
    "articles": ("article_id", "slug", "title", "category_id", "location_id", "status"),
    "events": ("event_id", "business_id", "location_id", "title", "starts_at", "ends_at"),
    "coupons": ("coupon_id", "business_id", "title", "code", "expires_at", "status"),
    "jobs": ("job_id", "business_id", "title", "location_id", "employment_type", "status"),
    "faqs": ("faq_id", "page_id", "question", "answer", "position"),
    "media_references": ("media_id", "owner_type", "owner_id", "file_name", "alt_text", "position"),
}

# ---------------------------------------------------------------------------
# SEO
# ---------------------------------------------------------------------------
PAGE_TYPE_CATEGORY = "category"
PAGE_TYPE_LOCATION = "location"
PAGE_TYPE_CATEGORY_LOCATION = "category_location"
PAGE_TYPE_LANDING = "landing"
PAGE_TYPE_FAQ = "faq"

URL_ROOT = "/"
URL_CATEGORY_PREFIX = "/category"
URL_LOCATION_PREFIX = "/location"
URL_FAQ_PREFIX = "/faq"

REDIRECT_STATUS_CODE = 301

TITLE_MAX_LENGTH = 60
META_DESCRIPTION_MAX_LENGTH = 155

ROBOTS_RECOMMENDATIONS = (
    "Allow all crawlers on category, location, and category-location pages.",
    "Disallow: /search (parameterized internal search results).",
    "Disallow: /admin and any operator-only paths.",
    "Reference the XML sitemap index in robots.txt via a Sitemap: directive.",
    "Serve robots.txt with a 200 status and text/plain content type.",
)

SITEMAP_MAX_URLS_PER_FILE = 5000

# ---------------------------------------------------------------------------
# Content work item types
# ---------------------------------------------------------------------------
WORK_TYPE_ARTICLE = "article"
WORK_TYPE_GUIDE = "guide"
WORK_TYPE_FAQ = "faq"
WORK_TYPE_COMPARISON = "comparison"
WORK_TYPE_CITY_PAGE = "city_page"
WORK_TYPE_CATEGORY_PAGE = "category_page"
WORK_TYPE_BUSINESS_DESCRIPTION = "business_description"
WORK_TYPE_SEO_METADATA = "seo_metadata"
WORK_TYPE_IMAGE_ALT_TEXT = "image_alt_text"

PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3

CONTENT_TYPE_TO_WORK_TYPE = {
    "article": WORK_TYPE_ARTICLE,
    "guide": WORK_TYPE_GUIDE,
    "faq": WORK_TYPE_FAQ,
    "comparison": WORK_TYPE_COMPARISON,
    "city_page": WORK_TYPE_CITY_PAGE,
    "category_page": WORK_TYPE_CATEGORY_PAGE,
}
DEFAULT_WORK_TYPE = WORK_TYPE_ARTICLE

# ---------------------------------------------------------------------------
# Image specifications (width, height)
# ---------------------------------------------------------------------------
IMAGE_TYPE_HERO = "hero"
IMAGE_TYPE_CATEGORY = "category"
IMAGE_TYPE_LOCATION = "location"
IMAGE_TYPE_BUSINESS = "business"
IMAGE_TYPE_PLACEHOLDER = "placeholder"
IMAGE_TYPE_LOGO = "logo"
IMAGE_TYPE_ICON = "icon"

IMAGE_DIMENSIONS = {
    IMAGE_TYPE_HERO: (1920, 900),
    IMAGE_TYPE_CATEGORY: (1200, 675),
    IMAGE_TYPE_LOCATION: (1200, 675),
    IMAGE_TYPE_BUSINESS: (800, 600),
    IMAGE_TYPE_PLACEHOLDER: (800, 600),
    IMAGE_TYPE_LOGO: (512, 512),
    IMAGE_TYPE_ICON: (128, 128),
}

IMAGE_FORMAT_DEFAULT = "webp"
IMAGE_FORMAT_LOGO = "svg"
IMAGE_NAMING_STANDARD = "{image_type}--{subject_slug}--{width}x{height}.{ext}"

# ---------------------------------------------------------------------------
# Validation severities
# ---------------------------------------------------------------------------
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"

VALIDATION_DUPLICATE_BUSINESS = "duplicate_business"
VALIDATION_MISSING_CATEGORY = "missing_category"
VALIDATION_MISSING_LOCATION = "missing_location"
VALIDATION_BROKEN_RELATIONSHIP = "broken_relationship"
VALIDATION_MISSING_METADATA = "missing_metadata"
VALIDATION_MISSING_SEO = "missing_seo"

# ---------------------------------------------------------------------------
# Quality scoring — weights are explicit and must sum to 1.0
# ---------------------------------------------------------------------------
QUALITY_WEIGHT_SEO = 0.20
QUALITY_WEIGHT_CONTENT = 0.20
QUALITY_WEIGHT_IMPORT = 0.25
QUALITY_WEIGHT_COMPLETENESS = 0.15
QUALITY_WEIGHT_AUTOMATION = 0.10
QUALITY_WEIGHT_LAUNCH = 0.10

# Deductions applied per validation finding when computing the import score.
IMPORT_SCORE_DEDUCTION_CRITICAL = 15
IMPORT_SCORE_DEDUCTION_WARNING = 5

SCORE_MIN = 0
SCORE_MAX = 100

# ---------------------------------------------------------------------------
# Launch readiness thresholds (applied to overall quality score)
# ---------------------------------------------------------------------------
LAUNCH_READY_THRESHOLD = 85
LAUNCH_NEEDS_WORK_THRESHOLD = 60

READINESS_READY = "READY"
READINESS_NEEDS_WORK = "NEEDS_WORK"
READINESS_NOT_READY = "NOT_READY"

GRADE_BANDS = (
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0, "F"),
)

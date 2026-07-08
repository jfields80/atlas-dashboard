"""Constants for the Website Intelligence & Work Planning Engine (AES-005A Part 1).

This module is the single source of truth for:

- engine identity (name / version)
- scoring categories and their weights
- score bounds and precision
- grade bands
- launch readiness bands
- finding severities, recommendation priorities, work order statuses

Everything in this module is deterministic, immutable data. No logic lives here.
"""

# ---------------------------------------------------------------------------
# Engine identity
# ---------------------------------------------------------------------------

ENGINE_NAME = "website_intelligence"
ENGINE_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Score bounds
# ---------------------------------------------------------------------------

SCORE_MIN = 0.0
SCORE_MAX = 100.0
SCORE_PRECISION = 2

# ---------------------------------------------------------------------------
# Scoring categories (stable, ordered)
# ---------------------------------------------------------------------------

CATEGORY_SEO = "seo"
CATEGORY_NAVIGATION = "navigation"
CATEGORY_CONTENT = "content"
CATEGORY_DIRECTORY = "directory"
CATEGORY_COMMERCIAL = "commercial"
CATEGORY_MONETIZATION = "monetization"
CATEGORY_UX = "ux"

# Stable ordering. All iteration in the scoring engine follows this tuple.
SCORE_CATEGORIES = (
    CATEGORY_SEO,
    CATEGORY_NAVIGATION,
    CATEGORY_CONTENT,
    CATEGORY_DIRECTORY,
    CATEGORY_COMMERCIAL,
    CATEGORY_MONETIZATION,
    CATEGORY_UX,
)

# Weights must sum to exactly 1.0 (validated by the scoring engine).
CATEGORY_WEIGHTS = {
    CATEGORY_SEO: 0.15,
    CATEGORY_NAVIGATION: 0.15,
    CATEGORY_CONTENT: 0.15,
    CATEGORY_DIRECTORY: 0.20,
    CATEGORY_COMMERCIAL: 0.15,
    CATEGORY_MONETIZATION: 0.10,
    CATEGORY_UX: 0.10,
}

# Tolerance used when validating that weights sum to 1.0 (floating point safety).
WEIGHT_SUM_TOLERANCE = 1e-9

# ---------------------------------------------------------------------------
# Grades
# ---------------------------------------------------------------------------

GRADE_A = "A"
GRADE_B = "B"
GRADE_C = "C"
GRADE_D = "D"
GRADE_F = "F"

# Evaluated top-down: first threshold the score meets or exceeds wins.
# Scores below every threshold receive GRADE_FLOOR.
GRADE_BANDS = (
    (90.0, GRADE_A),
    (80.0, GRADE_B),
    (70.0, GRADE_C),
    (60.0, GRADE_D),
)
GRADE_FLOOR = GRADE_F

# ---------------------------------------------------------------------------
# Launch readiness
# ---------------------------------------------------------------------------

READINESS_READY = "READY"
READINESS_REVIEW = "REVIEW"
READINESS_NEEDS_WORK = "NEEDS_WORK"
READINESS_NOT_READY = "NOT_READY"

# Evaluated top-down: first threshold the score meets or exceeds wins.
# Scores below every threshold receive READINESS_FLOOR.
READINESS_BANDS = (
    (90.0, READINESS_READY),
    (75.0, READINESS_REVIEW),
    (60.0, READINESS_NEEDS_WORK),
)
READINESS_FLOOR = READINESS_NOT_READY

# ---------------------------------------------------------------------------
# Finding severities
# ---------------------------------------------------------------------------

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"

SEVERITIES = (
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    SEVERITY_INFO,
)

# ---------------------------------------------------------------------------
# Recommendation / work order priorities
# ---------------------------------------------------------------------------

PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"

PRIORITIES = (
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
)

# ---------------------------------------------------------------------------
# Work order statuses
# ---------------------------------------------------------------------------

WORK_ORDER_STATUS_PENDING = "PENDING"
WORK_ORDER_STATUS_APPROVED = "APPROVED"
WORK_ORDER_STATUS_REJECTED = "REJECTED"

WORK_ORDER_STATUSES = (
    WORK_ORDER_STATUS_PENDING,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_REJECTED,
)

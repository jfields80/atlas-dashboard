"""Component-system constants (AES-WEB-002A; AES-WEB-002 §4, §7.3, §9.2, §22).

Constants only — no computation, no imports beyond the standard library
(dependency matrix, AES-WEB-001 §3.2). Every component-system magic number
lives here or does not exist.

Scope note: 002A owns the naming grammar, complexity budgets, composition
limits, and version constants that the registry needs to validate
definitions. The §3.2 selection scoring tables and CTA label/action table
support the selection and conversion waves (002D/002F) and are deferred
there, not authored in 002A.
"""

# ---------------------------------------------------------------------------
# Component identity / naming grammar (AES-WEB-002 §4.1, §4.3)
# ---------------------------------------------------------------------------

# component_id := family "." pattern "." intent — exactly three segments.
COMPONENT_ID_SEGMENT_COUNT = 3
COMPONENT_ID_SEGMENT_MAX_LENGTH = 24
COMPONENT_ID_MAX_LENGTH = 64
# Each segment is [a-z][a-z0-9-]* (validated by the registry).
COMPONENT_ID_SEGMENT_PATTERN = r"^[a-z][a-z0-9-]*$"
COMPONENT_ID_SEPARATOR = "."

# Variant delimiter (§4.2): listing.card.standard::compact.
VARIANT_DELIMITER = "::"

# Namespaces (§4.3).
EXPERIMENTAL_PREFIX = "x."
EXTENSION_PREFIX = "ext."
PROHIBITED_SITE_PREFIX = "site."

# Reserved words that may not appear as a family segment (§4.3).
RESERVED_FAMILY_WORDS = ("atlas", "internal", "test")

# ---------------------------------------------------------------------------
# Complexity budget (AES-WEB-002 §7.3 — BLOCKING at registration)
# ---------------------------------------------------------------------------

MAX_REQUIRED_PROPS = 6
MAX_OPTIONAL_PROPS = 10
MAX_VARIANTS = 6  # excludes the global density axis
MAX_BOOL_PROPS = 2
# complexity score = required_props + 0.5*optional_props + 2*variants.
MAX_COMPLEXITY_SCORE = 20
# Weight numerator/denominator kept integer to avoid float arithmetic:
# score*2 = 2*required + optional + 4*variants  <=  MAX_COMPLEXITY_SCORE*2.
COMPLEXITY_SCORE_DOUBLED_CEILING = MAX_COMPLEXITY_SCORE * 2

# ---------------------------------------------------------------------------
# Composition limits (AES-WEB-002 §9.2)
# ---------------------------------------------------------------------------

MAX_COMPOSITION_DEPTH = 6
MAX_SECTIONS_PER_BODY_DEFAULT = 12

# ---------------------------------------------------------------------------
# Footer link ceiling (AES-WEB-002 §5.15; Wave 2, AES-WEB-002C)
# ---------------------------------------------------------------------------

# §5.15: footer link farms are forbidden — "footer SEO links capped at
# constants ceiling, default 40". Declared here (name + default only);
# enforcement is gate work (CG-CMP-006 family, AES-WEB-002I).
FOOTER_SEO_LINK_CEILING = 40

# ---------------------------------------------------------------------------
# Semantic version rule (semver, AES-WEB-002 §22)
# ---------------------------------------------------------------------------

SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"

# Component-system version axes themselves live in ``contracts/versions.py``
# (AES-WEB-002 §22.1) — the ``contracts/`` layer owns versions and may not
# import ``constants/``. Compatibility-range axes (declarative data the
# registry validates against) live here.

# Compatibility-range axes a definition may pin (AES-WEB-002 §22.1).
COMPATIBILITY_AXES = (
    "renderer",
    "token_schema",
    "registry_schema",
    "analytics_contract",
    "accessibility_contract",
    "seo_contract",
    "responsive_contract",
)

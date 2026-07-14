"""SEO metadata limits and compilation rules (AES-WEB-001 §5.8,
constants/seo.py; internal sequencing label AES-WEB-002J.5).

Deterministic truncation rules consume these limits; the SEO Engine
(``engines/website_generation/seo/``) is the sole consumer. Constants only
-- no computation, no floats, no imports beyond the standard library (§3.2
constants-are-stdlib-only doctrine), and no import of another constants
module (mirrors ``constants/content.py``'s independent-declaration
precedent for cross-module values that must stay byte-identical).

Role-id namespace note: ``PAGE_ROLE_HOME``/``PAGE_ROLE_CATEGORY`` below name
the same two ``PagePlan.page_type`` values the Information Architecture
Engine declares (``constants/ia.py``'s ``PAGE_ROLE_HOME`` /
``PAGE_ROLE_CATEGORY``). Per the constants-are-stdlib-only doctrine this
module may not import ``constants/ia.py``, so the values are independently
declared here and must stay byte-identical to their ``constants/ia.py``
counterparts; a cross-module consistency test enforces the equality.

Role rule tables (AES-WEB-002J.5 D2/D1): per-role source-slot lookup for the
title and meta-description compilers, in the same "add-an-entry-not-a-branch"
style as ``constants/content.py``'s ``SLOT_MIN_LENGTHS``/``SLOT_MAX_LENGTHS``
and ``constants/brand.py``'s per-family dict-keyed tables (``PALETTES``,
``TYPE_SCALES``, ...). Both MVP roles read the same two slots today; a
future role with different slot needs is a new table entry, never a new
branch in the engine. A ``PagePlan.page_type`` absent from these tables is
always a deterministic ``unsupported_page_types`` validation error -- the
engine never falls back to a default slot silently.
"""

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Named limits (Phase 1 values, byte-identical; consumed by the SEO Engine)
# ---------------------------------------------------------------------------

TITLE_MAX_LENGTH = 60
META_DESCRIPTION_MAX_LENGTH = 160
META_DESCRIPTION_MIN_LENGTH = 50
CANONICAL_URL_MAX_LENGTH = 2048
SITEMAP_FILENAME = "sitemap.xml"
ROBOTS_FILENAME = "robots.txt"

# ---------------------------------------------------------------------------
# Title composition (AES-WEB-002J.5 Decision D2)
# ---------------------------------------------------------------------------

# The separator is literal: space, pipe, space.
TITLE_SEPARATOR = " | "

# Documentation of the composition rule (not used for string formatting --
# the engine composes with plain concatenation): "{hero_h1} | {business_name}".
TITLE_TEMPLATE = "{hero_h1}" + TITLE_SEPARATOR + "{business_name}"

# ---------------------------------------------------------------------------
# Content-slot sources (Decisions D1/D2). Independently declared, must stay
# byte-identical to constants/content.py's SLOT_HERO_H1/SLOT_INTRO and
# constants/ia.py's CONTENT_SLOT_HERO_H1/CONTENT_SLOT_INTRO.
# ---------------------------------------------------------------------------

TITLE_SOURCE_SLOT = "hero_h1"
META_SOURCE_SLOT = "intro"

# ---------------------------------------------------------------------------
# Page roles (independently declared; must stay byte-identical to
# constants/ia.py's PAGE_ROLE_HOME/PAGE_ROLE_CATEGORY, and (AES-WEB-002K.1)
# information_architecture_engine.PAGE_ROLE_BUSINESS_PROFILE -- see module
# docstring).
# ---------------------------------------------------------------------------

PAGE_ROLE_HOME = "home"
PAGE_ROLE_CATEGORY = "category"
# AES-WEB-002K.1: IA now emits business-profile pages (an optional
# listing_dataset input), and those pages need a real <title>/meta
# description too -- same D1/D2 hero_h1/intro source slots, no new rule
# needed. Not a schema change: this table is declarative Python data, never
# a registered artifact.
PAGE_ROLE_BUSINESS_PROFILE = "business-profile"

# Per-role source-slot rule tables (D1/D2). Keys are the complete set of
# ``PagePlan.page_type`` values the SEO Engine supports; a page_type absent
# from these tables is an ``unsupported_page_types`` validation error.
TITLE_SOURCE_SLOT_BY_ROLE: Dict[str, str] = {
    PAGE_ROLE_HOME: TITLE_SOURCE_SLOT,
    PAGE_ROLE_CATEGORY: TITLE_SOURCE_SLOT,
    PAGE_ROLE_BUSINESS_PROFILE: TITLE_SOURCE_SLOT,
}

META_SOURCE_SLOT_BY_ROLE: Dict[str, str] = {
    PAGE_ROLE_HOME: META_SOURCE_SLOT,
    PAGE_ROLE_CATEGORY: META_SOURCE_SLOT,
    PAGE_ROLE_BUSINESS_PROFILE: META_SOURCE_SLOT,
}

# The complete set of page roles the SEO Engine supports -- the two tables
# above always share the same key set (enforced by test).
SUPPORTED_PAGE_ROLES: Tuple[str, ...] = tuple(sorted(TITLE_SOURCE_SLOT_BY_ROLE))

# ---------------------------------------------------------------------------
# Robots plan (Decision D5): a fixed, site-level allow-all plan. A plan
# only -- file emission belongs to Assembly (a later, unauthorized phase).
# ---------------------------------------------------------------------------

ROBOTS_DIRECTIVES: Tuple[str, ...] = ("User-agent: *", "Allow: /")

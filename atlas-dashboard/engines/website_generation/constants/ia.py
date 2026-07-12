"""Information Architecture constants (AES-WEB-001 §5.3 / Part 2 / Part 13
Phase 2; internal sequencing label AES-WEB-002J.3).

Route grammar and the minimal per-role content-slot vocabulary the
Information Architecture Engine declares. Constants only -- no computation,
no imports beyond the standard library (§3.2 constants-are-stdlib-only
doctrine). ``engines/website_generation/ia/`` is the only consumer.

Tree amendment (operator decision carried through the AES-WEB-002J.3
delivery): AES-WEB-001 Part 2 does not name a ``constants/ia.py`` module;
this file is authorized as an additive companion to the ``ia/`` package,
following the ``constants/brand.py`` precedent added alongside ``brand/``
in AES-WEB-002J.2.

Content-slot vocabulary is a namespace distinct from component-recipe
``slot_id``\\ s (``constants/components.py``): these name raw content
placeholders the (future) Content Engine must fill, keyed by
``(page_route, slot_id)`` on ``ContentCandidate``/``ContentBlock`` -- never
a component's internal slot needs. Deliberately minimal for the current
(home, category)-only page universe (approved operator decision); a later
phase may extend this vocabulary as new page roles are authorized.
"""

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Route grammar (AES-WEB-001 §5.3: "routes are normalized, unique, and
# stable-sorted")
# ---------------------------------------------------------------------------

HOME_ROUTE = "/"

# Category routes are "/<slug>/": single path segment, trailing slash.
CATEGORY_ROUTE_TEMPLATE = "/%s/"

# ---------------------------------------------------------------------------
# Minimal content-slot vocabulary (AES-WEB-001 §5.3: "every page declares
# its content slots -- typed placeholders the content stage must fill").
# Page-role values are plain strings here (matching PagePlan.page_type's
# str typing); constants/ may not import contracts/enums.PageRole.
# ---------------------------------------------------------------------------

PAGE_ROLE_HOME = "home"
PAGE_ROLE_CATEGORY = "category"

CONTENT_SLOT_HERO_H1 = "hero_h1"
CONTENT_SLOT_INTRO = "intro"

CONTENT_SLOTS_BY_ROLE: Dict[str, Tuple[str, ...]] = {
    PAGE_ROLE_HOME: (CONTENT_SLOT_HERO_H1, CONTENT_SLOT_INTRO),
    PAGE_ROLE_CATEGORY: (CONTENT_SLOT_HERO_H1, CONTENT_SLOT_INTRO),
}

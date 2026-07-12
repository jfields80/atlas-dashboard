"""Brand token taxonomy constants (AES-WEB-001 §5.2 / Part 2 / Part 13
Phase 2; internal sequencing label AES-WEB-002J.2).

Every value here is authored, deterministic, and a plain string or integer
— no floats, no clock, no randomness (§3.2 constants-are-stdlib-only
doctrine: this module imports nothing beyond ``typing``). The Brand Engine
(``engines/website_generation/brand/``) is the only consumer; it maps the
bare per-family token ids below onto full token ids (``color.``,
``typography.``, ``spacing.``, ``radius.`` prefixes, everything else
unprefixed into ``extended_tokens``) and assembles the final
``BrandPackage``.

Four authored brand families (AES-WEB-001 §5.2 "palette selection ...
seeded from stable spec attributes"; classification keyword tables below):

* ``field_guide`` — travel/outdoor/place businesses (PetTripFinder's home).
* ``civic_slate`` — professional/legal/B2B services.
* ``market_clay`` — local commerce, food, craft, market.
* ``harbor_ink`` — data/finance/technology/analytics, and the fallback
  family when no keyword matches.

Every color pairing enumerated in ``SANCTIONED_CONTRAST_PAIRS`` clears its
required WCAG 2.x threshold for all four families (verified independently
against the standard relative-luminance formula; worst observed margin is
65 hundredths, i.e. 0.65:1, against the required minimum).
"""

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Token grouping (Phase 1 names retained verbatim; extended additively)
# ---------------------------------------------------------------------------

TOKEN_GROUP_PALETTE = "palette"
TOKEN_GROUP_TYPE_SCALE = "type_scale"
TOKEN_GROUP_SPACING_SCALE = "spacing_scale"
TOKEN_GROUP_RADIUS_SCALE = "radius_scale"
TOKEN_GROUP_EXTENDED_TOKENS = "extended_tokens"

TOKEN_GROUPS = (
    TOKEN_GROUP_PALETTE,
    TOKEN_GROUP_TYPE_SCALE,
    TOKEN_GROUP_SPACING_SCALE,
    TOKEN_GROUP_RADIUS_SCALE,
    TOKEN_GROUP_EXTENDED_TOKENS,
)

# Full-token-id prefixes routing a resolved token into its BrandPackage
# field (§5.2 token mapping): color.* -> palette, typography.* -> type_scale,
# spacing.* -> spacing_scale, radius.* -> radius_scale, everything else ->
# extended_tokens.
TOKEN_PREFIX_COLOR = "color."
TOKEN_PREFIX_TYPOGRAPHY = "typography."
TOKEN_PREFIX_SPACING = "spacing."
TOKEN_PREFIX_RADIUS = "radius."

# ---------------------------------------------------------------------------
# Brand families and deterministic classification
# ---------------------------------------------------------------------------

FAMILY_FIELD_GUIDE = "field_guide"
FAMILY_CIVIC_SLATE = "civic_slate"
FAMILY_MARKET_CLAY = "market_clay"
FAMILY_HARBOR_INK = "harbor_ink"

# Fixed ordered rule table (documented precedence; first family with at
# least one keyword hit in the spec's keyword bag wins). harbor_ink is both
# a normal keyword-matched family and the designated fallback when nothing
# else matches.
FAMILY_ORDER: Tuple[str, ...] = (
    FAMILY_FIELD_GUIDE,
    FAMILY_CIVIC_SLATE,
    FAMILY_MARKET_CLAY,
    FAMILY_HARBOR_INK,
)

FAMILY_FALLBACK = FAMILY_HARBOR_INK

# Keyword bags are lower-case substrings checked against the lower-cased,
# space-joined (niche, audience, value_proposition, sorted directory
# taxonomy) text — never business_name (§5.2 classification decision).
FAMILY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    FAMILY_FIELD_GUIDE: (
        "travel",
        "outdoor",
        "destination",
        "park",
        "trail",
        "hotel",
        "stay",
        "pet-friendly",
    ),
    FAMILY_CIVIC_SLATE: (
        "professional",
        "legal",
        "services",
        "b2b",
    ),
    FAMILY_MARKET_CLAY: (
        "local commerce",
        "food",
        "craft",
        "market",
    ),
    FAMILY_HARBOR_INK: (
        "data",
        "finance",
        "technology",
        "analytics",
    ),
}

# ---------------------------------------------------------------------------
# Banned voice language (§5.2 voice profile — never emitted)
# ---------------------------------------------------------------------------

BANNED_VOICE_PHRASES: Tuple[str, ...] = (
    "pawsome",
    "pawfect",
    "furbaby",
    "unleash",
    "discover the best",
    "your trusted partner",
)

# ---------------------------------------------------------------------------
# Voice register fragments (one per family; spec-derived specifics are
# interpolated by token_resolver.build_voice_profile)
# ---------------------------------------------------------------------------

VOICE_REGISTER_FIELD_GUIDE = (
    "Register: mature travel-guide, practical and verification-first. "
    "Warmth: friendly but not childish -- confident guidance, not gushing "
    "enthusiasm. Sentence style: short declarative sentences leading with "
    "the concrete detail (what is verified, what it costs, who it suits). "
    "Specificity: names neighborhoods, amenities, and policies rather than "
    "vague superlatives. Forbidden: no pet puns, no exclamation-point "
    "salesmanship, and none of the banned generic phrases."
)

VOICE_REGISTER_CIVIC_SLATE = (
    "Register: professional and precise, service-oriented without being "
    "stiff. Warmth: respectful and measured -- competence conveyed through "
    "clarity, not enthusiasm. Sentence style: structured sentences that "
    "state the service, the credential, and the outcome in order. "
    "Specificity: names credentials, service areas, and process steps "
    "rather than vague claims of excellence. Forbidden: no hype "
    "superlatives and none of the banned generic phrases."
)

VOICE_REGISTER_MARKET_CLAY = (
    "Register: warm local-commerce voice, neighborly and specific. "
    "Warmth: genuinely welcoming -- like a knowledgeable regular, not a "
    "billboard. Sentence style: conversational sentences that name the "
    "maker, the ingredient, or the craft behind the offering. Specificity: "
    "names products, makers, and provenance rather than generic praise. "
    "Forbidden: no cliche discovery openings and none of the banned "
    "generic phrases."
)

VOICE_REGISTER_HARBOR_INK = (
    "Register: neutral, analytical, data-forward. Warmth: respectful and "
    "understated -- credibility from precision, not persuasion. Sentence "
    "style: direct sentences that lead with the metric, the capability, or "
    "the integration. Specificity: names figures, protocols, and "
    "capabilities rather than vague promises. Forbidden: no marketing "
    "bombast and none of the banned generic phrases."
)

VOICE_REGISTER_FRAGMENTS: Dict[str, str] = {
    FAMILY_FIELD_GUIDE: VOICE_REGISTER_FIELD_GUIDE,
    FAMILY_CIVIC_SLATE: VOICE_REGISTER_CIVIC_SLATE,
    FAMILY_MARKET_CLAY: VOICE_REGISTER_MARKET_CLAY,
    FAMILY_HARBOR_INK: VOICE_REGISTER_HARBOR_INK,
}

# ---------------------------------------------------------------------------
# Palettes — bare color-token id (no "color." prefix) -> lower-case hex.
# color.action.secondary equals the family's text.link value throughout.
# *.disabled values are authored low-saturation mixes, WCAG-exempt for
# disabled controls, and excluded from SANCTIONED_CONTRAST_PAIRS.
# ---------------------------------------------------------------------------

PALETTE_FIELD_GUIDE: Dict[str, str] = {
    "surface.page": "#faf7f0",
    "surface.raised": "#ffffff",
    "surface.elevated": "#ffffff",
    "surface.sponsored": "#f3ead9",
    "surface.featured": "#e9efe6",
    "surface.inverse": "#1e332a",
    "text.default": "#23312a",
    "text.muted": "#54655c",
    "text.inverse": "#f5f1e6",
    "text.link": "#1a5f8a",
    "text.error": "#9e2f26",
    "text.success": "#2c6240",
    "action.primary": "#2e5544",
    "action.primary.hover": "#254636",
    "action.primary.active": "#1e3a2d",
    "action.primary.disabled": "#a9b8ae",
    "action.secondary": "#1a5f8a",
    "border.default": "#d8d2c4",
    "border.strong": "#78837a",
    "focus.ring": "#b45309",
    "overlay.scrim": "#1e332a8c",
}

PALETTE_CIVIC_SLATE: Dict[str, str] = {
    "surface.page": "#f6f7f9",
    "surface.raised": "#ffffff",
    "surface.elevated": "#ffffff",
    "surface.sponsored": "#eef0f4",
    "surface.featured": "#e8ecf1",
    "surface.inverse": "#232a33",
    "text.default": "#252c35",
    "text.muted": "#535e6b",
    "text.inverse": "#eef1f5",
    "text.link": "#1f4f96",
    "text.error": "#a02c2c",
    "text.success": "#28623c",
    "action.primary": "#31435c",
    "action.primary.hover": "#283850",
    "action.primary.active": "#202d42",
    "action.primary.disabled": "#a7adb6",
    "action.secondary": "#1f4f96",
    "border.default": "#d5dae1",
    "border.strong": "#75808e",
    "focus.ring": "#8a4b0f",
    "overlay.scrim": "#232a338c",
}

PALETTE_MARKET_CLAY: Dict[str, str] = {
    "surface.page": "#faf5ef",
    "surface.raised": "#ffffff",
    "surface.elevated": "#ffffff",
    "surface.sponsored": "#f4e9dd",
    "surface.featured": "#efe9dc",
    "surface.inverse": "#33261d",
    "text.default": "#33291f",
    "text.muted": "#65584a",
    "text.inverse": "#f6efe6",
    "text.link": "#8a3e17",
    "text.error": "#9e2f26",
    "text.success": "#4f5d24",
    "action.primary": "#8a3e17",
    "action.primary.hover": "#743310",
    "action.primary.active": "#5f2a0d",
    "action.primary.disabled": "#c3b6a7",
    "action.secondary": "#8a3e17",
    "border.default": "#e0d6c8",
    "border.strong": "#8c7e69",
    "focus.ring": "#1f4f96",
    "overlay.scrim": "#33261d8c",
}

PALETTE_HARBOR_INK: Dict[str, str] = {
    "surface.page": "#f7f8f8",
    "surface.raised": "#ffffff",
    "surface.elevated": "#ffffff",
    "surface.sponsored": "#edf1f2",
    "surface.featured": "#e7eef0",
    "surface.inverse": "#17262b",
    "text.default": "#1d2b30",
    "text.muted": "#4e5f66",
    "text.inverse": "#edf2f4",
    "text.link": "#155e75",
    "text.error": "#a02c2c",
    "text.success": "#1f6e50",
    "action.primary": "#155e75",
    "action.primary.hover": "#114c5f",
    "action.primary.active": "#0d3c4b",
    "action.primary.disabled": "#a3b0b4",
    "action.secondary": "#155e75",
    "border.default": "#d3dbde",
    "border.strong": "#718289",
    "focus.ring": "#b45309",
    "overlay.scrim": "#17262b8c",
}

PALETTES: Dict[str, Dict[str, str]] = {
    FAMILY_FIELD_GUIDE: PALETTE_FIELD_GUIDE,
    FAMILY_CIVIC_SLATE: PALETTE_CIVIC_SLATE,
    FAMILY_MARKET_CLAY: PALETTE_MARKET_CLAY,
    FAMILY_HARBOR_INK: PALETTE_HARBOR_INK,
}

# ---------------------------------------------------------------------------
# Contrast evidence table — bare palette keys (as above), required
# thresholds in integer hundredths (450 = 4.50:1 for text; 300 = 3.00:1 for
# focus/border/UI). Revalidated live by BrandEngine.resolve() (§5.2).
# ---------------------------------------------------------------------------

CONTRAST_REQUIRED_TEXT = 450
CONTRAST_REQUIRED_UI = 300

SANCTIONED_CONTRAST_PAIRS: Tuple[Tuple[str, str, int], ...] = (
    ("text.default", "surface.page", CONTRAST_REQUIRED_TEXT),
    ("text.default", "surface.raised", CONTRAST_REQUIRED_TEXT),
    ("text.muted", "surface.page", CONTRAST_REQUIRED_TEXT),
    ("text.muted", "surface.raised", CONTRAST_REQUIRED_TEXT),
    ("text.default", "surface.sponsored", CONTRAST_REQUIRED_TEXT),
    ("text.default", "surface.featured", CONTRAST_REQUIRED_TEXT),
    ("text.inverse", "surface.inverse", CONTRAST_REQUIRED_TEXT),
    ("text.inverse", "action.primary", CONTRAST_REQUIRED_TEXT),
    ("text.inverse", "action.primary.hover", CONTRAST_REQUIRED_TEXT),
    ("text.inverse", "action.primary.active", CONTRAST_REQUIRED_TEXT),
    ("text.link", "surface.page", CONTRAST_REQUIRED_TEXT),
    ("text.link", "surface.raised", CONTRAST_REQUIRED_TEXT),
    ("text.error", "surface.page", CONTRAST_REQUIRED_TEXT),
    ("text.success", "surface.page", CONTRAST_REQUIRED_TEXT),
    ("focus.ring", "surface.page", CONTRAST_REQUIRED_UI),
    ("border.strong", "surface.page", CONTRAST_REQUIRED_UI),
    ("action.primary", "surface.page", CONTRAST_REQUIRED_UI),
)

# ---------------------------------------------------------------------------
# Typography — bare typography-token id -> CSS-shorthand-like string
# ("weight size/line-height family-stack[; extra-declarations]"). Sizes and
# weights per role are one shared modular scale; only the family stack (and
# the mono-influenced treatment for harbor_ink's price role) varies.
# ---------------------------------------------------------------------------

TYPE_SCALE_FIELD_GUIDE: Dict[str, str] = {
    "heading.display": "700 34px/1.15 Rockwell, 'Roboto Slab', Georgia, serif",
    "heading.2": "700 26px/1.2 Rockwell, 'Roboto Slab', Georgia, serif",
    "heading.3": "600 20px/1.3 Rockwell, 'Roboto Slab', Georgia, serif",
    "body.default": "400 16px/1.5 'Seravek', 'Noto Sans', 'Segoe UI', sans-serif",
    "label.default": "600 13px/1.4 'Seravek', 'Noto Sans', 'Segoe UI', sans-serif",
    "price.default": (
        "700 20px/1.2 'Seravek', 'Noto Sans', 'Segoe UI', sans-serif; "
        "font-variant-numeric: tabular-nums"
    ),
}

TYPE_SCALE_CIVIC_SLATE: Dict[str, str] = {
    "heading.display": "700 34px/1.15 'Source Serif Pro', Georgia, 'Times New Roman', serif",
    "heading.2": "700 26px/1.2 'Source Serif Pro', Georgia, 'Times New Roman', serif",
    "heading.3": "600 20px/1.3 'Source Serif Pro', Georgia, 'Times New Roman', serif",
    "body.default": "400 16px/1.5 'Segoe UI', Arial, 'Helvetica Neue', sans-serif",
    "label.default": "600 13px/1.4 'Segoe UI', Arial, 'Helvetica Neue', sans-serif",
    "price.default": (
        "700 20px/1.2 'Segoe UI', Arial, 'Helvetica Neue', sans-serif; "
        "font-variant-numeric: tabular-nums"
    ),
}

TYPE_SCALE_MARKET_CLAY: Dict[str, str] = {
    "heading.display": "700 34px/1.15 'Century Gothic', 'Poppins', 'Segoe UI', sans-serif",
    "heading.2": "700 26px/1.2 'Century Gothic', 'Poppins', 'Segoe UI', sans-serif",
    "heading.3": "600 20px/1.3 'Century Gothic', 'Poppins', 'Segoe UI', sans-serif",
    "body.default": "400 16px/1.5 'Segoe UI', 'Noto Sans', sans-serif",
    "label.default": "600 13px/1.4 'Segoe UI', 'Noto Sans', sans-serif",
    "price.default": (
        "700 20px/1.2 'Segoe UI', 'Noto Sans', sans-serif; "
        "font-variant-numeric: tabular-nums"
    ),
}

TYPE_SCALE_HARBOR_INK: Dict[str, str] = {
    "heading.display": "700 34px/1.15 'Inter', 'Helvetica Neue', Arial, sans-serif",
    "heading.2": "700 26px/1.2 'Inter', 'Helvetica Neue', Arial, sans-serif",
    "heading.3": "600 20px/1.3 'Inter', 'Helvetica Neue', Arial, sans-serif",
    "body.default": "400 16px/1.5 'Inter', Arial, sans-serif",
    "label.default": "600 13px/1.4 'Inter', Arial, sans-serif",
    "price.default": (
        "700 20px/1.2 'IBM Plex Mono', 'Roboto Mono', monospace; "
        "font-variant-numeric: tabular-nums"
    ),
}

TYPE_SCALES: Dict[str, Dict[str, str]] = {
    FAMILY_FIELD_GUIDE: TYPE_SCALE_FIELD_GUIDE,
    FAMILY_CIVIC_SLATE: TYPE_SCALE_CIVIC_SLATE,
    FAMILY_MARKET_CLAY: TYPE_SCALE_MARKET_CLAY,
    FAMILY_HARBOR_INK: TYPE_SCALE_HARBOR_INK,
}

# ---------------------------------------------------------------------------
# Spacing scale — shared across every family (bare spacing-token id -> px).
# ---------------------------------------------------------------------------

SPACING_SCALE: Dict[str, str] = {
    "section.small": "48px",
    "section.medium": "72px",
    "section.large": "104px",
    "stack.default": "16px",
    "inline.default": "8px",
}

# ---------------------------------------------------------------------------
# Radius scale — varies slightly per family (bare radius-token id -> px).
# ---------------------------------------------------------------------------

RADIUS_FIELD_GUIDE: Dict[str, str] = {
    "card": "10px",
    "control": "6px",
    "badge": "999px",
}

RADIUS_CIVIC_SLATE: Dict[str, str] = {
    "card": "4px",
    "control": "4px",
    "badge": "999px",
}

RADIUS_MARKET_CLAY: Dict[str, str] = {
    "card": "14px",
    "control": "8px",
    "badge": "999px",
}

RADIUS_HARBOR_INK: Dict[str, str] = {
    "card": "8px",
    "control": "6px",
    "badge": "999px",
}

RADIUS_SCALES: Dict[str, Dict[str, str]] = {
    FAMILY_FIELD_GUIDE: RADIUS_FIELD_GUIDE,
    FAMILY_CIVIC_SLATE: RADIUS_CIVIC_SLATE,
    FAMILY_MARKET_CLAY: RADIUS_MARKET_CLAY,
    FAMILY_HARBOR_INK: RADIUS_HARBOR_INK,
}

# ---------------------------------------------------------------------------
# Extended tokens — every remaining catalog domain (container, grid, border
# width/style, shadow, icon, focus-ring width/style, breakpoint, aspect).
# Shared across every family except image.treatment.default, authored per
# family in IMAGE_TREATMENT below.
# ---------------------------------------------------------------------------

SHARED_EXTENDED_TOKENS: Dict[str, str] = {
    "container.width.default": "1200px",
    "grid.columns.2": "repeat(2, minmax(0, 1fr))",
    "grid.columns.3": "repeat(3, minmax(0, 1fr))",
    "grid.columns.4": "repeat(4, minmax(0, 1fr))",
    "grid.gap.default": "24px",
    "border.default": "1px solid",
    "shadow.raised": "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)",
    "shadow.sticky": "0 -1px 4px rgba(0,0,0,0.10)",
    "icon.size.sm": "16px",
    "icon.size.md": "20px",
    "icon.size.lg": "24px",
    "focus.ring.default": "2px solid",
    "breakpoint.sm": "640px",
    "breakpoint.md": "1024px",
    "breakpoint.lg": "1280px",
    "aspect.card": "3:2",
    "aspect.hero": "16:9",
    "aspect.gallery": "4:3",
}

IMAGE_TREATMENT: Dict[str, str] = {
    FAMILY_FIELD_GUIDE: "duotone-spruce",
    FAMILY_CIVIC_SLATE: "flat-neutral",
    FAMILY_MARKET_CLAY: "warm-overlay",
    FAMILY_HARBOR_INK: "cool-duotone",
}

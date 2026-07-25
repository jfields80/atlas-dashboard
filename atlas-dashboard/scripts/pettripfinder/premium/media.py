"""PETTRIPFINDER-DESIGN-002 -- placeholder-first media system.

A single reusable media component with a view-model (``MediaSpec``) already
shaped for a later Google Places media phase, and a renderer that -- for now --
only ever produces intentional premium placeholders (states 2-8). No provider
is implemented here: no Google Places call, no API key, no Place ID resolution,
no remote download, no invented photography.

The placeholders are designed, not "broken image" fallbacks: a category-tinted
gradient wash, a soft brand pattern, a monogram, a category glyph, and honest
label/sublabel text. Every media region keeps a fixed aspect ratio so the
layout is stable whether a future photo or the placeholder fills it.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional

# Provider source types (only PLACEHOLDER / LOCAL are renderable in this phase).
SOURCE_PLACEHOLDER = "placeholder"
SOURCE_LOCAL = "local"
SOURCE_GOOGLE_PLACES = "google_places"   # reserved for a later phase; never rendered here

CATEGORY_HOTEL = "hotel"
CATEGORY_PARK = "park"
CATEGORY_RESTAURANT = "restaurant"
CATEGORY_CITY = "city"
CATEGORY_BRAND = "brand"


def _e(s: str) -> str:
    return html.escape(s or "", quote=True)


def _initials(name: str) -> str:
    words = re.sub(r"[^A-Za-z0-9 ]", " ", name or "").split()
    letters = [w[0] for w in words if w and w[0].isalpha()]
    return ("".join(letters[:2]) or "PT").upper()


# Category glyphs (inline SVG, currentColor, decorative). Deliberately simple,
# editorial line icons -- never a photographic claim.
_GLYPHS = {
    CATEGORY_HOTEL: (
        '<path d="M3 21V7l9-4 9 4v14"/><path d="M3 21h18"/><path d="M9 21v-5h6v5"/>'
        '<path d="M8 10h.01M12 10h.01M16 10h.01"/>'),
    CATEGORY_PARK: (
        '<path d="M12 3c3 2.5 4.5 5.5 4.5 8a4.5 4.5 0 0 1-9 0c0-2.5 1.5-5.5 4.5-8Z"/>'
        '<path d="M12 13v8"/>'),
    CATEGORY_RESTAURANT: (
        '<path d="M6 3v8a2 2 0 0 0 4 0V3"/><path d="M8 3v18"/>'
        '<path d="M17 3c-1.5 0-2.5 2-2.5 5s1 4 2.5 4v9"/>'),
    CATEGORY_CITY: (
        '<path d="M3 21V9l6-3v15"/><path d="M9 21V4l6 3v14"/><path d="M15 21V9l6 3v9"/>'
        '<path d="M3 21h18"/>'),
    CATEGORY_BRAND: (
        '<path d="M3 21V9l9-5 9 5v12"/><path d="M9 21v-6h6v6"/><path d="M3 21h18"/>'),
}


@dataclass(frozen=True)
class MediaSpec:
    """Media view-model. In this phase only ``source_type`` in
    {placeholder, local} renders; ``google_places`` fields are carried for a
    later provider and never trigger a network call here."""
    category: str = CATEGORY_HOTEL          # fallback_category / visual family
    label: str = ""                         # primary label (e.g. hotel name)
    sublabel: str = ""                       # secondary (e.g. corridor)
    initials: str = ""                       # monogram; derived from label when empty
    alt: str = ""                            # accessible description
    # --- future media object (not used to render in this phase) ---
    source_type: str = SOURCE_PLACEHOLDER
    source_id: str = ""                      # e.g. Google Place ID / asset id
    url: str = ""                            # image URL or local proxy route
    width: int = 0
    height: int = 0
    author_attribution: str = ""
    provider_attribution: str = ""
    loading_state: str = "idle"              # idle | loading | ready | error | missing

    def resolved_initials(self) -> str:
        return self.initials or _initials(self.label)

    def resolved_alt(self) -> str:
        if self.alt:
            return self.alt
        base = self.label or "PetTripFinder"
        return ("Branded placeholder for %s. No approved photograph is available; "
                "PetTripFinder shows a neutral placeholder rather than a stock or "
                "third-party photo." % base)


def render_media(spec: MediaSpec, *, ratio: str = "4x3", variant: str = "card",
                 glyph: bool = True, label: bool = True) -> str:
    """Render the media region for ``spec``.

    ``ratio``   -- aspect class: "4x3" | "3x2" | "16x9" | "1x1" | "hero".
    ``variant`` -- "card" | "hero" | "tile" | "thumb" (tunes label sizing/pattern).
    In this phase every spec renders an intentional placeholder (the provider is
    not implemented); a future photo would render inside the same fixed-ratio box.
    """
    cat = spec.category if spec.category in _GLYPHS else CATEGORY_BRAND
    glyph_svg = ""
    if glyph:
        glyph_svg = (
            '<svg class="pm-glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true">%s</svg>' % _GLYPHS[cat])
    mono = '<span class="pm-mono" aria-hidden="true">%s</span>' % _e(spec.resolved_initials())
    label_html = ""
    if label and (spec.label or spec.sublabel):
        sub = '<span class="pm-sub">%s</span>' % _e(spec.sublabel) if spec.sublabel else ""
        label_html = ('<span class="pm-label"><span class="pm-name">%s</span>%s</span>'
                      % (_e(spec.label), sub))
    # data-* hooks make it trivial for a later media phase to swap in a photo
    # without touching layout (the box, ratio, and alt are already declared).
    return (
        '<figure class="pm pm--%s pm--%s pm--r-%s" data-media-slot="%s" '
        'data-media-source="%s" data-media-category="%s" role="img" aria-label="%s">'
        '<span class="pm-wash" aria-hidden="true"></span>'
        '<span class="pm-inner">%s%s%s</span>'
        '</figure>'
    ) % (variant, cat, ratio.replace("x", "-"), cat, _e(spec.source_type), cat,
         _e(spec.resolved_alt()), glyph_svg, mono, label_html)

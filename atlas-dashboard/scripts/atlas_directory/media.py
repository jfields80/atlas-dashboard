"""Atlas Directory — placeholder-first media renderer (niche-agnostic).

Renders a fixed-ratio media region for a ``MediaSpec`` using only its visual
``family`` (never a domain category). In this phase it always produces an
intentional designed placeholder (gradient wash + monogram + line glyph);
``source_type`` values for a real provider are carried but never fetched here.
"""

from __future__ import annotations

import html
import re

from scripts.atlas_directory.config import (
    FAMILY_BRAND, FAMILY_CITY, FAMILY_NATURE, FAMILY_PRIMARY, FAMILY_WARM,
    VALID_FAMILIES,
)
from scripts.atlas_directory.viewmodels import MediaSpec


def _ea(s: str) -> str:
    return html.escape(s or "", quote=True)


def _initials(name: str) -> str:
    words = re.sub(r"[^A-Za-z0-9 ]", " ", name or "").split()
    letters = [w[0] for w in words if w and w[0].isalpha()]
    return ("".join(letters[:2]) or "AD").upper()


# Line glyphs (currentColor, decorative). Niche-agnostic keys; a config may map
# a category to any of these, or fall back to the family's default glyph.
GLYPHS = {
    "home": ('<path d="M3 21V7l9-4 9 4v14"/><path d="M3 21h18"/><path d="M9 21v-5h6v5"/>'
             '<path d="M8 10h.01M12 10h.01M16 10h.01"/>'),
    "leaf": ('<path d="M12 3c3 2.5 4.5 5.5 4.5 8a4.5 4.5 0 0 1-9 0c0-2.5 1.5-5.5 4.5-8Z"/>'
             '<path d="M12 13v8"/>'),
    "fork": ('<path d="M6 3v8a2 2 0 0 0 4 0V3"/><path d="M8 3v18"/>'
             '<path d="M17 3c-1.5 0-2.5 2-2.5 5s1 4 2.5 4v9"/>'),
    "city": ('<path d="M3 21V9l6-3v15"/><path d="M9 21V4l6 3v14"/><path d="M15 21V9l6 3v9"/>'
             '<path d="M3 21h18"/>'),
    "brand": ('<path d="M3 21V9l9-5 9 5v12"/><path d="M9 21v-6h6v6"/><path d="M3 21h18"/>'),
}
_FAMILY_DEFAULT_GLYPH = {
    FAMILY_PRIMARY: "home", FAMILY_NATURE: "leaf", FAMILY_WARM: "fork",
    FAMILY_CITY: "city", FAMILY_BRAND: "brand",
}


def render_media(spec: MediaSpec, *, ratio: str = "4x3", variant: str = "card",
                 glyph: bool = True, label: bool = True) -> str:
    fam = spec.family if spec.family in VALID_FAMILIES else FAMILY_BRAND
    glyph_key = spec.glyph or _FAMILY_DEFAULT_GLYPH[fam]
    glyph_svg = ""
    if glyph:
        glyph_svg = (
            '<svg class="pm-glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '%s</svg>' % GLYPHS.get(glyph_key, GLYPHS["brand"]))
    initials = spec.initials or _initials(spec.label)
    mono = '<span class="pm-mono" aria-hidden="true">%s</span>' % _ea(initials)
    label_html = ""
    if label and (spec.label or spec.sublabel):
        sub = '<span class="pm-sub">%s</span>' % _ea(spec.sublabel) if spec.sublabel else ""
        label_html = ('<span class="pm-label"><span class="pm-name">%s</span>%s</span>'
                      % (_ea(spec.label), sub))
    alt = spec.alt or (
        "Branded placeholder for %s. No approved photograph is available; a neutral "
        "placeholder is shown rather than a stock or third-party photo." % (spec.label or "this listing"))
    return (
        '<figure class="pm pm--%s pm--%s pm--r-%s" data-media-slot="%s" '
        'data-media-source="%s" role="img" aria-label="%s">'
        '<span class="pm-wash" aria-hidden="true"></span>'
        '<span class="pm-inner">%s%s%s</span></figure>'
    ) % (variant, fam, ratio.replace("x", "-"), fam, _ea(spec.source_type), _ea(alt),
         glyph_svg, mono, label_html)

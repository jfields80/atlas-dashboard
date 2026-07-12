"""Pure resolution internals for the Brand Engine (AES-WEB-001 §5.2).

Family classification, token-scale assembly, WCAG 2.x contrast math, and
voice-profile assembly. Every function here is pure: no I/O, no clock, no
randomness, no AI. Internal floating-point math is used only for the WCAG
luminance/ratio computation (§5.2 permits this); the only value that ever
leaves this module for a canonical artifact is the integer
``floor(ratio * 100)``.

Family classification (fixed ordered rule table; documented, not guessed):
build a lower-case keyword bag from ``niche``, ``audience``,
``value_proposition``, and sorted ``directory_taxonomy`` (never
``business_name``). Walk ``FAMILY_ORDER``; the first family with at least
one keyword present in the bag wins. If no family's keywords match at all,
``FAMILY_FALLBACK`` (``harbor_ink``) is returned. If more than one family
matches (a spec's text happens to contain keywords from >=2 families), the
tie is broken deterministically by :func:`break_family_tie` — stable SHA-256
over a canonical fingerprint of the spec's stable fields, never Python
``hash()`` or randomness. The four authored families never actually tie
under this scheme (their keyword vocabularies are disjoint), but the
mechanism is real, reachable, and directly tested — not dead code reserved
for a case that can never occur.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from engines.website_generation.constants.brand import (
    FAMILY_FALLBACK,
    FAMILY_KEYWORDS,
    FAMILY_ORDER,
    IMAGE_TREATMENT,
    PALETTES,
    RADIUS_SCALES,
    SANCTIONED_CONTRAST_PAIRS,
    SHARED_EXTENDED_TOKENS,
    SPACING_SCALE,
    TOKEN_PREFIX_COLOR,
    TOKEN_PREFIX_RADIUS,
    TOKEN_PREFIX_SPACING,
    TOKEN_PREFIX_TYPOGRAPHY,
    TYPE_SCALES,
    VOICE_REGISTER_FRAGMENTS,
)
from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    ContrastEvidence,
    canonical_json,
    sha256_of_text,
)

# ---------------------------------------------------------------------------
# Family classification
# ---------------------------------------------------------------------------


def build_keyword_bag(spec: BusinessSpec) -> str:
    """Lower-case, space-joined classification text (§5.2).

    Drawn from ``niche``, ``audience``, ``value_proposition``, and sorted
    ``directory_taxonomy`` only — never ``business_name``.
    """
    parts = [spec.niche, spec.audience, spec.value_proposition]
    parts.extend(sorted(spec.directory_taxonomy))
    return " ".join(parts).lower()


def _family_matches(family: str, text: str) -> bool:
    return any(keyword in text for keyword in FAMILY_KEYWORDS[family])


def resolve_family(spec: BusinessSpec) -> str:
    """Classify ``spec`` into one of the four authored brand families."""
    text = build_keyword_bag(spec)
    matched = tuple(family for family in FAMILY_ORDER if _family_matches(family, text))
    if not matched:
        return FAMILY_FALLBACK
    if len(matched) == 1:
        return matched[0]
    return break_family_tie(matched, spec)


def _spec_fingerprint(spec: BusinessSpec) -> str:
    """Canonical, stable fingerprint of the fields classification depends on."""
    return canonical_json(
        {
            "business_name": spec.business_name,
            "niche": spec.niche,
            "audience": spec.audience,
            "value_proposition": spec.value_proposition,
            "directory_taxonomy": list(spec.directory_taxonomy),
        }
    )


def break_family_tie(candidates: Tuple[str, ...], spec: BusinessSpec) -> str:
    """Deterministic SHA-256 tie-break among fixed approved choices (§5.2).

    Never Python ``hash()``/randomness. Same ``candidates`` set (any order)
    and same spec always resolve to the same choice.
    """
    if len(candidates) == 1:
        return candidates[0]
    ordered = tuple(sorted(set(candidates)))
    if len(ordered) == 1:
        return ordered[0]
    digest = sha256_of_text(_spec_fingerprint(spec))
    index = int(digest[:8], 16) % len(ordered)
    return ordered[index]


# ---------------------------------------------------------------------------
# WCAG 2.x contrast math (internal floats; only the integer result escapes)
# ---------------------------------------------------------------------------


def _srgb_channel_to_linear(channel: int) -> float:
    c = channel / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")[:6]
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return (
        0.2126 * _srgb_channel_to_linear(r)
        + 0.7152 * _srgb_channel_to_linear(g)
        + 0.0722 * _srgb_channel_to_linear(b)
    )


def contrast_ratio_hundredths(hex_a: str, hex_b: str) -> int:
    """WCAG 2.x contrast ratio between two hex colors as ``floor(ratio*100)``.

    E.g. black vs. white is exactly 21:1 -> 2100; a color against itself is
    exactly 1:1 -> 100. Internal float math only; the integer is the only
    value that ever reaches a canonical artifact.
    """
    lum_a = _relative_luminance(hex_a)
    lum_b = _relative_luminance(hex_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return math.floor(ratio * 100)


def build_contrast_evidence(family: str) -> Tuple[ContrastEvidence, ...]:
    """Sorted, integer-only WCAG evidence for every sanctioned pair (§5.2)."""
    palette = PALETTES[family]
    evidence = []
    for foreground, background, required in SANCTIONED_CONTRAST_PAIRS:
        ratio_hundredths = contrast_ratio_hundredths(
            palette[foreground], palette[background]
        )
        evidence.append(
            ContrastEvidence(
                foreground_token=TOKEN_PREFIX_COLOR + foreground,
                background_token=TOKEN_PREFIX_COLOR + background,
                contrast_ratio_hundredths=ratio_hundredths,
                required_hundredths=required,
                passed=ratio_hundredths >= required,
            )
        )
    return tuple(
        sorted(evidence, key=lambda e: (e.foreground_token, e.background_token))
    )


# ---------------------------------------------------------------------------
# Token-scale assembly (bare per-family tables -> full prefixed token ids)
# ---------------------------------------------------------------------------


def build_palette_tokens(family: str) -> Dict[str, str]:
    return {TOKEN_PREFIX_COLOR + key: value for key, value in PALETTES[family].items()}


def build_type_scale_tokens(family: str) -> Dict[str, str]:
    return {
        TOKEN_PREFIX_TYPOGRAPHY + key: value
        for key, value in TYPE_SCALES[family].items()
    }


def build_spacing_tokens() -> Dict[str, str]:
    return {TOKEN_PREFIX_SPACING + key: value for key, value in SPACING_SCALE.items()}


def build_radius_tokens(family: str) -> Dict[str, str]:
    return {
        TOKEN_PREFIX_RADIUS + key: value
        for key, value in RADIUS_SCALES[family].items()
    }


def build_extended_tokens(family: str) -> Dict[str, str]:
    tokens = dict(SHARED_EXTENDED_TOKENS)
    tokens["image.treatment.default"] = IMAGE_TREATMENT[family]
    return tokens


# ---------------------------------------------------------------------------
# Voice profile (one deterministic string; §5.2)
# ---------------------------------------------------------------------------


def build_voice_profile(spec: BusinessSpec, family: str) -> str:
    taxonomy_text = ", ".join(sorted(spec.directory_taxonomy)) or "its core offering"
    monetization_text = spec.monetization_model or "no stated monetization model"
    return (
        "%s For %s: covers %s, monetized via %s, speaking directly to %s."
        % (
            VOICE_REGISTER_FRAGMENTS[family],
            spec.business_name,
            taxonomy_text,
            monetization_text,
            spec.audience,
        )
    )

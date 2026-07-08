"""Deterministic primitives shared by Directory Builder engines.

Pure functions only. Same input -> same output, forever. No randomness,
no clocks, no I/O.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from engines.directory_builder.constants import ID_HASH_LENGTH, SCORE_MAX, SCORE_MIN

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Deterministic ASCII slug: lowercase, hyphen-separated, no leading/trailing hyphens."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return _SLUG_STRIP.sub("-", normalized.lower()).strip("-")


def deterministic_id(prefix: str, *parts: str) -> str:
    """Stable ID derived from a canonical key. Never positional, never random."""
    canonical = "|".join(p.strip().lower() for p in parts)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:ID_HASH_LENGTH]
    return f"{prefix}-{digest}"


def fingerprint(payload: str) -> str:
    """Full sha256 hex fingerprint of a canonical payload string."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clamp_score(value: float) -> int:
    """Clamp a raw score into the [SCORE_MIN, SCORE_MAX] integer band."""
    return int(max(SCORE_MIN, min(SCORE_MAX, round(value))))


def truncate(value: str, max_length: int) -> str:
    """Deterministic truncation with no ellipsis surprises in exports."""
    return value if len(value) <= max_length else value[: max_length - 1].rstrip() + "…"

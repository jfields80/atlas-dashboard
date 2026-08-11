"""Domain-neutrality scan (AES-SEO-001 §7.5, §22.3).

Generic Demand Mapping engine code must contain no project or domain
literals — not in identifiers, not in strings, not in comments. The banned
markers are data (extensible per fixture, following the doctrine-as-data
precedent of ADR-PTF-AUTOMATED-BROWSING).

Matching is token-based, not substring-based: file text is lowered and
split into alphabetic runs, so ``pet`` is caught inside ``pet_fee`` (the
underscore separates tokens) while legitimate generic words that merely
contain a marker as a substring (``competition`` ⊃ ``pet``,
``category``/``categorical`` ⊃ ``cat``) never false-positive.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "engines" / "demand_mapping"

# The first validation fixture's project and domain vocabulary (§22.3).
# Extend this set when a new fixture domain is adopted.
BANNED_TOKENS: Set[str] = {
    "pettripfinder", "ptf",
    "pet", "pets",
    "hotel", "hotels", "lodging", "motel", "motels",
    "columbus", "ohio",
    "fee", "fees", "deposit", "deposits",
    "weight", "weights",
    "cat", "cats", "dog", "dogs", "species", "breed", "breeds",
}

_TOKEN = re.compile(r"[a-z]+")


def _tokens_of(path: Path) -> Set[str]:
    return set(_TOKEN.findall(path.read_text(encoding="utf-8").lower()))


class TestDomainNeutrality:
    def test_no_banned_tokens_in_engine_package(self):
        offenders: Dict[str, Set[str]] = {}
        modules = sorted(PACKAGE_ROOT.rglob("*.py"))
        assert modules, "engines/demand_mapping is missing or empty"
        for path in modules:
            hits = _tokens_of(path) & BANNED_TOKENS
            if hits:
                offenders[str(path.relative_to(REPO_ROOT))] = hits
        assert not offenders, (
            "domain/project literals found in generic engine code "
            "(AES-SEO-001 §7.5/§22.3): %r" % offenders
        )

    def test_scan_covers_all_file_content_kinds(self):
        # Self-check of the tokenizer: identifiers, strings, and comments
        # all reduce to tokens, and underscore-joined identifiers split.
        sample = "value_label = 'Example Text'  # explanatory comment"
        tokens = set(_TOKEN.findall(sample.lower()))
        assert {"value", "label", "example", "text", "comment"} <= tokens

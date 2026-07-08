"""
atlas/core/engine_versions.py

Engine Version Registry.

Every engine that participates in a scored pipeline run declares a
semver version string here.  Every persisted artifact (Prediction
Ledger row, run record) stores the full EngineVersionSet so that
historical calibration comparisons are version-partitioned — not a
mixed population of different heuristics.

Rules:
  - Bump a version string whenever a heuristic, weight, formula, or
    decision threshold changes inside that engine.
  - Never change a version string for a no-op refactor.
  - This file is the single source of truth for current versions.
  - EngineVersionSet is frozen; construct a new one if you need to
    represent a historical version set.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class EngineVersionSet:
    """
    Immutable snapshot of all engine versions active at pipeline execution
    time.  Stored verbatim in every run record and ledger snapshot.
    """
    # v2 core engines (frozen — do not bump without corresponding code change)
    scout:           str = "2.0.0"
    market_capacity: str = "2.0.0"
    scorer:          str = "2.0.0"
    valuation:       str = "2.0.0"
    architect:       str = "2.0.0"

    # v3 engines
    synergy:         str = "1.0.0"
    liquidity:       str = "1.0.0"
    classifier:      str = "1.0.0"
    committee:       str = "1.0.0"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    def as_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)

    def fingerprint(self) -> str:
        """
        Short deterministic hash of the full version set.
        Used as a compact identifier in log messages and run records.
        """
        raw = self.as_json().encode()
        return hashlib.sha256(raw).hexdigest()[:12]

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> "EngineVersionSet":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, s: str) -> "EngineVersionSet":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# The active version set used by the current pipeline.
# Import this constant — never construct EngineVersionSet inline in
# production code, or version tracking diverges from this registry.
# ---------------------------------------------------------------------------

CURRENT_VERSION_SET = EngineVersionSet()

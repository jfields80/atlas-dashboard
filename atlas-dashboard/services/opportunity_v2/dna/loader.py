"""
loader.py — YAML on disk is source of truth; mirrored to SQLite for query.

Design:
- YAML files in /industry_dna/*.yml are canonical (git-diffable, human-editable).
- Loader validates each YAML against the OpportunityDNA schema on load.
- Mirror table `opportunity_dna_profiles` stores serialized JSON keyed by slug;
  handy for admin UI / cross-profile queries later.
- Explicit `sync_all()` and `load(slug)` — no lazy magic that hides errors.

Validation is fail-loud. A bad DNA profile should crash the loader, not
silently degrade the engine's output.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml

from .schema import (OpportunityDNA, CustomerProfile, BuyingBehavior,
                       IntentProfile, EcosystemNode, EcosystemEdge,
                       SearchDimension, CommercialDNA, MonetizationStream,
                       AssetPreference, ScoringWeights, LearningRecord,
                       JourneyStage, BusinessModelOption,
                       Intensity, Cadence, BuyingCycle, PrimaryIntent, EdgeType)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DNA_DIR = PROJECT_ROOT / "industry_dna"
DB_PATH = PROJECT_ROOT / "atlas.db"


# ---------------------------------------------------------------------------
# YAML -> dataclass hydration. Enum strings become enum values; nested dicts
# become nested dataclasses; missing fields fall back to schema defaults.
# ---------------------------------------------------------------------------

_ENUM_FIELDS = {
    Intensity: {"supply_intensity", "directory_potential", "decision_complexity",
                 "customer_emotion", "trust_importance", "price_sensitivity",
                 "urgency_when_buying", "local_intent", "commercial_intent",
                 "review_importance", "visual_importance", "content_appetite",
                 "strength", "lead_value", "recurring_revenue_potential"},
    Cadence: {"purchase_cadence"},
    BuyingCycle: {"buying_cycle"},
    PrimaryIntent: {"primary_intent"},
    EdgeType: {"edge_type"},
}


def _coerce_enum(field_name: str, value: Any) -> Any:
    if not isinstance(value, str):
        return value
    for enum_cls, names in _ENUM_FIELDS.items():
        if field_name in names:
            try:
                return enum_cls(value)
            except ValueError:
                raise ValueError(f"Field '{field_name}' has invalid value '{value}'. "
                                  f"Expected one of {[e.value for e in enum_cls]}.")
    return value


def _hydrate(cls, data: dict):
    if data is None:
        return None
    if not is_dataclass(cls):
        return data
    kwargs = {}
    type_hints = None
    for f in fields(cls):
        if f.name not in data:
            continue
        raw = data[f.name]

        # Resolve annotations lazily; typing.get_type_hints is the reliable way
        if type_hints is None:
            import typing
            try:
                type_hints = typing.get_type_hints(cls)
            except Exception:
                type_hints = {}
        annot = type_hints.get(f.name, f.type)

        # list[SomeDataclass]
        origin = getattr(annot, "__origin__", None)
        if origin is list:
            args = getattr(annot, "__args__", ())
            if args and is_dataclass(args[0]):
                kwargs[f.name] = [_hydrate(args[0], item) for item in (raw or [])]
                continue
            kwargs[f.name] = raw or []
            continue

        # Optional[SomeDataclass] or direct dataclass
        if is_dataclass(annot):
            kwargs[f.name] = _hydrate(annot, raw)
            continue
        # Optional[X] resolves via __args__
        args = getattr(annot, "__args__", ())
        dc_arg = next((a for a in args if is_dataclass(a)), None)
        if dc_arg is not None and isinstance(raw, dict):
            kwargs[f.name] = _hydrate(dc_arg, raw)
            continue

        kwargs[f.name] = _coerce_enum(f.name, raw)
    return cls(**kwargs)


def _hydrate_dna(raw: dict) -> OpportunityDNA:
    """Explicit hydration for the top-level DNA — clearer than the generic
    path for the outer container, and handles the Optional[X] fields."""
    def sub(cls, key):
        return _hydrate(cls, raw.get(key)) if raw.get(key) else None

    def sub_list(cls, key):
        return [_hydrate(cls, item) for item in (raw.get(key) or [])]

    weights = raw.get("scoring_weights") or {}
    weights_obj = ScoringWeights(**{k: float(v) for k, v in weights.items()})

    learning_raw = raw.get("learning") or {}
    learning_obj = LearningRecord(**{
        "published_assets": learning_raw.get("published_assets", []),
        "observed_outcomes": learning_raw.get("observed_outcomes", []),
        "adjustment_history": learning_raw.get("adjustment_history", []),
        "frozen": learning_raw.get("frozen", True),
    })

    return OpportunityDNA(
        slug=raw["slug"], display_name=raw["display_name"],
        version=raw.get("version", "1.0"), author=raw.get("author", ""),
        summary=raw.get("summary", ""),
        customer=sub(CustomerProfile, "customer"),
        behavior=sub(BuyingBehavior, "behavior"),
        intent=sub(IntentProfile, "intent"),
        ecosystem_nodes=sub_list(EcosystemNode, "ecosystem_nodes"),
        ecosystem_edges=sub_list(EcosystemEdge, "ecosystem_edges"),
        search_dimensions=sub_list(SearchDimension, "search_dimensions"),
        commercial=sub(CommercialDNA, "commercial"),
        asset_preferences=sub_list(AssetPreference, "asset_preferences"),
        scoring_weights=weights_obj,
        seed_geography_hint=raw.get("seed_geography_hint"),
        learning=learning_obj,
    )


def validate(dna: OpportunityDNA) -> list[str]:
    """Returns a list of validation errors. Empty list = valid."""
    errors: list[str] = []
    if not dna.slug or " " in dna.slug:
        errors.append("slug must be non-empty and contain no spaces")
    node_names = {n.name for n in dna.ecosystem_nodes}
    for e in dna.ecosystem_edges:
        if e.from_node not in node_names:
            errors.append(f"edge from_node '{e.from_node}' not in ecosystem_nodes")
        if e.to_node not in node_names and e.to_node != dna.display_name:
            errors.append(f"edge to_node '{e.to_node}' not in ecosystem_nodes")
    w = dna.scoring_weights
    total = (w.search_demand + w.competition + w.directory_weakness
              + w.business_count + w.monetization + w.automation_fit)
    if not (0.95 <= total <= 1.05):
        errors.append(f"scoring_weights sum to {total:.3f}, expected ~1.0")
    if not dna.search_dimensions:
        errors.append("search_dimensions must contain at least one dimension")
    if not dna.commercial or not dna.commercial.streams:
        errors.append("commercial.streams must list at least one monetization stream")
    return errors


# ---------------------------------------------------------------------------
# Load / list / sync
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> OpportunityDNA:
    raw = yaml.safe_load(path.read_text())
    dna = _hydrate_dna(raw)
    errs = validate(dna)
    if errs:
        raise ValueError(f"Invalid DNA profile {path.name}: " + "; ".join(errs))
    return dna


def load(slug: str, dna_dir: Path | None = None) -> OpportunityDNA:
    dna_dir = dna_dir or DNA_DIR
    for path in dna_dir.glob("*.yml"):
        if path.stem == slug:
            return load_yaml(path)
    raise FileNotFoundError(f"No DNA profile with slug '{slug}' in {dna_dir}")


def list_profiles(dna_dir: Path | None = None) -> list[OpportunityDNA]:
    dna_dir = dna_dir or DNA_DIR
    return [load_yaml(p) for p in sorted(dna_dir.glob("*.yml"))]


# ---------------------------------------------------------------------------
# SQLite mirror
# ---------------------------------------------------------------------------

MIRROR_SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunity_dna_profiles (
    slug TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    version TEXT,
    author TEXT,
    summary TEXT,
    profile_json TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def _conn(db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _to_serializable(obj):
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(x) for x in obj]
    if hasattr(obj, "value") and hasattr(obj, "name"):  # Enum
        return obj.value
    return obj


def sync_all(dna_dir: Path | None = None, db_path=None) -> dict:
    """Load every YAML, validate, and upsert into the SQLite mirror.
    Returns {slug: 'ok' | error string} per profile."""
    with _conn(db_path) as c:
        c.executescript(MIRROR_SCHEMA)
    results: dict[str, str] = {}
    dna_dir = dna_dir or DNA_DIR
    for path in sorted(dna_dir.glob("*.yml")):
        try:
            dna = load_yaml(path)
            payload = json.dumps(_to_serializable(asdict(dna)))
            with _conn(db_path) as c:
                c.execute(
                    """INSERT INTO opportunity_dna_profiles
                       (slug, display_name, version, author, summary, profile_json, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                       ON CONFLICT(slug) DO UPDATE SET
                         display_name=excluded.display_name,
                         version=excluded.version,
                         author=excluded.author,
                         summary=excluded.summary,
                         profile_json=excluded.profile_json,
                         updated_at=CURRENT_TIMESTAMP""",
                    (dna.slug, dna.display_name, dna.version, dna.author,
                     dna.summary, payload))
            results[dna.slug] = "ok"
        except Exception as e:
            results[path.stem] = f"error: {e}"
    return results

"""ATLAS-WORKERS-001 -- configurable model pricing (Stage 5).

Pricing lives OUTSIDE the worker contract and outside validation logic: prices
are supplied at run time (a JSON file or an in-memory table), never hardcoded
into the schema or the validator. When no price is supplied for a model, cost
is reported as 0.0 with an explicit ``pricing_unknown`` signal rather than a
guessed number.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class ModelPricing:
    """USD per 1,000 tokens."""
    input_per_1k: float = 0.0
    output_per_1k: float = 0.0
    cached_input_per_1k: float = 0.0


def _key(provider: str, model: str) -> str:
    return "%s/%s" % (provider or "", model or "")


def load_pricing(path: Optional[str]) -> Dict[str, ModelPricing]:
    """Load a pricing table from JSON: {"provider/model": {"input_per_1k": ...}}."""
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: Dict[str, ModelPricing] = {}
    for k, v in data.items():
        out[k] = ModelPricing(
            input_per_1k=float(v.get("input_per_1k", 0.0)),
            output_per_1k=float(v.get("output_per_1k", 0.0)),
            cached_input_per_1k=float(v.get("cached_input_per_1k", 0.0)))
    return out


def pricing_for(table: Dict[str, ModelPricing], provider: str, model: str) -> Optional[ModelPricing]:
    return table.get(_key(provider, model)) or table.get(model)


def estimate_cost(pricing: Optional[ModelPricing], *, input_tokens: int, output_tokens: int,
                  cached_input_tokens: int = 0) -> float:
    if pricing is None:
        return 0.0
    billable_input = max(0, input_tokens - cached_input_tokens)
    return round(
        billable_input / 1000.0 * pricing.input_per_1k
        + cached_input_tokens / 1000.0 * pricing.cached_input_per_1k
        + output_tokens / 1000.0 * pricing.output_per_1k, 6)

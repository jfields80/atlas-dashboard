"""ATLAS-WORKERS-002 -- live model evaluation configuration.

The candidate low-cost models, their endpoints, credential env-var NAMES (never
values), and pricing METADATA. Pricing lives here (benchmark metadata), never in
validation logic. Prices are per MILLION tokens.

IMPORTANT: the prices below are conservative OPERATOR-SUPPLIED PLACEHOLDERS. They
are used only to compute a worst-case cost estimate for the $1.00 airlock ceiling
and cost-per-result reporting; the operator must confirm live prices before any
paid run. pricing_source records this explicitly.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from services.research_workers.pricing import ModelPricing
from services.research_workers.providers import ChatRequestOptions

PRICING_SOURCE = "operator_placeholder_unverified"
PRICING_OBSERVED_DATE = "2026-07-19"


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model_id: str
    base_url: str
    credential_env: str
    input_per_million: float
    output_per_million: float
    cached_input_per_million: float = 0.0
    max_output_tokens: int = 1024
    temperature: float = 0.0
    reasoning: str = "none"                    # provider-specific; "none" when not configurable
    # Chat-completions request shape (ATLAS-WORKERS-002 repair). The GPT-5
    # family requires max_completion_tokens and accepts only the default
    # temperature; the legacy defaults below fit DeepSeek's dialect.
    token_limit_param: str = "max_tokens"
    send_temperature: bool = True
    pricing_source: str = PRICING_SOURCE
    pricing_observed_date: str = PRICING_OBSERVED_DATE

    def to_dict(self) -> Dict:
        return dict(sorted(asdict(self).items()))

    def to_request_options(self) -> ChatRequestOptions:
        return ChatRequestOptions(token_limit_param=self.token_limit_param,
                                  send_temperature=self.send_temperature,
                                  temperature=self.temperature)

    def to_pricing(self) -> ModelPricing:
        # ModelPricing is per 1,000 tokens; config is per 1,000,000.
        return ModelPricing(
            input_per_1k=self.input_per_million / 1000.0,
            output_per_1k=self.output_per_million / 1000.0,
            cached_input_per_1k=self.cached_input_per_million / 1000.0)


# The first-round candidates (Grok intentionally excluded unless separately
# authorized). Explicit model IDs only -- no deprecated aliases.
DEFAULT_MODELS: List[ModelConfig] = [
    ModelConfig(provider="openai", model_id="gpt-5-nano-2025-08-07",
                base_url="https://api.openai.com/v1", credential_env="OPENAI_API_KEY",
                input_per_million=0.05, cached_input_per_million=0.005, output_per_million=0.40,
                token_limit_param="max_completion_tokens", send_temperature=False),
    ModelConfig(provider="deepseek", model_id="deepseek-v4-flash",
                base_url="https://api.deepseek.com/v1", credential_env="DEEPSEEK_API_KEY",
                input_per_million=0.14, cached_input_per_million=0.014, output_per_million=0.28),
    ModelConfig(provider="gemini", model_id="gemini-3.1-flash-lite",
                base_url="https://generativelanguage.googleapis.com/v1beta", credential_env="GEMINI_API_KEY",
                input_per_million=0.10, cached_input_per_million=0.025, output_per_million=0.40),
]

MODELS_BY_ID = {m.model_id: m for m in DEFAULT_MODELS}


# ATLAS-WORKERS-002 -- operator-selected single-model target. Standard API
# pricing per the official OpenAI GPT-5.4 Nano documentation (per MILLION
# tokens), operator-verified on the date below. Deliberately kept OUT of
# DEFAULT_MODELS so the default multi-model bakeoff is unchanged; this config is
# reachable only by an EXACT (provider, model_id) selection.
#
# base_url is OpenAI's canonical API root including the "/v1" segment because the
# adapter forms the endpoint as base_url + "/chat/completions"; a bare host would
# resolve to a non-existent path.
#
# Request shape (2026-07-20 diagnosis, verified against the operator's direct
# canary on this exact model): the GPT-5 family rejects the legacy "max_tokens"
# parameter (it requires "max_completion_tokens") and rejects any non-default
# "temperature" -- both were previously sent, so every call failed with HTTP 400
# invalid_request_error before a model response existed. Hence
# token_limit_param="max_completion_tokens" and send_temperature=False here; no
# reasoning-effort parameter is sent (the working direct canary sent none).
GPT_5_4_NANO_2026_03_17 = ModelConfig(
    provider="openai", model_id="gpt-5.4-nano-2026-03-17",
    base_url="https://api.openai.com/v1", credential_env="OPENAI_API_KEY",
    input_per_million=0.20, cached_input_per_million=0.02, output_per_million=1.25,
    token_limit_param="max_completion_tokens", send_temperature=False,
    pricing_source="Official OpenAI GPT-5.4 Nano model documentation",
    pricing_observed_date="2026-07-20")


# Every model the evaluate command may target by an EXACT (provider, model_id):
# the default bakeoff set plus the explicit single-model targets. Selection never
# falls back to a different model, snapshot, or undated alias.
AVAILABLE_MODELS: List[ModelConfig] = list(DEFAULT_MODELS) + [GPT_5_4_NANO_2026_03_17]


def select_model(provider: str, model_id: str) -> ModelConfig:
    """Return the one configured model whose provider AND model_id match exactly.

    Raises KeyError when there is no exact match -- the caller must surface that
    error and NEVER substitute a different model, snapshot, or undated alias.
    """
    for m in AVAILABLE_MODELS:
        if m.provider == provider and m.model_id == model_id:
            return m
    raise KeyError("no configured model for provider=%r model_id=%r" % (provider, model_id))


def pricing_table(models: Optional[List[ModelConfig]] = None) -> Dict[str, ModelPricing]:
    """provider/model_id -> ModelPricing, for services.research_workers.pricing."""
    return {"%s/%s" % (m.provider, m.model_id): m.to_pricing() for m in (models or DEFAULT_MODELS)}


def pricing_config_hash(models: Optional[List[ModelConfig]] = None) -> str:
    payload = [m.to_dict() for m in (models or DEFAULT_MODELS)]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()

"""
Scout Intelligence Memory Layer

This system does NOT run Scout.
It analyzes historical Scout outputs to detect:
- drift sources
- reliability degradation
- field instability
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ProviderDrift:
    provider: str
    verified_ratio: float
    estimated_ratio: float
    stability_score: float


@dataclass
class FieldStability:
    field: str
    reliability_score: float
    degradation_flag: bool


@dataclass
class ScoutMemoryReport:
    opportunity_id: int
    provider_drift: List[ProviderDrift]
    field_stability: List[FieldStability]
    overall_health_trend: str
    degradation_detected: bool


class ScoutIntelligenceMemory:

    def analyze(self, scout_runs: List[dict], opportunity_id: int) -> ScoutMemoryReport:

        provider_map: Dict[str, Dict[str, int]] = {}
        field_map: Dict[str, Dict[str, int]] = {}

        for run in scout_runs:
            findings = run.get("findings_json") or {}

            for provider in findings.get("provider_summaries", []):
                name = provider.get("provider", "unknown")

                if name not in provider_map:
                    provider_map[name] = {
                        "verified": 0,
                        "estimated": 0
                    }

                provider_map[name]["verified"] += len(provider.get("verified_fields", []))
                provider_map[name]["estimated"] += len(provider.get("estimated_fields", []))

                # field tracking
                for f in provider.get("verified_fields", []):
                    field_map.setdefault(f, {"good": 0, "bad": 0})
                    field_map[f]["good"] += 1

                for f in provider.get("estimated_fields", []):
                    field_map.setdefault(f, {"good": 0, "bad": 0})
                    field_map[f]["bad"] += 1

        provider_drift = []
        for provider, stats in provider_map.items():
            total = stats["verified"] + stats["estimated"]
            if total == 0:
                continue

            verified_ratio = stats["verified"] / total
            estimated_ratio = stats["estimated"] / total

            stability = verified_ratio - estimated_ratio

            provider_drift.append(ProviderDrift(
                provider=provider,
                verified_ratio=verified_ratio,
                estimated_ratio=estimated_ratio,
                stability_score=stability
            ))

        field_stability = []
        for field, stats in field_map.items():
            total = stats["good"] + stats["bad"]
            score = stats["good"] / total if total else 0

            field_stability.append(FieldStability(
                field=field,
                reliability_score=score,
                degradation_flag=score < 0.5
            ))

        degradation_detected = any(
            p.stability_score < 0 for p in provider_drift
        ) or any(
            f.degradation_flag for f in field_stability
        )

        trend = (
            "degrading" if degradation_detected else "stable"
        )

        return ScoutMemoryReport(
            opportunity_id=opportunity_id,
            provider_drift=provider_drift,
            field_stability=field_stability,
            overall_health_trend=trend,
            degradation_detected=degradation_detected
        )
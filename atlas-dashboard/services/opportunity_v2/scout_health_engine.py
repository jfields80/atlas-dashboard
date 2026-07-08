# services/opportunity_v2/scout_health_engine.py

from dataclasses import dataclass


@dataclass
class ScoutHealthScore:
    opportunity_id: int
    total_fields: int
    verified_fields: int
    estimated_fields: int
    unknown_fields: int

    provider_verified_ratio: float
    completeness_ratio: float
    health_score: float


class ScoutHealthEngine:

    def compute(self, scout_result, opportunity_id: int) -> ScoutHealthScore:
        verified = 0
        estimated = 0
        unknown = 0
        total = 0

        # flatten provider summaries
        for summary in scout_result.provider_summaries:
            verified += len(summary.verified_fields or [])
            estimated += len(summary.estimated_fields or [])
            unknown += len(summary.unknown_fields or [])

        total = verified + estimated + unknown

        if total == 0:
            return ScoutHealthScore(
                opportunity_id=opportunity_id,
                total_fields=0,
                verified_fields=0,
                estimated_fields=0,
                unknown_fields=0,
                provider_verified_ratio=0.0,
                completeness_ratio=0.0,
                health_score=0.0,
            )

        provider_verified_ratio = verified / total
        completeness_ratio = (verified + estimated) / total

        # weighted health score (simple but stable)
        health_score = (
            (provider_verified_ratio * 0.6) +
            (completeness_ratio * 0.4)
        ) * 100

        return ScoutHealthScore(
            opportunity_id=opportunity_id,
            total_fields=total,
            verified_fields=verified,
            estimated_fields=estimated,
            unknown_fields=unknown,
            provider_verified_ratio=provider_verified_ratio,
            completeness_ratio=completeness_ratio,
            health_score=health_score,
        )
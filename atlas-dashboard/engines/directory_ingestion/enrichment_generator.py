"""
Module 5 — Enrichment Task Generator
====================================

Generates deterministic work items ("future AI Employee jobs") from gaps in
each normalized listing plus its quality score.

Rules are explicit and ordered; task ids are stable hashes so replaying the
pipeline never mints new ids for the same work.
"""

from __future__ import annotations

import hashlib
from typing import Callable, Optional

from engines.directory_ingestion.ingestion_models import (
    EnrichmentTask,
    EnrichmentTaskType,
    NormalizedListing,
    QualityScore,
    TaskPriority,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

_DESCRIPTION_MIN_CHARS = 80

# A listing scoring at/above this on monetization readiness is worth a
# premium-candidate research pass.
_PREMIUM_CANDIDATE_MONETIZATION_MIN = 70
_PREMIUM_CANDIDATE_OVERALL_MIN = 70

# Address verification is requested when location accuracy is below this.
_ADDRESS_VERIFY_LOCATION_MAX = 60


_Rule = tuple[
    EnrichmentTaskType,
    TaskPriority,
    Callable[[NormalizedListing, QualityScore], Optional[str]],
]


def _rule_find_website(l: NormalizedListing, _q: QualityScore) -> Optional[str]:
    return "Website missing" if not l.website.value else None


def _rule_find_phone(l: NormalizedListing, _q: QualityScore) -> Optional[str]:
    return "Phone missing" if not l.phone.value else None


def _rule_find_email(l: NormalizedListing, _q: QualityScore) -> Optional[str]:
    return "Email missing" if not l.email.value else None


def _rule_write_description(l: NormalizedListing, _q: QualityScore) -> Optional[str]:
    if not l.description.value:
        return "Description missing"
    if len(l.description.value) < _DESCRIPTION_MIN_CHARS:
        return f"Description under {_DESCRIPTION_MIN_CHARS} chars"
    return None


def _rule_categorize(l: NormalizedListing, _q: QualityScore) -> Optional[str]:
    return "No categories assigned" if not l.categories else None


def _rule_verify_address(l: NormalizedListing, q: QualityScore) -> Optional[str]:
    if q.location_accuracy < _ADDRESS_VERIFY_LOCATION_MAX:
        return f"Location accuracy {q.location_accuracy} below {_ADDRESS_VERIFY_LOCATION_MAX}"
    return None


def _rule_find_photos(l: NormalizedListing, _q: QualityScore) -> Optional[str]:
    # Phase 3B schema carries no media; every listing needs photo sourcing.
    return "No photo pipeline in Phase 3B — photos required before launch"


def _rule_find_owner(l: NormalizedListing, q: QualityScore) -> Optional[str]:
    if q.monetization_readiness >= _PREMIUM_CANDIDATE_MONETIZATION_MIN:
        return "Monetizable listing — owner contact needed for outreach"
    return None


def _rule_find_social(l: NormalizedListing, _q: QualityScore) -> Optional[str]:
    return "Social profiles not captured in ingestion schema"


def _rule_premium_candidate(l: NormalizedListing, q: QualityScore) -> Optional[str]:
    if (
        q.monetization_readiness >= _PREMIUM_CANDIDATE_MONETIZATION_MIN
        and q.overall >= _PREMIUM_CANDIDATE_OVERALL_MIN
    ):
        return (
            f"overall={q.overall}, monetization={q.monetization_readiness} — "
            "evaluate for premium placement"
        )
    return None


# Rule table: evaluation order is fixed and part of the engine contract.
_RULES: tuple[_Rule, ...] = (
    (EnrichmentTaskType.FIND_WEBSITE, TaskPriority.HIGH, _rule_find_website),
    (EnrichmentTaskType.FIND_PHONE, TaskPriority.HIGH, _rule_find_phone),
    (EnrichmentTaskType.FIND_EMAIL, TaskPriority.MEDIUM, _rule_find_email),
    (EnrichmentTaskType.WRITE_DESCRIPTION, TaskPriority.MEDIUM, _rule_write_description),
    (EnrichmentTaskType.CATEGORIZE_BUSINESS, TaskPriority.HIGH, _rule_categorize),
    (EnrichmentTaskType.VERIFY_ADDRESS, TaskPriority.MEDIUM, _rule_verify_address),
    (EnrichmentTaskType.FIND_PHOTOS, TaskPriority.LOW, _rule_find_photos),
    (EnrichmentTaskType.FIND_OWNER, TaskPriority.MEDIUM, _rule_find_owner),
    (EnrichmentTaskType.FIND_SOCIAL_MEDIA, TaskPriority.LOW, _rule_find_social),
    (EnrichmentTaskType.FIND_PREMIUM_CANDIDATE, TaskPriority.HIGH, _rule_premium_candidate),
)


class EnrichmentTaskGenerator:
    """Stateless generator of enrichment work items."""

    def generate(
        self, listing: NormalizedListing, quality: QualityScore
    ) -> list[EnrichmentTask]:
        tasks: list[EnrichmentTask] = []
        for task_type, priority, rule in _RULES:
            rationale = rule(listing, quality)
            if rationale is None:
                continue
            tasks.append(
                EnrichmentTask(
                    task_id=self._task_id(listing.listing_id, task_type),
                    listing_id=listing.listing_id,
                    task_type=task_type,
                    priority=priority,
                    rationale=rationale,
                )
            )
        return tasks

    def generate_batch(
        self,
        listings: list[NormalizedListing],
        scores_by_listing: dict[str, QualityScore],
    ) -> list[EnrichmentTask]:
        tasks: list[EnrichmentTask] = []
        for listing in listings:
            quality = scores_by_listing[listing.listing_id]
            tasks.extend(self.generate(listing, quality))
        # Deterministic queue ordering: priority, then task type, then listing.
        priority_order = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}
        tasks.sort(key=lambda t: (priority_order[t.priority], t.task_type.value, t.listing_id))
        return tasks

    @staticmethod
    def _task_id(listing_id: str, task_type: EnrichmentTaskType) -> str:
        digest = hashlib.sha256(f"{listing_id}::{task_type.value}".encode()).hexdigest()
        return f"tsk_{digest[:16]}"

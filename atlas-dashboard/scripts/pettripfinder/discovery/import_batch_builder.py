"""AES-DATA-004C Task 11 -- deterministic official-site import batch
manifests, in the exact schema
``scripts.pettripfinder.importer.batch.BatchJob``/manifest expect, so a
later phase can hand these to ``scripts/run_import_batch.py`` unmodified.
Not executed in this phase.

Only READY_FOR_PET_POLICY_IMPORT / READY_WITH_BRAND_SUPPLEMENT candidates
with a resolved, official, non-third-party URL are included. Never carries
pet-policy assumptions, expected READY status, ratings/reviews, or
provider-category claims as verified facts -- a batch job is only ever
``(job_id, candidate_name, category, expected_city, expected_state, urls)``
plus optional relationship hints, exactly the importer's own contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, WebsiteResolution


@dataclass(frozen=True)
class ImportJob:
    job_id: str
    candidate_name: str
    category: str
    expected_city: str
    expected_state: str
    urls: Tuple[str, ...]
    source_relationship_hint: str = ""
    source_type_hint: str = ""
    static_fixtures: Tuple[str, ...] = ()
    enabled: bool = True
    discovery_candidate_id: str = ""    # provenance only -- not a BatchJob field


def _canonical_category(discovery_category: str) -> str:
    # The importer has no separate "motels" category -- both map to its
    # single "hotels" lodging category (disclosed, deliberate).
    return C.IMPORTER_CATEGORY_HOTELS


def build_import_job(
    candidate: DiscoveryCandidate, *, resolved_url: str, is_confirmed: bool,
) -> ImportJob:
    job_id = candidate.candidate_id   # already matches ^[a-z0-9][a-z0-9_-]{0,63}$
    return ImportJob(
        job_id=job_id, candidate_name=candidate.name,
        category=_canonical_category(candidate.category_candidates[0] if candidate.category_candidates else ""),
        expected_city=candidate.city, expected_state=candidate.state,
        urls=(resolved_url,),
        source_relationship_hint="EXACT_ENTITY_DOMAIN" if is_confirmed else "",
        discovery_candidate_id=candidate.candidate_id,
    )


def build_batches(
    jobs: Sequence[ImportJob], *, batch_id_prefix: str, batch_name_prefix: str,
    max_jobs_per_batch: int = C.RESOLUTION_MAX_JOBS_PER_BATCH,
) -> Tuple[dict, ...]:
    """Stable ordering (sorted by job_id), deterministic batch IDs, no
    duplicate locations within or across batches."""
    ordered = sorted(jobs, key=lambda j: j.job_id)
    seen_ids = set()
    deduped = []
    for j in ordered:
        if j.job_id in seen_ids:
            continue
        seen_ids.add(j.job_id)
        deduped.append(j)

    manifests = []
    for i in range(0, len(deduped), max_jobs_per_batch):
        chunk = deduped[i:i + max_jobs_per_batch]
        batch_number = i // max_jobs_per_batch + 1
        batch_id = "%s-%03d" % (batch_id_prefix, batch_number)
        manifests.append({
            "manifest_schema_version": C.RESOLUTION_MANIFEST_SCHEMA_VERSION,
            "batch_id": batch_id,
            "batch_name": "%s %03d" % (batch_name_prefix, batch_number),
            "defaults": {},
            "jobs": [
                {
                    "job_id": j.job_id, "candidate_name": j.candidate_name,
                    "category": j.category, "expected_city": j.expected_city,
                    "expected_state": j.expected_state, "urls": list(j.urls),
                    "source_relationship_hint": j.source_relationship_hint,
                    "source_type_hint": j.source_type_hint,
                    "static_fixtures": list(j.static_fixtures), "enabled": j.enabled,
                }
                for j in chunk
            ],
        })
    return tuple(manifests)


def dumps_batch_manifest(manifest: dict) -> str:
    return json.dumps(manifest, sort_keys=True, indent=2)


def build_batch_index(
    hotel_manifests: Sequence[dict], motel_manifests: Sequence[dict], *,
    hotel_paths: Sequence[str], motel_paths: Sequence[str],
) -> dict:
    return {
        "batches": [
            {"category": "hotel", "batch_id": m["batch_id"], "path": p, "job_count": len(m["jobs"])}
            for m, p in zip(hotel_manifests, hotel_paths)
        ] + [
            {"category": "motel", "batch_id": m["batch_id"], "path": p, "job_count": len(m["jobs"])}
            for m, p in zip(motel_manifests, motel_paths)
        ],
        "total_batches": len(hotel_manifests) + len(motel_manifests),
        "total_jobs": sum(len(m["jobs"]) for m in hotel_manifests)
                     + sum(len(m["jobs"]) for m in motel_manifests),
    }

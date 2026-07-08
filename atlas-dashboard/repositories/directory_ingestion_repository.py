"""
Directory Ingestion Repository
==============================

Raw SQL persistence for the ingestion subsystem. Atlas contract:

    * Raw SQL only — no ORM.
    * No business logic. Serialization to/from row shape only.
    * The service layer (and ultimately PipelineRunner) decides WHAT to
      write; this class only knows HOW.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from engines.directory_ingestion.ingestion_models import (
    DuplicateCluster,
    DuplicatePair,
    EnrichmentTask,
    EnrichmentTaskType,
    MergeRecommendation,
    NormalizedListing,
    Provenance,
    QualityScore,
    RawListing,
    SeedPackage,
    SourceType,
    TaggedValue,
    TaskPriority,
)

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "models" / "directory_ingestion_schema.sql"


class DirectoryIngestionRepository:
    """SQLite-backed repository. One instance per connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")

    # -- schema ---------------------------------------------------------------

    def ensure_schema(self) -> None:
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self._conn.executescript(sql)
        self._conn.commit()

    # -- runs -----------------------------------------------------------------

    def create_run(self, run_id: str, directory_slug: str,
                   engine_name: str, engine_version: str) -> None:
        self._conn.execute(
            "INSERT INTO di_ingestion_runs (run_id, directory_slug, engine_name, engine_version) "
            "VALUES (?, ?, ?, ?)",
            (run_id, directory_slug, engine_name, engine_version),
        )
        self._conn.commit()

    def complete_run(self, run_id: str, package_id: str) -> None:
        self._conn.execute(
            "UPDATE di_ingestion_runs SET status = 'complete', package_id = ?, "
            "completed_at = datetime('now') WHERE run_id = ?",
            (package_id, run_id),
        )
        self._conn.commit()

    def fail_run(self, run_id: str) -> None:
        self._conn.execute(
            "UPDATE di_ingestion_runs SET status = 'failed', "
            "completed_at = datetime('now') WHERE run_id = ?",
            (run_id,),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM di_ingestion_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def find_run_by_package(self, package_id: str) -> Optional[dict]:
        """Idempotency lookup — replaying identical inputs reuses the run."""
        row = self._conn.execute(
            "SELECT * FROM di_ingestion_runs WHERE package_id = ? AND status = 'complete' "
            "ORDER BY created_at LIMIT 1",
            (package_id,),
        ).fetchone()
        return dict(row) if row else None

    # -- raw listings ------------------------------------------------------------

    def save_raw_listings(self, run_id: str, raws: list[RawListing]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO di_raw_listings "
            "(raw_id, run_id, source_type, source_name, source_url, payload_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (r.raw_id, run_id, r.source_type.value, r.source_name,
                 r.source_url, json.dumps(list(r.payload)))
                for r in raws
            ],
        )
        self._conn.commit()

    def get_raw_listings(self, run_id: str) -> list[RawListing]:
        rows = self._conn.execute(
            "SELECT * FROM di_raw_listings WHERE run_id = ? ORDER BY raw_id",
            (run_id,),
        ).fetchall()
        return [
            RawListing(
                raw_id=row["raw_id"],
                source_type=SourceType(row["source_type"]),
                source_name=row["source_name"],
                source_url=row["source_url"],
                payload=tuple(tuple(pair) for pair in json.loads(row["payload_json"])),
            )
            for row in rows
        ]

    # -- normalized listings ---------------------------------------------------------

    def save_normalized_listings(
        self, run_id: str, listings: list[NormalizedListing]
    ) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO di_normalized_listings ("
            " listing_id, run_id, raw_id, business_name, address, city, state,"
            " zip_code, country, phone, website, email, categories_json,"
            " subcategories_json, hours, latitude, longitude, amenities_json,"
            " services_json, pricing_notes, description, seo_summary,"
            " provenance_json, source_type, source_url, confidence, verified,"
            " is_canonical"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            [self._listing_to_row(run_id, l) for l in listings],
        )
        self._conn.commit()

    def mark_non_canonical(self, listing_ids: list[str]) -> None:
        self._conn.executemany(
            "UPDATE di_normalized_listings SET is_canonical = 0 WHERE listing_id = ?",
            [(lid,) for lid in listing_ids],
        )
        self._conn.commit()

    def get_normalized_listings(
        self, run_id: str, canonical_only: bool = False
    ) -> list[NormalizedListing]:
        sql = "SELECT * FROM di_normalized_listings WHERE run_id = ?"
        if canonical_only:
            sql += " AND is_canonical = 1"
        sql += " ORDER BY listing_id"
        rows = self._conn.execute(sql, (run_id,)).fetchall()
        return [self._row_to_listing(row) for row in rows]

    # -- duplicate clusters --------------------------------------------------------

    def save_duplicate_clusters(
        self, run_id: str, clusters: list[DuplicateCluster]
    ) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO di_duplicate_clusters "
            "(cluster_id, run_id, canonical_listing_id, confidence, "
            " merge_recommendation, pairs_json) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    c.cluster_id, run_id, c.canonical_listing_id, c.confidence,
                    c.merge_recommendation.value,
                    json.dumps([
                        {"a": p.listing_id_a, "b": p.listing_id_b,
                         "similarity": p.similarity,
                         "signals": list(p.matched_signals)}
                        for p in c.pairs
                    ]),
                )
                for c in clusters
            ],
        )
        self._conn.executemany(
            "INSERT OR REPLACE INTO di_duplicate_cluster_members (cluster_id, listing_id) "
            "VALUES (?, ?)",
            [(c.cluster_id, lid) for c in clusters for lid in c.listing_ids],
        )
        self._conn.commit()

    def get_duplicate_clusters(self, run_id: str) -> list[DuplicateCluster]:
        rows = self._conn.execute(
            "SELECT * FROM di_duplicate_clusters WHERE run_id = ? ORDER BY cluster_id",
            (run_id,),
        ).fetchall()
        clusters: list[DuplicateCluster] = []
        for row in rows:
            member_rows = self._conn.execute(
                "SELECT listing_id FROM di_duplicate_cluster_members "
                "WHERE cluster_id = ? ORDER BY listing_id",
                (row["cluster_id"],),
            ).fetchall()
            pairs = tuple(
                DuplicatePair(
                    listing_id_a=p["a"], listing_id_b=p["b"],
                    similarity=p["similarity"], matched_signals=tuple(p["signals"]),
                )
                for p in json.loads(row["pairs_json"])
            )
            clusters.append(
                DuplicateCluster(
                    cluster_id=row["cluster_id"],
                    listing_ids=tuple(m["listing_id"] for m in member_rows),
                    canonical_listing_id=row["canonical_listing_id"],
                    confidence=row["confidence"],
                    merge_recommendation=MergeRecommendation(row["merge_recommendation"]),
                    pairs=pairs,
                )
            )
        return clusters

    # -- quality scores ---------------------------------------------------------------

    def save_quality_scores(self, run_id: str, scores: list[QualityScore]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO di_quality_scores ("
            " listing_id, run_id, completeness, contact_quality, location_accuracy,"
            " seo_readiness, monetization_readiness, verification_quality,"
            " freshness, overall, explanations_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (s.listing_id, run_id, s.completeness, s.contact_quality,
                 s.location_accuracy, s.seo_readiness, s.monetization_readiness,
                 s.verification_quality, s.freshness, s.overall,
                 json.dumps(list(s.explanations)))
                for s in scores
            ],
        )
        self._conn.commit()

    def get_quality_scores(self, run_id: str) -> list[QualityScore]:
        rows = self._conn.execute(
            "SELECT * FROM di_quality_scores WHERE run_id = ? ORDER BY listing_id",
            (run_id,),
        ).fetchall()
        return [
            QualityScore(
                listing_id=row["listing_id"],
                completeness=row["completeness"],
                contact_quality=row["contact_quality"],
                location_accuracy=row["location_accuracy"],
                seo_readiness=row["seo_readiness"],
                monetization_readiness=row["monetization_readiness"],
                verification_quality=row["verification_quality"],
                freshness=row["freshness"],
                overall=row["overall"],
                explanations=tuple(json.loads(row["explanations_json"])),
            )
            for row in rows
        ]

    # -- enrichment tasks ----------------------------------------------------------------

    def save_enrichment_tasks(self, run_id: str, tasks: list[EnrichmentTask]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO di_enrichment_tasks "
            "(task_id, run_id, listing_id, task_type, priority, rationale, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (t.task_id, run_id, t.listing_id, t.task_type.value,
                 t.priority.value, t.rationale, t.status)
                for t in tasks
            ],
        )
        self._conn.commit()

    def get_enrichment_tasks(
        self, run_id: str, status: Optional[str] = None
    ) -> list[EnrichmentTask]:
        sql = "SELECT * FROM di_enrichment_tasks WHERE run_id = ?"
        params: list = [run_id]
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY task_id"
        rows = self._conn.execute(sql, params).fetchall()
        return [
            EnrichmentTask(
                task_id=row["task_id"],
                listing_id=row["listing_id"],
                task_type=EnrichmentTaskType(row["task_type"]),
                priority=TaskPriority(row["priority"]),
                rationale=row["rationale"],
                status=row["status"],
            )
            for row in rows
        ]

    def update_task_status(self, task_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE di_enrichment_tasks SET status = ? WHERE task_id = ?",
            (status, task_id),
        )
        self._conn.commit()

    # -- seed packages ------------------------------------------------------------------

    def save_seed_package(self, run_id: str, package: SeedPackage,
                          package_json: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO di_seed_packages "
            "(package_id, run_id, directory_slug, engine_name, engine_version, "
            " statistics_json, package_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                package.package_id, run_id, package.directory_slug,
                package.engine_name, package.engine_version,
                json.dumps(vars(package.statistics)), package_json,
            ),
        )
        self._conn.commit()

    def get_seed_package_json(self, package_id: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT package_json FROM di_seed_packages WHERE package_id = ?",
            (package_id,),
        ).fetchone()
        return row["package_json"] if row else None

    # -- row mapping -----------------------------------------------------------------------

    @staticmethod
    def _listing_to_row(run_id: str, l: NormalizedListing) -> tuple:
        provenance = {
            "address": l.address.provenance.value,
            "city": l.city.provenance.value,
            "state": l.state.provenance.value,
            "zip_code": l.zip_code.provenance.value,
            "country": l.country.provenance.value,
            "phone": l.phone.provenance.value,
            "website": l.website.provenance.value,
            "email": l.email.provenance.value,
            "hours": l.hours.provenance.value,
            "pricing_notes": l.pricing_notes.provenance.value,
            "description": l.description.provenance.value,
            "seo_summary": l.seo_summary.provenance.value,
        }
        return (
            l.listing_id, run_id, l.raw_id, l.business_name,
            l.address.value, l.city.value, l.state.value, l.zip_code.value,
            l.country.value, l.phone.value, l.website.value, l.email.value,
            json.dumps(list(l.categories)), json.dumps(list(l.subcategories)),
            l.hours.value, l.latitude, l.longitude,
            json.dumps(list(l.amenities)), json.dumps(list(l.services)),
            l.pricing_notes.value, l.description.value, l.seo_summary.value,
            json.dumps(provenance), l.source_type.value, l.source_url,
            l.confidence, int(l.verified),
        )

    @staticmethod
    def _row_to_listing(row: sqlite3.Row) -> NormalizedListing:
        provenance = json.loads(row["provenance_json"])

        def tv(field: str, value: Optional[str]) -> TaggedValue:
            if value is None:
                return TaggedValue.unknown()
            return TaggedValue(
                value=value,
                provenance=Provenance(provenance.get(field, Provenance.UNKNOWN.value)),
            )

        return NormalizedListing(
            listing_id=row["listing_id"],
            raw_id=row["raw_id"],
            business_name=row["business_name"],
            address=tv("address", row["address"]),
            city=tv("city", row["city"]),
            state=tv("state", row["state"]),
            zip_code=tv("zip_code", row["zip_code"]),
            country=tv("country", row["country"]),
            phone=tv("phone", row["phone"]),
            website=tv("website", row["website"]),
            email=tv("email", row["email"]),
            categories=tuple(json.loads(row["categories_json"])),
            subcategories=tuple(json.loads(row["subcategories_json"])),
            hours=tv("hours", row["hours"]),
            latitude=row["latitude"],
            longitude=row["longitude"],
            amenities=tuple(json.loads(row["amenities_json"])),
            services=tuple(json.loads(row["services_json"])),
            pricing_notes=tv("pricing_notes", row["pricing_notes"]),
            description=tv("description", row["description"]),
            seo_summary=tv("seo_summary", row["seo_summary"]),
            source_type=SourceType(row["source_type"]),
            source_url=row["source_url"],
            confidence=row["confidence"],
            verified=bool(row["verified"]),
        )

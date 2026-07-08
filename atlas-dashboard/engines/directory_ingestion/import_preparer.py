"""
Module 7 — Import Preparation
=============================

Turns a SeedPackage into import-ready artifacts:

    * JSON payload (canonical interchange format)
    * CSV (businesses flat file)
    * SQLite staging SQL script
    * Future API payloads share the JSON shape (documented extension point)

Every artifact is accompanied by a ValidationReport. Serialization only —
no database writes here; persistence belongs to the repository layer.
"""

from __future__ import annotations

import csv
import io
import json

from engines.directory_ingestion.ingestion_models import (
    ImportPackage,
    NormalizedListing,
    SeedPackage,
    ValidationIssue,
    ValidationReport,
)

_FORMAT_JSON = "json"
_FORMAT_CSV = "csv"
_FORMAT_SQLITE = "sqlite_staging"

_CSV_COLUMNS = (
    "listing_id", "business_name", "address", "city", "state", "zip_code",
    "country", "phone", "website", "email", "categories", "subcategories",
    "hours", "latitude", "longitude", "amenities", "services",
    "pricing_notes", "description", "seo_summary", "source_type",
    "source_url", "confidence", "verified",
)


class ImportPreparer:
    """Stateless import-artifact generator."""

    # -- public API -----------------------------------------------------------

    def to_json(self, package: SeedPackage) -> ImportPackage:
        payload = {
            "package_id": package.package_id,
            "directory_slug": package.directory_slug,
            "engine_name": package.engine_name,
            "engine_version": package.engine_version,
            "statistics": vars(package.statistics),
            "categories": [
                {"slug": c.slug, "name": c.name, "parent_slug": c.parent_slug,
                 "keywords": list(c.keywords)}
                for c in package.categories
            ],
            "locations": [
                {"slug": loc.slug, "name": loc.name, "level": loc.level,
                 "parent_slug": loc.parent_slug, "state_code": loc.state_code}
                for loc in package.locations
            ],
            "businesses": [self._listing_row(b) for b in package.businesses],
            "enrichment_queue": [
                {"task_id": t.task_id, "listing_id": t.listing_id,
                 "task_type": t.task_type.value, "priority": t.priority.value,
                 "rationale": t.rationale, "status": t.status}
                for t in package.enrichment_queue
            ],
        }
        artifact = json.dumps(payload, indent=2, sort_keys=True)
        return ImportPackage(
            package_id=package.package_id,
            format=_FORMAT_JSON,
            artifact=artifact,
            validation=self.validate(package),
        )

    def to_csv(self, package: SeedPackage) -> ImportPackage:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for b in package.businesses:
            writer.writerow(self._listing_row(b, flatten=True))
        return ImportPackage(
            package_id=package.package_id,
            format=_FORMAT_CSV,
            artifact=buffer.getvalue(),
            validation=self.validate(package),
        )

    def to_sqlite_staging(self, package: SeedPackage) -> ImportPackage:
        """
        Emits a self-contained SQL script creating and populating staging
        tables. The script is executed by tooling of the operator's choice;
        this engine never touches a database.
        """
        lines: list[str] = [
            "BEGIN TRANSACTION;",
            "CREATE TABLE IF NOT EXISTS staging_businesses (",
            "    listing_id TEXT PRIMARY KEY,",
            "    business_name TEXT NOT NULL,",
            "    address TEXT, city TEXT, state TEXT, zip_code TEXT, country TEXT,",
            "    phone TEXT, website TEXT, email TEXT,",
            "    categories TEXT, subcategories TEXT, hours TEXT,",
            "    latitude REAL, longitude REAL,",
            "    amenities TEXT, services TEXT, pricing_notes TEXT,",
            "    description TEXT, seo_summary TEXT,",
            "    source_type TEXT, source_url TEXT,",
            "    confidence REAL, verified INTEGER",
            ");",
        ]
        for b in package.businesses:
            row = self._listing_row(b, flatten=True)
            values = ", ".join(self._sql_literal(row[c]) for c in _CSV_COLUMNS)
            lines.append(
                f"INSERT OR REPLACE INTO staging_businesses "
                f"({', '.join(_CSV_COLUMNS)}) VALUES ({values});"
            )
        lines.append("COMMIT;")
        return ImportPackage(
            package_id=package.package_id,
            format=_FORMAT_SQLITE,
            artifact="\n".join(lines),
            validation=self.validate(package),
        )

    # -- validation -------------------------------------------------------------

    def validate(self, package: SeedPackage) -> ValidationReport:
        issues: list[ValidationIssue] = []

        seen_ids: set[str] = set()
        category_slugs = {c.slug for c in package.categories}

        for b in package.businesses:
            if b.listing_id in seen_ids:
                issues.append(ValidationIssue(b.listing_id, "error", "Duplicate listing_id in package"))
            seen_ids.add(b.listing_id)
            if not b.business_name.strip():
                issues.append(ValidationIssue(b.listing_id, "error", "Empty business_name"))
            if not (b.city.value and b.state.value) and b.latitude is None:
                issues.append(
                    ValidationIssue(b.listing_id, "warning", "No city/state and no coordinates")
                )
            for cat in b.categories:
                slug = cat.lower().replace(" ", "-")
                if category_slugs and slug not in category_slugs:
                    issues.append(
                        ValidationIssue(
                            b.listing_id, "warning",
                            f"Category '{cat}' not in blueprint hierarchy",
                        )
                    )

        for task in package.enrichment_queue:
            if task.listing_id not in seen_ids:
                issues.append(
                    ValidationIssue(task.listing_id, "error",
                                    f"Enrichment task {task.task_id} references unknown listing")
                )

        has_errors = any(i.severity == "error" for i in issues)
        return ValidationReport(
            valid=not has_errors,
            issues=tuple(issues),
            checked_records=len(package.businesses),
        )

    # -- helpers -----------------------------------------------------------------

    @staticmethod
    def _listing_row(b: NormalizedListing, flatten: bool = False) -> dict:
        def join(values: tuple[str, ...]) -> str:
            return "; ".join(values)

        row = {
            "listing_id": b.listing_id,
            "business_name": b.business_name,
            "address": b.address.value,
            "city": b.city.value,
            "state": b.state.value,
            "zip_code": b.zip_code.value,
            "country": b.country.value,
            "phone": b.phone.value,
            "website": b.website.value,
            "email": b.email.value,
            "categories": join(b.categories) if flatten else list(b.categories),
            "subcategories": join(b.subcategories) if flatten else list(b.subcategories),
            "hours": b.hours.value,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "amenities": join(b.amenities) if flatten else list(b.amenities),
            "services": join(b.services) if flatten else list(b.services),
            "pricing_notes": b.pricing_notes.value,
            "description": b.description.value,
            "seo_summary": b.seo_summary.value,
            "source_type": b.source_type.value,
            "source_url": b.source_url,
            "confidence": b.confidence,
            "verified": b.verified,
        }
        if not flatten:
            row["provenance"] = {
                "address": b.address.provenance.value,
                "city": b.city.provenance.value,
                "state": b.state.provenance.value,
                "phone": b.phone.provenance.value,
                "website": b.website.provenance.value,
                "email": b.email.provenance.value,
            }
        return row

    @staticmethod
    def _sql_literal(value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

"""ProjectAssemblyRepository — persistence layer for writing Project Assemblies.

Persistence only. Serializes validated models into deterministic CSV and
JSON artifacts under projects/<project_slug>/.

Pydantic v1/v2 compatible.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from engines.directory_builder.constants import SCAFFOLD_TABLE_HEADERS
from engines.directory_builder.models import BuildManifest, ManifestFile, ProjectAssembly


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return {k: _dump(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_dump(v) for v in obj]
    return obj


class ProjectAssemblyRepository:
    def __init__(self, projects_root: str | Path) -> None:
        self._root = Path(projects_root)

    def project_path(self, project_slug: str) -> Path:
        return self._root / project_slug

    def write_assembly(self, assembly: ProjectAssembly) -> tuple[ManifestFile, ...]:
        base = self.project_path(assembly.project_slug)

        for rel_dir in assembly.structure.directories:
            (base / rel_dir).mkdir(parents=True, exist_ok=True)

        written: list[ManifestFile] = []

        def w(rel_path: str, payload: bytes) -> None:
            target = base / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            written.append(
                ManifestFile(
                    path=rel_path,
                    sha256=hashlib.sha256(payload).hexdigest(),
                    size_bytes=len(payload),
                )
            )

        imp = assembly.import_package

        w(
            "imports/businesses.csv",
            self._csv(
                (
                    "business_id",
                    "name",
                    "slug",
                    "category_id",
                    "location_id",
                    "website",
                    "phone",
                    "description",
                ),
                [_dump(b) for b in imp.businesses],
            ),
        )

        w(
            "imports/categories.csv",
            self._csv(
                ("category_id", "name", "slug", "description"),
                [_dump(c) for c in imp.categories],
            ),
        )

        w(
            "imports/locations.csv",
            self._csv(
                ("location_id", "city", "state", "slug"),
                [_dump(l) for l in imp.locations],
            ),
        )

        w(
            "imports/relationships.csv",
            self._csv(
                ("relationship_id", "business_id", "category_id", "location_id"),
                [_dump(r) for r in imp.relationships],
            ),
        )

        w(
            "imports/tags.csv",
            self._csv(
                ("tag_id", "business_id", "tag"),
                [_dump(t) for t in imp.tags],
            ),
        )

        w(
            "imports/amenities.csv",
            self._csv(
                ("amenity_id", "business_id", "amenity"),
                [_dump(a) for a in imp.amenities],
            ),
        )

        for table in imp.scaffold_tables:
            w(f"imports/{table}.csv", self._csv(SCAFFOLD_TABLE_HEADERS[table], []))

        w("imports/import_package.json", self._json(_dump(imp)))

        seo = assembly.seo_package

        w(
            "seo/pages.csv",
            self._csv(
                (
                    "page_id",
                    "page_type",
                    "url_path",
                    "title",
                    "meta_description",
                    "canonical_url",
                    "category_id",
                    "location_id",
                ),
                [
                    {k: v for k, v in _dump(p).items() if k != "breadcrumbs"}
                    for p in seo.pages
                ],
            ),
        )

        w(
            "seo/internal_links.csv",
            self._csv(
                ("from_path", "to_path", "anchor_text"),
                [_dump(l) for l in seo.internal_links],
            ),
        )

        w(
            "seo/redirects.csv",
            self._csv(
                ("from_path", "to_path", "status_code"),
                [_dump(r) for r in seo.redirects],
            ),
        )

        w(
            "seo/breadcrumbs.json",
            self._json({p.url_path: list(p.breadcrumbs) for p in seo.pages}),
        )

        w("seo/sitemap_plan.json", self._json([_dump(s) for s in seo.sitemap_plan]))
        w(
            "seo/robots_recommendations.md",
            self._md_list("robots.txt Recommendations", seo.robots_recommendations),
        )
        w("seo/seo_build_package.json", self._json(_dump(seo)))

        content = assembly.content_package

        w(
            "content/content_queue.csv",
            self._csv(
                (
                    "item_id",
                    "work_type",
                    "title",
                    "target_keyword",
                    "target_path",
                    "priority",
                    "instructions",
                ),
                [_dump(i) for i in content.items],
            ),
        )

        w("content/content_build_package.json", self._json(_dump(content)))

        images = assembly.image_package

        w(
            "assets/images/image_specifications.csv",
            self._csv(
                (
                    "spec_id",
                    "image_type",
                    "subject",
                    "subject_slug",
                    "width",
                    "height",
                    "file_name",
                    "image_format",
                    "notes",
                ),
                [_dump(s) for s in images.specs],
            ),
        )

        w("assets/images/image_package.json", self._json(_dump(images)))

        w("reports/validation_report.json", self._json(_dump(assembly.validation_report)))
        w("reports/quality_report.json", self._json(_dump(assembly.quality)))
        w("reports/project_status.json", self._json(_dump(assembly.status)))

        w(
            "tasks/ai_build_queue.csv",
            self._csv(
                (
                    "unit_id",
                    "unit_type",
                    "title",
                    "instructions",
                    "priority",
                    "depends_on",
                ),
                [
                    {
                        **_dump(u),
                        "depends_on": ";".join(u.depends_on),
                    }
                    for u in assembly.ai_queue.units
                ],
            ),
        )

        w("tasks/ai_build_queue.json", self._json(_dump(assembly.ai_queue)))

        w(
            "config/project.json",
            self._json(
                {
                    "project_slug": assembly.project_slug,
                    "directories": list(assembly.structure.directories),
                }
            ),
        )

        return tuple(written)

    def write_manifest(
        self,
        assembly: ProjectAssembly,
        manifest: BuildManifest,
    ) -> tuple[str, ...]:
        base = self.project_path(assembly.project_slug)

        paths = {
            "build_manifest.json": self._json(_dump(manifest)),
            "project_summary.json": self._json(
                {
                    "project_slug": assembly.project_slug,
                    "build_id": manifest.build_id,
                    "counts": {
                        "businesses": len(assembly.import_package.businesses),
                        "categories": len(assembly.import_package.categories),
                        "locations": len(assembly.import_package.locations),
                        "seo_pages": len(assembly.seo_package.pages),
                        "content_items": len(assembly.content_package.items),
                        "image_specs": len(assembly.image_package.specs),
                        "ai_work_units": len(assembly.ai_queue.units),
                    },
                    "quality": _dump(assembly.quality),
                    "operator_summary": assembly.status.operator_summary,
                }
            ),
            "launch_status.json": self._json(
                {
                    "project_slug": assembly.project_slug,
                    "launch_readiness": assembly.status.launch_readiness,
                    "completion_percentage": assembly.status.completion_percentage,
                    "critical_warnings": list(assembly.status.critical_warnings),
                    "validation_passed": assembly.validation_report.passed,
                }
            ),
        }

        for rel, payload in paths.items():
            target = base / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)

        return tuple(paths.keys())

    @staticmethod
    def _json(data: Any) -> bytes:
        return (
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")

    @staticmethod
    def _csv(headers: tuple[str, ...] | list[str], rows: list[dict[str, Any]]) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=list(headers),
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})

        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def _md_list(title: str, items: Any) -> bytes:
        lines = [f"# {title}", ""] + [f"- {item}" for item in items] + [""]
        return "\n".join(lines).encode("utf-8")
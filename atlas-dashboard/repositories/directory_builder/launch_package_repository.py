"""LaunchPackageRepository — persistence layer for reading Launch Packages.

Persistence only: file I/O and parsing into validated Pydantic models.
No business logic, no orchestration, no SQL (launch packages are file
artifacts by contract).

blueprint.json is mandatory. Every other file is optional; anything
missing is recorded in LaunchPackage.missing_files so the honesty layer
downstream (validation, completeness scoring) can account for it.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from engines.directory_builder.models import (
    AiTaskEntry,
    Blueprint,
    CategoryDef,
    ContentPlanEntry,
    LaunchPackage,
    LocationDef,
    MonetizationModel,
    MonetizationPlan,
    SeedBusiness,
    SeoPageEntry,
    UrlMapEntry,
)

FILE_BLUEPRINT = "blueprint.json"
FILE_SEED_BUSINESSES = "seed_businesses.json"
FILE_CATEGORIES = "categories.json"
FILE_LOCATIONS = "locations.json"
FILE_URL_MAP = "url_map.csv"
FILE_SEO_PAGES = "seo_pages.csv"
FILE_CONTENT_PLAN = "content_plan.csv"
FILE_MONETIZATION = "monetization_plan.json"
FILE_AI_TASKS = "ai_task_queue.csv"
FILE_CHECKLIST = "launch_checklist.md"
FILE_OPERATOR_NOTES = "operator_notes.md"

OPTIONAL_FILES = (
    FILE_SEED_BUSINESSES,
    FILE_CATEGORIES,
    FILE_LOCATIONS,
    FILE_URL_MAP,
    FILE_SEO_PAGES,
    FILE_CONTENT_PLAN,
    FILE_MONETIZATION,
    FILE_AI_TASKS,
    FILE_CHECKLIST,
    FILE_OPERATOR_NOTES,
)


class LaunchPackageNotFoundError(FileNotFoundError):
    """Raised when the package directory or its mandatory blueprint is missing."""


class LaunchPackageRepository:
    def load(self, package_dir: str | Path) -> LaunchPackage:
        root = Path(package_dir)
        if not root.is_dir():
            raise LaunchPackageNotFoundError(f"Launch package directory not found: {root}")

        blueprint_path = root / FILE_BLUEPRINT
        if not blueprint_path.is_file():
            raise LaunchPackageNotFoundError(f"Mandatory {FILE_BLUEPRINT} not found in {root}")

        missing: list[str] = [name for name in OPTIONAL_FILES if not (root / name).is_file()]

        blueprint = Blueprint(**self._read_json(blueprint_path))

        seed_businesses = tuple(
            SeedBusiness(**row) for row in self._read_json_list(root / FILE_SEED_BUSINESSES)
        )
        categories = tuple(CategoryDef(**row) for row in self._read_json_list(root / FILE_CATEGORIES))
        locations = tuple(LocationDef(**row) for row in self._read_json_list(root / FILE_LOCATIONS))

        url_map = tuple(UrlMapEntry(**row) for row in self._read_csv(root / FILE_URL_MAP))
        seo_pages = tuple(SeoPageEntry(**row) for row in self._read_csv(root / FILE_SEO_PAGES))
        content_plan = tuple(
            ContentPlanEntry(**self._coerce_priority(row)) for row in self._read_csv(root / FILE_CONTENT_PLAN)
        )
        ai_task_queue = tuple(
            AiTaskEntry(**self._coerce_priority(row)) for row in self._read_csv(root / FILE_AI_TASKS)
        )

        monetization = MonetizationPlan()
        monetization_path = root / FILE_MONETIZATION
        if monetization_path.is_file():
            raw = self._read_json(monetization_path)
            models = tuple(MonetizationModel(**m) for m in raw.get("models", []))
            monetization = MonetizationPlan(models=models)

        return LaunchPackage(
            blueprint=blueprint,
            seed_businesses=seed_businesses,
            categories=categories,
            locations=locations,
            url_map=url_map,
            seo_pages=seo_pages,
            content_plan=content_plan,
            monetization_plan=monetization,
            ai_task_queue=ai_task_queue,
            launch_checklist_md=self._read_text(root / FILE_CHECKLIST),
            operator_notes_md=self._read_text(root / FILE_OPERATOR_NOTES),
            missing_files=tuple(sorted(missing)),
        )

    # -- primitive readers --------------------------------------------------
    @staticmethod
    def _read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_json_list(path: Path) -> list[dict]:
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    @staticmethod
    def _read_csv(path: Path) -> list[dict]:
        if not path.is_file():
            return []
        with path.open(newline="", encoding="utf-8") as handle:
            return [
                {k.strip(): (v or "").strip() for k, v in row.items() if k}
                for row in csv.DictReader(handle)
            ]

    @staticmethod
    def _read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    @staticmethod
    def _coerce_priority(row: dict) -> dict:
        coerced = dict(row)
        raw = str(coerced.get("priority", "")).strip()
        coerced["priority"] = int(raw) if raw.isdigit() else 2
        return coerced

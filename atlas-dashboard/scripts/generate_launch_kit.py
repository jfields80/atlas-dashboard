"""
scripts/generate_launch_kit.py

Directory #1 Operator Runner.

Run from:

    C:\\Atlas\\atlas-dashboard

Example:

    python scripts\\generate_launch_kit.py --project pettripfinder --blueprint examples\\pettripfinder\\blueprint_input.json --seed examples\\pettripfinder\\seed_package_input.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


_CWD = os.getcwd()
if _CWD not in sys.path:
    sys.path.insert(0, _CWD)


def _import_launch_kit_service():
    try:
        from services.launch_kit_service import LaunchKitService  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Could not import services.launch_kit_service.LaunchKitService. "
            "Run this script from C:\\Atlas\\atlas-dashboard."
        ) from exc

    return LaunchKitService


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")

    return data


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def build_launch_kit(
    blueprint_data: Dict[str, Any],
    seed_data: Dict[str, Any],
    project_slug: str,
    service_factory: Any | None = None,
) -> Any:
    """
    Compatibility adapter for LaunchKitService.

    Public legacy contract:
        returns launch_kit only

    Supported service methods:
        generate_launch_kit(...)
        generate(...)
        build_launch_kit(...)
        create_launch_kit(...)

    Supported call styles:
        keyword args:
            blueprint=, seed_package=, project_slug=

        positional args:
            blueprint_data, seed_data, project_slug
    """

    ServiceFactory = service_factory or _import_launch_kit_service()
    service = ServiceFactory()

    method_names = (
        "generate_launch_kit",
        "generate",
        "build_launch_kit",
        "create_launch_kit",
    )

    attempts = []

    for method_name in method_names:
        if not hasattr(service, method_name):
            continue

        method = getattr(service, method_name)

        attempts.extend(
            [
                lambda method=method: method(
                    blueprint=blueprint_data,
                    seed_package=seed_data,
                    project_slug=project_slug,
                ),
                lambda method=method: method(
                    blueprint_data,
                    seed_data,
                    project_slug,
                ),
            ]
        )

    if not attempts:
        raise AttributeError(
            "LaunchKitService does not expose generate_launch_kit(), "
            "generate(), build_launch_kit(), or create_launch_kit()."
        )

    last_error: TypeError | None = None

    for attempt in attempts:
        try:
            result = attempt()
            if isinstance(result, tuple) and len(result) == 2:
                return result[0]
            return result
        except TypeError as exc:
            last_error = exc

    raise TypeError(
        "LaunchKitService exists, but no supported call signature matched."
    ) from last_error


def write_launch_package(
    output_dir: Path,
    project_slug: str,
    launch_kit: Mapping[str, Any] | Any,
    overwrite: bool = False,
) -> Path:
    """
    Write launch package using the legacy operator-runner contract.

    Required legacy files:
        launch_package.json
        json_export.json
        listings.csv
        url_map.json
        seo_export.json
        content_plan_export.json
        ai_task_queue_export.json
        launch_checklist.md
        operator_notes.md
    """

    package_dir = output_dir / project_slug

    if package_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Launch package already exists at {package_dir}. "
                "Pass overwrite=True to regenerate it."
            )
        shutil.rmtree(package_dir)

    package_dir.mkdir(parents=True, exist_ok=True)

    data = _to_jsonable(launch_kit)

    _write_json(package_dir / "launch_package.json", data)

    if not isinstance(data, dict):
        return package_dir

    if "json_export" in data:
        _write_json(package_dir / "json_export.json", data["json_export"])

    if "csv_export" in data:
        _write_csv(package_dir / "listings.csv", data["csv_export"])

    if "url_map" in data:
        _write_json(package_dir / "url_map.json", data["url_map"])

    if "seo_export" in data:
        _write_json(package_dir / "seo_export.json", data["seo_export"])

    if "content_plan_export" in data:
        _write_json(
            package_dir / "content_plan_export.json",
            data["content_plan_export"],
        )

    if "ai_task_queue_export" in data:
        _write_json(
            package_dir / "ai_task_queue_export.json",
            data["ai_task_queue_export"],
        )

    if "launch_checklist" in data:
        _write_markdown(
            package_dir / "launch_checklist.md",
            data["launch_checklist"],
        )

    if "operator_notes" in data:
        _write_markdown(
            package_dir / "operator_notes.md",
            data["operator_notes"],
        )

    return package_dir


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_to_jsonable(value), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_csv(path: Path, rows: Any) -> None:
    normalized_rows = _normalize_rows(rows)

    with path.open("w", encoding="utf-8", newline="") as f:
        if not normalized_rows:
            f.write("")
            return

        headers = sorted(
            {
                key
                for row in normalized_rows
                for key in row.keys()
            }
        )

        writer = csv.DictWriter(f, fieldnames=headers, lineterminator="\n")
        writer.writeheader()

        for row in normalized_rows:
            writer.writerow(
                {
                    key: _csv_cell(row.get(key, ""))
                    for key in headers
                }
            )


def _write_markdown(path: Path, value: Any) -> None:
    if isinstance(value, str):
        content = value
    elif isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        content = "\n".join(f"- {item}" for item in value)
    else:
        content = str(value)

    if content and not content.endswith("\n"):
        content += "\n"

    path.write_text(content, encoding="utf-8", newline="\n")


def _normalize_rows(rows: Any) -> list[dict[str, Any]]:
    rows = _to_jsonable(rows)

    if rows is None:
        return []

    if isinstance(rows, dict):
        return [rows]

    if not isinstance(rows, list):
        return [{"value": rows}]

    normalized: list[dict[str, Any]] = []

    for row in rows:
        if isinstance(row, dict):
            normalized.append(row)
        else:
            normalized.append({"value": row})

    return normalized


def _csv_cell(value: Any) -> str:
    value = _to_jsonable(value)

    if value is None:
        return ""

    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)

    return str(value)


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]

    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump())

    if hasattr(value, "dict"):
        return _to_jsonable(value.dict())

    if hasattr(value, "__dict__"):
        return {
            str(k): _to_jsonable(v)
            for k, v in vars(value).items()
            if not k.startswith("_")
        }

    return str(value)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a launch package from blueprint JSON and seed package JSON."
    )

    parser.add_argument(
        "--project",
        required=True,
        help="Project slug/name, e.g. pettripfinder",
    )

    parser.add_argument(
        "--blueprint",
        required=True,
        type=Path,
        help="Path to blueprint JSON",
    )

    parser.add_argument(
        "--seed",
        required=True,
        type=Path,
        help="Path to seed package JSON",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("launch_packages"),
        help="Output directory for generated launch packages",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing launch package directory",
    )

    return parser.parse_args(argv)


def run(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    project_slug = slugify(args.project)

    print(f"[operator-runner] project: {project_slug}")

    print(f"[operator-runner] loading blueprint: {args.blueprint}")
    try:
        blueprint_data = load_json(args.blueprint)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[operator-runner] ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"[operator-runner] loading seed package: {args.seed}")
    try:
        seed_data = load_json(args.seed)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[operator-runner] ERROR: {exc}", file=sys.stderr)
        return 1

    print("[operator-runner] calling LaunchKitService...")

    try:
        launch_kit = build_launch_kit(
            blueprint_data=blueprint_data,
            seed_data=seed_data,
            project_slug=project_slug,
        )
    except Exception as exc:
        print(f"[operator-runner] ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        package_dir = write_launch_package(
            output_dir=args.output_dir,
            project_slug=project_slug,
            launch_kit=launch_kit,
            overwrite=args.overwrite,
        )
    except FileExistsError as exc:
        print(f"[operator-runner] ERROR: {exc}", file=sys.stderr)
        return 3

    print(f"[operator-runner] DONE. Launch package ready at: {package_dir}")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
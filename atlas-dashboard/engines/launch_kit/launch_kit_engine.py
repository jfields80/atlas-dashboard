"""Launch Kit Engine.

Deterministic, framework-independent engine that converts raw blueprint
and seed-package dictionaries into a fully rendered launch package
(:class:`LaunchKit`).

Guarantees
----------
* Pure computation: no filesystem, no network, no clock, no randomness.
* Byte-identical output for identical input (JSON keys sorted, CSV rows
  and fieldnames deterministically ordered, ``\\n`` line endings).
* Defensive extraction: any missing optional blueprint / seed-package
  section produces an empty-but-valid file instead of an exception.
* Zero imports from Phase 3A (Blueprint) or Phase 3B (Ingestion) code.

The only hard requirements are ``project_slug`` (non-empty, sanitizable)
and that ``blueprint`` / ``seed_package`` are mappings.
"""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from engines.launch_kit.models import (
    LAUNCH_KIT_FILENAMES,
    LaunchFile,
    LaunchKit,
    LaunchKitInput,
    LaunchKitInputError,
    LaunchKitStats,
)

# ---------------------------------------------------------------------------
# Named constants (no magic values in logic below)
# ---------------------------------------------------------------------------

JSON_INDENT = 2
CSV_LINE_TERMINATOR = "\n"
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
MAX_GENERATED_URL_ROWS = 5000  # hard cap on category x location URL explosion

# Tolerant key aliases for defensive extraction. First match wins.
LISTING_KEYS = ("listings", "businesses", "seed_businesses", "records", "items")
CATEGORY_KEYS = ("categories", "category_list")
LOCATION_KEYS = ("locations", "location_list", "cities")
SEO_SECTION_KEYS = ("seo_blueprint", "seo_plan", "seo")
SEO_PAGE_KEYS = ("pages", "seo_pages", "page_plan")
URL_MAP_KEYS = ("url_map", "urls", "url_structure_examples")
CONTENT_SECTION_KEYS = ("content_strategy", "content_plan", "content")
CONTENT_ITEM_KEYS = ("items", "articles", "pieces", "plan", "topics")
MONETIZATION_KEYS = ("monetization_plan", "monetization")
AI_TASK_KEYS = ("ai_task_definitions", "ai_tasks", "tasks", "task_queue")
ROADMAP_KEYS = ("roadmap", "launch_roadmap", "plan")
ROADMAP_PHASE_KEYS = ("phases", "milestones", "stages")
PHASE_TASK_KEYS = ("tasks", "steps", "items", "checklist")
RISK_SECTION_KEYS = ("risk_analysis", "risks", "risk_assessment")
RISK_ITEM_KEYS = ("risks", "items", "entries")
DATA_QUALITY_KEYS = ("data_quality", "quality_report", "quality")

# Preferred CSV column ordering (columns present in data appear in this
# order first; any extra columns follow, sorted alphabetically).
SEED_CSV_PREFERRED = (
    "id",
    "listing_id",
    "name",
    "business_name",
    "category",
    "subcategory",
    "address",
    "city",
    "state",
    "zip",
    "postal_code",
    "phone",
    "email",
    "website",
    "url",
    "latitude",
    "longitude",
    "description",
    "rating",
    "review_count",
    "source",
    "quality_score",
)
URL_MAP_FIELDS = ("url", "page_type", "source", "notes")
SEO_PAGES_PREFERRED = (
    "url",
    "slug",
    "page_type",
    "title",
    "meta_description",
    "primary_keyword",
    "secondary_keywords",
    "priority",
)
CONTENT_PLAN_PREFERRED = (
    "title",
    "content_type",
    "target_keyword",
    "target_url",
    "priority",
    "status",
    "notes",
)
AI_TASK_PREFERRED = (
    "task_id",
    "phase",
    "name",
    "title",
    "description",
    "task_type",
    "depends_on",
    "priority",
    "status",
)
AI_TASK_DEFAULT_STATUS = "pending"

# Blueprint sections tracked for the operator-notes coverage report.
TRACKED_BLUEPRINT_SECTIONS = (
    ("seo", SEO_SECTION_KEYS),
    ("content_strategy", CONTENT_SECTION_KEYS),
    ("monetization_plan", MONETIZATION_KEYS),
    ("ai_task_definitions", AI_TASK_KEYS),
    ("roadmap", ROADMAP_KEYS),
    ("risk_analysis", RISK_SECTION_KEYS),
)
TRACKED_SEED_SECTIONS = (
    ("listings", LISTING_KEYS),
    ("categories", CATEGORY_KEYS),
    ("locations", LOCATION_KEYS),
)

DEFAULT_CHECKLIST_SECTIONS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "Pre-Launch",
        (
            "Register or confirm the domain",
            "Set up hosting / platform for the directory",
            "Configure analytics and search console",
        ),
    ),
    (
        "Data Import",
        (
            "Import seed businesses from seed_businesses.csv",
            "Create categories from categories.json",
            "Create location pages from locations.json",
            "Spot-check 10 random listings for accuracy",
        ),
    ),
    (
        "SEO Setup",
        (
            "Implement URL structure from url_map.csv",
            "Create pages listed in seo_pages.csv",
            "Submit sitemap to search engines",
        ),
    ),
    (
        "Content",
        ("Work through content_plan.csv in priority order",),
    ),
    (
        "Monetization",
        (
            "Implement the plan in monetization_plan.json",
            "Verify at least one revenue path is live at launch",
        ),
    ),
    (
        "Launch",
        (
            "Final QA pass on all page types",
            "Go live",
            "Record launch date and baseline metrics in Atlas",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Generic defensive-extraction helpers
# ---------------------------------------------------------------------------


def _first(mapping: Any, keys: Sequence[str], default: Any = None) -> Any:
    """Return the first present, non-None value among ``keys``."""
    if not isinstance(mapping, Mapping):
        return default
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _as_dict_list(value: Any) -> List[Dict[str, Any]]:
    """Coerce a value into a list of dicts, dropping anything else."""
    if not isinstance(value, (list, tuple)):
        return []
    out: List[Dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(dict(item))
        elif isinstance(item, str):
            out.append({"name": item})
    return out


def slugify(value: str) -> str:
    """Lowercase, replace non-alphanumerics with hyphens, strip edges."""
    return SLUG_PATTERN.sub("-", str(value).strip().lower()).strip("-")


def _cell(value: Any) -> str:
    """Render a single CSV cell deterministically."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def _render_json(payload: Any) -> str:
    return json.dumps(payload, indent=JSON_INDENT, sort_keys=True, ensure_ascii=False) + "\n"


def _render_csv(
    rows: Sequence[Mapping[str, Any]],
    preferred: Sequence[str] = (),
) -> str:
    """Render rows to CSV with deterministic column ordering.

    Column order: preferred columns that actually appear (in preferred
    order), then all remaining columns sorted alphabetically. When there
    are no rows, the preferred columns alone form a header-only file so
    the CSV is still valid and openable.
    """
    seen: set = set()
    for row in rows:
        seen.update(str(k) for k in row.keys())

    fieldnames: List[str] = [c for c in preferred if c in seen]
    extras = sorted(seen - set(fieldnames))
    fieldnames.extend(extras)
    if not fieldnames:
        fieldnames = list(preferred)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator=CSV_LINE_TERMINATOR)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _cell(row.get(k)) for k in fieldnames})
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Section extractors
# ---------------------------------------------------------------------------


def _extract_listings(seed_package: Mapping[str, Any]) -> List[Dict[str, Any]]:
    listings = _first(seed_package, LISTING_KEYS)
    if listings is None:
        # Tolerate one level of nesting, e.g. {"seed_package": {...}} or {"data": {...}}
        for wrapper_key in ("seed_package", "data", "package"):
            inner = seed_package.get(wrapper_key)
            if isinstance(inner, Mapping):
                listings = _first(inner, LISTING_KEYS)
                if listings is not None:
                    break
    return _as_dict_list(listings)


def _extract_categories(
    seed_package: Mapping[str, Any],
    listings: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Explicit categories if present; otherwise derived from listings."""
    explicit = _as_dict_list(_first(seed_package, CATEGORY_KEYS))
    if explicit:
        normalized = []
        for cat in explicit:
            name = str(_first(cat, ("name", "category", "label"), "")).strip()
            if not name:
                continue
            entry = dict(cat)
            entry["name"] = name
            entry.setdefault("slug", slugify(name))
            normalized.append(entry)
        return sorted(normalized, key=lambda c: c["slug"])

    names: set = set()
    for listing in listings:
        raw = _first(listing, ("category", "categories", "primary_category"))
        if isinstance(raw, str) and raw.strip():
            names.add(raw.strip())
        elif isinstance(raw, (list, tuple)):
            names.update(str(v).strip() for v in raw if str(v).strip())
    return [
        {"name": name, "slug": slugify(name), "derived_from": "listings"}
        for name in sorted(names, key=lambda n: slugify(n))
    ]


def _extract_locations(
    seed_package: Mapping[str, Any],
    listings: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Explicit locations if present; otherwise derived from listing city/state."""
    explicit = _as_dict_list(_first(seed_package, LOCATION_KEYS))
    if explicit:
        normalized = []
        for loc in explicit:
            name = str(
                _first(loc, ("name", "city", "location", "label"), "")
            ).strip()
            if not name:
                continue
            entry = dict(loc)
            entry["name"] = name
            state = str(_first(loc, ("state", "region", "province"), "")).strip()
            slug_base = f"{name}-{state}" if state else name
            entry.setdefault("slug", slugify(slug_base))
            normalized.append(entry)
        return sorted(normalized, key=lambda l: l["slug"])

    pairs: set = set()
    for listing in listings:
        city = str(_first(listing, ("city", "town"), "")).strip()
        state = str(_first(listing, ("state", "region", "province"), "")).strip()
        if city:
            pairs.add((city, state))
    return [
        {
            "name": city,
            "state": state,
            "slug": slugify(f"{city}-{state}" if state else city),
            "derived_from": "listings",
        }
        for city, state in sorted(pairs, key=lambda p: slugify(f"{p[0]}-{p[1]}"))
    ]


def _extract_seo_section(blueprint: Mapping[str, Any]) -> Mapping[str, Any]:
    section = _first(blueprint, SEO_SECTION_KEYS, {})
    return section if isinstance(section, Mapping) else {}


def _extract_url_rows(
    blueprint: Mapping[str, Any],
    categories: Sequence[Mapping[str, Any]],
    locations: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """URL map from the blueprint when available, else generated."""
    seo = _extract_seo_section(blueprint)
    explicit = _as_dict_list(_first(seo, URL_MAP_KEYS) or _first(blueprint, URL_MAP_KEYS))
    if explicit:
        rows = []
        for entry in explicit:
            url = str(
                _first(entry, ("url", "path", "pattern", "name"), "")
            ).strip()
            if not url:
                continue
            rows.append(
                {
                    "url": url,
                    "page_type": str(_first(entry, ("page_type", "type"), "")),
                    "source": "blueprint",
                    "notes": str(_first(entry, ("notes", "description"), "")),
                }
            )
        return sorted(rows, key=lambda r: (r["page_type"], r["url"]))

    rows = [{"url": "/", "page_type": "home", "source": "generated", "notes": ""}]
    for cat in categories:
        rows.append(
            {
                "url": f"/{cat['slug']}/",
                "page_type": "category",
                "source": "generated",
                "notes": cat.get("name", ""),
            }
        )
    for loc in locations:
        rows.append(
            {
                "url": f"/{loc['slug']}/",
                "page_type": "location",
                "source": "generated",
                "notes": loc.get("name", ""),
            }
        )
    for loc in locations:
        for cat in categories:
            if len(rows) >= MAX_GENERATED_URL_ROWS:
                return rows
            rows.append(
                {
                    "url": f"/{loc['slug']}/{cat['slug']}/",
                    "page_type": "location_category",
                    "source": "generated",
                    "notes": f"{cat.get('name', '')} in {loc.get('name', '')}",
                }
            )
    return rows


def _extract_seo_page_rows(blueprint: Mapping[str, Any]) -> List[Dict[str, Any]]:
    seo = _extract_seo_section(blueprint)
    pages = _as_dict_list(_first(seo, SEO_PAGE_KEYS))
    rows = []
    for page in pages:
        row = dict(page)
        for key in ("secondary_keywords",):
            if isinstance(row.get(key), (list, tuple)):
                row[key] = "; ".join(str(v) for v in row[key])
        rows.append(row)
    return rows


def _extract_content_rows(blueprint: Mapping[str, Any]) -> List[Dict[str, Any]]:
    section = _first(blueprint, CONTENT_SECTION_KEYS, {})
    if isinstance(section, (list, tuple)):
        return _as_dict_list(section)
    if not isinstance(section, Mapping):
        return []
    return _as_dict_list(_first(section, CONTENT_ITEM_KEYS))


def _extract_monetization(blueprint: Mapping[str, Any]) -> Mapping[str, Any]:
    section = _first(blueprint, MONETIZATION_KEYS, {})
    return section if isinstance(section, Mapping) else {"plan": section}


def _extract_ai_task_rows(blueprint: Mapping[str, Any]) -> List[Dict[str, Any]]:
    tasks = _as_dict_list(_first(blueprint, AI_TASK_KEYS))
    rows = []
    for index, task in enumerate(tasks, start=1):
        row = dict(task)
        row.setdefault("task_id", f"T{index:03d}")
        row.setdefault("status", AI_TASK_DEFAULT_STATUS)
        if isinstance(row.get("depends_on"), (list, tuple)):
            row["depends_on"] = "; ".join(str(v) for v in row["depends_on"])
        rows.append(row)
    return rows


def _extract_roadmap_phases(
    blueprint: Mapping[str, Any],
) -> List[Tuple[str, List[str]]]:
    roadmap = _first(blueprint, ROADMAP_KEYS, {})
    if isinstance(roadmap, (list, tuple)):
        phases_raw = _as_dict_list(roadmap)
    elif isinstance(roadmap, Mapping):
        phases_raw = _as_dict_list(_first(roadmap, ROADMAP_PHASE_KEYS))
    else:
        phases_raw = []

    phases: List[Tuple[str, List[str]]] = []
    for index, phase in enumerate(phases_raw, start=1):
        name = str(
            _first(phase, ("name", "phase", "title", "label"), f"Phase {index}")
        ).strip() or f"Phase {index}"
        tasks_raw = _first(phase, PHASE_TASK_KEYS, [])
        tasks: List[str] = []
        if isinstance(tasks_raw, (list, tuple)):
            for task in tasks_raw:
                if isinstance(task, str) and task.strip():
                    tasks.append(task.strip())
                elif isinstance(task, Mapping):
                    label = str(
                        _first(task, ("name", "title", "task", "description"), "")
                    ).strip()
                    if label:
                        tasks.append(label)
        phases.append((name, tasks))
    return phases


def _extract_risks(blueprint: Mapping[str, Any]) -> List[Dict[str, Any]]:
    section = _first(blueprint, RISK_SECTION_KEYS, {})
    if isinstance(section, (list, tuple)):
        return _as_dict_list(section)
    if not isinstance(section, Mapping):
        return []
    return _as_dict_list(_first(section, RISK_ITEM_KEYS))


# ---------------------------------------------------------------------------
# Markdown renderers
# ---------------------------------------------------------------------------


def _plural(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def _render_checklist(
    project_name: str,
    phases: Sequence[Tuple[str, Sequence[str]]],
    stats: LaunchKitStats,
    generated_at: Optional[str],
) -> str:
    lines: List[str] = [f"# Launch Checklist — {project_name}", ""]
    if generated_at:
        lines.extend([f"Generated: {generated_at}", ""])

    sections: Sequence[Tuple[str, Sequence[str]]]
    if phases:
        lines.extend(
            [
                "Checklist sections are derived from the blueprint roadmap.",
                "",
            ]
        )
        sections = phases
    else:
        lines.extend(
            [
                "No roadmap was found in the blueprint; this is the standard "
                "directory launch checklist.",
                "",
            ]
        )
        sections = DEFAULT_CHECKLIST_SECTIONS

    for name, tasks in sections:
        lines.append(f"## {name}")
        lines.append("")
        if tasks:
            for task in tasks:
                lines.append(f"- [ ] {task}")
        else:
            lines.append("- [ ] (no tasks defined for this phase)")
        lines.append("")

    lines.extend(
        [
            "## Data Import Reference",
            "",
            f"- [ ] Import {stats.listing_count} seed "
            f"{_plural(stats.listing_count, 'business', 'businesses')} "
            "(seed_businesses.csv)",
            f"- [ ] Create {stats.category_count} "
            f"{_plural(stats.category_count, 'category', 'categories')} "
            "(categories.json)",
            f"- [ ] Create {stats.location_count} location "
            f"{_plural(stats.location_count, 'page', 'pages')} "
            "(locations.json)",
            f"- [ ] Implement {stats.url_count} "
            f"{_plural(stats.url_count, 'URL', 'URLs')} (url_map.csv)",
            "",
        ]
    )
    return "\n".join(lines)


def _render_operator_notes(
    project_name: str,
    project_slug: str,
    stats: LaunchKitStats,
    risks: Sequence[Mapping[str, Any]],
    monetization: Mapping[str, Any],
    seed_package: Mapping[str, Any],
    generated_at: Optional[str],
) -> str:
    lines: List[str] = [f"# Operator Notes — {project_name}", ""]
    lines.append(f"Project slug: `{project_slug}`")
    if generated_at:
        lines.append(f"Generated: {generated_at}")
    lines.append("")

    lines.extend(
        [
            "## Package Summary",
            "",
            f"- Seed businesses: {stats.listing_count}",
            f"- Categories: {stats.category_count}",
            f"- Locations: {stats.location_count}",
            f"- Planned URLs: {stats.url_count}",
            f"- SEO pages defined: {stats.seo_page_count}",
            f"- Content plan items: {stats.content_item_count}",
            f"- AI tasks queued: {stats.ai_task_count}",
            "",
        ]
    )

    lines.extend(["## Source Coverage", ""])
    if stats.sections_present:
        lines.append("Populated from source data:")
        lines.append("")
        for name in stats.sections_present:
            lines.append(f"- {name}")
        lines.append("")
    if stats.sections_missing:
        lines.append(
            "Missing from source data (files were generated empty or from "
            "fallbacks — verify before launch):"
        )
        lines.append("")
        for name in stats.sections_missing:
            lines.append(f"- {name}")
        lines.append("")

    lines.extend(["## Monetization Summary", ""])
    if monetization:
        model = _first(
            monetization, ("primary_model", "model", "strategy", "summary")
        )
        if model is not None:
            lines.append(f"Primary model: {_cell(model)}")
            lines.append("")
        lines.append("Full details: `monetization_plan.json`")
    else:
        lines.append(
            "No monetization plan was found in the blueprint. Define at least "
            "one revenue path before launch — an unmonetized launch repeats "
            "the existing portfolio gap."
        )
    lines.append("")

    lines.extend(["## Risks", ""])
    if risks:
        for risk in risks:
            label = str(
                _first(risk, ("name", "risk", "title", "description"), "")
            ).strip()
            severity = str(_first(risk, ("severity", "level", "impact"), "")).strip()
            mitigation = str(
                _first(risk, ("mitigation", "response", "plan"), "")
            ).strip()
            bullet = f"- {label}" if label else "- (unlabeled risk)"
            if severity:
                bullet += f" (severity: {severity})"
            lines.append(bullet)
            if mitigation:
                lines.append(f"  - Mitigation: {mitigation}")
    else:
        lines.append("No risk analysis was found in the blueprint.")
    lines.append("")

    quality = _first(seed_package, DATA_QUALITY_KEYS)
    lines.extend(["## Data Quality", ""])
    if isinstance(quality, Mapping) and quality:
        for key in sorted(quality.keys(), key=str):
            lines.append(f"- {key}: {_cell(quality[key])}")
    else:
        lines.append(
            "No data quality report was found in the seed package. Treat all "
            "seed data as UNVERIFIED until spot-checked."
        )
    lines.append("")

    lines.extend(
        [
            "## How To Use This Package",
            "",
            "1. Read `launch_checklist.md` and work top to bottom.",
            "2. Import `seed_businesses.csv` into your directory platform.",
            "3. Build the URL structure from `url_map.csv`.",
            "4. Create the pages in `seo_pages.csv` and work through "
            "`content_plan.csv`.",
            "5. Use `ai_task_queue.csv` as the queue for AI-assisted content "
            "and enrichment work.",
            "6. Implement `monetization_plan.json` before declaring launch "
            "complete.",
            "",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Engine entry point
# ---------------------------------------------------------------------------


def _validate_input(kit_input: LaunchKitInput) -> str:
    """Validate required fields; return the sanitized project slug."""
    if not isinstance(kit_input.blueprint, Mapping):
        raise LaunchKitInputError("blueprint must be a mapping (dict)")
    if not isinstance(kit_input.seed_package, Mapping):
        raise LaunchKitInputError("seed_package must be a mapping (dict)")
    slug = slugify(kit_input.project_slug or "")
    if not slug:
        raise LaunchKitInputError(
            "project_slug is required and must contain at least one "
            "alphanumeric character"
        )
    return slug


def _section_coverage(
    blueprint: Mapping[str, Any], seed_package: Mapping[str, Any]
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    present: List[str] = []
    missing: List[str] = []
    for label, keys in TRACKED_BLUEPRINT_SECTIONS:
        (present if _first(blueprint, keys) is not None else missing).append(
            f"blueprint.{label}"
        )
    for label, keys in TRACKED_SEED_SECTIONS:
        found = _first(seed_package, keys) is not None
        if not found and label == "listings":
            found = bool(_extract_listings(seed_package))
        (present if found else missing).append(f"seed_package.{label}")
    return tuple(present), tuple(missing)


def build_launch_kit(kit_input: LaunchKitInput) -> LaunchKit:
    """Build a complete, in-memory launch package.

    Deterministic: identical input produces byte-identical file content.
    """
    slug = _validate_input(kit_input)
    project_name = (kit_input.project_name or "").strip() or slug.replace(
        "-", " "
    ).title()
    blueprint: Mapping[str, Any] = kit_input.blueprint
    seed_package: Mapping[str, Any] = kit_input.seed_package

    listings = _extract_listings(seed_package)
    categories = _extract_categories(seed_package, listings)
    locations = _extract_locations(seed_package, listings)
    url_rows = _extract_url_rows(blueprint, categories, locations)
    seo_page_rows = _extract_seo_page_rows(blueprint)
    content_rows = _extract_content_rows(blueprint)
    monetization = _extract_monetization(blueprint)
    ai_task_rows = _extract_ai_task_rows(blueprint)
    roadmap_phases = _extract_roadmap_phases(blueprint)
    risks = _extract_risks(blueprint)
    sections_present, sections_missing = _section_coverage(blueprint, seed_package)

    stats = LaunchKitStats(
        listing_count=len(listings),
        category_count=len(categories),
        location_count=len(locations),
        url_count=len(url_rows),
        seo_page_count=len(seo_page_rows),
        content_item_count=len(content_rows),
        ai_task_count=len(ai_task_rows),
        sections_present=sections_present,
        sections_missing=sections_missing,
    )

    rendered: Dict[str, str] = {
        "blueprint.json": _render_json(dict(blueprint)),
        "seed_businesses.csv": _render_csv(listings, SEED_CSV_PREFERRED),
        "seed_businesses.json": _render_json(listings),
        "categories.json": _render_json(categories),
        "locations.json": _render_json(locations),
        "url_map.csv": _render_csv(url_rows, URL_MAP_FIELDS),
        "seo_pages.csv": _render_csv(seo_page_rows, SEO_PAGES_PREFERRED),
        "content_plan.csv": _render_csv(content_rows, CONTENT_PLAN_PREFERRED),
        "monetization_plan.json": _render_json(dict(monetization)),
        "ai_task_queue.csv": _render_csv(ai_task_rows, AI_TASK_PREFERRED),
        "launch_checklist.md": _render_checklist(
            project_name, roadmap_phases, stats, kit_input.generated_at
        ),
        "operator_notes.md": _render_operator_notes(
            project_name,
            slug,
            stats,
            risks,
            monetization,
            seed_package,
            kit_input.generated_at,
        ),
    }

    files = tuple(
        LaunchFile(filename=name, content=rendered[name])
        for name in LAUNCH_KIT_FILENAMES
    )
    return LaunchKit(
        project_slug=slug,
        project_name=project_name,
        files=files,
        stats=stats,
        generated_at=kit_input.generated_at,
    )

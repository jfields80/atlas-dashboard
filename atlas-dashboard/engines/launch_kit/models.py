"""Launch Kit models.

Frozen, framework-independent dataclasses describing the input contract
and the fully rendered output of the Launch Kit Engine.

Design notes
------------
* ``LaunchKitInput`` is a *tolerant* contract: ``blueprint`` and
  ``seed_package`` are plain dictionaries. The engine performs defensive
  extraction and never assumes any Phase 3A / 3B internal model shape.
* ``LaunchKit.files`` contains every export file rendered to its final
  string content. The exporter is therefore a dumb byte-writer; all
  determinism guarantees live in the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

# Canonical file order for a launch package. The engine always emits all
# of these, in this order, even when a source section is missing (in
# which case the file is empty-but-valid).
LAUNCH_KIT_FILENAMES: Tuple[str, ...] = (
    "blueprint.json",
    "seed_businesses.csv",
    "seed_businesses.json",
    "categories.json",
    "locations.json",
    "url_map.csv",
    "seo_pages.csv",
    "content_plan.csv",
    "monetization_plan.json",
    "ai_task_queue.csv",
    "launch_checklist.md",
    "operator_notes.md",
)


class LaunchKitInputError(ValueError):
    """Raised when the minimum required Launch Kit input is invalid."""


@dataclass(frozen=True)
class LaunchKitInput:
    """Minimum contract required to generate a launch package.

    Required:
        project_slug: URL/filesystem-safe identifier for the project.
        blueprint:    Raw blueprint dictionary (Phase 3A output or
                      hand-authored JSON). May be sparse.
        seed_package: Raw seed package dictionary (Phase 3B output or
                      hand-authored JSON). May be sparse.

    Optional:
        project_name: Human-readable name. Defaults to a title-cased
                      version of the slug.
        generated_at: Explicit timestamp string. If omitted, no
                      timestamp appears anywhere in the package, which
                      keeps output byte-identical across runs.
    """

    project_slug: str
    blueprint: Mapping[str, Any] = field(default_factory=dict)
    seed_package: Mapping[str, Any] = field(default_factory=dict)
    project_name: Optional[str] = None
    generated_at: Optional[str] = None


@dataclass(frozen=True)
class LaunchFile:
    """A single, fully rendered file within a launch package."""

    filename: str
    content: str

    @property
    def extension(self) -> str:
        return self.filename.rsplit(".", 1)[-1] if "." in self.filename else ""


@dataclass(frozen=True)
class LaunchKitStats:
    """Summary counts used for reporting and operator notes."""

    listing_count: int = 0
    category_count: int = 0
    location_count: int = 0
    url_count: int = 0
    seo_page_count: int = 0
    content_item_count: int = 0
    ai_task_count: int = 0
    sections_present: Tuple[str, ...] = ()
    sections_missing: Tuple[str, ...] = ()


@dataclass(frozen=True)
class LaunchKit:
    """Complete, in-memory launch package. Never touches the filesystem."""

    project_slug: str
    project_name: str
    files: Tuple[LaunchFile, ...]
    stats: LaunchKitStats
    generated_at: Optional[str] = None

    def file_map(self) -> Dict[str, LaunchFile]:
        return {f.filename: f for f in self.files}

    def get_file(self, filename: str) -> LaunchFile:
        for f in self.files:
            if f.filename == filename:
                return f
        raise KeyError(f"Launch kit has no file named {filename!r}")

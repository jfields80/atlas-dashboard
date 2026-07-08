"""Launch Kit Exporter.

Writes a fully rendered :class:`LaunchKit` to disk. This module is a
deliberately dumb byte-writer: all content and determinism guarantees
live in the engine. The exporter only decides *where* files go.

Default layout:

    launch_packages/{project_slug}/
        blueprint.json
        seed_businesses.csv
        ...

The output root is configurable per-exporter or per-call. Re-exporting
the same LaunchKit to the same location produces byte-identical files
(existing files are overwritten).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from engines.launch_kit.models import LaunchKit

DEFAULT_OUTPUT_ROOT = "launch_packages"
FILE_ENCODING = "utf-8"
FILE_NEWLINE = ""  # engine content already uses "\n"; do not translate


class LaunchKitExportError(RuntimeError):
    """Raised when a launch kit cannot be written to disk."""


class LaunchKitExporter:
    """Writes LaunchKit objects to a configurable output directory."""

    def __init__(self, output_root: Union[str, Path] = DEFAULT_OUTPUT_ROOT) -> None:
        self._output_root = Path(output_root)

    @property
    def output_root(self) -> Path:
        return self._output_root

    def package_dir(self, kit: LaunchKit) -> Path:
        return self._output_root / kit.project_slug

    def export(
        self,
        kit: LaunchKit,
        output_root: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Write every file in the kit; return the package directory.

        Args:
            kit: The rendered launch kit.
            output_root: Optional per-call override of the output root.

        Raises:
            LaunchKitExportError: If the directory or any file cannot be
                written.
        """
        root = Path(output_root) if output_root is not None else self._output_root
        package_dir = root / kit.project_slug
        try:
            package_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LaunchKitExportError(
                f"Could not create package directory {package_dir}: {exc}"
            ) from exc

        for launch_file in kit.files:
            target = package_dir / launch_file.filename
            try:
                with open(
                    target, "w", encoding=FILE_ENCODING, newline=FILE_NEWLINE
                ) as handle:
                    handle.write(launch_file.content)
            except OSError as exc:
                raise LaunchKitExportError(
                    f"Could not write {target}: {exc}"
                ) from exc
        return package_dir

    def written_paths(self, kit: LaunchKit) -> List[Path]:
        """The paths export() writes, in kit order (no filesystem access)."""
        package_dir = self.package_dir(kit)
        return [package_dir / f.filename for f in kit.files]

from __future__ import annotations

from pathlib import Path

from acdis.safeguards.path_fence import PathFenceError, ensure_acdis_path


def write_markdown_report(markdown_text: str, output_path: str | Path, overwrite: bool = False) -> Path:
    target = ensure_acdis_path(output_path)
    if target.exists() and not overwrite:
        raise PathFenceError(f"Refusing to overwrite existing output file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown_text, encoding="utf-8")
    return target

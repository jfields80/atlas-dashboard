from __future__ import annotations

import os
import subprocess
from pathlib import Path


APPROVED_ROOT = Path(r"C:\Atlas-Grok")


class PathFenceError(ValueError):
    """Raised when an ACDIS path falls outside the approved worktree."""


def get_approved_root() -> Path:
    return APPROVED_ROOT.resolve()


def get_active_git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(APPROVED_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise PathFenceError("Unable to resolve the active Git root")
    return Path(result.stdout.strip()).resolve()


def ensure_acdis_path(path: str | os.PathLike[str]) -> Path:
    candidate = Path(path).expanduser()
    resolved = candidate.resolve(strict=False)
    approved = get_approved_root()

    if resolved == approved:
        return approved

    if not str(resolved).startswith(str(approved)):
        raise PathFenceError(f"Rejected path outside approved worktree: {resolved}")

    if resolved.drive.lower() != approved.drive.lower():
        raise PathFenceError(f"Rejected path on different drive: {resolved}")

    if resolved == approved.parent:
        raise PathFenceError(f"Rejected path that resolves to Atlas root: {resolved}")

    if resolved == Path(r"C:\Atlas"):
        raise PathFenceError(f"Rejected Atlas root: {resolved}")

    return resolved

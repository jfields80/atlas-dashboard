import pytest

from acdis.safeguards.path_fence import PathFenceError, ensure_acdis_path, get_active_git_root, get_approved_root


def test_path_fence_accepts_approved_worktree():
    approved = get_approved_root()
    resolved = ensure_acdis_path(approved)
    assert resolved == approved


def test_path_fence_rejects_primary_atlas_root():
    with pytest.raises(PathFenceError):
        ensure_acdis_path(r"C:\Atlas")


def test_path_fence_rejects_unrelated_root():
    with pytest.raises(PathFenceError):
        ensure_acdis_path(r"C:\Windows")


def test_path_fence_rejects_escape_path():
    approved = get_approved_root()
    with pytest.raises(PathFenceError):
        ensure_acdis_path(str(approved.parent / "outside"))


def test_active_git_root_matches_worktree():
    assert get_active_git_root() == get_approved_root()

"""Tests for the worker-artifact backup/restore tooling (Phase 1).

Every test builds its own synthetic tree under ``tmp_path``. No test reads,
writes, or copies a real worker artifact, and no test writes anywhere inside
the repository. The two assertions that look at real repository state
(attestation index cleanliness) are read-only and skip when the file is absent.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import backup_worker_artifacts as bak  # noqa: E402
from scripts.pettripfinder import restore_worker_artifacts as res  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures -- entirely synthetic
# --------------------------------------------------------------------------- #

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture()
def source_tree(tmp_path: Path) -> Path:
    """A miniature worker-run tree with one of every artifact class."""
    root = tmp_path / "src" / "pettripfinder"

    capture_body = b'{"html": "<html>synthetic capture body</html>"}'
    screenshot = b"\x89PNG\r\n\x1a\n synthetic screenshot bytes"
    cas_digest = sha(screenshot)

    files = {
        "attestation_batch_001/attestations/attest-aaa.json": json.dumps({
            "attestation_id": "attest-aaa",
            "attestation_hash": "sha256:" + "a" * 64,
            "listing_key": "synthetic hotel one",
            "observed_at": "2026-07-29T14:42:41.806Z",
            "publishable": True,
            "official_url": "https://example.com/hotels/one/overview",
            "affirmation": {"operator_id": "testoperator"},
            "approval": {"approver_id": "testoperator", "state": "APPROVED"},
            "ingestion": {"listing_key": "synthetic hotel one",
                          "canonical_url": "https://example.com/hotels/one/overview"},
            "screenshots": [{"sha256": cas_digest, "byte_length": len(screenshot)}],
        }).encode("utf-8"),
        "attestation_batch_001/captures/example-com-one.json": capture_body,
        f"attestation_batch_001/cas/objects/{cas_digest[:2]}/{cas_digest}.bin": screenshot,
        "attestation_batch_001/retrieval/retr-one.json": b'{"status": "ACCESS_BLOCKED"}',
        "columbus_hotel_pilot/model_results/mr-1.json": b'{"model": "synthetic"}',
        "columbus_hotel_pilot/assignments/as-1.json": b'{"assignment_id": "as-1"}',
        "columbus_hotel_pilot/validated_results/vr-1.json": b'{"status": "READY"}',
        "columbus_hotel_pilot/routing_envelopes/re-1.json": b'{"route": "READY"}',
        "operator_summary.json": b'{"note": "synthetic"}',
        # Excluded rendered previews, at two different depths:
        "boundary_preview/site/index.html": b"<html>preview</html>",
        "boundary_preview/site/go/a/index.html": b"<html>preview nested</html>",
        "inventory16_preview/site/about/index.html": b"<html>preview</html>",
    }
    for rel, data in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return root


@pytest.fixture()
def backup_root(tmp_path: Path) -> Path:
    return tmp_path / "backups"


def make_snapshot(source_tree: Path, backup_root: Path, name: str = "snap-1") -> Path:
    bak.create_snapshot(source_tree, backup_root, snapshot_name=name)
    return backup_root / "snapshots" / name


# --------------------------------------------------------------------------- #
# Backup: happy path and exclusions
# --------------------------------------------------------------------------- #

def test_successful_snapshot(source_tree, backup_root):
    manifest = bak.create_snapshot(source_tree, backup_root, snapshot_name="snap-1")
    snap = backup_root / "snapshots" / "snap-1"
    assert snap.is_dir()
    assert (snap / "manifest.json").is_file()
    assert (snap / "manifest.sha256").is_file()
    assert manifest["totals"]["files"] == 9  # 12 written, 3 under site/
    assert not (backup_root / "snapshots" / "snap-1-partial").exists()


def test_site_directories_excluded(source_tree, backup_root):
    manifest = bak.create_snapshot(source_tree, backup_root, snapshot_name="s")
    paths = [e["relative_path"] for e in manifest["files"]]
    assert not any("/site/" in p or p.startswith("site/") for p in paths)
    assert not (backup_root / "snapshots" / "s" / "payload" / "boundary_preview" / "site").exists()


def test_manifest_paths_are_posix_and_relative(source_tree, backup_root):
    manifest = bak.create_snapshot(source_tree, backup_root, snapshot_name="s")
    for entry in manifest["files"]:
        rel = entry["relative_path"]
        assert "\\" not in rel, f"backslash in manifest path: {rel}"
        assert not rel.startswith("/")
        assert not re.match(r"^[A-Za-z]:", rel)
        assert set(entry) >= {
            "relative_path", "byte_size", "sha256",
            "artifact_class", "snapshot_timestamp_utc",
        }


def test_artifact_classes_assigned(source_tree, backup_root):
    manifest = bak.create_snapshot(source_tree, backup_root, snapshot_name="s")
    classes = {e["artifact_class"] for e in manifest["files"]}
    assert {"attestation", "capture", "cas_object", "retrieval",
            "model_result", "assignment", "validated_result",
            "routing_envelope"} <= classes
    assert "derived_preview" not in classes


def test_copied_file_hashes_match_source(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        # Payload is namespaced: payload/<source_namespace>/<relative_path>
        copied = snap / "payload" / entry["source_namespace"] / entry["relative_path"]
        assert sha(copied.read_bytes()) == entry["sha256"]
        assert copied.stat().st_size == entry["byte_size"]


def test_dry_run_writes_nothing(source_tree, backup_root):
    manifest = bak.create_snapshot(source_tree, backup_root, snapshot_name="s", dry_run=True)
    assert manifest["dry_run"] is True
    assert manifest["totals"]["files"] == 9
    assert not backup_root.exists()


# --------------------------------------------------------------------------- #
# Backup: refusals
# --------------------------------------------------------------------------- #

def test_missing_source_root_refused(tmp_path, backup_root):
    with pytest.raises(bak.BackupError, match="source root does not exist"):
        bak.create_snapshot(tmp_path / "nope", backup_root)


def test_backup_root_inside_repository_refused(source_tree, tmp_path):
    """A .git anywhere above the source makes that whole tree off-limits."""
    repo = tmp_path / "src"
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    with pytest.raises(bak.BackupError, match="inside the git repository"):
        bak.create_snapshot(source_tree, repo / "backups")


def test_backup_root_inside_repository_refused_with_relative_paths(
    source_tree, tmp_path, monkeypatch
):
    """Regression: relative roots must not bypass the in-repository refusal.

    find_repo_root() previously walked an unresolved path, so a relative
    --source-root produced parents that never contained .git, silently
    disabling the check. A real snapshot was written inside the repo.
    """
    (tmp_path / "src" / ".git").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path / "src")
    with pytest.raises(bak.BackupError, match="inside the git repository"):
        bak.create_snapshot(Path("pettripfinder"), Path("tmpbk"))
    assert not (tmp_path / "src" / "tmpbk").exists(), "wrote despite refusal"


def test_find_repo_root_resolves_relative_paths(source_tree, tmp_path, monkeypatch):
    (tmp_path / "src" / ".git").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path / "src")
    assert bak.find_repo_root(Path("pettripfinder")) == (tmp_path / "src").resolve()
    assert bak.find_repo_root(Path(".")) == (tmp_path / "src").resolve()


def test_deeply_nested_relative_source_still_finds_repo(tmp_path, monkeypatch):
    """Mirrors the real layout: repo root two levels above the working dir."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    src = repo / "dash" / "data" / "worker_runs" / "ptf"
    src.mkdir(parents=True)
    (src / "a.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(repo / "dash")
    with pytest.raises(bak.BackupError, match="inside the git repository"):
        bak.create_snapshot(Path("data/worker_runs/ptf"), Path("tmpbk"))
    assert not (repo / "dash" / "tmpbk").exists()


def test_backup_root_inside_source_root_refused(source_tree):
    with pytest.raises(bak.BackupError, match="inside the source root"):
        bak.create_snapshot(source_tree, source_tree / "backups")


def test_source_inside_backup_root_refused(source_tree, tmp_path):
    with pytest.raises(bak.BackupError, match="inside the backup root"):
        bak.create_snapshot(source_tree, source_tree.parent)


def test_snapshot_name_collision_refused(source_tree, backup_root):
    bak.create_snapshot(source_tree, backup_root, snapshot_name="dup")
    with pytest.raises(bak.BackupError, match="already exists"):
        bak.create_snapshot(source_tree, backup_root, snapshot_name="dup")


def test_partial_not_promoted_on_failure(source_tree, backup_root, monkeypatch):
    """A verification failure mid-copy must leave -partial and no final dir."""
    real = bak.sha256_file
    calls = {"n": 0}

    def flaky(path):
        calls["n"] += 1
        if calls["n"] > 12:          # fail during the post-copy verify pass
            return ("0" * 64, 0)
        return real(path)

    monkeypatch.setattr(bak, "sha256_file", flaky)
    with pytest.raises(bak.BackupError, match="destination verification failed"):
        bak.create_snapshot(source_tree, backup_root, snapshot_name="boom")
    assert not (backup_root / "snapshots" / "boom").exists()
    assert (backup_root / "snapshots" / "boom-partial").exists()


def test_existing_partial_refused(source_tree, backup_root):
    (backup_root / "snapshots" / "x-partial").mkdir(parents=True)
    with pytest.raises(bak.BackupError, match="partial snapshot already exists"):
        bak.create_snapshot(source_tree, backup_root, snapshot_name="x")


# --------------------------------------------------------------------------- #
# Verification: tamper detection
# --------------------------------------------------------------------------- #

def test_verify_clean_snapshot(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    result = res.restore_snapshot(snap, snap, verify_only=True)
    assert result["files_verified"] == 9


def test_tampered_payload_detected(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    victim = next((snap / "payload").rglob("*.json"))
    victim.write_bytes(victim.read_bytes() + b" ")
    with pytest.raises(res.RestoreError, match="failed SHA-256"):
        res.restore_snapshot(snap, snap, verify_only=True)


def test_one_byte_corruption_detected(source_tree, backup_root):
    """Negative test: a single flipped byte must fail verification."""
    snap = make_snapshot(source_tree, backup_root)
    victim = next((snap / "payload").rglob("*.bin"))
    data = bytearray(victim.read_bytes())
    data[0] ^= 0x01
    victim.write_bytes(bytes(data))
    with pytest.raises(res.RestoreError, match="failed SHA-256"):
        res.restore_snapshot(snap, snap, verify_only=True)


def test_tampered_manifest_detected(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][0]["byte_size"] = 999999
    (snap / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(res.RestoreError, match="manifest integrity check FAILED"):
        res.restore_snapshot(snap, snap, verify_only=True)


def test_missing_payload_file_detected(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    next((snap / "payload").rglob("*.json")).unlink()
    with pytest.raises(res.RestoreError, match="missing payload file"):
        res.restore_snapshot(snap, snap, verify_only=True)


def test_extra_payload_file_detected(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    (snap / "payload" / "smuggled.json").write_text("{}", encoding="utf-8")
    with pytest.raises(res.RestoreError, match="undeclared file"):
        res.restore_snapshot(snap, snap, verify_only=True)


def test_missing_manifest_hash_detected(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    (snap / "manifest.sha256").unlink()
    with pytest.raises(res.RestoreError, match="missing manifest.sha256"):
        res.restore_snapshot(snap, snap, verify_only=True)


# --------------------------------------------------------------------------- #
# Restore
# --------------------------------------------------------------------------- #

def test_restore_to_clean_directory(source_tree, backup_root, tmp_path):
    snap = make_snapshot(source_tree, backup_root)
    dest = tmp_path / "restored"
    result = res.restore_snapshot(snap, dest)
    assert result["files_written"] == 9
    manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        out = dest / entry["relative_path"]
        assert out.is_file()
        assert sha(out.read_bytes()) == entry["sha256"]
    assert not list(dest.glob(".restore-staging-*")), "staging dir left behind"


def test_restore_refuses_existing_file(source_tree, backup_root, tmp_path):
    snap = make_snapshot(source_tree, backup_root)
    dest = tmp_path / "restored"
    res.restore_snapshot(snap, dest)
    with pytest.raises(res.RestoreError, match="refusing to overwrite"):
        res.restore_snapshot(snap, dest)


def test_allow_existing_identical_skips(source_tree, backup_root, tmp_path):
    snap = make_snapshot(source_tree, backup_root)
    dest = tmp_path / "restored"
    res.restore_snapshot(snap, dest)
    result = res.restore_snapshot(snap, dest, allow_existing_identical=True)
    assert result["files_written"] == 0
    assert result["files_skipped_identical"] == 9


def test_differing_file_never_overwritten_even_with_flag(source_tree, backup_root, tmp_path):
    snap = make_snapshot(source_tree, backup_root)
    dest = tmp_path / "restored"
    res.restore_snapshot(snap, dest)
    manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    victim = dest / manifest["files"][0]["relative_path"]
    original = victim.read_bytes()
    victim.write_bytes(b"locally modified")
    with pytest.raises(res.RestoreError, match="refusing to overwrite"):
        res.restore_snapshot(snap, dest, allow_existing_identical=True)
    assert victim.read_bytes() == b"locally modified"  # untouched
    assert original != b"locally modified"


def test_restore_never_deletes_unrelated_files(source_tree, backup_root, tmp_path):
    snap = make_snapshot(source_tree, backup_root)
    dest = tmp_path / "restored"
    dest.mkdir()
    keep = dest / "pre-existing.txt"
    keep.write_text("keep me", encoding="utf-8")
    res.restore_snapshot(snap, dest)
    assert keep.read_text(encoding="utf-8") == "keep me"


# --------------------------------------------------------------------------- #
# Evidence-chain integrity (synthetic)
# --------------------------------------------------------------------------- #

def test_cas_filename_matches_content_hash(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    objects = list((snap / "payload").rglob("cas/objects/*/*.bin"))
    assert objects, "fixture should contain a CAS object"
    for obj in objects:
        assert sha(obj.read_bytes()) == obj.stem
        assert obj.parent.name == obj.stem[:2]


def test_attestation_resolves_to_cas_object(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    payload = snap / "payload"
    attestations = list(payload.rglob("attestations/*.json"))
    assert attestations
    for path in attestations:
        record = json.loads(path.read_text(encoding="utf-8"))
        for shot in record.get("screenshots", []):
            digest = shot["sha256"]
            batch = path.parents[1]
            target = batch / "cas" / "objects" / digest[:2] / f"{digest}.bin"
            assert target.is_file(), f"attestation cites a missing CAS object: {digest[:12]}"
            assert sha(target.read_bytes()) == digest


# --------------------------------------------------------------------------- #
# Attestation index
# --------------------------------------------------------------------------- #

def test_index_contains_only_allowed_fields(source_tree):
    index = bak.build_attestation_index(source_tree)
    allowed = {
        "listing_key", "attestation_id", "attestation_hash", "observed_at",
        "operator_id", "capture_sha256", "publishable", "source_url",
        "source_url_omitted", "source_url_omission_reason",
    }
    assert index["totals"]["attestations"] == 1
    for entry in index["attestations"]:
        assert set(entry) <= allowed, f"unexpected field(s): {set(entry) - allowed}"


def test_index_excludes_payload_content(source_tree):
    """Assert against the entries, not the descriptive header.

    The schema `description` legitimately contains words like "HTML" and
    "cookies" while explaining what is excluded; only the records matter.
    """
    blob = json.dumps(bak.build_attestation_index(source_tree)["attestations"])
    for forbidden in ("<html", "synthetic capture body", "png", "screenshot",
                      "cookie", "authorization", "set-cookie"):
        assert forbidden not in blob.lower(), f"index leaked: {forbidden}"


@pytest.mark.parametrize("url,safe,reason_fragment", [
    ("https://www.marriott.com/en-us/hotels/cmhcw-overview", True, ""),
    ("https://example.com/a?utm_source=x", True, ""),
    ("http://localhost:8080/page", False, "private_or_local_host"),
    ("http://127.0.0.1/page", False, "private_or_local_host"),
    ("http://192.168.1.4/page", False, "private_or_local_host"),
    ("file:///C:/Atlas/secret.html", False, "non_web_scheme"),
    ("https://user:pw@example.com/a", False, "embedded_userinfo"),
    ("https://example.com/a?token=abc123", False, "credentialed_query_parameter"),
    ("https://example.com/a?X-Amz-Signature=deadbeef", False, "credentialed_query_parameter"),
    ("https://example.com/a?sessionid=zzz", False, "credentialed_query_parameter"),
    ("https://example.com/a?k=AIzaSyEXAMPLEEXAMPLEEXAMPLEEXAMPLE00000", False, ""),
    ("", False, "missing_or_non_string"),
])
def test_source_url_safety(url, safe, reason_fragment):
    ok, reason = bak.source_url_safety(url)
    assert ok is safe, f"{url} -> {ok} ({reason})"
    if not safe and reason_fragment:
        assert reason_fragment in reason


def test_unsafe_url_is_omitted_with_reason(tmp_path):
    root = tmp_path / "s"
    rec = root / "b/attestations/a.json"
    rec.parent.mkdir(parents=True)
    rec.write_text(json.dumps({
        "attestation_id": "attest-x",
        "listing_key": "k",
        "official_url": "https://example.com/a?access_token=SECRETVALUE123",
        "screenshots": [{"sha256": "0" * 64}],
    }), encoding="utf-8")
    entry = bak.build_attestation_index(root)["attestations"][0]
    assert entry.get("source_url_omitted") is True
    # Either refusal is correct: the credential-shaped-token scan fires before
    # query-parameter inspection. What matters is that it is refused with a
    # recorded reason and the value never lands in the index.
    assert entry["source_url_omission_reason"] in (
        "credential_pattern_in_url",
        "credentialed_query_parameter:access_token",
    )
    assert "source_url" not in entry
    assert "SECRETVALUE123" not in json.dumps(entry)


# --------------------------------------------------------------------------- #
# No absolute paths / no secrets in emitted metadata
# --------------------------------------------------------------------------- #

SECRET_RX = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"nfp_[A-Za-z0-9]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
]
# A drive letter must not be preceded by another letter, otherwise the "s" in
# "https://" reads as a drive. This matches C:\ and C:/ but never a URL scheme.
ABSPATH_RX = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]|(?<![\w.:])/(?:Users|home)/")


def test_manifest_has_no_absolute_paths_or_secrets(source_tree, backup_root):
    snap = make_snapshot(source_tree, backup_root)
    text = (snap / "manifest.json").read_text(encoding="utf-8")
    assert not ABSPATH_RX.search(text), "absolute path leaked into manifest"
    for rx in SECRET_RX:
        assert not rx.search(text), f"secret pattern in manifest: {rx.pattern}"


def test_index_has_no_absolute_paths_or_secrets(source_tree):
    text = json.dumps(bak.build_attestation_index(source_tree), indent=2)
    assert not ABSPATH_RX.search(text), "absolute path leaked into index"
    for rx in SECRET_RX:
        assert not rx.search(text), f"secret pattern in index: {rx.pattern}"


# Phase 1B: the index lives in tracked docs/, NOT under gitignored data/.
REAL_INDEX = (REPO_ROOT / "docs" / "pettripfinder" / "artifact_indexes"
              / "attestation_index.json")
LEGACY_INDEX = (REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                / "_index" / "attestation_index.json")


def test_tracked_index_exists_at_docs_path():
    assert REAL_INDEX.is_file(), (
        "the attestation index must live at docs/pettripfinder/artifact_indexes/ "
        "so git can actually track it"
    )


def test_legacy_ignored_index_removed():
    assert not LEGACY_INDEX.exists(), (
        "the old index under gitignored data/ must be removed once the tracked "
        "replacement is verified"
    )


def test_tracked_index_path_is_not_gitignored():
    """The whole point of the move: git must be able to track this file."""
    import subprocess
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT.parent), "check-ignore", "-q",
         REAL_INDEX.relative_to(REPO_ROOT.parent).as_posix()],
        capture_output=True,
    )
    assert proc.returncode != 0, "tracked index path is gitignored"


def test_tracked_index_is_clean():
    """Read-only guard on the git-tracked index: no secrets, no absolute paths."""
    text = REAL_INDEX.read_text(encoding="utf-8")
    assert not ABSPATH_RX.search(text), "absolute path in tracked attestation index"
    for rx in SECRET_RX:
        assert not rx.search(text), f"secret pattern in tracked index: {rx.pattern}"
    for forbidden in ("<html", "set-cookie", "authorization"):
        assert forbidden not in text.lower(), f"tracked index leaked: {forbidden}"
    index = json.loads(text)
    allowed = {
        "listing_key", "attestation_id", "attestation_hash", "observed_at",
        "operator_id", "capture_sha256", "publishable", "source_url",
        "source_url_omitted", "source_url_omission_reason",
    }
    for entry in index["attestations"]:
        assert set(entry) <= allowed


# --------------------------------------------------------------------------- #
# Redaction
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Phase 1B -- multiple source roots and namespaces
# --------------------------------------------------------------------------- #

@pytest.fixture()
def second_tree(tmp_path: Path) -> Path:
    """A second artifact tree that deliberately reuses relative path names."""
    root = tmp_path / "src2" / "import_wave"
    files = {
        # Same relative path as the first tree -> would collide without namespaces
        "attestation_batch_001/attestations/attest-aaa.json": b'{"attestation_id":"other"}',
        "candidates/example-com-1.json": b'{"candidate_id":"c1"}',
        "reports/example-com-1.json": b'{"report":"r1"}',
        "site/index.html": b"<html>excluded</html>",
    }
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return root


def test_multiple_source_roots_snapshot(source_tree, second_tree, backup_root):
    manifest = bak.create_snapshot(
        backup_root=backup_root, snapshot_name="multi",
        source_roots={"worker_runs": source_tree, "import_wave": second_tree},
    )
    assert set(manifest["sources"]) == {"worker_runs", "import_wave"}
    assert manifest["sources"]["worker_runs"]["files"] == 9
    assert manifest["sources"]["import_wave"]["files"] == 3   # site/ excluded
    assert manifest["totals"]["files"] == 12
    payload = backup_root / "snapshots" / "multi" / "payload"
    assert (payload / "worker_runs").is_dir() and (payload / "import_wave").is_dir()


def test_identical_relative_paths_across_roots_do_not_collide(
    source_tree, second_tree, backup_root
):
    bak.create_snapshot(
        backup_root=backup_root, snapshot_name="multi",
        source_roots={"worker_runs": source_tree, "import_wave": second_tree},
    )
    payload = backup_root / "snapshots" / "multi" / "payload"
    a = payload / "worker_runs" / "attestation_batch_001/attestations/attest-aaa.json"
    b = payload / "import_wave" / "attestation_batch_001/attestations/attest-aaa.json"
    assert a.is_file() and b.is_file()
    assert a.read_bytes() != b.read_bytes(), "one root overwrote the other"


def test_every_manifest_entry_records_its_namespace(source_tree, second_tree, backup_root):
    manifest = bak.create_snapshot(
        backup_root=backup_root, snapshot_name="m",
        source_roots={"worker_runs": source_tree, "import_wave": second_tree},
    )
    assert all(e.get("source_namespace") in {"worker_runs", "import_wave"}
               for e in manifest["files"])


def test_site_excluded_in_every_root(source_tree, second_tree, backup_root):
    manifest = bak.create_snapshot(
        backup_root=backup_root, snapshot_name="m",
        source_roots={"worker_runs": source_tree, "import_wave": second_tree},
    )
    assert not any("site/" in e["relative_path"] for e in manifest["files"])


def test_duplicate_namespace_refused():
    with pytest.raises(bak.BackupError, match="duplicate source namespace"):
        bak.collect_source_roots(["ns=a/b", "ns=c/d"])


def test_same_path_twice_refused(source_tree):
    with pytest.raises(bak.BackupError, match="supplied twice"):
        bak.collect_source_roots([f"one={source_tree}", f"two={source_tree}"])


def test_two_namespaces_same_tree_refused(source_tree, backup_root):
    with pytest.raises(bak.BackupError, match="resolve to the same source root"):
        bak.create_snapshot(
            backup_root=backup_root,
            source_roots={"a": source_tree, "b": source_tree},
        )


@pytest.mark.parametrize("bad", ["=path", "bad/ns=path", "bad ns=path", "bad\\ns=path"])
def test_invalid_namespace_refused(bad):
    with pytest.raises(bak.BackupError):
        bak.parse_source_arg(bad)


def test_no_source_root_refused():
    with pytest.raises(bak.BackupError, match="at least one --source-root"):
        bak.collect_source_roots([])


def test_repo_refusal_applies_to_every_root(source_tree, second_tree, tmp_path):
    """A second root inside a repo must be refused just like the first."""
    (tmp_path / "src2" / ".git").mkdir(parents=True, exist_ok=True)
    with pytest.raises(bak.BackupError, match="inside the git repository"):
        bak.create_snapshot(
            backup_root=tmp_path / "src2" / "bk",
            source_roots={"a": source_tree, "b": second_tree},
        )


def test_source_roots_unmodified_by_snapshot(source_tree, second_tree, backup_root):
    def fingerprint(root):
        return {p.relative_to(root).as_posix(): sha(p.read_bytes())
                for p in sorted(root.rglob("*")) if p.is_file()}
    before = (fingerprint(source_tree), fingerprint(second_tree))
    bak.create_snapshot(backup_root=backup_root, snapshot_name="m",
                        source_roots={"a": source_tree, "b": second_tree})
    assert (fingerprint(source_tree), fingerprint(second_tree)) == before


# --------------------------------------------------------------------------- #
# Phase 1B -- namespaced restore
# --------------------------------------------------------------------------- #

def make_multi(source_tree, second_tree, backup_root, name="multi") -> Path:
    bak.create_snapshot(backup_root=backup_root, snapshot_name=name,
                        source_roots={"worker_runs": source_tree,
                                      "import_wave": second_tree})
    return backup_root / "snapshots" / name


def test_multi_root_verify_only(source_tree, second_tree, backup_root):
    snap = make_multi(source_tree, second_tree, backup_root)
    result = res.restore_snapshot(snap, verify_only=True)
    assert result["files_verified"] == 12


def test_restore_requires_mapping_per_namespace(source_tree, second_tree, backup_root, tmp_path):
    snap = make_multi(source_tree, second_tree, backup_root)
    with pytest.raises(res.RestoreError, match="no destination mapping"):
        res.restore_snapshot(snap, destinations={"worker_runs": tmp_path / "w"})


def test_restore_refuses_bare_root_for_multi_namespace(source_tree, second_tree,
                                                       backup_root, tmp_path):
    snap = make_multi(source_tree, second_tree, backup_root)
    with pytest.raises(res.RestoreError, match="no destination mapping"):
        res.restore_snapshot(snap, destination_root=tmp_path / "everything")


def test_restore_refuses_unknown_namespace_mapping(source_tree, second_tree,
                                                   backup_root, tmp_path):
    snap = make_multi(source_tree, second_tree, backup_root)
    with pytest.raises(res.RestoreError, match="not in this snapshot"):
        res.restore_snapshot(snap, destinations={
            "worker_runs": tmp_path / "w",
            "import_wave": tmp_path / "i",
            "typo_wave": tmp_path / "t",
        })


def test_multi_root_restore_places_each_namespace(source_tree, second_tree,
                                                  backup_root, tmp_path):
    snap = make_multi(source_tree, second_tree, backup_root)
    w, i = tmp_path / "dest_w", tmp_path / "dest_i"
    result = res.restore_snapshot(snap, destinations={"worker_runs": w, "import_wave": i})
    assert result["files_written"] == 12
    assert (w / "attestation_batch_001/attestations/attest-aaa.json").is_file()
    assert (i / "candidates/example-com-1.json").is_file()
    # The colliding name landed in both destinations with the right bytes.
    a = w / "attestation_batch_001/attestations/attest-aaa.json"
    b = i / "attestation_batch_001/attestations/attest-aaa.json"
    assert a.read_bytes() != b.read_bytes()
    assert not list(w.glob(".restore-staging-*"))


def test_multi_root_tamper_still_detected(source_tree, second_tree, backup_root):
    snap = make_multi(source_tree, second_tree, backup_root)
    victim = snap / "payload" / "import_wave" / "candidates" / "example-com-1.json"
    victim.write_bytes(victim.read_bytes() + b" ")
    with pytest.raises(res.RestoreError, match="failed SHA-256"):
        res.restore_snapshot(snap, verify_only=True)


def test_multi_root_manifest_has_no_secrets_or_abspaths(source_tree, second_tree, backup_root):
    snap = make_multi(source_tree, second_tree, backup_root)
    text = (snap / "manifest.json").read_text(encoding="utf-8")
    assert not ABSPATH_RX.search(text)
    for rx in SECRET_RX:
        assert not rx.search(text)
    # Namespaces are logical labels, never filesystem locations.
    assert "src2" not in text and "tmp" not in text.lower().split('"snapshot_id"')[0]


def test_redaction_masks_known_patterns():
    # Both literals below are synthetic placeholders, never real credentials.
    dirty = "failed on AIzaSyEXAMPLEEXAMPLEEXAMPLEEXAMPLE00000 and nfp_EXAMPLEEXAMPLE"
    clean = bak.redact(dirty)
    assert "AIzaSy" not in clean and "nfp_" not in clean
    assert clean.count("[REDACTED]") == 2
    assert res.redact(dirty) == clean

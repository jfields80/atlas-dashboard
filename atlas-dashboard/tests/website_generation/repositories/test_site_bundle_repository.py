"""Site Bundle Repository tests (AES-WEB-001 §9.3; AES-WEB-002J.12).

Covers: successful materialization, integrity verification (pre- and
post-write), path safety, symlink defense-in-depth, destination policy,
determinism, the architectural import/schema boundary, and browser-openable
readiness (via a genuine Renderer+Assembly bundle).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from engines.website_generation import (
    ArtifactKind,
    BundleFile,
    SiteBundle,
    canonical_json,
    sha256_of_text,
)
from engines.website_generation.contracts.errors import (
    SiteBundleRepositoryError,
    WebsiteGenerationError,
)
import repositories.site_bundle_repository as sbr_module
from repositories.site_bundle_repository import (
    MANIFEST_FILENAME,
    SiteBundleMaterialization,
    SiteBundleRepository,
)

from ..gates._qge_fixtures import real_bundle

# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _bundle_with_files(pages: dict) -> SiteBundle:
    files = tuple(BundleFile(path=p, content=c) for p, c in sorted(pages.items()))
    file_map = {bf.path: sha256_of_text(bf.content) for bf in files}
    return SiteBundle(
        schema_version="1.1.0",
        artifact_kind=ArtifactKind.SITE_BUNDLE,
        source_hashes={},
        file_map=file_map,
        bundle_hash=sha256_of_text(canonical_json(file_map)),
        files=files,
    )


def _single_file_bundle(path: str, content: str = "<!doctype html><html><body>x</body></html>") -> SiteBundle:
    return _bundle_with_files({path: content})


def _full_bundle() -> SiteBundle:
    return _bundle_with_files(
        {
            "index.html": "<!doctype html><html><head><title>Home</title></head><body><p>Home</p></body></html>",
            "hotels/index.html": "<!doctype html><html><head><title>Hotels</title></head><body><p>Hotels</p></body></html>",
            "styles.css": "body{margin:0}",
            "sitemap.xml": '<?xml version="1.0" encoding="UTF-8"?><urlset></urlset>',
            "robots.txt": "User-agent: *\nAllow: /\n",
        }
    )


def _staging_path_for(destination: Path) -> Path:
    return destination.parent / f".{destination.name}.__staging__"


@pytest.fixture(scope="module")
def symlinks_supported(tmp_path_factory) -> bool:
    base = tmp_path_factory.mktemp("symlink_probe")
    target = base / "target"
    target.mkdir()
    link = base / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        return False
    return True


def _try_create_junction(link: Path, target: Path) -> bool:
    """NTFS junction via ``mklink /J`` -- unlike symlinks, junctions need no
    special privilege on Windows, making them a realistic, low-bar attack
    surface distinct from symlinks (``Path.is_symlink()`` does not detect
    them; the repository's ``_is_symlink_or_reparse_point`` helper does)."""
    if sys.platform != "win32":
        return False
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and link.exists()


@pytest.fixture(scope="module")
def junctions_supported(tmp_path_factory) -> bool:
    if sys.platform != "win32":
        return False
    base = tmp_path_factory.mktemp("junction_probe")
    target = base / "target"
    target.mkdir()
    link = base / "link"
    return _try_create_junction(link, target)


# ---------------------------------------------------------------------------
# A. Successful materialization
# ---------------------------------------------------------------------------


class TestSuccessfulMaterialization:
    def test_root_and_nested_and_system_files_written(self, tmp_path):
        bundle = _full_bundle()
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        for expected in ("index.html", "hotels/index.html", "styles.css", "sitemap.xml", "robots.txt"):
            assert (destination / expected).exists(), expected

    def test_exact_utf8_bytes_preserved(self, tmp_path):
        content = "<!doctype html><html><body>café ☃</body></html>"
        bundle = _single_file_bundle("index.html", content)
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        assert (destination / "index.html").read_bytes() == content.encode("utf-8")

    def test_nested_directories_created(self, tmp_path):
        bundle = _bundle_with_files(
            {"hotels/luxury/index.html": "<!doctype html><html><body>L</body></html>"}
        )
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        assert (destination / "hotels" / "luxury" / "index.html").is_file()

    def test_result_metadata(self, tmp_path):
        bundle = _full_bundle()
        destination = tmp_path / "site"
        result = SiteBundleRepository().materialize(bundle, destination)
        assert isinstance(result, SiteBundleMaterialization)
        assert result.destination == str(destination)
        assert result.written_paths == tuple(sorted(bundle.file_map))
        assert result.bundle_hash == bundle.bundle_hash
        assert result.manifest_path == MANIFEST_FILENAME

    def test_manifest_with_build_id(self, tmp_path):
        bundle = _full_bundle()
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination, build_id="build-42")
        import json

        manifest = json.loads((destination / MANIFEST_FILENAME).read_text(encoding="utf-8"))
        assert manifest["build_id"] == "build-42"
        assert manifest["bundle_hash"] == bundle.bundle_hash
        assert manifest["file_map"] == bundle.file_map

    def test_manifest_without_build_id_omits_field(self, tmp_path):
        bundle = _full_bundle()
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        raw = (destination / MANIFEST_FILENAME).read_text(encoding="utf-8")
        assert "build_id" not in raw

    def test_manifest_is_deterministic_utf8_lf_sorted_with_trailing_newline(self, tmp_path):
        bundle = _full_bundle()
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        raw_bytes = (destination / MANIFEST_FILENAME).read_bytes()
        text = raw_bytes.decode("utf-8")
        assert "\r\n" not in text
        assert text.endswith("\n")
        assert raw_bytes == text.encode("utf-8")


# ---------------------------------------------------------------------------
# B. Integrity
# ---------------------------------------------------------------------------


class TestIntegrity:
    def test_valid_bundle_succeeds(self, tmp_path):
        bundle = _full_bundle()
        result = SiteBundleRepository().materialize(bundle, tmp_path / "site")
        assert result.bundle_hash == bundle.bundle_hash

    def test_content_hash_mismatch_rejected(self, tmp_path):
        bundle = _full_bundle()
        tampered = tuple(
            bf.copy(update={"content": bf.content + "TAMPERED"}) if bf.path == "index.html" else bf
            for bf in bundle.files
        )
        bad = bundle.copy(update={"files": tampered})
        destination = tmp_path / "site"
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bad, destination)
        assert excinfo.value.category == "content_hash_mismatch"
        assert not destination.exists()

    def test_file_map_missing_entry_rejected(self, tmp_path):
        bundle = _full_bundle()
        trimmed = dict(bundle.file_map)
        del trimmed["index.html"]
        bad = bundle.copy(update={"file_map": trimmed})
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bad, tmp_path / "site")
        assert excinfo.value.category == "mapping_mismatch"

    def test_file_map_unknown_entry_rejected(self, tmp_path):
        bundle = _full_bundle()
        extra = dict(bundle.file_map)
        extra["orphan.html"] = sha256_of_text("orphan")
        bad = bundle.copy(update={"file_map": extra})
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bad, tmp_path / "site")
        assert excinfo.value.category == "mapping_mismatch"

    def test_bundle_hash_mismatch_rejected(self, tmp_path):
        bundle = _full_bundle()
        bad = bundle.copy(update={"bundle_hash": "0" * 64})
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bad, tmp_path / "site")
        assert excinfo.value.category == "bundle_hash_mismatch"

    def test_duplicate_bundle_file_path_rejected(self, tmp_path):
        files = (
            BundleFile(path="index.html", content="A"),
            BundleFile(path="index.html", content="A"),
        )
        file_map = {"index.html": sha256_of_text("A")}
        bad = SiteBundle(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.SITE_BUNDLE,
            source_hashes={},
            file_map=file_map,
            bundle_hash=sha256_of_text(canonical_json(file_map)),
            files=files,
        )
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bad, tmp_path / "site")
        assert excinfo.value.category == "duplicate_path"

    def test_no_silent_repair_no_partial_output(self, tmp_path):
        bundle = _full_bundle()
        tampered = tuple(
            bf.copy(update={"content": "WRONG"}) if bf.path == "styles.css" else bf
            for bf in bundle.files
        )
        bad = bundle.copy(update={"files": tampered})
        destination = tmp_path / "site"
        with pytest.raises(SiteBundleRepositoryError):
            SiteBundleRepository().materialize(bad, destination)
        assert not destination.exists()

    def test_post_write_verification_failure_detected(self, tmp_path, monkeypatch):
        bundle = _full_bundle()
        destination = tmp_path / "site"
        original_read_bytes = Path.read_bytes

        def _tampered_read_bytes(self):
            data = original_read_bytes(self)
            if self.name == "index.html" and "hotels" not in self.parts:
                return data + b"TAMPERED-AFTER-WRITE"
            return data

        monkeypatch.setattr(Path, "read_bytes", _tampered_read_bytes)

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bundle, destination)
        assert excinfo.value.category == "post_write_verification_failure"
        assert not destination.exists()


# ---------------------------------------------------------------------------
# C. Path safety
# ---------------------------------------------------------------------------


class TestPathSafety:
    @pytest.mark.parametrize(
        "bad_path",
        [
            "/index.html",
            "//server/index.html",
            "C:/index.html",
            "C:\\index.html",
            "assets\\logo.svg",
            "../index.html",
            "assets/../../index.html",
            "CON/index.html",
            "assets/CON.txt",
            "assets/aux",
            "weird./index.html",
            "weird /index.html",
            "bad\x01name.html",
            "bad*name.html",
            "bad?name.html",
            'bad"name.html',
            "bad<name>.html",
            "bad|name.html",
            "bad:name.html",
        ],
    )
    def test_unsafe_path_rejected(self, tmp_path, bad_path):
        bundle = _single_file_bundle(bad_path)
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bundle, tmp_path / "site")
        assert excinfo.value.category == "unsafe_path"

    def test_case_only_collision_rejected(self, tmp_path):
        bundle = _bundle_with_files(
            {"About/index.html": "<html>A</html>", "about/index.html": "<html>B</html>"}
        )
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bundle, tmp_path / "site")
        assert excinfo.value.category == "case_collision"

    def test_file_directory_collision_rejected(self, tmp_path):
        files = (
            BundleFile(path="assets", content="A"),
            BundleFile(path="assets/logo.svg", content="B"),
        )
        file_map = {bf.path: sha256_of_text(bf.content) for bf in files}
        bundle = SiteBundle(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.SITE_BUNDLE,
            source_hashes={},
            file_map=file_map,
            bundle_hash=sha256_of_text(canonical_json(file_map)),
            files=files,
        )
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bundle, tmp_path / "site")
        assert excinfo.value.category == "file_directory_collision"

    def test_case_insensitive_file_directory_collision_rejected(self, tmp_path):
        # "Assets" and "assets/logo.svg" collide on a case-insensitive
        # filesystem (Windows NTFS, default macOS) even though the strings
        # differ in case.
        files = (
            BundleFile(path="Assets", content="A"),
            BundleFile(path="assets/logo.svg", content="B"),
        )
        file_map = {bf.path: sha256_of_text(bf.content) for bf in files}
        bundle = SiteBundle(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.SITE_BUNDLE,
            source_hashes={},
            file_map=file_map,
            bundle_hash=sha256_of_text(canonical_json(file_map)),
            files=files,
        )
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bundle, tmp_path / "site")
        assert excinfo.value.category == "file_directory_collision"


class TestContainmentPrimitive:
    """White-box: containment holds structurally once path syntax is
    validated (no relative path built from safe segments can escape a
    joined base), so this defense-in-depth primitive is unreachable via the
    public API. Tested directly."""

    def test_rejects_escaping_target(self, tmp_path):
        staging = tmp_path / "staging"
        staging.mkdir()
        escaping_target = staging / ".." / "escaped.html"
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository._assert_contained(escaping_target, staging)
        assert excinfo.value.category == "unsafe_path"

    def test_accepts_contained_target(self, tmp_path):
        staging = tmp_path / "staging"
        staging.mkdir()
        target = staging / "a" / "b.html"
        SiteBundleRepository._assert_contained(target, staging)  # no raise


# ---------------------------------------------------------------------------
# Symlink policy (fail-closed)
# ---------------------------------------------------------------------------


class TestSymlinkPolicyPublicAPI:
    def test_symlinked_destination_root_rejected(self, tmp_path, symlinks_supported):
        if not symlinks_supported:
            pytest.skip("platform/user cannot create symlinks")
        real_target = tmp_path / "real_target"
        real_target.mkdir()
        link = tmp_path / "linked_dest"
        link.symlink_to(real_target, target_is_directory=True)

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(_full_bundle(), link)
        assert excinfo.value.category == "symlink_detected"

    def test_symlinked_intermediate_ancestor_rejected(self, tmp_path, symlinks_supported):
        if not symlinks_supported:
            pytest.skip("platform/user cannot create symlinks")
        real_parent = tmp_path / "real_parent"
        real_parent.mkdir()
        linked_parent = tmp_path / "linked_parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        destination = linked_parent / "site"

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(_full_bundle(), destination)
        assert excinfo.value.category == "symlink_detected"

    def test_symlinked_staging_root_rejected(self, tmp_path, symlinks_supported):
        if not symlinks_supported:
            pytest.skip("platform/user cannot create symlinks")
        destination = tmp_path / "site"
        elsewhere = tmp_path / "elsewhere_dir"
        elsewhere.mkdir()
        staging = _staging_path_for(destination)
        staging.symlink_to(elsewhere, target_is_directory=True)

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(_full_bundle(), destination)
        assert excinfo.value.category == "symlink_detected"


class TestJunctionPolicyPublicAPI:
    """NTFS junctions require no elevated privilege (confirmed: ``mklink /J``
    succeeds for a standard user where ``os.symlink`` raises
    ``WinError 1314``) and redirect writes just as a symlink does --
    ``Path.is_symlink()`` alone does not detect them. Exercises the same
    three call sites as :class:`TestSymlinkPolicyPublicAPI` via a junction
    instead of a symlink."""

    def test_junction_destination_root_rejected(self, tmp_path, junctions_supported):
        if not junctions_supported:
            pytest.skip("junctions unavailable on this platform")
        real_target = tmp_path / "real_target"
        real_target.mkdir()
        link = tmp_path / "junction_dest"
        assert _try_create_junction(link, real_target)

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(_full_bundle(), link)
        assert excinfo.value.category == "symlink_detected"

    def test_junction_intermediate_ancestor_rejected(self, tmp_path, junctions_supported):
        if not junctions_supported:
            pytest.skip("junctions unavailable on this platform")
        real_parent = tmp_path / "real_parent"
        real_parent.mkdir()
        linked_parent = tmp_path / "junction_parent"
        assert _try_create_junction(linked_parent, real_parent)
        destination = linked_parent / "site"

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(_full_bundle(), destination)
        assert excinfo.value.category == "symlink_detected"

    def test_junction_staging_root_rejected(self, tmp_path, junctions_supported):
        if not junctions_supported:
            pytest.skip("junctions unavailable on this platform")
        destination = tmp_path / "site"
        elsewhere = tmp_path / "elsewhere_dir"
        elsewhere.mkdir()
        staging = _staging_path_for(destination)
        assert _try_create_junction(staging, elsewhere)

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(_full_bundle(), destination)
        assert excinfo.value.category == "symlink_detected"


class TestSymlinkDefenseInDepth:
    """White-box: with staging always freshly created by this repository
    (stale plain leftovers are wiped, never a symlink itself -- verified
    separately), no legitimate single-threaded call can inject a symlink
    file/directory *inside* a fresh staging tree mid-call. These branches
    are tested directly against a hand-seeded staging directory."""

    def test_write_files_refuses_existing_symlink_target(self, tmp_path, symlinks_supported):
        if not symlinks_supported:
            pytest.skip("platform/user cannot create symlinks")
        staging = tmp_path / "staging"
        staging.mkdir()
        elsewhere = tmp_path / "elsewhere.html"
        elsewhere.write_text("elsewhere")
        (staging / "index.html").symlink_to(elsewhere)

        bundle = _single_file_bundle("index.html")
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository()._write_files(bundle, staging)
        assert excinfo.value.category == "symlink_detected"

    def test_mkdir_checked_refuses_symlinked_intermediate_directory(self, tmp_path, symlinks_supported):
        if not symlinks_supported:
            pytest.skip("platform/user cannot create symlinks")
        staging = tmp_path / "staging"
        staging.mkdir()
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()
        (staging / "assets").symlink_to(real_dir, target_is_directory=True)

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository._mkdir_checked(staging / "assets" / "sub", staging)
        assert excinfo.value.category == "symlink_detected"


# ---------------------------------------------------------------------------
# D. Destination policy
# ---------------------------------------------------------------------------


class TestDestinationPolicy:
    def test_missing_destination_is_created_including_parents(self, tmp_path):
        destination = tmp_path / "nested" / "site"
        SiteBundleRepository().materialize(_full_bundle(), destination)
        assert (destination / "index.html").exists()

    def test_existing_empty_destination_accepted(self, tmp_path):
        destination = tmp_path / "site"
        destination.mkdir()
        SiteBundleRepository().materialize(_full_bundle(), destination)
        assert (destination / "index.html").exists()

    def test_existing_nonempty_destination_rejected_and_untouched(self, tmp_path):
        destination = tmp_path / "site"
        destination.mkdir()
        (destination / "preexisting.txt").write_text("do not touch")
        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(_full_bundle(), destination)
        assert excinfo.value.category == "destination_not_empty"
        assert (destination / "preexisting.txt").read_text() == "do not touch"
        assert not (destination / "index.html").exists()

    def test_destination_untouched_on_bundle_validation_error(self, tmp_path):
        bad_bundle = _single_file_bundle("../escape.html")
        destination = tmp_path / "site"
        with pytest.raises(SiteBundleRepositoryError):
            SiteBundleRepository().materialize(bad_bundle, destination)
        assert not destination.exists()

    def test_stale_staging_directory_is_removed_before_use(self, tmp_path):
        destination = tmp_path / "site"
        staging = _staging_path_for(destination)
        staging.mkdir(parents=True)
        (staging / "leftover.txt").write_text("stale junk from a crashed run")

        result = SiteBundleRepository().materialize(_full_bundle(), destination)

        assert not (destination / "leftover.txt").exists()
        assert set(result.written_paths) == set(_full_bundle().file_map)
        assert not staging.exists()

    def test_staging_path_exists_as_file_raises_staging_failure(self, tmp_path):
        destination = tmp_path / "site"
        staging = _staging_path_for(destination)
        staging.parent.mkdir(parents=True, exist_ok=True)
        staging.write_text("not a directory")

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(_full_bundle(), destination)
        assert excinfo.value.category == "staging_failure"

    def test_write_failure_cleans_staging_and_leaves_destination_untouched(self, tmp_path, monkeypatch):
        bundle = _full_bundle()
        destination = tmp_path / "site"
        original_write_bytes = Path.write_bytes

        def _flaky_write_bytes(self, data):
            if self.name == "index.html" and "hotels" not in self.parts:
                raise OSError("simulated disk failure")
            return original_write_bytes(self, data)

        monkeypatch.setattr(Path, "write_bytes", _flaky_write_bytes)

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bundle, destination)
        assert excinfo.value.category == "write_failure"
        assert not destination.exists()
        assert not _staging_path_for(destination).exists()

    def test_cleanup_failure_surfaces_as_typed_error(self, tmp_path, monkeypatch):
        bundle = _full_bundle()
        destination = tmp_path / "site"

        def _always_fail_write(self, data):
            raise OSError("disk full")

        def _always_fail_rmtree(path, *args, **kwargs):
            raise OSError("cleanup blocked")

        monkeypatch.setattr(Path, "write_bytes", _always_fail_write)
        monkeypatch.setattr(shutil, "rmtree", _always_fail_rmtree)

        with pytest.raises(SiteBundleRepositoryError) as excinfo:
            SiteBundleRepository().materialize(bundle, destination)
        assert excinfo.value.category == "cleanup_failure"
        assert isinstance(excinfo.value.__context__, OSError)


# ---------------------------------------------------------------------------
# E. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_bundle_produces_byte_identical_output(self, tmp_path):
        bundle = _full_bundle()
        dest_a = tmp_path / "a"
        dest_b = tmp_path / "b"
        SiteBundleRepository().materialize(bundle, dest_a)
        SiteBundleRepository().materialize(bundle, dest_b)
        for path in bundle.file_map:
            assert (dest_a / path).read_bytes() == (dest_b / path).read_bytes()

    def test_fresh_instances_agree(self, tmp_path):
        bundle = _full_bundle()
        result_a = SiteBundleRepository().materialize(bundle, tmp_path / "a")
        result_b = SiteBundleRepository().materialize(bundle, tmp_path / "b")
        assert result_a.written_paths == result_b.written_paths
        assert result_a.bundle_hash == result_b.bundle_hash

    def test_reordered_files_tuple_yields_identical_output(self, tmp_path):
        bundle = _full_bundle()
        reordered = bundle.copy(update={"files": tuple(reversed(bundle.files))})
        dest_a = tmp_path / "a"
        dest_b = tmp_path / "b"
        SiteBundleRepository().materialize(bundle, dest_a)
        SiteBundleRepository().materialize(reordered, dest_b)
        for path in bundle.file_map:
            assert (dest_a / path).read_bytes() == (dest_b / path).read_bytes()

    def test_manifest_deterministic_across_destinations(self, tmp_path):
        bundle = _full_bundle()
        dest_a = tmp_path / "a"
        dest_b = tmp_path / "b"
        SiteBundleRepository().materialize(bundle, dest_a, build_id="fixed-id")
        SiteBundleRepository().materialize(bundle, dest_b, build_id="fixed-id")
        assert (dest_a / MANIFEST_FILENAME).read_bytes() == (dest_b / MANIFEST_FILENAME).read_bytes()

    def test_bundle_not_mutated(self, tmp_path):
        bundle = _full_bundle()
        before = bundle.copy()
        SiteBundleRepository().materialize(bundle, tmp_path / "site")
        assert bundle == before


# ---------------------------------------------------------------------------
# F. Architecture
# ---------------------------------------------------------------------------


class TestArchitecture:
    def test_error_is_a_website_generation_error(self):
        assert issubclass(SiteBundleRepositoryError, WebsiteGenerationError)

    def test_module_has_no_forbidden_imports(self):
        source = Path(sbr_module.__file__).read_text(encoding="utf-8")
        forbidden_tokens = (
            "import socket",
            "import urllib",
            "import requests",
            "import uuid",
            "import random",
            "import tempfile",
            "import datetime",
            "os.environ",
            "from engines.website_generation.rendering",
            "from engines.website_generation.assembly",
            "from engines.website_generation.gates",
            "from engines.website_generation.pipeline",
            "from engines.website_generation.components",
            "from repositories.artifact_store_repository",
            "from repositories.build_state_repository",
            "from services",
        )
        for token in forbidden_tokens:
            assert token not in source, token

    def test_pipeline_remains_unwired(self):
        from engines.website_generation.constants.build import (
            PHASE1_EXECUTED_STAGES,
            STAGE_GATING,
            STAGE_SPEC_COMPILATION,
        )

        assert STAGE_GATING not in PHASE1_EXECUTED_STAGES
        assert PHASE1_EXECUTED_STAGES == (STAGE_SPEC_COMPILATION,)

    def test_sitebundle_schema_current(self):
        # AES-WEB-002M.1: SiteBundle current schema is 1.2.0 (additive
        # assets); this repository now also materializes binary asset
        # entries (see test_media_materialization.py).
        import engines.website_generation as wge

        assert wge.SCHEMA_VERSIONS[ArtifactKind.SITE_BUNDLE] == "1.2.0"

    def test_result_model_and_repository_not_exported_from_public_surface(self):
        import engines.website_generation as wge

        assert "SiteBundleMaterialization" not in wge.__all__
        assert "SiteBundleRepository" not in wge.__all__


# ---------------------------------------------------------------------------
# G. Browser-openable readiness (real Renderer + Assembly output)
# ---------------------------------------------------------------------------


class TestBrowserReadiness:
    def test_root_page_references_styles_css_relatively(self, tmp_path):
        bundle, _seo, _content, _site = real_bundle(("/", "/hotels"))
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        root_html = (destination / "index.html").read_text(encoding="utf-8")
        assert 'href="styles.css"' in root_html

    def test_nested_page_retains_assembly_generated_relative_link(self, tmp_path):
        bundle, _seo, _content, _site = real_bundle(("/", "/hotels"))
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        nested_html = (destination / "hotels" / "index.html").read_text(encoding="utf-8")
        assert 'href="../styles.css"' in nested_html

    def test_no_local_absolute_paths_leak_into_output(self, tmp_path):
        bundle, _seo, _content, _site = real_bundle(("/", "/hotels"))
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        for path in bundle.file_map:
            text = (destination / path).read_text(encoding="utf-8")
            assert str(tmp_path) not in text
            assert str(destination) not in text

    def test_expected_site_files_all_exist(self, tmp_path):
        bundle, _seo, _content, _site = real_bundle(("/", "/hotels"))
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination)
        for path in bundle.file_map:
            assert (destination / path).exists(), path
        assert (destination / MANIFEST_FILENAME).exists()

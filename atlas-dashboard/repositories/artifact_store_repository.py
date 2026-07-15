"""Content-addressable artifact store for the WGE (AES-WEB-001 §9.1).

Persistence only: canonical serialization, SHA-256 content addressing,
put/get/exists, the three validation rings applied at persistence time
(§4.4), deterministic file layout, and atomic writes. No business
orchestration, no AI, no engine invocation.

AES-WEB-002M.1 adds the §9.1-specified raw-bytes object class ("objects ...
canonical JSON **or raw bytes**"): ``put_bytes``/``get_bytes``/
``exists_bytes`` for binary assets (images, fonts) per §4.3 ("Binary assets
... are stored as raw bytes in the CAS and referenced from artifacts by
hash; artifacts themselves never embed binary data"). Raw-bytes objects are
identity-only: no schema, no artifact kind, no kind-index marker, no
provenance ring -- their whole contract is ``sha256(bytes)``. A distinct
``.bin`` suffix keeps the two object classes structurally separate (an
artifact hash and a bytes hash can never resolve to each other's payload).

File layout (deterministic, derived from content hashes)::

    <base_dir>/
        objects/<first2>/<sha256>.json    # canonical artifact JSON
        objects/<first2>/<sha256>.bin     # raw binary asset bytes (M.1)
        kinds/<artifact_kind>/<sha256>    # empty marker files (kind index)

Source-hash verification policy (Phase 1 decision, recorded per the
Sprint 1 directive): every entry in an artifact's ``source_hashes`` must
already exist in the store — no orphan provenance (§4.4 ring 3) — with
one documented exemption: keys prefixed ``external:`` denote provenance
of upstream Atlas records that live outside the CAS (e.g. the
BusinessSpec's upstream inputs, which the future service layer will
snapshot). Their hashes are recorded verbatim but not resolved here.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Union

from engines.website_generation.contracts.artifacts import (
    ArtifactHeader,
    artifact_sha256,
    canonical_artifact_json,
    model_from_dict,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactValidationError,
    RepositoryCorruptionError,
)
from engines.website_generation.contracts.versions import (
    registered_artifact_model,
)

EXTERNAL_SOURCE_PREFIX = "external:"


class ArtifactStoreRepository:
    """Content-addressable store keyed by sha256(canonical JSON)."""

    def __init__(self, base_dir: Union[str, Path]) -> None:
        self._base_dir = Path(base_dir)
        self._objects_dir = self._base_dir / "objects"
        self._kinds_dir = self._base_dir / "kinds"
        self._objects_dir.mkdir(parents=True, exist_ok=True)
        self._kinds_dir.mkdir(parents=True, exist_ok=True)

    # -- paths --------------------------------------------------------

    def _object_path(self, artifact_hash: str) -> Path:
        return self._objects_dir / artifact_hash[:2] / (
            artifact_hash + ".json"
        )

    def _bytes_path(self, content_hash: str) -> Path:
        return self._objects_dir / content_hash[:2] / (
            content_hash + ".bin"
        )

    def _kind_marker_path(self, kind: ArtifactKind, artifact_hash: str) -> Path:
        return self._kinds_dir / ArtifactKind(kind).value / artifact_hash

    # -- public API (persistence only) ---------------------------------

    def put(self, artifact: ArtifactHeader) -> str:
        """Validate (rings 1-3) and persist an artifact; return its hash.

        Idempotent: putting an artifact whose hash already exists is a
        no-op returning the existing hash.
        """
        if not isinstance(artifact, ArtifactHeader):
            raise ArtifactValidationError(
                "artifacts must derive from ArtifactHeader",
                stage="artifact_store",
            )

        # Ring 1 — schema: a registered model must exist for the declared
        # (kind, schema_version), and the instance must be of that model.
        model_cls = registered_artifact_model(
            artifact.artifact_kind, artifact.schema_version
        )
        if not isinstance(artifact, model_cls):
            raise ArtifactValidationError(
                "artifact instance is not the registered model for %s %s"
                % (
                    ArtifactKind(artifact.artifact_kind).value,
                    artifact.schema_version,
                ),
                stage="artifact_store",
                diagnostics={
                    "expected_model": model_cls.__name__,
                    "actual_model": type(artifact).__name__,
                },
            )

        # Ring 3 (provenance half) — every non-external source hash must
        # already exist in the store: no orphan provenance.
        missing: List[str] = []
        for key in sorted(artifact.source_hashes):
            if key.startswith(EXTERNAL_SOURCE_PREFIX):
                continue
            if not self.exists(artifact.source_hashes[key]):
                missing.append(key)
        if missing:
            raise ArtifactValidationError(
                "source hashes not present in store: %s" % ", ".join(missing),
                stage="artifact_store",
                diagnostics={"missing_source_keys": missing},
            )

        canonical = canonical_artifact_json(artifact)
        artifact_hash = artifact_sha256(artifact)

        object_path = self._object_path(artifact_hash)
        if object_path.exists():
            # Content-addressed idempotence: identical content, no-op.
            return artifact_hash

        object_path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(object_path, canonical)

        marker = self._kind_marker_path(artifact.artifact_kind, artifact_hash)
        marker.parent.mkdir(parents=True, exist_ok=True)
        if not marker.exists():
            self._atomic_write_text(marker, "")

        return artifact_hash

    def get(
        self, artifact_hash: str, expected_kind: ArtifactKind
    ) -> ArtifactHeader:
        """Load an artifact, verifying identity and declared kind."""
        object_path = self._object_path(artifact_hash)
        if not object_path.exists():
            raise ArtifactNotFoundError(
                "artifact %s not found" % artifact_hash,
                stage="artifact_store",
                diagnostics={"artifact_hash": artifact_hash},
            )

        raw = object_path.read_text(encoding="utf-8")

        # Ring 3 (identity half) — recomputed hash must match the key
        # under which the object is stored (tamper detection).
        recomputed = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if recomputed != artifact_hash:
            raise ArtifactIntegrityError(
                "stored artifact content does not match its hash",
                stage="artifact_store",
                diagnostics={
                    "artifact_hash": artifact_hash,
                    "recomputed_hash": recomputed,
                },
            )

        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise RepositoryCorruptionError(
                "stored artifact is not valid JSON: %s" % exc,
                stage="artifact_store",
                diagnostics={"artifact_hash": artifact_hash},
            )

        declared_kind = payload.get("artifact_kind")
        declared_version = payload.get("schema_version")
        if declared_kind != ArtifactKind(expected_kind).value:
            raise ArtifactValidationError(
                "artifact kind mismatch: expected %s, stored %s"
                % (ArtifactKind(expected_kind).value, declared_kind),
                stage="artifact_store",
                diagnostics={"artifact_hash": artifact_hash},
            )

        model_cls = registered_artifact_model(
            ArtifactKind(declared_kind), str(declared_version)
        )
        return model_from_dict(model_cls, payload)

    def exists(self, artifact_hash: str) -> bool:
        """True iff the hash resolves to a stored object."""
        return self._object_path(str(artifact_hash)).exists()

    # -- raw-bytes object class (AES-WEB-002M.1; §9.1/§4.3) --------------

    def put_bytes(self, data: bytes) -> str:
        """Persist raw binary bytes content-addressed; return their hash.

        Idempotent, like :meth:`put`: putting bytes whose hash already
        exists is a no-op returning the existing hash. Only real ``bytes``
        are accepted -- text belongs in artifacts, never in the binary
        object class (fail-closed against accidental str writes that would
        silently pick up an encoding).
        """
        if not isinstance(data, bytes):
            raise ArtifactValidationError(
                "raw-bytes objects must be bytes, got %s" % type(data).__name__,
                stage="artifact_store",
            )
        content_hash = hashlib.sha256(data).hexdigest()
        bytes_path = self._bytes_path(content_hash)
        if bytes_path.exists():
            return content_hash
        bytes_path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_bytes(bytes_path, data)
        return content_hash

    def get_bytes(self, content_hash: str) -> bytes:
        """Load raw bytes, verifying content identity (tamper detection --
        the same ring-3 identity check :meth:`get` applies to artifacts)."""
        bytes_path = self._bytes_path(str(content_hash))
        if not bytes_path.exists():
            raise ArtifactNotFoundError(
                "bytes object %s not found" % content_hash,
                stage="artifact_store",
                diagnostics={"content_hash": str(content_hash)},
            )
        data = bytes_path.read_bytes()
        recomputed = hashlib.sha256(data).hexdigest()
        if recomputed != content_hash:
            raise ArtifactIntegrityError(
                "stored bytes object does not match its hash",
                stage="artifact_store",
                diagnostics={
                    "content_hash": str(content_hash),
                    "recomputed_hash": recomputed,
                },
            )
        return data

    def exists_bytes(self, content_hash: str) -> bool:
        """True iff the hash resolves to a stored raw-bytes object."""
        return self._bytes_path(str(content_hash)).exists()

    def list_by_kind(self, kind: ArtifactKind) -> List[str]:
        """Stable-sorted hashes of stored artifacts of one kind."""
        kind_dir = self._kinds_dir / ArtifactKind(kind).value
        if not kind_dir.exists():
            return []
        return sorted(p.name for p in kind_dir.iterdir() if p.is_file())

    # -- internals -----------------------------------------------------

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        """Write via a same-directory temp file + os.replace (atomic)."""
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".tmp-", suffix=".part"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
            os.replace(tmp_name, str(path))
        except Exception:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

    @staticmethod
    def _atomic_write_bytes(path: Path, data: bytes) -> None:
        """Binary twin of :meth:`_atomic_write_text` -- same same-directory
        temp file + ``os.replace`` discipline, no encoding involved."""
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".tmp-", suffix=".part"
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp_name, str(path))
        except Exception:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

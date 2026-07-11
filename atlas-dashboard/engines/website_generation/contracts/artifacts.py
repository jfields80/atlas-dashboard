"""Artifact contract catalog for the Website Generation Engine.

AES-WEB-001 Phase 1 (v1.0.0): the twelve artifact kinds (§4.1), each a
frozen Pydantic model carrying the three mandatory header fields
(``schema_version``, ``artifact_kind``, ``source_hashes``), plus the
shared canonical-serialization and SHA-256 identity helpers (§4.3).

Pydantic compatibility
----------------------
Per the Atlas ``pydantic_compat`` doctrine (engines/directory_blueprint/
pydantic_compat.py), no module in this subsystem touches a
version-specific Pydantic API outside a single isolation point. Because
the AES-WEB-001 import matrix (§3.1) forbids this package from importing
other engine packages, that isolation point is embedded here (the
AES-005A ``website_intelligence.models`` precedent) rather than imported
across an engine boundary:

* models derive from :class:`FrozenModel`, frozen under v1 and v2;
* serialization goes through :func:`model_to_dict` /
  :func:`model_from_dict`, never ``.dict()`` / ``.model_dump()`` directly;
* no ``@validator`` / ``@field_validator`` — validation beyond type
  coercion lives in the compiler, registry, and repositories.

Phase 1 payload depth
---------------------
Later-phase payload depth is intentionally deferred and represented with
typed minimal structures — never untyped dict dumping. ComponentManifest
remains schema 1.0.0 with no ``selection_trace`` (AES-WEB-002A deferred).
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Type, TypeVar

import pydantic
from pydantic import BaseModel, Field

from engines.website_generation.contracts.enums import (
    ArtifactKind,
    BuildState,
    GateSeverity,
    StageExecutionStatus,
)

PYDANTIC_V2: bool = str(getattr(pydantic, "VERSION", "1.0")).startswith("2")

_M = TypeVar("_M", bound=BaseModel)


# ---------------------------------------------------------------------------
# Pydantic v1/v2 isolation (pydantic_compat doctrine, embedded per §3.1)
# ---------------------------------------------------------------------------

if PYDANTIC_V2:
    from pydantic import ConfigDict

    class FrozenModel(BaseModel):
        """Immutable base model (Pydantic v2)."""

        model_config = ConfigDict(frozen=True, extra="forbid")

else:

    class FrozenModel(BaseModel):
        """Immutable base model (Pydantic v1)."""

        class Config:
            frozen = True
            allow_mutation = False
            extra = "forbid"


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """Serialize a model to a plain dict under either Pydantic major."""
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()


def model_from_dict(model_cls: Type[_M], data: Dict[str, Any]) -> _M:
    """Construct and validate a model from a dict under either major."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(data)  # type: ignore[attr-defined]
    return model_cls.parse_obj(data)


# ---------------------------------------------------------------------------
# Canonical serialization and content identity (AES-WEB-001 §4.3)
# ---------------------------------------------------------------------------

def _canonicalize(value: Any) -> Any:
    """Reduce a value to canonical JSON-serializable primitives.

    Deterministic null handling: ``None`` is preserved and emitted as
    JSON ``null`` — fields are never silently dropped. Enums collapse to
    their string values. Tuples emit as JSON arrays. Mapping keys must be
    strings so sorted-key output is total and stable.
    """
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        # Phase 1 contracts declare no float fields; floats are rejected
        # rather than risking representation drift across platforms.
        raise ArtifactCanonicalizationError(
            "float values are not permitted in Phase 1 canonical artifacts"
        )
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, BaseModel):
        return _canonicalize(model_to_dict(value))
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key in value:
            if not isinstance(key, str):
                raise ArtifactCanonicalizationError(
                    "canonical mappings require string keys, got %r"
                    % type(key).__name__
                )
            out[key] = _canonicalize(value[key])
        return out
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ArtifactCanonicalizationError(
        "unsupported canonical value type: %r" % type(value).__name__
    )


class ArtifactCanonicalizationError(ValueError):
    """A value cannot be represented in canonical artifact JSON."""


def canonical_json(payload: Any) -> str:
    """Canonical JSON: UTF-8, sorted keys, no insignificant whitespace."""
    return json.dumps(
        _canonicalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_artifact_json(artifact: BaseModel) -> str:
    """Canonical JSON text of a frozen artifact model."""
    return canonical_json(model_to_dict(artifact))


def sha256_of_text(text: str) -> str:
    """SHA-256 hex digest of UTF-8 encoded text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def artifact_sha256(artifact: BaseModel) -> str:
    """Content identity of an artifact: sha256(canonical_json) (§4.3)."""
    return sha256_of_text(canonical_artifact_json(artifact))


# ---------------------------------------------------------------------------
# Mandatory artifact header (AES-WEB-001 §4.1)
# ---------------------------------------------------------------------------

class ArtifactHeader(FrozenModel):
    """The three mandatory header fields carried by every artifact."""

    schema_version: str = Field(...)
    artifact_kind: ArtifactKind = Field(...)
    source_hashes: Dict[str, str] = Field(...)


# ---------------------------------------------------------------------------
# 1. BusinessSpec
# ---------------------------------------------------------------------------

class BusinessSpec(ArtifactHeader):
    """Canonical business identity (§4.1 artifact #1)."""

    artifact_kind: ArtifactKind = ArtifactKind.BUSINESS_SPEC
    business_name: str
    niche: str
    audience: str
    value_proposition: str
    directory_taxonomy: Tuple[str, ...] = ()
    monetization_model: str = ""
    geography: str = ""
    legal_footer_facts: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# 2. BrandPackage
# ---------------------------------------------------------------------------

class BrandPackage(ArtifactHeader):
    """Design tokens and voice profile (§4.1 artifact #2).

    Phase 1 minimal typed payload; full token taxonomy arrives in Phase 2.
    """

    artifact_kind: ArtifactKind = ArtifactKind.BRAND_PACKAGE
    palette: Dict[str, str] = {}
    type_scale: Dict[str, str] = {}
    spacing_scale: Dict[str, str] = {}
    voice_profile: str = ""
    asset_hashes: Dict[str, str] = {}


# ---------------------------------------------------------------------------
# 3. SiteArchitecture
# ---------------------------------------------------------------------------

class PagePlan(FrozenModel):
    """A planned page: route, type, and typed content slots."""

    route: str
    page_type: str
    title: str = ""
    content_slots: Tuple[str, ...] = ()


class SiteArchitecture(ArtifactHeader):
    """Page inventory, routes, and nav topology (§4.1 artifact #3)."""

    artifact_kind: ArtifactKind = ArtifactKind.SITE_ARCHITECTURE
    pages: Tuple[PagePlan, ...] = ()
    nav_routes: Tuple[str, ...] = ()
    sitemap_routes: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# 4. ContentCandidate
# ---------------------------------------------------------------------------

class ContentCandidate(ArtifactHeader):
    """Raw drafted copy keyed to an IA slot (§4.1 artifact #4).

    Never consumed downstream directly — validation-only input to the
    Content Engine.
    """

    artifact_kind: ArtifactKind = ArtifactKind.CONTENT_CANDIDATE
    page_route: str
    slot_id: str
    body: str
    origin: str = "human"


# ---------------------------------------------------------------------------
# 5. ContentPackage
# ---------------------------------------------------------------------------

class ContentBlock(FrozenModel):
    """A validated, normalized, escaped content block bound to a slot."""

    page_route: str
    slot_id: str
    text: str


class ContentPackage(ArtifactHeader):
    """Validated content blocks — the only content downstream sees (#5)."""

    artifact_kind: ArtifactKind = ArtifactKind.CONTENT_PACKAGE
    blocks: Tuple[ContentBlock, ...] = ()


# ---------------------------------------------------------------------------
# 6. ComponentManifest — schema 1.0.0, no selection_trace (AES-WEB-002A
# deferred; do not amend in Phase 1)
# ---------------------------------------------------------------------------

class ComponentInstance(FrozenModel):
    """A component instance with bound content refs and props."""

    component_id: str
    component_version: str = "1.0.0"
    props: Dict[str, str] = {}
    content_refs: Tuple[str, ...] = ()


class PageComponents(FrozenModel):
    """Component instances resolved for one page."""

    route: str
    components: Tuple[ComponentInstance, ...] = ()


class ComponentManifest(ArtifactHeader):
    """Per-page component instances (§4.1 artifact #6). Schema 1.0.0."""

    artifact_kind: ArtifactKind = ArtifactKind.COMPONENT_MANIFEST
    pages: Tuple[PageComponents, ...] = ()


# ---------------------------------------------------------------------------
# 7. LayoutPlan
# ---------------------------------------------------------------------------

class LayoutRegion(FrozenModel):
    """An ordered region holding component indexes from the manifest."""

    region_id: str
    component_indexes: Tuple[int, ...] = ()


class PageLayout(FrozenModel):
    """Deterministic composition tree for one page."""

    route: str
    regions: Tuple[LayoutRegion, ...] = ()


class LayoutPlan(ArtifactHeader):
    """Deterministic page composition (§4.1 artifact #7)."""

    artifact_kind: ArtifactKind = ArtifactKind.LAYOUT_PLAN
    pages: Tuple[PageLayout, ...] = ()


# ---------------------------------------------------------------------------
# 8. RenderedPageSet
# ---------------------------------------------------------------------------

class RenderedPage(FrozenModel):
    """One emitted page referenced by content hash (no embedded binary)."""

    route: str
    html_hash: str
    css_hash: str = ""


class RenderedPageSet(ArtifactHeader):
    """Emitted HTML/CSS per page, content-hashed (§4.1 artifact #8)."""

    artifact_kind: ArtifactKind = ArtifactKind.RENDERED_PAGE_SET
    pages: Tuple[RenderedPage, ...] = ()
    shared_css_hash: str = ""


# ---------------------------------------------------------------------------
# 9. SEOPackage
# ---------------------------------------------------------------------------

class SEOEntry(FrozenModel):
    """SEO metadata for one route."""

    route: str
    title: str = ""
    meta_description: str = ""
    canonical_url: str = ""


class SEOPackage(ArtifactHeader):
    """Titles, metadata, canonical URLs, sitemap plan (§4.1 artifact #9)."""

    artifact_kind: ArtifactKind = ArtifactKind.SEO_PACKAGE
    entries: Tuple[SEOEntry, ...] = ()
    sitemap_routes: Tuple[str, ...] = ()
    robots_directives: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# 10. SiteBundle
# ---------------------------------------------------------------------------

class SiteBundle(ArtifactHeader):
    """Complete static site file map: path → content hash (#10)."""

    artifact_kind: ArtifactKind = ArtifactKind.SITE_BUNDLE
    file_map: Dict[str, str] = {}
    bundle_hash: str = ""


# ---------------------------------------------------------------------------
# 11. QualityReport / LaunchCertificate
# ---------------------------------------------------------------------------

class GateResult(FrozenModel):
    """One gate's typed result — gates return results, never raise (§5.10)."""

    gate_id: str
    severity: GateSeverity
    passed: bool
    details: str = ""


class LaunchCertificateBody(FrozenModel):
    """Certificate issued only on full blocking-gate pass (§10.3)."""

    bundle_hash: str
    build_id: str
    gate_results_digest: str
    engine_versions: Dict[str, str] = {}
    overrides: Tuple[str, ...] = ()


class QualityReport(ArtifactHeader):
    """Gate results and optional certificate (§4.1 artifact #11)."""

    artifact_kind: ArtifactKind = ArtifactKind.QUALITY_REPORT
    gate_results: Tuple[GateResult, ...] = ()
    certified: bool = False
    certificate: Optional[LaunchCertificateBody] = None


# ---------------------------------------------------------------------------
# 12. BuildManifest
# ---------------------------------------------------------------------------

class StageRecord(FrozenModel):
    """One pipeline stage's manifest record.

    Phase 1 records unimplemented future stages with status
    ``NOT_EXECUTED`` and ``artifact_hash`` of ``None`` — a stage is never
    reported successful unless it actually ran.
    """

    stage_name: str
    status: StageExecutionStatus
    artifact_kind: Optional[ArtifactKind] = None
    artifact_hash: Optional[str] = None
    engine_version: Optional[str] = None


class TransitionRecord(FrozenModel):
    """One recorded state transition (§6.9 audit projection)."""

    from_state: BuildState
    to_state: BuildState
    outcome: str


class BuildManifest(ArtifactHeader):
    """Ordered audit record of the build (§4.1 artifact #12)."""

    artifact_kind: ArtifactKind = ArtifactKind.BUILD_MANIFEST
    build_id: str
    pipeline_version: str
    engine_versions: Dict[str, str] = {}
    final_state: BuildState
    stage_records: Tuple[StageRecord, ...] = ()
    transitions: Tuple[TransitionRecord, ...] = ()
    generated_at: str = ""


# ---------------------------------------------------------------------------
# Compiler-input contract boundary (Phase 1 decision, documented)
# ---------------------------------------------------------------------------

class SpecCompilerInput(FrozenModel):
    """Minimal typed input contract for the BusinessSpecCompiler.

    Design decision (recorded per Sprint 1 directive): the upstream Atlas
    models (Directory Builder / Project Assembly / Launch Kit) do not yet
    expose a stable frozen interface for WGE ingestion, and importing raw
    persistence models would couple the compiler to unrelated schemas.
    This contract is therefore the narrowly typed Phase 1 boundary; the
    (future) service layer loads upstream records and maps them into this
    shape. ``upstream_hashes`` carries the SHA-256 provenance of those
    upstream records under ``external:``-prefixed keys (see
    artifact_store_repository source-hash verification policy).
    """

    business_name: str = ""
    niche: str = ""
    audience: str = ""
    value_proposition: str = ""
    directory_taxonomy: Tuple[str, ...] = ()
    monetization_model: str = ""
    geography: str = ""
    legal_footer_facts: Tuple[str, ...] = ()
    upstream_hashes: Dict[str, str] = {}

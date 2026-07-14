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
typed minimal structures — never untyped dict dumping.

ComponentManifest selection trace (AES-WEB-001 v1.1.0 amendment A1)
------------------------------------------------------------------
Per AES-WEB-002 §14.3 and ADR-14, ``ComponentManifest`` optionally carries
a schema-versioned ``selection_trace`` block recording, per slot, the
deterministic candidate filtering, scoring, and tie-breaking of the future
Component Engine (§14.2). The block is additive and optional, so the schema
moves from 1.0.0 to 1.1.0 as a minor bump with no migration (old readers
still parse). The 1.0.0 shape is retained byte-for-byte as
:class:`ComponentManifestV1` — because the canonical serializer emits
``None`` as JSON ``null`` rather than dropping it, a 1.0.0 manifest MUST NOT
declare the field at all, so its serialization and hash are unchanged. The
Layout Engine ignores the trace. No thirteenth artifact and no independent
``SelectionTrace`` artifact are created (both alternatives are rejected in
§14.3); the trace is an embedded, typed sub-structure only.

BrandPackage token/contrast expansion (AES-WEB-001 §5.2 / Part 2 / Part 13
Phase 2; internal sequencing label AES-WEB-002J.2)
--------------------------------------------------------------------------
``BrandPackage`` gains ``radius_scale``, ``extended_tokens`` (the non-color/
type/spacing/radius token domains), and ``contrast_evidence`` (pre-computed,
integer-only WCAG 2.x contrast records). The additive fields move the
schema from 1.0.0 to 1.1.0 with no migration (old readers still parse). The
1.0.0 shape is retained byte-for-byte as :class:`BrandPackageV1` for the
same reason documented above for ``ComponentManifestV1``: the canonical
serializer never drops a declared field, so a 1.0.0 payload must not
declare the Phase 2 fields at all.

SiteArchitecture hierarchy/topology expansion (AES-WEB-001 §5.3 / Part 2 /
Part 13 Phase 2; internal sequencing label AES-WEB-002J.3)
--------------------------------------------------------------------------
``SiteArchitecture`` gains ``page_ids`` (stable, content-derived page
identifiers keyed by route), ``page_hierarchy`` (parent/child relationships
declaring the exactly-one-root page tree), and ``internal_link_topology``
(deterministic internal-link intent between pages) -- the nav-tree/
hierarchy/link-topology depth §4.1 artifact #3 and AES-WEB-002 §6.2/§26
describe as consumed from "SiteArchitecture topology". The additive fields
move the schema from 1.0.0 to 1.1.0 with no migration (old readers still
parse); ``PagePlan`` is unchanged and shared byte-for-byte by both schema
versions. The 1.0.0 shape is retained byte-for-byte as
:class:`SiteArchitectureV1` for the same reason documented above for
``ComponentManifestV1``/``BrandPackageV1``: the canonical serializer never
drops a declared field, so a 1.0.0 payload must not declare the new fields
at all. The Information Architecture Engine (``engines/website_generation/
ia/``) is not wired into pipeline execution by this delivery.

LayoutPlan region/placement expansion (AES-WEB-001 §5.6 / Part 2 / Part 13
Phase 2; internal sequencing label AES-WEB-002J.7)
--------------------------------------------------------------------------
``LayoutPlan`` gains ``region_details`` (typed region identity per
``RegionKind`` plus deterministic per-component grid and responsive
placement, keyed back to the unchanged ``pages``/``regions`` structure by
``(route, region_id)``). The additive field moves the schema from 1.0.0 to
1.1.0 with no migration (old readers still parse). The 1.0.0 shape is
retained byte-for-byte as :class:`LayoutPlanV1` for the same reason
documented above for ``ComponentManifestV1``/``BrandPackageV1``/
``SiteArchitectureV1``: the canonical serializer never drops a declared
field, so a 1.0.0 payload must not declare the new field at all.
``LayoutRegion`` and ``PageLayout`` are unchanged and shared byte-for-byte
by both schema versions -- new capability is expressed only as new sibling
nested models (:class:`GridPlacement`, :class:`ResponsiveSelection`,
:class:`ComponentPlacement`, :class:`RegionLayoutDetail`), never by
restructuring an existing field's type (the established J.2/J.3 idiom). The
Layout Engine (``engines/website_generation/layouts/``) is not wired into
pipeline execution by this delivery.

RenderedPageSet HTML/shared-CSS text payload (AES-WEB-001 §5.7 / Part 2 /
Part 13 Phase 2; internal sequencing label AES-WEB-002J.8)
--------------------------------------------------------------------------
``RenderedPageSet`` gains ``page_details`` (per-page emitted HTML text,
keyed back to the unchanged ``pages`` by route) and ``shared_css`` (the
shared CSS text payload backing ``shared_css_hash``). The additive fields
move the schema from 1.0.0 to 1.1.0 with no migration (old readers still
parse). The 1.0.0 shape is retained byte-for-byte as
:class:`RenderedPageSetV1` for the same reason documented above for
``ComponentManifestV1``/``BrandPackageV1``/``SiteArchitectureV1``/
``LayoutPlanV1``: the canonical serializer never drops a declared field, so
a 1.0.0 payload must not declare the new fields at all. ``RenderedPage`` is
unchanged and shared byte-for-byte by both schema versions; new capability
is expressed only as a new sibling nested model (:class:`RenderedPageDetail`),
never by restructuring ``RenderedPage`` itself. The Renderer
(``engines/website_generation/rendering/``) is not wired into pipeline
execution by this delivery.

SiteBundle per-file text payload (AES-WEB-001 §5.9 / Part 2 / Part 13
Phase 2; internal sequencing label AES-WEB-002J.10)
--------------------------------------------------------------------------
``SiteBundle`` gains ``files`` (per-file UTF-8 text content, keyed back to
the unchanged ``file_map`` path → content-hash map by path). The additive
field moves the schema from 1.0.0 to 1.1.0 with no migration (old readers
still parse). The 1.0.0 shape is retained byte-for-byte as
:class:`SiteBundleV1` for the same reason documented above -- the Assembly
Engine is a pure "No file I/O" engine (§5.9), so the assembled static-site
text must travel inside the returned artifact for the (future)
site_bundle_repository (§9.3) to materialize to disk; new capability is a
new sibling nested model (:class:`BundleFile`), never a restructuring of
``file_map``/``bundle_hash``. The Assembly Engine
(``engines/website_generation/assembly/``) is not wired into pipeline
execution by this delivery.

QualityReport deferred-gate coverage (AES-WEB-001 §5.10 / Part 2 / Part 13
Phase 3; internal sequencing label AES-WEB-002J.11)
--------------------------------------------------------------------------
``QualityReport`` gains ``deferred_gate_ids`` (the registered gates the
Quality Gate Engine did not evaluate this run, because the deterministic
static facts they require are not derivable from the current artifacts).
The additive field moves the schema from 1.0.0 to 1.1.0 with no migration
(old readers still parse). The 1.0.0 shape is retained byte-for-byte as
:class:`QualityReportV1` for the same reason documented above -- the
canonical serializer never drops a declared field, so a 1.0.0 payload must
not declare the new field at all. ``GateResult``/``LaunchCertificateBody``
are unchanged and shared byte-for-byte by both schema versions; the report
is thereby self-describing about its own gate coverage (the AES-005A
quality-gate honesty lesson, §5.10). The Quality Gate Engine
(``engines/website_generation/gates/quality_gate_engine.py``) is not wired
into pipeline execution by this delivery.
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
    AssetRole,
    BuildState,
    GateSeverity,
    ListingKind,
    RegionKind,
    StageExecutionStatus,
    VerificationStatus,
    Weekday,
)
from engines.website_generation.contracts.render_data import RenderDataBundle

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
# 2. BrandPackage — schema 1.1.0 with radius/extended tokens and contrast
# evidence (AES-WEB-001 §5.2 / Part 2 / Part 13 Phase 2 amendment; internal
# sequencing label AES-WEB-002J.2)
# ---------------------------------------------------------------------------

class ContrastEvidence(FrozenModel):
    """One WCAG 2.x contrast-ratio record embedded in a BrandPackage (§5.2).

    Stores only pre-computed integer evidence — never a float — so the
    (future) accessibility gate can verify without recomputing (§5.2, §10.3).
    ``contrast_ratio_hundredths`` is ``floor(ratio * 100)`` (e.g. ``450``
    means 4.50:1); ``required_hundredths`` is the sanctioned threshold for
    this pair (450 for text pairs, 300 for focus/border/UI pairs).
    """

    foreground_token: str
    background_token: str
    contrast_ratio_hundredths: int
    required_hundredths: int
    passed: bool


class BrandPackageV1(ArtifactHeader):
    """BrandPackage schema 1.0.0 (pre-Phase-2 shape).

    Retained for replay of packages produced before AES-WEB-002J.2. Carries
    none of the Phase 2 fields (``radius_scale``, ``extended_tokens``,
    ``contrast_evidence``), so its canonical serialization and content hash
    are byte-identical to the original 1.0.0 contract. The current schema is
    1.1.0 (:class:`BrandPackage`). Internal compatibility model — not part
    of the public surface.
    """

    artifact_kind: ArtifactKind = ArtifactKind.BRAND_PACKAGE
    palette: Dict[str, str] = {}
    type_scale: Dict[str, str] = {}
    spacing_scale: Dict[str, str] = {}
    voice_profile: str = ""
    asset_hashes: Dict[str, str] = {}


class BrandPackage(ArtifactHeader):
    """Design tokens, voice profile, and contrast evidence (§4.1 artifact #2).

    Schema 1.1.0 (AES-WEB-001 §5.2 / Part 2 / Part 13 Phase 2): additive over
    the 1.0.0 shape (:class:`BrandPackageV1`) with ``radius_scale``,
    ``extended_tokens``, and ``contrast_evidence``. No migration required —
    the fields are additive and old 1.0.0 payloads still load via
    BrandPackageV1.
    """

    artifact_kind: ArtifactKind = ArtifactKind.BRAND_PACKAGE
    palette: Dict[str, str] = {}
    type_scale: Dict[str, str] = {}
    spacing_scale: Dict[str, str] = {}
    voice_profile: str = ""
    asset_hashes: Dict[str, str] = {}
    radius_scale: Dict[str, str] = {}
    extended_tokens: Dict[str, str] = {}
    contrast_evidence: Tuple[ContrastEvidence, ...] = ()


# ---------------------------------------------------------------------------
# 3. SiteArchitecture — schema 1.1.0 with page ids, hierarchy, and internal-
# link topology (AES-WEB-001 §5.3 / Part 2 / Part 13 Phase 2 amendment;
# internal sequencing label AES-WEB-002J.3)
# ---------------------------------------------------------------------------

class PagePlan(FrozenModel):
    """A planned page: route, type, and typed content slots."""

    route: str
    page_type: str
    title: str = ""
    content_slots: Tuple[str, ...] = ()


class SiteArchitectureV1(ArtifactHeader):
    """SiteArchitecture schema 1.0.0 (pre-J.3 shape).

    Retained for replay of packages produced before AES-WEB-002J.3. Carries
    none of the Phase 2 fields (``page_ids``, ``page_hierarchy``,
    ``internal_link_topology``), so its canonical serialization and content
    hash are byte-identical to the original 1.0.0 contract. The current
    schema is 1.1.0 (:class:`SiteArchitecture`). Internal compatibility
    model -- not part of the public surface.
    """

    artifact_kind: ArtifactKind = ArtifactKind.SITE_ARCHITECTURE
    pages: Tuple[PagePlan, ...] = ()
    nav_routes: Tuple[str, ...] = ()
    sitemap_routes: Tuple[str, ...] = ()


class PageHierarchyEntry(FrozenModel):
    """One page's position in the site tree (AES-WEB-001 §5.3).

    ``parent_route`` is ``""`` for exactly one page: the root (home) page.
    Every other page's ``parent_route`` must name another page's ``route``.
    """

    route: str
    parent_route: str = ""


class InternalLinkIntent(FrozenModel):
    """Deterministic internal-link intent from one page to others (§4.1
    artifact #3; AES-WEB-002 §6.2/§26 "from SiteArchitecture topology").

    Structural intent only -- no anchor text, no rendering, no component
    selection. Every route named here (``from_route`` and every entry of
    ``to_routes``) must exist among the artifact's ``pages``.
    """

    from_route: str
    to_routes: Tuple[str, ...] = ()


class SiteArchitecture(ArtifactHeader):
    """Page inventory, routes, hierarchy, and internal-link topology (§4.1
    artifact #3). Schema 1.1.0.

    AES-WEB-002J.3 (AES-WEB-001 §5.3 / Part 2 / Part 13 Phase 2): additive
    over the 1.0.0 shape (:class:`SiteArchitectureV1`) with ``page_ids``,
    ``page_hierarchy``, and ``internal_link_topology``. No migration
    required -- the fields are additive and old 1.0.0 payloads still load
    via SiteArchitectureV1.
    """

    artifact_kind: ArtifactKind = ArtifactKind.SITE_ARCHITECTURE
    pages: Tuple[PagePlan, ...] = ()
    nav_routes: Tuple[str, ...] = ()
    sitemap_routes: Tuple[str, ...] = ()
    page_ids: Dict[str, str] = {}
    page_hierarchy: Tuple[PageHierarchyEntry, ...] = ()
    internal_link_topology: Tuple[InternalLinkIntent, ...] = ()


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
# 6. ComponentManifest — schema 1.1.0 with optional selection_trace
# (AES-WEB-001 v1.1.0 amendment A1; AES-WEB-002 §14.3, ADR-14)
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


# --- Selection trace (embedded, typed; AES-WEB-002 §14.2/§14.3, ADR-14) ----

# The selection_trace block is itself schema-versioned (§14.3). This is the
# version of the trace sub-structure, independent of the ComponentManifest
# artifact schema version.
SELECTION_TRACE_SCHEMA_VERSION: str = "1.0.0"


class SelectionScoreComponent(FrozenModel):
    """One additive integer scoring factor for a candidate (§14.2 step 6).

    Scores are additive integers from static tables (PREFERRED +100, exact
    intent match +50, monetization-config alignment +30, brand-profile
    affinity +20, optional-asset availability +10). Integer arithmetic only
    — no floats, per the canonical-serialization rules.
    """

    factor: str
    points: int


class SelectionCandidate(FrozenModel):
    """One candidate considered for a slot (top-5 named candidates; §14.3).

    ``eliminated_by`` records the filter ID that removed the candidate
    (§14.2 steps 1–5: candidate-role, compatibility, lifecycle,
    required-capability, commercial-purpose); an empty value means the
    candidate survived filtering into scoring. ``score`` is the integer
    total when scored, or ``None`` when eliminated before scoring.
    """

    component_id: str
    component_version: str = ""
    eliminated_by: str = ""
    score: Optional[int] = None
    score_components: Tuple[SelectionScoreComponent, ...] = ()


class SlotSelectionTrace(FrozenModel):
    """Per-slot record of the deterministic selection decision (§14.3).

    Records candidates considered (top-5 named), eliminations, scores,
    tie-break application, and the chosen ``(component_id, version,
    variant)``. Beyond the top-5 named candidates, eliminations compress to
    per-filter counts in ``elimination_counts`` (filter ID → count).
    """

    slot_id: str
    candidates: Tuple[SelectionCandidate, ...] = ()
    elimination_counts: Dict[str, int] = {}
    tie_break_basis: str = ""
    chosen_component_id: str = ""
    chosen_component_version: str = ""
    chosen_variant: str = ""


class SelectionTrace(FrozenModel):
    """Schema-versioned selection-trace block embedded in ComponentManifest.

    Produced deterministically by the (future) Component Engine as a pure
    function of a deterministic selection; ignored by the Layout Engine
    (§14.3, ADR-14). Hashes with the manifest and travels with provenance.
    """

    schema_version: str = SELECTION_TRACE_SCHEMA_VERSION
    slots: Tuple[SlotSelectionTrace, ...] = ()


class ComponentManifestV1(ArtifactHeader):
    """ComponentManifest schema 1.0.0 (pre-amendment shape).

    Retained for replay and validation of manifests produced before
    amendment A1. It carries no ``selection_trace`` field, so its canonical
    serialization and content hash are byte-identical to the original 1.0.0
    contract. The current schema is 1.1.0 (:class:`ComponentManifest`).
    Internal compatibility model — not part of the public surface.
    """

    artifact_kind: ArtifactKind = ArtifactKind.COMPONENT_MANIFEST
    pages: Tuple[PageComponents, ...] = ()


class ComponentManifest(ArtifactHeader):
    """Per-page component instances (§4.1 artifact #6). Schema 1.1.0.

    Amendment A1 (AES-WEB-002 §14.3, ADR-14): optionally carries a
    schema-versioned ``selection_trace`` block recording per-slot candidate
    filtering, scoring, and tie-breaking, produced deterministically by the
    Component Engine and ignored by the Layout Engine. The field is additive
    and optional (absent by default), so 1.0.0 payloads still parse and the
    schema bump from 1.0.0 to 1.1.0 requires no migration.
    """

    artifact_kind: ArtifactKind = ArtifactKind.COMPONENT_MANIFEST
    pages: Tuple[PageComponents, ...] = ()
    selection_trace: Optional[SelectionTrace] = None


class ComponentCompilationResult(FrozenModel):
    """Non-artifact result of :meth:`ComponentEngineInterface.compile`
    (AES-WEB-002J.19; ADR-WEB-CONTENT-BINDING-MAP; AES-WEB-002K.1).

    Bundles the bound ``ComponentManifest`` with its companion
    ``ContentPackage`` -- the original input blocks plus every block Phase B
    projected from ``ListingDataset``/derived values -- plus (AES-WEB-002K.1)
    ``render_data``: the typed, non-artifact link/card/contact/hours data
    the Renderer needs to emit real hyperlinks and enriched listing cards,
    which flat ``ContentBlock.text`` cannot represent
    (``contracts/render_data.py``). Deliberately **not** an
    :class:`ArtifactHeader` subclass: it carries no ``schema_version``/
    ``artifact_kind``/``source_hashes`` of its own and is never registered
    in the schema catalog (``contracts/versions.py``) -- it is an internal
    engine-call return value, not one of the AES-WEB-001 §4.1 (+ J.17)
    artifact kinds. ``render_data`` defaults to an empty bundle, so every
    pre-K.1 caller/test remains source-compatible.
    """

    component_manifest: ComponentManifest
    content_package: ContentPackage
    render_data: RenderDataBundle = RenderDataBundle(entries=())


# ---------------------------------------------------------------------------
# 7. LayoutPlan — schema 1.1.0 with typed region identity and deterministic
# grid/responsive placement (AES-WEB-001 §5.6 / Part 2 / Part 13 Phase 2
# amendment; internal sequencing label AES-WEB-002J.7)
# ---------------------------------------------------------------------------

class LayoutRegion(FrozenModel):
    """An ordered region holding component indexes from the manifest.

    Unchanged since schema 1.0.0 and shared byte-for-byte by
    :class:`LayoutPlanV1` and :class:`LayoutPlan`. ``region_id`` is a plain
    string for 1.0.0 compatibility; engine-produced plans set it to the
    producing :class:`~engines.website_generation.contracts.enums.RegionKind`
    value, and schema 1.1.0's :class:`RegionLayoutDetail` carries the same
    identity typed as the enum for downstream (Renderer) consumption.
    ``component_indexes`` are the original ``ComponentManifest`` page
    indexes, in manifest order -- never renumbered.
    """

    region_id: str
    component_indexes: Tuple[int, ...] = ()


class PageLayout(FrozenModel):
    """Deterministic composition tree for one page.

    Unchanged since schema 1.0.0 and shared byte-for-byte by
    :class:`LayoutPlanV1` and :class:`LayoutPlan`.
    """

    route: str
    regions: Tuple[LayoutRegion, ...] = ()


class LayoutPlanV1(ArtifactHeader):
    """LayoutPlan schema 1.0.0 (pre-J.7 shape).

    Retained for replay of plans produced before AES-WEB-002J.7. Carries
    none of the J.7 fields (``region_details``), so its canonical
    serialization and content hash are byte-identical to the original 1.0.0
    contract. The current schema is 1.1.0 (:class:`LayoutPlan`). Internal
    compatibility model — not part of the public surface.
    """

    artifact_kind: ArtifactKind = ArtifactKind.LAYOUT_PLAN
    pages: Tuple[PageLayout, ...] = ()


class GridPlacement(FrozenModel):
    """Deterministic abstract grid placement referencing BrandPackage tokens
    (AES-WEB-002 §8.3, §10 -- semantic tokens only, never pixels or CSS).

    ``columns_token`` is the first ``grid.columns.*`` token the component's
    ``design_token_dependencies`` declares (declared-order tie-break, §10.3),
    or ``""`` when the component declares no grid-columns dependency
    (single-column/flow placement -- the deterministic default, never
    invented). ``column_span`` is always 1: the Layout Engine performs no
    grid-solving (AES-WEB-001 §5.6 "no complex grid-solving algorithm").
    """

    columns_token: str = ""
    column_span: int = 1


class ResponsiveSelection(FrozenModel):
    """Responsive adaptation mirrored verbatim from the component's
    ``ResponsiveContract`` (AES-WEB-002 §11.2: LayoutPlan chooses only among
    adaptations the registry already authorizes; every MVP component
    declares exactly one authorized adaptation, so the Layout Engine's
    "choice" is a deterministic copy, never an invention of new behavior).
    """

    collapse_behavior: str = ""
    mobile_order: str = "dom-order"
    content_priority: Tuple[str, ...] = ()
    truncation: str = "none"
    sticky: str = "none"
    table_adaptation: str = ""
    image_behavior: str = ""


class ComponentPlacement(FrozenModel):
    """Deterministic grid and responsive placement for one component
    instance, keyed back to its original ``ComponentManifest`` page index
    (AES-WEB-002 §8.2/§11 -- never a renumbered or region-local index)."""

    component_index: int
    grid: GridPlacement = Field(default_factory=GridPlacement)
    responsive: ResponsiveSelection = Field(default_factory=ResponsiveSelection)


class RegionLayoutDetail(FrozenModel):
    """Typed region identity and per-component placement detail for one
    region already present in ``pages`` (AES-WEB-002 §9.1). Schema 1.1.0
    only -- keyed back to its ``LayoutRegion`` by ``(route, region_id)``.
    ``placements`` preserves the same order as the matching
    ``LayoutRegion.component_indexes``.
    """

    route: str
    region_id: str
    region_kind: RegionKind
    placements: Tuple[ComponentPlacement, ...] = ()


class LayoutPlan(ArtifactHeader):
    """Deterministic page composition (§4.1 artifact #7). Schema 1.1.0.

    AES-WEB-002J.7 (AES-WEB-001 §5.6 / Part 2 / Part 13 Phase 2): additive
    over the 1.0.0 shape (:class:`LayoutPlanV1`) with ``region_details``
    carrying typed region identity plus deterministic grid and responsive
    placement. No migration required -- the field is additive and old 1.0.0
    payloads still load via LayoutPlanV1.
    """

    artifact_kind: ArtifactKind = ArtifactKind.LAYOUT_PLAN
    pages: Tuple[PageLayout, ...] = ()
    region_details: Tuple[RegionLayoutDetail, ...] = ()


# ---------------------------------------------------------------------------
# 8. RenderedPageSet — schema 1.1.0 with HTML/shared-CSS text payloads
# (AES-WEB-001 §5.7 / Part 2; internal sequencing label AES-WEB-002J.8)
# ---------------------------------------------------------------------------

class RenderedPage(FrozenModel):
    """One emitted page referenced by content hash (no embedded binary).

    Unchanged since schema 1.0.0 and shared byte-for-byte by
    :class:`RenderedPageSetV1` and :class:`RenderedPageSet`. ``css_hash``
    stays ``""`` for every page: CSS is emitted once per build and shared
    across pages (AES-WEB-001 §5.7/§8.4; AES-WEB-002 §20.2), never
    per-page -- the field is retained only for 1.0.0 replay compatibility.
    """

    route: str
    html_hash: str
    css_hash: str = ""


class RenderedPageSetV1(ArtifactHeader):
    """RenderedPageSet schema 1.0.0 (pre-J.8 hash-only shape).

    Retained for replay of page sets produced before AES-WEB-002J.8. Carries
    no HTML/CSS text payload -- only content hashes -- so its canonical
    serialization and content hash are byte-identical to the original 1.0.0
    contract. The current schema is 1.1.0 (:class:`RenderedPageSet`).
    Internal compatibility model -- not part of the public surface.
    """

    artifact_kind: ArtifactKind = ArtifactKind.RENDERED_PAGE_SET
    pages: Tuple[RenderedPage, ...] = ()
    shared_css_hash: str = ""


class RenderedPageDetail(FrozenModel):
    """Emitted HTML text payload for one page (AES-WEB-001 §5.7; schema
    1.1.0 addition). Schema 1.1.0 only -- keyed back to its ``RenderedPage``
    by ``route`` (mirroring the ``RegionLayoutDetail``/``LayoutPlan`` J.7
    idiom: new capability is a new sibling nested model, never a
    restructured existing field).

    Text only, per §4.3 ("artifacts themselves never embed binary data") --
    HTML/CSS are UTF-8 text, not images/fonts, so this is not a CAS-binary
    exception.
    """

    route: str
    html: str


class RenderedPageSet(ArtifactHeader):
    """Emitted HTML/CSS per page, content-hashed (§4.1 artifact #8).
    Schema 1.1.0.

    AES-WEB-002J.8 (AES-WEB-001 §5.7 / Part 2): additive over the 1.0.0
    shape (:class:`RenderedPageSetV1`) with ``page_details`` (per-page HTML
    text, keyed back to ``pages`` by route) and ``shared_css`` (the shared
    CSS text payload backing ``shared_css_hash``). The Renderer is a pure
    engine with no CAS/filesystem access of its own (AES-WEB-001 §5's
    "no side effects" engine contract), so the emitted text must travel
    inside the returned artifact for a future service layer to persist it.
    No migration required -- the fields are additive and old 1.0.0 payloads
    still load via RenderedPageSetV1.
    """

    artifact_kind: ArtifactKind = ArtifactKind.RENDERED_PAGE_SET
    pages: Tuple[RenderedPage, ...] = ()
    shared_css_hash: str = ""
    page_details: Tuple[RenderedPageDetail, ...] = ()
    shared_css: str = ""


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
# 10. SiteBundle — schema 1.1.0 with per-file text payloads (AES-WEB-001
# §5.9 / Part 2; internal sequencing label AES-WEB-002J.10)
# ---------------------------------------------------------------------------

class SiteBundleV1(ArtifactHeader):
    """SiteBundle schema 1.0.0 (pre-J.10 hash-only shape).

    Retained for replay of bundles produced before AES-WEB-002J.10. Carries
    no per-file text payload -- only the ``file_map`` (path → content hash)
    and ``bundle_hash`` -- so its canonical serialization and content hash
    are byte-identical to the original 1.0.0 contract. The current schema is
    1.1.0 (:class:`SiteBundle`). Internal compatibility model -- not part of
    the public surface.
    """

    artifact_kind: ArtifactKind = ArtifactKind.SITE_BUNDLE
    file_map: Dict[str, str] = {}
    bundle_hash: str = ""


class BundleFile(FrozenModel):
    """One emitted static-site file: its bundle-root-relative path and its
    UTF-8 text content (AES-WEB-001 §5.9; schema 1.1.0 addition).

    Text only, per §4.3 ("artifacts themselves never embed binary data") --
    HTML/CSS/XML/robots are UTF-8 text, not images/fonts, so this is not a
    CAS-binary exception (the same reasoning :class:`RenderedPageDetail`
    documents). ``path`` is always a forward-slash, bundle-root-relative
    path (never absolute, never containing ``..``); its content hash is the
    matching :attr:`SiteBundle.file_map` entry (``file_map[path]``), so the
    hash is not duplicated onto this model.
    """

    path: str
    content: str


class SiteBundle(ArtifactHeader):
    """Complete static site file map: path → content hash (§4.1 artifact
    #10). Schema 1.1.0.

    AES-WEB-002J.10 (AES-WEB-001 §5.9 / Part 2): additive over the 1.0.0
    shape (:class:`SiteBundleV1`) with ``files`` (the per-file UTF-8 text
    payloads whose content hashes are ``file_map``). The Assembly Engine is a
    pure engine with no CAS/filesystem access of its own (§5.9 "No file I/O
    -- the repository materializes the bundle to disk"), so the assembled
    text must travel inside the returned artifact for the (future)
    site_bundle_repository (§9.3) to persist it. ``file_map`` stays the
    §5.9-mandated path → content-hash map and ``bundle_hash`` the hash of the
    sorted file map; ``files`` carries the same paths' content, keyed back to
    ``file_map`` by path. No migration required -- the field is additive and
    old 1.0.0 payloads still load via SiteBundleV1.
    """

    artifact_kind: ArtifactKind = ArtifactKind.SITE_BUNDLE
    file_map: Dict[str, str] = {}
    bundle_hash: str = ""
    files: Tuple[BundleFile, ...] = ()


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


class QualityReportV1(ArtifactHeader):
    """QualityReport schema 1.0.0 (pre-J.11 shape).

    Retained for replay of reports produced before AES-WEB-002J.11. Carries
    no ``deferred_gate_ids`` field, so its canonical serialization and
    content hash are byte-identical to the original 1.0.0 contract. The
    current schema is 1.1.0 (:class:`QualityReport`). Internal compatibility
    model -- not part of the public surface.
    """

    artifact_kind: ArtifactKind = ArtifactKind.QUALITY_REPORT
    gate_results: Tuple[GateResult, ...] = ()
    certified: bool = False
    certificate: Optional[LaunchCertificateBody] = None


class QualityReport(ArtifactHeader):
    """Gate results and optional certificate (§4.1 artifact #11).
    Schema 1.1.0.

    AES-WEB-002J.11 (AES-WEB-001 §5.10 / Part 2): additive over the 1.0.0
    shape (:class:`QualityReportV1`) with ``deferred_gate_ids`` -- the
    registered gates the Quality Gate Engine did not evaluate this run
    (because the deterministic static facts they require are not derivable
    from the current artifacts), so the report is self-describing about its
    own coverage rather than silently omitting them (the AES-005A
    quality-gate honesty lesson, §5.10). ``gate_results`` carries the
    evaluated gates' verdicts; a gate id appears in exactly one of
    ``gate_results`` or ``deferred_gate_ids``, never both. No migration
    required -- the field is additive and old 1.0.0 payloads still load via
    QualityReportV1.
    """

    artifact_kind: ArtifactKind = ArtifactKind.QUALITY_REPORT
    gate_results: Tuple[GateResult, ...] = ()
    certified: bool = False
    certificate: Optional[LaunchCertificateBody] = None
    deferred_gate_ids: Tuple[str, ...] = ()


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


# ---------------------------------------------------------------------------
# 13. ListingDataset (AES-WEB-002J.17 -- ADR-WEB-LISTING-DATASET; additive
# to the AES-WEB-001 §4.1 twelve-artifact catalog)
# ---------------------------------------------------------------------------

class ListingContact(FrozenModel):
    """Phone/email/website contact fields (shape-validated only; ADR §9)."""

    phone: str = ""
    email: str = ""
    website_url: str = ""


class ListingAddress(FrozenModel):
    """A postal address. No geocoding or normalization is performed here."""

    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""


class ListingGeo(FrozenModel):
    """Integer micro-degree coordinates (§4.3 float prohibition; ADR §5).
    ``lat_micro``/``long_micro`` are ``degrees * 1_000_000``."""

    lat_micro: int
    long_micro: int


class ListingRating(FrozenModel):
    """Aggregate rating only -- no raw review corpus in v1 (ADR scope).
    ``rating_hundredths`` mirrors :class:`ContrastEvidence`'s integer-ratio
    convention (``450`` means 4.50)."""

    rating_hundredths: int
    review_count: int


class ListingHoursEntry(FrozenModel):
    """One weekday's operating hours. ``opens``/``closes`` use ``HH:MM``
    (24-hour) and are both required unless ``closed`` is true."""

    day: Weekday
    opens: str = ""
    closes: str = ""
    closed: bool = False


class ListingSponsorship(FrozenModel):
    """Sponsorship *state* -- monetization policy/tier rules live in
    ``constants/``, never here (ADR §12)."""

    kind: ListingKind
    disclosure_text: str = ""


class ListingVerification(FrozenModel):
    """Verification *state* only -- methodology is AES-WEB-005's future
    authority (ADR §13). ``verified_at`` is a preserved external input,
    never generated at compile time."""

    status: VerificationStatus
    verified_at: str = ""
    source: str = ""


class ListingAssetRef(FrozenModel):
    """A CAS hash reference into an asset store (§10.2's ``AssetRole`` id
    space) -- never a filesystem path or URL."""

    role: AssetRole
    asset_hash: str


class ListingCTA(FrozenModel):
    """A single call-to-action target for a listing."""

    label: str
    target_route: str


class ListingProvenance(FrozenModel):
    """Minimal upstream-sourcing provenance (ADR §11). ``observed_at`` is a
    preserved external input, never generated at compile time."""

    source_id: str
    source_type: str = ""
    source_record_id: str = ""
    source_url: str = ""
    observed_at: str = ""
    source_hash: str = ""


class ListingCategory(FrozenModel):
    """A category a listing may belong to (§27.5 directory taxonomy)."""

    category_id: str
    label: str
    slug: str


class ListingLocation(FrozenModel):
    """A location a listing may belong to."""

    location_id: str
    city: str
    state: str
    slug: str


class ListingRecord(FrozenModel):
    """One listing's deterministic input facts (ADR §7-§9). Exactly one
    ``category_id`` (required); ``location_id`` is zero-or-one (empty
    string means none). No ``canonical_route`` field -- route derivation is
    IA/Component-binding policy (ADR §6), never stored here."""

    listing_id: str
    business_name: str
    slug: str
    category_id: str
    location_id: str = ""
    description: str = ""
    listing_kind: ListingKind = ListingKind.ORGANIC
    contact: Optional[ListingContact] = None
    address: Optional[ListingAddress] = None
    geo: Optional[ListingGeo] = None
    rating: Optional[ListingRating] = None
    hours: Tuple[ListingHoursEntry, ...] = ()
    sponsorship: Optional[ListingSponsorship] = None
    verification: Optional[ListingVerification] = None
    credentials: Tuple[str, ...] = ()
    assets: Tuple[ListingAssetRef, ...] = ()
    cta: Optional[ListingCTA] = None
    provenance: Optional[ListingProvenance] = None


class ListingDataset(ArtifactHeader):
    """A deterministic, normalized corpus of listings plus their categories
    and locations (AES-WEB-002J.17 additive artifact #13;
    ADR-WEB-LISTING-DATASET). Schema 1.0.0.

    Input state for the Website Generation Engine -- not the operational
    data authority (AES-WEB-005, when written, owns sourcing/freshness/
    verification methodology/correction). An empty dataset
    (``listings=(), categories=(), locations=()``) is valid. The Component
    Engine's (future) binding phase is the sole intended consumer; the
    Renderer never consumes this artifact directly.
    """

    artifact_kind: ArtifactKind = ArtifactKind.LISTING_DATASET
    listings: Tuple[ListingRecord, ...] = ()
    categories: Tuple[ListingCategory, ...] = ()
    locations: Tuple[ListingLocation, ...] = ()

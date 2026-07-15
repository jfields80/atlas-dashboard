"""Abstract interfaces for the Website Generation Engine (Phase 1 subset).

AES-WEB-001 §3.5 declares extension points as abstract interfaces in
``contracts/interfaces.py``. Phase 1 needs only the typed stage boundary
the skeleton pipeline composes against; DeploymentAdapter, GateCheck, and
CognitionProvider interfaces arrive with their implementing phases (never
before — no interface is declared here until a phase consumes it).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence, Tuple

from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    ComponentCompilationResult,
    ComponentManifest,
    ContentCandidate,
    ContentPackage,
    LayoutPlan,
    ListingDataset,
    QualityReport,
    RenderedPageSet,
    SEOPackage,
    SiteArchitecture,
    SiteBundle,
    SpecCompilerInput,
)
from engines.website_generation.contracts.components import (
    ComponentDefinition,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    ComponentFamily,
    LifecycleStatus,
    PageRole,
)
from engines.website_generation.contracts.render_data import RenderDataBundle


class SpecCompilerInterface(ABC):
    """The sole ingestion boundary into the WGE (AES-WEB-001 §5.1)."""

    @abstractmethod
    def compile(self, compiler_input: SpecCompilerInput) -> BusinessSpec:
        """Compile upstream values into a canonical BusinessSpec."""
        raise NotImplementedError


class BrandEngineInterface(ABC):
    """The Brand Engine's sole entry point (AES-WEB-001 §5.2 / Part 2)."""

    @abstractmethod
    def resolve(self, spec: BusinessSpec) -> BrandPackage:
        """Resolve a BusinessSpec into a deterministic BrandPackage."""
        raise NotImplementedError


class InformationArchitectureEngineInterface(ABC):
    """The Information Architecture Engine's sole entry point (AES-WEB-001
    §5.3).

    ``listing_dataset`` is an additive, optionally-``None`` input
    (AES-WEB-002K.1): omitted, ``plan`` is byte-identical to its pre-K.1
    behavior (home + category routes only); supplied, one additional
    ``business-profile`` ``PagePlan`` is emitted per ``ListingRecord``
    (ADR-WEB-LISTING-DATASET §6 route convention), excluded from
    ``nav_routes`` (site-wide navigation names category routes only, never
    every business)."""

    @abstractmethod
    def plan(
        self,
        spec: BusinessSpec,
        brand: BrandPackage,
        listing_dataset: Optional[ListingDataset] = None,
        editorial_pages: Tuple[Tuple[str, str], ...] = (),
    ) -> SiteArchitecture:
        """Plan a deterministic SiteArchitecture from a BusinessSpec and a
        BrandPackage, plus (AES-WEB-002K.1) the optional profile-route
        expansion a ListingDataset enables and (PILOT-PTF-1) the optional
        static/trust ``(route, title)`` pages ``editorial_pages`` enables."""
        raise NotImplementedError


class ContentEngineInterface(ABC):
    """The Content Engine's sole entry point (AES-WEB-001 §5.4).

    The determinism airlock: validates candidates against slot schemas and
    policy constraints into a deterministic ``ContentPackage``. Not a
    generation interface -- there is no ``generate``/``resolve``/``draft``/
    ``author`` method, by design (Decision A1/A2).
    """

    @abstractmethod
    def validate(
        self,
        site_architecture: SiteArchitecture,
        candidates: Sequence[ContentCandidate],
        business_spec: BusinessSpec,
    ) -> ContentPackage:
        """Validate ContentCandidates against a SiteArchitecture and
        BusinessSpec into a deterministic ContentPackage."""
        raise NotImplementedError


class SEOEngineInterface(ABC):
    """The SEO Engine's sole entry point (AES-WEB-001 §5.8).

    Compiles titles, meta descriptions, canonical URLs, the sitemap plan,
    and robots directives from already-validated artifacts. Structured data
    is out of scope for this delivery (AES-WEB-002J.5 Decision D4) -- there
    is no ``generate``/``draft``/``author`` method, by design.
    """

    @abstractmethod
    def compile(
        self,
        site_architecture: SiteArchitecture,
        content_package: ContentPackage,
        business_spec: BusinessSpec,
        base_url: str = "",
    ) -> SEOPackage:
        """Compile a deterministic SEOPackage from a SiteArchitecture,
        ContentPackage, and BusinessSpec. ``base_url`` (AES-WEB-002K.1) is
        additive: empty (default) preserves the pre-K.1 self-canonical
        (route-relative) behavior; supplied, canonical/sitemap URLs become
        absolute (``base_url.rstrip("/") + route``)."""
        raise NotImplementedError


class ComponentEngineInterface(ABC):
    """The Component Engine's sole entry point (AES-WEB-001 §5.5).

    Maps each ``SiteArchitecture`` page's recipe slots to component
    instances from the registry (AES-WEB-002 §14, §26), then binds every
    honestly-bindable required field (AES-WEB-002J.19 Phase B;
    ADR-WEB-CONTENT-BINDING-MAP), emitting a deterministic
    ``ComponentCompilationResult`` — a bound ``ComponentManifest`` with an
    embedded ``selection_trace`` (§14.3, ADR-14), plus the companion
    ``ContentPackage`` (the original input blocks plus every block Phase B
    projected). Selection is the pure §14.2 pipeline, now bindability-aware
    (§14.2 extended by J.19: a candidate whose required fields are
    categorically unbindable under the current architecture is eliminated
    before scoring, never silently bound with fabricated values). There is
    no ``generate``/``draft``/``author`` method, by design.

    ``listing_dataset``/``brand_package`` are additive, optionally-``None``
    inputs (J.19): omitting one is honest only when no *selected* required
    binding rule needs it -- Phase B fails the whole compile, never a
    partial result, when a selected required field's source is missing.
    The registry is an injected read-only :class:`ComponentRegistryView`
    dependency (§15.3), not an artifact input, so tests may drive the engine
    with reduced fixture registries.
    """

    @abstractmethod
    def compile(
        self,
        site_architecture: SiteArchitecture,
        content_package: ContentPackage,
        listing_dataset: Optional[ListingDataset] = None,
        brand_package: Optional[BrandPackage] = None,
        commercial_strategy: str = "directory",
    ) -> ComponentCompilationResult:
        """Compile a deterministic ``ComponentCompilationResult`` from a
        ``SiteArchitecture``, ``ContentPackage``, and the optional
        ``ListingDataset``/``BrandPackage`` Phase-B binding inputs.

        ``commercial_strategy`` (AES-WEB-002L.1, additive, defaulting to
        ``"directory"`` -- byte-identical to pre-L.1 behavior when omitted)
        selects which per-page-role recipe/commercial-defaults table
        composes each page; a pre-classified strategy id, never a
        ``BusinessSpec`` itself (the Component Engine consumes a
        declarative strategy selection, it does not classify one -- see
        ``components/commercial_strategy.classify_commercial_strategy``,
        which the caller runs beforehand). Literal string, not an imported
        constant: ``contracts/`` may not import ``constants/`` (independent
        declaration, must stay byte-identical to ``constants.commercial_
        strategy.STRATEGY_DIRECTORY``)."""
        raise NotImplementedError


class LayoutEngineInterface(ABC):
    """The Layout Engine's sole entry point (AES-WEB-001 §5.6).

    Composes ordered page regions and responsive/grid placement, expressed
    purely in design tokens and component-contract data, from a
    ``ComponentManifest`` and a ``BrandPackage`` (AES-WEB-002J.7 decision
    D-3: public artifact inputs only -- no ``SiteArchitecture``). Produces
    no markup -- only a composition tree the (future) Renderer walks. There
    is no ``select``/``draft``/``author`` method, by design: the Layout
    Engine never selects components or variants, only places what the
    ComponentManifest already chose. The registry is an injected read-only
    :class:`ComponentRegistryView` dependency (AES-WEB-002J.7 decision D-3),
    not an artifact input and not a method parameter -- ``layouts/`` may not
    import the sibling ``components/`` package that builds the default
    registry, so the concrete engine receives it through constructor
    injection instead of a default-factory keyword (contrast
    ``ComponentEngineInterface``, whose concrete class lives inside
    ``components/`` and therefore can default it).
    """

    @abstractmethod
    def compose(
        self,
        component_manifest: ComponentManifest,
        brand_package: BrandPackage,
    ) -> LayoutPlan:
        """Compose a deterministic ``LayoutPlan`` from a ``ComponentManifest``
        and a ``BrandPackage``."""
        raise NotImplementedError


class RendererInterface(ABC):
    """The Renderer's sole entry point (AES-WEB-001 §5.7).

    Emits deterministic HTML/CSS from a ``LayoutPlan``, resolving component
    instances from the ``ComponentManifest`` (AES-WEB-002J.8 decision D-1:
    ``LayoutPlan.ComponentPlacement.component_index`` names an index into
    ``ComponentManifest`` page components, so the Renderer needs the
    manifest as a fourth input beyond the three §5.7 summarizes -- the
    manifest is not itself walked or reordered, only indexed). Binds content
    from ``ContentPackage`` and design tokens from ``BrandPackage``. Produces
    no selection, no layout decisions, no SEO metadata, and no file output --
    only a ``RenderedPageSet``. There is no ``select``/``compose``/``plan``
    method, by design: the Renderer never selects components, reorders
    layout, or invents content. The registry is an injected read-only
    :class:`ComponentRegistryView` dependency (mirroring
    ``LayoutEngineInterface``'s constructor-injection precedent), not an
    artifact input and not a method parameter -- ``rendering/`` may not
    import the sibling ``components/`` package that builds the default
    registry.

    ``render_data`` is an additive, optionally-``None`` input
    (AES-WEB-002K.1): the typed link/card/contact/hours data
    (``contracts/render_data.py``) the Component Engine's Phase B already
    produced, keyed by ``(route, component_index)`` -- the Renderer only
    *indexes* it (the same way it indexes the manifest), never derives it.
    Omitted, rendering is byte-identical to pre-K.1 behavior.
    """

    @abstractmethod
    def render(
        self,
        layout_plan: LayoutPlan,
        component_manifest: ComponentManifest,
        content_package: ContentPackage,
        brand_package: BrandPackage,
        render_data: Optional[RenderDataBundle] = None,
    ) -> RenderedPageSet:
        """Render a deterministic ``RenderedPageSet`` from a ``LayoutPlan``,
        ``ComponentManifest``, ``ContentPackage``, ``BrandPackage``, and
        (AES-WEB-002K.1) the optional ``RenderDataBundle``."""
        raise NotImplementedError


class AssemblyEngineInterface(ABC):
    """The Assembly Engine's sole entry point (AES-WEB-001 §5.9).

    Produces the complete static site as a deterministic ``SiteBundle``:
    injects the ``SEOPackage``'s per-route metadata (title, meta description,
    self-canonical URL) plus the shared-stylesheet link into each
    ``RenderedPageSet`` page's ``<head>`` (preserving the Renderer's body
    byte-for-byte), maps every route to a bundle-root-relative output file,
    emits ``sitemap.xml``/``robots.txt`` from the SEO artifact, and computes
    the bundle-level hash. Pure engine: **No file I/O** -- the (future)
    site_bundle_repository materializes the bundle to disk (§5.9, §9.3);
    ``BrandPackage`` is accepted for asset provenance (§5.9 "BrandPackage
    (assets)") and source-hash completeness. There is no
    ``render``/``compile``/``select`` method, by design: Assembly never
    re-renders body markup, recomputes SEO decisions, executes gates, or
    writes files.
    """

    @abstractmethod
    def assemble(
        self,
        rendered_page_set: RenderedPageSet,
        seo_package: SEOPackage,
        brand_package: BrandPackage,
    ) -> SiteBundle:
        """Assemble a deterministic ``SiteBundle`` from a ``RenderedPageSet``,
        ``SEOPackage``, and ``BrandPackage``."""
        raise NotImplementedError


class QualityGateEngineInterface(ABC):
    """The Quality Gate Engine's sole entry point (AES-WEB-001 §5.10).

    Evaluates the registered gate list (``constants/gates.py``) in declared
    order against the assembled artifacts and returns a deterministic
    ``QualityReport``. Every gate content failure is a typed ``GateResult``
    (``passed=False``), never an exception (§5.10); only gate *malfunction*
    raises ``GateExecutionError``. Gates whose required deterministic static
    facts are not derivable from the current artifacts are reported in the
    report's ``deferred_gate_ids`` rather than silently omitted or falsely
    passed (the AES-005A honesty lesson). Inputs are the four §5.10 declared
    artifacts plus (AES-WEB-002L.2) the optional ``component_manifest``;
    the engine reads no engine implementation, no filesystem, and
    no network -- it consumes artifacts only, and writes nothing (report
    persistence is a repository concern). There is no
    ``render``/``assemble``/``compile`` method, by design.
    """

    @abstractmethod
    def evaluate(
        self,
        site_bundle: SiteBundle,
        seo_package: SEOPackage,
        content_package: ContentPackage,
        site_architecture: SiteArchitecture,
        component_manifest: Optional[ComponentManifest] = None,
    ) -> QualityReport:
        """Evaluate a deterministic ``QualityReport`` from a ``SiteBundle``,
        ``SEOPackage``, ``ContentPackage``, and ``SiteArchitecture``.

        ``component_manifest`` (AES-WEB-002L.2, additive, optional) supplies
        the page's already-resolved ``CommercialStrategy``
        (``source_hashes["commercial_strategy"]``) so CG-CMP-010's real
        evaluation can verify the CommercialStrategy layer's own declared
        page requirements (primary CTA, required trust surfaces, non-empty
        commercial main) against the real rendered output -- verification,
        never (re)classification. Omitting it reproduces the exact pre-L.2
        report byte-for-byte (CG-CMP-010 stays in ``deferred_gate_ids``)."""
        raise NotImplementedError


class ComponentRegistryView(ABC):
    """Read-only registry protocol the Component Engine consumes (§15.3).

    The concrete registry implements this. Every accessor is a pure,
    deterministic lookup or index over declarative data — no selection,
    scoring, or ranking lives here (that is the §14 pipeline, a later wave).
    Returned collections are immutable tuples.
    """

    @abstractmethod
    def get(
        self, component_id: str, version_req: Optional[str] = None
    ) -> ComponentDefinition:
        """Return the definition for ``component_id`` (optionally a specific
        version). Raises ``ComponentNotFoundError`` /
        ``UnsupportedComponentVersionError``."""
        raise NotImplementedError

    @abstractmethod
    def resolve_variant(
        self, component_id: str, variant: str
    ) -> VariantSpec:
        """Return the ``VariantSpec`` for ``(component_id, variant)``."""
        raise NotImplementedError

    @abstractmethod
    def candidates_for(
        self, page_role: PageRole, slot_need: Optional[str] = None
    ) -> Tuple[ComponentDefinition, ...]:
        """Deterministic index lookup of components declaring support for
        ``page_role`` (sorted by ``component_id``). This is a registry index,
        not selection: no filtering pipeline, scoring, or tie-breaking."""
        raise NotImplementedError

    @abstractmethod
    def by_family(
        self, family: ComponentFamily
    ) -> Tuple[ComponentDefinition, ...]:
        """All definitions in ``family``, ordered by ``component_id``."""
        raise NotImplementedError

    @abstractmethod
    def lifecycle(self, component_id: str) -> LifecycleStatus:
        """The lifecycle status of ``component_id``."""
        raise NotImplementedError

    @abstractmethod
    def replacement_for(self, component_id: str) -> Optional[str]:
        """The replacement component id for a deprecated component, or None."""
        raise NotImplementedError

    @abstractmethod
    def registry_version(self) -> str:
        """The registry semantic version."""
        raise NotImplementedError

    @abstractmethod
    def registry_hash(self) -> str:
        """The SHA-256 registry fingerprint over all definitions."""
        raise NotImplementedError

"""Component-system contracts (AES-WEB-002A — Contracts and Registry).

The frozen, declarative ``ComponentDefinition`` (AES-WEB-002 §3) and its
sub-contracts. These are component-system contracts, **not** part of the
twelve-artifact catalog (AES-WEB-001 §4.1) — no new ``ArtifactKind`` is
added. They live in ``contracts/`` because the component ``catalog/`` may
import only ``contracts/`` and ``constants/`` (AES-WEB-002 §29.2), so the
definition types must be reachable from there.

Doctrine (inherited, non-negotiable): frozen Pydantic models via the
embedded ``pydantic_compat`` isolation (:class:`FrozenModel`), ``extra``
forbidden, tuples instead of lists, no floats, deterministic ``Enum``
serialization, canonical UTF-8 JSON. Per the AES-WEB-001 §4.x contract
doctrine, these models carry **no validators** — semantic validation
(naming grammar, complexity budget, compatibility) is the registry's job
(AES-WEB-002 §15.2), executed at registration time.

The §3 "frozenset of X" fields are realized as ``Tuple[X, ...]`` because
canonical serialization requires a deterministic order (a set has none);
uniqueness/order are validated by the registry, not the model.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from pydantic import Field

from engines.website_generation.contracts.artifacts import FrozenModel
from engines.website_generation.contracts.enums import (
    AssetRole,
    CommercialPurpose,
    ComponentFamily,
    ConversionGoal,
    LifecycleStatus,
    ListingKind,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
)


# ---------------------------------------------------------------------------
# Prop and content-slot specs (AES-WEB-002 §8)
# ---------------------------------------------------------------------------

class PropSpec(FrozenModel):
    """A typed prop declaration (§8.1).

    ``prop_type`` is drawn from the closed :class:`PropType` set. Free-form
    strings are prohibited as props — human-readable text is content and
    belongs in a slot. Optional props (those in ``optional_props``) declare
    a deterministic ``default``; nullable is prohibited (absence is the only
    null). ``enum_values`` applies to ``STR_ENUM``; ``int_min``/``int_max``
    to ``INT_BOUNDED``. The registry validates these invariants (§15.2).
    """

    prop_type: PropType
    enum_values: Tuple[str, ...] = ()
    int_min: Optional[int] = None
    int_max: Optional[int] = None
    default: Optional[str] = None
    description: str = ""


class SlotSpec(FrozenModel):
    """A content-slot declaration (§8.2).

    Slots bind ``ContentPackage`` block references with a declared block
    type and cardinality. ``max_count`` applies only to ``ONE_TO_N``.
    """

    block_type: str
    cardinality: SlotCardinality = SlotCardinality.EXACTLY_ONE
    max_count: Optional[int] = None
    description: str = ""


class VariantSpec(FrozenModel):
    """A named, registered rendering mode of a component (§7.1).

    A variant is a contract-complete presentation mode — not a density
    axis (shared, §7.1), not a responsive adaptation (owned by
    ``responsive_contract``), and not a content-driven state.
    """

    display_name: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# Capability contracts (AES-WEB-002 §11, §12, §13, §16, §17, §18)
# ---------------------------------------------------------------------------

class ResponsiveContract(FrozenModel):
    """Which responsive adaptations a component supports (§11.3).

    The registry owns *which* adaptations exist; ``LayoutPlan`` chooses
    which an instance uses; the renderer emits media queries. Values follow
    the §11.3 grammar (e.g. ``sticky`` ∈ {none, top, bottom}; ``truncation``
    ∈ {none, line-clamp(n)}; ``table_adaptation`` ∈ {scroll-x,
    stacked-rows}).
    """

    collapse_behavior: str = ""
    mobile_order: str = "dom-order"
    content_priority: Tuple[str, ...] = ()
    truncation: str = "none"
    sticky: str = "none"
    table_adaptation: str = ""
    image_behavior: str = ""
    touch_target: str = ""


class AccessibilityContract(FrozenModel):
    """Accessibility roles, states, focus behavior, and labels (§3, §12).

    ``state_machine`` names the §12.6 interactive state machine (e.g.
    ``drawer``, ``accordion``, ``tabs``, ``gallery``, ``pagination``), or is
    empty for static components. ``required_labels`` lists ``A11Y_LABEL``
    prop names that MUST be bound. WCAG 2.2 AA is baseline; verification is
    gate-enforced, not model-enforced.
    """

    state_machine: str = ""
    keyboard_operable: bool = False
    focus_management: bool = False
    required_labels: Tuple[str, ...] = ()
    live_region_role: str = ""


class SEOContract(FrozenModel):
    """SEO capability the component *declares* (§13.1).

    Components declare capability; the SEO Engine remains authoritative for
    site-wide compilation. ``heading_levels`` are the levels the component
    may emit; ``link_kinds`` ∈ {internal, outbound, sponsored, nofollow};
    ``schema_fragments`` are the schema.org fragment types it can
    contribute; ``content_visibility`` ∈ {always-visible,
    progressive-disclosure}.
    """

    heading_levels: Tuple[int, ...] = ()
    link_kinds: Tuple[str, ...] = ()
    schema_fragments: Tuple[str, ...] = ()
    content_visibility: str = "always-visible"


class AnalyticsContract(FrozenModel):
    """Declared analytics identifiers, emitted as inert ``data-`` attributes.

    No analytics SDK or network call exists in the component system (§18);
    identifiers describe the interface, never the visitor. ``impression_id``
    is the stable slug (``component_id`` with dots→dashes);
    ``interaction_events`` is the subset of the event registry
    (``constants/analytics.py``) the component can emit.
    """

    impression_id: str
    interaction_events: Tuple[str, ...] = ()


class ConversionContract(FrozenModel):
    """Conversion declaration for conversion-bearing components (§16.1).

    Declarative only — 002A performs no selection, scoring, or conversion
    resolution. ``urgency_policy`` ∈ {none, spec-backed-offer-only} (§2.1
    E1); ``persuasion_role`` ∈ {initiate, reinforce, close}.
    """

    conversion_goal: ConversionGoal
    primary_action: str = ""
    secondary_action: str = ""
    persuasion_role: str = ""
    urgency_policy: str = "none"
    analytics_event: str = ""
    repetition_limit_per_page: Optional[int] = None
    placement_regions: Tuple[RegionKind, ...] = ()
    success_state: str = ""
    failure_state: str = ""


class DirectoryContract(FrozenModel):
    """Listing-kind semantics and disclosure needs (§6, §6.3)."""

    supported_listing_kinds: Tuple[ListingKind, ...] = ()
    requires_disclosure: bool = False


class MonetizationContract(FrozenModel):
    """Monetization disclosure, link attributes, analytics separation (§17).

    Every monetized surface satisfies visible + semantic + machine-readable
    + analytic disclosure (§17.1). Every ``monetization`` family component
    MUST carry a non-null contract — the registry enforces this (§15.2).
    """

    requires_visible_disclosure: bool = True
    disclosure_kind: str = ""
    link_rel: str = ""
    separated_analytics_event: str = ""


class RenderingContract(FrozenModel):
    """Emitter key, stable class prefix, DOM budget (§3, §20.1, §25).

    ``emitter_key`` resolves to a renderer emitter table entry (validated
    when the renderer exists, in a later wave); ``class_prefix`` is the
    component's stable ``ac-<family>`` class prefix; ``dom_budget`` is the
    §25 per-instance element ceiling.
    """

    emitter_key: str
    class_prefix: str
    dom_budget: Optional[int] = None


class DeprecationInfo(FrozenModel):
    """Deprecation metadata (§3, §22.4).

    Present only when ``lifecycle_status`` is ``DEPRECATED``; a
    ``replacement_component_id`` on the definition is then mandatory.
    """

    since_version: str
    sunset_after_registry_minors: int = 2
    reason: str = ""


# ---------------------------------------------------------------------------
# ComponentDefinition (AES-WEB-002 §3)
# ---------------------------------------------------------------------------

class ComponentDefinition(FrozenModel):
    """The normative, frozen, declarative component contract (§3).

    Identity is ``(component_id, component_version)``; the registry keys by
    ``component_id`` and serves the version index. This is declarative data
    only — it describes identity, contracts, and capabilities, and never
    carries markup, emitters, selection logic, or runtime behavior (§2.2).

    The §3 "frozenset of X" fields are realized as ``Tuple[X, ...]`` for
    canonical serializability; the registry validates uniqueness/order.
    """

    # Identity and lifecycle
    component_id: str
    component_family: ComponentFamily
    component_version: str
    lifecycle_status: LifecycleStatus
    display_name: str = ""
    description: str = ""

    # Commercial purpose (§2.1)
    commercial_purpose: CommercialPurpose
    secondary_purposes: Tuple[CommercialPurpose, ...] = ()

    # Placement compatibility (§6)
    supported_page_roles: Tuple[PageRole, ...] = ()

    # Props and content slots (§8)
    required_props: Dict[str, PropSpec] = {}
    optional_props: Dict[str, PropSpec] = {}
    required_content_slots: Dict[str, SlotSpec] = {}
    optional_content_slots: Dict[str, SlotSpec] = {}

    # Assets and variants (§3, §7)
    supported_asset_roles: Tuple[AssetRole, ...] = ()
    supported_variants: Dict[str, VariantSpec] = {}
    default_variant: str = ""

    # Structure and composition (§3, §9)
    semantic_element: SemanticElement = SemanticElement.DIV
    allowed_parent_regions: Tuple[RegionKind, ...] = ()
    allowed_child_components: Tuple[str, ...] = ()
    forbidden_child_components: Tuple[str, ...] = ()

    # Tokens (§10)
    design_token_dependencies: Tuple[str, ...] = ()

    # Capability contracts (§11, §12, §13, §18)
    responsive_contract: ResponsiveContract = Field(
        default_factory=ResponsiveContract
    )
    accessibility_contract: AccessibilityContract = Field(
        default_factory=AccessibilityContract
    )
    seo_contract: SEOContract = Field(default_factory=SEOContract)
    analytics_contract: AnalyticsContract

    # Optional capability contracts (§16, §6, §17)
    conversion_contract: Optional[ConversionContract] = None
    directory_contract: Optional[DirectoryContract] = None
    monetization_contract: Optional[MonetizationContract] = None

    # Validation, rendering, compatibility (§3, §20, §22)
    validation_rules: Tuple[str, ...] = ()
    rendering_contract: RenderingContract
    compatibility_range: Dict[str, str] = {}

    # Deprecation and gates (§22.4, §21)
    deprecation_status: Optional[DeprecationInfo] = None
    replacement_component_id: Optional[str] = None
    quality_gate_requirements: Tuple[str, ...] = ()
    example_fixture_ids: Tuple[str, ...] = ()

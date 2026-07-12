"""Shared synthetic fixture vocabulary for AES-WEB-002I component gate checks.

AES-WEB-002 §21 defines each gate's inputs as "implied: ComponentManifest +
registry + rendered output + upstream artifacts per family" and states
gates are "executed by the Quality Gate Engine in declared order" (§21
preamble). Per the AES-WEB-002I Architectural Preflight's Ambiguity
Register (decision AMB-002I-01, operator-approved), this repository has no
Quality Gate Engine, no ``GateCheck`` interface, and no ``rendering/``
package (AES-WEB-001 Part 2 / Part 13 Phase 2-3 deliverables, never
executed — see the module docstrings of
``engines.website_generation.gates`` and
``engines.website_generation.constants.gates``). Those remain out of scope
for this delivery.

This module defines a small, local, declaratively-synthetic data
vocabulary used only by the sibling check modules in this package — NOT
the real ``ComponentManifest`` / ``ComponentInstance``
(``contracts/artifacts.py``, which this delivery is not authorized to
modify and whose Phase-1 skeleton shape is too minimal to carry
instance-level facts such as region placement, variant, or bound
prop/slot data) and NOT real rendered HTML/CSS. Every gate-check function
in this package's sibling modules operates only on these synthetic
stand-ins, built by hand in tests as frozen, deterministic fixture data
(AMB-002I-03). No function in this package reads a clock, generates a
UUID, calls a network, or consumes random state — the same input always
produces the same :class:`CheckOutcome`.

Two synthetic shapes cover every §21 gate family:

* :class:`SyntheticInstance` — a bound component instance in a synthetic
  page tree, standing in for what a real ``ComponentManifest`` binding
  (AES-WEB-002 §3.1, §14) would carry once the Component Engine exists.
  Wraps a real, frozen :class:`ComponentDefinition` (the one part of the
  contract that *is* fully built — AES-WEB-002 §3, frozen at 002A exit) so
  every declared capability contract (accessibility, SEO, responsive,
  conversion, monetization, rendering) is checked against real,
  authority-shaped data; only the instance-level *binding* facts are
  synthetic.
* :class:`SyntheticRenderedPage` — hand-authored facts a real Renderer +
  HTML/CSS analysis pass would derive (AES-WEB-002 §20, §21 preamble
  "rendered output"), used only so CG-RND and the rendering-dependent
  members of CG-A11Y/CG-SEO/CG-RSP are individually testable now. This is
  not HTML; it is a flat record of the specific booleans/values each
  gate's §21 pass condition inspects. Do not mistake a passing check
  against this structure for a real rendering-validation result.

Every check function returns a :class:`CheckOutcome` (``passed`` plus a
human-readable ``details`` string naming the page route, instance path,
component id/version, and violating value, per the §21 preamble
diagnostic requirement) rather than a bare ``bool``, so failures are
legible without a debugger — matching the AES-WEB-001 §10.4 two-fixture
discipline these checks are individually tested against.

Import boundary (AES-WEB-002 §29.2, as extended by this delivery): this
package imports only ``engines.website_generation.contracts`` and the
Python standard library. It never imports ``components/registry.py``,
``components/catalog/``, ``rendering/``, ``repositories/``, ``services/``,
``pipeline/``, or the legacy ``engines/website_generator`` package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from engines.website_generation.constants.components import (
    CTA_PRIMARY_GOAL_MAX_REPETITIONS_PER_PAGE,
    MAX_SECTIONS_PER_BODY_DEFAULT,
)
from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.contracts.enums import RegionKind

# AES-WEB-002 §17.2: "Interleaved cap per page (constants, default 3)."
# Not yet centralized in constants/components.py; this delivery may modify
# only constants/gates.py, so the default lives here, cited to its source.
_DEFAULT_SPONSORED_PER_PAGE_CAP = 3

__all__ = [
    "CheckOutcome",
    "SyntheticInstance",
    "SyntheticPage",
    "SyntheticRenderedPage",
]


@dataclass(frozen=True)
class CheckOutcome:
    """The result of one gate-check function against one synthetic fixture.

    ``passed`` is the boolean verdict; ``details`` is a diagnostic string.
    A passing outcome MAY still carry an explanatory ``details`` string
    (e.g. "no violations found"); a failing outcome MUST name the specific
    violating value per AES-WEB-002 §21's diagnostic requirement.
    """

    passed: bool
    details: str = ""


@dataclass(frozen=True)
class SyntheticInstance:
    """A synthetic, gate-check-only stand-in for one bound component
    instance within a synthetic page tree.

    Not a production artifact. ``instance_path`` is a diagnostic identity
    string (e.g. ``"home#hero.search.directory-1"``), not a real
    content-derived hash (AES-WEB-002 §4.2 instance identity is a later
    wave's concern). ``definition`` is a real, frozen
    :class:`ComponentDefinition` so contract-level facts (props, slots,
    variants, capability contracts, lifecycle, compatibility) are checked
    against authority-shaped data; every other field is a hand-authored
    binding fact standing in for what the Component Engine would resolve.
    """

    instance_path: str
    definition: ComponentDefinition
    page_route: str = ""
    page_role: str = ""
    region: Optional[RegionKind] = None
    variant: str = ""
    requested_version: str = ""
    registry_known_ids: Tuple[str, ...] = ()
    compatibility_environment: Mapping[str, str] = field(default_factory=dict)
    bound_required_props: Mapping[str, str] = field(default_factory=dict)
    bound_optional_props: Mapping[str, str] = field(default_factory=dict)
    bound_required_slots: Mapping[str, Tuple[str, ...]] = field(
        default_factory=dict
    )
    bound_optional_slots: Mapping[str, Tuple[str, ...]] = field(
        default_factory=dict
    )
    # asset ref -> resolved AssetRole.value ("" means unresolved in the CAS)
    asset_ref_roles: Mapping[str, str] = field(default_factory=dict)
    route_refs: Tuple[str, ...] = ()
    # the subset of route_refs that resolve in the synthetic SiteArchitecture
    resolved_routes: Tuple[str, ...] = ()
    build_allows_deprecated: bool = False
    listing_kind: str = ""
    rank_position: Optional[int] = None
    rank_rationale_bound: bool = True
    evidence_ref: str = ""
    disclosure_visible: bool = False
    disclosure_semantic_attrs: Mapping[str, str] = field(default_factory=dict)
    verification_state: str = ""
    verification_badge_rendered: bool = False
    urgency_claim: bool = False
    urgency_offer_expiry: str = ""
    price_exact: bool = True
    price_disclaimer_bound: bool = False
    consent_prechecked_marketing: bool = False
    consent_equal_weight: bool = True
    cta_label_class: str = ""
    trust_adjacent: bool = False
    bound_field_count: int = 0
    conversion_hierarchy_rank: Optional[int] = None
    recipe_hierarchy_rank: Optional[int] = None
    page_sponsored_count: int = 0
    page_sponsored_cap: int = _DEFAULT_SPONSORED_PER_PAGE_CAP
    mobile_reorder_compliant: bool = True
    table_data_loss: bool = False
    children: Tuple["SyntheticInstance", ...] = ()


@dataclass(frozen=True)
class SyntheticPage:
    """A synthetic page: an ordered set of top-level region instances plus
    page-level composition facts, standing in for a ``LayoutPlan`` +
    ``ComponentManifest`` page entry. Used by composition-family checks
    that inspect cross-instance, whole-page facts (heading hierarchy,
    landmark hierarchy, CTA repetition, sticky-region count, section
    count, required-role components present).
    """

    route: str
    page_role: str = ""
    regions: Tuple["SyntheticInstance", ...] = ()
    required_role_components_present: bool = True
    section_count: int = 0
    section_ceiling: int = MAX_SECTIONS_PER_BODY_DEFAULT
    sticky_region_count: int = 0
    sticky_regions_overlap: bool = False
    heading_sequence: Tuple[int, ...] = ()
    landmark_roles: Tuple[str, ...] = ()
    unlabeled_nav_count: int = 0
    nested_interactive_controls: Tuple[str, ...] = ()
    cta_primary_weight_regions: Tuple[str, ...] = ()
    primary_goal_repetitions: int = 0
    primary_goal_repetition_ceiling: int = CTA_PRIMARY_GOAL_MAX_REPETITIONS_PER_PAGE


@dataclass(frozen=True)
class SyntheticRenderedPage:
    """A synthetic stand-in for a page's "rendered output" (§21 preamble).

    Hand-authored facts a real Renderer plus an HTML/CSS analysis pass
    would derive. Contrast ratios are recorded in hundredths (``450`` =
    4.50:1) to keep this fixture vocabulary integer-only, matching the
    canonical-serialization "no floats" doctrine even though these
    fixtures are never serialized or hashed.
    """

    route: str
    dom_ids: Tuple[str, ...] = ()
    heading_sequence: Tuple[int, ...] = ()
    landmark_roles: Tuple[str, ...] = ()
    named_nav_labels: Tuple[str, ...] = ()
    unlabeled_nav_count: int = 0
    nested_interactive_controls: Tuple[str, ...] = ()
    html_conformant: bool = True
    conformance_errors: Tuple[str, ...] = ()
    inline_script_count: int = 0
    unapproved_inline_style_count: int = 0
    escaped_probe_leaks: Tuple[str, ...] = ()
    external_request_hosts: Tuple[str, ...] = ()
    unresolved_asset_refs: Tuple[str, ...] = ()
    internal_metadata_markers: Tuple[str, ...] = ()
    unsafe_urls: Tuple[str, ...] = ()
    attribute_order_stable: bool = True
    class_names_stable: bool = True
    render_hash_a: str = "x"
    render_hash_b: str = "x"
    structured_data_fragments_well_formed: bool = True
    duplicate_entity_ids: Tuple[str, ...] = ()
    no_js_baseline_present: bool = True
    crawler_visible_text: str = ""
    user_visible_text: str = ""
    hidden_headings: Tuple[str, ...] = ()
    outbound_links: Mapping[str, str] = field(default_factory=dict)
    internal_links: Mapping[str, bool] = field(default_factory=dict)
    internal_link_count: int = 0
    internal_link_floor: int = 0
    internal_link_ceiling: int = 24
    duplicate_block_reuse_count: int = 0
    duplicate_block_reuse_ceiling: int = 1
    visible_nap: Tuple[str, str, str] = ("", "", "")
    schema_nap: Tuple[str, str, str] = ("", "", "")
    pagination_crawl_safe: bool = True
    breadcrumb_present_per_role: bool = True
    horizontal_overflow_at_320: bool = False
    reflow_safe_at_200pct: bool = True
    touch_targets_ge_44px_at_sm: bool = True
    contrast_ratio_hundredths: int = 450
    contrast_required_hundredths: int = 450
    focus_ring_wired: bool = True
    outline_none_without_replacement: bool = False
    focus_trap_valid: bool = True
    reduced_motion_unresolved_tokens: Tuple[str, ...] = ()
    live_region_declarations_valid: bool = True
    dialog_state_machine_valid: bool = True
    alt_texts: Mapping[str, str] = field(default_factory=dict)
    decorative_images: Tuple[str, ...] = ()
    alt_length_ceiling: int = 125
    skip_link_first_focusable: bool = True
    form_error_summary_present: bool = True
    form_inline_association_present: bool = True
    form_autocomplete_present: bool = True
    redundant_link_texts: Tuple[str, ...] = ()
    image_aspect_and_srcset_declared: bool = True
    sticky_bounds_declared: bool = True

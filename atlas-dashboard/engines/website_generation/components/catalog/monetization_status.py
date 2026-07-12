"""Wave 7 catalog — Monetization, Legal, and Status (AES-WEB-002H;
AES-WEB-002 §27.8).

The full eight-component §27.8 Wave 7 inventory: the four ``monetization.*``
components (``monetization.disclosure.advertising``,
``monetization.prompt.upgrade``, ``monetization.ribbon.sponsor``,
``monetization.section.premium-profile``), one ``commerce.*`` component
(``commerce.pricing.sponsorship``), two ``status.*`` components
(``status.listing.pending``, ``status.listing.unavailable``), and one
``legal.*`` component (``legal.statement.standard``). All eight are
declarative frozen data only — no markup, no emitters, no selection, no
behavior (§2.2). This is the eighth and final catalog wave, closing the
72-component MVP inventory (15+8+9+12+13+7+8=72, §27.8 closing line).

Scope boundary (operator-approved via the AES-WEB-002H architectural
preflight's Ambiguity Register, AMB-002H-01/02/03): this delivery is the
Wave 7 component catalog, registry updates, one small additive constants
table, fixtures, and tests *only*. It does **not**:

* build any ``rendering/`` or ``gates/`` package, real emitter functions, or
  executable gate-check logic, despite AES-WEB-002 §31's 002H phase text
  literally listing "emitters" among the wave's deliverables (AMB-002H-01).
  Continues the AES-WEB-002B/C/D/E/F/G precedent unchanged: no
  ``rendering/`` or ``gates/`` package exists anywhere in this repository
  yet — ``RenderingContract.emitter_key`` is declared metadata only. Every
  definition in this module registers ``PROPOSED``;
* author, integrate, modify, or remove ``_UNBUILT_FAMILY_SENTINEL`` gating
  from any ``*_RECIPE_SLOTS`` table in ``constants/components.py``
  (AMB-002H-02 — recipe integration for slots this wave's own components
  could now satisfy, e.g. ``BUSINESS_PROFILE_RECIPE_SLOTS``'s
  ``unavailable_state`` slot and ``VERIFICATION_RECIPE_SLOTS``'s pending-state
  slot, remains deferred to the later recipe-integration phase, per the
  unchanged AMB-002F-02/AMB-002G-02 precedent this module continues a third
  time);
* register any P3-deferred monetization component (native ad block,
  lead-purchase block, affiliate comparison, partner offer — §5.10, §34.2);
* touch ``constants/gates.py`` (no gate ID reservations have been added by
  any wave since 002A; 002I's exclusive scope);
* touch ``constants/analytics.py`` — the existing generic
  ``component_impression``/``cta_click`` event names are sufficient for
  every Wave 7 component; no new event name is declared.

Documented interpretive resolutions (consistent with the Wave 1-6 precedent
of recording, not guessing, when §27.8's table under-determines a detail):

* **Roles for ``legal.statement.standard``** ("dedicated legal pages, footer
  links" — no literal ``PageRole`` match): modeled as ``_ALL_ROLES``,
  matching ``legal.footer.directory``'s own Wave-2 precedent and §5.15's
  family-level "roles ALL" statement — a legal statement (privacy, terms,
  etc.) is reachable via footer links from every page role.
* **Roles for ``monetization.disclosure.advertising``** ("any page hosting
  paid units"): modeled as every ``PageRole`` *except* ``LEAD_GEN_LANDING``
  and ``VERIFICATION`` — the two roles §6.1's Monetization column marks "F"
  (forbidden) — rather than blanket ``_ALL_ROLES``, since claiming
  hosting-eligibility on an explicitly forbidden role would misstate the
  contract. Computed directly from the §6.1 matrix, not guessed.
* **Roles for ``monetization.ribbon.sponsor``** ("listing/zone contexts"):
  modeled as the exact union of ``listing.card.featured`` and
  ``listing.card.sponsored``'s own §27.5 declared roles (home, category,
  city, city-category, search-results) — the ribbon is the visible marker
  *for those same cards*, so it should support no broader a context than the
  cards it decorates. §6.1 also names a "clearly-separated featured block"
  on best-of, but ``listing.card.featured`` itself does not declare
  ``best-of`` as a supported role (§27.5) — including it here would paper
  over a Wave-4-level gap rather than honestly reflect the current catalog.
  Flagged as a known, carried limitation, not silently resolved.
* **Roles for ``monetization.prompt.upgrade``** ("claim, prof (owner
  contexts P3)"): modeled as ``CLAIM_LISTING`` only. The parenthetical
  marks the ``BUSINESS_PROFILE`` usage P3 (owner-session upsells require a
  notion of session/ownership this static-first MVP does not have); §34.2's
  general P3-exclusion policy is applied here at the per-role grain rather
  than including a flagged-P3 capability in the MVP contract.
* **``commerce.pricing.sponsorship`` pricing/disclaimer shape**: modeled as
  a ``PriceSpec`` content slot (cardinality ``one_to_n`` — "PriceSpec set")
  plus a required ``RichTextBlock`` disclaimer slot, directly implementing
  E4 ("non-exact PriceSpec renders bound disclaimer") — both are existing
  §8.4 typed content models, no new block type invented.
* **``legal.statement.standard`` semantic element**: modeled as ``ARTICLE``
  (a self-contained written statement), with ``seo_contract.heading_levels
  = (3, 4)`` reflecting §9.3's ownership split (section containers own H2;
  components own H3+ internally) — the same rule, applied directly, that
  ``content.description.business`` (Wave 4) and ``content.section.editorial``
  (Wave 6) were built against.
* **No ``conversion_contract`` on any Wave 7 component, including
  ``monetization.prompt.upgrade``**: §27.8's RP column is blank for every
  row (unlike, e.g., ``cta.claim.listing``'s explicit ``target_route``
  prop) — inventing a conversion goal and action target here would fabricate
  scope the authority table does not state. The upgrade/inquiry *action*
  affordances remain owned by Wave 5's ``cta.*`` family and Wave 4/5's
  existing conversion surfaces.
* **``MONETIZATION_DISCLOSURE_KINDS`` constants table**
  (``constants/components.py``): §17.1 requires disclosure text to come
  from "a constants-registered disclosure text set"; no such table existed
  before this wave. Added as a small, additive, wave-scoped table mirroring
  the ``CTA_GOAL_LABEL_CLASSES`` precedent (AES-WEB-002F; §16.2), not a new
  ``contracts/enums.py`` member (enum changes are a frozen-contract concern).

All eight definitions carry no ``directory_contract`` (none is
listing-kind-bearing — that remains Wave 4's domain) and no
``conversion_contract`` (see above). Only the four ``monetization.*``
definitions carry a non-null ``monetization_contract`` — the registry
enforces this for the ``MONETIZATION`` family and only that family (§15.2).
"""

from __future__ import annotations

from typing import Tuple

from engines.website_generation.contracts.components import (
    AccessibilityContract,
    ComponentDefinition,
    MonetizationContract,
    PropSpec,
    RenderingContract,
    SEOContract,
    SlotSpec,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
)
from engines.website_generation.constants.components import (
    MONETIZATION_DISCLOSURE_KIND_ADVERTISING,
    MONETIZATION_DISCLOSURE_KIND_PREMIUM,
    MONETIZATION_DISCLOSURE_KIND_SPONSORED,
    MONETIZATION_DISCLOSURE_KIND_UPGRADE,
)
from engines.website_generation.components.catalog.layout_atoms import (
    _COMPAT,
    _analytics,
    _fixtures,
)

# ---------------------------------------------------------------------------
# Shared role tuples (§27.8)
# ---------------------------------------------------------------------------

# §5.15 family-level "roles ALL" statement; matches legal.footer.directory's
# own Wave-2 _ALL_ROLES precedent.
_ALL_ROLES: Tuple[PageRole, ...] = tuple(PageRole)

# §6.1 Monetization column: every role except the two explicit "F" roles
# (lead-gen-landing, verification). Computed from the matrix, not guessed.
_MONETIZATION_DISCLOSURE_ADVERTISING_ROLES: Tuple[PageRole, ...] = tuple(
    role
    for role in PageRole
    if role not in (PageRole.LEAD_GEN_LANDING, PageRole.VERIFICATION)
)

# Exact union of listing.card.featured's and listing.card.sponsored's own
# §27.5 declared roles (AES-WEB-002E) — the ribbon decorates those same
# cards, no broader a context.
_MONETIZATION_RIBBON_SPONSOR_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.CITY_CATEGORY,
    PageRole.SEARCH_RESULTS,
)

_MONETIZATION_SECTION_PREMIUM_PROFILE_ROLES: Tuple[PageRole, ...] = (
    PageRole.BUSINESS_PROFILE,
)

# "claim" only — the BUSINESS_PROFILE ("owner contexts") usage is P3 per
# §27.8's own parenthetical; see module docstring.
_MONETIZATION_PROMPT_UPGRADE_ROLES: Tuple[PageRole, ...] = (
    PageRole.CLAIM_LISTING,
)

_COMMERCE_PRICING_SPONSORSHIP_ROLES: Tuple[PageRole, ...] = (
    PageRole.SPONSOR_PAGE,
)

_STATUS_LISTING_PENDING_ROLES: Tuple[PageRole, ...] = (
    PageRole.BUSINESS_PROFILE,
    PageRole.CLAIM_LISTING,
)

_STATUS_LISTING_UNAVAILABLE_ROLES: Tuple[PageRole, ...] = (
    PageRole.BUSINESS_PROFILE,
)


# ---------------------------------------------------------------------------
# monetization.* (§5.10, §27.8)
# ---------------------------------------------------------------------------

MONETIZATION_DISCLOSURE_ADVERTISING = ComponentDefinition(
    component_id="monetization.disclosure.advertising",
    component_family=ComponentFamily.MONETIZATION,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Advertising Disclosure",
    description=(
        "Visible advertising/sponsorship disclosure for any page hosting "
        "paid units (§17.1). Renders the registered disclosure text set — "
        "components never author disclosure copy inline (§8.4 "
        "DisclosureBlock: kind enum + RichText body from "
        "constants-registered templates)."
    ),
    commercial_purpose=CommercialPurpose.PREPARE_MONETIZATION,
    secondary_purposes=(CommercialPurpose.ESTABLISH_TRUST,),
    supported_page_roles=_MONETIZATION_DISCLOSURE_ADVERTISING_ROLES,
    required_props={
        "disclosure_kind": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=(MONETIZATION_DISCLOSURE_KIND_ADVERTISING,),
            default=MONETIZATION_DISCLOSURE_KIND_ADVERTISING,
            description="Disclosure kind, from the registered set (§17.1).",
        ),
    },
    required_content_slots={
        "disclosure": SlotSpec(
            block_type="DisclosureBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="The visible + semantic disclosure content (§17.1).",
        ),
    },
    supported_variants={
        "page-level": VariantSpec(display_name="Page-level"),
        "inline": VariantSpec(display_name="Inline"),
    },
    default_variant="page-level",
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.ANNOUNCEMENT, RegionKind.BODY),
    design_token_dependencies=(
        "typography.label.default",
        "color.text.muted",
        "color.surface.raised",
        "radius.control",
    ),
    accessibility_contract=AccessibilityContract(),
    monetization_contract=MonetizationContract(
        requires_visible_disclosure=True,
        disclosure_kind=MONETIZATION_DISCLOSURE_KIND_ADVERTISING,
    ),
    analytics_contract=_analytics("monetization.disclosure.advertising"),
    rendering_contract=RenderingContract(
        emitter_key="monetization.disclosure.advertising@1",
        class_prefix="ac-monetization",
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-001",),
    example_fixture_ids=_fixtures("monetization.disclosure.advertising")
    + (
        "fx-monetization.disclosure.advertising-sponsored",
        "fx-monetization.disclosure.advertising-malicious",
    ),
)

MONETIZATION_RIBBON_SPONSOR = ComponentDefinition(
    component_id="monetization.ribbon.sponsor",
    component_family=ComponentFamily.MONETIZATION,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Sponsor Ribbon",
    description=(
        "The visible paid marker for listing/zone contexts (§17.1) — a "
        "distinct surface token, not a style choice (§6.3 non-confusion "
        "rule: paid kinds MUST be visually distinguishable from organic at "
        "a glance)."
    ),
    commercial_purpose=CommercialPurpose.PREPARE_MONETIZATION,
    secondary_purposes=(CommercialPurpose.ESTABLISH_TRUST,),
    supported_page_roles=_MONETIZATION_RIBBON_SPONSOR_ROLES,
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="The visible paid marker label (e.g. 'Sponsored').",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.label.default",
        "color.surface.sponsored",
        "color.text.inverse",
    ),
    accessibility_contract=AccessibilityContract(),
    monetization_contract=MonetizationContract(
        requires_visible_disclosure=True,
        disclosure_kind=MONETIZATION_DISCLOSURE_KIND_SPONSORED,
    ),
    analytics_contract=_analytics("monetization.ribbon.sponsor"),
    rendering_contract=RenderingContract(
        emitter_key="monetization.ribbon.sponsor@1",
        class_prefix="ac-monetization",
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-001",),
    example_fixture_ids=_fixtures("monetization.ribbon.sponsor")
    + ("fx-monetization.ribbon.sponsor-sponsored",),
)

MONETIZATION_SECTION_PREMIUM_PROFILE = ComponentDefinition(
    component_id="monetization.section.premium-profile",
    component_family=ComponentFamily.MONETIZATION,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Premium Profile Section",
    description=(
        "Premium profile content, extending — never gating — core facts "
        "(§17.2: 'core facts never paywalled'). Renders only after the "
        "core-facts cluster (CG-COM-012)."
    ),
    commercial_purpose=CommercialPurpose.PREPARE_MONETIZATION,
    supported_page_roles=_MONETIZATION_SECTION_PREMIUM_PROFILE_ROLES,
    required_content_slots={
        "premium_blocks": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Premium profile content blocks.",
        ),
    },
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.surface.elevated",
        "spacing.section.medium",
    ),
    accessibility_contract=AccessibilityContract(),
    monetization_contract=MonetizationContract(
        requires_visible_disclosure=True,
        disclosure_kind=MONETIZATION_DISCLOSURE_KIND_PREMIUM,
    ),
    analytics_contract=_analytics("monetization.section.premium-profile"),
    rendering_contract=RenderingContract(
        emitter_key="monetization.section.premium-profile@1",
        class_prefix="ac-monetization",
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-012",),
    example_fixture_ids=_fixtures("monetization.section.premium-profile")
    + ("fx-monetization.section.premium-profile-sponsored",),
)

MONETIZATION_PROMPT_UPGRADE = ComponentDefinition(
    component_id="monetization.prompt.upgrade",
    component_family=ComponentFamily.MONETIZATION,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Upgrade Prompt",
    description=(
        "Claim-flow upgrade prompt. Never positioned as a requirement "
        "(E10 adjacency, §17.2: 'never disguised as verification "
        "requirements') — renders only after the claim form context, "
        "clearly optional and disclosed."
    ),
    commercial_purpose=CommercialPurpose.PREPARE_MONETIZATION,
    supported_page_roles=_MONETIZATION_PROMPT_UPGRADE_ROLES,
    required_content_slots={
        "offer": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Upgrade offer copy.",
        ),
        "disclosure": SlotSpec(
            block_type="DisclosureBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Mandatory disclosure that the upgrade is optional.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.surface.raised",
        "color.text.default",
        "radius.card",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(),
    monetization_contract=MonetizationContract(
        requires_visible_disclosure=True,
        disclosure_kind=MONETIZATION_DISCLOSURE_KIND_UPGRADE,
    ),
    analytics_contract=_analytics("monetization.prompt.upgrade"),
    rendering_contract=RenderingContract(
        emitter_key="monetization.prompt.upgrade@1",
        class_prefix="ac-monetization",
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-004",),
    example_fixture_ids=_fixtures("monetization.prompt.upgrade")
    + (
        "fx-monetization.prompt.upgrade-sponsored",
        "fx-monetization.prompt.upgrade-malicious",
    ),
)


# ---------------------------------------------------------------------------
# commerce.* (§5.12, §27.8)
# ---------------------------------------------------------------------------

COMMERCE_PRICING_SPONSORSHIP = ComponentDefinition(
    component_id="commerce.pricing.sponsorship",
    component_family=ComponentFamily.COMMERCE,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Sponsorship Pricing",
    description=(
        "Sponsorship pricing tiers for the sponsor-acquisition page. "
        "Non-exact PriceSpec kinds MUST render the bound disclaimer slot "
        "(E4, CG-COM-006) — hidden fees are prohibited by contract, not "
        "just policy."
    ),
    commercial_purpose=CommercialPurpose.PREPARE_MONETIZATION,
    secondary_purposes=(CommercialPurpose.REDUCE_UNCERTAINTY,),
    supported_page_roles=_COMMERCE_PRICING_SPONSORSHIP_ROLES,
    required_content_slots={
        "pricing": SlotSpec(
            block_type="PriceSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Sponsorship pricing tiers/options (§8.4 PriceSpec).",
        ),
        "disclaimer": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description=(
                "E4 disclaimer, mandatory for non-exact PriceSpec kinds."
            ),
        ),
    },
    supported_variants={
        "cards": VariantSpec(display_name="Cards"),
        "table": VariantSpec(display_name="Table"),
    },
    default_variant="cards",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.price.default",
        "typography.body.default",
        "spacing.stack.default",
        "radius.card",
        "color.border.default",
        "color.text.muted",
    ),
    accessibility_contract=AccessibilityContract(),
    analytics_contract=_analytics("commerce.pricing.sponsorship"),
    rendering_contract=RenderingContract(
        emitter_key="commerce.pricing.sponsorship@1", class_prefix="ac-commerce"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-006",),
    example_fixture_ids=_fixtures("commerce.pricing.sponsorship")
    + ("fx-commerce.pricing.sponsorship-sponsored",),
)


# ---------------------------------------------------------------------------
# status.* (§5.14, §27.8)
# ---------------------------------------------------------------------------

STATUS_LISTING_PENDING = ComponentDefinition(
    component_id="status.listing.pending",
    component_family=ComponentFamily.STATUS,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Pending Verification State",
    description=(
        "Pending-verification listing state. Never fakes VERIFIED (E10) — "
        "a verification badge renders only when content verification_state "
        "is actually VERIFIED (§6.3); this component is the honest interim "
        "state while it is not."
    ),
    commercial_purpose=CommercialPurpose.SYSTEM_STATUS,
    secondary_purposes=(CommercialPurpose.REDUCE_UNCERTAINTY,),
    supported_page_roles=_STATUS_LISTING_PENDING_ROLES,
    required_content_slots={
        "message": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Pending-state message.",
        ),
        "expectation_text": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="What the visitor should expect next.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.muted",
        "color.border.default",
    ),
    accessibility_contract=AccessibilityContract(live_region_role="status"),
    analytics_contract=_analytics("status.listing.pending"),
    rendering_contract=RenderingContract(
        emitter_key="status.listing.pending@1", class_prefix="ac-status"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-004",),
    example_fixture_ids=_fixtures("status.listing.pending"),
)

STATUS_LISTING_UNAVAILABLE = ComponentDefinition(
    component_id="status.listing.unavailable",
    component_family=ComponentFamily.STATUS,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Unavailable Listing State",
    description=(
        "Replaces the profile CTA cluster when a listing is unavailable, "
        "closed, stale, or archived (§6.1 'R unavailable/closed/pending "
        "states'; CG-STR-006). Recovery links are mandatory content, "
        "matching status.results.zero's Wave-3 precedent — every status "
        "component MUST bind at least one recovery action (§5.14)."
    ),
    commercial_purpose=CommercialPurpose.SYSTEM_STATUS,
    secondary_purposes=(CommercialPurpose.REDUCE_UNCERTAINTY,),
    supported_page_roles=_STATUS_LISTING_UNAVAILABLE_ROLES,
    required_props={
        "reason": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("unavailable", "closed", "stale", "archived"),
            description="Unavailability reason (§27.8).",
        ),
    },
    required_content_slots={
        "message": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Reason-specific explanation message.",
        ),
        "recovery_links": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Mandatory recovery links (category/city page, etc.).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.muted",
        "color.text.link",
        "color.border.default",
    ),
    accessibility_contract=AccessibilityContract(live_region_role="status"),
    seo_contract=SEOContract(link_kinds=("internal",)),
    analytics_contract=_analytics("status.listing.unavailable"),
    rendering_contract=RenderingContract(
        emitter_key="status.listing.unavailable@1", class_prefix="ac-status"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-STR-006",),
    example_fixture_ids=_fixtures("status.listing.unavailable"),
)


# ---------------------------------------------------------------------------
# legal.* (§5.15, §27.8)
# ---------------------------------------------------------------------------

LEGAL_STATEMENT_STANDARD = ComponentDefinition(
    component_id="legal.statement.standard",
    component_family=ComponentFamily.LEGAL,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Legal Statement",
    description=(
        "Kind-specific legal statement content (privacy, terms, "
        "accessibility, editorial standards, advertising, data-source) for "
        "dedicated legal pages and footer-linked destinations. Required "
        "sections per kind are content-rule validated, not contract-level "
        "(§27.8)."
    ),
    commercial_purpose=CommercialPurpose.SATISFY_LEGAL,
    secondary_purposes=(CommercialPurpose.ESTABLISH_TRUST,),
    supported_page_roles=_ALL_ROLES,
    required_props={
        "kind": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=(
                "privacy",
                "terms",
                "accessibility",
                "editorial-standards",
                "advertising",
                "data-source",
            ),
            description="Legal statement kind (§27.8).",
        ),
    },
    required_content_slots={
        "body": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Kind-specific legal statement content.",
        ),
    },
    semantic_element=SemanticElement.ARTICLE,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.heading.2",
        "typography.heading.3",
        "typography.body.default",
        "color.text.default",
        "color.text.link",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(),
    seo_contract=SEOContract(
        heading_levels=(3, 4), link_kinds=("internal",)
    ),
    analytics_contract=_analytics("legal.statement.standard"),
    rendering_contract=RenderingContract(
        emitter_key="legal.statement.standard@1", class_prefix="ac-legal"
    ),
    compatibility_range=_COMPAT,
    example_fixture_ids=_fixtures("legal.statement.standard")
    + ("fx-legal.statement.standard-malicious",),
)


# Wave 7 export — lexicographic by component_id (§15.2 ordering law). The
# full §27.8 eight-component inventory, closing the 72-component MVP.
WAVE7_COMPONENTS: Tuple[ComponentDefinition, ...] = (
    COMMERCE_PRICING_SPONSORSHIP,
    LEGAL_STATEMENT_STANDARD,
    MONETIZATION_DISCLOSURE_ADVERTISING,
    MONETIZATION_PROMPT_UPGRADE,
    MONETIZATION_RIBBON_SPONSOR,
    MONETIZATION_SECTION_PREMIUM_PROFILE,
    STATUS_LISTING_PENDING,
    STATUS_LISTING_UNAVAILABLE,
)

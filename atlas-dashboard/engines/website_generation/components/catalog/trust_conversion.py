"""Wave 5 catalog — Trust and Conversion (AES-WEB-002F; AES-WEB-002 §27.6).

The full thirteen-component §27.6 Wave 5 inventory: the three ``trust.*``
components, ``content.faq.standard``, the five ``form.*`` components, and
the four ``cta.*`` components. All thirteen are declarative frozen data
only — no markup, no emitters, no selection, no behavior (§2.2).

``content.faq.standard`` is a ``content``-family component (§5.8), not
``trust``/``cta``/``form``. It is registered here, in this wave's primary
catalog file, rather than deferred to ``seo_editorial.py`` (Wave 6, whose
own §29.1 file comment reads "``seo.* + content.*``"). This mirrors the
exact precedent AES-WEB-002E set for ``content.description.business`` in
``listings_profiles.py`` (also a cross-family component placed in its
*wave's* file, not its family's generic file) and is independently
confirmed by ``constants/components.py``'s own pre-existing comment on the
``faqs`` recipe slot: "``content.faq.standard`` is Wave 5" — written in
AES-WEB-002D, before this delivery existed. Operator-approved per the
AES-WEB-002F preflight's Ambiguity Register, AMB-002F-01.

Scope boundary (operator-approved, AMB-002F-02 / AMB-002F-03): this
delivery is the Wave 5 component catalog, registry updates, fixtures,
conversion metadata, and tests *only*. It does **not**:

* author ``LEAD_GEN_LANDING_RECIPE_SLOTS`` or ``CLAIM_LISTING_RECIPE_SLOTS``
  (left for the later recipe-integration phase);
* remove ``_UNBUILT_FAMILY_SENTINEL`` gating or otherwise modify
  ``HOME_RECIPE_SLOTS`` / ``CATEGORY_RECIPE_SLOTS`` /
  ``BUSINESS_PROFILE_RECIPE_SLOTS`` in ``constants/components.py``;
* extend ``listings_profiles.py``'s ``PROFILE_CONTACT_PANEL``
  ``allowed_child_components`` to reference the new ``cta.*`` family, even
  though that module's own docstring anticipated this at Wave 5 time.

Continues the AES-WEB-002B/C/D/E precedent unchanged: no ``rendering/`` or
``gates/`` package exists anywhere in this repository yet —
``RenderingContract.emitter_key`` is declared metadata only. Every
definition in this module registers ``PROPOSED`` — §23 promotion requires a
complete emitter and full §30.2 fixture set, neither of which this wave
builds.

Documented interpretive resolutions (consistent with the Wave 1-4
precedent of recording, not guessing, when §27.6's table under-determines
a detail):

* **"fields (≤N)" / "consent"** (``form.lead.quote``, ``form.claim.standard``,
  ``form.submission.listing``, ``form.correction.standard``,
  ``form.capture.newsletter``): §27.6 lists these under "RS" (required
  slots), but a slot binds one typed ``ContentPackage`` block (§8.2) and
  none of §8.4's typed content models is a heterogeneous, variable-count
  "form field" type. Wave 1 (§27.2) already built exactly the primitives
  this needs — ``atom.field.text``, ``atom.field.select``,
  ``atom.field.choice`` — as leaf components explicitly scoped to the
  ``forms`` page-role group. This module therefore models "fields" and
  "consent" as ``allowed_child_components`` referencing those three
  primitives (``atom.field.choice`` alone for "consent", per its own
  Wave-1 notes: "equal-weight consent"), not as content slots. This is the
  same class of resolution AES-WEB-002E used for ``profile.header.business``'s
  "badges" (resolved via an existing reference, not an invented slot) —
  composition over invented content-block types. Per-family friction
  ceilings (§16.5) are recorded as constants (below) for the eventual
  CG-COM-010 gate to enforce against bound child counts; they are not
  modeled as a contract-level max on ``allowed_child_components`` because
  §3's contract has no such per-composition numeric field.
* **"states"** (all five ``form.*`` components): modeled via
  ``ConversionContract.success_state`` / ``failure_state`` (§16.1, already
  present on the contract), not as content slots — those two fields exist
  on the contract precisely for this purpose.
* **"stat blocks with evidence_ref"** (``trust.statistics.strip``) and
  **"QA pairs"** (``content.faq.standard``): §8.4 names no dedicated
  statistics-with-evidence or question/answer block type. Modeled as
  ``block_type="StatBlock"`` and ``block_type="QAPair"`` respectively —
  new string labels, not one of §8.4's named types, chosen by analogy to
  the closest existing shape (``CredentialBlock``'s issuer+evidence_ref
  pattern for statistics; a simple repeated pair for FAQ) pending a future
  Content Engine authority ruling. ``SlotSpec.block_type`` is an
  unconstrained ``str`` at the contract level (no closed enum exists yet),
  so this does not violate any frozen contract.
* **"label"** (``cta.claim.listing``, ``cta.sponsor.inquiry``,
  ``cta.submit.listing``): unlike "fields", a CTA's label is a single,
  homogeneous piece of text — modeled directly as a ``RichTextBlock``
  content slot, matching ``atom.button.action``'s own Wave-1 "RS: label"
  shape, with no child-component indirection (nothing is gained by
  wrapping ``atom.button.action`` here; §5.7 describes a CTA as an action
  affordance in its own right, not a form).
* **"goal" prop** (``cta.sticky.mobile``): modeled as a ``STR_ENUM`` prop
  over the full closed ``ConversionGoal`` enum (§16.2) — "the page's
  primary goal" (§16.3) is resolved at selection/manifest-binding time,
  not fixed per component definition.
* **"target" prop** (``cta.sticky.mobile``): modeled as ``ROUTE_REF``.
  §8.1's closed ``PropType`` set has no prop type spanning both internal
  routes and ``tel:``/``mailto:`` targets (that duality is a *content*-slot
  concept, ``LinkSpec``, per §8.4) — a known, flagged limitation rather
  than a silent invention, matching the restraint AES-WEB-002E's
  ``profile.gallery.standard`` docstring showed when a gate ID had no
  concrete §21 entry to cite.
* **"footer contexts"** (``cta.sponsor.inquiry``): read as a *region*
  concern (§9.1 ``RegionKind.FOOTER`` is an allowed parent region,
  alongside ``BODY``), not an additional page-role — ``supported_page_roles``
  stays scoped to the single role (``sponsor-page``) §6.1's matrix actually
  names for the ``SPONSORSHIP_INQUIRY`` goal.
* **"listing contexts"** (``trust.reviews.summary``): read as the same
  role set ``listing.card.standard`` uses (§27.5) — home, category, city,
  city-category, search-results, collection — since that is where a
  listing's inline rating summary would render, plus ``business-profile``
  for the "prof" half of "prof, listing contexts".
* **Density variants** (``trust.reviews.list``'s "comfortable, compact"):
  §7.1 is explicit that density is "a shared axis, globally defined," not
  a per-component variant — matching ``listing.card.standard``'s own
  precedent (§27.5), this is modeled as a ``density`` prop, not a
  ``supported_variants`` entry, even though §27.6's table lists it under
  "Variants".

All thirteen definitions carry no ``directory_contract`` (none is
listing-kind-bearing — that is Wave 4's domain) and no
``monetization_contract`` (none is ``ComponentFamily.MONETIZATION`` — the
§15.2 registry-integrity rule requiring one applies only to that family;
``cta.sponsor.inquiry`` is monetization-*adjacent* but is a ``cta`` family
inquiry entry point, not a monetized surface itself).
"""

from __future__ import annotations

from typing import Tuple

from engines.website_generation.contracts.components import (
    AccessibilityContract,
    ComponentDefinition,
    ConversionContract,
    PropSpec,
    RenderingContract,
    SEOContract,
    SlotSpec,
    VariantSpec,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    ConversionGoal,
    LifecycleStatus,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
)
from engines.website_generation.components.catalog.layout_atoms import (
    _COMPAT,
    _FORM_ROLES,
    _analytics,
    _fixtures,
)

# ---------------------------------------------------------------------------
# Shared role tuples (§27.6)
# ---------------------------------------------------------------------------

_PROFILE_ONLY_ROLES: Tuple[PageRole, ...] = (PageRole.BUSINESS_PROFILE,)

# "listing contexts" (trust.reviews.summary) — the same role set
# listing.card.standard uses (§27.5), plus business-profile for "prof".
_LISTING_CONTEXT_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.CITY_CATEGORY,
    PageRole.SEARCH_RESULTS,
    PageRole.COLLECTION,
)
_TRUST_REVIEWS_SUMMARY_ROLES: Tuple[PageRole, ...] = (
    PageRole.BUSINESS_PROFILE,
) + _LISTING_CONTEXT_ROLES

_TRUST_STATISTICS_STRIP_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.SPONSOR_PAGE,
    PageRole.LEAD_GEN_LANDING,
)
_CONTENT_FAQ_STANDARD_ROLES: Tuple[PageRole, ...] = (
    PageRole.BUSINESS_PROFILE,
    PageRole.CATEGORY,
    PageRole.CITY,
    PageRole.EDITORIAL_GUIDE,
)
_FORM_LEAD_QUOTE_ROLES: Tuple[PageRole, ...] = (
    PageRole.LEAD_GEN_LANDING,
    PageRole.BUSINESS_PROFILE,
    PageRole.CITY_CATEGORY,
)
_FORM_CLAIM_STANDARD_ROLES: Tuple[PageRole, ...] = (PageRole.CLAIM_LISTING,)
_FORM_SUBMISSION_LISTING_ROLES: Tuple[PageRole, ...] = (PageRole.SUBMISSION,)
_FORM_CORRECTION_STANDARD_ROLES: Tuple[PageRole, ...] = (PageRole.CORRECTION,)
_FORM_CAPTURE_NEWSLETTER_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.EDITORIAL_GUIDE,
)
_CTA_CLAIM_LISTING_ROLES: Tuple[PageRole, ...] = (
    PageRole.BUSINESS_PROFILE,
    PageRole.HOME,
    PageRole.CATEGORY,
)
_CTA_STICKY_MOBILE_ROLES: Tuple[PageRole, ...] = (
    PageRole.BUSINESS_PROFILE,
    PageRole.LEAD_GEN_LANDING,
    PageRole.CITY_CATEGORY,
)
_CTA_SPONSOR_INQUIRY_ROLES: Tuple[PageRole, ...] = (PageRole.SPONSOR_PAGE,)
_CTA_SUBMIT_LISTING_ROLES: Tuple[PageRole, ...] = (
    PageRole.HOME,
    PageRole.CATEGORY,
    PageRole.SUBMISSION,
)

# "fields" / "consent" composition (see module docstring). Referenced by
# every form.* definition's allowed_child_components.
_FORM_FIELD_PRIMITIVES: Tuple[str, ...] = (
    "atom.field.choice",
    "atom.field.select",
    "atom.field.text",
)
_CONSENT_ONLY_PRIMITIVE: Tuple[str, ...] = ("atom.field.choice",)

# ConversionGoal's full closed set, as STR_ENUM values, for
# cta.sticky.mobile's "goal (page primary)" prop (§16.3).
_ALL_CONVERSION_GOALS: Tuple[str, ...] = tuple(g.value for g in ConversionGoal)


# ---------------------------------------------------------------------------
# trust.* (§5.6, §27.6)
# ---------------------------------------------------------------------------

TRUST_REVIEWS_SUMMARY = ComponentDefinition(
    component_id="trust.reviews.summary",
    component_family=ComponentFamily.TRUST,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Reviews Summary",
    description=(
        "Aggregate rating summary with a text equivalent (stars are "
        "aria-hidden decoration, §12.4); AggregateRating schema capability "
        "only when the bound RatingSummary is genuine (§13.2)."
    ),
    commercial_purpose=CommercialPurpose.ESTABLISH_TRUST,
    supported_page_roles=_TRUST_REVIEWS_SUMMARY_ROLES,
    required_content_slots={
        "rating_summary": SlotSpec(
            block_type="RatingSummary",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Count, mean, distribution (§8.4 RatingSummary).",
        ),
    },
    supported_variants={
        "inline": VariantSpec(display_name="Inline"),
        "block": VariantSpec(display_name="Block"),
    },
    default_variant="inline",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.default",
        "icon.size.sm",
        "spacing.stack.default",
    ),
    seo_contract=SEOContract(schema_fragments=("AggregateRating",)),
    analytics_contract=_analytics("trust.reviews.summary", "review_expand"),
    rendering_contract=RenderingContract(
        emitter_key="trust.reviews.summary@1", class_prefix="ac-trust"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-003", "CG-SEO-005"),
    example_fixture_ids=_fixtures("trust.reviews.summary"),
)

TRUST_REVIEWS_LIST = ComponentDefinition(
    component_id="trust.reviews.list",
    component_family=ComponentFamily.TRUST,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Reviews List",
    description=(
        "Individual reviews (§8.4 ReviewBlock), each carrying evidence_ref "
        "provenance — CG-COM-003 blocks any entry without one (E2). "
        "'comfortable/compact' (§27.6 Variants column) is modeled as the "
        "shared density prop (§7.1), not a variant — see module docstring."
    ),
    commercial_purpose=CommercialPurpose.ESTABLISH_TRUST,
    supported_page_roles=_PROFILE_ONLY_ROLES,
    required_props={
        "density": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=("comfortable", "compact"),
            description="The shared global density axis (§7.1) — not a variant.",
        ),
    },
    required_content_slots={
        "reviews": SlotSpec(
            block_type="ReviewBlock",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Author, rating, body, date, evidence_ref per review (§8.4).",
        ),
    },
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.body.default",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    analytics_contract=_analytics("trust.reviews.list", "review_expand"),
    rendering_contract=RenderingContract(
        emitter_key="trust.reviews.list@1", class_prefix="ac-trust"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-003",),
    example_fixture_ids=_fixtures("trust.reviews.list"),
)

TRUST_STATISTICS_STRIP = ComponentDefinition(
    component_id="trust.statistics.strip",
    component_family=ComponentFamily.TRUST,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Statistics Strip",
    description=(
        "Evidenced statistics (§8.4 has no dedicated stat-with-evidence "
        "type; modeled as block_type='StatBlock' by analogy to "
        "CredentialBlock — see module docstring). Not color-only (§12.4)."
    ),
    commercial_purpose=CommercialPurpose.ESTABLISH_TRUST,
    supported_page_roles=_TRUST_STATISTICS_STRIP_ROLES,
    required_content_slots={
        "statistics": SlotSpec(
            block_type="StatBlock",
            cardinality=SlotCardinality.ONE_TO_N,
            description="Evidenced statistics, each carrying evidence_ref (E2/E11 parity).",
        ),
    },
    supported_variants={
        "strip": VariantSpec(display_name="Strip"),
        "grid": VariantSpec(display_name="Grid"),
    },
    default_variant="strip",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.heading.2",
        "typography.body.default",
        "color.text.default",
        "grid.columns.3",
        "spacing.section.medium",
    ),
    analytics_contract=_analytics("trust.statistics.strip"),
    rendering_contract=RenderingContract(
        emitter_key="trust.statistics.strip@1", class_prefix="ac-trust"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-003",),
    example_fixture_ids=_fixtures("trust.statistics.strip"),
)


# ---------------------------------------------------------------------------
# content.faq.standard (§5.8, §27.6) — see module docstring for placement
# ---------------------------------------------------------------------------

CONTENT_FAQ_STANDARD = ComponentDefinition(
    component_id="content.faq.standard",
    component_family=ComponentFamily.CONTENT,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="FAQ",
    description=(
        "Question/answer pairs (§8.4 has no dedicated QA type; modeled as "
        "block_type='QAPair' — see module docstring). FAQPage schema "
        "capability only for visible content (§13.2, CG-SEO-006)."
    ),
    commercial_purpose=CommercialPurpose.REDUCE_UNCERTAINTY,
    supported_page_roles=_CONTENT_FAQ_STANDARD_ROLES,
    required_content_slots={
        "qa_pairs": SlotSpec(
            block_type="QAPair",
            cardinality=SlotCardinality.ONE_TO_N,
            max_count=12,
            description="Question/answer pairs, up to the §27.6 ceiling of 12.",
        ),
    },
    supported_variants={
        "accordion": VariantSpec(display_name="Accordion"),
        "open-list": VariantSpec(display_name="Open list"),
    },
    default_variant="accordion",
    semantic_element=SemanticElement.SECTION,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "typography.heading.3",
        "typography.body.default",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(
        # §12.6 Accordion row: buttons with aria-expanded + aria-controls;
        # panels labeled by headers; Tab mandatory.
        state_machine="accordion",
        keyboard_operable=True,
    ),
    seo_contract=SEOContract(
        schema_fragments=("FAQPage",), content_visibility="always-visible"
    ),
    analytics_contract=_analytics("content.faq.standard"),
    rendering_contract=RenderingContract(
        emitter_key="content.faq.standard@1", class_prefix="ac-content"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-002", "CG-SEO-006"),
    example_fixture_ids=_fixtures("content.faq.standard"),
)


# ---------------------------------------------------------------------------
# form.* (§5.13, §27.6) — "fields"/"consent"/"states" resolutions in the
# module docstring.
# ---------------------------------------------------------------------------

FORM_LEAD_QUOTE = ComponentDefinition(
    component_id="form.lead.quote",
    component_family=ComponentFamily.FORM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Lead/Quote Request Form",
    description=(
        "Quote/lead capture, friction-budgeted to <=6 fields (§16.5, "
        "CG-COM-010); mandatory lead-handling disclosure (§17.2)."
    ),
    commercial_purpose=CommercialPurpose.COLLECT_LEAD,
    supported_page_roles=_FORM_LEAD_QUOTE_ROLES,
    required_props={
        "action_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="BusinessSpec.form_endpoint-derived submission route (§5.13 MVP posture).",
        ),
    },
    required_content_slots={
        "disclosure": SlotSpec(
            block_type="DisclosureBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description='Mandatory "your request is sent to providers..." disclosure (§17.2).',
        ),
    },
    allowed_child_components=_FORM_FIELD_PRIMITIVES,
    semantic_element=SemanticElement.FORM,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.raised",
        "typography.body.default",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
        "radius.control",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.QUOTE_REQUEST,
        primary_action="submit_form",
        persuasion_role="close",
        urgency_policy="none",
        analytics_event="form_complete",
        repetition_limit_per_page=1,
        placement_regions=(RegionKind.BODY,),
        success_state="form_success",
        failure_state="form_error",
    ),
    analytics_contract=_analytics(
        "form.lead.quote", "form_start", "form_complete", "form_fail"
    ),
    rendering_contract=RenderingContract(
        emitter_key="form.lead.quote@1", class_prefix="ac-form"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-005", "CG-COM-010", "CG-A11Y-012"),
    example_fixture_ids=_fixtures("form.lead.quote"),
)

FORM_CLAIM_STANDARD = ComponentDefinition(
    component_id="form.claim.standard",
    component_family=ComponentFamily.FORM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Claim Listing Form",
    description=(
        "Listing claim intake, step one <=5 fields (§16.5); adjacent to "
        "the verification explanation (§26.10); never renders a "
        "verification badge itself (E10 stays owned by profile.header.business)."
    ),
    commercial_purpose=CommercialPurpose.ENCOURAGE_CLAIM,
    supported_page_roles=_FORM_CLAIM_STANDARD_ROLES,
    required_props={
        "listing_ref": PropSpec(
            prop_type=PropType.LISTING_REF,
            description="The listing being claimed.",
        ),
        "action_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="Claim-submission endpoint route.",
        ),
    },
    allowed_child_components=_FORM_FIELD_PRIMITIVES,
    semantic_element=SemanticElement.FORM,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.raised",
        "typography.body.default",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
        "radius.control",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.LISTING_CLAIM,
        primary_action="submit_form",
        persuasion_role="close",
        urgency_policy="none",
        analytics_event="claim_start",
        repetition_limit_per_page=1,
        placement_regions=(RegionKind.BODY,),
        success_state="form_success",
        failure_state="form_error",
    ),
    analytics_contract=_analytics(
        "form.claim.standard", "claim_start", "form_complete", "form_fail"
    ),
    rendering_contract=RenderingContract(
        emitter_key="form.claim.standard@1", class_prefix="ac-form"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-004", "CG-COM-010"),
    example_fixture_ids=_fixtures("form.claim.standard"),
)

FORM_SUBMISSION_LISTING = ComponentDefinition(
    component_id="form.submission.listing",
    component_family=ComponentFamily.FORM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Listing Submission Form",
    description=(
        "New-listing submission; the free path must render with equal "
        "visual weight to any paid fast-track option (E8/CG-COM-007) — "
        "the paid option itself is monetization.* (Wave 7), out of scope here."
    ),
    commercial_purpose=CommercialPurpose.ENCOURAGE_SUBMISSION,
    supported_page_roles=_FORM_SUBMISSION_LISTING_ROLES,
    required_props={
        "action_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="Submission endpoint route.",
        ),
    },
    required_content_slots={
        "standards_link": SlotSpec(
            block_type="LinkSpec",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Editorial standards link (§27.6 RS).",
        ),
    },
    allowed_child_components=_FORM_FIELD_PRIMITIVES,
    semantic_element=SemanticElement.FORM,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.raised",
        "typography.body.default",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
        "radius.control",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.LISTING_SUBMISSION,
        primary_action="submit_form",
        persuasion_role="close",
        urgency_policy="none",
        analytics_event="submission_start",
        repetition_limit_per_page=1,
        placement_regions=(RegionKind.BODY,),
        success_state="form_success",
        failure_state="form_error",
    ),
    analytics_contract=_analytics(
        "form.submission.listing", "submission_start", "form_complete", "form_fail"
    ),
    rendering_contract=RenderingContract(
        emitter_key="form.submission.listing@1", class_prefix="ac-form"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-007",),
    example_fixture_ids=_fixtures("form.submission.listing"),
)

FORM_CORRECTION_STANDARD = ComponentDefinition(
    component_id="form.correction.standard",
    component_family=ComponentFamily.FORM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Correction Request Form",
    description=(
        "Data-correction intake, <=5 fields (§16.5); no monetization of "
        "any kind on this role (§6.1) — carries no monetization contract."
    ),
    commercial_purpose=CommercialPurpose.REDUCE_UNCERTAINTY,
    supported_page_roles=_FORM_CORRECTION_STANDARD_ROLES,
    required_props={
        "listing_ref": PropSpec(
            prop_type=PropType.LISTING_REF,
            description="The listing the correction applies to.",
        ),
        "action_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="Correction-submission endpoint route.",
        ),
    },
    allowed_child_components=_FORM_FIELD_PRIMITIVES,
    semantic_element=SemanticElement.FORM,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.raised",
        "typography.body.default",
        "color.text.default",
        "color.border.default",
        "spacing.stack.default",
        "radius.control",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.CORRECTION_REQUEST,
        primary_action="submit_form",
        persuasion_role="close",
        urgency_policy="none",
        analytics_event="correction_start",
        repetition_limit_per_page=1,
        placement_regions=(RegionKind.BODY,),
        success_state="form_success",
        failure_state="form_error",
    ),
    analytics_contract=_analytics(
        "form.correction.standard", "correction_start", "form_complete", "form_fail"
    ),
    rendering_contract=RenderingContract(
        emitter_key="form.correction.standard@1", class_prefix="ac-form"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-A11Y-012",),
    example_fixture_ids=_fixtures("form.correction.standard"),
)

FORM_CAPTURE_NEWSLETTER = ComponentDefinition(
    component_id="form.capture.newsletter",
    component_family=ComponentFamily.FORM,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Newsletter Capture",
    description=(
        "<=2 fields (§16.5); consent MUST be unchecked by default (E8, "
        "CG-COM-007) — modeled via atom.field.choice, never a pre-checked "
        "prop (§8.1 has no BOOL default that could smuggle this in)."
    ),
    commercial_purpose=CommercialPurpose.COLLECT_LEAD,
    supported_page_roles=_FORM_CAPTURE_NEWSLETTER_ROLES,
    required_props={
        "action_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="Newsletter-signup endpoint route.",
        ),
    },
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="Signup prompt copy.",
        ),
    },
    allowed_child_components=_CONSENT_ONLY_PRIMITIVE,
    supported_variants={
        "inline": VariantSpec(display_name="Inline"),
        "band": VariantSpec(display_name="Band"),
    },
    default_variant="inline",
    semantic_element=SemanticElement.FORM,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.surface.raised",
        "typography.body.default",
        "color.text.default",
        "spacing.inline.default",
        "radius.control",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.NEWSLETTER_SIGNUP,
        primary_action="submit_form",
        persuasion_role="initiate",
        urgency_policy="none",
        analytics_event="form_complete",
        repetition_limit_per_page=1,
        placement_regions=(RegionKind.BODY,),
        success_state="form_success",
        failure_state="form_error",
    ),
    analytics_contract=_analytics(
        "form.capture.newsletter", "form_start", "form_complete", "form_fail"
    ),
    rendering_contract=RenderingContract(
        emitter_key="form.capture.newsletter@1", class_prefix="ac-form"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-007", "CG-COM-010"),
    example_fixture_ids=_fixtures("form.capture.newsletter"),
)


# ---------------------------------------------------------------------------
# cta.* (§5.7, §27.6)
# ---------------------------------------------------------------------------

CTA_CLAIM_LISTING = ComponentDefinition(
    component_id="cta.claim.listing",
    component_family=ComponentFamily.CTA,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Claim Listing CTA",
    description=(
        "Goal LISTING_CLAIM; label class constrained by the §16.2 "
        "CTA_GOAL_LABEL_CLASSES table (E9, CG-COM-008)."
    ),
    commercial_purpose=CommercialPurpose.ENCOURAGE_CLAIM,
    supported_page_roles=_CTA_CLAIM_LISTING_ROLES,
    required_props={
        "target_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="The claim-listing page route.",
        ),
    },
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="CTA label text (§16.2 label-class constrained).",
        ),
    },
    supported_variants={
        "band": VariantSpec(display_name="Band"),
        "inline": VariantSpec(display_name="Inline"),
    },
    default_variant="inline",
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.action.primary",
        "color.action.primary.hover",
        "typography.label.default",
        "radius.control",
        "focus.ring.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.LISTING_CLAIM,
        primary_action="navigate",
        persuasion_role="reinforce",
        urgency_policy="none",
        analytics_event="claim_start",
        repetition_limit_per_page=3,
        placement_regions=(RegionKind.BODY,),
    ),
    analytics_contract=_analytics("cta.claim.listing", "cta_click"),
    rendering_contract=RenderingContract(
        emitter_key="cta.claim.listing@1", class_prefix="ac-cta"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-008",),
    example_fixture_ids=_fixtures("cta.claim.listing"),
)

CTA_STICKY_MOBILE = ComponentDefinition(
    component_id="cta.sticky.mobile",
    component_family=ComponentFamily.CTA,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Sticky Mobile CTA",
    description=(
        "<md only, single instance, footer clearance (§11.5). Binds only "
        "the page's primary goal (§16.3) — 'goal' is a STR_ENUM prop over "
        "the full ConversionGoal set, resolved at manifest-binding time, "
        "not fixed per definition. 'target' is ROUTE_REF only — a known "
        "PropType-closed-set limitation for tel:/mailto: goals (see module "
        "docstring)."
    ),
    commercial_purpose=CommercialPurpose.IMPROVE_CONVERSION,
    supported_page_roles=_CTA_STICKY_MOBILE_ROLES,
    required_props={
        "goal": PropSpec(
            prop_type=PropType.STR_ENUM,
            enum_values=_ALL_CONVERSION_GOALS,
            description="The page's primary conversion_goal (§16.3), bound at selection time.",
        ),
        "target_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="Navigation target for the bound goal.",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.STICKY_MOBILE,),
    design_token_dependencies=(
        "color.action.primary",
        "typography.label.default",
        "shadow.sticky",
        "spacing.stack.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.QUOTE_REQUEST,
        primary_action="navigate",
        persuasion_role="close",
        urgency_policy="none",
        analytics_event="cta_click",
        repetition_limit_per_page=1,
        placement_regions=(RegionKind.STICKY_MOBILE,),
    ),
    analytics_contract=_analytics("cta.sticky.mobile", "cta_click"),
    rendering_contract=RenderingContract(
        emitter_key="cta.sticky.mobile@1", class_prefix="ac-cta"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-CMP-009", "CG-RSP-006"),
    example_fixture_ids=_fixtures("cta.sticky.mobile"),
)

CTA_SPONSOR_INQUIRY = ComponentDefinition(
    component_id="cta.sponsor.inquiry",
    component_family=ComponentFamily.CTA,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Sponsor Inquiry CTA",
    description=(
        "Goal SPONSORSHIP_INQUIRY (§6.1: sponsor-page only). 'footer "
        "contexts' (§27.6) is read as a region concern, not an additional "
        "page role — see module docstring."
    ),
    commercial_purpose=CommercialPurpose.ENCOURAGE_SPONSORSHIP,
    supported_page_roles=_CTA_SPONSOR_INQUIRY_ROLES,
    required_props={
        "target_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="The sponsor-inquiry form route.",
        ),
    },
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="CTA label text (§16.2 label-class constrained).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY, RegionKind.FOOTER),
    design_token_dependencies=(
        "color.action.primary",
        "color.action.primary.hover",
        "typography.label.default",
        "radius.control",
        "focus.ring.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.SPONSORSHIP_INQUIRY,
        primary_action="navigate",
        persuasion_role="close",
        urgency_policy="none",
        analytics_event="sponsor_inquiry_start",
        repetition_limit_per_page=3,
        placement_regions=(RegionKind.BODY, RegionKind.FOOTER),
    ),
    analytics_contract=_analytics(
        "cta.sponsor.inquiry", "cta_click", "sponsor_inquiry_start"
    ),
    rendering_contract=RenderingContract(
        emitter_key="cta.sponsor.inquiry@1", class_prefix="ac-cta"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-008",),
    example_fixture_ids=_fixtures("cta.sponsor.inquiry"),
)

CTA_SUBMIT_LISTING = ComponentDefinition(
    component_id="cta.submit.listing",
    component_family=ComponentFamily.CTA,
    component_version="1.0.0",
    lifecycle_status=LifecycleStatus.PROPOSED,
    display_name="Submit Listing CTA",
    description=(
        "Goal LISTING_SUBMISSION; label class constrained by the §16.2 "
        "CTA_GOAL_LABEL_CLASSES table (E9, CG-COM-008)."
    ),
    commercial_purpose=CommercialPurpose.ENCOURAGE_SUBMISSION,
    supported_page_roles=_CTA_SUBMIT_LISTING_ROLES,
    required_props={
        "target_route": PropSpec(
            prop_type=PropType.ROUTE_REF,
            description="The listing-submission page route.",
        ),
    },
    required_content_slots={
        "label": SlotSpec(
            block_type="RichTextBlock",
            cardinality=SlotCardinality.EXACTLY_ONE,
            description="CTA label text (§16.2 label-class constrained).",
        ),
    },
    semantic_element=SemanticElement.DIV,
    allowed_parent_regions=(RegionKind.BODY,),
    design_token_dependencies=(
        "color.action.primary",
        "color.action.primary.hover",
        "typography.label.default",
        "radius.control",
        "focus.ring.default",
    ),
    accessibility_contract=AccessibilityContract(keyboard_operable=True),
    conversion_contract=ConversionContract(
        conversion_goal=ConversionGoal.LISTING_SUBMISSION,
        primary_action="navigate",
        persuasion_role="reinforce",
        urgency_policy="none",
        analytics_event="submission_start",
        repetition_limit_per_page=3,
        placement_regions=(RegionKind.BODY,),
    ),
    analytics_contract=_analytics("cta.submit.listing", "cta_click"),
    rendering_contract=RenderingContract(
        emitter_key="cta.submit.listing@1", class_prefix="ac-cta"
    ),
    compatibility_range=_COMPAT,
    quality_gate_requirements=("CG-COM-008",),
    example_fixture_ids=_fixtures("cta.submit.listing"),
)


# Wave 5 export — lexicographic by component_id (§15.2 ordering law). The
# full §27.6 thirteen-component inventory.
WAVE5_COMPONENTS: Tuple[ComponentDefinition, ...] = (
    CONTENT_FAQ_STANDARD,
    CTA_CLAIM_LISTING,
    CTA_SPONSOR_INQUIRY,
    CTA_STICKY_MOBILE,
    CTA_SUBMIT_LISTING,
    FORM_CAPTURE_NEWSLETTER,
    FORM_CLAIM_STANDARD,
    FORM_CORRECTION_STANDARD,
    FORM_LEAD_QUOTE,
    FORM_SUBMISSION_LISTING,
    TRUST_REVIEWS_LIST,
    TRUST_REVIEWS_SUMMARY,
    TRUST_STATISTICS_STRIP,
)

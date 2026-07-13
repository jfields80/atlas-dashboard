"""Component-system constants (AES-WEB-002A; AES-WEB-002 §4, §7.3, §9.2, §22).

Constants only — no computation, no imports beyond the standard library
(dependency matrix, AES-WEB-001 §3.2). Every component-system magic number
lives here or does not exist.

Scope note: 002A owns the naming grammar, complexity budgets, composition
limits, and version constants that the registry needs to validate
definitions. The §3.2 selection scoring tables and CTA label/action table
support the selection and conversion waves (002D/002F) and are deferred
there, not authored in 002A. The selection scoring tables landed in 002D;
the CTA label/action-class table and the §16.5 friction-budget constants
land in 002F; the §5.9 SEO local-links block ceilings and the five
secondary-role recipe tables (editorial-guide, collection, service-area,
verification, regional-hub — closing §26's bounded deferral, §34.2) land in
002G, at the end of this module. Per the AES-WEB-002G preflight's
Ambiguity Register (AMB-002G-02, operator-approved): 002G does not modify
HOME_RECIPE_SLOTS, CATEGORY_RECIPE_SLOTS, or BUSINESS_PROFILE_RECIPE_SLOTS
above, and does not remove any _UNBUILT_FAMILY_SENTINEL entry from them —
that integration remains deferred to the later recipe-integration phase.
"""

# ---------------------------------------------------------------------------
# Component identity / naming grammar (AES-WEB-002 §4.1, §4.3)
# ---------------------------------------------------------------------------

# component_id := family "." pattern "." intent — exactly three segments.
COMPONENT_ID_SEGMENT_COUNT = 3
COMPONENT_ID_SEGMENT_MAX_LENGTH = 24
COMPONENT_ID_MAX_LENGTH = 64
# Each segment is [a-z][a-z0-9-]* (validated by the registry).
COMPONENT_ID_SEGMENT_PATTERN = r"^[a-z][a-z0-9-]*$"
COMPONENT_ID_SEPARATOR = "."

# Variant delimiter (§4.2): listing.card.standard::compact.
VARIANT_DELIMITER = "::"

# Namespaces (§4.3).
EXPERIMENTAL_PREFIX = "x."
EXTENSION_PREFIX = "ext."
PROHIBITED_SITE_PREFIX = "site."

# Reserved words that may not appear as a family segment (§4.3).
RESERVED_FAMILY_WORDS = ("atlas", "internal", "test")

# ---------------------------------------------------------------------------
# Complexity budget (AES-WEB-002 §7.3 — BLOCKING at registration)
# ---------------------------------------------------------------------------

MAX_REQUIRED_PROPS = 6
MAX_OPTIONAL_PROPS = 10
MAX_VARIANTS = 6  # excludes the global density axis
MAX_BOOL_PROPS = 2
# complexity score = required_props + 0.5*optional_props + 2*variants.
MAX_COMPLEXITY_SCORE = 20
# Weight numerator/denominator kept integer to avoid float arithmetic:
# score*2 = 2*required + optional + 4*variants  <=  MAX_COMPLEXITY_SCORE*2.
COMPLEXITY_SCORE_DOUBLED_CEILING = MAX_COMPLEXITY_SCORE * 2

# ---------------------------------------------------------------------------
# Composition limits (AES-WEB-002 §9.2)
# ---------------------------------------------------------------------------

MAX_COMPOSITION_DEPTH = 6
MAX_SECTIONS_PER_BODY_DEFAULT = 12

# ---------------------------------------------------------------------------
# Footer link ceiling (AES-WEB-002 §5.15; Wave 2, AES-WEB-002C)
# ---------------------------------------------------------------------------

# §5.15: footer link farms are forbidden — "footer SEO links capped at
# constants ceiling, default 40". Declared here (name + default only);
# enforcement is gate work (CG-CMP-006 family, AES-WEB-002I).
FOOTER_SEO_LINK_CEILING = 40

# ---------------------------------------------------------------------------
# Semantic version rule (semver, AES-WEB-002 §22)
# ---------------------------------------------------------------------------

SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"

# Component-system version axes themselves live in ``contracts/versions.py``
# (AES-WEB-002 §22.1) — the ``contracts/`` layer owns versions and may not
# import ``constants/``. Compatibility-range axes (declarative data the
# registry validates against) live here.

# Compatibility-range axes a definition may pin (AES-WEB-002 §22.1).
COMPATIBILITY_AXES = (
    "renderer",
    "token_schema",
    "registry_schema",
    "analytics_contract",
    "accessibility_contract",
    "seo_contract",
    "responsive_contract",
)

# ---------------------------------------------------------------------------
# Selection pipeline (AES-WEB-002D; AES-WEB-002 §14.2)
# ---------------------------------------------------------------------------

# Filter-stage identifiers recorded on an eliminated SelectionCandidate
# (§14.3 "eliminated_by"). Steps 6-9 (scoring, tie-breaking, variant
# selection, fallback/failure) do not eliminate a candidate from the pool,
# so they have no filter identifier here.
SELECTION_FILTER_CANDIDATE_ROLE = "candidate_role"
SELECTION_FILTER_COMPATIBILITY = "compatibility"
SELECTION_FILTER_LIFECYCLE = "lifecycle"
SELECTION_FILTER_REQUIRED_CAPABILITY = "required_capability"
SELECTION_FILTER_COMMERCIAL_PURPOSE = "commercial_purpose"

# Additive integer scoring factors (§14.2 step 6 — "stable scoring... static
# tables... integer arithmetic only"). SELECTION_SCORE_BRAND_PROFILE_AFFINITY
# is reserved but never awarded in AES-WEB-002D: the registry declares no
# brand-profile-tag metadata on ComponentDefinition, so that stage is an
# explicit, documented no-op (decision: do not add capability/brand-affinity
# metadata fields) rather than an invented heuristic.
SELECTION_SCORE_PREFERRED_LIFECYCLE = 100
SELECTION_SCORE_EXACT_INTENT_MATCH = 50
SELECTION_SCORE_MONETIZATION_ALIGNMENT = 30
SELECTION_SCORE_BRAND_PROFILE_AFFINITY = 20
SELECTION_SCORE_OPTIONAL_ASSET_AVAILABILITY = 10

# Score-component factor labels (SelectionScoreComponent.factor, §14.3).
SELECTION_FACTOR_PREFERRED_LIFECYCLE = "preferred_lifecycle"
SELECTION_FACTOR_EXACT_INTENT_MATCH = "exact_intent_match"
SELECTION_FACTOR_MONETIZATION_ALIGNMENT = "monetization_alignment"
SELECTION_FACTOR_OPTIONAL_ASSET_AVAILABILITY = "optional_asset_availability"

# Deterministic tie-break basis label (§14.2 step 7), recorded verbatim on
# SlotSelectionTrace.tie_break_basis whenever any candidate survives to
# ranking. The leading non_fallback_first key is the audit-W-2 remediation:
# a declared fallback (§14.2 step 9) is a last resort, ranked after every
# non-fallback survivor regardless of score; the remaining keys are the
# §14.2 order within each class.
SELECTION_TIE_BREAK_BASIS = (
    "non_fallback_first,score_desc,component_id_asc,version_desc"
)

# Trace size bound (§14.3 — "beyond the top 5 named candidates per slot,
# eliminations compress to per-filter counts").
SELECTION_TRACE_NAMED_CANDIDATE_LIMIT = 5

# Implementation-phase lifecycle build flags (§14.1 "implementation-phase
# capability flags from constants"). No component in the registry is ACTIVE
# or PREFERRED yet (§23 promotion requires emitters + full fixtures, later
# waves), so PROPOSED participation is explicitly enabled for deterministic
# composition during this phase — a build-flag toggle, never a change to any
# component's registered lifecycle_status or to certification semantics
# (§23 promotion still requires operator approval, recorded on the registry
# entry, regardless of this flag).
DEFAULT_LIFECYCLE_ALLOW_PROPOSED = True
DEFAULT_LIFECYCLE_ALLOW_EXPERIMENTAL = False
DEFAULT_LIFECYCLE_ALLOW_DEPRECATED = False

# Default concrete versions the Component Engine (AES-WEB-002J.6) evaluates
# each definition's compatibility_range against (§14.2 step 2 -- "against
# renderer / token-schema / registry versions"). Every catalog definition
# pins these three axes at ">=1.0.0,<2.0.0"; the Phase-1 baseline is 1.0.0
# on all three. registry_schema tracks the component-contract schema version
# (COMPONENT_CONTRACT_SCHEMA_VERSION in contracts/versions.py, currently
# "1.0.0"); it is duplicated here as a literal because constants/ may not
# import contracts/ (the import-audit matrix, §3.2). The renderer and
# token-schema axes are not versioned anywhere concrete yet (rendering/ is a
# later phase, AES-WEB-001 §5.7), so they carry the 1.0.0 baseline.
DEFAULT_COMPATIBILITY_VERSIONS = {
    "renderer": "1.0.0",
    "token_schema": "1.0.0",
    "registry_schema": "1.0.0",
}

# ---------------------------------------------------------------------------
# Recipe slot tables (AES-WEB-002D; AES-WEB-002 §26.1, §26.2)
# ---------------------------------------------------------------------------
#
# Declarative default component sequences per PageRole (§26): slot purposes,
# not hard component pins — selection fills them. Only the home (§26.1) and
# category (§26.2) recipes are authored here, matching the AES-WEB-002D
# acceptance criterion ("home + category fixture pages compose from recipes
# §26.1-26.2 with real selection"); the remaining sixteen page-role recipes
# require components from later waves and are out of this wave's scope.
#
# Each slot is a plain dict (constants hold data only, never computation):
#   slot_id                  -- stable slot identifier within the recipe
#   page_role                -- PageRole.value the recipe composes for
#   purpose                  -- CommercialPurpose.value the slot declares
#                                (§14.2 step 5), or "" for unconstrained
#   required_region          -- RegionKind.value the candidate must declare
#                                in allowed_parent_regions, or "" for none
#   required_prop_names      -- prop dict keys (required or optional) the
#                                candidate must declare (§14.2 step 1's
#                                slot-signature check — see selector.py's
#                                SlotSelectionRequest docstring for why
#                                purpose alone under-determines many slots)
#   required_slot_names      -- content-slot dict keys (required or
#                                optional) the candidate must declare
#   monetization_eligible     -- bool; §14.2 step 6 monetization-alignment
#                                scoring input
#   fallback_component_id    -- the slot's guaranteed-satisfiable Wave 1/2
#                                fallback (§14.2 step 9), or "" when the
#                                slot's real candidate is itself a Wave <=3
#                                component (no fallback needed in this
#                                registry state)
#   required                 -- bool; §26 "any optional slot with no
#                                eligible component is dropped and traced;
#                                any required slot failure is
#                                ComponentResolutionError"
#
# Slots for component families not yet registered (monetization.*, trust.*,
# content.*, cta.*, form.*, seo.*local-links — Waves 5-7) declare a
# sentinel required_slot_names value that no real definition will ever
# declare, so they deterministically resolve to nothing (correctly dropped
# as optional) rather than risking an accidental purpose/role match against
# an unrelated Wave 1-3 component. AES-WEB-002E's business-profile recipe
# (below) reuses the same sentinel for its own not-yet-built dependencies
# (trust.*, cta.*, form.*, status.* are still Wave 5-7; "services offered"
# has no dedicated §27.5 component in Wave 4 either).
_UNBUILT_FAMILY_SENTINEL = ("__unbuilt_family_slot__",)

HOME_RECIPE_SLOTS = (
    {
        "slot_id": "utility_bar",
        "page_role": "home",
        "purpose": "ORIENT",
        "required_region": "ANNOUNCEMENT",
        "required_prop_names": (),
        "required_slot_names": ("message",),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.1 "(O)"
    },
    {
        "slot_id": "hero",
        "page_role": "home",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.1 "R hero.search.directory"
    },
    {
        "slot_id": "categories_grid",
        "page_role": "home",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("category_tiles",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.grid.standard",
        "required": True,  # §26.1 "R category discovery grid"
    },
    {
        "slot_id": "locations_grid",
        "page_role": "home",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("location_tiles",),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.1 "location discovery grid" (§6.1: REC)
    },
    {
        "slot_id": "featured_zone",
        "page_role": "home",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": True,
        "fallback_component_id": "",
        "required": False,  # §26.1 "(O, disclosed)" — monetization.* is Wave 7
    },
    {
        "slot_id": "trust_strip",
        "page_role": "home",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "REC value/trust strip" — trust.* is Wave 5
    },
    {
        "slot_id": "editorial_resources",
        "page_role": "home",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.1 "(O)" — content.* is Wave 6
    },
    {
        "slot_id": "claim_cta_band",
        "page_role": "home",
        "purpose": "ENCOURAGE_CLAIM",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.1 "claim-your-listing CTA band" — cta.* is Wave 5
    },
    {
        "slot_id": "newsletter_capture",
        "page_role": "home",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.1 "(O)" — form.capture.newsletter is Wave 5
    },
)

CATEGORY_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "category",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.2 "Compact category hero"
    },
    {
        "slot_id": "filters",
        "page_role": "category",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        "required_prop_names": ("facet_set_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.2 "filter links"
    },
    {
        "slot_id": "sort",
        "page_role": "category",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        "required_prop_names": ("sort_options_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.2 "+ sort"
    },
    {
        "slot_id": "results_summary",
        "page_role": "category",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("summary_text",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.2 "+ results summary"
    },
    {
        "slot_id": "listing_cards",
        "page_role": "category",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        # "density" (§7.1's shared density axis) is declared only by
        # listing.card.standard among the AES-WEB-002E listing.* siblings
        # (§27.5's RP column lists it only for that row) — required here so
        # this organic-default slot resolves to the ORGANIC card, never to
        # listing.card.featured/sponsored (which also satisfy "cat" +
        # EXPOSE_INVENTORY + listing_ref once Wave 4 registers them).
        "required_prop_names": ("listing_ref", "density"),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §26.2 "listing cards (paginated)"
    },
    {
        "slot_id": "pagination",
        "page_role": "category",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        "required_prop_names": ("page_context",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": True,  # §26.2 "(paginated)"; nav.pagination.standard is Wave 2
    },
    {
        "slot_id": "related_categories_cities",
        "page_role": "category",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.2 "related categories" / "top cities" — seo.* is Wave 6
    },
    {
        "slot_id": "claim_cta_band",
        "page_role": "category",
        "purpose": "ENCOURAGE_CLAIM",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.2 "claim CTA band" — cta.* is Wave 5
    },
    {
        "slot_id": "zero_results",
        "page_role": "category",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("message", "recovery_links"),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": True,  # §26.2 "zero-results state mandatory"
    },
)

# ---------------------------------------------------------------------------
# Recipe slot table (AES-WEB-002E; AES-WEB-002 §26.6)
# ---------------------------------------------------------------------------
#
# The business-profile recipe (§26.6's sequence: profile header -> contact
# panel -> description -> services -> hours -> service areas -> gallery (O)
# -> credentials (O) -> reviews (O) -> FAQs (O) -> map + directions ->
# related listings (REC) -> claim CTA (O) -> correction link (O)), encoded
# in the same slot-dict shape as HOME_RECIPE_SLOTS/CATEGORY_RECIPE_SLOTS.
# §26.6 was already fully specified in prose by AES-WEB-002; only this
# data-table encoding was outstanding (AES-WEB-002D authored only the home
# and category tables, matching its own acceptance criterion). Slots needing
# trust.*/cta.*/form.*/status.* components (reviews, FAQs, claim CTA,
# correction link, unavailable/closed/pending states) stay
# _UNBUILT_FAMILY_SENTINEL-gated exactly as HOME_RECIPE_SLOTS already does
# for its own Wave 5-7 dependencies — those families are not authorized
# before their own waves. "Services offered" has no dedicated component in
# the §27.5 Wave 4 inventory at all (it is not one of the twelve listing/
# profile IDs), so it is sentinel-gated for the same reason, not because it
# belongs to a later wave specifically.
BUSINESS_PROFILE_RECIPE_SLOTS = (
    {
        "slot_id": "profile_header",
        "page_role": "business-profile",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "HERO",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": ("name",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.6 "Profile header" — replaces hero (§6.1)
    },
    {
        "slot_id": "contact_panel",
        "page_role": "business-profile",
        "purpose": "DRIVE_CALL",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("contact_info",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §26.6 "contact panel"
    },
    {
        "slot_id": "description",
        "page_role": "business-profile",
        "purpose": "REDUCE_UNCERTAINTY",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("description",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.6 "description"
    },
    {
        "slot_id": "services",
        "page_role": "business-profile",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "services" — no dedicated §27.5 component
    },
    {
        "slot_id": "hours",
        "page_role": "business-profile",
        "purpose": "REDUCE_UNCERTAINTY",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("hours",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.6 "hours"
    },
    {
        "slot_id": "service_areas",
        "page_role": "business-profile",
        "purpose": "SUPPORT_LOCAL_SEO",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("area_links",),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "service areas" (not marked "(O)" but not
                             # every business has a distinct service area)
    },
    {
        "slot_id": "gallery",
        "page_role": "business-profile",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("images",),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "gallery (O)"
    },
    {
        "slot_id": "credentials",
        "page_role": "business-profile",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("credentials",),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "credentials (O)"
    },
    {
        "slot_id": "reviews",
        "page_role": "business-profile",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "reviews (summary + list)" — trust.* is Wave 5
    },
    {
        "slot_id": "faqs",
        "page_role": "business-profile",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "FAQs (O)" — content.faq.standard is Wave 5
    },
    {
        "slot_id": "map_directions",
        "page_role": "business-profile",
        "purpose": "REDUCE_UNCERTAINTY",
        "required_region": "",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": ("location", "directions_text"),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.6 "map + directions"
    },
    {
        "slot_id": "related_listings",
        "page_role": "business-profile",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": False,  # §6.1 "REC related listings"
    },
    {
        "slot_id": "claim_cta_band",
        "page_role": "business-profile",
        "purpose": "ENCOURAGE_CLAIM",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "claim CTA (if unclaimed)" — cta.* is Wave 5
    },
    {
        "slot_id": "correction_link",
        "page_role": "business-profile",
        # AES-WEB-002J.6 data-defect fix: this field was "CORRECTION_REQUEST",
        # which is a ConversionGoal (§16.2), not a CommercialPurpose -- the
        # only such mismatch across all eighteen recipe tables. The recipe
        # "purpose" field is a CommercialPurpose (§14.2 step 5), so the value
        # was invalid and raised on enum coercion the moment a real consumer
        # (the Component Engine) resolved the business-profile recipe. Set to
        # REDUCE_UNCERTAINTY, matching the profile family's declared purpose
        # (§5.5) and the correction recipe's own correction_form slot. The
        # slot is optional and carries the unbuilt-family sentinel (form.* is
        # Wave 5+), so it drops regardless of purpose -- this correction is
        # behavior-preserving for selection.
        "purpose": "REDUCE_UNCERTAINTY",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "correction link" — form.* is Wave 5
    },
    {
        "slot_id": "unavailable_state",
        "page_role": "business-profile",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.6 "unavailable/closed/pending variants" —
                             # status.listing.* is Wave 7
    },
)

# ---------------------------------------------------------------------------
# CTA label/action-class table (AES-WEB-002F; AES-WEB-002 §16.2, E9)
# ---------------------------------------------------------------------------
#
# §16.2: "Each goal maps in constants/components.py to: permitted CTA label
# classes (E9 enforcement table), permitted action target types (tel:,
# mailto:, route, external URL + rel policy), and its analytics event name."
#
# Scoped to the six ConversionGoal values Wave 5's cta.*/form.* components
# actually declare (constants hold data only; extending to further goals is
# additive, registry-minor work for whichever later wave needs them, per
# §22.2). Keyed by ConversionGoal.value (plain str, since constants/ may not
# import contracts/ — AES-WEB-001 §3.2).
#
# Label classes are controlled-vocabulary tags, not literal marketing copy —
# copy itself is a Content Engine / ContentPackage concern (§8.4
# RichTextBlock), never registry or constants data (§3.1 ownership map:
# "Text/media content" belongs to ContentPackage, never registry/constants).
CTA_GOAL_LABEL_CLASSES = {
    "LISTING_CLAIM": ("claim",),
    "QUOTE_REQUEST": ("quote", "request"),
    "LISTING_SUBMISSION": ("submit", "add-listing"),
    "CORRECTION_REQUEST": ("correct", "suggest-edit"),
    "NEWSLETTER_SIGNUP": ("subscribe", "signup"),
    "SPONSORSHIP_INQUIRY": ("inquire", "sponsor"),
}

# Every Wave 5 conversion-bearing component targets an internal route; none
# is tel:/mailto: (that is profile.contact.panel's domain, Wave 4, §27.5).
CTA_GOAL_ACTION_TARGET_TYPES = {
    "LISTING_CLAIM": ("route",),
    "QUOTE_REQUEST": ("route",),
    "LISTING_SUBMISSION": ("route",),
    "CORRECTION_REQUEST": ("route",),
    "NEWSLETTER_SIGNUP": ("route",),
    "SPONSORSHIP_INQUIRY": ("route",),
}

# §18.2's registered event names (constants/analytics.py), bound per goal.
CTA_GOAL_ANALYTICS_EVENT = {
    "LISTING_CLAIM": "claim_start",
    "QUOTE_REQUEST": "form_start",
    "LISTING_SUBMISSION": "submission_start",
    "CORRECTION_REQUEST": "correction_start",
    "NEWSLETTER_SIGNUP": "form_start",
    "SPONSORSHIP_INQUIRY": "sponsor_inquiry_start",
}

# §16.3: "the page's primary conversion_goal ... may repeat at most 3 times
# per page (hero/inline/sticky-or-footer)."
CTA_PRIMARY_GOAL_MAX_REPETITIONS_PER_PAGE = 3

# ---------------------------------------------------------------------------
# Form friction budgets (AES-WEB-002F; AES-WEB-002 §16.5, gate CG-COM-010 W)
# ---------------------------------------------------------------------------
#
# "Quote/lead <= 6 fields; newsletter <= 2; claim step one <= 5;
# correction <= 5; sponsor inquiry <= 6. Required-field count <= 4 on any
# MVP form." Declared here as data (name + default only, per §25's closing
# rule); enforcement is gate work (CG-COM-010, WARNING severity, AES-WEB-002I).
FORM_FRICTION_BUDGET_QUOTE_LEAD_MAX_FIELDS = 6
FORM_FRICTION_BUDGET_NEWSLETTER_MAX_FIELDS = 2
FORM_FRICTION_BUDGET_CLAIM_STEP_ONE_MAX_FIELDS = 5
FORM_FRICTION_BUDGET_CORRECTION_MAX_FIELDS = 5
FORM_FRICTION_BUDGET_SPONSOR_INQUIRY_MAX_FIELDS = 6
FORM_FRICTION_BUDGET_MAX_REQUIRED_FIELDS = 4

# ---------------------------------------------------------------------------
# SEO local-links block ceilings (AES-WEB-002G; AES-WEB-002 §5.9, §9.2)
# ---------------------------------------------------------------------------
#
# §5.9: "link stuffing beyond constants-declared per-block ceilings
# (default: 24 links per block, <=2 blocks per page)." Declared here as
# data (name + default only, per §25's closing rule); enforcement is gate
# work (CG-SEO-004, AES-WEB-002I). SEO_LOCAL_LINKS_MAX_PER_BLOCK is consumed
# directly by both seo.local-links.* components' slot ``max_count``
# (catalog/seo_editorial.py); SEO_LOCAL_LINKS_MAX_BLOCKS_PER_PAGE is a
# page-level/recipe-level ceiling with no single-component home (mirrors
# CTA_PRIMARY_GOAL_MAX_REPETITIONS_PER_PAGE's page-level-constant pattern
# above), declared here for the eventual gate/recipe consumer.
SEO_LOCAL_LINKS_MAX_PER_BLOCK = 24
SEO_LOCAL_LINKS_MAX_BLOCKS_PER_PAGE = 2

# ---------------------------------------------------------------------------
# Secondary recipe slot tables (AES-WEB-002G; AES-WEB-002 §6.1, §26 closing
# note, §34.2 bounded deferral)
# ---------------------------------------------------------------------------
#
# §26's closing note: "(editorial-guide, collection, service-area,
# verification, regional-hub recipes derive from §6.1 rows using the same
# frame; their full recipe tables are authored in AES-WEB-002G/H phase
# deliveries under this section's rules — recorded as a bounded deferral in
# §34.2.)" §31's AES-WEB-002G entry places authorship of all five tables in
# this wave, "closing §26's bounded deferral." No §26 prose subsection
# exists for these five roles (unlike home/category/business-profile before
# them) — each table below is derived directly from its own §6.1 matrix row
# plus the implicit common frame (§26 preamble: skip link -> header ->
# breadcrumb -> [recipe body] -> footer, not repeated as slots here).
#
# Modeling rule applied uniformly below (documented, not guessed, exactly
# the discipline the catalog modules use for under-determined table cells):
#   - A §6.1 cell with no descriptive text ("O"/"F" alone) is not modeled
#     as a slot at all -- inventing a specific purpose for an undescribed
#     cell would fabricate scope the authority does not state.
#   - A descriptive cell with a genuinely real, role-matching Wave 1-6
#     candidate (checked against that candidate's actual declared
#     supported_page_roles and required_props/required_content_slots, not
#     assumed) binds to that candidate's real prop/slot names.
#   - A required ("R") cell with no real candidate gets a guaranteed-
#     satisfiable Wave 1/2 fallback (required=True, fallback_component_id
#     set, honest required_slot_names/required_prop_names describing the
#     eventually-intended shape) -- the same treatment HOME_RECIPE_SLOTS's
#     own "hero" slot already uses.
#   - A required ("R") cell whose only plausible candidate is a Wave 7
#     family (monetization.*/status.*/legal.statement.*) does NOT get a
#     generic Wave 1/2 fallback forced into a status/legal-shaped slot;
#     it is modeled required=False with the _UNBUILT_FAMILY_SENTINEL,
#     exactly mirroring BUSINESS_PROFILE_RECIPE_SLOTS's own
#     "unavailable_state" slot precedent (also a §6.1 "R" cell, also
#     modeled required=False pending its dependency wave).
#   - An optional/recommended cell with no real candidate is sentinel-gated
#     (content-slot-filtered slots) or left with plain honest
#     required_prop_names and no sentinel (prop-filtered slots, where
#     §14.2 step 1's role filter alone already excludes every
#     non-role-matching candidate before slot-signature checking runs).
#
# Per the AES-WEB-002G preflight's Ambiguity Register (AMB-002G-02,
# operator-approved): this section is strictly additive. It does not touch
# HOME_RECIPE_SLOTS, CATEGORY_RECIPE_SLOTS, or BUSINESS_PROFILE_RECIPE_SLOTS
# above, including the _UNBUILT_FAMILY_SENTINEL slots those tables already
# carry for content.*/seo.* dependencies this wave happens to ship
# (HOME_RECIPE_SLOTS's "editorial_resources", CATEGORY_RECIPE_SLOTS's
# "related_categories_cities") -- that integration remains deferred to the
# later recipe-integration phase.

EDITORIAL_GUIDE_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "editorial-guide",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R editorial hero" -- no hero.* covers editorial-guide
    },
    {
        "slot_id": "embedded_listings",
        "page_role": "editorial-guide",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "O embedded listings" -- no listing.* covers editorial-guide (role filter drops it)
    },
    {
        "slot_id": "author_source_disclosure",
        "page_role": "editorial-guide",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("disclosure",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R author/source disclosure" -- legal.statement.standard is Wave 7; no trust.* covers editorial-guide
    },
    {
        "slot_id": "contextual_cta",
        "page_role": "editorial-guide",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "O contextual" -- no cta.* covers editorial-guide
    },
    {
        "slot_id": "related_guides_categories",
        "page_role": "editorial-guide",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        "required_prop_names": (),
        # Real candidate: content.resources.grid (this wave) -- its own
        # §27.7 roles include editorial-guide and its "Internal-link
        # support" note fits "related guides + categories" directly.
        "required_slot_names": ("resources",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §6.1 "R related guides + categories"
    },
)

COLLECTION_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "collection",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R collection hero" -- no hero.* covers collection
    },
    {
        "slot_id": "collection_cards",
        "page_role": "collection",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        # Real candidate: listing.card.standard (§27.5) -- its own roles
        # explicitly include "collection".
        "required_prop_names": ("listing_ref", "density"),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §6.1 "R collection cards"
    },
    {
        "slot_id": "empty_state",
        "page_role": "collection",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "R empty state" -- status.results.zero (Wave 3) does not cover collection; modeled required=False pending recipe-integration, mirroring BUSINESS_PROFILE_RECIPE_SLOTS's unavailable_state
    },
)

SERVICE_AREA_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "service-area",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        # Real candidate: hero.local.standard (§27.4) -- its own roles
        # explicitly include "service-area".
        "required_prop_names": ("context_role",),
        "required_slot_names": ("h1", "intro"),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R local hero"
    },
    {
        "slot_id": "providers_serving_area",
        "page_role": "service-area",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §6.1 "R providers serving area" -- no listing.* covers service-area
    },
    {
        "slot_id": "quote_cta",
        "page_role": "service-area",
        "purpose": "COLLECT_LEAD",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "REC quote" -- no form.*/cta.* covers service-area
    },
    {
        "slot_id": "area_parent_links",
        "page_role": "service-area",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("area_links",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §6.1 "R area + parent links" -- seo.local-links.* (this wave) does not declare service-area in its §27.7-authorized role list
    },
    {
        "slot_id": "zero_results",
        "page_role": "service-area",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "R zero-results" -- status.results.zero (Wave 3) does not cover service-area; modeled required=False pending recipe-integration
    },
)

VERIFICATION_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "verification",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R minimal hero" -- no hero.* covers verification
    },
    {
        "slot_id": "listing_summary",
        "page_role": "verification",
        "purpose": "REDUCE_UNCERTAINTY",
        "required_region": "",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §6.1 "R listing summary" -- no listing.* covers verification
    },
    {
        "slot_id": "verification_methodology",
        "page_role": "verification",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("methodology",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R verification methodology" -- no trust.* covers verification
    },
    {
        "slot_id": "verify_cta",
        "page_role": "verification",
        "purpose": "REDUCE_UNCERTAINTY",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("label",),
        "monetization_eligible": False,
        "fallback_component_id": "atom.button.action",
        "required": True,  # §6.1 "R verify CTA" -- no cta.* covers verification; ConversionGoal has no VERIFY member (§16.2), so no conversion_contract goal is asserted here
    },
    {
        "slot_id": "pending_state",
        "page_role": "verification",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "R pending state" -- status.listing.pending is Wave 7 (§27.8); modeled required=False pending recipe-integration
    },
)

REGIONAL_HUB_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "regional-hub",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R regional hero" -- no hero.* covers regional-hub
    },
    {
        "slot_id": "region_navigator",
        "page_role": "regional-hub",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        # Real candidate: directory.locations.grid (§27.4) -- its own
        # roles explicitly include "regional-hub".
        "required_prop_names": ("location_source_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.grid.standard",
        "required": True,  # §6.1 "R region navigator"
    },
    {
        "slot_id": "top_listings_per_region",
        "page_role": "regional-hub",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "REC top listings per child region" -- no listing.* covers regional-hub (role filter drops it)
    },
    {
        "slot_id": "regional_statistics",
        "page_role": "regional-hub",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "O regional statistics" -- no trust.* covers regional-hub
    },
    {
        "slot_id": "child_region_links",
        "page_role": "regional-hub",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        "required_prop_names": (),
        # Real candidate: seo.local-links.cities (this wave) -- its own
        # §27.7 roles explicitly include "regional-hub".
        "required_slot_names": ("city_links",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §6.1 "R child-region link grids"
    },
    {
        "slot_id": "sparse_region_state",
        "page_role": "regional-hub",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "R sparse-region state" -- status.results.zero (Wave 3) does not cover regional-hub; modeled required=False pending recipe-integration
    },
)


# ---------------------------------------------------------------------------
# Monetization disclosure kinds (AES-WEB-002H; AES-WEB-002 §17.1, §8.4)
# ---------------------------------------------------------------------------
#
# §17.1: "visible (human-readable label from the constants-registered
# disclosure text set)". §8.4's DisclosureBlock content model: "disclosure
# kind enum + RichText body from constants-registered templates." No member
# of contracts/enums.py names this set -- MonetizationContract.disclosure_kind
# (contracts/components.py) is a plain ``str`` field, not an enum reference,
# per the frozen §3 ComponentDefinition schema -- so a new, additive,
# controlled-vocabulary constants table is the correct home for it, mirroring
# the CTA_GOAL_LABEL_CLASSES precedent (AES-WEB-002F; §16.2) rather than
# inventing a new contracts/enums.py member (out of scope: enum changes are
# a frozen-contract concern, §3 Frozen-Contract Register item 7).
#
# Scoped to the four kinds AES-WEB-002H's own MonetizationContract-bearing
# components (the MONETIZATION-family four; §5.10, §27.8) actually need.
# commerce.pricing.sponsorship's own E4 disclaimer is a plain RichTextBlock
# content slot, not a MonetizationContract (COMMERCE is not a
# monetization_contract-required family, §15.2), so it draws no kind from
# this table. Extending this set is additive, registry-minor work for
# whichever later wave needs more kinds (§22.2).
MONETIZATION_DISCLOSURE_KIND_ADVERTISING = "advertising"
MONETIZATION_DISCLOSURE_KIND_PREMIUM = "premium"
MONETIZATION_DISCLOSURE_KIND_SPONSORED = "sponsored"
MONETIZATION_DISCLOSURE_KIND_UPGRADE = "upgrade"

MONETIZATION_DISCLOSURE_KINDS = (
    MONETIZATION_DISCLOSURE_KIND_ADVERTISING,
    MONETIZATION_DISCLOSURE_KIND_PREMIUM,
    MONETIZATION_DISCLOSURE_KIND_SPONSORED,
    MONETIZATION_DISCLOSURE_KIND_UPGRADE,
)


# ---------------------------------------------------------------------------
# Remaining recipe slot tables (AES-WEB-002J.1 "Recipe Completion"; AES-WEB-002
# §26.3-26.5, §26.7-26.13, §6.1)
# ---------------------------------------------------------------------------
#
# Closes the recipe-table gap tracked since 002A (this module's opening
# docstring), the §26 closing note, and the Implementation Roadmap ("002J MVP
# integration: All recipes end-to-end"): after HOME/CATEGORY (002D, §26.1-
# 26.2), BUSINESS_PROFILE (002E, §26.6), and the five secondary roles closing
# the §34.2 bounded deferral (002G, above), ten PageRoles still had no recipe
# table -- city, city-category, search-results, comparison, best-of,
# lead-gen-landing, claim-listing, sponsor-page, submission, correction (the
# order below matches their row order in the §6.1 matrix, the same
# convention the five secondary tables above already use). Confirmed absent
# by direct inspection of this module and by the explicit forward-looking
# regression guards in tests/website_generation/components/test_catalog_wave6.py
# (``test_no_city_category_recipe_table_created``) and
# test_catalog_wave7.py (``test_no_new_recipe_table_created_by_wave7``),
# both updated alongside this delivery since their premise ("this table does
# not exist yet") is exactly what this delivery changes -- no other
# assertion in either file is touched.
#
# Unlike 002D/002G, every catalog wave (1-7) and the component gate families
# (002I) are registered by this point, so most slots below bind to a real,
# already-registered candidate rather than falling straight to sentinel-
# gating. The modeling discipline is unchanged from the block comment above
# EDITORIAL_GUIDE_RECIPE_SLOTS, applied uniformly:
#   - A §6.1 cell with no descriptive text ("O"/"F" alone) is not modeled as
#     a slot. Nor is a cell whose concept is actually an internal detail of
#     another slot's real candidate (sponsored cards interleaved into an
#     existing listing_cards-shaped slot, exactly as CATEGORY_RECIPE_SLOTS
#     already declines to give "O sponsored cards inline" its own slot; a
#     form's own success/error states, e.g. form.lead.quote's
#     ConversionContract.success_state/failure_state, rather than a separate
#     recipe slot for lead-gen-landing's "R form success/error"; or a link
#     already folded into a real candidate's own required_content_slots,
#     e.g. form.submission.listing's own "standards_link").
#   - A descriptive cell (or, where §26.x's prose is more granular than the
#     §6.1 matrix cell it summarizes, a prose sequence step -- the same
#     latitude CATEGORY_RECIPE_SLOTS already used to expand "R filters/sort
#     links, R results summary" into three slots) with a genuinely real,
#     role-matching candidate (checked against that candidate's actual
#     declared supported_page_roles and required_props/required_content_slots
#     via components.registry.build_default_registry(), not assumed) binds
#     to that candidate's real prop/slot names, noted with a "Real candidate"
#     comment, and receives a guaranteed-satisfiable Wave 1/2
#     fallback_component_id (every required slot below carries one,
#     regardless of whether a real candidate was also found -- the
#     belt-and-suspenders posture SERVICE_AREA_RECIPE_SLOTS/
#     REGIONAL_HUB_RECIPE_SLOTS already use, superseding CATEGORY_RECIPE_
#     SLOTS's older practice of sometimes omitting it).
#   - A required ("R") cell with no real candidate still gets a
#     guaranteed-satisfiable Wave 1/2 fallback: required=True,
#     fallback_component_id set, honest required_prop_names/
#     required_slot_names describing the eventually-intended shape (the
#     same treatment HOME_RECIPE_SLOTS's own "hero" slot already uses). Two
#     §6.1 cells name a specific component id that was never registered in
#     any of the seven catalog waves (§27) -- "hero.city.standard" (city)
#     and "hero.leadgen.offer" (lead-gen-landing); both resolve to
#     hero.local.standard where its own supported_page_roles actually cover
#     the role, or to the same honest-fallback treatment otherwise. Recorded
#     here rather than silently invented or silently renamed, matching the
#     Index's own D1-D4 discrepancy-recording precedent.
#   - A required ("R") *status* cell (empty/zero/pending/sparse-state) whose
#     only real candidate is status.results.zero/status.listing.* and that
#     candidate does not declare this specific role is modeled required=False
#     with the sentinel, exactly mirroring COLLECTION_RECIPE_SLOTS's
#     "empty_state" / SERVICE_AREA_RECIPE_SLOTS's "zero_results" /
#     VERIFICATION_RECIPE_SLOTS's "pending_state" / REGIONAL_HUB_RECIPE_
#     SLOTS's "sparse_region_state" precedent -- a status cell is the one
#     case this module already treats as "no invented fallback", since a
#     generic Wave 1/2 primitive cannot honestly stand in for a recovery-
#     action state component. Where a real status.* candidate *does* declare
#     the role (status.listing.pending for claim-listing, per
#     STATUS_CELL_COVERAGE in test_catalog_wave7.py), the cell binds to it
#     directly instead.
#   - An optional/recommended cell with no real candidate is sentinel-gated
#     (content-slot-filtered slots) or left with plain honest
#     required_prop_names and no sentinel (prop-filtered slots, where
#     §14.2 step 1's role filter alone -- confirmed empty of candidates for
#     that role via the same registry check -- already excludes every
#     non-role-matching candidate before slot-signature checking runs).
#   - best-of's "O clearly-separated featured block" and comparison's
#     "O affiliate (P3, disclosed)" cells are two special cases already
#     characterized by name in test_catalog_wave7.py: the former is recorded
#     there as a known, carried gap (neither listing.card.featured nor
#     monetization.ribbon.sponsor declares best-of), modeled here
#     required=False and sentinel-gated rather than silently dropped; the
#     latter is P3 scope per §34.2 and correctly absent from the 72-component
#     MVP inventory, so no comparison affiliate slot is modeled at all.
#
# Per the AMB-002G-02/AMB-002F-02/AMB-002H-02 precedent this delivery
# continues a final time: strictly additive. It does not touch
# HOME_RECIPE_SLOTS, CATEGORY_RECIPE_SLOTS, BUSINESS_PROFILE_RECIPE_SLOTS,
# EDITORIAL_GUIDE_RECIPE_SLOTS, COLLECTION_RECIPE_SLOTS,
# SERVICE_AREA_RECIPE_SLOTS, VERIFICATION_RECIPE_SLOTS, or
# REGIONAL_HUB_RECIPE_SLOTS above.

CITY_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "city",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        # §6.1 names "hero.city.standard", never registered in any catalog
        # wave (§27.4 lists only hero.search.directory/hero.local.standard)
        # -- recorded as a discrepancy, not invented. Real candidate:
        # hero.local.standard (§27.4) -- its own roles explicitly include
        # "city".
        "required_prop_names": ("context_role",),
        "required_slot_names": ("h1", "intro"),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R hero.city.standard"
    },
    {
        "slot_id": "categories_in_city_navigator",
        "page_role": "city",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        # Real candidate: directory.categories.grid (§27.4) -- its own roles
        # explicitly include "city".
        "required_prop_names": ("category_source_ref", "columns"),
        "required_slot_names": ("category_tiles",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.grid.standard",
        "required": True,  # §26.3 "categories-in-city navigator"
    },
    {
        "slot_id": "listing_cards",
        "page_role": "city",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        # "density" required so this organic-default slot resolves to
        # listing.card.standard, never listing.card.featured/sponsored --
        # the same discipline CATEGORY_RECIPE_SLOTS's own "listing_cards"
        # slot already documents.
        "required_prop_names": ("listing_ref", "density"),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §26.3 "listing cards"
    },
    {
        "slot_id": "local_facts",
        "page_role": "city",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "O local facts" -- no trust.* covers city
    },
    {
        "slot_id": "nearby_cities_parent_region",
        "page_role": "city",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        # Real candidate: seo.local-links.cities (§27.7) -- its own roles
        # explicitly include "city".
        "required_prop_names": ("city_source_ref",),
        "required_slot_names": ("city_links",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §6.1 "R nearby cities + parent region"
    },
    {
        "slot_id": "zero_results",
        "page_role": "city",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        # Real candidate: status.results.zero (§27.4) -- its own roles
        # explicitly include "city"; no fallback needed, mirroring
        # CATEGORY_RECIPE_SLOTS's own "zero_results" slot exactly.
        "required_prop_names": (),
        "required_slot_names": ("message", "recovery_links"),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": True,  # §26.3 / §6.1 "R zero-results"
    },
)

CITY_CATEGORY_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "city-category",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        # Real candidate: hero.local.standard (§27.4) -- its own roles
        # explicitly include "city-category".
        "required_prop_names": ("context_role",),
        "required_slot_names": ("h1", "intro"),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.4 "Compact local hero"
    },
    {
        "slot_id": "filters",
        "page_role": "city-category",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        # Real candidate: directory.filters.panel (§27.4) -- its own roles
        # explicitly include "city-category".
        "required_prop_names": ("facet_set_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.4 "filter links"
    },
    {
        "slot_id": "results_summary",
        "page_role": "city-category",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        # Real candidate: directory.results.summary (§27.4) -- its own roles
        # explicitly include "city-category". No "sort" step appears in
        # §26.4's own prose or in §6.1's Discovery cell for this role
        # (unlike category's), so no sort slot is modeled here.
        "required_prop_names": (),
        "required_slot_names": ("summary_text",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.4 "results summary"
    },
    {
        "slot_id": "listing_cards",
        "page_role": "city-category",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        "required_prop_names": ("listing_ref", "density"),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §26.4 "listing cards"
    },
    {
        "slot_id": "quote_cta_band",
        "page_role": "city-category",
        "purpose": "COLLECT_LEAD",
        "required_region": "",
        # No cta.quote.* component exists; form.lead.quote (§27.6) is the
        # real QUOTE_REQUEST-goal candidate and its own roles explicitly
        # include "city-category".
        "required_prop_names": ("action_route",),
        "required_slot_names": ("disclosure",),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "REC quote CTA"
    },
    {
        "slot_id": "nearby_city_links",
        "page_role": "city-category",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        # §26.4 "nearby city-category links -> parent city + parent category
        # links" is two prose steps; §6.1's single "R nearby city-category
        # links" cell compresses both, the same compression CATEGORY_RECIPE_
        # SLOTS's own "R filters/sort links, R results summary" cell used
        # before being expanded into granular slots. Real candidate:
        # seo.local-links.cities (§27.7) -- its own roles explicitly include
        # "city-category"; covers the city-axis half.
        "required_prop_names": ("city_source_ref",),
        "required_slot_names": ("city_links",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.4 / §6.1 "R nearby city-category links"
    },
    {
        "slot_id": "parent_category_links",
        "page_role": "city-category",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        # Real candidate: seo.local-links.categories (§27.7) -- its own
        # roles explicitly include "city-category"; covers the
        # category-axis half of the same compressed §6.1 cell.
        "required_prop_names": ("category_source_ref",),
        "required_slot_names": ("category_links",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.4 "parent city + parent category links"
    },
    {
        "slot_id": "zero_results",
        "page_role": "city-category",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("message", "recovery_links"),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": True,  # §6.1 "R zero-results"
    },
)

SEARCH_RESULTS_RECIPE_SLOTS = (
    # §6.1 Hero column: "F (results header instead)"; §26.5: "No hero, no
    # trust, minimal chrome." No hero slot is modeled for this role.
    {
        "slot_id": "results_header",
        "page_role": "search-results",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        # Real candidate: directory.results.summary (§27.4) -- its own
        # roles explicitly include "search-results".
        "required_prop_names": (),
        "required_slot_names": ("summary_text",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.5 "Results header (query echo + count)"
    },
    {
        "slot_id": "filters",
        "page_role": "search-results",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        # Real candidate: directory.filters.panel (§27.4) -- its own roles
        # explicitly include "search-results".
        "required_prop_names": ("facet_set_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.5 "filters/sort"
    },
    {
        "slot_id": "sort",
        "page_role": "search-results",
        "purpose": "SUPPORT_DISCOVERY",
        "required_region": "",
        # Real candidate: directory.sort.control (§27.4) -- its own roles
        # explicitly include "search-results".
        "required_prop_names": ("sort_options_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §26.5 "filters/sort"
    },
    {
        "slot_id": "listing_rows_or_cards",
        "page_role": "search-results",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        # "density" required so this organic-default slot resolves to
        # listing.card.standard rather than listing.card.sponsored or
        # listing.row.compact (neither of which declares "density"),
        # mirroring CATEGORY_RECIPE_SLOTS's own "listing_cards" discipline.
        "required_prop_names": ("listing_ref", "density"),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §26.5 "compact rows or cards"
    },
    {
        "slot_id": "pagination",
        "page_role": "search-results",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        # Real candidate: nav.pagination.standard (§27.3) -- its own roles
        # explicitly include "search-results"; no fallback needed, mirroring
        # CATEGORY_RECIPE_SLOTS's own "pagination" slot exactly.
        "required_prop_names": ("page_context",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": True,  # §26.5 "pagination"
    },
    {
        "slot_id": "related_searches",
        "page_role": "search-results",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.5 "related searches (O)" -- no seo.* covers this
    },
    {
        "slot_id": "zero_results",
        "page_role": "search-results",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        # Real candidate: status.results.zero (§27.4) -- its own roles
        # explicitly include "search-results"; no fallback needed, mirroring
        # CATEGORY_RECIPE_SLOTS's own "zero_results" slot exactly.
        "required_prop_names": (),
        "required_slot_names": ("message", "recovery_links"),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": True,  # §26.5 / §6.1 "R zero-results"
    },
)

COMPARISON_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "comparison",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.7 "Comparison hero" -- no hero.* covers comparison
    },
    {
        "slot_id": "methodology",
        "page_role": "comparison",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("methodology",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.7 "methodology block (E6)" -- no dedicated methodology component exists in any wave
    },
    {
        "slot_id": "comparison_table",
        "page_role": "comparison",
        "purpose": "SUPPORT_COMPARISON",
        "required_region": "",
        # Real candidate: content.table.comparison (§27.7) -- its own roles
        # explicitly include "comparison".
        "required_prop_names": (),
        "required_slot_names": ("table",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.7 "comparison table"
    },
    {
        "slot_id": "page_cta_band",
        "page_role": "comparison",
        "purpose": "IMPROVE_CONVERSION",
        "required_region": "",
        # §26.7's "per-row CTA" is modeled as part of comparison_table's own
        # content (a per-row action belongs to the table's ComparisonTableBlock,
        # not a separate top-level recipe slot -- the same non-duplication
        # rule CATEGORY_RECIPE_SLOTS applies to "sponsored cards inline").
        # No cta.* component covers comparison.
        "required_prop_names": (),
        "required_slot_names": ("label",),
        "monetization_eligible": False,
        "fallback_component_id": "atom.button.action",
        "required": True,  # §26.7 "page CTA band"
    },
    {
        "slot_id": "empty_comparison",
        "page_role": "comparison",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "R empty-comparison" -- status.results.zero does not cover comparison; modeled required=False pending recipe-integration, mirroring COLLECTION_RECIPE_SLOTS's "empty_state" precedent
    },
    {
        "slot_id": "related_links",
        "page_role": "comparison",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.7 "related links" (§6.1 SEO-links cell: bare "REC") -- no seo.* covers comparison
    },
    # §6.1 Monetization cell "O affiliate (P3, disclosed)" is P3 scope,
    # correctly absent from the 72-component MVP inventory (§27.1 closing;
    # confirmed exercisability-absent by
    # test_comparison_affiliate_monetization_correctly_unexercisable in
    # test_catalog_wave7.py) -- no affiliate slot is modeled.
)

BEST_OF_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "best-of",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.8 "Editorial hero" -- no hero.* covers best-of
    },
    {
        "slot_id": "ranking_methodology",
        "page_role": "best-of",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("methodology",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.8 "ranking methodology" -- no dedicated methodology component exists in any wave
    },
    {
        "slot_id": "ranked_listing_cards",
        "page_role": "best-of",
        "purpose": "EXPOSE_INVENTORY",
        "required_region": "",
        # Pre-existing Wave-4 gap (recorded in test_catalog_wave7.py's
        # TestMonetizationCellAndStatusExercisability docstring): no
        # listing.* component declares "best-of" among its
        # supported_page_roles, and no ranking_rationale content slot exists
        # anywhere in the registry.
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §26.8 "ranked listing cards with per-rank rationale slots"
    },
    {
        "slot_id": "related_best_of_links",
        "page_role": "best-of",
        "purpose": "STRENGTHEN_INTERNAL_LINKING",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("related_links",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.stack.standard",
        "required": True,  # §6.1 "R related best-of links" -- neither seo.local-links.cities nor seo.local-links.categories covers best-of
    },
    {
        "slot_id": "featured_block",
        "page_role": "best-of",
        "purpose": "PREPARE_MONETIZATION",
        "required_region": "",
        # Confirmed known gap: neither listing.card.featured nor
        # monetization.ribbon.sponsor declares "best-of"
        # (test_best_of_featured_block_is_a_known_uncovered_gap,
        # test_catalog_wave7.py).
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": True,
        "fallback_component_id": "",
        "required": False,  # §6.1 "O clearly-separated featured block"
    },
)

LEAD_GEN_LANDING_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "lead-gen-landing",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        # §6.1 names "hero.leadgen.offer", never registered in any catalog
        # wave (§27.4 lists only hero.search.directory/hero.local.standard,
        # neither of which declares "lead-gen-landing") -- recorded as a
        # discrepancy, not invented.
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §6.1 "R hero.leadgen.offer"
    },
    {
        "slot_id": "social_proof_listings",
        "page_role": "lead-gen-landing",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §26.11 "social-proof listings (O)" -- no listing.* covers lead-gen-landing
    },
    {
        "slot_id": "trust_adjacent_to_form",
        "page_role": "lead-gen-landing",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        # Real candidate: trust.statistics.strip (§27.6) -- its own roles
        # explicitly include "lead-gen-landing".
        "required_prop_names": (),
        "required_slot_names": ("statistics",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.11 / §6.1 "R trust adjacent to form"
    },
    {
        "slot_id": "lead_quote_form",
        "page_role": "lead-gen-landing",
        "purpose": "COLLECT_LEAD",
        "required_region": "",
        # Real candidate: form.lead.quote (§27.6) -- its own roles
        # explicitly include "lead-gen-landing"; literally named in §6.1.
        # Its own ConversionContract.success_state/failure_state satisfies
        # §6.1's "R form success/error" Status cell -- not a separate slot,
        # mirroring CATEGORY_RECIPE_SLOTS's "sponsored cards inline"
        # non-duplication rule.
        "required_prop_names": ("action_route",),
        "required_slot_names": ("disclosure",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.11 "lead/quote form (<= 6 fields)"; §6.1 "R form.lead.quote (single goal)"
    },
)

CLAIM_LISTING_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "claim-listing",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.10 "Compact explainer hero" -- no hero.* covers claim-listing
    },
    {
        "slot_id": "listing_preview",
        "page_role": "claim-listing",
        "purpose": "REDUCE_UNCERTAINTY",
        "required_region": "",
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "O preview of listing" -- no listing.* covers claim-listing
    },
    {
        "slot_id": "verification_explanation",
        "page_role": "claim-listing",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": ("explanation",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.10 "verification explanation" -- no trust.* covers claim-listing
    },
    {
        "slot_id": "claim_form",
        "page_role": "claim-listing",
        "purpose": "ENCOURAGE_CLAIM",
        "required_region": "",
        # Real candidate: form.claim.standard (§27.6) -- its own roles are
        # exactly ("claim-listing",); literally named in §6.1.
        "required_prop_names": ("action_route", "listing_ref"),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.10 "claim form (<= 5 fields step one)"; §6.1 "R form.claim.standard"
    },
    {
        "slot_id": "upgrade_preview",
        "page_role": "claim-listing",
        "purpose": "PREPARE_MONETIZATION",
        "required_region": "",
        # Real candidate: monetization.prompt.upgrade (§27.8) -- its own
        # roles are exactly ("claim-listing",); confirmed via
        # MONETIZATION_CELL_COVERAGE in test_catalog_wave7.py.
        "required_prop_names": (),
        "required_slot_names": ("disclosure", "offer"),
        "monetization_eligible": True,
        "fallback_component_id": "",
        "required": False,  # §26.10 "upgrade preview (O, disclosed, after form)"
    },
    {
        "slot_id": "claim_state",
        "page_role": "claim-listing",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        # Real candidate: status.listing.pending (§27.8) -- its own roles
        # explicitly include "claim-listing"; confirmed via
        # STATUS_CELL_COVERAGE in test_catalog_wave7.py, unlike the other
        # required-status cells in this delivery.
        "required_prop_names": (),
        "required_slot_names": ("expectation_text", "message"),
        "monetization_eligible": False,
        "fallback_component_id": "atom.alert.notice",
        "required": True,  # §6.1 "R states"
    },
)

SPONSOR_PAGE_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "sponsor-page",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.9 "Offer hero" -- no hero.* covers sponsor-page
    },
    {
        "slot_id": "audience_statistics",
        "page_role": "sponsor-page",
        "purpose": "ESTABLISH_TRUST",
        "required_region": "",
        # Real candidate: trust.statistics.strip (§27.6) -- its own roles
        # explicitly include "sponsor-page".
        "required_prop_names": (),
        "required_slot_names": ("statistics",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.9 "audience statistics (evidenced)"
    },
    {
        "slot_id": "example_placements",
        "page_role": "sponsor-page",
        "purpose": "",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "O example placements" -- no component covers this
    },
    {
        "slot_id": "sponsor_inquiry_cta",
        "page_role": "sponsor-page",
        "purpose": "ENCOURAGE_SPONSORSHIP",
        "required_region": "",
        # Real candidate: cta.sponsor.inquiry (§27.6) -- its own roles are
        # exactly ("sponsor-page",).
        "required_prop_names": ("target_route",),
        "required_slot_names": ("label",),
        "monetization_eligible": False,
        "fallback_component_id": "atom.button.action",
        "required": True,  # §26.9 "sponsor inquiry form"; §6.1 "R sponsor inquiry form"
    },
    {
        "slot_id": "sponsorship_pricing",
        "page_role": "sponsor-page",
        "purpose": "PREPARE_MONETIZATION",
        "required_region": "",
        # Real candidate: commerce.pricing.sponsorship (§27.8) -- its own
        # roles are exactly ("sponsor-page",).
        "required_prop_names": (),
        "required_slot_names": ("disclaimer", "pricing"),
        "monetization_eligible": True,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.9 "sponsorship pricing"; §6.1 "R sponsorship pricing"
    },
    {
        "slot_id": "paid_placement_disclosure",
        "page_role": "sponsor-page",
        "purpose": "PREPARE_MONETIZATION",
        "required_region": "",
        # Real candidate: monetization.disclosure.advertising (§27.8) --
        # confirmed via MONETIZATION_CELL_COVERAGE in test_catalog_wave7.py.
        "required_prop_names": ("disclosure_kind",),
        "required_slot_names": ("disclosure",),
        "monetization_eligible": True,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.9 "paid-placement disclosure"; §6.1 "R paid-placement disclosure"
    },
    {
        "slot_id": "states",
        "page_role": "sponsor-page",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "R states" -- no status.* covers sponsor-page; modeled required=False pending recipe-integration
    },
)

SUBMISSION_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "submission",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.12 "Compact hero" -- no hero.* covers submission
    },
    {
        "slot_id": "submission_form",
        "page_role": "submission",
        "purpose": "ENCOURAGE_SUBMISSION",
        "required_region": "",
        # Real candidate: form.submission.listing (§27.6) -- its own roles
        # are exactly ("submission",); literally named in §6.1. Its own
        # required "standards_link" content slot satisfies §26.12's
        # "editorial standards link" step -- not a separate slot, mirroring
        # CATEGORY_RECIPE_SLOTS's "sponsored cards inline" non-duplication
        # rule.
        "required_prop_names": ("action_route",),
        "required_slot_names": ("standards_link",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.12 "submission form"; §6.1 "R form.submission.listing"
    },
    {
        "slot_id": "paid_fast_track",
        "page_role": "submission",
        "purpose": "PREPARE_MONETIZATION",
        "required_region": "",
        # Real candidate: monetization.disclosure.advertising (§27.8) --
        # confirmed via MONETIZATION_CELL_COVERAGE in test_catalog_wave7.py.
        "required_prop_names": ("disclosure_kind",),
        "required_slot_names": ("disclosure",),
        "monetization_eligible": True,
        "fallback_component_id": "",
        "required": False,  # §26.12 "paid fast-track option (O, disclosed, equal-weight free path)"
    },
    {
        "slot_id": "states",
        "page_role": "submission",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "R states" -- no status.* covers submission; modeled required=False pending recipe-integration
    },
)

CORRECTION_RECIPE_SLOTS = (
    {
        "slot_id": "hero",
        "page_role": "correction",
        "purpose": "COMMUNICATE_VALUE",
        "required_region": "HERO",
        "required_prop_names": (),
        "required_slot_names": ("h1",),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.13 "Minimal hero" -- no hero.* covers correction
    },
    {
        "slot_id": "listing_being_corrected",
        "page_role": "correction",
        "purpose": "ORIENT",
        "required_region": "",
        # No listing.* component covers correction. purpose=ORIENT (rather
        # than REDUCE_UNCERTAINTY) deliberately: form.correction.standard
        # also declares "listing_ref" among its own required props, and
        # binding this slot's purpose to REDUCE_UNCERTAINTY would let step 5
        # commercial-purpose matching resolve it to the form component
        # instead of the intended fallback -- verified against the real
        # ComponentSelector, not assumed.
        "required_prop_names": ("listing_ref",),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.card.shell",
        "required": True,  # §6.1 "R listing being corrected (summary)"
    },
    {
        "slot_id": "data_source_disclosure",
        "page_role": "correction",
        "purpose": "SATISFY_LEGAL",
        "required_region": "",
        # Real candidate: legal.statement.standard (§27.8, universal) with
        # kind="data-source" (one of its registered kind enum values).
        "required_prop_names": ("kind",),
        "required_slot_names": ("body",),
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "REC data-source disclosure"
    },
    {
        "slot_id": "correction_form",
        "page_role": "correction",
        "purpose": "REDUCE_UNCERTAINTY",
        "required_region": "",
        # Real candidate: form.correction.standard (§27.6) -- its own roles
        # are exactly ("correction",); literally named in §6.1.
        "required_prop_names": ("action_route", "listing_ref"),
        "required_slot_names": (),
        "monetization_eligible": False,
        "fallback_component_id": "layout.section.container",
        "required": True,  # §26.13 "correction form"; §6.1 "R form.correction.standard"
    },
    {
        "slot_id": "states",
        "page_role": "correction",
        "purpose": "SYSTEM_STATUS",
        "required_region": "",
        "required_prop_names": (),
        "required_slot_names": _UNBUILT_FAMILY_SENTINEL,
        "monetization_eligible": False,
        "fallback_component_id": "",
        "required": False,  # §6.1 "R states" -- no status.* covers correction; modeled required=False pending recipe-integration
    },
)


# ---------------------------------------------------------------------------
# Page-role -> recipe slot table map (AES-WEB-002J.6; AES-WEB-002 §26)
#
# §26: recipes are "declarative default sequences per PageRole ... consumed
# by the Component Engine (slot needs)". This map is the single lookup the
# Component Engine (components/component_engine.py) uses to resolve a page's
# PageRole to its recipe slot table. Keyed by the PageRole *value* string
# (constants/ may not import contracts/, §3.2), which is exactly the string
# every recipe slot dict already carries in its "page_role" field and the
# string SiteArchitecture stores in PagePlan.page_type. All eighteen §6.1
# roles are covered -- one recipe table each, authored across AES-WEB-002D
# (home/category), AES-WEB-002E (business-profile), and AES-WEB-002J.1
# (the remaining fifteen). Insertion order follows the PageRole enum
# declaration order (contracts/enums.py) for readability; lookups are by key
# and never depend on this order.
RECIPE_SLOTS_BY_PAGE_ROLE = {
    "home": HOME_RECIPE_SLOTS,
    "category": CATEGORY_RECIPE_SLOTS,
    "city": CITY_RECIPE_SLOTS,
    "city-category": CITY_CATEGORY_RECIPE_SLOTS,
    "search-results": SEARCH_RESULTS_RECIPE_SLOTS,
    "business-profile": BUSINESS_PROFILE_RECIPE_SLOTS,
    "comparison": COMPARISON_RECIPE_SLOTS,
    "best-of": BEST_OF_RECIPE_SLOTS,
    "editorial-guide": EDITORIAL_GUIDE_RECIPE_SLOTS,
    "collection": COLLECTION_RECIPE_SLOTS,
    "service-area": SERVICE_AREA_RECIPE_SLOTS,
    "lead-gen-landing": LEAD_GEN_LANDING_RECIPE_SLOTS,
    "claim-listing": CLAIM_LISTING_RECIPE_SLOTS,
    "sponsor-page": SPONSOR_PAGE_RECIPE_SLOTS,
    "submission": SUBMISSION_RECIPE_SLOTS,
    "correction": CORRECTION_RECIPE_SLOTS,
    "verification": VERIFICATION_RECIPE_SLOTS,
    "regional-hub": REGIONAL_HUB_RECIPE_SLOTS,
}

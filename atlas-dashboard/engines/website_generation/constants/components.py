"""Component-system constants (AES-WEB-002A; AES-WEB-002 §4, §7.3, §9.2, §22).

Constants only — no computation, no imports beyond the standard library
(dependency matrix, AES-WEB-001 §3.2). Every component-system magic number
lives here or does not exist.

Scope note: 002A owns the naming grammar, complexity budgets, composition
limits, and version constants that the registry needs to validate
definitions. The §3.2 selection scoring tables and CTA label/action table
support the selection and conversion waves (002D/002F) and are deferred
there, not authored in 002A.
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
        "purpose": "CORRECTION_REQUEST",
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

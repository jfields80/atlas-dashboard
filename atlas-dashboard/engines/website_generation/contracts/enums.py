"""Core enumerations for the Website Generation Engine (AES-WEB-001 Phase 1).

Every enum is a ``str`` subclass so canonical JSON serialization is stable
under both Pydantic v1 and v2 and across process runs.

Authority: AES-WEB-001 §4.1 (ArtifactKind), §6.2 (BuildState), §6.7
(StageOutcome routing), §10.1 (GateSeverity), §4.5 (artifact lifecycle).
"""

from __future__ import annotations

from enum import Enum


class ArtifactKind(str, Enum):
    """The twelve artifact kinds of the AES-WEB-001 catalog (§4.1)."""

    BUSINESS_SPEC = "BUSINESS_SPEC"
    BRAND_PACKAGE = "BRAND_PACKAGE"
    SITE_ARCHITECTURE = "SITE_ARCHITECTURE"
    CONTENT_CANDIDATE = "CONTENT_CANDIDATE"
    CONTENT_PACKAGE = "CONTENT_PACKAGE"
    COMPONENT_MANIFEST = "COMPONENT_MANIFEST"
    LAYOUT_PLAN = "LAYOUT_PLAN"
    RENDERED_PAGE_SET = "RENDERED_PAGE_SET"
    SEO_PACKAGE = "SEO_PACKAGE"
    SITE_BUNDLE = "SITE_BUNDLE"
    QUALITY_REPORT = "QUALITY_REPORT"
    BUILD_MANIFEST = "BUILD_MANIFEST"


class BuildState(str, Enum):
    """Build lifecycle states (AES-WEB-001 §6.2)."""

    INITIALIZED = "INITIALIZED"
    SPEC_COMPILED = "SPEC_COMPILED"
    BRAND_RESOLVED = "BRAND_RESOLVED"
    IA_PLANNED = "IA_PLANNED"
    CONTENT_DRAFTING = "CONTENT_DRAFTING"
    CONTENT_VALIDATED = "CONTENT_VALIDATED"
    COMPONENTS_RESOLVED = "COMPONENTS_RESOLVED"
    LAYOUT_COMPOSED = "LAYOUT_COMPOSED"
    RENDERED = "RENDERED"
    SEO_COMPILED = "SEO_COMPILED"
    ASSEMBLED = "ASSEMBLED"
    GATED = "GATED"
    CERTIFIED = "CERTIFIED"
    PACKAGED = "PACKAGED"
    DEPLOY_READY = "DEPLOY_READY"

    # Failure / control states (reachable from any active state).
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    ESCALATED_HUMAN = "ESCALATED_HUMAN"
    CANCELLED = "CANCELLED"
    GATE_REJECTED = "GATE_REJECTED"


class StageOutcome(str, Enum):
    """Outcomes the effectful shell reports to the pure transition law.

    Routing semantics follow AES-WEB-001 §6.2, §6.7 and §6.8.
    """

    SUCCESS = "SUCCESS"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    ESCALATE = "ESCALATE"
    CANCEL = "CANCEL"
    GATE_REJECT = "GATE_REJECT"
    REWORK = "REWORK"
    RETRY = "RETRY"


class GateSeverity(str, Enum):
    """Quality gate severities (AES-WEB-001 §10.1)."""

    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


class ArtifactLifecycleState(str, Enum):
    """Lifecycle tracked *about* artifacts, never inside them (§4.5)."""

    PRODUCED = "PRODUCED"
    VALIDATED = "VALIDATED"
    CONSUMED = "CONSUMED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class StageExecutionStatus(str, Enum):
    """Execution status of a pipeline stage as recorded in the BuildManifest.

    Phase 1 records unimplemented future stages as ``NOT_EXECUTED`` —
    never as successful (Sprint 1 directive; AES-WEB-001 Part 13 Phase 1).
    """

    EXECUTED = "EXECUTED"
    NOT_EXECUTED = "NOT_EXECUTED"


# ===========================================================================
# Component system enumerations (AES-WEB-002A — Contracts and Registry)
#
# Every enum is a ``str`` subclass for stable canonical JSON serialization.
# Values are taken verbatim from AES-WEB-002; no members are invented.
# ===========================================================================


class ComponentFamily(str, Enum):
    """Component taxonomy families (AES-WEB-002 §5). Values are the
    ``component_id`` family segment; membership is permanent per component.

    Governing interpretation (documented, not guessed): the members below are
    the complete, non-lossy enumeration of every family segment the authority
    names — the fifteen commercial family segments defined in §5.1–§5.15
    (``nav, hero, directory, listing, profile, trust, cta, content, seo,
    monetization, social, commerce, form, status, legal``) plus the two
    §5.16 foundation families (``layout``, ``atom``): seventeen in total.

    NOTE — the authority's advertised family counts are internally
    inconsistent: §5's opening sentence says "Fourteen top-level families",
    §34.1 says "Sixteen-family taxonomy", yet §5.1–§5.16 enumerate seventeen
    distinct family segments. No arithmetic reconciles 14, 16, and 17. Per
    ADR-WEB-COMPONENT-FAMILY-TAXONOMY (docs/architecture/decisions/) the
    explicit 17-member enumeration is normative and the 14/16 prose totals
    are treated as editorial inconsistencies. This is the enum future catalog
    and compatibility work MUST use.
    """

    NAV = "nav"
    HERO = "hero"
    DIRECTORY = "directory"
    LISTING = "listing"
    PROFILE = "profile"
    TRUST = "trust"
    CTA = "cta"
    CONTENT = "content"
    SEO = "seo"
    MONETIZATION = "monetization"
    SOCIAL = "social"
    COMMERCE = "commerce"
    FORM = "form"
    STATUS = "status"
    LEGAL = "legal"
    LAYOUT = "layout"
    ATOM = "atom"


class PageRole(str, Enum):
    """The eighteen directory page roles (AES-WEB-002 §6.1).

    ``SiteArchitecture`` assigns exactly one role per page; a component's
    ``supported_page_roles`` declares which roles may host it.
    """

    HOME = "home"
    CATEGORY = "category"
    CITY = "city"
    CITY_CATEGORY = "city-category"
    SEARCH_RESULTS = "search-results"
    BUSINESS_PROFILE = "business-profile"
    COMPARISON = "comparison"
    BEST_OF = "best-of"
    EDITORIAL_GUIDE = "editorial-guide"
    COLLECTION = "collection"
    SERVICE_AREA = "service-area"
    LEAD_GEN_LANDING = "lead-gen-landing"
    CLAIM_LISTING = "claim-listing"
    SPONSOR_PAGE = "sponsor-page"
    SUBMISSION = "submission"
    CORRECTION = "correction"
    VERIFICATION = "verification"
    REGIONAL_HUB = "regional-hub"


class RegionKind(str, Enum):
    """Page composition regions (AES-WEB-002 §9.1)."""

    SKIP = "SKIP"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    HEADER = "HEADER"
    BREADCRUMB = "BREADCRUMB"
    HERO = "HERO"
    BODY = "BODY"
    STICKY_MOBILE = "STICKY_MOBILE"
    FOOTER = "FOOTER"


class CommercialPurpose(str, Enum):
    """Closed set of component commercial purposes (AES-WEB-002 §2.1)."""

    ORIENT = "ORIENT"
    COMMUNICATE_VALUE = "COMMUNICATE_VALUE"
    ESTABLISH_TRUST = "ESTABLISH_TRUST"
    SUPPORT_DISCOVERY = "SUPPORT_DISCOVERY"
    REDUCE_UNCERTAINTY = "REDUCE_UNCERTAINTY"
    CREATE_LEGITIMATE_URGENCY = "CREATE_LEGITIMATE_URGENCY"
    COLLECT_LEAD = "COLLECT_LEAD"
    DRIVE_CALL = "DRIVE_CALL"
    SUPPORT_COMPARISON = "SUPPORT_COMPARISON"
    EXPOSE_INVENTORY = "EXPOSE_INVENTORY"
    STRENGTHEN_INTERNAL_LINKING = "STRENGTHEN_INTERNAL_LINKING"
    SUPPORT_LOCAL_SEO = "SUPPORT_LOCAL_SEO"
    IMPROVE_ACCESSIBILITY = "IMPROVE_ACCESSIBILITY"
    INCREASE_ENGAGEMENT = "INCREASE_ENGAGEMENT"
    PREPARE_MONETIZATION = "PREPARE_MONETIZATION"
    IMPROVE_CONVERSION = "IMPROVE_CONVERSION"
    ENCOURAGE_CLAIM = "ENCOURAGE_CLAIM"
    ENCOURAGE_SPONSORSHIP = "ENCOURAGE_SPONSORSHIP"
    ENCOURAGE_SUBMISSION = "ENCOURAGE_SUBMISSION"
    SATISFY_LEGAL = "SATISFY_LEGAL"
    SYSTEM_STATUS = "SYSTEM_STATUS"


class LifecycleStatus(str, Enum):
    """Component lifecycle states (AES-WEB-002 §23, closed enum)."""

    PROPOSED = "PROPOSED"
    EXPERIMENTAL = "EXPERIMENTAL"
    ACTIVE = "ACTIVE"
    PREFERRED = "PREFERRED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"
    BLOCKED = "BLOCKED"


class ListingKind(str, Enum):
    """Listing-kind semantics carried on listing content blocks (§6.3)."""

    ORGANIC = "ORGANIC"
    FEATURED = "FEATURED"
    SPONSORED = "SPONSORED"
    VERIFIED = "VERIFIED"
    EDITORIAL_PICK = "EDITORIAL_PICK"
    RANKED = "RANKED"
    CURATED = "CURATED"
    RECENTLY_ADDED = "RECENTLY_ADDED"
    INCOMPLETE = "INCOMPLETE"


class ConversionGoal(str, Enum):
    """Closed set of conversion goals (AES-WEB-002 §16.2)."""

    PHONE_CALL = "PHONE_CALL"
    EMAIL = "EMAIL"
    QUOTE_REQUEST = "QUOTE_REQUEST"
    BOOKING = "BOOKING"
    LISTING_CLAIM = "LISTING_CLAIM"
    LISTING_SUBMISSION = "LISTING_SUBMISSION"
    NEWSLETTER_SIGNUP = "NEWSLETTER_SIGNUP"
    SPONSORSHIP_INQUIRY = "SPONSORSHIP_INQUIRY"
    PAID_UPGRADE = "PAID_UPGRADE"
    AFFILIATE_CLICK = "AFFILIATE_CLICK"
    PURCHASE = "PURCHASE"
    COMPARE = "COMPARE"
    SAVE = "SAVE"
    SHARE = "SHARE"
    CORRECTION_REQUEST = "CORRECTION_REQUEST"
    PROFILE_COMPLETION = "PROFILE_COMPLETION"


class AssetRole(str, Enum):
    """Asset roles a component may consume (AES-WEB-002 §3, §10.2)."""

    LOGO = "LOGO"
    HERO_IMAGE = "HERO_IMAGE"
    GALLERY_IMAGE = "GALLERY_IMAGE"
    ICON = "ICON"


class PropType(str, Enum):
    """Closed set of prop types (AES-WEB-002 §8.1).

    There is deliberately no free-form ``STR`` prop type — human-readable
    text is content and belongs in a slot, not a prop.
    """

    STR_ENUM = "STR_ENUM"
    INT_BOUNDED = "INT_BOUNDED"
    BOOL = "BOOL"
    TOKEN_REF = "TOKEN_REF"
    ASSET_REF = "ASSET_REF"
    ROUTE_REF = "ROUTE_REF"
    CONTENT_BLOCK_REF = "CONTENT_BLOCK_REF"
    LISTING_REF = "LISTING_REF"
    COLLECTION_REF = "COLLECTION_REF"
    ANALYTICS_LABEL = "ANALYTICS_LABEL"
    A11Y_LABEL = "A11Y_LABEL"


class SlotCardinality(str, Enum):
    """Content-slot cardinality (AES-WEB-002 §8.2)."""

    EXACTLY_ONE = "exactly_one"
    ZERO_OR_ONE = "zero_or_one"
    ONE_TO_N = "one_to_n"


class SemanticElement(str, Enum):
    """Root element / landmark a component emits (AES-WEB-002 §3)."""

    SECTION = "section"
    NAV = "nav"
    HEADER = "header"
    FOOTER = "footer"
    ASIDE = "aside"
    ARTICLE = "article"
    FORM = "form"
    DIV = "div"

"""AES-DATA-001 Official URL Importer -- centralized vocabulary and caps.

Every stable slug, cap, and enum used across the importer lives here so no
module invents ad hoc strings (mission section 31). Pure data only -- no I/O,
no network, no third-party imports.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Versions (recorded in every candidate for replay; mission section 6/23).
# --------------------------------------------------------------------------- #

EXTRACTION_VERSION = "1.0.0"          # deterministic snapshot+pipeline revision
PROMPT_VERSION = "1.0.0"              # LLM prompt/schema revision
IMPORTER_VERSION = "1.1.0"            # AES-DATA-002A: additive multi-source contracts
AGGREGATION_VERSION = "1.0.0"         # source-set aggregation schema revision


# --------------------------------------------------------------------------- #
# Caps and limits (mission sections 5/6/11/26).
# --------------------------------------------------------------------------- #

NORMALIZED_TEXT_CAP_BYTES = 50 * 1024        # 50 KB of UTF-8 normalized text
EVIDENCE_QUOTE_CAP = 300                      # chars per evidence snippet
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 3 * 1024 * 1024          # 3 MB decompressed body cap
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 15
LLM_MAX_TOKENS = 2048
LLM_MALFORMED_RETRIES = 1                     # one retry only
MAX_AGGREGATE_SOURCES = 4                     # AES-DATA-002 source-set cap

USER_AGENT = "AtlasImporter/1.0 (+https://pettripfinder.com; official-source importer)"


# --------------------------------------------------------------------------- #
# Fetch / content policy.
# --------------------------------------------------------------------------- #

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})          # plus scheme-default (None)
HTML_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})
PDF_CONTENT_TYPE = "application/pdf"


# --------------------------------------------------------------------------- #
# Category slugs (map importer category -> launch-package category slug).
# --------------------------------------------------------------------------- #

CATEGORY_HOTELS = "hotels"
CATEGORY_PARKS = "parks"
CATEGORY_RESTAURANTS = "restaurants"
IMPORTER_CATEGORIES = (CATEGORY_HOTELS, CATEGORY_PARKS, CATEGORY_RESTAURANTS)

CATEGORY_SLUG_BY_IMPORTER = {
    CATEGORY_HOTELS: "pet-friendly-hotels",
    CATEGORY_PARKS: "pet-friendly-parks",
    CATEGORY_RESTAURANTS: "pet-friendly-restaurants",
}


# --------------------------------------------------------------------------- #
# The production seed CSV schema (exact 15 columns; mission section 21).
# --------------------------------------------------------------------------- #

SEED_CSV_COLUMNS = (
    "name", "category", "address", "city", "state", "postal_code", "phone",
    "website_url", "source_url", "source_type", "observed_at", "rating",
    "amenities", "pet_policy", "canonical",
)


# --------------------------------------------------------------------------- #
# Support states, extraction methods, recommendation, review status.
# --------------------------------------------------------------------------- #

SUPPORT_SUPPORTED = "SUPPORTED"
SUPPORT_AMBIGUOUS = "AMBIGUOUS"
SUPPORT_UNSUPPORTED = "UNSUPPORTED"
SUPPORT_STATES = frozenset({SUPPORT_SUPPORTED, SUPPORT_AMBIGUOUS, SUPPORT_UNSUPPORTED})

METHOD_JSON_LD = "JSON_LD"
METHOD_MICRODATA = "MICRODATA"
METHOD_META = "META"
METHOD_OPEN_GRAPH = "OPEN_GRAPH"
METHOD_TEL_LINK = "TEL_LINK"
METHOD_ADDRESS_BLOCK = "ADDRESS_BLOCK"
METHOD_LLM_TEXT = "LLM_TEXT"
METHOD_OPERATOR_EDIT = "OPERATOR_EDIT"
EXTRACTION_METHODS = frozenset({
    METHOD_JSON_LD, METHOD_MICRODATA, METHOD_META, METHOD_OPEN_GRAPH,
    METHOD_TEL_LINK, METHOD_ADDRESS_BLOCK, METHOD_LLM_TEXT, METHOD_OPERATOR_EDIT,
})

RECOMMEND_READY = "READY"
RECOMMEND_REVIEW = "REVIEW"
RECOMMEND_REJECT = "REJECT"

REVIEW_PENDING = "PENDING"
REVIEW_APPROVED = "APPROVED"
REVIEW_EDITED_AND_APPROVED = "EDITED_AND_APPROVED"
REVIEW_REJECTED = "REJECTED"
REVIEW_EXPORTED_TO_STAGING = "EXPORTED_TO_STAGING"
REVIEW_PROMOTED = "PROMOTED"
APPROVED_REVIEW_STATES = frozenset({REVIEW_APPROVED, REVIEW_EDITED_AND_APPROVED})


# --------------------------------------------------------------------------- #
# Official-source relationship (mission section 17).
# --------------------------------------------------------------------------- #

REL_EXACT_ENTITY_DOMAIN = "EXACT_ENTITY_DOMAIN"
REL_OFFICIAL_BRAND_DOMAIN = "OFFICIAL_BRAND_DOMAIN"
REL_OFFICIAL_PROPERTY_SUBDOMAIN = "OFFICIAL_PROPERTY_SUBDOMAIN"
REL_OFFICIAL_GOVERNMENT_DOMAIN = "OFFICIAL_GOVERNMENT_DOMAIN"
REL_OFFICIAL_GROUP_DOMAIN = "OFFICIAL_GROUP_DOMAIN"
REL_OFFICIAL_HOSTED_SYSTEM = "OFFICIAL_HOSTED_SYSTEM"
REL_OPERATOR_CONFIRMED_OFFICIAL = "OPERATOR_CONFIRMED_OFFICIAL"
REL_UNKNOWN = "UNKNOWN"
REL_THIRD_PARTY = "THIRD_PARTY"
SOURCE_RELATIONSHIPS = frozenset({
    REL_EXACT_ENTITY_DOMAIN, REL_OFFICIAL_BRAND_DOMAIN,
    REL_OFFICIAL_PROPERTY_SUBDOMAIN, REL_OFFICIAL_GOVERNMENT_DOMAIN,
    REL_OFFICIAL_GROUP_DOMAIN, REL_OFFICIAL_HOSTED_SYSTEM,
    REL_OPERATOR_CONFIRMED_OFFICIAL, REL_UNKNOWN, REL_THIRD_PARTY,
})
# Relationships accepted as official enough to allow a READY candidate.
OFFICIAL_RELATIONSHIPS = frozenset({
    REL_EXACT_ENTITY_DOMAIN, REL_OFFICIAL_BRAND_DOMAIN,
    REL_OFFICIAL_PROPERTY_SUBDOMAIN, REL_OFFICIAL_GOVERNMENT_DOMAIN,
    REL_OFFICIAL_GROUP_DOMAIN, REL_OFFICIAL_HOSTED_SYSTEM,
    REL_OPERATOR_CONFIRMED_OFFICIAL,
})
# Known third-party discovery hosts that can never be a publication authority.
THIRD_PARTY_HOST_MARKERS = (
    "yelp.", "tripadvisor.", "bringfido.", "google.", "facebook.", "instagram.",
    "booking.", "expedia.", "reddit.", "opentable.", "petswelcome.", "allstays.",
)


# --------------------------------------------------------------------------- #
# Source roles (AES-DATA-002; additive). Deterministically assigned by
# supply order -- never operator-supplied, never model-proposed. Not yet
# consumed by any aggregation logic in this phase.
# --------------------------------------------------------------------------- #

SOURCE_ROLE_PRIMARY = "PRIMARY"
SOURCE_ROLE_SUPPLEMENTAL = "SUPPLEMENTAL"


# --------------------------------------------------------------------------- #
# Failure / condition reason slugs (mission section 31). Centralized set.
# --------------------------------------------------------------------------- #

REASON_UNSAFE_URL = "unsafe_url"
REASON_UNSAFE_HOST = "unsafe_host"
REASON_UNSAFE_REDIRECT = "unsafe_redirect"
REASON_INVALID_SCHEME = "invalid_scheme"
REASON_INVALID_PORT = "invalid_port"
REASON_DNS_RESOLUTION_FAILED = "dns_resolution_failed"
REASON_FETCH_TIMEOUT = "fetch_timeout"
REASON_REDIRECT_LIMIT = "redirect_limit"
REASON_BLOCKED_SOURCE = "blocked_source"
REASON_RATE_LIMITED_SOURCE = "rate_limited_source"
REASON_FETCH_FAILED = "fetch_failed"
REASON_OVERSIZED_RESPONSE = "oversized_response"
REASON_UNSUPPORTED_CONTENT_TYPE = "unsupported_content_type"
REASON_PDF_SOURCE = "pdf_source"
REASON_JAVASCRIPT_RENDERED = "javascript_rendered"
REASON_MALFORMED_HTML = "malformed_html"
REASON_MULTI_ENTITY = "multi_entity"
REASON_ENTITY_MISMATCH = "entity_mismatch"
REASON_NO_PET_EVIDENCE = "no_pet_evidence"
REASON_NO_PETS = "no_pets"
REASON_EXTRACTION_UNPARSEABLE = "extraction_unparseable"
REASON_EVIDENCE_MISMATCH = "evidence_mismatch"
REASON_UNSUPPORTED_FIELD = "unsupported_field"
REASON_CONFLICTING_EVIDENCE = "conflicting_evidence"
REASON_MISSING_REQUIRED_FIELD = "missing_required_field"
REASON_UNCERTAIN_SOURCE_RELATIONSHIP = "uncertain_source_relationship"
REASON_DUPLICATE_CANDIDATE = "duplicate_candidate"
REASON_DUPLICATE_INVENTORY_ROW = "duplicate_inventory_row"
REASON_STAGING_VALIDATION_FAILED = "staging_validation_failed"
REASON_PROMOTION_CONFIRMATION_REQUIRED = "promotion_confirmation_required"

# AES-DATA-002 multi-source aggregation reason slugs. The first four are
# aggregate-level recommendation reasons (AES-DATA-002A registered them;
# AES-DATA-002B is the first phase to emit them). The next three are
# per-source SourceRecord.excluded_reason values (AES-DATA-002B) -- distinct
# from the aggregate reasons because a SourceRecord names WHY that one
# source was dropped, not why the whole candidate needs review.
REASON_IDENTITY_CONFLICT = "identity_conflict"
REASON_GEOGRAPHY_CONFLICT = "geography_conflict"
REASON_POLICY_CONFLICT = "policy_conflict"
REASON_INCOMPLETE_SOURCE_SET = "incomplete_source_set"
REASON_DUPLICATE_SOURCE_URL = "duplicate_source_url"
REASON_DIFFERENT_REGISTRABLE_DOMAIN = "different_registrable_domain"
REASON_THIRD_PARTY_SOURCE = "third_party_source"

REASON_SLUGS = frozenset({
    REASON_UNSAFE_URL, REASON_UNSAFE_HOST, REASON_UNSAFE_REDIRECT,
    REASON_INVALID_SCHEME, REASON_INVALID_PORT, REASON_DNS_RESOLUTION_FAILED,
    REASON_FETCH_TIMEOUT, REASON_REDIRECT_LIMIT, REASON_BLOCKED_SOURCE,
    REASON_RATE_LIMITED_SOURCE, REASON_FETCH_FAILED, REASON_OVERSIZED_RESPONSE,
    REASON_UNSUPPORTED_CONTENT_TYPE, REASON_PDF_SOURCE, REASON_JAVASCRIPT_RENDERED,
    REASON_MALFORMED_HTML, REASON_MULTI_ENTITY, REASON_ENTITY_MISMATCH,
    REASON_NO_PET_EVIDENCE, REASON_NO_PETS, REASON_EXTRACTION_UNPARSEABLE,
    REASON_EVIDENCE_MISMATCH, REASON_UNSUPPORTED_FIELD, REASON_CONFLICTING_EVIDENCE,
    REASON_MISSING_REQUIRED_FIELD, REASON_UNCERTAIN_SOURCE_RELATIONSHIP,
    REASON_DUPLICATE_CANDIDATE, REASON_DUPLICATE_INVENTORY_ROW,
    REASON_STAGING_VALIDATION_FAILED, REASON_PROMOTION_CONFIRMATION_REQUIRED,
    REASON_IDENTITY_CONFLICT, REASON_GEOGRAPHY_CONFLICT, REASON_POLICY_CONFLICT,
    REASON_INCOMPLETE_SOURCE_SET, REASON_DUPLICATE_SOURCE_URL,
    REASON_DIFFERENT_REGISTRABLE_DOMAIN, REASON_THIRD_PARTY_SOURCE,
})

# Reasons that force a candidate to REVIEW vs REJECT (recommendation logic).
REVIEW_FETCH_REASONS = frozenset({
    REASON_BLOCKED_SOURCE, REASON_RATE_LIMITED_SOURCE, REASON_PDF_SOURCE,
    REASON_JAVASCRIPT_RENDERED,
})
REJECT_FETCH_REASONS = frozenset({
    REASON_UNSAFE_URL, REASON_UNSAFE_HOST, REASON_UNSAFE_REDIRECT,
    REASON_INVALID_SCHEME, REASON_INVALID_PORT, REASON_DNS_RESOLUTION_FAILED,
    REASON_FETCH_TIMEOUT, REASON_REDIRECT_LIMIT, REASON_FETCH_FAILED,
    REASON_OVERSIZED_RESPONSE, REASON_UNSUPPORTED_CONTENT_TYPE,
})


# --------------------------------------------------------------------------- #
# Default gitignored output roots (data/ is gitignored repo-wide).
# --------------------------------------------------------------------------- #

DEFAULT_OUTPUT_ROOT = "data/import"
CAS_SUBDIR = "cas"
CANDIDATES_SUBDIR = "candidates"
REPORTS_SUBDIR = "reports"
STAGING_CSV_NAME = "approved_candidates.csv"
STAGING_AUDIT_NAME = "approved_candidates_audit.jsonl"
REJECTIONS_NAME = "rejections.jsonl"

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"


# --------------------------------------------------------------------------- #
# AES-WORK-001A -- batch import queue: contracts, manifest, and identity.
# Additive only; no existing constant above is changed.
# --------------------------------------------------------------------------- #

BATCHES_SUBDIR = "batches"
MAX_BATCH_WORKERS = 4
BATCH_MANIFEST_SCHEMA_VERSION = "1.0"
BATCH_STATE_VERSION = "1.0"
BATCH_REPORT_VERSION = "1.0"

REASON_DUPLICATE_JOB_ID = "duplicate_job_id"
REASON_INVALID_JOB = "invalid_job"
REASON_UNSAFE_MANIFEST_PATH = "unsafe_manifest_path"
REASON_INVALID_BATCH_ID = "invalid_batch_id"

BATCH_REASON_SLUGS = frozenset({
    REASON_DUPLICATE_JOB_ID, REASON_INVALID_JOB, REASON_UNSAFE_MANIFEST_PATH,
    REASON_INVALID_BATCH_ID,
})
REASON_SLUGS = REASON_SLUGS | BATCH_REASON_SLUGS

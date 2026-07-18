"""AES-DATA-004A discovery -- centralized vocabulary and caps.

Mirrors ``scripts.pettripfinder.importer.constants``'s convention: plain
string module-level constants (not ``Enum`` classes) with ``frozenset``
validation groupings. Pure data only -- no I/O, no network, no third-party
imports.
"""

from __future__ import annotations

DISCOVERY_VERSION = "1.0.0"


# --------------------------------------------------------------------------- #
# Providers (Task 1). Foursquare is a reserved identifier -- no working
# client ships in this phase (mission Task 5).
# --------------------------------------------------------------------------- #

PROVIDER_GOOGLE_PLACES = "GOOGLE_PLACES"
PROVIDER_OPENSTREETMAP = "OPENSTREETMAP"
PROVIDER_FOURSQUARE = "FOURSQUARE"
DISCOVERY_PROVIDERS = frozenset({
    PROVIDER_GOOGLE_PLACES, PROVIDER_OPENSTREETMAP, PROVIDER_FOURSQUARE,
})
# Providers with a working live client in this phase.
IMPLEMENTED_PROVIDERS = frozenset({PROVIDER_GOOGLE_PLACES, PROVIDER_OPENSTREETMAP})


# --------------------------------------------------------------------------- #
# Canonical discovery categories (Task 1). Deliberately NOT the same set as
# scripts.pettripfinder.importer.constants.IMPORTER_CATEGORIES -- discovery
# categories describe *search intent* against third-party providers, and a
# single discovery category can later fan into an importer category plus a
# capability (e.g. discovery's "emergency_veterinary" query results still
# land in the importer's single "veterinary" category, with emergency
# service proven or not as a capability -- discovery never asserts it).
# Do not force these into importer semantics (mission Task 1).
# --------------------------------------------------------------------------- #

CATEGORY_HOTEL = "hotel"
CATEGORY_MOTEL = "motel"
CATEGORY_VETERINARY = "veterinary"
CATEGORY_EMERGENCY_VETERINARY = "emergency_veterinary"
CATEGORY_BOARDING = "boarding"
CATEGORY_DAYCARE = "daycare"
CATEGORY_GROOMING = "grooming"
CATEGORY_PET_STORE = "pet_store"
CATEGORY_DOG_PARK = "dog_park"
CATEGORY_PARK = "park"
CATEGORY_TRAIL = "trail"
CATEGORY_RESTAURANT = "restaurant"
CATEGORY_ATTRACTION = "attraction"

DISCOVERY_CATEGORIES = (
    CATEGORY_HOTEL, CATEGORY_MOTEL, CATEGORY_VETERINARY,
    CATEGORY_EMERGENCY_VETERINARY, CATEGORY_BOARDING, CATEGORY_DAYCARE,
    CATEGORY_GROOMING, CATEGORY_PET_STORE, CATEGORY_DOG_PARK, CATEGORY_PARK,
    CATEGORY_TRAIL, CATEGORY_RESTAURANT, CATEGORY_ATTRACTION,
)
DISCOVERY_CATEGORY_SET = frozenset(DISCOVERY_CATEGORIES)


# --------------------------------------------------------------------------- #
# Website resolution states (Task 10).
# --------------------------------------------------------------------------- #

WEBSITE_STATE_OFFICIAL_PRESENT = "OFFICIAL_WEBSITE_PRESENT"
WEBSITE_STATE_MISSING = "WEBSITE_MISSING"
WEBSITE_STATE_AMBIGUOUS = "WEBSITE_AMBIGUOUS"
WEBSITE_STATE_PROVIDER_URL_ONLY = "PROVIDER_URL_ONLY"
WEBSITE_STATE_CONFLICTING = "CONFLICTING_WEBSITES"
WEBSITE_STATES = frozenset({
    WEBSITE_STATE_OFFICIAL_PRESENT, WEBSITE_STATE_MISSING,
    WEBSITE_STATE_AMBIGUOUS, WEBSITE_STATE_PROVIDER_URL_ONLY,
    WEBSITE_STATE_CONFLICTING,
})

# Registrable domains that are never an "official website" even when a
# provider supplies them as the business's website/url field (mission
# Task 10: "obvious social/directory domain exclusion").
NON_OFFICIAL_DOMAINS = frozenset({
    "facebook.com", "instagram.com", "twitter.com", "x.com", "yelp.com",
    "foursquare.com", "tripadvisor.com", "linkedin.com", "yellowpages.com",
    "bbb.org", "nextdoor.com", "google.com", "goo.gl", "maps.google.com",
    "booking.com", "expedia.com", "opentable.com", "doordash.com",
    "grubhub.com", "ubereats.com", "bringfido.com",
})


# --------------------------------------------------------------------------- #
# Record eligibility (Task 1 DiscoveryRecord.eligibility_state).
# --------------------------------------------------------------------------- #

ELIGIBILITY_ELIGIBLE = "ELIGIBLE"
ELIGIBILITY_OUT_OF_MARKET_BOUNDS = "OUT_OF_MARKET_BOUNDS"
ELIGIBILITY_MISSING_IDENTITY = "MISSING_IDENTITY"
ELIGIBILITY_PERMANENTLY_CLOSED = "PERMANENTLY_CLOSED"
ELIGIBILITY_STATES = frozenset({
    ELIGIBILITY_ELIGIBLE, ELIGIBILITY_OUT_OF_MARKET_BOUNDS,
    ELIGIBILITY_MISSING_IDENTITY, ELIGIBILITY_PERMANENTLY_CLOSED,
})


# --------------------------------------------------------------------------- #
# Merge reasons / candidate review state (Task 9).
# --------------------------------------------------------------------------- #

MERGE_REASON_SAME_PROVIDER_ID = "same_provider_id"
MERGE_REASON_SAME_ADDRESS = "same_normalized_address"
MERGE_REASON_PHONE_PLUS_NAME = "phone_plus_compatible_name"
MERGE_REASON_DOMAIN_PLUS_NAME_PLUS_ADDRESS = "domain_plus_name_plus_address"
MERGE_REASON_COORDS_PLUS_NAME_PLUS_ADDRESS = "coords_plus_name_plus_address"
MERGE_REASONS = frozenset({
    MERGE_REASON_SAME_PROVIDER_ID, MERGE_REASON_SAME_ADDRESS,
    MERGE_REASON_PHONE_PLUS_NAME, MERGE_REASON_DOMAIN_PLUS_NAME_PLUS_ADDRESS,
    MERGE_REASON_COORDS_PLUS_NAME_PLUS_ADDRESS,
})

CONFLICT_ADDRESS_MISMATCH = "conflicting_address"
CONFLICT_CATEGORY_MISMATCH = "conflicting_category"
CONFLICT_WEBSITE_MISMATCH = "conflicting_website"

REVIEW_STATE_SINGLE_SOURCE = "SINGLE_SOURCE"
REVIEW_STATE_AUTO_MERGED = "AUTO_MERGED"
REVIEW_STATE_NEEDS_REVIEW = "NEEDS_REVIEW"
REVIEW_STATES = frozenset({
    REVIEW_STATE_SINGLE_SOURCE, REVIEW_STATE_AUTO_MERGED,
    REVIEW_STATE_NEEDS_REVIEW,
})


# --------------------------------------------------------------------------- #
# Query / provider execution state (Task 6/11).
# --------------------------------------------------------------------------- #

QUERY_STATE_PLANNED = "PLANNED"
QUERY_STATE_COMPLETED = "COMPLETED"
QUERY_STATE_FAILED = "FAILED"
QUERY_STATE_SKIPPED_NO_CREDENTIAL = "SKIPPED_NO_CREDENTIAL"
QUERY_STATE_SKIPPED_CAP_REACHED = "SKIPPED_CAP_REACHED"
QUERY_STATE_DISABLED = "DISABLED"
QUERY_STATES = frozenset({
    QUERY_STATE_PLANNED, QUERY_STATE_COMPLETED, QUERY_STATE_FAILED,
    QUERY_STATE_SKIPPED_NO_CREDENTIAL, QUERY_STATE_SKIPPED_CAP_REACHED,
    QUERY_STATE_DISABLED,
})

PROVIDER_ERROR_AUTH = "provider_auth_failed"
PROVIDER_ERROR_RATE_LIMITED = "provider_rate_limited"
PROVIDER_ERROR_TIMEOUT = "provider_timeout"
PROVIDER_ERROR_TRANSIENT = "provider_transient_error"
PROVIDER_ERROR_INVALID_REQUEST = "provider_invalid_request"
PROVIDER_ERROR_UNAVAILABLE = "provider_unavailable"
PROVIDER_ERROR_OVERSIZED_RESPONSE = "provider_oversized_response"
PROVIDER_ERRORS = frozenset({
    PROVIDER_ERROR_AUTH, PROVIDER_ERROR_RATE_LIMITED, PROVIDER_ERROR_TIMEOUT,
    PROVIDER_ERROR_TRANSIENT, PROVIDER_ERROR_INVALID_REQUEST,
    PROVIDER_ERROR_UNAVAILABLE, PROVIDER_ERROR_OVERSIZED_RESPONSE,
})


# --------------------------------------------------------------------------- #
# Network / request caps.
# --------------------------------------------------------------------------- #

CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 3 * 1024 * 1024

# Google Places API (New) -- https://places.googleapis.com/v1/places:searchText
# (POST, header auth). Mirrors the existing repo convention already used by
# services/opportunity_v2/google_places_business_data_source.py and
# services/connectors/google_connector.py -- both already converged on this
# endpoint/auth style; the discovery client reuses the same env var name
# (GOOGLE_PLACES_API_KEY) and header-based auth for consistency.
GOOGLE_PLACES_API_KEY_ENV = "GOOGLE_PLACES_API_KEY"
GOOGLE_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PAGE_SIZE = 20
GOOGLE_MAX_RETRIES = 2                 # transient (5xx/timeout) only
GOOGLE_RETRY_BACKOFF_SECONDS = 0.5
# Minimum field mask for discovery identity + website-readiness classification.
# Deliberately excludes rating/userRatingCount/priceLevel/photos/reviews/
# openingHours/editorialSummary -- Atlas never treats Google ratings/hours as
# verified facts (doctrine #1/#3), so there is no reason to pay for them here.
GOOGLE_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.addressComponents",
    "places.location",
    "places.primaryType",
    "places.types",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.businessStatus",
])
GOOGLE_USER_AGENT = "AtlasDiscovery/1.0 (+https://pettripfinder.com; market-discovery)"

# OpenStreetMap / Overpass -- no credential; public fair-use etiquette caps
# usage well under the documented 10,000 req/day, 1 GB/day guideline
# (https://dev.overpass-api.de/overpass-doc/en/preface/commons.html).
OVERPASS_DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"
OVERPASS_USER_AGENT = "AtlasDiscovery/1.0 (+https://pettripfinder.com; discovery-research; contact-repo-owner)"
OVERPASS_QL_TIMEOUT_SECONDS = 25       # server-side [timeout:N] directive
OVERPASS_CLIENT_TIMEOUT_SECONDS = 30   # client-side HTTP read timeout
OVERPASS_MAX_RETRIES = 1               # transient only; public server, be gentle
OVERPASS_ATTRIBUTION = "© OpenStreetMap contributors (ODbL) -- www.openstreetmap.org/copyright"
OVERPASS_RETRY_BACKOFF_SECONDS = 1.0
MAX_OVERPASS_ELEMENTS_PER_QUERY = 500  # defensive cap; truncates with a disclosed warning

FOURSQUARE_API_KEY_ENV = "FOURSQUARE_API_KEY"

# Google Places caching policy (mission Task 7/doctrine #17): the Place ID is
# the only field Google's terms exempt from caching restrictions outright;
# every other field (name/address/phone/website/coordinates) is subject to a
# documented 30-day-maximum temporary-cache exception for coordinates and no
# stated long-term retention allowance for the rest
# (https://developers.google.com/maps/documentation/places/web-service/policies,
# https://cloud.google.com/maps-platform/terms/). Discovery therefore treats
# every non-place_id Google field as a temporary research signal that expires
# and must be re-verified through the official website (the doctrine's actual
# factual authority) before any long-lived use -- never redistributed,
# published, or promoted to inventory directly from provider data.
GOOGLE_CACHE_RETENTION_DAYS = 30

DEFAULT_DISCOVERY_ROOT = "data/discovery"
CACHE_SUBDIR = "cache"
CANDIDATES_SUBDIR = "candidates"
REPORTS_SUBDIR = "reports"

DEFAULT_MAX_PAGES_PER_QUERY = 1
DEFAULT_MAX_GOOGLE_REQUESTS = 0        # explicit opt-in required at CLI/runner
DEFAULT_MAX_OVERPASS_REQUESTS = 0      # explicit opt-in required at CLI/runner

# --------------------------------------------------------------------------- #
# Deduplication (Task 9).
# --------------------------------------------------------------------------- #

DEDUP_COORD_PROXIMITY_METERS = 150.0
# Provider trust/priority order for picking a candidate's display fields
# when multiple source records disagree cosmetically -- Google Places is the
# mission's designated primary business-discovery source.
PROVIDER_PRIORITY = (PROVIDER_GOOGLE_PLACES, PROVIDER_OPENSTREETMAP, PROVIDER_FOURSQUARE)

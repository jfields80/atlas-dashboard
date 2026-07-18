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
# AES-DATA-004B Phase 4: same address, materially different names (a
# rebrand, or two distinct tenants sharing one street address) -- flagged,
# never silently merged.
CONFLICT_NAME_MISMATCH = "conflicting_name"

# --------------------------------------------------------------------------- #
# Import-planning next actions (AES-DATA-004B Phase 10). Deterministic,
# priority-ordered classification of what should happen to a candidate
# next -- never a verified fact, never a pet-friendliness claim.
# --------------------------------------------------------------------------- #

NEXT_ACTION_EXCLUDE_CLOSED = "EXCLUDE_CLOSED"
NEXT_ACTION_REVIEW_OUT_OF_SCOPE = "REVIEW_OUT_OF_SCOPE"
NEXT_ACTION_REVIEW_IDENTITY = "REVIEW_IDENTITY"
NEXT_ACTION_REVIEW_CONFLICTING_WEBSITE = "REVIEW_CONFLICTING_WEBSITE"
NEXT_ACTION_RESOLVE_OFFICIAL_WEBSITE = "RESOLVE_OFFICIAL_WEBSITE"
NEXT_ACTION_MISSING_WEBSITE = "MISSING_WEBSITE"
NEXT_ACTION_READY_FOR_OFFICIAL_SITE_IMPORT = "READY_FOR_OFFICIAL_SITE_IMPORT"
NEXT_ACTIONS = frozenset({
    NEXT_ACTION_EXCLUDE_CLOSED, NEXT_ACTION_REVIEW_OUT_OF_SCOPE,
    NEXT_ACTION_REVIEW_IDENTITY, NEXT_ACTION_REVIEW_CONFLICTING_WEBSITE,
    NEXT_ACTION_RESOLVE_OFFICIAL_WEBSITE, NEXT_ACTION_MISSING_WEBSITE,
    NEXT_ACTION_READY_FOR_OFFICIAL_SITE_IMPORT,
})

# AES-DATA-004B Phase 5: a resolved OFFICIAL_WEBSITE_PRESENT URL has not
# been fetched or verified as THIS property's specific page (vs. a chain
# homepage, booking redirect, franchise-management page, or third-party
# booking page) -- syntax/domain classification only, disclosed rather than
# silently assumed location-specific.
WARNING_LOCATION_PAGE_UNVERIFIED = "location_page_unverified"

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

# --------------------------------------------------------------------------- #
# Query-yield/saturation reporting (AES-DATA-004B Phase 3). A query
# returning the provider's per-page maximum is only POTENTIALLY saturated
# (more may exist beyond the cap) -- never treated as proof of completeness.
# --------------------------------------------------------------------------- #

YIELD_SATURATION_NOT_SATURATED = "NOT_SATURATED"
YIELD_SATURATION_POTENTIAL = "POTENTIALLY_SATURATED"
YIELD_SATURATION_TRUNCATED = "TRUNCATED_BY_ELEMENT_CAP"
YIELD_CACHE_HIT = "CACHE_HIT"
YIELD_LIVE_CALL = "LIVE_CALL"
YIELD_DISABLED = "DISABLED"
YIELD_SKIPPED = "SKIPPED"
# Provider trust/priority order for picking a candidate's display fields
# when multiple source records disagree cosmetically -- Google Places is the
# mission's designated primary business-discovery source.
PROVIDER_PRIORITY = (PROVIDER_GOOGLE_PLACES, PROVIDER_OPENSTREETMAP, PROVIDER_FOURSQUARE)


# =========================================================================== #
# AES-DATA-004C -- lodging scope cleanup and official-website resolution.
# =========================================================================== #

# --------------------------------------------------------------------------- #
# Task 1: lodging scope classification.
# --------------------------------------------------------------------------- #

SCOPE_IN_SCOPE = "IN_SCOPE"
SCOPE_BORDERLINE = "BORDERLINE_SCOPE"
SCOPE_OUT_OF_SCOPE = "OUT_OF_SCOPE"
SCOPE_UNKNOWN = "UNKNOWN_SCOPE"
SCOPE_STATES = frozenset({SCOPE_IN_SCOPE, SCOPE_BORDERLINE, SCOPE_OUT_OF_SCOPE, SCOPE_UNKNOWN})
# Fraction of the market bounding box's own extent used to build a
# "borderline" buffer around it -- a candidate just outside the strict
# bounds but within this buffer is BORDERLINE, not OUT_OF_SCOPE outright.
SCOPE_BORDERLINE_BUFFER_FRACTION = 0.25

# --------------------------------------------------------------------------- #
# Task 3: identity-conflict resolution outcomes.
# --------------------------------------------------------------------------- #

IDENTITY_SAME_LOCATION_CURRENT_NAME = "SAME_LOCATION_CURRENT_NAME"
IDENTITY_DISTINCT_LOCATIONS = "DISTINCT_LOCATIONS"
IDENTITY_POSSIBLE_REBRAND = "POSSIBLE_REBRAND"
IDENTITY_SHARED_COMPLEX_DISTINCT_PROPERTIES = "SHARED_COMPLEX_DISTINCT_PROPERTIES"
IDENTITY_DIFFERENT_ENTITY = "DIFFERENT_ENTITY"
IDENTITY_UNRESOLVED = "UNRESOLVED_IDENTITY"
IDENTITY_OUTCOMES = frozenset({
    IDENTITY_SAME_LOCATION_CURRENT_NAME, IDENTITY_DISTINCT_LOCATIONS,
    IDENTITY_POSSIBLE_REBRAND, IDENTITY_SHARED_COMPLEX_DISTINCT_PROPERTIES,
    IDENTITY_DIFFERENT_ENTITY, IDENTITY_UNRESOLVED,
})
# Deterministic, disclosed, non-exhaustive keyword/token lists used only to
# distinguish non-lodging entities (restaurant/conference center) sharing an
# address with a real lodging candidate, and to recognize a shared parent
# hotel-brand family (e.g. "Residence Inn by Marriott" vs "Marriott") when
# two DIFFERENT bookable brand-lines occupy one development. Never used to
# merge -- only to classify an already-unmerged conflict pair.
IDENTITY_RESTAURANT_KEYWORDS = frozenset({
    "restaurant", "bar", "grill", "cafe", "bistro", "pub", "kitchen", "diner",
    "steakhouse", "tavern", "brewery", "eatery",
})
IDENTITY_CONFERENCE_KEYWORDS = frozenset({"conference", "convention", "banquet"})
IDENTITY_HOTEL_BRAND_FAMILY_TOKENS = frozenset({
    "marriott", "hilton", "hyatt", "ihg", "wyndham", "choice", "bestwestern",
    "radisson", "accor", "redroof", "extendedstay", "sonesta", "wyndhamhotels",
})

# --------------------------------------------------------------------------- #
# Task 4: official-website resolution states.
# --------------------------------------------------------------------------- #

WEBSITE_RES_PROPERTY_URL_CONFIRMED = "PROPERTY_OFFICIAL_URL_CONFIRMED"
WEBSITE_RES_PROPERTY_URL_PROBABLE = "PROPERTY_OFFICIAL_URL_PROBABLE"
WEBSITE_RES_CHAIN_HOMEPAGE_ONLY = "CHAIN_HOMEPAGE_ONLY"
WEBSITE_RES_BRAND_LOCATION_SEARCH_ONLY = "BRAND_LOCATION_SEARCH_ONLY"
WEBSITE_RES_MANAGEMENT_COMPANY_PAGE = "MANAGEMENT_COMPANY_PAGE"
WEBSITE_RES_THIRD_PARTY_BOOKING_URL = "THIRD_PARTY_BOOKING_URL"
WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL = "SOCIAL_OR_DIRECTORY_URL"
WEBSITE_RES_MISSING = "WEBSITE_MISSING"
WEBSITE_RES_CONFLICTING_URLS = "CONFLICTING_OFFICIAL_URLS"
WEBSITE_RES_FETCH_BLOCKED = "FETCH_BLOCKED"
WEBSITE_RES_UNRESOLVED = "UNRESOLVED"
WEBSITE_RESOLUTION_STATES = frozenset({
    WEBSITE_RES_PROPERTY_URL_CONFIRMED, WEBSITE_RES_PROPERTY_URL_PROBABLE,
    WEBSITE_RES_CHAIN_HOMEPAGE_ONLY, WEBSITE_RES_BRAND_LOCATION_SEARCH_ONLY,
    WEBSITE_RES_MANAGEMENT_COMPANY_PAGE, WEBSITE_RES_THIRD_PARTY_BOOKING_URL,
    WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL, WEBSITE_RES_MISSING,
    WEBSITE_RES_CONFLICTING_URLS, WEBSITE_RES_FETCH_BLOCKED, WEBSITE_RES_UNRESOLVED,
})
# States a static (no-fetch) classification is allowed to reach on its own --
# CONFIRMED and MANAGEMENT_COMPANY_PAGE (an accepted-with-provenance state)
# require an actual fetch (Task 5: "do not call a URL confirmed merely from
# path syntax").
STATIC_REACHABLE_WEBSITE_STATES = frozenset({
    WEBSITE_RES_PROPERTY_URL_PROBABLE, WEBSITE_RES_CHAIN_HOMEPAGE_ONLY,
    WEBSITE_RES_BRAND_LOCATION_SEARCH_ONLY, WEBSITE_RES_THIRD_PARTY_BOOKING_URL,
    WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL, WEBSITE_RES_MISSING, WEBSITE_RES_UNRESOLVED,
})

# --------------------------------------------------------------------------- #
# Task 5: static URL classification -- domain lists.
#
# Reconciled, disclosed union of discovery's own NON_OFFICIAL_DOMAINS (exact
# registrable-domain matching) plus the importer's independently-maintained
# THIRD_PARTY_HOST_MARKERS substring list (constants.py:
# scripts.pettripfinder.importer -- reddit., petswelcome., allstays. were
# present there but not here). The importer module itself is NOT modified;
# this is only a same-spirit addition on the discovery side.
# --------------------------------------------------------------------------- #

THIRD_PARTY_BOOKING_DOMAINS = frozenset({
    "booking.com", "expedia.com", "hotels.com", "priceline.com", "trivago.com",
    "kayak.com", "orbitz.com", "travelocity.com", "agoda.com", "hotwire.com",
})
SOCIAL_OR_DIRECTORY_DOMAINS = frozenset({
    "facebook.com", "instagram.com", "twitter.com", "x.com", "yelp.com",
    "foursquare.com", "tripadvisor.com", "linkedin.com", "yellowpages.com",
    "bbb.org", "nextdoor.com", "google.com", "goo.gl", "maps.google.com",
    "opentable.com", "doordash.com", "grubhub.com", "ubereats.com",
    "bringfido.com", "reddit.com", "petswelcome.com", "allstays.com",
})
URL_SHORTENER_DOMAINS = frozenset({
    "bit.ly", "tinyurl.com", "t.co", "ow.ly", "buff.ly", "is.gd",
})
# Well-known major hotel-brand corporate domains (public, non-exhaustive,
# general knowledge -- never used to fabricate a property URL, only to
# distinguish "this is a big multi-property chain domain" from "this is
# probably an independent single-property domain" during static
# classification; doctrine #7 -- never invent an official website).
KNOWN_CHAIN_BRAND_DOMAINS = frozenset({
    "marriott.com", "hilton.com", "hyatt.com", "ihg.com", "wyndhamhotels.com",
    "choicehotels.com", "bestwestern.com", "redroof.com",
    "extendedstayamerica.com", "sonesta.com", "radisson.com", "accor.com",
    "laquinta.com", "motel6.com", "super8.com", "daysinn.com",
    "econolodge.com", "ramada.com", "travelodge.com", "qualityinn.com",
    "comfortinn.com", "holidayinn.com",
})
# Path fragments suggesting a brand-wide locator/search page rather than one
# specific property.
BRAND_LOCATOR_PATH_HINTS = frozenset({
    "locations", "search", "find-a-hotel", "find-hotels", "hotel-search",
})
# Third-party property-MANAGEMENT platforms (distinct from pure booking
# aggregators like Booking.com/Expedia, which list any hotel regardless of
# relationship) -- these operate/franchise the specific properties they
# list, so a page here can carry real property-specific identity (Task 8:
# "A management-company property page may be accepted when it clearly
# identifies the selected hotel and address, but must retain
# MANAGEMENT_COMPANY_PAGE provenance"). Found live during Wave 1 resolution
# (oyorooms.com used by Google Places as the "official" website for at
# least 2 independent budget properties) -- disclosed, minimal, expand only
# on further confirmed evidence, never guessed.
PROPERTY_MANAGEMENT_DOMAINS = frozenset({"oyorooms.com"})

# --------------------------------------------------------------------------- #
# Task 6/14: fetch-plan ceilings (absolute ceilings, not targets).
# --------------------------------------------------------------------------- #

RESOLUTION_MAX_HTTP_REQUESTS = 40
RESOLUTION_MAX_REQUESTS_PER_CANDIDATE = 2
RESOLUTION_MAX_REQUESTS_PER_DOMAIN = 4
RESOLUTION_MIN_DOMAIN_PACING_SECONDS = 1.0

# --------------------------------------------------------------------------- #
# Task 9: missing-website next actions.
# --------------------------------------------------------------------------- #

MISSING_ACTION_RESOLVE_FROM_BRAND_LOCATOR = "RESOLVE_FROM_BRAND_LOCATOR"
MISSING_ACTION_RESOLVE_FROM_MANAGEMENT_COMPANY = "RESOLVE_FROM_MANAGEMENT_COMPANY"
MISSING_ACTION_MANUAL_REVIEW = "MANUAL_REVIEW"
MISSING_ACTION_NO_OFFICIAL_SITE_FOUND = "NO_OFFICIAL_SITE_FOUND"
MISSING_ACTION_CLOSED_OR_REBRANDED_REVIEW = "CLOSED_OR_REBRANDED_REVIEW"
MISSING_ACTION_OUT_OF_SCOPE = "OUT_OF_SCOPE"
MISSING_ACTION_DEFER_LOW_PRIORITY = "DEFER_LOW_PRIORITY"
MISSING_WEBSITE_ACTIONS = frozenset({
    MISSING_ACTION_RESOLVE_FROM_BRAND_LOCATOR, MISSING_ACTION_RESOLVE_FROM_MANAGEMENT_COMPANY,
    MISSING_ACTION_MANUAL_REVIEW, MISSING_ACTION_NO_OFFICIAL_SITE_FOUND,
    MISSING_ACTION_CLOSED_OR_REBRANDED_REVIEW, MISSING_ACTION_OUT_OF_SCOPE,
    MISSING_ACTION_DEFER_LOW_PRIORITY,
})

# --------------------------------------------------------------------------- #
# Task 10: final resolution / import-eligibility outcomes.
# --------------------------------------------------------------------------- #

RESOLUTION_READY_FOR_PET_POLICY_IMPORT = "READY_FOR_PET_POLICY_IMPORT"
RESOLUTION_READY_WITH_BRAND_SUPPLEMENT = "READY_WITH_BRAND_SUPPLEMENT"
RESOLUTION_REVIEW_IDENTITY = "REVIEW_IDENTITY"
RESOLUTION_REVIEW_WEBSITE = "REVIEW_WEBSITE"
RESOLUTION_MISSING_OFFICIAL_WEBSITE = "MISSING_OFFICIAL_WEBSITE"
RESOLUTION_EXCLUDE_OUT_OF_SCOPE = "EXCLUDE_OUT_OF_SCOPE"
RESOLUTION_EXCLUDE_CLOSED = "EXCLUDE_CLOSED"
RESOLUTION_DEFER = "DEFER"
RESOLUTION_OUTCOMES = frozenset({
    RESOLUTION_READY_FOR_PET_POLICY_IMPORT, RESOLUTION_READY_WITH_BRAND_SUPPLEMENT,
    RESOLUTION_REVIEW_IDENTITY, RESOLUTION_REVIEW_WEBSITE,
    RESOLUTION_MISSING_OFFICIAL_WEBSITE, RESOLUTION_EXCLUDE_OUT_OF_SCOPE,
    RESOLUTION_EXCLUDE_CLOSED, RESOLUTION_DEFER,
})
RESOLUTION_ELIGIBLE_FOR_BATCH = frozenset({
    RESOLUTION_READY_FOR_PET_POLICY_IMPORT, RESOLUTION_READY_WITH_BRAND_SUPPLEMENT,
})

# --------------------------------------------------------------------------- #
# Task 11: import-batch generation (mirrors the importer's own BatchJob
# schema exactly -- scripts.pettripfinder.importer.batch.BatchJob -- so
# generated manifests are consumable by scripts/run_import_batch.py
# unmodified in a later phase; not executed in this phase).
# --------------------------------------------------------------------------- #

IMPORTER_CATEGORY_HOTELS = "hotels"     # the importer has no separate "motels" category
RESOLUTION_MAX_JOBS_PER_BATCH = 20
RESOLUTION_MANIFEST_SCHEMA_VERSION = "1.0"

# --------------------------------------------------------------------------- #
# Task 9: name-token recognition for missing-website categorization.
# Deliberately broader than IDENTITY_HOTEL_BRAND_FAMILY_TOKENS (which is
# narrowly scoped to the shared-complex identity heuristic) -- this list
# recognizes common major chain/sub-brand NAME words (not domains) so a
# missing-website candidate that is obviously chain-branded can be queued
# for a brand-locator lookup in a later phase rather than manual research
# now. Disclosed, non-exhaustive, public general knowledge only.
# --------------------------------------------------------------------------- #

MISSING_WEBSITE_CHAIN_NAME_TOKENS = frozenset({
    "marriott", "hilton", "hyatt", "wyndham", "choice", "bestwestern", "best",
    "redroof", "extendedstay", "sonesta", "radisson", "hampton", "holiday",
    "comfort", "quality", "days", "super8", "motel6", "laquinta", "ramada",
    "travelodge", "econolodge", "baymont", "americinn", "candlewood",
    "staybridge", "homewood", "home2", "towneplace", "residence", "fairfield",
    "springhill", "courtyard", "aloft", "sheraton", "westin", "doubletree",
    "embassy", "tru", "even", "avid", "microtel", "knightsinn", "wingate",
})

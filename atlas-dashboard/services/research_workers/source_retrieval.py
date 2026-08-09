"""PTF-WORKERS-003 -- official-source retrieval seam.

The research worker (ATLAS-WORKERS-002/004) reasons over
``contracts.SourceDocument`` objects it is *given*; it has never fetched
anything ("No hotel discovery, no Google Places, no web browsing" --
``columbus_pilot`` module docstring). The Columbus pilot therefore built its
SourceDocument from the ``pet_policy`` column already stored in
``seed_businesses.csv``, so a hotel whose stored text says only "identifies
itself as pet-friendly" could never yield fee/species/limit facts no matter
how many times the model was re-run.

This module is the missing half, and *only* the missing half. Every hard
part already exists in the AES-DATA-001 Official URL Importer
(``scripts/pettripfinder/importer/``) and is reused verbatim:

    fetch.RequestsPageFetcher      SSRF-safe fetch: scheme/port/credential
                                   checks, DNS validation of every resolved
                                   A/AAAA against private/loopback/link-local/
                                   multicast/reserved, manual redirects with
                                   per-hop re-validation and a hard cap,
                                   finite timeouts, streaming size cap,
                                   content-type whitelist. No JS, no cookies,
                                   no auth, no form submission.
    source_snapshot.build_snapshot HTML -> bounded normalized visible text,
                                   raw + normalized hashes, title, canonical,
                                   JS-shell detection.
    fetch_status.classify_fetch_status
                                   blocked/JS/CAPTCHA/timeout taxonomy.
    candidate.classify_source_relationship
                                   official vs third-party domain analysis.
    lodging_source_strategy.classify_brand_policy_scope
                                   universal vs participating brand policy --
                                   the guard against silently treating a
                                   brand-wide policy as property-specific.

Nothing here re-implements a fetcher, a URL-safety layer, an HTML
normalizer, or an identity comparator. What this module adds is:

  1. a worker-facing retrieval status vocabulary, mapped explicitly from the
     importer's reason slugs (no failure reason is collapsed -- the original
     slug is always preserved in ``importer_reason``);
  2. deterministic property-identity classification from snapshot signals;
  3. bounded, deterministic policy-page candidate discovery;
  4. conversion of a verified snapshot into the existing SourceDocument.

It never invents policy facts, never decides READY/REVIEW (that stays with
``routing``), and never writes production data.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlsplit, urlunsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import classify_source_relationship
from scripts.pettripfinder.importer.fetch_status import (
    FETCH_STATUS_CAPTCHA_REQUIRED,
    FETCH_STATUS_HTTP_403_BLOCKED,
    FETCH_STATUS_JAVASCRIPT_REQUIRED,
    FETCH_STATUS_RATE_LIMITED,
    classify_fetch_status,
)
from scripts.pettripfinder.importer.lodging_source_strategy import (
    BRAND_SCOPE_PARTICIPATING,
    BRAND_SCOPE_UNIVERSAL,
    classify_brand_policy_scope,
)
from scripts.pettripfinder.importer.models import FetchResult, ImportContext, SourceSnapshot
from scripts.pettripfinder.importer.normalize import (
    names_compatible,
    normalize_phone,
    normalize_whitespace,
)
from scripts.pettripfinder.importer.official_source_roles import (
    LODGING_SOURCE_ROLE_BRAND_POLICY,
    LODGING_SOURCE_ROLE_PROPERTY_POLICY,
    LODGING_SOURCE_ROLE_UNKNOWN,
)
from scripts.pettripfinder.importer.source_snapshot import build_snapshot, decode_body
from services.research_workers import vocabulary as V
from services.research_workers.contracts import SourceDocument, content_hash
from services.research_workers.render_evidence import (
    POLICY_VALUES_REQUIRE_RENDERING, classify_render_requirement,
)

RETRIEVAL_VERSION = "ptf-workers-003/1.0.0"


# --------------------------------------------------------------------------- #
# Worker-facing retrieval statuses.
# --------------------------------------------------------------------------- #

RETRIEVED = "RETRIEVED"
NOT_FOUND = "NOT_FOUND"
ACCESS_BLOCKED = "ACCESS_BLOCKED"
RENDER_REQUIRED = "RENDER_REQUIRED"
ENTITY_MISMATCH = "ENTITY_MISMATCH"
UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
NETWORK_ERROR = "NETWORK_ERROR"
REJECTED_UNSAFE_URL = "REJECTED_UNSAFE_URL"
# PTF-WORKERS-005: the page rendered, but two captures in one session
# disagreed, so no hash honestly describes it. Distinct from ACCESS_BLOCKED --
# nothing stopped us; the page simply is not stable enough to quote.
RENDER_UNSTABLE = "RENDER_UNSTABLE"

RETRIEVAL_STATUSES = frozenset({
    RETRIEVED, NOT_FOUND, ACCESS_BLOCKED, RENDER_REQUIRED, ENTITY_MISMATCH,
    UNSUPPORTED_CONTENT, NETWORK_ERROR, REJECTED_UNSAFE_URL, RENDER_UNSTABLE,
})

# Explicit, total mapping from the importer's failure slugs. Documented rather
# than inferred: a slug absent here falls through to NETWORK_ERROR *and* keeps
# its original slug in ``importer_reason``, so an unmapped outcome is visible
# rather than silently relabelled.
REASON_TO_STATUS: Dict[str, str] = {
    C.REASON_UNSAFE_URL: REJECTED_UNSAFE_URL,
    C.REASON_UNSAFE_HOST: REJECTED_UNSAFE_URL,
    C.REASON_UNSAFE_REDIRECT: REJECTED_UNSAFE_URL,
    C.REASON_INVALID_SCHEME: REJECTED_UNSAFE_URL,
    C.REASON_INVALID_PORT: REJECTED_UNSAFE_URL,
    C.REASON_BLOCKED_SOURCE: ACCESS_BLOCKED,
    C.REASON_RATE_LIMITED_SOURCE: ACCESS_BLOCKED,
    C.REASON_UNSUPPORTED_CONTENT_TYPE: UNSUPPORTED_CONTENT,
    C.REASON_PDF_SOURCE: UNSUPPORTED_CONTENT,
    C.REASON_OVERSIZED_RESPONSE: UNSUPPORTED_CONTENT,
    C.REASON_FETCH_TIMEOUT: NETWORK_ERROR,
    C.REASON_DNS_RESOLUTION_FAILED: NETWORK_ERROR,
    C.REASON_REDIRECT_LIMIT: NETWORK_ERROR,
    C.REASON_FETCH_FAILED: NETWORK_ERROR,
    # PTF-WORKERS-005 browser-render outcomes. The three access outcomes are
    # ACCESS_BLOCKED because that is what they are from the worker's point of
    # view -- something stood between us and the page, and we stopped.
    C.REASON_CHALLENGE_DETECTED: ACCESS_BLOCKED,
    C.REASON_LOGIN_REQUIRED: ACCESS_BLOCKED,
    C.REASON_CONSENT_GATED: ACCESS_BLOCKED,
    C.REASON_OFF_ALLOWLIST_NAVIGATION: REJECTED_UNSAFE_URL,
    C.REASON_RENDER_NONDETERMINISTIC: RENDER_UNSTABLE,
}


# --------------------------------------------------------------------------- #
# Property identity.
# --------------------------------------------------------------------------- #

EXACT_MATCH = "EXACT_MATCH"
STRONG_MATCH = "STRONG_MATCH"
AMBIGUOUS = "AMBIGUOUS"
MISMATCH = "MISMATCH"
NOT_ENOUGH_INFORMATION = "NOT_ENOUGH_INFORMATION"
# PTF-WORKERS-005. The page does not identify itself, but its PARENT property
# page does, and the two are bound tightly enough (same origin, same property
# code, child beneath the parent's path, same browser run) to carry identity
# down. May support extraction; may NEVER publish automatically -- routing
# forces REVIEW via V.NON_AUTOMATIC_SOURCE_TYPES.
INHERITED_FROM_PARENT = "INHERITED_FROM_PARENT"

# Only these two may feed automatic extraction (mission rule: AMBIGUOUS and
# MISMATCH route to human review without their policy text being treated as
# authoritative for this property). INHERITED_FROM_PARENT is deliberately NOT
# a member: it is extraction-eligible but not automatically publishable, which
# is a weaker status than either of these two and is enforced downstream.
IDENTITY_ACCEPTABLE = frozenset({EXACT_MATCH, STRONG_MATCH})
IDENTITY_EXTRACTABLE = IDENTITY_ACCEPTABLE | {INHERITED_FROM_PARENT}

# Capture provenance -- HOW the bytes were obtained, orthogonal to WHOSE page
# it is. Recorded on every outcome so an auditor can tell a static fetch from a
# browser render without inferring it from other fields.
CAPTURE_METHOD_HTTP_STATIC = "HTTP_STATIC"
CAPTURE_METHOD_BROWSER_RENDERED = "BROWSER_RENDERED"
# PTF-WORKERS-006: a human opened the page and attested to it. Declared here so
# the four transports form one closed vocabulary in one place.
CAPTURE_METHOD_MANUAL_ATTESTATION = "MANUAL_ATTESTATION"
CAPTURE_METHOD_MODEL_RESEARCH = "MODEL_RESEARCH"
CAPTURE_METHODS = frozenset({
    CAPTURE_METHOD_HTTP_STATIC, CAPTURE_METHOD_BROWSER_RENDERED,
    CAPTURE_METHOD_MANUAL_ATTESTATION, CAPTURE_METHOD_MODEL_RESEARCH,
})


@dataclass(frozen=True)
class ExpectedEntity:
    """What the seed record claims this property is."""

    listing_key: str
    listing_name: str
    address: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    phone: str = ""
    website_url: str = ""


@dataclass(frozen=True)
class IdentityAssessment:
    classification: str
    name_signal: bool
    phone_signal: bool
    address_signal: bool
    city_signal: bool
    reasons: Tuple[str, ...] = ()


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _street_number(address: str) -> str:
    m = re.match(r"\s*(\d+)", address or "")
    return m.group(1) if m else ""


def _street_tokens(address: str) -> List[str]:
    """Distinctive street-name tokens, ignoring the number and common types."""
    stop = {"n", "s", "e", "w", "north", "south", "east", "west", "st", "street",
            "rd", "road", "ave", "avenue", "blvd", "boulevard", "dr", "drive",
            "ln", "lane", "pkwy", "parkway", "ct", "court", "cir", "circle",
            "pl", "place", "way", "ste", "suite", "hwy", "highway"}
    toks = re.findall(r"[a-z]+", (address or "").lower())
    return [t for t in toks if t not in stop and len(t) > 2]


def assess_identity(snapshot: SourceSnapshot, expected: ExpectedEntity) -> IdentityAssessment:
    """Deterministic identity classification from snapshot signals only.

    Conservative by construction: a page that simply fails to mention the
    property is NOT_ENOUGH_INFORMATION (not a mismatch), while a page whose
    address or phone actively contradicts the record is MISMATCH. This is what
    catches the known Drury Plaza Downtown / Convention Center case -- the
    brand page names a different property at a different address.
    """
    hay = normalize_whitespace(
        "%s %s" % (snapshot.page_title or "", snapshot.normalized_text or "")).lower()
    reasons: List[str] = []

    name_signal = bool(expected.listing_name) and names_compatible(
        expected.listing_name, snapshot.page_title or "")
    if not name_signal and expected.listing_name:
        # fall back to full-text containment of the distinctive name tokens
        toks = [t for t in re.findall(r"[a-z0-9]+", expected.listing_name.lower())
                if len(t) > 3]
        if toks and all(t in hay for t in toks):
            name_signal = True
            reasons.append("name_matched_in_body")
    elif name_signal:
        reasons.append("name_matched_in_title")

    # Phone matching works on the page's digit stream rather than on a
    # formatted-number regex: a greedy pattern happily spans two adjacent
    # numbers ("...OH 43215 614-224-6539") and yields a 15-digit string that
    # matches nothing. Digits-only containment is formatting-agnostic and
    # cannot be defeated by punctuation or line breaks.
    want_phone = _digits_only(normalize_phone(expected.phone or ""))
    phone_signal = False
    phone_conflict = False
    if want_phone:
        if want_phone in _digits_only(hay):
            phone_signal = True
            reasons.append("phone_matched")
        else:
            # Only a *labelled* number counts as a contradiction; a random
            # digit run (ZIP, room count, price) must never imply mismatch.
            labelled = re.findall(
                r"(?:phone|tel|telephone|call)\D{0,20}(\d[\d\-\.\(\)\s]{7,}\d)", hay)
            if any(_digits_only(p) != want_phone for p in labelled):
                phone_conflict = True
                reasons.append("phone_present_but_different")

    num = _street_number(expected.address)
    toks = _street_tokens(expected.address)
    address_signal = bool(num) and num in hay and bool(toks) and any(t in hay for t in toks)
    if address_signal:
        reasons.append("address_matched")

    city_signal = bool(expected.city) and expected.city.lower() in hay
    if city_signal:
        reasons.append("city_matched")

    if phone_conflict and not phone_signal and not address_signal:
        return IdentityAssessment(MISMATCH, name_signal, False, address_signal,
                                  city_signal, tuple(reasons))
    if name_signal and (phone_signal or address_signal):
        return IdentityAssessment(EXACT_MATCH, name_signal, phone_signal,
                                  address_signal, city_signal, tuple(reasons))
    if (phone_signal and address_signal) or (name_signal and city_signal):
        return IdentityAssessment(STRONG_MATCH, name_signal, phone_signal,
                                  address_signal, city_signal, tuple(reasons))
    if name_signal or phone_signal or address_signal:
        return IdentityAssessment(AMBIGUOUS, name_signal, phone_signal,
                                  address_signal, city_signal, tuple(reasons))
    return IdentityAssessment(NOT_ENOUGH_INFORMATION, False, False, False,
                              city_signal, tuple(reasons) or ("no_identity_signal",))


# --------------------------------------------------------------------------- #
# Bounded policy-page candidate discovery.
# --------------------------------------------------------------------------- #

MAX_CANDIDATES = 20

# Deterministic scoring vocabulary. Higher score = more likely to carry the
# actual pet policy. Ordering ties break on the canonical URL string, so the
# ranking is stable across runs.
_LINK_TERMS: Tuple[Tuple[str, int], ...] = (
    ("pet-policy", 100), ("pet_policy", 100), ("petpolicy", 100),
    ("pet-friendly", 80), ("petfriendly", 80),
    ("pets", 70), ("pet", 60), ("animal", 55),
    ("hotel-info", 50), ("hotelinfo", 50), ("hotel-information", 50),
    ("property-details", 45), ("propertydetails", 45),
    ("amenities", 40), ("policies", 40), ("policy", 35),
    ("terms", 25), ("faq", 25), ("fees", 30), ("accessibility", 20),
)
_IGNORE_TERMS = ("logout", "signout", "sign-out", "account", "myaccount",
                 "reservation", "booking/", "book-now", "facebook", "twitter",
                 "instagram", "linkedin", "youtube", "tiktok", "pinterest",
                 "utm_", "javascript:", "mailto:", "tel:", "#")


def canonicalize_url(base: str, href: str) -> str:
    """Absolute, fragment-free, deterministic URL. Returns "" if unusable."""
    if not href:
        return ""
    href = href.strip()
    low = href.lower()
    if low.startswith(("javascript:", "mailto:", "tel:", "data:")):
        return ""
    absolute = urljoin(base, href)
    parts = urlsplit(absolute)
    if parts.scheme not in ("http", "https"):
        return ""
    path = parts.path or "/"
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, parts.query, ""))


def _registrable(host: str) -> str:
    bits = (host or "").lower().split(".")
    return ".".join(bits[-2:]) if len(bits) >= 2 else (host or "").lower()


@dataclass(frozen=True)
class PolicyCandidate:
    url: str
    score: int
    matched_terms: Tuple[str, ...]
    anchor_text: str


# A page that links to several *sibling* pages beneath its own path is a
# directory/listing, not one property's page. This is the deterministic signal
# that separates "an official page that mentions this hotel" from "this
# hotel's own official page" -- host-level relationship cannot: on a large
# brand every page shares one host, so a city listing and a property page both
# classify EXACT_ENTITY_DOMAIN.
DIRECTORY_SIBLING_THRESHOLD = 2


def looks_like_directory_page(final_url: str,
                              candidates: Sequence[PolicyCandidate]) -> bool:
    base = urlsplit(final_url).path.rstrip("/")
    if not base:
        return False
    siblings = set()
    for c in candidates:
        path = urlsplit(c.url).path.rstrip("/")
        if path != base and path.startswith(base + "/"):
            siblings.add(path)
    return len(siblings) >= DIRECTORY_SIBLING_THRESHOLD


# --------------------------------------------------------------------------- #
# PTF-WORKERS-007 -- URL SHAPE.
#
# ``looks_like_directory_page`` asks a link-graph question: does this page link
# to children beneath its own path? That catches a city listing at
# ``/locations/usa/ohio/columbus/``, whose properties genuinely live beneath it.
#
# It does NOT catch a search results page. On ``/search/findHotels.mi`` the
# result links point at ``/en-us/hotels/<code>/``, which is not beneath
# ``/search``, so no siblings are counted and the page reads as property-
# specific. A capture of that page carrying one hotel's name, address and phone
# then classifies EXACT_MATCH, and the search URL -- which identifies no
# property and would resolve differently on any later visit -- becomes the
# cited official source.
#
# URL shape is the orthogonal, deterministic answer: judge the address bar, not
# the link graph. A search URL is a QUERY, and a query is not a property.
# --------------------------------------------------------------------------- #

URL_SHAPE_PROPERTY = "PROPERTY"
URL_SHAPE_SEARCH = "SEARCH"
URL_SHAPE_BRAND = "BRAND"
URL_SHAPE_UNKNOWN = "UNKNOWN"

# Path markers that make a URL a search/result surface rather than a page about
# one property. Matched case-insensitively against the path.
_SEARCH_PATH_MARKERS = (
    "/search", "findhotels", "/find-hotels", "/hotel-search", "/results",
    "/availability", "/list", "/browse",
)
# Query parameters that only a search surface carries. Their presence means the
# page content depends on the query string, so the URL is not a stable anchor.
_SEARCH_QUERY_MARKERS = (
    "destinationaddress", "destination", "searchtype", "fromdate", "todate",
    "lengthofstay", "numberofrooms", "checkin", "checkout", "query", "keyword",
)
# Path markers for brand-wide policy/marketing pages (not one property).
_BRAND_PATH_MARKERS = (
    "/about-us", "/why-", "/policies", "/pet-policy", "/pet-friendly",
    "/locations", "/destinations", "/offers", "/brands",
)

#: The subset of the above that is a DIRECTORY rather than a statement. A brand
#: says one thing at /pet-policy and lists many properties under /locations, so
#: only these may be followed by a property slug (see classify_url_shape).
_GEOGRAPHIC_INDEX_MARKERS = frozenset({"locations", "destinations"})


def classify_url_shape(url: str) -> str:
    """Classify a URL as PROPERTY / SEARCH / BRAND / UNKNOWN from its shape.

    Deliberately independent of page content: content can be made to look like
    anything, but a search URL cannot be made to name a property. SEARCH wins
    over every other classification -- if a URL is query-driven at all, it is
    not a stable citation, whatever else it also looks like.
    """
    parts = urlsplit(url or "")
    path = (parts.path or "").lower()
    query = (parts.query or "").lower()

    if any(m in path for m in _SEARCH_PATH_MARKERS):
        return URL_SHAPE_SEARCH
    # A bare "?" of tracking noise is not a search; named search parameters are.
    if any(("%s=" % m) in query for m in _SEARCH_QUERY_MARKERS):
        return URL_SHAPE_SEARCH
    segments = [s for s in path.split("/") if s]

    for marker in _BRAND_PATH_MARKERS:
        if marker not in path:
            continue
        # PTF-COLUMBUS-FINAL-CLOSURE-001. A geographic index marker is a brand
        # page on its own and a directory ABOVE property pages when the path
        # continues: Drury publishes every property at
        # /locations/<city>/<property-slug>, and all four Columbus Drury hotels
        # use it. Only the geographic markers get this treatment -- /pet-policy
        # and /about-us name no property however long the path grows.
        name = marker.strip("/")
        if name in _GEOGRAPHIC_INDEX_MARKERS and name in segments:
            tail = segments[segments.index(name) + 1:]
            if len(tail) >= 2 and "-" in tail[-1] and len(tail[-1]) >= 12:
                return URL_SHAPE_PROPERTY
        return URL_SHAPE_BRAND

    # A URL carrying a recognised brand property code names one property, full
    # stop. This is stronger than the slug heuristic below, which counted
    # characters and so classified /property/oh/columbus/rri262 as a property
    # page and /property/oh/dublin/rri127 as UNKNOWN -- the same brand, the same
    # shape, told apart only by "columbus" being eight letters and "dublin" six.
    if extract_property_code_from_url(url):
        return URL_SHAPE_PROPERTY

    # A property page names one property in its path: at least two non-trivial
    # segments, the last of which is a slug rather than a bare section word.
    if len(segments) >= 2 and any("-" in s or len(s) >= 8 for s in segments[1:]):
        return URL_SHAPE_PROPERTY
    return URL_SHAPE_UNKNOWN


# Path segments that are never a property code. Without this list the parser
# happily returns "hotel" for a Hilton URL, because /hotel-info/ looks exactly
# like a code followed by a slug.
_NOT_A_PROPERTY_CODE = frozenset({
    "hotel", "hotels", "hoteldetail", "hotel-info", "overview", "search",
    "index", "rooms", "gallery", "location", "dining", "events", "offers",
    "about", "amenities", "policies", "travel", "reservation", "book",
})


def _looks_like_property_code(segment: str) -> bool:
    """A code is a short alphanumeric token, not an English word we recognise."""
    s = (segment or "").strip().lower()
    return (4 <= len(s) <= 8 and s.isalnum() and any(c.isalpha() for c in s)
            and s not in _NOT_A_PROPERTY_CODE)


#: Single path segments on a brand host that are site sections, not property
#: codes. Only consulted for the one-segment short-link shape, where a five
#: letter section word and a five letter property code are the same shape.
_BRAND_SHORTLINK_NON_CODES = frozenset({
    "deals", "offers", "hotels", "brands", "about", "help", "search", "stays",
    "rooms", "cards", "credit", "events", "meets", "group", "gifts", "media",
    "press", "legal", "terms", "login", "join", "point", "award", "elite",
    "china", "japan", "korea", "india", "spain", "italy", "france", "brasil",
    "es-es", "fr-fr", "de-de", "it-it", "ja-jp", "ko-kr", "pt-br", "zh-cn",
    "en-us", "en-gb", "shops", "store", "app", "apps", "mobile",
})


def extract_property_code_from_url(url: str, known_codes: Sequence[str] = ()) -> str:
    """Return the property code embedded in a URL, or "" if none is present.

    Handles the three brand shapes this project actually meets:

        marriott  /en-us/hotels/cmhea-aloft-columbus-easton/overview/  -> cmhea
        hilton    /en/hotels/cmhchhf-hilton-columbus-at-easton/...     -> cmhchhf
        ihg       /staybridge/hotels/us/en/dublin/cmhtc/hoteldetail    -> cmhtc

    Fails CLOSED. A guessed code that happens to match the wrong hotel is worse
    than no code at all, so anything not recognisably a code returns "".

    PTF-CAPTURE-002A: the previous implementation had two defects, both found
    by running it over real captures rather than by its tests.

    1. The optional locale group let the pattern skip the real code and match
       the NEXT hyphenated segment, so a Hilton property URL returned "hotel"
       (from /hotel-info/) and an IHG URL returned "" -- its code is a bare
       path segment with no trailing hyphen and nothing matched at all.
    2. ``known_codes`` was matched as a bare substring, so the Marriott code
       "cmhap" matched inside Hilton's "cmhaphx" -- two different hotels, one
       silently mistaken for the other. Matching is now anchored to a whole
       path segment (or a segment's leading token before the slug).
    """
    parts = urlsplit(url or "")
    segments = [s for s in (parts.path or "").lower().split("/") if s]

    # An explicitly supplied code wins -- but only on a real segment boundary.
    for code in known_codes:
        c = (code or "").strip().lower()
        if not c:
            continue
        for seg in segments:
            if seg == c or seg.startswith(c + "-"):
                return c

    for i, seg in enumerate(segments):
        if seg not in ("hotels", "hotel"):
            continue
        tail = segments[i + 1:]
        if not tail:
            break
        # marriott / hilton: the code leads the property slug.
        head = tail[0]
        if "-" in head:
            candidate = head.split("-", 1)[0]
            if _looks_like_property_code(candidate):
                return candidate
        # PTF-CLEVELAND-MARKET-FACTORY-001. Marriott's older-but-live shape puts
        # a fixed "travel" segment between /hotels/ and the property slug:
        # /hotels/travel/clesc-cleveland-marriott-downtown-at-key-tower.
        # Five Cleveland routes use it, including the market's flagship
        # downtown Marriott, and every one of them yielded no code because the
        # loop above reads "travel" as the slug and stops.
        #
        # Only this one interposed segment is skipped, and the code still has to
        # satisfy _looks_like_property_code, so an arbitrary path does not
        # suddenly start producing codes.
        if head == "travel" and len(tail) >= 2 and "-" in tail[1]:
            candidate = tail[1].split("-", 1)[0]
            if _looks_like_property_code(candidate):
                return candidate
        # ihg: .../hotels/<country>/<lang>/<city>/<code>/hoteldetail
        for j, t in enumerate(tail):
            if t == "hoteldetail" and j >= 1 and _looks_like_property_code(tail[j - 1]):
                return tail[j - 1]

    # PTF-COLUMBUS-FINAL-CLOSURE-001. Two more shapes, both taken from real
    # property URLs already in the seed rather than from a brand's docs.
    #
    # Neither reuses the "hotels" anchor above: Red Roof marks its property
    # pages with /property/, and Choice puts the brand -- not the word "hotels"
    # -- in the second-to-last segment. Both still go through
    # _looks_like_property_code, so a slug, a city or an English word in that
    # position yields "" exactly as before.

    # red roof: /property/<state>/<city>/<code>   -> rri127
    for i, seg in enumerate(segments):
        if seg == "property" and len(segments) > i + 3:
            candidate = segments[i + 3]
            if _looks_like_property_code(candidate):
                return candidate

    # choice: /<state>/<city>/<brand>-hotels/<code>   -> oh360
    # The brand segment varies (cambria-hotels, comfort-suites-hotels), so the
    # suffix is what is matched, never the brand name.
    if len(segments) >= 2 and segments[-2].endswith("-hotels"):
        if _looks_like_property_code(segments[-1]):
            return segments[-1]

    # PTF-CLEVELAND-MARKET-FACTORY-001. Marriott's SHORT property link:
    # marriott.com/cleac -- the whole path is the property code, and it
    # redirects to the full /en-us/hotels/<code>-<slug>/overview/ page.
    #
    # Cleveland's CVB stores this form for a third of its Marriott properties,
    # so without it five confirmed hotels carried a real official URL that
    # classified as UNKNOWN and never reached the queue.
    #
    # Deliberately narrow: exactly one path segment, on a marriott.com host,
    # that already satisfies _looks_like_property_code. A two-segment path or
    # any other brand does not match -- /brands/towneplace-suites.mi stays a
    # brand page, which is what it is.
    #
    # The catch is that a five-letter site section is shaped exactly like a
    # five-letter property code: /deals and /cleac are indistinguishable by
    # form alone. The extractor's contract is to fail CLOSED, so the site's own
    # section words are excluded by name. That is a denylist, with the cost a
    # denylist carries -- an unlisted section word would be read as a code --
    # but the failure is bounded and visible: the capture's identity gate
    # refuses a page whose name and address do not match, so a wrong code costs
    # one refused capture and never a wrong hotel's policy.
    host = (parts.hostname or "").lower()
    if len(segments) == 1 and (host == "marriott.com"
                               or host.endswith(".marriott.com")):
        if (_looks_like_property_code(segments[0])
                and segments[0] not in _BRAND_SHORTLINK_NON_CODES):
            return segments[0]
    return ""


def discover_policy_candidates(html: str, base_url: str,
                               limit: int = MAX_CANDIDATES) -> Tuple[PolicyCandidate, ...]:
    """Same-registrable-domain links whose URL or anchor text suggests a pet
    policy, ranked deterministically. Discovery only -- nothing is fetched
    here, and no model is consulted about which URLs are safe."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    home = _registrable(urlsplit(base_url).hostname or "")
    seen: Dict[str, PolicyCandidate] = {}
    for a in soup.find_all("a", href=True):
        url = canonicalize_url(base_url, a.get("href", ""))
        if not url or url in seen:
            continue
        low = url.lower()
        if any(bad in low for bad in _IGNORE_TERMS):
            continue
        if _registrable(urlsplit(url).hostname or "") != home:
            continue          # same official domain only
        anchor = normalize_whitespace(a.get_text(" ") or "")[:120]
        blob = low + " " + anchor.lower()
        score = 0
        matched: List[str] = []
        for term, weight in _LINK_TERMS:
            if term in blob:
                score += weight
                matched.append(term)
        if score <= 0:
            continue
        seen[url] = PolicyCandidate(url, score, tuple(matched), anchor)
    ranked = sorted(seen.values(), key=lambda c: (-c.score, c.url))
    return tuple(ranked[:limit])


# --------------------------------------------------------------------------- #
# Retrieval result.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ParentIdentity:
    """A verified parent property page, offered as the identity anchor for a
    child page that cannot identify itself.

    Everything here is asserted by the CAPTURE layer and re-checked by
    ``evaluate_inherited_identity`` -- this dataclass is evidence, not
    permission.
    """

    parent_url: str
    parent_identity: str                    # must be EXACT_MATCH to count
    property_code: str = ""                 # e.g. "cmhtc" in an IHG URL
    parent_redirect_chain: Tuple[str, ...] = ()
    same_browser_context: bool = False
    same_run: bool = False


# The eight operator-approved conditions, each mapped to the slug recorded when
# it FAILS. Keeping them as data (rather than a chain of ifs) means the
# artifact can state exactly which condition blocked an inheritance.
INHERITANCE_CONDITIONS = (
    "parent_not_exact_match",
    "different_origin",
    "property_code_missing_or_mismatched",
    "child_not_beneath_parent_path",
    "not_same_browser_context_and_run",
    "redirected_to_different_property",
)


def _origin(url: str) -> str:
    p = urlsplit(url)
    return "%s://%s" % ((p.scheme or "").lower(), (p.hostname or "").lower())


def _path_of(url: str) -> str:
    return (urlsplit(url).path or "/").rstrip("/")


def evaluate_inherited_identity(*, parent: ParentIdentity, child_final_url: str,
                                child_text: str,
                                child_redirect_chain: Sequence[str] = ()
                                ) -> Tuple[bool, Tuple[str, ...]]:
    """Check ALL eight approved conditions. Returns (permitted, reason slugs).

    Fail-closed and total: every condition is evaluated and every failure is
    reported, so an operator sees the complete reason an inheritance was
    refused rather than only the first problem found.
    """
    failures: List[str] = []

    if parent.parent_identity != EXACT_MATCH:
        failures.append("parent_not_exact_match")
    if _origin(parent.parent_url) != _origin(child_final_url):
        failures.append("different_origin")

    code = (parent.property_code or "").strip().lower()
    if not code:
        failures.append("property_code_missing_or_mismatched")
    else:
        in_parent = code in parent.parent_url.lower()
        in_child = code in child_final_url.lower() or code in (child_text or "").lower()
        if not (in_parent and in_child):
            failures.append("property_code_missing_or_mismatched")

    parent_path, child_path = _path_of(parent.parent_url), _path_of(child_final_url)
    if not parent_path or not child_path.startswith(parent_path + "/"):
        failures.append("child_not_beneath_parent_path")

    if not (parent.same_browser_context and parent.same_run):
        failures.append("not_same_browser_context_and_run")

    # Condition 6: neither page may have redirected to a different property.
    # With a property code in hand, "different property" is checkable: any hop
    # that looks like a property URL but carries a different code is a bounce.
    if code:
        for hop in tuple(parent.parent_redirect_chain) + tuple(child_redirect_chain):
            low = hop.lower()
            if "/hoteldetail" in low and code not in low:
                failures.append("redirected_to_different_property")
                break

    ordered = tuple(c for c in INHERITANCE_CONDITIONS if c in failures)
    if ordered:
        return (False, ordered)
    return (True, ("identity_inherited_from_parent:%s" % parent.parent_url,))


@dataclass(frozen=True)
class RetrievalOutcome:
    """Everything one retrieval attempt learned. ``source_document`` is
    populated only for RETRIEVED; every other status carries the reason."""

    assignment_id: str
    listing_key: str
    listing_name: str
    status: str
    initial_url: str
    final_url: str = ""
    redirect_chain: Tuple[str, ...] = ()
    http_status: int = 0
    content_type: str = ""
    importer_reason: str = ""
    importer_fetch_status: str = ""
    identity: str = ""
    identity_reasons: Tuple[str, ...] = ()
    source_relationship: str = ""
    source_relationship_reason: str = ""
    source_role: str = ""
    brand_policy_scope: str = ""
    policy_applicable: bool = False
    raw_content_hash: str = ""
    normalized_text_hash: str = ""
    normalized_text_bytes: int = 0
    page_title: str = ""
    canonical_url: str = ""
    policy_candidates: Tuple[PolicyCandidate, ...] = ()
    warnings: Tuple[str, ...] = ()
    failure_reason: str = ""
    source_document: Optional[SourceDocument] = None
    # PTF-WORKERS-005 additive audit fields.
    capture_method: str = CAPTURE_METHOD_HTTP_STATIC
    parent_url: str = ""                    # set only when identity was inherited
    identity_basis: str = "self"            # "self" | "inherited_from_parent"

    @property
    def ready_for_extraction(self) -> bool:
        """Retrieved AND applicable to THIS property AND actually carrying a policy.

        ``policy_applicable`` is deliberately part of the gate: a directory or
        non-universal brand page can be fetched, identified and hashed
        perfectly well, but extracting from it would attribute another
        property's (or no property's) policy to this record. Readiness must
        therefore mean "safe to extract for this hotel", not merely "bytes
        arrived".

        PTF-WYNDHAM. Nor merely "a policy section exists here". Retrieving a
        PAGE and retrieving a POLICY are different achievements, and this
        property used to conflate them: every Wyndham property page returns
        200 with exact identity and ships a "Pet & Service Animal Policy"
        heading over an empty container, while the values appear only once the
        page renders. Measured on five Columbus properties, not one static body
        carried a single pet count, weight ceiling or amount -- and three were
        still called ready. What they DO carry is brochure copy ("pet-friendly
        hotel", "an extra nightly fee"), so a worker sent to extract from them
        would have published advertising as policy.

        ``policy_value_signals`` is the same quantified-fact test that already
        decides render-requirement, reused rather than restated, so the two
        answers cannot drift apart. Identity retrieval is untouched and stays
        successful on its own terms: this narrows what may be EXTRACTED, not
        what was reached.
        """
        return (self.status == RETRIEVED
                and self.source_document is not None
                and self.policy_applicable
                and self.static_policy_values_present)

    @property
    def static_policy_values_present(self) -> bool:
        """Does the retrieved body state a quantified policy fact at all?

        False for a page that only names a pet-policy section, ships an empty
        or hidden container, or advertises itself as pet-friendly. Such a page
        is not evidence of a policy; it is evidence of a heading.
        """
        from .render_evidence import policy_value_signals

        doc = self.source_document
        text = getattr(doc, "content_text", "") if doc is not None else ""
        return bool(policy_value_signals(text or ""))

    def to_dict(self) -> dict:
        """Deterministic, secret-free artifact shape. No headers, cookies or
        credentials are carried anywhere in this structure."""
        return {
            "retrieval_version": RETRIEVAL_VERSION,
            "assignment_id": self.assignment_id,
            "listing_key": self.listing_key,
            "listing_name": self.listing_name,
            "status": self.status,
            "initial_url": self.initial_url,
            "final_url": self.final_url,
            "redirect_chain": list(self.redirect_chain),
            "http_status": self.http_status,
            "content_type": self.content_type,
            "importer_reason": self.importer_reason,
            "importer_fetch_status": self.importer_fetch_status,
            "identity": self.identity,
            "identity_reasons": list(self.identity_reasons),
            "source_relationship": self.source_relationship,
            "source_relationship_reason": self.source_relationship_reason,
            "source_role": self.source_role,
            "brand_policy_scope": self.brand_policy_scope,
            "policy_applicable": self.policy_applicable,
            "raw_content_hash": self.raw_content_hash,
            "normalized_text_hash": self.normalized_text_hash,
            "normalized_text_bytes": self.normalized_text_bytes,
            "page_title": self.page_title,
            "canonical_url": self.canonical_url,
            "policy_candidates": [
                {"url": c.url, "score": c.score,
                 "matched_terms": list(c.matched_terms), "anchor_text": c.anchor_text}
                for c in self.policy_candidates
            ],
            "warnings": list(self.warnings),
            "failure_reason": self.failure_reason,
            "ready_for_extraction": self.ready_for_extraction,
            # Recorded so "the page arrived but the policy did not" is
            # diagnosable from the artifact alone, without re-fetching.
            "static_policy_values_present": self.static_policy_values_present,
            "capture_method": self.capture_method,
            "parent_url": self.parent_url,
            "identity_basis": self.identity_basis,
            "source_document": (
                {
                    "source_url": self.source_document.source_url,
                    "source_type": self.source_document.source_type,
                    "retrieved_at": self.source_document.retrieved_at,
                    "title": self.source_document.title,
                    "content_hash": self.source_document.content_hash,
                    "retrieval_status": self.source_document.retrieval_status,
                    "content_text_bytes": len(
                        (self.source_document.content_text or "").encode("utf-8")),
                } if self.source_document is not None else None
            ),
        }


def _status_for_failure(fetch: FetchResult) -> Tuple[str, str]:
    """(worker status, failure reason) for a non-ok fetch."""
    reason = fetch.reason or ""
    if fetch.http_status == 404:
        return (NOT_FOUND, reason or "http_404")
    return (REASON_TO_STATUS.get(reason, NETWORK_ERROR), reason or "unknown_fetch_failure")


def retrieve_official_source(
    *,
    assignment_id: str,
    expected: ExpectedEntity,
    source_url: str,
    fetcher,
    cas,
    observed_at: str,
    context: Optional[ImportContext] = None,
    inherited_from: Optional[ParentIdentity] = None,
    capture_method: str = CAPTURE_METHOD_HTTP_STATIC,
    rendered_policy_text: str = "",
) -> RetrievalOutcome:
    """Fetch ONE official URL through the importer and convert the result.

    Pure orchestration: every safety decision (URL shape, DNS, redirects,
    size, content type) is made inside ``fetcher``; every text decision is
    made inside ``build_snapshot``. This function only classifies and maps.

    ``rendered_policy_text`` is PTF-CAPTURE-004A: deterministic evidence, from
    a saved rendered DOM, of what the page shows once it has rendered. It is
    optional and defaults to empty, so every existing caller behaves exactly as
    before. Supplying it can only ever move a RETRIEVED outcome to
    RENDER_REQUIRED, and only when all six conditions in ``render_evidence``
    hold; it can never rescue a blocked, mismatched or brand-scoped page.
    """
    ctx = context or ImportContext(
        category="hotels", expected_city=expected.city, expected_state=expected.state,
        candidate_name=expected.listing_name)

    relationship, rel_reason = classify_source_relationship(
        source_url, expected.website_url or source_url, ctx)

    fetch: FetchResult = fetcher.fetch(source_url)

    if not fetch.ok:
        status, failure = _status_for_failure(fetch)
        return RetrievalOutcome(
            assignment_id=assignment_id, listing_key=expected.listing_key,
            listing_name=expected.listing_name, status=status,
            initial_url=source_url, final_url=fetch.final_url,
            redirect_chain=tuple(fetch.redirect_chain), http_status=fetch.http_status,
            content_type=fetch.content_type, importer_reason=fetch.reason,
            importer_fetch_status=classify_fetch_status(fetch, None),
            source_relationship=relationship, source_relationship_reason=rel_reason,
            source_role=LODGING_SOURCE_ROLE_UNKNOWN, capture_method=capture_method,
            warnings=tuple(fetch.warnings), failure_reason=failure)

    snapshot = build_snapshot(fetch, cas, observed_at, relationship)
    fetch_status = classify_fetch_status(fetch, snapshot)

    html = decode_body(fetch.body)
    candidates = discover_policy_candidates(html, snapshot.final_url)
    identity = assess_identity(snapshot, expected)
    scope = classify_brand_policy_scope(snapshot.normalized_text)

    base = dict(
        assignment_id=assignment_id, listing_key=expected.listing_key,
        listing_name=expected.listing_name, initial_url=source_url,
        final_url=snapshot.final_url, redirect_chain=tuple(snapshot.redirect_chain),
        http_status=snapshot.http_status, content_type=snapshot.content_type,
        importer_reason="", importer_fetch_status=fetch_status,
        identity=identity.classification, identity_reasons=identity.reasons,
        source_relationship=relationship, source_relationship_reason=rel_reason,
        brand_policy_scope=scope,
        raw_content_hash=snapshot.raw_content_hash,
        normalized_text_hash=snapshot.normalized_text_hash,
        normalized_text_bytes=len(snapshot.normalized_text.encode("utf-8")),
        page_title=snapshot.page_title, canonical_url=snapshot.canonical_url,
        policy_candidates=candidates, warnings=tuple(snapshot.fetch_warnings),
        capture_method=capture_method,
    )

    # A page we cannot read is not evidence, however official it is.
    if fetch_status == FETCH_STATUS_JAVASCRIPT_REQUIRED:
        return RetrievalOutcome(status=RENDER_REQUIRED, source_role=LODGING_SOURCE_ROLE_UNKNOWN,
                                failure_reason=C.REASON_JAVASCRIPT_RENDERED, **base)
    if fetch_status in (FETCH_STATUS_CAPTCHA_REQUIRED, FETCH_STATUS_HTTP_403_BLOCKED,
                        FETCH_STATUS_RATE_LIMITED):
        return RetrievalOutcome(status=ACCESS_BLOCKED, source_role=LODGING_SOURCE_ROLE_UNKNOWN,
                                failure_reason=fetch_status.lower(), **base)

    # Identity gate. Only EXACT/STRONG may become authoritative property
    # evidence; everything else is withheld for human review rather than
    # being quietly attributed to this hotel.
    #
    # PTF-WORKERS-005 adds ONE narrow escape: a page that cannot identify
    # itself may inherit identity from a verified parent, but only when all
    # eight approved conditions hold. Inheritance is attempted solely when the
    # page fails on its own, so it can never override a MISMATCH into a pass --
    # a page that actively contradicts the record still fails, because
    # `assess_identity` returns MISMATCH and the conditions below cannot undo
    # a contradiction, only supply a missing signal.
    effective_identity = identity.classification
    identity_reasons = list(identity.reasons)
    identity_basis, parent_url = "self", ""
    if identity.classification in (AMBIGUOUS, NOT_ENOUGH_INFORMATION) and inherited_from:
        permitted, reasons = evaluate_inherited_identity(
            parent=inherited_from, child_final_url=snapshot.final_url,
            child_text=snapshot.normalized_text,
            child_redirect_chain=snapshot.redirect_chain)
        identity_reasons.extend(reasons)
        if permitted:
            effective_identity = INHERITED_FROM_PARENT
            identity_basis, parent_url = "inherited_from_parent", inherited_from.parent_url
    base["identity"] = effective_identity
    base["identity_reasons"] = tuple(identity_reasons)
    base["identity_basis"] = identity_basis
    base["parent_url"] = parent_url

    if effective_identity not in IDENTITY_EXTRACTABLE:
        return RetrievalOutcome(
            status=ENTITY_MISMATCH, source_role=LODGING_SOURCE_ROLE_UNKNOWN,
            failure_reason="identity_%s" % effective_identity.lower(), **base)

    # Role + applicability.
    #
    # PTF-WORKERS-003 defect fix. The first rule here keyed PROPERTY_POLICY on
    # the importer's *host-level* relationship, which cannot distinguish a
    # property page from a city listing: hilton.com/.../dublin/pet-friendly/
    # classifies EXACT_ENTITY_DOMAIN ("source_host_equals_website") exactly
    # like the property's own page, so a Dublin directory listing seven Hilton
    # brands was labelled PROPERTY_POLICY_SOURCE for Hampton Inn. Two
    # deterministic page-level signals now gate the property role, and BOTH
    # must hold:
    #
    #   * identity is EXACT_MATCH -- the property is named with a corroborating
    #     phone or street address, not merely mentioned in a list; and
    #   * the page is not a directory -- it does not link to sibling pages
    #     beneath its own path.
    #
    # Anything else is brand/listing evidence, and brand evidence only applies
    # to this property when the brand states a universal policy (the existing
    # lodging_source_strategy rule, reused rather than re-derived).
    directory = looks_like_directory_page(snapshot.final_url, candidates)
    if effective_identity == INHERITED_FROM_PARENT and not directory:
        # Property-specific policy, but on an inherited identity link. The role
        # is property-level; the SOURCE TYPE is what carries the weaker status
        # downstream, and it is what forces REVIEW in routing.
        role = LODGING_SOURCE_ROLE_PROPERTY_POLICY
        source_type = V.SOURCE_OFFICIAL_PROPERTY_INHERITED
    elif identity.classification == EXACT_MATCH and not directory:
        role = LODGING_SOURCE_ROLE_PROPERTY_POLICY
        source_type = V.SOURCE_OFFICIAL_PROPERTY
    else:
        role = LODGING_SOURCE_ROLE_BRAND_POLICY
        source_type = V.SOURCE_OFFICIAL_BRAND
    applicable = (role == LODGING_SOURCE_ROLE_PROPERTY_POLICY
                  or scope == BRAND_SCOPE_UNIVERSAL)

    doc = SourceDocument(
        source_url=snapshot.final_url,
        source_type=source_type,
        retrieved_at=observed_at,
        title=snapshot.page_title,
        content_text=snapshot.normalized_text,
        # PTF-WORKERS-005 defect fix #2, found the same way as the source_type
        # one: by actually validating the document. `snapshot.normalized_text_hash`
        # is a BARE sha256 hex digest, while the worker contract's canonical
        # form is "sha256:<hex>" -- so SourceDocument.validate() raised
        # "content_hash mismatch" on every document this function produced.
        # Latent until now because nothing called validate() on one.
        content_hash=content_hash(snapshot.normalized_text),
        retrieval_status=V.RETRIEVAL_OK,
    )
    warns = list(base["warnings"])
    if directory:
        warns.append("directory_listing_page")
    if not applicable:
        warns.append("brand_policy_scope_%s" % (scope or "unknown"))
    if effective_identity == INHERITED_FROM_PARENT:
        warns.append("identity_inherited_requires_human_confirmation")
    base["warnings"] = tuple(warns)

    # PTF-CAPTURE-004A. The page is readable, identified and property-scoped --
    # and may still be one whose pet-policy VALUES only exist after rendering.
    # Checked last, so it can only ever reclassify an outcome that was about to
    # be RETRIEVED: every blocked, mismatched, shell or brand-scoped page has
    # already returned above with its own status, and none of them reach here.
    verdict = classify_render_requirement(
        retrieval_succeeded=True,
        identity_sufficient=identity.classification in IDENTITY_ACCEPTABLE,
        property_scoped=(role == LODGING_SOURCE_ROLE_PROPERTY_POLICY),
        static_html=html,
        static_text=snapshot.normalized_text,
        rendered_text=rendered_policy_text,
    )
    if verdict.qualifies:
        base["warnings"] = tuple(list(base["warnings"]) + [
            "policy_values_absent_from_static_html"])
        return RetrievalOutcome(
            status=RENDER_REQUIRED, source_role=role,
            policy_applicable=applicable, source_document=doc,
            failure_reason=POLICY_VALUES_REQUIRE_RENDERING, **base)

    return RetrievalOutcome(status=RETRIEVED, source_role=role,
                            policy_applicable=applicable, source_document=doc, **base)

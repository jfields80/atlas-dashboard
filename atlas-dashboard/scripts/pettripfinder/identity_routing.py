"""PTF-IDENTITY-ROUTING-P0-001 -- ptf-identity-routing/1.0.

Where an official property endpoint lives for a confirmed hotel identity that
is NOT yet publication inventory.

WHY THIS EXISTS
---------------
The capture ladder needs one thing before it can ask a hotel about itself: the
hotel's own URL. Until now the only place to keep one was
``seed_businesses.csv``, and a seed row is not routing -- it is INVENTORY.
``assemble_netlify_bundle`` derives held hotels as (seed hotels - verified
hotels) and gates that count against the release contract, so adding a
confirmed-but-unpublished identity to the seed changes what the site claims is
held and stops the build. The result was 28 verified URLs with nowhere to live.

This module is the smallest thing that fixes that: a routing record binds an
EXISTING identity to an official endpoint, and nothing else.

WHAT A ROUTING RECORD IS NOT
----------------------------
* Not publication. Nothing in the publication path reads this file -- not the
  generator, not the assembler, not the publication guard -- so a routing
  record cannot create a profile, a route, a sitemap entry or a held-inventory
  count. The tests assert that rather than trusting it.
* Not a second identity system. ``hotel_ref.normalized_name`` + ``market_id``
  is the join key, exactly as everywhere else. No id is minted here.
* Not policy. The membrane refuses a pet-policy field name outright. Knowing
  WHERE to ask is not knowing the answer, and a routing record grants no
  permission to publish, promote, or believe anything about a pet.
* Not a confidence score. ``binding_method`` is categorical and is never
  upgraded because a record became authoritative.

ADAPTED, NOT INVENTED
---------------------
``discovery/url_record.py`` already models an official URL well -- redirect
history, a PASS/FAIL/UNCHECKED identity check, FD-5's 30-day revalidation
cadence, and the rule that two independent stable keys are required and a name
alone never suffices. This contract reuses that vocabulary instead of coining
a parallel one; what it adds is the binding to an identity, and a place to
keep it.

Pure and deterministic: no network, no clock. Reading the committed file is the
only IO.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery.membrane import normalize_field_name  # noqa: E402
from scripts.pettripfinder.discovery.url_record import (                   # noqa: E402
    DEFAULT_REVALIDATION_CADENCE_DAYS,
    IDENTITY_CHECK_VALUES,
    IDENTITY_UNCHECKED,
)
from scripts.pettripfinder.identity_evidence import POLICY_FIELD_NAMES      # noqa: E402
from scripts.pettripfinder.site_data import normalize_name                 # noqa: E402

SCHEMA = "ptf-identity-routing/1.0"
CONTRACT_VERSION = "1.0.0"

ROUTING_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                / "identity_routing.json")

# --------------------------------------------------------------------------- #
# Status vocabulary. Closed.
# --------------------------------------------------------------------------- #

ROUTING_CONFIRMED = "ROUTING_CONFIRMED"   #: identity-bound; the queue may use it
ROUTING_HELD = "ROUTING_HELD"             #: binding too weak to act on
ROUTING_CONFLICT = "ROUTING_CONFLICT"     #: two records disagree; a human decides
ROUTING_STALE = "ROUTING_STALE"           #: past its revalidation horizon

ROUTING_STATUSES = (ROUTING_CONFIRMED, ROUTING_HELD, ROUTING_CONFLICT, ROUTING_STALE)

#: The ONLY status the capture queue may act on. A held, conflicted or stale
#: record is retained and visible -- it is simply not a work instruction.
USABLE_STATUSES = frozenset({ROUTING_CONFIRMED})

#: How identity was bound to the URL. Categorical, and never upgraded merely
#: because the record was written to authority.
BINDING_PAGE_RENDERED = "PAGE_RENDERED"
BINDING_BRAND_INDEX = "BRAND_INDEX_BINDING"
BINDING_METHODS = (BINDING_PAGE_RENDERED, BINDING_BRAND_INDEX)

#: Hosts that can never be an official property endpoint. A third-party page
#: may DISCOVER a URL; it may never BE one. Includes a known-dead franchisee
#: domain that now serves a parking lander while still being indexed with its
#: old hotel content -- exactly the case a naive "it returns 200" check passes.
NEVER_OFFICIAL_DOMAINS = frozenset({
    "booking.com", "expedia.com", "trip.com", "hotels.com", "priceline.com",
    "orbitz.com", "travelocity.com", "hotelplanner.com", "reservations.com",
    "guestreservations.com", "reservationdesk.com", "easemytrip.com",
    "agoda.com", "trivago.com", "hotelguides.com", "room77.com", "yelp.com",
    "tripadvisor.com", "google.com", "maps.apple.com", "waze.com",
    "travelweekly.com", "aaa.com", "foursquare.com", "cvent.com",
    "h-rez.com", "besthotelsohio.com", "columbusohhotel.com",
    "comfortsuitesgrovecity.com",
})

REQUIRED_FIELDS = ("routing_id", "schema_version", "hotel_ref", "market_id",
                   "official_property_url", "official_domain", "brand",
                   "binding_method", "binding_sources", "observed_at",
                   "verified_at", "status")
OPTIONAL_FIELDS = ("property_code", "identity_context", "identity_signals_matched",
                   "property_identity_check", "revalidation_cadence_days",
                   "canonical_destination", "notes")
ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS) | frozenset(OPTIONAL_FIELDS)

HOTEL_REF_REQUIRED = ("market_id", "canonical_name", "normalized_name")
HOTEL_REF_OPTIONAL = ("street_identity",)
HOTEL_REF_ALLOWED = frozenset(HOTEL_REF_REQUIRED) | frozenset(HOTEL_REF_OPTIONAL)

#: The queue's own contract requires a non-empty address/city/state/phone
#: (queue._REQUIRED_HOTEL_FIELDS). A seed hotel gets those from its seed row; a
#: non-seed identity has no committed source at all. This block carries exactly
#: those fields and nothing else, so a routing record can produce a valid queue
#: entry without a seed row. It is NOT canonical identity and is read by
#: nothing in the publication path.
IDENTITY_CONTEXT_ALLOWED = frozenset({"address", "city", "state", "postal_code",
                                      "phone"})
#: The subset the capture queue cannot proceed without.
IDENTITY_CONTEXT_REQUIRED_FOR_QUEUE = ("address", "city", "state", "phone")

#: PTF-COLUMBUS-INTEGRATE-UNRESOLVED-001. The phone is substitutable, on exactly
#: the terms ``capture_automation.queue`` now accepts: a record offering an
#: address AND a postal code AND a property code gives the capture-time gate the
#: address and property_identifier key groups, which is the same two-group
#: standard ``identity_keys`` applies everywhere. This mirror exists because a
#: routing record is checked HERE before it is ever shaped into a queue entry,
#: so a rule enforced only in the queue would still refuse it upstream.
IDENTITY_CONTEXT_REQUIRED_WITHOUT_PHONE = ("address", "city", "state",
                                           "postal_code")

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class IdentityRoutingError(ValueError):
    """A routing record is malformed, or policy has been smuggled into it."""


def registrable_domain(url: str) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    labels = [l for l in host.split(".") if l]
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _assert_membrane_clean(keys, *, where: str) -> None:
    """Routing answers WHERE to ask, never WHAT the answer is."""
    hits = sorted({str(k) for k in keys
                   if normalize_field_name(k) in POLICY_FIELD_NAMES})
    if hits:
        raise IdentityRoutingError(
            "%s carries pet-policy field name(s) %s -- a routing record says "
            "where a property speaks for itself and may never carry what it "
            "said" % (where, hits))


def _require_nonempty_str(record: Mapping, field: str, *, where: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise IdentityRoutingError(
            "%s: %r must be a non-empty string, got %r" % (where, field, value))
    return value


def validate_record(record: Mapping) -> Dict:
    """Fail closed on anything the frozen 1.0 contract would reject."""
    if not isinstance(record, Mapping):
        raise IdentityRoutingError(
            "a routing record must be a mapping, got %r" % type(record).__name__)
    where = "routing record %r" % (record.get("routing_id") or "<no routing_id>")

    _assert_membrane_clean(record.keys(), where=where)
    unknown = sorted(set(map(str, record.keys())) - ALLOWED_FIELDS)
    if unknown:
        raise IdentityRoutingError(
            "%s carries unknown field(s) %s (additionalProperties is false)"
            % (where, unknown))
    missing = [f for f in REQUIRED_FIELDS if f not in record]
    if missing:
        raise IdentityRoutingError("%s is missing required field(s) %s"
                                   % (where, missing))

    _require_nonempty_str(record, "routing_id", where=where)
    if record.get("schema_version") != CONTRACT_VERSION:
        raise IdentityRoutingError(
            "%s: schema_version must be %r, got %r"
            % (where, CONTRACT_VERSION, record.get("schema_version")))
    if record.get("status") not in ROUTING_STATUSES:
        raise IdentityRoutingError(
            "%s: status must be one of %s, got %r"
            % (where, list(ROUTING_STATUSES), record.get("status")))
    if record.get("binding_method") not in BINDING_METHODS:
        raise IdentityRoutingError(
            "%s: binding_method must be one of %s, got %r -- an index binding "
            "is never relabelled as a rendered page"
            % (where, list(BINDING_METHODS), record.get("binding_method")))

    # ---- hotel_ref: a reference into existing identity authority --------- #
    ref = record.get("hotel_ref")
    if not isinstance(ref, Mapping):
        raise IdentityRoutingError("%s: hotel_ref must be a mapping" % where)
    unknown_ref = sorted(set(map(str, ref.keys())) - HOTEL_REF_ALLOWED)
    if unknown_ref:
        raise IdentityRoutingError(
            "%s: hotel_ref carries unknown key(s) %s -- routing references the "
            "existing identity authority and never extends it" % (where, unknown_ref))
    for field in HOTEL_REF_REQUIRED:
        _require_nonempty_str(ref, field, where="%s hotel_ref" % where)
    if normalize_name(ref["canonical_name"]) != ref["normalized_name"]:
        raise IdentityRoutingError(
            "%s: hotel_ref.normalized_name %r is not the normalization of "
            "canonical_name %r -- the join key must be derivable, never typed"
            % (where, ref["normalized_name"], ref["canonical_name"]))

    market_id = _require_nonempty_str(record, "market_id", where=where)
    if ref["market_id"] != market_id:
        raise IdentityRoutingError(
            "%s: market_id %r does not match hotel_ref.market_id %r"
            % (where, market_id, ref["market_id"]))

    # ---- the URL --------------------------------------------------------- #
    url = _require_nonempty_str(record, "official_property_url", where=where)
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise IdentityRoutingError(
            "%s: official_property_url must be https, got %r" % (where, parts.scheme))
    if "@" in (parts.netloc or ""):
        raise IdentityRoutingError("%s: URL carries embedded credentials" % where)
    domain = registrable_domain(url)
    if domain in NEVER_OFFICIAL_DOMAINS:
        raise IdentityRoutingError(
            "%s: %r is a third-party or known-dead host. A third-party source "
            "may DISCOVER an official URL and may never BE one." % (where, domain))
    declared = _require_nonempty_str(record, "official_domain", where=where)
    if declared != domain:
        raise IdentityRoutingError(
            "%s: official_domain %r does not match the URL's domain %r"
            % (where, declared, domain))

    # ---- provenance ------------------------------------------------------- #
    sources = record.get("binding_sources")
    if not isinstance(sources, (list, tuple)) or not sources or \
            not all(isinstance(s, str) and s.strip() for s in sources):
        raise IdentityRoutingError(
            "%s: binding_sources must be a non-empty array of non-empty strings "
            "-- a routing record that cannot say what bound it is a guess" % where)
    for field in ("observed_at", "verified_at"):
        value = _require_nonempty_str(record, field, where=where)
        if not _ISO_DATE.match(value):
            raise IdentityRoutingError(
                "%s: %s must be an ISO date (YYYY-MM-DD), got %r" % (where, field, value))

    if record.get("status") == ROUTING_CONFIRMED and \
            not record.get("identity_signals_matched"):
        raise IdentityRoutingError(
            "%s: a ROUTING_CONFIRMED record must record the identity signals "
            "that bound it" % where)

    check = record.get("property_identity_check", IDENTITY_UNCHECKED)
    if check not in IDENTITY_CHECK_VALUES:
        raise IdentityRoutingError(
            "%s: property_identity_check must be one of %s"
            % (where, sorted(IDENTITY_CHECK_VALUES)))
    cadence = record.get("revalidation_cadence_days", DEFAULT_REVALIDATION_CADENCE_DAYS)
    if isinstance(cadence, bool) or not isinstance(cadence, int) or cadence <= 0:
        raise IdentityRoutingError(
            "%s: revalidation_cadence_days must be a positive integer" % where)

    # ---- identity_context: queue fuel, never canonical identity ---------- #
    context = record.get("identity_context")
    if context is not None:
        if not isinstance(context, Mapping):
            raise IdentityRoutingError("%s: identity_context must be a mapping" % where)
        _assert_membrane_clean(context.keys(), where="%s identity_context" % where)
        unknown_c = sorted(set(map(str, context.keys())) - IDENTITY_CONTEXT_ALLOWED)
        if unknown_c:
            raise IdentityRoutingError(
                "%s: identity_context carries unknown key(s) %s. It exists ONLY "
                "to satisfy the capture queue's required fields and is not a "
                "second identity record." % (where, unknown_c))
        for k, v in context.items():
            if not isinstance(v, str):
                raise IdentityRoutingError(
                    "%s: identity_context.%s must be a string" % (where, k))

    return dict(record)


def validate_authority(doc: Mapping) -> List[Dict]:
    """Validate the whole file, including the cross-record collision rules."""
    if not isinstance(doc, Mapping):
        raise IdentityRoutingError("routing authority must be a JSON object")
    if doc.get("schema") != SCHEMA:
        raise IdentityRoutingError(
            "unsupported schema %r (expected %r)" % (doc.get("schema"), SCHEMA))
    records = doc.get("routes")
    if not isinstance(records, list):
        raise IdentityRoutingError("routing authority must carry a 'routes' array")

    validated = [validate_record(r) for r in records]

    # One ACTIVE routing record per identity.
    by_hotel: Dict[str, str] = {}
    for r in validated:
        key = (r["market_id"], r["hotel_ref"]["normalized_name"])
        if r["status"] in USABLE_STATUSES:
            if key in by_hotel:
                raise IdentityRoutingError(
                    "two active routing records for %s: %r and %r"
                    % (key, by_hotel[key], r["routing_id"]))
            by_hotel[key] = r["routing_id"]

    # A property code, and a URL, may each bind exactly one identity.
    #
    # PTF-CLEVELAND-MARKET-FACTORY-001: a property code is unique WITHIN ITS
    # BRAND, not across all of them. Cleveland is the first market dense enough
    # to prove it -- IHG's Hotel Indigo Cleveland Beachwood is `clebd` at
    # ihg.com, and Marriott's Residence Inn Cleveland Beachwood is `clebd` at
    # marriott.com. Both extractions are correct and the two hotels are a mile
    # apart. Comparing codes globally called that a corruption and refused the
    # whole authority.
    #
    # Scoping by registrable domain is what makes the check true rather than
    # merely strict: it still catches the case the rule exists for -- one
    # brand's code pointed at two of that brand's properties, which is how a
    # capture ends up proving the wrong hotel -- and it no longer invents a
    # collision between two independent namespaces. The URL check stays global,
    # because one URL really cannot be two properties whoever serves it.
    code_seen: Dict[tuple, tuple] = {}
    for r in validated:
        code = (r.get("property_code") or "").strip().lower()
        if not code:
            continue
        scope = (registrable_domain(r.get("official_property_url") or "") or "",
                 code)
        key = (r["market_id"], r["hotel_ref"]["normalized_name"])
        if scope in code_seen and code_seen[scope] != key:
            raise IdentityRoutingError(
                "property code %r on %s binds two different identities: %s and "
                "%s -- one endpoint cannot be property-specific for two "
                "properties" % (code, scope[0] or "(no domain)",
                                code_seen[scope][1], key[1]))
        code_seen[scope] = key

    url_seen: Dict[str, tuple] = {}
    for r in validated:
        value = (r.get("official_property_url") or "").strip()
        if not value:
            continue
        key = (r["market_id"], r["hotel_ref"]["normalized_name"])
        if value in url_seen and url_seen[value] != key:
            raise IdentityRoutingError(
                "URL %r binds two different identities: %s and %s -- one "
                "endpoint cannot be property-specific for two properties"
                % (value, url_seen[value][1], key[1]))
        url_seen[value] = key
    return validated


def load_routes(path: Optional[Path] = None) -> List[Dict]:
    """Every validated routing record. A missing file is an empty authority --
    routing is additive, and its absence must never break a caller."""
    target = Path(path) if path is not None else ROUTING_PATH
    if not target.exists():
        return []
    return validate_authority(json.loads(target.read_text(encoding="utf-8")))


def usable_routes_by_key(routes: Sequence[Mapping], *,
                         market_id: Optional[str] = None) -> Dict[str, Dict]:
    """normalized_name -> record, for records the capture queue may act on."""
    out: Dict[str, Dict] = {}
    for r in routes:
        if r["status"] not in USABLE_STATUSES:
            continue
        if market_id is not None and r["market_id"] != market_id:
            continue
        out[r["hotel_ref"]["normalized_name"]] = dict(r)
    return out


def queue_identity_fields(record: Mapping) -> Optional[Dict[str, str]]:
    """The queue-required identity fields, or None when the record cannot
    supply them. Returning None is a real answer: a routing record may know a
    URL and still lack the address the queue contract demands."""
    context = record.get("identity_context") or {}
    present = lambda f: bool(str(context.get(f) or "").strip())   # noqa: E731
    ok = all(present(f) for f in IDENTITY_CONTEXT_REQUIRED_FOR_QUEUE)
    if not ok:
        # A record with no phone may still qualify, but only by paying for it
        # with a postal code AND a property code -- never by simply having less.
        ok = (all(present(f) for f in IDENTITY_CONTEXT_REQUIRED_WITHOUT_PHONE)
              and bool(str(record.get("property_code") or "").strip()))
    if not ok:
        return None
    return {
        "address": context.get("address", ""), "city": context.get("city", ""),
        "state": context.get("state", ""), "phone": context.get("phone", ""),
        "postal_code": context.get("postal_code", ""),
    }


__all__ = [
    "SCHEMA", "CONTRACT_VERSION", "ROUTING_PATH", "IdentityRoutingError",
    "ROUTING_CONFIRMED", "ROUTING_HELD", "ROUTING_CONFLICT", "ROUTING_STALE",
    "ROUTING_STATUSES", "USABLE_STATUSES",
    "BINDING_PAGE_RENDERED", "BINDING_BRAND_INDEX", "BINDING_METHODS",
    "NEVER_OFFICIAL_DOMAINS", "REQUIRED_FIELDS", "OPTIONAL_FIELDS",
    "IDENTITY_CONTEXT_ALLOWED", "IDENTITY_CONTEXT_REQUIRED_FOR_QUEUE",
    "registrable_domain", "validate_record", "validate_authority",
    "load_routes", "usable_routes_by_key", "queue_identity_fields",
]

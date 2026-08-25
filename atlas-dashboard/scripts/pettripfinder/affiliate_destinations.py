"""PTF-MEASUREMENT-001 Phase 1b -- affiliate destinations as market authority.

WHY THIS EXISTS
---------------
The booking action (``/go/<id>/booking/``) has always redirected to the
property's own official URL, with ``commercial_actions.AffiliateConfig`` able
to append one global query parameter. That model never matched how hotel
affiliate programs issue links: a program hands the publisher a network
tracking URL or a brand deep link carrying the property's own code, per
property, and the publisher is accountable for every one of them.

So an affiliate destination is AUTHORITY, not configuration. It is stored in
the market shard architecture (PTF-MARKET-AUTHORITY-SHARDING-001), keyed by
the same ``identity_key`` the policy package uses, and every row binds the
destination to the property it was mapped against: the seed row's
``website_url`` at mapping time is recorded, and a build whose seed row has
since moved refuses the destination rather than sending a traveller to a
hotel that is no longer the one reviewed.

WHAT IT REFUSES (fail closed -- a raise, never a silent fallback)
-----------------------------------------------------------------
* a provider the registry does not know, or knows but is not enrolled in;
* a destination whose host is not in the provider's allowlist;
* an ``identity_key`` with no seed row in this market;
* ``official_url_at_mapping`` that differs from the seed row's ``website_url``;
* a row whose market is not the shard's market;
* a malformed destination (not https, no host, a credential in it);
* two rows for one identity.

WHAT IT DOES WHEN THERE IS NOTHING
----------------------------------
Returns ``None``. The booking action then behaves exactly as it does today:
the official URL, no affiliate parameter, ``affiliate_provider`` empty. Every
committed shard starts at ``count: 0``, so no public output changes.

THE SHARD RULE
--------------
A market writer edits ``markets/authority/<market_id>/affiliate_destinations.json``
and nothing else. The cross-market view is DERIVED in memory
(:func:`assemble_global_view`); there is no generated global file to fight
over. Every mapping names the human who approved it -- ``approved_by`` is an
attestation, and the build does not fill it in.

Pure and deterministic: no network, no clock.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]

PROVIDERS_SCHEMA = "ptf-affiliate-providers/1.0"
DESTINATIONS_SCHEMA = "ptf-affiliate-destinations/1.0"
PROVIDERS_PATH = REPO_ROOT / "deploy" / "netlify" / "affiliate_providers.json"

#: The rel policy every affiliate booking link carries. Search engines ask for
#: ``sponsored`` on paid links; ``nofollow`` is the conservative companion;
#: ``noopener`` is what every outbound link here already carries.
REL_AFFILIATE = "nofollow sponsored noopener"

STATUS_ACTIVE = "active"
STATUS_SUSPENDED = "suspended"
STATUSES = frozenset({STATUS_ACTIVE, STATUS_SUSPENDED})

_PROVIDER_KEYS = frozenset({
    "provider_id", "display_name", "allowed_destination_hosts", "disclosure",
    "rel", "enrolled",
})
_DESTINATION_KEYS = frozenset({
    "identity_key", "provider_id", "program_id", "destination_url",
    "official_url_at_mapping", "approved_by", "approved_at", "status", "note",
})
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AffiliateDestinationError(ValueError):
    """Refused rather than routed. Nothing falls back when this is raised."""


def _normalize_name(text: str) -> str:
    from scripts.pettripfinder.site_data import normalize_name
    return normalize_name(text)


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AffiliateProvider:
    provider_id: str
    display_name: str
    allowed_destination_hosts: Tuple[str, ...]
    disclosure: str
    rel: str
    enrolled: bool


def validate_providers_document(doc: Mapping) -> List[str]:
    problems: List[str] = []
    if not isinstance(doc, Mapping):
        return ["providers document is not an object"]
    if doc.get("schema") != PROVIDERS_SCHEMA:
        problems.append("schema is %r, expected %r" % (doc.get("schema"), PROVIDERS_SCHEMA))
    rows = doc.get("providers")
    if not isinstance(rows, list):
        return problems + ["providers must be a list"]
    if doc.get("count") != len(rows):
        problems.append("count %r does not match %d providers" % (doc.get("count"), len(rows)))
    seen = set()
    for i, row in enumerate(rows):
        where = "providers[%d]" % i
        if not isinstance(row, Mapping):
            problems.append("%s is not an object" % where)
            continue
        unknown = sorted(set(row) - _PROVIDER_KEYS)
        missing = sorted(_PROVIDER_KEYS - set(row))
        if unknown:
            problems.append("%s has unknown keys %s" % (where, unknown))
        if missing:
            problems.append("%s is missing %s" % (where, missing))
            continue
        pid = row["provider_id"]
        if not isinstance(pid, str) or not _ID_RE.match(pid):
            problems.append("%s provider_id %r is not a safe id" % (where, pid))
        elif pid in seen:
            problems.append("%s duplicates provider_id %r" % (where, pid))
        seen.add(pid)
        if not isinstance(row["display_name"], str) or not row["display_name"].strip():
            problems.append("%s needs a display_name" % where)
        hosts = row["allowed_destination_hosts"]
        if not isinstance(hosts, list) or not hosts or \
                any(not isinstance(h, str) or not _HOST_RE.match(h) for h in hosts):
            problems.append("%s allowed_destination_hosts must be a non-empty list "
                            "of bare lowercase hostnames" % where)
        if not isinstance(row["disclosure"], str) or not row["disclosure"].strip():
            problems.append("%s needs disclosure text" % where)
        if row["rel"] != REL_AFFILIATE:
            problems.append("%s rel must be %r" % (where, REL_AFFILIATE))
        if not isinstance(row["enrolled"], bool):
            problems.append("%s enrolled must be a boolean" % where)
    return problems


def providers_from_document(doc: Mapping) -> Dict[str, AffiliateProvider]:
    problems = validate_providers_document(doc)
    if problems:
        raise AffiliateDestinationError("affiliate providers refused: %s"
                                        % "; ".join(problems))
    out: Dict[str, AffiliateProvider] = {}
    for row in doc["providers"]:
        out[row["provider_id"]] = AffiliateProvider(
            provider_id=row["provider_id"], display_name=row["display_name"],
            allowed_destination_hosts=tuple(row["allowed_destination_hosts"]),
            disclosure=row["disclosure"], rel=row["rel"], enrolled=bool(row["enrolled"]))
    return out


def load_providers(path: Optional[Path] = None) -> Dict[str, AffiliateProvider]:
    path = Path(path) if path is not None else PROVIDERS_PATH
    if not path.is_file():
        raise AffiliateDestinationError("no affiliate provider registry at %s" % path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        raise AffiliateDestinationError("affiliate providers is not JSON: %s" % exc)
    return providers_from_document(doc)


# --------------------------------------------------------------------------- #
# Destinations (per-market shard)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AffiliateDestination:
    """A RESOLVED destination: every check in :func:`destination_for` has
    passed. The redirect layer consumes exactly these three facts."""
    provider_id: str
    destination_url: str
    rel: str = REL_AFFILIATE


def shard_path(market_id: str, authority_dir: Optional[Path] = None) -> Path:
    from scripts.pettripfinder.market_authority import affiliate_shard_path
    return affiliate_shard_path(market_id, authority_dir)


def empty_document(market_id: str) -> Dict:
    return {
        "schema": DESTINATIONS_SCHEMA,
        "contract": DESTINATIONS_SCHEMA,
        "market_id": market_id,
        "note": ("This market's affiliate booking destinations, keyed by the "
                 "policy package's identity_key. A row binds one approved "
                 "program deep link to one property and records the official "
                 "URL it was mapped against; the build refuses a row whose "
                 "provider is not enrolled, whose host is not allowlisted, or "
                 "whose property has since changed its official URL. Every row "
                 "names the human who approved it. No row here creates a "
                 "booking link on its own: the booking CTA is a separate "
                 "founder/design decision."),
        "count": 0,
        "destinations": [],
    }


def validate_destinations_document(doc: Mapping, market_id: str) -> List[str]:
    problems: List[str] = []
    if not isinstance(doc, Mapping):
        return ["destinations document is not an object"]
    if doc.get("schema") != DESTINATIONS_SCHEMA:
        problems.append("schema is %r, expected %r"
                        % (doc.get("schema"), DESTINATIONS_SCHEMA))
    if doc.get("market_id") != market_id:
        problems.append("shard declares market_id %r but sits under %r"
                        % (doc.get("market_id"), market_id))
    rows = doc.get("destinations")
    if not isinstance(rows, list):
        return problems + ["destinations must be a list"]
    if doc.get("count") != len(rows):
        problems.append("count %r does not match %d destinations"
                        % (doc.get("count"), len(rows)))
    seen = set()
    for i, row in enumerate(rows):
        where = "destinations[%d]" % i
        if not isinstance(row, Mapping):
            problems.append("%s is not an object" % where)
            continue
        unknown = sorted(set(row) - _DESTINATION_KEYS)
        missing = sorted(_DESTINATION_KEYS - {"note"} - set(row))
        if unknown:
            problems.append("%s has unknown keys %s" % (where, unknown))
        if missing:
            problems.append("%s is missing %s" % (where, missing))
            continue
        key = row["identity_key"]
        if not isinstance(key, str) or not key or key != _normalize_name(key):
            problems.append("%s identity_key %r is not a normalized identity key"
                            % (where, key))
        elif key in seen:
            problems.append("%s duplicates identity_key %r" % (where, key))
        seen.add(key)
        for name in ("provider_id", "program_id"):
            if not isinstance(row[name], str) or not _ID_RE.match(row[name]):
                problems.append("%s %s %r is not a safe id" % (where, name, row[name]))
        for name in ("destination_url", "official_url_at_mapping"):
            problems.extend("%s %s: %s" % (where, name, p)
                            for p in _url_problems(row[name]))
        if not isinstance(row["approved_by"], str) or not row["approved_by"].strip():
            problems.append("%s needs approved_by (a human attestation)" % where)
        if not isinstance(row["approved_at"], str) or not _DATE_RE.match(row["approved_at"]):
            problems.append("%s approved_at must be YYYY-MM-DD" % where)
        if row["status"] not in STATUSES:
            problems.append("%s status %r not in %s" % (where, row["status"], sorted(STATUSES)))
    return problems


def _url_problems(url) -> List[str]:
    if not isinstance(url, str) or not url:
        return ["empty"]
    parts = urlsplit(url)
    out = []
    if parts.scheme != "https":
        out.append("not https")
    if not parts.hostname:
        out.append("no host")
    if parts.username or parts.password:
        out.append("carries credentials")
    if any(ch in url for ch in ("<", ">", '"', "'", " ")):
        out.append("contains markup or whitespace")
    return out


def load_market_destinations_document(market_id: str,
                                      authority_dir: Optional[Path] = None) -> Dict:
    """This market's shard, validated. A missing shard is an EMPTY shard: the
    affiliate authority is additive and its absence must never break a build
    (the same rule routing follows)."""
    path = shard_path(market_id, authority_dir)
    if not path.is_file():
        return empty_document(market_id)
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        raise AffiliateDestinationError("%s is not JSON: %s" % (path.name, exc))
    problems = validate_destinations_document(doc, market_id)
    if problems:
        raise AffiliateDestinationError("affiliate shard for %s refused: %s"
                                        % (market_id, "; ".join(problems)))
    return doc


def assemble_global_view(authority_dir: Optional[Path] = None,
                         market_ids: Optional[Sequence[str]] = None) -> Dict[str, Dict]:
    """Every market's destinations, keyed ``identity_key`` -> row (with the
    owning ``market_id`` attached). Derived in memory; one identity mapped
    by two markets is refused, exactly as routing and exclusions are."""
    from scripts.pettripfinder.market_authority import sharded_market_ids
    ids = tuple(market_ids) if market_ids is not None else sharded_market_ids(authority_dir)
    out: Dict[str, Dict] = {}
    for market_id in sorted(ids):
        doc = load_market_destinations_document(market_id, authority_dir)
        for row in doc["destinations"]:
            key = row["identity_key"]
            if key in out:
                raise AffiliateDestinationError(
                    "identity %r mapped by both %s and %s"
                    % (key, out[key]["market_id"], market_id))
            out[key] = dict(row, market_id=market_id)
    return out


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #

def _check_row(row: Mapping, *, provider: Optional[AffiliateProvider],
               seed_row: Optional[Mapping], market_id: str) -> List[str]:
    """Why this mapped row may not be used, or []."""
    problems: List[str] = []
    if provider is None:
        problems.append("provider %r is not in the registry" % row["provider_id"])
    elif not provider.enrolled:
        problems.append("provider %r is not enrolled" % row["provider_id"])
    else:
        host = (urlsplit(row["destination_url"]).hostname or "").lower()
        if not any(host == h or host.endswith("." + h)
                   for h in provider.allowed_destination_hosts):
            problems.append("destination host %r is not allowlisted for %r"
                            % (host, provider.provider_id))
    if seed_row is None:
        problems.append("identity %r has no seed row in %s" % (row["identity_key"], market_id))
    else:
        if (seed_row.get("market_id") or "") != market_id:
            problems.append("seed row belongs to %r, not %r"
                            % (seed_row.get("market_id"), market_id))
        current = (seed_row.get("website_url") or "").strip()
        if current != row["official_url_at_mapping"].strip():
            problems.append("official URL drifted since mapping: mapped against %r, "
                            "seed now %r" % (row["official_url_at_mapping"], current))
    if row.get("status") != STATUS_ACTIVE:
        problems.append("status is %r" % row.get("status"))
    return problems


def destination_for(row: Mapping, market_id: str, *,
                    providers: Optional[Mapping[str, AffiliateProvider]] = None,
                    destinations: Optional[Mapping] = None,
                    authority_dir: Optional[Path] = None) -> Optional[AffiliateDestination]:
    """The affiliate destination for one seed ``row`` in ``market_id``.

    ``None`` when the market has no mapping for this property -- the caller
    then uses the official URL, which is today's behaviour in full. A mapping
    that EXISTS but fails any check raises: a wrong affiliate link is worse
    than none, and silently falling back would hide the defect until the
    next person reads the shard.
    """
    key = _normalize_name(row.get("name", ""))
    if not key:
        return None
    doc = destinations if destinations is not None else \
        load_market_destinations_document(market_id, authority_dir)
    matches = [d for d in doc.get("destinations", []) if d.get("identity_key") == key]
    if not matches:
        return None
    if len(matches) > 1:
        raise AffiliateDestinationError("identity %r has %d destination rows in %s"
                                        % (key, len(matches), market_id))
    mapped = matches[0]
    if (row.get("market_id") or market_id) != market_id:
        raise AffiliateDestinationError(
            "row %r belongs to %r, resolved for %r"
            % (row.get("name"), row.get("market_id"), market_id))
    registry = providers if providers is not None else load_providers()
    problems = _check_row(mapped, provider=registry.get(mapped["provider_id"]),
                          seed_row=row, market_id=market_id)
    if problems:
        raise AffiliateDestinationError("affiliate destination for %r refused: %s"
                                        % (key, "; ".join(problems)))
    return AffiliateDestination(provider_id=mapped["provider_id"],
                                destination_url=mapped["destination_url"],
                                rel=registry[mapped["provider_id"]].rel)


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #

GATE_ALLOWLISTED = "affiliate.destinations_allowlisted"
GATE_IDENTITY_BOUND = "affiliate.identity_bound"
GATE_ENROLLED = "affiliate.no_destination_without_enrolled_provider"
AFFILIATE_GATES = (GATE_ALLOWLISTED, GATE_IDENTITY_BOUND, GATE_ENROLLED)


def run_affiliate_gates(gates, gate: Callable, *, authority_dir: Optional[Path] = None,
                        providers_path: Optional[Path] = None,
                        market_ids: Optional[Sequence[str]] = None) -> int:
    """Record the three affiliate gates into ``gates`` via the assembler's
    ``_gate``. With zero destinations all three pass. Returns the number of
    destination rows examined."""
    from scripts.pettripfinder.market_authority import load_market_seed_rows

    try:
        registry = load_providers(providers_path)
        view = assemble_global_view(authority_dir, market_ids)
    except AffiliateDestinationError as exc:
        for gid in AFFILIATE_GATES:
            gate(gates, gid, False, str(exc))
        return 0

    not_allowlisted: List[str] = []
    unbound: List[str] = []
    unenrolled: List[str] = []
    seed_cache: Dict[str, Dict[str, Dict]] = {}
    for key, row in sorted(view.items()):
        market_id = row["market_id"]
        provider = registry.get(row["provider_id"])
        if provider is None or not provider.enrolled:
            unenrolled.append("%s -> %s" % (key, row["provider_id"]))
        else:
            host = (urlsplit(row["destination_url"]).hostname or "").lower()
            if not any(host == h or host.endswith("." + h)
                       for h in provider.allowed_destination_hosts):
                not_allowlisted.append("%s -> %s" % (key, host))
        if market_id not in seed_cache:
            seed_cache[market_id] = {
                _normalize_name(r.get("name", "")): r
                for r in load_market_seed_rows(market_id, authority_dir)}
        seed = seed_cache[market_id].get(key)
        if seed is None:
            unbound.append("%s: no seed row in %s" % (key, market_id))
        elif (seed.get("website_url") or "").strip() != row["official_url_at_mapping"].strip():
            unbound.append("%s: official URL drifted" % key)
    gate(gates, GATE_ALLOWLISTED, not not_allowlisted,
         "; ".join(not_allowlisted[:6]) or "%d destinations" % len(view))
    gate(gates, GATE_IDENTITY_BOUND, not unbound,
         "; ".join(unbound[:6]) or "%d destinations" % len(view))
    gate(gates, GATE_ENROLLED, not unenrolled,
         "; ".join(unenrolled[:6]) or "%d enrolled providers"
         % sum(1 for p in registry.values() if p.enrolled))
    return len(view)


__all__ = [
    "PROVIDERS_SCHEMA", "DESTINATIONS_SCHEMA", "PROVIDERS_PATH", "REL_AFFILIATE",
    "STATUS_ACTIVE", "STATUS_SUSPENDED", "STATUSES",
    "AffiliateDestinationError", "AffiliateProvider", "AffiliateDestination",
    "validate_providers_document", "providers_from_document", "load_providers",
    "shard_path", "empty_document", "validate_destinations_document",
    "load_market_destinations_document", "assemble_global_view",
    "destination_for", "GATE_ALLOWLISTED", "GATE_IDENTITY_BOUND", "GATE_ENROLLED",
    "AFFILIATE_GATES", "run_affiliate_gates",
]

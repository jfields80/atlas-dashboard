"""ATLAS-THROUGHPUT-003 -- the ONE typed writer for a sealed market package.

``build_sealed_package`` takes a :class:`PackageInputs` (the proposed state of
ONE market, as the documents the owning contracts already define) and returns
a sealed package -- or raises :class:`PackageWriteError` naming every reason
the proposed state may not be serialized. Nothing is written until every
check passes: the writer rejects BEFORE serialization, never after.

Every content rule is delegated to the module that owns it:

    market / corridors      scripts.pettripfinder.markets.contract.parse_market
    census                  scripts.pettripfinder.contracts.census.validate
    identity keys           scripts.pettripfinder.contracts.identity_key
    policy records          scripts.pettripfinder.contracts.policy_schema.validate_record
    evidence                scripts.pettripfinder.contracts.evidence (validate,
                            publication_blockers, unevidenced_facts)
    exclusions              scripts.pettripfinder.hotel_exclusions.validate
    routing                 scripts.pettripfinder.identity_routing.validate_authority
    partition               scripts.pettripfinder.contracts.partition (validate, reconcile)
    public routes           scripts.pettripfinder.markets.routes (hotel_route,
                            corridor_route, build_route_table)
    display join            scripts.pettripfinder.site_data.normalize_name
    same premises           scripts.pettripfinder.hotel_exclusions.co_located_distinct

What this module adds is the CROSS-contract binding those modules cannot see
from inside one document: a policy record's identity must exist in the census
and in the partition as PUBLISHED_PET_FRIENDLY; its evidence must bind to a
reference that names the same identity; its route must resolve to the routing
authority for the same identity on the same first-party domain; a refundable
amount in ``pet_fee`` is a deposit and belongs in ``other_charges``; an
exclusion and a policy record may not share an identity; two identities on
one premises must be proven distinct or declared related.
"""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import identity_routing as IR
from scripts.pettripfinder import sealed_market_package as SMP
from scripts.pettripfinder.contracts import census as CENSUS
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as EVIDENCE
from scripts.pettripfinder.contracts import partition as PARTITION
from scripts.pettripfinder.contracts import policy_schema as POLICY
from scripts.pettripfinder.contracts.identity_key import is_canonical_key, ptf_identity_key
from scripts.pettripfinder.market_authority import (SEED_COLUMNS, build_exclusions_shard,
                                                    build_routing_shard)
from scripts.pettripfinder.markets.contract import MarketConfig, parse_market, slugify
from scripts.pettripfinder.markets.routes import (MarketRouteError, build_route_table,
                                                  corridor_route, hotel_route)
from scripts.pettripfinder.sealed_market_package import Issue
from scripts.pettripfinder.site_data import normalize_name

REPO_ROOT = SMP.REPO_ROOT
LAUNCH_PACKAGE = SMP.LAUNCH_PACKAGE

#: The versions of every owning contract a package is validated against.
CONTRACT_VERSIONS: "OrderedDict[str, str]" = OrderedDict((
    ("market", "ptf-market/1.1"),
    ("census", CENSUS.SCHEMA),
    ("partition", PARTITION.SCHEMA),
    ("policy_schema", enums.POLICY_SCHEMA_VERSION),
    ("evidence", "contracts.evidence PUBLICATION_GRADE_REQUIRED=%s"
                 % ",".join(EVIDENCE.PUBLICATION_GRADE_REQUIRED)),
    ("identity_key", "ptf_identity_key/1.0"),
    ("identity_routing", IR.SCHEMA),
    ("hotel_exclusions", HE.SCHEMA),
    ("sealed_market_package", SMP.SCHEMA),
))

#: Policy record statuses a pet-friendly record may carry. A record with any
#: other status -- a hold, an observation, a silence -- is not clean.
PET_FRIENDLY_STATUSES = frozenset({"VERIFIED_PET_FRIENDLY"})

#: Capture methods that cost money. A reference captured through one of these
#: must carry a paid reservation (rule O of the fast lane).
PAID_LANE_PREFIXES = ("firecrawl", "brightdata", "google_places", "places",
                      "unlocker", "spider")

_SENTINELS = frozenset({"unknown", "unstated", "n/a", "na", "none", "null",
                        "not applicable", "not_applicable", "tbd", "?"})
_DERIVED_STREET_WORD = re.compile(r"[a-z]")


class PackageWriteError(ValueError):
    """The proposed state may not be serialized. Carries every issue found."""

    def __init__(self, issues: Sequence[Issue]):
        self.issues = tuple(issues)
        head = "; ".join(str(i) for i in self.issues[:6])
        more = " (+%d more)" % (len(self.issues) - 6) if len(self.issues) > 6 else ""
        super().__init__("proposed market state rejected before serialization: %s%s" % (head, more))

    def codes(self) -> Tuple[str, ...]:
        return tuple(sorted({i.code for i in self.issues}))


@dataclass
class PackageInputs:
    """The proposed state of one market, in the owning contracts' own shapes."""

    market_id: str
    execution_zone: str
    created_from_source_sha: str
    market: Mapping                                  # ptf-market/1.1 document
    census: Mapping                                  # ptf-market-identity-census/1.1 document
    pet_friendly_records: Sequence[Mapping]          # policy schema 1.2/1.3 records
    verified_no_pets_records: Sequence[Mapping]      # ptf-hotel-exclusions/1.0 records
    official_routes: Sequence[Mapping]               # ptf-identity-routing/1.0 records
    seed_rows: Sequence[Mapping[str, str]]           # SEED_COLUMNS rows this market owns
    partition: Mapping                               # ptf-market-final-partition/1.1 document
    intended_delta: Mapping
    parent_live_state: Mapping
    dependency_input_digests: Mapping[str, str]
    evidence_references: Optional[Sequence[Mapping]] = None   # derived from records when None
    paid_reservations: Mapping[str, Mapping] = field(default_factory=dict)  # artifact sha -> reservation
    founder_holds: Sequence[Mapping] = ()
    relations: Mapping[str, Mapping] = field(default_factory=dict)          # identity_key -> relation
    coverage_scorecard: Mapping = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Small helpers.
# --------------------------------------------------------------------------- #

def registrable_domain(url: str) -> str:
    return IR.registrable_domain(url)


def is_paid_lane(capture_method: str) -> bool:
    text = str(capture_method or "").strip().lower()
    return any(text.startswith(p) for p in PAID_LANE_PREFIXES)


def _is_sentinel(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() in _SENTINELS


def _premises_key(address: str, postal_code: str) -> str:
    """The exclusions contract's street identity, or "" when the row carries
    no street at all -- a postal code alone is not a premises."""
    key = HE.address_key(address or "", postal_code or "")
    number, words, _postal = key.split("|", 2)
    if not number and not _DERIVED_STREET_WORD.search(words):
        return ""
    return key


def _same_brand_family(source_domain: str, official_url: str, census_brand: str) -> bool:
    """A brand-family page for a property whose own domain the census names
    (the Seelbach's page on hilton.com) is still that property's first party
    when the family agrees. Anything less is not."""
    family = next((f for fragment, f in HE.BRAND_FAMILY_HOSTS if fragment in source_domain), "")
    if not family:
        return False
    official_family, _code = HE.brand_scoped_property_identity(official_url)
    return family == official_family or family == census_brand.strip().upper().replace(" ", "_")


def _record_source_urls(record: Mapping) -> List[str]:
    """Every page a record claims to have been read from: its own source_url
    and the source_url of each publication-grade evidence entry."""
    urls: List[str] = []
    if record.get("source_url"):
        urls.append(str(record["source_url"]))
    for entry in record.get("evidence") or ():
        if isinstance(entry, Mapping) and entry.get("source_url") \
                and entry.get("artifact_class") == enums.PUBLICATION_GRADE_EVIDENCE:
            urls.append(str(entry["source_url"]))
    return urls


def _record_identity(record: Mapping) -> str:
    key = str(record.get("identity_key") or "").strip()
    if key:
        return key
    name = str(record.get("name") or record.get("canonical_name") or "")
    try:
        return ptf_identity_key(name) if name else ""
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
# The writer.
# --------------------------------------------------------------------------- #

def build_sealed_package(inputs: PackageInputs, *, sealed_at: str) -> "OrderedDict[str, Any]":
    """Validate the proposed state against every owning contract and seal it.

    Raises :class:`PackageWriteError` with EVERY issue found (not the first),
    so a reviewer sees the whole picture in one refusal.
    """
    issues: List[Issue] = []
    market_id = str(inputs.market_id or "").strip()

    # ---- market / geography ---------------------------------------------- #
    market: Optional[MarketConfig] = None
    try:
        market = parse_market(dict(inputs.market), source="package:%s" % market_id)
    except Exception as exc:
        issues.append(Issue("market", "MARKET_CONTRACT", str(exc)[:300]))
    if market is not None and market.market_id != market_id:
        issues.append(Issue("market.market_id", "WRONG_MARKET",
                            "market document is for %r, package for %r" % (market.market_id, market_id)))
    corridor_ids: Set[str] = set(c.corridor_id for c in market.corridors) if market else set()
    market_states: Tuple[str, ...] = tuple(market.states) if market else ()

    # ---- census ------------------------------------------------------------ #
    census_doc = inputs.census
    for issue in CENSUS.validate(census_doc, market_states=market_states):
        issues.append(Issue("census." + issue.path, "CENSUS_" + issue.code, issue.detail))
    census_rows: List[Mapping] = [r for r in (census_doc.get("hotels") or ()) if isinstance(r, Mapping)]
    census_keys: Set[str] = set()
    census_by_key: Dict[str, Mapping] = {}
    for index, row in enumerate(census_rows):
        key = _record_identity(row)
        if not key:
            continue
        if key in census_by_key:
            issues.append(Issue("census.hotels[%d]" % index, "DUPLICATE_IDENTITY",
                                "identity %r appears twice in the census" % key))
            continue
        census_by_key[key] = row
        census_keys.add(key)
        corridor = str(row.get("corridor") or "")
        if corridor and corridor_ids and corridor not in corridor_ids:
            issues.append(Issue("census.hotels[%d].corridor" % index, "INVALID_MARKET_ASSIGNMENT",
                                "corridor %r is not a corridor of %s" % (corridor, market_id)))
        for field_name in ("canonical_name", "address", "city", "postal_code", "official_url"):
            if _is_sentinel(row.get(field_name)):
                issues.append(Issue("census.hotels[%d].%s" % (index, field_name), "SENTINEL_VALUE",
                                    "%r is a sentinel for absence; omit the value" % row.get(field_name)))

    # ---- identity records: derived from the census, plus relations -------- #
    identity_records = _identity_records(census_rows, inputs.relations, issues)
    issues.extend(_same_premises_issues(identity_records))

    # ---- routing authority ------------------------------------------------- #
    routes = [dict(r) for r in inputs.official_routes]
    route_by_key: Dict[str, Mapping] = {}
    retired_outside_census: List[str] = []
    try:
        IR.validate_authority(build_routing_shard(market_id, routes))
    except Exception as exc:
        issues.append(Issue("official_routes", "ROUTING_CONTRACT", str(exc)[:300]))
    for index, route in enumerate(routes):
        ref = route.get("hotel_ref") if isinstance(route.get("hotel_ref"), Mapping) else {}
        key = str(ref.get("identity_key") or ref.get("normalized_name") or "")
        if route.get("market_id") != market_id:
            issues.append(Issue("official_routes[%d].market_id" % index, "INVALID_MARKET_ASSIGNMENT",
                                "route declares %r, package is for %r" % (route.get("market_id"), market_id)))
        usable = route.get("status") in IR.USABLE_STATUSES
        if key and census_keys and key not in census_keys:
            if usable:
                issues.append(Issue("official_routes[%d]" % index, "ROUTE_IDENTITY_NOT_IN_CENSUS",
                                    "an ACTIVE route binds %r, which the census does not carry" % key))
            else:
                # A retired or held route for a candidate the census never
                # admitted (a restaurant, a venue) is acquisition history,
                # not a dangling reference: it binds nothing the site
                # publishes. Counted, never refused. (ATLAS-THROUGHPUT-004:
                # 003 over-read Cleveland's four ROUTING_RETIRED rows.)
                retired_outside_census.append(key)
        if key and usable:
            route_by_key[key] = route

    # ---- seed rows (the display join) ------------------------------------- #
    seed_rows = [dict(r) for r in inputs.seed_rows]
    seed_by_norm: Dict[str, List[Mapping]] = {}
    for index, row in enumerate(seed_rows):
        if str(row.get("market_id") or "") != market_id:
            issues.append(Issue("seed_rows[%d].market_id" % index, "INVALID_MARKET_ASSIGNMENT",
                                "seed row %r belongs to %r" % (row.get("name"), row.get("market_id"))))
        missing = [c for c in SEED_COLUMNS if c not in row]
        if missing:
            issues.append(Issue("seed_rows[%d]" % index, "SEED_COLUMNS",
                                "missing column(s) %s" % missing))
        seed_by_norm.setdefault(normalize_name(str(row.get("name") or "")), []).append(row)

    # ---- partition ---------------------------------------------------------- #
    partition_doc = inputs.partition
    for issue in PARTITION.validate(partition_doc):
        issues.append(Issue("partition." + issue.path, "PARTITION_" + issue.code, issue.detail))
    reconciliation = PARTITION.reconcile(census_keys, partition_doc, market_id=market_id)
    if reconciliation.missing_from_partition:
        issues.append(Issue("partition", "ORPHAN_PARTITION",
                            "%d census identities have no partition row: %s"
                            % (len(reconciliation.missing_from_partition),
                               list(reconciliation.missing_from_partition[:5]))))
    if reconciliation.missing_from_census:
        issues.append(Issue("partition", "ORPHAN_PARTITION",
                            "%d partition rows name no census identity: %s"
                            % (len(reconciliation.missing_from_census),
                               list(reconciliation.missing_from_census[:5]))))
    if reconciliation.duplicated_in_partition:
        issues.append(Issue("partition", "DUPLICATE_IDENTITY",
                            "partition rows duplicated: %s" % list(reconciliation.duplicated_in_partition[:5])))
    partition_state: Dict[str, str] = {}
    unresolved_rows: List[Dict] = []
    for item in partition_doc.get("items") or ():
        if not isinstance(item, Mapping):
            continue
        key = _record_identity(item)
        state = PARTITION.normalise_blocker(str(item.get("final_state") or ""))
        if key:
            partition_state[key] = state
        if state and state not in enums.TERMINAL_STATES:
            unresolved_rows.append(OrderedDict((
                ("identity_key", key), ("final_state", state),
                ("next_action", str(item.get("next_action") or "")),
                ("next_action_source", str(item.get("next_action_source") or "")),
            )))

    # ---- evidence references ------------------------------------------------ #
    references, evidence_hashes = _evidence_references(inputs, issues)
    ref_by_hash: Dict[Tuple[str, str], Mapping] = {
        (str(r["identity_key"]), str(r["artifact_sha256"])): r for r in references}

    # ---- pet-friendly policy records --------------------------------------- #
    pf_records = [dict(r) for r in inputs.pet_friendly_records]
    pf_keys: Set[str] = set()
    for index, record in enumerate(pf_records):
        path = "pet_friendly_records[%d]" % index
        key = _record_identity(record)
        if not key:
            issues.append(Issue(path + ".identity_key", "MISSING_IDENTITY",
                                "a policy record must carry a canonical identity key"))
            continue
        if not is_canonical_key(key):
            issues.append(Issue(path + ".identity_key", "IDENTITY_NOT_CANONICAL",
                                "%r is not the output of ptf_identity_key/1.0" % key))
        if key in pf_keys:
            issues.append(Issue(path, "DUPLICATE_IDENTITY", "identity %r has two policy records" % key))
        pf_keys.add(key)
        if census_keys and key not in census_keys:
            issues.append(Issue(path + ".identity_key", "MISSING_IDENTITY",
                                "identity %r is not in the census" % key))
        if str(record.get("market_id") or market_id) != market_id:
            issues.append(Issue(path + ".market_id", "INVALID_MARKET_ASSIGNMENT",
                                "record declares %r, package is for %r" % (record.get("market_id"), market_id)))
        corridor = str(record.get("corridor") or "")
        if corridor and corridor_ids and corridor not in corridor_ids:
            issues.append(Issue(path + ".corridor", "INVALID_MARKET_ASSIGNMENT",
                                "corridor %r is not a corridor of %s" % (corridor, market_id)))

        # The owning policy contract, the owning evidence contract.
        for issue in POLICY.validate_record(record):
            issues.append(Issue(path + "." + issue.path, "POLICY_" + issue.code, issue.detail))
        for issue in EVIDENCE.validate(record):
            issues.append(Issue(path + "." + issue.path, "EVIDENCE_" + issue.code, issue.detail))
        for blocker in EVIDENCE.publication_blockers(record):
            issues.append(Issue(path + ".evidence", "PUBLICATION_BLOCKED", blocker))

        # Status: a clean pet-friendly record states acceptance and nothing else.
        facts = record.get("facts") if isinstance(record.get("facts"), Mapping) else {}
        status = record.get("verification_state")
        if status is not None and status not in PET_FRIENDLY_STATUSES:
            issues.append(Issue(path + ".verification_state", "INVALID_POLICY_STATUS",
                                "%r is not a publishable status (%s)" % (status, sorted(PET_FRIENDLY_STATUSES))))
        if facts.get("pets_allowed") is not True:
            issues.append(Issue(path + ".facts.pets_allowed", "INVALID_POLICY_STATUS",
                                "a pet-friendly record must state pets_allowed: true, got %r"
                                % (facts.get("pets_allowed"),)))
        for hold_field in ("hold", "hold_reason", "blocker"):
            if record.get(hold_field):
                issues.append(Issue(path + "." + hold_field, "INVALID_POLICY_STATUS",
                                    "a held record is not clean"))
        # Fee / deposit conflation: a refundable amount is a deposit and lives in
        # other_charges under its own kind, never in pet_fee.
        fee = facts.get("pet_fee")
        if isinstance(fee, Mapping) and fee.get("refundable") is True:
            issues.append(Issue(path + ".facts.pet_fee.refundable", "FEE_DEPOSIT_CONFLATION",
                                "a refundable amount is a deposit: other_charges[kind=%s], not pet_fee"
                                % enums.CHARGE_REFUNDABLE_DEPOSIT))
        for legacy in ("pet_deposit", "deposit", "fee", "fee_basis", "fee_currency"):
            if legacy in facts:
                issues.append(Issue(path + ".facts." + legacy, "FEE_DEPOSIT_CONFLATION",
                                    "%r is not a schema fact field; use pet_fee / other_charges" % legacy))
        # Partition agreement: the row must be published in the partition.
        if partition_state and partition_state.get(key) != enums.PUBLISHED_PET_FRIENDLY:
            issues.append(Issue(path, "UNRESOLVED_PROMOTED_CLEAN",
                                "partition state for %r is %r, not %s"
                                % (key, partition_state.get(key), enums.PUBLISHED_PET_FRIENDLY)))
        # Display join: exactly one seed row by the record's join key -- the
        # ``key`` site_data.load_published_hotel_policy_facts indexes by (a
        # display rename lives in the name, the key stays the join).
        join_key = str(record.get("key") or normalize_name(str(record.get("name") or "")))
        matches = seed_by_norm.get(join_key, [])
        if len(matches) != 1:
            issues.append(Issue(path + ".key", "NO_DISPLAY_ROW" if not matches else "AMBIGUOUS_DISPLAY_ROW",
                                "%d seed rows match join key %r (the verified-only join fails closed)"
                                % (len(matches), join_key)))
        # Route: the record's source must be the identity's own first-party
        # endpoint. The routing shard is ACQUISITION authority ("nothing in the
        # publication path reads this file"; a published identity may hold no
        # active route -- the Cincinnati precedent), so it binds only when it
        # carries a usable record; the census's official_url binds otherwise.
        # The first-party gate (fast lane rule C) judges the page itself.
        route = route_by_key.get(key)
        source_domains = sorted({registrable_domain(u) for u in _record_source_urls(record)} - {""})
        if not source_domains:
            issues.append(Issue(path + ".source_url", "INVALID_ROUTE",
                                "a policy record must cite the page it was read from"))
        for source_domain in source_domains:
            if source_domain in IR.NEVER_OFFICIAL_DOMAINS:
                issues.append(Issue(path + ".source_url", "INVALID_ROUTE",
                                    "%r is never an official property source" % source_domain))
            elif route is not None:
                route_domain = registrable_domain(str(route.get("official_property_url") or ""))
                if source_domain != route_domain:
                    issues.append(Issue(path + ".source_url", "INVALID_ROUTE",
                                        "record read %r but the identity is routed to %r"
                                        % (source_domain, route_domain)))
            else:
                census_row = census_by_key.get(key) or {}
                official_url = str(census_row.get("official_url") or census_row.get("_official_url") or "")
                official = registrable_domain(official_url)
                if official and official != source_domain and not _same_brand_family(
                        source_domain, official_url, str(census_row.get("brand") or census_row.get("_brand") or "")):
                    issues.append(Issue(path + ".source_url", "INVALID_ROUTE",
                                        "record read %r but the census binds the identity to %r"
                                        % (source_domain, official)))
        # Evidence binding: every publication-grade entry binds to a reference
        # that names THIS identity and the same page.
        for e_index, entry in enumerate(record.get("evidence") or ()):
            if not isinstance(entry, Mapping):
                continue
            if entry.get("artifact_class") != enums.PUBLICATION_GRADE_EVIDENCE:
                continue
            digest = SMP.normalise_sha256(str(entry.get("artifact_sha256") or ""))
            e_path = "%s.evidence[%d]" % (path, e_index)
            if not digest:
                continue    # already reported by the evidence contract
            reference = ref_by_hash.get((key, digest))
            if reference is None:
                other = [r for (k, h), r in ref_by_hash.items() if h == digest]
                if other:
                    issues.append(Issue(e_path, "POLICY_EVIDENCE_IDENTITY_MISMATCH",
                                        "artifact %s is bound to %r, not %r"
                                        % (digest[:23], other[0]["identity_key"], key)))
                else:
                    issues.append(Issue(e_path, "MISSING_EVIDENCE_BINDING",
                                        "artifact %s has no evidence reference for %r" % (digest[:23], key)))
                continue
            if str(entry.get("source_url") or "") != str(reference.get("source_url") or ""):
                issues.append(Issue(e_path + ".source_url", "POLICY_EVIDENCE_IDENTITY_MISMATCH",
                                    "entry cites %r, reference was captured from %r"
                                    % (entry.get("source_url"), reference.get("source_url"))))

    # ---- verified-no-pets records --------------------------------------- #
    exclusions = [dict(r) for r in inputs.verified_no_pets_records]
    try:
        HE.validate(build_exclusions_shard(market_id, exclusions))
    except Exception as exc:
        issues.append(Issue("verified_no_pets_records", "EXCLUSION_CONTRACT", str(exc)[:300]))
    for index, record in enumerate(exclusions):
        path = "verified_no_pets_records[%d]" % index
        key = _record_identity({"identity_key": "", "name": record.get("canonical_name")})
        if str(record.get("market_id") or "") != market_id:
            issues.append(Issue(path + ".market_id", "INVALID_MARKET_ASSIGNMENT",
                                "exclusion declares %r, package is for %r" % (record.get("market_id"), market_id)))
        if record.get("exclusion_state") == HE.VERIFIED_NO_PETS:
            if census_keys and key not in census_keys:
                issues.append(Issue(path, "MISSING_IDENTITY", "identity %r is not in the census" % key))
            if key in pf_keys:
                issues.append(Issue(path, "CONFLICTING_STATUS",
                                    "%r is both pet-friendly and verified-no-pets" % key))
            if partition_state and partition_state.get(key) != enums.VERIFIED_NO_PETS:
                issues.append(Issue(path, "UNRESOLVED_PROMOTED_CLEAN",
                                    "partition state for %r is %r, not %s"
                                    % (key, partition_state.get(key), enums.VERIFIED_NO_PETS)))
            digest = SMP.normalise_sha256(str(record.get("source_hash") or ""))
            if digest and (key, digest) not in ref_by_hash:
                issues.append(Issue(path + ".source_hash", "MISSING_EVIDENCE_BINDING",
                                    "artifact %s has no evidence reference for %r" % (digest[:23], key)))

    # ---- public routes: the routes the changed market will publish -------- #
    public_routes: List[str] = []
    if market is not None:
        entries: List[Tuple[str, Dict]] = []
        for record in pf_records:
            name = str(record.get("name") or "")
            try:
                entries.append((hotel_route(market, name), {"hotel": name}))
            except MarketRouteError as exc:
                issues.append(Issue("pet_friendly_records", "INVALID_ROUTE", str(exc)))
        published_corridors = sorted({str(census_by_key.get(_record_identity(r), {}).get("corridor")
                                          or r.get("corridor") or "") for r in pf_records} - {""})
        for corridor_id in published_corridors:
            if corridor_id in corridor_ids:
                entries.append((corridor_route(market, market.corridor_by_id(corridor_id)),
                                {"corridor": corridor_id}))
        try:
            public_routes = list(build_route_table(entries))
        except MarketRouteError as exc:
            issues.append(Issue("pet_friendly_records", "INVALID_ROUTE", str(exc)))

    # ---- intended delta and parent live state ----------------------------- #
    delta = OrderedDict(inputs.intended_delta)
    if delta.get("market_id") != market_id:
        issues.append(Issue("intended_delta.market_id", "WRONG_MARKET", "delta must name the package market"))
    parent = OrderedDict(inputs.parent_live_state)

    if issues:
        raise PackageWriteError(_dedupe(issues))

    # ---- assemble the body (nothing above wrote a byte) ------------------- #
    fresh: "OrderedDict[str, Any]" = OrderedDict((
        ("census_count", len(census_keys)),
        ("published_pet_friendly", len(pf_records)),
        ("verified_no_pets", sum(1 for e in exclusions if e.get("exclusion_state") == HE.VERIFIED_NO_PETS)),
        ("out_of_category", sum(1 for e in exclusions if e.get("exclusion_state") == HE.OUT_OF_CURRENT_CATEGORY)),
        ("unresolved", len(unresolved_rows)),
        ("public_routes", len(public_routes)),
    ))
    if retired_outside_census:                      # recorded only when present
        fresh["retired_routes_outside_census"] = len(retired_outside_census)
    fresh["evidence_references"] = len(references)
    # Whether the reference table came from an independent capture manifest
    # (the acquisition run's own record of what it fetched) or was derived from
    # the records themselves. A derived table can prove that one artifact binds
    # one identity; only a supplied one can prove a record cites a page that
    # was actually captured for it.
    fresh["evidence_references_source"] = ("supplied_capture_manifest" if inputs.evidence_references is not None
                                           else "derived_from_records")
    fresh["evidence_artifacts_available"] = sum(1 for r in references if r["artifact_available"])
    fresh["paid_evidence_references"] = sum(1 for r in references if r.get("paid_reservation"))
    if inputs.coverage_scorecard:
        # A RE-DERIVATION (the lane's rule L, a revalidation) carries the
        # package's own scorecard: keep it byte-for-byte so an additive writer
        # field cannot change a sealed package's digest, but refuse a count
        # that no longer agrees with the sections.
        scorecard = OrderedDict(inputs.coverage_scorecard)
        for key, value in fresh.items():
            if key in scorecard and key != "evidence_references_source" and scorecard[key] != value:
                issues.append(Issue("coverage_scorecard.%s" % key, "SCORECARD_MISMATCH",
                                    "scorecard says %r, the sections derive %r" % (scorecard[key], value)))
        if issues:
            raise PackageWriteError(_dedupe(issues))
    else:
        scorecard = fresh
    scorecard["counts_by_partition_state"] = OrderedDict(sorted(reconciliation.counts_by_state.items()))

    body: "OrderedDict[str, Any]" = OrderedDict((
        ("schema", SMP.SCHEMA),
        ("market_id", market_id),
        ("created_from_source_sha", str(inputs.created_from_source_sha)),
        ("execution_zone", str(inputs.execution_zone)),
        ("census", _plain(census_doc)),
        ("identity_records", identity_records),
        ("market", _plain(inputs.market)),
        ("official_routes", routes),
        ("pet_friendly_records", pf_records),
        ("verified_no_pets_records", exclusions),
        ("seed_rows", [OrderedDict((c, str(r.get(c, ""))) for c in SEED_COLUMNS) for r in seed_rows]),
        ("partition", _plain(partition_doc)),
        ("evidence_references", references),
        ("evidence_hashes", evidence_hashes),
        ("unresolved_rows", unresolved_rows),
        ("founder_holds", [_plain(h) for h in inputs.founder_holds]),
        ("intended_delta", delta),
        ("parent_live_state", parent),
        ("dependency_input_digests", OrderedDict(sorted(
            (k, SMP.normalise_sha256(v)) for k, v in inputs.dependency_input_digests.items()))),
        ("builder_version", SMP.BUILDER_VERSION),
        ("contract_versions", OrderedDict(CONTRACT_VERSIONS)),
        ("coverage_scorecard", scorecard),
        ("validation_state", SMP.VALIDATION_STATE_SEALED),
    ))
    sealed = SMP.seal(body, sealed_at=sealed_at)
    shape_issues = SMP.validate(sealed)
    if shape_issues:
        raise PackageWriteError(shape_issues)
    return sealed


def _dedupe(issues: Sequence[Issue]) -> List[Issue]:
    seen: Set[Tuple[str, str, str]] = set()
    out: List[Issue] = []
    for issue in issues:
        if tuple(issue) in seen:
            continue
        seen.add(tuple(issue))
        out.append(issue)
    return out


def _plain(document: Any) -> Any:
    """A JSON round-trip: detaches the package from the caller's objects."""
    return json.loads(json.dumps(document, ensure_ascii=False), object_pairs_hook=OrderedDict)


def _identity_records(census_rows: Sequence[Mapping], relations: Mapping[str, Mapping],
                      issues: List[Issue]) -> List["OrderedDict[str, Any]"]:
    out: List["OrderedDict[str, Any]"] = []
    for row in census_rows:
        key = _record_identity(row)
        if not key:
            continue
        name = str(row.get("canonical_name") or row.get("display_name") or "")
        relation = relations.get(key)
        record: "OrderedDict[str, Any]" = OrderedDict((
            ("identity_key", key),
            ("canonical_name", name),
            ("slug", str(row.get("slug") or slugify(name))),
            ("street", str(row.get("address") or row.get("street") or "")),
            ("city", str(row.get("city") or "")),
            ("state", str(row.get("state") or "")),
            ("postal_code", str(row.get("postal_code") or "")[:5]),
            ("phone", str(row.get("phone") or "")),
            ("brand_family", str(row.get("brand") or row.get("_brand") or "")),
            ("property_code", str(row.get("property_code") or row.get("_property_code") or "")),
            ("official_url", str(row.get("official_url") or row.get("_official_url") or "")),
            ("corridor", str(row.get("corridor") or "")),
            ("aliases", sorted({str(a) for a in (row.get("identity_key_aliases") or ())
                                if str(a) != key})),
            ("collision_state", str(row.get("collision_state") or enums.COLLISION_NONE)),
        ))
        if relation is not None:
            record["relation"] = OrderedDict(relation)
        out.append(record)
    return out


def _same_premises_issues(identity_records: Sequence[Mapping]) -> List[Issue]:
    """Two identities on one premises must be proven distinct or declared.

    Not naive same-address uniqueness: the exclusions contract's
    ``co_located_distinct`` admits a pair with distinct canonical first-party
    URLs and distinct brand-scoped property codes, and an explicit declared
    relation (a founder ruling, a same-campus resolution) admits any pair. A
    pair that is neither proven nor declared is refused -- as is a pair whose
    URLs or codes say ONE property.
    """
    out: List[Issue] = []
    by_premises: Dict[str, List[Mapping]] = {}
    for record in identity_records:
        key = _premises_key(record.get("street", ""), record.get("postal_code", ""))
        if key:
            by_premises.setdefault(key, []).append(record)
    for premises, records in sorted(by_premises.items()):
        if len(records) < 2:
            continue
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                a, b = records[i], records[j]
                declared = _declared_distinct(a, b)
                verdict, why = HE.co_located_distinct(
                    {"canonical_name": a["canonical_name"], "official_url": a["official_url"]},
                    {"canonical_name": b["canonical_name"], "official_url": b["official_url"]})
                if verdict == HE.CO_LOCATED_DUPLICATE and not (a.get("relation") or b.get("relation")):
                    out.append(Issue("identity_records", "SAME_PREMISES_DUPLICATE",
                                     "%r and %r at %s: %s" % (a["identity_key"], b["identity_key"], premises, why)))
                elif verdict != HE.CO_LOCATED_DISTINCT and not declared:
                    out.append(Issue("identity_records", "SAME_PREMISES_UNPROVEN",
                                     "%r and %r share premises %s and are neither mechanically "
                                     "distinct (%s) nor declared related by a ruling"
                                     % (a["identity_key"], b["identity_key"], premises, why)))
    return out


def _declared_distinct(a: Mapping, b: Mapping) -> bool:
    for x, y in ((a, b), (b, a)):
        relation = x.get("relation")
        if isinstance(relation, Mapping) and relation.get("type") in (
                SMP.RELATION_CO_LOCATED_DISTINCT, SMP.RELATION_REBRAND_OF, SMP.RELATION_SUPERSEDES) \
                and relation.get("related_identity_key") == y.get("identity_key") \
                and relation.get("ruling_ref"):
            return True
    for x in (a, b):
        if x.get("collision_state") == enums.COLLISION_RESOLVED:
            return True
    return False


def _evidence_references(inputs: PackageInputs, issues: List[Issue]
                         ) -> Tuple[List["OrderedDict[str, Any]"], "OrderedDict[str, str]"]:
    """Explicit references when supplied; otherwise one per (identity, artifact)
    derived from the records' own publication-grade entries."""
    references: List["OrderedDict[str, Any]"] = []
    if inputs.evidence_references is not None:
        for ref in inputs.evidence_references:
            record = OrderedDict(ref)
            record["artifact_sha256"] = SMP.normalise_sha256(str(record.get("artifact_sha256") or ""))
            references.append(record)
    else:
        seen: Set[Tuple[str, str]] = set()
        for record in inputs.pet_friendly_records:
            key = _record_identity(record)
            for entry in record.get("evidence") or ():
                if not isinstance(entry, Mapping) or entry.get("artifact_class") != enums.PUBLICATION_GRADE_EVIDENCE:
                    continue
                digest = SMP.normalise_sha256(str(entry.get("artifact_sha256") or ""))
                if not digest or (key, digest) in seen:
                    continue
                seen.add((key, digest))
                references.append(_reference(key, digest, entry, inputs))
        for record in inputs.verified_no_pets_records:
            key = _record_identity({"identity_key": "", "name": record.get("canonical_name")})
            digest = SMP.normalise_sha256(str(record.get("source_hash") or ""))
            if not digest or (key, digest) in seen:
                continue
            seen.add((key, digest))
            references.append(_reference(key, digest, {
                "source_url": record.get("source_url"), "captured_at": record.get("observed_at"),
                "artifact_kind": enums.ARTIFACT_RENDERED_HTML,
                "capture_method": record.get("capture_method") or record.get("capture_lane") or "recorded",
                "source_grade": record.get("source_grade") or enums.GRADE_PT1_FIRST_PARTY,
            }, inputs))
    hashes: "OrderedDict[str, str]" = OrderedDict()
    identity_of_artifact: Dict[str, str] = {}
    for index, ref in enumerate(references):
        ev_ref = str(ref.get("evidence_ref") or "")
        if ev_ref in hashes:
            issues.append(Issue("evidence_references[%d]" % index, "DUPLICATE_REF",
                                "evidence_ref %r declared twice" % ev_ref))
        hashes[ev_ref] = str(ref.get("artifact_sha256") or "")
        # One captured page is one property's page: an artifact bound to two
        # identities is a wrong-property binding for at least one of them.
        digest = str(ref.get("artifact_sha256") or "")
        owner = str(ref.get("identity_key") or "")
        if digest in identity_of_artifact and identity_of_artifact[digest] != owner:
            issues.append(Issue("evidence_references[%d]" % index, "POLICY_EVIDENCE_IDENTITY_MISMATCH",
                                "artifact %s is bound to both %r and %r"
                                % (digest[:23], identity_of_artifact[digest], owner)))
        identity_of_artifact.setdefault(digest, owner)
        if is_paid_lane(str(ref.get("capture_lane") or "")) and not ref.get("paid_reservation"):
            # Recorded, not refused here: rule O of the fast lane decides whether
            # a package may depend on an uncoordinated paid acquisition. The
            # writer's job is to make the dependency VISIBLE.
            ref["paid_reservation"] = None
    for ref in references:
        if ref.get("paid_reservation") is None:
            ref.pop("paid_reservation", None)
    return references, OrderedDict(sorted(hashes.items()))


def _reference(identity_key: str, digest: str, entry: Mapping, inputs: PackageInputs
               ) -> "OrderedDict[str, Any]":
    ref_id = "ref:%s:%s" % (slugify(identity_key), digest.split(":", 1)[1][:16])
    reservation = inputs.paid_reservations.get(digest) or inputs.paid_reservations.get(digest.split(":", 1)[1])
    record: "OrderedDict[str, Any]" = OrderedDict((
        ("evidence_ref", ref_id),
        ("identity_key", identity_key),
        ("artifact_sha256", digest),
        ("source_url", str(entry.get("source_url") or "")),
        ("captured_at", str(entry.get("captured_at") or "")),
        ("artifact_kind", EVIDENCE.canonical_artifact_kind(str(entry.get("artifact_kind") or ""))),
        ("capture_lane", str(entry.get("capture_method") or entry.get("capture_lane") or "")),
        ("source_grade", EVIDENCE.canonical_source_grade(str(entry.get("source_grade") or ""))),
        ("artifact_available", False),
    ))
    if reservation:
        record["paid_reservation"] = OrderedDict(reservation)
    return record


# --------------------------------------------------------------------------- #
# Proposed authority structures: what the package becomes on disk.
# --------------------------------------------------------------------------- #

def proposed_authority(package: Mapping) -> "OrderedDict[str, Any]":
    """The authority documents a package proposes, keyed by repository-relative
    path. These are the SAME shapes the registered markets commit, produced
    from one proposed state -- never copied from a sibling market."""
    market_id = str(package["market_id"])
    us = market_id.replace("-", "_")
    policy_package = OrderedDict((
        ("schema_version", str(package["contract_versions"]["policy_schema"])),
        ("market", market_id),
        ("market_id", market_id),
        ("package_id", package["package_id"]),
        ("hotels", list(package["pet_friendly_records"])),
    ))
    # Records may carry their own schema_version (1.2 / 1.3); the package
    # header states the newest the contract accepts, records keep their own.
    versions = {str(r.get("schema_version") or "") for r in package["pet_friendly_records"]}
    if len(versions) == 1 and versions != {""}:
        policy_package["schema_version"] = versions.pop()
    seed_text = _render_seed_csv(package["seed_rows"])
    return OrderedDict((
        ("launch_packages/pettripfinder/markets/%s.json" % market_id, package["market"]),
        ("launch_packages/pettripfinder/identity_census/%s.json" % market_id, package["census"]),
        ("launch_packages/pettripfinder/hotel_policy_facts_%s.json" % market_id, policy_package),
        ("launch_packages/pettripfinder/markets/authority/%s/hotel_exclusions.json" % market_id,
         build_exclusions_shard(market_id, package["verified_no_pets_records"])),
        ("launch_packages/pettripfinder/markets/authority/%s/identity_routing.json" % market_id,
         build_routing_shard(market_id, package["official_routes"],
                             source_batches=["sealed package %s" % package["package_id"]])),
        ("launch_packages/pettripfinder/markets/authority/%s/seed_businesses.csv" % market_id, seed_text),
        ("launch_packages/pettripfinder/%s_final_partition_package.json" % us, package["partition"]),
    ))


def _render_seed_csv(rows: Sequence[Mapping[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(SEED_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in SEED_COLUMNS})
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Adapter: a registered market's committed authority as package inputs.
#
# Reads only; used to seal a FROZEN copy of a live market (the pilot) and by
# the adversarial fixtures that mutate one field of a real state.
# --------------------------------------------------------------------------- #

def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def _source_sha(repo_root: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root),
                              capture_output=True, check=True).stdout.decode().strip()
    except Exception:
        return "0000000"


def committed_partition_path(market_id: str, launch_package: Optional[Path] = None) -> Optional[Path]:
    """The partition of record for a registered market.

    Three tables named partitions (ATLAS-THROUGHPUT-001 release model,
    observation 1). The manifest builder's table is the one the release
    contract's ``unresolved`` count is derived from, so it wins; second is the
    assembler's lookup, which since PTF-FINAL-ASSEMBLER-REGISTERED-MARKET-
    DISCOVERY-001 is ``market_partition_resolution`` (the market's own release
    contract, or the frozen legacy table) rather than a table in the
    assembler; the caller's newest-file glob remains the last resort for
    fixtures that commit no contract.
    """
    from scripts.pettripfinder.build_market_manifest import _PARTITION_FILES
    from scripts.pettripfinder.assemble_production_site import _partition_path
    lp = Path(launch_package) if launch_package else LAUNCH_PACKAGE
    name = _PARTITION_FILES.get(market_id)
    if name and (lp / name).is_file():
        return lp / name
    path = _partition_path(market_id)
    if path is not None and (lp / Path(path).name).is_file():
        return lp / Path(path).name
    return None


def inputs_from_committed_market(market_id: str, *, execution_zone: str,
                                 intended_delta: Mapping, parent_live_state: Mapping,
                                 launch_package: Optional[Path] = None,
                                 source_sha: Optional[str] = None) -> PackageInputs:
    """A registered market's committed authority, read as package inputs."""
    from scripts.pettripfinder.site_data import published_facts_path

    lp = Path(launch_package) if launch_package else LAUNCH_PACKAGE
    us = market_id.replace("-", "_")
    paths: "OrderedDict[str, Path]" = OrderedDict((
        ("market", lp / "markets" / ("%s.json" % market_id)),
        ("census", lp / "identity_census" / ("%s.json" % market_id)),
        # Columbus keeps the unsuffixed package name; site_data owns that rule.
        ("policy_package", lp / published_facts_path(market_id).name),
        ("exclusions", lp / "markets" / "authority" / market_id / "hotel_exclusions.json"),
        ("routing", lp / "markets" / "authority" / market_id / "identity_routing.json"),
        ("seed", lp / "markets" / "authority" / market_id / "seed_businesses.csv"),
    ))
    partition = committed_partition_path(market_id, lp)
    if partition is None:
        candidates = sorted(lp.glob("%s_final_partition_*.json" % us))
        partition = candidates[-1] if candidates else None
    if partition is not None:
        paths["partition"] = partition
    missing = [k for k, p in paths.items() if not p.is_file()]
    if missing:
        raise FileNotFoundError("market %r commits no %s" % (market_id, missing))
    digests = OrderedDict((k, SMP.sha256_bytes(p.read_bytes())) for k, p in paths.items())
    with paths["seed"].open(encoding="utf-8") as f:
        seed_rows = list(csv.DictReader(f))
    partition_doc = _read_json(paths["partition"]) if "partition" in paths else OrderedDict(
        (("schema", PARTITION.SCHEMA), ("market_id", market_id), ("items", [])))
    return PackageInputs(
        market_id=market_id,
        execution_zone=execution_zone,
        created_from_source_sha=source_sha or _source_sha(lp.parents[1]),
        market=_read_json(paths["market"]),
        census=_read_json(paths["census"]),
        pet_friendly_records=list(_read_json(paths["policy_package"]).get("hotels") or ()),
        verified_no_pets_records=list(_read_json(paths["exclusions"]).get("exclusions") or ()),
        official_routes=list(_read_json(paths["routing"]).get("routes") or ()),
        seed_rows=seed_rows,
        partition=partition_doc,
        intended_delta=OrderedDict(intended_delta),
        parent_live_state=OrderedDict(parent_live_state),
        dependency_input_digests=digests,
    )


__all__ = [
    "CONTRACT_VERSIONS", "PET_FRIENDLY_STATUSES", "PAID_LANE_PREFIXES",
    "PackageWriteError", "PackageInputs", "build_sealed_package", "proposed_authority",
    "inputs_from_committed_market", "committed_partition_path", "is_paid_lane",
    "registrable_domain",
]

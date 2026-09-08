"""ATLAS-THROUGHPUT-003 -- the whole-release identity/route index.

Global knowledge without global rendering. A :class:`MarketIndex` is what
one market contributes to the composed release -- every published identity
with its canonical key, display name, public route, premises key, brand
family and property code, plus the corridor and market routes -- derived
from the SAME committed authority and the SAME route helpers the assembler
publishes from (``markets.routes.hotel_route`` / ``corridor_route``,
``site_data.verified_public_hotels``, ``build_market_manifest.build_package``).
A :class:`ReleaseIndex` is the set of market indexes for one release.

:func:`compare` sets the CURRENT VERIFIED LIVE release against a PROPOSED one
and reports every forbidden difference: a live market gone, an unrelated
profile or route gone, an identity claimed by two markets, a route claimed
twice, an identity that moved market, a property deleted or a market's
membership changed without a declared intent. Everything is O(data): the
cost is the number of profiles in the release, never a render.

:func:`current_verified_live` reads what production actually serves -- the
newest DEPLOYED deployment record, the global deployment manifest and the
deployment-state pin -- and refuses to call anything "live" those three do not
agree on.
"""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import sealed_market_package as SMP
from scripts.pettripfinder.contracts.identity_key import IdentityKeyError, ptf_identity_key
from scripts.pettripfinder.markets.contract import MarketConfig, parse_market
from scripts.pettripfinder.markets.routes import corridor_route, hotel_route, market_route
from scripts.pettripfinder.site_data import normalize_name

REPO_ROOT = SMP.REPO_ROOT
DEPLOY_DIR = REPO_ROOT / "deploy" / "netlify"
PINS_DIR = REPO_ROOT / "tests" / "pettripfinder" / "pins"

INDEX_SCHEMA = "ptf-release-index/1.0"

# Finding codes.
MISSING_LIVE_MARKET = "MISSING_LIVE_MARKET"
MISSING_UNRELATED_PROFILE = "MISSING_UNRELATED_PROFILE"
MISSING_UNRELATED_ROUTE = "MISSING_UNRELATED_ROUTE"
CROSS_MARKET_IDENTITY_COLLISION = "CROSS_MARKET_IDENTITY_COLLISION"
DUPLICATE_ROUTE = "DUPLICATE_ROUTE"
OWNERSHIP_MOVEMENT = "OWNERSHIP_MOVEMENT"
UNEXPECTED_PROPERTY_DELETION = "UNEXPECTED_PROPERTY_DELETION"
UNEXPECTED_MEMBERSHIP_CHANGE = "UNEXPECTED_MEMBERSHIP_CHANGE"
UNINTENDED_ADDITION = "UNINTENDED_ADDITION"
UNINTENDED_UPDATE = "UNINTENDED_UPDATE"
UNINTENDED_ROUTE_CHANGE = "UNINTENDED_ROUTE_CHANGE"
INTENT_NOT_REALISED = "INTENT_NOT_REALISED"
DELTA_MISMATCH = "DELTA_MISMATCH"
UNRELATED_MARKET_CHANGED = "UNRELATED_MARKET_CHANGED"


class ReleaseIndexError(RuntimeError):
    """The index could not be derived or the live state is inconsistent."""


@dataclass(frozen=True)
class ProfileEntry:
    identity_key: str            # CANONICAL: ptf_identity_key of the published display name
    declared_identity_key: str   # what the record itself declares (may be defective)
    name: str
    route: str
    market_id: str
    premises_key: str
    official_url: str
    brand_family: str
    property_code: str
    record_digest: str

    def to_dict(self) -> "OrderedDict[str, str]":
        return OrderedDict((k, getattr(self, k)) for k in (
            "identity_key", "declared_identity_key", "name", "route", "market_id",
            "premises_key", "official_url", "brand_family", "property_code", "record_digest"))


@dataclass
class MarketIndex:
    market_id: str
    market_slug: str
    route_mode: str
    participating: bool
    source: str                                  # committed | package
    profiles: "OrderedDict[str, ProfileEntry]"
    corridor_routes: Tuple[str, ...]
    market_route: str
    verified_no_pets: int = 0
    census_count: Optional[int] = None
    package_id: str = ""

    @property
    def hotel_routes(self) -> Tuple[str, ...]:
        return tuple(sorted(p.route for p in self.profiles.values()))

    @property
    def routes(self) -> Tuple[str, ...]:
        return tuple(sorted(set(self.hotel_routes) | set(self.corridor_routes) | {self.market_route}))

    def to_dict(self) -> "OrderedDict[str, Any]":
        return OrderedDict((
            ("market_id", self.market_id), ("market_slug", self.market_slug),
            ("route_mode", self.route_mode), ("participating", self.participating),
            ("source", self.source), ("package_id", self.package_id),
            ("census_count", self.census_count), ("verified_no_pets", self.verified_no_pets),
            ("market_route", self.market_route),
            ("corridor_routes", list(self.corridor_routes)),
            ("profiles", [self.profiles[k].to_dict() for k in sorted(self.profiles)]),
        ))

    def digest(self) -> str:
        return SMP.sha256_text(SMP.canonical_json(self.to_dict()))


@dataclass
class ReleaseIndex:
    markets: "OrderedDict[str, MarketIndex]" = field(default_factory=OrderedDict)
    label: str = ""

    @property
    def participating(self) -> Tuple[str, ...]:
        return tuple(sorted(m for m, idx in self.markets.items() if idx.participating))

    @property
    def total_profiles(self) -> int:
        return sum(len(idx.profiles) for idx in self.markets.values() if idx.participating)

    def profile_counts(self) -> "OrderedDict[str, int]":
        return OrderedDict((m, len(self.markets[m].profiles)) for m in self.participating)

    def to_dict(self) -> "OrderedDict[str, Any]":
        return OrderedDict((
            ("schema", INDEX_SCHEMA), ("label", self.label),
            ("participating_markets", list(self.participating)),
            ("total_profiles", self.total_profiles),
            ("markets", [self.markets[m].to_dict() for m in sorted(self.markets)]),
        ))

    def digest(self) -> str:
        return SMP.sha256_text(SMP.canonical_json(OrderedDict(
            (k, v) for k, v in self.to_dict().items() if k != "label")))


# --------------------------------------------------------------------------- #
# Deriving an index.
# --------------------------------------------------------------------------- #

def canonical_identity(name: str) -> str:
    """The contract's identity for a published display name."""
    try:
        return ptf_identity_key(name)
    except IdentityKeyError:
        return normalize_name(name)


def _identity(record: Mapping, name: str) -> str:
    """The CANONICAL identity of a published record: derived from the name it
    publishes under, by the identity-key contract. The record's own
    ``identity_key`` is carried beside it as ``declared_identity_key`` --
    production carries records whose declared key is a bare brand token
    (``tru``, ``hampton``), and indexing by those would report three hotels
    in three markets as one identity."""
    return canonical_identity(name)


def _record_digest(record: Mapping) -> str:
    """The identity of a published record: its facts, evidence and status --
    never its approval bookkeeping, which may be re-signed without a change."""
    body = OrderedDict((k, record.get(k)) for k in (
        "identity_key", "name", "facts", "service_animal_statement", "computation_class",
        "evidence", "source_url", "verification_state", "withheld_fields", "schema_version"))
    return SMP.sha256_text(SMP.canonical_json(body))


def _entries(market: MarketConfig, pf_records: Sequence[Mapping],
             seed_rows: Sequence[Mapping[str, str]]) -> "OrderedDict[str, ProfileEntry]":
    seed_by_key: Dict[str, Mapping[str, str]] = {}
    for row in seed_rows:
        if row.get("category") == "pet-friendly-hotels":
            seed_by_key[normalize_name(str(row.get("name") or ""))] = row
    out: "OrderedDict[str, ProfileEntry]" = OrderedDict()
    for record in pf_records:
        join_key = str(record.get("key") or normalize_name(str(record.get("name") or "")))
        seed = seed_by_key.get(join_key)
        if seed is None:
            raise ReleaseIndexError("published record %r has no seed row in %s (the join fails closed)"
                                    % (join_key, market.market_id))
        name = str(seed.get("name") or record.get("name") or "")
        source_url = str(record.get("source_url") or "")
        if not source_url:
            for entry in record.get("evidence") or ():
                if isinstance(entry, Mapping) and entry.get("source_url"):
                    source_url = str(entry["source_url"])
                    break
        family, code = HE.brand_scoped_property_identity(source_url)
        identity = _identity(record, name)
        if identity in out:
            raise ReleaseIndexError("two published records in %s resolve to identity %r"
                                    % (market.market_id, identity))
        out[identity] = ProfileEntry(
            identity_key=identity, declared_identity_key=str(record.get("identity_key") or ""),
            name=name,
            route=hotel_route(market, name), market_id=market.market_id,
            premises_key=HE.address_key(str(seed.get("address") or ""), str(seed.get("postal_code") or "")),
            official_url=source_url, brand_family=family, property_code=code,
            record_digest=_record_digest(record))
    return out


def index_from_committed(market_id: str, *, participating: bool) -> MarketIndex:
    """One registered market's contribution, from its committed authority."""
    from scripts.pettripfinder.build_market_manifest import build_package
    from scripts.pettripfinder.market_ownership import owned_by
    from scripts.pettripfinder.markets.contract import load_markets, market_by_id
    from scripts.pettripfinder.site_data import (load_published_hotel_policy_facts,
                                                 published_facts_path, read_production_rows)

    market = market_by_id(load_markets(), market_id)
    package = build_package(market_id)
    seed_rows = owned_by(read_production_rows(), market_id, context="release index")
    facts = load_published_hotel_policy_facts(market_id)
    path = published_facts_path(market_id)
    records = json.loads(path.read_text(encoding="utf-8-sig")).get("hotels", []) if path.is_file() else []
    published = [r for r in records if str(r.get("key") or normalize_name(str(r.get("name") or ""))) in facts]
    profiles = _entries(market, published, seed_rows)
    routes = tuple(sorted(p.route for p in profiles.values()))
    if routes != tuple(package.hotel_routes):
        raise ReleaseIndexError(
            "index routes for %s disagree with build_market_manifest (%d vs %d)"
            % (market_id, len(routes), len(package.hotel_routes)))
    corridor_routes = published_corridor_routes(market, profiles, seed_rows)
    if corridor_routes != tuple(package.corridor_routes):
        raise ReleaseIndexError(
            "index corridor routes for %s disagree with build_market_manifest (%d vs %d)"
            % (market_id, len(corridor_routes), len(package.corridor_routes)))
    return MarketIndex(
        market_id=market_id, market_slug=market.market_slug, route_mode=market.route_mode,
        participating=participating, source="committed", profiles=profiles,
        corridor_routes=corridor_routes, market_route=market_route(market),
        verified_no_pets=package.verified_no_pets_count,
        census_count=package.confirmed_identity_count)


def published_corridor_routes(market: MarketConfig, profiles: Mapping[str, ProfileEntry],
                              seed_rows: Sequence[Mapping[str, str]]) -> Tuple[str, ...]:
    """The corridor routes the market publishes for these profiles -- the
    SAME deterministic assignment (``markets.assignment.assign_hotels``) the
    generator and ``build_market_manifest`` publish from, including each
    corridor's minimum-count rule."""
    from scripts.pettripfinder.markets.assignment import assign_hotels

    published_names = {p.name for p in profiles.values()}
    verified = [dict(r) for r in seed_rows
                if r.get("category") == "pet-friendly-hotels" and str(r.get("name") or "") in published_names]
    assignment = assign_hotels(market, verified, fail_closed=False)
    return tuple(sorted(corridor_route(market, market.corridor_by_id(cid))
                        for cid in assignment.published))


def index_from_package(package: Mapping, *, participating: bool) -> MarketIndex:
    """A sealed package's contribution, from its own sections."""
    market = parse_market(dict(package["market"]), source="package:%s" % package["package_id"])
    profiles = _entries(market, package["pet_friendly_records"], package["seed_rows"])
    corridor_routes = published_corridor_routes(market, profiles, package["seed_rows"])
    return MarketIndex(
        market_id=str(package["market_id"]), market_slug=market.market_slug,
        route_mode=market.route_mode, participating=participating, source="package",
        profiles=profiles, corridor_routes=corridor_routes, market_route=market_route(market),
        verified_no_pets=sum(1 for e in package["verified_no_pets_records"]
                             if e.get("exclusion_state") == HE.VERIFIED_NO_PETS),
        census_count=int(package["census"].get("count") or len(package["census"].get("hotels") or ())),
        package_id=str(package["package_id"]))


# --------------------------------------------------------------------------- #
# The current verified live release.
# --------------------------------------------------------------------------- #

@dataclass
class LiveState:
    deploy_id: str
    previous_deploy_id: str
    rollback_target: str
    source_commit: str
    bundle_sha256: str
    sitemap_sha256: str
    participating_markets: Tuple[str, ...]
    profile_counts: "OrderedDict[str, int]"
    total_profiles: int
    sitemap_route_count: int
    deployment_record: str
    authorization_id: str
    problems: Tuple[str, ...] = ()
    rollback_record: Optional[str] = None
    rollback_markets: Tuple[str, ...] = ()

    def to_dict(self) -> "OrderedDict[str, Any]":
        return OrderedDict((
            ("live_deploy_id", self.deploy_id), ("previous_deploy_id", self.previous_deploy_id),
            ("rollback_target", self.rollback_target), ("source_commit", self.source_commit),
            ("bundle_sha256", self.bundle_sha256), ("sitemap_sha256", self.sitemap_sha256),
            ("participating_markets", list(self.participating_markets)),
            ("profile_counts", OrderedDict(self.profile_counts)),
            ("total_profiles", self.total_profiles),
            ("sitemap_route_count", self.sitemap_route_count),
            ("deployment_record", self.deployment_record),
            ("authorization_id", self.authorization_id),
            ("rollback_record", self.rollback_record),
            ("rollback_markets", list(self.rollback_markets)),
            ("problems", list(self.problems)),
        ))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def current_verified_live(deploy_dir: Optional[Path] = None,
                          pins_dir: Optional[Path] = None) -> LiveState:
    """What production serves, as three committed records agree it does.

    Fail closed: every disagreement between the newest DEPLOYED record, the
    global manifest and the deployment-state pin is a ``problem``; a caller
    that needs a live state must refuse on any problem. The rollback chain is
    checked here too (H12): the newest record's rollback target must be the
    previous record's deployment, and that record must exist with its own
    market set.
    """
    deploy = Path(deploy_dir) if deploy_dir else DEPLOY_DIR
    pins = Path(pins_dir) if pins_dir else PINS_DIR
    problems: List[str] = []
    records = []
    for path in sorted((deploy / "deployment_records").glob("*.json")):
        doc = _read_json(path)
        if doc.get("final_status") == "DEPLOYED" and doc.get("deployed_at"):
            records.append((str(doc["deployed_at"]), path, doc))
    if not records:
        raise ReleaseIndexError("no DEPLOYED deployment record under %s" % deploy)
    records.sort(key=lambda r: r[0])
    _at, path, record = records[-1]
    by_deploy = {doc.get("deployment_id"): (p, doc) for _a, p, doc in records}

    if record.get("rollback_target") != record.get("previous_deployment_id"):
        problems.append("newest record: rollback_target %r is not previous_deployment_id %r"
                        % (record.get("rollback_target"), record.get("previous_deployment_id")))
    rollback_record = None
    rollback_markets: Tuple[str, ...] = ()
    if len(records) > 1:
        _pat, prev_path, prev = records[-2]
        if prev.get("deployment_id") != record.get("rollback_target"):
            problems.append("rollback_target %r is not the previous DEPLOYED record's deployment %r"
                            % (record.get("rollback_target"), prev.get("deployment_id")))
    target = by_deploy.get(record.get("rollback_target"))
    if target is None:
        problems.append("rollback_target %r has no DEPLOYED record of its own" % record.get("rollback_target"))
    else:
        rollback_record = target[0].name
        rollback_markets = tuple(target[1].get("participating_markets") or ())
        if not rollback_markets or not target[1].get("profile_counts"):
            problems.append("rollback record %s carries no market set" % target[0].name)

    manifest_path = deploy / "global_deployment_manifest.json"
    if manifest_path.is_file():
        manifest = _read_json(manifest_path)
        if manifest.get("bundle_sha256") != record.get("bundle_sha256"):
            problems.append("global manifest bundle %r != deployed bundle %r"
                            % (manifest.get("bundle_sha256"), record.get("bundle_sha256")))
        manifest_markets = [m.get("market_id") if isinstance(m, Mapping) else m
                            for m in (manifest.get("participating_markets") or ())]
        if manifest_markets != list(record.get("participating_markets") or ()):
            problems.append("global manifest participation differs from the deployed record")
        for m in (manifest.get("participating_markets") or ()):
            if isinstance(m, Mapping) and m.get("published_profiles") != \
                    (record.get("profile_counts") or {}).get(m.get("market_id")):
                problems.append("global manifest counts %r profiles for %s, record %r"
                                % (m.get("published_profiles"), m.get("market_id"),
                                   (record.get("profile_counts") or {}).get(m.get("market_id"))))
        if manifest.get("total_published_profiles") != record.get("total_profiles"):
            problems.append("global manifest total_published_profiles %r != record %r"
                            % (manifest.get("total_published_profiles"), record.get("total_profiles")))
    else:
        problems.append("no global deployment manifest")

    pin_path = pins / "deployment_state.json"
    if pin_path.is_file():
        live = (_read_json(pin_path).get("live") or {})
        for key, record_key in (("deploy_id", "deployment_id"), ("bundle_sha256", "bundle_sha256"),
                                ("rollback_target", "rollback_target"), ("total_profiles", "total_profiles"),
                                ("sitemap_route_count", "sitemap_route_count")):
            if live.get(key) != record.get(record_key):
                problems.append("deployment_state pin %s=%r != record %r" % (key, live.get(key), record.get(record_key)))
        if list(live.get("participating_markets") or ()) != list(record.get("participating_markets") or ()):
            problems.append("deployment_state pin participation differs from the deployed record")

    auth_path = deploy / "deployment_authorizations" / ("%s.json" % record.get("authorization_id"))
    if auth_path.is_file():
        auth = _read_json(auth_path)
        if auth.get("bundle_sha256") != record.get("bundle_sha256"):
            problems.append("authorization %s binds bundle %r, record deployed %r"
                            % (auth_path.name, auth.get("bundle_sha256"), record.get("bundle_sha256")))
        if auth.get("authorization_status") != "DEPLOYED":
            problems.append("authorization %s status is %r" % (auth_path.name, auth.get("authorization_status")))
    else:
        problems.append("authorization %r not found" % record.get("authorization_id"))

    return LiveState(
        deploy_id=str(record.get("deployment_id") or ""),
        previous_deploy_id=str(record.get("previous_deployment_id") or ""),
        rollback_target=str(record.get("rollback_target") or ""),
        source_commit=str(record.get("source_commit") or ""),
        bundle_sha256=str(record.get("bundle_sha256") or ""),
        sitemap_sha256=str(record.get("sitemap_sha256") or ""),
        participating_markets=tuple(record.get("participating_markets") or ()),
        profile_counts=OrderedDict((k, int(v)) for k, v in (record.get("profile_counts") or {}).items()),
        total_profiles=int(record.get("total_profiles") or 0),
        sitemap_route_count=int(record.get("sitemap_route_count") or 0),
        deployment_record=path.name,
        authorization_id=str(record.get("authorization_id") or ""),
        problems=tuple(problems),
        rollback_record=rollback_record,
        rollback_markets=rollback_markets,
    )


def live_index(live: Optional[LiveState] = None) -> Tuple[ReleaseIndex, LiveState, List[str]]:
    """The committed authority of every live market, checked against the
    live record's profile counts. Returns ``(index, live_state, problems)``:
    a problem means the committed tree is NOT the live source and nothing
    derived from it may be called CURRENT_VERIFIED_LIVE."""
    from scripts.pettripfinder.market_authority import registered_market_ids

    state = live if live is not None else current_verified_live()
    problems = list(state.problems)
    index = ReleaseIndex(label="CURRENT_VERIFIED_LIVE")
    registered = set(registered_market_ids())
    for market_id in sorted(registered):
        participating = market_id in state.participating_markets
        try:
            index.markets[market_id] = index_from_committed(market_id, participating=participating)
        except Exception as exc:
            problems.append("%s: committed authority does not index: %s" % (market_id, str(exc)[:160]))
    for market_id in state.participating_markets:
        if market_id not in index.markets:
            problems.append("live market %s is not registered in the committed tree" % market_id)
            continue
        expected = state.profile_counts.get(market_id)
        actual = len(index.markets[market_id].profiles)
        if expected != actual:
            problems.append("%s: committed authority publishes %d profiles, live record says %r"
                            % (market_id, actual, expected))
    if index.total_profiles != state.total_profiles:
        problems.append("committed authority totals %d profiles, live record says %d"
                        % (index.total_profiles, state.total_profiles))
    return index, state, problems


# --------------------------------------------------------------------------- #
# Composition and comparison.
# --------------------------------------------------------------------------- #

def compose(live: ReleaseIndex, package_index: MarketIndex, *,
            participates: bool) -> ReleaseIndex:
    """The proposed release: every live market unchanged (the SAME entries,
    never re-derived from the package's view of them) with the package's
    market replaced or added."""
    proposed = ReleaseIndex(label="PROPOSED")
    for market_id, idx in live.markets.items():
        if market_id != package_index.market_id:
            proposed.markets[market_id] = idx
    replaced = MarketIndex(**{**package_index.__dict__, "participating": participates})
    proposed.markets[package_index.market_id] = replaced
    proposed.markets = OrderedDict(sorted(proposed.markets.items()))
    return proposed


def _finding(code: str, market: str, detail: str, **extra: Any) -> "OrderedDict[str, Any]":
    out: "OrderedDict[str, Any]" = OrderedDict((("code", code), ("market_id", market), ("detail", detail)))
    out.update(extra)
    return out


def compare(live: ReleaseIndex, proposed: ReleaseIndex, *, package_market: str,
            intended_delta: Mapping) -> "OrderedDict[str, Any]":
    """Every forbidden difference between the live and proposed releases."""
    started = time.perf_counter()
    findings: List["OrderedDict[str, Any]"] = []
    delta = intended_delta or {}
    intended_removals = set(delta.get("remove_property_ids") or ())
    intended_adds = set(delta.get("add_property_ids") or ())
    intended_updates = set(delta.get("update_property_ids") or ())
    intended_route_adds = set(delta.get("add_routes") or ())
    intended_route_removes = set(delta.get("remove_routes") or ())
    intended_route_changes = {str(c.get("from")): str(c.get("to"))
                              for c in (delta.get("change_routes") or ()) if isinstance(c, Mapping)}
    participation_intent = {str(p.get("market_id")): (p.get("from"), p.get("to"))
                            for p in (delta.get("expected_participation_delta") or ())
                            if isinstance(p, Mapping)}

    # 1. Live markets and their members must survive unless the package is about them.
    for market_id, live_idx in live.markets.items():
        prop_idx = proposed.markets.get(market_id)
        if prop_idx is None:
            findings.append(_finding(MISSING_LIVE_MARKET, market_id,
                                     "live market absent from the proposed release"))
            continue
        if market_id == package_market:
            continue
        if live_idx.participating != prop_idx.participating:
            findings.append(_finding(UNEXPECTED_MEMBERSHIP_CHANGE, market_id,
                                     "participation changed %r -> %r by a package for %s"
                                     % (live_idx.participating, prop_idx.participating, package_market)))
        if prop_idx is not live_idx and prop_idx.digest() != live_idx.digest():
            findings.append(_finding(UNRELATED_MARKET_CHANGED, market_id,
                                     "an unrelated market's index changed under a package for %s"
                                     % package_market))
        for key, entry in live_idx.profiles.items():
            if key not in prop_idx.profiles:
                findings.append(_finding(MISSING_UNRELATED_PROFILE, market_id,
                                         "profile %r (%s) missing" % (key, entry.route), identity_key=key))
        for route in live_idx.routes:
            if route not in prop_idx.routes:
                findings.append(_finding(MISSING_UNRELATED_ROUTE, market_id, "route %s missing" % route, route=route))

    # 2. Cross-market identity and route uniqueness over the WHOLE proposed release.
    owners: Dict[str, str] = {}
    route_owners: Dict[str, Tuple[str, str]] = {}
    for market_id, idx in proposed.markets.items():
        if not idx.participating:
            continue
        for key in idx.profiles:
            if key in owners and owners[key] != market_id:
                findings.append(_finding(CROSS_MARKET_IDENTITY_COLLISION, market_id,
                                         "identity %r is published by %s and %s" % (key, owners[key], market_id),
                                         identity_key=key, other_market=owners[key]))
            owners.setdefault(key, market_id)
        for route in idx.routes:
            claim = (market_id, "route")
            if route in route_owners and route_owners[route][0] != market_id:
                findings.append(_finding(DUPLICATE_ROUTE, market_id,
                                         "route %s claimed by %s and %s" % (route, route_owners[route][0], market_id),
                                         route=route, other_market=route_owners[route][0]))
            route_owners.setdefault(route, claim)

    # 3. Ownership movement: an identity live in market A, proposed in market B.
    live_owner: Dict[str, str] = {}
    for market_id, idx in live.markets.items():
        if idx.participating:
            for key in idx.profiles:
                live_owner[key] = market_id
    for key, market_id in owners.items():
        if key in live_owner and live_owner[key] != market_id:
            findings.append(_finding(OWNERSHIP_MOVEMENT, market_id,
                                     "identity %r moves from %s to %s" % (key, live_owner[key], market_id),
                                     identity_key=key, from_market=live_owner[key]))

    # 4. The package market against its declared intent.
    live_pkg = live.markets.get(package_market)
    prop_pkg = proposed.markets.get(package_market)
    actual_adds: List[str] = []
    actual_removes: List[str] = []
    actual_updates: List[str] = []
    route_adds: List[str] = []
    route_removes: List[str] = []
    if prop_pkg is not None:
        live_profiles = live_pkg.profiles if live_pkg is not None else OrderedDict()
        live_routes = set(live_pkg.routes) if live_pkg is not None and live_pkg.participating else set()
        for key, entry in prop_pkg.profiles.items():
            if key not in live_profiles:
                actual_adds.append(key)
            elif live_profiles[key].record_digest != entry.record_digest or live_profiles[key].route != entry.route:
                actual_updates.append(key)
        for key in live_profiles:
            if key not in prop_pkg.profiles:
                actual_removes.append(key)
        route_adds = sorted(set(prop_pkg.routes) - live_routes)
        route_removes = sorted(live_routes - set(prop_pkg.routes))
        for key in actual_removes:
            if key not in intended_removals:
                findings.append(_finding(UNEXPECTED_PROPERTY_DELETION, package_market,
                                         "profile %r removed without declared intent" % key, identity_key=key))
        for key in actual_adds:
            if key not in intended_adds:
                findings.append(_finding(UNINTENDED_ADDITION, package_market,
                                         "profile %r added without declared intent" % key, identity_key=key))
        for key in actual_updates:
            if key not in intended_updates:
                findings.append(_finding(UNINTENDED_UPDATE, package_market,
                                         "profile %r changed without declared intent" % key, identity_key=key))
        for key in intended_removals:
            if key not in actual_removes:
                findings.append(_finding(INTENT_NOT_REALISED, package_market,
                                         "declared removal of %r did not happen" % key, identity_key=key))
        for key in intended_adds:
            if key not in actual_adds:
                findings.append(_finding(INTENT_NOT_REALISED, package_market,
                                         "declared addition of %r did not happen" % key, identity_key=key))
        changed_from = set(intended_route_changes)
        changed_to = set(intended_route_changes.values())
        for route in route_removes:
            if route not in intended_route_removes and route not in changed_from:
                findings.append(_finding(UNINTENDED_ROUTE_CHANGE, package_market,
                                         "route %s removed without declared intent" % route, route=route))
        for route in route_adds:
            if route not in intended_route_adds and route not in changed_to and live_pkg is not None \
                    and live_pkg.participating:
                findings.append(_finding(UNINTENDED_ROUTE_CHANGE, package_market,
                                         "route %s added without declared intent" % route, route=route))
        expected_profile_delta = delta.get("expected_profile_delta")
        actual_profile_delta = len(prop_pkg.profiles) - len(live_profiles)
        if expected_profile_delta is not None and expected_profile_delta != actual_profile_delta:
            findings.append(_finding(DELTA_MISMATCH, package_market,
                                     "expected_profile_delta %r, actual %d" % (expected_profile_delta, actual_profile_delta)))
        expected_no_pets_delta = delta.get("expected_verified_no_pets_delta")
        actual_no_pets_delta = prop_pkg.verified_no_pets - (live_pkg.verified_no_pets if live_pkg else 0)
        if expected_no_pets_delta is not None and expected_no_pets_delta != actual_no_pets_delta:
            findings.append(_finding(DELTA_MISMATCH, package_market,
                                     "expected_verified_no_pets_delta %r, actual %d"
                                     % (expected_no_pets_delta, actual_no_pets_delta)))
        elif expected_no_pets_delta is None and actual_no_pets_delta != 0:
            findings.append(_finding(DELTA_MISMATCH, package_market,
                                     "verified_no_pets changed by %d without a declared "
                                     "expected_verified_no_pets_delta" % actual_no_pets_delta))
        live_participates = live_pkg.participating if live_pkg is not None else False
        if live_participates != prop_pkg.participating:
            intent = participation_intent.get(package_market)
            if intent != (live_participates, prop_pkg.participating):
                findings.append(_finding(UNEXPECTED_MEMBERSHIP_CHANGE, package_market,
                                         "participation %r -> %r not declared" % (live_participates, prop_pkg.participating)))
    expected_market_delta = delta.get("expected_market_count_delta")
    actual_market_delta = len(proposed.participating) - len(live.participating)
    if expected_market_delta is not None and expected_market_delta != actual_market_delta:
        findings.append(_finding(DELTA_MISMATCH, package_market,
                                 "expected_market_count_delta %r, actual %d" % (expected_market_delta, actual_market_delta)))

    codes = OrderedDict()
    for f in findings:
        codes[f["code"]] = codes.get(f["code"], 0) + 1
    return OrderedDict((
        ("live_digest", live.digest()),
        ("proposed_digest", proposed.digest()),
        ("live_participating", list(live.participating)),
        ("proposed_participating", list(proposed.participating)),
        ("live_total_profiles", live.total_profiles),
        ("proposed_total_profiles", proposed.total_profiles),
        ("package_market", package_market),
        ("actual_delta", OrderedDict((
            ("add_property_ids", sorted(actual_adds)), ("update_property_ids", sorted(actual_updates)),
            ("remove_property_ids", sorted(actual_removes)),
            ("add_routes", route_adds), ("remove_routes", route_removes),
            ("profile_delta", (len(prop_pkg.profiles) if prop_pkg else 0)
                              - (len(live_pkg.profiles) if live_pkg else 0)),
            ("verified_no_pets_delta", (prop_pkg.verified_no_pets if prop_pkg else 0)
                                       - (live_pkg.verified_no_pets if live_pkg else 0)),
            ("market_count_delta", actual_market_delta),
        ))),
        ("finding_counts", codes),
        ("findings", findings),
        ("passed", not findings),
        ("seconds", round(time.perf_counter() - started, 4)),
    ))


# --------------------------------------------------------------------------- #
# Benchmark: the index at N markets, synthesised from real ones.
# --------------------------------------------------------------------------- #

def synthesise(live: ReleaseIndex, target_markets: int) -> ReleaseIndex:
    """Clone real market indexes under new ids until ``target_markets`` exist.
    Every cloned identity and route is re-keyed so the clone collides with
    nothing (a benchmark measures cost, not findings)."""
    out = ReleaseIndex(label="SYNTHETIC_%d" % target_markets)
    out.markets.update(live.markets)
    sources = [idx for idx in live.markets.values() if idx.participating] or list(live.markets.values())
    n = 0
    while len(out.markets) < target_markets:
        base = sources[n % len(sources)]
        n += 1
        suffix = "x%d" % n
        market_id = "%s-%s" % (base.market_id, suffix)
        profiles: "OrderedDict[str, ProfileEntry]" = OrderedDict()
        for key, entry in base.profiles.items():
            new_key = "%s %s" % (key, suffix)
            profiles[new_key] = ProfileEntry(
                identity_key=new_key, declared_identity_key=new_key,
                name="%s %s" % (entry.name, suffix),
                route=entry.route.rstrip("/") + "-" + suffix + "/", market_id=market_id,
                premises_key=entry.premises_key, official_url=entry.official_url,
                brand_family=entry.brand_family, property_code=entry.property_code,
                record_digest=entry.record_digest)
        out.markets[market_id] = MarketIndex(
            market_id=market_id, market_slug="%s-%s" % (base.market_slug, suffix),
            route_mode=base.route_mode, participating=True, source="synthetic", profiles=profiles,
            corridor_routes=tuple(r.rstrip("/") + "-" + suffix + "/" for r in base.corridor_routes),
            market_route=base.market_route.rstrip("/") + "-" + suffix + "/",
            verified_no_pets=base.verified_no_pets, census_count=base.census_count)
    return out


def benchmark(live: ReleaseIndex, package_index: MarketIndex, intended_delta: Mapping,
              sizes: Sequence[int] = (10, 25, 50, 100)) -> List["OrderedDict[str, Any]"]:
    rows: List["OrderedDict[str, Any]"] = []
    for size in sizes:
        big = synthesise(live, size) if size > len(live.markets) else live
        started = time.perf_counter()
        proposed = compose(big, package_index, participates=True)
        report = compare(big, proposed, package_market=package_index.market_id, intended_delta=intended_delta)
        digest_started = time.perf_counter()
        big.digest()
        proposed.digest()
        rows.append(OrderedDict((
            ("markets", len(big.markets)), ("participating", len(big.participating)),
            ("profiles", big.total_profiles),
            ("compose_and_compare_seconds", round(digest_started - started, 4)),
            ("digest_seconds", round(time.perf_counter() - digest_started, 4)),
            ("total_seconds", round(time.perf_counter() - started, 4)),
            ("findings", len(report["findings"])),
        )))
    return rows


__all__ = [
    "INDEX_SCHEMA", "ReleaseIndexError", "ProfileEntry", "MarketIndex", "ReleaseIndex",
    "LiveState", "index_from_committed", "index_from_package", "current_verified_live",
    "live_index", "compose", "compare", "synthesise", "benchmark",
    "MISSING_LIVE_MARKET", "MISSING_UNRELATED_PROFILE", "MISSING_UNRELATED_ROUTE",
    "CROSS_MARKET_IDENTITY_COLLISION", "DUPLICATE_ROUTE", "OWNERSHIP_MOVEMENT",
    "UNEXPECTED_PROPERTY_DELETION", "UNEXPECTED_MEMBERSHIP_CHANGE", "UNINTENDED_ADDITION",
    "UNINTENDED_UPDATE", "UNINTENDED_ROUTE_CHANGE", "INTENT_NOT_REALISED", "DELTA_MISMATCH",
    "UNRELATED_MARKET_CHANGED",
]

"""ATLAS-THROUGHPUT-003 -- stage a sealed package as a repository-shaped tree
and build the changed market from it, without touching committed authority.

A staging tree mirrors the repository layout the loaders expect::

    <stage>/launch_packages/pettripfinder/markets/<every registered market>.json
    <stage>/launch_packages/pettripfinder/markets/<package market>.json
    <stage>/launch_packages/pettripfinder/identity_census/<market>.json
    <stage>/launch_packages/pettripfinder/hotel_policy_facts_<market>.json
    <stage>/launch_packages/pettripfinder/markets/authority/<market>/...
    <stage>/launch_packages/pettripfinder/{identity_routing,hotel_exclusions}.json
    <stage>/launch_packages/pettripfinder/seed_businesses.csv
    <stage>/launch_packages/pettripfinder/ptf_global_authority_manifest.json
    <stage>/launch_packages/pettripfinder/<partition of record>.json
    <stage>/deploy/netlify/release_contracts/<market>.json   (derived)

:func:`overlay` then points every module-level path constant on the build
path at the staging tree -- the SAME constants a test would monkeypatch --
and restores them afterwards. Templates, static assets, control files
(``deploy/netlify/headers.*``, ``redirects``, ``measurement.json``,
``affiliate_providers.json``) stay the repository's: they are shared release
state, not market data.

:func:`build_changed_market` runs the real per-market assembler
(``assemble_netlify_bundle.assemble``) under the overlay, so every gate that
market's bundle owes is the gate it gets, and returns the bundle digest
computed by ``assemble_production_site.bundle_digest`` -- the same formula the
deployer re-hashes.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple

from scripts.pettripfinder import market_package_writer as WRITER
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = SMP.REPO_ROOT

#: Sections of a committed release contract that are release POLICY rather
#: than market facts. A staged contract copies them from the committed
#: contracts, which must all agree (checked); everything else is derived.
SHARED_CONTRACT_SECTIONS = ("canonical", "minimum_release_gates",
                            "forbidden_output_tokens", "publish")


class StagingError(RuntimeError):
    """The package could not be staged or built (fail closed)."""


# --------------------------------------------------------------------------- #
# Materialise the tree.
# --------------------------------------------------------------------------- #

def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, document: Any) -> None:
    _write_text(path, json.dumps(document, indent=1, ensure_ascii=False) + "\n")


def stage_package(package: Mapping, stage_root: Path, *,
                  repo_root: Optional[Path] = None) -> "OrderedDict[str, str]":
    """Write the package's proposed authority into ``stage_root``.

    Returns ``{repo-relative path: sha256}`` of every file written. The tree
    is rebuilt from scratch on every call (a stale staging tree is exactly the
    mutable dependency H10 forbids).
    """
    from scripts.pettripfinder import market_authority as MA
    from scripts.pettripfinder.affiliate_destinations import empty_document
    from scripts.pettripfinder.build_market_manifest import _PARTITION_FILES

    repo = Path(repo_root) if repo_root else REPO_ROOT
    stage = Path(stage_root)
    if stage.exists():
        shutil.rmtree(stage)
    market_id = str(package["market_id"])
    lp = stage / "launch_packages" / "pettripfinder"
    written: "OrderedDict[str, str]" = OrderedDict()

    # The registry is shared state: every registered market travels, so
    # ownership validation and the cross-market invariants see the whole
    # registry, with the package's market added or replaced.
    committed_markets = repo / "launch_packages" / "pettripfinder" / "markets"
    for path in sorted(committed_markets.glob("*.json")):
        if path.stem == market_id:
            continue
        target = lp / "markets" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        written[target.relative_to(stage).as_posix()] = SMP.sha256_bytes(target.read_bytes())

    for relpath, document in WRITER.proposed_authority(package).items():
        target = stage / relpath
        if relpath.endswith("_final_partition_package.json"):
            # The manifest builder counts unresolved from the partition it
            # NAMES; stage under that name when the market has one.
            name = _PARTITION_FILES.get(market_id)
            if name:
                target = lp / name
        if isinstance(document, str):
            _write_text(target, document)
        else:
            _write_json(target, document)
        written[target.relative_to(stage).as_posix()] = SMP.sha256_bytes(target.read_bytes())

    # Affiliate shard: additive authority, a missing shard is an empty shard.
    committed_affiliate = (repo / "launch_packages" / "pettripfinder" / "markets" / "authority"
                           / market_id / "affiliate_destinations.json")
    affiliate_target = lp / "markets" / "authority" / market_id / "affiliate_destinations.json"
    if committed_affiliate.is_file():
        shutil.copyfile(committed_affiliate, affiliate_target)
    else:
        _write_json(affiliate_target, empty_document(market_id))
    written[affiliate_target.relative_to(stage).as_posix()] = SMP.sha256_bytes(affiliate_target.read_bytes())

    # Same-campus resolutions are shared identity state the guard reads;
    # blueprint / categories / locations / pilot config and content are the
    # generator's base package (shared, copied verbatim so the pilot loader
    # reads them from the stage).
    for name in ("identity_resolutions.json", "blueprint.json", "categories.json", "locations.json",
                 "pilot_config.json", "pilot_content.json"):
        source = repo / "launch_packages" / "pettripfinder" / name
        if source.is_file():
            target = lp / name
            shutil.copyfile(source, target)
            written[target.relative_to(stage).as_posix()] = SMP.sha256_bytes(target.read_bytes())

    # The three generated globals and the authority manifest, from the staged
    # shard(s) -- exactly what ``build_global_authority --write`` would emit.
    authority_dir = lp / "markets" / "authority"
    # Under the overlay: the registry the shard walk checks against is the
    # STAGED registry (which carries the package's market), never the
    # committed one -- a shadow or fixture market is registered in staging only.
    with overlay(stage):
        rendered = (
            (lp / "identity_routing.json", MA.render_json(MA.assemble_routing_document(authority_dir))),
            (lp / "hotel_exclusions.json", MA.render_json(MA.assemble_exclusions_document(authority_dir))),
            (lp / "seed_businesses.csv", MA.render_seed_csv(MA.assemble_seed_rows(authority_dir))),
            (lp / "ptf_global_authority_manifest.json", MA.render_json(MA.build_manifest(authority_dir))),
        )
    for target, text in rendered:
        _write_text(target, text)
        written[target.relative_to(stage).as_posix()] = SMP.sha256_bytes(target.read_bytes())
    return written


# --------------------------------------------------------------------------- #
# The overlay.
# --------------------------------------------------------------------------- #

def _patch_targets(stage: Path) -> List[Tuple[str, str, Any]]:
    """(module, attribute, staged value) for every path constant on the build path."""
    lp = stage / "launch_packages" / "pettripfinder"
    return [
        ("scripts.pettripfinder.markets.contract", "MARKETS_DIR", lp / "markets"),
        ("scripts.pettripfinder.market_authority", "LAUNCH_PACKAGE", lp),
        ("scripts.pettripfinder.market_authority", "AUTHORITY_DIR", lp / "markets" / "authority"),
        ("scripts.pettripfinder.market_authority", "GLOBAL_ROUTING_PATH", lp / "identity_routing.json"),
        ("scripts.pettripfinder.market_authority", "GLOBAL_EXCLUSIONS_PATH", lp / "hotel_exclusions.json"),
        ("scripts.pettripfinder.market_authority", "GLOBAL_SEED_PATH", lp / "seed_businesses.csv"),
        ("scripts.pettripfinder.market_authority", "MANIFEST_PATH", lp / "ptf_global_authority_manifest.json"),
        ("scripts.pettripfinder.site_data", "PRODUCTION_CSV", lp / "seed_businesses.csv"),
        ("scripts.pettripfinder.site_data", "PUBLISHED_FACTS_PATH", lp / "hotel_policy_facts.json"),
        ("scripts.pettripfinder.hotel_exclusions", "EXCLUSIONS_PATH", lp / "hotel_exclusions.json"),
        ("scripts.pettripfinder.identity_routing", "ROUTING_PATH", lp / "identity_routing.json"),
        ("scripts.pettripfinder.publication_guard", "RESOLUTIONS_PATH", lp / "identity_resolutions.json"),
        ("scripts.pettripfinder.release_contracts", "REPO_ROOT", stage),
        ("scripts.pettripfinder.release_contracts", "RELEASE_CONTRACTS_DIR",
         stage / "deploy" / "netlify" / "release_contracts"),
        ("scripts.pettripfinder.build_market_manifest", "_REPO_ROOT", stage),
        ("scripts.pettripfinder.assemble_netlify_bundle", "REPO_ROOT", stage),
        ("scripts.pettripfinder.assemble_production_site", "PACKAGE_DIR", lp),
        ("scripts.pettripfinder.assemble_production_site", "CENSUS_DIR", lp / "identity_census"),
        # PTF-FINAL-ASSEMBLER-REGISTERED-MARKET-DISCOVERY-001: the partition
        # resolver's standalone default; the assembler passes its own
        # (patched) PACKAGE_DIR explicitly, this keeps direct callers honest.
        ("scripts.pettripfinder.market_partition_resolution", "PACKAGE_DIR", lp),
        ("scripts.pettripfinder.market_reports", "MARKETS_DIR", lp / "markets"),
        # ATLAS-THROUGHPUT-004: the generator's base package (seed CSV,
        # blueprint, categories, locations, pilot config/content) is read
        # through the pilot loader's own constant, imported by name into the
        # production generator -- both must point at the stage, or an
        # unregistered market's rows come from the committed CSV.
        ("scripts.generate_pettripfinder_pilot", "LAUNCH_PACKAGE_DIR", lp),
        ("scripts.generate_pettripfinder_columbus_site", "LAUNCH_PACKAGE_DIR", lp),
    ]


#: The generator's process-wide BUILD STATE: what ``_prepare_build`` sets for
#: the market it builds (categories, labels, the /go/ route prefix, the
#: measurement config). A staged build of one market must not leave another
#: market's state behind for whatever runs next in the same process -- the
#: 003 migration audit found exactly that: a Dayton build left
#: ``_GO_MARKET_PREFIX = "dayton-oh"`` and three Columbus /go/ route tests
#: later in the session read a prefixed route.
BUILD_STATE_ATTRIBUTES: Tuple[Tuple[str, str], ...] = (
    ("scripts.pettripfinder.site_pages", "PUBLISHED_CATEGORIES"),
    ("scripts.pettripfinder.site_pages", "COMPARISON_ROUTE"),
    ("scripts.pettripfinder.approved_hotel_profile", "MARKET_LABEL"),
    ("scripts.pettripfinder.approved_hotel_profile", "MARKET_STATE"),
    ("scripts.pettripfinder.approved_hotel_profile", "MARKET_METRO_DEFAULT"),
    ("scripts.pettripfinder.approved_hotel_profile", "PUBLISHED_CATEGORIES"),
    ("scripts.pettripfinder.commercial_actions", "_GO_MARKET_PREFIX"),
    ("scripts.pettripfinder.measurement", "_CONFIG"),
)


@contextmanager
def preserved_build_state() -> Iterator[None]:
    """Snapshot the generator's build state and put it back afterwards."""
    import importlib
    saved: List[Tuple[Any, str, Any]] = []
    for module_name, attribute in BUILD_STATE_ATTRIBUTES:
        module = importlib.import_module(module_name)
        if hasattr(module, attribute):
            saved.append((module, attribute, getattr(module, attribute)))
    try:
        yield
    finally:
        for module, attribute, value in reversed(saved):
            setattr(module, attribute, value)


#: The overlay rewrites process-wide module constants, so only one staging
#: tree may be overlaid at a time; concurrent requests (the bundle cache's
#: per-key workers) serialise here. Re-entrant: build_changed_market overlays
#: around a stage_package that overlays for its own globals.
_OVERLAY_LOCK = threading.RLock()


@contextmanager
def overlay(stage_root: Path) -> Iterator[Path]:
    """Point the build path at ``stage_root``; restore everything on exit,
    including the generator's build state."""
    import importlib
    stage = Path(stage_root)
    saved: List[Tuple[Any, str, Any]] = []
    env_key = "PTF_IDENTITY_CENSUS_DIR"
    _OVERLAY_LOCK.acquire()
    env_saved = os.environ.get(env_key)
    state = preserved_build_state()
    state.__enter__()
    try:
        for module_name, attribute, value in _patch_targets(stage):
            module = importlib.import_module(module_name)
            if not hasattr(module, attribute):
                raise StagingError("%s has no %s to overlay" % (module_name, attribute))
            saved.append((module, attribute, getattr(module, attribute)))
            setattr(module, attribute, value)
        os.environ[env_key] = str(stage / "launch_packages" / "pettripfinder" / "identity_census")
        yield stage
    finally:
        for module, attribute, value in reversed(saved):
            setattr(module, attribute, value)
        if env_saved is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = env_saved
        state.__exit__(None, None, None)
        _OVERLAY_LOCK.release()


# --------------------------------------------------------------------------- #
# The staged release contract: derived under the overlay from the staged
# authority, with the shared policy sections copied from the committed
# contracts (which must all agree).
# --------------------------------------------------------------------------- #

def shared_contract_sections(repo_root: Optional[Path] = None) -> "OrderedDict[str, Any]":
    repo = Path(repo_root) if repo_root else REPO_ROOT
    directory = repo / "deploy" / "netlify" / "release_contracts"
    docs = [json.loads(p.read_text(encoding="utf-8-sig"))
            for p in sorted(directory.glob("*.json")) if p.name != "release_contracts_superseded.json"]
    if not docs:
        raise StagingError("no committed release contracts to take the shared sections from")
    out: "OrderedDict[str, Any]" = OrderedDict()
    for section in SHARED_CONTRACT_SECTIONS:
        values = {json.dumps(d.get(section), sort_keys=True) for d in docs}
        if len(values) != 1:
            raise StagingError("committed contracts disagree on %r; a staged contract cannot "
                               "choose between them" % section)
        out[section] = docs[0][section]
    return out


def derive_staged_contract(package: Mapping, stage_root: Path, *,
                           repo_root: Optional[Path] = None) -> "OrderedDict[str, Any]":
    """The release contract the staged authority derives. Must be called
    INSIDE :func:`overlay`."""
    from scripts.pettripfinder.release_contracts import CONTRACT_SCHEMA, derive_authority

    market_id = str(package["market_id"])
    derived = derive_authority(market_id)
    recon = derived.reconciliation()
    shared = shared_contract_sections(repo_root)
    contract: "OrderedDict[str, Any]" = OrderedDict((
        ("schema", CONTRACT_SCHEMA),
        ("contract_id", "pettripfinder-%s-release/1.0" % market_id),
        ("market_id", market_id),
        ("product", "pettripfinder-%s" % market_id),
        ("release_name_prefix", "package-%s" % market_id),
        ("description", "Release-gate contract DERIVED from sealed package %s by "
                        "ATLAS-THROUGHPUT-003 package staging. Every number below is "
                        "derived from the staged authority; nothing is copied from a "
                        "sibling market." % package["package_id"]),
        ("deployment_authorization", OrderedDict((
            ("grants_deployment", False),
            ("asserts_market_complete", False),
            ("means", "A passing contract means the staged package assembles under every "
                      "per-market release gate. It is not a deployment authorization."),
        ))),
        ("canonical", shared["canonical"]),
        ("identity_census", OrderedDict((
            ("path", "launch_packages/pettripfinder/identity_census/%s.json" % market_id),
            ("schema", str(package["census"].get("schema") or "")),
            ("expected_count", derived.confirmed_identities),
        ))),
        ("reconciliation", OrderedDict((
            ("confirmed_identities", recon["confirmed_identities"]),
            ("published_pet_friendly", recon["published_pet_friendly"]),
            ("verified_no_pets", recon["verified_no_pets"]),
            ("resolved", recon["resolved"]),
            ("unresolved", recon["unresolved"]),
            ("out_of_current_category", recon["resolved"] - recon["published_pet_friendly"]
                                        - recon["verified_no_pets"]),
        ))),
        ("policy_package", OrderedDict((
            ("path", derived.policy_package_path),
            ("expected_sha256", derived.policy_package_sha256),
            ("expected_schema_version", derived.policy_package_schema_version),
            ("expected_record_count", derived.policy_package_record_count),
            ("identity_authority", True),
        ))),
        ("public_surface", OrderedDict((
            ("seed_hotel_rows", derived.seed_hotel_rows),
            ("public_hotel_profile_count", derived.published_hotel_profiles),
            ("excluded_public_profile_count", derived.excluded_public_profiles),
        ))),
        ("routes", OrderedDict((
            ("market_slug", derived.market_slug),
            ("route_mode", derived.route_mode),
            ("hotel_route_count", derived.hotel_route_count),
            ("published_corridor_route_count", derived.corridor_route_count),
        ))),
        ("minimum_release_gates", shared["minimum_release_gates"]),
        ("forbidden_output_tokens", shared["forbidden_output_tokens"]),
        ("publish", shared["publish"]),
        ("provenance", OrderedDict((
            ("sealed_package_id", package["package_id"]),
            ("sealed_package_digest", package["package_digest"]),
            ("created_from_source_sha", package["created_from_source_sha"]),
        ))),
    ))
    target = Path(stage_root) / "deploy" / "netlify" / "release_contracts" / ("%s.json" % market_id)
    _write_json(target, contract)
    return contract


# --------------------------------------------------------------------------- #
# Build the changed market.
# --------------------------------------------------------------------------- #

def build_changed_market(package: Mapping, stage_root: Path, output_root: Path, *,
                         context: str = "production", cold: bool = True,
                         repo_root: Optional[Path] = None) -> "OrderedDict[str, Any]":
    """Stage the package, derive its contract, assemble its bundle.

    ``cold=True`` forces a real build (the session cache is bypassed), which
    is what the determinism gate requires; a warm build is allowed only for
    the changed-market build itself when the caller has already proven the
    package cold.
    """
    from scripts.pettripfinder import assembly_session_cache as ASC
    from scripts.pettripfinder.assemble_netlify_bundle import assemble
    from scripts.pettripfinder.assemble_production_site import bundle_digest, file_hashes
    from scripts.pettripfinder.markets.contract import parse_market

    stage = Path(stage_root)
    output = Path(output_root)
    started = time.perf_counter()
    staged = stage_package(package, stage, repo_root=repo_root)
    events_before = len(ASC.EVENTS)
    with overlay(stage):
        contract = derive_staged_contract(package, stage, repo_root=repo_root)
        market = parse_market(dict(package["market"]), source="package:%s" % package["package_id"])
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True)
        if cold:
            with ASC.cold():
                manifest = assemble(context, str(output), contract=contract, market=market)
        else:
            manifest = assemble(context, str(output), contract=contract, market=market)
    site_dir = output / "site"
    hashes = file_hashes(site_dir)
    events = [dict(e) for e in ASC.EVENTS[events_before:]]
    return OrderedDict((
        ("market_id", package["market_id"]),
        ("package_id", package["package_id"]),
        ("context", context),
        ("cold", cold),
        ("staged_files", staged),
        ("staged_input_digest", SMP.sha256_text(SMP.canonical_json(staged))),
        ("contract_sha256", SMP.sha256_text(SMP.canonical_json(contract))),
        ("bundle_sha256", bundle_digest(hashes)),
        ("file_count", len(hashes)),
        ("html_count", sum(1 for k in hashes if k.endswith(".html"))),
        ("release_name", manifest.get("release_name") if isinstance(manifest, Mapping) else None),
        ("gates_failing", [g for g, r in (manifest.get("gates") or {}).items()
                           if isinstance(r, Mapping) and not r.get("pass")]
         if isinstance(manifest, Mapping) else []),
        ("cache_events", [OrderedDict((("verdict", e.get("verdict")),
                                       ("assembly_kind", e.get("assembly_kind")),
                                       ("input_key", e.get("input_key")),
                                       ("seconds", e.get("seconds"))))
                          for e in events]),
        ("seconds", round(time.perf_counter() - started, 3)),
    ))


__all__ = ["StagingError", "SHARED_CONTRACT_SECTIONS", "BUILD_STATE_ATTRIBUTES", "preserved_build_state",
           "stage_package", "overlay",
           "shared_contract_sections", "derive_staged_contract", "build_changed_market"]

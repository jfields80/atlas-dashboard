"""PTF-PER-MARKET-RELEASE-CONTRACTS-001 -- one release contract per market.

Until this module existed, the Netlify assembler read a single committed
``deploy/netlify/release_contract.json``. That document was Columbus's: it named
Columbus's policy package, Columbus's 88 published profiles, and Columbus's one
held row. Assembling any other market still loaded it, so Cleveland's nineteen
verified hotels were checked against Columbus's eighty-eight and the build
failed closed on a number that was never about Cleveland. The failure was
correct behaviour on a wrong premise -- exactly the shape of defect that a
shared, market-calibrated constant produces.

The replacement has two halves, kept apart on purpose:

  CONTRACT    ``deploy/netlify/release_contracts/<market_id>.json`` -- a
              complete, self-contained, human-reviewed document per market.
              There is no inheritance and no base file: a reader can answer
              "what does this market promise?" from one file, and an edit to
              one market cannot silently move another market's expectations.

  DERIVATION  ``derive_authority()`` below -- the same numbers computed from
              that market's OWN committed authority (identity census, policy
              package, exclusion registry, seed inventory, corridor/route
              config, and any reconciliation manifest the market commits).

A contract is valid only when the reviewed document and the derived authority
agree on every field. Neither half alone is sufficient. Derivation alone would
be a gate that recomputes its own expectation and therefore proves nothing; a
reviewed document alone would drift from the authority the moment an inventory
changed. Requiring both means a number can only move when someone changes the
authority AND states the new number, and any disagreement fails closed.

What a passing contract does and does not mean
----------------------------------------------
A passing release contract is a STRUCTURAL statement: the assembled package for
this market is internally consistent and safe to publish as a static bundle. It
is not a deployment authorization, and it is not a claim that the market is
complete. Cleveland passes with 161 identities still unresolved; Dayton passes
with 90. Every contract records this in its ``deployment_authorization`` block,
and the assembler copies it into the deployment manifest so the artifact carries
the caveat with it.

Reuse of the derivation
-----------------------
The reconciliation numbers come from
``scripts.pettripfinder.build_market_manifest.build_package`` -- the module that
already derives a market's package manifest -- rather than from a second
implementation here. Two derivations of the same fact eventually disagree, and
the one nobody is looking at is the one that goes wrong.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_CONTRACTS_DIR = REPO_ROOT / "deploy" / "netlify" / "release_contracts"

#: Versioned schema of the per-market contract documents.
CONTRACT_SCHEMA = "ptf-market-release-contract/1.0"

#: The five reconciliation fields every contract states about its market.
#: ``confirmed_identities`` and ``unresolved`` may be ``None`` for a market that
#: commits no identity census (Columbus): absent is a fact, zero is a claim.
RECONCILIATION_FIELDS = ("confirmed_identities", "published_pet_friendly",
                         "verified_no_pets", "resolved", "unresolved")


class ReleaseContractError(ValueError):
    """A contract is missing, malformed, or not the contract it claims to be."""


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def contract_path(market_id: str) -> Path:
    """The committed contract path for ``market_id``.

    Purely positional -- there is no fallback to another market's document.
    A fallback is what made one market's numbers gate another market's build.
    """
    mid = (market_id or "").strip()
    if not mid:
        raise ReleaseContractError("market_id is required to locate a release contract")
    return RELEASE_CONTRACTS_DIR / ("%s.json" % mid)


def available_market_ids() -> Tuple[str, ...]:
    """Every market with a committed release contract, sorted."""
    if not RELEASE_CONTRACTS_DIR.is_dir():
        return ()
    return tuple(sorted(p.stem for p in RELEASE_CONTRACTS_DIR.glob("*.json")))


def load_contract(market_id: str) -> Dict:
    """Load and self-check one market's contract (fail closed).

    Three checks before the document is handed back, because each of them is a
    way a build could otherwise validate the wrong market:

      * the file must exist -- a market with no reviewed contract has no
        release expectations, and inventing them at assembly time is precisely
        what this module removes;
      * the schema must be the one this code understands;
      * the ``market_id`` INSIDE the document must equal the one requested, so
        a copied-and-not-edited contract cannot pass as another market's.
    """
    path = contract_path(market_id)
    if not path.is_file():
        raise ReleaseContractError(
            "no release contract for market %r (expected %s); markets with a "
            "committed contract: %s"
            % (market_id, path.relative_to(REPO_ROOT).as_posix(),
               list(available_market_ids())))
    contract = json.loads(path.read_text(encoding="utf-8-sig"))
    schema = str(contract.get("schema") or "")
    if schema != CONTRACT_SCHEMA:
        raise ReleaseContractError(
            "release contract %s declares schema %r, expected %r"
            % (path.name, schema, CONTRACT_SCHEMA))
    declared = str(contract.get("market_id") or "")
    if declared != market_id:
        raise ReleaseContractError(
            "release contract %s declares market_id %r but was loaded for %r "
            "(a contract may never stand in for another market)"
            % (path.name, declared, market_id))
    return contract


# --------------------------------------------------------------------------- #
# Derivation from committed authority
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class DerivedAuthority:
    """What a market's own committed authority says, independent of any contract.

    Every field here is computed from files under ``launch_packages/`` plus the
    market registry. Nothing is read from the contract, which is what makes the
    comparison in :func:`contract_disagreements` meaningful.
    """

    market_id: str
    market_slug: str
    route_mode: str
    policy_package_path: str
    policy_package_sha256: str
    policy_package_schema_version: str
    policy_package_record_count: int
    seed_hotel_rows: int
    published_hotel_profiles: int
    excluded_public_profiles: int
    confirmed_identities: Optional[int]
    verified_no_pets: int
    resolved: int
    unresolved: Optional[int]
    hotel_route_count: int
    corridor_route_count: int

    def reconciliation(self) -> "OrderedDict[str, Optional[int]]":
        return OrderedDict([
            ("confirmed_identities", self.confirmed_identities),
            ("published_pet_friendly", self.published_hotel_profiles),
            ("verified_no_pets", self.verified_no_pets),
            ("resolved", self.resolved),
            ("unresolved", self.unresolved),
        ])


def derive_authority(market_id: str) -> DerivedAuthority:
    """Compute ``market_id``'s release facts from its own committed authority."""
    # Imported here rather than at module import time: the assembler imports
    # this module, and build_market_manifest imports the assembler's siblings.
    from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
    from scripts.pettripfinder.build_market_manifest import build_package
    from scripts.pettripfinder.market_ownership import owned_by
    from scripts.pettripfinder.markets import load_markets, market_by_id
    from scripts.pettripfinder.site_data import published_facts_path, read_production_rows

    market = market_by_id(load_markets(), market_id)
    package = build_package(market_id)

    pkg_path = published_facts_path(market_id)
    if not pkg_path.is_file():
        # Named rather than allowed to surface as a bare FileNotFoundError:
        # a market with no committed policy package has no verified inventory,
        # so it has nothing a release contract could be about.
        raise ReleaseContractError(
            "market %r commits no policy package at %s -- there is no verified "
            "inventory for a release contract to describe"
            % (market_id, pkg_path.relative_to(REPO_ROOT).as_posix()))
    pkg_bytes = pkg_path.read_bytes()
    pkg = json.loads(pkg_bytes.decode("utf-8-sig"))

    seed_rows = owned_by(read_production_rows(), market_id,
                         context="release contract derivation")
    seed_hotels = [r for r in seed_rows if r.get("category") == "pet-friendly-hotels"]

    published = package.published_pet_friendly_count
    return DerivedAuthority(
        market_id=market_id,
        market_slug=market.market_slug,
        route_mode=market.route_mode,
        policy_package_path=pkg_path.relative_to(REPO_ROOT).as_posix(),
        policy_package_sha256=content_sha256(pkg_bytes),
        policy_package_schema_version=str(pkg.get("schema_version")),
        policy_package_record_count=len(pkg.get("hotels", [])),
        seed_hotel_rows=len(seed_hotels),
        published_hotel_profiles=published,
        # Held rows are DERIVED, never declared: a seed hotel this market owns
        # that the committed package does not verify has no public route.
        excluded_public_profiles=len(seed_hotels) - published,
        confirmed_identities=package.confirmed_identity_count,
        verified_no_pets=package.verified_no_pets_count,
        resolved=published + package.verified_no_pets_count,
        unresolved=package.unresolved_count,
        hotel_route_count=len(package.hotel_routes),
        corridor_route_count=len(package.corridor_routes),
    )


# --------------------------------------------------------------------------- #
# Cross-checks against additional committed reconciliation artifacts
# --------------------------------------------------------------------------- #

def _cross_check(contract: Dict, check: Dict) -> List[str]:
    """One declarative reconciliation cross-check.

    A market may commit a separate reconciliation artifact -- Cleveland's
    unresolved manifest, Dayton's recovery-run partition. Their shapes differ
    because they were written by different sprints for different questions, so
    the contract declares HOW to read each one instead of this module knowing
    any market by name:

      ``key_map``     contract reconciliation field -> key in that document
      ``length_sum``  contract reconciliation field -> list keys whose combined
                      length must equal it (a partition of the same total)

    The point is not redundancy for its own sake. These artifacts were written
    by the work that produced the numbers; if the contract and the derivation
    both drifted the same way, the artifact would still disagree.
    """
    problems: List[str] = []
    rel = check["path"]
    path = REPO_ROOT / rel
    if not path.is_file():
        return ["reconciliation cross-check file missing: %s" % rel]
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    stated = contract.get("reconciliation") or {}

    for field, key in sorted((check.get("key_map") or {}).items()):
        if key not in doc:
            problems.append("%s: key %r absent (needed for %s)" % (rel, key, field))
            continue
        if doc[key] != stated.get(field):
            problems.append("%s: %s=%r but contract states %r"
                            % (rel, key, doc[key], stated.get(field)))

    for field, keys in sorted((check.get("length_sum") or {}).items()):
        total = 0
        missing = [k for k in keys if not isinstance(doc.get(k), list)]
        if missing:
            problems.append("%s: expected list(s) %s for %s" % (rel, missing, field))
            continue
        for key in keys:
            total += len(doc[key])
        if total != stated.get(field):
            problems.append("%s: %s lengths sum to %d but contract states %r"
                            % (rel, list(keys), total, stated.get(field)))
    return problems


# --------------------------------------------------------------------------- #
# Agreement
# --------------------------------------------------------------------------- #

def contract_disagreements(contract: Dict, derived: DerivedAuthority) -> List[str]:
    """Every way ``contract`` disagrees with ``derived``, as readable strings.

    Returns a list rather than raising so the caller can report all of them at
    once: fixing a contract one failed assertion at a time hides how far it has
    drifted.
    """
    problems: List[str] = []

    def _cmp(label: str, stated, actual) -> None:
        if stated != actual:
            problems.append("%s: contract states %r, authority derives %r"
                            % (label, stated, actual))

    if contract.get("market_id") != derived.market_id:
        problems.append("market_id: contract states %r, derivation is for %r"
                        % (contract.get("market_id"), derived.market_id))
        return problems

    pkg = contract.get("policy_package") or {}
    _cmp("policy_package.path", pkg.get("path"), derived.policy_package_path)
    _cmp("policy_package.expected_sha256", pkg.get("expected_sha256"),
         derived.policy_package_sha256)
    _cmp("policy_package.expected_schema_version",
         str(pkg.get("expected_schema_version")), derived.policy_package_schema_version)
    _cmp("policy_package.expected_record_count", pkg.get("expected_record_count"),
         derived.policy_package_record_count)

    surface = contract.get("public_surface") or {}
    _cmp("public_surface.public_hotel_profile_count",
         surface.get("public_hotel_profile_count"), derived.published_hotel_profiles)
    _cmp("public_surface.excluded_public_profile_count",
         surface.get("excluded_public_profile_count"), derived.excluded_public_profiles)
    _cmp("public_surface.seed_hotel_rows", surface.get("seed_hotel_rows"),
         derived.seed_hotel_rows)

    routes = contract.get("routes") or {}
    _cmp("routes.market_slug", routes.get("market_slug"), derived.market_slug)
    _cmp("routes.route_mode", routes.get("route_mode"), derived.route_mode)
    _cmp("routes.hotel_route_count", routes.get("hotel_route_count"),
         derived.hotel_route_count)
    _cmp("routes.published_corridor_route_count",
         routes.get("published_corridor_route_count"), derived.corridor_route_count)

    stated_recon = contract.get("reconciliation") or {}
    derived_recon = derived.reconciliation()
    for field in RECONCILIATION_FIELDS:
        _cmp("reconciliation.%s" % field, stated_recon.get(field), derived_recon[field])

    # A market whose contract claims a census must have one; a market that
    # declares none must derive none. Both directions matter: silently gaining
    # a census would leave the contract understating the market, and silently
    # losing one would turn a real universe into "unknown" without review.
    census = contract.get("identity_census")
    if census is None:
        if derived.confirmed_identities is not None:
            problems.append(
                "identity_census: contract declares none, but the market now "
                "commits a census deriving %d confirmed identities"
                % derived.confirmed_identities)
    else:
        census_path = REPO_ROOT / census["path"]
        if not census_path.is_file():
            problems.append("identity_census.path missing: %s" % census["path"])
        _cmp("identity_census.expected_count", census.get("expected_count"),
             derived.confirmed_identities)

    for check in contract.get("reconciliation_cross_checks") or []:
        problems.extend(_cross_check(contract, check))

    # Internal arithmetic. Checked separately from the derivation comparison so a
    # contract that is self-inconsistent is reported as such rather than as a
    # mismatch against the authority.
    published = stated_recon.get("published_pet_friendly")
    no_pets = stated_recon.get("verified_no_pets")
    resolved = stated_recon.get("resolved")
    confirmed = stated_recon.get("confirmed_identities")
    unresolved = stated_recon.get("unresolved")

    if not all(isinstance(v, int) for v in (published, no_pets, resolved)):
        problems.append(
            "reconciliation: published_pet_friendly, verified_no_pets and "
            "resolved must all be stated as integers (got %r / %r / %r)"
            % (published, no_pets, resolved))
    elif resolved != published + no_pets:
        problems.append(
            "reconciliation.resolved (%d) != published_pet_friendly + "
            "verified_no_pets (%d + %d)" % (resolved, published, no_pets))

    # confirmed and unresolved are the pair a market without a census cannot
    # state. They travel together: one alone would be an arithmetic claim with
    # nothing on the other side of it.
    if (confirmed is None) != (unresolved is None):
        problems.append(
            "reconciliation: confirmed_identities and unresolved must be stated "
            "or absent together (got %r / %r)" % (confirmed, unresolved))
    elif confirmed is not None and isinstance(resolved, int):
        if confirmed - resolved != unresolved:
            problems.append(
                "reconciliation: confirmed_identities - resolved != unresolved "
                "(%r - %r != %r)" % (confirmed, resolved, unresolved))

    return problems


def verify_contract(market_id: str) -> List[str]:
    """Load ``market_id``'s contract and compare it to its own authority."""
    return contract_disagreements(load_contract(market_id), derive_authority(market_id))


def verify_all() -> "OrderedDict[str, List[str]]":
    """market_id -> disagreements, for every committed contract."""
    return OrderedDict((mid, verify_contract(mid)) for mid in available_market_ids())


# --------------------------------------------------------------------------- #
# CLI (read-only report)
# --------------------------------------------------------------------------- #

def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", default=None,
                    help="verify one market (default: every committed contract)")
    args = ap.parse_args(argv)

    markets = (args.market,) if args.market else available_market_ids()
    failed = 0
    for mid in markets:
        contract = load_contract(mid)
        derived = derive_authority(mid)
        problems = contract_disagreements(contract, derived)
        recon = derived.reconciliation()
        fmt = lambda v: "n/a" if v is None else str(v)
        print("=== %s (%s) ===" % (mid, contract["contract_id"]))
        print("  policy package     : %s (%d records, schema %s)"
              % (derived.policy_package_path, derived.policy_package_record_count,
                 derived.policy_package_schema_version))
        print("  public surface     : %d published / %d held of %d seed rows"
              % (derived.published_hotel_profiles, derived.excluded_public_profiles,
                 derived.seed_hotel_rows))
        print("  reconciliation     : %s confirmed / %d published / %d no-pets / "
              "%d resolved / %s unresolved"
              % (fmt(recon["confirmed_identities"]), recon["published_pet_friendly"],
                 recon["verified_no_pets"], recon["resolved"], fmt(recon["unresolved"])))
        print("  routes             : %d hotel / %d published corridor (%s)"
              % (derived.hotel_route_count, derived.corridor_route_count,
                 derived.route_mode))
        if problems:
            failed += 1
            print("  AGREEMENT          : FAILED (%d)" % len(problems))
            for p in problems:
                print("      - %s" % p)
        else:
            print("  AGREEMENT          : ok")
        print("  means              : %s"
              % contract["deployment_authorization"]["means"])
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

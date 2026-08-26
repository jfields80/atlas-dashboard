"""PTF-LOUISVILLE-INTEGRATION-HARDENING-001 mechanical integration writer.

Projects Louisville's pre-existing NOT_LODGING census disposition into its
market-local exclusion shard, regenerates compatibility globals through the
canonical assembler, then writes a release contract whose numeric fields come
only from ``derive_authority``.  It neither captures evidence nor changes a
founder decision, policy fact, routing record, or seed row.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder.market_authority import (
    build_exclusions_shard,
    exclusions_shard_path,
    render_json,
    write_generated_artifacts,
)
from scripts.pettripfinder.release_contracts import derive_authority

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
MARKET = "louisville-ky"
WORK = "PTF-LOUISVILLE-INTEGRATION-HARDENING-001"
OPERATOR = "jfields80"
REVIEWED_AT = "2026-08-17"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dump(path: Path, document) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _project_category_exit() -> None:
    census_path = PKG / "identity_census" / (MARKET + ".json")
    census = _load(census_path)
    exits = [row for row in census["hotels"]
             if row.get("lodging_state") == "NOT_LODGING"]
    if len(exits) != 1:
        raise SystemExit("expected exactly one Louisville NOT_LODGING census row")

    shard_path = exclusions_shard_path(MARKET)
    shard = _load(shard_path)
    records = list(shard["exclusions"])
    row = exits[0]
    if any(r.get("normalized_name") == row["normalized_name"] for r in records):
        return

    record = OrderedDict([
        ("exclusion_id", "louisville-ooc-" + row["slug"]),
        ("canonical_name", row["canonical_name"]),
        ("normalized_name", row["normalized_name"]),
        ("address", row["address"]),
        ("city", row["city"]),
        ("state", row["state"]),
        ("postal_code", row["postal_code"]),
        ("official_url", row.get("official_url") or row["provenance"]),
        ("exclusion_state", HE.OUT_OF_CURRENT_CATEGORY),
        ("evidence_quote", "Census category disposition: NOT_LODGING; not in the current pet-friendly-hotels category."),
        ("source_url", "launch_packages/pettripfinder/identity_census/louisville-ky.json"),
        ("observed_at", row["observed_at"]),
        ("source_hash", "sha256:" + hashlib.sha256(census_path.read_bytes()).hexdigest()),
        ("reviewer_id", OPERATOR),
        ("reviewed_at", REVIEWED_AT),
        ("notes", WORK + ": mechanical registry projection of the existing census NOT_LODGING disposition. No pet-policy fact or new founder decision is asserted; re-entry requires an explicit reviewed supersession."),
        ("market_id", MARKET),
    ])
    record["record_hash"] = HE.record_hash(record)
    record["approval_hash"] = HE.approval_hash(record)
    records.append(record)
    document = build_exclusions_shard(MARKET, records)
    HE.validate(document)
    _dump(shard_path, document)


def _write_release_contract() -> None:
    """Use the existing reviewed contract shape with Louisville-derived values."""
    template = _load(REPO / "deploy" / "netlify" / "release_contracts" / "indianapolis-in.json")
    contract = copy.deepcopy(template)
    authority = derive_authority(MARKET)
    reconciliation = authority.reconciliation()
    out_of_category = (authority.resolved - authority.published_hotel_profiles
                       - authority.verified_no_pets)
    if out_of_category != 1:
        raise SystemExit("Louisville category-exit registry did not derive exactly one terminal exit")

    contract.update({
        "contract_id": "pettripfinder-louisville-ky-release/1.0",
        "market_id": MARKET,
        "product": "pettripfinder-louisville-ky",
        "release_name_prefix": "prod-006-louisville",
        "description": ("Deterministic release-gate contract for the PetTripFinder "
                        "Louisville market (" + WORK + "). It describes only "
                        "current reviewed authority and grants no deployment authorization."),
    })
    contract["deployment_authorization"]["grants_deployment"] = False
    contract["deployment_authorization"]["asserts_market_complete"] = False
    contract["deployment_authorization"]["means"] = (
        "A passing contract means this market's assembled package is structurally "
        "consistent and safe to publish as a static bundle. It is not a deployment "
        "authorization and it makes no claim that the market is complete -- %d of "
        "its %d confirmed identities remain unresolved."
        % (authority.unresolved, authority.confirmed_identities))
    contract["identity_census"] = {
        "path": "launch_packages/pettripfinder/identity_census/louisville-ky.json",
        "schema": "ptf-market-identity-census/1.1",
        "expected_count": authority.confirmed_identities,
        "note": ("The committed Louisville census is the identity universe. The "
                 "fourteen publication records and four property-specific refusals "
                 "are founder-approved; one NOT_LODGING census disposition is "
                 "mechanically represented as an out-of-current-category registry row."),
    }
    contract["reconciliation"] = {
        "confirmed_identities": reconciliation["confirmed_identities"],
        "published_pet_friendly": reconciliation["published_pet_friendly"],
        "verified_no_pets": reconciliation["verified_no_pets"],
        "out_of_current_category": out_of_category,
        "resolved": reconciliation["resolved"],
        "unresolved": reconciliation["unresolved"],
        "note": ("Counts are derived from the current final partition and exclusion "
                 "registry; unresolved is not negative pet evidence."),
    }
    contract["reconciliation_cross_checks"] = [{
        "path": "launch_packages/pettripfinder/louisville_final_partition_001.json",
        "key_map": {"confirmed_identities": "count"},
        "note": "The final partition carries the same committed Louisville identity universe.",
    }]
    contract["policy_package"] = {
        "path": authority.policy_package_path,
        "expected_sha256": authority.policy_package_sha256,
        "expected_schema_version": authority.policy_package_schema_version,
        "expected_record_count": authority.policy_package_record_count,
        "identity_authority": True,
        "note": ("The Louisville policy package is the sole identity authority for "
                 "its fourteen verified profiles; every record retains the final "
                 "founder decision, record-hash, and evidence-hash binding."),
        "schema_note": "Schema 1.2; source-silent facts remain absent.",
    }
    contract["public_surface"] = {
        "seed_hotel_rows": authority.seed_hotel_rows,
        "public_hotel_profile_count": authority.published_hotel_profiles,
        "excluded_public_profile_count": authority.excluded_public_profiles,
        "held_hotel_exclusion": ("All unresolved Louisville census identities, the "
                                  "four verified-no-pets exclusions, and the one "
                                  "out-of-current-category disposition have no seed "
                                  "row or public profile."),
    }
    contract["routes"] = {
        "market_slug": authority.market_slug,
        "route_mode": authority.route_mode,
        "hotel_route_count": authority.hotel_route_count,
        "published_corridor_route_count": authority.corridor_route_count,
        "note": "Routes are derived from the fourteen current verified profiles.",
    }
    _dump(REPO / "deploy" / "netlify" / "release_contracts" / (MARKET + ".json"), contract)


def main() -> None:
    _project_category_exit()
    write_generated_artifacts()
    _write_release_contract()


if __name__ == "__main__":
    main()

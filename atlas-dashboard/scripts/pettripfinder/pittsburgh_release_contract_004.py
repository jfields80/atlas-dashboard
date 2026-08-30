# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 15 -- re-author the release contract.

    python -m scripts.pettripfinder.pittsburgh_release_contract_004 --write

Pittsburgh's contract was calibrated to the LIVE market -- 26 published, 4
refused, 33 resolved. The hardened market is a different market, so eleven
values disagree with the authority now committed.

EVERY NUMBER IS DERIVED, NEVER TYPED
--------------------------------------
Each figure is read from ``release_contracts.derive_authority``, the same
function ``contract_disagreements`` checks the contract against. Nothing is
copied from a work order's expectation. That is deliberate: this order's own
prompt expected 50 published and 13 refused, and the mechanical reconciliation
produced 46 and 10 because six founder-signed rows name identities the
registered census does not hold. Typing the expected numbers in would have
produced a contract that passed its own arithmetic and described a market that
does not exist.

THIS GRANTS NOTHING
--------------------
``deployment_authorization.grants_deployment`` stays false and
``asserts_market_complete`` stays false. A passing contract is a STRUCTURAL
statement: the authority files agree, the routes match the reviewed inventory,
no held identity leaks. It is not a deployment authorization, and this order
creates none, consumes none and deploys nothing. Pittsburgh stays hidden from
navigation and the sitemap.

THE OLD PRODUCTION PIN IS STALE, AND SAYING SO IS THE POINT
-------------------------------------------------------------
The authorization that put Pittsburgh's 26 profiles live was signed against the
contract this run replaces. It cannot authorise the hardened market, and this
module does not repair it: a deployment authorization is the founder's to
grant. The values a future one would need are printed and recorded.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA               # noqa: E402
from scripts.pettripfinder.release_contracts import (                  # noqa: E402
    contract_disagreements, derive_authority)
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (       # noqa: E402
    AS_OF, MARKET_ID, REPORTS, WORK_ORDER, _load, _write)

CONTRACT = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
            / ("%s.json" % MARKET_ID))
HANDOFF = REPORTS / "pittsburgh_hardened_sync_004_deployment_handoff.json"


class ContractError(RuntimeError):
    pass


def reauthor() -> Dict:
    contract = _load(CONTRACT)
    derived = derive_authority(MARKET_ID)
    recon = dict(derived.reconciliation())
    # OUT_OF_CURRENT_CATEGORY is contract-local: the derivation does not carry
    # it, and the contract's own arithmetic (resolved == published + no-pets +
    # category exits) needs it. Its authority is the exclusion REGISTRY, never
    # a census annotation (PTF-PER-MARKET-RELEASE-CONTRACTS-001).
    recon["out_of_current_category"] = sum(
        1 for row in MA.load_market_exclusions_document(MARKET_ID)["exclusions"]
        if row["exclusion_state"] == "OUT_OF_CURRENT_CATEGORY")

    contract["description"] = (
        "Deterministic release-gate contract for the PetTripFinder Pittsburgh "
        "market through %s. Calibrated to THIS market's committed authority; "
        "no number is inherited from or comparable to another market's "
        "contract." % WORK_ORDER)
    contract["deployment_authorization"] = OrderedDict((
        ("grants_deployment", False),
        ("asserts_market_complete", False),
        ("means",
         "A passing contract means this market's assembled package is "
         "STRUCTURALLY deployable: its authority files agree, its routes match "
         "its reviewed inventory, no held identity leaks, and every publish "
         "gate holds. It is not a deployment authorization and asserts nothing "
         "about the market being complete -- %d of this market's %d confirmed "
         "identities are still unresolved, the market is hidden from "
         "navigation and the sitemap, and no founder deployment decision "
         "exists for the hardened Pittsburgh."
         % (recon["unresolved"], recon["confirmed_identities"])),
    ))

    package = contract["policy_package"]
    package["expected_sha256"] = derived.policy_package_sha256
    package["expected_schema_version"] = derived.policy_package_schema_version
    package["expected_record_count"] = derived.policy_package_record_count
    package["note"] = (
        "The verified hotel identities are DERIVED from this package at "
        "assembly time via scripts.pettripfinder.site_data."
        "verified_public_hotels(); they are not restated here. Every record is "
        "Schema %s, founder-approved against its final record_hash and "
        "evidence_hash, and backed by PUBLICATION_GRADE_EVIDENCE whose raw "
        "bytes live in the gitignored capture tree. The two conditional "
        "cleaning charges whose sources never state refundability publish "
        "under 1.3's other_charges[].refundable_stated=false rather than "
        "asserting a boolean nobody wrote (%s Phase 5)."
        % (derived.policy_package_schema_version, WORK_ORDER))

    surface = contract["public_surface"]
    surface["seed_hotel_rows"] = derived.seed_hotel_rows
    surface["public_hotel_profile_count"] = derived.published_hotel_profiles
    surface["excluded_public_profile_count"] = derived.excluded_public_profiles

    routes = contract["routes"]
    routes["hotel_route_count"] = derived.hotel_route_count
    routes["published_corridor_route_count"] = derived.corridor_route_count
    routes["note"] = (
        "route_mode market_prefixed: this market's hub, corridor and "
        "policy-comparison pages live under /pet-friendly-hotels/%s/. %s "
        "applied the 32 already-signed founder decisions, taking published "
        "corridors to %d. The market and its corridors remain hidden from "
        "navigation and the sitemap (show_in_navigation=false, "
        "show_in_sitemap=false)."
        % (derived.market_slug, WORK_ORDER, derived.corridor_route_count))

    contract["reconciliation"] = OrderedDict(
        [(field, recon[field]) for field in
         ("confirmed_identities", "published_pet_friendly", "verified_no_pets",
          "out_of_current_category", "resolved", "unresolved")]
        + [("note",
            "%s resolved the founder holds carried out of "
            "PTF-PITTSBURGH-HARDENED-SYNC-004 and added six identities that "
            "each carried a founder signature the sync could not apply while "
            "the identity did not exist, taking the REGISTERED census to %d by "
            "ADD-ONLY promotion -- all 96 prior identities preserved, the "
            "115-row shadow recensus NOT promoted. Authority now stands at %d "
            "published and %d verified-no-pets, after WITHDRAWING SpringHill "
            "Suites Pittsburgh Airport: it published as pet-friendly from a "
            "2026-08-17 capture, and the page this market owns from six days "
            "later states pets are not allowed beside the same fee line. "
            "resolved = %d + %d + %d; unresolved is COUNTED from the committed "
            "final partition, never derived by subtraction."
            % (WORK_ORDER, recon["confirmed_identities"],
               recon["published_pet_friendly"], recon["verified_no_pets"],
               recon["published_pet_friendly"], recon["verified_no_pets"],
               recon["out_of_current_category"]))])

    contract["identity_census"]["expected_count"] = derived.confirmed_identities
    return contract


def run(write: bool) -> int:
    contract = reauthor()
    derived = derive_authority(MARKET_ID)
    problems: List[str] = contract_disagreements(contract, derived)
    print("release-contract disagreements : %d" % len(problems))
    for problem in problems:
        print("   %s" % problem)
    if problems:
        raise ContractError("the re-authored contract still disagrees")
    recon = contract["reconciliation"]
    print("published pet-friendly : %d" % recon["published_pet_friendly"])
    print("verified no-pets       : %d" % recon["verified_no_pets"])
    print("out of category        : %d" % recon["out_of_current_category"])
    print("resolved / unresolved  : %d / %d"
          % (recon["resolved"], recon["unresolved"]))
    print("grants_deployment      : %s"
          % contract["deployment_authorization"]["grants_deployment"])
    if not write:
        print("(check only -- pass --write)")
        return 0

    _write(CONTRACT, contract)
    print("WROTE %s" % CONTRACT.name)
    _write(HANDOFF, OrderedDict((
        ("schema", "ptf-deployment-handoff/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("deployment_performed", False),
        ("deployment_authorization_created", False),
        ("deployment_authorization_required", True),
        ("old_authorization_status",
         "STALE. The authorization that put Pittsburgh's 26 live profiles up "
         "was signed against the release contract this order replaced. Its "
         "policy-package sha256, schema version and record count no longer "
         "describe the market, so it cannot authorise the hardened Pittsburgh. "
         "It is left exactly as committed: repairing or re-signing a "
         "deployment authorization is the founder's act, not this order's."),
        ("values_a_future_authorization_would_pin", OrderedDict((
            ("market_id", MARKET_ID),
            ("policy_package_path", derived.policy_package_path),
            ("policy_package_sha256", derived.policy_package_sha256),
            ("policy_package_schema_version", derived.policy_package_schema_version),
            ("policy_package_record_count", derived.policy_package_record_count),
            ("seed_hotel_rows", derived.seed_hotel_rows),
            ("published_hotel_profiles", derived.published_hotel_profiles),
            ("confirmed_identities", derived.confirmed_identities),
            ("verified_no_pets", derived.verified_no_pets),
            ("resolved", derived.resolved),
            ("unresolved", derived.unresolved),
            ("hotel_route_count", derived.hotel_route_count),
            ("corridor_route_count", derived.corridor_route_count),
        ))),
        ("launch_participation_unchanged", True),
        ("navigation_and_sitemap", "unchanged -- Pittsburgh stays hidden"),
    )))
    print("WROTE %s" % HANDOFF.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except ContractError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

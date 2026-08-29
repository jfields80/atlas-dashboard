"""PTF-DETROIT-ANN-ARBOR-DISPLAY-INVENTORY-AND-RELEASE-CONTRACT-005 -- author
the Detroit release contract.

A release contract is required of every market that has inventory to release.
Detroit held real policy authority from Pass 1 onward and still had none, so it
was correctly contractless; seeding it in this order is what makes the contract
both possible and mandatory.

EVERY COUNT IS DERIVED
----------------------
``release_contracts.derive_authority`` reads this market's own committed
authority and returns the numbers. Nothing here recomputes one. A contract that
states its own count of something the authority also derives is a second source
of truth waiting to disagree, and the assembler's
``authority.reconciliation_matches_market_authority`` gate exists precisely to
catch that disagreement -- there is no reason to hand it one.

IT GRANTS NO DEPLOYMENT
-----------------------
``grants_deployment`` is false and ``asserts_market_complete`` is false. A
passing contract says the assembled package is STRUCTURALLY sound. It says
nothing about whether this market should be published, and Detroit has open
founder rulings, a 238-row shadow census staged and unpromoted, and no launch
participation.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.release_contracts import (
    RELEASE_CONTRACTS_DIR, contract_disagreements, contract_path,
    derive_authority, load_contract,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-DISPLAY-INVENTORY-AND-RELEASE-CONTRACT-005"

#: Structural sections every market's contract shares -- canonical hosts, the
#: release-gate list, the forbidden-output tokens and the publish rules. They
#: describe the PIPELINE, not the market, so they are read from a committed
#: sibling contract rather than retyped and quietly diverged.
STRUCTURAL_SECTIONS = ("canonical", "minimum_release_gates",
                       "forbidden_output_tokens", "publish")
STRUCTURAL_SOURCE = "pittsburgh-pa"


def build() -> OrderedDict:
    authority = derive_authority(MARKET)
    market = json.loads((PACKAGE / "markets" / ("%s.json" % MARKET))
                        .read_text(encoding="utf-8"))
    partition = json.loads((PACKAGE / "detroit_ann_arbor_final_partition_001.json")
                           .read_text(encoding="utf-8"))
    sibling = json.loads((RELEASE_CONTRACTS_DIR / ("%s.json" % STRUCTURAL_SOURCE))
                         .read_text(encoding="utf-8"))
    states = partition["final_state_counts"]
    awaiting = states.get("AWAITING_POLICY_OBSERVATION", 0)

    doc = OrderedDict([
        ("schema", "ptf-market-release-contract/1.0"),
        ("contract_id", "pettripfinder-detroit-ann-arbor-mi-release/1.0"),
        ("market_id", MARKET),
        ("product", "pettripfinder-detroit-ann-arbor-mi"),
        ("release_name_prefix", "prod-006-detroit-ann-arbor"),
        ("description",
         "Deterministic release-gate contract for the PetTripFinder Detroit-Ann Arbor "
         "market (%s). Consumed by scripts/pettripfinder/assemble_netlify_bundle.py. "
         "Every count below is DERIVED from this market's own committed authority by "
         "release_contracts.derive_authority; none is hand-calculated and none is "
         "inherited from or comparable to another market's contract. It exists because "
         "this order seeded the market's display inventory for the first time -- Detroit "
         "has held real policy authority since Pass 1 but had nothing to release until "
         "now. Contains NO credentials and NO remote project identifiers. The committed "
         "hotel-policy package is the single identity authority for the verified hotels; "
         "this contract deliberately does NOT duplicate a hard-coded allow-list."
         % WORK_ORDER),
        ("deployment_authorization", OrderedDict([
            ("grants_deployment", False),
            ("asserts_market_complete", False),
            ("means",
             "A passing contract means this market's assembled package is STRUCTURALLY "
             "deployable: its authority files agree, its display inventory matches its "
             "reviewed publications, no held identity leaks, and every publish/tech gate "
             "holds. It is NOT a deployment authorization and it makes no claim that this "
             "market's identity universe is resolved. %d of its %d identities are still "
             "awaiting policy observation; a %d-row shadow recensus is staged and "
             "UNPROMOTED; ten municipalities and one same-address identity pair await "
             "founder rulings; the market is hidden from navigation and the sitemap; it "
             "holds no launch participation; and NO founder deployment decision exists "
             "for Detroit."
             % (awaiting, authority.confirmed_identities, 238)),
        ])),
        ("canonical", sibling["canonical"]),
        ("identity_census", OrderedDict([
            ("path", "launch_packages/pettripfinder/identity_census/%s.json" % MARKET),
            ("schema", "ptf-market-identity-census/1.1"),
            ("expected_count", authority.confirmed_identities),
            ("note",
             "%d canonical identities. 182 until founder ruling DTW-ID-003-NOVI-11-MILE "
             "superseded the stale Courtyard Detroit Novi identity with its Sonesta "
             "Select successor at one address; the retired name is preserved as that "
             "row's former_name and in the duplicate ledger."
             % authority.confirmed_identities),
        ])),
        ("reconciliation", OrderedDict([
            ("confirmed_identities", authority.confirmed_identities),
            ("published_pet_friendly", authority.published_hotel_profiles),
            ("verified_no_pets", authority.verified_no_pets),
            ("out_of_current_category",
             authority.resolved - authority.published_hotel_profiles
             - authority.verified_no_pets),
            ("resolved", authority.resolved),
            ("unresolved", authority.unresolved),
            ("note",
             "7/7 until founder decision B-003-1 registered the text_extract artifact "
             "kind, which unblocked the 28-row Capture Pass 3 packet: 10 publications and "
             "18 first-party refusals, each re-hashed from disk and quote-checked verbatim "
             "against the artifact bytes at approval time. Two POLICY_NOT_FOUND rows were "
             "NOT converted -- source silence is absence, not a refusal -- and remain "
             "held, outside both authority and this market's display inventory."),
        ])),
        ("reconciliation_cross_checks", [OrderedDict([
            ("path", "launch_packages/pettripfinder/detroit_ann_arbor_final_partition_001.json"),
            ("key_map", OrderedDict([("confirmed_identities", "count")])),
            ("note",
             "The committed final partition is the disposition authority; its count is "
             "the same %d-identity universe the census commits."
             % authority.confirmed_identities),
        ])]),
        ("policy_package", OrderedDict([
            ("path", authority.policy_package_path),
            ("expected_sha256", authority.policy_package_sha256),
            ("expected_schema_version", authority.policy_package_schema_version),
            ("expected_record_count", authority.policy_package_record_count),
            ("identity_authority", True),
            ("note",
             "The verified hotel identities are DERIVED from this package at assembly "
             "time via release_contracts.derive_authority, never from a list duplicated "
             "here."),
        ])),
        ("public_surface", OrderedDict([
            ("seed_hotel_rows", authority.seed_hotel_rows),
            ("public_hotel_profile_count", authority.published_hotel_profiles),
            ("excluded_public_profile_count", authority.excluded_public_profiles),
            ("held_hotel_exclusion",
             "Every seed hotel this market owns that is absent from the committed package "
             "must not render a public profile. This market's display inventory IS its "
             "published set -- it was seeded from that package, one row per approved "
             "record -- so the difference is zero by construction rather than by luck, "
             "and a future publication that forgets to seed will show up here as a "
             "mismatch rather than as a missing page."),
        ])),
        ("routes", OrderedDict([
            ("market_slug", authority.market_slug),
            ("route_mode", authority.route_mode),
            ("hotel_route_count", authority.hotel_route_count),
            ("published_corridor_route_count", authority.corridor_route_count),
            ("note",
             "route_mode %s: this market's hub, corridor and policy-comparison pages live "
             "under its own prefix. %d corridor route(s) meet this market's "
             "minimum_hotel_count of 5 and therefore render; the other corridors hold "
             "published hotels but not yet enough of them. The identity-ROUTING authority "
             "is a different thing entirely and now holds 162 records: seeding WITHDREW "
             "the 17 routes publication answered, because the display inventory is the "
             "source of truth for a published hotel."
             % (authority.route_mode, authority.corridor_route_count)),
        ])),
        ("minimum_release_gates", sibling["minimum_release_gates"]),
        ("forbidden_output_tokens", sibling["forbidden_output_tokens"]),
        ("publish", sibling["publish"]),
        ("market_visibility", OrderedDict([
            ("show_in_navigation", market["show_in_navigation"]),
            ("show_in_sitemap", market["show_in_sitemap"]),
            ("minimum_published_hotels", market["minimum_published_hotels"]),
            ("launch_participation", False),
            ("readiness_state", "CANDIDATE_MARKET"),
            ("note",
             "Hidden on purpose. This market assembles as a CANDIDATE: its authority is "
             "internally consistent and its display inventory is real, but it carries no "
             "launch participation and no founder deployment decision, and it is "
             "reachable only by direct URL until it does."),
        ])),
    ])
    return doc


def main(argv=None) -> int:
    doc = build()
    path = contract_path(MARKET)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")

    # Written, then immediately read back and checked against the authority it
    # claims to describe. A contract nobody verified is a claim, not a gate.
    disagreements = contract_disagreements(load_contract(MARKET), derive_authority(MARKET))
    if disagreements:
        raise SystemExit("STOP: contract disagrees with derived authority: %s"
                         % list(disagreements))
    print("release contract  : %s" % path.relative_to(_REPO_ROOT).as_posix())
    print("disagreements     : 0")
    rec = doc["reconciliation"]
    print("counts            : census %d | published %d | no-pets %d | resolved %d | "
          "unresolved %d | seed %d"
          % (doc["identity_census"]["expected_count"], rec["published_pet_friendly"],
             rec["verified_no_pets"], rec["resolved"], rec["unresolved"],
             doc["public_surface"]["seed_hotel_rows"]))
    print("grants_deployment : %s" % doc["deployment_authorization"]["grants_deployment"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

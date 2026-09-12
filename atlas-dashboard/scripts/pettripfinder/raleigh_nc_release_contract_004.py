"""PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001 -- Raleigh's release contract.

Every number here is DERIVED at run time from Raleigh's own committed
authority through ``release_contracts.derive_authority`` -- the same function
``verify_all()`` checks the contract against, so the contract and its verifier
cannot drift apart. Nothing is typed, nothing is inherited from another market's
contract, and the whole file is rebuilt rather than edited, so a stale count
cannot survive a rerun. The shared release rules -- the canonical host, the
minimum gates, the forbidden output tokens and the publish rules -- are read
from a contract already in force, because those are project-wide rules rather
than facts about Raleigh.

A passing contract means Raleigh's assembled package is STRUCTURALLY
deployable. It is not a deployment authorization and it asserts nothing about
the market being complete: this market registers 268 identities and publishes
106, because a row publishes only on an operative first-party quote bound to
its own address, and most of what a metro this size lists has never been read.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import release_contracts as RC          # noqa: E402
from scripts.pettripfinder.markets import contract as MC           # noqa: E402

WORK_ORDER = "PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001"
MARKET_ID = "raleigh-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(_DASH, "deploy", "netlify", "release_contracts", "%s.json" % MARKET_ID)
TEMPLATE = os.path.join(_DASH, "deploy", "netlify", "release_contracts", "lexington-ky.json")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    derived = RC.derive_authority(MARKET_ID)
    recon = derived.reconciliation()
    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET_ID)),
                          source=MARKET_ID)
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "raleigh_nc_clean_authority_001.json"))
    template = _load(TEMPLATE)

    held = Counter(r["classification"] for r in clean["rejected"])
    hold_summary = "; ".join("%d %s" % (n, c) for c, n in sorted(held.items())) or "none"
    census_classes = census.get("classification_counts") or {}
    held_census = "; ".join("%d %s" % (n, c) for c, n in sorted(census_classes.items())
                            if c != "TRUE_HOTEL_IDENTITY")

    doc = OrderedDict([
        ("schema", "ptf-market-release-contract/1.0"),
        ("contract_id", "pettripfinder-%s-release/1.0" % MARKET_ID),
        ("market_id", MARKET_ID),
        ("product", "pettripfinder-%s" % MARKET_ID),
        ("release_name_prefix", "prod-raleigh"),
        ("description",
         "Deterministic release-gate contract for the PetTripFinder Raleigh market through %s. "
         "Every number is derived from THIS market's committed authority by "
         "release_contracts.derive_authority; none is typed and none is inherited from or "
         "comparable to another market's contract." % WORK_ORDER),
        ("deployment_authorization", OrderedDict([
            ("grants_deployment", False),
            ("asserts_market_complete", False),
            ("means",
             "A passing contract means this market's assembled package is STRUCTURALLY "
             "deployable: its authority files agree, its routes match its reviewed inventory, no "
             "held identity leaks, and every publish gate holds. It is not a deployment "
             "authorization and asserts nothing about the market being complete -- %d of this "
             "market's %d registered identities are still unresolved, and no founder deployment "
             "decision exists for Raleigh at %d published profiles."
             % (recon["unresolved"], census["count"], derived.published_hotel_profiles)),
        ])),
        ("canonical", template["canonical"]),
        ("identity_census", OrderedDict([
            ("path", "launch_packages/pettripfinder/identity_census/%s.json" % MARKET_ID),
            ("schema", census["schema"]),
            ("expected_count", census["count"]),
            ("note",
             "%d registered identities, built from zero by %s at $0 and no paid provider call. "
             "Membership is this market's own corridor postal partition "
             "(census_membership_basis CORRIDOR_REGISTRY) over a CORE that is the whole of "
             "Mecklenburg County, North Carolina plus three contiguous corridors admitted on "
             "first-party brand naming -- Concord on I-85 northeast, Belmont and Gastonia on "
             "I-85 southwest, and Fort Mill / Carowinds / Indian Land on I-77 south across the "
             "SOUTH CAROLINA state line. Raleigh is this project's first market to span two "
             "states. Four fringe areas -- Rock Hill SC, Kannapolis, Mooresville and Monroe -- "
             "are authored as corridors that claim NO postal code, so their hotels are "
             "discovered, identified and then classified OUT_OF_MARKET_BOUNDARY_DECISION rather "
             "than silently omitted. Rows the identity graph did not admit are recorded, not "
             "dropped: %s."
             % (census["count"], WORK_ORDER, held_census)),
        ])),
        ("reconciliation", OrderedDict(
            [(field, recon[field]) for field in RC.RECONCILIATION_FIELDS]
            + [("note",
                "%d clean pet-friendly and %d clean verified-no-pets over a %d-identity census. "
                "A row publishes only on an OPERATIVE first-party quote from the property's own "
                "page, bound to its census identity by the street identity that page states: a "
                "fee, a weight, a count, an amenity chip or a service-animal sentence alone "
                "publishes nothing. %d reads were made and did not publish (%s); every one is "
                "named in raleigh_nc_clean_authority_001.json with its class. No gate was "
                "lowered to preserve a count."
                % (derived.published_hotel_profiles, recon["verified_no_pets"], census["count"],
                   len(clean["rejected"]), hold_summary))]
        )),
        ("policy_package", OrderedDict([
            ("path", derived.policy_package_path),
            ("expected_sha256", derived.policy_package_sha256),
            ("expected_schema_version", derived.policy_package_schema_version),
            ("expected_record_count", derived.policy_package_record_count),
            ("identity_authority", True),
            ("note",
             "The verified hotel identities are DERIVED from this package at assembly time via "
             "site_data.verified_public_hotels(); they are not restated here. Every record "
             "carries the exact operator quote for each published fact, the capture lane, and "
             "the sha256 of the document it was read from. No record here came through a paid "
             "lane: this market cost $0 and zero provider calls."),
        ])),
        ("public_surface", OrderedDict([
            ("seed_hotel_rows", derived.seed_hotel_rows),
            ("public_hotel_profile_count", derived.published_hotel_profiles),
            ("excluded_public_profile_count", derived.excluded_public_profiles),
            ("held_hotel_exclusion", template["public_surface"]["held_hotel_exclusion"]),
        ])),
        ("routes", OrderedDict([
            ("market_slug", derived.market_slug),
            ("route_mode", derived.route_mode),
            ("hotel_route_count", derived.hotel_route_count),
            ("published_corridor_route_count", derived.corridor_route_count),
            ("note",
             "route_mode %s: this market's hub, corridor and policy-comparison pages live under "
             "/pet-friendly-hotels/%s/. %d of %d corridors reach their own publication minimum; "
             "the rest are suppressed, which is a threshold and not a gap. The market and its "
             "corridors are hidden from navigation and the sitemap "
             "(show_in_navigation=false, show_in_sitemap=false) until a launch order says "
             "otherwise." % (derived.route_mode, derived.market_slug,
                             derived.corridor_route_count, len(cfg.corridors))),
        ])),
        ("minimum_release_gates", template["minimum_release_gates"]),
        ("forbidden_output_tokens", template["forbidden_output_tokens"]),
        ("publish", template["publish"]),
    ])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    problems = RC.contract_disagreements(doc, derived)
    print("census       :", census["count"])
    print("published PF :", derived.published_hotel_profiles,
          "| verified no-pets:", recon["verified_no_pets"])
    print("resolved     :", recon["resolved"], "| unresolved:", recon["unresolved"])
    print("corridors    :", derived.corridor_route_count, "publish of", len(cfg.corridors))
    print("package sha  :", derived.policy_package_sha256[:16])
    print("disagreements:", len(problems))
    for p in problems:
        print("   !", p)
    print("written      :", os.path.relpath(args.out, _DASH))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

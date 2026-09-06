"""PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002 -- Phase 4b, Toledo's release contract.

Every number here is DERIVED from Toledo's own committed authority at run time.
Nothing is typed, nothing is inherited from another market's contract, and the
whole file is rebuilt rather than edited, so a stale count cannot survive a
rerun. The gate list, the forbidden-token list and the publish rules are copied
from the market contracts already in force, because those are project-wide
release rules rather than facts about Toledo.

A passing contract means Toledo's assembled package is STRUCTURALLY deployable.
It is not a deployment authorization and it asserts nothing about the market
being complete: 28 of its 54 confirmed identities are still unresolved.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.assemble_netlify_bundle import content_sha256  # noqa: E402
from scripts.pettripfinder import market_authority as MA          # noqa: E402
from scripts.pettripfinder.markets import contract as MC          # noqa: E402

WORK_ORDER = "PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002"
MARKET_ID = "toledo-oh"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
OUT = os.path.join(_DASH, "deploy", "netlify", "release_contracts", "%s.json" % MARKET_ID)
TEMPLATE = os.path.join(_DASH, "deploy", "netlify", "release_contracts", "pittsburgh-pa.json")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET_ID)),
                          source=MARKET_ID)
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(PKG, "toledo_oh_final_partition_001.json"))
    policy_path = os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET_ID)
    policy = _load(policy_path)
    exclusions = MA.load_market_exclusions(MARKET_ID)
    seed_rows = MA.load_market_seed_rows(MARKET_ID)
    template = _load(TEMPLATE)

    pf = len(policy["hotels"])
    no_pets = len(exclusions)
    counts = Counter(i["final_state"] for i in partition["items"])
    resolved = sum(1 for i in partition["items"] if i["resolved"])
    unresolved = partition["count"] - resolved

    # Corridors publish only at or above their own minimum. Derived, never typed.
    per_corridor = Counter(h.get("corridor", "") for h in
                           _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))["hotels"])
    published_by_corridor = Counter()
    keys = {h["key"] for h in policy["hotels"]}
    for h in census["hotels"]:
        if h["identity_key"] in keys:
            published_by_corridor[h["corridor"]] += 1
    published_corridors = [c.corridor_id for c in cfg.corridors
                           if published_by_corridor.get(c.corridor_id, 0) >= c.minimum_hotel_count]

    doc = OrderedDict([
        ("schema", "ptf-market-release-contract/1.0"),
        ("contract_id", "pettripfinder-%s-release/1.0" % MARKET_ID),
        ("market_id", MARKET_ID),
        ("product", "pettripfinder-%s" % MARKET_ID),
        ("release_name_prefix", "prod-toledo"),
        ("description",
         "Deterministic release-gate contract for the PetTripFinder Toledo market through %s. "
         "Every number is derived from THIS market's committed authority; none is inherited from "
         "or comparable to another market's contract." % WORK_ORDER),
        ("deployment_authorization", OrderedDict([
            ("grants_deployment", False),
            ("asserts_market_complete", False),
            ("means",
             "A passing contract means this market's assembled package is STRUCTURALLY "
             "deployable: its authority files agree, its routes match its reviewed inventory, no "
             "held identity leaks, and every publish gate holds. It is not a deployment "
             "authorization and asserts nothing about the market being complete -- %d of this "
             "market's %d confirmed identities are still unresolved, five addresses carry two "
             "chain identities each and are held by founder ruling TOLEDO-R2, and no founder "
             "deployment decision exists for Toledo at %d published profiles."
             % (unresolved, census["count"], pf)),
        ])),
        ("canonical", template["canonical"]),
        ("identity_census", OrderedDict([
            ("path", "launch_packages/pettripfinder/identity_census/%s.json" % MARKET_ID),
            ("schema", census["schema"]),
            ("expected_count", census["count"]),
            ("note",
             "%d confirmed identities built from zero by PTF-TOLEDO-OH-NEW-MARKET-001 across four "
             "free discovery lanes -- a local OSM extract, the owned Marriott and Wyndham brand "
             "harvests, Hilton's own city pages and Destination Toledo's partner roster -- and "
             "reconciled into one identity graph. Every admitted row carries a street or a phone, "
             "a postal code claimed by exactly one corridor, and the observations that admitted "
             "it. The census policy_state column is legacy-frozen at POLICY_NOT_VERIFIED (the "
             "Cleveland precedent); the final partition and the policy/exclusion authorities are "
             "the publication truth." % census["count"]),
        ])),
        ("reconciliation", OrderedDict([
            ("confirmed_identities", census["count"]),
            ("published_pet_friendly", pf),
            ("verified_no_pets", no_pets),
            ("out_of_current_category", 0),
            ("resolved", resolved),
            ("unresolved", unresolved),
            ("note",
             "%s promoted the clean inventory PTF-TOLEDO-OH-NEW-MARKET-001 left pending: %d "
             "pet-friendly and %d verified-no-pets, every one bound to a first-party page by an "
             "identity the page itself confirmed, and every one audited against the known "
             "wrong-evidence classes. Bowling Green is in by founder ruling TOLEDO-R1A. The tenth "
             "refusal this market read is NOT here: founder ruling TOLEDO-R3 holds both reads at "
             "10667/10667B Fremont Pike, where address_key collapses a building letter and two "
             "Wyndham brands state opposite policies." % (WORK_ORDER, pf, no_pets)),
        ])),
        ("reconciliation_cross_checks", [OrderedDict([
            ("path", "launch_packages/pettripfinder/toledo_oh_final_partition_001.json"),
            ("key_map", {"confirmed_identities": "count"}),
            ("note", "The committed final partition is the disposition authority; every census "
                     "identity appears in it exactly once."),
        ])]),
        ("policy_package", OrderedDict([
            ("path", "launch_packages/pettripfinder/hotel_policy_facts_%s.json" % MARKET_ID),
            # content_sha256, never a raw byte hash: git rewrites LF to CRLF on
            # checkout, so a byte hash makes the same reviewed package hash
            # differently in a fresh clone (PTF-SITE-005).
            ("expected_sha256", content_sha256(open(policy_path, "rb").read())),
            ("expected_schema_version", policy["schema_version"]),
            ("expected_record_count", pf),
            ("identity_authority", True),
            ("note",
             "The verified hotel identities are DERIVED from this package at assembly time via "
             "site_data.verified_public_hotels(); they are not restated here. Every record "
             "carries the exact quote its fact came from, the lane that read it and the sha256 of "
             "the document. Where a source states a per-night ladder beside a headline fee, both "
             "are published as fee_tiers rather than flattening to one price."),
        ])),
        ("public_surface", OrderedDict([
            ("seed_hotel_rows", len(seed_rows)),
            ("public_hotel_profile_count", pf),
            ("excluded_public_profile_count", len(seed_rows) - pf),
            ("held_hotel_exclusion", template["public_surface"]["held_hotel_exclusion"]),
        ])),
        ("routes", OrderedDict([
            ("market_slug", cfg.market_slug),
            ("route_mode", cfg.route_mode),
            ("hotel_route_count", pf),
            ("published_corridor_route_count", len(published_corridors)),
            ("published_corridors", published_corridors),
            ("note",
             "route_mode %s: this market's hub, corridor and policy-comparison pages live under "
             "/pet-friendly-hotels/%s/. %d of %d corridors reach their own publication minimum; "
             "the rest are suppressed, which is a threshold and not a gap. The market and its "
             "corridors are hidden from navigation and the sitemap "
             "(show_in_navigation=false, show_in_sitemap=false) until a launch order says "
             "otherwise." % (cfg.route_mode, cfg.market_slug,
                             len(published_corridors), len(cfg.corridors))),
        ])),
        ("minimum_release_gates", template["minimum_release_gates"]),
        ("forbidden_output_tokens", template["forbidden_output_tokens"]),
        ("publish", template["publish"]),
    ])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("census      :", census["count"])
    print("published PF:", pf, "| verified no-pets:", no_pets)
    print("resolved    :", resolved, "| unresolved:", unresolved)
    print("partition   :", dict(counts))
    print("corridors   :", len(published_corridors), "publish of", len(cfg.corridors))
    print("package sha :", doc["policy_package"]["expected_sha256"][:16])
    print("written     :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

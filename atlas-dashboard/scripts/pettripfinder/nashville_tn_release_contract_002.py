"""PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002 -- Nashville's release contract.

Every number here is DERIVED from Nashville's own committed authority at run
time. Nothing is typed, nothing is inherited from another market's contract, and
the whole file is rebuilt rather than edited, so a stale count cannot survive a
rerun. The gate list, the forbidden-token list and the publish rules are read
from the market contracts already in force, because those are project-wide
release rules rather than facts about Nashville.

A passing contract means Nashville's assembled package is STRUCTURALLY
deployable. It is not a deployment authorization and it asserts nothing about
the market being complete -- Nashville is, on purpose, registered far below the
inventory it discovered, because most of its reads cannot meet the modern
evidence standard.
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

from scripts.pettripfinder.assemble_netlify_bundle import content_sha256  # noqa: E402
from scripts.pettripfinder import market_authority as MA          # noqa: E402
from scripts.pettripfinder.markets import contract as MC          # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002"
SHADOW_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
OUT = os.path.join(_DASH, "deploy", "netlify", "release_contracts", "%s.json" % MARKET_ID)
TEMPLATE = os.path.join(_DASH, "deploy", "netlify", "release_contracts", "lexington-ky.json")


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
    partition = _load(os.path.join(PKG, "nashville_tn_final_partition_001.json"))
    holds = _load(os.path.join(PKG, "nashville_tn_identity_holds_002.json"))
    shadow = _load(os.path.join(PKG, "markets", "reports",
                                "nashville_tn_shadow_market_001.json"))
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
    projected = shadow["projected"]

    keys = {h["key"] for h in policy["hotels"]}
    published_by_corridor = Counter()
    for h in census["hotels"]:
        if h["identity_key"] in keys:
            published_by_corridor[h["corridor"]] += 1
    published_corridors = [c.corridor_id for c in cfg.corridors
                           if published_by_corridor.get(c.corridor_id, 0) >= c.minimum_hotel_count]

    hold_summary = "; ".join("%d %s" % (n, c) for c, n in holds["counts_by_class"].items())
    gate_summary = "; ".join("%d %s" % (n, c)
                             for c, n in holds["counts_by_gate_classification"].items())

    doc = OrderedDict([
        ("schema", "ptf-market-release-contract/1.0"),
        ("contract_id", "pettripfinder-%s-release/1.0" % MARKET_ID),
        ("market_id", MARKET_ID),
        ("product", "pettripfinder-%s" % MARKET_ID),
        ("release_name_prefix", "prod-nashville"),
        ("description",
         "Deterministic release-gate contract for the PetTripFinder Nashville market through %s. "
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
             "market's %d registered identities are still unresolved, %d rows are held by the "
             "modern production gates and publish nothing, and no founder deployment decision "
             "exists for Nashville at %d published profiles."
             % (unresolved, census["count"], holds["count"], pf)),
        ])),
        ("canonical", template["canonical"]),
        ("identity_census", OrderedDict([
            ("path", "launch_packages/pettripfinder/identity_census/%s.json" % MARKET_ID),
            ("schema", census["schema"]),
            ("expected_count", census["count"]),
            ("note",
             "%d registered identities, carried across from the %d-identity shadow %s built from "
             "zero for $0 and 17 Firecrawl credits. Membership is this market's own corridor "
             "postal partition (census_membership_basis CORRIDOR_REGISTRY), with Opryland and "
             "Vanderbilt/West End claiming their properties by explicit_hotel_ids so display "
             "stays true without making membership ambiguous. One shadow identity is NOT "
             "registered: the registered census contract requires a city and no committed source "
             "states one for it. It is named in nashville_tn_identity_holds_002.json."
             % (census["count"], projected["census"], SHADOW_ORDER)),
        ])),
        ("reconciliation", OrderedDict([
            ("confirmed_identities", census["count"]),
            ("published_pet_friendly", pf),
            ("verified_no_pets", no_pets),
            ("out_of_current_category", 0),
            ("resolved", resolved),
            ("unresolved", unresolved),
            ("note",
             "%s registered the clean inventory %s left pending -- %d clean pet-friendly and %d "
             "clean verified-no-pets. The count gate reproduced all four shadow numbers exactly "
             "BEFORE any row was removed, and only then did the modern gates run. %d rows are "
             "held and publish nothing (%s; by gate: %s). The dominant hold is NO_CAPTURE_HASH: "
             "the shadow's attended browser lane read 154 pages for $0 and recorded a byte "
             "LENGTH rather than a document hash, so those reads cannot be tied to a document "
             "and cannot be published. Every held row keeps its registered census identity. No "
             "gate was lowered to preserve a count."
             % (WORK_ORDER, SHADOW_ORDER, projected["pet_friendly"],
                projected["verified_no_pets"], holds["count"], hold_summary, gate_summary)),
        ])),
        ("reconciliation_cross_checks", [OrderedDict([
            ("path", "launch_packages/pettripfinder/nashville_tn_final_partition_001.json"),
            ("key_map", {"confirmed_identities": "count"}),
            ("note", "The committed final partition is the disposition authority; every "
                     "registered census identity appears in it exactly once."),
        ])]),
        ("policy_package", OrderedDict([
            ("path", "launch_packages/pettripfinder/hotel_policy_facts_%s.json" % MARKET_ID),
            ("expected_sha256", content_sha256(open(policy_path, "rb").read())),
            ("expected_schema_version", policy["schema_version"]),
            ("expected_record_count", pf),
            ("identity_authority", True),
            ("note",
             "The verified hotel identities are DERIVED from this package at assembly time via "
             "site_data.verified_public_hotels(); they are not restated here. Every record "
             "carries the exact operator quote for each published fact, the capture lane, the "
             "sha256 of the document it was read from, and -- because every published row here "
             "came through a paid lane -- the reservation that bought the page, whose request "
             "envelope hash is derived from the committed run rather than invented."),
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
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
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

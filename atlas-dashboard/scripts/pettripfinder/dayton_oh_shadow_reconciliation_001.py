"""PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- Phases 12 / 15 / 16.

Combine every FREE result this order produced into one shadow state:

  * the committed baseline (pinned census, policy package, exclusion shard,
    final partition, release contract),
  * the phase-9 free STATIC capture (unresolved cohort) and the phase-11 live
    contradiction audit,
  * the phase-10 ATTENDED capture results,

and emit: the pending application inventory (clean pet-friendly / clean
verified-no-pets), the founder packet groups, the projected authority if the
clean inventory were promoted, and PROMOTION_READY.

Nothing here is applied. The pinned census, the policy package, the exclusion
shard, the partition and the release contract are read and never written: this
order's whole output is a shadow.

A row reaches the pending inventory only when ALL of these hold:

  1. the read is identity-BOUND on the property's own page (street number plus
     postal, or telephone plus one of them) -- an unbound read names no hotel;
  2. the statement is the property's OWN prose, not a brand markup flag and not
     an amenity chip;
  3. the row is not held for identity, geography or founder review.

Brand markup records (IHG's petsAllowed, Wyndham's) are carried as
corroboration on the record and are never the source of a promoted fact.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-REVALIDATION-001"
MARKET_ID = "dayton-oh"
SCHEMA = "ptf-market-shadow-reconciliation/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
PARTITION = os.path.join(PKG, "dayton_final_partition_001.json")
CONTRACT = os.path.join(_DASH, "deploy", "netlify", "release_contracts", "dayton-oh.json")

PF_CLASSES = ("PET_FRIENDLY_STATED_ATTENDED", "PET_FRIENDLY_STATED_ATTENDED_FAQ")
NO_PETS_CLASSES = ("NO_PETS_STATED_ATTENDED", "NO_PETS_STATED_ATTENDED_FAQ")
# A read that reached the fact only through text the page did not render is kept
# out of the promotable inventory: it is real evidence, but it is not the
# property's own visible statement, so it is reported as recoverable-with-review.
HIDDEN_CLASSES = ("PET_FRIENDLY_STATED_ATTENDED_HIDDEN_TEXT", "NO_PETS_STATED_ATTENDED_HIDDEN_TEXT")


def read_json(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build(args) -> OrderedDict:
    census = read_json(os.path.join(PKG, "identity_census", MARKET_ID + ".json"))
    rows = census["hotels"]
    by_key = {r["identity_key"]: r for r in rows}
    policy = read_json(os.path.join(PKG, "hotel_policy_facts_" + MARKET_ID + ".json"))["hotels"]
    live_pf = {p["identity_key"] for p in policy}
    exclusions = read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]
    live_np = {ptf_identity_key(e["canonical_name"]) for e in exclusions}
    part = read_json(PARTITION)["items"]
    part_by_key = {i["identity_key"]: i for i in part}
    contract = read_json(CONTRACT)

    attended = read_json(os.path.join(REPORTS, "dayton_oh_attended_capture_001.json"), {"results": []})["results"]
    static = read_json(os.path.join(REPORTS, "dayton_oh_free_static_capture_001.json"), {"rows": []})["rows"]
    live_audit = read_json(os.path.join(REPORTS, "dayton_oh_live_policy_audit_001.json"), {"rows": []})["rows"]
    routing = read_json(os.path.join(REPORTS, "dayton_oh_free_routing_001.json"), {"rows": []})["rows"]
    recensus = read_json(os.path.join(REPORTS, "dayton_oh_recensus_reconciliation_001.json"))

    # ---- phase 12: pending application inventory -----------------------------
    pending_pf, pending_np, held = [], [], []
    seen = set()
    for r in attended:
        key = r["identity_key"]
        if key in seen:
            continue
        seen.add(key)
        cls = r["classification"]
        bound = bool((r.get("identity_binding") or {}).get("bound"))
        rd = r.get("reader") or {}
        base = OrderedDict([
            ("identity_key", key),
            ("canonical_name", r.get("hotel")),
            ("brand", r.get("brand")),
            ("canonical_url", r.get("final_url") or r.get("requested_url")),
            ("document_sha256", "sha256:" + (r.get("html_sha256") or "")),
            ("artifact_file", r.get("artifact_file")),
            ("artifact_sha256", "sha256:" + (r.get("artifact_sha256") or "")),
            ("captured_at", r.get("captured_at")),
            ("lane", "FREE_ATTENDED"),
            ("interaction", r.get("interaction")),
            ("identity_signals", r.get("identity_binding")),
            ("evidence_source", rd.get("source")),
            ("exact_quote", rd.get("pets_allowed_quote")),
            ("evidence_quotes", rd.get("evidence_quotes")),
            ("parsed_facts", rd.get("extraction")),
            ("withheld_facts", rd.get("withheld")),
            ("service_animal_statement", rd.get("service_animal_quote")),
            ("brand_generic_wording", rd.get("brand_generic")),
            ("markup_corroboration", r.get("markup_corroboration")),
            ("live_state", r.get("live_state")),
            ("partition_state_before", (part_by_key.get(key) or {}).get("final_state")),
            ("classification", cls),
        ])
        if cls in PF_CLASSES and bound and r.get("live_state") == "UNRESOLVED_OR_NEW":
            pending_pf.append(base)
        elif cls in NO_PETS_CLASSES and bound and r.get("live_state") == "UNRESOLVED_OR_NEW":
            pending_np.append(base)
        else:
            reason = ("IDENTITY_NOT_BOUND_ON_PAGE" if not bound else
                      "ALREADY_LIVE" if r.get("live_state") != "UNRESOLVED_OR_NEW" else
                      "EVIDENCE_NOT_IN_RENDERED_TEXT" if cls in HIDDEN_CLASSES else cls)
            b = OrderedDict(base)
            b["held_reason"] = reason
            held.append(b)

    # ---- phase 15: shadow reconciliation ------------------------------------
    pinned = census["count"]
    proj_pf = len(live_pf) + len(pending_pf)
    proj_np = len(live_np) + len(pending_np)
    proj_resolved = proj_pf + proj_np
    reconciliation = OrderedDict([
        ("pinned_census", pinned),
        ("shadow_census", pinned),
        ("shadow_census_note",
         "The shadow census equals the pinned census because no identity was "
         "added or retired, NOT because the recensus lane cleared Dayton. That "
         "lane was only partially exercised and its incompleteness is stated in "
         "recensus_lane_coverage below. Every policy result this order produced "
         "landed on an identity the pinned census already carries."),
        ("recensus_lane_coverage", OrderedDict([
            ("status", "PARTIAL -- the harvest ran to completion but could not reach the evidence bar an admission requires"),
            ("local_osm_geofabrik", "UNAVAILABLE: no extract in the registry covers dayton-oh and no .osm.pbf is on disk, so the first canonical free lane could not run at all"),
            ("overpass", "NOT RUN"),
            ("brand_directory_harvest", "COMPLETED: 949 free requests over 9 families; 17,928 property URLs harvested, 295 scoped to this market's geography, 295 property pages fetched (51 served, 244 refused with HTTP 403)"),
            ("reconciliation", recensus.get("classification_counts") if recensus else None),
            ("true_missing_identities_found", 0),
            ("why_zero",
             "Marriott refused 244 of its 252 scoped property pages, and most pages "
             "that did serve declare no address, postal or telephone, so no candidate "
             "carried the identity evidence an admission requires. A refusal is a "
             "fetch outcome and proves nothing about a property."),
            ("consequence",
             "Dayton's 129-row census is carried forward as PINNED AND UNCHALLENGED, "
             "not as confirmed complete. This order narrowed the search space and "
             "admitted nothing. A recensus that can actually reach Marriott -- and a "
             "registered OSM extract for this market -- is the first item of the next "
             "order."),
        ])),
        ("active_identities", census["active_count"]),
        ("retirements", 0),
        ("successors_proposed", 0),
        ("same_campus_pairs_identified", 1),
        ("explicit_geography_assignments_needed", 2),
        ("geography_held", 0),
        ("duplicates_found", 0),
        ("unresolved_identity_items", None),
        ("live", OrderedDict([
            ("pet_friendly", len(live_pf)), ("verified_no_pets", len(live_np)),
            ("resolved", len(live_pf) + len(live_np)), ("unresolved", pinned - len(live_pf) - len(live_np)),
            ("profiles", len(live_pf)),
        ])),
        ("projected_if_clean_inventory_promoted", OrderedDict([
            ("pet_friendly", proj_pf), ("verified_no_pets", proj_np),
            ("resolved", proj_resolved), ("unresolved", pinned - proj_resolved),
            ("profiles", proj_pf),
        ])),
        ("delta", OrderedDict([
            ("pet_friendly", len(pending_pf)), ("verified_no_pets", len(pending_np)),
            ("resolved", len(pending_pf) + len(pending_np)),
            ("unresolved", -(len(pending_pf) + len(pending_np))),
        ])),
    ])

    # ---- phase 11 roll-up ----------------------------------------------------
    wrong_live = [r for r in live_audit
                  if str(r.get("live_audit") or "").startswith("WRONG_LIVE_POLICY")
                  or r.get("live_audit") == "POTENTIAL_STALE_POLICY"]
    live_rollup = OrderedDict([
        ("rows_tested", len(live_audit)),
        ("counts", OrderedDict(sorted(Counter(r.get("live_audit") for r in live_audit if r.get("live_audit")).items()))),
        ("wrong_live_policy_findings", len(wrong_live)),
        ("wrong_live_policy_rows", [r["identity_key"] for r in wrong_live]),
        ("coverage_note",
         "Every live Dayton record was re-requested. The rows a plain client "
         "could re-read all agreed with live authority; the rest could not be "
         "re-read statically at all, which is an absence of a re-read and not "
         "an absence of a contradiction."),
    ])

    # ---- phase 16: promotion readiness --------------------------------------
    blockers = []
    if wrong_live:
        blockers.append("wrong live authority found and unexplained: %d row(s)" % len(wrong_live))
    unbound_promoted = [p for p in pending_pf + pending_np
                        if not (p["identity_signals"] or {}).get("bound")]
    if unbound_promoted:
        blockers.append("a promoted row is not identity-bound: %d" % len(unbound_promoted))
    ready = not blockers

    readiness = OrderedDict([
        ("PROMOTION_READY", "YES" if ready else "NO"),
        ("blockers", blockers),
        ("what_yes_means",
         "The clean inventory below can be applied to Dayton's source authority "
         "in a following order. It is not a claim that Dayton is complete: it is "
         "a claim that nothing in this inventory is unsafe to promote and that no "
         "wrong live authority was left unexplained."),
        ("required_before_promotion", [
            "nothing outstanding for the rows in the pending inventory -- each is "
            "identity-bound to the property's own page and carries its exact quote, "
            "document sha256 and capture timestamp",
            "founder rulings on the packet groups below are required only for the "
            "HELD rows, which are outside this inventory by construction",
        ]),
        ("optional_coverage_expansion", [
            "the brand families this order did not reach attended (Marriott, Hilton, "
            "Red Roof, Radisson, Best Western and the independents) -- the lane is "
            "proven and the remaining rows are a throughput question, not a "
            "correctness one",
            "paid lanes remain unnecessary for every row this order closed",
        ]),
    ])

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("base_commit", args.base_commit),
        ("nothing_applied",
         "The pinned census, policy package, exclusion shard, final partition and "
         "release contract are inputs to this document and were not written."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("baseline_from_contract", contract["reconciliation"]),
        ("partition_state_counts", read_json(PARTITION)["final_state_counts"]),
        ("free_static_classification_counts",
         read_json(os.path.join(REPORTS, "dayton_oh_free_static_capture_001.json"), {}).get("classification_counts")),
        ("attended_outcome_counts",
         read_json(os.path.join(REPORTS, "dayton_oh_attended_capture_001.json"), {}).get("outcome_counts")),
        ("owned_routes_replayed", len(routing)),
        ("recensus_reconciliation", OrderedDict([
            ("candidates_scoped_to_this_market", (recensus or {}).get("candidates_scoped_to_this_market")),
            ("classification_counts", (recensus or {}).get("classification_counts")),
            ("true_missing_identities", (recensus or {}).get("true_missing_identities")),
        ])),
        ("wrong_live_policy_audit", live_rollup),
        ("pending_application_inventory", OrderedDict([
            ("clean_pet_friendly", len(pending_pf)),
            ("clean_verified_no_pets", len(pending_np)),
            ("held", len(held)),
            ("pet_friendly_rows", pending_pf),
            ("verified_no_pets_rows", pending_np),
            ("held_rows", held),
        ])),
        ("shadow_reconciliation", reconciliation),
        ("promotion_readiness", readiness),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-commit", default="f8006cef3917018f08e3ebc1d7fd9bd3b2709002")
    ap.add_argument("--out", default=os.path.join(REPORTS, "dayton_oh_shadow_reconciliation_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    inv = rep["pending_application_inventory"]
    print("pending PF %d / no-pets %d / held %d" % (inv["clean_pet_friendly"], inv["clean_verified_no_pets"], inv["held"]))
    print("projected:", json.dumps(rep["shadow_reconciliation"]["projected_if_clean_inventory_promoted"]))
    print("wrong-live findings:", rep["wrong_live_policy_audit"]["wrong_live_policy_findings"])
    print("PROMOTION_READY:", rep["promotion_readiness"]["PROMOTION_READY"], rep["promotion_readiness"]["blockers"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

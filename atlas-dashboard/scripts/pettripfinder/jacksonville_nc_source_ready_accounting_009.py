"""PTF-JACKSONVILLE-NC-PARALLEL-SOURCE-READY-001 -- Phase 10: complete accounting.

Every discovered candidate, every census identity in exactly one disposition, every
hold by class, and per-corridor coverage, computed from the committed market-local
documents -- never typed. Also records the shadow package's identity, its
independent reproduction and the release stop.

Output:
  launch_packages/pettripfinder/markets/reports/jacksonville_nc_source_ready_accounting_009.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-JACKSONVILLE-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "jacksonville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "jacksonville_nc_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
TIMINGS = OrderedDict([
    ("JACKSONVILLE_START_TIMESTAMP", "2026-09-13T14:45:18Z"),
    ("geography_written", "2026-09-13T14:52:20Z"),
    ("osm_lane_seconds", 397.0),
    ("brand_lane_free_requests", 88),
    ("attended_and_static_reads", "2026-09-13T14:55Z-15:15Z"),
    ("source_ready_inputs_committed", "2026-09-13T15:28:16Z (3a2d5bd0; LF writer fix 1f0ce641 at 15:29:00Z)"),
    ("shadow_package_sealed_and_fast", "2026-09-13T15:29:06Z-15:29:35Z"),
    ("independent_reproduction", "2026-09-13T15:30Z (clean worktree at 1f0ce641: digest-only seal, then the full derived chain rebuilt from the raw captures -- zero content diff, same digest)"),
    ("ZERO_TO_SOURCE_READY", "44 min 17 s (14:45:18Z -> 15:29:35Z, FAST-passed sealed shadow package)"),
])


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "jacksonville_nc_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "jacksonville_nc_geography_001.json"))
    osm = _load(os.path.join(REPORTS, "jacksonville_nc_osm_lane_001.json"))
    capture = _load(os.path.join(REPORTS, "jacksonville_nc_attended_capture_001.json"))
    shadow = _load(os.path.join(REPORTS, "jacksonville_nc_shadow_package_008.json"))

    hotels = census["hotels"]
    non_admitted = census["non_admitted"]
    states = Counter(i["final_state"] for i in partition["items"])
    by_state = {}
    for i in partition["items"]:
        by_state.setdefault(i["final_state"], []).append(i["canonical_name"])

    def names(klass, prefix=None):
        return [r["canonical_name"] for r in non_admitted if r["classification"] == klass
                and (prefix is None or (r.get("classification_reason") or "").startswith(prefix))]

    geography_holds = names("IDENTITY_REVIEW_REQUIRED", "GEOGRAPHY_HOLD")
    identity_review = [n for n in names("IDENTITY_REVIEW_REQUIRED") if n not in geography_holds]
    holds = OrderedDict([
        ("IDENTITY_HOLDS", OrderedDict([
            ("count", len(identity_review) + len(names("NAME_ONLY_UNRESOLVED")) + len(names("SAME_IDENTITY_REBRAND_SUCCESSOR"))),
            ("identity_review_required", identity_review),
            ("name_only_unresolved", names("NAME_ONLY_UNRESOLVED")),
            ("rebrand_unresolved", names("SAME_IDENTITY_REBRAND_SUCCESSOR")),
            ("note", "Not census identities: none is registered, none publishes. The two rebrand holds need one "
                     "first-party page stating the current flag (Choice / G6 refused this client), not a founder ruling.")])),
        ("ROUTING_HOLDS", OrderedDict([("count", states.get("AWAITING_OFFICIAL_URL", 0)),
                                       ("identities", by_state.get("AWAITING_OFFICIAL_URL", []))])),
        ("ACCESS_BLOCKED", OrderedDict([("count", states.get("ACCESS_BLOCKED", 0)),
                                        ("identities", by_state.get("ACCESS_BLOCKED", []))])),
        ("EVIDENCE_HOLDS", OrderedDict([("count", states.get("AWAITING_POLICY_OBSERVATION", 0)),
                                        ("identities", by_state.get("AWAITING_POLICY_OBSERVATION", []))])),
        ("GEOGRAPHY_HOLDS", OrderedDict([("count", len(geography_holds)), ("identities", geography_holds)])),
        ("PAID_HOLDS", OrderedDict([("count", 0), ("note", "No paid lane was used or reserved; the six ACCESS_BLOCKED "
                                                            "identities are the paid-lane candidates for a later order under a founder budget.")])),
        ("FOUNDER_HOLDS", OrderedDict([("count", 0), ("note", "No row requires a founder ruling.")])),
    ])

    pf = {i["identity_key"] for i in partition["items"] if i["final_state"] == "PUBLISHED_PET_FRIENDLY"}
    np_ = {i["identity_key"] for i in partition["items"] if i["final_state"] == "VERIFIED_NO_PETS"}
    minimum = {c["corridor_id"]: c.get("minimum_hotel_count", 5)
               for c in _load(os.path.join(PKG, "markets", "proposed", "%s.json" % MARKET_ID))["corridors"]}
    klass = {c["corridor_id"]: c["geography_class"] for c in geography["corridors"]}
    coverage = []
    for c in geography["corridors"]:
        cid = c["corridor_id"]
        rows = [h for h in hotels if h.get("corridor") == cid]
        n_pf = sum(1 for h in rows if h["identity_key"] in pf)
        n_np = sum(1 for h in rows if h["identity_key"] in np_)
        coverage.append(OrderedDict([
            ("corridor_id", cid), ("geography_class", klass[cid]), ("postal_codes", c["included_postal_codes"]),
            ("census", len(rows)), ("pet_friendly", n_pf), ("verified_no_pets", n_np),
            ("unresolved", len(rows) - n_pf - n_np),
            ("corridor_page_publishes", n_pf >= minimum.get(cid, 5)),
        ]))

    unnamed_map = sum(1 for e in osm["elements"] if not (e.get("tags") or {}).get("name"))
    doc = OrderedDict([
        ("schema", "ptf-market-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("display_market", "Jacksonville, North Carolina"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane (map, owned brand "
             "harvest, brand city pages and sitemaps, county tourism roster, competitor leads, first-party reads). "
             "Not counted: %d unnamed map elements (a map element with no name is not an identity) and three "
             "retired Wyndham routes (Super 8, Travelodge, Baymont) that redirect to the brand's search." % unnamed_map),
            ("classification_counts", census["classification_counts"]),
            ("REGISTERED_CENSUS", census["count"]),
            ("registered_census_note", "The proposed census the registration order will register; nothing is registered by this order."),
            ("PET_FRIENDLY", states.get("PUBLISHED_PET_FRIENDLY", 0)),
            ("VERIFIED_NO_PETS", states.get("VERIFIED_NO_PETS", 0)),
            ("RESOLVED", partition["resolved"]), ("UNRESOLVED", partition["unresolved"]),
            ("partition_counts_by_state", OrderedDict(sorted(states.items()))),
            ("every_census_identity_has_exactly_one_disposition",
             len(partition["items"]) == census["count"]
             and len({i["identity_key"] for i in partition["items"]}) == census["count"]),
            ("outside_market_refused", len(names("OUTSIDE_MARKET"))),
            ("military_government_nonpublic_refused",
             [r["canonical_name"] for r in non_admitted if "MILITARY_GOVERNMENT_NONPUBLIC" in (r.get("classification_reason") or "")]),
        ])),
        ("holds_by_class", holds),
        ("corridor_coverage", coverage),
        ("first_party_reads", capture["counts"]),
        ("package", OrderedDict([
            ("PACKAGE_CREATED", "YES"), ("execution_zone", shadow["execution_zone"]),
            ("package_id", shadow["package_id"]), ("PACKAGE_DIGEST", shadow["package_digest"]),
            ("created_from_source_sha", shadow["created_from_source_sha"]),
            ("package_path", shadow["package_path"]),
            ("BUILD_INPUT_KEY", shadow["build_input_key"]),
            ("INTENDED_DELTA", shadow["intended_delta"]),
            ("VALIDATION_RECEIPT", OrderedDict([("path", shadow["receipt_path"]), ("digest", shadow["receipt_digest"]),
                                                ("eligible", shadow["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
                                                ("rules", shadow["fast_rules"]),
                                                ("unknown", shadow["unknown_rules"]), ("failed", shadow["failed_rules"]),
                                                ("determinism", shadow["determinism_result"])])),
            ("COVERAGE_SCORECARD", shadow["coverage_scorecard"]),
            ("UNRESOLVED_SET", shadow["unresolved_set"]),
            ("HOLD_SET", shadow["hold_set_non_admitted_census_rows"]),
            ("PACKAGE_REPRODUCIBLE", "YES"),
            ("reproduction",
             "Sealed twice in-process (equal digests); then, in a clean git worktree at the source commit, sealed "
             "again by a separate process (equal digest), and the whole derived chain -- geography, capture, census, "
             "clean set, partition, staged policy package, staged shard -- rebuilt from the raw captures with zero "
             "content difference against the commit, sealing to the same digest a third time."),
            ("parent_binding", shadow["parent_binding"]),
        ])),
        ("factory_code_changed", "NO -- every changed path is a jacksonville_nc_* helper, the market's discovery config, or a document under the market's own proposed / staging / report paths"),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only; no whole-site candidate was assembled"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the generated globals, release contracts and the market registry are unchanged"),
        ("next_order", [
            "read the Fayetteville-live parent (after Netlify is restored and Fayetteville deploys)",
            "rebase this branch on it; copy markets/proposed/jacksonville-nc.json, identity_census_proposed/jacksonville-nc.json and the staged launch_package documents into their registered paths",
            "market_registration_cli --write, build_global_authority --write/--check, release contract, registration_release_lane register + seal --work-order (a NEW package id against the new parent; this shadow package's rule N fails by design once the parent moves)",
            "regression_delta classify, compose and reproduce the candidate, prepare the founder packet, deploy only on authorization",
        ]),
    ])
    return doc


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    a = doc["accounting"]
    print({k: a[k] for k in ("TOTAL_DISCOVERED", "REGISTERED_CENSUS", "PET_FRIENDLY", "VERIFIED_NO_PETS", "RESOLVED", "UNRESOLVED")})
    print({k: v["count"] for k, v in doc["holds_by_class"].items()})
    for c in doc["corridor_coverage"]:
        print(c["corridor_id"].split("__")[1], c["geography_class"], c["census"], c["pet_friendly"], c["verified_no_pets"], c["unresolved"], c["corridor_page_publishes"])
    print(doc["package"]["PACKAGE_DIGEST"], doc["package"]["BUILD_INPUT_KEY"]["staged_input_digest"])
    print("one disposition each:", a["every_census_identity_has_exactly_one_disposition"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

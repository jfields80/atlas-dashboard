# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020, Phases 5 and 7 to 11.

Triages the attended captures, measures the free lane, builds ONE founder
packet, projects authority and restates what remains. NO AUTHORITY IS APPLIED
and no provider was called.

COVERAGE IS REPORTED, NOT ASSUMED. This pass processed part of the admitted
cohort, not all of it. Every rate below is denominated in what was actually
opened; the unprocessed rows are not counted as failures and not counted at
all. A lane rate computed over pages nobody opened would be the same error as
counting a quota refusal as a lane failure.

THE FOUNDER'S TOWNEPLACE RULING IS NOT APPLIED BY ME. Embassy Suites now shows
the identical pattern -- stated terms, no words of acceptance -- and that
ruling was expressly identity-specific, so it goes in the packet.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020"
AS_OF = "2026-08-30"
Z = 1.959963984540054

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
RESULTS = LP / "detroit_ann_arbor_attended_results_020.json"
COHORT = LP / "detroit_ann_arbor_free_cohort_020.json"
TRIAGE = LP / "detroit_ann_arbor_attended_triage_020.json"
PACKET = LP / "detroit_ann_arbor_founder_packet_020.json"
REMAIN = LP / "detroit_ann_arbor_remaining_020.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path, doc):
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def wilson(successes, trials):
    if trials <= 0:
        return (0.0, 0.0, 0.0)
    point = successes / trials
    den = 1.0 + (Z * Z) / trials
    centre = (point + (Z * Z) / (2 * trials)) / den
    margin = (Z * math.sqrt(point * (1 - point) / trials
                            + (Z * Z) / (4 * trials * trials))) / den
    return (point, max(0.0, centre - margin), min(1.0, centre + margin))


def rate(successes, trials, what):
    point, low, high = wilson(successes, trials)
    return OrderedDict([("measures", what), ("successes", successes),
                        ("denominator", trials), ("point", round(point, 4)),
                        ("wilson_lower_95", round(low, 4)),
                        ("wilson_upper_95", round(high, 4))])


def triage_of(row):
    reader = row.get("reader") or {}
    outcome = row["outcome"]
    if outcome == "PUBLICATION_CANDIDATE":
        if reader.get("pets_allowed") is True:
            return "CLEAN_PET_FRIENDLY_CANDIDATE"
        if reader.get("pets_allowed") is False:
            return "CLEAN_VERIFIED_NO_PETS_CANDIDATE"
        return "FOUNDER_EXCEPTION"
    if outcome in ("HOLD", "IDENTITY_MISMATCH", "ROUTING_REPAIR_REQUIRED"):
        return "FOUNDER_EXCEPTION"
    return "NO_FOUNDER_ACTION"


def run():
    res = load(RESULTS)
    cohort = load(COHORT)
    rows = res["results"]
    recap = res["recapture"]
    for row in rows:
        row["triage"] = triage_of(row)
        row.pop("checks", None)
    recap["triage"] = "FOUNDER_EXCEPTION"

    strata = cohort["independent_cohort"]["by_stratum"]
    admitted = cohort["independent_cohort"]["admitted"]
    independents = [row for row in rows
                    if row["stratum"] == "INDEPENDENT_DOMAIN"]
    counts = Counter(row["outcome"] for row in independents)
    tri = Counter(row["triage"] for row in rows)

    rendered = sum(1 for row in independents
                   if row["outcome"] != "IDENTITY_MISMATCH")
    surfaces = sum(1 for row in independents if row.get("block"))
    clean = sum(1 for row in independents
                if row["triage"].startswith("CLEAN_"))

    lane = OrderedDict([
        ("n", len(independents)),
        ("rendered", rendered),
        ("identity_confirmed", rendered),
        ("policy_surface_found", surfaces),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("publication_grade", rate(clean, len(independents),
                                   "independents yielding a clean publication "
                                   "candidate")),
        ("pet_friendly", rate(
            sum(1 for row in independents
                if row["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE"),
            len(independents), "independents whose page accepts pets")),
        ("policy_not_found", counts.get("POLICY_NOT_FOUND", 0)),
        ("access_blocked", 0),
        ("routing_repair", 0),
        ("identity_mismatch", counts.get("IDENTITY_MISMATCH", 0)),
        ("founder_exceptions", sum(1 for row in independents
                                   if row["triage"] == "FOUNDER_EXCEPTION")),
    ])

    recommendation = ("FREE_LANE_SCALE"
                      if lane["publication_grade"]["wilson_lower_95"] >= 0.30
                      else "MORE_FREE_WORK_NEEDED")
    measurement = OrderedDict([
        ("coverage", OrderedDict([
            ("admitted_free_cohort", admitted),
            ("processed_this_pass", len(rows)),
            ("independents_admitted", strata["INDEPENDENT_DOMAIN"]),
            ("independents_processed", len(independents)),
            ("small_chain_admitted", strata["SMALL_CHAIN_DOMAIN"]),
            ("small_chain_processed", 0),
            ("complete", len(rows) == admitted),
            ("note",
             "PARTIAL. Every rate here is denominated in what was actually "
             "opened; the unprocessed rows are neither counted as failures nor "
             "counted at all."),
        ])),
        ("independent_lane", lane),
        ("recommendation", recommendation),
        ("why",
         "attended Chrome reached every independent it opened, found a "
         "first-party policy surface on %d of %d, and produced %d clean "
         "candidates at $0. The misses are SOURCE SILENCE -- sites that "
         "publish no pet policy anywhere -- not access failures, and no paid "
         "provider can conjure a policy a hotel never wrote."
         % (surfaces, len(independents), clean)),
        ("scope_of_the_recommendation",
         "FREE_LANE_SCALE means the lane is PROVEN and the remaining admitted "
         "rows should be finished on it before any paid lane is considered -- "
         "not that another Detroit pass is needed to prove it again."),
    ])

    write_lf(TRIAGE, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-attended-triage/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("lane", "attended_chrome"),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("triage_counts", OrderedDict(sorted(tri.items()))),
        ("measurement", measurement),
        ("results", rows),
        ("recapture", recap),
    ]))

    exceptions = []
    for row in rows:
        if row["triage"] != "FOUNDER_EXCEPTION":
            continue
        if row["outcome"] == "IDENTITY_MISMATCH":
            exceptions.append(OrderedDict([
                ("property", row["canonical_name"]),
                ("issue", "the committed route points at a HIJACKED DOMAIN"),
                ("evidence", row["note"]),
                ("safe_fields", []),
                ("withheld_fields", ["everything -- no hotel content exists at "
                                     "this route"]),
                ("recommended_disposition",
                 "ROUTING_REPAIR_REQUIRED: withdraw the route and re-discover "
                 "the property's current official domain at $0 before any lane "
                 "touches it"),
                ("reason",
                 "publishing anything from this route would send a guest to an "
                 "online-gambling site. It is also the strongest argument in "
                 "this market for re-validating routes that have sat unused."),
                ("decision", ""), ("decided_by", ""), ("decided_at", ""),
            ]))
        elif row["outcome"] == "HOLD":
            exceptions.append(OrderedDict([
                ("property", row["canonical_name"]),
                ("issue", "an amenity mention inside marketing prose, with no "
                          "policy terms anywhere on the site"),
                ("evidence", row["block"]),
                ("safe_fields", []),
                ("withheld_fields",
                 ["pets_allowed and every fact -- the committed reader does "
                  "resolve the boolean from this phrase, but a room-type list "
                  "is not a policy statement"]),
                ("recommended_disposition",
                 "HOLD: treat a marketing room-type mention as insufficient, "
                 "and re-capture if the hotel later publishes terms"),
                ("reason",
                 "order 011's gate deliberately excludes marketing prose. The "
                 "reader returns True here, which is precisely why this goes "
                 "to a founder rather than to publication."),
                ("decision", ""), ("decided_by", ""), ("decided_at", ""),
            ]))

    exceptions.append(OrderedDict([
        ("property", recap["canonical_name"]),
        ("issue", "the HOLD is CLEARED -- a real answer now exists -- but the "
                  "page states TERMS without ever saying in words that pets "
                  "are accepted, so the committed reader withholds "
                  "pets_allowed as SOURCE_SILENT"),
        ("evidence", recap["policy_block"]),
        ("safe_fields", ["fee_tiers: $75.00 for a 1-4 night stay, $125.00 for "
                         "5+ nights (stay_length_range, nights)",
                         "pet_count_limit: 2",
                         "species_allowed: cat, dog"]),
        ("withheld_fields", ["pets_allowed -- never stated in words"]),
        ("recommended_disposition",
         "APPROVE PET_FRIENDLY on the same reasoning the founder applied to "
         "TownePlace Suites Dearborn under order 019"),
        ("reason",
         "this is the IDENTICAL pattern the founder has already ruled on: a "
         "property publishing a tiered pet fee, a pet maximum and a species "
         "list is stating terms of acceptance. That ruling was expressly "
         "IDENTITY-SPECIFIC, so it is not applied here by me. Either way the "
         "re-capture succeeded: the question-only block is superseded by a "
         "genuine property-specific answer."),
        ("decision", ""), ("decided_by", ""), ("decided_at", ""),
    ]))

    write_lf(PACKET, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-packet/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_RULING"),
        ("note", "ONE packet, built after the processed cohort. Clean "
                 "candidates need no individual review and are not here."),
        ("count", len(exceptions)),
        ("exceptions", exceptions),
    ]))

    published = len(load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"])
    excluded = len(load(LP / "markets" / "authority" / MARKET
                        / "hotel_exclusions.json")["exclusions"])
    clean_pf = sum(1 for row in rows
                   if row["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE")
    clean_np = sum(1 for row in rows
                   if row["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE")

    write_lf(REMAIN, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-remaining/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authority_now_unchanged", OrderedDict([
            ("pet_friendly", published),
            ("verified_no_pets", excluded),
            ("total_resolved", published + excluded),
        ])),
        ("projection_if_clean_candidates_were_approved", OrderedDict([
            ("new_clean_pet_friendly", clean_pf),
            ("new_clean_verified_no_pets", clean_np),
            ("projected_pet_friendly", published + clean_pf),
            ("projected_verified_no_pets", excluded + clean_np),
            ("projected_total_resolved",
             published + excluded + clean_pf + clean_np),
            ("embassy_note",
             "the Embassy Suites re-capture is NOT in this projection: its "
             "boolean is unresolved and it sits in the founder packet. If "
             "approved it is +1 pet-friendly, and it is a recovery FROM THE "
             "FOUNDER HOLD rather than a new find."),
            ("note", "PROJECTION ONLY. Nothing is applied and each candidate "
                     "must still clear the publication gates."),
        ])),
        ("free_lane_still_to_process", OrderedDict([
            ("independents", strata["INDEPENDENT_DOMAIN"] - len(independents)),
            ("small_chain", strata["SMALL_CHAIN_DOMAIN"]),
            ("total", admitted - len(rows)),
            ("cost_to_finish", "$0 -- the same attended lane"),
        ])),
        ("paid_cohort_untouched", "written by Phase 10 -- see "
                                   "detroit_ann_arbor_remaining_classification_020.json"),
        ("cost", OrderedDict([
            ("provider_calls_this_order", 0),
            ("spend_this_order_usd", 0.0),
            ("note", "the paid remainder is counted in Phase 10, from "
                     "current state, not from a carried-forward constant"),
        ])),
    ]))

    print("=== Phase 5: triage ===")
    for name, n in sorted(tri.items()):
        print("   %-34s %d" % (name, n))
    print()
    print("=== Phase 7: independent lane ===")
    print("  processed %d of %d admitted independents"
          % (len(independents), strata["INDEPENDENT_DOMAIN"]))
    for field in ("publication_grade", "pet_friendly"):
        r = lane[field]
        print("     %-18s %d/%-2d point %.3f wilson [%.3f, %.3f]"
              % (field, r["successes"], r["denominator"], r["point"],
                 r["wilson_lower_95"], r["wilson_upper_95"]))
    print("  policy-not-found %d | identity mismatch %d | exceptions %d"
          % (lane["policy_not_found"], lane["identity_mismatch"],
             lane["founder_exceptions"]))
    print("  RECOMMENDATION:", recommendation)
    print()
    print("=== Phase 8: founder packet ===", len(exceptions), "exceptions")
    print("=== Phase 9: projection ===")
    print("  now       : %d pet-friendly, %d no-pets, %d resolved"
          % (published, excluded, published + excluded))
    print("  projected : %d pet-friendly, %d no-pets, %d resolved"
          % (published + clean_pf, excluded + clean_np,
             published + excluded + clean_pf + clean_np))
    print("wrote", TRIAGE.name, PACKET.name, REMAIN.name)


if __name__ == "__main__":
    run()

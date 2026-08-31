# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020-COMPLETION, Phases 6 to 10.

Closes Pass 020 over the WHOLE admitted cohort. Order 020 admitted 45 rows and
processed 12; the completion order processed the exact remaining 33 -- no
substitutions, no new identities, and none of the first 12 revisited -- so
every rate below is finally denominated in the cohort that was admitted rather
than in the part of it somebody got to.

WHY THIS IS A NEW FILE. ``detroit_ann_arbor_attended_close_020.py`` is the
record of what the partial pass computed and what it honestly said about its
own coverage. Rewriting it would erase that. This module supersedes it for the
completed cohort and leaves it standing.

THE STRATA ARE NOT BLENDED. Independents and small-chain domains are different
lanes with different failure modes, and order 020 measured only the first. They
are reported separately and combined only after.

NO AUTHORITY IS APPLIED. The three founder rulings the completion order carried
in are recorded as PENDING APPLICATION DISPOSITIONS -- a ruling is not a write.
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
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020-COMPLETION"
PARENT_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020"
AS_OF = "2026-08-30"
Z = 1.959963984540054

#: Authority is COUNTED FROM THE COMMITTED FILES, never carried in as a
#: constant. The completion order was written against 85/72/157, and by the
#: time it ran commit f5828db had already applied the Kensington and Embassy
#: rulings, taking the market to 87/72/159. A projection built on the order's
#: prose would have added those two hotels a second time.

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
RESULTS = LP / "detroit_ann_arbor_attended_results_020.json"
COHORT = LP / "detroit_ann_arbor_free_cohort_020.json"
TRIAGE = LP / "detroit_ann_arbor_attended_triage_020.json"
PACKET = LP / "detroit_ann_arbor_founder_packet_020.json"
REMAIN = LP / "detroit_ann_arbor_remaining_020.json"
INVENTORY = LP / "detroit_ann_arbor_application_inventory_020.json"

#: The rulings the completion order supplied by name. They are carried, not
#: re-asked, and they are dispositions PENDING APPLICATION -- nothing here
#: writes authority.
FOUNDER_RULINGS = {
    "the kensington hotel ann arbor": "APPROVE_PARTIAL",
    "roberts riverwalk hotel": "ROUTING_REPAIR_REQUIRED",
    "embassy suites by hilton detroit livonia novi":
        "APPROVE_PET_FRIENDLY_IDENTITY_SPECIFIC",
}

#: What the packet recommends for each still-open exception, and why. Written
#: here rather than derived, so the recommendation is a sentence a person can
#: argue with rather than a label a function produced.
RECOMMENDATIONS = {
    "hyatt place detroit livonia": (
        "HOLD -- do not publish; the page must be corrected at source",
        "the route, the schema.org payload and all three census signals say "
        "Livonia, but the only pet block on the page says 'Hyatt Place Detroit "
        "/ Auburn Hills is pet-friendly!'. Publishing it would bind the sister "
        "hotel's terms to this building. Nothing else on the surface states "
        "this property's own policy."),
    "the bell tower hotel": (
        "RULE ON THE SEMANTICS -- is 'we only allow service animals' a refusal?",
        "the property answers its own question 'Are pets allowed?' with an "
        "exclusive permission over a category that is definitionally not a "
        "pet. Reading that as VERIFIED_NO_PETS is defensible and is also an "
        "inference: policy_reading records a service_animal_exception quote "
        "and derives no pets_allowed value from it. A ruling here sets the "
        "precedent for every 'service animals only' surface in every market."),
    "radisson hotel detroit farmington hills": (
        "ROUTING_REPAIR_REQUIRED -- withdraw the route and re-discover at $0",
        "the committed route 302s to the Radisson brand index and the "
        "destination page 404s. Radisson Americas properties have been "
        "migrating to Choice-managed domains, so the property very likely "
        "still exists at a new first-party URL. No lane should touch it until "
        "the route is repaired."),
    "drury inn and suites": (
        "ROUTING_REPAIR_REQUIRED -- withdraw the route and re-discover at $0",
        "the committed route is a legacy host (wwws.druryhotels.com) that "
        "fails at the network layer, and the current property slug cannot be "
        "derived because the census canonical_name is the bare chain word "
        "'Drury Inn & Suites' with no city. druryhotels.com itself serves "
        "normally, so this is a slug to find, not a wall to buy through."),
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def authority_now():
    """Count the market's authority from the committed files, right now."""
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    return published, excluded


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
    """Unchanged from the partial close: the same rule over more rows."""
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


def stratum_block(rows, name):
    counts = Counter(row["outcome"] for row in rows)
    reached = [r for r in rows if r["outcome"] not in
               ("IDENTITY_MISMATCH", "ROUTING_REPAIR_REQUIRED")]
    surfaces = sum(1 for r in rows if r.get("block"))
    clean_pf = sum(1 for r in rows
                   if r["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE")
    clean_np = sum(1 for r in rows
                   if r["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE")
    n = len(rows)
    return OrderedDict([
        ("stratum", name),
        ("n", n),
        ("rendered", len(reached)),
        ("identity_confirmed", len(reached)),
        ("policy_surface_found", surfaces),
        ("outcome_counts", OrderedDict(sorted(counts.items()))),
        ("publication_grade", rate(clean_pf + clean_np, n,
                                   "rows yielding a clean publication "
                                   "candidate in either direction")),
        ("pet_friendly", rate(clean_pf, n, "rows whose page accepts pets")),
        ("verified_no_pets", rate(clean_np, n,
                                  "rows whose page refuses pets in its own "
                                  "words")),
        ("policy_not_found", counts.get("POLICY_NOT_FOUND", 0)),
        ("access_blocked", counts.get("ACCESS_BLOCKED", 0)),
        ("routing_repair", counts.get("ROUTING_REPAIR_REQUIRED", 0)),
        ("identity_mismatch", counts.get("IDENTITY_MISMATCH", 0)),
        ("founder_exceptions", sum(1 for r in rows
                                   if r["triage"] == "FOUNDER_EXCEPTION")),
    ])


def exception_entry(row):
    """One consolidated packet line. Decision fields stay empty."""
    reader = row.get("reader") or {}
    withheld = reader.get("withheld") or {}
    facts = reader.get("facts") or {}
    return OrderedDict([
        ("property", row["canonical_name"]),
        ("identity_key", row["identity_key"]),
        ("stratum", row.get("stratum", "")),
        ("issue", row.get("issue") or row.get("note", "")),
        ("evidence", row.get("block", "")),
        ("evidence_artifact", row.get("block_artifact", "")),
        ("evidence_sha256", row.get("block_sha256", "")),
        ("safe_fields", sorted(facts)),
        ("withheld_fields", withheld),
        ("recommended_disposition", row.get("recommended_disposition", "")),
        ("reason", row.get("recommendation_reason", "")),
        ("founder_ruling_already_given",
         FOUNDER_RULINGS.get(row["identity_key"], "")),
        ("decision", ""), ("decided_by", ""), ("decided_at", ""),
    ])


def close_triage():
    res = load(RESULTS)
    cohort = load(COHORT)
    rows = res["results"]
    recap = res["recapture"]

    admitted = [r["identity_key"] for r in cohort["admitted_rows"]]
    keys = [r["identity_key"] for r in rows]
    assert len(rows) == len(admitted) == 45, (len(rows), len(admitted))
    assert len(set(keys)) == 45, "duplicate identity in the cohort"
    assert set(keys) == set(admitted), "processed set is not the admitted set"
    assert recap["identity_key"] not in set(admitted), (
        "the Embassy re-capture must stay outside the 45-row denominator")

    for row in rows:
        row["triage"] = triage_of(row)
        row.pop("checks", None)
    recap["triage"] = "FOUNDER_EXCEPTION"

    independents = [r for r in rows if r["stratum"] == "INDEPENDENT_DOMAIN"]
    small_chain = [r for r in rows if r["stratum"] == "SMALL_CHAIN_DOMAIN"]
    tri = Counter(row["triage"] for row in rows)

    clean_pf = sum(1 for r in rows if r["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE")
    clean_np = sum(1 for r in rows if r["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE")
    reached = sum(1 for r in rows if r["outcome"] not in
                  ("IDENTITY_MISMATCH", "ROUTING_REPAIR_REQUIRED"))
    silent = sum(1 for r in rows if r["outcome"] == "POLICY_NOT_FOUND")

    combined = OrderedDict([
        ("n", len(rows)),
        ("rendered", reached),
        ("publication_grade", rate(clean_pf + clean_np, len(rows),
                                   "the completed 45-row cohort yielding a "
                                   "clean publication candidate")),
        ("pet_friendly", rate(clean_pf, len(rows), "cohort rows accepting pets")),
        ("verified_no_pets", rate(clean_np, len(rows),
                                  "cohort rows refusing pets in their own words")),
    ])

    measurement = OrderedDict([
        ("coverage", OrderedDict([
            ("admitted_free_cohort", len(admitted)),
            ("processed_by_order_020", sum(1 for r in rows if r.get("batch") == 1)),
            ("processed_by_this_completion",
             sum(1 for r in rows if r.get("batch") == 2)),
            ("processed_total", len(rows)),
            ("missing", 0), ("duplicates", 0), ("complete", True),
            ("note", "COMPLETE. Every rate below is denominated in the cohort "
                     "that was admitted, not in the part of it that had been "
                     "opened when the partial pass stopped."),
        ])),
        ("independent_lane", stratum_block(independents, "INDEPENDENT_DOMAIN")),
        ("small_chain_lane", stratum_block(small_chain, "SMALL_CHAIN_DOMAIN")),
        ("combined", combined),
        ("lane_status", "FREE_LANE_QUALIFIED_AND_COMPLETE"),
        ("what_that_means",
         "the free attended lane is not on trial any more. It opened %d of %d "
         "admitted rows, produced %d clean publication candidates at $0, and "
         "the only rows it could not answer are two dead routes and %d sites "
         "that publish no pet policy at all. No further generic free-lane "
         "probe should be commissioned for this market."
         % (reached, len(rows), clean_pf + clean_np, silent)),
        ("why_the_strata_are_not_blended",
         "the small-chain lane was entirely unmeasured when order 020 stopped, "
         "so a combined figure quoted then would have been an independent-only "
         "figure wearing a cohort-wide label."),
    ])

    write_lf(TRIAGE, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-attended-triage/1.1"),
        ("work_order", WORK_ORDER),
        ("supersedes_partial_close_of", PARENT_ORDER),
        ("market_id", MARKET), ("as_of", AS_OF),
        ("lane", "attended_chrome"),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("triage_counts", OrderedDict(sorted(tri.items()))),
        ("measurement", measurement),
        ("results", rows),
        ("recapture", recap),
    ]))
    return rows, recap, tri


def build_packet(rows, recap):
    exceptions = []
    for row in rows:
        if row["triage"] != "FOUNDER_EXCEPTION":
            continue
        rec = RECOMMENDATIONS.get(row["identity_key"])
        if rec:
            row["recommended_disposition"], row["recommendation_reason"] = rec
        elif row["identity_key"] in FOUNDER_RULINGS:
            row["recommended_disposition"] = "%s (founder has ruled)" % \
                FOUNDER_RULINGS[row["identity_key"]]
            row["recommendation_reason"] = (
                "carried from the completion order; not re-asked")
        exceptions.append(exception_entry(row))

    recap = dict(recap)
    recap["recommended_disposition"] = (
        "APPROVE_PET_FRIENDLY, identity-specific (founder has ruled)")
    recap["recommendation_reason"] = (
        "carried from the completion order; not re-asked. Counted in the "
        "application inventory and NOT in the 45-row lane measurement.")
    exceptions.append(exception_entry(recap))

    ruled = [e for e in exceptions if e["founder_ruling_already_given"]]
    open_ = [e for e in exceptions if not e["founder_ruling_already_given"]]
    write_lf(PACKET, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-packet/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_RULING"),
        ("note", "ONE consolidated packet over the whole 45-row cohort plus "
                 "the Embassy re-capture. Clean candidates need no individual "
                 "review and are not here. The three rulings the completion "
                 "order supplied are recorded, not re-asked."),
        ("count", len(exceptions)),
        ("already_ruled", len(ruled)),
        ("awaiting_ruling", len(open_)),
        ("exceptions", exceptions),
    ]))
    return exceptions, ruled, open_


def build_inventory(rows, recap, exceptions, published, excluded):
    def bucket(name, items, why):
        return OrderedDict([("bucket", name), ("count", len(items)),
                            ("why", why), ("identities", items)])

    clean_pf = [r["identity_key"] for r in rows
                if r["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE"]
    clean_np = [r["identity_key"] for r in rows
                if r["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE"]
    approved_pf = ["the kensington hotel ann arbor", recap["identity_key"]]
    approved_np = []

    # NO ROW MAY BE PROPOSED THAT AUTHORITY ALREADY HOLDS.
    already = sorted((set(clean_pf) | set(clean_np)) & (published | excluded))
    assert not already, (
        "these rows are already authority and must not be applied again: %s"
        % already)
    approved_already_applied = [k for k in approved_pf
                                if k in published or k in excluded]
    repairs = [r["identity_key"] for r in rows
               if r["outcome"] in ("ROUTING_REPAIR_REQUIRED", "IDENTITY_MISMATCH")]
    open_exc = [e["identity_key"] for e in exceptions
                if not e["founder_ruling_already_given"]
                and e["identity_key"] not in repairs]
    no_action = [r["identity_key"] for r in rows
                 if r["triage"] == "NO_FOUNDER_ACTION"]

    every = clean_pf + clean_np + approved_pf + approved_np + repairs + \
        open_exc + no_action
    dupes = [k for k, n in Counter(every).items() if n > 1]
    assert not dupes, "an identity appears in two application buckets: %s" % dupes
    assert not (set(clean_pf) | set(clean_np)) & set(open_exc), \
        "clean and exception buckets overlap"
    assert len(set(every)) == 46, (
        "the inventory must cover the 45 cohort rows plus Embassy exactly once, "
        "got %d" % len(set(every)))

    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-application-inventory/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "PREPARED_NOT_APPLIED"),
        ("nothing_here_is_applied",
         "This document is a plan. It writes no policy fact, no exclusion, no "
         "route and no launch status, and it is not a founder approval."),
        ("one_verdict_per_identity", True),
        ("duplicate_identities", 0),
        ("already_authority_not_proposed_again", approved_already_applied),
        ("no_already_authority_row_is_treated_as_new", True),
        ("buckets", [
            bucket("CLEAN_PET_FRIENDLY", clean_pf,
                   "first-party allowance, identity corroborated, no founder "
                   "question outstanding"),
            bucket("CLEAN_VERIFIED_NO_PETS", clean_np,
                   "affirmative first-party refusal in the property's own "
                   "words -- never silence"),
            bucket("FOUNDER_APPROVED_PET_FRIENDLY", approved_pf,
                   "the founder has already ruled AND commit f5828db has "
                   "already applied both -- they are live authority now, so "
                   "they are listed for completeness and contribute NOTHING "
                   "to the projection. Embassy's ruling is identity-specific "
                   "and may not be widened to any other row."),
            bucket("FOUNDER_APPROVED_NO_PETS", approved_np, "none"),
            bucket("FOUNDER_EXCEPTION", open_exc,
                   "genuinely open questions, each with its evidence in the "
                   "packet and its decision fields empty"),
            bucket("ROUTING_REPAIR_REQUIRED", repairs,
                   "no property surface was reached; the repair is free and "
                   "must precede any lane"),
            bucket("NO_AUTHORITY_ACTION", no_action,
                   "reached and swept at $0 and the site publishes no pet "
                   "policy. SOURCE SILENCE IS ABSENCE."),
        ]),
        ("embassy_note",
         "the Embassy Suites re-capture is included HERE because it is real "
         "authority work, and excluded from the 45-row lane measurement "
         "because it was never in the admitted cohort. Both statements are "
         "true at once and neither is a double count."),
    ])
    write_lf(INVENTORY, doc)
    return (clean_pf, clean_np, approved_pf, repairs, open_exc, no_action,
            approved_already_applied)


def build_remaining(clean_pf, clean_np, approved_pf, repairs, open_exc,
                    approved_already_applied, published, excluded):
    pf_now, np_now = len(published), len(excluded)
    resolved_now = pf_now + np_now
    # The founder-approved pair is already live authority, so it adds nothing.
    new_pf = len(clean_pf) + (len(approved_pf) - len(approved_already_applied))
    new_np = len(clean_np)
    key = "projection_if_every_clean_candidate_passes_the_publication_gates"
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-remaining/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authority_now_unchanged", OrderedDict([
            ("pet_friendly", pf_now),
            ("verified_no_pets", np_now),
            ("total_resolved", resolved_now),
            ("counted_from", "the committed policy package and exclusion "
                             "registry, at run time"),
            ("the_order_said", OrderedDict([
                ("pet_friendly", 85), ("verified_no_pets", 72),
                ("total_resolved", 157),
                ("why_it_differs",
                 "commit f5828db applied the Kensington and Embassy founder "
                 "rulings after the completion order was written. Both hotels "
                 "are live authority now. Projecting from the order's prose "
                 "would have counted them twice."),
            ])),
        ])),
        (key, OrderedDict([
            ("new_clean_pet_friendly", len(clean_pf)),
            ("founder_approved_pet_friendly_already_applied",
             approved_already_applied),
            ("new_clean_verified_no_pets", new_np),
            ("projected_pet_friendly", pf_now + new_pf),
            ("projected_verified_no_pets", np_now + new_np),
            ("projected_total_resolved", resolved_now + new_pf + new_np),
            ("deliberately_not_counted", OrderedDict([
                ("roberts_riverwalk", "ruled ROUTING_REPAIR_REQUIRED; it "
                                      "resolves nothing until the route is "
                                      "repaired"),
                ("open_founder_exceptions", open_exc),
                ("routing_repairs", repairs),
                ("source_silent_rows", "a site that publishes no pet policy "
                                       "resolves to UNKNOWN, never to a "
                                       "refusal"),
            ])),
            ("note", "PROJECTION ONLY. Nothing is applied and every candidate "
                     "must still clear the publication gates."),
        ])),
        ("free_lane_still_to_process", OrderedDict([
            ("independents", 0), ("small_chain", 0), ("total", 0),
            ("note", "the admitted free cohort is finished, 45 of 45."),
        ])),
        ("paid_cohort_untouched",
         "rebuilt from current state in "
         "detroit_ann_arbor_remaining_classification_020.json"),
        ("cost", OrderedDict([
            ("provider_calls_this_order", 0),
            ("spend_this_order_usd", 0.0),
            ("note", "33 properties opened on attended Chrome; no paid "
                     "provider was called and no balance moved."),
        ])),
    ])
    write_lf(REMAIN, doc)
    return doc, key


def main():
    published, excluded = authority_now()
    rows, recap, tri = close_triage()
    exceptions, ruled, open_ = build_packet(rows, recap)
    (clean_pf, clean_np, approved_pf, repairs, open_exc, no_action,
     already) = build_inventory(rows, recap, exceptions, published, excluded)
    remaining, key = build_remaining(clean_pf, clean_np, approved_pf, repairs,
                                     open_exc, already, published, excluded)
    print("cohort 45/45, duplicates 0")
    print("triage:", dict(sorted(tri.items())))
    print("packet: %d exceptions (%d already ruled, %d open)"
          % (len(exceptions), len(ruled), len(open_)))
    print("inventory: clean_pf=%d clean_np=%d approved_pf=%d (already applied "
          "%d) repairs=%d open_exceptions=%d no_action=%d"
          % (len(clean_pf), len(clean_np), len(approved_pf), len(already),
             len(repairs), len(open_exc), len(no_action)))
    auth = remaining["authority_now_unchanged"]
    proj = remaining[key]
    print("authority counted from the files: pf %d | no-pets %d | resolved %d "
          "(the order said 85/72/157)"
          % (auth["pet_friendly"], auth["verified_no_pets"],
             auth["total_resolved"]))
    print("projection: pf %d -> %d | no-pets %d -> %d | resolved %d -> %d"
          % (auth["pet_friendly"], proj["projected_pet_friendly"],
             auth["verified_no_pets"], proj["projected_verified_no_pets"],
             auth["total_resolved"], proj["projected_total_resolved"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

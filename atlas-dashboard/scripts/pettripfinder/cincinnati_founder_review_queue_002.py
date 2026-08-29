"""PTF-CINCINNATI-HARDENED-SYNC-002 Phase 7 -- rebuild the founder-review queue.

    python -m scripts.pettripfinder.cincinnati_founder_review_queue_002
    python -m scripts.pettripfinder.cincinnati_founder_review_queue_002 --write

WHY THE COMMITTED QUEUE HAD TO GO
----------------------------------
``cincinnati-oh_founder_review_queue.json`` was generated on 2026-08-16 by
PTF-CINCINNATI-CENSUS-RECONCILIATION-001 and never regenerated. On the day
after it was written, PTF-CINCINNATI-URL-ROUTING-RECOVERY-001C bound 210
official property URLs, and Capture Pass 1 resolved 27 identities. The
committed queue knows about neither: it grades 238 of its 250 rows
``MISSING_URL`` and marks every row ``NOT_STARTED``, including the twenty-one
that are published on the live site.

A worklist that says a routed row has no URL sends someone to re-find a URL
this market already owns. That is the specific failure this rebuild exists to
end, and ``test_no_routed_identity_is_reported_as_missing_a_url`` pins it.

WHAT IS NOT INFERRED
--------------------
The 121-row queue that preceded the 250-row one is not consulted, and no review
history is reconstructed from it. It carried no field capable of recording a
review outcome, so nothing in it was ever a review; the reconciliation work
order says so in its own note. Historical prose about "progress through row 73"
describes work against that document and is not evidence that any row was
decided. Only artifacts that can carry a decision are read:

    the final partition          what state each identity is actually in
    the three decision batches   the founder's 27 Capture Pass 1 rulings
    the 21c founder review       the 21st ruling, made after its recapture
    the policy package           what is published, and under whose approval
    the exclusion registry       what is refused, and what left the category
    the routing shard            which identities have a verified URL
    the Pass 1 results           the three rows that reached no disposition

DISTINCTIONS THE REBUILD IS REQUIRED TO KEEP
---------------------------------------------
* POLICY_NOT_FOUND is not a missing URL and not a refusal. The page served and
  was silent. Chester Inn & Suites is the one clean case.
* A pre-opening property is not closed, not unresolved-for-want-of-a-page, and
  must never be read as no-pets. Three Cincinnati identities are buildings that
  do not yet operate, and there is still no canonical
  ``AWAITING_PROPERTY_OPENING`` state for them -- Batch A put that on the
  backlog and it is still there, so the queue reports the hold rather than
  inventing the state.
* An access-blocked page is a fact about a server, not about a hotel.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

WORK_ORDER = "PTF-CINCINNATI-HARDENED-SYNC-002"
MARKET_ID = "cincinnati-oh"
AS_OF = "2026-08-29"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
AUTH = PKG / "markets" / "authority" / MARKET_ID
OUT = REPORTS / "cincinnati-oh_founder_review_queue.json"

#: Identities whose own page says the building is not open yet. Each is
#: recorded here with the artifact that established it, because the rebuild
#: must not re-derive an operating status from prose on every run.
PRE_OPENING = {
    "cincinnati s fidelity hotel": (
        "Its own page is titled 'Fidelity Hotel Cincinnati | Opening Summer "
        "2026'. Founder direction HOLD_PREOPENING, recorded in "
        "cincinnati_capture_pass1_founder_decisions_batchA.json."),
    "marriott cincinnati downtown": (
        "A $540M project at 5th & Plum, groundbreaking July 2026, planned "
        "opening late 2028/early 2029; no marriott.com property page exists "
        "yet. Recorded in cincinnati_url_routing_recovery_001_results.json."),
    "hyatt house cincinnati north": (
        "A stalled construction project at Cox Road and Liberty Way, halted "
        "2021 and refinanced 2024, not open for bookings; no hyatt.com "
        "property page exists. Recorded in "
        "cincinnati_url_routing_recovery_001_results.json."),
}

#: The one row whose page was unreachable for a reason on the server's side.
ACCESS_BLOCKED = "budget host town center motel"

LANES = OrderedDict((
    ("RESOLVED_PUBLISHED", "Published pet-friendly. No action."),
    ("RESOLVED_NO_PETS", "Verified no-pets, in the exclusion registry. "
                         "No action."),
    ("RESOLVED_OUT_OF_CATEGORY", "Not lodging in the current category. "
                                 "No action."),
    ("HOLD_PRE_OPENING", "The property does not operate yet. Do not capture, "
                         "do not classify as no-pets, do not read silence as "
                         "a refusal. Revisit after it opens."),
    ("HOLD_ACCESS_BLOCKED", "The property's own page failed on the server's "
                            "side. Retry the page; a failure to reach it says "
                            "nothing about its pet policy."),
    ("POLICY_OBSERVATION_REQUIRED", "The route is verified and the page "
                                    "serves. Observe the pet policy on it."),
    ("POLICY_RE_OBSERVATION_REQUIRED", "The page served and was silent on "
                                       "pets. A richer render may still "
                                       "surface a policy; silence is not a "
                                       "refusal."),
    ("ROUTING_VERIFICATION_REQUIRED", "The census carries a URL that the "
                                      "routing pass never adjudicated. Verify "
                                      "the binding before capturing."),
    ("IDENTITY_REVIEW", "Identity is provisional or unresolved; policy work "
                        "cannot safely bind to this record."),
    ("PROPERTY_LEVEL_URL_RECOVERY", "No official URL is known. Recover a "
                                    "first-party or brand property URL."),
))


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _decisions() -> Dict[str, Dict]:
    """identity_key -> the founder's ruling, from artifacts that carry one."""
    out: Dict[str, Dict] = {}
    for batch in "ABC":
        doc = _load(REPORTS / ("cincinnati_capture_pass1_founder_decisions_"
                               "batch%s.json" % batch))
        for row in doc["rows"]:
            out[row["identity_key"]] = {
                "founder_decision": row["founder_decision"],
                "decision_id": row["decision_id"],
                "source": "cincinnati_capture_pass1_founder_decisions_batch"
                          "%s.json" % batch,
            }
    for row in _load(REPORTS / "cincinnati_21c_recapture_001_founder_review.json"):
        key = "21c museum hotel cincinnati"
        out[key] = {
            "founder_decision": "APPROVE_PARTIAL_PUBLICATION",
            "decision_id": row["decision_id"],
            "source": "cincinnati_21c_recapture_001_founder_review.json",
        }
    return out


def build() -> Dict:
    partition = {i["identity_key"]: i
                 for i in _load(PKG / "cincinnati_final_partition_001.json")["items"]}
    census = {h["identity_key"]: h
              for h in _load(PKG / "identity_census" / "cincinnati-oh.json")["hotels"]}
    routes = {r["hotel_ref"]["identity_key"]: r
              for r in _load(AUTH / "identity_routing.json")["routes"]}
    published = {h["identity_key"]: h
                 for h in _load(PKG / "hotel_policy_facts_cincinnati-oh.json")["hotels"]}
    exclusions = {e["normalized_name"]: e
                  for e in _load(AUTH / "hotel_exclusions.json")["exclusions"]}
    pass1 = {r["identity_key"]: r
             for r in _load(REPORTS
                            / "cincinnati_capture_pass1_001_results.json")["rows"]}
    decisions = _decisions()

    rows: List[Dict] = []
    for index, key in enumerate(sorted(census), start=1):
        hotel = census[key]
        state = partition[key]["final_state"]
        route = routes.get(key)

        # URL grade. A routed identity has a URL, full stop -- that is the
        # whole point of the routing authority, and the old queue's failure
        # was to grade one MISSING_URL anyway.
        if route:
            url = route["official_property_url"]
            grade = ("EXACT_PROPERTY_FIRST_PARTY"
                     if route["binding_method"] == "PAGE_RENDERED"
                     else "BRAND_PROPERTY_PAGE")
        elif hotel.get("official_url"):
            url, grade = hotel["official_url"], "UNVERIFIED_CENSUS_URL"
        else:
            url, grade = "", "MISSING_URL"

        decision = decisions.get(key)
        record = published.get(key)
        exclusion = exclusions.get(key)
        result = pass1.get(key)

        if state == "PUBLISHED_PET_FRIENDLY":
            lane, status = "RESOLVED_PUBLISHED", "DECIDED"
        elif state == "VERIFIED_NO_PETS":
            lane, status = "RESOLVED_NO_PETS", "DECIDED"
        elif state == "OUT_OF_CURRENT_CATEGORY":
            lane, status = "RESOLVED_OUT_OF_CATEGORY", "DECIDED"
        elif key in PRE_OPENING:
            lane, status = "HOLD_PRE_OPENING", "HELD"
        elif key == ACCESS_BLOCKED:
            lane, status = "HOLD_ACCESS_BLOCKED", "HELD"
        elif result is not None and result["outcome"] == "POLICY_NOT_FOUND":
            lane, status = "POLICY_RE_OBSERVATION_REQUIRED", "NOT_STARTED"
        elif state == "AWAITING_IDENTITY_RESOLUTION":
            lane, status = "IDENTITY_REVIEW", "NOT_STARTED"
        elif grade == "UNVERIFIED_CENSUS_URL":
            lane, status = "ROUTING_VERIFICATION_REQUIRED", "NOT_STARTED"
        elif state == "AWAITING_OFFICIAL_URL":
            lane, status = "PROPERTY_LEVEL_URL_RECOVERY", "NOT_STARTED"
        else:
            lane, status = "POLICY_OBSERVATION_REQUIRED", "NOT_STARTED"

        row = OrderedDict((
            ("row_id", "CIN-Q2-%03d" % index),
            ("identity_key", key),
            ("hotel", hotel["canonical_name"]),
            ("city", hotel["city"]),
            ("state", hotel["state"]),
            ("postal_code", hotel["postal_code"]),
            ("corridor", hotel["corridor"]),
            ("official_url", url),
            ("url_grade", grade),
            ("final_state", state),
            ("capture_lane", lane),
            ("next_action", LANES[lane]),
            ("review_status", status),
        ))
        if decision:
            row["founder_decision"] = decision["founder_decision"]
            row["decision_id"] = decision["decision_id"]
            row["decision_source"] = decision["source"]
        if record:
            approval = record["approval"]
            row["approval_decision"] = approval["decision"]
            row["reviewer_id"] = approval["operator"]
            row["reviewed_at"] = approval["approval_date"]
            row["record_hash"] = approval["record_hash"]
        if exclusion:
            row["exclusion_state"] = exclusion["exclusion_state"]
            row["reviewer_id"] = exclusion["reviewer_id"]
            row["reviewed_at"] = exclusion["reviewed_at"]
        if key in PRE_OPENING:
            row["hold_reason"] = "PRE_OPENING"
            row["hold_note"] = PRE_OPENING[key]
            row["backlog_item"] = ("No canonical AWAITING_PROPERTY_OPENING "
                                   "state exists yet; Batch A raised it and it "
                                   "is still open.")
        if key == ACCESS_BLOCKED:
            row["hold_reason"] = "ACCESS_BLOCKED"
            row["hold_note"] = result["notes"] if result else ""
        if lane == "POLICY_RE_OBSERVATION_REQUIRED":
            row["prior_outcome"] = "POLICY_NOT_FOUND"
            row["prior_outcome_note"] = (
                "The page served its content and named no pet policy. Silence "
                "in the one section where pet-friendliness would appear is not "
                "a no-pets answer.")
        rows.append(row)

    lane_counts = Counter(r["capture_lane"] for r in rows)
    return OrderedDict((
        ("schema", "ptf-market-founder-review-queue/1.1"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("generated_at", AS_OF),
        ("supersedes", OrderedDict((
            ("work_order", "PTF-CINCINNATI-CENSUS-RECONCILIATION-001"),
            ("generated_at", "2026-08-16"),
            ("count", 250),
            ("why", "Generated the day before 210 routes were bound and 27 "
                    "identities were resolved. It graded 238 rows MISSING_URL "
                    "and marked all 250 NOT_STARTED, including the 21 that are "
                    "published."),
        ))),
        ("note", "Derived from the committed authority: the final partition "
                 "for state, the routing shard for URLs, the policy package "
                 "and exclusion registry for what is resolved and by whom, and "
                 "the three decision batches plus the 21c review for the "
                 "founder's rulings. No review outcome is inferred from the "
                 "prior 121-row discovery queue, which carried no field able "
                 "to record one."),
        ("sources", [
            "launch_packages/pettripfinder/cincinnati_final_partition_001.json",
            "launch_packages/pettripfinder/identity_census/cincinnati-oh.json",
            "launch_packages/pettripfinder/markets/authority/cincinnati-oh/identity_routing.json",
            "launch_packages/pettripfinder/markets/authority/cincinnati-oh/hotel_exclusions.json",
            "launch_packages/pettripfinder/hotel_policy_facts_cincinnati-oh.json",
            "launch_packages/pettripfinder/markets/reports/cincinnati_capture_pass1_001_results.json",
            "launch_packages/pettripfinder/markets/reports/cincinnati_capture_pass1_founder_decisions_batchA.json",
            "launch_packages/pettripfinder/markets/reports/cincinnati_capture_pass1_founder_decisions_batchB.json",
            "launch_packages/pettripfinder/markets/reports/cincinnati_capture_pass1_founder_decisions_batchC.json",
            "launch_packages/pettripfinder/markets/reports/cincinnati_21c_recapture_001_founder_review.json",
        ]),
        ("count", len(rows)),
        ("review_status_counts",
         OrderedDict(sorted(Counter(r["review_status"] for r in rows).items()))),
        ("lane_counts", OrderedDict((lane, lane_counts[lane])
                                    for lane in LANES if lane_counts[lane])),
        ("lane_meanings", LANES),
        ("url_grade_counts",
         OrderedDict(sorted(Counter(r["url_grade"] for r in rows).items()))),
        ("rows", rows),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    doc = build()
    print("rows            : %d" % doc["count"])
    print("review_status   : %s" % dict(doc["review_status_counts"]))
    print("url_grade       : %s" % dict(doc["url_grade_counts"]))
    print("lanes:")
    for lane, n in doc["lane_counts"].items():
        print("   %-32s %3d" % (lane, n))
    if args.write:
        OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
        print("WROTE %s" % OUT.name)
    else:
        print("(check only -- pass --write)")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())

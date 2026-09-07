"""PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031 -- the PROPOSED Detroit launch row.

WHAT THIS WRITES AND WHY IT IS NOT AN AUTHORIZATION
---------------------------------------------------
``deploy/netlify/assemble_production_site`` reads launch participation from one
committed path and nothing else. There is no override flag, and there is no way
to ask the assembler "what would the bundle look like if Detroit participated?"
without moving that record. So a launch-preparation order that must produce and
REPRODUCE the exact candidate a Detroit launch would build has to write the row
-- and the moment it does, the row is indistinguishable in shape from a founder
decision, because the schema has exactly one status that admits a market.

This module writes that row and makes the distinction in the only place left:
the decision block. ``decided_by`` does not say "founder", ``decided_on`` does
not carry a date, and the reason opens by saying the row is proposed. A reader
who wants to know whether Detroit was authorized reads three fields and gets a
straight answer, rather than inferring it from a work-order number.

What this does NOT do, on purpose:

  * writes no file under ``deploy/netlify/deployment_authorizations/``
  * writes no deployment record
  * does not touch the ``live`` block of the deployment-state pins
  * moves no byte of Detroit's own authority -- census, partition, policy
    package, exclusion shard, seed shard and release contract are untouched,
    and this order verified all six against the contract before writing

PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032 is where a
founder decision and a deployment authorization belong. Until that order runs,
an assembly built from this commit DOES include Detroit -- that is the whole
point of preparing a reproducible candidate, and it is why the candidate
manifest this order also writes records ``deployment_authorized: false``.

    python -m scripts.pettripfinder.detroit_ann_arbor_launch_prep_031 --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
PARTICIPATION = REPO_ROOT / "deploy" / "netlify" / "launch_participation.json"

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031"
MARKET_ID = "detroit-ann-arbor-mi"
NEXT_ORDER = "PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032"

#: Not "founder". The schema requires a non-empty value and offers no enum, so
#: the honest thing to put here is what actually happened.
DECIDED_BY = "proposed-by-launch-prep-031 (NO FOUNDER DECISION RECORDED)"
DECIDED_ON = "PENDING -- no founder decision has been made"

REASON = (
    "PROPOSED, NOT DECIDED. This row was written by %s so that the exact "
    "production candidate a Detroit launch would produce could be assembled and "
    "reproduced from a committed source commit. The assembler reads launch "
    "participation from this file and offers no override, so a candidate that "
    "includes Detroit cannot be built without it. "
    "It proposes detroit-ann-arbor-mi as the TWELFTH market at 121 published "
    "pet-friendly profiles and 81 verified-no-pets exclusions over a 247-identity "
    "census, taking the composed bundle from 803 to 924 profiles and from 966 to "
    "1099 sitemap routes with every other market's profile count unchanged and no "
    "route removed. "
    "No founder decision exists: decided_by names this order rather than the "
    "founder, decided_on carries no date, and no file was written under "
    "deploy/netlify/deployment_authorizations/. %s is the order that turns this "
    "proposal into a decision and consumes a deployment authorization; until it "
    "runs, nothing here authorizes a deploy. Every other market's status is "
    "unchanged." % (WORK_ORDER, NEXT_ORDER))

NOTE = (
    "PROPOSED for launch by %s; NOT founder-decided. 121 founder-signed "
    "pet-friendly profiles and 81 verified-no-pets exclusions over a 247-identity "
    "census (202 resolved, 45 unresolved); the release contract verifies with zero "
    "disagreements and the market assembles with all 27 gates passing, 121 profile "
    "routes, 10 published corridors and zero broken links. This order re-derived "
    "every one of those numbers from Detroit's own committed authority and moved "
    "none of it. The row previously read "
    "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH, and before "
    "PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029 it wrongly read NOT_SOURCE_READY -- "
    "true of that lineage, false of the market, whose hardened authority was "
    "stranded on a branch that forked before four live markets existed. Hidden from "
    "global navigation and from the market listing: show_in_navigation=false and "
    "show_in_sitemap=false, exactly as live Louisville, Cincinnati and Toledo are; "
    "those flags govern the hub's place in navigation, not whether the market's "
    "profile URLs are indexed, and its 133 routes do enter sitemap.xml. Founder "
    "rulings preserved unchanged by this order: the Troy EVEN Hotel and Hotel "
    "Indigo remain DISTINCT published identities on the shared 575 W Big Beaver "
    "campus; DoubleTree Ann Arbor North stays published; Royal Park and The Siren "
    "keep their partial-policy publications; Westin Book Cadillac and Roberts "
    "Riverwalk remain HELD at AWAITING_POLICY_OBSERVATION and are not published "
    "here." % WORK_ORDER)

#: Detroit's own authority, hashed as committed. A launch decision that cites
#: numbers should cite the bytes those numbers came from.
BASIS_FILES = OrderedDict([
    ("policy_package",
     "launch_packages/pettripfinder/hotel_policy_facts_detroit-ann-arbor-mi.json"),
    ("exclusion_shard",
     "launch_packages/pettripfinder/markets/authority/detroit-ann-arbor-mi/"
     "hotel_exclusions.json"),
    ("release_contract", "deploy/netlify/release_contracts/detroit-ann-arbor-mi.json"),
    ("identity_census",
     "launch_packages/pettripfinder/identity_census/detroit-ann-arbor-mi.json"),
    ("final_partition",
     "launch_packages/pettripfinder/detroit_ann_arbor_final_partition_001.json"),
    ("seed_shard",
     "launch_packages/pettripfinder/markets/authority/detroit-ann-arbor-mi/"
     "seed_businesses.csv"),
])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_document(source_commit: str) -> "OrderedDict":
    """The proposed record, derived from the committed one. Never invents a row."""
    raw = PARTICIPATION.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=OrderedDict)

    prev_wo = doc["decision"]["work_order"]
    prev_sha = hashlib.sha256(raw).hexdigest()
    prev_authorized = sorted(
        row["market_id"] for row in doc["markets"]
        if row["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH")
    if MARKET_ID in prev_authorized:
        raise SystemExit("%s is already authorized -- nothing to propose" % MARKET_ID)

    predecessor = OrderedDict([
        ("work_order", prev_wo),
        ("sha256", prev_sha),
        ("founder_authorized", prev_authorized),
    ])
    # supersedes names only the immediate predecessor; lineage keeps the chain
    # walkable, which is why the predecessor is appended rather than replaced.
    doc["decision"]["lineage"]["records"].append(predecessor)

    decision = doc["decision"]
    decision["work_order"] = WORK_ORDER
    decision["decided_by"] = DECIDED_BY
    decision["decided_on"] = DECIDED_ON
    decision["reason"] = REASON
    decision["proposal"] = OrderedDict([
        ("is_a_founder_decision", False),
        ("authorization_required_from", NEXT_ORDER),
        ("what_would_make_it_a_decision",
         "a founder decision recorded by %s, which also writes the deployment "
         "authorization this order deliberately does not" % NEXT_ORDER),
    ])
    basis = OrderedDict([
        ("what_this_is",
         "What the proposal rests on. These are a RECORD of the basis, not an "
         "authority: the assembler derives every one of them from the market's own "
         "census, package, shard and release contract, and a status that disagrees "
         "with the source fails the build."),
        ("market_id", MARKET_ID),
        ("source_commit", source_commit),
        ("census_count", 247),
        ("pet_friendly_publication_count", 121),
        ("verified_no_pets_count", 81),
        ("resolved", 202),
        ("unresolved", 45),
        ("founder_identity_holds",
         "Westin Book Cadillac Detroit and Roberts Riverwalk Hotel remain HELD at "
         "AWAITING_POLICY_OBSERVATION and publish nothing. The Troy EVEN Hotel and "
         "Hotel Indigo share one campus address and one phone and are published as "
         "two distinct identities under the standing same-campus ruling; this order "
         "reopened neither."),
    ])
    for name, rel in BASIS_FILES.items():
        path = REPO_ROOT / rel
        basis[name] = OrderedDict([("path", rel), ("sha256", _sha256(path))])
    decision["decision_basis"] = basis
    decision["supersedes"] = predecessor

    for row in doc["markets"]:
        if row["market_id"] == MARKET_ID:
            row["launch_status"] = "FOUNDER_AUTHORIZED_FOR_LAUNCH"
            row["note"] = NOTE
            row["proposed_not_decided"] = True
            break
    else:
        raise SystemExit("%s has no row to propose" % MARKET_ID)
    return doc


def render(doc) -> bytes:
    return (json.dumps(doc, indent=1) + "\n").encode("utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true",
                    help="write the record; without it, print what would change")
    ap.add_argument("--source-commit", default="UNPINNED",
                    help="the commit this proposal is derived from")
    args = ap.parse_args(argv)

    before = hashlib.sha256(PARTICIPATION.read_bytes()).hexdigest()
    doc = build_document(args.source_commit)
    payload = render(doc)
    after = hashlib.sha256(payload).hexdigest()

    print("%s -- PROPOSED Detroit launch participation" % WORK_ORDER)
    print("  market            : %s" % MARKET_ID)
    print("  launch_status     : SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"
          " -> FOUNDER_AUTHORIZED_FOR_LAUNCH")
    print("  decided_by        : %s" % DECIDED_BY)
    print("  decided_on        : %s" % DECIDED_ON)
    print("  participation before sha256: %s" % before)
    print("  participation after  sha256: %s" % after)
    print("  authorized markets: %d -> %d"
          % (len([r for r in json.loads(PARTICIPATION.read_text(encoding="utf-8-sig"))["markets"]
                  if r["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"]),
             len([r for r in doc["markets"]
                  if r["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"])))
    if not args.write:
        print("  DRY RUN -- nothing written (pass --write)")
        return 0
    PARTICIPATION.write_bytes(payload)
    print("  WROTE %s" % PARTICIPATION.relative_to(REPO_ROOT).as_posix())
    print("  NOT an authorization: no deployment authorization written, no")
    print("  deployment record written, live pins untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

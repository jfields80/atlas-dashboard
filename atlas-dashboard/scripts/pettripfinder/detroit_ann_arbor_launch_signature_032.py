"""PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032 -- the signature.

WHAT THIS CHANGES, AND WHAT IT DELIBERATELY DOES NOT
----------------------------------------------------
PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031 wrote Detroit's participation row as a
PROPOSAL. The schema admits exactly one status, so the row already read
FOUNDER_AUTHORIZED_FOR_LAUNCH and the candidate already assembled -- what was
missing was a decision. The proposal said so in three fields:

    decided_by          proposed-by-launch-prep-031 (NO FOUNDER DECISION RECORDED)
    decided_on          PENDING -- no founder decision has been made
    proposed_not_decided true

This module replaces exactly those three facts with the founder's decision. It
does NOT touch ``launch_status`` -- that value is already correct and has been
since 031 -- which is precisely why the composed bundle must not move. The
assembler reads ``launch_status`` and nothing else from this record.

That expectation is the whole risk of this order, so it is not assumed. The
order requires the bundle to be reassembled from the signed, committed source
and to match the packet's digest exactly; if it does not, the artifact the
founder authorized is not the artifact that would deploy, and a new
authorization is required. This module therefore prints the record's own hash
before and after so the change is visible and attributable.

    python -m scripts.pettripfinder.detroit_ann_arbor_launch_signature_032 --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
PARTICIPATION = REPO_ROOT / "deploy" / "netlify" / "launch_participation.json"

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032"
PREP_ORDER = "PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031"
MARKET_ID = "detroit-ann-arbor-mi"
DECIDED_ON = "2026-09-07"

REASON = (
    "Founder authorizes Detroit / Ann Arbor to participate in the next "
    "production assembly, joining as the TWELFTH market with 121 pet-friendly "
    "profiles over a 247-identity census. Every other market's decision is "
    "unchanged, and no other participation moved: Fort Wayne and Lexington are "
    "not registered for launch and are absent from the candidate. "
    "%s prepared this decision. It verified Detroit's authority on the current "
    "deployed lineage rather than trusting the prior order's report, audited "
    "the 121 published rows for wrong-authority defects and found none, "
    "reproduced the exact candidate a launch would build twice from clean "
    "worktrees, and then wrote this row as a PROPOSAL because the assembler "
    "admits exactly one status and the candidate could not otherwise be "
    "composed. This work order is the founder authorization instrument that "
    "turns that proposal into a decision. "
    "The founder was shown that signing this record changes the record's own "
    "bytes and therefore its sha256, and that the composed bundle must NOT "
    "move because the assembler reads launch_status alone -- and bound this "
    "authorization to a bundle reassembled from the signed source and proved "
    "identical to the prepared candidate 92b39c81c31988a1, rather than to the "
    "expectation that it would be." % PREP_ORDER)

NOTE = (
    "121 founder-signed pet-friendly profiles and 81 verified-no-pets "
    "exclusions over a 247-identity census (202 resolved, 45 unresolved); the "
    "release contract verifies with zero disagreements and the market "
    "assembles with all 27 gates passing, 121 profile routes, 10 published "
    "corridors and zero broken links. Prepared by %s and ADMITTED here by %s, "
    "which is the founder's explicit launch decision. Hidden from global "
    "navigation and from the market listing: show_in_navigation=false and "
    "show_in_sitemap=false, exactly as live Louisville, Cincinnati and Toledo "
    "are -- those flags govern the hub's place in navigation, not whether the "
    "market's profile URLs are indexed, and its 133 routes do enter "
    "sitemap.xml. Founder rulings carried into this launch unchanged: the Troy "
    "EVEN Hotel and Hotel Indigo remain DISTINCT published identities on the "
    "shared 575 W Big Beaver campus, which is the only shared premise among "
    "the 121; DoubleTree Ann Arbor North stays published; Royal Park and The "
    "Siren keep their partial-policy publications; Westin Book Cadillac and "
    "Roberts Riverwalk remain HELD at AWAITING_POLICY_OBSERVATION and publish "
    "nothing. This launch resolves none of those holds."
    % (PREP_ORDER, WORK_ORDER))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_document() -> "OrderedDict":
    raw = PARTICIPATION.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=OrderedDict)

    decision = doc["decision"]
    if decision["work_order"] != PREP_ORDER:
        raise SystemExit(
            "expected the committed record to be %s's proposal, found %s"
            % (PREP_ORDER, decision["work_order"]))
    if decision["decided_by"] == "founder":
        raise SystemExit("the record is already signed; nothing to authorize")

    row = next((r for r in doc["markets"] if r["market_id"] == MARKET_ID), None)
    if row is None:
        raise SystemExit("%s has no row" % MARKET_ID)
    if row["launch_status"] != "FOUNDER_AUTHORIZED_FOR_LAUNCH":
        raise SystemExit(
            "%s reads %s; 031 should have left it admitted"
            % (MARKET_ID, row["launch_status"]))

    # The decision, signed. work_order moves from the preparing order to the
    # authorizing one; the lineage below is NOT touched, because 031 never
    # deployed and this is the same decision reaching its final form rather
    # than a new record superseding it.
    decision["work_order"] = WORK_ORDER
    decision["decided_by"] = "founder"
    decision["decided_on"] = DECIDED_ON
    decision["reason"] = REASON
    decision["prepared_by"] = OrderedDict([
        ("work_order", PREP_ORDER),
        ("what_it_did",
         "verified the source, audited the published set, reproduced the exact "
         "candidate, and wrote this row as a proposal carrying no signature"),
        ("proposal_state",
         "decided_by named the preparing order, decided_on was PENDING, and the "
         "row carried proposed_not_decided: true"),
    ])
    # The proposal block described a decision that had not happened. It has.
    decision.pop("proposal", None)
    basis = decision.get("decision_basis")
    if basis is not None:
        basis["what_this_is"] = (
            "What the founder was shown when deciding. These are a RECORD of "
            "the basis, not an authority: the assembler derives every one of "
            "them from the market's own census, package, shard and release "
            "contract, and a status that disagrees with the source fails the "
            "build.")

    row["note"] = NOTE
    row.pop("proposed_not_decided", None)
    return doc


def render(doc) -> bytes:
    return (json.dumps(doc, indent=1) + "\n").encode("utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    before = _sha256_bytes(PARTICIPATION.read_bytes())
    doc = build_document()
    payload = render(doc)
    after = _sha256_bytes(payload)
    authorized = sorted(r["market_id"] for r in doc["markets"]
                        if r["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH")

    print("%s -- FOUNDER LAUNCH DECISION" % WORK_ORDER)
    print("  market             : %s" % MARKET_ID)
    print("  launch_status      : FOUNDER_AUTHORIZED_FOR_LAUNCH (unchanged -- "
          "set by %s)" % PREP_ORDER)
    print("  decided_by         : founder")
    print("  decided_on         : %s" % DECIDED_ON)
    print("  authorized markets : %d" % len(authorized))
    print("  record sha256 before: %s" % before)
    print("  record sha256 after : %s" % after)
    print("  the RECORD moves; the composed bundle must NOT. That is proved by")
    print("  reassembly against the packet digest, never assumed.")
    if not args.write:
        print("  DRY RUN -- nothing written (pass --write)")
        return 0
    PARTICIPATION.write_bytes(payload)
    print("  WROTE %s" % PARTICIPATION.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

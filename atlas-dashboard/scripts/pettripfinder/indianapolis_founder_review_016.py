# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-BACKLOG-ACQUISITION-016 -- the founder review of what 22 rows bought.

Thirteen pages served. This rules on them under the SAME reading rules 013
committed, imported rather than copied, so a rule cannot quietly drift between
one review and the next.

WHY THE READER WAS NOT WIDENED TO CATCH THE THIRTEENTH
------------------------------------------------------
Omni Severin's block says, in the property's own words:

    "Yes, Omni Severin Hotel is a pet friendly hotel for pets under 25 pounds."

That is an affirmative permission and a human reads it in a second. 013's
``_ALLOWS`` has no "pet friendly" pattern, so the block falls through to the
fee-language HOLD. The gap is in our reader, not in the source.

Adding the pattern would take one line, and this module deliberately does not
add it. A reading rule widened DURING the review whose count it raises is not a
rule, it is a result being arranged: the same edit would have to be defended
whether or not it produced a profile, and here it is inseparable from producing
one. The honest sequence is 014's -- surface the HOLD, name the cause, and let
the rule change happen in its own work order where the only question on the
table is whether the rule is right.

Nothing forces the shortcut either way: 44 + 12 clears the target of 50 without
this row. That is a reason to be careful, not a reason to relax.

NOTHING HERE PROMOTES ANYTHING. A signature proposes an authority. It writes no
profile, edits no census and publishes no page.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from scripts.pettripfinder import indianapolis_founder_review_013 as R
from scripts.pettripfinder.contracts import enums

LP = Path(__file__).resolve().parents[2] / "launch_packages" / "pettripfinder"
REVIEWER = "PTF-FOUNDER-001"
WORK_ORDER = "PTF-INDIANAPOLIS-BACKLOG-ACQUISITION-016"
RUN = "indianapolis_in_market_acquisition_016.json"


def _rows() -> List[Dict]:
    run = json.loads((LP / RUN).read_text(encoding="utf-8"))
    out: List[Dict] = []
    for result in run["results"]:
        block = R._block(result.get("artifact_dir", ""))
        out.append(OrderedDict((
            ("identity_key", result["identity_key"]),
            ("canonical_name", result.get("canonical_name", "")),
            ("brand", result.get("brand", "")),
            ("family", result.get("family", "")),
            ("corridor", result.get("corridor", "")),
            ("outcome", result.get("outcome")),
            ("final_state", result.get("final_state")),
            ("publication_grade", bool(result.get("publication_grade"))),
            ("provider", result.get("provider")),
            ("source_url", result.get("source_url", "")),
            ("policy_block", block),
            ("artifact_dir", result.get("artifact_dir", "")),
            ("content_hash", result.get("content_hash", "")),
            ("completed_at", result.get("completed_at", "")),
            ("detail", (result.get("detail") or "")[:220]),
            ("locator", R._locator(result.get("artifact_dir", ""))),
        )))
    return out


def packet(rows: List[Dict]) -> Dict:
    """Exception-only: what a person must actually look at."""
    candidates = [r for r in rows if r["publication_grade"]]
    no_evidence = [r for r in rows if r["outcome"] != "VALID"]
    return OrderedDict((
        ("schema", "ptf-founder-review-packet/1.0"),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("status", "EXCEPTIONS_ONLY"),
        ("nothing_is_published_by_this_file",
         "This packet proposes. It signs no row, promotes no identity and "
         "publishes nothing. A reading is never a decision: a service-animal "
         "sentence is a legal access category and not a pet permission, and a "
         "'fee' token says MENTIONED, not APPLIES."),
        ("counts", OrderedDict((
            ("attempted", len(rows)),
            ("valid", sum(1 for r in rows if r["outcome"] == "VALID")),
            ("publication_grade", len(candidates)),
            ("by_outcome", OrderedDict(sorted(
                Counter(r["outcome"] for r in rows).items()))),
            ("by_family", OrderedDict(sorted(
                Counter(r["family"] for r in rows).items()))),
        ))),
        ("review_candidates", candidates),
        ("no_evidence_to_rule_on", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("outcome", r["outcome"]), ("detail", r["detail"]),
        )) for r in no_evidence]),
    ))


def analysis(rows: List[Dict]) -> Dict:
    candidates = [r for r in rows if r["publication_grade"]]
    reviewed: List[Dict] = []
    for row in sorted(candidates, key=lambda r: r["identity_key"]):
        reading = R.read_block(row["policy_block"])
        disposition, reason = R.rule(row, reading)
        reviewed.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("family", row["family"]),
            ("policy_block", row["policy_block"]),
            ("source_url", row["source_url"]),
            ("reading", reading),
            ("disposition", disposition),
            ("reason", reason),
            ("semantic_hash", R._semantic_hash(row)),
            ("content_hash", row["content_hash"]),
            ("completed_at", row["completed_at"]),
        )))
    holds = [r for r in reviewed if r["disposition"] == R.HOLD]
    counts = Counter(r["disposition"] for r in reviewed)

    return OrderedDict((
        ("schema", "ptf-founder-review-analysis/1.0"),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("reading_rules",
         "imported verbatim from PTF-INDIANAPOLIS-TARGETED-FOUNDER-REVIEW-013 "
         "(scripts/pettripfinder/indianapolis_founder_review_013.py). They are "
         "not redefined here: a rule that differs between two reviews of the "
         "same market is two rules."),
        ("accounting", OrderedDict((
            ("attempted", len(rows)),
            ("candidates", len(candidates)),
            ("reviewed", len(reviewed)),
            ("each_candidate_once",
             len({r["identity_key"] for r in reviewed}) == len(reviewed)),
        ))),
        ("dispositions", OrderedDict(sorted(counts.items()))),
        ("reviewed", reviewed),
        ("exceptions", holds),
        ("the_reader_gap_we_did_not_paper_over", OrderedDict((
            ("identity_key", "omni severin hotel indianapolis"),
            ("what_the_source_says",
             "Yes, Omni Severin Hotel is a pet friendly hotel for pets under "
             "25 pounds."),
            ("why_it_held",
             "013's _ALLOWS carries 'pets allowed', 'pets welcome' and "
             "'N pets allowed'. It has no 'pet friendly' pattern, so an "
             "affirmative permission fell through to the fee-language HOLD."),
            ("this_is_our_defect_not_the_sources", True),
            ("why_the_rule_was_not_widened_here",
             "a reading rule widened during the review whose count it raises "
             "is a result being arranged. The same one-line edit has to be "
             "defensible when it produces nothing; here it is inseparable from "
             "producing a profile. It belongs in its own work order, the way "
             "014 handled the Home2 question-only block."),
            ("not_counted_in_the_new_signed_total", True),
            ("cost_to_resolve", "zero -- the capture is already paid for"),
        ))),
    ))


def signature(doc: Dict) -> Dict:
    now = datetime.now(timezone.utc).isoformat()
    signed, withheld = [], []
    for row in doc["reviewed"]:
        if row["disposition"] == R.HOLD:
            withheld.append(OrderedDict((
                ("identity_key", row["identity_key"]),
                ("canonical_name", row["canonical_name"]),
                ("disposition", R.HOLD), ("reason", row["reason"]),
                ("policy_block", row["policy_block"]),
                ("founder_reviewer_id", REVIEWER),
            )))
            continue
        authority = ("PUBLISHED_PET_FRIENDLY"
                     if row["disposition"] == R.APPROVE_PET_FRIENDLY
                     else "VERIFIED_NO_PETS")
        signed.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("brand", row["family"]), ("corridor", ""),
            # The CANONICAL publishing token. "APPROVED" is only a legacy
            # alias the vocabulary maps onto this one; writing the alias
            # put two spellings of one decision into the same package.
            ("founder_decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
            ("founder_reviewer_id", REVIEWER),
            ("founder_reviewed_at", now[:10]),
            ("reviewed_disposition", row["disposition"]),
            ("proposes_authority", authority),
            ("founder_note", row["reason"]),
            ("bound_semantic_hash", row["semantic_hash"]),
            ("bound_snapshot_hash", row["content_hash"]),
            ("bound_source_url", row["source_url"]),
            ("true_capture_completed_at", row["completed_at"]),
            ("promotion", ""),
        )))
    by_authority = Counter(r["proposes_authority"] for r in signed)
    return OrderedDict((
        ("schema", "ptf-founder-decision-ledger/1.0"),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("approval_vocabulary", "founder-approval-vocabulary/1.0"),
        ("decided_by", REVIEWER), ("decided_at", now[:10]),
        ("recorded_by", "claude-opus-5 (agent) -- transcription only; every "
                        "disposition is derived from the quoted block by the "
                        "013 rules and no raw evidence was altered"),
        ("status", "RECORDED"),
        ("candidates_reviewed", len(doc["reviewed"])),
        ("signed_count", len(signed)), ("withheld_count", len(withheld)),
        ("signed_by_authority", OrderedDict(sorted(by_authority.items()))),
        ("nothing_is_published_by_this_file",
         "This view records decisions. It registers no market, promotes no "
         "census row, publishes no page and deploys nothing."),
        ("signed", signed), ("withheld", withheld),
    ))


def running_total(sig: Dict) -> Dict:
    # What was PROMOTED when this work order ran. Deliberately a constant
    # and not a read of the live package: PTF-INDIANAPOLIS-56-PROFILE-
    # AUTHORITY-PROMOTION-017 later promoted this market, and a review
    # that recomputed its own history from live state would report
    # "44 + 12 = 86" -- counting the promotion its own signatures caused.
    promoted = 24
    prior = 0
    for name in ("indianapolis_in_founder_signature_013.json",
                 "indianapolis_in_founder_signature_014.json"):
        prior += sum(1 for r in json.loads((LP / name).read_text(encoding="utf-8"))
                     ["signed"] if r["proposes_authority"] == "PUBLISHED_PET_FRIENDLY")
    new = sig["signed_by_authority"].get("PUBLISHED_PET_FRIENDLY", 0)
    total = promoted + prior + new
    return OrderedDict((
        ("promoted_pet_friendly", promoted),
        ("signed_pet_friendly_013_014", prior),
        ("current_signed_pet_friendly", promoted + prior),
        ("new_signed_pet_friendly", new),
        ("projected_total_after_review", total),
        ("target", 50),
        ("remaining_gap_to_50", max(0, 50 - total)),
        ("target_met_in_signatures", total >= 50),
        ("caveat", "these are SIGNATURES, which propose authority. Not one row "
                   "is promoted, no profile is written and nothing is "
                   "published. The 50 is met in signed evidence, not on the "
                   "site."),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-out", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--signature-out", default="")
    args = parser.parse_args(argv)

    rows = _rows()
    pkt = packet(rows)
    doc = analysis(rows)
    sig = signature(doc)
    doc["running_total"] = running_total(sig)

    for path, payload in ((args.packet_out, pkt), (args.out, doc),
                          (args.signature_out, sig)):
        if path:
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("attempted %d | candidates %d" % (pkt["counts"]["attempted"],
                                            pkt["counts"]["publication_grade"]))
    print("dispositions %s" % dict(doc["dispositions"]))
    print("signed %d (%s), withheld %d"
          % (sig["signed_count"], dict(sig["signed_by_authority"]),
             sig["withheld_count"]))
    total = doc["running_total"]
    print("44 + %d = %d, gap to 50 = %d"
          % (total["new_signed_pet_friendly"],
             total["projected_total_after_review"],
             total["remaining_gap_to_50"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

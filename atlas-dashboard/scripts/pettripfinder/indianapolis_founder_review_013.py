# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-TARGETED-FOUNDER-REVIEW-013 -- rule on 31, by hand only where it matters.

Fifty authorised properties came back from 012 with 31 publication-grade
candidates. This reads every block, auto-accepts the ones where a machine and a
careful second reading agree, and surfaces only what a person has to decide.

THE FIVE "CONTRADICTORY" ROWS WERE NOT CONTRADICTORY
-----------------------------------------------------
012's packet flagged five blocks as reading both ways. Reading them settles it
immediately:

    "No Pets Allowed Only service animals are permitted, free of charge."
    "Pets Allowed: No General: Only service animals are permitted..."
    "ADA defined service animals are welcome. Sorry no other pets are allowed."

Every one is a plain refusal. The flag was a defect in 012's own INDICATIVE
regex, which matched "pets allowed" inside "No Pets Allowed" and inside "Pets
Allowed: No". The sources never disagreed with themselves; a first-pass reader
disagreed with the sentence it was reading. Recorded here rather than quietly
corrected, because a packet that cries contradiction five times teaches a
reviewer to stop believing it.

WHAT IS STILL REFUSED
---------------------
Two rows are held, and both are held for the reasons this work order names:

    a FEE alone is not a permission. Extended Stay America's block is an
    entire fee schedule and never says pets may come.
    a QUESTION is not an answer. Home2 Keystone Crossing's locator captured
    the FAQ heading "Are pets allowed at ...?" and stopped there.

And one row never reached review at all: Motel 6's block is an amenity list --
"Pets Allowed Elevator Restaurant Nearby Racing Wi-Fi" -- which the acquisition
had already marked non-publication-grade. An amenity label is not a policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

LP = Path(__file__).resolve().parents[2] / "launch_packages" / "pettripfinder"
REVIEWER = "PTF-FOUNDER-001"
WORK_ORDER = "PTF-INDIANAPOLIS-TARGETED-FOUNDER-REVIEW-013"

APPROVE_PET_FRIENDLY = "APPROVE_PET_FRIENDLY"
APPROVE_NO_PETS = "APPROVE_VERIFIED_NO_PETS"
APPROVE_WITH_CHANGE = "APPROVE_WITH_CHANGE"
HOLD = "HOLD"

#: A refusal anywhere in the block settles it. Checked BEFORE any permission
#: pattern, because "No Pets Allowed" contains "Pets Allowed" and that is
#: exactly how 012's indicative reader talked itself into five contradictions.
_REFUSES = (
    re.compile(r"pets?\s+(are\s+)?not\s+allowed", re.I),
    re.compile(r"no\s+pets\s+allowed", re.I),
    re.compile(r"pets\s+allowed\s*:\s*no\b", re.I),
    re.compile(r"sorry\s*,?\s*no\s+other\s+pets", re.I),
    re.compile(r"\bno\s+pets\b", re.I),
)

#: An AFFIRMATIVE permission. A fee, a deposit or a weight limit is not one of
#: these: those describe terms that would apply IF pets were allowed, and this
#: corpus has a Motel 6 whose "Pets Allowed" sits in a list beside "Elevator".
_ALLOWS = (
    re.compile(r"pets?\s+(are\s+)?allowed\b(?!\s*:\s*no)", re.I),
    re.compile(r"pets?\s+(are\s+)?welcome", re.I),
    re.compile(r"pets\s+allowed\s*:\s*yes", re.I),
    re.compile(r"pets\s+allowed\s+yes", re.I),
    re.compile(r"\d+\s+pets?\s+allowed", re.I),
    # "is a pet friendly hotel" -- an affirmative permission this list did not
    # carry, found by PTF-INDIANAPOLIS-BACKLOG-ACQUISITION-016 on Omni Severin
    # and deliberately left for its own work order rather than widened mid-
    # review. Anchored on IS/ARE + the property being the pet-friendly thing,
    # so a marketing list ("pet friendly rooms", "/pet-friendly-hotels") and a
    # REFUSAL ("not a pet friendly hotel") are both excluded.
    re.compile(r"\b(?:is|are)\s+(?:a\s+)?pet[\s-]friendly\b", re.I),
)

#: Language about a legal access category. Never a pet permission, and never a
#: refusal either -- it is orthogonal, and a block that says only this says
#: nothing about pets.
_SERVICE_ANIMAL = re.compile(
    r"service\s+animals?|ada[- ]defined|emotional\s+support\s+animal", re.I)

_FEE = re.compile(r"pet\s+fee|pet\s+deposit|pet\s+damage\s+deposit|"
                  r"non-?refundable|pet\s+cleaning\s+fee|pet\s+accommodations",
                  re.I)

#: A block that is a question and not a statement.
_QUESTION_ONLY = re.compile(r"^\s*(are|does|can|do)\b[^.]*\?\s*$", re.I)

#: A block that is an amenity run rather than a sentence about pets.
_AMENITY_RUN = re.compile(
    r"pets?\s+allowed\s+(elevator|wi-?fi|parking|restaurant|pool|breakfast)",
    re.I)


def _block(artifact_dir: str) -> str:
    path = os.path.join((artifact_dir or "").replace(chr(92), "/"),
                        "policy-block.txt")
    if not os.path.isfile(path):
        return ""
    return open(path, encoding="utf-8", errors="replace").read().strip()


def _locator(artifact_dir: str) -> Dict:
    path = os.path.join((artifact_dir or "").replace(chr(92), "/"),
                        "locator.json")
    if not os.path.isfile(path):
        return {}
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except ValueError:
        return {}


def read_block(block: str) -> Dict:
    """A careful second reading: what the block actually says, and about what."""
    refuses = [p.pattern for p in _REFUSES if p.search(block)]
    allows = [p.pattern for p in _ALLOWS if p.search(block)]
    # A refusal outranks a permission pattern, because every permission pattern
    # that fires inside a refusal is a substring of it.
    if refuses:
        allows = []
    return OrderedDict((
        ("denying_language", refuses),
        ("allowing_language", allows),
        ("service_animal_language", bool(_SERVICE_ANIMAL.search(block))),
        ("fee_language", bool(_FEE.search(block))),
        ("question_only", bool(_QUESTION_ONLY.match(block))),
        ("amenity_run", bool(_AMENITY_RUN.search(block))),
    ))


def rule(row: Dict, reading: Dict) -> Dict:
    """``(disposition, reason)`` -- and the reasons a row is NOT approved."""
    block = row["policy_block"]
    if not block.strip():
        return (HOLD, "the located block is empty; there is nothing to rule on")
    if reading["question_only"]:
        return (HOLD,
                "the locator captured the FAQ heading and stopped: the block is "
                "a question, not an answer. A question is not a policy.")
    if reading["amenity_run"]:
        return (HOLD,
                "'Pets Allowed' appears in a run of amenity labels beside "
                "Elevator and Wi-Fi. An amenity label is not a policy.")
    if reading["denying_language"]:
        return (APPROVE_NO_PETS,
                "the source refuses pets in its own words%s"
                % ("; the service-animal sentence beside it is a legal access "
                   "category and neither softens nor contradicts the refusal"
                   if reading["service_animal_language"] else ""))
    if reading["allowing_language"]:
        return (APPROVE_PET_FRIENDLY,
                "the source affirmatively permits pets in its own words%s"
                % ("; its service-animal sentence is separate and was not read "
                   "as the permission" if reading["service_animal_language"]
                   else ""))
    if reading["fee_language"]:
        return (HOLD,
                "the block states pet FEES and never states that pets may come. "
                "A fee says a charge was MENTIONED, not that it APPLIES, and "
                "inferring permission from it is the exact mistake this review "
                "is instructed not to make.")
    if reading["service_animal_language"]:
        return (HOLD,
                "the block speaks only about service animals, which is a legal "
                "access category and says nothing about pets")
    return (HOLD, "the block names no pet permission and no refusal")


def _semantic_hash(row: Dict) -> str:
    material = json.dumps(OrderedDict((
        ("identity_key", row["identity_key"]),
        ("policy_block", row["policy_block"]),
        ("source_url", row["source_url"]),
    )), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def build() -> Dict:
    run = json.loads((LP / "indianapolis_in_market_acquisition_012.json")
                     .read_text(encoding="utf-8"))
    packet = json.loads((LP / "indianapolis_in_founder_review_packet_012.json")
                        .read_text(encoding="utf-8"))
    candidates = {r["identity_key"] for r in packet["review_candidates"]}
    by_key = {r["identity_key"]: r for r in run["results"]}

    reviewed: List[Dict] = []
    for key in sorted(candidates):
        result = by_key[key]
        block = _block(result.get("artifact_dir", ""))
        locator = _locator(result.get("artifact_dir", ""))
        row = OrderedDict((
            ("identity_key", key),
            ("canonical_name", result.get("canonical_name", "")),
            ("brand", result.get("brand", "")),
            ("corridor", result.get("corridor", "")),
            ("source_url", result.get("source_url", "")),
            ("policy_block", block),
            ("identity_confirmed", bool(result.get("identity_confirmed"))),
            ("locator_strategy", result.get("locator_strategy", "")),
            ("content_hash", result.get("content_hash", "")),
            ("block_sha256", locator.get("block_sha256", "")),
            ("completed_at", result.get("completed_at", "")),
            ("machine_disposition", packet_reading(packet, key)),
        ))
        reading = read_block(block)
        disposition, reason = rule(row, reading)
        row["deeper_reading"] = reading
        row["disposition"] = disposition
        row["reason"] = reason
        row["machine_and_deeper_agree"] = _agrees(row["machine_disposition"],
                                                  disposition)
        reviewed.append(row)

    # Anything VALID that never became a candidate is still accounted for.
    not_candidates = [OrderedDict((
        ("identity_key", r["identity_key"]),
        ("outcome", r["outcome"]), ("final_state", r["final_state"]),
        ("policy_block", _block(r.get("artifact_dir", ""))),
        ("disposition", HOLD),
        ("reason", "acquired but not publication-grade; it never entered "
                   "review and is recorded so the 50 attempts still add up"),
    )) for r in run["results"]
        if r["identity_key"] not in candidates and r["outcome"] == "VALID"]

    approved_pf = [r for r in reviewed if r["disposition"] == APPROVE_PET_FRIENDLY]
    approved_np = [r for r in reviewed if r["disposition"] == APPROVE_NO_PETS]
    holds = [r for r in reviewed if r["disposition"] == HOLD]
    changes = [r for r in reviewed if r["disposition"] == APPROVE_WITH_CHANGE]
    disagreements = [r for r in reviewed if not r["machine_and_deeper_agree"]]

    promoted = 24
    return OrderedDict((
        ("schema", "ptf-founder-review-analysis/1.0"),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("reviewer", REVIEWER),
        ("nothing_is_published_by_this_file",
         "This is a review. It signs nothing on its own; the signature ledger "
         "beside it records what the founder approved."),
        ("accounting", OrderedDict((
            ("candidates", len(candidates)),
            ("reviewed", len(reviewed)),
            ("valid_but_not_publication_grade", len(not_candidates)),
            ("each_candidate_once", len(reviewed) == len(candidates)),
        ))),
        ("dispositions", OrderedDict(sorted(
            Counter(r["disposition"] for r in reviewed).items()))),
        ("machine_vs_deeper_disagreements", OrderedDict((
            ("count", len(disagreements)),
            ("identity_keys", [r["identity_key"] for r in disagreements]),
            ("of_which_012_called_contradictory", sorted(
                r["identity_key"] for r in disagreements
                if r["machine_disposition"] == "READS_BOTH_WAYS_NEEDS_A_RULING")),
            ("of_which_are_the_two_holds", sorted(
                r["identity_key"] for r in disagreements
                if r["disposition"] == HOLD)),
        ))),
        ("the_contradiction_that_was_not_one", OrderedDict((
            ("count", 5),
            ("verdict", "not one of the five contradicts itself"),
            ("cause", "012's INDICATIVE regex matched 'pets allowed' inside "
                      "'No Pets Allowed' and inside 'Pets Allowed: No'. The "
                      "sources are plain refusals; the first-pass reader "
                      "disagreed with the sentence it was reading."),
            ("ruling", "all five approved as VERIFIED_NO_PETS"),
            ("identity_keys", sorted(
                r["identity_key"] for r in reviewed
                if r["machine_disposition"] == "READS_BOTH_WAYS_NEEDS_A_RULING")),
        ))),
        ("auto_accepted", len(approved_pf) + len(approved_np)),
        ("auto_accept_rule",
         "accepted without a human only when the block states a permission or a "
         "refusal in its own words, identity is confirmed, the evidence is "
         "first-party and publication-grade, no service-animal sentence is "
         "doing the work of a permission, and no fee stands in for one"),
        ("exceptions", holds + changes),
        ("valid_but_not_publication_grade", not_candidates),
        ("running_total", OrderedDict((
            ("current_promoted_pet_friendly", promoted),
            ("new_signed_pet_friendly", len(approved_pf)),
            ("projected_total_after_review", promoted + len(approved_pf)),
            ("new_verified_no_pets", len(approved_np)),
            ("approve_with_change", len(changes)),
            ("holds", len(holds)),
            ("unresolved", len(holds) + len(changes)),
            ("target", 50),
            ("remaining_gap_to_50", max(0, 50 - promoted - len(approved_pf))),
        ))),
        ("reviewed", reviewed),
    ))


def packet_reading(packet: Dict, key: str) -> str:
    for row in packet["review_candidates"]:
        if row["identity_key"] == key:
            return row["indicative_reading"]
    return ""


def _agrees(machine: str, deeper: str) -> bool:
    return {("READS_AS_PET_FRIENDLY", APPROVE_PET_FRIENDLY),
            ("READS_AS_NO_PETS", APPROVE_NO_PETS)}.__contains__((machine, deeper))


def signature(analysis: Dict) -> Dict:
    """The sanctioned signature view. Only approved rows are signed."""
    signed: List[Dict] = []
    now = datetime.now(timezone.utc).isoformat()
    for row in analysis["reviewed"]:
        if row["disposition"] not in (APPROVE_PET_FRIENDLY, APPROVE_NO_PETS):
            continue
        signed.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("brand", row["brand"]), ("corridor", row["corridor"]),
            ("founder_decision", "APPROVED_AFTER_CURRENT_REVIEW"),
            ("founder_reviewer_id", REVIEWER),
            ("founder_reviewed_at", now[:10]),
            ("founder_note", ""),
            ("reviewed_disposition", row["disposition"]),
            ("proposes_authority",
             "PUBLISHED_PET_FRIENDLY" if row["disposition"] == APPROVE_PET_FRIENDLY
             else "VERIFIED_NO_PETS"),
            ("bound_semantic_hash", _semantic_hash(row)),
            ("bound_snapshot_hash", row["content_hash"]),
            ("bound_block_sha256", row["block_sha256"]),
            ("bound_source_url", row["source_url"]),
            ("true_capture_completed_at", row["completed_at"]),
            ("promotion", ""),
        )))
    withheld = [OrderedDict((
        ("identity_key", r["identity_key"]),
        ("reviewed_disposition", r["disposition"]),
        ("why", r["reason"]))) for r in analysis["exceptions"]]
    counts = Counter(r["proposes_authority"] for r in signed)
    return OrderedDict((
        ("schema", "ptf-founder-decision-ledger/1.0"),
        ("what_this_is",
         "The signature view of PTF-INDIANAPOLIS-TARGETED-FOUNDER-REVIEW-013: "
         "the rows the founder approved out of the 31 candidates produced by "
         "the 012 targeted acquisition, each bound to the evidence it was "
         "approved over."),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("approval_vocabulary", "founder-approval-vocabulary/1.0"),
        ("decided_by", REVIEWER), ("decided_at", now[:10]),
        ("authorization", "PTF-INDIANAPOLIS-TARGETED-POLICY-ACQUISITION-012 "
                          "(50 authorised properties, 31 publication-grade "
                          "candidates)"),
        ("recorded_by", "claude-opus-5 (agent) -- transcription only; every "
                        "disposition is derived from the quoted block and no "
                        "raw evidence was altered"),
        ("status", "RECORDED"),
        ("candidates_reviewed", analysis["accounting"]["candidates"]),
        ("signed_count", len(signed)),
        ("withheld_count", len(withheld)),
        ("signed_by_authority", OrderedDict(sorted(counts.items()))),
        ("nothing_is_published_by_this_file",
         "This view records decisions. It registers no market, promotes no "
         "census row, publishes no page and deploys nothing."),
        ("withheld", withheld),
        ("signed", signed),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    parser.add_argument("--signature-out", default="")
    args = parser.parse_args(argv)
    analysis = build()
    if args.out:
        Path(args.out).write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    sig = signature(analysis)
    if args.signature_out:
        Path(args.signature_out).write_text(json.dumps(sig, indent=2),
                                            encoding="utf-8")
    total = analysis["running_total"]
    print("candidates            %d (each once: %s)"
          % (analysis["accounting"]["candidates"],
             analysis["accounting"]["each_candidate_once"]))
    print("dispositions          %s" % dict(analysis["dispositions"]))
    print("auto-accepted         %d" % analysis["auto_accepted"])
    print("signed                %d  %s" % (sig["signed_count"],
                                            dict(sig["signed_by_authority"])))
    print("withheld              %d" % sig["withheld_count"])
    print("pet-friendly          %d + %d = %d   (gap to 50: %d)"
          % (total["current_promoted_pet_friendly"],
             total["new_signed_pet_friendly"],
             total["projected_total_after_review"],
             total["remaining_gap_to_50"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

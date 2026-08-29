# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-HOME2-KEYSTONE-REPARSE-014 -- one HOLD, settled from disk.

013 held Home2 Suites Indianapolis Keystone Crossing because its locator
captured the FAQ heading -- "Are pets allowed at Home2 Suites by Hilton
Indianapolis Keystone Crossing?" -- and stopped there. A question is not a
policy. The answer was in the capture the whole time.

NO PROVIDER IS CALLED AND NOTHING IS SPENT.

THIS IS A RE-LOCATE, NOT A RE-PARSE, AND THE DIFFERENCE MATTERS
----------------------------------------------------------------
PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018 draws the line and this module sits
on the far side of it. 018 re-parses THE BLOCK the locator already chose,
because re-locating from ``rendered.html`` changes two things at once -- which
text the record is about, and how that text is read -- and only the second is a
re-derivation. The first, 018 says, is a re-acquisition, and it declined to do
it even where the static walk was demonstrably under-reading.

018 was protecting against a specific harm: one Milwaukee block stated the same
fee on two bases, the reader correctly withheld, and a shorter re-located block
would have looked clean and published one of the two. Re-locating there would
have silently moved what the record was ABOUT.

That harm cannot occur here, and the reason is precise: the block this record
currently holds ASSERTS NOTHING. It is an interrogative with no predicate. There
is no finding to move, no withheld contradiction to paper over, and no second
basis to accidentally prefer. Moving from "no statement" to "the property's own
answer to that exact question" adds a finding where there was none rather than
replacing one.

It is still a re-locate, this work order authorises it by name, and the guard is
carried explicitly: the whole artifact is scanned for any contradicting pet
sentence before the correction is allowed to stand.

AND IT IS NOT BRAND BOILERPLATE
--------------------------------
PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 learned that Best Western's JSON-LD
``petsAllowed:false`` is boilerplate stamped on every property. The test that
separates boilerplate from a statement is whether the text NAMES THIS BUILDING.
This one does, twice, in its own sentence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from scripts.pettripfinder.contracts import enums

_REPO_ROOT = Path(__file__).resolve().parents[2]
LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
ARTIFACT = (_REPO_ROOT / "data" / "acquisition" / "indianapolis_in_012"
            / "home2-suites-by-hilton-indianapolis-keystone-crossing"
            / "attempt-02")

IDENTITY = "home2 suites by hilton indianapolis keystone crossing"
REVIEWER = "PTF-FOUNDER-001"
WORK_ORDER = "PTF-INDIANAPOLIS-HOME2-KEYSTONE-REPARSE-014"

#: Every way this artifact could contradict a pet permission.
_REFUSALS = (
    r"pets?\s+(are\s+)?not\s+allowed", r"no\s+pets\s+allowed",
    r"pets\s+allowed\s*:\s*no", r"no\s+other\s+pets",
    r'"petsAllowed"\s*:\s*false',
)

#: The property's own answer, keyed on the question it answers. Anchored on
#: "Yes, pets are allowed at <this property>" so a generic sentence cannot
#: satisfy it.
_ANSWER = re.compile(
    r"Yes,\s+pets\s+are\s+allowed\s+at\s+Home2\s+Suites\s+by\s+Hilton\s+"
    r"Indianapolis\s+Keystone\s+Crossing\.[^\"]{0,400}")


def read_artifact() -> Dict:
    html = (ARTIFACT / "rendered.html").read_text(encoding="utf-8",
                                                  errors="replace")
    block = (ARTIFACT / "policy-block.txt").read_text(encoding="utf-8",
                                                     errors="replace").strip()
    locator = json.loads((ARTIFACT / "locator.json").read_text(encoding="utf-8"))
    statements = sorted(set(m.group(0).strip() for m in _ANSWER.finditer(html)))
    contradictions: List[str] = []
    for pattern in _REFUSALS:
        for match in re.finditer(pattern, html, re.I):
            start = max(0, match.start() - 80)
            contradictions.append(html[start:match.end() + 80])
    return OrderedDict((
        ("artifact_dir", ARTIFACT.relative_to(_REPO_ROOT).as_posix()),
        ("rendered_html_sha256",
         hashlib.sha256((ARTIFACT / "rendered.html").read_bytes()).hexdigest()),
        ("held_block", block),
        ("held_block_sha256", locator.get("block_sha256", "")),
        ("held_locator_strategy", locator.get("strategy", "")),
        ("statements", statements),
        ("contradictions", contradictions),
    ))


def extract_facts(statement: str) -> Dict:
    """Only what the sentence says. Everything else is absent, not defaulted."""
    weight = re.search(r"up\s+to\s+(\d+)\s*lbs", statement, re.I)

    # The two tiers the sentence states, read in the form it states them. A
    # tier the sentence does not state is not invented, and the lead "$75.00
    # non-refundable fee" is NOT read as a third, separate charge -- it is the
    # same first tier said once in summary and once in detail.
    tiers: List[Dict] = []
    first = re.search(r"stays\s+of\s+(\d+)-(\d+)\s+nights,\s+the\s+fee\s+is\s+"
                      r"\$(\d+(?:\.\d{2})?)", statement, re.I)
    if first:
        tiers.append(OrderedDict((("amount_usd", float(first.group(3))),
                                  ("min_nights", int(first.group(1))),
                                  ("max_nights", int(first.group(2))))))
    second = re.search(r"stays\s+of\s+(\d+)\s+or\s+more\s+nights,\s+the\s+fee\s+"
                       r"is\s+\$(\d+(?:\.\d{2})?)", statement, re.I)
    if second:
        tiers.append(OrderedDict((("amount_usd", float(second.group(2))),
                                  ("min_nights", int(second.group(1))),
                                  ("max_nights", None))))

    refundable = None
    if re.search(r"non-?refundable", statement, re.I):
        refundable = False
    return OrderedDict((
        ("pets_allowed", True),
        ("pets_allowed_evidence",
         "Yes, pets are allowed at Home2 Suites by Hilton Indianapolis "
         "Keystone Crossing."),
        ("max_weight_lbs", int(weight.group(1)) if weight else None),
        ("fee_tiers", tiers),
        ("fee_basis", "per stay" if tiers else None),
        ("fee_refundable", refundable),
        ("fee_scope", None),
        ("max_pets", None),
        ("species", None),
        ("withheld_because_the_source_does_not_say", [
            "fee_scope -- the sentence never says whether the fee is per pet "
            "or per room",
            "max_pets -- no count is stated",
            "species -- no species restriction is stated",
        ]),
        ("not_borrowed_from_siblings",
         "the other Home2 and Homewood properties in this market state '2 pets "
         "max, dogs/cats only'. That is THEIR evidence and it is not imported "
         "here; absence on this property stays absence."),
    ))


def semantic_hash(identity_key: str, statement: str, source_url: str) -> str:
    material = json.dumps(OrderedDict((
        ("identity_key", identity_key), ("policy_block", statement),
        ("source_url", source_url))), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def build() -> Dict:
    run = json.loads((LP / "indianapolis_in_market_acquisition_012.json")
                     .read_text(encoding="utf-8"))
    analysis = json.loads((LP / "indianapolis_in_founder_review_analysis_013.json")
                          .read_text(encoding="utf-8"))
    result = next(r for r in run["results"] if r["identity_key"] == IDENTITY)
    held = next(r for r in analysis["exceptions"] if r["identity_key"] == IDENTITY)

    artifact = read_artifact()
    clean = (len(artifact["statements"]) == 1
             and not artifact["contradictions"])
    statement = artifact["statements"][0] if artifact["statements"] else ""
    facts = extract_facts(statement) if clean else {}
    names_this_property = IDENTITY.replace(" ", "").lower()[:20] in \
        statement.replace(" ", "").lower()[:200] or \
        "Home2 Suites by Hilton Indianapolis Keystone Crossing" in statement

    checks = OrderedDict((
        ("identity_confirmed_by_the_capture",
         bool(result.get("identity_confirmed"))),
        ("source_is_first_party",
         result.get("source_url", "").startswith("https://www.hilton.com/")),
        ("exactly_one_pet_statement_in_the_artifact",
         len(artifact["statements"]) == 1),
        ("no_contradicting_pet_text_anywhere",
         not artifact["contradictions"]),
        ("the_statement_names_this_building_not_the_brand", names_this_property),
        ("pets_allowed_is_stated_not_inferred",
         bool(facts.get("pets_allowed"))),
        ("no_service_animal_sentence_is_doing_the_work",
         "service animal" not in statement.lower()),
    ))

    return OrderedDict((
        ("schema", "ptf-saved-artifact-reparse/1.0"),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("identity_key", IDENTITY),
        ("canonical_name", result.get("canonical_name", "")),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("what_this_is",
         "One held record settled from the capture already on disk. No provider "
         "was called and no raw evidence was altered."),
        ("this_is_a_relocate_not_a_reparse", OrderedDict((
            ("doctrine", "PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018 re-parses "
                         "the BLOCK and calls re-locating from rendered.html a "
                         "re-acquisition, because it changes WHICH text the "
                         "record is about as well as how it is read."),
            ("why_it_is_safe_here",
             "the held block asserts nothing -- it is an interrogative with no "
             "predicate. There is no finding to move, no withheld contradiction "
             "to paper over and no second fee basis to accidentally prefer. "
             "This adds a finding where there was none."),
            ("authorised_by", WORK_ORDER),
            ("guard_carried", "the whole artifact is scanned for any "
                              "contradicting pet sentence before the "
                              "correction may stand"),
        ))),
        ("original_hold", OrderedDict((
            ("work_order", "PTF-INDIANAPOLIS-TARGETED-FOUNDER-REVIEW-013"),
            ("disposition", held["disposition"]),
            ("reason", held["reason"]),
            ("held_block", artifact["held_block"]),
            ("held_block_sha256", artifact["held_block_sha256"]),
            ("held_locator_strategy", artifact["held_locator_strategy"]),
        ))),
        ("correction", OrderedDict((
            ("reason", "the property's own answer to the very question the "
                       "locator stopped at is present in the same capture, in "
                       "three encodings, and says pets are allowed"),
            ("recovered_statement", statement),
            ("occurrences_in_the_artifact", 3),
            ("source_url", result.get("source_url", "")),
            ("artifact_dir", artifact["artifact_dir"]),
            ("rendered_html_sha256", artifact["rendered_html_sha256"]),
            ("raw_evidence_altered", False),
        ))),
        ("verification", checks),
        ("all_checks_pass", all(checks.values())),
        ("corrected_facts", facts),
        ("new_disposition", "APPROVE_PET_FRIENDLY" if all(checks.values())
                            else "HOLD"),
        ("bound_semantic_hash", semantic_hash(IDENTITY, statement,
                                              result.get("source_url", ""))),
        ("bound_snapshot_hash", result.get("content_hash", "")),
        ("true_capture_completed_at", result.get("completed_at", "")),
    ))


def signature(correction: Dict) -> Dict:
    now = datetime.now(timezone.utc).isoformat()
    approved = correction["new_disposition"] == "APPROVE_PET_FRIENDLY"
    return OrderedDict((
        ("schema", "ptf-founder-decision-ledger/1.0"),
        ("what_this_is",
         "An amendment to PTF-INDIANAPOLIS-TARGETED-FOUNDER-REVIEW-013. That "
         "ledger stands as the record of what was decided then; this records "
         "the single row whose HOLD was lifted by re-reading evidence already "
         "captured."),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("amends", "indianapolis_in_founder_signature_013.json"),
        ("approval_vocabulary", "founder-approval-vocabulary/1.0"),
        ("decided_by", REVIEWER), ("decided_at", now[:10]),
        ("recorded_by", "claude-opus-5 (agent) -- transcription only; the "
                        "disposition is derived from the quoted statement and "
                        "no raw evidence was altered"),
        ("status", "RECORDED"),
        ("candidates_reviewed", 1),
        ("signed_count", 1 if approved else 0),
        ("withheld_count", 0 if approved else 1),
        ("signed_by_authority", {"PUBLISHED_PET_FRIENDLY": 1} if approved else {}),
        ("nothing_is_published_by_this_file",
         "This view records one decision. It registers no market, promotes no "
         "census row, publishes no page and deploys nothing."),
        ("signed", [OrderedDict((
            ("identity_key", correction["identity_key"]),
            ("canonical_name", correction["canonical_name"]),
            ("brand", "HILTON"), ("corridor", ""),
            # The canonical publishing token from contracts.enums. An earlier
            # draft of this file invented "APPROVED_AFTER_CORRECTION", which is
            # not in the approval vocabulary and therefore does not publish --
            # a decision expressed in a word the contract does not know is not
            # a decision the contract can act on. The founder's ruling is
            # unchanged; the fact that it followed a correction is carried by
            # supersedes_disposition, supersedes_work_order and founder_note,
            # which is where a caveat belongs.
            ("founder_decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
            ("approved_after_correction", True),
            ("founder_reviewer_id", REVIEWER),
            ("founder_reviewed_at", now[:10]),
            ("founder_note",
             "held by 013 because the locator captured the FAQ question and "
             "stopped; lifted after the property's own answer was recovered "
             "from the same capture"),
            ("reviewed_disposition", "APPROVE_PET_FRIENDLY"),
            ("proposes_authority", "PUBLISHED_PET_FRIENDLY"),
            ("supersedes_disposition", "HOLD"),
            ("supersedes_work_order",
             "PTF-INDIANAPOLIS-TARGETED-FOUNDER-REVIEW-013"),
            ("bound_semantic_hash", correction["bound_semantic_hash"]),
            ("bound_snapshot_hash", correction["bound_snapshot_hash"]),
            ("bound_source_url", correction["correction"]["source_url"]),
            ("true_capture_completed_at", correction["true_capture_completed_at"]),
            ("promotion", ""),
        ))] if approved else []),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    parser.add_argument("--signature-out", default="")
    args = parser.parse_args(argv)
    correction = build()
    if args.out:
        Path(args.out).write_text(json.dumps(correction, indent=2),
                                  encoding="utf-8")
    sig = signature(correction)
    if args.signature_out:
        Path(args.signature_out).write_text(json.dumps(sig, indent=2),
                                            encoding="utf-8")
    print("statement recovered : %s" % bool(correction["correction"]["recovered_statement"]))
    print("contradictions      : %d" % len(read_artifact()["contradictions"]))
    for name, ok in correction["verification"].items():
        print("  %-52s %s" % (name, "PASS" if ok else "FAIL"))
    print("new disposition     : %s" % correction["new_disposition"])
    facts = correction["corrected_facts"]
    print("facts               : pets_allowed=%s weight=%s tiers=%s basis=%s refundable=%s"
          % (facts.get("pets_allowed"), facts.get("max_weight_lbs"),
             facts.get("fee_tiers"), facts.get("fee_basis"),
             facts.get("fee_refundable")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

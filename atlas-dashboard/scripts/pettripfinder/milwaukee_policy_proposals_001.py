"""PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 -- structured proposals.

Turns the durable acquisition journal into schema-1.2-shaped policy PROPOSALS
and a run report. It publishes nothing, approves nothing, and writes no
authority: the output is a founder-review packet.

Why this is a projection and not an interpretation
--------------------------------------------------
Every fact here was already produced by the proven reading path -- the router
stored ``document.observation`` built by the pilots' own ``build_observation``,
which is where schema 1.2 is enforced. This module reshapes those records for
review and re-asserts the frozen rules as gates. It never reads a page, never
fills a gap, and never turns an absence into a value.

The frozen semantics it re-checks per proposal:

* ``per_day`` is not ``per_night``; ``fee_basis`` is one of per_night/per_day/
  per_stay and ``fee_scope`` is a separate field.
* unknown is ABSENCE. A withheld field appears in ``withheld_fields`` with a
  reason and is absent from the facts, never present as null or "unknown".
* nothing is inferred: species, refundability, fee scope, fee basis, weight
  scope and reservation requirement are only present when the source said them.
* a generic "pets welcome" is not dogs + cats.
* an individual weight limit is not a combined one.
* service-animal statements stay outside the pet-policy facts.
* a missing policy is not a no-pets policy.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Mapping, Optional

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

MARKET = "milwaukee-wi"
WORK_ORDER = "PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
JOURNAL = (REPO / "data" / "acquisition" / "milwaukee-router-001"
           / "milwaukee-router-001" / "journal.jsonl")

PUBLICATION_GRADE = "ACQUIRED_PUBLICATION_GRADE"

#: Facts that may never be inferred. Present only if the source stated them.
NEVER_INFERRED = ("species", "refundable", "fee_scope", "fee_basis",
                  "weight_scope", "reservation_required")
VALID_FEE_BASES = {"per_night", "per_day", "per_stay"}


def read_journal() -> List[Dict]:
    if not JOURNAL.exists():
        return []
    return [json.loads(line) for line in
            JOURNAL.read_text(encoding="utf-8").splitlines() if line.strip()]


def _gate(extraction: Dict, withheld: Dict) -> List[str]:
    """Frozen-semantics violations in one extraction. Empty is the good case."""
    problems: List[str] = []

    fee = extraction.get("pet_fee") or {}
    if isinstance(fee, dict) and fee:
        basis = fee.get("basis")
        if basis is not None and basis not in VALID_FEE_BASES:
            problems.append("pet_fee.basis %r is outside the frozen set" % basis)
        # per_day and per_night are different words the source chose; a
        # proposal that silently renames one to the other is a semantic edit.
        if "basis" in fee and "scope" in fee and fee.get("scope") == fee.get("basis"):
            problems.append("pet_fee scope and basis collapsed into one value")

    for key in NEVER_INFERRED:
        if key in extraction and extraction[key] in (None, "", "unknown", "unstated"):
            problems.append("%s is present but empty; unknown must be ABSENCE" % key)

    for key, value in extraction.items():
        if value in (None, "unknown", "unstated"):
            problems.append("%s carries a sentinel rather than being absent" % key)

    overlap = sorted(set(withheld) & set(extraction))
    if overlap:
        problems.append("withheld and asserted at once: %s" % overlap)

    weight = extraction.get("weight_limit") or {}
    combined = extraction.get("combined_weight_limit") or {}
    if weight and combined and weight == combined:
        problems.append("individual and combined weight limits are the same object")

    return problems


def _is_refusal(extraction: Dict) -> bool:
    """A captured no-pets finding.

    Kept OUT of the violations list on purpose. A refusal is not a malformed
    record -- it is a legitimate, well-formed finding that happens to need a
    different reviewer decision, because turning it into a VERIFIED_NO_PETS
    exclusion is a publication act this work order may not take. Filing it as
    a "semantic violation" would slander 19 correct captures and hide the real
    violation count, which is zero.
    """
    return extraction.get("pets_allowed") is False


#: Review states a row can hold, beyond ready and refusal. Added by
#: PTF-MILWAUKEE-OBSERVATION-STORE-INTEGRATION-025, because a row can be
#: publication grade at ACQUISITION level and still not be something a founder
#: should be handed: a fee the schema cannot carry, a surface that published no
#: terms, or two production observations that disagree. Calling any of those
#: FOUNDER_REVIEW_READY would promote a row on the strength of how it was
#: fetched rather than what it says.
HELD_SCHEMA = "HELD_SCHEMA_CANNOT_REPRESENT"
HELD_INSUFFICIENT = "HELD_INSUFFICIENT_EVIDENCE"
HELD_CONFLICT = "CURRENT_STATE_CONFLICT"


def _review_status(problems: List[str], refusal: bool, extraction: Mapping,
                   withheld: Mapping, entry: Mapping) -> str:
    """What a reviewer should be told this row is.

    Ordered by how much it stops a human acting: a frozen-semantics violation
    and a conflict are defects; a schema-unrepresentable fee is a real policy
    nobody can publish as one field; a surface with no terms is a fact about
    the hotel. A refusal is reviewable and complete, so it keeps its own state.
    """
    if problems:
        return "HELD_SEMANTIC_REVIEW"
    if entry.get("_conflict"):
        return HELD_CONFLICT
    reasons = set(withheld.values())
    if "SCHEMA_CANNOT_REPRESENT" in reasons:
        return HELD_SCHEMA
    if refusal:
        return "REFUSAL_FOUNDER_REVIEW"
    if "ARTIFACT_INSUFFICIENT" in reasons or not extraction:
        return HELD_INSUFFICIENT
    # A bare allowed-flag is not a policy. Added by
    # PTF-MILWAUKEE-FINAL-ACQUISITION-PASS-026: three Motel 6 captures asserted
    # pets_allowed from a block of page chrome -- ratings, a phone number, a
    # nightly rate -- and one Red Roof capture carried nothing but a
    # service-animal sentence. All four would have been handed to a founder as
    # ready. A guest learns nothing from either, and a service-animal statement
    # is a legal obligation rather than a pet policy.
    substantive = set(extraction) - {"pets_allowed", "pets_allowed_quote",
                                     "service_animal_exception",
                                     "service_animal_statement"}
    if not substantive:
        return HELD_INSUFFICIENT
    return "FOUNDER_REVIEW_READY"


def build(rederived: Optional[Mapping] = None, write: bool = True,
          extra_entries: Optional[List[Dict]] = None) -> Dict:
    """Project the journal -- and any explicitly supplied production sources --
    into proposals.

    ``rederived`` maps identity_key -> a re-derived reading of that record's own
    persisted evidence block, supplied by a work order authorised to re-derive
    one. It replaces the READING and nothing else: identity, provenance,
    publication status and review status are still computed from the journal
    exactly as before. Passing nothing reproduces the original output byte for
    byte, which is what makes this seam safe to leave in place.
    """
    rederived = dict(rederived or {})
    # ``extra_entries`` carries production observations from Milwaukee runs
    # OTHER than milwaukee-router-001, in the same entry shape read_journal
    # returns. Added by PTF-MILWAUKEE-OBSERVATION-STORE-INTEGRATION-025: this
    # store was a projection of one journal, which is why seventeen Marriott,
    # eleven Hilton and sixteen earlier-run observations had no current row.
    # The caller decides which runs are eligible and which observation wins per
    # identity; this function still owns the shaping, the frozen-semantics gate
    # and the review status, so every row is gated by one code path. Passing no
    # extras reproduces the original output exactly.
    entries = read_journal() + list(extra_entries or [])
    states = Counter(e["final_state"] for e in entries)

    proposals: List[Dict] = []
    rejected: List[Dict] = []
    for entry in entries:
        if entry["final_state"] != PUBLICATION_GRADE:
            continue
        doc = (entry.get("result") or {}).get("document") or {}
        obs = doc.get("observation") or {}
        extraction = dict(obs.get("extraction") or {})
        withheld = dict(doc.get("withheld_fields") or {})
        non_inferences = list(doc.get("non_inferences") or ())
        evidence = list(obs.get("evidence") or ())
        supersession = None
        update = rederived.get(entry["identity_key"])
        if update:
            # The previous reading is not discarded: it is carried here, on the
            # row it replaced, so a proposal says what it used to say and which
            # reader changed its mind.
            supersession = {
                "superseded_by": update["work_order"],
                "reader_commit": update["reader_commit"],
                "evidence_block_path": update["evidence_block_path"],
                "evidence_block_sha256": update["evidence_block_sha256"],
                "previous_facts": extraction,
                "previous_withheld_fields": withheld,
            }
            extraction = dict(update["extraction"])
            withheld = dict(update["withheld"])
            non_inferences = list(update["non_inferences"])
            evidence = list(update["evidence"])
        problems = _gate(extraction, withheld)
        refusal = _is_refusal(extraction)

        proposal = {
            "identity_key": entry["identity_key"],
            "canonical_name": entry["canonical_name"],
            "market_id": MARKET,
            "brand": entry["brand"],
            "policy_schema_version": "1.2",
            "proposed_facts": extraction,
            "withheld_fields": withheld,
            "non_inferences": non_inferences,
            "evidence": [
                {"quote": item.get("quote", ""),
                 "location": item.get("location", ""),
                 "field_refs": list(item.get("field_refs") or ())}
                for item in evidence],
            "service_animal_statement": extraction.get("service_animal_statement", ""),
            "provenance": {
                "source_url": doc.get("source_url", ""),
                "final_url": doc.get("final_url", ""),
                "authority_tier": obs.get("authority_tier", ""),
                "source_type": obs.get("source_type", ""),
                "retrieved_at": obs.get("retrieved_at", ""),
                "capture_method": doc.get("capture_method", ""),
                "provider": doc.get("provider", ""),
                "reader": doc.get("reader", ""),
                "snapshot_hash": obs.get("snapshot_hash", ""),
                "raw_pointer": obs.get("raw_pointer", ""),
                "obs_id": obs.get("obs_id", ""),
            },
            "publication_grade": (doc.get("publication_grade") or {}).get("verdict", ""),
            "identity_check": obs.get("identity_check") or {},
            "source_run": entry.get("source_run", "milwaukee-router-001"),
            "frozen_semantics_violations": problems,
            "is_refusal": refusal,
            # The two facts this whole work order turns on.
            "published": False,
            "founder_approved": False,
            "rederivation": supersession,
            "review_status": _review_status(problems, refusal, extraction,
                                            withheld, entry),
        }
        (rejected if problems else proposals).append(proposal)

    ready = [p for p in proposals if p["review_status"] == "FOUNDER_REVIEW_READY"]
    refusals = [p for p in proposals if p["review_status"] == "REFUSAL_FOUNDER_REVIEW"]
    held_states = Counter(p["review_status"] for p in proposals + rejected)
    doc = {
        "schema": "ptf-milwaukee-policy-proposals/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "note": (
            "Structured proposals only. Nothing here is published and nothing "
            "is approved: published=false and founder_approved=false on every "
            "row, no policy authority file exists for this market, and the "
            "market's three authority shards are untouched. Each proposal "
            "carries the exact contiguous quotes its facts rest on, the fields "
            "the source was silent about, and the inferences that were "
            "deliberately NOT made."),
        "policy_schema_version": "1.2",
        "authority_written": False,
        "founder_approvals_created": 0,
        "source_runs": sorted({e.get("source_run", "milwaukee-router-001")
                               for e in entries}),
        "acquisition_state_counts": dict(states),
        "publication_grade_total": states.get(PUBLICATION_GRADE, 0),
        "proposal_total": len(proposals) + len(rejected),
        "founder_review_ready": len(ready),
        "refusal_founder_review": len(refusals),
        "held_semantic_review": len(rejected),
        "review_status_counts": dict(held_states),
        "refusal_note": (
            "A captured refusal is a finding, not an exclusion. Nothing here "
            "creates a VERIFIED_NO_PETS record: that is a founder decision and "
            "a publication act, and this work order takes neither. Each refusal "
            "carries the exact quote it rests on so the decision is reviewable."),
        "items": proposals + rejected,
    }
    if write:
        out = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
        out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                        .encode("utf-8"))
    return doc


def main() -> int:
    doc = build()
    print("acquisition states     : %s" % doc["acquisition_state_counts"])
    print("publication-grade      : %d" % doc["publication_grade_total"])
    print("proposals              : %d" % doc["proposal_total"])
    print("  founder-review ready : %d" % doc["founder_review_ready"])
    print("  held semantic review : %d" % doc["held_semantic_review"])
    print("authority written      : %s" % doc["authority_written"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

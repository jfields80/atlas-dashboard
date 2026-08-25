"""PTF-MILWAUKEE-FOUNDER-DECISION-036 -- record the founder's decisions.

RECORDS what the founder decided, and applies nothing on its own. The ledger it
writes is the founder's answer sitting beside the question 036 asked, bound to
the exact hashes the committed review package showed them.

WHY THE LEDGER IS ITS OWN FILE
------------------------------
``founder_review_036`` regenerates its package, so a decision written into the
package could be erased by a re-run. Dayton learned this and split the two:
the generated question and the human answer live in separate files, and nothing
that regenerates can destroy an attestation.

ATTRIBUTION
-----------
``decided_by`` is the founder, because the founder gave these decisions
explicitly and in writing. That is the only circumstance in which their name
may appear on a decision. This module never infers a ruling, never fills a
default, and fails closed if asked to record a decision it was not given: the
bulk cohort is DERIVED from the package's own mechanical verdict rather than
listed, so it cannot quietly include a row the founder was not shown, and the
five individual rulings are transcribed one by one from their message.

WHAT THE FOUNDER SAID
---------------------
Verbatim, in ``DECISION_ORDER`` below. In summary: approve the 93 mechanically
clean candidates exactly as proposed; approve the three Wyndham refusals whose
quote reads "no other pets", on the strength of the full evidence context and
explicitly not the isolated phrase; and HOLD Hyatt Regency and Saint Kate,
declining to authorise an inference from a priced pet policy to
``pets_allowed = true``.

Run:
  python -m scripts.pettripfinder.acquisition.founder_decisions_036 [--record]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import founder_review_036 as F   # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-FOUNDER-DECISION-036"
REVIEW_WORK_ORDER = F.WORK_ORDER
MARKET = F.MARKET

#: The founder. Their name appears here because they gave these decisions
#: explicitly and in writing, in the decision order quoted below.
FOUNDER = "jfields80"
DECIDED_AT = "2026-08-21"
RECORDED_BY = ("claude-opus-5 (%s, agent) -- transcription only; the decisions "
               "are the founder's, and no ruling was inferred, defaulted or "
               "completed by the agent" % WORK_ORDER)

#: The founder's instruction, kept verbatim so a reader can check the
#: transcription against the source rather than trusting it.
DECISION_ORDER = """PTF-MILWAUKEE-FOUNDER-DECISION-036

I explicitly approve the 93 mechanically clean Milwaukee founder-review
candidates exactly as proposed in:

launch_packages/pettripfinder/milwaukee_founder_review_036/

This approval is limited to the records bound to the record_hash and
evidence_hash values in that committed review package.

I additionally make the following individual decisions:

APPROVE_REFUSAL:
- Baymont Mequon
- Days Inn West Allis
- Super 8 Airport

Reason:
The complete first-party evidence states that ADA-defined service animals are
welcome and that no other pets are allowed. I approve these as verified
no-pets/refusal records based on the full evidence context, not the isolated
phrase "no other pets."

HOLD:
- Hyatt Regency Milwaukee
- Saint Kate

Reason:
These properties publish priced pet-policy information, but the current
evidence does not explicitly state pets_allowed=true in the manner required by
the frozen PTF evidence contract. I am not authorizing an inference from a
priced pet policy to pets_allowed=true in this decision.

TOTAL EXPLICIT FOUNDER DECISIONS:

APPROVED PET-FRIENDLY: 70
APPROVED REFUSAL: 26
HELD: 2

TOTAL APPROVED: 96
TOTAL HELD FROM THE 98-ROW REVIEW COHORT: 2"""

APPROVE = "APPROVE"
APPROVE_REFUSAL = "APPROVE_REFUSAL"
HOLD = "HOLD"

#: The bulk ruling, as the founder framed it: the mechanically clean cohort,
#: exactly as proposed. Derived from the package rather than enumerated -- a
#: hand-listed cohort could include a row the founder was never shown.
BULK_RULING = ("the 93 mechanically clean candidates, approved exactly as the "
               "committed package proposed them")

#: The five the package refused to recommend, decided one at a time. Each is
#: named here by the founder's own shorthand and resolved to exactly one
#: candidate; a shorthand that matched two rows would fail closed.
INDIVIDUAL_RULINGS: Tuple[Tuple[str, str, str], ...] = (
    ("Baymont Mequon", APPROVE_REFUSAL,
     "the complete first-party evidence states that ADA-defined service "
     "animals are welcome and that no other pets are allowed; approved as a "
     "verified no-pets record on the full evidence context, not the isolated "
     "phrase \"no other pets\""),
    ("Days Inn West Allis", APPROVE_REFUSAL,
     "the complete first-party evidence states that ADA-defined service "
     "animals are welcome and that no other pets are allowed; approved as a "
     "verified no-pets record on the full evidence context, not the isolated "
     "phrase \"no other pets\""),
    ("Super 8 Airport", APPROVE_REFUSAL,
     "the complete first-party evidence states that ADA-defined service "
     "animals are welcome and that no other pets are allowed; approved as a "
     "verified no-pets record on the full evidence context, not the isolated "
     "phrase \"no other pets\""),
    ("Hyatt Regency Milwaukee", HOLD,
     "the property publishes priced pet-policy information, but the current "
     "evidence does not explicitly state pets_allowed=true in the manner the "
     "frozen PTF evidence contract requires; no inference from a priced pet "
     "policy to pets_allowed=true is authorised by this decision"),
    ("Saint Kate", HOLD,
     "the property publishes priced pet-policy information, but the current "
     "evidence does not explicitly state pets_allowed=true in the manner the "
     "frozen PTF evidence contract requires; no inference from a priced pet "
     "policy to pets_allowed=true is authorised by this decision"),
)

#: The totals the founder stated. Asserted, not assumed: if the package does
#: not produce exactly these numbers, the transcription is wrong and nothing
#: is written.
STATED_TOTALS = {"approved_pet_friendly": 70, "approved_refusal": 26,
                 "held": 2, "approved": 96, "cohort": 98}

LEDGER = F.LEDGER


class TranscriptionError(RuntimeError):
    """The decision order cannot be transcribed exactly as given."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def committed_package() -> Dict:
    """The package the founder read, as committed. Never regenerated here."""
    return json.loads(F.REVIEW_JSON.read_text(encoding="utf-8"))


def resolve(shorthand: str, candidates: Sequence[Mapping]) -> Dict:
    """The one candidate a founder's shorthand names, or an error.

    Fails closed on purpose. "Super 8 Airport" naming two hotels is not a
    decision about either of them, and guessing which one the founder meant is
    exactly the inference this module exists not to make.
    """
    import re
    tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9]+", shorthand)]
    matches = [row for row in candidates
               if all(token in row["identity_key"] for token in tokens)]
    if len(matches) != 1:
        raise TranscriptionError(
            "%r matches %d candidates (%s); a decision must name exactly one"
            % (shorthand, len(matches),
               ", ".join(row["identity_key"] for row in matches) or "none"))
    return matches[0]


def decisions() -> List[Dict]:
    """Every decision, transcribed and bound to the committed hashes."""
    package = committed_package()
    candidates = package["candidates"]
    by_key = {row["identity_key"]: row for row in candidates}

    individual: Dict[str, Tuple[str, str, str]] = {}
    for shorthand, ruling, reason in INDIVIDUAL_RULINGS:
        row = resolve(shorthand, candidates)
        if row["proposed_decision"] != F.PROPOSE_INDIVIDUAL:
            raise TranscriptionError(
                "%r was not one of the rows the package sent to individual "
                "review; the founder ruled on a different question"
                % row["identity_key"])
        if row["identity_key"] in individual:
            raise TranscriptionError("%r was ruled on twice" % shorthand)
        individual[row["identity_key"]] = (shorthand, ruling, reason)

    out: List[Dict] = []
    for row in candidates:
        key = row["identity_key"]
        if key in individual:
            shorthand, ruling, reason = individual[key]
            basis = ("an individual ruling in the decision order, naming this "
                     "property as %r" % shorthand)
        elif row["proposed_decision"] == F.PROPOSE_INDIVIDUAL:
            raise TranscriptionError(
                "%r was sent to individual review and the decision order does "
                "not rule on it" % key)
        else:
            ruling = (APPROVE_REFUSAL
                      if row["proposed_decision"] == F.PROPOSE_APPROVE_REFUSAL
                      else APPROVE)
            reason = ("approved exactly as the committed package proposed it, "
                      "under the founder's bulk ruling")
            basis = BULK_RULING
        out.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("review_state", row["review_state"]),
            ("proposed", row["proposed_decision"]),
            ("decision", ruling),
            ("decision_basis", basis),
            ("reason", reason),
            ("decided_by", FOUNDER),
            ("decided_at", DECIDED_AT),
            ("record_hash", row["record_hash"]),
            ("evidence_hash", row["evidence_hash"]),
        ]))
    return out


def counts() -> Dict:
    rows = decisions()
    package = {row["identity_key"]: row for row in committed_package()["candidates"]}
    approved_pet_friendly = sum(
        1 for row in rows if row["decision"] == APPROVE)
    approved_refusal = sum(1 for row in rows
                           if row["decision"] == APPROVE_REFUSAL)
    held = sum(1 for row in rows if row["decision"] == HOLD)
    return {
        "cohort": len(rows),
        "approved_pet_friendly": approved_pet_friendly,
        "approved_refusal": approved_refusal,
        "approved": approved_pet_friendly + approved_refusal,
        "held": held,
        "bulk_ruling_rows": sum(1 for row in rows
                                if row["decision_basis"] == BULK_RULING),
        "individually_ruled_rows": sum(
            1 for row in rows if row["decision_basis"] != BULK_RULING),
    }


def assert_matches_the_decision_order() -> Dict:
    """The founder stated their own totals. If the package does not produce
    exactly those numbers, the transcription is wrong and nothing is written."""
    measured = counts()
    mismatches = {key: (STATED_TOTALS[key], measured[key])
                  for key in STATED_TOTALS
                  if measured.get(key) != STATED_TOTALS[key]}
    if mismatches:
        raise TranscriptionError(
            "the decision order states totals the package does not produce: %s"
            % ", ".join("%s stated %d, measured %d" % (key, stated, got)
                        for key, (stated, got) in sorted(mismatches.items())))
    return measured


def ledger_document() -> Dict:
    measured = assert_matches_the_decision_order()
    rows = decisions()
    return OrderedDict([
        ("schema", "ptf-milwaukee-founder-decisions/1.0"),
        ("work_order", WORK_ORDER),
        ("review_work_order", REVIEW_WORK_ORDER),
        ("market_id", MARKET),
        ("decided_by", FOUNDER),
        ("decided_at", DECIDED_AT),
        ("recorded_by", RECORDED_BY),
        ("recorded_at", _now()),
        ("status", "RECORDED"),
        ("what_recorded_means", (
            "The founder's rulings are on file and bound to the exact hashes "
            "the committed review package showed them. A decision recorded "
            "against a record that has since moved does not bind, and the "
            "application step re-checks every hash before it writes an "
            "approval.")),
        ("why_a_separate_file_from_the_package", (
            "The review package is emitted by an idempotent generator, so "
            "re-running it would overwrite anything written into it. A human "
            "attestation must not live somewhere a regeneration can erase.")),
        ("source_package", OrderedDict([
            ("path", F.REVIEW_JSON.relative_to(REPO).as_posix()),
            ("sha256", F._sha256_file(F.REVIEW_JSON)),
            ("commit", F._git("rev-parse", "HEAD")),
        ])),
        ("decision_order", DECISION_ORDER),
        ("counts", measured),
        ("decisions", rows),
    ])


def record(write: bool = False) -> Dict:
    doc = ledger_document()
    if write:
        LEDGER.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--record", action="store_true",
                        help="write the ledger")
    args = parser.parse_args(argv)
    doc = record(write=args.record)
    print(json.dumps(doc["counts"], indent=2))
    print("ledger %s: %s" % ("written" if args.record else "NOT written",
                             LEDGER.relative_to(REPO).as_posix()))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())

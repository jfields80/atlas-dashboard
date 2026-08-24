"""PTF-MILWAUKEE-FOUNDER-DECISION-040 -- the founder's answers to 039's six.

039 put six rows in front of a person with an advisory verdict on each. This
records what the person actually said, and only that. The verdicts 039
recommended are not consulted anywhere in this module: a machine's opinion is
not evidence that a founder agreed with it, and a ledger that quietly used the
recommendation when the answer was missing would be a ledger that approves
things nobody approved.

The founder's order is transcribed verbatim below and asserted against the
decisions this module records. If the two ever disagree, the module refuses to
produce a ledger at all.

BOUND UNDER semantic-approval/1.0
----------------------------------
Each decision carries the semantic hash of the exact candidate the founder was
shown, computed by the contract 039 introduced. A later reader repair that
changes how a reading is produced will not withdraw these approvals; a change
to what they SAY still will.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import approval_binding as AB                     # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F36      # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_039 as V39      # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-FOUNDER-DECISION-040"
MARKET = "milwaukee-wi"

#: The human who made these decisions. Never inferred, never defaulted, and
#: never this assistant.
FOUNDER = "jfields80"

#: The founder's decision date. A clock reading here would make every rebuild
#: of the authority a diff and its sha256 unpinnable -- the defect 037 hit.
DECIDED_AT = "2026-08-22T12:00:00-05:00"

LEDGER = F36.PKG / "milwaukee_founder_decisions_040.json"

NEWLINE = chr(10)

APPROVE = "APPROVE"
APPROVE_REFUSAL = "APPROVE_REFUSAL"
HOLD = "HOLD"
DECISIONS = (APPROVE, APPROVE_REFUSAL, HOLD)

#: The founder's order, transcribed. Asserted against what this module records
#: so a later edit to either half cannot drift from the other in silence.
DECISION_ORDER = """PTF-MILWAUKEE-FOUNDER-DECISION-040

1. Country Inn & Suites by Radisson, Brown Deer - Milwaukee North
   DECISION: APPROVE

2. Country Inn & Suites by Radisson, Milwaukee West (Brookfield)
   DECISION: APPROVE

3. Econo Lodge Milwaukee Airport
   DECISION: APPROVE_REFUSAL

4. Knickerbocker on the Lake
   DECISION: HOLD

5. Saint Kate - The Arts Hotel
   DECISION: APPROVE

6. The Iron Horse Hotel
   DECISION: HOLD
"""

#: Shorthand as the founder wrote it -> the decision. Resolution against the
#: committed 039 package is done by ``resolve``, which fails closed rather
#: than picking a best match.
ANSWERS: Sequence = (
    ("Country Inn & Suites by Radisson, Brown Deer", APPROVE),
    ("Country Inn & Suites by Radisson, Milwaukee West", APPROVE),
    ("Econo Lodge Milwaukee Airport", APPROVE_REFUSAL),
    ("Knickerbocker on the Lake", HOLD),
    ("Saint Kate", APPROVE),
    ("The Iron Horse Hotel", HOLD),
)

#: Why each hold is a hold, in the founder's own terms. A hold with no reason
#: is indistinguishable from an unanswered row six months from now.
HOLD_REASONS = {
    "knickerbocker on the lake":
        "the first-party policy subpage carries real pet language but the "
        "identity gate declined the evidence; the founder will not bypass the "
        "gate by hand, and the row waits for a generic subpage-binding "
        "solution",
    "the iron horse hotel":
        "the first-party policy subpage carries real pet language but the "
        "identity gate declined the evidence; the founder will not bypass the "
        "gate by hand, and the row waits for a generic subpage-binding "
        "solution",
}


class DecisionError(RuntimeError):
    """Raised rather than guessing. Every caller here fails closed."""


def committed_package() -> Dict:
    if not V39.REVIEW_JSON.is_file():
        raise DecisionError(
            "the 039 review package is not committed; a decision must bind to "
            "the exact rows the founder was shown, not to a package rebuilt "
            "after the fact")
    return json.loads(V39.REVIEW_JSON.read_text(encoding="utf-8"))


def resolve(shorthand: str, candidates: Sequence[Mapping]) -> Dict:
    """One candidate, or an error. Never a best guess.

    A shorthand that matches two rows is an ambiguity, and an ambiguous
    approval is the one kind this repository must never resolve on its own --
    the two Country Inn properties differ by a single word.
    """
    needle = shorthand.lower()
    hits = [row for row in candidates
            if needle in row["property_name"].lower()]
    if len(hits) == 1:
        return hits[0]
    raise DecisionError(
        "%r matches %d candidates (%s); a founder decision must name exactly "
        "one row" % (shorthand, len(hits),
                     ", ".join(row["property_name"] for row in hits) or "none"))


def semantic_record(candidate: Mapping) -> Dict:
    """The candidate as a record the binding contract can hash.

    Built from the committed 039 package rather than from a fresh derivation:
    the hash must describe what the founder READ, and a value re-derived today
    is a different claim about the same page.
    """
    from scripts.pettripfinder.acquisition import authority_build_040 as A40
    return A40.semantic_row(candidate)


def decisions() -> List[Dict]:
    package = committed_package()
    candidates = package["candidates"]
    out: List[Dict] = []
    seen: List[str] = []
    for shorthand, verdict in ANSWERS:
        candidate = resolve(shorthand, candidates)
        key = candidate["identity_key"]
        if key in seen:
            raise DecisionError("%s appears twice in the founder's order" % key)
        seen.append(key)
        record = semantic_record(candidate)
        out.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", candidate["property_name"]),
            ("decision", verdict),
            ("decided_by", FOUNDER),
            ("decided_at", DECIDED_AT),
            ("decision_basis", "explicit written founder decision, "
                               "PTF-MILWAUKEE-FOUNDER-DECISION-040"),
            ("reason", HOLD_REASONS.get(key, "")
             or "the founder approved the candidate as presented in the 039 "
                "review package"),
            # Lineage back to the row the founder actually saw.
            ("candidate_work_order", V39.WORK_ORDER),
            ("candidate_package", V39.REVIEW_JSON.name),
            ("prior_review_status", candidate["status"]),
            ("originating_work_order", "PTF-MILWAUKEE-IDENTITY-RESOLUTION-"
                                       "AND-FULL-CLOSURE-038"),
            ("machine_recommended", candidate["recommended_machine_verdict"]),
            ("agrees_with_machine",
             candidate["recommended_machine_verdict"] == verdict),
            ("source_url", candidate["source_url"]),
            ("evidence_origin", candidate["evidence_origin"]),
            ("run_id", candidate["run_id"]),
            ("run_kind", candidate["run_kind"]),
            ("attempt_dir", candidate["attempt_dir"]),
            ("evidence_quote", candidate["evidence_quote"]),
            ("identity_status", candidate["identity_status"]),
            # The binding.
            ("binding_contract", AB.BINDING_CONTRACT_VERSION),
            ("semantic_hash", AB.semantic_hash(record)),
        ]))
    return out


def assert_matches_the_decision_order() -> Dict:
    """The transcript and the records must say the same thing."""
    written = []
    for line in DECISION_ORDER.splitlines():
        stripped = line.strip()
        if stripped.startswith("DECISION:"):
            written.append(stripped.split(":", 1)[1].strip())
    recorded = [row["decision"] for row in decisions()]
    if written != recorded:
        raise DecisionError(
            "the transcribed order says %s and the ledger records %s"
            % (written, recorded))
    return {"decisions_in_order": written}


def counts() -> Dict:
    rows = decisions()
    return {
        "total": len(rows),
        "by_decision": dict(Counter(row["decision"] for row in rows)),
        "agreeing_with_the_machine": sum(1 for row in rows
                                         if row["agrees_with_machine"]),
        "overriding_the_machine": sum(1 for row in rows
                                      if not row["agrees_with_machine"]),
    }


def assert_writable() -> List[Dict]:
    """Every condition the work order says must stop a write."""
    package = committed_package()
    candidates = package["candidates"]
    if len(candidates) != V39.EXPECTED_CANDIDATES:
        raise DecisionError("the 039 package holds %d candidates, not %d"
                            % (len(candidates), V39.EXPECTED_CANDIDATES))
    rows = decisions()
    if len(rows) != V39.EXPECTED_CANDIDATES:
        raise DecisionError("%d decisions for %d candidates"
                            % (len(rows), len(candidates)))

    keys = [row["identity_key"] for row in rows]
    if len(set(keys)) != len(keys):
        raise DecisionError("a candidate is decided twice: %s" % keys)
    undecided = sorted({row["identity_key"] for row in candidates} - set(keys))
    if undecided:
        raise DecisionError("no decision for %s" % undecided)
    for row in rows:
        if row["decision"] not in DECISIONS:
            raise DecisionError("%s: %r is not a decision"
                                % (row["identity_key"], row["decision"]))

    # The hash binding must match the package the founder was shown. A
    # candidate that has moved since is not the candidate they answered.
    for row, candidate in zip(rows, [resolve(name, candidates)
                                     for name, _ in ANSWERS]):
        if row["evidence_quote"] != candidate["evidence_quote"]:
            raise DecisionError("%s: the evidence has moved since the 039 "
                                "package was written" % row["identity_key"])
        if row["source_url"] != candidate["source_url"]:
            raise DecisionError("%s: the source URL has moved since the 039 "
                                "package was written" % row["identity_key"])
    assert_matches_the_decision_order()
    return rows


def ledger_document() -> Dict:
    rows = assert_writable()
    return OrderedDict([
        ("schema", "ptf-founder-decision-ledger/2.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("what_this_is",
         "The founder's explicit answers to the six candidates "
         "PTF-...-APPROVAL-BINDING-039 put in front of them. This ledger is "
         "ADDITIVE: the 036 ledger is untouched and remains the record of "
         "what was decided then."),
        ("decided_by", FOUNDER),
        ("decided_at", DECIDED_AT),
        ("binding_contract", AB.BINDING_CONTRACT_VERSION),
        ("supersedes_nothing",
         "036's decision ledger is historical authority and is not modified, "
         "reinterpreted or re-derived by this file."),
        ("candidate_package", V39.REVIEW_JSON.name),
        ("candidate_work_order", V39.WORK_ORDER),
        ("decision_order_transcript", DECISION_ORDER),
        ("counts", counts()),
        ("decisions", rows),
    ])


def load_ledger() -> Dict:
    if not LEDGER.is_file():
        raise DecisionError("the 040 decision ledger has not been recorded")
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def record(write: bool = False) -> Dict:
    doc = ledger_document()
    if write:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(
            json.dumps(doc, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
    return {k: v for k, v in doc.items()
            if k not in ("decisions", "decision_order_transcript")}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps(record(write=False), indent=2, default=str))
    if args.list:
        for row in decisions():
            print("%-46s %-16s (machine said %s)"
                  % (row["canonical_name"][:46], row["decision"],
                     row["machine_recommended"]))
    if args.record:
        print(json.dumps(record(write=True), indent=2, default=str))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())

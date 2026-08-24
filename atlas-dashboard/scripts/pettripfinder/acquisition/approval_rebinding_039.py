"""PTF-MILWAUKEE-FOUNDER-REVIEW-AND-APPROVAL-BINDING-039 -- rebind, do not re-ask.

036 bound each founder decision to a ``record_hash`` over the whole store row
and an ``evidence_hash`` over its citations. The rule was right: a decision
must stop applying the moment the record moves. The SCOPE was wrong. A store
row also carries how its reading was produced, and one of those fields --
``rederivation.reader_commit`` -- is re-derived on every projection.

038 measured the cost. Repairing a reader defect and re-projecting the store
withdrew sixteen of the founder's ninety-eight decisions. This module
reproduces that from committed state rather than repeating the claim, and the
reproduction sharpens it: of the sixteen, FIFTEEN are approvals whose facts,
withholdings, evidence, source and schema are byte-identical -- only the
commit stamp moved. The sixteenth is Saint Kate, whose facts really did change
and whose decision was a HOLD, not an approval.

So: **not one founder APPROVAL in this market has a substantive change.**

WHAT THIS DOES
--------------
Adds a versioned second binding -- ``semantic-approval/1.0``, defined in
``scripts/pettripfinder/approval_binding.py`` -- and records, per decision,
the old hashes, the new semantic hash, the classification, and a deterministic
proof that the meaning is unchanged. A decision applies when EITHER binding
holds. Nothing in 036's ledger is edited; what the founder decided stays
exactly as they wrote it, and this sits beside it as a migration.

WHAT IT REFUSES TO DO
---------------------
It does not approve anything. A row whose approved meaning changed is not
rebound: it goes to the founder. That is the whole difference between fixing a
binding and quietly loosening one.
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

from scripts.pettripfinder import approval_binding as AB                    # noqa: E402
from scripts.pettripfinder.acquisition import founder_decisions_036 as D36  # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F36     # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S25  # noqa: E402
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash  # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-FOUNDER-REVIEW-AND-APPROVAL-BINDING-039"
MARKET = "milwaukee-wi"

PKG = F36.PKG / "milwaukee_approval_binding_039"
REBINDING = PKG / "milwaukee-approval-rebinding-039.json"
REPORT_MD = PKG / "milwaukee-approval-binding-039-report.md"

NEWLINE = chr(10)

# --- the classification the work order asks for ----------------------------- #
FACTS_AND_EVIDENCE_IDENTICAL = "A_FACTS_AND_EVIDENCE_IDENTICAL"
PROVENANCE_ONLY = "B_FACTS_IDENTICAL_EVIDENCE_PROVENANCE_CHANGED"
SUBSTANTIVE = "C_SUBSTANTIVE_FACT_CHANGE"
OTHER = "D_OTHER"


def store_rows() -> Dict[str, Dict]:
    """The committed store: the record each decision was bound to."""
    return {row["identity_key"]: row for row in F36.R34.store_doc()["items"]}


def projected_rows() -> Dict[str, Dict]:
    """The rows a re-projection WOULD write. Nothing is written to get them."""
    return {row["identity_key"]: row
            for row in S25.integrate(write=False)["projected_items"]}


def classify(decision: Mapping, committed: Mapping,
             projected: Optional[Mapping]) -> Dict:
    """One decision, under both bindings, before and after a re-projection."""
    old_binds_now = (decision.get("record_hash") == record_hash(committed)
                     and decision.get("evidence_hash")
                     == evidence_hash(committed.get("evidence") or ()))
    row = OrderedDict([
        ("identity_key", decision["identity_key"]),
        ("canonical_name", committed.get("canonical_name", "")),
        ("founder_decision", decision["decision"]),
        ("old_binding", OrderedDict([
            ("contract", "record_hash+evidence_hash (036)"),
            ("record_hash", decision.get("record_hash", "")),
            ("evidence_hash", decision.get("evidence_hash", "")),
            ("still_binds_committed_store", old_binds_now),
        ])),
        ("new_binding", OrderedDict([
            ("contract", AB.BINDING_CONTRACT_VERSION),
            ("semantic_hash", AB.semantic_hash(committed)),
        ])),
    ])

    if projected is None:
        row["classification"] = OTHER
        row["why"] = ("the projection no longer produces a row for this "
                      "identity; a decision cannot be rebound to a record "
                      "that does not exist")
        row["affected_by_reprojection"] = True
        row["semantic_difference"] = {}
        return row

    old_would_break = (record_hash(committed) != record_hash(projected)
                       or evidence_hash(committed.get("evidence") or ())
                       != evidence_hash(projected.get("evidence") or ()))
    difference = AB.semantic_difference(committed, projected)
    row["affected_by_reprojection"] = old_would_break
    row["semantic_difference"] = difference
    row["semantic_hash_after_reprojection"] = AB.semantic_hash(projected)

    if difference:
        row["classification"] = SUBSTANTIVE
        row["why"] = ("the approved meaning itself moved (%s); this is not a "
                      "provenance artefact and it is NOT rebound"
                      % ", ".join(sorted(difference)))
        return row
    if not old_would_break:
        row["classification"] = FACTS_AND_EVIDENCE_IDENTICAL
        row["why"] = ("nothing moved at all: the old binding still holds "
                      "through a re-projection, and the new one agrees")
        return row
    moved = sorted(_provenance_that_moved(committed, projected))
    row["classification"] = PROVENANCE_ONLY
    row["provenance_that_moved"] = moved
    row["why"] = ("the approved meaning is byte-identical and only "
                  "implementation provenance moved (%s), so the 036 binding "
                  "would withdraw an approval over a field that records how "
                  "the reading was produced rather than what it says"
                  % ", ".join(moved))
    return row


def _provenance_that_moved(before: Mapping, after: Mapping) -> List[str]:
    out = []
    for name in AB.PROVENANCE_TOP_LEVEL:
        if name in ("provenance", "rederivation"):
            continue
        if before.get(name) != after.get(name):
            out.append(name)
    for parent, names in (("provenance", AB.PROVENANCE_PROVENANCE),
                          ("rederivation", AB.PROVENANCE_REDERIVATION)):
        left = before.get(parent) or {}
        right = after.get(parent) or {}
        out.extend("%s.%s" % (parent, name) for name in names
                   if left.get(name) != right.get(name))
    return out


def classified_decisions() -> List[Dict]:
    committed = store_rows()
    projected = projected_rows()
    out = []
    for decision in F36.load_ledger()["decisions"]:
        key = decision["identity_key"]
        row = committed.get(key)
        if row is None:
            continue
        out.append(classify(decision, row, projected.get(key)))
    return sorted(out, key=lambda item: item["identity_key"])


# --------------------------------------------------------------------------- #
# The migration.
# --------------------------------------------------------------------------- #

def rebinding_document() -> Dict:
    rows = classified_decisions()
    affected = [row for row in rows if row["affected_by_reprojection"]]
    rebound = [row for row in affected if row["classification"] in
               (PROVENANCE_ONLY, FACTS_AND_EVIDENCE_IDENTICAL)]
    needs_review = [row for row in rows
                    if row["classification"] in (SUBSTANTIVE, OTHER)]
    return OrderedDict([
        ("schema", "ptf-approval-rebinding/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("binding_contract", AB.BINDING_CONTRACT_VERSION),
        ("supersedes_contract", "record_hash+evidence_hash (036)"),
        ("migration_reason",
         "036's record_hash covered the whole store row, including "
         "rederivation.reader_commit, which the store's own projection "
         "re-derives on every run. A reader repair therefore withdrew sixteen "
         "founder decisions, fifteen of them without changing a single "
         "approved fact. The old hashes are preserved on every row below; "
         "this adds a second, semantic binding rather than redefining the "
         "first."),
        ("what_is_semantic", OrderedDict([
            ("record", list(AB.SEMANTIC_TOP_LEVEL)),
            ("provenance", list(AB.SEMANTIC_PROVENANCE)),
            ("rederivation", list(AB.SEMANTIC_REDERIVATION)),
        ])),
        ("what_is_provenance_only", OrderedDict([
            ("record", list(AB.PROVENANCE_TOP_LEVEL)),
            ("provenance", list(AB.PROVENANCE_PROVENANCE)),
            ("rederivation", list(AB.PROVENANCE_REDERIVATION)),
        ])),
        ("source_ledger", F36.LEDGER.name),
        ("decisions_total", len(rows)),
        ("counts_by_classification",
         dict(Counter(row["classification"] for row in rows))),
        ("affected_by_reprojection", len(affected)),
        ("rebound_without_founder_action", len(rebound)),
        ("requires_founder_re_review", len(needs_review)),
        ("requires_founder_re_review_rows",
         [OrderedDict([("identity_key", row["identity_key"]),
                       ("canonical_name", row["canonical_name"]),
                       ("founder_decision", row["founder_decision"]),
                       ("difference", row["semantic_difference"])])
          for row in needs_review]),
        ("decisions", rows),
    ])


def semantic_binding_for(identity_key: str) -> str:
    """The rebound semantic hash for one decision, or empty if not rebound."""
    entry = rebound_index().get(identity_key)
    return entry[0] if entry else ""


_INDEX: Dict[str, tuple] = {}


def rebound_index() -> Dict[str, tuple]:
    """identity_key -> (semantic_hash, old_record_hash, old_evidence_hash).

    Three values, not one, and the two old hashes are the reason. The semantic
    route must admit a row whose PROVENANCE moved -- never a row whose
    DECISION moved. Editing a decision's ``record_hash`` in the ledger is
    tampering with the founder's own statement about which record they saw,
    and a rebinding that ignored it would quietly forgive exactly that. So a
    decision reaches the semantic route only if it still carries the hashes
    this migration examined when it proved the meaning unchanged.

    A row that needs founder re-review is deliberately absent.
    """
    if not _INDEX:
        if REBINDING.is_file():
            doc = json.loads(REBINDING.read_text(encoding="utf-8"))
        else:
            doc = rebinding_document()
        for row in doc["decisions"]:
            if row["classification"] in (SUBSTANTIVE, OTHER):
                continue
            _INDEX[row["identity_key"]] = (row["new_binding"]["semantic_hash"],
                                           row["old_binding"]["record_hash"],
                                           row["old_binding"]["evidence_hash"])
    return _INDEX


def report_markdown() -> str:
    doc = rebinding_document()
    counts = doc["counts_by_classification"]
    lines = [
        "# Approval binding, corrected -- %s" % WORK_ORDER,
        "",
        "A founder approval is a statement about a claim: this property, "
        "these facts, this evidence, this source, this schema. 036 bound each "
        "decision to a hash of the whole store row, which also carries how "
        "the reading was produced -- including `rederivation.reader_commit`, "
        "a field the projection re-derives every run.",
        "",
        "## What that cost, reproduced from committed state",
        "",
        "| | |",
        "| --- | ---: |",
        "| founder decisions | %d |" % doc["decisions_total"],
        "| withdrawn by a re-projection under the 036 binding | %d |"
        % doc["affected_by_reprojection"],
        "| of those, approved meaning byte-identical | %d |"
        % doc["rebound_without_founder_action"],
        "| of those, approved meaning genuinely changed | %d |"
        % sum(1 for row in doc["decisions"]
              if row["classification"] == SUBSTANTIVE
              and row["affected_by_reprojection"]),
        "",
        "Every one of the byte-identical rows is an **approval**. The single "
        "row whose meaning moved is a **hold**, so not one founder approval "
        "in this market has a substantive change.",
        "",
        "## Classification",
        "",
        "| class | rows |",
        "| --- | ---: |",
    ]
    for name in (FACTS_AND_EVIDENCE_IDENTICAL, PROVENANCE_ONLY, SUBSTANTIVE,
                 OTHER):
        if counts.get(name):
            lines.append("| %s | %d |" % (name, counts[name]))
    lines += [
        "",
        "## What is semantic and what is not",
        "",
        "Semantic -- change it and the approval must be earned again: the "
        "property identity, the proposed facts, the withheld fields (a "
        "withholding is a claim that nothing is being asserted), the service "
        "animal statement, the refusal flag, the cited evidence, the "
        "publication grade, the identity check, the review status, the frozen "
        "semantics violations, the schema version, the source URL and its "
        "snapshot hash, the authority tier and source type, and the canonical "
        "evidence block's own sha256.",
        "",
        "Provenance -- recorded, never deleted, never on its own a reason to "
        "withdraw an approval: `reader_commit`, the derivation note, the "
        "superseding work order, the block's filesystem PATH (the block's "
        "HASH is semantic), the previous reader's facts, the retrieval "
        "timestamp, capture method, provider, reader name, raw pointer and "
        "observation id, the source run, and the mutable "
        "`published`/`founder_approved` flags an approval itself sets.",
        "",
        "Neither list is open-ended. A field in a store row that appears on "
        "neither fails `unclassified_fields`, and hashing refuses rather than "
        "guessing -- an unclassified field is either a tamper hole or a "
        "spurious invalidation, and which one it is is not for code to "
        "decide.",
        "",
        "## Rows still needing the founder",
        "",
    ]
    if doc["requires_founder_re_review_rows"]:
        for row in doc["requires_founder_re_review_rows"]:
            lines.append("* **%s** (%s) -- %s"
                         % (row["canonical_name"], row["founder_decision"],
                            ", ".join(sorted(row["difference"])) or "see ledger"))
    else:
        lines.append("None.")
    lines += ["", "Nothing here was approved, published or deployed.", ""]
    return NEWLINE.join(lines) + NEWLINE


def write(apply: bool = False) -> Dict:
    doc = rebinding_document()
    if apply:
        PKG.mkdir(parents=True, exist_ok=True)
        REBINDING.write_text(
            json.dumps(doc, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
        REPORT_MD.write_text(report_markdown(), encoding="utf-8")
        _INDEX.clear()
    return {k: v for k, v in doc.items() if k != "decisions"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--affected", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.classify:
        print(json.dumps(write(apply=False), indent=2, default=str))
    if args.affected:
        for row in classified_decisions():
            if row["affected_by_reprojection"]:
                print("%-46s %-14s %s" % (row["identity_key"][:46],
                                          row["founder_decision"],
                                          row["classification"]))
    if args.apply:
        print(json.dumps(write(apply=True), indent=2, default=str))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())

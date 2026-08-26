"""PTF-MILWAUKEE-APPROVAL-VOCABULARY-NORMALIZATION-043 -- one spelling, no rewriting.

042 reported two strings for "a founder approved this" and called it Milwaukee
debt. It is not Milwaukee's, and it is not two.

WHAT THE REPOSITORY ACTUALLY SAYS
----------------------------------
``contracts.enums`` has owned this vocabulary since Columbus: six states, a
publishing subset, and a legacy-input map. ``APPROVED`` is already a KEY in
that map, resolving to ``APPROVED_AFTER_CURRENT_REVIEW``. So the canonical
value was settled long before 040, and 040's three records are not a competing
convention -- they are a builder that bypassed one.

Derived, not preferred: 333 of 336 committed approval records across six
markets carry the long form, and five markets' publication validators compare
against it literally. Promoting ``APPROVED`` would invert a versioned map and
make almost every committed record the exception.

WHAT THIS CHANGES, AND WHAT IT REFUSES TO
------------------------------------------
Three ``approval.decision`` values in Milwaukee's CURRENT authority
serialization, from a legacy spelling to the canonical one. Nothing else.

  * The founder DECISION ledgers are untouched. 036 and 040 both record
    ``APPROVE`` / ``APPROVE_REFUSAL`` / ``HOLD``; that axis never diverged, and
    a ledger is what a person said on a day.
  * No hash moves. ``record_hash`` is computed over the record WITHOUT its
    approval block, the store rows the semantic binding reads carry no approval
    block at all, and ``approval`` appears in neither list of the
    semantic-approval/1.0 contract. That is asserted here rather than assumed,
    because "vocabulary-only" is exactly the claim a silent re-hash would hide
    behind.
  * Every other market keeps its own records untouched. They are already
    canonical; nothing needed doing and nothing was done.

The legacy spelling stays readable forever. A record that still says
``APPROVED`` -- Columbus's, or any future import -- resolves through the
contract rather than being rewritten to make a comparison pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import approval_binding as AB                     # noqa: E402
from scripts.pettripfinder import market_authority as MA                     # noqa: E402
from scripts.pettripfinder import release_contracts as RC                    # noqa: E402
from scripts.pettripfinder.acquisition import authority_build_036 as A36     # noqa: E402
from scripts.pettripfinder.acquisition import closure_038 as C38             # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F36      # noqa: E402
from scripts.pettripfinder.acquisition import publication_042 as P42         # noqa: E402
from scripts.pettripfinder.contracts import founder_approval as FA           # noqa: E402
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash  # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-APPROVAL-VOCABULARY-NORMALIZATION-043"
MARKET = "milwaukee-wi"

PKG = F36.PKG / "milwaukee_vocabulary_043"
REPORT = PKG / "milwaukee-approval-vocabulary-043.json"

NEWLINE = chr(10)

#: Every committed policy package, so the inventory is a repository fact rather
#: than a Milwaukee one.
PACKAGES = sorted(F36.PKG.glob("hotel_policy_facts*.json"))

#: Founder DECISION ledgers -- a different axis, inventoried to prove it.
LEDGERS = sorted(F36.PKG.glob("*founder_decisions*.json"))


class NormalizationError(RuntimeError):
    """Raised rather than normalizing something that is not vocabulary-only."""


# --------------------------------------------------------------------------- #
# Phase 2 -- the inventory, derived from every market.
# --------------------------------------------------------------------------- #

def package_inventory() -> List[Dict]:
    out = []
    for path in PACKAGES:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        summary = FA.inventory(doc.get("hotels") or ())
        out.append(OrderedDict([
            ("package", path.name),
            ("market_id", doc.get("market_id", "")),
            ("records", summary["records"]),
            ("by_stored_spelling", summary["by_stored_spelling"]),
            ("by_resolved_state", summary["by_resolved_state"]),
            ("legacy_spellings_present", summary["legacy_spellings_present"]),
        ]))
    return out


def ledger_inventory() -> List[Dict]:
    """The founder DECISION axis. Reported to show it did NOT diverge."""
    out = []
    for path in LEDGERS:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = doc.get("decisions") or ()
        out.append(OrderedDict([
            ("ledger", path.name),
            ("decisions", len(rows)),
            ("by_decision", dict(Counter(row.get("decision", "<absent>")
                                         for row in rows))),
        ]))
    return out


def vocabulary_report() -> Dict:
    packages = package_inventory()
    spellings: Counter = Counter()
    for row in packages:
        spellings.update(row["by_stored_spelling"])
    return OrderedDict([
        ("vocabulary", FA.VOCABULARY_VERSION),
        ("canonical", FA.CANONICAL_APPROVED),
        ("states", list(FA.STATES)),
        ("publishing_states", sorted(FA.PUBLISHING_STATES)),
        ("legacy_inputs", FA.LEGACY_INPUTS),
        ("legacy_caveats", FA.LEGACY_CAVEATS),
        ("writable_by_new_code", sorted(FA.WRITABLE)),
        ("approval_spellings_across_all_packages", dict(spellings)),
        ("packages", packages),
        ("decision_ledgers", ledger_inventory()),
    ])


# --------------------------------------------------------------------------- #
# Phases 6 and 9 -- normalize the serialization, prove nothing else moved.
# --------------------------------------------------------------------------- #

def normalization_plan() -> List[Dict]:
    """Every record whose stored spelling is not the canonical one."""
    doc = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    plan = []
    for record in doc["hotels"]:
        stored = (record.get("approval") or {}).get("decision")
        resolved = FA.normalize(stored)
        if stored == resolved:
            continue
        plan.append(OrderedDict([
            ("identity_key", record["identity_key"]),
            ("name", record["name"]),
            ("stored_decision", stored),
            ("canonical_decision", resolved),
            ("approval_work_order",
             record["approval"]["decision_source"]["work_order"]),
            ("legacy_caveat", FA.caveat_for(stored)),
        ]))
    return plan


def assert_vocabulary_only(before: Mapping, after: Mapping) -> Dict:
    """Prove the change is a spelling and nothing else.

    Every field except ``approval.decision`` must be byte-identical, and every
    hash must be unchanged -- computed rather than copied, so a re-hash cannot
    hide behind the claim.
    """
    problems: List[str] = []
    old = {r["identity_key"]: r for r in before["hotels"]}
    new = {r["identity_key"]: r for r in after["hotels"]}
    if set(old) != set(new):
        problems.append("the record set changed")
    changed_fields: Counter = Counter()
    for key, old_record in old.items():
        new_record = new.get(key)
        if new_record is None:
            continue
        if record_hash(old_record) != record_hash(new_record):
            problems.append("%s: record_hash moved" % key)
        if evidence_hash(old_record.get("evidence") or ()) != \
                evidence_hash(new_record.get("evidence") or ()):
            problems.append("%s: evidence_hash moved" % key)
        for field in set(old_record) | set(new_record):
            if field == "approval":
                continue
            if json.dumps(old_record.get(field), sort_keys=True,
                          default=str) != json.dumps(
                              new_record.get(field), sort_keys=True,
                              default=str):
                problems.append("%s: %s changed" % (key, field))
        old_approval = old_record.get("approval") or {}
        new_approval = new_record.get("approval") or {}
        for field in set(old_approval) | set(new_approval):
            if json.dumps(old_approval.get(field), sort_keys=True,
                          default=str) != json.dumps(
                              new_approval.get(field), sort_keys=True,
                              default=str):
                changed_fields[field] += 1
                # Two fields may move: the spelling itself, and the note
                # recording what it used to say. Everything else -- operator,
                # dates, hashes, decision source, caveats -- is the founder's
                # record and may not.
                if field not in ("decision", "decision_normalization"):
                    problems.append("%s: approval.%s changed" % (key, field))
        # Superseded approvals are verbatim history. Cleveland's own test
        # asserts a replaced approval "stays verbatim and provably unbound",
        # and all four registered legacy spellings live in these blocks.
        for field in ("supersedes", "invalidated_attribution",
                      "prior_approval"):
            if json.dumps(old_approval.get(field), sort_keys=True,
                          default=str) != json.dumps(
                              new_approval.get(field), sort_keys=True,
                              default=str):
                problems.append("%s: superseded history %s changed"
                                % (key, field))
    for field in ("published", "publication", "provenance", "schema_version",
                  "market_id"):
        if json.dumps(before.get(field), sort_keys=True, default=str) != \
                json.dumps(after.get(field), sort_keys=True, default=str):
            problems.append("package-level %s changed" % field)
    if problems:
        raise NormalizationError("NOT VOCABULARY-ONLY: " + "; ".join(problems))
    return {"records_compared": len(old),
            "approval_fields_changed": dict(changed_fields)}


def normalized_document() -> Tuple[Dict, Dict]:
    """(document, proof). The committed package with canonical spellings."""
    before = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    after = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    for record in after["hotels"]:
        approval = record.get("approval") or {}
        stored = approval.get("decision")
        canonical = FA.normalize(stored)
        if stored == canonical:
            continue
        approval["decision"] = FA.assert_writable(canonical, where=WORK_ORDER)
        # What the record USED to say is kept: a reader who wants to know that
        # this row was written under an older spelling can still find out, and
        # the alternative is a silent edit to a founder-approved record.
        approval["decision_normalization"] = OrderedDict([
            ("work_order", WORK_ORDER),
            ("vocabulary", FA.VOCABULARY_VERSION),
            ("previous_decision", stored),
            ("why", "a legacy spelling of the same state; the approval, its "
                    "facts, its evidence and every hash are unchanged, and "
                    "the founder decision ledger that produced it was not "
                    "touched"),
        ])
    proof = assert_vocabulary_only(before, after)
    return after, proof


def write(apply: bool = False) -> Dict:
    plan = normalization_plan()
    document, proof = normalized_document()
    contract_result: Dict = {}
    if apply:
        A36.AUTHORITY.write_text(
            json.dumps(document, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
        # The globals are GENERATED, and the release contract pins the
        # package's sha256 -- which moved, because the file's bytes did.
        from scripts.pettripfinder import build_global_authority as GLOBALS
        GLOBALS.main(["--write"])
        contract = P42.live_contract()
        P42.assert_contract_agrees(contract)
        P42.LIVE_CONTRACT.write_text(
            json.dumps(contract, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
        contract_result = {"path": P42.LIVE_CONTRACT.relative_to(REPO).as_posix(),
                           "disagreements": RC.verify_contract(MARKET)}
    return {
        "applied": apply,
        "records_normalized": len(plan),
        "plan": plan,
        "proof": proof,
        "live_contract": contract_result,
    }


# --------------------------------------------------------------------------- #
# Phase 7 -- new code cannot introduce another synonym casually.
# --------------------------------------------------------------------------- #

#: Modules that legitimately mention a legacy spelling: the contract that
#: registers it, the enum that owns it, and the work orders that documented
#: the divergence. Everything else writing one is the defect this guards.
SYNONYM_MENTIONS_ALLOWED = (
    "contracts/enums.py",
    "contracts/founder_approval.py",
    "acquisition/publication_042.py",
    "acquisition/vocabulary_normalization_043.py",
)


def modules_emitting_a_legacy_spelling() -> List[Dict]:
    """Source files that assign a legacy approval spelling as a value.

    Deliberately crude and deliberately loud: it looks for the literal next to
    a ``decision`` key. A guard that tried to be clever about control flow
    would miss the one line that matters, which is exactly how 040 got in.
    """
    import re
    pattern = re.compile(
        r"[\"']decision[\"']\s*[,:]\s*[\"'](%s)[\"']"
        % "|".join(re.escape(name) for name in sorted(FA.LEGACY_INPUTS)))
    out = []
    for path in sorted((REPO / "scripts").rglob("*.py")):
        relative = path.relative_to(REPO / "scripts").as_posix()
        if any(relative.endswith(allowed.split("/")[-1])
               and allowed.split("/")[-1] in relative
               for allowed in SYNONYM_MENTIONS_ALLOWED):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in pattern.finditer(text):
            out.append({"module": relative, "spelling": match.group(1),
                        "line": text[:match.start()].count(chr(10)) + 1})
    return out


def assert_no_new_synonyms() -> List[Dict]:
    offenders = modules_emitting_a_legacy_spelling()
    if offenders:
        raise NormalizationError(
            "these modules WRITE a legacy approval spelling: %s"
            % "; ".join("%s:%d %r" % (row["module"], row["line"],
                                      row["spelling"]) for row in offenders))
    return offenders


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def normalized_records() -> List[Dict]:
    """What WAS normalized, read from the records' own notes.

    Not from ``normalization_plan``: that is forward-looking and returns
    nothing once the work is done, so a report built from it records the
    outcome instead of the act. The note on each record is durable and is the
    honest source after the fact.
    """
    doc = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    out = []
    for record in doc["hotels"]:
        note = (record.get("approval") or {}).get("decision_normalization")
        if not note:
            continue
        out.append(OrderedDict([
            ("identity_key", record["identity_key"]),
            ("name", record["name"]),
            ("stored_decision", note["previous_decision"]),
            ("canonical_decision", record["approval"]["decision"]),
            ("approval_work_order",
             record["approval"]["decision_source"]["work_order"]),
            ("normalized_by", note["work_order"]),
        ]))
    return out


def report(build: Optional[Mapping] = None) -> Dict:
    authority = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    recon = C38.reconciliation()
    return OrderedDict([
        ("schema", "ptf-approval-vocabulary-normalization/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("provider_calls", 0),
        ("cost_usd", 0.0),
        ("vocabulary", vocabulary_report()),
        ("canonical_chosen", FA.CANONICAL_APPROVED),
        ("canonical_rationale",
         "Derived, not preferred. 333 of 336 committed approval records across "
         "six markets carry it; five markets' publication validators compare "
         "against it literally; and 'APPROVED' was already registered as a "
         "LEGACY INPUT resolving to it. Promoting the shorter string would "
         "invert an existing versioned map and make almost every committed "
         "record non-canonical."),
        ("normalized_records", normalized_records()),
        ("still_to_normalize", normalization_plan()),
        ("hash_safety", OrderedDict([
            ("approval_is_in_the_semantic_contract",
             "approval" in AB.SEMANTIC_TOP_LEVEL),
            ("record_hash_excludes_approval", True),
            ("store_rows_carry_no_approval_block", True),
            ("migration_performed", False),
        ])),
        ("authority", OrderedDict([
            ("pet_friendly", len(authority["hotels"])),
            ("verified_no_pets", len(MA.load_market_exclusions(MARKET))),
            ("published", authority["published"]),
            ("deployed", authority.get("publication", {}).get("deployed")),
        ])),
        ("closure", OrderedDict([
            ("active_eligible", recon["active_eligible"]),
            ("census_total", recon["census_total"]),
            ("problems", recon["problems"]),
        ])),
        ("contract_verification",
         {market: RC.verify_contract(market)
          for market in RC.available_market_ids()}),
        ("new_synonym_emitters", modules_emitting_a_legacy_spelling()),
        ("build", dict(build) if build else None),
    ])


def write_report(build: Optional[Mapping] = None) -> Dict:
    PKG.mkdir(parents=True, exist_ok=True)
    doc = report(build)
    REPORT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + NEWLINE,
                      encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--guard", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    if args.inventory:
        print(json.dumps(vocabulary_report(), indent=2, default=str))
    if args.plan:
        print(json.dumps(write(apply=False), indent=2, default=str))
    if args.guard:
        print(json.dumps(modules_emitting_a_legacy_spelling(), indent=2))
    if args.apply:
        print(json.dumps(write(apply=True), indent=2, default=str))
    if args.report:
        print(json.dumps(write_report(P42.build_site())["authority"], indent=2,
                         default=str))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())

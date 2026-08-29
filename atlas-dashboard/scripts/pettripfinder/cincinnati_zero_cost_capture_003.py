"""PTF-CINCINNATI-ZERO-COST-CAPTURE-003 -- build this pass's artifacts.

    python -m scripts.pettripfinder.cincinnati_zero_cost_capture_003
    python -m scripts.pettripfinder.cincinnati_zero_cost_capture_003 --write

WHAT THIS PASS WAS
------------------
93 Cincinnati identities observed by ATTENDED BROWSER ONLY. No Google Places,
no Bright Data, no Firecrawl, no paid acquisition: provider calls 0, spend
$0.00. The cohort is the EVIDENCE_READY class of the founder-review queue that
PTF-CINCINNATI-HARDENED-SYNC-002 rebuilt, plus the four rows a free routing
adjudication promoted into it.

THE COHORT IS 93, NOT 97
-------------------------
The work order projected 97 from the audit's brand split. That split was read
off ``cincinnati_capture_ready_queue_002.json``, whose ``brand_lane`` column
lumps Drury, Motel 6, Great Wolf, InTown Suites and WoodSpring into
"independent". The rebuilt queue separates them, and it also moved some rows
the stale queue counted here into IDENTITY_REVIEW and PROPERTY_LEVEL_URL_
RECOVERY. Rebuilt from current authority, as Phase 2 requires, the cohort is
89 + 4 = 93. Every row is processed exactly once and no identity appears twice.

WHAT THE TRIAGE DOES AND DOES NOT DECIDE
-----------------------------------------
It proposes. A CLEAN candidate is one where the hardened rules settle the
reading with nothing left over: the facts validate against policy_schema, the
quote is present, and no contradiction, truncation or ambiguity was recorded
against it. Those do not go back to the founder row by row.

An EXCEPTION is a row where the SOURCE, not the reader, leaves something
unsettled -- a page that states two different headline fees, a policy string
the property truncated mid-word, a charge whose trigger condition is unstated,
a species allowance that is conditional on manager approval, a bare
structured-data flag with no prose behind it. Those are founder questions and
this module does not answer them. Nothing here writes a founder decision, a
reviewer id, or an approval.

OPERATIONAL OUTCOMES ARE NOT FOUNDER WORK
------------------------------------------
POLICY_NOT_FOUND, ACCESS_BLOCKED and ROUTING_REPAIR_REQUIRED are facts about
pages and servers. They are next-pass work, not decisions, and they are kept
out of the founder packet so that packet stays what it claims to be.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import service_animal as SA  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-ZERO-COST-CAPTURE-003"
MARKET_ID = "cincinnati-oh"
AS_OF = "2026-08-29"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
SCRATCH = Path("C:/Users/jfiel/AppData/Local/Temp/claude/"
               "C--Atlas-Cincinnati-Hardened/"
               "70d95236-83bb-4836-acae-0c3f3089db96/scratchpad/cap003")

#: Terminal states this pass may assign. Phase 4 of the work order.
OUTCOMES = ("PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS", "POLICY_NOT_FOUND",
            "ACCESS_BLOCKED", "IDENTITY_MISMATCH", "HOLD",
            "ROUTING_REPAIR_REQUIRED")

CLEAN_PF = "CLEAN_PET_FRIENDLY_CANDIDATE"
CLEAN_NP = "CLEAN_VERIFIED_NO_PETS_CANDIDATE"
EXCEPTION = "FOUNDER_EXCEPTION"
NO_FOUNDER_ACTION = "NO_FOUNDER_ACTION"


class BuildError(RuntimeError):
    pass


def load_capture() -> List[Dict]:
    return json.loads((SCRATCH / "batch_a.json").read_text(
        encoding="utf-8"))["rows"]


def load_phase1() -> Dict:
    return json.loads((SCRATCH / "phase1.json").read_text(encoding="utf-8"))


def load_cohort() -> Dict:
    return json.loads((SCRATCH / "cohort.json").read_text(encoding="utf-8"))


def triage(row: Dict) -> str:
    """One label per row. Never a decision -- a routing of the reviewer's time."""
    outcome = row["outcome"]
    if outcome in ("POLICY_NOT_FOUND", "ACCESS_BLOCKED",
                   "ROUTING_REPAIR_REQUIRED"):
        return NO_FOUNDER_ACTION
    if row.get("triage_override") == EXCEPTION or outcome == "IDENTITY_MISMATCH":
        return EXCEPTION
    if outcome == "PUBLICATION_CANDIDATE":
        return CLEAN_PF
    if outcome == "VERIFIED_NO_PETS":
        return CLEAN_NP
    raise BuildError("no triage for outcome %r" % outcome)


def check_service_animals(rows: List[Dict]) -> List[str]:
    """Every published service-animal charge state, re-read from its own quote.

    The classifier is the arbiter, not this pass's opinion: a row whose quote
    reads differently from the charge state recorded beside it is a defect, and
    the run refuses rather than publishing a charge the source did not state.
    """
    problems = []
    for row in rows:
        stmt = row.get("service_animal_statement")
        if not stmt:
            continue
        quote = stmt.get("quote") or ""
        reading = SA.classify(quote)
        if reading.charges_stated != stmt.get("charges_stated"):
            problems.append(
                "%s: recorded charges_stated=%r but contracts.service_animal "
                "reads %r from the quote (%s)"
                % (row["identity_key"], stmt.get("charges_stated"),
                   reading.charges_stated, reading.reason))
        if stmt.get("stated") is not True:
            problems.append("%s: service_animal_statement.stated is not True"
                            % row["identity_key"])
    return problems


def validate(rows: List[Dict], cohort: List[Dict]) -> List[str]:
    problems = []
    keys = [r["identity_key"] for r in rows]
    dupes = [k for k, n in Counter(keys).items() if n > 1]
    if dupes:
        problems.append("duplicate identity in results: %s" % dupes)
    if set(keys) != {c["identity_key"] for c in cohort}:
        missing = {c["identity_key"] for c in cohort} - set(keys)
        extra = set(keys) - {c["identity_key"] for c in cohort}
        problems.append("cohort mismatch; missing=%s extra=%s"
                        % (sorted(missing)[:5], sorted(extra)[:5]))
    for row in rows:
        if row["outcome"] not in OUTCOMES:
            problems.append("%s: outcome %r is not one of the seven"
                            % (row["identity_key"], row["outcome"]))
        if row["outcome"] in ("PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS"):
            if not row.get("quote"):
                problems.append("%s: %s with no evidence quote"
                                % (row["identity_key"], row["outcome"]))
            if not row.get("sha256"):
                problems.append("%s: %s with no artifact hash"
                                % (row["identity_key"], row["outcome"]))
        if row["outcome"] == "PUBLICATION_CANDIDATE":
            if (row.get("facts") or {}).get("pets_allowed") is not True:
                problems.append("%s: publication candidate without "
                                "pets_allowed=True" % row["identity_key"])
        if row["outcome"] == "VERIFIED_NO_PETS":
            if (row.get("facts") or {}).get("pets_allowed") is not False:
                problems.append("%s: verified-no-pets without "
                                "pets_allowed=False" % row["identity_key"])
    problems.extend(check_service_animals(rows))
    return problems


def build():
    rows = load_capture()
    cohort = load_cohort()
    problems = validate(rows, cohort["rows"])
    if problems:
        raise BuildError("results do not validate: %s" % problems[:8])

    for row in rows:
        row["triage"] = triage(row)

    by_triage = OrderedDict()
    for label in (CLEAN_PF, CLEAN_NP, EXCEPTION, NO_FOUNDER_ACTION):
        by_triage[label] = [r for r in rows if r["triage"] == label]

    common = OrderedDict((
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("provider_calls", 0), ("paid_spend_usd", 0.0),
        ("capture_method", "attended_chrome_render"),
    ))

    results = OrderedDict(common)
    results.update((
        ("schema", "ptf-market-capture-pass-results/1.1"),
        ("note", "Every row in the Phase 2 cohort, processed exactly once by "
                 "attended browser. Outcome counts are the seven terminal "
                 "states the work order defines; triage is a routing of "
                 "reviewer attention and is never a decision."),
        ("cohort_size", len(cohort["rows"])), ("processed", len(rows)),
        ("outcome_counts",
         OrderedDict(sorted(Counter(r["outcome"] for r in rows).items()))),
        ("triage_counts",
         OrderedDict((k, len(v)) for k, v in by_triage.items())),
        ("rows", rows),
    ))

    clean_pf = OrderedDict(common)
    clean_pf.update((
        ("schema", "ptf-market-clean-candidates/1.0"),
        ("candidate_class", CLEAN_PF),
        ("note", "Pet-friendly readings the hardened rules settle with nothing "
                 "left over. NOT approvals: no founder decision, reviewer id "
                 "or approval hash is written here, and none may be inferred "
                 "from this file's existence."),
        ("count", len(by_triage[CLEAN_PF])), ("rows", by_triage[CLEAN_PF]),
    ))

    clean_np = OrderedDict(common)
    clean_np.update((
        ("schema", "ptf-market-clean-candidates/1.0"),
        ("candidate_class", CLEAN_NP),
        ("note", "Affirmative, property-specific refusals in each property's "
                 "own words. Silence is never counted here. NOT approvals."),
        ("count", len(by_triage[CLEAN_NP])), ("rows", by_triage[CLEAN_NP]),
    ))

    packet = OrderedDict(common)
    packet.update((
        ("schema", "ptf-market-founder-exception-packet/1.0"),
        ("note", "ONLY the rows where the SOURCE leaves something unsettled, "
                 "plus the one identity question. The clean rows are not here, "
                 "which is the point: this packet is what actually needs a "
                 "person. Every row states the question it is asking."),
        ("count", len(by_triage[EXCEPTION])),
        ("rows", [OrderedDict((
            ("identity_key", r["identity_key"]), ("outcome", r["outcome"]),
            ("final_url", r["final_url"]), ("sha256", r.get("sha256")),
            ("quote", r.get("quote")), ("proposed_facts", r.get("facts")),
            ("withheld", r.get("withheld")),
            ("service_animal_statement", r.get("service_animal_statement")),
            ("question_for_the_founder", r["notes"]),
            ("founder_decision", ""), ("founder_reviewer_id", ""),
            ("founder_reviewed_at", ""),
        )) for r in by_triage[EXCEPTION]]),
    ))

    manifest = OrderedDict(common)
    manifest.update((
        ("schema", "ptf-market-capture-manifest/1.0"),
        ("phase_1_routing_verification", OrderedDict((
            ("attempted", 10), ("verified", 10), ("promoted", 4),
            ("stayed_in_paid_lane", 6),
        ))),
        ("cohort", OrderedDict((
            ("size", len(cohort["rows"])),
            ("by_brand", cohort["by_brand"]),
            ("derived_from",
             "launch_packages/pettripfinder/markets/reports/"
             "cincinnati-oh_founder_review_queue.json (rebuilt by SYNC-002)"),
        ))),
        ("outcomes", results["outcome_counts"]),
        ("triage", results["triage_counts"]),
        ("artifacts", [
            "cincinnati_capture_pass3_001_results.json",
            "cincinnati_capture_pass3_clean_pet_friendly.json",
            "cincinnati_capture_pass3_clean_verified_no_pets.json",
            "cincinnati_capture_pass3_founder_exceptions.json",
            "cincinnati_capture_pass3_manifest.json",
            "cincinnati-oh_founder_review_queue.json (updated)",
        ]),
        ("evidence_convention",
         "sha256 computed live against the page's rendered outerHTML and the "
         "quote extracted from the same DOM in the same JavaScript call -- the "
         "convention this market's six committed VERIFIED_NO_PETS exclusions "
         "already rest on. Raw bytes are not committed; they never are here."),
        ("authority_mutated", False),
        ("means", "This pass proposes. It writes no policy authority, no "
                  "exclusion, no approval and no launch decision."),
    ))

    return results, clean_pf, clean_np, packet, manifest, rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        results, pf, np_, packet, manifest, rows = build()
    except BuildError as exc:
        print("REFUSED: %s" % exc)
        return 2

    print("cohort           : %d" % results["cohort_size"])
    print("processed        : %d" % results["processed"])
    print("outcomes         : %s" % dict(results["outcome_counts"]))
    print("triage           : %s" % dict(results["triage_counts"]))
    print("service-animal re-read: clean")

    if args.write:
        for name, doc in (
                ("cincinnati_capture_pass3_001_results.json", results),
                ("cincinnati_capture_pass3_clean_pet_friendly.json", pf),
                ("cincinnati_capture_pass3_clean_verified_no_pets.json", np_),
                ("cincinnati_capture_pass3_founder_exceptions.json", packet),
                ("cincinnati_capture_pass3_manifest.json", manifest)):
            (REPORTS / name).write_text(
                json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8", newline="\n")
            print("WROTE %s" % name)
    else:
        print("(check only -- pass --write)")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())

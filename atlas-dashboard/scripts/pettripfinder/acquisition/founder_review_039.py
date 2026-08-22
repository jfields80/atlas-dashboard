"""PTF-...-FOUNDER-REVIEW-AND-APPROVAL-BINDING-039 -- the six, put in front of a person.

038 closed the market and left exactly six rows marked
AWAITING_FOUNDER_DECISION. This turns them into something a founder can
actually read: the quote, where it came from, what the reader made of it, what
changed to make the row reviewable at all, and what is still ambiguous.

The verdict each row carries is ADVISORY. It is the machine saying what it
would do, printed next to the evidence so the founder can disagree with it
cheaply. Nothing here approves anything and nothing here reaches authority.

THREE KINDS OF ROW, AND THEY ARE NOT EQUIVALENT
------------------------------------------------
Three came off evidence already on disk, captured by provider DECISION TESTS
that 025 deliberately excludes from the production store. The evidence is
real; what it is not is a production observation, and approving it means
knowingly admitting a record the store's own selection rule refuses. That is a
founder's call to make, and it is printed on the row rather than buried.

Two were fetched in 038's bounded reacquisition and DECLINED at the identity
gate -- a first-party /faq and /dogs/ page carrying the hotel's name and
nothing physical. They appear here with no proposed facts, because the router
never bound the page to the property and a parse of an unbound page is not a
fact. The founder can bind an identity; this package cannot.

One is Saint Kate, whose page always said it was pet-friendly and whose reader
used to disagree with it. The parser changed, so the founder is asked again --
being asked again is the point. A parser that changed its mind is a reason to
look, never a reason to approve.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import closure_038 as C38            # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F36     # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S25  # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-FOUNDER-REVIEW-AND-APPROVAL-BINDING-039"
MARKET = "milwaukee-wi"

PKG = F36.PKG / "milwaukee_founder_review_039"
REVIEW_JSON = PKG / "founder-review-039.json"
REVIEW_MD = PKG / "founder-review-039.md"

NEWLINE = chr(10)

EXPECTED_CANDIDATES = 6

APPROVE = "APPROVE"
APPROVE_REFUSAL = "APPROVE_REFUSAL"
HOLD = "HOLD"

#: Where a row's evidence came from, and why that matters to a reader of this
#: package. Neither is better than the other; they fail differently.
FROM_PERSISTED = "PERSISTED_OFFLINE_RECOVERY"
FROM_REACQUISITION = "BOUNDED_REACQUISITION_038"

#: A service-animal statement should START at the service-animal wording. When
#: it does not, the locator has swept in the line above it.
_SERVICE_ANIMAL_OPENER = re.compile(
    r"^\W*(?:only\s+)?(?:ada\s+)?(?:certified\s+|trained\s+|registered\s+)?"
    r"(?:service|assistance|guide|support)\s+(?:animal|animals|dog|dogs)\b"
    r"|^\W*(?:pets?\s+allowed\s*:|no\s+pets\b)",
    re.IGNORECASE)

#: Facts that make an allowance worth publishing. An allowance alone is still
#: publishable -- plenty of approved Milwaukee records are single-field -- but
#: the distinction belongs on the row.
SUBSTANTIVE = ("pet_fee", "fee_basis", "fee_cap", "pet_count_limit",
               "weight_limit", "species", "deposit", "other_charges",
               "fee_tiers", "fee_pet_schedule")


def _ledger_row(identity_key: str) -> Dict:
    doc = json.loads(C38.LEDGER.read_text(encoding="utf-8"))
    for row in doc["active_eligible"]:
        if row["identity_key"] == identity_key:
            return row
    return {}


def evidence_origin(run_id: str) -> str:
    from scripts.pettripfinder.acquisition import bounded_reacquisition_038 as B38
    return FROM_REACQUISITION if run_id == B38.RUN_ID else FROM_PERSISTED


def ambiguities(candidate: Mapping, ledger_row: Mapping) -> List[str]:
    """Everything a founder should not have to notice for themselves."""
    out: List[str] = []
    facts = candidate["proposed_facts"] or {}
    reading = candidate["reader_reading"] or {}

    if not candidate["identity_confirmed"]:
        out.append(
            "the router DECLINED this page: it is on the property's own "
            "domain and carries the hotel's name, but a policy subpage states "
            "no address, telephone or JSON-LD, so the identity gate could not "
            "bind it. Approving this row means binding the identity by hand, "
            "which is a founder's act and not a parser's.")
        out.append(
            "no facts are proposed for that reason. The reader's own reading "
            "of the block is shown for information and is NOT trustworthy "
            "here -- on this page it read a penalty for an unauthorised pet "
            "as a pet fee."
            if "pet_fee" in reading else
            "no facts are proposed for that reason.")

    if candidate["run_kind"] != S25.CURRENT_PRODUCTION:
        out.append(
            "the capture came from %s, a run 025 classifies %s and therefore "
            "excludes from the production store. Approving it means knowingly "
            "admitting a record the store's own selection rule will not hold, "
            "and the row will need a production capture or an explicit "
            "supersession before it can be projected."
            % (candidate["run_id"], candidate["run_kind"]))

    if facts and "pets_allowed" not in facts:
        out.append("the source prices a pet policy without stating that pets "
                   "are allowed; a price is not permission")

    if facts.get("pets_allowed") is False:
        quote = " ".join(
            item for item in [candidate.get("evidence_block", "")][:1])
        if not F36.refusal_quote_is_self_contained(quote[:200]):
            out.append("the refusal reads as a contrast rather than a "
                       "statement; read the block in full before approving it "
                       "as VERIFIED_NO_PETS")

    statement = (facts.get("service_animal_exception")
                 or reading.get("service_animal_exception") or "")
    if statement and not _SERVICE_ANIMAL_OPENER.match(statement.strip()):
        out.append(
            "the service-animal statement begins mid-sentence (%r): the "
            "locator captured text ahead of the service-animal wording. The "
            "facts beside it are read from their own quotes and are "
            "unaffected, but the sentence a guest would be shown is not clean."
            % statement[:80])

    if candidate.get("withheld_fields"):
        out.append("the reader withheld %s rather than guessing"
                   % ", ".join("%s (%s)" % (field, why) for field, why
                               in sorted(candidate["withheld_fields"].items())))

    if ledger_row.get("disposition") == C38.SOURCE_CONFLICT:
        out.append("the source contradicts itself")
    return out


def advisory_verdict(candidate: Mapping, issues: Sequence[str]) -> Dict:
    """What the machine would do, and the one sentence saying why."""
    facts = candidate["proposed_facts"] or {}

    if not candidate["identity_confirmed"]:
        return {"verdict": HOLD,
                "why": "the page is not bound to this property; no amount of "
                       "good policy text fixes an unbound identity, and 039 "
                       "does not touch the gate that said so"}
    if not facts:
        return {"verdict": HOLD, "why": "no publishable fact is proposed"}
    if "pets_allowed" not in facts:
        return {"verdict": HOLD,
                "why": "the page prices a pet policy without granting one, "
                       "and an allowance is never inferred from a price"}
    if facts.get("pets_allowed") is False:
        return {"verdict": APPROVE_REFUSAL,
                "why": "the property's own page refuses pets in a quoted, "
                       "self-contained statement; admitting it as "
                       "VERIFIED_NO_PETS answers the traveller as usefully as "
                       "an allowance would"}
    stated = sorted(set(facts) & set(SUBSTANTIVE))
    return {
        "verdict": APPROVE,
        "why": ("the page states an allowance%s, every value is quoted, and "
                "everything the source did not state is absent rather than "
                "invented"
                % (" and " + ", ".join(stated) if stated else
                   " and nothing else -- a single-field record, which this "
                   "market already publishes")),
    }


def candidate_row(candidate: Mapping) -> Dict:
    ledger_row = _ledger_row(candidate["identity_key"])
    issues = ambiguities(candidate, ledger_row)
    verdict = advisory_verdict(candidate, issues)
    return OrderedDict([
        ("identity_key", candidate["identity_key"]),
        ("property_name", candidate["canonical_name"]),
        ("brand", candidate["brand"]),
        ("address", candidate["address"]),
        ("source_url", candidate["source_url"]),
        ("census_url", candidate.get("census_url", "")),
        ("provider_lineage", candidate["acquisition_lineage"]),
        ("run_id", candidate["run_id"]),
        ("run_kind", candidate["run_kind"]),
        ("evidence_origin", evidence_origin(candidate["run_id"])),
        ("evidence_quote", candidate["evidence_block"]),
        ("evidence_quote_chars", candidate["evidence_block_chars"]),
        ("attempt_dir", candidate["attempt_dir"]),
        ("current_parsed_facts", candidate["reader_reading"]),
        ("parse_is_trustworthy", candidate["reader_reading_trustworthy"]),
        ("proposed_publication_facts", candidate["proposed_facts"]),
        ("withheld_fields", candidate["withheld_fields"]),
        ("previously", OrderedDict([
            ("disposition_before_038", ledger_row.get("census_final_state", "")),
            ("why_it_was_unresolved_or_held", candidate["why_reviewable_now"]),
        ])),
        ("what_changed_in_038", candidate["why_reviewable_now"]),
        ("identity_status", "CONFIRMED" if candidate["identity_confirmed"]
                            else "DECLINED_BY_ROUTER_IDENTITY_GATE"),
        ("reader_locator_status", candidate["locator_lineage"]),
        ("ambiguity", issues),
        ("recommended_machine_verdict", verdict["verdict"]),
        ("recommended_because", verdict["why"]),
        ("verdict_is_advisory_only", True),
        ("founder_decision", "<UNANSWERED>"),
        ("status", "AWAITING_FOUNDER_DECISION"),
    ])


def rows() -> List[Dict]:
    """The six, from the committed package if it exists.

    A review package is a record of what the founder was SHOWN. Once they have
    answered, re-deriving it from live state would rewrite the question after
    the fact -- and live state no longer offers these rows as candidates at
    all, because PTF-MILWAUKEE-FOUNDER-DECISION-040 decided every one of them.
    Before the package is written, the derivation is the only source there is.
    """
    if REVIEW_JSON.is_file():
        return list(json.loads(
            REVIEW_JSON.read_text(encoding="utf-8"))["candidates"])
    return [candidate_row(candidate) for candidate in C38.new_candidates()]


def derived_rows() -> List[Dict]:
    """The package as live state would produce it now, for regeneration."""
    return [candidate_row(candidate) for candidate in C38.new_candidates()]


def assert_cohort() -> List[Dict]:
    out = rows()
    if len(out) != EXPECTED_CANDIDATES:
        raise SystemExit(
            "ABORT: 038 derives %d candidates, not %d. The package must "
            "contain exactly the rows 038 left awaiting a decision."
            % (len(out), EXPECTED_CANDIDATES))
    # Rows 036 had already ruled on. 040's decisions are ABOUT these six and
    # are deliberately not treated as prior decisions here.
    decided = {d["identity_key"] for d in F36.load_ledger()["decisions"]
               if d["decision"] != "HOLD"}
    overlap = sorted({row["identity_key"] for row in out} & decided)
    if overlap:
        raise SystemExit("ABORT: already-decided rows in the package: %s"
                         % overlap)
    return out


def document() -> Dict:
    out = assert_cohort()
    return OrderedDict([
        ("schema", "ptf-milwaukee-founder-review-039/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("status", "AWAITING_FOUNDER_DECISION"),
        ("what_this_is",
         "The six rows PTF-...-FULL-CLOSURE-038 made reviewable. None is "
         "approved, none is in authority, and 036's decisions do not reach "
         "them. The verdict on each row is what the machine would do; the "
         "decision is not the machine's to make."),
        ("verdict_is_advisory_only", True),
        ("candidate_count", len(out)),
        ("counts_by_recommended_verdict",
         dict(Counter(row["recommended_machine_verdict"] for row in out))),
        ("counts_by_evidence_origin",
         dict(Counter(row["evidence_origin"] for row in out))),
        ("provider_calls_in_039", 0),
        ("candidates", out),
    ])


def report_markdown() -> str:
    doc = document()
    lines = [
        "# Six properties awaiting a founder decision -- %s" % WORK_ORDER,
        "",
        "None of these is approved. None is in authority. Nothing below was "
        "published or deployed, and 039 made no provider call.",
        "",
        "The **recommended verdict** on each row is advisory: it is what the "
        "machine would do, printed next to the evidence so disagreeing with "
        "it is cheap.",
        "",
    ]
    for index, row in enumerate(doc["candidates"], start=1):
        lines += [
            "## %d. %s" % (index, row["property_name"]),
            "",
            "| | |",
            "| --- | --- |",
            "| address | %s |" % row["address"],
            "| source read | %s |" % row["source_url"],
            "| evidence origin | %s |" % row["evidence_origin"],
            "| provider lineage | %s |" % row["provider_lineage"],
            "| identity | %s |" % row["identity_status"],
            "| locator | %s |" % row["reader_locator_status"],
            "| **recommended** | **%s** |" % row["recommended_machine_verdict"],
            "",
            "> %s" % (row["evidence_quote"][:600] or "(no quote)"),
            "",
            "**Proposed publication facts** — `%s`"
            % (json.dumps(row["proposed_publication_facts"], default=str)
               if row["proposed_publication_facts"] else
               "none proposed; see ambiguity"),
            "",
            "**Reader's current parse** — `%s`%s"
            % (json.dumps(row["current_parsed_facts"], default=str),
               "" if row["parse_is_trustworthy"]
               else "  ⚠ **not trustworthy on this row**"),
            "",
            "**What changed in 038** — %s" % row["what_changed_in_038"],
            "",
            "**Why the machine says %s** — %s"
            % (row["recommended_machine_verdict"], row["recommended_because"]),
            "",
        ]
        if row["ambiguity"]:
            lines.append("**Ambiguity**")
            lines.append("")
            for item in row["ambiguity"]:
                lines.append("* %s" % item)
            lines.append("")
        lines += ["**Founder decision:** `<UNANSWERED>`", "", "---", ""]
    lines += [
        "## Answering",
        "",
        "Reply with one of `APPROVE`, `APPROVE_REFUSAL` or `HOLD` per property "
        "name. A row with no answer stays held: silence is not approval, and "
        "an unanswered row is not a rounding error.",
        "",
    ]
    return NEWLINE.join(lines) + NEWLINE


def write(apply: bool = False) -> Dict:
    doc = document()
    if apply:
        PKG.mkdir(parents=True, exist_ok=True)
        REVIEW_JSON.write_text(
            json.dumps(doc, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
        REVIEW_MD.write_text(report_markdown(), encoding="utf-8")
    return {k: v for k, v in doc.items() if k != "candidates"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        for row in rows():
            print("%-46s %-18s %s" % (row["property_name"][:46],
                                      row["recommended_machine_verdict"],
                                      row["evidence_origin"]))
    if args.apply:
        print(json.dumps(write(apply=True), indent=2, default=str))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())

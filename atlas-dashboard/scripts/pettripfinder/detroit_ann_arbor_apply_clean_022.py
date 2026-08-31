# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ATTENDED-COMPLETION-ADOPTION-022, Phases 7 and 8.

Applies the mechanically verified clean block from the adopted Pass-020
completion. Every row here already passed order 011's publication gates
unloosened; the ones that did not are absent, not accommodated.

PROVENANCE IS RECORDED TRUTHFULLY, NOT INHERITED. The 011 builders were written
for Bright Data and hard-code ``rendered_fetch`` / ``rendered_html`` /
``PT2_BRAND``. None of that is true of an attended-Chrome capture of an
independent hotel's own site, so this run overrides them with
``attended_browser`` / ``text_extract`` / ``PT1_FIRST_PARTY``. Copying a
convenient label would put a false capture method into permanent authority.

THE EXTERNAL COMPLETION IS STAMPED WHERE IT APPLIES. 33 of these captures were
produced by a different session and adopted by this order after forensic
verification. Each record carries that, so nobody later reads this market's
history as one unbroken chain of orders it was not.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_authority_application_011 as A11,
    detroit_ann_arbor_candidate_reconciliation_011 as R11)
from scripts.pettripfinder import market_authority as MA           # noqa: E402
from scripts.pettripfinder.contracts import enums                  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ATTENDED-COMPLETION-ADOPTION-022"
PROVENANCE = "PTF-DETROIT-ANN-ARBOR-ATTENDED-020-EXTERNAL-COMPLETION-ADOPTED"
ADOPTION_COMMIT = "295607a"
EXTERNAL_COMMIT = "b5c5c6a"
DECISION_DATE = "2026-08-30"
FOUNDER = "jfields80"

LP = A11.LP
PRECHECK = LP / "detroit_ann_arbor_clean_precheck_022.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
#: Resolved through the sanctioned shard API. Spelling the generated global's
#: FILENAME here -- even while pointing at the shard -- trips the write-
#: discipline scan, and rightly so: the scan is textual precisely because a
#: module that knows that name is one edit away from writing the global.
EXCLUSIONS_PATH = MA.exclusions_shard_path(MARKET)
REPORT = LP / "detroit_ann_arbor_clean_application_022.json"

#: The 12 rows this session captured under order 020 itself. Everything else in
#: the cohort came from the adopted external completion.
OWN_CAPTURE_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020"


def own_rows():
    """The 12 identities THIS session captured, read from commit 3068310.

    THE LOOKUP MUST NOT FAIL SILENTLY. This worktree sits in a subdirectory of
    the repo, so a git object path without that prefix returns empty output --
    which would quietly label every applied record as externally captured. A
    provenance stamp that defaults to the wrong answer on a path typo is worse
    than no stamp, so both prefixes are tried and an empty result is fatal.
    """
    import subprocess
    rel = ("launch_packages/pettripfinder/"
           "detroit_ann_arbor_attended_triage_020.json")
    for prefix in ("atlas-dashboard/", ""):
        out = subprocess.run(
            ["git", "show", "3068310:%s%s" % (prefix, rel)],
            cwd=str(_REPO_ROOT), capture_output=True, text=True).stdout
        if out.strip():
            rows = {row["identity_key"] for row in json.loads(out)["results"]}
            if len(rows) != 12:
                raise SystemExit("STOP: expected 12 own-capture rows at "
                                 "3068310, read %d" % len(rows))
            return rows
    raise SystemExit("STOP: could not read the order-020 triage at 3068310; "
                     "refusing to guess which captures were this session's")


def run():
    precheck = R11.load(PRECHECK)
    passed = precheck["passed_rows"]
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    facts_doc = R11.load(FACTS_PATH)
    excl_doc = R11.load(EXCLUSIONS_PATH)
    published = {row["identity_key"] for row in facts_doc["hotels"]}
    excluded = {row["normalized_name"] for row in excl_doc["exclusions"]}
    mine = own_rows()

    # Truthful capture provenance for the attended lane.
    A11.WORK_ORDER = WORK_ORDER
    A11.DECISION_DATE = DECISION_DATE
    A11.SOURCE_GRADE = enums.GRADE_PT1_FIRST_PARTY
    A11.ARTIFACT_KIND = enums.ARTIFACT_TEXT_EXTRACT
    A11.CAPTURE_METHOD = "attended_browser"

    # A committed test forbids this alias appearing in ANY tracked citation
    # artifact. The publication gate does not know about it -- that rule lives
    # in the Sonesta identity suite -- so a row can pass every gate and still
    # break the build. Caught here and withheld, NOT resolved by narrowing the
    # test to admit this order's own data.
    banned_url_fragments = {
        "sonesta-es-suites":
            "tests/pettripfinder/test_sonesta_identity_and_scope.py forbids "
            "this fragment in any tracked citation artifact. Detroit's ES "
            "Suites Auburn Hills appears to be a LEGITIMATE current "
            "first-party URL, so this is a test-scope conflict for the "
            "founder, not bad evidence -- withheld pending that ruling.",
    }

    # The Pass-3 founder review packet is FROZEN by committed guards: its two
    # POLICY_NOT_FOUND holds may not enter authority, and any identity in it
    # that publishes must name EVIDENCE-VOCABULARY-AND-PROMOTION-004 as its
    # authorising instrument -- which an order-022 record cannot do. Daxton is
    # a Pass-3 hold that this cohort ANSWERED with real first-party evidence,
    # which is arguably the hold working as intended, but that is a founder
    # call about the scope of a freeze guard and not a thing to settle by
    # editing the guard during the application it would block.
    pass3 = R11.load(LP / "detroit_ann_arbor_capture_pass3_founder_review_"
                          "packet.json")
    pass3_keys = {c["identity_key"] for c in pass3["candidates"]}

    new_facts, new_excl, applied, withheld = [], [], [], []
    for row in passed:
        key = row["identity_key"]
        if key in pass3_keys:
            withheld.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", row["canonical_name"]),
                ("canonical_url", row["canonical_url"]),
                ("reason",
                 "identity is in the FROZEN Pass-3 founder review packet. "
                 "tests/pettripfinder/test_detroit_ann_arbor_capture_pass3_"
                 "001.py forbids its two holds from entering authority at all, "
                 "and requires any published packet identity to name "
                 "EVIDENCE-VOCABULARY-AND-PROMOTION-004. This row is a Pass-3 "
                 "POLICY_NOT_FOUND hold that the attended cohort ANSWERED on "
                 "the property's own /faq. Withheld pending a founder ruling "
                 "on the freeze guard's scope -- not resolved by editing it."),
            ]))
            continue
        hit = [f for f in banned_url_fragments
               if f in (row["canonical_url"] or "")]
        if hit:
            withheld.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", row["canonical_name"]),
                ("canonical_url", row["canonical_url"]),
                ("reason", banned_url_fragments[hit[0]]),
            ]))
            continue
        if key in published or key in excluded:
            raise SystemExit("STOP: %r already carries authority" % key)
        census_row = census[key]
        external = key not in mine
        candidate = dict(row["gate_candidate"])
        # The 011 builders were written for a paid pass and expect an
        # attempt id and a source pass. The attended lane has neither: there
        # is no provider attempt to point at. Both are stamped with what is
        # actually true rather than borrowed from a paid run.
        candidate["attempt_id"] = "attended:%s" % row["block_sha256"][:16]
        candidate["source_pass"] = (
            "%s (external completion, adopted %s)" % (OWN_CAPTURE_ORDER,
                                                      ADOPTION_COMMIT)
            if external else OWN_CAPTURE_ORDER)
        source_url = row["canonical_url"]

        if row["verdict_class"] == "PET_FRIENDLY":
            record = A11.build_publication_record(candidate, census_row,
                                                  source_url)
            target = new_facts
        else:
            record = A11.build_exclusion_record(candidate, census_row,
                                                source_url)
            target = new_excl

        approval = record.get("approval") or OrderedDict()
        approval["operator"] = FOUNDER
        approval["approval_date"] = DECISION_DATE
        approval["authorisation"] = OrderedDict([
            ("instrument", WORK_ORDER),
            ("clause", "Founder authorizes the mechanically verified CLEAN "
                       "BLOCK as one block. Apply only rows that pass the "
                       "current publication gates."),
            ("scope", "the clean block, gate-passing rows only"),
            ("lane", "attended_chrome"), ("spend_usd", 0.0),
        ])
        approval["capture_provenance"] = OrderedDict([
            ("acquired_by_order", OWN_CAPTURE_ORDER),
            ("captured_by",
             "this session, order 020" if not external
             else "A DIFFERENT SESSION -- adopted, not produced, by %s"
                  % WORK_ORDER),
            ("external_completion", external),
            ("provenance_event", PROVENANCE if external else ""),
            ("external_commit", EXTERNAL_COMMIT if external else ""),
            ("adoption_commit", ADOPTION_COMMIT if external else ""),
            ("capture_method", "attended_browser"),
            ("artifact_kind", enums.ARTIFACT_TEXT_EXTRACT),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("provider_calls", 0), ("spend_usd", 0.0),
        ])
        record["approval"] = approval
        target.append(record)
        applied.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("class", row["verdict_class"]),
            ("external_completion", external),
        ]))

    facts_doc["hotels"] = list(facts_doc["hotels"]) + new_facts
    A11.write_lf(FACTS_PATH, facts_doc)
    if new_excl:
        excl_doc["exclusions"] = list(excl_doc["exclusions"]) + new_excl
        excl_doc["count"] = len(excl_doc["exclusions"])
        A11.write_lf(EXCLUSIONS_PATH, excl_doc)

    R11.write_lf(REPORT, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-clean-application/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("adoption_commit", ADOPTION_COMMIT),
        ("external_commit", EXTERNAL_COMMIT),
        ("applied_pet_friendly", len(new_facts)),
        ("applied_verified_no_pets", len(new_excl)),
        ("from_external_completion",
         sum(1 for a in applied if a["external_completion"])),
        ("from_this_sessions_own_capture",
         sum(1 for a in applied if not a["external_completion"])),
        ("withheld_on_a_committed_cross_market_rule", withheld),
        ("gate_rejected", precheck["gates"]["rejected"]),
        ("rejections", [OrderedDict([
            ("canonical_name", r["canonical_name"]),
            ("class", r["verdict_class"]),
            ("reason", r["gate_failures"]),
        ]) for r in precheck["rejected_rows"]]),
        ("applied", applied),
    ]))

    print("=== Phases 7-8: clean block applied ===")
    print("  pet-friendly applied   :", len(new_facts))
    print("  verified-no-pets applied:", len(new_excl))
    print("  from external completion:",
          sum(1 for a in applied if a["external_completion"]))
    print("  from this session's own :",
          sum(1 for a in applied if not a["external_completion"]))
    for w in withheld:
        print("  WITHHELD %s -- %s" % (w["canonical_name"], w["reason"][:60]))
    print("  pet-friendly total now :", len(facts_doc["hotels"]))
    print("  exclusions total now   :", len(excl_doc["exclusions"]))


if __name__ == "__main__":
    run()

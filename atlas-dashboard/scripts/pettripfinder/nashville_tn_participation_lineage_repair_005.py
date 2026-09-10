"""PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 -- a defect this launch cannot repair itself.

WHAT WENT WRONG

``nashville_tn_launch_authorization_005.py --write-participation`` rebuilt the
``decision`` block of ``deploy/netlify/launch_participation.json`` from scratch
instead of extending the one already there. Two fields were lost:

  supersedes   the immediate predecessor decision, with its own sha256
  lineage      every ancestor decision, oldest first, each with the sha256 the
               participation record had when that decision was written

The lineage is what lets a deployment authorization be matched to the
participation record it signed after more than one reissue. The 047
authorization is four reissues back; without the lineage nothing can prove which
record it bound, and ``test_deployment_authorization_047`` says so by failing.

WHY IT IS NOT REPAIRED HERE

``launch_participation.json`` is bound by sha256 into the LIVE deployment
authorization. Editing it now makes the authorization that production is running
under stop verifying against its own repository -- the release chain would read
as broken to say that a prose block is missing. The file changes on the next
participation write, when a new authorization binds the new hash; that is when
the block goes back, and it is the only moment it can.

WHAT THIS WRITES INSTEAD

The exact block the next participation write must restore, derived rather than
typed: the ancestors are read from the last commit that still carried them, and
each new record's sha256 is the real hash of the participation file at the
commit where that decision was written. The same invariants ``047`` asserts are
checked here before anything is written, so the repair is known-good before it
is handed on.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
LEXINGTON = "PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
PARTICIPATION = "atlas-dashboard/deploy/netlify/launch_participation.json"
OUT = (_DASH / "launch_packages" / "pettripfinder" / "markets" / "reports"
       / "nashville_tn_participation_lineage_defect_005.json")
AUTHORIZED = "FOUNDER_AUTHORIZED_FOR_LAUNCH"


def blob(commit):
    """The participation file exactly as ``commit`` committed it."""
    return subprocess.run(["git", "show", "%s:%s" % (commit, PARTICIPATION)],
                          cwd=str(_DASH.parent), check=True,
                          stdout=subprocess.PIPE).stdout


def record_at(commit):
    """One lineage record for the decision that commit wrote."""
    raw = blob(commit)
    doc = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    return OrderedDict((
        ("work_order", doc["decision"]["work_order"]),
        ("sha256", hashlib.sha256(raw).hexdigest()),
        ("founder_authorized", sorted(row["market_id"] for row in doc["markets"]
                                      if row["launch_status"] == AUTHORIZED)),
    )), doc


def check(records, current_sha, *, current_is_an_ancestor):
    """Exactly what test_deployment_authorization_047 asserts about a lineage."""
    problems = []
    shas = [r["sha256"] for r in records]
    if len(shas) != len(set(shas)):
        problems.append("a lineage may not repeat a record")
    counts = [len(r["founder_authorized"]) for r in records]
    if counts != sorted(counts):
        problems.append("the authorized set only ever grew: %s" % counts)
    if not current_is_an_ancestor and current_sha in shas:
        problems.append("the current record may not appear in its own lineage")
    if current_is_an_ancestor and current_sha != shas[-1]:
        problems.append("the current record must be the newest ancestor")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ancestors-from", required=True,
                    help="the last commit whose decision block still carried a lineage")
    ap.add_argument("--lexington-commit", required=True,
                    help="the commit that wrote the Lexington launch decision")
    args = ap.parse_args(argv)

    from scripts.pettripfinder import launch_participation as LP

    prior = json.loads(blob(args.ancestors_from).decode("utf-8-sig"),
                       object_pairs_hook=OrderedDict)["decision"]
    ancestors = list(prior["lineage"]["records"])
    if prior["work_order"] != LEXINGTON:
        raise SystemExit("REFUSING: %s carries the %s decision, not Lexington's"
                         % (args.ancestors_from, prior["work_order"]))

    lexington, lex_doc = record_at(args.lexington_commit)
    if lexington["work_order"] != LEXINGTON:
        raise SystemExit("REFUSING: %s did not write the Lexington decision"
                         % args.lexington_commit)
    if lexington["sha256"] in {r["sha256"] for r in ancestors}:
        raise SystemExit("REFUSING: the Lexington record is already an ancestor")

    current_sha = LP.participation_sha256()
    current = json.loads(
        (_DASH / "deploy" / "netlify" / "launch_participation.json")
        .read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
    nashville = OrderedDict((
        ("work_order", current["decision"]["work_order"]),
        ("sha256", current_sha),
        ("founder_authorized", sorted(row["market_id"] for row in current["markets"]
                                      if row["launch_status"] == AUTHORIZED)),
    ))
    if nashville["work_order"] != WORK_ORDER:
        raise SystemExit("REFUSING: the committed decision is %s" % nashville["work_order"])

    should_be_now = ancestors + [lexington]
    for_the_next_write = should_be_now + [nashville]
    problems = (check(should_be_now, current_sha, current_is_an_ancestor=False)
                + check(for_the_next_write, current_sha, current_is_an_ancestor=True))
    if problems:
        raise SystemExit("REFUSING: the repair does not satisfy the lineage contract: %s"
                         % problems)

    doc = OrderedDict((
        ("schema", "ptf-participation-lineage-defect/1.0"),
        ("work_order", WORK_ORDER),
        ("severity", "the record is incomplete; nothing live is wrong"),
        ("what_broke",
         "--write-participation rebuilt the decision block instead of extending it, so "
         "decision.supersedes and decision.lineage were dropped. The lineage is how a "
         "deployment authorization signed several reissues back is matched to the "
         "participation record it bound; without it that match cannot be made at all."),
        ("why_it_is_not_repaired_here",
         "launch_participation.json is bound by sha256 into the LIVE deployment "
         "authorization %s. Rewriting it now would make the authorization production is "
         "running under stop verifying against its own repository. The block goes back on "
         "the next participation write, when a new authorization binds the new hash."
         % "ptf-auth-nashville-005-c12b410ec833"),
        ("current_participation_sha256", current_sha),
        ("what_the_current_file_should_have_carried", OrderedDict((
            ("supersedes", lexington),
            ("lineage", OrderedDict((
                ("what_this_is", prior["lineage"]["what_this_is"]),
                ("records", should_be_now),
            ))),
        ))),
        ("what_the_next_participation_write_must_carry", OrderedDict((
            ("supersedes", nashville),
            ("lineage", OrderedDict((
                ("what_this_is", prior["lineage"]["what_this_is"]),
                ("records", for_the_next_write),
            ))),
            ("note", "supersedes names the Nashville decision because that is the one the "
                     "next write replaces, and the Nashville record joins the lineage at "
                     "the same moment it stops being current."),
        ))),
        ("derivation", OrderedDict((
            ("ancestors_read_from", args.ancestors_from),
            ("lexington_record_measured_at", args.lexington_commit),
            ("lexington_sha256_is_what_its_authorization_bound", True),
            ("how", "each record's sha256 is the real hash of the participation file at "
                    "the commit that wrote that decision. Nothing here is transcribed."),
        ))),
        ("contract_checked_before_writing", OrderedDict((
            ("no_repeated_record", True),
            ("authorized_set_only_grew", True),
            ("current_record_absent_from_its_own_lineage", True),
            ("checked_by", "the same assertions as "
                           "test_deployment_authorization_047::"
                           "test_the_lineage_is_ordered_and_ends_before_the_current_record"),
        ))),
        ("authorizations_that_need_this_lineage_to_be_matchable",
         [r["work_order"] for r in should_be_now]),
    ))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("ancestors read from :", args.ancestors_from, "(%d records)" % len(ancestors))
    print("lexington record    :", lexington["sha256"],
          "(%d markets)" % len(lexington["founder_authorized"]))
    print("nashville record    :", nashville["sha256"],
          "(%d markets)" % len(nashville["founder_authorized"]))
    print("current file        :", current_sha)
    print("contract problems   : 0")
    print("written             :", OUT.relative_to(_DASH).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

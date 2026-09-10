"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- the two shared registries.

Registering a market touches two documents that belong to every market:

  deploy/netlify/launch_participation.json                 a row for the market
  launch_packages/pettripfinder/bundle_cache_closure.json  its two declared inputs

Both are edited here rather than by hand so the change is auditable and
re-runnable, which is what PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-
PREP-002 established for the same pair.

THE CLOSURE
-----------
The build closure enumerates every registered market's market document and
release contract BY NAME, because a per-market build reads all of them while
resolving the registry. Registering Charlotte therefore extends it by exactly
two paths. Until they are declared the bundle cache counts them as undeclared
reads and publishes every bundle UNTRUSTED -- which is the guard working, not
failing: an unlisted input is an input nobody proved constant. The symptom is
`test_atlas_throughput_004::TestCrossRun` reading UNTRUSTED on a build of
DAYTON, a market Charlotte never touched.

CHARLOTTE'S PARTICIPATION ROW

A REGISTERED market must carry an EXPLICIT participation status. That is not a
style rule: `launch_participation.verify_participation` reports any registered
market missing from the document as `unlisted`, and
`test_release_composition_contract_006` asserts that list is empty. Silence is
not a decision, so Charlotte gets a row saying, in the document's own
vocabulary, that it is source-ready and NOT authorized:

    SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH

which is exactly what Detroit has carried since its own registration. This
module DOES NOT authorize anything and does not touch the authorized set.

WHY THIS IS A REISSUE AND NOT AN EDIT
-------------------------------------
The participation record is sha256-bound into the live deployment
authorization, and the current file's decision block carries no chain of its
own -- it is legal only because the repair record committed beside it by
PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006 covers that file at that
exact sha256. Changing a single byte makes the repair stop covering it and
`load_participation()` then refuses with "the decision chain is broken". The
failure is silent until something loads the document, at which point the
assembler reads EVERY market as UNLISTED and refuses the whole build.

So the write goes through `extend_decision(..., path=...)`, which pulls the
ancestors out of the repair record and puts the chain back whole -- 8 records
forward to 9 -- instead of starting a fresh one-link chain that would lose
eight orders of lineage.

Output: launch_packages/pettripfinder/markets/reports/charlotte_nc_participation_registration_010.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import launch_participation as LP  # noqa: E402
from scripts.pettripfinder.market_authority import load_markets  # noqa: E402

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
DECIDED_BY = WORK_ORDER
REASON = (
    "Charlotte is registered, releasable and NOT authorized. This write records that "
    "third fact explicitly so the market is not merely absent from the participation "
    "document, which the assembler and the composition contract both read as UNLISTED. "
    "The founder-authorized set is unchanged at thirteen markets; the founder's Charlotte "
    "decision, if it comes, is a separate write.")
OUT = (_DASH / "launch_packages" / "pettripfinder" / "markets" / "reports"
       / "charlotte_nc_participation_registration_010.json")


def market_row() -> "OrderedDict[str, object]":
    """The row, with the SAME keys Detroit's carries and no others.

    An unknown key here is not harmless: the row is read by the assembler and
    by the composition contract, and a key neither of them knows is a claim
    nobody validates.
    """
    doc = LP.load_participation()
    template = next((m for m in doc["markets"]
                     if m["market_id"] == "detroit-ann-arbor-mi"), None)
    if template is None:
        raise SystemExit("no withheld market to take the row shape from")
    row: "OrderedDict[str, object]" = OrderedDict()
    for key in template:
        row[key] = template[key]
    row["market_id"] = MARKET_ID
    row["launch_status"] = LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
    for key in ("note", "reason", "why", "rationale"):
        if key in row:
            row[key] = (
                "Built from zero on the redesigned factory by %s: 268 registered "
                "identities, 106 published, 41 verified-no-pets. Source-ready and "
                "awaiting a founder launch decision." % WORK_ORDER)
    for key in ("recorded_by", "work_order", "registered_by", "decided_by"):
        if key in row:
            row[key] = WORK_ORDER
    for key in ("recorded_on", "registered_on", "as_of"):
        if key in row:
            row[key] = time.strftime("%Y-%m-%d", time.gmtime())
    return row


CLOSURE_PATH = _DASH / "launch_packages" / "pettripfinder" / "bundle_cache_closure.json"
CLOSURE_INPUTS = ("deploy/netlify/release_contracts/%s.json" % MARKET_ID,
                  "launch_packages/pettripfinder/markets/%s.json" % MARKET_ID)
CLOSURE_NOTE = (
    "%s: the closure enumerates every REGISTERED market's market document and release "
    "contract by name, so registering Charlotte extends it by exactly two paths. Until "
    "they are declared the bundle cache calls them undeclared reads and publishes every "
    "bundle UNTRUSTED -- including bundles of markets Charlotte never touched, which is "
    "how it was found: a cold DAYTON build read UNTRUSTED. That is the guard working; an "
    "unlisted input is an input nobody proved constant." % WORK_ORDER)


def wire_closure(*, write: bool):
    """Declare Charlotte's two shared data inputs. Returns what it added."""
    doc = json.loads(CLOSURE_PATH.read_text(encoding="utf-8-sig"),
                     object_pairs_hook=OrderedDict)
    shared = list(doc["shared_data_inputs"])
    added = [p for p in CLOSURE_INPUTS if p not in shared]
    for p in CLOSURE_INPUTS:
        if not (_DASH / p).is_file():
            raise SystemExit("declared input does not exist: %s" % p)
    if not added:
        return []
    doc["shared_data_inputs"] = sorted(shared + added)
    doc["remeasured_by"] = list(doc.get("remeasured_by") or []) + [CLOSURE_NOTE]
    if write:
        CLOSURE_PATH.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                                encoding="utf-8", newline="\n")
    return added


def closure_only_report(prior_sha, closure_added, args):
    report = OrderedDict((
        ("schema", "ptf-participation-registration/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("written", bool(args.write)),
        ("participation_row_already_present", True),
        ("participation_sha256", prior_sha),
        ("launch_status", LP.launch_status(MARKET_ID)),
        ("founder_authorized", sorted(LP.authorized_market_ids())),
        ("closure_inputs_declared", list(CLOSURE_INPUTS)),
        ("closure_inputs_added_by_this_run", closure_added),
        ("decision_problems", LP.decision_problems(LP.load_participation())),
    ))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")
    for key, value in report.items():
        if key not in ("schema", "work_order", "market_id", "as_of"):
            print("%-34s %s" % (key, value))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    path = LP.PARTICIPATION_PATH
    prior = json.loads(path.read_text(encoding="utf-8-sig"))
    prior_sha = LP.participation_sha256(path)
    before = sorted(LP.authorized_market_ids(prior))

    already = any(m["market_id"] == MARKET_ID for m in prior["markets"])
    closure_added = wire_closure(write=args.write)

    if already:
        # The row is in place; the run is here for the closure, or to re-report.
        report = closure_only_report(prior_sha, closure_added, args)
        return 0

    doc = json.loads(json.dumps(prior), object_pairs_hook=OrderedDict)
    doc["markets"].append(market_row())
    doc["markets"] = sorted(doc["markets"], key=lambda m: m["market_id"])
    doc["decision"] = LP.extend_decision(
        prior, prior_sha, work_order=WORK_ORDER, decided_by=DECIDED_BY,
        decided_on=time.strftime("%Y-%m-%d", time.gmtime()), reason=REASON, path=path,
        markets_added=[MARKET_ID],
        founder_authorized_set_unchanged=True)

    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    # Validate against the bytes this WOULD write, not against the file still on
    # disk: `decision_problems` re-hashes `path`, and the file still on disk is
    # the predecessor, which the new block quite properly names as its newest
    # ancestor. Checking the new block against the old file therefore reports
    # "a decision may not be its own ancestor" about a record that is not the
    # current one yet. A scratch copy is the only honest thing to hash.
    scratch = path.with_name(path.name + ".candidate")
    try:
        scratch.write_text(text, encoding="utf-8", newline="\n")
        problems = LP.decision_problems(doc, path=scratch)
    finally:
        if scratch.exists():
            scratch.unlink()

    if args.write and not problems:
        path.write_text(text, encoding="utf-8", newline="\n")
        reloaded = LP.load_participation()
        problems = LP.decision_problems(reloaded, path=path)
        registered = [m.market_id for m in load_markets()]
        from scripts.pettripfinder.assemble_production_site import market_eligibility
        rows = {m.market_id: market_eligibility(m)["assemblable"] for m in load_markets()}
        verify = LP.verify_participation(registered, rows)
    else:
        reloaded, verify = doc, None

    chain = LP.decision_chain(reloaded, path) if args.write else {"records": []}
    report = OrderedDict((
        ("schema", "ptf-participation-registration/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("written", bool(args.write and not problems)),
        ("prior_sha256", prior_sha),
        ("new_sha256", LP.participation_sha256(path) if args.write else ""),
        ("launch_status", LP.launch_status(MARKET_ID, reloaded)),
        ("founder_authorized_before", before),
        ("founder_authorized_after", sorted(LP.authorized_market_ids(reloaded))),
        ("founder_authorized_set_unchanged",
         before == sorted(LP.authorized_market_ids(reloaded))),
        ("decision_chain_records", len(chain.get("records") or [])),
        ("decision_chain_carried_by", chain.get("carried_by", "")),
        ("decision_problems", problems),
        ("verify_participation", verify),
    ))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")
    for key in ("written", "prior_sha256", "new_sha256", "launch_status",
                "founder_authorized_set_unchanged", "decision_chain_records",
                "decision_problems", "verify_participation"):
        print("%-32s %s" % (key, report[key]))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

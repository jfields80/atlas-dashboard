"""PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006 -- the decision chain contract.

WHAT WENT WRONG, AND WHY NOTHING CAUGHT IT

PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 rebuilt the
participation ``decision`` block from scratch instead of extending the committed
one, and ``supersedes`` and ``lineage`` were simply not written. The record
loaded cleanly afterwards because ``load_participation`` checked four fields and
neither of those was among them. The lineage is how a deployment authorization
signed several reissues back is matched to the participation record it bound --
047 is four reissues back -- so losing it costs a real proof, silently.

So the defect is not "a writer forgot a field". It is that the contract did not
ask. These tests are the asking:

  * ``decision_problems`` REFUSES a block with no chain, which is the exact
    shape 005 committed;
  * ``extend_decision`` makes the correct block the easy one to write, because
    it builds from the predecessor rather than from nothing;
  * the one documented exception -- a chain that cannot be restored because the
    record is sha256-bound into the LIVE authorization -- is allowed only while
    a repair record names that exact record, and is refused the moment it does
    not.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder import launch_participation as LP

REPO = Path(__file__).resolve().parents[2]
AUTHORIZED = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
WITHHELD = LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH


def _doc(authorized, withheld=(), *, work_order, chain=None):
    doc = {
        "schema": LP.PARTICIPATION_SCHEMA,
        "decision": {
            "work_order": work_order,
            "decided_by": "founder",
            "decided_on": "2026-09-10",
            "reason": "a decision",
        },
        "markets": ([{"market_id": m, "launch_status": AUTHORIZED} for m in authorized]
                    + [{"market_id": m, "launch_status": WITHHELD} for m in withheld]),
    }
    if chain:
        doc["decision"].update(chain)
    return doc


def _write(tmp_path, doc, name="launch_participation.json"):
    path = tmp_path / name
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path


class TestExtendDecisionCarriesTheChain:

    def test_the_predecessor_becomes_the_newest_ancestor(self, tmp_path):
        first = _doc(["columbus-oh"], work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        first_path = _write(tmp_path, first)
        first_sha = LP.participation_sha256(first_path)

        block = LP.extend_decision(first, first_sha,
                                   work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011",
                                   decided_by="founder", decided_on="2026-09-10",
                                   reason="admit st-louis")
        assert block["supersedes"]["work_order"] == first["decision"]["work_order"]
        assert block["supersedes"]["sha256"] == first_sha
        assert block["supersedes"]["founder_authorized"] == ["columbus-oh"]
        assert [r["sha256"] for r in block["lineage"]["records"]] == [first_sha]

    def test_every_ancestor_comes_forward_whole(self, tmp_path):
        """The failure mode was losing the chain, so the chain is what is counted."""
        doc = _doc(["columbus-oh"], work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        orders = ["PTF-ST-LOUIS-REGISTER-PUBLISH-011",
                  "PTF-LOUISVILLE-PUBLICATION-008",
                  "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"]
        markets = ["st-louis-mo", "louisville-ky", "toledo-oh"]
        for step, (order, market) in enumerate(zip(orders, markets), start=1):
            path = _write(tmp_path, doc)
            sha = LP.participation_sha256(path)
            nxt = _doc([m["market_id"] for m in doc["markets"]] + [market],
                       work_order=order)
            nxt["decision"] = LP.extend_decision(
                doc, sha, work_order=order, decided_by="founder",
                decided_on="2026-09-10", reason="admit %s" % market)
            doc = nxt
            assert len(doc["decision"]["lineage"]["records"]) == step
        assert [r["work_order"] for r in doc["decision"]["lineage"]["records"]] == \
            ["PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046"] + orders[:-1]
        assert LP.decision_problems(doc, path=_write(tmp_path, doc)) == []

    def test_it_is_deterministic(self, tmp_path):
        first = _doc(["columbus-oh"], work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        sha = LP.participation_sha256(_write(tmp_path, first))
        kwargs = dict(work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011", decided_by="founder",
                      decided_on="2026-09-10", reason="admit st-louis")
        a = json.dumps(LP.extend_decision(first, sha, **kwargs))
        b = json.dumps(LP.extend_decision(first, sha, **kwargs))
        assert a == b
        assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()

    def test_the_decisions_own_fields_are_kept_and_the_chain_stays_last(self, tmp_path):
        first = _doc(["columbus-oh"], work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        sha = LP.participation_sha256(_write(tmp_path, first))
        block = LP.extend_decision(first, sha,
                                   work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011",
                                   decided_by="founder", decided_on="2026-09-10",
                                   reason="admit st-louis",
                                   markets_moved=["st-louis-mo"],
                                   registered_but_still_withheld=["detroit-ann-arbor-mi"])
        assert block["markets_moved"] == ["st-louis-mo"]
        assert block["registered_but_still_withheld"] == ["detroit-ann-arbor-mi"]
        assert list(block)[-2:] == ["supersedes", "lineage"]

    def test_a_decision_may_not_supersede_itself(self, tmp_path):
        first = _doc(["columbus-oh"], work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        sha = LP.participation_sha256(_write(tmp_path, first))
        second = copy.deepcopy(first)
        second["decision"] = LP.extend_decision(
            first, sha, work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011",
            decided_by="founder", decided_on="2026-09-10", reason="x")
        with pytest.raises(LP.LaunchParticipationError):
            LP.extend_decision(second, sha, work_order="PTF-LOUISVILLE-PUBLICATION-008",
                               decided_by="founder", decided_on="2026-09-10", reason="y")


class TestTheContractRefusesWhatTheNashvilleLaunchWrote:

    def test_a_block_with_no_chain_is_refused(self, tmp_path):
        """The exact shape 005 committed, with no repair record in reach."""
        doc = _doc(["columbus-oh", "nashville-tn"],
                   work_order="PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005")
        problems = LP.decision_problems(doc, path=_write(tmp_path, doc))
        assert problems, "a dropped chain must be refused"
        assert any("supersedes" in p for p in problems)
        assert any("lineage" in p for p in problems)

    def test_load_participation_refuses_it_too(self, tmp_path):
        doc = _doc(["columbus-oh"], work_order="PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003")
        path = _write(tmp_path, doc)
        with pytest.raises(LP.LaunchParticipationError) as caught:
            LP.load_participation(path)
        assert "decision chain is broken" in str(caught.value)

    def test_a_repeated_ancestor_is_refused(self, tmp_path):
        first = _doc(["columbus-oh"], work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        sha = LP.participation_sha256(_write(tmp_path, first))
        block = LP.extend_decision(first, sha, work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011",
                                   decided_by="founder", decided_on="2026-09-10", reason="x")
        block["lineage"]["records"].append(dict(block["lineage"]["records"][0]))
        doc = _doc(["columbus-oh", "st-louis-mo"],
                   work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011", chain=block)
        assert any("repeats a record" in p
                   for p in LP.decision_problems(doc, path=_write(tmp_path, doc)))

    def test_a_shrinking_authorized_set_is_refused(self, tmp_path):
        first = _doc(["columbus-oh", "dayton-oh"],
                     work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        sha = LP.participation_sha256(_write(tmp_path, first))
        block = LP.extend_decision(first, sha, work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011",
                                   decided_by="founder", decided_on="2026-09-10", reason="x")
        block["lineage"]["records"].insert(
            0, {"work_order": "PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046",
                "sha256": "b" * 64,
                "founder_authorized": ["a", "b", "c", "d"]})
        doc = _doc(["columbus-oh", "dayton-oh"],
                   work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011", chain=block)
        assert any("shrinks the authorized set" in p
                   for p in LP.decision_problems(doc, path=_write(tmp_path, doc)))

    def test_dropping_a_market_the_previous_decision_authorized_is_refused(self, tmp_path):
        """No unrelated participant decision may be lost by a later write."""
        first = _doc(["columbus-oh", "toledo-oh"],
                     work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        sha = LP.participation_sha256(_write(tmp_path, first))
        block = LP.extend_decision(first, sha, work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011",
                                   decided_by="founder", decided_on="2026-09-10", reason="x")
        doc = _doc(["columbus-oh", "st-louis-mo"],   # toledo-oh silently gone
                   work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011", chain=block)
        assert any("drops market(s)" in p and "toledo-oh" in p
                   for p in LP.decision_problems(doc, path=_write(tmp_path, doc)))

    def test_supersedes_must_name_the_newest_ancestor(self, tmp_path):
        first = _doc(["columbus-oh"], work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        sha = LP.participation_sha256(_write(tmp_path, first))
        block = LP.extend_decision(first, sha, work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011",
                                   decided_by="founder", decided_on="2026-09-10", reason="x")
        block["supersedes"] = dict(block["supersedes"], sha256="c" * 64)
        doc = _doc(["columbus-oh", "st-louis-mo"],
                   work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011", chain=block)
        assert any("newest ancestor" in p
                   for p in LP.decision_problems(doc, path=_write(tmp_path, doc)))

    def test_a_record_may_not_be_its_own_ancestor(self, tmp_path):
        """Checked BEFORE the write, against the record about to be replaced.

        A writer that pins the predecessor's hash but never changes the content
        would produce a record listing itself as its own ancestor, and the
        matching that lineage exists for would return two answers.
        """
        first = _doc(["columbus-oh"],
                     work_order="PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046")
        first_path = _write(tmp_path, first)
        first_sha = LP.participation_sha256(first_path)

        second = _doc(["columbus-oh", "st-louis-mo"],
                      work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011")
        second["decision"] = LP.extend_decision(
            first, first_sha, work_order="PTF-ST-LOUIS-REGISTER-PUBLISH-011",
            decided_by="founder", decided_on="2026-09-10", reason="admit st-louis")
        second_path = _write(tmp_path, second, name="second.json")
        assert LP.decision_problems(second, path=second_path) == []

        # The defect: the record was never actually replaced, so the file it
        # names as its predecessor is the file itself.
        assert any("its own ancestor" in p
                   for p in LP.decision_problems(second, path=first_path))


class TestTheCommittedRecordAndItsOneDocumentedException:
    """The documented exception ENDED at PTF-CHARLOTTE-NC-ZERO-TO-LIVE-
    BENCHMARK-001.

    PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005 rebuilt the
    decision block instead of extending it and dropped the chain. It could not
    be put back at the time: the participation record is sha256-bound into the
    LIVE deployment authorization, so any edit had to wait for a write that had
    its own reason to exist. PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006
    therefore committed a REPAIR RECORD beside it, naming the exact sha256 it
    covered and the exact block the next write had to carry.

    Registering Charlotte was that next write, and it carried exactly that
    block. So these tests now assert the closure rather than the exception: the
    chain is in the record itself, and the repair record is spent history whose
    prescription can be checked against what was actually written.
    """

    def test_the_committed_record_loads_and_its_chain_is_reachable(self):
        doc = LP.load_participation()
        chain = LP.decision_chain(doc)
        assert chain["supersedes"]["work_order"] == \
            "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
        assert len(chain["records"]) >= 9
        assert chain["records"][0]["work_order"] == \
            "PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046"

    def test_the_record_carries_its_own_chain_again(self):
        """Honest about where the chain lives -- and it lives at home again."""
        decision = LP.load_participation()["decision"]
        assert LP.decision_chain()["carried_by"] == LP.PARTICIPATION_PATH.name
        assert decision["supersedes"]
        assert decision["lineage"]["records"]
        # And no repair record covers the current file any more, which is what
        # "closed" means: the cover was per-sha256 and this is a new record.
        assert LP._repair_covers(LP.PARTICIPATION_PATH) is None

    def test_a_stale_repair_record_does_not_excuse_a_missing_chain(self, tmp_path):
        """The exception is per-record, not a standing licence.

        The repair names the exact participation sha256 it covers. Any other
        record -- a later one, an edited one -- gets no cover at all.
        """
        doc = _doc(["columbus-oh"],
                   work_order="PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005")
        other = _write(tmp_path, doc)
        assert LP.participation_sha256(other) != json.loads(
            LP.LINEAGE_REPAIR_PATH.read_text(encoding="utf-8-sig")
        )["current_participation_sha256"]
        assert LP.decision_problems(doc, path=other)

    def test_the_repair_names_the_block_the_next_write_must_carry(self):
        repair = json.loads(LP.LINEAGE_REPAIR_PATH.read_text(encoding="utf-8-sig"))
        nxt = repair["what_the_next_participation_write_must_carry"]
        # The record it prescribed FOR is the one the next write superseded, so
        # the sha it names is now the newest ancestor rather than the current
        # file. That is the prescription being spent, not being wrong.
        assert nxt["supersedes"]["sha256"] == \
            LP.decision_chain()["records"][-1]["sha256"]
        assert nxt["supersedes"]["sha256"] != LP.participation_sha256()
        assert nxt["supersedes"]["work_order"] == \
            "PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
        records = nxt["lineage"]["records"]
        assert records[-1] == nxt["supersedes"]
        assert [r["sha256"] for r in records] == sorted(
            {r["sha256"] for r in records}, key=[r["sha256"] for r in records].index)
        counts = [len(r["founder_authorized"]) for r in records]
        assert counts == sorted(counts)

    def test_the_next_write_would_produce_exactly_that_block(self):
        """The committed decision agrees with the repair's prescription.

        The two were derived independently -- the repair from git, the write
        from ``extend_decision`` reading the contract -- so agreeing is evidence
        rather than a tautology. This ASSERTED A PREDICTION until the write
        happened; it now asserts the outcome, which is the stronger claim: the
        chain that came back is the chain that was lost, and not merely a
        well-formed one.
        """
        decision = LP.load_participation()["decision"]
        expected = json.loads(LP.LINEAGE_REPAIR_PATH.read_text(
            encoding="utf-8-sig"))["what_the_next_participation_write_must_carry"]
        assert decision["supersedes"] == expected["supersedes"]
        assert decision["lineage"]["records"] == expected["lineage"]["records"]
        # The write that carried it was a registration, not a launch: it is
        # named, and it moved no authorization.
        assert decision["work_order"] == "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
        assert LP.authorized_market_ids() == decision["supersedes"]["founder_authorized"]

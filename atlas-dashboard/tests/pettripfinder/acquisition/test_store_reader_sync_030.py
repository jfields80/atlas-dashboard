"""PTF-MILWAUKEE-STORE-READER-SYNC-030.

WHAT THESE TESTS GUARD
----------------------
The store now DERIVES what it says. That is more useful and more dangerous
than projecting a journal: a reader change reaches a hundred and fourteen rows
at once, and the thing standing between an improvement and a silent corruption
is that selection stays frozen, the block stays the one the observation was
about, and the run's own reading is still on the row beside the derived one.

So the tests are mostly about what must NOT move: which observation wins, which
block it is read from, what the journals still say, and the fact that a
derived row never claims to be what the run reported.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import store_integration_025 as S
from scripts.pettripfinder.acquisition import store_reader_sync_030 as R
from scripts.pettripfinder.brightdata import policy_locator as PL
import scripts.pettripfinder.milwaukee_policy_proposals_001 as PROP


def _code_of(function):
    """A function's CODE, with its docstring and comments removed.

    The prose in these functions describes what was removed and why, so a
    substring scan over the source would find the very words it is asserting
    are gone.
    """
    import inspect
    source = inspect.getsource(function)
    body = source.split('"""')
    code = body[0] + ("".join(body[2:]) if len(body) > 2 else "")
    return " ".join(line for line in code.splitlines()
                    if not line.strip().startswith("#"))


def store():
    return json.loads(R.STORE.read_text(encoding="utf-8-sig"))


def rows_by_identity():
    return {row["identity_key"]: row for row in store()["items"]}


# --------------------------------------------------------------------------- #
# 1 / 2 -- history is a record, not a working copy.
# --------------------------------------------------------------------------- #

#: The commit 030 made. Its freezes are claims about that commit, not about
#: everything anyone has done to these files since.
COMMIT_030 = "c10bc0d"


def _touched_by(commit):
    return subprocess.run(
        ["git", "show", "--pretty=format:", "--name-only", commit],
        cwd=str(REPO), capture_output=True, text=True).stdout.split()


def test_the_router_journal_still_says_what_its_reader_said():
    """The store derived new facts; the journal was not edited to match.

    Proved from the rows the projection moved: each carries the run's own
    reading as ``previous_facts``, and that is exactly what the journal still
    holds. If anyone had "fixed" the journal, these would now agree.
    """
    journal = {entry["identity_key"]: entry for entry in PROP.read_journal()}
    moved = [row for row in store()["items"]
             if (row.get("rederivation") or {}).get("superseded_by")
             == S.CURRENT_STATE_WORK_ORDER
             and row["identity_key"] in journal]
    assert moved
    differing = 0
    for row in moved:
        entry = journal[row["identity_key"]]
        historical = S.historical_reading(entry)
        assert row["rederivation"]["previous_facts"] == historical["extraction"]
        assert (row["rederivation"]["previous_withheld_fields"]
                == historical["withheld"])
        if historical["extraction"] != row["proposed_facts"]:
            differing += 1
    # The whole point: the journal and the store disagree, on purpose, and the
    # store carries both readings rather than pretending they agree.
    assert differing > 0


def test_historical_run_reports_are_untouched():
    for name in ("ptf_milwaukee_observation_rederivation_018.json",
                 "ptf_marriott_supersession_022.json",
                 "ptf_generic_reader_corpus_024.json",
                 "ptf_milwaukee_final_pass_026.json",
                 "ptf_identity_binding_027.json",
                 "ptf_premium_resolution_028.json",
                 "ptf_generic_reader_hardening_029.json"):
        path = ("atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                + name)
        if not (REPO / path).is_file():
            continue
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", name


# --------------------------------------------------------------------------- #
# 3 / 5 -- selection is frozen; reading is not.
# --------------------------------------------------------------------------- #

def test_selection_is_unchanged_and_owns_no_reading():
    chosen, superseded, conflicts = R.selection()
    rows = rows_by_identity()
    # Derived from the store rather than pinned: 032 added a recovered
    # observation, and the selection must track it exactly -- which a hard
    # number cannot express and this equality can.
    assert len(chosen) == len(rows)
    assert not conflicts
    assert len({entry["identity_key"] for entry in chosen}) == len(rows)
    assert sorted(entry["identity_key"] for entry in chosen) == sorted(rows)


def test_every_selected_observation_has_a_persisted_block():
    chosen, _superseded, _conflicts = R.selection()
    assert all(entry.get("_block") for entry in chosen)
    audit = R.replay_audit()
    assert audit["rows_blocked"] == 0
    assert audit["rows_compared"] == len(rows_by_identity())


def test_the_projection_runs_after_selection_and_changes_no_winner():
    """A projection entry exists only for an identity selection already chose."""
    chosen, _superseded, _conflicts = R.selection()
    selected = {entry["identity_key"] for entry in chosen}
    projection = S.current_state_projection(chosen)
    assert set(projection) <= selected


# --------------------------------------------------------------------------- #
# 4 / 6 -- one reading path.
# --------------------------------------------------------------------------- #

def test_the_projection_covers_every_production_family():
    """Not one family privileged, and router-001 no longer the exception."""
    chosen, _superseded, _conflicts = R.selection()
    by_run = {}
    for entry in chosen:
        by_run.setdefault(entry.get("source_run"), []).append(entry)
    assert len(by_run) >= 7
    projection = S.current_state_projection(chosen)
    # Every family is READ. Only the families whose stored entry was built from
    # a journal can differ, which is why the changed set is router-heavy -- but
    # the read itself is unconditional.
    read = 0
    for entries in by_run.values():
        for entry in entries:
            current = S._read_block(entry["_block"], entry.get("brand", ""))
            assert isinstance(current["extraction"], dict)
            read += 1
    assert read == len(chosen)
    assert set(projection) <= {entry["identity_key"] for entry in chosen}


def test_router_rows_no_longer_need_a_named_overlay():
    """The asymmetry this work order exists to remove.

    ``current_state_projection`` consults no queue, no allow-list and no work
    order's report. A router-001 row is re-read because it was selected, and
    for no other reason.
    """
    for term in ("queued_identities", "milwaukee-router-001", "QUEUE"):
        assert term not in _code_of(S.current_state_projection), term
    changed = S.current_state_projection(R.selection()[0])
    router = {entry["identity_key"] for entry in R.selection()[0]
              if entry.get("source_run") == "milwaukee-router-001"}
    assert set(changed) & router


def test_a_row_whose_reading_did_not_change_gets_no_lineage():
    """Saying "a work order changed this" when nothing changed is a false claim."""
    chosen, _superseded, _conflicts = R.selection()
    projection = S.current_state_projection(chosen)
    for entry in chosen:
        current = S._read_block(entry["_block"], entry.get("brand", ""))
        historical = S.historical_reading(entry)
        if S.same_reading(historical, current):
            assert entry["identity_key"] not in projection


# --------------------------------------------------------------------------- #
# 7 -- the block is the one the observation was about.
# --------------------------------------------------------------------------- #

def test_no_re_location_and_no_re_selection_of_a_source():
    """The projection reads a file. It has no path to a page or a locator."""
    for term in ("locate", "source_selection", "SS.select", "requests",
                 "capture_property", "http"):
        assert term not in _code_of(S.current_state_projection), term


def test_a_superseded_identity_is_read_from_its_superseding_capture():
    """The Trade's whole point is that a later capture replaced an
    understated FAQ reading. Re-reading the replaced one answers the question
    the supersession already settled."""
    chosen, superseded, _conflicts = R.selection()
    trade = next(entry for entry in chosen
                 if entry["identity_key"] == "the trade autograph collection")
    block = R.selected_block(trade, superseded)
    assert block["from_supersession"] is True
    assert block["sha256"] != trade["_evidence_block_sha256"]
    assert block["sha256"] == (
        superseded["the trade autograph collection"]["current"]
        ["policy_block_sha256"])


def test_the_evidence_hash_on_every_moved_row_matches_the_file():
    for row in store()["items"]:
        lineage = row.get("rederivation") or {}
        if lineage.get("superseded_by") != S.CURRENT_STATE_WORK_ORDER:
            continue
        path = REPO / "atlas-dashboard" / lineage["evidence_block_path"]
        assert path.is_file(), lineage["evidence_block_path"]
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        assert S.sha256_text(text) == lineage["evidence_block_sha256"]


# --------------------------------------------------------------------------- #
# 8 -- no provider can be reached.
# --------------------------------------------------------------------------- #

def test_the_whole_projection_needs_no_provider_call():
    from scripts.pettripfinder.acquisition import fresh_proof_019a as PROOF
    R.selection()               # warms any git/config read before the guard
    with PROOF.no_provider_calls() as attempts:
        audit = R.replay_audit()
        review = R.safety_review()
    assert attempts == []
    assert audit["rows_compared"] == len(rows_by_identity())
    assert review["changed_rows"] == audit["rows_stale"]


# --------------------------------------------------------------------------- #
# 9 / 10 -- the shape of the store.
# --------------------------------------------------------------------------- #

def test_one_identity_is_one_row():
    keys = [row["identity_key"] for row in store()["items"]]
    assert len(keys) == len(set(keys))


def test_the_row_count_moves_only_when_an_observation_is_added():
    """030 added none. 032 added one and 033 two, all from evidence on disk."""
    from scripts.pettripfinder.acquisition import locator_recovery_032 as R32
    from scripts.pettripfinder.acquisition import label_value_hardening_033 as R33
    assert len(store()["items"]) == (114 + len(R32.journal_rows())
                                     + len(R33.journal_rows()))


def test_the_integration_added_and_removed_nothing():
    result = S.integrate(write=False)
    assert result["rows_before"] == result["rows_after"]
    assert result["added"] == []
    assert result["removed"] == []
    assert result["duplicates"] == []
    assert result["conflicts"] == []


# --------------------------------------------------------------------------- #
# 11 -- 029's stale rows.
# --------------------------------------------------------------------------- #

def test_the_rows_029_left_stale_now_carry_the_current_reading():
    """Derived, not named: any row whose store facts disagree with a re-read
    of its own selected block is stale, and after this work order there are
    none of those except where a supersession deliberately outranks the read.
    """
    audit = R.replay_audit()
    chosen, superseded, _conflicts = R.selection()
    unexplained = [row for row in audit["stale"] if not row["superseded"]]
    assert unexplained == [], [row["identity_key"] for row in unexplained]


def test_the_specific_identities_029_reported_are_current():
    rows = rows_by_identity()
    for identity in ("avid hotels milwaukee west waukesha",
                     "comfort suites milwaukee airport",
                     "extended stay america milwaukee waukesha",
                     "extended stay america milwaukee wauwatosa"):
        row = rows[identity]
        assert (row.get("rederivation") or {}).get("superseded_by") \
            == S.CURRENT_STATE_WORK_ORDER
    assert rows["avid hotels milwaukee west waukesha"][
        "proposed_facts"]["pet_count_limit"] == 2
    assert rows["extended stay america milwaukee waukesha"][
        "proposed_facts"]["pet_count_limit"] == 2


# --------------------------------------------------------------------------- #
# 12 -- earlier lineage survives.
# --------------------------------------------------------------------------- #

def test_the_022_marriott_supersessions_still_win():
    """One of them rests on a determination and reads LESS from its block.

    A projection that overrode it would discard an adjudication to look
    consistent, so 022 is applied last and these three rows keep its marker.
    """
    rows = rows_by_identity()
    superseded = S.marriott_supersessions()
    assert len(superseded) == 3
    for identity in superseded:
        assert (rows[identity].get("rederivation") or {}).get("superseded_by") \
            == "PTF-MARRIOTT-OBSERVATION-CLOSURE-022"
    poplar = rows["residence inn by marriott milwaukee brookfield at poplar creek"]
    assert poplar["proposed_facts"]["weight_limit"] == {"value": 50.0,
                                                        "unit": "lb"}
    assert poplar["proposed_facts"]["pet_count_limit"] == 2


def test_018s_attribution_is_kept_where_the_reading_agrees():
    """The newer reading wins; where it agrees the original credit stands."""
    rows = rows_by_identity()
    overlay = S.overlay_018()
    assert overlay
    kept = [identity for identity in overlay
            if (rows[identity].get("rederivation") or {}).get("superseded_by")
            == "PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018"]
    assert kept
    chosen, _superseded, _conflicts = R.selection()
    by_key = {entry["identity_key"]: entry for entry in chosen}
    for identity in kept:
        current = S._read_block(by_key[identity]["_block"],
                                by_key[identity].get("brand", ""))
        assert current["extraction"] == overlay[identity]["extraction"]


def test_every_lineage_marker_is_from_the_known_vocabulary():
    known = {S.CURRENT_STATE_WORK_ORDER,
             "PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018",
             "PTF-MARRIOTT-OBSERVATION-CLOSURE-022"}
    for row in store()["items"]:
        lineage = row.get("rederivation") or {}
        if lineage:
            assert lineage["superseded_by"] in known, lineage["superseded_by"]


def test_a_derived_row_says_it_is_derived():
    for row in store()["items"]:
        lineage = row.get("rederivation") or {}
        if lineage.get("superseded_by") != S.CURRENT_STATE_WORK_ORDER:
            continue
        assert "current-state projection" in lineage["derivation"]
        assert lineage["reader_commit"]
        assert "previous_facts" in lineage


# --------------------------------------------------------------------------- #
# Safety: nothing got less safe.
# --------------------------------------------------------------------------- #

def test_no_applied_row_lifted_a_withholding_or_lost_a_field():
    """The two shapes a reader regression takes, checked on the applied set.

    The one row that loses fields under a re-read is superseded, so 022's
    determination outranks the read and the row never moves.
    """
    review = R.safety_review()
    for row in review["needing_review"]:
        assert row["identity_key"] in S.marriott_supersessions(), row


def test_no_row_was_promoted_merely_for_having_more_fields():
    """Every review-state move in this work order was toward caution."""
    rows = rows_by_identity()
    for identity in ("comfort suites milwaukee airport",
                     "courtyard by marriott milwaukee downtown",
                     "courtyard by marriott milwaukee brookfield at poplar creek"):
        assert rows[identity]["review_status"] == "HELD_SCHEMA_CANNOT_REPRESENT"
        assert rows[identity]["withheld_fields"]["pet_fee"] \
            == "SCHEMA_CANNOT_REPRESENT"


def test_a_marriott_charge_no_field_carries_withholds_the_fee():
    """The gap the projection surfaced, pinned.

    "Daily cleaning fee of $5/ day in addition to the one time non-refundable
    pet fee ... Per Stay: $50.00" produced BOTH charges and published only the
    fifty, understating a five-night stay by half.
    """
    from scripts.pettripfinder.brightdata import marriott_surface as MS
    from scripts.pettripfinder.contracts import enums
    block = ("Pet Policy Pets Welcome Daily cleaning fee of $5/ day in "
             "addition to the one time non-refundable pet fee "
             "Non-Refundable Pet Fee Per Stay: $50.00 "
             "Maximum Number of Pets in Room: 2")
    result = MS.to_extraction(MS.parse_policy_block(block, locator_id="t"),
                              location="t")
    assert "pet_fee" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert result.extraction["pet_count_limit"] == 2


def test_a_single_clean_marriott_charge_still_publishes():
    """The guard must not fire on a block with one charge and nothing else."""
    from scripts.pettripfinder.brightdata import marriott_surface as MS
    block = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: "
             "$150.00 Maximum Pet Weight: 50.0lbs "
             "Maximum Number of Pets in Room: 1")
    result = MS.to_extraction(MS.parse_policy_block(block, locator_id="t"),
                              location="t")
    assert result.extraction["pet_fee"] == 15000
    assert result.extraction["fee_basis"] == "per_stay"
    assert not result.withheld


# --------------------------------------------------------------------------- #
# 13 / 14 -- authority and publication.
# --------------------------------------------------------------------------- #

def test_no_milwaukee_policy_authority_exists():
    root = REPO / "atlas-dashboard" / "launch_packages" / "pettripfinder"
    assert list(root.rglob("*hotel_policy_facts*milwaukee*")) == []
    assert store()["authority_written"] is False
    assert store()["founder_approvals_created"] == 0


def test_nothing_is_published():
    assert all(not row.get("published") for row in store()["items"])


def test_the_market_counters_did_not_move():
    counters = R.counters()
    assert counters["census_total"] == 147
    assert counters["active_eligible"] == 133
    from scripts.pettripfinder.acquisition import locator_recovery_032 as R32
    from scripts.pettripfinder.acquisition import label_value_hardening_033 as R33
    recovered = len(R32.journal_rows()) + len(R33.journal_rows())
    assert counters["observed"] == 114 + recovered
    assert counters["active_unresolved"] == 19 - recovered
    assert counters["published"] == 0
    assert counters["sum_of_final_states"] == 147


def test_routing_and_capture_machinery_are_unchanged():
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census",
                 "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json"):
        assert not any(name == path or name.startswith(path.rstrip("/") + "/")
                       for name in _touched_by(COMMIT_030)),             "%s was modified by 030" % path

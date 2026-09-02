"""PTF-MILWAUKEE-OBSERVATION-STORE-INTEGRATION-025.

The Milwaukee current-state store was a projection of one journal. Five work
orders in a row said so and left it alone. This one reconciles it.

WHAT THESE TESTS GUARD
----------------------
That the store is a SELECTION and never a merge. One identity, one row, taken
from one observation -- a row assembled from two captures would describe no
page that ever existed.

That eligibility is decided by what a run WAS. A control capture that reads
cleanly is still a control, and letting one into current state would put a
measurement artefact in front of a founder.

And that widening the store did not quietly promote anything: published and
founder-approved stay zero, and a fee the schema cannot carry is held rather
than called ready because its capture was publication grade.
"""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP     # noqa: E402
from scripts.pettripfinder.acquisition import generic_reader_024 as G        # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS         # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY           # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S     # noqa: E402
from pettripfinder.acquisition import locator_freeze as LOCATOR_FREEZE
from pettripfinder.acquisition import reader_freeze as READER_FREEZE
from . import authority_freeze as AUTHORITY_FREEZE


def store():
    return json.loads(S.STORE.read_text(encoding="utf-8-sig"))


def report():
    return json.loads(S.INTEGRATION_REPORT.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# 1-3. Sources, determinism, exclusions.
# --------------------------------------------------------------------------- #

def test_multiple_production_runs_project_deterministically():
    first = S.integrate(write=False)
    second = S.integrate(write=False)
    assert first["rows_after"] == second["rows_after"]
    assert first["added"] == second["added"]
    assert first["rows_by_source_run"] == second["rows_by_source_run"]


def test_one_identity_has_exactly_one_current_row():
    rows = store()["items"]
    counts = Counter(i["identity_key"] for i in rows)
    assert not [k for k, n in counts.items() if n > 1]
    assert report()["duplicates"] == []


def test_controls_and_benchmarks_are_excluded():
    """A control capture must never outrank a production one."""
    eligible = {s[0] for s in S.SOURCES}
    for run, (kind, _why) in S.RUN_KINDS.items():
        if kind in (S.CONTROL, S.BENCHMARK, S.DIAGNOSTIC, S.REPLAY,
                    S.DECISION_TEST):
            assert run not in eligible, run
    assert store()["source_runs"] == sorted(
        set(store()["source_runs"]) & eligible)
    for excluded in ("hilton-decision-023-control", "marriott-decision-020-control",
                     "firecrawl-benchmark-002", "spider-benchmark-001",
                     "locator-fresh-proof-019a"):
        assert excluded not in store()["source_runs"]


#: Runs under ``data/acquisition/`` that belong to ANOTHER market.
#:
#: ``store_integration_025`` is Milwaukee's module -- ``MARKET`` is
#: "milwaukee-wi" and ``RUN_KINDS`` feeds Milwaukee's projection -- but
#: ``data/acquisition/`` is shared by every market, so each new market drops
#: directories here that this table has no business classifying. They are listed
#: EXPLICITLY rather than filtered by prefix: the gate below is that nobody may
#: leave a run undecided, and a silent pattern match would let a genuinely
#: unclassified Milwaukee run through the moment its name happened to match.
OTHER_MARKET_RUNS = {
    "st_louis_direct_http_001",   # PTF-ST-LOUIS-MARKET-001, zero-cost lane
    "st_louis_paid_002",          # PTF-ST-LOUIS-PAID-ACQUISITION-002
    "louisville_rebuild_002",     # PTF-LOUISVILLE-MARKET-REBUILD-002, paid pass
    "louisville_expansion_003",   # PTF-LOUISVILLE-COVERAGE-EXPANSION-003
    # PTF-GRAND-RAPIDS-HOLLAND-PAID-ACQUISITION-AUTHORIZATION-009: 65
    # properties under a $9.66 cap, settled $7.25. Belongs to
    # grand-rapids-holland-mi and must never reach Milwaukee's projection.
    "grand_rapids_holland_mi_factory_001",
    # PTF-GRAND-RAPIDS-POLICY-ACQUISITION-028: the 20 URLs Google Places
    # batches 026 and 027 recovered, fetched under a $4.00 operating cap and
    # settled at $1.70. Also grand-rapids-holland-mi, and excused here for the
    # same reason: it is another market's run, and the companion test below
    # proves the excuse does not let it reach Milwaukee's projection.
    "gr_028",
    # PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-030: one capture RE-LOCATED out
    # of gr_028's own declined bytes once 029 settled its identity. No provider
    # was called to produce it. Also grand-rapids-holland-mi.
    "gr_030_relocated",
    # PTF-PITTSBURGH-PAID-ACQUISITION-AUTHORIZATION-003: 92 attempted under a
    # $17.50 cap, settled $17.08, 43 VALID. Materialised into this checkout by
    # PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 3 so the 67 owned pages could be
    # replayed offline through the current reader at $0. Belongs to
    # pittsburgh-pa and must never reach Milwaukee's projection.
    "pittsburgh_pa_factory_recensus_001",
    # PTF-PITTSBURGH-IDENTITY-AND-RECAPTURE-006: one attended-Chrome re-capture
    # of SpringHill Suites Pittsburgh Airport, taken for $0.00 to settle a
    # contradiction between a published record and the property's own page.
    # Also pittsburgh-pa, and it holds no rendered bytes at all -- only the
    # atomic hash+quote record the attended-capture contract defines.
    "pittsburgh_pa_free_recapture_006",
    # PTF-PITTSBURGH-IDENTITY-CLOSE-007: attended-Chrome reads of three
    # Pittsburgh properties plus IHG's Cranberry Township directory, all for
    # $0.00. Also pittsburgh-pa, and it holds no rendered bytes -- only the
    # atomic hash+quote records the attended-capture contract defines.
    "pittsburgh_pa_free_capture_007",
    # PTF-DAYTON-OH-HARDENED-REVALIDATION-001 phase 9: 48 first-party HTTPS GETs
    # over the unresolved cohort through the canonical direct_http lane, $0.00
    # and no provider. Every target refused a plain client, so the run holds
    # denial pages rather than policy -- which is the evidence that Dayton needs
    # the attended lane. Belongs to dayton-oh and must never reach Milwaukee's
    # projection.
    "dayton_oh_free_static_001",
    # PTF-DAYTON-OH-HARDENED-REVALIDATION-001 phase 11: the same lane re-run
    # over all 55 LIVE Dayton records to test published authority against the
    # properties' own pages. $0.00, no provider, and it wrote nothing to
    # authority. Also dayton-oh.
    "dayton_oh_live_audit_001",
}


def test_every_run_on_disk_is_classified():
    """An unclassified run is a run nobody decided about."""
    on_disk = {p.name for p in (REPO / "data" / "acquisition").iterdir()
               if p.is_dir()}
    # wyndham-008 is journalled inside the resume-007 tree rather than as its
    # own top-level directory, so it is named in RUN_KINDS without appearing here.
    unclassified = on_disk - set(S.RUN_KINDS) - OTHER_MARKET_RUNS
    assert not unclassified, unclassified


def test_no_foreign_run_can_reach_the_milwaukee_projection():
    """The escape hatch above must stay an escape hatch.

    Naming a run as another market's is only safe while that also keeps it out
    of Milwaukee's sources: if one were ever both excused here AND readable as a
    Milwaukee source, the exemption would have hidden a real classification gap.
    """
    assert OTHER_MARKET_RUNS.isdisjoint(set(S.RUN_KINDS))
    assert OTHER_MARKET_RUNS.isdisjoint({s.run for s in S.SOURCES}
                                        if hasattr(next(iter(S.SOURCES), None),
                                                   "run") else set(S.SOURCES))


def test_a_decision_run_is_not_an_eligible_source():
    assert S.RUN_KINDS["hilton-decision-023"][0] == S.DECISION_TEST
    assert S.RUN_KINDS["marriott-decision-020"][0] == S.DECISION_TEST
    assert S.RUN_KINDS["hilton-decision-023-control"][0] == S.CONTROL


# --------------------------------------------------------------------------- #
# 4-5. Marriott supersession and Hilton ingestion.
# --------------------------------------------------------------------------- #

def test_the_marriott_022_supersessions_beat_the_020_readings():
    rows = {i["canonical_name"]: i for i in store()["items"]}
    for name in ("The Trade, Autograph Collection",
                 "Residence Inn by Marriott Milwaukee Brookfield at Poplar Creek",
                 "Sheraton Milwaukee Brookfield Hotel"):
        row = rows[name]
        assert row["rederivation"], name
        assert "pet_fee" not in row["proposed_facts"], name
        assert row["withheld_fields"]["pet_fee"] == "SCHEMA_CANNOT_REPRESENT"


def test_the_trade_no_longer_asserts_the_understated_fee():
    row = next(i for i in store()["items"]
               if i["canonical_name"] == "The Trade, Autograph Collection")
    assert 12500 not in row["proposed_facts"].values()
    assert row["rederivation"]["previous_facts"] is not None


def test_the_hilton_production_rows_entered():
    rows = [i for i in store()["items"]
            if i.get("source_run") == "hilton-milwaukee-023"]
    assert len(rows) == 10
    assert all(i["brand"] == "HILTON" for i in rows)


def test_the_hilton_non_publication_grade_row_did_not_enter():
    """Spark is ACQUIRED_NONPUBLICATION_GRADE; the store takes publication
    grade only, so it is absent rather than admitted with a caveat."""
    names = {i["canonical_name"] for i in store()["items"]}
    assert "Spark by Hilton Milwaukee Airport" not in names


def test_the_marriott_production_rows_entered():
    rows = [i for i in store()["items"]
            if i.get("source_run") == "marriott-milwaukee-020"]
    assert len(rows) == 17


# --------------------------------------------------------------------------- #
# 6-7. The 024 re-derivations.
# --------------------------------------------------------------------------- #

def test_every_queued_row_rests_on_its_own_persisted_evidence():
    """Narrowed by PTF-MILWAUKEE-STORE-READER-SYNC-030.

    This used to require a ``rederivation`` block on every queued row, because
    the overlay was scoped to that queue and stamped all fifteen unconditionally
    -- including rows whose reading had not changed at all. Lineage now records
    a CHANGE, so six Hilton rows whose stored reading already equalled the
    current one carry none, and stamping them would claim a work order changed
    a reading it did not touch.

    The invariant that replaces it is stronger and is what the old one was
    reaching for: every queued row's facts are what the current reader makes of
    that row's own persisted block, and any lineage present names a real block.
    """
    queued = {i["canonical_name"] for i in
              json.loads(G.QUEUE_REPORT.read_text(encoding="utf-8-sig"))["items"]}
    rows = {i["canonical_name"]: i for i in store()["items"]}
    entries = []
    for run_id, journal, capture_root in S.SOURCES:
        entries.extend(S.load_source(run_id, journal, capture_root))
    superseded = S.marriott_supersessions()
    chosen, _conflicts = S.select_current(entries, superseded)
    by_name = {e["canonical_name"]: e for e in chosen}
    seen = 0
    for name in queued:
        row = rows.get(name)
        if row is None:          # Spark, which is not publication grade
            continue
        seen += 1
        lineage = row.get("rederivation") or {}
        if lineage:
            assert lineage["evidence_block_sha256"], name
            assert lineage["evidence_block_path"].endswith(
                "policy-block.txt"), name
        entry = by_name.get(name)
        if entry is None or row["identity_key"] in superseded:
            continue
        current = S._read_block(entry["_block"], entry.get("brand", ""))
        assert current["extraction"] == row["proposed_facts"], name
    assert seen >= 15


def test_banded_fees_are_withheld_in_the_store():
    """No row ever carries one amount for a price the source states in bands.

    NARROWED by work order 034, which taught the reader to build the ladder
    schema 1.2 had always been able to hold: the count of rows HELD for a
    banded fee fell from twenty-nine to eleven, and pinning that count made
    "sixteen or more are stuck" a requirement rather than an observation. What
    the store must never contain is asserted directly instead -- a single
    ``pet_fee`` beside a ladder, or a held fee that leaked its amount anyway.
    """
    rows = store()["items"]
    held = [i for i in rows
            if i["withheld_fields"].get("pet_fee") == "SCHEMA_CANNOT_REPRESENT"]
    for row in held:
        assert "pet_fee" not in row["proposed_facts"], row["canonical_name"]
    laddered = [i for i in rows
                if (i["proposed_facts"] or {}).get("fee_tiers")
                or (i["proposed_facts"] or {}).get("fee_pet_schedule")]
    for row in laddered:
        assert "pet_fee" not in row["proposed_facts"], row["canonical_name"]
    assert held or laddered


def test_non_fee_facts_survive_a_withheld_fee():
    rows = {i["canonical_name"]: i for i in store()["items"]}
    row = rows.get("Home2 Suites by Hilton Menomonee Falls Milwaukee")
    if row is None:
        pytest.skip("row not present in this worktree")
    assert row["proposed_facts"].get("weight_limit", {}).get("value") == 100.0
    # The fee is a ladder now (034). What this test is about is that the rest
    # of the policy survives whatever happens to the fee, and that no single
    # amount is published for a banded one.
    assert "pet_fee" not in row["proposed_facts"]
    assert (row["withheld_fields"].get("pet_fee") == "SCHEMA_CANNOT_REPRESENT"
            or row["proposed_facts"].get("fee_tiers"))


# --------------------------------------------------------------------------- #
# 8. Conflicts are held, not resolved.
# --------------------------------------------------------------------------- #

def test_a_conflict_would_be_held_rather_than_resolved():
    entries = [
        {"identity_key": "x", "canonical_name": "X", "source_run": "milwaukee-router-001",
         "_evidence_block_sha256": "aaa"},
        {"identity_key": "x", "canonical_name": "X", "source_run": "hilton-milwaukee-023",
         "_evidence_block_sha256": "bbb"},
    ]
    chosen, conflicts = S.select_current(entries, superseded={})
    assert len(chosen) == 1
    assert len(conflicts) == 1
    assert chosen[0]["source_run"] == "hilton-milwaukee-023"   # newest wins
    assert conflicts[0]["_conflict"]["runs"] == ["hilton-milwaukee-023",
                                                 "milwaukee-router-001"]


def test_identical_blocks_in_two_runs_are_not_a_conflict():
    entries = [
        {"identity_key": "x", "canonical_name": "X",
         "source_run": "milwaukee-resume-007", "_evidence_block_sha256": "same"},
        {"identity_key": "x", "canonical_name": "X",
         "source_run": "milwaukee-wyndham-008", "_evidence_block_sha256": "same"},
    ]
    chosen, conflicts = S.select_current(entries, superseded={})
    assert len(chosen) == 1 and conflicts == []


def test_the_measured_run_had_no_conflicts_and_no_removals():
    doc = report()
    assert doc["conflicts"] == []
    assert doc["removed"] == []
    assert doc["duplicates"] == []


def test_no_row_merges_fields_from_two_observations():
    """Every row names exactly one originating run."""
    for row in store()["items"]:
        assert isinstance(row.get("source_run"), str) and row["source_run"]


# --------------------------------------------------------------------------- #
# 9-12. History, publication and authority.
# --------------------------------------------------------------------------- #

def test_historical_reports_and_journals_are_unchanged():
    for path in ("atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                 "ptf_marriott_milwaukee_run_020.json",
                 "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                 "ptf_hilton_milwaukee_run_023.json",
                 "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                 "ptf_marriott_supersession_022.json",
                 "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                 "ptf_generic_reader_rederivation_queue_024.json"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO.parent), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 025" % path


def test_prior_facts_stay_inspectable_through_supersession_metadata():
    superseded = [i for i in store()["items"] if i.get("rederivation")]
    assert superseded
    for row in superseded:
        assert "previous_facts" in row["rederivation"], row["canonical_name"]
        assert "previous_withheld_fields" in row["rederivation"]


def test_published_and_founder_approved_remain_zero():
    rows = store()["items"]
    assert sum(1 for i in rows if i.get("published")) == 0
    assert sum(1 for i in rows if i.get("founder_approved")) == 0
    assert store()["founder_approvals_created"] == 0


def test_no_milwaukee_policy_authority_was_created():
    # NARROWED. This claimed "store integration 025 created no Milwaukee authority",
    # which was true and still is -- but read against the live filesystem
    # it became "Milwaukee may never have one", and the founder approved
    # 96 records in PTF-MILWAUKEE-FOUNDER-DECISION-036. The historical
    # claim is checked against the commit; the standing claim -- that
    # authority is recorded and never live inventory -- is checked too.
    AUTHORITY_FREEZE.assert_commit_created_no_authority("02a9d9c")
    AUTHORITY_FREEZE.assert_authority_is_recorded_not_live()
    assert store()["authority_written"] is False


def test_a_schema_held_row_is_not_called_ready():
    """Publication grade at acquisition level does not promote a row."""
    for row in store()["items"]:
        if row["withheld_fields"].get("pet_fee") == "SCHEMA_CANNOT_REPRESENT":
            assert row["review_status"] != "FOUNDER_REVIEW_READY", \
                row["canonical_name"]


def test_review_states_are_reported_with_counts():
    counts = store()["review_status_counts"]
    assert counts["HELD_SCHEMA_CANNOT_REPRESENT"] > 0
    assert sum(counts.values()) == len(store()["items"])


# --------------------------------------------------------------------------- #
# The builder seam stays safe when unused.
# --------------------------------------------------------------------------- #

def test_the_builder_without_extras_still_projects_the_router_run_alone():
    doc = PROP.build(write=False)
    assert doc["source_runs"] == ["milwaukee-router-001"]
    assert len(doc["items"]) == 58


# --------------------------------------------------------------------------- #
# Freezes.
# --------------------------------------------------------------------------- #

def test_acquisition_routing_and_providers_are_unchanged():
    for brand, provider in (("HILTON", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("CHOICE", PROVIDERS.FIRECRAWL),
                            ("WYNDHAM", PROVIDERS.FIRECRAWL),
                            ("IHG", PROVIDERS.FIRECRAWL)):
        assert REGISTRY.resolve(brand=brand,
                                url="https://example.com/x").provider == provider
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census",
                 "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO.parent), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 025" % path
    LOCATOR_FREEZE.assert_locator_surface_unchanged()
    READER_FREEZE.assert_reader_protections_unchanged()

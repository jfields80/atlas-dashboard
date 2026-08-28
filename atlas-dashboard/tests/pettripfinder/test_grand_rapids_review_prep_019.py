# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FOUNDER-REVIEW-PROMOTION-PREP-019.

The counts are pinned because a test that only asserted "validation passed"
would still pass if the candidate list quietly emptied. The arithmetic is
asserted too: every reusable row and every unresolved routed row has to land in
exactly one bucket, and the buckets have to add back up to what went in.

Three things get their own tests because they are the ways this pass could do
real damage rather than merely be wrong:

  * writing an approval. No founder review has run for this market, so every
    row must leave here MACHINE_REVIEWED_PENDING_OPERATOR with empty decision
    fields. An attestation needs the human, not the field.
  * promoting a held identity. Comfort Suites Grandville has clean, publication-
    grade evidence and is still withheld, because whether that answer belongs to
    one hotel or two has not been decided.
  * spending. Nothing here may construct a provider.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_review_prep_019 as P  # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
PACKET = LP / "grand_rapids_holland_mi_exception_review_packet_019.json"
REPAIR = LP / "grand_rapids_holland_mi_routing_repair_019.json"
HOLDS = LP / "grand_rapids_holland_mi_identity_holds_019.json"
AUTHORITY = LP / "grand_rapids_holland_mi_proposed_authority_candidates_019.json"


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def packet():
    return _load(PACKET)


@pytest.fixture(scope="module")
def repair():
    return _load(REPAIR)


@pytest.fixture(scope="module")
def holds():
    return _load(HOLDS)


@pytest.fixture(scope="module")
def authority():
    return _load(AUTHORITY)


# --------------------------------------------------------------------------- #
# Phase 1
# --------------------------------------------------------------------------- #

def test_all_54_reusable_rows_are_classified_exactly_once(packet):
    counts = packet["by_classification"]
    assert packet["reusable_rows"] == 54
    assert sum(counts.values()) == 54
    assert set(counts) == set(P.ALL_CLASSES)
    keys = [r["identity_key"] for r in packet["exceptions"] + packet["clean"]]
    assert len(keys) == 54
    assert len(set(keys)) == 54


def test_the_split_between_clean_and_exception(packet):
    counts = packet["by_classification"]
    assert counts["CLEAN_PET_FRIENDLY"] == 31
    assert counts["CLEAN_VERIFIED_NO_PETS"] == 14
    assert counts["POLICY_FACT_CORRECTION"] == 4
    assert counts["IDENTITY_CONFLICT"] == 1
    assert counts["HOLD_ALLOWANCE_NOT_STATED"] == 1
    assert counts["HOLD_SOURCE_SILENT_ON_PETS"] == 3
    assert packet["exceptions_requiring_a_reading"] == 9
    assert packet["clean_rows_coverable_by_a_class_signature"] == 45


def test_a_membrane_refusal_outranks_a_clean_policy_reading():
    """The ladder's first real rung. A record the membrane says is about
    another property cannot be corrected into authority, whatever its facts
    say, so it must not be reachable through a disposition."""
    store = {"x": {"membrane": {"verdict": "REJECT_WRONG_PROPERTY"},
                   "readiness": "POLICY_CONFIRMED", "publication_grade": True}}
    analysis = {"x": {"proposed_disposition": "APPROVE_PET_FRIENDLY"}}
    klass, why = P.classify_reusable("x", store, {}, analysis)
    assert klass == P.IDENTITY_CONFLICT
    assert "another property" in why


def test_a_row_with_no_disposition_is_never_filed_as_clean():
    store = {"x": {"membrane": {"verdict": "VALID"}}}
    with pytest.raises(ValueError):
        P.classify_reusable("x", store, {}, {"x": {}})


def test_source_silence_is_a_hold_and_not_a_no_pets_finding(packet):
    """Three pages rendered and never mentioned pets. That is a fact about the
    source; publishing it as 'no pets' would invent a policy the hotel never
    stated."""
    silent = [r for r in packet["exceptions"]
              if r["classification"] == P.HOLD_SOURCE_SILENT_ON_PETS]
    assert len(silent) == 3
    assert {r["identity_key"] for r in silent} == {
        "doubletree by hilton hotel grand rapids airport",
        "drury inn and suites grand rapids", "tulyp"}
    for row in silent:
        assert row["membrane_verdict"] == "NO_RECORD"
        assert row["publication_grade"] is False


def test_every_clean_row_carries_its_own_semantic_hash(packet):
    """A class signature is only a signature because of this. Without a
    per-row hash it would bind to a count, and a fact could move underneath
    it without lapsing the approval."""
    assert packet["binding_contract"] == "semantic-approval/1.0"
    for row in packet["clean"]:
        assert row["semantic_approval_hash"].startswith("sha256:")
        assert row["snapshot_hash"]


# --------------------------------------------------------------------------- #
# Phase 2
# --------------------------------------------------------------------------- #

def test_the_routing_verdicts(repair):
    assert repair["rows_adjudicated"] == 11
    assert repair["routing_repair_required_in"] == 8
    assert repair["same_page_already_failed_in"] == 3
    assert repair["by_verdict"] == {
        "ROUTE_IS_CORRECT_IDENTITY_UNCORROBORATED": 7,
        "ROUTE_IS_DEAD": 1,
        "ROUTE_NAMES_ANOTHER_BRAND": 1,
        "ROUTE_REDIRECTED_OFF_THE_PROPERTY": 2}


def test_seven_of_the_eight_are_not_routing_defects(repair):
    """The finding. Their URLs already reach the property's own page; the
    identity gate refused on corroboration, which no purchase changes."""
    uncorroborated = [a for a in repair["adjudications"]
                      if a["verdict"] == P.ROUTE_IS_CORRECT_IDENTITY_UNCORROBORATED]
    assert len(uncorroborated) == 7
    for row in uncorroborated:
        assert row["page_title"], "a route with no page cannot be called correct"
        assert row["saved_capture"], "the ruling is only free if the capture kept"


def test_no_repair_was_applied_and_the_reason_is_recorded(repair):
    """Zero is a real answer here. The one owned alternative URL is the stable
    form of the same page the current route already reaches, and the overlay
    contract refuses to displace a route a lane can fetch."""
    assert repair["repairs_applied"] == 0
    assert repair["repairs_available_offline"] == 0
    assert repair["owned_alternative_urls_found"] == 1
    assert repair["why_no_repair_was_applied"]
    alt = [a for a in repair["adjudications"]
           if a["owned_alternative_url"]["exists"]]
    assert len(alt) == 1
    assert alt[0]["identity_key"] == "fairfield inn and suites grand rapids wyoming"
    assert alt[0]["owned_alternative_url"]["would_change_the_route"] is False


def test_a_name_and_a_url_from_two_different_chains_refute_the_route(repair):
    """One row of 82. A census row named 'Best Western' carrying a
    wyndhamhotels.com URL is refuted by the two chains' own authority."""
    scan = repair["brand_contradiction_scan"]
    assert scan["routed_rows_scanned"] == 82
    assert scan["contradictions"] == 1
    assert scan["rows"][0]["identity_key"] == "best western"
    assert scan["rows"][0]["name_brand"] == "BEST_WESTERN"
    assert scan["rows"][0]["url_brand"] == "WYNDHAM"


def test_the_brand_check_only_ever_refutes():
    """It may never propose a route. A name with no chain marker, or a URL on
    a domain no chain owns, produces nothing at all."""
    assert P.brand_contradiction("The Ada Hotel", "https://www.adahotel.com/") == ("", "")
    assert P.brand_contradiction("Best Western", "https://bestwestern.com/x") == ("", "")
    assert P.brand_contradiction("Best Western",
                                 "https://www.wyndhamhotels.com/baymont/x") == (
        "BEST_WESTERN", "WYNDHAM")


def test_every_unresolved_row_names_one_exact_next_action(repair):
    """Exact, not generic: each says what is missing for THAT row."""
    for row in repair["adjudications"]:
        assert row["next_action"]
    fairfield = [a for a in repair["adjudications"]
                 if a["identity_key"] == "fairfield inn and suites grand rapids wyoming"][0]
    assert "SouthW." in fairfield["next_action"], (
        "the corrupt census address is the whole reason this row failed")
    bluejay = [a for a in repair["adjudications"]
               if a["identity_key"] == "the bluejay hotel"][0]
    assert "the blue jay hotel and events" in bluejay["next_action"]


def test_the_half_expanded_direction_is_detected_and_a_clean_one_is_not():
    assert P._HALF_EXPANDED.search("5970 Metro Way SouthW.")
    assert not P._HALF_EXPANDED.search("5970 Metro Way Southwest")
    assert not P._HALF_EXPANDED.search("255 28th Street SW")


# --------------------------------------------------------------------------- #
# Phase 3
# --------------------------------------------------------------------------- #

def test_both_named_holds_are_open_and_neither_is_merged(holds):
    assert holds["count"] == 2
    pairs = {tuple(h["identity_keys"]) for h in holds["holds"]}
    assert ("comfort inn", "comfort suites grandville grand rapids sw") in pairs
    assert ("sleep inn and suites", "spark by hilton grand rapids") in pairs
    for hold in holds["holds"]:
        assert hold["dedup_verdict"] == "DISTINCT_PROPERTIES"
        assert hold["resolved_by_this_pass"] is False
        assert hold["merged_by_this_pass"] is False
        assert hold["decided_on_shared_telephone"] is False
        assert hold["evidence_that_would_settle_it"]
        assert len(hold["halves"]) == 2


def test_a_third_pair_of_the_same_shape_is_surfaced_not_merged(holds):
    """The two named holds are a shared street plus an identical switchboard
    plus incompatible names. Exactly one other pair in this census is the same
    shape, and a founder asked about two should be told there are three."""
    questions = holds["surfaced_identity_questions"]
    assert questions["pairs_ruled_distinct"] == 10
    assert questions["of_those_sharing_an_identical_telephone"] == 3
    assert questions["named_by_the_work_order"] == 2
    unnamed = [q for q in questions["pairs"]
               if q["shares_an_identical_telephone"] and not q["is_a_named_hold"]]
    assert [q["identity_keys"] for q in unnamed] == [
        ["budgetel grand rapids", "budgetel inn and suites hotel"]]
    # Only the same-shape pairs are held back. A pair the gate ruled distinct on
    # DIFFERING telephones was decided on evidence, not on a shared building --
    # AmericInn and the Best Western Hospitality share a street and nothing
    # else -- and holding those out would cost coverage for no reason.
    for question in questions["pairs"]:
        if question["shares_an_identical_telephone"]:
            assert question["in_authority_candidates"] == [], (
                "a pair sharing a street AND a switchboard is still being "
                "argued about and may not be in the candidate list")


# --------------------------------------------------------------------------- #
# Phase 4
# --------------------------------------------------------------------------- #

def test_this_is_a_candidate_list_and_not_an_authority(authority):
    assert authority["is_an_authority"] is False
    assert "founder_review is NOT_RUN" in authority["why_not"]


def test_no_approval_is_written_anywhere(authority, packet):
    """The rule this repository learned the hard way: twenty-six approvals were
    once written under a founder's name for rows the founder had never seen."""
    for row in authority["candidates"]:
        assert row["review_status"] == P.PENDING
        assert row["founder_decision"] == ""
    for row in packet["exceptions"] + packet["clean"]:
        assert row["review_status"] == P.PENDING
        assert row["founder_decision"] == ""
        assert row["founder_reviewer_id"] == ""
        assert row["founder_reviewed_at"] == ""


def test_the_candidate_counts(authority):
    counts = authority["counts"]
    assert counts["census"] == 163
    assert counts["routed"] == 82
    assert counts["reusable_evidence_processed"] == 54
    assert counts["pet_friendly_candidates"] == 31
    assert counts["verified_no_pets_candidates"] == 13
    assert counts["hold_count"] == 4
    assert counts["policy_fact_corrections"] == 4
    assert counts["identity_review_count"] == 1
    assert counts["routing_unresolved"] == 11
    assert counts["routing_repairs_completed"] == 0
    assert counts["identity_holds"] == 2
    assert counts["clean_but_withheld_on_an_open_identity"] == 1
    assert counts["total_resolved"] == 44
    assert counts["total_unresolved"] == 20


def test_the_counts_reconcile(authority):
    """54 reusable rows plus 11 unresolved routed rows, split three ways with
    nothing invented and nothing dropped."""
    reconcile = authority["counts_reconcile"]
    assert reconcile["ok"] is True
    assert reconcile["total"] == reconcile["expected"] == 65


def test_clean_evidence_is_still_withheld_when_the_identity_is_open(authority):
    """Comfort Suites Grandville answered its page at publication grade. It is
    still not a candidate, because whether that answer belongs to one hotel or
    two is the open question."""
    assert authority["withheld_on_an_open_identity"] == [
        "comfort suites grandville grand rapids sw"]
    keys = {c["identity_key"] for c in authority["candidates"]}
    assert "comfort suites grandville grand rapids sw" not in keys


def test_every_validation_check_passes(authority):
    validation = authority["validation"]
    for name, check in validation.items():
        if name == "all_pass":
            continue
        assert check["ok"] is True, "%s: %r" % (name, check)
    assert validation["all_pass"] is True


def test_nothing_was_spent(authority, packet, repair, holds):
    for document in (authority, packet, repair, holds):
        assert document["provider_calls"] == 0
        assert document["usd_spent"] == 0.0
        assert document["plan_credits_spent"] == 0.0


def test_the_registered_shard_is_recorded_and_unchanged(authority):
    """Grand Rapids is already registered -- but as a DISCOVERY-STAGE market
    that publishes no policy claim, is hidden from navigation and the sitemap,
    and carries zero exclusions and zero affiliate destinations. Promotion here
    is that market's first policy content, not a registration, so PTF-047's
    deployment-record coupling does not fire. The baseline is recorded so the
    delta a promotion would make is a fact rather than a memory."""
    baseline = authority["registered_shard_baseline"]
    assert baseline["exists"] is True
    assert baseline["exclusions"] == 0
    assert baseline["destinations"] == 0
    assert baseline["routes"] == 110
    assert baseline["show_in_navigation"] is False
    assert baseline["show_in_sitemap"] is False
    assert baseline["unchanged_by_this_pass"] is True


def test_no_market_authority_is_written_by_this_pass():
    """Not this market's and not anybody else's. The shard files on disk must
    still match the commit, which is the only check that catches a write this
    module did not mean to make."""
    import subprocess
    shards = "launch_packages/pettripfinder/markets"
    result = subprocess.run(["git", "status", "--porcelain", "--", shards],
                            cwd=str(REPO_ROOT.parent), capture_output=True,
                            text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        "a market contract or authority shard changed: %r" % result.stdout)


def test_every_candidate_belongs_to_this_market(authority):
    assert authority["market_id"] == "grand-rapids-holland-mi"

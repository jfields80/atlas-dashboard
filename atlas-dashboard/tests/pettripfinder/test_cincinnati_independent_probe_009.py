"""PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-009 -- closing the independent lane.

14 rows, attended Chrome, no provider and no dollar. Combined with PROBE-008 the
genuine-independent lane closes at 12/19 publication-grade across 9 of 16
domains, and the final answer is SITE_BY_SITE_FREE_ONLY.

The important thing this order did was catch a defect in its own predecessor's
METHOD, not its arithmetic. Every prior Cincinnati sweep read ``innerText``.
The Warehouse Hotel's policy lives in the DOM and not in innerText, so this
order re-read every row it had just called silent using ``textContent`` -- and
four more policies appeared, two of them on rows PROBE-008 had recorded as
POLICY_NOT_FOUND and one on a template PROBE-008's commit message claimed to
have "settled".

These tests pin the three things that follow from that:

* the corrections are CARRIED, not just noticed. A wrong answer left in a
  committed artifact is worse than one never written;
* the lane is measured on the CORRECTED readings, because scoring it on
  findings this order disproved would understate it by two;
* the recommendation still refuses to call silence a paid-lane problem, and
  refuses to promote a 63% yield spread across sixteen unrelated websites into
  a family-wide rate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_independent_probe_009 as P
from scripts.pettripfinder import cincinnati_probe009_apply as A
from scripts.pettripfinder.contracts import enums, service_animal as SA

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def results():
    return _load(P.RESULTS)


@pytest.fixture(scope="module")
def rows(results):
    return results["rows"]


@pytest.fixture(scope="module")
def cohort():
    return _load(P.COHORT)


@pytest.fixture(scope="module")
def lane():
    return _load(P.MEASUREMENT)


@pytest.fixture(scope="module")
def pending():
    return _load(P.PENDING)


# ---------------------------------------------------------------- it cost nothing

def test_the_probe_called_no_provider_and_spent_nothing(results):
    assert results["provider_calls"] == 0
    assert results["paid_spend_usd"] == 0.0
    assert results["capture_method"] == "attended_chrome_render"
    for row in results["rows"]:
        assert row["provider_calls"] == 0 and row["cost_usd"] == 0.0
    assert _load(P.REPRICE)["spend_this_order_usd"] == 0.0


def test_every_admitted_row_was_processed_exactly_once(results, rows, cohort):
    assert results["cohort_size"] == results["processed"] == 14
    keys = [r["identity_key"] for r in rows]
    assert len(keys) == len(set(keys)) == 14
    assert set(keys) == {r["identity_key"] for r in cohort["rows"]}
    urls = [r["official_property_url"] for r in rows]
    assert len(urls) == len(set(urls))


def test_nothing_was_applied_and_no_approval_was_written(results):
    assert results["authority_mutated"] is False
    assert results["approvals_written"] == 0
    for path in (P.RESULTS, P.COHORT, P.MEASUREMENT, P.PENDING, P.REPRICE):
        blob = Path(path).read_text(encoding="utf-8")
        assert "APPROVED_AFTER_CURRENT_REVIEW" not in blob, path.name
        assert "record_hash" not in blob, path.name


def test_the_probe_itself_wrote_no_authority(results):
    """Same correction as PROBE-008's: the claim is about the ORDER.

    APPLICATION-010 has since applied these findings, so a totals assertion
    here would fail on this probe's own success.
    """
    assert results["authority_mutated"] is False
    assert results["approvals_written"] == 0


# ------------------------------------------------- the cohort, rebuilt not trusted

def test_there_were_fourteen_rows_not_seventeen(cohort):
    """PROBE-008 said 17. Its counter used a subset denominator.

    It subtracted only the seven rows it measured as Independent/ESA from the
    24 labelled ones, ignoring the three Choice-platform rows it also
    observed. PROBE-008 opened by correcting the same shape of slip in
    APPLICATION-007, which is why this order rebuilt rather than trusted.
    """
    assert "17 rows still unobserved. There are 14" in cohort["correction"]
    audit = cohort["audit"]
    assert audit["labelled_independent_or_esa"] == 24
    assert audit["suppressed_observed_by_probe_008"] == 10
    assert audit["admitted"] == 14
    assert audit["admitted"] + audit["suppressed_observed_by_probe_008"] == \
        audit["labelled_independent_or_esa"]


# ------------------------------------------------- the method defect and its fixes

def test_the_method_defect_is_recorded(results):
    """innerText was the wrong surface, and saying so is the finding."""
    defect = results["method_defect_found"]
    assert "innerText" in defect and "textContent" in defect
    assert "149,578" in defect
    assert "word boundaries" in defect


def test_the_drury_template_was_overturned_on_all_four(results, rows):
    """PROBE-008 called this template settled. It settled it backwards.

    Its own JSON-LD says petsAllowed:false while the page body carries a full
    pet policy in an embedded JSON payload. All four Cincinnati Drury
    properties are pet-friendly.
    """
    drury = [r for r in rows if r["official_domain"] == "druryhotels.com"]
    assert len(drury) == 3
    for row in drury:
        assert row["outcome"] == "PUBLICATION_CANDIDATE"
        assert row["policy_surface"] == "EMBEDDED_JSON_PAYLOAD"
        assert row["facts"]["pets_allowed"] is True
        assert "schema.org/False" in row["structured_flag"]
        assert row["triage"] == "FOUNDER_EXCEPTION"
    fix = results["probe_008_corrections"][
        "drury inn and suites cincinnati northeast mason"]
    assert fix["was"] == "POLICY_NOT_FOUND"
    assert fix["now"] == "PUBLICATION_CANDIDATE"
    assert "opposite direction" in fix["why"]


def test_every_probe_008_row_this_pass_rechecked_is_carried(results):
    """Confirmations as well as reversals -- otherwise 'corrections' would
    only ever mean 'the ones that changed'."""
    fixes = results["probe_008_corrections"]
    assert len(fixes) == 4
    changed = [k for k, v in fixes.items() if v["was"] != v["now"]]
    confirmed = [k for k, v in fixes.items() if v["was"] == v["now"]]
    assert sorted(changed) == ["drury inn and suites cincinnati northeast mason",
                               "wildwood inn"]
    assert sorted(confirmed) == ["golden lamb", "symphony hotel and restaurant"]
    for key in changed:
        assert fixes[key]["quote"]
        assert fixes[key]["sha256_page"]
        assert fixes[key]["facts"]


def test_the_lane_is_measured_on_the_corrected_readings(lane):
    """Scoring the lane on findings this order disproved understates it."""
    assert "corrected outcome" in lane["corrections_applied"]
    superseded = [r for r in lane["rows"] if r.get("superseded_by")]
    assert len(superseded) == 2
    for row in superseded:
        assert row["superseded_by"] == P.WORK_ORDER
        assert row["outcome"] == "PUBLICATION_CANDIDATE"
        assert row["policy_surface_found"] is True


# -------------------------------------------------------- the readings are honest

def test_every_row_ends_in_one_outcome_and_one_triage(rows):
    for row in rows:
        assert row["outcome"] in set(P.OUTCOMES_009), row["identity_key"]
        assert row["triage"] in set(P.TRIAGES), row["identity_key"]


def test_silence_was_never_read_as_a_refusal(rows):
    silent = [r for r in rows if r["outcome"] == "POLICY_NOT_FOUND"]
    assert len(silent) == 4
    for row in silent:
        assert row["facts"] == {} and row["quote"] == ""
        assert row["triage"] == "NO_FOUNDER_ACTION"
        assert "textContent" in row["notes"] or "read" in row["notes"]


def test_a_word_boundary_false_positive_was_caught(rows):
    """An earlier substring scan "found" pets at Hillcrest, inside
    "Com-pet-ition Racing"."""
    row = next(r for r in rows if r["identity_key"] == "hillcrest motel")
    assert row["outcome"] == "POLICY_NOT_FOUND"
    assert "Com-pet-ition" in row["notes"]


def test_a_pre_opening_hotel_is_held_not_called_a_capture_failure(rows):
    row = next(r for r in rows
               if r["identity_key"] == "cincinnati s fidelity hotel")
    assert row["outcome"] == "HOLD"
    assert row["hold_reason"] == "PRE_OPENING"
    assert "OPENING SUMMER 2026" in row["quote"]
    assert row["facts"] == {}


def test_every_refusal_is_affirmative_and_property_bound(rows):
    refusals = [r for r in rows if r["outcome"] == "VERIFIED_NO_PETS"]
    assert len(refusals) == 4
    for row in refusals:
        assert row["facts"]["pets_allowed"] is False
        assert row["sha256_policy_surface"] and row["sha256_page"]
        assert row["quote"]


def test_every_service_animal_reading_matches_the_classifier(rows):
    seen = 0
    for row in rows:
        stmt = row.get("service_animal_statement")
        if not stmt:
            continue
        seen += 1
        assert SA.charges_stated(stmt["quote"]) in ("no_charge", "not_addressed")
    assert seen >= 6


# ------------------------------------------------------- the founder-held row

def test_the_great_wolf_hold_condition_is_reported_as_met_not_applied(rows):
    """Ruling #2 of APPLICATION-004 named what would lift the hold.

    The founder declined a bare JSON-LD flag and asked for property-specific
    prose. The property's own FAQ now supplies it. This order REPORTS that the
    stated condition is satisfied; applying it is a later order's decision, and
    nothing here writes authority.
    """
    row = next(r for r in rows
               if r["identity_key"] == "great wolf lodge cincinnati mason")
    assert row["outcome"] == "VERIFIED_NO_PETS"
    assert row["policy_surface"] == "PROPERTY_FAQ_ACCORDION"
    assert "we do not allow any pets into the lodge" in row["quote"]
    assert "ruling" in row["satisfies_hold"] and "#2" in row["satisfies_hold"]
    # This pass reported; PTF-CINCINNATI-FREE-LANE-APPLICATION-010 applied the
    # row as VERIFIED_NO_PETS on exactly this evidence. Asserting it was still
    # unresolved would make this test fail on its own finding being acted on,
    # so what is pinned is that the probe's own artifact claims no authority.
    results = _load(P.RESULTS)
    assert results["authority_mutated"] is False


def test_the_great_wolf_corporate_json_ld_was_not_used(rows):
    """Its JSON-LD carries a Chicago HQ address -- weaker than what the
    founder already refused."""
    row = next(r for r in rows
               if r["identity_key"] == "great wolf lodge cincinnati mason")
    assert "CORPORATE address in Chicago" in row["notes"]


# ------------------------------------------------------ the brand correction

def test_the_hilton_row_is_reported_and_not_rewritten(rows, lane):
    row = next(r for r in rows if r["identity_key"] == "the well house hotel")
    assert row["outcome"] == "BRAND_CLASSIFICATION_STALE"
    correction = row["brand_correction"]
    assert correction["census_family"] == "INDEPENDENT"
    assert correction["observed_family"] == "HILTON"
    assert "TAPESTRY COLLECTION BY HILTON" in correction["first_party_evidence"]
    assert "does not edit identity authority" in correction["not_rewritten_here"]
    # The shard still says what it said.
    routes = {r["hotel_ref"]["identity_key"]: r
              for r in _load(AUTH / "identity_routing.json")["routes"]}
    assert routes["the well house hotel"]["brand"] == "INDEPENDENT"
    # And it is not in the independent lane.
    assert "the well house hotel" not in {r["identity_key"]
                                          for r in lane["rows"]}


# --------------------------------------------------------- the semantic guards

def test_a_combined_weight_was_not_published_as_per_pet(rows):
    """Drury says "combined weight of 80 pounds" -- explicitly combined."""
    row = next(r for r in rows if r["official_domain"] == "druryhotels.com")
    assert row["facts"]["combined_weight_limit"]["value"] == 80
    assert "weight_limit" not in row["facts"]


def test_a_per_room_fee_was_not_published_as_per_pet(rows):
    row = next(r for r in rows if r["official_domain"] == "druryhotels.com")
    assert row["facts"]["pet_fee"]["scope"] == "per_room"
    assert row["facts"]["pet_fee"]["basis"] == "per_night"


def test_an_unstated_weight_scope_was_withheld(rows):
    """Warehouse says "2 pets max, 60 lb weight limit" and never says which."""
    row = next(r for r in rows
               if r["identity_key"] == "the warehouse hotel at champion mill")
    assert "60 lb weight limit" in row["quote"]
    assert "weight_limit" not in row["facts"]
    assert "combined_weight_limit" not in row["facts"]
    assert row["facts"]["pet_count_limit"] == 2


def test_a_room_type_condition_was_not_forced_into_a_tier(rows):
    assert enums.TIER_CONDITION_TYPES == ("stay_length_range", "pet_count_range")
    row = next(r for r in rows
               if r["identity_key"] == "the warehouse hotel at champion mill")
    assert "Limited to Standard Room types" in row["quote"]
    assert "fee_tiers" not in row["facts"] and "pet_fee" not in row["facts"]
    assert row["triage"] == "FOUNDER_EXCEPTION"


def test_two_charges_with_different_bases_were_not_collapsed(rows):
    """$50 per STAY plus $10 per NIGHT beyond three nights."""
    row = next(r for r in rows
               if r["identity_key"] == "the warehouse hotel at champion mill")
    assert "$50 per stay" in row["quote"]
    assert "additional $10/night" in row["quote"]
    assert "pet_fee" not in row["facts"]
    assert "different bases" in row["question_for_the_founder"]


# ---------------------------------------------------- the consolidated lane

def test_the_lane_counts_each_genuine_independent_once(lane):
    stats = lane["stats"]
    assert stats["n"] == 19
    keys = [r["identity_key"] for r in lane["rows"]]
    assert len(keys) == len(set(keys)) == 19
    assert lane["excluded_from_the_lane"] == {
        "choice_platform_mislabelled": 3, "esa": 1,
        "brand_classification_stale_hilton": 1}


def test_the_lane_result(lane):
    stats = lane["stats"]
    assert stats["rendered"] == 19 and stats["identity_confirmed"] == 19
    assert stats["publication_grade"] == 12
    assert stats["pet_friendly"] == 7 and stats["verified_no_pets"] == 5
    assert stats["policy_not_found"] == 6 and stats["hold"] == 1
    assert stats["access_blocked"] == 0
    assert 0.62 < stats["publication_grade_point_rate"] < 0.64
    assert 0.40 < stats["wilson_95_lower"] < 0.42
    assert lane["distinct_domains"] == 16
    assert len(lane["domains_yielding_publication_grade"]) == 9


def test_the_final_recommendation_is_site_by_site(lane):
    assert lane["FINAL_RECOMMENDATION"] == "SITE_BY_SITE_FREE_ONLY"
    assert "SILENCE, not access" in lane["because"]
    assert "no further probe" in lane["no_further_probe"].lower() or \
        "not" in lane["no_further_probe"]


def test_silence_can_never_produce_a_paid_lane_recommendation():
    """Derived, so it holds for inputs this order did not get.

    A family that renders perfectly and publishes nothing is still not a paid
    lane -- a provider cannot fetch text that was never written.
    """
    silent = dict(n=20, rendered=20, identity_confirmed=20, access_blocked=0,
                  publication_grade=0, wilson_95_lower=0.0,
                  distinct_domains=20, distinct_domains_yielding=0)
    assert P.final_recommendation(silent)[0] == "SITE_BY_SITE_FREE_ONLY"

    blocked = dict(n=20, rendered=8, identity_confirmed=8, access_blocked=12,
                   publication_grade=4, wilson_95_lower=0.08,
                   distinct_domains=20, distinct_domains_yielding=4)
    assert P.final_recommendation(blocked)[0] == "PAID_LANE_REQUIRED"

    broad = dict(n=20, rendered=20, identity_confirmed=20, access_blocked=0,
                 publication_grade=17, wilson_95_lower=0.64,
                 distinct_domains=18, distinct_domains_yielding=15)
    assert P.final_recommendation(broad)[0] == "FREE_LANE_SCALE"


def test_a_narrow_but_high_yield_still_is_not_family_scale():
    narrow = dict(n=10, rendered=10, identity_confirmed=10, access_blocked=0,
                  publication_grade=9, wilson_95_lower=0.60,
                  distinct_domains=10, distinct_domains_yielding=3)
    assert P.final_recommendation(narrow)[0] == "SITE_BY_SITE_FREE_ONLY"


# ------------------------------------------------------------ the pending work

def test_probe_008_work_is_carried_forward_not_stranded(pending):
    counts = pending["counts"]
    assert sum(counts.values()) == 24          # 10 from 008 + 14 from 009
    assert counts["CLEAN_PET_FRIENDLY"] == 1
    assert counts["CLEAN_VERIFIED_NO_PETS"] == 7
    assert counts["FOUNDER_EXCEPTION"] == 8
    assert counts["NO_AUTHORITY_ACTION"] == 8
    keys = {e["identity_key"] for b in pending["buckets"].values() for e in b}
    for named in ("country inn and suites erlanger",
                  "country inn and suites airport",
                  "radisson hotel cincinnati riverfront",
                  "intown suites cincinnati north",
                  "studio 6 extended stay fairfield oh cincinnati",
                  "the summit hotel"):
        assert named in keys, named


def test_no_pending_entry_carries_a_decision(pending):
    for bucket in pending["buckets"].values():
        for entry in bucket:
            assert entry["founder_decision"] == ""
            assert entry["founder_reviewer_id"] == ""


def test_corrected_entries_say_what_they_supersede(pending):
    entries = [e for b in pending["buckets"].values() for e in b
               if e.get("supersedes")]
    assert len(entries) == 2
    for entry in entries:
        assert "POLICY_NOT_FOUND" in entry["supersedes"]
        assert entry["outcome"] == "PUBLICATION_CANDIDATE"
        assert entry["issue"]


def test_every_founder_exception_is_answerable(pending):
    for entry in pending["buckets"]["FOUNDER_EXCEPTION"]:
        assert entry["issue"], entry["identity_key"]
        assert entry["quote"], entry["identity_key"]
        assert entry["sha256_page"]


# ------------------------------------------------------------------ the reprice

def test_the_independents_are_never_priced():
    """Whatever their yield. Their failures are silence."""
    reprice = _load(P.REPRICE)
    free = reprice["lanes"]["FREE_SITE_BY_SITE"]
    assert set(free["families"]) == {"INDEPENDENT", "ESA"}
    assert free["evidence_captured_pending_application"] == 12
    assert "silence" in reprice["bright_data"]["note"]
    assert set(reprice["lanes"]["BRIGHT_DATA"]["families"]) == {"MARRIOTT",
                                                               "HILTON"}


def test_no_unobserved_independents_remain():
    reprice = _load(P.REPRICE)
    assert reprice["free_attended"]["remaining_site_by_site_opportunities"] == 0
    assert "no unobserved independents left" in \
        reprice["free_attended"]["note"]


def test_the_stale_brand_row_is_counted_where_the_page_proves(reprice=None):
    reprice = _load(P.REPRICE)
    assert reprice["brand_classification_stale"]["count"] == 1
    assert reprice["by_family_observed"]["HILTON"] == 9   # 8 + the Well House
    assert "NOT rewritten" in reprice["brand_classification_stale"]["note"]


def test_firecrawl_stays_at_zero():
    reprice = _load(P.REPRICE)
    assert reprice["firecrawl"]["rows"] == 0
    assert reprice["firecrawl"]["projected_usd"] == 0.0


def test_the_reprice_covers_every_unresolved_row():
    reprice = _load(P.REPRICE)
    counted = sum(v["rows"] for v in reprice["lanes"].values())
    assert counted == reprice["unresolved_routed"] == 79
    assert reprice["unresolved_routed"] + reprice["unresolved_unrouted"] == \
        reprice["unresolved_total"] == 119
    assert "not an authorization" in reprice["note"]


# --------------------------------------------- the two deferred orders stay deferred

def test_the_species_key_defect_was_not_touched():
    from scripts.pettripfinder import canonical_view as CV
    package = _load(PKG / "hotel_policy_facts_cincinnati-oh.json")
    singular = [h for h in package["hotels"]
                if set(h["facts"].get("species") or {}) & {"dog", "cat"}]
    assert len(singular) == 8
    for record in singular:
        view = CV.build(record, market_id="cincinnati-oh")
        assert view.dogs_state == "" and view.cats_state == ""


def test_the_mainstay_identity_hold_was_not_resolved(rows):
    partition = _load(PKG / "cincinnati_final_partition_001.json")
    item = next(i for i in partition["items"]
                if i["identity_key"] == "comfort suites mainstay hotel")
    assert item["resolved"] is False
    routes = {r["hotel_ref"]["identity_key"]
              for r in _load(AUTH / "identity_routing.json")["routes"]}
    assert "comfort suites mainstay hotel" in routes
    assert "comfort suites mainstay hotel" not in {r["identity_key"]
                                                   for r in rows}

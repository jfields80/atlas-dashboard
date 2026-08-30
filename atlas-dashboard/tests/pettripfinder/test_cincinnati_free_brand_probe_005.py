"""PTF-CINCINNATI-FREE-BRAND-PROBE-005 -- what a free-lane probe may claim.

Ten fresh IHG and Choice properties, attended Chrome, no provider and no
dollar. The probe returned 10/10 publication-grade, and a perfect score is
exactly when a measurement most needs pinning down, because the three ways it
could be wrong are all invisible in the headline:

* the SAMPLE could be rigged -- drawn from rows a previous pass already
  succeeded on, or stacked onto one sub-brand and one URL template;
* the RATE could be overstated -- a point estimate from five trials read as if
  it were a rate, which is how a $0.197 lane gets authorized on noise;
* the PROBE could have become authority -- an observation file read one step
  later as an approval.

The Wilson lower bound is the honest number here, and these tests pin that the
recommendation is derived from it rather than from 100%.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_free_brand_probe_005 as P
from scripts.pettripfinder.contracts import service_animal as SA

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"

COHORT = REPORTS / "cincinnati_probe005_cohort.json"
RESULTS = REPORTS / "cincinnati_probe005_results.json"
MEASUREMENT = REPORTS / "cincinnati_probe005_measurement.json"
REPRICE = REPORTS / "cincinnati_probe005_reprice.json"

OUTCOMES = set(P.OUTCOMES)
TRIAGES = set(P.TRIAGES)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def results():
    return _load(RESULTS)


@pytest.fixture(scope="module")
def rows(results):
    return results["rows"]


@pytest.fixture(scope="module")
def measurement():
    return _load(MEASUREMENT)


# ---------------------------------------------------------------- it cost nothing

def test_the_probe_called_no_provider_and_spent_nothing(results):
    assert results["provider_calls"] == 0
    assert results["paid_spend_usd"] == 0.0
    assert results["capture_method"] == "attended_chrome_render"
    for row in results["rows"]:
        assert row["provider_calls"] == 0
        assert row["cost_usd"] == 0.0


def test_the_cohort_respected_its_cap(results):
    cohort = _load(COHORT)
    assert cohort["cap"] == 10
    assert cohort["count"] <= 10
    assert results["cohort_size"] == results["processed"] == 10


def test_every_row_was_processed_exactly_once(rows):
    keys = [r["identity_key"] for r in rows]
    assert len(keys) == len(set(keys)) == 10
    urls = [r["official_property_url"] for r in rows]
    assert len(urls) == len(set(urls))


# ------------------------------------------------------------- the sample is fresh

def test_no_probed_row_had_been_resolved_before_the_probe(rows):
    """A probe of already-answered rows measures the previous pass, not the lane.

    Checked against authority AS IT WAS -- every record and exclusion approved
    before this probe ran. PTF-...-APPLICATION-007 has since published or
    excluded most of these rows, which is the probe succeeding, not a
    violation, and comparing against live authority would read that success as
    a failure.
    """
    published = {h["identity_key"] for h in
                 _load(PKG / "hotel_policy_facts_cincinnati-oh.json")["hotels"]
                 if h["approval"]["approval_date"] < "2026-08-30"}
    excluded = {e["normalized_name"] for e in
                _load(AUTH / "hotel_exclusions.json")["exclusions"]
                if e.get("reviewed_at", "") < "2026-08-30"}
    probed = {r["identity_key"] for r in rows}
    assert probed.isdisjoint(published)
    assert probed.isdisjoint(excluded)


def test_no_probed_row_was_captured_by_an_earlier_pass(rows):
    """'Fresh' has to mean fresh for the question, not absent from one file."""
    seen = P._previously_captured()
    assert len(seen) > 50, "the freshness filter is not actually loading anything"
    assert {r["identity_key"] for r in rows}.isdisjoint(seen)


def test_the_sample_is_split_and_diversified(rows):
    """A sample stacked on one sub-brand or one template measures that template.

    PTF-DETROIT-BRIGHTDATA-PILOT-014 is the precedent: Marriott scored 0/2 on a
    legacy URL shape and 11/11 on the current one, and a sample drawn only from
    the first would have condemned a lane that worked.
    """
    cohort = {r["identity_key"]: r for r in _load(COHORT)["rows"]}
    families = [r["family"] for r in rows]
    assert families.count("IHG") == 5
    assert families.count("CHOICE") == 5
    for family in ("IHG", "CHOICE"):
        members = [cohort[r["identity_key"]] for r in rows
                   if r["family"] == family]
        assert len({m["sub_brand"] for m in members}) >= 4
        assert len({m["city"] for m in members}) >= 3


def test_every_row_is_a_first_party_property_url(rows):
    for row in rows:
        url = row["official_property_url"]
        assert url.startswith("https://")
        host = url.split("/")[2]
        assert host in ("www.ihg.com", "www.choicehotels.com"), row["identity_key"]


# ------------------------------------------------------- it did not become authority

def test_the_probe_wrote_no_authority_and_no_approval(results):
    assert results["authority_mutated"] is False
    assert results["approvals_written"] == 0
    blob = RESULTS.read_text(encoding="utf-8")
    assert "APPROVED_AFTER_CURRENT_REVIEW" not in blob
    assert "jfields80" not in blob
    assert "record_hash" not in blob


def test_the_probe_itself_wrote_no_authority(results):
    """This asserted 74/16/135 while that was the live state.

    The claim it was making -- that a MEASUREMENT order writes no authority --
    is not about the totals, and stating it as totals made it expire the moment
    the founder ruled. What holds permanently is that nothing in the probe's
    own artifacts is an approval, which
    ``test_the_probe_wrote_no_authority_and_no_approval`` pins.
    """
    assert results["authority_mutated"] is False
    assert results["approvals_written"] == 0


# ------------------------------------------------------------- the readings are honest

def test_every_row_ends_in_exactly_one_outcome_and_one_triage(rows):
    for row in rows:
        assert row["outcome"] in OUTCOMES, row["identity_key"]
        assert row["triage"] in TRIAGES, row["identity_key"]


def test_every_refusal_is_affirmative_and_quoted(rows):
    """Silence is never a refusal. Each no-pets row states it in words."""
    for row in rows:
        if row["outcome"] == "VERIFIED_NO_PETS":
            assert row["facts"]["pets_allowed"] is False
            quote = row["quote"].lower()
            assert ("not allowed" in quote or "pets allowed: no" in quote), \
                row["identity_key"]
            assert row["sha256_policy_surface"]


def test_every_quote_is_bound_to_this_property(rows):
    """Generic chain policy is not property-specific evidence.

    An IHG row must carry a sentence, rendered on that page, that names this
    hotel. Usually it is the quote itself; where the surface is the Pet policy
    accordion the panel says only "Our pet friendly hotel", so the naming
    sentence is recorded separately as ``binding_quote``. A panel that names
    nobody is generic chain wording until something on the page binds it.
    """
    for row in rows:
        if row["family"] == "IHG":
            core = row["page_identity"]["name"].split(" - ")[0].split(" (")[0]
            bound = (row["quote"] + " " + row.get("binding_quote", "")).lower()
            assert core.lower()[:12] in bound, row["identity_key"]
            if core.lower()[:12] not in row["quote"].lower():
                assert row["policy_surface"] == "PET_POLICY_ACCORDION"
                assert row["binding_quote"], row["identity_key"]
        else:
            assert row["policy_surface"] == "ESSENTIAL_DETAILS_PETS_BLOCK"
            assert row["quote"].startswith("Pets Allowed:")


def test_every_service_animal_reading_matches_the_classifier(rows):
    """The contract arbitrates, never a plausible reading of the sentence."""
    seen = 0
    for row in rows:
        stmt = row.get("service_animal_statement")
        if not stmt:
            continue
        seen += 1
        assert SA.charges_stated(stmt["quote"]) in ("no_charge", "not_addressed")
    assert seen >= 5


def test_identity_disagreements_are_recorded_not_corrected(rows):
    """Three pages disagree with the census, and none was quietly overwritten.

    One of them is a street digit on a drive where the neighbouring hotel is
    8955 -- exactly the shape where a tidy-up binds the wrong building.
    """
    flagged = [r for r in rows if r["identity_disagreements"]]
    assert len(flagged) == 4          # one street, one name, two phones
    kinds = sorted(d.split(":")[0] for r in flagged
                   for d in r["identity_disagreements"])
    assert kinds == ["name", "phone", "phone", "street"]
    for row in flagged:
        census = row["census_identity"]
        page = row["page_identity"]
        assert census != page
        # The census values are carried verbatim beside the page values.
        assert census["name"], row["identity_key"]


def test_a_fee_the_schema_cannot_hold_was_not_converted(rows):
    """Staybridge states 50 USD per WEEK. There is no per_week basis.

    Dividing by seven would publish a number the hotel never stated, so the
    row is a founder question instead of a quiet conversion.
    """
    from scripts.pettripfinder.contracts import enums
    row = next(r for r in rows
               if r["identity_key"] == "staybridge suites cincinnati north")
    assert "per week" in row["quote"].lower()
    assert "pet_fee" not in row["facts"]
    assert row["triage"] == "FOUNDER_EXCEPTION"
    assert not hasattr(enums, "BASIS_PER_WEEK")


def test_the_multi_charge_row_was_not_collapsed(rows):
    """Ruling 8 of APPLICATION-004 forbade one headline for three charges."""
    row = next(r for r in rows
               if r["identity_key"] ==
               "candlewood suites cincinnati northeast mason")
    assert row["triage"] == "FOUNDER_EXCEPTION"
    assert "pet_fee" not in row["facts"]
    assert row["question_for_the_founder"]


def test_the_renamed_property_is_a_question_not_a_registration(rows):
    """Its refusal is clean; its NAME is what needs a ruling."""
    row = next(r for r in rows
               if r["identity_key"] == "holiday inn express and suites bellevue")
    assert row["outcome"] == "VERIFIED_NO_PETS"
    assert row["triage"] == "FOUNDER_EXCEPTION"
    assert row["page_identity"]["phone"].endswith("8599572320")
    assert row["question_for_the_founder"]


def test_the_choice_surface_hash_is_not_treated_as_property_unique(rows, results):
    """Two Choice hotels produce the SAME surface digest, by design.

    Their refusal blocks are word-for-word and markup-for-markup identical, so
    the digest proves what was said and never by whom. If a later application
    used it as the evidence key, two hotels would share one evidence ref.
    """
    assert "CHOICE" in results["surface_hash_is_not_property_unique"]
    choice = [r for r in rows if r["family"] == "CHOICE"]
    surface = [r["sha256_policy_surface"] for r in choice]
    assert len(set(surface)) < len(surface), "the collision this pins is gone"
    # The page digest and the URL are what actually separate them.
    assert len({r["sha256_page"] for r in choice}) == len(choice)


# --------------------------------------------------------------- the measurement

def test_wilson_is_the_interval_it_claims_to_be():
    assert P.wilson(0, 0) == (0.0, 0.0, 0.0)
    point, lo, hi = P.wilson(5, 5)
    assert point == 1.0 and hi == 1.0
    assert 0.55 < lo < 0.60          # five perfect trials is NOT a rate of 1.0
    point, lo, hi = P.wilson(10, 10)
    assert 0.70 < lo < 0.75          # ten is better, and still not certainty
    _p, lo5, _h = P.wilson(5, 5)
    _p, lo10, _h = P.wilson(10, 10)
    assert lo10 > lo5


def test_the_families_are_measured_separately(measurement):
    """Access is not extraction, so one family's result never carries another.

    PTF-ACQUISITION-BRAND-REPAIR-003 is the precedent for keeping these apart.
    """
    assert set(measurement["families"]) == {"IHG", "CHOICE", "COMBINED"}
    assert set(measurement["recommendations"]) == {"IHG", "CHOICE"}
    for family in ("IHG", "CHOICE"):
        assert measurement["families"][family]["attempted"] == 5
    assert measurement["families"]["COMBINED"]["attempted"] == 10


def test_the_counters_reconcile_to_the_rows(rows, measurement):
    for family in ("IHG", "CHOICE"):
        stats = measurement["families"][family]
        subset = [r for r in rows if r["family"] == family]
        assert stats["attempted"] == len(subset)
        assert stats["publication_grade"] == sum(
            1 for r in subset
            if r["outcome"] in ("PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS"))
        assert stats["pet_friendly"] + stats["verified_no_pets"] == \
            stats["publication_grade"]


def test_policy_not_found_is_not_counted_as_publication_grade():
    """It is an honest observation and it publishes nothing."""
    assert "POLICY_NOT_FOUND" not in P.PUBLICATION_GRADE
    assert "ACCESS_BLOCKED" not in P.PUBLICATION_GRADE
    assert set(P.PUBLICATION_GRADE) == {"PUBLICATION_CANDIDATE",
                                        "VERIFIED_NO_PETS"}


def test_a_blocked_family_cannot_reach_free_lane_scale():
    """The recommendation is derived, so it can be tested on inputs we did not get."""
    blocked = dict(attempted=5, page_rendered=3, identity_confirmed=3,
                   access_blocked=2, publication_grade=3,
                   wilson_95_lower=0.30)
    assert P.recommend(blocked)[0] == "PAID_LANE_REQUIRED"

    thin = dict(attempted=5, page_rendered=5, identity_confirmed=5,
                access_blocked=0, publication_grade=1, wilson_95_lower=0.04)
    assert P.recommend(thin)[0] == "MORE_FREE_PROBE_NEEDED"

    unbound = dict(attempted=5, page_rendered=5, identity_confirmed=2,
                   access_blocked=0, publication_grade=5, wilson_95_lower=0.57)
    assert P.recommend(unbound)[0] == "MORE_FREE_PROBE_NEEDED"


def test_the_recommendation_rests_on_the_lower_bound_not_the_point(measurement):
    for family in ("IHG", "CHOICE"):
        rec = measurement["recommendations"][family]
        stats = measurement["families"][family]
        assert rec["recommendation"] in ("FREE_LANE_SCALE",
                                         "MORE_FREE_PROBE_NEEDED",
                                         "PAID_LANE_REQUIRED")
        assert "Wilson lower" in rec["because"] or "publication-grade" in rec["because"]
        assert stats["wilson_95_lower"] < stats["publication_grade_point_rate"] \
            or stats["publication_grade"] == 0


# ------------------------------------------------------------------- the reprice

def test_the_reprice_covers_every_unresolved_routed_row():
    reprice = _load(REPRICE)
    lanes = reprice["lanes"]
    counted = sum(lanes[name]["rows"] for name in
                  ("attended_chrome_free", "bright_data", "firecrawl",
                   "blocked", "unproven"))
    assert counted == reprice["unresolved_routed"]
    assert reprice["unresolved_routed"] + reprice["unresolved_unrouted"] == \
        reprice["unresolved_total"] == 160


def test_the_free_lane_holds_exactly_the_two_probed_families():
    reprice = _load(REPRICE)
    free = reprice["lanes"]["attended_chrome_free"]
    assert set(free["families"]) == {"IHG", "CHOICE"}
    assert free["usd"] == 0.0
    assert free["rows"] == 42


def test_no_row_is_costed_on_a_lane_it_has_no_evidence_for():
    """An unproven family is reported as unproven, never priced."""
    reprice = _load(REPRICE)
    for family in reprice["lanes"]["unproven"]["families"]:
        assert reprice["lane_evidence"][family]["lane"] == "UNPROVEN"
    assert "usd" not in reprice["lanes"]["unproven"]
    assert reprice["lanes"]["blocked"]["families"] == {"HYATT": 4}


def test_the_reprice_authorizes_nothing():
    reprice = _load(REPRICE)
    assert "not an authorization" in reprice["note"]
    assert reprice["lanes"]["bright_data"]["usd_per_attempt"] == 0.197


# ------------------------------------------ Phase 7: the deferred display defect

def test_the_species_key_defect_is_display_only_and_still_eight_rows():
    """Report-only. The eight founder-approved records are NOT rewritten here.

    The authority value is intact and correct in every one of them -- what
    fails is the projection, which reads ``species["dogs"]`` while these say
    ``species["dog"]``. Renaming the key would move ``record_hash`` and break
    the founder's binding, which is why it needs its own work order rather
    than a line in a probe.
    """
    from scripts.pettripfinder import canonical_view as CV
    package = _load(PKG / "hotel_policy_facts_cincinnati-oh.json")

    singular = [h for h in package["hotels"]
                if set((h["facts"].get("species") or {})) & {"dog", "cat"}]
    assert len(singular) == 8
    assert {h["approval"]["approval_date"] for h in singular} == {"2026-08-17"}

    for record in singular:
        view = CV.build(record, market_id="cincinnati-oh")
        assert view.dogs_state == ""
        assert view.cats_state == ""
        # ...while the authority itself is present and well-formed.
        assert record["facts"]["species"]

    # The control: the same record with the keys spelled plural projects fine,
    # which isolates the cause to the key spelling and nothing else.
    import copy
    probe = copy.deepcopy(singular[0])
    probe["facts"]["species"] = {
        {"dog": "dogs", "cat": "cats"}.get(k, k): v
        for k, v in probe["facts"]["species"].items()}
    assert CV.build(probe, market_id="cincinnati-oh").dogs_state == "accepted"


def test_the_records_applied_since_use_the_form_that_renders():
    from scripts.pettripfinder import canonical_view as CV
    package = _load(PKG / "hotel_policy_facts_cincinnati-oh.json")
    applied = [h for h in package["hotels"]
               if h["approval"]["approval_date"] == "2026-08-29"
               and h["facts"].get("species")]
    assert len(applied) >= 20
    for record in applied:
        assert set(record["facts"]["species"]) <= {"dogs", "cats"}
        assert CV.build(record, market_id="cincinnati-oh").dogs_state != ""

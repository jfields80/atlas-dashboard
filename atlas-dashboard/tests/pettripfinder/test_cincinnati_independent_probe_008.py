"""PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008 -- what a mixed probe may claim.

Ten rows, attended Chrome, no provider and no dollar. Independents come back
2/6 publication-grade, and the recommendation is MORE_FREE_PROBE_NEEDED.

This probe could go wrong in three ways that a headline number hides, and each
has a test here:

* it could FLATTER the family. Three of the four never-captured rows turned out
  to be Choice-platform pages wearing a stale INDEPENDENT label. Counting them
  as independents would credit the independent lane with 3/3 that the Choice
  lane produced, and the blended number would read 6/10 instead of 2/6;
* it could OVER-GENERALISE a clustered win. The two successes are on two
  domains out of six, and independents share no platform, so that is a fact
  about two websites. The recommendation function refuses FREE_LANE_SCALE on
  fewer than three yielding domains even when the rate would otherwise pass;
* it could turn a re-read into an authority claim. Two rows previously recorded
  POLICY_NOT_FOUND now have policies. Nothing here applies them.

It also carries a correction: PTF-CINCINNATI-FREE-LANE-APPLICATION-007 reported
24 rows available for this probe. Four were.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_independent_probe_008 as P
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
def measurement():
    return _load(P.MEASUREMENT)


# ---------------------------------------------------------------- it cost nothing

def test_the_probe_called_no_provider_and_spent_nothing(results):
    assert results["provider_calls"] == 0
    assert results["paid_spend_usd"] == 0.0
    assert results["capture_method"] == "attended_chrome_render"
    for row in results["rows"]:
        assert row["provider_calls"] == 0 and row["cost_usd"] == 0.0
    assert _load(P.REPRICE)["spend_this_order_usd"] == 0.0


def test_the_cohort_respected_its_cap(results, cohort):
    assert cohort["cap"] == 10
    assert cohort["count"] <= 10
    assert results["cohort_size"] == results["processed"] == 10


def test_every_row_was_processed_exactly_once(rows):
    keys = [r["identity_key"] for r in rows]
    assert len(keys) == len(set(keys)) == 10
    urls = [r["official_property_url"] for r in rows]
    assert len(urls) == len(set(urls))


def test_nothing_was_applied_and_no_approval_was_written(results):
    assert results["authority_mutated"] is False
    assert results["approvals_written"] == 0
    for path in (P.RESULTS, P.COHORT, P.MEASUREMENT, P.REPRICE):
        blob = Path(path).read_text(encoding="utf-8")
        assert "APPROVED_AFTER_CURRENT_REVIEW" not in blob, path.name
        assert "record_hash" not in blob, path.name


def test_the_probe_itself_wrote_no_authority(results):
    """This asserted 91/40/94 while that was the live state.

    PTF-CINCINNATI-FREE-LANE-APPLICATION-010 has since applied this probe's
    findings, which is the probe succeeding. The claim worth keeping is that a
    MEASUREMENT order writes nothing, and that is about the order, not the
    totals.
    """
    assert results["authority_mutated"] is False
    assert results["approvals_written"] == 0


# --------------------------------------------------------------- the correction

def test_only_four_rows_had_never_been_captured(cohort):
    """APPLICATION-007 said 24 were available. Four were.

    Its filter took routed + unresolved and never asked whether the row had
    already been looked at. This pins the real number so the mistake is not
    repeated from the same artifact.
    """
    assert "24 rows" in cohort["correction"]
    audit = cohort["audit"]
    assert audit["routed_total"] == 24
    assert audit["admitted_fresh"] == 4
    assert audit["suppressed_previously_captured"] == 14
    assert audit["admitted_re_examine"] == 6
    assert (audit["admitted_fresh"] + audit["admitted_re_examine"]
            + audit["suppressed_previously_captured"]) == audit["routed_total"]


# ------------------------------------------------ it did not flatter the family

def test_choice_platform_rows_are_not_counted_as_independents(rows, measurement):
    """Three "independents" are Choice pages wearing a stale brand label.

    Blended, the probe would read 6/10 publication-grade. Kept apart, the
    independents read 2/6 -- and 2/6 is the number the decision rests on.
    """
    choice = [r for r in rows if r["platform"] == "CHOICE_PLATFORM"]
    assert len(choice) == 3
    for row in choice:
        assert row["official_domain"] == "choicehotels.com"
        assert row["family"] == "INDEPENDENT", "the shard's stale label"
    independents = measurement["INDEPENDENT"]["stats"]
    assert independents["attempted"] == 6
    assert independents["publication_grade"] == 2
    assert measurement["CHOICE_PLATFORM_MISLABELLED"]["stats"]["attempted"] == 3
    # The blend this avoids.
    assert independents["publication_grade_point_rate"] < 0.5
    assert measurement["rates_are_never_blended"] is True


def test_no_independent_stat_counts_a_choice_page(rows, measurement):
    independents = [r for r in rows if r["platform"].startswith("INDEPENDENT")]
    assert len(independents) == 6
    assert all(r["official_domain"] != "choicehotels.com" for r in independents)
    assert len({r["official_domain"] for r in independents}) == 6


def test_the_single_esa_row_is_not_generalised(measurement):
    esa = measurement["ESA"]
    assert esa["included"] is True
    assert esa["stats"]["attempted"] == 1
    assert "single property cannot carry a family rate" in esa["do_not_generalise"]
    assert esa["free_capturable"] is True


# --------------------------------------- it did not over-generalise a clustered win

def test_the_recommendation_refuses_a_two_domain_win(measurement):
    """Two successes on two domains is a fact about two websites."""
    assert measurement["INDEPENDENT"]["distinct_domains_with_yield"] == 2
    assert measurement["INDEPENDENT"]["recommendation"] == "MORE_FREE_PROBE_NEEDED"
    assert "clustered" in measurement["INDEPENDENT"]["because"]


def test_clustering_beats_a_passing_rate_in_the_decision():
    """Derived, so it can be tested on inputs this probe did not get.

    A 5/6 yield concentrated on two domains still must not scale.
    """
    strong = dict(attempted=6, rendered=6, identity_confirmed=6,
                  access_blocked=0, publication_grade=5, wilson_95_lower=0.42)
    assert P.recommend_independents(strong, 2)[0] == "MORE_FREE_PROBE_NEEDED"
    spread = dict(attempted=10, rendered=10, identity_confirmed=10,
                  access_blocked=0, publication_grade=8, wilson_95_lower=0.49)
    assert P.recommend_independents(spread, 6)[0] == "MORE_FREE_PROBE_NEEDED"
    scale = dict(attempted=10, rendered=10, identity_confirmed=10,
                 access_blocked=0, publication_grade=9, wilson_95_lower=0.60)
    assert P.recommend_independents(scale, 6)[0] == "FREE_LANE_SCALE"


def test_an_all_silent_family_is_not_called_a_paid_lane():
    """Silence is not an access failure, and no provider sells a policy a
    hotel never wrote down."""
    silent = dict(attempted=6, rendered=6, identity_confirmed=6,
                  access_blocked=0, publication_grade=0, wilson_95_lower=0.0)
    verdict, why = P.recommend_independents(silent, 0)
    assert verdict == "MORE_FREE_PROBE_NEEDED"
    assert "no paid lane fixes it" in why


def test_a_blocked_family_is_a_paid_lane():
    blocked = dict(attempted=6, rendered=2, identity_confirmed=2,
                   access_blocked=4, publication_grade=1, wilson_95_lower=0.03)
    assert P.recommend_independents(blocked, 1)[0] == "PAID_LANE_REQUIRED"


# ---------------------------------------------------------- the readings are honest

def test_every_row_ends_in_one_outcome_and_one_triage(rows):
    for row in rows:
        assert row["outcome"] in set(P.OUTCOMES), row["identity_key"]
        assert row["triage"] in set(P.TRIAGES), row["identity_key"]


def test_silence_was_never_read_as_a_refusal(rows):
    """Four independents state nothing, and none became VERIFIED_NO_PETS."""
    silent = [r for r in rows if r["outcome"] == "POLICY_NOT_FOUND"]
    assert len(silent) == 4
    for row in silent:
        assert row["facts"] == {}
        assert row["quote"] == ""
        assert row["triage"] == "NO_FOUNDER_ACTION"


def test_a_bare_structured_flag_did_not_become_a_refusal(rows):
    """Drury publishes petsAllowed:False in JSON-LD and nothing in prose.

    Ruling #2 of APPLICATION-004 refused exactly this shape for Great Wolf
    Lodge. Four Cincinnati Drury properties share the template, so accepting
    it here would have written the founder's declined standard into four rows
    at once.
    """
    row = next(r for r in rows if r["official_domain"] == "druryhotels.com")
    assert row["outcome"] == "POLICY_NOT_FOUND"
    assert "schema.org/False" in row["structured_flag_recorded_not_published"]
    assert row["facts"] == {}


def test_corporate_policy_was_not_read_as_property_policy(rows):
    """Motel 6's "Pets Stay Free" is a chain page the property never binds."""
    row = next(r for r in rows if r["family"] == "ESA")
    assert row["facts"] == {"pets_allowed": True}
    assert "pet_fee" not in row["facts"]
    assert "never binds to itself" in row["question_for_the_founder"]
    assert row["triage"] == "FOUNDER_EXCEPTION"


def test_every_refusal_is_affirmative_and_property_bound(rows):
    for row in rows:
        if row["outcome"] != "VERIFIED_NO_PETS":
            continue
        assert row["facts"]["pets_allowed"] is False
        assert row["sha256_policy_surface"] and row["sha256_page"]
        quote = row["quote"].lower()
        assert "pets allowed: no" in quote or "no pets allowed" in quote


def test_the_recovered_refusal_names_its_own_hotel(rows):
    row = next(r for r in rows
               if r["identity_key"] == "intown suites cincinnati north")
    assert row["outcome"] == "VERIFIED_NO_PETS"
    assert row["recovered_from"].startswith("POLICY_NOT_FOUND")
    assert "INTOWN SUITES CINCINNATI OH" in row["quote"]
    assert row["quote"].count("INTOWN SUITES CINCINNATI OH") >= 2


def test_every_service_animal_reading_matches_the_classifier(rows):
    seen = 0
    for row in rows:
        stmt = row.get("service_animal_statement")
        if not stmt:
            continue
        seen += 1
        assert SA.charges_stated(stmt["quote"]) in ("no_charge", "not_addressed")
    assert seen >= 4


# ------------------------------------------------------------ the semantic guards

def test_a_room_type_condition_was_not_forced_into_a_stay_length_tier(rows):
    """The Summit's second $50 applies to two named room types.

    TIER_CONDITION_TYPES holds stay_length_range and pet_count_range only, so
    there is nowhere to put a room-type condition. Publishing it as a tier
    would tell every guest they might owe it.
    """
    assert enums.TIER_CONDITION_TYPES == ("stay_length_range", "pet_count_range")
    row = next(r for r in rows if r["identity_key"] == "the summit hotel")
    assert "One Bedroom Suites" in row["quote"]
    assert "fee_tiers" not in row["facts"]
    assert row["facts"]["pet_fee"]["amount_cents"] == 5000
    assert row["triage"] == "FOUNDER_EXCEPTION"


def test_a_strict_weight_bound_kept_its_operator(rows):
    """"dogs UNDER 50 pounds" excludes a 50lb dog."""
    row = next(r for r in rows if r["identity_key"] == "the summit hotel")
    assert "under 50 pounds" in row["quote"]
    assert row["facts"]["weight_limit"]["operator"] == "lt"
    assert row["facts"]["species"]["cats"] == "prohibited"


def test_a_refundable_deposit_was_not_published_as_a_fee(rows):
    """Erlanger states a per-night fee AND a refundable per-stay deposit.

    They are two charges and the source says so, which is why this row is
    clean rather than an exception -- nothing about it is contradictory.
    """
    row = next(r for r in rows
               if r["identity_key"] == "country inn and suites erlanger")
    assert row["facts"]["pet_fee"]["amount_cents"] == 2500
    assert row["facts"]["pet_fee"]["basis"] == "per_night"
    charges = row["facts"]["other_charges"]
    assert len(charges) == 1
    assert charges[0]["kind"] == "refundable_deposit"
    assert charges[0]["kind"] in enums.OTHER_CHARGE_KINDS
    assert charges[0]["amount_cents"] == 10000
    assert row["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE"


def test_an_in_page_contradiction_is_recorded_not_resolved(rows):
    """The Studio 6 page states two different street addresses."""
    row = next(r for r in rows if r["family"] == "ESA")
    assert len(row["identity_disagreements"]) == 1
    assert "contradicts ITSELF" in row["identity_disagreements"][0]
    assert row["page_identity"]["street"] == "Seward Road"
    assert row["triage"] == "FOUNDER_EXCEPTION"


# --------------------------------------------------- no reader was generalised

def test_the_probe_proposes_no_shared_independent_reader(results):
    """Six domains, five different answers."""
    assert "measures capturability, not reader design" in \
        results["no_shared_independent_reader_is_proposed"]
    locators = results["locators_by_domain"]
    assert len(locators) >= 8
    independent_domains = {r["official_domain"] for r in results["rows"]
                           if r["platform"].startswith("INDEPENDENT")}
    assert independent_domains <= set(locators)
    # Each domain's finding is recorded on its own, including the empty ones.
    assert sum(1 for v in locators.values() if v.startswith("Nothing")) == 4


# ------------------------------------------------------------------ the reprice

def test_independents_moved_to_partial_not_to_a_paid_lane():
    reprice = _load(P.REPRICE)
    partial = reprice["lanes"]["FREE_LANE_PARTIAL"]
    assert set(partial["families"]) == {"INDEPENDENT", "ESA"}
    assert partial["rows"] == 24
    assert "silence is not something a paid provider can buy" in \
        reprice["independent_and_esa"]["what_changed"]
    assert reprice["independent_and_esa"]["still_unobserved"] == 17


def test_firecrawl_stays_at_zero():
    reprice = _load(P.REPRICE)
    assert reprice["firecrawl"]["rows"] == 0
    assert reprice["firecrawl"]["usd"] == 0.0


def test_bright_data_is_unchanged_by_this_probe():
    reprice = _load(P.REPRICE)
    assert reprice["bright_data"]["rows"] == 50
    assert reprice["bright_data"]["projected_usd"] == 9.85
    assert set(reprice["lanes"]["BRIGHT_DATA"]["families"]) == {"MARRIOTT",
                                                               "HILTON"}


def test_the_reprice_covers_every_unresolved_row():
    reprice = _load(P.REPRICE)
    counted = sum(v["rows"] for v in reprice["lanes"].values())
    assert counted == reprice["unresolved_routed"] == 79
    assert reprice["unresolved_routed"] + reprice["unresolved_unrouted"] == \
        reprice["unresolved_total"] == 119
    assert "not an authorization" in reprice["note"]


# ---------------------------------------------- the two deferred orders stay deferred

def test_the_species_key_defect_was_not_touched_by_this_order():
    """This asserted the defect was still present, and it no longer is.

    PTF-CINCINNATI-SPECIES-KEY-REBIND-011 renamed the eight records' species
    keys to the spelling canonical_view reads. What THIS order is entitled to
    claim is that it did not touch them, and the durable form of that claim is
    that no record anywhere carries a singular key and every record with
    species evidence projects.
    """
    from scripts.pettripfinder import canonical_view as CV
    package = _load(PKG / "hotel_policy_facts_cincinnati-oh.json")
    for record in package["hotels"]:
        species = (record.get("facts") or {}).get("species") or {}
        assert not (set(species) & {"dog", "cat"}), record["identity_key"]
        if species:
            view = CV.build(record, market_id="cincinnati-oh")
            assert view.dogs_state or view.cats_state, record["identity_key"]
def test_the_mainstay_identity_hold_was_not_resolved():
    """Neither published nor excluded, and it still holds its route."""
    partition = _load(PKG / "cincinnati_final_partition_001.json")
    item = next(i for i in partition["items"]
                if i["identity_key"] == "comfort suites mainstay hotel")
    assert item["resolved"] is False
    assert item["final_state"] not in ("PUBLISHED_PET_FRIENDLY",
                                       "VERIFIED_NO_PETS")
    routes = {r["hotel_ref"]["identity_key"]
              for r in _load(AUTH / "identity_routing.json")["routes"]}
    assert "comfort suites mainstay hotel" in routes
    probed = {r["identity_key"] for r in _load(P.RESULTS)["rows"]}
    assert "comfort suites mainstay hotel" not in probed

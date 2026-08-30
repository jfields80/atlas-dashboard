"""PTF-CINCINNATI-FREE-LANE-SCALE-006 -- running a qualified lane out.

32 rows, attended Chrome, no provider and no dollar. Combined with PROBE-005
the free lane closes at 42/42 publication-grade.

A scale run fails differently from a probe. A probe's risk is that its sample
flatters the lane; a scale run's risk is that VOLUME starts making decisions --
that a template's boilerplate gets read as a fact thirty times, that two hotels
a hundred feet apart get reconciled into one because it is tidier, that a
founder question gets answered in flight because stopping was inconvenient.
These pin the three:

* the IHG structured field says "per night" whatever the prose says. Six rows
  turn on that, and the one row where field and prose agree is published clean
  -- which is what makes it a finding rather than a blanket distrust;
* four pairs of near-neighbour properties appear in this cohort, including two
  Riverfront Holiday Inns with OPPOSITE pet policies. None was normalised
  toward another;
* every exception carries an empty decision field, and both per-week rows are
  in the packet rather than divided by seven.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_free_lane_scale_006 as S
from scripts.pettripfinder import cincinnati_scale006_apply as A
from scripts.pettripfinder.contracts import enums, service_animal as SA

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def results():
    return _load(S.RESULTS)


@pytest.fixture(scope="module")
def rows(results):
    return results["rows"]


@pytest.fixture(scope="module")
def cohort():
    return _load(S.COHORT)


@pytest.fixture(scope="module")
def lane():
    return _load(S.LANE)


@pytest.fixture(scope="module")
def packet():
    return _load(S.PACKET)


# ---------------------------------------------------------------- it cost nothing

def test_the_scale_run_called_no_provider_and_spent_nothing(results):
    assert results["provider_calls"] == 0
    assert results["paid_spend_usd"] == 0.0
    assert results["capture_method"] == "attended_chrome_render"
    for row in results["rows"]:
        assert row["provider_calls"] == 0 and row["cost_usd"] == 0.0
    assert _load(S.REPRICE)["spend_this_order_usd"] == 0.0


def test_every_admitted_row_was_processed_exactly_once(results, rows, cohort):
    assert results["cohort_size"] == results["processed"] == 32
    keys = [r["identity_key"] for r in rows]
    assert len(keys) == len(set(keys)) == 32
    assert set(keys) == {r["identity_key"] for r in cohort["rows"]}
    urls = [r["official_property_url"] for r in rows]
    assert len(urls) == len(set(urls))


def test_no_row_was_observed_by_both_passes(rows):
    """The lane total is 42 only if the two cohorts are disjoint."""
    probe = {r["identity_key"] for r in _load(S.PROBE_RESULTS)["rows"]}
    assert probe.isdisjoint({r["identity_key"] for r in rows})
    assert len(probe) == 10


# ------------------------------------------------- the cohort was rebuilt, not assumed

def test_the_cohort_was_rebuilt_from_current_state(cohort):
    assert "no historical remaining-row count was trusted" in cohort["basis"]
    for family, audit in cohort["audit_by_family"].items():
        # Every routed row is accounted for by admission or a named suppression.
        suppressed = sum(v for k, v in audit.items()
                         if k.startswith("suppressed_"))
        assert audit["admitted"] + suppressed == audit["routed_total"], family


def test_the_cohort_is_exactly_what_remained(cohort):
    audit = cohort["audit_by_family"]
    assert audit["IHG"]["routed_total"] == 24
    assert audit["IHG"]["admitted"] == 19
    assert audit["CHOICE"]["routed_total"] == 18
    assert audit["CHOICE"]["admitted"] == 13
    assert cohort["count"] == 32
    for family in ("IHG", "CHOICE"):
        assert audit[family]["suppressed_answered_by_probe_005"] == 5


def test_no_row_was_admitted_that_authority_already_answered(rows):
    published = {h["identity_key"] for h in
                 _load(PKG / "hotel_policy_facts_cincinnati-oh.json")["hotels"]}
    excluded = {e["normalized_name"] for e in
                _load(AUTH / "hotel_exclusions.json")["exclusions"]}
    probed = {r["identity_key"] for r in rows}
    assert probed.isdisjoint(published) and probed.isdisjoint(excluded)
    assert probed.isdisjoint(S._previously_captured())


# ------------------------------------------------------- it did not become authority

def test_nothing_was_applied_and_no_approval_was_written(results):
    assert results["authority_mutated"] is False
    assert results["approvals_written"] == 0
    for path in (S.RESULTS, S.CLEAN_PF, S.CLEAN_NP, S.PACKET):
        blob = Path(path).read_text(encoding="utf-8")
        assert "APPROVED_AFTER_CURRENT_REVIEW" not in blob, path.name
        assert "jfields80" not in blob, path.name
        assert "record_hash" not in blob, path.name


def test_the_committed_totals_did_not_move():
    package = _load(PKG / "hotel_policy_facts_cincinnati-oh.json")
    assert len(package["hotels"]) == 74
    exclusions = _load(AUTH / "hotel_exclusions.json")["exclusions"]
    assert sum(1 for e in exclusions
               if e["exclusion_state"] == "VERIFIED_NO_PETS") == 16
    assert _load(AUTH / "identity_routing.json")["count"] == 135


def test_the_reprice_does_not_deduct_rows_a_founder_has_not_ruled_on():
    """Answered is not resolved. Deducting these would price the market as if
    a founder had already ruled."""
    reprice = _load(S.REPRICE)
    free = reprice["lanes"]["ATTENDED_CHROME_FREE_CLOSED"]
    assert free["rows"] == 42 and free["answered_pending_review"] == 42
    assert reprice["unresolved_total"] == 160


# ------------------------------------------------------------- the readings are honest

def test_every_row_ends_in_one_outcome_and_one_triage(rows):
    for row in rows:
        assert row["outcome"] in set(S.OUTCOMES), row["identity_key"]
        assert row["triage"] in set(S.TRIAGES), row["identity_key"]


def test_every_refusal_is_affirmative_and_quoted(rows):
    for row in rows:
        if row["outcome"] == "VERIFIED_NO_PETS":
            assert row["facts"]["pets_allowed"] is False
            quote = row["quote"].lower()
            assert "not allowed" in quote or "pets allowed: no" in quote, \
                row["identity_key"]
            assert row["sha256_policy_surface"] and row["sha256_page"]


def test_every_ihg_quote_names_its_own_hotel(rows):
    """No policy was read from a sibling property."""
    for row in rows:
        if row["family"] != "IHG":
            continue
        core = row["page_identity"]["name"].split(" - ")[0].split("(")[0]
        core = re.sub(r"[^a-z ]", "", core.lower()).strip()
        assert core[:14] in row["quote"].lower(), row["identity_key"]


def test_every_service_animal_reading_matches_the_classifier(rows):
    seen = 0
    for row in rows:
        stmt = row.get("service_animal_statement")
        if not stmt:
            continue
        seen += 1
        assert SA.charges_stated(stmt["quote"]) in ("no_charge", "not_addressed")
    assert seen >= 13


# ------------------------------------------------- the template finding, and its limit

IHG_FIELD_CONFLICTS = (
    "candlewood suites erlanger south cincinnati",
    "holiday inn cincinnati airport",
    "holiday inn express hotel and suites mason",
)


@pytest.mark.parametrize("identity_key", IHG_FIELD_CONFLICTS)
def test_a_boilerplate_nightly_label_never_became_a_published_basis(rows,
                                                                    identity_key):
    """IHG prints "Pet fee per night" whatever the prose says.

    Holiday Inn Cincinnati Airport is the sharpest case: the prose says "75.00
    USD per stay" and the field says "per night", same number. Over seven
    nights those readings differ by 450 USD, and publishing the wrong one tells
    a guest a price the hotel never quoted.
    """
    row = next(r for r in rows if r["identity_key"] == identity_key)
    assert "pet fee per night" in row["quote"].lower()
    assert "pet_fee" not in row["facts"], "the contradicted fee was published"
    assert row["triage"] == "FOUNDER_EXCEPTION"
    assert row["question_for_the_founder"]


def test_the_row_where_field_and_prose_agree_is_clean(rows):
    """Otherwise the finding would be a blanket distrust of the field."""
    row = next(r for r in rows
               if r["identity_key"] == "holiday inn cincinnati riverfront")
    assert "flat nonrefundable fee of 25 USD per night" in row["quote"]
    assert "pet fee per night: 25 usd" in row["quote"].lower()
    assert row["facts"]["pet_fee"]["amount_cents"] == 2500
    assert row["facts"]["pet_fee"]["basis"] == "per_night"
    assert row["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE"


def test_a_flat_room_fee_was_not_published_as_per_pet(rows):
    """"a flat ... fee ... for up to 2 pets in the room" is per_room."""
    row = next(r for r in rows
               if r["identity_key"] == "holiday inn cincinnati riverfront")
    assert row["facts"]["pet_fee"]["scope"] == "per_room"


# ------------------------------------------------------------ the semantic guards

def test_neither_per_week_row_was_converted(rows):
    """50 USD per week is not 7.14 per night. There is no per_week basis."""
    assert not hasattr(enums, "BASIS_PER_WEEK")
    milford = next(r for r in rows
                   if r["identity_key"] == "staybridge suites milford")
    assert "per week" in milford["quote"].lower()
    assert "pet_fee" not in milford["facts"]
    assert milford["triage"] == "FOUNDER_EXCEPTION"
    # And PROBE-005's row is still in the packet beside it, unconverted.
    packet_keys = {r["identity_key"] for r in _load(S.PACKET)["rows"]}
    assert "staybridge suites cincinnati north" in packet_keys
    assert "staybridge suites milford" in packet_keys


def test_tier_boundaries_stated_in_days_were_not_read_as_nights(rows):
    assert enums.TIER_BOUNDARY_UNITS == ("nights", "pets")
    row = next(r for r in rows
               if r["identity_key"] == "staybridge suites florence")
    assert "1 to 6 days" in row["quote"]
    assert "fee_tiers" not in row["facts"] and "pet_fee" not in row["facts"]
    assert row["triage"] == "FOUNDER_EXCEPTION"


def test_a_nonrefundable_deposit_was_not_published_as_either(rows):
    """Cincinnati West calls 500 USD a deposit and then says it is not
    refundable. That is a contradiction to rule on, not a field to pick."""
    row = next(r for r in rows
               if r["identity_key"] == "holiday inn express cincinnati west")
    assert "deposit" in row["quote"].lower()
    assert "nonrefundable" in row["quote"].lower()
    assert row["facts"] == {"pets_allowed": True}
    assert row["triage"] == "FOUNDER_EXCEPTION"


def test_strict_weight_bounds_kept_their_operator(rows):
    """"under 25lbs" excludes a 25lb dog; "up to 20 lbs" does not."""
    strict = next(r for r in rows
                  if r["identity_key"] == "quality inn and suites lawrenceburg")
    assert "under 25lbs" in strict["quote"]
    assert strict["facts"]["weight_limit"]["operator"] == "lt"
    inclusive = next(r for r in rows
                     if r["identity_key"] == "quality inn and suites florence")
    assert inclusive["facts"]["weight_limit"]["operator"] == "lte"


def test_no_species_was_inferred_from_a_sibling(rows):
    """Species appear only where the page states them, in plural keys."""
    for row in rows:
        species = row["facts"].get("species")
        if species is None:
            continue
        assert set(species) <= {"dogs", "cats"}, row["identity_key"]
        quote = row["quote"].lower()
        assert "dog" in quote or "cat" in quote, row["identity_key"]


def test_silence_was_never_read_as_a_refusal(rows):
    for row in rows:
        if row["outcome"] == "POLICY_NOT_FOUND":
            assert row["facts"].get("pets_allowed") is None


# ---------------------------------------------------- neighbours stayed separate

NEIGHBOURS = (
    # (a, b, what makes them confusable)
    ("holiday inn cincinnati riverfront",
     "holiday inn express and suites cincinnati riverfront",
     "near-identical names in the same city -- and OPPOSITE pet policies"),
    ("comfort inn blue ash",
     "holiday inn express hotel and suites cincinnati blue ash",
     "4640 and 4660 Creek Road"),
    ("comfort inn oxford", "sleep inn and suites oxford",
     "5056 and 5190 College Corner Pike"),
    ("holiday inn express and suites cincinnati northeast milford",
     "staybridge suites milford", "same town, different roads"),
)


@pytest.mark.parametrize("a,b,why", NEIGHBOURS)
def test_near_neighbours_were_not_reconciled(rows, a, b, why):
    """Volume is when 'these are probably the same' starts sounding tidy."""
    by_key = {r["identity_key"]: r for r in rows}
    ra, rb = by_key[a], by_key[b]
    assert ra["identity_key"] != rb["identity_key"], why
    assert ra["official_property_url"] != rb["official_property_url"]
    assert ra["page_identity"]["street"] != rb["page_identity"]["street"]
    assert ra["sha256_page"] != rb["sha256_page"]


def test_the_two_riverfronts_kept_their_opposite_policies(rows):
    by_key = {r["identity_key"]: r for r in rows}
    assert by_key["holiday inn cincinnati riverfront"][
        "facts"]["pets_allowed"] is True
    assert by_key["holiday inn express and suites cincinnati riverfront"][
        "facts"]["pets_allowed"] is False


def test_the_choice_surface_digest_is_still_not_property_unique(rows, results):
    """The collision PROBE-005 predicted, at scale: seven hotels, one digest.

    It proves what was said, never by whom. The page digest is what separates
    them, and every one of them is distinct.
    """
    assert "CHOICE" in results["surface_hash_is_not_property_unique"]
    choice = [r for r in rows if r["family"] == "CHOICE"]
    digests = [r["sha256_policy_surface"] for r in choice]
    assert len(set(digests)) < len(digests)
    assert max(digests.count(d) for d in digests) >= 5
    assert len({r["sha256_page"] for r in choice}) == len(choice)


# ---------------------------------------------------------- identity differences

def test_every_difference_is_recorded_with_a_kind_and_never_corrected(rows):
    flagged = [r for r in rows if r["identity_disagreements"]]
    assert len(flagged) == 10
    kinds = {r["difference_kind"] for r in flagged}
    assert kinds <= {"formatting", "stale_census", "rename_or_naming",
                     "different_property", "unresolved"}
    for row in flagged:
        assert row["difference_kind"], row["identity_key"]
        # Both sides are carried verbatim; nothing was overwritten.
        assert row["census_identity"]["name"]
        assert row["page_identity"]["name"]
        assert row["census_identity"] != row["page_identity"]


def test_rows_with_no_recorded_difference_really_agree(rows):
    """Otherwise 'no difference' would just mean 'not looked at'."""
    for row in rows:
        if row["identity_disagreements"]:
            continue
        assert row["street_agrees_after_formatting"], row["identity_key"]
        census, page = row["census_identity"], row["page_identity"]
        assert census["postal_code"] == page["postal_code"], row["identity_key"]


def test_the_unresolved_identity_is_the_only_unconfirmed_row(rows):
    """Three of four signals disagree on one row, and it is held, not guessed."""
    unresolved = [r for r in rows if r["difference_kind"] == "unresolved"]
    assert [r["identity_key"] for r in unresolved] == \
        ["comfort suites mainstay hotel"]
    row = unresolved[0]
    assert row["identity_confirmed"] is False
    assert len(row["identity_disagreements"]) == 3
    assert row["triage"] == "FOUNDER_EXCEPTION"
    assert all(r["identity_confirmed"] for r in rows
               if r["identity_key"] != row["identity_key"])


def test_a_subset_name_is_not_treated_as_a_rename(rows):
    """Hebron was PREFIXED to the census name; Bellevue was REPLACED.

    PROBE-005 sent the Bellevue row to the founder because the place name
    itself changed. Treating a prefix the same way would flood the packet.
    """
    row = next(r for r in rows
               if r["identity_key"] == "holiday inn express cincinnati airport")
    assert row["difference_kind"] == "formatting"
    assert row["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE"
    assert "Cincinnati Airport" in row["page_identity"]["name"]
    assert "Cincinnati Airport" in row["census_identity"]["name"]


# ----------------------------------------------------------------- the packet

def test_the_packet_holds_only_genuine_exceptions(packet, rows):
    assert packet["count"] == 10
    keys = {r["identity_key"] for r in packet["rows"]}
    scale_exceptions = {r["identity_key"] for r in rows
                        if r["triage"] == "FOUNDER_EXCEPTION"}
    probe_exceptions = {r["identity_key"]
                        for r in _load(S.PROBE_RESULTS)["rows"]
                        if r["triage"] == "FOUNDER_EXCEPTION"}
    assert keys == scale_exceptions | probe_exceptions
    assert len(scale_exceptions) == 7 and len(probe_exceptions) == 3
    clean = {r["identity_key"] for r in rows
             if r["triage"].startswith("CLEAN_")}
    assert keys.isdisjoint(clean), "a clean row was sent to review"


def test_every_packet_entry_is_answerable(packet):
    for entry in packet["rows"]:
        assert entry["property"] and entry["family"]
        assert entry["issue"], entry["identity_key"]
        assert entry["evidence_quote"]
        assert entry["evidence_sha256_page"]
        assert entry["recommended_disposition"]
        assert entry["reason"]
        assert entry["withheld_fields"], entry["identity_key"]


def test_no_decision_was_made_in_flight(packet):
    for entry in packet["rows"]:
        assert entry["founder_decision"] == ""
        assert entry["founder_reviewer_id"] == ""
        assert entry["founder_note"] == ""


def test_the_packet_carries_both_passes(packet):
    sources = {e["observed_by"] for e in packet["rows"]}
    assert sources == {"PTF-CINCINNATI-FREE-BRAND-PROBE-005",
                       "PTF-CINCINNATI-FREE-LANE-SCALE-006"}


# ------------------------------------------------------------- the measurement

def test_the_lane_closes_at_forty_two(lane):
    combined = lane["COMBINED"]["free_lane_total"]
    assert combined["n"] == 42
    assert combined["publication_grade"] == 42
    assert combined["pet_friendly"] == 17
    assert combined["verified_no_pets"] == 25
    assert combined["policy_not_found"] == 0
    assert combined["access_blocked"] == 0
    assert combined["wilson_95_lower"] > 0.90


def test_the_families_still_close_separately(lane):
    assert lane["IHG"]["free_lane_total"]["n"] == 24
    assert lane["CHOICE"]["free_lane_total"]["n"] == 18
    for family in ("IHG", "CHOICE"):
        total = lane[family]["free_lane_total"]
        assert total["publication_grade"] == total["n"]
        assert total["wilson_95_lower"] > 0.80
        assert total["wilson_95_lower"] < 1.0, "a rate is not a certainty"


def test_scale_did_not_quietly_beat_the_probe_bound(lane):
    """More trials must RAISE the lower bound, or the arithmetic is wrong."""
    for family in ("IHG", "CHOICE", "COMBINED"):
        probe = lane[family]["probe_005"]["wilson_95_lower"]
        total = lane[family]["free_lane_total"]["wilson_95_lower"]
        assert total > probe, family


def test_the_counters_reconcile_to_the_rows(rows, lane):
    for family in ("IHG", "CHOICE"):
        stats = lane[family]["scale_006"]
        subset = [r for r in rows if r["family"] == family]
        assert stats["n"] == len(subset)
        assert stats["clean_pet_friendly"] + stats["clean_verified_no_pets"] \
            + stats["founder_exception"] == len(subset)


# ------------------------------------------------------------------- the reprice

def test_firecrawl_stays_at_zero():
    """It is not resurrected because an older plan named it."""
    reprice = _load(S.REPRICE)
    assert reprice["firecrawl"]["rows"] == 0
    assert reprice["firecrawl"]["usd"] == 0.0
    assert "older plan" in reprice["firecrawl"]["why"]


def test_the_reprice_covers_every_unresolved_routed_row():
    reprice = _load(S.REPRICE)
    counted = sum(v["rows"] for v in reprice["lanes"].values())
    assert counted == reprice["unresolved_routed"] == 120
    assert reprice["unresolved_routed"] + reprice["unresolved_unrouted"] == 160
    assert sum(reprice["unrouted_by_state"].values()) == 40


def test_no_family_is_costed_without_evidence():
    reprice = _load(S.REPRICE)
    assert set(reprice["lanes"]["BRIGHT_DATA"]["families"]) == {"MARRIOTT",
                                                               "HILTON"}
    assert reprice["bright_data"]["projected_usd"] == 9.85
    assert "usd" not in reprice["lanes"]["FREE_LANE_UNPROVEN"]
    assert reprice["lanes"]["BLOCKED_BY_ADR"]["families"] == {"HYATT": 4}
    assert "not an authorization" in reprice["note"]


# ------------------------------------------------ Phase 10: still report-only

def test_the_species_key_defect_was_not_touched():
    """Deferred to PTF-CINCINNATI-SPECIES-KEY-REBIND-007, unchanged at 8."""
    from scripts.pettripfinder import canonical_view as CV
    package = _load(PKG / "hotel_policy_facts_cincinnati-oh.json")
    singular = [h for h in package["hotels"]
                if set(h["facts"].get("species") or {}) & {"dog", "cat"}]
    assert len(singular) == 8
    assert {h["approval"]["approval_date"] for h in singular} == {"2026-08-17"}
    for record in singular:
        view = CV.build(record, market_id="cincinnati-oh")
        assert view.dogs_state == "" and view.cats_state == ""

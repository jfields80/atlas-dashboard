# -*- coding: utf-8 -*-
"""PTF-GENERIC-CROSS-RUN-DISCOVERY-ATTEMPT-LEDGER-001.

The paid-attempt ledger stopped this project buying the same PAGE twice. It
cannot stop it buying the same LOOKUP twice, because every lane it records
fetches a page you already have a URL for. This is the missing half, and these
tests pin the six behaviours it exists for:

  * a hotel renamed by a re-census is not re-discovered for money;
  * the 30-day provider cache expiring does not make it a new question;
  * a genuinely changed address DOES permit a new lookup;
  * a dual-brand building keeps both of its hotels;
  * a lookup that already failed is not repeated by the method that failed;
  * an override must carry a durable reason.

The negative tests are the load-bearing ones. Suppressing a hotel that was
never looked up means it never gets a URL, never gets a policy and never gets
published -- which is worse than paying twice to find it.
"""
from __future__ import annotations

import pytest

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL

PROVIDER = "GOOGLE_PLACES"
METHOD = "searchText"
MASK = ("places.displayName", "places.nationalPhoneNumber", "places.websiteUri")


def row(identity_key, name, street, postal, phone="", city="Indianapolis",
        state="IN", place_id=""):
    return {"identity_key": identity_key, "canonical_name": name,
            "street": street, "city": city, "state": state,
            "postal_code": postal, "telephone": phone, "place_id": place_id}


def attempt(source, *, run_id="run-1", bind_state=DAL.BIND_BOUND,
            place_id="PLACE-A", website="https://hotel.example.com/",
            method=METHOD, at="2026-01-01T00:00:00Z", bind_method="PHONE"):
    return DAL.build_attempt(source, market_id="indianapolis-in",
                             work_order="WO-1", run_id=run_id,
                             provider=PROVIDER, method=method, field_mask=MASK,
                             attempted_at=at, place_id=place_id,
                             website_uri=website, bind_state=bind_state,
                             bind_method=bind_method)


def ledger_of(*records):
    return DAL.merge(DAL.new_ledger(), list(records))


def decide(target, ledger, material=None, method=METHOD):
    payable, suppressed = DAL.suppress(
        [target], ledger, provider=PROVIDER, method=method, field_mask=MASK,
        material_changes={target["identity_key"]: material} if material else None)
    single = (payable or suppressed)[0]
    return single["discovery_history"], bool(payable)


CANDLEWOOD = row("candlewood suites indianapolis east",
                 "Candlewood Suites Indianapolis East",
                 "7040 Shadeland Road", "46219", phone="3175551212")


class TestARenameIsNotANewQuestion:
    """The leak this module closes."""

    def test_the_same_hotel_under_a_new_key_is_not_bought_again(self):
        after_rename = row("candlewood suites indianapolis east side",
                           "Candlewood Suites Indianapolis East",
                           "7040 Shadeland Road", "46219", phone="3175551212")
        history, payable = decide(after_rename, ledger_of(attempt(CANDLEWOOD)))
        assert not payable
        assert history["decision"] == DAL.SUPPRESSED_URL_ALREADY_KNOWN
        assert history["url_already_known"] is True

    def test_the_fingerprint_ignores_the_identity_key_entirely(self):
        renamed = dict(CANDLEWOOD, identity_key="something else entirely")
        assert (DAL.query_fingerprint(renamed, provider=PROVIDER, method=METHOD,
                                      field_mask=MASK)
                == DAL.query_fingerprint(CANDLEWOOD, provider=PROVIDER,
                                         method=METHOD, field_mask=MASK))

    def test_the_premises_carry_no_identity_key(self):
        assert "identity_key" not in DAL.query_premises(CANDLEWOOD)


class TestCacheExpiryDoesNotReopenTheQuestion:
    """The provider cache is a performance store with a 30-day expiry. The
    ledger is a memory without one."""

    def test_a_lookup_from_last_year_still_suppresses_today(self):
        old = attempt(CANDLEWOOD, at="2025-01-01T00:00:00Z", run_id="ancient")
        history, payable = decide(CANDLEWOOD, ledger_of(old))
        assert not payable
        assert history["prior_run_id"] == "ancient"

    def test_suppression_does_not_consult_a_cache_pointer(self):
        """The record keeps one so a human can find the payload, but the
        decision never depends on the file still being there."""
        old = DAL.build_attempt(CANDLEWOOD, market_id="indianapolis-in",
                                work_order="WO", run_id="r", provider=PROVIDER,
                                method=METHOD, field_mask=MASK,
                                attempted_at="2025-01-01T00:00:00Z",
                                place_id="PLACE-A", website_uri="https://h.example",
                                bind_state=DAL.BIND_BOUND,
                                cache_pointer="data/discovery/gone/deleted.json")
        history, payable = decide(CANDLEWOOD, ledger_of(old))
        assert not payable
        assert history["prior_cache_pointer"].endswith("deleted.json")


class TestAMateriallyChangedAddressPermitsANewLookup:

    def test_a_moved_hotel_may_be_looked_up_again(self):
        moved = row("candlewood suites indianapolis east",
                    "Candlewood Suites Indianapolis East",
                    "9000 Completely Different Parkway", "46229",
                    phone="3175551212")
        history, payable = decide(
            moved, ledger_of(attempt(CANDLEWOOD)),
            material={"reason": DAL.MATERIAL_PREMISES_CHANGED,
                      "detail": "the property relocated; street and postal code "
                                "both differ from the prior lookup"})
        assert payable
        assert history["decision"] == DAL.ALLOWED_PREMISES_CHANGED

    def test_the_claim_is_checked_against_the_record_not_believed(self):
        """An assertion that the address changed, over premises that fingerprint
        identically, is contradicted by the ledger's own record."""
        history, payable = decide(
            CANDLEWOOD, ledger_of(attempt(CANDLEWOOD)),
            material={"reason": DAL.MATERIAL_PREMISES_CHANGED,
                      "detail": "claiming a change that did not happen"})
        assert not payable
        assert history["decision"] == DAL.SUPPRESSED_URL_ALREADY_KNOWN


class TestDualBrandBuildingsKeepBothHotels:
    """The failure that costs coverage rather than money, which is the more
    expensive one."""

    def test_a_shared_switchboard_does_not_suppress_a_sibling_brand(self):
        hampton = row("hampton inn downtown", "Hampton Inn Downtown",
                      "10 Shared Street", "46204", phone="3175559999")
        homewood = row("homewood suites downtown", "Homewood Suites Downtown",
                       "10 Shared Street", "46204", phone="3175559999")
        history, payable = decide(homewood, ledger_of(attempt(hampton)))
        assert payable, "a shared phone line collapsed two different hotels"
        assert history["decision"] == DAL.FIRST_DISCOVERY_LOOKUP

    def test_a_shared_address_does_not_suppress_a_sibling_brand(self):
        place = row("hyatt place downtown", "Hyatt Place Downtown",
                    "130 South Pennsylvania Street", "46204")
        house = row("hyatt house downtown", "Hyatt House Downtown",
                    "130 South Pennsylvania Street", "46204")
        _history, payable = decide(house, ledger_of(attempt(place)))
        assert payable

    def test_two_different_provider_place_ids_refute_a_premises_match(self):
        a = row("inn one", "Inn One", "1 Same Street", "46204", phone="3175550000")
        b = row("inn one annex", "Inn One Annex", "1 Same Street", "46204",
                phone="3175550000", place_id="PLACE-B")
        _history, payable = decide(b, ledger_of(attempt(a, place_id="PLACE-A")))
        assert payable

    def test_a_compatible_name_at_one_address_IS_the_same_property(self):
        """The guard proposes on premises and confirms on the name -- so the
        unqualified form of the same hotel still suppresses."""
        full = row("candlewood suites indianapolis east",
                   "Candlewood Suites Indianapolis East",
                   "7040 Shadeland Road", "46219")
        short = row("candlewood suites", "Candlewood Suites",
                    "7040 Shadeland Road", "46219")
        _history, payable = decide(short, ledger_of(attempt(full)))
        assert not payable


class TestAFailedLookupIsNotBlindlyRepeated:

    def test_the_same_method_that_found_nothing_is_not_bought_again(self):
        failed = attempt(CANDLEWOOD, bind_state=DAL.BIND_NO_WEBSITE,
                         website="", place_id="PLACE-A")
        history, payable = decide(CANDLEWOOD, ledger_of(failed))
        assert not payable
        assert history["decision"] == DAL.SUPPRESSED_SAME_METHOD_ALREADY_FAILED

    def test_an_ota_only_answer_is_a_finding_not_an_invitation_to_retry(self):
        failed = attempt(CANDLEWOOD, bind_state=DAL.BIND_REJECTED_URL_SHAPE,
                         website="https://www.booking.com/hotel/x.html")
        _history, payable = decide(CANDLEWOOD, ledger_of(failed))
        assert not payable

    def test_a_genuinely_different_method_is_allowed_after_a_failure(self):
        failed = attempt(CANDLEWOOD, bind_state=DAL.BIND_NO_RESULT, website="")
        history, payable = decide(
            CANDLEWOOD, ledger_of(failed), method="nearbySearch",
            material={"reason": DAL.MATERIAL_DIFFERENT_METHOD,
                      "detail": "searchText found nothing; nearbySearch on the "
                                "coordinates is a different question"})
        assert payable
        assert history["decision"] == DAL.ALLOWED_DIFFERENT_METHOD

    def test_asserting_a_different_method_while_repeating_the_same_one_is_refused(self):
        failed = attempt(CANDLEWOOD, bind_state=DAL.BIND_NO_RESULT, website="")
        history, payable = decide(
            CANDLEWOOD, ledger_of(failed),
            material={"reason": DAL.MATERIAL_DIFFERENT_METHOD,
                      "detail": "claiming novelty while running searchText again"})
        assert not payable
        assert history["decision"] == DAL.SUPPRESSED_SAME_METHOD_ALREADY_FAILED


class TestAnOverrideMustCarryADurableReason:

    def test_an_override_without_a_detail_is_refused_outright(self):
        with pytest.raises(DAL.DiscoveryLedgerError) as excinfo:
            decide(CANDLEWOOD, ledger_of(attempt(CANDLEWOOD)),
                   material={"reason": DAL.MATERIAL_OPERATOR_OVERRIDE,
                             "detail": "   "})
        assert "durable" in str(excinfo.value)

    def test_an_override_with_a_reason_permits_the_lookup_and_records_it(self):
        history, payable = decide(
            CANDLEWOOD, ledger_of(attempt(CANDLEWOOD)),
            material={"reason": DAL.MATERIAL_OPERATOR_OVERRIDE,
                      "detail": "PTF-FOUNDER-001: the recorded website 404s"})
        assert payable
        assert history["decision"] == DAL.ALLOWED_OPERATOR_OVERRIDE
        assert "PTF-FOUNDER-001" in history["material_change_reason"]

    def test_every_material_kind_demands_a_detail(self):
        for kind in DAL.MATERIAL_CHANGES:
            with pytest.raises(DAL.DiscoveryLedgerError):
                decide(CANDLEWOOD, ledger_of(attempt(CANDLEWOOD)),
                       material={"reason": kind, "detail": ""})


class TestSuppressionStaysAccountedForInCoverage:

    def test_the_split_is_a_partition_that_invents_and_drops_nothing(self):
        cohort = [CANDLEWOOD,
                  row("new hotel", "New Hotel", "1 Fresh Road", "46000"),
                  row("another", "Another Inn", "2 Fresh Road", "46000")]
        payable, suppressed = DAL.suppress(cohort, ledger_of(attempt(CANDLEWOOD)),
                                           provider=PROVIDER, method=METHOD,
                                           field_mask=MASK)
        assert len(payable) + len(suppressed) == len(cohort)
        keys = {r["identity_key"] for r in payable + suppressed}
        assert keys == {r["identity_key"] for r in cohort}

    def test_a_suppressed_row_keeps_the_url_that_settled_it(self):
        _payable, suppressed = DAL.suppress([CANDLEWOOD],
                                            ledger_of(attempt(CANDLEWOOD)),
                                            provider=PROVIDER, method=METHOD,
                                            field_mask=MASK)
        assert suppressed[0]["discovery_history"]["prior_website_uri"]
        assert suppressed[0]["settled_because"]

    def test_the_summary_states_the_partition(self):
        cohort = [CANDLEWOOD, row("new hotel", "New Hotel", "1 Fresh Road", "46000")]
        payable, suppressed = DAL.suppress(cohort, ledger_of(attempt(CANDLEWOOD)),
                                           provider=PROVIDER, method=METHOD,
                                           field_mask=MASK)
        report = DAL.summary(payable, suppressed)
        assert report["accounted_for"] == len(cohort)
        assert report["url_already_known"] == 1


class TestTheRecordAndTheStore:

    def test_an_unknown_bind_state_is_refused(self):
        with pytest.raises(DAL.DiscoveryLedgerError):
            attempt(CANDLEWOOD, bind_state="PROBABLY_FINE")

    def test_merging_the_same_run_twice_does_not_double_it(self):
        record = attempt(CANDLEWOOD)
        once = DAL.merge(DAL.new_ledger(), [record])
        twice = DAL.merge(once, [record])
        assert len(twice["attempts"]) == 1

    def test_a_richer_field_mask_is_a_different_question(self):
        """A mask that did not ask for a website could not have returned one."""
        thin = DAL.query_fingerprint(CANDLEWOOD, provider=PROVIDER,
                                     method=METHOD, field_mask=("places.id",))
        rich = DAL.query_fingerprint(CANDLEWOOD, provider=PROVIDER,
                                     method=METHOD, field_mask=MASK)
        assert thin != rich

    def test_the_record_carries_everything_a_later_run_needs(self):
        record = attempt(CANDLEWOOD)
        for field in ("market_id", "work_order", "run_id", "identity_key",
                      "normalized_name", "street", "city", "state",
                      "postal_code", "telephone", "provider",
                      "discovery_method", "query_fingerprint", "field_mask",
                      "attempted_at", "place_id", "website_uri",
                      "national_phone_number", "bind_result", "bind_method",
                      "bind_state", "outcome", "cache_pointer",
                      "paid_requests", "cost_usd_minor"):
            assert field in record, field

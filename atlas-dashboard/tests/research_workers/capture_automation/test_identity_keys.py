"""Capture-time identity gate -- FD-5 stable-key counting.

The runner has always checked identity before touching a policy region. What
these tests lock down is the *evidentiary bar* that check now has to clear:

  * two INDEPENDENT approved stable keys, where independence is by group, so
    two address-derived variants are one key and two property-identifier
    variants are one key;
  * at least one of them proven by an authoritative field-specific source --
    structured metadata, a labelled DOM field, a rendered evidence view, or
    adapter metadata. Unlabelled body text can contribute a key but can never
    be the authoritative one;
  * name, city and page title never count, in any combination.

Every case the founder named is asserted here by name.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib

import pytest

from services.research_workers.capture_automation import identity_keys as IK
from services.research_workers.capture_automation.contracts import (
    DomSnapshot, ObservedIdentity,
)
from services.research_workers.capture_automation.evidence_completeness import (
    FIELD_PROPERTY_PHONE, FIELD_STREET, FieldObservation,
)
from services.research_workers.capture_automation.identity_check import (
    IdentityOutcome, classify_identity, verify_identity,
)

STREET = "1375 North Cassady Avenue"
POSTAL = "43219"
PHONE = "614-475-7551"
CITY = "Columbus"
NAME = "Columbus Airport Marriott"
CODE = "cmham"
URL = "https://www.marriott.com/en-us/hotels/cmham-columbus-airport-marriott/overview/"


def expected(**kw):
    base = dict(street=STREET, postal_code=POSTAL, phone=PHONE,
                property_code="", name=NAME, city=CITY)
    base.update(kw)
    return IK.ExpectedIdentity(**base)


def dom(*, html="", text="", jsonld=(), title="", canonical=""):
    return DomSnapshot(final_url=URL, title=title, canonical_url=canonical,
                       html=html, text=text, jsonld=tuple(jsonld))


def ld(**kw):
    addr = {"@type": "PostalAddress"}
    if "street" in kw:
        addr["streetAddress"] = kw["street"]
    if "postal" in kw:
        addr["postalCode"] = kw["postal"]
    block = {"@type": "Hotel", "name": kw.get("name", NAME), "address": addr}
    if "phone" in kw:
        block["telephone"] = kw["phone"]
    return (block,)


def observed(**kw):
    base = dict(name=NAME, phone="", street="", city="", state="", postal_code="",
                property_code="", sources=("jsonld",))
    base.update(kw)
    return ObservedIdentity(**base)


def assess(d, exp=None, **kw):
    return IK.evaluate(d, exp or expected(), **kw)


# --------------------------------------------------------------------------- #
# The named insufficiency cases.
# --------------------------------------------------------------------------- #

class TestInsufficientCombinations:
    def test_name_plus_city_fails(self):
        """Zero approved keys. The single most important case -- this is what
        source_retrieval's STRONG_MATCH would have accepted."""
        d = dom(text="%s %s welcome" % (NAME, CITY), title=NAME)
        result = assess(d, expected(street="", phone=""))
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert "name, city and page title never establish identity" in result.reason
        assert result.independent_groups == ()

    def test_name_plus_phone_fails(self):
        """One approved key. name never counts."""
        d = dom(jsonld=ld(phone=PHONE), text=NAME)
        result = assess(d, expected(street=""))
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert result.independent_groups == (IK.GROUP_PHONE,)
        assert "FD-5 requires 2" in result.reason

    def test_name_plus_address_fails(self):
        """One approved key."""
        d = dom(jsonld=ld(street=STREET), text=NAME)
        result = assess(d, expected(phone=""))
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert result.independent_groups == (IK.GROUP_ADDRESS,)

    def test_two_address_derived_keys_are_not_independent(self):
        """streetAddress and postalCode+street-number restate one fact."""
        d = dom(jsonld=ld(street=STREET, postal=POSTAL),
                text="%s %s %s" % (NAME, STREET, POSTAL))
        result = assess(d, expected(phone=""))
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert result.independent_groups == (IK.GROUP_ADDRESS,)
        assert len({k.group for k in result.counting_keys}) == 1

    def test_two_unlabeled_body_text_matches_fail(self):
        """Two independent keys, but neither authoritative. A digit run loose
        in prose is a coincidence, not a citation."""
        d = dom(text="Welcome. %s. Call %s today." % (STREET, PHONE))
        result = assess(d)
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert len(result.independent_groups) >= 2
        assert not result.has_authoritative
        assert "none from an authoritative field-specific source" in result.reason

    def test_page_title_alone_is_nothing(self):
        result = assess(dom(title=NAME), expected(street="", phone=""))
        assert result.outcome == IK.IDENTITY_INCOMPLETE


# --------------------------------------------------------------------------- #
# The named passing cases.
# --------------------------------------------------------------------------- #

class TestSufficientCombinations:
    def test_phone_plus_address_passes(self):
        d = dom(jsonld=ld(street=STREET, phone=PHONE))
        result = assess(d)
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert set(result.independent_groups) == {IK.GROUP_ADDRESS, IK.GROUP_PHONE}
        assert result.has_authoritative

    def test_structured_property_id_plus_address_passes(self):
        d = dom(jsonld=ld(street=STREET),
                html='<span itemprop="propertyID">%s</span>' % CODE)
        result = assess(d, expected(phone="", property_code=CODE))
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert set(result.independent_groups) == {IK.GROUP_ADDRESS,
                                                  IK.GROUP_PROPERTY_IDENTIFIER}

    def test_property_identifier_plus_phone_passes(self):
        d = dom(jsonld=ld(phone=PHONE),
                html='<span itemprop="propertyID">%s</span>' % CODE)
        result = assess(d, expected(street="", property_code=CODE))
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert set(result.independent_groups) == {IK.GROUP_PHONE,
                                                  IK.GROUP_PROPERTY_IDENTIFIER}

    def test_one_labeled_dom_key_plus_one_structured_key_passes(self):
        """The founder's mixed case: a labelled DOM field and an independent
        structured field, in the same rendered session."""
        d = dom(jsonld=ld(phone=PHONE),
                html='<address>%s, %s OH %s</address>' % (STREET, CITY, POSTAL))
        result = assess(d)
        assert result.outcome == IK.IDENTITY_CONFIRMED
        bases = {k.basis for k in result.counting_keys}
        assert IK.BASIS_LABELED_DOM in bases and IK.BASIS_STRUCTURED in bases

    def test_two_labeled_dom_keys_pass(self):
        d = dom(html='<address>%s</address><a href="tel:%s">call</a>' % (STREET, PHONE))
        result = assess(d)
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert all(k.basis == IK.BASIS_LABELED_DOM for k in result.counting_keys)

    def test_one_authoritative_plus_one_body_text_key_passes(self):
        """Only ONE key must be authoritative; the second may come from text."""
        d = dom(jsonld=ld(street=STREET), text="Reservations %s" % PHONE)
        result = assess(d)
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert result.has_authoritative

    def test_a_rendered_evidence_view_is_authoritative(self):
        d = dom(text="Call %s" % PHONE)
        views = (FieldObservation(field=FIELD_STREET, text=STREET, visible=True,
                                  in_frame=True, box={"width": 200, "height": 20}),)
        result = assess(d, field_observations=views)
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert any(k.basis == IK.BASIS_EVIDENCE_VIEW for k in result.counting_keys)

    def test_adapter_metadata_is_authoritative(self):
        d = dom(text="Call %s" % PHONE)
        result = assess(d, adapter_metadata={"street": STREET})
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert any(k.basis == IK.BASIS_ADAPTER_METADATA for k in result.counting_keys)


# --------------------------------------------------------------------------- #
# Address agreement: the correction to E-1.
#
# The previous rule was bidirectional substring containment, which scored
# "1100 Main Street" as agreeing with "100 Main Street" -- a DIFFERENT building
# -- and did so at an authoritative basis, so the contradiction never surfaced.
# --------------------------------------------------------------------------- #

class TestAddressAgreement:
    def test_a_different_street_number_is_not_agreement(self):
        assert not IK._addresses_agree("100 Main Street", "1100 Main Street")

    def test_a_different_street_number_produces_identity_failed(self):
        """The behaviour that matters: not merely 'no key', but a CONFLICT."""
        d = dom(jsonld=ld(street="1100 Main Street", phone=PHONE))
        result = assess(d, expected(street="100 Main Street"))
        assert result.outcome == IK.IDENTITY_FAILED
        assert "contradicted" in result.reason
        assert any(c.key == "normalized_street_address" for c in result.conflicts)

    def test_abbreviated_directional_and_type_agree(self):
        assert IK._addresses_agree("7474 N High St", "7474 North High Street")
        assert IK._addresses_agree("7474 North High Street", "7474 N High St")

    def test_unit_and_suite_variation_agrees(self):
        assert IK._addresses_agree("1375 N Cassady Ave Suite 100",
                                   "1375 North Cassady Avenue")
        assert IK._addresses_agree("1375 N Cassady Ave", "1375 N Cassady Ave Ste 210")
        assert IK._addresses_agree("500 Oak Road Unit 4B", "500 Oak Rd")

    def test_punctuation_variation_agrees(self):
        assert IK._addresses_agree("1375 N. Cassady Ave.", "1375 N Cassady Ave")
        assert IK._addresses_agree("100 Main St.", "100 Main Street")

    def test_a_rendered_address_block_with_city_state_zip_agrees(self):
        """An <address> element carries locality the queue's street-only field
        does not. That is not a disagreement."""
        assert IK._addresses_agree("1375 North Cassady Avenue",
                                   "1375 North Cassady Avenue, Columbus OH 43219")

    def test_a_different_street_name_is_not_agreement(self):
        assert not IK._addresses_agree("100 Main Street", "100 Oak Street")

    def test_a_different_street_type_is_not_agreement(self):
        assert not IK._addresses_agree("100 Main Street", "100 Main Avenue")

    def test_conflicting_directionals_are_not_agreement(self):
        assert not IK._addresses_agree("100 N Main St", "100 S Main St")

    def test_an_unparseable_address_is_silence_not_conflict(self):
        """A value with no street number states nothing we can disagree with."""
        d = dom(jsonld=ld(street="Airport Concourse", phone=PHONE))
        result = assess(d, expected(street="100 Main Street"))
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert result.conflicts == ()


# --------------------------------------------------------------------------- #
# Phone matching: the correction to E-2.
# --------------------------------------------------------------------------- #

class TestPhoneMatching:
    def test_unrelated_numbers_cannot_synthesize_the_phone(self):
        """THE regression. Expected 614-475-7551; the page prints $614, 475 and
        7551 in three unrelated sentences and never prints the number. The old
        rule concatenated every digit on the page and matched."""
        text = "Rooms from $614 . Established 475 . Suite 7551 . Free parking."
        d = dom(jsonld=ld(street=STREET), text=text)
        result = assess(d)
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert IK.GROUP_PHONE not in result.independent_groups

    def test_digits_are_not_concatenated_across_lines(self):
        assert IK.phone_runs("Call 614\nthen 475\nthen 7551") == ()

    def test_a_phone_inside_a_longer_digit_run_does_not_count(self):
        assert IK.phone_runs("Reference 99961447575518888") == ()

    @pytest.mark.parametrize("rendered", [
        "+1 614-475-7551", "(614) 475-7551", "614.475.7551", "6144757551",
        "614-475-7551", "Call us at (614) 475-7551 today.",
    ])
    def test_real_phone_renderings_are_still_found(self, rendered):
        assert "6144757551" in IK.phone_runs(rendered)

    def test_a_real_rendered_phone_still_proves_the_key(self):
        d = dom(jsonld=ld(street=STREET), text="Reservations: (614) 475-7551")
        result = assess(d)
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert IK.GROUP_PHONE in result.independent_groups


# --------------------------------------------------------------------------- #
# Body-text boundaries: the correction to E-3.
# --------------------------------------------------------------------------- #

class TestBodyTextBoundaries:
    def test_street_number_must_be_a_standalone_token(self):
        """'12' inside '2012' is a year, not a street number."""
        d = dom(jsonld=ld(phone=PHONE),
                text="Serving guests since 2012 on our domain.")
        result = assess(d, expected(street="12 Main Street"))
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert IK.GROUP_ADDRESS not in result.independent_groups

    def test_street_name_must_not_match_inside_a_word(self):
        """'main' inside 'domain' is not a street name."""
        assert not IK.token_present("main", "visit our domain today")
        assert IK.token_present("main", "on main street")

    def test_street_number_must_not_match_inside_a_longer_number(self):
        assert not IK.token_present("12", "since 2012")
        assert not IK.token_present("100", "1100 units")
        assert IK.token_present("100", "100 main street")

    def test_all_name_tokens_are_required_not_merely_one(self):
        d = dom(jsonld=ld(phone=PHONE),
                text="1375 guests served on Cassady. No street named here.")
        result = assess(d, expected(street="1375 North Oak Cassady Avenue"))
        assert IK.GROUP_ADDRESS not in result.independent_groups

    def test_a_genuine_body_text_address_still_counts_as_a_weak_key(self):
        d = dom(jsonld=ld(phone=PHONE),
                text="Located at 1375 North Cassady Avenue, Columbus.")
        result = assess(d)
        assert IK.GROUP_ADDRESS in result.independent_groups
        assert not any(k.authoritative for k in result.counting_keys
                       if k.group == IK.GROUP_ADDRESS)


# --------------------------------------------------------------------------- #
# Property identifiers: the corrections to E-4, E-5 and E-6.
# --------------------------------------------------------------------------- #

class TestPropertyIdentifierMatching:
    def test_chi_does_not_match_chicago(self):
        """THE regression. A three-letter code inside an ordinary word."""
        d = dom(jsonld=ld(phone=PHONE),
                text="Visit our sister property in Chicago Heights.")
        result = assess(d, expected(street="", property_code="chi"))
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert IK.GROUP_PROPERTY_IDENTIFIER not in result.independent_groups

    def test_a_short_identifier_is_refused_from_body_text_even_standalone(self):
        d = dom(jsonld=ld(phone=PHONE), text="Code chi applies.")
        result = assess(d, expected(street="", property_code="chi"))
        assert IK.GROUP_PROPERTY_IDENTIFIER not in result.independent_groups

    def test_a_long_enough_identifier_must_still_be_a_standalone_token(self):
        d = dom(jsonld=ld(phone=PHONE), text="See cmhamberley for details.")
        result = assess(d, expected(street="", property_code="cmham"))
        assert IK.GROUP_PROPERTY_IDENTIFIER not in result.independent_groups

    def test_a_standalone_long_identifier_counts_from_body_text(self):
        d = dom(jsonld=ld(phone=PHONE), text="Property code cmham applies.")
        result = assess(d, expected(street="", property_code="cmham"))
        assert IK.GROUP_PROPERTY_IDENTIFIER in result.independent_groups

    def test_a_structured_identifier_is_named_official_property_id(self):
        d = dom(jsonld=ld(street=STREET),
                html='<span itemprop="propertyID">%s</span>' % CODE)
        result = assess(d, expected(phone="", property_code=CODE))
        assert any(k.key == "official_property_id" for k in result.counting_keys)

    def test_other_bases_are_named_stable_chain_property_identifier(self):
        """Founder decision 4: the chain identifier is emitted under its own
        name, with its evidence basis preserved."""
        for kwargs, want_basis in (
            (dict(canonical=URL), IK.BASIS_CANONICAL_URL),
            (dict(text="Property code %s applies." % CODE), IK.BASIS_BODY_TEXT),
        ):
            d = dom(jsonld=ld(street=STREET), **kwargs)
            result = assess(d, expected(phone="", property_code=CODE))
            match = [k for k in result.counting_keys
                     if k.group == IK.GROUP_PROPERTY_IDENTIFIER]
            assert match, kwargs
            assert match[0].key == "stable_chain_property_identifier"
            assert match[0].basis == want_basis

    def test_adapter_metadata_identifier_is_the_chain_identifier(self):
        d = dom(jsonld=ld(street=STREET))
        result = assess(d, expected(phone="", property_code=CODE),
                        adapter_metadata={"property_code": CODE})
        match = [k for k in result.counting_keys
                 if k.group == IK.GROUP_PROPERTY_IDENTIFIER]
        assert match[0].key == "stable_chain_property_identifier"
        assert match[0].basis == IK.BASIS_ADAPTER_METADATA


# --------------------------------------------------------------------------- #
# Canonical URL as a weak key: the correction to E-5.
# --------------------------------------------------------------------------- #

class TestCanonicalUrlIsWeak:
    def test_canonical_url_plus_weak_text_stays_incomplete(self):
        """Two independent keys, but the only non-text one is a canonical link.
        Nothing rendered and property-specific proved anything, so this must not
        confirm."""
        d = dom(canonical=URL, text="Reservations (614) 475-7551")
        result = assess(d, expected(street="", property_code=CODE))
        assert set(result.independent_groups) == {IK.GROUP_PHONE,
                                                  IK.GROUP_PROPERTY_IDENTIFIER}
        assert not result.has_authoritative
        assert result.outcome == IK.IDENTITY_INCOMPLETE

    def test_canonical_url_still_counts_toward_the_two_key_total(self):
        """It is a valid independent key -- it just cannot be the authoritative
        one. Paired with a structured address it confirms."""
        d = dom(jsonld=ld(street=STREET), canonical=URL)
        result = assess(d, expected(phone="", property_code=CODE))
        assert result.outcome == IK.IDENTITY_CONFIRMED
        assert set(result.independent_groups) == {IK.GROUP_ADDRESS,
                                                  IK.GROUP_PROPERTY_IDENTIFIER}
        assert result.has_authoritative

    def test_the_requested_url_alone_still_proves_nothing(self):
        d = dom(jsonld=ld(street=STREET))          # code only in final_url
        result = assess(d, expected(phone="", property_code=CODE))
        assert IK.GROUP_PROPERTY_IDENTIFIER not in result.independent_groups


# --------------------------------------------------------------------------- #
# Contradiction and circularity.
# --------------------------------------------------------------------------- #

class TestContradictionAndCircularity:
    def test_a_contradicting_authoritative_phone_fails_outright(self):
        d = dom(jsonld=ld(street=STREET, phone="999-000-1111"))
        result = assess(d)
        assert result.outcome == IK.IDENTITY_FAILED
        assert "contradicted" in result.reason

    def test_a_contradicting_authoritative_address_fails_outright(self):
        d = dom(jsonld=ld(street="12 Elsewhere Road", phone=PHONE))
        result = assess(d)
        assert result.outcome == IK.IDENTITY_FAILED

    def test_a_property_code_only_in_the_requested_url_does_not_count(self):
        """Circular: proving a URL with that same URL. The code must appear in
        page content or adapter metadata."""
        d = dom(jsonld=ld(street=STREET))          # code is only in final_url
        result = assess(d, expected(phone="", property_code=CODE))
        assert result.outcome == IK.IDENTITY_INCOMPLETE
        assert IK.GROUP_PROPERTY_IDENTIFIER not in result.independent_groups

    def test_a_property_code_in_the_pages_own_canonical_link_counts(self):
        d = dom(jsonld=ld(street=STREET), canonical=URL)
        result = assess(d, expected(phone="", property_code=CODE))
        assert result.outcome == IK.IDENTITY_CONFIRMED

    def test_silence_is_not_contradiction(self):
        """A page that simply says nothing is INCOMPLETE, never FAILED."""
        result = assess(dom(text="no identity here at all"))
        assert result.outcome == IK.IDENTITY_INCOMPLETE


# --------------------------------------------------------------------------- #
# Vocabulary and structure.
# --------------------------------------------------------------------------- #

class TestVocabulary:
    def test_the_four_outcomes_exist(self):
        assert IK.IDENTITY_OUTCOMES == {
            "IDENTITY_CONFIRMED", "IDENTITY_FAILED", "IDENTITY_INCOMPLETE",
            "ACCESS_BLOCKED"}

    def test_only_confirmed_may_proceed(self):
        assert IK.MAY_PROCEED == {IK.IDENTITY_CONFIRMED}

    def test_the_approved_key_set_is_what_capture_can_actually_collect(self):
        assert IK.APPROVED_KEYS == {
            "official_property_id", "normalized_street_address",
            "postal_code_plus_street_number", "property_phone",
            "stable_chain_property_identifier"}

    def test_verified_coordinates_is_excluded_rather_than_left_dead(self):
        """Nothing at capture time can produce coordinates -- a DomSnapshot has
        none and a QueueEntry carries no expected lat/lon -- so advertising the
        key would promise evidence this module can never collect. It remains a
        valid key on the discovery/static path, which is untouched."""
        import inspect

        from scripts.pettripfinder.discovery import url_record

        assert "verified_coordinates" not in IK.APPROVED_KEYS
        assert "verified_coordinates" not in IK.KEY_GROUPS
        assert "verified_coordinates" in url_record.STABLE_IDENTITY_KEYS
        assert "KEY_VERIFIED_COORDINATES" not in inspect.getsource(IK)

    def test_every_approved_key_is_reachable(self):
        """No dead approved keys: each one is emitted somewhere in collection."""
        import inspect

        src = inspect.getsource(IK.collect_keys)
        for key in IK.APPROVED_KEYS:
            const = {
                "official_property_id": "KEY_OFFICIAL_PROPERTY_ID",
                "normalized_street_address": "KEY_NORMALIZED_STREET_ADDRESS",
                "postal_code_plus_street_number": "KEY_POSTAL_PLUS_STREET_NUMBER",
                "property_phone": "KEY_PROPERTY_PHONE",
                "stable_chain_property_identifier": "KEY_STABLE_CHAIN_IDENTIFIER",
            }[key]
            assert const in src, "%s is approved but never emitted" % key

    def test_every_approved_key_has_an_independence_group(self):
        assert set(IK.KEY_GROUPS) == set(IK.APPROVED_KEYS)

    def test_the_canonical_url_basis_is_weak_not_authoritative(self):
        """Founder decision 5: it may contribute a key, never the authoritative
        one."""
        assert IK.BASIS_CANONICAL_URL in IK.WEAK_BASES
        assert IK.BASIS_CANONICAL_URL not in IK.AUTHORITATIVE_BASES
        assert IK.BASIS_CANONICAL_URL not in IK.NON_COUNTING_BASES

    def test_name_city_and_title_are_never_keys(self):
        for never in ("name", "city", "page_title"):
            assert never not in IK.APPROVED_KEYS

    def test_body_text_is_never_authoritative(self):
        assert IK.BASIS_BODY_TEXT not in IK.AUTHORITATIVE_BASES

    def test_title_and_url_never_count_at_all(self):
        assert IK.BASIS_PAGE_TITLE in IK.NON_COUNTING_BASES
        assert IK.BASIS_URL in IK.NON_COUNTING_BASES

    def test_address_variants_share_a_group(self):
        assert (IK.KEY_GROUPS["normalized_street_address"]
                == IK.KEY_GROUPS["postal_code_plus_street_number"])

    def test_property_identifier_variants_share_a_group(self):
        assert (IK.KEY_GROUPS["official_property_id"]
                == IK.KEY_GROUPS["stable_chain_property_identifier"])

    def test_minimum_is_two(self):
        assert IK.MINIMUM_INDEPENDENT_KEYS == 2


# --------------------------------------------------------------------------- #
# The four-outcome wrapper, and what it must not disturb.
# --------------------------------------------------------------------------- #

class TestClassifyIdentityWrapper:
    def _entry(self, **kw):
        from services.research_workers.capture_automation.queue import QueueEntry
        base = dict(hotel_id="h", listing_key="k", hotel_name=NAME, brand="marriott",
                    official_url=URL, expected_address=STREET, expected_city=CITY,
                    expected_state="OH", expected_postal_code=POSTAL,
                    expected_phone=PHONE, expected_property_code=CODE)
        base.update(kw)
        return QueueEntry(**base)

    def test_a_search_url_is_access_blocked(self):
        d = DomSnapshot(final_url="https://www.marriott.com/search/findHotels.mi",
                        title=NAME)
        out = classify_identity(d, self._entry(), observed_at="2026-08-03")
        assert out.outcome == IK.ACCESS_BLOCKED
        assert not out.may_proceed

    def test_a_property_code_mismatch_is_identity_failed(self):
        d = DomSnapshot(final_url=URL, title=NAME, jsonld=ld(street=STREET, phone=PHONE))
        out = classify_identity(d, self._entry(expected_property_code="zzzzz"),
                                observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_FAILED

    def test_a_confirmed_page_may_proceed(self):
        d = DomSnapshot(final_url=URL, title=NAME, canonical_url=URL,
                        text="%s %s" % (STREET, PHONE),
                        jsonld=ld(street=STREET, phone=PHONE))
        out = classify_identity(d, self._entry(), observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_CONFIRMED
        assert out.may_proceed

    def test_an_old_style_pass_without_fd5_keys_becomes_incomplete(self):
        """THE behavioural change. A page whose only evidence is a name plus a
        city satisfied source_retrieval's STRONG_MATCH; under FD-5 it is
        IDENTITY_INCOMPLETE and stops."""
        d = DomSnapshot(final_url=URL, title=NAME, canonical_url="",
                        text="%s in %s. Welcome." % (NAME, CITY))
        entry = self._entry(expected_address="", expected_phone="",
                            expected_property_code="")
        out = classify_identity(d, entry, observed_at="2026-08-03")
        assert out.verdict is not None and out.verdict.ok, (
            "precondition: the OLD gate accepts this page")
        assert out.outcome == IK.IDENTITY_INCOMPLETE
        assert not out.may_proceed

    def test_the_wrapper_only_ever_withholds(self):
        """It can never rescue a verdict the existing gate rejected."""
        d = DomSnapshot(final_url="https://www.marriott.com/search/findHotels.mi",
                        jsonld=ld(street=STREET, phone=PHONE))
        out = classify_identity(d, self._entry(), observed_at="2026-08-03")
        assert out.outcome != IK.IDENTITY_CONFIRMED

    def test_the_outcome_serializes_with_its_evidence(self):
        # Page text is required for the EXISTING gate to accept at all; the
        # FD-5 layer runs only on a page that already survived it.
        d = DomSnapshot(final_url=URL, canonical_url=URL, title=NAME,
                        text="%s %s %s" % (NAME, STREET, PHONE),
                        jsonld=ld(street=STREET, phone=PHONE))
        payload = classify_identity(d, self._entry(), observed_at="2026-08-03").to_dict()
        assert payload["outcome"] == IK.IDENTITY_CONFIRMED
        assert payload["keys"]["independent_groups"]
        assert payload["keys"]["has_authoritative_key"] is True


class TestExistingConsumersUnchanged:
    def test_verify_identity_still_returns_the_old_verdict_type(self):
        from services.research_workers.capture_automation.identity_check import (
            IdentityVerdict,
        )
        d = DomSnapshot(final_url=URL, jsonld=ld(street=STREET, phone=PHONE))
        from services.research_workers.capture_automation.queue import QueueEntry
        entry = QueueEntry(hotel_id="h", listing_key="k", hotel_name=NAME,
                           brand="marriott", official_url=URL,
                           expected_address=STREET, expected_phone=PHONE)
        out = verify_identity(d, entry, observed_at="2026-08-03")
        assert isinstance(out, IdentityVerdict)
        assert hasattr(out, "ok")

    def test_operator_capture_is_not_routed_through_the_new_gate(self):
        """Historical operator-capture behaviour is unchanged unless something
        explicitly routes it through classify_identity."""
        src = pathlib.Path(
            "services/research_workers/operator_capture.py").read_text(encoding="utf-8")
        assert "classify_identity" not in src
        assert "identity_keys" not in src

    def test_assess_identity_was_not_retuned(self):
        """The importer and operator_capture depend on its current thresholds."""
        src = pathlib.Path(
            "services/research_workers/source_retrieval.py").read_text(encoding="utf-8")
        assert "IDENTITY_ACCEPTABLE = frozenset({EXACT_MATCH, STRONG_MATCH})" in src


# --------------------------------------------------------------------------- #
# Real corpus.
# --------------------------------------------------------------------------- #

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class TestAgainstTheRealCorpus:
    @pytest.mark.parametrize("name", sorted(
        p.name for p in FIXTURES.glob("*.json")) if FIXTURES.exists() else [])
    def test_every_real_capture_is_judged_without_error(self, name):
        from .conftest import entry_for, load_fixture

        dom_ = DomSnapshot.from_capture_payload(load_fixture(name))
        out = classify_identity(dom_, entry_for(name), observed_at="2026-08-03")
        assert out.outcome in IK.IDENTITY_OUTCOMES
        if out.outcome == IK.IDENTITY_CONFIRMED:
            assert len(out.keys.independent_groups) >= 2
            assert out.keys.has_authoritative


# --------------------------------------------------------------------------- #
# Seed-versus-page DISAGREEMENT, on the real corpus.
#
# The corpus alone cannot prove the gate discriminates: conftest builds each
# QueueEntry's expected_* fields FROM the fixture's own JSON-LD, so the queue
# and the page agree by construction. These cases introduce the disagreement a
# real seed can carry, which is the only condition under which a wrong-property
# confirmation is possible.
# --------------------------------------------------------------------------- #

REAL = "marriott-cmham.json"


def _real_dom(**replace):
    from .conftest import load_fixture

    snap = DomSnapshot.from_capture_payload(load_fixture(REAL))
    return dataclasses.replace(snap, **replace) if replace else snap


class TestSeedVersusPageDisagreement:
    def test_a_street_number_disagreement_fails_on_a_real_page(self):
        """The seed says 11375; the page says 1375. Different building. Under
        the old substring rule '1375 ...' was contained in '11375 ...' and this
        confirmed."""
        from .conftest import entry_for

        entry = entry_for(REAL, expected_address="11375 North Cassady Avenue")
        out = classify_identity(_real_dom(), entry, observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_FAILED
        assert not out.may_proceed

    def test_a_phone_disagreement_fails_on_a_real_page(self):
        from .conftest import entry_for

        entry = entry_for(REAL, expected_phone="614-555-0199")
        out = classify_identity(_real_dom(), entry, observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_FAILED
        assert not out.may_proceed

    def test_a_property_code_substring_of_page_prose_does_not_count(self):
        """'colu' occurs inside 'Columbus' throughout this page."""
        exp = IK.ExpectedIdentity(street="", phone="", property_code="colu",
                                  name="Columbus Airport Marriott", city="Columbus")
        result = IK.evaluate(_real_dom(canonical_url=""), exp)
        assert IK.GROUP_PROPERTY_IDENTIFIER not in result.independent_groups
        assert result.outcome != IK.IDENTITY_CONFIRMED

    def test_canonical_url_plus_weak_text_on_a_real_page_stays_incomplete(self):
        """A real rendered page stripped of structured identity: its canonical
        link and its body text still agree with the seed, and that is still not
        enough."""
        stripped = _real_dom(jsonld=(), html="")
        exp = IK.ExpectedIdentity(street="", phone="614-475-7551",
                                  property_code="cmham", name=NAME, city=CITY)
        result = IK.evaluate(stripped, exp)
        assert set(result.independent_groups) == {IK.GROUP_PHONE,
                                                  IK.GROUP_PROPERTY_IDENTIFIER}
        assert not result.has_authoritative
        assert result.outcome == IK.IDENTITY_INCOMPLETE

    def test_the_unmodified_real_page_still_confirms(self):
        """Guards the four above: they must fail for the disagreement, not
        because the fixture stopped working."""
        from .conftest import entry_for

        out = classify_identity(_real_dom(), entry_for(REAL), observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_CONFIRMED

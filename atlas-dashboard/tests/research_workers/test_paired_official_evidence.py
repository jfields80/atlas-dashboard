"""PTF-WORKERS-007 -- paired official evidence (identity capture + policy capture).

All offline: no network, no browser, no model call, no spend.

The fixtures model the real Marriott shape that motivated this sprint -- a
property page at /en-us/hotels/<code>-<slug>/overview/ that proves identity,
and an expanded card on /search/findHotels.mi that states the policy. The
binding between them is the evidence under test; the operator's say-so is not.
"""

from __future__ import annotations

import pytest

from services.research_workers import operator_capture as OC
from services.research_workers import routing as R
from services.research_workers import source_retrieval as SR

PROPERTY_URL = "https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/"
SEARCH_URL = ("https://www.marriott.com/search/findHotels.mi"
              "?destinationAddress.destination=Columbus&propertyCode=cmhea")

ADDRESS = "4176 Brighton Rose Way"
PHONE = "+1 614-762-9162"
NAME = "Aloft Columbus Easton"

PET_BLOCK = (
    "<h4>Pet Policy</h4><p>Pets Welcome</p>"
    "<p>A signed policy is required at check in</p>"
    "<p>Non-Refundable Pet Fee Per Night: $50.00</p>"
    "<p>Maximum Pet Weight: 40.0lbs</p>"
    "<p>Maximum Number of Pets in Room: 2</p>"
)

PROPERTY_HTML = """<html><head><title>%s | Modern Hotel</title>
<link rel="canonical" href="%s"></head><body>
<h1>%s</h1><p>%s, Columbus, Ohio, USA, 43219</p><p>Tel: %s</p>
<h3>HOTEL INFORMATION</h3><p>Check-in: 3:00 pm Check-out: 12:00 pm</p>
<p>Front Desk Staffed</p>
<p>A stylish boutique hotel in the Urban District at Easton Town Center. %s</p>
</body></html>""" % (NAME, PROPERTY_URL, NAME, ADDRESS, PHONE, "Amenity copy. " * 40)


def _card(name=NAME, address=ADDRESS, phone=PHONE, pets=True):
    """One expanded result card: identity then policy, contiguous."""
    policy = ("<h4>Pet Policy</h4><p>A signed policy is required at check in</p>"
              "<p>Non-refundable fee: 50 Per Night</p>" if pets else "")
    return ("<div class='card'><h3>%s</h3>"
            "<p>Location %s Columbus, Ohio, USA, 43219</p>"
            "<p>Telephone: %s</p>"
            "<h4>Property Information</h4><p>CHECK IN: 03:00 PM</p>"
            "%s"
            "<h4>Amenities</h4><p>Pet friendly Pool Fitness center</p></div>"
            % (name, address, phone, policy))


def _other_results(n=35):
    return "".join(
        "<div><a href='/en-us/hotels/cmh%02d-other-%d/overview/'>Other Hotel %d</a>"
        "<p>A Columbus hotel description number %d.</p></div>" % (i, i, i, i)
        for i in range(n))


def _search_html(card=None, extras=35):
    return ("<html><head><title>Where Can We Take You? | Marriott Bonvoy</title></head>"
            "<body><h1>1 - 36 of 36 Results</h1>%s%s</body></html>"
            % (card if card is not None else _card(), _other_results(extras)))


def _job(**over):
    base = dict(
        assignment_id="attest-aloft",
        listing_key="aloft columbus easton", listing_name=NAME,
        expected_address=ADDRESS, expected_city="Columbus", expected_state="OH",
        expected_postal_code="43219", expected_phone=PHONE,
        official_url=PROPERTY_URL,
        failure_reason="blocked_source", retrieval_status="ACCESS_BLOCKED")
    base.update(over)
    return OC.CaptureJob(**base)


def _payload(url, html, at="2026-07-29T11:06:28Z", **over):
    base = dict(schema=OC.CAPTURE_SCHEMA, captured_at=at, final_url=url,
                title="capture", html=html, text="", extension_version="1.0.0")
    base.update(over)
    return base


def _identity_payload(at="2026-07-29T11:06:28Z", **over):
    return _payload(PROPERTY_URL, PROPERTY_HTML, at=at, **over)


def _policy_payload(card=None, at="2026-07-29T11:08:02Z", url=SEARCH_URL, **over):
    return _payload(url, _search_html(card), at=at, **over)


def _pair(identity=None, policy=None, job=None):
    return OC.ingest_paired_capture(
        identity_payload=identity or _identity_payload(),
        policy_payload=policy or _policy_payload(),
        job=job or _job(), observed_at="2026-07-29")


# --------------------------------------------------------------------------- #
# 1. URL shape -- the guard that closes the pre-existing hole.
# --------------------------------------------------------------------------- #

class TestUrlShape:
    @pytest.mark.parametrize("url,expected", [
        (PROPERTY_URL, SR.URL_SHAPE_PROPERTY),
        (SEARCH_URL, SR.URL_SHAPE_SEARCH),
        ("https://www.marriott.com/search/findHotels.mi", SR.URL_SHAPE_SEARCH),
        ("https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/hotel-info/",
         SR.URL_SHAPE_PROPERTY),
        ("https://www.redroof.com/why-red-roof/pet-policy", SR.URL_SHAPE_BRAND),
        ("https://www.wyndhamhotels.com/laquinta/about-us/pet-friendly-hotels",
         SR.URL_SHAPE_BRAND),
        ("https://example.invalid/", SR.URL_SHAPE_UNKNOWN),
    ])
    def test_classification(self, url, expected):
        assert SR.classify_url_shape(url) == expected

    def test_query_driven_url_is_search_even_without_search_path(self):
        assert SR.classify_url_shape(
            "https://brand.invalid/hotels/list?checkin=2026-07-29") == SR.URL_SHAPE_SEARCH

    def test_search_page_refused_on_the_single_capture_path(self):
        """The defect this sprint found: a search page carrying one hotel's
        name, address and phone was accepted as a PROPERTY policy source, and
        the search URL became the cited official evidence."""
        out = OC.ingest_capture(_policy_payload(), _job(), observed_at="2026-07-29")
        assert not out.accepted
        assert out.source_role == OC.SOURCE_ROLE_SEARCH_SURFACE
        assert out.policy_applicable is False
        assert "search_results_page" in out.warnings

    def test_property_page_still_accepted_on_the_single_capture_path(self):
        out = OC.ingest_capture(_identity_payload(), _job(), observed_at="2026-07-29")
        assert out.accepted
        assert out.source_role == OC.SOURCE_ROLE_PROPERTY


# --------------------------------------------------------------------------- #
# 1b. Cross-brand property-code extraction (PTF-CAPTURE-002A).
#
# Both defects below were found by running the parser over real captures, not
# by its tests -- so these pin the real URL shapes of all three brands.
# --------------------------------------------------------------------------- #

class TestPropertyCodeExtraction:
    @pytest.mark.parametrize("url,expected", [
        # Marriott -- code leads the slug, two-part locale segment first.
        ("https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/",
         "cmhea"),
        ("https://www.marriott.com/en-us/hotels/cmhta-towneplace-suites-columbus-"
         "airport-gahanna/overview/", "cmhta"),
        # Hilton -- previously returned "hotel", picked up from /hotel-info/.
        ("https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/hotel-info/",
         "cmhchhf"),
        ("https://www.hilton.com/en/hotels/cmhaphx-hampton-suites-columbus-airport/",
         "cmhaphx"),
        # IHG -- bare segment before /hoteldetail; previously returned "".
        ("https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail",
         "cmhtc"),
        ("https://www.ihg.com/holidayinn/hotels/us/en/columbus/cmhdt/hoteldetail",
         "cmhdt"),
    ])
    def test_recognised_brand_shapes(self, url, expected):
        assert SR.extract_property_code_from_url(url) == expected

    @pytest.mark.parametrize("url", [
        "https://www.marriott.com/search/findHotels.mi?destinationAddress.destination=x",
        "https://www.hilton.com/en/locations/usa/ohio/columbus/",
        "https://www.redroof.com/why-red-roof/pet-policy",
        "https://www.marriott.com/hotels/travel/",
        "https://www.marriott.com/en-us/hotels/",
        "https://example.invalid/",
        "not even a url",
        "",
    ])
    def test_fails_closed_on_generic_and_malformed(self, url):
        """A guessed code that matches the wrong hotel is worse than no code."""
        assert SR.extract_property_code_from_url(url) == ""

    def test_never_returns_a_generic_path_word(self):
        for url in ("https://www.hilton.com/en/hotels/cmhchhf-x/hotel-info/",
                    "https://brand.invalid/hotels/overview/rooms/"):
            assert SR.extract_property_code_from_url(url) not in (
                "hotel", "hotels", "overview", "rooms", "hotel-info")

    def test_known_code_matches_only_on_a_segment_boundary(self):
        """The collision that made this a correctness bug, not a tidiness one:
        Marriott's 'cmhap' is a prefix of Hilton's 'cmhaphx'. A bare substring
        match silently identified one hotel as the other."""
        hilton = "https://www.hilton.com/en/hotels/cmhaphx-hampton-columbus-airport/"
        # The Marriott code must NOT be claimed for this Hilton property. It no
        # longer matches, so the parser falls through and reports the code the
        # URL actually carries.
        assert SR.extract_property_code_from_url(hilton, known_codes=["cmhap"]) != "cmhap"
        assert SR.extract_property_code_from_url(hilton, known_codes=["cmhap"]) == "cmhaphx"
        assert SR.extract_property_code_from_url(hilton, known_codes=["cmhaphx"]) == "cmhaphx"

    def test_prefix_collision_across_two_real_seed_codes(self):
        """Both codes are real: cmhap (Courtyard Columbus Airport, Marriott)
        and cmhaphx (Hampton Inn Columbus Airport, Hilton)."""
        marriott = "https://www.marriott.com/en-us/hotels/cmhap-courtyard-columbus-airport/"
        assert SR.extract_property_code_from_url(marriott) == "cmhap"
        hilton = "https://www.hilton.com/en/hotels/cmhaphx-hampton-columbus-airport/"
        assert SR.extract_property_code_from_url(hilton) == "cmhaphx"

    def test_known_code_wins_when_it_matches(self):
        url = "https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/"
        assert SR.extract_property_code_from_url(url, known_codes=["cmhea"]) == "cmhea"

    def test_unknown_known_code_falls_back_to_parsing(self):
        url = "https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/"
        assert SR.extract_property_code_from_url(url, known_codes=["zzzz"]) == "cmhea"

    def test_paired_binding_still_confirms_the_marriott_code(self):
        """The consumer that motivated the fix keeps working."""
        _, paired, _ = _pair()
        assert paired.property_code == "cmhea"
        assert "property_code" in paired.matched_signals


# --------------------------------------------------------------------------- #
# 2. The valid Aloft package.
# --------------------------------------------------------------------------- #

class TestValidPair:
    def test_accepted_with_all_four_signals(self):
        out, paired, failures = _pair()
        assert failures == ()
        assert out.accepted
        assert paired is not None
        assert set(paired.matched_signals) == set(OC.REQUIRED_BINDING_SIGNALS)

    def test_role_is_paired_not_property(self):
        """A borrowed identity stays visible in every artifact."""
        out, _, _ = _pair()
        assert out.source_role == OC.SOURCE_ROLE_PAIRED_POLICY
        assert out.source_role != OC.SOURCE_ROLE_PROPERTY

    def test_cites_the_property_url_never_the_search_url(self):
        out, paired, _ = _pair()
        assert out.source_document.source_url == PROPERTY_URL
        assert "findHotels" not in out.source_document.source_url
        assert paired.policy_capture_url == SEARCH_URL

    def test_attested_content_is_the_policy_text(self):
        out, _, _ = _pair()
        assert "signed policy is required at check in" in out.source_document.content_text

    def test_property_code_recorded(self):
        _, paired, _ = _pair()
        assert paired.property_code == "cmhea"

    def test_binding_note_explains_the_evidence(self):
        _, paired, _ = _pair()
        for fragment in ("bound to the property identity", "Binding signals",
                         "single expanded card"):
            assert fragment in paired.binding_note

    def test_card_span_and_gap_recorded(self):
        _, paired, _ = _pair()
        assert 0 < paired.card_span_chars <= OC.MAX_CARD_SPAN_CHARS
        assert paired.capture_gap_seconds == 94


# --------------------------------------------------------------------------- #
# 3. Fail-closed binding.
# --------------------------------------------------------------------------- #

class TestBindingFailsClosed:
    def test_mismatched_address(self):
        _, paired, failures = _pair(policy=_policy_payload(_card(address="99 Wrong St")))
        assert paired is None
        assert "address_not_matched" in failures

    def test_mismatched_phone(self):
        _, paired, failures = _pair(policy=_policy_payload(_card(phone="+1 614-000-0000")))
        assert paired is None
        assert "phone_not_matched" in failures

    def test_wrong_hotel_card(self):
        """A Residence Inn card paired with Aloft identity fails on every
        identity signal at once, not just the first one found."""
        wrong = _card(name="Residence Inn by Marriott Columbus Easton",
                      address="3999 Easton Loop West", phone="+1 614-414-1000")
        _, paired, failures = _pair(policy=_policy_payload(wrong))
        assert paired is None
        for slug in ("name_not_matched", "address_not_matched", "phone_not_matched"):
            assert slug in failures

    def test_missing_property_specific_capture_a(self):
        """A search page cannot lend an identity it never had."""
        _, paired, failures = _pair(identity=_policy_payload())
        assert paired is None
        assert any("identity_capture_not_accepted" in f for f in failures)

    def test_generic_search_capture_b_without_binding_context(self):
        """Results list, no card expanded: no identity, no policy, no pairing."""
        _, paired, failures = _pair(policy=_policy_payload(card=""))
        assert paired is None
        assert failures

    def test_two_expanded_cards_is_ambiguous(self):
        two = _card() + _card(name="Courtyard by Marriott Columbus Easton",
                              address="3900 Morse Crossing", phone="+1 614-414-2000")
        _, paired, failures = _pair(policy=_policy_payload(two))
        assert paired is None
        assert "multiple_expanded_cards" in failures

    def test_policy_capture_without_pet_text(self):
        _, paired, failures = _pair(policy=_policy_payload(_card(pets=False)))
        assert paired is None
        assert "policy_capture_has_no_policy_text" in failures

    def test_duplicate_capture_is_not_corroboration(self):
        _, paired, failures = _pair(policy=_identity_payload(at="2026-07-29T11:08:02Z"))
        assert paired is None
        assert failures

    def test_cross_domain_pair_refused(self):
        hilton = _payload(
            "https://www.hilton.com/en/hotels/cmhchhf-x/hotel-info/",
            _search_html(), at="2026-07-29T11:08:02Z")
        _, paired, failures = _pair(policy=hilton)
        assert paired is None
        assert failures

    def test_captures_too_far_apart(self):
        _, paired, failures = _pair(
            policy=_policy_payload(at="2026-07-29T14:30:00Z"))
        assert paired is None
        assert "captures_not_same_session" in failures

    def test_all_failures_reported_not_just_the_first(self):
        wrong = _card(name="Wrong Hotel", address="1 Nowhere", phone="+1 000-000-0000")
        _, paired, failures = _pair(
            policy=_policy_payload(wrong, at="2026-07-29T20:00:00Z"))
        assert paired is None
        assert len(failures) >= 4

    def test_every_failure_slug_is_declared(self):
        """A slug that is not in PAIRING_CONDITIONS is one no operator doc
        explains, so the vocabulary must stay closed."""
        wrong = _card(name="Wrong", address="1 Nowhere", phone="+1 000-000-0000",
                      pets=False)
        _, failures = OC.bind_paired_captures(
            identity=OC.ingest_capture(_identity_payload(), _job(),
                                       observed_at="2026-07-29"),
            policy_payload=_policy_payload(wrong), job=_job(),
            identity_captured_at="2026-07-29T11:06:28Z",
            policy_captured_at="2026-07-29T11:08:02Z")
        assert set(failures) <= set(OC.PAIRING_CONDITIONS)


# --------------------------------------------------------------------------- #
# 4. Attestation gate P and review-state behaviour.
# --------------------------------------------------------------------------- #

class MemoryCas:
    def __init__(self):
        self.blobs = {}

    def put_bytes(self, data: bytes) -> str:
        import hashlib
        h = hashlib.sha256(data).hexdigest()
        self.blobs[h] = data
        return h


def _affirmation():
    return OC.OperatorAffirmation(
        operator_id="jfields80", attested_at="2026-07-29T11:10:00-04:00",
        address_confirmed=True, address_observed=ADDRESS,
        phone_confirmed=True, phone_observed=PHONE)


def _failure_record():
    return OC.AutomatedFailure(status="ACCESS_BLOCKED", reason="blocked_source",
                               artifact_path="data/worker_runs/x.json")


def _shots(n=1):
    cas = MemoryCas()
    return [OC.store_screenshot(cas, b"\x89PNG shot %d" % i, width=1920, height=919)
            for i in range(n)]


def _build(paired=None, ingestion=None, job=None):
    return OC.build_attestation(
        ingestion=ingestion, job=job or _job(), affirmation=_affirmation(),
        automated_failure=_failure_record(), screenshots=_shots(),
        observed_at="2026-07-29", observed_timezone="America/New_York",
        paired_evidence=paired)


class TestGateP:
    def test_paired_attestation_builds(self):
        out, paired, _ = _pair()
        att = _build(paired=paired, ingestion=out)
        assert att.paired_evidence is not None
        assert att.official_url == PROPERTY_URL

    def test_record_cites_both_captures(self):
        out, paired, _ = _pair()
        d = _build(paired=paired, ingestion=out).to_dict()
        pe = d["paired_evidence"]
        assert pe["identity_capture_url"] == PROPERTY_URL
        assert pe["policy_capture_url"] == SEARCH_URL
        assert pe["identity_text_hash"] and pe["policy_text_hash"]
        assert pe["binding_note"]

    def test_paired_evidence_is_inside_the_hash(self):
        """Hash-bound: altering the recorded binding changes the identity of
        the attestation, so an approval cannot survive a swapped capture."""
        out, paired, _ = _pair()
        a = _build(paired=paired, ingestion=out)
        import dataclasses
        tampered = dataclasses.replace(paired, policy_text_hash="0" * 64)
        b = _build(paired=tampered, ingestion=out)
        assert a.attestation_hash() != b.attestation_hash()

    def test_paired_role_without_evidence_is_refused(self):
        out, _, _ = _pair()
        with pytest.raises(OC.AttestationError, match="gateP"):
            _build(paired=None, ingestion=out)

    def test_evidence_on_a_non_paired_capture_is_refused(self):
        single = OC.ingest_capture(_identity_payload(), _job(), observed_at="2026-07-29")
        _, paired, _ = _pair()
        with pytest.raises(OC.AttestationError, match="gateP"):
            _build(paired=paired, ingestion=single)

    def test_three_of_four_signals_is_refused(self):
        out, paired, _ = _pair()
        import dataclasses
        weak = dataclasses.replace(paired, matched_signals=("name_exact", "address_exact",
                                                            "phone_exact"))
        with pytest.raises(OC.AttestationError, match="four strong signals"):
            _build(paired=weak, ingestion=out)

    def test_never_publishable_until_approved(self):
        out, paired, _ = _pair()
        att = _build(paired=paired, ingestion=out)
        assert att.approval.state == OC.APPROVAL_PENDING
        assert att.publishable is False


class TestReviewRouting:
    def test_reason_code_routes_review(self):
        assert R.PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW in R.REVIEW_REASONS
        assert R.PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW not in R.READY_REASONS

    def test_paired_reason_is_never_waivable_by_the_fee_waiver(self):
        from scripts.pettripfinder import prod003_approvals as PA
        assert R.PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW not in PA.WAIVABLE_REASON_CODES

    def test_fee_reason_is_never_waivable_by_the_paired_waiver(self):
        from scripts.pettripfinder import prod003_approvals as PA
        assert "STRUCTURED_FEE_REQUIRED" not in PA.PAIRED_WAIVABLE_REASON_CODES


# --------------------------------------------------------------------------- #
# 5. The single-capture path is unchanged.
# --------------------------------------------------------------------------- #

class TestSingleCapturePathUnchanged:
    def test_single_capture_attestation_has_no_paired_key(self):
        """Byte-level backward compatibility: a 1.0-shaped record must not
        gain a key, or every previously-issued attestation hash would change."""
        single = OC.ingest_capture(_identity_payload(), _job(), observed_at="2026-07-29")
        att = _build(paired=None, ingestion=single)
        assert "paired_evidence" not in att.attested_content()
        assert att.paired_evidence is None

    def test_single_capture_hash_is_stable_across_the_feature(self):
        single = OC.ingest_capture(_identity_payload(), _job(), observed_at="2026-07-29")
        a = _build(paired=None, ingestion=single)
        b = _build(paired=None, ingestion=single)
        assert a.attestation_hash() == b.attestation_hash()
        assert a.to_dict() == b.to_dict()

    def test_single_capture_still_cites_its_own_url(self):
        single = OC.ingest_capture(_identity_payload(), _job(), observed_at="2026-07-29")
        assert _build(paired=None, ingestion=single).official_url == PROPERTY_URL

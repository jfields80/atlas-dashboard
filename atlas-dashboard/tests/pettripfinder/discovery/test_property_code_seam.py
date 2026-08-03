"""Pre-batch hardening: the seam populates expected_property_code.

The 10-candidate pilot confirmed 10/10 on address + phone alone, so this adds
no coverage. It adds **detection strength**: a silent redirect to a SIBLING
property publishes its own valid address and phone, so both existing keys would
agree with the wrong hotel. A mismatched property code is the only signal that
turns that into IDENTITY_FAILED rather than a confident confirmation of the
wrong property.

The rules these tests hold in place:

  * never infer a code where none exists -- Wyndham and other codeless shapes
    stay empty and keep confirming on address + phone;
  * a matching code is a THIRD independent key, not a replacement for either
    existing one;
  * a mismatched code FAILS identity outright -- it is a contradiction, not a
    shortfall;
  * URL parsing must not lift a code out of unrelated path text.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord
from scripts.pettripfinder.discovery.queue_seam import (
    PROJECTED_PENDING_IDENTITY, project_candidate,
)
from services.research_workers.capture_automation import identity_keys as IK
from services.research_workers.capture_automation.adapters import known_brands
from services.research_workers.capture_automation.contracts import DomSnapshot
from services.research_workers.capture_automation.identity_check import classify_identity
from services.research_workers.capture_automation.queue import validate_entry
from services.research_workers.source_retrieval import extract_property_code_from_url

STREET = "1375 North Cassady Avenue"
POSTAL = "43219"
PHONE = "614-475-7551"
NAME = "AC Hotel Columbus Dublin"

MARRIOTT_URL = "https://www.marriott.com/en-us/hotels/cmhac-ac-hotel-columbus-dublin/overview/"
SIBLING_URL = "https://www.marriott.com/en-us/hotels/cmhaw-aloft-columbus-westerville/overview/"
WYNDHAM_URL = ("https://www.wyndhamhotels.com/days-inn/columbus-ohio/"
               "days-inn-columbus-worthington/overview")


def _candidate(**kw):
    rec = DiscoveryRecord(
        provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="gp1",
        canonical_category=C.CATEGORY_HOTEL, name=NAME, normalized_name=NAME.lower(),
        address_line=STREET, city="Dublin", state="OH", postal_code=POSTAL,
        phone=PHONE, observed_at="2026-08-03", source_query_id="q1")
    base = dict(candidate_id="dc_ac", source_records=(rec,), name=NAME,
                normalized_name=rec.normalized_name, address_line=STREET,
                city="Dublin", state="OH", postal_code=POSTAL,
                provider_ids=((rec.provider, rec.provider_record_id),),
                market_id="columbus-oh", review_state=C.REVIEW_STATE_SINGLE_SOURCE)
    base.update(kw)
    return DiscoveryCandidate(**base)


def _project(url=MARRIOTT_URL, **kw):
    base = dict(resolution_outcome=C.RESOLUTION_READY_FOR_PET_POLICY_IMPORT,
                resolved_url=url, url_identity_never_validated=True,
                url_revalidation_blocked=True, run_context_ref="run-1")
    base.update(kw)
    return project_candidate(_candidate(), **base)


def _ld(street=STREET, postal=POSTAL, phone=PHONE, name=NAME):
    addr = {"@type": "PostalAddress", "streetAddress": street, "postalCode": postal}
    return ({"@type": "Hotel", "name": name, "telephone": phone, "address": addr},)


def _dom(final_url=MARRIOTT_URL, **kw):
    return DomSnapshot(final_url=final_url, title=NAME, canonical_url=final_url,
                       text="%s %s %s" % (NAME, STREET, PHONE),
                       jsonld=kw.pop("jsonld", _ld()), **kw)


def _entry(url=MARRIOTT_URL):
    result = _project(url=url)
    assert result.outcome == PROJECTED_PENDING_IDENTITY, result.reason
    return result.entry


# --------------------------------------------------------------------------- #
# Seam population.
# --------------------------------------------------------------------------- #

class TestSeamPopulatesTheCode:
    def test_a_marriott_url_yields_its_code(self):
        assert _entry().expected_property_code == "cmhac"

    def test_an_ihg_url_yields_its_code(self):
        url = "https://www.ihg.com/avidhotels/hotels/us/en/hilliard/cmhav/hoteldetail"
        assert _entry(url).expected_property_code == "cmhav"

    def test_a_hilton_url_yields_its_code(self):
        url = "https://www.hilton.com/en/hotels/cmhcees-embassy-suites-columbus/"
        assert _entry(url).expected_property_code == "cmhcees"

    def test_the_seam_uses_the_same_extractor_as_the_seed_path(self):
        """One definition of 'property code'. A second would let the two paths
        disagree about the same URL."""
        e = _entry()
        assert e.expected_property_code == extract_property_code_from_url(MARRIOTT_URL)


class TestNothingIsInferred:
    def test_wyndham_stays_empty_and_still_projects(self):
        """Codeless is a SUPPORTED shape, not a defect."""
        result = _project(url=WYNDHAM_URL)
        assert result.outcome == PROJECTED_PENDING_IDENTITY
        assert result.entry.expected_property_code == ""

    def test_url_parsing_cannot_lift_a_code_from_unrelated_path_text(self):
        """Words that merely look code-shaped must not become a property code.
        A guessed code that matches the wrong hotel is worse than none."""
        for url in (
            "https://www.example-hotel.test/rooms/deluxe/overview",
            "https://www.example-hotel.test/about/contact",
            "https://www.example-hotel.test/en-us/booking/reserve/",
            "https://www.example-hotel.test/",
        ):
            assert extract_property_code_from_url(url) == "", url

    def test_a_generic_slug_after_hotels_is_not_treated_as_a_code(self):
        """Reserved words following /hotels/ are refused outright -- they are
        the shape most likely to be mistaken for a code."""
        for url in ("https://www.marriott.com/en-us/hotels/overview/",
                    "https://www.marriott.com/en-us/hotels/",
                    "https://brand.test/hotels/",
                    "https://brand.test/hotels/reservations/"):
            assert extract_property_code_from_url(url) == "", url


# --------------------------------------------------------------------------- #
# Identity consequences.
# --------------------------------------------------------------------------- #

class TestIdentityConsequences:
    def test_a_matching_code_confirms_and_adds_a_third_key(self):
        entry = _entry()
        out = classify_identity(_dom(), entry, observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_CONFIRMED
        assert set(out.keys.independent_groups) == {
            IK.GROUP_ADDRESS, IK.GROUP_PHONE, IK.GROUP_PROPERTY_IDENTIFIER}

    def test_a_mismatched_code_fails_identity(self):
        """A contradiction, not a shortfall -- IDENTITY_FAILED, never
        IDENTITY_INCOMPLETE."""
        entry = _entry()
        out = classify_identity(_dom(final_url=SIBLING_URL), entry,
                                observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_FAILED
        assert not out.may_proceed

    def test_a_sibling_redirect_with_a_conflicting_code_fails_closed(self):
        """THE case this change exists for. The sibling publishes its OWN valid
        address and phone, so both original keys agree with the wrong hotel and
        would have confirmed. Only the code catches it."""
        sibling_street = "1002 Some Other Road"
        sibling_phone = "614-000-9999"
        entry = _entry()
        dom = DomSnapshot(
            final_url=SIBLING_URL, title="Aloft Columbus Westerville",
            canonical_url=SIBLING_URL,
            text="Aloft Columbus Westerville %s %s" % (sibling_street, sibling_phone),
            jsonld=_ld(street=sibling_street, phone=sibling_phone,
                       name="Aloft Columbus Westerville"))
        out = classify_identity(dom, entry, observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_FAILED
        assert not out.may_proceed

    def test_a_missing_code_does_not_block_address_plus_phone(self):
        """The pilot's measured baseline must survive unchanged."""
        entry = _entry(WYNDHAM_URL)
        assert entry.expected_property_code == ""
        out = classify_identity(_dom(final_url=WYNDHAM_URL), entry,
                                observed_at="2026-08-03")
        assert out.outcome == IK.IDENTITY_CONFIRMED
        assert set(out.keys.independent_groups) == {IK.GROUP_ADDRESS, IK.GROUP_PHONE}

    def test_wyndham_remains_supported_without_a_code(self):
        entry = _entry(WYNDHAM_URL)
        out = classify_identity(_dom(final_url=WYNDHAM_URL), entry,
                                observed_at="2026-08-03")
        assert out.may_proceed

    def test_a_code_alone_never_confirms(self):
        """The code is a third key, not a replacement. Address+phone
        requirements are unchanged."""
        entry = _entry()
        dom = DomSnapshot(final_url=MARRIOTT_URL, title=NAME, canonical_url=MARRIOTT_URL,
                          text=NAME, jsonld=({"@type": "Hotel", "name": NAME},))
        out = classify_identity(dom, entry, observed_at="2026-08-03")
        assert out.outcome != IK.IDENTITY_CONFIRMED

    def test_evidence_basis_and_provenance_are_preserved(self):
        entry = _entry()
        out = classify_identity(_dom(), entry, observed_at="2026-08-03")
        assert out.keys.has_authoritative
        assert all(k.basis for k in out.keys.counting_keys)
        assert entry.discovery_provenance_refs
        assert entry.candidate_id == "dc_ac"


# --------------------------------------------------------------------------- #
# The real corpus.
# --------------------------------------------------------------------------- #

PILOT_DIR = pathlib.Path(
    r"C:\Atlas\atlas-dashboard\data\worker_runs\pettripfinder\pilot_10\captures")


@pytest.mark.skipif(not PILOT_DIR.exists(), reason="pilot corpus is gitignored")
class TestAgainstThePilotCaptures:
    def test_every_captured_page_still_confirms(self):
        """The hardening must not cost a single confirmation the pilot won."""
        queue = json.load(open(
            r"C:\Atlas\atlas-dashboard\data\worker_runs\pettripfinder"
            r"\capture_batches\pilot-10-queue.json", encoding="utf-8"))
        payloads = [json.load(open(p, encoding="utf-8"))
                    for p in sorted(PILOT_DIR.glob("*.json"))]
        checked = 0
        for i, raw in enumerate(queue["hotels"]):
            raw = dict(raw)
            raw["expected_property_code"] = extract_property_code_from_url(
                raw["official_url"])
            entry, _ = validate_entry(raw, i, known_brands=known_brands())
            match = [d for d in payloads
                     if d.get("requested_url", "").split("?")[0]
                     == entry.official_url.split("?")[0]]
            if not match:
                continue
            out = classify_identity(DomSnapshot.from_capture_payload(match[0]),
                                    entry, observed_at="2026-08-03")
            assert out.outcome == IK.IDENTITY_CONFIRMED, entry.hotel_id
            checked += 1
        assert checked >= 9, "expected the 9 captured pilot pages"

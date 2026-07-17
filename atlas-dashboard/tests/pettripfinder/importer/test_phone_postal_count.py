"""AES-DATA-001 -- live-candidate defect repairs (mission A/B/C): phone-role
classification, postal derivation from a supported address, and co-stated
pet-count/weight extraction. No network."""

from __future__ import annotations

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext

_URL = "https://www.druryhotels.com/locations/columbus-oh/drury-inn-and-suites-columbus-dublin"

_JSONLD = (
    '<script type="application/ld+json">{"@type":"Hotel",'
    '"name":"Drury Inn & Suites Columbus Dublin",'
    '"url":"%s",'
    '"address":{"@type":"PostalAddress",'
    '"streetAddress":"6170 Parkcenter Circle, Dublin, OH 43017",'
    '"addressLocality":"Dublin","addressRegion":"OH"}}</script>' % _URL
)


def _run(body_html, facts, tmp_path, jsonld=_JSONLD):
    html = "<!doctype html><html><head><title>Drury</title>%s</head><body>%s</body></html>" % (
        jsonld, body_html)
    fetcher = StaticPageFetcher()
    fetcher.add_html(_URL, html)
    extractor = StaticFactExtractor({"facts": facts})
    cas = ArtifactStoreRepository(tmp_path / "cas")
    ctx = ImportContext(category="hotels", expected_city="Dublin", expected_state="OH")
    return run_import(_URL, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-16", created_at="1970-01-01T00:00:00")


# --------------------------------------------------------------------------- #
# A. Phone role classification.
# --------------------------------------------------------------------------- #

class TestPhoneRoleClassification:
    def test_property_signal(self):
        assert N.classify_phone_role("614-798-8802", "P: 614-798-8802") == N.PHONE_ROLE_PROPERTY
        assert N.classify_phone_role("614-798-8802", "Phone: 614-798-8802") == N.PHONE_ROLE_PROPERTY

    def test_toll_free_reservation(self):
        assert N.classify_phone_role("800-378-7946", "800-DRURYINN (800-378-7946)") \
            == N.PHONE_ROLE_RESERVATION
        assert N.classify_phone_role("888-123-4567", "Reservations: 888-123-4567") \
            == N.PHONE_ROLE_RESERVATION

    def test_brand_central_booking(self):
        assert N.classify_phone_role("800-111-2222", "brand central booking 800-111-2222") \
            == N.PHONE_ROLE_BRAND

    def test_unknown_when_no_signal(self):
        assert N.classify_phone_role("614-555-0000", "614-555-0000") == N.PHONE_ROLE_UNKNOWN


class TestPhoneResolutionPipeline:
    def test_property_preferred_over_reservation(self, tmp_path):
        body = ("<p>Reservations: 800-DRURYINN (800-378-7946)</p><p>P: 614-798-8802</p>"
                "<p>Dogs welcome.</p>")
        c = _run(body, [
            {"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"},
            {"field": "phone", "value": "614-798-8802", "quote": "P: 614-798-8802"},
            {"field": "phone", "value": "800-378-7946", "quote": "800-DRURYINN (800-378-7946)"},
        ], tmp_path)
        assert dict(c.proposed_fields)["phone"] == "614-798-8802"

    def test_distinct_roles_do_not_conflict(self, tmp_path):
        body = ("<p>Reservations: 800-DRURYINN (800-378-7946)</p><p>P: 614-798-8802</p>"
                "<p>Dogs welcome.</p>")
        c = _run(body, [
            {"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"},
            {"field": "phone", "value": "614-798-8802", "quote": "P: 614-798-8802"},
            {"field": "phone", "value": "800-378-7946", "quote": "800-DRURYINN (800-378-7946)"},
        ], tmp_path)
        assert not any(cf.field_name == "phone" for cf in c.conflicts)
        # Both numbers preserved as evidence, each with its classified role.
        roles = sorted(w for e in c.evidence if e.field_name == "phone" for w in e.warnings)
        assert "phone_role:PROPERTY_PHONE" in roles
        assert "phone_role:RESERVATION_PHONE" in roles

    def test_two_property_phones_conflict(self, tmp_path):
        body = ("<p>P: 614-798-8802</p><p>Phone: 614-798-1234</p><p>Dogs welcome.</p>")
        c = _run(body, [
            {"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"},
            {"field": "phone", "value": "614-798-8802", "quote": "P: 614-798-8802"},
            {"field": "phone", "value": "614-798-1234", "quote": "Phone: 614-798-1234"},
        ], tmp_path)
        assert any(cf.field_name == "phone" for cf in c.conflicts)
        assert c.recommendation == C.RECOMMEND_REVIEW


# --------------------------------------------------------------------------- #
# B. Postal-code derivation.
# --------------------------------------------------------------------------- #

class TestPostalDerivation:
    def test_zip_from_full_address(self):
        assert N.extract_postal_from_address("6170 Parkcenter Circle, Dublin, OH 43017") == "43017"

    def test_zip_plus_four(self):
        assert N.extract_postal_from_address("1 A St, Dublin, OH 43017-1234") == "43017"

    def test_no_zip_returns_empty(self):
        assert N.extract_postal_from_address("6170 Parkcenter Circle, Dublin, OH") == ""
        assert N.extract_postal_from_address("") == ""

    def test_derived_in_pipeline_with_evidence(self, tmp_path):
        c = _run("<p>Dogs welcome.</p>", [
            {"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"},
        ], tmp_path)
        assert dict(c.proposed_fields)["postal_code"] == "43017"
        assert dict(c.proposed_fields)["address"] == "6170 Parkcenter Circle"
        # The derived postal carries evidence tied back to the address span.
        pev = [e for e in c.evidence if e.field_name == "postal_code"]
        assert pev and "derived_from:address" in pev[0].warnings

    def test_no_derivation_without_address_zip(self, tmp_path):
        jsonld = (
            '<script type="application/ld+json">{"@type":"Hotel","name":"Drury",'
            '"address":{"@type":"PostalAddress","streetAddress":"6170 Parkcenter Circle",'
            '"addressLocality":"Dublin","addressRegion":"OH"}}</script>')
        c = _run("<p>Dogs welcome.</p>", [
            {"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"},
        ], tmp_path, jsonld=jsonld)
        assert dict(c.proposed_fields)["postal_code"] == ""


# --------------------------------------------------------------------------- #
# C. Co-stated pet-count / weight extraction.
# --------------------------------------------------------------------------- #

class TestCountPhrases:
    @pytest.mark.parametrize("text,expected", [
        ("limit of two pets", "2"),
        ("maximum of 2 pets", "2"),
        ("up to two pets", "2"),
        ("no more than two pets", "2"),
        ("two pets per room", "2"),
        ("Limit of two pets per room with a combined weight of 80 pounds", "2"),
    ])
    def test_count_phrase(self, text, expected):
        assert N.normalize_count(text) == expected

    def test_weight_phrase_not_confused_for_count(self):
        assert N.normalize_count("a combined weight of 80 pounds") == ""

    def test_one_sentence_supports_both(self, tmp_path):
        # LLM proposes only weight_limit from the dual sentence; count is derived.
        c = _run("<p>Dogs welcome. Limit of two pets per room with a combined "
                 "weight of 80 pounds.</p>", [
            {"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"},
            {"field": "weight_limit", "value": "80 pounds",
             "quote": "Limit of two pets per room with a combined weight of 80 pounds"},
        ], tmp_path)
        facts = dict(c.pet_facts)
        assert facts.get("pet_count_limit") == "2"
        assert facts.get("weight_limit") == "80 lb"
        derived = [e for e in c.evidence if e.field_name == "pet_count_limit"]
        assert derived and derived[0].warnings[0].startswith("derived_from:")


# --------------------------------------------------------------------------- #
# D/E9. The full Drury regression.
# --------------------------------------------------------------------------- #

def test_drury_candidate_is_ready(tmp_path):
    body = ("<p>Reservations: 800-DRURYINN (800-378-7946)</p><p>P: 614-798-8802</p>"
            "<p>Dogs and cats welcome. Limit of two pets per room with a combined "
            "weight of 80 pounds.</p>")
    c = _run(body, [
        {"field": "pets_allowed", "value": "true", "quote": "Dogs and cats welcome"},
        {"field": "species_allowed", "value": "dogs and cats", "quote": "Dogs and cats welcome"},
        {"field": "phone", "value": "614-798-8802", "quote": "P: 614-798-8802"},
        {"field": "phone", "value": "800-378-7946", "quote": "800-DRURYINN (800-378-7946)"},
        {"field": "weight_limit", "value": "80 pounds",
         "quote": "Limit of two pets per room with a combined weight of 80 pounds"},
    ], tmp_path)
    p = dict(c.proposed_fields)
    assert p["phone"] == "614-798-8802"
    assert p["postal_code"] == "43017"
    assert p["address"] == "6170 Parkcenter Circle"
    assert dict(c.pet_facts)["pet_count_limit"] == "2"
    assert not any(cf.field_name == "phone" for cf in c.conflicts)
    assert c.recommendation == C.RECOMMEND_READY

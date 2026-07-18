"""AES-DATA-004A discovery -- normalization tests (Task 8)."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import (
    normalize_address_line,
    normalize_business_name,
    normalize_phone,
    normalize_postal,
    normalize_record,
    normalize_state,
    normalize_url,
    names_loosely_compatible,
    registrable_domain,
    validate_coordinate,
)


def test_business_name_case_punct_whitespace():
    assert normalize_business_name("  O'Brien's   Pet Store, LLC.  ") == normalize_business_name("obriens pet store llc")


def test_business_name_preserves_chain_qualifiers():
    assert normalize_business_name("Petco Columbus #864") != normalize_business_name("Petco")
    assert normalize_business_name("MedVet Columbus") != normalize_business_name("MedVet Hilliard")


def test_phone_normalizes_various_formats():
    assert normalize_phone("(614) 555-0100") == "614-555-0100"
    assert normalize_phone("614.555.0100") == "614-555-0100"
    assert normalize_phone("+1 614 555 0100") == "614-555-0100"
    assert normalize_phone("12345") == ""


def test_state_name_and_code():
    assert normalize_state("ohio") == "OH"
    assert normalize_state("OH") == "OH"
    assert normalize_state("Not A State") == ""


def test_postal_code():
    assert normalize_postal("43215") == "43215"
    assert normalize_postal("43215-1234") == "43215"
    assert normalize_postal("abc") == ""


def test_url_normalizes_scheme_host_default_ports():
    assert normalize_url("HTTPS://Example.COM:443/path/") == "https://example.com/path"
    assert normalize_url("not a url") == ""


def test_registrable_domain():
    assert registrable_domain("https://www.example.com/path") == "example.com"
    assert registrable_domain("sub.example.com") == "example.com"
    assert registrable_domain("example.com") == "example.com"


def test_address_line_whitespace():
    assert normalize_address_line("  123   Main   St  ") == "123 Main St"


def test_names_loosely_compatible_exact_only():
    assert names_loosely_compatible("Acme Pets", "acme pets") is True
    assert names_loosely_compatible("Acme Pets", "Acme Pets Columbus") is False   # no fuzzy/prefix


def test_validate_coordinate_bounds_and_null_island():
    assert validate_coordinate(39.96, -82.99) is True
    assert validate_coordinate(91, 0) is False
    assert validate_coordinate(0.0, 0.0) is False
    assert validate_coordinate(None, None) is False


def test_normalize_record_drops_invalid_coordinates_with_warning():
    r = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                        canonical_category=C.CATEGORY_VETERINARY, name="Test",
                        latitude=200.0, longitude=-82.99)
    out = normalize_record(r)
    assert out.latitude is None and out.longitude is None
    assert "invalid_coordinates_dropped" in out.warnings


def test_normalize_record_preserves_raw_name():
    r = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                        canonical_category=C.CATEGORY_VETERINARY, name="ACME Vet Clinic, LLC.")
    out = normalize_record(r)
    assert out.name == "ACME Vet Clinic, LLC."   # raw value untouched
    assert out.normalized_name == normalize_business_name("ACME Vet Clinic, LLC.")


def test_normalize_record_phone_and_state_and_postal():
    r = DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="p1",
                        canonical_category=C.CATEGORY_VETERINARY, name="Test",
                        phone="(614) 555-0100", state="ohio", postal_code="43215-6789")
    out = normalize_record(r)
    assert out.phone == "614-555-0100"
    assert out.state == "OH"
    assert out.postal_code == "43215"

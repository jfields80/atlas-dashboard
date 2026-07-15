"""PILOT-PTF-1 real-launch-package proof (updated AES-WEB-002N.1).

Uses the actual ``launch_packages/pettripfinder/`` sample files (not the
dedicated 12-listing acceptance fixture) to prove the converter and
readiness check behave honestly against real, currently-insufficient
inventory. Does NOT assert launch readiness -- the opposite: it asserts the
real sample package is honestly reported as NOT launch-ready.

AES-WEB-002N.1: the seed authority is now the operator-editable CSV
(``seed_businesses.csv``; the stale JSON was removed), the sample package
carries three clean records (the "Duplicate Sunset Bay Inn" noise moved to
dedicated dedup fixtures in ``tests/pettripfinder/``), provenance survives
into every record, and the readiness verdict counts READY listings only.
"""

from __future__ import annotations

import json
import pathlib

from scripts.generate_pettripfinder_pilot import (
    compute_inventory_readiness,
    load_launch_package,
    read_seed_businesses_csv,
)
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset

_LAUNCH_PACKAGE_DIR = (
    pathlib.Path(__file__).resolve().parents[3] / "launch_packages" / "pettripfinder"
)


def _load(name: str):
    with (_LAUNCH_PACKAGE_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


class TestRealSeedFilesParse:
    def test_seed_businesses_csv_parses(self):
        seed = read_seed_businesses_csv(_LAUNCH_PACKAGE_DIR / "seed_businesses.csv")
        assert len(seed) == 3
        for row in seed:
            # Required publish columns are present in the sample rows.
            for field in ("name", "category", "city", "state", "address",
                          "website_url", "source_url", "source_type",
                          "observed_at", "pet_policy"):
                assert str(row.get(field, "")).strip(), (row.get("name"), field)

    def test_stale_seed_json_removed(self):
        # The JSON seed was removed with the CSV promotion -- one authority.
        assert not (_LAUNCH_PACKAGE_DIR / "seed_businesses.json").exists()

    def test_categories_parses(self):
        cats = _load("categories.json")
        assert len(cats) == 3

    def test_locations_parses(self):
        locs = _load("locations.json")
        assert len(locs) == 2

    def test_pilot_config_parses(self):
        config = _load("pilot_config.json")
        assert config["project_name"] == "PetTripFinder"
        assert config["base_url"] == "https://pettripfinder.com"

    def test_pilot_content_parses(self):
        content = _load("pilot_content.json")
        assert "home" in content
        assert "editorial_pages" in content


class TestRealPackageConversion:
    def _build(self):
        seed = read_seed_businesses_csv(_LAUNCH_PACKAGE_DIR / "seed_businesses.csv")
        cats = _load("categories.json")
        locs = _load("locations.json")
        return build_listing_dataset(seed_businesses=seed, categories=cats, locations=locs)

    def test_clean_package_has_no_duplicates(self):
        # AES-WEB-002N.1 cleanup: the "Duplicate Sunset Bay Inn" noise row
        # was removed from the real package (dedup behavior stays covered
        # by dedicated fixtures in tests/pettripfinder/).
        result = self._build()
        assert result.ok
        assert result.rejected_duplicates == ()

    def test_provenance_survives_into_every_record(self):
        result = self._build()
        assert result.ok
        for listing in result.dataset.listings:
            assert listing.provenance is not None, listing.listing_id
            assert listing.provenance.source_url.startswith("https://")
            assert listing.provenance.source_type
            assert listing.provenance.observed_at

    def test_three_unique_valid_listings_remain(self):
        result = self._build()
        assert result.ok
        assert len(result.dataset.listings) == 3

    def test_no_duplicated_locality_in_street_address(self):
        # AES-WEB-002K.2 address-duplication fix: the real seed package's
        # "123 Sunset Bay Road, Columbus, OH" address field must not carry
        # its own city/state as a trailing, redundant locality.
        result = self._build()
        assert result.ok
        for listing in result.dataset.listings:
            if listing.address is None or not listing.address.city:
                continue
            suffix = ", %s, %s" % (listing.address.city, listing.address.state)
            assert not listing.address.street.endswith(suffix), listing.listing_id

    def test_source_urls_never_become_ctas(self):
        result = self._build()
        assert result.ok
        assert all(listing.cta is None for listing in result.dataset.listings)

    def test_no_verified_badge_produced(self):
        # No listing carries a VERIFIED ListingKind -- the real sample
        # package supplies no verification data at all (§14 honesty rule).
        result = self._build()
        assert result.ok
        from engines.website_generation.contracts.enums import ListingKind
        assert all(
            listing.listing_kind != ListingKind.VERIFIED for listing in result.dataset.listings
        )

    def test_no_fake_default_listings(self):
        result = self._build()
        assert result.ok
        names = {l.business_name for l in result.dataset.listings}
        assert names == {"Sunset Bay Pet-Friendly Inn", "Barkside Cafe", "Riverbend Off-Leash Dog Park"}


class TestRealPackageReadiness:
    def _readiness(self):
        seed = read_seed_businesses_csv(_LAUNCH_PACKAGE_DIR / "seed_businesses.csv")
        cats = _load("categories.json")
        locs = _load("locations.json")
        config = _load("pilot_config.json")
        result = build_listing_dataset(seed_businesses=seed, categories=cats, locations=locs)
        return compute_inventory_readiness(
            result.dataset, config["inventory_thresholds"], reference_date="2026-07-15",
        )

    def test_readiness_is_false(self):
        assert self._readiness()["launch_inventory_ready"] is False

    def test_ready_only_counting(self):
        # AES-WEB-002N.1 (remediated semantics): the strict threshold counts
        # READY listings only, and recommended-field gaps (no phone; no
        # authorized image without the media overlay) are non-demoting
        # advisories -- so the sample's three required-complete, fresh rows
        # are READY, yet still far below the 30/10-per-category threshold.
        readiness = self._readiness()
        assert readiness["total_unique_listings"] == 3
        assert readiness["counts_by_state"]["READY"] == 3
        assert readiness["counts_by_state"]["READY_WITH_WARNINGS"] == 0
        assert readiness["counts_by_state"]["NOT_READY"] == 0
        assert readiness["ready_total"] == 3
        assert set(readiness["categories_below_target"]) == {
            "pet-friendly-hotels", "pet-friendly-parks", "pet-friendly-restaurants",
        }
        for assessment in readiness["assessments"]:
            assert "no_phone" in assessment.advisories

    def test_load_launch_package_helper_matches_direct_reads(self):
        package = load_launch_package()
        assert package["blueprint"]["project_profile"]["project_name"] == "PetTripFinder"
        assert len(package["seed_businesses"]) == 3

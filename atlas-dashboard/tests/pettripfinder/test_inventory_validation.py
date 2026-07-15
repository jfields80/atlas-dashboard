"""Launch inventory contract and validation tests (AES-WEB-002N.1).

Covers the operator CSV loader, canonical-record dedup (closed quality
set + operator override), provenance wiring, the READY /
READY_WITH_WARNINGS / NOT_READY publish assessment (including staleness
against an explicit reference date -- never a clock), READY-only launch
threshold counting, and the deterministic operator readiness report.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.generate_pettripfinder_pilot import read_seed_businesses_csv  # noqa: E402
from scripts.pettripfinder.inventory_validation import (  # noqa: E402
    NOT_READY,
    READY,
    READY_WITH_WARNINGS,
    assess_inventory,
    compute_launch_readiness,
    format_readiness_report,
)
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset  # noqa: E402

_CATEGORIES = [
    {"name": "Pet-Friendly Hotels", "slug": "pet-friendly-hotels"},
    {"name": "Pet-Friendly Parks", "slug": "pet-friendly-parks"},
    {"name": "Pet-Friendly Restaurants", "slug": "pet-friendly-restaurants"},
]

_THRESHOLDS = {
    "minimum_total_listings": 30,
    "minimum_per_category": 10,
    "required_categories": [
        "pet-friendly-hotels", "pet-friendly-parks", "pet-friendly-restaurants",
    ],
}


def _row(**overrides):
    """A fully publish-complete seed row (READY when combined with rating;
    still warns on phone/postal/image unless supplied)."""
    base = {
        "name": "Acme Inn",
        "category": "pet-friendly-hotels",
        "address": "1 Main St",
        "city": "Columbus",
        "state": "OH",
        "postal_code": "43215",
        "phone": "555-0100",
        "website_url": "https://example.com/acme",
        "source_url": "https://example.com/acme/pets",
        "source_type": "OFFICIAL_WEBSITE",
        "observed_at": "2026-07-01",
        "rating": "4.5",
        "pet_policy": "Dogs under 50 lbs welcome, $20/night",
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def _build(rows, media_by_key=None):
    result = build_listing_dataset(
        seed_businesses=rows, categories=_CATEGORIES, media_by_key=media_by_key or {},
    )
    assert result.ok, result.errors
    return result


def _assess_one(row_overrides=None, *, reference_date=""):
    result = _build([_row(**(row_overrides or {}))])
    (assessment,) = assess_inventory(result.dataset, reference_date=reference_date)
    return assessment


# --------------------------------------------------------------------------- #
# CSV loader
# --------------------------------------------------------------------------- #

class TestCsvLoader:
    def test_semicolon_amenities(self, tmp_path):
        csv_path = tmp_path / "seed.csv"
        csv_path.write_text(
            "name,category,city,state,amenities\n"
            "Acme,pet-friendly-hotels,Columbus,OH,water_bowls;patio\n",
            encoding="utf-8",
        )
        (row,) = read_seed_businesses_csv(csv_path)
        assert row["amenities"] == ["water_bowls", "patio"]

    def test_legacy_json_array_amenities(self, tmp_path):
        csv_path = tmp_path / "seed.csv"
        csv_path.write_text(
            'name,category,city,state,amenities\n'
            'Acme,pet-friendly-hotels,Columbus,OH,"[""a"", ""b""]"\n',
            encoding="utf-8",
        )
        (row,) = read_seed_businesses_csv(csv_path)
        assert row["amenities"] == ["a", "b"]

    def test_empty_cells_become_absent_fields(self, tmp_path):
        csv_path = tmp_path / "seed.csv"
        csv_path.write_text(
            "name,category,city,state,phone,amenities\n"
            "Acme,pet-friendly-hotels,Columbus,OH,,\n",
            encoding="utf-8",
        )
        (row,) = read_seed_businesses_csv(csv_path)
        assert "phone" not in row


# --------------------------------------------------------------------------- #
# Canonical dedup
# --------------------------------------------------------------------------- #

class TestCanonicalDedup:
    def test_richer_record_beats_lexically_first_junk(self):
        junk = {
            "name": "Aaa Duplicate Inn", "category": "pet-friendly-hotels",
            "city": "Columbus", "state": "OH",
            "address": "1 Main Street", "pet_policy": "Dogs ok",
        }
        rich = _row(address="1 Main St")  # same normalized address key
        result = _build([junk, rich])
        (listing,) = result.dataset.listings
        assert listing.business_name == "Acme Inn"
        (rejected,) = result.rejected_duplicates
        assert "Aaa Duplicate Inn" in rejected
        assert "duplicate of Acme Inn" in rejected

    def test_operator_canonical_override_wins(self):
        junk = {
            "name": "Aaa Duplicate Inn", "category": "pet-friendly-hotels",
            "city": "Columbus", "state": "OH",
            "address": "1 Main Street", "pet_policy": "Dogs ok",
            "canonical": "true",
        }
        rich = _row(address="1 Main St")
        result = _build([junk, rich])
        assert result.dataset.listings[0].business_name == "Aaa Duplicate Inn"

    def test_conflicting_canonical_markers_fall_through_to_quality(self):
        a = _row(name="Zeta Inn", canonical="true")
        b = dict(_row(name="Alpha Inn", canonical="true"), phone=None)
        b.pop("phone", None)
        result = _build([a, b])
        # Both marked -> markers cancel; Zeta has more closed-set fields.
        assert result.dataset.listings[0].business_name == "Zeta Inn"

    def test_policy_length_breaks_quality_ties(self):
        a = _row(name="Beta Inn", pet_policy="Dogs welcome with a very detailed policy statement")
        b = _row(name="Alpha Inn")
        result = _build([a, b])
        assert result.dataset.listings[0].business_name == "Beta Inn"

    def test_lexical_name_is_final_tie_break(self):
        a = _row(name="Beta Inn")
        b = _row(name="Alpha Inn")
        result = _build([a, b])
        assert result.dataset.listings[0].business_name == "Alpha Inn"

    def test_arbitrary_extra_fields_never_change_selection(self):
        # Closed-set rule: a pile of unrelated optional fields on the junk
        # record must not out-rank real quality fields.
        junk = {
            "name": "Aaa Duplicate Inn", "category": "pet-friendly-hotels",
            "city": "Columbus", "state": "OH", "address": "1 Main Street",
            "pet_policy": "Dogs ok",
            "extra_a": "x", "extra_b": "y", "extra_c": "z", "extra_d": "w",
        }
        rich = _row(address="1 Main St")
        result = _build([junk, rich])
        assert result.dataset.listings[0].business_name == "Acme Inn"

    def test_rejected_duplicates_always_reported(self):
        result = _build([_row(), _row(name="Other Name Same Address")])
        assert len(result.rejected_duplicates) == 1


# --------------------------------------------------------------------------- #
# Provenance wiring
# --------------------------------------------------------------------------- #

class TestProvenance:
    def test_provenance_fields_survive(self):
        result = _build([_row()])
        provenance = result.dataset.listings[0].provenance
        assert provenance.source_id == "example.com"
        assert provenance.source_type == "OFFICIAL_WEBSITE"
        assert provenance.source_url == "https://example.com/acme/pets"
        assert provenance.observed_at == "2026-07-01"

    def test_unsafe_source_url_rejected(self):
        row = _row(source_url="javascript:evil()")
        result = build_listing_dataset(seed_businesses=[row], categories=_CATEGORIES)
        assert not result.ok
        assert any("unsafe_source_url" in e for e in result.errors)

    def test_missing_source_url_yields_no_provenance(self):
        row = _row(source_url=None, source_type=None, observed_at=None)
        result = _build([row])
        assert result.dataset.listings[0].provenance is None


# --------------------------------------------------------------------------- #
# Readiness states
# --------------------------------------------------------------------------- #

class TestReadinessStates:
    def test_fully_complete_listing_is_ready_with_no_advisories(self):
        from engines.website_generation.contracts.artifacts import (
            ListingAssetRef,
            sha256_of_bytes,
        )
        from engines.website_generation.contracts.enums import AssetRole

        ref = ListingAssetRef(
            role=AssetRole.HERO_IMAGE, asset_hash=sha256_of_bytes(b"img"),
            mime_type="image/png", bundle_allowed=True,
        )
        result = _build(
            [_row()], media_by_key={("acme inn", "columbus", "oh"): (ref,)},
        )
        (assessment,) = assess_inventory(result.dataset)
        assert assessment.state == READY
        assert assessment.missing_required == ()
        assert assessment.warnings == ()
        assert assessment.advisories == ()

    def test_recommended_gaps_are_advisories_never_demoting(self):
        # Remediated doctrine (proof A): all required fields present but no
        # phone, no postal code, no rating, no image -> still READY, with
        # every gap visible as an advisory.
        assessment = _assess_one({"phone": None, "postal_code": None, "rating": None})
        assert assessment.state == READY
        assert assessment.warnings == ()
        assert set(assessment.advisories) == {
            "no_phone", "no_postal_code", "no_rating", "no_authorized_image",
        }

    def test_no_rating_never_required_for_ready(self):
        # Proof E: a listing without a trustworthy rating source must still
        # be capable of READY -- ratings are never fabricated to qualify.
        assessment = _assess_one({"rating": None})
        assert assessment.state == READY
        assert "no_rating" in assessment.advisories

    def test_no_authorized_image_never_required_for_ready(self):
        # Proof F: images are recommended, not required.
        assessment = _assess_one({})
        assert assessment.state == READY
        assert "no_authorized_image" in assessment.advisories

    @pytest.mark.parametrize("field,expected", [
        ("address", "street_address"),
        ("source_url", "source_url"),
        ("source_type", "source_type"),
        ("observed_at", "observed_at"),
        ("pet_policy", "pet_policy"),
        ("website_url", "website_url"),
    ])
    def test_each_missing_required_field_is_not_ready(self, field, expected):
        overrides = {field: None}
        if field == "source_url":
            # Without a source_url no provenance exists at all -- the
            # source_type/observed_at requirements fail with it.
            overrides.update({"source_type": None, "observed_at": None})
        assessment = _assess_one(overrides)
        assert assessment.state == NOT_READY
        assert expected in assessment.missing_required

    def test_malformed_observed_date_is_not_ready(self):
        assessment = _assess_one({"observed_at": "last Tuesday"})
        assert assessment.state == NOT_READY
        assert "observed_at" in assessment.missing_required

    def test_park_requires_official_page_like_everyone(self):
        assessment = _assess_one({
            "category": "pet-friendly-parks", "website_url": None,
        })
        assert assessment.state == NOT_READY
        assert "website_url" in assessment.missing_required


# --------------------------------------------------------------------------- #
# Staleness (explicit reference date -- never a clock)
# --------------------------------------------------------------------------- #

class TestStaleness:
    def test_hotel_stale_after_180_days(self):
        # Proof B: staleness is the one N.1 condition that demotes an
        # otherwise-complete listing to READY_WITH_WARNINGS -- publishable,
        # but not threshold-counting until refreshed.
        assessment = _assess_one(
            {"observed_at": "2026-01-01"}, reference_date="2026-07-15",
        )  # 195 days
        assert assessment.state == READY_WITH_WARNINGS
        assert any(w.startswith("stale_observation") for w in assessment.warnings)

    def test_hotel_fresh_within_180_days(self):
        assessment = _assess_one(
            {"observed_at": "2026-06-01"}, reference_date="2026-07-15",
        )
        assert assessment.state == READY
        assert assessment.warnings == ()

    def test_park_fresh_at_200_days_stale_after_365(self):
        fresh = _assess_one(
            {"category": "pet-friendly-parks", "observed_at": "2026-01-01"},
            reference_date="2026-07-15",
        )
        assert not any(w.startswith("stale_observation") for w in fresh.warnings)
        stale = _assess_one(
            {"category": "pet-friendly-parks", "observed_at": "2025-07-01"},
            reference_date="2026-07-15",
        )
        assert any(w.startswith("stale_observation") for w in stale.warnings)

    def test_empty_reference_date_skips_staleness(self):
        assessment = _assess_one({"observed_at": "2020-01-01"}, reference_date="")
        assert not any(w.startswith("stale_observation") for w in assessment.warnings)


# --------------------------------------------------------------------------- #
# Launch threshold counting (READY only; NOT_READY blocks)
# --------------------------------------------------------------------------- #

class TestLaunchThreshold:
    def _publishable_rows(self, count_per_category):
        """Rows complete on every required field, with ordinary advisory
        gaps left in place (no phone, no image, no rating on some) -- the
        remediated doctrine says these still count (proof D)."""
        rows = []
        for cat in ("pet-friendly-hotels", "pet-friendly-parks", "pet-friendly-restaurants"):
            for i in range(count_per_category):
                name = "%s Biz %02d" % (cat.split("-")[-1].title(), i)
                overrides = {
                    "name": name, "category": cat,
                    "address": "%d %s Way" % (100 + i, cat),
                }
                if i % 2 == 0:
                    overrides["phone"] = None
                    overrides["rating"] = None
                rows.append(_row(**overrides))
        return rows

    def test_thirty_listings_with_advisory_gaps_pass(self):
        # Proof D: 30 fully publishable listings -- none with an image,
        # half without phone/rating -- satisfy 30 total / 10 per category.
        rows = self._publishable_rows(10)
        result = _build(rows)
        assessments = assess_inventory(result.dataset)
        assert all(a.state == READY for a in assessments)
        assert all("no_authorized_image" in a.advisories for a in assessments)
        readiness = compute_launch_readiness(assessments, _THRESHOLDS)
        assert readiness["ready_total"] == 30
        assert readiness["launch_inventory_ready"] is True

    def test_stale_listings_do_not_count_toward_threshold(self):
        # Proof B (threshold half): one stale hotel -> READY_WITH_WARNINGS
        # -> hotels drop to 9 and launch readiness fails.
        rows = self._publishable_rows(10)
        rows[0] = dict(rows[0], observed_at="2025-01-01")
        result = _build(rows)
        readiness = compute_launch_readiness(
            assess_inventory(result.dataset, reference_date="2026-07-15"),
            _THRESHOLDS,
        )
        assert readiness["counts_by_state"][READY_WITH_WARNINGS] == 1
        assert readiness["ready_total"] == 29
        assert readiness["categories_below_target"] == ["pet-friendly-hotels"]
        assert readiness["launch_inventory_ready"] is False

    def test_single_not_ready_listing_blocks_launch(self):
        # Proof C: missing required field -> NOT_READY -> never counts and
        # blocks production launch even with 30 READY listings present.
        rows = self._publishable_rows(10)
        rows.append({
            "name": "Hollow Record", "category": "pet-friendly-hotels",
            "city": "Columbus", "state": "OH", "address": "9 Nowhere Rd",
        })
        result = _build(rows)
        assessments = assess_inventory(result.dataset)
        readiness = compute_launch_readiness(assessments, _THRESHOLDS)
        hollow = next(a for a in assessments if a.business_name == "Hollow Record")
        assert hollow.state == NOT_READY
        assert readiness["ready_total"] == 30  # thresholds numerically met...
        assert readiness["counts_by_state"][NOT_READY] == 1
        assert readiness["launch_inventory_ready"] is False  # ...but blocked


# --------------------------------------------------------------------------- #
# Report determinism
# --------------------------------------------------------------------------- #

class TestReportDeterminism:
    def test_report_is_deterministic_and_names_everything(self):
        result = _build([_row(), _row(
            name="Beta Cafe", category="pet-friendly-restaurants",
            address="2 Side St", phone=None,
        )])
        assessments = assess_inventory(result.dataset, reference_date="2026-07-15")
        readiness = compute_launch_readiness(assessments, _THRESHOLDS)
        first = format_readiness_report(assessments, readiness, result.rejected_duplicates)
        second = format_readiness_report(assessments, readiness, result.rejected_duplicates)
        assert first == second
        assert "Acme Inn" in first and "Beta Cafe" in first
        assert "launch_inventory_ready: False" in first

    def test_ready_listings_show_advisory_gaps(self):
        # Remediated doctrine (proof A, reporting half): READY listings
        # keep their advisory gaps visible in the operator report.
        result = _build([_row(phone=None, rating=None)])
        assessments = assess_inventory(result.dataset)
        readiness = compute_launch_readiness(assessments, _THRESHOLDS)
        report = format_readiness_report(assessments, readiness)
        assert "[READY] Acme Inn" in report
        assert "advisory: no_phone" in report
        assert "advisory: no_rating" in report
        assert "advisory: no_authorized_image" in report

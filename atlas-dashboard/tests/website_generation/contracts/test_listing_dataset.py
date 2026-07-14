"""ListingDataset contract tests (AES-WEB-002J.17; ADR-WEB-LISTING-DATASET).

Covers: valid construction (empty, single, multiple, every optional nested
model), identity/route rules, cross-record reference integrity, numeric
range validation, contact/hours validation, sponsorship/verification
independence, asset/provenance validation, catalog/versioning registration,
and the architectural invariants (no legacy imports, no forbidden runtime
facilities, deterministic canonical hashing).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engines.website_generation import (
    SCHEMA_VERSIONS,
    ArtifactKind,
    ArtifactValidationError,
    ListingAddress,
    ListingAssetRef,
    ListingCTA,
    ListingCategory,
    ListingContact,
    ListingDataset,
    ListingGeo,
    ListingHoursEntry,
    ListingLocation,
    ListingProvenance,
    ListingRating,
    ListingRecord,
    ListingSponsorship,
    ListingVerification,
    AssetRole,
    ListingKind,
    VerificationStatus,
    Weekday,
    artifact_sha256,
    canonical_artifact_json,
    registered_artifact_model,
    validate_listing_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    REPO_ROOT
    / "engines"
    / "website_generation"
    / "contracts"
    / "listing_dataset_validator.py"
)


def _header(**overrides):
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
    )
    fields.update(overrides)
    return fields


def _category(category_id="cat-hotels", label="Hotels", slug="hotels") -> ListingCategory:
    return ListingCategory(category_id=category_id, label=label, slug=slug)


def _location(location_id="loc-austin", city="Austin", state="TX", slug="austin-tx") -> ListingLocation:
    return ListingLocation(location_id=location_id, city=city, state=state, slug=slug)


def _listing(**overrides) -> ListingRecord:
    fields = dict(
        listing_id="lakeview-lodge",
        business_name="Lakeview Lodge",
        slug="lakeview-lodge",
        category_id="cat-hotels",
        location_id="loc-austin",
    )
    fields.update(overrides)
    return ListingRecord(**fields)


def _dataset(listings=(), categories=(_category(),), locations=(_location(),), **overrides) -> ListingDataset:
    return ListingDataset(listings=listings, categories=categories, locations=locations, **_header(**overrides))


# --------------------------------------------------------------------------- #
# A. Valid artifacts
# --------------------------------------------------------------------------- #

class TestValidDatasets:
    def test_empty_dataset_is_valid(self):
        dataset = ListingDataset(**_header())
        assert dataset.listings == ()
        assert dataset.categories == ()
        assert dataset.locations == ()
        validate_listing_dataset(dataset)  # does not raise

    def test_categories_with_no_listings_valid(self):
        dataset = _dataset(listings=(), categories=(_category(),), locations=())
        validate_listing_dataset(dataset)

    def test_locations_with_no_listings_valid(self):
        dataset = _dataset(listings=(), categories=(), locations=(_location(),))
        validate_listing_dataset(dataset)

    def test_one_listing(self):
        dataset = _dataset(listings=(_listing(),))
        validate_listing_dataset(dataset)
        assert len(dataset.listings) == 1

    def test_multiple_listings(self):
        dataset = _dataset(
            listings=(
                _listing(listing_id="a", slug="a"),
                _listing(listing_id="b", slug="b"),
            )
        )
        validate_listing_dataset(dataset)
        assert len(dataset.listings) == 2

    def test_organic_listing(self):
        listing = _listing(listing_kind=ListingKind.ORGANIC)
        dataset = _dataset(listings=(listing,))
        validate_listing_dataset(dataset)

    def test_sponsored_listing(self):
        listing = _listing(
            listing_kind=ListingKind.SPONSORED,
            sponsorship=ListingSponsorship(
                kind=ListingKind.SPONSORED, disclosure_text="Sponsored placement"
            ),
        )
        dataset = _dataset(listings=(listing,))
        validate_listing_dataset(dataset)

    def test_verified_listing(self):
        listing = _listing(
            verification=ListingVerification(
                status=VerificationStatus.VERIFIED,
                verified_at="2026-01-01",
                source="operator-review",
            )
        )
        dataset = _dataset(listings=(listing,))
        validate_listing_dataset(dataset)

    def test_unrated_listing_has_no_rating_field(self):
        listing = _listing()
        assert listing.rating is None
        dataset = _dataset(listings=(listing,))
        validate_listing_dataset(dataset)

    def test_listing_with_every_optional_nested_model(self):
        listing = _listing(
            description="A lakeside lodge that welcomes pets.",
            contact=ListingContact(
                phone="555-0100", email="stay@lakeview.example",
                website_url="https://lakeview.example",
            ),
            address=ListingAddress(
                street="1 Lake Rd", city="Austin", state="TX",
                postal_code="78701", country="US",
            ),
            geo=ListingGeo(lat_micro=30_267_000, long_micro=-97_743_000),
            rating=ListingRating(rating_hundredths=450, review_count=900),
            hours=(
                ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),
                ListingHoursEntry(day=Weekday.SUNDAY, closed=True),
            ),
            sponsorship=ListingSponsorship(kind=ListingKind.ORGANIC),
            verification=ListingVerification(status=VerificationStatus.UNVERIFIED),
            credentials=("Licensed pet boarding",),
            assets=(ListingAssetRef(role=AssetRole.LOGO, asset_hash="a" * 64),),
            cta=ListingCTA(label="Book now", target_route="/hotels/lakeview-lodge/"),
            provenance=ListingProvenance(source_id="src-1", observed_at="2026-01-01"),
        )
        dataset = _dataset(listings=(listing,))
        validate_listing_dataset(dataset)

    def test_canonical_json_deterministic(self):
        dataset = _dataset(listings=(_listing(),))
        a = canonical_artifact_json(dataset)
        b = canonical_artifact_json(_dataset(listings=(_listing(),)))
        assert a == b

    def test_artifact_hash_stable(self):
        dataset = _dataset(listings=(_listing(),))
        assert artifact_sha256(dataset) == artifact_sha256(
            _dataset(listings=(_listing(),))
        )

    def test_hash_changes_with_content(self):
        a = _dataset(listings=(_listing(),))
        b = _dataset(listings=(_listing(business_name="Different Name"),))
        assert artifact_sha256(a) != artifact_sha256(b)


# --------------------------------------------------------------------------- #
# B. Identity and routing
# --------------------------------------------------------------------------- #

class TestIdentityAndRouting:
    def test_valid_ids_and_slugs_accepted(self):
        listing = _listing(listing_id="lake-view-lodge-2", slug="lake-view-lodge-2")
        dataset = _dataset(listings=(listing,))
        validate_listing_dataset(dataset)

    def test_invalid_listing_id_rejected(self):
        listing = _listing(listing_id="Lake View!", slug="lake-view-lodge")
        dataset = _dataset(listings=(listing,))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "invalid_ids" in exc.value.diagnostics

    def test_invalid_slug_rejected(self):
        listing = _listing(slug="not_a_slug")
        dataset = _dataset(listings=(listing,))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "invalid_ids" in exc.value.diagnostics

    def test_duplicate_listing_id_rejected(self):
        dataset = _dataset(
            listings=(
                _listing(listing_id="dup", slug="a"),
                _listing(listing_id="dup", slug="b"),
            )
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "duplicate_listing_ids" in exc.value.diagnostics

    def test_duplicate_category_id_rejected(self):
        dataset = _dataset(
            categories=(_category(category_id="c1"), _category(category_id="c1", slug="other"))
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "duplicate_category_ids" in exc.value.diagnostics

    def test_duplicate_location_id_rejected(self):
        dataset = _dataset(
            locations=(_location(location_id="l1"), _location(location_id="l1", slug="other"))
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "duplicate_location_ids" in exc.value.diagnostics

    def test_duplicate_category_slug_pair_rejected(self):
        dataset = _dataset(
            listings=(
                _listing(listing_id="a", slug="same-slug", category_id="cat-hotels"),
                _listing(listing_id="b", slug="same-slug", category_id="cat-hotels"),
            )
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "duplicate_category_slugs" in exc.value.diagnostics

    def test_duplicate_derived_route_rejected(self):
        # Same category + same slug via two different listing_ids triggers
        # both duplicate_category_slugs and duplicate_routes.
        dataset = _dataset(
            listings=(
                _listing(listing_id="a", slug="same", category_id="cat-hotels"),
                _listing(listing_id="b", slug="same", category_id="cat-hotels"),
            )
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "duplicate_routes" in exc.value.diagnostics

    def test_route_is_not_a_stored_field(self):
        with pytest.raises(Exception):  # extra="forbid" -- pydantic v1/v2 both raise
            ListingRecord(
                listing_id="x", business_name="X", slug="x",
                category_id="cat-hotels", canonical_route="/hotels/x/",
            )

    def test_input_tuple_ordering_is_preserved(self):
        dataset = _dataset(
            listings=(
                _listing(listing_id="z", slug="z"),
                _listing(listing_id="a", slug="a"),
            )
        )
        assert [l.listing_id for l in dataset.listings] == ["z", "a"]

    def test_reordered_input_changes_canonical_bytes(self):
        # Producers must sort deterministically themselves -- the artifact
        # does not silently reorder caller data (ADR / mission directive).
        forward = _dataset(
            listings=(
                _listing(listing_id="a", slug="a"),
                _listing(listing_id="b", slug="b"),
            )
        )
        reversed_ = _dataset(
            listings=(
                _listing(listing_id="b", slug="b"),
                _listing(listing_id="a", slug="a"),
            )
        )
        assert canonical_artifact_json(forward) != canonical_artifact_json(reversed_)


# --------------------------------------------------------------------------- #
# C. References
# --------------------------------------------------------------------------- #

class TestReferences:
    def test_category_reference_resolves(self):
        dataset = _dataset(listings=(_listing(category_id="cat-hotels"),))
        validate_listing_dataset(dataset)

    def test_missing_category_reference_rejected(self):
        dataset = _dataset(listings=(_listing(category_id="cat-does-not-exist"),))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "unresolved_category_refs" in exc.value.diagnostics

    def test_location_reference_resolves(self):
        dataset = _dataset(listings=(_listing(location_id="loc-austin"),))
        validate_listing_dataset(dataset)

    def test_missing_nonempty_location_reference_rejected(self):
        dataset = _dataset(listings=(_listing(location_id="loc-does-not-exist"),))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(dataset)
        assert "unresolved_location_refs" in exc.value.diagnostics

    def test_empty_location_id_accepted(self):
        dataset = _dataset(listings=(_listing(location_id=""),))
        validate_listing_dataset(dataset)


# --------------------------------------------------------------------------- #
# D. Numeric validation
# --------------------------------------------------------------------------- #

class TestNumericValidation:
    def test_rating_zero_accepted(self):
        listing = _listing(rating=ListingRating(rating_hundredths=0, review_count=0))
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_rating_five_hundred_accepted(self):
        listing = _listing(rating=ListingRating(rating_hundredths=500, review_count=1))
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_rating_below_range_rejected(self):
        listing = _listing(rating=ListingRating(rating_hundredths=-1, review_count=1))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "invalid_ratings" in exc.value.diagnostics

    def test_rating_above_range_rejected(self):
        listing = _listing(rating=ListingRating(rating_hundredths=501, review_count=1))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "invalid_ratings" in exc.value.diagnostics

    def test_negative_review_count_rejected(self):
        listing = _listing(rating=ListingRating(rating_hundredths=400, review_count=-1))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "invalid_review_counts" in exc.value.diagnostics

    def test_coordinate_boundaries_accepted(self):
        listing = _listing(geo=ListingGeo(lat_micro=90_000_000, long_micro=180_000_000))
        validate_listing_dataset(_dataset(listings=(listing,)))
        listing2 = _listing(
            listing_id="b", slug="b",
            geo=ListingGeo(lat_micro=-90_000_000, long_micro=-180_000_000),
        )
        validate_listing_dataset(_dataset(listings=(listing2,)))

    def test_coordinate_overflow_rejected(self):
        listing = _listing(geo=ListingGeo(lat_micro=90_000_001, long_micro=0))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "invalid_coordinates" in exc.value.diagnostics

    def test_no_float_accepted_anywhere_in_canonical_payload(self):
        dataset = _dataset(
            listings=(
                _listing(
                    rating=ListingRating(rating_hundredths=450, review_count=900),
                    geo=ListingGeo(lat_micro=30_267_000, long_micro=-97_743_000),
                ),
            )
        )
        payload = canonical_artifact_json(dataset)
        assert "." not in payload.replace('"1.0.0"', "")  # no decimal points outside the schema-version string


# --------------------------------------------------------------------------- #
# E. Contact / hours
# --------------------------------------------------------------------------- #

class TestContactAndHours:
    def test_valid_url_email_phone_shapes(self):
        listing = _listing(
            contact=ListingContact(
                phone="555-0100", email="a@b.com", website_url="https://x.example"
            )
        )
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_unsafe_website_url_rejected(self):
        listing = _listing(
            contact=ListingContact(website_url="javascript:alert(1)")
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "unsafe_urls" in exc.value.diagnostics

    def test_unsafe_source_url_rejected(self):
        listing = _listing(
            provenance=ListingProvenance(source_id="s1", source_url="data:text/html,x")
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "unsafe_urls" in exc.value.diagnostics

    def test_unsafe_cta_target_rejected(self):
        listing = _listing(
            cta=ListingCTA(label="Book", target_route="//evil.example/x")
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "unsafe_urls" in exc.value.diagnostics

    def test_local_path_asset_rejected(self):
        listing = _listing(
            assets=(ListingAssetRef(role=AssetRole.LOGO, asset_hash="C:/local/path.png"),)
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "unsafe_asset_refs" in exc.value.diagnostics

    def test_valid_hours(self):
        listing = _listing(
            hours=(ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),)
        )
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_duplicate_weekday_rejected(self):
        listing = _listing(
            hours=(
                ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),
                ListingHoursEntry(day=Weekday.MONDAY, opens="09:00", closes="21:00"),
            )
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "invalid_hours" in exc.value.diagnostics

    def test_closed_day_accepted(self):
        listing = _listing(hours=(ListingHoursEntry(day=Weekday.SUNDAY, closed=True),))
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_incomplete_open_close_pair_rejected(self):
        listing = _listing(
            hours=(ListingHoursEntry(day=Weekday.MONDAY, opens="08:00"),)
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "invalid_hours" in exc.value.diagnostics

    def test_malformed_time_rejected(self):
        listing = _listing(
            hours=(ListingHoursEntry(day=Weekday.MONDAY, opens="8am", closes="20:00"),)
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "invalid_hours" in exc.value.diagnostics


# --------------------------------------------------------------------------- #
# F. Sponsorship and verification
# --------------------------------------------------------------------------- #

class TestSponsorshipAndVerification:
    def test_organic_unverified(self):
        listing = _listing(
            listing_kind=ListingKind.ORGANIC,
            verification=ListingVerification(status=VerificationStatus.UNVERIFIED),
        )
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_sponsored_unverified(self):
        listing = _listing(
            listing_kind=ListingKind.SPONSORED,
            sponsorship=ListingSponsorship(kind=ListingKind.SPONSORED),
            verification=ListingVerification(status=VerificationStatus.UNVERIFIED),
        )
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_organic_verified(self):
        listing = _listing(
            listing_kind=ListingKind.ORGANIC,
            verification=ListingVerification(status=VerificationStatus.VERIFIED),
        )
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_sponsored_and_verified_are_independent_axes(self):
        listing = _listing(
            listing_kind=ListingKind.SPONSORED,
            sponsorship=ListingSponsorship(kind=ListingKind.SPONSORED),
            verification=ListingVerification(status=VerificationStatus.VERIFIED),
        )
        validate_listing_dataset(_dataset(listings=(listing,)))  # no inference/rejection

    def test_supplied_verified_at_preserved(self):
        listing = _listing(
            verification=ListingVerification(
                status=VerificationStatus.VERIFIED, verified_at="2026-01-01T00:00:00Z"
            )
        )
        assert listing.verification.verified_at == "2026-01-01T00:00:00Z"

    def test_no_clock_generated_value_field_exists(self):
        # ListingVerification/ListingProvenance accept only caller-supplied
        # strings -- there is no default_factory reading the clock.
        v = ListingVerification(status=VerificationStatus.UNVERIFIED)
        assert v.verified_at == ""
        p = ListingProvenance(source_id="s")
        assert p.observed_at == ""


# --------------------------------------------------------------------------- #
# G. Assets and provenance
# --------------------------------------------------------------------------- #

class TestAssetsAndProvenance:
    def test_valid_asset_hash(self):
        listing = _listing(
            assets=(ListingAssetRef(role=AssetRole.LOGO, asset_hash="a" * 64),)
        )
        validate_listing_dataset(_dataset(listings=(listing,)))

    def test_url_asset_rejected(self):
        listing = _listing(
            assets=(ListingAssetRef(role=AssetRole.LOGO, asset_hash="https://x/logo.png"),)
        )
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "unsafe_asset_refs" in exc.value.diagnostics

    def test_provenance_supplied_and_preserved(self):
        listing = _listing(
            provenance=ListingProvenance(
                source_id="src-1", source_type="import", source_record_id="rec-9",
                source_url="https://source.example/rec-9", observed_at="2026-01-01",
                source_hash="c" * 64,
            )
        )
        dataset = _dataset(listings=(listing,))
        validate_listing_dataset(dataset)
        assert dataset.listings[0].provenance.source_id == "src-1"

    def test_empty_optional_provenance_absent_by_default(self):
        listing = _listing()
        assert listing.provenance is None

    def test_empty_provenance_source_id_rejected(self):
        listing = _listing(provenance=ListingProvenance(source_id=""))
        with pytest.raises(ArtifactValidationError) as exc:
            validate_listing_dataset(_dataset(listings=(listing,)))
        assert "empty_provenance_source_ids" in exc.value.diagnostics

    def test_source_hashes_deterministic(self):
        dataset = _dataset(listings=(_listing(),), source_hashes={"external:x": "a" * 64})
        assert artifact_sha256(dataset) == artifact_sha256(
            _dataset(listings=(_listing(),), source_hashes={"external:x": "a" * 64})
        )


# --------------------------------------------------------------------------- #
# H. Catalog / versioning
# --------------------------------------------------------------------------- #

class TestCatalogVersioning:
    def test_thirteenth_artifact_kind_present(self):
        assert ArtifactKind.LISTING_DATASET in list(ArtifactKind)
        assert len(list(ArtifactKind)) == 13

    def test_listing_dataset_registered_at_1_0_0(self):
        model_cls = registered_artifact_model(ArtifactKind.LISTING_DATASET, "1.0.0")
        assert model_cls is ListingDataset

    def test_schema_versions_map_has_entry(self):
        assert SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET] == "1.0.0"

    def test_no_existing_artifact_version_changed(self):
        unchanged = {
            ArtifactKind.BUSINESS_SPEC: "1.0.0",
            ArtifactKind.CONTENT_CANDIDATE: "1.0.0",
            ArtifactKind.CONTENT_PACKAGE: "1.0.0",
            ArtifactKind.SEO_PACKAGE: "1.0.0",
            ArtifactKind.BUILD_MANIFEST: "1.0.0",
            ArtifactKind.BRAND_PACKAGE: "1.1.0",
            ArtifactKind.SITE_ARCHITECTURE: "1.1.0",
            ArtifactKind.COMPONENT_MANIFEST: "1.1.0",
            ArtifactKind.LAYOUT_PLAN: "1.1.0",
            ArtifactKind.RENDERED_PAGE_SET: "1.1.0",
            ArtifactKind.SITE_BUNDLE: "1.1.0",
            ArtifactKind.QUALITY_REPORT: "1.1.0",
        }
        for kind, version in unchanged.items():
            assert SCHEMA_VERSIONS[kind] == version

    def test_no_engine_version_added_for_listing_dataset(self):
        from engines.website_generation import ENGINE_VERSIONS

        assert "listing_dataset" not in ENGINE_VERSIONS
        assert "listing_dataset_engine" not in ENGINE_VERSIONS


# --------------------------------------------------------------------------- #
# I. Architecture
# --------------------------------------------------------------------------- #

class TestArchitecture:
    def _source(self) -> str:
        return MODULE_PATH.read_text(encoding="utf-8")

    def test_no_legacy_model_imports(self):
        src = self._source()
        for banned in (
            "directory_builder", "directory_ingestion", "launch_kit",
            "directory_blueprint",
        ):
            assert banned not in src, banned

    def test_no_services_or_repositories_imports(self):
        src = self._source()
        assert "services." not in src
        assert "repositories." not in src
        assert "import services" not in src
        assert "import repositories" not in src

    def test_no_forbidden_runtime_facilities(self):
        src = self._source()
        for banned in (
            "import socket", "import urllib", "import requests", "import uuid",
            "import random", "import datetime", "os.environ", "import webbrowser",
            "http.server", "import subprocess", "time.time", "anthropic",
            "import time",
        ):
            assert banned not in src, banned

    def test_validator_imports_only_stdlib_and_contracts(self):
        tree = ast.parse(self._source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.startswith(
                    "engines.website_generation.contracts"
                ) or node.module in ("typing", "__future__"), node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name in ("re", "typing"), alias.name

    def test_public_surface_intentional(self):
        import engines.website_generation as wge

        for name in (
            "ListingDataset", "ListingRecord", "ListingCategory",
            "ListingLocation", "validate_listing_dataset",
        ):
            assert name in wge.__all__

    def test_pipeline_remains_unwired(self):
        from engines.website_generation.constants.build import (
            PHASE1_EXECUTED_STAGES,
            STAGE_SPEC_COMPILATION,
        )

        assert PHASE1_EXECUTED_STAGES == (STAGE_SPEC_COMPILATION,)

    def test_all_components_remain_proposed(self):
        from engines.website_generation.components.registry import build_default_registry

        registry = build_default_registry()
        ids = [d.component_id for d in registry.all_definitions()]
        assert {str(registry.lifecycle(c)) for c in ids} == {"LifecycleStatus.PROPOSED"}

    def test_no_dict_str_any_in_module(self):
        src = MODULE_PATH.parent.joinpath("artifacts.py").read_text(encoding="utf-8")
        # ListingDataset section only -- crude but effective guard against a
        # future Dict[str, Any] creeping into the new models specifically.
        section = src[src.index("class ListingContact") :]
        assert "Dict[str, Any]" not in section
